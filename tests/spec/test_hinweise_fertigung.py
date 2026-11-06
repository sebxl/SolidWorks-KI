"""Paket Konstruktionsstil: Hinweise art "fertigung" – Innenradius nach der Fräserregel R ≥ T/5 (Regel 8) und
Bohrungseintritt ohne Fase (Regel 6)."""

from swki.spec.hinweise import fertigung_hinweise, hinweise

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 10}}
FLAECHE = {"feature": "f1", "flaeche": "+y"}


def _tasche(ende, radius=None, fid="t1"):
    r = {"radius": radius} if radius is not None else {}
    return {"id": fid, "typ": "schnitt", "skizze": {"ebene": FLAECHE, "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 20, **r}}]}, "ende": ende}


def _spec(*features):
    return {"features": [PLATTE, *features]}


def _radius(spec):
    return [h for h in fertigung_hinweise(spec) if "Regel 8" in h["meldung"]]


def test_tasche_scharf():
    [h] = _radius(_spec(_tasche({"typ": "blind", "tiefe": 15})))
    assert h["art"] == "fertigung" and h["pfad"] == "features[1].skizze.elemente[0]"
    assert "R ≥ 3" in h["meldung"] and "scharf" in h["meldung"]


def test_tasche_radius_zu_klein():
    [h] = _radius(_spec(_tasche({"typ": "blind", "tiefe": 15}, radius=2)))
    assert "R 2" in h["meldung"] and "R ≥ 3" in h["meldung"]


def test_tasche_radius_genug():
    assert _radius(_spec(_tasche({"typ": "blind", "tiefe": 15}, radius=3))) == []


def test_tasche_verrundung_knoten_ok():
    rund = {"id": "r1", "typ": "verrundung", "kanten": [{"feature": "t1", "auswahl": "senkrechte_kanten"}], "radius": 3}
    assert _radius(_spec(_tasche({"typ": "blind", "tiefe": 15}), rund)) == []


def test_durchbruch_dicke():
    [h] = _radius(_spec(_tasche({"typ": "durch_alles"})))
    assert "R ≥ 2" in h["meldung"]


def test_bis_flaeche_still():
    assert _radius(_spec(_tasche({"typ": "bis_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}}))) == []


def test_polygon_konkav_extrusion():
    l_form = {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"polygon": {"punkte": [[0, 0], [40, 0], [40, 10], [10, 10], [10, 30], [0, 30]]}}]},
        "ende": {"typ": "blind", "tiefe": 12}}
    [h] = _radius({"features": [l_form]})
    assert "R ≥ 2,4" in h["meldung"] and "[10, 10]" in h["meldung"]


def test_polygon_konkav_mit_radien_ok():
    l_form = {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"polygon": {"punkte": [[0, 0], [40, 0], [40, 10], [10, 10], [10, 30], [0, 30]], "radien": [0, 0, 0, 3, 0, 0]}}]},
        "ende": {"typ": "blind", "tiefe": 12}}
    assert _radius({"features": [l_form]}) == []


def test_kreis_langloch_still():
    f = {"id": "t1", "typ": "schnitt", "skizze": {"ebene": FLAECHE, "elemente": [
        {"kreis": {"mitte": [0, 0], "durchmesser": 10}}, {"langloch": {"mitte": [20, 0], "laenge": 10, "breite": 6}}]},
        "ende": {"typ": "blind", "tiefe": 8}}
    assert _radius(_spec(f)) == []


def test_bohrung_ohne_fase():
    def nb(fid, art, groesse="M6", **w):
        return {"id": fid, "typ": "normbohrung", "art": art, "groesse": groesse, "flaeche": FLAECHE,
                "positionen": [[0, 0]], "durch": True, **w}
    spec = _spec(nb("g", "gewinde"), nb("s", "stift", groesse=6), nb("z", "zylinderschraube"),
                 nb("k", "senkschraube"), nb("ok", "zylinderschraube", fase=0.5),
                 {"id": "b", "typ": "bohrung", "flaeche": FLAECHE, "positionen": [[5, 5]], "durchmesser": 6, "durch": True})
    eintritt = [h for h in fertigung_hinweise(spec) if "Regel 6" in h["meldung"]]
    assert [h["pfad"] for h in eintritt] == ["features[1]", "features[2]", "features[3]", "features[6]"]
    assert "fase: nenn" in eintritt[0]["meldung"] and "fase: 0,5" in eintritt[1]["meldung"]


def test_in_hinweise_nach_zusammenfassen():
    arten = [h["art"] for h in hinweise(_spec(_tasche({"typ": "blind", "tiefe": 15})))]
    assert "fertigung" in arten
