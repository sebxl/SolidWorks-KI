import json
import subprocess

import pytest

from swki.cli import main
from swki.pruefung import befehle
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


def test_compiler_aenderungen_ohne_git(monkeypatch):
    def kein_git(*a, **k):
        raise FileNotFoundError("git")
    monkeypatch.setattr(befehle.subprocess, "run", kein_git)
    [zeile] = befehle._compiler_aenderungen("2026-10-01T10:00:00")
    assert zeile.startswith("(git nicht ausführbar")


def test_compiler_aenderungen_git_fehler(monkeypatch):
    monkeypatch.setattr(befehle.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 128, stdout="", stderr="fatal: kein Repo"))
    assert befehle._compiler_aenderungen("2026-10-01T10:00:00") == ["(git log fehlgeschlagen: fatal: kein Repo)"]
