"""Kleine Baugruppe mit Kaufteil für Tests (selbst formuliert): Halter (fixiert) mit Zentrierbohrung Ø 40 und
4 Senkungen M5, Muster-Getriebemotor aus dem Katalog (tests/kaufteile/beispiel.py), 4 × ISO 4762 M5 x 12 je Senkung.
Der Katalog liegt in einem Testordner; katalog() schreibt den Eintrag, gibt ihn frei und legt ein Prüfer-Urteil ab."""

import copy
import json
from pathlib import Path

import yaml

from swki.kaufteile import katalog as kat
from swki.kaufteile.eintrag import freigeben
from swki.spec.freigabe import pruefsumme
from tests.kaufteile.beispiel import EINTRAG, schreibe as schreibe_eintrag

L = 21.2132
HALTER = {
    "art": "teil", "name": "Halter", "material": "1.0038", "eigenschaften": {"Benennung": "Halter"},
    "parameter": {"B": 80, "H": 10, "Z": 40, "LK": 60},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=B", "hoehe": "=B"}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}},
        {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 0]],
         "durchmesser": "=Z", "durch": True},
        {"id": "f3", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M5",
         "flaeche": {"feature": "f1", "flaeche": "-y"},
         "positionen": [["=LK/8**0.5", "=LK/8**0.5"], ["=-LK/8**0.5", "=LK/8**0.5"], ["=-LK/8**0.5", "=-LK/8**0.5"],
                        ["=LK/8**0.5", "=-LK/8**0.5"]], "durch": True},
    ],
}
BAUGRUPPE = {
    "art": "baugruppe", "name": "Motorprobe", "eigenschaften": {"Benennung": "Motorprobe"},
    "komponenten": [
        {"id": "halter", "quelle": {"teil": "halter.yaml"}, "fixiert": True},
        {"id": "motor", "quelle": {"kaufteil": "SWKI-MUSTER GM42-10"}},
        {"id": "schraube", "quelle": {"normteil": "ISO 4762 M5x12"}, "je_position": {"komponente": "halter", "feature": "f3"}},
    ],
    "verknuepfungen": [
        {"id": "v1", "typ": "deckungsgleich", "a": {"komponente": "motor", "referenz": "EINBAU_FLANSCH"},
         "b": {"komponente": "halter", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v2", "typ": "konzentrisch", "a": {"komponente": "motor", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "halter", "feature": "f2", "instanz": 1, "achse": True}, "drehung_sperren": False},
        {"id": "v3", "typ": "parallel", "a": {"komponente": "motor", "referenz": "EINBAU_DREHLAGE"},
         "b": {"komponente": "halter", "ebene": "vorne"}, "ausrichtung": "gleich"},
        {"id": "v4", "typ": "deckungsgleich", "a": {"komponente": "schraube", "referenz": "EINBAU_EBENE"},
         "b": {"komponente": "halter", "feature": "f3", "instanz": "je", "flaeche": "-y"}, "ausrichtung": "gleich"},
        {"id": "v5", "typ": "konzentrisch", "a": {"komponente": "schraube", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "halter", "feature": "f3", "instanz": "je", "achse": True}},
    ],
}


def kopie(spec: dict | None = None) -> dict:
    return copy.deepcopy(spec or BAUGRUPPE)


def katalog(ordner: Path, monkeypatch, eintrag: dict | None = None, geprueft: bool = True) -> Path:
    """Eintrag schreiben und freigeben, bestandenes Urteil ablegen, Katalog umbiegen; liefert den Eintragspfad."""
    pfad = schreibe_eintrag(ordner, eintrag or EINTRAG)
    freigeben(pfad)
    if geprueft:
        urteil = {"freigabe_pruefsumme": pruefsumme(eintrag or EINTRAG), "bestanden": True, "maengel": []}
        kat.urteil_pfad(pfad).write_text(json.dumps(urteil), encoding="utf-8")
    monkeypatch.setattr(kat, "ORDNER", ordner)
    return pfad


def schreibe(ordner: Path, baugruppe: dict | None = None) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    for name, spec in (("halter.yaml", HALTER), ("motorprobe.yaml", baugruppe or BAUGRUPPE)):
        (ordner / name).write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ordner / "motorprobe.yaml"
