"""Paket Konstruktionsstil im Schnellbau (Stufe C3a): Bohrungsfase; was noch fehlt, meldet er – nie still."""

import math

import pytest

pytest.importorskip("build123d")

from swki.schnellbau.fehler import NICHT_UNTERSTUETZT, SchnellbauFehler  # noqa: E402
from swki.schnellbau.teil import baue  # noqa: E402
from swki.spec.normen import normmasse  # noqa: E402

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}
OBEN = {"feature": "f1", "flaeche": "+y"}


def _spec(*features):
    return {"art": "teil", "name": "T", "features": [PLATTE, *features]}


def _kegel(r, c):
    """Volumen, das die Fase über dem Zylinder wegnimmt: π·c·(r·c + c²/3)."""
    return math.pi * c * (r * c + c * c / 3)


def test_fase_bohrung_durch():
    loch = {"id": "f2", "typ": "bohrung", "flaeche": OBEN, "positionen": [[-20, 0], [20, 0]],
            "durchmesser": 6, "durch": True, "fase": 0.5}
    teil = baue(_spec(loch))
    soll = 100 * 60 * 20 - 2 * (math.pi * 3 ** 2 * 20 + math.pi * 0.5 * (3 * 0.5 + 0.5 ** 2 / 3))
    assert teil.solid.volume == pytest.approx(soll, rel=1e-9)
    assert teil.meldungen == []


def test_fase_nenn_gewinde():
    loch = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": OBEN,
            "positionen": [[0, 0]], "tiefe": 12, "gewindetiefe": 10}
    r = normmasse("gewinde", "M8")["kernloch"] / 2
    c = (8 - 2 * r) / 2
    ohne = baue(_spec(loch)).solid.volume
    mit = baue(_spec(dict(loch, fase="nenn"))).solid.volume
    assert ohne - mit == pytest.approx(_kegel(r, c), rel=1e-9)


def test_fase_zylinderschraube_am_senkungsrand():
    loch = {"id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M6", "flaeche": OBEN,
            "positionen": [[0, 0]], "durch": True}
    r = normmasse("zylinderschraube", "M6")["senkung_d"] / 2
    ohne = baue(_spec(loch)).solid.volume
    mit = baue(_spec(dict(loch, fase=0.5))).solid.volume
    assert ohne - mit == pytest.approx(_kegel(r, 0.5), rel=1e-9)


MUSTER = {"id": "f3", "typ": "muster_linear", "features": ["f2"], "richtung1": {"achse": "x", "abstand": 20, "anzahl": 3}}


def test_fase_im_muster():
    loch = {"id": "f2", "typ": "bohrung", "flaeche": OBEN, "positionen": [[-20, 0]], "durchmesser": 6, "durch": True}
    ohne = baue(_spec(loch, MUSTER)).solid.volume
    mit = baue(_spec(dict(loch, fase=0.5), MUSTER)).solid.volume
    assert ohne - mit == pytest.approx(3 * _kegel(3, 0.5), rel=1e-9)


def test_fase_ohne_bohrungen():
    loch = {"id": "f2", "typ": "bohrung", "flaeche": OBEN, "positionen": [[-20, 0]], "durchmesser": 6, "durch": True,
            "fase": 0.5}
    teil = baue(_spec(loch, MUSTER), bohrungen=False)
    assert teil.solid.volume == pytest.approx(100 * 60 * 20, rel=1e-9)
    assert "f2" in teil.uebersprungen and "f3" in teil.uebersprungen


def test_austragung_nicht_unterstuetzt():
    sweep = {"id": "f2", "typ": "austragung", "profil": {"ebene": "rechts", "elemente": []}, "pfad": {}}
    with pytest.raises(SchnellbauFehler) as e:
        baue({"art": "teil", "name": "T", "features": [PLATTE, sweep]})
    assert e.value.code == NICHT_UNTERSTUETZT
