"""Live: Baugruppen bauen (Spec 3b §7) – Probe aus tests/baugruppe/beispiel.py, Werte-Verknüpfungen, Fehlerpfad."""

import json
import pathlib
import shutil

import pytest

from swki.aenderungen import abweichungen
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


def _unveraendert(pfad, bau):
    """Prüfsummen des Laufs (Protokoll sha256) gegen die Dateien: nichts geändert, nichts fehlt (Spec §8: pruefen und
    aenderungen speichern nie)."""
    protokoll = json.loads((pfad.parent / "protokolle" / "probe.lauf-1.protokoll.json").read_text(encoding="utf-8"))
    assert abweichungen(pathlib.Path(bau["ordner"]), protokoll["sha256"]) == {"geaendert": [], "fehlend": []}


def test_probe_besteht_pruefung(capsys, auftrag):
    pfad, code, bau = _baue(capsys, auftrag)
    assert code == 0, bau
    _unveraendert(pfad, bau)
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    assert code == 0, bericht
    assert bericht["maengel"] == [], json.dumps(bericht["pruefungen"], indent=1, ensure_ascii=False)
    assert [g["einschraublaenge"] for g in bericht["gewindepaarungen"]] == pytest.approx([9.6, 9.6], abs=0.01)
    assert all(pathlib.Path(p).stat().st_size > 0 for p in bericht["bilder"].values())
    _unveraendert(pfad, bau)  # swki pruefen speichert nie
    code, aend = _lauf(capsys, "aenderungen", str(pfad))
    assert code == 0 and aend["geaendert"] == [] and aend["fehlend"] == [], aend
    _unveraendert(pfad, bau)  # swki aenderungen speichert nie


def test_kollision_wird_gemeldet(capsys, auftrag):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][3]["quelle"] = {"normteil": "ISO 8734 8x30"}   # Stift ragt 10 mm in den Deckel
    pfad, code, bau = _baue(capsys, auftrag, spec)
    assert code == 0, bau
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    maengel = {m["pruefung"]: m for m in bericht["maengel"]}
    assert maengel["kollision"]["knoten"] == ["deckel", "stift"], bericht["maengel"]


def test_werte_verknuepfungen(capsys, auftrag):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"] = spec["komponenten"][:2]
    spec["parameter"] = {"S": 5, "W": 30}
    spec["freiheitsgrade"] = {"deckel": "unterbestimmt"}
    spec["pruefung"] = {"masse_pruefen": [
        {"was": "Abstand", "von": {"komponente": "platte", "feature": "f1", "flaeche": "+y"},
         "zu": {"komponente": "deckel", "feature": "f1", "flaeche": "-y"}, "soll": "=S"}]}
    spec["verknuepfungen"] = [
        {"id": "w1", "typ": "abstand", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "-y"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt", "wert": "=S"},
        {"id": "w2", "typ": "winkel", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "+x"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+x"}, "ausrichtung": "gleich", "wert": "=W"},
    ]
    pfad, code, bau = _baue(capsys, auftrag, spec)
    assert code == 0, bau
    assert [k["status"] for k in bau["knoten"]] == ["ok"] * 4
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    assert code == 0 and bericht["maengel"] == [], bericht["maengel"]


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
