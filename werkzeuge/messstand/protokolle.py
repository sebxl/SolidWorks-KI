"""Fehler-KPI aus den Protokollen eines Messstand-Auftrags (auftraege/<auftrag>/protokolle/) und das Ergebnis des
letzten bestandenen Laufs im Arbeitsordner."""

import json
import re
from pathlib import Path

_DATEI = re.compile(r"^(?P<spec>.+)\.lauf-(?P<n>\d+)\.(?P<art>protokoll|pruefbericht|pruefer)\.json$")


def _lies(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def dateien(auftrag: Path) -> list[tuple[str, int, str, Path]]:
    """(spec, lauf, art, pfad) aller Protokolldateien, nach Lauf sortiert."""
    ordner = Path(auftrag) / "protokolle"
    liste = []
    for p in ordner.glob("*.json") if ordner.is_dir() else []:
        m = _DATEI.match(p.name)
        if m:
            liste.append((m["spec"], int(m["n"]), m["art"], p))
    return sorted(liste, key=lambda x: (x[1], x[2]))


def auswerten(auftrag: Path) -> dict:
    laeufe = abbrueche = pruefmaengel = pruefer_urteile = pruefer_maengel = 0
    letzter_pruefer: tuple[int, bool] | None = None
    for spec, n, art, p in dateien(auftrag):
        d = _lies(p)
        if d is None:
            continue
        if art == "protokoll":
            laeufe += 1
            if d.get("status") != "ok":
                abbrueche += 1
        elif art == "pruefbericht":
            pruefmaengel += sum(1 for x in d.get("pruefungen", []) if x.get("ok") is False)
        else:
            pruefer_urteile += 1
            if not d.get("bestanden"):
                pruefer_maengel += max(1, len(d.get("maengel") or []))
            if letzter_pruefer is None or n >= letzter_pruefer[0]:
                letzter_pruefer = (n, bool(d.get("bestanden")))
    return {"laeufe": laeufe, "bauabbrueche": abbrueche, "pruefmaengel": pruefmaengel,
            "pruefer_urteile": pruefer_urteile, "pruefer_maengel": pruefer_maengel,
            "letzter_lauf": letzter_pruefer[0] if letzter_pruefer else None,
            "pruefer_bestanden": bool(letzter_pruefer and letzter_pruefer[1])}


def ergebnisdatei(lauf_ordner: Path) -> Path | None:
    """Baugruppe (.sldasm) vor Teil (.sldprt) im Laufordner; bei mehreren Teilen ohne Baugruppe keins."""
    lauf_ordner = Path(lauf_ordner)
    if not lauf_ordner.is_dir():
        return None
    asm = sorted(lauf_ordner.glob("*.SLDASM")) + sorted(lauf_ordner.glob("*.sldasm"))
    if asm:
        return asm[0]
    prt = sorted({p.resolve() for p in [*lauf_ordner.glob("*.SLDPRT"), *lauf_ordner.glob("*.sldprt")]})
    return prt[0] if len(prt) == 1 else None
