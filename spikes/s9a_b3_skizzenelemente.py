"""S9a Baustein 3: Skizzenelemente und ihre Rückgaben.

Skizze auf Ebene vorne: CreateCenterRectangle, CreateCircleByRadius, geschlossenes Dreieck per
CreateLine, CreateCenterLine. Je Rückgabe: Typ, Konstruktionsflag, Endpunkte/Mittelpunkt, Name;
Selektion eines Segments per Select4 mit Marke; automatisch erzeugte Relationen, Punktanzahl.
Zwei Durchläufe: ISketchManager.AddToDB = False (Standard, mit Inferenz) und = True.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import ebenen, mm3, select_mark, start, teil


def _seg(seg) -> dict:
    d = {"typ": seg.GetType, "konstruktion": bool(seg.ConstructionGeometry), "name": seg.GetName}
    if d["typ"] == 0:  # swSketchLINE
        a, b = seg.GetStartPoint2, seg.GetEndPoint2
        d["start_mm"] = mm3((a.X, a.Y, a.Z))
        d["ende_mm"] = mm3((b.X, b.Y, b.Z))
    elif d["typ"] == 1:  # swSketchARC
        c = seg.GetCenterPoint2
        d["mitte_mm"] = mm3((c.X, c.Y, c.Z))
        d["radius_mm"] = round(seg.GetRadius * 1000, 4)
    d["laenge_mm"] = round(seg.GetLength * 1000, 4)
    return d


def _relationen(sk) -> dict:
    rm = sk.RelationManager
    rels = rm.GetRelations(0) or ()  # swAll
    out = {"anzahl": rm.GetRelationsCount(0), "typen": sorted(r.GetRelationType for r in rels)}
    tang = [[e.GetName for e in r.GetEntities] for r in rels if r.GetRelationType == 6]
    if tang:
        out["tangential_zwischen"] = tang
    return out


def _lauf(app, r, addtodb: bool) -> dict:
    d: dict = {}
    with teil(app, r) as model:
        vorne = ebenen(model)[0]
        model.ClearSelection2(True)
        vorne.Select2(False, 0)
        sm = model.SketchManager
        sm.InsertSketch(True)
        sk = sm.ActiveSketch
        sm.AddToDB = addtodb
        try:
            rect = sm.CreateCenterRectangle(0.0, 0.0, 0.0, 0.040, 0.020, 0.0)
            d["rechteck"] = {"rueckgabe_typ": type(rect).__name__, "anzahl": len(rect),
                             "segmente": [_seg(s) for s in rect]}
            d["rel_nach_rechteck"] = _relationen(sk)

            kreis = sm.CreateCircleByRadius(0.070, 0.0, 0.0, 0.010)
            d["kreis"] = _seg(kreis)

            pts = [(0.100, -0.010), (0.130, -0.010), (0.115, 0.015)]  # Grundlinie y=-10 = Tangente an Kreis
            linien = []
            for i in range(3):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % 3]
                linien.append(sm.CreateLine(x1, y1, 0.0, x2, y2, 0.0))
            d["dreieck"] = [_seg(s) for s in linien]
            d["dreieck_endpunkt_gemeinsam"] = linien[0].GetEndPoint2.GetID == linien[1].GetStartPoint2.GetID

            ml = sm.CreateCenterLine(-0.060, -0.030, 0.0, -0.060, 0.030, 0.0)
            d["mittellinie"] = _seg(ml)
        finally:
            sm.AddToDB = False

        d["rel_gesamt"] = _relationen(sk)
        d["skizzenpunkte"] = len(sk.GetSketchPoints2 or ())
        d["skizzensegmente"] = len(sk.GetSketchSegments or ())

        model.ClearSelection2(True)
        ok = select_mark(model, rect[0], 4, append=False)
        selmgr = model.SelectionManager
        d["select4_segment"] = {"rueckgabe": ok, "anzahl_mark4": selmgr.GetSelectedObjectCount2(4),
                                "typ_sel": selmgr.GetSelectedObjectType3(1, 4)}
        ok2 = select_mark(model, kreis, 4, append=True)
        d["select4_kreis_append"] = {"rueckgabe": ok2, "anzahl_mark4": selmgr.GetSelectedObjectCount2(4)}
        model.ClearSelection2(True)
        sm.InsertSketch(True)
    return d


def pruefen() -> dict:
    r, app = start()
    return {f"addtodb_{a}": _lauf(app, r, a) for a in (False, True)}


if __name__ == "__main__":
    lauf("s9a_b3_skizzenelemente", pruefen)
