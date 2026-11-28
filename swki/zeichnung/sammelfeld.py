"""Sammelangaben über dem Schriftfeld, ohne SolidWorks (Zeichnen, PDF-Prüfung und Zeichnungsprüfung rechnen dieselbe
Lage): Band, Umbruch der Zeilen und das Rauheitsfeld.

Rauheitsfeld (Nutzer 28.11.2026): kleiner Kasten rechts oben im Band, darin das Rauheitssymbol nach ISO 1302:2002
(Grundsymbol, Feld a „Ra 3,2“, ohne Hinweislinie) und der Hinweis „Alle Flächen ohne andere Angabe“ – ersetzt die
Textzeile „Oberflächen ohne Angabe: Ra 3,2“. Maße live vermessen (spikes/z1_diag_rauheitsfeld.py, 28.11.2026,
Hinweistext 3,5 mm): Lage des Symbols (`SetPosition2`/`GetPosition`) ist seine Spitze; das Symbol reicht 3,0 mm nach
links, 10,0 mm nach oben, der Strich über „Ra 3,2“ 20,8 mm nach rechts; der zweizeilige Hinweis ist 40,8 × 10,9 mm, seine
Lage die linke obere Ecke (Text 1,4 mm darüber). Eine Blattskizze folgt dem Blattmaßstab (bei 1:2 halb so groß).
"""

import math
from dataclasses import dataclass

from swki.zeichnung.blatt import SCHRIFTFELD_MM, zeichenfeld

SAMMEL_ZEICHEN = 72                 # Zeichen je Zeile im Band (180 mm, live 2,36 mm je Zeichen)
SAMMEL_ZEICHEN_MM = 180 / SAMMEL_ZEICHEN   # Breite je Zeichen mit Reserve (2,5 mm)
SAMMEL_ZEILENABSTAND_MM = 4.55      # Hinweistext 3,5 mm, live 27.11. vermessen
SAMMEL_OBERKANTE_MM = 1.4           # Textoberkante über `IAnnotation.GetPosition` (Live 19.11.)
SAMMEL_LINKS_MM = 1.0               # Sammelhinweis: Abstand vom linken Rand des Bands
SAMMEL_SPALT_MM = 3.0               # Abstand Sammelzeile – Rauheitsfeld
ZEILE_MM = 5.0                      # = blatt.SAMMEL_ZEILE_MM (Höhe einer Zeile im Band)

RAUHEITSFELD_MM = (71.0, 14.0)      # Breite, Höhe des Kastens
FELD_RAND_MM = 1.5                  # Innenabstand
SYMBOL_LINKS_MM, SYMBOL_HOEHE_MM, SYMBOL_RECHTS_MM = 3.0, 10.0, 20.8   # um die Spitze, live 28.11.
SYMBOL_HINWEIS_SPALT_MM = 2.5
HINWEIS_HOEHE_MM = 10.9             # zwei Zeilen, live 28.11.
HINWEIS_UNTER_LAGE_MM = 9.47        # Unterkante des Texts unter `GetPosition` (live 28.11.)


@dataclass(frozen=True)
class Rauheitsfeld:
    rahmen: tuple[float, float, float, float]   # Kasten (x0, y0, x1, y1) in Blatt-mm
    symbol: tuple[float, float]                 # Spitze des Rauheitssymbols
    hinweis: tuple[float, float]                # linke obere Ecke des Hinweises (`SetPosition2`)
    zeile: int                                  # erste Zeile des Sammelhinweises neben dem Kasten


def umbrechen(zeilen: list[str], zeichen: int = SAMMEL_ZEICHEN) -> list[str]:
    """Zeilen, die breiter als das Band wären, nach „, “ bzw. am letzten Leerzeichen umbrechen (Härteangabe der
    Buchse: 77 Zeichen ≈ 182 mm gegen 180 mm Schriftfeldbreite). Zusammengefügt mit Leerzeichen ergibt sich die
    Zeile wieder (Prüfung Z1.4 vergleicht whitespace-normalisiert)."""
    aus = []
    for z in zeilen:
        while len(z) > zeichen:
            schnitt = z.rfind(", ", 0, zeichen)
            if schnitt > 0:
                aus.append(z[:schnitt + 1])
                z = z[schnitt + 2:]
                continue
            schnitt = z.rfind(" ", 0, zeichen)
            if schnitt <= 0:
                break
            aus.append(z[:schnitt])
            z = z[schnitt + 1:]
        aus.append(z)
    return aus


def _zeilen_neben_feld() -> int:
    """So viele Zeilen des Sammelhinweises stehen neben dem Kasten (0,5 mm Überlappung zählt nicht)."""
    return math.ceil((RAUHEITSFELD_MM[1] - 0.5) / SAMMEL_ZEILENABSTAND_MM)


def frei_zeichen() -> int:
    """Zeichen, die links neben dem Rauheitsfeld Platz haben."""
    breite = SCHRIFTFELD_MM[0] - SAMMEL_LINKS_MM - RAUHEITSFELD_MM[0] - SAMMEL_SPALT_MM
    return int(breite / SAMMEL_ZEICHEN_MM)


def sammel_aufteilung(zeilen: list[str]) -> tuple[list[str], int]:
    """Zeilen des Sammelhinweises (umgebrochen auf die Bandbreite) und die Zeile, an deren Oberkante das Rauheitsfeld
    rechts beginnt: die erste, ab der alle Zeilen neben dem Kasten kurz genug sind (`frei_zeichen`); passt es nirgends,
    unter der letzten Zeile (Index = Zeilenzahl). Live 27.11.: eine eigene Zeile hob das Band der Spannplatte um 5 mm,
    die Ansichten passten nicht mehr auf A3 1:2 (A4 1:5) – deshalb steht der Kasten neben den Zeilen."""
    umbrochen = umbrechen(zeilen)
    n, frei = _zeilen_neben_feld(), frei_zeichen()
    zeile = next(i for i in range(len(umbrochen) + 1) if all(len(z) <= frei for z in umbrochen[i:i + n]))
    return umbrochen, zeile


def sammel_zeilenzahl(zeilen: list[str]) -> int:
    """Zeilen, die das Band über dem Schriftfeld braucht (Höhe = Zahl × `SAMMEL_ZEILE_MM`): Sammelhinweis und
    Rauheitsfeld."""
    umbrochen, zeile = sammel_aufteilung(zeilen)
    return max(len(umbrochen), math.ceil((zeile * SAMMEL_ZEILENABSTAND_MM + RAUHEITSFELD_MM[1]) / ZEILE_MM - 1e-9))


def sammelband(format_: str, hoehe_mm: float) -> tuple[float, float, float, float]:
    """Reserviertes Band über dem Schriftfeld (Blatt-mm), so breit wie das Schriftfeld, rechtsbündig."""
    x0, y0, x1, _ = zeichenfeld(format_)
    sb, sh = SCHRIFTFELD_MM
    return (x1 - sb, y0 + sh, x1, y0 + sh + hoehe_mm)


def rauheitsfeld(band: tuple[float, float, float, float], zeilen: list[str]) -> Rauheitsfeld:
    """Kasten rechtsbündig im Band, Oberkante an der Zeile `sammel_aufteilung`; Symbol links, Hinweis rechts daneben,
    beide mittig in der Höhe."""
    _, zeile = sammel_aufteilung(zeilen)
    b, h = RAUHEITSFELD_MM
    x1, y1 = band[2], band[3] - zeile * SAMMEL_ZEILENABSTAND_MM
    x0, y0 = x1 - b, y1 - h
    symbol = (x0 + FELD_RAND_MM + SYMBOL_LINKS_MM, y0 + (h - SYMBOL_HOEHE_MM) / 2)
    hinweis_x = symbol[0] + SYMBOL_RECHTS_MM + SYMBOL_HINWEIS_SPALT_MM
    hinweis_y = (y0 + y1) / 2 + HINWEIS_HOEHE_MM / 2 - (HINWEIS_HOEHE_MM - HINWEIS_UNTER_LAGE_MM)
    return Rauheitsfeld((x0, y0, x1, y1), symbol, (hinweis_x, hinweis_y), zeile)


def sammelzeilen_lage(band: tuple[float, float, float, float]) -> tuple[float, float]:
    """Linke obere Ecke des Sammelhinweises (`SetPosition2`)."""
    return band[0] + SAMMEL_LINKS_MM, band[3] - SAMMEL_OBERKANTE_MM
