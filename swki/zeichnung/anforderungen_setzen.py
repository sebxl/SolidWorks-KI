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
IDatumTag.SetLabel (1), GetAnnotation; ISFSymbol.GetAnnotation; IAnnotation.SetPosition2 (3, 2014), GetPosition.
"""

import math
from dataclasses import dataclass, field

from swki.verbindung import callout_leer, r8_array
from swki.zeichnung.angaben import _enthalten, bohrbilder, hinweis_lagen_bewertet
from swki.zeichnung.bemassen import _anzeige, _loesche, _ruf, kurzname
from swki.zeichnung.blatt import SCHRIFTFELD_MM, zeichenfeld
from swki.zeichnung.lesbarkeit import _schneidet
from swki.zeichnung.massplan import Mass
from swki.zeichnung.toleranzangaben import SAMMEL_RAUHEIT, Toleranz

TOL_BILAT, TOL_SYMMETRISCH, TOL_PASSUNG = 2, 4, 7   # swTolType_e
PASSUNG_EINZEILIG = 3                               # FitDisplayStyle (Spike e: „200,00 H7“ in einer Zeile)
HUELLE = "<MOD-EP>"                                 # Symboldatei gtol97.sym, „Encompassing“ (Spike f)
PRAEFIX_TEXT, SUFFIX_TEXT = 1, 2                    # swDimensionTextParts_e
EINE_KONFIG = 1                                     # swInConfigurationOpts_e.swThisConfiguration
KANTE, ECKPUNKT, SILHOUETTE = 1, 2, 4               # swViewEntityType_e
SF_BEARBEITET, FUEHRUNG_GERADE, PFEIL_GESCHLOSSEN = 1, 1, 1  # swSFSymType_e, swLeaderStyle_e, swArrowStyle_e
LINEAR = (2, 11, 12)                                # swDimensionType_e: Linear, HorLinear, VertLinear
RUND = (5, 6, 14, 15)                               # swDimensionType_e: Radial, Diameter, RadialLinear, DiametricLinear
PUNKT_TOL_MM = 0.1                                  # Bezugspunkt liegt auf der Kante / in der Kreismitte
KANTE_VERLAENGERT_MM = 1.0                          # Bezugspunkt höchstens so weit hinter dem Kantenende (virtuelle
#                                                     Ecke einer Fase: Buchse f3 setzt 0,5 mm über der Bohrungskante an)
WERT_TOL_MM = 0.005                                 # neues Zeichnungsmaß misst dasselbe wie das Modellmaß
HILFSLINIE_LUECKE_MM = 1.0                          # wie zeichnen.HILFSLINIE_LUECKE_MM
HILFSLINIE_KREIS_MM = 6.0                           # Hilfslinie an einer Kreismitte beginnt höchstens so weit hinter dem Kreis
# Größe (Breite, Höhe) und Versatz (Mitte − Bezugspunkt der Annotation) in Blatt-mm, live gemessen 27.11. (Text 3,5 mm):
# Rauheit: Bezugspunkt = Spitze des Symbols, Symbol und Text rechts darüber (Breite = Grundbreite + Text);
# Rahmen: Bezugspunkt = linke obere Ecke; Bezug: Bezugspunkt = Ansatz der Hinweislinie am Kasten
# Rauheit mit Text im Feld a (unter dem Strich): Höhe und Versatz geschätzt nach Spike g, live nachgemessen
GROESSE_RAUHEIT, VERSATZ_RAUHEIT = (8.5, 10.0), (-2.6, 5.0)
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
SAMMEL_ZEICHEN = 72                                 # Zeichen je Zeile im Band (180 mm, live 2,36 mm je Zeichen)
SAMMEL_ZEILENABSTAND_MM = 4.55                      # Hinweistext 3,5 mm, live 27.11. vermessen
SAMMEL_RAUHEIT_ZEICHEN_MM = 2.6                     # „Oberflächen ohne Angabe: Ra 3,2“ live 78 mm für 31 Zeichen
SAMMEL_SPALT_ZEICHEN = 4                            # Abstand Sammelzeile – allgemeine Rauheit rechts daneben
SAMMEL_OBERKANTE_MM = 1.4                           # Textoberkante über `IAnnotation.GetPosition` (Live 19.11.)
# Allgemeine Rauheit als eigener Hinweis rechts im Band (Z1.4 sucht `SAMMEL_RAUHEIT` im Text der Notizen); Wortlaut
# ist ein Vorschlag (ISO 21920-1 zeichnet sie als Symbol „√Ra 3,2 (√)“ in Schriftfeldnähe, recherche.md Kap. 6: C)
SAMMEL_RAUHEIT_ZEILE = f"Oberflächen ohne Angabe: {SAMMEL_RAUHEIT}"


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
    punkt: bool = False                    # Eckpunkt (IVertex) statt Kante
    radius_mm: float | None = None         # Kreis: Radius im Modell (mm)

    def laenge(self) -> float:
        return math.dist(self.a, self.e)


def sichtbare_kanten(mu, view) -> list[Kante]:
    """Sichtbare Kanten der Ansicht (Kanten, Silhouetten, Eckpunkte) mit Blatt- und Modellkoordinaten und den Features
    ihrer Nachbarflächen (`IFace2.GetFeature`; Silhouetten und Eckpunkte ohne). Schnittansichten liefern die Kanten der
    Schnittflächen mit (Feature „Schnitt1“, Live 27.11.)."""
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
    for p in list(view.GetVisibleEntities2(callout_leer(), ECKPUNKT) or ()):
        try:
            q_m = tuple(_ruf(p, "GetPoint"))[:3]
        except Exception:  # noqa: BLE001 – COM
            continue
        b = blatt(q_m)
        aus.append(Kante(p, b, b, tuple(x * 1000 for x in q_m), tuple(x * 1000 for x in q_m), punkt=True))
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
                   hilfslinie: tuple | None = None) -> Kante | None:
    """Kante, an der ein Maß in `punkt` ansetzt (Blatt-mm), in dieser Reihenfolge:
    1. die gerade Kante quer zur Messrichtung (Maßlinie waagrecht „h“ → senkrechte Kante), auf deren Strecke der Punkt
       liegt, höchstens `KANTE_VERLAENGERT_MM` über ihr Ende hinaus (Review Task 5: nicht irgendwo auf ihrer Geraden –
       live lag eine Taschenkante 15 mm weiter auf derselben Linie;
       trifft zugleich ein Kreis, gewinnt die Kante),
    2. die Kreiskante, deren Mitte auf der Hilfslinie liegt (`_kreis_der_hilfslinie`; ohne Hilfslinie: Mitte im Punkt),
    3. ein Eckpunkt im Punkt (Live 27.11.: Fase der Buchse, eine Seite endet an der Fasenkante).
    Toleranz `PUNKT_TOL_MM`; unter mehreren geraden Kanten die nächste zum Punkt."""
    passend = []
    for k in kanten:
        if k.kreis or k.punkt or k.laenge() < 1e-6:
            continue
        dx, dy = abs(k.e[0] - k.a[0]), abs(k.e[1] - k.a[1])
        quer = dx < 1e-3 * max(dy, 1e-9) if richtung == "h" else dy < 1e-3 * max(dx, 1e-9)
        if (quer and _abstand_gerade(punkt, k.a, k.e) <= PUNKT_TOL_MM
                and _abstand_strecke(punkt, k.a, k.e) <= KANTE_VERLAENGERT_MM):
            passend.append(k)
    if passend:
        return min(passend, key=lambda k: _abstand_strecke(punkt, k.a, k.e))
    if hilfslinie is not None:
        k = _kreis_der_hilfslinie(hilfslinie, kanten)
        if k is not None:
            return k
    kreise = [k for k in kanten if k.kreis and math.dist(k.kreis[0], punkt) <= PUNKT_TOL_MM]
    if kreise:
        return max(kreise, key=lambda k: k.kreis[1])
    ecke = min((k for k in kanten if k.punkt and math.dist(k.a, punkt) <= PUNKT_TOL_MM),
               key=lambda k: math.dist(k.a, punkt), default=None)
    if ecke is not None:
        return ecke
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


def _ersetze(drw, mu, view, dd, kanten: list[Kante] | None = None, bezug=None) -> tuple[object | None, str]:
    """Ein Modellmaß als Zeichnungsmaß an denselben Bezugspunkten neu setzen. Liefert (neues Anzeigemaß, '') oder
    (None, Grund); das Modellmaß wird nur gelöscht, wenn das neue denselben Wert misst und das Löschen wirkt. Jedes
    Löschen wird nach Wirkung geprüft; ein stehengebliebenes Maß steht im Grund."""
    if _ruf(dd, "Type2") in RUND:
        return _ersetze_rund(drw, mu, view, dd, kanten)
    b = hilfslinien(dd)
    if b is None:
        return None, "kein lineares Maß mit zwei Hilfslinien"
    richtung, linien, punkte = b
    kanten = sichtbare_kanten(mu, view) if kanten is None else kanten
    gewaehlt = [kante_am_punkt(p, richtung, kanten, h) for p, h in zip(punkte, linien)]
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
    kreise = [k for k in kanten if k.kreis and k.radius_mm is not None and abs(k.radius_mm - r_soll) < WERT_TOL_MM
              and any(math.dist(p, k.kreis[0]) < PUNKT_TOL_MM or abs(math.dist(p, k.kreis[0]) - k.kreis[1]) < 0.3
                      for p in punkte)]
    if not kreise:
        return None, f"keine Kreiskante mit Radius {round(r_soll, 3)} am Maß"
    x, y, _ = (list(_ruf(_ruf(dd, "GetAnnotation"), "GetPosition")) + [0.0])[:3]
    drw.ClearSelection2(True)
    if not view.SelectEntity(kreise[0].obj, False):
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


def _strecke_quer(a, b, c, d) -> bool:
    """Schneiden sich die Strecken a–b und c–d (echt, nicht nur in einem gemeinsamen Endpunkt)?"""
    def seite(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    d1, d2, d3, d4 = seite(c, d, a), seite(c, d, b), seite(a, b, c), seite(a, b, d)
    return d1 * d2 < -1e-9 and d3 * d4 < -1e-9


def _auf_strecke(p, s, tol: float = 0.1) -> bool:
    return _abstand_strecke(p, s[0], s[1]) <= tol


@dataclass
class Anmerkung:
    """Gesetzte Anmerkung mit Hinweislinie an `anker` (Blatt-mm, zurückgelesen). Verhält sich in der
    Lesbarkeitsschleife wie ein Hinweis (`zeichnen._Hinweis`): `zeilen`, `lage` (Mitte des Rechtecks), `rechteck()`,
    `verwerfen()`; Größe und Versatz (Mitte − `IAnnotation.GetPosition`) sind je Art live gemessen, `vermessen` bleibt
    wahr. `kante`: die gewählte gerade Kante (Bezug: Lagen quer zu ihr; vom Abstand zu Kanten ausgenommen).
    `einhaengen`: (Kreiskante, Punkt) → (Annotation, Ansatz) oder None – Bohrung: an eine andere Instanz hängen;
    `kreise`: die Kreiskanten aller Instanzen."""
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
    kreise: list = field(default_factory=list)
    einhaengen: object = None
    fixiert: tuple | None = None              # Lage der besten Runde (zeichnen._lesbar_anlegen stellt sie wieder her)

    def rechteck(self, lage: tuple | None = None) -> tuple | None:
        lage = self.lage if lage is None else lage
        if lage is None:
            return None
        (x, y), (b, h) = lage, self.groesse
        return (x - b / 2, y - h / 2, x + b / 2, y + h / 2)

    def stand(self) -> tuple | None:
        """Gewählte Lage dieser Runde (`zeichnen._lesbar_anlegen` stellt die beste Runde über `fixiert` wieder her)."""
        return self.soll

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
        """Wo die Hinweislinie die Kante trifft: Bezug senkrecht unter dem Kasten, sonst der Anker."""
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
        gerückter Bezugskasten nie als verworfen erkannt); False, wenn keine Lage mehr übrig ist."""
        lage = self.soll if self.soll is not None else self.lage
        if lage is not None and lage not in self.verworfen:
            self.verworfen.append(lage)
        return len(self.verworfen) < len(self._roh())

    def _roh(self, anker: tuple | None = None) -> list[tuple[float, float]]:
        """Lagen (Mitte des Rechtecks) in fester Rangfolge. Bezug: Kasten quer zur Kante nach außen, entlang der Kante
        verteilt; sonst in acht Richtungen um den Anker (diagonal zuerst) im Abstand `ANM_ABSTAENDE_MM`, das Rechteck
        auf der vom Anker abgewandten Seite (Review Task 5: die 16 Lagen der Bohrungsangaben reichten nicht)."""
        if self.art != "bezug" or self.kante is None:
            ax, ay = self.anker if anker is None else anker
            b, h = self.groesse
            aus = []
            for d in ANM_ABSTAENDE_MM:
                for w in ANM_RICHTUNGEN_GRAD:
                    c, s = math.cos(math.radians(w)), math.sin(math.radians(w))
                    ex, ey = ax + d * c, ay + d * s
                    aus.append((round(ex + (b / 2 if c > 0.1 else -b / 2 if c < -0.1 else 0.0), 3),
                                round(ey + (h / 2 if s > 0.9 else -h / 2 if s < -0.9 else 0.0), 3)))
            return aus
        a, e = self.kante
        n = self._normale()
        aus = []
        for abstand in BEZUG_ABSTAENDE_MM:
            for t in BEZUG_TEILUNG:
                p = (a[0] + (e[0] - a[0]) * t + n[0] * abstand, a[1] + (e[1] - a[1]) * t + n[1] * abstand)
                aus.append((round(p[0] + n[0] * self.groesse[1] / 2, 3), round(p[1] + n[1] * self.groesse[1] / 2, 3)))
        return aus

    def bewerten(self, lage, hindernisse=(), texte=(), kanten=(), masslinien=(), ansaetze=()) -> int:
        """Zahl der Verstöße einer Lage (0 = frei; Review Task 5, C2):
        - das Rechteck kreuzt eine Strecke aus `hindernisse`,
        - Rechteck samt `ABSTAND_KANTE_MM` kreuzt eine sichtbare Kante (`kanten`) außer der eigenen,
        - die Hinweislinie quert ein Textrechteck (`texte`: Hinweise, gelegte Anmerkungen) oder eine Maß- bzw.
          Hilfslinie (`masslinien`),
        - ihr Fußpunkt liegt näher als `ANSATZ_ABSTAND_MM` an einem anderen Ansatz (`ansaetze`)."""
        r = self.rechteck(lage)
        g = ABSTAND_KANTE_MM
        weit = (r[0] - g, r[1] - g, r[2] + g, r[3] + g)
        linie = self.hinweislinie(lage)
        eigen = self.kante
        zahl = sum(1 for a, b in hindernisse if _schneidet(a, b, r))
        zahl += sum(1 for a, b in kanten if _schneidet(a, b, weit)
                    and not (eigen and _auf_strecke(a, eigen) and _auf_strecke(b, eigen)))
        zahl += sum(1 for t in texte if _schneidet(linie[0], linie[1], t))
        zahl += sum(1 for a, b in masslinien if _strecke_quer(linie[0], linie[1], a, b))
        fuss = self.fusspunkt(lage)
        zahl += sum(1 for p in ansaetze if math.dist(p, fuss) < ANSATZ_ABSTAND_MM)
        return zahl

    def kandidaten(self, hindernisse: list[tuple] = (), texte: list[tuple] = (), kanten: list[tuple] = (),
                   masslinien: list[tuple] = (), ansaetze: list = ()) -> list[tuple[float, float]]:
        """Lagen, beste zuerst: wenigste Verstöße (`bewerten`), dann außerhalb des Körpers, dann Rang."""
        bewertet = []
        for i, lage in enumerate(self._roh()):
            r = self.rechteck(lage)
            im_koerper = r[0] < self.umriss[2] and self.umriss[0] < r[2] and r[1] < self.umriss[3] and self.umriss[1] < r[3]
            bewertet.append((self.bewerten(lage, hindernisse, texte, kanten, masslinien, ansaetze), im_koerper, i, lage))
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
    xs = [p[0] for k in kanten for p in (k.a, k.e)]
    ys = [p[1] for k in kanten for p in (k.a, k.e)]
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


def ansatzpunkt(k: Kante, kanten: list[Kante], belegt: list, umriss: tuple | None = None) -> tuple[float, float]:
    """Punkt auf der Kante, an dem die Hinweislinie ansetzt (Review Task 5, C2: ohne Pickpunkt endeten die Linien an
    Kantenenden, zwei teilten sich einen Ecke): auf einer Geraden bei 50/35/65/20/80 % ihrer Länge, auf einem Kreis
    unter 45°/135°/315°/225° (vom Körper weg zuerst); mindestens `ANSATZ_ABSTAND_MM` von schon belegten Ansätzen und
    0,5 mm von anderen Kanten, damit die Wahl am Punkt eindeutig ist."""
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
            if o is k or o.punkt:
                continue
            d = abs(math.dist(p, o.kreis[0]) - o.kreis[1]) if o.kreis else _abstand_strecke(p, o.a, o.e)
            if d < 0.5 and not (not o.kreis and not k.kreis and _auf_strecke(o.a, (k.a, k.e), 0.05)
                                and _auf_strecke(o.e, (k.a, k.e), 0.05)):
                return False
        return True

    return next((p for p in punkte if frei(p)), punkte[0])


def _waehle_am_punkt(drw, view, k: Kante, punkt: tuple[float, float]) -> bool:
    """Kante am Punkt wählen (`SelectByID2("", "EDGE", x, y, …)`, wie Stufe 3 `_kreis_am_punkt`; Spike h: die
    Hinweislinie setzt dann dort an). Wahr, wenn eine Kante gewählt ist; sonst `IView.SelectEntity` (ohne Punkt)."""
    drw.ClearSelection2(True)
    drw.ActivateView(_ruf(view, "GetName2"))
    if _ruf(drw, "Extension").SelectByID2("", "EDGE", punkt[0] / 1000, punkt[1] / 1000, 0, False, 0,
                                         callout_leer(), 0):
        sm = _ruf(drw, "SelectionManager")
        if any(sm.GetSelectedObjectType3(i, -1) == KANTE for i in range(1, sm.GetSelectedObjectCount2(-1) + 1)):
            return True
    drw.ClearSelection2(True)
    return bool(view.SelectEntity(k.obj, False))


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


def _einfuegen_mit(drw, view, kanten: list[Kante], belegt: list, umriss: tuple, einfuegen):
    """Fabrik: Kreis- oder Geradenkante am Ansatzpunkt wählen, mit `einfuegen()` einsetzen, Ansatz zurücklesen.
    Liefert (Annotation, Ansatz) oder None."""
    def am(k: Kante):
        p = ansatzpunkt(k, kanten, belegt, umriss)
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
        am = _einfuegen_mit(drw, views[rolle], kanten, belegt, umriss, einfuegen)
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
            ist_bohrung = typen.get(m.merkmal) in ("bohrung", "normbohrung")
            anmerkungen.append(Anmerkung(
                "rauheit", m.merkmal, (m.text,), gesetzt[0], rolle, gesetzt[1], umriss, (breite, GROESSE_RAUHEIT[1]),
                (breite / 2 + VERSATZ_RAUHEIT[0], VERSATZ_RAUHEIT[1]), kante=None if k.kreis else (k.a, k.e),
                kreise=bohrungskreise(kanten, namen) if ist_bohrung else [], einhaengen=am if ist_bohrung else None))
    return meldungen


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
        am = _einfuegen_mit(drw, views[rolle], kanten, belegt, umriss, einfuegen)
        gesetzt = am(k)
        if gesetzt is None:
            meldungen.append(f"FORM_LAGE_NICHT_GESETZT: {etikett} – Kante in {rolle} nicht auswählbar oder "
                             "InsertGtol abgelehnt")
            continue
        if not zustand.get("beschriftet"):
            meldungen.append(f"FORM_LAGE_NICHT_GESETZT: {etikett} – Rahmen nicht beschriftet")
        if n > 1 and not zustand.get("oben"):
            meldungen.append(f"FORM_LAGE_NUR_EINE_INSTANZ: {etikett} – „{n} ×“ über dem Rahmen nicht gesetzt")
        if anmerkungen is not None:
            breite = RAHMEN_ZELLE_MM * (1 + len(fl.bezug)) + ZEICHEN_MM * len(fl.wert) + 2
            hoehe = RAHMEN_HOEHE_MM + (RAHMEN_TEXT_OBEN_MM if n > 1 else 0.0)
            ist_bohrung = typen.get(m.merkmal) in ("bohrung", "normbohrung")
            anmerkungen.append(Anmerkung(
                "form_lage", m.merkmal, (" ".join((fl.wert,) + tuple(fl.bezug)),) + ((f"{n} ×",) if n > 1 else ()),
                gesetzt[0], rolle, gesetzt[1],
                umriss, (breite, hoehe), (breite / 2, hoehe / 2 - RAHMEN_HOEHE_MM),
                kante=None if k.kreis else (k.a, k.e),
                kreise=bohrungskreise(kanten, namen) if ist_bohrung else [], einhaengen=am if ist_bohrung else None))
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
        gesetzt = _einfuegen_mit(drw, views[rolle], kanten, belegt, umriss, einfuegen)(k)
        if gesetzt is None:
            meldungen.append(f"BEZUG_NICHT_GESETZT: {m.text} – Kante in {rolle} nicht auswählbar oder InsertDatumTag2 "
                             "abgelehnt")
            continue
        if not zustand.get("label"):
            meldungen.append(f"BEZUG_NICHT_GESETZT: {m.text} – Buchstabe nicht gesetzt")
        if anmerkungen is not None:
            anmerkungen.append(Anmerkung("bezug", m.merkmal, (m.text,), gesetzt[0], rolle, gesetzt[1], umriss,
                                         GROESSE_BEZUG, (0.0, 0.0), kante=(k.a, k.e)))
    return meldungen


def _loesche_anmerkung(drw, ann) -> bool:
    drw.ClearSelection2(True)
    ok = ann.Select2(False, 0) and _ruf(drw, "Extension").DeleteSelection2(0)
    drw.ClearSelection2(True)
    return bool(ok)


def instanzen_umhaengen(drw, anmerkungen: list[Anmerkung], hinweise: list, meldungen: list | None = None,
                        hindernisse: list[tuple] = (), kanten: list[tuple] = (), masslinien: list[tuple] = ()) -> None:
    """Rauheit/Rahmen an einer Bohrung erst nach der Lage der Bohrungsangabe an eine Instanz hängen (Review Task 5, I1):
    je Bohrung die beste erreichbare Lage bewerten (`Anmerkung.bewerten`, Text- und Hinweislinien der Angaben als
    Hindernis, die Bohrung der Angabe zählt einen Verstoß mehr); ist das eine andere Bohrung, wird die Anmerkung dort neu
    eingefügt und die alte gelöscht."""
    texte = [h.rechteck() for h in hinweise if h.rechteck()]
    for a in anmerkungen:
        if not a.kreise or a.einhaengen is None or a.fixiert is not None:
            continue
        besetzt = [h.kreis[0] for h in hinweise if h.merkmal == a.merkmal]

        def guete(k, a=a, besetzt=besetzt):
            m, r = k.kreis
            beste = min(a.bewerten(lage, hindernisse, texte, kanten, masslinien) for lage in a._roh(m))
            return beste + (1 if any(math.dist(m, p) < PUNKT_TOL_MM for p in besetzt) else 0)

        heute = min(a.kreise, key=lambda k: abs(math.dist(a.anker, k.kreis[0]) - k.kreis[1]))
        ziel = min(a.kreise, key=lambda k: (guete(k), k is not heute))
        if ziel is heute:
            continue
        neu = a.einhaengen(ziel)
        if neu is None:
            if meldungen is not None and f"ANMERKUNG_NICHT_UMGEHAENGT: {a.merkmal} {a.zeilen[0]}" not in meldungen:
                meldungen.append(f"ANMERKUNG_NICHT_UMGEHAENGT: {a.merkmal} {a.zeilen[0]}")
            continue
        if not _loesche_anmerkung(drw, a.ann) and meldungen is not None:
            meldungen.append(f"ANMERKUNG_DOPPELT: {a.merkmal} {a.zeilen[0]} – alte nicht gelöscht")
        a.ann, a.anker = neu
        a.verworfen.clear()


def anmerkungen_legen(anmerkungen: list[Anmerkung], hindernisse: list[tuple], texte: list[tuple] | None = None,
                      kanten: list[tuple] = (), masslinien: list[tuple] = ()) -> list[tuple]:
    """Lage jeder Anmerkung: die beste nicht verworfene ihrer `kandidaten` (Verstöße nach `Anmerkung.bewerten` gegen
    `hindernisse`, die schon gelegten, `texte`, `kanten`, `masslinien` und die Ansätze der anderen); eine fixierte
    Lage (beste Runde) gilt unverändert. `SetPosition2` mit Bezugspunkt = Mitte − Versatz; danach die wirkliche Lage
    zurücklesen (ein Bezugskasten rückt auf die Senkrechte zur Kante). Liefert Rechtecke und Hinweislinien als
    Strecken."""
    gelegt: list[tuple] = []
    rechtecke = list(texte or [])
    for a in anmerkungen:
        ansaetze = [b.fusspunkt() if b.lage else b.anker for b in anmerkungen if b is not a]
        if a.fixiert is not None:
            lage = a.fixiert
        else:
            kandidaten = a.kandidaten(hindernisse + gelegt, rechtecke, kanten, masslinien, ansaetze)
            frei = [lage for lage in kandidaten if not any(math.dist(lage, w) <= 0.5 for w in a.verworfen)]
            lage = frei[0] if frei else kandidaten[0]
        a.soll = lage
        versatz = a.versatz_bei(lage)
        a.ann.SetPosition2((lage[0] - versatz[0]) / 1000, (lage[1] - versatz[1]) / 1000, 0)
        ist = [c * 1000 for c in list(_ruf(a.ann, "GetPosition"))[:2]]
        a.lage = (round(ist[0] + versatz[0], 3), round(ist[1] + versatz[1], 3))
        r = a.rechteck()
        rechtecke.append(r)
        ecken = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
        gelegt += list(zip(ecken, ecken[1:] + ecken[:1])) + [a.hinweislinie()]
    return gelegt


# --- Sammelangaben ----------------------------------------------------------------------------------------------------


def umbrechen(zeilen: list[str], zeichen: int = SAMMEL_ZEICHEN) -> list[str]:
    """Zeilen, die breiter als das Band wären, nach „, “ bzw. am letzten Leerzeichen umbrechen (Härteangabe der
    Buchse: 77 Zeichen ≈ 182 mm gegen 180 mm Schriftfeldbreite). Zusammengefügt mit Leerzeichen ergibt sich die
    Zeile wieder (Prüfung Z1.4 vergleicht whitespace-normalisiert)."""
    aus = []
    for z in zeilen:
        while len(z) > zeichen:
            schnitt = z.rfind(", ", 0, zeichen)
            if schnitt > 0:
                aus.append(z[:schnitt + 1])
                z = z[schnitt + 2:]
                continue
            schnitt = z.rfind(" ", 0, zeichen)
            if schnitt <= 0:
                break
            aus.append(z[:schnitt])
            z = z[schnitt + 1:]
        aus.append(z)
    return aus



def sammel_aufteilung(zeilen: list[str]) -> tuple[list[str], int]:
    """Zeilen des Sammelhinweises (umgebrochen auf die Bandbreite) und die Zeile, in der rechts die allgemeine Rauheit
    steht (eigener Hinweis `SAMMEL_RAUHEIT_ZEILE`, Vorschlag Task 5): die erste Zeile, neben die sie passt; passt sie
    nirgends, eine Zeile mehr (Index = Zeilenzahl). Live 27.11.: eine eigene Zeile hob das Band der Spannplatte um
    5 mm, die Ansichten passten nicht mehr auf A3 1:2 (A4 1:5)."""
    umbrochen = umbrechen(zeilen)
    frei = SAMMEL_ZEICHEN - len(SAMMEL_RAUHEIT_ZEILE) - SAMMEL_SPALT_ZEICHEN
    return umbrochen, next((i for i, z in enumerate(umbrochen) if len(z) <= frei), len(umbrochen))


def sammel_zeilenzahl(zeilen: list[str]) -> int:
    """Zeilen, die das Band über dem Schriftfeld braucht (Höhe = Zahl × `SAMMEL_ZEILE_MM`)."""
    umbrochen, zeile = sammel_aufteilung(zeilen)
    return max(len(umbrochen), zeile + 1)


def sammelband(format_: str, hoehe_mm: float) -> tuple[float, float, float, float]:
    """Reserviertes Band über dem Schriftfeld (Blatt-mm), so breit wie das Schriftfeld, rechtsbündig."""
    x0, y0, x1, _ = zeichenfeld(format_)
    sb, sh = SCHRIFTFELD_MM
    return (x1 - sb, y0 + sh, x1, y0 + sh + hoehe_mm)


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


def sammelangaben_setzen(drw, zeilen: list[str], format_: str, hoehe_mm: float) -> list[str]:
    """Sammelhinweis ohne Hinweislinie, linke obere Ecke an der Oberkante des Bands, und rechts daneben die allgemeine
    Rauheit (`sammel_aufteilung`). Lage über `SetPosition2` (`InsertNote` ohne Auswahl legt den Hinweis sonst unter
    das Blatt, Spike a). Liefert Meldungen `SAMMELANGABEN_NICHT_GESETZT`."""
    umbrochen, zeile = sammel_aufteilung(zeilen)
    x0, _, x1, y1 = sammelband(format_, hoehe_mm)
    meldungen = []
    if umbrochen and _notiz_an(drw, "\n".join(umbrochen), x0 + 1.0, y1) is None:
        meldungen.append("SAMMELANGABEN_NICHT_GESETZT: InsertNote abgelehnt")
    rechts = x1 - 3.0 - len(SAMMEL_RAUHEIT_ZEILE) * SAMMEL_RAUHEIT_ZEICHEN_MM
    if _notiz_an(drw, SAMMEL_RAUHEIT_ZEILE, rechts, y1 - zeile * SAMMEL_ZEILENABSTAND_MM) is None:
        meldungen.append(f"SAMMELANGABEN_NICHT_GESETZT: {SAMMEL_RAUHEIT_ZEILE} – InsertNote abgelehnt")
    drw.ClearSelection2(True)
    return meldungen


def sammel_pruefen(pdf_texte: list[tuple[str, tuple]], zeilen: list[str], band: tuple) -> list[str]:
    """Stehen alle Zeilen der Sammelangaben (`sammel_aufteilung` samt allgemeiner Rauheit) im PDF und innerhalb des
    Bands? (`pruefe_pdf` übergeht Texte am Schriftfeld; ein Überlauf fiele sonst nicht auf.)"""
    meldungen = []
    for z in sammel_aufteilung(zeilen)[0] + [SAMMEL_RAUHEIT_ZEILE]:
        treffer = [r for t, r in pdf_texte if t == z.strip()]
        if not treffer:
            meldungen.append(f"SAMMELANGABE_FEHLT: „{z}“ nicht im PDF")
            continue
        r = min(treffer, key=lambda r: math.dist((r[0], r[1]), (band[0], band[3])))
        if r[0] < band[0] - 0.5 or r[1] < band[1] - 0.5 or r[2] > band[2] + 0.5 or r[3] > band[3] + 0.5:
            meldungen.append(f"SAMMELANGABE_UEBERLAUF: „{z}“ bei ({r[0]:.0f}, {r[1]:.0f})–({r[2]:.0f}, {r[3]:.0f}) mm "
                             f"außerhalb des Bands ({band[0]:.0f}, {band[1]:.0f})–({band[2]:.0f}, {band[3]:.0f})")
    return meldungen
