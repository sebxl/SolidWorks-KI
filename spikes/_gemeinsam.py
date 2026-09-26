"""Hilfen für Machbarkeitstests (Stufe 0). Kein Produktionscode."""

import json
import traceback
from pathlib import Path

from swki.konfig import PROJEKT, lade_rechner
from swki.verbindung import mm, verbinde, wert

ERGEBNISSE = PROJEKT / "docs" / "stufe0" / "ergebnisse"


def start():
    r = lade_rechner()
    return r, verbinde(r.sw_jahr)


def neues_teil(app, r):
    model = app.NewDocument(str(r.vorlage_teil), 0, 0, 0)
    if model is None:
        raise RuntimeError(f"NewDocument mit {r.vorlage_teil} fehlgeschlagen")
    return model


def neue_baugruppe(app, r):
    if r.vorlage_baugruppe is None:
        raise RuntimeError("Keine Baugruppenvorlage in config/rechner.yaml")
    model = app.NewDocument(str(r.vorlage_baugruppe), 0, 0, 0)
    if model is None:
        raise RuntimeError(f"NewDocument mit {r.vorlage_baugruppe} fehlgeschlagen")
    return model


def standardebenen(model) -> list:
    # FirstFeature/GetNextFeature sind laut sldworks.tlb Property-Get-artig gebunden:
    # pywin32 (dynamic dispatch) ruft sie schon beim Attributzugriff auf und liefert direkt
    # das IFeature-Objekt zurück. Ein zusätzliches "()" – auch über wert(), da jedes
    # CDispatch-Objekt selbst __call__ definiert und damit fälschlich "callable" ist –
    # scheitert dann mit com_error "Mitglied nicht gefunden". Daher reiner Attributzugriff.
    ebenen = []
    f = model.FirstFeature
    while f is not None and len(ebenen) < 3:
        if wert(f.GetTypeName2) == "RefPlane":
            ebenen.append(f)
        f = f.GetNextFeature
    return ebenen


def letztes_feature(model):
    return model.FeatureByPositionReverse(0)


def kasten(model, ebene, breite, hoehe, tiefe, mitte=(0.0, 0.0)):
    """Rechteck-Skizze auf ebene + Extrusion blind (alle Maße in mm)."""
    model.ClearSelection2(True)
    ebene.Select2(False, 0)
    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.CreateCenterRectangle(mm(mitte[0]), mm(mitte[1]), 0.0, mm(mitte[0] + breite / 2), mm(mitte[1] + hoehe / 2), 0.0)
    sm.InsertSketch(True)
    skizze = letztes_feature(model)
    model.ClearSelection2(True)
    skizze.Select2(False, 0)
    feat = model.FeatureManager.FeatureExtrusion3(
        True, False, False, 0, 0, mm(tiefe), 0.0, False, False, False, False, 0.0, 0.0,
        False, False, False, False, True, True, True, 0, 0.0, False,
    )
    if feat is None:
        raise RuntimeError("FeatureExtrusion3 lieferte None")
    return feat


def speichere(model, pfad: Path) -> int:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    return int(model.SaveAs3(str(pfad), 0, 1))  # swSaveAsCurrentVersion, swSaveAsOptions_Silent


def schliesse(app, model) -> None:
    app.CloseDoc(wert(model.GetTitle))


def lauf(name: str, fn) -> dict:
    try:
        ergebnis = {"ok": True, **fn()}
    except Exception as e:  # Spike: alles protokollieren
        ergebnis = {"ok": False, "fehler": repr(e), "trace": traceback.format_exc()}
    ERGEBNISSE.mkdir(parents=True, exist_ok=True)
    (ERGEBNISSE / f"{name}.json").write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str))
    return ergebnis
