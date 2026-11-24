"""Spike Z1.0, Diagnose zu Frage 4: Warum fügt InsertModelAnnotations keine Modellmaße ein? Varianten je frischer
Zeichnung. Wegwerf. Aufruf: .venv\\Scripts\\python.exe -m spikes.z1_diag_modellmasse <teil.SLDPRT>"""

import sys
import time
from pathlib import Path

from spikes.s9a_gemeinsam import start
from spikes.z1_zeichnung import SW_DEFAULT_TEMPLATE_DRAWING, SW_DOC_PART, anzeige_masse, oeffne, ruf, views
from swki.verbindung import callout_leer

VARIANTEN = {
    "IMA3_markiert_versteckte_Features": ("ima3_versteckt", 32768),
    "IMA4_alle_markiert_versteckte_Features": ("ima4_versteckt", 32768),
    "IMA4_alle_markiert_bohrung_versteckt": ("ima4_versteckt", 32768 | 1048576),
    "IMA3_alle_masse_8": ("ima3", 8),
    "IMA3_markiert_plus_masse_32776": ("ima3", 8 | 32768),
    "IMA3_markiert_und_nicht_557064": ("ima3", 8 | 32768 | 524288),
    "IMA4_alle_ansichten_markiert": ("ima4_alle", 32768),
    "ImportAnnotations_2025": ("import", None),
}


def zeichnung(app, vorlage, teil: Path):
    drw = app.NewDocument(vorlage, 0, 0, 0)
    ruf(drw, "GetCurrentSheet").SetProperties2(8, 13, 1, 1, True, 0.42, 0.297, True)
    drw.Create1stAngleViews2(str(teil))
    return drw


def main(teil: Path) -> None:
    r, app = start()
    vorlage = app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_DRAWING)
    oeffne(app, teil, SW_DOC_PART)
    for name, (art, typen) in VARIANTEN.items():
        drw = zeichnung(app, vorlage, teil)
        ext = ruf(drw, "Extension")
        t0 = time.time()
        try:
            if art == "ima3":
                for v in views(drw)[:3]:
                    vn = ruf(v, "GetName2")
                    ext.SelectByID2(vn, "DRAWINGVIEW", 0, 0, 0, False, 0, callout_leer(), 0)
                    drw.ActivateView(vn)
                    drw.ClearSelection2(True)
                    drw.InsertModelAnnotations3(0, typen, False, True, False, False)
            elif art == "ima3_versteckt":
                for v in views(drw)[:3]:
                    vn = ruf(v, "GetName2")
                    ext.SelectByID2(vn, "DRAWINGVIEW", 0, 0, 0, False, 0, callout_leer(), 0)
                    drw.ActivateView(vn)
                    drw.ClearSelection2(True)
                    drw.InsertModelAnnotations3(0, typen, False, False, True, False)
            elif art == "ima4_versteckt":
                ext.SelectByID2(ruf(views(drw)[0], "GetName2"), "DRAWINGVIEW", 0, 0, 0, False, 0, callout_leer(), 0)
                drw.ActivateView(ruf(views(drw)[0], "GetName2"))
                drw.ClearSelection2(True)
                drw.InsertModelAnnotations4(0, typen, True, False, True, False, False, False)
            elif art == "ima4_alle":
                ext.SelectByID2(ruf(views(drw)[0], "GetName2"), "DRAWINGVIEW", 0, 0, 0, False, 0, callout_leer(), 0)
                drw.ActivateView(ruf(views(drw)[0], "GetName2"))
                drw.ClearSelection2(True)
                drw.InsertModelAnnotations4(0, typen, True, True, False, False, False, False)
            else:
                for v in views(drw)[:3]:
                    v.ImportAnnotations(True, False, False, False, False)
            ergebnis = {ruf(v, "GetName2"): (len(anzeige_masse(v)), len(ruf(v, "GetAnnotations") or ())) for v in views(drw)}
            if art.endswith("versteckt"):
                ergebnis["beispiel"] = [ruf(d.GetDimension2(0), "FullName") for v in views(drw) for d in anzeige_masse(v)][:12]
        except Exception as e:
            ergebnis = repr(e)[:300]
        print(name, round(time.time() - t0, 2), "s", ergebnis, flush=True)
        app.CloseDoc(ruf(drw, "GetTitle"))
    app.CloseAllDocuments(True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
