"""S4: Volumen, Hüllquader, Screenshots der Standardansichten."""

from spikes._gemeinsam import kasten, lauf, neues_teil, schliesse, standardebenen, start
from swki.api.bauen import api_db
from swki.api.index import enum
from swki.verbindung import in_mm, in_mm3, wert


def pruefen() -> dict:
    r, app = start()
    db = api_db(r.sw_jahr)
    ansichten = {e["name"]: e["wert"] for e in enum(db, "swStandardViews_e")}
    model = neues_teil(app, r)
    try:
        kasten(model, standardebenen(model)[1], 100, 60, 20)
        # CreateMassProperty(): gleiche Bindungs-Eigenart wie FirstFeature (siehe _gemeinsam.py) –
        # reiner Attributzugriff statt Aufruf mit "()", sonst com_error "Mitglied nicht gefunden".
        mp = model.Extension.CreateMassProperty
        box = [in_mm(v) for v in model.GetPartBox(True)]
        ordner = r.arbeitsordner / "stufe0" / "s4"
        ordner.mkdir(parents=True, exist_ok=True)
        bilder = {}
        for name, enum_name in [("iso", "swIsometricView"), ("vorne", "swFrontView"),
                                ("oben", "swTopView"), ("rechts", "swRightView")]:
            model.ShowNamedView2("", ansichten[enum_name])
            model.ViewZoomtofit2  # Sub ohne Argumente: gleiche Bindungs-Eigenart, kein "()"
            for endung in ("png", "jpg"):
                pfad = ordner / f"{name}.{endung}"
                fehler = int(model.SaveAs3(str(pfad), 0, 3))  # Silent | Copy
                bilder[f"{name}.{endung}"] = {"fehler": fehler, "bytes": pfad.stat().st_size if pfad.exists() else 0}
        return {
            "abweichungen": [
                "CreateMassProperty und ViewZoomtofit2 werden wie FirstFeature in _gemeinsam.py "
                "als reiner Attributzugriff ohne '()' aufgerufen (Bindungs-Eigenart, siehe dort).",
            ],
            "volumen_mm3": in_mm3(wert(mp.Volume)),
            "volumen_soll_mm3": 120000.0,
            "oberflaeche_mm2": round(wert(mp.SurfaceArea) * 1e6, 3),
            "huellquader_mm": box,
            "bilder": bilder,
            "ordner": str(ordner),
        }
    finally:
        schliesse(app, model)


if __name__ == "__main__":
    lauf("s4_masse_screenshot", pruefen)
