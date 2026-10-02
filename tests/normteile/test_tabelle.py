import copy
from pathlib import Path

import pytest

from swki.normteile.fehler import NormteilFehler
from swki.normteile.tabelle import lade_normtabelle, norm_datei, regel_erfuellt, tabellen_befunde

DATEN = Path(__file__).parent / "daten"


def _tabelle():
    return lade_normtabelle("ISO 9999", DATEN)


@pytest.mark.parametrize("text", ["ISO 9999", "ISO9999", "iso9999", "iso-9999"])
def test_norm_datei(text):
    assert norm_datei(text) == "iso9999"


def test_laden_normalisiert_schluessel():
    t = _tabelle()
    assert list(t["groessen"]) == ["M5", "M6", "M8"]
    assert t["vorgabe_variante"] == "8.8" and set(t["varianten"]) == {"8.8", "A2"}
    assert t["quellen"][0]["abgerufen"] == "2026-10-02"


def test_unbekannte_norm():
    with pytest.raises(NormteilFehler) as e:
        lade_normtabelle("ISO 1", DATEN)
    assert e.value.daten["code"] == "NORMTEIL_UNBEKANNT" and "iso9999" in str(e.value)


def test_testtabelle_ohne_befund():
    assert tabellen_befunde(_tabelle(), DATEN) == []


@pytest.mark.parametrize(("regel", "masse", "ok"), [
    ("b > a", {"a": 5, "b": 10}, True),
    ("b > a", {"a": 10, "b": 10}, False),
    ("b >= a", {"a": 10, "b": 10}, True),
    ("a == b/2", {"a": 5, "b": 10}, True),
    ("a*2 < b", {"a": 5, "b": 10}, False),
    ("a <= 3**0.5", {"a": 1.7}, True),
])
def test_regel(regel, masse, ok):
    assert regel_erfuellt(regel, masse) is ok


def _befunde(aendern):
    t = copy.deepcopy(_tabelle())
    aendern(t)
    return tabellen_befunde(t, DATEN)


@pytest.mark.parametrize(("aendern", "pfad"), [
    (lambda t: t["groessen"]["M6"]["masse"].update(b=5), "groessen.M6.masse"),          # Regel b > a verletzt
    (lambda t: t["groessen"]["M6"]["masse"].pop("b"), "groessen.M6.masse"),             # Maß fehlt
    (lambda t: t["groessen"]["M6"].update(laengen=[12, 10]), "groessen.M6.laengen"),    # nicht aufsteigend
    (lambda t: t["groessen"]["M6"].pop("laengen"), "groessen.M6"),                      # laenge: true ohne laengen
    (lambda t: t["groessen"]["M6"]["masse"].update(a=4.5), "parameter.a"),              # fällt mit der Größe
    (lambda t: t.update(vorgabe_variante="10.9"), "vorgabe_variante"),
    (lambda t: t.update(vorlage="vorlagen/fehlt.yaml"), "vorlage"),
    (lambda t: t["quellen"].pop(0), "groessen.M5.status"),                              # nur noch 1 Quelle
    (lambda t: t["regeln"].append("a b"), "regeln"),
])
def test_tabellenbefunde(aendern, pfad):
    assert pfad in [b["pfad"] for b in _befunde(aendern)]


def test_gesperrt_braucht_grund():
    befunde = _befunde(lambda t: t["groessen"]["M8"].pop("grund"))
    assert befunde and befunde[0]["pfad"].startswith("groessen")


def test_nutzerentscheidung_ersetzt_quellen():
    def entscheiden(t):
        t["quellen"].pop(0)
        t["groessen"]["M5"]["entscheidung"] = "Nutzer 2026-10-05: b = 10 (Quelle A 10, Quelle B 10.5)"
    assert "groessen.M5.status" not in [b["pfad"] for b in _befunde(entscheiden)]
