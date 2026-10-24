"""Referenz Zentrieraufnahme (Paket Formschräge) ohne SolidWorks: gültig ohne Hinweis, Sollvolumen passt zur Rechnung."""

import importlib.util
from pathlib import Path

import pytest

from swki.formschraege import querschnitt_koeffizienten, volumen
from swki.spec.hinweise import hinweise
from swki.spec.laden import lade_spec

ORDNER = Path(__file__).parent / "zentrieraufnahme"


def _rechnung() -> dict[str, float]:
    modul_spec = importlib.util.spec_from_file_location("sollvolumen_zentrieraufnahme", ORDNER / "sollvolumen.py")
    modul = importlib.util.module_from_spec(modul_spec)
    modul_spec.loader.exec_module(modul)
    return modul.rechnung()


def test_gueltig_ohne_hinweis():
    spec = lade_spec(ORDNER / "zentrieraufnahme.yaml")
    assert hinweise(spec) == []
    assert [f["id"] for f in spec["features"]] == ["f1", "zapfen", "tasche", "trichter", "steg"]


def test_sollvolumen_aus_rechnung():
    spec = lade_spec(ORDNER / "zentrieraufnahme.yaml")
    assert sum(_rechnung().values()) == pytest.approx(spec["pruefung"]["volumen"]["soll"], abs=0.001)


def test_sollvolumen_unabhaengig_von_swki_formschraege():
    # Zapfen, Tasche und Trichter rechnet sollvolumen.py mit eigenen Formeln; sie müssen swki.formschraege bestätigen
    p = lade_spec(ORDNER / "zentrieraufnahme.yaml")["parameter"]
    teile = list(_rechnung().values())
    zapfen = querschnitt_koeffizienten({"kreis": {"durchmesser": p["DZ"]}}, {})
    tasche = querschnitt_koeffizienten({"rechteck": {"breite": p["TL"], "hoehe": p["TB"], "radius": p["TR"]}}, {})
    trichter = querschnitt_koeffizienten({"kreis": {"durchmesser": p["DR"]}}, {})
    assert teile[1] == pytest.approx(volumen(zapfen, p["HZ"], p["WZ"], "kleiner"))
    assert teile[3] == pytest.approx(-volumen(tasche, p["TT"], p["WT"], "kleiner"))
    assert teile[4] == pytest.approx(-volumen(trichter, p["H"], p["WR"], "groesser"))
