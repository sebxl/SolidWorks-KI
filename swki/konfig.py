"""Projekt- und Rechnerkonfiguration."""

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from swki.cli import SwkiFehler

PROJEKT = Path(__file__).resolve().parent.parent


class KonfigFehler(SwkiFehler):
    pass


@dataclass(frozen=True)
class Rechner:
    sw_jahr: int
    installationsordner: Path
    vorlage_teil: Path
    vorlage_baugruppe: Path | None
    materialdatenbank: Path | None
    arbeitsordner: Path
    normteilbibliothek: Path | None = None
    kaufteilbibliothek: Path | None = None
    blender: Path | None = None  # blender.exe für Blender-Skripte in Aufträgen (optional)
    dateien: dict[str, Path] = field(default_factory=dict)  # benannte Eingabedateien für Auftragsskripte (optional)


_PFADFELDER = ("installationsordner", "vorlage_teil", "vorlage_baugruppe", "materialdatenbank", "arbeitsordner",
               "normteilbibliothek", "kaufteilbibliothek", "blender")


def swki_home() -> Path:
    return Path(os.environ.get("SWKI_HOME", Path.home() / ".swki"))


def rechner_pfad() -> Path:
    return PROJEKT / "config" / "rechner.yaml"


def lade_standard(pfad: Path | None = None) -> dict:
    pfad = pfad or PROJEKT / "config" / "standard.yaml"
    with open(pfad, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rechner_als_dict(r: Rechner) -> dict:
    d = asdict(r)
    for feld in _PFADFELDER:
        d[feld] = str(d[feld]) if d[feld] is not None else None
    d["dateien"] = {k: str(v) for k, v in d["dateien"].items()}
    return d


def schreibe_rechner(r: Rechner, pfad: Path | None = None) -> None:
    pfad = pfad or rechner_pfad()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("# Rechnerspezifisch – nicht ins Git. Erzeugt von: swki rechner init\n")
        d = rechner_als_dict(r)
        if not d["dateien"]:
            del d["dateien"]
        yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False)


def lade_rechner(pfad: Path | None = None) -> Rechner:
    pfad = pfad or rechner_pfad()
    if not pfad.exists():
        raise KonfigFehler(f"{pfad} fehlt. Zuerst ausführen: python -m swki rechner init")
    with open(pfad, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    for feld in _PFADFELDER:
        d[feld] = Path(d[feld]) if d.get(feld) else None
    d["dateien"] = {k: Path(v) for k, v in (d.get("dateien") or {}).items()}
    return Rechner(**d)
