"""Live: manuelle Parameteränderung an einem gebauten Teil wird vor dem nächsten Lauf erkannt (Spec 3b §8)."""

import json
import shutil

import pythoncom
import pytest
import yaml

from swki.auftrag import lauf_ordner
from swki.cli import main
from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.pruefung.messen import oeffne
from swki.verbindung import verbinde

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-AENDERUNGEN"
SPEC = {
    "art": "teil", "name": "Platte", "material": "1.0038", "eigenschaften": {"Benennung": "Testplatte"},
    "parameter": {"L": 100, "B": 60},
    "features": [{"id": "f1", "typ": "extrusion",
                  "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
                  "ende": {"typ": "blind", "tiefe": 10}}],
    "pruefung": {"huellquader": ["=L", 10, "=B"]},
}


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _setze_parameter(pfad, name: str, wert: float) -> None:
    """Wie ein Anwender: Teil öffnen, globale Variable ändern (Property-Put per Invoke, S9a), speichern, schließen."""
    app = verbinde(lade_rechner().sw_jahr)
    model = oeffne(app, pfad)
    try:
        gleichungen = model.GetEquationMgr
        index = next(i for i in range(gleichungen.GetCount) if gleichungen.Equation(i).startswith(f'"{name}"'))
        dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
        gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, f'"{name}" = {wert}')
        gleichungen.EvaluateAll
        sw.rebuild(model)
        sw.speichere(model, pfad)
    finally:
        sw.schliesse(app, model)


def test_manuelle_aenderung_am_teil(capsys, tmp_path):
    spec_pfad = tmp_path / AUFTRAG / "platte.yaml"
    spec_pfad.parent.mkdir()
    spec_pfad.write_text(yaml.safe_dump(SPEC, allow_unicode=True), encoding="utf-8")
    try:
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        _setze_parameter(lauf_ordner(lade_rechner(), AUFTRAG, 1) / f"{AUFTRAG}_Platte.sldprt", "L", 120)
        code, daten = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 1 and daten["code"] == "MANUELL_GEAENDERT" and daten["lauf"] == 1, daten
        code, daten = _lauf(capsys, "aenderungen", str(spec_pfad))
        assert code == 0, daten
        [eintrag] = daten["geaendert"]
        assert eintrag["datei"] == f"{AUFTRAG}_Platte.sldprt"
        assert eintrag["parameter"] == [{"name": "L", "soll": 100, "ist": 120.0}]
        code, bau = _lauf(capsys, "bauen", str(spec_pfad), "--verwerfen")
        assert code == 0 and bau["lauf"] == 2, bau
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)
