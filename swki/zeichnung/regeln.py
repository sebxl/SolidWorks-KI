"""Regelkatalog der Zeichnungsprüfung (Design 2026-11-16 §8.1): swki/wissen/zeichnungsregeln.yaml als Daten."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from swki.konfig import PROJEKT

TABELLE = PROJEKT / "swki" / "wissen" / "zeichnungsregeln.yaml"
PRUEFUNGEN = (
    "vollstaendig", "ueberbestimmt", "toleranzen", "sammelangaben", "schriftfeld", "ansichten", "lesbarkeit",
    "gewinde", "drehteil",
)


@dataclass(frozen=True)
class Regel:
    id: str
    pruefung: str
    text: str
    quelle: str
    beleg: str  # A | B | C: nur die Norm- und Praxisstütze
    art: str  # hart | hinweis
    herkunft: str  # norm | projekt (Entscheidung des Nutzers oder des Designs)

    def __post_init__(self):
        def fehler(grund: str):
            raise ValueError(f"Zeichnungsregel {self.id}: {grund}")

        if self.pruefung not in PRUEFUNGEN:
            fehler(f"pruefung {self.pruefung!r} unbekannt")
        if self.beleg not in ("A", "B", "C"):
            fehler(f"beleg {self.beleg!r} ungültig")
        if self.art not in ("hart", "hinweis"):
            fehler(f"art {self.art!r} ungültig")
        if self.herkunft not in ("norm", "projekt"):
            fehler(f"herkunft {self.herkunft!r} ungültig")
        if not self.text.strip() or not self.quelle.strip():
            fehler("text und quelle dürfen nicht leer sein")
        if self.herkunft == "projekt" and "Nutzer" not in self.quelle and "Design" not in self.quelle:
            fehler("Projektregel nennt in quelle weder Nutzer noch Design")
        if self.art == "hart" and self.beleg == "C" and self.herkunft != "projekt":
            fehler("harte Regel mit beleg C nur als Projektregel")


def lade_regeln(pfad: Path | None = None) -> list[Regel]:
    pfad = pfad or TABELLE
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    if not daten:
        raise ValueError(f"Regelkatalog {pfad} ist leer")
    return [Regel(**eintrag) for eintrag in daten]


def regel(regeln: list[Regel], id_: str) -> Regel:
    for r in regeln:
        if r.id == id_:
            return r
    raise KeyError(f"Zeichnungsregel {id_!r} nicht im Katalog")
