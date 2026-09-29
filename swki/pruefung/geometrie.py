"""Reine Geometrie für die Prüfung: Abstände zwischen Punkten, Achsen und Ebenen; analytisches Sollvolumen.

Alle Längen in mm.
"""

import math
from dataclasses import dataclass

from swki.compiler.anker import Vektor, differenz, laenge, punkt_achse_abstand, skalar
from swki.spec.ausdruck import auswerten

_PARALLEL = 1.0 - 1e-6


@dataclass
class Messgeometrie:
    art: str  # "punkt" | "achse" | "ebene"
    punkt: Vektor
    richtung: Vektor | None = None  # Achse: Richtung; Ebene: Normale (Einheitsvektoren)


class NichtMessbar(ValueError):
    pass


def abstand(a: Messgeometrie, b: Messgeometrie) -> float:
    """Kürzester Abstand; Achsen/Ebenen müssen zueinander parallel sein, sonst NichtMessbar."""
    if a.art == "punkt" and b.art == "punkt":
        return laenge(differenz(a.punkt, b.punkt))
    if a.art == "punkt" or b.art == "punkt":
        p, g = (a, b) if a.art == "punkt" else (b, a)
        if g.art == "achse":
            return punkt_achse_abstand(p.punkt, g.punkt, g.richtung)
        return abs(skalar(differenz(p.punkt, g.punkt), g.richtung))
    if a.art == "achse" and b.art == "achse":
        if abs(skalar(a.richtung, b.richtung)) < _PARALLEL:
            raise NichtMessbar("Achsen sind nicht parallel")
        return punkt_achse_abstand(a.punkt, b.punkt, b.richtung)
    if a.art == "ebene" and b.art == "ebene":
        if abs(skalar(a.richtung, b.richtung)) < _PARALLEL:
            raise NichtMessbar("Ebenen sind nicht parallel")
        return abs(skalar(differenz(a.punkt, b.punkt), a.richtung))
    achse, ebene = (a, b) if a.art == "achse" else (b, a)
    if abs(skalar(achse.richtung, ebene.richtung)) > 1e-6:
        raise NichtMessbar("Achse ist nicht parallel zur Ebene")
    return abs(skalar(differenz(achse.punkt, ebene.punkt), ebene.richtung))


def _flaeche(element: dict, p: dict) -> float | None:
    if "rechteck" in element:
        r = element["rechteck"]
        return auswerten(r["breite"], p) * auswerten(r["hoehe"], p)
    if "kreis" in element:
        return math.pi * auswerten(element["kreis"]["durchmesser"], p) ** 2 / 4
    if "polygon" in element:
        pts = [(auswerten(x, p), auswerten(y, p)) for x, y in element["polygon"]["punkte"]]
        return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2
    return None


def _pappus(f: dict, p: dict) -> float:
    elemente = f["skizze"]["elemente"]
    linie = next(e["mittellinie"] for e in elemente if "mittellinie" in e)
    a = (auswerten(linie["von"][0], p), auswerten(linie["von"][1], p))
    b = (auswerten(linie["bis"][0], p), auswerten(linie["bis"][1], p))
    d = (b[0] - a[0], b[1] - a[1])
    n = math.hypot(*d)
    volumen = 0.0
    for e in elemente:
        if "polygon" not in e:
            continue
        pts = [(auswerten(x, p), auswerten(y, p)) for x, y in e["polygon"]["punkte"]]
        a2 = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2
        cx = sum((x1 + x2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / (6 * a2)
        cy = sum((y1 + y2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / (6 * a2)
        r = abs(d[0] * (cy - a[1]) - d[1] * (cx - a[0])) / n
        volumen += abs(a2) * 2 * math.pi * r
    return volumen * auswerten(f.get("winkel", 360), p) / 360


def volumen_auto(spec: dict) -> tuple[float | None, str]:
    """Sollvolumen aus der Spezifikation, soweit analytisch möglich (Annahme: Schnitte liegen ganz im Material,
    Aufsätze überlappen nicht). Rückgabe (volumen, grund); volumen None = nicht berechenbar, grund sagt warum."""
    p = spec.get("parameter", {})
    beitrag: dict[str, float] = {}
    for f in spec["features"]:
        typ = f["typ"]
        if typ in ("extrusion", "schnitt"):
            ende = f["ende"]
            if ende["typ"] == "durch_alles":
                return None, f"{f['id']}: durch_alles"
            flaechen = [_flaeche(e, p) for e in f["skizze"]["elemente"]]
            v = sum(flaechen) * auswerten(ende["tiefe"], p)
            beitrag[f["id"]] = -v if typ == "schnitt" else v
        elif typ == "rotation":
            v = _pappus(f, p)
            beitrag[f["id"]] = -v if f.get("schnitt") else v
        elif typ == "bohrung":
            if f.get("durch"):
                return None, f"{f['id']}: Bohrung durch"
            d, t = auswerten(f["durchmesser"], p), auswerten(f["tiefe"], p)
            v = math.pi * d**2 / 4 * t
            if "senkung" in f:
                ds, ts = auswerten(f["senkung"]["durchmesser"], p), auswerten(f["senkung"]["tiefe"], p)
                v += math.pi * (ds**2 - d**2) / 4 * ts
            beitrag[f["id"]] = -v * len(f["positionen"])
        elif typ == "muster_linear":
            kopien = f["richtung1"]["anzahl"] * f.get("richtung2", {}).get("anzahl", 1) - 1
            beitrag[f["id"]] = kopien * sum(beitrag[q] for q in f["features"])
        elif typ == "muster_kreis":
            beitrag[f["id"]] = (f["anzahl"] - 1) * sum(beitrag[q] for q in f["features"])
        elif typ == "spiegeln":
            beitrag[f["id"]] = sum(beitrag[q] for q in f["features"])
        else:
            return None, f"{f['id']}: {typ} nicht analytisch berechenbar"
    return sum(beitrag.values()), "analytisch"
