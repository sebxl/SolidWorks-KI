"""S9a Baustein 5: Gleichungen / globale Variablen.

Quader auf Ebene oben: Skizze "f1_skizze" mit Maß D1 (Breite X), Extrusion "f1" (Tiefe = Y).
"L" = 296; "D1@f1_skizze" = "L"; "D1@f1" = "L" / 10. Danach L per Equation-Setter auf 200 ändern.
"""

import pythoncom

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import ebenen, extrusion_blind, letztes, partbox_mm, select_mark, start, teil
from swki.verbindung import callout_leer

SW_INPUT_DIM_VAL_ON_CREATE = 10


def gleichung_setzen(em, index: int, text: str) -> None:
    """IEquationMgr.Equation(Index) = text – parametrisierte Property-Put per rohem Invoke."""
    dispid = em._oleobj_.GetIDsOfNames("Equation")
    em._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, text)


def _gleichungen(em) -> list:
    return [{"i": i, "text": em.Equation(i), "wert": em.Value(i), "global": em.GlobalVariable(i)}
            for i in range(em.GetCount)]


def pruefen() -> dict:
    r, app = start()
    d: dict = {"varianten": []}
    alt = app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE)
    try:
        app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, False)
        with teil(app, r) as model:
            oben = ebenen(model)[1]
            model.ClearSelection2(True)
            oben.Select2(False, 0)
            sm = model.SketchManager
            sm.InsertSketch(True)
            sm.AddToDB = True
            try:
                rect = sm.CreateCenterRectangle(0.0, 0.0, 0.0, 0.050, 0.030, 0.0)
            finally:
                sm.AddToDB = False
            model.ClearSelection2(True)
            select_mark(model, rect[0], 0, append=False)
            model.AddDimension2(0.0, 0.0, 0.045)
            model.ClearSelection2(True)
            sm.FullyDefineSketch(True, True, 1023, True, 1, callout_leer(), 1, callout_leer(), 1, 1)
            sm.InsertSketch(True)
            skf = letztes(model)
            skf.Name = "f1_skizze"
            model.ClearSelection2(True)
            skf.Select2(False, 0)
            ext = extrusion_blind(model, 0.020)
            ext.Name = "f1"
            dd = ext.GetFirstDisplayDimension
            d["extrusion_tiefe_mass"] = {"fullname": dd.GetDimension2(0).FullName, "name": dd.GetDimension2(0).Name}
            d["partbox_start_mm"] = partbox_mm(model)

            em = model.GetEquationMgr
            d["add_L"] = em.Add2(-1, '"L" = 296', True)
            d["status_nach_add_L"] = em.Status
            d["add_skizze"] = em.Add2(-1, '"D1@f1_skizze" = "L"', True)
            d["add_tiefe"] = em.Add2(-1, '"D1@f1" = "L" / 10', True)
            d["status_nach_add"] = em.Status
            d["add_ungueltig"] = em.Add2(-1, '"D9@gibtsnicht" = 5', True)
            d["status_nach_ungueltig"] = em.Status
            d["gleichungen_nach_add"] = _gleichungen(em)
            if d["add_ungueltig"] >= 0:
                d["delete_ungueltig"] = em.Delete(d["add_ungueltig"])
            d["evaluateall"] = em.EvaluateAll
            d["partbox_ohne_rebuild_mm"] = partbox_mm(model)
            d["editrebuild3"] = model.EditRebuild3
            d["partbox_L296_mm"] = partbox_mm(model)

            gleichung_setzen(em, 0, '"L" = 200')
            d["nach_setzen"] = {"text": em.Equation(0), "wert": em.Value(0), "status": em.Status}
            d["partbox_nach_setzen_vor_rebuild_mm"] = partbox_mm(model)
            em.EvaluateAll
            model.EditRebuild3
            d["partbox_L200_mm"] = partbox_mm(model)
            d["gleichungen_ende"] = _gleichungen(em)
            d["whatswrong_count"] = model.Extension.GetWhatsWrongCount
    finally:
        app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, alt)
    return d


if __name__ == "__main__":
    lauf("s9a_b5_gleichungen", pruefen)
