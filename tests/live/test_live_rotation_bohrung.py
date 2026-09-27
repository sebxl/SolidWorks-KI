"""Live: Rotation und Bohrung, parametrische Lage (SolidWorks muss laufen)."""

import math

import pythoncom
import pytest

from swki.compiler import sw
from swki.compiler.topologie import flaechen

from .bauhilfe import gebautes_teil, volumen_mm3, zylinder_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
VOLL = 100 * 60 * 20
BOHRUNG = {
    "id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
    "positionen": [[-40, 20]], "durchmesser": 8, "durch": True,
}


def _spec(*features, **weiteres):
    return {"art": "teil", "name": "T", "features": [KLOTZ, *features], **weiteres}


def _achsen_xz(feature) -> list[tuple[float, float]]:
    return sorted((round(z.punkt[0], 4), round(z.punkt[2], 4)) for z in flaechen(feature) if z.art == "zylinder")


def test_rotation_rohr_und_nut():
    rohr = {
        "id": "f1", "typ": "rotation",
        "skizze": {"ebene": "vorne", "elemente": [
            {"polygon": {"punkte": [[10, 0], [30, 0], [30, 40], [10, 40]]}},
            {"mittellinie": {"von": [0, -10], "bis": [0, 50]}},
        ]},
    }
    nut = {
        "id": "f2", "typ": "rotation", "schnitt": True,
        "skizze": {"ebene": "vorne", "elemente": [
            {"polygon": {"punkte": [[25, 20], [31, 20], [31, 25], [25, 25]]}},
            {"mittellinie": {"von": [0, -10], "bis": [0, 50]}},
        ]},
    }
    spec = {"art": "teil", "name": "T", "features": [rohr, nut]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        erwartet = math.pi * (30**2 - 10**2) * 40 - math.pi * (30**2 - 25**2) * 5
        assert volumen_mm3(ctx.model) == pytest.approx(erwartet, abs=1e-3)
        assert ctx.ergebnis("f1").richtung == pytest.approx((0, 1, 0))


def test_bohrungen_mit_senkung():
    bohrung = {
        "id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
        "positionen": [[-30, 15], [30, -15]], "durchmesser": 8, "durch": True,
        "senkung": {"durchmesser": 14, "tiefe": 4},
    }
    with gebautes_teil(_spec(bohrung)) as (ctx, fehler, _):
        assert fehler is None
        erg = ctx.ergebnis("f2")
        assert [f.Name for f in erg.features] == ["f2", "f2_senkung"]
        assert erg.punkte == [(-30.0, 20.0, -15.0), (30.0, 20.0, 15.0)]
        erwartet = 100 * 60 * 20 - 2 * (zylinder_mm3(8, 20) + zylinder_mm3(14, 4) - zylinder_mm3(8, 4))
        assert volumen_mm3(ctx.model) == pytest.approx(erwartet, abs=1e-3)


def test_lage_haengt_an_parameter():
    spec = _spec({**BOHRUNG, "positionen": [["=-L/2+10", "=T"]]}, parameter={"L": 100, "T": 20})
    spec["features"][0] = {**KLOTZ, "skizze": {"ebene": "oben", "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]}}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        gleichungen = ctx.model.GetEquationMgr
        dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
        texte = [gleichungen.Equation(i) for i in range(gleichungen.GetCount)]
        i_l = texte.index('"L" = 100')
        gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, i_l, '"L" = 140')
        gleichungen.EvaluateAll
        sw.rebuild(ctx.model)
        # Bohrung bleibt 10 mm vom linken Rand: X = -140/2 + 10 = -60; Z = -T = -20
        assert _achsen_xz(ctx.ergebnis("f2").features[0]) == [(-60.0, -20.0)]
