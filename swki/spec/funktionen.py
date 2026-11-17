"""Funktionsangaben an Features (Zeichnungsableitung, Design 2026-11-16 §4.1–4.3).

Ein Feature trägt `funktion: <schlüssel>` aus swki/wissen/funktionen.yaml und/oder eigene Werte (passung, toleranz,
rauheit, form_lage, huelle, bearbeitung, behandlung). aufloesen() liefert die geltenden Werte: eigene Werte gehen vor
Tabellenwerte; eine eigene toleranz ersetzt die Passung der Tabelle. `unbestaetigt` nennt die Werte, die aus einem noch
nicht bestätigten Tabelleneintrag stammen (validieren meldet sie, Hinweis art "funktion").
"""

from functools import cache
from pathlib import Path

import yaml

from swki.cli import SwkiFehler
from swki.konfig import PROJEKT

TABELLE = PROJEKT / "swki" / "wissen" / "funktionen.yaml"
ANFORDERUNG_FELDER = ("funktion", "passung", "toleranz", "rauheit", "form_lage", "huelle", "bearbeitung", "behandlung")
_WERTE = ("passung", "toleranz", "rauheit", "form_lage", "huelle", "bearbeitung", "behandlung")
_BELEGTE = ("passung", "rauheit", "form_lage")  # Werte mit Beleg in der Tabelle (huelle ist Nutzerentscheid)


class FunktionFehler(SwkiFehler):
    def __init__(self, meldung: str):
        super().__init__(meldung)
        self.daten = {"code": "FUNKTION_UNBEKANNT"}


@cache
def _lade(pfad: Path) -> dict[str, dict]:
    return yaml.safe_load(pfad.read_text(encoding="utf-8"))


def lade_funktionen(pfad: Path = TABELLE) -> dict[str, dict]:
    """Regeltabelle (gecacht, nicht verändern)."""
    return _lade(pfad)


def aufloesen(feature: dict, tabelle: dict | None = None) -> dict:
    """Geltende Anforderungen eines Features: {passung, toleranz, rauheit, form_lage, huelle, bearbeitung, behandlung,
    unbestaetigt}. Wirft FunktionFehler (FUNKTION_UNBEKANNT), wenn die Funktion nicht in der Tabelle steht."""
    tabelle = lade_funktionen() if tabelle is None else tabelle
    name = feature.get("funktion")
    if name is not None and name not in tabelle:
        raise FunktionFehler(f"Funktion {name!r} steht nicht in funktionen.yaml (Feature {feature.get('id')!r})")
    eintrag = tabelle.get(name, {}) if name is not None else {}
    ergebnis, aus_tabelle = {}, []
    for feld in _WERTE:
        if feld in feature:
            ergebnis[feld] = feature[feld]
        elif feld == "passung" and "toleranz" in feature:
            ergebnis[feld] = None  # eigene Toleranz ersetzt die Tabellenpassung
        else:
            ergebnis[feld] = eintrag.get(feld)
            if ergebnis[feld] is not None:
                aus_tabelle.append(feld)
    ergebnis["huelle"] = bool(ergebnis["huelle"])
    unbestaetigt = [] if eintrag.get("bestaetigt", True) else [f for f in _BELEGTE if f in aus_tabelle]
    return {**ergebnis, "unbestaetigt": unbestaetigt}


def anforderung_befunde(spec: dict) -> list[dict]:
    """Befunde zu den Anforderungsfeldern (blockieren validieren): unbekannte Funktion, Hülle ohne Passung/Toleranz,
    Passung und Toleranz zugleich, Bezugsbuchstabe ohne `bezuege`, `toleranzen` ohne Parameter, örtliche Behandlung
    ohne Eintrag im Top-Level `behandlung`."""
    befunde = []
    tabelle = lade_funktionen()
    bezuege = set(spec.get("bezuege", {}))
    arten = {b.get(k) for b in spec.get("behandlung", []) for k in ("art", "id")} - {None}  # Verweis über art oder id
    for i, f in enumerate(spec.get("features", [])):
        pfad = f"features[{i}]"
        if "funktion" in f and f["funktion"] not in tabelle:
            befunde.append({"pfad": f"{pfad}.funktion",
                            "meldung": f"Funktion {f['funktion']!r} unbekannt (swki/wissen/funktionen.yaml: "
                                       f"{', '.join(sorted(tabelle))})"})
        elif any(feld in f for feld in ANFORDERUNG_FELDER):
            a = aufloesen(f, tabelle)
            if "passung" in f and "toleranz" in f:
                befunde.append({"pfad": f"{pfad}.toleranz", "meldung": "passung und toleranz zugleich – eines davon"})
            elif a["huelle"] and a["passung"] is None and a["toleranz"] is None:
                befunde.append({"pfad": f"{pfad}.huelle",
                                "meldung": "Hülle Ⓔ nur an Passmaßen (ISO 8015, Nutzer 16.11.2026): passung oder "
                                           "toleranz fehlt"})
        for j, fl in enumerate(f.get("form_lage", [])):
            fehlend = [b for b in fl.get("bezug", []) if b not in bezuege]
            if fehlend:
                befunde.append({"pfad": f"{pfad}.form_lage[{j}].bezug",
                                "meldung": f"Bezug {', '.join(fehlend)} fehlt in bezuege"})
        if "behandlung" in f and f["behandlung"] not in arten:
            befunde.append({"pfad": f"{pfad}.behandlung",
                            "meldung": f"Behandlung {f['behandlung']!r} steht nicht im Top-Level behandlung "
                                       "(art oder id)"})
    ids = {f.get("id") for f in spec.get("features", [])}
    for name, anker in spec.get("bezuege", {}).items():
        if anker.get("feature") not in ids:
            befunde.append({"pfad": f"bezuege.{name}.feature",
                            "meldung": f"Bezug {name}: Feature {anker.get('feature')!r} gibt es nicht"})
    parameter = spec.get("parameter", {})
    for name in spec.get("toleranzen", {}):
        if name not in parameter:
            befunde.append({"pfad": f"toleranzen.{name}", "meldung": f"Parameter {name!r} gibt es nicht"})
    return befunde
