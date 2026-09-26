import json
import subprocess
import sys

from swki.cli import main


def test_version_als_json(capsys):
    assert main(["version"]) == 0
    daten = json.loads(capsys.readouterr().out)
    assert daten == {"version": "0.1.0"}


def test_modulaufruf():
    ergebnis = subprocess.run(
        [sys.executable, "-m", "swki", "version"], capture_output=True, text=True, encoding="utf-8"
    )
    assert ergebnis.returncode == 0
    assert json.loads(ergebnis.stdout)["version"] == "0.1.0"


def test_unbekannter_befehl_gibt_fehler(capsys):
    assert main(["gibtsnicht"]) == 1
    daten = json.loads(capsys.readouterr().out)
    assert "fehler" in daten


def test_help_gibt_null(capsys):
    assert main(["--help"]) == 0
    output = capsys.readouterr().out
    assert "usage:" in output.lower()


def test_unerwartete_exception_wird_als_json_fehler_gemeldet(capsys, monkeypatch):
    def _kaputt(args):
        raise RuntimeError("kaputt")

    monkeypatch.setattr("swki.rechner._zeigen", _kaputt)
    assert main(["rechner", "zeigen"]) == 1
    daten = json.loads(capsys.readouterr().out)
    assert "RuntimeError" in daten["fehler"]
    assert "kaputt" in daten["fehler"]
