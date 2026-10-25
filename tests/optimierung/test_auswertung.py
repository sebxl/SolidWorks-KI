"""Reine Bewertungslogik des Runners (Spec C2 §3, §4): Kennzahlen, Fehlerbilder, Nebenbedingungen, Stillstand,
Grenzanschlag, Belastbarkeit."""

import pytest

from swki.optimierung.auswertung import (Fortschritt, belastbar, erweitere, fehlerbilder, grenzanschlaege, kennzahlen,
                                         verletzung, wilson)


def _l(ergebnis, fehlerbild=None, gueltig=True):
    return {"ergebnis": ergebnis, "fehlerbild": fehlerbild, "gueltig": gueltig}


LAEUFE = {"a": [_l("richtig")] * 8 + [_l("falsch", "Abprall am Keil")] * 2,
          "b": [_l("richtig")] * 9 + [_l("liegt", "liegt an der Kante"), _l("falsch", gueltig=False)]}


def test_kennzahlen_nur_gueltige_laeufe():
    k = kennzahlen(LAEUFE)
    assert k["anteil_richtig:a"] == 0.8 and k["anteil_richtig:b"] == 0.9
    assert k["min_anteil_richtig"] == 0.8 and k["mittel_anteil_richtig"] == pytest.approx(0.85)
    assert k["anteil_ungueltig"] == pytest.approx(1 / 21)
    assert k["gueltig:b"] == 10


def test_fehlerbilder_als_anteile_aller_gueltigen_laeufe():
    f = fehlerbilder(LAEUFE)
    assert f == {"Abprall am Keil": pytest.approx(2 / 20), "liegt an der Kante": pytest.approx(1 / 20)}


def test_fehlerbild_ohne_klasse_nach_ergebnis():
    assert fehlerbilder({"a": [_l("richtig"), _l("verklemmt")]}) == {"verklemmt": 0.5}


@pytest.mark.parametrize("ausdruck, wert", [("min_anteil_richtig >= 0.9", 0.1), ("min_anteil_richtig >= 0.5", -0.3),
                                            ("abstand <= 4", 1.0), ("fehlt >= 1", float("inf"))])
def test_verletzung(ausdruck, wert):
    assert verletzung(ausdruck, {"min_anteil_richtig": 0.8, "abstand": 5.0}) == pytest.approx(wert)


def test_wilson():
    lo, hi = wilson(1992, 1992)
    assert lo == pytest.approx(0.99807, abs=1e-4) and hi == 1.0
    assert wilson(0, 0) == (0.0, 1.0)


def test_fortschritt_stillstand_nach_proben_und_minuten():
    f = Fortschritt(maximieren=True, epsilon=0.01, proben=3, minuten=None)
    f.melde(0, 0.5, 0.0)
    f.melde(1, 0.505, 1.0)              # unter epsilon: keine Verbesserung
    f.melde(2, 0.7, 2.0)
    assert f.bester == (2, 0.7) and not f.stillstand(4, 3.0)
    f.melde(3, 0.701, 3.0)
    f.melde(4, None, 4.0)               # verworfene Probe zählt als Probe
    f.melde(5, 0.6, 5.0)
    assert f.stillstand(5, 5.0)
    g = Fortschritt(maximieren=False, epsilon=0.0, proben=None, minuten=1.0)
    g.melde(0, 3.0, 0.0)
    g.melde(1, 2.0, 30.0)
    assert not g.stillstand(1, 80.0) and g.stillstand(1, 91.0)
    g.neu_beginnen(91.0)                # neue Phase: Uhr und Zähler von vorn, Bester bleibt
    assert not g.stillstand(1, 120.0) and g.bester == (1, 2.0)


def test_grenzanschlag_und_erweitern():
    bereich = {"T": (180.0, 196.0), "Y": (195.0, 225.0)}
    rahmen = {"T": (176.0, 196.0), "Y": (195.0, 225.0)}
    a = grenzanschlaege({"T": 180.1, "Y": 210.0}, bereich, rahmen)
    assert a == [{"name": "T", "seite": "unten", "wert": 180.1, "bereich": [180.0, 196.0], "erweiterbar": True}]
    assert grenzanschlaege({"T": 195.95, "Y": 195.2}, bereich, rahmen) == [
        {"name": "T", "seite": "oben", "wert": 195.95, "bereich": [180.0, 196.0], "erweiterbar": False},
        {"name": "Y", "seite": "unten", "wert": 195.2, "bereich": [195.0, 225.0], "erweiterbar": False}]
    assert erweitere((180.0, 196.0), (176.0, 196.0), "unten") == (176.0, 196.0)       # halbe Spanne, gekappt
    assert erweitere((100.0, 110.0), (0.0, 200.0), "oben") == (100.0, 115.0)


def test_belastbar_im_wilson_bereich():
    stufe1 = {"a": (190, 192), "b": (192, 192)}
    assert belastbar(stufe1, {"a": (380, 384), "b": (383, 384)})
    assert not belastbar(stufe1, {"a": (300, 384), "b": (384, 384)})
