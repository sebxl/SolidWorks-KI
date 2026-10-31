"""Validierung einer Änderungs-Spec gegen die Bestandsaufnahme (Plan Task 4, Spec §4.4)."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from swki.bestand.ablage import schreibe_aufnahme
from swki.bestand.fehler import (BESTAND_ALTWERT, BESTAND_EINHEIT, BESTAND_REFERENZ, BESTAND_UNBEKANNT, BESTAND_VERALTET,
                                 BEREICH_FEHLT, FOLGEN_ABWEICHEND, KINDER_FEHLEN, MASS_GESTEUERT, BestandFehler)
from swki.bestand.spec import befunde_gegen_aufnahme, feature_befunde, freigeben, validieren
from swki.cli import main
from swki.konfig import Rechner
from swki.spec.freigabe import FreigabeFehler, pruefe_freigabe, pruefsumme
from swki.spec.laden import SpecFehler
from tests.bestand.beispiel_aufnahme import AUFNAHME, SHA, aufnahme

BASIS = {
    "art": "aenderung",
    "name": "Lagerdeckel_Rev",
    "bestand": {"datei": "Lagerdeckel.SLDPRT", "sha256": SHA, "aufnahme": 1},
    "parameter": {"A_neu": 45, "RA": 12},
    "punkte": [
        {"id": "p1", "was": "Abstand Bohrung 40 → 45", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": "=A_neu",
         "konfigurationen": "alle"},
        {"id": "p2", "was": "Fase entfällt", "typ": "unterdruecken", "feature": "Fase3"},
        {"id": "p3", "was": "Zwei Gewinde M6", "typ": "feature", "name": "Gewinde M6 Deckel",
         "feature": {"typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [0, 30, 20]},
                     "positionen": [["=-50+RA", 15], ["=-50+RA", -15]], "bezug": {"u": "-rand", "v": "mitte"},
                     "tiefe": 10, "gewindetiefe": 8}},
        {"id": "p4", "typ": "material", "neu": "1.4301"},
        {"id": "p5", "typ": "eigenschaft", "name": "Revision", "neu": "B"},
        {"id": "p6", "typ": "skript", "datei": "skripte/p6_endbedingung.py", "luecke": "Endbedingung ändern"},
    ],
    "bereiche": [
        {"punkte": ["p1", "p3", "p6"], "box": {"min": [-50, -20, 0], "max": [-20, 40, 20]}},
        {"punkte": ["p2"], "features": ["Fase3"]},
    ],
    "pruefung": {
        "masse_pruefen": [{"was": "Randabstand", "von": {"flaeche": {"nahe": [-50, 0, 10], "normale": [-1, 0, 0]}},
                           "zu": {"punkt": [-38, 15, 20]}, "soll": "=RA", "tol": 0.01}],
        "volumen_delta": {"soll": 1250, "toleranz_prozent": 1},
    },
}


def spec_mit(**aenderungen):
    spec = copy.deepcopy(BASIS)
    spec.update(aenderungen)
    return spec


def punkte(*punkte_, bereich=True):
    """Spec mit genau diesen Punkten; ein Bereich nennt alle (außer bei bereich=False)."""
    spec = spec_mit(punkte=list(punkte_), bereiche=[])
    if bereich:
        spec["bereiche"] = [{"punkte": [p["id"] for p in punkte_], "features": ["Fase3"]}]
    return spec


def codes(befunde) -> list[str | None]:
    return [b.get("code") for b in befunde]


# --- Grundzustand ---

def test_basis_ist_gegen_die_aufnahme_gueltig(tmp_path):
    assert befunde_gegen_aufnahme(BASIS, AUFNAHME) == []
    assert feature_befunde(BASIS, AUFNAHME, tmp_path)[0] == []


# --- mass ---

@pytest.mark.parametrize("name,code", [
    ("D1@Skizze1", MASS_GESTEUERT), ("D8@Skizze9", MASS_GESTEUERT), ("D7@Skizze9", MASS_GESTEUERT),
    ("D9@Weg", BESTAND_REFERENZ)])
def test_mass_punkt_befunde(name, code):
    spec = punkte({"id": "m1", "typ": "mass", "mass": name, "alt": 100, "neu": 110})
    befunde = befunde_gegen_aufnahme(spec, AUFNAHME)
    assert [(b["pfad"], b["code"]) for b in befunde] == [("punkte[0].mass", code)]


def test_gesteuert_nennt_die_quelle():
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D1@Skizze1", "alt": 100, "neu": 110})
    meldung = befunde_gegen_aufnahme(spec, AUFNAHME)[0]["meldung"]
    assert "Variable" in meldung and "L" in meldung
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D8@Skizze9", "alt": 4, "neu": 5})
    assert "Konstruktionstabelle" in befunde_gegen_aufnahme(spec, AUFNAHME)[0]["meldung"]


GLEICHUNG_L = {"id": "g1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110, "folgen": ["D1@Skizze1", "D3@Skizze2"]}
GLEICHUNG_D3 = {"id": "g1", "typ": "gleichung", "gleichung": "D3@Skizze2", "alt": '"D1@Skizze1" + 5', "neu": '"D1@Skizze1" + 6'}


@pytest.mark.parametrize("punkt", [GLEICHUNG_L, GLEICHUNG_D3], ids=["variable", "gleichung"])
@pytest.mark.parametrize("nummer, text", [(1, "CGS"), (2, "MKS"), (3, "Zoll"), (4, "benutzerdefiniert")])
def test_gleichung_in_datei_ohne_mm(punkt, nummer, text):
    """`alt` und `neu` gelten dort in der Einheit der Datei, Spec und Skill versprechen mm."""
    a = aufnahme(einheitensystem=nummer)
    (b,) = befunde_gegen_aufnahme(punkte(punkt), a)
    assert (b["pfad"], b["code"]) == ("punkte[0]", BESTAND_EINHEIT) and text in b["meldung"] and text in b["einheit"]


@pytest.mark.parametrize("punkt", [GLEICHUNG_L, GLEICHUNG_D3], ids=["variable", "gleichung"])
def test_gleichung_in_mm_ohne_befund(punkt):
    assert befunde_gegen_aufnahme(punkte(punkt), AUFNAHME) == []


def test_mass_punkt_rechnet_in_jeder_datei_in_mm():
    """`SetSystemValue3` nimmt Meter, das Einheitensystem spielt keine Rolle."""
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45})
    assert befunde_gegen_aufnahme(spec, aufnahme(einheitensystem=3)) == []


def test_verknuepftes_mass_ist_setzbar():
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D1@S5", "alt": 8, "neu": 9, "folgen": ["D2@S6"]})
    assert befunde_gegen_aufnahme(spec, AUFNAHME) == []


def test_altwert_abweichend():
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D2@Skizze4", "alt": 41, "neu": 45})
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME)
    assert (b["pfad"], b["code"]) == ("punkte[0].alt", BESTAND_ALTWERT)
    assert "Standard: 40" in b["meldung"]


def test_altwert_nennt_wert_je_konfiguration():
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D5@Skizze5", "alt": 12, "neu": 13, "konfigurationen": "alle"})
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME)
    assert b["code"] == BESTAND_ALTWERT and "Standard: 12" in b["meldung"] and "Variante B: 15" in b["meldung"]
    spec["punkte"][0]["konfigurationen"] = ["Standard"]
    assert befunde_gegen_aufnahme(spec, AUFNAHME) == []
    spec["punkte"][0].update(alt=15, konfigurationen=["Variante B"])
    assert befunde_gegen_aufnahme(spec, AUFNAHME) == []


def test_alt_in_unterdrueckter_konfiguration():
    # D2@Skizze4 ist in Variante B nicht lesbar (None): zählt nicht als Abweichung
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45, "konfigurationen": "alle"})
    assert befunde_gegen_aufnahme(spec, AUFNAHME) == []
    spec["punkte"][0]["konfigurationen"] = ["Variante B"]
    assert befunde_gegen_aufnahme(spec, AUFNAHME) == []


def test_altwert_toleriert_rauschen_der_gleitkommazahl():
    a = aufnahme()
    a["masse"][4]["werte"]["Standard"] = 40.0000000001
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45})
    assert befunde_gegen_aufnahme(spec, a) == []


def test_unbekannte_konfiguration():
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45, "konfigurationen": ["Gibt es nicht"]})
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME)
    assert (b["pfad"], b["code"]) == ("punkte[0].konfigurationen[0]", BESTAND_REFERENZ)


# --- gleichung ---

def test_gleichung_variable_alt_und_referenz():
    ok = punkte({"id": "g1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110,
                 "folgen": ["D1@Skizze1", "D3@Skizze2"]})
    assert befunde_gegen_aufnahme(ok, AUFNAHME) == []
    ok["punkte"][0]["alt"] = 99
    assert codes(befunde_gegen_aufnahme(ok, AUFNAHME)) == [BESTAND_ALTWERT]
    ok["punkte"][0].update(alt=100, variable="Z")
    assert [(b["pfad"], b["code"]) for b in befunde_gegen_aufnahme(ok, AUFNAHME)] == [("punkte[0].variable", BESTAND_REFERENZ)]


def test_gleichung_links_alt_ist_die_rechte_seite():
    ok = punkte({"id": "g1", "typ": "gleichung", "gleichung": "D3@Skizze2", "alt": '"D1@Skizze1"+5',
                 "neu": '"D1@Skizze1" + 6'})
    assert befunde_gegen_aufnahme(ok, AUFNAHME) == []
    ok["punkte"][0]["alt"] = '"D1@Skizze1" + 4'
    (b,) = befunde_gegen_aufnahme(ok, AUFNAHME)
    assert (b["pfad"], b["code"]) == ("punkte[0].alt", BESTAND_ALTWERT) and '"D1@Skizze1" + 5' in b["meldung"]
    ok["punkte"][0]["gleichung"] = "D9@Weg"
    assert [(b["pfad"], b["code"]) for b in befunde_gegen_aufnahme(ok, AUFNAHME)] == [("punkte[0].gleichung", BESTAND_REFERENZ)]


# --- folgen ---

def test_folgen_abweichend():
    zu_wenig = punkte({"id": "m1", "typ": "mass", "mass": "D1@S5", "alt": 8, "neu": 9})
    (b,) = befunde_gegen_aufnahme(zu_wenig, AUFNAHME)
    assert (b["pfad"], b["code"]) == ("punkte[0].folgen", FOLGEN_ABWEICHEND) and "D2@S6" in b["meldung"]
    zu_viel = punkte({"id": "m1", "typ": "mass", "mass": "D1@S5", "alt": 8, "neu": 9, "folgen": ["D2@S6", "D2@Skizze4"]})
    (b,) = befunde_gegen_aufnahme(zu_viel, AUFNAHME)
    assert b["code"] == FOLGEN_ABWEICHEND and "D2@Skizze4" in b["meldung"]
    stimmt = punkte({"id": "m1", "typ": "mass", "mass": "D1@S5", "alt": 8, "neu": 9, "folgen": ["D2@S6"]})
    assert befunde_gegen_aufnahme(stimmt, AUFNAHME) == []


def test_folgen_bei_variable_unvollstaendig():
    spec = punkte({"id": "g1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110, "folgen": ["D1@Skizze1"]})
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME)
    assert b["code"] == FOLGEN_ABWEICHEND and "D3@Skizze2" in b["meldung"]


def test_getriebene_nie_in_folgen():
    spec = punkte({"id": "m1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45, "folgen": ["D7@Skizze9"]})
    assert codes(befunde_gegen_aufnahme(spec, AUFNAHME)) == [FOLGEN_ABWEICHEND]


def test_folgen_an_punkt_ohne_folgen_sind_zu_viel():
    spec = punkte({"id": "u1", "typ": "unterdruecken", "feature": "Fase3", "folgen": ["D2@S6"]})
    assert codes(befunde_gegen_aufnahme(spec, AUFNAHME)) == [FOLGEN_ABWEICHEND]


# --- feature-Punkte, loeschen, unterdruecken ---

def test_unbekanntes_feature_bei_unterdruecken_aufheben_loeschen():
    for typ in ("unterdruecken", "aufheben", "loeschen"):
        spec = punkte({"id": "u1", "typ": typ, "feature": "Fase9"})
        assert [(b["pfad"], b["code"]) for b in befunde_gegen_aufnahme(spec, AUFNAHME)] == \
            [("punkte[0].feature", BESTAND_REFERENZ)]


def test_loeschen_ohne_kinder():
    spec = punkte({"id": "l1", "typ": "loeschen", "feature": "Bohrung2"})
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME)
    assert (b["pfad"], b["code"]) == ("punkte[0].kinder", KINDER_FEHLEN)
    assert "Fase3" in b["meldung"] and "Verrundung1" in b["meldung"]
    spec["punkte"][0]["kinder"] = ["Fase3"]
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME)
    assert b["code"] == KINDER_FEHLEN and "Verrundung1" in b["meldung"] and "Fase3" not in b["meldung"]
    spec["punkte"][0]["kinder"] = ["Fase3", "Verrundung1"]
    assert befunde_gegen_aufnahme(spec, AUFNAHME) == []


def test_loeschen_blatt_braucht_keine_kinder():
    assert befunde_gegen_aufnahme(punkte({"id": "l1", "typ": "loeschen", "feature": "Verrundung1"}), AUFNAHME) == []


def test_loeschen_unbekanntes_kind():
    spec = punkte({"id": "l1", "typ": "loeschen", "feature": "Verrundung1", "kinder": ["Nichts"]})
    assert [(b["pfad"], b["code"]) for b in befunde_gegen_aufnahme(spec, AUFNAHME)] == \
        [("punkte[0].kinder[0]", BESTAND_REFERENZ)]


def _mit_gleichung(links: str) -> dict:
    gleichungen = [*AUFNAHME["gleichungen"], {"index": 3, "text": f'"{links}" = "suppressed"', "links": links, "global": False}]
    return aufnahme(gleichungen=gleichungen)


@pytest.mark.parametrize("typ", ["unterdruecken", "aufheben"])
@pytest.mark.parametrize("links", ["Fase3", "fase3", "Fase3@Lagerdeckel.Part"])
def test_gleichung_steuert_die_unterdrueckung(typ, links):
    """Sonst nähme der nächste Neuaufbau den Punkt zurück; `validieren` sagt es vor dem Bau, an der Quelle."""
    (b,) = befunde_gegen_aufnahme(punkte({"id": "u1", "typ": typ, "feature": "Fase3"}), _mit_gleichung(links))
    assert (b["pfad"], b["code"]) == ("punkte[0].feature", MASS_GESTEUERT) and "Gleichung" in b["meldung"]
    assert '"suppressed"' in b["meldung"] and "Nutzer" in b["meldung"]
    # Kein Punkt-Weg in Etappe 1: Ein gleichung-Punkt endete im Mangel `konfigurationen`, den kein Nachbessern behebt
    assert "nicht über einen gleichung- oder skript-Punkt" in b["meldung"]


def test_gleichung_rechts_steuert_die_unterdrueckung_nicht():
    a = aufnahme(gleichungen=[*AUFNAHME["gleichungen"], {"index": 3, "text": '"Fase4" = "Fase3"', "links": "Fase4", "global": False}])
    assert befunde_gegen_aufnahme(punkte({"id": "u1", "typ": "unterdruecken", "feature": "Fase3"}), a) == []


def test_gleichung_sperrt_loeschen_nicht():
    spec = punkte({"id": "u1", "typ": "loeschen", "feature": "Fase3", "kinder": ["Verrundung1"]})
    assert befunde_gegen_aufnahme(spec, _mit_gleichung("Fase3")) == []


def test_tabelle_sperrt_unterdruecken():
    a = aufnahme(tabelle=True)  # unabhängig vom Feature: tabellengesteuerte Unterdrückung ist ohne Excel nicht lesbar
    for typ in ("unterdruecken", "aufheben"):
        spec = punkte({"id": "u1", "typ": typ, "feature": "Fase3"})
        assert befunde_gegen_aufnahme(spec, AUFNAHME) == []
        (b,) = befunde_gegen_aufnahme(spec, a)
        assert (b["pfad"], b["code"]) == ("punkte[0].feature", MASS_GESTEUERT) and "Konstruktionstabelle" in b["meldung"]
    assert befunde_gegen_aufnahme(punkte({"id": "l1", "typ": "loeschen", "feature": "Verrundung1"}), a) == []


def test_feature_mit_tabellenmerkmal_sperrt_unterdruecken():
    a = aufnahme()
    a["features"][4]["tabelle"] = True
    spec = punkte({"id": "u1", "typ": "unterdruecken", "feature": "Fase3"})
    assert codes(befunde_gegen_aufnahme(spec, a)) == [MASS_GESTEUERT]


def test_eigenschaft_unbekannte_konfiguration():
    spec = punkte({"id": "e1", "typ": "eigenschaft", "name": "Revision", "neu": "B", "konfiguration": "Gibt es nicht"})
    assert [(b["pfad"], b["code"]) for b in befunde_gegen_aufnahme(spec, AUFNAHME)] == \
        [("punkte[0].konfiguration", BESTAND_REFERENZ)]


def test_feature_nach_unbekannt():
    spec = punkte({"id": "f1", "typ": "feature", "name": "Neu", "nach": "Fase9",
                   "feature": {"typ": "fase", "kanten": [{"nahe": [0, 0, 0]}], "abstand": 1}})
    assert [(b["pfad"], b["code"]) for b in befunde_gegen_aufnahme(spec, AUFNAHME)] == \
        [("punkte[0].nach", BESTAND_REFERENZ)]


# --- Bereiche ---

def test_bereich_fehlt_nur_bei_geometrie():
    ohne = punkte({"id": "p4", "typ": "material", "neu": "1.4301"}, {"id": "p5", "typ": "eigenschaft", "name": "R", "neu": "B"},
                  bereich=False)
    assert befunde_gegen_aufnahme(ohne, AUFNAHME) == []
    for p in (BASIS["punkte"][0], BASIS["punkte"][1], BASIS["punkte"][2], BASIS["punkte"][5],
              {"id": "l1", "typ": "loeschen", "feature": "Verrundung1"},
              {"id": "a1", "typ": "aufheben", "feature": "Fase3"},
              {"id": "g1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110, "folgen": ["D1@Skizze1", "D3@Skizze2"]}):
        spec = punkte(copy.deepcopy(p), bereich=False)
        spec["bereiche"] = [{"punkte": ["p4"], "features": ["Fase3"]}]  # anderer Punkt: deckt p nicht
        befunde = [b for b in befunde_gegen_aufnahme(spec, AUFNAHME) if b.get("code") == BEREICH_FEHLT]
        assert [b["pfad"] for b in befunde] == ["punkte[0]"], p["id"]


def test_bereich_nennt_unbekannten_punkt():
    spec = copy.deepcopy(BASIS)
    spec["bereiche"][1]["punkte"].append("p9")
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME)
    assert b["pfad"] == "bereiche[1].punkte[1]" and "p9" in b["meldung"]


def test_bereich_nennt_unbekanntes_feature():
    spec = copy.deepcopy(BASIS)
    spec["bereiche"][1]["features"] = ["Fase3", "Fase9", "Gewinde M6 Deckel"]  # Fase9 gibt es nicht, das neue Feature schon
    assert [(b["pfad"], b["code"]) for b in befunde_gegen_aufnahme(spec, AUFNAHME)] == \
        [("bereiche[1].features[1]", BESTAND_REFERENZ)]


# --- id, Pfade, Messpunkte ---

def test_id_darf_kein_featurename_sein():
    spec = punkte({"id": "Fase3", "typ": "material", "neu": "1.4301"}, bereich=False)
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME)
    assert b["pfad"] == "punkte[0].id" and "Fase3" in b["meldung"]


def test_bestand_datei_passt_zur_aufnahme_und_ist_relativ():
    spec = copy.deepcopy(BASIS)
    spec["bestand"]["datei"] = "Anders.SLDPRT"
    assert [(b["pfad"], b["code"]) for b in befunde_gegen_aufnahme(spec, AUFNAHME)] == [("bestand.datei", BESTAND_REFERENZ)]
    spec["bestand"]["datei"] = "lagerdeckel.sldprt"  # Groß-/Kleinschreibung zählt nicht
    assert befunde_gegen_aufnahme(spec, AUFNAHME) == []
    for datei in ("../Lagerdeckel.SLDPRT", "C:\\Kunde\\Lagerdeckel.SLDPRT", "/x/Lagerdeckel.SLDPRT", "a\\..\\b.SLDPRT"):
        spec["bestand"]["datei"] = datei
        befunde = [b for b in befunde_gegen_aufnahme(spec, AUFNAHME) if "relativ" in b["meldung"]]
        assert [(b["pfad"], b["code"]) for b in befunde] == [("bestand.datei", BESTAND_REFERENZ)], datei


def test_skript_datei_bleibt_im_auftragsordner():
    for datei in ("../p6.py", "/etc/p6.py", "C:\\p6.py", "skripte\\..\\..\\p6.py"):
        spec = copy.deepcopy(BASIS)
        spec["punkte"][5]["datei"] = datei
        befunde = befunde_gegen_aufnahme(spec, AUFNAHME)
        assert [b["pfad"] for b in befunde] == ["punkte[5].datei"], datei


def test_skript_datei_fehlt(tmp_path):
    spec = copy.deepcopy(BASIS)
    assert befunde_gegen_aufnahme(spec, AUFNAHME) == []  # ohne Ordner wird nur der Pfad geprüft
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME, tmp_path)
    assert b["pfad"] == "punkte[5].datei" and "fehlt" in b["meldung"]
    skript = tmp_path / "skripte" / "p6_endbedingung.py"
    skript.parent.mkdir()
    skript.write_text("import os\ndef bauen(ctx):\n    pass\n", encoding="utf-8")
    (b,) = befunde_gegen_aufnahme(spec, AUFNAHME, tmp_path)
    assert b["pfad"] == "punkte[5].datei" and "Zeile 1" in b["meldung"] and "'os'" in b["meldung"]
    skript.write_text("def bauen(ctx):\n    pass\n", encoding="utf-8")
    assert befunde_gegen_aufnahme(spec, AUFNAHME, tmp_path) == []


def test_pruefung_nennt_unbekanntes_feature():
    spec = copy.deepcopy(BASIS)
    spec["pruefung"]["masse_pruefen"][0]["von"] = {"feature": "Fase9", "flaeche": "+z"}
    spec["pruefung"]["masse_pruefen"][0]["zu"] = {"feature": "Fase3", "flaeche": "+z"}
    assert [(b["pfad"], b["code"]) for b in befunde_gegen_aufnahme(spec, AUFNAHME)] == \
        [("pruefung.masse_pruefen[0].von.feature", BESTAND_REFERENZ)]


def test_pruefung_darf_neues_feature_nennen():
    spec = copy.deepcopy(BASIS)
    spec["pruefung"]["masse_pruefen"][0]["von"] = {"feature": "p3", "flaeche": "+z"}
    assert befunde_gegen_aufnahme(spec, AUFNAHME) == []


# --- feature-Punkte wie in einer Teil-Spec ---

def test_feature_punkt_wie_teil(tmp_path):
    spec = copy.deepcopy(BASIS)
    spec["punkte"][2]["feature"]["groesse"] = "M7"
    befunde, hinweise = feature_befunde(spec, AUFNAHME, tmp_path)
    assert [b["pfad"] for b in befunde] == ["punkte[2].feature.groesse"] and "M7" in befunde[0]["meldung"]
    assert hinweise == []


def test_feature_punkt_schema_befund_am_punkt_pfad(tmp_path):
    spec = copy.deepcopy(BASIS)
    del spec["punkte"][2]["feature"]["positionen"]
    befunde, _ = feature_befunde(spec, AUFNAHME, tmp_path)
    assert [b["pfad"] for b in befunde] == ["punkte[2].feature"]


def test_feature_punkt_verbietet_inneres_skript(tmp_path):
    """Review: Der Teil-Handler nennt die Rückgabe nach der ID, ein fremdes Feature wäre umbenannt. Notausgang ist der Punkt."""
    (tmp_path / "s.py").write_text("def bauen(ctx):\n    pass\n", encoding="utf-8")
    spec = copy.deepcopy(BASIS)
    spec["punkte"][2]["feature"] = {"typ": "skript", "datei": "s.py", "luecke": "x"}
    befunde, _ = feature_befunde(spec, AUFNAHME, tmp_path)
    treffer = [b for b in befunde if b["pfad"] == "punkte[2].feature.typ"]
    assert len(treffer) == 1 and "Punkt" in treffer[0]["meldung"] and "skript" in treffer[0]["meldung"]


def test_feature_punkt_ohne_features_hat_keine_befunde(tmp_path):
    assert feature_befunde(punkte({"id": "m", "typ": "material", "neu": "x"}), AUFNAHME, tmp_path) == ([], [])


def test_feature_verweist_auf_fremdes_feature(tmp_path):
    fase = {"id": "f1", "typ": "feature", "name": "Neue Fase",
            "feature": {"typ": "fase", "kanten": [{"feature": "Schnitt-Linear1", "auswahl": "alle_kanten"}], "abstand": 1}}
    bohrung = {"id": "f2", "typ": "feature", "name": "Neue Bohrung",
               "feature": {"typ": "bohrung", "flaeche": {"feature": "Schnitt-Linear1", "flaeche": "+y"},
                           "durchmesser": 4, "tiefe": 5, "positionen": [[0, 0]]}}
    spec = punkte(fase, bohrung)
    assert feature_befunde(spec, AUFNAHME, tmp_path)[0] == []
    spec["punkte"][1]["feature"]["flaeche"]["feature"] = "Schnitt-Linear9"
    spec["punkte"][0]["feature"]["kanten"][0]["feature"] = "Schnitt-Linear9"
    befunde, _ = feature_befunde(spec, AUFNAHME, tmp_path)
    assert [(b["pfad"], b["code"]) for b in befunde] == [
        ("punkte[0].feature.kanten[0].feature", BESTAND_REFERENZ), ("punkte[1].feature.flaeche.feature", BESTAND_REFERENZ)]


def test_feature_punkt_darf_frueheren_punkt_nennen_aber_nicht_spaeteren(tmp_path):
    erst = {"id": "f1", "typ": "feature", "name": "Neue Fase",
            "feature": {"typ": "fase", "kanten": [{"feature": "f2", "auswahl": "alle_kanten"}], "abstand": 1}}
    zweit = {"id": "f2", "typ": "feature", "name": "Neue Bohrung",
             "feature": {"typ": "bohrung", "flaeche": {"feature": "Schnitt-Linear1", "flaeche": "+y"},
                         "durchmesser": 4, "tiefe": 5, "positionen": [[0, 0]]}}
    befunde, _ = feature_befunde(punkte(erst, zweit), AUFNAHME, tmp_path)
    assert [b["pfad"] for b in befunde] == ["punkte[0].feature.kanten[0].feature"]
    assert feature_befunde(punkte(zweit, {**erst, "id": "f3"}), AUFNAHME, tmp_path)[0] == []  # f2 steht hier vorn


def test_hinweise_der_feature_punkte(tmp_path):
    spec = copy.deepcopy(BASIS)
    _, hinweise = feature_befunde(spec, AUFNAHME, tmp_path)
    assert hinweise and all(h["pfad"].startswith("punkte[2].feature") for h in hinweise)
    assert {h["art"] for h in hinweise} <= {"feste_zahl", "bezug", "zusammenfassen"}


# --- validieren ---

@pytest.fixture
def umg(tmp_path, monkeypatch):
    """Arbeitsordner mit Aufnahme 1 des Auftrags `a1`; die Spec liegt in tmp_path/a1/."""
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    monkeypatch.setattr("swki.bestand.spec.lade_rechner", lambda: r)
    schreibe_aufnahme(r, "a1", 1, AUFNAHME)
    ordner = tmp_path / "a1"
    (ordner / "skripte").mkdir(parents=True)
    (ordner / "skripte" / "p6_endbedingung.py").write_text("def bauen(ctx):\n    pass\n", encoding="utf-8")
    return type("Umgebung", (), {"r": r, "ordner": ordner})


def _schreibe(umg, spec, name="aenderung.yaml") -> Path:
    pfad = umg.ordner / name
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def test_validieren_gibt_alles_aus(umg):
    erg = validieren(_schreibe(umg, BASIS))
    assert erg["gueltig"] is True and erg["art"] == "aenderung" and erg["name"] == "Lagerdeckel_Rev"
    assert erg["punkte"] == 6 and erg["pruefsumme"] == pruefsumme(BASIS)
    assert erg["version_aelter"] is False
    assert erg["folgen"] == {"p1": []}
    assert {h["art"] for h in erg["hinweise"]} <= {"feste_zahl", "bezug", "zusammenfassen"}
    assert all(h["pfad"].startswith("punkte[2].feature") for h in erg["hinweise"])


def test_validieren_nennt_erwartete_folgen(umg):
    spec = punkte({"id": "g1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110,
                   "folgen": ["D1@Skizze1", "D3@Skizze2"]},
                  {"id": "m1", "typ": "mass", "mass": "D1@S5", "alt": 8, "neu": 9, "folgen": ["D2@S6"]})
    assert validieren(_schreibe(umg, spec))["folgen"] == {"g1": ["D1@Skizze1", "D3@Skizze2"], "m1": ["D2@S6"]}


def test_validieren_sammelt_alle_befunde(umg):
    spec = copy.deepcopy(BASIS)
    spec["punkte"][0]["alt"] = 41
    spec["punkte"][1]["feature"] = "Fase9"
    spec["punkte"][2]["feature"]["groesse"] = "M7"
    spec["punkte"][5]["datei"] = "skripte/gibt_es_nicht.py"
    with pytest.raises(SpecFehler) as e:
        validieren(_schreibe(umg, spec))
    assert sorted(b["pfad"] for b in e.value.daten["befunde"]) == [
        "punkte[0].alt", "punkte[1].feature", "punkte[2].feature.groesse", "punkte[5].datei"]


def test_validieren_schema_befund_kommt_vor_der_aufnahme(umg):
    spec = copy.deepcopy(BASIS)
    del spec["punkte"][0]["alt"]
    with pytest.raises(SpecFehler):
        validieren(_schreibe(umg, spec))


def test_aufnahme_unbekannt(umg):
    spec = copy.deepcopy(BASIS)
    spec["bestand"]["aufnahme"] = 2
    with pytest.raises(BestandFehler) as e:
        validieren(_schreibe(umg, spec))
    assert e.value.daten["code"] == BESTAND_UNBEKANNT


def test_aufnahme_passt_nicht_zur_sha256(umg):
    spec = copy.deepcopy(BASIS)
    spec["bestand"]["sha256"] = "0" * 64
    with pytest.raises(BestandFehler) as e:
        validieren(_schreibe(umg, spec))
    assert e.value.daten["code"] == BESTAND_UNBEKANNT and "sha256" in str(e.value)


def test_aufnahme_veraltet(umg):
    schreibe_aufnahme(umg.r, "a1", 2, aufnahme(datei={**AUFNAHME["datei"], "sha256": "0" * 64}))
    with pytest.raises(BestandFehler) as e:
        validieren(_schreibe(umg, BASIS))
    assert e.value.daten["code"] == BESTAND_VERALTET and e.value.daten["neuere"] == [2]
    spec = copy.deepcopy(BASIS)
    spec["bestand"].update(sha256="0" * 64, aufnahme=2)
    assert validieren(_schreibe(umg, spec))["gueltig"] is True  # die neueste Aufnahme gilt


def test_version_aelter_ist_hinweis(umg):
    schreibe_aufnahme(umg.r, "a1", 1, aufnahme(datei={**AUFNAHME["datei"], "version_aelter": True}))
    erg = validieren(_schreibe(umg, BASIS))
    assert erg["gueltig"] is True and erg["version_aelter"] is True
    (h,) = [h for h in erg["hinweise"] if h["art"] == "version_aelter"]
    assert "--hochstufen" in h["meldung"]


# --- freigeben: dieselbe Prüfung, sonst liefe die Spec am Weg `swki freigeben`, `swki bauen --hochstufen` ungeprüft durch ---

def test_freigabe_weiche_legt_kopie_an(umg, capsys):
    pfad = _schreibe(umg, BASIS)
    assert main(["freigeben", str(pfad)]) == 0
    erg = json.loads(capsys.readouterr().out)
    assert erg["art"] == "aenderung" and erg["pruefsumme"] == pruefsumme(BASIS)
    assert (umg.ordner / "aenderung.freigegeben.yaml").is_file()
    eintrag = json.loads((umg.ordner / "freigabe.json").read_text(encoding="utf-8"))["aenderung.yaml"]
    assert eintrag["pruefsumme"] == pruefsumme(BASIS)
    assert pruefe_freigabe(pfad, BASIS) == eintrag


def test_nach_der_freigabe_aendert_bauweg_nichts_anforderung_schon(umg):
    pfad = _schreibe(umg, BASIS)
    freigeben(pfad)
    bauweg = copy.deepcopy(BASIS)
    bauweg["punkte"][2]["feature"].update(bezug={"u": "+rand", "v": "mitte"}, flaeche={"nahe": [1, 30, 20]})
    pruefe_freigabe(pfad, bauweg)  # Bauweg geändert: keine Ausnahme
    anders = copy.deepcopy(BASIS)
    anders["bestand"]["sha256"] = "0" * 64
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(pfad, anders)
    assert e.value.daten["code"] == "FREIGABE_VERALTET"


def test_freigeben_weist_gleichung_in_zoll_datei_ab(umg):
    """Der Bau setzte `neu` sonst als Zoll."""
    schreibe_aufnahme(umg.r, "a1", 1, aufnahme(einheitensystem=3))
    pfad = _schreibe(umg, punkte({"id": "g1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110,
                                  "folgen": ["D1@Skizze1", "D3@Skizze2"]}))
    with pytest.raises(SpecFehler) as e:
        freigeben(pfad)
    assert codes(e.value.daten["befunde"]) == [BESTAND_EINHEIT]
    assert not (umg.ordner / "freigabe.json").exists() and not (umg.ordner / "aenderung.freigegeben.yaml").exists()


def test_freigeben_weist_gesteuerte_unterdrueckung_ab(umg):
    schreibe_aufnahme(umg.r, "a1", 1, _mit_gleichung("Fase3"))
    with pytest.raises(SpecFehler) as e:
        freigeben(_schreibe(umg, punkte({"id": "u1", "typ": "aufheben", "feature": "Fase3"})))
    assert codes(e.value.daten["befunde"]) == [MASS_GESTEUERT]


def test_freigeben_prueft_auch_neue_features(umg):
    spec = copy.deepcopy(BASIS)
    spec["punkte"][2]["feature"]["groesse"] = "M999"
    with pytest.raises(SpecFehler):
        freigeben(_schreibe(umg, spec))
    assert not (umg.ordner / "freigabe.json").exists()


def test_freigeben_auf_veralteter_aufnahme(umg):
    schreibe_aufnahme(umg.r, "a1", 2, aufnahme(datei={**AUFNAHME["datei"], "sha256": "0" * 64}))
    with pytest.raises(BestandFehler) as e:
        freigeben(_schreibe(umg, BASIS))
    assert e.value.daten["code"] == BESTAND_VERALTET and not (umg.ordner / "freigabe.json").exists()


def test_validieren_weiche(umg, capsys):
    pfad = _schreibe(umg, BASIS)
    assert main(["validieren", str(pfad)]) == 0
    erg = json.loads(capsys.readouterr().out)
    assert erg["gueltig"] is True and erg["art"] == "aenderung" and erg["folgen"] == {"p1": []}


def test_validieren_weiche_meldet_befunde(umg, capsys):
    spec = copy.deepcopy(BASIS)
    spec["punkte"][0]["alt"] = 41
    assert main(["validieren", str(_schreibe(umg, spec))]) == 1
    (b,) = json.loads(capsys.readouterr().out)["befunde"]
    assert (b["pfad"], b["code"]) == ("punkte[0].alt", BESTAND_ALTWERT)


def test_validieren_weiche_meldet_veraltete_aufnahme(umg, capsys):
    schreibe_aufnahme(umg.r, "a1", 2, aufnahme(datei={**AUFNAHME["datei"], "sha256": "0" * 64}))
    assert main(["validieren", str(_schreibe(umg, BASIS))]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == BESTAND_VERALTET
