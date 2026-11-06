"""Paket Konstruktionsstil: typ austragung (Profil entlang eines offenen Pfads) – Schema, validieren, Volumen."""

import copy
import math

import pytest

from swki.pruefung.geometrie import volumen_auto
from swki.pruefung.huellquader import huellquader_auto
from swki.spec.austragung import pfad_laenge
from swki.spec.laden import plausibel_befunde, schema_befunde

BLOCK = {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [30, 25], "breite": 80, "hoehe": 70}}]},
         "ende": {"typ": "mittig", "tiefe": 20}}
KANAL = {"id": "k1", "typ": "austragung", "schnitt": True,
         "profil": {"ebene": "rechts", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": "=D"}}]},
         "pfad": {"ebene": "oben", "start": [0, 0],
                  "segmente": [{"linie": [40, 0]}, {"bogen": [60, 20], "mitte": [40, 20]}, {"linie": [60, 50]}]}}


def _spec(kanal=None, *weitere):
    return {"art": "teil", "name": "T", "parameter": {"D": 8}, "features": [BLOCK, kanal or KANAL, *weitere],
            "pruefung": {"huellquader": "auto", "volumen": {"soll": "auto"}}}


def _befunde(spec, tmp_path):
    return schema_befunde(spec) or plausibel_befunde(spec, tmp_path)


def _meldungen(spec, tmp_path):
    return " | ".join(f"{b['pfad']}: {b['meldung']}" for b in _befunde(spec, tmp_path))


def test_gueltig(tmp_path):
    assert _befunde(_spec(), tmp_path) == []


def test_pfadlaenge():
    assert pfad_laenge(KANAL["pfad"], {}) == pytest.approx(70 + 10 * math.pi)


def test_volumen_kreis():
    v, grund = volumen_auto(_spec())
    assert grund == "analytisch"
    assert v == pytest.approx(80 * 70 * 20 - math.pi * 16 * (70 + 10 * math.pi))


def test_volumen_rechteck_aufsatz():
    k = copy.deepcopy(KANAL)
    del k["schnitt"]
    k["profil"]["elemente"] = [{"rechteck": {"mitte": [0, 0], "breite": 6, "hoehe": 4}}]
    v, _ = volumen_auto({**_spec(k), "features": [k]})
    assert v == pytest.approx(24 * (70 + 10 * math.pi))


def test_huellquader_aufsatz_nicht_berechenbar():
    k = {key: v for key, v in KANAL.items() if key != "schnitt"}
    hq, grund = huellquader_auto({**_spec(k), "features": [k]})
    assert hq is None and "k1" in grund


def test_huellquader_schnitt_zaehlt_nicht():
    assert huellquader_auto(_spec())[0] == [80, 20, 70]


def test_profil_nicht_senkrecht(tmp_path):
    k = copy.deepcopy(KANAL)
    k["profil"]["ebene"] = "vorne"
    assert "features[1].profil.ebene: " in _meldungen(_spec(k), tmp_path)


def test_profil_nicht_am_start(tmp_path):
    k = copy.deepcopy(KANAL)
    k["profil"]["elemente"][0]["kreis"]["mitte"] = [5, 0]
    assert "features[1].profil: " in _meldungen(_spec(k), tmp_path)


def test_bogen_zu_eng(tmp_path):
    k = copy.deepcopy(KANAL)
    k["profil"]["elemente"][0]["kreis"]["durchmesser"] = 44
    assert "features[1].pfad.segmente[1]: " in _meldungen(_spec(k), tmp_path)


def test_knick_im_pfad(tmp_path):
    k = copy.deepcopy(KANAL)
    k["pfad"]["segmente"] = [{"linie": [40, 0]}, {"linie": [40, 30]}]
    assert "features[1].pfad.segmente[1]: " in _meldungen(_spec(k), tmp_path)


def test_bogen_im_uhrzeigersinn(tmp_path):
    k = copy.deepcopy(KANAL)
    k["pfad"]["segmente"] = [{"linie": [40, 0]}, {"bogen": [60, -20], "mitte": [40, -20], "uhrzeigersinn": True},
                             {"linie": [60, -50]}]
    assert _befunde(_spec(k), tmp_path) == []
    assert pfad_laenge(k["pfad"], {}) == pytest.approx(70 + 10 * math.pi)


def test_pfad_geschlossen(tmp_path):
    k = copy.deepcopy(KANAL)
    k["pfad"]["segmente"] = [{"linie": [40, 0]}, {"bogen": [0, 0], "mitte": [20, 0]}]
    assert "features[1].pfad: " in _meldungen(_spec(k), tmp_path)


def test_profil_genau_ein_element(tmp_path):
    k = copy.deepcopy(KANAL)
    k["profil"]["elemente"] *= 2
    assert schema_befunde(_spec(k))


def test_profil_auf_flaeche_abgelehnt():
    k = copy.deepcopy(KANAL)
    k["profil"]["ebene"] = {"feature": "f1", "flaeche": "+x"}
    assert schema_befunde(_spec(k))


def test_id_endung_pfad_reserviert(tmp_path):
    spec = _spec()
    spec["features"][0]["id"] = "x_pfad"
    spec["features"][1]["pfad"] = KANAL["pfad"]
    assert "<id>_pfad" in _meldungen(spec, tmp_path)


def test_uhrzeigersinn_nicht_in_kontur(tmp_path):
    kontur = {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 30], "mitte": [40, 15], "uhrzeigersinn": True},
                                            {"linie": [0, 30]}, {"linie": [0, 0]}]}
    f = {"id": "f2", "typ": "extrusion", "skizze": {"ebene": "vorne", "elemente": [{"kontur": kontur}]},
         "ende": {"typ": "blind", "tiefe": 5}}
    spec = {"art": "teil", "name": "T", "parameter": {}, "features": [f]}
    assert "features[0].skizze.elemente[0].kontur.segmente[1].uhrzeigersinn" in _meldungen(spec, tmp_path)
