"""Befehl "swki zeichnen <spec>" (Zeichnungsableitung Z1.3)."""

from pathlib import Path

from swki.cli import ganzzahl_ab


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("zeichnen", help="Zeichnung des gebauten Teils (Stufe 1: Blatt und Ansichten, ohne Maße)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Vorgabe: letzter Lauf")

    def ausfuehren(a):
        from swki.zeichnung.zeichnen import zeichnen  # spät importiert: COM erst beim Aufruf

        return zeichnen(Path(a.spec), a.lauf)

    p.set_defaults(func=ausfuehren)
