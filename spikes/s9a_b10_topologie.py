"""S9a Baustein 10: Topologie lesen und Face/Edge mit Marke selektieren (Late Binding).

Quader 100 x 60 x 20 (Y 0..20) auf Ebene oben + Durchgangsbohrung r=5 bei (20, *, -10).
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import (
    flaeche_mit_normale, kasten_oben, letztes, modell_zu_skizze, schnitt, select_mark, start, teil,
)


def r6(v):
    return [round(x, 6) for x in v]


def _kante(e) -> dict:
    c = e.GetCurve
    out = {"is_line": bool(c.IsLine), "is_circle": bool(c.IsCircle)}
    if c.IsLine:
        out["lineparams"] = r6(c.LineParams)
    if c.IsCircle:
        out["circleparams"] = r6(c.CircleParams)
    sv, ev = e.GetStartVertex, e.GetEndVertex
    out["start"] = r6(sv.GetPoint) if sv is not None else None
    out["ende"] = r6(ev.GetPoint) if ev is not None else None
    return out


def pruefen() -> dict:
    r, app = start()
    d: dict = {}
    with teil(app, r) as model:
        k = kasten_oben(model, 100, 60, 20)
        deck = flaeche_mit_normale(k, (0.0, 1.0, 0.0))
        model.ClearSelection2(True)
        select_mark(model, deck, 0, append=False)
        sm = model.SketchManager
        sm.InsertSketch(True)
        u, v, _ = modell_zu_skizze(app, sm.ActiveSketch, (0.020, 0.020, -0.010))
        sm.CreateCircleByRadius(u, v, 0.0, 0.005)
        sm.InsertSketch(True)
        sk = letztes(model)
        model.ClearSelection2(True)
        sk.Select2(False, 0)
        bohr = schnitt(model, t1=1)

        # Flächen des Quader-Features
        fl = []
        for f in k.GetFaces:
            s = f.GetSurface
            e = {"is_plane": bool(s.IsPlane), "is_cylinder": bool(s.IsCylinder), "normal": r6(f.Normal),
                 "box": r6(f.GetBox), "flaeche_m2": round(f.GetArea, 9), "anzahl_kanten": len(f.GetEdges or ())}
            if s.IsPlane:
                e["planeparams"] = r6(s.PlaneParams)
                e["face_in_surface_sense"] = bool(f.FaceInSurfaceSense)
            fl.append(e)
        d["quader_flaechen"] = fl
        d["deckflaeche_kanten"] = [_kante(e) for e in deck.GetEdges]

        zyl = [f for f in bohr.GetFaces if f.GetSurface.IsCylinder][0]
        d["bohrung_zylinder"] = {"normal": r6(zyl.Normal), "cylinderparams": r6(zyl.GetSurface.CylinderParams),
                                 "box": r6(zyl.GetBox), "kanten": [_kante(e) for e in zyl.GetEdges]}
        d["face_getclosestpointon_(0.1,0.05,0.1)"] = r6(deck.GetClosestPointOn(0.1, 0.05, 0.1))
        kreis = [e for e in zyl.GetEdges if e.GetCurve.IsCircle][0]
        d["edge_getclosestpointon_(0.1,0.02,0)"] = r6(kreis.GetClosestPointOn(0.1, 0.02, 0.0))
        gerade = [e for e in deck.GetEdges if e.GetCurve.IsLine][0]
        d["edge_line_getclosestpointon_(0,0,0)"] = r6(gerade.GetClosestPointOn(0.0, 0.0, 0.0))
        d["face_getfeature_name"] = zyl.GetFeature.Name

        # Selektion mit Marke direkt auf Face/Edge
        sel = model.SelectionManager
        model.ClearSelection2(True)
        d["select4_face_mark2"] = select_mark(model, deck, 2, append=False)
        d["select4_edge_mark1"] = select_mark(model, gerade, 1, append=True)
        d["select4_edge2_mark1"] = select_mark(model, kreis, 1, append=True)
        d["sel_anzahl_alle"] = sel.GetSelectedObjectCount2(-1)
        d["sel_anzahl_mark1"] = sel.GetSelectedObjectCount2(1)
        d["sel_anzahl_mark2"] = sel.GetSelectedObjectCount2(2)
        d["sel_typen"] = [sel.GetSelectedObjectType3(i, -1) for i in range(1, sel.GetSelectedObjectCount2(-1) + 1)]
        d["sel_marks"] = [sel.GetSelectedObjectMark(i) for i in range(1, sel.GetSelectedObjectCount2(-1) + 1)]
        obj = sel.GetSelectedObject6(1, 2)
        d["getselectedobject6_ist_deck"] = bool(app.IsSame(obj, deck) == 1) if obj is not None else None
        model.ClearSelection2(True)

        # Feature-Typnamen im Baum
        typen = []
        f = model.FirstFeature
        while f is not None:
            typen.append([f.Name, f.GetTypeName2])
            f = f.GetNextFeature
        d["featurebaum"] = typen
    return d


if __name__ == "__main__":
    lauf("s9a_b10_topologie", pruefen)
