"""Paket Konstruktionsstil, Regel 3 und 6: Kandidaten für Muster und Spiegeln als Hinweis art "zusammenfassen"."""

from swki.spec.hinweise import muster_kandidaten, zusammenfassen

FLAECHE = {"feature": "f1", "flaeche": "+y"}


def _nb(fid, positionen):
    return {"id": fid, "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": FLAECHE,
            "positionen": positionen, "tiefe": 12, "gewindetiefe": 10}


def _tasche(fid, mitte, ebene=None):
    return {"id": fid, "typ": "schnitt", "skizze": {"ebene": ebene or FLAECHE, "elemente": [
        {"rechteck": {"mitte": mitte, "breite": 20, "hoehe": 10, "bezug": {"u": "mitte", "v": "mitte"}}}]},
        "ende": {"typ": "blind", "tiefe": 5}}


def _muster(fid, quellen):
    return {"id": fid, "typ": "muster_linear", "features": quellen, "richtung1": {"achse": "x", "abstand": 20, "anzahl": 3}}


def test_lochreihe_3_wird_muster():
    [h] = muster_kandidaten({"features": [_nb("f2", [[-20, 0], [0, 0], [20, 0]])]})
    assert h["art"] == "zusammenfassen" and h["knoten"] == ["f2"]
    assert "muster_linear" in h["meldung"] and "Teilung 20" in h["meldung"] and "(Regel 3)" in h["meldung"]


def test_reihe_in_v_mit_parametern():
    spec = {"parameter": {"T": 15}, "features": [_nb("f2", [[5, "=-T"], [5, 0], [5, "=T"], [5, "=2*T"]])]}
    [h] = muster_kandidaten(spec)
    assert "4 Positionen" in h["meldung"] and "Teilung 15" in h["meldung"]


def test_eckbild_4_bleibt():
    assert muster_kandidaten({"features": [_nb("f2", [[-20, -10], [20, -10], [20, 10], [-20, 10]])]}) == []


def test_ungleiche_teilung():
    assert muster_kandidaten({"features": [_nb("f2", [[0, 0], [10, 0], [25, 0]])]}) == []


def test_zwei_spiegelbildliche_taschen():
    [h] = muster_kandidaten({"features": [_tasche("t1", [-30, 0]), _tasche("t2", [30, 0])]})
    assert h["knoten"] == ["t1", "t2"] and "spiegeln" in h["meldung"]


def test_zwei_taschen_ohne_symmetrie():
    assert muster_kandidaten({"features": [_tasche("t1", [-30, 0]), _tasche("t2", [10, 0])]}) == []


def test_drei_gleiche_formen():
    [h] = muster_kandidaten({"features": [_tasche("t1", [-25, 5]), _tasche("t2", [0, 5]), _tasche("t3", [25, 5])]})
    assert h["knoten"] == ["t1", "t2", "t3"] and "muster_linear" in h["meldung"] and "Teilung 25" in h["meldung"]


def test_andere_ebene_ist_andere_form():
    spec = {"features": [_tasche("t1", [-30, 0]), _tasche("t2", [30, 0], ebene={"feature": "f1", "flaeche": "-y"})]}
    assert muster_kandidaten(spec) == []


def test_zwei_profile_einer_skizze():
    langloch = {"laenge": 10, "breite": 6}
    f = {"id": "f2", "typ": "schnitt", "skizze": {"ebene": FLAECHE, "elemente": [
        {"langloch": {"mitte": [-30, 0], **langloch}}, {"langloch": {"mitte": [30, 0], **langloch}}]},
        "ende": {"typ": "blind", "tiefe": 4}}
    [h] = muster_kandidaten({"features": [f]})
    assert h["knoten"] == ["f2"] and "spiegeln" in h["meldung"]


def test_kreise_einer_skizze_sind_loecher():
    f = {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}},
        {"kreis": {"mitte": [-30, 0], "durchmesser": 6}}, {"kreis": {"mitte": [30, 0], "durchmesser": 6}}]},
        "ende": {"typ": "blind", "tiefe": 10}}
    assert muster_kandidaten({"features": [f]}) == []


def test_muster_mit_festem_abstand_kein_hinweis_mehr():
    spec = {"features": [_nb("f2", [[0, 0]]), _muster("f3", ["f2"]),
                         {"id": "f4", "typ": "spiegeln", "features": ["f2"], "ebene": "vorne"},
                         {"id": "f5", "typ": "muster_kreis", "features": ["f2"], "achse": "y", "anzahl": 4}]}
    assert [h for h in zusammenfassen(spec) if "Regel 3" in h["meldung"]] == []


def test_verrundung_in_musterquelle_nicht_zusammenfassen():
    r = {"typ": "verrundung", "radius": 3}
    spec = {"features": [
        _tasche("t1", [-30, 0]), {"id": "r1", **r, "kanten": [{"feature": "t1", "auswahl": "senkrechte_kanten"}]},
        _muster("m1", ["t1", "r1"]),
        {"id": "r2", **r, "kanten": [{"nahe": [0, 0, 0]}]}, {"id": "r3", **r, "kanten": [{"nahe": [1, 0, 0]}]},
    ]}
    regel_6 = [h for h in zusammenfassen(spec) if "Regel 6" in h["meldung"]]
    assert [h["knoten"] for h in regel_6] == [["r2", "r3"]]
    assert "am Ende des Baums" not in regel_6[0]["meldung"]


def test_ausdrucksfehler_still():
    assert muster_kandidaten({"features": [_nb("f2", [["=X", 0], [0, 0], [20, 0]])]}) == []
