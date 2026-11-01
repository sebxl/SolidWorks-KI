"""Attrappe einer Baugruppen-Aufnahme (`bestand.json` einer Baugruppe, Plan Etappe 2) für die Tests ohne SolidWorks.

Haupt.SLDASM mit: Gehaeuse-1 (fixiert), Deckel-1, Platte-1, Schieber-1, elf Schrauben (eine Datei, elf Instanzen), Unter-1
(Unterbaugruppe mit Welle-1), Abgeleitet-1 (hängt am Basisteil Basis-1) und einer virtuellen Komponente. Verknüpfungen: Abstand1 und
Abstand2 frei, Abstand3 von einer Gleichung gesteuert, Winkel1, Deckungsgleich3 und Konzentrisch2 an Deckel-1, Konzentrisch5 an einer
Komponente der Unterbaugruppe, Grenze_Abstand1 (0 bis 5 mm, gefahren). Die Teile tragen die Aufnahme von `beispiel_aufnahme`
(Lagerdeckel) mit dem relativen Pfad als Dateinamen.
"""

import copy
import hashlib

from tests.bestand.beispiel_aufnahme import AUFNAHME

SHA_BG = "5e7d" * 16
HAUPT = "Haupt.SLDASM"
STANDARD_LAGE = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]


def sha(rel: str) -> str:
    return hashlib.sha256(rel.encode("utf-8")).hexdigest()


def _datei(rel: str, art: str = "teil", referenzen=(), aelter: bool = False) -> dict:
    return {"original": f"D:\\Kunde\\{rel.replace('/', chr(92))}", "sha256": sha(rel), "art": art, "versionen": ["18000[2025/268]"],
            "version_aelter": aelter, "referenzen": list(referenzen)}


DATEIEN = {
    "teile/Gehaeuse.SLDPRT": _datei("teile/Gehaeuse.SLDPRT"),
    "teile/Deckel.SLDPRT": _datei("teile/Deckel.SLDPRT"),
    "teile/Platte.SLDPRT": _datei("teile/Platte.SLDPRT"),
    "teile/Schieber.SLDPRT": _datei("teile/Schieber.SLDPRT"),
    "teile/Schraube.SLDPRT": _datei("teile/Schraube.SLDPRT"),
    "teile/Welle.SLDPRT": _datei("teile/Welle.SLDPRT"),
    "teile/Basis.SLDPRT": _datei("teile/Basis.SLDPRT"),
    "teile/Abgeleitet.SLDPRT": _datei("teile/Abgeleitet.SLDPRT", referenzen=["teile/Basis.SLDPRT"]),
    "Unter.SLDASM": _datei("Unter.SLDASM", art="baugruppe", referenzen=["teile/Welle.SLDPRT"]),  # trägt ihre Kinder
}


def _komp(datei: str, fixiert: bool = False, virtuell: bool = False) -> dict:
    return {"datei": datei, "konfiguration": "Standard", "virtuell": virtuell, "muster": False, "loesen": 0,
            "fixiert": {"Standard": fixiert}, "unterdrueckt": {"Standard": False}, "status": {"Standard": 3},
            "transform": {"Standard": list(STANDARD_LAGE)}}


KOMPONENTEN = {
    "Gehaeuse-1": _komp("teile/Gehaeuse.SLDPRT", fixiert=True),
    "Deckel-1": _komp("teile/Deckel.SLDPRT"),
    "Platte-1": _komp("teile/Platte.SLDPRT"),
    "Schieber-1": _komp("teile/Schieber.SLDPRT"),
    **{f"Schraube-{n}": _komp("teile/Schraube.SLDPRT") for n in range(1, 12)},
    "Unter-1": _komp("Unter.SLDASM"),
    "Unter-1/Welle-1": _komp("teile/Welle.SLDPRT"),
    "Abgeleitet-1": _komp("teile/Abgeleitet.SLDPRT"),
    "Basis-1": _komp("teile/Basis.SLDPRT"),
    "Teil1^Haupt-1": _komp("Teil1^Haupt.sldprt", virtuell=True),
}


def _mate(typ: int, partner: list[str], wert=None, min_=None, max_=None, grenze: bool = False, gesteuert: bool = False) -> dict:
    return {"typ": typ, "ausrichtung": 0, "wert": wert, "min": min_, "max": max_, "grenze": grenze, "gesteuert": gesteuert,
            "partner": partner, "fehler": {"Standard": 0}, "unterdrueckt": {"Standard": False}}


VERKNUEPFUNGEN = {
    "Abstand1": _mate(5, ["Schraube-1", "Gehaeuse-1"], wert=10.0),
    "Abstand2": _mate(5, ["Schraube-2", "Gehaeuse-1"], wert=3.0),
    "Abstand3": _mate(5, ["Schraube-3", "Gehaeuse-1"], wert=7.0, gesteuert=True),
    "Winkel1": _mate(6, ["Platte-1", "Gehaeuse-1"], wert=90.0),
    "Deckungsgleich3": _mate(0, ["Deckel-1", "Gehaeuse-1"]),
    "Konzentrisch2": _mate(1, ["Deckel-1", "Gehaeuse-1"]),
    "Konzentrisch5": _mate(1, ["Unter-1/Welle-1", "Gehaeuse-1"]),
    "Grenze_Abstand1": _mate(5, ["Schieber-1", "Gehaeuse-1"], wert=2.5, min_=0.0, max_=5.0, grenze=True),
}

BEWEGUNGEN = {
    "Grenze_Abstand1": {"komponente": "Schieber-1", "art": "abstand", "min": 0.0, "max": 5.0, "gefahren": True,
                        "bewegt": ["Schieber-1"], "kollisionen": [], "pruefungen": [], "hinweis": None},
}

AUFNAHME_BG = {
    "version": 2, "art": "baugruppe", "sw_jahr": 2025,
    "datei": {"name": HAUPT, "original": "D:\\Kunde\\Haupt.SLDASM", "sha256": SHA_BG, "versionen": ["18000[2025/268]"],
              "version_aelter": False},
    "konfigurationen": ["Standard"], "aktiv": "Standard", "einheitensystem": 5, "tabelle": False,
    "eigenschaften": {"datei": {"Benennung": "Haupt"}, "konfiguration": {"Standard": {}}}, "externe_referenzen": [],
    "gleichungen": [], "variablen": {}, "features": [], "reihenfolge": {"Standard": []}, "masse": [], "neuaufbau": [],
    "skizzen": {}, "material": "", "materialien": {}, "geometrie": {},
    "komponenten": KOMPONENTEN, "verknuepfungen": VERKNUEPFUNGEN, "kollisionen": [{"paar": ["Deckel-1", "Platte-1"], "volumen": 1.5}],
    "bewegungen": BEWEGUNGEN, "dateien": DATEIEN, "warnungen": [], "messung": {"lesen": {"s": 1.2, "mb": 900}},
}


def baugruppen_aufnahme(**aenderungen) -> dict:
    """Eine Kopie der Baugruppen-Aufnahme; Schlüssel auf oberster Ebene werden ersetzt."""
    a = copy.deepcopy(AUFNAHME_BG)
    a.update(aenderungen)
    return a


def teil_aufnahme(rel: str, **aenderungen) -> dict:
    """Aufnahme eines Teils der Baugruppe (Format von Etappe 1): der Lagerdeckel mit dem relativen Pfad als Dateiname."""
    a = copy.deepcopy(AUFNAHME)
    a["datei"] = {"name": rel, "original": f"D:\\Kunde\\{rel}", "sha256": sha(rel), "versionen": ["18000[2025/268]"],
                  "version_aelter": False}
    a.update(aenderungen)
    return a


def datei_aufnahmen(ersatz: dict | None = None):
    """`datei_aufnahme(rel)` wie `lade_datei_aufnahme`: Lagerdeckel-Aufnahme je Datei; `ersatz` (rel → Aufnahme) ersetzt einzelne.
    Unbekannte Dateien werfen KeyError."""
    ersatz = ersatz or {}

    def lade(rel: str) -> dict:
        if rel not in DATEIEN:
            raise KeyError(rel)
        return copy.deepcopy(ersatz.get(rel) or teil_aufnahme(rel))

    return lade


# Änderungs-Spec mit Punkten an zwei Teilen, einem Haupt-Punkt und Baugruppen-Punkten; die Anker der neuen Verknüpfung sind Bauweg
SPEC = {
    "art": "aenderung",
    "name": "Haupt_Rev",
    "bestand": {"datei": HAUPT, "sha256": SHA_BG, "aufnahme": 1},
    "parameter": {"A_neu": 45, "ABSTAND_NEU": 12},
    "punkte": [
        {"id": "p1", "was": "Abstand Bohrung der Platte", "typ": "mass", "in_datei": "teile/Platte.SLDPRT", "mass": "D2@Skizze4",
         "alt": 40, "neu": "=A_neu"},
        {"id": "p2", "typ": "unterdruecken", "in_datei": "teile/Platte.SLDPRT", "feature": "Fase3"},
        {"id": "p3", "typ": "mass", "in_datei": "teile/Deckel.SLDPRT", "mass": "D2@Skizze4", "alt": 40, "neu": 41,
         "lage_folgen": ["Deckel-1"]},
        {"id": "s1", "typ": "eigenschaft", "name": "Revision", "neu": "B"},
        {"id": "k1", "typ": "komponente_neu", "quelle": {"normteil": "ISO 4762 M6x16"}},
        {"id": "v1", "typ": "verknuepfung_neu", "art": "abstand", "wert": "=ABSTAND_NEU",
         "a": {"komponente": "k1", "ebene": "oben"}, "b": {"komponente": "Gehaeuse-1", "ebene": "oben"}},
        {"id": "w1", "typ": "verknuepfung_wert", "verknuepfung": "Abstand1", "alt": 10, "neu": "=ABSTAND_NEU"},
    ],
    "bereiche": [
        {"punkte": ["p1"], "in_datei": "teile/Platte.SLDPRT", "box": {"min": [-50, -20, 0], "max": [-20, 40, 20]}},
        {"punkte": ["p2"], "in_datei": "teile/Platte.SLDPRT", "features": ["Fase3"]},
        {"punkte": ["p3"], "in_datei": "teile/Deckel.SLDPRT", "box": {"min": [-50, -20, 0], "max": [-20, 40, 20]}},
    ],
    "pruefung": {
        "masse_pruefen": [{"was": "Randabstand", "in_datei": "teile/Platte.SLDPRT",
                           "von": {"flaeche": {"nahe": [-50, 0, 10], "normale": [-1, 0, 0]}}, "zu": {"punkt": [-38, 15, 20]},
                           "soll": "=A_neu", "tol": 0.01}],
    },
}


NEUE_DATEI = "ISO4762M6x16.SLDPRT"
NEUE_KOMPONENTE = "ISO4762M6x16-1"


def komponente(datei: str, fixiert: bool = False, virtuell: bool = False) -> dict:
    """Eine Komponente im Format der Aufnahme (Standard-Lage, voll bestimmt)."""
    return _komp(datei, fixiert, virtuell)


def verknuepfung(typ: int, partner: list[str], **felder) -> dict:
    """Eine Verknüpfung im Format der Aufnahme (`wert`, `min_`, `max_`, `grenze`, `gesteuert`)."""
    return _mate(typ, partner, **felder)


def dateien_json() -> dict:
    """`dateien.json` der Aufnahme: die Hauptdatei (`haupt: true`) und jede Datei mit Original und SHA-256."""
    return {HAUPT: {"original": "D:\\Kunde\\Haupt.SLDASM", "sha256": SHA_BG, "haupt": True},
            **{rel: {"original": d["original"], "sha256": d["sha256"]} for rel, d in DATEIEN.items()}}


def lauf_shas(**geaendert) -> dict[str, str]:
    """rel → SHA-256 der Dateien im Lauf: wie die Bestandskopie, `geaendert` (rel → SHA-256 oder None) ersetzt einzelne."""
    shas = {rel: d["sha256"] for rel, d in dateien_json().items()}
    return {rel: geaendert.get(rel, sha) for rel, sha in shas.items()} | {k: v for k, v in geaendert.items() if k not in shas}


def nachher_zu_spec() -> tuple[dict, dict, dict]:
    """Der Lauf-Stand, den `SPEC` verlangt (Baugruppen-Punkte): neue Schraube `k1` mit Abstand `v1` zum Gehäuse, Abstand1 auf 12 mm,
    Deckel-1 durch `lage_folgen` leicht verschoben. Dazu `neue` und `ersetzt` des Protokolls."""
    a = baugruppen_aufnahme()
    a["komponenten"][NEUE_KOMPONENTE] = _komp(NEUE_DATEI)
    a["verknuepfungen"]["Abstand4"] = _mate(5, [NEUE_KOMPONENTE, "Gehaeuse-1"], wert=12.0)
    a["verknuepfungen"]["Abstand1"]["wert"] = 12.0
    a["komponenten"]["Deckel-1"]["transform"]["Standard"][9] += 0.0005
    return a, {"k1": [NEUE_KOMPONENTE]}, {}
