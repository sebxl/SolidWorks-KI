"""Anforderungen in die Zeichnung (Z1.3 Stufe 4 Task 5): Toleranzen und Textzusätze an Zeichnungsmaßen, Rauheit,
Bezüge, Form-/Lagetoleranzen, Sammelangaben.

Spike Stufe 4 (docs/zeichnungsableitung/spike-z1.md, Nachtrag Stufe 4) ist verbindlich:
- Toleranz und Textzusatz an einem eingefügten Modellmaß gehen beim Wiederöffnen der SLDDRW verloren (sie hängen am
  Maß des Teils, das nie gespeichert wird). Sie stehen deshalb nur an **Zeichnungsmaßen**: `dauerhaft_machen` setzt
  das Maß über die sichtbaren Kanten an seinen Bezugspunkten neu (`AddDimension2`) und löscht das Modellmaß.
- Abmaße an Zeichnungsmaßen über `IDimensionTolerance.SetValues` (SetValues2 scheitert dort); Passung Typ 7 mit
  `SetFitValues`, `FitDisplayStyle` bleibt 3.
- Ⓔ an Maßen als Symbol `<MOD-EP>` (das Unicode-Zeichen lässt den ganzen Maßtext verschwinden).
- Rauheitstext an Platz 3 (ProdMethod) von `InsertSurfaceFinishSymbol3`; jede Anmerkung bekommt ihre Lage über
  `IAnnotation.SetPosition2`; parameterlose Methoden über `_ruf`.

API (swki api methode, SW 2025): IModelDoc2.AddDimension2 (3), InsertGtol (0), InsertDatumTag2 (0), InsertNote (1);
IView.SelectEntity (2), GetVisibleEntities2 (2, 2014); IDimension.GetSystemValue3 (2, 2004), GetSystemValue2 (1),
Tolerance; IDimensionTolerance.Type, SetValues (2, 2006), SetFitValues (2, 2006), FitDisplayStyle;
IDisplayDimension.SetText/GetText (2/1); IModelDocExtension.InsertSurfaceFinishSymbol3 (14, 2005; swSFMachining_Req = 1,
swSTRAIGHT = 1, swCLOSED_ARROWHEAD = 1); IGtol.SetFrameSymbols2 (9), SetFrameValues2 (6, 2016), GetAnnotation;
IDatumTag.SetLabel (1), GetAnnotation; ISFSymbol.GetAnnotation; IAnnotation.SetPosition2 (3, 2014), GetPosition;
Nachbesserung C: IView.GetFaceHatches (0, 2003), IFaceHatch.Face (2003), IFace2.GetEdges (0, 2001).
Runde D: IView.Type (swDrawingViewTypes_e, swDrawingSectionView = 2), ISelectionMgr.GetSelectedObject6 (2),
IEdge.GetCurveParams3 (0) zur Prüfung der am Punkt gewählten Kante; kein IVertex mehr (Eckpunkte liegen live 54–89 mm
neben ihrem Ort).
Rauheitsfeld (Nutzer 28.11.2026): InsertSurfaceFinishSymbol3 mit swSFBasic = 0, swNO_LEADER = 0, ISFSymbol.SetText (2),
IModelDoc2.SketchManager (2005) → ISketchManager.AddToDB (2008), CreateCornerRectangle (6, 2008), ISketchSegment.Color,
ISheet.GetProperties2
(Maßstab; eine Blattskizze folgt ihm, spikes/z1_diag_rauheitsfeld.py).
"""

import math
from dataclasses import dataclass, field, replace

from swki.verbindung import callout_leer, r8_array
from swki.zeichnung.angaben import _enthalten, bohrbilder, hinweis_lagen_bewertet
from swki.zeichnung.bemassen import _anzeige, _loesche, _ruf, kurzname
from swki.zeichnung.blatt import SCHRIFTFELD_MM, zeichenfeld
from swki.zeichnung.lesbarkeit import _schneidet
from swki.zeichnung.massplan import Mass
from swki.zeichnung.sammelfeld import (SAMMEL_OBERKANTE_MM, SAMMEL_ZEICHEN, SAMMEL_ZEILENABSTAND_MM,  # noqa: F401
                                       Rauheitsfeld, rauheitsfeld, sammel_aufteilung, sammel_zeilenzahl, sammelband,
                                       sammelzeilen_lage, umbrechen)
from swki.zeichnung.toleranzangaben import (SAMMEL_RAUHEIT, SAMMEL_RAUHEIT_FELD, SAMMEL_RAUHEIT_HINWEIS_ZEILEN,
                                            Toleranz)

TOL_BILAT, TOL_SYMMETRISCH, TOL_PASSUNG = 2, 4, 7   # swTolType_e
PASSUNG_EINZEILIG = 3                               # FitDisplayStyle (Spike e: „200,00 H7“ in einer Zeile)
HUELLE = "<MOD-EP>"                                 # Symboldatei gtol97.sym, „Encompassing“ (Spike f)
PRAEFIX_TEXT, SUFFIX_TEXT = 1, 2                    # swDimensionTextParts_e
EINE_KONFIG = 1                                     # swInConfigurationOpts_e.swThisConfiguration
KANTE, SILHOUETTE = 1, 4                            # swViewEntityType_e (Eckpunkte = 2: nicht mehr, Runde D I2)
SCHNITTANSICHT = 2                                  # swDrawingViewTypes_e.swDrawingSectionView
SF_BEARBEITET, FUEHRUNG_GERADE, PFEIL_GESCHLOSSEN = 1, 1, 1  # swSFSymType_e, swLeaderStyle_e, swArrowStyle_e
LINEAR = (2, 11, 12)                                # swDimensionType_e: Linear, HorLinear, VertLinear
RUND = (5, 6, 14, 15)                               # swDimensionType_e: Radial, Diameter, RadialLinear, DiametricLinear
PUNKT_TOL_MM = 0.1                                  # Bezugspunkt liegt auf der Kante / in der Kreismitte
KANTE_VERLAENGERT_MM = 1.0                          # Bezugspunkt höchstens so weit hinter dem Kantenende, in Modell-mm
#                                                     (× Maßstab der Ansicht): virtuelle Ecke einer Fase – Buchse f3
#                                                     (0,5 × 45°, 1:1) setzt 0,5 mm über der Bohrungskante an
WERT_TOL_MM = 0.005                                 # neues Zeichnungsmaß misst dasselbe wie das Modellmaß
# Runde D (I2): das neue Zeichnungsmaß setzt dort an, wo das Modellmaß ansetzte – in Messrichtung auf
# `BEZUG_MESS_TOL_MM`, entlang der Hilfslinie auf `BEZUG_ENTLANG_TOL_MM` (Lücke, virtuelle Fasenecke, Ansatz hinter
# einer Kreismitte 3,5–4,25 mm; ein fremder Eckpunkt lag 54–89 mm daneben)
BEZUG_MESS_TOL_MM, BEZUG_ENTLANG_TOL_MM = 0.15, 5.0
HILFSLINIE_LUECKE_MM = 1.0                          # wie zeichnen.HILFSLINIE_LUECKE_MM
HILFSLINIE_KREIS_MM = 6.0                           # Hilfslinie an einer Kreismitte beginnt höchstens so weit hinter dem Kreis
# Größe (Breite, Höhe) und Versatz (Mitte − Bezugspunkt der Annotation) in Blatt-mm, live gemessen 27.11. (Text 3,5 mm):
# Rauheit: Bezugspunkt = Spitze des Symbols, Symbol und Text rechts darüber (Breite = Grundbreite + Text);
# Rahmen: Bezugspunkt = linke obere Ecke; Bezug: Bezugspunkt = Ansatz der Hinweislinie am Kasten
# Rauheit nach ISO 1302:2002 mit Text im Feld a (Spike g), am PDF gemessen 28.11. (Nachbesserung C, „Ra 1,6“ der
# SpannplatteZ, Schnitt A-A): Bezugspunkt = Spitze; Dreieck bis 2,9 mm links der Spitze, waagrechter Strich 10,0 mm
# über ihr, der Text steht unter dem Strich, seine Box reicht bis 11,0 mm; Breite 23,7 mm = 9,9 mm + 2,3 mm je
# Zeichen. Geschätzt wird mit `ZEICHEN_MM` = 2,5 je Zeichen, die Grundbreite so, dass „Ra 1,6“ 23,7 mm ergibt
# (die frühere Angabe „live nachgemessen“ für 8,5 × 10 mm stimmte nicht: Höhe 11 statt 10 mm, Spitze 2,9 statt 2,6 mm)
GROESSE_RAUHEIT, VERSATZ_RAUHEIT = (8.7, 11.0), (-2.9, 5.5)
SF_TEXT_FELD_A = 8                                  # swSurfaceFinishSymbolText_e.swSFSymbolRoughnessValue1
RAHMEN_TEXT_OBEN, RAHMEN_TEXT_OBEN_MM = 3, 5.5      # swGTolTextParts_e.swGTolTextCalloutAbove; Höhe der Zeile
ABSTAND_KANTE_MM = 3.0                              # Symbol/Rahmen/Kasten so weit von sichtbaren Kanten (Review C2)
ANSATZ_ABSTAND_MM = 4.0                             # zwei Hinweislinien setzen nicht näher beieinander an
ANSATZ_TEILUNG = (0.5, 0.35, 0.65, 0.2, 0.8, 0.1, 0.9)  # Ansatz auf einer geraden Kante (Anteil der Länge)
KREIS_WINKEL = (45, 135, 315, 225)                  # Ansatz auf einem Kreis (Grad)
GROESSE_BEZUG = (7.0, 7.0)
RAHMEN_HOEHE_MM, RAHMEN_ZELLE_MM, ZEICHEN_MM = 7.0, 7.0, 2.5
NAEHE_ANMERKUNG_MM = 4.0                            # PDF-Befund gehört zur Anmerkung, wenn er ihr Rechteck so nah trifft
BEZUG_TEILUNG = (0.5, 0.3, 0.7, 0.15, 0.85)         # Lagen des Bezugskastens entlang der Kante
ANM_RICHTUNGEN_GRAD = (45, 135, 315, 225, 0, 180, 90, 270)  # Lagen von Rauheit und Rahmen um den Anker
ANM_ABSTAENDE_MM = (10.0, 15.0, 22.0, 30.0, 40.0)
BEZUG_ABSTAENDE_MM = (6.0, 10.0, 15.0)              # Abstand Kante – Kasten
ORT_MIN_MM = 6.0                                    # gleichwertige Kante derselben Fläche mindestens so lang
BEZUG_VERLAENGERUNG_MM = (3.0, 7.0, 12.0)           # Kasten so weit über das Kantenende hinaus (ISO 5459, Verlängerung)
JENSEITS_STREIFEN_MM, JENSEITS_LUECKE_MM = 15.0, 4.0  # Maßlinien in diesem Streifen zählen; so weit dahinter (`_jenseits`)
JENSEITS_MAX_MM = 50.0                              # Runde D (M4): weiter weg liegen Maßlinien anderer Ansichten
VERTIEFT = ("schnitt", "bohrung", "normbohrung")    # Merkmale mit Öffnung: Hinweislinie darf über ihren Rand (`offen`)
KONZENTRISCH_MM, OFFEN_RAND_MM = 0.3, 0.5           # `Anmerkung._offen_hier`: Kreise derselben Mitte; Ränder im Feld
SCHRAFFUR_BOGEN_STUECKE = 12
SF_GRUND, OHNE_FUEHRUNG = 0, 0                      # swSFSymType_e.swSFBasic, swLeaderStyle_e.swNO_LEADER
SCHWARZ = 0                                         # ISketchSegment.Color (COLORREF 0x00BBGGRR)


def wert_mm(dd) -> float | None:
    """Wert eines Anzeigemaßes in mm: Modellmaße über `GetSystemValue3`, Zeichnungsmaße liefern dort None (Spike c)
    → `GetSystemValue2("")`."""
    dim = dd.GetDimension2(0)
    try:
        w = dim.GetSystemValue3(EINE_KONFIG, None)
    except Exception:  # noqa: BLE001 – COM
        w = None
    if w is not None:
        w = list(w)[0] if isinstance(w, (list, tuple)) else w
        if w is not None:
            return w * 1000
    w = dim.GetSystemValue2("")
    return None if w is None else w * 1000


# --- sichtbare Kanten mit Modellkoordinaten --------------------------------------------------------------------------


@dataclass
class Kante:
    obj: object
    a: tuple[float, float]                 # Anfang auf dem Blatt (mm)
    e: tuple[float, float]                 # Ende auf dem Blatt (mm)
    a_m: tuple[float, float, float]        # Anfang im Modell (mm)
    e_m: tuple[float, float, float]
    kreis: tuple | None = None             # (Mitte Blatt-mm, Radius Blatt-mm) oder None (Gerade, Eckpunkt)
    features: set = field(default_factory=set)
    punkt: bool = False                    # Kantenende ohne Objekt (Wahl am Blattpunkt, `waehle_punkt`)
    radius_mm: float | None = None         # Kreis: Radius im Modell (mm)

    def laenge(self) -> float:
        return math.dist(self.a, self.e)


def sichtbare_kanten(mu, view) -> list[Kante]:
    """Sichtbare Kanten der Ansicht (Kanten, Silhouetten) mit Blatt- und Modellkoordinaten und den Features ihrer
    Nachbarflächen (`IFace2.GetFeature`; Silhouetten ohne). Schnittansichten liefern die Kanten der Schnittflächen mit
    (Feature „Schnitt1“, Live 27.11.). Keine Eckpunkte (Runde D, I2: `IVertex.GetPoint` über `ModelToViewTransform`
    landet 54–89 mm neben dem Ort, Spike Stufe 4 i)."""
    t = _ruf(view, "ModelToViewTransform")
    s = _ruf(view, "ScaleDecimal")

    def blatt(p_m):
        q = mu.CreatePoint(r8_array(list(p_m))).MultiplyTransform(t).ArrayData
        return q[0] * 1000, q[1] * 1000

    aus = []
    for typ in (KANTE, SILHOUETTE):
        for k in list(view.GetVisibleEntities2(callout_leer(), typ) or ()):
            try:
                c = _ruf(k, "GetCurve")
                kreis = None
                if typ == KANTE:
                    cp = _ruf(k, "GetCurveParams3")
                    a_m, e_m = tuple(_ruf(cp, "StartPoint"))[:3], tuple(_ruf(cp, "EndPoint"))[:3]
                    namen = {_ruf(_ruf(fl, "GetFeature"), "Name") for fl in list(_ruf(k, "GetTwoAdjacentFaces2") or ())
                             if fl is not None}
                else:
                    if not _ruf(c, "IsLine"):
                        continue
                    px, py, pz, dx, dy, dz = list(_ruf(c, "LineParams"))[:6]
                    a_m, e_m, namen = (px, py, pz), (px + dx * 1e-3, py + dy * 1e-3, pz + dz * 1e-3), set()
                if _ruf(c, "IsCircle"):
                    cx, cy, cz, *_, r = list(_ruf(c, "CircleParams"))
                    kreis = (blatt((cx, cy, cz)), r * 1000 * s)
                elif not _ruf(c, "IsLine"):
                    continue
            except Exception:  # noqa: BLE001 – COM: Kante ohne Kurve/Flächen überspringen
                continue
            aus.append(Kante(k, blatt(a_m), blatt(e_m), tuple(x * 1000 for x in a_m), tuple(x * 1000 for x in e_m),
                             kreis, namen, radius_mm=r * 1000 if kreis else None))
    return aus


def _abstand_gerade(p, a, e) -> float:
    """Abstand des Punkts p von der Geraden durch a, e (Blatt-mm)."""
    dx, dy = e[0] - a[0], e[1] - a[1]
    n = math.hypot(dx, dy)
    if n < 1e-9:
        return math.dist(p, a)
    return abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / n


def _abstand_strecke(p, a, e) -> float:
    dx, dy = e[0] - a[0], e[1] - a[1]
    n2 = dx * dx + dy * dy
    if n2 < 1e-12:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n2))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def _kreis_der_hilfslinie(hilfslinie: tuple, kanten: list[Kante]) -> Kante | None:
    """Kreiskante, deren Mitte das Maß bemaßt: Die Mitte liegt auf der Geraden der Hilfslinie, kurz vor ihrem Anfang
    (Live 27.11.: D3@m1 beginnt 3,5 mm, D1@st_positionen 4,25 mm hinter der Bohrungsmitte, bei 1:2 und 1:5 gleich –
    die Lücke hängt nicht am Kreis). Die nächste solche Mitte; unter ihren Kreisen der größte."""
    a, e = hilfslinie
    lang = math.dist(a, e) or 1.0
    d = ((e[0] - a[0]) / lang, (e[1] - a[1]) / lang)
    treffer = []
    for k in kanten:
        if not k.kreis:
            continue
        m, r = k.kreis
        hinter = (a[0] - m[0]) * d[0] + (a[1] - m[1]) * d[1]  # Anfang der Hilfslinie liegt in Linienrichtung hinter m
        if _abstand_gerade(m, a, e) <= PUNKT_TOL_MM and -PUNKT_TOL_MM <= hinter <= r + HILFSLINIE_KREIS_MM:
            treffer.append((hinter, k))
    if not treffer:
        return None
    mitte = min(treffer, key=lambda t: t[0])[1].kreis[0]
    return max((k for _, k in treffer if math.dist(k.kreis[0], mitte) <= PUNKT_TOL_MM), key=lambda k: k.kreis[1])


def kante_am_punkt(punkt: tuple[float, float], richtung: str, kanten: list[Kante],
                   hilfslinie: tuple | None = None, massstab: float = 1.0) -> Kante | None:
    """Kante, an der ein Maß in `punkt` ansetzt (Blatt-mm), in dieser Reihenfolge (Review Task 5, I2; Nachbesserung C):
    1. die gerade Kante quer zur Messrichtung (Maßlinie waagrecht „h“ → senkrechte Kante), auf deren Strecke der Punkt
       liegt (`PUNKT_TOL_MM`; trifft zugleich ein Kreis, gewinnt die Kante),
    2. die Kreiskante mit der Mitte im Punkt (unter mehreren der größte),
    3. die Kreiskante, deren Mitte auf der Hilfslinie liegt (`_kreis_der_hilfslinie`),
    4. erst dann die gerade Kante quer zur Messrichtung, deren Verlängerung den Punkt trifft, höchstens
       `KANTE_VERLAENGERT_MM` × `massstab` über ihr Ende hinaus (virtuelle Ecke einer Fase; nicht irgendwo auf ihrer
       Geraden – live lag eine Taschenkante 15 mm weiter auf derselben Linie; eine Wand, die knapp vor einer
       Kreismitte endet, verliert gegen den Kreis),
    5. ein Kantenende im Punkt (Live 27.11.: Fase der Buchse, eine Seite endet an der Fasenkante) – gewählt am
       Blattpunkt (`waehle_punkt`); kein Eckpunkt-Objekt mehr (Runde D, I2: ein IVertex-Treffer wäre Zufall).
    Unter mehreren geraden Kanten die nächste zum Punkt. `massstab`: Blatt-mm je Modell-mm der Ansicht – die
    Verlängerung gleicht ein Modellmaß aus (Fasenschenkel), keine Blattgröße. Ob das neue Maß wirklich dort ansetzt,
    prüft `_ersetze` nach Wirkung."""
    passend, verlaengert = [], []
    grenze = max(PUNKT_TOL_MM, KANTE_VERLAENGERT_MM * massstab)
    for k in kanten:
        if k.kreis or k.punkt or k.laenge() < 1e-6:
            continue
        dx, dy = abs(k.e[0] - k.a[0]), abs(k.e[1] - k.a[1])
        quer = dx < 1e-3 * max(dy, 1e-9) if richtung == "h" else dy < 1e-3 * max(dx, 1e-9)
        if not quer or _abstand_gerade(punkt, k.a, k.e) > PUNKT_TOL_MM:
            continue
        abstand = _abstand_strecke(punkt, k.a, k.e)
        if abstand <= PUNKT_TOL_MM:
            passend.append(k)
        elif abstand <= grenze:
            verlaengert.append(k)
    if passend:
        return min(passend, key=lambda k: _abstand_strecke(punkt, k.a, k.e))
    kreise = [k for k in kanten if k.kreis and math.dist(k.kreis[0], punkt) <= PUNKT_TOL_MM]
    if kreise:
        return max(kreise, key=lambda k: k.kreis[1])
    if hilfslinie is not None:
        k = _kreis_der_hilfslinie(hilfslinie, kanten)
        if k is not None:
            return k
    if verlaengert:
        return min(verlaengert, key=lambda k: _abstand_strecke(punkt, k.a, k.e))
    # Ende einer sichtbaren Kante ohne Eckpunkt-Objekt (Live 28.11.: Schnittansicht der Buchse liefert keine
    # IVertex) – gewählt wird dann über den Punkt (`waehle_punkt`)
    if any(not k.kreis and not k.punkt and min(math.dist(k.a, punkt), math.dist(k.e, punkt)) <= PUNKT_TOL_MM
           for k in kanten):
        return Kante(None, punkt, punkt, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), punkt=True)
    return None


def _bezugspunkt(a, e, luecke: float) -> tuple[float, float]:
    """Wie `mittellinien.bezugspunkt`: Anfang der Hilfslinie um die Lücke zum Bezug zurückgesetzt."""
    d = math.dist(a, e) or 1.0
    return (a[0] - (e[0] - a[0]) * luecke / d, a[1] - (e[1] - a[1]) * luecke / d)


def hilfslinien(dd) -> tuple[str, list[tuple], list[tuple[float, float]]] | None:
    """Richtung („h“: Maßlinie waagrecht), die beiden Hilfslinien (Anfang, Ende) und ihre Bezugspunkte (Anfang um die
    Lücke zurückgesetzt) eines linearen Anzeigemaßes in Blatt-mm (wie `zeichnen._bezuege`)."""
    if _ruf(dd, "Type2") not in LINEAR:
        return None
    daten = _ruf(dd, "GetDisplayData")
    if _ruf(daten, "GetLineCount") < 2:
        return None
    linien, waagrecht = [], True
    for k in (0, 1):
        linie = list(daten.GetLineAtIndex3(k))
        a, e = (linie[4] * 1000, linie[5] * 1000), (linie[7] * 1000, linie[8] * 1000)
        waagrecht = abs(e[0] - a[0]) < abs(e[1] - a[1])
        linien.append((a, e))
    return ("h" if waagrecht else "v"), linien, [_bezugspunkt(a, e, HILFSLINIE_LUECKE_MM) for a, e in linien]


# --- Zeichnungsmaße ---------------------------------------------------------------------------------------------------


def waehle_punkt(drw, view, k: Kante, anhaengen: bool) -> bool:
    """Kante bzw. Eckpunkt wählen: Objekt über `IView.SelectEntity`, ein Kantenende ohne Objekt über
    `SelectByID2("", "VERTEX", x, y, …)` am Blattpunkt."""
    if k.obj is not None:
        return bool(view.SelectEntity(k.obj, anhaengen))
    drw.ActivateView(_ruf(view, "GetName2"))
    return bool(_ruf(drw, "Extension").SelectByID2("", "VERTEX", k.a[0] / 1000, k.a[1] / 1000, 0, anhaengen, 0,
                                                    callout_leer(), 0))


def _loesche_gezaehlt(drw, view, dd) -> bool:
    """Anzeigemaß löschen und nach Wirkung prüfen: danach eins weniger in der Ansicht (Review Task 5, M2)."""
    vorher = len(_anzeige(view))
    _loesche(drw, dd)
    return len(_anzeige(view)) == vorher - 1


def bezuege_abweichung(richtung: str, alt: list[tuple[float, float]], neu: tuple | None) -> str:
    """Runde D (I2), nach Wirkung: Setzt das neue Zeichnungsmaß an denselben Bezugspunkten an wie das Modellmaß? In
    Messrichtung auf `BEZUG_MESS_TOL_MM`, entlang der Hilfslinie auf `BEZUG_ENTLANG_TOL_MM` (Zuordnung der beiden
    Punkte in beiden Reihenfolgen). '' wenn ja, sonst der Grund (auch, wenn die Hilfslinien nicht lesbar sind)."""
    if neu is None or len(neu[2]) != 2:
        return "Hilfslinien des neuen Maßes nicht lesbar"
    punkte = neu[2]
    i = 0 if richtung == "h" else 1          # Maßlinie waagrecht: gemessen wird x

    def passt(p, q) -> bool:
        return abs(p[i] - q[i]) <= BEZUG_MESS_TOL_MM and abs(p[1 - i] - q[1 - i]) <= BEZUG_ENTLANG_TOL_MM

    if any(all(passt(p, q) for p, q in zip(alt, reihe)) for reihe in (punkte, punkte[::-1])):
        return ""
    return (f"neues Maß setzt bei {', '.join(f'({p[0]:.1f}, {p[1]:.1f})' for p in punkte)} an statt "
            f"{', '.join(f'({p[0]:.1f}, {p[1]:.1f})' for p in alt)}")


def _ersetze(drw, mu, view, dd, kanten: list[Kante] | None = None, bezug=None) -> tuple[object | None, str]:
    """Ein Modellmaß als Zeichnungsmaß an denselben Bezugspunkten neu setzen. Liefert (neues Anzeigemaß, '') oder
    (None, Grund); das Modellmaß wird nur gelöscht, wenn das neue denselben Wert misst, an denselben Bezugspunkten
    ansetzt (`bezuege_abweichung`, Runde D I2) und das Löschen wirkt. Jedes
    Löschen wird nach Wirkung geprüft; ein stehengebliebenes Maß steht im Grund."""
    if _ruf(dd, "Type2") in RUND:
        return _ersetze_rund(drw, mu, view, dd, kanten)
    b = hilfslinien(dd)
    if b is None:
        return None, "kein lineares Maß mit zwei Hilfslinien"
    richtung, linien, punkte = b
    kanten = sichtbare_kanten(mu, view) if kanten is None else kanten
    try:  # Runde D (M6): ein COM-Ausfall ist eine Meldung, kein stilles 1:1
        massstab = float(_ruf(view, "ScaleDecimal"))
    except Exception:  # noqa: BLE001 – COM
        massstab = 0.0
    if not massstab > 0:
        return None, "Maßstab der Ansicht nicht lesbar"
    gewaehlt = [kante_am_punkt(p, richtung, kanten, h, massstab) for p, h in zip(punkte, linien)]
    if not all(gewaehlt):
        frei = [f"({p[0]:.1f}, {p[1]:.1f})" for p, k in zip(punkte, gewaehlt) if k is None]
        wort = f"Bezug {bezug} ohne" if bezug in ("mitte", "ursprung") else "keine"
        return None, f"{wort} sichtbare Kante am Bezugspunkt {', '.join(frei)}"
    alt = wert_mm(dd)
    x, y, _ = (list(_ruf(_ruf(dd, "GetAnnotation"), "GetPosition")) + [0.0])[:3]
    drw.ClearSelection2(True)
    if not (waehle_punkt(drw, view, gewaehlt[0], False) and waehle_punkt(drw, view, gewaehlt[1], True)):
        drw.ClearSelection2(True)
        return None, "Kanten nicht auswählbar"
    neu = drw.AddDimension2(x, y, 0)
    drw.ClearSelection2(True)
    if neu is None:
        return None, "AddDimension2 abgelehnt"
    w = wert_mm(neu)
    if alt is None or w is None or abs(w - alt) > WERT_TOL_MM:
        grund = f"neues Maß misst {w if w is None else round(w, 3)} statt {alt if alt is None else round(alt, 3)}"
    else:
        grund = bezuege_abweichung(richtung, punkte, hilfslinien(neu))
    if grund:
        if not _loesche_gezaehlt(drw, view, neu):
            grund += "; neues Maß nicht gelöscht, steht doppelt"
        return None, grund
    if not _loesche_gezaehlt(drw, view, dd):
        grund = "Modellmaß nicht gelöscht"
        if not _loesche_gezaehlt(drw, view, neu):
            grund += "; neues Maß nicht gelöscht, steht doppelt"
        return None, grund
    return neu, ""


def _ersetze_rund(drw, mu, view, dd, kanten: list[Kante] | None = None) -> tuple[object | None, str]:
    """Ø- oder R-Modellmaß über die Kreiskante allein als Zeichnungsmaß (Review Task 5, I5): der Kreis, dessen
    Modellradius zum Wert passt und dessen Mitte oder Rand eine Linie des Maßes berührt; `AddDimension2` an der Lage
    der Zahl, Wert vergleichen, Modellmaß löschen (nach Wirkung)."""
    alt = wert_mm(dd)
    if alt is None:
        return None, "Wert des Modellmaßes nicht lesbar"
    r_soll = alt / 2 if _ruf(dd, "Type2") in (6, 15) else alt
    daten = _ruf(dd, "GetDisplayData")
    punkte = []
    for i in range(_ruf(daten, "GetLineCount")):
        li = list(daten.GetLineAtIndex3(i))
        punkte += [(li[4] * 1000, li[5] * 1000), (li[7] * 1000, li[8] * 1000)]
    kanten = sichtbare_kanten(mu, view) if kanten is None else kanten

    def naehe(k: Kante) -> float:  # wie nah eine Linie des Maßes Mitte oder Rand des Kreises kommt
        return min(min(math.dist(p, k.kreis[0]), abs(math.dist(p, k.kreis[0]) - k.kreis[1])) for p in punkte)

    kreise = [k for k in kanten if k.kreis and k.radius_mm is not None and abs(k.radius_mm - r_soll) < WERT_TOL_MM
              and any(math.dist(p, k.kreis[0]) < PUNKT_TOL_MM or abs(math.dist(p, k.kreis[0]) - k.kreis[1]) < 0.3
                      for p in punkte)]
    if not kreise:
        return None, f"keine Kreiskante mit Radius {round(r_soll, 3)} am Maß"
    kreis = min(kreise, key=naehe)  # Nachbesserung C: der nächste, nicht der erste gleichen Radius
    x, y, _ = (list(_ruf(_ruf(dd, "GetAnnotation"), "GetPosition")) + [0.0])[:3]
    drw.ClearSelection2(True)
    if not view.SelectEntity(kreis.obj, False):
        return None, "Kreiskante nicht auswählbar"
    neu = drw.AddDimension2(x, y, 0)
    drw.ClearSelection2(True)
    if neu is None:
        return None, "AddDimension2 abgelehnt"
    w = wert_mm(neu)
    if w is None or abs(w - alt) > WERT_TOL_MM:
        grund = f"neues Maß misst {w if w is None else round(w, 3)} statt {round(alt, 3)}"
        if not _loesche_gezaehlt(drw, view, neu):
            grund += "; neues Maß nicht gelöscht, steht doppelt"
        return None, grund
    if not _loesche_gezaehlt(drw, view, dd):
        grund = "Modellmaß nicht gelöscht"
        if not _loesche_gezaehlt(drw, view, neu):
            grund += "; neues Maß nicht gelöscht, steht doppelt"
        return None, grund
    return neu, ""


def dauerhaft_machen(drw, mu, views: dict, plan: list[Mass]) -> tuple[dict[str, str], list[str]]:
    """Jedes Modellmaß des Plans mit Toleranz oder Textzusatz wird ein Zeichnungsmaß (Spike Stufe 4). Liefert alter
    Name → neuer Name (`RD<n>@<Ansicht>`) und Meldungen `MASS_NICHT_DAUERHAFT: <name> – <grund>` (das Modellmaß bleibt
    dann stehen, mit Toleranz und Zusatz nur bis zum Wiederöffnen)."""
    bezug = {m.name: m.bezug for m in plan if m.quelle == "modell" and m.name}
    ziel = {m.name for m in plan if m.quelle == "modell" and m.name and (m.toleranz or m.praefix or m.suffix)}
    namen, meldungen = {}, []
    if not ziel:
        return namen, meldungen
    for v in views.values():
        dds = [dd for dd in _anzeige(v) if kurzname(dd) in ziel and kurzname(dd) not in namen]
        if not dds:
            continue
        kanten = sichtbare_kanten(mu, v)
        for dd in dds:
            name = kurzname(dd)
            neu, grund = _ersetze(drw, mu, v, dd, kanten, bezug.get(name))
            if neu is None:
                meldungen.append(f"MASS_NICHT_DAUERHAFT: {name} – {grund}; Toleranz und Zusatz entfallen")
                namen.setdefault(name, name)
            else:
                namen[name] = kurzname(neu)
    for name in sorted(ziel - set(namen)):
        meldungen.append(f"MASS_NICHT_DAUERHAFT: {name} – nicht in der Zeichnung; Toleranz und Zusatz entfallen")
    return {a: n for a, n in namen.items() if a != n}, meldungen


def toleranz_setzen(dd, toleranz: Toleranz | None) -> bool:
    """Toleranz an ein Zeichnungsmaß: Passung als Typ 7 (`SetFitValues`, Bohrung groß, Welle klein geschrieben),
    symmetrische Abmaße als Typ 4, sonst Typ 2 mit `SetValues(unten, oben)` (m); Hülle als Suffix `<MOD-EP>` vor einem
    vorhandenen Suffix. Wahr, wenn alles gesetzt ist – geprüft nach Wirkung (Live 27.11.: `SetFitValues` meldete am
    Drehteil-Ø False, „32,00 k6 Ⓔ“ stand trotzdem im PDF)."""
    if toleranz is None:
        return True
    tol = _ruf(dd.GetDimension2(0), "Tolerance")
    if toleranz.passung is not None:
        p = toleranz.passung
        tol.Type = TOL_PASSUNG
        if p[:1].isupper():
            tol.SetFitValues(p, "")
        else:
            tol.SetFitValues("", p)
        tol.FitDisplayStyle = PASSUNG_EINZEILIG
        ok = _ruf(tol, "Type") == TOL_PASSUNG and p in (_ruf(tol, "GetHoleFitValue"), _ruf(tol, "GetShaftFitValue"))
    elif toleranz.oben is not None and toleranz.unten is not None:
        symmetrisch = abs(toleranz.oben + toleranz.unten) < 1e-9
        tol.Type = TOL_SYMMETRISCH if symmetrisch else TOL_BILAT
        tol.SetValues(toleranz.unten / 1000, toleranz.oben / 1000)
        ok = (abs(_ruf(tol, "GetMinValue") * 1000 - toleranz.unten) < 1e-6
              and abs(_ruf(tol, "GetMaxValue") * 1000 - toleranz.oben) < 1e-6)
    else:
        ok = False
    if toleranz.huelle:
        alt = dd.GetText(SUFFIX_TEXT) or ""
        if HUELLE not in alt:
            dd.SetText(SUFFIX_TEXT, f" {HUELLE}{alt}")
        ok = ok and HUELLE in (dd.GetText(SUFFIX_TEXT) or "")
    return ok


def zusaetze_setzen(views: dict, plan: list[Mass], namen: dict[str, str] | None = None,
                    nur: set[str] | None = None) -> list[str]:
    """Textzusätze und Toleranzen aus dem Maßplan an die Anzeigemaße gleichen (bzw. neuen, `namen`) Namens. Präfix und
    Suffix nur, wenn gesetzt (ein leeres Präfix löschte z. B. das Ø). `nur`: nur diese (alten) Namen – die Maße, die
    `dauerhaft_machen` umgewandelt hat; ein Modellmaß bekommt nichts (Review Task 5, I5: sonst zeigt das PDF, was die
    SLDDRW nach dem Wiederöffnen verliert). Liefert Meldungen `TOLERANZ_NICHT_GESETZT`."""
    namen = namen or {}
    je = {namen.get(m.name, m.name): m for m in plan if m.quelle == "modell" and m.name
          and (m.praefix or m.suffix or m.toleranz) and (nur is None or m.name in nur)}
    meldungen = []
    if not je:
        return meldungen
    for v in views.values():
        for dd in _anzeige(v):
            m = je.get(kurzname(dd))
            if m is None:
                continue
            if m.praefix:
                dd.SetText(PRAEFIX_TEXT, m.praefix)
            if m.suffix:
                dd.SetText(SUFFIX_TEXT, m.suffix)
            if not toleranz_setzen(dd, m.toleranz):
                meldungen.append(f"TOLERANZ_NICHT_GESETZT: {m.name}")
    return meldungen


# --- Anmerkungen (Rauheit, Bezug, Form/Lage) --------------------------------------------------------------------------


def _treffpunkt(linie: tuple, s: tuple, frei: float | None = None) -> tuple[float, float] | None:
    """Wo die Strecke `s` die Linie einer Anmerkung trifft – kreuzend, im Endpunkt von `s` berührend (Live 28.11.: die
    Hinweislinie lief genau durch das Ende der Maßlinie 12,00) oder auf ihr liegend (Überdeckung länger als `frei`,
    dann deren Mitte; Live 28.11.: Hinweislinie des Rahmens auf der Unterkante und der Hilfslinie). Treffen näher als
    `frei` an den Enden der Linie (Fußpunkt, Symbol) zählen nicht. None, wenn sie sich nicht treffen."""
    (a, b), (c, d) = linie, s
    frei = FUSS_FREI_MM if frei is None else frei
    lang = math.dist(a, b)
    if lang < 1e-9:
        return None
    u = ((b[0] - a[0]) / lang, (b[1] - a[1]) / lang)
    if _abstand_gerade(c, a, b) <= 0.05 and _abstand_gerade(d, a, b) <= 0.05:  # auf derselben Geraden
        t0, t1 = sorted(((q[0] - a[0]) * u[0] + (q[1] - a[1]) * u[1]) for q in (c, d))
        lo, hi = max(t0, 0.0), min(t1, lang)
        if hi - lo <= frei:
            return None
        m = (lo + hi) / 2
        return (a[0] + u[0] * m, a[1] + u[1] * m)
    r, w = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1])
    nenner = r[0] * w[1] - r[1] * w[0]
    if abs(nenner) < 1e-12:
        return None
    tl = ((c[0] - a[0]) * w[1] - (c[1] - a[1]) * w[0]) / nenner
    ts = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / nenner
    toleranz = 0.05 / (math.hypot(*w) or 1.0)
    if not (0.0 <= tl <= 1.0 and -toleranz <= ts <= 1.0 + toleranz):
        return None
    p = (a[0] + r[0] * tl, a[1] + r[1] * tl)
    return p if math.dist(p, a) > frei and math.dist(p, b) > frei else None


def _auf_strecke(p, s, tol: float = 0.1) -> bool:
    return _abstand_strecke(p, s[0], s[1]) <= tol


def _auf_kante(a, b, k: Kante, tol: float = 0.15) -> bool:
    """Liegt die Strecke a–b auf der Kante k (gerade: beide Enden auf der Strecke; Kreis: beide auf dem Kreis)?"""
    if k.kreis:
        m, r = k.kreis
        return all(abs(math.dist(p, m) - r) <= tol for p in (a, b))
    return _auf_strecke(a, (k.a, k.e), tol) and _auf_strecke(b, (k.a, k.e), tol)


def _in_flaeche(p, strecken: list[tuple]) -> bool:
    """Liegt p in der Fläche, die die Strecken umranden (gerade/ungerade Zahl der Schnitte eines Strahls nach rechts;
    die Strecken müssen nicht geordnet sein)?"""
    x, y = p
    innen = False
    for (ax, ay), (bx, by) in strecken:
        if (ay > y) != (by > y) and ax + (y - ay) * (bx - ax) / (by - ay) > x:
            innen = not innen
    return innen


# Verstoßarten (`Anmerkung.verstoesse`; Meldung ANMERKUNG_KREUZT, die Nähe `NAEHE` als ANMERKUNG_ZU_NAH, Runde D M3)
V_RECHTECK, V_KANTE_NAH, V_TEXT, V_MASSLINIE = "Rechteck auf Linie", "Kante näher als 3 mm", "Text", "Maßlinie"
V_ANSATZ, V_KANTE, V_SCHRAFFUR, V_HINWEISLINIE = "Ansatz näher als 4 mm", "Kante", "Schraffur", "Hinweislinie"
V_SYMBOL = "eigenes Symbol"
NAEHE = (V_KANTE_NAH, V_ANSATZ)
# Rauheit: von der Spitze aus liegen Dreieck, Strich und Text zwischen diesen Richtungen (Grad, am PDF 28.11.: linke
# Dreiecksecke 120°, Strichende 59°, untere Textecke 33°, Textende ~12°); kommt die Hinweislinie aus diesem Bereich,
# läuft sie durch das eigene Symbol (Live 28.11.: Ra 1,6 von unten an den Taschenboden)
RAUHEIT_SYMBOL_GRAD = (10.0, 122.0)
FUSS_FREI_MM = 0.5                                  # Strecken so nah am Fußpunkt berühren die Hinweislinie nur
SUCHE_JE_ANMERKUNG = 6                              # `anmerkungen_legen`: beste Lagen je Anmerkung (Runde D, C)
SUCHE_HOECHSTENS, STRAHL_BREITE = 20000, 200        # mehr Kombinationen: Strahlsuche mit dieser Breite


@dataclass
class Anmerkung:
    """Gesetzte Anmerkung mit Hinweislinie an `anker` (Blatt-mm, zurückgelesen). Verhält sich in der
    Lesbarkeitsschleife wie ein Hinweis (`zeichnen._Hinweis`): `zeilen`, `lage` (Mitte des Rechtecks), `rechteck()`,
    `verwerfen()`; Größe und Versatz (Mitte − `IAnnotation.GetPosition`) sind je Art live gemessen, `vermessen` bleibt
    wahr. `kante`: die gewählte gerade Kante (Bezug: Lagen quer zu ihr; vom Abstand zu Kanten ausgenommen).
    `einhaengen`: (Kante, Meldungen) → (Annotation, Ansatz) oder None – an einen anderen Ort hängen; `orte`: die
    Kanten, an die sie gehört – Kreiskanten aller Instanzen einer Bohrung oder (Nachbesserung C) die gleichwertigen
    geraden Kanten derselben Fläche in der Ansicht (`orte_der_flaeche`); `belegt`: die gemeinsame Liste der Ansätze
    (`_einfuegen_mit`).
    `schraffur`: Ränder der geschnittenen Flächen der Ansicht (`schraffur_strecken`); `offen`: Kanten des eigenen
    Merkmals (samt Muster/Spiegel), durch deren Öffnung die Hinweislinie laufen darf (Tasche, Bohrung; nicht im
    Schnitt) – gelten nur am Ort der heutigen Instanz (`_offen_hier`, Runde D I1). `wirkung`: () → Meldungen, wenn die
    zuletzt eingefügte Annotation nicht wirkt (Rahmen unbeschriftet; ausgewertet nach der Lesbarkeitsschleife,
    `anmerkungen_wirkung`, Runde E). `verworfen`: verworfene Lagen am heutigen Ort; `verworfen_orte`: die der anderen
    Orte (Index in `orte`) – Umhängen tauscht, statt zu leeren (Runde E, I-3)."""
    art: str                       # rauheit | form_lage | bezug
    merkmal: str
    zeilen: tuple[str, ...]
    ann: object
    rolle: str
    anker: tuple[float, float]
    umriss: tuple
    groesse: tuple[float, float]
    versatz: tuple[float, float]
    kante: tuple | None = None
    lage: tuple[float, float] | None = None
    verworfen: list = field(default_factory=list)
    vermessen: bool = True
    soll: tuple[float, float] | None = None   # gewählte Kandidatenlage (die zurückgelesene steht in `lage`)
    orte: list = field(default_factory=list)
    einhaengen: object = None
    fixiert: tuple | None = None              # (Lage, Instanz) der besten Runde (zeichnen._lesbar_anlegen)
    belegt: list | None = None
    schraffur: list = field(default_factory=list)
    offen: list = field(default_factory=list)
    wirkung: object = None
    verworfen_orte: dict = field(default_factory=dict)

    def rechteck(self, lage: tuple | None = None) -> tuple | None:
        lage = self.lage if lage is None else lage
        if lage is None:
            return None
        (x, y), (b, h) = lage, self.groesse
        return (x - b / 2, y - h / 2, x + b / 2, y + h / 2)

    def ort_nr(self, ort: Kante | None) -> int | None:
        """Index von `ort` in `orte` (nach Identität); None ohne Orte."""
        return next((i for i, o in enumerate(self.orte) if o is ort), None)

    def instanz(self) -> Kante | None:
        """Ort (Kante aus `orte`), an dem die Hinweislinie heute hängt; ohne Orte None."""
        if not self.orte:
            return None
        return min(self.orte, key=lambda k: abs(math.dist(self.anker, k.kreis[0]) - k.kreis[1]) if k.kreis
                   else _abstand_strecke(self.anker, k.a, k.e))

    def stand(self) -> tuple:
        """Stand dieser Runde: gewählte Lage und Instanz (Nachbesserung C: hat `instanzen_umhaengen` nach der besten
        Runde umgehängt, hängt die Wiederherstellung zurück, statt die alte Lage an die neue Bohrung zu setzen)."""
        return (self.soll, self.instanz())

    def _normale(self) -> tuple[float, float]:
        """Bezug: Normale der Kante, vom Körper weg."""
        a, e = self.kante
        lang = math.dist(a, e) or 1.0
        n = (-(e[1] - a[1]) / lang, (e[0] - a[0]) / lang)
        mitte = ((self.umriss[0] + self.umriss[2]) / 2, (self.umriss[1] + self.umriss[3]) / 2)
        return n if (a[0] - mitte[0]) * n[0] + (a[1] - mitte[1]) * n[1] >= 0 else (-n[0], -n[1])

    def versatz_bei(self, lage: tuple | None = None) -> tuple[float, float]:
        """Mitte − Bezugspunkt der Annotation. Bezugskasten: Bezugspunkt ist der Ansatz der Hinweislinie, die
        SolidWorks senkrecht zur Kante führt (Live 27.11.), also die Kastenseite zur Kante hin."""
        if self.art == "bezug" and self.kante is not None:
            n = self._normale()
            return (n[0] * self.groesse[1] / 2, n[1] * self.groesse[1] / 2)
        return self.versatz

    def fusspunkt(self, lage: tuple | None = None) -> tuple[float, float]:
        """Wo die Hinweislinie die Kante trifft: Bezug senkrecht unter dem Kasten (auch auf der Verlängerung der Kante
        über ihr Ende hinaus), sonst der Anker."""
        if self.art != "bezug" or self.kante is None:
            return self.anker
        lage = self.lage if lage is None else lage
        v = self.versatz_bei(lage)
        p = (lage[0] - v[0], lage[1] - v[1])
        a, e = self.kante
        lang = math.dist(a, e) or 1.0
        d = ((e[0] - a[0]) / lang, (e[1] - a[1]) / lang)
        t = (p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1]
        return (a[0] + d[0] * t, a[1] + d[1] * t)

    def hinweislinie(self, lage: tuple | None = None) -> tuple | None:
        """Hinweislinie, wie SolidWorks sie zieht (Live 27.11.): Rauheit vom Anker zur Spitze des Symbols (Bezugspunkt),
        Rahmen zur Mitte der nahen Schmalseite, Bezug senkrecht von der Kante zum Kasten."""
        lage = self.lage if lage is None else lage
        if lage is None:
            return None
        v = self.versatz_bei(lage)
        p = (lage[0] - v[0], lage[1] - v[1])
        if self.art in ("rauheit", "bezug"):
            return (self.fusspunkt(lage), p)
        r = self.rechteck(lage)
        seite = r[0] if abs(self.anker[0] - r[0]) <= abs(self.anker[0] - r[2]) else r[2]
        return (self.anker, (seite, (r[1] + r[3]) / 2))

    def verlaengerung(self, lage: tuple | None = None) -> tuple | None:
        """Bezug jenseits des Kantenendes (ISO 5459, Bezugsdreieck auf der Verlängerung der Fläche): die Linie, die
        SolidWorks vom Kantenende zum Dreieck zieht (Spike Stufe 4 i, 28.11.: `SetPosition2` über das Ende hinaus, die Lage
        bleibt, die Verlängerung erscheint im PDF). Sonst None."""
        if self.art != "bezug" or self.kante is None:
            return None
        fuss = self.fusspunkt(lage)
        a, e = self.kante
        if _auf_strecke(fuss, (a, e)):
            return None
        return (min((a, e), key=lambda q: math.dist(q, fuss)), fuss)

    def linien(self, lage: tuple | None = None) -> list[tuple]:
        """Alle Linien der Anmerkung außer dem Rechteck: Hinweislinie, beim Bezug auch die Verlängerung der Kante."""
        return [s for s in (self.hinweislinie(lage), self.verlaengerung(lage)) if s is not None]

    def nahe(self, rechteck: tuple) -> bool:
        """Liegt ein PDF-Befund (Rechteck) an dieser Anmerkung? Einzelbuchstaben und Werte gibt es mehrfach auf dem
        Blatt (Bezug „A“, Schnitt „A-A“; „0,02“ als Abmaß und Ebenheit)."""
        r = self.rechteck()
        if r is None:
            return False
        n = NAEHE_ANMERKUNG_MM
        return rechteck[0] < r[2] + n and r[0] - n < rechteck[2] and rechteck[1] < r[3] + n and r[1] - n < rechteck[3]

    def verwerfen(self) -> bool:
        """PDF-Befund: die gewählte Soll-Lage verwerfen (nicht die zurückgelesene, Review Task 5 I3 – sonst wird ein
        gerückter Bezugskasten nie als verworfen erkannt); False, wenn keine Lage mehr übrig ist – am heutigen Ort und,
        wenn die Anmerkung umgehängt werden kann, an den anderen Orten (Runde E, I-3: Verwerfungen bleiben je Ort)."""
        lage = self.soll if self.soll is not None else self.lage
        if lage is not None and lage not in self.verworfen:
            self.verworfen.append(lage)
        if len(self.verworfen) < len(self._roh()) or self.einhaengen is None:
            return len(self.verworfen) < len(self._roh())
        heute = self.instanz()
        return any(len(self.verworfen_orte.get(i, ())) < len(_probe(self, o)._roh())
                   for i, o in enumerate(self.orte) if o is not heute)

    def _roh(self, anker: tuple | None = None, weiter: dict | None = None) -> list[tuple[float, float]]:
        """Lagen (Mitte des Rechtecks) in fester Rangfolge. Bezug: Kasten quer zur Kante nach außen, entlang der Kante
        verteilt, danach auf der Verlängerung der Kante über beide Enden hinaus (ISO 5459, Nachbesserung C); sonst in
        acht Richtungen um den Anker (diagonal zuerst) im Abstand `ANM_ABSTAENDE_MM`, das Rechteck auf der vom Anker
        abgewandten Seite (Review Task 5: die 16 Lagen der Bohrungsangaben reichten nicht). `weiter`: zusätzliche
        Abstände jenseits der äußersten Maßlinie (`_jenseits`; Bezug: Schlüssel None, sonst je Richtung in Grad)."""
        weiter = weiter or {}
        if self.art != "bezug" or self.kante is None:
            ax, ay = self.anker if anker is None else anker
            b, h = self.groesse
            aus = []
            stufen = [(d, w) for d in ANM_ABSTAENDE_MM for w in ANM_RICHTUNGEN_GRAD]
            stufen += [(weiter[w], w) for w in ANM_RICHTUNGEN_GRAD if weiter.get(w)]
            for d, w in stufen:
                c, s = math.cos(math.radians(w)), math.sin(math.radians(w))
                ex, ey = ax + d * c, ay + d * s
                aus.append((round(ex + (b / 2 if c > 0.1 else -b / 2 if c < -0.1 else 0.0), 3),
                            round(ey + (h / 2 if s > 0.9 else -h / 2 if s < -0.9 else 0.0), 3)))
            return aus
        a, e = self.kante
        n = self._normale()
        lang = math.dist(a, e) or 1.0
        d = ((e[0] - a[0]) / lang, (e[1] - a[1]) / lang)
        abstaende = list(BEZUG_ABSTAENDE_MM) + ([weiter[None]] if weiter.get(None) else [])
        fuesse = [(a[0] + (e[0] - a[0]) * t, a[1] + (e[1] - a[1]) * t) for t in BEZUG_TEILUNG]
        aus = [(p, abstand) for abstand in abstaende for p in fuesse]
        # Verlängerung: über das Ende hinaus, so weit, dass der Kasten (Höhe quer zur Verlängerung) frei vom Teil liegt
        for u in BEZUG_VERLAENGERUNG_MM:
            for ende, richtung in ((e, d), (a, (-d[0], -d[1]))):
                fuss = (ende[0] + richtung[0] * (u + self.groesse[0] / 2), ende[1] + richtung[1] * (u + self.groesse[0] / 2))
                aus += [(fuss, abstand) for abstand in abstaende]
        return [(round(p[0] + n[0] * (abstand + self.groesse[1] / 2), 3),
                 round(p[1] + n[1] * (abstand + self.groesse[1] / 2), 3)) for p, abstand in aus]

    def _jenseits(self, masslinien: list[tuple]) -> dict:
        """Abstände jenseits der äußersten Maß- bzw. Hilfslinie in Richtung der Lagen (Nachbesserung C): Bezug quer zur
        Kante (Linien neben der Kante), sonst je Richtung (Linien in einem Streifen von `JENSEITS_STREIFEN_MM` um den
        Strahl). Nur, wenn weiter als die festen Abstände; Linien weiter als `JENSEITS_MAX_MM` gehören zu anderen
        Ansichten (Runde D, M4)."""
        punkte = [p for s in masslinien for p in s]
        if not punkte:
            return {}
        if self.art == "bezug" and self.kante is not None:
            a, e = self.kante
            n = self._normale()
            lang = math.dist(a, e) or 1.0
            d = ((e[0] - a[0]) / lang, (e[1] - a[1]) / lang)
            neben = [((p[0] - a[0]) * n[0] + (p[1] - a[1]) * n[1]) for p in punkte
                     if -JENSEITS_STREIFEN_MM <= (p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1] <= lang + JENSEITS_STREIFEN_MM]
            weit = max((x for x in neben if x <= JENSEITS_MAX_MM), default=0.0) + JENSEITS_LUECKE_MM
            return {None: round(weit, 3)} if weit > max(BEZUG_ABSTAENDE_MM) else {}
        aus = {}
        for w in ANM_RICHTUNGEN_GRAD:
            u = (math.cos(math.radians(w)), math.sin(math.radians(w)))
            vor = [(p[0] - self.anker[0]) * u[0] + (p[1] - self.anker[1]) * u[1] for p in punkte
                   if abs(-(p[0] - self.anker[0]) * u[1] + (p[1] - self.anker[1]) * u[0]) <= JENSEITS_STREIFEN_MM]
            weit = max((x for x in vor if x <= JENSEITS_MAX_MM), default=0.0) + JENSEITS_LUECKE_MM
            if weit > max(ANM_ABSTAENDE_MM):
                aus[w] = round(weit, 3)
        return aus

    def _offen_hier(self) -> list:
        """Runde D (I1): die offenen Kanten am Ort der heutigen Instanz – an einer Bohrung die Kreise derselben Mitte
        (Bohrung, Fase), an einer geraden Kante (Taschenboden) die Ränder, die im Feld dieser Kante liegen (die eigene
        Öffnung, nicht die gespiegelte). Ohne Orte gilt die gewählte Kante bzw. der Kreis durch den Anker."""
        if not self.offen:
            return []
        ort = self.instanz()
        if ort is not None and ort.kreis:
            mitten = [ort.kreis[0]]
        elif ort is not None or self.kante is not None:
            a, e = (ort.a, ort.e) if ort is not None else self.kante
            lang = math.dist(a, e)
            if lang < 1e-9:
                return []
            d = ((e[0] - a[0]) / lang, (e[1] - a[1]) / lang)

            def im_feld(p) -> bool:
                t = (p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1]
                return -OFFEN_RAND_MM <= t <= lang + OFFEN_RAND_MM

            return [k for k in self.offen if im_feld(k.a) and im_feld(k.e)]
        else:
            mitten = [k.kreis[0] for k in self.offen
                      if k.kreis and abs(math.dist(self.anker, k.kreis[0]) - k.kreis[1]) <= KONZENTRISCH_MM]
        return [k for k in self.offen if k.kreis and any(math.dist(k.kreis[0], m) <= KONZENTRISCH_MM for m in mitten)]

    def _kanten_kreuzungen(self, linien: list[tuple], kanten) -> int:
        """Wie viele Kanten die Linien der Anmerkung treffen (`_treffpunkt`; am Fußpunkt zählt nichts). Ausgenommen
        ist nur die erste Kreuzung der Hinweislinie ab dem Fußpunkt, wenn sie auf einer offenen Kante dieses Orts liegt
        (`_offen_hier`: die Linie verlässt die eigene Öffnung; Runde D I1 – jede weitere Kreuzung zählt, auch die des
        eigenen Rands nach einer fremden Kante). Die eigene Kante zählt, wenn die Linie auf ihr liegt."""
        offen = self._offen_hier()
        n = 0
        for i, linie in enumerate(linien):
            treffer = sorted((math.dist(p, linie[0]), s) for s in kanten
                             if (p := _treffpunkt(linie, s)) is not None)
            frei_bis = None
            if i == 0 and offen and treffer and any(_auf_kante(*treffer[0][1], k) for k in offen):
                frei_bis = treffer[0][0] + KONZENTRISCH_MM   # dieselbe Kreuzung (Bogenstücke, doppelte Kante)
            n += sum(1 for d, s in treffer
                     if not (frei_bis is not None and d <= frei_bis and any(_auf_kante(*s, k) for k in offen)))
        return n

    def _durch_symbol(self, lage) -> bool:
        """Läuft die Hinweislinie durch die eigene Anmerkung? Rauheit: kommt sie (zur Spitze) aus der Richtung, in der
        Dreieck und Text liegen; Rahmen: läuft sie vor ihrem Ende an der Schmalseite durch das eigene Rechteck (Live
        28.11.: durch „2 ×“ über dem Rahmen)."""
        fuss, ende = self.hinweislinie(lage)
        if self.art == "rauheit":
            w = math.degrees(math.atan2(fuss[1] - ende[1], fuss[0] - ende[0])) % 360
            return RAUHEIT_SYMBOL_GRAD[0] <= w <= RAUHEIT_SYMBOL_GRAD[1]
        if self.art != "form_lage":
            return False
        x0, y0, x1, y1 = self.rechteck(lage)
        innen = (x0 + 0.2, y0 + 0.2, x1 - 0.2, y1 - 0.2)
        lang = math.dist(fuss, ende)
        if lang <= FUSS_FREI_MM:
            return False
        for i in range(1, 20):
            s = i / 20 * (1 - FUSS_FREI_MM / lang)
            p = (fuss[0] + (ende[0] - fuss[0]) * s, fuss[1] + (ende[1] - fuss[1]) * s)
            if innen[0] < p[0] < innen[2] and innen[1] < p[1] < innen[3]:
                return True
        return False

    def _durch_schraffur(self, linien: list[tuple]) -> bool:
        """Läuft eine Linie durch eine geschnittene Fläche (Proben ab `FUSS_FREI_MM` hinter dem Fußpunkt)?"""
        if not self.schraffur:
            return False
        for a, b in linien:
            lang = math.dist(a, b)
            if lang <= FUSS_FREI_MM:
                continue
            for i in range(1, 10):
                t = FUSS_FREI_MM / lang + (1 - FUSS_FREI_MM / lang) * i / 10
                if _in_flaeche((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), self.schraffur):
                    return True
        return False

    def verstoesse(self, lage, hindernisse=(), texte=(), kanten=(), masslinien=(), ansaetze=(),
                   hinweislinien=(), selbst: bool = True) -> dict[str, int]:
        """Verstöße einer Lage je Art (Review Task 5, C2; Nachbesserung C):
        - `Rechteck auf Linie`: das Rechteck kreuzt eine Strecke aus `hindernisse` (auch Zeichenfeld, Schriftfeld,
          Band, Mittellinien – sie sind keine Kanten, Runde D M3),
        - `Kante näher als 3 mm` (Nähe): Rechteck samt `ABSTAND_KANTE_MM` kreuzt eine sichtbare Kante (`kanten`, je
          Kante einmal) außer der eigenen,
        - `Text`, `Maßlinie`, `Hinweislinie`: eine Linie der Anmerkung (`linien`) quert ein Textrechteck (`texte`:
          Hinweise, gelegte Anmerkungen, fremde Texte), eine Maß- bzw. Hilfslinie (`masslinien`; nicht, wo die
          Hilfslinie auf einer sichtbaren Kante liegt – kollinear, Runde D M2 –, dort zählt die Kante) oder eine andere
          Hinweislinie (`hinweislinien`),
        - `Kante`: sie kreuzt eine sichtbare Kante (`_kanten_kreuzungen`),
        - `Schraffur`: sie läuft durch eine geschnittene Fläche,
        - `Ansatz näher als 4 mm` (Nähe): ihr Fußpunkt liegt näher als `ANSATZ_ABSTAND_MM` an einem anderen Ansatz,
        - `eigenes Symbol`: die Hinweislinie läuft durch die eigene Anmerkung (`_durch_symbol`).
        `selbst=False` (Runde E, `_paar`): Schraffur und eigenes Symbol gehören zur Lage selbst und werden nicht
        gerechnet."""
        r = self.rechteck(lage)
        g = ABSTAND_KANTE_MM
        weit = (r[0] - g, r[1] - g, r[2] + g, r[3] + g)
        linien = self.linien(lage)
        eigen = self.kante
        fuss = self.fusspunkt(lage)

        def quer(s):
            return any(_treffpunkt(linie, s) is not None for linie in linien)

        def masslinie_quer(s):  # wo eine Hilfslinie auf einer Kante liegt, zählt die Kante (oder ihre Ausnahme)
            for linie in linien:
                p = _treffpunkt(linie, s)
                if p is not None and not any(_abstand_strecke(p, k0, k1) <= PUNKT_TOL_MM
                                             and _abstand_gerade(k0, *s) <= 0.05 and _abstand_gerade(k1, *s) <= 0.05
                                             for k0, k1 in kanten):
                    return True
            return False

        aus = {
            V_RECHTECK: sum(1 for a, b in hindernisse if _schneidet(a, b, r)),
            V_KANTE_NAH: sum(1 for a, b in kanten if _schneidet(a, b, weit)
                             and not (eigen and _auf_strecke(a, eigen) and _auf_strecke(b, eigen))),
            V_TEXT: sum(1 for t in texte if t and any(_schneidet(a, b, t) for a, b in linien)),
            V_MASSLINIE: sum(1 for s in masslinien if masslinie_quer(s)),
            V_HINWEISLINIE: sum(1 for s in hinweislinien if s and quer(s)),
            V_KANTE: self._kanten_kreuzungen(linien, kanten) if kanten else 0,
            V_SCHRAFFUR: int(selbst and self._durch_schraffur(linien)),
            V_ANSATZ: sum(1 for p in ansaetze if math.dist(p, fuss) < ANSATZ_ABSTAND_MM),
            V_SYMBOL: int(selbst and self._durch_symbol(lage)),
        }
        return {k: v for k, v in aus.items() if v}

    def bewerten(self, lage, hindernisse=(), texte=(), kanten=(), masslinien=(), ansaetze=(), hinweislinien=()) -> int:
        """Zahl der Verstöße einer Lage (0 = frei), Summe von `verstoesse`."""
        return sum(self.verstoesse(lage, hindernisse, texte, kanten, masslinien, ansaetze, hinweislinien).values())

    def kandidaten(self, hindernisse: list[tuple] = (), texte: list[tuple] = (), kanten: list[tuple] = (),
                   masslinien: list[tuple] = (), ansaetze: list = (), hinweislinien: list = ()) -> list[tuple[float, float]]:
        """Lagen, beste zuerst: wenigste Verstöße (`bewerten`), dann außerhalb des Körpers, dann Rang."""
        bewertet = []
        for i, lage in enumerate(self._roh(weiter=self._jenseits(masslinien))):
            r = self.rechteck(lage)
            im_koerper = r[0] < self.umriss[2] and self.umriss[0] < r[2] and r[1] < self.umriss[3] and self.umriss[1] < r[3]
            bewertet.append((self.bewerten(lage, hindernisse, texte, kanten, masslinien, ansaetze, hinweislinien),
                             im_koerper, i, lage))
        return [lage for *_, lage in sorted(bewertet)]


def instanzen(spec: dict, fid: str) -> int:
    """Wie oft ein Merkmal am Teil vorkommt: Positionen einer Bohrung bzw. ihres Bohrbilds, sonst mal 2 je Spiegeln und
    mal Anzahl je Muster, das es enthält (Review Task 5, I4: Ra 1,6 und // 0,05 gelten beiden Taschen)."""
    features = {f["id"]: f for f in spec.get("features", [])}
    f = features.get(fid, {})
    if f.get("typ") in ("bohrung", "normbohrung"):
        bild = bohrbilder(spec).get(fid)
        return bild.anzahl if bild else 1
    n = 1
    for m in _enthalten(spec, fid):
        if m["typ"] == "spiegeln":
            n *= 2
        elif m["typ"] == "muster_linear":
            n *= int((m.get("richtung1") or {}).get("anzahl", 1)) * int((m.get("richtung2") or {}).get("anzahl", 1))
        elif m["typ"] == "muster_kreis":
            n *= int(m.get("anzahl", 1))
    return n


def _ansichten_fuer(views: dict, achsen: dict, achse: int | None, modus: str | None) -> list[str]:
    """Rollen, deren Blickachse zur Anforderung passt (flach: gleich, quer: verschieden); ohne Einzelheit."""
    if achse is None or modus is None:
        return []
    return [r for r in views if r != "einzelheit" and r in achsen and (achsen[r] == achse) == (modus == "flach")]


def _ohne_kante(rollen: list[str], achse: int | None, modus: str | None) -> str:
    """Grund, wenn keine Kante gewählt werden konnte: keine Ansicht passender Blickachse oder keine Kante darin."""
    if not rollen:
        return ("keine Ansicht mit passender Blickachse (Achse unbekannt)" if achse is None or modus is None
                else f"keine Ansicht mit passender Blickachse ({'xyz'[achse]}, {modus})")
    return f"keine passende Kante in {', '.join(rollen)}"


def _zum_merkmal(k: Kante, namen: set[str]) -> bool:
    return any(n in namen or any(n.startswith(z + "_") for z in namen) for n in k.features)


def endkante(kanten: list[Kante], namen: set[str], achse: int, vorzeichen: int) -> Kante | None:
    """Gerade Kante einer Fläche mit Normale ±`achse` des Merkmals: beide Enden auf der äußersten Lage aller Kanten des
    Merkmals in dieser Richtung (Modellkoordinaten); die längste auf dem Blatt."""
    eigene = [k for k in kanten if _zum_merkmal(k, namen) and not k.kreis and not k.punkt]
    if not eigene:
        return None
    lagen = [p[achse] for k in eigene for p in (k.a_m, k.e_m)]
    grenze = max(lagen) if vorzeichen > 0 else min(lagen)
    auf = [k for k in eigene if abs(k.a_m[achse] - grenze) < 1e-3 and abs(k.e_m[achse] - grenze) < 1e-3
           and k.laenge() > 1.0]
    return max(auf, key=lambda k: k.laenge(), default=None)


def orte_der_flaeche(kanten: list[Kante], k: Kante, namen: set[str], achse: int | None,
                     schraffur: list[tuple] = ()) -> list[Kante]:
    """Gerade Kanten derselben Fläche wie `k` (Normale ±`achse` des Merkmals, beide Enden auf ihrer Lage), mindestens
    `ORT_MIN_MM` lang, im Schnitt nur auf dem Rand der Schnittfläche (der Rand einer Taschenöffnung hinter dem Schnitt
    gehört auch zur Fläche, ist aber nicht ihre Kante im Schnitt). `k` zuerst (Nachbesserung C: ▱ 0,02 an der
    Unterseite zwischen den Taschen lag über „SCHNITT A-A“; dieselbe Fläche zeigt sich rechts und links frei)."""
    if k.kreis or k.punkt or achse is None:
        return [k]
    grenze = k.a_m[achse]
    aus = [o for o in kanten if o is not k and not o.kreis and not o.punkt and _zum_merkmal(o, namen)
           and abs(o.a_m[achse] - grenze) < 1e-3 and abs(o.e_m[achse] - grenze) < 1e-3 and o.laenge() >= ORT_MIN_MM
           and (not schraffur or any(_auf_strecke(o.a, s, 0.05) and _auf_strecke(o.e, s, 0.05) for s in schraffur))]
    return [k] + sorted(aus, key=lambda o: -o.laenge())


def bohrungskreise(kanten: list[Kante], namen: set[str]) -> list[Kante]:
    """Je Bohrung (Kreismitte) die kleinste Kreiskante des Merkmals – die Bohrung selbst, nicht ihre Fase."""
    je: dict[tuple, Kante] = {}
    for k in kanten:
        if k.kreis and _zum_merkmal(k, namen):
            s = (round(k.kreis[0][0], 1), round(k.kreis[0][1], 1))
            if s not in je or k.kreis[1] < je[s].kreis[1]:
                je[s] = k
    return sorted(je.values(), key=lambda k: k.kreis[0])


def kreiskante(kanten: list[Kante], namen: set[str], meiden: list | None = None) -> Kante | None:
    """Kreiskante der Bohrung, die am weitesten von den Punkten `meiden` liegt (Live 27.11.: Rauheit und
    Bohrungsangabe an derselben Stiftbohrung lagen übereinander)."""
    kreise = bohrungskreise(kanten, namen)
    if not kreise:
        return None
    if meiden:
        return max(kreise, key=lambda k: min(math.dist(k.kreis[0], p) for p in meiden))
    return kreise[0]


def _umriss(kanten: list[Kante]) -> tuple[float, float, float, float]:
    """Umriss der Kanten; Eckpunkte zählen nicht (Live 28.11.: `IVertex.GetPoint` landet über `ModelToViewTransform`
    neben der Ansicht – x um 62,5 mm versetzt in der Hauptansicht, im Schnitt 60 mm tiefer)."""
    linien = [k for k in kanten if not k.punkt] or kanten
    xs = [p[0] for k in linien for p in (k.a, k.e)]
    ys = [p[1] for k in linien for p in (k.a, k.e)]
    return (min(xs), min(ys), max(xs), max(ys))


def _kante_fuer(views: dict, mu, rollen: list[str], suche, cache: dict) -> tuple[str, Kante, list[Kante]] | None:
    """Unter den passenden Ansichten mit Kante die mit den wenigsten Maßen (Live 27.11.: Bezug B an der linken Kante
    der Hauptansicht lag in den Maßreihen; die Schnittansicht zeigt dieselbe Fläche fast frei)."""
    treffer = []
    for i, rolle in enumerate(rollen):
        if rolle not in cache:
            cache[rolle] = sichtbare_kanten(mu, views[rolle])
        k = suche(cache[rolle])
        if k is not None:
            treffer.append((len(_anzeige(views[rolle])), i, rolle, k))
    if not treffer:
        return None
    _, _, rolle, k = min(treffer, key=lambda t: t[:2])
    return rolle, k, cache[rolle]


def _melde(meldungen: list | None, text: str) -> None:
    """Meldung einmal aufnehmen (die Lesbarkeitsschleife hängt und legt in jeder Runde neu)."""
    if meldungen is not None and text not in meldungen:
        meldungen.append(text)


def ansatzpunkt(k: Kante, kanten: list[Kante], belegt: list, umriss: tuple | None = None,
                meldungen: list | None = None, etikett: str = "") -> tuple[float, float]:
    """Punkt auf der Kante, an dem die Hinweislinie ansetzt (Review Task 5, C2: ohne Pickpunkt endeten die Linien an
    Kantenenden, zwei teilten sich einen Ecke): auf einer Geraden bei 50/35/65/20/80 % ihrer Länge, auf einem Kreis
    unter 45°/135°/315°/225° (vom Körper weg zuerst); mindestens `ANSATZ_ABSTAND_MM` von schon belegten Ansätzen und
    0,5 mm von anderen Kanten, damit die Wahl am Punkt eindeutig ist. Ist keiner frei, der erste – mit Meldung
    `ANSATZ_NICHT_FREI` (Nachbesserung C)."""
    if k.kreis:
        (mx, my), r = k.kreis
        mitte = ((umriss[0] + umriss[2]) / 2, (umriss[1] + umriss[3]) / 2) if umriss else (mx, my)
        winkel = sorted(KREIS_WINKEL, key=lambda w: -((math.cos(math.radians(w)) * (mx - mitte[0]))
                                                      + (math.sin(math.radians(w)) * (my - mitte[1]))))
        punkte = [(mx + r * math.cos(math.radians(w)), my + r * math.sin(math.radians(w))) for w in winkel]
    else:
        punkte = [(k.a[0] + (k.e[0] - k.a[0]) * t, k.a[1] + (k.e[1] - k.a[1]) * t) for t in ANSATZ_TEILUNG]

    def frei(p) -> bool:
        if any(math.dist(p, q) < ANSATZ_ABSTAND_MM for q in belegt):
            return False
        for o in kanten:
            if o is k or o.punkt or (o.kreis and k.kreis and math.dist(o.kreis[0], k.kreis[0]) <= PUNKT_TOL_MM):
                continue  # konzentrisch (Fase derselben Bohrung, 0,25 mm daneben): gleichwertig, keine Mehrdeutigkeit
            d = abs(math.dist(p, o.kreis[0]) - o.kreis[1]) if o.kreis else _abstand_strecke(p, o.a, o.e)
            if d < 0.5 and not (not o.kreis and not k.kreis and _auf_strecke(o.a, (k.a, k.e), 0.05)
                                and _auf_strecke(o.e, (k.a, k.e), 0.05)):
                return False
        return True

    p = next((p for p in punkte if frei(p)), None)
    if p is None:
        _melde(meldungen, f"ANSATZ_NICHT_FREI: {etikett} – kein Ansatzpunkt der Kante frei (belegt oder an einer "
                          "anderen Kante), Hinweislinie am ersten")
        return punkte[0]
    return p


def schraffur_strecken(mu, view) -> tuple[list[tuple], list[str]]:
    """Ränder der geschnittenen (schraffierten) Flächen der Ansicht in Blatt-mm (`IView.GetFaceHatches`,
    `IFaceHatch.Face`, `IFace2.GetEdges`; Spike Stufe 4 i, 28.11.: Schnitt A-A der SpannplatteZ liefert eine Fläche mit zwölf
    Kanten, gleich den Kanten der Schnittfläche). Bögen in `SCHRAFFUR_BOGEN_STUECKE` Stücken; ohne Schnitt leer.
    Zweiter Wert (Runde D, I4): Gründe, warum die Schraffur nicht vollständig gelesen ist – `GetFaceHatches`
    gescheitert, Schnittansicht (`IView.Type`) ohne Schraffur, Fläche oder Kante unlesbar (ein fehlendes Stück öffnet
    den Rand, `_in_flaeche` zählte dann falsch). Leer, wenn alles gelesen ist."""
    try:
        schraffuren = list(_ruf(view, "GetFaceHatches") or ())
    except Exception:  # noqa: BLE001 – COM
        return [], ["GetFaceHatches gescheitert"]
    if not schraffuren:
        try:
            schnitt = _ruf(view, "Type") == SCHNITTANSICHT
        except Exception:  # noqa: BLE001 – COM
            return [], ["Ansichtsart nicht lesbar"]
        return [], (["Schnittansicht ohne Schraffur"] if schnitt else [])
    t = _ruf(view, "ModelToViewTransform")

    def blatt(p_m):
        q = mu.CreatePoint(r8_array(list(p_m)[:3])).MultiplyTransform(t).ArrayData
        return q[0] * 1000, q[1] * 1000

    aus, gruende = [], []
    for i, fh in enumerate(schraffuren, 1):
        try:
            kanten = list(_ruf(_ruf(fh, "Face"), "GetEdges") or ())
        except Exception:  # noqa: BLE001 – COM
            gruende.append(f"Fläche {i}: Kanten nicht lesbar")
            continue
        for j, k in enumerate(kanten, 1):
            try:
                cp, c = _ruf(k, "GetCurveParams3"), _ruf(k, "GetCurve")
                a_m, e_m = tuple(_ruf(cp, "StartPoint"))[:3], tuple(_ruf(cp, "EndPoint"))[:3]
                if _ruf(c, "IsCircle"):
                    cx, cy, cz = list(_ruf(c, "CircleParams"))[:3]
                    aus += _bogen(blatt(a_m), blatt(e_m), blatt((cx, cy, cz)))
                else:
                    aus.append((blatt(a_m), blatt(e_m)))
            except Exception:  # noqa: BLE001 – COM
                gruende.append(f"Fläche {i}: Kante {j} nicht lesbar")
    return aus, gruende


def _bogen(a, e, m) -> list[tuple]:
    """Bogen von a nach e um m (kürzerer Bogen; Vollkreis, wenn a = e) als Strecken."""
    r = math.dist(a, m)
    w0 = math.atan2(a[1] - m[1], a[0] - m[0])
    voll = math.dist(a, e) < 1e-6
    spanne = 2 * math.pi if voll else (math.atan2(e[1] - m[1], e[0] - m[0]) - w0 + math.pi) % (2 * math.pi) - math.pi
    n = SCHRAFFUR_BOGEN_STUECKE
    p = [(m[0] + r * math.cos(w0 + spanne * i / n), m[1] + r * math.sin(w0 + spanne * i / n)) for i in range(n + 1)]
    return list(zip(p, p[1:]))


def offene_kanten(kanten: list[Kante], namen: set[str], schraffur: list[tuple]) -> list[Kante]:
    """Kanten eines vertieften Merkmals (Tasche, Bohrung), die nicht auf dem Rand einer Schnittfläche liegen: durch
    seine Öffnung darf die Hinweislinie zum Boden laufen (Nachbesserung C: Ra 1,6 am Taschenboden im Schnitt A-A von
    unten, über den Rand der Öffnung)."""
    return [k for k in kanten if not k.punkt and _zum_merkmal(k, namen)
            and not any(_auf_strecke(k.a, s, 0.05) and _auf_strecke(k.e, s, 0.05) for s in schraffur)]


def _waehle_am_punkt(drw, view, k: Kante, punkt: tuple[float, float]) -> bool:
    """Kante am Punkt wählen (`SelectByID2("", "EDGE", x, y, …)`, wie Stufe 3 `_kreis_am_punkt`; Spike h: die
    Hinweislinie setzt dann dort an). Wahr, wenn dort die gesuchte Kante gewählt ist – geprüft an Anfang und Ende im
    Modell (`IEdge.GetCurveParams3`; Runde D M1: 0,25 mm daneben liegt die Fasenkante); sonst `IView.SelectEntity`
    (ohne Punkt)."""
    drw.ClearSelection2(True)
    drw.ActivateView(_ruf(view, "GetName2"))
    if _ruf(drw, "Extension").SelectByID2("", "EDGE", punkt[0] / 1000, punkt[1] / 1000, 0, False, 0,
                                         callout_leer(), 0):
        sm = _ruf(drw, "SelectionManager")
        if any(sm.GetSelectedObjectType3(i, -1) == KANTE and _dieselbe_kante(sm.GetSelectedObject6(i, -1), k)
               for i in range(1, sm.GetSelectedObjectCount2(-1) + 1)):
            return True
    drw.ClearSelection2(True)
    return bool(view.SelectEntity(k.obj, False))


def _dieselbe_kante(obj, k: Kante, tol_mm: float = 0.01) -> bool:
    """Ist die gewählte Kante `k`? Anfang und Ende im Modell (mm) gleich, in beliebiger Richtung."""
    try:
        cp = _ruf(obj, "GetCurveParams3")
        a, e = (tuple(c * 1000 for c in list(_ruf(cp, n))[:3]) for n in ("StartPoint", "EndPoint"))
    except Exception:  # noqa: BLE001 – COM: gewähltes Objekt ohne Kurve
        return False
    return any(math.dist(a, p) <= tol_mm and math.dist(e, q) <= tol_mm for p, q in ((k.a_m, k.e_m), (k.e_m, k.a_m)))


def ansatz_lesen(ann) -> tuple[float, float] | None:
    """Ende der ersten Hinweislinie an der Kante (Spike h: letzter Punkt von `IAnnotation.GetLeaderPointsAtIndex`)."""
    try:
        if not _ruf(ann, "GetLeaderCount"):
            return None
        p = list(ann.GetLeaderPointsAtIndex(0) or ())
    except Exception:  # noqa: BLE001 – COM
        return None
    return (p[-3] * 1000, p[-2] * 1000) if len(p) >= 3 else None


def _anmerkung_suche(spec_typ: str | None, achse: int | None, namen: set[str], meiden: list | None = None):
    """Suchfunktion für die Kante der Anforderung eines Features: Bohrung → Kreiskante (fern von `meiden`); Extrusion →
    Endfläche (+achse), Schnitt → Boden (−achse; Plan: Form/Lage an extrusion/schnitt gilt der Endfläche bzw. dem
    Boden)."""
    if spec_typ in ("bohrung", "normbohrung"):
        return lambda kanten: kreiskante(kanten, namen, meiden)
    if spec_typ not in ("extrusion", "schnitt") or achse is None:
        return lambda kanten: None
    vorzeichen = -1 if spec_typ == "schnitt" else 1
    return lambda kanten: endkante(kanten, namen, achse, vorzeichen)


def anmerkungen_setzen(drw, mu, views: dict, plan: list[Mass], achsen: dict, typen: dict[str, str],
                       enthalten: dict[str, set[str]] | None = None, anmerkungen: list | None = None,
                       besetzt: dict[str, list] | None = None, anzahl: dict[str, int] | None = None) -> list[str]:
    """Rauheit, Form/Lage und Bezüge des Plans setzen (je Eintrag Kante am Ansatzpunkt wählen, einfügen); die Lage setzt
    später `anmerkungen_legen`. `besetzt`: Merkmal → Kreismitten, an denen schon eine Bohrungsangabe hängt; `anzahl`:
    Merkmal → Instanzen (`instanzen`). Liefert die Meldungen; nie stilles Weglassen."""
    cache: dict = {}
    belegt: list = []
    return (rauheit_setzen(drw, mu, views, plan, achsen, typen, enthalten, anmerkungen, cache, besetzt, anzahl, belegt)
            + form_lage_setzen(drw, mu, views, plan, achsen, typen, enthalten, anmerkungen, cache, besetzt, anzahl,
                               belegt)
            + bezuege_setzen(drw, mu, views, plan, achsen, anmerkungen, cache, belegt))


def _einfuegen_mit(drw, view, kanten: list[Kante], belegt: list, umriss: tuple, einfuegen, etikett: str = "",
                   meldungen: list | None = None):
    """Fabrik: Kreis- oder Geradenkante am Ansatzpunkt wählen, mit `einfuegen()` einsetzen, Ansatz zurücklesen (kommt
    nach `belegt`). Liefert `am(Kante, Meldungen)` → (Annotation, Ansatz) oder None; ohne Meldungen gehen sie an
    `meldungen` der Fabrik."""
    def am(k: Kante, meld: list | None = None):
        p = ansatzpunkt(k, kanten, belegt, umriss, meldungen if meld is None else meld, etikett)
        if not _waehle_am_punkt(drw, view, k, p):
            return None
        ann = einfuegen()
        drw.ClearSelection2(True)
        if ann is None:
            return None
        ist = ansatz_lesen(ann) or p
        belegt.append(ist)
        return ann, ist
    return am


def rauheit_setzen(drw, mu, views: dict, plan: list[Mass], achsen: dict, typen: dict[str, str],
                   enthalten: dict[str, set[str]] | None = None, anmerkungen: list | None = None,
                   cache: dict | None = None, besetzt: dict[str, list] | None = None,
                   anzahl: dict[str, int] | None = None, belegt: list | None = None) -> list[str]:
    """Rauheitssymbol (bearbeitet) mit Hinweislinie an der Kante des Merkmals in einer Ansicht des Eintrags
    (`achse`/`modus`). Die Anforderung steht im Feld a unter dem waagrechten Strich (`ISFSymbol.SetText(
    swSFSymbolRoughnessValue1 = 8)`, Spike g; ISO 1302:2002/ISO 21920-1). Meldungen `RAUHEIT_NICHT_GESETZT` (keine Kante,
    Einfügen gescheitert) und `RAUHEIT_NUR_EINE_INSTANZ` (Spike h: eine Mehrfachauswahl ergibt nur eine Hinweislinie)."""
    meldungen, cache, belegt = [], {} if cache is None else cache, [] if belegt is None else belegt
    ext = _ruf(drw, "Extension")
    for m in (m for m in plan if m.quelle == "rauheit"):
        namen = (enthalten or {}).get(m.merkmal) or {m.merkmal}
        rollen = _ansichten_fuer(views, achsen, m.achse, m.modus)
        treffer = _kante_fuer(views, mu, rollen,
                              _anmerkung_suche(typen.get(m.merkmal), m.achse, namen, (besetzt or {}).get(m.merkmal)),
                              cache)
        if treffer is None:
            meldungen.append(f"RAUHEIT_NICHT_GESETZT: {m.merkmal} {m.text} – {_ohne_kante(rollen, m.achse, m.modus)}")
            continue
        rolle, k, kanten = treffer

        def einfuegen(text=m.text):
            sf = ext.InsertSurfaceFinishSymbol3(SF_BEARBEITET, FUEHRUNG_GERADE, 0, 0, 0, 0, PFEIL_GESCHLOSSEN,
                                                "", "", "", "", "", "", "")
            if sf is None:
                return None
            sf.SetText(SF_TEXT_FELD_A, text)
            return _ruf(sf, "GetAnnotation") if sf.GetText(SF_TEXT_FELD_A) == text else None

        umriss = _umriss(kanten)
        am = _einfuegen_mit(drw, views[rolle], kanten, belegt, umriss, einfuegen, f"{m.merkmal} {m.text}", meldungen)
        gesetzt = am(k)
        if gesetzt is None:
            meldungen.append(f"RAUHEIT_NICHT_GESETZT: {m.merkmal} {m.text} – Kante in {rolle} nicht auswählbar oder "
                             "Symbol nicht eingefügt")
            continue
        n = (anzahl or {}).get(m.merkmal, 1)
        if n > 1:
            meldungen.append(f"RAUHEIT_NUR_EINE_INSTANZ: {m.merkmal} {m.text} – Symbol an einer von {n} Instanzen")
        if anmerkungen is not None:
            breite = GROESSE_RAUHEIT[0] + ZEICHEN_MM * len(m.text)
            schraffur = _schraffur(cache, mu, views, rolle, meldungen)
            orte = _orte(typen.get(m.merkmal), kanten, k, namen, m.achse, schraffur)
            anmerkungen.append(Anmerkung(
                "rauheit", m.merkmal, (m.text,), gesetzt[0], rolle, gesetzt[1], umriss, (breite, GROESSE_RAUHEIT[1]),
                (breite / 2 + VERSATZ_RAUHEIT[0], VERSATZ_RAUHEIT[1]), kante=None if k.kreis else (k.a, k.e),
                orte=orte, einhaengen=am if len(orte) > 1 else None, belegt=belegt, schraffur=schraffur or [],
                offen=_offen(typen.get(m.merkmal), kanten, namen, schraffur)))
    return meldungen


def _offen(typ: str | None, kanten: list[Kante], namen: set[str], schraffur: list[tuple] | None) -> list[Kante]:
    """`offene_kanten` eines vertieften Merkmals; ist die Schraffur ungelesen (None), ist nichts offen (Runde D, I4:
    sonst wären im Schnitt alle eigenen Kanten offen)."""
    return offene_kanten(kanten, namen, schraffur) if typ in VERTIEFT and schraffur is not None else []


def _orte(typ: str | None, kanten: list[Kante], k: Kante, namen: set[str], achse: int | None,
          schraffur: list[tuple] | None) -> list[Kante]:
    """Orte einer Rauheit bzw. eines Rahmens: Bohrung → Kreiskanten aller Instanzen; Extrusion (Endfläche +achse) und
    Schnitt (Boden −achse) → die gleichwertigen geraden Kanten der Fläche (`orte_der_flaeche`); bei ungelesener
    Schraffur (None) nur `k` (Runde D, I4: sonst würde der Taschenrand hinter dem Schnitt ein Ort)."""
    if typ in ("bohrung", "normbohrung"):
        return bohrungskreise(kanten, namen)
    if typ in ("extrusion", "schnitt") and schraffur is not None:
        return orte_der_flaeche(kanten, k, namen, achse, schraffur)
    return [k]


def _schraffur(cache: dict, mu, views: dict, rolle: str, meldungen: list | None = None) -> list[tuple] | None:
    """`schraffur_strecken` der Ansicht, je Ansicht einmal (im Kanten-Cache unter („schraffur“, Rolle)). Ist sie nicht
    vollständig gelesen: None und je Grund `SCHRAFFUR_UNGELESEN: <Ansicht> – <Grund>` (Runde D, I4; nie still)."""
    schluessel = ("schraffur", rolle)
    if schluessel not in cache:
        cache[schluessel] = schraffur_strecken(mu, views[rolle])
    strecken, gruende = cache[schluessel]
    if not gruende:
        return strecken
    try:
        name = _ruf(views[rolle], "GetName2")
    except Exception:  # noqa: BLE001 – COM
        name = rolle
    for g in gruende:
        _melde(meldungen, f"SCHRAFFUR_UNGELESEN: {name} – {g}")
    return None


def _rahmen_gesetzt(gt, symbol: str, werte: list[str]) -> bool:
    """Rahmen nach Wirkung prüfen (Live 27.11.: SetFrameSymbols2/SetFrameValues2 melden False, obwohl gesetzt)."""
    try:
        return (list(gt.GetFrameSymbols2(1) or ())[:1] == [symbol]
                and [str(w) for w in list(gt.GetFrameValues(1) or ())[:len(werte)]] == werte)
    except Exception:  # noqa: BLE001 – COM
        return False


def form_lage_setzen(drw, mu, views: dict, plan: list[Mass], achsen: dict, typen: dict[str, str],
                     enthalten: dict[str, set[str]] | None = None, anmerkungen: list | None = None,
                     cache: dict | None = None, besetzt: dict[str, list] | None = None,
                     anzahl: dict[str, int] | None = None, belegt: list | None = None) -> list[str]:
    """Toleranzrahmen (Symbol, Wert, Bezüge) mit Hinweislinie an der Kante des Merkmals (wie die Rauheit). Mehrere
    Instanzen: „n ×“ über dem Rahmen (ISO 1101; `IGtol.SetText(swGTolTextCalloutAbove = 3, …)`, Spike h). Meldungen
    `FORM_LAGE_NICHT_GESETZT`, `FORM_LAGE_NUR_EINE_INSTANZ`."""
    meldungen, cache, belegt = [], {} if cache is None else cache, [] if belegt is None else belegt
    for m in (m for m in plan if m.quelle == "form_lage" and m.form_lage):
        fl = m.form_lage
        etikett = f"{m.merkmal} {fl.art} {fl.wert}"
        namen = (enthalten or {}).get(m.merkmal) or {m.merkmal}
        rollen = _ansichten_fuer(views, achsen, m.achse, m.modus)
        treffer = _kante_fuer(views, mu, rollen,
                              _anmerkung_suche(typen.get(m.merkmal), m.achse, namen, (besetzt or {}).get(m.merkmal)),
                              cache)
        if treffer is None:
            meldungen.append(f"FORM_LAGE_NICHT_GESETZT: {etikett} – {_ohne_kante(rollen, m.achse, m.modus)}")
            continue
        rolle, k, kanten = treffer
        bez = list(fl.bezug) + ["", "", ""]
        wert = fl.wert + (" <MOD-MMC>" if fl.mmr else "")
        n = (anzahl or {}).get(m.merkmal, 1)
        zustand: dict = {}

        def wirkung(zustand=zustand, etikett=etikett, n=n) -> list[str]:  # nach Wirkung, auch nach dem Umhängen
            aus = [] if zustand.get("beschriftet") else [f"FORM_LAGE_NICHT_GESETZT: {etikett} – Rahmen nicht "
                                                         "beschriftet"]
            if n > 1 and not zustand.get("oben"):
                aus.append(f"FORM_LAGE_NUR_EINE_INSTANZ: {etikett} – „{n} ×“ über dem Rahmen nicht gesetzt")
            return aus

        def einfuegen(fl=fl, bez=bez, wert=wert, n=n, zustand=zustand):
            gt = _ruf(drw, "InsertGtol")
            if gt is None:
                return None
            gt.SetFrameSymbols2(1, fl.symbol, False, "", False, "", "", "", "")
            gt.SetFrameValues2(1, wert, "", bez[0], bez[1], bez[2])
            zustand["beschriftet"] = _rahmen_gesetzt(gt, fl.symbol, [wert, "", bez[0], bez[1], bez[2]])
            if n > 1:
                gt.SetText(RAHMEN_TEXT_OBEN, f"{n} ×")
                zustand["oben"] = gt.GetText(RAHMEN_TEXT_OBEN) == f"{n} ×"
            return _ruf(gt, "GetAnnotation")

        umriss = _umriss(kanten)
        am = _einfuegen_mit(drw, views[rolle], kanten, belegt, umriss, einfuegen, etikett, meldungen)
        gesetzt = am(k)
        if gesetzt is None:
            meldungen.append(f"FORM_LAGE_NICHT_GESETZT: {etikett} – Kante in {rolle} nicht auswählbar oder "
                             "InsertGtol abgelehnt")
            continue
        if anmerkungen is None:  # sonst im Endstand (`anmerkungen_wirkung`, Runde E M7)
            meldungen += wirkung()
        else:
            breite = RAHMEN_ZELLE_MM * (1 + len(fl.bezug)) + ZEICHEN_MM * len(fl.wert) + 2
            hoehe = RAHMEN_HOEHE_MM + (RAHMEN_TEXT_OBEN_MM if n > 1 else 0.0)
            schraffur = _schraffur(cache, mu, views, rolle, meldungen)
            orte = _orte(typen.get(m.merkmal), kanten, k, namen, m.achse, schraffur)
            anmerkungen.append(Anmerkung(
                "form_lage", m.merkmal, (" ".join((fl.wert,) + tuple(fl.bezug)),) + ((f"{n} ×",) if n > 1 else ()),
                gesetzt[0], rolle, gesetzt[1],
                umriss, (breite, hoehe), (breite / 2, hoehe / 2 - RAHMEN_HOEHE_MM),
                kante=None if k.kreis else (k.a, k.e),
                orte=orte, einhaengen=am if len(orte) > 1 else None, belegt=belegt, schraffur=schraffur or [],
                offen=_offen(typen.get(m.merkmal), kanten, namen, schraffur), wirkung=wirkung))
    return meldungen


def bezuege_setzen(drw, mu, views: dict, plan: list[Mass], achsen: dict, anmerkungen: list | None = None,
                   cache: dict | None = None, belegt: list | None = None) -> list[str]:
    """Bezugsdreieck mit Buchstabe an der Kante der Ankerfläche (`{feature, flaeche: "±a"}`) in einer Ansicht quer zu
    ihrer Normale. Meldung `BEZUG_NICHT_GESETZT`."""
    meldungen, cache, belegt = [], {} if cache is None else cache, [] if belegt is None else belegt
    for m in (m for m in plan if m.quelle == "bezug"):
        anker = m.anker or {}
        flaeche = anker.get("flaeche")
        if not (isinstance(flaeche, str) and len(flaeche) == 2 and flaeche[0] in "+-" and flaeche[1] in "xyz"
                and anker.get("feature")):
            meldungen.append(f"BEZUG_NICHT_GESETZT: {m.text} – Anker {anker} ohne Flächenrichtung")
            continue
        achse, vorzeichen = "xyz".index(flaeche[1]), (-1 if flaeche[0] == "-" else 1)
        treffer = _kante_fuer(views, mu, _ansichten_fuer(views, achsen, achse, "quer"),
                              lambda kanten, f=anker["feature"], a=achse, v=vorzeichen: endkante(kanten, {f}, a, v),
                              cache)
        if treffer is None:
            meldungen.append(f"BEZUG_NICHT_GESETZT: {m.text} – keine Kante der Fläche {anker['feature']} {flaeche}")
            continue
        rolle, k, kanten = treffer
        zustand: dict = {}

        def einfuegen(text=m.text, zustand=zustand):
            tag = _ruf(drw, "InsertDatumTag2")
            if tag is None:
                return None
            tag.SetLabel(text)
            zustand["label"] = _ruf(tag, "GetLabel") == text
            return _ruf(tag, "GetAnnotation")

        umriss = _umriss(kanten)
        gesetzt = _einfuegen_mit(drw, views[rolle], kanten, belegt, umriss, einfuegen, f"Bezug {m.text}", meldungen)(k)
        if gesetzt is None:
            meldungen.append(f"BEZUG_NICHT_GESETZT: {m.text} – Kante in {rolle} nicht auswählbar oder InsertDatumTag2 "
                             "abgelehnt")
            continue
        if not zustand.get("label"):
            meldungen.append(f"BEZUG_NICHT_GESETZT: {m.text} – Buchstabe nicht gesetzt")
        if anmerkungen is not None:
            anmerkungen.append(Anmerkung("bezug", m.merkmal, (m.text,), gesetzt[0], rolle, gesetzt[1], umriss,
                                         GROESSE_BEZUG, (0.0, 0.0), kante=(k.a, k.e), belegt=belegt,
                                         schraffur=_schraffur(cache, mu, views, rolle, meldungen) or []))
    return meldungen


def _loesche_anmerkung(drw, ann) -> bool:
    drw.ClearSelection2(True)
    ok = ann.Select2(False, 0) and _ruf(drw, "Extension").DeleteSelection2(0)
    drw.ClearSelection2(True)
    return bool(ok)


def _umhaengen(drw, a: Anmerkung, ziel: Kante, meldungen: list | None) -> bool:
    """Anmerkung an den Ort `ziel` neu einfügen und die alte löschen (nach Wirkung gemeldet). Der alte Ansatz
    verlässt `belegt` vorher (Nachbesserung C: sonst sperrt er am kleinen Kreis die Nachbarpunkte). Die verworfenen
    Lagen bleiben am alten Ort, die des neuen kommen zurück (Runde E, I-3). Ob der neue Rahmen beschriftet ist, zählt
    erst im Endstand (`anmerkungen_wirkung`, Runde E M7: sonst blieb die Meldung einer Zwischenstufe stehen)."""
    alt = a.ort_nr(a.instanz())
    if a.belegt is not None and a.anker in a.belegt:
        a.belegt.remove(a.anker)
    neu = a.einhaengen(ziel, meldungen)
    if neu is None:
        if a.belegt is not None:
            a.belegt.append(a.anker)
        _melde(meldungen, f"ANMERKUNG_NICHT_UMGEHAENGT: {a.merkmal} {a.zeilen[0]}")
        return False
    if not _loesche_anmerkung(drw, a.ann):
        _melde(meldungen, f"ANMERKUNG_DOPPELT: {a.merkmal} {a.zeilen[0]} – alte nicht gelöscht")
    a.ann, a.anker = neu
    a.soll = None  # Gesamtreview (b): die gewählte Lage gehört zum alten Ort
    if not ziel.kreis:
        a.kante = (ziel.a, ziel.e)
    if alt is not None:
        a.verworfen_orte[alt] = a.verworfen
    a.verworfen = a.verworfen_orte.pop(a.ort_nr(ziel), [])
    return True


def anmerkungen_wirkung(anmerkungen: list[Anmerkung]) -> list[str]:
    """Runde E (M7): Wirkung jeder Anmerkung im Endstand (`wirkung`: Rahmen beschriftet, „n ×“ gesetzt) – nach der
    Lesbarkeitsschleife, also an der zuletzt eingefügten Annotation (auch nach dem Umhängen)."""
    return [text for a in anmerkungen for text in (a.wirkung() if a.wirkung else [])]


def instanzen_umhaengen(drw, anmerkungen: list[Anmerkung], meldungen: list | None = None) -> None:
    """Ist die beste Runde fixiert (`fixiert` = (Lage, Ort)), kommt die Anmerkung an deren Ort zurück (Nachbesserung
    C). Die Wahl des Orts selbst trifft `_gemeinsam` (Runde E, I-3: eine zweite Bewertung hier – ohne die Hinweislinien
    der Angaben, ein belegter Ort als Verstoß – hängte jede Runde um, `_gemeinsam` hängte zurück)."""
    for a in anmerkungen:
        if a.fixiert is None or len(a.orte) < 2 or a.einhaengen is None:
            continue
        ziel = a.fixiert[1]
        if ziel is not None and ziel is not a.instanz() and not _umhaengen(drw, a, ziel, meldungen):
            a.fixiert = None  # Gesamtreview (b): die Lage am anderen Ort gilt nicht am alten Anker – neu legen


def _setze(a: Anmerkung, lage: tuple[float, float]) -> None:
    """`SetPosition2` mit Bezugspunkt = Mitte − Versatz, dann die wirkliche Lage zurücklesen."""
    a.soll = lage
    versatz = a.versatz_bei(lage)
    a.ann.SetPosition2((lage[0] - versatz[0]) / 1000, (lage[1] - versatz[1]) / 1000, 0)
    ist = [c * 1000 for c in list(_ruf(a.ann, "GetPosition"))[:2]]
    a.lage = (round(ist[0] + versatz[0], 3), round(ist[1] + versatz[1], 3))


def _gegen_andere(a: Anmerkung, anmerkungen: list[Anmerkung], hindernisse, texte, hinweislinien) -> tuple:
    """Hindernisse, Texte, Ansätze und Hinweislinien für `a` samt aller anderen gelegten Anmerkungen."""
    andere = [b for b in anmerkungen if b is not a and b.lage is not None]
    linien = [s for b in andere for s in b.linien()]
    return (list(hindernisse) + [s for b in andere for s in _rechteck_strecken(b.rechteck())] + linien,
            list(texte) + [b.rechteck() for b in andere],
            [b.fusspunkt() for b in andere], list(hinweislinien) + linien)


def _paar(a: Anmerkung, la: tuple, b: Anmerkung, lb: tuple) -> int:
    """Verstöße von `a` an `la` gegen `b` an `lb` allein – wie `_gegen_andere` sie zählt (Rechteck und Linien von b als
    Hindernis, sein Rechteck als Text, sein Ansatz, seine Linien als Hinweislinien); Schraffur und eigenes Symbol
    gehören zur Lage selbst und zählen hier nicht."""
    linien = b.linien(lb)
    return sum(a.verstoesse(la, _rechteck_strecken(b.rechteck(lb)) + linien, [b.rechteck(lb)], (), (),
                            [b.fusspunkt(lb)], linien, selbst=False).values())


def _huelle(a: Anmerkung, lage: tuple) -> tuple[float, float, float, float]:
    """Hüllrechteck einer Anmerkung an `lage`: Rechteck, Hinweislinie, Verlängerung (samt Fußpunkt)."""
    r = a.rechteck(lage)
    xs, ys = [r[0], r[2]], [r[1], r[3]]
    for p, q in a.linien(lage):
        xs += [p[0], q[0]]
        ys += [p[1], q[1]]
    return (min(xs), min(ys), max(xs), max(ys))


def _getrennt(h1: tuple, h2: tuple) -> bool:
    """Liegen zwei Hüllen weiter als `ANSATZ_ABSTAND_MM` auseinander? Dann gibt es zwischen ihnen keinen Verstoß
    (Kreuzungen brauchen Berührung, ein Ansatz zählt erst unter diesem Abstand)."""
    g = ANSATZ_ABSTAND_MM
    return h1[0] - h2[2] > g or h2[0] - h1[2] > g or h1[1] - h2[3] > g or h2[1] - h1[3] > g


def _paar_kosten(a: Anmerkung, la: tuple, ha: tuple, b: Anmerkung, lb: tuple, hb: tuple) -> int:
    """Gegenseitige Verstöße zweier Kandidaten (`_paar` in beide Richtungen); getrennte Hüllen zählen nichts und werden
    nicht gerechnet (Runde E: die Paare machten den Großteil der Laufzeit von `_gemeinsam`)."""
    if _getrennt(ha, hb):
        return 0
    return _paar(a, la, b, lb) + _paar(b, lb, a, la)


def _probe(a: Anmerkung, ort: Kante) -> Anmerkung:
    """`a` an einem anderen Ort, angesetzt, wo `ansatzpunkt` dort ansetzen würde (Kreis: unter 45°/135°/… vom Körper
    weg, Gerade: Mitte) – Runde D: mit der Kreismitte als Anker lief die Probe-Hinweislinie durch die eigene Bohrung
    und ein anderer Ort sah schlechter aus, als er ist."""
    anker = ansatzpunkt(ort, [ort], [], a.umriss)
    return replace(a, anker=anker, kante=None if ort.kreis else (ort.a, ort.e), lage=None,
                   verworfen=list(a.verworfen_orte.get(a.ort_nr(ort), ())))


def _gemeinsam(gruppe: list[Anmerkung], alle: list[Anmerkung], hindernisse, texte, kanten, masslinien,
               hinweislinien, drw=None, meldungen: list | None = None, besetzt: dict | None = None) -> None:
    """Runde D (C): Lagen einer Ansicht gemeinsam wählen. Je Anmerkung und Ort die besten `SUCHE_JE_ANMERKUNG` nicht
    verworfenen Kandidaten gegen alles Feste (Hindernisse, Texte, Kanten, schon gelegte und fixierte Anmerkungen) –
    mit `drw` auch an den gleichwertigen anderen Orten (`orte`; Live SpannplatteZ: unter ▱ 0,02 zwischen den Taschen
    steht „SCHNITT A-A“, frei ist es nur an der Unterseite links oder rechts; ein Ort mit der Bohrungsangabe desselben
    Merkmals, `besetzt`, verliert bei Gleichstand). Dann die Kombination mit der kleinsten Summe aller Verstöße samt
    der gegenseitigen (`_paar_kosten`, in beide Richtungen – so zählt `anmerkungen_pruefen`; getrennte Hüllen zählen
    nichts, Runde E); bei Gleichstand weniger Orte mit Bohrungsangabe, dann der heutige Ort, dann der Rang. Ein Ort,
    an dem alle Lagen verworfen sind, bietet nur die beste verworfene, und die kommt nach allen freien (Runde E). Bis
    `SUCHE_HOECHSTENS` Kombinationen vollständig, sonst Strahlsuche (`STRAHL_BREITE`). Liegt die Wahl an einem anderen
    Ort, wird umgehängt (`_umhaengen`); scheitert das, gilt die beste Lage am heutigen Ort."""
    kand = []                    # je Anmerkung: [(Kosten, besetzt, Ortrang, Rang, Lage, Probe, Ort, alle verworfen)]
    for a in gruppe:
        h, t_, ans, hl = _gegen_andere(a, alle, hindernisse, texte, hinweislinien)
        heute = a.instanz()
        orte = [heute] + ([o for o in a.orte if o is not heute] if drw is not None and a.einhaengen else [])
        liste_a = []
        for r_ort, ort in enumerate(orte):
            probe = a if r_ort == 0 else _probe(a, ort)
            liste = probe.kandidaten(h, t_, kanten, masslinien, ans, hl)
            frei = [lage for lage in liste if not any(math.dist(lage, w) <= 0.5 for w in probe.verworfen)]
            alle_verworfen = int(not frei)   # Rückfall: die beste verworfene Lage, nach allen freien (Runde E)
            frei = (frei or liste[:1])[:SUCHE_JE_ANMERKUNG]
            # Runde E: die Lage der letzten Runde bleibt am heutigen Ort Kandidat, solange nicht verworfen – nach dem
            # Umhängen setzt die Hinweislinie anders an als die Probe annahm, ihre Lage fehlt dann unter `_roh`
            if (r_ort == 0 and a.soll is not None and not any(math.dist(a.soll, w) <= 0.5 for w in a.verworfen)
                    and not any(math.dist(a.soll, lage) <= 0.5 for lage in frei)):
                frei, alle_verworfen = (frei + [a.soll], 0) if not alle_verworfen else ([a.soll], 0)
            mehr = int(ort is not None and ort.kreis is not None
                       and any(math.dist(ort.kreis[0], q) < PUNKT_TOL_MM for q in (besetzt or {}).get(a.merkmal, ())))
            liste_a += [(probe.bewerten(lage, h, t_, kanten, masslinien, ans, hl), mehr, r_ort, i, lage, probe, ort,
                         alle_verworfen) for i, lage in enumerate(frei)]
        kand.append(sorted(liste_a, key=lambda e: (e[7],) + e[:4]))
    n = len(gruppe)
    huellen = [[_huelle(e[5], e[4]) for e in liste] for liste in kand]
    paar = {(i, j): [[_paar_kosten(ei[5], ei[4], hi, ej[5], ej[4], hj) for ej, hj in zip(kand[j], huellen[j])]
                     for ei, hi in zip(kand[i], huellen[i])] for i in range(n) for j in range(i + 1, n)}
    strahl = [((0, 0, 0, 0), ())]              # ((verworfen, Summe, besetzt, Ortwechsel), Wahl je Anmerkung bisher)
    zahl = 1
    for i in range(n):
        zahl *= len(kand[i])
        weiter = []
        for (verw, summe, besetzt_n, wechsel), wahl in strahl:
            for k, e in enumerate(kand[i]):
                plus = e[0] + sum(paar[(j, i)][wahl[j]][k] for j in range(i))
                weiter.append(((verw + e[7], summe + plus, besetzt_n + e[1], wechsel + (e[2] > 0)), wahl + (k,)))
        weiter.sort()
        strahl = weiter if zahl <= SUCHE_HOECHSTENS else weiter[:STRAHL_BREITE]
    _, wahl = min(strahl)
    for a, liste, k in zip(gruppe, kand, wahl):
        _, _, r_ort, _, lage, _, ort, _ = liste[k]
        if r_ort and not _umhaengen(drw, a, ort, meldungen):
            lage = next(e[4] for e in liste if e[2] == 0)
        _setze(a, lage)


def anmerkungen_legen(anmerkungen: list[Anmerkung], hindernisse: list[tuple], texte: list[tuple] | None = None,
                      kanten: list[tuple] = (), masslinien: list[tuple] = (),
                      hinweislinien: list[tuple] = (), drw=None, meldungen: list | None = None,
                      besetzt: dict | None = None) -> list[tuple]:
    """Lagen der Anmerkungen (Runde D, C: gemeinsam je Ansicht, `_gemeinsam`, mit `drw` auch über die gleichwertigen
    Orte; vorher nacheinander mit Nachlegen – die Hinweislinie von ▱ 0,02 lief durch „SCHNITT A-A“, weil jede
    Anmerkung nur ihre eigenen Verstöße sah). Verstöße nach `Anmerkung.bewerten` gegen `hindernisse`, `texte`,
    `kanten`, `masslinien`, `hinweislinien` und die anderen Anmerkungen; eine fixierte Lage (beste Runde) gilt
    unverändert und ist für die anderen fest, ebenso die Ansichten, die schon gelegt sind. `besetzt`: Merkmal →
    Kreismitten mit Bohrungsangabe. `SetPosition2` mit Bezugspunkt = Mitte − Versatz; die wirkliche Lage wird
    zurückgelesen (ein Bezugskasten rückt auf die Senkrechte zur Kante). Liefert Rechtecke und Linien aller
    Anmerkungen als Strecken."""
    texte = list(texte or [])
    if drw is not None:  # beste Runde: an deren Ort zurück (Runde E: den Ort sonst wählt allein `_gemeinsam`)
        instanzen_umhaengen(drw, anmerkungen, meldungen)
    for a in anmerkungen:
        a.lage = None  # noch nicht gelegt: zählt für die anderen nicht
    for a in anmerkungen:
        if a.fixiert is not None:
            _setze(a, a.fixiert[0])
    gruppen: dict[str, list[Anmerkung]] = {}
    for a in anmerkungen:
        if a.fixiert is None:
            gruppen.setdefault(a.rolle, []).append(a)
    for gruppe in gruppen.values():
        _gemeinsam(gruppe, anmerkungen, hindernisse, texte, kanten, masslinien, hinweislinien, drw, meldungen,
                   besetzt)
    return [s for a in anmerkungen for s in _rechteck_strecken(a.rechteck()) + a.linien()]


def anmerkungen_pruefen(anmerkungen: list[Anmerkung], hindernisse: list[tuple] = (), texte: list[tuple] = (),
                        kanten: list[tuple] = (), masslinien: list[tuple] = (),
                        hinweislinien: list[tuple] = ()) -> list[str]:
    """Nach der letzten Runde (Nachbesserung C, nie still): jede Anmerkung an ihrer zurückgelesenen Lage gegen alles,
    was steht – `hindernisse` usw. wie bei `anmerkungen_legen` und alle anderen Anmerkungen (Rechteck, Linien,
    Ansatz). Meldung `ANMERKUNG_KREUZT: <merkmal> <art> „<text>“ – <was> (<anzahl>), …` je Anmerkung mit Kreuzungen;
    die Nähe (`NAEHE`: Kante näher als 3 mm, Ansatz näher als 4 mm) getrennt als `ANMERKUNG_ZU_NAH: …` (Runde D, M3)."""
    meldungen = []
    for a in anmerkungen:
        if a.lage is None:
            continue
        h, t_, ans, hl = _gegen_andere(a, anmerkungen, hindernisse, texte, hinweislinien)
        v = a.verstoesse(a.lage, h, t_, kanten, masslinien, ans, hl)
        for code, arten in (("ANMERKUNG_KREUZT", [k for k in v if k not in NAEHE]),
                            ("ANMERKUNG_ZU_NAH", [k for k in v if k in NAEHE])):
            if arten:
                was = ", ".join(f"{k} ({v[k]})" for k in arten)
                meldungen.append(f"{code}: {a.merkmal} {a.art} „{a.zeilen[0]}“ – {was}")
    return meldungen


def _rechteck_strecken(r: tuple) -> list[tuple]:
    ecken = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    return list(zip(ecken, ecken[1:] + ecken[:1]))


# --- Sammelangaben ----------------------------------------------------------------------------------------------------


def _notiz_an(drw, text: str, x_mm: float, oben_mm: float):
    """Hinweis auf dem Blatt (`IDrawingDoc.EditSheet` vorher; Live 27.11.: sonst gehört er zur zuletzt aktiven
    Ansicht) mit der linken oberen Ecke bei (x, oben)."""
    _ruf(drw, "EditSheet")
    drw.ClearSelection2(True)
    note = drw.InsertNote(text)
    if note is None:
        return None
    ann = _ruf(note, "GetAnnotation")
    ann.SetPosition2(x_mm / 1000, (oben_mm - SAMMEL_OBERKANTE_MM) / 1000, 0)
    return ann


def _rauheitssymbol_frei(drw, text: str, x_mm: float, y_mm: float):
    """Rauheitssymbol (Grundsymbol, ohne Hinweislinie) auf dem Blatt, Feld a `text`, Spitze bei (x, y)."""
    _ruf(drw, "EditSheet")
    drw.ClearSelection2(True)
    sf = _ruf(drw, "Extension").InsertSurfaceFinishSymbol3(SF_GRUND, OHNE_FUEHRUNG, x_mm / 1000, y_mm / 1000, 0, 0,
                                                           PFEIL_GESCHLOSSEN, "", "", "", "", "", "", "")
    if sf is None:
        return None
    sf.SetText(SF_TEXT_FELD_A, text)
    if sf.GetText(SF_TEXT_FELD_A) != text:
        return None
    ann = _ruf(sf, "GetAnnotation")
    ann.SetPosition2(x_mm / 1000, y_mm / 1000, 0)
    return ann


def _rechteck_auf_blatt(drw, r: tuple[float, float, float, float]) -> bool:
    """Rechteck (Blatt-mm) als Skizze auf dem Blatt. Eine Blattskizze folgt dem Blattmaßstab (Spike 28.11.: bei 1:2
    halb so groß), die Koordinaten werden deshalb durch ihn geteilt; `AddToDB`, damit nichts einrastet."""
    _ruf(drw, "EditSheet")
    drw.ClearSelection2(True)
    eig = list(_ruf(_ruf(drw, "GetCurrentSheet"), "GetProperties2"))
    f = eig[2] / eig[3] if eig[3] else 1.0
    skm = _ruf(drw, "SketchManager")
    skm.AddToDB = True
    try:
        segs = skm.CreateCornerRectangle(r[0] / 1000 / f, r[1] / 1000 / f, 0, r[2] / 1000 / f, r[3] / 1000 / f, 0)
    finally:
        skm.AddToDB = False
    segs = list(segs or ())
    for s in segs:  # Live 28.11.: sonst blau im PDF (Farbe der unterbestimmten Skizze); 0 = schwarz (COLORREF)
        s.Color = SCHWARZ
    drw.ClearSelection2(True)
    return len(segs) == 4 and all(s.Color == SCHWARZ for s in segs)


def sammelangaben_setzen(drw, zeilen: list[str], format_: str, hoehe_mm: float) -> list[str]:
    """Sammelhinweis ohne Hinweislinie, linke obere Ecke an der Oberkante des Bands, und rechts das Rauheitsfeld
    (Nutzer 28.11.2026, `sammelfeld.rauheitsfeld`): Kasten, Rauheitssymbol nach ISO 1302:2002 (Grundsymbol – die
    Halbzeugflächen bleiben roh –, Feld a `SAMMEL_RAUHEIT`) und der Hinweis „Alle Flächen ohne andere Angabe“. Lage
    über `SetPosition2` (`InsertNote` ohne Auswahl legt den Hinweis sonst unter das Blatt, Spike a). Liefert Meldungen
    `SAMMELANGABEN_NICHT_GESETZT`."""
    umbrochen, _ = sammel_aufteilung(zeilen)
    band = sammelband(format_, hoehe_mm)
    feld = rauheitsfeld(band, zeilen)
    meldungen = []
    x, lage_y = sammelzeilen_lage(band)
    if umbrochen and _notiz_an(drw, "\n".join(umbrochen), x, lage_y + SAMMEL_OBERKANTE_MM) is None:
        meldungen.append("SAMMELANGABEN_NICHT_GESETZT: InsertNote abgelehnt")
    if _rauheitssymbol_frei(drw, SAMMEL_RAUHEIT, *feld.symbol) is None:
        meldungen.append(f"SAMMELANGABEN_NICHT_GESETZT: Rauheitssymbol {SAMMEL_RAUHEIT} – nicht eingefügt")
    hinweis = "\n".join(SAMMEL_RAUHEIT_HINWEIS_ZEILEN)
    if _notiz_an(drw, hinweis, feld.hinweis[0], feld.hinweis[1] + SAMMEL_OBERKANTE_MM) is None:
        meldungen.append(f"SAMMELANGABEN_NICHT_GESETZT: {' '.join(SAMMEL_RAUHEIT_HINWEIS_ZEILEN)} – InsertNote abgelehnt")
    if not _rechteck_auf_blatt(drw, feld.rahmen):
        meldungen.append("SAMMELANGABEN_NICHT_GESETZT: Rahmen des Rauheitsfelds – Skizze abgelehnt")
    drw.ClearSelection2(True)
    return meldungen


def _ausserhalb(r: tuple, feld: tuple, tol: float = 0.5) -> bool:
    return r[0] < feld[0] - tol or r[1] < feld[1] - tol or r[2] > feld[2] + tol or r[3] > feld[3] + tol


def _ueber(r: tuple, feld: tuple, tol: float = 0.5) -> bool:
    return r[0] < feld[2] - tol and feld[0] < r[2] - tol and r[1] < feld[3] - tol and feld[1] < r[3] - tol


def _mm(r: tuple) -> str:
    return f"({r[0]:.0f}, {r[1]:.0f})–({r[2]:.0f}, {r[3]:.0f}) mm"


def sammel_pruefen(pdf_texte: list[tuple[str, tuple]], zeilen: list[str], band: tuple) -> list[str]:
    """Stehen alle Zeilen der Sammelangaben (`sammel_aufteilung`) im PDF und innerhalb des Bands, ohne das
    Rauheitsfeld zu überdecken, und die Texte des Rauheitsfelds (`SAMMEL_RAUHEIT_FELD`) im Kasten? (`pruefe_pdf`
    übergeht Texte am Schriftfeld; ein Überlauf fiele sonst nicht auf.) Gleiche Texte anderswo (eine Merkmalsrauheit
    „Ra 3,2“) zählen nicht: es gilt der nächste Treffer."""
    meldungen = []
    feld = rauheitsfeld(band, zeilen).rahmen
    for z in sammel_aufteilung(zeilen)[0]:
        treffer = [r for t, r in pdf_texte if t == z.strip()]
        if not treffer:
            meldungen.append(f"SAMMELANGABE_FEHLT: „{z}“ nicht im PDF")
            continue
        r = min(treffer, key=lambda r: math.dist((r[0], r[1]), (band[0], band[3])))
        if _ausserhalb(r, band):
            meldungen.append(f"SAMMELANGABE_UEBERLAUF: „{z}“ bei {_mm(r)} außerhalb des Bands {_mm(band)}")
        elif _ueber(r, feld):
            meldungen.append(f"SAMMELANGABE_UEBERLAUF: „{z}“ bei {_mm(r)} überdeckt das Rauheitsfeld {_mm(feld)}")
    mitte = ((feld[0] + feld[2]) / 2, (feld[1] + feld[3]) / 2)
    for z in SAMMEL_RAUHEIT_FELD:
        treffer = [r for t, r in pdf_texte if t == z]
        if not treffer:
            meldungen.append(f"SAMMELANGABE_FEHLT: „{z}“ nicht im PDF")
            continue
        r = min(treffer, key=lambda r: math.dist(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), mitte))
        if _ausserhalb(r, feld):
            meldungen.append(f"SAMMELANGABE_UEBERLAUF: „{z}“ bei {_mm(r)} außerhalb des Rauheitsfelds {_mm(feld)}")
    return meldungen
