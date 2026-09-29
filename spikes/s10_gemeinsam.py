"""Gemeinsame Hilfen für Spike S10 (Stufe 2c: Normbohrungen, runde Konturen, Endbedingungen). Kein Produktionscode.

Baut auf spikes/s9a_gemeinsam.py und spikes/s9b_gemeinsam.py auf (Late Binding erzwungen, eigenes Teil, Marken).
Enum-Werte laut `swki api enum` (2026-09-29); Belegung von Value1…Value12 laut API-Hilfe zu HoleWizard5 (Remarks).
"""

import math
from pathlib import Path

from swki.compiler.kontext import Kontext
from swki.konfig import lade_rechner

SW_STANDARD_ISO = 8  # swWzdHoleStandards_e.swStandardISO
SW_WZD = {"zylinderschraube": 0, "senkschraube": 1, "stift": 2, "gewinde": 4}  # swWzdGeneralHoleTypes_e
SW_BEFESTIGUNG = {  # swWzdHoleStandardFastenerTypes_e
    "zylinderschraube": 139,  # swStandardISOSocketHeadCap
    "senkschraube": 140,  # swStandardISOSocketCTSKFlatHead
    "stift": 710,  # swStandardISODowelHole
    "gewinde": 147,  # swStandardISOTappedHole
}
SW_END_BLIND, SW_END_DURCH_ALLES = 0, 1  # swEndConditions_e
SW_SCHRAUBE_NORMAL = 1  # swWzdHoleScrewClearanceTypes_e.swScrewClearanceNormal
SW_KOSMETISCH_OHNE_BESCHRIFTUNG = 2  # swWzdHoleCosmeticThreadTypes_e.swCosmeticThreadWithoutCallout
SW_GEWINDE_BLIND, SW_GEWINDE_DURCH = 0, 1  # swWzdHoleThreadEndCondition_e
SW_SEL_FACES = 2  # swSelectType_e.swSelFACES
SW_FM_HOLE_WZD = 25  # swFeatureNameID_e.swFmHoleWzd (CreateDefinition)
DICKE_MM = 30.0  # Prüfblock 60 × 60 × 30 mm (Y 0…30), Bohrungen von der Deckfläche
ARBEIT_S10 = lade_rechner().arbeitsordner / "stufe0" / "s10"
_DATEN = (
    "Type", "Standard2", "FastenerType2", "FastenerSize", "EndCondition", "Depth", "HoleDepth", "HoleDiameter",
    "Diameter", "ThreadDepth", "ThreadDiameter", "ThreadEndCondition", "TapDrillDiameter", "TapDrillDepth",
    "CounterBoreDiameter", "CounterBoreDepth", "CounterSinkDiameter", "CounterSinkAngle", "NearCounterSinkDiameter",
    "ThruHoleDiameter", "ThruHoleDepth", "DrillAngle", "HoleFit", "CosmeticThreadType", "GetSketchPointCount",
)


def werte(art: str, gewindetiefe_m: float | None) -> list[float]:
    """Value1…Value12 von HoleWizard5 je Art (API-Hilfe, Remarks; −1 = Normwert/ungenutzt)."""
    v = [-1.0] * 12
    if art == "gewinde":
        v[0] = -1.0 if gewindetiefe_m is None else gewindetiefe_m  # Tap Thread Depth
        v[6] = SW_KOSMETISCH_OHNE_BESCHRIFTUNG  # Cosmetic Thread Type
        v[7] = SW_GEWINDE_DURCH if gewindetiefe_m is None else SW_GEWINDE_BLIND  # Thread End Condition
    elif art in ("zylinderschraube", "senkschraube"):
        v[3] = SW_SCHRAUBE_NORMAL  # Screw Fit
    return v


def bohrung(model, art, groesse, positionen_mm, tiefe_mm=None, gewindetiefe_mm=None, deckflaeche_y_mm=DICKE_MM):
    """Bohrungsassistent von der Deckfläche (Normale +Y) an den Positionen (x, z) in mm; jede Position per SelectByRay
    mit Marke 0 (API-Hilfe HoleWizard5: „SelectByRay with Mark = 0 for each location“). tiefe_mm None = durch alles."""
    model.ClearSelection2(True)
    y = (deckflaeche_y_mm + 1.0) / 1000
    treffer = [
        model.Extension.SelectByRay(x / 1000, y, z / 1000, 0.0, -1.0, 0.0, 0.0005, SW_SEL_FACES, i > 0, 0, 0)
        for i, (x, z) in enumerate(positionen_mm)
    ]
    if art == "stift" and tiefe_mm is None:
        # Abweichung vom Plan (S10 Frage 1): HoleWizard5 mit swWzdHole (Stiftloch) und Endbedingung „durch alles“ liefert
        # immer None (auch bei Maßkombinationen −1/0/Tiefe, Durchmesser, Screw Fit); über CreateDefinition +
        # InitializeHole + CreateFeature geht dieselbe Bohrung (Vorselektion wie bei HoleWizard5). Nachteil: das Feature
        # liest danach FastenerType2 = −1 (nicht 710) und Type 25 (swHoleThru); FastenerType2 lässt sich per Late Binding
        # nicht nachsetzen („can not be set“). Erkennbar bleibt es an FastenerSize "Ø<d>.0" und Type 25.
        d = model.FeatureManager.CreateDefinition(SW_FM_HOLE_WZD)
        d.InitializeHole(SW_WZD[art], SW_STANDARD_ISO, SW_BEFESTIGUNG[art], groesse, SW_END_DURCH_ALLES)
        f = model.FeatureManager.CreateFeature(d)
    else:
        f = model.FeatureManager.HoleWizard5(
            SW_WZD[art], SW_STANDARD_ISO, SW_BEFESTIGUNG[art], groesse,
            SW_END_DURCH_ALLES if tiefe_mm is None else SW_END_BLIND, -1,
            0.0 if tiefe_mm is None else tiefe_mm / 1000, -1,
            *werte(art, None if gewindetiefe_mm is None else gewindetiefe_mm / 1000),
            "", False, False, True, False, True, False,
        )
    model.ClearSelection2(True)
    return treffer, f


def unterfeatures(f) -> list[dict]:
    """Unterfeatures (Positions-/Profilskizze, kosmetisches Gewinde) mit Bestimmtheit, Punkt- und Segmentzahl."""
    out, s = [], f.GetFirstSubFeature
    while s is not None:
        eintrag = {"name": s.Name, "typ": s.GetTypeName2}
        if eintrag["typ"] == "ProfileFeature":
            sk = s.GetSpecificFeature2
            eintrag.update(status=sk.GetConstrainedStatus, punkte=len(sk.GetSketchPoints2 or ()),
                           segmente=len(sk.GetSketchSegments or ()))
        out.append(eintrag)
        s = s.GetNextSubFeature
    return out


def geometrie(f) -> dict:
    """Zylinder- und Kegelflächen des Features (mm): Radius, Achslage (x, z), Box [xmin, ymin, zmin, xmax, ymax, zmax]."""
    zylinder, kegel = [], []
    for fc in f.GetFaces or ():
        s = fc.GetSurface
        box = [round(c * 1000, 4) for c in fc.GetBox]
        if s.IsCylinder:
            c = s.CylinderParams
            zylinder.append({"r": round(c[6] * 1000, 4), "achse_xz": [round(c[0] * 1000, 4), round(c[2] * 1000, 4)],
                             "box": box})
        elif s.IsCone:
            kegel.append({"params": [round(x, 6) for x in s.ConeParams], "box": box})
    return {"zylinder": zylinder, "kegel": kegel}


def daten(f) -> dict:
    """IWizardHoleFeatureData2 über IFeature.GetDefinition (nullargumentig, ohne "()"); Längen roh in Metern."""
    d = f.GetDefinition
    out = {}
    for name in _DATEN:
        try:
            out[name] = getattr(d, name)
        except Exception as e:  # Spike: jeden Lesefehler festhalten
            out[name] = f"FEHLER {e!r}"
    return out


def kontext(app, model, parameter: dict | None = None) -> Kontext:
    """Baukontext für Produktionshilfen (Skizzierer, skizziere, verknuepfe) im Spike-Teil."""
    return Kontext(app, model, {"parameter": parameter or {}}, Path("s10.yaml"), 0.1)


def soll_volumen(art: str, m: dict, tiefe: float | None, dicke: float, spitze_grad: float = 118.0) -> float:
    """Erwartetes Volumen (mm³) einer Normbohrung – dieselbe Formel wie geometrie.normbohrung_volumen (Task 4):
    Tiefe = zylindrischer Teil ab der Fläche, darunter bei blind die Bohrspitze; Senkungen von der Fläche aus."""
    d = m.get("kernloch") or m.get("durchgang") or m["durchmesser"]
    v = math.pi * d**2 / 4 * (dicke if tiefe is None else tiefe)
    if tiefe is not None:
        v += math.pi * d**2 / 12 * (d / 2) / math.tan(math.radians(spitze_grad) / 2)
    if art == "zylinderschraube":
        v += math.pi * (m["senkung_d"] ** 2 - d**2) / 4 * m["senkung_t"]
    elif art == "senkschraube":
        ds = m["senkung_d"]
        h = (ds - d) / 2 / math.tan(math.radians(m["senkwinkel"]) / 2)
        v += math.pi * h / 12 * (ds**2 + ds * d + d**2) - math.pi * d**2 / 4 * h
    return v
