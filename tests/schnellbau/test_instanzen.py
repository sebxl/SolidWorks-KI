"""Schnellbau (Stufe C3a): Instanzpunkte und Achsrichtungen gemusterter und gespiegelter Bohrungen wie im Compiler,
Drehsinn des Kreismusters um die Bezugsachse (achse_y = −y), Ankerfehler über der Anzahl."""

import math

import pytest
import yaml

pytest.importorskip("build123d")

from build123d import Vector  # noqa: E402

from swki.schnellbau.baugruppe import Baugruppe  # noqa: E402
from swki.schnellbau.fehler import ANKER, SchnellbauFehler  # noqa: E402
from swki.schnellbau.teil import baue  # noqa: E402
from swki.spec.instanzen import anzahl_instanzen  # noqa: E402

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 120, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}
REIHE = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [[-40, 10]], "tiefe": 12, "gewindetiefe": 10, "fase": "nenn"}
MUSTER = {"id": "m1", "typ": "muster_linear", "features": ["f2"], "richtung1": {"achse": "x", "abstand": 20, "anzahl": 5}}
SPIEGEL = {"id": "s1", "typ": "spiegeln", "features": ["f2", "m1"], "ebene": "vorne"}
SPEC = {"art": "teil", "name": "T", "features": [PLATTE, REIHE, MUSTER, SPIEGEL]}


def _punkte(spec=SPEC, fid="f2"):
    return baue(spec).features[fid].punkte


def test_reihe_und_spiegel_wie_solidworks():
    p = _punkte()
    assert len(p) == 10
    assert p[4][0] == pytest.approx(40) and p[4][2] == pytest.approx(-10)
    assert p[5][0] == pytest.approx(-40) and p[5][2] == pytest.approx(10)
    assert p[9][0] == pytest.approx(40) and p[9][2] == pytest.approx(10)
    assert p[8][0] == pytest.approx(20)


def test_punkte_wie_anzahl_instanzen():
    assert len(_punkte()) == anzahl_instanzen(SPEC, "f2")


def test_richtungen_parallel_zu_punkten():
    info = baue(SPEC).features["f2"]
    assert len(info.richtungen) == len(info.punkte) == 10
    assert all(r == pytest.approx((0, -1, 0)) for r in info.richtungen)


def test_ohne_bohrungen_trotzdem_instanzpunkte():
    """Die Baugruppe baut Teile mit bohrungen=False; die Instanzpunkte müssen dort trotzdem stehen."""
    from swki.schnellbau.teil import Schnellbau
    teil = Schnellbau(SPEC, bohrungen=False).baue()
    assert len(teil.features["f2"].punkte) == 10 and len(teil.features["f2"].richtungen) == 10


def _scheibe(achse="y", anzahl=2, winkel=90):
    scheibe = {"id": "f1", "typ": "extrusion",
               "skizze": {"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 100}}]},
               "ende": {"typ": "blind", "tiefe": 10}}
    loch = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[30, 0]],
            "durchmesser": 8, "durch": True}
    kreis = {"id": "k1", "typ": "muster_kreis", "features": ["f2"], "achse": achse, "anzahl": anzahl, "winkel": winkel}
    return {"art": "teil", "name": "S", "features": [scheibe, loch, kreis]}


def test_kreismuster_dreht_um_bezugsachse():
    teil = baue(_scheibe())
    p = teil.features["f2"].punkte
    assert len(p) == 2
    assert p[0][0] == pytest.approx(30) and p[0][2] == pytest.approx(0, abs=1e-9)
    assert p[1][0] == pytest.approx(0, abs=1e-9) and p[1][2] == pytest.approx(30)
    assert not teil.solid.is_inside(Vector(0, 5, 30))      # hier sitzt die gedrehte Bohrung (SolidWorks: um −y)
    assert teil.solid.is_inside(Vector(0, 5, -30))


def test_richtung_gedrehter_kopie():
    wuerfel = {"id": "f1", "typ": "extrusion",
               "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 40}}]},
               "ende": {"typ": "blind", "tiefe": 40}}
    loch = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+x"}, "positionen": [[0, 20]],
            "durchmesser": 6, "tiefe": 5}
    kreis = {"id": "k1", "typ": "muster_kreis", "features": ["f2"], "achse": "y", "anzahl": 4}
    info = baue({"art": "teil", "name": "W", "features": [wuerfel, loch, kreis]}).features["f2"]
    assert info.richtungen[0] == pytest.approx((-1, 0, 0))
    # Drehung von (−1, 0, 0) um −y um 90°: (0, 0, −1)
    assert info.richtungen[1] == pytest.approx((0, 0, -1), abs=1e-9)
    assert info.richtungen[2] == pytest.approx((1, 0, 0), abs=1e-9)


def test_kreismuster_kopien_gemerkt():
    info = baue(_scheibe()).features["k1"]
    assert list(info.kopien) == ["f2"] and len(info.kopien["f2"][0]) == 1 and len(info.kopien["f2"][1]) == 1


def test_spiegel_quelle_bohrung_nimmt_nur_eigene_positionen():
    """spiegeln [f2, m1]: von f2 zählen nur die eigenen Positionen, von m1 dessen Kopien (nicht doppelt)."""
    spec = {"art": "teil", "name": "T", "features": [PLATTE, dict(REIHE, positionen=[[-40, 5], [-40, 15]]),
                                                     MUSTER, SPIEGEL]}
    assert len(_punkte(spec)) == anzahl_instanzen(spec, "f2") == 2 + 2 * 4 + (2 + 2 * 4)


def _baugruppe(tmp_path, instanz):
    (tmp_path / "platte.yaml").write_text(yaml.safe_dump(SPEC), encoding="utf-8")
    bolzen = {"art": "teil", "name": "B", "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 6}}]},
         "ende": {"typ": "blind", "tiefe": 10}},
        {"id": "r1", "typ": "referenz", "achse": "y"}]}
    (tmp_path / "bolzen.yaml").write_text(yaml.safe_dump(bolzen), encoding="utf-8")
    bg = {"art": "baugruppe", "name": "G",
          "komponenten": [{"id": "platte", "quelle": {"teil": "platte.yaml"}, "fixiert": True},
                          {"id": "bolzen", "quelle": {"teil": "bolzen.yaml"}}],
          "verknuepfungen": [{"id": "v1", "typ": "konzentrisch",
                              "a": {"komponente": "platte", "feature": "f2", "instanz": instanz, "achse": True},
                              "b": {"komponente": "bolzen", "referenz": "r1"}}]}
    return Baugruppe(bg, ordner=tmp_path)


def test_instanz_ueber_anzahl_ist_ankerfehler(tmp_path):
    with pytest.raises(SchnellbauFehler) as e:
        _baugruppe(tmp_path, 11)
    assert e.value.code == ANKER
    meldung = str(e.value)
    assert "platte" in meldung and "f2" in meldung and "11" in meldung and "10" in meldung


def test_instanz_auf_musterkopie(tmp_path):
    bg = _baugruppe(tmp_path, 7)
    s = bg.seite({"komponente": "platte", "feature": "f2", "instanz": 7, "achse": True})
    p7 = baue(SPEC).features["f2"].punkte[6]
    assert s.punkt == pytest.approx(p7) and p7[0] == pytest.approx(-20)
    assert s.richtung == pytest.approx((0, -1, 0))
    assert bg.komp["bolzen"].t[0] == pytest.approx(p7[0]) and bg.komp["bolzen"].t[2] == pytest.approx(p7[2])
    assert math.isfinite(bg.komp["bolzen"].t[1])
