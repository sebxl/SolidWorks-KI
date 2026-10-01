"""Das Sollvolumen der Referenz Auswerferhalteplatte passt zur Maßtabelle (ohne SolidWorks).

Schlägt fehl, wenn swki/wissen/bohrungsnormen.yaml geändert wurde, ohne soll neu zu rechnen (sollvolumen.py).
"""

import importlib.util
from pathlib import Path

import pytest
import yaml

ORDNER = Path(__file__).parent / "auswerferhalteplatte"


def test_sollvolumen_aus_tabelle():
    modul_spec = importlib.util.spec_from_file_location("sollvolumen", ORDNER / "sollvolumen.py")
    modul = importlib.util.module_from_spec(modul_spec)
    modul_spec.loader.exec_module(modul)
    soll = yaml.safe_load((ORDNER / "auswerferhalteplatte.yaml").read_text(encoding="utf-8"))["pruefung"]["volumen"]["soll"]
    assert sum(modul.rechnung().values()) == pytest.approx(soll, abs=0.001)
