"""Paket Konstruktionsstil: Instanzen gemusterter und gespiegelter Bohrungen (Anzahl, Träger, Kopien)."""

import pytest

from swki.spec.instanzen import anzahl_instanzen, kopien_kreis, kopien_linear, kopien_spiegeln, traeger


def _loch(fid="f7", n=1):
    return {"id": fid, "typ": "bohrung", "positionen": [[0, 0]] * n, "durchmesser": 6, "durch": True}


def _lin(fid, quellen, n1, n2=None):
    f = {"id": fid, "typ": "muster_linear", "features": quellen, "richtung1": {"achse": "x", "abstand": 40, "anzahl": n1}}
    if n2:
        f["richtung2"] = {"achse": "z", "abstand": 20, "anzahl": n2}
    return f


def _spiegel(fid, quellen):
    return {"id": fid, "typ": "spiegeln", "features": quellen, "ebene": "vorne"}


def test_anzahl_ohne_muster():
    assert anzahl_instanzen({"features": [_loch(n=2)]}, "f7") == 2


def test_anzahl_reihe():
    assert anzahl_instanzen({"features": [_loch(), _lin("f8", ["f7"], 5)]}, "f7") == 5


def test_anzahl_raster_und_kreis():
    kreis = {"id": "k", "typ": "muster_kreis", "features": ["f7"], "achse": "y", "anzahl": 6}
    assert anzahl_instanzen({"features": [_loch(n=2), _lin("f8", ["f7"], 3, 2), kreis]}, "f7") == 2 + 2 * 5 + 2 * 5


def test_anzahl_formplatte():
    spec = {"features": [_loch(), _lin("f8", ["f7"], 4), _spiegel("f9", ["f7", "f8"])]}
    assert traeger(spec, "f7") == ["f8", "f9"]
    assert anzahl_instanzen(spec, "f7") == 8


def test_traeger_transitiv():
    spec = {"features": [_loch(), _lin("f8", ["f7"], 4), _spiegel("f9", ["f8"]), _loch("f10")]}
    assert traeger(spec, "f7") == ["f8", "f9"] and traeger(spec, "f10") == []
    assert anzahl_instanzen(spec, "f7") == 1 + 3 + 3


def test_kopien_linear_umkehren():
    kopien = kopien_linear([(0.0, 20.0, 5.0)], {"achse": "x", "abstand": 10, "anzahl": 3, "umkehren": True}, None, {})
    assert kopien == [(-10.0, 20.0, 5.0), (-20.0, 20.0, 5.0)]


def test_kopien_linear_zwei_richtungen_reihenfolge():
    r1 = {"achse": "x", "abstand": "=A", "anzahl": 2}
    r2 = {"achse": "z", "abstand": 5, "anzahl": 2}
    assert kopien_linear([(0.0, 0.0, 0.0)], r1, r2, {"A": 10}) == [(0.0, 0.0, 5.0), (10.0, 0.0, 0.0), (10.0, 0.0, 5.0)]


def test_kopien_spiegeln_lage_25():
    assert kopien_spiegeln([(10.0, 1.0, 2.0), (30.0, 1.0, 2.0)], 0, 25.0) == [(40.0, 1.0, 2.0), (20.0, 1.0, 2.0)]


def test_kopien_kreis_um_minus_y():
    # Spike S20 d: rechtsdrehend um die Achsrichtung; achse_y zeigt nach −y; 4 × 360° → 90°-Schritte
    kopien = kopien_kreis([(30.0, 10.0, 0.0)], (0.0, -1.0, 0.0), 4, 360)
    assert kopien == [pytest.approx(p, abs=1e-9) for p in [(0.0, 10.0, 30.0), (-30.0, 10.0, 0.0), (0.0, 10.0, -30.0)]]


def test_kopien_kreis_teilwinkel():
    kopien = kopien_kreis([(30.0, 0.0, 0.0)], (0.0, 0.0, 1.0), 4, 90)
    assert kopien[0] == pytest.approx((30 * 0.8660254037844387, 15.0, 0.0))
    assert kopien[-1] == pytest.approx((0.0, 30.0, 0.0), abs=1e-9)
