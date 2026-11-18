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
import json
import math
import time
from pathlib import Path

import win32com.client.dynamic

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.messen import oeffne
from swki.pruefung.schleife import lies_laeufe
from swki.spec.freigabe import pruefe_freigabe
from swki.spec.laden import lade_spec
from swki.verbindung import byref_long, callout_leer, r8_array, verbinde
from swki.zeichnung.ansichten import (Ansicht, achsvektor, blickachsen, hinweise, vorzugsansichten,
                                     waehle_ansichten, weitere_rollen)
from swki.zeichnung.bemassen import MASSABSTAND_M, bemasse, ordne_masse_an, setze_neu
from swki.zeichnung.blatt import FORMATE, SCHRIFTFELD_MM, zeichenfeld
from swki.zeichnung.lesbarkeit import pruefe_pdf
from swki.zeichnung.reihen import ABSTAND_MM, LinMass, reihen, seite
from swki.zeichnung.layout import anordnen
from swki.zeichnung.massplan import massplan, massplan_meldungen
from swki.zeichnung.zuordnung import max_je_ansicht

NAEHE_MM = 25.0  # Befund gehört zur nächsten Maßzahl in diesem Umkreis (Live 18.11.: Kennbuchstabe „A“ auf der Maßlinie, Zahl 18 mm weg)

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
    lage = {"seite": (x1 + ABSTAND_PROBE_M, (y0 + y1) / 2), "seite_rechts": (x0 - ABSTAND_PROBE_M, (y0 + y1) / 2),
            "drauf": ((x0 + x1) / 2, y0 - ABSTAND_PROBE_M), "unter": ((x0 + x1) / 2, y1 + ABSTAND_PROBE_M)}[rolle]
    return drw.CreateUnfoldedViewAt3(lage[0], lage[1], 0, False)


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
    lauf, meldungen = waehle_lauf(spec_pfad, lauf)
    meldungen += hinweise(spec)
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
        views, schnitt, nicht_erzeugt = _erzeuge(drw, teil, ansichten)
        meldungen += nicht_erzeugt
        plan = massplan(spec, json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8")))
        basis = next(a.rolle for a in ansichten if a.modellansicht)
        bem = bemasse(drw, views, plan, ["haupt"] + [r for r in views if r != "haupt"], max_je_ansicht(standard),
                      weitere_rollen(spec), lambda rolle: _projektion(drw, views["haupt"], rolle),
                      vorzugsansichten(spec, plan), blickachsen(ansichten, weitere_rollen(spec)))
        meldungen += bem.meldungen
        meldungen += massplan_meldungen(spec)
        for rolle in [r for r in list(views) if r not in ("haupt", basis) and not bem.je_ansicht.get(r)]:
            if not _loesche_ansicht(drw, views.pop(rolle)):  # Ansicht ohne eigenes Maß entfällt (Design §6.1)
                meldungen.append(f"ANSICHT_NICHT_GELOESCHT: {rolle} ohne Maß blieb auf dem Blatt")
        groessen = {rolle: _groesse_1zu1(v) for rolle, v in views.items()}
        format_, massstab, plaetze = anordnen(groessen)
        blattformat = r.zeichnung.get(format_)
        if blattformat is None:
            raise ZeichnungFehler("ZEICHNUNG_VORLAGE_FEHLT", f"config/rechner.yaml: zeichnung.{format_} fehlt")
        _blatt(drw, format_, massstab, blattformat)
        for v in views.values():  # Ansichten folgen sonst ihrem automatischen Maßstab (Live Z1.3: Platte zu groß)
            v.ScaleDecimal = massstab[0] / massstab[1]
        for p in sorted(plaetze, key=lambda p: p.rolle != basis):  # Elternansicht zuerst, Kinder sind ausgerichtet
            _setze_lage(views[p.rolle], p.mitte_mm)
        neu_gesetzt = _neue_masse(drw, views, plan, bem.neu, achsvektor(spec), meldungen)
        for rolle, v in views.items():
            if not ordne_masse_an(drw, v):
                meldungen.append(f"MASSE_NICHT_ANGEORDNET: {rolle}")
        eigenschaften = _eigenschaften(drw, spec, format_, massstab)
        _ruf(drw, "EditRebuild3")
        zeichnung, pdf = ausgabe / f"{zeichnungsname(spec)}.slddrw", ausgabe / f"{zeichnungsname(spec)}.pdf"
        meldungen += _lesbar_anlegen(drw, ext, views, pdf, format_)
        _speichern(ext, zeichnung)
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
            "eigenschaften": eigenschaften, "meldungen": meldungen,
            "masse": {"plan": len(plan), "gesetzt": bem.gesetzt + sum(neu_gesetzt.values()), "geloescht": bem.geloescht,
                      "je_ansicht": {r: len(bem.je_ansicht.get(r, [])) + neu_gesetzt.get(r, 0) for r in views}}, "dauer_s": round(time.time() - t0, 1)}


def _speichern(ext, ziel: Path) -> None:
    f, w = byref_long(), byref_long()
    if not ext.SaveAs(str(ziel), 0, SAVE_SILENT, callout_leer(), f, w):
        raise ZeichnungFehler("ZEICHNUNG_SPEICHERN", f"SaveAs {ziel.name}: Fehler {f.value}")


def _ausschluss(format_: str) -> list[tuple]:
    """Rand, Rahmen und Schriftfeld gehören nicht zur Lesbarkeitsprüfung der Ansichten."""
    b, h = FORMATE[format_]
    x0, y0, x1, y1 = zeichenfeld(format_)
    return [(0, 0, b, y0), (0, y1, b, h), (0, 0, x0, h), (x1, 0, b, h),
            (x1 - SCHRIFTFELD_MM[0], y0, x1, y0 + SCHRIFTFELD_MM[1])]


LINEAR = (2, 11, 12)  # swDimensionType_e: swLinearDimension, swHorLinearDimension, swVertLinearDimension


def _lineare_masse(view) -> list[tuple[object, LinMass, float]]:
    """Je lineares Maß der Ansicht: Annotation, Spanne/Lage/Textlänge in Blatt-mm (spikes/z1_diag_masslinien.py:
    `IDisplayData` liefert zuerst die beiden Hilfslinien, die Textlage beginnt am Anfang der Zahl; die Annotation sitzt
    in der Zahlmitte) und der Querversatz Annotation – Maßlinie."""
    aus = []
    for i, dd in enumerate(list(_ruf(view, "GetDisplayDimensions") or ())):
        if _ruf(dd, "Type2") not in LINEAR:
            continue
        daten = _ruf(dd, "GetDisplayData")
        if _ruf(daten, "GetLineCount") < 2 or _ruf(daten, "GetTextCount") < 1:
            continue
        h1, h2 = (list(daten.GetLineAtIndex3(k)) for k in (0, 1))
        ann = _ruf(dd, "GetAnnotation")
        ax, ay = (v * 1000 for v in list(_ruf(ann, "GetPosition"))[:2])
        tx, ty = (v * 1000 for v in list(daten.GetTextPositionAtIndex(0))[:2])
        waagrecht = abs(h1[7] - h1[4]) < abs(h1[8] - h1[5])  # Hilfslinie senkrecht → Maßlinie waagrecht
        if waagrecht:
            m = LinMass(i, "h", h1[4] * 1000, h2[4] * 1000, ty, 2 * abs(ax - tx))
            aus.append((ann, m, ay - ty))
        else:
            m = LinMass(i, "v", h1[5] * 1000, h2[5] * 1000, tx, 2 * abs(ay - ty))
            aus.append((ann, m, ax - tx))
    return aus


def _reihen_anlegen(views: dict, vorlauf: dict) -> list[tuple[tuple, tuple[float, float]]]:
    """Nutzer 18.11.2026: Maße übereinander, Zahlen von Linien gekreuzt → lineare Maße je Ansichtsseite in Reihen
    (`swki.zeichnung.reihen`), Lage über `IAnnotation.SetPosition2` (Maßlinie folgt der Zahl). Liefert je Maß die
    Ansichtsseite (Rolle, Richtung, Seite) und die Lage der Zahl in Blatt-mm."""
    platz = []
    for rolle, v in views.items():
        masse, umriss = _lineare_masse(v), _umriss_mm(v)
        eigen = {(r, s): mm for (ro, r, s), mm in vorlauf.items() if ro == rolle}
        lage = reihen([m for _, m, _ in masse], umriss, eigen)
        for ann, m, versatz in masse:
            entlang, quer = lage[m.schluessel]
            x, y = (entlang, quer + versatz) if m.richtung == "h" else (quer + versatz, entlang)
            ann.SetPosition2(x / 1000, y / 1000, 0)
            platz.append(((rolle, m.richtung, seite(m, umriss)), (x, y)))
    return platz


def _lesbar_anlegen(drw, ext, views: dict, pdf: Path, format_: str, runden: int = 3) -> list[str]:
    """Reihen anlegen, PDF speichern, am PDF prüfen (was der Leser sieht). Ein Befund an einer Maßzahl rückt alle
    Reihen ihrer Ansichtsseite um einen Reihenabstand nach außen (Beschriftungen von SolidWorks, die die Reihenanlage
    nicht kennt), dann neu; höchstens `runden` Mal. Was bleibt, wird gemeldet."""
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        pruefen = False
    else:
        pruefen = True
    vorlauf: dict[tuple, float] = {}
    befunde = []
    for runde in range(runden + 1):
        platz = _reihen_anlegen(views, vorlauf)
        _ruf(drw, "EditRebuild3")
        _speichern(ext, pdf)
        if not pruefen:
            return ["LESBARKEIT_UNGEPRUEFT: pymupdf fehlt (Extra pdf)"]
        befunde = pruefe_pdf(pdf, _ausschluss(format_))
        if not befunde or runde == runden:
            break
        seiten = set()
        for b in befunde:
            mx, my = (b.rechteck_mm[0] + b.rechteck_mm[2]) / 2, (b.rechteck_mm[1] + b.rechteck_mm[3]) / 2
            nah = min(platz, key=lambda p: math.dist(p[1], (mx, my)), default=None)
            if nah and math.dist(nah[1], (mx, my)) <= NAEHE_MM:
                seiten.add(nah[0])
        if not seiten:
            break
        for s in seiten:
            vorlauf[s] = vorlauf.get(s, 0.0) + ABSTAND_MM
    return [f"LESBARKEIT: {b.art} „{b.text}“{' / „' + b.anderes + '“' if b.anderes else ''} bei "
            f"({b.rechteck_mm[0]:.0f}, {b.rechteck_mm[1]:.0f}) mm" for b in befunde]


def _loesche_ansicht(drw, view) -> bool:
    """Ansicht löschen und Wirkung prüfen: steht sie danach nicht mehr in den Blattansichten (Review I5)."""
    ext, name = _ruf(drw, "Extension"), _ruf(view, "GetName2")
    drw.ClearSelection2(True)
    ext.SelectByID2(name, "DRAWINGVIEW", 0, 0, 0, False, 0, callout_leer(), 0)
    ext.DeleteSelection2(0)
    return name not in [_ruf(v, "GetName2") for v in list(_ruf(_ruf(drw, "GetCurrentSheet"), "GetViews") or ())]


def _neue_masse(drw, views: dict, plan: list, neu: dict, achse: tuple, meldungen: list[str]) -> dict[str, int]:
    """Neue Maße (Drehteil) über Kanten: Ø links neben der Ansicht, Längen darüber, gestaffelt. Liefert die Zahl der
    wirklich gesetzten Maße je Ansicht (Review I2)."""
    nach_id = {m.id: m for m in plan}
    gesetzt: dict[str, int] = {}
    for rolle, ids in neu.items():
        x0, y0, x1, y1 = (c / 1000 for c in _umriss_mm(views[rolle]))
        zaehler = {"durchmesser": 0, "laenge": 0}
        for mid in ids:
            m = nach_id[mid]
            i = zaehler.setdefault(m.art, 0)
            zaehler[m.art] = i + 1
            platz = ((x0 - 0.012 - i * MASSABSTAND_M, (y0 + y1) / 2) if m.art == "durchmesser"
                     else ((x0 + x1) / 2, y1 + 0.012 + i * MASSABSTAND_M))
            if setze_neu(drw, views[rolle], m, achse, platz):
                gesetzt[rolle] = gesetzt.get(rolle, 0) + 1
            else:
                meldungen.append(f"MASS_NICHT_GESETZT: {mid} ({m.art} {m.wert:g}) – keine passenden Kanten in {rolle}")
    return gesetzt


def zeichnungsname(spec: dict) -> str:
    """Dateiname der Zeichnung = Zeichnungsnummer (das ISO-Muster zeigt ihn groß im Schriftfeld; Nutzer 17.11.2026)."""
    return (spec.get("eigenschaften") or {}).get("Zeichnungsnummer") or spec["name"]


def waehle_lauf(spec_pfad: Path, lauf: int | None) -> tuple[int, list[str]]:
    """Design §5: gezeichnet wird der letzte bestandene Lauf (Bau ok, keine Code-Mängel, Prüfer bestanden). Ein
    ausdrücklich genannter Lauf darf ungeprüft sein; dann trägt das Ergebnis eine Meldung (nur zur Ansicht)."""
    alle = lies_laeufe(spec_pfad)
    if lauf is None:
        bestanden = [e["lauf"] for e in alle if e["bestanden"]]
        if not bestanden:
            raise ZeichnungFehler("ZEICHNUNG_LAUF_NICHT_BESTANDEN", "kein bestandener Lauf (Bau, swki pruefen, Prüfer); "
                                  "zur Ansicht eines ungeprüften Laufs: swki zeichnen <spec> --lauf N")
        return bestanden[-1], []
    eintrag = next((e for e in alle if e["lauf"] == lauf), None)
    if eintrag is None or not eintrag["bestanden"]:
        return lauf, [f"LAUF_NICHT_BESTANDEN: Lauf {lauf} ist nicht bestanden – Zeichnung nur zur Ansicht"]
    return lauf, []


def _erzeuge(drw, teil: Path, ansichten: list[Ansicht]) -> tuple[dict, str | None, list[str]]:
    """Basis = die Ansicht mit Modellansicht. Ein Schnitt ohne Modellansicht entsteht aus ihr (Längsschnitt eines
    Drehteils), die übrigen werden aus der Hauptansicht projiziert. Liefert Ansichten, Name des wirklich erzeugten
    Schnitts und Meldungen für verlangte, aber nicht erzeugte Schnitte (Review I1)."""
    basis = next(a for a in ansichten if a.modellansicht)
    view = drw.CreateDrawViewFromModelView3(str(teil), basis.modellansicht, 0.25, 0.2, 0)
    if view is None:
        raise ZeichnungFehler("ZEICHNUNG_ANSICHT", f"Modellansicht {basis.modellansicht} nicht erzeugt")
    if basis.winkel_grad:
        view.Angle = math.radians(basis.winkel_grad)
    views, schnitt, meldungen = {basis.rolle: view}, None, []
    for a in ansichten:
        if a is basis:
            continue
        if a.modellansicht is None and a.schnitt and a.rolle == "haupt":
            v = _laengsschnitt(drw, view)
            schnitt = _ruf(v, "GetName2") if v is not None else None
        else:
            v = _projektion(drw, views["haupt"], a.rolle)
            if a.schnitt:
                meldungen.append(f"SCHNITT_NICHT_UNTERSTUETZT: Ansicht {a.rolle} bräuchte einen Schnitt (Frästeil, "
                                 "Stufe 1 zeichnet sie ungeschnitten)")
        if v is None:
            raise ZeichnungFehler("ZEICHNUNG_ANSICHT", f"Ansicht {a.rolle} nicht erzeugt")
        views[a.rolle] = v
    return views, schnitt, meldungen


def _png(pdf: Path) -> str | None:
    try:
        import pymupdf
    except ImportError:
        return None
    png = pdf.with_suffix(".png")
    with pymupdf.open(pdf) as doc:
        doc[0].get_pixmap(dpi=110).save(png)
    return str(png)
