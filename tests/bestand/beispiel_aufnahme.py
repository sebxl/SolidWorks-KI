"""Attrappe einer Bestandsaufnahme (`bestand.json`, Plan Task 4) für die Tests ohne SolidWorks.

Gesteuert: `D1@Skizze1` über die Variable `L`, `D3@Skizze2` über `"D1@Skizze1" + 5`, `D8@Skizze9` über die Tabelle.
Verknüpft: `D1@S5` und `D2@S6` (Gruppe `Spalt`). Frei: `D2@Skizze4` (in Variante B nicht lesbar). Getrieben: `D7@Skizze9`.
Baum: Skizze4 → Bohrung2 → Fase3 → Verrundung1; Schnitt-Linear1 ist eine Fläche zum Ankern.
"""

import copy

SHA = "9a1c" * 16


def _mass(name, feature, werte, zustand="treibend", quelle=None, gruppe=None):
    return {"name": name, "feature": feature, "werte": werte, "einheit": "mm", "zustand": zustand, "quelle": quelle,
            "gruppe": gruppe, "punkte": [[0.0, 0.0, 0.0]]}


def _feature(name, typ, eltern=(), kinder=()):
    return {"name": name, "typ": typ, "eltern": list(eltern), "kinder": list(kinder),
            "unterdrueckt": {"Standard": False, "Variante B": False}, "tabelle": False}


AUFNAHME = {
    "version": 1, "sw_jahr": 2025,
    "datei": {"name": "Lagerdeckel.SLDPRT", "original": "D:\\Kunde\\Lagerdeckel.SLDPRT", "sha256": SHA,
              "versionen": ["18000[2025/268]"], "version_aelter": False},
    "konfigurationen": ["Standard", "Variante B"], "aktiv": "Standard",
    "material": "1.0038", "materialien": {"Standard": "1.0038", "Variante B": "1.0038"}, "eigenschaften": {"datei": {"Benennung": "Lagerdeckel"}, "konfiguration": {"Standard": {}}},
    "externe_referenzen": [],
    "gleichungen": [
        {"index": 0, "text": '"L"= 100', "links": "L", "global": True},
        {"index": 1, "text": '"D1@Skizze1" = "L"', "links": "D1@Skizze1", "global": False},
        {"index": 2, "text": '"D3@Skizze2" = "D1@Skizze1" + 5', "links": "D3@Skizze2", "global": False},
    ],
    "variablen": {"L": 100.0},
    "features": [
        _feature("Skizze1", "ProfileFeature", kinder=["Aufsatz"]),
        _feature("Aufsatz", "Boss", eltern=["Skizze1"]),
        _feature("Skizze4", "ProfileFeature", kinder=["Bohrung2"]),
        _feature("Bohrung2", "Cut", eltern=["Skizze4"], kinder=["Fase3"]),
        _feature("Fase3", "Chamfer", eltern=["Bohrung2"], kinder=["Verrundung1"]),
        _feature("Verrundung1", "Fillet", eltern=["Fase3"]),
        _feature("Schnitt-Linear1", "Cut"),
    ],
    "skizzen": {"Skizze1": 3, "Skizze4": 3},
    "masse": [
        _mass("D1@Skizze1", "Skizze1", {"Standard": 100.0, "Variante B": 100.0}, "gesteuert",
              {"art": "variable", "name": "L"}),
        _mass("D3@Skizze2", "Skizze2", {"Standard": 105.0, "Variante B": 105.0}, "gesteuert",
              {"art": "gleichung", "name": "D3@Skizze2"}),
        _mass("D1@S5", "S5", {"Standard": 8.0, "Variante B": 8.0}, gruppe="Spalt"),
        _mass("D2@S6", "S6", {"Standard": 8.0, "Variante B": 8.0}, gruppe="Spalt"),
        _mass("D2@Skizze4", "Skizze4", {"Standard": 40.0, "Variante B": None}),
        _mass("D5@Skizze5", "Skizze5", {"Standard": 12.0, "Variante B": 15.0}),
        _mass("D7@Skizze9", "Skizze9", {"Standard": 3.0, "Variante B": 3.0}, "getrieben"),
        _mass("D8@Skizze9", "Skizze9", {"Standard": 4.0, "Variante B": 4.0}, "gesteuert",
              {"art": "tabelle", "name": None}),
    ],
    "neuaufbau": [],
    "geometrie": {"Standard": {"koerper": 1, "volumen": 12345.6, "box": [0, 0, 0, 1, 1, 1], "schwerpunkt": [0, 0, 0]}},
    "tabelle": False,
}


def aufnahme(**aenderungen) -> dict:
    """Eine Kopie der Attrappe; Schlüssel auf oberster Ebene werden ersetzt."""
    a = copy.deepcopy(AUFNAHME)
    a.update(aenderungen)
    return a
