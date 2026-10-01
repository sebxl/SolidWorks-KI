"""Live: Code-Prüfung normbohrungen gegen die freigegebene Kopie und Baum-Kennzahl (SolidWorks muss laufen)."""

import json
import shutil

import pytest
import yaml

from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-NORMBOHRUNG"
SPEC = {
    "art": "teil", "name": "Platte", "material": "1.1191", "eigenschaften": {"Benennung": "Prüfplatte Normbohrung"},
    "parameter": {"L": 100, "A": 15},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}},
        {"id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8",
         "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [["=-L/2+A", 0], ["=L/2-A", 0]], "durch": True},
    ],
    "pruefung": {
        "huellquader": ["=L", 20, 60],
        "masse_pruefen": [{"was": "Schraubenabstand", "von": {"feature": "f2", "instanz": 1, "achse": True},
                           "zu": {"feature": "f2", "instanz": 2, "achse": True}, "soll": "=L-2*A"}],
        "schwerpunkt": {"soll": [0, None, 0]},
    },
}


@pytest.fixture
def spec_pfad(tmp_path):
    ordner = tmp_path / AUFTRAG
    ordner.mkdir()
    yield ordner / "platte.yaml"
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _schreibe(pfad, spec) -> None:
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")


def test_normbohrung_bestanden_mit_baum(capsys, spec_pfad):
    _schreibe(spec_pfad, SPEC)
    assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(spec_pfad))
    assert code == 0, bau
    code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
    assert code == 0 and bericht["bestanden"] is True, bericht["maengel"]
    ergebnisse = {p["id"]: p for p in bericht["pruefungen"]}
    assert ergebnisse["normbohrungen"]["ok"] is True
    assert ergebnisse["mass:Schraubenabstand"]["ist"] == pytest.approx(70)
    assert bericht["baum"] == {"knoten": 2, "features": 2}
    assert _lauf(capsys, "bericht", str(spec_pfad))[0] == 0
    assert "## Feature-Baum (letzter Lauf)" in (spec_pfad.parent / "bericht.md").read_text(encoding="utf-8")


def test_groesse_nach_freigabe_geaendert_ist_mangel(capsys, spec_pfad):
    _schreibe(spec_pfad, SPEC)
    assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
    geaendert = json.loads(json.dumps(SPEC))
    geaendert["features"][1]["groesse"] = "M10"  # Bauweg geändert – die Prüfsumme bemerkt es nicht
    _schreibe(spec_pfad, geaendert)
    code, bau = _lauf(capsys, "bauen", str(spec_pfad))
    assert code == 0, bau
    code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
    assert code == 0 and bericht["bestanden"] is False
    [mangel] = [m for m in bericht["maengel"] if m["pruefung"] == "normbohrungen"]
    assert mangel["knoten"] == ["f2"] and "groesse" in mangel["beschreibung"]
