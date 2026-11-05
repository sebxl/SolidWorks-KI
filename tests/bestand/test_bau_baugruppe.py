"""swki bauen für art: aenderung an einer Baugruppe ohne SolidWorks (Spec Bestandsdateien §6, §8.1, §8.3; Plan Etappe 2 Task 10):
Spec, Freigabe, Aufnahme, Kopien und Protokolle sind echt, die offenen Dokumente Attrappen. Ungemessen, S19 kann die Attrappe
korrigieren. Kern der Tests: Der Lauf entsteht aus einer frischen Kopie, erst die Teil-Scheiben, dann die Haupt-Punkte, und
gespeichert wird nur, was ein Punkt ändert, nie nach einem Fehler."""

import hashlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from swki.aenderungen import befund, sha256_datei
from swki.auftrag import lauf_datei, lauf_ordner
from swki.baugruppe import bau as baugruppe_bau
from swki.baugruppe.modell import Quelle
from swki.baugruppe.referenzen import TeilReferenz
from swki.bestand import ablage, bau, bau_baugruppe, pfade, punkte_baugruppe, spec as spec_modul, sw_bestand
from swki.bestand.bau_baugruppe import bauen_baugruppe, pruefe_stand_baugruppe
from swki.bestand.fehler import BESTAND_ABWEICHEND, BESTAND_PFAD_FREMD, BESTAND_VERSION_AELTER, BestandFehler
from swki.bestand.sw_baugruppe_bestand import lies_baugruppe
from swki.bestand.vergleich_baugruppe import (bekannte_fehler_baugruppe, neuer_verknuepfungsfehler, vergleiche_baugruppe,
                                              vergleiche_dateien)
from swki.cli import SwkiFehler
from swki.compiler.bauen import BauAbbruch
from swki.compiler.fehler import REBUILD_FEHLER, SPEICHERN_FEHLGESCHLAGEN, BauFehler
from swki.konfig import Rechner
from swki.pruefung.geometrie import Messgeometrie
from swki.pruefung.messen import SW_OPEN_READONLY
from swki.spec.freigabe import FreigabeFehler
from swki.spec.freigabe import freigeben as freigabe_ohne_pruefung
from tests.bestand.beispiel_aufnahme import aufnahme as beispiel
from tests.bestand.sw_attrappe import teil_aus
from tests.bestand.sw_attrappe_baugruppe import App, muster_baugruppe

HAUPT = "Haupt.SLDASM"
GRUND, SCHLITTEN = "teile/Grund.SLDPRT", "teile/Schlitten.SLDPRT"
WEITERE = ("Unter.SLDASM", GRUND, SCHLITTEN, "teile/Schraube.SLDPRT", "teile/Welle.SLDPRT")
MASS = {"id": "p1", "typ": "mass", "in_datei": GRUND, "mass": "D2@Skizze4", "alt": 40, "neu": 45}
MASS2 = {"id": "p2", "typ": "mass", "in_datei": SCHLITTEN, "mass": "D2@Skizze4", "alt": 40, "neu": 46}
EIGENSCHAFT = {"id": "s1", "typ": "eigenschaft", "name": "Revision", "neu": "B"}
WERT = {"id": "w1", "typ": "verknuepfung_wert", "verknuepfung": "Abstand1", "alt": 3, "neu": 4}
KONFIGURATIONEN = ("Standard", "Leicht")
ORIGINAL = "D:\\Kunde\\"


def inhalt(rel: str) -> bytes:
    return f"bestand {rel}".encode()


def sha_von(rel: str) -> str:
    return hashlib.sha256(inhalt(rel)).hexdigest()


class BauApp(App):
    """ISldWorks mit echten Teil-Attrappen: Geöffnet wird, was in der Aufnahme der Datei steht."""

    def __init__(self, original, referenzen, baugruppe_, teile):
        super().__init__(original, referenzen, baugruppe_)
        self.teile, self.modelle = teile, {}
        self.vor_teil = lambda rel, teil: None
        self.optionen = {}
        self.GetCurrentLicenseType = 2

    def OpenDoc6(self, pfad, typ, optionen, konfiguration, fehler, warnungen):
        p = Path(pfad)
        self.optionen[p.name] = optionen
        rel = next((r for r in self.teile if p.as_posix().endswith(f"/{r}")), None)
        if rel is None:
            dok = super().OpenDoc6(pfad, typ, optionen, konfiguration, fehler, warnungen)
            if p.name != self.original.name:
                dok.GetPartBox = lambda welt: (0.0,) * 6
            return dok
        assert p.read_bytes() == inhalt(rel) and p.stat().st_mode & stat.S_IWRITE  # frisch aus dem Bestand, beschreibbar
        self.geoeffnet.append(p)
        self.ereignisse.append(("offen", p.name))
        teil = self.modelle[rel] = teil_aus(self.teile[rel], p)
        self.vor_teil(rel, teil)
        self.offen.append(teil)
        return teil


def _teil_aufnahme(rel: str) -> dict:
    a = beispiel()
    a["datei"] = {"name": rel, "original": ORIGINAL + rel, "sha256": sha_von(rel), "versionen": ["18000[2025/268]"],
                  "version_aelter": False}
    a["reihenfolge"] = {k: [f["name"] for f in a["features"]] for k in a["konfigurationen"]}
    a["geometrie"] = {k: {"koerper": 1, "volumen": 1000.0, "box": [0] * 6, "schwerpunkt": [0] * 3} for k in a["konfigurationen"]}
    for m in a["masse"]:
        if m["name"] == "D2@Skizze4":
            m["werte"] = {"Standard": 40.0, "Variante B": 40.0}
    return a


class Lauf:
    """Auftrag A mit Aufnahme 1 der Musterbaugruppe: Bestandskopien, dateien.json, bestand.json, Aufnahme je Teil, Attrappe."""

    def __init__(self, tmp_path, monkeypatch, konfigurationen=KONFIGURATIONEN, aktiv=None, fehlerhaft=None):
        self.tmp_path, self.monkeypatch = tmp_path, monkeypatch
        self.r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
        for modul in (bau, bau_baugruppe, spec_modul, sw_bestand):
            monkeypatch.setattr(modul, "lade_rechner", lambda: self.r)
        standard = {"toleranzen": {"anker_mm": 0.01}}
        monkeypatch.setattr(bau, "lade_standard", lambda: standard)
        monkeypatch.setattr(bau_baugruppe, "lade_standard", lambda: standard)
        self.spec_pfad = tmp_path / "auftraege" / "A" / "aenderung.yaml"
        self.spec_pfad.parent.mkdir(parents=True)
        self.kunde = tmp_path / "kunde"
        self.asm = muster_baugruppe(tmp_path / "unbekannt", konfigurationen)
        self.asm.aktiv = aktiv or konfigurationen[0]
        if fehlerhaft is not None:
            fehlerhaft(self.asm)
        self.ordner = ablage.bestand_ordner(self.r, "A", 1)
        self.teile = {rel: _teil_aufnahme(rel) for rel in WEITERE if rel.endswith(".SLDPRT")}
        self.app = BauApp(self.kunde / HAUPT, [self.kunde / rel for rel in WEITERE], self.asm, self.teile)
        self.asm.Save3 = self._save3
        self.monkeypatch.setattr(bau_baugruppe, "verbinde", lambda jahr: self.app)
        self._lege_bestand_an()

    def _save3(self, optionen, fehler, warnungen):
        """`Save3` schreibt wirklich: Sonst sähe eine SHA-256 nie, dass die Hauptdatei gespeichert ist."""
        self.asm.gespeichert.append(self.asm.aktiv)
        Path(self.asm.GetPathName).write_bytes(b"gespeichert")
        return True

    def _lege_bestand_an(self) -> None:
        dateien = {}
        for rel in (HAUPT, *WEITERE):
            ziel = self.ordner / rel
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_bytes(inhalt(rel))
            os.chmod(ziel, stat.S_IREAD)
            dateien[rel] = {"original": ORIGINAL + rel, "sha256": sha_von(rel), "versionen": ["18000[2025/268]"],
                            "art": "baugruppe" if rel.endswith("ASM") else "teil", "version_aelter": False, "referenzen": []}
        dateien[HAUPT]["haupt"] = True
        self.dateien = dateien
        ablage.schreibe_dateien(self.r, "A", 1, dateien)
        gelesen = lies_baugruppe(self.app, self.asm, dateien=WEITERE, kollision=True)
        self.aufnahme = {**gelesen, "sw_jahr": 2025, "bewegungen": {},
                         "datei": {"name": HAUPT, "original": ORIGINAL + HAUPT, "sha256": sha_von(HAUPT),
                                   "versionen": ["18000[2025/268]"], "version_aelter": False},
                         "dateien": {rel: d for rel, d in dateien.items() if not d.get("haupt")}}
        for rel, a in self.teile.items():
            ablage.schreibe_datei_aufnahme(self.r, "A", 1, rel, a)

    def schreibe(self, *punkte, bereiche=None, pruefen=True):
        """Spec und Freigabe. `pruefen=False`: ohne Prüfung gegen die Aufnahme (Quellen sucht `validieren` in der Tabelle)."""
        ablage.schreibe_aufnahme(self.r, "A", 1, self.aufnahme)
        if bereiche is None:
            bereiche = [{"punkte": [p["id"]], "in_datei": p["in_datei"], "features": ["Fase3"]}
                        for p in punkte if "in_datei" in p]
        spec = {"art": "aenderung", "name": "Haupt_Rev", "bestand": {"datei": HAUPT, "sha256": sha_von(HAUPT), "aufnahme": 1},
                "parameter": {"RA": 12}, "punkte": list(punkte), "bereiche": bereiche}
        self.spec_pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
        if pruefen:
            spec_modul.freigeben(self.spec_pfad)
        else:
            freigabe_ohne_pruefung(self.spec_pfad, spec_modul.lade_aenderung(self.spec_pfad))
        return self.spec_pfad

    def baue(self, **argumente):
        return bau.bauen(self.spec_pfad, **argumente)

    def protokoll(self, lauf=1) -> dict:
        return json.loads(lauf_datei(self.spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))

    def lauf_pfad(self, rel: str, lauf=1) -> Path:
        return lauf_ordner(self.r, "A", lauf) / rel

    def lauf_inhalt(self, rel: str, lauf=1) -> bytes:
        return self.lauf_pfad(rel, lauf).read_bytes()

    def geoeffnet(self) -> list[str]:
        return [Path(p).name for p in self.app.geoeffnet]

    def teil(self, rel=GRUND):
        return self.app.modelle[rel]

    def teil_fehler(self, rel=GRUND) -> None:
        """Nach dem Setzen des Maßes hat die Datei einen neuen Neuaufbau-Fehler."""
        def vor_teil(name, teil):
            if name == rel:
                teil.bei_neuaufbau = lambda t: (t.fehler.__setitem__(t.aktiv, [("Fase3", 7, False)])
                                                if t.masse["D2@Skizze4"].gesetzt else None)

        self.app.vor_teil = vor_teil


@pytest.fixture
def lauf(tmp_path, monkeypatch):
    return Lauf(tmp_path, monkeypatch)


@pytest.fixture
def normteil(tmp_path, monkeypatch):
    """Normteil aus der Bibliothek; Quelle, Kontext und Bibliotheksvermerk ohne Tabelle und SolidWorks."""
    quelle = tmp_path / "bibliothek"
    quelle.mkdir()
    (quelle / "ISO4762_M5x20.sldprt").write_bytes(b"normteil")
    q = Quelle("normteil", {"art": "teil", "features": []}, norm="ISO 4762", groesse="M5", laenge=20.0,
               schluessel="ISO4762_M5x20")
    monkeypatch.setattr(punkte_baugruppe, "normteil_quelle", lambda quelle_, pfad: (q, []))
    monkeypatch.setattr(punkte_baugruppe.normteil_befehle, "hole",
                        lambda norm, groesse, variante: {"pfad": str(quelle / "ISO4762_M5x20.sldprt"), "gebaut": False})
    monkeypatch.setattr(punkte_baugruppe, "kontext_aus_datei", lambda app, model, spec, pfad, tol, protokoll:
                        SimpleNamespace(model=model, ergebnisse={}))
    monkeypatch.setattr(punkte_baugruppe, "lade_rechner", lambda: SimpleNamespace(sw_jahr=2025))
    monkeypatch.setattr(baugruppe_bau, "bibliotheksordner", lambda r: quelle)
    monkeypatch.setattr(baugruppe_bau, "lies_eintrag", lambda ordner, schluessel: {"pruefsumme": "xyz"})
    return quelle


NEU = {"id": "k1", "typ": "komponente_neu", "quelle": {"normteil": "ISO 4762 M5x20"}}
NEUE_DATEI = "ISO4762_M5x20.sldprt"
NEUE_KOMPONENTE = "ISO4762_M5x20-1"


# --- Reihenfolge -----------------------------------------------------------------------------------------------------------

def test_teil_scheiben_laufen_zuerst(lauf):
    """Präzisierung 6: Eine neue Verknüpfung kann an einem neuen Feature hängen, egal wie die Punkte in der Spec stehen."""
    lauf.schreibe(WERT, EIGENSCHAFT, MASS)
    aus = lauf.baue()
    assert aus["status"] == "ok"
    assert [k["id"] for k in aus["knoten"]] == ["p1", "w1", "s1"]
    ereignisse = lauf.app.ereignisse
    assert ereignisse.index(("zu", "Grund.SLDPRT")) < ereignisse.index(("offen", HAUPT))  # `ReplaceComponents2` schließt Dateien


def test_haupt_punkte_in_spec_reihenfolge(lauf):
    lauf.schreibe(EIGENSCHAFT, WERT)
    assert [k["id"] for k in lauf.baue()["knoten"]] == ["s1", "w1"]


def test_baugruppe_und_scheibe_oeffnen_sichtbar_und_beschreibbar(lauf):
    """Mit Fenster wie in Etappe 1, dort sind die Handler gemessen."""
    lauf.schreibe(MASS, EIGENSCHAFT)
    lauf.baue()
    assert lauf.app.sichtbarkeit == []  # `DocumentVisible` kommt nur beim Öffnen ohne Fenster
    assert not lauf.app.optionen[HAUPT] & SW_OPEN_READONLY and lauf.lauf_pfad(HAUPT).stat().st_mode & stat.S_IWRITE


def test_scheibe_mit_anderer_schreibweise_trifft_die_aufgenommene_datei(lauf):
    lauf.schreibe({**MASS, "in_datei": "TEILE\\grund.sldprt"}, pruefen=False,
                  bereiche=[{"punkte": ["p1"], "in_datei": GRUND, "features": ["Fase3"]}])
    aus = lauf.baue()
    assert list(aus["dateien"]) == ["haupt", f"geaendert:{GRUND}"]


# --- Was gespeichert wird --------------------------------------------------------------------------------------------------

def test_nur_geaenderte_dateien_werden_gespeichert(lauf):
    lauf.schreibe(MASS)
    lauf.baue()
    assert lauf.teil().gespeichert == ["Standard"]
    assert len(lauf.app.modelle) == 1  # kein anderes Teil geöffnet
    assert lauf.lauf_inhalt(GRUND) == b"gespeichert"
    for rel in (HAUPT, SCHLITTEN, "Unter.SLDASM", "teile/Schraube.SLDPRT", "teile/Welle.SLDPRT"):
        assert sha256_datei(lauf.lauf_pfad(rel)) == sha_von(rel)


def test_haupt_bleibt_ungespeichert_ohne_baugruppen_punkt(lauf):
    """Sie wird trotzdem geöffnet und neu aufgebaut: Nur so zeigen sich Verknüpfungsfehler, die das geänderte Teil auslöst."""
    lauf.schreibe(MASS)
    aus = lauf.baue()
    assert lauf.asm.gespeichert == [] and aus["status"] == "ok"
    assert HAUPT in lauf.geoeffnet() and set(lauf.asm.neuaufbauten) >= set(KONFIGURATIONEN)
    assert ("zu", HAUPT) in lauf.app.ereignisse


def test_ungespeicherte_haupt_mit_neuem_fehler_bricht_ab(lauf):
    """Das geänderte Teil bricht eine Verknüpfung: Das Teil ist gespeichert, der Lauf gilt trotzdem nicht."""
    lauf.schreibe(MASS)
    lauf.asm.mates[0].GetErrorCode2 = lambda warnung: 7
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert e.value.daten["fehler"]["code"] == REBUILD_FEHLER and lauf.asm.gespeichert == []


def test_haupt_wird_gespeichert_mit_lage_folgen(lauf):
    """Die Lage von Komponenten steckt in der Baugruppe: Ohne Speichern ginge sie verloren."""
    lauf.schreibe({**MASS, "lage_folgen": ["Grund-1"]})
    aus = lauf.baue()
    assert lauf.asm.gespeichert == ["Standard"] and aus["dateien"]["haupt"] == str(lauf.lauf_pfad(HAUPT))


def test_haupt_wird_gespeichert_mit_baugruppen_punkt(lauf):
    lauf.schreibe(WERT)
    aus = lauf.baue()
    assert lauf.asm.gespeichert == ["Standard"] and lauf.lauf_inhalt(HAUPT) == b"gespeichert"
    assert aus["dateien"] == {"haupt": str(lauf.lauf_pfad(HAUPT))}


def test_eigenschaft_an_der_baugruppe_laeuft_ueber_den_teil_handler(lauf):
    lauf.schreibe(EIGENSCHAFT)
    assert lauf.baue()["status"] == "ok"
    assert lauf.asm.eigenschaften[""]["Revision"] == "B" and lauf.asm.gespeichert == ["Standard"]


def test_teil_typ_ohne_in_datei_laeuft_nie_an_der_baugruppe(lauf):
    """`bauen` validiert nicht: Eine alte Freigabe darf keinen Teil-Handler auf die Baugruppe loslassen."""
    lauf.schreibe({"id": "p1", "typ": "unterdruecken", "feature": "Fase3"}, pruefen=False, bereiche=[])
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert e.value.daten["fehler"]["punkt"] == "p1" and lauf.asm.gespeichert == []


# --- Nach einem Fehler -----------------------------------------------------------------------------------------------------

def test_fehler_in_scheibe_speichert_die_baugruppe_nicht(lauf):
    lauf.schreibe(MASS, WERT)
    lauf.teil_fehler()
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    d = e.value.daten
    assert d["fehler"]["punkt"] == "p1" and d["fehler"]["code"] == REBUILD_FEHLER
    assert [(k["id"], k["status"]) for k in d["knoten"]] == [("p1", "fehler"), ("w1", "uebersprungen")]
    assert HAUPT not in lauf.geoeffnet() and lauf.asm.gespeichert == []
    assert lauf.teil().gespeichert == [] and lauf.lauf_inhalt(GRUND) == inhalt(GRUND)


def test_fehler_in_scheibe_stoppt_die_uebrigen_scheiben(lauf):
    lauf.schreibe(MASS, MASS2)
    lauf.teil_fehler()
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert [(k["id"], k["status"]) for k in e.value.daten["knoten"]] == [("p1", "fehler"), ("p2", "uebersprungen")]
    assert "Schlitten.SLDPRT" not in lauf.geoeffnet()


def test_spaetere_scheibe_scheitert_die_fruehere_bleibt_im_lauf_ordner(lauf):
    """Der Lauf-Ordner bleibt liegen, der nächste beginnt ab dem Bestand; nur das Protokoll sagt, was er wert ist."""
    lauf.schreibe(MASS, MASS2)
    lauf.teil_fehler(SCHLITTEN)
    with pytest.raises(BauAbbruch):
        lauf.baue()
    p = lauf.protokoll()
    assert lauf.lauf_inhalt(GRUND) == b"gespeichert"
    assert p["status"] == "fehler" and p["dateien"] == {} and p["sha256"] == {}


def test_fehler_im_baugruppen_punkt_speichert_nicht(lauf):
    """Ein gesteuerter Wert kommt still nicht an; die Teil-Scheibe davor bleibt gespeichert, die Baugruppe nicht."""
    lauf.schreibe(MASS, WERT, EIGENSCHAFT)
    lauf.asm.mates[1].gesteuert = True
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    d = e.value.daten
    assert d["fehler"]["punkt"] == "w1"
    assert [(k["id"], k["status"]) for k in d["knoten"]] == [("p1", "ok"), ("w1", "fehler"), ("s1", "uebersprungen")]
    assert lauf.asm.gespeichert == [] and lauf.lauf_inhalt(HAUPT) == inhalt(HAUPT)
    assert ("zu", HAUPT) in lauf.app.ereignisse


def test_speicherfehler_der_baugruppe_steht_im_protokoll(lauf):
    lauf.schreibe(WERT)
    lauf.asm.Save3 = lambda o, e, w: False
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert e.value.daten["fehler"]["code"] == SPEICHERN_FEHLGESCHLAGEN and "punkt" not in e.value.daten["fehler"]
    assert lauf.protokoll()["status"] == "fehler" and ("zu", HAUPT) in lauf.app.ereignisse


def test_neuer_verknuepfungsfehler_bricht_ab(lauf):
    """Der Fehler sitzt an einer Verknüpfung, die kein Punkt nennt, und nur in der anderen Konfiguration."""
    lauf.schreibe(WERT)
    fremd = lauf.asm.mates[0]
    fremd.GetErrorCode2 = lambda warnung: 12 if lauf.asm.aktiv == "Leicht" else 0
    with pytest.raises(BauAbbruch, match="Hub") as e:
        lauf.baue()
    assert e.value.daten["fehler"]["code"] == REBUILD_FEHLER and lauf.asm.gespeichert == []
    assert "Leicht" in e.value.daten["fehler"]["meldung"]


def test_neuer_fehler_laut_whats_wrong_bricht_beim_punkt_ab(lauf):
    lauf.schreibe(WERT, EIGENSCHAFT)
    kette = lauf.asm.neuaufbauten

    def rebuild_bricht(nur_oben=False):
        kette.append(lauf.asm.aktiv)
        lauf.asm.fehler[lauf.asm.aktiv] = [("Abstand1", 9)]
        return True

    lauf.asm.ForceRebuild3 = rebuild_bricht
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert e.value.daten["fehler"]["punkt"] == "w1" and lauf.asm.gespeichert == []


def test_bekannter_verknuepfungsfehler_bricht_nicht_ab(tmp_path, monkeypatch):
    """Review Focus 5: Der Bestand ist schon nicht sauber, das fällt nicht dem Lauf zur Last."""
    def kaputt(asm):
        asm.mates[0].code = 12
        asm.fehler = {"Standard": [("Hub", 12)], "Leicht": [("Hub", 12)]}

    lauf = Lauf(tmp_path, monkeypatch, fehlerhaft=kaputt)
    lauf.schreibe(WERT, EIGENSCHAFT)
    assert lauf.baue()["status"] == "ok"
    assert lauf.asm.gespeichert == ["Standard"]


def test_bekannter_fehler_nur_an_der_verknuepfung_gelesen_bricht_nicht_ab(lauf):
    """`GetErrorCode2` kannte ihn schon, `GetWhatsWrong` nennt ihn erst im Lauf: Bekannt ist er trotzdem."""
    lauf.asm.mates[0].code = 12
    lauf.aufnahme["verknuepfungen"]["Hub"]["fehler"] = {"Standard": 12, "Leicht": 12}
    lauf.asm.fehler = {"Standard": [("Hub", 12)], "Leicht": [("Hub", 12)]}
    lauf.schreibe(WERT)
    assert lauf.baue()["status"] == "ok"


def test_anderer_code_an_bekannter_verknuepfung_ist_neu(lauf):
    lauf.asm.mates[0].code = 13
    lauf.aufnahme["verknuepfungen"]["Hub"]["fehler"] = {"Standard": 12, "Leicht": 12}
    lauf.schreibe(WERT)
    with pytest.raises(BauAbbruch, match="Hub"):
        lauf.baue()
    assert lauf.asm.gespeichert == []


def test_alles_in_offen_wird_geschlossen_auch_nach_einem_fehler(lauf, normteil):
    lauf.schreibe(NEU, WERT, pruefen=False)
    lauf.asm.mates[1].gesteuert = True
    with pytest.raises(BauAbbruch):
        lauf.baue()
    assert ("zu", NEUE_DATEI) in lauf.app.ereignisse and ("zu", HAUPT) in lauf.app.ereignisse
    assert lauf.app.offen == []


def test_fehler_beim_holen_schliesst_und_oeffnet_die_baugruppe_nicht(lauf, normteil, monkeypatch):
    def scheitert(*_):
        raise punkte_baugruppe.NormteilFehler("NORMTEIL_UNBEKANNT", "gibt es nicht")

    monkeypatch.setattr(punkte_baugruppe.normteil_befehle, "hole", scheitert)
    lauf.schreibe(NEU, pruefen=False)
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert e.value.daten["fehler"]["code"] == "NORMTEIL_UNBEKANNT" and HAUPT not in lauf.geoeffnet()
    assert [(k["id"], k["status"]) for k in e.value.daten["knoten"]] == [("k1", "uebersprungen")]


def test_schliessfehler_verdeckt_den_baufehler_nicht(lauf):
    lauf.schreibe(WERT)
    lauf.asm.mates[1].gesteuert = True

    def schliesse(titel):
        raise OSError("Schließen kaputt")

    lauf.app.CloseDoc = schliesse
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert e.value.daten["fehler"]["punkt"] == "w1"


def test_schliessfehler_nach_dem_speichern_steht_im_protokoll(lauf):
    lauf.schreibe(WERT)

    def schliesse(titel):
        raise OSError("Schließen kaputt")

    lauf.app.CloseDoc = schliesse
    with pytest.raises(BauAbbruch, match="Schließen kaputt"):
        lauf.baue()
    assert lauf.protokoll()["status"] == "fehler"


def test_protokoll_steht_auch_wenn_das_kopieren_scheitert(lauf, monkeypatch):
    """Minor aus Task 8: Ein Ordner ohne Protokoll sperrte den Auftrag mit BESTAND_AUFTRAG_BELEGT."""
    lauf.schreibe(MASS)

    def scheitert(quelle, dateien, ziel):
        ziel.mkdir(parents=True)
        raise OSError("Platte voll")

    monkeypatch.setattr(bau_baugruppe, "lauf_kopie_alle", scheitert)
    with pytest.raises(BauAbbruch, match="Platte voll"):
        lauf.baue()
    assert ablage.spec_laeufe(lauf.r, "A") == []
    assert (lauf_ordner(lauf.r, "A", 1) / "protokoll.json").is_file()


# --- Pfadschutz ------------------------------------------------------------------------------------------------------------

def test_pfadschutz_vor_dem_bau(lauf):
    """Sperre 1 greift, bevor der erste Punkt läuft: Eine Teil-Scheibe wäre sonst schon gespeichert."""
    lauf.schreibe(MASS, WERT)
    fremd = str(lauf.kunde / "teile" / "Fremd.SLDPRT")
    lauf.app.GetDocumentDependencies2 = lambda pfad, *rest: ("Fremd.SLDPRT", fremd) if pfad.endswith(HAUPT) else None
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert e.value.daten["fehler"]["code"] == BESTAND_PFAD_FREMD and fremd in e.value.daten["fehler"]["meldung"]
    assert lauf.app.geoeffnet == [] and lauf.lauf_inhalt(GRUND) == inhalt(GRUND)
    assert [k["status"] for k in e.value.daten["knoten"]] == ["uebersprungen", "uebersprungen"]
    assert ablage.spec_laeufe(lauf.r, "A") == []


def test_pfadschutz_nach_dem_oeffnen_speichert_nicht(lauf):
    """Sperre 2: Die Baugruppe lädt doch vom gespeicherten Pfad; sie wird ohne Speichern geschlossen."""
    lauf.schreibe(WERT)
    lauf.asm.pfade_wie_gespeichert = lauf.kunde
    lauf.asm.vom_original.add("Schraube-1")
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert e.value.daten["fehler"]["code"] == BESTAND_PFAD_FREMD
    assert lauf.asm.gespeichert == [] and ("zu", HAUPT) in lauf.app.ereignisse


# --- Lauf und Bestand ------------------------------------------------------------------------------------------------------

def test_lauf_startet_immer_aus_dem_bestand(lauf):
    """Die Attrappe prüft beim Öffnen den Inhalt: Lauf 2 sieht nichts von dem, was Lauf 1 gespeichert hat."""
    lauf.schreibe(MASS, EIGENSCHAFT)
    lauf.baue()
    assert lauf.lauf_inhalt(GRUND, 1) == b"gespeichert"
    assert lauf.baue()["lauf"] == 2
    assert lauf.app.geoeffnet[-2:] == [lauf.lauf_pfad(GRUND, 2), lauf.lauf_pfad(HAUPT, 2)]
    for rel in (HAUPT, *WEITERE):
        assert (lauf.ordner / rel).read_bytes() == inhalt(rel) and not (lauf.ordner / rel).stat().st_mode & stat.S_IWRITE


def test_lauf_ordner_traegt_alle_dateien(lauf):
    lauf.schreibe(MASS)
    lauf.baue()
    assert all(lauf.lauf_pfad(rel).is_file() for rel in (HAUPT, *WEITERE))


def test_bestandsdatei_veraendert(lauf):
    lauf.schreibe(MASS)
    ziel = lauf.ordner / "teile" / "Schraube.SLDPRT"
    os.chmod(ziel, stat.S_IWRITE)
    ziel.write_bytes(b"von Hand")
    with pytest.raises(BestandFehler) as e:
        lauf.baue()
    assert e.value.daten["code"] == BESTAND_ABWEICHEND and "Schraube" in str(e.value)
    assert lauf.app.geoeffnet == [] and not lauf_ordner(lauf.r, "A", 1).exists()


def test_bestandsdatei_fehlt(lauf):
    lauf.schreibe(MASS)
    ziel = lauf.ordner / "Unter.SLDASM"
    os.chmod(ziel, stat.S_IWRITE)
    ziel.unlink()
    with pytest.raises(BestandFehler) as e:
        lauf.baue()
    assert e.value.daten["code"] == BESTAND_ABWEICHEND and not lauf_ordner(lauf.r, "A", 1).exists()


def test_dateien_json_passt_nicht_zur_aufnahme(lauf):
    lauf.schreibe(MASS)
    dateien = ablage.lade_dateien(lauf.r, "A", 1)
    dateien.pop("teile/Welle.SLDPRT")
    ablage.schreibe_dateien(lauf.r, "A", 1, dateien)
    with pytest.raises(BestandFehler) as e:
        lauf.baue()
    assert e.value.daten["code"] == BESTAND_ABWEICHEND


def test_bau_ohne_freigabe(lauf):
    lauf.schreibe(MASS)
    lauf.spec_pfad.write_text(lauf.spec_pfad.read_text(encoding="utf-8").replace("neu: 45", "neu: 47"), encoding="utf-8")
    with pytest.raises(FreigabeFehler):
        lauf.baue()
    assert lauf.app.geoeffnet == []


def test_protokoll_traegt_alle_shas(lauf, normteil):
    lauf.schreibe(MASS, NEU, pruefen=False)
    aus = lauf.baue()
    p = lauf.protokoll()
    assert set(p["sha256"]) == {HAUPT, *WEITERE, NEUE_DATEI}
    assert p["sha256"][GRUND] == hashlib.sha256(b"gespeichert").hexdigest()
    assert p["sha256"][NEUE_DATEI] == hashlib.sha256(b"normteil").hexdigest()
    assert p["sha256"]["teile/Welle.SLDPRT"] == sha_von("teile/Welle.SLDPRT")
    soll = {"haupt": str(lauf.lauf_pfad(HAUPT)), f"geaendert:{GRUND}": str(lauf.lauf_pfad(GRUND))}
    assert p["dateien"] == aus["dateien"] == soll
    assert p["neue"] == {"k1": [NEUE_KOMPONENTE]} and p["ersetzt"] == {} and p["neue_dateien"] == [NEUE_DATEI]
    assert p["bestand"] == {"sha256": sha_von(HAUPT), "aufnahme": 1}
    assert "ISO4762_M5x20" in p["normteile"]
    assert {"kopieren", "teile", "dateien", "vorbereiten", "bauen", "speichern"} <= set(p["messung"])
    assert all("s" in e and "mb" in e for e in p["messung"].values())


def test_protokoll_ersetzt_nennt_alt_und_neu(lauf, normteil):
    lauf.schreibe({"id": "e1", "typ": "komponente_ersetzen", "komponente": "Schraube-1", "quelle": NEU["quelle"]}, pruefen=False)
    lauf.baue()
    p = lauf.protokoll()
    assert p["ersetzt"] == {"Schraube-1": NEUE_KOMPONENTE} and p["neue"] == {"e1": [NEUE_KOMPONENTE]}


def test_protokoll_lizenz(lauf):
    lauf.schreibe(WERT)
    lauf.asm.Extension.GetLicenseType = 0
    lauf.baue()
    assert lauf.protokoll()["lizenz"]["sitzung"]["typ"] == 2 and lauf.protokoll()["lizenz"]["datei"]["typ"] == 0


def test_abbruch_traegt_den_vermerk_der_aufnahme(lauf):
    lauf.schreibe(MASS)
    lauf.teil_fehler()
    with pytest.raises(BauAbbruch):
        lauf.baue()
    assert lauf.protokoll()["bestand"] == {"sha256": sha_von(HAUPT), "aufnahme": 1}
    assert ablage.spec_laeufe(lauf.r, "A") == []
    assert (lauf_ordner(lauf.r, "A", 1) / "protokoll.json").is_file()


def test_aktive_konfiguration_wie_aufgenommen(tmp_path, monkeypatch):
    """Sonst öffnet der Kollege eine andere Variante: Die aktive kommt zuletzt und steht beim Speichern."""
    lauf = Lauf(tmp_path, monkeypatch, aktiv="Leicht")
    lauf.schreibe(WERT, EIGENSCHAFT)
    lauf.baue()
    assert lauf.asm.gespeichert == ["Leicht"]
    assert lauf.aufnahme["aktiv"] == "Leicht"


def test_manuell_geaendert_gilt_wie_bisher(lauf):
    """`protokoll.sha256` deckt alle Dateien: Auch eine Datei, die kein Punkt nennt, zählt."""
    lauf.schreibe(MASS)
    lauf.baue()
    lauf.lauf_pfad("teile/Welle.SLDPRT").write_bytes(b"von Hand")
    with pytest.raises(SwkiFehler) as e:
        lauf.baue()
    assert e.value.daten["code"] == "MANUELL_GEAENDERT" and "teile/Welle.SLDPRT" in e.value.daten["geaendert"]
    assert lauf.baue(verwerfen=True)["lauf"] == 2
    assert lauf.protokoll(2)["verworfen"]["lauf"] == 1


def test_fehlerhafter_lauf_loest_kein_manuell_geaendert_aus(lauf):
    lauf.schreibe(MASS)
    lauf.teil_fehler()
    with pytest.raises(BauAbbruch):
        lauf.baue()
    lauf.app.vor_teil = lambda rel, teil: None
    assert lauf.baue()["lauf"] == 2


def test_belegter_lauf(lauf):
    lauf.schreibe(MASS)
    lauf_ordner(lauf.r, "A", 3).mkdir(parents=True)
    with pytest.raises(SwkiFehler, match="Lauf 3 von A existiert schon"):
        lauf.baue(lauf=3)


# --- Version ---------------------------------------------------------------------------------------------------------------

def test_aeltere_datei_ohne_punkt_stoert_nicht(lauf):
    lauf.aufnahme["dateien"]["teile/Schraube.SLDPRT"]["version_aelter"] = True
    lauf.schreibe(MASS)
    assert lauf.baue()["status"] == "ok"
    assert lauf.protokoll()["hochgestuft"] is False


def test_aeltere_haupt_ungespeichert_stoert_nicht(lauf):
    lauf.aufnahme["datei"]["version_aelter"] = True
    lauf.schreibe(MASS)
    assert lauf.baue()["status"] == "ok"


def test_aeltere_datei_mit_punkt_verlangt_hochstufen(lauf):
    lauf.aufnahme["dateien"][GRUND]["version_aelter"] = True
    lauf.schreibe(MASS)
    with pytest.raises(BestandFehler) as e:
        lauf.baue()
    assert e.value.daten["code"] == BESTAND_VERSION_AELTER and GRUND in str(e.value) and "--hochstufen" in str(e.value)
    assert lauf.app.geoeffnet == [] and not lauf_ordner(lauf.r, "A", 1).exists()
    assert lauf.baue(hochstufen=True)["status"] == "ok"
    assert lauf.protokoll()["hochgestuft"] is True


def test_aeltere_haupt_gespeichert_verlangt_hochstufen(lauf):
    lauf.aufnahme["datei"]["version_aelter"] = True
    lauf.schreibe(WERT)
    with pytest.raises(BestandFehler) as e:
        lauf.baue()
    assert e.value.daten["code"] == BESTAND_VERSION_AELTER and HAUPT in str(e.value)


# --- Vertrag mit swki pruefen -----------------------------------------------------------------------------------------------

@pytest.fixture
def anker(monkeypatch):
    """`loese_im_teil` ohne Geometrie."""
    def loese(ctx, seite):
        return TeilReferenz(SimpleNamespace(name=f"Fläche {seite}"), Messgeometrie("ebene", (0, 0, 0), (0, 0, 1)), False)

    monkeypatch.setattr(punkte_baugruppe, "loese_im_teil", loese)


def skript_punkt(lauf, text: str) -> dict:
    (lauf.spec_pfad.parent / "s.py").write_text(text, encoding="utf-8")
    return {"id": "x1", "typ": "skript", "datei": "s.py", "luecke": "Test"}


def vertrag(lauf) -> None:
    """Was `swki pruefen` (Task 11) aus dem Protokoll liest, muss zum Lauf passen: jeder Eintrag von `vergleiche_dateien` und
    `vergleiche_baugruppe` steht auf `ok: True`, und die Änderungserkennung schweigt."""
    assert lauf.baue()["status"] == "ok"
    p = lauf.protokoll()
    spec = spec_modul.lade_aenderung(lauf.spec_pfad)
    nachher = lies_baugruppe(lauf.app, lauf.asm, dateien=WEITERE, kollision=True)
    eintraege = [vergleiche_dateien(spec, ablage.lade_dateien(lauf.r, "A", 1), p["sha256"], p["neue_dateien"]),
                 *vergleiche_baugruppe(spec, lauf.aufnahme, nachher, p["neue"], p["ersetzt"], p["neue_dateien"])]
    assert not [e for e in eintraege if e["ok"] is not True]
    assert befund(lauf.r, "A", lauf.spec_pfad) is None


ERSETZEN = {"id": "e1", "typ": "komponente_ersetzen", "komponente": "Schraube-1", "quelle": NEU["quelle"]}
VERKNUEPFUNG_NEU = {"id": "v1", "typ": "verknuepfung_neu", "art": "abstand", "wert": 12,
                    "a": {"komponente": "Grund-1", "nahe": [0, 0, 0]}, "b": {"komponente": "Schraube-2", "nahe": [0, 0, 0]}}


def test_vertrag_nur_teil(lauf):
    lauf.schreibe(MASS)
    vertrag(lauf)


def test_vertrag_lage_folgen(lauf):
    lauf.schreibe({**MASS, "lage_folgen": ["Grund-1"]})
    vertrag(lauf)


def test_vertrag_eigenschaft(lauf):
    lauf.schreibe(EIGENSCHAFT)
    vertrag(lauf)


def test_vertrag_skript(lauf):
    lauf.schreibe(skript_punkt(lauf, "def bauen(ctx):\n    return None\n"), pruefen=False, bereiche=[])
    vertrag(lauf)


def test_vertrag_komponente_neu_aus_quelle(lauf, normteil):
    lauf.schreibe(NEU, pruefen=False)
    vertrag(lauf)


def test_vertrag_komponente_neu_wie(lauf):
    lauf.schreibe({"id": "k1", "typ": "komponente_neu", "wie": "Schraube-1"}, pruefen=False)
    vertrag(lauf)


def test_vertrag_komponente_ersetzen(lauf, normteil):
    lauf.schreibe(ERSETZEN, pruefen=False)
    vertrag(lauf)


def test_vertrag_komponente_entfernen(lauf):
    lauf.schreibe({"id": "e1", "typ": "komponente_entfernen", "komponente": "Schraube-1", "verknuepfungen": ["Abstand1"]},
                  pruefen=False)
    vertrag(lauf)


def test_vertrag_verknuepfung_neu(lauf, anker):
    lauf.schreibe(VERKNUEPFUNG_NEU, pruefen=False)
    vertrag(lauf)


def test_vertrag_verknuepfung_wert(lauf):
    lauf.schreibe(WERT)
    vertrag(lauf)


def test_vertrag_verknuepfung_loeschen(lauf):
    lauf.schreibe({"id": "l1", "typ": "verknuepfung_loeschen", "verknuepfung": "Deckungsgleich1"}, pruefen=False)
    vertrag(lauf)


def test_vertrag_alles_zusammen(lauf, normteil, anker):
    lauf.schreibe(WERT, MASS, NEU, ERSETZEN | {"komponente": "Schraube-2"},
                  VERKNUEPFUNG_NEU | {"b": {"komponente": "k1", "nahe": [0, 0, 0]}}, EIGENSCHAFT,
                  {"id": "l1", "typ": "verknuepfung_loeschen", "verknuepfung": "Deckungsgleich1"}, pruefen=False)
    vertrag(lauf)


# --- Skript an der Hauptbaugruppe -------------------------------------------------------------------------------------------

def test_skript_nimmt_eine_verknuepfung_speichert_nicht(lauf):
    """Auch ein Skript darf nichts aus dem Bestand verschwinden lassen."""
    lauf.schreibe(skript_punkt(lauf, "def bauen(ctx):\n    ctx.model.mates.pop()\n"), pruefen=False, bereiche=[])
    with pytest.raises(BauAbbruch, match="Deckungsgleich1") as e:
        lauf.baue()
    assert e.value.daten["fehler"]["schritt"] == "stand" and lauf.asm.gespeichert == []


def test_skript_scheitert_mit_punkt_id(lauf):
    punkt = skript_punkt(lauf, "def bauen(ctx):\n    raise ValueError('kaputt')\n")
    lauf.schreibe(punkt, EIGENSCHAFT, pruefen=False, bereiche=[])
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    d = e.value.daten
    assert d["fehler"]["punkt"] == "x1" and lauf.asm.gespeichert == []
    assert [(k["id"], k["status"]) for k in d["knoten"]] == [("x1", "fehler"), ("s1", "uebersprungen")]


# --- Korrekturrunde: Abbrüche, die im Protokoll stehen müssen ------------------------------------------------------------------

def test_pruefsummen_scheitern_das_protokoll_steht_trotzdem(lauf, monkeypatch):
    """Sperrt jemand eine Datei nach dem Schließen, sperrte ein Ordner ohne Protokoll den Auftrag für `aufnehmen`."""
    lauf.schreibe(MASS)

    def wirft(ordner, dateien):
        raise PermissionError("gesperrt")

    monkeypatch.setattr(bau_baugruppe, "pruefsummen", wirft)
    with pytest.raises(BauAbbruch, match="gesperrt") as e:
        lauf.baue()
    assert e.value.daten["fehler"]["code"] == "PermissionError"
    p = lauf.protokoll()
    assert p["status"] == "fehler" and p["dateien"] == {} and p["sha256"] == {}
    assert ablage.spec_laeufe(lauf.r, "A") == []


def test_sperre_2_nach_gespeicherter_scheibe(lauf):
    """Die Scheibe ist gespeichert, die Baugruppe wird abgewiesen: Nichts mehr speichern, der Lauf gilt nicht."""
    lauf.schreibe(MASS, WERT)
    lauf.asm.pfade_wie_gespeichert = lauf.kunde
    lauf.asm.vom_original.add("Schraube-1")
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    p = lauf.protokoll()
    assert e.value.daten["fehler"]["code"] == BESTAND_PFAD_FREMD and "punkt" not in e.value.daten["fehler"]
    assert p["status"] == "fehler" and p["sha256"] == {} and p["dateien"] == {}
    assert [(k["id"], k["status"]) for k in p["knoten"]] == [("p1", "ok"), ("w1", "uebersprungen")]
    assert lauf.lauf_inhalt(GRUND) == b"gespeichert" and lauf.asm.gespeichert == [] and lauf.app.offen == []


def test_fehlgeschlagenes_schliessen_nach_sperre_2_steht_im_protokoll(lauf):
    """Das Dokument ist noch offen: `fehler_dict` allein verlöre das."""
    lauf.schreibe(WERT)
    lauf.asm.pfade_wie_gespeichert = lauf.kunde
    lauf.asm.vom_original.add("Schraube-1")

    def schliesse(titel):
        raise OSError("Schließen kaputt")

    lauf.app.CloseDoc = schliesse
    with pytest.raises(BauAbbruch):
        lauf.baue()
    f = lauf.protokoll()["fehler"]
    assert f["code"] == BESTAND_PFAD_FREMD and "Schließen kaputt" in f["schliessen_fehlgeschlagen"]


def test_fehler_der_scheibe_nennt_die_datei(lauf):
    """Der Stand kennt keine Datei: `Konfiguration Variante B` allein sagt bei zwei Scheiben nichts."""
    lauf.schreibe(MASS, MASS2)
    aufnahme = ablage.lade_datei_aufnahme(lauf.r, "A", 1, SCHLITTEN)
    aufnahme["reihenfolge"] = {k: ["GibtEsNicht"] for k in aufnahme["konfigurationen"]}
    ablage.schreibe_datei_aufnahme(lauf.r, "A", 1, SCHLITTEN, aufnahme)
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    f = e.value.daten["fehler"]
    assert SCHLITTEN in f["meldung"] and f["code"] == REBUILD_FEHLER and f["schritt"] == "stand"


def test_oeffnen_der_scheibe_scheitert_nennt_die_datei_und_behaelt_den_code(lauf, monkeypatch):
    lauf.schreibe(MASS)
    roh = bau_baugruppe.oeffne_in

    def oeffne_in(app, pfad, wurzel, sichtbar=False, nur_lesen=True):
        if pfad.suffix == ".SLDPRT":
            raise BestandFehler(BESTAND_PFAD_FREMD, "fremd", schliessen_fehlgeschlagen="offen")
        return roh(app, pfad, wurzel, sichtbar, nur_lesen)

    monkeypatch.setattr(bau_baugruppe, "oeffne_in", oeffne_in)
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    f = e.value.daten["fehler"]
    assert f["code"] == BESTAND_PFAD_FREMD and f["meldung"] == f"{GRUND}: fremd" and HAUPT not in lauf.geoeffnet()
    assert f["schliessen_fehlgeschlagen"] == "offen"  # die Datei in der Meldung kostet das Feld nicht


def test_schliessfehler_der_scheibe_verdeckt_den_baufehler_nicht(lauf):
    lauf.schreibe(MASS)
    lauf.teil_fehler()

    def schliesse(titel):
        raise OSError("Schließen kaputt")

    lauf.app.CloseDoc = schliesse
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    f = e.value.daten["fehler"]
    assert f["code"] == REBUILD_FEHLER and f["punkt"] == "p1" and GRUND in f["meldung"]


def test_schliessfehler_nach_gespeicherter_scheibe_nennt_die_datei(lauf):
    lauf.schreibe(MASS, WERT)

    def schliesse(titel):
        raise OSError("Schließen kaputt")

    lauf.app.CloseDoc = schliesse
    with pytest.raises(BauAbbruch) as e:
        lauf.baue()
    assert f"{GRUND}: Schließen kaputt" == e.value.daten["fehler"]["meldung"] and HAUPT not in lauf.geoeffnet()


def test_messung_fuehrt_jede_scheibe(lauf):
    lauf.schreibe(MASS, MASS2)
    lauf.baue()
    m = lauf.protokoll()["messung"]
    assert all({"s", "mb"} <= set(m[f"teile:{rel}"]) for rel in (GRUND, SCHLITTEN)) and "teile" in m


# --- Gemeinsame Regeln -----------------------------------------------------------------------------------------------------

def test_bekannte_fehler_aus_neuaufbau_und_verknuepfungen():
    aufnahme = {"neuaufbau": [{"konfiguration": "A", "feature": "F1", "code": 1, "warnung": False},
                              {"konfiguration": "A", "feature": "F2", "code": 1, "warnung": True},
                              {"konfiguration": "B", "feature": "F3", "code": 1, "warnung": False}],
                "verknuepfungen": {"M1": {"fehler": {"A": 7, "B": 0}}, "M2": {"fehler": {"A": 0, "B": 7}},
                                   "M3": {"fehler": None}}}
    assert bekannte_fehler_baugruppe(aufnahme, "A") == {"F1", "M1"}
    assert bekannte_fehler_baugruppe(aufnahme, "B") == {"F3", "M2"}
    assert bekannte_fehler_baugruppe({}, "A") == set()


@pytest.mark.parametrize("vorher, code, text", [({"fehler": {"A": 7}}, 7, None), ({"fehler": {"A": 7}}, 8, "Fehler 8 in A"),
                                                ({"fehler": {"A": 0}}, 0, None), ({"fehler": {"A": 0}}, 7, "Fehler 7 in A"),
                                                ({"fehler": {"B": 7}}, 7, "Fehler 7 in A"), (None, 0, None),
                                                (None, 7, "Fehler 7 in A"), (None, None, "Fehlercode in A nicht lesbar")])
def test_neuer_verknuepfungsfehler(vorher, code, text):
    assert neuer_verknuepfungsfehler(vorher, {"fehler": {"A": code}}, "A") == text


# --- Weiche ----------------------------------------------------------------------------------------------------------------

def test_weiche_nach_der_art_der_aufnahme(lauf, monkeypatch):
    aufrufe = []
    monkeypatch.setattr(bau_baugruppe, "bauen_baugruppe", lambda *a: aufrufe.append(a) or {"status": "ok"})
    lauf.schreibe(MASS)
    assert lauf.baue(lauf=7, hochstufen=True) == {"status": "ok"}
    pfad, spec, aufnahme, *rest = aufrufe[0]
    assert pfad == lauf.spec_pfad.resolve() and spec["name"] == "Haupt_Rev" and aufnahme["art"] == "baugruppe"
    assert rest == [7, False, False, True]


# --- pruefe_stand_baugruppe ------------------------------------------------------------------------------------------------

@pytest.fixture
def stand(lauf):
    """Die Baugruppe offen im Lauf, unverändert; `spec` trägt nur `punkte`."""
    lauf.asm.wurzel = lauf.tmp_path / "unbekannt"
    return lauf


def _pruefe(stand, *punkte, neue=None):
    pruefe_stand_baugruppe(stand.asm, stand.aufnahme, {"punkte": list(punkte), "parameter": {}}, neue or {})


def test_stand_prueft_den_pfadschutz_nach_jedem_wechsel(stand, tmp_path):
    """§8.1a nach S19c: Aktiv unterdrückt, in `Leicht` lädt Schraube-1 vom gespeicherten Pfad; die Baugruppe ging über
    `oeffne_in` auf, nach dem Wechsel sperrt die zweite Sperre."""
    stand.asm.komp("Schraube-1").unterdrueckt.add("Standard")
    stand.asm.pfade_wie_gespeichert, stand.asm.vom_original = tmp_path / "kunde", {"Schraube-1"}
    ordner = stand.asm.wurzel
    (ordner / "teile").mkdir(parents=True, exist_ok=True)
    stand.app.GetDocumentDependencies2 = lambda pfad, *rest: ("Schraube", str(ordner / "teile" / "Schraube.SLDPRT"))
    stand.app.baugruppe = stand.asm
    asm = pfade.oeffne_in(stand.app, ordner / HAUPT, ordner)
    with pytest.raises(BestandFehler) as e:
        _pruefe(stand)
    assert e.value.daten["code"] == BESTAND_PFAD_FREMD and "Umschalten auf Leicht" in e.value.daten["wo"] and asm is stand.asm


def test_stand_unveraendert_besteht_und_endet_in_der_aktiven(stand):
    gesehen = []
    rebuild = stand.asm.ForceRebuild3
    stand.asm.ForceRebuild3 = lambda nur_oben: (gesehen.append(stand.asm.aktiv), rebuild(nur_oben))[1]
    _pruefe(stand)
    assert gesehen == ["Leicht", "Standard"] and stand.asm.aktiv == "Standard"


def test_stand_rebuild_ohne_meldung_ist_ein_fehler(stand):
    stand.asm.ForceRebuild3 = lambda nur_oben: False
    with pytest.raises(BauFehler) as e:
        _pruefe(stand)
    assert e.value.code == REBUILD_FEHLER and e.value.schritt == "stand"


def test_stand_rebuild_false_mit_bekanntem_fehler_besteht(stand):
    stand.aufnahme["neuaufbau"] = [{"konfiguration": k, "feature": "Hub", "code": 12, "warnung": False} for k in KONFIGURATIONEN]
    stand.asm.fehler = {k: [("Hub", 12)] for k in KONFIGURATIONEN}
    stand.asm.ForceRebuild3 = lambda nur_oben: False
    _pruefe(stand)


def test_stand_neuer_fehler_in_der_anderen_konfiguration(stand):
    stand.asm.fehler = {"Leicht": [("Abstand1", 9)]}
    with pytest.raises(BauFehler, match="Leicht"):
        _pruefe(stand)


def test_stand_nicht_lesbarer_fehlercode_zaehlt_als_fehler(stand):
    def wirft(warnung):
        raise RuntimeError("nicht lesbar")

    stand.asm.mates[1].GetErrorCode2 = wirft
    with pytest.raises(BauFehler, match="Abstand1"):
        _pruefe(stand)


def test_stand_bestandskomponente_verschwunden(stand):
    stand.asm.entferne(stand.asm.komp("Schraube-5"))
    with pytest.raises(BauFehler, match="Schraube-5"):
        _pruefe(stand)


def test_stand_bestandsverknuepfung_verschwunden(stand):
    stand.asm.mates = stand.asm.mates[:-1]
    with pytest.raises(BauFehler, match="Deckungsgleich1"):
        _pruefe(stand)


def test_stand_bestandsfeature_verschwunden(stand):
    stand.aufnahme["reihenfolge"] = {k: ["Ebene vorne", "Ebene oben"] for k in KONFIGURATIONEN}
    with pytest.raises(BauFehler, match="Ebene oben"):
        _pruefe(stand)


def test_stand_entfernt_gilt_mit_kindern_und_verknuepfungen(stand):
    stand.asm.entferne(stand.asm.komp("Unter-1"))
    stand.asm.entferne(stand.asm.komp("Schraube-1"))
    _pruefe(stand, {"id": "e1", "typ": "komponente_entfernen", "komponente": "Unter-1", "verknuepfungen": []},
            {"id": "e2", "typ": "komponente_entfernen", "komponente": "Schraube-1", "verknuepfungen": ["Abstand1"]})


def test_stand_entfernte_komponente_ist_wieder_da(stand):
    with pytest.raises(BauFehler, match="Schraube-1"):
        _pruefe(stand, {"id": "e1", "typ": "komponente_entfernen", "komponente": "Schraube-1", "verknuepfungen": []})


def test_stand_mitgenannte_verknuepfung_steht_noch(stand):
    stand.asm.komponenten.remove(stand.asm.komp("Schraube-1"))
    with pytest.raises(BauFehler, match="Abstand1"):
        _pruefe(stand, {"id": "e1", "typ": "komponente_entfernen", "komponente": "Schraube-1", "verknuepfungen": ["Abstand1"]})


def test_stand_neue_komponente_fehlt(stand):
    with pytest.raises(BauFehler, match="Neu-1"):
        _pruefe(stand, NEU, neue={"k1": ["Neu-1"]})


def test_stand_neue_komponente_ohne_namen_im_protokoll(stand):
    with pytest.raises(BauFehler, match="k1"):
        _pruefe(stand, NEU)


def test_stand_neue_komponente_unterdrueckt_in_einer_konfiguration(stand):
    stand.asm.komponente("Neu-1", "Neu.SLDPRT").unterdrueckt.add("Leicht")
    with pytest.raises(BauFehler, match="Neu-1.*Leicht"):
        _pruefe(stand, NEU, neue={"k1": ["Neu-1"]})


def test_stand_ersetzt_alt_weg_neu_da(stand):
    p = {"id": "e1", "typ": "komponente_ersetzen", "komponente": "Schraube-1", "quelle": NEU["quelle"]}
    with pytest.raises(BauFehler, match="Schraube-1"):
        _pruefe(stand, p, neue={"e1": ["Grund-1"]})
    stand.asm.komp("Schraube-1").Name2 = "Neu-1"
    _pruefe(stand, p, neue={"e1": ["Neu-1"]})


def test_stand_ersetzt_ohne_namen(stand):
    stand.asm.komp("Schraube-1").Name2 = "Neu-1"
    p = {"id": "e1", "typ": "komponente_ersetzen", "komponente": "Schraube-1", "quelle": NEU["quelle"]}
    with pytest.raises(BauFehler, match="e1"):
        _pruefe(stand, p)


def _neue_mate(stand, name="v1", typ=5, wert=0.012):
    return stand.asm.mate(name, typ, [stand.asm.seite("Grund-1"), stand.asm.seite("Schraube-2")], wert=wert)


VERKNUEPFUNG = {"id": "v1", "typ": "verknuepfung_neu", "art": "abstand", "wert": 12,
                "a": {"komponente": "Grund-1", "nahe": [0, 0, 0]}, "b": {"komponente": "Schraube-2", "nahe": [0, 0, 0]}}


def test_stand_neue_verknuepfung_steht(stand):
    _neue_mate(stand)
    _pruefe(stand, VERKNUEPFUNG)


def test_stand_neue_verknuepfung_fehlt(stand):
    with pytest.raises(BauFehler, match="v1"):
        _pruefe(stand, VERKNUEPFUNG)


def test_stand_neue_verknuepfung_unterdrueckt(stand):
    _neue_mate(stand).unterdrueckt.add("Leicht")
    with pytest.raises(BauFehler, match="v1.*Leicht"):
        _pruefe(stand, VERKNUEPFUNG)


def test_stand_neue_verknuepfung_anderer_wert(stand):
    _neue_mate(stand, wert=0.013)
    with pytest.raises(BauFehler, match="v1"):
        _pruefe(stand, VERKNUEPFUNG)


def test_stand_neue_verknuepfung_mit_fehler(stand):
    _neue_mate(stand).code = 7
    with pytest.raises(BauFehler, match="v1"):
        _pruefe(stand, VERKNUEPFUNG)


def test_stand_scharnier_braucht_beide(stand):
    _neue_mate(stand, typ=1, wert=None)
    p = {**VERKNUEPFUNG, "art": "scharnier", "anlage_a": VERKNUEPFUNG["a"], "anlage_b": VERKNUEPFUNG["b"]}
    p.pop("wert")
    with pytest.raises(BauFehler, match="v1.anlage"):
        _pruefe(stand, p)


def test_stand_verknuepfung_wert_steht_in_den_genannten(stand):
    mate = stand.asm.mates[1]
    mate.je_konfiguration = {"Standard": 0.004, "Leicht": 0.003}
    _pruefe(stand, {**WERT, "konfigurationen": ["Standard"]})
    with pytest.raises(BauFehler, match="Abstand1"):
        _pruefe(stand, WERT)


def test_stand_grenze_steht(stand):
    p = {"id": "w2", "typ": "verknuepfung_wert", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30}
    with pytest.raises(BauFehler, match="Hub"):
        _pruefe(stand, p)
    _pruefe(stand, {**p, "neu": 25})


def test_stand_geloeschte_verknuepfung_ist_noch_da(stand):
    with pytest.raises(BauFehler, match="Abstand1"):
        _pruefe(stand, {"id": "l1", "typ": "verknuepfung_loeschen", "verknuepfung": "Abstand1"})


def test_stand_geloeschte_verknuepfung_ist_weg(stand):
    stand.asm.mates.remove(stand.asm.mates[1])
    _pruefe(stand, {"id": "l1", "typ": "verknuepfung_loeschen", "verknuepfung": "Abstand1"})

