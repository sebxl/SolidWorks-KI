"""S9a Baustein 1: Skizzenkoordinaten (u,v) -> Modell (X,Y,Z) je Standardebene + Extrusionsrichtung.

Außermittiges Rechteck: Mitte (u=30, v=10) mm, Größe 20 x 10 mm, Extrusion blind 5 mm.
GetPartBox zeigt, wohin u, v und die Extrusionsnormale im Modell zeigen.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import ebenen, extrusion_blind, letztes, partbox_mm, start, teil

U, V, B, H, T = 30.0, 10.0, 20.0, 10.0, 5.0


def pruefen() -> dict:
    r, app = start()
    daten: dict = {"eingabe_mm": {"u": U, "v": V, "breite_u": B, "hoehe_v": H, "tiefe": T}}
    for i, name in enumerate(("vorne", "oben", "rechts")):
        with teil(app, r) as model:
            e = ebenen(model)[i]
            model.ClearSelection2(True)
            e.Select2(False, 0)
            sm = model.SketchManager
            sm.InsertSketch(True)
            segs = sm.CreateCenterRectangle(U / 1000, V / 1000, 0.0, (U + B / 2) / 1000, (V + H / 2) / 1000, 0.0)
            sk = sm.ActiveSketch
            xf = sk.ModelToSketchTransform
            arr = [round(x, 6) for x in xf.ArrayData]
            sm.InsertSketch(True)
            skf = letztes(model)
            model.ClearSelection2(True)
            skf.Select2(False, 0)
            feat = extrusion_blind(model, T / 1000)
            daten[name] = {
                "ebene": e.Name,
                "anzahl_segmente": len(segs) if segs else None,
                "model_to_sketch_arraydata": arr,
                "extrusion": feat.Name if feat else None,
                "partbox_mm": partbox_mm(model),
            }
    return daten


if __name__ == "__main__":
    lauf("s9a_b1_koordinaten", pruefen)
