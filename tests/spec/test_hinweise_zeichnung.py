"""Zeichnungsableitung Z1.1 (Design 2026-11-16 §4.5): Hinweise zu Verfahren, Bearbeitung und unbestätigten
Funktionswerten."""

from swki.spec.hinweise import fertigung_hinweise, funktion_hinweise, hinweise

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}
WELLE = {"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
    {"polygon": {"punkte": [[0, 0], [10, 0], [10, 40], [0, 40]]}},
    {"mittellinie": {"von": [0, -5], "bis": [0, 45]}}]}}
TASCHE = {"id": "t1", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"}, "elemente": [
    {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 20}}]}, "ende": {"typ": "blind", "tiefe": 15}}


def _regel8(spec):
    return [h for h in fertigung_hinweise(spec) if "Regel 8" in h["meldung"]]


def test_fraesen_scharfe_tasche_meldet_regel8():
    assert _regel8({"features": [PLATTE, TASCHE]})


def test_erodieren_ohne_fraeserregel():
    assert not _regel8({"features": [PLATTE, {**TASCHE, "bearbeitung": "erodieren"}]})


def test_schleifen_drehteil_ohne_freistich():
    spec = {"verfahren": "drehen", "features": [{**WELLE, "bearbeitung": "schleifen"}]}
    assert any("Freistich" in h["meldung"] and h["art"] == "fertigung" for h in fertigung_hinweise(spec))


def test_schleifen_fraesteil_ohne_freistich_hinweis():
    spec = {"verfahren": "fraesen", "features": [{**WELLE, "bearbeitung": "schleifen"}]}
    assert not any("Freistich" in h["meldung"] for h in fertigung_hinweise(spec))


def test_feine_rauheit_ohne_schleifen():
    spec = {"features": [{"id": "f1", "typ": "bohrung", "rauheit": {"Ra": 0.4}}]}
    [h] = [h for h in fertigung_hinweise(spec) if "Ra 0,4" in h["meldung"]]
    assert "schleifen" in h["meldung"] and h["pfad"] == "features[0].rauheit"


def test_feine_rauheit_mit_schleifen_ohne_hinweis():
    spec = {"features": [{"id": "f1", "typ": "bohrung", "rauheit": {"Ra": 0.4}, "bearbeitung": "schleifen"}]}
    assert not [h for h in fertigung_hinweise(spec) if "Ra 0,4" in h["meldung"]]


def test_unbestaetigter_tabellenwert():
    [h] = funktion_hinweise({"features": [{"id": "s1", "typ": "normbohrung", "funktion": "stiftbohrung"}]})
    assert h["art"] == "funktion" and h["pfad"] == "features[0].funktion" and "Nutzer" in h["meldung"]


def test_bestaetigter_wert_ohne_hinweis():
    assert funktion_hinweise({"features": [{"id": "g", "typ": "bohrung", "funktion": "lagersitz_gehaeuse"}]}) == []


def test_unbekannte_funktion_ohne_absturz():
    assert funktion_hinweise({"features": [{"id": "x", "typ": "bohrung", "funktion": "gibtsnicht"}]}) == []


def test_hinweise_enthaelt_funktion():
    assert any(h["art"] == "funktion" for h in hinweise(
        {"features": [PLATTE, {"id": "s1", "typ": "normbohrung", "art": "stift", "groesse": "8", "fase": 0.5,
                               "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 0]], "tiefe": 8,
                               "funktion": "stiftbohrung"}]}))


def test_position_ohne_oe_zone_als_hinweis():
    """Gesamtreview M2: validieren nennt Form/Lage, die die Zeichnung noch nicht richtig trägt (art „zeichnung“)."""
    from swki.spec.hinweise import zeichnung_hinweise

    f = {"id": "b1", "typ": "bohrung", "durchmesser": 6, "tiefe": 10, "fase": 0.5, "positionen": [[0, 0]],
         "flaeche": {"feature": "f1", "flaeche": "+y"}, "form_lage": [{"art": "position", "wert": 0.1, "bezug": ["A"]}]}
    [h] = zeichnung_hinweise({"features": [PLATTE, f]})
    assert h["art"] == "zeichnung" and h["pfad"] == "features[1].form_lage[0]" and "FORM_LAGE_NICHT_UNTERSTUETZT" in h["meldung"]
    assert any(x["art"] == "zeichnung" for x in hinweise({"features": [PLATTE, f]}))
    assert zeichnung_hinweise({"features": [PLATTE]}) == []
