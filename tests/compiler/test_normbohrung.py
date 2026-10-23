from types import SimpleNamespace

import pytest

from swki.compiler.anker import Flaeche
from swki.compiler.fehler import BauFehler
from swki.compiler.handler import normbohrung as nb
from swki.compiler.handler.normbohrung import hole_werte
from swki.compiler.skizze import Skizzenebene


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


_DECK = {"feature": "f1", "flaeche": "+y"}


def _ebene(lage: float):
    return Skizzenebene(object(), "oben", lage, (0.0, 1.0, 0.0))


def test_positionsskizze_ohne_bezug_behaelt_die_flaeche(monkeypatch):
    monkeypatch.setattr(nb, "loese_flaeche", lambda ctx, anker: pytest.fail("nicht neu auflösen"))
    alt = _ebene(20.0)
    assert nb.skizzenebene_nach_bohrung(SimpleNamespace(tol_mm=0.1), {"flaeche": _DECK}, alt) is alt
    assert nb.skizzenebene_nach_bohrung(SimpleNamespace(tol_mm=0.1), {"flaeche": _DECK, "bezug": {"u": "ursprung"}},
                                        alt) is alt


def test_positionsskizze_mit_bezug_loest_die_flaeche_nach_dem_bohren_neu_auf(monkeypatch):
    neu = Flaeche("ebene", (0.0, 20.0, 0.0), normale=(0.0, 1.0, 0.0), objekt=object())
    monkeypatch.setattr(nb, "loese_flaeche", lambda ctx, anker: neu)
    se = nb.skizzenebene_nach_bohrung(SimpleNamespace(tol_mm=0.1), {"flaeche": _DECK, "bezug": {"u": "-rand"}},
                                      _ebene(20.0))
    assert se.flaeche is neu


@pytest.mark.parametrize("loese", [
    lambda ctx, anker: Flaeche("ebene", (0.0, 12.0, 0.0), normale=(0.0, 1.0, 0.0)),  # andere Ebene (Senkungsgrund)
    lambda ctx, anker: (_ for _ in ()).throw(BauFehler("REFERENZ_NICHT_GEFUNDEN", "keine Fläche")),  # {nahe} im Loch
])
def test_positionsskizze_behaelt_die_alte_flaeche_ohne_passende_neue(monkeypatch, loese):
    monkeypatch.setattr(nb, "loese_flaeche", loese)
    alt = _ebene(20.0)
    assert nb.skizzenebene_nach_bohrung(SimpleNamespace(tol_mm=0.1), {"flaeche": _DECK, "bezug": {"v": "mitte"}},
                                        alt) is alt


def test_positionsskizze_mehrdeutige_flaeche_ist_ein_baufehler(monkeypatch):
    def loese(ctx, anker):
        raise BauFehler("REFERENZ_MEHRDEUTIG", "zwei Flächen")

    monkeypatch.setattr(nb, "loese_flaeche", loese)
    with pytest.raises(BauFehler) as e:
        nb.skizzenebene_nach_bohrung(SimpleNamespace(tol_mm=0.1), {"flaeche": _DECK, "bezug": {"u": "-rand"}},
                                     _ebene(20.0))
    assert e.value.code == "REFERENZ_MEHRDEUTIG"


class _Modell:
    """Attrappe: die Instanzen der weiteren Positionen erscheinen erst mit dem `ab`-ten ForceRebuild3 (live belegt:
    SolidWorks übernimmt die Punkte der Positionsskizze verzögert, ein Neuaufbau davor erzeugt nur die erste Bohrung)."""

    EditRebuild3 = True
    Extension = SimpleNamespace(GetWhatsWrongCount=0)

    def __init__(self, ab: int | None):
        self.ab, self.neuaufbauten = ab, 0

    def ForceRebuild3(self, nur_oben):
        self.neuaufbauten += 1
        return True

    def zylinder(self):
        if self.ab is not None and self.neuaufbauten >= self.ab:
            return [_zylinder(-30, -10), _zylinder(30, -10)]
        return [_zylinder(-30, -10)]


class _Uhr:
    def __init__(self):
        self.t, self.pausen = 0.0, []

    def __call__(self):
        return self.t

    def schlafe(self, s):
        self.pausen.append(s)
        self.t += s


_PUNKTE = [(-30.0, 20.0, -10.0), (30.0, 20.0, -10.0)]


def _abwarten(monkeypatch, ab):
    modell, uhr = _Modell(ab), _Uhr()
    monkeypatch.setattr(nb, "flaechen", lambda feature: modell.zylinder())
    ctx = SimpleNamespace(tol_mm=0.1, model=modell)
    return modell, uhr, lambda: nb._neu_aufbauen_bis_vollstaendig(ctx, None, "f2", _PUNKTE, uhr.schlafe, uhr)


def test_neuaufbau_sofort_vollstaendig(monkeypatch):
    modell, uhr, aufruf = _abwarten(monkeypatch, 1)
    assert aufruf() == 1
    assert modell.neuaufbauten == 1 and uhr.pausen == []


def test_neuaufbau_wiederholt_bis_die_instanzen_da_sind(monkeypatch):
    modell, uhr, aufruf = _abwarten(monkeypatch, 3)
    assert aufruf() == 3
    assert modell.neuaufbauten == 3 and len(uhr.pausen) == 2


def test_neuaufbau_gibt_nach_der_frist_auf(monkeypatch):
    modell, uhr, aufruf = _abwarten(monkeypatch, None)
    with pytest.raises(BauFehler) as e:
        aufruf()
    assert e.value.code == "FEATURE_NICHT_ERZEUGT"
    assert "Position 2 fehlt" in str(e.value) and f"nach {modell.neuaufbauten} Neuaufbauten" in str(e.value)
    assert uhr.t >= nb._FRIST_S and modell.neuaufbauten > 2
