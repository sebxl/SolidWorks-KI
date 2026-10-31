"""Neue Features gegen die freigegebene Kopie (Prüfer Referenz Lauf 1): `punkt:<id>` belegt Werte, nicht nur, dass das Feature da ist.
Reine Logik über Messwerte je Konfiguration, ohne SolidWorks; die Messung selbst steht in `tests/live/test_live_bestand.py`."""

import copy

import pytest

from swki.bestand.feature_messung import bewerte, messart, teil_spec
from swki.bestand.vergleich import vergleiche
from swki.spec.normen import SW_BEFESTIGUNG, SW_END_BLIND, SW_NORM
from tests.bestand.beispiel_aufnahme import aufnahme

M6 = {"id": "p5", "typ": "feature", "name": "Gewinde M6", "feature": {
    "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [45, 0, 20]}, "positionen": [["=-50+RA", 24], ["=-50+RA", -24]],
    "tiefe": 10, "gewindetiefe": "=G"}}
SPEC = {"art": "aenderung", "parameter": {"RA": 12, "G": 8}, "punkte": [{"id": "p1", "typ": "eigenschaft", "name": "R", "neu": "B"}, M6]}
ACHSE = (0.0, 0.0, 1.0)
TOLERANZEN = {"verzahnung_mm": 0.01, "winkel_grad": 0.05}


def _ist(**mehr) -> dict:
    return {"typ": 0, "befestigung": SW_BEFESTIGUNG["gewinde"], "norm": SW_NORM["ISO"], "groesse": "M6", "ende": SW_END_BLIND, "tiefe": 10.0,
            "gewindetiefe": 8.0, "positionen": 2,
            "achsen": [((-38.0, 24.0, 12.0), ACHSE), ((-38.0, 24.0, 18.0), ACHSE), ((-38.0, -24.0, 12.0), ACHSE)], **mehr}


def _bewerte(standard=None, variante=None, spec=SPEC) -> dict:
    return bewerte(spec, {"Standard": {"Gewinde M6": standard or _ist()}, "Variante B": {"Gewinde M6": variante or _ist()}}, TOLERANZEN)["p5"]


def test_stimmt_mit_ist_und_soll_je_konfiguration():
    e = _bewerte()
    assert e["fehler"] == []
    assert e["soll"] == {"art": "gewinde", "groesse": "M6", "tiefe": 10, "gewindetiefe": 8, "positionen": [[-38, 24], [-38, -24]]}
    assert set(e["ist"]) == {"Standard", "Variante B"}
    assert e["ist"]["Variante B"] == {"groesse": "M6", "tiefe": 10.0, "gewindetiefe": 8.0, "positionen": [[-38.0, 24.0], [-38.0, -24.0]]}


@pytest.mark.parametrize("abweichung, text", [
    ({"gewindetiefe": 7.5}, "gewindetiefe: ist 7.5 statt 8"), ({"tiefe": 12.0}, "tiefe: ist 12 statt 10"),
    ({"groesse": "M8"}, "groesse: ist M8 statt M6"), ({"positionen": 3}, "positionen: ist 3 statt 2")])
def test_abweichung_in_einer_konfiguration_ist_ein_fehler(abweichung, text):
    e = _bewerte(variante=_ist(**abweichung))
    assert e["fehler"] == [f"Variante B: {text}"]


def test_achse_versetzt_ist_ein_fehler():
    achsen = [((-38.02, 24.0, 12.0), ACHSE), ((-38.0, -24.0, 12.0), ACHSE)]
    e = _bewerte(standard=_ist(achsen=achsen))
    assert len(e["fehler"]) == 2 and all(t.startswith("Standard: ") for t in e["fehler"])  # die Position fehlt, die Achse ist überzählig
    assert "[-38, 24]" in e["fehler"][0] and "-38.02" in e["fehler"][1]


def test_achse_unter_der_toleranz_zaehlt_nicht():
    achsen = [((-38.005, 24.0, 12.0), ACHSE), ((-38.0, -24.0, 12.0), ACHSE)]
    assert _bewerte(standard=_ist(achsen=achsen))["fehler"] == []


def test_achsen_auf_einer_anderen_ebene():
    """Skizze auf Ebene oben: `modellpunkt` legt v auf -z."""
    spec = copy.deepcopy(SPEC)
    spec["punkte"][1]["feature"]["positionen"] = [[10, 20]]
    ist = _ist(positionen=1, achsen=[((10.0, 5.0, -20.0), (0.0, -1.0, 0.0))])
    assert _bewerte(ist, ist, spec)["fehler"] == []


@pytest.mark.parametrize("achsen", [[], "keine Flächen lesbar"])
def test_keine_achsen_ist_ein_fehler(achsen):
    assert len(_bewerte(standard=_ist(achsen=achsen))["fehler"]) >= 1


def test_nicht_lesbar_ist_ein_fehler():
    e = _bewerte(standard="Feature Gewinde M6 fehlt im Teil")
    assert e["fehler"] == ["Standard: Feature Gewinde M6 fehlt im Teil"] and e["ist"]["Standard"] == "Feature Gewinde M6 fehlt im Teil"


def test_fehlende_konfiguration_ist_ein_fehler():
    e = bewerte(SPEC, {"Standard": {"Gewinde M6": _ist()}, "Variante B": {}}, TOLERANZEN)["p5"]
    assert e["fehler"] == ["Variante B: nicht gemessen"]


def test_formschraege_abweichung():
    f = {"typ": "schnitt", "ende": {"typ": "blind", "tiefe": 5, "formschraege": {"winkel": "=W", "querschnitt": "kleiner"}}}
    spec = {"parameter": {"W": 5}, "punkte": [{"id": "p1", "typ": "feature", "name": "Tasche", "feature": f}]}
    gut = {"flaechen": [{"winkel": 5.0, "vorzeichen": -1}]}
    assert messart(f) == "formschraege"
    e = bewerte(spec, {"Standard": {"Tasche": gut}}, TOLERANZEN)["p1"]
    assert e["fehler"] == [] and e["soll"] == {"winkel": 5, "querschnitt": "kleiner"} and e["ist"] == {"Standard": [5.0]}
    e = bewerte(spec, {"Standard": {"Tasche": {"flaechen": [{"winkel": 7.0, "vorzeichen": -1}]}}}, TOLERANZEN)["p1"]
    assert len(e["fehler"]) == 1 and "7°" in e["fehler"][0]


def test_verzahnung_abweichung():
    f = {"typ": "verzahnung", "art": "stirnrad", "modul": 2, "zaehne": 20, "zahndickenabmass": -0.05}
    spec = {"parameter": {}, "punkte": [{"id": "p1", "typ": "feature", "name": "Rad", "feature": f}]}
    gut = {"art": "stirnrad", "kopfkreis": 44.0, "fusskreis": 35.0, "zaehne": 20}
    assert messart(f) == "verzahnung"
    e = bewerte(spec, {"Standard": {"Rad": gut}}, TOLERANZEN)["p1"]
    assert e["fehler"] == [] and e["soll"]["modul"] == 2 and e["ist"]["Standard"] == gut
    e = bewerte(spec, {"Standard": {"Rad": {**gut, "zaehne": 19}}}, TOLERANZEN)["p1"]
    assert e["fehler"] == ["Standard: zaehne: ist 19 statt 20"]


def test_nicht_messbare_typen_stehen_nicht_drin():
    f = {"typ": "extrusion", "ende": {"typ": "blind", "tiefe": 5}}
    spec = {"parameter": {}, "punkte": [{"id": "p1", "typ": "feature", "name": "Block", "feature": f}]}
    assert messart(f) is None and bewerte(spec, {"Standard": {}}, TOLERANZEN) == {}


def test_teil_spec_nennt_die_features_beim_namen():
    t = teil_spec(SPEC)
    assert t["parameter"] == SPEC["parameter"] and [f["id"] for f in t["features"]] == ["Gewinde M6"]
    assert t["features"][0]["groesse"] == "M6" and "id" not in M6["feature"]


# --- im Vergleich ---

def _nachher(name="Gewinde M6") -> tuple[dict, dict]:
    a = aufnahme()
    a["reihenfolge"] = {k: [f["name"] for f in a["features"]] for k in a["konfigurationen"]}
    n = copy.deepcopy(a)
    n["features"].append({"name": name, "typ": "HoleWzd", "eltern": [], "kinder": [], "unterdrueckt": {"Standard": False, "Variante B": False},
                          "tabelle": False})
    for k in n["konfigurationen"]:
        n["reihenfolge"][k].append(name)
    return a, n


def _punkt(punkt: dict, messung=None) -> dict:
    a, n = _nachher()
    spec = {"punkte": [punkt]}
    return next(e for e in vergleiche(spec, a, n, {"RA": 12, "G": 8}, feature_messung=messung or {}) if e["id"] == f"punkt:{punkt['id']}")


def test_punkt_traegt_ist_und_soll():
    e = _punkt(M6, {"p5": _bewerte()})
    assert e["ok"] is True and e["soll"]["gewindetiefe"] == 8 and e["ist"]["Standard"]["groesse"] == "M6"


def test_abweichung_ergibt_mangel():
    e = _punkt(M6, {"p5": _bewerte(variante=_ist(gewindetiefe=7.5))})
    assert e["ok"] is False and "Variante B: gewindetiefe: ist 7.5 statt 8" in e["hinweis"] and e["soll"]["gewindetiefe"] == 8
    assert e["ist"]["Variante B"]["gewindetiefe"] == 7.5


def test_messbarer_typ_ohne_messung_ist_nicht_bestanden():
    e = _punkt(M6)
    assert e["ok"] is False and "nicht gemessen" in e["hinweis"]


def test_nicht_messbarer_typ_nennt_was_fehlt():
    punkt = {"id": "p5", "typ": "feature", "name": "Gewinde M6", "feature": {"typ": "extrusion", "ende": {"typ": "blind", "tiefe": 5}}}
    e = _punkt(punkt)
    assert e["ok"] is True and "extrusion" in e["hinweis"] and "nicht gemessen" in e["hinweis"]
