"""SolidWorks-Schicht der Kaufteile (Spec 3c §6, Spike S15): STEP importieren (Optionen nur für den Import, danach
wiederhergestellt), Diagnose ohne Reparatur, Bezugsgeometrie an Importflächen, Massenüberschreibung, Messwerte.

Late Binding (swki/wissen/pywin32-fallstricke.md): nullargumentige Member ohne "()"; IBody2 hat Typinfo – seine
Methoden mit "()", Properties (Check3) ohne (S9b)."""

from contextlib import contextmanager
from pathlib import Path

import pythoncom

from swki.compiler import sw
from swki.compiler.anker import AnkerFehler, Flaeche
from swki.compiler.eigenschaften import lies_eigenschaften, setze_eigenschaften, setze_material
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.topologie import flaeche_aus, koerper, mit_abstand, referenz_geometrie
from swki.kaufteile.bewertung import KaufteilMesswerte
from swki.kaufteile.eintrag import eigenschaften
from swki.kaufteile.fehler import KAUFTEIL_IMPORT
from swki.kaufteile.ortung import (Ortung, ebene_durch_achse, kandidaten, orte_ebene, orte_gewinde, orte_zylinder)
from swki.pruefung.bewertung import messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from swki.pruefung.messen import rebuild_fehler
from swki.verbindung import byref_long, byref_str, callout_leer, in_mm, in_mm3, mm

SW_3D_INTERCONNECT = 691      # swUserPreferenceToggle_e.swMultiCAD_Enable3DInterconnect
SW_IMPORT_DIAGNOSE = 690      # swUserPreferenceToggle_e.swImportNeutralRunDiagnostics
SW_IMPORT_STRUKTUR = 579      # swUserPreferenceIntegerValue_e.swImportNeutralAssemblyStructureMapping
STRUKTUR_MEHRKOERPER = 2      # swImportNeutralAssemblyStructureMapping_e.…_MultibodyPart
SW_SHEET_BODY = 1             # swBodyType_e.swSheetBody
REF_PLANE_DECKUNGSGLEICH = 4  # swRefPlaneReferenceConstraints_e.swRefPlaneReferenceConstraint_Coincident
SW_ANZEIGE_ACHSEN, SW_ANZEIGE_EBENEN = 4, 5  # swUserPreferenceToggle_e.swDisplayAxes / swDisplayPlanes
SW_IN_DIESER_KONFIGURATION = 1  # swInConfigurationOpts_e.swThisConfiguration
SW_OHNE_OPTION = 0            # swUserPreferenceOption_e.swDetailingNoOptionSpecified


def optionen(app) -> dict:
    """Die Import-Optionen, die importiere() vorübergehend setzt, im vorgefundenen Stand (fürs Protokoll)."""
    return {"3d_interconnect": bool(app.GetUserPreferenceToggle(SW_3D_INTERCONNECT)),
            "importdiagnose": bool(app.GetUserPreferenceToggle(SW_IMPORT_DIAGNOSE)),
            "strukturabbildung": int(app.GetUserPreferenceIntegerValue(SW_IMPORT_STRUKTUR))}


@contextmanager
def importoptionen(app):
    """3D Interconnect aus (sonst behält das Teil einen Verweis auf das Original), keine automatische Importdiagnose
    (sie repariert bzw. fragt), Baugruppen-STEP als Mehrkörperteil; danach immer der vorgefundene Stand."""
    with sw.einstellung(app, SW_3D_INTERCONNECT, False), sw.einstellung(app, SW_IMPORT_DIAGNOSE, False), \
            sw.einstellung_int(app, SW_IMPORT_STRUKTUR, STRUKTUR_MEHRKOERPER):
        yield


def importiere(app, pfad: Path):
    """STEP-Datei als neues Teil (ungespeichert); KAUFTEIL_IMPORT, wenn SolidWorks kein Dokument liefert."""
    with importoptionen(app):
        daten = app.GetImportFileData(str(pfad))
        fehler = byref_long()
        model = app.LoadFile4(str(pfad), "r", daten, fehler)
    if model is None:
        raise BauFehler(KAUFTEIL_IMPORT, f"{pfad.name}: Import gescheitert (swFileLoadError {fehler.value})",
                        schritt="import")
    return model


def interconnect_features(model) -> list[str]:
    """Namen der Features, die noch über 3D Interconnect an der Originaldatei hängen (Soll: keine)."""
    namen, f = [], model.FirstFeature
    while f is not None:
        if f.Is3DInterconnectFeature:
            namen.append(f.Name)
        f = f.GetNextFeature
    return namen


def alle_flaechen(model) -> list[Flaeche]:
    return [flaeche_aus(f) for b in koerper(model) for f in (b.GetFaces() or ())]


def koerperfehler(model) -> dict[str, int]:
    """Fehlerzahl je Volumenkörper laut IBody2.Check3 (ohne Reparatur)."""
    ergebnis = {}
    for i, b in enumerate(koerper(model), start=1):
        fehler = b.Check3
        ergebnis[str(i)] = 0 if fehler is None else int(fehler.Count)
    return ergebnis


def flaechenkoerper(model) -> int:
    return len(model.GetBodies2(SW_SHEET_BODY, False) or ())


def _datensatz(f: Flaeche) -> dict:
    """Datensatz für diagnose.uebersicht: Punkt auf der begrenzten Fläche (nächster zur Mitte der Box) und Fläche."""
    box = f.objekt.GetBox
    q = f.objekt.GetClosestPointOn((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2)
    satz = {"art": f.art, "punkt": f.punkt, "auf": tuple(in_mm(c) for c in q[:3]),
            "flaeche_mm2": f.objekt.GetArea * 1e6}
    return satz | ({"normale": f.normale} if f.art == "ebene" else {"achse": f.achse, "radius": f.radius})


def diagnose(model, flaechen: list[Flaeche]) -> dict:
    """Kennzahlen des importierten Teils (Spec 3c §5.1) ohne die Flächenübersicht."""
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return {"koerper": len(koerper(model)), "flaechenkoerper": flaechenkoerper(model), "koerperfehler": koerperfehler(model),
            "flaechen": len(flaechen), "huellquader": sw.teilebox_mm(model), "volumen": round(in_mm3(mp.Volume), 3),
            "schwerpunkt": [round(in_mm(c), 4) for c in mp.CenterOfMass], "interconnect": interconnect_features(model)}


def datensaetze(flaechen: list[Flaeche]) -> list[dict]:
    return [_datensatz(f) for f in flaechen if f.art in ("ebene", "zylinder")]


def _bezugsachse(model, flaeche: Flaeche, name: str):
    sw.auswahl_leeren(model)
    sw.waehle(model, flaeche.objekt, 0)
    if not model.InsertAxis2(True):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Bezugsachse nicht erzeugt", schritt="einbau")
    feature = sw.letztes_feature(model)
    feature.Name = name
    return feature


def _bezugsebene(model, flaeche: Flaeche, name: str):
    sw.auswahl_leeren(model)
    sw.waehle(model, flaeche.objekt, 0)
    feature = model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0, 0, 0.0)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Bezugsebene nicht erzeugt", schritt="einbau")
    feature.Name = name
    return feature


def _ebene_durch_achse(model, achse, nahe, name: str):
    """Bezugsebene durch eine Bezugsachse und einen Punkt; der Punkt ist ein 3D-Skizzenpunkt <name>_punkt (Spike S15c)."""
    sm = model.SketchManager
    sw.auswahl_leeren(model)
    sm.Insert3DSketch(True)
    with sw.ohne_inferenz(sm):
        punkt = sm.CreatePoint(*(mm(c) for c in nahe))
    sm.Insert3DSketch(True)
    if punkt is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Skizzenpunkt nicht erzeugt", schritt="einbau")
    skizze = sw.letztes_feature(model)
    skizze.Name = f"{name}_punkt"
    sw.auswahl_leeren(model)
    achse.Select2(False, 0)
    if not model.Extension.SelectByID2(f"Point1@{skizze.Name}", "EXTSKETCHPOINT", 0, 0, 0, True, 1, callout_leer(), 0):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Skizzenpunkt nicht auswählbar", schritt="einbau")
    feature = model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0)
    sw.auswahl_leeren(model)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Bezugsebene durch Achse und Punkt nicht erzeugt",
                        schritt="einbau")
    feature.Name = name
    return feature


def _geortet(flaechen: list[Flaeche], art: str, punkt, tol_mm: float) -> list[Flaeche]:
    """Vorauswahl (rein geometrisch) und echter Abstand zur begrenzten Fläche (COM) nur für die Kandidaten."""
    return mit_abstand(kandidaten(flaechen, art, tuple(punkt), tol_mm), tuple(punkt))


def _messung(o: Ortung, feature) -> dict:
    bezug = Messgeometrie(*referenz_geometrie(feature)) if feature is not None else None
    return {"ist": o.ist, "abweichung": o.abweichung, "bezug": bezug}


def lege_einbau_an(model, spec: dict, flaechen: list[Flaeche], tol_mm: float) -> dict:
    """Einbaureferenzen orten, gegenprüfen und als benannte Bezugsgeometrie anlegen (zuerst zylinder und ebene, dann
    ebene_durch_achse). Ortungsfehler werden Messwerte (Text), keine Abbrüche: die Prüfung meldet sie als Mangel."""
    ergebnis: dict[str, dict | str] = {}
    reihenfolge = sorted(spec["einbau"].items(), key=lambda kv: "ebene_durch_achse" in kv[1])
    for name, w in reihenfolge:
        art, soll = next(iter(w.items()))
        try:
            if art == "zylinder":
                o = orte_zylinder(_geortet(flaechen, "zylinder", soll["nahe"], tol_mm), name, soll, tol_mm)
                ergebnis[name] = _messung(o, _bezugsachse(model, o.flaeche, name))
            elif art == "ebene":
                o = orte_ebene(_geortet(flaechen, "ebene", soll["nahe"], tol_mm), name, soll, tol_mm)
                ergebnis[name] = _messung(o, _bezugsebene(model, o.flaeche, name))
            else:
                achse = ergebnis.get(soll["achse"])
                if not isinstance(achse, dict) or achse["bezug"] is None:
                    ergebnis[name] = f"{soll['achse']} fehlt"
                    continue
                o = ebene_durch_achse(name, achse["bezug"].punkt, achse["bezug"].richtung, soll["nahe"])
                feature = None if o.abweichung else _ebene_durch_achse(model, model.FeatureByName(soll["achse"]),
                                                                       soll["nahe"], name)
                ergebnis[name] = _messung(o, feature)
        except AnkerFehler as e:
            ergebnis[name] = f"{e.code}: {e}"
    return ergebnis


def orte_gewinde_alle(spec: dict, flaechen: list[Flaeche], tol_mm: float) -> dict:
    ergebnis: dict[str, dict | str] = {}
    for gruppe, w in spec.get("gewinde", {}).items():
        try:
            for o in orte_gewinde(flaechen, gruppe, w, tol_mm):
                ergebnis[o.name] = {"ist": o.ist, "abweichung": o.abweichung}
        except AnkerFehler as e:
            for i in range(1, len(w["positionen"]) + 1):
                ergebnis.setdefault(f"{gruppe}.{i}", f"{e.code}: {e}")
    return ergebnis


def setze_masse(model, kg: float) -> None:
    """Massenüberschreibung (IMassPropertyOverrideOptions, seit SW 2020; Spike S15d). Abweichung vom Plan-Code: Die
    Überschreibung wirkt nur, wenn alle Volumenkörper ausgewählt sind und die Optionen mit
    IMassProperty2.SetOverrideOptions(Optionen, swThisConfiguration, leer) zurückgeschrieben werden; GetOverrideOptions
    und SetOverrideMassValue allein lassen die Masse aus dem Material stehen."""
    sw.auswahl_leeren(model)
    try:
        for i, b in enumerate(koerper(model)):
            b.Select2(i > 0, None)
        mp = model.Extension.CreateMassProperty2
        optionen_masse = mp.GetOverrideOptions
        optionen_masse.OverrideMass = True
        optionen_masse.SetOverrideMassValue(kg)
        if not mp.SetOverrideOptions(optionen_masse, SW_IN_DIESER_KONFIGURATION, pythoncom.Empty):
            raise BauFehler(FEATURE_NICHT_ERZEUGT, "Massenüberschreibung nicht gesetzt", schritt="einbau")
    finally:
        sw.auswahl_leeren(model)


def richte_ein(app, model, spec: dict, tol_mm: float) -> tuple[list[Flaeche], dict, dict]:
    """Material, Eigenschaften, Einbaureferenzen, Gewindepositionen, Masse; danach Rebuild. Liefert (Flächen, einbau,
    gewinde)."""
    setze_material(app, model, spec["material"])
    setze_eigenschaften(model, eigenschaften(spec))
    flaechen = alle_flaechen(model)
    einbau = lege_einbau_an(model, spec, flaechen, tol_mm)
    gewinde = orte_gewinde_alle(spec, flaechen, tol_mm)
    if "masse" in spec:
        setze_masse(model, spec["masse"]["kg"])
    sw.rebuild(model)
    return flaechen, einbau, gewinde


def _messpunkt(mp: dict, einbau: dict, gewinde: dict, flaechen: list[Flaeche], tol_mm: float) -> Messgeometrie | str:
    if "punkt" in mp:
        return Messgeometrie("punkt", tuple(mp["punkt"]))
    if "referenz" in mp:
        m = einbau.get(mp["referenz"], f"{mp['referenz']} fehlt")
        return m if isinstance(m, str) else (m["bezug"] or f"{mp['referenz']}: keine Bezugsgeometrie")
    if "gewinde" in mp:
        m = gewinde.get(f"{mp['gewinde']}.{mp['instanz']}", "Gewindeposition fehlt")
        return m if isinstance(m, str) else Messgeometrie("achse", m["ist"]["punkt"], m["ist"]["achse"])
    w = mp["flaeche"]
    try:
        o = orte_ebene(_geortet(flaechen, "ebene", w["nahe"], tol_mm), "flaeche", w, tol_mm)
    except AnkerFehler as e:
        return f"{e.code}: {e}"
    return o.abweichung or Messgeometrie("ebene", o.flaeche.punkt, o.flaeche.normale)


def _durchmesser(spec: dict, einbau: dict, flaechen: list[Flaeche], tol_mm: float) -> dict:
    ergebnis: dict[str, dict | str] = {}
    for dp in spec.get("pruefung", {}).get("durchmesser_pruefen", []):
        try:
            o = orte_zylinder(_geortet(flaechen, "zylinder", dp["nahe"], tol_mm), dp["was"],
                              {"nahe": dp["nahe"], "durchmesser": dp["soll"]}, tol_mm)
        except AnkerFehler as e:
            ergebnis[dp["was"]] = f"{e.code}: {e}"
            continue
        wert = {"durchmesser": o.ist["durchmesser"], "achse": Messgeometrie("achse", o.ist["punkt"], o.ist["achse"])}
        if "referenz" in dp and isinstance(einbau.get(dp["referenz"]), dict) and einbau[dp["referenz"]]["bezug"]:
            wert["referenz"] = einbau[dp["referenz"]]["bezug"]
        ergebnis[dp["was"]] = wert
    return ergebnis


def messe(model, spec: dict, flaechen: list[Flaeche], einbau: dict, gewinde: dict, tol_mm: float) -> KaufteilMesswerte:
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    pr = spec.get("pruefung", {})
    punkte = {messpunkt_schluessel(p): _messpunkt(p, einbau, gewinde, flaechen, tol_mm)
              for m in pr.get("masse_pruefen", []) for p in (m["von"], m["zu"])}
    return KaufteilMesswerte(
        rebuild_fehler=rebuild_fehler(model), koerper=len(koerper(model)), flaechenkoerper=flaechenkoerper(model),
        koerperfehler=koerperfehler(model), box=sw.teilebox_mm(model), volumen=in_mm3(mp.Volume), masse_kg=mp.Mass,
        masse_ueberschrieben=bool(mp.GetOverrideOptions.OverrideMass),
        material=model.GetMaterialPropertyName2("", byref_str()) or "", eigenschaften=lies_eigenschaften(model),
        einbau=einbau, gewinde=gewinde, messpunkte=punkte, durchmesser=_durchmesser(spec, einbau, flaechen, tol_mm))


def zeige_bezuege(model) -> None:
    """Bezugsachsen und -ebenen im eigenen Dokument einblenden (Bilder für Nutzer und Prüfer, Spike S15h)."""
    for toggle in (SW_ANZEIGE_ACHSEN, SW_ANZEIGE_EBENEN):
        model.Extension.SetUserPreferenceToggle(toggle, SW_OHNE_OPTION, True)
