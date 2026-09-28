"""Live: Musterabstände, Kreismusterwinkel, Ebenenversatz und Fasenwinkel hängen per Gleichung an Parametern."""

import math

import pythoncom
import pytest

from swki.compiler import sw

from .bauhilfe import gebautes_teil

pytestmark = pytest.mark.sw

PARAMETER = {"V": -15, "A1": 21, "A2": 13, "W": 300, "FW": 33}
SPEC = {"art": "teil", "name": "T", "parameter": PARAMETER, "features": [
    {"id": "f1", "typ": "extrusion",
     "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": "=V"}},
                "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
     "ende": {"typ": "blind", "tiefe": 20}},
    {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[-40, -20]], "durchmesser": 8, "durch": True},
    {"id": "f3", "typ": "muster_linear", "features": ["f2"],
     "richtung1": {"achse": "x", "abstand": "=A1", "anzahl": 4},
     "richtung2": {"achse": "z", "abstand": "=A2", "anzahl": 2, "umkehren": True}},
    {"id": "f4", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[10, 0]], "durchmesser": 6, "durch": True},
    {"id": "f5", "typ": "muster_kreis", "features": ["f4"], "achse": "y", "anzahl": 5, "winkel": "=W"},
    {"id": "f6", "typ": "fase", "kanten": [{"nahe": [50, 5, 0]}], "abstand": 1.5, "winkel": "=FW"},
]}


def _setze_parameter(model, name: str, wert: float) -> None:
    """Globale Variable ändern (Property-Put nur per Invoke, S9a), dann Gleichungen auswerten und neu aufbauen."""
    gleichungen = model.GetEquationMgr
    index = list(PARAMETER).index(name)  # globale Variablen stehen in Parameter-Reihenfolge vorne
    dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
    gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, f'"{name}" = {wert}')
    gleichungen.EvaluateAll
    sw.rebuild(model)


def _mass(model, name: str) -> float:
    return model.Parameter(name).SystemValue


def test_masse_folgen_parametern():
    with gebautes_teil(SPEC) as (ctx, fehler, _):
        assert fehler is None
        model = ctx.model
        gleichungen = model.GetEquationMgr
        texte = [gleichungen.Equation(i) for i in range(gleichungen.GetCount)]
        assert '"D3@f3" = "A1"' in texte and '"D4@f3" = "A2"' in texte
        assert '"D3@f5" = "W"' in texte and '"D2@f6" = "FW"' in texte
        # Ebenenname ist sprachabhängig ("Ebene1"); Maß = Betrag, daher negiert
        assert len([t for t in texte if t.startswith('"D1@') and t.endswith('= -("V")')]) == 1

        assert sw.teilebox_mm(model)[1] == pytest.approx(-15, abs=1e-6)
        _setze_parameter(model, "V", -25)
        assert sw.teilebox_mm(model)[1] == pytest.approx(-25, abs=1e-6)

        _setze_parameter(model, "A1", 22)
        _setze_parameter(model, "A2", 14)
        _setze_parameter(model, "W", 240)
        _setze_parameter(model, "FW", 40)
        assert _mass(model, "D3@f3") == pytest.approx(0.022)
        assert _mass(model, "D4@f3") == pytest.approx(0.014)
        assert _mass(model, "D3@f5") == pytest.approx(math.radians(240))
        assert _mass(model, "D2@f6") == pytest.approx(math.radians(40))
