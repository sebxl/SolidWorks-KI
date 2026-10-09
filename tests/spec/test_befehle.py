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


def test_freigeben_nennt_die_kopie(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "freigeben", str(pfad))
    assert code == 0 and daten["kopie"] == str(tmp_path / "platte.freigegeben.yaml")


def test_freigabe_kopie_wird_nicht_freigegeben(capsys, tmp_path):
    pfad = tmp_path / "platte.freigegeben.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "freigeben", str(pfad))
    assert code == 1 and daten["code"] == "FREIGABE_KOPIE"
    assert "platte.yaml" in daten["fehler"]
    assert not (tmp_path / "freigabe.json").exists()


def test_validieren_nennt_auto_werte(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    spec = {**GUELTIG, "pruefung": {**GUELTIG["pruefung"], "huellquader": "auto"}}
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "validieren", str(pfad))
    assert code == 0 and daten["auto"]["huellquader"] == [100, 20, 60]
    assert daten["auto"]["volumen"].startswith("nicht berechenbar (f3: verrundung")   # Beispiel hat Verrundungen
