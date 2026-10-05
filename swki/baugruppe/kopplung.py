"""Kopplungen über Verzahnungen (Spec 4b §5) ohne SolidWorks: Kopplungsgraph, abgeleitete Übersetzung, Zahnphase,
Eingriff und die Drehung einer Komponente um ihre Achse.

Lagen in Baugruppenkoordinaten (mm) aus der Teil-Lage (swki.verzahnung.Verzahnung) und Transform2.ArrayData
(Zeilenvektor-Konvention wie swki.baugruppe.geometrie.transformiere, Verschiebung in m)."""

import math
from dataclasses import dataclass

from swki.baugruppe.geometrie import drehmatrix
from swki.compiler.anker import differenz, skalar
from swki.spec.ausdruck import auswerten
from swki.verbindung import in_mm, mm
from swki.verzahnung import Stirnrad, Verzahnung, Zahnstange, verzahnung_im_teil

KOPPLUNGEN = ("zahnrad", "zahnstange")
GEKOPPELT = "gekoppelt"
_PARALLEL = 1.0 - 1e-6

Vektor = tuple[float, float, float]


def _kreuz(a: Vektor, b: Vektor) -> Vektor:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _einheit(a: Vektor) -> Vektor:
    n = math.sqrt(skalar(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def _senkrecht(a: Vektor, n: Vektor) -> Vektor:
    """Anteil von a senkrecht zur Einheitsrichtung n."""
    t = skalar(a, n)
    return (a[0] - t * n[0], a[1] - t * n[1], a[2] - t * n[2])


def winkel_um(a: Vektor, b: Vektor, n: Vektor) -> float:
    """Vorzeichenbehafteter Winkel (rad) von a nach b um die Einheitsachse n (Rechte-Hand-Regel)."""
    a, b = _senkrecht(a, n), _senkrecht(b, n)
    return math.atan2(skalar(n, _kreuz(a, b)), skalar(a, b))


def _bruch(x: float) -> float:
    """Anteil in [0, 1)."""
    return x - math.floor(x)


def _gefaltet(x: float) -> float:
    """Anteil in (−0,5; 0,5]."""
    x = _bruch(x)
    return x - 1.0 if x > 0.5 else x


# --- Lage in der Baugruppe -----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Rad:
    """Stirnrad in Baugruppenkoordinaten."""
    punkt: Vektor     # Punkt auf der Radachse (mm)
    achse: Vektor     # Einheitsrichtung (Normale der Skizzenebene)
    zahn: Vektor      # Einheitsrichtung von der Achse zur Mitte von Zahn 1
    geo: Stirnrad
    breite: tuple[float, float]  # Bereich entlang achse (Skalarprodukt mit achse, mm)


@dataclass(frozen=True)
class Stange:
    """Zahnstange in Baugruppenkoordinaten."""
    punkt: Vektor     # Mitte von Zahn 1 auf der Profilmittellinie (mm)
    reihe: Vektor     # Einheitsrichtung der Zahnreihe
    kopf: Vektor      # Einheitsrichtung der Zähne
    achse: Vektor     # Breitenrichtung (Normale der Skizzenebene)
    geo: Zahnstange
    breite: tuple[float, float]


def _punkt(p: Vektor, t) -> Vektor:
    return tuple(p[0] * t[i] + p[1] * t[3 + i] + p[2] * t[6 + i] + in_mm(t[9 + i]) for i in range(3))


def _richtung(v: Vektor, t) -> Vektor:
    return _einheit(tuple(v[0] * t[i] + v[1] * t[3 + i] + v[2] * t[6 + i] for i in range(3)))


def in_baugruppe(vz: Verzahnung, t) -> Rad | Stange:
    """Verzahnung (Teilkoordinaten) mit der Lage t der Komponente in Baugruppenkoordinaten."""
    achse = _richtung(vz.normale, t)
    versatz = skalar(tuple(in_mm(t[9 + i]) for i in range(3)), achse)  # Drehung erhält Skalarprodukte, die Verschiebung nicht
    breite = (vz.breite[0] + versatz, vz.breite[1] + versatz)
    if isinstance(vz.geo, Stirnrad):
        return Rad(_punkt(vz.bezugspunkt, t), achse, _richtung(vz.zahnrichtung, t), vz.geo, breite)
    return Stange(_punkt(vz.bezugspunkt, t), _richtung(vz.zahnrichtung, t), _richtung(vz.kopfrichtung, t), achse, vz.geo,
                  breite)


def verzahnung_der_seite(quellen: dict, seite: dict) -> Verzahnung:
    """Verzahnung, auf die eine Kopplungsseite {komponente, feature} zeigt (Teil-Spec der Quelle)."""
    from swki.baugruppe.aufloesen import basis

    spec = quellen[basis(seite["komponente"])].spec
    f = next(x for x in spec["features"] if x["id"] == seite["feature"])
    return verzahnung_im_teil(f, spec.get("parameter", {}))


# --- Übersetzung ---------------------------------------------------------------------------------------------------


def teilkreise(a: Stirnrad, b: Stirnrad | Zahnstange) -> tuple[float, float]:
    """Zähler/Nenner der Zahnradverknüpfung (Teilkreis-Ø in mm, wie IGearMateFeatureData) bzw. (Teilkreis-Ø des Ritzels,
    0) bei der Zahnstange."""
    return (a.m * a.z, b.m * b.z) if isinstance(b, Stirnrad) else (a.m * a.z, 0.0)


# --- Zahnphase -----------------------------------------------------------------------------------------------------


def phasenfehler(a: Rad, b: Rad | Stange) -> float:
    """Phasenfehler von a gegenüber b als Anteil der Teilung von a in (−0,5; 0,5] (0 = Zahn in Lücke, Spec 4b §5.4).

    Zahnrad: fa + fb ≡ 0,5 mit fa = Lage der Zahnmitte von a zur Mittenlinie a→b und fb = Lage von b zur Gegenrichtung,
    beide um a.achse gemessen. Zahnstange: fa − σ·fr ≡ 0,5 mit fr = Lage der Zahnstange am Wälzpunkt (Teilung) und
    σ = (achse × e)·reihe (Abrollsinn); e zeigt von der Radachse zum Wälzpunkt."""
    n, tau_a = a.achse, 2 * math.pi / a.geo.z
    if isinstance(b, Rad):
        e = _einheit(_senkrecht(differenz(b.punkt, a.punkt), n))
        fa = _bruch(winkel_um(a.zahn, e, n) / tau_a)
        fb = _bruch(winkel_um(b.zahn, (-e[0], -e[1], -e[2]), n) / (2 * math.pi / b.geo.z))
        return _gefaltet(fa - (0.5 - fb))
    w = tuple(b.punkt[i] + b.reihe[i] * skalar(differenz(a.punkt, b.punkt), b.reihe) for i in range(3))
    e = _einheit(_senkrecht(differenz(w, a.punkt), n))
    fr = _bruch(skalar(differenz(w, b.punkt), b.reihe) / b.geo.p)
    sigma = 1.0 if skalar(_kreuz(n, e), b.reihe) > 0 else -1.0
    fa = _bruch(winkel_um(a.zahn, e, n) / tau_a)
    return _gefaltet(fa - (0.5 + sigma * fr))


def phasenwinkel(a: Rad, b: Rad | Stange) -> float:
    """Drehung von a um a.achse in Grad (Rechte-Hand-Regel), die den Phasenfehler aufhebt."""
    return phasenfehler(a, b) * 360.0 / a.geo.z


def drehe(t, punkt: Vektor, achse: Vektor, winkel: float) -> list[float]:
    """Transform2.ArrayData nach einer Drehung der Komponente um die Achse (punkt in mm, achse) um winkel Grad."""
    q = drehmatrix(achse, winkel)
    c = [[t[3 * j + i] for j in range(3)] for i in range(3)]
    neu_c = [[sum(q[i][k] * c[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    v = [in_mm(t[9 + i]) - punkt[i] for i in range(3)]
    neu_v = [sum(q[i][k] * v[k] for k in range(3)) + punkt[i] for i in range(3)]
    return [neu_c[k % 3][k // 3] for k in range(9)] + [mm(x) for x in neu_v] + list(t[12:16])


# --- Eingriff ------------------------------------------------------------------------------------------------------


def _ueberdeckung(a: tuple[float, float], b: tuple[float, float], gleichsinnig: bool) -> float:
    """Länge der Überdeckung zweier Bereiche entlang derselben Achse (b ggf. gespiegelt)."""
    b = b if gleichsinnig else (-b[1], -b[0])
    return min(a[1], b[1]) - max(a[0], b[0])


def eingriff(a: Rad, b: Rad | Stange) -> dict:
    """Ist-Werte des Eingriffs (Spec 4b §5.5): parallel/senkrecht, Abstand, Soll, Breitenüberdeckung, im_bereich."""
    if isinstance(b, Rad):
        cos = skalar(a.achse, b.achse)
        d = _senkrecht(differenz(b.punkt, a.punkt), a.achse)
        abstand = math.sqrt(skalar(d, d))
        return {"achsen_parallel": abs(cos) > _PARALLEL, "achsabstand": round(abstand, 6),
                "soll": round(a.geo.m * (a.geo.z + b.geo.z) / 2, 6),
                "ueberdeckung": round(_ueberdeckung(a.breite, b.breite, cos > 0), 6), "im_bereich": True}
    senkrecht = abs(skalar(a.achse, b.reihe)) < 1e-6 and abs(skalar(a.achse, b.kopf)) < 1e-6
    lage = skalar(differenz(a.punkt, b.punkt), b.reihe)
    return {"achsen_parallel": senkrecht, "achsabstand": round(skalar(differenz(a.punkt, b.punkt), b.kopf), 6),
            "soll": round(a.geo.r, 6), "ueberdeckung": round(_ueberdeckung(a.breite, b.breite, skalar(a.achse, b.achse) > 0), 6),
            "im_bereich": -b.geo.p / 2 <= lage <= (b.geo.z - 0.5) * b.geo.p}


# --- Kopplungsgraph ------------------------------------------------------------------------------------------------


def kopplungen(spec: dict) -> list[dict]:
    return [v for v in spec.get("verknuepfungen", []) if v["typ"] in KOPPLUNGEN]


def mitglieder(spec: dict, name: str) -> set[str]:
    """Komponente bzw. alle Mitglieder der Gruppe name."""
    gruppe = {k["id"] for k in spec["komponenten"] if k.get("gruppe") == name}
    return gruppe or {name}


def antriebsmenge(spec: dict, kid: str) -> set[str]:
    """Bewegte Komponente einer Bewegung samt ihrer Gruppe, wenn die Gruppe den Freiheitsgrad trägt."""
    gruppe = next((k.get("gruppe") for k in spec["komponenten"] if k["id"] == kid), None)
    return mitglieder(spec, gruppe) if gruppe and spec.get("freiheitsgrade", {}).get(gruppe) == 1 else {kid}


def gekoppelte(spec: dict, start: set[str]) -> list[str]:
    """Komponenten mit freiheitsgrade: gekoppelt, die über Kopplungen von start aus erreichbar sind (Spec-Reihenfolge der
    Komponenten). Weitergereicht wird nur über gekoppelte Komponenten."""
    fg = spec.get("freiheitsgrade", {})
    erreicht, neu = set(start), set(start)
    while neu:
        weiter = set()
        for v in kopplungen(spec):
            ka, kb = v["a"]["komponente"], v["b"]["komponente"]
            for von, nach in ((ka, kb), (kb, ka)):
                if von in neu and nach not in erreicht and fg.get(nach) == GEKOPPELT:
                    weiter.add(nach)
        erreicht |= weiter
        neu = weiter
    return [k["id"] for k in spec["komponenten"] if k["id"] in erreicht - set(start)]


def soll_drehungen(spec: dict, quellen: dict, bewegt: set[str], art: str, bereich: float,
                   wege: dict[str, float]) -> dict[str, float]:
    """Betrag der Drehung (Grad) jeder über Kopplungen getriebenen Komponente für eine Bewegung (Spec 4b §5.2,
    UEBERSETZUNG_WIDERSPRUCH). bewegt: Mitglieder der bewegten Komponente bzw. Gruppe; art/bereich der Bewegung
    (Abstand mm bzw. Winkel Grad); wege: Betrag der Endlage-Verschiebung je Komponente (mm, für Zahnstangen außerhalb
    der bewegten Menge)."""
    drehung = {k: bereich for k in bewegt} if art == "winkel" else {}
    weg = {k: bereich for k in bewegt} if art == "abstand" else {}
    weg |= {k: w for k, w in wege.items() if k not in weg}
    geaendert = True
    while geaendert:
        geaendert = False
        for v in kopplungen(spec):
            ka, kb = v["a"]["komponente"], v["b"]["komponente"]
            a = verzahnung_der_seite(quellen, v["a"]).geo
            b = verzahnung_der_seite(quellen, v["b"]).geo
            if v["typ"] == "zahnstange":
                if ka not in drehung and kb in weg:
                    drehung[ka] = weg[kb] * 360.0 / (math.pi * a.m * a.z)
                    geaendert = True
            else:
                for x, gx, y, gy in ((ka, a, kb, b), (kb, b, ka, a)):
                    if x in drehung and y not in drehung:
                        drehung[y] = drehung[x] * gx.z / gy.z
                        geaendert = True
    return {k: w for k, w in drehung.items() if k not in bewegt}


def endlagen_wege(bewegung: dict, p: dict) -> dict[str, float]:
    """Betrag der erwarteten Verschiebung je Komponente aus erwartet.endlagen (mm)."""
    ergebnis = {}
    for e in bewegung.get("erwartet", {}).get("endlagen", []):
        if "verschiebung" in e:
            ergebnis[e["komponente"]] = math.sqrt(sum(auswerten(w, p) ** 2 for w in e["verschiebung"]))
    return ergebnis
