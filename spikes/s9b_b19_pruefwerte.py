"""S9b Baustein 19: Prüfwerte.

Quader 100 x 60 x 20 (Y 0..20), Material 1.2312 (7850 kg/m³), zwei Bohrungen r=4 durch alles bei
(X=-30, Z=-15) und (X=30, Z=15) -> Soll-Achsabstand sqrt(60² + 30²) = 67,082 mm.
Soll: V = 120000 - 2·π·16·20 = 117989,381 mm³; m = V·7,85e-6 kg/mm³.
Geprüft: CreateMassProperty2 (UseSystemUnits True/False), GetPartBox, Achsabstand aus CylinderParams
(und IMeasure.CenterDistance), Bestimmtheitsstatus aller Skizzen im Baum, Rebuild-Fehlerzahl.
"""

import math

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import kasten_oben, partbox_mm, start, teil
from spikes.s9b_b14_lineares_muster import bohrung
from spikes.s9b_gemeinsam import dispatch_array, whatswrong
from swki.verbindung import callout_leer

SOLL_V = 120000 - 2 * math.pi * 16 * 20


def massewerte(model, system: bool, recalculate: bool) -> dict:
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = system
    if recalculate:
        mp.Recalculate                      # ohne (): nullargumentig, wird beim Attributzugriff ausgeführt
    return {"UseSystemUnits": system, "recalculate": recalculate, "volumen": mp.Volume,
            "oberflaeche": mp.SurfaceArea, "masse": mp.Mass, "dichte": mp.Density,
            "schwerpunkt": list(mp.CenterOfMass)}


def zylinder_achsen(feat) -> list:
    out = []
    for f in feat.GetFaces or ():
        s = f.GetSurface
        if s.IsCylinder:
            ox, oy, oz, ax, ay, az, r = s.CylinderParams
            out.append({"face": f, "o": (ox, oy, oz), "a": (ax, ay, az), "r": r})
    return out


def achsabstand(z1, z2) -> float:
    """Abstand paralleler Achsen: |(o2 - o1) x a1| (a1 Einheitsvektor), in m."""
    d = [z2["o"][i] - z1["o"][i] for i in range(3)]
    a = z1["a"]
    c = (d[1] * a[2] - d[2] * a[1], d[2] * a[0] - d[0] * a[2], d[0] * a[1] - d[1] * a[0])
    return math.sqrt(sum(x * x for x in c))


def skizzen_status(model) -> list:
    out, f = [], model.FirstFeature
    while f is not None:
        if f.GetTypeName2 == "ProfileFeature":
            sk = f.GetSpecificFeature2
            out.append({"name": f.Name, "status": sk.GetConstrainedStatus})
        f = f.GetNextFeature
    return out


def pruefen() -> dict:
    r, app = start()
    d: dict = {"soll_volumen_mm3": round(SOLL_V, 3), "soll_masse_kg": round(SOLL_V * 7.85e-6, 6),
               "soll_achsabstand_mm": round(math.hypot(60, 30), 4)}
    with teil(app, r) as model:
        k = kasten_oben(model, 100, 60, 20)
        b1 = bohrung(app, model, k, (-0.030, 0.020, -0.015))
        b2 = bohrung(app, model, k, (0.030, 0.020, 0.015))
        model.SetMaterialPropertyName2("", "SolidWorks DIN Materials", "1.2312 (40CrMnMoS8-6)")
        d["masse_system"] = massewerte(model, True, False)
        d["masse_dokument_ohne_recalculate"] = massewerte(model, False, False)
        d["masse_dokument_mit_recalculate"] = massewerte(model, False, True)
        d["partbox_mm"] = partbox_mm(model)
        z1, z2 = zylinder_achsen(b1)[0], zylinder_achsen(b2)[0]
        d["zylinder"] = [{"o_mm": [round(x * 1000, 4) for x in z["o"]], "a": [round(x, 6) for x in z["a"]],
                          "r_mm": round(z["r"] * 1000, 4)} for z in (z1, z2)]
        d["achsabstand_cylinderparams_mm"] = round(achsabstand(z1, z2) * 1000, 6)
        try:
            ms = model.Extension.CreateMeasure
            ms.Calculate(dispatch_array([z1["face"], z2["face"]]))
            d["imeasure_ohne_flag"] = "kein Fehler"
        except Exception as e:
            d["imeasure_ohne_flag"] = repr(e)
        ms = model.Extension.CreateMeasure
        ms._FlagAsMethod("Calculate")
        ok = ms.Calculate(dispatch_array([z1["face"], z2["face"]]))
        d["imeasure"] = {"calculate": ok, "center_distance_mm": round(ms.CenterDistance * 1000, 6),
                         "distance_mm": round(ms.Distance * 1000, 6), "is_parallel": ms.IsParallel}
        d["skizzen_status"] = skizzen_status(model)
        # vorhandene Skizze zum Bearbeiten öffnen: EditSketch ohne () liefert nur eine gebundene Methode
        sk_feat = model.FeatureByPositionReverse(1)  # Skizze der zweiten Bohrung
        model.ClearSelection2(True)
        sk_feat.Select2(False, 0)
        x = model.EditSketch
        d["editsketch_ohne_klammern"] = {"typ": type(x).__name__, "active_sketch": model.SketchManager.ActiveSketch is not None}
        # Weg: Skizze selektieren + InsertSketch(True) öffnet sie
        model.SketchManager.InsertSketch(True)
        d["insertsketch_oeffnet"] = model.SketchManager.ActiveSketch is not None
        d["fullydefine"] = model.SketchManager.FullyDefineSketch(True, True, 1023, True, 1, callout_leer(), 1,
                                                                 callout_leer(), 1, 1)
        model.SketchManager.InsertSketch(True)
        d["skizzen_status_danach"] = skizzen_status(model)
        d["rebuild"] = model.EditRebuild3
        d["whatswrong"] = whatswrong(model)
    return d


if __name__ == "__main__":
    lauf("s9b_b19_pruefwerte", pruefen)
