"""Globale Variablen (Parameter), Material und benutzerdefinierte Eigenschaften eines Teils (Spike S9a/S9b)."""

import xml.etree.ElementTree as ET
from pathlib import Path

from swki.compiler.fehler import GLEICHUNG_FEHLER, MATERIAL_UNBEKANNT, BauFehler
from swki.verbindung import byref_bool, byref_str

SW_CUSTOM_INFO_TEXT = 30  # swCustomInfoType_e.swCustomInfoText
SW_CUSTOM_PROPERTY_REPLACE_VALUE = 2  # swCustomPropertyAddOption_e
ERSTELLER = "SolidWorks-KI"


def globale_variablen(model, parameter: dict) -> None:
    """Jeder Parameter wird eine SW-Gleichung "Name" = Wert (Dokumenteinheit mm bzw. Grad, Spike S9a Baustein 5)."""
    gleichungen = model.GetEquationMgr
    for name, wert in parameter.items():
        if gleichungen.Add2(-1, f'"{name}" = {wert!r}', True) < 0:
            raise BauFehler(GLEICHUNG_FEHLER, f"Globale Variable {name} = {wert} abgelehnt", schritt="parameter")


def material_passt(ist: str, soll: str) -> bool:
    """"1.2312" passt zu "1.2312 (40CrMnMoS8-6)" (Name in der SW-Materialdatenbank)."""
    return ist == soll or ist.startswith(f"{soll} (")


def materialien(datei: Path) -> list[str]:
    """Materialnamen einer *.sldmat (XML, UTF-16 mit BOM – als Bytes parsen)."""
    return [m.get("name") for m in ET.fromstring(datei.read_bytes()).iter("material")]


def finde_material(datenbanken: list[str], soll: str) -> tuple[str, str]:
    """(Datenbankpfad, voller Materialname); exakter Name vor eindeutigem Präfix-Treffer."""
    treffer = [(db, name) for db in datenbanken if Path(db).exists() for name in materialien(Path(db))
               if material_passt(name, soll)]
    exakt = [t for t in treffer if t[1] == soll]
    if exakt:
        return exakt[0]
    namen = sorted({name for _, name in treffer})
    if len(namen) == 1:
        return treffer[0]
    grund = f"mehrdeutig: {namen}" if namen else "in keiner Materialdatenbank gefunden"
    raise BauFehler(MATERIAL_UNBEKANNT, f"Material {soll!r} {grund}", schritt="material")


def setze_material(app, model, soll: str) -> str:
    datenbank, name = finde_material(list(app.GetMaterialDatabases or ()), soll)
    model.SetMaterialPropertyName2("", datenbank, name)  # liefert immer None (S9b) → zurücklesen
    gesetzt = model.GetMaterialPropertyName2("", byref_str())
    if gesetzt != name:
        raise BauFehler(MATERIAL_UNBEKANNT, f"Material {name!r} ließ sich nicht zuweisen", schritt="material")
    return name


def eigenschaften_fuer(spec: dict, auftrag: str) -> dict[str, str]:
    werte = {"Ersteller": ERSTELLER, "Auftrag": auftrag}
    if "material" in spec:
        werte["Material"] = spec["material"]
    werte.update(spec.get("eigenschaften", {}))
    return werte


def setze_eigenschaften(model, werte: dict[str, str]) -> None:
    verwalter = model.Extension.CustomPropertyManager("")
    for name, wert in werte.items():
        if verwalter.Add3(name, SW_CUSTOM_INFO_TEXT, wert, SW_CUSTOM_PROPERTY_REPLACE_VALUE) != 0:
            raise BauFehler(GLEICHUNG_FEHLER, f"Eigenschaft {name} ließ sich nicht setzen", schritt="eigenschaften")


def lies_eigenschaften(model) -> dict[str, str]:
    verwalter = model.Extension.CustomPropertyManager("")
    werte = {}
    for name in verwalter.GetNames or ():
        wert, aufgeloest, war_cache, verknuepft = byref_str(), byref_str(), byref_bool(), byref_bool()
        verwalter.Get6(name, False, wert, aufgeloest, war_cache, verknuepft)
        werte[name] = aufgeloest.value
    return werte
