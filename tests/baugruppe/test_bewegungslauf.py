"""Stufe 4a: Ablauf der Bewegungsprüfung mit der Attrappe – Grundstellung, Grenze, Paarläufe, Speicher, Aufräumen."""

import pytest

from swki.baugruppe.bewegung import bewegungen
from swki.baugruppe.bewegungslauf import SpeicherKnapp, fahre
from swki.konfig import lade_standard
from tests.baugruppe.attrappe_mechanik import Attrappe
from tests.baugruppe.beispiel_bewegung import BAUGRUPPE

BEKANNT = {frozenset({"bolzen", "schieber"})}  # statische Überlappung: in den Läufen nicht neu


def _fahre(mech, grenze_mb=3500):
    return fahre(mech, bewegungen(BAUGRUPPE, lade_standard()), BEKANNT, grenze_mb, 0.1)


def test_ohne_befund():
    mech = Attrappe()
    m = _fahre(mech)
    assert mech.aufrufe[:8] == [("unterdruecke", "Hub", True), ("unterdruecke", "Schwenk", True), ("status",),
                                ("halte", "Hub"), ("halte", "Schwenk"), ("status",),
                                ("unterdruecke", "Schwenk", False), ("unterdruecke", "Hub", False)]
    assert m.status_frei == {"platte": 3, "schieber": 2, "hebel": 2}
    assert m.status_gehalten == {"platte": 3, "schieber": 3, "hebel": 3}
    assert mech.unterdrueckt == set()
    assert [(x.bewegung, x.gegen) for x in m.laeufe] == [("Hub", {}), ("Schwenk", {}), ("Hub", {"Schwenk": "max"}),
                                                          ("Schwenk", {"Hub": "max"})]
    hub = m.laeufe[0]
    assert hub.stellungen == [0.0, 25.0, 50.0, 75.0, 100.0] and hub.grenze == {"oben": False, "unten": None}
    assert all(x.kollisionen == [] and x.fehler is None for x in m.laeufe)
    assert [p["bewegungen"] for p in m.paare] == [["Hub", "Schwenk"]]
    assert mech.bilder == ["Hub-min", "Hub-mitte", "Hub-max", "Schwenk-min", "Schwenk-mitte", "Schwenk-max"]
    assert mech.geloest == ["Schwenk", "Hub"] and mech.werte == {"Hub": 0.0, "Schwenk": 0.0}


def test_bewegte_menge_und_raum():
    hub = _fahre(Attrappe()).laeufe[0]
    assert hub.bewegt == ["schieber", "hebel"] and len(hub.lagen) == 5
    assert hub.raum == pytest.approx([-100.0, 20.0, -30.0, 83.0, 48.0, 10.0])


def test_kollision_nur_im_paarlauf():
    mech = Attrappe(kollision=lambda w: [{"paar": ["anschlag", "hebel"], "volumen": 5.0}]
                    if w["Hub"] >= 75 and w["Schwenk"] >= 60 else [])
    m = _fahre(mech)
    assert [x.kollisionen for x in m.laeufe[:2]] == [[], []]
    assert [(k["stellung"], k["gegen"], k["paar"], k["bild"]) for x in m.laeufe[2:] for k in x.kollisionen] == [
        (75.0, {"Schwenk": "max"}, ["anschlag", "hebel"], "Hub-kollision-Schwenk-1.png"),
        (67.5, {"Hub": "max"}, ["anschlag", "hebel"], "Schwenk-kollision-Hub-1.png")]


def test_grenze_geht_durch():
    assert _fahre(Attrappe(durchlass={"Hub"})).laeufe[0].grenze == {"oben": True, "unten": None}


def test_lauffehler_beendet_den_lauf():
    m = _fahre(Attrappe(fehler_bei=("Hub", 50.0)))
    hub = m.laeufe[0]
    assert hub.fehler == {"stellung": 50.0, "meldung": "Rebuild-Fehler"} and hub.stellungen == [0.0, 25.0]
    assert hub.grenze == {} and [x.bewegung for x in m.laeufe] == ["Hub", "Schwenk"]  # keine Paarläufe mit Hub


def test_speicher_knapp_raeumt_auf():
    mech = Attrappe(speicher=5000.0)
    with pytest.raises(SpeicherKnapp) as e:
        _fahre(mech)
    assert e.value.daten == {"code": "SPEICHER_KNAPP", "privat_mb": 5000, "grenze_mb": 3500}
    assert mech.geloest == ["Schwenk", "Hub"]


def test_aufraeumfehler_verdeckt_die_ursache_nicht():
    mech = Attrappe(interferenz_wirft=True, loese_wirft=True)
    with pytest.raises(RuntimeError, match="Kollision kaputt"):
        _fahre(mech)
    assert mech.geloest == ["Schwenk", "Hub"]


def test_aufraeumen_aktiviert_die_grenzen():
    mech = Attrappe(halte_wirft=True)
    with pytest.raises(RuntimeError, match="Antrieb kaputt"):
        _fahre(mech)
    assert mech.unterdrueckt == set()
    assert mech.geloest == ["Schwenk", "Hub"]
