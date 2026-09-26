"""S9a Baustein 2: Skizze auf planarer Fläche und auf versetzter Ebene, Modell -> Skizze per Transform.

Quader 100 (X) x 60 (Z) x 20 (Y) auf Ebene oben. (a) Deckfläche (Normale +Y) per Select4 wählen,
Kreis r=5 an Modellposition (20, 20, -10) -> Schnitt blind 10. (b) Ebene parallel zu Ebene oben
im Abstand 50, Kreis r=4 an Modellposition (-20, 50, 15) -> Aufsatz blind 10 (Richtung prüfen).
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import (
    ebenen, extrusion_blind, flaeche_mit_normale, kasten_oben, letztes, mathutil, mm3, modell_zu_skizze, r8_array, partbox_mm, schnitt,
    select_mark, start, teil, zylinder,
)


def pruefen() -> dict:
    r, app = start()
    d: dict = {"varianten": []}
    # Verworfene Varianten IMathUtility.CreatePoint
    mu_roh = app.GetMathUtility
    d["varianten"].append({"variante": "mu.CreatePoint ohne _FlagAsMethod (Attributzugriff)",
                           "ergebnis": f"liefert bereits Punkt {tuple(mu_roh.CreatePoint.ArrayData)}; "
                                       "anschließender Aufruf mit Argument -> com_error 'Mitglied nicht gefunden'"})
    mu = mathutil(app)
    d["varianten"].append({"variante": "CreatePoint([0.02, 0.02, -0.01]) rohe Liste",
                           "arraydata": list(mu.CreatePoint([0.02, 0.02, -0.01]).ArrayData), "bewertung": "Müll"})
    d["varianten"].append({"variante": "CreatePoint(VARIANT(VT_ARRAY|VT_R8, [...]))",
                           "arraydata": list(mu.CreatePoint(r8_array([0.02, 0.02, -0.01])).ArrayData), "bewertung": "korrekt"})
    with teil(app, r) as model:
        kasten = kasten_oben(model, 100, 60, 20)
        d["kasten_partbox_mm"] = partbox_mm(model)
        # --- (a) Skizze auf Deckfläche
        deck = flaeche_mit_normale(kasten, (0.0, 1.0, 0.0))
        d["deckflaeche_gefunden"] = deck is not None
        d["deckflaeche_box_mm"] = mm3(deck.GetBox)
        model.ClearSelection2(True)
        d["select4_face_rueckgabe"] = select_mark(model, deck, 0, append=False)
        d["selektiert_anzahl"] = model.SelectionManager.GetSelectedObjectCount2(-1)
        sm = model.SketchManager
        sm.InsertSketch(True)
        sk = sm.ActiveSketch
        d["a_aktive_skizze"] = sk is not None
        uvw = modell_zu_skizze(app, sk, (0.020, 0.020, -0.010))
        d["a_skizzenkoord_mm"] = mm3(uvw)
        d["a_xform"] = [round(x, 6) for x in sk.ModelToSketchTransform.ArrayData]
        sm.CreateCircleByRadius(uvw[0], uvw[1], 0.0, 0.005)
        sm.InsertSketch(True)
        skf = letztes(model)
        model.ClearSelection2(True)
        skf.Select2(False, 0)
        cut = schnitt(model, 0, 0.010)
        d["a_schnitt"] = cut.Name if cut else None
        d["a_zylinder_origin_mm_axis_r_mm"] = zylinder(cut) if cut else None
        d["a_partbox_mm"] = partbox_mm(model)

        # --- (b) versetzte Ebene
        oben = ebenen(model)[1]
        model.ClearSelection2(True)
        d["b_select4_auf_refplane_feature"] = select_mark(model, oben, 0, append=False)
        d["b_selektiert_mark0"] = model.SelectionManager.GetSelectedObjectCount2(0)
        ebene = model.FeatureManager.InsertRefPlane(8, 0.050, 0, 0.0, 0, 0.0)  # swRefPlaneReferenceConstraint_Distance
        d["b_refplane"] = ebene.Name if ebene else None
        d["b_refplane_typ"] = ebene.GetTypeName2 if ebene else None
        model.ClearSelection2(True)
        ebene.Select2(False, 0)
        sm.InsertSketch(True)
        sk2 = sm.ActiveSketch
        d["b_xform"] = [round(x, 6) for x in sk2.ModelToSketchTransform.ArrayData]
        uvw2 = modell_zu_skizze(app, sk2, (-0.020, 0.050, 0.015))
        d["b_skizzenkoord_mm"] = mm3(uvw2)
        sm.CreateCircleByRadius(uvw2[0], uvw2[1], 0.0, 0.004)
        sm.InsertSketch(True)
        skf2 = letztes(model)
        model.ClearSelection2(True)
        skf2.Select2(False, 0)
        boss = extrusion_blind(model, 0.010)
        d["b_aufsatz"] = boss.Name if boss else None
        d["b_zylinder"] = zylinder(boss) if boss else None
        d["b_partbox_mm"] = partbox_mm(model)
    return d


if __name__ == "__main__":
    lauf("s9a_b2_skizze_flaeche_ebene", pruefen)
