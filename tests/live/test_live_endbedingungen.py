"""Live: Endbedingungen bis_flaeche und versatz_von_flaeche (SolidWorks muss laufen)."""

import math

import pythoncom
import pytest

from swki.compiler import sw
from swki.compiler.anker import flaeche_in_richtung
from swki.compiler.topologie import flaechen

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
VOLL = 100 * 60 * 20
KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
DECKFLAECHE = {"feature": "f1", "flaeche": "+y"}
UNTERSEITE = {"feature": "f1", "flaeche": "-y"}


def _spec(*features, parameter=None):
    return {"art": "teil", "name": "T", "parameter": parameter or {}, "features": [KLOTZ, *features]}


def test_tasche_mit_restwandstaerke():
    tasche = {"id": "f2", "typ": "schnitt",
              "skizze": {"ebene": DECKFLAECHE, "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 20, "hoehe": 20}}]},
              "ende": {"typ": "versatz_von_flaeche", "flaeche": UNTERSEITE, "abstand": "=RW"}}
    with gebautes_teil(_spec(tasche, parameter={"RW": 5})) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 400 * 15, abs=1e-3)
        boden = flaeche_in_richtung(flaechen(ctx.ergebnis("f2").features[0]), "+y")
        assert boden.punkt[1] == pytest.approx(5, abs=1e-6)
        g = ctx.model.GetEquationMgr
        texte = [g.Equation(i) for i in range(g.GetCount)]
        assert '"D1@f2" = "RW"' in texte
        dispid = g._oleobj_.GetIDsOfNames("Equation")
        g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, texte.index('"RW" = 5'), '"RW" = 8')
        g.EvaluateAll
        sw.rebuild(ctx.model)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 400 * 12, abs=1e-3)


def test_durchbruch_bis_flaeche():
    durchbruch = {"id": "f2", "typ": "schnitt",
                  "skizze": {"ebene": DECKFLAECHE, "elemente": [{"kreis": {"mitte": [10, 5], "durchmesser": 10}}]},
                  "ende": {"typ": "bis_flaeche", "flaeche": UNTERSEITE}}
    with gebautes_teil(_spec(durchbruch)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - math.pi * 25 * 20, abs=1e-3)


def test_aufsatz_bis_flaeche():
    zapfen = {"id": "f2", "typ": "extrusion",
              "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": 40}},
                         "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 10}}]},
              "ende": {"typ": "bis_flaeche", "flaeche": DECKFLAECHE, "umkehren": True}}
    with gebautes_teil(_spec(zapfen)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL + math.pi * 25 * 20, abs=1e-3)
        assert sw.teilebox_mm(ctx.model)[4] == pytest.approx(40, abs=1e-6)
