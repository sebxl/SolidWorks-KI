"""swki aenderungen über das Maßprotokoll (Spec Bemaßungsbezug §7): einzelne Maße statt globaler Variablen."""

import json
import math

import pytest

from swki import aenderungen
from swki.aenderungen import lies_masse, mass_differenz, soll_masse, vorschlaege
from swki.auftrag import lauf_datei, lauf_ordner
from swki.baugruppe.freigabe import freigeben_baugruppe
from swki.baugruppe.laden import lade_baugruppe
from swki.konfig import lade_standard
from swki.spec.freigabe import freigeben
from tests.baugruppe.beispiel import BAUGRUPPE, schreibe
from tests.spec.beispiel import GUELTIG
from tests.test_aenderungen import _lauf, umgebung  # noqa: F401  (Fixture)


def _m(name, roh, wert, art="groesse", pfad="features[0].profil.laenge", bezug=None, vorzeichen=1):
    return {"name": name, "pfad": pfad, "art": art, "bezug": bezug, "roh": roh, "vorzeichen": vorzeichen, "wert": wert}


def test_mass_differenz_meldet_nur_geaenderte():
    masse = [_m("D1@s", "=L", 100.0), _m("D2@s", "=B", 60.0, pfad="features[0].profil.breite"),
             _m("D3@s", 5, 5.0, art="radius", pfad="features[0].profil.radius")]
    differenz = mass_differenz(masse, {"D1@s": 90.0, "D2@s": 60.0, "D3@s": 5.0000001})
    assert differenz == [{"name": "D1@s", "pfad": "features[0].profil.laenge", "art": "groesse", "bezug": None,
                          "roh": "=L", "soll": 100.0, "ist": 90.0, "delta": -10.0}]


def test_mass_differenz_meldet_fehlendes_mass():
    differenz = mass_differenz([_m("D1@s", "=L", 100.0)], {})
    assert differenz[0]["ist"] is None and differenz[0]["delta"] is None and differenz[0]["soll"] == 100.0


def test_vorschlag_direkter_parameter():
    differenz = mass_differenz([_m("D1@s", "=L", 100.0)], {"D1@s": 90.0})
    assert vorschlaege(differenz, {"L": 100}) == [{"parameter": "L", "neu": 90.0}]


def test_vorschlag_negierter_parameter():
    """Das Maß ist ein Betrag: roh =-P mit Betrag 10 heißt P = -10; ist 12 → P = -12. Leerzeichen sind egal."""
    differenz = mass_differenz([_m("D1@s", " = - P ", 10.0, vorzeichen=-1)], {"D1@s": 12.0})
    assert vorschlaege(differenz, {"P": -10}) == [{"parameter": "P", "neu": -12.0}]


def test_kein_vorschlag_bei_zusammengesetztem_ausdruck_zahl_oder_unbekanntem_parameter():
    masse = [_m("D1@s", "=L/2", 50.0), _m("D2@s", 30, 30.0), _m("D3@s", "=X", 7.0), _m("D4@s", "=L+2", 12.0)]
    differenz = mass_differenz(masse, {"D1@s": 40.0, "D2@s": 31.0, "D3@s": 8.0, "D4@s": 13.0})
    assert len(differenz) == 4
    assert vorschlaege(differenz, {"L": 100}) == []


@pytest.mark.parametrize("art", ["konstruktion", "skript"])
def test_konstruktion_und_skript_nie_als_vorschlag(art):
    """Das Konstruktionsmaß der Symmetrie-Mittellinie trägt einen Lagepfad – nach art trennen, nicht nach pfad."""
    differenz = mass_differenz([_m("D1@s", "=L", 100.0, art=art, pfad="features[0].positionen[0][0]")],
                               {"D1@s": 90.0})
    assert len(differenz) == 1 and vorschlaege(differenz, {"L": 100}) == []


def test_lage_nie_als_parametervorschlag():
    differenz = mass_differenz([_m("D1@s", "=-XG", 10.0, art="lage", pfad="features[1].positionen[0][0]",
                                   vorzeichen=-1)], {"D1@s": 12.0})
    assert vorschlaege(differenz, {"XG": -10}) == [{"pfad": "features[1].positionen[0][0]", "bezug": None, "delta": 2.0}]


def test_vorschlag_lage_mit_bezug_delta():
    differenz = mass_differenz([_m("D1@s", 10, 10.0, art="lage", pfad="features[1].positionen[0][0]", bezug="-rand")],
                               {"D1@s": 12.0})
    assert vorschlaege(differenz, {}) == [{"pfad": "features[1].positionen[0][0]", "bezug": "-rand", "delta": 2.0}]


def test_konflikt_zwei_masse_ein_parameter():
    masse = [_m("D1@s", "=B", 60.0), _m("D2@s", "=B", 60.0, pfad="features[0].profil.hoehe")]
    differenz = mass_differenz(masse, {"D1@s": 65.0, "D2@s": 70.0})
    assert vorschlaege(differenz, {"B": 60}) == [{"parameter": "B", "konflikt": [65.0, 70.0]}]


def test_gleiche_neue_werte_sind_kein_konflikt():
    masse = [_m("D1@s", "=B", 60.0), _m("D2@s", "=B", 60.0, pfad="features[0].profil.hoehe")]
    differenz = mass_differenz(masse, {"D1@s": 65.0, "D2@s": 65.0})
    assert vorschlaege(differenz, {"B": 60}) == [{"parameter": "B", "neu": 65.0}]


def test_lies_masse_in_mm_und_grad():
    class Mass:
        def __init__(self, wert):
            self.SystemValue = wert

    class Modell:
        def __init__(self, werte):
            self.werte = werte

        def Parameter(self, name):
            return Mass(self.werte[name]) if name in self.werte else None

    masse = [_m("D1@s", "=L", 100.0), _m("D2@s", "=W", 30.0, art="winkel"), _m("D3@s", 1, 1.0, art="radius")]
    modell = Modell({"D1@s": 0.09, "D2@s": math.radians(45), "D3@s": 0.001})   # D3 fehlt nicht, D4 schon
    ist = lies_masse(modell, masse + [_m("D4@s", 1, 1.0)])
    assert ist == pytest.approx({"D1@s": 90.0, "D2@s": 45.0, "D3@s": 1.0})


def _protokoll_mit_masse():
    return {"status": "ok", "knoten": [
        {"id": "f1", "masse": [_m("D1@f1_skizze", "=L", 100.0)]},
        {"id": "f2", "masse": None},
        {"id": "f3", "masse": [_m("D1@f3_skizze", "=B", 60.0), _m("D2@f3_skizze", 5, 5.0, art="radius")]}]}


def test_soll_masse_teil(umgebung):
    r, spec_pfad = umgebung
    freigeben(spec_pfad, GUELTIG)
    soll = soll_masse(_protokoll_mit_masse(), spec_pfad, "A", lade_standard())
    assert list(soll) == ["A_Platte_1.sldprt"]
    assert [m["name"] for m in soll["A_Platte_1.sldprt"]] == ["D1@f1_skizze", "D1@f3_skizze", "D2@f3_skizze"]


def test_soll_masse_alter_lauf_ohne_masse_ist_leer(umgebung):
    """Ohne das Feld masse (Lauf vor diesem Paket) braucht soll_masse nicht einmal eine Freigabe."""
    r, spec_pfad = umgebung
    assert soll_masse({"knoten": [{"id": "f1", "typ": "extrusion"}]}, spec_pfad, "A", lade_standard()) == {}
    assert soll_masse({}, spec_pfad, "A", lade_standard()) == {}


def test_soll_masse_baugruppe(tmp_path):
    pfad = schreibe(tmp_path / "A")
    freigeben_baugruppe(lade_baugruppe(pfad))
    teile = {datei: {"knoten": [{"id": "f1", "masse": [_m(f"D1@{datei}", "=L", 10.0)]}]} for datei in
             lade_baugruppe(pfad).teile}
    protokoll = {"knoten": [{"id": "v1", "masse": None}], "teile": teile}
    soll = soll_masse(protokoll, pfad, "A", lade_standard())
    assert soll["A_Probe.sldasm"] == []
    teil_dateien = [n for n in soll if n.endswith(".sldprt")]
    assert len(teil_dateien) == len(teile) and all(len(soll[n]) == 1 for n in teil_dateien)
    # Teilprotokoll ohne masse-Feld (alter Lauf): das Teil bleibt auf dem alten Weg
    teile_alt = {d: ({"knoten": [{"id": "f1"}]} if i == 0 else t) for i, (d, t) in enumerate(teile.items())}
    soll_alt = soll_masse({**protokoll, "teile": teile_alt}, pfad, "A", lade_standard())
    assert len(soll_alt) == len(soll) - 1


def test_alter_lauf_ohne_masse_liest_globale_variablen(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    freigeben(spec_pfad, GUELTIG)
    datei = _lauf(r, spec_pfad, 1)
    datei.write_bytes(b"von Hand geaendert")
    modell = object()
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: "app")
    monkeypatch.setattr(aenderungen, "oeffne", lambda app, pfad: modell)
    monkeypatch.setattr(aenderungen.sw, "schliesse", lambda app, model: None)
    monkeypatch.setattr(aenderungen, "lies_globale_variablen", lambda m: {"L": 120.0})
    monkeypatch.setattr(aenderungen, "lies_masse", lambda *a: pytest.fail("alter Lauf ohne Maßprotokoll"))
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {datei.name: {"L": 100}})
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert ergebnis["geaendert"] == [{"datei": datei.name, "parameter": [{"name": "L", "soll": 100, "ist": 120.0}],
                                      "masse": [], "vorschlaege": []}]


def test_aenderungen_ausgabe_mit_masse_und_vorschlaegen(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    protokoll_pfad = lauf_datei(spec_pfad, 1, "protokoll")
    protokoll = json.loads(protokoll_pfad.read_text(encoding="utf-8"))
    masse = [_m("D1@f1_skizze", "=L", 100.0), _m("D2@f1_skizze", "=-XG", 10.0, art="lage",
                                                  pfad="features[0].positionen[0][0]", vorzeichen=-1),
             _m("D3@f1_skizze", "=B", 60.0, pfad="features[0].profil.breite")]
    protokoll["knoten"] = [{"id": "f1", "masse": masse}]
    protokoll_pfad.write_text(json.dumps(protokoll), encoding="utf-8")
    datei.write_bytes(b"von Hand geaendert")
    geschlossen = []
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: "app")
    monkeypatch.setattr(aenderungen, "oeffne", lambda app, pfad: "modell")
    monkeypatch.setattr(aenderungen.sw, "schliesse", lambda app, model: geschlossen.append(model))
    monkeypatch.setattr(aenderungen, "lies_globale_variablen", lambda m: pytest.fail("Maßweg liest keine Variablen"))
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {datei.name: {"L": 100, "XG": -10, "B": 60}})
    monkeypatch.setattr(aenderungen, "soll_masse", lambda *a: {datei.name: masse})
    monkeypatch.setattr(aenderungen, "lies_masse", lambda model, m: {"D1@f1_skizze": 90.0, "D2@f1_skizze": 12.0,
                                                                     "D3@f1_skizze": 60.0})
    eintrag = aenderungen.aenderungen(spec_pfad)["geaendert"][0]
    assert eintrag["datei"] == datei.name and eintrag["parameter"] == []
    assert [m["name"] for m in eintrag["masse"]] == ["D1@f1_skizze", "D2@f1_skizze"]
    assert eintrag["vorschlaege"] == [{"parameter": "L", "neu": 90.0},
                                      {"pfad": "features[0].positionen[0][0]", "bezug": None, "delta": 2.0}]
    assert "hinweis" not in eintrag and geschlossen == ["modell"]


def test_aenderungen_hinweis_wenn_weder_parameter_noch_masse_abweichen(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    datei.write_bytes(b"von Hand geaendert")
    masse = [_m("D1@f1_skizze", "=L", 100.0)]
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: "app")
    monkeypatch.setattr(aenderungen, "oeffne", lambda app, pfad: "modell")
    monkeypatch.setattr(aenderungen.sw, "schliesse", lambda app, model: None)
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {datei.name: {"L": 100}})
    monkeypatch.setattr(aenderungen, "soll_masse", lambda *a: {datei.name: masse})
    monkeypatch.setattr(aenderungen, "lies_masse", lambda model, m: {"D1@f1_skizze": 100.0})
    eintrag = aenderungen.aenderungen(spec_pfad)["geaendert"][0]
    assert eintrag["masse"] == [] and eintrag["vorschlaege"] == [] and "Parameter gleich" in eintrag["hinweis"]


def test_baugruppendokument_im_massweg_vergleicht_nur_verknuepfungen(umgebung, monkeypatch):
    """Im Maßweg gibt es keine globalen Variablen: Parameter der Baugruppe dürfen nicht als fehlend gemeldet werden,
    die Verknüpfungswerte werden weiter verglichen."""
    from swki.baugruppe import sw_baugruppe

    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    asm = datei.with_name("A_Probe.sldasm")
    asm.write_bytes(b"asm")
    protokoll_pfad = lauf_datei(spec_pfad, 1, "protokoll")
    protokoll = json.loads(protokoll_pfad.read_text(encoding="utf-8"))
    protokoll["sha256"] |= aenderungen.pruefsummen(asm.parent, [asm])
    protokoll_pfad.write_text(json.dumps(protokoll), encoding="utf-8")
    asm.write_bytes(b"asm von Hand")
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: "app")
    monkeypatch.setattr(aenderungen, "oeffne", lambda app, pfad: "modell")
    monkeypatch.setattr(aenderungen.sw, "schliesse", lambda app, model: None)
    monkeypatch.setattr(aenderungen, "lies_globale_variablen", lambda m: pytest.fail("Maßweg liest keine Variablen"))
    monkeypatch.setattr(sw_baugruppe, "verknuepfungswerte", lambda model: {"v1": 7.0})
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {asm.name: {"ABST": 35, "verknuepfung:v1": 5.0}})
    monkeypatch.setattr(aenderungen, "soll_masse", lambda *a: {asm.name: []})
    monkeypatch.setattr(aenderungen, "lies_masse", lambda model, m: {})
    eintrag = aenderungen.aenderungen(spec_pfad)["geaendert"][0]
    assert eintrag["parameter"] == [{"name": "verknuepfung:v1", "soll": 5.0, "ist": 7.0}]
    assert eintrag["masse"] == [] and eintrag["vorschlaege"] == []
