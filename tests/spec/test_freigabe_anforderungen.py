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


# --- Gesamtreview C1: Tabellenstand der Freigabe gegen heute ---------------------------------------------------------

def _freigegeben(tmp_path, spec):
    import yaml

    from swki.spec.freigabe import freigeben

    pfad = tmp_path / "t.yaml"
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    freigeben(pfad, spec)
    return pfad


def test_funktionen_unveraendert_keine_meldung(tmp_path):
    from swki.spec.freigabe import funktionen_veraltet

    assert funktionen_veraltet(_freigegeben(tmp_path, _mit({"id": "s1", **STIFT}))) is None
    ohne = tmp_path / "ohne"
    ohne.mkdir()
    assert funktionen_veraltet(_freigegeben(ohne, SPEC)) is None   # ohne Anforderungen: kein Schlüssel, keine Meldung


def test_tabellenwert_geaendert_meldet_funktionen_veraltet(tmp_path, monkeypatch):
    """C-Wert der Stiftbohrung H7 → H8 nach der Freigabe: die Prüfsumme (nur der Name) bleibt, die Meldung nicht."""
    from swki.spec import funktionen
    from swki.spec.freigabe import funktionen_veraltet, pruefe_freigabe

    spec = _mit({"id": "s1", **STIFT})
    pfad = _freigegeben(tmp_path, spec)
    tabelle = {**funktionen.lade_funktionen(), "stiftbohrung": {**funktionen.lade_funktionen()["stiftbohrung"],
                                                               "passung": "H8"}}
    monkeypatch.setattr(funktionen, "lade_funktionen", lambda pfad=None: tabelle)
    pruefe_freigabe(pfad, spec)                                   # die Freigabe selbst sieht nichts
    meldung = funktionen_veraltet(pfad)
    assert meldung.startswith("FUNKTIONEN_VERALTET:") and "H7" in meldung and "H8" in meldung


def test_funktion_aus_tabelle_entfernt_meldet_funktionen_veraltet(tmp_path, monkeypatch):
    from swki.spec import funktionen
    from swki.spec.freigabe import funktionen_veraltet

    pfad = _freigegeben(tmp_path, _mit({"id": "s1", **STIFT}))
    tabelle = {k: v for k, v in funktionen.lade_funktionen().items() if k != "stiftbohrung"}
    monkeypatch.setattr(funktionen, "lade_funktionen", lambda pfad=None: tabelle)
    assert funktionen_veraltet(pfad).startswith("FUNKTIONEN_VERALTET:")


def test_bauweg_der_arbeitsdatei_zaehlt_nicht(tmp_path):
    """Verglichen wird die freigegebene Kopie: Zusammenfassen oder Umbenennen in der Arbeitsdatei ist kein Tabellenwechsel."""
    import yaml

    from swki.spec.freigabe import funktionen_veraltet

    zwei = _mit({"id": "s1", **STIFT, "positionen": [[0, 0]]}, {"id": "s2", **STIFT, "positionen": [[10, 0]]})
    pfad = _freigegeben(tmp_path, zwei)
    eins = _mit({"id": "stifte", **STIFT, "positionen": [[0, 0], [10, 0]]})
    pfad.write_text(yaml.safe_dump(eins, allow_unicode=True), encoding="utf-8")
    assert funktionen_veraltet(pfad) is None


def test_freigabe_ohne_anforderungen_schluessel_heisst_keine(tmp_path):
    """`freigeben` legt `anforderungen` nur ab, wenn es welche gibt: fehlt der Schlüssel, aber die Kopie hat welche,
    gilt der Stand als veraltet (Freigabe aus der Zeit vor Z1.1)."""
    from swki.spec.freigabe import freigabe_pfad, funktionen_veraltet

    pfad = _freigegeben(tmp_path, _mit({"id": "s1", **STIFT}))
    daten = json.loads(freigabe_pfad(pfad).read_text(encoding="utf-8"))
    del daten["t.yaml"]["anforderungen"]
    freigabe_pfad(pfad).write_text(json.dumps(daten), encoding="utf-8")
    assert funktionen_veraltet(pfad).startswith("FUNKTIONEN_VERALTET:")
