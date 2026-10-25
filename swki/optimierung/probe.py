"""Geometrie einer Probe und Prüfstufe 0 (Spec C2 §4): Werte der Stellschrauben in die Specs (im Speicher), Schnellbau
der Baugruppe (C1), Validierung der geänderten Specs, Kollision je Gelenk-Endstellung, Bauraum; danach die konvexen
Stücke für die Prüfaufgabe (Zerlegung je Teil und Parameterstand zwischengespeichert).

Gebaut wird aus einer Kopie der Specs im Lauf-Ordner (`specs/`), damit eine Studie eine feste Form hat. Eine Teil-Spec
mit Block wird als Baugruppe aus einer fixierten Komponente gerechnet (Komponente = Dateiname ohne Endung).
Kollision: je Paar von Komponenten verschiedener Körper bzw. jedes Paar, das im Ausgangsstand frei ist (Paare, die
sich schon im freigegebenen Stand schneiden – verschraubt, eingepresst –, nimmt der Ausgangsstand aus und meldet sie).
"""

import copy
import hashlib
import json
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from build123d import Axis, Location

from swki.optimierung.auftrag import Auftrag, je_datei
from swki.schnellbau.baugruppe import Baugruppe
from swki.schnellbau.fehler import SchnellbauFehler
from swki.schnellbau.zerlegung import zerlege
from swki.spec.laden import plausibel_befunde, schema_befunde


@dataclass
class Geometrie:
    werte: dict
    befunde: list = field(default_factory=list)          # Prüfstufe 0: Validierung
    kollisionen: list = field(default_factory=list)      # [{stellung, a, b, mm3}]
    bauraum: list = field(default_factory=list)          # Überschreitungen
    daten: dict | None = None                            # Probe für die Arbeitsprozesse (JSON)
    zeiten: dict = field(default_factory=dict)
    bg: Baugruppe | None = None

    @property
    def gueltig(self) -> bool:
        return not (self.befunde or self.kollisionen or self.bauraum)

    def stufe0(self) -> dict:
        return {"befunde": self.befunde[:5], "kollisionen": self.kollisionen[:5], "bauraum": self.bauraum[:3]}


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:24]


class Probenbau:
    def __init__(self, auftrag: Auftrag, specs: Path, cache: Path, simulation: dict | None = None):
        """specs: Ordner mit der Kopie der Specs; cache: Zerlegungen."""
        self.a = auftrag
        self.specs = specs
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)
        self.sim = simulation or {}
        self.datei = auftrag.spec_pfad.name
        self.spec = yaml.safe_load((specs / self.datei).read_text(encoding="utf-8"))
        self.ist_baugruppe = self.spec.get("art") == "baugruppe"
        neben = self.a.block.get("nebenbedingungen", {})
        self.kollision = neben.get("kollision", {})
        self.toleranz = self.kollision.get("toleranz_mm3", 0.01)
        self.ausnehmen = {frozenset(p) for p in self.kollision.get("ausnehmen", [])}
        self.grund_paare: set | None = None      # im Ausgangsstand schon geschnittene Paare (aus der ersten Probe)
        self.grund_meldung: list = []
        self.zerlegungen = {"neu": 0, "cache": 0}
        self._paare: dict = {}                   # (Stellung, a, Stand a, b, Stand b) → Schnittvolumen

    # --- Specs ------------------------------------------------------------------------------------------------------
    def _baugruppe_spec(self, eigene: dict) -> dict:
        if self.ist_baugruppe:
            return dict(self.spec, parameter={**self.spec.get("parameter", {}), **eigene})
        kid = Path(self.datei).stem
        return {"art": "baugruppe", "name": self.spec["name"],
                "komponenten": [{"id": kid, "quelle": {"teil": self.datei}, "fixiert": True}], "verknuepfungen": []}

    def _teilspec(self, datei: str) -> dict:
        return yaml.safe_load((self.specs / datei).read_text(encoding="utf-8"))

    def _validieren(self, je: dict) -> list[str]:
        out = []
        for datei, werte in je.items():
            if datei == self.datei and self.ist_baugruppe:
                spec = dict(self.spec, parameter={**self.spec.get("parameter", {}), **werte})
                b = schema_befunde(spec, "baugruppe")
            else:
                roh = self._teilspec(datei)
                spec = dict(roh, parameter={**roh.get("parameter", {}), **werte})
                b = schema_befunde(spec) or plausibel_befunde(spec, self.specs)
            out += [f"{datei}: {x['pfad']}: {x['meldung']}" for x in b]
        return out

    # --- Bau --------------------------------------------------------------------------------------------------------
    def baue(self, werte: dict, genauigkeit: dict | None = None, mit_daten: bool = True) -> Geometrie:
        t0 = time.perf_counter()
        g = Geometrie(dict(werte))
        je = je_datei(self.a.stellschrauben, werte)
        g.befunde = self._validieren(je)
        if g.befunde:
            g.zeiten["stufe0_s"] = round(time.perf_counter() - t0, 3)
            return g
        teil_werte = {d: w for d, w in je.items() if not (d == self.datei and self.ist_baugruppe)}
        eigene = je.get(self.datei, {}) if self.ist_baugruppe else {}
        try:
            bg = Baugruppe(self._baugruppe_spec(eigene), self.specs, parameter=teil_werte,
                           bohrungen=self.sim.get("bohrungen", False))
        except SchnellbauFehler as e:
            g.befunde = [f"Schnellbau: {e}"]
            g.zeiten["stufe0_s"] = round(time.perf_counter() - t0, 3)
            return g
        g.bg = bg
        g.zeiten["schnellbau_s"] = round(time.perf_counter() - t0, 3)
        if not self.kollision.get("aus"):
            g.kollisionen = self._kollisionen(bg, je)
        g.bauraum = self._bauraum(bg)
        g.zeiten["stufe0_s"] = round(time.perf_counter() - t0, 3)
        if g.gueltig and mit_daten:
            t1 = time.perf_counter()
            g.daten = self._daten(bg, je, werte, genauigkeit or {})
            g.zeiten["zerlegung_s"] = round(time.perf_counter() - t1, 3)
        return g

    # --- Stellungen -------------------------------------------------------------------------------------------------
    def _bewegt(self, bg: Baugruppe, koerper: str) -> set:
        """Körper und alle an ihm hängenden Körper."""
        out, neu = {koerper}, True
        while neu:
            neu = False
            for gl in bg.gelenke:
                if gl.eltern in out and gl.komponente not in out:
                    out.add(gl.komponente)
                    neu = True
        return out

    def stellungen(self, bg: Baugruppe) -> list[tuple[str, dict, set]]:
        """[(Name, {Komponente: Solid}, bewegte Komponenten)] Grundstellung und jede Gelenk-Endstellung (übrige Gelenke
        in Grundstellung)."""
        solids = bg.solids()
        out = [("grund", solids, set(solids))]
        for gl in bg.gelenke:
            if gl.bereich is None:
                continue
            koerper = self._bewegt(bg, gl.komponente)
            for wert in gl.bereich:
                if abs(wert) < 1e-12:
                    continue
                if gl.typ == "schub":
                    loc = Location(tuple(float(c) * wert for c in gl.achse))
                    bewegt = {k: s.moved(loc) for k, s in solids.items() if bg.komp[k].koerper in koerper}
                else:
                    ax = Axis(tuple(float(c) for c in gl.punkt), tuple(float(c) for c in gl.achse))
                    bewegt = {k: s.rotate(ax, float(np.degrees(wert))) for k, s in solids.items()
                              if bg.komp[k].koerper in koerper}
                einheit = "mm" if gl.typ == "schub" else "°"
                w = wert if gl.typ == "schub" else float(np.degrees(wert))
                out.append((f"{gl.id}={w:g}{einheit}", {**solids, **bewegt}, set(bewegt)))
        return out

    @staticmethod
    def _schnitt(a, b) -> float:
        ba, bb = a.bounding_box(), b.bounding_box()
        if (ba.max.X < bb.min.X or bb.max.X < ba.min.X or ba.max.Y < bb.min.Y or bb.max.Y < ba.min.Y
                or ba.max.Z < bb.min.Z or bb.max.Z < ba.min.Z):
            return 0.0
        s = a & b
        return 0.0 if s is None else float(sum(x.volume for x in s.solids()))

    def _schluessel(self, bg: Baugruppe, je: dict) -> dict[str, str]:
        """Stand je Komponente (Spec und Werte der Datei, Lage) – gleiche Paare werden nicht neu geschnitten."""
        return {kid: _sha({"spec": self._teilspec(k.datei), "werte": je.get(k.datei, {}), "t": k.t})
                for kid, k in bg.komp.items()}

    def _kollisionen(self, bg: Baugruppe, je: dict) -> list[dict]:
        ids = sorted(bg.komp)
        stand = self._schluessel(bg, je)

        def schnitt(name, solids, a, b) -> float:
            k = (name, a, stand[a], b, stand[b])
            if k not in self._paare:
                self._paare[k] = self._schnitt(solids[a], solids[b])
            return self._paare[k]

        stellungen = self.stellungen(bg)
        if self.grund_paare is None:            # Ausgangsstand = erste gebaute Probe (Startpunkt der Studie)
            self.grund_paare = set()
            name, solids, _ = stellungen[0]
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    v = schnitt(name, solids, a, b)
                    if v > self.toleranz:
                        self.grund_paare.add(frozenset((a, b)))
                        self.grund_meldung.append({"a": a, "b": b, "mm3": round(v, 3)})
        out = []
        for name, solids, bewegt in stellungen:
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    paar = frozenset((a, b))
                    if paar in self.ausnehmen or paar in self.grund_paare:
                        continue
                    if name != "grund" and (a in bewegt) == (b in bewegt):
                        continue                # beide fest oder gemeinsam bewegt: wie in der Grundstellung
                    v = schnitt(name, solids, a, b)
                    if v > self.toleranz:
                        out.append({"stellung": name, "a": a, "b": b, "mm3": round(v, 3)})
        return out

    def _bauraum(self, bg: Baugruppe) -> list[str]:
        raum = self.a.block.get("nebenbedingungen", {}).get("bauraum")
        if not raum:
            return []
        lo, hi = np.array(raum["min"], float), np.array(raum["max"], float)
        out = []
        for name, solids, _ in self.stellungen(bg):
            for k, s in solids.items():
                bb = s.bounding_box()
                a, b = np.array([bb.min.X, bb.min.Y, bb.min.Z]), np.array([bb.max.X, bb.max.Y, bb.max.Z])
                if np.any(a < lo - 1e-6) or np.any(b > hi + 1e-6):
                    out.append(f"{k} ({name}): {np.round(a, 2).tolist()} … {np.round(b, 2).tolist()} außerhalb")
        return out

    # --- Daten für die Arbeitsprozesse --------------------------------------------------------------------------
    def _stuecke(self, bg: Baugruppe, kid: str, je: dict, tol: float) -> list[np.ndarray]:
        k = bg.komp[kid]
        schluessel = _sha({"spec": self._teilspec(k.datei), "werte": je.get(k.datei, {}), "tol": tol,
                           "bohrungen": self.sim.get("bohrungen", False)})
        pfad = self.cache / f"{Path(k.datei).stem}_{schluessel}.pkl"
        if pfad.exists():
            self.zerlegungen["cache"] += 1
            punkte = pickle.loads(pfad.read_bytes())
        else:
            self.zerlegungen["neu"] += 1
            punkte = [s.punkte for s in zerlege(k.teil.solid, tol)]
            pfad.write_bytes(pickle.dumps(punkte))
        t = np.array(k.t, float)
        return [p + t for p in punkte]

    def _daten(self, bg: Baugruppe, je: dict, werte: dict, genauigkeit: dict) -> dict:
        tol = self.sim.get("zerlegung_toleranz_mm", 0.01)
        komponenten = list(self.sim.get("komponenten") or bg.komp)
        stuecke = {kid: [np.round(p, 6).tolist() for p in self._stuecke(bg, kid, je, tol)]
                   for kid in komponenten if kid in bg.komp}
        parameter = {k.datei: {n: float(v) for n, v in k.teil.parameter.items()} for k in bg.komp.values()}
        if self.ist_baugruppe:
            parameter[self.datei] = {n: float(v) for n, v in bg.p.items()}
        return {"werte": werte, "stuecke": stuecke,
                "koerper": {kid: bg.komp[kid].koerper or "welt" for kid in bg.komp},
                "lage": {kid: list(map(float, bg.komp[kid].t)) for kid in bg.komp},
                "gelenke": [{"id": gl.id, "typ": gl.typ, "komponente": gl.komponente, "eltern": gl.eltern,
                             "achse": [float(c) for c in gl.achse], "punkt": [float(c) for c in gl.punkt],
                             "bereich": None if gl.bereich is None else list(gl.bereich)} for gl in bg.gelenke],
                "parameter": parameter, "genauigkeit": dict(genauigkeit),
                "simulation": copy.deepcopy(self.sim), "meldungen": list(bg.meldungen)}

    def mjcf(self, g: Geometrie) -> str:
        """MJCF der Probe über swki.schnellbau.mjcf (für Prüfaufgaben mit MJCF = True), Genauigkeit eingerechnet."""
        from swki.schnellbau.mjcf import erzeuge
        sim = dict(self.sim)
        f = g.daten.get("genauigkeit", {}) if g.daten else {}
        sim["zeitschritt_s"] = sim.get("zeitschritt_s", 2e-5) * f.get("zeitschritt_faktor", 1.0)
        sim["kontakt_zeitkonstante_s"] = sim.get("kontakt_zeitkonstante_s", 3e-4) * f.get("kontakt_faktor", 1.0)
        return erzeuge(g.bg, sim, self.specs).xml
