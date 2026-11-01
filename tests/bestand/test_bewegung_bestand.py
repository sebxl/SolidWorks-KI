"""Bewegungen gegen den Bestand (Spec Bestandsdateien §8.4, Plan Etappe 2 Task 6), ohne SolidWorks: die Mechanik-Attrappe der Stufe 4a
(`tests/baugruppe/attrappe_mechanik.py`: Schieber und Hebel auf einer Platte, Hub 0…100 und Schwenk 0…90)."""

import copy
import json

import pytest

from swki.baugruppe.bewegungslauf import StellungFehler
from swki.baugruppe.sw_baugruppe import NAECHSTE
from swki.bestand.bewegung_bestand import (SeiteUnklar, abdeckung, als_verknuepfung, bekannte_paare, bewegte_seite, fahre_bestand,
                                           grenze_als_bewegung, grenzen_der_aufnahme, ohne_fahrt, statische_paare,
                                           vergleiche_bewegungen)
from tests.baugruppe.attrappe_mechanik import Attrappe
from tests.bestand.beispiel_baugruppe import baugruppen_aufnahme, komponente, verknuepfung

SCHIEBER_BOLZEN = frozenset({"bolzen", "schieber"})  # die Attrappe meldet in jedem Lauf diese Überlappung
BEKANNT = {SCHIEBER_BOLZEN}


def aufnahme(**ueber) -> dict:
    """Platte (fixiert), Schieber und Hebel mit den Grenzen Hub (Abstand, Schieber an Platte) und Schwenk (Winkel, Hebel an Schieber)."""
    a = baugruppen_aufnahme(
        komponenten={"platte": komponente("teile/Platte.SLDPRT", fixiert=True), "schieber": komponente("teile/Schieber.SLDPRT"),
                     "hebel": komponente("teile/Welle.SLDPRT")},
        verknuepfungen={"Hub": verknuepfung(5, ["schieber", "platte"], wert=0.0, min_=0.0, max_=100.0, grenze=True),
                        "Schwenk": verknuepfung(6, ["hebel", "schieber"], wert=0.0, min_=0.0, max_=90.0, grenze=True)},
        kollisionen=[], bewegungen={})
    a.update(ueber)
    return a


def fahre_alle(mech=None, a=None, bekannt=None, schritte=4, **kw) -> dict:
    a = a or aufnahme()
    return fahre_bestand(mech or Attrappe(), a, grenzen_der_aufnahme(a), schritte, BEKANNT if bekannt is None else bekannt,
                         kw.pop("grenze_mb", 3500), 0.1, **kw)


class SchwenkKaputt(Attrappe):
    """Die treibende Verknüpfung des Schwenks lässt sich nicht anlegen (StellungFehler wie in `SwMechanik.halte`)."""

    def halte(self, b, wert):
        if b.name == "Schwenk":
            raise StellungFehler("Schwenk", wert, "Zwang")
        super().halte(b, wert)


# ----------------------------------------------------------------------------------------------------------- bewegte Seite

def test_fixierter_partner_bewegt_sich_nicht():
    a = aufnahme()
    mech = Attrappe()
    assert bewegte_seite(mech, "Hub", a["verknuepfungen"]["Hub"], a) == "schieber"
    v = {**a["verknuepfungen"]["Hub"], "partner": ["platte", "schieber"]}
    assert bewegte_seite(mech, "Hub", v, a) == "schieber"
    assert mech.aufrufe == []  # die Aufnahme verrät es, nichts wird gefahren


def test_ebene_der_hauptbaugruppe_ist_nie_die_bewegte_seite():
    a = aufnahme()
    mech = Attrappe()
    assert bewegte_seite(mech, "Hub", {**a["verknuepfungen"]["Hub"], "partner": [None, "schieber"]}, a) == "schieber"
    assert bewegte_seite(mech, "Hub", {**a["verknuepfungen"]["Hub"], "partner": ["schieber", None]}, a) == "schieber"
    with pytest.raises(SeiteUnklar):
        bewegte_seite(mech, "Hub", {**a["verknuepfungen"]["Hub"], "partner": [None, None]}, a)
    assert mech.aufrufe == []


def test_probeschritt_findet_die_bewegte_seite():
    a = aufnahme()  # Hebel und Schieber sind beide nicht fixiert: der Schwenk dreht nur den Hebel
    mech = Attrappe()
    assert bewegte_seite(mech, "Schwenk", a["verknuepfungen"]["Schwenk"], a) == "hebel"
    assert bewegte_seite(mech, "Schwenk", {**a["verknuepfungen"]["Schwenk"], "partner": ["schieber", "hebel"]}, a) == "hebel"
    # aufgeräumt: keine treibende Verknüpfung, Grenze wieder aktiv
    assert mech.gehalten == set() and mech.unterdrueckt == set() and mech.geloest == ["Schwenk", "Schwenk"]


def test_probeschritt_beide_bewegt_ist_seite_a():
    a = aufnahme()  # der Hub verschiebt Schieber und Hebel
    v = {**a["verknuepfungen"]["Hub"], "partner": ["schieber", "hebel"]}
    assert bewegte_seite(Attrappe(), "Hub", v, a) == "schieber"
    assert bewegte_seite(Attrappe(), "Hub", {**v, "partner": ["hebel", "schieber"]}, a) == "hebel"


def test_probeschritt_ohne_bewegung_ist_unklar_und_raeumt_auf():
    a = aufnahme()
    mech = Attrappe()
    v = {**a["verknuepfungen"]["Hub"], "partner": ["platte", "platte2"]}
    a["komponenten"]["platte"]["fixiert"]["Standard"] = False
    with pytest.raises(SeiteUnklar):
        bewegte_seite(mech, "Hub", v, a)  # platte2 steht nicht im Modell
    assert mech.gehalten == set() and mech.unterdrueckt == set()
    with pytest.raises(SeiteUnklar):  # beide im Modell, der Hub bewegt keine von beiden
        bewegte_seite(Attrappe(), "Hub", {**v, "partner": ["platte", "platte"]}, a)


def test_probeschritt_scheitert_mit_stellung_fehler():
    a = aufnahme()
    mech = Attrappe(fehler_bei=("Schwenk", 90.0))
    with pytest.raises(StellungFehler):
        bewegte_seite(mech, "Schwenk", a["verknuepfungen"]["Schwenk"], a)
    assert mech.gehalten == set() and mech.unterdrueckt == set()


# -------------------------------------------------------------------------------------------------- Grenze als Bewegung

def test_grenze_als_bewegung():
    a = aufnahme()
    b = grenze_als_bewegung("Hub", a["verknuepfungen"]["Hub"], "schieber", 7)
    assert (b.name, b.grenze, b.art, b.komponente, b.min, b.max, b.schritte, b.gekoppelt) == ("Hub", "Hub", "abstand", "schieber", 0.0,
                                                                                           100.0, 7, ())
    assert grenze_als_bewegung("Schwenk", a["verknuepfungen"]["Schwenk"], "hebel", 4).art == "winkel"
    with pytest.raises(ValueError):
        grenze_als_bewegung("X", {**a["verknuepfungen"]["Hub"], "typ": 0}, "schieber", 4)
    with pytest.raises(ValueError):
        grenze_als_bewegung("X", {**a["verknuepfungen"]["Hub"], "max": None}, "schieber", 4)


@pytest.mark.parametrize("zahl,text", [(0, "gleich"), (1, "entgegengesetzt"), (2, None)])
def test_ausrichtung_wird_uebernommen(zahl, text):
    assert NAECHSTE == 2  # die Zahl 2 der Aufnahme ist „nächste", im Compiler None
    v = {**aufnahme()["verknuepfungen"]["Hub"], "ausrichtung": zahl}
    verk = als_verknuepfung("Hub", v)
    assert verk.ausrichtung == text
    assert (verk.id, verk.vorlage, verk.typ, verk.drehung_sperren) == ("Hub", "Hub", "grenze_abstand", False)
    assert (verk.min, verk.max, verk.wert) == (0.0, 100.0, 0.0)
    assert verk.a == {"komponente": "schieber", "index": 0} and verk.b == {"komponente": "platte", "index": 1}


def test_verknuepfung_winkel_und_ebene_der_hauptbaugruppe():
    v = {**aufnahme()["verknuepfungen"]["Schwenk"], "partner": [None, "hebel"], "ausrichtung": None}
    verk = als_verknuepfung("Schwenk", v)
    assert verk.typ == "grenze_winkel" and verk.ausrichtung is None
    assert verk.a == {"komponente": None, "index": 0} and verk.b == {"komponente": "hebel", "index": 1}


def test_grenzen_der_aufnahme_nur_oberste_ebene_nicht_unterdrueckt():
    a = aufnahme()
    a["verknuepfungen"]["Unten"] = verknuepfung(5, ["Unter-1/Welle-1", "platte"], min_=0.0, max_=5.0, grenze=True)
    a["verknuepfungen"]["Aus"] = verknuepfung(5, ["schieber", "platte"], min_=0.0, max_=5.0, grenze=True)
    a["verknuepfungen"]["Aus"]["unterdrueckt"]["Standard"] = True
    a["verknuepfungen"]["Ebene"] = verknuepfung(5, ["schieber", None], min_=0.0, max_=5.0, grenze=True)
    a["verknuepfungen"]["Abstand"] = verknuepfung(5, ["schieber", "platte"], wert=3.0)
    a["verknuepfungen"]["Unlesbar"] = verknuepfung(5, ["schieber", "platte"], min_=0.0, max_=5.0, grenze=True)
    a["verknuepfungen"]["Unlesbar"]["partner"] = None
    assert list(grenzen_der_aufnahme(a)) == ["Hub", "Schwenk", "Ebene", "Unlesbar"]


# ----------------------------------------------------------------------------------------------------------------- Fahrt

def test_fahrt_an_der_aufnahme_haelt_ergebnis_fest():
    mech = Attrappe()
    erg = fahre_alle(mech, bekannt=set())
    assert list(erg) == ["Hub", "Schwenk"]
    hub, schwenk = erg["Hub"], erg["Schwenk"]
    assert (hub["komponente"], hub["art"], hub["min"], hub["max"], hub["gefahren"], hub["hinweis"]) == ("schieber", "abstand", 0.0, 100.0,
                                                                                                      True, None)
    assert hub["bewegt"] == ["schieber", "hebel"]
    assert hub["raum"] == pytest.approx([-100.0, 20.0, -30.0, 83.0, 48.0, 10.0])
    # die Überlappung der Attrappe steht in jedem Lauf der Bewegung: Grundstellung und Paarlauf
    assert hub["kollisionen"] == [{"paar": ["bolzen", "schieber"], "volumen": 1.0}] * 2
    assert {e["id"] for e in hub["pruefungen"]} == {"freiheitsgrad:schieber", "bewegung:Hub", "bewegung_kollision:Hub", "grenze:Hub",
                                                    "sollweg:Hub:schieber"}
    assert {e["id"]: e["ok"] for e in hub["pruefungen"]}["bewegung_kollision:Hub"] is False
    assert (schwenk["komponente"], schwenk["art"], schwenk["bewegt"], schwenk["gefahren"]) == ("hebel", "winkel", ["hebel"], True)
    assert {e["id"] for e in schwenk["pruefungen"]} >= {"freiheitsgrad:hebel", "sollweg:Schwenk:hebel", "grenze:Schwenk"}
    json.dumps(erg)  # geht in bestand.json
    assert mech.geloest == ["Schwenk", "Schwenk", "Hub"] and mech.unterdrueckt == set() and mech.gehalten == set()  # erste: Probeschritt


def test_bekannte_kollision_ist_keine_in_der_fahrt():
    erg = fahre_alle()
    assert erg["Hub"]["kollisionen"] == [] and all(e["ok"] for e in erg["Hub"]["pruefungen"])
    assert all(e["ok"] for e in erg["Schwenk"]["pruefungen"])


def test_eine_kaputte_grenze_kostet_nur_sie_selbst():
    mech = SchwenkKaputt()
    a = aufnahme()
    a["verknuepfungen"]["Schwenk"]["partner"] = ["hebel", "platte"]  # bewegte Seite ohne Probeschritt
    erg = fahre_alle(mech, a)
    assert erg["Schwenk"]["gefahren"] is False and "Schwenk" in erg["Schwenk"]["hinweis"] and "Zwang" in erg["Schwenk"]["hinweis"]
    assert erg["Schwenk"]["komponente"] == "hebel" and erg["Schwenk"]["pruefungen"] == [] and erg["Schwenk"]["bewegt"] == []
    assert erg["Hub"]["gefahren"] is True and erg["Hub"]["bewegt"] == ["schieber", "hebel"]
    assert all(e["ok"] for e in erg["Hub"]["pruefungen"])
    assert mech.unterdrueckt == set() and mech.gehalten == set()


class SchwenkFaelltHeraus(Attrappe):
    """Die Grundstellung des Schwenks scheitert, die Stellung `geht` gelingt (`None`: nichts gelingt mehr)."""

    def __init__(self, geht=None):
        super().__init__()
        self.geht = geht

    def halte(self, b, wert):
        if b.name == "Schwenk" and wert != self.geht:
            raise StellungFehler("Schwenk", wert, "Zwang")
        super().halte(b, wert)


def _schwenk_faellt_heraus(wert):
    a = aufnahme()
    a["verknuepfungen"]["Schwenk"]["partner"] = ["hebel", "platte"]  # bewegte Seite ohne Probeschritt
    a["verknuepfungen"]["Schwenk"]["wert"] = wert
    return a


def test_herausgefallene_grenze_steht_wieder_auf_dem_gelesenen_wert():
    """Zusatz Task 8: Die übrigen Grenzen fahren sonst aus einer Lage, die es im Bestand nicht gibt."""
    mech = SchwenkFaelltHeraus(geht=30.0)
    mech.werte["Schwenk"] = 70.0            # wo die gescheiterte Fahrt sie stehen ließ
    erg = fahre_alle(mech, _schwenk_faellt_heraus(30.0))
    assert mech.werte["Schwenk"] == 30.0 and "Ausgangslage" not in erg["Schwenk"]["hinweis"]
    assert mech.unterdrueckt == set() and mech.gehalten == set() and erg["Hub"]["gefahren"] is True


def test_nicht_zurueckgestellte_grenze_traegt_den_hinweis():
    mech = SchwenkFaelltHeraus()
    erg = fahre_alle(mech, _schwenk_faellt_heraus(30.0))
    assert "Ausgangslage" in erg["Schwenk"]["hinweis"] and "Zwang" in erg["Schwenk"]["hinweis"]
    assert mech.unterdrueckt == set() and mech.gehalten == set()


def test_unbekannter_wert_der_grenze_traegt_den_hinweis():
    erg = fahre_alle(SchwenkFaelltHeraus(), _schwenk_faellt_heraus(None))
    assert "Wert der Grenze nicht gelesen" in erg["Schwenk"]["hinweis"]


def test_probeschritt_stellt_auf_den_gelesenen_wert_zurueck():
    a = aufnahme()
    a["verknuepfungen"]["Schwenk"]["wert"] = 30.0
    mech = Attrappe()
    assert bewegte_seite(mech, "Schwenk", a["verknuepfungen"]["Schwenk"], a) == "hebel"
    assert mech.werte["Schwenk"] == 30.0


def test_gescheiterter_probeschritt_stellt_zurueck():
    a = aufnahme()
    a["verknuepfungen"]["Schwenk"]["wert"] = 30.0
    mech = Attrappe(fehler_bei=("Schwenk", 90.0))
    erg = fahre_alle(mech, a)
    assert erg["Schwenk"]["gefahren"] is False and mech.gehalten == set() and mech.unterdrueckt == set()


def test_ohne_fahrt_ist_null_nicht_false():
    a = aufnahme()
    e = ohne_fahrt(grenzen_der_aufnahme(a), "ohne Bewegung")
    assert e["Hub"]["gefahren"] is None and e["Hub"]["hinweis"] == "ohne Bewegung" and e["Hub"]["min"] == 0.0
    json.dumps(e)


def test_probeschritt_gescheitert_kostet_nur_die_grenze():
    erg = fahre_alle(Attrappe(fehler_bei=("Schwenk", 90.0)))
    assert erg["Schwenk"]["gefahren"] is False and "Probeschritt gescheitert" in erg["Schwenk"]["hinweis"]
    assert erg["Schwenk"]["komponente"] is None and erg["Hub"]["gefahren"] is True


def test_alle_grenzen_kaputt_fahren_nichts():
    class Kaputt(Attrappe):
        def halte(self, b, wert):
            raise StellungFehler(b.name, wert, "Zwang")

    erg = fahre_alle(Kaputt())
    assert [e["gefahren"] for e in erg.values()] == [False, False]


def test_grenze_ohne_weg_wird_nicht_gefahren():
    a = aufnahme()
    a["verknuepfungen"]["Hub"]["max"] = 0.0
    mech = Attrappe()
    erg = fahre_bestand(mech, a, {"Hub": a["verknuepfungen"]["Hub"]}, 4, set(), 3500, 0.1)
    assert erg["Hub"]["gefahren"] is False and "min gleich max" in erg["Hub"]["hinweis"] and erg["Hub"]["komponente"] == "schieber"
    assert mech.aufrufe == []  # fahre läuft nicht einmal an
    erg = fahre_alle(a=a)  # die andere Grenze fährt weiter
    assert erg["Hub"]["gefahren"] is False and erg["Schwenk"]["gefahren"] is True


@pytest.mark.parametrize("feld,wert,text", [("max", None, "nicht gelesen"), ("min", 200.0, "größer"),
                                            ("typ", 0, "weder Abstand noch Winkel"),
                                            ("partner", None, "nicht gelesen")])
def test_unlesbare_grenze_wird_nicht_gefahren(feld, wert, text):
    a = aufnahme()
    a["verknuepfungen"]["Hub"][feld] = wert
    erg = fahre_alle(a=a)
    assert erg["Hub"]["gefahren"] is False and text in erg["Hub"]["hinweis"]
    assert erg["Schwenk"]["gefahren"] is True


def test_grenze_an_der_hauptbaugruppe_fuehrt_die_andere_seite():
    a = aufnahme()
    a["verknuepfungen"]["Hub"]["partner"] = [None, "schieber"]
    mech = Attrappe()
    erg = fahre_bestand(mech, a, {"Hub": a["verknuepfungen"]["Hub"]}, 4, BEKANNT, 3500, 0.1)
    assert erg["Hub"]["komponente"] == "schieber" and erg["Hub"]["gefahren"] is True
    a["verknuepfungen"]["Hub"]["partner"] = [None, None]
    erg = fahre_bestand(Attrappe(), a, {"Hub": a["verknuepfungen"]["Hub"]}, 4, set(), 3500, 0.1)
    assert erg["Hub"]["gefahren"] is False and "keine bewegte Komponente" in erg["Hub"]["hinweis"]


def test_lauf_mit_fehler_ist_gefahren_mit_hinweis():
    erg = fahre_alle(Attrappe(fehler_bei=("Hub", 50.0)))
    assert erg["Hub"]["gefahren"] is True and "50" in erg["Hub"]["hinweis"] and "Rebuild-Fehler" in erg["Hub"]["hinweis"]
    assert {e["id"]: e["ok"] for e in erg["Hub"]["pruefungen"]}["bewegung:Hub"] is False


def test_speicher_knapp_bricht_ab():
    from swki.baugruppe.bewegungslauf import SpeicherKnapp

    mech = Attrappe(speicher=5000.0)
    with pytest.raises(SpeicherKnapp):
        fahre_alle(mech)
    assert mech.unterdrueckt == set() and mech.gehalten == set()


# --------------------------------------------------------------------------------------------------------------- Vergleich

def punkt(typ: str, pid: str, **felder) -> dict:
    return {"id": pid, "typ": typ, **felder}


def spec_aus(*punkte, **rest) -> dict:
    return {"art": "aenderung", "name": "T", "punkte": list(punkte), **rest}


def neu_punkt(pid: str) -> dict:
    return punkt("komponente_neu", pid, quelle={"normteil": "ISO 4762 M6x16"})


def ersetzen(pid: str, alt: str) -> dict:
    return punkt("komponente_ersetzen", pid, komponente=alt, quelle={"normteil": "ISO 4762 M6x16"})


def vergleich(vorher_bew, nachher_bew, spec=None, neue=None, ersetzt=None, vorher=None, nachher=None) -> dict[str, dict]:
    v = vorher or aufnahme(bewegungen=vorher_bew)
    n = nachher or aufnahme(bewegungen=nachher_bew)
    eintraege = vergleiche_bewegungen(v, n, spec or spec_aus(), neue or {}, ersetzt)
    assert len({e["id"] for e in eintraege}) == len(eintraege)
    return {e["id"]: e for e in eintraege}


@pytest.fixture(scope="module")
def gefahren() -> dict:
    return fahre_alle()


def kopie(basis, **felder) -> dict:
    """Die Fahrt (Hub und Schwenk) als Kopie; `felder` ersetzt Felder von Hub."""
    k = copy.deepcopy(basis)
    k["Hub"].update(felder)
    return k


def setze(k: dict, g: str, pid: str, ok, hinweis=None) -> None:
    """Die Prüfung `pid` der Grenze `g` auf `ok` stellen."""
    for e in k[g]["pruefungen"]:
        if e["id"] == pid:
            e["ok"] = ok
            if hinweis:
                e["hinweis"] = hinweis
            return
    raise KeyError(pid)


def falsche(e: dict[str, dict]) -> list[str]:
    return sorted(k for k, x in e.items() if x["ok"] is False)


def test_gefahren_und_nachher_ohne_fehler_ok(gefahren):
    e = vergleich(gefahren, copy.deepcopy(gefahren))
    assert {"bewegung:Hub", "bewegung_menge:Hub", "bewegung_kollision:Hub", "grenze:Hub", "sollweg:Hub:schieber", "freiheitsgrad:schieber",
            "bewegung:Schwenk", "bewegung_menge:Schwenk", "sollweg:Schwenk:hebel"} <= set(e)
    assert all(x["ok"] is True for x in e.values()), {k: x for k, x in e.items() if x["ok"] is not True}


def test_gefahren_und_nachher_fehler_ist_mangel(gefahren):
    nachher = kopie(gefahren)
    setze(nachher, "Hub", "grenze:Hub", False, "Schritt oben ging durch")
    e = vergleich(gefahren, nachher)
    assert falsche(e) == ["grenze:Hub"] and "ging durch" in e["grenze:Hub"]["hinweis"]


def test_nachher_nicht_gefahren_ist_mangel(gefahren):
    nachher = kopie(gefahren, gefahren=False, hinweis="Stellung 0 nicht herstellbar", bewegt=[], pruefungen=[])
    e = vergleich(gefahren, nachher)
    assert falsche(e) == ["bewegung:Hub"] and "nicht herstellbar" in e["bewegung:Hub"]["hinweis"]
    assert e["bewegung:Schwenk"]["ok"] is True


def test_nachher_ohne_gelesene_fahrt_ist_nicht_nachgewiesen(gefahren):
    nachher = kopie(gefahren)
    del nachher["Hub"]["gefahren"]
    e = vergleich(gefahren, nachher)
    assert e["bewegung:Hub"]["ok"] is None and falsche(e) == []


def test_im_bestand_nicht_gefahren_ist_kein_mangel(gefahren):
    vorher = kopie(gefahren, gefahren=False, hinweis="Stellung 0 nicht herstellbar (Zwang)", bewegt=[], pruefungen=[])
    nachher = kopie(gefahren, gefahren=False, hinweis="auch nicht", bewegt=[], pruefungen=[])
    e = vergleich(vorher, nachher)
    assert e["bewegung:Hub"]["ok"] is True and "Zwang" in e["bewegung:Hub"]["hinweis"] and "bewegung_menge:Hub" not in e
    # fährt der Lauf, ist das kein Mangel und kein Soll
    assert vergleich(vorher, copy.deepcopy(gefahren))["bewegung:Hub"]["ok"] is True
    assert falsche(vergleich(vorher, copy.deepcopy(gefahren))) == []


def test_was_im_bestand_nicht_bestand_ist_kein_mangel_des_laufs(gefahren):
    vorher = kopie(gefahren)
    setze(vorher, "Hub", "grenze:Hub", False, "Schritt oben ging durch")
    nachher = kopie(gefahren)
    setze(nachher, "Hub", "grenze:Hub", False, "Schritt oben ging durch")
    e = vergleich(vorher, nachher)
    assert e["grenze:Hub"]["ok"] is True and "Schon im Bestand nicht bestanden" in e["grenze:Hub"]["hinweis"]
    assert "ging durch" in e["grenze:Hub"]["hinweis"] and falsche(e) == []
    # im Bestand in Ordnung, im Lauf nicht: Mangel
    assert falsche(vergleich(gefahren, nachher)) == ["grenze:Hub"]
    # im Lauf nicht geprüft (ok None) bleibt nicht nachgewiesen
    nachher = kopie(gefahren)
    setze(nachher, "Hub", "grenze:Hub", None)
    assert vergleich(vorher, nachher)["grenze:Hub"]["ok"] is None


def test_freiheitsgrad_schon_im_bestand_unbestimmt_ist_kein_mangel(gefahren):
    vorher, nachher = kopie(gefahren), kopie(gefahren)
    for k in (vorher, nachher):
        setze(k, "Hub", "freiheitsgrad:schieber", False, "ohne Antrieb voll bestimmt")
    e = vergleich(vorher, nachher)
    assert e["freiheitsgrad:schieber"]["ok"] is True and falsche(e) == []
    assert falsche(vergleich(gefahren, nachher)) == ["freiheitsgrad:schieber"]


def test_grenze_fehlt_ohne_punkt_ist_mangel(gefahren):
    nachher = copy.deepcopy(gefahren)
    del nachher["Hub"]
    e = vergleich(gefahren, nachher)
    assert falsche(e) == ["bewegung:Hub"] and "fehlt im Lauf" in e["bewegung:Hub"]["hinweis"]
    assert falsche(vergleich(gefahren, {})) == ["bewegung:Hub", "bewegung:Schwenk"]


def test_grenze_geloescht_mit_punkt_ist_ok(gefahren):
    nachher = copy.deepcopy(gefahren)
    del nachher["Hub"]
    e = vergleich(gefahren, nachher, spec_aus(punkt("verknuepfung_loeschen", "d1", verknuepfung="Hub")))
    assert falsche(e) == [] and not [k for k in e if k.endswith("Hub") or ":Hub:" in k]
    assert e["bewegung:Schwenk"]["ok"] is True
    # ein entferntes Teil nimmt seine Verknüpfungen mit
    e = vergleich(gefahren, nachher, spec_aus(punkt("komponente_entfernen", "d2", komponente="schieber", verknuepfungen=["Hub"])))
    assert falsche(e) == []


def test_neuer_bereich_aus_punkt_gilt(gefahren):
    nachher = kopie(gefahren, max=25.0)
    spec = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Hub", grenze="max", alt=100, neu=25))
    e = vergleich(gefahren, nachher, spec)
    assert falsche(e) == [] and e["bewegung_menge:Hub"]["ok"] is True
    # ohne Punkt, oder mit einem Punkt für ein anderes Feld, ist der Bereich ein Mangel
    assert falsche(vergleich(gefahren, nachher)) == ["bewegung:Hub"]
    assert "max" in vergleich(gefahren, nachher)["bewegung:Hub"]["hinweis"]
    assert falsche(vergleich(gefahren, nachher, spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Hub", grenze="min", alt=0,
                                                                neu=0)))) == ["bewegung:Hub"]
    assert falsche(vergleich(gefahren, nachher, spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Hub", alt=100, neu=25)))) == [
        "bewegung:Hub"]
    # die Menge bleibt verlangt
    assert falsche(vergleich(gefahren, kopie(gefahren, max=25.0, bewegt=["schieber"]), spec)) == ["bewegung_menge:Hub"]


def test_andere_menge_ist_mangel(gefahren):
    e = vergleich(gefahren, kopie(gefahren, bewegt=["schieber"]))
    assert falsche(e) == ["bewegung_menge:Hub"] and e["bewegung_menge:Hub"]["fehlen"] == ["hebel"]
    e = vergleich(gefahren, kopie(gefahren, bewegt=["schieber", "hebel", "platte"]))
    assert falsche(e) == ["bewegung_menge:Hub"] and e["bewegung_menge:Hub"]["zusaetzlich"] == ["platte"]
    assert falsche(vergleich(gefahren, kopie(gefahren, bewegt=["hebel", "schieber"]))) == []  # Reihenfolge zählt nicht
    assert vergleich(gefahren, kopie(gefahren, bewegt=None))["bewegung_menge:Hub"]["ok"] is None


def test_neue_schraube_am_bewegten_teil_darf_mitfahren(gefahren):
    nachher = kopie(gefahren, bewegt=["schieber", "hebel", "Schraube-12", "Unter-2/Welle-1"])
    assert falsche(vergleich(gefahren, nachher)) == ["bewegung_menge:Hub"]  # ohne Punkt fährt sie unerklärt mit
    e = vergleich(gefahren, nachher, spec_aus(neu_punkt("k1"), neu_punkt("k2")), neue={"k1": ["Schraube-12"], "k2": ["Unter-2"]})
    assert falsche(e) == [] and e["bewegung_menge:Hub"]["ok"] is True
    # ein Protokoll, das kein Punkt deckt, gibt nichts frei
    assert falsche(vergleich(gefahren, nachher, neue={"k1": ["Schraube-12"], "k2": ["Unter-2"]})) == ["bewegung_menge:Hub"]


def test_entfernte_komponente_darf_fehlen_ersetzte_zieht_um(gefahren):
    nachher = kopie(gefahren, bewegt=["schieber"])
    assert falsche(vergleich(gefahren, nachher, spec_aus(punkt("komponente_entfernen", "e1", komponente="hebel", verknuepfungen=[])))) == []
    nachher = kopie(gefahren, bewegt=["schieber", "hebel2"])
    ersetzt, spec = {"hebel": "hebel2"}, spec_aus(ersetzen("r1", "hebel"))
    assert vergleich(gefahren, nachher, spec, ersetzt=ersetzt)["bewegung_menge:Hub"]["ok"] is True
    assert falsche(vergleich(gefahren, nachher)) == ["bewegung_menge:Hub"]  # ohne Ersetzung fehlt hebel
    assert falsche(vergleich(gefahren, nachher, ersetzt=ersetzt)) == ["bewegung_menge:Hub"]  # ohne Punkt gilt die Ersetzung nicht
    assert "bewegung_menge:Hub" in falsche(vergleich(gefahren, kopie(gefahren, bewegt=["schieber"]), spec, ersetzt=ersetzt))


def test_ersetzte_fixierte_komponente_darf_nicht_mitfahren(gefahren):
    nachher = kopie(gefahren, bewegt=["schieber", "hebel", "platte2"])
    e = vergleich(gefahren, nachher, spec_aus(ersetzen("r1", "platte")), ersetzt={"platte": "platte2"})
    assert falsche(e) == ["bewegung_menge:Hub"] and e["bewegung_menge:Hub"]["zusaetzlich"] == ["platte2"]


def test_protokoll_ohne_punkt_macht_die_fixierte_platte_nicht_frei(gefahren):
    nachher = kopie(gefahren, bewegt=["schieber", "hebel", "platte"])
    assert falsche(vergleich(gefahren, nachher, neue={"gibt_es_nicht": ["platte"]})) == ["bewegung_menge:Hub"]
    # ein Punkt, der die Komponente neu anlegt, hilft nicht, wenn sie im Bestand schon da ist (Protokoll ungültig)
    assert falsche(vergleich(gefahren, nachher, spec_aus(neu_punkt("k1")), neue={"k1": ["platte"]})) == ["bewegung_menge:Hub"]


def test_neue_kollision_ist_mangel_bekannte_nicht(gefahren):
    kollision = {"paar": ["anschlag", "hebel"], "volumen": 5.0}
    e = vergleich(gefahren, kopie(gefahren, kollisionen=[kollision]))
    assert falsche(e) == ["bewegung_kollision:Hub"] and e["bewegung_kollision:Hub"]["knoten"] == ["anschlag", "hebel"]
    assert e["bewegung_kollision:Hub"]["ist"] == [{"paar": ["anschlag", "hebel"], "volumen": 5.0}]
    # statisch im Bestand
    statisch = aufnahme(bewegungen=gefahren, kollisionen=[{"paar": ["hebel", "anschlag"], "volumen": 2.0}])
    assert falsche(vergleich(None, None, vorher=statisch, nachher=aufnahme(bewegungen=kopie(gefahren, kollisionen=[kollision])))) == []
    # in der Fahrt des Bestands (auch einer anderen Grenze)
    vorher = kopie(gefahren)
    vorher["Schwenk"]["kollisionen"] = [kollision]
    assert falsche(vergleich(vorher, kopie(gefahren, kollisionen=[kollision]))) == []
    # dasselbe Paar in mehreren Läufen zählt einmal
    e = vergleich(gefahren, kopie(gefahren, kollisionen=[kollision, {**kollision, "volumen": 7.0}]))
    assert e["bewegung_kollision:Hub"]["ist"] == [{"paar": ["anschlag", "hebel"], "volumen": 7.0}]
    # nicht gelesen
    assert vergleich(gefahren, kopie(gefahren, kollisionen=None))["bewegung_kollision:Hub"]["ok"] is None


def test_kollision_erlaubt_gilt_auch_in_der_fahrt(gefahren):
    kollision = {"paar": ["anschlag", "hebel"], "volumen": 5.0}
    nachher = kopie(gefahren, kollisionen=[kollision])
    spec = spec_aus(kollision_erlaubt=[{"paar": ["anschlag", "hebel"], "grund": "Anschlag"}])
    assert falsche(vergleich(gefahren, nachher, spec)) == []
    # eine Punkt-ID steht für die Komponenten, die der Lauf erzeugt hat
    nachher = kopie(gefahren, kollisionen=[{"paar": ["Anschlag-1", "hebel"], "volumen": 5.0}])
    spec = spec_aus(punkt("komponente_neu", "k1", quelle={"normteil": "x"}), kollision_erlaubt=[{"paar": ["k1", "hebel"], "grund": "x"}])
    assert falsche(vergleich(gefahren, nachher, spec, neue={"k1": ["Anschlag-1"]})) == []
    assert falsche(vergleich(gefahren, nachher, spec)) == ["bewegung_kollision:Hub"]


def test_bekannte_paare():
    vorher = aufnahme(kollisionen=[{"paar": ["platte", "hebel"], "volumen": 1.0}],
                      bewegungen={"Hub": {"kollisionen": [{"paar": ["schieber", "bolzen"], "volumen": 1.0}]}, "Schwenk": {}})
    spec = spec_aus(neu_punkt("k1"), kollision_erlaubt=[{"paar": ["k1", "schieber"], "grund": "x"}])
    assert bekannte_paare(vorher, spec, {"k1": ["Neu-1"]}) == {
        frozenset({"platte", "hebel"}), SCHIEBER_BOLZEN, frozenset({"Neu-1", "schieber"})}
    # ohne Punkt, der das Protokoll deckt, bleibt die Punkt-ID ein Name
    assert bekannte_paare(vorher, spec_aus(kollision_erlaubt=spec["kollision_erlaubt"]), {"k1": ["Neu-1"]}) == {
        frozenset({"platte", "hebel"}), SCHIEBER_BOLZEN, frozenset({"k1", "schieber"})}
    # ersetzte Komponenten gelten unter dem neuen Namen
    assert bekannte_paare(vorher, spec_aus(ersetzen("r1", "hebel"), ersetzen("r2", "schieber")), {},
                          {"hebel": "hebel2", "schieber": "schieber2"}) == {
        frozenset({"platte", "hebel2"}), frozenset({"schieber2", "bolzen"})}
    assert statische_paare(vorher) == {frozenset({"platte", "hebel"})}


def test_ohne_fahrt_in_der_aufnahme_ist_ok_none(gefahren):
    e = vergleich({}, gefahren)  # --ohne-bewegung
    assert [e["bewegung:Hub"]["ok"], e["bewegung:Schwenk"]["ok"]] == [None, None] and "bewegung_menge:Hub" not in e
    vorher = copy.deepcopy(gefahren)
    del vorher["Hub"]["gefahren"]  # gefahren nicht gesetzt
    e = vergleich(vorher, gefahren)
    assert e["bewegung:Hub"]["ok"] is None and e["bewegung:Schwenk"]["ok"] is True
    # ohne Fahrt im Bestand nützt auch ein fehlender Lauf nichts
    assert falsche(vergleich({}, {})) == []


def test_ohne_grenzen_nichts_zu_vergleichen():
    a = aufnahme(verknuepfungen={}, bewegungen={})
    assert vergleiche_bewegungen(a, copy.deepcopy(a), spec_aus(), {}) == []


def test_unterbaugruppe_nur_hinweis(gefahren):
    a = aufnahme(bewegungen=gefahren)
    a["verknuepfungen"]["Unten"] = verknuepfung(5, ["Unter-1/Welle-1", "platte"], min_=0.0, max_=5.0, grenze=True)
    a["komponenten"]["Frei-1"] = komponente("teile/Welle.SLDPRT")
    a["komponenten"]["Frei-1"]["status"]["Standard"] = 2
    a["komponenten"]["Fest-1"] = komponente("teile/Welle.SLDPRT", fixiert=True)
    a["komponenten"]["Fest-1"]["status"]["Standard"] = 2  # fixiert bewegt sich nicht
    assert abdeckung(a) == ["Grenze Unten liegt in einer Unterbaugruppe (Unter-1/Welle-1, platte), nicht gefahren",
                            "Komponente Frei-1 ist beweglich (unterbestimmt) und hat keine Grenze, nicht gefahren"]
    e = vergleich(None, None, vorher=a, nachher=copy.deepcopy(a))
    assert falsche(e) == [] and "Unten" not in " ".join(e) and "Unterbaugruppe" in e["bewegung_abdeckung"]["hinweis"]
    assert "Frei-1" in e["bewegung_abdeckung"]["hinweis"] and e["bewegung_abdeckung"]["ok"] is True
    assert abdeckung(aufnahme()) == []


def test_neue_grenze_im_lauf_hat_kein_soll(gefahren):
    nachher = copy.deepcopy(gefahren)
    nachher["Neu"] = copy.deepcopy(gefahren["Hub"])
    for e in nachher["Neu"]["pruefungen"]:
        e["id"] = e["id"].replace("Hub", "Neu")
    setze(nachher, "Neu", "grenze:Neu", False, "ging durch")
    e = vergleich(gefahren, nachher)
    assert falsche(e) == ["grenze:Neu"] and "bewegung_menge:Neu" not in e
    nachher["Neu"].update(gefahren=False, hinweis="Zwang")
    e = vergleich(gefahren, nachher)
    assert e["bewegung:Neu"]["ok"] is None and falsche(e) == []


def test_lauf_ohne_eine_pruefung_beweist_nichts(gefahren):
    nachher = kopie(gefahren)
    nachher["Hub"]["pruefungen"] = [x for x in nachher["Hub"]["pruefungen"]
                                    if x["id"] not in ("bewegung:Hub", "bewegung_kollision:Hub", "sollweg:Hub:schieber")]
    e = vergleich(gefahren, nachher)
    assert e["bewegung:Hub"]["ok"] is None and e["bewegung_kollision:Hub"]["ok"] is None
    assert e["sollweg:Hub:schieber"]["ok"] is None and falsche(e) == []
    leer = kopie(gefahren, pruefungen=[])  # gar keine Prüfungen: nichts bestanden
    e = vergleich(gefahren, leer)
    assert all(x["ok"] is None for k, x in e.items() if (k.endswith("Hub") or "Hub:" in k or k == "freiheitsgrad:schieber")
               and not k.startswith("bewegung_menge"))


def test_ersetzte_komponente_behaelt_ihre_pruefungen(gefahren):
    nachher = kopie(gefahren, komponente="schieber2", bewegt=["schieber2", "hebel"])
    for x in nachher["Hub"]["pruefungen"]:
        x["id"] = x["id"].replace("schieber", "schieber2")
    setze(nachher, "Hub", "sollweg:Hub:schieber2", False)
    e = vergleich(gefahren, nachher, spec_aus(ersetzen("r1", "schieber")), ersetzt={"schieber": "schieber2"})
    assert falsche(e) == ["sollweg:Hub:schieber2"]
    assert e["freiheitsgrad:schieber2"]["ok"] is True


def test_nur_dieselbe_id_wird_zusammengefuehrt(gefahren):
    # zwei Grenzen an derselben Komponente: freiheitsgrad:<k> steht nur einmal, das schlechtere Urteil gilt
    zwei = copy.deepcopy(gefahren)
    zwei["Zwei"] = copy.deepcopy(gefahren["Hub"])
    for x in zwei["Zwei"]["pruefungen"]:
        x["id"] = x["id"].replace("Hub", "Zwei")
    nachher = copy.deepcopy(zwei)
    setze(nachher, "Zwei", "freiheitsgrad:schieber", False, "mit Antrieb unterbestimmt")
    a = aufnahme(bewegungen=zwei)
    a["verknuepfungen"]["Zwei"] = copy.deepcopy(a["verknuepfungen"]["Hub"])
    b = aufnahme(bewegungen=nachher)
    b["verknuepfungen"]["Zwei"] = copy.deepcopy(b["verknuepfungen"]["Hub"])
    e = vergleich(None, None, vorher=a, nachher=b)
    assert falsche(e) == ["freiheitsgrad:schieber"]


# ------------------------------------------------------------------------------------- Korrekturrunde 1 (Review Task 6)

def test_im_bestand_nicht_gefahren_der_lauf_faehrt_trotzdem(gefahren):
    """Bestand ohne Weg, ein Punkt öffnet den Bereich: Die Fahrt des Laufs wird bewertet, ihr Fehler und ihre neue Kollision zählen."""
    vorher = kopie(gefahren, gefahren=False, hinweis="min gleich max: kein Weg, nicht gefahren", bewegt=[], pruefungen=[], max=0.0)
    lauf = fahre_alle(Attrappe(fehler_bei=("Hub", 50.0)))
    lauf["Hub"]["kollisionen"] = [{"paar": ["anschlag", "hebel"], "volumen": 500.0}]
    e = vergleich(vorher, lauf, spec_aus(punkt("verknuepfung_wert", "w", verknuepfung="Hub", grenze="max", alt=0, neu=100)))
    assert "bewegung:Hub" in falsche(e) and "bewegung_kollision:Hub" in falsche(e)
    assert "kein Weg" in e["bewegung:Hub"]["hinweis"]  # der Grund bleibt im Eintrag
    assert "bewegung_menge:Hub" not in e  # kein Soll für die Menge
    # fuhr auch der Lauf nicht, bleibt es bei ok True mit Hinweis
    e = vergleich(vorher, kopie(vorher, hinweis="auch nicht"))
    assert e["bewegung:Hub"]["ok"] is True and "kein Weg" in e["bewegung:Hub"]["hinweis"]
    # fährt der Lauf sauber, bleibt es ohne Mangel und der Grund steht weiter da
    e = vergleich(vorher, copy.deepcopy(gefahren))
    assert falsche(e) == [] and "kein Weg" in e["bewegung:Hub"]["hinweis"]


def bricht_ab(stellung: float, **kw) -> dict:
    return fahre_alle(Attrappe(fehler_bei=("Hub", stellung)), **kw)


def test_lauf_darf_nicht_frueher_abbrechen_als_der_bestand():
    bestand, spaeter, frueher = bricht_ab(100.0), bricht_ab(100.0), bricht_ab(75.0)
    # der Bestand bricht bei 100 ab (Belege in `ist`): gleicher Abbruch ist kein Mangel des Laufs
    assert [x["ist"][0]["stellung"] for x in bestand["Hub"]["pruefungen"] if x["id"] == "bewegung:Hub"] == [100.0]
    e = vergleich(bestand, spaeter)
    assert e["bewegung:Hub"]["ok"] is True and "nicht schlechter" in e["bewegung:Hub"]["hinweis"]
    # früher abbrechen ist schlechter, auch wenn die Prüfung beide Male ok False ist
    assert "bewegung:Hub" in falsche(vergleich(bestand, frueher))
    # ein Bestand, der bei 75 abbrach, hält einen Lauf bei 100 aus
    assert "bewegung:Hub" not in falsche(vergleich(frueher, bestand))
    # ein Abbruch, den der Bestand nicht hatte (anderes `gegen`), ist schlechter
    anders = copy.deepcopy(spaeter)
    for x in anders["Hub"]["pruefungen"]:
        if x["id"] == "bewegung:Hub":
            x["ist"][0]["gegen"] = {"Schwenk": "max"}
    assert "bewegung:Hub" in falsche(vergleich(bestand, anders))


def pruefung_mit_ist(k: dict, g: str, pid: str, ist) -> None:
    for x in k[g]["pruefungen"]:
        if x["id"] == pid:
            x["ok"], x["ist"] = False, ist
            return
    raise KeyError(pid)


def test_sollweg_nur_angehoben_wenn_nicht_schlechter(gefahren):
    def lauf(betrag, anzahl):
        k = kopie(gefahren)
        pruefung_mit_ist(k, "Hub", "sollweg:Hub:schieber", {"groesste_abweichung": {"betrag": betrag}, "abweichende_stellungen": anzahl})
        return k

    pid = "sollweg:Hub:schieber"
    assert vergleich(lauf(0.2, 1), lauf(0.2, 1))[pid]["ok"] is True
    assert vergleich(lauf(0.2, 1), lauf(0.1, 1))[pid]["ok"] is True
    assert vergleich(lauf(0.2, 1), lauf(50.0, 1))[pid]["ok"] is False  # Betrag größer
    assert vergleich(lauf(0.2, 1), lauf(0.2, 5))[pid]["ok"] is False  # mehr Stellungen
    kaputt = lauf(0.2, 1)
    pruefung_mit_ist(kaputt, "Hub", pid, None)
    assert vergleich(kaputt, kaputt)[pid]["ok"] is False  # unbekanntes Format wird nie angehoben


def test_grenze_nur_angehoben_wenn_durchgang_teilmenge(gefahren):
    def lauf(oben, unten):
        k = kopie(gefahren)
        pruefung_mit_ist(k, "Hub", "grenze:Hub", {"oben": oben, "unten": unten})
        return k

    assert vergleich(lauf(True, None), lauf(True, None))["grenze:Hub"]["ok"] is True
    assert vergleich(lauf(True, False), lauf(True, None))["grenze:Hub"]["ok"] is True
    assert vergleich(lauf(True, None), lauf(True, True))["grenze:Hub"]["ok"] is False  # unten geht neu durch
    assert vergleich(lauf(False, True), lauf(True, False))["grenze:Hub"]["ok"] is False


def test_freiheitsgrad_nur_angehoben_wenn_gleich(gefahren):
    def lauf(ohne, mit):
        k = kopie(gefahren)
        pruefung_mit_ist(k, "Hub", "freiheitsgrad:schieber", {"ohne_antrieb": ohne, "mit_antrieb": mit})
        return k

    assert vergleich(lauf(3, 3), lauf(3, 3))["freiheitsgrad:schieber"]["ok"] is True
    assert vergleich(lauf(3, 3), lauf(2, 3))["freiheitsgrad:schieber"]["ok"] is False


def test_weniger_stellungen_im_lauf_ist_mangel(gefahren):
    kurz = fahre_alle(schritte=1)
    assert gefahren["Hub"]["stellungen"] == 5 and kurz["Hub"]["stellungen"] == 2
    e = vergleich(gefahren, kurz)
    assert "bewegung:Hub" in falsche(e) and "2 Stellungen" in e["bewegung:Hub"]["hinweis"]
    assert falsche(vergleich(kurz, gefahren)) == []  # mehr ist in Ordnung
    # fehlt die Zahl in einem Stand, ist der Eintrag nicht nachgewiesen
    ohne = copy.deepcopy(gefahren)
    del ohne["Hub"]["stellungen"]
    assert vergleich(gefahren, ohne)["bewegung:Hub"]["ok"] is None
    assert vergleich(ohne, gefahren)["bewegung:Hub"]["ok"] is None
    assert vergleich(gefahren, ohne)["bewegung:Schwenk"]["ok"] is True
    # nicht gefahrene Grenzen tragen 0 Stellungen
    a = aufnahme()
    a["verknuepfungen"]["Hub"]["max"] = 0.0
    assert fahre_alle(a=a)["Hub"]["stellungen"] == 0


def test_neue_grenze_im_lauf_ohne_fahrt_eintrag_ist_nicht_nachgewiesen(gefahren):
    nachher = aufnahme(bewegungen={})
    vorher = aufnahme(bewegungen={}, verknuepfungen={})
    e = vergleiche_bewegungen(vorher, nachher, spec_aus(), {})
    assert {x["id"]: x["ok"] for x in e} == {"bewegung:Hub": None, "bewegung:Schwenk": None}
    ohne_feld = {k: x for k, x in nachher.items() if k != "bewegungen"}
    assert {x["id"]: x["ok"] for x in vergleiche_bewegungen(vorher, ohne_feld, spec_aus(), {})} == {"bewegung:Hub": None,
                                                                                                    "bewegung:Schwenk": None}
    # eine Grenze, die ein Punkt löscht, fällt nicht darunter
    assert vergleiche_bewegungen(vorher, nachher, spec_aus(punkt("verknuepfung_loeschen", "d", verknuepfung="Hub"),
                                                           punkt("verknuepfung_loeschen", "d2", verknuepfung="Schwenk")), {}) == []


def test_kollision_nur_im_paarlauf(gefahren):
    def nur_zusammen(w):
        return [{"paar": ["hebel", "platte"], "volumen": 9.0}] if w["Hub"] >= 100 and w["Schwenk"] >= 90 else []

    lauf = fahre_alle(Attrappe(kollision=nur_zusammen))
    assert {"paar": ["hebel", "platte"], "volumen": 9.0} in lauf["Hub"]["kollisionen"]  # nur im Lauf gegen den Schwenk
    e = vergleich(gefahren, lauf)
    assert falsche(e) == ["bewegung_kollision:Hub", "bewegung_kollision:Schwenk"]
    # kannte der Bestand sie aus seiner Fahrt, ist sie keine neue
    assert falsche(vergleich(lauf, copy.deepcopy(lauf))) == []


def test_kollision_ohne_befund_im_feld_ist_nicht_bestanden(gefahren):
    n = kopie(gefahren)
    setze(n, "Hub", "bewegung_kollision:Hub", False, "Kollision")
    e = vergleich(gefahren, n)["bewegung_kollision:Hub"]
    assert e["ok"] is None and "nicht nachgewiesen" in e["hinweis"]  # das Feld kollisionen trägt nichts
    setze(n, "Hub", "bewegung_kollision:Hub", None)
    assert vergleich(gefahren, n)["bewegung_kollision:Hub"]["ok"] is None
    # trägt das Feld nur bekannte Paare, ist die Prüfung des Laufs (False) ohne Belang
    n["Hub"]["kollisionen"] = [{"paar": ["bolzen", "schieber"], "volumen": 1.0}]
    setze(n, "Hub", "bewegung_kollision:Hub", False, "Kollision")
    assert vergleich(gefahren, n)["bewegung_kollision:Hub"]["ok"] is False  # der Bestand kennt das Paar nicht
    bekannt = aufnahme(bewegungen=gefahren, kollisionen=[{"paar": ["bolzen", "schieber"], "volumen": 1.0}])
    e = {x["id"]: x["ok"] for x in vergleiche_bewegungen(bekannt, aufnahme(bewegungen=n), spec_aus(), {})}
    assert e["bewegung_kollision:Hub"] is True


def test_gleicher_abbruch_in_beiden_staenden_besteht():
    """`grenze` und `sollweg` laufen nach einem Abbruch nicht (None); bricht der Bestand ebenso ab, besteht die Baugruppe trotzdem."""
    e = vergleich(bricht_ab(100.0), bricht_ab(100.0))
    assert all(x["ok"] is True for x in e.values()), {k: x for k, x in e.items() if x["ok"] is not True}
    assert "Abbruch" in e["grenze:Hub"]["hinweis"] and "Abbruch" in e["sollweg:Hub:schieber"]["hinweis"]
    assert "Schon im Bestand nicht bestanden" in e["bewegung:Hub"]["hinweis"]


def test_fruehere_abbruch_im_lauf_bleibt_mangel_und_none_bleibt_none():
    e = vergleich(bricht_ab(100.0), bricht_ab(75.0))
    assert falsche(e) == ["bewegung:Hub"] and e["grenze:Hub"]["ok"] is None and e["sollweg:Hub:schieber"]["ok"] is None
    # ein None nur im Lauf wird nicht angehoben (der Bestand lief durch)
    e = vergleich(fahre_alle(), bricht_ab(100.0))
    assert falsche(e) == ["bewegung:Hub"] and e["grenze:Hub"]["ok"] is None
    # ein None nur im Bestand ebenso: der Lauf hat die Prüfung, ihr Urteil gilt
    assert vergleich(bricht_ab(100.0), fahre_alle())["grenze:Hub"]["ok"] is True
    # weniger Stellungen als im Bestand heben die Prüfungen nach dem Abbruch nicht an
    kurz = fahre_alle(Attrappe(fehler_bei=("Hub", 100.0)), schritte=2)
    e = vergleich(bricht_ab(100.0), kurz)
    assert e["bewegung:Hub"]["ok"] is False and e["grenze:Hub"]["ok"] is None
