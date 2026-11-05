"""swki pruefen für art: aenderung an einer Baugruppe ohne SolidWorks (Spec Bestandsdateien §7, §8.3, §8.4; Plan Etappe 2 Task 11): Spec,
Freigabe, Aufnahme, Bau, Kopien, Protokoll und Bericht sind echt, offen sind nur Attrappen. Ungemessen, S19 kann sie korrigieren. Kern:
Nur Dateien mit geänderter SHA-256 werden als Teil verglichen, Bestand und Lauf sind nie zugleich offen, nichts wird gespeichert, und
ein Lauf besteht nur, was nachgewiesen ist."""

import copy
import hashlib
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from swki import durchlauf as d
from swki.aenderungen import sha256_datei
from swki.auftrag import lauf_datei, lauf_ordner
from swki.baugruppe import sw_bewegung
from swki.baugruppe.bewegungslauf import SpeicherKnapp
from swki.bestand import ablage, ausgabe as ausgabe_modul, pruefen as pruefen_modul, pruefen_baugruppe as modul, punkte_baugruppe
from swki.bestand import spec as spec_modul
from swki.bestand.bewegung_bestand import fahre_bestand, grenzen_der_aufnahme, statische_paare
from swki.bestand.differenz import Abweichung
from swki.bestand.fehler import BESTAND_ABWEICHEND, BESTAND_PFAD_FREMD, BestandFehler
from swki.bestand.sw_baugruppe_bestand import VERKNUEPFUNG_UNERREICHT, mechanik_fuer
from swki.compiler.fehler import REBUILD_FEHLER, BauFehler
from swki.pruefung import befehle
from swki.pruefung.bewertung import Messwerte
from swki.pruefung.messen import SW_OPEN_READONLY
from swki.pruefung.schleife import lies_laeufe
from tests.bestand.sw_attrappe_baugruppe import App, Interferenz, Kollisionen, Mate
from tests.bestand.test_bau_baugruppe import (EIGENSCHAFT, GRUND, HAUPT, MASS, MASS2, NEU, NEUE_DATEI, NEUE_KOMPONENTE, SCHLITTEN, WERT, Lauf,
                                              normteil)  # noqa: F401
from tests.bestand.test_pruefen import Umgebung
from tests.bestand.test_spec_baugruppe import TEIL_PUNKT, freigabe_der_teil_quelle, schreibe_teil

STANDARD = {"toleranzen": {"anker_mm": 0.01, "volumen_prozent": 0.5}, "bewegung_schritte": 4, "speicher_grenze_mb": 16000,
            "max_nachbesserungen": 3, "gleichungen": False}
DECKEL = "Deckel2.SLDPRT"
IM_BEREICH = [-40.0, 10.0, 10.0, -30.0, 20.0, 20.0]
BOX = {"min": [-50, 0, 0], "max": [-20, 40, 20]}
BEREICH = [{"punkte": ["p1"], "in_datei": GRUND, "box": BOX}]
BEREICHE = [*BEREICH, {"punkte": ["p2"], "in_datei": SCHLITTEN, "box": BOX}]


class Pruefung(Lauf):
    """Der Lauf-Aufbau aus `test_bau_baugruppe`, dazu `bewegungen` und Bilder der Aufnahme, und ein Öffnen, das beim Prüfen aufpasst."""

    def __init__(self, tmp_path, monkeypatch, zusatz=0, **k):
        self.zusatz = zusatz
        super().__init__(tmp_path, monkeypatch, **k)
        for m in (pruefen_modul, ausgabe_modul):
            monkeypatch.setattr(m, "lade_rechner", lambda: self.r)
        monkeypatch.setattr(pruefen_modul, "lade_standard", lambda: STANDARD)
        monkeypatch.setattr(befehle, "lade_standard", lambda: STANDARD)
        monkeypatch.setattr(befehle, "_compiler_aenderungen", lambda seit: [])
        monkeypatch.setattr(modul, "verbinde", lambda jahr: self.app)
        monkeypatch.setattr(pruefen_modul, "lies_bestand", self._lies)
        monkeypatch.setattr(pruefen_modul, "koerper_differenz", self._differenz)
        monkeypatch.setattr(pruefen_modul, "alle_feature_boxen", lambda modelle, konfigurationen, namen: {})
        monkeypatch.setattr(pruefen_modul, "screenshots", self._screenshots)
        monkeypatch.setattr(modul, "screenshots", self._screenshots)
        monkeypatch.setattr(sw_bewegung, "iso_bild", lambda app, model, pfad: str(pfad))
        self.verlauf, self.bilder, self.gelesen = [], [], []
        self.abweichung = [Abweichung("hinzu", IM_BEREICH, 500.0)]
        self.oeffnen_bau = self.app.OpenDoc6

    def _lege_bestand_an(self) -> None:
        super()._lege_bestand_an()
        for rel, a in self.teile.items():
            a["eigenschaften"]["konfiguration"]["Variante B"] = {}
            ablage.schreibe_datei_aufnahme(self.r, "A", 1, rel, a)
        for n in range(self.zusatz):
            self._weitere_datei(f"teile/Zusatz{n}.SLDPRT")
        ablage.schreibe_dateien(self.r, "A", 1, self.dateien)
        schlitten = self.asm.komp("Schlitten-1")
        lagen = copy.deepcopy(schlitten.lagen)
        grenzen = grenzen_der_aufnahme(self.aufnahme)
        self.aufnahme["bewegungen"] = fahre_bestand(mechanik_fuer(self.app, self.asm, grenzen, self.aufnahme, None), self.aufnahme,
                                                    grenzen, 4, statische_paare(self.aufnahme), 16000, 0.01)
        schlitten.lagen = lagen
        bilder = self.ordner / "bilder"
        bilder.mkdir()
        for name in ("iso", "vorne"):
            (bilder / f"{name}.png").write_bytes(b"bild")
        ablage.schreibe_datei_aufnahme(self.r, "A", 1, "Unter.SLDASM", {"warnungen": []})

    def _weitere_datei(self, rel: str) -> None:
        ziel = self.ordner / rel
        ziel.write_bytes(rel.encode())
        os.chmod(ziel, stat.S_IREAD)
        eintrag = {"original": f"D:\\Kunde\\{rel}", "sha256": hashlib.sha256(rel.encode()).hexdigest(), "versionen": ["18000[2025/268]"],
                   "art": "teil", "version_aelter": False, "referenzen": []}
        self.dateien[rel] = eintrag
        self.aufnahme["dateien"][rel] = eintrag

    def _rel(self, pfad: Path) -> str:
        return Path(pfad).relative_to(self.lauf_pfad("")).as_posix()

    def _lies(self, app, model):
        rel = self._rel(model.GetPathName)
        self.gelesen.append(rel)
        nachher = copy.deepcopy(self.teile[rel])
        del nachher["datei"]
        for m in nachher["masse"]:
            if m["name"] == "D2@Skizze4":
                soll = next(p["neu"] for p in (MASS, MASS2) if p["in_datei"] == rel)
                m["werte"] = dict.fromkeys(m["werte"], float(soll))
        return nachher

    def _differenz(self, app, a, b, konfiguration):
        return list(self.abweichung)

    def _screenshots(self, app, model, ordner):
        if model is self.asm:
            self.aufgebaut_beim_bild = self.asm.aktiv in self.asm.aufgebaut
        self.bilder.append((model.GetTitle, Path(ordner)))
        return {"iso": str(Path(ordner) / "iso.png"), "vorne": str(Path(ordner) / "vorne.png")}

    def _oeffne_beim_pruefen(self, pfad, typ, optionen, konfiguration, fehler, warnungen):
        """Scheitert wie SolidWorks an gleichen Namen und nennt jeden Verstoß gegen die Regeln des Prüfens."""
        p = Path(pfad)
        assert optionen & SW_OPEN_READONLY, f"{p.name}: Prüfen öffnet nur lesend (Spec §7)"
        offen = [Path(x.GetPathName) for x in self.app.offen]
        assert p.name.lower() not in [o.name.lower() for o in offen], "SolidWorks öffnet zwei gleichnamige Dokumente nicht zugleich"
        assert not any(o.suffix == ".SLDASM" for o in offen) and (not offen or p.suffix != ".SLDASM"), "Teile vor der Baugruppe, je einzeln"
        assert p.is_relative_to(self.lauf_pfad("")), f"{p}: Geprüft wird im Lauf-Ordner, die Bestandskopie bleibt zu"
        self.verlauf.append(self._rel(p))
        return App.OpenDoc6(self.app, pfad, typ, optionen, konfiguration, fehler, warnungen)

    def gebaut(self, *punkte, bereiche=BEREICH):
        self.schreibe(*(punkte or (MASS,)), bereiche=bereiche)
        assert self.baue()["status"] == "ok"
        return self.spec_pfad

    def pruefe(self, lauf=1):
        self.app.OpenDoc6 = self._oeffne_beim_pruefen
        try:
            return pruefen_modul.pruefen(self.spec_pfad, lauf)
        finally:
            self.app.OpenDoc6 = self.oeffnen_bau

    def bericht_datei(self, lauf=1) -> dict:
        return json.loads(lauf_datei(self.spec_pfad, lauf, "pruefbericht").read_text(encoding="utf-8"))


@pytest.fixture
def u(tmp_path, monkeypatch):
    return Pruefung(tmp_path, monkeypatch)


def ids(bericht: dict) -> dict[str, dict]:
    return {e["id"]: e for e in bericht["pruefungen"]}


# --- Bestanden ---------------------------------------------------------------------------------------------------------------

def test_neuaufbau_vor_bildern_und_fahrt(u):
    """Teil geändert, Baugruppe ungespeichert: Das zweite Öffnen zeigte sonst den alten Stand."""
    u.gebaut()
    u.pruefe()
    assert u.aufgebaut_beim_bild is True


def test_ohne_mangel_bestanden(u):
    u.gebaut(MASS, EIGENSCHAFT)
    b = u.pruefe()
    assert b["bestanden"] is True, b["maengel"]
    assert b["maengel"] == [] and b["lauf"] == 1 and b["datei"] == str(u.lauf_pfad(HAUPT))
    alle = ids(b)
    for pid in ("pfade", "dateien", "komponenten", "verknuepfungen", "bestimmtheit", "kollision", "lage", "punkt:p1", "punkt:s1",
                "baum", "masse", "gleichungen", "konfigurationen", "eigenschaften", "neuaufbau", "externe_referenzen",
                "bewegung:Hub", f"{GRUND}/baum", f"{GRUND}/masse"):
        assert alle[pid]["ok"] is True, alle[pid]


def test_ok_none_ist_nicht_bestanden(u):
    u.aufnahme["kollisionen"] = None  # „nicht gelesen“ in der Aufnahme
    u.gebaut()
    b = u.pruefe()
    assert b["bestanden"] is False and ids(b)["kollision"]["ok"] is None
    assert [m for m in b["maengel"] if m["pruefung"] == "kollision"][0]["nicht_nachgewiesen"] is True
    assert lies_laeufe(u.spec_pfad)[0]["code_maengel"] == 1


def test_neue_kollision_ist_mangel(u):
    u.gebaut()
    u.asm.kollisionen = Kollisionen(1, [Interferenz(("Grund-1", "Schraube-2"), 2.0)])
    b = u.pruefe()
    assert b["bestanden"] is False and ids(b)["kollision"]["ok"] is False


# --- Nur geänderte Dateien --------------------------------------------------------------------------------------------------

def test_nur_geaenderte_teile_werden_verglichen(tmp_path, monkeypatch):
    """Lauf 30 hat rund 35 Dateien, eine davon ändert ein Punkt: eine `vorher_`-Kopie, ein Vergleich."""
    u = Pruefung(tmp_path, monkeypatch, zusatz=29)
    assert len(u.dateien) == 35
    u.gebaut()
    b = u.pruefe()
    assert b["bestanden"] is True, b["maengel"]
    assert [p.name for p in (u.lauf_pfad("vergleich")).glob("vorher_*")] == ["vorher_teile_Grund.SLDPRT"]
    assert u.gelesen == [GRUND] and b["dateien"]["geaendert"] == [GRUND] and list(b["differenzen"]) == [GRUND]


def test_vorher_kopie_steht_in_keiner_pruefsumme(u):
    u.gebaut()
    u.pruefe()
    assert not [rel for rel in u.protokoll()["sha256"] if "vorher_" in rel]
    assert (u.lauf_pfad("vergleich") / "vorher_teile_Grund.SLDPRT").read_bytes() != b"gespeichert"


def test_zwei_teile_je_eine_scheibe(u):
    u.gebaut(MASS, MASS2, bereiche=BEREICHE)
    b = u.pruefe()
    assert b["bestanden"] is True, b["maengel"]
    assert sorted(b["differenzen"]) == [GRUND, SCHLITTEN] and b["differenzen"][GRUND]["Standard"][0]["bereich"] == 0
    assert [x for x in u.verlauf if "Grund" in x and "vorher" not in x][:1] == [GRUND]


def test_datei_ohne_punkt_geaendert_ist_mangel_ohne_teilpruefung(u):
    u.gebaut()
    u.lauf_pfad("teile/Schraube.SLDPRT").write_bytes(b"nebenbei gespeichert")
    b = u.pruefe()
    e = ids(b)["dateien"]
    assert b["bestanden"] is False and e["ok"] is False and "teile/Schraube.SLDPRT" in e["hinweis"]
    assert "teile/Schraube.SLDPRT" not in u.gelesen and list(b["differenzen"]) == [GRUND]


def test_datei_mit_punkt_unveraendert_laesst_den_punkt_nicht_stumm(u):
    u.gebaut()
    u.lauf_pfad(GRUND).write_bytes(u.ordner.joinpath(GRUND).read_bytes())
    b = u.pruefe()
    assert ids(b)["punkt:p1"]["ok"] is False and ids(b)["dateien"]["ok"] is False and u.gelesen == [] and b["bestanden"] is False


def test_fehlende_lauf_datei_ist_nie_gleich(u):
    """Fehlt eine Datei im Lauf, lösen die Suchregeln aufs Original auf (S19c P.c3, die Attrappe seit Task 13 ebenso): Sperre 1
    öffnet die Baugruppe nicht (§8.1a), die Prüfung bricht ab statt zu bestehen."""
    u.gebaut()
    u.lauf_pfad(GRUND).unlink()
    with pytest.raises(BestandFehler) as e:
        u.pruefe()
    assert e.value.daten["code"] == BESTAND_PFAD_FREMD and GRUND.split("/")[-1] in str(e.value)


# --- Präfixe, Hauptdatei ------------------------------------------------------------------------------------------------------

def test_teilpruefungen_tragen_die_datei_ausser_punkten(u):
    u.gebaut()
    b = u.pruefe()
    alle = ids(b)
    assert "punkt:p1" in alle and f"{GRUND}/punkt:p1" not in alle and f"{GRUND}/skizzen" in alle
    assert [e["konfiguration"] for e in b["pruefungen"] if e["id"] == f"{GRUND}/bereich"] == ["Standard", "Variante B"]
    assert not [e["id"] for e in b["pruefungen"] if e["id"] in ("bereich", "volumen_delta")]
    assert all(e["id"].startswith((f"{GRUND}/", "punkt:")) or "/" not in e["id"] for e in alle.values())


def test_teilmangel_nennt_datei_und_punkt(u):
    u.gebaut()
    u.abweichung = [Abweichung("hinzu", [100.0, 100.0, 100.0, 110.0, 110.0, 110.0], 500.0)]  # außerhalb aller Bereiche
    b = u.pruefe()
    assert b["bestanden"] is False and any(m["pruefung"] == f"{GRUND}/bereich" for m in b["maengel"])


def test_baugruppen_punkt_kommt_nicht_in_den_vergleich_der_hauptdatei(u):
    u.gebaut(WERT, EIGENSCHAFT, bereiche=[])
    b = u.pruefe()
    alle = ids(b)
    assert b["bestanden"] is True, b["maengel"]
    assert alle["punkt:w1"]["ok"] is True and "wird nicht verglichen" not in alle["punkt:w1"].get("hinweis", "")
    assert [e["id"] for e in b["pruefungen"]].count("punkt:w1") == 1


def test_eigenschaft_an_der_hauptdatei_wird_nachgemessen(u):
    u.gebaut(MASS, EIGENSCHAFT)
    u.asm.eigenschaften.get("", {}).pop("Revision", None)
    b = u.pruefe()
    assert ids(b)["punkt:s1"]["ok"] is False and ids(b)["punkt:s1"]["knoten"] == ["s1"]


def test_skript_an_der_hauptbaugruppe_mit_bereich_ist_nicht_nachgewiesen(u):
    """Die Baugruppe hat keine Körper-Differenz: `ok: True` belegte einen Bereich, den niemand gemessen hat."""
    skript = {"id": "sk", "typ": "skript", "datei": "skripte/s.py", "luecke": "x"}
    datei = u.spec_pfad.parent / "skripte" / "s.py"
    datei.parent.mkdir()
    datei.write_text("def bauen(ctx):\n    return []\n", encoding="utf-8")
    u.gebaut(skript, bereiche=[{"punkte": ["sk"], "box": BOX}])
    b = u.pruefe()
    assert ids(b)["punkt:sk"]["ok"] is None and "Bereich" in ids(b)["punkt:sk"]["hinweis"] and b["bestanden"] is False


# --- Offen und geschlossen ---------------------------------------------------------------------------------------------------

def test_bestand_und_lauf_nie_zugleich_offen(u):
    """Die Regeln stehen in `_oeffne_beim_pruefen`; hier die Reihenfolge und dass am Ende nichts offen bleibt."""
    u.gebaut()
    beginn = len(u.app.ereignisse)
    u.pruefe()
    assert u.verlauf[:2] == ["vergleich/vorher_teile_Grund.SLDPRT", GRUND] and u.verlauf[-1] == HAUPT
    assert u.app.offen == [] and u.verlauf.count(HAUPT) == 2
    ereignisse = u.app.ereignisse[beginn:]
    assert all(ereignisse.index(("zu", titel)) < ereignisse.index(("offen", HAUPT)) for titel in ("vorher_teile_Grund.SLDPRT", "Grund.SLDPRT"))
    assert ("offen", "Grund.SLDPRT") not in [e for e in ereignisse[ereignisse.index(("offen", HAUPT)):]]


def test_lesen_unsichtbar_bilder_mit_fenster(u):
    u.gebaut()
    vorher = len(u.app.sichtbarkeit)
    u.pruefe()
    assert u.app.sichtbarkeit[vorher:].count(False) == 3  # Vorher-Kopie, Teil, Baugruppe; je mit dem Zurückschalten
    assert u.bilder[0] == ("Grund.SLDPRT", u.lauf_pfad("bilder") / "teile_Grund.SLDPRT")
    assert u.bilder[1] == ("vorher_teile_Grund.SLDPRT", u.lauf_pfad("vergleich") / "bilder" / "teile_Grund.SLDPRT")
    assert u.bilder[2] == (HAUPT, u.lauf_pfad("bilder"))


def test_kein_dokument_wird_gespeichert(u):
    u.gebaut(MASS, EIGENSCHAFT)
    vorher = {rel: sha256_datei(u.lauf_pfad(rel)) for rel in u.protokoll()["sha256"]}
    u.asm.Save3 = lambda *a: pytest.fail("Prüfen speichert nie")
    u.pruefe()
    assert {rel: sha256_datei(u.lauf_pfad(rel)) for rel in vorher} == vorher


def test_baugruppe_geht_auch_nach_einem_lesefehler_zu(u, monkeypatch):
    u.gebaut()
    monkeypatch.setattr(modul, "lies_baugruppe", lambda *a, **k: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        u.pruefe()
    assert u.app.offen == []


def test_pfad_fremd_bricht_ohne_bericht_ab(u, tmp_path):
    u.gebaut()
    u.asm.vom_original.add("Grund-1")
    u.asm.pfade_wie_gespeichert = tmp_path / "kunde"
    with pytest.raises(BestandFehler) as e:
        u.pruefe()
    assert e.value.daten["code"] == BESTAND_PFAD_FREMD and not lauf_datei(u.spec_pfad, 1, "pruefbericht").exists() and u.app.offen == []


def test_bestandskopie_veraendert(u):
    u.gebaut()
    ziel = u.ordner / GRUND
    os.chmod(ziel, stat.S_IWRITE)
    ziel.write_bytes(b"jemand war hier")
    with pytest.raises(BestandFehler) as e:
        u.pruefe()
    assert e.value.daten["code"] == BESTAND_ABWEICHEND and u.app.offen == []


def test_lauf_ohne_hauptdatei(u):
    u.gebaut()
    u.lauf_pfad(HAUPT).unlink()
    with pytest.raises(pruefen_modul.SwkiFehler, match="fehlt"):
        u.pruefe()


# --- Bewegung -----------------------------------------------------------------------------------------------------------------

def test_bewegung_laeuft_und_steht_im_bericht(u):
    u.gebaut()
    b = u.pruefe()
    hub = b["bewegungen"]["Hub"]
    assert hub["gefahren"] is True and hub["stellungen"] == 5 and hub["bewegt"] == ["Schlitten-1"]
    alle = ids(b)
    assert alle["bewegung:Hub"]["ok"] is True and alle["bewegung_menge:Hub"]["ok"] is True and alle["bewegung_kollision:Hub"]["ok"] is True
    assert sorted(b["bilder_bewegung"]) == ["Hub-max", "Hub-min", "Hub-mitte"]
    assert b["bilder_bewegung"]["Hub-min"] == str(u.lauf_pfad("bilder") / "Hub-min.png")


def test_ohne_grenze_keine_fahrt(u):
    """Die Grenze fehlt im Lauf: keine Mechanik, und was im Bestand fuhr, ist ein Mangel."""
    u.gebaut()
    u.asm.mates = [m for m in u.asm.mates if m.Name != "Hub"]
    b = u.pruefe()
    assert b["bewegungen"] == {} and ids(b)["bewegung:Hub"]["ok"] is False and ids(b)["verknuepfungen"]["ok"] is False


def test_speicher_knapp_bricht_ab(u, monkeypatch):
    u.gebaut()
    monkeypatch.setattr(sw_bewegung, "privat_mb", lambda pid: 20000.0)
    with pytest.raises(SpeicherKnapp):
        u.pruefe()
    assert not lauf_datei(u.spec_pfad, 1, "pruefbericht").exists() and u.app.offen == []


def test_speicher_zu_beginn_zaehlt_fuer_frisch(u, monkeypatch):
    u.gebaut()
    monkeypatch.setattr(sw_bewegung, "privat_mb", lambda pid: 20000.0)
    monkeypatch.setattr(modul._Messung, "speicher_mb", lambda self: 500.0)
    with pytest.raises(SpeicherKnapp) as e:
        u.pruefe()
    assert e.value.daten["frisch"] is True and e.value.daten["privat_mb_start"] == 500


def test_baufehler_der_fahrt_ist_nicht_nachgewiesen_und_schreibt_den_bericht(u, monkeypatch):
    def kaputt(*a, **k):
        raise BauFehler(REBUILD_FEHLER, "Kollision in der Fahrt nicht lesbar", schritt="kollision")

    u.gebaut()
    monkeypatch.setattr(modul, "fahre_bestand", kaputt)
    b = u.pruefe()
    assert b["bestanden"] is False and ids(b)["bewegung:Hub"]["ok"] is None and "nicht lesbar" in b["bewegungen"]["Hub"]["hinweis"]
    assert u.app.offen == []


def test_bekannte_fehler_der_fahrt_kommen_aus_dem_bestand(u, monkeypatch):
    """Spec §8.4: Alte Fehler stoppen die Fahrt nicht, neue schon. Mit der Lauf-Aufnahme wären auch neue Fehler „bekannt“."""
    u.gebaut()
    gesehen = {}
    echt = modul.mechanik_fuer

    def mechanik(app, asm, grenzen, aufnahme, ordner):
        gesehen.update(aufnahme=aufnahme, ordner=ordner, grenzen=sorted(grenzen))
        return echt(app, asm, grenzen, aufnahme, ordner)

    monkeypatch.setattr(modul, "mechanik_fuer", mechanik)
    u.pruefe()
    assert gesehen["aufnahme"]["datei"]["sha256"] == u.aufnahme["datei"]["sha256"] and gesehen["ordner"] == u.lauf_pfad("bilder")
    assert gesehen["grenzen"] == ["Hub"]


def frei(asm) -> None:
    """Eine bewegliche Komponente ohne Grenze."""
    asm.komponente("Frei-1", "teile/Welle.SLDPRT", status=2)


def test_abdeckung_nennt_nur_was_nicht_gefahren_ist(tmp_path, monkeypatch):
    u = Pruefung(tmp_path, monkeypatch, fehlerhaft=frei)
    u.gebaut()
    b = u.pruefe()
    assert "Frei-1" in ids(b)["bewegung_abdeckung"]["hinweis"] and any("Frei-1" in h for h in b["nicht_abgedeckt"])
    assert "Schlitten-1" not in ids(b)["bewegung_abdeckung"]["hinweis"]  # sie hat eine Grenze und ist gefahren
    assert not [t for t in [*b["nicht_abgedeckt"], *(w["meldung"] for w in b["warnungen"])] if "Schlitten-1" in t]


def test_ohne_offene_bewegung_kein_eintrag_zur_abdeckung(u):
    u.gebaut()
    assert "bewegung_abdeckung" not in ids(u.pruefe())


def test_fahrt_nur_in_der_aktiven_konfiguration_steht_da(u):
    u.gebaut()
    assert any("Fahrt" in h and "Standard" in h and "Leicht" in h for h in u.pruefe()["nicht_abgedeckt"])


# --- Bericht ------------------------------------------------------------------------------------------------------------------

def test_pruefbericht_traegt_pfade_und_dateien(u):
    u.gebaut(MASS, EIGENSCHAFT)
    b = u.pruefe()
    alle = ids(b)
    assert alle["pfade"]["ok"] is True and alle["pfade"]["geladen"] >= 1 and alle["pfade"]["fremd"] == []
    assert alle["dateien"]["ok"] is True
    assert b["dateien"]["geaendert"] == sorted([GRUND, HAUPT]) and b["dateien"]["neu"] == []
    assert b["differenzen"][GRUND]["Standard"][0]["volumen"] == 500.0
    assert set(b["messung"]) >= {f"teile:{GRUND}", "oeffnen", "lesen", "kollision", "bilder", "fahrt"}
    assert u.bericht_datei() == json.loads(json.dumps(b, default=str))
    assert (u.lauf_pfad("pruefbericht.json")).is_file()


def test_vorher_bilder_von_bestand_und_teil(u):
    u.gebaut()
    b = u.pruefe()
    assert b["bilder_vorher"]["iso"] == str(u.ordner / "bilder" / "iso.png") and b["bilder"]["iso"] == str(u.lauf_pfad("bilder") / "iso.png")
    assert b["bilder_vorher"][f"{GRUND}/iso"] == str(u.lauf_pfad("vergleich") / "bilder" / "teile_Grund.SLDPRT" / "iso.png")
    assert b["bilder"][f"{GRUND}/iso"] == str(u.lauf_pfad("bilder") / "teile_Grund.SLDPRT" / "iso.png")


def test_bilder_von_swki_bestand_zeige_sind_keine_vorher_bilder(u):
    u.gebaut()
    (u.ordner / "bilder" / "zeige_Grund-1.png").write_bytes(b"bild")
    assert sorted(k for k in u.pruefe()["bilder_vorher"] if "/" not in k) == ["iso", "vorne"]


def test_teil_wird_gegen_die_freigegebene_kopie_gemessen(u, monkeypatch):
    u.gebaut()
    echt = modul.freigegebene_spec
    monkeypatch.setattr(modul, "freigegebene_spec", lambda pfad: {**echt(pfad), "parameter": {"RA": 99}})
    gesehen = []
    pruefe = modul.pruefe_teil
    monkeypatch.setattr(modul, "pruefe_teil", lambda app, teil, frei, *a, **k: gesehen.append((teil, frei)) or pruefe(app, teil, frei, *a, **k))
    u.pruefe()
    assert gesehen[0][0]["parameter"] == {"RA": 12} and gesehen[0][1]["parameter"] == {"RA": 99}
    assert gesehen[0][1]["bestand"]["datei"] == GRUND


def test_fehlende_bilder_der_aufnahme_stehen_in_den_warnungen(u):
    u.gebaut()
    for p in (u.ordner / "bilder").glob("*.png"):
        p.unlink()
    assert any("Vorher-Bilder" in w["meldung"] for w in u.pruefe()["warnungen"])


def test_gegenprobe_steht_in_den_warnungen(u):
    u.gebaut()
    u.asm.versteckt.append(Mate(u.asm, "Versteckt1", 0))
    w = u.pruefe()["warnungen"]
    assert [x["verknuepfungen"] for x in w if x["code"] == VERKNUEPFUNG_UNERREICHT] == [["Versteckt1"]]


def test_gegenprobe_aus_unterbaugruppen_wird_gesammelt(u):
    u.gebaut()
    meldung = {"code": VERKNUEPFUNG_UNERREICHT, "verknuepfungen": ["Innen1"], "meldung": "Innen1 nicht erreicht"}
    ablage.schreibe_datei_aufnahme(u.r, "A", 1, "Unter.SLDASM", {"warnungen": [meldung]})
    w = u.pruefe()["warnungen"]
    assert {**meldung, "datei": "Unter.SLDASM"} in w


def test_fehlende_aufnahme_einer_unterbaugruppe_ist_nicht_still(u):
    u.gebaut()
    (u.ordner / "aufnahme" / "Unter.SLDASM.json").unlink()
    assert any(x.get("datei") == "Unter.SLDASM" for x in u.pruefe()["warnungen"])


def test_warnungen_stehen_einmal_da(tmp_path, monkeypatch):
    """Die Aufnahme nennt die Abdeckung schon, der Lauf nennt sie wieder."""
    u = Pruefung(tmp_path, monkeypatch, fehlerhaft=frei)
    u.aufnahme["warnungen"] = [{"code": "BEWEGUNG_ABDECKUNG", "meldung": "Komponente Frei-1 ist beweglich (unterbestimmt) und hat "
                                                                       "keine Grenze, nicht gefahren"}]
    u.gebaut()
    w = u.pruefe()["warnungen"]
    assert len([x for x in w if x["code"] == "BEWEGUNG_ABDECKUNG"]) == 1


def test_bestandsfehler_stehen_im_bericht(tmp_path, monkeypatch):
    def fehlerhaft(asm):
        asm.mate("Kaputt1", 0, [asm.seite("Grund-1"), asm.seite("Schraube-5")], code=7)
        asm.kollisionen = Kollisionen(1, [Interferenz(("Grund-1", "Schraube-5"), 3.0)])

    u = Pruefung(tmp_path, monkeypatch, fehlerhaft=fehlerhaft)
    u.gebaut()
    b = u.pruefe()
    assert b["bestandsfehler"]["verknuepfungen"] == [{"verknuepfung": "Kaputt1", "konfiguration": k, "code": 7} for k in ("Standard", "Leicht")]
    assert [k["paar"] for k in b["bestandsfehler"]["kollisionen"]] == [["Grund-1", "Schraube-5"]]
    assert b["bewegungen"]["Hub"]["kollisionen"] == [] and ids(b)["bewegung_kollision:Hub"]["ok"] is True  # die Fahrt kennt das Paar


# --- Status, Bericht, Prüfer, Durchlauf ------------------------------------------------------------------------------------------

def test_status_und_bericht(u):
    u.gebaut(MASS, WERT)
    u.pruefe()
    assert befehle.status(u.spec_pfad)["empfehlung"] == "pruefer"
    text = Path(befehle.bericht(u.spec_pfad)["bericht"]).read_text(encoding="utf-8")
    for teil in ("Änderung am Bestand", "Haupt.SLDASM", "Abstand1: 3 → 4", GRUND, "### Bewegungen", "### Kollisionen", "### Nicht abgedeckt"):
        assert teil in text, teil
    assert "Wirkung auf Baugruppen nicht geprüft" not in text


def test_pruefer_auftrag_nennt_alle_bilder(u):
    u.gebaut()
    b = u.pruefe()
    text = d.pruefer_auftrag(u.spec_pfad, 1, b)
    assert str(u.ordner / "bilder" / "iso.png") in text and str(u.lauf_pfad("bilder") / "iso.png") in text
    assert str(u.lauf_pfad("vergleich") / "bilder" / "teile_Grund.SLDPRT" / "iso.png") in text
    assert f"Bewegungsbilder (Lauf, je Grenze min, mitte, max): {u.lauf_pfad('bilder') / 'Hub-max.png'}" in text


def test_durchlauf_mit_neustart_und_ausgabe_der_warnungen(tmp_path, monkeypatch):
    u = Pruefung(tmp_path, monkeypatch, fehlerhaft=frei)
    u.schreibe(MASS, bereiche=BEREICH, pruefen=False)
    neustarts = []
    monkeypatch.setattr(d, "_neustart", lambda erg, vor: neustarts.append(vor))
    echt = u.baue

    def _bauen_und_umschalten(a):
        aus = echt()
        u.app.OpenDoc6 = u._oeffne_beim_pruefen
        return aus

    monkeypatch.setattr("swki.compiler.bauen._bauen", _bauen_und_umschalten)
    erg = d.durchlauf(u.spec_pfad, neustart=True)
    assert erg["schritt"] == "fertig", erg
    assert neustarts == ["bauen", "pruefen"] and erg["pruefung"]["bestanden"] is True and "pruefer_auftrag" in erg
    assert erg["pruefung"]["warnungen"]


def test_durchlauf_speicher_knapp_endet_im_schritt_pruefen(u, monkeypatch):
    u.schreibe(MASS, bereiche=BEREICH, pruefen=False)
    monkeypatch.setattr(sw_bewegung, "privat_mb", lambda pid: 20000.0)
    echt = u.baue

    def _bauen_und_umschalten(a):
        aus = echt()
        u.app.OpenDoc6 = u._oeffne_beim_pruefen
        return aus

    monkeypatch.setattr("swki.compiler.bauen._bauen", _bauen_und_umschalten)
    erg = d.durchlauf(u.spec_pfad)
    assert erg["schritt"] == "pruefen" and erg["code"] == "SPEICHER_KNAPP"


# --- Teil-Weg --------------------------------------------------------------------------------------------------------------------

def test_teil_pruefen_bleibt_gleich(tmp_path, monkeypatch):
    """Die Weiche fragt `aufnahme["art"]`: Ein Teil geht nie über den Baugruppen-Weg; `tests/bestand/test_pruefen.py` bleibt unverändert."""
    monkeypatch.setattr(modul, "pruefen_baugruppe", lambda *a: pytest.fail("Teil auf dem Baugruppen-Weg"))
    teil = Umgebung(tmp_path, monkeypatch)
    b = pruefen_modul.pruefen(teil.schreibe())
    assert b["bestanden"] is True and "pfade" not in {e["id"] for e in b["pruefungen"]} and "dateien" not in b


def test_pruefe_teil_geht_ueber_den_pfadschutz(u, monkeypatch):
    gesehen = []
    echt = pruefen_modul.oeffne_in

    def oeffne_in(app, pfad, wurzel, sichtbar=False, nur_lesen=True):
        gesehen.append((Path(pfad).name, wurzel, sichtbar, nur_lesen))
        return echt(app, pfad, wurzel, sichtbar=sichtbar, nur_lesen=nur_lesen)

    monkeypatch.setattr(pruefen_modul, "oeffne_in", oeffne_in)
    u.gebaut()
    u.pruefe()
    ordner = u.lauf_pfad("")
    assert gesehen == [("vorher_teile_Grund.SLDPRT", ordner, False, True), ("Grund.SLDPRT", ordner, False, True),
                       ("Grund.SLDPRT", ordner, True, True), ("vorher_teile_Grund.SLDPRT", ordner, True, True)]


def test_vorher_kopie_flach(tmp_path):
    quelle = tmp_path / "bestand" / "teile" / "unter" / "A.SLDPRT"
    quelle.parent.mkdir(parents=True)
    quelle.write_bytes(b"a")
    ordner = tmp_path / "lauf"
    assert ablage.vorher_kopie(quelle, ordner, "teile/unter/A.SLDPRT") == ordner / "vergleich" / "vorher_teile_unter_A.SLDPRT"
    assert ablage.vorher_kopie(quelle, ordner) == ordner / "vergleich" / "vorher_A.SLDPRT"


def test_neue_komponente_wird_geprueft(u, normteil):  # noqa: F811
    u.gebaut(NEU, bereiche=[])
    b = u.pruefe()
    alle = ids(b)
    assert alle["punkt:k1"]["ok"] is True and alle["punkt:k1"]["ist"] == [NEUE_KOMPONENTE]
    assert b["dateien"]["neu"] == [NEUE_DATEI] and alle["dateien"]["ok"] is True and alle["komponenten"]["ok"] is True and b["bestanden"] is True


@pytest.fixture
def eigenes_teil(u, monkeypatch):
    """`quelle.teil`: Teilbau und Speichern ohne SolidWorks; die Messwerte eines Teils wie im Soll."""
    schreibe_teil(u.spec_pfad.parent)
    teil = SimpleNamespace(GetPathName=None, GetTitle=DECKEL, GetPartBox=lambda welt: (0.0,) * 6)

    def baue(app, r, standard, spec, pfad, auftrag, protokoll):
        return teil, SimpleNamespace(model=teil, ergebnisse={}), None

    def speichere(model, pfad):
        Path(pfad).write_bytes(b"deckel")
        teil.GetPathName = str(Path(pfad).with_suffix(".SLDPRT"))

    monkeypatch.setattr(punkte_baugruppe, "baue_teil_dokument", baue)
    monkeypatch.setattr(punkte_baugruppe.sw, "speichere", speichere)
    monkeypatch.setattr(punkte_baugruppe, "lade_rechner", lambda: u.r)
    gemessen = SimpleNamespace(werte=Messwerte([], {}, [-50, 0, -30, 50, 15, 30], 1000.0, (0, 0, 0), "1.0038", {}), kontexte=[])

    def kontext(app, model, spec, spec_pfad, tol, protokoll):
        gemessen.kontexte.append((Path(model.GetPathName).name, spec["parameter"]["H"], spec_pfad.name, protokoll["status"]))
        return SimpleNamespace(model=model)

    monkeypatch.setattr(modul, "kontext_aus_datei", kontext)
    monkeypatch.setattr(modul, "messe", lambda ctx, soll: gemessen.werte)
    return gemessen


def test_eigenes_neues_teil_wird_gegen_die_freigabe_gemessen(u, eigenes_teil):
    u.schreibe(TEIL_PUNKT, bereiche=[], pruefen=False)
    freigabe_der_teil_quelle(u.spec_pfad)
    assert u.baue()["status"] == "ok"
    b = u.pruefe()
    alle = ids(b)
    assert alle[f"{DECKEL}/rebuild"]["ok"] is True and alle[f"{DECKEL}/huellquader"]["ok"] is True, alle
    assert b["bestanden"] is True, b["maengel"]
    assert b["teilpruefungen"][DECKEL] == {"bestanden": True, "maengel": 0} and f"teile:{DECKEL}" in b["messung"]
    assert eigenes_teil.kontexte == [(DECKEL, 15, "Deckel2.yaml", "ok")]
    assert u.verlauf == [DECKEL, HAUPT, HAUPT]  # zu, bevor die Baugruppe aufgeht; `_oeffne_beim_pruefen` prüft den Rest


def test_eigenes_neues_teil_mit_mangel_ist_nicht_bestanden(u, eigenes_teil):
    u.schreibe(TEIL_PUNKT, bereiche=[], pruefen=False)
    freigabe_der_teil_quelle(u.spec_pfad)
    u.baue()
    eigenes_teil.werte.box = [-50, 0, -30, 50, 99, 30]
    b = u.pruefe()
    assert b["bestanden"] is False and ids(b)[f"{DECKEL}/huellquader"]["ok"] is False
    assert b["teilpruefungen"][DECKEL] == {"bestanden": False, "maengel": 1}


def test_gescheiterte_messung_des_neuen_teils_ist_nicht_nachgewiesen(u, eigenes_teil, monkeypatch):
    u.schreibe(TEIL_PUNKT, bereiche=[], pruefen=False)
    freigabe_der_teil_quelle(u.spec_pfad)
    u.baue()
    monkeypatch.setattr(modul, "messe", lambda ctx, soll: 1 / 0)
    b = u.pruefe()
    e = ids(b)[f"{DECKEL}/messung"]
    assert e["ok"] is None and "ZeroDivisionError" in e["hinweis"] and b["bestanden"] is False and u.app.offen == []


def test_neues_teil_fehlt_im_protokoll_ist_nicht_nachgewiesen(u, eigenes_teil):
    u.schreibe(TEIL_PUNKT, bereiche=[], pruefen=False)
    freigabe_der_teil_quelle(u.spec_pfad)
    u.baue()
    datei = lauf_datei(u.spec_pfad, 1, "protokoll")
    p = json.loads(datei.read_text(encoding="utf-8"))
    p["neue_dateien"] = []
    datei.write_text(json.dumps(p), encoding="utf-8")
    b = u.pruefe()
    assert ids(b)["Deckel2.yaml/messung"]["ok"] is None and b["bestanden"] is False


def test_pfad_fremd_am_neuen_teil_bleibt_laut(u, eigenes_teil, monkeypatch):
    u.schreibe(TEIL_PUNKT, bereiche=[], pruefen=False)
    freigabe_der_teil_quelle(u.spec_pfad)
    u.baue()

    echt = modul.oeffne_in

    def fremd(app, pfad, *a, **k):
        if Path(pfad).name == DECKEL:
            raise BestandFehler(BESTAND_PFAD_FREMD, "fremd")
        return echt(app, pfad, *a, **k)

    monkeypatch.setattr(modul, "oeffne_in", fremd)
    with pytest.raises(BestandFehler):
        u.pruefe()
    assert not lauf_datei(u.spec_pfad, 1, "pruefbericht").exists()


def test_lauf_datei_nach_dem_bau_geaendert_ist_mangel(u, normteil):  # noqa: F811
    """Auch eine neue Datei: Ihre SHA-256 kennt nur das Protokoll."""
    u.gebaut(NEU, bereiche=[])
    u.lauf_pfad(NEUE_DATEI).write_bytes(b"nach dem Bau von Hand")
    b = u.pruefe()
    e = ids(b)["dateien"]
    assert e["ok"] is False and NEUE_DATEI in e["hinweis"] and e["nach_dem_bau"] == [NEUE_DATEI] and b["bestanden"] is False


def test_veraltete_datei_ohne_pruefsumme_ist_nicht_bestanden(u):
    """Ein Protokoll ohne `sha256` belegt nichts."""
    u.gebaut()
    datei = lauf_datei(u.spec_pfad, 1, "protokoll")
    p = json.loads(datei.read_text(encoding="utf-8"))
    p["sha256"] = {}
    datei.write_text(json.dumps(p), encoding="utf-8")
    b = u.pruefe()
    assert ids(b)["dateien"]["ok"] is False and b["bestanden"] is False


def test_abbruch_vor_dem_oeffnen_ohne_lauf(u):
    u.schreibe(MASS, bereiche=BEREICH)
    with pytest.raises(pruefen_modul.SwkiFehler, match="keinen Lauf"):
        pruefen_modul.pruefen(u.spec_pfad)
    assert spec_modul.lade_aenderung(u.spec_pfad)["name"] == "Haupt_Rev" and not lauf_ordner(u.r, "A", 1).exists()
