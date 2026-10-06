"""Originale der Kaufteile (Spec 3c §5.1, §7): unveränderte Kopien im Quellordner
<kaufteilbibliothek>/quellen/<hersteller>/. Dateien des Nutzers werden nur gelesen; im Quellordner wird nie etwas
überschrieben (eine neue Herstellerversion bekommt einen eigenen Namen)."""

import shutil
from pathlib import Path

from swki.aenderungen import sha256_datei
from swki.kaufteile.fehler import KAUFTEIL_FORMAT, KAUFTEIL_QUELLE_ABWEICHEND, KAUFTEIL_QUELLE_FEHLT, KaufteilFehler
from swki.kaufteile.katalog import dateiname, ordnername
from swki.konfig import Rechner, swki_home

ENDUNGEN = (".step", ".stp")


def bibliothek(r: Rechner) -> Path:
    return r.kaufteilbibliothek or swki_home() / "kaufteile"


def quellordner(r: Rechner, hersteller: str) -> Path:
    return bibliothek(r) / "quellen" / ordnername(hersteller)


def pruefe_format(pfad: Path) -> None:
    if pfad.suffix.lower() not in ENDUNGEN:
        raise KaufteilFehler(KAUFTEIL_FORMAT, f"{pfad.name}: nur STEP ({', '.join(ENDUNGEN)}) – andere Formate beim "
                                              "Hersteller als STEP holen", erlaubt=list(ENDUNGEN))


def _kopiere(quelle: Path, ziel: Path, sha: str) -> bool:
    """Kopie anlegen, wenn sie fehlt; liegt dort schon eine Datei, muss sie gleich sein (nie überschreiben)."""
    if ziel.exists():
        vorhanden = sha256_datei(ziel)
        if vorhanden != sha:
            raise KaufteilFehler(KAUFTEIL_QUELLE_ABWEICHEND, f"{ziel.name} liegt schon im Quellordner mit anderem "
                                                             "Inhalt", pfad=str(ziel), vorhanden=vorhanden, neu=sha)
        return False
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(quelle, ziel)
    return True


def uebernimm(r: Rechner, quelle: Path, hersteller: str, bestellnummer: str, eintrag: dict | None = None,
              neue_version: bool = False) -> dict:
    """Original in den Quellordner kopieren. Mit vorhandenem Katalogeintrag muss die Datei dessen SHA-256 haben (so
    stellt ein anderer Rechner das Original wieder her); --neue-version legt sie als <datei>.<sha8>.<endung> ab."""
    pruefe_format(quelle)
    if not quelle.is_file():
        raise KaufteilFehler(KAUFTEIL_QUELLE_FEHLT, f"{quelle} fehlt", pfad=str(quelle))
    sha = sha256_datei(quelle)
    ordner = quellordner(r, hersteller)
    endung = quelle.suffix.lower()
    if neue_version:
        ziel = ordner / f"{dateiname(bestellnummer)}.{sha[:8]}{endung}"
    elif eintrag is not None:
        if sha != eintrag["original"]["sha256"]:
            raise KaufteilFehler(KAUFTEIL_QUELLE_ABWEICHEND,
                                 f"{quelle.name} weicht vom Katalogeintrag ab – neue Herstellerversion? Nutzer fragen; "
                                 "dann swki kaufteil untersuchen … --neue-version",
                                 eintrag=eintrag["original"]["sha256"], neu=sha)
        ziel = ordner / eintrag["original"]["datei"]
    else:
        ziel = ordner / f"{dateiname(bestellnummer)}{endung}"
    kopiert = False if quelle.resolve() == ziel.resolve() else _kopiere(quelle, ziel, sha)
    return {"datei": ziel.name, "pfad": str(ziel), "sha256": sha, "kopiert": kopiert}


def uebernimm_datenblatt(r: Rechner, quelle: Path, hersteller: str) -> dict:
    if not quelle.is_file():
        raise KaufteilFehler(KAUFTEIL_QUELLE_FEHLT, f"{quelle} fehlt", pfad=str(quelle))
    ziel = quellordner(r, hersteller) / quelle.name
    sha = sha256_datei(quelle)
    kopiert = False if quelle.resolve() == ziel.resolve() else _kopiere(quelle, ziel, sha)
    return {"datei": ziel.name, "pfad": str(ziel), "sha256": sha, "kopiert": kopiert}


def original(r: Rechner, spec: dict) -> Path:
    """Original eines Eintrags im Quellordner; fehlt es oder weicht es ab, Fehler mit Code."""
    pfad = quellordner(r, spec["hersteller"]) / spec["original"]["datei"]
    if not pfad.is_file():
        raise KaufteilFehler(KAUFTEIL_QUELLE_FEHLT, f"{pfad} fehlt – Nutzer gibt die Datei erneut: swki kaufteil "
                                                    "untersuchen <step> --hersteller … --bestellnummer …", pfad=str(pfad))
    if (sha := sha256_datei(pfad)) != spec["original"]["sha256"]:
        raise KaufteilFehler(KAUFTEIL_QUELLE_ABWEICHEND, f"{pfad.name} im Quellordner weicht vom Eintrag ab",
                             pfad=str(pfad), eintrag=spec["original"]["sha256"], vorhanden=sha)
    return pfad
