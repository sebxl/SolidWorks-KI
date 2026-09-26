"""S9a Baustein 7: FeatureCut4 blind und durch alles, Richtung.

Quader 100 x 60 x 20 (Y 0..20) auf Ebene oben. Rechteck 20 x 10 um Modellpunkt (20, *, -10).
(a) Skizze auf Deckfläche (Y=20): blind 5, durch alles, blind 5 mit Dir=True.
(b) Skizze auf Ebene oben (Y=0, Normale +Y): durch alles ohne / mit Dir=True.
Nachweis über Volumenänderung (CreateMassProperty2) und Box der erzeugten Flächen.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import (
    ebenen, flaeche_mit_normale, kasten_oben, modell_zu_skizze, schnitt, select_mark,
    skizze_auf_ebene, skizze_ende_und_waehlen, start, teil, volumen_mm3,
)

V0 = 100 * 60 * 20


def _rechteck_um(app, model, sm, x, y, z):
    u, v, _ = modell_zu_skizze(app, sm.ActiveSketch, (x, y, z))
    sm.CreateCenterRectangle(u, v, 0.0, u + 0.010, v + 0.005, 0.0)


def _auswertung(model, f) -> dict:
    if f is None:
        return {"feature": None, "volumen_mm3": volumen_mm3(model), "whatswrong": model.Extension.GetWhatsWrongCount}
    ys = []
    for fc in f.GetFaces or ():
        b = fc.GetBox
        ys += [b[1], b[4]]
    return {"feature": f.Name, "typname": f.GetTypeName2, "volumen_mm3": volumen_mm3(model),
            "abgetragen_mm3": round(V0 - volumen_mm3(model), 3), "anzahl_flaechen": len(f.GetFaces or ()),
            "y_bereich_flaechen_mm": [round(min(ys) * 1000, 3), round(max(ys) * 1000, 3)] if ys else None,
            "whatswrong": model.Extension.GetWhatsWrongCount}


def pruefen() -> dict:
    r, app = start()
    d: dict = {}
    for name, kw in {"deck_blind_5": dict(t1=0, tiefe_m=0.005),
                     "deck_durch_alles": dict(t1=1),
                     "deck_blind_5_dir": dict(t1=0, tiefe_m=0.005, umkehren=True)}.items():
        with teil(app, r) as model:
            k = kasten_oben(model, 100, 60, 20)
            deck = flaeche_mit_normale(k, (0.0, 1.0, 0.0))
            model.ClearSelection2(True)
            select_mark(model, deck, 0, append=False)
            sm = model.SketchManager
            sm.InsertSketch(True)
            _rechteck_um(app, model, sm, 0.020, 0.020, -0.010)
            skizze_ende_und_waehlen(model)
            d[name] = _auswertung(model, schnitt(model, **kw))
    for name, kw in {"ebene_oben_durch_alles": dict(t1=1),
                     "ebene_oben_durch_alles_dir": dict(t1=1, umkehren=True)}.items():
        with teil(app, r) as model:
            kasten_oben(model, 100, 60, 20)
            sm = skizze_auf_ebene(model, ebenen(model)[1])
            _rechteck_um(app, model, sm, 0.020, 0.0, -0.010)
            skizze_ende_und_waehlen(model)
            d[name] = _auswertung(model, schnitt(model, **kw))
    return d


if __name__ == "__main__":
    lauf("s9a_b7_schnitt", pruefen)
