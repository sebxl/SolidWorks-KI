"""Paket Konstruktionsstil: volumen: auto mit Verrundung senkrechter Kanten und Fase am Bohrungseintritt."""

import math

import pytest

from swki.pruefung.geometrie import volumen_auto

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}
VOLL = 100 * 60 * 20
FLAECHE = {"feature": "f1", "flaeche": "+y"}
TASCHE = {"id": "t1", "typ": "schnitt", "skizze": {"ebene": FLAECHE, "elemente": [
    {"rechteck": {"mitte": [-20, 0], "breite": 40, "hoehe": 20}}]}, "ende": {"typ": "blind", "tiefe": 10}}
RUND = {"id": "r1", "typ": "verrundung", "kanten": [{"feature": "t1", "auswahl": "senkrechte_kanten"}], "radius": "=R"}


def _v(*features, parameter=None):
    return volumen_auto({"art": "teil", "name": "T", "parameter": parameter or {"R": 3}, "features": [PLATTE, *features]})


def test_verrundung_tasche():
    v, grund = _v(TASCHE, RUND)
    assert grund == "analytisch"
    assert v == pytest.approx(VOLL - (800 - (4 - math.pi) * 9) * 10)


def test_verrundung_aussenecken_platte():
    rund = {"id": "r1", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": 5}
    v, _ = _v(rund)
    assert v == pytest.approx(VOLL - (4 - math.pi) * 25 * 20)


def test_verrundung_polygon():
    poly = {"id": "t1", "typ": "schnitt", "skizze": {"ebene": FLAECHE, "elemente": [
        {"polygon": {"punkte": [[-40, -10], [0, -10], [0, 10], [-40, 10]]}}]}, "ende": {"typ": "blind", "tiefe": 10}}
    v, _ = _v(poly, RUND)
    assert v == pytest.approx(VOLL - (800 - (4 - math.pi) * 9) * 10)


def test_verrundung_gespiegelt():
    spiegel = {"id": "s1", "typ": "spiegeln", "features": ["t1", "r1"], "ebene": "rechts"}
    v, _ = _v(TASCHE, RUND, spiegel)
    assert v == pytest.approx(VOLL - 2 * (800 - (4 - math.pi) * 9) * 10)


def test_verrundung_nahe_offen():
    v, grund = _v(TASCHE, {"id": "r1", "typ": "verrundung", "kanten": [{"nahe": [0, 20, 0]}], "radius": 3})
    assert v is None and "r1" in grund and "verrundung" in grund


def test_verrundung_auf_skizzenradius_offen():
    tasche = {**TASCHE, "skizze": {**TASCHE["skizze"], "elemente": [
        {"rechteck": {"mitte": [-20, 0], "breite": 40, "hoehe": 20, "radius": 2}}]}}
    v, grund = _v(tasche, RUND)
    assert v is None and "r1" in grund


def _loch(**w):
    return {"id": "f2", "typ": "bohrung", "flaeche": FLAECHE, "positionen": [[-20, 0], [20, 0]], "durchmesser": 6,
            "durch": True, **w}


def test_bohrungsfase_volumen():
    v, _ = _v(_loch(fase=0.5))
    c = 0.5
    assert v == pytest.approx(VOLL - 2 * (math.pi * 9 * 20 + math.pi * c * (3 * c + c * c / 3)))


def test_gewinde_nenn_volumen():
    nb = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": FLAECHE,
          "positionen": [[0, 0]], "tiefe": 15, "gewindetiefe": 12}
    ohne, _ = _v(nb)
    mit, _ = _v({**nb, "fase": "nenn"})
    assert ohne - mit == pytest.approx(math.pi * 0.6 * (3.4 * 0.6 + 0.36 / 3))


def test_muster_mit_fase():
    muster = {"id": "m1", "typ": "muster_linear", "features": ["f2"], "richtung1": {"achse": "x", "abstand": 10, "anzahl": 3}}
    loch = {**_loch(fase=0.5), "positionen": [[-40, 0]]}
    v, _ = _v(loch, muster)
    c = 0.5
    assert v == pytest.approx(VOLL - 3 * (math.pi * 9 * 20 + math.pi * c * (3 * c + c * c / 3)))
