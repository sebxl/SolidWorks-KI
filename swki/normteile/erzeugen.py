"""Spezifikation eines Normteils aus Bauvorlage und Tabellenzeile; Prüfsummen und Befunde (Spec 3a §5–§7)."""

import hashlib
import json
from pathlib import Path

import yaml

from swki.normteile.schluessel import Anfrage
from swki.normteile.tabelle import ORDNER
from swki.spec.hinweise import feste_masse
from swki.spec.laden import plausibel_befunde, schema_befunde


def vorlage_text(t: dict, ordner: Path = ORDNER) -> str:
    return (ordner / t["vorlage"]).read_text(encoding="utf-8")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def vorlage_pruefsumme(text: str) -> str:
    return _sha(text.replace("\r\n", "\n"))


def teil_pruefsumme(t: dict, a: Anfrage, text: str) -> str:
    """Prüfsumme über alles, was das Teil bestimmt: Norm, Benennung, Maße der Größe, Länge, Variante mit Werkstoff und
    Vorlage. Ändert sich eines davon, gilt die Bibliotheksdatei als veraltet."""
    inhalt = {"norm": t["norm"], "benennung": t["benennung"], "groesse": a.groesse,
              "masse": t["groessen"][a.groesse]["masse"], "laenge": a.laenge, "variante": a.variante,
              "material": t["varianten"][a.variante]["material"], "vorlage": vorlage_pruefsumme(text)}
    return _sha(json.dumps(inhalt, sort_keys=True, ensure_ascii=False))


def benennung(t: dict, a: Anfrage) -> str:
    return f"{t['benennung']} {t['norm']} - {a.bezeichnung} - {a.variante}"


def erzeuge_spec(t: dict, a: Anfrage, text: str) -> dict:
    """Vorlage mit den Parametern der Tabellenzeile (plus l), Name, Werkstoff und Eigenschaften; Features und Prüfung
    bleiben unverändert."""
    spec = yaml.safe_load(text)
    parameter = dict(t["groessen"][a.groesse]["masse"])
    if a.laenge is not None:
        parameter["l"] = a.laenge
    spec["name"] = a.schluessel
    spec["parameter"] = parameter
    spec["material"] = t["varianten"][a.variante]["material"]
    spec["eigenschaften"] = {"Benennung": benennung(t, a), "Norm": t["norm"], "Groesse": a.bezeichnung,
                             "Festigkeitsklasse": a.variante}
    return spec


def spec_befunde(spec: dict, ordner: Path = ORDNER) -> list[dict]:
    """Schema- und Plausibilitätsbefunde; feste Zahlen in Features gelten bei Normteilen als Befund (jedes Maß ist ein
    Ausdruck über die Tabellenwerte)."""
    befunde = schema_befunde(spec) or plausibel_befunde(spec, ordner)
    return befunde + [{"pfad": h["pfad"], "meldung": h["meldung"]} for h in feste_masse(spec)]
