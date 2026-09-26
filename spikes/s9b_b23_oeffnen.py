"""S9b Baustein 23: Gespeichertes Teil aus dem Arbeitsordner öffnen (für "swki pruefen").

Voraussetzung: Baustein 20 hat s9b_b20_teil.SLDPRT gespeichert.
ISldWorks.OpenDoc6(FileName, Type=swDocPART 1, Options=swOpenDocOptions_Silent 1, Configuration "",
Errors[byref], Warnings[byref]); zusätzlich OpenDoc7 über GetOpenDocSpec. Fälle: normal öffnen + messen,
Datei bereits offen, Datei fehlt, ReadOnly-Option.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import ARBEIT, partbox_mm, start, volumen_mm3
from spikes.s9b_gemeinsam import byref_long

TEIL = ARBEIT / "s9b_b20_teil.SLDPRT"
SW_DOC_PART = 1
SILENT, READONLY = 1, 2


def oeffne(app, pfad, options: int = SILENT):
    err, warn = byref_long(), byref_long()
    model = app.OpenDoc6(str(pfad), SW_DOC_PART, options, "", err, warn)
    return model, {"model": model is not None, "errors": err.value, "warnings": warn.value}


def offene_titel(app) -> list:
    out, d = [], app.GetFirstDocument
    while d is not None:
        out.append(d.GetTitle)
        d = d.GetNext
    return out


def pruefen() -> dict:
    r, app = start()
    d: dict = {"datei": str(TEIL), "existiert": TEIL.exists(), "offen_vorher": offene_titel(app)}
    mtime = TEIL.stat().st_mtime
    model, info = oeffne(app, TEIL)
    d["opendoc6"] = info
    titel = model.GetTitle
    try:
        d["opendoc6"].update({"titel": titel, "pfad": model.GetPathName, "typ": model.GetType,
                              "volumen_mm3": volumen_mm3(model), "partbox_mm": partbox_mm(model),
                              "aktiv_ist_model": app.IsSame(app.ActiveDoc, model) == 1,
                              "whatswrong": model.Extension.GetWhatsWrongCount, "saveflag": model.GetSaveFlag})
        # zweites Öffnen derselben Datei
        model2, info2 = oeffne(app, TEIL)
        info2["gleiches_objekt"] = (app.IsSame(model, model2) == 1) if model2 is not None else None
        info2["offen"] = offene_titel(app)
        d["opendoc6_bereits_offen"] = info2
        # OpenDoc7 über DocumentSpecification, ebenfalls bereits offen
        try:
            spec = app.GetOpenDocSpec(str(TEIL))
            spec.Silent = True
            m7 = app.OpenDoc7(spec)
            d["opendoc7_bereits_offen"] = {"model": m7 is not None, "error": spec.Error, "warning": spec.Warning,
                                           "gleiches_objekt": (app.IsSame(model, m7) == 1) if m7 is not None else None}
        except Exception as e:
            d["opendoc7_bereits_offen"] = {"fehler": repr(e)}
    finally:
        d["closedoc"] = app.CloseDoc(titel)
    d["offen_nach_close"] = offene_titel(app)
    d["datei_unveraendert"] = TEIL.stat().st_mtime == mtime
    # fehlende Datei
    m, info = oeffne(app, ARBEIT / "gibtsnicht.SLDPRT")
    d["opendoc6_fehlt"] = info
    # ReadOnly
    m, info = oeffne(app, TEIL, SILENT | READONLY)
    if m is not None:
        info["titel"] = m.GetTitle
        info["readonly"] = m.IsOpenedReadOnly
        app.CloseDoc(m.GetTitle)
    d["opendoc6_readonly"] = info
    # OpenDoc7 normal
    spec = app.GetOpenDocSpec(str(TEIL))
    spec.Silent = True
    m7 = app.OpenDoc7(spec)
    d["opendoc7"] = {"model": m7 is not None, "error": spec.Error, "warning": spec.Warning,
                     "doc_type": spec.DocumentType}
    if m7 is not None:
        d["opendoc7"]["volumen_mm3"] = volumen_mm3(m7)
        app.CloseDoc(m7.GetTitle)
    d["offen_am_ende"] = offene_titel(app)
    return d


if __name__ == "__main__":
    lauf("s9b_b23_oeffnen", pruefen)
