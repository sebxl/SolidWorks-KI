"""Live: swki freigeben + swki bauen Ende zu Ende (SolidWorks muss laufen)."""

import json
import shutil

import pytest
import yaml

from swki.auftrag import lauf_datei, lauf_ordner
from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw

SPEC = {
    "art": "teil", "name": "Platte", "material": "1.2312", "eigenschaften": {"Benennung": "Testplatte"},
    "parameter": {"L": 100},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}},
        {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [["=-L/2+15", 0], ["=L/2-15", 0]], "durchmesser": 8, "durch": True},
    ],
    "pruefung": {"huellquader": ["=L", 20, 60]},
}


@pytest.fixture
def auftrag(tmp_path):
    ordner = tmp_path / "SWKI-LIVE-BAUEN"
    ordner.mkdir()
    spec_pfad = ordner / "platte.yaml"
    spec_pfad.write_text(yaml.safe_dump(SPEC, allow_unicode=True), encoding="utf-8")
    yield spec_pfad
    shutil.rmtree(lade_rechner().arbeitsordner / "SWKI-LIVE-BAUEN", ignore_errors=True)


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_bauen_ohne_freigabe_verweigert(capsys, auftrag):
    code, daten = _lauf(capsys, "bauen", str(auftrag))
    assert code == 1 and daten["code"] == "FREIGABE_FEHLT"


def test_freigeben_und_bauen(capsys, auftrag):
    assert _lauf(capsys, "freigeben", str(auftrag))[0] == 0
    code, daten = _lauf(capsys, "bauen", str(auftrag))
    assert code == 0, daten
    assert daten["lauf"] == 1 and daten["status"] == "ok"
    assert [k["status"] for k in daten["knoten"]] == ["ok", "ok"]
    ordner = lauf_ordner(lade_rechner(), "SWKI-LIVE-BAUEN", 1)
    assert (ordner / "SWKI-LIVE-BAUEN_Platte.sldprt").stat().st_size > 0
    assert (ordner / "SWKI-LIVE-BAUEN_Platte.step").stat().st_size > 0
    protokoll = json.loads(lauf_datei(auftrag, 1, "protokoll").read_text(encoding="utf-8"))
    assert protokoll["status"] == "ok" and set(protokoll["phasen"]) == {"vorbereiten", "bauen", "speichern"}
    # zweiter Lauf baut frisch in lauf-2
    code, daten = _lauf(capsys, "bauen", str(auftrag))
    assert code == 0 and daten["lauf"] == 2


def test_bauabbruch_wird_protokolliert(capsys, auftrag):
    spec = {**SPEC, "features": [*SPEC["features"], {
        "id": "f3", "typ": "fase", "kanten": [{"nahe": [50, 20, 30]}], "abstand": 1}]}  # Ecke → mehrdeutig
    auftrag.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    _lauf(capsys, "freigeben", str(auftrag))
    code, daten = _lauf(capsys, "bauen", str(auftrag))
    assert code == 1
    assert daten["fehler"]["code"] == "REFERENZ_MEHRDEUTIG"
    assert [k["status"] for k in daten["knoten"]] == ["ok", "ok", "fehler"]
    assert daten["dateien"]["teil"].endswith(".sldprt")  # Teilstand wird zur Diagnose trotzdem gespeichert
