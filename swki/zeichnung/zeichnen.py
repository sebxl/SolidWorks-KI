"""`swki zeichnen`: Zeichnung eines gebauten Teils, Stufe 1 ohne Maße (Plan 2026-11-17, Design §5, §6.1).

Spike Z1.0 (docs/zeichnungsableitung/spike-z1.md) ist verbindlich: Teil vorher öffnen, Blatt über `SetupSheet5` mit dem
Blattformat aus `config/rechner.yaml` (`zeichnung`), leere Dispatch-Argumente über `callout_leer()`, nullargumentige
Member liefert der dynamische Dispatch beim Zugriff (`_ruf`).

API (swki api methode, SW 2025): ISldWorks.NewDocument (4), GetUserPreferenceStringValue (1);
IDrawingDoc.SetupSheet5 (11, 2009), CreateDrawViewFromModelView3 (5, 2005), CreateUnfoldedViewAt3 (4, 2005),
ActivateView (1), CreateSectionViewAt5 (7, 2010), GetCurrentSheet; IView.Angle/Position (put), GetOutline, GetName2;
ISketchManager.CreateLine (6), CreateCornerRectangle (6, 2008); IDrawingDoc.CreateDetailViewAt4 (12, 2017;
swDetViewSTANDARD = 0, swDetCirclePROFILE = 0); ISelectionMgr.GetSelectedObjectCount2 (1); IModelDocExtension.SetUserPreferenceToggle (3, 2009), SelectByID2 (9),
SaveAs (6), CustomPropertyManager (1) → ICustomPropertyManager.Add3 (4, 2014); IModelDoc2.EditRebuild3, ClearSelection2.
Stufe 3 (spikes/z1_diag_bohrungsangabe.py, z1_diag_hinweis_ansatz.py): IView.SelectEntity (2), ISelectionMgr.
GetSelectedObjectType3 (2), GetSelectedObject6 (2, 2006), IModelDoc2.InsertNote (1), INote.GetAnnotation,
IAnnotation.GetLeaderCount, GetPosition, SetPosition2 (3, 2014); IDisplayDimension.SetText (2;
swDimensionTextPrefix = 1, swDimensionTextSuffix = 2); IModelDocExtension.SetUserPreferenceInteger/String (3, 2009).
Runde E: IView.GetSection (0, 2000) → IDrSection.GetLabel (0, 2000) – Schnittbuchstabe nach Wirkung.
"""

import hashlib
from collections import Counter
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import Callable
import json
import math
import time
from pathlib import Path

import win32com.client.dynamic

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.messen import oeffne
from swki.pruefung.schleife import lies_laeufe
from swki.spec.freigabe import funktionen_veraltet, pruefe_freigabe
from swki.spec.laden import lade_spec
from swki.verbindung import byref_long, callout_leer, r8_array, verbinde
from swki.zeichnung import anforderungen_setzen as anf
from swki.zeichnung.angaben import (HINWEIS_ABSTAENDE_MM, HINWEIS_ABSTAND_QUER_MM, HINWEIS_ABSTAND_ZEILE_MM,
                                    HINWEIS_RICHTUNGEN_GRAD, _enthalten, hinweis_lagen, hinweis_lagen_bewertet)
from swki.zeichnung.ansichten import (Ansicht, achsvektor, blickachsen, hinweise, vorzugsansichten,
                                     waehle_ansichten, weitere_rollen)
from swki.zeichnung.bemassen import EINZELHEIT_MIN, MASSABSTAND_M, bemasse, kurzname, ordne_masse_an, setze_neu
from swki.zeichnung.blatt import FORMATE, SAMMEL_ZEILE_MM, SCHRIFTFELD_MM, zeichenfeld
from swki.zeichnung.lesbarkeit import Befund, _schneidet, _ueberlappt, ausserhalb, pruefe_pdf, texte
from swki.zeichnung.reihen import ABSTAND_MM, LinMass, radius_zahl_frei, reihen, seite
from swki.zeichnung.layout import anordnen, einzelheit_passt
from swki.zeichnung.massplan import Mass, massplan, massplan_meldungen
from swki.zeichnung.toleranzangaben import sammelangaben
from swki.zeichnung.mittellinien import bezugspunkt, linien, ohne_kante
from swki.zeichnung.zuordnung import max_je_ansicht

NAEHE_EIGENER_TEXT_MM = 4.0  # PDF-Text gehört zum Hinweis/zur Anmerkung gleichen Wortlauts, wenn so nah am Rechteck
NAEHE_MM = 25.0  # Befund gehört zur nächsten Maßzahl in diesem Umkreis (Live 18.11.: Kennbuchstabe „A“ auf der Maßlinie, Zahl 18 mm weg)

SW_DEFAULT_TEMPLATE_DRAWING = 10            # swUserPreferenceStringValue_e
SW_DWG_TEMPLATE_CUSTOM = 12                 # swDwgTemplates_e
PAPIER = {"A4": 7, "A4quer": 6, "A3quer": 8}  # swDwgPaperSizes_e (A4 hoch = A4sizeVertical)
AUTO_MITTELLINIEN = (189, 190, 308)         # swDetailingAutoInsertCenterMarks, …CenterLines, …CenterMarksForHoles
# Nutzer 18.11.2026: keine Mittelpunktkreuze an Taschenecken – …CenterMarksForFillets, …ForSlots ausdrücklich aus
# (Vorlagenwert war an; SolidWorks setzt die Marken beim Anlegen einer Einzelheit in allen Ansichten neu)
KEINE_MARKEN = (309, 402)
SAVE_SILENT = 1                             # swSaveAsOptions_Silent
EIGENSCHAFT_TEXT = 30                       # swCustomInfoType_e.swCustomInfoText
EIGENSCHAFT_ERSETZEN = 2                    # swCustomPropertyAddOption_e.swCustomPropertyReplaceValue
ABSTAND_PROBE_M = 0.12                      # Probeplatzierung vor der Anordnung
DETAIL_STANDARD, DETAIL_PROFIL = 0, 0        # swDetViewStyle_e.swDetViewSTANDARD, swDetCircleShowType_e.swDetCirclePROFILE
EINZELHEIT_RAND_MM = 2.0                     # Rand des Einzelheit-Rechtecks um die Merkmalskanten (Blatt-mm)
KANTE_SICHTBAR = 1                           # swViewEntityType_e.swViewEntityType_Edge
RADIAL = 5                                   # swDimensionType_e.swRadialDimension
HILFSLINIE_LUECKE_MM = 1.0                   # Lücke zwischen Bezug und Hilfslinie (Live: Ursprung 223,0, Hilfslinie ab 222,0)
MITTELLINIE_UEBERSTAND_MM = 3.0              # Mittellinie so weit über den Körper hinaus
MITTENBEZUG = ("ursprung", "mitte")          # Maßprotokoll: Bezüge, die eine Mittellinie brauchen
RADIUS_ABSTAND_MM = 8.0                      # Zahl eines Radiusmaßes so weit hinter dem Bogen (Blatt-mm)
ZEICHENBREITE_MM = 2.6                       # geschätzte Breite eines Zeichens der Maßzahl (Live: „200,00“ 16,8 mm)
# Hinweis (Bohrungsangabe) vor dem Vermessen am PDF; Live 19.11. (Spannplatte): „Senkung Ø6 × 90°“ 39,8 mm breit,
# zwei Zeilen 10,9 mm hoch, Oberkante 1,4 mm über `IAnnotation.GetPosition`
HINWEIS_ZEICHEN_MM, HINWEIS_ZEILE_MM, HINWEIS_OBERKANTE_MM = 2.5, 5.5, 1.4
HINWEIS_ANSATZ_GRAD = 30.0                   # weicht der Ansatz am Kreis mehr ab, wird der Hinweis neu angehängt
# Beschriftung der Einzelheit „EINZELHEIT B“ statt „DETAIL B“ (Spike Stufe 3): swDetailingDetailViewLabels_PerStandard
# (Toggle) aus, …_Name (Integer) = swDetailingViewLabelsName_custom, …_CustomName (String)
EINZELHEIT_NORM, EINZELHEIT_NAME, NAME_EIGEN, EINZELHEIT_TEXT = 240, 241, 3, 81
EINZELHEIT_OBEN = 337                        # swDetailingDetailViewLabels_AboveView (Live 19.11.: unter der Ansicht lag
#                                              die Beschriftung auf der Maßreihe darunter)
# Stufe 4: Rauheitstext so hoch wie Hinweise (swUserPreferenceTextFormat_e: Note = 0, SurfaceFinish = 5; Live 27.11.:
# die Vorlage hat 6,35 mm, „Ra 0,8“ wurde so breit wie eine Maßreihe)
TEXT_HINWEIS, TEXT_RAUHEIT = 0, 5
SF_NORM, SF_NORM_1302_2002 = 629, 1          # swDetailingSFSymbolStandard / …_1302_2002 (Vorlage: 2 = ISO 21920-1)
DOKUMENTART = "Einzelteilzeichnung"           # Schriftfeld (Z1.4 Entscheidung 3)


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


def _laengsschnitt(drw, stirn, buchstabe: str = "A"):
    """Schnittlinie senkrecht durch die Mitte der ungedrehten Stirnansicht, Schnitt (A-A, ohne Bezugsbuchstaben der
    nächste, `schnitt_buchstabe`) links daneben (Spike Z1.0)."""
    x0, y0, x1, y1 = (v / 1000 for v in _umriss_mm(stirn))
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    _waehle_ansicht(drw, stirn)
    oben, unten = _in_ansicht(stirn, xm, y1 + 0.005), _in_ansicht(stirn, xm, y0 - 0.005)
    _ruf(drw, "SketchManager").CreateLine(oben[0], oben[1], 0, unten[0], unten[1], 0)
    return drw.CreateSectionViewAt5(x0 - ABSTAND_PROBE_M, ym, 0, buchstabe, 0, None, 0)


def _fraesschnitt(drw, mu, haupt, durch: tuple[str, ...], buchstabe: str = "A"):
    """Nutzer 19.11.2026: Taschentiefe in der unteren Ansicht ohne sichtbaren Bezug → untere Ansicht als Schnitt A-A.
    Schnittlinie waagrecht durch die Mitte des ersten Merkmals aus `durch` (seine sichtbaren Kanten in der Hauptansicht),
    über den Umriss hinaus; Schnitt darunter, Blick von oben wie die Projektion nach Methode 1
    (spikes/z1_diag_frässchnitt.py: ohne `ChangeDirection` liegt die Taschenöffnung unten wie in der Projektion)."""
    kanten = _kanten(mu, haupt)
    punkte = next(([p for a, e, _ in kanten[m] for p in (a, e)] for m in durch if kanten.get(m)), None)
    if not punkte:
        return None
    ym = (min(p[1] for p in punkte) + max(p[1] for p in punkte)) / 2
    x0, y0, x1, _ = _umriss_mm(haupt)
    _waehle_ansicht(drw, haupt)
    a, b = _in_ansicht(haupt, (x0 - 5) / 1000, ym / 1000), _in_ansicht(haupt, (x1 + 5) / 1000, ym / 1000)
    _ruf(drw, "SketchManager").CreateLine(a[0], a[1], 0, b[0], b[1], 0)
    return drw.CreateSectionViewAt5((x0 + x1) / 2000, y0 / 1000 - ABSTAND_PROBE_M, 0, buchstabe, 0, None, 0)


def _in_ansicht(view, x_m: float, y_m: float) -> tuple[float, float]:
    """Blattpunkt (m) → Skizzenkoordinaten der aktiven, ungedrehten Ansicht: relativ zum Ansichtsursprung
    (`IView.Position`) und im Modellmaßstab (÷ `IView.ScaleDecimal`). Live Z1.3: Blattkoordinaten direkt landen um
    Lage und Maßstab versetzt (Spike Z1.0 hatte das nicht bemerkt)."""
    px, py = list(_ruf(view, "Position"))[:2]
    s = _ruf(view, "ScaleDecimal")
    return ((x_m - px) / s, (y_m - py) / s)


def _kanten(mu, view) -> dict[str, list[tuple]]:
    """Sichtbare Kanten der Ansicht je Feature (über ihre Flächen, `IFace2.GetFeature`) in Blatt-mm:
    (Anfang, Ende, Bogen) mit Bogen = (Mitte, Radius in Modell-mm) oder None (spikes/z1_diag_merkmalskanten.py;
    `IView.ModelToViewTransform` liefert Blattkoordinaten samt Maßstab)."""
    t = _ruf(view, "ModelToViewTransform")

    def blatt(p_m):
        q = mu.CreatePoint(r8_array(list(p_m))).MultiplyTransform(t).ArrayData
        return q[0] * 1000, q[1] * 1000

    je: dict[str, list[tuple]] = {}
    for k in list(view.GetVisibleEntities2(callout_leer(), KANTE_SICHTBAR) or ()):
        try:
            cp, c = _ruf(k, "GetCurveParams3"), _ruf(k, "GetCurve")
            a, e = blatt(_ruf(cp, "StartPoint")), blatt(_ruf(cp, "EndPoint"))
            bogen = None
            if _ruf(c, "IsCircle"):
                cx, cy, cz, *_, r = list(_ruf(c, "CircleParams"))
                bogen = (blatt((cx, cy, cz)), r * 1000)
            namen = {_ruf(_ruf(fl, "GetFeature"), "Name") for fl in list(_ruf(k, "GetTwoAdjacentFaces2") or ())
                     if fl is not None}
        except Exception:  # noqa: BLE001 – COM: Kante ohne Kurve/Flächen überspringen
            continue
        for n in namen:
            je.setdefault(n, []).append((a, e, bogen))
    return je


def _strecken(kanten: dict, massstab: float) -> list[tuple]:
    """Kanten als Strecken in Blatt-mm; Bögen (kürzerer Bogen) und Vollkreise in 12 Stücken."""
    aus = []
    for liste in kanten.values():
        for a, e, bogen in liste:
            if not bogen:
                aus.append((a, e))
                continue
            m = bogen[0]
            voll = math.dist(a, e) < 1e-6
            r = bogen[1] * massstab if voll else math.dist(a, m)
            w0 = math.atan2(a[1] - m[1], a[0] - m[0])
            spanne = 2 * math.pi if voll else (math.atan2(e[1] - m[1], e[0] - m[0]) - w0 + math.pi) % (2 * math.pi) - math.pi
            punkte = [(m[0] + r * math.cos(w0 + spanne * i / 12), m[1] + r * math.sin(w0 + spanne * i / 12))
                      for i in range(13)]
            aus += list(zip(punkte, punkte[1:]))
    return aus


def _rechteck_strecken(r: tuple) -> list[tuple]:
    ecken = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    return list(zip(ecken, ecken[1:] + ecken[:1]))


def _radien_setzen(mu, views: dict, rahmen: dict | None = None, mittel: dict | None = None,
                   extra: list[tuple] | None = None) -> None:
    """Nutzer 18.11.2026: Pfeil von R4 zeigte auf das Mittelpunktkreuz. Zahl jedes Radiusmaßes außen auf einen Strahl
    durch seinen Bogen, frei von sichtbaren Kanten und vom Rahmen einer Einzelheit (`rahmen`: Rolle → Rechteck)
    (`reihen.radius_zahl_frei`); den Bogen findet sein Mittelpunkt – Ende der letzten Linie aus `IDisplayData`
    (spikes/z1_diag_merkmalskanten.py). `extra`: Strecken auf dem ganzen Blatt (Hinweistexte und ihre Hinweislinien)."""
    for rolle, v in views.items():
        dds = [dd for dd in list(_ruf(v, "GetDisplayDimensions") or ()) if _ruf(dd, "Type2") == RADIAL]
        if not dds:
            continue
        kanten = _kanten(mu, v)
        boegen = [(a, e, b) for liste in kanten.values() for a, e, b in liste if b]
        hindernisse = _strecken(kanten, _ruf(v, "ScaleDecimal"))
        for anders in list(_ruf(v, "GetDisplayDimensions") or ()):  # Maß- und Hilfslinien der übrigen Maße
            if _ruf(anders, "Type2") == RADIAL:
                continue
            daten = _ruf(anders, "GetDisplayData")
            for i in range(_ruf(daten, "GetLineCount")):
                linie = list(daten.GetLineAtIndex3(i))
                hindernisse.append(((linie[4] * 1000, linie[5] * 1000), (linie[7] * 1000, linie[8] * 1000)))
        if (rahmen or {}).get(rolle):
            hindernisse += _rechteck_strecken(rahmen[rolle])
        hindernisse += (mittel or {}).get(rolle, [])
        hindernisse += extra or []
        for dd in dds:
            daten = _ruf(dd, "GetDisplayData")
            n = _ruf(daten, "GetLineCount")
            if n < 1:
                continue
            linie = list(daten.GetLineAtIndex3(n - 1))
            mitte = (linie[7] * 1000, linie[8] * 1000)
            text = "".join(str(daten.GetTextAtIndex(i)) for i in range(_ruf(daten, "GetTextCount"))).strip()
            for a, e, (m, _) in boegen:
                if math.dist(m, mitte) < 0.3:
                    lage = radius_zahl_frei(m, a, e, RADIUS_ABSTAND_MM, hindernisse, ZEICHENBREITE_MM * len(text))
                    if lage:
                        _ruf(dd, "GetAnnotation").SetPosition2(lage[0] / 1000, lage[1] / 1000, 0)
                        break


def _bezuege(dd) -> tuple[str, list[tuple[float, float]]] | None:
    """Richtung (h: Maßlinie waagrecht) und Bezugspunkte eines linearen Maßes in Blatt-mm: Anfang der beiden Hilfslinien
    aus `IDisplayData`, um die Lücke zum Bezug zurückgesetzt (`mittellinien.bezugspunkt`)."""
    if _ruf(dd, "Type2") not in LINEAR:
        return None
    daten = _ruf(dd, "GetDisplayData")
    if _ruf(daten, "GetLineCount") < 2:
        return None
    punkte, waagrecht = [], True
    for k in (0, 1):
        linie = list(daten.GetLineAtIndex3(k))
        a, e = (linie[4] * 1000, linie[5] * 1000), (linie[7] * 1000, linie[8] * 1000)
        waagrecht = abs(e[0] - a[0]) < abs(e[1] - a[1])  # Hilfslinie senkrecht → Maßlinie waagrecht
        punkte.append(bezugspunkt(a, e, HILFSLINIE_LUECKE_MM))
    return ("h" if waagrecht else "v"), punkte


def _einzelheit(drw, mu, views: dict, rolle: str, angebot: list[tuple[str, list[str]]], genutzt: list[str],
                gruppe: dict[str, str], mitten: set[str], buchstabe: str | None, bereich: dict, meldungen: list[str],
                sammel_mm: float = 0.0):
    """Einzelheit (Nutzer 18.11.2026: dichte Hauptansicht; „Details werden in der Regel vergrößert“). Je angebotenem
    Merkmal (meiste Maße zuerst): Rechteck um seine sichtbaren Kanten (`_kanten`, auch Unter-Features `<id>_…` und
    Merkmale, die zu ihm zählen, z. B. seine Verrundung); hinein dürfen nur Maße, deren beide Bezüge im Rechteck liegen
    und die keinen Mittenbezug haben (`mitten`; Nutzer 18.11.: 27/47/60 zeigten in der Einzelheit auf die Plattenmitte
    außerhalb). Das erste Merkmal mit `EINZELHEIT_MIN` solchen Maßen, das vergrößert aufs Blatt passt
    (`layout.einzelheit_passt` mit den Ansichten `genutzt`), wird als Profil skizziert (bleibt ausgewählt,
    spikes/z1_diag_einzelheit.py) und doppelt so groß angelegt. `bereich` bekommt Größe des Rechtecks und Versatz seiner
    Mitte von `IView.Position` in Modell-mm (Position einer Einzelheit = Modellpunkt der Elternansicht,
    spikes/z1_diag_einzelheit_lage.py). Liefert (Ansicht, Merkmal, Maßnamen) oder None."""
    if buchstabe is None:  # Runde E: alle Buchstaben vergeben
        _melde(meldungen, "EINZELHEIT_BUCHSTABE: kein freier Buchstabe – Einzelheit entfällt")
        return None
    eltern = views[rolle]
    kanten = _kanten(mu, eltern)
    ux0, uy0, ux1, uy1 = _umriss_mm(eltern)
    s, pos = _ruf(eltern, "ScaleDecimal"), [v * 1000 for v in list(_ruf(eltern, "Position"))[:2]]
    dds = list(_ruf(eltern, "GetDisplayDimensions") or ())
    for merkmal, namen in angebot:
        zu = {merkmal} | {m for m, g in gruppe.items() if g == merkmal}
        punkte = [p for n, liste in kanten.items() if n in zu or any(n.startswith(z + "_") for z in zu)
                  for a, e, _ in liste for p in (a, e)]
        if not punkte:
            continue
        x0 = max(min(p[0] for p in punkte) - EINZELHEIT_RAND_MM, ux0)
        y0 = max(min(p[1] for p in punkte) - EINZELHEIT_RAND_MM, uy0)
        x1 = min(max(p[0] for p in punkte) + EINZELHEIT_RAND_MM, ux1)
        y1 = min(max(p[1] for p in punkte) + EINZELHEIT_RAND_MM, uy1)

        def drin(p, x0=x0, y0=y0, x1=x1, y1=y1):
            return x0 - 0.5 <= p[0] <= x1 + 0.5 and y0 - 0.5 <= p[1] <= y1 + 0.5

        hinein = []
        for dd in dds:
            name = kurzname(dd)
            if name not in namen or name in mitten:
                continue
            if _ruf(dd, "Type2") == RADIAL:  # Radius: Mittelpunkt (Ende der letzten Linie) im Rahmen
                daten = _ruf(dd, "GetDisplayData")
                linie = list(daten.GetLineAtIndex3(_ruf(daten, "GetLineCount") - 1))
                if drin((linie[7] * 1000, linie[8] * 1000)):
                    hinein.append(name)
                continue
            b = _bezuege(dd)
            if b and all(drin(p) for p in b[1]):
                hinein.append(name)
        groesse = ((x1 - x0) / s, (y1 - y0) / s)
        if len(hinein) < EINZELHEIT_MIN:
            meldungen.append(f"EINZELHEIT_NICHT_FUER: {merkmal} – nur {len(hinein)} Maße mit beiden Bezügen im Rahmen")
            continue
        if not einzelheit_passt({r: _groesse_1zu1(views[r]) for r in genutzt}, groesse, sammel_mm):
            meldungen.append(f"EINZELHEIT_ZU_GROSS: {merkmal} ({groesse[0]:.0f} × {groesse[1]:.0f} mm) passt "
                             "vergrößert nicht aufs Blatt")
            continue
        _waehle_ansicht(drw, eltern)
        a, b = _in_ansicht(eltern, x0 / 1000, y0 / 1000), _in_ansicht(eltern, x1 / 1000, y1 / 1000)
        rechteck = list(_ruf(drw, "SketchManager").CreateCornerRectangle(a[0], a[1], 0, b[0], b[1], 0) or ())
        if len(rechteck) != 4 or _ruf(drw, "SelectionManager").GetSelectedObjectCount2(-1) < 4:
            return None
        bereich.update(groesse=groesse, versatz=(((x0 + x1) / 2 - pos[0]) / s, ((y0 + y1) / 2 - pos[1]) / s),
                       eltern=rolle)
        z = Fraction(2 * s).limit_denominator(100)
        det = drw.CreateDetailViewAt4(ux1 / 1000 + ABSTAND_PROBE_M, uy0 / 1000, 0, DETAIL_STANDARD, z.numerator,
                                      z.denominator, buchstabe, DETAIL_PROFIL, True, False, False, 5)
        if det is not None:
            meldungen += _buchstabe_pruefen(eltern, buchstabe)
        return (det, merkmal, hinein) if det is not None else None
    return None


def _mittellinien(drw, mu, views: dict, plan: list) -> tuple[dict[str, list[tuple]], list[str]]:
    """Nutzer 18.11.2026: Maße ab Teilmitte brauchen eine gezeichnete Mittellinie. Je Ansicht: Bezugspunkte ohne Kante
    (`mittellinien.ohne_kante`) von Maßen mit `bezug` ursprung/mitte → Mittellinie über den Körper
    (`ISketchManager.CreateCenterLine`, spikes/z1_diag_mittellinie.py). Andere Maße mit Bezug ohne Kante (z. B. Tiefe
    auf einen verdeckten Boden) werden gemeldet, nicht verziert. Liefert die Linien je Rolle (Hindernisse für
    Radiuszahlen) und Meldungen."""
    mitten = {m.name for m in plan if m.quelle == "modell" and m.bezug in MITTENBEZUG}
    alle = {m.name for m in plan if m.quelle == "modell"}
    je, meldungen = {}, []
    for rolle, v in views.items():
        kanten = _kanten(mu, v)
        strecken = _strecken(kanten, _ruf(v, "ScaleDecimal"))
        if not strecken:
            continue
        kreise = [(b[0], b[1] * _ruf(v, "ScaleDecimal")) for liste in kanten.values() for _, _, b in liste if b]
        gerade = [(a, e) for liste in kanten.values() for a, e, b in liste if not b]
        gebogen = _strecken({k: [x for x in liste if x[2]] for k, liste in kanten.items()}, _ruf(v, "ScaleDecimal"))
        xs = [p[0] for s in strecken for p in s]
        ys = [p[1] for s in strecken for p in s]
        bezuege = []
        for dd in list(_ruf(v, "GetDisplayDimensions") or ()):
            name, b = kurzname(dd), _bezuege(dd)
            if name not in alle or not b:
                continue
            frei = [(k, p) for k, p in enumerate(b[1]) if ohne_kante(p, gerade, kreise, gebogen, b[0])]
            if name in mitten:
                bezuege += [(b[0], p) for _, p in frei]
                for k, _ in frei:  # Hilfslinie an der Mitte als Mittellinie (Live 19.11.: lag als Volllinie auf ihr)
                    if not dd.SetExtensionLineAsCenterline(k, True):
                        meldungen.append(f"HILFSLINIE_NICHT_MITTELLINIE: {name} in {rolle}")
            elif frei:
                meldungen.append(f"BEZUG_OHNE_KANTE: {name} in {rolle} setzt an einem Punkt ohne sichtbare Kante an")
        linien_rolle = linien(bezuege, (min(xs), min(ys), max(xs), max(ys)), MITTELLINIE_UEBERSTAND_MM)
        if not linien_rolle:
            continue
        _waehle_ansicht(drw, v)
        sk = _ruf(drw, "SketchManager")
        for (ax, ay), (bx, by) in linien_rolle:
            a, b = _in_ansicht(v, ax / 1000, ay / 1000), _in_ansicht(v, bx / 1000, by / 1000)
            if sk.CreateCenterLine(a[0], a[1], 0, b[0], b[1], 0) is None:
                meldungen.append(f"MITTELLINIE_NICHT_GEZEICHNET: {rolle} ({ax:.0f}, {ay:.0f})–({bx:.0f}, {by:.0f})")
        drw.ClearSelection2(True)
        je[rolle] = linien_rolle
    return je, meldungen


EINZELHEIT_BUCHSTABEN = "ZYXWVUTSRPNMLKJHGFEDCBA"  # ab Z rückwärts, ohne I, O, Q (recherche.md: TUM, Beleg B)
SCHNITT_BUCHSTABEN = EINZELHEIT_BUCHSTABEN[::-1]   # ab A vorwärts


def einzelheit_buchstabe(i: int, vergeben: set[str] | frozenset = frozenset()) -> str | None:
    """Buchstabe der `i`-ten Einzelheit (0 = erste): Einzelheiten vom Alphabetende (Z, Y, X …), Schnitte vom Anfang
    (A-A, B-B …; docs/zeichnungsableitung/recherche.md, TUM Zeichnungserstellung, Beleg B). Ohne I, O, Q und ohne
    `vergeben` (Bezugsbuchstaben, Schnitte; Runde D: die Einzelheit hieß „B“ wie Bezug B). None, wenn keiner frei ist
    (Runde E: Meldung beim Aufrufer statt IndexError)."""
    frei = [b for b in EINZELHEIT_BUCHSTABEN if b not in vergeben]
    return frei[i] if 0 <= i < len(frei) else None


def schnitt_buchstabe(i: int, vergeben: set[str] | frozenset = frozenset()) -> str | None:
    """Buchstabe des `i`-ten Schnitts: ab A vorwärts, ohne I, O, Q und ohne `vergeben` (Bezugsbuchstaben; Runde E: der
    Schnitt hieß fest „A“ wie Bezug A der SpannplatteZ). None, wenn keiner frei ist."""
    frei = [b for b in SCHNITT_BUCHSTABEN if b not in vergeben]
    return frei[i] if 0 <= i < len(frei) else None


def _schnitt_pruefen(view, buchstabe: str) -> list[str]:
    """Nach Wirkung: trägt die Schnittansicht den verlangten Buchstaben (`IView.GetSection` → `IDrSection.GetLabel`)?"""
    try:
        ist = str(_ruf(_ruf(view, "GetSection"), "GetLabel"))
    except Exception:  # noqa: BLE001 – COM
        return [f"SCHNITT_BUCHSTABE: „{buchstabe}“ verlangt, Schnittbezeichnung nicht lesbar"]
    return [] if ist == buchstabe else [f"SCHNITT_BUCHSTABE: „{buchstabe}“ verlangt, Schnitt trägt „{ist}“"]


def _buchstabe_pruefen(eltern, buchstabe: str) -> list[str]:
    """Nach Wirkung: trägt ein Einzelheitenkreis der Elternansicht den Buchstaben (`IDetailCircle.GetLabel`)?"""
    labels = [str(_ruf(k, "GetLabel")) for k in list(_ruf(eltern, "GetDetailCircles") or ())]
    if buchstabe in labels:
        return []
    ist = ", ".join(f"„{b}“" for b in labels) or "keinen"
    return [f"EINZELHEIT_BUCHSTABE: „{buchstabe}“ verlangt, Einzelheitenkreis trägt {ist}"]


def _kennbuchstabe(eltern, rahmen: tuple, buchstabe: str) -> tuple[str, Callable[[], bool]] | None:
    """Kennbuchstabe der Einzelheit um den Rahmen in der Elternansicht weitersetzen: oben links, oben rechts, unten
    links, unten rechts außen. `IDetailCircle.Get/SetLabelPosition` in Blatt-m; SolidWorks rückt den Buchstaben selbst
    etwas vom Rahmen ab (spikes/z1_diag_detailbuchstabe.py)."""
    kreise = list(_ruf(eltern, "GetDetailCircles") or ())
    if not kreise:
        return None
    x0, y0, x1, y1 = rahmen
    lagen = iter([(x0 - 4, y1 + 2), (x1 + 4, y1 + 2), (x0 - 4, y0 - 6), (x1 + 4, y0 - 6)])

    def weiter() -> bool:
        lage = next(lagen, None)
        if lage is None:
            return False
        kreise[0].SetLabelPosition(lage[0] / 1000, lage[1] / 1000)
        return True

    return buchstabe, weiter


def _planzahlen(plan: list) -> tuple[int, int]:
    """Ruling A (Stufe 3): Maße (Quelle modell/neu) und Angaben getrennt zählen."""
    return (sum(1 for m in plan if m.quelle in ("modell", "neu")), sum(1 for m in plan if m.quelle == "angabe"))


@dataclass
class _Hinweis:
    """Gesetzte Bohrungsangabe: Hinweis mit Hinweislinie an der Kreiskante `kreise[instanz]` (Kante, (Mitte, Radius)
    in Blatt-mm) in Ansicht `rolle`; `kreise` sind alle Bohrungen des Bohrbilds in dieser Ansicht."""
    merkmal: str
    zeilen: tuple[str, ...]
    ann: object
    rolle: str
    kreise: list
    instanz: int
    umriss: tuple                  # Körper in der Ansicht (Blatt-mm)
    groesse: tuple[float, float]   # Textrechteck (Blatt-mm; geschätzt, dann am PDF vermessen)
    versatz: tuple[float, float]   # Mitte des Textrechtecks − Lage der Annotation (Blatt-mm)
    lage: tuple[float, float] | None = None
    verworfen: list = field(default_factory=list)
    vermessen: bool = False
    text: str = ""
    view: object = None
    winkel: float | None = None    # Ansatz der Hinweislinie am Kreis (Grad); None: wo SelectEntity ihn hinlegt
    punktwahl: bool = True         # False: Wahl am Kreispunkt gelang nicht – nicht jede Runde neu versuchen
    # Review Task 5 (I1): Textformen (Hinweistext, Zeilen im PDF); [0] zweizeilig, [1] dreizeilig (Umbruch statt „ – “)
    varianten: list = field(default_factory=list)
    variante: int = 0
    fixiert: tuple | None = None   # (Bohrung, Lage, Variante) der besten Runde

    @property
    def kreis(self) -> tuple:
        return self.kreise[self.instanz][1]

    def stand(self) -> tuple:
        return (self.instanz, self.lage, self.variante)

    def groesse_von(self, v: int) -> tuple[float, float]:
        """Größe der Textform `v`: die heutige gemessen/geschätzt, eine andere aus Zeichen- und Zeilenzahl umgerechnet."""
        if v == self.variante or not self.varianten:
            return self.groesse
        heute, andere = self.varianten[self.variante][1], self.varianten[v][1]
        return (self.groesse[0] * max(map(len, andere)) / max(map(len, heute)), self.groesse[1] * len(andere) / len(heute))

    def rechteck(self) -> tuple | None:
        if self.lage is None:
            return None
        (x, y), (b, h) = self.lage, self.groesse
        return (x - b / 2, y - h / 2, x + b / 2, y + h / 2)

    def hinweislinie(self) -> tuple | None:
        return None if self.lage is None else _hinweislinie(self.kreis, self.lage, self.groesse, len(self.zeilen))

    def verwerfen(self) -> bool:
        """PDF-Befund: heutige Lage verwerfen; False, wenn alle Lagen verworfen sind."""
        if self.lage is not None and self.lage not in self.verworfen:
            self.verworfen.append(self.lage)
        return len(self.verworfen) < len(HINWEIS_RICHTUNGEN_GRAD) * len(HINWEIS_ABSTAENDE_MM) * len(self.kreise)


def _hinweislinie(kreis: tuple, lage: tuple, groesse: tuple, zeilen: int) -> tuple:
    """Hinweislinie vom Kreis (radial) zur nahen Seite der ersten Zeile – dort setzt SolidWorks an (Live 19.11.)."""
    (mx, my), r = kreis
    ziel = (lage[0] - groesse[0] / 2 if lage[0] > mx else lage[0] + groesse[0] / 2,
            lage[1] + groesse[1] / 2 - groesse[1] / zeilen / 2)
    d = math.dist(ziel, (mx, my)) or 1.0
    return ((mx + (ziel[0] - mx) * r / d, my + (ziel[1] - my) * r / d), ziel)


def _ansatz(kreis: tuple, lage: tuple, groesse: tuple, zeilen: int) -> float:
    """Winkel (Grad) des Kreispunkts, an dem die Hinweislinie zum Text hin ansetzt."""
    (a, _) = _hinweislinie(kreis, lage, groesse, zeilen)
    return math.degrees(math.atan2(a[1] - kreis[0][1], a[0] - kreis[0][0]))


def _hinweis_zu(b, hinweise: list) -> "_Hinweis | None":
    """Hinweis, zu dem ein PDF-Befund gehört (Text oder anderer Text eine seiner Zeilen; bei mehreren der nächste)."""
    treffer = [h for h in hinweise if h.lage is not None and (b.text in h.zeilen or b.anderes in h.zeilen)
               and (not hasattr(h, "nahe") or h.nahe(b.rechteck_mm))]  # Anmerkung: Text allein ist mehrdeutig
    if not treffer and b.art == "linie_durch_text":  # fremder Text, von der Hinweislinie einer Anmerkung gekreuzt
        treffer = [h for h in hinweise if hasattr(h, "nahe") and h.lage is not None
                   and _schneidet(*h.hinweislinie(), b.rechteck_mm)]
    if not treffer:
        return None
    if b.anderes and all(b.text in h.zeilen and b.anderes in h.zeilen for h in treffer):
        return None  # zwei Zeilen desselben Hinweises: Zeilenabstand, kein Befund für die Lage
    mx, my = (b.rechteck_mm[0] + b.rechteck_mm[2]) / 2, (b.rechteck_mm[1] + b.rechteck_mm[3]) / 2
    return min(treffer, key=lambda h: math.dist(h.lage, (mx, my)))


def _hinweise_vermessen(hinweise: list, pdf_texte: list[tuple[str, tuple]]) -> list:
    """Größe und Versatz noch ungemessener Hinweise aus ihren Zeilen im PDF (je Zeile die nächste gleichlautende;
    Vereinigung der Rechtecke) und der Lage der Annotation. Liefert die eben vermessenen Hinweise: ihre Lage galt mit
    der geschätzten Größe – verworfene Lagen zählen nicht mehr, `_hinweise_legen` wählt neu."""
    neu = []
    for h in hinweise:
        if h.vermessen or h.lage is None:
            continue
        rechtecke = []
        for zeile in h.zeilen:
            kandidaten = [r for t, r in pdf_texte if t == zeile]
            if kandidaten:
                rechtecke.append(min(kandidaten, key=lambda r: math.dist(h.lage, ((r[0] + r[2]) / 2,
                                                                                    (r[1] + r[3]) / 2))))
        h.vermessen = True
        if len(rechtecke) != len(h.zeilen):
            continue  # Zeile im PDF nicht gefunden (anders umbrochen): Schätzung bleibt
        x0, y0 = min(r[0] for r in rechtecke), min(r[1] for r in rechtecke)
        x1, y1 = max(r[2] for r in rechtecke), max(r[3] for r in rechtecke)
        px, py = (c * 1000 for c in list(_ruf(h.ann, "GetPosition"))[:2])
        h.groesse, h.versatz = (x1 - x0, y1 - y0), ((x0 + x1) / 2 - px, (y0 + y1) / 2 - py)
        h.verworfen.clear()
        neu.append(h)
    return neu


def _enthaltene(spec: dict, plan: list, quellen: tuple[str, ...] = ("angabe",)) -> dict[str, set[str]]:
    """Je Angabe (bzw. Eintrag aus `quellen`) die Features, deren Flächen die Kanten tragen dürfen: das Merkmal, seine
    Muster und Spiegel (Spike Stufe 3: Kanten von Musterinstanzen gehören zum Muster-Feature; Nachbesserung C: Ra 1,6
    darf auch an den gespiegelten Taschenboden)."""
    return {m.merkmal: {m.merkmal} | {f["id"] for f in _enthalten(spec, m.merkmal)}
            for m in plan if m.quelle in quellen}


def _fremde_texte(pdf_texte: list[tuple[str, tuple]], hinweise: list) -> list[tuple]:
    """Textrechtecke des PDFs, die zu keinem Hinweis bzw. keiner Anmerkung gehören. Eigen ist ein Text nur in der Nähe
    seines Hinweises (Nachbesserung C: Bezug „A“ machte sonst die Kennbuchstaben „A“ der Schnittlinie unsichtbar, der
    Stifthinweis legte sich darauf) und nur, wenn seine Wörter in den Zeilen des Hinweises stehen (Runde D, I3: pymupdf
    liefert Rahmenzellen getrennt oder anders umbrochen; Wörter ohne Buchstaben und Ziffern – Symbolzeichen – zählen
    nicht).
    Runde E (I-2): Die eigenen Zeilen werden verbraucht – jede eigene Zeile bzw. jedes eigene Wort deckt höchstens
    einen PDF-Text, den nächstgelegenen (Abstand zum Rechteck, dann zur Mitte), und jeder PDF-Text gehört höchstens
    einem Hinweis. Erst ganze Zeilen (wortgleich; das geschätzte Rechteck eines unvermessenen Hinweises entscheidet
    zwischen „Fase 0,5 × 45°“ und dem Fasenmaß „0,5 × 45°“ darunter nicht sicher), dann die Wörter der übrigen Zeilen
    als Multimenge (getrennt gelieferte Rahmenzellen). Sonst schluckte „0,05 A“ das „A“ der Schnittlinie daneben."""
    def woerter(text: str) -> Counter:
        return Counter(w for w in text.split() if any(c.isalnum() for c in w))

    n = NAEHE_EIGENER_TEXT_MM
    eigene = [(h.rechteck(), [" ".join(z.split()) for z in h.zeilen]) for h in hinweise]

    def nahe(r, q) -> bool:
        return r[0] < q[2] + n and q[0] - n < r[2] and r[1] < q[3] + n and q[1] - n < r[3]

    def abstand(r, q) -> tuple[float, float]:
        dx, dy = max(q[0] - r[2], r[0] - q[2], 0.0), max(q[1] - r[3], r[1] - q[3], 0.0)
        return (math.hypot(dx, dy), math.dist(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), ((q[0] + q[2]) / 2,
                                                                                         (q[1] + q[3]) / 2)))

    paare = sorted((abstand(r, q), i, j) for i, (_, r) in enumerate(pdf_texte)
                   for j, (q, _) in enumerate(eigene) if q is not None and nahe(r, q))
    vergeben: set[int] = set()
    zeilen_rest = [Counter(z) for _, z in eigene]
    for _, i, j in paare:  # ganze Zeilen
        text = " ".join(pdf_texte[i][0].split())
        if i not in vergeben and zeilen_rest[j][text] > 0:
            zeilen_rest[j][text] -= 1
            vergeben.add(i)
    worte_rest = [Counter() for _ in eigene]
    for j, rest in enumerate(zeilen_rest):
        for z, k in rest.items():
            for _ in range(k):
                worte_rest[j] += woerter(z)
    for _, i, j in paare:  # Wörter der übrigen Zeilen; Texte ohne Wörter (Symbolzeichen) sind bei Nähe eigen
        if i in vergeben:
            continue
        w = woerter(pdf_texte[i][0])
        if w <= worte_rest[j]:
            worte_rest[j] -= w
            vergeben.add(i)
    return [r for i, (_, r) in enumerate(pdf_texte) if i not in vergeben]


def _kreiskanten(mu, view, namen: set[str]) -> list[tuple]:
    """Sichtbare Kreiskanten der Ansicht, deren Nachbarfläche zu einem Feature aus `namen` gehört (auch Unter-Features
    `<name>_…`): je Kreismitte die äußerste als (Kante, Mitte Blatt-mm, Radius Blatt-mm)."""
    t = _ruf(view, "ModelToViewTransform")
    s = _ruf(view, "ScaleDecimal")
    je: dict[tuple, tuple] = {}
    for k in list(view.GetVisibleEntities2(callout_leer(), KANTE_SICHTBAR) or ()):
        try:
            c = _ruf(k, "GetCurve")
            if not _ruf(c, "IsCircle"):
                continue
            feats = {_ruf(_ruf(fl, "GetFeature"), "Name") for fl in list(_ruf(k, "GetTwoAdjacentFaces2") or ())
                     if fl is not None}
            if not any(n in namen or any(n.startswith(z + "_") for z in namen) for n in feats):
                continue
            cx, cy, cz, *_, r = list(_ruf(c, "CircleParams"))
            q = mu.CreatePoint(r8_array([cx, cy, cz])).MultiplyTransform(t).ArrayData
        except Exception:  # noqa: BLE001 – COM: Kante ohne Kurve/Flächen überspringen
            continue
        mitte, radius = (q[0] * 1000, q[1] * 1000), r * 1000 * s
        schluessel = (round(mitte[0], 1), round(mitte[1], 1))
        if schluessel not in je or radius > je[schluessel][2]:
            je[schluessel] = (k, mitte, radius)
    return list(je.values())


def _koerper(strecken: list[tuple]) -> tuple[float, float, float, float]:
    xs = [p[0] for s in strecken for p in s]
    ys = [p[1] for s in strecken for p in s]
    return (min(xs), min(ys), max(xs), max(ys))


def _angaben_setzen(drw, mu, views: dict, plan: list, achsen: dict[str, int],
                    enthalten: dict[str, set[str]] | None = None, hinweise: list | None = None) -> list[str]:
    """Bohrungsangaben (Plan-Einträge `quelle: angabe`) als Hinweis mit Hinweislinie (Spike Stufe 3: Kreiskante wählen
    – am Kreispunkt zum Text hin, sonst `IView.SelectEntity` –, dann `InsertNote`: die Hinweislinie hängt an der
    Auswahl). Je Angabe die erste Ansicht, deren Blickachse gleich `Mass.achse` ist und die eine Kreiskante des Merkmals
    oder seines Musters/Spiegels zeigt (`enthalten`); unter mehreren Bohrungen die mit der besten freien Lage
    (`hinweis_lagen_bewertet`). Die Größe des Texts ist zuerst geschätzt und wird nach einem PDF-Befund am PDF vermessen
    (`_hinweise_vermessen`; Live 19.11.: `INote.GetExtent` lieferte 53 × 13,5 mm samt Hinweislinie für 40 × 11 mm
    Text); die Lage setzt später `_hinweise_legen`. Gesetzte Hinweise kommen nach `hinweise`. Liefert Meldungen (`ANGABE_OHNE_ANSICHT`, `ANGABE_NICHT_GESETZT`, `ANGABE_OHNE_HINWEISLINIE`)."""
    meldungen, masslinien = [], None
    for m in (m for m in plan if m.quelle == "angabe"):
        namen = (enthalten or {}).get(m.merkmal) or {m.merkmal}
        notiz, zeilen = _notiztext(m.text or "")
        schaetzung = (max(len(z) for z in zeilen) * HINWEIS_ZEICHEN_MM, len(zeilen) * HINWEIS_ZEILE_MM)
        wahl = None
        for rolle, v in views.items():
            if m.achse is None or achsen.get(rolle) != m.achse:
                continue
            kreise = _kreiskanten(mu, v, namen)
            if not kreise:
                continue
            strecken = _strecken(_kanten(mu, v), _ruf(v, "ScaleDecimal"))
            umriss = _koerper(strecken)
            if masslinien is None:  # Seiten der Maße stehen schon, die Reihen rücken später nur nach außen
                masslinien = _masslinien(views)
            kreise = [(kante, (mitte, r)) for kante, mitte, r in kreise]
            wahl = min(((*hinweis_lagen_bewertet(kreis, umriss, strecken + masslinien, schaetzung)[0], i, rolle, v,
                         kreise, umriss) for i, (_, kreis) in enumerate(kreise)), key=lambda w: (w[0], w[2]))
            break
        if wahl is None:
            meldungen.append(f"ANGABE_OHNE_ANSICHT: {m.merkmal}")
            continue
        _, lage, i, rolle, v, kreise, umriss = wahl
        gesetzt = _hinweis_einfuegen(drw, v, kreise[i][0], notiz, kreise[i][1],
                                     _ansatz(kreise[i][1], lage, schaetzung, len(zeilen)))
        if gesetzt is None:
            meldungen.append(f"ANGABE_NICHT_GESETZT: {m.merkmal} – Kreiskante in {rolle} nicht auswählbar oder "
                             "InsertNote abgelehnt")
            continue
        ann, winkel = gesetzt
        if _ruf(ann, "GetLeaderCount") != 1:
            meldungen.append(f"ANGABE_OHNE_HINWEISLINIE: {m.merkmal} in {rolle}")
        if hinweise is not None:  # Lage = linke obere Ecke (Live 19.11.: Textoberkante im PDF knapp darüber)
            drei = _dreizeilig(m.text or "")
            hinweise.append(_Hinweis(m.merkmal, zeilen, ann, rolle, kreise, i, umriss, schaetzung,
                                     (schaetzung[0] / 2, HINWEIS_OBERKANTE_MM - schaetzung[1] / 2), text=notiz,
                                     view=v, winkel=winkel,
                                     varianten=[(notiz, zeilen)] + ([_notiztext(drei)] if drei else [])))
    return meldungen


ZEILENUMBRUCH = chr(10)


def _dreizeilig(text: str) -> str | None:
    """Dreizeilige Form einer Bohrungsangabe: erste Zeile am Strich umbrechen („2 × Ø8 H7 Ⓔ“ / „15 tief“ /
    „Fase 0,5 × 45°“; Review Task 5, I1). Der Umbruch trennt, der Strich entfällt (Runde D: „… Ⓔ –“ am Zeilenende
    stand im PDF direkt vor „16,00“ und las sich als „–16,00“); die Prüfung behandelt Umbruch und „ – “ gleich
    (`pruefen.angabentext`). None ohne „ – “."""
    zeilen = text.split(ZEILENUMBRUCH)
    i = zeilen[0].find(" – ")
    if i < 0:
        return None
    return ZEILENUMBRUCH.join([zeilen[0][:i], zeilen[0][i + 3:]] + zeilen[1:])


def _notiztext(text: str) -> tuple[str, tuple[str, ...]]:
    """Text für `InsertNote` und die Zeilen, wie das PDF sie zeigt. Live 27.11.: Das Unicode-Zeichen „Ⓔ“ lässt auch
    einen Hinweis verschwinden; das Symbol `<MOD-EP>` erscheint als umkreistes E, pymupdf liest „E“."""
    notiz = text.replace("Ⓔ", anf.HUELLE)
    return notiz, tuple(z.strip() for z in text.replace("Ⓔ", "E").split("\n"))


def _kreis_am_punkt(drw, kreis: tuple, winkel: float) -> bool:
    """Kreiskante am Blattpunkt unter `winkel` wählen (spikes/z1_diag_hinweis_ansatz.py: `SelectByID2("", "EDGE", x,
    y, …)` wählt Ansicht und Kante; die Hinweislinie setzt dann an diesem Punkt an statt auf der Gegenseite). Wahr,
    wenn dort eine Kreiskante gewählt ist (der Punkt liegt auf dem gesuchten Kreis; der Radius wird nicht verglichen,
    ein anderer Kreis müsste ihn genau dort kreuzen)."""
    (mx, my), r = kreis
    x, y = mx + r * math.cos(math.radians(winkel)), my + r * math.sin(math.radians(winkel))
    drw.ClearSelection2(True)
    if not _ruf(drw, "Extension").SelectByID2("", "EDGE", x / 1000, y / 1000, 0, False, 0, callout_leer(), 0):
        return False
    sm = _ruf(drw, "SelectionManager")
    for i in range(1, sm.GetSelectedObjectCount2(-1) + 1):
        if sm.GetSelectedObjectType3(i, -1) != KANTE_SICHTBAR:  # swSelEDGES = 1
            continue
        try:
            c = _ruf(sm.GetSelectedObject6(i, -1), "GetCurve")
            return bool(_ruf(c, "IsCircle"))
        except Exception:  # noqa: BLE001 – COM: gewähltes Objekt ohne Kurve
            return False
    return False


def _hinweis_einfuegen(drw, view, kante, text: str, kreis: tuple | None = None, winkel: float | None = None):
    """Kreiskante wählen – am Punkt unter `winkel`, sonst über `IView.SelectEntity` –, Hinweis einfügen (die
    Hinweislinie hängt an der Auswahl, Spike Stufe 3). Liefert (Annotation, Winkel des Ansatzes oder None) oder None."""
    drw.ActivateView(_ruf(view, "GetName2"))
    if winkel is not None and kreis is not None and _kreis_am_punkt(drw, kreis, winkel):
        gewaehlt = winkel
    else:
        drw.ClearSelection2(True)
        if not view.SelectEntity(kante, False):
            return None
        gewaehlt = None
    note = drw.InsertNote(text)
    drw.ClearSelection2(True)
    return None if note is None else (_ruf(note, "GetAnnotation"), gewaehlt)


def _hindernisse_fest(mu, views: dict, fest: dict, mittel: dict, format_: str,
                      band: tuple | None = None) -> list[tuple]:
    """Was sich in der Lesbarkeitsschleife nicht bewegt (Blatt-mm): Kanten aller Ansichten (die Einzelheit als ihr
    Rahmen), Mittellinien, Rahmen der Einzelheit in der Elternansicht, Zeichenfeld, Schriftfeld und das Band der
    Sammelangaben."""
    kanten, linien = _kanten_und_linien(mu, views, fest, mittel, format_, band)
    return kanten + linien


def _einmal(strecken: list[tuple]) -> list[tuple]:
    """Jede Strecke einmal (Runde D, M3: `_kanten` legt eine Kante zwischen zwei Features bei beiden ab)."""
    gesehen, aus = set(), []
    for a, e in strecken:
        schluessel = frozenset(((round(a[0], 2), round(a[1], 2)), (round(e[0], 2), round(e[1], 2))))
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            aus.append((a, e))
    return aus


def _kanten_und_linien(mu, views: dict, fest: dict, mittel: dict, format_: str,
                       band: tuple | None = None) -> tuple[list[tuple], list[tuple]]:
    """(sichtbare Kanten aller Ansichten, je einmal; übrige feste Linien: Rahmen der Einzelheit und in der
    Elternansicht, Mittellinien, Zeichenfeld, Schriftfeld, Band). Für die Anmerkungen sind nur die Kanten „Kante“
    (Runde D, M3); die übrigen Linien sind Hindernis für das Rechteck."""
    kanten, linien = [], []
    for rolle, v in views.items():
        if rolle == "einzelheit" and fest.get("einzelheit"):
            linien += _rechteck_strecken(fest["einzelheit"])
        else:
            kanten += _strecken(_kanten(mu, v), _ruf(v, "ScaleDecimal"))
    for linien_rolle in mittel.values():
        linien += linien_rolle
    if fest.get("rahmen"):
        linien += _rechteck_strecken(fest["rahmen"])
    x0, y0, x1, y1 = zeichenfeld(format_)
    linien += _rechteck_strecken((x0, y0, x1, y1))
    linien += _rechteck_strecken((x1 - SCHRIFTFELD_MM[0], y0, x1, y0 + SCHRIFTFELD_MM[1]))
    if band:
        linien += _rechteck_strecken(band)
    return _einmal(kanten), linien


def _masslinien(views: dict) -> list[tuple]:
    """Maß- und Hilfslinien aller Anzeigemaße und die Rechtecke der linearen Maßzahlen (Blatt-mm), wie sie gerade
    liegen (nach der Reihenanlage)."""
    aus = []
    for v in views.values():
        for dd in list(_ruf(v, "GetDisplayDimensions") or ()):
            daten = _ruf(dd, "GetDisplayData")
            for i in range(_ruf(daten, "GetLineCount")):
                linie = list(daten.GetLineAtIndex3(i))
                aus.append(((linie[4] * 1000, linie[5] * 1000), (linie[7] * 1000, linie[8] * 1000)))
        for ann, m, _ in _lineare_masse(v):
            ax, ay = (c * 1000 for c in list(_ruf(ann, "GetPosition"))[:2])
            dx, dy = (m.text / 2, 2.0) if m.richtung == "h" else (2.0, m.text / 2)
            aus += _rechteck_strecken((ax - dx, ay - dy, ax + dx, ay + dy))
    return aus


def _melde(meldungen: list | None, text: str) -> None:
    """Meldung einmal aufnehmen (die Lesbarkeitsschleife legt die Hinweise in jeder Runde neu)."""
    if meldungen is not None and text not in meldungen:
        meldungen.append(text)


def _alten_hinweis_loeschen(drw, h) -> bool:
    """Alten Hinweis löschen und die Wirkung prüfen wie `_loesche_ansicht` (Review I5): danach eine Notiz weniger in
    seiner Ansicht (`IView.GetNoteCount`; Auswahl über `IAnnotation.Select2` + `DeleteSelection2` wie
    `bemassen._loesche`)."""
    vorher = _ruf(h.view, "GetNoteCount")
    drw.ClearSelection2(True)
    ok = h.ann.Select2(False, 0) and _ruf(drw, "Extension").DeleteSelection2(0)
    drw.ClearSelection2(True)
    return bool(ok) and _ruf(h.view, "GetNoteCount") == vorher - 1


def _hinweise_legen(drw, hinweise: list, views: dict, statisch: list[tuple],
                    meldungen: list | None = None, nah_texte: list[tuple] = ()) -> list[tuple]:
    """Lage jedes Hinweises neu wählen (nach der Reihenanlage, vor den Radiuszahlen): über alle Bohrungen des Bohrbilds
    die beste Lage aus `hinweis_lagen_bewertet`, die kein PDF-Befund verworfen hat (bei Gleichstand die heutige
    Bohrung). Hindernisse sind `statisch`, die Maße, wie sie jetzt liegen, und die schon gelegten Hinweise (Live 19.11.,
    Spannplatte: an der zuerst gewählten Bohrung war nach der Reihenanlage keine der 16 Lagen frei, an der letzten der
    Reihe schon). Wechselt die Bohrung oder dreht der Ansatz der Hinweislinie am Kreis um mehr als
    `HINWEIS_ANSATZ_GRAD` (Live 19.11.: Hinweislinie quer durch die Bohrung), wird der Hinweis neu eingefügt
    (`_hinweis_einfuegen` am Kreispunkt zum Text hin) und der alte gelöscht; bleibt der alte stehen, meldet
    `meldungen` `ANGABE_DOPPELT`, fehlt dem neuen die Hinweislinie, `ANGABE_OHNE_HINWEISLINIE`.
    `IAnnotation.SetPosition2` setzt den Bezugspunkt der Notiz (Mitte − `versatz`); die Hinweislinie zieht mit
    (Spike Stufe 3). Mindestabstand (Nachbesserung C, `angaben.HINWEIS_ABSTAND_ZEILE_MM`): zu den Maß- und
    Hilfslinien und Maßzahlen, zu `nah_texte` (fremde Texte, Anmerkungen; als Strecken) und den Texten der schon
    gelegten Hinweise – nicht zu Kanten. Liefert Rechtecke und Hinweislinien aller Hinweise als Strecken."""
    if not hinweise:
        return []
    masslinien = _masslinien(views)
    hindernisse = statisch + masslinien
    gelegt: list[tuple] = []
    texte_gelegt: list[tuple] = []
    for h in hinweise:
        nah = masslinien + list(nah_texte) + texte_gelegt
        formen = range(len(h.varianten)) if h.varianten else [h.variante]
        beste = None
        if h.fixiert is not None:  # beste Runde wiederherstellen
            beste = (None, h.fixiert[0], h.fixiert[1], h.fixiert[2])
        for v in ([] if beste else formen):
            groesse = h.groesse_von(v)
            for j, (_, kreis) in enumerate(h.kreise):
                for wert, lage in hinweis_lagen_bewertet(kreis, h.umriss, hindernisse + gelegt, groesse, nah):
                    if any(math.dist(lage, w) <= 0.5 for w in h.verworfen):
                        continue
                    # frei vor Form: die dreizeilige Form nur, wenn die zweizeilige keine freie Lage hat (Review I1)
                    schluessel = (wert[0], v, *wert[1:], j != h.instanz, j)
                    if beste is None or schluessel < beste[0]:
                        beste = (schluessel, j, lage, v)
                    break  # Lagen kommen sortiert: die erste nicht verworfene ist die beste dieser Bohrung
        if beste is None:  # alle verworfen: heutige Bohrung und Form, erste Lage
            beste = (None, h.instanz, hinweis_lagen(h.kreis, h.umriss, hindernisse + gelegt, h.groesse, nah)[0],
                     h.variante)
        _, j, lage, v = beste
        if v != h.variante:
            groesse = h.groesse_von(v)
            h.text, h.zeilen = h.varianten[v]
            h.groesse, h.versatz = groesse, (groesse[0] / 2, HINWEIS_OBERKANTE_MM - groesse[1] / 2)
            h.variante, h.vermessen, h.winkel, h.punktwahl = v, False, None, True  # neu einfügen, dann am PDF vermessen
        winkel = _ansatz(h.kreise[j][1], lage, h.groesse, len(h.zeilen))
        gedreht = (h.punktwahl if h.winkel is None
                   else abs((winkel - h.winkel + 180) % 360 - 180) > HINWEIS_ANSATZ_GRAD)
        if j != h.instanz or gedreht:
            neu = _hinweis_einfuegen(drw, h.view, h.kreise[j][0], h.text, h.kreise[j][1], winkel)
            if neu is not None:
                if not _alten_hinweis_loeschen(drw, h):
                    _melde(meldungen, f"ANGABE_DOPPELT: {h.merkmal} in {h.rolle} – alter Hinweis nicht gelöscht")
                (h.ann, h.winkel), h.instanz = neu, j
                h.punktwahl = h.winkel is not None
                if _ruf(h.ann, "GetLeaderCount") != 1:
                    _melde(meldungen, f"ANGABE_OHNE_HINWEISLINIE: {h.merkmal} in {h.rolle}")
            elif j != h.instanz:
                lage = hinweis_lagen(h.kreis, h.umriss, hindernisse + gelegt, h.groesse, nah)[0]
        h.lage = lage
        h.ann.SetPosition2((h.lage[0] - h.versatz[0]) / 1000, (h.lage[1] - h.versatz[1]) / 1000, 0)
        gelegt += _rechteck_strecken(h.rechteck()) + [h.hinweislinie()]
        texte_gelegt += _rechteck_strecken(h.rechteck())
    return gelegt


def _anmerkungen_kreuzen(views: dict, notizen: list, anmerkungen: list, kanten: list[tuple], pdf: Path,
                         linien: list[tuple] = ()) -> list[str]:
    """`ANMERKUNG_KREUZT`/`ANMERKUNG_ZU_NAH` aus dem Endstand (Nachbesserung C): Maße, wie sie liegen,
    Bohrungsangaben (Rechteck und Hinweislinie), fremde Texte des letzten PDFs, die sichtbaren Kanten (`kanten`), die
    übrigen festen Linien (`linien`: Rahmen, Mittellinien – Hindernis für das Rechteck, Runde D M3) und die anderen
    Anmerkungen an ihrer zurückgelesenen Lage (`anforderungen_setzen.anmerkungen_pruefen`)."""
    masslinien = _masslinien(views)
    try:
        fremde = _fremde_texte(texte(pdf), notizen + anmerkungen) if pdf.exists() else []
    except ImportError:  # ohne pymupdf: nur gegen Maße, Angaben und Kanten
        fremde = []
    hinw = [s for h in notizen if h.lage for s in _rechteck_strecken(h.rechteck()) + [h.hinweislinie()]]
    return anf.anmerkungen_pruefen(anmerkungen, masslinien + hinw + [s for r in fremde for s in _rechteck_strecken(r)]
                                   + list(linien), [h.rechteck() for h in notizen if h.rechteck()] + fremde, kanten,
                                   masslinien, [h.hinweislinie() for h in notizen if h.lage])


def hinweis_im_pdf(h, pdf_texte: list[tuple[str, tuple]]) -> tuple | None:
    """Rechteck eines Hinweises, wie das PDF ihn zeigt: je Zeile der nächste gleichlautende Text (wie
    `_hinweise_vermessen`), vereinigt; None, wenn eine Zeile fehlt."""
    if h.lage is None:
        return None
    rechtecke = zeilen_im_pdf(h, pdf_texte)
    if rechtecke is None:
        return None
    return (min(r[0] for r in rechtecke), min(r[1] for r in rechtecke), max(r[2] for r in rechtecke),
            max(r[3] for r in rechtecke))


def zeilen_im_pdf(h, pdf_texte: list[tuple[str, tuple]]) -> list[tuple] | None:
    """Je Zeile eines Hinweises das Rechteck des nächsten gleichlautenden PDF-Texts; None, wenn eine Zeile fehlt."""
    if h.lage is None:
        return None
    rechtecke = []
    for zeile in h.zeilen:
        treffer = [r for wort, r in pdf_texte if wort == zeile]
        if not treffer:
            return None
        rechtecke.append(min(treffer, key=lambda r: math.dist(h.lage, ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2))))
    return rechtecke


def zu_nah(rechteck: tuple, strecken: list[tuple]) -> int:
    """Wie viele Strecken das Rechteck näher als `HINWEIS_ABSTAND_ZEILE_MM` in Zeilenrichtung bzw.
    `HINWEIS_ABSTAND_QUER_MM` quer dazu berühren (Nachbesserung C, Punkt 4)."""
    gx, gy = HINWEIS_ABSTAND_ZEILE_MM, HINWEIS_ABSTAND_QUER_MM
    weit = (rechteck[0] - gx, rechteck[1] - gy, rechteck[2] + gx, rechteck[3] + gy)
    return sum(1 for a, b in strecken if _schneidet(a, b, weit))


def _hinweise_zu_nah(views: dict, notizen: list, anmerkungen: list, pdf: Path) -> list[str]:
    """Endprüfung Punkt 4 am PDF (nie still): ein Hinweis, dessen Text näher als eine Schrifthöhe in Zeilenrichtung
    bzw. 1 mm quer an fremdem Text, Maß- oder Hilfslinien liegt → `ANGABE_ZU_NAH`. Gemessen je Zeile (Rechtecke aus dem
    PDF, `zeilen_im_pdf`; Runde D: am umschließenden Rechteck galt „Fase …“ als zu nah an „16,00“, das 4,8 mm höher
    stand); fehlt eine Zeile im PDF, das geschätzte Rechteck. Die Zahl zählt jede fremde Strecke einmal."""
    if not notizen:
        return []
    try:
        pdf_texte = texte(pdf) if pdf.exists() else []
    except ImportError:
        return ["ANGABE_ZU_NAH: ungeprüft – pymupdf fehlt (Extra pdf)"]
    alle = notizen + anmerkungen
    fremde = _fremde_texte(pdf_texte, alle)
    aus = []
    for h in notizen:
        rechtecke = zeilen_im_pdf(h, pdf_texte) or ([h.rechteck()] if h.rechteck() else [])
        if not rechtecke:
            continue
        nah = (_masslinien(views) + [s for q in fremde for s in _rechteck_strecken(q)]
               + [s for o in alle if o is not h and o.rechteck() for s in _rechteck_strecken(o.rechteck())])
        n = sum(1 for s in nah if any(zu_nah(r, [s]) for r in rechtecke))
        if n:
            aus.append(f"ANGABE_ZU_NAH: {h.merkmal} in {h.rolle} – Text „{h.zeilen[0]}“ näher als "
                       f"{zahl_mm(HINWEIS_ABSTAND_ZEILE_MM)} mm (Zeilenrichtung) bzw. {zahl_mm(HINWEIS_ABSTAND_QUER_MM)} mm "
                       f"an fremdem Text oder Maßlinie ({n})")
    return aus


def zahl_mm(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def _gruppen(spec: dict) -> dict[str, str]:
    """Verrundung und Fase zählen zum Merkmal, dessen Kanten sie bearbeiten (Einzelheit: Tasche samt Eckradius)."""
    aus = {}
    for f in spec.get("features", []):
        if f.get("typ") in ("verrundung", "fase"):
            ziele = [k.get("feature") for k in f.get("kanten", []) if isinstance(k, dict) and k.get("feature")]
            if ziele:
                aus[f["id"]] = ziele[0]
    return aus


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
             "DrawnBy": "swki", "DrawnDate": time.strftime("%d.%m.%Y"),
             "Dokumentart": DOKUMENTART}
    cpm = _ruf(drw, "Extension").CustomPropertyManager("")
    for name, wert in werte.items():
        cpm.Add3(name, EIGENSCHAFT_TEXT, str(wert), EIGENSCHAFT_ERSETZEN)
    return werte


def zeichnen(spec_pfad: Path, lauf: int | None = None) -> dict:
    t0 = time.time()
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    if veraltet := funktionen_veraltet(spec_pfad):  # Gesamtreview C1: nie mit geänderten Tabellenwerten zeichnen
        raise ZeichnungFehler("FUNKTIONEN_VERALTET", veraltet)
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
    (ausgabe / "zeichnung.json").unlink(missing_ok=True)  # nie eine alte Übergabe neben einer neuen Zeichnung
    lauf_datei(spec_pfad, lauf, "zeichnung.pruefbericht").unlink(missing_ok=True)  # alter Prüfbericht gilt nicht mehr
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
        for toggle in KEINE_MARKEN:
            ext.SetUserPreferenceToggle(toggle, 0, False)
        ext.SetUserPreferenceToggle(EINZELHEIT_NORM, 0, False)  # vor dem Anlegen der Einzelheit, in jeder Zeichnung
        ext.SetUserPreferenceInteger(EINZELHEIT_NAME, 0, NAME_EIGEN)
        ext.SetUserPreferenceString(EINZELHEIT_TEXT, 0, "EINZELHEIT")
        ext.SetUserPreferenceToggle(EINZELHEIT_OBEN, 0, True)
        rauheit_text = ext.GetUserPreferenceTextFormat(TEXT_RAUHEIT, 0)
        rauheit_text.CharHeight = _ruf(ext.GetUserPreferenceTextFormat(TEXT_HINWEIS, 0), "CharHeight")
        ext.SetUserPreferenceTextFormat(TEXT_RAUHEIT, 0, rauheit_text)
        ext.SetUserPreferenceInteger(SF_NORM, 0, SF_NORM_1302_2002)  # Spike g: ohne losen Strich, Text im Feld a
        _blatt(drw, "A3quer", (1, 1), r.zeichnung.get("A3quer") or next(iter(r.zeichnung.values())))
        mu = mathutil(app)
        bezugsbuchstaben = set(spec.get("bezuege") or {})  # Runde E: der Schnitt heißt nicht wie ein Bezug
        views, schnitt, nicht_erzeugt, schnittbuchstaben = _erzeuge(drw, mu, teil, ansichten, bezugsbuchstaben)
        meldungen += nicht_erzeugt
        protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
        plan = massplan(spec, protokoll)
        sammel = sammelhoehe_mm(spec)  # Platz der Sammelangaben über dem Schriftfeld (Task 5 schreibt sie)
        basis = next(a.rolle for a in ansichten if a.modellansicht)
        # Runde D/E: Einzelheit ab Z rückwärts, Schnitt ab A; Bezugsbuchstaben und der Schnittbuchstabe sind vergeben
        buchstabe = einzelheit_buchstabe(0, {m.text for m in plan if m.quelle == "bezug"} | bezugsbuchstaben
                                         | schnittbuchstaben)
        bereich: dict = {}
        gruppe = _gruppen(spec)
        mitten = {m.name for m in plan if m.quelle == "modell" and m.bezug in MITTENBEZUG}
        bem = bemasse(drw, views, plan, ["haupt"] + [r for r in views if r != "haupt"], max_je_ansicht(standard),
                      weitere_rollen(spec), lambda rolle: _projektion(drw, views["haupt"], rolle),
                      vorzugsansichten(spec, plan), blickachsen(ansichten, weitere_rollen(spec)),
                      lambda rolle, angebot, genutzt: _einzelheit(drw, mu, views, rolle, angebot, genutzt, gruppe,
                                                                  mitten, buchstabe, bereich, meldungen, sammel),
                      {spec["features"][0]["id"]} if spec.get("features") else set(), gruppe)
        meldungen += bem.meldungen
        meldungen += massplan_meldungen(spec, protokoll)
        for rolle in [r for r in list(views) if r not in ("haupt", basis) and not bem.je_ansicht.get(r)]:
            if not _loesche_ansicht(drw, views.pop(rolle)):  # Ansicht ohne eigenes Maß entfällt (Design §6.1)
                meldungen.append(f"ANSICHT_NICHT_GELOESCHT: {rolle} ohne Maß blieb auf dem Blatt")
        groessen = {rolle: _groesse_1zu1(v) for rolle, v in views.items()}
        if "einzelheit" in views:
            groessen["einzelheit"] = bereich["groesse"]  # GetOutline einer Einzelheit: Rand ~12 mm, später veraltet
        format_, massstab, plaetze = anordnen(groessen, sammel)
        blattformat = r.zeichnung.get(format_)
        if blattformat is None:
            raise ZeichnungFehler("ZEICHNUNG_VORLAGE_FEHLT", f"config/rechner.yaml: zeichnung.{format_} fehlt")
        _blatt(drw, format_, massstab, blattformat)
        eigen = {p.rolle: p.massstab for p in plaetze if p.massstab}
        for rolle, v in views.items():  # Ansichten folgen sonst ihrem automatischen Maßstab (Live Z1.3: Platte zu groß)
            m = eigen.get(rolle, massstab)
            v.ScaleDecimal = m[0] / m[1]
        fest = {}  # Umriss der Einzelheit selbst gerechnet (GetOutline folgt dem Maßstab nicht, spikes/z1_diag_einzelheit_lage.py)
        for p in sorted(plaetze, key=lambda p: p.rolle != basis):  # Elternansicht zuerst, Kinder sind ausgerichtet
            if p.rolle == "einzelheit":
                f = p.massstab[0] / p.massstab[1]
                _setze_lage(views[p.rolle], (p.mitte_mm[0] - bereich["versatz"][0] * f,
                                             p.mitte_mm[1] - bereich["versatz"][1] * f))
                (cx, cy), (b, h) = p.mitte_mm, p.groesse_mm
                fest["einzelheit"] = (cx - b / 2, cy - h / 2, cx + b / 2, cy + h / 2)
            else:
                _setze_lage(views[p.rolle], p.mitte_mm)
        if "einzelheit" in views and bereich:  # Rahmen der Einzelheit in der Elternansicht (Hindernis für Radiuszahlen)
            px, py = (x * 1000 for x in list(_ruf(views[bereich["eltern"]], "Position"))[:2])
            f = massstab[0] / massstab[1]
            cx, cy = px + bereich["versatz"][0] * f, py + bereich["versatz"][1] * f
            b, h = bereich["groesse"][0] * f, bereich["groesse"][1] * f
            fest["rahmen"] = (cx - b / 2, cy - h / 2, cx + b / 2, cy + h / 2)
        neu_gesetzt = _neue_masse(drw, views, plan, bem.neu, achsvektor(spec), meldungen)
        for rolle, v in views.items():
            if not ordne_masse_an(drw, v):
                meldungen.append(f"MASSE_NICHT_ANGEORDNET: {rolle}")
        mittel, m_meld = _mittellinien(drw, mu, views, plan)
        meldungen += m_meld
        notizen: list[_Hinweis] = []  # Bohrungsangaben (Name `hinweise` ist die Ansichtswahl-Funktion)
        achsen = blickachsen(ansichten, weitere_rollen(spec))
        meldungen += _angaben_setzen(drw, mu, views, plan, achsen, enthalten=_enthaltene(spec, plan), hinweise=notizen)
        # Stufe 4: nach allen Schritten, die Maße über `kurzname` suchen, vor der Reihenanlage (Toleranz und Zusatz
        # verbreitern die Zahl). Toleranz und Zusatz nur an Zeichnungsmaßen (Spike Stufe 4: am Modellmaß verloren).
        namen, d_meld = anf.dauerhaft_machen(drw, mu, views, plan)
        meldungen += d_meld + anf.zusaetze_setzen(views, plan, namen, nur=set(namen))
        anmerkungen: list[anf.Anmerkung] = []
        meldungen += anf.anmerkungen_setzen(drw, mu, views, plan, achsen,
                                            {f["id"]: f.get("typ") for f in spec.get("features", [])},
                                            _enthaltene(spec, plan, ("angabe", "rauheit", "form_lage")), anmerkungen,
                                            {h.merkmal: [h.kreis[0]] for h in notizen},
                                            {m.merkmal: anf.instanzen(spec, m.merkmal) for m in plan})
        zeilen_sammel = sammelangaben(spec)
        band = anf.sammelband(format_, sammel)
        s_meld = anf.sammelangaben_setzen(drw, zeilen_sammel, format_, sammel)
        meldungen += s_meld
        eigenschaften = _eigenschaften(drw, spec, format_, massstab)
        _ruf(drw, "EditRebuild3")
        zeichnung, pdf = ausgabe / f"{zeichnungsname(spec)}.slddrw", ausgabe / f"{zeichnungsname(spec)}.pdf"
        _speichern(ext, zeichnung)  # zuerst: das Schriftfeld zeigt den Dateinamen (sonst „Zeichn1“ im PDF)
        rahmen = {bereich["eltern"]: fest["rahmen"]} if "rahmen" in fest else None
        anm_kanten, anm_linien = _kanten_und_linien(mu, views, fest, mittel, format_, band)
        statisch, angaben_meld = anm_kanten + anm_linien, []

        fremde: list[tuple] = []  # Textrechtecke des letzten PDFs außer Hinweisen und Anmerkungen (Live 28.11.: Rahmen
        #                           lag auf „SCHNITT A-A“)

        def nach_reihen():  # Hinweise zuerst (meiden Maße und Kanten), dann Anmerkungen, dann die Radiuszahlen
            if notizen or anmerkungen:  # IDisplayData zeigt die eben gesetzten Reihen erst nach dem Neuaufbau (19.11.)
                _ruf(drw, "EditRebuild3")
            # Anmerkungen der letzten Runde sind Hindernis für die Hinweise (Review Task 5, I1)
            anm_text = [s for a in anmerkungen if a.lage for s in _rechteck_strecken(a.rechteck())]
            anm = anm_text + [s for a in anmerkungen if a.lage for s in a.linien()]
            fremd = [s for r in fremde for s in _rechteck_strecken(r)]
            gelegt = _hinweise_legen(drw, notizen, views, statisch + anm + fremd, angaben_meld, fremd + anm_text)
            if anmerkungen:  # Orte wählt `_gemeinsam` (Runde E: kein zweites Umhängen davor)
                masslinien = _masslinien(views)
                gelegt += anf.anmerkungen_legen(anmerkungen, masslinien + gelegt + fremd + anm_linien,
                                                [h.rechteck() for h in notizen if h.rechteck()] + fremde, anm_kanten,
                                                masslinien, [h.hinweislinie() for h in notizen if h.lage], drw,
                                                angaben_meld, {h.merkmal: [h.kreis[0]] for h in notizen})
            _radien_setzen(mu, views, rahmen, mittel, gelegt)

        meldungen += _lesbar_anlegen(drw, ext, views, pdf, format_, fest, nach_reihen,
                                     _kennbuchstabe(views[bereich["eltern"]], fest["rahmen"], buchstabe)
                                     if "rahmen" in fest else None, runden=5 if anmerkungen else 3,
                                     hinweise=notizen + anmerkungen, band=band, fremde_texte=fremde)
        meldungen += angaben_meld + _sammel_im_pdf(pdf, zeilen_sammel, band)
        meldungen += anf.anmerkungen_wirkung(anmerkungen)  # Runde E (M7): Rahmen im Endstand nach Wirkung
        if anmerkungen:  # Nachbesserung C: was nach der letzten Runde noch kreuzt, steht in den Meldungen
            meldungen += _anmerkungen_kreuzen(views, notizen, anmerkungen, anm_kanten, pdf, anm_linien)
        meldungen += _hinweise_zu_nah(views, notizen, anmerkungen, pdf)
        _speichern(ext, zeichnung)
        info = [{"rolle": rolle, "name": _ruf(v, "GetName2"), "massstab": round(_ruf(v, "ScaleDecimal"), 4),
                 "umriss_mm": [round(x, 1) for x in fest.get(rolle) or _umriss_mm(v)]} for rolle, v in views.items()]
    finally:
        if drw is not None:
            sw.schliesse(app, drw)
        sw.schliesse(app, model)
    if _sha(teil) != sha_teil:
        raise ZeichnungFehler("ZEICHNUNG_TEIL_GEAENDERT", f"{teil.name} wurde beim Zeichnen verändert")
    masse = {"plan": _planzahlen(plan)[0], "gesetzt": bem.gesetzt + sum(neu_gesetzt.values()), "geloescht": bem.geloescht,
             "je_ansicht": {r: len(bem.je_ansicht.get(r, [])) + neu_gesetzt.get(r, 0) for r in views}}
    uebergabe_pfad = schreibe_uebergabe(  # Eingabe für Z1.4 (Design §8.1)
        ausgabe / "zeichnung.json",
        uebergabe(plan, masse, _sha(zeichnung), meldungen, format_, massstab, lauf, {i["rolle"]: i["name"] for i in info},
                  namen))
    anm_plan = sum(1 for m in plan if m.quelle in ("rauheit", "form_lage", "bezug"))
    return {"zeichnung": str(zeichnung), "pdf": str(pdf), "png": _png(pdf), "format": format_,
            "massstab": f"{massstab[0]}:{massstab[1]}", "ansichten": info, "schnitt": schnitt,
            "eigenschaften": eigenschaften, "meldungen": meldungen,
            "masse": masse, "uebergabe": str(uebergabe_pfad),
            "angaben": {"plan": _planzahlen(plan)[1], "gesetzt": len(notizen)},
            "anmerkungen": {"plan": anm_plan, "gesetzt": len(anmerkungen)},
            "zeichnungsmasse": namen, "dauer_s": round(time.time() - t0, 1)}


def _sammel_im_pdf(pdf: Path, zeilen: list[str], band: tuple) -> list[str]:
    """`anforderungen_setzen.sammel_pruefen` am PDF; ohne pymupdf (Extra pdf) die Meldung SAMMELANGABE_FEHLT
    „ungeprüft“ (Z-SAM-1, hart) statt eines rohen ImportError (Gesamtreview I4)."""
    try:
        pdf_texte = texte(pdf)
    except ImportError:
        return ["SAMMELANGABE_FEHLT: Sammelangaben im PDF ungeprüft – pymupdf fehlt (Extra pdf)"]
    return anf.sammel_pruefen(pdf_texte, zeilen, band)


def sammelhoehe_mm(spec: dict) -> float:
    """Höhe der Sammelangaben über dem Schriftfeld: eine Zeile je Zeile des Sammelhinweises (umgebrochen, mit der
    allgemeinen Rauheit, `anforderungen_setzen.sammel_zeilenzahl`)."""
    return anf.sammel_zeilenzahl(sammelangaben(spec)) * SAMMEL_ZEILE_MM


def schreibe_uebergabe(pfad: Path, daten: dict) -> Path:
    """Schreibt die Übergabe atomar (tmp-Datei, dann replace), UTF-8, Umlaute und Ⓔ im Klartext."""
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(pfad)
    return pfad


def uebergabe(plan: list[Mass], gesetzt: dict, sha_zeichnung: str, meldungen: list[str], format_: str | None = None,
              massstab: tuple[int, int] | None = None, lauf: int | None = None,
              ansichten: dict[str, str] | None = None, namen: dict[str, str] | None = None) -> dict:
    """Übergabe an die Zeichnungsprüfung Z1.4 (Design §8.1), reine Funktion: Maßplan (Toleranz und FormLage als dict),
    was gesetzt wurde, SHA-256 der .slddrw und die Meldungen. `namen` (Stufe 4): Modellmaß → Zeichnungsmaß, das es
    ersetzt (`anforderungen_setzen.dauerhaft_machen`). Das JSON schreibt `zeichnen` als `zeichnung/zeichnung.json`."""
    daten = {"schema": 1, "format": format_, "massstab": f"{massstab[0]}:{massstab[1]}" if massstab else None,
             "lauf": lauf, "plan": [asdict(m) for m in plan], "gesetzt": gesetzt, "sha256_slddrw": sha_zeichnung,
             "meldungen": list(meldungen)}
    if ansichten is not None:
        daten["ansichten"] = dict(ansichten)
    if namen is not None:
        daten["zeichnungsmasse"] = dict(namen)
    return daten


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


def _reihen_anlegen(views: dict, vorlauf: dict, fest: dict | None = None) -> list[tuple[tuple, tuple[float, float]]]:
    """Nutzer 18.11.2026: Maße übereinander, Zahlen von Linien gekreuzt → lineare Maße je Ansichtsseite in Reihen
    (`swki.zeichnung.reihen`), Lage über `IAnnotation.SetPosition2` (Maßlinie folgt der Zahl). Liefert je Maß die
    Ansichtsseite (Rolle, Richtung, Seite) und die Lage der Zahl in Blatt-mm."""
    platz = []
    for rolle, v in views.items():
        masse, umriss = _lineare_masse(v), _rand(fest, rolle) or _umriss_mm(v)
        eigen = {(r, s): mm for (ro, r, s), mm in vorlauf.items() if ro == rolle}
        lage = reihen([m for _, m, _ in masse], umriss, eigen)
        for ann, m, versatz in masse:
            entlang, quer = lage[m.schluessel]
            x, y = (entlang, quer + versatz) if m.richtung == "h" else (quer + versatz, entlang)
            ann.SetPosition2(x / 1000, y / 1000, 0)
            platz.append(((rolle, m.richtung, seite(m, umriss)), (x, y), m.text))
    return platz


def _rand(fest: dict | None, rolle: str):
    """Selbst gerechneter Rahmen (Einzelheit) samt dem Rand, den SolidWorks um Ansichten legt (~6 mm)."""
    r = (fest or {}).get(rolle)
    return (r[0] - 6, r[1] - 6, r[2] + 6, r[3] + 6) if r else None


def _lesbar_anlegen(drw, ext, views: dict, pdf: Path, format_: str, fest: dict | None = None,
                    nach_reihen: Callable[[], None] | None = None,
                    kennbuchstabe: tuple[str, Callable[[], bool]] | None = None, runden: int = 3,
                    hinweise: list | None = None, band: tuple | None = None,
                    fremde_texte: list | None = None) -> list[str]:
    """Reihen anlegen, PDF speichern, am PDF prüfen (was der Leser sieht). Ein Befund an einer Maßzahl rückt alle
    Reihen ihrer Ansichtsseite um einen Reihenabstand nach außen (Beschriftungen von SolidWorks, die die Reihenanlage
    nicht kennt), dann neu; höchstens `runden` Mal. Ein Befund am Kennbuchstaben der Einzelheit (`kennbuchstabe`:
    Buchstabe, Umsetzen auf die nächste Rahmenecke → False, wenn keine mehr) setzt ihn um (Live 19.11.: „A“ lag auf der
    Mittellinie). Ein Befund an einem Hinweis (Bohrungsangabe; Text eine seiner Zeilen) verwirft dessen Lage, `nach_reihen`
    legt ihn auf die nächste (Plan Stufe 3 Task 4); Hinweise rücken keine Reihen. Anmerkungen (Stufe 4: Rauheit,
    Rahmen, Bezug) stehen mit in `hinweise` und gelten nur bei Nähe als betroffen; Befunde an Hinweisen und Anmerkungen
    zählen nicht für den Kennbuchstaben („A“, „B“ gibt es als Bezug und als Kennbuchstabe). `band`: Sammelangaben, für
    Maßzahlen und Hinweise gesperrt wie das Schriftfeld. Endet die letzte Runde mit mehr Befunden als die beste, wird
    die beste wiederhergestellt (Reihenabstände und `fixiert` je Hinweis/Anmerkung, Review Task 5 I1). Was bleibt,
    wird gemeldet."""
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        pruefen = False
    else:
        pruefen = True
    vorlauf: dict[tuple, float] = {}
    x0, y0, x1, _ = zeichenfeld(format_)
    sperren = [(x1 - SCHRIFTFELD_MM[0], y0, x1, y0 + SCHRIFTFELD_MM[1])] + ([band] if band else [])

    def anlegen_und_pruefen():
        platz = _reihen_anlegen(views, vorlauf, fest)
        if nach_reihen:  # Radiuszahlen meiden die Linien der eben angelegten Maße
            nach_reihen()
        _ruf(drw, "EditRebuild3")
        _speichern(ext, pdf)
        if not pruefen:
            return platz, None
        rahmen = tuple((h.zeilen[0], h.rechteck()) for h in hinweise or []
                       if getattr(h, "art", "") == "form_lage" and h.rechteck())
        befunde = pruefe_pdf(pdf, _ausschluss(format_), rahmen=rahmen) + ausserhalb(
            [(f"{s[0]}/{s[1]}{s[2]}", x, y, laenge, s[1]) for s, (x, y), laenge in platz], zeichenfeld(format_),
            sperren)
        for h in hinweise or []:  # pruefe_pdf übergeht Rand und Schriftfeld
            r = h.rechteck()
            if r and (r[0] < x0 or r[1] < y0 or r[2] > x1 or r[3] > zeichenfeld(format_)[3] or
                      any(_ueberlappt(r, s) for s in sperren)):
                befunde.append(Befund("ausserhalb", h.zeilen[0], r))
        return platz, befunde

    befunde, beste = [], None
    for runde in range(runden + 2):
        platz, befunde = anlegen_und_pruefen()
        if befunde is None:
            return ["LESBARKEIT_UNGEPRUEFT: pymupdf fehlt (Extra pdf)"]
        if fremde_texte is not None:  # Texte, die sich nicht bewegen (Ansichtsbeschriftung, Maßzahlen): Hindernis
            fremde_texte[:] = _fremde_texte(texte(pdf), hinweise or [])
        if beste is None or len(befunde) < beste[0]:  # Review Task 5 (I1): beste Runde merken
            beste = (len(befunde), dict(vorlauf), [(h, h.stand()) for h in hinweise or []])
        if not befunde or runde == runden + 1:
            break
        umgesetzt = False
        an_hinweis = {id(b): h for b in befunde if (h := _hinweis_zu(b, hinweise or []))}
        if kennbuchstabe and any(kennbuchstabe[0] in (b.text, b.anderes) for b in befunde if id(b) not in an_hinweis):
            umgesetzt = kennbuchstabe[1]()
        vermessen = _hinweise_vermessen(hinweise or [], texte(pdf))  # Lage galt mit geschätzter Größe: neu wählen
        umgesetzt = umgesetzt or bool(vermessen)
        for h in {id(h): h for h in an_hinweis.values() if all(h is not v for v in vermessen)}.values():
            umgesetzt = h.verwerfen() or umgesetzt
        seiten = set()
        for b in (b for b in befunde if b.art != "ausserhalb"  # Rücken nach außen hilft da nicht
                  and id(b) not in an_hinweis
                  and not (kennbuchstabe and kennbuchstabe[0] in (b.text, b.anderes))):
            mx, my = (b.rechteck_mm[0] + b.rechteck_mm[2]) / 2, (b.rechteck_mm[1] + b.rechteck_mm[3]) / 2
            nah = min(platz, key=lambda p: math.dist(p[1], (mx, my)), default=None)
            if nah and math.dist(nah[1], (mx, my)) <= NAEHE_MM:
                seiten.add(nah[0])
        if runde >= runden:
            seiten = set()
        if not seiten and not umgesetzt:
            break
        for s in seiten:
            vorlauf[s] = vorlauf.get(s, 0.0) + ABSTAND_MM
    if beste is not None and len(befunde) > beste[0]:  # letzte Runde schlechter: die beste wiederherstellen
        vorlauf.clear()
        vorlauf.update(beste[1])
        for h, stand in beste[2]:
            h.fixiert = stand
        platz, befunde = anlegen_und_pruefen()
        for h, _ in beste[2]:
            h.fixiert = None
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
    """Neue Maße (Drehteil) über Kanten: Ø links neben der Ansicht, Längen darüber, gestaffelt; Toleranz des Plans
    direkt daran (sie sind schon Zeichnungsmaße, Spike Stufe 4). Liefert die Zahl der wirklich gesetzten Maße je
    Ansicht (Review I2)."""
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
            dd = setze_neu(drw, views[rolle], m, achse, platz)
            if dd is not None:
                gesetzt[rolle] = gesetzt.get(rolle, 0) + 1
                if not anf.toleranz_setzen(dd, m.toleranz):
                    meldungen.append(f"TOLERANZ_NICHT_GESETZT: {mid}")
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


def _erzeuge(drw, mu, teil: Path, ansichten: list[Ansicht],
             vergeben: set[str] | frozenset = frozenset()) -> tuple[dict, str | None, list[str], set[str]]:
    """Basis = die Ansicht mit Modellansicht. Ein Schnitt ohne Modellansicht entsteht aus ihr (Längsschnitt eines
    Drehteils), die übrigen werden aus der Hauptansicht projiziert. Liefert Ansichten, Name des wirklich erzeugten
    Schnitts, Meldungen für verlangte, aber nicht erzeugte Schnitte (Review I1) und die vergebenen Schnittbuchstaben.
    Jeder Schnitt heißt nach dem nächsten freien `schnitt_buchstabe` ohne `vergeben` (Bezüge) und ohne die Buchstaben
    der Schnitte davor (Gesamtreview a; nach Wirkung geprüft, `SCHNITT_BUCHSTABE`; None: keiner frei – gemeldet,
    SolidWorks wählt)."""
    basis = next(a for a in ansichten if a.modellansicht)
    belegt: set[str] = set()

    def naechster() -> str | None:
        b = schnitt_buchstabe(0, set(vergeben) | belegt)
        if b is None:
            meldungen.append("SCHNITT_BUCHSTABE: kein freier Buchstabe (alle als Bezug vergeben) – SolidWorks wählt")
        else:
            belegt.add(b)
        return b

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
            buchstabe = naechster()
            v = _laengsschnitt(drw, view, buchstabe or "")
            schnitt = _ruf(v, "GetName2") if v is not None else None
            if v is not None and buchstabe:
                meldungen += _schnitt_pruefen(v, buchstabe)
        elif a.schnitt and a.durch and a.rolle == "drauf":
            buchstabe = naechster()
            v = _fraesschnitt(drw, mu, views["haupt"], a.durch, buchstabe or "")
            if v is not None and buchstabe:
                meldungen += _schnitt_pruefen(v, buchstabe)
            if v is None:
                meldungen.append(f"SCHNITT_NICHT_ERZEUGT: durch {', '.join(a.durch)} – Projektion statt Schnitt")
                v = _projektion(drw, views["haupt"], a.rolle)
            else:
                schnitt = _ruf(v, "GetName2")
        else:
            v = _projektion(drw, views["haupt"], a.rolle)
            if a.schnitt:
                meldungen.append(f"SCHNITT_NICHT_UNTERSTUETZT: Ansicht {a.rolle} bräuchte einen Schnitt (Frästeil, "
                                 "Stufe 1 zeichnet sie ungeschnitten)")
        if v is None:
            raise ZeichnungFehler("ZEICHNUNG_ANSICHT", f"Ansicht {a.rolle} nicht erzeugt")
        views[a.rolle] = v
    return views, schnitt, meldungen, belegt


def _png(pdf: Path) -> str | None:
    try:
        import pymupdf
    except ImportError:
        return None
    png = pdf.with_suffix(".png")
    with pymupdf.open(pdf) as doc:
        doc[0].get_pixmap(dpi=110).save(png)
    return str(png)
