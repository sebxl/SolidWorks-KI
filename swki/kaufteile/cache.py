"""Cache der Kaufteile (Spec 3c §5.3, §7): <kaufteilbibliothek>/<sw_jahr>/<schluessel>.sldprt + .json, nicht im Git.
Maßgeblich sind Katalogeintrag und Original; die Datei ist jederzeit neu erzeugbar. Gültig ist ein Cache-Eintrag nur
mit gleicher Cache-Prüfsumme, bestandener Prüfung und unveränderter .sldprt (SHA-256)."""

import hashlib
import json
import os
import shutil
from pathlib import Path

from swki.aenderungen import sha256_datei
from swki.kaufteile.quelle import bibliothek
from swki.konfig import Rechner
from swki.spec.freigabe import pruefsumme

IMPORTWEG_VERSION = 2  # bei jeder Änderung an Import, Ortung oder Bezugsgeometrie erhöhen (Spec 3c §5.3);
#                        2: Gewinde-Ø-Bereich D1…Kernloch, Gewindemodell mit gemessenem Ø (2026-10-06)


def cacheordner(r: Rechner) -> Path:
    return bibliothek(r) / str(r.sw_jahr)


def cache_pruefsumme(spec: dict) -> str:
    inhalt = {"freigabe": pruefsumme(spec), "original": spec["original"]["sha256"], "importweg": IMPORTWEG_VERSION}
    return hashlib.sha256(json.dumps(inhalt, sort_keys=True).encode("utf-8")).hexdigest()


def teil_pfad(ordner: Path, schluessel: str) -> Path:
    return ordner / f"{schluessel}.sldprt"


def lies(ordner: Path, schluessel: str) -> dict | None:
    pfad = ordner / f"{schluessel}.json"
    if not pfad.is_file():
        return None
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None  # defekter Eintrag gilt als fehlend: neu aufnehmen


def ist_aktuell(ordner: Path, schluessel: str, summe: str) -> bool:
    e = lies(ordner, schluessel)
    teil = teil_pfad(ordner, schluessel)
    return (e is not None and e.get("pruefsumme") == summe and e.get("bestanden") is True and teil.is_file()
            and sha256_datei(teil) == e.get("sldprt_sha256"))


def lege_ab(ordner: Path, schluessel: str, teil: Path, eintrag: dict) -> Path:
    """Geprüftes Teil in den Cache kopieren, dann den Eintrag atomar schreiben (ohne Eintrag gilt die Datei als veraltet)."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = teil_pfad(ordner, schluessel)
    shutil.copy2(teil, ziel)
    daten = {**eintrag, "sldprt_sha256": sha256_datei(ziel)}
    tmp = ordner / f"{schluessel}.json.tmp"
    tmp.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, ordner / f"{schluessel}.json")
    return ziel
