"""S9b Baustein 15: Kreismuster eines Schnitt-Features um eine Achse.

Scheibe R50 x 10 (auf Ebene oben, Y 0..10), Saat: Bohrung r=4 durch alles bei (X=30, Z=0),
Einzelvolumen π·16·10 = 502,65 mm³. Achse: Referenzachse aus Ebene vorne ∩ Ebene rechts (= Modell-Y,
InsertAxis2) oder Zylinder-Mantelfläche der Scheibe.
Wege: CreateDefinition(swFmCirPattern=5) -> ICircularPatternFeatureData -> CreateFeature, und das obsolete
FeatureCircularPattern5 (14 Parameter). Instanzen über Zylinderflächen des Körpers (X, Z, Winkel).
"""

import math

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import (
    ebenen, extrusion_blind, flaeche_mit_normale, letztes, modell_zu_skizze, schnitt, select_mark,
    skizze_auf_ebene, skizze_ende_und_waehlen, start, teil, volumen_mm3,
)
from spikes.s9b_gemeinsam import whatswrong

SW_FM_CIRPATTERN = 5
BOHRUNG_MM3 = round(math.pi * 16 * 10, 3)


def scheibe(model):
    sm = skizze_auf_ebene(model, ebenen(model)[1])
    sm.CreateCircleByRadius(0.0, 0.0, 0.0, 0.050)
    skizze_ende_und_waehlen(model)
    return extrusion_blind(model, 0.010)


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


def bohrungen(model) -> list:
    """Kleine Zylinder (r < 10 mm): (X, Z, Winkel° um +Y von +X aus, atan2(-Z, X))."""
    out = []
    for body in model.GetBodies2(0, True) or ():
        for f in body.GetFaces() or ():
            s = f.GetSurface
            if s.IsCylinder:
                c = s.CylinderParams
                if c[6] < 0.010:
                    x, z = c[0] * 1000, c[2] * 1000
                    out.append((round(x, 3), round(z, 3), round(math.degrees(math.atan2(-z, x)) % 360, 3)))
    return sorted(out, key=lambda t: t[2])


def achse_y(model):
    ev = ebenen(model)
    model.ClearSelection2(True)
    select_mark(model, ev[0], 0, append=False)   # Ebene vorne
    select_mark(model, ev[2], 0, append=True)    # Ebene rechts
    ok = model.InsertAxis2(True)
    return ok, letztes(model)


def _lauf(app, r, fn) -> dict:
    with teil(app, r) as model:
        k = scheibe(model)
        cut = bohrung(app, model, k, (0.030, 0.010, 0.0))
        v0 = volumen_mm3(model)
        info: dict = {}
        try:
            f = fn(model, k, cut, info)
        except Exception as e:
            return {"fehler": repr(e), **info}
        return {"feature": f.Name if f else None, "typ": f.GetTypeName2 if f else None,
                "abnahme_mm3": round(v0 - volumen_mm3(model), 3), "instanzen_x_z_winkel": bohrungen(model),
                "whatswrong": whatswrong(model), **info}


def _cd(model, achse, cut, n, spacing, equal, reverse=None, info=None, spacing_zuerst=False):
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, achse, 1, append=False)   # Achse Marke 1
    select_mark(model, cut, 4, append=True)      # Feature Marke 4
    data = fm.CreateDefinition(SW_FM_CIRPATTERN)
    data.TotalInstances = n
    if spacing_zuerst:                            # Fehlvariante: EqualSpacing-Put setzt Spacing zurück
        data.Spacing = spacing
        data.EqualSpacing = equal
    else:
        data.EqualSpacing = equal                 # ZUERST EqualSpacing ...
        data.Spacing = spacing                    # ... dann Spacing (rad; bei EqualSpacing = Gesamtwinkel)
    if reverse is not None:
        data.ReverseDirection = reverse
    if info is not None:
        info["data_vor_createfeature"] = {"TotalInstances": data.TotalInstances, "Spacing": data.Spacing,
                                          "EqualSpacing": data.EqualSpacing}
    return fm.CreateFeature(data)


def cd_achse_gleichmaessig(model, k, cut, info):
    ok, a = achse_y(model)
    info["achse"] = {"insertaxis2": ok, "name": a.Name, "typ": a.GetTypeName2}
    return _cd(model, a, cut, 6, 2 * math.pi, True)


def cd_achse_teilung_30(model, k, cut, info):
    _, a = achse_y(model)
    return _cd(model, a, cut, 3, math.radians(30), False, info=info)


def cd_achse_teilung_30_spacing_zuerst(model, k, cut, info):
    _, a = achse_y(model)
    return _cd(model, a, cut, 3, math.radians(30), False, info=info, spacing_zuerst=True)


def cd_achse_teilung_30_reverse(model, k, cut, info):
    _, a = achse_y(model)
    return _cd(model, a, cut, 3, math.radians(30), False, reverse=True, info=info)


def cd_achse_gleichmaessig_60_gesamt(model, k, cut, info):
    _, a = achse_y(model)
    return _cd(model, a, cut, 3, math.radians(60), True, info=info)


def cd_zylinderflaeche(model, k, cut, info):
    mantel = next(f for f in k.GetFaces if f.GetSurface.IsCylinder)
    return _cd(model, mantel, cut, 4, 2 * math.pi, True)


def cp5_achse(model, k, cut, info):
    _, a = achse_y(model)
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, a, 1, append=False)
    select_mark(model, cut, 4, append=True)
    return fm.FeatureCircularPattern5(6, 2 * math.pi, False, "NULL", False, True, False, False, False, False,
                                      1, 0.0, "NULL", False)


def cp5_teilung_30(model, k, cut, info):
    _, a = achse_y(model)
    fm = model.FeatureManager
    model.ClearSelection2(True)
    select_mark(model, a, 1, append=False)
    select_mark(model, cut, 4, append=True)
    return fm.FeatureCircularPattern5(3, math.radians(30), False, "NULL", False, False, False, False, False, False,
                                      1, 0.0, "NULL", False)


def pruefen() -> dict:
    r, app = start()
    d: dict = {"bohrung_mm3": BOHRUNG_MM3, "winkel_konvention": "atan2(-Z, X) = Drehung um +Y (rechte Hand)"}
    for fn in (cd_achse_gleichmaessig, cd_achse_gleichmaessig_60_gesamt, cd_achse_teilung_30,
               cd_achse_teilung_30_spacing_zuerst, cd_achse_teilung_30_reverse, cd_zylinderflaeche, cp5_achse,
               cp5_teilung_30):
        d[fn.__name__] = _lauf(app, r, fn)
    return d


if __name__ == "__main__":
    lauf("s9b_b15_kreismuster", pruefen)
