"""Live: Negativfälle am Stehlager (Spec 3b §14) – zu lange Schraube, Überlappung, unterbestimmte Komponente, manuelle
Änderung an einem gebauten Teil der Baugruppe."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from swki.auftrag import lauf_ordner
from swki.cli import main
from swki.konfig import lade_rechner
from tests.live.test_live_aenderungen import _setze_parameter

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-STEHLAGER"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "stehlager"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def auftrag(tmp_path):
    ordner = tmp_path / AUFTRAG
    shutil.copytree(REFERENZ, ordner)
    yield ordner
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _aendere(ordner: Path, aendern) -> Path:
    pfad = ordner / "stehlager.yaml"
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    aendern(spec)
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def _komponente(spec: dict, kid: str) -> dict:
    return next(k for k in spec["komponenten"] if k["id"] == kid)


def _baue_und_pruefe(capsys, pfad: Path) -> dict:
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, bau
    return _lauf(capsys, "pruefen", str(pfad))[1]


def _maengel(bericht: dict) -> dict:
    assert bericht["bestanden"] is False, bericht
    return {m["pruefung"]: m for m in bericht["maengel"]}


def test_zu_lange_deckelschraube(capsys, auftrag):
    # M8 × 40 statt × 35: Einschraublänge 18,6 mm > Gewindetiefe 16 mm, an beiden Deckelschrauben; sonst nichts
    pfad = _aendere(auftrag, lambda s: _komponente(s, "deckelschraube").update(quelle={"normteil": "ISO 4762 M8x40"}))
    maengel = _maengel(_baue_und_pruefe(capsys, pfad))
    assert set(maengel) == {"gewinde:deckelschraube.1", "gewinde:deckelschraube.2"}, maengel
    for i in (1, 2):
        assert "Einschraublänge 18.60" in maengel[f"gewinde:deckelschraube.{i}"]["beschreibung"], maengel


def test_ueberlappung(capsys, auftrag):
    # Stift 8 × 40 statt × 30: beide Stifte ragen 8 mm über die Stiftbohrungen (Tiefe 12) in den Fuß des Unterteils
    pfad = _aendere(auftrag, lambda s: _komponente(s, "stift").update(quelle={"normteil": "ISO 8734 8x40"}))
    maengel = _maengel(_baue_und_pruefe(capsys, pfad))
    assert set(maengel) == {"kollision"}, maengel
    assert {"stift.1", "stift.2", "unterteil"} <= set(maengel["kollision"]["knoten"]), maengel


def test_unterbestimmte_komponente(capsys, auftrag):
    # ohne v3 (parallel) dreht das Unterteil frei um die Stiftachse
    pfad = _aendere(auftrag, lambda s: s.update(verknuepfungen=[v for v in s["verknuepfungen"] if v["id"] != "v3"]))
    maengel = _maengel(_baue_und_pruefe(capsys, pfad))
    assert set(maengel) == {"bestimmtheit"}, maengel
    assert "unterteil" in maengel["bestimmtheit"]["knoten"], maengel


def test_manuelle_aenderung_in_der_baugruppe(capsys, auftrag):
    pfad = auftrag / "stehlager.yaml"
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, bau
    _setze_parameter(lauf_ordner(lade_rechner(), AUFTRAG, 1) / f"{AUFTRAG}_Grundplatte.sldprt", "L", 210)
    code, daten = _lauf(capsys, "bauen", str(pfad))
    assert code == 1 and daten["code"] == "MANUELL_GEAENDERT", daten
    code, daten = _lauf(capsys, "aenderungen", str(pfad))
    assert code == 0, daten
    assert [e["datei"] for e in daten["geaendert"]] == [f"{AUFTRAG}_Grundplatte.sldprt"], daten  # nur die Grundplatte
    assert daten["geaendert"][0]["parameter"] == [{"name": "L", "soll": 200, "ist": 210.0}]
    assert daten["fehlend"] == [], daten
