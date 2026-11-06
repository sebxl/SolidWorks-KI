"""Paket Konstruktionsstil: Prüfungen muster, kanten und bohrbild gegen aktuelle Spec und freigegebene Kopie."""

import copy

from swki.pruefung.bewertung import (Messwerte, bewerte, bohrbild_abweichungen, kanten_abweichungen,
                                     muster_abweichungen)
from swki.spec.normen import normmasse

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5, "winkel_grad": 0.01}}
PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 200, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}
FL = {"feature": "f1", "flaeche": "+y"}
TASCHE = {"id": "t1", "typ": "schnitt", "skizze": {"ebene": FL, "elemente": [
    {"rechteck": {"mitte": [-60, 0], "breite": 30, "hoehe": 20}}]}, "ende": {"typ": "blind", "tiefe": 8}}
RUND = {"id": "r1", "typ": "verrundung", "kanten": [{"feature": "t1", "auswahl": "senkrechte_kanten"}], "radius": "=R"}
FORMMUSTER = {"id": "m1", "typ": "muster_linear", "features": ["t1", "r1"],
              "richtung1": {"achse": "x", "abstand": 40, "anzahl": 3}}
GEWINDE = {"id": "g1", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": FL,
           "positionen": [[-60, 20]], "tiefe": 12, "gewindetiefe": 10, "fase": "nenn"}
REIHE = {"id": "m2", "typ": "muster_linear", "features": ["g1"], "richtung1": {"achse": "x", "abstand": 30, "anzahl": 5}}


def _spec(*features):
    return {"art": "teil", "name": "T", "parameter": {"R": 4}, "features": [PLATTE, *features], "pruefung": {}}


IST_FORM = {"typ": "LPattern", "n1": 3, "n2": 1, "a1": 40.0, "a2": 0.0, "quellen": ["t1", "r1"]}


def test_muster_passt():
    assert muster_abweichungen(FORMMUSTER, FORMMUSTER, IST_FORM, {}) == []


def test_muster_anzahl_gebaut_falsch():
    assert muster_abweichungen(FORMMUSTER, FORMMUSTER, IST_FORM | {"n1": 2}, {}) == ["anzahl Richtung 1: ist 2 statt 3"]


def test_muster_quellen_falsch():
    assert muster_abweichungen(FORMMUSTER, FORMMUSTER, IST_FORM | {"quellen": ["t1"]}, {}) == [
        "Quellen: ist ['t1'] statt ['r1', 't1']"]


def test_formmuster_gegen_kopie_geaendert():
    aktuell = copy.deepcopy(FORMMUSTER)
    aktuell["richtung1"]["abstand"] = 45
    fehler = muster_abweichungen(aktuell, FORMMUSTER, IST_FORM | {"a1": 45.0}, {})
    assert fehler == ["abstand Richtung 1: 45 statt 40 laut Freigabe"]


def test_formmuster_fehlt_gegen_kopie():
    assert muster_abweichungen(None, FORMMUSTER, None, {}) == ["Muster der Freigabe fehlt"]


def test_kreismuster_und_spiegeln():
    kreis = {"id": "k", "typ": "muster_kreis", "features": ["t1"], "achse": "y", "anzahl": 6}
    assert muster_abweichungen(kreis, kreis, {"typ": "CirPattern", "n": 6, "winkel": 360.0, "quellen": ["t1"]}, {}) == []
    spiegel = {"id": "s", "typ": "spiegeln", "features": ["t1"], "ebene": "rechts"}
    assert muster_abweichungen(spiegel, spiegel, {"typ": "MirrorPattern", "quellen": ["t1"]}, {}) == []
    assert muster_abweichungen(spiegel, spiegel, "Feature s fehlt im Teil", {}) == ["Feature s fehlt im Teil"]


def test_kanten_radius_falsch():
    assert kanten_abweichungen(RUND, {"typ": "Fillet", "radius": 3.0, "flaechen": 4}, {"R": 4}) == ["radius: ist 3 statt 4"]
    assert kanten_abweichungen(RUND, {"typ": "Fillet", "radius": 4.0, "flaechen": 4}, {"R": 4}) == []


def test_kanten_fase_feld_nenn():
    assert kanten_abweichungen(GEWINDE, {"typ": "Chamfer", "abstand": 0.5, "winkel": 45.0, "flaechen": 1}, {}) == []
    assert kanten_abweichungen(GEWINDE, {"typ": "Chamfer", "abstand": 0.6, "winkel": 45.0, "flaechen": 1}, {}) == [
        "abstand: ist 0.6 statt 0.5"]
    assert kanten_abweichungen(GEWINDE, {"typ": "Chamfer", "abstand": 0.5, "winkel": 45.0, "flaechen": 0}, {}) == [
        "keine Fläche"]


def test_bohrbild_darf_zu_positionen_werden():
    kopie = _spec(GEWINDE, REIHE)
    aktuell = _spec({**GEWINDE, "positionen": [[-60 + 30 * k, 20] for k in range(5)]})
    assert bohrbild_abweichungen(kopie, aktuell) == []


def test_bohrbild_anzahl_weicht_ab():
    kopie = _spec(GEWINDE, REIHE)
    aktuell = _spec(GEWINDE, {**REIHE, "richtung1": {**REIHE["richtung1"], "anzahl": 4}})
    assert bohrbild_abweichungen(kopie, aktuell) == ["gewinde M6 Tiefe 12/10: 4 Instanzen statt 5 laut Freigabe"]


def _messwerte(**w) -> Messwerte:
    return Messwerte(rebuild_fehler=[], skizzen={}, box=[0] * 6, volumen=1.0, schwerpunkt=(0, 0, 0), material="",
                     eigenschaften={}, **w)


IST_NB = {"typ": 3, "befestigung": 128, "norm": 8, "groesse": normmasse("gewinde", "M6")["sw_groesse"], "ende": 0,
          "tiefe": 12.0, "gewindetiefe": 10.0, "positionen": 5}


def test_bewerte_reihe_nachgebessert_zu_positionen(monkeypatch):
    import swki.pruefung.bewertung as b

    monkeypatch.setattr(b, "normbohrung_abweichungen", lambda f, ist, p: [] if ist["positionen"] == len(f["positionen"])
                        else ["positionen"])
    kopie = _spec(GEWINDE, REIHE)
    aktuell = _spec({**GEWINDE, "positionen": [[-60 + 30 * k, 20] for k in range(5)]})
    m = _messwerte(normbohrungen={"g1": IST_NB}, kanten={"g1_fase": {"typ": "Chamfer", "abstand": 0.5, "winkel": 45.0,
                                                                       "flaechen": 1}})
    bericht = bewerte(aktuell, m, STANDARD, freigegeben=kopie)
    ids = {p["id"]: p["ok"] for p in bericht["pruefungen"]}
    assert ids["normbohrungen"] and ids["bohrbild"] and ids["kanten"] and "muster" not in ids


def test_bewerte_kanten_knoten_ohne_kopie_ungeprueft():
    kopie = _spec(TASCHE)
    aktuell = _spec(TASCHE, RUND)
    bericht = bewerte(aktuell, _messwerte(kanten={}), STANDARD, freigegeben=kopie)
    assert "kanten" not in {p["id"] for p in bericht["pruefungen"]}


def test_bewerte_formmuster_fehlt():
    kopie = _spec(TASCHE, RUND, FORMMUSTER)
    aktuell = _spec(TASCHE, RUND)
    bericht = bewerte(aktuell, _messwerte(kanten={"r1": {"typ": "Fillet", "radius": 4.0, "flaechen": 4}}), STANDARD,
                      freigegeben=kopie)
    [mangel] = bericht["maengel"]
    assert mangel["pruefung"] == "muster" and mangel["knoten"] == ["m1"]


LOCH = {"id": "b1", "typ": "bohrung", "flaeche": FL, "positionen": [[-60, 0]], "durchmesser": 6, "durch": True}


def test_gemischtes_muster_verliert_form_gegen_kopie():
    """Review: Muster aus Tasche und Bohrung – fällt die Tasche aus den Quellen, ist das ein Mangel."""
    gemischt = {"id": "m1", "typ": "muster_linear", "features": ["t1", "b1"],
                "richtung1": {"achse": "x", "abstand": 40, "anzahl": 3}}
    kopie = _spec(TASCHE, LOCH, gemischt)
    aktuell = _spec(TASCHE, LOCH, {**gemischt, "features": ["b1"]})
    ist = {"typ": "LPattern", "n1": 3, "n2": 1, "a1": 40.0, "a2": 0.0, "quellen": ["b1"]}
    bericht = bewerte(aktuell, _messwerte(muster={"m1": ist}), STANDARD, freigegeben=kopie)
    [mangel] = [m for m in bericht["maengel"] if m["pruefung"] == "muster"]
    assert mangel["knoten"] == ["m1"]


def test_gemischtes_muster_bohrung_darf_wandern():
    """Die Bohrung eines gemischten Musters darf in eigene Positionen wechseln (Bauweg), die Form nicht."""
    gemischt = {"id": "m1", "typ": "muster_linear", "features": ["t1", "b1"],
                "richtung1": {"achse": "x", "abstand": 40, "anzahl": 3}}
    assert muster_abweichungen({**gemischt, "features": ["t1"]}, gemischt,
                               {"typ": "LPattern", "n1": 3, "n2": 1, "a1": 40.0, "a2": 0.0, "quellen": ["t1"]}, {},
                               bohrungen=frozenset({"b1"})) == []


def test_bohrbild_teilung_geaendert():
    """Review / Design §6: gleiche Anzahl, aber andere Teilung → Lagen weichen von der Freigabe ab."""
    kopie = _spec(GEWINDE, REIHE)
    aktuell = _spec(GEWINDE, {**REIHE, "richtung1": {**REIHE["richtung1"], "abstand": 25}})
    [fehler] = bohrbild_abweichungen(kopie, aktuell)
    assert "Lagen" in fehler and "gewinde M6" in fehler


def test_bohrbild_spiegeln_wie_positionen():
    loch = {**LOCH, "positionen": [[-40, 10]]}
    kopie = _spec(loch, {"id": "s1", "typ": "spiegeln", "features": ["b1"], "ebene": "vorne"})
    aktuell = _spec({**loch, "positionen": [[-40, 10], [-40, -10]]})
    assert bohrbild_abweichungen(kopie, aktuell) == []
    falsch = _spec({**loch, "positionen": [[-40, 10], [40, 10]]})
    assert bohrbild_abweichungen(kopie, falsch)


def test_bohrbild_lage_nicht_berechenbar_zaehlt_nur():
    kreis = {"id": "k1", "typ": "muster_kreis", "features": ["b1"], "achse": "y", "anzahl": 4}
    kopie = _spec(LOCH, kreis)
    aktuell = _spec({**LOCH, "positionen": [[-60, 0], [0, 60], [60, 0], [0, -60]]})
    assert bohrbild_abweichungen(kopie, aktuell) == []
