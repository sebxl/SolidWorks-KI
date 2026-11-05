"""Punkt-Handler der Baugruppe an der Attrappe (Spec Bestandsdateien §4.1, §8.2, §8.3; Plan Etappe 2 Task 9). Ungemessen: gegen
den API-Index, S19 Zeile e kann die Attrappe korrigieren. Rückgaben von SolidWorks beweisen nichts, darum prüfen die Tests vor
allem, was nach dem Neuaufbau nachgemessen wird."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.baugruppe import bau, sw_baugruppe
from swki.baugruppe.fehler import KOMPONENTE_FEHLER, TEIL_BAU, VERKNUEPFUNG_FEHLER
from swki.baugruppe.modell import Quelle
from swki.baugruppe.referenzen import TeilReferenz
from swki.bestand import punkte_baugruppe
from swki.bestand.fehler import BESTAND_ALTWERT, BESTAND_REFERENZ, NAME_BELEGT, VERKNUEPFUNGEN_FEHLEN
from swki.bestand.punkte_baugruppe import (PUNKTE, BauKontext, NeueDatei, hole_neue_dateien, loesche_komponente, punkt_handler)
from swki.bestand.sw_baugruppe_bestand import lies_komponenten, lies_verknuepfungen
from swki.bestand.vergleich_baugruppe import ersetzen_ziele, vergleiche_baugruppe
from swki.compiler.anker import AnkerFehler
from swki.compiler.fehler import REFERENZ_NICHT_GEFUNDEN, UNBEKANNTER_TYP, BauFehler
from swki.compiler.protokoll import Protokoll
from swki.normteile.fehler import NormteilFehler
from swki.pruefung.geometrie import Messgeometrie
from tests.bestand.sw_attrappe_baugruppe import geschuetzt, lage, muster_baugruppe

KONFIGURATIONEN = ("Standard", "Leicht")
QUELLE = {"normteil": "ISO 4762 M5x20"}
SCHLUESSEL = "normteil:ISO 4762 M5x20:"
ALLE_SCHRAUBEN = {"id": "p1", "komponente": "Schraube-1", "quelle": QUELLE, "alle_instanzen": True}


def kontext_von(tmp_path: Path, spec: dict | None = None, konfigurationen=KONFIGURATIONEN) -> BauKontext:
    ordner = tmp_path / "A1" / "lauf-3"
    ordner.mkdir(parents=True)
    asm = geschuetzt(muster_baugruppe(ordner, konfigurationen))
    auftrag = tmp_path / "auftraege" / "A1"
    auftrag.mkdir(parents=True)
    aufnahme = {"konfigurationen": list(konfigurationen), "aktiv": konfigurationen[0], "dateien": {},
                "komponenten": lies_komponenten(asm, list(konfigurationen))}
    return BauKontext(SimpleNamespace(), asm, spec or {"punkte": [], "parameter": {"H": 12.5}}, auftrag / "rev.yaml", ordner,
                      aufnahme, {"toleranzen": {"anker_mm": 0.01}}, protokoll=Protokoll("A1", "rev.yaml", 3, 2025))


@pytest.fixture
def b(tmp_path):
    return kontext_von(tmp_path)


def neue_datei(b: BauKontext, name="ISO4762_M5x20.sldprt", art="normteil", schluessel=SCHLUESSEL) -> Path:
    """Was `hole_neue_dateien` hinterlässt, ohne Bibliothek und SolidWorks."""
    pfad = b.ordner / name
    model = SimpleNamespace(GetPartBox=lambda welt: (-0.004, -0.002, 0.0, 0.004, 0.002, 0.020), GetPathName=str(pfad))
    ctx = SimpleNamespace(model=model, ergebnisse={})
    b.quellen[schluessel] = NeueDatei(pfad, art, ctx)
    b.kontexte[name.casefold()] = ctx
    return pfad


def verbinde(a="Grund-1", b="Schraube-1", id="v1", art="parallel", **mehr) -> dict:
    return {"id": id, "art": art, "a": {"komponente": a, "nahe": [0, 0, 0]}, "b": {"komponente": b, "nahe": [0, 0, 0]}, **mehr}


def komponenten(b):
    return lies_komponenten(b.asm, b.aufnahme["konfigurationen"])


def mates(b):
    return lies_verknuepfungen(b.asm, b.aufnahme["konfigurationen"])


# --- Register ------------------------------------------------------------------------------------------------------------

def test_register_kennt_die_sechs_typen():
    assert set(PUNKTE) == {"komponente_neu", "komponente_entfernen", "komponente_ersetzen", "verknuepfung_neu",
                           "verknuepfung_wert", "verknuepfung_loeschen"}


def test_unbekannter_typ_bricht_ab():
    with pytest.raises(BauFehler) as e:
        punkt_handler("mass")
    assert e.value.code == UNBEKANNTER_TYP


# --- fuege_ein -----------------------------------------------------------------------------------------------------------

def test_fuege_ein_ohne_konfiguration_bleibt_wie_bisher(b):
    pfad = b.ordner / "Neu.SLDPRT"
    sw_baugruppe.fuege_ein(b.app, b.asm, pfad, [0, 0, 0, 10, 20, 30])
    e = b.asm.eingefuegt[-1]
    assert (e["option"], e["neuer_name"], e["benutze"], e["konfiguration"]) == (0, "", False, "")
    assert e["mitte"] == (0.005, 0.01, 0.015)


def test_fuege_ein_mit_benannter_konfiguration(b):
    sw_baugruppe.fuege_ein(b.app, b.asm, b.ordner / "Neu.SLDPRT", [0] * 6, "Lang")
    e = b.asm.eingefuegt[-1]
    assert (e["option"], e["benutze"], e["konfiguration"]) == (0, True, "Lang")
    assert b.asm.komp("Neu-1").ReferencedConfiguration == "Lang"


# --- hole_neue_dateien ---------------------------------------------------------------------------------------------------

@pytest.fixture
def bibliothek(tmp_path, monkeypatch):
    """Normteil- und Kaufteil-Bibliothek, Öffnen und Kontext ohne SolidWorks; `geoeffnet` listet die Pfade."""
    quelle = tmp_path / "bibliothek"
    quelle.mkdir()
    (quelle / "ISO4762_M5x20.sldprt").write_bytes(b"normteil")
    (quelle / "HST_K1.sldprt").write_bytes(b"kaufteil")
    aufrufe = SimpleNamespace(geoeffnet=[], kontexte=[], hole=[])

    def oeffne_in(app, pfad, wurzel, sichtbar=False, nur_lesen=True):
        aufrufe.geoeffnet.append((Path(pfad), Path(wurzel), sichtbar, nur_lesen))
        return SimpleNamespace(GetPathName=str(pfad), GetPartBox=lambda welt: (0.0,) * 6)

    def kontext_aus_datei(app, model, spec, spec_pfad, tol, protokoll):
        aufrufe.kontexte.append((spec, spec_pfad, tol, protokoll))
        return SimpleNamespace(model=model, ergebnisse={})

    def normteil_quelle(q, pfad):
        return Quelle("normteil", {"art": "teil", "features": []}, norm="ISO 4762", groesse="M5", laenge=20.0,
                      schluessel="ISO4762_M5x20"), []

    def hole_normteil(norm, groesse, variante):
        aufrufe.hole.append((norm, groesse, variante))
        return {"pfad": str(quelle / "ISO4762_M5x20.sldprt"), "gebaut": False}

    def kaufteil_quelle(q, pfad):
        return Quelle("kaufteil", {"art": "teil", "features": []}, schluessel="HST_K1",
                      eintrag={"hersteller": "HST", "bestellnummer": "K1"}), []

    def hole_kaufteil(text):
        aufrufe.hole.append(text)
        return {"pfad": str(quelle / "HST_K1.sldprt"), "gebaut": True, "pruefsumme": "abc", "gewinde_modell": {}}

    monkeypatch.setattr(punkte_baugruppe, "oeffne_in", oeffne_in)
    monkeypatch.setattr(punkte_baugruppe, "kontext_aus_datei", kontext_aus_datei)
    monkeypatch.setattr(punkte_baugruppe, "normteil_quelle", normteil_quelle)
    monkeypatch.setattr(punkte_baugruppe, "kaufteil_quelle", kaufteil_quelle)
    monkeypatch.setattr(punkte_baugruppe.normteil_befehle, "hole", hole_normteil)
    monkeypatch.setattr(punkte_baugruppe.kaufteil_befehle, "hole", hole_kaufteil)
    monkeypatch.setattr(punkte_baugruppe, "lade_rechner", lambda: SimpleNamespace(sw_jahr=2025))
    monkeypatch.setattr(bau, "bibliotheksordner", lambda r: quelle)
    monkeypatch.setattr(bau, "lies_eintrag", lambda ordner, schluessel: {"pruefsumme": "xyz"})
    monkeypatch.setattr(bau, "angaben_fuer_bericht", lambda eintrag: {"quelle": "beleg"})
    return aufrufe


def test_neu_aus_normteil_liegt_neben_der_baugruppe(tmp_path, bibliothek):
    p = {"id": "p1", "typ": "komponente_neu", "quelle": QUELLE}
    b = kontext_von(tmp_path, {"punkte": [p]})
    dateien = hole_neue_dateien(b, b.spec)
    ziel = b.ordner / "ISO4762_M5x20.sldprt"
    assert dateien == {"ISO4762_M5x20.sldprt": ziel}
    assert ziel.read_bytes() == b"normteil"
    assert bibliothek.hole == [("ISO 4762", "M5x20", None)]
    assert bibliothek.geoeffnet == [(ziel, b.ordner, False, False)]
    assert b.protokoll.normteile["ISO4762_M5x20"]["pruefsumme"] == "xyz"
    assert punkt_handler("komponente_neu")(b, p) == ["ISO4762_M5x20-1"]
    assert b.neue == {"p1": ["ISO4762_M5x20-1"]}
    assert b.asm.eingefuegt[-1]["pfad"] == str(ziel)
    assert komponenten(b)["ISO4762_M5x20-1"]["datei"] == "ISO4762_M5x20.sldprt"


def test_kaufteil_kommt_aus_dem_katalog_neben_die_baugruppe(tmp_path, bibliothek):
    b = kontext_von(tmp_path, {"punkte": [{"id": "p1", "typ": "komponente_ersetzen", "komponente": "Grund-1",
                                           "quelle": {"kaufteil": "HST K1"}}]})
    assert hole_neue_dateien(b, b.spec) == {"HST_K1.sldprt": b.ordner / "HST_K1.sldprt"}
    assert bibliothek.hole == ["HST K1"]
    assert b.protokoll.kaufteile["HST_K1"]["pruefsumme"] == "abc" and b.protokoll.kaufteile["HST_K1"]["quelle"] == "beleg"


def test_zwei_punkte_mit_gleicher_quelle_holen_einmal(tmp_path, bibliothek):
    punkte = [{"id": f"p{i}", "typ": "komponente_neu", "quelle": QUELLE} for i in (1, 2)]
    b = kontext_von(tmp_path, {"punkte": punkte})
    assert len(hole_neue_dateien(b, b.spec)) == 1
    assert len(bibliothek.hole) == 1 and len(b.offen) == 1
    punkt_handler("komponente_neu")(b, punkte[0])
    punkt_handler("komponente_neu")(b, punkte[1])
    assert b.neue == {"p1": ["ISO4762_M5x20-1"], "p2": ["ISO4762_M5x20-2"]}


def test_punkte_ohne_quelle_holen_nichts(tmp_path, bibliothek):
    b = kontext_von(tmp_path, {"punkte": [{"id": "p1", "typ": "komponente_neu", "wie": "Schraube-1"}]})
    assert hole_neue_dateien(b, b.spec) == {} and not bibliothek.hole


def test_vorhandene_datei_wird_nicht_ueberschrieben(tmp_path, bibliothek):
    b = kontext_von(tmp_path, {"punkte": [{"id": "p1", "typ": "komponente_neu", "quelle": QUELLE}]})
    (b.ordner / "ISO4762_M5x20.sldprt").write_bytes(b"vom kollegen")
    with pytest.raises(BauFehler) as e:
        hole_neue_dateien(b, b.spec)
    assert e.value.code == NAME_BELEGT
    assert (b.ordner / "ISO4762_M5x20.sldprt").read_bytes() == b"vom kollegen"


def test_fehler_der_bibliothek_bricht_mit_ihrem_code_ab(tmp_path, bibliothek, monkeypatch):
    def scheitert(*_):
        raise NormteilFehler("NORMVORLAGE_UNGEPRUEFT", "kein Urteil")

    monkeypatch.setattr(punkte_baugruppe.normteil_befehle, "hole", scheitert)
    b = kontext_von(tmp_path, {"punkte": [{"id": "p1", "typ": "komponente_neu", "quelle": QUELLE}]})
    with pytest.raises(BauFehler) as e:
        hole_neue_dateien(b, b.spec)
    assert e.value.code == "NORMVORLAGE_UNGEPRUEFT" and "ISO 4762 M5x20" in str(e.value)


def test_unbekanntes_normteil_nennt_den_befund(tmp_path, bibliothek, monkeypatch):
    monkeypatch.setattr(punkte_baugruppe, "normteil_quelle", lambda q, pfad: (None, [{"pfad": pfad, "meldung": "gibt es nicht"}]))
    b = kontext_von(tmp_path, {"punkte": [{"id": "p1", "typ": "komponente_neu", "quelle": QUELLE}]})
    with pytest.raises(BauFehler) as e:
        hole_neue_dateien(b, b.spec)
    assert "gibt es nicht" in str(e.value)


@pytest.fixture
def teil_bau(monkeypatch):
    """`baue_teil_dokument` und `speichere` ohne SolidWorks. `aufrufe.fehler` macht den Bau scheitern."""
    aufrufe = SimpleNamespace(fehler=None, spec=None, spec_pfad=None, auftrag=None, gespeichert=[])

    def baue(app, r, standard, spec, spec_pfad, auftrag, protokoll):
        aufrufe.spec, aufrufe.spec_pfad, aufrufe.auftrag = spec, spec_pfad, auftrag
        model = SimpleNamespace(GetPathName="", GetPartBox=lambda welt: (0.0,) * 6)
        return model, SimpleNamespace(model=model, ergebnisse={}), aufrufe.fehler

    def speichere(model, pfad):
        aufrufe.gespeichert.append(pfad)
        model.GetPathName = str(pfad.with_suffix(".SLDPRT"))  # S12: GetPathName schreibt die Endung groß

    monkeypatch.setattr(punkte_baugruppe, "baue_teil_dokument", baue)
    monkeypatch.setattr(punkte_baugruppe.sw, "speichere", speichere)
    monkeypatch.setattr(punkte_baugruppe, "lade_rechner", lambda: SimpleNamespace(sw_jahr=2025))
    return aufrufe


def test_teil_quelle_baut_aus_der_freigegebenen_spec(tmp_path, teil_bau):
    b = kontext_von(tmp_path, {"punkte": [{"id": "p1", "typ": "komponente_neu", "quelle": {"teil": "halter.yaml"}}]})
    (b.spec_pfad.parent / "halter.yaml").write_text("name: Spaeter_geaendert\n", encoding="utf-8")
    (b.spec_pfad.parent / "halter.freigegeben.yaml").write_text("name: Halter\nmaterial: S235\n", encoding="utf-8")
    dateien = hole_neue_dateien(b, b.spec)
    assert teil_bau.spec == {"name": "Halter", "material": "S235"}
    assert teil_bau.spec_pfad == b.spec_pfad.parent / "halter.yaml"
    assert teil_bau.auftrag == "A1"   # Kopfbaustein Auftrag wie bei eigenen Teilen
    assert teil_bau.gespeichert == [b.ordner / "Halter.sldprt"]
    assert dateien == {"Halter.SLDPRT": b.ordner / "Halter.SLDPRT"}
    assert b.protokoll.teile["halter.yaml"]["lauf"] == 3 and b.protokoll.teile["halter.yaml"]["status"] == "ok"
    assert "halter.sldprt" in b.kontexte and len(b.offen) == 1


def test_gescheitertes_teil_wird_nie_gespeichert(tmp_path, teil_bau):
    teil_bau.fehler = BauFehler("REBUILD_FEHLER", "Skizze offen", schritt="rebuild")
    b = kontext_von(tmp_path, {"punkte": [{"id": "p1", "typ": "komponente_neu", "quelle": {"teil": "halter.yaml"}}]})
    (b.spec_pfad.parent / "halter.freigegeben.yaml").write_text("name: Halter\n", encoding="utf-8")
    with pytest.raises(BauFehler) as e:
        hole_neue_dateien(b, b.spec)
    assert e.value.code == TEIL_BAU and "Skizze offen" in str(e.value)
    assert not teil_bau.gespeichert
    assert b.protokoll.teile["halter.yaml"]["status"] == "fehler"
    assert len(b.offen) == 1   # bleibt offen, schließt der Bau


# --- komponente_neu ------------------------------------------------------------------------------------------------------

def test_neu_wie_komponente_gleiche_datei_gleiche_konfiguration(b):
    b.asm.komp("Schraube-1").referenz = "Lang"
    namen = punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    assert namen == ["Schraube-12"] and b.neue == {"p1": ["Schraube-12"]}
    e = b.asm.eingefuegt[-1]
    assert e["pfad"] == str(b.ordner / "teile" / "Schraube.SLDPRT") and e["konfiguration"] == "Lang" and e["benutze"] is True
    k = komponenten(b)["Schraube-12"]
    assert k["datei"] == "teile/Schraube.SLDPRT" and k["konfigurationen"] == {"Standard": "Lang", "Leicht": "Lang"}


def test_neu_wie_folgt_der_konfiguration_je_baugruppen_konfiguration(b):
    """Die Vorlage kann in jeder Konfiguration der Baugruppe eine andere ihres Teils zeigen; `_punkt_komponente_neu` vergleicht je
    Konfiguration."""
    b.asm.komp("Schraube-1").referenzen = {"Standard": "Lang", "Leicht": "Kurz"}
    punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    assert komponenten(b)["Schraube-12"]["konfigurationen"] == {"Standard": "Lang", "Leicht": "Kurz"}


def test_neu_wie_mit_ausdruecklicher_konfiguration(b):
    punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1", "konfiguration": "Kurz"})
    assert komponenten(b)["Schraube-12"]["konfigurationen"] == {"Standard": "Kurz", "Leicht": "Kurz"}


def test_neu_wie_unterdrueckte_vorlage_mit_aktiver_instanz_laedt_nichts(b, monkeypatch):
    """Plan Review Focus 4: `GetModelDoc2` ist dann `None`, die Datei steht trotzdem fest. Geladen ist sie über Schraube-2, ein
    zweites Öffnen bräche ab (`PruefFehler`: bereits offen)."""
    monkeypatch.setattr(punkte_baugruppe, "oeffne_in", lambda *a, **k: pytest.fail("Die Datei ist schon geladen"))
    b.asm.komp("Schraube-1").unterdrueckt.add("Standard")
    assert punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"}) == ["Schraube-12"]
    assert komponenten(b)["Schraube-12"]["unterdrueckt"] == {"Standard": False, "Leicht": False}


def test_neu_wie_nimmt_den_pfad_im_lauf_nie_den_gespeicherten(b, tmp_path, monkeypatch):
    """§8.1a: `GetPathName` einer unterdrückten Komponente nennt den gespeicherten Pfad, in der Kopie also den Kundenordner. Ist
    keine Instanz aktiv, lädt der Handler die Datei selbst, über den Pfadschutz."""
    geoeffnet = []

    def oeffne_in(app, pfad, wurzel, sichtbar, nur_lesen):
        geoeffnet.append((pfad, wurzel))
        return "teil"

    monkeypatch.setattr(punkte_baugruppe, "oeffne_in", oeffne_in)
    b.asm.pfade_wie_gespeichert = tmp_path / "kundenordner"
    geschuetzt(b.asm, [b.ordner / "teile" / "Schraube.SLDPRT"])  # Sperre 1 hat die Kopie aufgelöst
    b.aufnahme["dateien"] = {"teile/Schraube.SLDPRT": {}}
    for n in range(1, 12):
        b.asm.komp(f"Schraube-{n}").unterdrueckt.add("Standard")
    punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    soll = b.ordner / "teile" / "Schraube.SLDPRT"
    assert b.asm.eingefuegt[-1]["pfad"] == str(soll)
    assert geoeffnet == [(soll, b.ordner)] and b.offen == ["teil"]


def test_neu_wie_ohne_lesbare_datei_bricht_ab(b, monkeypatch):
    roh = lies_komponenten

    def ohne_datei(*argumente):
        k = roh(*argumente)
        k["Schraube-1"]["datei"] = None
        return k

    monkeypatch.setattr(punkte_baugruppe, "lies_komponenten", ohne_datei)
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    assert e.value.code == KOMPONENTE_FEHLER and not b.asm.eingefuegt


def test_neu_wie_ohne_lesbare_konfiguration_bricht_ab(b, monkeypatch):
    roh = lies_komponenten

    def ohne_konfiguration(*argumente):
        k = roh(*argumente)
        del k["Schraube-1"]["konfigurationen"]["Leicht"]
        return k

    monkeypatch.setattr(punkte_baugruppe, "lies_komponenten", ohne_konfiguration)
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    assert e.value.code == KOMPONENTE_FEHLER and "Leicht" in str(e.value) and not b.asm.eingefuegt


def test_neu_wie_unbekannte_vorlage(b):
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Fehlt-1"})
    assert e.value.code == BESTAND_REFERENZ


def test_neu_in_allen_konfigurationen_aktiv(b):
    """S19e T9.2: Eine neue Komponente ist anders als ein neues Feature (S18c) in allen Konfigurationen aktiv. Wäre sie es nicht,
    hebt der Handler auf (nächster Test)."""
    punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    assert komponenten(b)["Schraube-12"]["unterdrueckt"] == {"Standard": False, "Leicht": False}
    assert b.asm.aktiv == "Standard"


def test_neu_nur_in_der_aktiven_wird_aufgehoben(b):
    b.asm.neu_nur_in_der_aktiven = True
    punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    assert komponenten(b)["Schraube-12"]["unterdrueckt"] == {"Standard": False, "Leicht": False}


def test_fixieren_wirkt_in_allen_konfigurationen(b, monkeypatch):
    """S19e T9.6: `FixComponent` in einer Konfiguration fixiert in allen; die Schleife je Konfiguration ruft es einmal."""
    aufrufe, echt = [], b.asm.FixComponent
    monkeypatch.setattr(b.asm, "FixComponent", lambda: (aufrufe.append(b.asm.aktiv), echt())[1])
    punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1", "fixiert": True})
    assert aufrufe == ["Standard"] and komponenten(b)["Schraube-12"]["fixiert"] == {"Standard": True, "Leicht": True}


def test_neu_bleibt_unterdrueckt_ist_ein_fehler(b):
    b.asm.wirkungslos = True  # alle Rückgaben melden Erfolg, nur das Nachmessen sieht es
    b.asm.neu_nur_in_der_aktiven = True
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    assert e.value.code == KOMPONENTE_FEHLER and "Leicht" in str(e.value) and e.value.schritt == "nachmessen"
    assert b.neue == {}


def test_neu_fixiert_in_allen_konfigurationen(b):
    punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1", "fixiert": True})
    assert komponenten(b)["Schraube-12"]["fixiert"] == {"Standard": True, "Leicht": True}


def test_neu_ohne_angabe_ist_nicht_fixiert(b):
    punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    assert komponenten(b)["Schraube-12"]["fixiert"] == {"Standard": False, "Leicht": False}


def test_neu_aus_quelle_mit_konfiguration_und_box(b):
    pfad = neue_datei(b)
    punkt_handler("komponente_neu")(b, {"id": "p1", "quelle": QUELLE, "konfiguration": "Lang"})
    e = b.asm.eingefuegt[-1]
    assert e["pfad"] == str(pfad) and e["konfiguration"] == "Lang"
    assert e["mitte"] == pytest.approx((0.0, 0.0, 0.010))  # Boxzentrum des Teils, wie beim Einfügen in eigene Baugruppen
    assert komponenten(b)["ISO4762_M5x20-1"]["konfigurationen"] == {"Standard": "Lang", "Leicht": "Lang"}


# --- komponente_entfernen ------------------------------------------------------------------------------------------------

def test_entfernen_nimmt_komponente_und_genannte_verknuepfungen(b):
    namen = punkt_handler("komponente_entfernen")(b, {"id": "p1", "komponente": "Schlitten-1", "verknuepfungen": ["Hub"]})
    assert namen == ["Schlitten-1"]
    assert "Schlitten-1" not in komponenten(b) and "Hub" not in mates(b)
    assert b.asm.loeschoptionen == [0]


def test_entfernen_prueft_die_mitgenommenen_verknuepfungen(b):
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_entfernen")(b, {"id": "p1", "komponente": "Schlitten-1", "verknuepfungen": []})
    assert e.value.code == VERKNUEPFUNGEN_FEHLEN and "Hub" in str(e.value)


def test_entfernen_genannte_verknuepfung_bleibt_stehen(b):
    b.asm.bleibt_stehen = {"Hub"}
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_entfernen")(b, {"id": "p1", "komponente": "Schlitten-1", "verknuepfungen": ["Hub"]})
    assert e.value.code == KOMPONENTE_FEHLER and "Hub" in str(e.value)


def test_entfernen_komponente_bleibt_stehen(b):
    b.asm.wirkungslos = True
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_entfernen")(b, {"id": "p1", "komponente": "Schraube-3", "verknuepfungen": []})
    assert e.value.code == KOMPONENTE_FEHLER and e.value.schritt == "nachmessen"


def test_entfernen_einer_unterbaugruppe_nimmt_die_kinder(b):
    assert punkt_handler("komponente_entfernen")(b, {"id": "p1", "komponente": "Unter-1", "verknuepfungen": []}) == [
        "Unter-1", "Unter-1/Welle-1"]


def test_loesche_komponente_nimmt_nur_die_gewaehlte(b):
    loesche_komponente(b.asm, b.asm.komp("Schraube-3"))
    assert "Schraube-3" not in [k.Name2 for k in b.asm.komponenten] and b.asm.auswahl is None


def test_loesche_komponente_auswahl_scheitert(b):
    komp = b.asm.komp("Schraube-3")
    komp.Select4 = lambda anhaengen, daten, popup: False
    with pytest.raises(BauFehler) as e:
        loesche_komponente(b.asm, komp)
    assert e.value.code == KOMPONENTE_FEHLER


# --- komponente_ersetzen -------------------------------------------------------------------------------------------------

def test_ersetzen_ruft_mit_reattach_und_misst_nach(b):
    pfad = neue_datei(b, "Neu.sldprt")
    namen = punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE})
    assert b.asm.ersetzungen == [{"datei": str(pfad), "konfiguration": "", "alle": False, "wahl": 0, "neu_zuordnen": True}]
    assert namen == ["Neu-1"]
    assert komponenten(b)["Neu-1"]["datei"] == "Neu.sldprt"
    assert mates(b)["Hub"]["partner"] == ["Neu-1", "Grund-1"]


def test_ersetzen_bleibt_wirkungslos(b):
    neue_datei(b, "Neu.sldprt")
    b.asm.wirkungslos = True
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE})
    assert e.value.code == KOMPONENTE_FEHLER and e.value.schritt == "nachmessen"
    assert b.ersetzt == {}


def test_ersetzen_mit_konfiguration_waehlt_von_hand(b):
    neue_datei(b, "Neu.sldprt")
    punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE,
                                             "konfiguration": "Lang"})
    assert b.asm.ersetzungen[0]["konfiguration"] == "Lang" and b.asm.ersetzungen[0]["wahl"] == 1
    assert komponenten(b)["Neu-1"]["konfigurationen"] == {"Standard": "Lang", "Leicht": "Lang"}


def test_ersetzen_konfiguration_nicht_uebernommen(b, monkeypatch):
    neue_datei(b, "Neu.sldprt")
    roh = b.asm.ReplaceComponents2
    monkeypatch.setattr(b.asm, "ReplaceComponents2", lambda d, k, a, w, r: roh(d, "", a, w, r))
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE,
                                                 "konfiguration": "Lang"})
    assert "Lang" in str(e.value)


def test_ersetzen_nennt_verlorene_verknuepfungen(b):
    neue_datei(b, "Neu.sldprt")
    b.asm.verliert = {"Hub"}
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE})
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Hub" in str(e.value)


def test_ersetzen_nennt_neue_verknuepfungsfehler(b):
    neue_datei(b, "Neu.sldprt")
    b.asm.bricht = {"Hub": 47}
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE})
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Hub" in str(e.value) and "47" in str(e.value)


def test_ersetzen_alter_fehler_stoert_nicht(b):
    neue_datei(b, "Neu.sldprt")
    next(m for m in b.asm.mates if m.Name == "Hub").code = 47
    assert punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE}) == ["Neu-1"]


def test_ersetzen_fuehrt_alt_zu_neu(b):
    neue_datei(b, "Neu.sldprt")
    punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE})
    assert b.ersetzt == {"Schlitten-1": "Neu-1"} and b.neue == {"p1": ["Neu-1"]}


def test_ersetzen_fuehrt_alt_zu_neu_bei_alle_instanzen(b):
    neue_datei(b, "Neu.sldprt")
    namen = punkt_handler("komponente_ersetzen")(b, ALLE_SCHRAUBEN)
    assert len(b.asm.ersetzungen) == 11 and not any(e["alle"] for e in b.asm.ersetzungen)
    assert set(b.ersetzt) == {f"Schraube-{n}" for n in range(1, 12)}
    assert sorted(b.ersetzt.values()) == sorted(f"Neu-{n}" for n in range(1, 12))
    assert sorted(namen) == sorted(b.ersetzt.values()) and b.neue["p1"] == namen


def test_ersetzen_alle_instanzen_ohne_lesbare_datei_bricht_ab(b):
    b.aufnahme["komponenten"]["Schraube-1"]["datei"] = None
    neue_datei(b, "Neu.sldprt")
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, ALLE_SCHRAUBEN)
    assert e.value.code == KOMPONENTE_FEHLER and not b.asm.ersetzungen


def test_ersetzen_alle_instanzen_in_einer_unterbaugruppe_bricht_ab(b):
    """`ReplaceComponents2` kennt nur die oberste Ebene (API-Hilfe), `vergleiche_baugruppe` zählt jede Ebene als Instanz."""
    b.asm.komponente("Unter-1/Schraube-1", "teile/Schraube.SLDPRT")
    b.aufnahme["komponenten"] = komponenten(b)
    neue_datei(b, "Neu.sldprt")
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, ALLE_SCHRAUBEN)
    assert e.value.code == KOMPONENTE_FEHLER and "Unter-1/Schraube-1" in str(e.value)
    assert not b.asm.ersetzungen


def test_ersetzen_trifft_nebenbei_eine_andere_komponente(b, monkeypatch):
    neue_datei(b, "Neu.sldprt")
    roh = b.asm.ReplaceComponents2

    def auch_andere(d, k, a, w, r):
        roh(d, k, a, w, r)
        b.asm.entferne(b.asm.komp("Schraube-5"))

    monkeypatch.setattr(b.asm, "ReplaceComponents2", auch_andere)
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE})
    assert "Schraube-5" in str(e.value)


# --- verknuepfung_neu ----------------------------------------------------------------------------------------------------

@pytest.fixture
def anker(monkeypatch):
    """`loese_im_teil` ohne Geometrie: liefert eine Fläche im Teil und merkt sich Kontext und Anker."""
    aufrufe = []

    def loese(ctx, seite):
        aufrufe.append((ctx, seite))
        return TeilReferenz(SimpleNamespace(name=f"Fläche {seite}"), Messgeometrie("ebene", (0, 0, 0), (0, 0, 1)), False)

    monkeypatch.setattr(punkte_baugruppe, "loese_im_teil", loese)
    return aufrufe


def test_verknuepfung_neu_loest_punkt_id_und_sw_name(b, anker):
    neue_datei(b)
    punkt_handler("komponente_neu")(b, {"id": "s1", "quelle": QUELLE})
    b.asm.komp("Grund-1").feature_namen = {"Bohrung3"}
    p = {"id": "v1", "art": "konzentrisch", "a": {"komponente": "s1", "nahe": [0, 0, 1]},
         "b": {"komponente": "Grund-1", "feature": "Bohrung3", "flaeche": "+z"}}
    assert punkt_handler("verknuepfung_neu")(b, p) == ["v1"]
    e = mates(b)["v1"]
    assert e["typ"] == 1 and e["partner"] == ["ISO4762_M5x20-1", "Grund-1"]
    assert anker[0][1] == {"nahe": [0, 0, 1]} and anker[1][1] == {"feature": "Bohrung3", "flaeche": "+z"}
    assert anker[0][0] is b.kontexte["iso4762_m5x20.sldprt"]
    assert "Bohrung3" in anker[1][0].ergebnisse  # fremde Namen wie punkte.kontext


def test_kontext_einer_datei_gilt_fuer_alle_instanzen(b, anker):
    p = {"id": "v1", "art": "parallel", "a": {"komponente": "Schraube-1", "nahe": [0, 0, 0]},
         "b": {"komponente": "Schraube-2", "nahe": [0, 0, 0]}}
    punkt_handler("verknuepfung_neu")(b, p)
    assert anker[0][0] is anker[1][0] and "schraube.sldprt" in b.kontexte
    assert anker[0][0].spec["features"] == [] and anker[0][0].gleichungen is False


def test_referenz_im_fremden_teil_geht_ueber_die_komponente(b, monkeypatch):
    """`{komponente, referenz}`: Bezugsgeometrie wird über `IComponent2.FeatureByName` gewählt, nicht über
    `GetCorrespondingEntity`."""
    b.asm.komp("Grund-1").feature_namen = {"Achse1"}

    def loese(ctx, seite):
        return TeilReferenz(ctx.ergebnisse[seite["referenz"]].features[0], Messgeometrie("achse", (0, 0, 0), (0, 0, 1)), True)

    monkeypatch.setattr(punkte_baugruppe, "loese_im_teil", loese)
    p = {"id": "v1", "art": "parallel", "a": {"komponente": "Grund-1", "referenz": "Achse1"},
         "b": {"komponente": "Grund-1", "referenz": "Achse1"}}
    punkt_handler("verknuepfung_neu")(b, p)
    assert [s.Reference.name for s in next(m for m in b.asm.mates if m.Name == "v1").daten.seiten] == ["Achse1", "Achse1"]


def test_anker_in_unterbaugruppe_trifft_die_komponente_darin(b, anker):
    p = {"id": "v1", "art": "parallel", "a": {"komponente": "Unter-1/Welle-1", "nahe": [0, 0, 0]},
         "b": {"komponente": "Grund-1", "nahe": [0, 0, 0]}}
    punkt_handler("verknuepfung_neu")(b, p)
    assert mates(b)["v1"]["partner"] == ["Unter-1/Welle-1", "Grund-1"]


def test_anker_an_einer_unterbaugruppe_selbst_bricht_ab(b, anker):
    p = verbinde("Unter-1", "Grund-1")
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == BESTAND_REFERENZ and "Unter-1" in str(e.value)


def test_anker_an_nicht_geladener_komponente_bricht_ab(b, anker):
    b.asm.komp("Grund-1").unterdrueckt.add("Standard")
    p = verbinde()
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == BESTAND_REFERENZ and "Grund-1" in str(e.value)


def test_unbekanntes_feature_im_anker_bricht_ab(b, anker):
    p = {"id": "v1", "art": "parallel", "a": {"komponente": "Grund-1", "feature": "Fehlt", "flaeche": "+z"},
         "b": {"komponente": "Schraube-1", "nahe": [0, 0, 0]}}
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == BESTAND_REFERENZ and "Grund-1" in str(e.value) and "Fehlt" in str(e.value)


def test_anker_fehler_nennt_die_komponente(b, monkeypatch):
    def loese(ctx, seite):
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, "keine Fläche")

    monkeypatch.setattr(punkte_baugruppe, "loese_im_teil", loese)
    p = verbinde()
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == REFERENZ_NICHT_GEFUNDEN and "Grund-1" in str(e.value)


def test_verknuepfung_neu_nach_ersetzen_folgt_dem_neuen_namen(b, anker):
    neue_datei(b, "Neu.sldprt")
    punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE})
    p = verbinde("Schlitten-1", "Grund-1")
    punkt_handler("verknuepfung_neu")(b, p)
    assert mates(b)["v1"]["partner"] == ["Neu-1", "Grund-1"]


def test_verknuepfung_neu_in_allen_konfigurationen_aktiv(b, anker):
    """S19e T9.18: aktiv in allen Konfigurationen, das Aufheben je Konfiguration schadet nicht."""
    p = verbinde()
    punkt_handler("verknuepfung_neu")(b, p)
    assert mates(b)["v1"]["unterdrueckt"] == {"Standard": False, "Leicht": False}


def test_verknuepfung_neu_bleibt_unterdrueckt_ist_ein_fehler(b, anker):
    b.asm.wirkungslos = True
    b.asm.neu_nur_in_der_aktiven = True
    p = verbinde()
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Leicht" in str(e.value) and e.value.schritt == "nachmessen"


def test_verknuepfung_neu_abstand_mit_parameter(b, anker):
    p = {"id": "v1", "art": "abstand", "wert": "=H", "a": {"komponente": "Grund-1", "nahe": [0, 0, 0]},
         "b": {"komponente": "Schraube-1", "nahe": [0, 0, 0]}}
    punkt_handler("verknuepfung_neu")(b, p)
    assert mates(b)["v1"]["wert"] == 12.5 and b.asm.gleichungen.zeilen == []  # Zahl, keine Gleichung


def test_verknuepfung_neu_wert_kommt_nicht_an(b, anker, monkeypatch):
    p = {"id": "v1", "art": "abstand", "wert": 20, "a": {"komponente": "Grund-1", "nahe": [0, 0, 0]},
         "b": {"komponente": "Schraube-1", "nahe": [0, 0, 0]}}
    roh = b.asm.AddMate5

    def falsch(typ, ausrichtung, flip, d, *rest):
        return roh(typ, ausrichtung, flip, 0.001, *rest)

    monkeypatch.setattr(b.asm, "AddMate5", falsch)
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == VERKNUEPFUNG_FEHLER and "wert" in str(e.value)


def test_verknuepfung_neu_grenze(b, anker):
    p = {"id": "v1", "art": "grenze_abstand", "min": 0, "max": "=H", "a": {"komponente": "Grund-1", "nahe": [0, 0, 0]},
         "b": {"komponente": "Schraube-1", "nahe": [0, 0, 0]}}
    punkt_handler("verknuepfung_neu")(b, p)
    e = mates(b)["v1"]
    assert (e["min"], e["max"], e["grenze"]) == (0.0, 12.5, True)


def test_scharnier_sind_zwei_verknuepfungen(b, anker):
    p = verbinde(art="scharnier", anlage_a={"komponente": "Grund-1", "nahe": [0, 0, 1]},
                 anlage_b={"komponente": "Schraube-1", "nahe": [0, 0, 1]})
    assert punkt_handler("verknuepfung_neu")(b, p) == ["v1", "v1.anlage"]
    m = mates(b)
    assert m["v1"]["typ"] == 1 and m["v1.anlage"]["typ"] == 0 and m["v1.anlage"]["ausrichtung"] == 1


def test_scharnier_ohne_anlage_bricht_ab(b, anker):
    p = verbinde(art="scharnier")
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == VERKNUEPFUNG_FEHLER and "anlage" in str(e.value)


@pytest.mark.parametrize("art", ["zahnrad", "zahnstange"])
def test_kopplung_in_fremder_baugruppe_gibt_es_nicht(b, anker, art):
    p = verbinde(art=art)
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == VERKNUEPFUNG_FEHLER and "skript" in str(e.value)


def test_name_einer_vorhandenen_verknuepfung_misst_nie_die_alte(b, anker, monkeypatch):
    """Gleicher Typ, gleiche Partner, gleicher Wert wie `Abstand1`: Gemessen würde die alte, und die neue trägt den falschen
    Wert."""
    roh = b.asm.AddMate5

    def falsch(typ, ausrichtung, flip, d, *rest):
        return roh(typ, ausrichtung, flip, 0.001, *rest)

    monkeypatch.setattr(b.asm, "AddMate5", falsch)
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, verbinde("Schraube-1", "Grund-1", id="Abstand1", art="abstand", wert=3))
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Abstand1" in str(e.value) and e.value.schritt == "nachmessen"


def test_name_einer_vorhandenen_verknuepfung_ohne_gross_und_klein(b, anker):
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, verbinde("Schraube-1", "Grund-1", id="abstand1", art="abstand", wert=3))
    assert e.value.code == VERKNUEPFUNG_FEHLER and e.value.schritt == "nachmessen"


def test_ausrichtung_wird_nachgemessen(b, anker, monkeypatch):
    roh = b.asm.AddMate5

    def umgekehrt(typ, ausrichtung, *rest):
        return roh(typ, 1 - ausrichtung, *rest)

    monkeypatch.setattr(b.asm, "AddMate5", umgekehrt)
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, verbinde(ausrichtung="gleich"))
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Ausrichtung" in str(e.value)


def test_ausrichtung_steht_wie_genannt(b, anker):
    punkt_handler("verknuepfung_neu")(b, verbinde(ausrichtung="entgegengesetzt"))
    assert mates(b)["v1"]["ausrichtung"] == 1


def test_ohne_genannte_ausrichtung_wird_sie_nicht_verlangt(b, anker, monkeypatch):
    roh = b.asm.AddMate5

    def umgekehrt(typ, ausrichtung, *rest):
        return roh(typ, 1, *rest)

    monkeypatch.setattr(b.asm, "AddMate5", umgekehrt)
    assert punkt_handler("verknuepfung_neu")(b, verbinde()) == ["v1"]


def test_doppelter_name_scheitert_still_und_faellt_beim_nachmessen_auf(b, anker):
    p = verbinde(id="Hub")
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == VERKNUEPFUNG_FEHLER


def test_ein_fehler_erst_nach_dem_anlegen_bricht_ab(b, anker, monkeypatch):
    """`verknuepfe` sieht nur die aktive Konfiguration, das Nachmessen alle."""
    original = sw_baugruppe.verknuepfe

    def verknuepfe(*argumente, **benannt):
        f = original(*argumente, **benannt)
        f.code = 47
        return f

    monkeypatch.setattr(punkte_baugruppe.sw_baugruppe, "verknuepfe", verknuepfe)
    p = verbinde()
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_neu")(b, p)
    assert e.value.code == VERKNUEPFUNG_FEHLER and "47" in str(e.value)


@pytest.mark.parametrize("seite", ["a", "b"])
def test_drehung_mit_normteil_gesperrt(b, anker, seite):
    neue_datei(b)
    punkt_handler("komponente_neu")(b, {"id": "s1", "quelle": QUELLE})
    p = verbinde(art="konzentrisch")
    p[seite] = {"komponente": "s1", "nahe": [0, 0, 0]}
    punkt_handler("verknuepfung_neu")(b, p)
    assert next(m for m in b.asm.mates if m.Name == "v1").drehung_gesperrt is True


def test_drehung_fremder_teile_bleibt_frei_ohne_angabe(b, anker):
    p = verbinde(art="konzentrisch")
    punkt_handler("verknuepfung_neu")(b, p)
    assert next(m for m in b.asm.mates if m.Name == "v1").drehung_gesperrt is False


def test_drehung_sperren_ausdruecklich(b, anker):
    neue_datei(b)
    punkt_handler("komponente_neu")(b, {"id": "s1", "quelle": QUELLE})
    p = {"id": "v1", "art": "konzentrisch", "drehung_sperren": False, "a": {"komponente": "s1", "nahe": [0, 0, 0]},
         "b": {"komponente": "Schraube-1", "nahe": [0, 0, 0]}}
    punkt_handler("verknuepfung_neu")(b, p)
    assert next(m for m in b.asm.mates if m.Name == "v1").drehung_gesperrt is False


# --- verknuepfung_wert ---------------------------------------------------------------------------------------------------

def mate(b, name="Abstand1"):
    return next(m for m in b.asm.mates if m.Name == name)


def test_verknuepfung_wert_prueft_alt_live(b):
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Abstand1", "alt": 9, "neu": 5})
    assert e.value.code == BESTAND_ALTWERT and "Standard" in str(e.value) and e.value.schritt == "alt"
    assert mate(b).wert_d1.aufrufe == []


def test_verknuepfung_wert_alt_gilt_je_konfiguration(b):
    mate(b).je_konfiguration = {"Standard": 0.003, "Leicht": 0.004}
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Abstand1", "alt": 3, "neu": 5})
    assert e.value.code == BESTAND_ALTWERT and "Leicht" in str(e.value)


def test_verknuepfung_wert_alle_konfigurationen(b):
    assert punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Abstand1", "alt": 3, "neu": "=H"}) == ["Abstand1"]
    assert mates(b)["Abstand1"]["werte"]["Leicht"]["wert"] == 12.5
    assert mate(b).wert_d1.aufrufe == [(pytest.approx(0.0125), 2, None)]


def test_verknuepfung_wert_nur_in_den_genannten(b):
    p = {"id": "p1", "verknuepfung": "Abstand1", "alt": 3, "neu": 5, "konfigurationen": ["Leicht"]}
    punkt_handler("verknuepfung_wert")(b, p)
    w = mates(b)["Abstand1"]["werte"]
    assert w["Leicht"]["wert"] == 5 and w["Standard"]["wert"] == 3
    assert mate(b).wert_d1.aufrufe == [(pytest.approx(0.005), 3, ["Leicht"])]


def test_verknuepfung_wert_alt_nur_in_den_genannten(b):
    mate(b).je_konfiguration = {"Standard": 0.003, "Leicht": 0.004}
    p = {"id": "p1", "verknuepfung": "Abstand1", "alt": 4, "neu": 5, "konfigurationen": ["Leicht"]}
    punkt_handler("verknuepfung_wert")(b, p)
    assert mates(b)["Abstand1"]["werte"]["Standard"]["wert"] == 3


def test_verknuepfung_wert_winkel_in_radiant(b):
    b.asm.mate("Winkel1", 6, [b.asm.seite("Grund-1"), b.asm.seite("Schraube-1")], wert=0.5235987755982988, typname="MateAngleDim")
    punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Winkel1", "alt": 30, "neu": 45})
    assert mates(b)["Winkel1"]["wert"] == pytest.approx(45)


def test_verknuepfung_wert_status_ist_nicht_null(b):
    mate(b).wert_d1.status = 1
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Abstand1", "alt": 3, "neu": 5})
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Status 1" in str(e.value)


def test_verknuepfung_wert_springt_zurueck(b):
    mate(b).gesteuert = True
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Abstand1", "alt": 3, "neu": 5})
    assert e.value.code == VERKNUEPFUNG_FEHLER and e.value.schritt == "nachmessen"


def test_verknuepfung_wert_unbekannt(b):
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Fehlt", "alt": 3, "neu": 5})
    assert e.value.code == BESTAND_REFERENZ


def test_verknuepfung_wert_neuer_fehler_bricht_ab(b, monkeypatch):
    roh = mate(b).schreibe_d1

    def mit_fehler(wert, konfigurationen):
        roh(wert, konfigurationen)
        mate(b).code = 47

    monkeypatch.setattr(mate(b), "schreibe_d1", mit_fehler)
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Abstand1", "alt": 3, "neu": 5})
    assert "47" in str(e.value)


def test_grenze_aendern_misst_nach(b):
    """Hub: steht auf 10, Grenzen 0 bis 25. `ModifyDefinition` meldet Erfolg, ohne etwas zu tun: Nur das Nachmessen sieht es."""
    b.asm.wirkungslos = True
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30})
    assert e.value.code == VERKNUEPFUNG_FEHLER and e.value.schritt == "nachmessen" and "max" in str(e.value)


def test_grenze_aendern_ueber_die_definition(b):
    """Einmal, in der aktiven Konfiguration: `ModifyDefinition` wirkt in allen (S19e T9.27); je Konfiguration gesetzt war die
    Verknüpfung danach in Standard unterdrückt (S19e3)."""
    punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30})
    w = mates(b)["Hub"]["werte"]
    assert w["Standard"] == {"wert": 10, "min": 0, "max": 30} and w["Leicht"] == {"wert": 10, "min": 0, "max": 30}
    aktiv, oben, komponente = mate(b, "Hub").modifiziert[0]
    assert [x[0] for x in mate(b, "Hub").modifiziert] == ["Standard"]
    assert oben is b.asm and komponente is not None and komponente.value is None  # Nothing wie im Beispiel der API-Hilfe
    assert b.asm.aktiv == "Standard"


def test_grenze_danach_unterdrueckt_ist_ein_fehler(b):
    """S19e3: `ModifyDefinition` außerhalb der ersten Konfiguration unterdrückte Hub in Standard, still."""
    b.asm.unterdrueckt_nach_definition = {"Leicht"}
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30})
    assert e.value.code == VERKNUEPFUNG_FEHLER and e.value.schritt == "nachmessen" and "unterdrückt in Leicht" in str(e.value)


def test_unterdrueckt_wie_im_bestand_ist_kein_fehler(b):
    """Was der Kollege unterdrückt hat, bleibt so: Nur eine neu unterdrückte Verknüpfung ist ein Fehler."""
    mate(b, "Hub").unterdrueckt.add("Leicht")
    punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30})
    assert mates(b)["Hub"]["unterdrueckt"] == {"Standard": False, "Leicht": True}


def test_grenze_die_den_wert_ausschliesst_bricht_mit_grund_ab(b):
    """S19e T9.26: min 15 bei Hub auf 10 übernimmt SolidWorks nicht, die Rückgabe sagt trotzdem Erfolg."""
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Hub", "grenze": "min", "alt": 0, "neu": 15})
    assert e.value.schritt == "nachmessen" and "schlösse den aktuellen Wert" in str(e.value) and "Standard: 10" in str(e.value)


def test_grenze_min_und_winkel(b):
    b.asm.mate("Schwenk", 6, [b.asm.seite("Grund-1"), b.asm.seite("Schraube-1")], wert=0.0, spanne=(0.0, 1.5707963267948966),
               typname="MateAngleDim")
    punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Schwenk", "grenze": "min", "alt": 0, "neu": -30})
    assert mates(b)["Schwenk"]["werte"]["Leicht"]["min"] == pytest.approx(-30)
    assert mates(b)["Schwenk"]["werte"]["Leicht"]["max"] == pytest.approx(90)


def test_grenze_alt_live_je_konfiguration(b):
    mate(b, "Hub").daten.spannen = {"Leicht": (-0.010, 0.020)}
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30})
    assert e.value.code == BESTAND_ALTWERT and "Leicht" in str(e.value)
    assert mate(b, "Hub").modifiziert == []


def test_grenze_nur_in_den_genannten_gibt_es_nicht(b):
    """`ModifyDefinition` wirkt in allen Konfigurationen (S19e T9.27): `validieren` weist das ab, der Handler als zweite Linie."""
    p = {"id": "p1", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30, "konfigurationen": ["Leicht"]}
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, p)
    assert e.value.code == VERKNUEPFUNG_FEHLER and "alle Konfigurationen" in str(e.value) and mate(b, "Hub").modifiziert == []


def test_grenze_wirkt_auch_in_den_uebrigen_ist_ein_fehler(b):
    """Wirkte `ModifyDefinition` doch nur in der aktiven, stünde die andere Konfiguration still alt: Das Nachmessen sieht es."""
    b.asm.definition_ueberall = False
    p = {"id": "p1", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30}
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, p)
    assert e.value.code == VERKNUEPFUNG_FEHLER and "max steht in Leicht auf 25" in str(e.value)


# --- verknuepfung_loeschen -----------------------------------------------------------------------------------------------

def test_verknuepfung_loeschen_misst_nach(b):
    assert punkt_handler("verknuepfung_loeschen")(b, {"id": "p1", "verknuepfung": "Abstand1"}) == ["Abstand1"]
    assert "Abstand1" not in mates(b) and "Hub" in mates(b)


def test_verknuepfung_loeschen_bleibt_stehen(b):
    b.asm.wirkungslos = True
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_loeschen")(b, {"id": "p1", "verknuepfung": "Abstand1"})
    assert e.value.code == VERKNUEPFUNG_FEHLER


def test_verknuepfung_loeschen_unbekannt(b):
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_loeschen")(b, {"id": "p1", "verknuepfung": "Fehlt"})
    assert e.value.code == BESTAND_REFERENZ


def test_verknuepfung_loeschen_nimmt_eine_andere_mit(b, monkeypatch):
    roh = b.asm.EditDelete

    def auch_hub():
        roh()
        b.asm.mates.remove(mate(b, "Hub"))

    monkeypatch.setattr(b.asm, "EditDelete", auch_hub)
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_loeschen")(b, {"id": "p1", "verknuepfung": "Abstand1"})
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Hub" in str(e.value)


# --- Zusammenspiel mit dem Vergleich ---------------------------------------------------------------------------------------

def stand(b) -> dict:
    return {"konfigurationen": b.aufnahme["konfigurationen"], "aktiv": b.aufnahme["aktiv"], "komponenten": komponenten(b),
            "verknuepfungen": mates(b), "kollisionen": []}


def test_das_protokoll_passt_zum_vergleich(b, anker):
    neue_datei(b)
    neue_datei(b, "Neu.sldprt", art="teil", schluessel="teil:neu.yaml:")
    punkte = [{"id": "s1", "typ": "komponente_neu", "quelle": QUELLE},
              {"id": "e1", "typ": "komponente_ersetzen", "komponente": "Schraube-2", "quelle": {"teil": "neu.yaml"}},
              {"id": "v1", "typ": "verknuepfung_neu", "art": "abstand", "wert": 4, "a": {"komponente": "s1", "nahe": [0, 0, 0]},
               "b": {"komponente": "Grund-1", "nahe": [0, 0, 0]}},
              {"id": "w1", "typ": "verknuepfung_wert", "verknuepfung": "Abstand1", "alt": 3, "neu": 5},
              {"id": "l1", "typ": "verknuepfung_loeschen", "verknuepfung": "Deckungsgleich1"}]
    vorher = stand(b)
    for p in punkte:
        punkt_handler(p["typ"])(b, p)
    e = {x["id"]: x for x in vergleiche_baugruppe({"punkte": punkte, "parameter": {}}, vorher, stand(b), b.neue, b.ersetzt,
                                                  ["ISO4762_M5x20.sldprt", "Neu.sldprt"])}
    fehl = {n: x for n, x in e.items() if x["ok"] is not True}
    assert not fehl, fehl
    assert b.neue == {"s1": ["ISO4762_M5x20-1"], "e1": ["Neu-1"]} and b.ersetzt == {"Schraube-2": "Neu-1"}


def test_lage_der_uebrigen_bleibt_beim_einfuegen(b):
    punkt_handler("komponente_neu")(b, {"id": "p1", "wie": "Schraube-1"})
    assert komponenten(b)["Schlitten-1"]["transform"]["Standard"] == lage(0.010)
    assert komponenten(b)["Schraube-12"]["transform"]["Standard"] == lage()


# --- Nicht lesbar ist nie Erfolg --------------------------------------------------------------------------------------------

def verknuepfungen_lesen_als(monkeypatch, aendere):
    """Alle Lesungen laufen durch `aendere`, auch die vor dem Schreiben: nicht lesbar auf beiden Seiten ist nicht gleich."""
    roh = lies_verknuepfungen

    def lies(*argumente):
        m = roh(*argumente)
        aendere(m)
        return m

    monkeypatch.setattr(punkte_baugruppe, "lies_verknuepfungen", lies)


def test_ersetzen_partner_auf_beiden_seiten_nicht_lesbar(b, monkeypatch):
    neue_datei(b, "Neu.sldprt")
    verknuepfungen_lesen_als(monkeypatch, lambda m: m["Hub"].update(partner=None))
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE})
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Hub" in str(e.value)


def test_ersetzen_fehlercode_nicht_lesbar(b, monkeypatch):
    neue_datei(b, "Neu.sldprt")
    verknuepfungen_lesen_als(monkeypatch, lambda m: m["Hub"]["fehler"].pop("Leicht"))
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE})
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Hub" in str(e.value) and "Leicht" in str(e.value)


def test_ersetzen_konfiguration_nicht_lesbar(b, monkeypatch):
    neue_datei(b, "Neu.sldprt")
    roh = lies_komponenten

    def lies(*argumente):
        k = roh(*argumente)
        if "Neu-1" in k:
            del k["Neu-1"]["konfigurationen"]["Leicht"]
        return k

    monkeypatch.setattr(punkte_baugruppe, "lies_komponenten", lies)
    with pytest.raises(BauFehler) as e:
        punkt_handler("komponente_ersetzen")(b, {"id": "p1", "komponente": "Schlitten-1", "quelle": QUELLE,
                                                 "konfiguration": "Lang"})
    assert e.value.code == KOMPONENTE_FEHLER and "Leicht" in str(e.value)


def test_wert_in_den_uebrigen_nicht_lesbar(b, monkeypatch):
    verknuepfungen_lesen_als(monkeypatch, lambda m: m["Abstand1"]["werte"].pop("Standard"))
    p = {"id": "p1", "verknuepfung": "Abstand1", "alt": 3, "neu": 5, "konfigurationen": ["Leicht"]}
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, p)
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Standard" in str(e.value) and "nicht lesbar" in str(e.value)


def test_wert_fehlercode_nicht_lesbar(b, monkeypatch):
    verknuepfungen_lesen_als(monkeypatch, lambda m: m["Abstand1"]["fehler"].pop("Leicht"))
    with pytest.raises(BauFehler) as e:
        punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Abstand1", "alt": 3, "neu": 5})
    assert e.value.code == VERKNUEPFUNG_FEHLER and "Leicht" in str(e.value)


def test_wert_ohne_grenzen_bleibt_ohne_grenzen(b):
    """`None` in einem gelesenen Eintrag heißt: trägt keinen Wert. Das ist gleich und nicht „nicht lesbar“."""
    assert punkt_handler("verknuepfung_wert")(b, {"id": "p1", "verknuepfung": "Abstand1", "alt": 3, "neu": 5}) == ["Abstand1"]


# --- Handler und Vergleich zusammen -----------------------------------------------------------------------------------------

def lauf(b: BauKontext, punkte: list[dict], dateien: list[str]) -> dict:
    b.spec["punkte"] = punkte
    vorher = stand(b)
    for p in punkte:
        punkt_handler(p["typ"])(b, p)
    e = vergleiche_baugruppe({"punkte": punkte, "parameter": {}}, vorher, stand(b), b.neue, b.ersetzt, dateien)
    return {x["id"]: (x["ok"], x.get("hinweis")) for x in e if x["ok"] is not True}


def test_alle_sechs_zusammen(b, anker):
    neue_datei(b)
    neue_datei(b, "Neu.sldprt", art="teil", schluessel="teil:neu.yaml:")
    punkte = [{"id": "s1", "typ": "komponente_neu", "quelle": QUELLE},
              {"id": "s2", "typ": "komponente_neu", "wie": "Schraube-4", "fixiert": True},
              {"id": "e1", "typ": "komponente_ersetzen", "komponente": "Schraube-2", "quelle": {"teil": "neu.yaml"}},
              {"id": "w0", "typ": "komponente_entfernen", "komponente": "Schraube-3", "verknuepfungen": []},
              {"typ": "verknuepfung_neu", **verbinde("s1", "Grund-1", art="abstand", wert=4)},
              {"id": "w1", "typ": "verknuepfung_wert", "verknuepfung": "Abstand1", "alt": 3, "neu": 5},
              {"id": "l1", "typ": "verknuepfung_loeschen", "verknuepfung": "Deckungsgleich1"}]
    assert lauf(b, punkte, ["ISO4762_M5x20.sldprt", "Neu.sldprt"]) == {}


ENTFERNEN = {"id": "w0", "typ": "komponente_entfernen", "komponente": "Schraube-3", "verknuepfungen": []}
ALLE = {"typ": "komponente_ersetzen", **ALLE_SCHRAUBEN, "id": "e1"}


@pytest.mark.parametrize("punkte", [[ENTFERNEN, ALLE], [ALLE, ENTFERNEN]], ids=["erst_entfernen", "erst_ersetzen"])
def test_eine_schraube_weg_die_uebrigen_tauschen(b, punkte):
    neue_datei(b, "Neu.sldprt")
    assert lauf(b, punkte, ["Neu.sldprt"]) == {}
    assert "Schraube-3" not in b.ersetzt and len(b.ersetzt) == 10
    assert "Schraube-3" not in komponenten(b)
    assert sum(k["datei"] == "Neu.sldprt" for k in komponenten(b).values()) == 10


def test_ersetzen_trifft_die_zum_entfernen_genannte_nicht(b):
    b.spec["punkte"] = [ALLE, ENTFERNEN]
    neue_datei(b, "Neu.sldprt")
    punkt_handler("komponente_ersetzen")(b, ALLE)
    assert "Schraube-3" in komponenten(b)


def test_ersetzen_einer_entfernten_unterbaugruppe_zaehlt_ihre_kinder_nicht(b):
    b.asm.komponente("Unter-1/Schraube-1", "teile/Schraube.SLDPRT")
    b.aufnahme["komponenten"] = komponenten(b)
    neue_datei(b, "Neu.sldprt")
    entfernen = {"id": "w0", "typ": "komponente_entfernen", "komponente": "Unter-1", "verknuepfungen": []}
    assert lauf(b, [entfernen, ALLE], ["Neu.sldprt"]) == {}


# --- Die gemeinsame Instanzmenge --------------------------------------------------------------------------------------------

KOMPONENTEN = {"A-1": {"datei": "A.SLDPRT"}, "A-2": {"datei": "a.sldprt"}, "B-1": {"datei": "B.SLDPRT"},
               "Sub-1": {"datei": "Sub.SLDASM"}, "Sub-1/A-3": {"datei": "A.SLDPRT"}}


def test_ziele_ohne_alle_instanzen_nur_die_genannte():
    assert ersetzen_ziele({"komponente": "A-1"}, KOMPONENTEN, []) == (["A-1"], [])


def test_ziele_alle_instanzen_jede_ebene():
    assert ersetzen_ziele({"komponente": "A-1", "alle_instanzen": True}, KOMPONENTEN, []) == (["A-1", "A-2", "Sub-1/A-3"], [])


def test_ziele_ohne_die_entfernten_samt_kindern():
    punkte = [{"typ": "komponente_entfernen", "komponente": "A-2"}, {"typ": "komponente_entfernen", "komponente": "Sub-1"}]
    assert ersetzen_ziele({"komponente": "A-1", "alle_instanzen": True}, KOMPONENTEN, punkte) == (["A-1"], [])


def test_ziele_nicht_lesbare_datei_ist_unbewiesen():
    k = {**KOMPONENTEN, "A-2": {"datei": None}}
    ziele, unlesbar = ersetzen_ziele({"komponente": "A-1", "alle_instanzen": True}, k, [])
    assert ziele == ["A-1", "Sub-1/A-3"] and "A-2" in unlesbar[0]
