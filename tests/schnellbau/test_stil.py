"""Konstruktionsstil im Schnellbau (Stufe C3a): Bohrungsfase, Austragung, Verrundung/Fase und Muster als Musterquelle."""

import math
from pathlib import Path

import pytest
import yaml

pytest.importorskip("build123d")

from swki.schnellbau.fehler import GEOMETRIE, SchnellbauFehler  # noqa: E402
from swki.schnellbau.teil import baue  # noqa: E402
from swki.spec.normen import normmasse  # noqa: E402

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}
OBEN = {"feature": "f1", "flaeche": "+y"}


def _spec(*features):
    return {"art": "teil", "name": "T", "features": [PLATTE, *features]}


def _kegel(r, c):
    """Volumen, das die Fase über dem Zylinder wegnimmt: π·c·(r·c + c²/3)."""
    return math.pi * c * (r * c + c * c / 3)


def test_fase_bohrung_durch():
    loch = {"id": "f2", "typ": "bohrung", "flaeche": OBEN, "positionen": [[-20, 0], [20, 0]],
            "durchmesser": 6, "durch": True, "fase": 0.5}
    teil = baue(_spec(loch))
    soll = 100 * 60 * 20 - 2 * (math.pi * 3 ** 2 * 20 + math.pi * 0.5 * (3 * 0.5 + 0.5 ** 2 / 3))
    assert teil.solid.volume == pytest.approx(soll, rel=1e-9)
    assert teil.meldungen == []


def test_fase_nenn_gewinde():
    loch = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": OBEN,
            "positionen": [[0, 0]], "tiefe": 12, "gewindetiefe": 10}
    r = normmasse("gewinde", "M8")["kernloch"] / 2
    c = (8 - 2 * r) / 2
    ohne = baue(_spec(loch)).solid.volume
    mit = baue(_spec(dict(loch, fase="nenn"))).solid.volume
    assert ohne - mit == pytest.approx(_kegel(r, c), rel=1e-9)


def test_fase_zylinderschraube_am_senkungsrand():
    loch = {"id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M6", "flaeche": OBEN,
            "positionen": [[0, 0]], "durch": True}
    r = normmasse("zylinderschraube", "M6")["senkung_d"] / 2
    ohne = baue(_spec(loch)).solid.volume
    mit = baue(_spec(dict(loch, fase=0.5))).solid.volume
    assert ohne - mit == pytest.approx(_kegel(r, 0.5), rel=1e-9)


MUSTER = {"id": "f3", "typ": "muster_linear", "features": ["f2"], "richtung1": {"achse": "x", "abstand": 20, "anzahl": 3}}


def test_fase_im_muster():
    loch = {"id": "f2", "typ": "bohrung", "flaeche": OBEN, "positionen": [[-20, 0]], "durchmesser": 6, "durch": True}
    ohne = baue(_spec(loch, MUSTER)).solid.volume
    mit = baue(_spec(dict(loch, fase=0.5), MUSTER)).solid.volume
    assert ohne - mit == pytest.approx(3 * _kegel(3, 0.5), rel=1e-9)


def test_fase_ohne_bohrungen():
    loch = {"id": "f2", "typ": "bohrung", "flaeche": OBEN, "positionen": [[-20, 0]], "durchmesser": 6, "durch": True,
            "fase": 0.5}
    teil = baue(_spec(loch, MUSTER), bohrungen=False)
    assert teil.solid.volume == pytest.approx(100 * 60 * 20, rel=1e-9)
    assert "f2" in teil.uebersprungen and "f3" in teil.uebersprungen


# austragung ---------------------------------------------------------------------------------------------------------
KABEL = {"id": "k1", "typ": "austragung",
         "profil": {"ebene": "rechts", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 8}}]},
         "pfad": {"ebene": "vorne", "start": [0, 0], "segmente": [
             {"linie": [40, 0]}, {"bogen": [60, 20], "mitte": [40, 20]}, {"linie": [60, 60]}]}}
KABEL_VOLUMEN = math.pi * 16 * (40 + math.pi * 10 + 40)


def test_austragung_kreis_aufsatz():
    teil = baue({"art": "teil", "name": "T", "features": [KABEL]})
    assert teil.solid.volume == pytest.approx(KABEL_VOLUMEN, rel=1e-9)
    info = teil.features["k1"]
    assert (info.typ, info.op) == ("austragung", "plus")
    assert info.richtung == pytest.approx((1, 0, 0))


def test_austragung_rechteck_schnitt_uhrzeigersinn():
    spec = yaml.safe_load((Path(__file__).parents[1] / "referenz" / "stil" / "spannplatte.yaml").read_text("utf-8"))
    f1, k1 = (next(f for f in spec["features"] if f["id"] == i) for i in ("f1", "k1"))
    p = spec["parameter"]
    teil = baue({"art": "teil", "name": "T", "parameter": p, "features": [f1, k1]})
    soll = p["L"] * p["B"] * p["H"] - p["NB"] * p["NT"] * (
        p["L"] / 2 - p["XN"] + math.pi * p["RN"] / 2 + (p["B"] / 2 - p["ZN"] - p["RN"]))
    assert teil.solid.volume == pytest.approx(soll, rel=1e-9)
    assert teil.features["k1"].op == "minus"


def test_austragung_gespiegelt():
    spiegel = {"id": "s1", "typ": "spiegeln", "features": ["k1"], "ebene": "rechts"}
    teil = baue({"art": "teil", "name": "T", "features": [KABEL, spiegel]})
    assert teil.solid.volume == pytest.approx(2 * KABEL_VOLUMEN, rel=1e-9)


# Verrundung und Fase als Musterquelle ------------------------------------------------------------------------------
def _tasche(mitte_u=-30):
    return {"id": "t1", "typ": "schnitt", "skizze": {"ebene": OBEN, "elemente": [
        {"rechteck": {"mitte": [mitte_u, 0], "breite": 30, "hoehe": 20}}]}, "ende": {"typ": "blind", "tiefe": 12}}


RUNDUNG = {"id": "r1", "typ": "verrundung", "kanten": [{"feature": "t1", "auswahl": "senkrechte_kanten"}], "radius": 3}
TASCHE_RUND = 30 * 20 * 12 - (4 - math.pi) * 9 * 12


def test_tasche_mit_verrundung_gespiegelt():
    spiegel = {"id": "s1", "typ": "spiegeln", "features": ["t1", "r1"], "ebene": "rechts"}
    teil = baue(_spec(_tasche(), RUNDUNG, spiegel))
    assert len(teil.solid.solids()) == 1
    assert teil.solid.volume == pytest.approx(100 * 60 * 20 - 2 * TASCHE_RUND, rel=1e-9)


def test_tasche_mit_verrundung_gemustert():
    muster = {"id": "m1", "typ": "muster_linear", "features": ["t1", "r1"],
              "richtung1": {"achse": "x", "abstand": 40, "anzahl": 2}}
    teil = baue(_spec(_tasche(), RUNDUNG, muster))
    assert teil.solid.volume == pytest.approx(100 * 60 * 20 - 2 * TASCHE_RUND, rel=1e-9)


def test_aufsatz_kante_verrundet_gespiegelt():
    aufsatz = {"id": "a1", "typ": "extrusion", "skizze": {"ebene": OBEN, "elemente": [
        {"rechteck": {"mitte": [-30, 0], "breite": 10, "hoehe": 10}}]}, "ende": {"typ": "blind", "tiefe": 10}}
    rund = {"id": "r1", "typ": "verrundung", "kanten": [{"feature": "a1", "kanten_an": "+y"}], "radius": 2}
    spiegel = {"id": "s1", "typ": "spiegeln", "features": ["a1", "r1"], "ebene": "rechts"}
    einzeln = baue(_spec(aufsatz, rund)).solid.volume - 100 * 60 * 20
    zwei = baue(_spec(aufsatz, rund, spiegel))
    assert einzeln < 1000 and einzeln > 0
    assert zwei.solid.volume - 100 * 60 * 20 == pytest.approx(2 * einzeln, rel=1e-9)


def test_fase_in_musterquelle():
    fase = {"id": "r1", "typ": "fase", "kanten": [{"feature": "t1", "auswahl": "senkrechte_kanten"}], "abstand": 2}
    spiegel = {"id": "s1", "typ": "spiegeln", "features": ["t1", "r1"], "ebene": "rechts"}
    teil = baue(_spec(_tasche(), fase, spiegel))
    assert teil.solid.volume == pytest.approx(100 * 60 * 20 - 2 * (30 * 20 * 12 - 4 * 2 * 2 / 2 * 12), rel=1e-9)


def test_verrundung_ausserhalb_von_mustern_unveraendert():
    teil = baue(_spec(_tasche(), RUNDUNG))
    assert teil.features["r1"].teile is None
    assert teil.solid.volume == pytest.approx(100 * 60 * 20 - TASCHE_RUND, rel=1e-9)


def test_differenzfehler_wird_gemeldet(monkeypatch):
    """Scheitert die Differenz für die Musterkopien, meldet der Schnellbau es mit Feature-ID – nie still weglassen."""
    from build123d import Shape
    from swki.schnellbau.teil import Schnellbau
    original = Schnellbau._differenz

    def differenz(self, a, b):
        def sub(x, y):
            raise RuntimeError("boolesche Differenz kaputt")
        monkeypatch.setattr(Shape, "__sub__", sub)     # erst hier: die Tasche davor baut normal
        return original(self, a, b)

    monkeypatch.setattr(Schnellbau, "_differenz", differenz)
    spiegel = {"id": "s1", "typ": "spiegeln", "features": ["t1", "r1"], "ebene": "rechts"}
    with pytest.raises(SchnellbauFehler) as e:
        baue(_spec(_tasche(), RUNDUNG, spiegel))
    assert e.value.code == GEOMETRIE
    assert "r1" in str(e.value)


# Muster mit Verrundungsquelle bleibt musterbar (Schlussreview C3a) ------------------------------------------------
KLEIN_RUND = 15 * 20 * 12 - (4 - math.pi) * 9 * 12     # Tasche 15 × 20 × 12 mit R3 an den senkrechten Kanten


def _klein():
    t = _tasche(-40)
    t["skizze"]["elemente"][0]["rechteck"]["breite"] = 15
    return t


def _muster_gemischt():
    return {"id": "m1", "typ": "muster_linear", "features": ["t1", "r1"],
            "richtung1": {"achse": "x", "abstand": 20, "anzahl": 2}}


def test_spiegeln_von_muster_mit_quelle_und_verrundung():
    spiegel = {"id": "s1", "typ": "spiegeln", "features": ["t1", "r1", "m1"], "ebene": "rechts"}
    teil = baue(_spec(_klein(), RUNDUNG, _muster_gemischt(), spiegel))
    assert teil.solid.volume == pytest.approx(100 * 60 * 20 - 4 * KLEIN_RUND, rel=1e-9)


def test_spiegeln_nur_des_musters():
    spiegel = {"id": "s1", "typ": "spiegeln", "features": ["m1"], "ebene": "rechts"}
    teil = baue(_spec(_klein(), RUNDUNG, _muster_gemischt(), spiegel))
    assert teil.solid.volume == pytest.approx(100 * 60 * 20 - 3 * KLEIN_RUND, rel=1e-9)


def test_muster_kreis_mit_verrundung_als_quelle():
    kreis = {"id": "m1", "typ": "muster_kreis", "features": ["t1", "r1"], "achse": "y", "anzahl": 2, "winkel": 180}
    teil = baue(_spec(_tasche(), RUNDUNG, kreis))
    assert teil.solid.volume == pytest.approx(100 * 60 * 20 - 2 * TASCHE_RUND, rel=1e-9)
