"""Änderungs-Spec `art: aenderung` (Spec Bestandsdateien §4): Laden, Prüfsumme, validieren, freigeben.

`lade_aenderung` prüft ohne SolidWorks und ohne Aufnahme: Schema und Plausibilität der Spec selbst. Die Prüfung gegen die
Bestandsaufnahme (`bestand.json`, Spec §4.4 Punkt 2 bis 6) kommt dazu, sobald sie da ist (`befunde_gegen_aufnahme`).

Grundsatz der Prüfsumme (Spec §4.5): Was geändert wird und wo sich die Geometrie ändern darf, ist Anforderung; wie swki es
erreicht, ist Bauweg. `bauweg_frei` liefert die Anforderung.
"""

import copy
from pathlib import Path

from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck
from swki.spec.freigabe import freigeben as spec_freigeben
from swki.spec.freigabe import kopie_pfad, pruefsumme
from swki.spec.laden import SpecFehler, _pfad, _werte, lade_yaml, schema_befunde

PRUEF_FELDER = ("art", "name", "bestand", "parameter", "bereiche", "pruefung")
# Bauweg in den Punkten: Anker und Bezug neuer Features, Einfügestelle, Skriptdatei (Reihenfolge: nach id sortiert)
BAUWEG_SCHLUESSEL = frozenset({"nach", "bezug", "flaeche", "ebene", "kanten"})


def _ohne_bauweg(obj):
    if isinstance(obj, dict):
        return {k: _ohne_bauweg(v) for k, v in obj.items() if k not in BAUWEG_SCHLUESSEL}
    if isinstance(obj, list):
        return [_ohne_bauweg(v) for v in obj]
    return obj


def bauweg_frei(spec: dict) -> dict:
    """Die Anforderungen einer Änderungs-Spec (Grundlage der Prüfsumme): ohne Anker, `bezug`, `nach`, Skriptdateien und
    ohne die Reihenfolge der Punkte. Die Spec selbst bleibt unverändert."""
    kern = {feld: copy.deepcopy(spec[feld]) for feld in PRUEF_FELDER if feld in spec}
    punkte = []
    for punkt in sorted(spec.get("punkte", []), key=lambda p: str(p.get("id", ""))):
        rest = {k: v for k, v in punkt.items() if not (punkt.get("typ") == "skript" and k == "datei")}
        punkte.append(_ohne_bauweg(rest))
    kern["punkte"] = punkte
    return kern


def _plausibel_befunde(spec: dict) -> list[dict]:
    """Doppelte Punkt-IDs und Ausdrücke, deren Parameter fehlen (Anforderungen werden als `=Name` geführt)."""
    befunde, parameter = [], spec.get("parameter", {})
    ids = [p["id"] for p in spec["punkte"]]
    for i, pid in enumerate(ids):
        if pid in ids[:i]:
            befunde.append({"pfad": f"punkte[{i}].id", "meldung": f"ID {pid!r} ist doppelt"})

    zu_pruefen = [(["punkte", i, "neu"], p["neu"]) for i, p in enumerate(spec["punkte"])
                  if (p["typ"] == "mass" or "variable" in p) and ist_ausdruck(p.get("neu"))]
    zu_pruefen += [(pfad, roh) for pfad, _, roh in _werte(spec.get("pruefung", {}), ["pruefung"])]
    for pfad, roh in zu_pruefen:
        try:
            auswerten(roh, parameter)
        except AusdruckFehler as e:
            befunde.append({"pfad": _pfad(pfad), "meldung": str(e)})
    return befunde


def aenderung_befunde(spec: dict) -> list[dict]:
    """Alle Befunde einer Änderungs-Spec ohne Aufnahme: Schema, danach Plausibilität."""
    return schema_befunde(spec, "aenderung") or _plausibel_befunde(spec)


def lade_aenderung(pfad: Path) -> dict:
    """Lädt und prüft eine Änderungs-Spec; wirft SpecFehler mit allen Befunden."""
    spec = lade_yaml(pfad)
    if befunde := aenderung_befunde(spec):
        raise SpecFehler(befunde)
    return spec


def validieren(pfad: Path) -> dict:
    """`swki validieren` für art: aenderung. Hinweise gibt es noch keine."""
    spec = lade_aenderung(pfad)
    return {"gueltig": True, "spec": str(pfad), "art": "aenderung", "name": spec["name"], "punkte": len(spec["punkte"]),
            "pruefsumme": pruefsumme(spec), "hinweise": []}


def freigeben(pfad: Path) -> dict:
    """Freigabe der Anforderungen – nur nach ausdrücklichem OK des Nutzers."""
    spec = lade_aenderung(pfad)
    return {"spec": str(pfad), "art": "aenderung", "kopie": str(kopie_pfad(pfad)), **spec_freigeben(pfad, spec)}
