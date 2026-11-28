"""Spike Z1.3 Stufe 4, Teil f: Hülle Ⓔ an einem Zeichnungsmaß über das SolidWorks-Symbol.

Teil e hat gezeigt: Ein Suffix mit dem Unicode-Zeichen „Ⓔ“ (U+24BA) lässt den ganzen Maßtext verschwinden. Das war
auch der Grund, warum in Teil a die 200 fehlte. Die Symboldatei `lang/german/gtol97.sym` hat dafür `*EP, Encompassing`
(Kreis mit E). Hier wird geprüft, wie es als Suffix „ <MOD-EP>“ an einem Maß mit Passung H7 (FIT, FitDisplayStyle 3:
„200,00 H7“ in einer Zeile) aussieht. Dazu kommt ein Maß mit Präfix „4 × “ und Suffix „ (= 120)“ zur Gegenprobe.

    .venv\\Scripts\\python.exe -m spikes.z1_diag_stufe4f <zeichnung.SLDDRW> <teil.SLDPRT>
"""

import json
import sys
from pathlib import Path

from spikes.z1_diag_stufe4c import PRAEFIX, SUFFIX, SW_DOC_DRAWING, ansicht, gerade_kanten, masse_setzen, sha
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, callout_leer, verbinde
from swki.zeichnung.bemassen import _anzeige, kurzname
from swki.zeichnung.zeichnen import SAVE_SILENT, _ruf


def main(pfad: Path, teil: Path) -> None:
    app = verbinde(lade_rechner().sw_jahr)
    mu = mathutil(app)
    sha_teil = sha(teil)
    f, w = byref_long(), byref_long()
    drw = app.OpenDoc6(str(pfad), SW_DOC_DRAWING, 1, "", f, w)
    kopie = pfad.with_name(pfad.stem + "_s4f.SLDDRW")
    v = ansicht(drw, "Zeichenansicht1")
    k = gerade_kanten(mu, v, "f1")
    senk = [x for x in k if abs(x[1][0] - x[2][0]) < 0.05]
    links, rechts = min(senk, key=lambda x: x[1][0]), max(senk, key=lambda x: x[1][0])
    x_m = (links[1][0] + rechts[1][0]) / 2000
    werte = {}
    a, _ = masse_setzen(drw, v, [links[0], rechts[0]], (x_m, 0.095))
    tol = _ruf(a.GetDimension2(0), "Tolerance")
    tol.Type = 7
    werte["fit"] = tol.SetFitValues("H7", "")
    tol.FitDisplayStyle = 3
    werte["suffix_ep"] = a.SetText(SUFFIX, " <MOD-EP>")
    b, _ = masse_setzen(drw, v, [links[0], rechts[0]], (x_m, 0.080))
    b.SetText(PRAEFIX, "4 × ")
    b.SetText(SUFFIX, " (= 120)")
    namen = {kurzname(a): "fit_ep", kurzname(b): "zusatz"}
    _ruf(drw, "EditRebuild3")
    _ruf(drw, "Extension").SaveAs(str(kopie), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    drw = app.OpenDoc6(str(kopie), SW_DOC_DRAWING, 1, "", f, w)
    v = ansicht(drw, "Zeichenansicht1")
    for dd in _anzeige(v):
        if kurzname(dd) in namen:
            tol = _ruf(dd.GetDimension2(0), "Tolerance")
            werte[namen[kurzname(dd)]] = {"typ": _ruf(tol, "Type"), "passung": _ruf(tol, "GetHoleFitValue"),
                                          "praefix": dd.GetText(PRAEFIX), "suffix": dd.GetText(SUFFIX)}
    pdf = kopie.with_suffix(".pdf")
    _ruf(drw, "Extension").SaveAs(str(pdf), 0, SAVE_SILENT, callout_leer(), byref_long(), byref_long())
    for d in list(app.GetDocuments or ()):
        if "Z1S4-" in d.GetPathName:
            app.CloseDoc(d.GetTitle)
    werte["teil_sha_gleich"] = sha(teil) == sha_teil
    print(json.dumps(werte, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
