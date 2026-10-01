import json

import pytest

from swki.cli import main
from swki.pruefung.befehle import LaufFehler, pruefe_lauf_gebaut


def test_gebauter_lauf_darf_geprueft_werden():
    pruefe_lauf_gebaut({"status": "ok", "fehler": None}, 2)


def test_abgebrochener_lauf_wird_nicht_geprueft():
    protokoll = {"status": "fehler", "fehler": {"code": "SKIZZE_NICHT_BESTIMMT", "meldung": "f3_skizze: Status 2"}}
    with pytest.raises(LaufFehler) as e:
        pruefe_lauf_gebaut(protokoll, 2)
    assert e.value.daten == {"code": "LAUF_ABGEBROCHEN"}
    assert "Lauf 2" in str(e.value) and "SKIZZE_NICHT_BESTIMMT" in str(e.value)


def test_max_darf_nicht_negativ_sein(capsys, tmp_path):
    code = main(["status", str(tmp_path / "platte.yaml"), "--max", "-1"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 1 and "--max" in daten["fehler"]
