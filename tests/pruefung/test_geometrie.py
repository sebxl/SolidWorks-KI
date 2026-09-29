import math

import pytest

from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand, volumen_auto

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
])
def test_volumen_nicht_berechenbar(feature, grund):
    spec = {"features": [_extr("f1", "extrusion", [{"rechteck": {"mitte": [0, 0], "breite": 1, "hoehe": 1}}], 1),
                         feature]}
    volumen, text = volumen_auto(spec)
    assert volumen is None and text.startswith(grund)
