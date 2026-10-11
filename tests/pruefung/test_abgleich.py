"""Abgleich freigegebene Spec ↔ Merkmalsbericht (ohne SolidWorks; STEP des Testteils mit CadQuery erzeugt)."""

import copy
from pathlib import Path

import pytest

from swki.pruefung.abgleich import abgleich
from swki.pruefung.merkmale import merkmale_aus_datei

STEP = Path(__file__).parent / "daten" / "platte_merkmale.step"

# Spec des Testteils (so gebaut wie platte_merkmale.step)
SPEC = {
    "art": "teil", "name": "Platte",
    "parameter": {"L": 100, "B": 60, "T": 20, "D": 6.6},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
         "ende": {"typ": "blind", "tiefe": "=T"}},
        {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [[40, 20], [-40, 20], [40, -20], [-40, -20]], "durchmesser": "=D", "durch": True,
         "senkung": {"durchmesser": 11, "tiefe": 6.4}},
        {"id": "f3", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+x"}, "positionen": [[0, 10]],
         "durchmesser": 5, "tiefe": 12},
        {"id": "f4", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"feature": "f1", "flaeche": "-z"},
         "positionen": [[30, 10]], "tiefe": 12, "gewindetiefe": 10},
        {"id": "f5", "typ": "schnitt",
         "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                    "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 30, "hoehe": 20, "radius": 4}}]},
         "ende": {"typ": "blind", "tiefe": 8}},
        {"id": "f6", "typ": "extrusion",
         "skizze": {"ebene": {"feature": "f1", "flaeche": "-y"}, "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 16}}]},
         "ende": {"typ": "blind", "tiefe": 5}},
        {"id": "f7", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": 2},
        {"id": "f8", "typ": "fase", "kanten": [{"feature": "f1", "kanten_an": "+y"}], "abstand": 1},
    ],
}


@pytest.fixture(scope="module")
def m():
    return merkmale_aus_datei(STEP)


def _spec(**aenderungen):
    s = copy.deepcopy(SPEC)
    for fid, felder in aenderungen.items():
        f = next(f for f in s["features"] if f["id"] == fid)
        if felder is None:
            s["features"].remove(f)
        else:
            f.update(felder)
            for k in [k for k, v in felder.items() if v is None]:
                del f[k]
    return s


def _feature(s, fid):
    return next(f for f in s["features"] if f["id"] == fid)


def test_passende_spec_besteht(m):
    e = abgleich(SPEC, m)
    assert e["ok"] is True, e
    assert e["geprueft"] == 7 and e["knoten"] == [] and "unerwartet" not in e and "nicht_geprueft" not in e


def test_bohrung_auf_der_falschen_seite(m):
    e = abgleich(_spec(f3={"flaeche": {"feature": "f1", "flaeche": "-x"}}), m)
    assert e["ok"] is False and e["knoten"] == ["f3"]
    assert "offen von +X statt von -X" in e["ist"]["f3"][0]


def test_bohrung_an_falscher_position(m):
    e = abgleich(_spec(f4={"positionen": [[-30, 10]]}), m)
    assert e["ok"] is False and "keine Bohrung mit Achse Z bei (X -30 | Y 10)" in e["ist"]["f4"][0]
    assert "unerwartet" in e   # die gebaute bei X 30 hat kein Feature mehr


def test_durchmesser_tiefe_senkung_durch(m):
    e = abgleich(_spec(f2={"senkung": {"durchmesser": 11, "tiefe": 5}}, f3={"durchmesser": 6, "tiefe": 10}), m)
    texte = " ".join(e["ist"]["f2"] + e["ist"]["f3"])
    assert "Senkung Ø 11 × 6,4 statt Ø 11 × 5" in texte
    assert "Ø 5 statt 6" in texte and "Tiefe 12 statt 10" in texte
    e = abgleich(_spec(f3={"durch": True, "tiefe": None}), m)
    assert "blind statt durch" in e["ist"]["f3"][0]


def test_unerwartete_bohrung_ist_mangel_wenn_alles_abgebildet(m):
    e = abgleich(_spec(f3=None), m)
    assert e["ok"] is False and e["unerwartet"] == ["X (Y 10 | Z 0)"] and "ohne Feature" in e["hinweis"]


def test_muster_und_spiegeln_werden_aufgeloest(m):
    s = _spec(f2={"positionen": [[-40, -20]]})
    s["features"].insert(2, {"id": "f9", "typ": "muster_linear", "features": ["f2"],
                             "richtung1": {"achse": "x", "abstand": 80, "anzahl": 2},
                             "richtung2": {"achse": "z", "abstand": 40, "anzahl": 2, "umkehren": True}})
    assert abgleich(s, m)["ok"] is True
    s = _spec(f2={"positionen": [[40, 20]]})
    s["features"][2:2] = [{"id": "s1", "typ": "spiegeln", "features": ["f2"], "ebene": "rechts"},
                          {"id": "s2", "typ": "spiegeln", "features": ["f2", "s1"], "ebene": "vorne"}]
    assert abgleich(s, m)["ok"] is True


def test_zapfen_verrundung_fase(m):
    e = abgleich(_spec(f6={"skizze": {"ebene": {"feature": "f1", "flaeche": "-y"},
                                      "elemente": [{"kreis": {"mitte": [10, 0], "durchmesser": 16}}]}},
                       f7={"radius": 3}, f8={"winkel": 30}), m)
    assert sorted(e["knoten"]) == ["f6", "f7", "f8"]
    assert "Zapfen Ø 16 Achse Y bei (X 10 | Z 0) fehlt" in e["ist"]["f6"][0]


def test_nicht_abgebildetes_macht_unerwartetes_zum_hinweis(m):
    s = _spec(f3=None)
    s["features"].append({"id": "r1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": []}})
    e = abgleich(s, m)
    assert e["ok"] is True and e["unerwartet"] and e["nicht_geprueft"] == ["r1: Typ rotation"]


def test_flaeche_ueber_nahe(m):
    e = abgleich(_spec(f3={"flaeche": {"nahe": [50, 5, 10]}}), m)
    assert e["ok"] is True, e
