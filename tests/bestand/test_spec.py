import copy
import json

import pytest
import yaml

from swki.bestand.spec import bauweg_frei, freigeben, lade_aenderung
from swki.cli import main
from swki.spec.freigabe import pruefsumme
from swki.spec.laden import SpecFehler, art_der_datei, plausibel_befunde

SHA = "9a1c" * 16

# Beispiel aus Spec §4 (ohne volumen_delta auto)
BEISPIEL = {
    "art": "aenderung",
    "name": "Lagerdeckel_Rev",
    "bestand": {"datei": "Lagerdeckel.SLDPRT", "sha256": SHA, "aufnahme": 1},
    "parameter": {"A_neu": 45, "RA": 12},
    "punkte": [
        {"id": "p1", "was": "Abstand Bohrung zur linken Kante 40 → 45", "typ": "mass", "mass": "D2@Skizze4",
         "alt": 40, "neu": "=A_neu", "konfigurationen": "alle", "folgen": ["D1@Skizze7"]},
        {"id": "p2", "was": "Fase an der Oberkante entfällt", "typ": "unterdruecken", "feature": "Fase3"},
        {"id": "p3", "was": "Zwei Gewinde M6 für den Deckel ergänzen", "typ": "feature", "name": "Gewinde M6 Deckel",
         "feature": {"typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [0, 30, 20]},
                     "positionen": [["=-50+RA", 15], ["=-50+RA", -15]], "bezug": {"u": "-rand", "v": "mitte"},
                     "tiefe": 10, "gewindetiefe": 8}},
        {"id": "p4", "typ": "material", "neu": "1.4301"},
        {"id": "p5", "typ": "eigenschaft", "name": "Revision", "neu": "B"},
        {"id": "p6", "typ": "skript", "datei": "skripte/p6_endbedingung.py",
         "luecke": "Endbedingung eines fremden Schnitts ändern"},
    ],
    "bereiche": [
        {"punkte": ["p1", "p3"], "box": {"min": [-50, -20, 0], "max": [-20, 40, 20]}},
        {"punkte": ["p2"], "features": ["Fase3"]},
    ],
    "pruefung": {
        "masse_pruefen": [{"was": "Randabstand Gewinde",
                           "von": {"flaeche": {"nahe": [-50, 0, 10], "normale": [-1, 0, 0]}},
                           "zu": {"punkt": [-38, 15, 20]}, "soll": "=RA", "tol": 0.01}],
        "volumen_delta": {"soll": 1250, "toleranz_prozent": 1},
    },
}


def _schreibe(tmp_path, spec, name="aenderung.yaml"):
    pfad = tmp_path / name
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def _befunde(tmp_path, spec) -> list[dict]:
    with pytest.raises(SpecFehler) as e:
        lade_aenderung(_schreibe(tmp_path, spec))
    return e.value.daten["befunde"]


def spec_mit_feature(**feature):
    """Änderungs-Spec mit einem feature-Punkt; die Schlüssel von `feature` ersetzen bzw. ergänzen dessen Inhalt."""
    spec = copy.deepcopy(BEISPIEL)
    spec["punkte"][2]["feature"].update(feature)
    return spec


def test_beispiel_der_spec_ist_gueltig(tmp_path):
    spec = lade_aenderung(_schreibe(tmp_path, BEISPIEL))
    assert spec == BEISPIEL


def test_beispiel_ohne_optionales_ist_gueltig(tmp_path):
    spec = {"art": "aenderung", "name": "A", "bestand": BEISPIEL["bestand"], "bereiche": [],
            "punkte": [{"id": "p4", "typ": "material", "neu": "1.4301"}]}
    assert lade_aenderung(_schreibe(tmp_path, spec)) == spec


def test_art_wird_erkannt(tmp_path):
    assert art_der_datei(_schreibe(tmp_path, BEISPIEL)) == "aenderung"


def test_schema_lehnt_unbekannten_punkt_typ_ab(tmp_path):
    spec = copy.deepcopy(BEISPIEL)
    spec["punkte"][0]["typ"] = "verschieben"
    befunde = _befunde(tmp_path, spec)
    assert [b["pfad"] for b in befunde] == ["punkte[0].typ"]


def test_schema_verlangt_alt_bei_mass(tmp_path):
    spec = copy.deepcopy(BEISPIEL)
    del spec["punkte"][0]["alt"]
    befunde = _befunde(tmp_path, spec)
    assert any("alt" in b["meldung"] and b["pfad"] == "punkte[0]" for b in befunde)


def test_schema_lehnt_unbekanntes_feld_im_punkt_ab(tmp_path):
    spec = copy.deepcopy(BEISPIEL)
    spec["punkte"][1]["alt"] = 1  # unterdruecken kennt kein alt
    assert _befunde(tmp_path, spec)


def test_schema_verlangt_bereiche_und_punkte(tmp_path):
    spec = copy.deepcopy(BEISPIEL)
    del spec["bereiche"]
    spec["punkte"] = []
    pfade = {b["pfad"] for b in _befunde(tmp_path, spec)}
    assert pfade == {"(Wurzel)", "punkte"}


def test_schema_bereich_braucht_genau_eines_von_box_und_features(tmp_path):
    spec = copy.deepcopy(BEISPIEL)
    spec["bereiche"][0]["features"] = ["Fase3"]  # box und features zugleich
    assert _befunde(tmp_path, spec)
    spec["bereiche"][0] = {"punkte": ["p1"]}  # keines von beiden
    assert _befunde(tmp_path, spec)


def test_volumen_delta_auto_ist_befund(tmp_path):
    spec = copy.deepcopy(BEISPIEL)
    spec["pruefung"]["volumen_delta"]["soll"] = "auto"
    befunde = _befunde(tmp_path, spec)
    assert [b["pfad"] for b in befunde] == ["pruefung.volumen_delta.soll"]


def test_gleichung_hat_zwei_formen(tmp_path):
    variable = {"id": "g1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": "=A_neu"}
    links = {"id": "g2", "typ": "gleichung", "gleichung": "D1@Skizze1", "alt": '"L" * 2', "neu": '"L" * 3'}
    spec = {**BEISPIEL, "punkte": [variable, links], "bereiche": []}
    assert lade_aenderung(_schreibe(tmp_path, spec)) == spec
    mischung = {"id": "g3", "typ": "gleichung", "variable": "L", "gleichung": "D1@Skizze1", "alt": 1, "neu": 2}
    assert _befunde(tmp_path, {**BEISPIEL, "punkte": [mischung], "bereiche": []})


def test_doppelte_punkt_id_ist_befund(tmp_path):
    spec = copy.deepcopy(BEISPIEL)
    spec["punkte"][1]["id"] = "p1"
    befunde = _befunde(tmp_path, spec)
    assert [b["pfad"] for b in befunde] == ["punkte[1].id"]


def test_unbekannter_parameter_in_neu_ist_befund(tmp_path):
    spec = copy.deepcopy(BEISPIEL)
    spec["punkte"][0]["neu"] = "=A_alt"
    befunde = _befunde(tmp_path, spec)
    assert [b["pfad"] for b in befunde] == ["punkte[0].neu"]


# --- plausibel_befunde: fremde Features gelten als früheres Feature ---

def _teil(verweis):
    return {"art": "teil", "name": "T", "parameter": {},
            "features": [{"id": "f1", "typ": "extrusion", "skizze": {"ebene": "vorne", "elemente": []},
                          "ende": {"typ": "blind", "tiefe": 5}},
                         {"id": "f2", "typ": "verrundung", "kanten": {"feature": verweis, "auswahl": "alle_kanten"},
                          "radius": 1}],
            "pruefung": {"masse_pruefen": [{"was": "x", "von": {"feature": verweis, "flaeche": "+z"},
                                            "zu": {"punkt": [0, 0, 0]}, "soll": 1}]}}


def test_plausibel_ohne_fremde_meldet_unbekannten_verweis(tmp_path):
    pfade = [b["pfad"] for b in plausibel_befunde(_teil("bestand_1"), tmp_path) if "Verweis" in b["meldung"]]
    assert pfade == ["features[1].kanten.feature", "pruefung.masse_pruefen[0].von.feature"]


def test_plausibel_mit_fremden_akzeptiert_den_verweis(tmp_path):
    befunde = plausibel_befunde(_teil("bestand_1"), tmp_path, fremde=frozenset({"bestand_1"}))
    assert not [b for b in befunde if "Verweis" in b["meldung"]]


# --- Prüfsumme: Anforderung vs. Bauweg ---

def test_bauweg_aendert_pruefsumme_nicht():
    a = spec_mit_feature(flaeche={"nahe": [0, 30, 20]}, bezug={"u": "-rand"})
    b = spec_mit_feature(flaeche={"nahe": [1, 30, 20]}, bezug={"u": "+rand"})
    assert pruefsumme(a) == pruefsumme(b)


def test_bauweg_nach_flaechenanker_kanten_und_skript_datei_aendern_pruefsumme_nicht():
    a = spec_mit_feature(kanten={"nahe": [0, 0, 0]}, skizze={"ebene": {"feature": "X", "flaeche": "+z"}, "elemente": []})
    b = copy.deepcopy(a)
    b["punkte"][2]["nach"] = "Fase3"
    b["punkte"][2]["feature"]["kanten"] = {"nahe": [9, 9, 9]}
    b["punkte"][2]["feature"]["skizze"]["ebene"] = {"nahe": [1, 2, 3]}  # Wechsel zwischen zwei Flächenankern
    b["punkte"][5]["datei"] = "skripte/anders.py"
    assert pruefsumme(a) == pruefsumme(b)


def _mit_skizze(ebene, typ="extrusion", **rest):
    spec = copy.deepcopy(BEISPIEL)
    spec["punkte"][2]["feature"] = {"typ": typ, "skizze": {"ebene": ebene, "elemente": []}, **rest}
    return spec


@pytest.mark.parametrize("a,b", [
    ({"versatz": {"ebene": "oben", "abstand": 10}}, {"versatz": {"ebene": "oben", "abstand": 11}}),
    ({"versatz": {"ebene": "oben", "abstand": 10}}, {"versatz": {"ebene": "vorne", "abstand": 10}}),
    ("vorne", "oben"),
    ("vorne", {"versatz": {"ebene": "vorne", "abstand": 10}}),
])
def test_ebene_der_skizze_ausser_flaechenanker_ist_anforderung(a, b):
    assert pruefsumme(_mit_skizze(a)) != pruefsumme(_mit_skizze(b))


def test_flaechenanker_als_ebene_ist_bauweg_standardebene_nicht():
    assert pruefsumme(_mit_skizze({"nahe": [0, 0, 0]})) == pruefsumme(_mit_skizze({"feature": "X", "flaeche": "+z"}))
    assert pruefsumme(_mit_skizze({"nahe": [0, 0, 0]})) != pruefsumme(_mit_skizze("vorne"))


def test_ebene_eines_referenz_features_ist_anforderung():
    a = {"typ": "referenz", "ebene": {"basis": "oben", "abstand": 10}}
    b = {"typ": "referenz", "ebene": {"basis": "oben", "abstand": 12}}
    spec_a, spec_b = copy.deepcopy(BEISPIEL), copy.deepcopy(BEISPIEL)
    spec_a["punkte"][2]["feature"], spec_b["punkte"][2]["feature"] = a, b
    assert pruefsumme(spec_a) != pruefsumme(spec_b)


def test_groesse_der_normbohrung_aendert_pruefsumme():
    anders = spec_mit_feature(groesse="M8")
    assert pruefsumme(anders) != pruefsumme(BEISPIEL)


def test_reihenfolge_der_punkte_aendert_pruefsumme_nicht():
    a = copy.deepcopy(BEISPIEL)
    b = copy.deepcopy(BEISPIEL)
    b["punkte"].reverse()
    assert pruefsumme(a) == pruefsumme(b)


def test_luecke_des_skript_punkts_aendert_pruefsumme():
    b = copy.deepcopy(BEISPIEL)
    b["punkte"][5]["luecke"] = "etwas anderes"
    assert pruefsumme(b) != pruefsumme(BEISPIEL)


def _aendere(spec, schluessel):
    if schluessel == "neu":
        spec["punkte"][0]["neu"] = "=RA"
    elif schluessel == "alt":
        spec["punkte"][0]["alt"] = 41
    elif schluessel == "folgen":
        spec["punkte"][0]["folgen"] = []
    elif schluessel == "bereiche":
        spec["bereiche"][0]["box"]["max"] = [-20, 40, 21]
    elif schluessel == "positionen":
        spec["punkte"][2]["feature"]["positionen"][0] = [5, 15]
    elif schluessel == "tiefe":
        spec["punkte"][2]["feature"]["tiefe"] = 11
    elif schluessel == "bestand.sha256":
        spec["bestand"]["sha256"] = "0" * 64
    elif schluessel == "parameter":
        spec["parameter"]["RA"] = 13
    elif schluessel == "pruefung":
        spec["pruefung"]["volumen_delta"]["soll"] = 1251
    elif schluessel == "feature":
        spec["punkte"][1]["feature"] = "Fase4"
    elif schluessel == "id":
        spec["punkte"][1]["id"] = "p9"
    else:
        raise AssertionError(schluessel)


@pytest.mark.parametrize("aenderung", ["neu", "alt", "folgen", "bereiche", "positionen", "tiefe", "bestand.sha256",
                                       "parameter", "pruefung", "feature", "id"])
def test_anforderung_aendert_pruefsumme(aenderung):
    anders = copy.deepcopy(BEISPIEL)
    _aendere(anders, aenderung)
    assert pruefsumme(anders) != pruefsumme(BEISPIEL)


def test_bauweg_frei_aendert_das_original_nicht():
    original = copy.deepcopy(BEISPIEL)
    kern = bauweg_frei(BEISPIEL)
    assert BEISPIEL == original
    assert "bezug" not in kern["punkte"][2]["feature"] and "flaeche" not in kern["punkte"][2]["feature"]
    assert "datei" not in kern["punkte"][5] and kern["punkte"][5]["luecke"]
    assert [p["id"] for p in kern["punkte"]] == ["p1", "p2", "p3", "p4", "p5", "p6"]
    assert "max_nachbesserungen" not in kern


def test_max_nachbesserungen_aendert_pruefsumme_nicht():
    anders = {**BEISPIEL, "max_nachbesserungen": 7}
    assert pruefsumme(anders) == pruefsumme(BEISPIEL)


# --- validieren, freigeben ---

# validieren und freigeben gegen die Aufnahme (Ausgabe, Weiche): tests/bestand/test_validieren.py


def test_validieren_weiche_meldet_befunde(tmp_path, capsys):
    spec = copy.deepcopy(BEISPIEL)
    del spec["punkte"][0]["alt"]
    assert main(["validieren", str(_schreibe(tmp_path, spec))]) == 1
    assert json.loads(capsys.readouterr().out)["befunde"]


def test_freigeben_verweigert_ungueltige_spec(tmp_path):
    spec = copy.deepcopy(BEISPIEL)
    del spec["punkte"][0]["alt"]
    with pytest.raises(SpecFehler):
        freigeben(_schreibe(tmp_path, spec))
    assert not (tmp_path / "freigabe.json").exists()
