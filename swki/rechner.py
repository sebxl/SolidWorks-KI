"""Erkennung der lokalen SolidWorks-Installation und Befehle "swki rechner …"."""

import re
from pathlib import Path
from typing import Protocol

from swki.konfig import (
    KonfigFehler, Rechner, lade_rechner, rechner_als_dict, rechner_pfad, schreibe_rechner, swki_home,
)

_BASIS = r"HKLM\SOFTWARE\SolidWorks"
_JAHR_RE = re.compile(r"^SOLIDWORKS (\d{4})$")


class Registry(Protocol):
    def unterschluessel(self, pfad: str) -> list[str]: ...
    def wert(self, pfad: str, name: str) -> str | None: ...


class WinRegistry:
    def _oeffne(self, pfad: str):
        import winreg

        hive_name, _, rest = pfad.partition("\\")
        hive = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}[hive_name]
        return winreg.OpenKey(hive, rest)

    def unterschluessel(self, pfad: str) -> list[str]:
        import winreg

        try:
            with self._oeffne(pfad) as k:
                anzahl = winreg.QueryInfoKey(k)[0]
                return [winreg.EnumKey(k, i) for i in range(anzahl)]
        except OSError:
            return []

    def wert(self, pfad: str, name: str) -> str | None:
        import winreg

        try:
            with self._oeffne(pfad) as k:
                return str(winreg.QueryValueEx(k, name)[0])
        except OSError:
            return None


def sw_jahre(reg: Registry) -> list[int]:
    jahre = [int(m.group(1)) for s in reg.unterschluessel(_BASIS) if (m := _JAHR_RE.match(s))]
    return sorted(jahre)


def _erstes(liste: str | None) -> str | None:
    if not liste:
        return None
    teil = liste.split(";")[0].strip()
    return teil or None


def _suche(ordner: str | None, muster: str) -> Path | None:
    if not ordner or not Path(ordner).is_dir():
        return None
    treffer = sorted(Path(ordner).glob(muster))
    return treffer[0] if treffer else None


def erkenne(reg: Registry, jahr: int | None = None) -> Rechner:
    jahre = sw_jahre(reg)
    if not jahre:
        raise KonfigFehler("Kein SOLIDWORKS in der Registry gefunden (HKLM\\SOFTWARE\\SolidWorks).")
    jahr = jahr or jahre[-1]
    if jahr not in jahre:
        raise KonfigFehler(f"SOLIDWORKS {jahr} nicht installiert. Gefunden: {jahre}")
    basis = f"SOLIDWORKS {jahr}"
    ordner = reg.wert(rf"{_BASIS}\{basis}\Setup", "SolidWorks Folder")
    if not ordner:
        raise KonfigFehler(f"Installationsordner von {basis} nicht gefunden.")
    vorlagen_schl = rf"HKCU\Software\SolidWorks\{basis}\Document Templates"
    ext_schl = rf"HKCU\Software\SolidWorks\{basis}\ExtReferences"
    vorlagen_ordner = _erstes(reg.wert(ext_schl, "Document Template Folders"))
    teil = reg.wert(vorlagen_schl, "Default Part Template")
    baugruppe = reg.wert(vorlagen_schl, "Default Assembly Template")
    teil_pfad = Path(teil) if teil else _suche(vorlagen_ordner, "*.prtdot")
    if teil_pfad is None:
        raise KonfigFehler(f"Keine Teilevorlage für {basis} gefunden.")
    baugruppe_pfad = Path(baugruppe) if baugruppe else _suche(vorlagen_ordner, "*.asmdot")
    mat = _erstes(reg.wert(ext_schl, "Material Database Folders"))
    return Rechner(
        sw_jahr=jahr,
        installationsordner=Path(ordner.rstrip("\\")),
        vorlage_teil=teil_pfad,
        vorlage_baugruppe=baugruppe_pfad,
        materialdatenbank=Path(mat) if mat else None,
        arbeitsordner=swki_home() / "arbeit",
    )


def _init(args) -> dict:
    pfad = rechner_pfad()
    if pfad.exists() and not args.neu:
        return {"unveraendert": True, "pfad": str(pfad), **rechner_als_dict(lade_rechner(pfad))}
    r = erkenne(WinRegistry(), args.jahr)
    schreibe_rechner(r, pfad)
    r.arbeitsordner.mkdir(parents=True, exist_ok=True)
    return {"unveraendert": False, "pfad": str(pfad), **rechner_als_dict(r)}


def _zeigen(args) -> dict:
    return rechner_als_dict(lade_rechner())


def einrichten(subparsers) -> None:
    gruppe = subparsers.add_parser("rechner").add_subparsers(dest="unterbefehl", required=True)
    p = gruppe.add_parser("init")
    p.add_argument("--jahr", type=int)
    p.add_argument("--neu", action="store_true", help="vorhandene rechner.yaml überschreiben")
    p.set_defaults(func=_init)
    gruppe.add_parser("zeigen").set_defaults(func=_zeigen)
