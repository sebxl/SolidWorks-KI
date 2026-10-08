"""Formschräge an Extrusion und Schnitt (Paket Formschräge, Spec 2026-10-07): Richtung, Soll-Vorzeichen, versetzter
Querschnitt, Zusammenfall des Profils. Reine Rechnung ohne SolidWorks; Längen in mm, Winkel in Grad.

Bedeutung (Spec §3): r zeigt von der Skizzenebene weg ins Feature (Aufsatz: Wachstumsrichtung, Schnitt: Schnittrichtung).
querschnitt "kleiner": der extrudierte Bereich (Material beim Aufsatz, Aussparung beim Schnitt) wird entlang r kleiner,
"groesser": er wächst.
"""

import math

from swki.compiler.anker import RICHTUNGEN, Vektor, differenz, skalar
from swki.spec.ausdruck import auswerten

TYPEN = ("extrusion", "schnitt")
STANDARDNORMALE: dict[str, Vektor] = {"vorne": (0.0, 0.0, 1.0), "oben": (0.0, 1.0, 0.0), "rechts": (1.0, 0.0, 0.0)}
_QUER = 1e-6  # |cos| unter dem eine Richtung quer zur Extrusionsrichtung liegt
_PARALLEL = 1.0 - 1e-6  # |cos| ab dem eine Flächennormale parallel zu r liegt (Deck- und Bodenfläche)


def schraege(f: dict) -> dict | None:
    """formschraege-Angabe eines extrusion-/schnitt-Knotens, sonst None."""
    if f.get("typ") not in TYPEN:
        return None
    return f.get("ende", {}).get("formschraege")


def skizzennormale(ebene) -> Vektor | None:
    """Normale der Skizzenebene aus der Spezifikation (Standardebene, Versatzebene, Flächenanker mit Richtung);
    None bei {nahe: …} – die Normale kennt dann erst das Modell."""
    if isinstance(ebene, str):
        return STANDARDNORMALE[ebene]
    if "versatz" in ebene:
        return STANDARDNORMALE[ebene["versatz"]["ebene"]]
    if "flaeche" in ebene:
        return RICHTUNGEN[ebene["flaeche"]]
    return None


def extrusionsrichtung(normale: Vektor, typ: str, umkehren: bool) -> Vektor:
    """r: ein Aufsatz wächst mit der Skizzennormale, ein Schnitt geht dagegen; umkehren dreht beides (wie der Handler)."""
    gegen = (typ == "schnitt") != bool(umkehren)
    return tuple(-c for c in normale) if gegen else tuple(normale)


def soll_vorzeichen(typ: str, querschnitt: str) -> int:
    """Soll-Vorzeichen von n·r je Seitenfläche (n äußere Normale des Körpers), Spec §6.1: Aufsatz kleiner +1,
    Aufsatz groesser −1, Schnitt kleiner −1, Schnitt groesser +1."""
    return 1 if (querschnitt == "kleiner") == (typ == "extrusion") else -1


def quer_zur_richtung(richtung: str, normale: Vektor) -> bool:
    """True, wenn die Achsrichtung "+x" … "-z" senkrecht zur Extrusionsrichtung steht (Seitenfläche)."""
    return abs(skalar(RICHTUNGEN[richtung], normale)) < _QUER


def feste_tiefe(ende: dict, parameter: dict) -> float | None:
    """Tiefe T einer Seite: blind = tiefe, mittig = tiefe/2; bei anderen Endbedingungen hängt sie von der Geometrie ab."""
    if ende["typ"] == "blind":
        return auswerten(ende["tiefe"], parameter)
    if ende["typ"] == "mittig":
        return auswerten(ende["tiefe"], parameter) / 2
    return None


def grenze_kleiner(element: dict, parameter: dict) -> tuple[float, str] | None:
    """Größter Einzug (mm), bevor ein Profil bei querschnitt "kleiner" zusammenfällt, und das maßgebende Maß (Spec §5.2);
    None für Profile ohne Vorabprüfung (Polygon, Kontur)."""
    if "kreis" in element:
        return auswerten(element["kreis"]["durchmesser"], parameter) / 2, "halber Durchmesser"
    if "rechteck" in element:
        r = element["rechteck"]
        radius = auswerten(r.get("radius", 0), parameter)
        if radius > 0:
            return radius, "Eckradius"
        return min(auswerten(r["breite"], parameter), auswerten(r["hoehe"], parameter)) / 2, "halbe kürzere Seite"
    if "langloch" in element:
        return auswerten(element["langloch"]["breite"], parameter) / 2, "halbe Breite"
    return None


def _konvexes_polygon(punkte: list[tuple[float, float]]) -> tuple[float, float, float] | None:
    """A, P, K eines konvexen Polygons mit scharfen Ecken; K = Σ tan(θᵢ/2) mit dem Außenwinkel θᵢ je Ecke."""
    n = len(punkte)
    kreuz = []
    for k in range(n):
        (xa, ya), (xb, yb), (xc, yc) = punkte[k - 1], punkte[k], punkte[(k + 1) % n]
        kreuz.append((xb - xa) * (yc - yb) - (yb - ya) * (xc - xb))
    if not (all(c > 0 for c in kreuz) or all(c < 0 for c in kreuz)):
        return None
    flaeche = abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(punkte, punkte[1:] + punkte[:1]))) / 2
    umfang = sum(math.dist(punkte[k], punkte[(k + 1) % n]) for k in range(n))
    k_summe = 0.0
    for k in range(n):
        a, b, c = punkte[k - 1], punkte[k], punkte[(k + 1) % n]
        v1, v2 = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
        cos_theta = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))
        k_summe += math.tan(math.acos(max(-1.0, min(1.0, cos_theta))) / 2)
    return flaeche, umfang, k_summe


def querschnitt_koeffizienten(element: dict, parameter: dict) -> tuple[float, float, float] | None:
    """A, P, K des um d nach außen versetzten Querschnitts A(d) = A + P·d + K·d² (Spec §6.2); None, wenn das Profil
    nicht analytisch ist (Kontur, Polygon mit Radien oder nicht konvex)."""
    p = parameter
    if "kreis" in element:
        d = auswerten(element["kreis"]["durchmesser"], p)
        return math.pi * d * d / 4, math.pi * d, math.pi
    if "rechteck" in element:
        r = element["rechteck"]
        b, h, radius = auswerten(r["breite"], p), auswerten(r["hoehe"], p), auswerten(r.get("radius", 0), p)
        k = math.pi if radius > 0 else 4.0
        return b * h - (4 - math.pi) * radius**2, 2 * (b + h) - (8 - 2 * math.pi) * radius, k
    if "langloch" in element:
        laenge, breite = auswerten(element["langloch"]["laenge"], p), auswerten(element["langloch"]["breite"], p)
        return laenge * breite + math.pi * breite**2 / 4, 2 * laenge + math.pi * breite, math.pi
    if "polygon" in element:
        poly = element["polygon"]
        radien = poly.get("radien", 0)
        if any(auswerten(r, p) != 0 for r in (radien if isinstance(radien, list) else [radien])):
            return None
        return _konvexes_polygon([(auswerten(u, p), auswerten(v, p)) for u, v in poly["punkte"]])
    return None


def volumen(koeffizienten: tuple[float, float, float], tiefe: float, winkel: float, querschnitt: str,
            mittig: bool = False) -> float:
    """Volumen (mm³) eines geschrägten Features: ∫ A(±h·tan α) dh über die Tiefe; bei mittig zwei Hälften tiefe/2."""
    a, p, k = koeffizienten
    t = math.tan(math.radians(winkel))
    s = 1 if querschnitt == "groesser" else -1

    def seite(h: float) -> float:
        return a * h + s * p * t * h * h / 2 + k * t * t * h**3 / 3

    return 2 * seite(tiefe / 2) if mittig else seite(tiefe)


def volumen_feature(f: dict, parameter: dict) -> tuple[float | None, str]:
    """Sollvolumen eines extrusion-/schnitt-Knotens mit formschraege (blind oder mittig); (None, Grund) sonst."""
    s, ende = schraege(f), f["ende"]
    if ende["typ"] not in ("blind", "mittig"):
        return None, f"{f['id']}: ende {ende['typ']} mit Formschräge (Tiefe hängt von der Geometrie ab)"
    elemente = f["skizze"]["elemente"]
    if len(elemente) != 1:
        return None, f"{f['id']}: Formschräge mit mehreren Profilen nicht analytisch"
    koeffizienten = querschnitt_koeffizienten(elemente[0], parameter)
    if koeffizienten is None:
        return None, f"{f['id']}: Formschräge mit diesem Profil nicht analytisch (Kreis, Rechteck, Langloch, konvexes Polygon)"
    v = volumen(koeffizienten, auswerten(ende["tiefe"], parameter), auswerten(s["winkel"], parameter), s["querschnitt"],
                mittig=ende["typ"] == "mittig")
    return v, "analytisch"


def seitenflaechen(messungen: list[tuple[Vektor, Vektor]], r: Vektor, ebenenpunkt: Vektor | None = None) -> list[dict]:
    """Winkel (Grad) und Vorzeichen von n·r je Seitenfläche aus (Punkt in mm, äußere Einheitsnormale) – Spec §6.1.
    Flächen mit Normale parallel zu r (Deck- und Bodenflächen) zählen nicht. ebenenpunkt (nur bei mittig): Punkt der
    Skizzenebene; Flächen hinter der Skizzenebene messen gegen −r. Vorzeichen 0 = Wand ohne Schräge."""
    ergebnis = []
    for punkt, n in messungen:
        c = skalar(n, r)
        if abs(c) > _PARALLEL:
            continue
        if ebenenpunkt is not None and skalar(differenz(punkt, ebenenpunkt), r) < 0:
            c = -c
        ergebnis.append({"winkel": round(math.degrees(math.asin(min(1.0, abs(c)))), 6),
                         "vorzeichen": 0 if abs(c) < 1e-9 else (1 if c > 0 else -1)})
    return ergebnis
