"""Live: Feature verzahnung (Spec 4b §4) – Stirnrad auf einer Welle, Zahnstange auf einem Rücken, Achse als Referenz,
Messung der Verzahnung und Negativfall Zahnweite (SolidWorks muss laufen)."""

import pytest

from swki.compiler.anker import zylinder_zu_punkten
from swki.compiler.topologie import flaechen, koerper
from swki.pruefung.geometrie import volumen_auto

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
RAD = {
    "art": "teil", "name": "Rad", "parameter": {"M": 2, "Z": 20, "B": 16, "AS": -0.05, "L": 20},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 12}}]},
         "ende": {"typ": "blind", "tiefe": "=L"}},
        {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": "=L"}},
         "mitte": [0, 0], "modul": "=M", "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
}
STANGE = {
    "art": "teil", "name": "Stange", "parameter": {"M": 2, "Z": 9, "B": 20, "AS": -0.05, "H": 15},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [
             {"rechteck": {"mitte": ["=(Z-1)*pi*M/2", "=-1.25*M-H/2"], "breite": "=Z*pi*M", "hoehe": "=H"}}]},
         "ende": {"typ": "blind", "tiefe": "=B"}},
        {"id": "z1", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": "=M",
         "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
}


def test_stirnrad_auf_welle():
    with gebautes_teil(RAD) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        erg = ctx.ergebnis("z1")
        assert [f.Name for f in erg.features] == ["z1"] and erg.punkte == [(0.0, 0.0, 20.0)]
        assert erg.richtung == (0.0, 0.0, 1.0)
        assert len(koerper(ctx.model)) == 1
        assert volumen_mm3(ctx.model) == pytest.approx(volumen_auto(RAD)[0], rel=1e-3)
        [achse] = zylinder_zu_punkten(flaechen(erg.features[0]), erg.punkte, 0.1)  # Radachse als Referenz
        assert achse.radius == pytest.approx(17.5, abs=1e-3)                       # Fußkreis d_f = 35


def test_zahnstange_auf_ruecken():
    with gebautes_teil(STANGE) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        assert len(koerper(ctx.model)) == 1
        assert volumen_mm3(ctx.model) == pytest.approx(volumen_auto(STANGE)[0], rel=1e-3)
        assert ctx.ergebnis("z1").punkte == []


def test_stirnrad_oben_mit_winkel_und_umkehren():
    spec = {**RAD, "features": [RAD["features"][0] | {"skizze": {"ebene": "oben", "elemente": [
        {"kreis": {"mitte": [0, 0], "durchmesser": 12}}]}},
        RAD["features"][1] | {"ebene": {"versatz": {"ebene": "oben", "abstand": 0}}, "winkel": 9, "umkehren": True}]}
    with gebautes_teil(spec) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        assert ctx.ergebnis("z1").richtung == (0.0, -1.0, 0.0) and len(koerper(ctx.model)) == 1
