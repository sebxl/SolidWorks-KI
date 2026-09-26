"""S9b Baustein 22: Geändertes, ungespeichertes Dokument per CloseDoc ohne Rückfrage schließen?

(a) Neues, nie gespeichertes Teil mit Features (GetSaveFlag True) -> CloseDoc(Titel).
(b) Gespeichertes Teil (Baustein 20) öffnen, Bohrung hinzufügen (GetSaveFlag True) -> CloseDoc(Titel);
    Datei auf der Platte muss unverändert bleiben (mtime, Größe), erneutes Öffnen zeigt altes Volumen.
Gemessen wird die Dauer von CloseDoc (ein modaler Dialog würde den Aufruf blockieren).
"""

import time

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import kasten_oben, neues_teil, start, volumen_mm3
from spikes.s9b_b14_lineares_muster import bohrung
from spikes.s9b_b23_oeffnen import TEIL, offene_titel, oeffne


def _close(app, titel) -> dict:
    t0 = time.perf_counter()
    ret = app.CloseDoc(titel)
    return {"rueckgabe": ret, "sekunden": round(time.perf_counter() - t0, 3),
            "noch_offen": titel in offene_titel(app)}


def pruefen() -> dict:
    r, app = start()
    d: dict = {"offen_vorher": offene_titel(app)}
    # (a)
    model, titel = neues_teil(app, r)
    kasten_oben(model, 100, 60, 20)
    d["neu_ungespeichert"] = {"titel": titel, "saveflag": model.GetSaveFlag, **_close(app, titel)}
    # (b)
    st = TEIL.stat()
    model, info = oeffne(app, TEIL)
    titel = model.GetTitle
    v0 = volumen_mm3(model)
    k = model.FirstFeature
    while k is not None and k.GetTypeName2 != "Extrusion":
        k = k.GetNextFeature
    bohrung(app, model, k, (0.030, 0.020, 0.015))
    d["gespeichert_geaendert"] = {"titel": titel, "open": info, "volumen_vorher": v0,
                                  "volumen_geaendert": volumen_mm3(model), "saveflag": model.GetSaveFlag,
                                  **_close(app, titel)}
    st2 = TEIL.stat()
    d["gespeichert_geaendert"]["datei_unveraendert"] = (st.st_mtime, st.st_size) == (st2.st_mtime, st2.st_size)
    model, _ = oeffne(app, TEIL)
    d["gespeichert_geaendert"]["volumen_nach_wiederoeffnen"] = volumen_mm3(model)
    app.CloseDoc(model.GetTitle)
    d["offen_am_ende"] = offene_titel(app)
    return d


if __name__ == "__main__":
    lauf("s9b_b22_schliessen", pruefen)
