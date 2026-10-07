"""Gültiger Katalogeintrag für Tests (Muster-Getriebemotor wie die Referenz Motorhalter, Spec 3c §11; selbst
formuliert). STEP-Koordinaten: Flanschfläche y = 0 (Normale −y), Zentrierbund y −3…0, Welle Ø 10 bis y = −25, Gehäuse
bis y = 82; 4 × M5 auf Lochkreis Ø 60."""

import copy
from pathlib import Path

import yaml

from swki.kaufteile.katalog import eintrag_pfad

SHA = "0123456789abcdef" * 4
L = 21.2132  # Lochkreis Ø 60 / √8

EINTRAG = {
    "art": "kaufteil", "hersteller": "SWKI-MUSTER", "bestellnummer": "GM42-10",
    "benennung": "Getriebemotor GM42, i = 10 (Muster)",
    "original": {"datei": "gm42-10.step", "sha256": SHA, "bezug": {"art": "nutzer", "datum": "2026-10-07"}},
    "datenblatt": {"datei": "datenblatt.md"},
    "koerper": 2, "material": "1.0038", "masse": {"kg": 1.2, "beleg": ["d1"]},
    "eigenschaften": {"Benennung": "Getriebemotor GM42-10"},
    "belege": {"d1": {"art": "datenblatt", "datei": "datenblatt.md", "seite": 1}},
    "einbau": {
        "EINBAU_ACHSE": {"zylinder": {"nahe": [5, -15, 0], "durchmesser": 10, "senkrecht_zu": "EINBAU_FLANSCH"}},
        "EINBAU_FLANSCH": {"ebene": {"nahe": [25, 0, 25], "normale": [0, -1, 0]}},
        "EINBAU_DREHLAGE": {"ebene_durch_achse": {"achse": "EINBAU_ACHSE", "nahe": [0, 0, 25]}},
    },
    "gewinde": {"flansch": {"groesse": "M5", "gewindetiefe": 8, "tiefe": 10, "normale": [0, -1, 0], "beleg": ["d1"],
                            "positionen": [[L, 0, L], [-L, 0, L], [-L, 0, -L], [L, 0, -L]]}},
    "pruefung": {
        "huellquader": {"soll": [60, 107, 60], "tol": 0.1, "beleg": ["d1"]},
        "volumen": {"soll": 220000.0, "toleranz_prozent": 0.01},
        "durchmesser_pruefen": [
            {"was": "Wellen-Ø", "nahe": [5, -15, 0], "soll": 10, "referenz": "EINBAU_ACHSE", "beleg": ["d1"]},
            {"was": "Zentrierbund-Ø", "nahe": [20, -1.5, 0], "soll": 40, "referenz": "EINBAU_ACHSE", "beleg": ["d1"]},
        ],
        "masse_pruefen": [
            {"was": "Wellenüberstand", "von": {"referenz": "EINBAU_FLANSCH"},
             "zu": {"flaeche": {"nahe": [0, -25, 0], "normale": [0, -1, 0]}}, "soll": 25, "tol": 0.05, "beleg": ["d1"]},
            {"was": "Lochabstand", "von": {"gewinde": "flansch", "instanz": 1}, "zu": {"gewinde": "flansch", "instanz": 2},
             "soll": 42.4264, "tol": 0.05, "beleg": ["d1"]},
        ],
    },
}


def kopie(spec: dict | None = None) -> dict:
    return copy.deepcopy(spec or EINTRAG)


def schreibe(katalog: Path, spec: dict | None = None) -> Path:
    """Schreibt den Eintrag an seinen Platz im Katalog und liefert den Pfad."""
    spec = spec or EINTRAG
    pfad = eintrag_pfad(spec["hersteller"], spec["bestellnummer"], katalog)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad
