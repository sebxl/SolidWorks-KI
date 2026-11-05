"""`swki bestand aufnehmen` für Baugruppen (Spec Bestandsdateien §8.1, §8.1a, §8.5, §8.7; Plan Etappe 2 Task 8) an der Attrappe,
ohne SolidWorks. Gelesen wird die Baugruppe echt über `lies_baugruppe`, die einzelnen Dateien über eine Attrappe von
`lies_bestand`."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.aenderungen import sha256_datei
from swki.bestand import aufnahme_baugruppe, befehle, sw_bestand
from swki.bestand.ablage import (aufnahmen, bestand_ordner, lade_aufnahme, lade_datei_aufnahme, lade_dateien, spec_laeufe)
from swki.bestand.sw_baugruppe_bestand import VERKNUEPFUNG_UNERREICHT
from swki.bestand.bewegung_bestand import vergleiche_bewegungen
from swki.bestand.fehler import (BESTAND_AUFTRAG_BELEGT, BESTAND_OFFEN, BESTAND_PFAD_FREMD, BESTAND_REFERENZ,
                                 BESTAND_REFERENZ_EXTERN,
                                 BESTAND_VERSION_NEUER, BestandFehler)
from swki.cli import main
from swki.compiler.fehler import BauFehler
from swki.konfig import Rechner, lade_standard
from tests.bestand.sw_attrappe_baugruppe import App, Komp, Mate, muster_baugruppe

ORIGINALE = ("Unter.SLDASM", "teile/Grund.SLDPRT", "teile/Schlitten.SLDPRT", "teile/Schraube.SLDPRT", "teile/Welle.SLDPRT")
GELESEN = {"version": 1, "konfigurationen": ["Standard"], "aktiv": "Standard", "material": "", "eigenschaften": {},
           "features": []}


@pytest.fixture
def u(tmp_path, monkeypatch):
    """Original im Kundenordner, Attrappe von SolidWorks, Rechner unter `tmp_path`."""
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    kunde = tmp_path / "kunde"
    (kunde / "teile").mkdir(parents=True)
    haupt = kunde / "Haupt.SLDASM"
    haupt.write_bytes(b"haupt")
    for rel in ORIGINALE:
        (kunde / rel).write_bytes(rel.encode())
    asm = muster_baugruppe(tmp_path / "unbekannt")
    app = App(haupt, [kunde / rel for rel in ORIGINALE], asm)
    app.abhaengig["Unter.SLDASM"] = [str(kunde / "teile" / "Welle.SLDPRT")]
    x = SimpleNamespace(r=r, haupt=haupt, kunde=kunde, app=app, asm=asm, gelesen=[], bilder=[], lesefehler=None)

    def lies(app_, model):
        app.ereignisse.append(("lies", model.GetTitle))
        x.gelesen.append(Path(model.GetPathName))
        if x.lesefehler is not None:
            raise x.lesefehler
        return dict(GELESEN)

    def bilder(app_, model, ordner):
        x.bilder.append(Path(model.GetPathName))
        app.ereignisse.append(("bild", model.GetTitle))
        return {}

    monkeypatch.setattr(aufnahme_baugruppe, "lade_rechner", lambda: r)
    monkeypatch.setattr(aufnahme_baugruppe, "verbinde", lambda jahr: app)
    monkeypatch.setattr(aufnahme_baugruppe, "lies_bestand", lies)
    monkeypatch.setattr(aufnahme_baugruppe, "screenshots", bilder)
    monkeypatch.setattr(aufnahme_baugruppe, "lies_baugruppe_einzeln", lambda app_, model: lies(app_, model))
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    monkeypatch.setattr(befehle, "verbinde", lambda jahr: app)
    return x


def _lauf(r, auftrag, n, protokoll):
    ordner = r.arbeitsordner / auftrag / f"lauf-{n}"
    ordner.mkdir(parents=True)
    if protokoll is not None:
        (ordner / "protokoll.json").write_text(json.dumps(protokoll), encoding="utf-8")
    return ordner


def test_kopiert_alle_und_liest_jede_datei_einmal(u):
    aus = aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    ordner = bestand_ordner(u.r, "a1", 1)
    kopien = [p.relative_to(ordner).as_posix() for p in ordner.rglob("*") if p.suffix.startswith(".SLD")]
    assert sorted(kopien) == sorted(["Haupt.SLDASM", *ORIGINALE])
    a = lade_aufnahme(u.r, "a1", 1)
    assert len(a["komponenten"]) == 15 and sum(k["datei"] == "teile/Schraube.SLDPRT" for k in a["komponenten"].values()) == 11
    assert sorted(p.name for p in u.gelesen) == sorted(Path(rel).name for rel in ORIGINALE)  # 11 Instanzen → eine Aufnahme
    assert aus["neu"] is True and aus["aufnahme"] == 1


def test_format_von_bestand_json(u):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    a = lade_aufnahme(u.r, "a1", 1)
    assert a["version"] == 2 and a["art"] == "baugruppe" and a["sw_jahr"] == 2025
    assert a["datei"]["name"] == "Haupt.SLDASM" and a["datei"]["original"] == str(u.haupt)
    assert a["datei"]["sha256"] == sha256_datei(u.haupt)
    assert a["datei"]["versionen"] == ["18000[2025/268]"] and a["datei"]["version_aelter"] is False
    assert "Haupt.SLDASM" not in a["dateien"] and set(a["dateien"]) == set(ORIGINALE)
    d = a["dateien"]["teile/Grund.SLDPRT"]
    assert d["art"] == "teil" and d["referenzen"] == [] and d["original"] == str(u.kunde / "teile" / "Grund.SLDPRT")
    assert d["sha256"] == sha256_datei(u.kunde / "teile" / "Grund.SLDPRT") and d["versionen"] and d["version_aelter"] is False
    assert "haupt" not in d
    unter = a["dateien"]["Unter.SLDASM"]
    assert unter["art"] == "baugruppe" and unter["referenzen"] == ["teile/Welle.SLDPRT"]
    assert a["kollisionen"] == [] and a["bewegungen"]["Hub"]["gefahren"] is True
    assert set(a["messung"]) == {"kopieren", "oeffnen", "lesen", "dateien", "fenster", "kollision", "bilder", "fahrt"}
    assert a["messung"]["lesen"]["s"] >= 0 and "mb" in a["messung"]["lesen"]


def test_datei_aufnahme_nennt_den_relativen_pfad(u):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    t = lade_datei_aufnahme(u.r, "a1", 1, "teile/Grund.SLDPRT")
    assert t["datei"]["name"] == "teile/Grund.SLDPRT" and t["sw_jahr"] == 2025 and t["datei"]["sha256"]


def test_dateien_json_traegt_die_angaben_und_die_hauptdatei(u):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    d = lade_dateien(u.r, "a1", 1)
    assert d["Haupt.SLDASM"]["haupt"] is True and d["Haupt.SLDASM"]["art"] == "baugruppe"
    assert d["teile/Grund.SLDPRT"]["art"] == "teil"


def test_abgeleitetes_teil_traegt_seine_referenz_relativ(u):
    u.app.abhaengig["Schlitten.SLDPRT"] = [str(u.kunde / "teile" / "Grund.SLDPRT")]
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert lade_aufnahme(u.r, "a1", 1)["dateien"]["teile/Schlitten.SLDPRT"]["referenzen"] == ["teile/Grund.SLDPRT"]


def test_teil_mit_referenz_auf_die_hauptbaugruppe(u):
    """In-Context-Teil: Das Ziel liegt in der Kopie (§8.1), also wird es aufgenommen."""
    u.app.abhaengig["Schlitten.SLDPRT"] = [str(u.haupt)]
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert lade_aufnahme(u.r, "a1", 1)["dateien"]["teile/Schlitten.SLDPRT"]["referenzen"] == ["Haupt.SLDASM"]


def test_referenz_eines_teils_ausserhalb_der_kopie_lehnt_ab(u):
    u.app.abhaengig["Schlitten.SLDPRT"] = ["D:\\Sonst\\Fremd.SLDPRT"]
    with pytest.raises(BestandFehler) as e:
        aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert e.value.daten["code"] == BESTAND_REFERENZ_EXTERN and aufnahmen(u.r, "a1") == []


def test_liest_nach_dem_schliessen_der_baugruppe(u):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    e = u.app.ereignisse
    zu = e.index(("zu", "Haupt.SLDASM"))
    lesen = [i for i, x in enumerate(e) if x[0] == "lies"]
    assert lesen and min(lesen) > zu
    offen = 0   # jede Datei einzeln: Es ist nie mehr als ein Dokument offen
    for art, _ in e:
        offen += {"offen": 1, "zu": -1}.get(art, 0)
        assert offen <= 1
    assert e[-2:] == [("bild", "Haupt.SLDASM"), ("zu", "Haupt.SLDASM")]


def test_oeffnet_nie_das_original(u):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    ordner = bestand_ordner(u.r, "a1", 1)
    assert u.app.geoeffnet and all(p.is_relative_to(ordner) for p in u.app.geoeffnet)


def test_liest_unsichtbar_nur_das_bild_im_fenster(u):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert u.app.sichtbarkeit.count(False) == len(ORIGINALE) + 1   # Baugruppe und jede Datei
    assert len(u.app.geoeffnet) == len(ORIGINALE) + 2 and u.bilder == [bestand_ordner(u.r, "a1", 1) / "Haupt.SLDASM"]


def test_kollision_und_fahrt_im_fenster(u, monkeypatch):
    """S19d P.d1: Ohne Fenster ist `InterferenceDetectionManager` `None`, keine Kollision wäre gelesen, die Fahrt bräche ab."""
    gelesen, echt = [], aufnahme_baugruppe.lies_kollisionen
    monkeypatch.setattr(aufnahme_baugruppe, "lies_kollisionen", lambda asm: gelesen.append(asm.sichtbar) or echt(asm))
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    a = lade_aufnahme(u.r, "a1", 1)
    assert gelesen == [True] and a["kollisionen"] == [] and a["bewegungen"]["Hub"]["gefahren"] is True


def test_datei_aus_neuerem_jahr(u):
    u.app.versionen["Schraube.SLDPRT"] = ("19000[2026/300]",)
    with pytest.raises(BestandFehler) as e:
        aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert e.value.daten["code"] == BESTAND_VERSION_NEUER and aufnahmen(u.r, "a1") == [] and u.app.geoeffnet == []


def test_aeltere_einzeldatei_steht_in_dateien(u):
    u.app.versionen["Schraube.SLDPRT"] = ("16000[2023/100]",)
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert lade_aufnahme(u.r, "a1", 1)["dateien"]["teile/Schraube.SLDPRT"]["version_aelter"] is True


def test_lightweight_komponente(u):
    u.asm.komp("Schraube-1").modell = None
    u.asm.komp("Schlitten-1").modell = None
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    a = lade_aufnahme(u.r, "a1", 1)
    assert a["komponenten"]["Schraube-1"]["status"] == {"Standard": 3} and a["bewegungen"]["Hub"]["gefahren"] is True


def test_unterdrueckte_komponente(u):
    u.asm.komp("Schraube-1").unterdrueckt.add("Standard")
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    k = lade_aufnahme(u.r, "a1", 1)["komponenten"]["Schraube-1"]
    assert k["unterdrueckt"] == {"Standard": True} and k["transform"] == {"Standard": None}


def test_warnung_offen(u):
    (u.kunde / "teile" / "~$Schraube.SLDPRT").write_bytes(b"x")
    aus = aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    w = next(w for w in aus["warnungen"] if w["code"] == BESTAND_OFFEN)
    assert w["datei"] == "teile/Schraube.SLDPRT" and "offen" in w["meldung"]
    assert lade_aufnahme(u.r, "a1", 1)["warnungen"] == aus["warnungen"]
    assert not list(bestand_ordner(u.r, "a1", 1).rglob("~$*"))


def test_gegenprobe_der_verknuepfungen_steht_in_den_warnungen(u):
    u.asm.versteckt.append(Mate(u.asm, "Versteckt1", 0))
    aus = aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert any(w["code"] == VERKNUEPFUNG_UNERREICHT for w in aus["warnungen"])
    assert any(w["code"] == VERKNUEPFUNG_UNERREICHT for w in lade_aufnahme(u.r, "a1", 1)["warnungen"])


def test_speicher_wird_vor_dem_oeffnen_gemessen(u, monkeypatch):
    """`SPEICHER_KNAPP` urteilt nach dem Stand zu Beginn: Nach dem Öffnen sähe frisches SolidWorks nie frisch aus."""
    stand = {"mb": 500.0}
    gefahren = {}
    wahr = aufnahme_baugruppe.oeffne_in

    def oeffne(*a, **k):
        stand["mb"] = 5000.0
        return wahr(*a, **k)

    def fahre(mech, a, grenzen, schritte, bekannt, grenze_mb, tol_mm, start_mb=None):
        gefahren["start_mb"] = start_mb
        return {}

    monkeypatch.setattr(aufnahme_baugruppe, "privat_mb", lambda pid: stand["mb"])
    monkeypatch.setattr(aufnahme_baugruppe, "oeffne_in", oeffne)
    monkeypatch.setattr(aufnahme_baugruppe, "fahre_bestand", fahre)
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert gefahren["start_mb"] == 500.0


def test_abdeckung_steht_in_den_warnungen(u):
    u.asm.komponente("Frei-1", "teile/Welle.SLDPRT", status=2)
    aus = aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert any("Frei-1 ist beweglich" in w["meldung"] for w in aus["warnungen"])
    assert not any("Schlitten-1" in w["meldung"] for w in aus["warnungen"])  # Partner der Grenze Hub


def test_herkunft_und_belegter_auftrag(u):
    """Original aus einem eigenen Lauf: `herkunft.json` in der Aufnahme, der Auftrag mit Spec-Läufen nimmt nichts auf."""
    lauf = _lauf(u.r, "alt", 30, {"auftrag": "alt", "lauf": 30, "spec": "alt.yaml"})
    haupt = lauf / "Haupt.SLDASM"
    haupt.write_bytes(b"haupt")
    u.app.original = haupt
    u.app.referenzen = [lauf / rel for rel in ORIGINALE]
    (lauf / "teile").mkdir()
    for rel in ORIGINALE:
        (lauf / rel).write_bytes(rel.encode())
    vorher = {p: p.stat().st_mtime_ns for p in lauf.rglob("*")}
    with pytest.raises(BestandFehler) as e:
        aufnahme_baugruppe.aufnehmen(haupt, "alt")
    assert e.value.daten["code"] == BESTAND_AUFTRAG_BELEGT and e.value.daten["laeufe"] == [30] and u.app.ereignisse == []
    aus = aufnahme_baugruppe.aufnehmen(haupt, "neu")
    assert aus["herkunft"] == {"auftrag": "alt", "lauf": 30, "spec": "alt.yaml"}
    gespeichert = json.loads((bestand_ordner(u.r, "neu", 1) / "herkunft.json").read_text(encoding="utf-8"))
    assert gespeichert == aus["herkunft"]
    assert {p: p.stat().st_mtime_ns for p in lauf.rglob("*")} == vorher    # der Lauf-Ordner bleibt unberührt
    assert not any(p.is_relative_to(lauf) for p in u.app.geoeffnet)


def test_spec_laeufe_zaehlen_laeufe_aus_aenderungen_nicht(u):
    _lauf(u.r, "a1", 1, {"bestand": {"sha256": "ab", "aufnahme": 1}})
    _lauf(u.r, "a1", 2, {"bestand": None})
    _lauf(u.r, "a1", 3, None)                # ohne lesbares Protokoll nie als frei werten
    (u.r.arbeitsordner / "a1" / "lauf-4").mkdir()
    (u.r.arbeitsordner / "a1" / "lauf-4" / "protokoll.json").write_text("{kaputt", encoding="utf-8")
    assert spec_laeufe(u.r, "a1") == [2, 3, 4]


def test_neue_fassung_im_auftrag_mit_aenderungs_lauf(u):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    _lauf(u.r, "a1", 1, {"bestand": {"sha256": "ab", "aufnahme": 1}})
    u.haupt.write_bytes(b"neue fassung")
    assert aufnahme_baugruppe.aufnehmen(u.haupt, "a1")["aufnahme"] == 2


def test_ohne_bewegung(u, monkeypatch):
    monkeypatch.setattr(aufnahme_baugruppe, "mechanik_fuer", lambda *a: pytest.fail("keine Mechanik ohne Bewegung"))
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1", ohne_bewegung=True)
    a = lade_aufnahme(u.r, "a1", 1)
    e = a["bewegungen"]["Hub"]
    assert not e["gefahren"] and "ohne Bewegung" in e["hinweis"] and a["messung"].get("fahrt", {}).get("s", 0) < 1


def test_ohne_bewegung_heisst_in_der_pruefung_nicht_nachgewiesen(u):
    """Spec §8.4: `ok: None`. `gefahren: False` wäre „im Bestand nicht gefahren, kein Soll“ und bestünde."""
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1", ohne_bewegung=True)
    a = lade_aufnahme(u.r, "a1", 1)
    e = {x["id"]: x for x in vergleiche_bewegungen(a, a, {"art": "aenderung", "punkte": [], "bereiche": []}, {})}
    assert e["bewegung:Hub"]["ok"] is None


def test_fahrt_speichert_nichts(u):
    u.asm.Save3 = lambda *a: pytest.fail("Fahrt speichert")
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    a = lade_aufnahme(u.r, "a1", 1)
    ordner = bestand_ordner(u.r, "a1", 1)
    assert a["bewegungen"]["Hub"]["gefahren"] is True and sha256_datei(ordner / "Haupt.SLDASM") == a["datei"]["sha256"]
    assert not os.access(ordner / "Haupt.SLDASM", os.W_OK)


def test_einzelnes_teil_geht_ueber_oeffne_in(u):
    """Pfadschutz auch beim Lesen je Datei: Eine Referenz aus der Kopie heraus öffnet nicht, die Aufnahme bleibt nicht liegen."""
    wahr = u.app.GetDocumentDependencies2

    def abhaengig(pfad, tief, suche, nur_lesen):
        if suche and Path(pfad).name == "Schraube.SLDPRT":
            return ("Fremd", "D:\\Kunde\\Fremd.SLDPRT")
        return wahr(pfad, tief, suche, nur_lesen)

    u.app.GetDocumentDependencies2 = abhaengig
    with pytest.raises(BestandFehler) as e:
        aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert e.value.daten["code"] == BESTAND_PFAD_FREMD and aufnahmen(u.r, "a1") == []
    assert not any(p.name == "Schraube.SLDPRT" for p in u.app.geoeffnet)


def test_pfad_fremd_nach_dem_oeffnen_entfernt_die_aufnahme(u):
    k = u.asm.komp("Grund-1")
    k.__class__ = type("Fremd", (Komp,), {"GetPathName": str(u.kunde / "teile" / "Grund.SLDPRT")})
    with pytest.raises(BestandFehler) as e:
        aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert e.value.daten["code"] == BESTAND_PFAD_FREMD and aufnahmen(u.r, "a1") == []
    assert ("zu", "Haupt.SLDASM") in u.app.ereignisse


def test_unterdrueckte_komponente_mit_gespeichertem_pfad_sichert_die_erste_sperre(u):
    """§8.1a nach S19c (T8.9, Entscheidung 2026-11-05): `GetPathName` einer unterdrückten Komponente nennt den gespeicherten Pfad,
    geladen ist nichts. Die Kopie ihrer Datei hat die erste Sperre aufgelöst, die Aufnahme geht durch."""
    u.asm.komp("Schraube-1").unterdrueckt.add("Standard")
    u.asm.pfade_wie_gespeichert = u.kunde
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert lade_aufnahme(u.r, "a1", 1)["komponenten"]["Schraube-1"]["unterdrueckt"] == {"Standard": True}


def test_nach_dem_umschalten_vom_original_geladen_verwirft_die_aufnahme(u):
    """Aktiv unterdrückt, in der anderen Konfiguration lädt die Komponente vom gespeicherten Pfad: Die zweite Sperre läuft nach
    jedem Wechsel beim Lesen erneut."""
    asm = muster_baugruppe(u.asm.wurzel, konfigurationen=("Standard", "Variante"))
    u.app.baugruppe = asm
    asm.komp("Schraube-1").unterdrueckt.add("Standard")
    asm.pfade_wie_gespeichert, asm.vom_original = u.kunde, {"Schraube-1"}
    with pytest.raises(BestandFehler) as e:
        aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert e.value.daten["code"] == BESTAND_PFAD_FREMD and "Umschalten auf Variante" in e.value.daten["wo"]
    assert e.value.daten["pfade"] == [str(u.kunde / "teile" / "Schraube.SLDPRT")]
    assert aufnahmen(u.r, "a1") == [] and ("zu", "Haupt.SLDASM") in u.app.ereignisse


def test_lesefehler_laesst_sich_nachholen(u):
    u.lesefehler = RuntimeError("COM weg")
    with pytest.raises(RuntimeError):
        aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert u.app.offen == [] and aufnahmen(u.r, "a1") == [1] and not (bestand_ordner(u.r, "a1", 1) / "bestand.json").exists()
    u.lesefehler = None
    assert aufnahme_baugruppe.aufnehmen(u.haupt, "a1")["aufnahme"] == 1
    assert lade_aufnahme(u.r, "a1", 1)["art"] == "baugruppe"


def test_baufehler_der_fahrt_schliesst_und_laesst_nachholen(u, monkeypatch):
    """Ruling Task 6: Ein `BauFehler` in der Fahrt bleibt laut, die Kopie liegt da, `--ohne-bewegung` oder ein neuer Versuch
    holt es nach."""
    def kaputt(*a, **k):
        raise BauFehler("REBUILD_FEHLER", "alt", schritt="rebuild")

    monkeypatch.setattr(aufnahme_baugruppe, "fahre_bestand", kaputt)
    with pytest.raises(BauFehler):
        aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert u.app.offen == [] and aufnahmen(u.r, "a1") == [1] and not (bestand_ordner(u.r, "a1", 1) / "bestand.json").exists()
    assert aufnahme_baugruppe.aufnehmen(u.haupt, "a1", ohne_bewegung=True)["aufnahme"] == 1


def test_gleiche_aufnahme_liest_nichts_neu(u):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    u.app.geoeffnet.clear()
    aus = aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert aus["neu"] is False and aus["aufnahme"] == 1 and u.app.geoeffnet == []


def test_geaenderte_einzeldatei_ist_eine_neue_aufnahme(u):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    (u.kunde / "teile" / "Grund.SLDPRT").write_bytes(b"anders")
    assert aufnahme_baugruppe.aufnehmen(u.haupt, "a1")["aufnahme"] == 2


def test_ausgabe_kompakt(u):
    aus = aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    assert {"zaehler", "komponenten", "verknuepfungen", "grenzen", "kollisionen", "dateien", "warnungen", "herkunft",
            "messung"} <= set(aus)
    assert aus["zaehler"]["komponenten"] == 15 and aus["zaehler"]["verknuepfungen"] == 3 and aus["zaehler"]["dateien"] == 5
    assert {"name": "Abstand1", "typ": "abstand", "wert": 3.0, "partner": ["Schraube-1", "Grund-1"]} in aus["verknuepfungen"]
    assert next(g for g in aus["grenzen"] if g["name"] == "Hub")["komponente"] == "Schlitten-1"
    assert aus["herkunft"] is None
    assert "transform" not in json.dumps(aus["komponenten"]) and "pruefungen" not in json.dumps(aus["grenzen"])


def test_weiche_nach_der_endung(u, monkeypatch):
    gerufen = []
    monkeypatch.setattr(aufnahme_baugruppe, "aufnehmen", lambda o, a, ohne_bewegung=False: gerufen.append((o, a,
                                                                                                           ohne_bewegung)) or {})
    befehle.aufnehmen(u.haupt, "a1", ohne_bewegung=True)
    assert gerufen == [(u.haupt, "a1", True)]


def test_teil_wie_bisher(u, monkeypatch):
    """`.sldprt` bleibt der Weg von Etappe 1: keine `dateien.json`, kein `art`, keine Baugruppen-Felder."""
    teil = u.kunde / "teile" / "Grund.SLDPRT"
    u.app.abhaengig.clear()
    gelesen = {**GELESEN, "externe_referenzen": [], "gleichungen": [], "variablen": {}, "reihenfolge": {}, "skizzen": {},
               "masse": [],
               "neuaufbau": [], "geometrie": {}, "tabelle": False, "einheitensystem": 5}
    monkeypatch.setattr(befehle, "oeffne_in", lambda app, pfad, wurzel, sichtbar=False,
                        nur_lesen=True: SimpleNamespace(GetTitle=pfad.name))
    monkeypatch.setattr(befehle, "lies_bestand", lambda app, model: gelesen)
    monkeypatch.setattr(befehle, "screenshots", lambda app, model, ordner: {})
    monkeypatch.setattr(aufnahme_baugruppe, "aufnehmen", lambda *a: pytest.fail("Teil geht nicht über den Baugruppen-Weg"))
    aus = befehle.aufnehmen(teil, "t1")
    a = lade_aufnahme(u.r, "t1", 1)
    assert aus["aufnahme"] == 1 and "art" not in a and "dateien" not in a and a["datei"]["name"] == "Grund.SLDPRT"
    assert not (bestand_ordner(u.r, "t1", 1) / "dateien.json").exists()


# --- swki bestand zeige --komponente -------------------------------------------------------------------------------------

@pytest.fixture
def aufgenommen(u, monkeypatch):
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    u.app.geoeffnet.clear()
    gesehen = []

    def zeige(app, asm, name, ziel):
        gesehen.append((name, ziel, asm.aktiv))

    monkeypatch.setattr(befehle, "zeige_komponente", zeige)
    u.gesehen = gesehen
    return u


def test_zeige_komponente_oeffnet_ueber_den_pfadschutz(aufgenommen):
    u = aufgenommen
    aus = befehle.zeige("a1", None, None, "Unter-1/Welle-1")
    ordner = bestand_ordner(u.r, "a1", 1)
    assert aus["bild"] == str(ordner / "bilder" / "zeige_Unter-1_Welle-1.png") and u.app.geoeffnet == [ordner / "Haupt.SLDASM"]
    assert u.gesehen == [("Unter-1/Welle-1", ordner / "bilder" / "zeige_Unter-1_Welle-1.png", "Standard")]
    assert u.app.offen == []


def test_zeige_komponente_schaltet_hinter_der_sperre_um(u, monkeypatch):
    """§8.1a: `zeige` wählt die Konfiguration, in der die aktiv unterdrückte Komponente lädt. Lädt sie dort vom gespeicherten
    Pfad, sperrt die zweite Sperre nach dem Wechsel, gezeigt wird nichts, geschlossen ohne Speichern (Korrektur 1, I1)."""
    asm = muster_baugruppe(u.asm.wurzel, konfigurationen=("Standard", "Variante"))
    u.app.baugruppe = asm
    asm.komp("Schraube-1").unterdrueckt.add("Standard")
    asm.pfade_wie_gespeichert = u.kunde
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    asm.vom_original = {"Schraube-1"}
    gesehen = []
    monkeypatch.setattr(befehle, "zeige_komponente", lambda app, m, name, ziel: gesehen.append(m.aktiv))
    with pytest.raises(BestandFehler) as e:
        befehle.zeige("a1", None, None, "Schraube-1")
    assert e.value.daten["code"] == BESTAND_PFAD_FREMD and "Umschalten auf Variante" in e.value.daten["wo"]
    assert gesehen == [] and u.app.offen == [] and asm.gespeichert == []


def test_zeige_komponente_in_der_anderen_konfiguration_ohne_fund(u, monkeypatch):
    asm = muster_baugruppe(u.asm.wurzel, konfigurationen=("Standard", "Variante"))
    u.app.baugruppe = asm
    asm.komp("Schraube-1").unterdrueckt.add("Standard")
    aufnahme_baugruppe.aufnehmen(u.haupt, "a1")
    gesehen = []
    monkeypatch.setattr(befehle, "zeige_komponente", lambda app, m, name, ziel: gesehen.append(m.aktiv))
    assert befehle.zeige("a1", None, None, "Schraube-1")["konfiguration"] == "Variante" and gesehen == ["Variante"]


def test_zeige_unbekannte_komponente(aufgenommen):
    with pytest.raises(BestandFehler) as e:
        befehle.zeige("a1", None, None, "Gibt-es-nicht")
    assert e.value.daten["code"] == BESTAND_REFERENZ and aufgenommen.app.geoeffnet == []


def test_zeige_genau_eines_von_dreien(aufgenommen):
    with pytest.raises(BestandFehler):
        befehle.zeige("a1", "D1@Skizze1", None, "Grund-1")
    with pytest.raises(BestandFehler):
        befehle.zeige("a1", None, None, None)


def test_zeige_komponente_in_der_ersten_konfiguration_ohne_unterdrueckung():
    a = {"aktiv": "A", "konfigurationen": ["A", "B"], "komponenten": {"K-1": {"unterdrueckt": {"A": True, "B": False}}}}
    assert befehle.komponente_sichtbar_in(a, "K-1") == "B"


def test_zeige_komponente_an_einer_teil_aufnahme(u):
    from tests.bestand.beispiel_aufnahme import AUFNAHME
    from swki.bestand.ablage import schreibe_aufnahme

    schreibe_aufnahme(u.r, "t1", 1, json.loads(json.dumps(AUFNAHME)))
    with pytest.raises(BestandFehler) as e:
        befehle.zeige("t1", None, None, "K-1")
    assert e.value.daten["code"] == BESTAND_REFERENZ


def test_zeige_komponente_waehlt_die_komponente(u, monkeypatch):
    monkeypatch.setattr(sw_bestand, "_aufnahme", _rahmen)
    monkeypatch.setattr(sw_bestand, "_einpassen", lambda model, ansicht: None)
    bilder = []
    monkeypatch.setattr(sw_bestand.sw, "speichere", lambda model, pfad, kopie=False: bilder.append((pfad, model.auswahl.Name2,
                                                                                                    kopie)))
    sw_bestand.zeige_komponente(None, u.asm, "Grund-1", Path("x.png"))
    assert bilder == [(Path("x.png"), "Grund-1", True)] and u.asm.auswahl is None


def test_zeige_komponente_in_einer_unterbaugruppe_gibt_es_nicht_mehr(u):
    with pytest.raises(BestandFehler) as e:
        sw_bestand.zeige_komponente(None, u.asm, "Weg-1", Path("x.png"))
    assert e.value.daten["code"] == BESTAND_REFERENZ


class _rahmen:  # noqa: N801 (steht für einen Kontextmanager)
    def __init__(self, app, model):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# --- Kommandozeile ------------------------------------------------------------------------------------------------------

def test_cli_aufnehmen_mit_baugruppe(u, monkeypatch, capsys):
    gerufen = []
    monkeypatch.setattr(befehle, "aufnehmen", lambda p, a, o=False: gerufen.append((p, a, o)) or {"ok": True})
    assert main(["bestand", "aufnehmen", str(u.haupt), "--auftrag", "a1", "--ohne-bewegung"]) == 0
    assert gerufen == [(u.haupt, "a1", True)]


def test_standard_traegt_was_die_fahrt_braucht():
    s = lade_standard()
    assert s["bewegung_schritte"] > 0 and s["speicher_grenze_mb"] > 0 and s["toleranzen"]["anker_mm"] > 0
