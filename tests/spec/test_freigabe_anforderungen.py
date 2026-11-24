"""Zeichnungsableitung Z1.1 (Design 2026-11-16 §4.2): Prüfsumme nach Wirkung – Anforderungen an Features ohne Feature-IDs,
neue Top-Level-Felder nur wenn vorhanden; aufgelöste Tabellenwerte in freigabe.json."""

import json

import pytest

from swki.spec.anforderungen import anforderungs_tupel, aufgeloeste_anforderungen
from swki.spec.freigabe import freigabe_pfad, pruefsumme

ALTER_HASH = "d9b9a1e9f687b21b74fd79739d51ae4a1d31ada2027368b8e2e7f072d61c9c6c"  # pruefsumme(SPEC) vor Z1.1
SPEC = {  # wie tests/spec/test_freigabe.py
    "art": "teil", "name": "Platte", "material": "1.2312", "parameter": {"L": 100},
    "features": [{"id": "f1", "typ": "extrusion"}], "pruefung": {"huellquader": [100, 20, 60]},
}
STIFT = {"typ": "normbohrung", "art": "stift", "groesse": "8", "funktion": "stiftbohrung"}


def _mit(*features, **oben):
    return {**SPEC, **oben, "features": [*SPEC["features"], *features]}


def test_ohne_neue_felder_unveraendert():
    assert pruefsumme(SPEC) == ALTER_HASH


def test_umbenennen_und_zusammenfassen_unveraendert():
    zwei = _mit({"id": "s1", **STIFT, "positionen": [[0, 0]]}, {"id": "s2", **STIFT, "positionen": [[10, 0]]})
    eins = _mit({"id": "stifte", **STIFT, "positionen": [[0, 0], [10, 0]]})
    assert pruefsumme(zwei) == pruefsumme(eins)


def test_muster_statt_positionen_unveraendert():
    reihe = _mit({"id": "s1", **STIFT, "positionen": [[0, 0], [10, 0], [20, 0]]})
    muster = _mit({"id": "s1", **STIFT, "positionen": [[0, 0]]},
                  {"id": "m1", "typ": "muster_linear", "features": ["s1"], "richtung1": {"achse": "x", "abstand": 10, "anzahl": 3}})
    assert pruefsumme(reihe) == pruefsumme(muster)


def test_funktion_an_einer_von_zwei_bohrungen_entfernt_aendert_summe():
    ohne = {k: v for k, v in STIFT.items() if k != "funktion"}
    beide = _mit({"id": "s1", **STIFT, "positionen": [[0, 0]]}, {"id": "s2", **STIFT, "positionen": [[10, 0]]})
    eine = _mit({"id": "s1", **STIFT, "positionen": [[0, 0]]}, {"id": "s2", **ohne, "positionen": [[10, 0]]})
    assert pruefsumme(beide) != pruefsumme(eine)


def test_maskierter_parameter_ohne_absturz():
    f = {"id": "b1", "typ": "bohrung", "durchmesser": "=D", "funktion": "gleitpassung_bohrung"}
    spec = {**SPEC, "parameter": {"D": "<raum>"}, "features": [f]}  # wie swki.optimierung.raum.maskiert
    assert anforderungs_tupel(spec)[0][1] == "=D"
    pruefsumme(spec)


def test_freigeben_legt_anforderungen_in_jedem_weg_ab(tmp_path):
    from swki.spec.freigabe import freigeben

    eintrag = freigeben(tmp_path / "t.yaml", _mit({"id": "s1", **STIFT}), zusatz={"raum": {"x": 1}})
    assert eintrag["raum"] == {"x": 1} and eintrag["anforderungen"][0]["passung"] == "H7"


def test_reihenfolge_unveraendert():
    gleit = {"id": "g1", "typ": "bohrung", "durchmesser": 10, "funktion": "gleitpassung_bohrung"}
    assert pruefsumme(_mit({"id": "s1", **STIFT}, gleit)) == pruefsumme(_mit(gleit, {"id": "s9", **STIFT}))


@pytest.mark.parametrize("aenderung", [{"passung": "H8"}, {"funktion": "gleitpassung_bohrung"}, {"huelle": False},
                                       {"groesse": "10"}, {"bearbeitung": "schleifen"}])
def test_anforderung_aendert_summe(aenderung):
    assert pruefsumme(_mit({"id": "s1", **STIFT})) != pruefsumme(_mit({"id": "s1", **STIFT, **aenderung}))


def test_funktion_hinzu_aendert_summe():
    ohne = {k: v for k, v in STIFT.items() if k != "funktion"}
    assert pruefsumme(_mit({"id": "s1", **ohne})) != pruefsumme(_mit({"id": "s1", **STIFT}))


@pytest.mark.parametrize("feld, wert", [
    ("verfahren", "drehen"), ("toleranzen", {"L": {"oben": 0.1, "unten": 0}}),
    ("halbzeug", {"art": "flach", "norm": "EN 10058", "masse": "100 x 20"}), ("behandlung", [{"art": "bruenieren"}]),
])
def test_top_level_aendert_summe(feld, wert):
    assert pruefsumme({**SPEC, feld: wert}) != pruefsumme(SPEC)


def test_bezuege_sind_bauweg():
    assert pruefsumme({**SPEC, "bezuege": {"A": {"feature": "f1", "flaeche": "-y"}}}) == ALTER_HASH


def test_durchmesser_ausdruck():
    f = {"id": "b1", "typ": "bohrung", "durchmesser": "=D", "funktion": "stiftbohrung"}
    assert anforderungs_tupel({"parameter": {"D": 8}, "features": [f]})[0][1] == 8.0
    assert anforderungs_tupel({"parameter": {}, "features": [f]})[0][1] == "=D"


def test_normbohrung_nenngroesse():
    assert anforderungs_tupel({"features": [{"id": "s1", **STIFT}]})[0][:2] == ["bohrung", "stift 8"]


def test_aufgeloeste_anforderungen():
    [a] = aufgeloeste_anforderungen({"features": [SPEC["features"][0], {"id": "s1", **STIFT}]})
    assert a["feature"] == "s1" and a["passung"] == "H7" and a["huelle"] is True


def test_freigeben_legt_aufgeloeste_werte_ab(tmp_path):
    from types import SimpleNamespace

    import yaml

    from swki.spec.befehle import _freigeben

    spec = {"art": "teil", "name": "P", "features": [
        {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
            {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 40}}]}, "ende": {"typ": "blind", "tiefe": 10}},
        {"id": "s1", "typ": "normbohrung", "art": "stift", "groesse": "8", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [[0, 0]], "tiefe": 8, "funktion": "stiftbohrung"}]}
    pfad = tmp_path / "p.yaml"
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    _freigeben(SimpleNamespace(spec=str(pfad)))
    eintrag = json.loads(freigabe_pfad(pfad).read_text(encoding="utf-8"))["p.yaml"]
    assert eintrag["anforderungen"][0]["feature"] == "s1" and eintrag["anforderungen"][0]["passung"] == "H7"
