"""Zeichnungsableitung Z1.1 (Design 2026-11-16 §4.3): Regeltabelle funktionen.yaml, Auflösung je Feature, Befunde."""

import pytest

from swki.spec.funktionen import FunktionFehler, anforderung_befunde, aufloesen, lade_funktionen


def test_tabelle_vollstaendig():
    t = lade_funktionen()
    assert {"stiftbohrung", "lagersitz_welle", "lagersitz_gehaeuse", "gleitpassung_bohrung", "gleitpassung_welle",
            "festsitz_bohrung", "festsitz_welle", "uebergang_bohrung", "uebergang_welle", "dichtflaeche_rwdr",
            "anlage"} == set(t)
    assert all({"quelle", "beleg", "bestaetigt"} <= set(e) for e in t.values())


def test_aufloesen_aus_tabelle():
    a = aufloesen({"id": "f3", "typ": "normbohrung", "funktion": "stiftbohrung"})
    assert a["passung"] == "H7" and a["huelle"] is True and a["rauheit"] == {"Ra": 0.8}
    assert "passung" in a["unbestaetigt"]


def test_feature_ueberschreibt_tabelle():
    a = aufloesen({"id": "f3", "typ": "bohrung", "funktion": "stiftbohrung", "rauheit": {"Ra": 0.4}})
    assert a["rauheit"] == {"Ra": 0.4} and "rauheit" not in a["unbestaetigt"]


def test_toleranz_ersetzt_tabellenpassung():
    a = aufloesen({"id": "f3", "typ": "bohrung", "funktion": "stiftbohrung", "toleranz": {"oben": 0.015, "unten": 0}})
    assert a["toleranz"] == {"oben": 0.015, "unten": 0} and a["passung"] is None and "passung" not in a["unbestaetigt"]


def test_bestaetigter_eintrag_ohne_unbestaetigt():
    assert aufloesen({"id": "g", "typ": "bohrung", "funktion": "lagersitz_gehaeuse"})["unbestaetigt"] == []


def test_form_lage_mit_it_grad():
    a = aufloesen({"id": "w", "typ": "rotation", "funktion": "lagersitz_welle"})
    assert a["form_lage"] == [{"art": "rundheit", "it": 4}]


def test_ohne_funktion_nur_eigene_werte():
    a = aufloesen({"id": "f1", "typ": "extrusion", "toleranz": {"oben": 0.1, "unten": 0}})
    assert a["toleranz"] == {"oben": 0.1, "unten": 0} and a["passung"] is None and a["huelle"] is False
    assert a["unbestaetigt"] == []


def test_unbekannte_funktion_fehler():
    with pytest.raises(FunktionFehler) as e:
        aufloesen({"id": "f1", "typ": "bohrung", "funktion": "lagersitz"})
    assert e.value.daten["code"] == "FUNKTION_UNBEKANNT" and "lagersitz" in str(e.value)


@pytest.mark.parametrize("spec, pfad", [
    ({"features": [{"id": "f1", "typ": "bohrung", "funktion": "gibtsnicht"}]}, "features[0].funktion"),
    ({"features": [{"id": "f1", "typ": "bohrung", "huelle": True}]}, "features[0].huelle"),
    ({"features": [{"id": "f1", "typ": "bohrung", "passung": "H7", "toleranz": {"oben": 0.1, "unten": 0}}]},
     "features[0].toleranz"),
    ({"features": [{"id": "f1", "typ": "bohrung", "form_lage": [{"art": "position", "wert": 0.1, "bezug": ["A"]}]}]},
     "features[0].form_lage[0].bezug"),
    ({"parameter": {"L": 50}, "toleranzen": {"Lx": {"oben": 0.1, "unten": 0}}, "features": []}, "toleranzen.Lx"),
    ({"features": [{"id": "f1", "typ": "bohrung", "behandlung": "haerten"}]}, "features[0].behandlung"),
])
def test_befunde(spec, pfad):
    assert [b["pfad"] for b in anforderung_befunde(spec)] == [pfad]


def test_keine_befunde_bei_gueltiger_spec():
    spec = {"parameter": {"L": 50}, "toleranzen": {"L": {"passung": "h11"}},
            "bezuege": {"A": {"feature": "f1", "flaeche": "-y"}},
            "behandlung": [{"art": "einsatzhaerten", "haerte": "58+4 HRC"}],
            "features": [{"id": "f1", "typ": "bohrung", "funktion": "stiftbohrung", "behandlung": "einsatzhaerten",
                          "form_lage": [{"art": "position", "wert": 0.1, "bezug": ["A"]}]}]}
    assert anforderung_befunde(spec) == []


def test_plausibel_befunde_enthalten_anforderungen(tmp_path):
    from swki.spec.laden import plausibel_befunde

    spec = {"art": "teil", "name": "P", "features": [
        {"id": "f1", "typ": "extrusion", "funktion": "gibtsnicht", "skizze": {"ebene": "oben", "elemente": [
            {"rechteck": {"mitte": [0, 0], "breite": 10, "hoehe": 10}}]}, "ende": {"typ": "blind", "tiefe": 5}}]}
    assert "features[0].funktion" in [b["pfad"] for b in plausibel_befunde(spec, tmp_path)]


def test_behandlung_verweis_ueber_id():
    spec = {"behandlung": [{"art": "einsatzhaerten", "id": "flanken"}],
            "features": [{"id": "f1", "typ": "rotation", "behandlung": "flanken"}]}
    assert anforderung_befunde(spec) == []


def test_bezugsanker_auf_unbekanntes_feature():
    spec = {"bezuege": {"A": {"feature": "gibtsnicht", "flaeche": "-y"}}, "features": [{"id": "f1", "typ": "extrusion"}]}
    assert [b["pfad"] for b in anforderung_befunde(spec)] == ["bezuege.A.feature"]
