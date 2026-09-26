"""S9b Baustein 12: Verrundung konstanter Radius auf per Entity selektierte Kanten.

Quader 100 x 60 x 20 (Y 0..20). Eine obere Längskante (Y=20, Z=+30, entlang X) wird mit R5 verrundet.
Soll-Volumenabnahme: (1 - pi/4) * 5² * 100 = 536,50 mm³.
Wege: CreateDefinition(swFmFillet=1) -> ISimpleFilletFeatureData2 -> CreateFeature (mehrere
Varianten der Kantenübergabe) und das (für diesen Fall obsolete) FeatureFillet3.
"""

import math

import pythoncom
import win32com.client

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import feature_masse, kasten_oben, r8_array, select_mark, start, teil, volumen_mm3
from spikes.s9b_gemeinsam import dispatch_array, flaechen_info, kanten_linie, whatswrong

SW_FM_FILLET = 1            # swFeatureNameID_e
SW_CONST_RADIUS_FILLET = 0  # swSimpleFilletType_e
SW_FILLET_CIRCULAR = 0      # swFeatureFilletProfileType_e
SOLL_ABNAHME = (1 - math.pi / 4) * 25 * 100


def _teil_mit_kante(model):
    k = kasten_oben(model, 100, 60, 20)
    return k, kanten_linie(k, (1, 0, 0), (None, 0.020, 0.030))


def _daten(fm, radius):
    d = fm.CreateDefinition(SW_FM_FILLET)
    ok = d.Initialize(SW_CONST_RADIUS_FILLET)
    d.DefaultRadius = radius
    d.ConicTypeForCrossSectionProfile = SW_FILLET_CIRCULAR
    d.OverflowType = 0
    return d, ok


def _ergebnis(model, f, v0):
    return {"feature": f.Name if f else None, "typ": f.GetTypeName2 if f else None,
            "abnahme_mm3": round(v0 - volumen_mm3(model), 3), "soll_mm3": round(SOLL_ABNAHME, 3),
            "zylinder": [x["cyl"] for x in flaechen_info(f) if x["zyl"]] if f else None,
            "masse": feature_masse(f) if f else None, "whatswrong": whatswrong(model)}


def pruefen() -> dict:
    r, app = start()
    d: dict = {"varianten": {}}
    v = d["varianten"]

    # 1) CreateDefinition + Selektion Mark 1 (laut Doku) – empfohlen
    with teil(app, r) as model:
        _, ek = _teil_mit_kante(model)
        v0 = volumen_mm3(model)
        fm = model.FeatureManager
        data, ok = _daten(fm, 0.005)
        model.ClearSelection2(True)
        sel = select_mark(model, ek[0], 1, append=False)
        f = fm.CreateFeature(data)
        v["createdefinition_mark1"] = {"initialize": ok, "select": sel, "typ_data": data.Type, **_ergebnis(model, f, v0),
                                       "selektion_danach": model.SelectionManager.GetSelectedObjectCount2(-1)}

    # 2) CreateDefinition + Edges-Property als VARIANT(VT_ARRAY|VT_DISPATCH), ohne Selektion
    with teil(app, r) as model:
        _, ek = _teil_mit_kante(model)
        v0 = volumen_mm3(model)
        fm = model.FeatureManager
        data, _ = _daten(fm, 0.005)
        model.ClearSelection2(True)
        data.Edges = dispatch_array(ek)
        n = data.GetEdgeCount
        f = fm.CreateFeature(data)
        v["createdefinition_edges_dispatch_array"] = {"edgecount": n, **_ergebnis(model, f, v0)}

    # 3) Edges-Property mit roher Python-Liste
    with teil(app, r) as model:
        _, ek = _teil_mit_kante(model)
        v0 = volumen_mm3(model)
        fm = model.FeatureManager
        data, _ = _daten(fm, 0.005)
        model.ClearSelection2(True)
        try:
            data.Edges = list(ek)
            n = data.GetEdgeCount
            f = fm.CreateFeature(data)
            v["createdefinition_edges_rohe_liste"] = {"edgecount": n, **_ergebnis(model, f, v0)}
        except Exception as e:
            v["createdefinition_edges_rohe_liste"] = {"fehler": repr(e)}

    # 4) Selektion Mark 0 statt 1
    with teil(app, r) as model:
        _, ek = _teil_mit_kante(model)
        v0 = volumen_mm3(model)
        fm = model.FeatureManager
        data, _ = _daten(fm, 0.005)
        model.ClearSelection2(True)
        select_mark(model, ek[0], 0, append=False)
        f = fm.CreateFeature(data)
        v["createdefinition_mark0"] = _ergebnis(model, f, v0)

    # 5) Vier Deckkanten, R4, Selektion vor CreateDefinition
    with teil(app, r) as model:
        k = kasten_oben(model, 100, 60, 20)
        top = kanten_linie(k, (1, 0, 0), (None, 0.020, None)) + kanten_linie(k, (0, 0, 1), (None, 0.020, None))
        v0 = volumen_mm3(model)
        model.ClearSelection2(True)
        for e in top:
            select_mark(model, e, 1, append=True)
        fm = model.FeatureManager
        data, _ = _daten(fm, 0.004)
        f = fm.CreateFeature(data)
        v["createdefinition_4_kanten"] = {"kanten": len(top), **_ergebnis(model, f, v0)}
        v["createdefinition_4_kanten"].pop("soll_mm3")

    # 6) Obsolet: FeatureFillet3 (Options=2 swFeatureFilletUniformRadius, Ftyp 0), Arrays als None/leer
    leer = lambda: win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [])  # noqa: E731
    for name, arrays in (("none", lambda: [None] * 7), ("r8_leer", lambda: [leer() for _ in range(7)]),
                         ("r8_radius", lambda: [r8_array([0.005])] + [leer() for _ in range(6)])):
        with teil(app, r) as model:
            _, ek = _teil_mit_kante(model)
            v0 = volumen_mm3(model)
            model.ClearSelection2(True)
            select_mark(model, ek[0], 1, append=False)
            try:
                f = model.FeatureManager.FeatureFillet3(2, 0.005, 0.0, 0.0, 0, 0, 0, *arrays())
                v[f"featurefillet3_{name}"] = _ergebnis(model, f, v0)
            except Exception as e:
                v[f"featurefillet3_{name}"] = {"fehler": repr(e)}

    # 7) Radius nachträglich über Maß ändern
    with teil(app, r) as model:
        _, ek = _teil_mit_kante(model)
        v0 = volumen_mm3(model)
        fm = model.FeatureManager
        data, _ = _daten(fm, 0.005)
        model.ClearSelection2(True)
        select_mark(model, ek[0], 1, append=False)
        f = fm.CreateFeature(data)
        dim = model.Parameter(f"D1@{f.Name}")
        dim.SetSystemValue3(0.008, 1, None)
        ok = model.EditRebuild3
        d["radius_aendern"] = {"rebuild": ok, "abnahme_mm3": round(v0 - volumen_mm3(model), 3),
                               "soll_mm3": round((1 - math.pi / 4) * 64 * 100, 3),
                               "zylinder": [x["cyl"] for x in flaechen_info(f) if x["zyl"]]}
    d["empfehlung"] = "CreateDefinition(swFmFillet) + Initialize(0) + Kanten Select4 Mark 1 + CreateFeature"
    return d


if __name__ == "__main__":
    lauf("s9b_b12_verrundung", pruefen)
