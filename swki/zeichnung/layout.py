"""Anordnung der Ansichten auf dem Blatt (Z1.3 Stufe 1; Recherche Kap. 3: Projektionsmethode 1).

Hauptansicht in der Mitte, Seitenansicht (von links gesehen) rechts daneben, von rechts gesehen links daneben, jeweils
auf gleicher Höhe; Draufsicht darunter, Ansicht von unten darüber, jeweils auf gleicher Achse. Um jede Ansicht
bleibt ein Rand für die Maße der Stufe 2 (`MASSRAND_MM`, auf dem Papier, unabhängig vom Maßstab). Format und
Maßstab: der erste Kandidat aus `blatt.kandidaten`, bei dem der Block in eine Freifläche passt; die Ansichten liegen dann nie im Schriftfeld (Review Focus 5).
"""

from dataclasses import dataclass

from swki.zeichnung.blatt import MASSSTAEBE, freiflaechen, kandidaten

MASSRAND_MM = 25


@dataclass(frozen=True)
class Platz:
    rolle: str
    mitte_mm: tuple[float, float]       # Blattkoordinaten, Ursprung links unten
    groesse_mm: tuple[float, float]     # Umriss im Blattmaßstab, ohne Rand
    massstab: tuple[int, int] | None = None  # eigener Maßstab (nur Einzelheit), sonst der des Blatts


def _zelle(groesse: tuple[float, float] | None, f: float) -> tuple[float, float]:
    if groesse is None:
        return (0.0, 0.0)
    return (groesse[0] * f + 2 * MASSRAND_MM, groesse[1] * f + 2 * MASSRAND_MM)


def _einzelheit_massstaebe(massstab: tuple[int, int]) -> list[tuple[int, int]]:
    """Normmaßstab der Einzelheit: der kleinste mit mindestens doppelter Vergrößerung (Nutzer 18.11.2026: „Details
    werden in der Regel vergrößert, sonst braucht man kein Detail.“)."""
    f = massstab[0] / massstab[1]
    groesser = [m for m in MASSSTAEBE if m[0] / m[1] >= 2 * f - 1e-9]
    return [min(groesser, key=lambda m: m[0] / m[1])] if groesser else []


def einzelheit_passt(groessen_1zu1: dict[str, tuple[float, float]], einzelheit: tuple[float, float],
                     sammel_mm: float = 0.0) -> bool:
    """Lohnt die Einzelheit? Nur wenn sie vergrößert aufs Blatt passt, ohne Format oder Blattmaßstab zu ändern."""
    try:
        ohne = anordnen(groessen_1zu1, sammel_mm)[:2]
        format_, massstab, plaetze = anordnen({**groessen_1zu1, "einzelheit": einzelheit}, sammel_mm)
    except ValueError:
        return False
    detail = next((p for p in plaetze if p.rolle == "einzelheit"), None)
    return (format_, massstab) == ohne and detail is not None and detail.massstab != massstab


def anordnen(groessen_1zu1: dict[str, tuple[float, float]],
             sammel_mm: float = 0.0) -> tuple[str, tuple[int, int], list[Platz]]:
    """groessen_1zu1: Umriss je Rolle (haupt, seite, drauf, seite_rechts, unter, einzelheit) in mm bei 1:1. Liefert
    Format, Maßstab und Plätze. Die Einzelheit (Nutzer 18.11.2026) bekommt einen eigenen, vergrößerten Maßstab und
    liegt in der Ecke unter der Seitenansicht oder rechts neben ihr; sie verbreitert dort Spalte und Reihe, ohne die
    Projektionen aus der Flucht zu bringen. Ob sie das Blatt verkleinern würde, prüft `einzelheit_passt` vorher.
    `sammel_mm`: Höhe der Sammelangaben über dem Schriftfeld, die keine Ansicht belegen darf."""
    detail = groessen_1zu1.get("einzelheit")
    for format_, massstab in kandidaten():
        f = massstab[0] / massstab[1]
        z = {r: _zelle(groessen_1zu1.get(r), f) for r in ("haupt", "seite", "drauf", "seite_rechts", "unter")}
        lagen = [(md, ort) for md in _einzelheit_massstaebe(massstab) for ort in ("ecke", "rechts")] if detail else [(None, "")]
        for md, ort in lagen:
            zd = _zelle(detail, md[0] / md[1]) if md else (0.0, 0.0)
            ecke, daneben = (zd, (0.0, 0.0)) if ort == "ecke" else ((0.0, 0.0), zd)
            spalte = max(z["haupt"][0], z["drauf"][0], z["unter"][0])     # Mittelspalte: unter / haupt / drauf
            reihe = max(z["haupt"][1], z["seite"][1], z["seite_rechts"][1], daneben[1])  # Mittelreihe
            rechts, unten = max(z["seite"][0], ecke[0]), max(z["drauf"][1], ecke[1])
            breite = z["seite_rechts"][0] + spalte + rechts + daneben[0]
            hoehe = z["unter"][1] + reihe + unten
            for x0, y0, x1, y1 in freiflaechen(format_, sammel_mm):
                if breite > x1 - x0 or hoehe > y1 - y0:
                    continue
                links = x0 + (x1 - x0 - breite) / 2
                oben = y1 - (y1 - y0 - hoehe) / 2
                mx = links + z["seite_rechts"][0] + spalte / 2
                my = oben - z["unter"][1] - reihe / 2
                mitten = {"haupt": (mx, my), "seite": (mx + spalte / 2 + z["seite"][0] / 2, my),
                          "seite_rechts": (mx - spalte / 2 - z["seite_rechts"][0] / 2, my),
                          "drauf": (mx, my - reihe / 2 - z["drauf"][1] / 2),
                          "unter": (mx, my + reihe / 2 + z["unter"][1] / 2),
                          "einzelheit": ((mx + spalte / 2 + rechts / 2, my - reihe / 2 - unten / 2) if ort == "ecke"
                                         else (mx + spalte / 2 + rechts + daneben[0] / 2, my))}
                plaetze = [Platz(r, mitten[r], _skaliert(g, f)) for r, g in groessen_1zu1.items() if r != "einzelheit"]
                if md:
                    plaetze.append(Platz("einzelheit", mitten["einzelheit"], _skaliert(detail, md[0] / md[1]), md))
                return format_, massstab, plaetze
    raise ValueError(f"Ansichten passen auf kein Format: {groessen_1zu1}")


def _skaliert(groesse: tuple[float, float], f: float) -> tuple[float, float]:
    return (groesse[0] * f, groesse[1] * f)
