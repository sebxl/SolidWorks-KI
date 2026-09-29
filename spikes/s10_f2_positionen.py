"""S10 Frage 2: mehrere Positionen in einem Bohrungsassistent-Feature, Positionsskizze voll bestimmt.

Block 100 × 60 × 30 (Y 0…30), Gewinde M8 blind 16 / Gewinde 12 an (u, v) = (−30, 10), (0, 10), (30, 10) auf der
Deckfläche (Modell X = u, Z = −v). Soll je Loch 605,80 mm³ (S9b).
A) alle Positionen per SelectByRay (Marke 0, angehängt) vor HoleWizard5.
B) eine Position per SelectByRay, danach die Positionsskizze öffnen (Select2 + InsertSketch, wie S9b), die übrigen
   Punkte mit CreatePoint anlegen (AddToDB) und alle Punkte mit dem Skizzierer des Compilers zum Ursprung bemaßen;
   Maße per Gleichung an L binden, dann L = 120 → äußere Achsen bei X = ±40.
Je Variante: Positionsskizze erkennbar (Unterskizze ohne Segmente?), Punktzahl (GetSketchPointCount), Bestimmtheit,
Volumenabnahme, Achslagen.
"""

import pythoncom

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import flaeche_mit_normale, kasten_oben, start, teil, volumen_mm3
from spikes.s9b_gemeinsam import whatswrong
from spikes.s10_gemeinsam import DICKE_MM, bohrung, geometrie, kontext, unterfeatures
from swki.compiler import sw
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.skizze import Skizzierer, ebene_aus_flaeche
from swki.compiler.topologie import flaeche_aus

POSITIONEN = [["=-L/2+20", 10], [0, 10], ["=L/2-20", 10]]
SOLL_JE_LOCH = 605.80


def _achsen(f) -> list:
    return sorted({tuple(z["achse_xz"]) for z in geometrie(f)["zylinder"]})


def variante_a(app, r) -> dict:
    with teil(app, r) as model:
        kasten_oben(model, 100, 60, DICKE_MM)
        v0 = volumen_mm3(model)
        treffer, f = bohrung(model, "gewinde", "M8", [(-30.0, -10.0), (0.0, -10.0), (30.0, -10.0)],
                             tiefe_mm=16, gewindetiefe_mm=12)
        if f is None:
            return {"selectbyray": treffer, "feature": None, "whatswrong": whatswrong(model)}
        return {"selectbyray": treffer, "feature": f.Name, "punkte": f.GetDefinition.GetSketchPointCount,
                "abnahme_mm3": round(v0 - volumen_mm3(model), 3), "soll_mm3": round(3 * SOLL_JE_LOCH, 2),
                "achsen_xz": _achsen(f), "unterfeatures": unterfeatures(f), "whatswrong": whatswrong(model)}


def _positionsskizze(f):
    s = f.GetFirstSubFeature
    while s is not None:
        if s.GetTypeName2 == "ProfileFeature" and not (s.GetSpecificFeature2.GetSketchSegments or ()):
            return s
        s = s.GetNextSubFeature
    return None


def variante_b(app, r) -> dict:
    with teil(app, r) as model:
        kasten = kasten_oben(model, 100, 60, DICKE_MM)
        globale_variablen(model, {"L": 100})
        ctx = kontext(app, model, {"L": 100})
        v0 = volumen_mm3(model)
        _, f = bohrung(model, "gewinde", "M8", [(-30.0, -10.0)], tiefe_mm=16, gewindetiefe_mm=12)
        d: dict = {"unterfeatures_vorher": unterfeatures(f)}
        skizze = _positionsskizze(f)
        if skizze is None:
            return {**d, "fehler": "keine Unterskizze ohne Segmente"}
        se = ebene_aus_flaeche(flaeche_aus(flaeche_mit_normale(kasten, (0.0, 1.0, 0.0))))
        sm = model.SketchManager
        model.ClearSelection2(True)
        skizze.Select2(False, 0)
        sm.InsertSketch(True)  # öffnet die selektierte Skizze (S9b)
        masse = []
        try:
            sk = Skizzierer(ctx, se, sm.ActiveSketch)
            with sw.einstellung(app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
                d["createpoint"] = []
                for u, v in POSITIONEN[1:]:
                    x, y = sk.zu_skizze(ctx.wert(u), ctx.wert(v))
                    d["createpoint"].append(sm.CreatePoint(x, y, 0.0) is not None)
                for p in POSITIONEN:
                    sk.lage(p, (ctx.wert(p[0]) + 8, ctx.wert(p[1]) + 8))
            d["status_offen"] = sm.ActiveSketch.GetConstrainedStatus
            masse = sk.masse
        except Exception as e:  # Spike: alles protokollieren
            d["fehler"] = repr(e)
        finally:
            sm.InsertSketch(True)
        skizze.Name = "f2_positionen"
        for m in masse:
            ctx.verknuepfe(f"{m.name}@f2_positionen", m.roh, m.vorzeichen)
        d["rebuild"] = model.EditRebuild3
        d["status"] = skizze.GetSpecificFeature2.GetConstrainedStatus
        d["punkte"] = f.GetDefinition.GetSketchPointCount
        d["abnahme_mm3"] = round(v0 - volumen_mm3(model), 3)
        d["soll_mm3"] = round(3 * SOLL_JE_LOCH, 2)
        d["achsen_xz"] = _achsen(f)
        d["masse"] = [f"{m.name}@f2_positionen = {m.roh}" for m in masse]
        g = model.GetEquationMgr
        texte = [g.Equation(i) for i in range(g.GetCount)]
        d["gleichungen"] = texte
        dispid = g._oleobj_.GetIDsOfNames("Equation")
        g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, texte.index('"L" = 100'), '"L" = 120')
        g.EvaluateAll
        d["rebuild_l120"] = model.EditRebuild3
        d["achsen_xz_l120"] = _achsen(f)  # Soll: (−40, −10), (0, −10), (40, −10)
        d["whatswrong"] = whatswrong(model)
        d["unterfeatures_nachher"] = unterfeatures(f)
        return d


def pruefen() -> dict:
    r, app = start()
    return {"a_selectbyray_mehrfach": variante_a(app, r), "b_positionsskizze": variante_b(app, r)}


if __name__ == "__main__":
    lauf("s10_f2_positionen", pruefen)
