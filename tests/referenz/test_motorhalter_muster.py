"""Muster-Getriebemotor der Referenz Motorhalter (Spec 3c §11): die Specs, aus denen die Test-STEP entsteht, sind gültig."""

from pathlib import Path

import pytest

from swki.baugruppe.befehle import validieren as validieren_baugruppe
from swki.spec.hinweise import hinweise
from swki.spec.laden import lade_spec

MUSTER = Path(__file__).parent / "motorhalter" / "muster"


@pytest.mark.parametrize("datei", ["gehaeuse.yaml", "welle.yaml"])
def test_muster_teile_gueltig_ohne_hinweis(datei):
    assert hinweise(lade_spec(MUSTER / datei)) == []


def test_muster_baugruppe_gueltig():
    v = validieren_baugruppe(MUSTER / "gm42.yaml")
    assert (v["komponenten"], v["verknuepfungen"], v["hinweise"]) == (2, 2, [])
