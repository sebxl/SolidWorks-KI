"""Lesbarkeit einer Zeichnung am PDF prüfen (Z1.3 Stufe 2, Nachtrag; Nutzer 18.11.2026: Maß auf der Schnittkennzeichnung,
Maßzahlen von Linien gekreuzt). Geprüft wird, was der Leser sieht: Texte mit ihren Rechtecken und alle Liniensegmente
aus dem PDF (pymupdf), nicht die API-Rückgabe.

- `text_ueber_text`: zwei Texte überlappen.
- `linie_durch_text`: ein Liniensegment kreuzt den Kern einer Maßzahl. Die eigene Maßlinie unter der Zahl berührt nur
  den Rand; deshalb zählt nur der Kern des Textrechtecks (innen um einen Teil der Höhe verkleinert).

Koordinaten der Befunde in Blatt-mm, Ursprung links unten (wie `IAnnotation.SetPosition2`).
"""

from dataclasses import dataclass
from pathlib import Path

PT_MM = 25.4 / 72
KERN = 0.22  # Anteil der Texthöhe, um den das Rechteck oben/unten verkleinert wird (Abstand zur eigenen Maßlinie)


@dataclass(frozen=True)
class Befund:
    art: str                                   # text_ueber_text | linie_durch_text
    text: str
    rechteck_mm: tuple[float, float, float, float]
    anderes: str = ""


def _schneidet(a, b, r) -> bool:
    """Schneidet die Strecke a–b das Rechteck r = (x0, y0, x1, y1)? (Liang-Barsky)"""
    x0, y0, x1, y1 = r
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def _ueberlappt(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _kern(r):
    """Textrechteck ohne Ober-/Unterlänge und Zeilenabstand; bei hochgestellter Schrift gilt die kurze Seite als Höhe."""
    h = min(r[2] - r[0], r[3] - r[1])
    dx, dy = (0.1 * h, KERN * h) if r[2] - r[0] >= r[3] - r[1] else (KERN * h, 0.1 * h)
    return (r[0] + dx, r[1] + dy, r[2] - dx, r[3] - dy)


def _im(r, bereiche) -> bool:
    return any(_ueberlappt(r, b) for b in bereiche)


def pruefe_pdf(pdf: Path, ausschluss_mm: list[tuple] | None = None, seite: int = 0) -> list[Befund]:
    import pymupdf

    ausschluss_mm = ausschluss_mm or []
    with pymupdf.open(pdf) as doc:
        page = doc[seite]
        hoehe_mm = page.rect.height * PT_MM

        def mm(x, y):
            return (x * PT_MM, hoehe_mm - y * PT_MM)

        texte = []  # (Text, Rechteck mm, achsparallel)
        for block in page.get_text("dict")["blocks"]:
            for zeile in block.get("lines", []):
                wort = "".join(s["text"] for s in zeile["spans"]).strip()
                if not wort:
                    continue
                x0, y0, x1, y1 = zeile["bbox"]
                (ax, ay), (bx, by) = mm(x0, y1), mm(x1, y0)
                r = (ax, ay, bx, by)
                cos, sin = zeile["dir"]
                if not _im(r, ausschluss_mm):
                    texte.append((wort, r, abs(cos) > 0.99 or abs(sin) > 0.99))
        linien = []
        for zeichnung in page.get_drawings():
            for element in zeichnung["items"]:
                if element[0] == "l":
                    linien.append((mm(element[1].x, element[1].y), mm(element[2].x, element[2].y)))
                elif element[0] == "re":
                    q = element[1]
                    ecken = [mm(q.x0, q.y0), mm(q.x1, q.y0), mm(q.x1, q.y1), mm(q.x0, q.y1)]
                    linien += list(zip(ecken, ecken[1:] + ecken[:1]))
    befunde = []
    kerne = [_kern(r) for _, r, _ in texte]
    for i, (wort, r, achsparallel) in enumerate(texte):
        for j in range(i + 1, len(texte)):
            if _ueberlappt(kerne[i], kerne[j]):  # Kern gegen Kern: Zeilenabstand des Textrahmens zählt nicht
                befunde.append(Befund("text_ueber_text", wort, r, texte[j][0]))
        # schräge Schrift an ihrer Hinweislinie (R4, Ø6): achsparalleles Rechteck schließt die Linie ein → nur Text gegen Text
        if achsparallel and any(_schneidet(a, b, kerne[i]) for a, b in linien):
            befunde.append(Befund("linie_durch_text", wort, r))
    return befunde


def ausserhalb(zahlen: list[tuple[str, float, float, float, str]], feld: tuple, sperren: list[tuple],
               hoehe: float = 3.5) -> list[Befund]:
    """Maßzahlen, die das Zeichenfeld verlassen oder in einem Sperrbereich (Schriftfeld) liegen. `pruefe_pdf` lässt Rand
    und Schriftfeld bewusst aus; eine dorthin gerückte Zahl fiele sonst durch. `zahlen`: (Name, Mitte x, Mitte y,
    Länge entlang der Maßlinie, Richtung h|v) in Blatt-mm."""
    aus = []
    for name, x, y, laenge, richtung in zahlen:
        dx, dy = (laenge / 2, hoehe / 2) if richtung == "h" else (hoehe / 2, laenge / 2)
        r = (x - dx, y - dy, x + dx, y + dy)
        if r[0] < feld[0] or r[1] < feld[1] or r[2] > feld[2] or r[3] > feld[3] or _im(r, sperren):
            aus.append(Befund("ausserhalb", name, r))
    return aus
