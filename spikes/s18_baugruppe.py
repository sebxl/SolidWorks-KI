"""S18: Baugruppen-Spec → Simulationsgeometrie (Schnellbau, Lage, Gelenke, konvexe Stücke in Maschinenkoordinaten).

Lage: nur Verschiebungen (Prüfstation AP 6.8: alle Eigenteile in Maschinenkoordinaten modelliert, Skelett-Prinzip).
Gleichungen je Verknüpfung, sobald eine Seite liegt:
  deckungsgleich (Standardebene oder Fläche)  Lage_a + t_a[i] = Lage_b + t_b[i] auf der Normalenachse i
  konzentrisch (Bohrungsachse, Instanz)       Achspunkte gleich auf den beiden Achsen quer zur Bohrung
  parallel                                    keine Verschiebung (Richtung wird nicht gedreht)
Freie Achsen nach allen Gleichungen (z. B. die Hubachse an einer Grenze zu einem Kaufteil) bleiben 0 = modellierte
Grundstellung; das wird gemeldet. Kaufteil-Referenzen (EINBAU_*) werden nicht gelöst.
Gelenke: grenze_abstand → Schubgelenk entlang −Normale der Fläche a (Abstand wächst), Bereich max − min; die
Komponenten einer gruppe fahren mit (wie swki.baugruppe).

Teilkoordinaten (x, y, z) → Maschine (X, Y, Z) = (x, −z, y) (Baugruppe z = −Maschine Y, pruefstation.yaml Kopf).
Längen in mm.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from spikes.s18_schnellbau import Schnellbau, lade
from spikes.s18_zerlegung import bericht, zerlege
from swki.compiler.skizze import NORMALE
from swki.spec.ausdruck import auswerten

ACHSE = {"rechts": 0, "oben": 1, "vorne": 2}


def maschine(p: np.ndarray) -> np.ndarray:
    """Teil-/Baugruppenkoordinaten → Maschinenkoordinaten."""
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1)


@dataclass
class Komponente:
    id: str
    spec_datei: str
    bau: Schnellbau
    t: list = field(default_factory=lambda: [None, None, None])


class Baugruppe:
    def __init__(self, ordner: Path, spec_datei: str, komponenten: list[str], parameter: dict | None = None,
                 freigegeben: bool = True, ohne: dict | None = None):
        """parameter: {teil-spec-datei: {NAME: wert}}; ohne: {teil-spec-datei: [feature-id, …]} – Topologie-Variante
        (Features weggelassen) einer Spec, wie sie die äußere Schleife erzeugt."""
        self.ordner = Path(ordner)
        self.spec = lade(self.ordner / self._datei(spec_datei, freigegeben))
        self.p = {k: auswerten(v, self.spec.get("parameter", {})) for k, v in self.spec.get("parameter", {}).items()}
        self.parameter = parameter or {}          # {teil-spec-datei: {NAME: wert}}
        self.freigegeben = freigegeben
        quellen = {k["id"]: k for k in self.spec["komponenten"]}
        self.gruppen = {k["id"]: k.get("gruppe") for k in self.spec["komponenten"]}
        self.komp: dict[str, Komponente] = {}
        self.zeiten = {}
        for kid in komponenten:
            q = quellen[kid]["quelle"]
            if "teil" not in q:
                raise ValueError(f"{kid}: nur Eigenteile ({q})")
            datei = q["teil"]
            spec = lade(self.ordner / self._datei(datei, freigegeben))
            if datei in (ohne or {}):
                spec = dict(spec, features=[f for f in spec["features"] if f["id"] not in ohne[datei]])
            t0 = time.perf_counter()
            bau = Schnellbau(spec, self.parameter.get(datei), name=kid, bohrungen=False)
            bau.teil = bau.baue()
            self.zeiten[kid] = time.perf_counter() - t0
            self.komp[kid] = Komponente(kid, datei, bau)
        if quellen_fix := [k["id"] for k in self.spec["komponenten"] if k.get("fixiert")]:
            self.fix = quellen_fix[0]
        self.meldungen: list[str] = []

    @staticmethod
    def _datei(datei: str, freigegeben: bool) -> str:
        return datei.replace(".yaml", ".freigegeben.yaml") if freigegeben else datei

    # --- Lage --------------------------------------------------------------------------------------------------
    def _seite(self, s: dict):
        """('ebene', achse, lage) | ('achse', punkt, richtung) | None (nicht lösbar hier)."""
        kid = s["komponente"]
        if kid == self.fix:
            if "ebene" in s:
                return ("ebene", ACHSE[s["ebene"]], 0.0)
            return None
        if kid not in self.komp:
            return None
        bau = self.komp[kid].bau
        if "ebene" in s:
            return ("ebene", ACHSE[s["ebene"]], 0.0)
        if "flaeche" in s and "feature" in s and "instanz" not in s:
            e = bau.flaechenebene({"feature": s["feature"], "flaeche": s["flaeche"]})
            return ("ebene", ACHSE[e.orientierung], e.lage)
        if s.get("achse") and "feature" in s:
            info = bau.features[s["feature"]]
            inst = s.get("instanz", 1)
            if inst == "je" or info.punkte is None:
                return None
            p = info.punkte[inst - 1]
            return ("achse", (p.X, p.Y, p.Z), info.richtung)
        return None

    def _t(self, kid: str):
        return [0.0, 0.0, 0.0] if kid == self.fix else self.komp[kid].t

    def loese_lage(self) -> None:
        glg = []   # (komp_a, komp_b, achse, c): t_a[i] - t_b[i] = c
        for v in self.spec["verknuepfungen"]:
            if v["typ"] not in ("deckungsgleich", "konzentrisch"):
                continue
            a, b = v["a"], v["b"]
            if not all(x["komponente"] in self.komp or x["komponente"] == self.fix for x in (a, b)):
                continue
            sa, sb = self._seite(a), self._seite(b)
            if sa is None or sb is None or sa[0] != sb[0]:
                self.meldungen.append(f"{v['id']}: nicht gelöst ({a.get('referenz') or a.get('feature')} / "
                                      f"{b.get('referenz') or b.get('feature')})")
                continue
            if sa[0] == "ebene":
                if sa[1] != sb[1]:
                    raise ValueError(f"{v['id']}: Ebenen nicht parallel")
                glg.append((a["komponente"], b["komponente"], sa[1], sb[2] - sa[2]))
            else:
                d = [abs(c) for c in sa[2]]
                ax = int(np.argmax(d))
                for i in range(3):
                    if i != ax:
                        glg.append((a["komponente"], b["komponente"], i, sb[1][i] - sa[1][i]))
        for _ in range(len(self.komp) + 2):
            for ka, kb, i, c in glg:
                ta, tb = self._t(ka), self._t(kb)
                if tb[i] is not None and ta[i] is None:
                    ta[i] = tb[i] + c
                elif ta[i] is not None and tb[i] is None:
                    tb[i] = ta[i] - c
                elif ta[i] is not None and abs(ta[i] - tb[i] - c) > 1e-6:
                    raise ValueError(f"Widerspruch {ka}/{kb} Achse {i}: {ta[i] - tb[i]:.6f} statt {c:.6f}")
        for k in self.komp.values():
            for i in range(3):
                if k.t[i] is None:
                    k.t[i] = 0.0
                    self.meldungen.append(f"{k.id}: Achse {'xyz'[i]} frei → 0 (modellierte Grundstellung)")

    # --- Gelenke -----------------------------------------------------------------------------------------------
    def gelenke(self) -> list[dict]:
        out = []
        for v in self.spec["verknuepfungen"]:
            if v["typ"] != "grenze_abstand":
                continue
            a = v["a"]
            if a["komponente"] not in self.komp:
                continue
            bau = self.komp[a["komponente"]].bau
            e = bau.flaechenebene({"feature": a["feature"], "flaeche": a["flaeche"]})
            achse_teil = -np.array(e.normale, float)
            achse_m = maschine(achse_teil[None, :])[0]
            lo, hi = auswerten(v["min"], self.p), auswerten(v["max"], self.p)
            gruppe = self.gruppen.get(a["komponente"])
            mit = [k for k in self.komp if k == a["komponente"] or (gruppe and self.gruppen.get(k) == gruppe)]
            out.append(dict(id=v["id"], komponenten=mit, achse_maschine=[round(float(c), 9) for c in achse_m],
                            hub=hi - lo, min=lo, max=hi))
        return out

    # --- Kollisionsgeometrie -----------------------------------------------------------------------------------
    def stuecke(self, toleranz: float = 0.01, cache: Path | None = None, nur: list | None = None) -> dict:
        """{komponente: [Eckpunktlisten in Maschinenkoordinaten (mm)]} und Zerlegungsbericht je Komponente."""
        out, berichte, zeiten = {}, {}, {}
        for k in self.komp.values():
            if nur is not None and k.id not in nur:
                continue
            solid = k.bau.teil.solid
            schl = hashlib.sha1(json.dumps([k.spec_datei, sorted(k.bau.p.items()), [f["id"] for f in k.bau.spec["features"]],
                                            toleranz]).encode()).hexdigest()[:16]
            datei = cache / f"{k.spec_datei}.{schl}.npz" if cache else None
            t0 = time.perf_counter()
            if datei and datei.exists():
                z = np.load(datei, allow_pickle=True)
                pts, ber = list(z["punkte"]), json.loads(str(z["bericht"]))
            else:
                st = zerlege(solid, toleranz)
                pts, ber = [s.punkte for s in st], bericht(solid, st)
                if datei:
                    datei.parent.mkdir(parents=True, exist_ok=True)
                    arr = np.empty(len(pts), dtype=object)
                    arr[:] = pts
                    np.savez(datei, punkte=arr, bericht=json.dumps(ber))
            zeiten[k.id] = time.perf_counter() - t0
            t = np.array(k.t, float)
            out[k.id] = [maschine(p + t) for p in pts]
            berichte[k.id] = ber
        return dict(stuecke=out, berichte=berichte, zeiten=zeiten)


def lade_sim(pfad: Path) -> dict:
    return yaml.safe_load(Path(pfad).read_text(encoding="utf-8"))
