"""Aufträge: Ordner, Läufe und Dateinamen.

Ein Auftrag ist der Ordner, in dem die Spezifikation liegt (auftraege/<name>/ oder tests/referenz/<name>/).
Erzeugte Dateien landen je Lauf unter <arbeitsordner>/<auftrag>/lauf-<n>/.
"""

import re
from pathlib import Path

from swki.konfig import Rechner

_LAUF_RE = re.compile(r"^lauf-(\d+)$")


def auftrag_name(spec_pfad: Path) -> str:
    return spec_pfad.resolve().parent.name


def auftrag_ordner(r: Rechner, auftrag: str) -> Path:
    return r.arbeitsordner / auftrag


def laeufe(r: Rechner, auftrag: str) -> list[int]:
    ordner = auftrag_ordner(r, auftrag)
    if not ordner.is_dir():
        return []
    return sorted(int(m.group(1)) for p in ordner.iterdir() if p.is_dir() and (m := _LAUF_RE.match(p.name)))


def naechster_lauf(r: Rechner, auftrag: str, spec_pfad: Path | None = None) -> int:
    """Höchste belegte Laufnummer + 1. Belegt ist ein Lauf mit Arbeitsordner oder – wenn spec_pfad gegeben ist – mit
    irgendeiner Lauf-Datei (Protokoll, Prüfbericht, Prüfer-Urteil) im Auftragsordner; sonst würde ein aufgeräumter
    Arbeitsordner alte Prüfdateien zu einem frisch gebauten Lauf stehen lassen."""
    bisher = laeufe(r, auftrag)
    if spec_pfad is not None:
        bisher = bisher + lauf_nummern_dateien(spec_pfad)
    return max(bisher) + 1 if bisher else 1


def lauf_ordner(r: Rechner, auftrag: str, lauf: int) -> Path:
    return auftrag_ordner(r, auftrag) / f"lauf-{lauf}"


def dateiname(spec: dict, auftrag: str, standard: dict) -> str:
    return standard["namensschema"]["datei"].format(auftrag=auftrag, name=spec["name"])


def protokoll_ordner(spec_pfad: Path) -> Path:
    return spec_pfad.parent / "protokolle"


def lauf_datei(spec_pfad: Path, lauf: int, art: str) -> Path:
    """protokolle/<spec>.lauf-<n>.<art>.json im Auftragsordner (art: protokoll | pruefbericht | pruefer)."""
    return protokoll_ordner(spec_pfad) / f"{spec_pfad.stem}.lauf-{lauf}.{art}.json"


def lauf_nummern_dateien(spec_pfad: Path) -> list[int]:
    """Laufnummern, zu denen im Protokollordner irgendeine Datei dieser Spezifikation liegt."""
    muster = re.compile(rf"^{re.escape(spec_pfad.stem)}\.lauf-(\d+)\.(?:protokoll|pruefbericht|pruefer)\.json$")
    ordner = protokoll_ordner(spec_pfad)
    if not ordner.is_dir():
        return []
    return sorted({int(m.group(1)) for p in ordner.iterdir() if (m := muster.match(p.name))})


def lauf_belegt(r: Rechner, auftrag: str, spec_pfad: Path, lauf: int) -> bool:
    """Gibt es zu diesem Lauf schon einen Arbeitsordner oder eine Lauf-Datei (Protokoll, Prüfbericht, Prüfer-Urteil)
    im Auftragsordner?"""
    return lauf_ordner(r, auftrag, lauf).exists() or lauf in lauf_nummern_dateien(spec_pfad)
