"""Auswahl von Flächen und Kanten ohne Namen (reine Geometrie, ohne SolidWorks).

Die Kandidaten (Flaeche, Kante) liefert swki.compiler.topologie aus SolidWorks; alle Längen in mm.
"""

import math
from dataclasses import dataclass

from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN, BauFehler

Vektor = tuple[float, float, float]

RICHTUNGEN: dict[str, Vektor] = {
    "+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0),
    "+y": (0.0, 1.0, 0.0), "-y": (0.0, -1.0, 0.0),
    "+z": (0.0, 0.0, 1.0), "-z": (0.0, 0.0, -1.0),
}
ACHSEN: dict[str, Vektor] = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
_PARALLEL = 1.0 - 1e-6  # |cos| ab dem zwei Richtungen als parallel gelten
_GLEICH_MM = 1e-4       # Lageunterschied, unterhalb dessen zwei Kandidaten gleich weit liegen


class AnkerFehler(BauFehler):
    pass


@dataclass
class Flaeche:
    art: str  # "ebene" | "zylinder" | "sonstige"
    punkt: Vektor  # Ebene: Punkt auf der Fläche; Zylinder: Punkt auf der Achse
    normale: Vektor | None = None  # Ebene: Einheitsnormale, aus dem Material heraus
    achse: Vektor | None = None  # Zylinder: Einheitsrichtung der Achse
    radius: float | None = None
    abstand: float | None = None  # Abstand zu einem Anker-Punkt (von topologie gesetzt)
    objekt: object = None  # IFace2


@dataclass
class Kante:
    art: str  # "linie" | "kreis" | "sonstige"
    start: Vektor
    ende: Vektor
    richtung: Vektor | None = None  # Linie: Einheitsrichtung
    abstand: float | None = None
    objekt: object = None  # IEdge


def skalar(a: Vektor, b: Vektor) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def differenz(a: Vektor, b: Vektor) -> Vektor:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def laenge(a: Vektor) -> float:
    return math.sqrt(skalar(a, a))


def punkt_achse_abstand(punkt: Vektor, achspunkt: Vektor, achse: Vektor) -> float:
    d = differenz(punkt, achspunkt)
    t = skalar(d, achse)
    return math.sqrt(max(skalar(d, d) - t * t, 0.0))


def flaeche_in_richtung(flaechen: list[Flaeche], richtung: str, koplanar_ok: bool = False) -> Flaeche:
    """Ebene Fläche mit Normale in `richtung`; bei mehreren die am weitesten in diese Richtung.

    Gleich weit außen liegende Teilflächen (eine Fläche, von einem Zapfen geteilt) sind beim Bauen mehrdeutig (auf
    welcher wird skizziert?), beim Messen nicht: dort zählt nur die Ebene (`koplanar_ok`)."""
    vek = RICHTUNGEN[richtung]
    passend = [f for f in flaechen if f.art == "ebene" and f.normale and skalar(f.normale, vek) > _PARALLEL]
    if not passend:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine ebene Fläche mit Normale {richtung}")
    passend.sort(key=lambda f: skalar(f.punkt, vek), reverse=True)
    if not koplanar_ok and len(passend) > 1 and skalar(passend[0].punkt, vek) - skalar(passend[1].punkt, vek) < _GLEICH_MM:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{len(passend)} gleich weit außen liegende Flächen mit Normale {richtung}")
    return passend[0]


def senkrechte_kanten(kanten: list[Kante], richtung: Vektor) -> list[Kante]:
    """Gerade Kanten parallel zu `richtung` (z. B. Extrusionsrichtung)."""
    treffer = [k for k in kanten if k.art == "linie" and k.richtung and abs(skalar(k.richtung, richtung)) > _PARALLEL]
    if not treffer:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, "keine Kante parallel zur Feature-Richtung")
    return treffer


def naechste(kandidaten: list, tol_mm: float, was: str):
    """Genau ein Kandidat mit abstand <= tol_mm, sonst NICHT_GEFUNDEN bzw. MEHRDEUTIG."""
    if not kandidaten:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine {was} vorhanden")
    sortiert = sorted(kandidaten, key=lambda k: k.abstand)
    innerhalb = [k for k in sortiert if k.abstand <= tol_mm]
    if not innerhalb:
        raise AnkerFehler(
            REFERENZ_NICHT_GEFUNDEN,
            f"keine {was} innerhalb {tol_mm} mm (nächster Abstand {sortiert[0].abstand:.3f} mm)",
        )
    if len(innerhalb) > 1:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{len(innerhalb)} {was}n innerhalb {tol_mm} mm")
    return innerhalb[0]


def zylinder_zu_punkten(zylinder: list[Flaeche], punkte: list[Vektor], tol_mm: float) -> list[Flaeche]:
    """Ordnet jedem Punkt (z. B. Bohrungsposition) die Zylinderfläche zu, deren Achse durch ihn läuft.

    Bei mehreren passenden Zylindern (Bohrung mit Senkung) gewinnt der kleinste Radius.
    """
    ergebnis = []
    for i, p in enumerate(punkte, start=1):
        passend = [z for z in zylinder if z.art == "zylinder" and punkt_achse_abstand(p, z.punkt, z.achse) <= tol_mm]
        if not passend:
            raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine Zylinderfläche für Instanz {i} bei {p}")
        ergebnis.append(min(passend, key=lambda z: z.radius))
    return ergebnis


def zylinder_durch_punkt(flaechen: list[Flaeche], punkt: Vektor, tol_mm: float) -> Flaeche:
    """Zylinderfläche, auf deren Mantel `punkt` liegt (|Abstand Punkt–Achse − Radius| ≤ tol_mm). SolidWorks teilt einen
    Vollzylinder oft in zwei Flächen; Treffer mit gleichem Radius gelten als eine Fläche."""
    treffer = [f for f in flaechen if f.art == "zylinder"
               and abs(punkt_achse_abstand(punkt, f.punkt, f.achse) - f.radius) <= tol_mm]
    if not treffer:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine Zylinderfläche durch {punkt}")
    if len({round(f.radius, 6) for f in treffer}) > 1:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{len(treffer)} Zylinderflächen mit verschiedenen Radien durch {punkt}")
    return treffer[0]


def randkante(kanten: list[Kante], achse_modell: Vektor, vorzeichen: int, punkt: Vektor, tol_mm: float) -> Kante:
    """Randkante einer Skizzenfläche in Richtung `vorzeichen` (+1/−1) entlang `achse_modell`: die äußerste gerade Kante
    quer zur Achse. Bei einem unterbrochenen Rand (mehrere gleich weit außen) die zu `punkt` (Kennpunkt im Modell) nächste,
    gemessen entlang der Kante; bei Gleichstand innerhalb `tol_mm` mehrdeutig."""
    quer = [k for k in kanten if k.art == "linie" and k.richtung and abs(skalar(k.richtung, achse_modell)) < 1e-6]
    if not quer:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, "keine Randkante quer zur Achse")
    lage = {id(k): vorzeichen * skalar(k.start, achse_modell) for k in quer}
    aussen = max(lage.values())
    aeusserste = [k for k in quer if aussen - lage[id(k)] <= tol_mm]

    def abstand(k: Kante) -> float:
        t = skalar(differenz(punkt, k.start), k.richtung)
        laenge_k = skalar(differenz(k.ende, k.start), k.richtung)
        return max(min(0.0, laenge_k) - t, t - max(0.0, laenge_k), 0.0)

    aeusserste.sort(key=abstand)
    if len(aeusserste) > 1 and abstand(aeusserste[1]) - abstand(aeusserste[0]) <= tol_mm:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"Randkante mehrdeutig: {len(aeusserste)} gleich weit außen, Punkt gleich weit von zwei Kanten")
    return aeusserste[0]
