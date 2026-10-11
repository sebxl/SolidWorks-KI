"""Vorprüfung: der Prüfer-Agent vergleicht die Spezifikation mit der Eingabe des Nutzers, bevor gebaut wird.

Neuer Ablauf für Einzelteile (Spec docs/superpowers/specs/2026-10-10-step-merkmale-design.md):
- Die Frage „hat der Konstrukteur die Eingabe richtig verstanden?“ beantwortet der Prüfer vor dem Bau, nur aus Eingabe
  und Spezifikation (Text) – parallel zum Bau oder während der Nutzer die Freigabe liest.
- Die Frage „ist das gebaute Teil die Spezifikation?“ beantwortet `swki pruefen` im Code (Prüfung `merkmale`: Abgleich
  der STEP mit der freigegebenen Kopie), ohne Screenshots.

Das Urteil liegt in protokolle/<spec>.vorpruefung.json mit der Prüfsumme des Spec-Texts, den der Prüfer gesehen hat.
Es gilt für einen Lauf nur, wenn genau dieser Text freigegeben ist (kopie_sha256 in freigabe.json) und der Prüfbericht
des Laufs die Bildprüfung ersetzt (`merkmale` ok, alles abgebildet). Sonst bleibt der Prüfer nach dem Bau nötig.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from swki.auftrag import protokoll_ordner
from swki.spec.freigabe import freigabe_eintrag

# Abgleich-Lücken, die andere Prüfungen schon abdecken (keine Bildprüfung nötig)
_ANDERSWO = ("(Prüfung formschraegen)", "(Prüfung koerper)")


def vorpruefung_pfad(spec_pfad: Path) -> Path:
    return protokoll_ordner(spec_pfad) / f"{spec_pfad.stem}.vorpruefung.json"


def text_sha256(spec_pfad: Path) -> str:
    return hashlib.sha256(spec_pfad.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def vorpruefung_auftrag(spec_pfad: Path) -> str:
    """Fertiger Prompt für den Prüfer-Agenten (Vorprüfung): nur Eingabe und Spezifikation."""
    ordner = spec_pfad.parent
    return (f"Vorprüfung (vor dem Bau) von {spec_pfad.name}. Eingabe des Nutzers: {ordner / 'eingabe'} (und "
            f"aufgabe.md, falls vorhanden). Spezifikation: {spec_pfad}. Prüfe nach Abschnitt „Vorprüfung“, ob die "
            "Spezifikation die Eingabe vollständig und richtig umsetzt. Antworte nur mit dem JSON-Urteil.")


def lege_ab(spec_pfad: Path, urteil: dict) -> Path:
    ziel = vorpruefung_pfad(spec_pfad)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    daten = {"spec_sha256": text_sha256(spec_pfad), "zeit": datetime.now().isoformat(timespec="seconds"),
             "urteil": urteil}
    ziel.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ziel


def lies(spec_pfad: Path) -> dict | None:
    pfad = vorpruefung_pfad(spec_pfad)
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else None


def offene_maengel(spec_pfad: Path) -> list[dict] | None:
    """Mängel der Vorprüfung, wenn sie genau den aktuellen Spec-Text betrifft und nicht bestanden ist (sonst None)."""
    v = lies(spec_pfad)
    if v is None or v["spec_sha256"] != text_sha256(spec_pfad) or v["urteil"]["bestanden"]:
        return None
    return v["urteil"]["maengel"]


def ersetzt_bildpruefung(bericht: dict | None) -> bool:
    """Der Prüfbericht belegt Lage und Vollständigkeit aller Features im Code (Prüfung `merkmale` ok, ohne Lücken
    außer solchen, die andere Prüfungen abdecken)."""
    e = next((p for p in (bericht or {}).get("pruefungen", []) if p.get("id") == "merkmale"), None)
    return bool(e) and e.get("ok") is True and all(t.endswith(_ANDERSWO) for t in e.get("nicht_geprueft", []))


def urteil_fuer_lauf(spec_pfad: Path, bericht: dict | None) -> dict | None:
    """Das Urteil der Vorprüfung, wenn es für diesen Lauf das Prüfer-Urteil nach dem Bau ersetzt."""
    v = lies(spec_pfad)
    if v is None or not ersetzt_bildpruefung(bericht):
        return None
    eintrag = freigabe_eintrag(spec_pfad)
    if eintrag is None or eintrag.get("kopie_sha256") != v["spec_sha256"]:
        return None
    return v["urteil"]
