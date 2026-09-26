"""Baut den API-Index aus der lokalen SolidWorks-Installation; Befehle "swki api …"."""

from pathlib import Path

from swki.api.chm import CHM_DATEIEN, entpacke, lese_ordner
from swki.api.codepruefung import pruefe
from swki.api.index import baue, enum, meta, methode, seit_je_member, suche
from swki.api.typbib import lese_typbibliothek
from swki.cli import SwkiFehler
from swki.konfig import PROJEKT, Rechner, lade_rechner, lade_standard, swki_home

TYPBIBLIOTHEKEN = ["sldworks.tlb", "swconst.tlb"]


def api_db(jahr: int) -> Path:
    return swki_home() / "api" / str(jahr) / "api.sqlite"


def baue_index(r: Rechner, ziel: Path | None = None, neu: bool = False) -> dict:
    ziel = ziel or api_db(r.sw_jahr)
    seiten, fehlend = [], []
    for name in CHM_DATEIEN:
        chm = r.installationsordner / "api" / name
        if not chm.exists():
            fehlend.append(name)
            continue
        seiten.extend(lese_ordner(entpacke(chm, ziel.parent / "html" / chm.stem, neu)))
    members, enums = [], []
    for name in TYPBIBLIOTHEKEN:
        m, e = lese_typbibliothek(r.installationsordner / name)
        members += m
        enums += e
    statistik = baue(ziel, members, enums, seiten, r.sw_jahr)
    return {"db": str(ziel), "fehlende_chm": fehlend, **statistik}


def _db(args) -> Path:
    pfad = Path(args.db) if args.db else api_db(lade_rechner().sw_jahr)
    if not pfad.exists():
        raise SwkiFehler(f"API-Index {pfad} fehlt. Zuerst ausführen: python -m swki api bauen")
    return pfad


def _bauen(args) -> dict:
    return baue_index(lade_rechner(), Path(args.db) if args.db else None, args.neu)


def _suche(args) -> dict:
    return {"treffer": suche(_db(args), args.text, args.limit)}


def _methode(args) -> dict:
    treffer = methode(_db(args), args.name)
    if not treffer:
        raise SwkiFehler(f"{args.name} nicht im Index. Mit 'swki api suche' nach dem richtigen Namen suchen.")
    return {"treffer": treffer}


def _enum(args) -> dict:
    werte = enum(_db(args), args.name)
    if not werte:
        raise SwkiFehler(f"Enum {args.name} nicht im Index.")
    return {"enum": args.name, "werte": werte}


def _pruefe_code(args) -> dict:
    max_jahr = lade_standard()["api"]["max_jahr_compiler"]
    pfade = [Path(p) for p in args.pfade] or [PROJEKT / "swki"]
    befunde = pruefe(pfade, seit_je_member(_db(args)), max_jahr)
    if befunde:
        raise _Befunde(max_jahr, befunde)
    return {"max_jahr": max_jahr, "befunde": []}


class _Befunde(SwkiFehler):
    def __init__(self, max_jahr, befunde):
        super().__init__(f"{len(befunde)} API-Aufruf(e) jünger als SW {max_jahr}")
        self.daten = {"max_jahr": max_jahr, "befunde": befunde}


def _info(args) -> dict:
    return meta(_db(args))


def einrichten(subparsers) -> None:
    gruppe = subparsers.add_parser("api").add_subparsers(dest="unterbefehl", required=True)

    def neu(name, func):
        p = gruppe.add_parser(name)
        p.add_argument("--db")
        p.set_defaults(func=func)
        return p

    neu("bauen", _bauen).add_argument("--neu", action="store_true")
    p = neu("suche", _suche)
    p.add_argument("text")
    p.add_argument("--limit", type=int, default=10)
    neu("methode", _methode).add_argument("name", help="Interface.Member, z. B. IFeatureManager.FeatureExtrusion3")
    neu("enum", _enum).add_argument("name")
    neu("pruefe-code", _pruefe_code).add_argument("pfade", nargs="*")
    neu("info", _info)
