"""S18f: Musterteil *Lagerdeckel* und Musterbaugruppe *Muster* in „fremdem" Stil (Spec Bestandsdateien §11/§12).

Bewusst über die rohe API, ohne swki.compiler: Der Bestand soll aussehen wie die Datei eines Kollegen – Namen wie von
SolidWorks vergeben, globale Variable mit Gleichung, verknüpftes Maßpaar, zwei Konfigurationen, unterbestimmte Skizze, ein
Feature-Typ, den swki nicht kennt (Rippe). Dieses Skript ist die Quelle der Dateien in tests/referenz/bestand/muster/.

Gebaut wird im Arbeitsordner (<arbeitsordner>/S18/muster/), nur fertige Dateien werden kopiert. Modell (mm): Platte in der
Ebene vorne, X -50…50, Y -30…30, Z 0…20; Oberseite Z = 20.

Soll-Volumen: Platte 120000, Tasche 50×30×8 = -12000, zwei Bohrungen Ø8×20 = -2010,62, Rippe 3×30×5 = +450,
Fase 2×2/2×100 = -200 → Standard 106239,38 mm³, Variante B (ohne Fase) 106439,38 mm³.

API (swki api methode, Parameterzahl laut Index):
  ISldWorks.NewDocument(4), .OpenDoc6(6), .CloseDoc(1), .GetImportFileData(1), .LoadFile4(4), .GetMaterialDatabases(0)
  ISketchManager.InsertSketch(1), .CreateCornerRectangle(6), .CreateCircleByRadius(4), .CreateLine(6)
  IModelDoc2.AddDimension2(3), .AddHorizontalDimension2(3), .AddVerticalDimension2(3)
  IModelDocExtension.SelectByID2(9), .SelectByRay(11), .SaveAs3(7), .CustomPropertyManager(1, Property), .GetWhatsWrongCount(0)
  IFeatureManager.FeatureExtrusion3(23), .FeatureCut4(27), .InsertFeatureChamfer(8), .InsertRib(10)
  IDisplayDimension.SetLinkedText(1) → swLinkDimensionError_e (1 = NoError)
  IEquationMgr.Add2(3); IConfigurationManager.AddConfiguration2(7); IFeature.SetSuppression2(3)
  IPartDoc.SetMaterialPropertyName2(3), .GetMaterialPropertyName2(2)
  ICustomPropertyManager.Add3(4) (swCustomInfoText = 30, swCustomPropertyReplaceValue = 2)
  IAssemblyDoc.AddComponent5(8), .FixComponent(0), .AddMate5(15)

Aufruf (SolidWorks offen, frei): ..\\..\\..\\.venv\\Scripts\\python.exe -m spikes.s18_muster
"""

import json
import shutil
import time
from pathlib import Path

import pythoncom
import win32com.client

from swki.compiler.eigenschaften import finde_material  # nur die Namenssuche in der Materialdatenbank
from swki.kaufteile.sw_kaufteil import importiere
from swki.konfig import PROJEKT, lade_rechner
from swki.verbindung import byref_long, byref_str, callout_leer, mm, r8_array, verbinde

SW_INPUT_DIM_VAL_ON_CREATE = 10   # swUserPreferenceToggle_e
SW_SAVEAS_SILENT = 1              # swSaveAsOptions_e
SW_SPECIFY_CONFIGURATION = 3      # swInConfigurationOpts_e
SW_SUPPRESS = 0                   # swFeatureSuppressionAction_e
SW_CHAMFER_ANGLE_DISTANCE = 1     # swChamferType_e
SW_CHAMFER_TANGENT_PROPAGATION = 4  # swFeatureChamferOption_e
SW_SEL_FACES = 2                  # swSelectType_e
SW_CUSTOM_TEXT, SW_REPLACE = 30, 2
SW_MATE_COINCIDENT, SW_MATE_CLOSEST, SW_MATE_OK = 0, 2, 1  # swMateType_e, swMateAlign_e, swAddMateError_e
SW_DIMENSION_DRIVEN = 1           # swDimensionDrivenState_e
SW_OPEN_SILENT = 1
SW_DOC_PART, SW_DOC_ASSEMBLY = 1, 2


def ursprung(model):
    f = model.FirstFeature
    while f.GetTypeName2 != "OriginProfileFeature":
        f = f.GetNextFeature
    model.ClearSelection2(True)
    model.Extension.SelectByID2(f"Point1@{f.Name}", "EXTSKETCHPOINT", 0, 0, 0, False, 0, callout_leer(), 0)
    punkt = model.SelectionManager.GetSelectedObject6(1, -1)
    model.ClearSelection2(True)
    return punkt


def ebenen(model) -> list:
    aus, f = [], model.FirstFeature
    while f is not None and len(aus) < 3:
        if f.GetTypeName2 == "RefPlane":
            aus.append(f)
        f = f.GetNextFeature
    return aus


class Skizze:
    """Eine offene Skizze: rechnet Modellpunkte (mm) in Skizzenkoordinaten (m) um."""

    def __init__(self, app, model):
        self.model, self.sm = model, model.SketchManager
        self.mu = app.GetMathUtility
        self.mu._FlagAsMethod("CreatePoint")
        self.skizze = model.SketchManager.ActiveSketch
        self.sm.AddToDB = True

    def uv(self, x, y, z) -> tuple[float, float]:
        p = self.mu.CreatePoint(r8_array([mm(x), mm(y), mm(z)]))
        u, v, _ = p.MultiplyTransform(self.skizze.ModelToSketchTransform).ArrayData
        return u, v

    def waehle(self, *objekte) -> None:
        self.model.ClearSelection2(True)
        for i, o in enumerate(objekte):
            d = self.model.SelectionManager.CreateSelectData
            o.Select4(i > 0, d)

    def mass(self, art: str, xyz, *objekte):
        self.waehle(*objekte)
        methode = {"h": self.model.AddHorizontalDimension2, "v": self.model.AddVerticalDimension2,
                   "d": self.model.AddDimension2}[art]
        u, v = self.uv(*xyz)
        dd = methode(u, v, 0.0)
        if dd is None:
            raise RuntimeError(f"Maß {art} {xyz} nicht erzeugt")
        self.model.ClearSelection2(True)
        return dd

    def ende(self):
        self.sm.AddToDB = False
        self.sm.InsertSketch(True)
        return self.model.FeatureByPositionReverse(0)


def skizze_auf_flaeche(app, model, x, y, z) -> Skizze:
    """Skizze auf der ebenen Fläche, die ein Strahl von oben bei (x, y) trifft (Oberseite Z = 20)."""
    model.ClearSelection2(True)
    if not model.Extension.SelectByRay(mm(x), mm(y), mm(z + 1), 0, 0, -1, 0.0005, SW_SEL_FACES, False, 0, 0):
        raise RuntimeError(f"Fläche bei {x, y, z} nicht getroffen")
    model.SketchManager.InsertSketch(True)
    return Skizze(app, model)


def rechteck(s: Skizze, nullpunkt, x0, y0, x1, y1, z):
    """Ecken-Rechteck: D1 Breite (obere Linie), D2 Höhe (linke Linie), D3/D4 Lage der Ecke unten links zum Ursprung."""
    seg = s.sm.CreateCornerRectangle(*s.uv(x0, y0, z), 0.0, *s.uv(x1, y1, z), 0.0)
    unten, rechts, oben, links = seg[0], seg[1], seg[2], seg[3]
    s.mass("d", ((x0 + x1) / 2, y1 + 10, z), oben)
    s.mass("d", (x0 - 10, (y0 + y1) / 2, z), links)
    ecke = unten.GetStartPoint2
    s.mass("h", ((x0 + 0) / 2, y0 - 12, z), ecke, nullpunkt)
    s.mass("v", (x0 - 16, (y0 + 0) / 2, z), ecke, nullpunkt)
    return seg


def kreis(s: Skizze, nullpunkt, x, y, z, d):
    """Kreis: D1 Durchmesser, D2/D3 Lage des Mittelpunkts zum Ursprung. Liefert das Durchmessermaß."""
    seg = s.sm.CreateCircleByRadius(*s.uv(x, y, z), 0.0, mm(d / 2))
    dd = s.mass("d", (x + d, y + d, z), seg)
    mitte = seg.GetCenterPoint2
    s.mass("h", (x / 2, y + 8, z), mitte, nullpunkt)
    s.mass("v", (x + 8, y / 2, z), mitte, nullpunkt)
    return dd


def extrusion(model, skizze, tiefe_mm):
    model.ClearSelection2(True)
    skizze.Select2(False, 0)
    f = model.FeatureManager.FeatureExtrusion3(True, False, False, 0, 0, mm(tiefe_mm), 0.0, False, False, False, False,
                                               0.0, 0.0, False, False, False, False, True, True, True, 0, 0.0, False)
    if f is None:
        raise RuntimeError("FeatureExtrusion3 lieferte None")
    return f


def schnitt(model, skizze, t1: int, tiefe_mm: float = 0.0):
    model.ClearSelection2(True)
    skizze.Select2(False, 0)
    f = model.FeatureManager.FeatureCut4(True, False, False, t1, 0, mm(tiefe_mm), 0.0, False, False, False, False, 0.0,
                                         0.0, False, False, False, False, False, True, True, True, True, False, 0, 0.0,
                                         False, False)
    if f is None:
        raise RuntimeError("FeatureCut4 lieferte None")
    return f


def volumen(model) -> float:
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return round(mp.Volume * 1e9, 2)


def rippe(app, model):
    """Rippe in der Tasche auf Ebene rechts: Linie auf Z = 17, im Skizzenbild ohne Maße und Beziehungen (unterbestimmt),
    beidseitig 3 mm dick, Richtung parallel zur Skizze bis auf den Taschenboden."""
    model.ClearSelection2(True)
    ebenen(model)[2].Select2(False, 0)
    model.SketchManager.InsertSketch(True)
    s = Skizze(app, model)
    s.sm.CreateLine(*s.uv(0, -10, 17), 0.0, *s.uv(0, 10, 17), 0.0)
    skizze = s.ende()
    v0 = volumen(model)
    for umkehren in (False, True):
        model.ClearSelection2(True)
        skizze.Select2(False, 0)
        model.FeatureManager.InsertRib(True, False, 0.003, 0, umkehren, False, False, 0.0, False, False)
        f = model.FeatureByPositionReverse(0)
        if f.GetTypeName2 == "Rib" and abs(volumen(model) - v0 - 450) < 0.1:
            return f, umkehren
        if f.GetTypeName2 == "Rib":
            f.Select2(False, 0)
            model.EditDelete
    raise RuntimeError("Rippe nicht erzeugt")


def kante_waehlen(model, y: float, z: float) -> None:
    """Die eine Kante, deren beide Enden auf Y = y, Z = z liegen (SelectByID2 mit Koordinaten traf eine andere Kante)."""
    model.ClearSelection2(True)
    for k in model.GetBodies2(0, False)[0].GetEdges():
        a, b = k.GetStartVertex, k.GetEndVertex
        if a is None or b is None:
            continue
        pa, pb = a.GetPoint, b.GetPoint
        if all(abs(q[1] - mm(y)) < 1e-6 and abs(q[2] - mm(z)) < 1e-6 for q in (pa, pb)):
            if not k.Select4(False, model.SelectionManager.CreateSelectData):
                raise RuntimeError("Kante nicht auswählbar")
            return
    raise RuntimeError(f"Kante Y={y}, Z={z} nicht gefunden")


def speichere(model, pfad: Path) -> dict:
    e, w = byref_long(), byref_long()
    ok = model.Extension.SaveAs3(str(pfad), 0, SW_SAVEAS_SILENT, callout_leer(), callout_leer(), e, w)
    if not ok or e.value:
        raise RuntimeError(f"Speichern {pfad.name}: Fehler {e.value}")
    return {"datei": pfad.name, "warnungen": w.value}


def baue_teil(app, r, ordner: Path) -> dict:
    d: dict = {}
    model = app.NewDocument(str(r.vorlage_teil), 0, 0, 0)
    nullpunkt = ursprung(model)
    # Grundplatte
    model.ClearSelection2(True)
    ebenen(model)[0].Select2(False, 0)
    model.SketchManager.InsertSketch(True)
    s = Skizze(app, model)
    rechteck(s, nullpunkt, -50, -30, 50, 30, 0)
    extrusion(model, s.ende(), 20)
    d["nach_platte"] = volumen(model)
    # Tasche von der Oberseite
    s = skizze_auf_flaeche(app, model, 40, 25, 20)
    seg = rechteck(s, nullpunkt, -25, -15, 25, 15, 20)
    # Referenzmaß (getrieben): die untere Linie ist durch die obere schon bestimmt
    referenz = s.mass("d", (0, -22, 20), seg[0]).GetDimension2(0)
    referenz.DrivenState = SW_DIMENSION_DRIVEN
    d["referenzmass"] = {"name": referenz.FullName, "zustand": referenz.DrivenState}
    schnitt(model, s.ende(), 0, 8)
    d["nach_tasche"] = volumen(model)
    # Zwei Bohrungen als einzelne Schnitte, Durchmesser verknüpft
    s = skizze_auf_flaeche(app, model, 40, 25, 20)
    dd1 = kreis(s, nullpunkt, -40, 15, 20, 8)
    schnitt(model, s.ende(), 1)
    s = skizze_auf_flaeche(app, model, 40, 25, 20)
    dd2 = kreis(s, nullpunkt, 40, -15, 20, 8)
    schnitt(model, s.ende(), 1)
    d["verknuepfung"] = [dd1.SetLinkedText("Bohrung_D"), dd2.SetLinkedText("Bohrung_D")]
    d["nach_bohrungen"] = volumen(model)
    # Rippe (Feature-Typ, den swki nicht kennt) mit unterbestimmter Skizze
    feature_rippe, umkehren = rippe(app, model)
    d["rippe"] = {"name": feature_rippe.Name, "typ": feature_rippe.GetTypeName2, "material_umgekehrt": umkehren}
    d["nach_rippe"] = volumen(model)
    # Fase an der Oberkante Y = +30
    kante_waehlen(model, y=30, z=20)
    fase = model.FeatureManager.InsertFeatureChamfer(SW_CHAMFER_TANGENT_PROPAGATION, SW_CHAMFER_ANGLE_DISTANCE, mm(2),
                                                     0.7853981633974483, 0, 0, 0, 0)
    if fase is None or not fase.GetFaces:
        raise RuntimeError("Fase nicht erzeugt")
    d["nach_fase"] = volumen(model)
    # Globale Variable mit Gleichung
    gl = model.GetEquationMgr
    d["gleichungen"] = [gl.Add2(-1, '"L" = 100', True), gl.Add2(-1, '"D1@Skizze1" = "L"', True)]
    model.EditRebuild3
    # Material und Eigenschaften
    db, name = finde_material(list(app.GetMaterialDatabases or ()), "1.0038")
    model.SetMaterialPropertyName2("", db, name)
    d["material"] = model.GetMaterialPropertyName2("", byref_str())
    eigenschaften = model.Extension.CustomPropertyManager("")
    for feld, wert in (("Benennung", "Lagerdeckel"), ("Revision", "A")):
        eigenschaften.Add3(feld, SW_CUSTOM_TEXT, wert, SW_REPLACE)
    # Zweite Konfiguration: Fase unterdrückt, eigene Eigenschaft
    standard = model.ConfigurationManager.ActiveConfiguration.Name
    variante = model.ConfigurationManager.AddConfiguration2("Variante B", "", "", 0, "", "", True)
    d["konfiguration_neu"] = variante is not None
    model.ShowConfiguration2("Variante B")  # AddConfiguration2 aktiviert die neue Konfiguration nicht verlässlich
    d["aktiv_beim_unterdruecken"] = model.ConfigurationManager.ActiveConfiguration.Name
    # swThisConfiguration traf hier die Konfiguration, in der das IFeature geholt wurde, nicht die aktive (S18c)
    namen = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, ["Variante B"])
    d["fase_unterdrueckt"] = fase.SetSuppression2(SW_SUPPRESS, SW_SPECIFY_CONFIGURATION, namen)
    model.Extension.CustomPropertyManager("Variante B").Add3("Bemerkung", SW_CUSTOM_TEXT, "ohne Fase", SW_REPLACE)
    model.EditRebuild3
    d["variante_b"] = volumen(model)
    d["konfiguration_aktiv"] = model.ShowConfiguration2(standard)
    model.EditRebuild3
    d["standard"] = volumen(model)
    d["konfigurationen"] = list(model.GetConfigurationNames)
    d["baum"] = feature_liste(model)
    d["speichern"] = speichere(model, ordner / "Lagerdeckel.SLDPRT")
    app.CloseDoc(model.GetTitle)
    return d


def feature_liste(model) -> list:
    aus, f = [], model.FirstFeature
    while f is not None:
        aus.append(f"{f.Name} [{f.GetTypeName2}]")
        f = f.GetNextFeature
    return aus


def baue_motor(app, ordner: Path) -> dict:
    step = PROJEKT / "tests" / "referenz" / "motorhalter" / "muster" / "gm42-10.step"  # nur lesen
    model = importiere(app, step)
    d = {"typ_import": feature_liste(model)[-3:], "volumen": volumen(model)}
    d["speichern"] = speichere(model, ordner / "gm42-10.SLDPRT")
    app.CloseDoc(model.GetTitle)
    return d


def baue_baugruppe(app, r, ordner: Path) -> dict:
    d: dict = {}
    pfad_deckel, pfad_motor = ordner / "Lagerdeckel.SLDPRT", ordner / "gm42-10.SLDPRT"
    e, w = byref_long(), byref_long()
    teile = [app.OpenDoc6(str(p), SW_DOC_PART, SW_OPEN_SILENT, "", e, w) for p in (pfad_deckel, pfad_motor)]
    asm = app.NewDocument(str(r.vorlage_baugruppe), 0, 0, 0)
    deckel = asm.AddComponent5(str(pfad_deckel), 0, "", False, "", 0.0, 0.0, mm(10))
    motor = asm.AddComponent5(str(pfad_motor), 0, "", False, "", mm(200), 0.0, 0.0)
    if deckel is None or motor is None:
        raise RuntimeError("AddComponent5 fehlgeschlagen")
    asm.ClearSelection2(True)
    deckel.Select4(False, asm.SelectionManager.CreateSelectData, False)
    asm._FlagAsMethod("FixComponent")
    asm.FixComponent()
    asm.ClearSelection2(True)
    d["speichern"] = speichere(asm, ordner / "Muster.SLDASM")
    # Verknüpfung auf eine Fläche des Lagerdeckels (Unterseite Z = 0), damit der Bezug an der Geometrie hängt
    asm.ClearSelection2(True)
    unten = asm.Extension.SelectByRay(mm(-20), 0.0, mm(-5), 0, 0, 1, 0.0005, SW_SEL_FACES, False, 1, 0)
    ebene = motor.FeatureByName(ebenen_name_motor(teile[1]))
    d["auswahl"] = [bool(unten), bool(ebene is not None and ebene.Select2(True, 1))]
    status = byref_long()
    mate = asm.AddMate5(SW_MATE_COINCIDENT, SW_MATE_CLOSEST, False, 0.0, 0.0, 0.0, 1, 1, 0.0, 0.0, 0.0, False, False, 0,
                        status)
    d["verknuepfung"] = {"status": status.value, "angelegt": mate is not None}
    asm.ClearSelection2(True)
    asm.EditRebuild3
    d["komponenten"] = [(k.Name2, k.GetPathName) for k in (asm.GetComponents(True) or ())]
    e2, w2 = byref_long(), byref_long()
    d["speichern2"] = asm.Save3(SW_SAVEAS_SILENT, e2, w2), e2.value, w2.value
    app.CloseDoc(asm.GetTitle)
    for t in teile:
        try:
            app.CloseDoc(t.GetTitle)
        except AttributeError:
            pass
    return d


def ebenen_name_motor(model) -> str:
    return ebenen(model)[0].Name


def nachpruefen(app, ordner: Path) -> dict:
    """Erwartet: öffnen ohne Neuaufbau-Fehler, beide Konfigurationen mit Soll-Volumen."""
    d: dict = {}
    e, w = byref_long(), byref_long()
    model = app.OpenDoc6(str(ordner / "Lagerdeckel.SLDPRT"), SW_DOC_PART, SW_OPEN_SILENT, "", e, w)
    d["oeffnen_teil"] = {"fehler": e.value, "warnungen": w.value}
    for k in model.GetConfigurationNames:
        model.ShowConfiguration2(k)
        ok = model.EditRebuild3
        d[k] = {"neuaufbau": ok, "whats_wrong": model.Extension.GetWhatsWrongCount, "volumen": volumen(model)}
    model.ShowConfiguration2("Standard")
    app.CloseDoc(model.GetTitle)
    e, w = byref_long(), byref_long()
    asm = app.OpenDoc6(str(ordner / "Muster.SLDASM"), SW_DOC_ASSEMBLY, SW_OPEN_SILENT, "", e, w)
    d["oeffnen_baugruppe"] = {"fehler": e.value, "warnungen": w.value}
    d["baugruppe"] = {"neuaufbau": asm.EditRebuild3, "whats_wrong": asm.Extension.GetWhatsWrongCount,
                      "komponenten": [(k.Name2, k.GetPathName) for k in (asm.GetComponents(True) or ())]}
    app.CloseDoc(asm.GetTitle)
    return d


def main() -> None:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    ordner = r.arbeitsordner / "S18" / "muster"
    ziel = PROJEKT / "tests" / "referenz" / "bestand" / "muster"
    if ordner.exists():
        shutil.rmtree(ordner)
    ordner.mkdir(parents=True)
    d: dict = {}
    alt = app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE)
    app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, False)
    t0 = time.monotonic()
    try:
        d["teil"] = baue_teil(app, r, ordner)
        d["motor"] = baue_motor(app, ordner)
        d["baugruppe"] = baue_baugruppe(app, r, ordner)
        d["nachpruefen"] = nachpruefen(app, ordner)
    finally:
        app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, alt)
    d["sekunden"] = round(time.monotonic() - t0, 1)
    ziel.mkdir(parents=True, exist_ok=True)
    for name in ("Lagerdeckel.SLDPRT", "gm42-10.SLDPRT", "Muster.SLDASM"):
        shutil.copy2(ordner / name, ziel / name)
    print(json.dumps(d, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
