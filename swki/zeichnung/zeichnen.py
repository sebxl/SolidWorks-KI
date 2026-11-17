"""`swki zeichnen`: Zeichnung eines gebauten Teils, Stufe 1 ohne Maße (Plan 2026-11-17, Design §5, §6.1).

Spike Z1.0 (docs/zeichnungsableitung/spike-z1.md) ist verbindlich: Teil vorher öffnen, Blatt über `SetupSheet5` mit dem
Blattformat aus `config/rechner.yaml` (`zeichnung`), leere Dispatch-Argumente über `callout_leer()`, nullargumentige
Member liefert der dynamische Dispatch beim Zugriff (`_ruf`).

API (swki api methode, SW 2025): ISldWorks.NewDocument (4), GetUserPreferenceStringValue (1);
IDrawingDoc.SetupSheet5 (11, 2009), CreateDrawViewFromModelView3 (5, 2005), CreateUnfoldedViewAt3 (4, 2005),
ActivateView (1), CreateSectionViewAt5 (7, 2010), GetCurrentSheet; IView.Angle/Position (put), GetOutline, GetName2;
ISketchManager.CreateLine (6); IModelDocExtension.SetUserPreferenceToggle (3, 2009), SelectByID2 (9),
SaveAs (6), CustomPropertyManager (1) → ICustomPropertyManager.Add3 (4, 2014); IModelDoc2.EditRebuild3, ClearSelection2.
"""

import hashlib
import math
import time
from pathlib import Path

import win32com.client.dynamic

from swki.auftrag import auftrag_name, dateiname, lauf_ordner, laeufe
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.messen import oeffne
from swki.spec.freigabe import pruefe_freigabe
from swki.spec.laden import lade_spec
from swki.verbindung import byref_long, callout_leer, r8_array, verbinde
from swki.zeichnung.ansichten import Ansicht, waehle_ansichten
from swki.zeichnung.blatt import FORMATE
from swki.zeichnung.layout import anordnen

SW_DEFAULT_TEMPLATE_DRAWING = 10            # swUserPreferenceStringValue_e
SW_DWG_TEMPLATE_CUSTOM = 12                 # swDwgTemplates_e
PAPIER = {"A4": 7, "A4quer": 6, "A3quer": 8}  # swDwgPaperSizes_e (A4 hoch = A4sizeVertical)
AUTO_MITTELLINIEN = (189, 190, 308)         # swDetailingAutoInsertCenterMarks, …CenterLines, …CenterMarksForHoles
SAVE_SILENT = 1                             # swSaveAsOptions_Silent
EIGENSCHAFT_TEXT = 30                       # swCustomInfoType_e.swCustomInfoText
EIGENSCHAFT_ERSETZEN = 2                    # swCustomPropertyAddOption_e.swCustomPropertyReplaceValue
ABSTAND_PROBE_M = 0.12                      # Probeplatzierung vor der Anordnung


class ZeichnungFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str):
        super().__init__(meldung)
        self.daten = {"code": code}


def _ruf(obj, name, *args):
    x = getattr(obj, name)
    if args:
        return x(*args)
    return x if isinstance(x, win32com.client.dynamic.CDispatch) or not callable(x) else x()


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _umriss_mm(view) -> tuple[float, float, float, float]:
    return tuple(v * 1000 for v in list(_ruf(view, "GetOutline")))


def _groesse_1zu1(view) -> tuple[float, float]:
    """Umriss in mm bei 1:1: SolidWorks skaliert neue Ansichten automatisch (IView.ScaleDecimal ≠ Blattmaßstab)."""
    x0, y0, x1, y1 = _umriss_mm(view)
    s = _ruf(view, "ScaleDecimal")
    return ((x1 - x0) / s, (y1 - y0) / s)


def _setze_lage(view, mitte_mm: tuple[float, float]) -> None:
    """IView.Position als double-Array (pywin32-fallstricke: rohe Tupel wirken nicht); danach zurücklesen."""
    view.Position = r8_array([mitte_mm[0] / 1000, mitte_mm[1] / 1000])
    ist = [v * 1000 for v in list(_ruf(view, "Position"))[:2]]
    if abs(ist[0] - mitte_mm[0]) > 0.5 or abs(ist[1] - mitte_mm[1]) > 0.5:
        raise ZeichnungFehler("ZEICHNUNG_LAGE", f"{_ruf(view, 'GetName2')}: Lage {ist} statt {list(mitte_mm)}")


def _blatt(drw, format_: str, massstab: tuple[int, int], blattformat: Path) -> None:
    b, h = FORMATE[format_]
    sheet = _ruf(drw, "GetCurrentSheet")
    if not drw.SetupSheet5(_ruf(sheet, "GetName"), PAPIER[format_], SW_DWG_TEMPLATE_CUSTOM, massstab[0], massstab[1],
                           True, str(blattformat), b / 1000, h / 1000, "Standard", True):
        raise ZeichnungFehler("ZEICHNUNG_BLATT", f"SetupSheet5 {format_} {massstab} mit {blattformat.name} abgelehnt")


def _waehle_ansicht(drw, view) -> None:
    name = _ruf(view, "GetName2")
    _ruf(drw, "Extension").SelectByID2(name, "DRAWINGVIEW", 0, 0, 0, False, 0, callout_leer(), 0)
    drw.ActivateView(name)


def _laengsschnitt(drw, stirn):
    """Schnittlinie senkrecht durch die Mitte der ungedrehten Stirnansicht, Schnitt A-A links daneben (Spike Z1.0)."""
    x0, y0, x1, y1 = (v / 1000 for v in _umriss_mm(stirn))
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    _waehle_ansicht(drw, stirn)
    oben, unten = _in_ansicht(stirn, xm, y1 + 0.005), _in_ansicht(stirn, xm, y0 - 0.005)
    _ruf(drw, "SketchManager").CreateLine(oben[0], oben[1], 0, unten[0], unten[1], 0)
    return drw.CreateSectionViewAt5(x0 - ABSTAND_PROBE_M, ym, 0, "A", 0, None, 0)


def _in_ansicht(view, x_m: float, y_m: float) -> tuple[float, float]:
    """Blattpunkt (m) → Skizzenkoordinaten der aktiven, ungedrehten Ansicht: relativ zum Ansichtsursprung
    (`IView.Position`) und im Modellmaßstab (÷ `IView.ScaleDecimal`). Live Z1.3: Blattkoordinaten direkt landen um
    Lage und Maßstab versetzt (Spike Z1.0 hatte das nicht bemerkt)."""
    px, py = list(_ruf(view, "Position"))[:2]
    s = _ruf(view, "ScaleDecimal")
    return ((x_m - px) / s, (y_m - py) / s)


def _projektion(drw, haupt, rolle: str):
    x0, y0, x1, y1 = (v / 1000 for v in _umriss_mm(haupt))
    _waehle_ansicht(drw, haupt)
    if rolle == "seite":
        return drw.CreateUnfoldedViewAt3(x1 + ABSTAND_PROBE_M, (y0 + y1) / 2, 0, False)
    return drw.CreateUnfoldedViewAt3((x0 + x1) / 2, y0 - ABSTAND_PROBE_M, 0, False)


def _eigenschaften(drw, spec: dict, format_: str, massstab: tuple[int, int]) -> dict:
    eig = spec.get("eigenschaften", {})
    werte = {"Description": eig.get("Benennung", spec["name"]), "Benennung": eig.get("Benennung", spec["name"]),
             "Material": spec.get("material", ""), "Zeichnungsnummer": eig.get("Zeichnungsnummer", spec["name"]),
             "DrawnBy": "swki", "DrawnDate": time.strftime("%d.%m.%Y")}
    cpm = _ruf(drw, "Extension").CustomPropertyManager("")
    for name, wert in werte.items():
        cpm.Add3(name, EIGENSCHAFT_TEXT, str(wert), EIGENSCHAFT_ERSETZEN)
    return werte


def zeichnen(spec_pfad: Path, lauf: int | None = None) -> dict:
    t0 = time.time()
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    if not r.zeichnung:
        raise ZeichnungFehler("ZEICHNUNG_VORLAGE_FEHLT", "config/rechner.yaml: zeichnung: {A4: …, A3quer: …} fehlt")
    auftrag = auftrag_name(spec_pfad)
    lauf = lauf or (laeufe(r, auftrag) or [None])[-1]
    if lauf is None:
        raise SwkiFehler(f"Auftrag {auftrag} hat noch keinen Lauf. Zuerst: swki bauen")
    ordner = lauf_ordner(r, auftrag, lauf)
    teil = ordner / f"{dateiname(spec, auftrag, standard)}.sldprt"
    if not teil.exists():
        raise SwkiFehler(f"{teil} fehlt (Lauf {lauf} ohne gespeichertes Teil)")
    ausgabe = ordner / "zeichnung"
    ausgabe.mkdir(exist_ok=True)
    sha_teil = _sha(teil)
    ansichten = waehle_ansichten(spec)
    app = verbinde(r.sw_jahr)
    model = oeffne(app, teil)
    drw = None
    try:
        drw = app.NewDocument(app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_DRAWING), 0, 0, 0)
        ext = _ruf(drw, "Extension")
        for toggle in AUTO_MITTELLINIEN:
            ext.SetUserPreferenceToggle(toggle, 0, True)
        _blatt(drw, "A3quer", (1, 1), r.zeichnung.get("A3quer") or next(iter(r.zeichnung.values())))
        views = _erzeuge(drw, teil, ansichten)
        groessen = {rolle: _groesse_1zu1(v) for rolle, v in views.items()}
        format_, massstab, plaetze = anordnen(groessen)
        blattformat = r.zeichnung.get(format_)
        if blattformat is None:
            raise ZeichnungFehler("ZEICHNUNG_VORLAGE_FEHLT", f"config/rechner.yaml: zeichnung.{format_} fehlt")
        _blatt(drw, format_, massstab, blattformat)
        for v in views.values():  # Ansichten folgen sonst ihrem automatischen Maßstab (Live Z1.3: Platte zu groß)
            v.ScaleDecimal = massstab[0] / massstab[1]
        basis = next(a.rolle for a in ansichten if a.modellansicht)
        for p in sorted(plaetze, key=lambda p: p.rolle != basis):  # Elternansicht zuerst, Kinder sind ausgerichtet
            _setze_lage(views[p.rolle], p.mitte_mm)
        schnitt = next((_ruf(views[a.rolle], "GetName2") for a in ansichten if a.schnitt), None)
        eigenschaften = _eigenschaften(drw, spec, format_, massstab)
        _ruf(drw, "EditRebuild3")
        zeichnung, pdf = ausgabe / f"{teil.stem}.slddrw", ausgabe / f"{teil.stem}.pdf"
        for ziel in (zeichnung, pdf):
            f, w = byref_long(), byref_long()
            if not ext.SaveAs(str(ziel), 0, SAVE_SILENT, callout_leer(), f, w):
                raise ZeichnungFehler("ZEICHNUNG_SPEICHERN", f"SaveAs {ziel.name}: Fehler {f.value}")
        info = [{"rolle": rolle, "name": _ruf(v, "GetName2"), "umriss_mm": [round(x, 1) for x in _umriss_mm(v)]}
                for rolle, v in views.items()]
    finally:
        if drw is not None:
            sw.schliesse(app, drw)
        sw.schliesse(app, model)
    if _sha(teil) != sha_teil:
        raise ZeichnungFehler("ZEICHNUNG_TEIL_GEAENDERT", f"{teil.name} wurde beim Zeichnen verändert")
    return {"zeichnung": str(zeichnung), "pdf": str(pdf), "png": _png(pdf), "format": format_,
            "massstab": f"{massstab[0]}:{massstab[1]}", "ansichten": info, "schnitt": schnitt,
            "eigenschaften": eigenschaften, "dauer_s": round(time.time() - t0, 1)}


def _erzeuge(drw, teil: Path, ansichten: list[Ansicht]) -> dict:
    """Basis = die Ansicht mit Modellansicht. Ein Schnitt ohne Modellansicht entsteht aus ihr (Längsschnitt eines
    Drehteils), die übrigen werden aus der Hauptansicht projiziert."""
    basis = next(a for a in ansichten if a.modellansicht)
    view = drw.CreateDrawViewFromModelView3(str(teil), basis.modellansicht, 0.25, 0.2, 0)
    if view is None:
        raise ZeichnungFehler("ZEICHNUNG_ANSICHT", f"Modellansicht {basis.modellansicht} nicht erzeugt")
    if basis.winkel_grad:
        view.Angle = math.radians(basis.winkel_grad)
    views = {basis.rolle: view}
    for a in ansichten:
        if a is basis:
            continue
        if a.modellansicht is None and a.schnitt and a.rolle == "haupt":
            v = _laengsschnitt(drw, view)
        else:
            v = _projektion(drw, views["haupt"], a.rolle)
        if v is None:
            raise ZeichnungFehler("ZEICHNUNG_ANSICHT", f"Ansicht {a.rolle} nicht erzeugt")
        views[a.rolle] = v
    return views


def _png(pdf: Path) -> str | None:
    try:
        import pymupdf
    except ImportError:
        return None
    png = pdf.with_suffix(".png")
    with pymupdf.open(pdf) as doc:
        doc[0].get_pixmap(dpi=110).save(png)
    return str(png)
