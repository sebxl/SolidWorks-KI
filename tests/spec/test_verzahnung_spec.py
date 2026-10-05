"""Format und Validieren des Features verzahnung (Spec 4b §4.1, §4.3), Hinweise und Sollvolumen."""

import copy
import math

import pytest

from swki.pruefung.geometrie import volumen_auto
from swki.spec.hinweise import hinweise
from swki.spec.laden import plausibel_befunde, schema_befunde
from swki.verzahnung import Stirnrad, Zahnstange

RAD = {
    "art": "teil", "name": "Rad", "material": "1.0038", "eigenschaften": {"Benennung": "Rad"},
    "parameter": {"M": 2, "Z": 20, "B": 16, "AS": -0.05, "D": 12, "L": 20},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": "=D"}}]},
         "ende": {"typ": "blind", "tiefe": "=L"}},
        {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": "=L"}},
         "mitte": [0, 0], "modul": "=M", "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
    "pruefung": {"volumen": {"soll": "auto"}},
}
STANGE = {
    "art": "teil", "name": "Stange", "parameter": {"M": 2, "Z": 9, "B": 20, "AS": -0.05, "H": 15},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [
             {"rechteck": {"mitte": ["=(Z-1)*pi*M/2", "=-1.25*M-H/2"], "breite": "=Z*pi*M", "hoehe": "=H"}}]},
         "ende": {"typ": "blind", "tiefe": "=B"}},
        {"id": "z1", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": "=M",
         "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS", "kopf": "+v"},
    ],
}


def _mit(spec: dict, **verzahnung) -> dict:
    neu = copy.deepcopy(spec)
    neu["features"][1].update(verzahnung)
    return neu


def _meldungen(spec: dict, tmp_path) -> list[str]:
    return [b["meldung"] for b in schema_befunde(spec) + plausibel_befunde(spec, tmp_path)]


def test_gueltige_verzahnungen(tmp_path):
    assert _meldungen(RAD, tmp_path) == []
    assert _meldungen(STANGE, tmp_path) == []


def test_ebene_nur_standard_oder_versatz():
    befunde = schema_befunde(_mit(RAD, ebene={"feature": "f1", "flaeche": "+z"}))
    assert [b["pfad"] for b in befunde] == ["features[1].ebene"]


def test_pflichtfelder():
    spec = copy.deepcopy(RAD)
    del spec["features"][1]["zahndickenabmass"]
    assert any("zahndickenabmass" in b["meldung"] for b in schema_befunde(spec))


@pytest.mark.parametrize(("aenderung", "code"), [
    ({"modul": 2.25}, "MODUL_NICHT_GENORMT"),
    ({"zaehne": 20.5}, "ZAEHNE_UNGANZ"),
    ({"zaehne": 16}, "UNTERSCHNITT"),
    ({"zahndickenabmass": 0}, "FLANKENSPIEL_FEHLT"),
    ({"zahndickenabmass": 0.8}, "FLANKENSPIEL_FEHLT"),
    ({"zahndickenabmass": -1.6, "modul": 1}, "VERZAHNUNG_GEOMETRIE"),
])
def test_befunde_stirnrad(tmp_path, aenderung, code):
    meldungen = _meldungen(_mit(RAD, **aenderung), tmp_path)
    assert any(m.startswith(code) for m in meldungen), meldungen


def test_zahnstange_ohne_unterschnittgrenze(tmp_path):
    assert _meldungen(_mit(STANGE, zaehne=3), tmp_path) == []


def test_winkel_und_kopf_je_art(tmp_path):
    assert _meldungen(_mit(RAD, winkel=0), tmp_path) == []
    assert _meldungen(_mit(RAD, winkel=359), tmp_path) == []
    assert any("[0, 360)" in m for m in _meldungen(_mit(RAD, winkel=360), tmp_path))
    assert "kopf gilt nur bei art: zahnstange" in _meldungen(_mit(RAD, kopf="-v"), tmp_path)
    assert "winkel gilt nur bei art: stirnrad" in _meldungen(_mit(STANGE, winkel=10), tmp_path)


def test_modul_und_zaehne_positiv(tmp_path):
    assert any("modul muss > 0" in m for m in _meldungen(_mit(RAD, modul=-2), tmp_path))


def test_hinweise_feste_zahlen_und_abmass():
    arten = {(h["art"], h["pfad"]) for h in hinweise(_mit(RAD, modul=2, zaehne=20, zahndickenabmass=-0.3))}
    assert ("feste_zahl", "features[1].modul") in arten
    assert ("feste_zahl", "features[1].zaehne") in arten
    assert ("abmass_gross", "features[1].zahndickenabmass") in arten
    assert not any(h["art"] == "abmass_gross" for h in hinweise(RAD))


def test_volumen_auto_mit_verzahnung():
    volumen, grund = volumen_auto(RAD)
    assert grund == "analytisch"
    assert volumen == pytest.approx(math.pi * 36 * 20 + Stirnrad(2, 20, -0.05).flaeche() * 16)
    volumen, _ = volumen_auto(STANGE)
    assert volumen == pytest.approx(9 * math.pi * 2 * 15 * 20 + Zahnstange(2, 9, -0.05).flaeche() * 20)


def test_pi_ist_kein_parametername(tmp_path):
    spec = copy.deepcopy(RAD)
    spec["parameter"]["pi"] = 3
    assert "pi ist die Kreiszahl und kein Parametername" in _meldungen(spec, tmp_path)
