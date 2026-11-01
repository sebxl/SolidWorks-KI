"""Korrekturrunde 1 zu Task 7 (Blindtest): Handänderungen dürfen nicht durchrutschen, bei fehlenden Daten steht nie `vollstaendig: true`.
Ein Test je Befund; die Nummern sind die der Korrekturrunde."""

import copy
import json

import pytest

from swki import aenderungen
from swki.aenderungen import AenderungFehler, pruefe_unveraendert, soll_verknuepfungen
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.pruefen import lagen_nach_sw_namen
from swki.bestand import abgleich, sw_bestand
from swki.bestand.ablage import aufnahmen_aus_lauf, unlesbare_herkunft
from swki.bestand.abgleich import abgleich_baugruppe, abgleich_teil
from swki.spec import laden
from tests.baugruppe.beispiel import schreibe as schreibe_baugruppe
from tests.baugruppe.beispiel_bewegung import schreibe as schreibe_bewegung
from tests.bestand.test_abgleich import (PROTOKOLL_BG, PROTOKOLL_TEIL, SOLL_LAGEN, SOLL_VERKNUEPFUNGEN, SPEC_TEIL, _f, _ist_bg, _ist_teil,
                                         _lage, _soll)
from tests.test_aenderungen import _lauf, umgebung  # noqa: F401  (Fixture)


def _teil(ist, protokoll=PROTOKOLL_TEIL):
    return abgleich_teil(protokoll, SPEC_TEIL, ist, auftrag="A")


def _bg(ist=None, soll=SOLL_VERKNUEPFUNGEN, protokoll=PROTOKOLL_BG, lagen=SOLL_LAGEN):
    return abgleich_baugruppe(protokoll, soll, ist or _ist_bg(), lagen)


def _feature(ist, name):
    return next(f for f in ist["features"] if f["name"] == name)


# --- 1: gleicher Name, anderer Typ -------------------------------------------------------------------------------------

def test_1_unveraendertes_teil_hat_keinen_typwechsel():
    a = _teil(_ist_teil())
    assert a["typ_geaendert"] == [] and a["vollstaendig"] is True


def test_1_gleicher_name_anderer_typ_wird_genannt():
    ist = _ist_teil()
    _feature(ist, "winkel")["typ"] = "Fillet"      # Schnitt durch eine Verrundung ersetzt, Name und Maß D1 gleich
    a = _teil(ist)
    assert a["typ_geaendert"] == [{"name": "winkel", "knoten": "winkel", "soll": "schnitt", "ist": "Fillet", "erlaubt": ["ICE"]}]
    assert a["nicht_erklaert"] is False


def test_1_normbohrung_wird_zum_schnitt():
    ist = _ist_teil()
    _feature(ist, "gewinde")["typ"] = "ICE"
    assert [t["name"] for t in _teil(ist)["typ_geaendert"]] == ["gewinde"]


def test_1_typ_ohne_beleg_ist_eine_luecke_kein_treffer():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"][0]["typ"] = "skript"
    ist = _ist_teil()
    _feature(ist, "f1")["typ"] = "Irgendwas"
    a = _teil(ist, protokoll)
    assert a["typ_geaendert"] == [] and a["vollstaendig"] is False
    assert any("skript" in text and "f1" in text for text in a["luecken"])


def test_1_tabelle_nennt_nur_belegte_typen():
    assert abgleich.TYP_TABELLE["schnitt"] == frozenset({"ICE"}) and abgleich.TYP_TABELLE["normbohrung"] == frozenset({"HoleWzd"})
    assert "skript" not in abgleich.TYP_TABELLE and "verzahnung" not in abgleich.TYP_TABELLE


# --- 2: Partner, Ausrichtung, Kopplungen, Soll aus der Spec -------------------------------------------------------------

def test_2_andere_partner_werden_genannt():
    ist = _ist_bg()
    ist["verknuepfungen"]["v2"]["partner"] = ["Platte-1", "Schraube-2"]
    a = _bg(ist)
    assert a["partner_geaendert"] == [{"id": "v2", "name": "v2", "soll": ["Platte-1", "Schraube-1"],
                                       "ist": ["Platte-1", "Schraube-2"]}]
    assert a["nicht_erklaert"] is False


def test_2_partner_reihenfolge_ist_egal():
    ist = _ist_bg()
    ist["verknuepfungen"]["v2"]["partner"] = ["Schraube-1", "Platte-1"]
    assert _bg(ist)["partner_geaendert"] == []


def test_2_ausrichtung_nur_wenn_das_soll_sie_nennt():
    ist = _ist_bg()
    ist["verknuepfungen"]["v2"]["ausrichtung"] = 1
    assert _bg(ist)["ausrichtung_geaendert"] == []                     # Soll nennt keine
    soll = {**SOLL_VERKNUEPFUNGEN, "v2": _soll("abstand", 5.0, ausrichtung="gleich")}
    a = _bg(ist, soll)
    assert a["ausrichtung_geaendert"] == [{"id": "v2", "name": "v2", "soll": "gleich", "ist": "entgegengesetzt"}]


def test_2_kopplung_ist_eine_luecke():
    protokoll = copy.deepcopy(PROTOKOLL_BG)
    protokoll["knoten"].append({"id": "k1", "typ": "zahnrad", "sw_name": "k1", "status": "ok"})
    soll = {**SOLL_VERKNUEPFUNGEN, "k1": _soll("zahnrad")}
    ist = _ist_bg()
    ist["verknuepfungen"]["k1"] = {**ist["verknuepfungen"]["v1"], "typ": 10}
    a = _bg(ist, soll, protokoll)
    assert a["vollstaendig"] is False and any("Übersetzung" in text and "k1" in text for text in a["luecken"])


def test_2_soll_ohne_partner_ist_eine_luecke():
    soll = {**SOLL_VERKNUEPFUNGEN, "v1": {"typ": "konzentrisch"}}
    a = _bg(soll=soll)
    assert a["vollstaendig"] is False and any("v1" in text and "Partner" in text for text in a["luecken"])


def test_2_soll_verknuepfungen_aus_spec_und_protokoll(tmp_path):
    bg = lade_baugruppe(schreibe_baugruppe(tmp_path / "A"))
    komponenten = [{"id": "platte", "sw_name": "Platte-1"}, {"id": "deckel", "sw_name": "Deckel-1"},
                   {"id": "schraube.1", "sw_name": "S-1"}, {"id": "schraube.2", "sw_name": None},
                   {"id": "stift", "sw_name": "Stift-1"}]
    soll = soll_verknuepfungen(bg.spec, bg.quellen, {"ABST": 35}, komponenten)
    assert soll["v1"] == {"typ": "deckungsgleich", "partner": ["Deckel-1", "Platte-1"], "ausrichtung": "entgegengesetzt",
                          "wert": None, "min": None, "max": None}
    assert soll["v2"]["ausrichtung"] is None
    assert soll["v4.1"]["partner"] == ["S-1", "Deckel-1"] and soll["v4.2"]["partner"] == [None, "Deckel-1"]


def test_2_soll_partner_ohne_namen_ist_eine_luecke():
    soll = {**SOLL_VERKNUEPFUNGEN, "v2": _soll("abstand", 5.0, partner=["Platte-1", None])}
    a = _bg(soll=soll)
    assert a["vollstaendig"] is False and any("v2" in text and "Partner" in text for text in a["luecken"])


# --- 3: Abstand und Grenze ---------------------------------------------------------------------------------------------

def test_3_abstand_wird_zur_grenze():
    ist = _ist_bg()
    ist["verknuepfungen"]["v2"].update(grenze=True, min=0.0, max=9.0)
    assert _bg(ist)["typ_geaendert"] == [{"id": "v2", "name": "v2", "soll": "abstand", "ist": "grenze_abstand"}]


def test_3_grenze_wird_zum_abstand():
    ist = _ist_bg()
    ist["verknuepfungen"]["v3"].update(grenze=False, min=None, max=None)
    assert _bg(ist)["typ_geaendert"] == [{"id": "v3", "name": "v3", "soll": "grenze_abstand", "ist": "abstand"}]


def test_3_abstand_wird_winkel():
    ist = _ist_bg()
    ist["verknuepfungen"]["v2"]["typ"] = 6
    assert _bg(ist)["typ_geaendert"][0]["ist"] == "winkel"


# --- 4: fehlender Soll-Wert -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("vid", ["v2", "v3"])
def test_4_abstand_und_grenze_ohne_soll_wert_sind_eine_luecke(vid):
    soll = {**SOLL_VERKNUEPFUNGEN, vid: {**SOLL_VERKNUEPFUNGEN[vid], "wert": None}}
    a = _bg(soll=soll)
    assert a["vollstaendig"] is False and any(vid in text and "Wert" in text for text in a["luecken"])


def test_4_grenze_ohne_max_ist_eine_luecke():
    soll = {**SOLL_VERKNUEPFUNGEN, "v3": {**SOLL_VERKNUEPFUNGEN["v3"], "max": None}}
    assert any("v3" in text for text in _bg(soll=soll)["luecken"])


def test_4_verknuepfung_ohne_soll_eintrag_ist_eine_luecke():
    soll = {k: v for k, v in SOLL_VERKNUEPFUNGEN.items() if k != "v2"}
    a = _bg(soll=soll)
    assert a["vollstaendig"] is False and any("v2" in text for text in a["luecken"])


def test_4_soll_nichts_ist_nie_vollstaendig():
    assert _bg(soll=None)["vollstaendig"] is False


# --- 5: Knoten ohne Namen, Lage ----------------------------------------------------------------------------------------

def test_5_teilknoten_ohne_namen_ist_eine_luecke():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"][1]["sw_name"] = None
    ist = _ist_teil()
    ist["features"] = [f for f in ist["features"] if f["name"] not in ("winkel", "winkel_skizze")]
    ist["masse"] = [m for m in ist["masse"] if "winkel" not in m["name"]]
    protokoll["knoten"][1]["masse"] = None
    a = _teil(ist, protokoll)
    assert a["vollstaendig"] is False and any("winkel" in text and "sw_name" in text for text in a["luecken"])


def test_5_uebersprungener_knoten_ist_keine_luecke():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"].append({"id": "f9", "typ": "verrundung", "sw_name": None, "status": "uebersprungen"})
    assert _teil(_ist_teil(), protokoll)["vollstaendig"] is True


def test_5_komponente_ohne_namen_ist_eine_luecke_und_lage_ungeprueft():
    protokoll = copy.deepcopy(PROTOKOLL_BG)
    protokoll["komponenten"][1]["sw_name"] = None
    protokoll["knoten"][1]["sw_name"] = None
    a = _bg(protokoll=protokoll)
    assert a["vollstaendig"] is False and a["lage_geprueft"] is False and "schraube.1" in a["lage_ungeprueft"]
    assert any("schraube.1" in text for text in a["luecken"])


def test_5_verknuepfung_ohne_namen_ist_eine_luecke():
    protokoll = copy.deepcopy(PROTOKOLL_BG)
    protokoll["knoten"][4]["sw_name"] = None            # v2
    ist = _ist_bg()
    del ist["verknuepfungen"]["v2"]
    a = _bg(ist, protokoll=protokoll)
    assert a["vollstaendig"] is False and any("v2" in text for text in a["luecken"])


def test_5_knoten_ohne_feature_brauchen_keinen_namen():
    """`grundstellung` (und `zahnphase`) legen kein Feature an."""
    assert any(k["typ"] == "grundstellung" and k["sw_name"] is None for k in PROTOKOLL_BG["knoten"])
    assert _bg()["vollstaendig"] is True


def test_5_umbenannt_und_verschoben_ist_lage_nicht_geprueft():
    ist = _ist_bg()
    ist["komponenten"]["Stift-1"] = ist["komponenten"].pop("Schraube-1")
    ist["komponenten"]["Stift-1"]["transform"]["Standard"] = _lage(0.5, 0, 0)
    a = _bg(ist)
    assert a["lage_geprueft"] is False and a["lage_ungeprueft"] == ["Schraube-1"]


def test_5_lagen_nach_sw_namen_ohne_namen_behaelt_die_id():
    assert lagen_nach_sw_namen({"a": [1], "b": [2]}, {"komponenten": [{"id": "a", "sw_name": None}, {"id": "b", "sw_name": "B-1"}]}) == {
        "a": [1], "B-1": [2]}


# --- 6: Grenzbereich ---------------------------------------------------------------------------------------------------

def test_6_geaendertes_max_der_grenze_wird_genannt():
    ist = _ist_bg()
    ist["verknuepfungen"]["v3"]["max"] = 40.0
    assert [(w["id"], w["feld"], w["soll"], w["ist"]) for w in _bg(ist)["werte"]] == [("v3", "max", 25.0, 40.0)]


def test_6_soll_der_grenze_traegt_min_und_max(tmp_path):
    bg = lade_baugruppe(schreibe_bewegung(tmp_path / "B"))
    soll = soll_verknuepfungen(bg.spec, bg.quellen, bg.spec.get("parameter", {}), [])
    grenze = soll["g1"]
    assert grenze["typ"] == "grenze_abstand" and grenze["min"] is not None and grenze["max"] is not None
    assert grenze["wert"] == grenze["min"]


# --- 8: unter erklärt nur Skizzen und den Bohrungsassistenten; Namensregeln am passenden Typ -----------------------------------

def test_8_kosmetikgewinde_unter_einem_schnitt_ist_neu():
    ist = _ist_teil()
    _feature(ist, "winkel")["unter"].append("Kosmetisches Gewinde1")
    ist["features"].append(_f("Kosmetisches Gewinde1", "CosmeticThread"))
    assert [f["name"] for f in _teil(ist)["features_neu"]] == ["Kosmetisches Gewinde1"]


def test_8_kosmetikgewinde_unter_dem_bohrungsassistenten_ist_erklaert():
    ist = _ist_teil()
    _feature(ist, "gewinde")["unter"].append("Kosmetisches Gewinde1")
    ist["features"].append(_f("Kosmetisches Gewinde1", "CosmeticThread"))
    assert _teil(ist)["features_neu"] == []


def test_8_skizze_unter_einem_schnitt_ist_erklaert():
    ist = _ist_teil()
    _feature(ist, "winkel")["unter"].append("Skizze9")
    ist["features"].append(_f("Skizze9", "ProfileFeature"))
    assert _teil(ist)["features_neu"] == []


@pytest.mark.parametrize("name", ["f1_positionen", "f1_skizze_skizze", "gewinde_skizze", "winkel_senkung_skizze"])
def test_8_hilfsskizze_am_falschen_knoten_ist_neu(name):
    ist = _ist_teil()
    ist["features"].append(_f(name, "ProfileFeature"))
    assert [f["name"] for f in _teil(ist)["features_neu"]] == [name]


def test_8_hilfsskizze_am_passenden_knoten_bleibt_erklaert():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"].append({"id": "b1", "typ": "bohrung", "sw_name": "b1, b1_senkung", "status": "ok", "masse": []})
    ist = _ist_teil()
    for name, typ in (("b1", "ICE"), ("b1_senkung", "ICE"), ("b1_skizze", "ProfileFeature"), ("b1_senkung_skizze", "ProfileFeature")):
        ist["features"].append(_f(name, typ))
    ist["features"].append(_f("gewinde_positionen_2", "ProfileFeature"))
    a = _teil(ist, protokoll)
    assert [f["name"] for f in a["features_neu"]] == ["gewinde_positionen_2"]


def test_8_referenzachse_nur_mit_muster():
    ist = _ist_teil()
    ist["features"].append(_f("achse_x", "RefAxis"))
    assert [f["name"] for f in _teil(ist)["features_neu"]] == ["achse_x"]
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"].append({"id": "m1", "typ": "muster_linear", "sw_name": "m1", "status": "ok", "masse": []})
    ist["features"].append(_f("m1", "LPattern"))
    assert _teil(ist, protokoll)["features_neu"] == []


def test_8_referenzachse_mit_falschem_typ_ist_neu():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"].append({"id": "m1", "typ": "muster_linear", "sw_name": "m1", "status": "ok", "masse": []})
    ist = _ist_teil()
    ist["features"] += [_f("m1", "LPattern"), _f("achse_x", "ProfileFeature")]
    assert [f["name"] for f in _teil(ist, protokoll)["features_neu"]] == ["achse_x"]


def test_8_masshinweis_erklaert_nur_skizzen_und_ebenen():
    protokoll = copy.deepcopy(PROTOKOLL_TEIL)
    protokoll["knoten"][0]["masse"].append({**protokoll["knoten"][0]["masse"][0], "name": "D1@Ebene1"})
    ist = _ist_teil()
    ist["features"].append(_f("Ebene1", "RefPlane", eltern=["Ebene vorne"]))
    assert _teil(ist, protokoll)["features_neu"] == []
    ist["features"][-1]["typ"] = "Fillet"                 # gleicher Name, falscher Typ
    assert [f["name"] for f in _teil(ist, protokoll)["features_neu"]] == ["Ebene1"]


# --- 9: nichts doppelt ------------------------------------------------------------------------------------------------

def test_9_gemeinsame_tabellen_und_helfer():
    assert abgleich.COMPILER_ENDUNGEN is laden.COMPILER_ENDUNGEN
    assert abgleich.ist_ordner is sw_bestand.ist_ordner
    from swki.baugruppe.sw_baugruppe import MATE_KOPPLUNG, MATE_TYP

    assert abgleich.VERKNUEPFUNGS_TYPEN == frozenset(MATE_TYP) | frozenset(MATE_KOPPLUNG)
    for typ, code in {**MATE_KOPPLUNG, **{k: v for k, v in MATE_TYP.items() if not k.startswith("grenze_")}}.items():
        assert abgleich.mate_name(code, grenze=False) == typ
    assert abgleich.mate_name(5, grenze=True) == "grenze_abstand" and abgleich.mate_name(6, grenze=True) == "grenze_winkel"


def test_9_eigenschaften_kommen_aus_dem_compiler():
    from swki.compiler.eigenschaften import eigenschaften_fuer

    soll = eigenschaften_fuer(SPEC_TEIL, "A")
    ist = _ist_teil()
    ist["eigenschaften"]["datei"] = dict(soll)
    assert _teil(ist)["eigenschaften"] == {"geaendert": [], "fehlen": [], "neu": []}
    del ist["eigenschaften"]["datei"]["Ersteller"]
    assert _teil(ist)["eigenschaften"]["fehlen"] == [{"name": "Ersteller", "soll": soll["Ersteller"]}]


# --- Neue Konfiguration -------------------------------------------------------------------------------------------------

def test_neue_konfiguration_am_teil_wird_genannt_und_der_rest_ist_luecke():
    ist = _ist_teil()
    ist["konfigurationen"] = ["Standard", "Variante"]
    for m in ist["masse"]:
        m["werte"]["Variante"] = 99.0
    a = _teil(ist)
    assert a["konfigurationen_neu"] == ["Standard", "Variante"]      # welche die gebaute war, steht nicht im Protokoll
    assert a["vollstaendig"] is False and any("Konfiguration" in text and "Variante" in text for text in a["luecken"])
    assert a["nicht_erklaert"] is False


def test_eine_konfiguration_ist_keine_neue():
    assert _teil(_ist_teil())["konfigurationen_neu"] == []


def test_neue_konfiguration_an_der_baugruppe():
    ist = _ist_bg()
    ist["konfigurationen"] = ["Standard", "Variante"]
    a = _bg(ist)
    assert a["konfigurationen_neu"] and a["vollstaendig"] is False and any("Konfiguration" in text for text in a["luecken"])


# --- 7: Aufnahme-Schutz schlägt nicht offen fehl -----------------------------------------------------------------------

def _herkunft(r, text, auftrag="B", nummer=1):
    pfad = r.arbeitsordner / auftrag / f"bestand-{nummer}" / "herkunft.json"
    pfad.parent.mkdir(parents=True)
    pfad.write_text(text, encoding="utf-8")
    return pfad


def _attrappen(monkeypatch, r, datei, geoeffnet):
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: geoeffnet.append("verbinde") or "app")
    monkeypatch.setattr(aenderungen, "oeffne", lambda app, pfad, **k: geoeffnet.append(pfad) or "modell")
    monkeypatch.setattr(aenderungen.sw, "schliesse", lambda app, model: None)
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {datei.name: {"L": 100}})
    monkeypatch.setattr(aenderungen, "soll_masse", lambda *a: {})
    monkeypatch.setattr(aenderungen, "soll_teile", lambda *a: {})
    monkeypatch.setattr(aenderungen, "lies_globale_variablen", lambda m: {"L": 100})


def test_7_unlesbare_herkunft_wird_gemeldet(umgebung):
    r, _ = umgebung
    pfad = _herkunft(r, '{"auftrag": "A", "lauf": 1, "spec"')
    [eintrag] = unlesbare_herkunft(r)
    assert eintrag["pfad"] == str(pfad) and eintrag["grund"]
    assert aufnahmen_aus_lauf(r, r.arbeitsordner / "A" / "lauf-1") == []


def test_7_herkunft_ohne_auftrag_oder_lauf_ist_unlesbar(umgebung):
    r, _ = umgebung
    _herkunft(r, json.dumps({"spec": "x.yaml"}))
    _herkunft(r, json.dumps([1]), auftrag="C")
    assert len(unlesbare_herkunft(r)) == 2


def test_7_lesbare_herkunft_ist_nicht_unlesbar(umgebung):
    r, _ = umgebung
    _herkunft(r, json.dumps({"auftrag": "A", "lauf": 1, "spec": "x.yaml"}))
    assert unlesbare_herkunft(r) == []


def test_7_aenderungen_oeffnet_bei_unlesbarer_herkunft_nichts(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    datei.write_bytes(b"x")
    pfad = _herkunft(r, '{"auftrag": "A", "lauf": 1, "spec"')
    geoeffnet = []
    _attrappen(monkeypatch, r, datei, geoeffnet)
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert geoeffnet == []
    assert ergebnis["unlesbar"][0]["pfad"] == str(pfad) and "herkunft.json" in ergebnis["text"]
    [eintrag] = ergebnis["geaendert"]
    assert eintrag["datei"] == datei.name and eintrag["sha256"]["ist"]


def test_7_auftrag_ohne_beachtung_der_schreibweise(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    datei.write_bytes(b"x")
    _herkunft(r, json.dumps({"auftrag": "a", "lauf": 1, "spec": "x.yaml"}))
    geoeffnet = []
    _attrappen(monkeypatch, r, datei, geoeffnet)
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert geoeffnet == [] and ergebnis["aufnahmen"] == [{"auftrag": "B", "aufnahme": 1}]
    assert [t["nummer"] for t in aufnahmen_aus_lauf(r, r.arbeitsordner / "A" / "lauf-1")] == [1]


def test_7_manuell_geaendert_nennt_die_unlesbare_herkunft(umgebung):
    r, spec_pfad = umgebung
    _lauf(r, spec_pfad, 1).write_bytes(b"x")
    pfad = _herkunft(r, "{")
    with pytest.raises(AenderungFehler) as e:
        pruefe_unveraendert(r, "A", spec_pfad)
    assert e.value.daten["herkunft_unlesbar"][0]["pfad"] == str(pfad) and "herkunft.json" in str(e.value)
    assert "swki aenderungen" not in str(e.value)       # das würde den Lauf in SolidWorks öffnen
