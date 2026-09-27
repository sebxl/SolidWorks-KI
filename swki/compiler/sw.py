"""SolidWorks-Grundfunktionen für den Compiler (Late Binding, verifiziert in Spike S9a).

Regeln (siehe swki/wissen/pywin32-fallstricke.md): nullargumentige Member ohne "()",
Objekt-Parameter mit callout_leer(), Punkte/Arrays mit r8_array().
"""

from contextlib import contextmanager
from pathlib import Path

from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, REBUILD_FEHLER, SPEICHERN_FEHLGESCHLAGEN, BauFehler
from swki.verbindung import byref_long, byref_variant, callout_leer, in_mm, mm, r8_array

SW_INPUT_DIM_VAL_ON_CREATE = 10  # swUserPreferenceToggle_e.swInputDimValOnCreate
SW_FULLY_CONSTRAINED = 3  # swConstrainedStatus_e.swFullyConstrained
SW_SET_VALUE_IN_THIS_CONFIGURATION = 1  # swSetValueInConfiguration_e
SW_SAVEAS_CURRENT_VERSION = 0  # swSaveAsVersion_e
SW_SAVEAS_SILENT = 1  # swSaveAsOptions_e
SW_SAVEAS_COPY = 2


def neues_teil(app, vorlage: Path):
    model = app.NewDocument(str(vorlage), 0, 0, 0)
    if model is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"NewDocument mit {vorlage} fehlgeschlagen", schritt="dokument")
    return model


def schliesse(app, model) -> None:
    """Schließt genau dieses (selbst angelegte) Dokument."""
    app.CloseDoc(model.GetTitle)


def standardebenen(model) -> list:
    """[Ebene vorne, Ebene oben, Ebene rechts] – die ersten drei RefPlane-Features (sprachunabhängig)."""
    ebenen, f = [], model.FirstFeature
    while f is not None and len(ebenen) < 3:
        if f.GetTypeName2 == "RefPlane":
            ebenen.append(f)
        f = f.GetNextFeature
    return ebenen


def letztes_feature(model):
    return model.FeatureByPositionReverse(0)


def auswahl_leeren(model) -> None:
    model.ClearSelection2(True)


def waehle(model, objekt, marke: int = 0, anhaengen: bool = False) -> None:
    """Face, Edge, Feature oder Skizzensegment mit Marke selektieren (Select4 + SelectData)."""
    daten = model.SelectionManager.CreateSelectData
    daten.Mark = marke
    if not objekt.Select4(anhaengen, daten):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Auswahl mit Marke {marke} fehlgeschlagen", schritt="auswahl")


@contextmanager
def einstellung(app, toggle: int, wert: bool):
    """Benutzereinstellung nur vorübergehend umschalten; alter Wert wird immer wiederhergestellt."""
    alt = app.GetUserPreferenceToggle(toggle)
    app.SetUserPreferenceToggle(toggle, wert)
    try:
        yield
    finally:
        app.SetUserPreferenceToggle(toggle, alt)


@contextmanager
def ohne_inferenz(sketch_manager):
    """AddToDB=True: keine automatischen Beziehungen beim Erzeugen (S9a); danach immer zurück."""
    sketch_manager.AddToDB = True
    try:
        yield
    finally:
        sketch_manager.AddToDB = False


def ursprung(model):
    """Ursprungspunkt des Teils (Skizzenpunkt des Features "OriginProfileFeature"), sprachunabhängig.

    Bezug für die Lagemaße der Skizzen (swki.compiler.skizze).
    """
    f = model.FirstFeature
    while f is not None and f.GetTypeName2 != "OriginProfileFeature":
        f = f.GetNextFeature
    if f is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, "Ursprung nicht gefunden", schritt="skizze")
    auswahl_leeren(model)
    model.Extension.SelectByID2(f"Point1@{f.Name}", "EXTSKETCHPOINT", 0, 0, 0, False, 0, callout_leer(), 0)
    punkt = model.SelectionManager.GetSelectedObject6(1, -1)
    auswahl_leeren(model)
    if punkt is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, "Ursprungspunkt nicht auswählbar", schritt="skizze")
    return punkt


def mathutil(app):
    mu = app.GetMathUtility
    mu._FlagAsMethod("CreatePoint", "CreateVector", "CreateTransform")  # sonst Aufruf beim Attributzugriff
    return mu


def modell_zu_skizze(mu, skizze, punkt_mm) -> tuple[float, float]:
    """Modellpunkt (mm) → Skizzenkoordinaten (m) der offenen Skizze."""
    p = mu.CreatePoint(r8_array([mm(x) for x in punkt_mm]))
    u, v, _ = p.MultiplyTransform(skizze.ModelToSketchTransform).ArrayData
    return u, v


def teilebox_mm(model) -> list[float]:
    """[xmin, ymin, zmin, xmax, ymax, zmax] in mm."""
    return [in_mm(x) for x in model.GetPartBox(True)]


def rebuild(model) -> None:
    """Baut neu auf; wirft REBUILD_FEHLER mit Feature und Code, wenn SolidWorks Fehler meldet."""
    ok = model.EditRebuild3
    if model.Extension.GetWhatsWrongCount == 0 and ok:
        return
    features, codes, warnungen = byref_variant(), byref_variant(), byref_variant()
    model.Extension.GetWhatsWrong(features, codes, warnungen)
    fehler = [
        f"{f.Name}: Code {c}"
        for f, c, w in zip(features.value or (), codes.value or (), warnungen.value or ())
        if not w
    ]
    if fehler or not ok:
        raise BauFehler(REBUILD_FEHLER, "; ".join(fehler) or "EditRebuild3 meldet Fehler", schritt="rebuild")


def speichere(model, pfad: Path, kopie: bool = False) -> None:
    """IModelDocExtension.SaveAs3; Format über die Endung (.sldprt, .step, .png …).

    Ohne kopie wird das Dokument beim Speichern als .sldprt umbenannt (Titel danach neu lesen, S9b).
    """
    pfad.parent.mkdir(parents=True, exist_ok=True)
    fehler, warnungen = byref_long(), byref_long()
    optionen = SW_SAVEAS_SILENT | (SW_SAVEAS_COPY if kopie else 0)
    ok = model.Extension.SaveAs3(str(pfad), SW_SAVEAS_CURRENT_VERSION, optionen, callout_leer(), callout_leer(),
                                 fehler, warnungen)
    if not ok or fehler.value:
        raise BauFehler(SPEICHERN_FEHLGESCHLAGEN, f"{pfad.name}: Fehler {fehler.value}", schritt="speichern")
