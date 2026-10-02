"""Normtabellen der Normteile (swki/wissen/normteile/<norm>.yaml, Spec 3a §4): laden, Schema, Regeln, Quellen."""

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from swki.konfig import PROJEKT
from swki.normteile.fehler import NORMTABELLE_UNGUELTIG, NORMTEIL_UNBEKANNT, NormteilFehler
from swki.spec.ausdruck import AusdruckFehler, auswerten
from swki.spec.normen import groesse_text

ORDNER = PROJEKT / "swki" / "wissen" / "normteile"
SCHEMA = PROJEKT / "schema" / "normtabelle.schema.json"
_REGEL = re.compile(r"^(.+?)\s*(<=|>=|==|<|>)\s*(.+)$")
_EPS = 1e-9
_VERGLEICHE = {
    "<": lambda a, b: a < b - _EPS,
    "<=": lambda a, b: a <= b + _EPS,
    ">": lambda a, b: a > b + _EPS,
    ">=": lambda a, b: a >= b - _EPS,
    "==": lambda a, b: abs(a - b) <= _EPS,
}


def norm_datei(norm: str) -> str:
    """Dateiname ohne Endung: "ISO 4762", "ISO4762", "iso-4762" → "iso4762"."""
    return re.sub(r"[\s_-]+", "", norm).lower()


def normen(ordner: Path = ORDNER) -> list[str]:
    return sorted(p.stem for p in ordner.glob("*.yaml"))


def lade_normtabelle(norm: str, ordner: Path = ORDNER) -> dict:
    """Normtabelle; Größen, Varianten und Datumsangaben als Text (YAML liest 8, 8.8 und Daten sonst als Zahl/Datum)."""
    pfad = ordner / f"{norm_datei(norm)}.yaml"
    if not pfad.is_file():
        raise NormteilFehler(NORMTEIL_UNBEKANNT,
                             f"Norm {norm!r} unbekannt; vorhanden: {', '.join(normen(ordner)) or 'keine'}")
    t = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    t["groessen"] = {groesse_text(g): z for g, z in (t.get("groessen") or {}).items()}
    t["varianten"] = {str(v): w for v, w in (t.get("varianten") or {}).items()}
    if "vorgabe_variante" in t:
        t["vorgabe_variante"] = str(t["vorgabe_variante"])
    for q in t.get("quellen") or []:
        q["abgerufen"] = str(q.get("abgerufen"))
        q["groessen"] = [groesse_text(g) for g in q.get("groessen") or []]
    return t


def regel_erfuellt(regel: str, masse: dict) -> bool:
    """Regel wie "dk > d" über die Maße einer Größe (Ausdruckssyntax der Spezifikation, ohne führendes "=")."""
    treffer = _REGEL.match(regel.strip())
    if not treffer:
        raise AusdruckFehler(f"Regel {regel!r}: Vergleich (<, <=, >, >=, ==) fehlt")
    links, op, rechts = treffer.groups()
    return _VERGLEICHE[op](auswerten(f"={links}", masse), auswerten(f"={rechts}", masse))


def tabellen_befunde(t: dict, ordner: Path = ORDNER) -> list[dict]:
    """Schema, Vorlage, Varianten, Maßnamen, Längenreihen, Regeln, „Maße steigen mit der Größe“, Quellenpflicht
    (≥ 2 Quellen je abgeglichener Größe; eine dokumentierte Nutzerentscheidung `entscheidung` ersetzt sie)."""
    schema = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    befunde = [{"pfad": "/".join(map(str, f.absolute_path)) or "(wurzel)", "meldung": f.message}
               for f in schema.iter_errors(t)]
    if befunde:
        return befunde
    if not (ordner / t["vorlage"]).is_file():
        befunde.append({"pfad": "vorlage", "meldung": f"Vorlage {t['vorlage']} fehlt"})
    if t["vorgabe_variante"] not in t["varianten"]:
        befunde.append({"pfad": "vorgabe_variante", "meldung": f"{t['vorgabe_variante']!r} ist keine Variante"})
    regeln = []
    for regel in t["regeln"]:
        if _REGEL.match(regel.strip()):
            regeln.append(regel)
        else:
            befunde.append({"pfad": "regeln", "meldung": f"Regel {regel!r}: Vergleich (<, <=, >, >=, ==) fehlt"})
    namen = set(t["parameter"])
    for g, z in t["groessen"].items():
        pfad = f"groessen.{g}"
        if set(z["masse"]) != namen:
            befunde.append({"pfad": f"{pfad}.masse", "meldung": f"Maße {sorted(z['masse'])} ≠ parameter {sorted(namen)}"})
            continue
        if t["laenge"] != ("laengen" in z):
            befunde.append({"pfad": pfad, "meldung": "laengen " + ("fehlt" if t["laenge"] else "nur bei laenge: true")})
        laengen = z.get("laengen", [])
        if laengen != sorted(set(laengen)):
            befunde.append({"pfad": f"{pfad}.laengen", "meldung": "Längenreihe muss aufsteigend und ohne Doppel sein"})
        for regel in regeln:
            try:
                if not regel_erfuellt(regel, z["masse"]):
                    befunde.append({"pfad": f"{pfad}.masse", "meldung": f"Regel {regel!r} verletzt ({z['masse']})"})
            except AusdruckFehler as e:
                befunde.append({"pfad": f"{pfad}.masse", "meldung": str(e)})
    for name in sorted(namen):
        werte = [z["masse"].get(name) for z in t["groessen"].values()]
        if None not in werte and any(b < a for a, b in zip(werte, werte[1:])):
            befunde.append({"pfad": f"parameter.{name}", "meldung": f"{name} fällt mit der Größe: {werte}"})
    belegt: dict[str, int] = {}
    for q in t["quellen"]:
        for g in q["groessen"]:
            belegt[g] = belegt.get(g, 0) + 1
    for g, z in t["groessen"].items():
        if z["status"] == "abgeglichen" and belegt.get(g, 0) < 2 and not z.get("entscheidung"):
            befunde.append({"pfad": f"groessen.{g}.status",
                            "meldung": f"abgeglichen, aber nur {belegt.get(g, 0)} Quelle(n)"})
    return befunde


def pruefe_tabelle(t: dict, ordner: Path = ORDNER) -> None:
    if befunde := tabellen_befunde(t, ordner):
        raise NormteilFehler(NORMTABELLE_UNGUELTIG, f"Normtabelle {t.get('norm')}: {len(befunde)} Befund(e)",
                             befunde=befunde)
