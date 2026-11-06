"""Muster-Getriebemotor der Referenz Motorhalter (Spec 3c §11): die Specs, aus denen die Test-STEP entsteht, sind gültig."""

from pathlib import Path

import pytest

from swki.baugruppe.befehle import validieren as validieren_baugruppe
from swki.spec.hinweise import hinweise
from swki.spec.laden import lade_spec

MUSTER = Path(__file__).parent / "motorhalter" / "muster"


@pytest.mark.parametrize("datei", ["gehaeuse.yaml", "welle.yaml"])
def test_muster_teile_gueltig_ohne_hinweis(datei):
    assert [h for h in hinweise(lade_spec(MUSTER / datei)) if h["art"] not in ("bezug", "fertigung")] == []  # Referenz eingefroren, alter Stil


def test_muster_baugruppe_gueltig():
    v = validieren_baugruppe(MUSTER / "gm42.yaml")
    hinweise = [h for h in v["hinweise"] if h["art"] not in ("bezug", "fertigung")]  # Referenz eingefroren, alter Stil
    assert (v["komponenten"], v["verknuepfungen"], hinweise) == (2, 2, [])
