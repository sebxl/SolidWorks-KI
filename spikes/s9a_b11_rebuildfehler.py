"""S9a Baustein 11: Rebuild-Fehler erkennen.

(a) Schnitt direkt mit Skizze außerhalb des Körpers (blind) -> Rückgabe von FeatureCut4?
(b) Gültiger Schnitt von Ebene Y=50 blind 40 nach unten, danach Tiefe per SetSystemValue3 auf 10
    (trifft den Körper nicht mehr) -> EditRebuild3 -> GetWhatsWrongCount / GetWhatsWrong /
    IFeature.GetErrorCode2. Varianten für die ByRef-Ausgabeparameter werden protokolliert.
"""

import pythoncom
import win32com.client

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import (
    ebenen, feature_masse, kasten_oben, schnitt, select_mark, skizze_auf_ebene, skizze_ende_und_waehlen,
    start, teil, volumen_mm3,
)


def byref_variant():
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, None)


def byref_bool():
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BOOL, False)


def _whatswrong(model, d: dict, praefix: str) -> None:
    ext = model.Extension
    d[f"{praefix}_count"] = ext.GetWhatsWrongCount
    try:
        feats, codes, warns = byref_variant(), byref_variant(), byref_variant()
        ret = ext.GetWhatsWrong(feats, codes, warns)
        d[f"{praefix}_getwhatswrong"] = {
            "rueckgabe": ret,
            "features": [f.Name for f in (feats.value or ())],
            "fehlercodes": list(codes.value or ()),
            "warnungen": list(warns.value or ()),
        }
    except Exception as e:
        d[f"{praefix}_getwhatswrong_fehler"] = repr(e)


def pruefen() -> dict:
    r, app = start()
    d: dict = {"varianten": []}
    # (a)
    with teil(app, r) as model:
        kasten_oben(model, 100, 60, 20)
        sm = skizze_auf_ebene(model, ebenen(model)[1])
        sm.CreateCircleByRadius(0.200, 0.0, 0.0, 0.005)
        skizze_ende_und_waehlen(model)
        f = schnitt(model, t1=0, tiefe_m=0.010, umkehren=True)
        d["a_rueckgabe"] = None if f is None else f.Name
        d["a_letztes_feature"] = model.FeatureByPositionReverse(0).Name
        _whatswrong(model, d, "a_whatswrong")
    # (b)
    with teil(app, r) as model:
        kasten_oben(model, 100, 60, 20)
        oben = ebenen(model)[1]
        model.ClearSelection2(True)
        select_mark(model, oben, 0, append=False)
        ebene = model.FeatureManager.InsertRefPlane(8, 0.050, 0, 0.0, 0, 0.0)
        sm = skizze_auf_ebene(model, ebene)
        sm.CreateCircleByRadius(0.0, 0.0, 0.0, 0.005)
        skizze_ende_und_waehlen(model)
        cut = schnitt(model, t1=0, tiefe_m=0.040)
        d["b_schnitt"] = cut.Name if cut else None
        d["b_volumen_ok_mm3"] = volumen_mm3(model)
        _whatswrong(model, d, "b_vorher")
        # Achtung: GetFirstDisplayDimension des Schnitts liefert zuerst D1@Ebene1 (Abstand der
        # Referenzebene) – eigenes Maß über FullName auswählen.
        d["b_masse_cut_vorher"] = feature_masse(cut)
        dim = model.Parameter(f"D1@{cut.Name}")
        d["b_setsystemvalue3"] = dim.SetSystemValue3(0.010, 1, None)
        d["b_editrebuild3"] = model.EditRebuild3
        d["b_volumen_nach_mm3"] = volumen_mm3(model)
        _whatswrong(model, d, "b_nachher")
        # GetErrorCode2 mit ByRef-bool
        try:
            w = byref_bool()
            code = cut.GetErrorCode2(w)
            d["b_geterrorcode2"] = {"code": code, "ist_warnung": w.value}
        except Exception as e:
            d["varianten"].append({"GetErrorCode2(byref_bool)": repr(e)})
        try:
            d["varianten"].append({"GetErrorCode2 ohne Argument": repr(cut.GetErrorCode2)})
        except Exception as e:
            d["varianten"].append({"GetErrorCode2 ohne Argument": repr(e)})
        d["b_masse_cut"] = feature_masse(cut)
    return d


if __name__ == "__main__":
    lauf("s9a_b11_rebuildfehler", pruefen)
