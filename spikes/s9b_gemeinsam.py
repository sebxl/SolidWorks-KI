"""Gemeinsame Hilfen für Spike S9b (Aufrufketten Stufe-2-Compiler, Teil B). Kein Produktionscode.

Baut auf spikes/s9a_gemeinsam.py auf (Late Binding, Teil anlegen, Selektion mit Marke …).
"""

import pythoncom
import win32com.client

from spikes.s9a_gemeinsam import ARBEIT, letztes, select_mark

__all__ = ["ARBEIT", "byref_variant", "byref_bool", "byref_long", "byref_str", "dispatch_array",
           "kanten_linie", "whatswrong", "flaechen_info", "feature_typen", "letztes", "select_mark"]


def byref_variant():
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, None)


def byref_bool():
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BOOL, False)


def byref_long(start: int = 0):
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, start)


def byref_str():
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")


def dispatch_array(objs):
    """Array von COM-Objekten als VARIANT(VT_ARRAY|VT_DISPATCH)."""
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, list(objs))


def kanten_linie(feat_oder_face, richtung, punkt_auf, tol=1e-6):
    """Gerade Kanten (aus Features/Flächen) mit Richtung ±richtung, die durch punkt_auf verlaufen.

    punkt_auf: (x, y, z) mit None für "beliebig" in der jeweiligen Koordinate.
    """
    faces = feat_oder_face.GetFaces or () if hasattr(feat_oder_face, "GetFaces") else [feat_oder_face]
    out, gesehen = [], []
    for f in faces:
        for e in f.GetEdges or ():
            c = e.GetCurve
            if not c.IsLine:
                continue
            px, py, pz, dx, dy, dz = c.LineParams
            if abs(abs(dx * richtung[0] + dy * richtung[1] + dz * richtung[2]) - 1.0) > tol:
                continue
            p = (px, py, pz)
            if any(soll is not None and abs(p[i] - soll) > tol for i, soll in enumerate(punkt_auf)):
                continue
            if any(e is g or _gleich(e, g) for g in gesehen):
                continue
            gesehen.append(e)
            out.append(e)
    return out


def _gleich(a, b) -> bool:
    try:
        sa = [round(x, 7) for x in a.GetStartVertex.GetPoint] + [round(x, 7) for x in a.GetEndVertex.GetPoint]
        sb = [round(x, 7) for x in b.GetStartVertex.GetPoint] + [round(x, 7) for x in b.GetEndVertex.GetPoint]
        return sa == sb or sa == sb[3:] + sb[:3]
    except Exception:
        return False


def whatswrong(model) -> dict:
    ext = model.Extension
    n = ext.GetWhatsWrongCount
    feats, codes, warns = byref_variant(), byref_variant(), byref_variant()
    ext.GetWhatsWrong(feats, codes, warns)
    return {"anzahl": n, "features": [f.Name for f in (feats.value or ())],
            "codes": list(codes.value or ()), "warnungen": list(warns.value or ())}


def flaechen_info(feat) -> list:
    out = []
    for f in feat.GetFaces or ():
        s = f.GetSurface
        d = {"eben": s.IsPlane, "zyl": s.IsCylinder, "flaeche_mm2": round(f.GetArea * 1e6, 4)}
        if s.IsCylinder:
            d["cyl"] = [round(x * 1000, 4) if i in (0, 1, 2, 6) else round(x, 6) for i, x in enumerate(s.CylinderParams)]
        if s.IsPlane:
            d["normal"] = [round(x, 6) for x in f.Normal]
        out.append(d)
    return out


def feature_typen(model) -> list:
    out, f = [], model.FirstFeature
    while f is not None:
        out.append((f.Name, f.GetTypeName2))
        f = f.GetNextFeature
    return out
