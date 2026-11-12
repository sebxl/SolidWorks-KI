"""Änderungs-Spec für Baugruppen: Schema, Laden, Prüfsumme (Plan Etappe 2 Task 3, Spec Bestandsdateien §4.1, §4.5)."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from swki.bestand.ablage import schreibe_aufnahme
from swki.bestand.spec import (BAUGRUPPEN_TYPEN, _summen, _teil_specs, freigeben, lade_aenderung, pruefe_freigabe_aenderung,
                               teil_summen_aenderung, validieren)
from swki.cli import main
from swki.konfig import Rechner
from swki.spec.freigabe import FreigabeFehler, pruefsumme
from swki.spec.freigabe import freigeben as spec_freigeben
from swki.spec.laden import SpecFehler
from tests.bestand.beispiel_baugruppe import baugruppen_aufnahme
from tests.bestand.test_spec import BEISPIEL as TEIL_BEISPIEL

SHA_BG = "5e7d" * 16

# Baugruppe mit jedem Baugruppen-Punkt, dazu Punkte an Teilen der Baugruppe (in_datei) und an der Hauptdatei
BAUGRUPPE = {
    "art": "aenderung",
    "name": "Haupt_Rev",
    "bestand": {"datei": "Haupt.SLDASM", "sha256": SHA_BG, "aufnahme": 1},
    "parameter": {"ABSTAND_NEU": 12, "T_NEU": 9},
    "kollision_erlaubt": [{"paar": ["k1", "Gehaeuse-1"], "grund": "Schraube im Kernloch"}],
    "punkte": [
        {"id": "k1", "was": "Schraube ergänzen", "typ": "komponente_neu", "quelle": {"normteil": "ISO 4762 M6x16"},
         "konfiguration": "Standard", "fixiert": False, "lage_folgen": ["Deckel-1"]},
        {"id": "k2", "typ": "komponente_neu", "wie": "Schraube-1"},
        {"id": "k3", "typ": "komponente_neu", "quelle": {"teil": "Deckel2.yaml"}},
        {"id": "k4", "typ": "komponente_neu", "quelle": {"kaufteil": "Nanotec GPLE60-2S-32"}},
        {"id": "v1", "typ": "verknuepfung_neu", "art": "konzentrisch", "ausrichtung": "gleich",
         "a": {"komponente": "k1", "feature": "f2", "instanz": 1, "achse": True},
         "b": {"komponente": "Gehaeuse-1", "nahe": [0, 0, 10]}},
        {"id": "v2", "typ": "verknuepfung_neu", "art": "abstand", "wert": "=ABSTAND_NEU",
         "a": {"komponente": "k1", "ebene": "oben"}, "b": {"komponente": "Gehaeuse-1", "feature": "f1", "flaeche": "+y"}},
        {"id": "v3", "typ": "verknuepfung_neu", "art": "grenze_abstand", "min": 0, "max": "=ABSTAND_NEU",
         "a": {"komponente": "k2", "referenz": "OBEN"}, "b": {"komponente": "Gehaeuse-1", "gewinde": "g1", "instanz": 2,
                                                              "achse": True}},
        {"id": "w1", "typ": "verknuepfung_wert", "verknuepfung": "Abstand1", "alt": 10, "neu": "=ABSTAND_NEU"},
        {"id": "w2", "typ": "verknuepfung_wert", "verknuepfung": "Grenze_Abstand1", "grenze": "max", "alt": 5, "neu": 6},
        {"id": "e1", "typ": "komponente_entfernen", "komponente": "Deckel-1",
         "verknuepfungen": ["Deckungsgleich3", "Konzentrisch2"]},
        {"id": "e2", "typ": "komponente_ersetzen", "komponente": "Schraube-2", "quelle": {"normteil": "ISO 4762 M8x20"},
         "alle_instanzen": True, "konfiguration": "Standard"},
        {"id": "l1", "typ": "verknuepfung_loeschen", "verknuepfung": "Abstand2"},
        {"id": "t1", "typ": "mass", "in_datei": "Teile/Platte.SLDPRT", "mass": "D1@Skizze1", "alt": 20, "neu": "=T_NEU"},
        {"id": "t2", "typ": "eigenschaft", "in_datei": "Teile/Platte.SLDPRT", "name": "Revision", "neu": "B"},
        {"id": "t3", "typ": "skript", "in_datei": "Teile/Platte.SLDPRT", "datei": "skripte/t3.py", "luecke": "Endbedingung"},
        {"id": "s1", "typ": "skript", "datei": "skripte/s1.py", "luecke": "Haupt-Skript"},
        {"id": "s2", "typ": "eigenschaft", "name": "Revision", "neu": "B"},
    ],
    "bereiche": [
        {"punkte": ["k1", "v1"], "in_datei": "Teile/Platte.SLDPRT", "box": {"min": [0, 0, 0], "max": [10, 10, 10]}},
        {"punkte": ["t1"], "box": {"min": [0, 0, 0], "max": [10, 10, 10]}},
    ],
    "pruefung": {
        "masse_pruefen": [{"was": "Abstand", "in_datei": "Teile/Platte.SLDPRT", "von": {"punkt": [0, 0, 0]},
                           "zu": {"punkt": [0, 0, 12]}, "soll": "=ABSTAND_NEU", "tol": 0.01}],
    },
}

ALT_HASH_LAGERDECKEL = "36909ed1a6ab3c0bf3bbf0e64b6145e1d5f35f1b98277e77c60526746e8c2dd0"  # vor Etappe 2 (Etappe-1-Stand)


def _schreibe(tmp_path, spec, name="aenderung.yaml"):
    pfad = tmp_path / name
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def _befunde(tmp_path, spec) -> list[dict]:
    with pytest.raises(SpecFehler) as e:
        lade_aenderung(_schreibe(tmp_path, spec))
    return e.value.daten["befunde"]


def _punkt(spec, pid) -> dict:
    return next(p for p in spec["punkte"] if p["id"] == pid)


def _mit(pid, **felder):
    spec = copy.deepcopy(BAUGRUPPE)
    _punkt(spec, pid).update(felder)
    return spec


# --- Schema ---

def test_beispiel_baugruppe_ist_gueltig(tmp_path):
    assert lade_aenderung(_schreibe(tmp_path, BAUGRUPPE)) == BAUGRUPPE


def test_baugruppen_typen():
    assert BAUGRUPPEN_TYPEN == frozenset({"komponente_neu", "komponente_entfernen", "komponente_ersetzen", "verknuepfung_neu",
                                          "verknuepfung_wert", "verknuepfung_loeschen"})
    assert {p["typ"] for p in BAUGRUPPE["punkte"]} >= BAUGRUPPEN_TYPEN


def test_wie_und_quelle_schliessen_sich_aus(tmp_path):
    beides = _mit("k1", wie="Schraube-1")
    keines = copy.deepcopy(BAUGRUPPE)
    del _punkt(keines, "k2")["wie"]
    for spec in (beides, keines):
        assert any(b["pfad"].startswith("punkte[") for b in _befunde(tmp_path, spec))


def test_quelle_wie_im_baugruppen_schema(tmp_path):
    for quelle in ({"teil": "Ordner/Deckel.yaml"}, {"normteil": "M6"}, {"kaufteil": "Nanotec"}, {"normteil": "ISO 4762 M6", "x": 1},
                   {"teil": "a.yaml", "normteil": "ISO 4762 M6"}):
        assert _befunde(tmp_path, _mit("k1", quelle=quelle))
    lade_aenderung(_schreibe(tmp_path, _mit("k1", quelle={"normteil": "ISO 4762 M6", "variante": "kurz"})))


def test_grenze_nur_min_oder_max(tmp_path):
    for grenze in ("mitte", ["min", "max"], "MIN"):
        assert _befunde(tmp_path, _mit("w2", grenze=grenze))
    lade_aenderung(_schreibe(tmp_path, _mit("w2", grenze="min")))


def test_art_der_verknuepfung_wie_in_der_baugruppen_spec(tmp_path):
    for art in ("deckungsgleich", "konzentrisch", "parallel", "senkrecht", "abstand", "winkel", "grenze_abstand", "grenze_winkel",
                "scharnier", "zahnrad", "zahnstange"):
        lade_aenderung(_schreibe(tmp_path, _mit("v1", art=art)))
    assert _befunde(tmp_path, _mit("v1", art="fest"))


@pytest.mark.parametrize("anker", [
    {"komponente": "K"}, {"nahe": [0, 0, 0]}, {"komponente": "K", "nahe": [0, 0]}, {"komponente": "K", "flaeche": "+y"},
    {"komponente": "K", "feature": "f", "flaeche": "oben"}, {"komponente": "K", "gewinde": "g", "achse": True},
    {"komponente": "K", "nahe": [0, 0, 0], "ebene": "oben"}, {"komponente": "K", "ebene": "unten"}])
def test_ungueltiger_anker_ist_befund(tmp_path, anker):
    assert _befunde(tmp_path, _mit("v1", a=anker))


@pytest.mark.parametrize("anker", [
    {"komponente": "K", "nahe": [0, "=A", 0]}, {"komponente": "K", "feature": "f"}, {"komponente": "K", "referenz": "R"},
    {"komponente": "K", "feature": "f", "flaeche": "+x"}, {"komponente": "K", "feature": "f", "instanz": "je", "flaeche": "-z"},
    {"komponente": "K", "feature": "f", "instanz": 2, "achse": True}, {"komponente": "K", "ebene": "rechts"},
    {"komponente": "K", "gewinde": "g", "instanz": 1, "achse": True}])
def test_anker_formen_der_baugruppen_spec(tmp_path, anker):
    spec = _mit("v1", a=anker)
    spec["parameter"]["A"] = 1
    lade_aenderung(_schreibe(tmp_path, spec))


@pytest.mark.parametrize("pid", ["k1", "e1", "e2", "v1", "w1", "l1"])
def test_in_datei_an_baugruppen_punkten_verboten(tmp_path, pid):
    assert _befunde(tmp_path, _mit(pid, in_datei="Teile/Platte.SLDPRT"))


def test_in_datei_an_allen_teil_typen_und_skript_erlaubt(tmp_path):
    spec = copy.deepcopy(TEIL_BEISPIEL)
    spec["punkte"] += [{"id": "p7", "typ": "gleichung", "variable": "L", "alt": 1, "neu": 2},
                       {"id": "p8", "typ": "aufheben", "feature": "Fase3"},
                       {"id": "p9", "typ": "loeschen", "feature": "Fase4", "kinder": []}]
    for p in spec["punkte"]:
        p["in_datei"] = "Teile/Platte.SLDPRT"
    assert lade_aenderung(_schreibe(tmp_path, spec)) == spec
    assert {p["typ"] for p in spec["punkte"]} >= {"mass", "gleichung", "unterdruecken", "aufheben", "loeschen", "feature",
                                                 "material", "eigenschaft", "skript"}


def test_in_datei_leer_ist_befund(tmp_path):
    assert _befunde(tmp_path, _mit("t1", in_datei=""))


def test_skript_ohne_in_datei_an_baugruppe_ist_haupt_punkt(tmp_path):
    spec = lade_aenderung(_schreibe(tmp_path, BAUGRUPPE))
    assert "in_datei" not in _punkt(spec, "s1") and "in_datei" in _punkt(spec, "t3")


@pytest.mark.parametrize("modell", [BAUGRUPPE, TEIL_BEISPIEL])
def test_lage_folgen_an_allen_punkt_typen(tmp_path, modell):
    spec = copy.deepcopy(modell)
    for p in spec["punkte"]:
        p["lage_folgen"] = ["Deckel-1", "Schraube-2"]
    assert lade_aenderung(_schreibe(tmp_path, spec)) == spec
    assert _befunde(tmp_path, _mit("k1", lage_folgen=["Deckel-1", "Deckel-1"]))  # doppelt
    assert _befunde(tmp_path, _mit("k1", lage_folgen="Deckel-1"))


def test_felder_der_teil_punkte_bleiben_verboten(tmp_path):
    """`a`/`b` gehören nur zu verknuepfung_neu; an anderen Punkten bleiben sie unbekannte Felder."""
    assert _befunde(tmp_path, _mit("t1", a={"komponente": "K", "nahe": [0, 0, 0]}))
    assert _befunde(tmp_path, _mit("l1", wert=3))


def test_kollision_erlaubt_form(tmp_path):
    for kollision in ([{"paar": ["a"], "grund": "x"}], [{"paar": ["a", "b", "c"], "grund": "x"}], [{"paar": ["a", "b"]}],
                      [{"paar": ["a", "b"], "grund": ""}], [{"paar": ["a", "b"], "grund": "x", "extra": 1}], {"paar": ["a", "b"]}):
        assert _befunde(tmp_path, {**BAUGRUPPE, "kollision_erlaubt": kollision})
    lade_aenderung(_schreibe(tmp_path, {**BAUGRUPPE, "kollision_erlaubt": []}))


def test_kollision_erlaubt_auch_an_teil_specs(tmp_path):
    spec = {**TEIL_BEISPIEL, "kollision_erlaubt": [{"paar": ["a", "b"], "grund": "x"}]}
    assert lade_aenderung(_schreibe(tmp_path, spec)) == spec


def test_pflichtfelder_der_baugruppen_punkte(tmp_path):
    for pid, feld in [("k3", "quelle"), ("v1", "art"), ("v1", "a"), ("v1", "b"), ("w1", "verknuepfung"), ("w1", "alt"),
                      ("w1", "neu"), ("e1", "komponente"), ("e1", "verknuepfungen"), ("e2", "komponente"), ("e2", "quelle"),
                      ("l1", "verknuepfung")]:
        spec = copy.deepcopy(BAUGRUPPE)
        del _punkt(spec, pid)[feld]
        assert _befunde(tmp_path, spec), (pid, feld)


def test_bereich_und_pruefung_mit_in_datei(tmp_path):
    lade_aenderung(_schreibe(tmp_path, BAUGRUPPE))  # bereiche[0].in_datei und pruefung.masse_pruefen[0].in_datei stehen darin
    spec = copy.deepcopy(BAUGRUPPE)
    spec["bereiche"][0]["in_datei"] = ""
    assert _befunde(tmp_path, spec)


def test_unbekannter_parameter_in_wert_ist_befund(tmp_path):
    for pid, feld in [("v2", "wert"), ("v3", "max"), ("w1", "neu")]:
        befunde = _befunde(tmp_path, _mit(pid, **{feld: "=NICHT_DA"}))
        assert [b["pfad"] for b in befunde] == [f"punkte[{[p['id'] for p in BAUGRUPPE['punkte']].index(pid)}].{feld}"]


def test_doppelte_id_der_baugruppen_punkte_ist_befund(tmp_path):
    spec = _mit("k2", id="k1")
    assert any("doppelt" in b["meldung"] for b in _befunde(tmp_path, spec))


# --- Prüfsumme: Anforderung vs. Bauweg ---

@pytest.mark.parametrize("feld", ["a", "b"])
def test_anker_einer_verknuepfung_sind_bauweg(feld):
    anders = _mit("v1", **{feld: {"komponente": "Anderes-1", "feature": "f9", "flaeche": "-x"}})
    assert pruefsumme(anders) == pruefsumme(BAUGRUPPE)
    assert pruefsumme(_mit("v3", **{feld: {"komponente": "Anderes-1", "nahe": [1, 2, 3]}})) == pruefsumme(BAUGRUPPE)


def test_a_und_b_fremder_punkte_bleiben_anforderung():
    """`a`/`b` sind nur an verknuepfung_neu Bauweg: Felder gleichen Namens an anderen Punkten (hier erfunden, ein Teil-Feature
    mit Schlüssel a) dürfen in der Prüfsumme nicht wegfallen."""
    a = copy.deepcopy(BAUGRUPPE)
    _punkt(a, "t1")["extra"] = {"a": 1, "b": 2}  # Schema ließe es nicht zu: die Prüfsumme schaut nur auf die Struktur
    b = copy.deepcopy(a)
    _punkt(b, "t1")["extra"] = {"a": 5, "b": 6}
    assert pruefsumme(a) != pruefsumme(b)


def test_anker_der_verknuepfung_andere_felder_bleiben_anforderung():
    assert pruefsumme(_mit("v2", wert=13)) != pruefsumme(BAUGRUPPE)
    assert pruefsumme(_mit("v1", art="parallel")) != pruefsumme(BAUGRUPPE)
    assert pruefsumme(_mit("v1", ausrichtung="entgegengesetzt")) != pruefsumme(BAUGRUPPE)


def _aendere(spec, was):
    if was == "neu":
        _punkt(spec, "w1")["neu"] = "=T_NEU"
    elif was == "alt":
        _punkt(spec, "w1")["alt"] = 11
    elif was == "lage_folgen":
        _punkt(spec, "k1")["lage_folgen"] = ["Deckel-1", "Schraube-2"]
    elif was == "kollision_erlaubt":
        spec["kollision_erlaubt"][0]["grund"] = "etwas anderes"
    elif was == "in_datei":
        _punkt(spec, "t1")["in_datei"] = "Teile/Andere.SLDPRT"
    elif was == "verknuepfungen":
        _punkt(spec, "e1")["verknuepfungen"] = ["Deckungsgleich3"]
    elif was == "quelle":
        _punkt(spec, "k1")["quelle"] = {"normteil": "ISO 4762 M8x16"}
    elif was == "wie":
        _punkt(spec, "k2")["wie"] = "Schraube-2"
    elif was == "komponente":
        _punkt(spec, "e1")["komponente"] = "Deckel-2"
    elif was == "bereich_in_datei":
        spec["bereiche"][0]["in_datei"] = "Teile/Andere.SLDPRT"
    elif was == "pruefung_in_datei":
        spec["pruefung"]["masse_pruefen"][0]["in_datei"] = "Teile/Andere.SLDPRT"
    elif was == "kollision_neu":
        spec["kollision_erlaubt"].append({"paar": ["k2", "Gehaeuse-1"], "grund": "noch eine"})
    elif was == "grenze":
        _punkt(spec, "w2")["grenze"] = "min"
    else:
        raise AssertionError(was)


@pytest.mark.parametrize("aenderung", ["neu", "alt", "lage_folgen", "kollision_erlaubt", "in_datei", "verknuepfungen", "quelle",
                                       "wie", "komponente", "bereich_in_datei", "pruefung_in_datei", "kollision_neu", "grenze"])
def test_anforderung_aendert_pruefsumme(aenderung):
    anders = copy.deepcopy(BAUGRUPPE)
    _aendere(anders, aenderung)
    assert pruefsumme(anders) != pruefsumme(BAUGRUPPE)


def test_reihenfolge_der_baugruppen_punkte_aendert_pruefsumme_nicht():
    umgekehrt = copy.deepcopy(BAUGRUPPE)
    umgekehrt["punkte"].reverse()
    assert pruefsumme(umgekehrt) == pruefsumme(BAUGRUPPE)


def test_skriptdatei_mit_in_datei_ist_weiter_bauweg():
    anders = _mit("t3", datei="skripte/anders.py")
    assert pruefsumme(anders) == pruefsumme(BAUGRUPPE)
    assert pruefsumme(_mit("t3", in_datei="Teile/Andere.SLDPRT")) != pruefsumme(BAUGRUPPE)


def test_spec_ohne_in_datei_bleibt_wie_bisher():
    """Etappe 1: Ohne Baugruppen-Felder und ohne Teil-Quelle ändert sich keine Prüfsumme (Freigaben bleiben gültig)."""
    pfad = Path(__file__).parent.parent / "referenz" / "bestand" / "lagerdeckel_rev.yaml"
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    assert pruefsumme(spec) == ALT_HASH_LAGERDECKEL
    assert pruefsumme(spec, teil_summen_aenderung(spec, pfad)) == ALT_HASH_LAGERDECKEL
    assert teil_summen_aenderung(spec, pfad) is None


# --- Teil-Quellen ---

def _teil(name="Deckel2", hoehe=15):
    return {"art": "teil", "name": name, "material": "1.0038", "parameter": {"L": 100, "B": 60, "H": hoehe},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
                          "ende": {"typ": "blind", "tiefe": "=H"}}],
            "pruefung": {"huellquader": ["=L", "=H", "=B"]}}


@pytest.fixture
def umg(tmp_path, monkeypatch):
    """Arbeitsordner mit der Baugruppen-Aufnahme 1 (`beispiel_baugruppe`) und Auftragsordner a1."""
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    monkeypatch.setattr("swki.bestand.spec.lade_rechner", lambda: r)
    schreibe_aufnahme(r, "a1", 1, baugruppen_aufnahme())
    ordner = tmp_path / "a1"
    ordner.mkdir()
    return type("Umgebung", (), {"r": r, "ordner": ordner})


def _auftrag(umg, spec=None, teil=None):
    """Teil-Spec und Änderungs-Spec (ein komponente_neu aus der Teil-Quelle) im Auftragsordner; Rückgabe: (Spec-Pfad, Spec)."""
    spec = spec or {"art": "aenderung", "name": "Haupt_Rev",
                    "bestand": BAUGRUPPE["bestand"],
                    "punkte": [{"id": "k3", "typ": "komponente_neu", "quelle": {"teil": "Deckel2.yaml"}},
                               {"id": "k4", "typ": "komponente_neu", "quelle": {"teil": "Deckel2.yaml"}},
                               {"id": "v1", "typ": "verknuepfung_neu", "art": "deckungsgleich",
                                "a": {"komponente": "k3", "ebene": "oben"}, "b": {"komponente": "Gehaeuse-1", "ebene": "oben"}}],
                    "bereiche": []}
    _schreibe(umg.ordner, teil or _teil(), "Deckel2.yaml")
    return _schreibe(umg.ordner, spec), spec


def test_teil_summen_je_datei_einmal(umg):
    pfad, spec = _auftrag(umg)
    assert teil_summen_aenderung(spec, pfad) == {"Deckel2.yaml": pruefsumme(_teil())}


def test_teil_summen_ohne_teil_quelle_none(umg):
    pfad, spec = _auftrag(umg, spec={**BAUGRUPPE, "punkte": [_punkt(BAUGRUPPE, "k1"), _punkt(BAUGRUPPE, "v1")]})
    assert teil_summen_aenderung(spec, pfad) is None


def test_teil_summen_auch_aus_komponente_ersetzen(umg):
    spec = {"art": "aenderung", "name": "H", "bestand": BAUGRUPPE["bestand"], "bereiche": [],
            "punkte": [{"id": "e2", "typ": "komponente_ersetzen", "komponente": "Schraube-2", "quelle": {"teil": "Deckel2.yaml"}}]}
    pfad, spec = _auftrag(umg, spec)
    assert teil_summen_aenderung(spec, pfad) == {"Deckel2.yaml": pruefsumme(_teil())}


def test_fehlende_teil_spec_ist_befund(umg):
    pfad, spec = _auftrag(umg)
    (umg.ordner / "Deckel2.yaml").unlink()
    with pytest.raises(SpecFehler) as e:
        teil_summen_aenderung(spec, pfad)
    assert "Deckel2.yaml" in e.value.daten["befunde"][0]["pfad"]


def test_teil_quelle_geht_in_die_pruefsumme(umg):
    pfad, spec = _auftrag(umg)
    ohne = pruefsumme(spec)
    mit = pruefsumme(spec, teil_summen_aenderung(spec, pfad))
    assert mit != ohne
    andere_teil = pruefsumme(spec, {"Deckel2.yaml": pruefsumme(_teil(hoehe=20))})
    assert andere_teil != mit


def test_validieren_nennt_pruefsumme_mit_teilen(umg):
    pfad, spec = _auftrag(umg)
    assert validieren(pfad)["pruefsumme"] == pruefsumme(spec, {"Deckel2.yaml": pruefsumme(_teil())})


def test_freigabe_legt_teil_und_aenderung_ab(umg):
    pfad, spec = _auftrag(umg)
    erg = freigeben(pfad)
    daten = json.loads((umg.ordner / "freigabe.json").read_text(encoding="utf-8"))
    assert set(daten) == {"aenderung.yaml", "Deckel2.yaml"}
    assert (umg.ordner / "Deckel2.freigegeben.yaml").is_file() and (umg.ordner / "aenderung.freigegeben.yaml").is_file()
    assert daten["aenderung.yaml"]["pruefsumme"] == pruefsumme(spec, {"Deckel2.yaml": pruefsumme(_teil())})
    assert erg["pruefsumme"] == daten["aenderung.yaml"]["pruefsumme"] and set(erg["teile"]) == {"Deckel2.yaml"}
    assert pruefe_freigabe_aenderung(pfad, spec)["pruefsumme"] == erg["pruefsumme"]


def test_freigabe_per_weiche_mit_teil(umg, capsys):
    pfad, _ = _auftrag(umg)
    assert main(["freigeben", str(pfad)]) == 0
    assert json.loads(capsys.readouterr().out)["art"] == "aenderung"
    assert (umg.ordner / "Deckel2.freigegeben.yaml").is_file()


def test_aenderung_der_teil_spec_macht_die_freigabe_veraltet(umg):
    pfad, spec = _auftrag(umg)
    freigeben(pfad)
    _schreibe(umg.ordner, _teil(hoehe=20), "Deckel2.yaml")  # Anforderung (Parameter) der Teil-Spec geändert
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe_aenderung(pfad, spec)
    assert e.value.daten["code"] == "FREIGABE_VERALTET" and "Deckel2.yaml" in str(e.value)


def test_bauweg_der_teil_spec_laesst_die_freigabe_gelten(umg):
    pfad, spec = _auftrag(umg)
    freigeben(pfad)
    teil = _teil()
    teil["max_nachbesserungen"] = 7  # Bauweg der Teil-Spec: nicht in ihrer Prüfsumme
    teil["features"][0]["ende"]["tiefe"] = "=H+0"
    _schreibe(umg.ordner, teil, "Deckel2.yaml")
    pruefe_freigabe_aenderung(pfad, spec)


def test_teil_spec_ohne_freigabe_ist_freigabe_fehlt(umg):
    pfad, spec = _auftrag(umg)
    freigeben(pfad)
    daten = json.loads((umg.ordner / "freigabe.json").read_text(encoding="utf-8"))
    del daten["Deckel2.yaml"]
    (umg.ordner / "freigabe.json").write_text(json.dumps(daten), encoding="utf-8")
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe_aenderung(pfad, spec)
    assert e.value.daten["code"] == "FREIGABE_FEHLT" and "Deckel2.yaml" in str(e.value)


def test_aenderung_der_anforderung_macht_die_freigabe_veraltet(umg):
    pfad, spec = _auftrag(umg)
    freigeben(pfad)
    anders = copy.deepcopy(spec)
    _punkt(anders, "v1")["art"] = "parallel"
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe_aenderung(pfad, anders)
    assert e.value.daten["code"] == "FREIGABE_VERALTET"


def test_freigabe_ohne_teil_quelle_unveraendert(umg):
    """Etappe 1 / reine Baugruppen-Punkte: kein `teile`, Prüfsumme wie `pruefsumme(spec)`, keine Teil-Kopie."""
    spec = {**BAUGRUPPE,
            "punkte": [_punkt(BAUGRUPPE, "k1")], "bereiche": [], "pruefung": {}, "kollision_erlaubt": []}
    pfad, _ = _auftrag(umg, spec)
    erg = freigeben(pfad)
    assert "teile" not in erg and erg["pruefsumme"] == pruefsumme(spec)
    assert not (umg.ordner / "Deckel2.freigegeben.yaml").exists()


def test_anlage_anker_einer_verknuepfung_sind_bauweg():
    """`anlage_a`/`anlage_b` sind Anker wie `a`/`b`: ganz Bauweg, auch wenn sie ganz fehlen."""
    spec = _mit("v1", art="scharnier", anlage_a={"komponente": "k1", "feature": "f2", "flaeche": "+y"},
                anlage_b={"komponente": "Gehaeuse-1", "nahe": [0, 0, 10]})
    anders = _mit("v1", art="scharnier", anlage_a={"komponente": "Anderes-1", "ebene": "oben"},
                  anlage_b={"komponente": "Anderes-2", "referenz": "R"})
    assert pruefsumme(anders) == pruefsumme(spec) == pruefsumme(_mit("v1", art="scharnier"))


# --- Verdrahtung: bauen, prüfen und ausgeben prüfen auch die Freigabe der Teil-Quelle ---

TEIL_PUNKT = {"id": "k3", "typ": "komponente_neu", "quelle": {"teil": "Deckel2.yaml"}}


def schreibe_teil(ordner: Path, hoehe: float = 15) -> None:
    """Die Teil-Spec `Deckel2.yaml` neben der Änderungs-Spec; eine andere Höhe ändert ihre Anforderung (Parameter)."""
    _schreibe(ordner, _teil(hoehe=hoehe), "Deckel2.yaml")


def freigabe_der_teil_quelle(spec_pfad: Path) -> None:
    """Freigabe samt Teil-Quelle wie `swki freigeben`, aber ohne die Prüfung gegen die Aufnahme. Die Bau-, Prüf- und Ausgabetests
    tragen die Teil-Quelle an einer Teil-Aufnahme, die `freigeben` (zu Recht) abweist: Sie belegen nur, dass `bauen`, `pruefen` und
    `ausgabe` die Freigabe der Teil-Quelle prüfen."""
    spec = lade_aenderung(spec_pfad)
    teile = _teil_specs(spec, spec_pfad)
    for datei, teil in teile.items():
        spec_freigeben(spec_pfad.parent / datei, teil)
    spec_freigeben(spec_pfad, spec, teile=_summen(teile))


def test_verknuepfung_wert_traegt_konfigurationen(tmp_path):
    spec = _mit("w1", konfigurationen=["Standard"])
    assert lade_aenderung(_schreibe(tmp_path, spec)) == spec
    assert lade_aenderung(_schreibe(tmp_path, _mit("w1", konfigurationen="alle")))
    assert _befunde(tmp_path, _mit("w1", konfigurationen=[]))  # mindestens eine Konfiguration
    assert _befunde(tmp_path, _mit("w1", konfigurationen="Standard"))  # entweder "alle" oder eine Liste
