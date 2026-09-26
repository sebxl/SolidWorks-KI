"""S9a Baustein 9: einfache Bohrungen per Kreis-Skizze + Schnitt, Flachsenkung, Achsen lesen.

Quader 100 x 60 x 20 (Y 0..20). Deckfläche: 3 Kreise r=4 an Modellpositionen
P1 (-30, 20, -15), P2 (0, 20, -15), P3 (30, 20, 15) -> Schnitt durch alles (Variante blind 10 in
eigenem Teil). Flachsenkung: zweite Skizze auf Deckfläche, Kreise r=7 konzentrisch -> Schnitt blind 4.
Achsen aus CylinderParams; Reihenfolge vor/nach ForceRebuild3 und in einem zweiten Teil.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import (
    flaeche_mit_normale, kasten_oben, letztes, modell_zu_skizze, schnitt, select_mark, start, teil,
    volumen_mm3, zylinder,
)

POS = [(-0.030, 0.020, -0.015), (0.0, 0.020, -0.015), (0.030, 0.020, 0.015)]


def _kreise_auf_flaeche(app, model, flaeche, radius_m):
    model.ClearSelection2(True)
    select_mark(model, flaeche, 0, append=False)
    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.AddToDB = True
    try:
        for p in POS:
            u, v, _ = modell_zu_skizze(app, sm.ActiveSketch, p)
            sm.CreateCircleByRadius(u, v, 0.0, radius_m)
    finally:
        sm.AddToDB = False
    sm.InsertSketch(True)
    sk = letztes(model)
    model.ClearSelection2(True)
    sk.Select2(False, 0)
    return sk


def _bohrteil(app, model, t1, tiefe):
    k = kasten_oben(model, 100, 60, 20)
    deck = flaeche_mit_normale(k, (0.0, 1.0, 0.0))
    _kreise_auf_flaeche(app, model, deck, 0.004)
    f = schnitt(model, t1=t1, tiefe_m=tiefe)
    return k, f


def pruefen() -> dict:
    r, app = start()
    d: dict = {"hinweis": "zylinder = [origin x,y,z mm, axis x,y,z, radius mm] je Zylinderfläche in GetFaces-Reihenfolge"}
    with teil(app, r) as model:
        k, f = _bohrteil(app, model, 1, 0.0)
        d["durch_alles"] = {"feature": f.Name, "zylinder": zylinder(f), "volumen_mm3": volumen_mm3(model)}
        model.ForceRebuild3(False)
        d["durch_alles_nach_forcerebuild"] = zylinder(f)
        deck = flaeche_mit_normale(k, (0.0, 1.0, 0.0))
        d["deckflaeche_nach_bohrung_gefunden"] = deck is not None
        _kreise_auf_flaeche(app, model, deck, 0.007)
        f2 = schnitt(model, t1=0, tiefe_m=0.004)
        d["flachsenkung"] = {"feature": f2.Name if f2 else None, "zylinder": zylinder(f2) if f2 else None,
                             "volumen_mm3": volumen_mm3(model),
                             "ebene_flaechen_y_mm": [round(fc.GetBox[1] * 1000, 3) for fc in (f2.GetFaces or ())
                                                     if fc.GetSurface.IsPlane] if f2 else None}
        d["whatswrong"] = model.Extension.GetWhatsWrongCount
    with teil(app, r) as model:
        _, f = _bohrteil(app, model, 0, 0.010)
        d["blind_10"] = {"feature": f.Name, "zylinder": zylinder(f), "volumen_mm3": volumen_mm3(model)}
    with teil(app, r) as model:
        _, f = _bohrteil(app, model, 1, 0.0)
        d["durch_alles_zweites_teil"] = zylinder(f)
    return d


if __name__ == "__main__":
    lauf("s9a_b9_bohrungen", pruefen)
