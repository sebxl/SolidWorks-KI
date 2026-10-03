"""Freigabe einer Spezifikation: Prüfsumme über die Anforderungen, gespeichert in freigabe.json.

Die Prüfsumme deckt nur die Anforderungen ab (Parameter, Material, Eigenschaften, Prüfwerte),
nicht den Bauweg (Features, Anker, Reihenfolge) – den darf Claude beim Nachbessern ändern.
Zusätzlich wird die ganze Spezifikation als <spec>.freigegeben.yaml abgelegt: Sie ist das Soll für den
Prüfer-Agenten und für das analytische Sollvolumen, auch wenn der Bauweg später nachgebessert wird.
Baugruppen: zusätzlich die Prüfsummen der Teil-Specs (Spec 3b §6).
Die Kopie ist der Rohtext der Spezifikationsdatei (Kommentare bleiben erhalten); nur wenn die Datei
fehlt oder inhaltlich nicht mehr zum übergebenen spec passt, dient yaml.safe_dump als Rückfall.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import yaml

from swki.cli import SwkiFehler

PRUEF_FELDER = ("art", "name", "parameter", "material", "eigenschaften", "pruefung")
PRUEF_FELDER_BAUGRUPPE = ("art", "name", "parameter", "eigenschaften", "komponenten", "freiheitsgrade", "pruefung")


class FreigabeFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str):
        super().__init__(meldung)
        self.daten = {"code": code}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pruefsumme(spec: dict, teile: dict[str, str] | None = None) -> str:
    """Prüfsumme der Anforderungen; bei Baugruppen zusätzlich über die Prüfsummen der Teil-Specs (Dateiname → Summe)."""
    felder = PRUEF_FELDER_BAUGRUPPE if spec.get("art") == "baugruppe" else PRUEF_FELDER
    kern = {feld: spec.get(feld) for feld in felder}
    if teile is not None:
        kern["teile"] = teile
    text = json.dumps(kern, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _sha256(text)


def freigabe_pfad(spec_pfad: Path) -> Path:
    return spec_pfad.parent / "freigabe.json"


def kopie_pfad(spec_pfad: Path) -> Path:
    return spec_pfad.with_name(f"{spec_pfad.stem}.freigegeben.yaml")


def _lies(pfad: Path) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}


def _rohtext_oder_dump(spec_pfad: Path, spec: dict) -> str:
    """Rohtext der Spezifikationsdatei, wenn er inhaltlich zu spec passt – sonst yaml.safe_dump als Rückfall."""
    if spec_pfad.exists():
        text = spec_pfad.read_text(encoding="utf-8")
        if yaml.safe_load(text) == spec:
            return text
    return yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)


def freigeben(spec_pfad: Path, spec: dict, zeitpunkt: str | None = None, teile: dict[str, str] | None = None) -> dict:
    pfad = freigabe_pfad(spec_pfad)
    daten = _lies(pfad)
    kopie = _rohtext_oder_dump(spec_pfad, spec)
    kopie_pfad(spec_pfad).write_text(kopie, encoding="utf-8")
    eintrag = {
        "pruefsumme": pruefsumme(spec, teile),
        "freigegeben": zeitpunkt or datetime.now().isoformat(timespec="seconds"),
        "kopie_sha256": _sha256(kopie),
    }
    daten[spec_pfad.name] = eintrag
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return eintrag


def pruefe_freigabe(spec_pfad: Path, spec: dict, teile: dict[str, str] | None = None) -> dict:
    """Wirft FreigabeFehler, wenn die Spezifikation nicht (mehr) freigegeben ist."""
    eintrag = _lies(freigabe_pfad(spec_pfad)).get(spec_pfad.name)
    if eintrag is None:
        raise FreigabeFehler("FREIGABE_FEHLT", f"{spec_pfad.name} ist nicht freigegeben. Zuerst: swki freigeben")
    if eintrag["pruefsumme"] != pruefsumme(spec, teile):
        raise FreigabeFehler(
            "FREIGABE_VERALTET",
            f"Anforderungen in {spec_pfad.name} wurden nach der Freigabe geändert. Nutzer fragen und neu freigeben.",
        )
    kopie = kopie_pfad(spec_pfad)
    if not kopie.exists():
        raise FreigabeFehler("FREIGABE_FEHLT", f"{kopie.name} fehlt. Nutzer fragen und neu freigeben.")
    if _sha256(kopie.read_text(encoding="utf-8")) != eintrag.get("kopie_sha256"):
        raise FreigabeFehler(
            "FREIGABE_VERALTET", f"{kopie.name} wurde nach der Freigabe geändert. Nutzer fragen und neu freigeben.",
        )
    return eintrag


def freigegebene_spec(spec_pfad: Path) -> dict:
    """Die Spezifikation im Stand der Freigabe (Soll für Prüfer und Sollvolumen)."""
    return yaml.safe_load(kopie_pfad(spec_pfad).read_text(encoding="utf-8"))
