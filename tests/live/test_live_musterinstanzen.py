"""Live: Instanzen gemusterter und gespiegelter Bohrungen (Paket Konstruktionsstil) – Protokoll, Prüfkontext,
Messgeometrie. SolidWorks muss laufen."""

from pathlib import Path

import pytest

from swki.pruefung.messen import kontext_aus_datei, messgeometrie

from .bauhilfe import gebautes_teil

pytestmark = pytest.mark.sw

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 120, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}
REIHE = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [[-40, 10]], "tiefe": 12, "gewindetiefe": 10, "fase": "nenn"}
MUSTER = {"id": "m1", "typ": "muster_linear", "features": ["f2"], "richtung1": {"achse": "x", "abstand": 20, "anzahl": 5}}
SPIEGEL = {"id": "s1", "typ": "spiegeln", "features": ["f2", "m1"], "ebene": "vorne"}
SPEC = {"art": "teil", "name": "T", "features": [PLATTE, REIHE, MUSTER, SPIEGEL]}


def _achse(ctx, n):
    return messgeometrie(ctx, SPEC, {"feature": "f2", "instanz": n, "achse": True}).punkt


def test_reihe_und_spiegel_instanzen():
    with gebautes_teil(SPEC) as (ctx, fehler, protokoll):
        assert fehler is None
        knoten = {k.id: k for k in protokoll.knoten}
        assert len(knoten["f2"].punkte) == 10
        assert _achse(ctx, 5)[0] == pytest.approx(40) and _achse(ctx, 5)[2] == pytest.approx(-10)
        assert _achse(ctx, 6)[0] == pytest.approx(-40) and _achse(ctx, 6)[2] == pytest.approx(10)  # Spiegelbild der Quelle
        assert _achse(ctx, 10)[0] == pytest.approx(40) and _achse(ctx, 10)[2] == pytest.approx(10)
        # Prüfkontext aus Datei und Protokoll (wie swki pruefen)
        ctx2 = kontext_aus_datei(ctx.app, ctx.model, SPEC, Path("live.yaml"), 0.1, protokoll.als_dict())
        assert [t.Name for t in ctx2.ergebnis("f2").traeger] == ["m1", "s1"]
        assert messgeometrie(ctx2, SPEC, {"feature": "f2", "instanz": 9, "achse": True}).punkt[0] == pytest.approx(20)
