"""Befehle "swki validieren <spec>" und "swki freigeben <spec>"."""

from pathlib import Path

from swki.spec.freigabe import freigeben, pruefsumme
from swki.spec.laden import lade_spec


def _validieren(args) -> dict:
    pfad = Path(args.spec)
    spec = lade_spec(pfad)
    return {
        "gueltig": True,
        "spec": str(pfad),
        "name": spec["name"],
        "features": len(spec["features"]),
        "pruefsumme": pruefsumme(spec),
    }


def _freigeben(args) -> dict:
    pfad = Path(args.spec)
    spec = lade_spec(pfad)
    return {"spec": str(pfad), **freigeben(pfad, spec)}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("validieren", help="Schema und Plausibilität prüfen (ohne SolidWorks)")
    p.add_argument("spec")
    p.set_defaults(func=_validieren)
    p = subparsers.add_parser("freigeben", help="Anforderungen freigeben (schreibt freigabe.json)")
    p.add_argument("spec")
    p.set_defaults(func=_freigeben)
