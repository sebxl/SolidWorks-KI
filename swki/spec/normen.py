"""Maßtabelle der Normbohrungen (swki/wissen/bohrungsnormen.yaml, Spike S10) und Zuordnung zum Bohrungsassistenten.

Enum-Werte laut `swki api enum` (Spec 2c §3.2); der Handler normbohrung und die Prüfung normbohrungen nutzen dieselben
Konstanten.
"""

from functools import cache
from pathlib import Path

import yaml

from swki.konfig import PROJEKT, lade_standard

TABELLE = PROJEKT / "swki" / "wissen" / "bohrungsnormen.yaml"
ARTEN = ("gewinde", "zylinderschraube", "senkschraube", "stift")
SW_ART = {"zylinderschraube": 0, "senkschraube": 1, "stift": 2, "gewinde": 4}  # swWzdGeneralHoleTypes_e
SW_NORM = {"ISO": 8}  # swWzdHoleStandards_e.swStandardISO
SW_BEFESTIGUNG = {  # swWzdHoleStandardFastenerTypes_e (Abhängig von S10 Frage 1)
    "zylinderschraube": 139,  # swStandardISOSocketHeadCap
    "senkschraube": 140,  # swStandardISOSocketCTSKFlatHead
    "stift": 710,  # swStandardISODowelHole
    "gewinde": 147,  # swStandardISOTappedHole
}
SW_END_BLIND = 0  # swEndConditions_e.swEndCondBlind
SW_END_DURCH_ALLES = 1  # swEndConditions_e.swEndCondThroughAll
SW_FM_HOLE_WZD = 25  # swFeatureNameID_e.swFmHoleWzd (IFeatureManager.CreateDefinition; Stift durch, Spike S10 Frage 1)
SW_BEFESTIGUNG_STIFT_DURCH = -1  # FastenerType2 eines über CreateDefinition gebauten Stiftlochs mit durch (S10 Frage 4)
SW_LOCH_DURCH = 25  # swWzdHoleTypes_e.swHoleThru: Type dieses Stiftlochs


def groesse_text(groesse) -> str:
    """Größe aus der Spezifikation als Tabellenschlüssel: "M8", "M10x1"; Stift-Nenndurchmesser 8 → "8"."""
    if isinstance(groesse, (int, float)) and not isinstance(groesse, bool):
        return f"{groesse:g}"
    return str(groesse)


@cache
def lade_tabelle(pfad: Path = TABELLE) -> dict:
    """Maßtabelle; Größen-Schlüssel immer als Text (YAML liest 8 sonst als Zahl). Nicht verändern (gecacht)."""
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    daten["normen"] = {
        norm: {art: {groesse_text(g): m for g, m in groessen.items()} for art, groessen in arten.items()}
        for norm, arten in daten["normen"].items()
    }
    return daten


def norm_von(f: dict, standard: dict | None = None) -> str:
    """Norm einer Bohrung: eigene Angabe, sonst bohrungsnorm aus config/standard.yaml, sonst ISO."""
    return f.get("norm") or (standard if standard is not None else lade_standard()).get("bohrungsnorm", "ISO")


def verfuegbare_groessen(art: str, norm: str = "ISO") -> list[str]:
    return list(lade_tabelle()["normen"].get(norm, {}).get(art, {}))


def normmasse(art: str, groesse, norm: str = "ISO") -> dict | None:
    """Maße (mm) einer Normbohrung laut Tabelle oder None, wenn Norm, Art oder Größe fehlen."""
    return lade_tabelle()["normen"].get(norm, {}).get(art, {}).get(groesse_text(groesse))


def bohrspitze_grad() -> float:
    return float(lade_tabelle()["bohrspitze_grad"])
