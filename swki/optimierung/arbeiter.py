"""Arbeitsprozess des Runners: lädt die Prüfaufgabe einmal, die Probe-Datei einmal je Probe, und rechnet Läufe."""

import importlib.util
import json
import sys
import time
from pathlib import Path

_modul = None
_probe: tuple[str, dict] | None = None


def lade_modul(pfad: Path, auftrag: Path | None = None):
    """Prüfaufgabe als Modul `swki_pruefaufgabe`; ihr Ordner und der Auftragsordner kommen in sys.path (eigene
    Hilfsdateien der Prüfaufgabe)."""
    pfad = Path(pfad)
    for ordner in (auftrag, pfad.parent):
        if ordner is not None and str(ordner) not in sys.path:
            sys.path.insert(0, str(ordner))
    spec = importlib.util.spec_from_file_location("swki_pruefaufgabe", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    for name in ("jobs", "lauf"):
        if not callable(getattr(modul, name, None)):
            raise AttributeError(f"{pfad.name}: Prüfaufgabe braucht eine Funktion {name}()")
    return modul


def init(modul_pfad: str, auftrag: str | None = None) -> None:
    global _modul
    _modul = lade_modul(Path(modul_pfad), Path(auftrag) if auftrag else None)


def lauf(arg: tuple[str, dict]) -> dict:
    global _probe
    pfad, job = arg
    if _probe is None or _probe[0] != pfad:
        _probe = (pfad, json.loads(Path(pfad).read_text(encoding="utf-8")))
    t0 = time.perf_counter()
    r = dict(_modul.lauf(_probe[1], job))
    r["_s"] = round(time.perf_counter() - t0, 4)
    return r
