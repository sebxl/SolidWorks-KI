"""Anordnung der Ansichten auf dem Blatt (Z1.3 Stufe 1; Recherche Kap. 3: Projektionsmethode 1).

Hauptansicht links oben, Seitenansicht (von links gesehen) rechts daneben auf gleicher Höhe, Draufsicht darunter auf
gleicher Achse. Um jede Ansicht bleibt ein Rand für die Maße der Stufe 2 (`MASSRAND_MM`, auf dem Papier, unabhängig
vom Maßstab). Format und Maßstab: der erste Kandidat aus `blatt.kandidaten`, bei dem der Block in eine Freifläche
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
    """groessen_1zu1: Umriss je Rolle (haupt, seite, drauf) in mm bei 1:1. Liefert Format, Maßstab und Plätze."""
    for format_, massstab in kandidaten():
        f = massstab[0] / massstab[1]
        haupt, seite, drauf = (_zelle(groessen_1zu1.get(r), f) for r in ("haupt", "seite", "drauf"))
        breite = max(haupt[0] + seite[0], drauf[0])
        hoehe = max(haupt[1], seite[1]) + drauf[1]
        for x0, y0, x1, y1 in freiflaechen(format_):
            if breite > x1 - x0 or hoehe > y1 - y0:
                continue
            links = x0 + (x1 - x0 - breite) / 2
            oben = y1 - (y1 - y0 - hoehe) / 2
            reihe = max(haupt[1], seite[1])
            mitte_haupt = (links + haupt[0] / 2, oben - reihe / 2)
            plaetze = [Platz("haupt", mitte_haupt, _skaliert(groessen_1zu1["haupt"], f))]
            if "seite" in groessen_1zu1:
                plaetze.append(Platz("seite", (links + haupt[0] + seite[0] / 2, mitte_haupt[1]),
                                     _skaliert(groessen_1zu1["seite"], f)))
            if "drauf" in groessen_1zu1:
                plaetze.append(Platz("drauf", (mitte_haupt[0], oben - reihe - drauf[1] / 2),
                                     _skaliert(groessen_1zu1["drauf"], f)))
            return format_, massstab, plaetze
    raise ValueError(f"Ansichten passen auf kein Format: {groessen_1zu1}")


def _skaliert(groesse: tuple[float, float], f: float) -> tuple[float, float]:
    return (groesse[0] * f, groesse[1] * f)
