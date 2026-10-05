"""Stufe 4a: Ablauf der Bewegungsprüfung mit der Attrappe – Grundstellung, Grenze, Paarläufe, Speicher, Aufräumen."""

import pytest

from swki.baugruppe.bewegung import bewegungen
from swki.baugruppe.bewegungslauf import SpeicherKnapp, bewegungen_oder_ersatz, fahre
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


# --- Fehlerpfade (Fix-Welle nach dem Gesamt-Review, Spec 4a §8.2.3): Mangel statt Abbruch -------------------------------

def _oder_ersatz(mech, statisch=None, grenze_mb=3500, soll=("g1", "g2")):
    from types import SimpleNamespace

    messwerte = statisch or SimpleNamespace(rebuild_fehler=[], verknuepfungen={"g1": 0, "g2": 0}, unterdrueckt=[])
    gebaut = []

    def fabrik():
        gebaut.append(True)
        return mech

    ergebnis = bewegungen_oder_ersatz(BAUGRUPPE, bewegungen(BAUGRUPPE, lade_standard()), messwerte, fabrik, BEKANNT,
                                      grenze_mb, 0.1, soll)
    return ergebnis, gebaut


def _nach_id(pruefungen):
    return {p["id"]: p for p in pruefungen}


def test_ohne_statische_fehler_wird_gefahren():
    (pruefungen, bericht, laeufe), gebaut = _oder_ersatz(Attrappe())
    assert gebaut and len(laeufe) == 4 and len(bericht["laeufe"]) == 4
    assert _nach_id(pruefungen)["bewegung:Hub"]["ok"] is True


@pytest.mark.parametrize("statisch", [{"rebuild_fehler": ["Skizze1: Fehler"], "verknuepfungen": {"g1": 0}, "unterdrueckt": []},
                                      {"rebuild_fehler": [], "verknuepfungen": {"g1": 0, "g2": 3}, "unterdrueckt": []},
                                      {"rebuild_fehler": [], "verknuepfungen": {"g1": 0, "g2": 0}, "unterdrueckt": ["g2"]}])
def test_statische_fehler_verhindern_die_bewegungspruefung(statisch):
    from types import SimpleNamespace

    mech = Attrappe()
    (pruefungen, bericht, laeufe), gebaut = _oder_ersatz(mech, SimpleNamespace(**statisch))
    assert not gebaut and mech.aufrufe == [] and laeufe == [] and bericht == {"laeufe": [], "paare": []}
    p = _nach_id(pruefungen)
    assert sorted(p) == ["bewegung:Hub", "bewegung:Schwenk"]
    for e in p.values():
        assert e["ok"] is None and "statische Fehler (siehe rebuild/verknuepfungen)" in e["hinweis"] and e["knoten"] == []


def test_fehlende_verknuepfung_verhindert_die_bewegungspruefung():
    # Spec 4b §10 Fall 3: eine erwartete, im Modell fehlende Verknüpfung (z. B. eine Kopplung) ist ein statischer Fehler;
    # eine fremde Verknüpfung zählt nicht (sie meldet nur verknuepfungen)
    from types import SimpleNamespace

    mech = Attrappe()
    fremd = SimpleNamespace(rebuild_fehler=[], verknuepfungen={"g1": 0, "g2": 0, "fremd": 0}, unterdrueckt=[])
    (_, _, laeufe), gebaut = _oder_ersatz(Attrappe(), fremd)
    assert gebaut and len(laeufe) == 4
    fehlt = SimpleNamespace(rebuild_fehler=[], verknuepfungen={"g1": 0}, unterdrueckt=[])
    (pruefungen, bericht, laeufe), gebaut = _oder_ersatz(mech, fehlt)
    assert not gebaut and mech.aufrufe == [] and laeufe == [] and bericht == {"laeufe": [], "paare": []}
    p = _nach_id(pruefungen)
    assert sorted(p) == ["bewegung:Hub", "bewegung:Schwenk"]
    assert all(e["ok"] is None and e["knoten"] == [] for e in p.values())


def test_stellungfehler_wird_zum_mangel_der_bewegung():
    mech = Attrappe(fehler_bei=("Hub", 0.0))  # der Rückweg auf min scheitert nach dem Grundstellungslauf
    (pruefungen, bericht, laeufe), _ = _oder_ersatz(mech)
    p = _nach_id(pruefungen)
    assert p["bewegung:Hub"]["ok"] is False and p["bewegung:Hub"]["knoten"] == ["schieber"]
    assert "Stellung 0 nicht herstellbar" in p["bewegung:Hub"]["hinweis"]
    assert p["bewegung:Schwenk"]["ok"] is None and "nicht geprüft" in p["bewegung:Schwenk"]["hinweis"]
    assert mech.geloest == ["Schwenk", "Hub"] and mech.unterdrueckt == set()  # Aufräumen lief
    assert laeufe == [] and bericht == {"laeufe": [], "paare": []}


def test_baufehler_wird_zum_mangel_aller_bewegungen():
    mech = Attrappe(unterdruecke_baufehler=True)
    (pruefungen, _, _), _ = _oder_ersatz(mech)
    p = _nach_id(pruefungen)
    assert sorted(p) == ["bewegung:Hub", "bewegung:Schwenk"]
    assert p["bewegung:Hub"]["ok"] is False and p["bewegung:Hub"]["knoten"] == ["schieber"]
    assert p["bewegung:Schwenk"]["ok"] is False and p["bewegung:Schwenk"]["knoten"] == ["hebel"]
    for e in p.values():
        assert e["hinweis"].startswith("Abbruch der Bewegungsprüfung: ") and "Rebuild-Fehler" in e["hinweis"]


def test_speicher_knapp_bleibt_ein_abbruch():
    with pytest.raises(SpeicherKnapp):
        _oder_ersatz(Attrappe(speicher=5000.0))


def test_ersatz_im_bericht():
    from swki.baugruppe.bewegung import ergaenze_bericht

    (pruefungen, bericht, _), _ = _oder_ersatz(Attrappe(fehler_bei=("Hub", 0.0)))
    ganz = ergaenze_bericht({"pruefungen": [], "maengel": [], "bestanden": True, "bilder": {}}, pruefungen, bericht, {})
    assert ganz["bestanden"] is False
    assert [m["pruefung"] for m in ganz["maengel"]] == ["bewegung:Hub"] and ganz["maengel"][0]["knoten"] == ["schieber"]
