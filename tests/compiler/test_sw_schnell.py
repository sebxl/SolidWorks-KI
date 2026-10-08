"""Schnellmodus und unsichtbares Anlegen (Messstand Umbau 1/2) ohne SolidWorks."""

from pathlib import Path

import pytest

from swki.compiler import sw


class _App:
    def __init__(self, fehler=False):
        self.log, self.fehler, self.CommandInProgress = [], fehler, False

    def DocumentVisible(self, sichtbar, typ):
        self.log.append(("sichtbar", sichtbar, typ))

    def NewDocument(self, vorlage, *a):
        self.log.append(("neu", vorlage))
        if self.fehler:
            raise RuntimeError("COM")
        return object()


def test_neues_teil_unsichtbar_und_danach_wieder_sichtbar():
    app = _App()
    assert sw.neues_teil(app, Path("v.prtdot")) is not None
    assert app.log == [("sichtbar", False, 1), ("neu", "v.prtdot"), ("sichtbar", True, 1)]


def test_neues_teil_setzt_sichtbarkeit_auch_nach_fehler_zurueck():
    app = _App(fehler=True)
    with pytest.raises(RuntimeError):
        sw.neues_teil(app, Path("v.prtdot"))
    assert app.log[-1] == ("sichtbar", True, 1)


class _Obj:
    pass


def test_schnell_setzt_zurueck_und_ueberspringt_fehlende_schalter():
    app, model = _App(), _Obj()
    model.ActiveView = None                       # unsichtbares Dokument: keine Ansicht
    model.SketchManager, model.FeatureManager = _Obj(), _Obj()
    with pytest.raises(ValueError):
        with sw.schnell(app, model):
            assert app.CommandInProgress is True and model.SketchManager.DisplayWhenAdded is False
            raise ValueError
    assert app.CommandInProgress is False and model.SketchManager.DisplayWhenAdded is True
    assert model.FeatureManager.EnableFeatureTree is True
