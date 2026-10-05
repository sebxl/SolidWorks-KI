"""Live: Feature verzahnung (Spec 4b §4) – Stirnrad auf einer Welle, Zahnstange auf einem Rücken, Achse als Referenz,
Messung der Verzahnung und Negativfall Zahnweite (SolidWorks muss laufen)."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from swki.cli import main
from swki.compiler.anker import zylinder_zu_punkten
from swki.compiler.handler import verzahnung as handler_verzahnung
from swki.compiler.topologie import flaechen, koerper
from swki.konfig import lade_rechner
from swki.pruefung.bewertung import verzahnung_abweichungen
from swki.pruefung.geometrie import volumen_auto
from swki.pruefung.messen import verzahnungen

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "zahnstangentrieb"
RAD = {
    "art": "teil", "name": "Rad", "parameter": {"M": 2, "Z": 20, "B": 16, "AS": -0.05, "L": 20},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 12}}]},
         "ende": {"typ": "blind", "tiefe": "=L"}},
        {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": "=L"}},
         "mitte": [0, 0], "modul": "=M", "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
}
STANGE = {
    "art": "teil", "name": "Stange", "parameter": {"M": 2, "Z": 9, "B": 20, "AS": -0.05, "H": 15},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [
             {"rechteck": {"mitte": ["=(Z-1)*pi*M/2", "=-1.25*M-H/2"], "breite": "=Z*pi*M", "hoehe": "=H"}}]},
         "ende": {"typ": "blind", "tiefe": "=B"}},
        {"id": "z1", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": "=M",
         "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
}
TOL = 0.005  # toleranzen.verzahnung_mm (config/standard.yaml)


def test_stirnrad_auf_welle():
    with gebautes_teil(RAD) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        erg = ctx.ergebnis("z1")
        assert [f.Name for f in erg.features] == ["z1"] and erg.punkte == [(0.0, 0.0, 20.0)]
        assert erg.richtung == (0.0, 0.0, 1.0)
        assert len(koerper(ctx.model)) == 1
        assert volumen_mm3(ctx.model) == pytest.approx(volumen_auto(RAD)[0], rel=1e-3)
        [achse] = zylinder_zu_punkten(flaechen(erg.features[0]), erg.punkte, 0.1)  # Radachse als Referenz
        assert achse.radius == pytest.approx(17.5, abs=1e-3)                       # Fußkreis d_f = 35


def test_zahnstange_auf_ruecken():
    with gebautes_teil(STANGE) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        assert len(koerper(ctx.model)) == 1
        assert volumen_mm3(ctx.model) == pytest.approx(volumen_auto(STANGE)[0], rel=1e-3)
        assert ctx.ergebnis("z1").punkte == []


def test_stirnrad_oben_mit_winkel_und_umkehren():
    spec = {**RAD, "features": [RAD["features"][0] | {"skizze": {"ebene": "oben", "elemente": [
        {"kreis": {"mitte": [0, 0], "durchmesser": 12}}]}},
        RAD["features"][1] | {"ebene": {"versatz": {"ebene": "oben", "abstand": 0}}, "winkel": 9, "umkehren": True}]}
    with gebautes_teil(spec) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        assert ctx.ergebnis("z1").richtung == (0.0, -1.0, 0.0) and len(koerper(ctx.model)) == 1


@pytest.mark.parametrize("spec", [RAD, STANGE], ids=["stirnrad", "zahnstange"])
def test_messung_der_verzahnung(spec):
    with gebautes_teil(spec) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        ist = verzahnungen(ctx.model, spec, 0.1, ctx.app)["z1"]
        assert isinstance(ist, dict), ist
        assert verzahnung_abweichungen(spec["features"][1], ist, spec["parameter"], TOL) == [], ist


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_negativ_zahnweite(capsys, tmp_path, monkeypatch):
    # Negativfall E1 (Spec 4b §4.6): der Bau verfälscht das Zahndickenabmaß um −0,05 mm (die Spec bleibt gültig und
    # unverändert) → genau der Mangel verzahnungen (Zahnweite); das Volumen bleibt in der Toleranz (−0,13 %)
    original = handler_verzahnung.aus_feature
    monkeypatch.setattr(handler_verzahnung, "aus_feature",
                        lambda f, p: replace(original(f, p), abmass=original(f, p).abmass - 0.05))
    auftrag = tmp_path / "SWKI-LIVE-ZAHNWEITE"
    shutil.copytree(REFERENZ, auftrag)
    spec = auftrag / "antriebswelle.yaml"
    try:
        assert _lauf(capsys, "validieren", str(spec))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec))
        assert code == 0, bau
        code, bericht = _lauf(capsys, "pruefen", str(spec))
        maengel = {m["pruefung"]: m for m in bericht["maengel"]}
        assert set(maengel) == {"verzahnungen"}, maengel
        assert maengel["verzahnungen"]["knoten"] == ["z1"]
        pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "verzahnungen")
        assert any(t.startswith("zahnweite W6") for t in pruefung["ist"]["z1"]), pruefung
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / "SWKI-LIVE-ZAHNWEITE", ignore_errors=True)
