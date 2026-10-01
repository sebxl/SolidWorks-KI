"""Handler "normbohrung" – Bohrungsassistent (IFeatureManager.HoleWizard5, ISO) mit allen Positionen in einem Feature
(Spec 2c §3; Aufrufkette wie S9b Baustein 21, Positionen laut Spike S10 Frage 2).

Die erste Position wird per SelectByRay auf der Fläche gewählt; die übrigen kommen als Skizzenpunkte in die
Positionsskizze, die danach voll bestimmt wird (Lagemaße zum Ursprung, per Gleichung an Parameter). Gewinde immer
kosmetisch, Größen und Normmaße aus swki/wissen/bohrungsnormen.yaml. Instanzen 1, 2, … in Reihenfolge der Positionen;
ihre Achspunkte gehen ins Bauprotokoll (masse_pruefen).

Sonderfall Stiftloch "durch alles": HoleWizard5 liefert dafür nie ein Feature (S10 Frage 1); dieser Fall läuft über
FeatureManager.CreateDefinition(swFmHoleWzd) → InitializeHole → Vorselektion → CreateFeature.
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import ebene_aus_flaeche, modellpunkt, positionen_festlegen, richtung
from swki.compiler.topologie import loese_flaeche
from swki.spec.normen import (
    SW_ART, SW_BEFESTIGUNG, SW_END_BLIND, SW_END_DURCH_ALLES, SW_NORM, groesse_text, norm_von, normmasse,
)
from swki.verbindung import mm

SW_SCHRAUBE_NORMAL = 1  # swWzdHoleScrewClearanceTypes_e.swScrewClearanceNormal
SW_GEWINDE_KOSMETISCH = 2  # swWzdHoleCosmeticThreadTypes_e.swCosmeticThreadWithoutCallout
SW_GEWINDE_BLIND = 0  # swWzdHoleThreadEndCondition_e.swEndThreadTypeBLIND
SW_GEWINDE_DURCH = 1  # swWzdHoleThreadEndCondition_e.swEndThreadTypeTHROUGH_ALL
SW_SEL_FACES = 2  # swSelectType_e.swSelFACES
SW_FM_HOLE_WZD = 25  # swFeatureNameID_e.swFmHoleWzd (IFeatureManager.CreateDefinition, S10 Frage 1)
_STRAHL_MM = 1.0  # Start des Auswahlstrahls über der Fläche
_STRAHL_RADIUS_M = 0.0005


def hole_werte(art: str, gewindetiefe_m: float | None) -> list[float]:
    """Value1…Value12 von HoleWizard5 je Art (API-Hilfe, Remarks; −1 = Normwert/ungenutzt) – Abhängig von S10 Frage 1."""
    v = [-1.0] * 12
    if art == "gewinde":
        v[0] = -1.0 if gewindetiefe_m is None else gewindetiefe_m  # Tap Thread Depth
        v[6] = SW_GEWINDE_KOSMETISCH  # Cosmetic Thread Type
        v[7] = SW_GEWINDE_DURCH if gewindetiefe_m is None else SW_GEWINDE_BLIND  # Thread End Condition
    elif art in ("zylinderschraube", "senkschraube"):
        v[3] = SW_SCHRAUBE_NORMAL  # Screw Fit
    return v


def _stiftloch_durch(model, norm: str, masse: dict):
    """Stiftloch durch alles über CreateDefinition (HoleWizard5 liefert dafür nie ein Feature, S10 Frage 1).
    Die erste Position muss vorselektiert sein; das Feature liest danach FastenerType2 = −1 (akzeptiert)."""
    definition = model.FeatureManager.CreateDefinition(SW_FM_HOLE_WZD)
    definition.InitializeHole(
        SW_ART["stift"], SW_NORM[norm], SW_BEFESTIGUNG["stift"], masse["sw_groesse"], SW_END_DURCH_ALLES,
    )
    return model.FeatureManager.CreateFeature(definition)


@handler("normbohrung")
def normbohrung(ctx, f: dict) -> FeatureErgebnis:
    norm = norm_von(f)
    masse = normmasse(f["art"], f["groesse"], norm)
    if masse is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"normbohrung {f['id']}: Größe {groesse_text(f['groesse'])} fehlt in der "
                                               "Maßtabelle", schritt="feature")
    flaeche = loese_flaeche(ctx, f["flaeche"])
    se = ebene_aus_flaeche(flaeche)
    punkte = [modellpunkt(se.orientierung, ctx.wert(u), ctx.wert(v), se.lage) for u, v in f["positionen"]]
    n = flaeche.normale
    x, y, z = (mm(c + _STRAHL_MM * nc) for c, nc in zip(punkte[0], n))
    sw.auswahl_leeren(ctx.model)
    if not ctx.model.Extension.SelectByRay(x, y, z, -n[0], -n[1], -n[2], _STRAHL_RADIUS_M, SW_SEL_FACES, False, 0, 0):
        raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"normbohrung {f['id']}: Fläche an Position 1 nicht getroffen",
                        schritt="auswahl")
    durch = bool(f.get("durch"))
    if f["art"] == "stift" and durch:
        feature = _stiftloch_durch(ctx.model, norm, masse)
    else:
        gewindetiefe = ctx.m(f["gewindetiefe"]) if "gewindetiefe" in f else None
        feature = ctx.model.FeatureManager.HoleWizard5(
            SW_ART[f["art"]], SW_NORM[norm], SW_BEFESTIGUNG[f["art"]], masse["sw_groesse"],
            SW_END_DURCH_ALLES if durch else SW_END_BLIND, -1, 0.0 if durch else ctx.m(f["tiefe"]), -1,
            *hole_werte(f["art"], gewindetiefe),
            "", False, False, True, False, True, False,
        )
    sw.auswahl_leeren(ctx.model)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"normbohrung {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    positionen_festlegen(ctx, feature, se, f["positionen"], f"{f['id']}_positionen")
    sw.rebuild(ctx.model)
    anzahl = feature.GetDefinition.GetSketchPointCount
    if anzahl != len(f["positionen"]):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"normbohrung {f['id']}: {anzahl} statt {len(f['positionen'])} Positionen",
                        schritt="feature")
    return FeatureErgebnis([feature], richtung=richtung(se, True), punkte=punkte)
