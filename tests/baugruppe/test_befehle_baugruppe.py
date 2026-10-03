import json

import yaml

from swki.cli import main
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe
from tests.spec.beispiel import GUELTIG


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_validieren_baugruppe(capsys, tmp_path):
    code, daten = _lauf(capsys, "validieren", str(schreibe(tmp_path / "A")))
    assert code == 0, daten
    assert (daten["gueltig"], daten["art"], daten["komponenten"], daten["verknuepfungen"]) == (True, "baugruppe", 5, 9)


def test_validieren_hinweise(capsys, tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][2]["b"] = {"komponente": "platte", "nahe": [50, 10, 0]}
    code, daten = _lauf(capsys, "validieren", str(schreibe(tmp_path / "A", baugruppe=spec)))
    assert code == 0, daten
    arten = {(h["art"], h["pfad"].split(":")[0]) for h in daten["hinweise"]}
    assert ("feste_zahl", "platte") in arten               # tiefe 16 in der Platte
    assert ("nahe", "verknuepfungen[2].b") in arten


def test_validieren_teil_unveraendert(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "validieren", str(pfad))
    assert code == 0 and daten["features"] == len(GUELTIG["features"]) and "art" not in daten
