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
from swki.bestand.sw_baugruppe_bestand import (VERKNUEPFUNG_UNERREICHT, baum_ohne_glieder, lies_baugruppe, lies_kollisionen,
                                               lies_komponenten, lies_verknuepfungen, mechanik_fuer)
from swki.bestand.vergleich_baugruppe import vergleiche_baugruppe
from swki.compiler.fehler import BauFehler
from tests.bestand.sw_attrappe_baugruppe import Bezug, Interferenz, Knoten, Kollisionen, Mate, Seite, lage, muster_baugruppe

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
    """S19a T8.4: `ReferenceComponent` ist die Wurzelkomponente (`Name2` wie der Titel der Baugruppe), nicht `None`. Was
    `GetComponents` nicht nennt, ist keine Komponente."""
    assert asm.mates[2].daten.MateEntity(1).ReferenceComponent.Name2 == "Haupt"
    assert lies_verknuepfungen(asm, ["Standard"])["Deckungsgleich1"]["partner"] == ["Grund-1", None]


def test_partner_einer_in_der_aktiven_unterdrueckten_komponente(asm):
    """S19a T8.5: Ist die Unterbaugruppe in der aktiven Konfiguration unterdrückt, meldet `ReferenceComponent` für ihr Kind die
    Wurzel; die Verknüpfung selbst ist nicht unterdrückt. Den Partner nennt die Konfiguration, in der das Kind geladen ist."""
    asm.mate("Wellenlage", 0, [asm.seite("Unter-1/Welle-1"), asm.seite("Grund-1")])
    asm.komp("Unter-1").unterdrueckt.add("Standard")
    asm.komp("Unter-1/Welle-1").nicht_genannt.add("Standard")
    v = lies_verknuepfungen(asm, ["Standard", "Leicht"])["Wellenlage"]
    assert v["partner"] == ["Unter-1/Welle-1", "Grund-1"] and v["unterdrueckt"] == {"Standard": False, "Leicht": False}


def test_partner_ueberall_unterdrueckt_bleibt_null(asm):
    """Keine Konfiguration lädt das Kind: Bestand und Lauf lesen dasselbe `None`, der Vergleich sieht keinen Unterschied."""
    asm.mate("Wellenlage", 0, [asm.seite("Unter-1/Welle-1"), asm.seite("Grund-1")])
    asm.komp("Unter-1/Welle-1").nicht_genannt.update({"Standard", "Leicht"})
    assert lies_verknuepfungen(asm, ["Standard", "Leicht"])["Wellenlage"]["partner"] == [None, "Grund-1"]


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


def _im_ordner(asm, *mates):
    """Die Verknüpfungen stecken in einem Ordner unter `MateGroup`; der Ordner selbst hat kein IMate2."""
    for m in mates:
        asm.mates.remove(m)
    ordner = Knoten(asm, "Ordner1", "FtrFolder", unter=mates)
    asm.mates.append(ordner)
    return ordner


def test_verknuepfung_im_ordner_wird_gelesen(asm):
    _im_ordner(asm, asm.mates[1])
    v = lies_verknuepfungen(asm, ["Standard"])
    assert "Abstand1" in v and "Ordner1" not in v and v["Abstand1"]["wert"] == pytest.approx(3.0)


def test_grenze_im_ordner_wird_gefahren(asm):
    """Sonst fehlte sie ohne Hinweis: Bestand und Lauf läsen gleich, der Vergleich sähe es nie."""
    _im_ordner(asm, asm.mates[0])
    a = lies_baugruppe(None, asm)
    g = grenzen_der_aufnahme(a)
    assert list(g) == ["Hub"] and _fahre(mechanik_fuer(APP, asm, g, a, None), a, g)["Hub"]["gefahren"] is True


def test_gegenprobe_schweigt_wenn_der_baum_alles_kennt(asm):
    _im_ordner(asm, asm.mates[1])
    assert lies_baugruppe(None, asm)["warnungen"] == []


def test_gegenprobe_nennt_was_der_baum_nicht_erreicht(asm):
    """`GetFeatures(False)` kennt sie, der Baumweg nicht: Das steht in `warnungen`, auch vor S19f nie still."""
    asm.versteckt.append(Mate(asm, "Versteckt1", 0))
    w = lies_baugruppe(None, asm)["warnungen"]
    assert [x["code"] for x in w] == [VERKNUEPFUNG_UNERREICHT] and w[0]["verknuepfungen"] == ["Versteckt1"]
    assert "Versteckt1" in w[0]["meldung"]


def test_gegenprobe_nicht_lesbar_ist_nie_still(asm):
    asm.__class__ = type("Ohne", (asm.__class__,), {"FeatureManager": property(lambda self: 1 / 0)})
    w = lies_baugruppe(None, asm)["warnungen"]
    assert [x["code"] for x in w] == [VERKNUEPFUNG_UNERREICHT] and "ZeroDivisionError" in w[0]["meldung"]


# --- Baum und ganzes Lesen --------------------------------------------------------------------------------------------

def test_baum_ohne_glieder(asm):
    assert [f.Name for f in baum_ohne_glieder(asm)] == ["Ebene vorne"]


@pytest.mark.parametrize("typ", ["LocalLPattern", "LocalCirPattern", "LocalChainPattern", "LocalCurvePattern",
                                 "LocalSketchPattern"])
def test_komponentenmuster_ist_ein_glied(asm, typ):
    """S19f T11.5, P.f1: Ein Komponentenmuster steht als `LocalLPattern` im Baum, seine Instanz als Unterfeature; die Instanzen
    stehen in `komponenten`. Sonst sähen `reihenfolge` und `_pruefe_baum` eine neue Musterinstanz als Feature."""
    asm.komponente("Schraube-12", "teile/Schraube.SLDPRT", muster=True)
    asm.glieder = [g for g in asm.glieder if g.Name != "Schraube-12"]
    asm.glieder.append(Knoten(asm, "Lokales lineares Muster1", typ, [Knoten(asm, "Schraube-12", "ReferencePattern")]))
    assert [f.Name for f in baum_ohne_glieder(asm)] == ["Ebene vorne"]
    assert lies_baugruppe(None, asm)["reihenfolge"] == {"Standard": ["Ebene vorne"], "Leicht": ["Ebene vorne"]}


def test_lies_baugruppe_ohne_bildschirmarbeit(asm):
    """S19d T11.11: In `sw.schnell` liest `lies_baugruppe` 5- bis 15-mal schneller (2,55 s → 0,34 s unsichtbar). Danach ist alles
    zurückgestellt."""
    app = SimpleNamespace(CommandInProgress=False, GetProcessID=os.getpid())
    gesehen, rebuild = [], asm.ForceRebuild3
    asm.ForceRebuild3 = lambda nur_oben: (gesehen.append(app.CommandInProgress), rebuild(nur_oben))[1]
    lies_baugruppe(app, asm)
    assert gesehen == [True, True] and app.CommandInProgress is False


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


class Stumm(Mate):
    """Pflichtfrage 5: Unterdrückt gibt die Verknüpfung gar nichts her, auch `GetSpecificFeature2` nicht."""

    @property
    def GetSpecificFeature2(self):
        return None if self.asm.aktiv in self.unterdrueckt else self.daten


@pytest.mark.parametrize("stumm", [False, True])
@pytest.mark.parametrize("aus", [{"Leicht"}, {"Standard"}, {"Standard", "Leicht"}])
def test_unterdrueckte_verknuepfung_ist_ein_unveraenderter_stand(asm, aus, stumm):
    """Unterdrückt in einer oder in allen Konfigurationen: Eine unveränderte Baugruppe ist bewiesen, nicht `ok: None`."""
    m = asm.mates[1]
    m.unterdrueckt.update(aus)
    if stumm:
        m.__class__ = Stumm
    vorher = lies_baugruppe(None, asm)
    nachher = copy.deepcopy(lies_baugruppe(None, asm))
    assert vorher["verknuepfungen"]["Abstand1"]["werte"].keys() == {"Standard", "Leicht"}
    assert {e["id"]: e["ok"] for e in vergleiche_baugruppe(SPEC, vorher, nachher, {}, {})} == {
        "komponenten": True, "verknuepfungen": True, "bestimmtheit": True, "kollision": True, "lage": True}


def test_ueberall_unterdrueckte_verknuepfung_ohne_gelesene_daten(asm):
    """Nichts gelesen: Ersatz, der in Bestand und Lauf gleich ist. Eine Zahl behauptet er nicht, `swMateUNKNOWN` steht als Typ."""
    m = asm.mates[1]
    m.unterdrueckt.update({"Standard", "Leicht"})
    m.__class__ = Stumm
    v = lies_baugruppe(None, asm)["verknuepfungen"]["Abstand1"]
    assert v["typ"] == 7 and v["partner"] == [] and v["grenze"] is False and v["wert"] is None
    assert v["werte"] == {"Standard": {"wert": None, "min": None, "max": None}, "Leicht": {"wert": None, "min": None,
                                                                                           "max": None}}


def test_wieder_aktivierte_verknuepfung_faellt_auf(asm):
    """Der Ersatz gilt nur, solange sie in beiden Ständen unterdrückt ist."""
    m = asm.mates[1]
    m.unterdrueckt.update({"Standard", "Leicht"})
    m.__class__ = Stumm
    vorher = lies_baugruppe(None, asm)
    m.unterdrueckt.clear()
    aus = {e["id"]: e["ok"] for e in vergleiche_baugruppe(SPEC, vorher, lies_baugruppe(None, asm), {}, {})}
    assert aus["verknuepfungen"] is False


def test_aktive_verknuepfung_ohne_lesbare_zahl_bleibt_unlesbar(asm):
    """Nur eine unterdrückte bekommt Ersatz: Bei einer aktiven heißt fehlend nicht gelesen."""
    asm.mates[1].Parameter = None
    assert "Standard" not in lies_verknuepfungen(asm, ["Standard"])["Abstand1"]["werte"]


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


def test_mechanik_liest_entitaeten_je_antrieb_frisch(asm, stand):
    """S19b T8.22, P.b4: `SwMechanik.status` ruft `ForceRebuild3`, danach ist jeder vorher gelesene Zeiger getrennt
    (`RPC_E_DISCONNECTED`), kein Antrieb ließe sich anlegen. Aus der unterdrückten Grenze lassen sie sich frisch lesen."""
    a, g = stand
    mech = mechanik_fuer(None, asm, g, a, None)
    asm.mates[0].unterdrueckt.add("Standard")  # wie `fahre`
    asm.ForceRebuild3(False)                    # wie `SwMechanik.status`
    v = mech.grenzen["Hub"]
    objekt, feature = mech.entitaet(v.a)
    assert objekt.Select4(False, None) is True and objekt.name == "Fläche von Schlitten-1" and feature is False
    assert mech.entitaet(v.b)[0].name == "Fläche von Grund-1"


def test_bezugsebene_wird_als_feature_gewaehlt(asm):
    asm.mate("Hub2", 5, [asm.seite("Schlitten-1"), sw_seite_ebene(asm)], wert=0.0, spanne=(0.0, 0.01))
    a = lies_baugruppe(None, asm)
    mech = mechanik_fuer(None, asm, grenzen_der_aufnahme(a), a, None)
    assert mech.entitaet(mech.grenzen["Hub2"].b)[1] is True


def sw_seite_ebene(asm):
    return Seite(None, Bezug("Ebene"), 4)


def test_unlesbare_entitaeten_lassen_nur_diese_grenze_herausfallen(asm, stand):
    a, g = stand
    teile = asm.mates[0].daten

    def kaputt(i):
        raise RuntimeError("COM weg")

    mech = mechanik_fuer(None, asm, g, a, None)
    teile.MateEntity = kaputt  # erst beim Anlegen des Antriebs gelesen
    with pytest.raises(StellungFehler) as e:
        mech.entitaet(mech.grenzen["Hub"].a)
    assert e.value.bewegung == "Hub" and "COM weg" in str(e.value)


def test_fahrt_an_der_attrappe(asm, stand):
    a, g = stand
    e = _fahre(mechanik_fuer(APP, asm, g, a, None), a, g)["Hub"]
    assert e["gefahren"] is True and e["komponente"] == "Schlitten-1" and e["stellungen"] == 6 and e["bewegt"] == ["Schlitten-1"]
    assert all(p["ok"] is not False for p in e["pruefungen"] if not p["id"].startswith("freiheitsgrad")), e["pruefungen"]
    assert asm.gespeichert == [] and [m.Name for m in asm.mates] == ["Hub", "Abstand1", "Deckungsgleich1"]  # Antrieb wieder weg


class Stumpf(Bezug):
    def Select4(self, anhaengen, daten):
        return False


def _zweite_grenze(asm, bezug):
    asm.komponente("Schlitten-2", "teile/Schlitten.SLDPRT", status=2)
    asm.mate("Hub2", 5, [Seite(asm.komp("Schlitten-2"), bezug), asm.seite("Grund-1")], wert=0.010, spanne=(-0.010, 0.015),
             typname="MateDistanceDim")
    asm.bewegt["Hub2"] = "Schlitten-2"
    a = lies_baugruppe(None, asm)
    return a, grenzen_der_aufnahme(a)


def test_ein_antrieb_scheitert_die_andere_grenze_faehrt(asm):
    """§8.4: `Select4` False wirft einen `BauFehler`. Nur diese Grenze fällt heraus, der Grund steht im Hinweis."""
    a, g = _zweite_grenze(asm, Stumpf("Fläche"))
    e = _fahre(mechanik_fuer(APP, asm, g, a, None), a, g)
    assert e["Hub2"]["gefahren"] is False and "Auswahl" in e["Hub2"]["hinweis"] and e["Hub"]["gefahren"] is True
    assert [m.Name for m in asm.mates] == ["Hub", "Abstand1", "Deckungsgleich1", "Hub2"] and not asm.mates[3].unterdrueckt


def test_com_fehler_beim_anlegen_gilt_nur_dieser_grenze(asm):
    class Kaputt(Bezug):
        def Select4(self, anhaengen, daten):
            raise RuntimeError("COM weg")

    a, g = _zweite_grenze(asm, Kaputt("Fläche"))
    e = _fahre(mechanik_fuer(APP, asm, g, a, None), a, g)
    assert e["Hub2"]["gefahren"] is False and "COM weg" in e["Hub2"]["hinweis"] and e["Hub"]["gefahren"] is True


def test_fehler_ohne_bezug_zu_einer_grenze_bleibt_laut(asm, stand):
    """Ruling Task 6, präzisiert: Nur das Anlegen des Antriebs fällt auf die Grenze zurück."""
    a, g = stand
    asm.mates[0].SetSuppression2 = lambda aktion, option, namen: False
    with pytest.raises(BauFehler):
        _fahre(mechanik_fuer(APP, asm, g, a, None), a, g)


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
    """Schlitten-1 ist unterbestimmt, aber Partner der Grenze Hub; Frei-1 hat keine, Gefahren-1 hat die Fahrt bewegt."""
    asm.komponente("Frei-1", "teile/Welle.SLDPRT", status=2)
    asm.komponente("Gefahren-1", "teile/Welle.SLDPRT", status=2)
    a = lies_baugruppe(None, asm)
    text = "Komponente {} ist beweglich (unterbestimmt) und hat keine Grenze, nicht gefahren"
    assert abdeckung(a) == [text.format("Frei-1"), text.format("Gefahren-1")]  # noch keine Fahrt, Schlitten-1 ist Partner
    a["bewegungen"] = {"Hub": {"bewegt": ["Gefahren-1"]}}
    assert abdeckung(a) == [text.format("Frei-1")]


def test_sw_bestand_helfer_sind_oeffentlich():
    for name in ("schalte", "gleichungen_von", "eigenschaften_von", "feature_eintrag", "lies_masse", "datei_referenzen",
                 "gleichungsdatei"):
        assert callable(getattr(sw_bestand, name))
