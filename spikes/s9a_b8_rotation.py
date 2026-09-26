"""S9a Baustein 8: FeatureRevolve2 als Aufsatz (360°) und als Schnitt (Nut).

Skizze auf Ebene vorne: geschlossener Linienzug (Rechteck x 10..30, y 0..40) + Mittellinie auf der
Y-Achse -> Rohr Ri 10, Ra 30, H 40 (Soll-Volumen pi*(30²-10²)*40).
Nut: Linienzug x 25..35, y 15..20 + Mittellinie -> Schnitt 360° (Soll-Abtrag pi*(30²-25²)*5).
Varianten: A nur Skizze selektiert (Mark 0); B Skizze Mark 0 + Mittellinie Mark 4 (Select4).
"""

import math

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import (
    ebenen, partbox_mm, select_mark, skizze_auf_ebene, start, teil, volumen_mm3, letztes,
)


def rotation(model, schnitt: bool, winkel_rad: float = 2 * math.pi, umkehren: bool = False):
    fm = model.FeatureManager
    return fm.FeatureRevolve2(True, True, False, schnitt, umkehren, False, 0, 0, winkel_rad, 0.0,
                              False, False, 0.0, 0.0, 0, 0.0, 0.0, True, True, True)


def _profil(model, pts, achse=((0.0, -0.010), (0.0, 0.050))):
    sm = skizze_auf_ebene(model, ebenen(model)[0])
    sm.AddToDB = True
    try:
        for i in range(len(pts)):
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
            sm.CreateLine(x1, y1, 0.0, x2, y2, 0.0)
        ml = sm.CreateCenterLine(achse[0][0], achse[0][1], 0.0, achse[1][0], achse[1][1], 0.0)
    finally:
        sm.AddToDB = False
    sm.InsertSketch(True)
    return letztes(model), ml


ROHR = [(0.010, 0.0), (0.030, 0.0), (0.030, 0.040), (0.010, 0.040)]
NUT = [(0.025, 0.015), (0.035, 0.015), (0.035, 0.020), (0.025, 0.020)]


def pruefen() -> dict:
    r, app = start()
    d: dict = {"soll_rohr_mm3": round(math.pi * (30**2 - 10**2) * 40, 3),
               "soll_nut_abtrag_mm3": round(math.pi * (30**2 - 25**2) * 5, 3)}
    for variante in ("A_nur_skizze", "B_skizze_plus_mittellinie_mark4"):
        v: dict = {}
        with teil(app, r) as model:
            sk, ml = _profil(model, ROHR)
            model.ClearSelection2(True)
            sk.Select2(False, 0)
            if variante.startswith("B"):
                v["select_mittellinie"] = select_mark(model, ml, 4, append=True)
            f = rotation(model, schnitt=False)
            v["aufsatz"] = None if f is None else {"feature": f.Name, "typname": f.GetTypeName2,
                                                   "volumen_mm3": volumen_mm3(model), "partbox_mm": partbox_mm(model)}
            if f is not None:
                vol0 = volumen_mm3(model)
                sk2, ml2 = _profil(model, NUT)
                model.ClearSelection2(True)
                sk2.Select2(False, 0)
                if variante.startswith("B"):
                    select_mark(model, ml2, 4, append=True)
                f2 = rotation(model, schnitt=True)
                v["schnitt"] = None if f2 is None else {"feature": f2.Name, "typname": f2.GetTypeName2,
                                                        "abgetragen_mm3": round(vol0 - volumen_mm3(model), 3)}
            v["whatswrong"] = model.Extension.GetWhatsWrongCount
        d[variante] = v
    return d


if __name__ == "__main__":
    lauf("s9a_b8_rotation", pruefen)
