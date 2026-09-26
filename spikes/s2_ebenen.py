"""S2: Sprachunabhängige Standardebenen."""

from spikes._gemeinsam import lauf, letztes_feature, neues_teil, schliesse, standardebenen, start
from swki.verbindung import wert


def pruefen() -> dict:
    r, app = start()
    model = neues_teil(app, r)
    try:
        ebenen = standardebenen(model)
        namen = [wert(e.Name) for e in ebenen]
        skizzen = []
        for e in ebenen:
            model.ClearSelection2(True)
            e.Select2(False, 0)
            model.SketchManager.InsertSketch(True)
            model.SketchManager.CreateCircleByRadius(0.0, 0.0, 0.0, 0.01)
            model.SketchManager.InsertSketch(True)
            skizzen.append(wert(letztes_feature(model).Name))
        return {"ebenen": namen, "anzahl": len(ebenen), "skizzen": skizzen}
    finally:
        schliesse(app, model)


if __name__ == "__main__":
    lauf("s2_ebenen", pruefen)
