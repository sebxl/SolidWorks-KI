"""S9b Baustein 16: Spiegeln von Features an einer Standardebene.

Quader 100 x 60 x 20 (Y 0..20), Saat: Bohrung r=4 durch alles bei (X=-30, Z=-15), 1005,31 mm³.
Spiegeln an Ebene rechts (X=0) -> Soll (30, -15); an Ebene vorne (Z=0) -> Soll (-30, 15).
Wege: IFeatureManager.InsertMirrorFeature2 (Feature Marke 1, Ebene Marke 2) und
CreateDefinition(swFmMirrorPattern=7 / swFmMirrorSolid=4).
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import ebenen, kasten_oben, select_mark, start, teil, volumen_mm3
from spikes.s9b_b14_lineares_muster import bohrung, bohrungs_xz
from spikes.s9b_gemeinsam import dispatch_array, whatswrong


def _lauf(app, r, fn) -> dict:
    with teil(app, r) as model:
        k = kasten_oben(model, 100, 60, 20)
        cut = bohrung(app, model, k, (-0.030, 0.020, -0.015))
        v0 = volumen_mm3(model)
        info: dict = {}
        try:
            f = fn(model, cut, info)
        except Exception as e:
            return {"fehler": repr(e), **info}
        return {"feature": f.Name if f else None, "typ": f.GetTypeName2 if f else None,
                "abnahme_mm3": round(v0 - volumen_mm3(model), 3), "bohrungen_xz_mm": bohrungs_xz(model),
                "whatswrong": whatswrong(model), **info}


def _mirror2(model, cut, ebene, merge=False):
    model.ClearSelection2(True)
    select_mark(model, cut, 1, append=False)      # Feature Marke 1
    select_mark(model, ebene, 2, append=True)     # Spiegelebene Marke 2
    return model.FeatureManager.InsertMirrorFeature2(False, False, merge, False, 0)


def mirror2_ebene_rechts(model, cut, info):
    return _mirror2(model, cut, ebenen(model)[2])


def mirror2_ebene_vorne(model, cut, info):
    return _mirror2(model, cut, ebenen(model)[0])


def mirror2_ebene_rechts_merge(model, cut, info):
    return _mirror2(model, cut, ebenen(model)[2], merge=True)


def mirror2_marken_vertauscht(model, cut, info):
    model.ClearSelection2(True)
    select_mark(model, ebenen(model)[2], 1, append=False)
    select_mark(model, cut, 2, append=True)
    return model.FeatureManager.InsertMirrorFeature2(False, False, False, False, 0)


def createdefinition_mirrorpattern(model, cut, info):
    model.ClearSelection2(True)
    select_mark(model, cut, 1, append=False)
    select_mark(model, ebenen(model)[2], 2, append=True)
    fm = model.FeatureManager
    out = {}
    for typ in (7, 4):
        data = fm.CreateDefinition(typ)
        out[typ] = repr(data)
    info["createdefinition"] = out
    data = fm.CreateDefinition(7)
    if data is None:
        return None
    data.Plane = ebenen(model)[2]
    data.PatternFeatureArray = dispatch_array([cut])
    return fm.CreateFeature(data)


def pruefen() -> dict:
    r, app = start()
    d: dict = {"hinweis": "InsertMirrorFeature2(BMirrorBody, BGeometryPattern, BMerge, BKnit, ScopeOptions)"}
    for fn in (mirror2_ebene_rechts, mirror2_ebene_vorne, mirror2_ebene_rechts_merge, mirror2_marken_vertauscht,
               createdefinition_mirrorpattern):
        d[fn.__name__] = _lauf(app, r, fn)
    return d


if __name__ == "__main__":
    lauf("s9b_b16_spiegeln", pruefen)
