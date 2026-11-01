"""Referenz Hubeinheit ohne SolidWorks: `hubeinheit_rev.yaml` gegen eine Attrappe der Aufnahme, gebaut aus den Soll-Namen von
`werkzeuge/bestand_muster.py`. Das belegt Schema, Namen und Punkte, nicht die Musterdateien: Die Aufnahme des echten Musters prüft erst der
Live-Test (`tests/referenz/test_bestand.py`)."""

import copy
import shutil
from pathlib import Path

import pytest
import yaml

from swki.bestand.ablage import schreibe_aufnahme, schreibe_datei_aufnahme
from swki.bestand.spec import validieren
from swki.konfig import PROJEKT, Rechner
from swki.spec.laden import SpecFehler
from tests.bestand.beispiel_aufnahme import _feature, _mass
from tests.bestand.beispiel_baugruppe import baugruppen_aufnahme, komponente, sha, teil_aufnahme, verknuepfung
from werkzeuge.bestand_muster import HUB_DATEIEN, HUB_KOMPONENTEN, HUB_VERKNUEPFUNGEN, HUBEINHEIT, KONFIG_OHNE, TEILE_HUB

REFERENZ = PROJEKT / "tests" / "referenz" / "bestand"
SPEC = REFERENZ / "hubeinheit_rev.yaml"
TEIL_SPEC = REFERENZ / "anschlag_neu.yaml"
PLATZHALTER = "0" * 64
KONFIGURATIONEN = ["Standard", KONFIG_OHNE]
ABSTAND, DECKUNGSGLEICH = 5, 0
AUFSATZ = "Aufsatz-Linear austragen1"


def _spec() -> dict:
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def _je(wert) -> dict:
    return dict.fromkeys(KONFIGURATIONEN, wert)


def _komponente(datei: str, fixiert: bool = False, weg: bool = False) -> dict:
    k = komponente(datei, fixiert)
    return {**k, "konfigurationen": _je("Standard"), "fixiert": _je(fixiert), "status": _je(3), "transform": _je(k["transform"]["Standard"]),
            "unterdrueckt": {"Standard": False, KONFIG_OHNE: weg}}


def _mate(typ: int, partner: list, wert=None, min_=None, max_=None, grenze: bool = False) -> dict:
    v = verknuepfung(typ, partner, wert=wert, min_=min_, max_=max_, grenze=grenze)
    return {**v, "werte": _je({"wert": wert, "min": min_, "max": max_}), "fehler": _je(0), "unterdrueckt": _je(False)}


def _teil_grundplatte() -> dict:
    masse = [_mass(f"D1@{AUFSATZ}", AUFSATZ, _je(15.0))]
    return _teil(TEILE_HUB[0], masse, [], {})


def _teil_schlitten() -> dict:
    masse = [_mass("D1@Skizze1", "Skizze1", _je(60.0), "gesteuert", {"art": "variable", "name": "L"})]
    gleichungen = [{"index": 0, "text": '"L"= 60', "links": "L", "global": True},
                   {"index": 1, "text": '"D1@Skizze1" = "L"', "links": "D1@Skizze1", "global": False}]
    return _teil(TEILE_HUB[1], masse, gleichungen, {"L": 60.0})


def _teil(rel: str, masse: list, gleichungen: list, variablen: dict) -> dict:
    return teil_aufnahme(rel, masse=masse, gleichungen=gleichungen, variablen=variablen, konfigurationen=["Standard"],
                         features=[_feature("Skizze1", "ProfileFeature", kinder=[AUFSATZ]), _feature(AUFSATZ, "Extrusion", eltern=["Skizze1"])])


def _aufnahme() -> dict:
    dateien = {rel: {"original": f"D:\\Kollege\\{rel}", "sha256": sha(rel), "art": "baugruppe" if rel.endswith("ASM") else "teil",
                     "versionen": [], "version_aelter": False, "referenzen": []} for rel in HUB_DATEIEN if rel != HUBEINHEIT}
    komponenten = {"Grundplatte-1": _komponente(TEILE_HUB[0], fixiert=True), "Schlitten-1": _komponente(TEILE_HUB[1]),
                   "Anschlag-1": _komponente(TEILE_HUB[2]), "Anschlag-2": _komponente(TEILE_HUB[2]),
                   "Muster-1": _komponente("Muster.SLDASM", weg=True), "Muster-1/Lagerdeckel-1": _komponente("Lagerdeckel.SLDPRT", weg=True),
                   "Muster-1/gm42-10-1": _komponente("gm42-10.SLDPRT", weg=True)}
    assert set(komponenten) == set(HUB_KOMPONENTEN)
    partner = {"Schlitten": ["Schlitten-1", "Grundplatte-1"], "Anschlag1": ["Anschlag-1", "Grundplatte-1"],
               "Anschlag2": ["Anschlag-2", "Grundplatte-1"], "Antrieb": ["Muster-1", None]}
    verknuepfungen = {n: _mate(DECKUNGSGLEICH, partner[n.split()[0] if not n.startswith("Hub") else "Schlitten"]) for n in HUB_VERKNUEPFUNGEN}
    verknuepfungen["Hub"] = _mate(ABSTAND, partner["Schlitten"], wert=0.0, min_=0.0, max_=25.0, grenze=True)
    verknuepfungen["Schlitten Seite"] = _mate(ABSTAND, partner["Schlitten"], wert=15.0)
    bewegungen = {"Hub": {"komponente": "Schlitten-1", "art": "abstand", "min": 0.0, "max": 25.0, "gefahren": True,
                          "bewegt": ["Schlitten-1"], "kollisionen": [], "pruefungen": [], "hinweis": None}}
    return baugruppen_aufnahme(datei={"name": HUBEINHEIT, "original": f"D:\\Kollege\\{HUBEINHEIT}", "sha256": PLATZHALTER, "versionen": [],
                                      "version_aelter": False},
                               konfigurationen=KONFIGURATIONEN, dateien=dateien, komponenten=komponenten, verknuepfungen=verknuepfungen,
                               bewegungen=bewegungen, kollisionen=[], eigenschaften={"datei": {"Revision": "A"}, "konfiguration": _je({})},
                               reihenfolge=_je([]))


@pytest.fixture
def auftrag(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    monkeypatch.setattr("swki.bestand.spec.lade_rechner", lambda: r)
    schreibe_aufnahme(r, "REF", 1, _aufnahme())
    schreibe_datei_aufnahme(r, "REF", 1, TEILE_HUB[0], _teil_grundplatte())
    schreibe_datei_aufnahme(r, "REF", 1, TEILE_HUB[1], _teil_schlitten())
    ordner = tmp_path / "REF"
    ordner.mkdir()
    shutil.copy2(TEIL_SPEC, ordner / TEIL_SPEC.name)
    return ordner


def _schreibe(ordner: Path, spec: dict) -> Path:
    pfad = ordner / SPEC.name
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def test_referenz_nennt_alle_punkt_typen_aus_dem_plan():
    typen = [p["typ"] for p in _spec()["punkte"]]
    assert sorted(set(typen)) == sorted({"mass", "gleichung", "komponente_neu", "verknuepfung_neu", "verknuepfung_wert",
                                         "komponente_entfernen", "komponente_ersetzen"})
    assert typen.count("verknuepfung_neu") == 2 and _spec()["kollision_erlaubt"]
    p1 = next(p for p in _spec()["punkte"] if p["typ"] == "mass")
    assert p1["in_datei"] == TEILE_HUB[0] and p1["lage_folgen"]
    assert next(p for p in _spec()["punkte"] if p["typ"] == "verknuepfung_wert")["grenze"] == "max"


def test_sha_ist_der_benannte_platzhalter():
    """Bis das Muster im Git liegt: Der Live-Test setzt die SHA-256 der erzeugten Datei ein, `lagerdeckel_rev.yaml` macht es für andere Jahre genauso."""
    assert _spec()["bestand"]["sha256"] == PLATZHALTER and "PLATZHALTER" in SPEC.read_text(encoding="utf-8")


def test_referenz_ist_gueltig_gegen_die_soll_namen(auftrag):
    erg = validieren(_schreibe(auftrag, _spec()))
    assert erg["gueltig"] is True and erg["punkte"] == len(_spec()["punkte"])
    assert erg["folgen"]["p2"] == ["D1@Skizze1"] and erg["haupt_speichern"] is True
    assert set(erg["dateien"]) == set(TEILE_HUB[:2])
    assert not [h for h in erg["hinweise"] if h["art"] == "grenzen_ohne_fahrt"]


def test_fehlende_verknuepfung_beim_entfernen(auftrag):
    spec = copy.deepcopy(_spec())
    p = next(p for p in spec["punkte"] if p["typ"] == "komponente_entfernen")
    p["verknuepfungen"] = p["verknuepfungen"][:-1]
    with pytest.raises(SpecFehler) as e:
        validieren(_schreibe(auftrag, spec))
    assert "VERKNUEPFUNGEN_FEHLEN" in [b.get("code") for b in e.value.daten["befunde"]]


def test_aufgabe_nennt_jeden_punkt():
    text = (REFERENZ / "eingabe" / "aufgabe_baugruppe.md").read_text(encoding="utf-8")
    assert all(wort in text for wort in ("Grundplatte", "Schlitten", "Hub", "Anschlag", "M6"))
