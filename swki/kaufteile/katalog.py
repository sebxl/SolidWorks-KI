"""Katalog der Kaufteile (Spec 3c §3, §4.1): je Kaufteil eine Datei swki/wissen/kaufteile/<hersteller>/<bestellnummer>.yaml
(art: kaufteil) im Git; daneben freigabe.json, <datei>.freigegeben.yaml und <datei>.pruefer.json.
Schlüssel "<Hersteller> <Bestellnummer>" (der Hersteller hat kein Leerzeichen)."""

import json
import re
from pathlib import Path

import yaml

from swki.kaufteile.fehler import KAUFTEIL_UNBEKANNT, KaufteilFehler
from swki.konfig import PROJEKT
from swki.spec.freigabe import pruefsumme

ORDNER = PROJEKT / "swki" / "wissen" / "kaufteile"
_KOPIE = ".freigegeben.yaml"


def _katalog(katalog: Path | None) -> Path:
    return ORDNER if katalog is None else katalog


def ordnername(hersteller: str) -> str:
    """Ordner des Herstellers: Kleinbuchstaben, alle Zeichen außer [a-z0-9-] → "-"."""
    return re.sub(r"[^a-z0-9-]+", "-", hersteller.lower()).strip("-")


def dateiname(bestellnummer: str) -> str:
    """Dateiname des Eintrags ohne Endung: Kleinbuchstaben, alle Zeichen außer [a-z0-9_-] → "_"."""
    return re.sub(r"[^a-z0-9_-]+", "_", bestellnummer.lower()).strip("_")


def schluessel(hersteller: str, bestellnummer: str) -> str:
    return f"{hersteller} {bestellnummer}"


def bibliotheksschluessel(hersteller: str, bestellnummer: str) -> str:
    """Dateiname im Cache und im Lauf-Ordner, z. B. "SWKI-MUSTER_GM42-10"."""
    return re.sub(r"[^A-Za-z0-9-]+", "_", f"{hersteller}_{bestellnummer}").strip("_")


def teile_schluessel(text: str) -> tuple[str, str]:
    """"SWKI-MUSTER GM42-10" → ("SWKI-MUSTER", "GM42-10"): der Hersteller endet am ersten Leerzeichen."""
    hersteller, _, bestellnummer = text.strip().partition(" ")
    return hersteller, bestellnummer.strip()


def eintrag_pfad(hersteller: str, bestellnummer: str, katalog: Path | None = None) -> Path:
    return _katalog(katalog) / ordnername(hersteller) / f"{dateiname(bestellnummer)}.yaml"


def eintraege(katalog: Path | None = None) -> list[Path]:
    """Alle Eintragsdateien (ohne Freigabe-Kopien), sortiert."""
    return sorted(p for p in _katalog(katalog).glob("*/*.yaml") if not p.name.endswith(_KOPIE))


def _kopf(pfad: Path) -> tuple[str, str] | None:
    """(hersteller, bestellnummer) einer Eintragsdatei ohne Prüfung; None, wenn sie nicht lesbar ist."""
    try:
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(daten, dict):
        return None
    return str(daten.get("hersteller")), str(daten.get("bestellnummer"))


def vorhandene(katalog: Path | None = None) -> list[str]:
    """Schlüssel aller lesbaren Einträge."""
    return [schluessel(*k) for p in eintraege(katalog) if (k := _kopf(p)) is not None]


def finde(text: str, katalog: Path | None = None) -> Path:
    """Pfad des Eintrags zum Schlüssel; KAUFTEIL_UNBEKANNT mit den vorhandenen Schlüsseln."""
    hersteller, bestellnummer = teile_schluessel(text)
    pfad = eintrag_pfad(hersteller, bestellnummer, katalog) if bestellnummer else None
    if pfad is not None and pfad.is_file() and _kopf(pfad) == (hersteller, bestellnummer):
        return pfad
    alle = vorhandene(katalog)
    gleich = [s for s in alle if teile_schluessel(s)[0] == hersteller]
    raise KaufteilFehler(KAUFTEIL_UNBEKANNT,
                         f"Kaufteil {text!r} unbekannt; vorhanden: {', '.join(gleich or alle) or 'keine'}",
                         vorhanden=gleich or alle)


def urteil_pfad(pfad: Path) -> Path:
    """Prüfer-Urteil neben dem Eintrag: <datei>.pruefer.json."""
    return pfad.with_name(f"{pfad.stem}.pruefer.json")


def geprueft(pfad: Path, spec: dict) -> bool:
    """Bestandenes Prüfer-Urteil zur aktuellen Freigabe-Prüfsumme des Eintrags vorhanden?"""
    datei = urteil_pfad(pfad)
    if not datei.is_file():
        return False
    u = json.loads(datei.read_text(encoding="utf-8"))
    return u.get("freigabe_pruefsumme") == pruefsumme(spec) and u.get("bestanden") is True
