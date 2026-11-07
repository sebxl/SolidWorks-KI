"""Paket Konstruktionsstil: Was der Schnellbau (noch, Stufe C3a) nicht kann, meldet er – nie still."""

import pytest

pytest.importorskip("build123d")

from swki.schnellbau.fehler import NICHT_UNTERSTUETZT, SchnellbauFehler  # noqa: E402
from swki.schnellbau.teil import baue  # noqa: E402

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}


def test_fase_feld_meldung():
    loch = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 0]],
            "durchmesser": 6, "durch": True, "fase": 0.5}
    teil = baue({"art": "teil", "name": "T", "features": [PLATTE, loch]})
    assert any("f2" in m and "fase" in m for m in teil.meldungen)


def test_austragung_nicht_unterstuetzt():
    sweep = {"id": "f2", "typ": "austragung", "profil": {"ebene": "rechts", "elemente": []}, "pfad": {}}
    with pytest.raises(SchnellbauFehler) as e:
        baue({"art": "teil", "name": "T", "features": [PLATTE, sweep]})
    assert e.value.code == NICHT_UNTERSTUETZT
