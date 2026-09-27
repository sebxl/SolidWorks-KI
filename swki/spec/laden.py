"""Laden einer Spezifikation (YAML) mit Schema- und Plausibilitätsprüfung."""

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from swki.cli import SwkiFehler
from swki.compiler.skriptpruefung import pruefe_skript
from swki.konfig import PROJEKT
from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck

SCHEMA_ORDNER = PROJEKT / "schema"
_POSITIV = {"breite", "hoehe", "durchmesser", "radius", "tiefe", "abstand"}
_WINKEL = {"winkel"}


class SpecFehler(SwkiFehler):
    def __init__(self, befunde: list[dict]):
        super().__init__(f"{len(befunde)} Befund(e) in der Spezifikation")
        self.daten = {"befunde": befunde}


def _pfad(teile) -> str:
    text = ""
    for t in teile:
        text += f"[{t}]" if isinstance(t, int) else (f".{t}" if text else str(t))
    return text or "(Wurzel)"


def lade_yaml(pfad: Path) -> dict:
    if not pfad.exists():
        raise SpecFehler([{"pfad": "(Datei)", "meldung": f"{pfad} fehlt"}])
    try:
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise SpecFehler([{"pfad": "(Datei)", "meldung": f"YAML-Fehler: {e}"}]) from None
    if not isinstance(daten, dict):
        raise SpecFehler([{"pfad": "(Wurzel)", "meldung": "Die Spezifikation muss ein YAML-Objekt sein"}])
    return daten


def schema_befunde(spec: dict) -> list[dict]:
    art = spec.get("art")
    datei = SCHEMA_ORDNER / f"{art}.schema.json"
    if art != "teil" or not datei.exists():
        return [{"pfad": "art", "meldung": f"Art {art!r} wird nicht unterstützt (Stufe 2: nur 'teil')"}]
    validator = Draft202012Validator(json.loads(datei.read_text(encoding="utf-8")))
    befunde = []
    for fehler in validator.iter_errors(spec):
        genau = best_match(fehler.context) if fehler.context else fehler
        befunde.append({"pfad": _pfad(genau.absolute_path), "meldung": genau.message})
    return sorted(befunde, key=lambda b: b["pfad"])


def _werte(obj, pfad: list, eltern: str | None = None):
    """Liefert (pfad, schlüssel, wert) für alle Zahlen und Ausdrücke unterhalb von obj."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _werte(v, [*pfad, k], k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _werte(v, [*pfad, i], eltern)
    elif (isinstance(obj, (int, float)) and not isinstance(obj, bool)) or ist_ausdruck(obj):
        yield pfad, eltern, obj


def _referenzen(obj, pfad: list):
    """Liefert (pfad, feature-id) für alle Verweise auf Features ("feature" und "features")."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "feature" and isinstance(v, str):
                yield [*pfad, k], v
            elif k == "features" and isinstance(v, list) and all(isinstance(x, str) for x in v):
                for i, x in enumerate(v):
                    yield [*pfad, k, i], x
            else:
                yield from _referenzen(v, [*pfad, k])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _referenzen(v, [*pfad, i])


def plausibel_befunde(spec: dict, auftrag_ordner: Path) -> list[dict]:
    befunde = []
    parameter = spec.get("parameter", {})
    features = spec["features"]

    ids = [f["id"] for f in features]
    for i, fid in enumerate(ids):
        if fid in ids[:i]:
            befunde.append({"pfad": f"features[{i}].id", "meldung": f"ID {fid!r} ist doppelt"})

    for i, f in enumerate(features):
        for pfad, ref in _referenzen({k: v for k, v in f.items() if k != "id"}, ["features", i]):
            if ref not in ids[:i]:
                befunde.append({"pfad": _pfad(pfad), "meldung": f"Verweis auf {ref!r}: kein früheres Feature"})
    for pfad, ref in _referenzen(spec.get("pruefung", {}), ["pruefung"]):
        if ref not in ids:
            befunde.append({"pfad": _pfad(pfad), "meldung": f"Verweis auf unbekanntes Feature {ref!r}"})

    for pfad, schluessel, roh in _werte({k: v for k, v in spec.items() if k != "parameter"}, []):
        try:
            wert = auswerten(roh, parameter)
        except AusdruckFehler as e:
            befunde.append({"pfad": _pfad(pfad), "meldung": str(e)})
            continue
        if schluessel in _POSITIV and "versatz" not in pfad and wert <= 0:
            befunde.append({"pfad": _pfad(pfad), "meldung": f"{schluessel} muss > 0 sein (ist {wert:g})"})
        if schluessel in _WINKEL and not 0 < wert <= 360:
            befunde.append({"pfad": _pfad(pfad), "meldung": f"winkel muss in (0, 360] liegen (ist {wert:g})"})

    for i, f in enumerate(features):
        elemente = f.get("skizze", {}).get("elemente", [])
        mittellinien = sum(1 for e in elemente if "mittellinie" in e)
        if f["typ"] == "rotation" and mittellinien != 1:
            befunde.append({"pfad": f"features[{i}].skizze.elemente", "meldung": "Rotation braucht genau eine mittellinie"})
        if f["typ"] != "rotation" and mittellinien:
            befunde.append({"pfad": f"features[{i}].skizze.elemente", "meldung": "mittellinie nur bei Rotation erlaubt"})
        if f["typ"] == "bohrung" and "senkung" in f:
            try:
                if auswerten(f["senkung"]["durchmesser"], parameter) <= auswerten(f["durchmesser"], parameter):
                    befunde.append({"pfad": f"features[{i}].senkung.durchmesser",
                                    "meldung": "Senkungsdurchmesser muss größer als der Bohrungsdurchmesser sein"})
            except AusdruckFehler:
                pass  # bereits oben gemeldet
        if f["typ"] == "skript":
            datei = auftrag_ordner / f["datei"]
            if not datei.exists():
                befunde.append({"pfad": f"features[{i}].datei", "meldung": f"{datei} fehlt"})
            else:
                for b in pruefe_skript(datei.read_text(encoding="utf-8")):
                    befunde.append({"pfad": f"features[{i}].datei", "meldung": f"Zeile {b['zeile']}: {b['meldung']}"})
    return befunde


def lade_spec(pfad: Path) -> dict:
    """Lädt und prüft eine Spezifikation; wirft SpecFehler mit allen Befunden."""
    spec = lade_yaml(pfad)
    befunde = schema_befunde(spec)
    if not befunde:
        befunde = plausibel_befunde(spec, pfad.parent)
    if befunde:
        raise SpecFehler(befunde)
    return spec
