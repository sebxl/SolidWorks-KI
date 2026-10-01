"""S10 Frage 5: runde Konturen in Skizzen – CreateFillet, CreateSketchSlot, CreateArc – jeweils voll bestimmt.

Skizzen mit dem Skizzierer des Compilers (Lagemaße zum Ursprung, AddToDB, Toggle 10 aus) auf einer Standardebene,
danach Extrusion blind 10 und Volumenabgleich mit der analytischen Fläche. Je Fall: Rückgaben, Segmente/Punkte,
Maße (Name, Wert, maßgebend/referenzierend), Bestimmtheit vor dem Schließen, Volumen ist/soll.
a) Rechteck 60 × 40 mit Eckradius 5: CreateFillet(0,005, swConstrainedCornerKeepGeometry = 1) nach Auswahl der beiden
   Linien einer Ecke („linien“) bzw. des Eckpunkts („punkt“). CreateFillet legt selbst ein maßgebendes Radiusmaß an;
   es wird über den Vergleich der Maßliste vor/nach dem Aufruf gefunden und per Gleichung an den Parameter R gebunden
   (R → 4, neu aufbauen, Volumen). Fall „eigenes_mass“ zeigt, was ein zusätzliches AddDimension2 bewirkt.
b) L-Polygon mit konkaver Ecke (Radien RK = 3, konkav RI = 5), Radiusmaße wie a) per Gleichung gebunden.
c) Langloch Mitte (10, 5), Länge 30, Breite 8: CreateSketchSlot Typ 1 (Mittelpunkt) und Typ 0 (Linie), Länge
   Mitte–Mitte, ohne Auto-Maße; Breite = Abstand der geraden Seiten, Länge = Mittellinie, Richtung = Beziehung (0°, 90°)
   bzw. Winkelmaß zu einer u-parallelen Hilfslinie (30°), Lage der Mitte; Breite/Länge per Gleichung an B und L
   gebunden (L → 40, B → 6, neu aufbauen, Volumen).
d) Kontur 80 × 20 mit zwei Halbkreisen (R 10) aus CreateLine/CreateArc auf oben, vorne, rechts: Richtung +1/−1 je
   nach Drehsinn der (u, v)-Abbildung, gemeinsame Endpunkte (Punktzahl vor/nach sgMERGEPOINTS), Bögen: Mittelpunkt
   voll, Endpunkt nur in der Koordinate mit kleinerem Abstand zum Mittelpunkt bemaßt.

Aufruf: python -m spikes.s10_f5_skizzen [Fallpräfix …] (ohne Argument alle Fälle; mit Argument nur passende, die JSON
heißt dann …_teil.json). Jeder Fall legt höchstens zwei Teile an (ein Neuversuch bei „Ausnahmefehler des Servers“,
mit Aufrufkette im Ergebnis – kein Überspielen).
"""

import math
import sys
import traceback

import pythoncom

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import start, teil, volumen_mm3
from spikes.s10_gemeinsam import kontext
from swki.compiler import sw
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.skizze import Skizzierer, _Mass, ebene_aufloesen
from swki.verbindung import mm

SW_ECKE_BEHALTEN = 1  # swConstrainedCornerAction_e.swConstrainedCornerKeepGeometry
SW_NUT = {"mittelpunkt": 1, "linie": 0}  # swSketchSlotCreationType_e (center_line, line)
SW_NUT_MITTE_MITTE = 0  # swSketchSlotLengthType_e.swSketchSlotLengthType_CenterCenter
SW_LINIE, SW_BOGEN = 0, 1  # swSketchSegments_e
HR_SERVERFEHLER = -2147417851  # RPC_E_SERVERFAULT „Ausnahmefehler des Servers“
L_FORM = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (20.0, 20.0), (20.0, 40.0), (0.0, 40.0)]
L_RADIEN = [3.0, 3.0, 3.0, 5.0, 3.0, 3.0]
SKIZZE = "s_skizze"


def _p(p) -> list:
    return [round(p.X * 1000, 4), round(p.Y * 1000, 4)]


def _segmente(skizze, ab: int = 0) -> list[dict]:
    out = []
    for s in list(skizze.GetSketchSegments or ())[ab:]:
        e = {"typ": s.GetType, "konstruktion": bool(s.ConstructionGeometry)}
        if e["typ"] == SW_LINIE:
            e |= {"start": _p(s.GetStartPoint2), "ende": _p(s.GetEndPoint2)}
        elif e["typ"] == SW_BOGEN:
            e |= {"mitte": _p(s.GetCenterPoint2), "radius": round(s.GetRadius * 1000, 4)}
        out.append(e)
    return out


def _masse(skizze_feature) -> list[dict]:
    out, dd = [], skizze_feature.GetFirstDisplayDimension
    while dd is not None:
        dim = dd.GetDimension2(0)
        # DrivenState: 2 = maßgebend (swDimensionDriving), 1 = referenzierend (swDimensionDriven)
        out.append({"name": dim.Name, "wert": round(dim.SystemValue, 9), "getrieben": dim.DrivenState})
        dd = skizze_feature.GetNextDisplayDimension(dd)
    return out


def _relationen(skizze) -> list:
    """Diagnose: Beziehungen der Skizze als (swConstraintType_e, Anzahl Entitäten)."""
    try:
        return [(r.GetRelationType, r.GetEntitiesCount) for r in skizze.RelationManager.GetRelations(0) or ()]
    except Exception as e:
        return f"FEHLER {e!r}"


def gleichsinnig(sk) -> bool:
    """Erhält die Abbildung (u, v) → Skizze den Drehsinn? (Determinante > 0)"""
    x0, y0 = sk.zu_skizze(0, 0)
    xu, yu = sk.zu_skizze(1, 0)
    xv, yv = sk.zu_skizze(0, 1)
    return (xu - x0) * (yv - y0) - (xv - x0) * (yu - y0) > 0


def verschmelzen(sk, x: float, y: float, art: str = "sgMERGEPOINTS") -> int:
    """Mehrere Skizzenpunkte an (x, y) mit art (sgMERGEPOINTS oder sgCOINCIDENT) zu einem machen; Rückgabe: Anzahl vorher."""
    gleich = [p for p in sk.skizze.GetSketchPoints2 or () if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8]
    for p in gleich[1:]:
        sw.auswahl_leeren(sk.model)
        sw.waehle(sk.model, gleich[0], 0)
        sw.waehle(sk.model, p, 0, anhaengen=True)
        sk.model.SketchAddConstraints(art)
    sw.auswahl_leeren(sk.model)
    return len(gleich)


def lage_nur(sk, uv, text_uv, nur: int) -> None:
    """Wie Skizzierer.lage, aber nur die u- (0) oder v-Lage (1) – Task 6 übernimmt das als lage(..., nur=…)."""
    x, y = sk.zu_skizze(*uv)
    punkt = sk._punkt(x, y)
    for wert, (index, _), waagrecht in ((x, sk.x_von, True), (y, sk.y_von, False)):
        if index != nur:
            continue
        sw.auswahl_leeren(sk.model)
        sw.waehle(sk.model, punkt, 0)
        sw.waehle(sk.model, sk.ursprung, 0, anhaengen=True)
        if abs(wert) < 1e-9:
            sk.model.SketchAddConstraints("sgVERTICALPOINTS2D" if waagrecht else "sgHORIZONTALPOINTS2D")
            continue
        t = sk._text(*text_uv)
        sk._merke(sk.model.AddHorizontalDimension2(*t) if waagrecht else sk.model.AddVerticalDimension2(*t), uv[index])
    sw.auswahl_leeren(sk.model)


def _linien_an(linien, x: float, y: float) -> list:
    return [s for s in linien for p in (s.GetStartPoint2, s.GetEndPoint2)
            if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8]


def _massnamen(sk) -> list[str]:
    """Namen der Maße der (noch offenen) Skizze über das letzte Feature des Baums."""
    return [m["name"] for m in _masse(sw.letztes_feature(sk.model))]


def verrunden(sk, linien, ecken_uv, radius_mm: float, art: str, roh=None, eigenes_mass: bool = False) -> list[dict]:
    """Ecken verrunden. Das von CreateFillet angelegte Radiusmaß wird per Maßlistenvergleich gefunden und als Maß der
    Skizze vorgemerkt (roh = Zahl oder "=Parameter"); eigenes_mass: zusätzlich AddDimension2 auf den Bogen (Gegenprobe)."""
    schritte = []
    for u, v in ecken_uv:
        x, y = sk.zu_skizze(u, v)
        sw.auswahl_leeren(sk.model)
        if art == "linien":
            for i, s in enumerate(_linien_an(linien, x, y)):
                sw.waehle(sk.model, s, 0, anhaengen=i > 0)
        else:
            sw.waehle(sk.model, sk._punkt(x, y), 0)
        vorher = _massnamen(sk)
        bogen = sk.sm.CreateFillet(mm(radius_mm), SW_ECKE_BEHALTEN)
        sw.auswahl_leeren(sk.model)
        neu = [n for n in _massnamen(sk) if n not in vorher]
        eintrag = {"ecke": [u, v], "bogen": bogen is not None, "status_nach_fillet": sk.skizze.GetConstrainedStatus,
                   "masse_von_createfillet": neu}
        if len(neu) == 1:
            sk.masse.append(_Mass(neu[0], radius_mm if roh is None else roh))
        if bogen is not None and eigenes_mass:
            sk.groesse(bogen, (u + 8, v + 8), radius_mm)
            eintrag |= {"eigenes_mass": sk.masse[-1].name, "status_nach_eigenem_mass": sk.skizze.GetConstrainedStatus}
            sk.masse.pop()  # referenzierend, nicht binden
        schritte.append(eintrag)
    return schritte


def richtung_zu_u(sk, linie, mitte_uv, winkel: float, art: str = "sgMERGEPOINTS") -> str:
    u_ist_x = sk.x_von[0] == 0
    w = winkel % 180
    sw.auswahl_leeren(sk.model)
    if w in (0, 90):
        sw.waehle(sk.model, linie, 0)
        sk.model.SketchAddConstraints("sgHORIZONTAL2D" if (w == 0) == u_ist_x else "sgVERTICAL2D")
        sw.auswahl_leeren(sk.model)
        return "beziehung"
    mu, mv = mitte_uv
    xa, ya = sk.zu_skizze(mu, mv)
    xb, yb = sk.zu_skizze(mu + 16, mv)
    hilfe = sk.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0)
    punkte_vorher = len(sk.skizze.GetSketchPoints2 or ())
    gleiche = verschmelzen(sk, xa, ya, art)
    sk.protokoll |= {"hilfslinie_punkte_vor_nach": [punkte_vorher, len(sk.skizze.GetSketchPoints2 or ())],
                     "hilfslinie_gleiche_punkte": gleiche, "hilfslinie_verschmelzen_mit": art}
    sw.waehle(sk.model, hilfe, 0)
    sk.model.SketchAddConstraints("sgHORIZONTAL2D" if u_ist_x else "sgVERTICAL2D")
    sw.auswahl_leeren(sk.model)
    sk.groesse(hilfe, (mu + 8, mv - 8), 16)
    sw.waehle(sk.model, linie, 0)
    sw.waehle(sk.model, hilfe, 0, anhaengen=True)
    halb = math.radians(w) / 2
    sk._merke(sk.model.AddDimension2(*sk._text(mu + 24 * math.cos(halb), mv + 24 * math.sin(halb))), w)
    sw.auswahl_leeren(sk.model)
    return "winkelmass"


def rechteck(art: str, roh=None, eigenes_mass: bool = False):
    def zeichnen(sk, ctx) -> list:
        sk.element({"rechteck": {"mitte": [0, 0], "breite": 60, "hoehe": 40}})
        linien = list(sk.skizze.GetSketchSegments or ())
        return verrunden(sk, linien, [(-30, -20), (30, -20), (30, 20), (-30, 20)], 5.0, art, roh, eigenes_mass)
    return zeichnen


def polygon(parametrisch: bool):
    def zeichnen(sk, ctx) -> list:
        sk.element({"polygon": {"punkte": [list(p) for p in L_FORM]}})
        linien = list(sk.skizze.GetSketchSegments or ())
        roh = {3.0: "=RK" if parametrisch else None, 5.0: "=RI" if parametrisch else None}
        return [s for ecke, r in zip(L_FORM, L_RADIEN) for s in verrunden(sk, linien, [ecke], r, "linien", roh[r])]
    return zeichnen


def langloch(typ: str, winkel: float, parametrisch: bool = False, art: str = "sgMERGEPOINTS"):
    def zeichnen(sk, ctx) -> dict:
        mu, mv, laenge, breite = 10.0, 5.0, 30.0, 8.0
        laenge_roh, breite_roh = ("=L", "=B") if parametrisch else (laenge, breite)
        w = math.radians(winkel)
        ende = (mu + laenge / 2 * math.cos(w), mv + laenge / 2 * math.sin(w))
        anfang = (mu, mv) if typ == "mittelpunkt" else (mu - laenge / 2 * math.cos(w), mv - laenge / 2 * math.sin(w))
        (x1, y1), (x2, y2) = sk.zu_skizze(*anfang), sk.zu_skizze(*ende)
        vorher = len(sk.skizze.GetSketchSegments or ())
        d: dict = {"status_verlauf": []}
        sk.protokoll = d

        def status(name: str) -> None:
            d["status_verlauf"].append([name, sk.skizze.GetConstrainedStatus])

        nut = sk.sm.CreateSketchSlot(SW_NUT[typ], SW_NUT_MITTE_MITTE, mm(breite), x1, y1, 0.0, x2, y2, 0.0,
                                     0.0, 0.0, 0.0, 1, False)
        d["nut"] = nut is not None
        if nut is None:
            return d
        status("nach_slot")
        d["relationen_nach_slot"] = _relationen(sk.skizze)
        d["punkte_nach_slot"] = [_p(p) for p in sk.skizze.GetSketchPoints2 or ()]
        neu = list(sk.skizze.GetSketchSegments or ())[vorher:]
        d["neue_segmente"] = _segmente(sk.skizze, vorher)
        d["mittelpunkt"] = _p(nut.GetCenterPointHandle)
        d["laenge_breite_mm"] = [round(nut.Length * 1000, 4), round(nut.Width * 1000, 4)]
        seiten = [x for x in neu if x.GetType == SW_LINIE and not x.ConstructionGeometry]
        achsen = [x for x in neu if x.GetType == SW_LINIE and x.ConstructionGeometry]
        d["seiten_achsen"] = [len(seiten), len(achsen)]
        if len(seiten) != 2 or not achsen:
            return d
        sw.auswahl_leeren(sk.model)
        sw.waehle(sk.model, seiten[0], 0)
        sw.waehle(sk.model, seiten[1], 0, anhaengen=True)
        sk._merke(sk.model.AddDimension2(*sk._text(mu, mv + 12)), breite_roh)
        sw.auswahl_leeren(sk.model)
        status("nach_breite")
        sk.groesse(achsen[0], (mu, mv - 12), laenge_roh)
        status("nach_laenge")
        d["richtung"] = richtung_zu_u(sk, achsen[0], (mu, mv), winkel, art)
        status("nach_richtung")
        sk.lage([mu, mv], (mu - 25, mv - 8))
        status("nach_lage")
        d["masse_merk"] = [m.name for m in sk.masse]
        return d
    return zeichnen


def kontur(sk, ctx) -> dict:
    ecken = [(-40.0, 25.0), (40.0, 25.0), (40.0, 45.0), (-40.0, 45.0)]
    segmente = [("linie", None), ("bogen", (40.0, 35.0)), ("linie", None), ("bogen", (-40.0, 35.0))]
    d: dict = {"gleichsinnig": gleichsinnig(sk), "erzeugt": []}
    sk.protokoll = d
    richtung = 1 if d["gleichsinnig"] else -1
    for i, (art, mitte) in enumerate(segmente):
        (xa, ya), (xb, yb) = sk.zu_skizze(*ecken[i]), sk.zu_skizze(*ecken[(i + 1) % 4])
        if art == "linie":
            seg = sk.sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)
        else:
            xm, ym = sk.zu_skizze(*mitte)
            seg = sk.sm.CreateArc(xm, ym, 0.0, xa, ya, 0.0, xb, yb, 0.0, richtung)
        d["erzeugt"].append(seg is not None)
    d["punkte_vor_verschmelzen"] = len(sk.skizze.GetSketchPoints2 or ())
    d["verschmolzen"] = [verschmelzen(sk, *sk.zu_skizze(*e)) for e in ecken]
    d["punkte_nach_verschmelzen"] = len(sk.skizze.GetSketchPoints2 or ())
    for i, (art, mitte) in enumerate(segmente):
        ende = ecken[(i + 1) % 4]
        if art == "bogen":
            sk.lage(list(mitte), (mitte[0] + 8, mitte[1] + 8))
            nur = 0 if abs(ende[0] - mitte[0]) <= abs(ende[1] - mitte[1]) else 1
            lage_nur(sk, ende, (ende[0] + 8, ende[1] + 8), nur)
        else:
            sk.lage(list(ende), (ende[0] + 8, ende[1] + 8))
    return d


def _serverfehler(e: Exception) -> bool:
    return getattr(e, "hresult", None) == HR_SERVERFEHLER


class _NeuerVersuch(Exception):
    pass


def setze_variable(model, name: str, wert) -> None:
    """Globale Variable (Gleichung "name" = wert) ändern und neu aufbauen (parametrisierte Property-Put, S9a-5)."""
    g = model.GetEquationMgr
    texte = [g.Equation(i) for i in range(g.GetCount)]
    index = next(i for i, t in enumerate(texte) if t.replace(" ", "").startswith(f'"{name}"='))
    dispid = g._oleobj_.GetIDsOfNames("Equation")
    g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, f'"{name}" = {wert!r}')
    g.EvaluateAll


def _fall(app, r, ebene, zeichnen, soll_flaeche, parameter=None, aendere=None) -> dict:
    """Ein Fall mit höchstens zwei Teilen: bei „Ausnahmefehler des Servers“ einmal neu, beide Aufrufketten im Ergebnis."""
    fehlversuche: list[dict] = []
    for versuch in range(2):
        try:
            d = _fall_einmal(app, r, ebene, zeichnen, soll_flaeche, parameter, aendere)
            d["fehlversuche_serverfehler"] = fehlversuche
            return d
        except _NeuerVersuch as e:
            fehlversuche.append({"versuch": versuch + 1, "meldung": str(e), "aufrufkette": traceback.format_exc()})
    return {"fehler_fall": "Serverfehler in beiden Versuchen", "fehlversuche_serverfehler": fehlversuche}


def _fall_einmal(app, r, ebene, zeichnen, soll_flaeche, parameter, aendere) -> dict:
    """Skizze auf ebene mit zeichnen(sk, ctx) (Skizze offen), schließen, Gleichungen setzen, Extrusion blind 10, Volumen."""
    with teil(app, r) as model:
        d: dict = {"stufe": "start"}
        if parameter:
            globale_variablen(model, parameter)
        ctx = kontext(app, model, parameter)
        se = ebene_aufloesen(ctx, ebene)
        sm = model.SketchManager
        sw.auswahl_leeren(model)
        sw.waehle(model, se.objekt, 0)
        sm.InsertSketch(True)
        d["stufe"] = "skizze_offen"
        masse = []
        try:
            try:
                sk = Skizzierer(ctx, se, sm.ActiveSketch)  # ModelToSketchTransform (zu_skizze) im Konstruktor
            except Exception as e:
                if _serverfehler(e):
                    raise _NeuerVersuch("Skizzierer.__init__ (ModelToSketchTransform)") from e
                raise
            try:
                with sw.einstellung(app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
                    d["schritte"] = zeichnen(sk, ctx)
            except Exception as e:  # Spike: Fehler als Befund festhalten, aber Serverfehler nie überspielen
                if _serverfehler(e):
                    raise _NeuerVersuch("in zeichnen") from e
                d["fehler"] = repr(e)
                d["teilprotokoll"] = getattr(sk, "protokoll", None)
            masse = sk.masse
            d["stufe"] = "gezeichnet"
            d["relationen"] = _relationen(sm.ActiveSketch)
            d["status"] = sm.ActiveSketch.GetConstrainedStatus
            d["punkte"] = len(sm.ActiveSketch.GetSketchPoints2 or ())
            d["segmente"] = _segmente(sm.ActiveSketch)
        finally:
            sm.InsertSketch(True)
        d["stufe"] = "geschlossen"
        skizze = sw.letztes_feature(model)
        skizze.Name = SKIZZE
        d["masse"] = _masse(skizze)
        for m in masse:
            ctx.verknuepfe(f"{m.name}@{SKIZZE}", m.roh, m.vorzeichen)
        d["gebunden"] = [f"{m.name}@{SKIZZE} = {m.roh}" for m in masse if isinstance(m.roh, str)]
        sw.auswahl_leeren(model)
        skizze.Select2(False, 0)
        f = model.FeatureManager.FeatureExtrusion3(
            True, False, False, 0, 0, 0.010, 0.0, False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True, 0, 0.0, False,
        )
        d["stufe"] = "extrudiert"
        d["extrusion"] = f is not None
        d["volumen_ist"] = volumen_mm3(model)
        d["volumen_soll"] = round(soll_flaeche * 10, 3)
        d["box"] = [round(c * 1000, 4) for c in model.GetPartBox(True)]
        if aendere is not None:
            try:
                d["aenderung"] = aendere(model, d)
            except Exception as e:
                if _serverfehler(e):
                    raise _NeuerVersuch("in aendere") from e
                d["aenderung"] = f"FEHLER {e!r}"
        return d


def per_gleichung(neue_werte: dict, flaeche_neu_mm2: float):
    """Änderungstest: Parameter (globale Variablen) per Gleichung ändern, neu aufbauen, Volumen mit der neuen
    analytischen Fläche vergleichen (nicht die Maße direkt ändern)."""
    def aendere(model, d) -> dict:
        for name, wert in neue_werte.items():
            setze_variable(model, name, wert)
        ok = model.EditRebuild3
        return {"neue_werte": neue_werte, "rebuild": ok, "volumen_ist": volumen_mm3(model),
                "volumen_soll": round(flaeche_neu_mm2 * 10, 3),
                "box": [round(c * 1000, 4) for c in model.GetPartBox(True)],
                "whatswrong": model.Extension.GetWhatsWrongCount,
                "masse_nachher": [(m["name"], m["wert"]) for m in _masse(model.FeatureByName(SKIZZE))]}
    return aendere


def pruefen(auswahl: list[str]) -> dict:
    r, app = start()
    ecke = math.pi / 4
    flaeche_rechteck = lambda rad: 2400 - rad**2 * (4 - math.pi)  # noqa: E731
    flaeche_l = lambda rk, ri: 1200 - 5 * rk**2 * (1 - ecke) + ri**2 * (1 - ecke)  # noqa: E731
    flaeche_nut = lambda laenge, breite: laenge * breite + math.pi * (breite / 2) ** 2  # noqa: E731
    flaeche_kontur = 1600 + 100 * math.pi
    nut_params = {"L": 30, "B": 8}
    nut_aendern = per_gleichung({"L": 40, "B": 6}, flaeche_nut(40, 6))
    faelle = {
        "a_rechteck_linien": ("oben", rechteck("linien", "=R"), flaeche_rechteck(5), {"R": 5},
                              per_gleichung({"R": 4}, flaeche_rechteck(4))),
        "a_rechteck_linien_eigenes_mass": ("oben", rechteck("linien", None, True), flaeche_rechteck(5), None, None),
        "a_rechteck_punkt": ("oben", rechteck("punkt"), flaeche_rechteck(5), None, None),
        "b_polygon_konkav": ("vorne", polygon(True), flaeche_l(3, 5), {"RK": 3, "RI": 5},
                             per_gleichung({"RK": 2, "RI": 4}, flaeche_l(2, 4))),
        "c_langloch_mittelpunkt_0": ("oben", langloch("mittelpunkt", 0, True), flaeche_nut(30, 8), nut_params, nut_aendern),
        "c_langloch_linie_0": ("oben", langloch("linie", 0, True), flaeche_nut(30, 8), nut_params, nut_aendern),
        "c_langloch_mittelpunkt_90": ("oben", langloch("mittelpunkt", 90, True), flaeche_nut(30, 8), nut_params, nut_aendern),
        "c_langloch_mittelpunkt_30": ("oben", langloch("mittelpunkt", 30, True), flaeche_nut(30, 8), nut_params, nut_aendern),
        "c_langloch_mittelpunkt_30_koinzident": ("oben", langloch("mittelpunkt", 30, True, "sgCOINCIDENT"),
                                                 flaeche_nut(30, 8), nut_params, nut_aendern),
        **{f"d_kontur_{e}": (e, kontur, flaeche_kontur, None, None) for e in ("oben", "vorne", "rechts")},
    }
    out: dict = {}
    for name, (ebene, zeichnen, soll, parameter, aendere) in faelle.items():
        if auswahl and not any(name.startswith(p) for p in auswahl):
            continue
        try:
            out[name] = _fall(app, r, ebene, zeichnen, soll, parameter, aendere)
        except Exception as e:  # Spike: ein Fehlschlag darf die Befunde der anderen Fälle nicht verlieren
            out[name] = {"fehler_fall": repr(e), "aufrufkette": traceback.format_exc()}
    return out


if __name__ == "__main__":
    teilauswahl = sys.argv[1:]
    lauf("s10_f5_skizzen" + ("_teil" if teilauswahl else ""), lambda: pruefen(teilauswahl))
