"""Zeichnungsableitung Z1.3 Stufe 1: zeichnen.py ohne SolidWorks – Laufwahl und Ansichtserzeugung mit Fake-COM
(Review I1, I5)."""

import pytest

from swki.zeichnung import zeichnen as z
from swki.zeichnung.ansichten import Ansicht


def _lauf(n, bestanden):
    return {"lauf": n, "bestanden": bestanden, "bau": "ok", "code_maengel": 0, "pruefer": "bestanden" if bestanden else None}


def test_letzter_bestandener_lauf(monkeypatch):
    monkeypatch.setattr(z, "lies_laeufe", lambda p: [_lauf(1, True), _lauf(2, False)])
    assert z.waehle_lauf(None, None) == (1, [])


def test_kein_bestandener_lauf_fehler(monkeypatch):
    monkeypatch.setattr(z, "lies_laeufe", lambda p: [_lauf(1, False)])
    with pytest.raises(z.ZeichnungFehler) as e:
        z.waehle_lauf(None, None)
    assert e.value.daten["code"] == "ZEICHNUNG_LAUF_NICHT_BESTANDEN" and "--lauf" in str(e.value)


def test_ausdruecklicher_lauf_mit_meldung(monkeypatch):
    monkeypatch.setattr(z, "lies_laeufe", lambda p: [_lauf(1, False)])
    lauf, meldungen = z.waehle_lauf(None, 1)
    assert lauf == 1 and any("nicht bestanden" in m for m in meldungen)


class _View:
    def __init__(self, name):
        self.GetName2, self.GetOutline, self.Position, self.ScaleDecimal, self.Angle = name, (0.1, 0.1, 0.2, 0.15), (0.15, 0.125), 1.0, 0


class _Drw:
    def __init__(self):
        self.n, self.schnitte = 0, 0
        self.Extension = type("E", (), {"SelectByID2": lambda *a: True})()
        self.SketchManager = type("S", (), {"CreateLine": lambda *a: object()})()

    def _neu(self):
        self.n += 1
        return _View(f"Zeichenansicht{self.n}")

    def CreateDrawViewFromModelView3(self, *a):
        return self._neu()

    def CreateUnfoldedViewAt3(self, *a):
        return self._neu()

    def CreateSectionViewAt5(self, *a):
        self.schnitte += 1
        v = self._neu()
        v.GetName2 = "Schnittansicht A-A"
        return v

    def ActivateView(self, name):
        return True


def test_fraesteil_schnitt_nicht_unterstuetzt_wird_gemeldet():
    drw = _Drw()
    views, schnitt, meldungen = z._erzeuge(drw, z.Path("t.sldprt"),
                                           [Ansicht("haupt", "*Oben"), Ansicht("drauf", None, schnitt=True)])
    assert set(views) == {"haupt", "drauf"} and schnitt is None and drw.schnitte == 0
    assert any("SCHNITT_NICHT_UNTERSTUETZT" in m for m in meldungen)


def test_drehteil_laengsschnitt_aus_stirn():
    drw = _Drw()
    views, schnitt, meldungen = z._erzeuge(drw, z.Path("t.sldprt"),
                                           [Ansicht("seite", "*Oben"), Ansicht("haupt", None, schnitt=True)])
    assert schnitt == "Schnittansicht A-A" and drw.schnitte == 1 and meldungen == []
