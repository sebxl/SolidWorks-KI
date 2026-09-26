"""S9b Baustein 20: Speichern (.sldprt, .step) und Screenshots (png) per IModelDocExtension.SaveAs3.

Teil: Quader 100 x 60 x 20 mit Bohrung, Material 1.2312. Ziel: %USERPROFILE%\\.swki\\arbeit\\stufe0\\s9\\.
SaveAs3(Name, Version, Options, ExportData, AdvancedSaveAsOptions, Errors[byref], Warnings[byref]).
Achtung: nach dem Speichern als .sldprt ändert sich der Titel -> Schließen per neuem Titel.
Das gespeicherte Teil (s9b_b20_teil.SLDPRT) wird von Baustein 22/23 weiterverwendet.
"""

import time

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import ARBEIT, kasten_oben, neues_teil, start, volumen_mm3
from spikes.s9b_b14_lineares_muster import bohrung
from spikes.s9b_gemeinsam import byref_long
from swki.verbindung import callout_leer

SW_SAVEAS_CURRENT = 0
SILENT, COPY = 1, 2
ANSICHTEN = {"iso": 7, "vorne": 1, "oben": 5, "rechts": 4}   # swStandardViews_e

TEIL = ARBEIT / "s9b_b20_teil.SLDPRT"
STEP = ARBEIT / "s9b_b20_teil.step"


def saveas3(model, pfad, options: int) -> dict:
    err, warn = byref_long(), byref_long()
    t0 = time.perf_counter()
    ok = model.Extension.SaveAs3(str(pfad), SW_SAVEAS_CURRENT, options, callout_leer(), callout_leer(), err, warn)
    return {"pfad": str(pfad), "options": options, "rueckgabe": ok, "errors": err.value, "warnings": warn.value,
            "sekunden": round(time.perf_counter() - t0, 3),
            "datei_bytes": pfad.stat().st_size if pfad.exists() else None, "titel_danach": model.GetTitle,
            "pfad_danach": model.GetPathName}


def pruefen() -> dict:
    r, app = start()
    ARBEIT.mkdir(parents=True, exist_ok=True)
    d: dict = {"ordner": str(ARBEIT)}
    model, titel = neues_teil(app, r)
    try:
        k = kasten_oben(model, 100, 60, 20)
        bohrung(app, model, k, (-0.030, 0.020, -0.015))
        model.SetMaterialPropertyName2("", "SolidWorks DIN Materials", "1.2312 (40CrMnMoS8-6)")
        d["volumen_mm3"] = volumen_mm3(model)
        d["titel_vorher"] = titel
        d["saveflag_vorher"] = model.GetSaveFlag
        # STEP-Export zuerst (Dokument noch unbenannt) und danach .sldprt
        d["step"] = saveas3(model, STEP, SILENT)
        d["sldprt"] = saveas3(model, TEIL, SILENT)
        titel = model.GetTitle                                  # neuer Titel für CloseDoc
        d["saveflag_nach_speichern"] = model.GetSaveFlag
        d["step_ueberschreiben"] = saveas3(model, STEP, SILENT)  # vorhandene Datei überschreiben
        d["sldprt_ueberschreiben"] = saveas3(model, TEIL, SILENT)
        d["step_kopf"] = STEP.read_text(encoding="latin-1", errors="replace").splitlines()[:6]
        d["bilder"] = {}
        for name, vid in ANSICHTEN.items():
            model.ShowNamedView2("", vid)
            model.ViewZoomtofit2
            d["bilder"][name] = saveas3(model, ARBEIT / f"s9b_b20_{name}.png", SILENT | COPY)
        d["titel_nach_bildern"] = model.GetTitle
    finally:
        d["closedoc"] = app.CloseDoc(titel)
    return d


if __name__ == "__main__":
    lauf("s9b_b20_speichern", pruefen)
