"""Regelkatalog der Zeichnungsprüfung (Design 2026-11-16 §8.1): swki/wissen/zeichnungsregeln.yaml als Daten."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from swki.konfig import PROJEKT

TABELLE = PROJEKT / "swki" / "wissen" / "zeichnungsregeln.yaml"


@dataclass(frozen=True)
class Regel:
    id: str
    pruefung: str
    text: str
    quelle: str
    beleg: str  # A | B | C
    art: str  # hart | hinweis


def lade_regeln(pfad: Path | None = None) -> list[Regel]:
    daten = yaml.safe_load((pfad or TABELLE).read_text(encoding="utf-8"))
    return [Regel(**eintrag) for eintrag in daten]


def regel(regeln: list[Regel], id_: str) -> Regel:
    for r in regeln:
        if r.id == id_:
            return r
    raise KeyError(f"Zeichnungsregel {id_!r} nicht im Katalog")
