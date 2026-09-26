"""S9a Baustein 4: explizite Maße ohne Eingabedialog, FullyDefineSketch, Umbenennen.

Skizze auf Ebene oben: Mittelpunktrechteck 100 x 60, Kreis r=10 bei (25, 10).
swInputDimValOnCreate aus (im finally zurück), Linie -> AddDimension2, Kreis -> AddDimension2,
Wert per SetSystemValue3 ändern, FullyDefineSketch für den Rest, Status prüfen, danach Skizze
umbenennen und FullName der Maße vorher/nachher vergleichen.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import ebenen, letztes, select_mark, start, teil
from swki.verbindung import callout_leer

SW_INPUT_DIM_VAL_ON_CREATE = 10  # swUserPreferenceToggle_e
REL_ALLE = 1023  # Summe swSketchFullyDefineRelationType_e (1..512)


def _dim_info(dd) -> dict:
    dim = dd.GetDimension2(0)
    return {"typ2": dd.Type2, "name": dim.Name, "fullname": dim.FullName,
            "namen_fuer_selektion": dim.GetNameForSelection,
            "wert_mm": round(dim.GetSystemValue3(1, None)[0] * 1000, 4)}


def _pkt(p) -> list:
    return [round(p.X * 1000, 4), round(p.Y * 1000, 4)]


def _feature_dims(feat) -> list:
    out = []
    dd = feat.GetFirstDisplayDimension
    while dd is not None:
        out.append(_dim_info(dd))
        dd = feat.GetNextDisplayDimension(dd)
    return out


def pruefen() -> dict:
    r, app = start()
    d: dict = {"varianten": []}
    alt = app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE)
    d["swInputDimValOnCreate_vorher"] = alt
    try:
        app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, False)
        with teil(app, r) as model:
            oben = ebenen(model)[1]
            model.ClearSelection2(True)
            oben.Select2(False, 0)
            sm = model.SketchManager
            sm.InsertSketch(True)
            sk = sm.ActiveSketch
            sm.AddToDB = True
            try:
                rect = sm.CreateCenterRectangle(0.0, 0.0, 0.0, 0.050, 0.030, 0.0)
                kreis = sm.CreateCircleByRadius(0.025, 0.010, 0.0, 0.010)
            finally:
                sm.AddToDB = False

            # Breite: untere Linie (rect[0]); Höhe: linke Linie (rect[1]).
            model.ClearSelection2(True)
            select_mark(model, rect[0], 0, append=False)
            dd_b = model.AddDimension2(0.0, 0.0, 0.045)  # Textposition in Modellkoordinaten (m)
            d["breite"] = _dim_info(dd_b) if dd_b is not None else None
            model.ClearSelection2(True)
            select_mark(model, rect[1], 0, append=False)
            dd_h = model.AddDimension2(-0.065, 0.0, 0.0)
            d["hoehe"] = _dim_info(dd_h) if dd_h is not None else None
            model.ClearSelection2(True)
            select_mark(model, kreis, 0, append=False)
            dd_k = model.AddDimension2(0.050, 0.0, -0.030)
            d["kreis"] = _dim_info(dd_k) if dd_k is not None else None
            model.ClearSelection2(True)

            # Werte setzen: Breite 120, Höhe 50, Durchmesser 16
            for dd, soll in ((dd_b, 120), (dd_h, 50), (dd_k, 16)):
                ret = dd.GetDimension2(0).SetSystemValue3(soll / 1000, 1, None)  # swSetValue_InThisConfiguration
                d["varianten"].append({"SetSystemValue3": soll, "rueckgabe": ret})
            d["laengen_nach_set_mm"] = {
                "untere_linie_start_ende": _pkt(rect[0].GetStartPoint2) + _pkt(rect[0].GetEndPoint2),
                "kreis_mitte": _pkt(kreis.GetCenterPoint2),
                "untere_linie": round(rect[0].GetLength * 1000, 4),
                "linke_linie": round(rect[1].GetLength * 1000, 4),
                "kreis_radius": round(kreis.GetRadius * 1000, 4),
            }
            d["status_vor_fullydefine"] = sk.GetConstrainedStatus
            ret = sm.FullyDefineSketch(True, True, REL_ALLE, True, 1, callout_leer(), 1, callout_leer(), 1, 1)
            d["fullydefine_rueckgabe"] = ret
            d["status_nach_fullydefine"] = sk.GetConstrainedStatus  # 3 = swFullyConstrained
            d["laengen_nach_fullydefine_mm"] = {
                "untere_linie_start_ende": _pkt(rect[0].GetStartPoint2) + _pkt(rect[0].GetEndPoint2),
                "kreis_mitte": _pkt(kreis.GetCenterPoint2),
                "untere_linie": round(rect[0].GetLength * 1000, 4),
                "linke_linie": round(rect[1].GetLength * 1000, 4),
                "kreis_radius": round(kreis.GetRadius * 1000, 4),
            }
            sm.InsertSketch(True)
            skf = letztes(model)
            d["skizze_name_alt"] = skf.Name
            d["skizze_typname"] = skf.GetTypeName2
            d["dims_vor_umbenennen"] = _feature_dims(skf)
            skf.Name = "f1_skizze"
            d["skizze_name_neu"] = skf.Name
            d["dims_nach_umbenennen"] = _feature_dims(skf)
            # Maß über Namen wiederfinden
            dim = model.Parameter("D1@f1_skizze")
            d["parameter_D1@f1_skizze"] = None if dim is None else {"fullname": dim.FullName,
                                                                    "wert_mm": round(dim.GetSystemValue3(1, None)[0] * 1000, 4)}
            d["status_skizze_nach_verlassen"] = skf.GetSpecificFeature2.GetConstrainedStatus
    finally:
        app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, alt)
        d["swInputDimValOnCreate_zurueck"] = app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE)
    return d


if __name__ == "__main__":
    lauf("s9a_b4_masse", pruefen)
