import math

import pytest

from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand, normbohrung_volumen, volumen_auto
from swki.spec.normen import norm_von, normmasse

P = Messgeometrie("punkt", (0, 0, 0))
ACHSE_Y = Messgeometrie("achse", (125, 46, 100), (0, 1, 0))
ACHSE_Y2 = Messgeometrie("achse", (-125, 0, 100), (0, -1, 0))
EBENE_OBEN = Messgeometrie("ebene", (0, 46, 0), (0, 1, 0))
EBENE_UNTEN = Messgeometrie("ebene", (10, 0, 5), (0, -1, 0))


def test_abstaende():
    assert abstand(P, Messgeometrie("punkt", (3, 4, 0))) == pytest.approx(5)
    assert abstand(ACHSE_Y, ACHSE_Y2) == pytest.approx(250)
    assert abstand(P, ACHSE_Y) == pytest.approx(math.hypot(125, 100))
    assert abstand(EBENE_OBEN, EBENE_UNTEN) == pytest.approx(46)
    assert abstand(P, EBENE_OBEN) == pytest.approx(46)
    assert abstand(Messgeometrie("achse", (5, 0, 7), (1, 0, 0)), EBENE_OBEN) == pytest.approx(46)


def test_nicht_parallel():
    with pytest.raises(NichtMessbar):
        abstand(ACHSE_Y, Messgeometrie("achse", (0, 0, 0), (1, 0, 0)))
    with pytest.raises(NichtMessbar):
        abstand(EBENE_OBEN, Messgeometrie("ebene", (0, 0, 0), (1, 0, 0)))
    with pytest.raises(NichtMessbar):
        abstand(ACHSE_Y, EBENE_OBEN)


def _extr(fid, typ, elemente, tiefe):
    return {"id": fid, "typ": typ, "skizze": {"ebene": "oben", "elemente": elemente},
            "ende": {"typ": "blind", "tiefe": tiefe}}


def test_volumen_klotz_mit_tasche_und_bohrungen():
    spec = {"parameter": {"L": 100}, "features": [
        _extr("f1", "extrusion", [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}], 20),
        _extr("f2", "schnitt", [{"kreis": {"mitte": [0, 0], "durchmesser": 10}}], 5),
        {"id": "f3", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[1, 1], [2, 2]],
         "durchmesser": 4, "tiefe": 10, "senkung": {"durchmesser": 6, "tiefe": 2}},
        {"id": "f4", "typ": "muster_linear", "features": ["f3"], "richtung1": {"achse": "x", "abstand": 10, "anzahl": 3}},
        {"id": "f5", "typ": "spiegeln", "features": ["f2"], "ebene": "rechts"},
    ]}
    bohrung = math.pi * 4 * 10 + math.pi * (9 - 4) * 2
    erwartet = 100 * 60 * 20 - 2 * math.pi * 25 * 5 - 2 * bohrung * 3
    volumen, grund = volumen_auto(spec)
    assert grund == "analytisch" and volumen == pytest.approx(erwartet)


def test_volumen_rotation_nach_pappus():
    spec = {"features": [{
        "id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
            {"polygon": {"punkte": [[10, 0], [30, 0], [30, 40], [10, 40]]}},
            {"mittellinie": {"von": [0, -10], "bis": [0, 50]}}]},
    }, {
        "id": "f2", "typ": "rotation", "schnitt": True, "winkel": 180, "skizze": {"ebene": "vorne", "elemente": [
            {"polygon": {"punkte": [[25, 20], [30, 20], [30, 25], [25, 25]]}},
            {"mittellinie": {"von": [0, 0], "bis": [0, 1]}}]},
    }]}
    erwartet = math.pi * (30**2 - 10**2) * 40 - math.pi * (30**2 - 25**2) * 5 / 2
    assert volumen_auto(spec)[0] == pytest.approx(erwartet)


def test_volumen_kreismuster():
    spec = {"features": [
        _extr("f1", "extrusion", [{"polygon": {"punkte": [[0, 0], [10, 0], [0, 10]]}}], 2),
        {"id": "f2", "typ": "muster_kreis", "features": ["f1"], "achse": "y", "anzahl": 4},
    ]}
    assert volumen_auto(spec)[0] == pytest.approx(4 * 50 * 2)


@pytest.mark.parametrize(("feature", "grund"), [
    ({"id": "f2", "typ": "verrundung", "kanten": [{"nahe": [0, 0, 0]}], "radius": 1}, "f2: verrundung"),
    ({"id": "f2", "typ": "bohrung", "flaeche": {"nahe": [0, 0, 0]}, "positionen": [[0, 0]], "durchmesser": 4,
      "durch": True}, "f2: Bohrung durch"),
    ({"id": "f2", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"nahe": [0, 0, 0]},
      "positionen": [[0, 0]], "durch": True}, "f2: Normbohrung durch"),
    ({"id": "f2", "typ": "schnitt", "skizze": {"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 0.5}}]},
      "ende": {"typ": "versatz_von_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}, "abstand": 0.2}},
     "f2: ende versatz_von_flaeche"),
    ({"id": "f2", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"langloch": {"mitte": [5, 0], "laenge": 2, "breite": 1}}, {"mittellinie": {"von": [0, -1], "bis": [0, 1]}}]}},
     "f2: Rotation mit Rundungen"),
])
def test_volumen_nicht_berechenbar(feature, grund):
    spec = {"features": [_extr("f1", "extrusion", [{"rechteck": {"mitte": [0, 0], "breite": 1, "hoehe": 1}}], 1),
                         feature]}
    volumen, text = volumen_auto(spec)
    assert volumen is None and text.startswith(grund)


def _platte(*elemente, tiefe=10, parameter=None):
    return {"parameter": parameter or {}, "features": [_extr("f1", "extrusion", list(elemente), tiefe)]}


def test_volumen_rechteck_mit_eckradius():
    rechteck = {"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60, "radius": "=R"}}
    assert volumen_auto(_platte(rechteck, parameter={"R": 6}))[0] == pytest.approx((6000 - (4 - math.pi) * 36) * 10)


def test_volumen_polygon_mit_radien_konvex():
    quadrat = {"polygon": {"punkte": [[0, 0], [40, 0], [40, 40], [0, 40]], "radien": 5}}
    assert volumen_auto(_platte(quadrat))[0] == pytest.approx((1600 - 4 * (25 - 25 * math.pi / 4)) * 10)


L_FORM = [[0, 0], [40, 0], [40, 20], [20, 20], [20, 40], [0, 40]]


@pytest.mark.parametrize("umlauf", [1, -1])
def test_volumen_polygon_mit_konkaver_ecke(umlauf):
    # 5 konvexe Ecken R3 nehmen Material weg, die konkave Ecke (20, 20) R5 fügt hinzu – unabhängig vom Umlaufsinn
    polygon = {"polygon": {"punkte": L_FORM[::umlauf], "radien": [3, 3, 3, 5, 3, 3][::umlauf]}}
    erwartet = (1200 - 5 * (9 - 9 * math.pi / 4) + (25 - 25 * math.pi / 4)) * 10
    assert volumen_auto(_platte(polygon))[0] == pytest.approx(erwartet)


def test_volumen_langloch():
    langloch = {"langloch": {"mitte": [10, 5], "laenge": 30, "breite": 8, "winkel": 30}}
    assert volumen_auto(_platte(langloch))[0] == pytest.approx((30 * 8 + math.pi * 16) * 10)


def test_volumen_kontur_mit_bogen():
    kontur = {"kontur": {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                                       {"linie": [0, 30]}, {"linie": [0, 0]}]}}
    assert volumen_auto(_platte(kontur))[0] == pytest.approx((1200 + math.pi * 225 / 2) * 10)


def _mit_normbohrung(**nb):
    return {"features": [
        _extr("f1", "extrusion", [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}], 20),
        {"id": "f2", "typ": "normbohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, **nb},
    ]}


def test_volumen_gewinde_m8_wie_s9b():
    spec = _mit_normbohrung(art="gewinde", groesse="M8", positionen=[[-20, 0], [20, 0]], tiefe=16, gewindetiefe=12)
    volumen, grund = volumen_auto(spec)
    assert grund == "analytisch"
    assert volumen == pytest.approx(120000 - 2 * 605.80, abs=0.02)  # S9b Baustein 21: 605,80 mm³ je Loch


def test_volumen_stift_blind():
    d = normmasse("stift", 8)["durchmesser"]
    spec = _mit_normbohrung(art="stift", groesse=8, positionen=[[0, 0]], tiefe=10)
    spitze = math.pi * d**2 / 12 * (d / 2) / math.tan(math.radians(59))
    assert volumen_auto(spec)[0] == pytest.approx(120000 - (math.pi * d**2 / 4 * 10 + spitze))


@pytest.mark.parametrize(("art", "masse", "erwartet"), [
    ("zylinderschraube", {"durchgang": 9, "senkung_d": 15, "senkung_t": 9}, math.pi / 4 * (81 * 22 + (225 - 81) * 9)),
    ("senkschraube", {"durchgang": 6.6, "senkung_d": 12.4, "senkwinkel": 90},
     math.pi / 4 * 6.6**2 * (22 - 2.9) + math.pi * 2.9 / 12 * (12.4**2 + 12.4 * 6.6 + 6.6**2)),
])
def test_normbohrung_volumen_durch(art, masse, erwartet):
    assert normbohrung_volumen(art, masse, None, dicke=22) == pytest.approx(erwartet)


def _drehteil(*elemente):
    return {"features": [{"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        *elemente, {"mittellinie": {"von": [0, -10], "bis": [0, 10]}}]}}]}


def test_rotation_rechteck():
    # Ring: Querschnitt 10 × 20, Schwerpunkt 15 mm von der Achse
    spec = _drehteil({"rechteck": {"mitte": [15, 0], "breite": 10, "hoehe": 20}})
    assert volumen_auto(spec)[0] == pytest.approx(200 * 2 * math.pi * 15)


def test_rotation_kreis():
    # Torus: Kreis Ø4 im Abstand 20
    spec = _drehteil({"kreis": {"mitte": [20, 0], "durchmesser": 4}})
    assert volumen_auto(spec)[0] == pytest.approx(math.pi * 4 * 2 * math.pi * 20)


def test_rotation_mit_mehreren_profilen_nicht_berechenbar():
    spec = _drehteil({"rechteck": {"mitte": [15, 0], "breite": 10, "hoehe": 20}},
                     {"kreis": {"mitte": [15, 0], "durchmesser": 4}})
    volumen, grund = volumen_auto(spec)
    assert volumen is None and grund == "f1: Rotation mit mehreren Profilen nicht analytisch"


def test_volumen_referenz_traegt_nichts_bei():
    spec = {"features": [
        {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
            {"rechteck": {"mitte": [0, 0], "breite": 10, "hoehe": 20}}]}, "ende": {"typ": "blind", "tiefe": 5}},
        {"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"},
        {"id": "EINBAU_EBENE", "typ": "referenz", "ebene": {"basis": "oben"}},
    ]}
    volumen, grund = volumen_auto(spec)
    assert volumen == pytest.approx(1000.0) and grund == "analytisch"


# Durchgang durch eine Platte (Messstand Umbau 2): Skizze bzw. Fläche auf einer Fläche einer Extrusion mit fester Tiefe
# entlang derselben Achse → die Tiefe dieser Extrusion ist die Dicke.
def _platte_mit(feature):
    return {"parameter": {"T": 2}, "features": [
        _extr("f1", "extrusion", [{"rechteck": {"mitte": [0, 0], "breite": 75, "hoehe": 89}}], "=T"), feature]}


def test_volumen_schnitt_durch_alles_auf_plattenflaeche():
    langloch = {"langloch": {"mitte": [27, 39.5], "laenge": 3.1, "breite": 4.8, "winkel": 0}}
    spec = _platte_mit({"id": "f2", "typ": "schnitt", "ende": {"typ": "durch_alles"},
                        "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"}, "elemente": [langloch, langloch]}})
    flaeche = 3.1 * 4.8 + math.pi * 2.4**2
    volumen, grund = volumen_auto(spec)
    assert grund == "analytisch" and volumen == pytest.approx(75 * 89 * 2 - 2 * flaeche * 2)


def test_volumen_bohrung_und_normbohrung_durch_auf_plattenflaeche():
    bohrung = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "-y"}, "positionen": [[0, 0]],
               "durchmesser": 4, "durch": True}
    assert volumen_auto(_platte_mit(bohrung))[0] == pytest.approx(75 * 89 * 2 - math.pi * 4 * 2)
    stift = {"id": "f2", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
             "positionen": [[0, 0], [10, 0]], "durch": True}
    masse = normmasse("stift", 8, norm_von({}))
    erwartet = 75 * 89 * 2 - 2 * normbohrung_volumen("stift", masse, None, dicke=2)
    assert volumen_auto(_platte_mit(stift))[0] == pytest.approx(erwartet)


@pytest.mark.parametrize("flaeche", [{"feature": "f1", "flaeche": "+x"}, {"nahe": [0, 2, 0]}])
def test_volumen_durch_quer_oder_ohne_feature_bleibt_offen(flaeche):
    spec = _platte_mit({"id": "f2", "typ": "bohrung", "flaeche": flaeche, "positionen": [[0, 0]], "durchmesser": 1,
                        "durch": True})
    assert volumen_auto(spec)[0] is None


def test_volumen_innere_profile_werden_abgezogen():
    # Platte mit Langlöchern in derselben Skizze (so schreiben Agenten das Durchlicht): Löcher abziehen, nicht addieren
    langloch = [{"langloch": {"mitte": [sx * 27, sz * 39.5], "laenge": 3.1, "breite": 4.8, "winkel": 0}}
                for sx in (-1, 1) for sz in (-1, 1)]
    platte = _platte({"rechteck": {"mitte": [0, 0], "breite": 75, "hoehe": 89, "radius": 3}}, *langloch, tiefe=2)
    loch = 3.1 * 4.8 + math.pi * 2.4**2
    rechteck = 75 * 89 - (4 - math.pi) * 9
    assert volumen_auto(platte)[0] == pytest.approx((rechteck - 4 * loch) * 2)


def test_volumen_getrennte_profile_werden_addiert():
    zwei = _platte({"rechteck": {"mitte": [-30, 0], "breite": 20, "hoehe": 10}},
                   {"kreis": {"mitte": [30, 0], "durchmesser": 10}}, tiefe=1)
    assert volumen_auto(zwei)[0] == pytest.approx(200 + math.pi * 25)
