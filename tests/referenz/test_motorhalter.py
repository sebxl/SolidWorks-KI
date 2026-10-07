"""Referenz Motorhalter (Spec 3c §11, Plan-Nachtrag GPLE60) ohne SolidWorks: gültig mit dem freigegebenen und
geprüften Katalogeintrag Nanotec GPLE60-2S-32 aus dem Repo, ohne Hinweis; 9 Komponenten, 18 Verknüpfungen."""

from pathlib import Path

from swki.baugruppe.befehle import validieren

MOTORHALTER = Path(__file__).parent / "motorhalter" / "motorhalter.yaml"


def test_motorhalter_gueltig_ohne_hinweis():
    v = validieren(MOTORHALTER)
    assert (v["komponenten"], v["verknuepfungen"], v["hinweise"]) == (9, 18, [])
