"""Laden einer Spezifikation (YAML) mit Schema- und Plausibilitätsprüfung."""

import json
import math
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from swki.cli import SwkiFehler
from swki.compiler.skriptpruefung import pruefe_skript
from swki.konfig import PROJEKT
from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck
from swki.spec.konturen import eckradien, kontur_punkte
from swki.spec.normen import groesse_text, norm_von, normmasse, verfuegbare_groessen

SCHEMA_ORDNER = PROJEKT / "schema"
_POSITIV = {"breite", "hoehe", "durchmesser", "radius", "tiefe", "abstand", "laenge", "gewindetiefe"}
_WINKEL = {"winkel"}
_TOL_KONTUR_MM = 1e-6
_RESERVIERT = re.compile(r"^achse_[xyz]$")  # Referenzachsen der Muster (handler/muster.py)
_COMPILER_ENDUNGEN = ("_skizze", "_senkung", "_positionen")  # vom Compiler angelegte Skizzen/Features


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


def _abstand2(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _radien_befunde(polygon: dict, pfad: str, p: dict) -> list[dict]:
    pts = [(auswerten(u, p), auswerten(v, p)) for u, v in polygon["punkte"]]
    roh, n = polygon.get("radien", 0), len(pts)
    if isinstance(roh, list) and len(roh) != n:
        return [{"pfad": f"{pfad}.radien", "meldung": f"radien: {len(roh)} Werte für {n} Ecken"}]
    befunde = []
    for k, r in enumerate(eckradien(polygon, p)):
        stelle = f"{pfad}.radien[{k}]" if isinstance(roh, list) else f"{pfad}.radien"
        kante = min(_abstand2(pts[k], pts[k - 1]), _abstand2(pts[k], pts[(k + 1) % n]))
        if r < 0:
            befunde.append({"pfad": stelle, "meldung": f"Radius an Ecke {k + 1} muss ≥ 0 sein (ist {r:g})"})
        elif r > 0 and r >= kante / 2:
            befunde.append({"pfad": stelle, "meldung": f"Radius {r:g} an Ecke {k + 1} muss kleiner als die halbe "
                                                       f"kürzere Nachbarkante ({kante / 2:g}) sein"})
    return befunde


def _kontur_befunde(kontur: dict, pfad: str, p: dict) -> list[dict]:
    punkte = kontur_punkte(kontur, p)
    befunde = []
    for k, s in enumerate(kontur["segmente"]):
        if "bogen" not in s:
            continue
        mitte = (auswerten(s["mitte"][0], p), auswerten(s["mitte"][1], p))
        if any(_abstand2(mitte, q) <= _TOL_KONTUR_MM for q in punkte):
            befunde.append({"pfad": f"{pfad}.segmente[{k}]",
                            "meldung": "Bogenmittelpunkt liegt auf einem Konturpunkt (Kreissektor) – wird nicht "
                                       "unterstützt; Kontur anders aufteilen"})
            continue
        ra, rb = _abstand2(punkte[k], mitte), _abstand2(punkte[k + 1], mitte)
        if abs(ra - rb) > _TOL_KONTUR_MM:
            befunde.append({"pfad": f"{pfad}.segmente[{k}]",
                            "meldung": f"Bogen: Anfang und Ende ungleich weit vom Mittelpunkt ({ra:g} / {rb:g} mm)"})
        elif _abstand2(punkte[k], punkte[k + 1]) <= _TOL_KONTUR_MM:
            befunde.append({"pfad": f"{pfad}.segmente[{k}]",
                            "meldung": "Bogen: Anfang = Ende (Vollkreis als kreis angeben)"})
    if _abstand2(punkte[0], punkte[-1]) > _TOL_KONTUR_MM:
        befunde.append({"pfad": f"{pfad}.segmente", "meldung": "Kontur ist nicht geschlossen: letzter Endpunkt muss start sein"})
    return befunde


def _element_befunde(e: dict, pfad: str, p: dict) -> list[dict]:
    """Eckradien, Kontur (Spec 2c §4); Langloch-Maße prüft die allgemeine Positiv-/Winkelprüfung."""
    try:
        if "rechteck" in e and "radius" in e["rechteck"]:
            r = e["rechteck"]
            if auswerten(r["radius"], p) >= min(auswerten(r["breite"], p), auswerten(r["hoehe"], p)) / 2:
                return [{"pfad": f"{pfad}.rechteck.radius",
                         "meldung": "radius muss kleiner als die halbe kürzere Seite sein"}]
        if "polygon" in e and "radien" in e["polygon"]:
            return _radien_befunde(e["polygon"], f"{pfad}.polygon", p)
        if "kontur" in e:
            return _kontur_befunde(e["kontur"], f"{pfad}.kontur", p)
    except AusdruckFehler:
        pass  # bereits oben gemeldet
    return []


def _ende_befunde(ende: dict, pfad: str) -> list[dict]:
    typ, befunde = ende["typ"], []
    if "flaeche" in ende and typ not in ("bis_flaeche", "versatz_von_flaeche"):
        befunde.append({"pfad": f"{pfad}.flaeche",
                        "meldung": f"flaeche gilt nur bei bis_flaeche/versatz_von_flaeche (typ ist {typ})"})
    if "abstand" in ende and typ != "versatz_von_flaeche":
        befunde.append({"pfad": f"{pfad}.abstand", "meldung": f"abstand gilt nur bei versatz_von_flaeche (typ ist {typ})"})
    if "tiefe" in ende and typ in ("bis_flaeche", "versatz_von_flaeche"):
        befunde.append({"pfad": f"{pfad}.tiefe", "meldung": f"tiefe gilt nicht bei {typ} (die Tiefe folgt aus der Fläche)"})
    return befunde


def _normbohrung_befunde(f: dict, pfad: str, p: dict) -> list[dict]:
    befunde = []
    norm = norm_von(f)
    if normmasse(f["art"], f["groesse"], norm) is None:
        verfuegbar = ", ".join(verfuegbare_groessen(f["art"], norm)) or "keine"
        befunde.append({"pfad": f"{pfad}.groesse",
                        "meldung": f"Größe {groesse_text(f['groesse'])!r} für {f['art']} ({norm}) nicht in der "
                                   f"Maßtabelle swki/wissen/bohrungsnormen.yaml; verfügbar: {verfuegbar}"})
    if "gewindetiefe" in f and f["art"] != "gewinde":
        befunde.append({"pfad": f"{pfad}.gewindetiefe", "meldung": "gewindetiefe nur bei art: gewinde"})
    if f["art"] == "gewinde" and not f.get("durch") and "gewindetiefe" not in f:
        befunde.append({"pfad": pfad, "meldung": "gewindetiefe ist Pflicht bei einer Gewindebohrung mit tiefe"})
    if "gewindetiefe" in f and "tiefe" in f:
        try:
            if auswerten(f["gewindetiefe"], p) > auswerten(f["tiefe"], p):
                befunde.append({"pfad": f"{pfad}.gewindetiefe", "meldung": "gewindetiefe darf nicht größer als tiefe sein"})
        except AusdruckFehler:
            pass  # bereits oben gemeldet
    try:
        pos = [(auswerten(u, p), auswerten(v, p)) for u, v in f["positionen"]]
        for k, q in enumerate(pos):
            gleich = next((j for j in range(k) if _abstand2(pos[j], q) <= _TOL_KONTUR_MM), None)
            if gleich is not None:
                befunde.append({"pfad": f"{pfad}.positionen[{k}]",
                                "meldung": f"Position {k + 1} ist doppelt (gleich Position {gleich + 1})"})
        masse = normmasse(f["art"], f["groesse"], norm)
        if "tiefe" in f and masse is not None:
            tiefe = auswerten(f["tiefe"], p)
            if f["art"] == "zylinderschraube":
                grenze, was = masse["senkung_t"], "Senktiefe"
            elif f["art"] == "senkschraube":
                grenze = (masse["senkung_d"] - masse["durchgang"]) / 2 / math.tan(math.radians(masse["senkwinkel"]) / 2)
                was = "Senkungshöhe"
            else:
                grenze = None
            if grenze is not None and tiefe <= grenze:
                befunde.append({"pfad": f"{pfad}.tiefe",
                                "meldung": f"tiefe {tiefe:g} muss größer als die {was} ({grenze:.4g} mm) sein"})
    except AusdruckFehler:
        pass  # bereits oben gemeldet
    return befunde


def plausibel_befunde(spec: dict, auftrag_ordner: Path) -> list[dict]:
    befunde = []
    parameter = spec.get("parameter", {})
    features = spec["features"]

    ids = [f["id"] for f in features]
    for i, fid in enumerate(ids):
        if fid in ids[:i]:
            befunde.append({"pfad": f"features[{i}].id", "meldung": f"ID {fid!r} ist doppelt"})
    skripte = [f["id"] for f in features if f["typ"] == "skript"]
    for i, fid in enumerate(ids):
        zusatz = any(re.fullmatch(rf"{re.escape(s)}_\d+", fid) for s in skripte)  # weitere Features eines Skripts
        if _RESERVIERT.match(fid) or fid.endswith(_COMPILER_ENDUNGEN) or zusatz:
            befunde.append({"pfad": f"features[{i}].id",
                            "meldung": f"ID {fid!r} ist für vom Compiler angelegte Features reserviert "
                                       "(achse_x|y|z, <id>_skizze, <id>_senkung, <id>_positionen, <skript-id>_<n>)"})

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
        if schluessel in _WINKEL and "langloch" in pfad:
            if not 0 <= wert < 180:
                befunde.append({"pfad": _pfad(pfad), "meldung": f"langloch.winkel muss in [0, 180) liegen (ist {wert:g})"})
        elif schluessel in _WINKEL and not 0 < wert <= 360:
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
        for k, e in enumerate(elemente):
            befunde += _element_befunde(e, f"features[{i}].skizze.elemente[{k}]", parameter)
        if "ende" in f:
            befunde += _ende_befunde(f["ende"], f"features[{i}].ende")
        if f["typ"] == "normbohrung":
            befunde += _normbohrung_befunde(f, f"features[{i}]", parameter)
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
