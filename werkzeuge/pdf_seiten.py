"""Datenblatt-PDF lesen: Seitentext, ganze Seiten oder Ausschnitte als PNG; ohne SolidWorks.

Herkunft: SWKI-13 (Retro AP 6.8 Etappe 4, Punkt 7) – ersetzt die Wegwerf-venv mit PyMuPDF.
Braucht die optionale Gruppe pdf: .venv\\Scripts\\python.exe -m pip install -e ".[pdf]" (setup\\einrichten.ps1 tut das).

Aufruf: .venv\\Scripts\\python.exe -m werkzeuge.pdf_seiten <modus> <pdf> …
  text       <pdf> [--seiten 1,3-5]                                       Text je Seite nach stdout
  seite      <pdf> <ordner> [--seiten 2-] [--dpi 150]                     ganze Seiten als <name>_s<n>.png
  ausschnitt <pdf> <ordner> --seite N --rechteck X0 Y0 X1 Y1 [--dpi 300]   Bereich in Prozent der Seite (0 0 = oben links)
                                                                           als <name>_s<n>_x<X0>-<X1>_y<Y0>-<Y1>.png
Seiten zählen ab 1. Vorgehen für Belege: erst text bzw. seite (Überblick), dann ausschnitt mit hoher Auflösung.
"""

import argparse
import sys
from pathlib import Path

INSTALLATION = 'PyMuPDF fehlt: .venv\\Scripts\\python.exe -m pip install -e ".[pdf]"'


def _pymupdf():
    try:
        import pymupdf
    except ImportError as e:
        raise SystemExit(INSTALLATION) from e
    return pymupdf


def seitenliste(angabe: str | None, anzahl: int) -> list[int]:
    """'3,1-2' → [3, 1, 2], '2-' → bis zur letzten Seite, None → alle Seiten (ab 1)."""
    if angabe is None:
        return list(range(1, anzahl + 1))
    seiten = []
    for teil in angabe.split(","):
        von, strich, bis = teil.strip().partition("-")
        try:
            a = int(von)
            b = (int(bis) if bis else anzahl) if strich else a
        except ValueError:
            raise ValueError(f"Seitenangabe {teil!r} ist keine Zahl bzw. kein Bereich") from None
        if not 1 <= a <= b <= anzahl:
            raise ValueError(f"Seite {teil!r} liegt nicht in 1–{anzahl} oder der Bereich ist leer")
        seiten += range(a, b + 1)
    return seiten


def seitentext(pdf: Path, seiten: str | None = None) -> list[tuple[int, str]]:
    """[(Seitennummer, Text)] in der angegebenen Reihenfolge."""
    with _pymupdf().open(pdf) as doc:
        return [(n, doc[n - 1].get_text()) for n in seitenliste(seiten, doc.page_count)]


def seitenbilder(pdf: Path, ordner: Path, seiten: str | None = None, dpi: int = 150) -> list[Path]:
    """Ganze Seiten als PNG <pdf-name>_s<n>.png in ordner (wird angelegt)."""
    pdf, ordner = Path(pdf), Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    pfade = []
    with _pymupdf().open(pdf) as doc:
        for n in seitenliste(seiten, doc.page_count):
            p = ordner / f"{pdf.stem}_s{n}.png"
            doc[n - 1].get_pixmap(dpi=dpi).save(p)
            pfade.append(p)
    return pfade


def ausschnitt(pdf: Path, seite: int, rechteck: tuple[float, float, float, float], ordner: Path,
               dpi: int = 300) -> Path:
    """Bereich (X0, Y0, X1, Y1) in Prozent von Seitenbreite/-höhe, Ursprung oben links, als PNG in ordner."""
    x0, y0, x1, y1 = rechteck
    if not (0 <= x0 < x1 <= 100 and 0 <= y0 < y1 <= 100):
        raise ValueError(f"Rechteck {rechteck}: verlangt 0 ≤ X0 < X1 ≤ 100 und 0 ≤ Y0 < Y1 ≤ 100 (Prozent)")
    pdf, ordner = Path(pdf), Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    pymupdf = _pymupdf()
    with pymupdf.open(pdf) as doc:
        (n,) = seitenliste(str(seite), doc.page_count)
        s = doc[n - 1]
        b, h = s.rect.width, s.rect.height
        clip = pymupdf.Rect(b * x0 / 100, h * y0 / 100, b * x1 / 100, h * y1 / 100)  # page.rect beginnt bei 0, 0
        p = ordner / f"{pdf.stem}_s{n}_x{x0:g}-{x1:g}_y{y0:g}-{y1:g}.png"
        s.get_pixmap(dpi=dpi, clip=clip).save(p)
    return p


def _bildzeile(p: Path) -> str:
    d = p.read_bytes()
    return f"{p}  ({int.from_bytes(d[16:20], 'big')} × {int.from_bytes(d[20:24], 'big')} px)"


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(prog="werkzeuge.pdf_seiten", description=__doc__.splitlines()[0],
                                epilog="Modi: text, seite, ausschnitt – je mit --help.")
    modi = a.add_subparsers(dest="modus", required=True, metavar="{text,seite,ausschnitt}")
    t = modi.add_parser("text", help="Text je Seite nach stdout")
    t.add_argument("pdf", type=Path)
    t.add_argument("--seiten", help="z. B. 1,3-5 oder 2- (Standard: alle)")
    s = modi.add_parser("seite", help="ganze Seiten als PNG in einen Ordner")
    s.add_argument("pdf", type=Path)
    s.add_argument("ordner", type=Path, help="Ausgabeordner (wird angelegt), z. B. im Scratchpad")
    s.add_argument("--seiten", help="z. B. 1,3-5 oder 2- (Standard: alle)")
    s.add_argument("--dpi", type=int, default=150, help="Auflösung (Standard 150)")
    c = modi.add_parser("ausschnitt", help="Bereich einer Seite als PNG, Rechteck in Prozent der Seite")
    c.add_argument("pdf", type=Path)
    c.add_argument("ordner", type=Path, help="Ausgabeordner (wird angelegt)")
    c.add_argument("--seite", type=int, required=True)
    c.add_argument("--rechteck", type=float, nargs=4, required=True, metavar=("X0", "Y0", "X1", "Y1"),
                   help="Prozent von Breite/Höhe, 0 0 = oben links, 100 100 = unten rechts")
    c.add_argument("--dpi", type=int, default=300, help="Auflösung (Standard 300)")
    args = a.parse_args(argv)
    try:
        if args.modus == "text":
            for n, text in seitentext(args.pdf, args.seiten):
                print(f"===== Seite {n} =====\n{text.rstrip()}\n")
        elif args.modus == "seite":
            for p in seitenbilder(args.pdf, args.ordner, args.seiten, args.dpi):
                print(_bildzeile(p))
        else:
            print(_bildzeile(ausschnitt(args.pdf, args.seite, tuple(args.rechteck), args.ordner, args.dpi)))
    except ValueError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
