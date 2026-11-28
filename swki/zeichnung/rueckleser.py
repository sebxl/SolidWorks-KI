"""Rückleser der Zeichnungsprüfung (Plan Z1.4 Task 4b, Design §8.1): eine von `swki zeichnen` gespeicherte SLDDRW
schreibgeschützt öffnen, als Ist-Modell (`ist.py`) lesen und ohne Speichern wieder schließen. Geschlossen wird nur, was
dieses Öffnen neu geladen hat (die Zeichnung und das mitgeladene Teil); vorher offene Dokumente bleiben unberührt.

Leselogik wie beim Zeichnen (nicht kopiert): Hilfslinien und Bezugspunkte linearer Maße `anforderungen_setzen.
hilfslinien`, sichtbare Kanten `sichtbare_kanten`, Kante am Bezugspunkt `kante_am_punkt` (dieselbe Streckenregel samt
verlängerter Kante an einer virtuellen Fasenecke), Wert `wert_mm`, Maßname `bemassen.kurzname`, Eigenschaften
`compiler.eigenschaften.lies_eigenschaften`. Spike: `docs/zeichnungsableitung/spike-z1.md` (Stufe 4, g–i), Sonde
Task 4b (28.11.2026, SpannplatteZ/BuchseZ/Spannplatte): Anmerkungen hängen an Kanten (Typ 1), deren Nachbarflächen die
Feature-Namen liefern (im Schnitt zusätzlich „Schnitt1“); Mittellinien sind Konstruktionslinien der Ansichtsskizze;
Ø an Linearmaßen des Längsschnitts kommt als Präfix `<MOD-DIAM>`, Ⓔ als Suffix `<MOD-EP>`.

API (swki api methode, SW 2025): ISldWorks.OpenDoc6 (6, 2001; swDocDRAWING = 3, swOpenDocOptions_Silent | _ReadOnly),
GetDocuments (0, 2009), CloseDoc (1); IModelDoc2.GetPathName (0, 2001), GetTitle (0, 2001); IDrawingDoc.GetFirstView,
GetCurrentSheet, GetSheetNames; ISheet.GetName, GetProperties2 (0, 2016: Papier, Vorlage, Maßstab n, m, Winkel, Breite,
Höhe in m); IView.GetNextView, GetName2 (0, 2005), Type (swDrawingViewTypes_e: Blatt 1, Schnitt 2, Einzelheit 3),
ScaleRatio, ScaleDecimal, Position, GetSection (0, 2000) → IDrSection.GetLabel (0, 2000), GetDetail (0, 2001) →
IDetailCircle.GetLabel (0, 2001), GetDisplayDimensions (0, 2009), GetNotes (0, 2009), GetFirstGTOL → IGtol.GetNextGTOL,
GetFirstDatumTag → IDatumTag.GetNext, GetFirstSFSymbol → ISFSymbol.GetNext, GetSketch → ISketch.GetSketchSegments,
ISketchSegment.GetType (swSketchLINE = 0), ConstructionGeometry, ISketchLine.GetStartPoint2/GetEndPoint2 (0, 2000) →
ISketchPoint.X/Y; IDisplayDimension.Type2 (2004), GetText (1; Präfix 1, Suffix 2), ShowParenthesis, GetDisplayData →
IDisplayData.GetTextCount, GetTextAtIndex (1), GetDimension2 (1, 2008) → IDimension.Tolerance (2006) →
IDimensionTolerance.Type, GetMinValue, GetMaxValue, GetHoleFitValue, GetShaftFitValue (0, 2006); INote.GetText,
GetAnnotation; IGtol.GetFrameValues (1), GetFrameSymbols2 (1), GetText (1, 2018; swGTolTextCalloutAbove = 3);
IDatumTag.GetLabel (0, 2000); ISFSymbol.GetText (1, 2000; swSFSymbolRoughnessValue1 = 8 Feld a,
swSFSymbolProductionMethod = 2 Feld c); IAnnotation.GetAttachedEntities3 (0, 2008), GetAttachedEntityTypes (0);
IEdge.GetTwoAdjacentFaces2 (0, 2001) → IFace2.GetFeature (0, 2001) → Name.
"""

import math
import os
import re
from dataclasses import replace
from pathlib import Path

from swki.compiler import sw
from swki.compiler.eigenschaften import lies_eigenschaften
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner
from swki.verbindung import byref_long, verbinde
from swki.zeichnung import anforderungen_setzen as anf
from swki.zeichnung.bemassen import _anzeige, _ruf, kurzname
from swki.zeichnung.blatt import FORMATE
from swki.zeichnung.ist import Ist, IstAngabe, IstAnsicht, IstMass, IstToleranz
from swki.zeichnung.mittellinien import ECKE_MM
from swki.zeichnung.zeichnen import ZeichnungFehler

DOC_ZEICHNUNG = 3                       # swDocumentTypes_e.swDocDRAWING
OEFFNEN_LESEN = 1 | 2                   # swOpenDocOptions_Silent | swOpenDocOptions_ReadOnly
BLATT, SCHNITT, EINZELHEIT = 1, 2, 3    # swDrawingViewTypes_e
LINEAR = anf.LINEAR                     # swDimensionType_e: Linear, HorLinear, VertLinear
WINKEL = 3                              # swAngularDimension
RADIUS, RADIUS_LINEAR = 5, 14           # swRadialDimension, swRadialLinearDimension
DURCHMESSER, DURCHMESSER_LINEAR = 6, 15  # swDiameterDimension, swDiametricLinearDimension
PRAEFIX, SUFFIX = 1, 2                  # swDimensionTextParts_e
KANTE = 1                               # swSelectType_e.swSelEDGES (angehängte Entität)
SKIZZE_LINIE = 0                        # swSketchSegments_e.swSketchLINE
SF_FELD_A, SF_FELD_C = 8, 2             # swSurfaceFinishSymbolText_e: RoughnessValue1, ProductionMethod
RAHMEN_OBEN = 3                         # swGTolTextParts_e.swGTolTextCalloutAbove
# swTolType_e → Ist-Typ; was hier fehlt (BASIC 1, MIN 5, MAX 6, FITTOLONLY 9, BLOCK 10, General 11), heißt
# „swTolType <n>“ und ist nie „keine“ (sonst ginge eine Toleranz ohne Funktion, Z-TOL-3, verloren)
TOL_TYP = {0: "keine", 2: "bilateral", 3: "grenz", 4: "symmetrisch", 7: "passung", 8: "passung"}
FORMAT_TOL_MM = 1.0


# --- reine Teile -----------------------------------------------------------------------------------------------------

def toleranz(typ: int, minimum: float, maximum: float, bohrung: str, welle: str) -> IstToleranz:
    """IDimensionTolerance → IstToleranz: Abmaße in mm, `unten` mit Vorzeichen (negativ unter dem Nennmaß; ±0,02 ergibt
    symmetrisch 0,02 / −0,02, Review Task 3 M2). Passung: Bohrung (groß) oder Welle (klein); sind beide gesetzt, ist
    die Passung „Bohrung/Welle“ (Gesamtreview M3: sonst gälte „H7/g6“ an einer Bohrung still als „H7“)."""
    art = TOL_TYP.get(typ, f"swTolType {typ}")
    if art == "keine":
        return IstToleranz("keine", None, None, None)
    oben, unten = maximum * 1000, minimum * 1000
    if art == "passung":
        werte = [w.strip() for w in (bohrung or "", welle or "") if w and w.strip()]
        return IstToleranz("passung", "/".join(werte) or None, oben, unten)
    return IstToleranz(art, None, oben, unten)


def _hat_durchmesser(text: str | None) -> bool:
    return "<MOD-DIAM>" in (text or "") or "Ø" in (text or "")


def massart(typ2: int, praefix: str, anzeige: str) -> str | None:
    """Maßart aus `IDisplayDimension.Type2`: linear (mit Ø im Präfix: Durchmesser, wie im Längsschnitt der Buchse),
    Durchmesser, Radius, Winkel; None für alles andere (Koordinaten-, Fasen-, Bogenmaß: nicht prüfbar, Meldung)."""
    if typ2 in LINEAR:
        return "durchmesser" if _hat_durchmesser(praefix) else "laenge"
    if typ2 in (DURCHMESSER, DURCHMESSER_LINEAR):
        return "durchmesser"
    if typ2 in (RADIUS, RADIUS_LINEAR):
        return "radius"
    if typ2 == WINKEL:
        return "winkel"
    return None


def praefix(art: str, text: str, anzeige: str) -> str:
    """Präfix laut Rücklesen. Ein Ø-Maß zeigt das Zeichen auch ohne Präfixtext (Typ Durchmesser): steht es in der
    angezeigten Zahl, kommt es ans Präfix (Plan Task 2: „Präfix oder Teil des Werts laut Rücklesen“)."""
    text = text or ""
    if art == "durchmesser" and not _hat_durchmesser(text) and _hat_durchmesser(anzeige):
        return text + "Ø"
    return text


def anzahl(text: str | None) -> int | None:
    """„n ד über dem Toleranzrahmen (`IGtol.GetText(3)`) → n; sonst None."""
    t = re.match(r"\s*(\d+)\s*[×x]", text or "")
    return int(t.group(1)) if t else None


def format_name(breite_mm: float, hoehe_mm: float) -> str:
    """Blattformat aus der Blattgröße (`blatt.FORMATE`); unbekannt: „B×H“ (die Lesbarkeit meldet es als unbekannt)."""
    for name, (b, h) in FORMATE.items():
        if abs(b - breite_mm) <= FORMAT_TOL_MM and abs(h - hoehe_mm) <= FORMAT_TOL_MM:
            return name
    return f"{breite_mm:.0f}×{hoehe_mm:.0f}"


def massstab_text(zaehler: float, nenner: float) -> str:
    def z(x: float) -> str:
        return f"{x:g}".replace(".", ",")
    return f"{z(zaehler)}:{z(nenner)}"


def rauheitstext(feld_a: str | None, feld_c: str | None) -> str:
    """Anforderung steht im Feld a (`ISFSymbol.GetText(8)`); Text im Feld c (Fertigungsverfahren, `GetText(2)`) macht
    den Text abweichend – Nachtrag Task 4b: „weicht ab“, nie still."""
    a, c = (feld_a or "").strip(), (feld_c or "").strip()
    return " ".join(t for t in (a, f"(Feld c: {c})" if c else "") if t)


def _naechstes_ende(p, k: anf.Kante) -> tuple[float, float]:
    return min((k.a, k.e), key=lambda q: math.dist(p, q))


FASE_VERHAELTNIS = 1.5   # Fasenkante höchstens so lang wie 1,5 × Abstand Ecke–Kantenende (45° an 90°: √2 ≈ 1,41)


def virtuelle_ecke(p: tuple[float, float], kanten: list[anf.Kante]) -> bool:
    """Gedachte scharfe Ecke einer gerundeten oder gefasten Ecke (Live 28.11.: Tasche 50 × 30 mit R4 der SpannplatteZ,
    die geraden Kanten enden 4 mm × Maßstab vor dem Punkt): p liegt auf den Geraden zweier nicht paralleler sichtbarer
    gerader Kanten (`PUNKT_TOL_MM`), hinter ihren zu p nächsten Enden, und eine sichtbare Kante bricht die Ecke
    zwischen diesen Enden (`_bricht_ecke`: tangentialer Bogen oder kurze Fasenkante nahe der Ecke). Wie
    `mittellinien.ohne_kante` („gedachte scharfe Ecke“), aber nur, wo die Ecke wirklich gezeichnet ist – nicht an der
    Spitze eines Trapezes, dessen Deckkante die Seiten verbindet (Review 4b, M1)."""
    tol = anf.PUNKT_TOL_MM
    geraden = [k for k in kanten if not k.kreis and not k.punkt and k.laenge() > 1e-6
               and anf._abstand_gerade(p, k.a, k.e) <= tol]
    for i, k1 in enumerate(geraden):
        for k2 in geraden[i + 1:]:
            d1 = ((k1.e[0] - k1.a[0]) / k1.laenge(), (k1.e[1] - k1.a[1]) / k1.laenge())
            d2 = ((k2.e[0] - k2.a[0]) / k2.laenge(), (k2.e[1] - k2.a[1]) / k2.laenge())
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) < 0.1:      # parallel: kein Schnittpunkt
                continue
            e1, e2 = _naechstes_ende(p, k1), _naechstes_ende(p, k2)
            if not (_hinter_ende(p, k1, e1, tol) and _hinter_ende(p, k2, e2, tol)):
                continue
            if any(b is not k1 and b is not k2 and not b.punkt and _bricht_ecke(b, p, e1, e2, k1, k2, tol)
                   for b in kanten):
                return True
    return False


def _hinter_ende(p, k: anf.Kante, ende, tol: float) -> bool:
    """p liegt auf der Verlängerung der Kante hinter `ende`, nicht auf der Kante selbst."""
    fern = k.e if ende == k.a else k.a
    lang = math.dist(ende, fern)
    return ((p[0] - ende[0]) * (ende[0] - fern[0]) + (p[1] - ende[1]) * (ende[1] - fern[1])) / lang >= -tol


def _bricht_ecke(b: anf.Kante, p, e1, e2, k1: anf.Kante, k2: anf.Kante, tol: float) -> bool:
    """Bricht die Kante b die Ecke p zwischen den Kantenenden e1, e2? Eine Verrundung ist ein Bogen, der beide Geraden
    berührt (Mitte im Abstand r von beiden, `tol`), gleich welcher Größe. Eine Fase ist eine gerade Verbindung nahe
    der Ecke: beide Enden höchstens `mittellinien.ECKE_MM` von p (dieselbe Grenze, mit der das Zeichnen eine gedachte
    scharfe Ecke annimmt) und die Kante höchstens `FASE_VERHAELTNIS` × diesen Abstand lang. Ein Bogen, der nicht
    berührt, bricht keine Ecke. Sonst wäre jede Fläche zwischen zwei Seiten eine „Fase“ (Trapez: Deckkante 80 mm,
    Spitze 89 mm von ihren Enden)."""
    if not _verbindet(b, e1, e2, tol):
        return False
    if b.kreis:
        m, r = b.kreis
        return (abs(anf._abstand_gerade(m, k1.a, k1.e) - r) <= tol
                and abs(anf._abstand_gerade(m, k2.a, k2.e) - r) <= tol)
    weit = max(math.dist(p, e1), math.dist(p, e2))
    return weit <= ECKE_MM + tol and b.laenge() <= FASE_VERHAELTNIS * weit + tol


def _verbindet(b: anf.Kante, e1, e2, tol: float) -> bool:
    return ((math.dist(b.a, e1) <= tol and math.dist(b.e, e2) <= tol)
            or (math.dist(b.a, e2) <= tol and math.dist(b.e, e1) <= tol))


def verdeckt(punkte: list[tuple[float, float]], richtung: str, linien: list[tuple], kanten: list[anf.Kante],
             mittellinien: list[tuple], massstab: float) -> bool:
    """Wahr, wenn ein Bezugspunkt des Maßes weder an einer sichtbaren Kante (`anforderungen_setzen.kante_am_punkt`,
    dieselbe Streckenregel wie beim Umwandeln, mit verlängerter Kante bei einer virtuellen Fasenecke) noch an einer
    gedachten scharfen Ecke (`virtuelle_ecke`) noch auf einer Mittellinie (`PUNKT_TOL_MM`) liegt – Maß an verdeckter
    Kante oder ohne sichtbaren Bezug (Z-ANS-1)."""
    for p, h in zip(punkte, linien):
        if anf.kante_am_punkt(p, richtung, kanten, h, massstab) is not None or virtuelle_ecke(p, kanten):
            continue
        if any(anf._abstand_strecke(p, a, e) <= anf.PUNKT_TOL_MM for a, e in mittellinien):
            continue
        return True
    return False


# --- COM ------------------------------------------------------------------------------------------------------------

def _melde(meldungen: list[str], text: str) -> None:
    if text not in meldungen:
        meldungen.append(text)


def _features(ann) -> tuple[str, ...]:
    """Feature-Namen der Flächen an den angehängten Kanten einer Anmerkung (roh, sortiert); () ohne Kante."""
    namen = set()
    try:
        typen = list(_ruf(ann, "GetAttachedEntityTypes") or ())
        objekte = list(_ruf(ann, "GetAttachedEntities3") or ())
    except Exception:  # noqa: BLE001 – COM: Anmerkung ohne angehängte Entität
        return ()
    for typ, obj in zip(typen, objekte):
        if typ != KANTE or obj is None:
            continue
        try:
            namen |= {_ruf(_ruf(fl, "GetFeature"), "Name") for fl in list(_ruf(obj, "GetTwoAdjacentFaces2") or ())
                      if fl is not None}
        except Exception:  # noqa: BLE001 – COM: Kante ohne Flächen
            continue
    return tuple(sorted(namen))


def _mittellinien(view) -> list[tuple]:
    """Konstruktionslinien der Ansichtsskizze (`zeichnen._mittellinien`: `CreateCenterLine`) in Blatt-mm: Skizze im
    Modellmaßstab relativ zum Ansichtsursprung (Umkehrung von `zeichnen._in_ansicht`)."""
    skizze = _ruf(view, "GetSketch")
    if skizze is None:
        return []
    px, py = list(_ruf(view, "Position"))[:2]
    s = _ruf(view, "ScaleDecimal")
    aus = []
    for sg in list(_ruf(skizze, "GetSketchSegments") or ()):
        try:
            if _ruf(sg, "GetType") != SKIZZE_LINIE or not _ruf(sg, "ConstructionGeometry"):
                continue
            a, e = _ruf(sg, "GetStartPoint2"), _ruf(sg, "GetEndPoint2")
            aus.append((((px + s * a.X) * 1000, (py + s * a.Y) * 1000), ((px + s * e.X) * 1000, (py + s * e.Y) * 1000)))
        except Exception:  # noqa: BLE001 – COM: Segment ohne Punkte
            continue
    return aus


def _beschriftung(view, typ: int) -> str | None:
    """Schnitt: „C-C“ (`IView.GetSection` → `IDrSection.GetLabel`); Einzelheit: der Buchstabe (`IView.GetDetail` →
    `IDetailCircle.GetLabel`); sonst None. Unlesbar: None (Z-ANS-2 meldet den Schnitt ohne Bezeichnung)."""
    try:
        if typ == SCHNITT:
            b = str(_ruf(_ruf(view, "GetSection"), "GetLabel") or "").strip()
            return f"{b}-{b}" if b else None
        if typ == EINZELHEIT:
            return str(_ruf(_ruf(view, "GetDetail"), "GetLabel") or "").strip() or None
    except Exception:  # noqa: BLE001 – COM
        return None
    return None


def _anzeige_text(dd) -> str:
    daten = _ruf(dd, "GetDisplayData")
    return "".join(str(daten.GetTextAtIndex(i)) for i in range(_ruf(daten, "GetTextCount")))


def _masse(view, name: str, kanten: list[anf.Kante], mittel: list[tuple], meldungen: list[str]) -> list[IstMass]:
    aus = []
    massstab = float(_ruf(view, "ScaleDecimal"))
    for dd in _anzeige(view):
        try:
            mname = kurzname(dd)
        except Exception:  # noqa: BLE001 – COM
            mname = "?"
        try:
            typ2 = _ruf(dd, "Type2")
            text_p, text_s = dd.GetText(PRAEFIX) or "", dd.GetText(SUFFIX) or ""
            anzeige = _anzeige_text(dd)
            art = massart(typ2, text_p, anzeige)
            if art is None:
                _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – Maß {mname} (Typ {typ2}) nicht prüfbar")
                continue
            wert = anf.wert_mm(dd)
            if wert is None:
                _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – Maß {mname} ohne Wert")
                continue
            if art == "winkel":
                wert = math.degrees(wert / 1000)
            tol = _ruf(dd.GetDimension2(0), "Tolerance")
            t = toleranz(int(_ruf(tol, "Type")), float(_ruf(tol, "GetMinValue") or 0.0),
                         float(_ruf(tol, "GetMaxValue") or 0.0), str(_ruf(tol, "GetHoleFitValue") or ""),
                         str(_ruf(tol, "GetShaftFitValue") or ""))
            klammer = bool(_ruf(dd, "ShowParenthesis"))
        except Exception as e:  # noqa: BLE001 – COM: nie still weglassen
            _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – Maß {mname} nicht lesbar ({type(e).__name__})")
            continue
        try:
            h = anf.hilfslinien(dd) if typ2 in LINEAR else None
        except Exception:  # noqa: BLE001 – COM: unlesbare Hilfslinien meldet `lage_des_masses`
            h = None
        richtung, punkte, sicht, unlesbar = lage_des_masses(typ2, art, h, kanten, mittel, massstab)
        if unlesbar:
            _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – Hilfslinien des Maßes {mname} nicht lesbar")
        aus.append(IstMass(mname, name, art, wert, praefix(art, text_p, anzeige), text_s, klammer, t, richtung, punkte,
                           sicht))
    return aus


def lage_des_masses(typ2: int, art: str, h, kanten: list[anf.Kante], mittel: list[tuple],
                    massstab: float) -> tuple[str | None, tuple | None, bool | None, bool]:
    """Richtung, Bezugspunkte (nur Längen, für Z-UEB-1), `verdeckt` und „unlesbar“ eines Maßes. `verdeckt` gibt es für
    jedes lineare Maß (`LINEAR`, auch Ø im Längsschnitt); sind seine Hilfslinien unlesbar (`h` None), ist es None und
    unlesbar wahr – der Aufrufer meldet es (Review 4b, M3: sonst bliebe ein lineares Ø-Maß still ungeprüft). Ø-, R- und
    Winkelmaße haben keine Hilfslinien zweier Kanten: None, nicht unlesbar."""
    if typ2 not in LINEAR:
        return None, None, None, False
    if h is None or len(h[2]) != 2:
        return None, None, None, True
    sicht = verdeckt(h[2], h[0], h[1], kanten, mittel, massstab)
    if art == "laenge":
        return h[0], (tuple(h[2][0]), tuple(h[2][1])), sicht, False
    return None, None, sicht, False


def _lage(ann) -> tuple[float, float] | None:
    """`IAnnotation.GetPosition` in Blatt-mm (Notiz: linke obere Ecke des Textkastens); None, wenn nicht lesbar – die
    Prüfung der Sammelangaben nennt die Lage dann „nicht geprüft“ (Gesamtreview c)."""
    try:
        p = list(_ruf(ann, "GetPosition") or ())
    except Exception:  # noqa: BLE001 – COM
        return None
    return (round(p[0] * 1000, 3), round(p[1] * 1000, 3)) if len(p) >= 2 else None


def _notiz(n, name: str) -> IstAngabe | None:
    text = str(_ruf(n, "GetText") or "")
    if not text.strip():
        return None
    ann = _ruf(n, "GetAnnotation")
    return IstAngabe("hinweis", name, text, None, None, (), None, None, _features(ann), _lage(ann))


def _rahmen(g, name: str) -> IstAngabe:
    werte = [str(w or "") for w in list(g.GetFrameValues(1) or ())] + ["", "", "", "", ""]
    symbol = (list(g.GetFrameSymbols2(1) or ()) or [""])[0] or None
    bezug = tuple(w.strip() for w in werte[2:5] if w.strip())
    return IstAngabe("form_lage", name, f"{symbol or ''} {werte[0]}".strip(), symbol, werte[0], bezug, None,
                     anzahl(g.GetText(RAHMEN_OBEN)), _features(_ruf(g, "GetAnnotation")))


def _bezugsdreieck(d, name: str) -> IstAngabe:
    label = str(_ruf(d, "GetLabel") or "")
    return IstAngabe("bezug", name, label, None, None, (label,) if label else (), None, None,
                     _features(_ruf(d, "GetAnnotation")))


def _rauheitssymbol(s, name: str) -> IstAngabe:
    """Rauheit mit Features der angehängten Kante und Lage (Spitze; Rauheitsfeld, Nutzer 28.11.2026)."""
    ann = _ruf(s, "GetAnnotation")
    return IstAngabe("rauheit", name, rauheitstext(s.GetText(SF_FELD_A), s.GetText(SF_FELD_C)), None, None, (),
                     None, None, _features(ann), _lage(ann))


# (Wort für Meldungen, erstes, nächstes, Leser) je verketteter Anmerkungsart der Ansicht
_KETTEN = (("Toleranzrahmen", "GetFirstGTOL", "GetNextGTOL", _rahmen),
           ("Bezugsdreieck", "GetFirstDatumTag", "GetNext", _bezugsdreieck),
           ("Rauheitssymbol", "GetFirstSFSymbol", "GetNext", _rauheitssymbol))
_ANFORDERUNG = ("rauheit", "form_lage", "bezug")   # Anforderungen hängen an einer Kante (Merkmal über ihre Flächen)


def _angaben(view, name: str, meldungen: list[str], blatt: bool = False) -> list[IstAngabe]:
    """Notizen, Toleranzrahmen, Bezugsdreiecke, Rauheitssymbole der Ansicht (auch des Blatts: Sammelangaben).
    Nie still (Review 4b): eine Anforderung ohne angehängte Kante – Ausnahme beim Lesen, Fläche, Ecke oder Silhouette
    statt Kante – meldet RUECKLESEN_UNVOLLSTAENDIG (ohne Kante kein Merkmal, I2); ein Hinweis ohne Anhängung
    (Sammelangabe) bleibt still, ebenso ein Rauheitssymbol ohne Anhängung auf dem Blatt (`blatt`; Rauheitsfeld, Nutzer
    28.11.2026: ob es im Feld steht, entscheidet `pruefen.sammelrauheit_symbole`, sonst ist es ein Mangel Z-TOL-4).
    Ein COM-Fehler an einer Anmerkung ist eine Meldung, die übrigen werden gelesen (M4)."""
    aus = []

    def eins(lies, x, wort: str) -> None:
        try:
            a = lies(x, name)
        except Exception as e:  # noqa: BLE001 – COM: nie still weglassen
            _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – {wort} nicht lesbar ({type(e).__name__})")
            return
        if a is None:
            return
        if a.art in _ANFORDERUNG and not a.features and not (blatt and a.art == "rauheit"):
            _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – {a.art} „{a.text}“ ohne angehängte Kante")
        aus.append(a)

    try:
        notizen = list(_ruf(view, "GetNotes") or ())
    except Exception as e:  # noqa: BLE001 – COM
        _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – Notizen nicht lesbar ({type(e).__name__})")
        notizen = []
    for n in notizen:
        eins(_notiz, n, "Notiz")
    for wort, erstes, naechstes, lies in _KETTEN:
        try:
            x = _ruf(view, erstes)
        except Exception as e:  # noqa: BLE001 – COM
            _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – {wort} nicht lesbar ({type(e).__name__})")
            continue
        while x is not None:
            eins(lies, x, wort)
            try:
                x = _ruf(x, naechstes)
            except Exception as e:  # noqa: BLE001 – COM: die Kette bricht ab, gemeldet
                _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – {wort} nicht lesbar ({type(e).__name__})")
                break
    return aus


def _lies(app, drw, rollen: dict[str, str]) -> Ist:
    mu = mathutil(app)
    meldungen: list[str] = []
    blatt = _ruf(drw, "GetCurrentSheet")
    eig = list(_ruf(blatt, "GetProperties2"))
    format_ = format_name(eig[5] * 1000, eig[6] * 1000)
    massstab = massstab_text(eig[2], eig[3])
    namen = [str(n) for n in list(_ruf(drw, "GetSheetNames") or ())]
    aktuell = str(_ruf(blatt, "GetName"))
    if len(namen) > 1:   # `GetFirstView` liefert nur die Ansichten des aktuellen Blatts (Review 4b, M4)
        _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {aktuell} – Zeichnung hat {len(namen)} Blätter, gelesen nur "
                          "das aktuelle")
    # Eigenschaften nur aus der Zeichnung (Get6). „Blatt“ setzt der Rückleser nicht selbst (Review 4b, M5): den
    # Blattzähler füllt SolidWorks; fehlt die Eigenschaft, prüft `pruefe_schriftfeld` das Feld nicht
    eigenschaften = {k: str(v) for k, v in lies_eigenschaften(drw).items()}
    rolle_von = {name: rolle for rolle, name in rollen.items()}
    ansichten, masse, angaben = [], [], []
    v = _ruf(drw, "GetFirstView")
    while v is not None:
        name, typ = str(_ruf(v, "GetName2")), int(_ruf(v, "Type"))
        angaben += _angaben(v, name, meldungen, blatt=typ == BLATT)
        if typ != BLATT:
            zaehler, nenner = list(_ruf(v, "ScaleRatio"))[:2]
            art = {SCHNITT: "schnitt", EINZELHEIT: "einzelheit"}.get(typ, "ansicht")
            ansichten.append(IstAnsicht(name, rolle_von.get(name), art, massstab_text(zaehler, nenner),
                                        _beschriftung(v, typ)))
            masse += _masse(v, name, anf.sichtbare_kanten(mu, v), _mittellinien(v), meldungen)
        v = _ruf(v, "GetNextView")
    for rolle, name in rollen.items():
        if not any(a.name == name for a in ansichten):
            _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: Ansicht {rolle} ({name}) aus der Übergabe nicht in der Zeichnung")
    return Ist(format_, massstab, tuple(ansichten), tuple(masse), tuple(angaben), eigenschaften, "", tuple(meldungen))


def _pfad(p) -> str:
    """Vergleichsform eines Dokumentpfads: absolut, Groß-/Kleinschreibung und Trenner wie Windows (`normcase`); ein
    ungespeichertes Dokument (leerer Pfad) bleibt leer."""
    p = str(p or "")
    return os.path.normcase(os.path.abspath(p)) if p else ""


def _offen(app) -> list[tuple[str, str, object]]:
    """Offene Dokumente als (Vergleichspfad, Pfad, Dokument)."""
    aus = []
    for d in list(app.GetDocuments or ()):
        roh = str(d.GetPathName or "")
        aus.append((_pfad(roh), roh, d))
    return aus


def _oeffne(app, slddrw: Path, vorher: set[str], eigene: list) -> object:
    """`OpenDoc6` schreibgeschützt; `eigene` bekommt, was dieses Öffnen neu geladen hat (Zeichnung und Teil) – auch wenn
    das Öffnen scheitert, damit `_schliesse` es wieder schließt."""
    fehler, warnungen = byref_long(), byref_long()
    try:
        drw = app.OpenDoc6(str(slddrw), DOC_ZEICHNUNG, OEFFNEN_LESEN, "", fehler, warnungen)
    except Exception as e:  # noqa: BLE001 – COM
        raise ZeichnungFehler("ZEICHNUNG_NICHT_GEOEFFNET",
                              f"{slddrw.name} ließ sich nicht öffnen ({type(e).__name__}: {e})") from e
    finally:
        eigene += [(p, roh, d) for p, roh, d in _offen(app) if p and p not in vorher]
    if drw is None:
        raise ZeichnungFehler("ZEICHNUNG_NICHT_GEOEFFNET", f"{slddrw.name} ließ sich nicht öffnen (Fehler {fehler.value})")
    return drw


def _schliesse(app, eigene: list, vorher: set[str]) -> list[str]:
    """Schließt die selbst geladenen Dokumente ohne Speichern, die Zeichnung zuerst (das Teil schließt SolidWorks oft
    mit ihr). Danach wird nachgesehen, nie still: was davon noch offen ist, und was erst während des Lesens dazukam
    (etwa ein Teil, das SolidWorks spät nachlädt, oder ein Dokument eines anderen) – das bleibt offen, weil es nicht
    sicher selbst geladen ist, und kommt als Meldung zurück."""
    fehler = {}
    for p, roh, d in sorted(eigene, key=lambda x: not x[0].endswith(".slddrw")):
        try:
            sw.schliesse(app, d)
        except Exception as e:  # noqa: BLE001 – COM: geprüft wird unten, ob es noch offen ist
            fehler[p] = type(e).__name__
    try:
        offen = _offen(app)
    except Exception as e:  # noqa: BLE001 – COM
        return [f"RUECKLESEN_NICHT_GESCHLOSSEN: offene Dokumente nicht lesbar ({type(e).__name__})"]
    pfade, selbst = {p for p, _, _ in offen}, {p for p, _, _ in eigene}
    aus = [f"RUECKLESEN_NICHT_GESCHLOSSEN: {Path(roh).name} blieb in SolidWorks offen"
           + (f" ({fehler[p]})" if p in fehler else "") for p, roh, _ in eigene if p in pfade]
    aus += [f"RUECKLESEN_NICHT_GESCHLOSSEN: {Path(roh).name} kam während des Lesens dazu – offen gelassen (nicht "
            "sicher selbst geladen)" for p, roh, _ in offen if p and p not in vorher and p not in selbst]
    return aus


def lies_zeichnung(slddrw: Path, rollen: dict[str, str], app=None) -> Ist:
    """Zeichnung schreibgeschützt öffnen, als Ist lesen, ohne Speichern schließen. `rollen`: Rolle → Ansichtsname aus
    der Übergabe (`zeichnung.json`, `ansichten`). Ist die Zeichnung schon offen (beim Nutzer), bricht der Rückleser ab,
    statt sie anzufassen. Geschlossen wird nur, was `OpenDoc6` neu geladen hat (Review 4b, M4: kein Dokument, das
    während des Lesens jemand anderes geöffnet hat), auch wenn Öffnen oder Lesen scheitert; was offen bleibt, meldet
    RUECKLESEN_NICHT_GESCHLOSSEN. Ein COM-Fehler beim Lesen wird `ZeichnungFehler` RUECKLESEN_FEHLER. Pfade werden
    nach `_pfad` verglichen. `sha256_slddrw` setzt der Aufrufer."""
    app = app or verbinde(lade_rechner().sw_jahr)
    vorher = {p for p, _, _ in _offen(app)}
    if _pfad(slddrw) in vorher:
        raise ZeichnungFehler("ZEICHNUNG_SCHON_OFFEN", f"{slddrw.name} ist in SolidWorks offen – bitte schließen")
    eigene: list = []
    try:
        drw = _oeffne(app, slddrw, vorher, eigene)
        try:
            ist = _lies(app, drw, rollen)
        except ZeichnungFehler:
            raise
        except Exception as e:  # noqa: BLE001 – COM: nie roh nach oben
            raise ZeichnungFehler("RUECKLESEN_FEHLER",
                                  f"{slddrw.name}: Rücklesen abgebrochen ({type(e).__name__}: {e})") from e
    finally:
        geblieben = _schliesse(app, eigene, vorher)
    return replace(ist, meldungen=ist.meldungen + tuple(geblieben)) if geblieben else ist
