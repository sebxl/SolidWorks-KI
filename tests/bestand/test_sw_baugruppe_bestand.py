"""Baugruppe lesen und fahren an der Attrappe (Spec Bestandsdateien §8.1, §8.3, §8.4; Plan Etappe 2 Task 8). Ungemessen: gegen den
API-Index, S19 kann die Attrappe korrigieren."""

import copy
import os
from types import SimpleNamespace

import pytest

from swki.baugruppe import sw_baugruppe
from swki.baugruppe.bewegung import Bewegung
from swki.baugruppe.bewegungslauf import StellungFehler
from swki.baugruppe.sw_bewegung import SwMechanik
from swki.bestand import sw_bestand
from swki.bestand.bewegung_bestand import abdeckung, fahre_bestand, grenzen_der_aufnahme, statische_paare
from swki.bestand.fehler import BESTAND_NICHT_LESBAR, BestandFehler
from swki.bestand.sw_baugruppe_bestand import (baum_ohne_glieder, lies_baugruppe, lies_kollisionen, lies_komponenten,
                                               lies_verknuepfungen, mechanik_fuer)
from swki.bestand.vergleich_baugruppe import vergleiche_baugruppe
from swki.compiler.fehler import BauFehler
from tests.bestand.sw_attrappe_baugruppe import Interferenz, Kollisionen, lage, muster_baugruppe

SPEC = {"art": "aenderung", "punkte": [], "bereiche": []}
APP = SimpleNamespace(GetProcessID=os.getpid())


@pytest.fixture
def asm(tmp_path):
    return muster_baugruppe(tmp_path / "bestand-1", ("Standard", "Leicht"))


# --- Komponenten ------------------------------------------------------------------------------------------------------

def test_komponenten_alle_ebenen_im_format(asm):
    k = lies_komponenten(asm, ["Standard"])
    assert "Unter-1/Welle-1" in k and len(k) == 15
    s = k["Schraube-3"]
    assert s["datei"] == "teile/Schraube.SLDPRT" and s["konfiguration"] == "Standard"
    assert s["konfigurationen"] == {"Standard": "Standard"}
    assert s["virtuell"] is False and s["muster"] is False and s["loesen"] == -1
    assert s["fixiert"] == {"Standard": False} and s["unterdrueckt"] == {"Standard": False} and s["status"] == {"Standard": 3}
    assert s["transform"] == {"Standard": lage()}
    assert k["Grund-1"]["fixiert"] == {"Standard": True} and k["Unter-1"]["loesen"] == 0


def test_komponenten_je_konfiguration_und_aktive_bleibt(asm):
    asm.aktiv = "Leicht"
    asm.komp("Grund-1").referenz = "Klein"
    asm.komp("Schlitten-1").lagen["Standard"] = lage(0.020)
    k = lies_komponenten(asm, ["Leicht", "Standard"])
    assert asm.aktiv == "Leicht" and k["Grund-1"]["konfiguration"] == "Klein"
    assert k["Schlitten-1"]["transform"] == {"Leicht": lage(0.010), "Standard": lage(0.020)}


def test_unterdrueckte_komponente_traegt_jedes_feld(asm):
    """Spec-Format: `transform` null, alle Felder je Konfiguration da, sonst würde eine unveränderte Baugruppe `ok: None`."""
    asm.komp("Schraube-2").unterdrueckt.add("Leicht")
    s = lies_komponenten(asm, ["Standard", "Leicht"])["Schraube-2"]
    assert s["unterdrueckt"] == {"Standard": False, "Leicht": True} and s["transform"] == {"Standard": lage(), "Leicht": None}
    assert s["konfigurationen"] == {"Standard": "Standard",
                                    "Leicht": "Standard"} and set(s["fixiert"]) == set(s["status"]) == {"Standard", "Leicht"}


def test_kind_einer_unterdrueckten_unterbaugruppe_traegt_jedes_feld(asm):
    """`GetComponents` nennt das Kind dort nicht: Es zählt als unterdrückt, nicht als fehlend."""
    asm.komp("Unter-1").unterdrueckt.add("Leicht")
    asm.komp("Unter-1/Welle-1").nicht_genannt.add("Leicht")
    w = lies_komponenten(asm, ["Standard", "Leicht"])["Unter-1/Welle-1"]
    assert w["unterdrueckt"]["Leicht"] is True and w["transform"]["Leicht"] is None
    assert w["konfigurationen"]["Leicht"] == "Standard" and w["fixiert"]["Leicht"] is False and "Leicht" in w["status"]


def test_nur_in_einer_nicht_aktiven_konfiguration_genannt(asm):
    asm.komp("Schraube-1").nicht_genannt.add("Standard")
    s = lies_komponenten(asm, ["Standard", "Leicht"])["Schraube-1"]
    assert s["unterdrueckt"] == {"Standard": True, "Leicht": False} and s["konfiguration"] == "Standard"


def test_unterdrueckte_ohne_jeden_lesbaren_wert_traegt_trotzdem_eintraege(asm):
    def gesperrt(self):
        raise RuntimeError("unterdrückt")

    k = asm.komponente("Weg-1", "teile/Weg.SLDPRT")
    k.unterdrueckt.update(("Standard", "Leicht"))
    k.__class__ = type("Gesperrt", (k.__class__,), {"ReferencedConfiguration": property(gesperrt), "IsFixed": property(gesperrt),
                                                     "GetConstrainedStatus": property(gesperrt)})
    w = lies_komponenten(asm, ["Standard", "Leicht"])["Weg-1"]
    assert w["konfigurationen"] == {"Standard": "", "Leicht": ""} and w["fixiert"] == {"Standard": False, "Leicht": False}
    assert w["status"] == {"Standard": 0, "Leicht": 0}


def test_nicht_lesbar_bei_aktiver_komponente_bleibt_unlesbar(asm):
    """Nur eine unterdrückte bekommt Ersatzwerte: Bei einer aktiven heißt fehlend nicht gelesen, das macht der Vergleich zu `ok:
    None`."""
    def gesperrt(self):
        raise RuntimeError("COM weg")

    k = asm.komp("Schraube-1")
    k.__class__ = type("Gesperrt", (k.__class__,), {"GetConstrainedStatus": property(gesperrt)})
    assert "Standard" not in lies_komponenten(asm, ["Standard"])["Schraube-1"]["status"]


def test_lightweight_komponente_laesst_sich_lesen(asm):
    """Review Focus 4: `GetModelDoc2` ist None, gelesen wird nur an der Komponente."""
    asm.komp("Schraube-1").modell = None
    assert lies_komponenten(asm, ["Standard"])["Schraube-1"]["status"] == {"Standard": 3}


def test_virtuelle_komponente_traegt_den_namen_ohne_pfad_in_der_kopie(asm):
    asm.komponente("Teil1^Haupt-1", "Teil1^Haupt.sldprt", virtuell=True)
    k = lies_komponenten(asm, ["Standard"])["Teil1^Haupt-1"]
    assert k["virtuell"] is True and k["datei"] == "Teil1^Haupt.sldprt"


def test_pfad_ausserhalb_der_kopie_wird_ueber_den_namen_zugeordnet(asm):
    """API-Hilfe `GetPathName`: Bei einer unterdrückten Komponente steht der gespeicherte Pfad da, nicht der aufgelöste."""
    k = asm.komp("Schraube-1")
    k.__class__ = type("Gespeichert", (k.__class__,), {"GetPathName": "D:\\Kunde\\teile\\Schraube.SLDPRT"})
    aus = lies_komponenten(asm, ["Standard"], ["teile/Schraube.SLDPRT"])
    assert aus["Schraube-1"]["datei"] == "teile/Schraube.SLDPRT"


def test_lies_baut_vor_den_lagen_neu_auf(asm):
    """Geändertes Teil, ungespeicherte Baugruppe: `Transform2` zeigt bis zum Neuaufbau die alte Lage."""
    k = asm.komp("Schlitten-1")
    k.veraltet = {"Standard": lage(0.001), "Leicht": lage(0.001)}
    aus = lies_komponenten(asm, ["Standard", "Leicht"])
    assert aus["Schlitten-1"]["transform"] == {"Standard": lage(0.010), "Leicht": lage(0.010)}
    assert asm.neuaufbauten[:2] == ["Standard", "Leicht"]


# --- Verknüpfungen ----------------------------------------------------------------------------------------------------

def test_grenze_gelesen_relativ_zu_d1(asm):
    """S13b D: Min/MaximumVariation sind relativ zum Wert `D1`, Werte in m."""
    v = lies_verknuepfungen(asm, ["Standard"])["Hub"]
    assert v["grenze"] is True and v["typ"] == 5 and v["ausrichtung"] == 0
    assert (v["wert"], v["min"], v["max"]) == pytest.approx((10.0, 0.0, 25.0))
    assert v["werte"]["Standard"] == pytest.approx({"wert": 10.0, "min": 0.0, "max": 25.0})
    assert v["partner"] == ["Schlitten-1",
                            "Grund-1"] and v["fehler"] == {"Standard": 0} and v["unterdrueckt"] == {"Standard": False}


def test_abstand_ohne_grenze(asm):
    v = lies_verknuepfungen(asm, ["Standard"])["Abstand1"]
    assert v["grenze"] is False and v["wert"] == pytest.approx(3.0) and v["min"] is None and v["max"] is None


def test_verknuepfung_ohne_zahl_traegt_null(asm):
    v = lies_verknuepfungen(asm, ["Standard"])["Deckungsgleich1"]
    assert v["wert"] is None and v["werte"] == {"Standard": {"wert": None, "min": None, "max": None}} and v["typ"] == 0


def test_partner_an_ebene_der_hauptbaugruppe_ist_null(asm):
    assert lies_verknuepfungen(asm, ["Standard"])["Deckungsgleich1"]["partner"] == ["Grund-1", None]


def test_winkel_in_grad(asm):
    m = asm.mate("Winkel1", 6, [asm.seite("Grund-1"), asm.seite("Schlitten-1")], wert=0.5235987755982988,
                 typname="MatePlanarAngleDim")
    assert m.daten.Type == 6
    assert lies_verknuepfungen(asm, ["Standard"])["Winkel1"]["wert"] == pytest.approx(30.0)


def test_werte_je_konfiguration(asm):
    asm.mates[1].je_konfiguration = {"Standard": 0.003, "Leicht": 0.007}
    v = lies_verknuepfungen(asm, ["Standard", "Leicht"])["Abstand1"]
    assert v["werte"]["Leicht"]["wert"] == pytest.approx(7.0) and v["wert"] == pytest.approx(3.0)


def test_fehler_und_unterdrueckung_je_konfiguration(asm):
    asm.mates[1].unterdrueckt.add("Leicht")
    asm.mates[2].code = 48
    v = lies_verknuepfungen(asm, ["Standard", "Leicht"])
    assert v["Abstand1"]["unterdrueckt"] == {"Standard": False, "Leicht": True}
    assert v["Deckungsgleich1"]["fehler"] == {"Standard": 48, "Leicht": 48}


def test_gesteuert_durch_gleichung(asm):
    asm.gleichungen.zeilen.append({"text": '"D1@Abstand1" = 3', "global": False, "wert": 3.0})
    v = lies_verknuepfungen(asm, ["Standard"])
    assert v["Abstand1"]["gesteuert"] is True and v["Hub"]["gesteuert"] is False


def test_unlesbare_partner_bleiben_none(asm):
    """Die Grenze gehört trotzdem dazu: `fahre_bestand` vermerkt sie als nicht gefahren."""
    def kaputt(i):
        raise RuntimeError("COM weg")

    asm.mates[0].daten.MateEntity = kaputt
    assert lies_verknuepfungen(asm, ["Standard"])["Hub"]["partner"] is None


def test_ordner_unter_den_verknuepfungen_zaehlt_nicht(asm):
    """Ein Ordner im Verknüpfungsbaum hat kein IMate2 (S19f klärt, wo seine Verknüpfungen stehen)."""
    ordner = asm.mate("Ordner1", 0, typname="FtrFolder")
    ordner.daten = None
    assert "Ordner1" not in lies_verknuepfungen(asm, ["Standard"])


# --- Baum und ganzes Lesen --------------------------------------------------------------------------------------------

def test_baum_ohne_glieder(asm):
    assert [f.Name for f in baum_ohne_glieder(asm)] == ["Ebene vorne"]


def test_lies_baugruppe_format(asm):
    d = lies_baugruppe(None, asm)
    assert d["version"] == 2 and d["art"] == "baugruppe" and d["konfigurationen"] == ["Standard",
                                                                                      "Leicht"] and d["aktiv"] == "Standard"
    assert d["einheitensystem"] == 5 and d["tabelle"] is False
    assert d["material"] == "" and d["materialien"] == {} and d["geometrie"] == {}
    assert [f["name"] for f in d["features"]] == ["Ebene vorne"] and d["reihenfolge"]["Leicht"] == ["Ebene vorne"]
    assert set(d["eigenschaften"]) == {"datei", "konfiguration"} and d["neuaufbau"] == [] and d["kollisionen"] == []
    assert "datei" not in d and "dateien" not in d and "bewegungen" not in d
    assert len(d["komponenten"]) == 15 and set(d["verknuepfungen"]) == {"Hub", "Abstand1", "Deckungsgleich1"}


def test_lies_baugruppe_aktive_bleibt_auch_nach_fehler(asm):
    asm.aktiv = "Leicht"
    asm.mates[0].Parameter = None  # bricht beim Lesen nicht ab: Der Wert bleibt `None`, die Fahrt vermerkt das
    lies_baugruppe(None, asm)
    assert asm.aktiv == "Leicht"
    asm.ForceRebuild3 = lambda nur_oben: (_ for _ in ()).throw(RuntimeError("COM weg"))
    with pytest.raises(RuntimeError):
        lies_baugruppe(None, asm)
    assert asm.aktiv == "Leicht"


def test_konfiguration_nicht_schaltbar(asm):
    asm.ShowConfiguration2 = lambda k: True
    with pytest.raises(BestandFehler) as e:
        lies_baugruppe(None, asm)
    assert e.value.daten["code"] == BESTAND_NICHT_LESBAR


def test_zweimal_gelesen_ist_ein_unveraenderter_stand(asm):
    """Das Format trägt den Vergleich der Baugruppe: Gleicher Stand heißt in jeder Prüfung `ok: True`, auch mit Unterdrücktem."""
    asm.komp("Schraube-2").unterdrueckt.add("Leicht")
    asm.komp("Unter-1").unterdrueckt.add("Leicht")
    asm.komp("Unter-1/Welle-1").nicht_genannt.add("Leicht")
    vorher = lies_baugruppe(None, asm)
    nachher = copy.deepcopy(lies_baugruppe(None, asm))
    assert {e["id"]: e["ok"] for e in vergleiche_baugruppe(SPEC, vorher, nachher, {}, {})} == {
        "komponenten": True, "verknuepfungen": True, "bestimmtheit": True, "kollision": True, "lage": True}


# --- Kollision: `[]` nur nach erfolgreichem Lesen ----------------------------------------------------------------------

def test_keine_kollision_nach_gelesenem_zaehler(asm):
    assert lies_kollisionen(asm) == [] and asm.kollisionen.fertig == 1 and asm.kollisionen.TreatCoincidenceAsInterference is False


def test_kollision_gelesen(asm):
    asm.kollisionen = Kollisionen(1, (Interferenz(["Schraube-1", "Grund-1"], 1.5),))
    assert lies_kollisionen(asm) == [{"paar": ["Grund-1", "Schraube-1"], "volumen": 1.5}]


@pytest.mark.parametrize("liste", [None, ()])
def test_zaehler_sagt_mehr_als_die_liste_ist_nicht_gelesen(asm, liste):
    """`sw_baugruppe.interferenzen` macht aus `None` still `[]`; hier trennt der Zähler „keine“ von „nicht gelesen“."""
    asm.kollisionen = Kollisionen(2, liste)
    assert lies_kollisionen(asm) is None and asm.kollisionen.fertig == 1


def test_fehler_beim_lesen_ist_nicht_gelesen(asm):
    def kaputt(self):
        raise RuntimeError("COM weg")

    k = asm.kollisionen
    k.__class__ = type("Kaputt", (Kollisionen,), {"GetInterferenceCount": property(kaputt)})
    assert lies_kollisionen(asm) is None and k.fertig == 1


# --- Mechanik -----------------------------------------------------------------------------------------------------------

@pytest.fixture
def stand(asm):
    a = lies_baugruppe(None, asm)
    return a, grenzen_der_aufnahme(a)


def _fahre(mech, a, g):
    return fahre_bestand(mech, a, g, 5, statische_paare(a), 1e9, 0.01, 0.0)


def test_mechanik_nur_oberste_nicht_unterdrueckte(asm):
    asm.komp("Schraube-2").unterdrueckt.add("Standard")
    a = lies_baugruppe(None, asm)
    mech = mechanik_fuer(None, asm, grenzen_der_aufnahme(a), a, None)
    assert "Unter-1" in mech.komponenten and "Unter-1/Welle-1" not in mech.komponenten and "Schraube-2" not in mech.komponenten


def test_mechanik_liest_entitaeten_vor_dem_unterdruecken(asm, stand):
    """`fahre` unterdrückt die Grenze, danach gibt sie ihre Entitäten nicht mehr her."""
    a, g = stand
    mech = mechanik_fuer(None, asm, g, a, None)
    asm.mates[0].unterdrueckt.add("Standard")  # wie `fahre`
    v = mech.grenzen["Hub"]
    assert mech.entitaet(v.a)[0].name == "Fläche von Schlitten-1" and mech.entitaet(v.b)[0].name == "Fläche von Grund-1"
    assert mech.entitaet(v.a)[1] is False


def test_bezugsebene_wird_als_feature_gewaehlt(asm):
    asm.mate("Hub2", 5, [asm.seite("Schlitten-1"), sw_seite_ebene(asm)], wert=0.0, spanne=(0.0, 0.01))
    a = lies_baugruppe(None, asm)
    mech = mechanik_fuer(None, asm, grenzen_der_aufnahme(a), a, None)
    assert mech.entitaet(mech.grenzen["Hub2"].b)[1] is True


def sw_seite_ebene(asm):
    from tests.bestand.sw_attrappe_baugruppe import Bezug, Seite

    return Seite(None, Bezug("Ebene"), 4)


def test_unlesbare_entitaeten_lassen_nur_diese_grenze_herausfallen(asm, stand):
    a, g = stand
    teile = asm.mates[0].daten

    def kaputt(i):
        raise RuntimeError("COM weg")

    alt, teile.MateEntity = teile.MateEntity, kaputt
    mech = mechanik_fuer(None, asm, g, a, None)
    teile.MateEntity = alt
    with pytest.raises(StellungFehler) as e:
        mech.entitaet(mech.grenzen["Hub"].a)
    assert e.value.bewegung == "Hub" and "COM weg" in str(e.value)


def test_fahrt_an_der_attrappe(asm, stand):
    a, g = stand
    e = _fahre(mechanik_fuer(APP, asm, g, a, None), a, g)["Hub"]
    assert e["gefahren"] is True and e["komponente"] == "Schlitten-1" and e["stellungen"] == 6 and e["bewegt"] == ["Schlitten-1"]
    assert all(p["ok"] is not False for p in e["pruefungen"] if not p["id"].startswith("freiheitsgrad")), e["pruefungen"]
    assert asm.gespeichert == [] and [m.Name for m in asm.mates] == ["Hub", "Abstand1", "Deckungsgleich1"]  # Antrieb wieder weg


def test_alter_verknuepfungsfehler_stoppt_die_fahrt_nicht(asm):
    """Review Focus 5: Was die Aufnahme als Fehler kennt, stoppt die Fahrt nicht."""
    asm.mates[2].code = 48
    asm.fehler["Standard"] = [("Deckungsgleich1", 48)]
    a = lies_baugruppe(None, asm)
    g = grenzen_der_aufnahme(a)
    mech = mechanik_fuer(APP, asm, g, a, None)
    assert mech.bekannte_fehler == {"Deckungsgleich1"}
    assert _fahre(mech, a, g)["Hub"]["gefahren"] is True


def test_ohne_bekannte_fehler_stoppt_der_alte_fehler(asm):
    asm.mates[2].code = 48
    b = Bewegung("Hub", "Hub", "abstand", "Schlitten-1", 0.0, 25.0, 5)
    a = lies_baugruppe(None, asm)
    mech = mechanik_fuer(None, asm, grenzen_der_aufnahme(a), a, None)
    mech.bekannte_fehler = frozenset()
    mech.unterdruecke(b, True)
    with pytest.raises(StellungFehler):
        mech.halte(b, 0.0)


def test_neuer_verknuepfungsfehler_stoppt_die_fahrt(asm):
    asm.mates[2].code = 48
    a = lies_baugruppe(None, asm)
    g = grenzen_der_aufnahme(a)
    mech = mechanik_fuer(APP, asm, g, a, None)
    asm.mates[1].code = 7                       # erst in der Fahrt
    e = _fahre(mech, a, g)["Hub"]
    assert e["gefahren"] is False
    assert "Abstand1" in e["hinweis"] and "Deckungsgleich1" not in e["hinweis"].split("Verknüpfungsfehler: ")[1]


def test_stelle_alte_fehler_zaehlen_nicht(monkeypatch):
    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", lambda m: None)
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda f: 5)
    from types import SimpleNamespace as NS

    antrieb = NS(Parameter=lambda n: NS(SetSystemValue3=lambda *a: 0))
    mates = [NS(Name="alt"), NS(Name="neu")]
    assert sw_baugruppe.stelle(None, antrieb, "abstand", 1.0, mates, bekannt=frozenset({"alt", "neu"})) is None
    assert sw_baugruppe.stelle(None, antrieb, "abstand", 1.0, mates, bekannt=frozenset({"alt"})) == "Verknüpfungsfehler: neu"
    assert sw_baugruppe.stelle(None, antrieb, "abstand", 1.0, mates) == "Verknüpfungsfehler: alt, neu"


def test_unterbaugruppe_als_bewegte_komponente(asm):
    """`_teilebox` fragt `GetPartBox` nur bei Teilen, eine Unterbaugruppe hat keins und läuft über `GetBox`."""
    asm.mates[0].daten.seiten[0] = asm.seite("Unter-1")
    asm.bewegt["Hub"] = "Unter-1"
    a = lies_baugruppe(None, asm)
    g = grenzen_der_aufnahme(a)
    e = _fahre(mechanik_fuer(APP, asm, g, a, None), a, g)["Hub"]
    assert e["gefahren"] is True and e["bewegt"] == ["Unter-1"]


def test_teilebox_eines_teils_wie_bisher(asm):
    mech = SwMechanik(None, asm, {}, None, {"Grund-1": asm.komp("Grund-1")})
    assert mech._teilebox("Grund-1", asm.komp("Grund-1")) == pytest.approx([0, 0, 0, 10, 10, 10])
    u = asm.komp("Unter-1")
    assert mech._teilebox("Unter-1", u) is None


def test_kollision_in_der_fahrt_nicht_gelesen_bricht_ab(asm, stand):
    """Nie „keine Kollision“ aus einer Liste, die SolidWorks nicht geliefert hat."""
    a, g = stand
    asm.kollisionen = Kollisionen(1, None)
    with pytest.raises(BauFehler):
        _fahre(mechanik_fuer(APP, asm, g, a, None), a, g)
    assert [m.Name for m in asm.mates] == ["Hub", "Abstand1", "Deckungsgleich1"]


def test_abdeckung_der_aufnahme(asm):
    a = lies_baugruppe(None, asm)
    assert abdeckung(a) == ["Komponente Schlitten-1 ist beweglich (unterbestimmt) und hat keine Grenze, nicht gefahren"]


def test_sw_bestand_helfer_sind_oeffentlich():
    for name in ("schalte", "gleichungen_von", "eigenschaften_von", "feature_eintrag", "lies_masse", "datei_referenzen",
                 "gleichungsdatei"):
        assert callable(getattr(sw_bestand, name))
