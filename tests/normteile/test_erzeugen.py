from pathlib import Path

import pytest

from swki.normteile.erzeugen import erzeuge_spec, spec_befunde, teil_pruefsumme, vorlage_pruefsumme, vorlage_text
from swki.normteile.fehler import NormteilFehler
from swki.normteile.schluessel import Anfrage, loese_auf, naechste_laengen

DATEN = Path(__file__).parent / "daten"


def test_aufloesen_mit_vorgabevariante():
    _, a = loese_auf("iso 9999", "M6 x 12", ordner=DATEN)
    assert a == Anfrage("ISO 9999", "M6", 12.0, "8.8")
    assert a.schluessel == "ISO9999_M6x12_8_8" and a.bezeichnung == "M6 x 12"


@pytest.mark.parametrize(("groesse", "variante", "code"), [
    ("M7x12", None, "NORMTEIL_UNBEKANNT"),
    ("Mx", None, "NORMTEIL_UNBEKANNT"),
    ("M6", None, "NORMLAENGE_UNGUELTIG"),
    ("M6x13", None, "NORMLAENGE_UNGUELTIG"),
    ("M6x12", "10.9", "NORMVARIANTE_UNBEKANNT"),
    ("M8x12", None, "NORMTEIL_GESPERRT"),
])
def test_aufloesen_fehler(groesse, variante, code):
    with pytest.raises(NormteilFehler) as e:
        loese_auf("ISO 9999", groesse, variante, DATEN)
    assert e.value.daten["code"] == code


def test_naechste_normlaengen():
    with pytest.raises(NormteilFehler) as e:
        loese_auf("ISO 9999", "M6x13", ordner=DATEN)
    assert e.value.daten["naechste"] == {"darunter": 12, "darueber": 16}
    assert naechste_laengen([10, 12], 30) == {"darunter": 12, "darueber": None}


def test_spec_aus_vorlage():
    t, a = loese_auf("ISO 9999", "M6x16", "A2", DATEN)
    spec = erzeuge_spec(t, a, vorlage_text(t, DATEN))
    assert spec["name"] == "ISO9999_M6x16_A2"
    assert spec["parameter"] == {"a": 6, "b": 12, "l": 16.0}
    assert spec["material"] == "1.4301"
    assert spec["eigenschaften"] == {"Benennung": "Testring ISO 9999 - M6 x 16 - A2", "Norm": "ISO 9999",
                                     "Groesse": "M6 x 16", "Festigkeitsklasse": "A2"}
    assert spec_befunde(spec, DATEN) == []


def test_feste_zahl_ist_befund():
    t, a = loese_auf("ISO 9999", "M6x16", ordner=DATEN)
    spec = erzeuge_spec(t, a, vorlage_text(t, DATEN))
    spec["features"][0]["skizze"]["elemente"][0]["polygon"]["punkte"][1] = [6, 0]
    assert [b["pfad"] for b in spec_befunde(spec, DATEN)] == ["features[0].skizze.elemente[0].polygon.punkte"]


def test_pruefsummen():
    t, a = loese_auf("ISO 9999", "M6x16", ordner=DATEN)
    text = vorlage_text(t, DATEN)
    summe = teil_pruefsumme(t, a, text)
    assert summe == teil_pruefsumme(t, a, text.replace("\n", "\r\n"))          # Zeilenenden zählen nicht
    assert summe != teil_pruefsumme(t, a, text + "\n# geändert\n")              # Vorlage zählt
    assert summe != teil_pruefsumme(t, Anfrage("ISO 9999", "M6", 12.0, "8.8"), text)
    t["groessen"]["M6"]["masse"]["b"] = 12.5
    assert summe != teil_pruefsumme(t, a, text)                                 # Tabellenwert zählt
    assert vorlage_pruefsumme("a\r\nb") == vorlage_pruefsumme("a\nb")
