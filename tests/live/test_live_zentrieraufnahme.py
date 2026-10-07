"""Live: Negativfälle an der Zentrieraufnahme (Spec Formschräge §9) – Richtung vertauscht, Winkel verfälscht. Jeder Fall
verfälscht nur den Bau des Zapfens (monkeypatch auf den Namen schraege, den der Handler importiert), die Spec bleibt
gültig und unverändert; die Prüfung formschraegen misst gegen die freigegebene Kopie und meldet den Zapfen."""

import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.compiler.handler import extrusion
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-ZENTRIER"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "zentrieraufnahme"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def spec(tmp_path):
    ordner = tmp_path / AUFTRAG
    shutil.copytree(REFERENZ, ordner)
    yield ordner / "zentrieraufnahme.yaml"
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _verfaelsche_zapfen(monkeypatch, aenderung: dict) -> None:
    original = extrusion.schraege

    def schraege(f: dict):
        s = original(f)
        return {**s, **aenderung} if s is not None and f["id"] == "zapfen" else s

    monkeypatch.setattr(extrusion, "schraege", schraege)


def _formschraegen(capsys, spec: Path) -> tuple[dict, dict]:
    """validieren, freigeben, bauen, pruefen; liefert die Prüfung formschraegen und die Mängel je Prüfung."""
    assert _lauf(capsys, "validieren", str(spec))[0] == 0
    assert _lauf(capsys, "freigeben", str(spec))[0] == 0
    code, ergebnis = _lauf(capsys, "bauen", str(spec))
    assert code == 0, ergebnis
    code, bericht = _lauf(capsys, "pruefen", str(spec))
    assert code in (0, 1) and "maengel" in bericht, bericht
    assert bericht["bestanden"] is False, bericht
    return next(p for p in bericht["pruefungen"] if p["id"] == "formschraegen"), {m["pruefung"]: m for m in bericht["maengel"]}


def test_richtung_vertauscht(capsys, spec, monkeypatch):
    # Der Zapfen wird nach oben weiter statt enger: alle Seitenflächen zeigen das falsche Vorzeichen; das Volumen
    # wächst mit (Mangel volumen), der Hüllquader nicht (der Zapfen bleibt im Grundriss der Platte)
    _verfaelsche_zapfen(monkeypatch, {"querschnitt": "groesser"})
    pruefung, maengel = _formschraegen(capsys, spec)
    assert pruefung["ok"] is False and pruefung["knoten"] == ["zapfen"], pruefung
    assert [t.split(" (")[0] for t in pruefung["ist"]["zapfen"]] == ["Querschnitt nicht kleiner"], pruefung
    assert set(maengel) == {"formschraegen", "volumen"}, maengel


def test_winkel_verfaelscht(capsys, spec, monkeypatch):
    # Der Zapfen wird mit WZ + 3° gebaut (die Gleichung am Feature folgt mit, ein Rebuild stellt nichts zurück)
    _verfaelsche_zapfen(monkeypatch, {"winkel": "=WZ+3"})
    pruefung, maengel = _formschraegen(capsys, spec)
    assert pruefung["ok"] is False and pruefung["knoten"] == ["zapfen"], pruefung
    assert [t.split(" (")[0] for t in pruefung["ist"]["zapfen"]] == ["Winkel 13° statt 10°"], pruefung
    assert pruefung["gemessen"]["zapfen"] == [13.0], pruefung
    assert set(maengel) == {"formschraegen", "volumen"}, maengel
