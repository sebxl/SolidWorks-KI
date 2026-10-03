import json
from pathlib import Path

from swki.cli import main

STEHLAGER = Path(__file__).resolve().parents[1] / "referenz" / "stehlager" / "stehlager.yaml"


def test_stehlager_ist_gueltig(capsys):
    code = main(["validieren", str(STEHLAGER)])
    daten = json.loads(capsys.readouterr().out)
    assert code == 0, daten
    assert (daten["komponenten"], daten["verknuepfungen"]) == (15, 30)
