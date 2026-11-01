"""Scheiben einer Änderungs-Spec an einer Baugruppe (Spec Bestandsdateien §4.1, §8; Plan Etappe 2 Task 4).

Eine Spec mit `in_datei` zerfällt in **Teil-Scheiben** und **Haupt-Punkte**. Eine Teil-Scheibe ist eine gewöhnliche Änderungs-Spec
von Etappe 1 (nur die Punkte, Bereiche und Messungen dieser Datei, `bestand.datei` der relative Pfad der Datei): Validierung,
Bau und Prüfung von Etappe 1 verarbeiten sie unverändert. Haupt-Punkte sind alle Punkte ohne `in_datei`: Baugruppen-Punkte,
`eigenschaft` und `skript` an der Hauptbaugruppe. Reine Funktionen über Dicts, ohne SolidWorks.

Die Scheibe hat eigene Indizes; `scheiben_karte` und `zurueck` führen einen Pfad der Scheibe (`punkte[0].alt`) auf den Pfad in der
ganzen Spec zurück, damit Befunde dort stehen, wo der Nutzer sie sucht.
"""

import copy
import re

from swki.bestand.fehler import BESTAND_REFERENZ, BestandFehler

# Punkte, die an der Hauptbaugruppe selbst (ohne in_datei) in Etappe 1 geprüft werden können; die übrigen Teil-Typen gehören an ein Teil
HAUPT_TYPEN = frozenset({"eigenschaft", "skript"})
_OHNE = ("in_datei", "lage_folgen")


def datei_schluessel(text: str) -> str:
    """Vergleichsform eines relativen Pfads in der Bestandskopie: `/` statt `\\`, ohne Groß-/Kleinschreibung (Windows)."""
    return text.replace("\\", "/").casefold()


def _in_datei(p: dict, schluessel: str) -> bool:
    return p.get("in_datei") is not None and datei_schluessel(p["in_datei"]) == schluessel


def dateien_mit_punkten(spec: dict) -> list[str]:
    """Die Dateien, an denen Punkte (`in_datei`) hängen, in der Reihenfolge der ersten Nennung und in der ersten Schreibweise."""
    gesehen, dateien = set(), []
    for p in spec["punkte"]:
        datei = p.get("in_datei")
        if datei is not None and datei_schluessel(datei) not in gesehen:
            gesehen.add(datei_schluessel(datei))
            dateien.append(datei)
    return dateien


def haupt_punkte(spec: dict) -> list[dict]:
    """Die Punkte ohne `in_datei`: Baugruppen-Punkte, `eigenschaft` und `skript` an der Hauptbaugruppe (Teil-Typen ohne `in_datei`
    meldet die Validierung)."""
    return [p for p in spec["punkte"] if "in_datei" not in p]


def aenderung_an_haupt(spec: dict) -> bool:
    """Wird die Hauptbaugruppe gespeichert? Ja, wenn ein Haupt-Punkt sie ändert oder ein Punkt `lage_folgen` nennt (die Lage von
    Komponenten steckt in der Baugruppe)."""
    return bool(haupt_punkte(spec)) or any(p.get("lage_folgen") for p in spec["punkte"])


def scheiben_karte(spec: dict, datei: str | None) -> dict:
    """Welche Einträge der Spec in der Scheibe der Datei landen (`None`: Haupt-Scheibe), als Indizes in der Spec: `punkte`,
    `bereiche`, `bereiche_punkte` (je Bereich der Scheibe die Stellen seiner Punkte im Bereich der Spec), `masse_pruefen`,
    `datei_punkt` (erster Punkt der Datei, trägt `bestand.datei` zurück)."""
    schl = None if datei is None else datei_schluessel(datei)
    if schl is None:
        punkte = [i for i, p in enumerate(spec["punkte"]) if "in_datei" not in p and p["typ"] in HAUPT_TYPEN]
    else:
        punkte = [i for i, p in enumerate(spec["punkte"]) if _in_datei(p, schl)]
    ids = {spec["punkte"][i]["id"] for i in punkte}
    bereiche, bereiche_punkte = [], []
    for j, b in enumerate(spec.get("bereiche", [])):
        gehoert = ("in_datei" not in b) if schl is None else _in_datei(b, schl)
        eigene = [k for k, pid in enumerate(b["punkte"]) if pid in ids] if gehoert else []
        if eigene:
            bereiche.append(j)
            bereiche_punkte.append(eigene)
    masse = [] if schl is None else [m for m, x in enumerate(spec.get("pruefung", {}).get("masse_pruefen", [])) if _in_datei(x, schl)]
    return {"punkte": punkte, "bereiche": bereiche, "bereiche_punkte": bereiche_punkte, "masse_pruefen": masse,
            "datei_punkt": punkte[0] if schl is not None and punkte else None}


def _scheibe(spec: dict, karte: dict, bestand: dict) -> dict:
    """Die Änderungs-Spec von Etappe 1 zur Karte: ohne `in_datei` und `lage_folgen`, ohne `kollision_erlaubt` (gilt für die ganze
    Baugruppe), Parameter vollständig (Ausdrücke der Punkte rechnen mit ihnen)."""
    punkte = [{k: copy.deepcopy(v) for k, v in spec["punkte"][i].items() if k not in _OHNE} for i in karte["punkte"]]
    bereiche = []
    for j, eigene in zip(karte["bereiche"], karte["bereiche_punkte"]):
        b = spec["bereiche"][j]
        bereiche.append({**{k: copy.deepcopy(v) for k, v in b.items() if k != "in_datei"}, "punkte": [b["punkte"][k] for k in eigene]})
    masse = [{k: copy.deepcopy(v) for k, v in spec["pruefung"]["masse_pruefen"][m].items() if k != "in_datei"}
             for m in karte["masse_pruefen"]]
    return {"art": "aenderung", "name": spec["name"], "bestand": bestand, "parameter": copy.deepcopy(spec.get("parameter", {})),
            "punkte": punkte, "bereiche": bereiche, "pruefung": {"masse_pruefen": masse} if masse else {}}


def scheibe(spec: dict, datei: str, dateien: dict) -> dict:
    """Die Teil-Änderungs-Spec für `datei` (Schreibweise egal): nur ihre Punkte, Bereiche und Messungen. `dateien` ist `dateien` der
    Baugruppen-Aufnahme (relativer Pfad → {sha256, …}, ohne die Hauptdatei); daraus kommen der aufgenommene Pfad und die
    `sha256`. Die Aufnahmenummer bleibt die der Spec. Die Spec bleibt unverändert."""
    schl = datei_schluessel(datei)
    rel = next((r for r in dateien if datei_schluessel(r) == schl), None)
    if rel is None:
        raise BestandFehler(BESTAND_REFERENZ, f"{datei!r} ist keine aufgenommene Datei der Baugruppe", datei=datei,
                            dateien=sorted(dateien))
    bestand = {"datei": rel, "sha256": dateien[rel]["sha256"], "aufnahme": spec["bestand"]["aufnahme"]}
    return _scheibe(spec, scheiben_karte(spec, datei), bestand)


def haupt_scheibe(spec: dict) -> dict:
    """Die Änderungs-Spec für die Hauptbaugruppe selbst: nur `eigenschaft` und `skript` ohne `in_datei` mit ihren Bereichen, so prüft
    der Code von Etappe 1 (Konfiguration, Skriptdatei, Bereich) sie unverändert."""
    return _scheibe(spec, scheiben_karte(spec, None), copy.deepcopy(spec["bestand"]))


_PUNKT = re.compile(r"^punkte\[(\d+)\]")
_BEREICH = re.compile(r"^bereiche\[(\d+)\](?:\.punkte\[(\d+)\])?")
_MESSUNG = re.compile(r"^pruefung\.masse_pruefen\[(\d+)\]")


def zurueck(pfad: str, karte: dict) -> str:
    """Pfad in der Scheibe (`punkte[0].alt`, `bereiche[0].features[1]`, `pruefung.masse_pruefen[0]…`, `bestand.datei`) auf den
    Pfad in der ganzen Spec abbilden. Anderes bleibt, wie es ist."""
    if m := _PUNKT.match(pfad):
        return f"punkte[{karte['punkte'][int(m.group(1))]}]" + pfad[m.end():]
    if m := _BEREICH.match(pfad):
        j = int(m.group(1))
        neu = f"bereiche[{karte['bereiche'][j]}]"
        if m.group(2) is not None:
            neu += f".punkte[{karte['bereiche_punkte'][j][int(m.group(2))]}]"
        return neu + pfad[m.end():]
    if m := _MESSUNG.match(pfad):
        return f"pruefung.masse_pruefen[{karte['masse_pruefen'][int(m.group(1))]}]" + pfad[m.end():]
    if pfad == "bestand.datei" and karte["datei_punkt"] is not None:
        return f"punkte[{karte['datei_punkt']}].in_datei"
    return pfad
