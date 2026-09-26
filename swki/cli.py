"""Kommandozeile von swki. Jeder Befehl liefert ein dict, das als JSON ausgegeben wird."""

import argparse
import json
import sys

from swki import __version__


class SwkiFehler(Exception):
    """Fachlicher Fehler, der als JSON {"fehler": ...} gemeldet wird."""


class SwkiArgumentParser(argparse.ArgumentParser):
    """ArgumentParser, das Fehler als SwkiFehler wirft statt zu beenden."""

    def error(self, message):
        raise SwkiFehler(message)


def ausgabe(daten: dict) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(daten, ensure_ascii=False, indent=2, default=str))


def _version(args) -> dict:
    return {"version": __version__}


def _parser() -> SwkiArgumentParser:
    parser = SwkiArgumentParser(prog="swki")
    sub = parser.add_subparsers(dest="befehl", required=True)
    p = sub.add_parser("version")
    p.set_defaults(func=_version)
    for modul in _befehlsgruppen():
        modul.einrichten(sub)
    return parser


def _befehlsgruppen() -> list:
    from swki import rechner
    from swki.api import bauen

    return [rechner, bauen]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        ausgabe(args.func(args))
        return 0
    except SystemExit as e:
        if e.code is None or e.code == 0:
            return 0
        return int(e.code)
    except SwkiFehler as e:
        ausgabe({"fehler": str(e), **getattr(e, "daten", {})})
        return 1
