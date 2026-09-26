"""S9b Baustein 13: Fase Abstand-Winkel und Abstand-Abstand auf Kanten.

Quader 100 x 60 x 20 (Y 0..20), obere Längskante (Y=20, Z=+30) bzw. Bodenkante (Y=0, Z=+30).
Soll: AD 3/45° -> 0,5*3*3*100 = 450 mm³; AD 3/30° -> 0,5*3*3*tan30°*100 = 259,81 mm³;
DD 2/4 -> 0,5*2*4*100 = 400 mm³.
Wege: IFeatureManager.InsertFeatureChamfer (nicht obsolet), CreateDefinition(swFmChamfer=0),
CreateDefinition(swFmFillet=1) mit Profil swFeatureFilletConicRhoZeroChamfer (Offset-Flächenfase).
"""

import math

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import feature_masse, kasten_oben, select_mark, start, teil, volumen_mm3
from spikes.s9b_gemeinsam import byref_bool, kanten_linie, whatswrong

KANTE_OBEN = (None, 0.020, 0.030)
KANTE_UNTEN = (None, 0.0, 0.030)


def _fase_info(model, f, v0):
    if f is None:
        return {"feature": None, "abnahme_mm3": round(v0 - volumen_mm3(model), 3)}
    w = byref_bool()
    return {"feature": f.Name, "typ": f.GetTypeName2, "abnahme_mm3": round(v0 - volumen_mm3(model), 3),
            "flaechen": [{"normal": [round(x, 4) for x in fc.Normal], "box_mm": [round(x * 1000, 3) for x in fc.GetBox]}
                         for fc in (f.GetFaces or ())],
            "masse": [(m["name"], m["typ2"], m["wert"]) for m in feature_masse(f)],
            "errorcode2": f.GetErrorCode2(w), "whatswrong": whatswrong(model)["anzahl"]}


def _chamfer(app, r, kante, args, mark=1):
    with teil(app, r) as model:
        k = kasten_oben(model, 100, 60, 20)
        e = kanten_linie(k, (1, 0, 0), kante)[0]
        v0 = volumen_mm3(model)
        model.ClearSelection2(True)
        select_mark(model, e, mark, append=False)
        try:
            f = model.FeatureManager.InsertFeatureChamfer(*args)
        except Exception as ex:
            return {"fehler": repr(ex)}
        return {"args": list(args), "mark": mark, **_fase_info(model, f, v0)}


def pruefen() -> dict:
    r, app = start()
    d: dict = {"hinweis": "InsertFeatureChamfer(Options, ChamferType, Width, Angle, OtherDist, VD1, VD2, VD3)",
               "insertfeaturechamfer": {}, "createdefinition": {}}
    c = d["insertfeaturechamfer"]
    w45, w30 = math.radians(45), math.radians(30)
    c["AD_3_45"] = _chamfer(app, r, KANTE_OBEN, (0, 1, 0.003, w45, 0, 0, 0, 0))
    c["AD_3_45_mark0"] = _chamfer(app, r, KANTE_OBEN, (0, 1, 0.003, w45, 0, 0, 0, 0), mark=0)
    c["AD_3_30"] = _chamfer(app, r, KANTE_OBEN, (0, 1, 0.003, w30, 0, 0, 0, 0))
    c["AD_3_30_flip"] = _chamfer(app, r, KANTE_OBEN, (1, 1, 0.003, w30, 0, 0, 0, 0))
    c["AD_3_30_bodenkante"] = _chamfer(app, r, KANTE_UNTEN, (0, 1, 0.003, w30, 0, 0, 0, 0))
    # Abstand-Abstand: laut Doku VertexChamDist1/2 -> live geprüft
    c["DD_doku_vd1_vd2"] = _chamfer(app, r, KANTE_OBEN, (0, 2, 0.0, 0, 0, 0.002, 0.004, 0))
    c["DD_width_vd1_vd2"] = _chamfer(app, r, KANTE_OBEN, (0, 2, 0.002, 0, 0, 0.002, 0.004, 0))
    c["DD_width_otherdist"] = _chamfer(app, r, KANTE_OBEN, (0, 2, 0.002, 0, 0.004, 0, 0, 0))
    c["DD_width_otherdist_flip"] = _chamfer(app, r, KANTE_OBEN, (1, 2, 0.002, 0, 0.004, 0, 0, 0))
    c["DD_width_otherdist_bodenkante"] = _chamfer(app, r, KANTE_UNTEN, (0, 2, 0.002, 0, 0.004, 0, 0, 0))
    c["EQ_otherdist"] = _chamfer(app, r, KANTE_OBEN, (0, 16, 0, 0, 0.003, 0, 0, 0))
    c["EQ_width_otherdist"] = _chamfer(app, r, KANTE_OBEN, (0, 16, 0.003, 0, 0.003, 0, 0, 0))

    cd = d["createdefinition"]
    with teil(app, r) as model:
        cd["swFmChamfer_0"] = repr(model.FeatureManager.CreateDefinition(0))
    for name, asym in (("fillet_offsetfase_sym_3", False), ("fillet_offsetfase_asym_2_4", True)):
        with teil(app, r) as model:
            k = kasten_oben(model, 100, 60, 20)
            e = kanten_linie(k, (1, 0, 0), KANTE_OBEN)[0]
            v0 = volumen_mm3(model)
            fm = model.FeatureManager
            data = fm.CreateDefinition(1)
            data.Initialize(0)
            data.ConicTypeForCrossSectionProfile = 3   # swFeatureFilletConicRhoZeroChamfer
            if asym:
                data.AsymmetricFillet = True
                data.DefaultRadius = 0.002
                data.DefaultDistance = 0.004
            else:
                data.DefaultRadius = 0.003
            model.ClearSelection2(True)
            select_mark(model, e, 1, append=False)
            f = fm.CreateFeature(data)
            cd[name] = _fase_info(model, f, v0)
    d["empfehlung"] = ("InsertFeatureChamfer: AD (Typ 1, Width, Angle), DD (Typ 2, Width=d1, OtherDist=d2); "
                       "Typ 16 (EqualDistance) liefert leeres Feature -> nicht verwenden")
    return d


if __name__ == "__main__":
    lauf("s9b_b13_fase", pruefen)
