"""Lesbarkeit einer Zeichnung am PDF prüfen (Z1.3 Stufe 2, Nachtrag; Nutzer 18.11.2026: Maß auf der Schnittkennzeichnung,
Maßzahlen von Linien gekreuzt). Geprüft wird, was der Leser sieht: Texte mit ihren Rechtecken und alle Liniensegmente
aus dem PDF (pymupdf), nicht die API-Rückgabe.

- `text_ueber_text`: zwei Texte überlappen.
- `linie_durch_text`: ein Liniensegment kreuzt den Kern einer Maßzahl. Die eigene Maßlinie unter der Zahl berührt nur
  den Rand; deshalb zählt nur der Kern des Textrechtecks (innen um einen Teil der Höhe verkleinert).

Koordinaten der Befunde in Blatt-mm, Ursprung links unten (wie `IAnnotation.SetPosition2`).
"""

import math
import re
from dataclasses import dataclass
from pathlib import Path

PT_MM = 25.4 / 72
KERN = 0.22  # Anteil der Texthöhe, um den das Rechteck oben/unten verkleinert wird (Abstand zur eigenen Maßlinie)
GLYPHE_MM = 0.5  # kürzer gezeichnete Striche in einem Text sind Teil eines Symbols (Hüllkreis Ⓔ)


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


def _quer_durch(a, b, o, d, u, v) -> bool:
    """Kreuzt die Strecke a–b das gedrehte Rechteck [u0, u1] × [v0, v1] (u entlang d ab o, v senkrecht nach links) und
    ist sie nicht parallel zu d (mehr als 10°)?"""
    sx, sy = b[0] - a[0], b[1] - a[1]
    laenge = (sx * sx + sy * sy) ** 0.5
    if laenge < 1e-9 or abs(sx * d[1] - sy * d[0]) / laenge < 0.17:
        return False

    def lokal(p):
        px, py = p[0] - o[0], p[1] - o[1]
        return (px * d[0] + py * d[1], -px * d[1] + py * d[0])

    return _schneidet(lokal(a), lokal(b), (u[0], v[0], u[1], v[1]))


def _ueberlappt(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _kern(r):
    """Textrechteck ohne Ober-/Unterlänge und Zeilenabstand; bei hochgestellter Schrift gilt die kurze Seite als Höhe."""
    h = min(r[2] - r[0], r[3] - r[1])
    dx, dy = (0.1 * h, KERN * h) if r[2] - r[0] >= r[3] - r[1] else (KERN * h, 0.1 * h)
    return (r[0] + dx, r[1] + dy, r[2] - dx, r[3] - dy)


def _im(r, bereiche) -> bool:
    return any(_ueberlappt(r, b) for b in bereiche)


def texte(pdf: Path, seite: int = 0) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Alle Textzeilen der Seite mit ihrem Rechteck in Blatt-mm (wie `pruefe_pdf` sie liest; Hinweise vermessen)."""
    import pymupdf

    with pymupdf.open(pdf) as doc:
        page = doc[seite]
        hoehe_mm = page.rect.height * PT_MM
        aus = []
        for block in page.get_text("rawdict")["blocks"]:
            for zeile in block.get("lines", []):
                wort = "".join(c["c"] for s in zeile["spans"] for c in s["chars"]).strip()
                if wort:
                    x0, y0, x1, y1 = zeile["bbox"]
                    aus.append((wort, (x0 * PT_MM, hoehe_mm - y1 * PT_MM, x1 * PT_MM, hoehe_mm - y0 * PT_MM)))
    return aus


def _zellteiler(a, b, r) -> bool:
    """Senkrechte Trennlinie einer Rahmenzelle durch den Text eines Toleranzrahmens (Z1.3 Stufe 4, Live 27.11.: das PDF
    liest „0,05 A“ als eine Zeile, der Strich zwischen Wert- und Bezugszelle kreuzt sie): senkrecht, innerhalb der
    Textbreite, über die ganze Schrifthöhe, nicht länger als die Rahmenhöhe (Texthöhe + 6 mm)."""
    h = r[3] - r[1]
    return (abs(a[0] - b[0]) < 0.05 and r[0] < a[0] < r[2] and abs(a[1] - b[1]) <= h + 6.0
            and min(a[1], b[1]) <= r[1] + 0.3 * h and max(a[1], b[1]) >= r[3] - 0.3 * h)


def _huelle(wort: str) -> bool:
    """Text mit dem Hüllsymbol `<MOD-EP>`: pymupdf liest es als einzelnes „E“ (Live 27.11.: „32,00 k6 E“)."""
    return re.search(r"(^|\s)E(\s|$)", wort) is not None


def _kreisstrich(a, b, r) -> bool:
    """Stück des Kreises um das E (Live 27.11.: Kreis aus 0,25 mm langen Strichen) innerhalb des Textrechtecks."""
    return (math.dist(a, b) < GLYPHE_MM
            and all(r[0] - 0.3 <= p[0] <= r[2] + 0.3 and r[1] - 0.3 <= p[1] <= r[3] + 0.3 for p in (a, b)))


def pruefe_pdf(pdf: Path, ausschluss_mm: list[tuple] | None = None, seite: int = 0,
               rahmen_texte: tuple[str, ...] = ()) -> list[Befund]:
    """`rahmen_texte`: Texte von Toleranzrahmen; deren eigene Zelltrennlinien zählen nicht (`_zellteiler`). Ebenso
    zählen die kurzen Striche des Hüllkreises in Texten mit Ⓔ nicht (`_kreisstrich`)."""
    import pymupdf

    ausschluss_mm = ausschluss_mm or []
    with pymupdf.open(pdf) as doc:
        page = doc[seite]
        hoehe_mm = page.rect.height * PT_MM

        def mm(x, y):
            return (x * PT_MM, hoehe_mm - y * PT_MM)

        texte = []  # (Text, Rechteck mm, achsparallel, gedrehter Kern oder None)
        for block in page.get_text("rawdict")["blocks"]:
            for zeile in block.get("lines", []):
                zeichen = [c for s in zeile["spans"] for c in s["chars"]]
                wort = "".join(c["c"] for c in zeichen).strip()
                if not wort:
                    continue
                x0, y0, x1, y1 = zeile["bbox"]
                (ax, ay), (bx, by) = mm(x0, y1), mm(x1, y0)
                r = (ax, ay, bx, by)
                cos, sin = zeile["dir"]
                achsparallel = abs(cos) > 0.99 or abs(sin) > 0.99
                kern = None
                if not achsparallel:  # Kern in Schriftrichtung: Grundlinie bis Versalhöhe, eigene Hinweislinie darunter
                    groesse = zeile["spans"][0]["size"] * PT_MM
                    o = mm(*zeichen[0]["origin"])
                    d = (cos, -sin)  # PDF-y zeigt nach unten
                    laenge = max((mm(*c["origin"])[0] - o[0]) * d[0] + (mm(*c["origin"])[1] - o[1]) * d[1]
                                 for c in zeichen) + 0.55 * groesse
                    kern = (o, d, (0.1 * groesse, laenge - 0.1 * groesse), (0.15 * groesse, 0.6 * groesse))
                if not _im(r, ausschluss_mm):
                    texte.append((wort, r, achsparallel, kern))
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
    kerne = [_kern(r) for _, r, _, _ in texte]
    for i, (wort, r, achsparallel, gedreht) in enumerate(texte):
        for j in range(i + 1, len(texte)):
            if _ueberlappt(kerne[i], kerne[j]):  # Kern gegen Kern: Zeilenabstand des Textrahmens zählt nicht
                befunde.append(Befund("text_ueber_text", wort, r, texte[j][0]))
        if achsparallel and any(_schneidet(a, b, kerne[i]) for a, b in linien
                                if not (wort in rahmen_texte and _zellteiler(a, b, r))
                                and not (_huelle(wort) and _kreisstrich(a, b, r))):
            befunde.append(Befund("linie_durch_text", wort, r))
        # schräge Schrift an ihrer Hinweislinie (R4, Ø6; Nutzer 18.11.2026: lag auf Kanten): gedrehter Kern, Linien
        # parallel zur Schrift (die eigene Hinweislinie) zählen nicht
        elif gedreht and any(_quer_durch(a, b, *gedreht) for a, b in linien):
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
