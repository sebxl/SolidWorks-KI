"""Normteilbibliothek (Spec 3a §3, §7): <normteilbibliothek>/<sw_jahr>/<schluessel>.sldprt + .json; nicht im Git.
Die Bibliothek ist ein Cache: maßgeblich sind Normtabelle und Bauvorlage."""

import json
import shutil
from pathlib import Path

from swki.konfig import Rechner, swki_home


def bibliotheksordner(r: Rechner) -> Path:
    return (r.normteilbibliothek or swki_home() / "normteile") / str(r.sw_jahr)


def teil_pfad(ordner: Path, schluessel: str) -> Path:
    return ordner / f"{schluessel}.sldprt"


def lies_eintrag(ordner: Path, schluessel: str) -> dict | None:
    pfad = ordner / f"{schluessel}.json"
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.is_file() else None


def ist_aktuell(ordner: Path, schluessel: str, pruefsumme: str) -> bool:
    """Datei vorhanden, Eintrag mit gleicher Prüfsumme und bestandener Selbstprüfung."""
    eintrag = lies_eintrag(ordner, schluessel)
    return (eintrag is not None and eintrag.get("pruefsumme") == pruefsumme and eintrag.get("bestanden") is True
            and teil_pfad(ordner, schluessel).is_file())


def lege_ab(ordner: Path, schluessel: str, quelle: Path, eintrag: dict) -> Path:
    """Geprüftes Teil in die Bibliothek kopieren, danach den Eintrag schreiben (ohne Eintrag gilt eine Datei als veraltet)."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = teil_pfad(ordner, schluessel)
    shutil.copy2(quelle, ziel)
    text = json.dumps(eintrag, indent=2, ensure_ascii=False) + "\n"
    (ordner / f"{schluessel}.json").write_text(text, encoding="utf-8")
    return ziel


def eintraege(ordner: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ordner.glob("*.json"))]
