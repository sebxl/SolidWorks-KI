"""Live: Baugruppen bauen (Spec 3b §7) – Probe aus tests/baugruppe/beispiel.py, Werte-Verknüpfungen, Fehlerpfad."""

import json
import shutil

import pytest

from swki.cli import main
from swki.konfig import lade_rechner
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-BAUGRUPPE"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def auftrag(tmp_path):
    yield tmp_path / AUFTRAG
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _baue(capsys, ordner, spec=None):
    pfad = schreibe(ordner, baugruppe=spec)
    assert _lauf(capsys, "validieren", str(pfad))[0] == 0
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    return pfad, *_lauf(capsys, "bauen", str(pfad))


def test_probe_baut(capsys, auftrag):
    pfad, code, bau = _baue(capsys, auftrag)
    assert code == 0, bau
    assert [k["id"] for k in bau["knoten"]] == ["platte", "deckel", "schraube.1", "schraube.2", "stift",
                                                "v1", "v2", "v3", "v4.1", "v4.2", "v5.1", "v5.2", "v6", "v7"]
    assert all(k["status"] == "ok" for k in bau["knoten"])
    protokoll = json.loads((pfad.parent / "protokolle" / "probe.lauf-1.protokoll.json").read_text(encoding="utf-8"))
    assert set(protokoll["sha256"]) == {f"{AUFTRAG}_Platte.sldprt", f"{AUFTRAG}_Deckel.sldprt", f"{AUFTRAG}_Probe.sldasm",
                                        "ISO4762_M8x16_8_8.sldprt", "ISO8734_8x16_St.sldprt"}
    assert set(protokoll["teile"]) == {"platte.yaml", "deckel.yaml"} and len(protokoll["komponenten"]) == 5
    assert {k["datei"] for k in protokoll["komponenten"]} <= set(protokoll["sha256"])


def test_werte_verknuepfungen(capsys, auftrag):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"] = spec["komponenten"][:2]
    spec["parameter"] = {"S": 5, "W": 30}
    spec["freiheitsgrade"] = {"deckel": "unterbestimmt"}
    spec["pruefung"] = {}
    spec["verknuepfungen"] = [
        {"id": "w1", "typ": "abstand", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "-y"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt", "wert": "=S"},
        {"id": "w2", "typ": "winkel", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "+x"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+x"}, "ausrichtung": "gleich", "wert": "=W"},
    ]
    _, code, bau = _baue(capsys, auftrag, spec)
    assert code == 0, bau
    assert [k["status"] for k in bau["knoten"]] == ["ok"] * 4


def test_senkrecht(capsys, auftrag):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"] = spec["komponenten"][:2]
    spec["freiheitsgrade"] = {"deckel": "unterbestimmt"}
    spec["pruefung"] = {}
    spec["verknuepfungen"] = [
        {"id": "s1", "typ": "senkrecht", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "+x"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+y"}}]
    _, code, bau = _baue(capsys, auftrag, spec)
    assert code == 0, bau


def test_fehlende_referenz_bricht_ab(capsys, auftrag):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][3]["b"]["flaeche"] = "-y"   # die Senkung hat keine Fläche −y
    pfad, code, bau = _baue(capsys, auftrag, spec)
    assert code == 1 and bau["fehler"]["code"] == "REFERENZ_NICHT_GEFUNDEN", bau
    assert "v4.1" in bau["fehler"]["meldung"] and "deckel" in bau["fehler"]["meldung"], bau["fehler"]  # Spec §11
    status = {k["id"]: k["status"] for k in bau["knoten"]}
    assert status["v4.1"] == "fehler" and status["v7"] == "uebersprungen"
    assert bau["dateien"]["baugruppe"].endswith(".sldasm")  # Stand zur Diagnose gespeichert
