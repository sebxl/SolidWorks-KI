"""Live: Extrusion und Schnitt (SolidWorks muss laufen)."""

import pythoncom
import pytest

from swki.compiler import sw

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": "=H"},
}


def _spec(*features, parameter=None):
    return {"art": "teil", "name": "T", "parameter": parameter or {"L": 100, "H": 20}, "features": [KLOTZ, *features]}


def test_extrusion_mit_parametern():
    with gebautes_teil(_spec()) as (ctx, fehler, _):
        assert fehler is None
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-50, 0, -30, 50, 20, 30], abs=1e-6)
        assert ctx.ergebnis("f1").richtung == (0.0, 1.0, 0.0)
        # Parameter sind SW-Gleichungen: "L", "H", Breite = "L", Lage der linken Ecke u = 0 - L/2 (Maß ist der Betrag,
        # daher negiert), Tiefe D1@f1 = "H"; Höhe 60 und Ecke v = -30 sind Zahlen und bekommen keine Gleichung
        gleichungen = ctx.model.GetEquationMgr
        assert [gleichungen.Equation(i) for i in range(gleichungen.GetCount)] == [
            '"L" = 100', '"H" = 20', '"D1@f1_skizze" = "L"', '"D3@f1_skizze" = -(0 - ("L" / 2))', '"D1@f1" = "H"',
        ]
        # L ändern (Property-Put nur per Invoke, S9a) → Teil wird länger
        dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
        gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, 0, '"L" = 120')
        gleichungen.EvaluateAll
        sw.rebuild(ctx.model)
        assert sw.teilebox_mm(ctx.model)[0:4:3] == pytest.approx([-60, 60], abs=1e-6)


def test_extrusion_mittig_und_umgekehrt():
    spec = {"art": "teil", "name": "T", "features": [{
        "id": "f1", "typ": "extrusion",
        "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [10, 5], "durchmesser": 8}}]},
        "ende": {"typ": "mittig", "tiefe": 30},
    }]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert sw.teilebox_mm(ctx.model) == pytest.approx([6, 1, -15, 14, 9, 15], abs=1e-6)


def test_schnitt_tasche_von_deckflaeche():
    tasche = {
        "id": "f2", "typ": "schnitt",
        "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                   "elemente": [{"rechteck": {"mitte": [10, 5], "breite": 20, "hoehe": 10}}]},
        "ende": {"typ": "blind", "tiefe": 5},
    }
    with gebautes_teil(_spec(tasche)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(100 * 60 * 20 - 20 * 10 * 5, abs=1e-3)
        assert ctx.ergebnis("f2").richtung == (0.0, -1.0, 0.0)


def test_schnitt_ohne_material_meldet_fehler():
    daneben = {
        "id": "f2", "typ": "schnitt",
        "skizze": {"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 5}}]},
        "ende": {"typ": "blind", "tiefe": 5},
    }
    with gebautes_teil(_spec(daneben)) as (_, fehler, protokoll):
        assert fehler.code == "FEATURE_NICHT_ERZEUGT"
        assert protokoll.knoten[1].status == "fehler"


def test_skizze_auf_versetzter_ebene():
    spec = {"art": "teil", "name": "T", "features": [{
        "id": "f1", "typ": "extrusion",
        "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": -15}},
                   "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 10, "hoehe": 10}}]},
        "ende": {"typ": "blind", "tiefe": 5},
    }]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-5, -15, -5, 5, -10, 5], abs=1e-6)


def test_quadratisches_rechteck_mit_parametern():
    # Bei einem Quadrat legt CreateCornerRectangle selbst eine Beziehung "gleiche Länge" an (trotz AddToDB); das
    # Maß der zweiten Seite wäre dann überzählig und seine Gleichung scheiterte ("Gleichungen: Code 1", Befund 4a)
    spec = {"art": "teil", "name": "T", "parameter": {"L": 20, "B": 20, "H": 20}, "features": [{
        "id": "f1", "typ": "extrusion",
        "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
        "ende": {"typ": "blind", "tiefe": "=H"},
    }]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-10, 0, -10, 10, 20, 10], abs=1e-6)
        # B allein ändern: die Seiten bleiben unabhängig (keine Gleich-Beziehung mehr)
        gleichungen = ctx.model.GetEquationMgr
        dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
        gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, 1, '"B" = 30')
        gleichungen.EvaluateAll
        sw.rebuild(ctx.model)
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-10, 0, -15, 10, 20, 15], abs=1e-6)
