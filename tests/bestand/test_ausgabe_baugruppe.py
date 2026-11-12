"""swki bestand ausgabe für Baugruppen ohne SolidWorks (Spec Bestandsdateien §8.5, §9; Plan Etappe 2 Task 11). Gebaut wird echt mit der
Attrappe, Prüfbericht und Prüfer-Urteil stehen als Dateien da. Kern: Ausgegeben wird nur, was sich geändert hat oder neu ist, nur
unter `ausgabe/`, und je Original eine Warnung, wenn es sich seit der Aufnahme geändert hat. Originale werden nur gelesen."""

import json
import os
import stat
from pathlib import Path

import pytest

from swki.aenderungen import sha256_datei
from swki.auftrag import lauf_datei, lauf_ordner
from swki.bestand import ablage
from swki.bestand import ausgabe as modul
from swki.bestand.fehler import BESTAND_NICHT_LESBAR, BESTAND_ORIGINAL_GEAENDERT, LAUF_NICHT_BESTANDEN, BestandFehler
from swki.cli import SwkiFehler
from swki.pruefung import befehle
from swki.pruefung.bericht import _punkt_text, bericht_markdown
from tests.bestand.test_bau_baugruppe import (EIGENSCHAFT, GRUND, HAUPT, MASS, MASS2, NEU, NEUE_DATEI, SCHLITTEN, WERT, WEITERE, inhalt,
                                              normteil)  # noqa: F401
from tests.bestand.test_pruefen_baugruppe import BEREICH, BEREICHE, Pruefung


class Ausgabe(Pruefung):
    """Originale liegen wirklich unter `kunde/`, dateien.json nennt sie."""

    def __init__(self, tmp_path, monkeypatch, **k):
        super().__init__(tmp_path, monkeypatch, **k)
        self.app.GetCurrentLicenseType = 0
        self.vor_voll = None
        self.kunde.mkdir()
        for rel, e in self.dateien.items():
            original = self.kunde / rel
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(inhalt(rel))
            e["original"] = str(original)
        ablage.schreibe_dateien(self.r, "A", 1, self.dateien)
        self.aufnahme["datei"]["original"] = str(self.kunde / HAUPT)
        self.app.vor_teil = lambda rel, teil: setattr(teil, "lizenz", 0)

    def bestanden(self, *punkte, bereiche=BEREICH, lauf=1):
        self.gebaut(*punkte, bereiche=bereiche)
        text = json.dumps({"bestanden": True, "maengel": [], "differenzen": {}, "pruefungen": []})
        lauf_datei(self.spec_pfad, lauf, "pruefbericht").write_text(text, encoding="utf-8")
        lauf_datei(self.spec_pfad, lauf, "pruefer").write_text(json.dumps({"bestanden": True, "maengel": []}), encoding="utf-8")
        return self.spec_pfad

    def ausgabe_ordner(self) -> Path:
        return self.r.arbeitsordner / "A" / "ausgabe"

    def ausgegeben(self) -> list[str]:
        return sorted(p.relative_to(self.ausgabe_ordner()).as_posix() for p in self.ausgabe_ordner().rglob("*") if p.is_file())


@pytest.fixture
def u(tmp_path, monkeypatch):
    return Ausgabe(tmp_path, monkeypatch)


def codes(erg):
    return [w["code"] for w in erg["warnungen"] if w["code"] != "BESTAND_LIZENZ"]


def test_ausgabe_nur_geaenderte_und_neue(u, normteil):  # noqa: F811
    spec = u.bestanden(NEU, MASS)
    erg = modul.ausgabe(spec)
    assert u.ausgegeben() == sorted([HAUPT, GRUND, NEUE_DATEI])
    je = {d["datei"]: d for d in erg["dateien"]}
    assert je[GRUND]["neu"] is False and je[GRUND]["original"] == str(u.kunde / GRUND)
    assert je[HAUPT]["neu"] is False and je[HAUPT]["original"] == str(u.kunde / HAUPT)
    assert je[NEUE_DATEI]["neu"] is True and je[NEUE_DATEI]["original"] == str(u.kunde / NEUE_DATEI)
    assert je[NEUE_DATEI]["ausgabe"] == str(u.ausgabe_ordner() / NEUE_DATEI)
    assert sorted(erg["unveraendert"]) == sorted(set(WEITERE) - {GRUND})
    assert erg["warnungen"] == [] or codes(erg) == []


def test_original_kommt_aus_dateien_json(u):
    """Eine Datei von außerhalb liegt in der Kopie flach neben der Baugruppe (§8.1), ihr Original anderswo."""
    anderswo = u.kunde.parent / "normalien" / "Grund.SLDPRT"
    anderswo.parent.mkdir()
    anderswo.write_bytes(inhalt(GRUND))
    u.dateien[GRUND]["original"] = str(anderswo)
    ablage.schreibe_dateien(u.r, "A", 1, u.dateien)
    erg = modul.ausgabe(u.bestanden())
    assert erg["dateien"][0]["original"] == str(anderswo) and codes(erg) == []


def test_ausgabe_behaelt_die_struktur_und_den_inhalt(u):
    spec = u.bestanden()
    erg = modul.ausgabe(spec)
    assert u.ausgegeben() == [GRUND]
    ziel = u.ausgabe_ordner() / GRUND
    assert ziel.read_bytes() == u.lauf_inhalt(GRUND) and sha256_datei(ziel) == erg["dateien"][0]["sha256"]


def test_ausgabe_liegt_nur_unter_ausgabe(u, tmp_path):
    spec = u.bestanden(MASS, EIGENSCHAFT)
    aussen = sorted(p for p in tmp_path.rglob("*") if p.is_file() and not p.is_relative_to(u.r.arbeitsordner))
    inhalte = {p: p.read_bytes() for p in aussen}
    modul.ausgabe(spec)
    neu = sorted(p for p in tmp_path.rglob("*") if p.is_file() and not p.is_relative_to(u.r.arbeitsordner))
    assert neu == aussen and {p: p.read_bytes() for p in aussen} == inhalte
    assert all(Path(d).is_relative_to(u.ausgabe_ordner()) for d in (x["ausgabe"] for x in modul.ausgabe_liste(spec)["dateien"]))


def test_ausgabe_warnt_je_geaendertem_original(u):
    spec = u.bestanden(MASS, EIGENSCHAFT)
    (u.kunde / GRUND).write_bytes(b"der Kollege")
    (u.kunde / HAUPT).write_bytes(b"der Kollege")
    erg = modul.ausgabe(spec)
    assert codes(erg) == [BESTAND_ORIGINAL_GEAENDERT] * 2
    assert sorted(w["datei"] for w in erg["warnungen"] if "datei" in w) == sorted([GRUND, HAUPT])
    assert all("überschreiben" in w["meldung"] for w in erg["warnungen"] if w["code"] == BESTAND_ORIGINAL_GEAENDERT)
    assert u.ausgegeben() == sorted([GRUND, HAUPT])  # kopiert trotzdem


def test_ausgabe_warnt_auch_wenn_ein_unveraendertes_original_neuer_ist(u):
    """Der Lauf ist gegen den alten Stand dieses Teils geprüft: Zurückkopiert läge die neue Baugruppe neben einem anderen Teil."""
    spec = u.bestanden()
    (u.kunde / SCHLITTEN).write_bytes(b"der Kollege")
    erg = modul.ausgabe(spec)
    assert codes(erg) == [BESTAND_ORIGINAL_GEAENDERT] and erg["warnungen"][-1]["datei"] == SCHLITTEN
    assert "alten Stand" in erg["warnungen"][-1]["meldung"]


def test_ausgabe_warnt_wenn_original_weg(u):
    spec = u.bestanden()
    (u.kunde / GRUND).unlink()
    erg = modul.ausgabe(spec)
    assert codes(erg) == [BESTAND_NICHT_LESBAR] and erg["warnungen"][-1]["datei"] == GRUND and u.ausgegeben() == [GRUND]


def test_neue_datei_warnt_wenn_am_ziel_schon_eine_liegt(u, normteil):  # noqa: F811
    spec = u.bestanden(NEU, bereiche=[])
    (u.kunde / NEUE_DATEI).write_bytes(b"gibt es schon")
    erg = modul.ausgabe(spec)
    assert codes(erg) == [BESTAND_ORIGINAL_GEAENDERT] and erg["warnungen"][-1]["datei"] == NEUE_DATEI


def test_ohne_ausgabe_keine_warnung_zum_original(u):
    """Kein geändertes Ergebnis: nichts zurückzukopieren, wie in Etappe 1."""
    spec = u.bestanden()
    u.lauf_pfad(GRUND).write_bytes(inhalt(GRUND))
    datei = lauf_datei(spec, 1, "protokoll")
    p = json.loads(datei.read_text(encoding="utf-8"))
    p["sha256"][GRUND] = sha256_datei(u.lauf_pfad(GRUND))
    datei.write_text(json.dumps(p), encoding="utf-8")
    (u.kunde / SCHLITTEN).write_bytes(b"der Kollege")
    erg = modul.ausgabe(spec)
    assert erg["dateien"] == [] and codes(erg) == [] and GRUND in erg["unveraendert"]


def test_ausgabe_aus_herkunft_schreibt_nicht_in_den_lauf(u):
    """Das Original liegt in einem eigenen Lauf (§8.5): Der ist das Original im Sinn von §3, geschrieben wird nur unter `ausgabe/`."""
    herkunft = u.r.arbeitsordner / "Pruefstation" / "lauf-30"
    herkunft.mkdir(parents=True)
    for rel, e in u.dateien.items():
        ziel = herkunft / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(inhalt(rel))
        e["original"] = str(ziel)
    ablage.schreibe_dateien(u.r, "A", 1, u.dateien)
    u.aufnahme["datei"]["original"] = str(herkunft / HAUPT)
    ablage.schreibe_herkunft(u.r, "A", 1, {"auftrag": "Pruefstation", "lauf": 30, "spec": "pruefstation.yaml"})
    spec = u.bestanden()
    vorher = {p: p.read_bytes() for p in herkunft.rglob("*") if p.is_file()}
    erg = modul.ausgabe(spec)
    assert erg["herkunft"] == {"auftrag": "Pruefstation", "lauf": 30, "spec": "pruefstation.yaml"}
    assert {p: p.read_bytes() for p in herkunft.rglob("*") if p.is_file()} == vorher
    assert Path(erg["dateien"][0]["original"]) == herkunft / GRUND and u.ausgegeben() == [GRUND]


def test_ohne_herkunft_steht_none_da(u):
    assert modul.ausgabe(u.bestanden())["herkunft"] is None


def test_alte_ausgabe_wandert_beiseite(u):
    """Lauf 1 ändert Grund, Lauf 2 nur Schlitten: Wer `ausgabe/` zurückkopiert, brächte sonst die verworfene Änderung mit."""
    spec = u.bestanden()
    erste = modul.ausgabe(spec)
    assert erste["alt"] is None and u.ausgegeben() == [GRUND]
    u.schreibe(MASS2, bereiche=[BEREICHE[1]])
    assert u.baue()["status"] == "ok"
    lauf_datei(spec, 2, "pruefbericht").write_text(json.dumps({"bestanden": True, "maengel": []}), encoding="utf-8")
    lauf_datei(spec, 2, "pruefer").write_text(json.dumps({"bestanden": True, "maengel": []}), encoding="utf-8")
    zweite = modul.ausgabe(spec, 2)
    alt = u.ausgabe_ordner().with_name("ausgabe_alt_1")
    assert zweite["alt"] == str(alt) and u.ausgegeben() == [SCHLITTEN]
    assert (alt / GRUND).read_bytes() == u.lauf_inhalt(GRUND)  # nichts gelöscht


def test_ausgabe_nimmt_die_naechste_freie_nummer(u):
    spec = u.bestanden()
    frueher = u.ausgabe_ordner().with_name("ausgabe_alt_1")
    frueher.mkdir(parents=True)
    (frueher / "x.txt").write_text("früher", encoding="utf-8")
    modul.ausgabe(spec)
    erg = modul.ausgabe(spec)
    assert erg["alt"] == str(u.ausgabe_ordner().with_name("ausgabe_alt_2")) and (frueher / "x.txt").read_text(encoding="utf-8") == "früher"
    assert u.ausgegeben() == [GRUND]


def test_leerer_ausgabe_ordner_wandert_nicht(u):
    spec = u.bestanden()
    u.ausgabe_ordner().mkdir(parents=True)
    assert modul.ausgabe(spec)["alt"] is None and not u.ausgabe_ordner().with_name("ausgabe_alt_1").exists()


def test_alte_ausgabe_wandert_auch_ohne_neue_datei(u):
    """Der Lauf gibt nichts aus: Unter `ausgabe/` darf dann auch nichts Altes als Ergebnis liegen."""
    spec = u.bestanden()
    modul.ausgabe(spec)
    u.lauf_pfad(GRUND).write_bytes(inhalt(GRUND))
    datei = lauf_datei(spec, 1, "protokoll")
    p = json.loads(datei.read_text(encoding="utf-8"))
    p["sha256"][GRUND] = sha256_datei(u.lauf_pfad(GRUND))
    datei.write_text(json.dumps(p), encoding="utf-8")
    erg = modul.ausgabe(spec)
    assert erg["dateien"] == [] and erg["alt"] and not u.ausgabe_ordner().exists()


def test_gesperrte_alte_ausgabe_bricht_vor_dem_kopieren_ab(u, monkeypatch):
    spec = u.bestanden()
    modul.ausgabe(spec)
    inhalt_vorher = (u.ausgabe_ordner() / GRUND).read_bytes()

    def gesperrt(self, ziel):
        raise PermissionError(13, "Zugriff verweigert")

    monkeypatch.setattr(Path, "rename", gesperrt)
    with pytest.raises(SwkiFehler, match="ausgabe"):
        modul.ausgabe(spec)
    assert (u.ausgabe_ordner() / GRUND).read_bytes() == inhalt_vorher


def test_ausgabe_liste_verschiebt_nichts(u):
    spec = u.bestanden()
    modul.ausgabe(spec)
    assert "alt" not in modul.ausgabe_liste(spec) and u.ausgegeben() == [GRUND]


def test_ausgabe_verlangt_bestandenen_lauf(u):
    spec = u.gebaut()
    with pytest.raises(BestandFehler) as e:
        modul.ausgabe(spec)
    assert e.value.daten["code"] == LAUF_NICHT_BESTANDEN and not u.ausgabe_ordner().exists()


def test_ausgabe_verweigert_von_hand_geaenderte_datei_ohne_punkt(u):
    """Geprüft ist, was im Protokoll steht: Auch eine Datei, die nicht ausgegeben würde, muss noch die gebaute sein."""
    spec = u.bestanden()
    u.lauf_pfad(SCHLITTEN).write_bytes(b"von Hand")
    with pytest.raises(SwkiFehler) as e:
        modul.ausgabe(spec)
    assert e.value.daten["code"] == "MANUELL_GEAENDERT" and not u.ausgabe_ordner().exists()


def test_datei_ohne_herkunft_im_protokoll_wird_nicht_ausgegeben(u):
    spec = u.bestanden()
    fremd = u.lauf_pfad("Fremd.SLDPRT")
    fremd.write_bytes(b"fremd")
    datei = lauf_datei(spec, 1, "protokoll")
    p = json.loads(datei.read_text(encoding="utf-8"))
    p["sha256"]["Fremd.SLDPRT"] = sha256_datei(fremd)
    datei.write_text(json.dumps(p), encoding="utf-8")
    with pytest.raises(SwkiFehler, match="Fremd.SLDPRT"):
        modul.ausgabe(spec)
    assert not u.ausgabe_ordner().exists()


def test_was_sonst_im_lauf_liegt_wird_nicht_ausgegeben(u):
    spec = u.bestanden()
    ordner = lauf_ordner(u.r, "A", 1)
    (ordner / "vergleich").mkdir()
    (ordner / "vergleich" / "vorher_teile_Grund.SLDPRT").write_bytes(b"vorher")
    modul.ausgabe(spec)
    assert u.ausgegeben() == [GRUND]


def test_schreibgeschuetzte_bestandskopien_stoeren_nicht(u):
    spec = u.bestanden()
    assert not (u.ordner / GRUND).stat().st_mode & stat.S_IWRITE
    modul.ausgabe(spec)
    assert os.access(u.ausgabe_ordner() / GRUND, os.W_OK)


# --- Bericht -------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("punkt, text", [
    (NEU, "neu: ISO 4762 M5x20"),
    ({"id": "k2", "typ": "komponente_neu", "wie": "Schraube-1"}, "neu wie Schraube-1"),
    ({"id": "k3", "typ": "komponente_entfernen", "komponente": "Schraube-2", "verknuepfungen": ["Abstand1"]},
     "Schraube-2 + Abstand1"),
    ({"id": "k4", "typ": "komponente_ersetzen", "komponente": "Schraube-3", "quelle": {"kaufteil": "Nanotec X"}}, "Schraube-3 → Nanotec X"),
    ({"id": "v1", "typ": "verknuepfung_neu", "art": "abstand", "wert": 5, "a": {"komponente": "k1"}, "b": {"komponente": "Grund-1"}},
     "abstand k1 – Grund-1"),
    (WERT, "Abstand1: 3 → 4"),
    ({"id": "w2", "typ": "verknuepfung_wert", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30}, "Hub (max): 25 → 30"),
    ({"id": "w3", "typ": "verknuepfung_loeschen", "verknuepfung": "Abstand1"}, "Abstand1"),
])
def test_punkt_text_der_baugruppen_punkte(punkt, text):
    assert _punkt_text(punkt) == text


def _bericht(u, ausgabe=None, **pruefbericht):
    letzter = {"maengel": [], "bilder": {}, "pruefungen": [], **pruefbericht}
    spec = {"name": "Haupt_Rev", "art": "aenderung", "bestand": {"datei": HAUPT, "aufnahme": 1}, "punkte": [
        {**MASS, "lage_folgen": ["Grund-1"]}, WERT]}
    return bericht_markdown(spec, "A", [], ("pruefer", "x"), letzter, None, None, [], ausgabe=ausgabe)


def test_bericht_nennt_lage_folgen_und_datei(u):
    text = _bericht(u)
    assert "Lage: Grund-1" in text and GRUND in text and "Wirkung auf Baugruppen" not in text


def test_bericht_differenzen_je_datei(u):
    a = {"art": "hinzu", "box": [0, 0, 0, 1, 1, 1], "volumen": 500.0, "bereich": 0}
    text = _bericht(u, differenzen={GRUND: {"Standard": [a], "Leicht": []}},
                    pruefungen=[{"id": f"{SCHLITTEN}/bereich", "ok": None, "konfiguration": "Standard", "hinweis": "kaputt"}])
    assert f"- {GRUND}, Standard: hinzu 500 mm³" in text and f"- {GRUND}, Leicht: keine Abweichung" in text
    text = _bericht(u, differenzen={SCHLITTEN: {"Standard": []}},
                    pruefungen=[{"id": f"{SCHLITTEN}/bereich", "ok": None, "konfiguration": "Standard", "hinweis": "kaputt"}])
    assert f"- {SCHLITTEN}, Standard: nicht nachgewiesen: kaputt" in text


def test_bericht_ohne_teilvergleich(u):
    assert "kein Teil verglichen" in _bericht(u, differenzen={})


def test_bericht_kollisionsliste_und_bestandsfehler(u):
    text = _bericht(u, pruefungen=[{"id": "kollision", "ok": False, "konfiguration": "Standard",
                                    "ist": [{"paar": ["A-1", "B-1"], "volumen": 2.0, "art": "neu"}],
                                    "bekannt": [{"paar": ["C-1", "D-1"], "volumen": 1.5}], "erlaubt": [{"paar": ["E-1", "F-1"], "volumen": 3.0}],
                                    "weggefallen": [{"paar": ["G-1", "H-1"], "volumen": None}]}],
                    bestandsfehler={"neuaufbau": ["Fase1: Code 7 (Standard)"], "verknuepfungen": [{"verknuepfung": "Kaputt1", "konfiguration": "Standard", "code": 7}],
                                    "kollisionen": [{"paar": ["C-1", "D-1"], "volumen": 1.5}], "bewegungen": [{"pruefung": "grenze:Hub", "hinweis": "ging durch"}]})
    for teil in ("neu: A-1 / B-1 (2 mm³)", "aus dem Bestand: C-1 / D-1 (1.5 mm³)", "erlaubt: E-1 / F-1 (3 mm³)", "weggefallen: G-1 / H-1",
                 "### Bestandsfehler", "Fase1: Code 7", "Kaputt1 (Standard): Code 7", "grenze:Hub: ging durch"):
        assert teil in text, teil


def test_bericht_bewegungen_warnungen_abdeckung(u):
    hub = {"komponente": "Schlitten-1", "art": "abstand", "min": 0.0, "max": 25.0, "gefahren": True, "stellungen": 9,
           "bewegt": ["Schlitten-1"], "kollisionen": [], "hinweis": None}
    weg = {"komponente": None, "min": None, "max": None, "gefahren": False, "stellungen": 0, "bewegt": [], "kollisionen": [],
           "hinweis": "min gleich max"}
    text = _bericht(u, bewegungen={"Hub": hub, "Klemme": weg}, warnungen=[{"code": "VERKNUEPFUNG_UNERREICHT", "meldung": "x fehlt"}],
                    nicht_abgedeckt=["Grenze y in Unterbaugruppe"], bilder_bewegung={"Hub-min": "a.png"})
    for teil in ("| Hub | Schlitten-1 | 0 … 25 | ja | 9 | Schlitten-1 | 0 | – |", "| Klemme | – | – | nein | 0 | – | 0 | min gleich max |",
                 "- VERKNUEPFUNG_UNERREICHT: x fehlt", "- Grenze y in Unterbaugruppe", "- Hub-min: `a.png`"):
        assert teil in text, teil
    assert "Grundstellung" not in text


def test_bericht_grenze_mit_namen_laeufe_trifft_den_alten_abschnitt_nicht(u):
    hub = {"komponente": "S-1", "min": 0.0, "max": 1.0, "gefahren": True, "stellungen": 2, "bewegt": [], "kollisionen": [], "hinweis": None}
    assert "| laeufe | S-1 |" in _bericht(u, bewegungen={"laeufe": hub})


def test_bericht_ausgabe_nennt_neue_dateien(u):
    text = _bericht(u, ausgabe={"dateien": [{"datei": NEUE_DATEI, "original": "K/n", "ausgabe": "A/n", "sha256": "x", "neu": True}],
                                "unveraendert": [], "warnungen": [], "herkunft": {"auftrag": "P", "lauf": 30, "spec": "s.yaml"}})
    assert f"- `{NEUE_DATEI}` (neu): neben die Hauptbaugruppe `K/n`, Ausgabe `A/n`" in text
    assert "Herkunft: Auftrag P, Lauf 30" in text


def test_bericht_ohne_pruefbericht_sagt_nicht_geprueft(u):
    spec = {"name": "Haupt_Rev", "art": "aenderung", "bestand": {"datei": HAUPT, "aufnahme": 1}, "punkte": [MASS]}
    text = bericht_markdown(spec, "A", [], ("bauen", "x"), None, None, None, [])
    for abschnitt in ("Kollisionen", "Bewegungen", "Warnungen", "Bestandsfehler (kein Mangel des Laufs)", "Nicht abgedeckt"):
        assert f"### {abschnitt}\n\n- nicht geprüft" in text, abschnitt
    assert "nichts bekannt" not in text and "keine Grenzverknüpfung" not in text


def test_bericht_ende_zu_ende(u):
    spec = u.gebaut(MASS, EIGENSCHAFT)
    u.pruefe()
    lauf_datei(spec, 1, "pruefer").write_text(json.dumps({"bestanden": True, "maengel": []}), encoding="utf-8")
    text = Path(befehle.bericht(spec)["bericht"]).read_text(encoding="utf-8")
    assert f"`{GRUND}`: Original `{u.kunde / GRUND}`" in text and "bestanden" in text
