"""swki bestand ausgabe, Status und Bericht für art: aenderung ohne SolidWorks (Spec Bestandsdateien §9). Gebaut wird echt mit der
Attrappe aus `test_bau` (Protokoll, Prüfsummen, Lizenz); der Prüfbericht und das Prüfer-Urteil stehen als Dateien da. Kern: Es wird
nur ausgegeben, was geprüft und vom Prüfer abgenommen ist, und nie außerhalb des Arbeitsordners."""

import hashlib
import json
from pathlib import Path

import pytest

from swki import aenderungen as aenderungen_modul
from swki.aenderungen import sha256_datei
from swki.auftrag import lauf_datei, lauf_ordner
from swki.bestand import ausgabe as modul
from swki.bestand import bau
from swki.bestand.fehler import (BESTAND_LIZENZ, BESTAND_NICHT_LESBAR, BESTAND_ORIGINAL_GEAENDERT, LAUF_NICHT_BESTANDEN,
                                 BestandFehler)
from swki.cli import SwkiFehler
from swki.pruefung import befehle
from swki.pruefung.schleife import empfehlung
from tests.bestand.test_bau import INHALT, MASS, Lauf

DIFFERENZEN = {"Standard": [{"art": "hinzu", "box": [-40.0, 10.0, 10.0, -30.0, 20.0, 20.0], "volumen": 500.0, "flaeche": 120.0,
                             "dicke": 5.0, "bereich": 0, "unter_toleranz": False, "duenn": False}],
               "Variante B": []}


class Ausgabe(Lauf):
    """Lauf 1 des Auftrags A gebaut (Datei weicht von der Bestandskopie ab), Original unter kunde/ unverändert."""

    def __init__(self, tmp_path, monkeypatch):
        super().__init__(tmp_path, monkeypatch)
        monkeypatch.setattr(modul, "lade_rechner", lambda: self.r)
        monkeypatch.setattr(befehle, "lade_standard", lambda: {"max_nachbesserungen": 3})
        monkeypatch.setattr(befehle, "_compiler_aenderungen", lambda seit: [])
        self.original = tmp_path / "kunde" / "Lagerdeckel.SLDPRT"
        self.original.parent.mkdir()
        self.original.write_bytes(INHALT)
        self.aufnahme["datei"]["original"] = str(self.original)
        self.arbeit = self.r.arbeitsordner
        self.nur_aussen = lambda: sorted(p for p in tmp_path.rglob("*") if p.is_file() and not p.is_relative_to(self.arbeit)
                                         and not p.is_relative_to(tmp_path / "auftraege"))

    def voll(self, typ=0):
        """Sitzung und Datei melden diese Lizenz (die Attrappe liefert sonst Student)."""
        self.app.GetCurrentLicenseType = typ
        self.vor_teil = lambda teil: setattr(teil, "lizenz", typ)

    def gebaut(self, *punkte, bestanden=True, urteil=True, lauf=1, **bericht):
        """Bauen und Prüfbericht und Urteil dazulegen. `bestanden=False`: Prüfbericht mit offenem Mangel."""
        self.schreibe(*(punkte or (MASS,)))
        nummer = bau.bauen(self.spec_pfad)["lauf"]
        assert nummer == lauf
        maengel = [] if bestanden else [{"pruefung": "baum", "knoten": [], "beschreibung": "x", "nicht_nachgewiesen": False}]
        text = json.dumps({"bestanden": bestanden, "maengel": maengel, "differenzen": DIFFERENZEN, **bericht})
        lauf_datei(self.spec_pfad, lauf, "pruefbericht").write_text(text, encoding="utf-8")
        if urteil is not None:
            lauf_datei(self.spec_pfad, lauf, "pruefer").write_text(json.dumps({"bestanden": urteil, "maengel": []}), encoding="utf-8")
        return self.spec_pfad

    def aendere_protokoll(self, aendere, lauf=1):
        datei = lauf_datei(self.spec_pfad, lauf, "protokoll")
        protokoll = json.loads(datei.read_text(encoding="utf-8"))
        aendere(protokoll)
        datei.write_text(json.dumps(protokoll), encoding="utf-8")

    def ausgabe_ordner(self):
        return self.arbeit / "A" / "ausgabe"


@pytest.fixture
def u(tmp_path, monkeypatch):
    return Ausgabe(tmp_path, monkeypatch)


def codes(erg):
    return [w["code"] for w in erg["warnungen"]]


def test_ausgabe_kopiert_nur_geaenderte_unter_originalnamen(u):
    u.voll()
    spec = u.gebaut()
    datei = u.lauf_datei()
    erg = modul.ausgabe(spec)
    ziel = u.ausgabe_ordner() / "Lagerdeckel.SLDPRT"
    assert erg["dateien"] == [{"datei": "Lagerdeckel.SLDPRT", "original": str(u.original), "ausgabe": str(ziel),
                               "sha256": sha256_datei(datei)}]
    assert erg["unveraendert"] == [] and erg["warnungen"] == [] and erg["lauf"] == 1 and erg["auftrag"] == "A"
    assert ziel.read_bytes() == datei.read_bytes() != INHALT
    assert u.original.read_bytes() == INHALT and u.nur_aussen() == [u.original]  # das Original wird nie angefasst


def test_ausgabe_nennt_unveraenderte_und_kopiert_sie_nicht(u):
    """Dieselbe SHA-256 wie die Bestandskopie: nichts auszugeben, die Datei steht unter `unveraendert`."""
    u.voll()
    spec = u.gebaut()
    u.lauf_datei().write_bytes(INHALT)
    u.aendere_protokoll(lambda p: p["sha256"].update({"Lagerdeckel.SLDPRT": hashlib.sha256(INHALT).hexdigest()}))
    erg = modul.ausgabe(spec)
    assert erg["dateien"] == [] and erg["unveraendert"] == ["Lagerdeckel.SLDPRT"]
    assert not u.ausgabe_ordner().exists()


def test_ausgabe_arbeitet_nur_aus_den_dateien_des_protokolls(u):
    """Was sonst im Lauf-Ordner liegt (Vorher-Kopie, Bilder), wird nie ausgegeben."""
    u.voll()
    spec = u.gebaut()
    ordner = lauf_ordner(u.r, "A", 1)
    (ordner / "vergleich").mkdir()
    (ordner / "vergleich" / "vorher_Lagerdeckel.SLDPRT").write_bytes(b"vorher")
    (ordner / "Fremd.SLDPRT").write_bytes(b"fremd")
    erg = modul.ausgabe(spec)
    assert [d["datei"] for d in erg["dateien"]] == ["Lagerdeckel.SLDPRT"]
    assert sorted(p.name for p in u.ausgabe_ordner().rglob("*") if p.is_file()) == ["Lagerdeckel.SLDPRT"]


@pytest.mark.parametrize("urteil, bestanden", [(None, True), (False, True), (True, False)], ids=["ohne_urteil", "urteil_maengel", "bericht_offen"])
def test_ausgabe_verlangt_bestandenen_lauf(u, urteil, bestanden):
    spec = u.gebaut(urteil=urteil, bestanden=bestanden)
    with pytest.raises(BestandFehler) as e:
        modul.ausgabe(spec)
    assert e.value.daten["code"] == LAUF_NICHT_BESTANDEN and e.value.daten["lauf"] == 1
    assert not u.ausgabe_ordner().exists()


def test_ausgabe_ohne_pruefbericht_ist_nicht_bestanden(u):
    spec = u.gebaut()
    lauf_datei(spec, 1, "pruefbericht").unlink()
    with pytest.raises(BestandFehler) as e:
        modul.ausgabe(spec)
    assert e.value.daten["code"] == LAUF_NICHT_BESTANDEN and not u.ausgabe_ordner().exists()


def test_ausgabe_ohne_lauf(u):
    u.schreibe(MASS)
    with pytest.raises(SwkiFehler, match="noch keinen Lauf"):
        modul.ausgabe(u.spec_pfad)


def test_ausgabe_vorgabe_ist_der_letzte_lauf_und_lauf_waehlt(u):
    spec = u.gebaut()
    bau.bauen(spec)  # Lauf 2: gebaut, ungeprüft
    with pytest.raises(BestandFehler, match="Lauf 2"):
        modul.ausgabe(spec)
    assert modul.ausgabe(spec, 1)["lauf"] == 1
    with pytest.raises(SwkiFehler, match="Lauf 5"):
        modul.ausgabe(spec, 5)


def test_ausgabe_warnt_wenn_original_neuer(u):
    u.voll()
    spec = u.gebaut()
    u.original.write_bytes(b"der Kollege war fleissig")
    erg = modul.ausgabe(spec)
    assert codes(erg) == [BESTAND_ORIGINAL_GEAENDERT] and "überschreiben" in erg["warnungen"][0]["meldung"]
    assert (u.ausgabe_ordner() / "Lagerdeckel.SLDPRT").is_file()  # kopiert trotzdem
    assert u.original.read_bytes() == b"der Kollege war fleissig"


def test_ausgabe_warnt_wenn_original_weg(u):
    """Review Focus 3: Original verschwunden (Laufwerk weg, Datei umbenannt) ist eine Warnung, kein Absturz."""
    u.voll()
    spec = u.gebaut()
    u.original.unlink()
    erg = modul.ausgabe(spec)
    assert codes(erg) == [BESTAND_NICHT_LESBAR] and str(u.original) in erg["warnungen"][0]["meldung"]
    assert (u.ausgabe_ordner() / "Lagerdeckel.SLDPRT").is_file()


def test_ausgabe_warnt_wenn_original_gesperrt(u, monkeypatch):
    u.voll()
    spec = u.gebaut()
    echt = modul.sha256_datei

    def gesperrt(pfad):
        if pfad == u.original:
            raise PermissionError(13, "Zugriff verweigert")
        return echt(pfad)

    monkeypatch.setattr(modul, "sha256_datei", gesperrt)
    erg = modul.ausgabe(spec)
    assert codes(erg) == [BESTAND_NICHT_LESBAR] and "Zugriff verweigert" in erg["warnungen"][0]["meldung"]
    assert (u.ausgabe_ordner() / "Lagerdeckel.SLDPRT").is_file()


def test_ausgabe_nennt_lizenz_und_original_zugleich(u):
    spec = u.gebaut()  # Attrappe: Student
    u.original.write_bytes(b"anders")
    assert codes(modul.ausgabe(spec)) == [BESTAND_LIZENZ, BESTAND_ORIGINAL_GEAENDERT]


@pytest.mark.parametrize("typ", [0, 5, 6, 7, 9])
def test_vollversionen_warnen_nicht(u, typ):
    u.voll(typ)
    assert modul.ausgabe(u.gebaut())["warnungen"] == []


@pytest.mark.parametrize("typ", [1, 2, 3, 4, 8])
def test_alle_anderen_lizenzen_warnen_und_kopieren_trotzdem(u, typ):
    """Ruling 5: Educational, Student, StudentDesignKit, PersonalEdition und Maker sind keine Vollversion."""
    u.voll(typ)
    erg = modul.ausgabe(u.gebaut())
    assert codes(erg) == [BESTAND_LIZENZ] and "swLicenseType_" in erg["warnungen"][0]["meldung"]
    assert (u.ausgabe_ordner() / "Lagerdeckel.SLDPRT").is_file()


def test_fehlende_lizenz_im_protokoll_warnt(u):
    u.voll()
    spec = u.gebaut()
    u.aendere_protokoll(lambda p: p.pop("lizenz"))
    assert codes(modul.ausgabe(spec)) == [BESTAND_LIZENZ]
    u.aendere_protokoll(lambda p: p.update(lizenz=None))
    assert codes(modul.ausgabe(spec)) == [BESTAND_LIZENZ]


def test_ausgabe_schreibt_nie_ausserhalb_des_arbeitsordners(u, tmp_path):
    """Eine Datei im Protokoll, die nicht im Lauf-Ordner liegt, wird weder gelesen noch kopiert."""
    u.voll()
    spec = u.gebaut()
    fremd = tmp_path / "kunde" / "Anderes.SLDPRT"
    fremd.write_bytes(b"fremd")
    vorher = u.nur_aussen()
    u.aendere_protokoll(lambda p: p["dateien"].update(teil=str(fremd)))
    with pytest.raises(SwkiFehler, match="Lauf-Ordner"):
        modul.ausgabe(spec)
    u.aendere_protokoll(lambda p: p["dateien"].update(teil=str(lauf_ordner(u.r, "A", 1) / ".." / ".." / ".." / "kunde" / "Anderes.SLDPRT")))
    with pytest.raises(SwkiFehler, match="Lauf-Ordner"):
        modul.ausgabe(spec)
    assert u.nur_aussen() == vorher and not u.ausgabe_ordner().exists()


def test_ziel_bleibt_im_arbeitsordner(u):
    """Zweite Sicherung: Weder der Auftragsname noch der relative Pfad der Datei führt aus dem Arbeitsordner heraus."""
    assert modul._ziel(u.r, "A", Path("Teil.SLDPRT")) == u.arbeit / "A" / "ausgabe" / "Teil.SLDPRT"
    for auftrag, rel in (("../aussen", Path("Teil.SLDPRT")), ("A", Path("..") / ".." / "Teil.SLDPRT"), ("A", Path("C:/x/Teil.SLDPRT"))):
        with pytest.raises(SwkiFehler, match="Arbeitsordner"):
            modul._ziel(u.r, auftrag, rel)


def test_ausgabe_verweigert_nach_manueller_aenderung_des_laufs(u):
    """Die Ausgabe muss das sein, was geprüft wurde: Ändert jemand die Lauf-Datei nach dem Bau, gilt der Prüfbericht nicht mehr."""
    u.voll()
    spec = u.gebaut()
    u.lauf_datei().write_bytes(b"von Hand")
    with pytest.raises(SwkiFehler) as e:
        modul.ausgabe(spec)
    assert e.value.daten["code"] == "MANUELL_GEAENDERT" and not u.ausgabe_ordner().exists()


def test_ausgabe_braucht_die_freigabe(u):
    u.voll()
    spec = u.gebaut()
    spec.write_text(spec.read_text(encoding="utf-8").replace("name: Lagerdeckel_Rev", "name: Anders"), encoding="utf-8")
    with pytest.raises(SwkiFehler):
        modul.ausgabe(spec)
    assert not u.ausgabe_ordner().exists()


def test_ausgabe_liste_kopiert_nicht(u):
    """Für den Bericht: dieselbe Liste samt Warnungen, ohne etwas zu schreiben."""
    u.voll()
    spec = u.gebaut()
    liste = modul.ausgabe_liste(spec)
    assert [d["datei"] for d in liste["dateien"]] == ["Lagerdeckel.SLDPRT"] and not u.ausgabe_ordner().exists()


def test_cli_ausgabe(u, monkeypatch):
    aufrufe = []
    monkeypatch.setattr(modul, "ausgabe", lambda pfad, lauf: aufrufe.append((pfad, lauf)) or {"dateien": []})
    from swki.cli import main

    assert main(["bestand", "ausgabe", str(u.spec_pfad), "--lauf", "2"]) == 0
    assert main(["bestand", "ausgabe", str(u.spec_pfad)]) == 0
    assert aufrufe == [(u.spec_pfad, 2), (u.spec_pfad, None)]


# --- Status, Bericht, swki aenderungen ---

def test_status_und_bericht_mit_aenderung(u):
    punkt = {**MASS, "folgen": ["D5@Skizze5"]}
    spec = u.gebaut(punkt)
    st = befehle.status(spec)
    assert st["empfehlung"] == "bestanden" and st["laeufe"][0]["bestanden"] is True
    assert empfehlung(st["laeufe"], 3)[0] == "bestanden"
    erg = befehle.bericht(spec)
    text = (spec.parent / "bericht.md").read_text(encoding="utf-8")
    assert erg["status"] == "bestanden" and erg["bericht"] == str(spec.parent / "bericht.md")
    assert "# Bericht Lagerdeckel_Rev (Auftrag A)" in text and "## Änderung am Bestand" in text
    assert "| p1 | mass | Abstand: D2@Skizze4: 40 → 45 | D5@Skizze5 |" in text  # Punkt mit Alt- und Neuwert und Folgen
    assert "Standard" in text and "hinzu" in text and "500" in text and "x -40…-30" in text  # Differenz mit Lage und Volumen
    assert "Variante B: keine Abweichung" in text
    assert "Lagerdeckel.SLDPRT" in text and str(u.original) in text  # Ausgabeliste mit Originalpfad
    assert "Wirkung auf Baugruppen nicht geprüft" in text
    assert "swLicenseType_Student" in text and "BESTAND_LIZENZ" in text
    assert not u.ausgabe_ordner().exists()  # der Bericht kopiert nichts


def test_bericht_sagt_nicht_nachgewiesen_statt_keine_abweichung(u):
    """Eine gescheiterte Differenz hinterlässt eine leere Liste: Das ist kein Nachweis, dass sich nichts geändert hat."""
    hinweis = "Differenz in Variante B nicht nachgewiesen: Flächenkörper"
    spec = u.gebaut(bestanden=False, urteil=None, differenzen={"Standard": [], "Variante B": []},
                    pruefungen=[{"id": "bereich", "ok": True, "konfiguration": "Standard", "ist": []},
                                {"id": "bereich", "ok": None, "konfiguration": "Variante B", "ist": [], "hinweis": hinweis}])
    befehle.bericht(spec)
    text = (spec.parent / "bericht.md").read_text(encoding="utf-8")
    assert "- Standard: keine Abweichung" in text
    assert f"- Variante B: nicht nachgewiesen: {hinweis}" in text and "Variante B: keine Abweichung" not in text


def test_bericht_nennt_nur_duenne_abweichung_nicht_nachgewiesen(u):
    """Abweichungen stehen da, die Konfiguration ist trotzdem nicht nachgewiesen: beides gehört in den Bericht."""
    zeile = {**DIFFERENZEN["Standard"][0], "bereich": None, "duenn": True}
    spec = u.gebaut(bestanden=False, urteil=None, differenzen={"Standard": [zeile]},
                    pruefungen=[{"id": "bereich", "ok": None, "konfiguration": "Standard", "ist": [zeile], "hinweis": "nur im Mittel dünn"}])
    befehle.bericht(spec)
    text = (spec.parent / "bericht.md").read_text(encoding="utf-8")
    assert "- Standard: nicht nachgewiesen: nur im Mittel dünn" in text and "in keinem Bereich" in text


def test_bericht_ohne_bestandenen_lauf_nennt_keine_ausgabe(u):
    spec = u.gebaut(urteil=None)
    befehle.bericht(spec)
    text = (spec.parent / "bericht.md").read_text(encoding="utf-8")
    assert "## Änderung am Bestand" in text and "Ausgabe erst nach bestandenem Lauf" in text
    assert "Wirkung auf Baugruppen nicht geprüft" in text


def test_bericht_zeigt_warnung_zum_original(u):
    u.voll()
    spec = u.gebaut()
    u.original.unlink()
    befehle.bericht(spec)
    text = (spec.parent / "bericht.md").read_text(encoding="utf-8")
    assert "BESTAND_NICHT_LESBAR" in text


def test_bericht_teil_bleibt_wie_bisher():
    from swki.pruefung.bericht import bericht_markdown

    text = bericht_markdown({"name": "Teil"}, "T", [], ("bauen", "x"), None, None, None, [])
    assert "Änderung am Bestand" not in text and "Wirkung auf Baugruppen" not in text


def test_aenderungen_verweist_auf_neuen_lauf(u, monkeypatch):
    """`swki aenderungen` liest bei art: aenderung keine Maße (kein SolidWorks, keine Freigabe nötig), sagt aber, was zu tun ist."""
    monkeypatch.setattr(aenderungen_modul, "lade_rechner", lambda: u.r)
    monkeypatch.setattr(aenderungen_modul, "lade_standard", lambda: {})
    monkeypatch.setattr(aenderungen_modul, "verbinde", lambda jahr: pytest.fail("kein SolidWorks nötig"))
    spec = u.gebaut()
    u.lauf_datei().write_bytes(b"von Hand")
    erg = aenderungen_modul.aenderungen(spec)
    assert erg["lauf"] == 1 and erg["fehlend"] == [] and erg["spec"] == spec.name
    [datei] = erg["geaendert"]
    assert datei["datei"] == "Lagerdeckel.SLDPRT" and datei["parameter"] == []
    assert "ab der Bestandskopie" in erg["text"] and "--uebernommen" in erg["text"] and "--verwerfen" in erg["text"]
    # der Befund bleibt, bauen verweigert weiter
    with pytest.raises(SwkiFehler) as e:
        bau.bauen(spec)
    assert e.value.daten["code"] == "MANUELL_GEAENDERT"


def test_aenderungen_ohne_aenderung_wie_bisher(u, monkeypatch):
    monkeypatch.setattr(aenderungen_modul, "lade_rechner", lambda: u.r)
    monkeypatch.setattr(aenderungen_modul, "lade_standard", lambda: {})
    spec = u.gebaut()
    assert aenderungen_modul.aenderungen(spec) == {"spec": spec.name, "lauf": 1, "geaendert": [], "fehlend": []}

