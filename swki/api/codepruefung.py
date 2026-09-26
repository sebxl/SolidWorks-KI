"""Findet SolidWorks-API-Aufrufe im Code, die erst nach max_jahr verfügbar sind."""

import ast
from pathlib import Path


def finde_api_namen(quelltext: str) -> list[tuple[str, int]]:
    return [
        (knoten.attr, knoten.lineno)
        for knoten in ast.walk(ast.parse(quelltext))
        if isinstance(knoten, ast.Attribute) and knoten.attr[:1].isupper()
    ]


def _dateien(pfade: list[Path]) -> list[Path]:
    ergebnis = []
    for p in pfade:
        ergebnis.extend(sorted(p.rglob("*.py")) if p.is_dir() else [p])
    return ergebnis


def pruefe(pfade: list[Path], seit: dict[str, int], max_jahr: int) -> list[dict]:
    befunde = []
    for datei in _dateien(pfade):
        for name, zeile in finde_api_namen(datei.read_text(encoding="utf-8")):
            jahr = seit.get(name)
            if jahr is not None and jahr > max_jahr:
                befunde.append({"datei": str(datei), "zeile": zeile, "name": name, "seit": jahr})
    return sorted(befunde, key=lambda b: (b["datei"], b["zeile"]))
