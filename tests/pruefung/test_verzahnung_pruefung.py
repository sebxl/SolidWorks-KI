"""Prüfung verzahnungen am Teil (Spec 4b §4.5) ohne SolidWorks: Soll gegen Messwerte, Flankenwahl."""

import math

import pytest

from swki.compiler.anker import AnkerFehler, Flaeche
from swki.pruefung.bewertung import Messwerte, bewerte, verzahnung_abweichungen
from swki.pruefung.messen import waehle_flanke
from swki.verzahnung import Stirnrad, Zahnstange

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5, "verzahnung_mm": 0.005}}
RAD = {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": "vorne", "mitte": [0, 0], "modul": "=M",
       "zaehne": "=Z", "breite": 10, "zahndickenabmass": "=AS"}
STANGE = {"id": "z2", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": 2,
          "zaehne": 3, "breite": 10, "zahndickenabmass": -0.05}
P = {"M": 2, "Z": 20, "AS": -0.05}


def _rad_ist(**aenderungen) -> dict:
    rad = Stirnrad(2, 20, -0.05)
    ist = {"art": "stirnrad", "kopfkreis": 2 * rad.ra, "fusskreis": 2 * rad.rf, "zaehne": 20, "k": 3,
           "zahnweite": rad.zahnweite()}
    return ist | aenderungen


def _stange_ist(**aenderungen) -> dict:
    st = Zahnstange(2, 3, -0.05)
    ist = {"art": "zahnstange", "zaehne": 3, "kopflinie": [2.0], "teilung": [st.p, st.p], "zahndicke": [st.s] * 3}
    return ist | aenderungen


def test_stirnrad_passt():
    assert verzahnung_abweichungen(RAD, _rad_ist(), P, 0.005) == []


def test_stirnrad_abweichungen():
    soll = Stirnrad(2, 20, -0.05).zahnweite()
    fehler = verzahnung_abweichungen(RAD, _rad_ist(zahnweite=soll + 0.01, zaehne=19), P, 0.005)
    assert fehler == [f"zaehne: ist 19 statt 20", f"zahnweite W3: ist {soll + 0.01} statt {round(soll, 6)}"]
    assert verzahnung_abweichungen(RAD, _rad_ist(kopfkreis=44.01), P, 0.005) == ["kopfkreis: ist 44.01 statt 44.0"]


def test_stirnrad_messfehler_ist_abweichung():
    ist = _rad_ist(fehler="Zahnweite nicht messbar: keine Flankenflächen")
    del ist["zahnweite"]
    assert verzahnung_abweichungen(RAD, ist, P, 0.005) == ["Zahnweite nicht messbar: keine Flankenflächen"]


def test_zahnstange():
    assert verzahnung_abweichungen(STANGE, _stange_ist(), {}, 0.005) == []
    fehler = verzahnung_abweichungen(STANGE, _stange_ist(teilung=[2 * math.pi, 2 * math.pi + 0.02]), {}, 0.005)
    assert len(fehler) == 1 and fehler[0].startswith("teilung:")
    assert verzahnung_abweichungen(STANGE, _stange_ist(kopflinie=[2.0, 2.1]), {}, 0.005)[0].startswith("kopflinie:")


def _spec(*features) -> dict:
    return {"art": "teil", "name": "R", "parameter": P, "features": list(features)}


def _messwerte(verzahnungen: dict) -> Messwerte:
    return Messwerte(rebuild_fehler=[], skizzen={}, box=[0] * 6, volumen=1.0, schwerpunkt=(0, 0, 0), material="",
                     eigenschaften={}, verzahnungen=verzahnungen)


def test_bewerte_mit_verzahnung():
    spec = _spec(RAD, STANGE)
    bericht = bewerte(spec, _messwerte({"z1": _rad_ist(), "z2": _stange_ist()}), STANDARD)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "verzahnungen")
    assert pruefung["ok"] is True and pruefung["knoten"] == []
    bericht = bewerte(spec, _messwerte({"z1": _rad_ist(fusskreis=34.9), "z2": "Feature z2 fehlt im Teil"}), STANDARD)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "verzahnungen")
    assert pruefung["ok"] is False and pruefung["knoten"] == ["z1", "z2"]
    assert any(m["pruefung"] == "verzahnungen" for m in bericht["maengel"])


def test_ohne_verzahnung_keine_pruefung():
    spec = _spec({"id": "f1", "typ": "referenz", "achse": "z"})
    assert all(p["id"] != "verzahnungen" for p in bewerte(spec, _messwerte({}), STANDARD)["pruefungen"])


def test_waehle_flanke():
    a = Flaeche("sonstige", (10.0, 1.0, 5.0))
    b = Flaeche("sonstige", (10.0, -1.0, 5.0))
    assert waehle_flanke([a, b], (10.05, 0.9, 0.0), (0.0, 0.0, 1.0), 0.5) is a  # z (Achsrichtung) zählt nicht
    with pytest.raises(AnkerFehler, match="keine Flanke"):
        waehle_flanke([a, b], (12.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.5)
