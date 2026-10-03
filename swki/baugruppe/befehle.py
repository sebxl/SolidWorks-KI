"""Baugruppen-Zweige der Befehle validieren und freigeben (Weiche in swki.spec.befehle)."""

from pathlib import Path

from swki.baugruppe.aufloesen import instanzen, verknuepfungen
from swki.baugruppe.hinweise import hinweise_baugruppe
from swki.baugruppe.laden import lade_baugruppe


def validieren(pfad: Path) -> dict:
    bg = lade_baugruppe(pfad)
    return {
        "gueltig": True, "spec": str(pfad), "art": "baugruppe", "name": bg.spec["name"],
        "komponenten": len(instanzen(bg.spec, bg.quellen)),
        "verknuepfungen": len(verknuepfungen(bg.spec, bg.quellen)),
        "hinweise": hinweise_baugruppe(bg),
    }
