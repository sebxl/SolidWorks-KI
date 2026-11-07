"""Geometrie der Baugruppenprüfung (ohne SolidWorks): Teil- → Baugruppenkoordinaten, Einschraublänge, Soll-Überlappung
einer Gewindepaarung. Längen in mm."""

import math

from swki.compiler.anker import differenz, laenge, skalar
from swki.pruefung.geometrie import Messgeometrie
from swki.verbindung import in_mm


def transformiere(g: Messgeometrie, t) -> Messgeometrie:
    """Teil- → Baugruppenkoordinaten mit IComponent2.Transform2.ArrayData: [0:9] Drehung (Zeile i = Bild der Achse i,
    Zeilenvektor-Konvention wie die Ebenennormale ArrayData[6:9] in Spike S11), [9:12] Verschiebung in m, [12] Maßstab
    (Spike S12 Zeile 12)."""
    skala = t[12] if len(t) > 12 and t[12] else 1.0

    def dreh(v):
        return tuple(v[0] * t[i] + v[1] * t[3 + i] + v[2] * t[6 + i] for i in range(3))

    p = dreh(g.punkt)
    punkt = tuple(skala * p[i] + in_mm(t[9 + i]) for i in range(3))
    richtung = None
    if g.richtung is not None:
        r = dreh(g.richtung)
        n = laenge(r)
        richtung = tuple(c / n for c in r)
    return Messgeometrie(g.art, punkt, richtung)


def drehmatrix(achse, winkel: float) -> list[list[float]]:
    """Drehung um achse (wird normiert) um winkel Grad nach der Rechte-Hand-Regel, Spaltenform (Rodrigues)."""
    n = math.sqrt(sum(c * c for c in achse))
    x, y, z = (c / n for c in achse)
    a = math.radians(winkel)
    c, s = math.cos(a), math.sin(a)
    k = 1 - c
    return [[c + x * x * k, x * y * k - z * s, x * z * k + y * s],
            [y * x * k + z * s, c + y * y * k, y * z * k - x * s],
            [z * x * k - y * s, z * y * k + x * s, c + z * z * k]]


def einschraublaenge(laenge_schraube: float, kopfauflage: Messgeometrie, eintritt: Messgeometrie) -> float:
    """Schaftlänge hinter dem Eintrittspunkt der Gewindebohrung: l − Abstand Kopfauflage–Eintritt entlang der Achse."""
    return laenge_schraube - abs(skalar(differenz(eintritt.punkt, kopfauflage.punkt), kopfauflage.richtung))


def _ansenkung_abzug(d: float, p: float, kernloch: float, einschraub: float, c: float) -> float:
    """Überlappung, die eine Ansenkung c × 45° am Eintritt wegnimmt (mm³). Geschlossen π·c·(rk·c + c²/3), wenn die
    Ansenkung im vollen Schaft liegt und nicht über den Nenn-Ø reicht; sonst numerisch (Mittelpunktsumme)."""
    rn, rk = d / 2, kernloch / 2
    if einschraub >= c + p and rk + c <= rn + 1e-9:
        return math.pi * c * (rk * c + c * c / 3)
    schritte = 20000
    h = min(c, einschraub) / schritte
    abzug = 0.0
    for k in range(schritte):
        x = (k + 0.5) * h  # Abstand vom Eintritt
        s = einschraub - x  # Abstand von der Schraubenspitze
        r = rn - p + s if s < p else rn
        rh = rk + c - x
        abzug += math.pi * (max(r * r - rk * rk, 0.0) - max(r * r - rh * rh, 0.0)) * h
    return abzug


def ueberlappung_soll(d: float, p: float, kernloch: float, einschraub: float, ansenkung: float = 0.0) -> float:
    """Soll-Überlappung Schraube (Nenn-Ø d, Endfase p × 45°) ↔ Kernloch (mm³): Ring Nenn-Ø/Kernloch-Ø über die
    Einschraublänge; im Fasenbereich nur der Teil, der über das Kernloch ragt; eine Ansenkung c × 45° am Eintritt der
    Bohrung (Feld fase, Paket Konstruktionsstil) nimmt ihren Teil weg."""
    if einschraub <= 0:
        return 0.0
    if ansenkung > 0:
        return ueberlappung_soll(d, p, kernloch, einschraub) - _ansenkung_abzug(d, p, kernloch, einschraub, ansenkung)
    rn, rk = d / 2, kernloch / 2
    a = rn - p  # Radius an der Spitze
    v = 0.0
    s_von, s_bis = max(rk - a, 0.0), min(p, einschraub)  # s: Abstand von der Spitze innerhalb der Fase
    if s_bis > s_von:
        v += math.pi * (((a + s_bis) ** 3 - (a + s_von) ** 3) / 3 - rk ** 2 * (s_bis - s_von))
    if einschraub > p:
        v += math.pi * (rn ** 2 - rk ** 2) * (einschraub - p)
    return v
