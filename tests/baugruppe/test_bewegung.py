"""Stufe 4a: Bewegungslogik ohne SolidWorks – Bewegungen aus der Spec, Lagevergleich, Räume, Paare, Bewertung."""

import math

import pytest

from swki.baugruppe.bewegung import (Bewegung, BewegungsMesswerte, Lauf, achse_winkel, bewegungen, bewerte_bewegungen,
                                     drehmatrix, ergaenze_bericht, ist_bewegt, paare, relative_drehung, schnitt,
                                     soll_weg, vereinige, verschiebung_mm, weg, winkel_grad)
from swki.konfig import lade_standard
from tests.baugruppe.beispiel_bewegung import BAUGRUPPE, kopie

EINS = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _t(c, v=(0.0, 0.0, 0.0)) -> list[float]:
    """Transform2.ArrayData aus der Spaltenform c (C · p = Bild von p) und einer Verschiebung in mm."""
    return [c[k % 3][k // 3] for k in range(9)] + [x / 1000 for x in v] + [1.0, 0.0, 0.0, 0.0]


def _mal(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _bws():
    return bewegungen(BAUGRUPPE, lade_standard())


def test_bewegungen_aus_der_spec():
    assert _bws() == [Bewegung("Hub", "g1", "abstand", "schieber", 0.0, 100.0, 4),
                      Bewegung("Schwenk", "g2", "winkel", "hebel", 0.0, 90.0, 4)]


def test_schritte_aus_der_vorgabe():
    spec = kopie(BAUGRUPPE)
    del spec["bewegungen"][0]["schritte"]
    assert bewegungen(spec, {"bewegung_schritte": 16})[0].schritte == 16


def test_stellungen():
    hub = _bws()[0]
    assert hub.schrittweite == 25.0 and hub.stellungen() == [0.0, 25.0, 50.0, 75.0, 100.0]


def test_verschiebung_und_weg():
    hub = _bws()[0]
    t0, t1 = _t(EINS, (-70, 30, -10)), _t(EINS, (30, 30, -10))
    assert verschiebung_mm(t0, t1) == pytest.approx((100.0, 0.0, 0.0))
    assert weg(hub, t0, t1) == pytest.approx(100.0)


def test_drehung_achse_und_winkel():
    t1 = _t(drehmatrix((0, 1, 0), 90))
    achse, winkel = achse_winkel(relative_drehung(_t(EINS), t1))
    assert achse == pytest.approx((0.0, 1.0, 0.0)) and winkel == pytest.approx(90.0)
    assert weg(_bws()[1], _t(EINS), t1) == pytest.approx(90.0)
    assert [c * 1 for c in drehmatrix((0, 1, 0), 90)[2]] == pytest.approx([-1.0, 0.0, 0.0])  # +x → −z


def test_relative_drehung_bei_gedrehter_ausgangslage():
    c0 = drehmatrix((0, 0, 1), 30)
    q = relative_drehung(_t(c0), _t(_mal(drehmatrix((0, 1, 0), 90), c0)))
    assert winkel_grad(_mal(q, [list(r) for r in zip(*drehmatrix((0, 1, 0), 90))])) == pytest.approx(0.0, abs=1e-6)


def test_ist_bewegt():
    assert not ist_bewegt(_t(EINS, (1, 2, 3)), _t(EINS, (1, 2, 3.0005)))
    assert ist_bewegt(_t(EINS, (1, 2, 3)), _t(EINS, (1, 2, 3.01)))
    assert ist_bewegt(_t(EINS), _t(drehmatrix((0, 1, 0), 0.01)))


def test_soll_weg_winkel_gefaltet():
    schwenk = Bewegung("S", "g", "winkel", "k", 0.0, 300.0, 4)
    assert soll_weg(schwenk, 270) == pytest.approx(90.0) and soll_weg(schwenk, 92.8) == pytest.approx(92.8)
    assert soll_weg(Bewegung("H", "g", "abstand", "k", 10.0, 50.0, 4), 5) == pytest.approx(5.0)


def test_vereinige_und_schnitt():
    a, b = [0, 0, 0, 10, 10, 10], [5, 5, 5, 20, 20, 20]
    assert vereinige(None, a) == a and vereinige(a, b) == [0, 0, 0, 20, 20, 20]
    assert schnitt(a, b) == [5, 5, 5, 10, 10, 10]
    assert schnitt(a, [10, 0, 0, 20, 10, 10]) is None  # nur Berührung


def test_paare():
    a, b, c = (Bewegung(n, "g", "abstand", "k", 0.0, 1.0, 2) for n in "ABC")
    grund = {"A": Lauf("A", raum=[0, 0, 0, 10, 10, 10]), "B": Lauf("B", raum=[5, 5, 5, 20, 20, 20]),
             "C": Lauf("C", raum=[50, 50, 50, 60, 60, 60])}
    assert paare([a, b, c], grund) == [(a, b, [5, 5, 5, 10, 10, 10])]


def _messwerte(hub_ende=(100, 0, 0), achse=(0, -1, 0), frei=None, gehalten=None, grenze=None, kollisionen=(), fehler=None):
    hub = Lauf("Hub", stellungen=[0.0, 100.0], fehler=fehler, grenze=grenze or {"oben": False, "unten": None},
               lagen=[{"schieber": _t(EINS), "hebel": _t(EINS)},
                      {"schieber": _t(EINS, hub_ende), "hebel": _t(EINS, hub_ende)}])
    schwenk = Lauf("Schwenk", stellungen=[0.0, 90.0], grenze={"oben": False, "unten": None},
                   lagen=[{"hebel": _t(EINS)}, {"hebel": _t(drehmatrix(achse, 90))}])
    paar = Lauf("Schwenk", gegen={"Hub": "max"}, stellungen=[0.0, 90.0], kollisionen=list(kollisionen))
    return BewegungsMesswerte(frei or {"schieber": 2, "hebel": 2}, gehalten or {"schieber": 3, "hebel": 3},
                              [hub, schwenk, paar], [])


def _pruefungen(m):
    pruefungen, _ = bewerte_bewegungen(kopie(BAUGRUPPE), _bws(), m, 0.1)
    return {p["id"]: p for p in pruefungen}


def test_bewertung_bestanden():
    pruefungen, bericht = bewerte_bewegungen(kopie(BAUGRUPPE), _bws(), _messwerte(), 0.1)
    assert [p["id"] for p in pruefungen] == [
        "freiheitsgrad:schieber", "bewegung:Hub", "bewegung_kollision:Hub", "grenze:Hub", "endlage:Hub:schieber",
        "endlage:Hub:hebel", "freiheitsgrad:hebel", "bewegung:Schwenk", "bewegung_kollision:Schwenk", "grenze:Schwenk",
        "endlage:Schwenk:hebel"]
    assert all(p["ok"] is True for p in pruefungen), pruefungen
    assert [(x["bewegung"], x["gegen"], x["stellungen"]) for x in bericht["laeufe"]] == [
        ("Hub", {}, 2), ("Schwenk", {}, 2), ("Schwenk", {"Hub": "max"}, 2)]


def test_endlage_falsche_richtung():
    p = _pruefungen(_messwerte(hub_ende=(-100, 0, 0)))
    assert p["endlage:Hub:schieber"]["ok"] is False and p["endlage:Hub:schieber"]["ist"] == pytest.approx([-100, 0, 0])
    assert p["endlage:Hub:hebel"]["ok"] is False


def test_endlage_falsche_drehachse():
    p = _pruefungen(_messwerte(achse=(0, 1, 0)))["endlage:Schwenk:hebel"]
    assert p["ok"] is False and p["abweichung_grad"] == pytest.approx(180.0)
    assert p["ist"]["achse"] == pytest.approx([0, 1, 0]) and p["ist"]["winkel"] == pytest.approx(90.0)


def test_freiheitsgrad():
    p = _pruefungen(_messwerte(frei={"schieber": 3, "hebel": 2}, gehalten={"schieber": 3, "hebel": 2}))
    assert p["freiheitsgrad:schieber"]["ok"] is False and "nicht beweglich" in p["freiheitsgrad:schieber"]["hinweis"]
    assert p["freiheitsgrad:hebel"]["ok"] is False
    assert "mehr als ein Freiheitsgrad offen" in p["freiheitsgrad:hebel"]["hinweis"]


def test_grenze_geht_durch():
    p = _pruefungen(_messwerte(grenze={"oben": True, "unten": None}))["grenze:Hub"]
    assert p["ok"] is False and "oben" in p["hinweis"]


def test_kollision_und_lauffehler():
    kollision = {"paar": ["anschlag", "hebel"], "volumen": 5.0, "stellung": 67.5, "gegen": {"Hub": "max"}, "bild": "x.png"}
    p = _pruefungen(_messwerte(kollisionen=[kollision], fehler={"stellung": 50.0, "meldung": "Rebuild-Fehler"}))
    assert p["bewegung_kollision:Schwenk"]["ok"] is False and p["bewegung_kollision:Schwenk"]["knoten"] == ["anschlag", "hebel"]
    assert p["bewegung:Hub"]["ok"] is False and p["grenze:Hub"]["ok"] is None
    assert p["endlage:Hub:schieber"]["ok"] is False and "abgebrochen" in p["endlage:Hub:schieber"]["hinweis"]


def test_ergaenze_bericht():
    bericht = {"bestanden": True, "pruefungen": [{"id": "rebuild", "ok": True}], "maengel": [], "bilder": {"iso": "i.png"}}
    neu = ergaenze_bericht(bericht, [{"id": "grenze:Hub", "ok": False, "hinweis": "geht durch", "knoten": ["schieber"]}],
                           {"laeufe": [], "paare": []}, {"Hub-min": "Hub-min.png"})
    assert neu["bestanden"] is False and [m["pruefung"] for m in neu["maengel"]] == ["grenze:Hub"]
    assert neu["bilder"] == {"iso": "i.png", "Hub-min": "Hub-min.png"} and neu["bewegungen"] == {"laeufe": [], "paare": []}
    assert len(neu["pruefungen"]) == 2 and bericht["maengel"] == []  # das Original bleibt unverändert
