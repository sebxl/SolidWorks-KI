"""Spike Z1.3 Stufe 4, Teil e. In Teil d blieb die Passung (Typ 7, H7) zwar erhalten, aber das Maß selbst war unsichtbar.
Schon in Teil a verschwand die Zahl 200 des Modellmaßes, sobald es eine Passung bekam.

Hier wird der Darstellungsweg gesucht. Fünf Zeichnungsmaße 200 liegen untereinander im freien Feld unter dem Schnitt:
- FIT mit FitDisplayStyle 0, 1 und 2,
- FITWITHTOL (8),
- ohne Toleranz, dafür mit dem Suffix „ H7 Ⓔ“ (Rückfallweg; Ⓔ in der Schrift des Blatts?).

    .venv\\Scripts\\python.exe -m spikes.z1_diag_stufe4e <zeichnung.SLDDRW> <teil.SLDPRT>
"""

import json
import sys
from pathlib import Path

from spikes.z1_diag_stufe4c import SUFFIX, SW_DOC_DRAWING, ansicht, gerade_kanten, masse_setzen, sha, wert_mm
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, verbinde
from swki.zeichnung.bemassen import _anzeige, kurzname
from swki.zeichnung.zeichnen import SAVE_SILENT, _ruf

VARIANTEN = [("fit_stil0", 7, 0), ("fit_stil1", 7, 1), ("fit_stil2", 7, 2), ("fitwithtol", 8, None), ("suffix", 0, None)]


def main(pfad: Path, teil: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    mu = mathutil(app)
    sha_teil = sha(teil)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    assert drw is not None, f.value
    kopie = pfad.with_name(pfad.stem + "_s4e.SLDDRW")
    v = ansicht(drw, "Zeichenansicht1")
    k = gerade_kanten(mu, v, "f1")
    senk = [x for x in k if abs(x[1][0] - x[2][0]) < 0.05]
    links, rechts = min(senk, key=lambda x: x[1][0]), max(senk, key=lambda x: x[1][0])
    x_m = (links[1][0] + rechts[1][0]) / 2000
    werte, namen = {}, {}
    for i, (name, typ, stil) in enumerate(VARIANTEN):
        dd, gew = masse_setzen(drw, v, [links[0], rechts[0]], (x_m, 0.095 - 0.012 * i))
        if dd is None:
            werte[name] = {"gesetzt": False, "gewaehlt": gew}
            continue
        tol = _ruf(dd.GetDimension2(0), "Tolerance")
        e = {"name": kurzname(dd)}
        if typ:
            tol.Type = typ
            e["fit"] = tol.SetFitValues("H7", "")
            if stil is not None:
                tol.FitDisplayStyle = stil
            e["stil"] = _ruf(tol, "FitDisplayStyle")
        else:
            e["suffix"] = dd.SetText(SUFFIX, " H7 Ⓔ")
        werte[name] = e
        namen[kurzname(dd)] = name
    _ruf(drw, "EditRebuild3")
    _ruf(drw, "Extension").SaveAs(str(kopie), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    drw = app.OpenDoc6(str(kopie), SW_DOC_DRAWING, 1, "", f, w)
    v = ansicht(drw, "Zeichenansicht1")
    for dd in _anzeige(v):
        n = kurzname(dd)
        if n in namen:
            tol = _ruf(dd.GetDimension2(0), "Tolerance")
            werte[namen[n]]["nach"] = {"typ": _ruf(tol, "Type"), "passung": _ruf(tol, "GetHoleFitValue"),
                                       "stil": _ruf(tol, "FitDisplayStyle"), "suffix": dd.GetText(SUFFIX),
                                       "wert": wert_mm(dd)}
    pdf = kopie.with_suffix(".pdf")
    _ruf(drw, "Extension").SaveAs(str(pdf), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    werte["teil_sha_gleich"] = sha(teil) == sha_teil
    print(json.dumps(werte, ensure_ascii=False, indent=1, default=str))
    import pymupdf
    with pymupdf.open(pdf) as doc:
        s = doc[0]
        s.get_pixmap(dpi=110).save(str(pdf.with_suffix(".png")))
        print([z for z in s.get_text().splitlines() if "200" in z or "H7" in z or "Ⓔ" in z])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
