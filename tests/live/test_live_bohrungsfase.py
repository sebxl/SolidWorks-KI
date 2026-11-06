"""Live: Feld `fase` an bohrung und normbohrung (Paket Konstruktionsstil) – Feature <id>_fase, Volumen, Muster.

SolidWorks muss laufen."""

import math

import pytest

from swki.pruefung.messen import rebuild_fehler

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}
FLAECHE = {"feature": "f1", "flaeche": "+y"}


def _bohrungen(mit_fase: bool) -> list[dict]:
    fase = (lambda w: {"fase": w}) if mit_fase else (lambda w: {})
    return [
        {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": FLAECHE,
         "positionen": [[-30, 0]], "tiefe": 15, "gewindetiefe": 12, **fase("nenn")},
        {"id": "f3", "typ": "bohrung", "flaeche": FLAECHE, "positionen": [[0, 0]], "durchmesser": 6.6, "durch": True,
         "senkung": {"durchmesser": 11, "tiefe": 6.8}, **fase(0.5)},
        {"id": "f4", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": FLAECHE, "positionen": [[30, 0]],
         "tiefe": 10, **fase("=FB")},
    ]


def _fase_mm3(r: float, c: float) -> float:
    return math.pi * c * (r * c + c * c / 3)


def test_bohrungsfase_drei_arten():
    volumen = {}
    for mit in (False, True):
        spec = {"art": "teil", "name": "T", "parameter": {"FB": 0.5}, "features": [PLATTE, *_bohrungen(mit)]}
        with gebautes_teil(spec) as (ctx, fehler, protokoll):
            assert fehler is None
            assert rebuild_fehler(ctx.model) == []
            volumen[mit] = volumen_mm3(ctx.model)
            if mit:
                namen = {fid: [x.Name for x in ctx.ergebnis(fid).features] for fid in ("f2", "f3", "f4")}
                assert namen == {"f2": ["f2", "f2_fase"], "f3": ["f3", "f3_senkung", "f3_fase"], "f4": ["f4", "f4_fase"]}
                d = ctx.model.FeatureByName("f2_fase").GetDefinition
                assert d.GetEdgeChamferDistance(0) * 1000 == pytest.approx(0.6)
                masse = {m["name"]: m["pfad"] for k in protokoll.knoten for m in (k.masse or [])}
                assert masse.get("D1@f3_fase") == "features[2].fase" and "D1@f2_fase" not in masse
    soll = _fase_mm3(3.4, 0.6) + _fase_mm3(5.5, 0.5) + _fase_mm3(4.0, 0.5)
    assert volumen[False] - volumen[True] == pytest.approx(soll, abs=1e-3)


def test_muster_nimmt_bohrungsfase_mit():
    loch = {"id": "f2", "typ": "bohrung", "flaeche": FLAECHE, "positionen": [[-40, 0]], "durchmesser": 6, "durch": True,
            "fase": 0.5}
    muster = {"id": "f3", "typ": "muster_linear", "features": ["f2"], "richtung1": {"achse": "x", "abstand": 20, "anzahl": 5}}
    with gebautes_teil({"art": "teil", "name": "T", "features": [PLATTE, loch, muster]}) as (ctx, fehler, _):
        assert fehler is None
        d = ctx.model.FeatureByName("f3").GetDefinition
        assert {q.Name for q in d.PatternFeatureArray} == {"f2", "f2_fase"}
        soll = 100 * 60 * 20 - 5 * (math.pi * 9 * 20 + _fase_mm3(3.0, 0.5))
        assert volumen_mm3(ctx.model) == pytest.approx(soll, abs=1e-3)
