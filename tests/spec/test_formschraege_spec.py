"""Format und Validieren der Option formschraege (Spec Formschräge §3, §5), Hinweise und Sollvolumen (§6.2)."""

import copy
import math

import pytest

from swki.formschraege import querschnitt_koeffizienten, volumen
from swki.pruefung.geometrie import volumen_auto
from swki.spec.hinweise import feste_masse
from swki.spec.laden import plausibel_befunde, schema_befunde

PLATTE = {
    "art": "teil", "name": "Aufnahme", "material": "1.0503", "eigenschaften": {"Benennung": "Aufnahme"},
    "parameter": {"L": 100, "B": 60, "H": 20, "DZ": 20, "HZ": 12, "WZ": 15},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}},
        {"id": "zapfen", "typ": "extrusion",
         "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                    "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": "=DZ"}}]},
         "ende": {"typ": "blind", "tiefe": "=HZ", "formschraege": {"winkel": "=WZ", "querschnitt": "kleiner"}}},
    ],
    "pruefung": {"volumen": {"soll": "auto"}},
}


def _mit(*features, **parameter) -> dict:
    neu = copy.deepcopy(PLATTE)
    neu["features"] += list(features)
    neu["parameter"].update(parameter)
    return neu


def _schraege(**ende) -> dict:
    neu = copy.deepcopy(PLATTE)
    neu["features"][1]["ende"]["formschraege"].update(ende)
    return neu


def _meldungen(spec: dict, tmp_path) -> list[str]:
    return [b["meldung"] for b in schema_befunde(spec) + plausibel_befunde(spec, tmp_path)]


def test_gueltige_formschraege(tmp_path):
    assert _meldungen(PLATTE, tmp_path) == []


def test_schema_querschnitt_und_pflichtfelder():
    assert schema_befunde(_schraege(querschnitt="innen"))
    ohne_winkel = copy.deepcopy(PLATTE)
    del ohne_winkel["features"][1]["ende"]["formschraege"]["winkel"]
    assert schema_befunde(ohne_winkel)
    assert schema_befunde(_schraege(neutral="oben"))


@pytest.mark.parametrize("winkel", [0, 90, 120, -5])
def test_winkel_ausserhalb(tmp_path, winkel):
    spec = _mit(WZ=winkel)
    befunde = plausibel_befunde(spec, tmp_path)
    assert [b["pfad"] for b in befunde if "(0, 90)" in b["meldung"]] == ["features[1].ende.formschraege.winkel"]


def test_profil_faellt_zusammen_kreis(tmp_path):
    # Einzug 12 · tan 40° = 10,07 mm ≥ halber Durchmesser 10 mm
    befunde = plausibel_befunde(_mit(WZ=40), tmp_path)
    assert [b["pfad"] for b in befunde] == ["features[1].ende.formschraege"]
    assert "halber Durchmesser 10 mm" in befunde[0]["meldung"]
    assert plausibel_befunde(_mit(WZ=39), tmp_path) == []
    assert plausibel_befunde(_schraege(querschnitt="groesser", winkel=60), tmp_path) == []


def test_profil_faellt_zusammen_eckradius_und_mittig(tmp_path):
    tasche = {"id": "tasche", "typ": "schnitt",
              "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                         "elemente": [{"rechteck": {"mitte": [30, 0], "breite": 30, "hoehe": 20, "radius": 3}}]},
              "ende": {"typ": "blind", "tiefe": 10, "formschraege": {"winkel": 20, "querschnitt": "kleiner"}}}
    befunde = plausibel_befunde(_mit(tasche), tmp_path)  # 10 · tan 20° = 3,64 ≥ Eckradius 3
    assert [b["pfad"] for b in befunde] == ["features[2].ende.formschraege"]
    assert "Eckradius 3 mm" in befunde[0]["meldung"]
    steg = copy.deepcopy(tasche) | {"id": "steg", "typ": "extrusion"}
    steg["ende"] = {"typ": "mittig", "tiefe": 16, "formschraege": {"winkel": 20, "querschnitt": "kleiner"}}
    assert plausibel_befunde(_mit(steg), tmp_path) == []  # je Seite 8 · tan 20° = 2,91 < 3
    durch = copy.deepcopy(tasche)
    durch["ende"] = {"typ": "durch_alles", "formschraege": {"winkel": 20, "querschnitt": "kleiner"}}
    assert plausibel_befunde(_mit(durch), tmp_path) == []  # Tiefe unbekannt: keine Vorabprüfung


def test_anker_quer_zur_extrusion(tmp_path):
    fase = {"id": "fase", "typ": "fase", "kanten": [{"feature": "zapfen", "kanten_an": "+x"}], "abstand": 1}
    rundung = {"id": "rund", "typ": "verrundung", "kanten": [{"feature": "zapfen", "auswahl": "senkrechte_kanten"}],
               "radius": 1}
    bohrung = {"id": "b1", "typ": "bohrung", "flaeche": {"feature": "zapfen", "flaeche": "-z"}, "positionen": [[0, 5]],
               "durchmesser": 3, "tiefe": 2}
    befunde = plausibel_befunde(_mit(fase, rundung, bohrung), tmp_path)
    assert [b["pfad"] for b in befunde] == ["features[2].kanten[0].kanten_an", "features[3].kanten[0].auswahl",
                                             "features[4].flaeche.flaeche"]
    assert "{nahe: [x, y, z]}" in befunde[0]["meldung"]
    assert "Eckradius in der Skizze" in befunde[1]["meldung"]


def test_anker_parallel_und_ohne_formschraege_bleiben_erlaubt(tmp_path):
    deckel = {"id": "b1", "typ": "bohrung", "flaeche": {"feature": "zapfen", "flaeche": "+y"}, "positionen": [[0, 0]],
              "durchmesser": 3, "tiefe": 2}
    seite_f1 = {"id": "b2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+x"}, "positionen": [[0, 10]],
                "durchmesser": 3, "tiefe": 2}
    rundung = {"id": "rund", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}],
               "radius": 1}
    assert plausibel_befunde(_mit(deckel, seite_f1, rundung), tmp_path) == []


def test_anker_in_pruefung(tmp_path):
    spec = _mit()
    spec["pruefung"]["masse_pruefen"] = [{"was": "Seite", "von": {"feature": "zapfen", "flaeche": "+z"},
                                          "zu": {"feature": "f1", "flaeche": "-z"}, "soll": 10}]
    befunde = plausibel_befunde(spec, tmp_path)
    assert [b["pfad"] for b in befunde] == ["pruefung.masse_pruefen[0].von.flaeche"]


def test_fester_winkel_ist_hinweis():
    spec = _schraege(winkel=15)
    assert [h["pfad"] for h in feste_masse(spec) if "formschraege" in h["pfad"]] == [
        "features[1].ende.formschraege.winkel"]
    assert [h for h in feste_masse(PLATTE) if "formschraege" in h["pfad"]] == []


def test_sollvolumen_mit_formschraege():
    v, grund = volumen_auto(PLATTE)
    assert grund == "analytisch"
    t = math.tan(math.radians(15))
    r1, r2 = 10, 10 - 12 * t
    assert v == pytest.approx(100 * 60 * 20 + math.pi * 12 / 3 * (r1 * r1 + r1 * r2 + r2 * r2))


def test_sollvolumen_mittig_und_schnitt():
    steg = {"id": "steg", "typ": "extrusion",
            "skizze": {"ebene": "vorne", "elemente": [{"rechteck": {"mitte": [0, 30], "breite": 40, "hoehe": 10}}]},
            "ende": {"typ": "mittig", "tiefe": 8, "formschraege": {"winkel": 5, "querschnitt": "kleiner"}}}
    tasche = {"id": "tasche", "typ": "schnitt",
              "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                         "elemente": [{"rechteck": {"mitte": [30, 0], "breite": 30, "hoehe": 20, "radius": 4}}]},
              "ende": {"typ": "blind", "tiefe": 8, "formschraege": {"winkel": 10, "querschnitt": "kleiner"}}}
    v, _ = volumen_auto(_mit(steg, tasche))
    zapfen = volumen(querschnitt_koeffizienten({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {}), 12, 15, "kleiner")
    k_steg = querschnitt_koeffizienten(steg["skizze"]["elemente"][0], {})
    k_tasche = querschnitt_koeffizienten(tasche["skizze"]["elemente"][0], {})
    erwartet = 100 * 60 * 20 + zapfen + volumen(k_steg, 8, 5, "kleiner", mittig=True) - volumen(k_tasche, 8, 10, "kleiner")
    assert v == pytest.approx(erwartet)


def test_sollvolumen_nicht_analytisch():
    trichter = {"id": "trichter", "typ": "schnitt",
                "skizze": {"ebene": {"feature": "f1", "flaeche": "-y"},
                           "elemente": [{"kreis": {"mitte": [-30, 0], "durchmesser": 8}}]},
                "ende": {"typ": "durch_alles", "formschraege": {"winkel": 20, "querschnitt": "groesser"}}}
    assert volumen_auto(_mit(trichter)) == (None, "trichter: durch_alles")
    ring = copy.deepcopy(PLATTE)
    ring["features"][1]["skizze"]["elemente"].append({"kreis": {"mitte": [0, 0], "durchmesser": 6}})
    assert volumen_auto(ring) == (None, "zapfen: Formschräge mit mehreren Profilen nicht analytisch")


def test_unbekannter_parameter_im_winkel(tmp_path):
    befunde = plausibel_befunde(_schraege(winkel="=WX"), tmp_path)
    assert [b["pfad"] for b in befunde] == ["features[1].ende.formschraege.winkel"]
    assert "WX" in befunde[0]["meldung"]


def test_skizze_auf_nahe_wird_abgelehnt(tmp_path):
    spec = _mit({"id": "fase", "typ": "fase", "kanten": [{"feature": "zapfen", "kanten_an": "+x"}], "abstand": 1})
    spec["features"][1]["skizze"]["ebene"] = {"nahe": [0, 20, 0]}  # Normale erst im Modell bekannt
    befunde = plausibel_befunde(spec, tmp_path)
    assert [b["pfad"] for b in befunde] == ["features[1].skizze.ebene"]  # kein Folgefehler am Anker kanten_an
    assert "{nahe" in befunde[0]["meldung"]


def test_senkrechte_kanten_bei_nahe_skizze_wird_abgelehnt(tmp_path):
    rundung = {"id": "rund", "typ": "verrundung", "kanten": [{"feature": "zapfen", "auswahl": "senkrechte_kanten"}],
               "radius": 1}
    spec = _mit(rundung)
    spec["features"][1]["skizze"]["ebene"] = {"nahe": [0, 20, 0]}  # Normale unbekannt, die Auswahl braucht sie nicht
    befunde = plausibel_befunde(spec, tmp_path)
    assert [b["pfad"] for b in befunde] == ["features[1].skizze.ebene", "features[2].kanten[0].auswahl"]


def test_ring_mit_kleiner_ohne_vorabpruefung(tmp_path):
    ring = copy.deepcopy(PLATTE)
    ring["features"][1]["skizze"]["elemente"].append({"kreis": {"mitte": [0, 0], "durchmesser": 6}})
    ring["parameter"]["WZ"] = 45  # beim einzelnen Kreis fiele das Profil zusammen
    assert plausibel_befunde(ring, tmp_path) == []
