"""Scheiben einer Baugruppen-Spec: Teil-Änderungs-Specs, die der Code von Etappe 1 unverändert verarbeitet (Plan Etappe 2 Task 4)."""

import copy

from swki.bestand.scheiben import (aenderung_an_haupt, dateien_mit_punkten, haupt_punkte, haupt_scheibe, scheibe, scheiben_karte,
                                   zurueck)
from swki.bestand.spec import befunde_gegen_aufnahme, feature_befunde
from tests.bestand.beispiel_baugruppe import DATEIEN, SHA_BG, SPEC, baugruppen_aufnahme, sha, teil_aufnahme

PLATTE, DECKEL = "teile/Platte.SLDPRT", "teile/Deckel.SLDPRT"


def _spec(**aenderungen) -> dict:
    spec = copy.deepcopy(SPEC)
    spec.update(aenderungen)
    return spec


def _ids(spec) -> list[str]:
    return [p["id"] for p in spec["punkte"]]


def test_dateien_mit_punkten_in_der_reihenfolge_der_ersten_nennung():
    assert dateien_mit_punkten(SPEC) == [PLATTE, DECKEL]
    umgekehrt = _spec(punkte=[SPEC["punkte"][2], SPEC["punkte"][0], SPEC["punkte"][1]])
    assert dateien_mit_punkten(umgekehrt) == [DECKEL, PLATTE]


def test_dateien_mit_punkten_nennt_eine_datei_einmal_auch_bei_anderer_schreibweise():
    spec = _spec()
    spec["punkte"][1]["in_datei"] = "Teile\\platte.sldprt"
    assert dateien_mit_punkten(spec) == [PLATTE, DECKEL]


def test_ohne_teil_punkte_keine_dateien():
    assert dateien_mit_punkten(_spec(punkte=[SPEC["punkte"][4]])) == []


def test_scheibe_enthaelt_nur_punkte_der_datei():
    s = scheibe(SPEC, PLATTE, DATEIEN)
    assert _ids(s) == ["p1", "p2"]
    assert _ids(scheibe(SPEC, DECKEL, DATEIEN)) == ["p3"]


def test_scheibe_ist_eine_aenderungs_spec_ohne_baugruppen_felder():
    s = scheibe(SPEC, PLATTE, DATEIEN)
    assert s["art"] == "aenderung" and s["name"] == SPEC["name"] and s["parameter"] == SPEC["parameter"]
    assert all("in_datei" not in p and "lage_folgen" not in p for p in s["punkte"])
    assert "kollision_erlaubt" not in s
    assert "in_datei" not in s["pruefung"]["masse_pruefen"][0]
    assert all("in_datei" not in b for b in s["bereiche"])


def test_scheibe_nimmt_nur_bereiche_und_messungen_der_datei():
    s = scheibe(SPEC, PLATTE, DATEIEN)
    assert [b["punkte"] for b in s["bereiche"]] == [["p1"], ["p2"]]
    assert len(s["pruefung"]["masse_pruefen"]) == 1
    d = scheibe(SPEC, DECKEL, DATEIEN)
    assert [b["punkte"] for b in d["bereiche"]] == [["p3"]]
    assert d["pruefung"].get("masse_pruefen", []) == []


def test_scheibe_bestand_nennt_datei_und_sha_aus_den_dateien():
    s = scheibe(SPEC, PLATTE, DATEIEN)
    assert s["bestand"] == {"datei": PLATTE, "sha256": sha(PLATTE), "aufnahme": SPEC["bestand"]["aufnahme"]}


def test_scheibe_findet_die_datei_unabhaengig_von_der_schreibweise_und_nennt_den_aufgenommenen_pfad():
    s = scheibe(SPEC, "Teile\\PLATTE.sldprt", DATEIEN)
    assert s["bestand"]["datei"] == PLATTE and _ids(s) == ["p1", "p2"]


def test_scheibe_aendert_die_spec_nicht():
    vorher = copy.deepcopy(SPEC)
    scheibe(SPEC, PLATTE, DATEIEN)
    assert SPEC == vorher


def test_scheibe_filtert_fremde_punkte_aus_dem_bereich():
    spec = _spec()
    spec["bereiche"][0]["punkte"] = ["p1", "p3", "k1"]  # Platten-Bereich nennt auch einen Punkt des Deckels und einen Baugruppen-Punkt
    s = scheibe(spec, PLATTE, DATEIEN)
    assert s["bereiche"][0]["punkte"] == ["p1"]


def test_scheibe_laesst_sich_wie_etappe_1_validieren():
    for datei in (PLATTE, DECKEL):
        s = scheibe(SPEC, datei, DATEIEN)
        assert befunde_gegen_aufnahme(s, teil_aufnahme(datei)) == []
        assert feature_befunde(s, teil_aufnahme(datei), None)[0] == []


def test_scheibe_nimmt_die_altwertpruefung_von_etappe_1_mit():
    spec = _spec()
    spec["punkte"][0]["alt"] = 41
    (b,) = befunde_gegen_aufnahme(scheibe(spec, PLATTE, DATEIEN), teil_aufnahme(PLATTE))
    assert b["code"] == "BESTAND_ALTWERT"


def test_haupt_punkte_sind_die_punkte_ohne_in_datei():
    assert [p["id"] for p in haupt_punkte(SPEC)] == ["s1", "k1", "v1", "w1"]


def test_aenderung_an_haupt():
    assert aenderung_an_haupt(SPEC) is True
    nur_teile = _spec(punkte=[p for p in SPEC["punkte"] if "in_datei" in p and "lage_folgen" not in p])
    assert aenderung_an_haupt(nur_teile) is False


def test_lage_folgen_allein_speichert_die_hauptbaugruppe():
    nur_teil_mit_lage = _spec(punkte=[SPEC["punkte"][2]])  # p3 trägt lage_folgen
    assert aenderung_an_haupt(nur_teil_mit_lage) is True
    ohne = copy.deepcopy(nur_teil_mit_lage)
    del ohne["punkte"][0]["lage_folgen"]
    assert aenderung_an_haupt(ohne) is False
    leer = copy.deepcopy(nur_teil_mit_lage)
    leer["punkte"][0]["lage_folgen"] = []
    assert aenderung_an_haupt(leer) is False


def test_haupt_scheibe_enthaelt_nur_eigenschaft_und_skript_ohne_in_datei():
    spec = _spec()
    spec["punkte"].append({"id": "s2", "typ": "skript", "datei": "skripte/s2.py", "luecke": "x"})
    spec["punkte"].append({"id": "m1", "typ": "material", "neu": "1.4301"})  # gehört nicht an die Hauptbaugruppe: meldet die Validierung
    spec["bereiche"].append({"punkte": ["s2", "p1"], "box": {"min": [0, 0, 0], "max": [1, 1, 1]}})
    h = haupt_scheibe(spec)
    assert _ids(h) == ["s1", "s2"]
    assert h["bestand"] == SPEC["bestand"] and [b["punkte"] for b in h["bereiche"]] == [["s2"]]
    assert befunde_gegen_aufnahme(h, baugruppen_aufnahme()) == []  # s2 steht im Bereich, die Baugruppen-Aufnahme trägt Etappe-1-Felder


def test_karte_fuehrt_die_pfade_der_scheibe_auf_die_spec_zurueck():
    karte = scheiben_karte(SPEC, DECKEL)
    assert karte["punkte"] == [2]
    assert zurueck("punkte[0].mass", karte) == "punkte[2].mass"
    assert zurueck("punkte[0]", karte) == "punkte[2]"
    assert zurueck("bereiche[0].features[1]", karte) == "bereiche[2].features[1]"
    assert zurueck("bereiche[0].punkte[0]", karte) == "bereiche[2].punkte[0]"
    karte_platte = scheiben_karte(SPEC, PLATTE)
    assert zurueck("punkte[1].feature", karte_platte) == "punkte[1].feature"
    assert zurueck("pruefung.masse_pruefen[0].von.feature", karte_platte) == "pruefung.masse_pruefen[0].von.feature"
    assert zurueck("bestand.datei", karte_platte) == "punkte[0].in_datei"
    assert zurueck("(Wurzel)", karte_platte) == "(Wurzel)"


def test_karte_bildet_auch_gefilterte_bereichspunkte_ab():
    spec = _spec()
    spec["bereiche"][0]["punkte"] = ["p3", "p1"]  # Platten-Bereich: p3 gehört dem Deckel, p1 steht an Stelle 1
    karte = scheiben_karte(spec, PLATTE)
    assert zurueck("bereiche[0].punkte[0]", karte) == "bereiche[0].punkte[1]"


def test_haupt_scheibe_und_teil_scheiben_tragen_die_aufnahmenummer_der_spec():
    assert scheibe(SPEC, PLATTE, DATEIEN)["bestand"]["aufnahme"] == haupt_scheibe(SPEC)["bestand"]["aufnahme"]
    assert haupt_scheibe(SPEC)["bestand"]["sha256"] == SHA_BG
