"""Musterteil *Lagerdeckel* und Musterbaugruppe *Muster* in „fremdem" Stil (Spec Bestandsdateien §11/§12, Spike S18f).

Bewusst über die rohe API, ohne swki.compiler: Der Bestand soll aussehen wie die Datei eines Kollegen – Namen wie von
SolidWorks vergeben, globale Variable mit Gleichung, verknüpftes Maßpaar, zwei Konfigurationen, unterbestimmte Skizze, ein
Feature-Typ, den swki nicht kennt (Rippe). Von hier stammen die Dateien in tests/referenz/bestand/muster/.

SolidWorks öffnet keine neueren Dateien und stuft ältere hoch, die Dateien im Git taugen also nur für ihr Jahr (`sw_jahr` in
bestand.json). Jedes andere Jahr erzeugt sich die Muster einmal selbst nach <arbeitsordner>/BESTAND-MUSTER/<jahr>/, nicht ins Git.
Neu eingecheckt wird von Hand, samt bestand.json und `sha256` in lagerdeckel_rev.yaml.

Gebaut wird in <arbeitsordner>/BESTAND-MUSTER/<jahr>/bau/, nur fehlerfrei nachgeprüfte Dateien werden kopiert. Modell (mm):
Platte in der Ebene vorne, X -50…50, Y -30…30, Z 0…20; Oberseite Z = 20.

Soll-Volumen: Platte 120000, Tasche 50×30×8 = -12000, zwei Bohrungen Ø8×20 = -2010,62, Rippe 3×30×5 = +450,
Fase 2×2/2×100 = -200 → Standard 106239,38 mm³, Variante B (ohne Fase) 106439,38 mm³.

Musterbaugruppe *Hubeinheit* (Etappe 2, Plan Task 12): `Hubeinheit.SLDASM` mit `teile/Grundplatte.SLDPRT` (fixiert),
`teile/Schlitten.SLDPRT` (eine Bewegung), zweimal `teile/Anschlag.SLDPRT` und der vorhandenen Unterbaugruppe `Muster.SLDASM` (mit dem
importierten Motor). Die Unterbaugruppe wird nur kopiert: Neu gebaut trüge sie andere SHA-256 als `lagerdeckel_rev.yaml`. Gebaut wird
in <arbeitsordner>/BESTAND-MUSTER/<jahr>/bau_hub/, geprüft dort, abgelegt in .../baugruppe/, mit `--ins-git` zusätzlich in
tests/referenz/bestand/muster/baugruppe/; `hubeinheit_ordner` findet sie. Anders als beim Lagerdeckel tragen die Verknüpfungen
Namen: Die Referenz `hubeinheit_rev.yaml` nennt sie, und die Nummern, die SolidWorks vergibt, hängen an Sprache und Reihenfolge.

Modell in der Baugruppe (mm): Grundplatte X -100…100, Y -40…40, Z 0…15. Schlitten X -30…30, Y -25…25, Z 0…20 im Teil, Ursprung in der
Baugruppe bei (-70, 0, 15), `Hub` lässt ihn 0…25 in +X fahren, Kernloch Ø5×12 bei (10, 10) von oben, Länge über die globale Variable
`L`. Anschlag X, Y ±10, Z 0…30 im Teil, Ursprung bei (30, 0, 15) und (70, 0, 15), die Verknüpfungen hängen an seinen Standardebenen,
damit ein Ersatz sie behält. Muster-1 Ursprung bei (0, 150, 0), Ebenen an den Ebenen der Baugruppe (Partner ohne Komponente), Abstand
von der Fläche des Lagerdeckels (Partner in der Unterbaugruppe). Konfiguration „Ohne Antrieb“: Muster-1 unterdrückt.

Soll-Volumen: Grundplatte 200×80×15 = 240000, Schlitten 60×50×20 - π·2,5²·12 = 59764,38, Anschlag 20×20×30 = 12000 mm³.

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
  IAssemblyDoc.AddComponent5(8), .FixComponent(0), .AddMate5(15), .GetComponents(1)
  IComponent2.SetSuppression2(1 → swSuppressionError_e), .GetSuppression2(0), .FeatureByName(1), .GetModelDoc2(0), .Name2, .Transform2,
    .SetTransformAndSolve2(1), .Select4(3), .GetConstrainedStatus(0), .GetPathName(0)
  IMathUtility.CreateTransform(1); IFeature.GetSpecificFeature2(0), .GetErrorCode2(1), .Parameter(1), .GetFirstSubFeature(0),
    .GetNextSubFeature(0); IMate2.MinimumVariation, .MaximumVariation

Aufruf (SolidWorks offen, frei): .venv\\Scripts\\python.exe -m werkzeuge.bestand_muster
                                 .venv\\Scripts\\python.exe -m werkzeuge.bestand_muster hubeinheit [--ins-git]
"""

import argparse
import json
import shutil
import time
from pathlib import Path

import pythoncom
import win32com.client

from swki.compiler.eigenschaften import finde_material  # nur die Namenssuche in der Materialdatenbank
from swki.kaufteile.sw_kaufteil import importiere
from swki.konfig import PROJEKT, Rechner, lade_rechner
from swki.verbindung import byref_bool, byref_long, byref_str, callout_leer, in_mm, mm, r8_array, verbinde

MUSTER_GIT = PROJEKT / "tests" / "referenz" / "bestand" / "muster"
DATEIEN = ("Lagerdeckel.SLDPRT", "gm42-10.SLDPRT", "Muster.SLDASM")
SOLL_VOLUMEN = {"Standard": 106239.38, "Variante B": 106439.38}  # mm³, Rechnung im Modulkopf

HUBEINHEIT = "Hubeinheit.SLDASM"
TEILE_HUB = ("teile/Grundplatte.SLDPRT", "teile/Schlitten.SLDPRT", "teile/Anschlag.SLDPRT")
HUB_DATEIEN = (HUBEINHEIT, *DATEIEN, *TEILE_HUB)
KONFIG_OHNE = "Ohne Antrieb"
SOLL_VOLUMEN_HUB = {"Grundplatte": 240000.0, "Schlitten": 59764.38, "Anschlag": 12000.0}  # mm³, Rechnung im Modulkopf
HUB_LAGE = {"Grundplatte-1": (0, 0, 0), "Schlitten-1": (-70, 0, 15), "Anschlag-1": (30, 0, 15), "Anschlag-2": (70, 0, 15),
            "Muster-1": (0, 150, 0)}  # Ursprung der Komponente in der Baugruppe (mm)
HUB_KOMPONENTEN = (*HUB_LAGE, "Muster-1/Lagerdeckel-1", "Muster-1/gm42-10-1")
# swConstrainedStatus_e. Die aktive Grenze `Hub` zählt als Bindung (S13b, Ruling Z. 4 in docs/stufe4a/ergebnisse.md, an der Hubeinheit
# gemessen): Schlitten-1 ist 3, mit unterdrückter Grenze 2.
HUB_STATUS = {"Grundplatte-1": 3, "Schlitten-1": 3, "Anschlag-1": 3, "Anschlag-2": 3, "Muster-1": 3}
HUB_VERKNUEPFUNGEN = ("Schlitten Auflage", "Schlitten Seite", "Hub", "Anschlag1 Auflage", "Anschlag1 Mitte", "Anschlag1 Lage",
                      "Anschlag2 Auflage", "Anschlag2 Mitte", "Anschlag2 Lage", "Antrieb vorne", "Antrieb rechts", "Antrieb Abstand")
HUB_GRENZE = {"Hub": (0.0, 25.0)}  # mm
TOL_LAGE_MM = 0.01

SW_INPUT_DIM_VAL_ON_CREATE = 10   # swUserPreferenceToggle_e
SW_SAVEAS_SILENT = 1              # swSaveAsOptions_e
SW_SPECIFY_CONFIGURATION = 3      # swInConfigurationOpts_e
SW_SUPPRESS = 0                   # swFeatureSuppressionAction_e
SW_CHAMFER_ANGLE_DISTANCE = 1     # swChamferType_e
SW_CHAMFER_TANGENT_PROPAGATION = 4  # swFeatureChamferOption_e
SW_SEL_FACES = 2                  # swSelectType_e
SW_CUSTOM_TEXT, SW_REPLACE = 30, 2
SW_MATE_COINCIDENT, SW_MATE_CLOSEST, SW_MATE_OK = 0, 2, 1  # swMateType_e, swMateAlign_e, swAddMateError_e
SW_MATE_DISTANCE = 5              # swMateType_e
SW_MATE_ALIGNED, SW_MATE_ANTI_ALIGNED = 0, 1  # swMateAlign_e
SW_DIMENSION_DRIVEN = 1           # swDimensionDrivenState_e
SW_OPEN_SILENT = 1
SW_OPEN_VOLL = 64                 # swOpenDocOptions_OverrideDefaultLoadLightweight
SW_DOC_PART, SW_DOC_ASSEMBLY = 1, 2
SW_KOMPONENTE_UNTERDRUECKT = 0    # swComponentSuppressionState_e
SW_UNTERDRUECKEN_OK = 2           # swSuppressionError_e.swSuppressionChangeOk
SW_MASS = "D1"                    # Maß einer Abstandsverknüpfung (Spike S12 Zeile 8)


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


def abweichungen(n: dict) -> list[str]:
    """Was am Ergebnis von `nachpruefen` gegen ein Muster spricht; eine andere Vorlage oder ein neues Jahr zeigt sich hier."""
    aus = []
    for k, soll in SOLL_VOLUMEN.items():
        ist = n.get(k)
        if ist is None:
            aus.append(f"Konfiguration {k} fehlt")
        elif not ist["neuaufbau"] or ist["whats_wrong"]:
            aus.append(f"{k}: Neuaufbau {ist['neuaufbau']}, What's Wrong {ist['whats_wrong']}")
        elif abs(ist["volumen"] - soll) > 0.02:
            aus.append(f"{k}: Volumen {ist['volumen']} statt {soll} mm³")
    b = n["baugruppe"]
    if n["oeffnen_baugruppe"]["fehler"] or not b["neuaufbau"] or b["whats_wrong"] or len(b["komponenten"]) != 2:
        aus.append(f"Baugruppe: {n['oeffnen_baugruppe']}, {b}")
    return aus


class MusterFehlt(RuntimeError):
    pass


def _jahr_im_git() -> int:
    return json.loads((MUSTER_GIT.parent / "bestand.json").read_text(encoding="utf-8"))["sw_jahr"]


def muster_ordner(r: Rechner) -> Path:
    """Ordner der Muster für das SolidWorks-Jahr dieses Rechners: die Dateien im Git oder die hier erzeugten."""
    if r.sw_jahr == _jahr_im_git():
        return MUSTER_GIT
    ordner = r.arbeitsordner / "BESTAND-MUSTER" / str(r.sw_jahr)
    fehlt = [n for n in DATEIEN if not (ordner / n).is_file()]
    if fehlt:
        raise MusterFehlt(f"Muster für SolidWorks {r.sw_jahr} fehlen ({', '.join(fehlt)}): -m werkzeuge.bestand_muster ausführen")
    return ordner


def hubeinheit_ordner(r: Rechner) -> Path:
    """Ordner der Musterbaugruppe: Die Kopie im Git gilt nur für ihr Jahr (Modulkopf), sonst die hier erzeugte."""
    git = MUSTER_GIT / "baugruppe"
    if r.sw_jahr == _jahr_im_git() and all((git / rel).is_file() for rel in HUB_DATEIEN):
        return git
    ordner = r.arbeitsordner / "BESTAND-MUSTER" / str(r.sw_jahr) / "baugruppe"
    fehlt = [rel for rel in HUB_DATEIEN if not (ordner / rel).is_file()]
    if fehlt:
        raise MusterFehlt(f"Musterbaugruppe für SolidWorks {r.sw_jahr} fehlt ({', '.join(fehlt)}): "
                          "-m werkzeuge.bestand_muster hubeinheit ausführen")
    return ordner


def uebernimm_muster(quelle: Path, ziel: Path) -> None:
    """Lagerdeckel, Motor und `Muster.SLDASM` unverändert in den Bauordner; die Baugruppe findet sie neben sich (S18g)."""
    ziel.mkdir(parents=True, exist_ok=True)
    for name in DATEIEN:
        shutil.copy2(quelle / name, ziel / name)


def uebernimm_hubeinheit(quelle: Path, ziel: Path) -> None:
    for rel in HUB_DATEIEN:
        (ziel / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle / rel, ziel / rel)


# ---------------------------------------------------------------------------------------------------- Hubeinheit (Etappe 2)


def baue_block(app, r, pfad: Path, box: tuple, hoehe: float, benennung: str, danach=None) -> dict:
    """Ein Teil aus einer Extrusion in der Ebene vorne: `box` (x0, y0, x1, y1) in mm, Z 0…`hoehe`. `danach(model, nullpunkt)` ergänzt
    Features, solange das Teil offen ist."""
    model = app.NewDocument(str(r.vorlage_teil), 0, 0, 0)
    nullpunkt = ursprung(model)
    model.ClearSelection2(True)
    ebenen(model)[0].Select2(False, 0)
    model.SketchManager.InsertSketch(True)
    s = Skizze(app, model)
    rechteck(s, nullpunkt, *box, 0)
    extrusion(model, s.ende(), hoehe)
    d = {"danach": danach(model, nullpunkt) if danach else None}
    model.EditRebuild3
    db, name = finde_material(list(app.GetMaterialDatabases or ()), "1.0038")
    model.SetMaterialPropertyName2("", db, name)
    model.Extension.CustomPropertyManager("").Add3("Benennung", SW_CUSTOM_TEXT, benennung, SW_REPLACE)
    d |= {"volumen": volumen(model), "baum": feature_liste(model), "speichern": speichere(model, pfad)}
    app.CloseDoc(model.GetTitle)
    return d


def schlitten_zusatz(app):
    """Kernloch Ø5×12 von oben bei (10, 10), Länge über die globale Variable `L` (Referenz: Punkt `gleichung` in einem Teil)."""
    def ergaenze(model, nullpunkt) -> dict:
        s = skizze_auf_flaeche(app, model, -20, -20, 20)
        kreis(s, nullpunkt, 10, 10, 20, 5)
        schnitt(model, s.ende(), 0, 12)
        gl = model.GetEquationMgr
        return {"gleichungen": [gl.Add2(-1, '"L" = 60', True), gl.Add2(-1, '"D1@Skizze1" = "L"', True)]}

    return ergaenze


def baue_hub_teile(app, r, ordner: Path) -> dict:
    (ordner / "teile").mkdir(parents=True, exist_ok=True)
    return {"grundplatte": baue_block(app, r, ordner / TEILE_HUB[0], (-100, -40, 100, 40), 15, "Grundplatte"),
            "schlitten": baue_block(app, r, ordner / TEILE_HUB[1], (-30, -25, 30, 25), 20, "Schlitten", schlitten_zusatz(app)),
            "anschlag": baue_block(app, r, ordner / TEILE_HUB[2], (-10, -10, 10, 10), 30, "Anschlag")}


def mates(asm) -> list:
    """Verknüpfungs-Features unter dem Ordner MateGroup, in Baumreihenfolge."""
    f = asm.FirstFeature
    while f is not None and f.GetTypeName2 != "MateGroup":
        f = f.GetNextFeature
    aus, unter = [], None if f is None else f.GetFirstSubFeature
    while unter is not None:
        aus.append(unter)
        unter = unter.GetNextSubFeature
    return aus


def strahl(asm, von, nach):
    """Auswahl der ersten Fläche auf dem Strahl von `von` (mm) in Richtung `nach`, für `verknuepfe`."""
    def waehle(anhaengen: bool) -> None:
        if not asm.Extension.SelectByRay(*(mm(c) for c in von), *nach, 0.0005, SW_SEL_FACES, anhaengen, 1, 0):
            raise RuntimeError(f"Keine Fläche auf dem Strahl {von} → {nach}")

    return waehle


def ebene_von(feature):
    def waehle(anhaengen: bool) -> None:
        if not feature.Select2(anhaengen, 1):
            raise RuntimeError(f"Ebene {feature.Name} nicht auswählbar")

    return waehle


def lage_mm(komp) -> list[float]:
    return [round(in_mm(x), 4) for x in komp.Transform2.ArrayData[9:12]]


def verknuepfe(asm, name: str, typ: int, ausrichtung: int, a, b, wert: float = 0.0, grenzen: tuple | None = None, flip: bool = False):
    """Eine Verknüpfung über `AddMate5`, benannt und neu aufgebaut; `grenzen` (unten, oben) in mm macht aus dem Abstand eine Grenze
    mit dem Wert `unten`. Das neue Feature kommt aus dem Baum, nie eine schon vorhandene Verknüpfung."""
    vorher = {f.Name for f in mates(asm)}
    unten, oben = grenzen or (wert, wert)
    asm.ClearSelection2(True)
    a(False)
    b(True)
    status = byref_long()
    asm.AddMate5(typ, ausrichtung, flip, mm(unten), mm(oben), mm(unten), 1, 1, 0.0, 0.0, 0.0, False, False, 0, status)
    asm.ClearSelection2(True)
    neu = [f for f in mates(asm) if f.Name not in vorher]
    if status.value != SW_MATE_OK or len(neu) != 1:
        raise RuntimeError(f"{name}: AddMate5 Status {status.value}, {len(neu)} neue Verknüpfungen")
    neu[0].Name = name
    asm.EditRebuild3
    return neu[0]


def abstand_mit_lage(asm, name: str, komp, soll: tuple, a, b, wert: float, ausrichtung: int = SW_MATE_ALIGNED, **optionen):
    """Abstand, dessen Vorzeichen SolidWorks wählt (S13 belegt nur Flächen gleicher Ausrichtung): Steht die Komponente danach falsch,
    einmal mit umgekehrter Bemaßung. Die Rückgabe sagt, ob es nötig war."""
    for flip in (False, True):
        f = verknuepfe(asm, name, SW_MATE_DISTANCE, ausrichtung, a, b, wert, flip=flip, **optionen)
        if all(abs(p - q) <= TOL_LAGE_MM for p, q in zip(lage_mm(komp), soll)):
            return flip
        f.Select2(False, 0)
        asm._FlagAsMethod("EditDelete")
        asm.EditDelete()
        asm.EditRebuild3
    raise RuntimeError(f"{name}: {komp.Name2} steht auf {lage_mm(komp)} statt {soll}")


def lege(app, komp, x: float, y: float, z: float) -> None:
    """Ursprung der Komponente auf (x, y, z) in mm, ohne Drehung: `AddComponent5` setzt die Mitte der Box, die kennt nur das Teil."""
    mu = app.GetMathUtility
    mu._FlagAsMethod("CreateTransform")
    t = mu.CreateTransform(r8_array([1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0, mm(x), mm(y), mm(z), 1.0, 0, 0, 0]))
    if not komp.SetTransformAndSolve2(t):
        raise RuntimeError(f"{komp.Name2}: Lage nicht gesetzt")


def anschlag_mates(asm, nummer: int, komp, platte, x: float) -> dict:
    """Anschlag an den eigenen Standardebenen: Die bleiben beim Ersetzen erhalten, seine Flächen nicht."""
    vorne, oben, rechts = (komp.FeatureByName(e.Name) for e in ebenen(komp.GetModelDoc2))
    mitte = platte.FeatureByName(ebenen(platte.GetModelDoc2)[1].Name)
    rechts_platte = platte.FeatureByName(ebenen(platte.GetModelDoc2)[2].Name)
    verknuepfe(asm, f"Anschlag{nummer} Auflage", SW_MATE_COINCIDENT, SW_MATE_CLOSEST, ebene_von(vorne),
               strahl(asm, (x + 15, 30, 60), (0, 0, -1)))
    verknuepfe(asm, f"Anschlag{nummer} Mitte", SW_MATE_COINCIDENT, SW_MATE_CLOSEST, ebene_von(oben), ebene_von(mitte))
    return {"flip": abstand_mit_lage(asm, f"Anschlag{nummer} Lage", komp, (x, 0, 15), ebene_von(rechts), ebene_von(rechts_platte), x)}


def baue_hubeinheit(app, r, ordner: Path) -> dict:
    d: dict = {}
    e, w = byref_long(), byref_long()
    pfade = {n: ordner / rel for n, rel in (("platte", TEILE_HUB[0]), ("schlitten", TEILE_HUB[1]), ("anschlag", TEILE_HUB[2]))}
    offen = [app.OpenDoc6(str(p), SW_DOC_PART, SW_OPEN_SILENT, "", e, w) for p in pfade.values()]
    offen.append(app.OpenDoc6(str(ordner / "Muster.SLDASM"), SW_DOC_ASSEMBLY, SW_OPEN_SILENT | SW_OPEN_VOLL, "", e, w))
    asm = app.NewDocument(str(r.vorlage_baugruppe), 0, 0, 0)
    platte = asm.AddComponent5(str(pfade["platte"]), 0, "", False, "", 0.0, 0.0, mm(7.5))
    schlitten = asm.AddComponent5(str(pfade["schlitten"]), 0, "", False, "", mm(-70), 0.0, mm(55))  # angehoben: Unterseite frei
    anschlag1 = asm.AddComponent5(str(pfade["anschlag"]), 0, "", False, "", mm(30), 0.0, mm(30))
    anschlag2 = asm.AddComponent5(str(pfade["anschlag"]), 0, "", False, "", mm(70), 0.0, mm(30))
    muster = asm.AddComponent5(str(ordner / "Muster.SLDASM"), 0, "", False, "", 0.0, mm(150), 0.0)
    if None in (platte, schlitten, anschlag1, anschlag2, muster):
        raise RuntimeError("AddComponent5 fehlgeschlagen")
    asm.ClearSelection2(True)
    platte.Select4(False, asm.SelectionManager.CreateSelectData, False)
    asm._FlagAsMethod("FixComponent")
    asm.FixComponent()
    asm.ClearSelection2(True)
    lege(app, muster, 0, 150, 0)
    d["speichern"] = speichere(asm, ordner / HUBEINHEIT)

    verknuepfe(asm, "Schlitten Auflage", SW_MATE_COINCIDENT, SW_MATE_ANTI_ALIGNED, strahl(asm, (-70, 0, 30), (0, 0, 1)),
               strahl(asm, (-70, 0, 30), (0, 0, -1)))
    d["seite"] = abstand_mit_lage(asm, "Schlitten Seite", schlitten, (lage_mm(schlitten)[0], 0, 15),
                                  strahl(asm, (-70, -60, 25), (0, 1, 0)), strahl(asm, (-70, -60, 7.5), (0, 1, 0)), 15)
    d["hub"] = abstand_mit_lage(asm, "Hub", schlitten, (-70, 0, 15), strahl(asm, (-150, 0, 25), (1, 0, 0)),
                                strahl(asm, (-150, 0, 7.5), (1, 0, 0)), 0, grenzen=HUB_GRENZE["Hub"])
    ebenen_hub = ebenen(asm)
    d["anschlag1"] = anschlag_mates(asm, 1, anschlag1, platte, 30)
    d["anschlag2"] = anschlag_mates(asm, 2, anschlag2, platte, 70)
    vorne, _, rechts = (muster.FeatureByName(e_.Name) for e_ in ebenen(muster.GetModelDoc2))
    verknuepfe(asm, "Antrieb vorne", SW_MATE_COINCIDENT, SW_MATE_CLOSEST, ebene_von(vorne), ebene_von(ebenen_hub[0]))
    verknuepfe(asm, "Antrieb rechts", SW_MATE_COINCIDENT, SW_MATE_CLOSEST, ebene_von(rechts), ebene_von(ebenen_hub[2]))
    d["antrieb"] = abstand_mit_lage(asm, "Antrieb Abstand", muster, HUB_LAGE["Muster-1"], strahl(asm, (-20, 100, 10), (0, 1, 0)),
                                    strahl(asm, (-20, 100, 7.5), (0, -1, 0)), 80, ausrichtung=SW_MATE_ANTI_ALIGNED)

    eigenschaften = asm.Extension.CustomPropertyManager("")
    for feld, wert in (("Benennung", "Hubeinheit"), ("Revision", "A")):
        eigenschaften.Add3(feld, SW_CUSTOM_TEXT, wert, SW_REPLACE)
    standard = asm.ConfigurationManager.ActiveConfiguration.Name
    d["konfiguration_neu"] = asm.ConfigurationManager.AddConfiguration2(KONFIG_OHNE, "", "", 0, "", "", True) is not None
    asm.ShowConfiguration2(KONFIG_OHNE)  # AddConfiguration2 aktiviert die neue Konfiguration nicht verlässlich
    komp = next(k for k in asm.GetComponents(True) if k.Name2 == "Muster-1")
    d["unterdruecken"] = komp.SetSuppression2(SW_KOMPONENTE_UNTERDRUECKT)
    if d["unterdruecken"] != SW_UNTERDRUECKEN_OK:
        raise RuntimeError(f"Muster-1 nicht unterdrückt: {d['unterdruecken']}")
    asm.EditRebuild3
    d["konfiguration_aktiv"] = asm.ShowConfiguration2(standard)
    asm.EditRebuild3
    s, w2 = byref_long(), byref_long()
    d["speichern2"] = asm.Save3(SW_SAVEAS_SILENT, s, w2), s.value, w2.value
    app.CloseDoc(asm.GetTitle)
    for dokument in offen:
        try:
            app.CloseDoc(dokument.GetTitle)
        except AttributeError:  # SolidWorks hat es mit der Baugruppe geschlossen
            pass
    return d


def _komponente_stand(k) -> dict:
    weg = k.GetSuppression2 == SW_KOMPONENTE_UNTERDRUECKT
    return {"lage": None if weg else lage_mm(k), "status": k.GetConstrainedStatus, "unterdrueckt": weg, "pfad": k.GetPathName}


def nachpruefen_hub(app, ordner: Path) -> dict:
    """Erwartet: öffnen ohne Fehler, in beiden Konfigurationen Neuaufbau ohne Fehler, alle Komponenten an ihrem Platz."""
    d: dict = {"volumen": {}}
    for rel, name in zip(TEILE_HUB, SOLL_VOLUMEN_HUB):
        e, w = byref_long(), byref_long()
        model = app.OpenDoc6(str(ordner / rel), SW_DOC_PART, SW_OPEN_SILENT, "", e, w)
        d["volumen"][name] = volumen(model)
        app.CloseDoc(model.GetTitle)
    e, w = byref_long(), byref_long()
    asm = app.OpenDoc6(str(ordner / HUBEINHEIT), SW_DOC_ASSEMBLY, SW_OPEN_SILENT | SW_OPEN_VOLL, "", e, w)
    d["oeffnen"] = {"fehler": e.value, "warnungen": w.value}
    aktiv = asm.ConfigurationManager.ActiveConfiguration.Name
    for k in asm.GetConfigurationNames:
        asm.ShowConfiguration2(k)
        ok = asm.ForceRebuild3(False)
        d[k] = {"neuaufbau": ok, "whats_wrong": asm.Extension.GetWhatsWrongCount,
                "komponenten": {x.Name2: _komponente_stand(x) for x in asm.GetComponents(False) or ()},
                "verknuepfungen": {f.Name: {"fehler": int(f.GetErrorCode2(byref_bool()))} for f in mates(asm)}}
    asm.ShowConfiguration2(aktiv)
    f = next(x for x in mates(asm) if x.Name == "Hub")
    m, wert = f.GetSpecificFeature2, f.Parameter(SW_MASS).SystemValue
    d["hub"] = {"wert": round(in_mm(wert), 4), "min": round(in_mm(wert + m.MinimumVariation), 4),
                "max": round(in_mm(wert + m.MaximumVariation), 4)}
    app.CloseDoc(asm.GetTitle)
    return d


def _komponenten_abweichung(k: str, stand: dict, ohne: bool) -> list[str]:
    # Kinder einer unterdrückten Unterbaugruppe nennt `GetComponents` womöglich nicht (S19f)
    aus = [f"{k}: {n} fehlt" for n in HUB_KOMPONENTEN if n not in stand and not (ohne and n.startswith("Muster-1/"))]
    for n, e in stand.items():
        soll_weg = ohne and n.startswith("Muster-1")
        if bool(e["unterdrueckt"]) != soll_weg:
            aus.append(f"{k}: {n} ist {'' if e['unterdrueckt'] else 'nicht '}unterdrückt")
        elif not soll_weg and n in HUB_LAGE:
            if e["lage"] is None or any(abs(p - q) > TOL_LAGE_MM for p, q in zip(e["lage"], HUB_LAGE[n])):
                aus.append(f"{k}: {n} steht auf {e['lage']} statt {list(HUB_LAGE[n])}")
            if e["status"] != HUB_STATUS[n]:
                aus.append(f"{k}: {n} hat Status {e['status']} statt {HUB_STATUS[n]}")
    return aus


def abweichungen_hub(n: dict) -> list[str]:
    """Was am Ergebnis von `nachpruefen_hub` gegen das Muster spricht."""
    aus = [f"{name}: Volumen {n['volumen'].get(name)} statt {soll} mm³" for name, soll in SOLL_VOLUMEN_HUB.items()
           if abs(n["volumen"].get(name, 0.0) - soll) > 0.02]
    if n["oeffnen"]["fehler"]:
        aus.append(f"Öffnen: {n['oeffnen']}")
    for k in ("Standard", KONFIG_OHNE):
        stand = n.get(k)
        if stand is None:
            aus.append(f"Konfiguration {k} fehlt")
            continue
        if not stand["neuaufbau"] or stand["whats_wrong"]:
            aus.append(f"{k}: Neuaufbau {stand['neuaufbau']}, What's Wrong {stand['whats_wrong']}")
        aus += _komponenten_abweichung(k, stand["komponenten"], k == KONFIG_OHNE)
        mate = stand["verknuepfungen"]
        aus += [f"{k}: Verknüpfung {v} fehlt" for v in HUB_VERKNUEPFUNGEN if v not in mate]
        aus += [f"{k}: Verknüpfung {v} hat Fehler {e['fehler']}" for v, e in mate.items() if e["fehler"]]
    unten, oben = HUB_GRENZE["Hub"]
    if abs(n["hub"]["min"] - unten) > TOL_LAGE_MM or abs(n["hub"]["max"] - oben) > TOL_LAGE_MM:
        aus.append(f"Hub: {n['hub']} statt {unten}…{oben} mm")
    return aus


def hubeinheit(r: Rechner, ins_git: bool) -> None:
    """Baut die Hubeinheit aus den vorhandenen Mustern; übernommen wird nur, was `abweichungen_hub` nicht beanstandet."""
    quelle = muster_ordner(r)
    app = verbinde(r.sw_jahr)
    jahr = r.arbeitsordner / "BESTAND-MUSTER" / str(r.sw_jahr)
    ordner = jahr / "bau_hub"
    if ordner.exists():
        shutil.rmtree(ordner)
    uebernimm_muster(quelle, ordner)
    d: dict = {}
    alt = app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE)
    app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, False)
    t0 = time.monotonic()
    try:
        d["teile"] = baue_hub_teile(app, r, ordner)
        d["baugruppe"] = baue_hubeinheit(app, r, ordner)
        d["nachpruefen"] = nachpruefen_hub(app, ordner)
    finally:
        app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, alt)
    d["sekunden"] = round(time.monotonic() - t0, 1)
    d["abweichungen"] = abweichungen_hub(d["nachpruefen"])
    print(json.dumps(d, indent=1, ensure_ascii=False, default=str))
    if d["abweichungen"]:
        raise SystemExit(f"Keine Hubeinheit für SolidWorks {r.sw_jahr}, nichts übernommen: {d['abweichungen']}")
    uebernimm_hubeinheit(ordner, jahr / "baugruppe")
    print(f"Hubeinheit für SolidWorks {r.sw_jahr} in {jahr / 'baugruppe'}")
    if ins_git:
        uebernimm_hubeinheit(ordner, MUSTER_GIT / "baugruppe")
        print(f"Kopie in {MUSTER_GIT / 'baugruppe'}, von Hand einchecken")


def main() -> None:
    parser = argparse.ArgumentParser(description="Musterdateien der Bestandsdateien im Arbeitsordner erzeugen")
    parser.add_argument("was", nargs="?", choices=["hubeinheit"], help="ohne Angabe: Lagerdeckel, Motor, Muster.SLDASM")
    parser.add_argument("--ins-git", action="store_true", help="Hubeinheit zusätzlich nach tests/referenz/bestand/muster/baugruppe/")
    args = parser.parse_args()
    r = lade_rechner()
    if args.was == "hubeinheit":
        hubeinheit(r, args.ins_git)
        return
    app = verbinde(r.sw_jahr)
    ziel = r.arbeitsordner / "BESTAND-MUSTER" / str(r.sw_jahr)
    ordner = ziel / "bau"
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
    d["abweichungen"] = abweichungen(d["nachpruefen"])
    print(json.dumps(d, indent=1, ensure_ascii=False, default=str))
    if d["abweichungen"]:
        raise SystemExit(f"Kein Muster für SolidWorks {r.sw_jahr}, nichts übernommen: {d['abweichungen']}")
    for name in DATEIEN:
        shutil.copy2(ordner / name, ziel / name)
    print(f"Muster für SolidWorks {r.sw_jahr} in {ziel}")


if __name__ == "__main__":
    main()
