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
import re
from pathlib import Path

from swki.compiler import sw
from swki.compiler.eigenschaften import lies_eigenschaften
from swki.compiler.sw import mathutil
from swki.konfig import lade_rechner, lade_standard
from swki.verbindung import byref_long, verbinde
from swki.zeichnung import anforderungen_setzen as anf
from swki.zeichnung.bemassen import _anzeige, _ruf, kurzname
from swki.zeichnung.blatt import FORMATE
from swki.zeichnung.ist import Ist, IstAngabe, IstAnsicht, IstMass, IstToleranz
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
    symmetrisch 0,02 / −0,02, Review Task 3 M2). Passung: Bohrung (groß) oder Welle (klein)."""
    art = TOL_TYP.get(typ, f"swTolType {typ}")
    if art == "keine":
        return IstToleranz("keine", None, None, None)
    oben, unten = maximum * 1000, minimum * 1000
    if art == "passung":
        return IstToleranz("passung", (bohrung or welle or "").strip() or None, oben, unten)
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


def virtuelle_ecke(p: tuple[float, float], kanten: list[anf.Kante]) -> bool:
    """Gedachte scharfe Ecke einer gerundeten oder gefasten Ecke (Live 28.11.: Tasche 50 × 30 mit R4 der SpannplatteZ,
    die geraden Kanten enden 4 mm × Maßstab vor dem Punkt): p liegt auf den Geraden zweier nicht paralleler sichtbarer
    gerader Kanten (`PUNKT_TOL_MM`), und eine sichtbare Kante (Bogen oder Fasenkante) verbindet ihre zu p nächsten
    Enden. Wie `mittellinien.ohne_kante` („gedachte scharfe Ecke“), aber nur, wo die Ecke wirklich gezeichnet ist."""
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
            if any(b is not k1 and b is not k2 and not b.punkt and _verbindet(b, e1, e2, tol) for b in kanten):
                return True
    return False


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
        richtung = punkte = None
        sicht = None
        h = anf.hilfslinien(dd) if typ2 in LINEAR else None
        if h is not None and len(h[2]) == 2:
            sicht = verdeckt(h[2], h[0], h[1], kanten, mittel, massstab)
            if art == "laenge":
                richtung, punkte = h[0], (tuple(h[2][0]), tuple(h[2][1]))
        elif art == "laenge":
            _melde(meldungen, f"RUECKLESEN_UNVOLLSTAENDIG: {name} – Hilfslinien des Maßes {mname} nicht lesbar")
        aus.append(IstMass(mname, name, art, wert, praefix(art, text_p, anzeige), text_s, klammer, t, richtung, punkte,
                           sicht))
    return aus


def _angaben(view, name: str) -> list[IstAngabe]:
    """Notizen, Toleranzrahmen, Bezugsdreiecke, Rauheitssymbole der Ansicht (auch des Blatts: Sammelangaben)."""
    aus = []
    for n in list(_ruf(view, "GetNotes") or ()):
        text = str(_ruf(n, "GetText") or "")
        if text.strip():
            aus.append(IstAngabe("hinweis", name, text, None, None, (), None, None, _features(_ruf(n, "GetAnnotation"))))
    g = _ruf(view, "GetFirstGTOL")
    while g is not None:
        werte = [str(w or "") for w in list(g.GetFrameValues(1) or ())] + ["", "", "", "", ""]
        symbol = (list(g.GetFrameSymbols2(1) or ()) or [""])[0] or None
        bezug = tuple(w.strip() for w in werte[2:5] if w.strip())
        aus.append(IstAngabe("form_lage", name, f"{symbol or ''} {werte[0]}".strip(), symbol, werte[0], bezug, None,
                             anzahl(g.GetText(RAHMEN_OBEN)), _features(_ruf(g, "GetAnnotation"))))
        g = _ruf(g, "GetNextGTOL")
    d = _ruf(view, "GetFirstDatumTag")
    while d is not None:
        label = str(_ruf(d, "GetLabel") or "")
        aus.append(IstAngabe("bezug", name, label, None, None, (label,) if label else (), None, None,
                             _features(_ruf(d, "GetAnnotation"))))
        d = _ruf(d, "GetNext")
    s = _ruf(view, "GetFirstSFSymbol")
    while s is not None:
        aus.append(IstAngabe("rauheit", name, rauheitstext(s.GetText(SF_FELD_A), s.GetText(SF_FELD_C)), None, None, (),
                             None, None, _features(_ruf(s, "GetAnnotation"))))
        s = _ruf(s, "GetNext")
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
    eigenschaften = {k: str(v) for k, v in lies_eigenschaften(drw).items()}
    feld = ((lade_standard().get("zeichnung") or {}).get("schriftfeld") or {}).get("blatt") or "Blatt"
    eigenschaften[feld] = f"{namen.index(aktuell) + 1 if aktuell in namen else 1}/{max(len(namen), 1)}"
    rolle_von = {name: rolle for rolle, name in rollen.items()}
    ansichten, masse, angaben = [], [], []
    v = _ruf(drw, "GetFirstView")
    while v is not None:
        name, typ = str(_ruf(v, "GetName2")), int(_ruf(v, "Type"))
        angaben += _angaben(v, name)
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


def _offen(app) -> set[str]:
    return {str(d.GetPathName).lower() for d in list(app.GetDocuments or ())}


def lies_zeichnung(slddrw: Path, rollen: dict[str, str], app=None) -> Ist:
    """Zeichnung schreibgeschützt öffnen, als Ist lesen, ohne Speichern schließen. `rollen`: Rolle → Ansichtsname aus
    der Übergabe (`zeichnung.json`, `ansichten`). Ist die Zeichnung schon offen (beim Nutzer), bricht der Rückleser ab,
    statt sie anzufassen. Schließt nur Dokumente, die dieses Öffnen neu geladen hat. `sha256_slddrw` setzt der Aufrufer."""
    app = app or verbinde(lade_rechner().sw_jahr)
    vorher = _offen(app)
    if str(slddrw).lower() in vorher:
        raise ZeichnungFehler("ZEICHNUNG_SCHON_OFFEN", f"{slddrw.name} ist in SolidWorks offen – bitte schließen")
    fehler, warnungen = byref_long(), byref_long()
    drw = app.OpenDoc6(str(slddrw), DOC_ZEICHNUNG, OEFFNEN_LESEN, "", fehler, warnungen)
    try:
        if drw is None:
            raise ZeichnungFehler("ZEICHNUNG_NICHT_GEOEFFNET", f"{slddrw.name} ließ sich nicht öffnen (Fehler {fehler.value})")
        return _lies(app, drw, rollen)
    finally:
        neu = [d for d in list(app.GetDocuments or ()) if str(d.GetPathName).lower() not in vorher]
        for d in sorted(neu, key=lambda d: not str(d.GetPathName).lower().endswith(".slddrw")):  # Zeichnung zuerst
            try:
                sw.schliesse(app, d)
            except Exception:  # noqa: BLE001 – COM: das Teil schloss SolidWorks schon mit der Zeichnung
                pass
