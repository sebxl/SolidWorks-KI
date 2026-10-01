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


def naechster_lauf(r: Rechner, auftrag: str) -> int:
    bisher = laeufe(r, auftrag)
    return bisher[-1] + 1 if bisher else 1


def lauf_ordner(r: Rechner, auftrag: str, lauf: int) -> Path:
    return auftrag_ordner(r, auftrag) / f"lauf-{lauf}"


def dateiname(spec: dict, auftrag: str, standard: dict) -> str:
    return standard["namensschema"]["datei"].format(auftrag=auftrag, name=spec["name"])


def protokoll_ordner(spec_pfad: Path) -> Path:
    return spec_pfad.parent / "protokolle"


def lauf_datei(spec_pfad: Path, lauf: int, art: str) -> Path:
    """protokolle/<spec>.lauf-<n>.<art>.json im Auftragsordner (art: protokoll | pruefbericht | pruefer)."""
    return protokoll_ordner(spec_pfad) / f"{spec_pfad.stem}.lauf-{lauf}.{art}.json"


def lauf_belegt(r: Rechner, auftrag: str, spec_pfad: Path, lauf: int) -> bool:
    """Gibt es zu diesem Lauf schon einen Arbeitsordner oder ein Protokoll im Auftragsordner?"""
    return lauf_ordner(r, auftrag, lauf).exists() or lauf_datei(spec_pfad, lauf, "protokoll").exists()
