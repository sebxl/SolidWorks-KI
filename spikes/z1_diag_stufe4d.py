"""Spike Z1.3 Stufe 4, Teil d. Ergebnisse aus Teil c (Zeichnungsmaße behalten Passung und Zusätze, Abmaße nicht) gezielt
nachprüfen:

1. Abmaße an Zeichnungsmaßen: `SetValues2` mit WhichConfigurations 1 lieferte False, das Maß zeigte „0,00/0,00“.
   Die Varianten -1 (swSetValue_NoConfiguration), 0 (UseCurrentSetting) und 2 (InAllConfigurations) sowie `SetValues`
   werden je an einem eigenen Maß über die äußeren waagrechten Kanten probiert.
2. Lage der Maße auf dem Blatt: In Teil c lagen A und C über dem Blattrand. Jetzt liegen alle Maße unter der Ansicht.
3. Maß zwischen zwei Kreiskanten (Bohrbild g1): Misst AddDimension2 von Mitte zu Mitte (30) wie das Modellmaß D3@m1?
4. Rauheit: In Teil c erschien von den sieben Textplätzen nur ProdMethod (M3) sichtbar über dem Symbol. Jetzt steht
   „Ra 0,8“ an diesem Platz.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_stufe4d <zeichnung.SLDDRW> <teil.SLDPRT>
"""

import json
import sys
from pathlib import Path

from spikes.z1_diag_stufe4c import (EINE_KONFIG, FUEHRUNG_GERADE, PFEIL_ZU, PRAEFIX, SF_BEARBEITET, SUFFIX,
                                    SW_DOC_DRAWING, TOL_BILAT, TOL_FIT, KANTE, ansicht, gerade_kanten, kreiskante,
                                    masse_setzen, sha, wert_mm)
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, r8_array, verbinde
from swki.zeichnung.bemassen import _anzeige, kurzname
from swki.zeichnung.zeichnen import SAVE_SILENT, _ruf


def kreise(mu, v, merkmal: str) -> list[tuple]:
    t = _ruf(v, "ModelToViewTransform")
    aus = []
    for k in list(v.GetVisibleEntities2(callout_leer(), KANTE) or ()):
        try:
            c = _ruf(k, "GetCurve")
            if not _ruf(c, "IsCircle"):
                continue
            namen = {_ruf(_ruf(f, "GetFeature"), "Name") for f in list(_ruf(k, "GetTwoAdjacentFaces2") or ()) if f}
            if merkmal not in namen:
                continue
            cx, cy, cz = list(_ruf(c, "CircleParams"))[:3]
            q = mu.CreatePoint(r8_array([cx, cy, cz])).MultiplyTransform(t).ArrayData
            aus.append((k, (round(q[0] * 1000, 2), round(q[1] * 1000, 2))))
        except Exception:  # noqa: BLE001
            continue
    return sorted(aus, key=lambda x: x[1])


def lies(v, namen: set[str]) -> dict:
    aus = {}
    for dd in _anzeige(v):
        n = kurzname(dd)
        if n not in namen:
            continue
        tol = _ruf(dd.GetDimension2(0), "Tolerance")
        aus[n] = {"wert": wert_mm(dd), "tol_typ": _ruf(tol, "Type"), "min": _ruf(tol, "GetMinValue"),
                  "max": _ruf(tol, "GetMaxValue"), "passung": _ruf(tol, "GetHoleFitValue"),
                  "praefix": dd.GetText(PRAEFIX), "suffix": dd.GetText(SUFFIX)}
    sf, s = [], _ruf(v, "GetFirstSFSymbol")
    while s is not None:
        sf.append([s.GetText(i) for i in range(10)])
        s = _ruf(s, "GetNext")
    aus["rauheit"] = sf
    return aus


def main(pfad: Path, teil: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    mu = mathutil(app)
    sha_teil = sha(teil)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    ext = _ruf(drw, "Extension")
    kopie = pfad.with_name(pfad.stem + "_s4d.SLDDRW")
    v = ansicht(drw, "Zeichenansicht1")
    k = gerade_kanten(mu, v, "f1")
    senk = [x for x in k if abs(x[1][0] - x[2][0]) < 0.05]
    waag = [x for x in k if abs(x[1][1] - x[2][1]) < 0.05]
    links, rechts = min(senk, key=lambda x: x[1][0]), max(senk, key=lambda x: x[1][0])
    unten, oben = min(waag, key=lambda x: x[1][1]), max(waag, key=lambda x: x[1][1])
    x_m, y_m = (links[1][0] + rechts[1][0]) / 2000, unten[1][1] / 1000
    werte, namen = {}, set()
    varianten = {"bilat_-1": -1, "bilat_0": 0, "bilat_2": 2, "bilat_setvalues": None}
    for i, (name, wahl) in enumerate(varianten.items()):
        dd, gew = masse_setzen(drw, v, [unten[0], oben[0]], (rechts[1][0] / 1000 + 0.035 + 0.012 * i, (unten[1][1] + oben[1][1]) / 2000))
        if dd is None:
            werte[name] = {"gesetzt": False, "gewaehlt": gew}
            continue
        tol = _ruf(dd.GetDimension2(0), "Tolerance")
        tol.Type = TOL_BILAT
        erg = tol.SetValues(-0.00005, 0.0001) if wahl is None else tol.SetValues2(-0.00005, 0.0001, wahl, None)
        werte[name] = {"name": kurzname(dd), "rueckgabe": erg}
        namen.add(kurzname(dd))
    a, _ = masse_setzen(drw, v, [links[0], rechts[0]], (x_m, y_m - 0.035))
    if a is not None:
        tol = _ruf(a.GetDimension2(0), "Tolerance")
        tol.Type = TOL_FIT
        werte["fit"] = {"name": kurzname(a), "rueckgabe": tol.SetFitValues("H7", ""), "suffix": a.SetText(SUFFIX, " Ⓔ")}
        namen.add(kurzname(a))
    kr = kreise(mu, v, "g1")
    werte["kreise_g1"] = [p for _, p in kr]
    if len(kr) >= 2:
        c, gew = masse_setzen(drw, v, [kr[0][0], kr[1][0]], ((kr[0][1][0] + kr[1][1][0]) / 2000, kr[0][1][1] / 1000 + 0.02))
        if c is not None:
            werte["kreis_mass"] = {"name": kurzname(c), "wert": wert_mm(c), "gewaehlt": gew,
                                   "praefix": c.SetText(PRAEFIX, "4 × "), "suffix": c.SetText(SUFFIX, " (= 120)")}
            namen.add(kurzname(c))
    kk = kreiskante(v, "st") or kreiskante(v, "st_fase")
    drw.ClearSelection2(True)
    if kk is not None:
        v.SelectEntity(kk, False)
    sf = ext.InsertSurfaceFinishSymbol3(SF_BEARBEITET, FUEHRUNG_GERADE, 0.30, 0.12, 0, 0, PFEIL_ZU,
                                        "", "", "Ra 0,8", "", "", "", "")
    if sf is not None:
        _ruf(sf, "GetAnnotation").SetPosition2(0.30, 0.12, 0)
    drw.ClearSelection2(True)
    _ruf(drw, "EditRebuild3")
    werte["vor"] = lies(v, namen)
    ext.SaveAs(str(kopie), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    drw = app.OpenDoc6(str(kopie), SW_DOC_DRAWING, 1, "", f, w)
    v = ansicht(drw, "Zeichenansicht1")
    werte["nach"] = lies(v, namen)
    pdf = kopie.with_suffix(".pdf")
    _ruf(drw, "Extension").SaveAs(str(pdf), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    werte["teil_sha_gleich"] = sha(teil) == sha_teil
    print(json.dumps(werte, ensure_ascii=False, indent=1, default=str))
    import pymupdf
    with pymupdf.open(pdf) as doc:
        text = doc[0].get_text()
        doc[0].get_pixmap(dpi=110).save(str(pdf.with_suffix(".png")))
    print("PDF:", {t: t in text for t in ("H7", "Ⓔ", "+0,10", "-0,05", "−0,05", "4 × 30,00 (= 120)", "Ra 0,8")})
    print([z for z in text.splitlines() if any(s in z for s in ("H7", "0,1", "0,05", "Ra", "×"))])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
