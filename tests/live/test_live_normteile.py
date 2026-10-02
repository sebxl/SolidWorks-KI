"""Live: Normteile aus Tabelle und Vorlage bauen und selbst prüfen (ohne Status, Urteil und Bibliothek)."""

import copy
import shutil

import pytest

from swki.konfig import lade_rechner
from swki.normteile.bau import baue_und_pruefe
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.schluessel import Anfrage
from swki.normteile.tabelle import lade_normtabelle

pytestmark = pytest.mark.sw


def _spec(norm, groesse, laenge=None):
    t = lade_normtabelle(norm)
    return erzeuge_spec(t, Anfrage(t["norm"], groesse, laenge, t["vorgabe_variante"]), vorlage_text(t))


def _pruefe(spec):
    ordner = lade_rechner().arbeitsordner / "SWKI-LIVE-NORMTEILE" / spec["name"]
    try:
        return baue_und_pruefe(spec, ordner)
    finally:
        shutil.rmtree(ordner, ignore_errors=True)


def _ok(ergebnis, *ids):
    assert ergebnis["bestanden"], ergebnis["maengel"]
    ok = {p["id"]: p["ok"] for p in ergebnis["pruefungen"]}
    assert all(ok.get(i) is True for i in ("huellquader", "volumen", "material", "eigenschaften", *ids)), ok


@pytest.mark.parametrize(("groesse", "laenge"), [("M5", 8), ("M10", 40), ("M16", 160)])
def test_iso4762(groesse, laenge):
    _ok(_pruefe(_spec("ISO 4762", groesse, laenge)), "mass:k", "mass:l", "mass:s", "mass:t", "mass:EINBAU_EBENE",
        "durchmesser:d", "durchmesser:dk")


@pytest.mark.parametrize("groesse", ["M5", "M10", "M16"])
def test_iso4032(groesse):
    _ok(_pruefe(_spec("ISO 4032", groesse)), "mass:m", "mass:s", "mass:EINBAU_EBENE", "durchmesser:d")


def test_verfaelschte_vorlage_scheitert():
    # Bauweg falsch (Innensechskant 10 % zu tief), Prüfung unverändert → die Selbstprüfung muss es finden.
    # Das Sollvolumen folgt dem Bauweg (volumen: auto aus derselben Spezifikation); einen falschen Bauweg fängt
    # masse_pruefen.
    spec = copy.deepcopy(_spec("ISO 4762", "M8", 30))
    spec["features"][1]["ende"]["tiefe"] = "=t*1.1"
    ergebnis = _pruefe(spec)
    assert not ergebnis["bestanden"]
    assert "mass:t" in {m["pruefung"] for m in ergebnis["maengel"]}


@pytest.mark.parametrize("groesse", ["M5", "M10", "M16"])
def test_iso7089(groesse):
    _ok(_pruefe(_spec("ISO 7089", groesse)), "mass:h", "mass:EINBAU_EBENE", "durchmesser:d1", "durchmesser:d2")


@pytest.mark.parametrize(("groesse", "laenge"), [("4", 8), ("8", 30), ("12", 100)])
def test_iso8734(groesse, laenge):
    _ok(_pruefe(_spec("ISO 8734", groesse, laenge)), "mass:l", "mass:EINBAU_EBENE_1", "mass:EINBAU_EBENE_2",
        "durchmesser:d")
