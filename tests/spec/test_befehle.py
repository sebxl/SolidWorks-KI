import json

import yaml

from swki.cli import main

from .beispiel import GUELTIG


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_validieren_ok(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "validieren", str(pfad))
    assert code == 0 and daten["gueltig"] is True and daten["features"] == 6
    # feste Maße sind erlaubt, werden aber gemeldet (die Freigabe-Prüfsumme deckt sie nicht ab)
    assert [h["pfad"] for h in daten["hinweise"]][0] == "features[1].durchmesser"
    assert daten["hinweise"][0]["art"] == "feste_zahl"
    assert any(h["art"] == "zusammenfassen" for h in daten["hinweise"])


def test_validieren_meldet_befunde(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump({**GUELTIG, "name": "mit Leerzeichen"}), encoding="utf-8")
    code, daten = _lauf(capsys, "validieren", str(pfad))
    assert code == 1
    assert daten["befunde"][0]["pfad"] == "name"


def test_freigeben(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "freigeben", str(pfad))
    assert code == 0 and len(daten["pruefsumme"]) == 64
    assert (tmp_path / "freigabe.json").exists()
