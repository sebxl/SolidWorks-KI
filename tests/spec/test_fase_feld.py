"""Paket Konstruktionsstil: Feld `fase` an bohrung und normbohrung (Schema und validieren)."""

import copy

from swki.spec.laden import plausibel_befunde, schema_befunde

from .beispiel import GUELTIG

FLAECHE = {"feature": "f1", "flaeche": "+y"}


def _spec(bohrung: dict) -> dict:
    spec = copy.deepcopy(GUELTIG)
    spec["parameter"]["FB"] = 0.5
    spec["features"].append(bohrung)
    return spec


def _nb(art, groesse="M8", **w):
    return {"id": "f9", "typ": "normbohrung", "art": art, "groesse": groesse, "flaeche": FLAECHE,
            "positionen": [[0, 0]], "durch": True, **w}


def _befunde(spec, tmp_path):
    return schema_befunde(spec) or plausibel_befunde(spec, tmp_path)


def test_fase_ok(tmp_path):
    bohrung = {"id": "f9", "typ": "bohrung", "flaeche": FLAECHE, "positionen": [[0, 0]], "durchmesser": 6,
               "durch": True, "fase": "=FB"}
    assert _befunde(_spec(bohrung), tmp_path) == []
    assert _befunde(_spec(_nb("gewinde", fase="nenn")), tmp_path) == []
    assert _befunde(_spec(_nb("stift", groesse=8, fase=0.5)), tmp_path) == []


def test_fase_nenn_nur_gewinde(tmp_path):
    [b] = _befunde(_spec(_nb("stift", groesse=8, fase="nenn")), tmp_path)
    assert b["pfad"] == "features[6].fase" and "gewinde" in b["meldung"]


def test_fase_nenn_nicht_an_bohrung(tmp_path):
    bohrung = {"id": "f9", "typ": "bohrung", "flaeche": FLAECHE, "positionen": [[0, 0]], "durchmesser": 6,
               "durch": True, "fase": "nenn"}
    [b] = _befunde(_spec(bohrung), tmp_path)
    assert b["pfad"] == "features[6].fase"


def test_fase_an_senkschraube(tmp_path):
    [b] = _befunde(_spec(_nb("senkschraube", fase=0.5)), tmp_path)
    assert b["pfad"] == "features[6].fase" and "senkschraube" in b["meldung"]


def test_fase_nicht_positiv(tmp_path):
    [b] = _befunde(_spec(_nb("zylinderschraube", fase=0)), tmp_path)
    assert b["pfad"] == "features[6].fase" and "> 0" in b["meldung"]


def test_fase_text_ungueltig(tmp_path):
    assert schema_befunde(_spec(_nb("gewinde", fase="gross")))


def test_id_endung_fase_reserviert(tmp_path):
    spec = copy.deepcopy(GUELTIG)
    spec["features"][3]["id"] = "f1_fase"
    befunde = plausibel_befunde(spec, tmp_path)
    assert any(b["pfad"] == "features[3].id" and "<id>_fase" in b["meldung"] for b in befunde)
