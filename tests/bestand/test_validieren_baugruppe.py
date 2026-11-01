"""Validierung einer Änderungs-Spec an einer Baugruppe gegen die Aufnahme (Plan Etappe 2 Task 4, Spec §4.1 Grenzen, §4.4, §8.2)."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from swki.bestand.ablage import schreibe_aufnahme, schreibe_datei_aufnahme
from swki.bestand.fehler import (BEREICH_FEHLT, BESTAND_ALTWERT, BESTAND_REFERENZ, BESTAND_REFERENZ_EXTERN, BESTAND_UNBEKANNT,
                                 BESTAND_VERALTET, MASS_GESTEUERT, NAME_BELEGT, VERKNUEPFUNGEN_FEHLEN, BestandFehler)
from swki.bestand.spec import aufnahme_zu, freigeben, validieren
from swki.bestand.spec_baugruppe import befunde_baugruppe, freigabe_angaben, pruefe_baugruppe
from swki.cli import main
from swki.konfig import Rechner
from swki.spec.freigabe import pruefsumme
from swki.spec.laden import SpecFehler
from tests.bestand.beispiel_baugruppe import DATEIEN, SPEC, baugruppen_aufnahme, datei_aufnahmen, teil_aufnahme
from tests.bestand.test_spec_baugruppe import _teil


def _spec(*punkte, bereiche=None, **mehr) -> dict:
    spec = copy.deepcopy(SPEC)
    spec["punkte"] = copy.deepcopy(list(punkte))
    spec["bereiche"] = copy.deepcopy(bereiche or [])
    spec["pruefung"] = {}
    spec.update(mehr)
    return spec


def _punkt(pid):
    return copy.deepcopy(next(p for p in SPEC["punkte"] if p["id"] == pid))


def _befunde(spec, aufnahme=None, tmp=None):
    return befunde_baugruppe(spec, aufnahme or baugruppen_aufnahme(), datei_aufnahmen(), tmp or Path("."))[0]


def _hinweise(spec, aufnahme=None, tmp=None):
    return befunde_baugruppe(spec, aufnahme or baugruppen_aufnahme(), datei_aufnahmen(), tmp or Path("."))[1]


def _codes(befunde) -> list:
    return [b.get("code") for b in befunde]


def _pfade(befunde) -> list[str]:
    return [b["pfad"] for b in befunde]


def _bereich(*pids, datei="teile/Platte.SLDPRT"):
    return {"punkte": list(pids), "in_datei": datei, "box": {"min": [0, 0, 0], "max": [1, 1, 1]}}


# --- Basis: die Beispiel-Spec ist gegen die Attrappe gültig ---

def test_beispiel_spec_ist_gegen_die_aufnahme_gueltig(tmp_path):
    assert pruefe_baugruppe(SPEC, baugruppen_aufnahme(), datei_aufnahmen(), tmp_path)[0] == []


# --- Teil-Punkte: in_datei ---

def test_teil_punkt_mit_unbekannter_datei():
    (b,) = _befunde(_spec({**_punkt("p1"), "in_datei": "teile/Gibts.SLDPRT"}))
    assert b["code"] == BESTAND_REFERENZ and b["pfad"] == "punkte[0].in_datei"
    assert "teile/Platte.SLDPRT" in b["meldung"] and "teile/Platte.SLDPRT" in b["dateien"]


@pytest.mark.parametrize("datei", ["C:\\Kunde\\teile\\Platte.SLDPRT", "/etc/Platte.SLDPRT", "teile/../../Platte.SLDPRT"])
def test_in_datei_muss_relativ_sein(datei):
    (b,) = _befunde(_spec({**_punkt("p1"), "in_datei": datei}))
    assert b["code"] == BESTAND_REFERENZ and "relativ" in b["meldung"]


def test_in_datei_findet_die_datei_unabhaengig_von_der_schreibweise():
    assert _befunde(_spec({**_punkt("p1"), "in_datei": "Teile\\PLATTE.sldprt"}, bereiche=[_bereich("p1", datei="teile/platte.sldprt")])) == []


def test_teil_punkt_auf_datei_mit_referenz():
    (b,) = _befunde(_spec({**_punkt("p1"), "in_datei": "teile/Abgeleitet.SLDPRT"}))
    assert b["code"] == BESTAND_REFERENZ_EXTERN and "teile/Basis.SLDPRT" in b["meldung"]


def test_teil_punkt_auf_basisteil_eines_anderen():
    (b,) = _befunde(_spec({**_punkt("p1"), "in_datei": "teile/Basis.SLDPRT"}))
    assert b["code"] == BESTAND_REFERENZ_EXTERN and "teile/Abgeleitet.SLDPRT" in b["meldung"]


def test_teil_punkt_auf_virtuelles_teil():
    (b,) = _befunde(_spec({**_punkt("p1"), "in_datei": "Teil1^Haupt.sldprt"}))
    assert b["code"] == BESTAND_REFERENZ and "virtuell" in b["meldung"]


def test_teil_punkt_auf_unterbaugruppe():
    (b,) = _befunde(_spec({**_punkt("p1"), "in_datei": "Unter.SLDASM"}))
    assert b["code"] == BESTAND_REFERENZ and "Unterbaugruppe" in b["meldung"]


def test_punkt_auf_die_hauptbaugruppe_mit_in_datei_ist_ein_befund():
    (b,) = _befunde(_spec({**_punkt("s1"), "in_datei": "Haupt.SLDASM"}))
    assert b["code"] == BESTAND_REFERENZ and "weglassen" in b["meldung"]


OHNE_IN_DATEI = {
    "mass": {"typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 41},
    "gleichung": {"typ": "gleichung", "variable": "L", "alt": 100, "neu": 101},
    "unterdruecken": {"typ": "unterdruecken", "feature": "Fase3"},
    "aufheben": {"typ": "aufheben", "feature": "Fase3"},
    "loeschen": {"typ": "loeschen", "feature": "Verrundung1"},
    "feature": {"typ": "feature", "name": "Neu", "feature": {"typ": "extrusion"}},
    "material": {"typ": "material", "neu": "1.4301"},
}


@pytest.mark.parametrize("typ", sorted(OHNE_IN_DATEI))
def test_teil_typ_ohne_in_datei_an_baugruppe(typ):
    (b,) = _befunde(_spec({"id": "x1", **OHNE_IN_DATEI[typ]}))
    assert b["code"] == BESTAND_REFERENZ and b["pfad"] == "punkte[0]" and "in_datei" in b["meldung"]


def test_eigenschaft_ohne_in_datei_ist_erlaubt():
    assert _befunde(_spec(_punkt("s1"))) == []


def test_skript_ohne_in_datei_ist_haupt_punkt_und_braucht_einen_bereich(tmp_path):
    (tmp_path / "skripte").mkdir()
    (tmp_path / "skripte" / "s2.py").write_text("def bauen(ctx):\n    pass\n", encoding="utf-8")
    spec = _spec({"id": "s2", "typ": "skript", "datei": "skripte/s2.py", "luecke": "x"})
    assert _befunde(spec, tmp=tmp_path) == []
    (b,) = pruefe_baugruppe(spec, baugruppen_aufnahme(), datei_aufnahmen(), tmp_path)[0]
    assert b["code"] == BEREICH_FEHLT and b["pfad"] == "punkte[0]"


# --- Komponenten ---

def test_komponente_in_unterbaugruppe_als_ziel():
    for typ in ({"typ": "komponente_entfernen", "komponente": "Unter-1/Welle-1", "verknuepfungen": ["Konzentrisch5"]},
                {"typ": "komponente_neu", "wie": "Unter-1/Welle-1"},
                {"typ": "komponente_ersetzen", "komponente": "Unter-1/Welle-1", "quelle": {"normteil": "ISO 4762 M6x16"}}):
        (b,) = _befunde(_spec({"id": "x1", **typ}))
        assert b["code"] == BESTAND_REFERENZ and "Unterbaugruppe" in b["meldung"], typ


def test_komponente_in_unterbaugruppe_als_partner_einer_verknuepfung():
    v = {**_punkt("v1"), "b": {"komponente": "Unter-1/Welle-1", "nahe": [0, 0, 0]}}
    assert _befunde(_spec(_punkt("k1"), v)) == []


def test_virtuelle_komponente_ist_kein_ziel():
    (b,) = _befunde(_spec({"id": "x1", "typ": "komponente_entfernen", "komponente": "Teil1^Haupt-1", "verknuepfungen": []}))
    assert b["code"] == BESTAND_REFERENZ and "virtuell" in b["meldung"]


def test_komponente_unbekannt():
    punkte = [{"id": "x1", "typ": "komponente_entfernen", "komponente": "Nix-1", "verknuepfungen": []},
              {"id": "x2", "typ": "komponente_ersetzen", "komponente": "Nix-1", "quelle": {"normteil": "ISO 4762 M6x16"}},
              {"id": "x3", "typ": "komponente_neu", "wie": "Nix-1"},
              {**_punkt("v1"), "id": "x4", "a": {"komponente": "Nix-1", "ebene": "oben"}},
              {**_punkt("s1"), "id": "x5", "lage_folgen": ["Nix-1"]}]
    befunde = _befunde(_spec(*punkte))
    assert _codes(befunde) == [BESTAND_REFERENZ] * 5
    assert _pfade(befunde) == ["punkte[0].komponente", "punkte[1].komponente", "punkte[2].wie", "punkte[3].a.komponente",
                               "punkte[4].lage_folgen[0]"]
    assert "Nix-1" in befunde[0]["meldung"] and "Gehaeuse-1" in befunde[0]["vorhanden"]


def test_neue_komponente_muss_vor_ihrer_verknuepfung_stehen():
    befunde = _befunde(_spec(_punkt("v1"), _punkt("k1")))
    assert _codes(befunde) == [BESTAND_REFERENZ] and befunde[0]["pfad"] == "punkte[0].a.komponente"
    assert _befunde(_spec(_punkt("k1"), _punkt("v1"))) == []


def test_anlage_der_verknuepfung_pruft_die_komponente():
    v = {**_punkt("v1"), "art": "scharnier", "anlage_a": {"komponente": "Nix-1", "ebene": "oben"}}
    (b,) = _befunde(_spec(_punkt("k1"), v))
    assert b["pfad"] == "punkte[1].anlage_a.komponente"


def test_entfernen_nennt_nicht_alle_verknuepfungen():
    (b,) = _befunde(_spec({"id": "e1", "typ": "komponente_entfernen", "komponente": "Deckel-1", "verknuepfungen": ["Deckungsgleich3"]}))
    assert b["code"] == VERKNUEPFUNGEN_FEHLEN and b["fehlen"] == ["Konzentrisch2"] and b["pfad"] == "punkte[0].verknuepfungen"


def test_entfernen_mit_allen_verknuepfungen_ist_gueltig():
    e1 = {"id": "e1", "typ": "komponente_entfernen", "komponente": "Deckel-1", "verknuepfungen": ["Konzentrisch2", "Deckungsgleich3"]}
    assert _befunde(_spec(e1)) == []


def test_entfernen_einer_komponente_ohne_verknuepfung():
    assert _befunde(_spec({"id": "e1", "typ": "komponente_entfernen", "komponente": "Basis-1", "verknuepfungen": []})) == []


def test_entfernen_nennt_eine_verknuepfung_die_nicht_dran_haengt_oder_nicht_existiert():
    e1 = {"id": "e1", "typ": "komponente_entfernen", "komponente": "Deckel-1",
          "verknuepfungen": ["Konzentrisch2", "Deckungsgleich3", "Abstand1", "Gibts1"]}
    befunde = _befunde(_spec(e1))
    assert _pfade(befunde) == ["punkte[0].verknuepfungen[2]", "punkte[0].verknuepfungen[3]"]
    assert _codes(befunde) == [BESTAND_REFERENZ] * 2


def test_entfernen_der_unterbaugruppe_nimmt_die_verknuepfungen_ihrer_komponenten_mit():
    e1 = {"id": "e1", "typ": "komponente_entfernen", "komponente": "Unter-1", "verknuepfungen": []}
    (b,) = _befunde(_spec(e1))
    assert b["code"] == VERKNUEPFUNGEN_FEHLEN and b["fehlen"] == ["Konzentrisch5"]


# --- Verknüpfungen ---

def test_verknuepfung_von_gleichung_gesteuert():
    (b,) = _befunde(_spec({"id": "w9", "typ": "verknuepfung_wert", "verknuepfung": "Abstand3", "alt": 7, "neu": 8}))
    assert b["code"] == MASS_GESTEUERT and b["pfad"] == "punkte[0].verknuepfung" and "skript" in b["meldung"]


def test_verknuepfung_unbekannt():
    for typ in ({"typ": "verknuepfung_wert", "verknuepfung": "Gibts1", "alt": 7, "neu": 8},
                {"typ": "verknuepfung_loeschen", "verknuepfung": "Gibts1"}):
        (b,) = _befunde(_spec({"id": "w9", **typ}))
        assert b["code"] == BESTAND_REFERENZ and b["pfad"] == "punkte[0].verknuepfung"


def test_verknuepfung_loeschen_bekannte_ist_gueltig():
    assert _befunde(_spec({"id": "l1", "typ": "verknuepfung_loeschen", "verknuepfung": "Abstand2"})) == []


def test_verknuepfung_wert_altwert():
    (b,) = _befunde(_spec({**_punkt("w1"), "alt": 11}))
    assert b["code"] == BESTAND_ALTWERT and b["pfad"] == "punkte[0].alt"
    assert _befunde(_spec(_punkt("w1"))) == []


def test_verknuepfung_wert_altwert_auch_fuer_die_grenze():
    w = {"id": "w2", "typ": "verknuepfung_wert", "verknuepfung": "Grenze_Abstand1", "grenze": "max", "alt": 5, "neu": 6}
    assert _befunde(_spec(w)) == []
    (b,) = _befunde(_spec({**w, "alt": 6}))
    assert b["code"] == BESTAND_ALTWERT and b["werte"] == {"max": 5.0}
    assert _befunde(_spec({**w, "grenze": "min", "alt": 0})) == []
    (b,) = _befunde(_spec({**w, "grenze": "min", "alt": 1}))
    assert b["code"] == BESTAND_ALTWERT


def test_verknuepfung_wert_ohne_zahl():
    """Eine konzentrische Verknüpfung hat keinen Wert."""
    (b,) = _befunde(_spec({"id": "w9", "typ": "verknuepfung_wert", "verknuepfung": "Konzentrisch2", "alt": 0, "neu": 1}))
    assert "Wert" in b["meldung"] and b["pfad"] == "punkte[0].verknuepfung"


def test_grenze_nur_an_grenzverknuepfungen():
    (b,) = _befunde(_spec({**_punkt("w1"), "grenze": "max"}))
    assert b["pfad"] == "punkte[0].grenze" and "keine Grenzverknüpfung" in b["meldung"]


def test_grenzverknuepfung_braucht_die_angabe_min_oder_max():
    (b,) = _befunde(_spec({"id": "w9", "typ": "verknuepfung_wert", "verknuepfung": "Grenze_Abstand1", "alt": 5, "neu": 6}))
    assert b["pfad"] == "punkte[0].grenze" and "min" in b["meldung"] and "max" in b["meldung"]


@pytest.mark.parametrize("art, fehlt", [("abstand", ["wert"]), ("winkel", ["wert"]), ("grenze_abstand", ["min", "max"]),
                                        ("grenze_winkel", ["min", "max"])])
def test_verknuepfung_neu_pflichtfelder_je_art(art, fehlt):
    v = {k: w for k, w in _punkt("v1").items() if k not in ("wert",)}
    v["art"] = art
    befunde = _befunde(_spec(_punkt("k1"), v))
    assert _pfade(befunde) == [f"punkte[1].{f}" for f in fehlt]


@pytest.mark.parametrize("art", ["deckungsgleich", "konzentrisch", "parallel", "senkrecht", "scharnier"])
def test_verknuepfung_neu_ohne_wert_ist_bei_anderen_arten_gueltig(art):
    v = {k: w for k, w in _punkt("v1").items() if k != "wert"}
    assert _befunde(_spec(_punkt("k1"), {**v, "art": art})) == []


def test_verknuepfung_neu_grenze_min_ueber_max():
    v = {**_punkt("v1"), "art": "grenze_abstand", "min": 15, "max": "=ABSTAND_NEU"}
    (b,) = _befunde(_spec(_punkt("k1"), v))
    assert b["pfad"] == "punkte[1].min" and "größer" in b["meldung"]
    assert _befunde(_spec(_punkt("k1"), {**v, "min": 1})) == []


# --- Neue Komponenten: Quelle und Dateiname ---

def test_neue_datei_heisst_wie_eine_im_bestand():
    a = baugruppen_aufnahme()
    a["dateien"]["ISO4762_M6x16_8_8.SLDPRT"] = copy.deepcopy(DATEIEN["teile/Platte.SLDPRT"])
    (b,) = _befunde(_spec(_punkt("k1")), a)
    assert b["code"] == NAME_BELEGT and b["pfad"] == "punkte[0].quelle" and b["datei"] == "ISO4762_M6x16_8_8.sldprt"
    assert "wie" in b["meldung"]


def test_neue_datei_heisst_wie_eine_im_bestand_in_einem_unterordner():
    """Neue Dateien liegen flach neben der Hauptbaugruppe, SolidWorks öffnet aber keine zwei gleichnamigen Dokumente."""
    a = baugruppen_aufnahme()
    a["dateien"]["teile/iso4762_m6x16_8_8.sldprt"] = copy.deepcopy(DATEIEN["teile/Platte.SLDPRT"])
    assert _codes(_befunde(_spec(_punkt("k1")), a)) == [NAME_BELEGT]


def test_neue_teil_datei_heisst_wie_eine_im_bestand(tmp_path):
    (tmp_path / "Deckel.yaml").write_text(yaml.safe_dump(_teil(name="Deckel")), encoding="utf-8")
    k = {"id": "k3", "typ": "komponente_neu", "quelle": {"teil": "Deckel.yaml"}}
    (b,) = _befunde(_spec(k), tmp=tmp_path)
    assert b["code"] == NAME_BELEGT and b["datei"] == "Deckel.sldprt" and "teile/Deckel.SLDPRT" in b["meldung"]


def test_neue_teil_datei_ist_der_name_der_teil_spec_mit_endung(tmp_path):
    (tmp_path / "Deckel2.yaml").write_text(yaml.safe_dump(_teil(name="Deckel2")), encoding="utf-8")
    k3 = {"id": "k3", "typ": "komponente_neu", "quelle": {"teil": "Deckel2.yaml"}}
    k4 = {"id": "k4", "typ": "komponente_neu", "quelle": {"teil": "Deckel2.yaml"}}
    assert _befunde(_spec(k3, k4), tmp=tmp_path) == []  # dieselbe Datei zweimal eingebaut, ein Name


def test_zwei_verschiedene_quellen_mit_gleichem_dateinamen(tmp_path):
    (tmp_path / "a.yaml").write_text(yaml.safe_dump(_teil(name="Gleich")), encoding="utf-8")
    (tmp_path / "b.yaml").write_text(yaml.safe_dump(_teil(name="Gleich", hoehe=20)), encoding="utf-8")
    punkte = [{"id": "k3", "typ": "komponente_neu", "quelle": {"teil": "a.yaml"}},
              {"id": "k4", "typ": "komponente_neu", "quelle": {"teil": "b.yaml"}}]
    (b,) = _befunde(_spec(*punkte), tmp=tmp_path)
    assert b["code"] == NAME_BELEGT and b["pfad"] == "punkte[1].quelle"


def test_neue_kaufteil_datei_heisst_wie_eine_im_bestand():
    a = baugruppen_aufnahme()
    a["dateien"]["Nanotec_GPLE60-2S-32.SLDPRT"] = copy.deepcopy(DATEIEN["teile/Platte.SLDPRT"])
    k = {"id": "k4", "typ": "komponente_neu", "quelle": {"kaufteil": "Nanotec GPLE60-2S-32"}}
    (b,) = _befunde(_spec(k), a)
    assert b["code"] == NAME_BELEGT and b["datei"] == "Nanotec_GPLE60-2S-32.sldprt"
    assert _befunde(_spec(k)) == []


def test_ersetzen_prueft_den_namen_der_neuen_datei():
    a = baugruppen_aufnahme()
    a["dateien"]["ISO4762_M8x20_8_8.SLDPRT"] = copy.deepcopy(DATEIEN["teile/Platte.SLDPRT"])
    e = {"id": "e2", "typ": "komponente_ersetzen", "komponente": "Schraube-2", "quelle": {"normteil": "ISO 4762 M8x20"}}
    assert _codes(_befunde(_spec(e), a)) == [NAME_BELEGT]
    assert _befunde(_spec(e)) == []


def test_wie_mit_gleicher_datei_ist_kein_name_belegt():
    assert _befunde(_spec({"id": "k2", "typ": "komponente_neu", "wie": "Schraube-1"})) == []


def test_wie_nennt_nur_vorhandene_komponenten():
    (b,) = _befunde(_spec(_punkt("k1"), {"id": "k2", "typ": "komponente_neu", "wie": "k1"}))
    assert b["code"] == BESTAND_REFERENZ and b["pfad"] == "punkte[1].wie"


def test_wie_konfiguration_muss_in_der_datei_vorkommen():
    k = {"id": "k2", "typ": "komponente_neu", "wie": "Schraube-1", "konfiguration": "Gibts nicht"}
    (b,) = _befunde(_spec(k))
    assert b["code"] == BESTAND_REFERENZ and b["pfad"] == "punkte[0].konfiguration"
    assert _befunde(_spec({**k, "konfiguration": "Variante B"})) == []


def test_unbekannte_normteil_quelle_ist_befund():
    k = {"id": "k1", "typ": "komponente_neu", "quelle": {"normteil": "ISO 4762 M6x17"}}
    (b,) = _befunde(_spec(k))
    assert b["pfad"] == "punkte[0].quelle" and "NORMLAENGE_UNGUELTIG" in b["meldung"]


def test_unbekanntes_kaufteil_ist_befund():
    k = {"id": "k1", "typ": "komponente_neu", "quelle": {"kaufteil": "Nanotec Gibtsnicht"}}
    (b,) = _befunde(_spec(k))
    assert b["pfad"] == "punkte[0].quelle" and "KAUFTEIL_UNBEKANNT" in b["meldung"]


def test_teil_quelle_fehlt(tmp_path):
    k = {"id": "k3", "typ": "komponente_neu", "quelle": {"teil": "Gibts.yaml"}}
    (b,) = _befunde(_spec(k), tmp=tmp_path)
    assert b["pfad"] == "punkte[0].quelle.teil" and "Gibts.yaml" in b["meldung"]


def test_teil_quelle_muss_art_teil_haben(tmp_path):
    (tmp_path / "Anderes.yaml").write_text(yaml.safe_dump({"art": "baugruppe", "name": "Anderes"}), encoding="utf-8")
    k = {"id": "k3", "typ": "komponente_neu", "quelle": {"teil": "Anderes.yaml"}}
    (b,) = _befunde(_spec(k), tmp=tmp_path)
    assert b["pfad"] == "punkte[0].quelle.teil" and "art: teil" in b["meldung"] and "baugruppe" in b["meldung"]


def test_teil_quelle_mit_schemafehler_nennt_die_datei(tmp_path):
    kaputt = _teil(name="Kaputt")
    del kaputt["features"]
    (tmp_path / "Kaputt.yaml").write_text(yaml.safe_dump(kaputt), encoding="utf-8")
    befunde = _befunde(_spec({"id": "k3", "typ": "komponente_neu", "quelle": {"teil": "Kaputt.yaml"}}), tmp=tmp_path)
    assert befunde and all(b["pfad"].startswith("Kaputt.yaml: ") for b in befunde)


# --- lage_folgen, kollision_erlaubt ---

def test_lage_folgen_unbekannt():
    (b,) = _befunde(_spec({**_punkt("p3"), "lage_folgen": ["Deckel-1", "Nix-2"]}, bereiche=[_bereich("p3", datei="teile/Deckel.SLDPRT")]))
    assert b["code"] == BESTAND_REFERENZ and b["pfad"] == "punkte[0].lage_folgen[1]"


def test_lage_folgen_nennt_auch_neue_komponenten():
    assert _befunde(_spec(_punkt("k1"), {**_punkt("s1"), "lage_folgen": ["k1", "Unter-1/Welle-1"]})) == []


def test_kollision_erlaubt_nennt_unbekannte_komponente():
    spec = _spec(_punkt("k1"), kollision_erlaubt=[{"paar": ["k1", "Gehaeuse-1"], "grund": "Schraube im Kernloch"},
                                                  {"paar": ["k1", "Nix-3"], "grund": "x"}])
    (b,) = _befunde(spec)
    assert b["code"] == BESTAND_REFERENZ and b["pfad"] == "kollision_erlaubt[1].paar[1]"


def test_kollision_erlaubt_nennt_neue_komponente_auch_vor_ihrem_punkt():
    spec = _spec(_punkt("k1"), kollision_erlaubt=[{"paar": ["k1", "Gehaeuse-1"], "grund": "Schraube im Kernloch"}])
    assert _befunde(spec) == []
    ohne = _spec(kollision_erlaubt=[{"paar": ["k1", "Gehaeuse-1"], "grund": "x"}])
    assert _codes(_befunde(ohne)) == [BESTAND_REFERENZ]


# --- Bereiche und Messungen ---

def test_bereich_nennt_unbekannten_punkt_und_unbekannte_datei():
    spec = _spec(_punkt("p1"), bereiche=[_bereich("p1", "gibts_nicht"), {**_bereich("p1"), "in_datei": "teile/Gibts.SLDPRT"}])
    befunde = _befunde(spec)
    assert _pfade(befunde) == ["bereiche[0].punkte[1]", "bereiche[1].in_datei"]
    assert befunde[1]["code"] == BESTAND_REFERENZ


def test_bereich_einer_anderen_datei_deckt_den_teil_punkt_nicht():
    spec = _spec(_punkt("p3"), bereiche=[_bereich("p3", datei="teile/Platte.SLDPRT")])
    (b,) = _befunde(spec)
    assert b["pfad"] == "bereiche[0].punkte[0]" and "teile/Deckel.SLDPRT" in b["meldung"] and "teile/Platte.SLDPRT" in b["meldung"]


def test_bereich_ohne_in_datei_gilt_fuer_die_hauptbaugruppe_nicht_fuer_teile():
    spec = _spec(_punkt("p1"), bereiche=[{"punkte": ["p1"], "box": {"min": [0, 0, 0], "max": [1, 1, 1]}}])
    (b,) = _befunde(spec)
    assert b["pfad"] == "bereiche[0].punkte[0]" and "Haupt.SLDASM" in b["meldung"]


def test_bereich_darf_baugruppen_punkte_nennen():
    spec = _spec(_punkt("p1"), _punkt("k1"), bereiche=[_bereich("p1", "k1")])
    assert _befunde(spec) == []


def test_masse_pruefen_braucht_in_datei_und_eine_datei_mit_punkten():
    spec = _spec(_punkt("p1"), bereiche=[_bereich("p1")])
    messung = copy.deepcopy(SPEC["pruefung"]["masse_pruefen"][0])
    ohne = {k: v for k, v in messung.items() if k != "in_datei"}
    spec["pruefung"] = {"masse_pruefen": [ohne, {**messung, "in_datei": "teile/Gibts.SLDPRT"},
                                          {**messung, "in_datei": "teile/Deckel.SLDPRT"}, messung]}
    befunde = _befunde(spec)
    assert _pfade(befunde) == ["pruefung.masse_pruefen[0]", "pruefung.masse_pruefen[1].in_datei", "pruefung.masse_pruefen[2].in_datei"]
    assert befunde[1]["code"] == BESTAND_REFERENZ and "Teile" in befunde[0]["meldung"]


def test_volumen_delta_gilt_nicht_fuer_baugruppen():
    spec = _spec(_punkt("s1"))
    spec["pruefung"] = {"volumen_delta": {"soll": 10}}
    (b,) = _befunde(spec)
    assert b["pfad"] == "pruefung.volumen_delta" and "Baugruppe" in b["meldung"]


def test_punkt_id_darf_keine_komponente_nennen():
    a = baugruppen_aufnahme()
    a["komponenten"]["k1"] = copy.deepcopy(a["komponenten"]["Deckel-1"])  # umbenannte Komponente, so heißt auch ein Punkt
    (b,) = _befunde(_spec({**_punkt("s1"), "id": "k1"}), a)
    assert b["pfad"] == "punkte[0].id" and "Komponente" in b["meldung"]


# --- Bereiche und Teil-Prüfungen über den Etappe-1-Code ---

def test_baugruppen_punkt_braucht_keinen_bereich(tmp_path):
    spec = _spec(_punkt("k1"), _punkt("v1"), _punkt("w1"), {"id": "e1", "typ": "komponente_entfernen", "komponente": "Basis-1",
                                                           "verknuepfungen": []})
    assert pruefe_baugruppe(spec, baugruppen_aufnahme(), datei_aufnahmen(), tmp_path)[0] == []


def test_teil_punkt_braucht_bereich(tmp_path):
    (b,) = pruefe_baugruppe(_spec(_punkt("p3")), baugruppen_aufnahme(), datei_aufnahmen(), tmp_path)[0]
    assert b["code"] == BEREICH_FEHLT and b["pfad"] == "punkte[0]"


def test_befunde_der_teil_scheibe_tragen_den_pfad_der_ganzen_spec(tmp_path):
    spec = copy.deepcopy(SPEC)
    spec["punkte"][2]["alt"] = 41  # p3 steht an Stelle 2
    spec["punkte"][1]["feature"] = "Gibts nicht"  # p2
    befunde = pruefe_baugruppe(spec, baugruppen_aufnahme(), datei_aufnahmen(), tmp_path)[0]
    pfade = {b["pfad"]: b["code"] for b in befunde}
    assert pfade["punkte[2].alt"] == BESTAND_ALTWERT and pfade["punkte[1].feature"] == BESTAND_REFERENZ
    assert len(befunde) == 2


def test_teil_punkt_braucht_einen_bereich_in_der_eigenen_datei(tmp_path):
    spec = _spec(_punkt("p3"), bereiche=[_bereich("p3", datei="teile/Platte.SLDPRT")])
    codes = _codes(pruefe_baugruppe(spec, baugruppen_aufnahme(), datei_aufnahmen(), tmp_path)[0])
    assert BEREICH_FEHLT in codes


def test_teil_punkte_werden_gegen_die_aufnahme_ihrer_datei_geprueft(tmp_path):
    abweichend = teil_aufnahme("teile/Deckel.SLDPRT")
    for m in abweichend["masse"]:
        if m["name"] == "D2@Skizze4":
            m["werte"] = {"Standard": 38.0, "Variante B": 38.0}
    assert pruefe_baugruppe(SPEC, baugruppen_aufnahme(), datei_aufnahmen(), tmp_path)[0] == []
    befunde = pruefe_baugruppe(SPEC, baugruppen_aufnahme(), datei_aufnahmen({"teile/Deckel.SLDPRT": abweichend}), tmp_path)[0]
    assert _pfade(befunde) == ["punkte[2].alt"] and befunde[0]["code"] == BESTAND_ALTWERT


def test_feature_punkt_in_teil_wird_wie_in_etappe_1_geprueft(tmp_path):
    f = {"id": "f1", "typ": "feature", "in_datei": "teile/Platte.SLDPRT", "name": "Gewinde M6 Deckel",
         "feature": {"typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"feature": "Gibts nicht", "flaeche": "+y"},
                     "positionen": [[1, 2]], "tiefe": 10, "gewindetiefe": 8}}
    befunde = pruefe_baugruppe(_spec(f, bereiche=[_bereich("f1")]), baugruppen_aufnahme(), datei_aufnahmen(), tmp_path)[0]
    assert befunde and all(b["pfad"].startswith("punkte[0].feature") for b in befunde)


# --- Hinweise ---

def test_hinweis_instanzen():
    p = {"id": "p9", "typ": "mass", "in_datei": "teile/Schraube.SLDPRT", "mass": "D2@Skizze4", "alt": 40, "neu": 41}
    h = _hinweise(_spec(p, bereiche=[_bereich("p9", datei="teile/Schraube.SLDPRT")]))
    (hin,) = [x for x in h if x["art"] == "instanzen"]
    assert hin["anzahl"] == 11 and hin["pfad"] == "punkte[0]" and hin["datei"] == "teile/Schraube.SLDPRT"
    assert "11" in hin["meldung"] and len(hin["komponenten"]) == 11


def test_keine_instanzen_hinweis_bei_einer_instanz():
    h = _hinweise(_spec(_punkt("p1"), bereiche=[_bereich("p1")]))
    assert not [x for x in h if x["art"] == "instanzen"]


def test_instanzen_hinweis_einmal_je_datei():
    p = {"id": "p9", "typ": "mass", "in_datei": "teile/Schraube.SLDPRT", "mass": "D2@Skizze4", "alt": 40, "neu": 41}
    q = {**p, "id": "p10", "mass": "D5@Skizze5", "alt": 12}
    h = _hinweise(_spec(p, q))
    assert len([x for x in h if x["art"] == "instanzen"]) == 1


def test_validieren_nennt_grenzen_ohne_fahrt():
    a = baugruppen_aufnahme(bewegungen={})
    (h,) = [x for x in _hinweise(_spec(_punkt("s1")), a) if x["art"] == "grenzen_ohne_fahrt"]
    assert h["grenzen"] == ["Grenze_Abstand1"] and "ok: None" in h["meldung"]


def test_grenze_die_im_bestand_nicht_fuhr_ist_ein_hinweis():
    a = baugruppen_aufnahme()
    a["bewegungen"]["Grenze_Abstand1"]["gefahren"] = False
    assert [x["grenzen"] for x in _hinweise(_spec(_punkt("s1")), a) if x["art"] == "grenzen_ohne_fahrt"] == [["Grenze_Abstand1"]]


def test_gefahrene_grenze_ist_kein_hinweis():
    assert not [x for x in _hinweise(_spec(_punkt("s1"))) if x["art"] == "grenzen_ohne_fahrt"]


def test_version_aelter_nennt_nur_dateien_die_gespeichert_werden(tmp_path):
    a = baugruppen_aufnahme()
    a["dateien"]["teile/Platte.SLDPRT"]["version_aelter"] = True
    a["dateien"]["teile/Deckel.SLDPRT"]["version_aelter"] = True
    spec = _spec(_punkt("p1"), _punkt("p2"), bereiche=[_bereich("p1", "p2")])
    h = pruefe_baugruppe(spec, a, datei_aufnahmen(), tmp_path)[1]
    assert [(x["datei"], x["pfad"]) for x in h if x["art"] == "version_aelter"] == [("teile/Platte.SLDPRT", "punkte[0].in_datei")]


def test_version_aelter_der_hauptbaugruppe_zaehlt_nur_wenn_sie_gespeichert_wird(tmp_path):
    a = baugruppen_aufnahme()
    a["datei"]["version_aelter"] = True
    nur_teil = _spec(_punkt("p1"), bereiche=[_bereich("p1")])
    assert not [x for x in pruefe_baugruppe(nur_teil, a, datei_aufnahmen(), tmp_path)[1] if x["art"] == "version_aelter"]
    mit_haupt = _spec(_punkt("s1"))
    (h,) = [x for x in pruefe_baugruppe(mit_haupt, a, datei_aufnahmen(), tmp_path)[1] if x["art"] == "version_aelter"]
    assert h["datei"] == "Haupt.SLDASM" and h["pfad"] == "bestand"


# --- Angaben für die Freigabe-Vorlage ---

def test_freigabe_angaben_je_punkt():
    p = {"id": "p9", "typ": "mass", "in_datei": "teile/Schraube.SLDPRT", "mass": "D2@Skizze4", "alt": 40, "neu": 41}
    spec = _spec(p, _punkt("p1"), _punkt("k1"),
                 {"id": "e1", "typ": "komponente_entfernen", "komponente": "Deckel-1", "verknuepfungen": ["Konzentrisch2", "Deckungsgleich3"]},
                 {"id": "e2", "typ": "komponente_ersetzen", "komponente": "Schraube-2", "quelle": {"normteil": "ISO 4762 M8x20"},
                  "alle_instanzen": True},
                 {"id": "e3", "typ": "komponente_ersetzen", "komponente": "Schraube-2", "quelle": {"normteil": "ISO 4762 M8x20"}},
                 {"id": "w2", "typ": "verknuepfung_wert", "verknuepfung": "Grenze_Abstand1", "grenze": "max", "alt": 5, "neu": 6},
                 {"id": "l1", "typ": "verknuepfung_loeschen", "verknuepfung": "Grenze_Abstand1"},
                 {"id": "l2", "typ": "verknuepfung_loeschen", "verknuepfung": "Abstand1"})
    angaben = freigabe_angaben(spec, baugruppen_aufnahme())
    assert set(angaben) == {"p9", "p1", "k1", "e1", "e2", "e3", "w2", "l1", "l2"}
    assert all(set(a) == {"instanzen", "verknuepfungen", "bewegungen"} for a in angaben.values())
    assert angaben["p9"] == {"instanzen": 11, "verknuepfungen": [], "bewegungen": []}
    assert angaben["p1"]["instanzen"] == 1 and angaben["k1"]["instanzen"] == 0
    assert angaben["e1"] == {"instanzen": 1, "verknuepfungen": ["Deckungsgleich3", "Konzentrisch2"], "bewegungen": []}
    assert angaben["e2"]["instanzen"] == 11 and angaben["e3"]["instanzen"] == 1
    assert angaben["e2"]["verknuepfungen"] == ["Abstand1", "Abstand2", "Abstand3"] and angaben["e3"]["verknuepfungen"] == ["Abstand2"]
    assert angaben["w2"] == {"instanzen": 0, "verknuepfungen": ["Grenze_Abstand1"], "bewegungen": ["Grenze_Abstand1"]}
    assert angaben["l1"] == angaben["w2"]
    assert angaben["l2"] == {"instanzen": 0, "verknuepfungen": ["Abstand1"], "bewegungen": []}


def test_freigabe_angaben_entfernen_nennt_die_bewegung_der_komponente():
    e = {"id": "e1", "typ": "komponente_entfernen", "komponente": "Schieber-1", "verknuepfungen": ["Grenze_Abstand1"]}
    assert freigabe_angaben(_spec(e), baugruppen_aufnahme())["e1"]["bewegungen"] == ["Grenze_Abstand1"]


# --- Durchgang durch validieren und freigeben ---

@pytest.fixture
def umg(tmp_path, monkeypatch):
    """Arbeitsordner mit Baugruppen-Aufnahme 1 (alle Teile aufgenommen) und Auftragsordner a1."""
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    monkeypatch.setattr("swki.bestand.spec.lade_rechner", lambda: r)
    schreibe_aufnahme(r, "a1", 1, baugruppen_aufnahme())
    for rel, d in DATEIEN.items():
        if d["art"] == "teil":
            schreibe_datei_aufnahme(r, "a1", 1, rel, teil_aufnahme(rel))
    ordner = tmp_path / "a1"
    ordner.mkdir()
    return type("Umgebung", (), {"r": r, "ordner": ordner})


def _schreibe(umg, spec, name="aenderung.yaml") -> Path:
    pfad = umg.ordner / name
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def test_validieren_einer_baugruppen_spec(umg):
    pfad = _schreibe(umg, SPEC)
    ergebnis = validieren(pfad)
    assert ergebnis["gueltig"] is True and ergebnis["art"] == "aenderung" and ergebnis["punkte"] == len(SPEC["punkte"])
    assert ergebnis["pruefsumme"] == pruefsumme(SPEC)
    assert ergebnis["version_aelter"] is False and ergebnis["dateien"] == ["teile/Platte.SLDPRT", "teile/Deckel.SLDPRT"]
    assert ergebnis["haupt_speichern"] is True
    assert ergebnis["folgen"] == {"p1": [], "p3": []}
    assert ergebnis["angaben"]["w1"]["verknuepfungen"] == ["Abstand1"]


def test_validieren_meldet_befunde_mit_pfad_der_ganzen_spec(umg):
    spec = copy.deepcopy(SPEC)
    spec["punkte"][2]["alt"] = 41
    with pytest.raises(SpecFehler) as e:
        validieren(_schreibe(umg, spec))
    assert [(b["pfad"], b["code"]) for b in e.value.daten["befunde"]] == [("punkte[2].alt", BESTAND_ALTWERT)]


def test_validieren_nennt_die_alte_datei_die_gespeichert_werden_muss(umg):
    a = baugruppen_aufnahme()
    a["dateien"]["teile/Deckel.SLDPRT"]["version_aelter"] = True
    schreibe_aufnahme(umg.r, "a1", 1, a)
    ergebnis = validieren(_schreibe(umg, SPEC))
    assert ergebnis["version_aelter"] is True
    (h,) = [x for x in ergebnis["hinweise"] if x["art"] == "version_aelter"]
    assert h["datei"] == "teile/Deckel.SLDPRT"


def test_validieren_ohne_alte_datei_im_speichersatz(umg):
    a = baugruppen_aufnahme()
    a["dateien"]["teile/Gehaeuse.SLDPRT"]["version_aelter"] = True  # wird nicht gespeichert
    schreibe_aufnahme(umg.r, "a1", 1, a)
    assert validieren(_schreibe(umg, SPEC))["version_aelter"] is False


def test_validieren_kennt_nur_die_jungste_aufnahme(umg):
    schreibe_aufnahme(umg.r, "a1", 2, baugruppen_aufnahme())
    with pytest.raises(BestandFehler) as e:
        validieren(_schreibe(umg, SPEC))
    assert e.value.daten["code"] == BESTAND_VERALTET


def test_aufnahme_zu_geht_fuer_baugruppen(umg):
    pfad = _schreibe(umg, SPEC)
    assert aufnahme_zu(SPEC, pfad)["art"] == "baugruppe"
    falsch = copy.deepcopy(SPEC)
    falsch["bestand"]["sha256"] = "0" * 64
    with pytest.raises(BestandFehler) as e:
        aufnahme_zu(falsch, pfad)
    assert e.value.daten["code"] == BESTAND_UNBEKANNT


def test_freigeben_einer_baugruppen_spec(umg, capsys):
    pfad = _schreibe(umg, SPEC)
    assert main(["freigeben", str(pfad)]) == 0
    assert json.loads(capsys.readouterr().out)["art"] == "aenderung"
    assert (umg.ordner / "aenderung.freigegeben.yaml").is_file()


def test_freigeben_verweigert_bei_befunden(umg):
    spec = copy.deepcopy(SPEC)
    spec["punkte"][-1]["alt"] = 11
    with pytest.raises(SpecFehler):
        freigeben(_schreibe(umg, spec))
    assert not (umg.ordner / "aenderung.freigegeben.yaml").exists()


def test_teil_aufnahmen_werden_nur_fuer_dateien_mit_punkten_gelesen(umg):
    """Eine fehlende Aufnahme einer Datei ohne Punkte stört nicht."""
    (umg.r.arbeitsordner / "a1" / "bestand-1" / "aufnahme" / "teile" / "Gehaeuse.SLDPRT.json").unlink()
    validieren(_schreibe(umg, SPEC))
