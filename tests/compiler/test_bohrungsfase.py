"""Paket Konstruktionsstil: Fase am Bohrungseintritt – Kantenwahl und Maße ohne SolidWorks."""

import pytest

from swki.compiler.fehler import REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.compiler.handler.kanten import eintrittskanten
from swki.spec.bohrungsfase import eintritt_radius, fase_abstand


def test_eintritt_groesster_kreis():
    kreise = [((0.0, 20.0, 0.0), 3.3, "loch"), ((0.0, 20.0, 0.0), 5.5, "senkung"), ((0.0, 13.2, 0.0), 5.5, "grund"),
              ((20.0, 20.0, 0.0), 5.5, "nachbar")]
    assert eintrittskanten(kreise, [(0.0, 20.0, 0.0)], 0.01) == ["senkung"]


def test_eintritt_je_position():
    kreise = [((x, 0.0, 0.0), 3.4, f"k{x:g}") for x in (0.0, 20.0, 40.0)]
    assert eintrittskanten(kreise, [(40.0, 0.0, 0.0), (0.0, 0.0, 0.0)], 0.01) == ["k40", "k0"]


def test_eintritt_fehlt():
    with pytest.raises(BauFehler) as e:
        eintrittskanten([((5.0, 0.0, 0.0), 3.0, "k")], [(0.0, 0.0, 0.0)], 0.01)
    assert e.value.code == REFERENZ_NICHT_GEFUNDEN


def _nb(art, groesse, **w):
    return {"id": "f2", "typ": "normbohrung", "art": art, "groesse": groesse, "positionen": [[0, 0]], "durch": True, **w}


def test_fase_abstand_nenn_m8():
    assert fase_abstand(_nb("gewinde", "M8", fase="nenn"), {}) == pytest.approx(0.6)
    assert fase_abstand(_nb("gewinde", "M10x1", fase="nenn"), {}) == pytest.approx(0.5)


def test_fase_abstand_wert_und_ohne():
    assert fase_abstand(_nb("stift", 8, fase="=FB"), {"FB": 0.5}) == 0.5
    assert fase_abstand(_nb("stift", 8), {}) is None


def test_eintritt_radius():
    assert eintritt_radius(_nb("gewinde", "M8"), {}) == pytest.approx(3.4)
    assert eintritt_radius(_nb("zylinderschraube", "M6"), {}) == pytest.approx(5.5)
    assert eintritt_radius(_nb("stift", 8), {}) == pytest.approx(4.0)
    bohrung = {"typ": "bohrung", "durchmesser": 6.6, "senkung": {"durchmesser": "=DS", "tiefe": 6}}
    assert eintritt_radius(bohrung, {"DS": 11}) == pytest.approx(5.5)
    assert eintritt_radius({"typ": "bohrung", "durchmesser": 6}, {}) == 3.0
