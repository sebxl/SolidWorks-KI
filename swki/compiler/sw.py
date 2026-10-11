"""SolidWorks-Grundfunktionen für den Compiler (Late Binding, verifiziert in Spike S9a).

Regeln (siehe swki/wissen/pywin32-fallstricke.md): nullargumentige Member ohne "()",
Objekt-Parameter mit callout_leer(), Punkte/Arrays mit r8_array().
"""

from contextlib import contextmanager
from pathlib import Path

from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, REBUILD_FEHLER, SPEICHERN_FEHLGESCHLAGEN, BauFehler
from swki.konfig import lade_rechner
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
def einstellung_int(app, wert_id: int, wert: int):
    """Wie einstellung(), aber für Integer-Benutzereinstellungen (Get/SetUserPreferenceIntegerValue)."""
    alt = app.GetUserPreferenceIntegerValue(wert_id)
    app.SetUserPreferenceIntegerValue(wert_id, wert)
    try:
        yield
    finally:
        app.SetUserPreferenceIntegerValue(wert_id, alt)


@contextmanager
def ohne_inferenz(sketch_manager):
    """AddToDB=True: keine automatischen Beziehungen beim Erzeugen (S9a); danach immer zurück."""
    sketch_manager.AddToDB = True
    try:
        yield
    finally:
        sketch_manager.AddToDB = False


@contextmanager
def schnell(app, model):
    """Bauen ohne Bildschirmarbeit (Messstand Umbau 1): CommandInProgress, keine Grafikaktualisierung, Skizzenelemente
    nicht einzeln anzeigen, Feature-Baum nicht nachführen. Danach immer zurück, auch nach einem Fehler."""
    schalter = [(lambda: app, "CommandInProgress", True), (lambda: model.ActiveView, "EnableGraphicsUpdate", False),
                (lambda: model.SketchManager, "DisplayWhenAdded", False),
                (lambda: model.FeatureManager, "EnableFeatureTree", False),
                (lambda: model.FeatureManager, "EnableFeatureTreeWindow", False)]
    gesetzt = []
    for objekt, name, wert_ in schalter:
        try:
            o = objekt()
            if o is not None:
                setattr(o, name, wert_)
                gesetzt.append((o, name, not wert_))
        except Exception:   # Schalter fehlt (Attrappe, Dokument ohne Ansicht): ohne ihn weiterbauen
            continue
    try:
        yield
    finally:
        for o, name, wert_ in reversed(gesetzt):
            try:
                setattr(o, name, wert_)
            except Exception:
                pass


def ausblenden(model, feature) -> None:
    """Bezugsgeometrie ausblenden, damit sie nicht in den Screenshots erscheint."""
    auswahl_leeren(model)
    feature.Select2(False, 0)
    model._FlagAsMethod("BlankRefGeom")
    model.BlankRefGeom()
    auswahl_leeren(model)


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


_ACHSRICHTUNGEN = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
SW_SOLID_BODY = 0  # swBodyType_e


def box_aus_punkten(punkte) -> list[float]:
    """[xmin, ymin, zmin, xmax, ymax, zmax] einer Punktmenge."""
    return [min(p[i] for p in punkte) for i in range(3)] + [max(p[i] for p in punkte) for i in range(3)]


def extrempunkte_mm(koerper) -> list[tuple[float, float, float]]:
    """Extrempunkte (mm) eines Körpers in ±X/±Y/±Z (IBody2.GetExtremePoint)."""
    punkte = []
    for d in _ACHSRICHTUNGEN:
        ok, x, y, z = koerper.GetExtremePoint(*d)
        if ok:
            punkte.append((in_mm(x), in_mm(y), in_mm(z)))
    return punkte


def huellquader_eng_mm(model) -> list[float]:
    """Enger Hüllquader [xmin … zmax] (mm) über die Extrempunkte aller Volumenkörper. GetPartBox schätzt bei
    Freiformflächen (Ausformung des Trichters AP 6.8) bis ~2 mm zu groß; ohne Körper bleibt es bei GetPartBox."""
    punkte = [p for k in (model.GetBodies2(SW_SOLID_BODY, False) or ()) for p in extrempunkte_mm(k)]
    return box_aus_punkten(punkte) if punkte else teilebox_mm(model)


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
    Gespeichert wird nur im Arbeitsordner aus config/rechner.yaml.
    """
    arbeit = lade_rechner().arbeitsordner.resolve()
    if not pfad.resolve().is_relative_to(arbeit):
        raise BauFehler(SPEICHERN_FEHLGESCHLAGEN, f"{pfad} liegt nicht im Arbeitsordner {arbeit} (CLAUDE.md)",
                        schritt="speichern")
    pfad.parent.mkdir(parents=True, exist_ok=True)
    fehler, warnungen = byref_long(), byref_long()
    optionen = SW_SAVEAS_SILENT | (SW_SAVEAS_COPY if kopie else 0)
    ok = model.Extension.SaveAs3(str(pfad), SW_SAVEAS_CURRENT_VERSION, optionen, callout_leer(), callout_leer(),
                                 fehler, warnungen)
    if not ok or fehler.value:
        raise BauFehler(SPEICHERN_FEHLGESCHLAGEN, f"{pfad.name}: Fehler {fehler.value}", schritt="speichern")
