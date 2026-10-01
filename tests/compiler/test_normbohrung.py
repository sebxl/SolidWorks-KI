from types import SimpleNamespace

import pytest

from swki.compiler.anker import Flaeche
from swki.compiler.fehler import BauFehler
from swki.compiler.handler import normbohrung as nb
from swki.compiler.handler.normbohrung import hole_werte


def test_gewinde_mit_gewindetiefe():
    assert hole_werte("gewinde", 0.012) == [0.012, -1, -1, -1, -1, -1, 2, 0, -1, -1, -1, -1]


def test_gewinde_durchgehend():
    werte = hole_werte("gewinde", None)
    assert werte[0] == -1 and werte[6] == 2 and werte[7] == 1


def test_zylinderschraube_normale_passung():
    assert hole_werte("zylinderschraube", None) == [-1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1]


def test_stift_nur_normwerte():
    assert hole_werte("stift", None) == [-1.0] * 12


def _zylinder(x, z):
    return Flaeche("zylinder", (x, 10.0, z), achse=(0.0, 1.0, 0.0), radius=4.0)


def test_bohrungen_pruefen_findet_jede_position(monkeypatch):
    monkeypatch.setattr(nb, "flaechen", lambda feature: [_zylinder(-30, -10), _zylinder(30, -10),
                                                          Flaeche("ebene", (0, 20, 0), normale=(0, 1, 0))])
    nb._bohrungen_pruefen(SimpleNamespace(tol_mm=0.1), None, "f2", [(-30.0, 20.0, -10.0), (30.0, 20.0, -10.0)])


def test_bohrungen_pruefen_meldet_fehlende_position(monkeypatch):
    monkeypatch.setattr(nb, "flaechen", lambda feature: [_zylinder(-30, -10)])
    with pytest.raises(BauFehler) as e:
        nb._bohrungen_pruefen(SimpleNamespace(tol_mm=0.1), None, "f2", [(-30.0, 20.0, -10.0), (30.0, 20.0, -10.0)])
    assert "Position 2 fehlt" in str(e.value)
