"""Baugruppen-Spezifikation laden (Spec 3b §5, 3c §8.2): Schema, Teil-Specs, Normteile, Kaufteile, Plausibilität."""

from pathlib import Path

from swki.baugruppe.modell import Baugruppe, Quelle
from swki.baugruppe.plausibel import plausibel_befunde
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.fehler import KaufteilFehler
from swki.kaufteile.katalog import bibliotheksschluessel, finde, geprueft
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.fehler import NormteilFehler
from swki.normteile.schluessel import loese_auf
from swki.normteile.tabelle import lade_normtabelle, pruefe_tabelle
from swki.spec.freigabe import FreigabeFehler, pruefe_freigabe
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


def kaufteil_spec(eintrag: dict) -> dict:
    """Teilansicht eines Kaufteils für die Baugruppe: die Einbaureferenzen als referenz-Features (Auswahl per Name wie
    bei Normteilen) und die Gewindegruppen; die fremde Geometrie selbst wird nie über Features angesprochen."""
    return {"art": "teil", "name": bibliotheksschluessel(eintrag["hersteller"], eintrag["bestellnummer"]),
            "features": [{"id": n, "typ": "referenz"} for n in eintrag["einbau"]], "gewinde": eintrag.get("gewinde", {})}


def _kaufteil(kid: str, quelle: dict) -> tuple[Quelle | None, list[dict]]:
    """Kaufteil aus dem Katalog (Spec 3c §8.2): Eintrag vorhanden und gültig; freigegeben und geprüft sind Befunde."""
    pfad_befund = f"komponenten.{kid}.quelle"
    try:
        pfad = finde(quelle["kaufteil"])
        eintrag = lade_eintrag(pfad)
    except KaufteilFehler as e:
        return None, [{"pfad": pfad_befund, "meldung": f"{e.daten['code']}: {e}"}]
    except SpecFehler as e:
        return None, [{"pfad": pfad_befund, "meldung": f"Katalogeintrag {quelle['kaufteil']} ungültig: {b['pfad']}: "
                                                       f"{b['meldung']}"} for b in e.daten["befunde"]]
    befunde = []
    try:
        pruefe_freigabe(pfad, eintrag)
    except FreigabeFehler as e:
        befunde.append({"pfad": pfad_befund, "meldung": f"KAUFTEIL_NICHT_FREIGEGEBEN: {e}"})
    if not befunde and not geprueft(pfad, eintrag):
        befunde.append({"pfad": pfad_befund, "meldung": f"KAUFTEIL_UNGEPRUEFT: {quelle['kaufteil']} hat kein bestandenes "
                                                        "Prüfer-Urteil zur aktuellen Freigabe"})
    q = Quelle("kaufteil", kaufteil_spec(eintrag), schluessel=bibliotheksschluessel(eintrag["hersteller"],
                                                                                     eintrag["bestellnummer"]),
               eintrag=eintrag, eintrag_pfad=pfad)
    return q, befunde


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
        if "teil" in q:
            quelle, b = _teil(k["id"], q["teil"], ordner, cache)
        elif "kaufteil" in q:
            quelle, b = _kaufteil(k["id"], q)
        else:
            quelle, b = _normteil(k["id"], q)
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
