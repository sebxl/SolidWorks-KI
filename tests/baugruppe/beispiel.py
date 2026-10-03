"""Kleine gültige Baugruppe für Tests (selbst formuliert): Platte mit Gewinde, Stiftloch und Durchgangsbohrung, Deckel
mit Zylinderschrauben-Senkung, zwei Schrauben ISO 4762 M8 x 16 je Senkung, ein Stift ISO 8734 8 x 16.

Lage: Platte y 0…20 (fixiert), Deckel y 20…35, Senkungsgrund y = 35 − 8,6 = 26,4, Schraubenende y = 10,4,
Einschraublänge im Gewinde 9,6 mm (Gewindetiefe 12)."""

import copy
from pathlib import Path

import yaml


def _block(name: str, hoehe: float, weitere: list) -> dict:
    return {
        "art": "teil", "name": name, "material": "1.0038", "eigenschaften": {"Benennung": name},
        "parameter": {"L": 100, "B": 60, "H": hoehe, "A": 60},
        "features": [
            {"id": "f1", "typ": "extrusion",
             "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
             "ende": {"typ": "blind", "tiefe": "=H"}},
            *weitere,
        ],
        "pruefung": {"huellquader": ["=L", "=H", "=B"]},
    }


PLATTE = _block("Platte", 20, [
    {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [["=-A/2", 0], ["=A/2", 0]], "tiefe": 16, "gewindetiefe": 12},
    {"id": "f3", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[0, 15]], "durch": True},
    {"id": "f4", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, -15]],
     "durchmesser": 11, "durch": True},
    {"id": "OBEN", "typ": "referenz", "ebene": {"basis": "oben", "abstand": "=H"}},
])
DECKEL = _block("Deckel", 15, [
    {"id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8",
     "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [["=-A/2", 0], ["=A/2", 0]], "durch": True},
])
BAUGRUPPE = {
    "art": "baugruppe", "name": "Probe", "eigenschaften": {"Benennung": "Probe"}, "parameter": {"ABST": 35},
    "komponenten": [
        {"id": "platte", "quelle": {"teil": "platte.yaml"}, "fixiert": True},
        {"id": "deckel", "quelle": {"teil": "deckel.yaml"}},
        {"id": "schraube", "quelle": {"normteil": "ISO 4762 M8x16"}, "je_position": {"komponente": "deckel", "feature": "f2"}},
        {"id": "stift", "quelle": {"normteil": "ISO 8734 8x16"}},
    ],
    "verknuepfungen": [
        {"id": "v1", "typ": "deckungsgleich", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "-y"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v2", "typ": "konzentrisch", "a": {"komponente": "deckel", "feature": "f2", "instanz": 1, "achse": True},
         "b": {"komponente": "platte", "feature": "f2", "instanz": 1, "achse": True}},
        {"id": "v3", "typ": "parallel", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "+x"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+x"}, "ausrichtung": "gleich"},
        {"id": "v4", "typ": "deckungsgleich", "a": {"komponente": "schraube", "referenz": "EINBAU_EBENE"},
         "b": {"komponente": "deckel", "feature": "f2", "instanz": "je", "flaeche": "+y"}, "ausrichtung": "gleich"},
        {"id": "v5", "typ": "konzentrisch", "a": {"komponente": "schraube", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "deckel", "feature": "f2", "instanz": "je", "achse": True}},
        {"id": "v6", "typ": "deckungsgleich", "a": {"komponente": "stift", "referenz": "EINBAU_EBENE_1"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "-y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v7", "typ": "konzentrisch", "a": {"komponente": "stift", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "platte", "feature": "f3", "instanz": 1, "achse": True}},
    ],
    "pruefung": {"masse_pruefen": [
        {"was": "Gesamthöhe", "von": {"komponente": "platte", "feature": "f1", "flaeche": "-y"},
         "zu": {"komponente": "deckel", "feature": "f1", "flaeche": "+y"}, "soll": "=ABST"},
    ]},
}


def kopie(spec: dict) -> dict:
    return copy.deepcopy(spec)


def schreibe(ordner: Path, baugruppe: dict | None = None, platte: dict | None = None, deckel: dict | None = None) -> Path:
    """Schreibt platte.yaml, deckel.yaml und probe.yaml nach ordner; liefert den Pfad der Baugruppen-Spec."""
    ordner.mkdir(parents=True, exist_ok=True)
    for name, spec in (("platte.yaml", platte or PLATTE), ("deckel.yaml", deckel or DECKEL),
                       ("probe.yaml", baugruppe or BAUGRUPPE)):
        (ordner / name).write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ordner / "probe.yaml"
