"""Referenz Linearschlitten (Spec 4a): Spezifikation gültig und ohne Hinweise, Bewegungen aufgelöst."""

from pathlib import Path

from swki.baugruppe.befehle import validieren
from swki.baugruppe.bewegung import bewegungen
from swki.baugruppe.laden import lade_baugruppe
from swki.konfig import lade_standard

REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "schlitten" / "linearschlitten.yaml"


def test_referenz_schlitten_gueltig_ohne_hinweise():
    ergebnis = validieren(REFERENZ)
    assert ergebnis["gueltig"] and ergebnis["hinweise"] == [], ergebnis["hinweise"]
    assert (ergebnis["komponenten"], ergebnis["verknuepfungen"]) == (10, 22)


def test_referenz_schlitten_bewegungen():
    bws = bewegungen(lade_baugruppe(REFERENZ).spec, lade_standard())
    assert [(b.name, b.art, b.komponente, b.min, b.max, b.schritte) for b in bws] == [
        ("Schlittenhub", "abstand", "schlitten", 0.0, 220.0, 8), ("Hebelschwenk", "winkel", "hebel", 0.0, 90.0, 8)]
