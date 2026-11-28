"""Format und Maßstab einer Zeichnung (Z1.3 Stufe 1; Recherche Kap. 2: ISO 5457 Ränder, ISO 5455 Vorzugsmaßstäbe).

Maße in mm. Das Zeichenfeld liegt innerhalb des Rahmens (links 20 mm, sonst 10 mm); das Schriftfeld (ISO 7200, 180 mm
breit) sitzt rechts unten. Ansichten passen, wenn ihr Platzbedarf über dem Schriftfeld (volle Breite) oder links
neben ihm (volle Höhe) liegt.
"""

FORMATE: dict[str, tuple[float, float]] = {"A4": (210, 297), "A3quer": (420, 297)}  # Reihenfolge = Vorrang
MASSSTAEBE: list[tuple[int, int]] = [(5, 1), (2, 1), (1, 1), (1, 2), (1, 5), (1, 10), (1, 20)]
SCHRIFTFELD_MM = (180, 55)  # Breite nach ISO 7200; Höhe des Schriftfelds im SW-2025-Format (Hausregel bis Z1.5)
RAND_LINKS_MM, RAND_MM = 20, 10
SAMMEL_ZEILE_MM = 5.0  # Zeilenhöhe der Sammelangaben über dem Schriftfeld (Hausregel bis Z1.5)


def zeichenfeld(format_: str) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) des Zeichenfelds in mm, Ursprung links unten auf dem Blatt."""
    b, h = FORMATE[format_]
    return (RAND_LINKS_MM, RAND_MM, b - RAND_MM, h - RAND_MM)


def freiflaechen(format_: str, sammel_mm: float = 0.0) -> list[tuple[float, float, float, float]]:
    """Rechtecke ohne Schriftfeld: über dem Schriftfeld (volle Breite) und links daneben (volle Höhe). Die
    Sammelangaben (`sammel_mm` hoch) stehen über dem Schriftfeld; das obere Rechteck beginnt deshalb höher."""
    x0, y0, x1, y1 = zeichenfeld(format_)
    sb, sh = SCHRIFTFELD_MM
    return [(x0, y0 + sh + sammel_mm, x1, y1), (x0, y0, x1 - sb, y1)]


def passt(bedarf_mm: tuple[float, float], format_: str, sammel_mm: float = 0.0) -> bool:
    b, h = bedarf_mm
    return any(b <= x1 - x0 and h <= y1 - y0 for x0, y0, x1, y1 in freiflaechen(format_, sammel_mm))


def _skaliert(bedarf_mm: tuple[float, float], massstab: tuple[int, int]) -> tuple[float, float]:
    f = massstab[0] / massstab[1]
    return (bedarf_mm[0] * f, bedarf_mm[1] * f)


def kandidaten():
    """(Format, Maßstab) in Vorrang-Reihenfolge: erst Vergrößerungen auf A4 (größte zuerst), dann je Maßstab ab 1:1
    abwärts das kleinste Format – lieber A3 in 1:2 als A4 in 1:5 (Review Focus 1)."""
    for m in MASSSTAEBE:
        if m[0] > m[1]:
            yield "A4", m
    for m in (m for m in MASSSTAEBE if m[0] <= m[1]):
        for format_ in FORMATE:
            yield format_, m


def waehle(bedarf_mm: tuple[float, float], sammel_mm: float = 0.0) -> tuple[str, tuple[int, int]]:
    """Format und Maßstab für einen Platzbedarf bei 1:1 (Ansichten samt Maßrand): der erste passende Kandidat."""
    for format_, m in kandidaten():
        if passt(_skaliert(bedarf_mm, m), format_, sammel_mm):
            return format_, m
    return "A3quer", MASSSTAEBE[-1]
