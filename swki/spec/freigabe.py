"""Freigabe einer Spezifikation: Prüfsumme über die Anforderungen, gespeichert in freigabe.json.

Die Prüfsumme deckt nur die Anforderungen ab (Parameter, Material, Eigenschaften, Prüfwerte),
nicht den Bauweg (Features, Anker, Reihenfolge) – den darf Claude beim Nachbessern ändern.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from swki.cli import SwkiFehler

PRUEF_FELDER = ("art", "name", "parameter", "material", "eigenschaften", "pruefung")


class FreigabeFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str):
        super().__init__(meldung)
        self.daten = {"code": code}


def pruefsumme(spec: dict) -> str:
    kern = {feld: spec.get(feld) for feld in PRUEF_FELDER}
    text = json.dumps(kern, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def freigabe_pfad(spec_pfad: Path) -> Path:
    return spec_pfad.parent / "freigabe.json"


def _lies(pfad: Path) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}


def freigeben(spec_pfad: Path, spec: dict, zeitpunkt: str | None = None) -> dict:
    pfad = freigabe_pfad(spec_pfad)
    daten = _lies(pfad)
    eintrag = {
        "pruefsumme": pruefsumme(spec),
        "freigegeben": zeitpunkt or datetime.now().isoformat(timespec="seconds"),
    }
    daten[spec_pfad.name] = eintrag
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return eintrag


def pruefe_freigabe(spec_pfad: Path, spec: dict) -> dict:
    """Wirft FreigabeFehler, wenn die Spezifikation nicht (mehr) freigegeben ist."""
    eintrag = _lies(freigabe_pfad(spec_pfad)).get(spec_pfad.name)
    if eintrag is None:
        raise FreigabeFehler("FREIGABE_FEHLT", f"{spec_pfad.name} ist nicht freigegeben. Zuerst: swki freigeben")
    if eintrag["pruefsumme"] != pruefsumme(spec):
        raise FreigabeFehler(
            "FREIGABE_VERALTET",
            f"Anforderungen in {spec_pfad.name} wurden nach der Freigabe geändert. Nutzer fragen und neu freigeben.",
        )
    return eintrag
