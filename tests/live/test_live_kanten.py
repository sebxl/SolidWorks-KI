"""Live: Verrundung und Fase (SolidWorks muss laufen)."""

import math

import pytest

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
VOLL = 100 * 60 * 20


def _spec(*features, **weiteres):
    return {"art": "teil", "name": "T", "features": [KLOTZ, *features], **weiteres}


def test_verrundung_senkrechte_kanten():
    f = {"id": "f2", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": 5}
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 4 * (1 - math.pi / 4) * 25 * 20, abs=1e-3)


def test_fase_mit_tangentenfortsetzung():
    rund = {"id": "f2", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": 5}
    fase = {"id": "f3", "typ": "fase", "kanten": [{"nahe": [50, 20, 0]}], "abstand": 1}
    with gebautes_teil(_spec(rund, fase)) as (ctx, fehler, _):
        assert fehler is None
        umfang = 2 * (100 - 10) + 2 * (60 - 10) + 2 * math.pi * 5
        vorher = VOLL - 4 * (1 - math.pi / 4) * 25 * 20
        # eine Kante gewählt, umlaufend gefast (Querschnitt 0,5 mm²); Eckbereiche weichen minimal ab
        assert volumen_mm3(ctx.model) == pytest.approx(vorher - 0.5 * umfang, abs=2.0)


def test_fase_mehrdeutiger_punkt():
    fase = {"id": "f2", "typ": "fase", "kanten": [{"nahe": [50, 20, 30]}], "abstand": 1}  # Ecke: 3 Kanten
    with gebautes_teil(_spec(fase)) as (_, fehler, _):
        assert fehler.code == "REFERENZ_MEHRDEUTIG"
