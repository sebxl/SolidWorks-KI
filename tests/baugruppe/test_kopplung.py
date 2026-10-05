"""Kopplungsrechnung ohne SolidWorks (Spec 4b §5): Lage, Zahnphase, Abrollen, Drehung, Eingriff, Graph, Übersetzung."""

import math

import pytest

from swki.baugruppe.bewegung import drehmatrix
from swki.baugruppe.kopplung import (Rad, Stange, drehe, eingriff, endlagen_wege, gekoppelte, in_baugruppe,
                                     phasenfehler, phasenwinkel, soll_drehungen, teilkreise, winkel_um)
from swki.baugruppe.modell import Quelle
from swki.verzahnung import Stirnrad, Zahnstange, verzahnung_im_teil

Z = (0.0, 0.0, 1.0)
EINS = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]


def _dreh(v, winkel, achse=Z):
    q = drehmatrix(achse, winkel)
    return tuple(sum(q[i][k] * v[k] for k in range(3)) for i in range(3))


def _rad(z, punkt=(0.0, 0.0, 0.0), zahn_grad=0.0, achse=Z, breite=(0.0, 10.0)):
    zahn = _dreh((1.0, 0.0, 0.0), zahn_grad, Z)
    return Rad(punkt, achse, zahn, Stirnrad(2.0, z, -0.05), breite)


def _stange(punkt=(0.0, 0.0, 0.0), z=20):
    return Stange(punkt, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), Z, Zahnstange(2.0, z, -0.05), (0.0, 20.0))


def test_winkel_um():
    assert math.degrees(winkel_um((1, 0, 0), (0, 1, 0), Z)) == pytest.approx(90)
    assert math.degrees(winkel_um((1, 0, 0), (0, -1, 0), Z)) == pytest.approx(-90)
    assert math.degrees(winkel_um((1, 0, 5), (0, 1, -3), Z)) == pytest.approx(90)  # Anteile entlang der Achse zählen nicht


def test_zahnrad_zahn_in_luecke():
    a = _rad(50)                                                   # Zahn 1 zeigt zu b
    b = _rad(25, punkt=(75.0, 0.0, 0.0), zahn_grad=180 + 360 / 50)  # Lücke von b zeigt zu a (halbe Teilung von b = 7,2°)
    assert phasenfehler(a, b) == pytest.approx(0.0, abs=1e-12)


def test_zahnrad_zahn_auf_zahn_halbe_teilung():
    a, b = _rad(50), _rad(25, punkt=(75.0, 0.0, 0.0), zahn_grad=180)
    assert abs(phasenfehler(a, b)) == pytest.approx(0.5)
    assert abs(phasenwinkel(a, b)) == pytest.approx(3.6)


@pytest.mark.parametrize(("za", "zb", "lage", "zahn_a", "zahn_b"), [
    (50, 25, (75.0, 0.0, 0.0), 13.0, 41.0), (20, 40, (0.0, 60.0, 5.0), -100.0, 3.0), (17, 23, (-28.0, -28.0, 0.0), 0.0, 0.0)])
def test_zahnrad_phase_herstellen_und_abrollen(za, zb, lage, zahn_a, zahn_b):
    a, b = _rad(za, zahn_grad=zahn_a), _rad(zb, punkt=lage, zahn_grad=zahn_b)
    w = phasenwinkel(a, b)
    a = Rad(a.punkt, a.achse, _dreh(a.zahn, w), a.geo, a.breite)
    assert phasenfehler(a, b) == pytest.approx(0.0, abs=1e-9)
    for theta in (5.0, 33.0, 400.0):  # Abrollen: a um +θ, b gegensinnig um θ·za/zb
        a2 = Rad(a.punkt, a.achse, _dreh(a.zahn, theta), a.geo, a.breite)
        b2 = Rad(b.punkt, b.achse, _dreh(b.zahn, -theta * za / zb), b.geo, b.breite)
        assert abs(phasenfehler(a2, b2)) == pytest.approx(0.0, abs=1e-9)


def test_zahnrad_gegenlaeufige_achse_misst_um_a():
    a = _rad(50)
    b = _rad(25, punkt=(75.0, 0.0, 0.0), zahn_grad=180 + 360 / 50, achse=(0.0, 0.0, -1.0))
    assert phasenfehler(a, b) == pytest.approx(0.0, abs=1e-12)


def test_zahnstange_zahn_in_luecke_und_abrollen():
    st = _stange()
    a = _rad(20, punkt=(0.0, 20.0, 0.0), zahn_grad=-90 + 9)  # Lücke des Ritzels (Teilung 18°) zeigt zur Zahnstange
    assert phasenfehler(a, st) == pytest.approx(0.0, abs=1e-12)
    for s in (3.0, 25.0, 130.0):  # Zahnstange um s nach +x, Ritzel rollt um s/r gegen den Uhrzeigersinn (σ = +1)
        st2 = _stange(punkt=(s, 0.0, 0.0))
        a2 = Rad(a.punkt, a.achse, _dreh(a.zahn, math.degrees(s / 20)), a.geo, a.breite)
        assert abs(phasenfehler(a2, st2)) == pytest.approx(0.0, abs=1e-9)


def test_zahnstange_phase_herstellen():
    st = _stange(punkt=(1.3, 0.0, 0.0))
    a = _rad(20, punkt=(40.0, 20.0, 7.0), zahn_grad=11.0)
    a = Rad(a.punkt, a.achse, _dreh(a.zahn, phasenwinkel(a, st)), a.geo, a.breite)
    assert phasenfehler(a, st) == pytest.approx(0.0, abs=1e-9)


def test_drehe_um_achse_durch_punkt():
    t = drehe(EINS, (10.0, 0.0, 0.0), Z, 90)
    assert t[0:3] == pytest.approx([0, 1, 0])        # Bild der x-Achse
    assert t[9:12] == pytest.approx([0.01, -0.01, 0])  # Ursprung (m): (0,0,0) um (10,0,0) gedreht
    assert t[12:] == EINS[12:]


def test_in_baugruppe_mit_lage():
    f = {"id": "z1", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": 30}}, "mitte": [0, 0],
         "modul": 2, "zaehne": 20, "breite": 16, "zahndickenabmass": -0.05}
    t = drehe(EINS, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90)  # Teil um y gedreht: Teil-z → Baugruppe +x
    t[9:12] = [0.1, 0.0, 0.0]
    rad = in_baugruppe(verzahnung_im_teil(f, {}), t)
    assert rad.punkt == pytest.approx((130.0, 0.0, 0.0))
    assert rad.achse == pytest.approx((1.0, 0.0, 0.0))
    assert rad.breite == pytest.approx((130.0, 146.0))


def test_eingriff_zahnrad():
    a, b = _rad(50), _rad(25, punkt=(75.0, 0.0, 5.0), breite=(5.0, 20.0))
    e = eingriff(a, b)
    assert e == {"achsen_parallel": True, "achsabstand": 75.0, "soll": 75.0, "ueberdeckung": 5.0, "im_bereich": True}
    assert eingriff(a, _rad(25, punkt=(75.0, 0.0, 0.0), breite=(-8.0, 0.0), achse=(0.0, 0.0, -1.0)))["ueberdeckung"] == 8.0


def test_eingriff_zahnstange():
    st = _stange(z=20)
    e = eingriff(_rad(20, punkt=(30.0, 20.0, 0.0), breite=(2.0, 18.0)), st)
    assert e == {"achsen_parallel": True, "achsabstand": 20.0, "soll": 20.0, "ueberdeckung": 16.0, "im_bereich": True}
    assert eingriff(_rad(20, punkt=(200.0, 20.0, 0.0)), st)["im_bereich"] is False


def test_teilkreise():
    assert teilkreise(Stirnrad(2, 50), Stirnrad(2, 25)) == (100, 50)
    assert teilkreise(Stirnrad(2, 20), Zahnstange(2, 9)) == (40, 0.0)


def _rad_spec(name, *zaehne):
    return {"art": "teil", "name": name, "features": [
        {"id": f"z{i}", "typ": "verzahnung", "art": "stirnrad", "ebene": "vorne", "mitte": [0, 0], "modul": 2,
         "zaehne": z, "breite": 10, "zahndickenabmass": -0.05} for i, z in enumerate(zaehne, start=1)]}


STANGE_SPEC = {"art": "teil", "name": "S", "features": [
    {"id": "z1", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": 2, "zaehne": 40,
     "breite": 10, "zahndickenabmass": -0.05}]}
TRIEB = {
    "komponenten": [{"id": "grundplatte", "fixiert": True}, {"id": "schlitten", "gruppe": "schieber"},
                    {"id": "zahnstange", "gruppe": "schieber"}, {"id": "ritzelwelle"}, {"id": "antriebswelle"}],
    "verknuepfungen": [
        {"id": "k1", "typ": "zahnstange", "a": {"komponente": "ritzelwelle", "feature": "z1"},
         "b": {"komponente": "zahnstange", "feature": "z1"}},
        {"id": "k2", "typ": "zahnrad", "a": {"komponente": "antriebswelle", "feature": "z1"},
         "b": {"komponente": "ritzelwelle", "feature": "z2"}}],
    "freiheitsgrade": {"schieber": 1, "ritzelwelle": "gekoppelt", "antriebswelle": "gekoppelt"},
}
QUELLEN = {"ritzelwelle": Quelle("teil", _rad_spec("R", 20, 25)), "antriebswelle": Quelle("teil", _rad_spec("A", 50)),
           "zahnstange": Quelle("teil", STANGE_SPEC)}


def test_gekoppelte():
    assert gekoppelte(TRIEB, {"schlitten", "zahnstange"}) == ["ritzelwelle", "antriebswelle"]
    assert gekoppelte(TRIEB, {"grundplatte"}) == []


def test_soll_drehungen_aus_der_uebersetzung():
    soll = soll_drehungen(TRIEB, QUELLEN, {"schlitten", "zahnstange"}, "abstand", 220.0, {})
    assert soll["ritzelwelle"] == pytest.approx(220 * 360 / (math.pi * 40))
    assert soll["antriebswelle"] == pytest.approx(220 * 360 / (math.pi * 40) * 25 / 50)


def test_soll_drehungen_mit_weg_aus_endlage():
    soll = soll_drehungen(TRIEB, QUELLEN, {"schlitten"}, "abstand", 220.0, {"zahnstange": 110.0})
    assert soll["ritzelwelle"] == pytest.approx(110 * 360 / (math.pi * 40))


def test_endlagen_wege():
    b = {"erwartet": {"endlagen": [{"komponente": "zahnstange", "verschiebung": ["=HUB", 0, 0]},
                                   {"komponente": "ritzelwelle", "drehung": {"achse": [0, 0, 1], "winkel": 5}}]}}
    assert endlagen_wege(b, {"HUB": 220}) == {"zahnstange": 220.0}
