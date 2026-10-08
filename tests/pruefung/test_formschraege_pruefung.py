"""Prüfung formschraegen (Spec Formschräge §6.1) ohne SolidWorks: Bewertung und Messung mit Ersatzobjekten."""

import math
from pathlib import Path

import pytest

from swki.compiler.kontext import FeatureErgebnis, Kontext
from swki.pruefung.bewertung import Messwerte, bewerte, formschraege_abweichungen
from swki.pruefung.messen import formschraegen, punkt_und_normale

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5, "winkel_grad": 0.01}}
ZAPFEN = {"id": "zapfen", "typ": "extrusion",
          "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                     "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 20}}]},
          "ende": {"typ": "blind", "tiefe": 12, "formschraege": {"winkel": "=WZ", "querschnitt": "kleiner"}}}
TASCHE = {"id": "tasche", "typ": "schnitt",
          "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                     "elemente": [{"rechteck": {"mitte": [30, 0], "breite": 30, "hoehe": 20}}]},
          "ende": {"typ": "blind", "tiefe": 8, "formschraege": {"winkel": 10, "querschnitt": "kleiner"}}}
P = {"WZ": 15}


def _ist(*paare) -> dict:
    return {"flaechen": [{"winkel": w, "vorzeichen": v} for w, v in paare]}


def test_passt():
    assert formschraege_abweichungen(ZAPFEN, _ist((15.0, 1)), P, 0.01) == []
    assert formschraege_abweichungen(TASCHE, _ist(*[(10.004, -1)] * 4), P, 0.01) == []


def test_winkel_und_richtung_falsch():
    fehler = formschraege_abweichungen(TASCHE, _ist((10.0, -1), (12.0, -1), (10.0, 1), (12.0, 1)), P, 0.01)
    assert fehler == ["Winkel 12° statt 10° (2 von 4 Seitenflächen)", "Querschnitt nicht kleiner (2 von 4 Seitenflächen)"]


def test_gerade_wand_und_keine_flaeche():
    assert formschraege_abweichungen(ZAPFEN, _ist((0.0, 0)), P, 0.01) == [
        "Winkel 0° statt 15° (1 von 1 Seitenflächen)", "Querschnitt nicht kleiner (1 von 1 Seitenflächen)"]
    assert formschraege_abweichungen(ZAPFEN, _ist(), P, 0.01) == ["keine geschrägte Seitenfläche gefunden"]


def _messwerte(formschraegen: dict) -> Messwerte:
    return Messwerte(rebuild_fehler=[], skizzen={}, box=[0] * 6, volumen=1.0, schwerpunkt=(0, 0, 0), material="",
                     eigenschaften={}, formschraegen=formschraegen)


def _spec(*features) -> dict:
    return {"art": "teil", "name": "T", "parameter": dict(P), "features": list(features)}


def test_bewerte_gegen_freigegebene_kopie():
    freigegeben = _spec(ZAPFEN, TASCHE)
    nachgebessert = _spec(ZAPFEN, TASCHE | {"ende": {"typ": "blind", "tiefe": 8}})  # Bauweg ohne Schräge
    bericht = bewerte(nachgebessert, _messwerte({"zapfen": _ist((15.0, 1)), "tasche": _ist((0.0, 0))}), STANDARD,
                      freigegeben=freigegeben)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "formschraegen")
    assert pruefung["ok"] is False and pruefung["knoten"] == ["tasche"]
    assert pruefung["gemessen"] == {"zapfen": [15.0], "tasche": [0.0]}
    assert [m["knoten"] for m in bericht["maengel"] if m["pruefung"] == "formschraegen"] == [["tasche"]]


def test_bewerte_fehlendes_feature_und_ohne_formschraege():
    bericht = bewerte(_spec(ZAPFEN), _messwerte({"zapfen": "Feature zapfen fehlt im Teil"}), STANDARD)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "formschraegen")
    assert pruefung["ist"] == {"zapfen": ["Feature zapfen fehlt im Teil"]}
    ohne = _spec(TASCHE | {"ende": {"typ": "blind", "tiefe": 8}})
    assert all(p["id"] != "formschraegen" for p in bewerte(ohne, _messwerte({}), STANDARD)["pruefungen"])


class _Flaeche:
    """Ersatz für IFace2/ISurface: eine Ebene mit äußerer Normale n durch den Punkt q (Meter)."""

    def __init__(self, q, n, umgekehrt=False):
        self.q, self.n, self.FaceInSurfaceSense = q, n, umgekehrt
        self.GetBox = [q[0] - 0.001, q[1] - 0.001, q[2] - 0.001, q[0] + 0.001, q[1] + 0.001, q[2] + 0.001]
        self.GetSurface = self
        self.IsPlane, self.PlaneParams, self.Normal = True, (*n, *q), n  # für swki.compiler.topologie.flaeche_aus

    def GetClosestPointOn(self, x, y, z):  # noqa: N802 – Name der SolidWorks-API
        return (*self.q, 0.0, 0.0)

    def EvaluateAtPoint(self, x, y, z):  # noqa: N802 – Name der SolidWorks-API
        n = tuple(-c for c in self.n) if self.FaceInSurfaceSense else self.n  # Trägerfläche zeigt entgegen
        return (*n, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


class _Feature:
    def __init__(self, faces):
        self.GetFaces = faces


class _Model:
    def __init__(self, features: dict):
        self.features = features

    def FeatureByName(self, name):  # noqa: N802 – Name der SolidWorks-API
        return self.features.get(name)


def test_punkt_und_normale_beachtet_flaechensinn():
    a = math.radians(15)
    for umgekehrt in (False, True):
        punkt, n = punkt_und_normale(_Flaeche((0.01, 0.025, 0.0), (math.cos(a), math.sin(a), 0.0), umgekehrt))
        assert punkt == pytest.approx((10.0, 25.0, 0.0))
        assert n == pytest.approx((math.cos(a), math.sin(a), 0.0))


def test_formschraegen_misst_seitenflaechen():
    a = math.radians(15)
    zapfen = _Feature([_Flaeche((0.01, 0.025, 0.0), (math.cos(a), math.sin(a), 0.0), True),
                       _Flaeche((0.0, 0.032, 0.0), (0.0, 1.0, 0.0))])
    ctx = Kontext(None, _Model({"zapfen": zapfen}), _spec(ZAPFEN), Path("t.yaml"), 0.1)
    ergebnis = formschraegen(ctx, _spec(ZAPFEN, TASCHE))
    assert ergebnis["zapfen"] == {"flaechen": [{"winkel": pytest.approx(15), "vorzeichen": 1}]}
    assert ergebnis["tasche"] == "Feature tasche fehlt im Teil"


def test_formschraegen_mittig_braucht_ebenenpunkt():
    steg = {"id": "steg", "typ": "extrusion",
            "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                       "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 10}}]},
            "ende": {"typ": "mittig", "tiefe": 8, "formschraege": {"winkel": 5, "querschnitt": "kleiner"}}}
    ctx = Kontext(None, _Model({"steg": _Feature([])}), _spec(steg), Path("t.yaml"), 0.1)
    assert formschraegen(ctx, _spec(steg))["steg"].startswith("REFERENZ_NICHT_GEFUNDEN")
    ctx.ergebnisse["f1"] = FeatureErgebnis([_Feature([_Flaeche((0.0, 0.02, 0.0), (0.0, 1.0, 0.0))])])
    assert formschraegen(ctx, _spec(steg))["steg"] == {"flaechen": []}


def test_ohne_formschraege_braucht_keine_winkeltoleranz():
    standard = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}}
    ohne = _spec(TASCHE | {"ende": {"typ": "blind", "tiefe": 8}})
    assert bewerte(ohne, _messwerte({}), standard)["bestanden"] is True


class _Kaputt(_Flaeche):
    def EvaluateAtPoint(self, x, y, z):  # noqa: N802 – Name der SolidWorks-API
        raise RuntimeError("COM-Fehler")


def test_messfehler_wird_fehlertext():
    zapfen = _Feature([_Kaputt((0.01, 0.025, 0.0), (1.0, 0.0, 0.0))])
    ctx = Kontext(None, _Model({"zapfen": zapfen}), _spec(ZAPFEN), Path("t.yaml"), 0.1)
    assert formschraegen(ctx, _spec(ZAPFEN))["zapfen"] == "Formschräge zapfen nicht messbar: COM-Fehler"
