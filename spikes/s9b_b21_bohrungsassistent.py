"""S9b Baustein 21 (optional): HoleWizard5 Gewindebohrung M8 (ISO) an einer Position auf einer Fläche.

Quader 100 x 60 x 20 (Y 0..20). Position per IModelDocExtension.SelectByRay (Marke 0) auf der
Deckfläche bei (X=10, Z=-5). HoleWizard5(swWzdTap=4, swStandardISO=8, swStandardISOTappedHole=147, SSize, …).
Soll blind: Kernloch Ø6,8 x 16 + 118°-Spitze = π·3,4²·16 + π·3,4²·(3,4/tan 59°)/3 = 605,80 mm³;
durch alles: π·3,4²·20 = 726,34 mm³.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import kasten_oben, start, teil, volumen_mm3
from spikes.s9b_gemeinsam import whatswrong

SW_WZD_TAP = 4
SW_STANDARD_ISO = 8
SW_ISO_TAPPED_HOLE = 147
SW_SEL_FACES = 2
SW_COSMETIC_THREAD_WITHOUT_CALLOUT = 2


def gewinde(model, ssize, end_type, durchmesser, tiefe, gewindetiefe, pos):
    x, y, z = pos
    model.ClearSelection2(True)
    sel = model.Extension.SelectByRay(x, y + 0.010, z, 0.0, -1.0, 0.0, 0.0005, SW_SEL_FACES, False, 0, 0)
    f = model.FeatureManager.HoleWizard5(
        SW_WZD_TAP, SW_STANDARD_ISO, SW_ISO_TAPPED_HOLE, ssize, end_type, durchmesser, tiefe, -1,
        gewindetiefe, -1, -1, -1, -1, -1, SW_COSMETIC_THREAD_WITHOUT_CALLOUT, -1, -1, -1, -1, -1,
        "", False, False, True, False, True, False)
    return sel, f


def _info(model, f, v0, sel) -> dict:
    out = {"selectbyray": sel, "feature": f.Name if f else None, "typ": f.GetTypeName2 if f else None,
           "abnahme_mm3": round(v0 - volumen_mm3(model), 3), "whatswrong": whatswrong(model)}
    if f:
        subs, s = [], f.GetFirstSubFeature
        while s is not None:
            subs.append((s.Name, s.GetTypeName2))
            s = s.GetNextSubFeature
        out["subfeatures"] = subs
        out["zylinder"] = [[round(x * 1000, 4) if i in (0, 1, 2, 6) else round(x, 6) for i, x in enumerate(fc.GetSurface.CylinderParams)]
                           for fc in (f.GetFaces or ()) if fc.GetSurface.IsCylinder]
    return out


def pruefen() -> dict:
    r, app = start()
    d: dict = {"soll_blind_mm3": 605.80, "soll_durch_alles_mm3": 726.34}
    faelle = {
        "M8x1.25_blind_d6.8": ("M8x1.25", 0, 0.0068, 0.016, 0.012),
        "M8_blind_d6.8": ("M8", 0, 0.0068, 0.016, 0.012),
        "M8_blind_d_minus1_norm": ("M8", 0, -1, 0.016, 0.012),
        "M8_blind_d_0": ("M8", 0, 0.0, 0.016, 0.012),
        "M8_durch_alles": ("M8", 1, -1, 0.0, 0.012),
        "M99_ungueltig": ("M99", 0, -1, 0.016, 0.012),
    }
    for name, (ssize, et, dia, tiefe, gt) in faelle.items():
        with teil(app, r) as model:
            kasten_oben(model, 100, 60, 20)
            v0 = volumen_mm3(model)
            try:
                sel, f = gewinde(model, ssize, et, dia, tiefe, gt, (0.010, 0.020, -0.005))
                d[name] = _info(model, f, v0, sel)
            except Exception as e:
                d[name] = {"fehler": repr(e)}
    return d


if __name__ == "__main__":
    lauf("s9b_b21_bohrungsassistent", pruefen)
