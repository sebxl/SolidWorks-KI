"""swki pruefen für art: aenderung ohne SolidWorks: Spec, Freigabe, Aufnahme, Kopien und Berichte sind echt, nur die offenen
Dokumente sind Attrappen. Kern: Ein Lauf besteht nur, was nachgewiesen ist (`ok: None` besteht nie), beide Dokumente tragen
verschiedene Namen und gehen wieder zu."""

import copy
import hashlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from swki import aenderungen
from swki.auftrag import lauf_datei, lauf_ordner
from swki.bestand import ablage, pruefen as modul
from swki.bestand import spec as spec_modul
from swki.bestand.differenz import Abweichung, DifferenzFehler
from swki.bestand.fehler import BESTAND_ABWEICHEND, BestandFehler
from swki.cli import SwkiFehler
from swki.compiler.anker import AnkerFehler
from swki.konfig import Rechner
from swki.pruefung import befehle
from swki.pruefung.befehle import LaufFehler
from swki.pruefung.geometrie import Messgeometrie
from swki.pruefung.schleife import empfehlung, lies_laeufe
from swki.spec.freigabe import FreigabeFehler
from swki.spec.normen import SW_BEFESTIGUNG, SW_END_BLIND, SW_NORM
from tests.bestand.beispiel_aufnahme import aufnahme as beispiel

INHALT = b"bestandskopie"
GEAENDERT = b"lauf"
MASS = {"id": "p1", "typ": "mass", "was": "Abstand", "mass": "D2@Skizze4", "alt": 40, "neu": 45}
IM_BEREICH = [-40.0, 10.0, 10.0, -30.0, 20.0, 20.0]


class Umgebung:
    """Auftrag A: Aufnahme 1, Lauf 1 mit Protokoll und geänderter Datei, Attrappen für SolidWorks."""

    def __init__(self, tmp_path, monkeypatch):
        self.r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
        for m in (modul, spec_modul):
            monkeypatch.setattr(m, "lade_rechner", lambda: self.r)
        monkeypatch.setattr(aenderungen, "lade_rechner", lambda: self.r)
        monkeypatch.setattr(modul, "lade_standard", lambda: {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}})
        self.spec_pfad = tmp_path / "auftraege" / "A" / "aenderung.yaml"
        self.spec_pfad.parent.mkdir(parents=True)
        self.aufnahme = beispiel()
        self.aufnahme["datei"]["sha256"] = hashlib.sha256(INHALT).hexdigest()
        self.aufnahme["reihenfolge"] = {k: [f["name"] for f in self.aufnahme["features"]] for k in self.aufnahme["konfigurationen"]}
        self.aufnahme["eigenschaften"]["konfiguration"]["Variante B"] = {}
        self.ordner = ablage.bestand_ordner(self.r, "A", 1)
        self.ordner.mkdir(parents=True)
        self.kopie = self.ordner / self.aufnahme["datei"]["name"]
        self.kopie.write_bytes(INHALT)
        os.chmod(self.kopie, stat.S_IREAD)
        ablage.schreibe_aufnahme(self.r, "A", 1, self.aufnahme)

        self.lauf_ordner = lauf_ordner(self.r, "A", 1)
        self.lauf_ordner.mkdir(parents=True)
        self.teil = self.lauf_ordner / self.kopie.name
        self.teil.write_bytes(GEAENDERT)

        self.nachher = copy.deepcopy(self.aufnahme)
        del self.nachher["datei"]
        for m in self.nachher["masse"]:
            if m["name"] == "D2@Skizze4":
                m["werte"] = {"Standard": 45.0, "Variante B": 45.0}
        self.abweichungen = {"Standard": [Abweichung("hinzu", IM_BEREICH, 500.0)], "Variante B": [Abweichung("hinzu", IM_BEREICH, 500.0)]}
        self.offen, self.geoeffnet, self.geschlossen, self.bilder, self.gelesen = [], [], [], [], []
        self.app = SimpleNamespace(CloseDoc=self._schliesse)
        self.vor_oeffnen = lambda pfad: None
        monkeypatch.setattr(modul, "verbinde", lambda jahr: self.app)
        monkeypatch.setattr(modul, "oeffne", self._oeffne)
        monkeypatch.setattr(modul, "lies_bestand", self._lies)
        monkeypatch.setattr(modul, "koerper_differenz", self._differenz)
        monkeypatch.setattr(modul, "alle_feature_boxen", lambda modelle, konfigurationen, namen: {})
        monkeypatch.setattr(modul, "screenshots", self._screenshots)

    def _oeffne(self, app, pfad, sichtbar=True, nur_lesen=False):
        self.vor_oeffnen(pfad)
        assert pfad.name not in self.offen, "SolidWorks öffnet zwei gleichnamige Dokumente nicht zugleich (S18d: Fehler 65536)"
        assert nur_lesen, "Prüfen öffnet nur lesend (Spec §7)"
        self.offen.append(pfad.name)
        self.geoeffnet.append({"pfad": pfad, "sichtbar": sichtbar, "zusammen": len(self.offen)})
        return SimpleNamespace(GetTitle=pfad.name, FeatureByName=lambda name: None, pfad=pfad)

    def _schliesse(self, titel):
        self.offen.remove(titel)
        self.geschlossen.append(titel)

    def _lies(self, app, model):
        assert model.pfad == self.teil  # die Aufnahme liefert „vorher“, gelesen wird nur der Lauf
        self.gelesen.append(model.pfad)
        return self.nachher

    def _differenz(self, app, a, b, konfiguration):
        assert (a.pfad.name, b.pfad) == (f"vorher_{self.kopie.name}", self.teil)
        wert = self.abweichungen[konfiguration]
        if isinstance(wert, Exception):
            raise wert
        return wert

    def _screenshots(self, app, model, ordner):
        self.bilder.append((model.GetTitle, ordner))
        return {"iso": str(ordner / "iso.png")}

    def schreibe(self, punkte=(MASS,), bereiche=None, pruefung=None, status="ok", freigeben=True, knoten=()):
        spec = {"art": "aenderung", "name": "Lagerdeckel_Rev",
                "bestand": {"datei": self.kopie.name, "sha256": self.aufnahme["datei"]["sha256"], "aufnahme": 1},
                "parameter": {"RA": 12}, "punkte": list(punkte),
                "bereiche": bereiche or [{"punkte": [p["id"] for p in punkte], "box": {"min": [-50, 0, 0], "max": [-20, 40, 20]}}]}
        if pruefung:
            spec["pruefung"] = pruefung
        self.spec_pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
        if freigeben:
            spec_modul.freigeben(self.spec_pfad)
        fehler = None if status == "ok" else {"code": "REBUILD_FEHLER", "meldung": "kaputt"}
        protokoll = {"status": status, "fehler": fehler, "dauer_s": 1.0, "gestartet": "2026-10-31T10:00:00", "knoten": list(knoten),
                     "dateien": {"teil": str(self.teil)} if status == "ok" else {}, "sha256": {self.teil.name: hashlib.sha256(GEAENDERT).hexdigest()}}
        ziel = lauf_datei(self.spec_pfad, 1, "protokoll")
        ziel.parent.mkdir(exist_ok=True)
        ziel.write_text(json.dumps(protokoll), encoding="utf-8")
        return self.spec_pfad


@pytest.fixture
def u(tmp_path, monkeypatch):
    return Umgebung(tmp_path, monkeypatch)


def test_pruefen_besteht(u):
    b = modul.pruefen(u.schreibe())
    assert b["bestanden"] is True and b["maengel"] == [] and b["lauf"] == 1 and b["datei"] == str(u.teil)
    ids = [e["id"] for e in b["pruefungen"]]
    assert ids.count("punkt:p1") == 1 and "baum" in ids and ids.count("bereich") == 2
    assert b["differenzen"]["Standard"][0]["volumen"] == 500.0 and b["differenzen"]["Variante B"][0]["bereich"] == 0
    assert b["bilder"] == {"iso": str(u.lauf_ordner / "bilder" / "iso.png")}
    assert b["bilder_vorher"] == {"iso": str(u.lauf_ordner / "vergleich" / "bilder" / "iso.png")}


def test_pruefen_oeffnet_vorher_unter_anderem_namen(u):
    """Plan Review Focus 1: Bestandskopie und Lauf heißen gleich. Die Attrappe scheitert wie SolidWorks an gleichen Namen."""
    assert u.kopie.name == u.teil.name
    modul.pruefen(u.schreibe())
    zusammen = [g for g in u.geoeffnet if g["zusammen"] == 2]
    assert len(zusammen) == 1
    vorher_pfad = u.geoeffnet[0]["pfad"]
    assert vorher_pfad.name != u.teil.name and vorher_pfad.parent == u.lauf_ordner / "vergleich"
    assert vorher_pfad.name == f"vorher_{u.teil.name}"
    assert vorher_pfad.read_bytes() == INHALT
    assert vorher_pfad.stat().st_mode & stat.S_IWRITE  # sonst Warnung beim Öffnen (Präzisierung 5)


def test_vergleichen_unsichtbar_bilder_sichtbar(u):
    """S18d: Differenz geht unsichtbar (+0 MB gegen +3,2 GB), Bilder brauchen ein Fenster."""
    modul.pruefen(u.schreibe())
    assert [g["sichtbar"] for g in u.geoeffnet] == [False, False, True, True]
    assert [t for t, _ in u.bilder] == [u.teil.name, f"vorher_{u.teil.name}"]


def test_schliesst_beide_dokumente(u):
    modul.pruefen(u.schreibe())
    assert u.offen == [] and sorted(u.geschlossen) == sorted([u.teil.name, f"vorher_{u.teil.name}"] * 2)


def test_schliesst_beide_auch_nach_fehler(u, monkeypatch):
    monkeypatch.setattr(modul, "lies_bestand", lambda app, model: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        modul.pruefen(u.schreibe())
    assert u.offen == []


def test_schliesst_das_erste_wenn_das_zweite_nicht_aufgeht(u):
    def scheitert(pfad):
        if pfad == u.teil:
            raise RuntimeError("geht nicht auf")

    u.vor_oeffnen = scheitert
    with pytest.raises(RuntimeError):
        modul.pruefen(u.schreibe())
    assert u.offen == []


def test_speichert_nichts_und_der_lauf_gilt_nicht_als_geaendert(u):
    """Die Vorher-Kopie liegt im Lauf-Ordner und bleibt liegen, Änderungserkennung und `pruefe_unveraendert` sehen sie nicht."""
    spec = u.schreibe()
    modul.pruefen(spec)
    assert (u.lauf_ordner / "vergleich" / f"vorher_{u.teil.name}").is_file()
    assert u.teil.read_bytes() == GEAENDERT and u.kopie.read_bytes() == INHALT
    assert aenderungen.pruefe_unveraendert(u.r, "A", spec) is None


def test_datei_ordner_fuer_externe_referenzen(u):
    """Bestandskopie und Lauf nennen dieselbe Datei in ihrem Ordner: keine neue Referenz."""
    u.aufnahme["externe_referenzen"] = [str(u.ordner / "Basis.SLDPRT")]
    ablage.schreibe_aufnahme(u.r, "A", 1, u.aufnahme)
    u.nachher["externe_referenzen"] = [str(u.lauf_ordner / "Basis.SLDPRT")]
    b = modul.pruefen(u.schreibe())
    e = next(x for x in b["pruefungen"] if x["id"] == "externe_referenzen")
    assert e["ok"] is True


def test_zweite_pruefung_ueberschreibt_die_vorher_kopie(u):
    spec = u.schreibe()
    modul.pruefen(spec)
    modul.pruefen(spec)
    assert (u.lauf_ordner / "vergleich" / f"vorher_{u.teil.name}").read_bytes() == INHALT


def test_pruefbericht_liegt_in_beiden_ordnern(u):
    spec = u.schreibe()
    b = modul.pruefen(spec)
    assert json.loads((u.lauf_ordner / "pruefbericht.json").read_text(encoding="utf-8"))["bestanden"] is True
    assert json.loads(lauf_datei(spec, 1, "pruefbericht").read_text(encoding="utf-8")) == json.loads(json.dumps(b, default=str))


def test_pruefen_lehnt_abgebrochenen_lauf_ab(u):
    with pytest.raises(LaufFehler) as e:
        modul.pruefen(u.schreibe(status="fehler"))
    assert e.value.daten["code"] == "LAUF_ABGEBROCHEN" and u.geoeffnet == []


def test_teil_fehlt(u):
    spec = u.schreibe()
    u.teil.unlink()
    with pytest.raises(SwkiFehler, match="fehlt"):
        modul.pruefen(spec)
    assert u.geoeffnet == []


def test_ohne_freigabe_kein_pruefen(u):
    with pytest.raises(FreigabeFehler):
        modul.pruefen(u.schreibe(freigeben=False))
    assert u.geoeffnet == []


def test_geaenderte_bestandskopie_bricht_ab(u):
    spec = u.schreibe()
    os.chmod(u.kopie, stat.S_IREAD | stat.S_IWRITE)
    u.kopie.write_bytes(b"anders")
    with pytest.raises(BestandFehler) as e:
        modul.pruefen(spec)
    assert e.value.daten["code"] == BESTAND_ABWEICHEND and u.geoeffnet == []


def test_mangel_aus_vergleich_und_bereich(u):
    u.nachher["masse"][4]["werte"]["Standard"] = 44.0  # D2@Skizze4
    u.abweichungen["Variante B"] = [Abweichung("hinzu", [10.0, 10.0, 10.0, 20.0, 20.0, 20.0], 7.0)]
    b = modul.pruefen(u.schreibe())
    assert b["bestanden"] is False
    assert {m["pruefung"] for m in b["maengel"]} == {"punkt:p1", "bereich"}


def test_masse_pruefen_soll_als_ausdruck(u):
    pruefung = {"masse_pruefen": [{"was": "Randabstand", "von": {"punkt": [0, 0, 0]}, "zu": {"punkt": ["=RA", 0, 0]}, "soll": "=RA"}]}
    b = modul.pruefen(u.schreibe(pruefung=pruefung))
    e = next(x for x in b["pruefungen"] if x["id"] == "mass:Randabstand")
    assert e["ok"] is True and e["ist"] == 12.0 and e["soll"] == 12 and e["tol"] == 0.01 and e["konfiguration"] == "Standard"


def test_masse_pruefen_abweichung_ist_mangel(u):
    pruefung = {"masse_pruefen": [{"was": "Rand", "von": {"punkt": [0, 0, 0]}, "zu": {"punkt": [13, 0, 0]}, "soll": "=RA", "tol": 0.5}]}
    b = modul.pruefen(u.schreibe(pruefung=pruefung))
    assert b["bestanden"] is False and b["maengel"][0]["pruefung"] == "mass:Rand"


def _feature_mass(seite: dict) -> dict:
    return {"masse_pruefen": [{"was": "M", "von": seite, "zu": {"punkt": [0, 0, 0]}, "soll": 1}]}


def test_messpunkt_loest_alle_drei_namen_auf(u, monkeypatch):
    """Validieren lässt Bestandsname, Punkt-ID und `name` eines neuen Features zu (Spec §4.2)."""
    neu = {"id": "p2", "typ": "feature", "name": "Gewinde M6", "feature": {"typ": "normbohrung"}}
    pruefung = {"masse_pruefen": [{"was": "M", "von": {"feature": seite, "flaeche": "+x"}, "zu": {"punkt": [0, 0, 0]}, "soll": 1}
                                  for seite in ("p2", "Gewinde M6", "Fase3", "Fehlt")]}
    spec = {"punkte": [MASS, neu], "parameter": {}, "pruefung": pruefung}
    features = {"Gewinde M6": "NEU", "Fase3": "ALT"}
    model = SimpleNamespace(FeatureByName=features.get)
    ctx = modul._messkontext(None, model, spec, Path("x.yaml"), 0.1)
    assert {n: e.features for n, e in ctx.ergebnisse.items()} == {"p2": ["NEU"], "Gewinde M6": ["NEU"], "Fase3": ["ALT"]}


def test_neue_normbohrung_wird_gegen_die_freigabe_gemessen(u, monkeypatch):
    """Der Referenz-Prüfer, Lauf 1: `punkt:<id>` belegte nur, dass das Feature da ist. Die Abweichung in einer Konfiguration ist ein Mangel."""
    f = {"typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [45, 0, 20]}, "positionen": [[-38, 24]], "tiefe": 10,
         "gewindetiefe": 8}
    neu = {"id": "p2", "typ": "feature", "name": "Gewinde M6", "feature": f}
    for k in u.nachher["konfigurationen"]:
        u.nachher["reihenfolge"][k].append("Gewinde M6")
    u.nachher["features"].append({"name": "Gewinde M6", "typ": "HoleWzd", "eltern": [], "kinder": [], "unter": [], "tabelle": False,
                                  "unterdrueckt": {"Standard": False, "Variante B": False}})
    ist = {"typ": 0, "befestigung": SW_BEFESTIGUNG["gewinde"], "norm": SW_NORM["ISO"], "groesse": "M6", "ende": SW_END_BLIND, "tiefe": 10.0,
           "gewindetiefe": 8.0, "positionen": 1, "achsen": [((-38.0, 24.0, 15.0), (0.0, 0.0, 1.0))]}
    monkeypatch.setattr(modul, "in_konfigurationen", lambda model, konfigurationen, messe: {
        "Standard": {"Gewinde M6": ist}, "Variante B": {"Gewinde M6": {**ist, "gewindetiefe": 7.0}}})
    b = modul.pruefen(u.schreibe(punkte=(MASS, neu)))
    e = next(x for x in b["pruefungen"] if x["id"] == "punkt:p2")
    assert e["ok"] is False and "Variante B: gewindetiefe: ist 7 statt 8" in e["hinweis"]
    assert e["soll"]["gewindetiefe"] == 8 and e["ist"]["Standard"]["positionen"] == [[-38.0, 24.0]]
    assert "punkt:p2" in [m["pruefung"] for m in b["maengel"]]


def test_messpunkt_feature_fehlt_ist_mangel(u):
    pruefung = _feature_mass({"feature": "Fase3", "flaeche": "+x"})
    b = modul.pruefen(u.schreibe(pruefung=pruefung))
    m = next(x for x in b["maengel"] if x["pruefung"] == "mass:M")
    assert "Fase3" in m["beschreibung"]


def test_messpunkt_flaeche_mit_ausdruecken(u, monkeypatch):
    aufrufe = []

    def messpunkt(mp, einbau, gewinde, flaechen, tol_mm):
        aufrufe.append((mp, einbau, gewinde, flaechen, tol_mm))
        return Messgeometrie("ebene", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))

    monkeypatch.setattr(modul, "messpunkt", messpunkt)
    monkeypatch.setattr(modul, "alle_flaechen", lambda model: ["FLAECHE"])
    pruefung = _feature_mass({"flaeche": {"nahe": ["=RA", 0, 10], "normale": [1, 0, 0]}})
    modul.pruefen(u.schreibe(pruefung=pruefung))
    assert aufrufe == [({"flaeche": {"nahe": [12, 0, 10], "normale": [1, 0, 0]}}, {}, {}, ["FLAECHE"], 0.1)]


def test_messpunkt_orten_scheitert_ist_mangel(u, monkeypatch):
    monkeypatch.setattr(modul, "alle_flaechen", lambda model: [])
    b = modul.pruefen(u.schreibe(pruefung=_feature_mass({"flaeche": {"nahe": [0, 0, 0], "normale": [1, 0, 0]}})))
    assert any(m["pruefung"] == "mass:M" and "REFERENZ_NICHT_GEFUNDEN" in m["beschreibung"] for m in b["maengel"])


def test_messen_faengt_nur_baufehler(u, monkeypatch):
    def messgeometrie(ctx, spec, mp):
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", "weg")

    monkeypatch.setattr(modul, "messgeometrie", messgeometrie)
    b = modul.pruefen(u.schreibe(pruefung=_feature_mass({"punkt": [0, 0, 0]})))
    assert any("REFERENZ_NICHT_GEFUNDEN: weg" in m["beschreibung"] for m in b["maengel"])


def test_none_besteht_nie_und_ist_sichtbar(u):
    """Ruling: `ok: None` zählt bei art: aenderung als nicht bestanden; `lies_laeufe` zählt es, sonst stünde 0 offene Mängel da."""
    u.abweichungen["Variante B"] = DifferenzFehler("Operations2 meldet Fehler 3")
    spec = u.schreibe()
    b = modul.pruefen(spec)
    e = [x for x in b["pruefungen"] if x["id"] == "bereich"]
    assert [x["ok"] for x in e] == [True, None] and "Fehler 3" in e[1]["hinweis"]
    assert b["bestanden"] is False
    [m] = b["maengel"]
    assert m["pruefung"] == "bereich" and m["nicht_nachgewiesen"] is True and "Fehler 3" in m["beschreibung"]
    lauf_datei(spec, 1, "pruefer").write_text('{"bestanden": true, "maengel": []}', encoding="utf-8")
    [lauf] = lies_laeufe(spec)
    assert lauf["code_maengel"] == 1 and lauf["bestanden"] is False and lauf["offen"] == 1
    assert empfehlung([lauf], 3)[0] == "nachbessern"


def test_mangel_ist_nachgewiesen(u):
    u.abweichungen["Standard"] = [Abweichung("hinzu", [10.0, 10.0, 10.0, 20.0, 20.0, 20.0], 7.0)]
    b = modul.pruefen(u.schreibe())
    assert [m["nicht_nachgewiesen"] for m in b["maengel"]] == [False]


@pytest.mark.parametrize("oks, ok", [((True, False), False), ((False, True), False), ((True, None), None), ((None, False), False),
                                     ((None, True), None), ((True, True), True)])
def test_ein_eintrag_je_punkt_der_schlechtere_gilt(oks, ok):
    a, b = oks
    davor, danach = {"id": "baum", "ok": True}, {"id": "bereich", "ok": True}
    roh = [{"id": "punkt:p1", "ok": a, "ist": "Wert", "knoten": ["p1"]}, davor, danach, {"id": "punkt:p1", "ok": b, "knoten": ["p1"]}]
    b = modul.bewerte_aenderung(roh)
    assert [e["id"] for e in b["pruefungen"]] == ["punkt:p1", "baum", "bereich"]
    assert b["pruefungen"][0]["ok"] is ok and b["pruefungen"][0]["ist"] == "Wert" and len(b["maengel"]) == (ok is not True)


def test_schlechtere_wirkung_bringt_ihren_hinweis_mit(u):
    """`vergleiche` sagt ok, die Differenz nicht: Der Mangel nennt, warum."""
    u.abweichungen = {"Standard": [], "Variante B": []}
    b = modul.pruefen(u.schreibe())
    [m] = b["maengel"]
    assert m["pruefung"] == "punkt:p1" and "keine Abweichung" in m["beschreibung"]


SKRIPT = {"id": "p8", "typ": "skript", "datei": "skripte/p8.py", "luecke": "x"}


def _neu(u, name):
    u.nachher["features"].append({"name": name, "typ": "ProfileFeature", "eltern": [], "kinder": [], "unter": [],
                                  "unterdrueckt": {"Standard": False, "Variante B": False}, "tabelle": False})
    for reihe in u.nachher["reihenfolge"].values():
        reihe.append(name)


def test_skript_durchgelaufen_besteht_und_erklaert_seine_features(u):
    _neu(u, "p8_skizze")
    b = modul.pruefen(u.schreibe(punkte=(MASS, SKRIPT), knoten=[{"id": "p8", "status": "ok", "sw_name": "p8_skizze"}]))
    assert b["bestanden"] is True, b["maengel"]
    e = next(x for x in b["pruefungen"] if x["id"] == "punkt:p8")
    assert e["ok"] is True and e["hinweis"] == "Notausgang, Nachweis über Bereiche, masse_pruefen und Prüfer"


def test_skript_ohne_protokoll_knoten_ist_nicht_nachgewiesen(u):
    b = modul.pruefen(u.schreibe(punkte=(MASS, SKRIPT), knoten=[{"id": "p8", "status": "offen", "sw_name": None}]))
    assert [(m["pruefung"], m["nicht_nachgewiesen"]) for m in b["maengel"]] == [("punkt:p8", True)]


def test_neues_feature_das_das_skript_nicht_zurueckgab_bleibt_offen(u):
    _neu(u, "Fremd")
    b = modul.pruefen(u.schreibe(punkte=(MASS, SKRIPT), knoten=[{"id": "p8", "status": "ok", "sw_name": None}]))
    assert [(m["pruefung"], m["nicht_nachgewiesen"]) for m in b["maengel"]] == [("baum", True)]


def test_skript_ohne_differenz_im_bereich_ist_mangel(u):
    u.abweichungen = {"Standard": [], "Variante B": []}
    u.nachher["masse"] = copy.deepcopy(u.aufnahme["masse"])
    b = modul.pruefen(u.schreibe(punkte=(SKRIPT,), knoten=[{"id": "p8", "status": "ok", "sw_name": None}]))
    assert [(m["pruefung"], m["nicht_nachgewiesen"]) for m in b["maengel"]] == [("punkt:p8", False)]


def test_nur_gemeinsame_konfigurationen(u):
    """Fehlt eine Konfiguration im Lauf, ist das Mangel `konfigurationen`, keine Differenz."""
    u.nachher["konfigurationen"] = ["Standard"]
    b = modul.pruefen(u.schreibe())
    assert list(b["differenzen"]) == ["Standard"] and {"konfigurationen"} <= {m["pruefung"] for m in b["maengel"]}


def test_feature_boxen_der_bereiche_kommen_aus_beiden_dokumenten(u, monkeypatch):
    gefragt = []

    def boxen(modelle, konfigurationen, namen):
        gefragt.append(([m.GetTitle for m in modelle], list(konfigurationen), set(namen)))
        return {"Fase3": [-41.0, 9.0, 9.0, -29.0, 21.0, 21.0]}

    monkeypatch.setattr(modul, "alle_feature_boxen", boxen)
    b = modul.pruefen(u.schreibe(bereiche=[{"punkte": ["p1"], "features": ["Fase3"]}]))
    assert gefragt == [([f"vorher_{u.teil.name}", u.teil.name], ["Standard", "Variante B"], {"Fase3"})]
    assert b["bestanden"] is True


def test_weiche_pruefen(u, monkeypatch):
    spec = u.schreibe()
    monkeypatch.setattr(modul, "pruefen", lambda pfad, lauf: {"bestand": pfad.name, "lauf": lauf})
    assert befehle.pruefen(spec, 3) == {"bestand": spec.name, "lauf": 3}


def test_weiche_lade_spec(u):
    assert befehle.lade_spec_beliebig(u.schreibe())["art"] == "aenderung"
