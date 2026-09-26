"""Gemeinsame Hilfen für Spike S9a (Aufrufketten Stufe-2-Compiler). Kein Produktionscode.

Erzwingt Late Binding (dynamischer Dispatch) unabhängig von einem vorhandenen gen_py-Cache.
"""

from contextlib import contextmanager
from pathlib import Path

import pythoncom
import win32com.client
import win32com.client.dynamic

from swki.konfig import lade_rechner
from swki.verbindung import callout_leer, jahr_aus_revision, wert

ARBEIT = Path.home() / ".swki" / "arbeit" / "stufe0" / "s9"


def verbinde_spaet(jahr: int):
    """Baustein 0: rein dynamisch gebundenes ISldWorks, auch wenn gen_py-Cache existiert."""
    major = jahr - 1992
    unk = None
    for progid in (f"SldWorks.Application.{major}", "SldWorks.Application"):
        try:
            unk = pythoncom.GetActiveObject(progid)  # PyIUnknown, kein gencache-Wrapping
            break
        except pythoncom.com_error:
            continue
    if unk is None:
        raise RuntimeError("SOLIDWORKS läuft nicht")
    app = win32com.client.dynamic.Dispatch(unk.QueryInterface(pythoncom.IID_IDispatch))
    if type(app) is not win32com.client.dynamic.CDispatch:
        raise RuntimeError(f"kein dynamischer Dispatch: {type(app)}")
    if jahr_aus_revision(app.RevisionNumber) != jahr:
        raise RuntimeError(f"falsche SW-Version: {app.RevisionNumber}")
    return app


def start():
    r = lade_rechner()
    return r, verbinde_spaet(r.sw_jahr)


def neues_teil(app, r):
    model = app.NewDocument(str(r.vorlage_teil), 0, 0, 0)
    if model is None:
        raise RuntimeError("NewDocument lieferte None")
    return model, model.GetTitle


@contextmanager
def teil(app, r):
    """Neues eigenes Teil; wird am Ende per eigenem Titel ungespeichert geschlossen."""
    model, titel = neues_teil(app, r)
    try:
        yield model
    finally:
        app.CloseDoc(titel)


def ebenen(model) -> list:
    """[Ebene vorne, Ebene oben, Ebene rechts] = erste drei RefPlane-Features."""
    out = []
    f = model.FirstFeature
    while f is not None and len(out) < 3:
        if f.GetTypeName2 == "RefPlane":
            out.append(f)
        f = f.GetNextFeature
    return out


def mm3(v) -> list:
    return [round(x * 1000.0, 4) for x in v]


def partbox_mm(model) -> list:
    return mm3(model.GetPartBox(True))


def letztes(model):
    return model.FeatureByPositionReverse(0)


def select_mark(model, obj, mark: int, append: bool = True) -> bool:
    """Entity/Feature/Segment per Select4 mit Marke selektieren."""
    sd = model.SelectionManager.CreateSelectData
    sd.Mark = mark
    return bool(obj.Select4(append, sd))


def extrusion(model, t1: int = 0, d1_m: float = 0.0, umkehren: bool = False,
              einseitig: bool = True, t2: int = 0, d2_m: float = 0.0):
    """FeatureExtrusion3 (23 Parameter). t1/t2: swEndConditions_e; umkehren = Dir (3. Parameter)."""
    fm = model.FeatureManager
    return fm.FeatureExtrusion3(
        einseitig, False, umkehren, t1, t2, d1_m, d2_m, False, False, False, False, 0.0, 0.0,
        False, False, False, False, True, True, True, 0, 0.0, False,
    )


def extrusion_blind(model, tiefe_m: float, umkehren: bool = False):
    return extrusion(model, 0, tiefe_m, umkehren)


def schnitt(model, t1: int = 0, tiefe_m: float = 0.0, umkehren: bool = False, seite_flip: bool = False):
    """FeatureCut4 (27 Parameter). t1: swEndConditions_e (0 blind, 1 durch alles)."""
    fm = model.FeatureManager
    return fm.FeatureCut4(
        True, seite_flip, umkehren, t1, 0, tiefe_m, 0.0, False, False, False, False, 0.0, 0.0,
        False, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False,
    )


def kasten_oben(model, b_mm: float, t_mm: float, h_mm: float):
    """Quader b (X) x t (Z) auf Ebene oben, Höhe h in +Y, mittig zum Ursprung."""
    oben = ebenen(model)[1]
    model.ClearSelection2(True)
    oben.Select2(False, 0)
    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.CreateCenterRectangle(0.0, 0.0, 0.0, b_mm / 2000, t_mm / 2000, 0.0)
    sm.InsertSketch(True)
    sk = letztes(model)
    model.ClearSelection2(True)
    sk.Select2(False, 0)
    return extrusion_blind(model, h_mm / 1000)


def r8_array(werte):
    """double-Array als VARIANT(VT_ARRAY|VT_R8). Rohe Python-Liste liefert bei CreatePoint Müll."""
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(x) for x in werte])


def mathutil(app):
    """IMathUtility; CreatePoint & Co. als Methode markieren (sonst Aufruf beim Attributzugriff)."""
    mu = app.GetMathUtility
    mu._FlagAsMethod("CreatePoint", "CreateVector", "CreateTransform")
    return mu


def modell_zu_skizze(app, sketch, xyz_m) -> list:
    """Modellpunkt (m) -> Skizzenkoordinaten (m) der Skizze über ModelToSketchTransform."""
    p = mathutil(app).CreatePoint(r8_array(xyz_m))
    q = p.MultiplyTransform(sketch.ModelToSketchTransform)
    return list(q.ArrayData)


def flaeche_mit_normale(feat, n, tol=1e-6):
    """Erste ebene Fläche des Features mit Normale n (Tupel)."""
    for f in feat.GetFaces or ():
        nn = f.Normal
        if all(abs(a - b) < tol for a, b in zip(nn, n)):
            return f
    return None


def zylinder(feat) -> list:
    out = []
    for f in feat.GetFaces or ():
        s = f.GetSurface
        if s.IsCylinder:
            out.append([round(x * 1000, 4) if i in (0, 1, 2, 6) else round(x, 6) for i, x in enumerate(s.CylinderParams)])
    return out


__all__ =["ARBEIT", "callout_leer", "wert"]


def skizze_ende_und_waehlen(model):
    """Skizze verlassen, Skizzen-Feature zurückgeben und (einzeln) selektieren."""
    model.SketchManager.InsertSketch(True)
    sk = letztes(model)
    model.ClearSelection2(True)
    sk.Select2(False, 0)
    return sk


def skizze_auf_ebene(model, ebene):
    model.ClearSelection2(True)
    ebene.Select2(False, 0)
    model.SketchManager.InsertSketch(True)
    return model.SketchManager


def feature_masse(feat) -> list:
    out = []
    dd = feat.GetFirstDisplayDimension
    while dd is not None:
        dim = dd.GetDimension2(0)
        out.append({"name": dim.Name, "fullname": dim.FullName, "typ2": dd.Type2,
                    "wert": round(dim.GetSystemValue3(1, None)[0], 9)})
        dd = feat.GetNextDisplayDimension(dd)
    return out


def volumen_mm3(model) -> float:
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return round(mp.Volume * 1e9, 3)
