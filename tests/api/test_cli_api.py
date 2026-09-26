import json

import pytest

from swki.api.chm import Seite
from swki.api.index import baue
from swki.api.typbib import EnumWert, Member, Parameter
from swki.cli import main


@pytest.fixture
def db(tmp_path):
    pfad = tmp_path / "api.sqlite"
    baue(
        pfad,
        [Member("IFeatureManager", "FeatureExtrusion4", "methode", [Parameter("Sd", False, False)])],
        [EnumWert("swEndConditions_e", "swEndCondBlind", 0)],
        [Seite("a.htm", "FeatureExtrusion4 Method (IFeatureManager)", "IFeatureManager", "FeatureExtrusion4",
               "Method", 2026, "Creates an extrusion.")],
        2026,
    )
    return pfad


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_methode(capsys, db):
    code, daten = _lauf(capsys, "api", "methode", "IFeatureManager.FeatureExtrusion4", "--db", str(db))
    assert code == 0 and daten["treffer"][0]["seit"] == 2026


def test_methode_unbekannt_ist_fehler(capsys, db):
    code, daten = _lauf(capsys, "api", "methode", "IX.Y", "--db", str(db))
    assert code == 1 and "IX.Y" in daten["fehler"]


def test_enum(capsys, db):
    _, daten = _lauf(capsys, "api", "enum", "swEndConditions_e", "--db", str(db))
    assert daten["werte"] == [{"name": "swEndCondBlind", "wert": 0}]


def test_suche(capsys, db):
    _, daten = _lauf(capsys, "api", "suche", "extrusion", "--db", str(db))
    assert daten["treffer"][0]["schluessel"] == "IFeatureManager.FeatureExtrusion4"


def test_pruefe_code(capsys, db, tmp_path):
    code_datei = tmp_path / "h.py"
    code_datei.write_text("fm.FeatureExtrusion4(True)\n", encoding="utf-8")
    code, daten = _lauf(capsys, "api", "pruefe-code", str(code_datei), "--db", str(db))
    assert code == 1
    assert daten["befunde"][0]["name"] == "FeatureExtrusion4"


def test_fehlender_index(capsys, tmp_path):
    code, daten = _lauf(capsys, "api", "info", "--db", str(tmp_path / "fehlt.sqlite"))
    assert code == 1 and "swki api bauen" in daten["fehler"]
