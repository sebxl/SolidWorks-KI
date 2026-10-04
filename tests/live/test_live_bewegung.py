"""Live: Bewegungsprobe (Spec 4a) – bauen in Grundstellung, prüfen mit Bewegungen, Bilder, Dateien unverändert."""

import json
import pathlib
import shutil

import pytest

from swki.aenderungen import abweichungen
from swki.cli import main
from swki.konfig import lade_rechner
from tests.baugruppe.beispiel_bewegung import schreibe

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-BEWEGUNG"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def auftrag(tmp_path):
    yield tmp_path / AUFTRAG
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _baue(capsys, ordner):
    pfad = schreibe(ordner)
    assert _lauf(capsys, "validieren", str(pfad))[0] == 0
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, bau
    return pfad, bau


def _protokoll(pfad):
    return json.loads((pfad.parent / "protokolle" / "bewegungsprobe.lauf-1.protokoll.json").read_text(encoding="utf-8"))


def test_bewegungsprobe_baut_in_grundstellung(capsys, auftrag):
    pfad, bau = _baue(capsys, auftrag)
    assert [k["id"] for k in bau["knoten"]] == ["platte", "schieber", "bolzen", "hebel", "v1", "v2", "g1", "v3", "v4",
                                                "s1", "s1.anlage", "g2", "grundstellung:Hub", "grundstellung:Schwenk"]
    assert all(k["status"] == "ok" for k in bau["knoten"]), bau["knoten"]
    assert "grundstellung" in _protokoll(pfad)["phasen"]


def test_bewegungsprobe_besteht_pruefung(capsys, auftrag):
    pfad, bau = _baue(capsys, auftrag)
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    assert code == 0, bericht
    assert bericht["maengel"] == [], json.dumps(bericht["pruefungen"], indent=1, ensure_ascii=False)
    assert [(x["bewegung"], x["gegen"]) for x in bericht["bewegungen"]["laeufe"]] == [
        ("Hub", {}), ("Schwenk", {}), ("Hub", {"Schwenk": "max"}), ("Schwenk", {"Hub": "max"})]
    assert {p["id"] for p in bericht["pruefungen"]} >= {
        "freiheitsgrad:schieber", "freiheitsgrad:hebel", "grenze:Hub", "grenze:Schwenk", "endlage:Hub:schieber",
        "endlage:Hub:hebel", "endlage:Schwenk:hebel", "bewegung_kollision:Hub", "bewegung_kollision:Schwenk"}
    for name in ("Hub-min", "Hub-mitte", "Hub-max", "Schwenk-min", "Schwenk-mitte", "Schwenk-max"):
        assert pathlib.Path(bericht["bilder"][name]).stat().st_size > 0
    assert abweichungen(pathlib.Path(bau["ordner"]), _protokoll(pfad)["sha256"]) == {"geaendert": [], "fehlend": []}
