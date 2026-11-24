"""Zeichnungsableitung Z1.1 (Design 2026-11-16 §4.1): Anforderungsfelder am Feature und Top-Level-Felder im Schema."""

import pytest

from swki.spec.laden import schema_befunde

BASIS = {"art": "teil", "name": "Platte", "parameter": {"D": 8, "A": 40},
         "features": [{"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
             {"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]}, "ende": {"typ": "blind", "tiefe": 20}}]}
BOHRUNG = {"id": "b1", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 0]],
           "durchmesser": "=D", "durch": True}


def _mit(feature_zusatz=None, **oben):
    spec = {**BASIS, **oben}
    spec["features"] = [{**BASIS["features"][0], **(feature_zusatz or {})}]
    return spec


def test_funktion_und_passung_am_feature():
    assert schema_befunde(_mit({"funktion": "anlage", "passung": "H7", "huelle": True,
                                "rauheit": {"Ra": 0.8}, "bearbeitung": "schleifen"})) == []


def test_felder_an_bohrung_und_normbohrung():
    norm = {"id": "s1", "typ": "normbohrung", "art": "stift", "groesse": "8", "flaeche": {"feature": "f1", "flaeche": "+y"},
            "positionen": [[10, 0]], "tiefe": 12, "funktion": "stiftbohrung", "toleranz": {"oben": 0.015, "unten": 0}}
    spec = {**BASIS, "features": [BASIS["features"][0], {**BOHRUNG, "funktion": "gleitpassung_bohrung"}, norm]}
    assert schema_befunde(spec) == []


def test_form_lage_mit_bezug():
    assert schema_befunde(_mit({"form_lage": [{"art": "rechtwinkligkeit", "wert": 0.02, "bezug": ["A"]}]},
                               bezuege={"A": {"feature": "f1", "flaeche": "-y"}})) == []


def test_position_mit_mmr():
    assert schema_befunde(_mit({"form_lage": [{"art": "position", "wert": 0.1, "bezug": ["A", "B", "C"], "mmr": True}]})) == []


def test_top_level_felder():
    assert schema_befunde(_mit(verfahren="fraesen", toleranzen={"A": {"oben": 0.02, "unten": -0.02}, "D": {"passung": "H7"}},
                               halbzeug={"art": "flach", "norm": "EN 10058", "masse": "100 x 20"},
                               behandlung=[{"art": "bruenieren"}])) == []


def test_feature_behandlung_verweis():
    assert schema_befunde(_mit({"behandlung": "einsatzhaerten"},
                               behandlung=[{"art": "einsatzhaerten", "haerte": {"wert": 60, "plus": 2, "minus": 2,
                                                                                "verfahren": "HRC"}}])) == []


def test_behandlung_nach_iso_15787():
    eintrag = {"art": "einsatzhaerten", "id": "zahnflanken", "zustand": "fertigteil",
               "haerte": {"wert": 60, "plus": 2, "minus": 2, "verfahren": "HRC"},
               "tiefe": {"art": "CHD", "wert": 0.8, "plus": 0.4, "grenzhaerte": "550 HV1"},
               "kernhaerte": {"wert": 30, "verfahren": "HRC"}}
    schicht = {"art": "verzinken", "schicht": {"norm": "DIN EN ISO 19598", "bezeichnung": "Fe//Zn8//Cn//T0", "dicke_um": 8}}
    assert schema_befunde(_mit({"behandlung": "zahnflanken"}, behandlung=[eintrag, schicht])) == []


@pytest.mark.parametrize("eintrag", [
    {"art": "einsatzhaerten", "haerte": "58+4 HRC"},                       # alte Schreibweise als Text
    {"art": "haerten", "haerte": {"wert": 58, "verfahren": "Shore"}},
    {"art": "einsatzhaerten", "tiefe": {"art": "Eht", "wert": 0.8}},
    {"art": "zaubern"},
    {"art": "haerten", "zustand": "gehaertet"},
])
def test_behandlung_ungueltig(eintrag):
    assert schema_befunde(_mit(behandlung=[eintrag]))


def test_halbzeug_werkstoff_aus_material():
    assert schema_befunde(_mit(halbzeug={"art": "flach", "norm": "EN 10058", "masse": "50 x 10", "werkstoff": "S235JR"}))


def test_halbzeug_toleranz_und_zustand():
    assert schema_befunde(_mit(halbzeug={"art": "rund", "norm": "DIN EN ISO 683-7", "masse": "20", "toleranz": "h9",
                                         "zustand": "+C"})) == []


@pytest.mark.parametrize("zusatz", [
    {"passung": "H77x"}, {"bearbeitung": "fraesen"}, {"rauheit": {"Ra": -1}}, {"rauheit": {"Ra": 0.8, "Rz": 4}},
    {"form_lage": [{"art": "gelb", "wert": 0.1}]}, {"form_lage": [{"art": "ebenheit", "wert": 0.1, "bezug": ["AB"]}]},
    {"toleranz": {"oben": 0.1}}, {"huelle": "ja"}, {"funktion": "Lagersitz"},
])
def test_ungueltige_feldwerte(zusatz):
    assert schema_befunde(_mit(zusatz))


def test_verfahren_nur_fraesen_oder_drehen():
    assert schema_befunde(_mit(verfahren="schleifen"))


def test_bezuege_nur_grossbuchstaben():
    assert schema_befunde(_mit(bezuege={"a": {"feature": "f1", "flaeche": "-y"}}))


def test_anforderung_nicht_an_muster():
    muster = {"id": "m1", "typ": "muster_linear", "features": ["f1"],
              "richtung1": {"achse": "x", "abstand": 10, "anzahl": 2}, "funktion": "anlage"}
    assert schema_befunde({**BASIS, "features": [BASIS["features"][0], muster]})
