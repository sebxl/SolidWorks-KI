"""Baugruppen-Spec → Lage der Eigenteile, Körper und Gelenke ohne SolidWorks (Spec C1 §2).

Lage: nur Verschiebungen (Teile in gleicher Orientierung, wie in den Referenz-Baugruppen und der Prüfstation AP 6.8).
Gleichungen je Verknüpfung, sobald eine Seite liegt:
  deckungsgleich (Standardebene, Fläche, Bezugsebene)   Lage_a + t_a[i] = Lage_b + t_b[i]
  konzentrisch, scharnier (Bohrungs-, Rad-, Bezugsachse) Achspunkte gleich quer zur Achse; scharnier dazu die Anlage
  grenze_abstand                                         Grundstellung = min: Ebene a liegt um min in −n_a neben b
  parallel, grenze_winkel                                keine Verschiebung
Eine Verknüpfung, die eine Drehung verlangt (Normalen/Achsen nicht parallel oder Ausrichtung umgekehrt), ist
NICHT_UNTERSTUETZT. Normteile und Kaufteile werden nicht gebaut; eine Achse über ein Normteil (Hebel → Drehbolzen →
Schlitten) wird über dessen zweite konzentrische Verknüpfung weitergereicht. Freie Achsen bleiben 0 (modellierte Lage)
und werden gemeldet.

Körper: Gelenke aus grenze_abstand (Schub entlang −n_a, Bereich 0 … max − min) und scharnier (Dreh; Bereich aus
grenze_winkel derselben Komponente, Drehsinn aus bewegungen.erwartet, sonst unbegrenzt). Starr verbunden (deckungsgleich,
konzentrisch, parallel, gruppe) wird ein Teil Teil des Körpers seines Partners, solange nicht beide Seiten schon einen
eigenen Körper haben. Kopplungen (zahnrad, zahnstange) werden gemeldet, nicht übertragen.
Längen in mm, Winkel der Gelenkbereiche im Bogenmaß.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from swki.compiler.anker import RICHTUNGEN
from swki.compiler.skizze import NORMALE
from swki.schnellbau.fehler import ANKER, NICHT_UNTERSTUETZT, SchnellbauFehler
from swki.schnellbau.teil import Schnellbau, Teil, lade
from swki.spec.ausdruck import auswerten

ACHSE_DER = {"rechts": 0, "oben": 1, "vorne": 2}
STARR = ("deckungsgleich", "konzentrisch", "parallel")
KOPPLUNGEN = ("zahnrad", "zahnstange")
_PAR = 1 - 1e-6


@dataclass
class Gelenk:
    id: str
    typ: str                    # "schub" | "dreh"
    komponente: str             # Körper, der sich bewegt
    eltern: str | None          # Körper, an dem er hängt (None = Welt)
    achse: tuple                # Einheitsvektor (Baugruppe)
    punkt: tuple                # Punkt auf der Achse (Dreh), mm
    bereich: tuple | None       # (min, max) relativ zur Grundstellung, mm bzw. rad; None = unbegrenzt
    mates: list = field(default_factory=list)


@dataclass
class Komponente:
    id: str
    datei: str
    teil: Teil
    t: list = field(default_factory=lambda: [None, None, None])
    koerper: str | None = None  # Körper (Komponenten-ID mit Gelenk) oder None = Welt


@dataclass
class _Seite:
    komp: str
    art: str                    # "ebene" | "achse"
    achse_i: int | None = None  # ebene: Normalenachse
    lage: float = 0.0           # ebene: Koordinate
    normale: tuple | None = None
    punkt: tuple | None = None  # achse
    richtung: tuple | None = None


class Baugruppe:
    def __init__(self, spec: dict | Path, ordner: Path | None = None, parameter: dict | None = None,
                 ohne: dict | None = None, bohrungen: bool = False, freigegeben: bool = False,
                 nur: list | None = None):
        """spec: Baugruppen-Spec (dict oder Pfad); ordner: Auftragsordner der Teil-Specs (Standard: Ordner der Spec);
        parameter {teil-datei: {NAME: wert}}; ohne {teil-datei: [feature-id]}; freigegeben: *.freigegeben.yaml lesen;
        nur: nur diese Eigenteile bauen (und das fixierte), die übrigen wie Normteile übergehen (Simulation eines
        Ausschnitts; freie Achsen bleiben in der modellierten Lage)."""
        if not isinstance(spec, dict):
            ordner = ordner or Path(spec).parent
            spec = lade(spec)
        self.spec, self.ordner = spec, Path(ordner)
        self.p = {k: auswerten(v, spec.get("parameter", {})) for k, v in spec.get("parameter", {}).items()}
        self.quellen = {k["id"]: k for k in spec["komponenten"]}
        self.fix = next(k["id"] for k in spec["komponenten"] if k.get("fixiert"))
        self.meldungen: list[str] = []
        self.komp: dict[str, Komponente] = {}
        for k in spec["komponenten"]:
            q = k["quelle"]
            if "teil" not in q or (nur is not None and k["id"] not in nur and not k.get("fixiert")):
                continue
            datei = q["teil"]
            pfad = self.ordner / (datei.replace(".yaml", ".freigegeben.yaml") if freigegeben else datei)
            tspec = lade(pfad)
            if datei in (ohne or {}):
                tspec = dict(tspec, features=[f for f in tspec["features"] if f["id"] not in ohne[datei]])
            teil = Schnellbau(tspec, (parameter or {}).get(datei), bohrungen=bohrungen).baue()
            self.komp[k["id"]] = Komponente(k["id"], datei, teil)
        self.komp[self.fix].t = [0.0, 0.0, 0.0]
        self.nicht_gebaut = [k["id"] for k in spec["komponenten"] if k["id"] not in self.komp]
        self.gelenke: list[Gelenk] = []
        self._loese_lage()
        self._koerper_und_gelenke()

    # --- Seiten -------------------------------------------------------------------------------------------------
    def _ebene(self, kid: str, ebene) -> tuple:
        return ACHSE_DER[ebene], 0.0, NORMALE[ebene]

    def seite(self, s: dict) -> _Seite | None:
        """Seite einer Verknüpfung in Teilkoordinaten der Komponente; None, wenn sie hier nicht lösbar ist."""
        kid = s["komponente"]
        if kid not in self.komp:
            return None
        bau = self.komp[kid].teil.bau
        if "ebene" in s:
            i, lage, n = self._ebene(kid, s["ebene"])
            return _Seite(kid, "ebene", i, lage, n)
        if s.get("instanz") == "je":
            return None
        if "referenz" in s:
            info = self.komp[kid].teil.features.get(s["referenz"])
            if info is None or info.typ != "referenz":
                raise SchnellbauFehler(ANKER, f"{kid}: keine Referenz {s['referenz']!r}")
            if info.ebene is not None:
                e = info.ebene
                return _Seite(kid, "ebene", ACHSE_DER[e.orientierung], e.lage, e.normale)
            return _Seite(kid, "achse", punkt=info.punkte[0], richtung=info.richtung)
        if s.get("achse"):
            info = self.komp[kid].teil.features[s["feature"]]
            if not info.punkte:
                raise SchnellbauFehler(ANKER, f"{kid}.{s['feature']}: keine Achse")
            return _Seite(kid, "achse", punkt=info.punkte[s.get("instanz", 1) - 1], richtung=info.richtung)
        if "flaeche" in s:
            e = bau.flaechenebene({"feature": s["feature"], "flaeche": s["flaeche"]})
            return _Seite(kid, "ebene", ACHSE_DER[e.orientierung], e.lage, e.normale)
        return None

    def _achse_ueber_normteil(self, s: dict, mate_id: str) -> _Seite | None:
        """Achse eines nicht gebauten Teils (Normteil-Referenz) über seine konzentrische Verknüpfung zu einem Eigenteil."""
        nid = s["komponente"]
        for v in self.spec["verknuepfungen"]:
            if v["id"] == mate_id or v["typ"] not in ("konzentrisch", "scharnier"):
                continue
            for x, y in ((v["a"], v["b"]), (v["b"], v["a"])):
                if x["komponente"] == nid and x.get("referenz") == s.get("referenz") and y["komponente"] in self.komp:
                    gegen = self.seite(y)
                    if gegen is not None and gegen.art == "achse":
                        return gegen
        return None

    def _seite_mit_kette(self, s: dict, mate_id: str) -> _Seite | None:
        if s["komponente"] in self.komp:
            return self.seite(s)
        return self._achse_ueber_normteil(s, mate_id) if "referenz" in s else None

    # --- Lage ---------------------------------------------------------------------------------------------------
    def _gleichungen(self) -> list:
        g = []      # (komp_a, komp_b, achse i, c): t_a[i] − t_b[i] = c
        for v in self.spec["verknuepfungen"]:
            typ = v["typ"]
            if typ in KOPPLUNGEN:
                self.meldungen.append(f"{v['id']}: Kopplung {typ} nicht ins Modell übertragen")
                continue
            if typ in ("parallel", "grenze_winkel"):
                continue
            paare = [(v["a"], v["b"], typ)]
            if typ == "scharnier":
                paare = [(v["a"], v["b"], "konzentrisch"), (v["anlage_a"], v["anlage_b"], "anlage")]
            for a, b, art in paare:
                sa, sb = self._seite_mit_kette(a, v["id"]), self._seite_mit_kette(b, v["id"])
                if sa is None or sb is None:
                    if a["komponente"] in self.komp and b["komponente"] in self.komp:
                        self.meldungen.append(f"{v['id']}: nicht gelöst")
                    continue
                if sa.komp == sb.komp:
                    continue
                if sa.art != sb.art:
                    raise SchnellbauFehler(NICHT_UNTERSTUETZT, f"{v['id']}: Ebene gegen Achse")
                if sa.art == "ebene":
                    if sa.achse_i != sb.achse_i:
                        raise SchnellbauFehler(NICHT_UNTERSTUETZT, f"{v['id']}: Drehung nötig (Ebenen nicht parallel)")
                    abstand = 0.0
                    if typ == "grenze_abstand":
                        abstand = -sa.normale[sa.achse_i] * auswerten(v["min"], self.p)
                    g.append((sa.komp, sb.komp, sa.achse_i, sb.lage - sa.lage + abstand, v["id"]))
                else:
                    if abs(abs(float(np.dot(sa.richtung, sb.richtung))) - 1) > 1e-6:
                        raise SchnellbauFehler(NICHT_UNTERSTUETZT, f"{v['id']}: Drehung nötig (Achsen nicht parallel)")
                    ax = int(np.argmax(np.abs(sa.richtung)))
                    for i in range(3):
                        if i != ax:
                            g.append((sa.komp, sb.komp, i, sb.punkt[i] - sa.punkt[i], v["id"]))
        return g

    def _loese_lage(self) -> None:
        glg = self._gleichungen()
        for _ in range(len(self.komp) + 2):
            for ka, kb, i, c, vid in glg:
                ta, tb = self.komp[ka].t, self.komp[kb].t
                if tb[i] is not None and ta[i] is None:
                    ta[i] = tb[i] + c
                elif ta[i] is not None and tb[i] is None:
                    tb[i] = ta[i] - c
                elif ta[i] is not None and abs(ta[i] - tb[i] - c) > 1e-6:
                    raise SchnellbauFehler(NICHT_UNTERSTUETZT,
                                           f"{vid}: Widerspruch {ka}/{kb} Achse {'xyz'[i]} ({ta[i] - tb[i]:.6f} statt {c:.6f})")
        for k in self.komp.values():
            for i in range(3):
                if k.t[i] is None:
                    k.t[i] = 0.0
                    self.meldungen.append(f"{k.id}: Achse {'xyz'[i]} frei → 0 (modellierte Lage)")

    # --- Körper und Gelenke -------------------------------------------------------------------------------------
    def _erwartete_drehung(self, kid: str) -> tuple | None:
        for b in self.spec.get("bewegungen", []):
            for e in b.get("erwartet", {}).get("endlagen", []):
                if e["komponente"] == kid and "drehung" in e:
                    a = np.array([auswerten(c, self.p) for c in e["drehung"]["achse"]], float)
                    return tuple(a / np.linalg.norm(a))
        return None

    def _koerper_und_gelenke(self) -> None:
        anker = {self.fix: "welt"}
        roh = []
        for v in self.spec["verknuepfungen"]:
            if v["typ"] == "grenze_abstand" and v["a"]["komponente"] in self.komp:
                s = self.seite(v["a"])
                achse = tuple(-c for c in s.normale)
                lo, hi = auswerten(v["min"], self.p), auswerten(v["max"], self.p)
                roh.append(Gelenk(v["id"], "schub", s.komp, v["b"]["komponente"], achse, (0, 0, 0), (0.0, hi - lo),
                                  [v["id"]]))
            elif v["typ"] == "scharnier" and v["a"]["komponente"] in self.komp:
                s = self._seite_mit_kette(v["a"], v["id"])
                gegen = self._seite_mit_kette(v["b"], v["id"])
                kid = v["a"]["komponente"]
                achse = self._erwartete_drehung(kid) or tuple(float(c) for c in s.richtung)
                t = np.array(self.komp[kid].t)
                bereich = None
                for w in self.spec["verknuepfungen"]:
                    if w["typ"] == "grenze_winkel" and w["a"]["komponente"] == kid:
                        bereich = (0.0, math.radians(auswerten(w["max"], self.p) - auswerten(w["min"], self.p)))
                eltern = gegen.komp if gegen is not None else v["b"]["komponente"]
                roh.append(Gelenk(v["id"], "dreh", kid, eltern, achse, tuple(np.array(s.punkt) + t), bereich, [v["id"]]))
        for g in roh:
            anker[g.komponente] = g.komponente
        # starre Verbindungen: ein Teil ohne eigenen Körper geht in den Körper seines Partners
        for _ in range(len(self.komp) + 2):
            for v in self.spec["verknuepfungen"]:
                if v["typ"] not in STARR:
                    continue
                a, b = v["a"]["komponente"], v["b"]["komponente"]
                if a not in self.komp or b not in self.komp:
                    continue
                if a in anker and b not in anker:
                    anker[b] = anker[a]
                elif b in anker and a not in anker:
                    anker[a] = anker[b]
            for kid, q in self.quellen.items():
                if kid in self.komp and kid not in anker and q.get("gruppe"):
                    partner = [k for k, p in self.quellen.items() if p.get("gruppe") == q["gruppe"] and k in anker]
                    if partner:
                        anker[kid] = anker[partner[0]]
        for kid, k in self.komp.items():
            if kid not in anker:
                self.meldungen.append(f"{kid}: mit keinem Körper starr verbunden → Welt")
            k.koerper = None if anker.get(kid, "welt") == "welt" else anker[kid]
        for g in roh:
            eltern = self.komp[g.eltern].koerper if g.eltern in self.komp else None
            g.eltern = eltern
            self.gelenke.append(g)

    # --- Abfragen -----------------------------------------------------------------------------------------------
    def welt(self, s: _Seite) -> _Seite:
        """Seite in Baugruppenkoordinaten (Grundstellung)."""
        t = self.komp[s.komp].t
        if s.art == "ebene":
            return _Seite(s.komp, "ebene", s.achse_i, s.lage + t[s.achse_i], s.normale)
        return _Seite(s.komp, "achse", punkt=tuple(np.array(s.punkt) + np.array(t)), richtung=s.richtung)

    def abstand(self, von: dict, zu: dict) -> float:
        """Abstand zweier Seiten wie masse_pruefen: Ebene–Ebene entlang der Normalen, Achse–Achse, Ebene–Achse (mm)."""
        a, b = self.welt(self.seite(von)), self.welt(self.seite(zu))
        if a.art == "ebene" and b.art == "ebene":
            return abs(a.lage - b.lage)
        if a.art == "achse" and b.art == "achse":
            d = np.array(b.punkt) - np.array(a.punkt)
            r = np.array(a.richtung)
            return float(np.linalg.norm(d - np.dot(d, r) * r))
        e, x = (a, b) if a.art == "ebene" else (b, a)
        return abs(x.punkt[e.achse_i] - e.lage)

    def solids(self) -> dict:
        """{komponente: Solid in Baugruppenkoordinaten (Grundstellung)}."""
        from build123d import Location
        return {kid: k.teil.solid.moved(Location(tuple(k.t))) for kid, k in self.komp.items()}
