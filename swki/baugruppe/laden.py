"""Baugruppen-Spezifikation laden (Spec 3b §5): Schema, Teil-Specs, Normteile, Plausibilität."""

from pathlib import Path

from swki.baugruppe.modell import Baugruppe, Quelle
from swki.baugruppe.plausibel import plausibel_befunde
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.fehler import NormteilFehler
from swki.normteile.schluessel import loese_auf
from swki.normteile.tabelle import lade_normtabelle, pruefe_tabelle
from swki.spec.laden import SpecFehler, lade_spec, lade_yaml, schema_befunde


def teile_normteil(text: str) -> tuple[str, str]:
    """"ISO 4762 M8x30" → ("ISO 4762", "M8x30"): das letzte Wort ist die Größe."""
    norm, _, groesse = text.strip().rpartition(" ")
    return norm.strip(), groesse


def _normteil(kid: str, quelle: dict) -> tuple[Quelle | None, list[dict]]:
    norm, groesse = teile_normteil(quelle["normteil"])
    try:
        pruefe_tabelle(lade_normtabelle(norm))
        t, a = loese_auf(norm, groesse, quelle.get("variante"))
    except NormteilFehler as e:
        return None, [{"pfad": f"komponenten.{kid}.quelle", "meldung": f"{e.daten['code']}: {e}"}]
    spec = erzeuge_spec(t, a, vorlage_text(t))
    return Quelle("normteil", spec, norm=t["norm"], groesse=a.groesse, laenge=a.laenge, variante=a.variante,
                  schluessel=a.schluessel, masse=dict(t["groessen"][a.groesse]["masse"])), []


def _teil(kid: str, datei: str, ordner: Path, cache: dict) -> tuple[Quelle | None, list[dict]]:
    if datei not in cache:
        try:
            cache[datei] = lade_spec(ordner / datei)
        except SpecFehler as e:
            cache[datei] = None
            return None, [{"pfad": f"{kid}: {b['pfad']}", "meldung": b["meldung"]} for b in e.daten["befunde"]]
    if cache[datei] is None:
        return None, []  # Befunde stehen schon bei der ersten Komponente mit dieser Datei
    return Quelle("teil", cache[datei], datei=datei), []


def lade_quellen(spec: dict, ordner: Path) -> tuple[dict[str, Quelle], dict[str, dict], list[dict]]:
    quellen, cache, befunde = {}, {}, []
    for k in spec["komponenten"]:
        q = k["quelle"]
        quelle, b = _teil(k["id"], q["teil"], ordner, cache) if "teil" in q else _normteil(k["id"], q)
        befunde += b
        if quelle is not None:
            quellen[k["id"]] = quelle
    return quellen, {d: s for d, s in cache.items() if s is not None}, befunde


def lade_baugruppe(pfad: Path) -> Baugruppe:
    """Lädt und prüft eine Baugruppen-Spezifikation; wirft SpecFehler mit allen Befunden."""
    spec = lade_yaml(pfad)
    befunde = schema_befunde(spec, "baugruppe")
    quellen, teile = {}, {}
    if not befunde:
        quellen, teile, befunde = lade_quellen(spec, pfad.parent)
        if not befunde:
            befunde = plausibel_befunde(spec, quellen)
    if befunde:
        raise SpecFehler(befunde)
    return Baugruppe(pfad, spec, quellen, teile)
