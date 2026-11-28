"""Spike Z1.3 Stufe 4, Teil h (Review Task 5, C2/I4): Hinweislinien der Anmerkungen.

1. Kante an einem gewählten Punkt wählen (`IModelDocExtension.SelectByID2("", "EDGE", x, y, …)`): setzt die
   Hinweislinie eines Rauheitssymbols, Rahmens und Bezugsdreiecks dort an? Rückgelesen über
   `IAnnotation.GetLeaderPointsAtIndex`.
2. Mehrfachauswahl (zwei Kreiskanten der Stiftbohrungen, Taschenböden t1 und s1) vor dem Einfügen: entstehen mehrere
   Hinweislinien (`IAnnotation.GetLeaderCount`)?
3. Rahmen: Text über dem Rahmen „2 ×“ (`IGtol.SetText(swGTolTextCalloutAbove = 3, …)`).

    .venv\\Scripts\\python.exe -m spikes.z1_diag_stufe4h <zeichnung.SLDDRW> <teil.SLDPRT>
"""

import json
import math
import sys
from pathlib import Path

from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, verbinde
from swki.zeichnung import anforderungen_setzen as an
from swki.zeichnung.zeichnen import SAVE_SILENT, _ruf

UEBER_RAHMEN = 3  # swGTolTextParts_e.swGTolTextCalloutAbove


def ansichten(drw) -> dict:
    aus, v = {}, _ruf(drw, "GetFirstView")
    while v is not None:
        aus[_ruf(v, "GetName2")] = v
        v = _ruf(v, "GetNextView")
    return aus


def hinweislinien(ann) -> list:
    aus = []
    for i in range(_ruf(ann, "GetLeaderCount") or 0):
        p = list(ann.GetLeaderPointsAtIndex(i) or ())
        aus.append([[round(p[k] * 1000, 2), round(p[k + 1] * 1000, 2)] for k in range(0, len(p) - 2, 3)])
    return aus


def am_punkt(drw, punkt) -> tuple[bool, int]:
    drw.ClearSelection2(True)
    ok = _ruf(drw, "Extension").SelectByID2("", "EDGE", punkt[0] / 1000, punkt[1] / 1000, 0, True, 0, callout_leer(), 0)
    sm = _ruf(drw, "SelectionManager")
    return bool(ok), [sm.GetSelectedObjectType3(i, -1) for i in range(1, sm.GetSelectedObjectCount2(-1) + 1)]


def main(pfad: Path, teil: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    mu = mathutil(app)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), 3, 1, "", f, w)
    ext = _ruf(drw, "Extension")
    uebergabe = json.loads((pfad.parent / "zeichnung.json").read_text(encoding="utf-8"))
    alle = ansichten(drw)
    haupt, drauf = alle[uebergabe["ansichten"]["haupt"]], alle[uebergabe["ansichten"]["drauf"]]
    werte = {}
    kh, kd = an.sichtbare_kanten(mu, haupt), an.sichtbare_kanten(mu, drauf)
    stifte = sorted({(round(k.kreis[0][0], 2), round(k.kreis[0][1], 2), round(k.kreis[1], 3))
                     for k in kh if k.kreis and "st" in k.features}, key=lambda t: (t[2], t[0]))[:2]
    boden_t1 = an.endkante(kd, {"t1"}, 1, -1)
    boden_s1 = an.endkante(kd, {"s1"}, 1, -1)
    werte["stifte"], werte["boden"] = stifte, [(k.a, k.e) if k else None for k in (boden_t1, boden_s1)]
    # 1. Punktwahl: Rauheit an t1 bei 30 % der Kante, Rahmen bei 70 %, Bezug an der Unterseite bei 20 %
    a, e = boden_t1.a, boden_t1.e
    p30 = (a[0] + 0.3 * (e[0] - a[0]), a[1] + 0.3 * (e[1] - a[1]))
    p70 = (a[0] + 0.7 * (e[0] - a[0]), a[1] + 0.7 * (e[1] - a[1]))
    drw.ActivateView(_ruf(drauf, "GetName2"))
    werte["wahl_30"] = am_punkt(drw, p30)
    sf = ext.InsertSurfaceFinishSymbol3(1, 1, p30[0] / 1000 + 0.02, p30[1] / 1000 + 0.03, 0, 0, 1, *([""] * 7))
    if sf is not None:
        sf.SetText(8, "Ra 1,6")
        _ruf(sf, "GetAnnotation").SetPosition2(p30[0] / 1000 + 0.02, p30[1] / 1000 + 0.03, 0)
        werte["rauheit_punkt"] = {"soll": p30, "linien": hinweislinien(_ruf(sf, "GetAnnotation"))}
    werte["wahl_70"] = am_punkt(drw, p70)
    gt = _ruf(drw, "InsertGtol")
    if gt is not None:
        gt.SetFrameSymbols2(1, "<IGTOL-PARA>", False, "", False, "", "", "", "")
        gt.SetFrameValues2(1, "0,05", "", "A", "", "")
        werte["rahmen_text_oben"] = gt.SetText(UEBER_RAHMEN, "2 ×")
        _ruf(gt, "GetAnnotation").SetPosition2(p70[0] / 1000 + 0.01, p70[1] / 1000 + 0.035, 0)
        werte["rahmen_punkt"] = {"soll": p70, "linien": hinweislinien(_ruf(gt, "GetAnnotation")),
                                 "text_oben": gt.GetText(UEBER_RAHMEN)}
    unten = an.endkante(kd, {"f1"}, 1, -1)
    p20 = (unten.a[0] + 0.2 * (unten.e[0] - unten.a[0]), unten.a[1] + 0.2 * (unten.e[1] - unten.a[1]))
    werte["wahl_20"] = am_punkt(drw, p20)
    tag = _ruf(drw, "InsertDatumTag2")
    if tag is not None:
        tag.SetLabel("A")
        _ruf(tag, "GetAnnotation").SetPosition2(p20[0] / 1000, p20[1] / 1000 + 0.012, 0)
        werte["bezug_punkt"] = {"soll": p20, "linien": hinweislinien(_ruf(tag, "GetAnnotation"))}
    # 2. Mehrfachauswahl
    drw.ActivateView(_ruf(haupt, "GetName2"))
    drw.ClearSelection2(True)
    kreise = [k for k in kh if k.kreis and "st" in k.features and abs(k.kreis[1] - stifte[0][2]) < 1e-3]
    for i, k in enumerate(kreise[:2]):
        haupt.SelectEntity(k.obj, i > 0)
    werte["zwei_kreise_gewaehlt"] = _ruf(drw, "SelectionManager").GetSelectedObjectCount2(-1)
    sf2 = ext.InsertSurfaceFinishSymbol3(1, 1, 0.2, 0.25, 0, 0, 1, *([""] * 7))
    if sf2 is not None:
        sf2.SetText(8, "Ra 0,8")
        werte["rauheit_zwei"] = hinweislinien(_ruf(sf2, "GetAnnotation"))
    drw.ActivateView(_ruf(drauf, "GetName2"))
    drw.ClearSelection2(True)
    drauf.SelectEntity(boden_t1.obj, False)
    if boden_s1 is not None:
        drauf.SelectEntity(boden_s1.obj, True)
    gt2 = _ruf(drw, "InsertGtol")
    if gt2 is not None:
        gt2.SetFrameSymbols2(1, "<IGTOL-PARA>", False, "", False, "", "", "", "")
        gt2.SetFrameValues2(1, "0,05", "", "A", "", "")
        _ruf(gt2, "GetAnnotation").SetPosition2(0.2, 0.09, 0)
        werte["rahmen_zwei"] = hinweislinien(_ruf(gt2, "GetAnnotation"))
    drw.ClearSelection2(True)
    _ruf(drw, "EditRebuild3")
    pdf = pfad.with_name(pfad.stem + "_s4h.pdf")
    ext.SaveAs(str(pdf), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    import pymupdf
    with pymupdf.open(pdf) as doc:
        doc[0].get_pixmap(dpi=110).save(str(pdf.with_suffix(".png")))
    print(json.dumps(werte, ensure_ascii=False, indent=1, default=str))
    _ = math


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
