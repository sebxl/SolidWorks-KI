"""Anordnung der Ansichten auf dem Blatt (Z1.3 Stufe 1; Recherche Kap. 3: Projektionsmethode 1).

Hauptansicht in der Mitte, Seitenansicht (von links gesehen) rechts daneben, von rechts gesehen links daneben, jeweils
auf gleicher Höhe; Draufsicht darunter, Ansicht von unten darüber, jeweils auf gleicher Achse. Um jede Ansicht
bleibt ein Rand für die Maße der Stufe 2 (`MASSRAND_MM`, auf dem Papier, unabhängig vom Maßstab). Format und Maßstab: der erste Kandidat aus `blatt.kandidaten`, bei dem der Block in eine Freifläche
passt; die Ansichten liegen dann nie im Schriftfeld (Review Focus 5).
"""

from dataclasses import dataclass

from swki.zeichnung.blatt import freiflaechen, kandidaten

MASSRAND_MM = 25


@dataclass(frozen=True)
class Platz:
    rolle: str
    mitte_mm: tuple[float, float]       # Blattkoordinaten, Ursprung links unten
    groesse_mm: tuple[float, float]     # Umriss im Blattmaßstab, ohne Rand


def _zelle(groesse: tuple[float, float] | None, f: float) -> tuple[float, float]:
    if groesse is None:
        return (0.0, 0.0)
    return (groesse[0] * f + 2 * MASSRAND_MM, groesse[1] * f + 2 * MASSRAND_MM)


def anordnen(groessen_1zu1: dict[str, tuple[float, float]]) -> tuple[str, tuple[int, int], list[Platz]]:
    """groessen_1zu1: Umriss je Rolle (haupt, seite, drauf, seite_rechts, unter) in mm bei 1:1. Liefert Format, Maßstab und Plätze."""
    for format_, massstab in kandidaten():
        f = massstab[0] / massstab[1]
        z = {r: _zelle(groessen_1zu1.get(r), f) for r in ("haupt", "seite", "drauf", "seite_rechts", "unter")}
        spalte = max(z["haupt"][0], z["drauf"][0], z["unter"][0])     # Mittelspalte: unter / haupt / drauf
        reihe = max(z["haupt"][1], z["seite"][1], z["seite_rechts"][1])  # Mittelreihe: seite_rechts / haupt / seite
        breite = z["seite_rechts"][0] + spalte + z["seite"][0]
        hoehe = z["unter"][1] + reihe + z["drauf"][1]
        for x0, y0, x1, y1 in freiflaechen(format_):
            if breite > x1 - x0 or hoehe > y1 - y0:
                continue
            links = x0 + (x1 - x0 - breite) / 2
            oben = y1 - (y1 - y0 - hoehe) / 2
            mx = links + z["seite_rechts"][0] + spalte / 2
            my = oben - z["unter"][1] - reihe / 2
            mitten = {"haupt": (mx, my), "seite": (mx + spalte / 2 + z["seite"][0] / 2, my),
                      "seite_rechts": (mx - spalte / 2 - z["seite_rechts"][0] / 2, my),
                      "drauf": (mx, my - reihe / 2 - z["drauf"][1] / 2), "unter": (mx, my + reihe / 2 + z["unter"][1] / 2)}
            plaetze = [Platz(r, mitten[r], _skaliert(g, f)) for r, g in groessen_1zu1.items()]
            return format_, massstab, plaetze
    raise ValueError(f"Ansichten passen auf kein Format: {groessen_1zu1}")


def _skaliert(groesse: tuple[float, float], f: float) -> tuple[float, float]:
    return (groesse[0] * f, groesse[1] * f)
