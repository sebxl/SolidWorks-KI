"""Lage eines verzahnung-Features im Teil (swki.verzahnung.verzahnung_im_teil), ohne SolidWorks."""

import pytest

from swki.compiler.skizze import modellpunkt
from swki.verzahnung import Stirnrad, Zahnstange, verzahnung_im_teil

RAD = {"id": "z1", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": 30}}, "mitte": [5, -2],
       "modul": 2, "zaehne": 20, "breite": 16, "zahndickenabmass": -0.05, "winkel": 90}


@pytest.mark.parametrize("orientierung", ["vorne", "oben", "rechts"])
def test_modell_wie_skizze(orientierung):
    f = {**RAD, "ebene": {"versatz": {"ebene": orientierung, "abstand": 30}}}
    vz = verzahnung_im_teil(f, {})
    assert vz.modell((5, -2)) == pytest.approx(modellpunkt(orientierung, 5, -2, 30))


def test_stirnrad():
    vz = verzahnung_im_teil(RAD, {})
    assert vz.geo == Stirnrad(2, 20, -0.05)
    assert vz.bezugspunkt == pytest.approx((5, -2, 30))
    assert vz.zahnrichtung == pytest.approx((0, 1, 0))  # winkel 90°: Zahn 1 auf +v
    assert vz.normale == (0.0, 0.0, 1.0) and vz.breite == (30, 46)


def test_umkehren_dreht_den_breitenbereich():
    assert verzahnung_im_teil({**RAD, "umkehren": True}, {}).breite == (14, 30)


def test_zahnstange_oben_kopf_unten():
    f = {"id": "z2", "art": "zahnstange", "ebene": "oben", "mitte": ["=A", 0], "modul": 2, "zaehne": 9, "breite": 20,
         "zahndickenabmass": -0.05, "kopf": "-v"}
    vz = verzahnung_im_teil(f, {"A": 7})
    assert vz.geo == Zahnstange(2, 9, -0.05)
    assert vz.bezugspunkt == pytest.approx((7, 0, 0))
    assert vz.zahnrichtung == (1.0, 0.0, 0.0)
    assert vz.kopfrichtung == pytest.approx((0, 0, 1))  # oben: v = −z, Kopf −v = +z
