"""Live: typ austragung (Paket Konstruktionsstil) – Aufsatz und Schnitt, Bogen in beide Richtungen, Volumen wie
volumen: auto, Maße im Protokoll. SolidWorks muss laufen."""

import copy

import pytest

from swki.pruefung.geometrie import volumen_auto
from swki.pruefung.messen import rebuild_fehler

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
SW_AUSGEBLENDET = 1  # IFeature.Visible (swVisibilityState_e: 1 ausgeblendet, 2 sichtbar)

BLOCK = {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [30, 0], "breite": 80, "hoehe": 120}}]},
         "ende": {"typ": "mittig", "tiefe": 20}}
KANAL = {"id": "k1", "typ": "austragung",
         "profil": {"ebene": "rechts", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": "=D"}}]},
         "pfad": {"ebene": "oben", "start": [0, 0],
                  "segmente": [{"linie": ["=L", 0]}, {"bogen": ["=L+R", "=R"], "mitte": ["=L", "=R"]}, {"linie": ["=L+R", 50]}]}}
P = {"D": 8, "L": 40, "R": 20}


def _pruefe(spec):
    with gebautes_teil(spec) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        assert rebuild_fehler(ctx.model) == []
        soll, grund = volumen_auto(spec)
        assert grund == "analytisch"
        assert volumen_mm3(ctx.model) == pytest.approx(soll, abs=1e-3)
        f, ebenen = ctx.model.FirstFeature, []
        while f is not None:  # Versatzebenen ausgeblendet wie Standardebenen (Screenshots, Konstruktionsstil)
            if f.GetTypeName2 == "RefPlane":
                ebenen.append(f.Visible)
            f = f.GetNextFeature
        assert set(ebenen) == {SW_AUSGEBLENDET}, ebenen
        return {m["pfad"] for k in protokoll.knoten for m in (k.masse or [])}


def test_austragung_aufsatz():
    pfade = _pruefe({"art": "teil", "name": "T", "parameter": P, "features": [KANAL]})
    assert "features[0].profil.elemente[0].kreis.durchmesser" in pfade
    assert {"features[0].pfad.segmente[0].linie[0]", "features[0].pfad.segmente[1].mitte[1]"} <= pfade


def test_austragung_schnitt_im_uhrzeigersinn():
    kanal = copy.deepcopy(KANAL)
    kanal["schnitt"] = True
    kanal["profil"]["elemente"][0]["kreis"]["mitte"] = [0, 5]            # Kanal 5 über der Mitte, Pfad auf einer
    kanal["pfad"]["ebene"] = {"versatz": {"ebene": "oben", "abstand": 5}}  # Versatzebene (wird ausgeblendet)
    kanal["pfad"]["segmente"] = [{"linie": ["=L", 0]},
                                 {"bogen": ["=L+R", "=-R"], "mitte": ["=L", "=-R"], "uhrzeigersinn": True},
                                 {"linie": ["=L+R", -50]}]
    _pruefe({"art": "teil", "name": "T", "parameter": P, "features": [BLOCK, kanal]})
