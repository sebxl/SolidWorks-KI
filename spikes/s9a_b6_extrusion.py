"""S9a Baustein 6: FeatureExtrusion3 blind / durch alles / Mittelebene / Richtung umkehren.

Je Variante ein eigenes Teil. Rechteck 40 x 30 auf Ebene oben (Normale +Y). Nachweis per GetPartBox.
Durch alles: Grundquader 100 x 60 x 20, dann Kreis r=5 auf Ebene vorne als Aufsatz, einmal innerhalb
des Quaders (X=0, Y=10) und einmal oberhalb (X=0, Y=30).
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import (
    ebenen, extrusion, feature_masse, kasten_oben, partbox_mm, skizze_auf_ebene, skizze_ende_und_waehlen,
    start, teil,
)


def _rechteck_oben(model):
    sm = skizze_auf_ebene(model, ebenen(model)[1])
    sm.CreateCenterRectangle(0.0, 0.0, 0.0, 0.020, 0.015, 0.0)
    return skizze_ende_und_waehlen(model)


def pruefen() -> dict:
    r, app = start()
    d: dict = {}
    faelle = {
        "blind_20": dict(t1=0, d1_m=0.020),
        "blind_20_umgekehrt_dir": dict(t1=0, d1_m=0.020, umkehren=True),
        "mittelebene_20": dict(t1=6, d1_m=0.020),
        "beidseitig_blind_20_10": dict(t1=0, d1_m=0.020, einseitig=False, t2=0, d2_m=0.010),
    }
    for name, kw in faelle.items():
        with teil(app, r) as model:
            _rechteck_oben(model)
            f = extrusion(model, **kw)
            d[name] = {"feature": f.Name if f else None, "typname": f.GetTypeName2 if f else None,
                       "partbox_mm": partbox_mm(model), "masse": feature_masse(f) if f else None}

    for name, t1, einseitig, y in (("durch_alles_aufsatz_innen", 1, True, 0.010),
                                   ("durch_alles_beide_aufsatz_innen", 9, True, 0.010),
                                   ("durch_alles_aufsatz_oberhalb", 1, True, 0.030),
                                   ("durch_alles_beide_aufsatz_oberhalb", 9, True, 0.030),
                                   ("durch_alles_zweiseitig_1_1_oberhalb", 1, False, 0.030)):
        with teil(app, r) as model:
            kasten_oben(model, 100, 60, 20)
            sm = skizze_auf_ebene(model, ebenen(model)[0])
            sm.CreateCircleByRadius(0.0, y, 0.0, 0.005)
            skizze_ende_und_waehlen(model)
            f = extrusion(model, t1=t1, d1_m=0.0, einseitig=einseitig, t2=1 if not einseitig else 0)
            info = {"feature": f.Name if f else None, "partbox_mm": partbox_mm(model)}
            if f:
                info["masse"] = feature_masse(f)
                zyl = [fc for fc in (f.GetFaces or ()) if fc.GetSurface.IsCylinder]
                info["anzahl_flaechen"] = len(f.GetFaces or ())
                info["whatswrong"] = model.Extension.GetWhatsWrongCount
                info["zylinder_box_mm"] = [[round(x * 1000, 3) for x in fc.GetBox] for fc in zyl]
            d[name] = info
    return d


if __name__ == "__main__":
    lauf("s9a_b6_extrusion", pruefen)
