"""Live: swki pruefen, status, bericht an einer kleinen Platte (SolidWorks muss laufen)."""

import json
import shutil

import pytest
import yaml

from swki.auftrag import lauf_datei
from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-PRUEFEN"
SPEC = {
    "art": "teil", "name": "Platte", "material": "1.2312", "eigenschaften": {"Benennung": "Prüfplatte"},
    "parameter": {"L": 100},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}},
        {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [["=-L/2+15", 0], ["=L/2-15", 0]], "durchmesser": 8, "durch": True},
    ],
    "pruefung": {
        "huellquader": ["=L", 20, 60],
        "volumen": {"soll": 120000 - 2 * 3.141592653589793 * 16 * 20, "toleranz_prozent": 0.1},
        "masse_pruefen": [
            {"was": "Bohrungsabstand", "von": {"feature": "f2", "instanz": 1, "achse": True},
             "zu": {"feature": "f2", "instanz": 2, "achse": True}, "soll": 70},
            {"was": "Dicke", "von": {"feature": "f1", "flaeche": "-y"}, "zu": {"feature": "f1", "flaeche": "+y"},
             "soll": 20},
        ],
        "schwerpunkt": {"soll": [0, 10, 0]},
    },
}


@pytest.fixture
def spec_pfad(tmp_path):
    ordner = tmp_path / AUFTRAG
    ordner.mkdir()
    pfad = ordner / "platte.yaml"
    yield pfad
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _bauen(capsys, pfad, spec):
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, daten = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, daten


def test_pruefen_bestanden_und_status(capsys, spec_pfad):
    _bauen(capsys, spec_pfad, SPEC)
    assert _lauf(capsys, "status", str(spec_pfad))[1]["empfehlung"] == "pruefen"
    code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
    assert code == 0
    assert bericht["bestanden"] is True, bericht["maengel"]
    ergebnisse = {p["id"]: p for p in bericht["pruefungen"]}
    assert ergebnisse["mass:Bohrungsabstand"]["ist"] == pytest.approx(70)
    assert ergebnisse["material"]["ist"].startswith("1.2312")
    assert lauf_datei(spec_pfad, 1, "pruefbericht").exists()
    assert _lauf(capsys, "status", str(spec_pfad))[1]["empfehlung"] == "pruefer"
    lauf_datei(spec_pfad, 1, "pruefer").write_text('{"bestanden": true, "maengel": []}', encoding="utf-8")
    assert _lauf(capsys, "status", str(spec_pfad))[1]["empfehlung"] == "bestanden"
    code, daten = _lauf(capsys, "bericht", str(spec_pfad))
    assert code == 0 and daten["status"] == "bestanden"
    assert "**Status:** bestanden" in (spec_pfad.parent / "bericht.md").read_text(encoding="utf-8")


def test_pruefen_findet_mangel_mit_knoten(capsys, spec_pfad):
    falsch = json.loads(json.dumps(SPEC))
    falsch["pruefung"]["masse_pruefen"][0]["soll"] = 71
    _bauen(capsys, spec_pfad, falsch)
    code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
    assert code == 0 and bericht["bestanden"] is False
    assert bericht["maengel"] == [{
        "pruefung": "mass:Bohrungsabstand", "knoten": ["f2"],
        "beschreibung": "mass:Bohrungsabstand: ist 70.0 statt 71.0",
    }]
