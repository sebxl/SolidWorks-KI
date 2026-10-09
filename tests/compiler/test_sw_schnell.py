"""Schnellmodus (Messstand Umbau 1) ohne SolidWorks. Unsichtbares Anlegen (DocumentVisible False) wurde in Umbau 2
verworfen: SolidWorks lehnt dann die globalen Variablen ab (GLEICHUNG_FEHLER)."""

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
