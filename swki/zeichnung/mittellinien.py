"""Mittellinien für Maße mit Mittenbezug (Z1.3 Stufe 2, Nachtrag; Nutzer 18.11.2026: Maße ab Teilmitte ohne gezeichnete
Mittellinie). Reine Geometrie in Blatt-mm; gezeichnet wird in `zeichnen` mit `ISketchManager.CreateCenterLine`
(erscheint im PDF als dünne Strichpunktlinie, spikes/z1_diag_mittellinie.py).

Ein Maß mit `bezug: ursprung`/`mitte` (Maßprotokoll) setzt mit einer Hilfslinie an einem Punkt an, der weder auf einer
sichtbaren Kante noch auf einem Kreismittelpunkt liegt – dort fehlt die Mittellinie. Waagrechte Maße (Hilfslinie
senkrecht) bekommen eine senkrechte Mittellinie durch diesen Punkt, senkrechte Maße eine waagrechte; jede Linie läuft
über den ganzen Körper und `ueberstand` darüber hinaus (ISO 128-2: Mittellinien wenig über den Umriss).
"""

import math

TOLERANZ_MM = 0.4
ECKE_MM = 6.0  # gedachte scharfe Ecke einer gerundeten Kante: so weit hinter dem Kantenende (Blatt-mm)


def bezugspunkt(anfang: tuple[float, float], ende: tuple[float, float], luecke: float) -> tuple[float, float]:
    """Hilfslinie von `anfang` (am Bezug) bis `ende` (über die Maßlinie): der Bezug liegt `luecke` vor dem Anfang."""
    d = math.dist(anfang, ende)
    if d < 1e-9:
        return anfang
    return (round(anfang[0] - (ende[0] - anfang[0]) / d * luecke, 6),
            round(anfang[1] - (ende[1] - anfang[1]) / d * luecke, 6))


def _abstand(p, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    t = 0.0 if n < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def _auf_verlaengerung(p, a, b, toleranz: float) -> bool:
    """Liegt p auf der Geraden durch a–b, höchstens `ECKE_MM` hinter einem Ende (gedachte scharfe Ecke)?"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = (dx * dx + dy * dy) ** 0.5
    if n < 1e-9:
        return False
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n
    quer = abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / n
    return quer <= toleranz and -ECKE_MM <= t <= n + ECKE_MM


def _legt_fest(p, a, b, richtung: str | None, toleranz: float) -> bool:
    """Legt die gerade Kante a–b die gemessene Koordinate von p fest? Nicht, wenn sie parallel zur Messrichtung läuft
    (h misst x, v misst y) und p nicht auf einem ihrer Endpunkte liegt (Live 19.11.: „24,00“ in halber Höhe der
    senkrechten Plattenkante)."""
    if not _auf_verlaengerung(p, a, b, toleranz):
        return False
    dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
    parallel = (richtung == "h" and dy < 0.1 * dx) or (richtung == "v" and dx < 0.1 * dy)
    return not parallel or min(math.dist(p, a), math.dist(p, b)) <= toleranz


def ohne_kante(p: tuple[float, float], strecken: list[tuple], kreismitten: list[tuple[float, float]],
               gebogen: list[tuple] = (), richtung: str | None = None, toleranz: float = TOLERANZ_MM) -> bool:
    """Liegt der Bezugspunkt frei – keine gerade Kante (oder ihre gedachte scharfe Ecke, Live 19.11.: 50/30 der
    gerundeten Tasche) legt die gemessene Koordinate fest (`richtung` h/v des Maßes), kein Bogen (`gebogen`: Stücke,
    ohne Verlängerung) und kein Kreismittelpunkt trägt ihn?"""
    return (not any(_legt_fest(p, a, b, richtung, toleranz) for a, b in strecken)
            and not any(_abstand(p, a, b) <= toleranz for a, b in gebogen)
            and not any(math.dist(p, m) <= toleranz for m in kreismitten))


def linien(bezuege: list[tuple[str, tuple[float, float]]], box: tuple[float, float, float, float],
           ueberstand: float) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Je Richtung und Koordinate eine Linie über den Körper (`box` = x0, y0, x1, y1). `bezuege`: (h|v, Punkt);
    h = waagrechtes Maß → senkrechte Linie bei x, v = senkrechtes Maß → waagrechte Linie bei y."""
    x0, y0, x1, y1 = box
    senkrecht, waagrecht = [], []
    for richtung, (x, y) in bezuege:
        ziel, wert = (senkrecht, x) if richtung == "h" else (waagrecht, y)
        if not any(abs(wert - w) <= TOLERANZ_MM for w in ziel):
            ziel.append(wert)
    return ([((x, y0 - ueberstand), (x, y1 + ueberstand)) for x in senkrecht]
            + [((x0 - ueberstand, y), (x1 + ueberstand, y)) for y in waagrecht])
