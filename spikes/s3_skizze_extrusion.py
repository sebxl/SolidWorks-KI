"""S3: Rechteck-Skizze voll bestimmt + Extrusion."""

from spikes._gemeinsam import lauf, letztes_feature, neues_teil, schliesse, standardebenen, start
from swki.api.bauen import api_db
from swki.api.index import enum
from swki.verbindung import callout_leer, mm, wert


def _status(model, skizze_feat, db) -> str:
    # GetSpecificFeature2/GetConstrainedStatus: gleiche Bindungs-Eigenart wie FirstFeature
    # (siehe spikes/_gemeinsam.py) – reiner Attributzugriff statt Aufruf mit "()".
    skizze = skizze_feat.GetSpecificFeature2
    code = wert(skizze.GetConstrainedStatus)
    namen = {e["wert"]: e["name"] for e in enum(db, "swConstrainedStatus_e")}
    return namen.get(code, str(code))


def pruefen() -> dict:
    r, app = start()
    db = api_db(r.sw_jahr)
    model = neues_teil(app, r)
    daten = {
        "abweichungen": [
            "GetSpecificFeature2 (IFeature) wird wie FirstFeature in _gemeinsam.py als reiner "
            "Attributzugriff ohne '()' aufgerufen (Bindungs-Eigenart, siehe dort).",
            "FullyDefineSketch: HorizontalDatumDisp/VerticalDatumDisp mit callout_leer() statt "
            "rohem Python None übergeben, sonst com_error 'Typenkonflikt' (arg 6).",
        ]
    }
    try:
        oben = standardebenen(model)[1]
        oben.Select2(False, 0)
        sm = model.SketchManager
        sm.InsertSketch(True)
        sm.CreateCenterRectangle(0.0, 0.0, 0.0, mm(50), mm(30), 0.0)
        # Variante A: FullyDefineSketch – Argumente gemäß "swki api methode ISketchManager.FullyDefineSketch"
        # (Index bestätigt 10 Parameter in dieser Reihenfolge; keine Abweichung zum Brief).
        try:
            relations_alle = sum(e["wert"] for e in enum(db, "swSketchFullyDefineRelationType_e"))
            # HorizontalDatumDisp/VerticalDatumDisp sind vom .NET-Typ System.Object; ein rohes
            # Python None löst com_error "Typenkonflikt" (arg 6) aus. Abweichung zum Brief:
            # callout_leer() (leeres VT_DISPATCH-VARIANT) statt None übergeben.
            daten["variante_a_rueckgabe"] = sm.FullyDefineSketch(
                True, True, relations_alle, True, 1, callout_leer(), 1, callout_leer(), 1, 1
            )
        except Exception as e:
            daten["variante_a_fehler"] = repr(e)
        sm.InsertSketch(True)
        skizze = letztes_feature(model)
        daten["status_nach_a"] = _status(model, skizze, db)
        model.ClearSelection2(True)
        skizze.Select2(False, 0)
        feat = model.FeatureManager.FeatureExtrusion3(
            True, False, False, 0, 0, mm(20), 0.0, False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True, 0, 0.0, False,
        )
        daten["extrusion"] = wert(feat.Name) if feat is not None else None
        daten["rebuild_fehler"] = wert(model.Extension.GetWhatsWrongCount) if hasattr(model.Extension, "GetWhatsWrongCount") else "n/a"
        return daten
    finally:
        schliesse(app, model)


if __name__ == "__main__":
    lauf("s3_skizze_extrusion", pruefen)
