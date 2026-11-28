"""Rauheitsfeld über dem Schriftfeld (Nutzer 28.11.2026): Kasten mit Rauheitssymbol (ISO 1302:2002, Feld a „Ra 3,2“)
und dem Hinweis „Alle Flächen ohne andere Angabe“ statt der Textzeile „Oberflächen ohne Angabe: Ra 3,2“."""

import pytest

from swki.zeichnung import sammelfeld as sf
from swki.zeichnung.toleranzangaben import sammelangaben
from tests.zeichnung.test_massplan import _lade_ref

FESTE = sammelangaben({})


def _zeilen_rechtecke(band, zeilen):
    """Geschätzte Rechtecke der umgebrochenen Sammelzeilen (2,5 mm je Zeichen, Zeilenabstand 4,55 mm)."""
    x, oben = band[0] + sf.SAMMEL_LINKS_MM, band[3]
    return [(x, oben - (i + 1) * sf.SAMMEL_ZEILENABSTAND_MM, x + len(z) * sf.SAMMEL_ZEICHEN_MM,
             oben - i * sf.SAMMEL_ZEILENABSTAND_MM) for i, z in enumerate(sf.umbrechen(zeilen))]


def _ueberlappt(a, b, tol=0.5):
    return a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol


@pytest.mark.parametrize("ref", [None, "zeichnung/spannplatte_z.yaml", "zeichnung/buchse_z.yaml"])
def test_rauheitsfeld_rechts_oben_ohne_ueberlappung_und_ohne_hoeheres_band(ref):
    """Das Band wird nicht höher als die Zeilen (Live 27.11.: 5 mm mehr kippten Format und Maßstab der Spannplatte);
    der Kasten steht rechtsbündig im Band, überdeckt keine Sammelzeile, Symbol und Hinweis liegen im Kasten."""
    zeilen = sammelangaben(_lade_ref(ref)) if ref else FESTE
    n = sf.sammel_zeilenzahl(zeilen)
    assert n == len(sf.umbrechen(zeilen))
    band = sf.sammelband("A3quer", n * sf.ZEILE_MM)
    feld = sf.rauheitsfeld(band, zeilen)
    x0, y0, x1, y1 = feld.rahmen
    assert (x1 - x0, y1 - y0) == sf.RAUHEITSFELD_MM and x1 == band[2] and y1 == band[3] and feld.zeile == 0
    assert y0 >= band[1] and x0 >= band[0]
    assert not any(_ueberlappt(r, feld.rahmen) for r in _zeilen_rechtecke(band, zeilen))
    sx, sy = feld.symbol
    assert x0 < sx - sf.SYMBOL_LINKS_MM and sx + sf.SYMBOL_RECHTS_MM < feld.hinweis[0]
    assert y0 < sy and sy + sf.SYMBOL_HOEHE_MM < y1
    hx, hy = feld.hinweis
    assert hy + sf.SAMMEL_OBERKANTE_MM < y1 and hy - sf.HINWEIS_UNTER_LAGE_MM > y0 and hx + 40.8 < x1


def test_lange_erste_zeilen_schieben_das_feld_nach_unten():
    zeilen = ["x" * 60, "y" * 30, "z" * 30, "w" * 30, "v" * 30]
    umbrochen, zeile = sf.sammel_aufteilung(zeilen)
    assert umbrochen == zeilen and zeile == 1
    lang = ["x" * 60, "y" * 60]
    assert sf.sammel_aufteilung(lang) == (lang, 2)
    # passt nirgends: der Kasten steht unter den Zeilen, das Band wächst um seine Höhe
    assert sf.sammel_zeilenzahl(lang) == 5   # 2 × 4,55 mm + 14 mm = 23,1 mm → 5 Zeilen à 5 mm


def test_frei_zeichen_neben_dem_feld():
    assert sf.frei_zeichen() == 42
