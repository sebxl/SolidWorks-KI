"""swki bauen für art: aenderung ohne SolidWorks: Spec, Freigabe, Aufnahme, Kopien und Protokolle sind echt, nur das offene
Dokument ist eine Attrappe. Kern der Tests: Es wird nur gespeichert, wenn alles gestimmt hat (S18c3)."""

import hashlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from swki.aenderungen import sha256_datei
from swki.auftrag import lauf_datei, lauf_ordner
from swki.bestand import bau, spec as spec_modul, sw_bestand
from swki.bestand import ablage
from swki.bestand.fehler import BESTAND_ABWEICHEND, BESTAND_VERSION_AELTER, BestandFehler
from swki.compiler import bauen as compiler_bauen
from swki.compiler.bauen import BauAbbruch
from swki.compiler.fehler import REBUILD_FEHLER, SPEICHERN_FEHLGESCHLAGEN, BauFehler
from swki.konfig import Rechner
from swki.spec.freigabe import FreigabeFehler
from tests.bestand.beispiel_aufnahme import aufnahme as beispiel
from tests.bestand.sw_attrappe import Teil, teil_aus

INHALT = b"bestandskopie"
MASS = {"id": "p1", "typ": "mass", "was": "Abstand", "mass": "D2@Skizze4", "alt": 40, "neu": 45}
VARIABLE = {"id": "p2", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110}
UNTERDRUECKEN = {"id": "p3", "typ": "unterdruecken", "feature": "Fase3"}


class Lauf:
    """Auftrag A mit Aufnahme 1: Bestandskopie, bestand.json, Spec, Attrappe für SolidWorks."""

    def __init__(self, tmp_path, monkeypatch):
        self.r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
        for modul in (bau, spec_modul, sw_bestand):
            monkeypatch.setattr(modul, "lade_rechner", lambda: self.r)
        monkeypatch.setattr(bau, "lade_standard", lambda: {"toleranzen": {"anker_mm": 0.01}})
        self.spec_pfad = tmp_path / "auftraege" / "A" / "aenderung.yaml"
        self.spec_pfad.parent.mkdir(parents=True)
        self.sha = hashlib.sha256(INHALT).hexdigest()
        self.aufnahme = beispiel()
        self.aufnahme["datei"]["sha256"] = self.sha
        self.aufnahme["reihenfolge"] = {k: [f["name"] for f in self.aufnahme["features"]] for k in self.aufnahme["konfigurationen"]}
        self.aufnahme["geometrie"] = {k: {"koerper": 1, "volumen": 1000.0, "box": [0] * 6, "schwerpunkt": [0] * 3}
                                      for k in self.aufnahme["konfigurationen"]}
        for m in self.aufnahme["masse"]:
            if m["name"] == "D2@Skizze4":
                m["werte"] = {"Standard": 40.0, "Variante B": 40.0}
        self.ordner = ablage.bestand_ordner(self.r, "A", 1)
        self.ordner.mkdir(parents=True)
        self.kopie = self.ordner / self.aufnahme["datei"]["name"]
        self.kopie.write_bytes(INHALT)
        os.chmod(self.kopie, stat.S_IREAD)
        self.geoeffnet = []
        self.app = SimpleNamespace(GetCurrentLicenseType=2, CloseDoc=lambda t: self.geschlossen.append(t))
        self.geschlossen = []
        self.teil: Teil | None = None
        self.vor_teil = lambda teil: None
        monkeypatch.setattr(bau, "verbinde", lambda jahr: self.app)
        monkeypatch.setattr(bau, "oeffne", self._oeffne)

    def _oeffne(self, app, pfad, sichtbar=True, nur_lesen=False):
        assert pfad.read_bytes() == INHALT and not nur_lesen  # die Lauf-Kopie liegt schon da und ist beschreibbar
        assert pfad.stat().st_mode & stat.S_IWRITE
        self.geoeffnet.append(pfad)
        self.teil = teil_aus(self.aufnahme, pfad)
        self.vor_teil(self.teil)
        return self.teil

    def schreibe(self, *punkte, freigeben=True):
        self.punkte = list(punkte)
        ablage.schreibe_aufnahme(self.r, "A", 1, self.aufnahme)
        spec = {"art": "aenderung", "name": "Lagerdeckel_Rev",
                "bestand": {"datei": self.aufnahme["datei"]["name"], "sha256": self.sha, "aufnahme": 1},
                "parameter": {"RA": 12}, "punkte": list(punkte), "bereiche": [{"punkte": [p["id"] for p in punkte], "features": ["Fase3"]}]}
        self.spec_pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
        if freigeben:
            spec_modul.freigeben(self.spec_pfad)
        return self.spec_pfad

    def protokoll(self, lauf=1) -> dict:
        return json.loads(lauf_datei(self.spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))

    def lauf_datei(self, lauf=1) -> Path:
        return lauf_ordner(self.r, "A", lauf) / self.aufnahme["datei"]["name"]


@pytest.fixture
def lauf(tmp_path, monkeypatch):
    return Lauf(tmp_path, monkeypatch)


def test_bau_startet_ab_bestand_und_speichert_an_ort(lauf):
    lauf.schreibe(MASS, VARIABLE, UNTERDRUECKEN)
    aus = bau.bauen(lauf.spec_pfad)
    ziel = lauf.lauf_datei()
    assert lauf.geoeffnet == [ziel] and ziel.name == "Lagerdeckel.SLDPRT"  # kein Namensschema <auftrag>_<name>
    assert lauf.teil.gespeichert == ["Standard"]  # genau ein Save3, kein SaveAs3 (die Attrappe kennt es nicht)
    assert lauf.geschlossen == ["Lagerdeckel.SLDPRT"]
    assert lauf.kopie.read_bytes() == INHALT and not lauf.kopie.stat().st_mode & stat.S_IWRITE
    assert aus["status"] == "ok" and aus["lauf"] == 1 and aus["fehler"] is None
    assert aus["dateien"] == {"teil": str(ziel)}
    assert [k["id"] for k in aus["knoten"]] == ["p1", "p2", "p3"]
    p = lauf.protokoll()
    assert p["sha256"] == {"Lagerdeckel.SLDPRT": sha256_datei(ziel)} and p["dateien"] == {"teil": str(ziel)}
    assert (lauf_ordner(lauf.r, "A", 1) / "protokoll.json").is_file()
    assert p["knoten"][0]["masse"][0]["name"] == "D2@Skizze4" and p["knoten"][0]["sw_name"] == "D2@Skizze4"


def test_bau_folgt_der_spec_reihenfolge(lauf, monkeypatch):
    """Die Prüfsumme sortiert nach id, gebaut wird in Spec-Reihenfolge."""
    lauf.schreibe(UNTERDRUECKEN, MASS)
    assert [k["id"] for k in bau.bauen(lauf.spec_pfad)["knoten"]] == ["p3", "p1"]


def test_bau_stoppt_beim_ersten_neuen_fehler(lauf):
    """Punkt p1 verursacht den Fehler, p2 läuft nicht mehr, gespeichert wird nichts."""
    lauf.schreibe(MASS, VARIABLE)

    def fehler_nach_setzen(teil):
        teil.bei_neuaufbau = lambda t: t.fehler.__setitem__(t.aktiv, [("Fase3", 7, False)]) if t.masse["D2@Skizze4"].gesetzt else None

    lauf.vor_teil = fehler_nach_setzen
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(lauf.spec_pfad)
    d = e.value.daten
    assert d["status"] == "fehler" and d["fehler"]["code"] == REBUILD_FEHLER and d["fehler"]["punkt"] == "p1"
    assert "p1" in str(e.value) and "Fase3: Code 7" in str(e.value)
    assert [(k["id"], k["status"]) for k in d["knoten"]] == [("p1", "fehler"), ("p2", "uebersprungen")]
    assert lauf.teil.gespeichert == [] and lauf.geschlossen and lauf.teil.gleichungen.gesetzt == []
    assert lauf.lauf_datei().read_bytes() == INHALT
    p = lauf.protokoll()
    assert p["status"] == "fehler" and p["dateien"] == {} and p["sha256"] == {}


def test_bekannter_fehler_stoppt_den_bau_nicht(lauf):
    """Plan Review Focus 2: Die Datei hat den Fehler schon, in dieser Konfiguration."""
    lauf.aufnahme["neuaufbau"] = [{"konfiguration": "Standard", "feature": "Fase3", "code": 12, "warnung": False}]
    lauf.schreibe(MASS)
    assert bau.bauen(lauf.spec_pfad)["status"] == "ok"
    assert lauf.teil.gespeichert == ["Standard"]


def test_bekannt_gilt_je_konfiguration(lauf):
    """Der Fehler steht nur in Variante B; derselbe Fehler in der aktiven Konfiguration ist neu."""
    lauf.aufnahme["neuaufbau"] = [{"konfiguration": "Variante B", "feature": "Fase3", "code": 12, "warnung": False}]
    lauf.schreibe(MASS)

    def fehler_nach_setzen(teil):
        teil.bei_neuaufbau = lambda t: (t.fehler.__setitem__("Standard", [("Fase3", 12, False)])
                                        if t.masse["D2@Skizze4"].gesetzt else None)

    lauf.vor_teil = fehler_nach_setzen
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(lauf.spec_pfad)
    assert e.value.daten["fehler"]["punkt"] == "p1" and lauf.teil.gespeichert == []


def test_warnung_aus_der_aufnahme_ist_nicht_bekannt(lauf):
    """Eine Warnung erklärt keinen späteren Fehler desselben Features."""
    lauf.aufnahme["neuaufbau"] = [{"konfiguration": "Standard", "feature": "Fase3", "code": 12, "warnung": True}]
    lauf.schreibe(MASS)

    def fehler_nach_setzen(teil):
        teil.bei_neuaufbau = lambda t: (t.fehler.__setitem__("Standard", [("Fase3", 12, False)])
                                        if t.masse["D2@Skizze4"].gesetzt else None)

    lauf.vor_teil = fehler_nach_setzen
    with pytest.raises(BauAbbruch):
        bau.bauen(lauf.spec_pfad)
    assert lauf.teil.gespeichert == []


def test_neuer_fehler_nur_in_anderer_konfiguration_verhindert_das_speichern(lauf):
    """S18c3: In der aktiven Konfiguration sieht alles gut aus."""
    lauf.schreibe(MASS)

    def fehler_nach_setzen(teil):
        teil.bei_neuaufbau = lambda t: (t.fehler.__setitem__("Variante B", [("Bohrung2", 1, False)])
                                        if t.masse["D2@Skizze4"].gesetzt else None)

    lauf.vor_teil = fehler_nach_setzen
    with pytest.raises(BauAbbruch, match="Variante B") as e:
        bau.bauen(lauf.spec_pfad)
    assert lauf.teil.gespeichert == [] and e.value.daten["fehler"]["code"] == REBUILD_FEHLER
    assert lauf.lauf_datei().read_bytes() == INHALT


def test_anderer_code_am_bekannten_feature_ist_neu(lauf):
    lauf.aufnahme["neuaufbau"] = [{"konfiguration": "Standard", "feature": "Fase3", "code": 12, "warnung": False}]
    lauf.schreibe(MASS)

    def code_wechselt(teil):
        teil.bei_neuaufbau = lambda t: (t.fehler.__setitem__("Standard", [("Fase3", 1, False)])
                                        if t.masse["D2@Skizze4"].gesetzt else None)

    lauf.vor_teil = code_wechselt
    with pytest.raises(BauAbbruch, match="Fase3: Code 1"):
        bau.bauen(lauf.spec_pfad)
    assert lauf.teil.gespeichert == []


def test_reorder_fehlschlag_speichert_nie(lauf, monkeypatch):
    """S18c3: False beschädigt die Konfiguration dauerhaft, `Save3` meldete trotzdem Erfolg."""
    from swki.compiler.kontext import FeatureErgebnis

    def handler(ctx, f):
        return FeatureErgebnis([ctx.model.neues_feature(f["id"], "Cut")])

    monkeypatch.setattr(bau.punkte, "alle_handler", lambda: {"bohrung": handler})
    p = {"id": "p5", "typ": "feature", "name": "Neu", "nach": "Fase3",
         "feature": {"typ": "bohrung", "durchmesser": 5, "tiefe": 5, "flaeche": {"nahe": [0, 0, 0]}, "positionen": [[0, 0]]}}
    lauf.schreibe(p, MASS)
    lauf.vor_teil = lambda teil: teil.reorder_unmoeglich.add("Neu")
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(lauf.spec_pfad)
    assert lauf.teil.gespeichert == [] and e.value.daten["fehler"]["punkt"] == "p5"
    assert [k["status"] for k in e.value.daten["knoten"]] == ["fehler", "uebersprungen"]


def test_beschaedigter_baum_ohne_fehlermeldung_verhindert_das_speichern(lauf):
    """S18c3: Die Rippe steht vorn, nichts meldet das; nur der Baum je Konfiguration zeigt es."""
    lauf.schreibe(MASS)

    def schaden(teil):
        k = teil.ordnung["Variante B"]
        teil.bei_neuaufbau = lambda t: k.insert(0, k.pop()) if t.masse["D2@Skizze4"].gesetzt and k[-1].Name != "Skizze1" else None

    lauf.vor_teil = schaden
    with pytest.raises(BauAbbruch, match="Reihenfolge"):
        bau.bauen(lauf.spec_pfad)
    assert lauf.teil.gespeichert == []


def test_nicht_genannte_konfiguration_behaelt_ihr_volumen(lauf):
    """Der Punkt nennt Variante B; ändert sich Standard, ist etwas schiefgegangen."""
    p = {**MASS, "konfigurationen": ["Variante B"]}
    lauf.schreibe(p)

    def schaden(teil):
        teil.bei_neuaufbau = lambda t: t.volumen.__setitem__("Standard", 900.0)

    lauf.vor_teil = schaden
    with pytest.raises(BauAbbruch, match="Volumen"):
        bau.bauen(lauf.spec_pfad)
    assert lauf.teil.gespeichert == []


def test_volumen_weg_verhindert_das_speichern(lauf):
    lauf.schreibe(MASS)

    def schaden(teil):
        teil.bei_neuaufbau = lambda t: t.volumen.__setitem__("Variante B", 0.0)

    lauf.vor_teil = schaden
    with pytest.raises(BauAbbruch, match="Volumen"):
        bau.bauen(lauf.spec_pfad)
    assert lauf.teil.gespeichert == []


def test_aktive_konfiguration_wird_vor_dem_speichern_wiederhergestellt(lauf):
    """Plan Review Focus 4: Sonst öffnet der Kollege eine andere Variante."""
    lauf.aufnahme["aktiv"] = "Variante B"
    lauf.aufnahme["konfigurationen"] = ["Variante B", "Standard"]
    lauf.schreibe(MASS, UNTERDRUECKEN)
    bau.bauen(lauf.spec_pfad)
    assert lauf.teil.gespeichert == ["Variante B"]


def test_bau_ohne_freigabe(lauf):
    lauf.schreibe(MASS, freigeben=False)
    with pytest.raises(FreigabeFehler) as e:
        bau.bauen(lauf.spec_pfad)
    assert e.value.daten["code"] == "FREIGABE_FEHLT" and lauf.geoeffnet == []


def test_bau_kopie_veraendert(lauf):
    lauf.schreibe(MASS)
    os.chmod(lauf.kopie, stat.S_IWRITE)
    lauf.kopie.write_bytes(b"von Hand geaendert")
    with pytest.raises(BestandFehler) as e:
        bau.bauen(lauf.spec_pfad)
    assert e.value.daten["code"] == BESTAND_ABWEICHEND and lauf.geoeffnet == []
    assert not lauf_ordner(lauf.r, "A", 1).exists()


def test_bau_aufnahme_nicht_mehr_die_juengste(lauf):
    lauf.schreibe(MASS)
    ablage.bestand_ordner(lauf.r, "A", 2).mkdir()
    with pytest.raises(BestandFehler) as e:
        bau.bauen(lauf.spec_pfad)
    assert e.value.daten["code"] == "BESTAND_VERALTET" and lauf.geoeffnet == []


def test_bau_laed_die_genannte_aufnahme(lauf, monkeypatch):
    """Nie „die jüngste“ raten: Die Spec nennt die Nummer."""
    lauf.schreibe(MASS)
    gefragt = []
    laden = ablage.lade_aufnahme
    monkeypatch.setattr(spec_modul, "lade_aufnahme", lambda r, auftrag, n: (gefragt.append(n), laden(r, auftrag, n))[1])
    bau.bauen(lauf.spec_pfad)
    assert gefragt == [1]


def test_version_aelter_ohne_hochstufen(lauf):
    lauf.aufnahme["datei"]["version_aelter"] = True
    lauf.schreibe(MASS)
    with pytest.raises(BestandFehler) as e:
        bau.bauen(lauf.spec_pfad)
    assert e.value.daten["code"] == BESTAND_VERSION_AELTER and "--hochstufen" in str(e.value)
    assert lauf.geoeffnet == [] and not lauf_ordner(lauf.r, "A", 1).exists()


def test_version_aelter_mit_hochstufen(lauf):
    lauf.aufnahme["datei"]["version_aelter"] = True
    lauf.schreibe(MASS)
    assert bau.bauen(lauf.spec_pfad, hochstufen=True)["status"] == "ok"
    assert lauf.protokoll()["hochgestuft"] is True


def test_hochstufen_ohne_aeltere_datei_ist_kein_vermerk(lauf):
    lauf.schreibe(MASS)
    bau.bauen(lauf.spec_pfad, hochstufen=True)
    assert lauf.protokoll()["hochgestuft"] is False


def test_lizenz_im_protokoll(lauf):
    """Ruling 5. `GetLicenseType` gilt der Datei (bei kommerzieller Lizenz immer 0), `GetCurrentLicenseType` der Sitzung."""
    lauf.schreibe(MASS)
    lauf.vor_teil = lambda teil: setattr(teil, "lizenz", 0)
    bau.bauen(lauf.spec_pfad)
    assert lauf.protokoll()["lizenz"] == {"typ": 0, "name": "swLicenseType_Full",
                                          "sitzung": {"typ": 2, "name": "swLicenseType_Student"}}


def test_lizenz_nicht_lesbar_stoert_den_fertigen_lauf_nicht(lauf):
    lauf.schreibe(MASS)
    lauf.app = SimpleNamespace(CloseDoc=lambda t: None)
    assert bau.bauen(lauf.spec_pfad)["status"] == "ok"
    assert lauf.protokoll()["lizenz"] is None


def test_belegter_lauf(lauf):
    lauf.schreibe(MASS)
    lauf_ordner(lauf.r, "A", 3).mkdir(parents=True)
    with pytest.raises(compiler_bauen.SwkiFehler, match="Lauf 3 von A existiert schon"):
        bau.bauen(lauf.spec_pfad, lauf=3)
    assert lauf.geoeffnet == []


def test_zweiter_lauf_beginnt_wieder_ab_der_bestandskopie(lauf):
    lauf.schreibe(MASS)
    bau.bauen(lauf.spec_pfad)
    assert bau.bauen(lauf.spec_pfad)["lauf"] == 2
    assert lauf.geoeffnet == [lauf.lauf_datei(1), lauf.lauf_datei(2)]


def test_manuell_geaenderter_lauf_wird_erkannt(lauf):
    lauf.schreibe(MASS)
    bau.bauen(lauf.spec_pfad)
    lauf.lauf_datei(1).write_bytes(b"von Hand")
    with pytest.raises(compiler_bauen.SwkiFehler) as e:
        bau.bauen(lauf.spec_pfad)
    assert e.value.daten["code"] == "MANUELL_GEAENDERT"
    assert bau.bauen(lauf.spec_pfad, verwerfen=True)["lauf"] == 2
    assert lauf.protokoll(2)["verworfen"]["lauf"] == 1


def test_speichern_nur_im_arbeitsordner(lauf, tmp_path):
    fremd = tmp_path / "kunde" / "lauf-1" / "Teil.SLDPRT"
    teil = Teil(fremd)
    with pytest.raises(BauFehler) as e:
        sw_bestand.speichere_an_ort(teil, fremd)
    assert e.value.code == SPEICHERN_FEHLGESCHLAGEN and teil.gespeichert == []


def test_speichern_nur_im_lauf_ordner(lauf):
    """Die Bestandskopie liegt auch im Arbeitsordner, wird aber nie gespeichert."""
    teil = Teil(lauf.kopie)
    with pytest.raises(BauFehler):
        sw_bestand.speichere_an_ort(teil, lauf.kopie)
    assert teil.gespeichert == []


def test_speichern_nur_das_offene_dokument(lauf):
    ziel = lauf_ordner(lauf.r, "A", 1) / "Lagerdeckel.SLDPRT"
    ziel.parent.mkdir(parents=True)
    teil = Teil(ziel.with_name("Anderes.SLDPRT"))
    with pytest.raises(BauFehler):
        sw_bestand.speichere_an_ort(teil, ziel)
    assert teil.gespeichert == []


def test_speichern_fehler_von_solidworks(lauf):
    ziel = lauf_ordner(lauf.r, "A", 1) / "Lagerdeckel.SLDPRT"
    ziel.parent.mkdir(parents=True)
    teil = Teil(ziel)
    teil.Save3 = lambda o, e, w: False
    with pytest.raises(BauFehler) as e:
        sw_bestand.speichere_an_ort(teil, ziel)
    assert e.value.code == SPEICHERN_FEHLGESCHLAGEN


def test_speicherfehler_steht_im_protokoll(lauf):
    lauf.schreibe(MASS)

    def kaputt(teil):
        teil.Save3 = lambda o, e, w: False

    lauf.vor_teil = kaputt
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(lauf.spec_pfad)
    assert e.value.daten["fehler"]["code"] == SPEICHERN_FEHLGESCHLAGEN and lauf.geschlossen
    assert "punkt" not in e.value.daten["fehler"] and lauf.protokoll()["dateien"] == {}


def test_kontextfehler_schliesst_das_dokument(lauf):
    p = {"id": "p5", "typ": "feature", "name": "Neu",
         "feature": {"typ": "fase", "kanten": {"feature": "Weg", "auswahl": "alle_kanten"}}}
    lauf.schreibe(p)
    with pytest.raises(BauAbbruch):
        bau.bauen(lauf.spec_pfad)
    assert lauf.geschlossen and lauf.teil.gespeichert == []


def test_cli_weiche_mit_hochstufen(lauf, monkeypatch):
    aufrufe = []
    monkeypatch.setattr(bau, "bauen", lambda *a: aufrufe.append(a) or {"status": "ok"})
    lauf.schreibe(MASS)
    from swki.cli import main

    assert main(["bauen", str(lauf.spec_pfad), "--hochstufen", "--lauf", "4"]) == 0
    assert aufrufe == [(lauf.spec_pfad, 4, False, False, True)]


def test_weiche_ohne_feld_hochstufen(lauf, monkeypatch):
    """`swki durchlauf` übergibt ein eigenes Namespace ohne dieses Feld (Plan, Voraussetzung)."""
    aufrufe = []
    monkeypatch.setattr(bau, "bauen", lambda *a: aufrufe.append(a) or {"status": "ok"})
    lauf.schreibe(MASS)
    compiler_bauen._bauen(SimpleNamespace(spec=str(lauf.spec_pfad), lauf=None, verwerfen=False, uebernommen=False))
    assert aufrufe == [(lauf.spec_pfad, None, False, False, False)]
