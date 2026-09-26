"""Kommandozeile von swki. Jeder Befehl liefert ein dict, das als JSON ausgegeben wird."""

import argparse
import json
import sys

from swki import __version__


class SwkiFehler(Exception):
    """Fachlicher Fehler, der als JSON {"fehler": ...} gemeldet wird."""


def ausgabe(daten: dict) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(daten, ensure_ascii=False, indent=2, default=str))


def _version(args) -> dict:
    return {"version": __version__}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swki")
    sub = parser.add_subparsers(dest="befehl", required=True)
    p = sub.add_parser("version")
    p.set_defaults(func=_version)
    for modul in _befehlsgruppen():
        modul.einrichten(sub)
    return parser


def _befehlsgruppen() -> list:
    """Module mit einer Funktion einrichten(subparsers). Wird in späteren Tasks ergänzt."""
    return []


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 2)
    try:
        ausgabe(args.func(args))
        return 0
    except SwkiFehler as e:
        ausgabe({"fehler": str(e)})
        return 1
