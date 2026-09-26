"""S9b Baustein 14: Lineares Muster eines Schnitt-Features (1 und 2 Richtungen).

Quader 100 x 60 x 20 (Y 0..20), Saat: Bohrung r=4 durch alles bei (X=-40, Z=-20), 1005,31 mm³.
Richtung 1: Bodenkante Y=0/Z=+30 (LineParams-Richtung +X) oder Referenzachse (Ebene vorne ∩ oben).
Richtung 2: Kante X=+50/Y=0 (LineParams-Richtung -Z).
Wege: CreateDefinition(swFmLPattern=6) -> ILinearPatternFeatureData -> CreateFeature, und das obsolete
FeatureLinearPattern5 (22 Parameter). Positionen der Instanzen über Zylinderflächen des Körpers.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import (
    ebenen, flaeche_mit_normale, kasten_oben, letztes, modell_zu_skizze, schnitt, select_mark, start, teil,
    volumen_mm3,
)
from spikes.s9b_gemeinsam import dispatch_array, kanten_linie, whatswrong

SW_FM_LPATTERN = 6
BOHRUNG_MM3 = 1005.31


def bohrung(app, model, k, p, rad=0.004):
    deck = flaeche_mit_normale(k, (0.0, 1.0, 0.0))
    model.ClearSelection2(True)
    select_mark(model, deck, 0, append=False)
    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.AddToDB = True
    try:
        u, v, _ = modell_zu_skizze(app, sm.ActiveSketch, p)
        sm.CreateCircleByRadius(u, v, 0.0, rad)
    finally:
        sm.AddToDB = False
    sm.InsertSketch(True)
    sk = letztes(model)
    model.ClearSelection2(True)
    sk.Select2(False, 0)
    return schnitt(model, 1)


def bohrungs_xz(model) -> list:
    """(X, Z) in mm aller Zylinderflächen des Körpers. IBody2 hat Typinfo -> GetFaces() MIT ()."""
    out = []
    for body in model.GetBodies2(0, True) or ():
        for f in body.GetFaces() or ():
            s = f.GetSurface
            if s.IsCylinder:
                c = s.CylinderParams
                out.append((round(c[0] * 1000, 3), round(c[2] * 1000, 3)))
    return sorted(out)


def achse_x(model):
    """Referenzachse aus Ebene vorne ∩ Ebene oben (= Modell-X)."""
    ev = ebenen(model)
    model.ClearSelection2(True)
    select_mark(model, ev[0], 0, append=False)
    select_mark(model, ev[1], 0, append=True)
    ok = model.InsertAxis2(True)
    return ok, letztes(model)


def _kanten(k):
    ex = kanten_linie(k, (1, 0, 0), (None, 0.0, 0.030))[0]
    ez = kanten_linie(k, (0, 0, 1), (0.050, 0.0, None))[0]
    return ex, ez


def _lauf(app, r, fn) -> dict:
    with teil(app, r) as model:
        k = kasten_oben(model, 100, 60, 20)
        cut = bohrung(app, model, k, (-0.040, 0.020, -0.020))
        v0 = volumen_mm3(model)
        info: dict = {}
        try:
            f = fn(model, k, cut, info)
        except Exception as e:
            return {"fehler": repr(e), **info}
        return {"feature": f.Name if f else None, "typ": f.GetTypeName2 if f else None,
                "abnahme_mm3": round(v0 - volumen_mm3(model), 3),
                "instanzen_xz_mm": bohrungs_xz(model), "whatswrong": whatswrong(model), **info}


def cd_1dir_kante(model, k, cut, info):
    ex, _ = _kanten(k)
    info["kante_richtung"] = [round(x, 6) for x in ex.GetCurve.LineParams[3:6]]
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, ex, 1, append=False)       # Richtung 1
    select_mark(model, cut, 4, append=True)       # zu musterndes Feature
    data = fm.CreateDefinition(SW_FM_LPATTERN)
    data.D1TotalInstances = 4
    data.D1Spacing = 0.020
    return fm.CreateFeature(data)


def cd_1dir_umgekehrt(model, k, cut, info):
    ex, _ = _kanten(k)
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, ex, 1, append=False)
    select_mark(model, cut, 4, append=True)
    data = fm.CreateDefinition(SW_FM_LPATTERN)
    data.D1TotalInstances = 3
    data.D1Spacing = 0.020
    data.D1ReverseDirection = True                # -X: Instanzen außerhalb des Körpers
    return fm.CreateFeature(data)


def cd_1dir_achse(model, k, cut, info):
    ok, a = achse_x(model)
    info["achse"] = {"insertaxis2": ok, "name": a.Name, "typ": a.GetTypeName2}
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, a, 1, append=False)        # Referenzachse (Feature) mit Marke 1
    select_mark(model, cut, 4, append=True)
    data = fm.CreateDefinition(SW_FM_LPATTERN)
    data.D1TotalInstances = 4
    data.D1Spacing = 0.020
    return fm.CreateFeature(data)


def cd_2dir_ohne_reverse(model, k, cut, info):
    ex, ez = _kanten(k)
    info["kante2_richtung"] = [round(x, 6) for x in ez.GetCurve.LineParams[3:6]]
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, ex, 1, append=False)
    select_mark(model, ez, 2, append=True)        # Richtung 2
    select_mark(model, cut, 4, append=True)
    data = fm.CreateDefinition(SW_FM_LPATTERN)
    data.D1TotalInstances, data.D1Spacing = 4, 0.020
    data.D2TotalInstances, data.D2Spacing = 3, 0.020
    return fm.CreateFeature(data)


def cd_2dir(model, k, cut, info):
    ex, ez = _kanten(k)
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, ex, 1, append=False)
    select_mark(model, ez, 2, append=True)
    select_mark(model, cut, 4, append=True)
    data = fm.CreateDefinition(SW_FM_LPATTERN)
    data.D1TotalInstances, data.D1Spacing = 4, 0.020
    data.D2TotalInstances, data.D2Spacing = 3, 0.020
    data.D2ReverseDirection = True                # Kante zeigt -Z, gewünscht +Z
    f = fm.CreateFeature(data)
    dd = f.GetDefinition
    info["definition"] = {"D2TotalInstances": dd.D2TotalInstances, "IsDirection2Specified": dd.IsDirection2Specified,
                          "GetD1AxisType": dd.GetD1AxisType, "GetD2AxisType": dd.GetD2AxisType}
    return f


def cd_properties_ohne_selektion(model, k, cut, info):
    ex, _ = _kanten(k)
    fm = model.FeatureManager
    model.ClearSelection2(True)
    data = fm.CreateDefinition(SW_FM_LPATTERN)
    data.D1Axis = ex
    data.PatternFeatureArray = dispatch_array([cut])
    data.D1TotalInstances, data.D1Spacing = 4, 0.020
    info["d1axis_gelesen"] = repr(data.D1Axis)
    info["featurecount"] = data.GetPatternFeatureCount
    return fm.CreateFeature(data)


def lp5_1dir(model, k, cut, info):
    ex, _ = _kanten(k)
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, ex, 1, append=False)
    select_mark(model, cut, 4, append=True)
    return fm.FeatureLinearPattern5(4, 0.020, 1, 0.0, False, False, "NULL", "NULL", False, False, False, False,
                                    False, False, True, True, False, False, 0.0, 0.0, False, False)


def lp5_2dir(model, k, cut, info):
    ex, ez = _kanten(k)
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, ex, 1, append=False)
    select_mark(model, ez, 2, append=True)
    select_mark(model, cut, 4, append=True)
    return fm.FeatureLinearPattern5(4, 0.020, 3, 0.020, False, True, "NULL", "NULL", False, False, False, False,
                                    False, False, True, True, False, False, 0.0, 0.0, False, False)


def pruefen() -> dict:
    r, app = start()
    d: dict = {"bohrung_mm3": BOHRUNG_MM3}
    for fn in (cd_1dir_kante, cd_1dir_umgekehrt, cd_1dir_achse, cd_2dir_ohne_reverse, cd_2dir,
               cd_properties_ohne_selektion, lp5_1dir, lp5_2dir):
        d[fn.__name__] = _lauf(app, r, fn)
    return d


if __name__ == "__main__":
    lauf("s9b_b14_lineares_muster", pruefen)
