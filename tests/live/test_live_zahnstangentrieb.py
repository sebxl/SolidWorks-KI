"""Live: Negativfälle am Zahnstangentrieb (Spec 4b §10) – Zahnphase versetzt, Drehrichtung umgekehrt, Kopplung fehlt,
Übersetzung verfälscht. Jeder Fall verfälscht nur den Bau (monkeypatch), die Spec bleibt gültig und unverändert; jeder
Fall liefert genau seine Mängelmenge. Je Fall frisches SolidWorks (Controller)."""

import json
import shutil
from pathlib import Path

import pytest

from swki.baugruppe import bau, sw_baugruppe
from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-TRIEB"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "zahnstangentrieb"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def spec(tmp_path):
    ordner = tmp_path / AUFTRAG
    shutil.copytree(REFERENZ, ordner)
    yield ordner / "zahnstangentrieb.yaml"
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _maengel(capsys, spec: Path) -> tuple[dict, dict]:
    assert _lauf(capsys, "validieren", str(spec))[0] == 0
    assert _lauf(capsys, "freigeben", str(spec))[0] == 0
    code, ergebnis = _lauf(capsys, "bauen", str(spec))
    assert code == 0, ergebnis
    code, bericht = _lauf(capsys, "pruefen", str(spec))
    assert code in (0, 1) and "maengel" in bericht, bericht
    assert bericht["bestanden"] is False, bericht
    return {m["pruefung"]: m for m in bericht["maengel"]}, bericht


def test_zahnphase_versetzt(capsys, spec, monkeypatch):
    # Die Antriebswelle (z 50) wird um eine halbe Teilung zu weit gedreht und die Phasenprüfung des Baus abgeschaltet:
    # Zahn auf Zahn schon in Grundstellung (statische Kollision); die Bewegung meldet dasselbe Paar nicht noch einmal
    original = bau.phasenwinkel
    monkeypatch.setattr(bau, "phasenwinkel", lambda a, b: original(a, b) + (180 / a.geo.z if a.geo.z == 50 else 0.0))
    monkeypatch.setattr(bau, "TOL_PHASE", 1.0)
    maengel, _ = _maengel(capsys, spec)
    assert set(maengel) == {"kollision"}, maengel
    assert set(maengel["kollision"]["knoten"]) == {"antriebswelle", "ritzelwelle"}, maengel


def test_drehrichtung_umgekehrt(capsys, spec, monkeypatch):
    # Zahnradverknüpfung mit umgekehrtem Reverse: die Antriebswelle dreht falsch herum, die Zähne laufen aufeinander
    monkeypatch.setitem(sw_baugruppe.REVERSE, "zahnrad", not sw_baugruppe.REVERSE["zahnrad"])
    maengel, _ = _maengel(capsys, spec)
    assert set(maengel) == {"bewegung_kollision:Schlittenhub", "sollweg:Schlittenhub:antriebswelle",
                            "endlage:Schlittenhub:antriebswelle"}, maengel


def test_kopplung_fehlt(capsys, spec, monkeypatch):
    # k2 wird beim Bau nicht angelegt: die statische Prüfung meldet sie als fehlend, die Bewegungsprüfung läuft nicht.
    # Ohne k2 entfällt beim Bau auch die Zahnphase von k2; die Antriebswelle bleibt in der Einbaulage, die Zähne liegen
    # aufeinander – die strenge Kollisionsprüfung meldet das (Spec-Menge {verknuepfungen} vom Controller nach dem
    # Live-Lauf erweitert, Ruling T14-1)
    original = bau.verknuepfungen
    monkeypatch.setattr(bau, "verknuepfungen", lambda s, q: [v for v in original(s, q) if v.id != "k2"])
    maengel, bericht = _maengel(capsys, spec)
    assert set(maengel) == {"verknuepfungen", "kollision"}, maengel
    assert maengel["verknuepfungen"]["knoten"] == ["k2"]
    assert set(maengel["kollision"]["knoten"]) == {"antriebswelle", "ritzelwelle"}, maengel
    assert next(p for p in bericht["pruefungen"] if p["id"] == "bewegung:Schlittenhub")["ok"] is None


def test_uebersetzung_verfaelscht(capsys, spec, monkeypatch):
    # Zähler der Zahnradverknüpfung um 10 % zu groß: die Antriebswelle dreht 156° statt 172°, die Zähne laufen
    # innerhalb des Hubs aufeinander; das Rücklesen zeigt die falsche Übersetzung
    original = bau.teilkreise
    monkeypatch.setattr(bau, "teilkreise", lambda a, b: (lambda z, n: (z * 1.1, n) if n else (z, n))(*original(a, b)))
    maengel, _ = _maengel(capsys, spec)
    assert set(maengel) == {"eingriff:k2", "sollweg:Schlittenhub:antriebswelle", "endlage:Schlittenhub:antriebswelle",
                            "bewegung_kollision:Schlittenhub"}, maengel
