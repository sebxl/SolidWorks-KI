"""Formschräge im Handler extrusion/schnitt: Parameter an FeatureExtrusion3/FeatureCut4 (ohne SolidWorks)."""

import math
from pathlib import Path

import pytest

from swki.compiler.handler.extrusion import (
    DDIR_KLEINER, ENDE, OHNE_SCHRAEGE, WINKEL_MASS, aufsatz, schnitt, schraege_sw,
)
from swki.compiler.kontext import Kontext


class _FeatureManager:
    def __init__(self):
        self.aufrufe = []

    def FeatureExtrusion3(self, *args):  # noqa: N802 – Name der SolidWorks-API
        self.aufrufe.append(("FeatureExtrusion3", args))
        return "feature"

    def FeatureCut4(self, *args):  # noqa: N802 – Name der SolidWorks-API
        self.aufrufe.append(("FeatureCut4", args))
        return "feature"


class _Model:
    def __init__(self):
        self.FeatureManager = _FeatureManager()


def _ctx(**parameter) -> Kontext:
    return Kontext(None, _Model(), {"parameter": parameter}, Path("t.yaml"), 0.1)


def _f(typ: str, querschnitt: str | None) -> dict:
    ende = {"typ": "blind", "tiefe": 10}
    if querschnitt:
        ende["formschraege"] = {"winkel": "=W", "querschnitt": querschnitt}
    return {"id": "f2", "typ": typ, "skizze": {"ebene": "oben", "elemente": []}, "ende": ende}


@pytest.mark.parametrize(("aufruf", "name", "anzahl"), [(aufsatz, "FeatureExtrusion3", 23), (schnitt, "FeatureCut4", 27)])
def test_schraege_an_index_7_9_11(aufruf, name, anzahl):
    model = _Model()
    aufruf(model, ENDE["blind"], 0.01, False, (True, True, 0.25))
    [(gerufen, args)] = model.FeatureManager.aufrufe
    assert gerufen == name and len(args) == anzahl
    assert (args[7], args[8], args[9], args[10], args[11], args[12]) == (True, False, True, False, 0.25, 0.0)


@pytest.mark.parametrize("aufruf", [aufsatz, schnitt])
def test_ohne_schraege_unveraendert(aufruf):
    model = _Model()
    aufruf(model, ENDE["blind"], 0.01, True)
    [(_, args)] = model.FeatureManager.aufrufe
    assert (args[2], args[7], args[9], args[11]) == (True, False, False, 0.0)


def test_ddir_kleiner_aus_spike():
    # Spike S16, Frage 1: Ddir1 True baut bei Aufsatz und Schnitt (auch mit umkehren) den Querschnitt "groesser"
    assert DDIR_KLEINER == {"extrusion": False, "schnitt": False}


def test_schraege_sw():
    ctx = _ctx(W=15)
    assert schraege_sw(ctx, _f("extrusion", None)) == OHNE_SCHRAEGE
    dchk, ddir, dang = schraege_sw(ctx, _f("extrusion", "kleiner"))
    assert (dchk, ddir) == (True, DDIR_KLEINER["extrusion"]) and dang == pytest.approx(math.radians(15))
    assert schraege_sw(ctx, _f("schnitt", "groesser"))[1] is (not DDIR_KLEINER["schnitt"])


def test_winkelmass_fuer_jede_endbedingung():
    # Spike S16, Frage 4: der Winkel ist bei allen Endbedingungen das Maß D3
    assert WINKEL_MASS == {typ: "D3" for typ in ENDE}
