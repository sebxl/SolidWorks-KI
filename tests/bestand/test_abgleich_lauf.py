"""`swki bestand abgleich` und `--referenzbau` (Spec Bestandsdateien §8.5, §8.6; Plan Etappe 2 Task 8), `speichere_an_ort` unter
einem Lauf-Ordner und der Block `baugruppe` in `swki aenderungen`, ohne SolidWorks."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from swki import aenderungen
from swki.bestand import abgleich_lauf, sw_bestand
from swki.bestand.abgleich import ungeprueft_baugruppe
from swki.bestand.ablage import bestand_ordner, schreibe_aufnahme, schreibe_datei_aufnahme, schreibe_herkunft
from swki.bestand.fehler import BESTAND_NICHT_LESBAR, BESTAND_REFERENZ, BESTAND_UNBEKANNT, BestandFehler
from swki.cli import main
from swki.compiler.fehler import SPEICHERN_FEHLGESCHLAGEN, BauFehler
from swki.konfig import Rechner
from tests.bestand.beispiel_aufnahme import AUFNAHME
from tests.bestand.beispiel_baugruppe import baugruppen_aufnahme, teil_aufnahme
from tests.bestand.sw_attrappe import Teil

REL = "teile/Deckel.SLDPRT"
ANDERE = "teile/Platte.SLDPRT"
SPEC_TEIL = {"art": "teil", "name": "Deckel", "parameter": {}, "features": []}


def _gelesen(rel: str) -> dict:
    """Teil-Aufnahme, wie `lies_bestand` sie liefert: mit der Reihenfolge je Konfiguration."""
    a = teil_aufnahme(rel)
    return {**a, "reihenfolge": {k: [f["name"] for f in a["features"]] for k in a["konfigurationen"]}}


def _protokoll(sha_deckel="1" * 64):
    teil = {"knoten": [{"id": "f1", "typ": "extrusion", "sw_name": "f1", "status": "ok", "masse": []}]}
    return {"status": "ok", "sha256": {"Haupt.SLDASM": "5e7d" * 16, "Deckel.SLDPRT": sha_deckel, "Platte.SLDPRT": "2" * 64,
                                       "Stift.step": "3" * 64},
            "komponenten": [{"id": "deckel", "sw_name": "Deckel-1", "datei": "Deckel.SLDPRT"}], "knoten": [],
            "teile": {"deckel.yaml": teil}}


@pytest.fixture
def u(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    spec_pfad = tmp_path / "auftraege" / "alt" / "alt.yaml"
    spec_pfad.parent.mkdir(parents=True)
    spec_pfad.write_text("art: baugruppe\nname: alt\n", encoding="utf-8")
    a = baugruppen_aufnahme()
    a["dateien"] = {REL: {**a["dateien"][REL], "sha256": "1" * 64}, ANDERE: {**a["dateien"][ANDERE], "sha256": "2" * 64}}
    schreibe_aufnahme(r, "neu", 1, a)
    schreibe_datei_aufnahme(r, "neu", 1, REL, _gelesen(REL))
    schreibe_datei_aufnahme(r, "neu", 1, ANDERE, _gelesen(ANDERE))
    (bestand_ordner(r, "neu", 1) / REL).parent.mkdir(parents=True)
    (bestand_ordner(r, "neu", 1) / REL).write_bytes(b"kopie")
    protokolle = spec_pfad.parent / "protokolle"
    protokolle.mkdir()
    (protokolle / "alt.lauf-30.protokoll.json").write_text(json.dumps(_protokoll()), encoding="utf-8")
    monkeypatch.setattr(abgleich_lauf, "lade_rechner", lambda: r)
    monkeypatch.setattr(abgleich_lauf, "verbinde", lambda jahr: pytest.fail("Der Abgleich braucht kein SolidWorks"))
    monkeypatch.setattr(abgleich_lauf, "soll_teile", lambda *x: {"Deckel.SLDPRT": ({"knoten": []}, SPEC_TEIL)})
    monkeypatch.setattr(abgleich_lauf, "soll_verknuepfungen_lauf", lambda spec_pfad, protokoll: {})
    monkeypatch.setattr(abgleich_lauf, "art_der_datei", lambda pfad: "baugruppe")
    schreibe_herkunft(r, "neu", 1, {"auftrag": "alt", "lauf": 30, "spec": "alt.yaml"})
    return SimpleNamespace(r=r, spec_pfad=spec_pfad, aufnahme=a)


def test_abgleich_oeffnet_keinen_lauf_ordner(u):
    """Kein `verbinde`, also kein Dokument; die Attrappe bricht beim ersten Versuch ab. Die Prüfung ist die SHA-256 der
    Aufnahme."""
    lauf = u.r.arbeitsordner / "alt" / "lauf-30"
    aus = abgleich_lauf.abgleich("neu", u.spec_pfad)
    assert not lauf.exists()    # nicht einmal der Ordner wird gebraucht
    assert aus["lauf"] == 30 and aus["aufnahme"] == 1
    assert aus["dateien"] == {"geaendert": [], "neu": [], "fehlend": []}


def test_abgleich_nennt_die_geaenderte_datei_und_ihren_baum(u):
    u.aufnahme["dateien"][REL]["sha256"] = "9" * 64
    schreibe_aufnahme(u.r, "neu", 1, u.aufnahme)
    aus = abgleich_lauf.abgleich("neu", u.spec_pfad)
    assert aus["dateien"]["geaendert"] == ["Deckel.SLDPRT"]
    assert set(aus["teile"]) == {REL} and "features_neu" in aus["teile"][REL]


def test_abgleich_nennt_neue_und_fehlende_dateien(u):
    u.aufnahme["dateien"]["teile/Neu.SLDPRT"] = {**u.aufnahme["dateien"][REL]}
    del u.aufnahme["dateien"][ANDERE]
    schreibe_aufnahme(u.r, "neu", 1, u.aufnahme)
    aus = abgleich_lauf.abgleich("neu", u.spec_pfad)
    assert aus["dateien"] == {"geaendert": [], "neu": ["Neu.SLDPRT"],
                              "fehlend": ["Platte.SLDPRT"]}  # die STEP-Ausgabe zählt nicht


def test_abgleich_baugruppe_ohne_lagen_steht_das_da(u):
    aus = abgleich_lauf.abgleich("neu", u.spec_pfad)
    assert aus["baugruppe"]["lage_geprueft"] is False and any("Lage nicht geprüft" in x for x in aus["baugruppe"]["luecken"])
    assert aus["baugruppe"]["vollstaendig"] is False


def test_abgleich_mit_lagen_aus_datei(u, tmp_path):
    a = u.aufnahme["komponenten"]["Deckel-1"]["transform"]["Standard"]
    lagen = tmp_path / "lagen.json"
    lagen.write_text(json.dumps([{"name": "Deckel-1", "transform": a}]), encoding="utf-8")
    assert abgleich_lauf.abgleich("neu", u.spec_pfad, lagen_pfad=lagen)["baugruppe"]["lage_geprueft"] is True


def test_abgleich_nimmt_lagen_aus_dem_pruefbericht(u):
    a = u.aufnahme["komponenten"]["Deckel-1"]["transform"]["Standard"]
    bericht = u.spec_pfad.parent / "protokolle" / "alt.lauf-30.pruefbericht.json"
    bericht.write_text(json.dumps({"lagen": {"Deckel-1": a}}), encoding="utf-8")
    assert abgleich_lauf.abgleich("neu", u.spec_pfad)["baugruppe"]["lage_geprueft"] is True


def test_abgleich_kaputte_lagen_datei(u, tmp_path):
    lagen = tmp_path / "lagen.json"
    lagen.write_text("{kaputt", encoding="utf-8")
    with pytest.raises(BestandFehler) as e:
        abgleich_lauf.abgleich("neu", u.spec_pfad, lagen_pfad=lagen)
    assert e.value.daten["code"] == BESTAND_NICHT_LESBAR


def test_abgleich_ohne_aufnahme(u):
    with pytest.raises(BestandFehler) as e:
        abgleich_lauf.abgleich("gibt-es-nicht", u.spec_pfad)
    assert e.value.daten["code"] == BESTAND_UNBEKANNT


def test_abgleich_mit_einer_aenderungs_spec(u, monkeypatch):
    monkeypatch.setattr(abgleich_lauf, "art_der_datei", lambda pfad: "aenderung")
    with pytest.raises(BestandFehler) as e:
        abgleich_lauf.abgleich("neu", u.spec_pfad)
    assert e.value.daten["code"] == BESTAND_REFERENZ


def test_abgleich_ohne_herkunft_nimmt_den_letzten_lauf(u, monkeypatch):
    (bestand_ordner(u.r, "neu", 1) / "herkunft.json").unlink()
    monkeypatch.setattr(abgleich_lauf, "letzter_gebauter_lauf", lambda p: (7, _protokoll()))
    assert abgleich_lauf.abgleich("neu", u.spec_pfad)["lauf"] == 7


def test_abgleich_ohne_lauf(u, monkeypatch):
    (bestand_ordner(u.r, "neu", 1) / "herkunft.json").unlink()
    monkeypatch.setattr(abgleich_lauf, "letzter_gebauter_lauf", lambda p: None)
    with pytest.raises(BestandFehler) as e:
        abgleich_lauf.abgleich("neu", u.spec_pfad)
    assert e.value.daten["code"] == BESTAND_UNBEKANNT


def test_abgleich_herkunft_einer_anderen_spec_gilt_nicht(u, monkeypatch):
    schreibe_herkunft(u.r, "neu", 1, {"auftrag": "alt", "lauf": 30, "spec": "andere.yaml"})
    monkeypatch.setattr(abgleich_lauf, "letzter_gebauter_lauf", lambda p: (5, _protokoll()))
    assert abgleich_lauf.abgleich("neu", u.spec_pfad)["lauf"] == 5


def test_abgleich_eines_teils(u, monkeypatch):
    a = {**json.loads(json.dumps(AUFNAHME))}
    a["datei"] = {**a["datei"], "name": "Deckel.SLDPRT", "sha256": "9" * 64}
    schreibe_aufnahme(u.r, "teil", 1, a)
    monkeypatch.setattr(abgleich_lauf, "art_der_datei", lambda pfad: "teil")
    protokoll = {"status": "ok", "sha256": {"Deckel.SLDPRT": "1" * 64}, "knoten": []}
    monkeypatch.setattr(abgleich_lauf, "letzter_gebauter_lauf", lambda p: (2, protokoll))
    aus = abgleich_lauf.abgleich("teil", u.spec_pfad)
    assert aus["dateien"]["geaendert"] == ["Deckel.SLDPRT"] and "Deckel.SLDPRT" in aus["teile"] and aus["baugruppe"] is None


def test_cli_abgleich(u, monkeypatch, tmp_path):
    gerufen = []
    monkeypatch.setattr(abgleich_lauf, "abgleich", lambda *a, **k: gerufen.append((a, k)) or {"ok": True})
    assert main(["bestand", "abgleich", "neu", "--spec", str(u.spec_pfad), "--aufnahme", "2", "--lagen", "x.json",
                 "--referenzbau"]) == 0
    assert gerufen == [(("neu", u.spec_pfad), {"aufnahme": 2, "lagen_pfad": Path("x.json"), "referenz": True})]


# --- Referenzbau -----------------------------------------------------------------------------------------------------------

class App:
    def __init__(self):
        self.geoeffnet, self.geschlossen = [], []

    def CloseDoc(self, titel):
        self.geschlossen.append(titel)


@pytest.fixture
def bau(u, monkeypatch):
    """Geänderter Deckel; `baue_teil_dokument`, `speichere`, Öffnen, Lesen und Differenz als Attrappen."""
    u.aufnahme["dateien"][REL]["sha256"] = "9" * 64
    schreibe_aufnahme(u.r, "neu", 1, u.aufnahme)
    app = App()
    gebaut, gespeichert = [], []

    def baue(app_, r, standard, spec, spec_pfad, auftrag, protokoll):
        gebaut.append((spec["name"], spec_pfad, auftrag))
        return SimpleNamespace(GetTitle=f"Teil{len(gebaut)}"), None, u.baufehler

    def oeffne_in(app_, pfad, wurzel, sichtbar=False, nur_lesen=True):
        app.geoeffnet.append((Path(pfad), Path(wurzel), sichtbar, nur_lesen))
        return SimpleNamespace(GetTitle=Path(pfad).name)

    monkeypatch.setattr(abgleich_lauf, "verbinde", lambda jahr: app)
    monkeypatch.setattr(abgleich_lauf, "baue_teil_dokument", baue)
    monkeypatch.setattr(abgleich_lauf.sw, "speichere", lambda model, pfad, kopie=False: gespeichert.append(Path(pfad)))
    monkeypatch.setattr(abgleich_lauf, "oeffne_in", oeffne_in)
    monkeypatch.setattr(abgleich_lauf, "lies_bestand", lambda app_, model: _gelesen(REL))
    monkeypatch.setattr(abgleich_lauf, "koerper_differenz", lambda a, v, n, k: [])
    monkeypatch.setattr(abgleich_lauf, "teil_specs", lambda *x: {"Deckel.SLDPRT": (SPEC_TEIL,
                                                                                   u.spec_pfad.parent / "deckel.yaml")})
    u.app, u.gebaut, u.gespeichert, u.baufehler = app, gebaut, gespeichert, None
    return u


def test_referenzbau_schreibt_nur_unter_referenz(bau):
    aus = abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)
    ordner = bau.r.arbeitsordner / "neu" / "referenz-1"
    assert aus["referenzbau"]["ordner"] == str(ordner)
    assert bau.gespeichert == [ordner / "referenz_Deckel.SLDPRT"]   # eigener Name: Die Bestandskopie ist zugleich offen
    assert not (bau.r.arbeitsordner / "alt").exists()


def test_referenzbau_baut_nur_geaenderte(bau):
    aus = abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)
    assert [g[0] for g in bau.gebaut] == ["Deckel"] and list(aus["referenzbau"]["teile"]) == [REL]


def test_referenzbau_vergleicht_mit_der_bestandskopie(bau):
    t = abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)["referenzbau"]["teile"][REL]
    ordner = bestand_ordner(bau.r, "neu", 1)
    assert bau.app.geoeffnet == [(ordner / REL, ordner, False, True)]
    assert t["features"]["id"] == "baum" and t["features"]["ok"] is True and t["masse"]["id"] == "masse"
    assert t["differenzen"] == {"Standard": [], "Variante B": []}
    assert bau.app.geschlossen == ["Deckel.SLDPRT", "Teil1"]


def test_referenzbau_meldet_differenzen(bau, monkeypatch):
    from swki.bestand.differenz import Abweichung, DifferenzFehler

    def differenz(a, v, n, k):
        if k == "Variante B":
            raise DifferenzFehler("Bilanz")
        return [Abweichung("hinzu", [0, 0, 0, 1, 1, 1], 1.0, 6.0)]

    monkeypatch.setattr(abgleich_lauf, "koerper_differenz", differenz)
    t = abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)["referenzbau"]["teile"][REL]
    assert t["differenzen"]["Standard"][0]["art"] == "hinzu" and t["differenzen"]["Variante B"] == "Bilanz"


def test_referenzbau_traegt_den_auftrag_der_spec_ein(bau):
    """Die Eigenschaft `Auftrag` wiche sonst immer ab: Gebaut wurde die Datei im Auftrag der Spec, nicht in dem der Aufnahme."""
    abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)
    assert bau.gebaut[0][2] == "alt"


def test_referenzbau_ohne_gemeinsame_konfiguration_steht_das_da(bau, monkeypatch):
    """Leere `differenzen` hieße sonst: gleich."""
    monkeypatch.setattr(abgleich_lauf, "lies_bestand", lambda a, m: {**_gelesen(REL), "konfigurationen": ["Andere"]})
    t = abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)["referenzbau"]["teile"][REL]
    assert t["differenzen"] == {} and "keine gemeinsame Konfiguration" in t["hinweis"] and bau.app.geoeffnet == []


def test_referenzbau_mit_gemeinsamer_konfiguration_ohne_hinweis(bau):
    assert "hinweis" not in abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)["referenzbau"]["teile"][REL]


def test_referenzbau_zaehlt_weiter(bau):
    (bau.r.arbeitsordner / "neu" / "referenz-3").mkdir(parents=True)
    assert abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)["referenzbau"]["ordner"].endswith("referenz-4")


def test_referenzbau_fehler_im_bau_steht_da(bau):
    bau.baufehler = BauFehler("REBUILD_FEHLER", "f1 kaputt", schritt="rebuild")
    t = abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)["referenzbau"]["teile"][REL]
    assert t["fehler"]["code"] == "REBUILD_FEHLER" and bau.gespeichert == [] and bau.app.geschlossen == ["Teil1"]


def test_referenzbau_ohne_teil_spec_steht_da(bau, monkeypatch):
    monkeypatch.setattr(abgleich_lauf, "teil_specs", lambda *x: {})
    aus = abgleich_lauf.abgleich("neu", bau.spec_pfad, referenz=True)["referenzbau"]
    assert aus["teile"] == {} and aus["nicht_gebaut"][0]["datei"] == REL and bau.gebaut == []


def test_referenzbau_ohne_geaenderte_datei_baut_nichts(u, monkeypatch):
    monkeypatch.setattr(abgleich_lauf, "teil_specs", lambda *x: {})
    aus = abgleich_lauf.abgleich("neu", u.spec_pfad, referenz=True)
    assert aus["referenzbau"]["teile"] == {}     # `verbinde` der Fixture schlägt sonst an


# --- speichere_an_ort ------------------------------------------------------------------------------------------------------

@pytest.fixture
def arbeit(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    monkeypatch.setattr(sw_bestand, "lade_rechner", lambda: r)
    return r.arbeitsordner


def _teil(pfad: Path) -> Teil:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    return Teil(pfad)


def test_speichere_an_ort_unterordner(arbeit):
    lauf = arbeit / "a1" / "lauf-3"
    ziel = lauf / "teile" / "A.SLDPRT"
    teil = _teil(ziel)
    sw_bestand.speichere_an_ort(teil, ziel, lauf)
    assert teil.gespeichert
    fremd = arbeit / "a1" / "bestand-1" / "teile" / "A.SLDPRT"
    teil = _teil(fremd)
    with pytest.raises(BauFehler) as e:
        sw_bestand.speichere_an_ort(teil, fremd, fremd.parent.parent)
    assert e.value.code == SPEICHERN_FEHLGESCHLAGEN and teil.gespeichert == []


def test_speichere_an_ort_fremder_auftrag(arbeit):
    """Auch bei gleicher Nummer: `lauf-30` eines anderen Auftrags ist nicht dieser Lauf."""
    fremd = arbeit / "anderer" / "lauf-30" / "A.SLDPRT"
    teil = _teil(fremd)
    with pytest.raises(BauFehler):
        sw_bestand.speichere_an_ort(teil, fremd, arbeit / "a1" / "lauf-30")
    assert teil.gespeichert == []


def test_speichere_an_ort_nur_direkt_unter_einem_auftrag(arbeit):
    tief = arbeit / "a1" / "bestand-1" / "lauf-3"
    ziel = tief / "A.SLDPRT"
    teil = _teil(ziel)
    with pytest.raises(BauFehler):
        sw_bestand.speichere_an_ort(teil, ziel, tief)
    assert teil.gespeichert == []


# --- swki aenderungen: Block baugruppe -------------------------------------------------------------------------------------

@pytest.fixture
def lauf(tmp_path, monkeypatch):
    """Lauf mit geänderter Baugruppe; `lies_baugruppe` und die Soll-Daten als Attrappen."""
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    spec_pfad = tmp_path / "A" / "b.yaml"
    spec_pfad.parent.mkdir()
    ordner = r.arbeitsordner / "A" / "lauf-1"
    ordner.mkdir(parents=True)
    datei = ordner / "A_b.sldasm"
    datei.write_bytes(b"von Hand")
    protokoll = {"status": "ok", "sha256": {datei.name: "0" * 64}, "komponenten": [], "knoten": []}
    x = SimpleNamespace(oeffnen=[], gelesen=baugruppen_aufnahme(), lesefehler=None, spec_pfad=spec_pfad, protokoll=protokoll)

    def lies(app, model):
        if x.lesefehler:
            raise x.lesefehler
        return x.gelesen

    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "lade_standard", lambda: {})
    monkeypatch.setattr(aenderungen, "letzter_gebauter_lauf", lambda p: (1, protokoll))
    monkeypatch.setattr(aenderungen, "art_der_datei", lambda p: "baugruppe")
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {datei.name: {}})
    monkeypatch.setattr(aenderungen, "soll_masse", lambda *a: {})
    monkeypatch.setattr(aenderungen, "soll_verknuepfungen_lauf", lambda p, pr: {})
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: SimpleNamespace(CloseDoc=lambda t: None))
    monkeypatch.setattr(aenderungen, "oeffne", lambda app, pfad, **k: x.oeffnen.append(k) or SimpleNamespace(GetTitle=pfad.name))
    monkeypatch.setattr(aenderungen, "lies_globale_variablen", lambda m: {})
    monkeypatch.setattr("swki.baugruppe.sw_baugruppe.verknuepfungswerte", lambda m: {})
    monkeypatch.setattr("swki.bestand.sw_baugruppe_bestand.lies_baugruppe", lies)
    return x


def test_aenderungen_block_baugruppe(lauf):
    e = aenderungen.aenderungen(lauf.spec_pfad)["geaendert"][0]
    assert "komponenten_neu" in e["baugruppe"] and e["baugruppe"]["luecken"]
    assert lauf.oeffnen == [{"sichtbar": False, "nur_lesen": True, "voll": True}]


def test_aenderungen_baugruppe_erklaert_den_hinweis(lauf):
    """Findet der Block etwas, steht „Datei geändert, nicht erklärt“ nicht mehr da."""
    lauf.protokoll["komponenten"] = [{"id": "x", "sw_name": "Weg-1", "datei": "Weg.SLDPRT"}]
    e = aenderungen.aenderungen(lauf.spec_pfad)["geaendert"][0]
    assert e["baugruppe"]["komponenten_weg"] and "nicht_erklaert" not in e


def test_aenderungen_nicht_lesbar_ist_ein_befund(lauf):
    lauf.lesefehler = RuntimeError("COM weg")
    e = aenderungen.aenderungen(lauf.spec_pfad)["geaendert"][0]
    assert e["baugruppe"]["vollstaendig"] is False and "COM weg" in e["baugruppe"]["luecken"][0] and e["nicht_erklaert"] is True


def test_ungeprueft_baugruppe_ist_nie_unveraendert():
    e = ungeprueft_baugruppe("kein Soll")
    assert e["nicht_erklaert"] is True and e["vollstaendig"] is False and e["luecken"] == ["kein Soll"]
    assert e["komponenten_geprueft"] is False and e["verknuepfungen_geprueft"] is False and e["lage_geprueft"] is False
