"""Zeichnungsableitung Z1.3 Stufe 3 Task 2: Angabetexte und Bohrbilder aus der Spec."""

from pathlib import Path

import yaml

from swki.zeichnung.angaben import Bohrbild, bohrbilder, bohrungsangabe, reihenzusatz, zahl

REF = Path(__file__).parents[1] / "referenz"


def _lade(pfad: str) -> dict:
    return yaml.safe_load((REF / pfad).read_text(encoding="utf-8"))


def _feature(spec: dict, fid: str) -> dict:
    return next(f for f in spec["features"] if f["id"] == fid)


def test_zahl():
    assert (zahl(6.6), zahl(10.0), zahl(0.5)) == ("6,6", "10", "0,5")


def test_spannplatte_gewinde_reihe():
    spec = _lade("stil/spannplatte.yaml")
    b = bohrbilder(spec)["g1"]
    assert (b.anzahl, b.teilung, b.reihe, b.teilkreis) == (5, 30.0, "m1", None)
    text, meld = bohrungsangabe(_feature(spec, "g1"), spec, b)
    assert text == "5 × M6 – 10 tief\nSenkung Ø6 × 90°" and meld == []
    assert reihenzusatz(b) == ("4 × ", " (= 120)")


def test_spannplatte_stift():
    spec = _lade("stil/spannplatte.yaml")
    text, _ = bohrungsangabe(_feature(spec, "st"), spec, bohrbilder(spec)["st"])
    assert text == "2 × Ø8 – 15 tief\nFase 0,5 × 45°"


def test_buchse_lochkreis():
    spec = _lade("buchse/buchse.yaml")
    b = bohrbilder(spec)["f5"]
    assert (b.anzahl, b.teilkreis) == (4, 40.0)
    assert bohrungsangabe(_feature(spec, "f5"), spec, b)[0] == "4 × Ø6 – durch\nTK Ø40"


def test_zwei_richtungen_und_spiegeln():
    spec = {"parameter": {}, "features": [
        {"id": "f1", "typ": "extrusion"},
        {"id": "b1", "typ": "bohrung", "durchmesser": 5, "durch": True, "positionen": [[0, 0]]},
        {"id": "m1", "typ": "muster_linear", "features": ["b1"], "richtung1": {"achse": "x", "abstand": 10, "anzahl": 3},
         "richtung2": {"achse": "z", "abstand": 10, "anzahl": 2}},
        {"id": "s1", "typ": "spiegeln", "features": ["m1"], "ebene": "rechts"}]}
    b = bohrbilder(spec)["b1"]
    assert b.anzahl == 12 and b.teilung is None and b.reihe is None


def test_unbekannte_groesse_gemeldet():
    f = {"id": "g9", "typ": "normbohrung", "art": "gewinde", "groesse": "M7", "positionen": [[0, 0]], "tiefe": 10}
    text, meld = bohrungsangabe(f, {"parameter": {}, "features": [f]}, Bohrbild("g9", 1, None, None, None))
    assert any(m.startswith("ANGABE_UNBEKANNT") for m in meld)
    assert "M7" in text


def test_zylinderschraube_durchgang():
    f = {"id": "z1", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M6", "positionen": [[0, 0]],
         "durch": True}
    text, meld = bohrungsangabe(f, {"parameter": {}, "features": [f]}, Bohrbild("z1", 2, None, None, None))
    assert text.startswith("2 × Ø6,6 – durch") and meld == []


def test_reihe_im_spiegel():
    spec = {"parameter": {}, "features": [
        {"id": "b1", "typ": "bohrung", "durchmesser": 5, "durch": True, "positionen": [[0, 0]]},
        {"id": "m1", "typ": "muster_linear", "features": ["b1"], "richtung1": {"achse": "x", "abstand": 30, "anzahl": 5}},
        {"id": "s1", "typ": "spiegeln", "features": ["m1"], "ebene": "rechts"}]}
    b = bohrbilder(spec)["b1"]
    assert b.anzahl == 10 and reihenzusatz(b) == ("4 × ", " (= 120)")


def test_fase_nenn_ohne_gewinde_gemeldet():
    f = {"id": "s9", "typ": "normbohrung", "art": "stift", "groesse": "8", "tiefe": 5, "fase": "nenn",
         "positionen": [[0, 0]]}
    text, meld = bohrungsangabe(f, {"parameter": {}, "features": [f]}, Bohrbild("s9", 1, None, None, None))
    assert any(m.startswith("ANGABE_UNVOLLSTAENDIG: s9") and "fase" in m for m in meld)


def test_tiefe_fehlt_gemeldet():
    f = {"id": "b9", "typ": "bohrung", "durchmesser": 5, "positionen": [[0, 0]]}
    _, meld = bohrungsangabe(f, {"parameter": {}, "features": [f]}, Bohrbild("b9", 1, None, None, None))
    assert any(m.startswith("ANGABE_UNVOLLSTAENDIG: b9") and "Tiefe" in m for m in meld)


def test_teilkreis_nicht_bestimmbar_gemeldet():
    spec = {"parameter": {}, "features": [
        {"id": "b1", "typ": "bohrung", "durchmesser": 5, "durch": True},
        {"id": "k1", "typ": "muster_kreis", "features": ["b1"], "achse": "y", "anzahl": 3}]}
    b = bohrbilder(spec)["b1"]
    assert b.anzahl == 3 and b.teilkreis is None
    _, meld = bohrungsangabe(spec["features"][0], spec, b)
    assert any(m.startswith("ANGABE_UNVOLLSTAENDIG: b1") and "Teilkreis" in m for m in meld)
