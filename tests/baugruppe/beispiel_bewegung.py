"""Kleine gültige Baugruppe mit Bewegungen für Tests (Stufe 4a, selbst formuliert): Grundplatte (fixiert), Schieber auf
der Platte, bündig an deren Seite −z und über eine Abstandsgrenze in x verschiebbar, Drehbolzen ISO 8734 8 × 30 im
Schieber, Hebel auf dem Schieber über ein Scharnier um den Bolzen und eine Winkelgrenze schwenkbar.

Lage in Grundstellung (mm): Platte x −100…100, y 0…20, z −30…30; Schieber x −100…−40, y 20…40, z −30…10; Bolzen in
x = −60, z = −10, y 20…50; Hebel y 40…48, entlang +x von der Bohrung (x −67…−17). Hub 0…HUB, Schwenk 0…SCHWENK."""

import copy
from pathlib import Path

import yaml


def _block(name: str, laenge: float, breite: float, hoehe: float, weitere: list) -> dict:
    return {
        "art": "teil", "name": name, "material": "1.0038", "eigenschaften": {"Benennung": name},
        "parameter": {"L": laenge, "B": breite, "H": hoehe},
        "features": [
            {"id": "f1", "typ": "extrusion",
             "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
             "ende": {"typ": "blind", "tiefe": "=H"}},
            *weitere,
        ],
        "pruefung": {"huellquader": ["=L", "=H", "=B"]},
    }


GRUNDPLATTE = _block("Grundplatte", 200, 60, 20, [])
SCHIEBER = _block("Schieber", 60, 40, 20, [
    {"id": "f2", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[10, 0]], "durch": True},
])
HEBEL = _block("Hebel", 50, 12, 8, [
    {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[-18, 0]],
     "durchmesser": 8.5, "durch": True},
])
BAUGRUPPE = {
    "art": "baugruppe", "name": "Bewegungsprobe", "eigenschaften": {"Benennung": "Bewegungsprobe"},
    "parameter": {"HUB": 100, "SCHWENK": 90},
    "komponenten": [
        {"id": "platte", "quelle": {"teil": "grundplatte.yaml"}, "fixiert": True},
        {"id": "schieber", "quelle": {"teil": "schieber.yaml"}},
        {"id": "bolzen", "quelle": {"normteil": "ISO 8734 8x30"}},
        {"id": "hebel", "quelle": {"teil": "hebel.yaml"}},
    ],
    "verknuepfungen": [
        {"id": "v1", "typ": "deckungsgleich", "a": {"komponente": "schieber", "feature": "f1", "flaeche": "-y"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v2", "typ": "deckungsgleich", "a": {"komponente": "schieber", "feature": "f1", "flaeche": "-z"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "-z"}, "ausrichtung": "gleich"},
        {"id": "g1", "typ": "grenze_abstand", "a": {"komponente": "schieber", "feature": "f1", "flaeche": "-x"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "-x"}, "ausrichtung": "gleich",
         "min": 0, "max": "=HUB"},
        {"id": "v3", "typ": "deckungsgleich", "a": {"komponente": "bolzen", "referenz": "EINBAU_EBENE_1"},
         "b": {"komponente": "schieber", "feature": "f1", "flaeche": "-y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v4", "typ": "konzentrisch", "a": {"komponente": "bolzen", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "schieber", "feature": "f2", "instanz": 1, "achse": True}},
        {"id": "s1", "typ": "scharnier", "a": {"komponente": "hebel", "feature": "f2", "instanz": 1, "achse": True},
         "b": {"komponente": "bolzen", "referenz": "EINBAU_ACHSE"},
         "anlage_a": {"komponente": "hebel", "feature": "f1", "flaeche": "-y"},
         "anlage_b": {"komponente": "schieber", "feature": "f1", "flaeche": "+y"}},
        {"id": "g2", "typ": "grenze_winkel", "a": {"komponente": "hebel", "feature": "f1", "flaeche": "+z"},
         "b": {"komponente": "schieber", "feature": "f1", "flaeche": "+z"}, "ausrichtung": "gleich",
         "min": 0, "max": "=SCHWENK"},
    ],
    "freiheitsgrade": {"schieber": 1, "hebel": 1},
    "bewegungen": [
        {"name": "Hub", "grenze": "g1", "schritte": 4, "erwartet": {"endlagen": [
            {"komponente": "schieber", "verschiebung": ["=HUB", 0, 0]},
            {"komponente": "hebel", "verschiebung": ["=HUB", 0, 0]},
        ]}},
        {"name": "Schwenk", "grenze": "g2", "schritte": 4, "erwartet": {"endlagen": [
            {"komponente": "hebel", "drehung": {"achse": [0, -1, 0], "winkel": "=SCHWENK"}},
        ]}},
    ],
}


def kopie(spec: dict) -> dict:
    return copy.deepcopy(spec)


def schreibe(ordner: Path, baugruppe: dict | None = None, grundplatte: dict | None = None, schieber: dict | None = None,
             hebel: dict | None = None) -> Path:
    """Schreibt die drei Teil-Specs und bewegungsprobe.yaml nach ordner; liefert den Pfad der Baugruppen-Spec."""
    ordner.mkdir(parents=True, exist_ok=True)
    for name, spec in (("grundplatte.yaml", grundplatte or GRUNDPLATTE), ("schieber.yaml", schieber or SCHIEBER),
                       ("hebel.yaml", hebel or HEBEL), ("bewegungsprobe.yaml", baugruppe or BAUGRUPPE)):
        (ordner / name).write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ordner / "bewegungsprobe.yaml"
