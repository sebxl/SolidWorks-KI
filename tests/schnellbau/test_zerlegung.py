"""Konvexe Zerlegung (Spec C1 §2): Volumen exakt, jedes Stück konvex bis auf die Pfeilhöhe."""

import math

import pytest

pytest.importorskip("build123d")

from scipy.spatial import ConvexHull  # noqa: E402

from swki.schnellbau.teil import baue  # noqa: E402
from swki.schnellbau.zerlegung import bericht, zerlege  # noqa: E402


def _teil(*features):
    return baue({"art": "teil", "name": "z", "parameter": {}, "features": list(features)})


L_PROFIL = {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "vorne", "elemente": [{"polygon": {
    "punkte": [[0, 0], [40, 0], [40, 10], [10, 10], [10, 30], [0, 30]]}}]}, "ende": {"typ": "blind", "tiefe": 5}}


def test_l_profil_zwei_stuecke_exakt():
    t = _teil(L_PROFIL)
    st = zerlege(t.solid)
    b = bericht(t.solid, st)
    assert b["stuecke"] == 2
    assert b["volumen_stuecke"] == pytest.approx(t.solid.volume)
    assert b["fuellfehler_mm3"] == pytest.approx(0, abs=1e-6)


def test_konvexer_koerper_bleibt_ganz():
    klotz = dict(L_PROFIL, skizze={"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 30}}]})
    st = zerlege(_teil(klotz).solid)
    assert len(st) == 1


def test_tasche_mit_innenradius_pfeilhoehe():
    tol = 0.01
    klotz = {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": 60, "hoehe": 40}}]}, "ende": {"typ": "blind", "tiefe": 10}}
    tasche = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"}, "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": 30, "hoehe": 20, "radius": 4}}]}, "ende": {"typ": "blind", "tiefe": 5}}
    t = _teil(klotz, tasche)
    st = zerlege(t.solid, tol)
    b = bericht(t.solid, st)
    assert b["volumen_stuecke"] == pytest.approx(t.solid.volume)
    # Füllfehler höchstens Pfeilhöhe × Fläche der konkaven Radien (4 Viertelzylinder, Höhe 5)
    assert 0 <= b["fuellfehler_mm3"] <= tol * 4 * (math.pi / 2 * 4) * 5
    for s in st:
        assert ConvexHull(s.punkte).volume == pytest.approx(s.huellvolumen)
