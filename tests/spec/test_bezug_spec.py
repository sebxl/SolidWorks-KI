"""Bemaßungsbezug (Spec 2026-10-23 §6): Schema von `bezug`, Befunde in validieren, Hinweis art "bezug"."""

import copy

import pytest

from swki.spec.hinweise import feste_masse, hinweise
from swki.spec.laden import plausibel_befunde, schema_befunde

PLATTE = {
    "art": "teil", "name": "Platte", "material": "1.0503", "eigenschaften": {"Benennung": "Platte"},
    "parameter": {"L": 100, "B": 60, "H": 20},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}},
    ],
}
FLAECHE = {"feature": "f1", "flaeche": "+y"}


def _spec(*features) -> dict:
    neu = copy.deepcopy(PLATTE)
    neu["features"] += list(features)
    return neu


def _skizze(element: dict, ebene="oben", fid="f2") -> dict:
    return {"id": fid, "typ": "extrusion", "skizze": {"ebene": ebene, "elemente": [element]},
            "ende": {"typ": "blind", "tiefe": 5}}


def _normbohrung(fid="f2", positionen=None, **weiteres) -> dict:
    return {"id": fid, "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8", "flaeche": FLAECHE,
            "positionen": positionen if positionen is not None else [["=-L/2+30", 20], ["=-L/2+30", -20]],
            "durch": True, **weiteres}


def _bohrung(fid="f2", **weiteres) -> dict:
    return {"id": fid, "typ": "bohrung", "flaeche": FLAECHE, "positionen": [[20, 0]], "durchmesser": 8, "durch": True,
            **weiteres}


# --- Schema ---------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("feature", [
    _skizze({"rechteck": {"mitte": [20, 0], "breite": 10, "hoehe": 5, "bezug": {"u": "-rand", "v": "mitte"}}}),
    _skizze({"kreis": {"mitte": [20, 0], "durchmesser": 5, "bezug": {"u": "+rand"}}}),
    _skizze({"langloch": {"mitte": [20, 0], "laenge": 12, "breite": 5, "bezug": {"v": "ursprung"}}}),
    _bohrung(bezug={"u": "mitte", "v": {"flaeche": {"feature": "f1", "flaeche": "-x"}}}),
    _normbohrung(bezug={"u": {"flaeche": {"nahe": [1, 2, 3]}}}),
], ids=["rechteck", "kreis", "langloch", "bohrung", "normbohrung"])
def test_schema_akzeptiert_bezug(feature):
    assert schema_befunde(_spec(feature)) == []


def test_schema_lehnt_bezug_an_polygon_ab():
    polygon = {"polygon": {"punkte": [[0, 0], [10, 0], [10, 10]], "bezug": {"u": "mitte"}}}
    assert schema_befunde(_spec(_skizze(polygon)))


@pytest.mark.parametrize("bezug", [{"u": "links"}, {}, {"w": "mitte"}, {"u": {"flaeche": "+y"}}, {"u": "mitte", "x": 1}])
def test_schema_lehnt_unbekannten_wert_ab(bezug):
    assert schema_befunde(_spec(_skizze({"kreis": {"mitte": [20, 0], "durchmesser": 5, "bezug": bezug}})))


# --- Befunde --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("ebene", ["oben", {"versatz": {"ebene": "oben", "abstand": 10}}], ids=["standard", "versatz"])
@pytest.mark.parametrize("bezug", [{"u": "-rand"}, {"u": "+rand"}, {"u": {"flaeche": FLAECHE}}],
                         ids=["minus_rand", "plus_rand", "flaeche"])
def test_rand_und_flaeche_auf_standard_oder_versatzebene_ist_befund(tmp_path, ebene, bezug):
    spec = _spec(_skizze({"kreis": {"mitte": [20, 0], "durchmesser": 5, "bezug": bezug}}, ebene))
    assert schema_befunde(spec) == []
    [b] = plausibel_befunde(spec, tmp_path)
    assert b["pfad"] == "features[1].skizze.elemente[0].kreis.bezug.u"
    assert "nur in Skizzen auf Flächen" in b["meldung"]


def test_befund_je_achse_mit_pfad_v(tmp_path):
    kreis = {"mitte": [20, 0], "durchmesser": 5, "bezug": {"u": "mitte", "v": "-rand"}}
    [b] = plausibel_befunde(_spec(_skizze({"kreis": kreis})), tmp_path)
    assert b["pfad"] == "features[1].skizze.elemente[0].kreis.bezug.v"


@pytest.mark.parametrize("ebene", [FLAECHE, {"nahe": [0, 20, 0]}], ids=["feature", "nahe"])
def test_rand_und_flaeche_auf_flaeche_erlaubt(tmp_path, ebene):
    rechteck = {"mitte": [20, 0], "breite": 10, "hoehe": 5,
                "bezug": {"u": "-rand", "v": {"flaeche": {"feature": "f1", "flaeche": "-x"}}}}
    assert plausibel_befunde(_spec(_skizze({"rechteck": rechteck}, ebene)), tmp_path) == []


def test_mitte_und_ursprung_auf_standardebene_erlaubt(tmp_path):
    langloch = {"mitte": [20, 0], "laenge": 12, "breite": 5, "bezug": {"u": "mitte", "v": "ursprung"}}
    assert plausibel_befunde(_spec(_skizze({"langloch": langloch})), tmp_path) == []


def test_bezug_von_bohrung_ist_immer_auf_flaeche(tmp_path):
    spec = _spec(_normbohrung(bezug={"u": "-rand", "v": {"flaeche": {"feature": "f1", "flaeche": "-x"}}}))
    assert plausibel_befunde(spec, tmp_path) == []


def test_bezug_flaeche_verweis_auf_spaeteres_feature_ist_befund(tmp_path):
    spec = _spec(_normbohrung("f2", bezug={"u": {"flaeche": {"feature": "f3", "flaeche": "-x"}}}), _bohrung("f3"))
    [b] = plausibel_befunde(spec, tmp_path)
    assert b["pfad"] == "features[1].bezug.u.flaeche.feature" and "kein früheres Feature" in b["meldung"]


# --- Hinweis art "bezug" --------------------------------------------------------------------------------------------

def _bezug_hinweise(spec: dict) -> list[dict]:
    return [h for h in hinweise(spec) if h["art"] == "bezug"]


def test_hinweis_bezug_bei_positionen_ohne_bezug():
    h1, h2 = _bezug_hinweise(_spec(_normbohrung(positionen=[[-70, 20], [-70, -20]])))
    assert [h1["pfad"], h2["pfad"]] == ["features[1].positionen"] * 2
    assert "Achse u" in h1["meldung"] and "Achse v" in h2["meldung"]
    assert h1["meldung"] == ("Lage ohne Bemaßungsbezug auf Achse u: bezug angeben (mitte oder rand), "
                             "sonst wird zum Ursprung bemaßt")


def test_hinweis_bezug_entfaellt_mit_bezug():
    spec = _spec(_normbohrung(positionen=[[-70, 20], [-70, -20]], bezug={"u": "-rand", "v": "mitte"}))
    assert _bezug_hinweise(spec) == []


def test_hinweis_bezug_ausdrueckliches_ursprung_unterdrueckt():
    spec = _spec(_normbohrung(positionen=[[-70, 20]], bezug={"u": "ursprung"}))
    [h] = _bezug_hinweise(spec)  # nur v ohne Bezug-Schlüssel
    assert "Achse v" in h["meldung"]


def test_hinweis_bezug_nur_achse_mit_lage_ungleich_null():
    [h] = _bezug_hinweise(_spec(_normbohrung(positionen=[[-70, 0], [30, 0]])))
    assert "Achse u" in h["meldung"]
    assert _bezug_hinweise(_spec(_normbohrung(positionen=[[0, 0]]))) == []


def test_hinweis_bezug_bohrung_und_ausdruecke():
    [h] = _bezug_hinweise(_spec(_bohrung(positionen=[["=L/2-10", 0]])))  # 40 ≠ 0
    assert h["pfad"] == "features[1].positionen" and "Achse u" in h["meldung"]
    assert _bezug_hinweise(_spec(_bohrung(positionen=[["=L-100", 0]]))) == []  # wertet zu 0 aus


def test_hinweis_bezug_ausdrucksfehler_gibt_keinen_hinweis_fuer_die_achse():
    [h] = _bezug_hinweise(_spec(_bohrung(positionen=[["=UNBEKANNT", 3]])))  # Fehler wird anderswo gemeldet
    assert "Achse v" in h["meldung"]


def test_hinweis_bezug_element_auf_flaeche():
    kreis = _skizze({"kreis": {"mitte": [20, 0], "durchmesser": 5}}, FLAECHE)
    [h] = _bezug_hinweise(_spec(kreis))
    assert h["pfad"] == "features[1].skizze.elemente[0].kreis.mitte" and "Achse u" in h["meldung"]
    # nahe-Anker ist ebenfalls eine Fläche
    nahe = _skizze({"kreis": {"mitte": [20, 0], "durchmesser": 5}}, {"nahe": [0, 20, 0]})
    assert len(_bezug_hinweise(_spec(nahe))) == 1


def test_hinweis_bezug_element_nicht_auf_standard_oder_versatzebene():
    kreis = {"kreis": {"mitte": [20, 0], "durchmesser": 5}}
    assert _bezug_hinweise(_spec(_skizze(kreis))) == []
    assert _bezug_hinweise(_spec(_skizze(kreis, {"versatz": {"ebene": "oben", "abstand": 3}}))) == []


def test_hinweis_bezug_nicht_fuer_polygon_kontur_mittellinie():
    elemente = [{"polygon": {"punkte": [[20, 0], [30, 0], [30, 10]]}},
                {"mittellinie": {"von": [20, -5], "bis": [20, 5]}}]
    feature = _skizze(elemente[0], FLAECHE)
    feature["skizze"]["elemente"] = elemente
    assert _bezug_hinweise(_spec(feature)) == []


def test_hinweis_bezug_rechteck_und_langloch_auf_flaeche():
    feature = _skizze({"rechteck": {"mitte": [20, 10], "breite": 4, "hoehe": 4}}, FLAECHE)
    feature["skizze"]["elemente"].append({"langloch": {"mitte": [0, 15], "laenge": 10, "breite": 4}})
    achsen = [(h["pfad"], "u" if "Achse u" in h["meldung"] else "v") for h in _bezug_hinweise(_spec(feature))]
    assert achsen == [("features[1].skizze.elemente[0].rechteck.mitte", "u"),
                      ("features[1].skizze.elemente[0].rechteck.mitte", "v"),
                      ("features[1].skizze.elemente[1].langloch.mitte", "v")]


def test_hinweise_reihenfolge_bezug_nach_feste_masse_vor_zusammenfassen():
    spec = _spec(_normbohrung("f2", positionen=[[-70, 20]]), _normbohrung("f3", positionen=[[-70, 20]]))
    arten = [h["art"] for h in hinweise(spec)]
    erster_bezug, letzter_fest = arten.index("bezug"), max(i for i, a in enumerate(arten) if a == "feste_zahl")
    assert letzter_fest < erster_bezug < arten.index("zusammenfassen")


# --- bezug ist Bauweg -----------------------------------------------------------------------------------------------

def test_bezug_ist_keine_feste_zahl():
    ohne = _spec(_normbohrung(positionen=[["=L", "=B"]]))
    mit = _spec(_normbohrung(positionen=[["=L", "=B"]],
                             bezug={"u": {"flaeche": {"nahe": [1, 2, 3]}}, "v": {"flaeche": {"feature": "f1", "flaeche": "-x"}}}))
    assert feste_masse(mit) == feste_masse(ohne) == []


def test_huellquader_auto_unveraendert_mit_bezug(tmp_path):
    ohne = _spec(_skizze({"kreis": {"mitte": [20, 0], "durchmesser": 5}}, FLAECHE))
    mit = copy.deepcopy(ohne)
    mit["features"][1]["skizze"]["elemente"][0]["kreis"]["bezug"] = {"u": "-rand", "v": "mitte"}
    for spec in (ohne, mit):
        spec["pruefung"] = {"huellquader": "auto"}
    assert plausibel_befunde(ohne, tmp_path) == plausibel_befunde(mit, tmp_path) == []
    from swki.pruefung.huellquader import huellquader_auto
    assert huellquader_auto(mit) == huellquader_auto(ohne)
