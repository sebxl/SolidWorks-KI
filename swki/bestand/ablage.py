"""Ablage der Bestandsdateien: <arbeitsordner>/<auftrag>/bestand-<n>/ enthält die schreibgeschützte Kopie des Originals
und die Aufnahme (bestand.json). Das Original wird nur gelesen. Ein Auftrag nimmt genau eine Datei auf; ändert sich
ihr Inhalt, entsteht eine neue Aufnahme (nie überschreiben)."""

import json
import os
import re
import shutil
import stat
from pathlib import Path

from swki.aenderungen import sha256_datei
from swki.bestand.fehler import (BESTAND_ABWEICHEND, BESTAND_ANDERE_DATEI, BESTAND_FORMAT, BESTAND_NICHT_LESBAR,
                                 BESTAND_UNBEKANNT, BestandFehler)
from swki.konfig import Rechner

ENDUNG = ".sldprt"
AUFNAHME_DATEI = "bestand.json"
_ORDNER = re.compile(r"^bestand-(\d+)$")


def bestand_ordner(r: Rechner, auftrag: str, nummer: int) -> Path:
    return r.arbeitsordner / auftrag / f"bestand-{nummer}"


def aufnahmen(r: Rechner, auftrag: str) -> list[int]:
    """Nummern der vorhandenen Aufnahmen des Auftrags, aufsteigend."""
    wurzel = r.arbeitsordner / auftrag
    if not wurzel.is_dir():
        return []
    return sorted(int(m.group(1)) for p in wurzel.iterdir() if p.is_dir() and (m := _ORDNER.match(p.name)))


def pruefe_format(pfad: Path) -> None:
    if pfad.suffix.lower() != ENDUNG:
        raise BestandFehler(BESTAND_FORMAT, f"{pfad.name}: nur Teile ({ENDUNG}) – Baugruppen und andere Formate sind "
                                            "hier nicht möglich", erlaubt=[ENDUNG])


def _kopie_in(ordner: Path) -> Path | None:
    """Die Bestandskopie einer Aufnahme (die einzige .sldprt im Ordner selbst)."""
    treffer = sorted(p for p in ordner.iterdir() if p.is_file() and p.suffix.lower() == ENDUNG) if ordner.is_dir() else []
    return treffer[0] if treffer else None


def kopiere_original(r: Rechner, auftrag: str, original: Path) -> dict:
    """Original lesen und als schreibgeschützte Kopie in bestand-<n>/ ablegen. Gleiche Datei (gleicher Name ohne
    Beachtung der Groß-/Kleinschreibung, gleiche SHA-256 wie die jüngste Aufnahme) → keine neue Aufnahme."""
    pruefe_format(original)
    try:
        sha = sha256_datei(original)
    except OSError as e:
        raise BestandFehler(BESTAND_NICHT_LESBAR, f"{original} lässt sich nicht lesen ({e.strerror or e}) – fehlt die "
                                                  "Datei, ist das Laufwerk nicht da oder hat sie ein Kollege offen?",
                            pfad=str(original)) from e
    nummern = aufnahmen(r, auftrag)
    if nummern:
        jung = nummern[-1]
        kopie = _kopie_in(bestand_ordner(r, auftrag, jung))
        if kopie is not None:
            if kopie.name.lower() != original.name.lower():
                raise BestandFehler(BESTAND_ANDERE_DATEI,
                                    f"Der Auftrag {auftrag} hat schon {kopie.name} aufgenommen – ein Auftrag nimmt "
                                    f"genau eine Datei auf, für {original.name} einen neuen Auftrag anlegen",
                                    vorhanden=kopie.name, neu=original.name)
            if sha256_datei(kopie) == sha:
                return {"nummer": jung, "pfad": kopie, "sha256": sha, "neu": False}
    nummer = (nummern[-1] if nummern else 0) + 1
    ziel = bestand_ordner(r, auftrag, nummer) / original.name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, ziel)
    os.chmod(ziel, stat.S_IREAD)
    return {"nummer": nummer, "pfad": ziel, "sha256": sha, "neu": True}


def lade_aufnahme(r: Rechner, auftrag: str, nummer: int) -> dict:
    pfad = bestand_ordner(r, auftrag, nummer) / AUFNAHME_DATEI
    if not pfad.is_file():
        raise BestandFehler(BESTAND_UNBEKANNT, f"Keine Aufnahme {nummer} im Auftrag {auftrag} – zuerst "
                                               "swki bestand aufnehmen", auftrag=auftrag, nummer=nummer)
    return json.loads(pfad.read_text(encoding="utf-8"))


def schreibe_aufnahme(r: Rechner, auftrag: str, nummer: int, daten: dict) -> Path:
    pfad = bestand_ordner(r, auftrag, nummer) / AUFNAHME_DATEI
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
    return pfad


def lauf_kopie(quelle: Path, ordner: Path) -> Path:
    """Arbeitskopie für einen Lauf: Kopie der (schreibgeschützten) Bestandskopie, beschreibbar."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / quelle.name
    shutil.copy2(quelle, ziel)
    os.chmod(ziel, stat.S_IREAD | stat.S_IWRITE)
    return ziel


def pruefe_kopie(aufnahme: dict, pfad: Path) -> None:
    """Die Bestandskopie muss noch die aufgenommene sein (SHA-256 aus `aufnahme["datei"]["sha256"]`)."""
    soll = aufnahme["datei"]["sha256"]
    ist = sha256_datei(pfad)
    if ist != soll:
        raise BestandFehler(BESTAND_ABWEICHEND, f"{pfad.name} weicht von der Aufnahme ab – jemand hat die "
                                                "Bestandskopie geändert", pfad=str(pfad), aufnahme=soll, vorhanden=ist)
