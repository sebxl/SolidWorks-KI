"""S17 (Paket Bemaßungsbezug): Bemaßen zu Modellkante, Seitenfläche und symmetrisch; Handtest (Breite ändern).

Block 100 × 60 × 20 auf Ebene oben über den Compiler (nur Zahlen, ohne Gleichungen); Deckfläche y = 20, Skizzen auf
{feature: f1, flaeche: "+y"}: u = X, v = −Z; linke Kante u = −50, rechte u = +50. Jeder Fall in einem eigenen Teil.
1 Punkt (−40, 10) zur linken Kante: AddHorizontal-/AddVerticalDimension2 (je nach Skizzenachse von u) bzw. AddDimension2.
2 wie 1 zur Seitenfläche −x von f1.
3 Rechteckseite (Rechteck 20 × 10, linke Seite bei u = −45) zur linken Kante mit AddDimension2 (Soll 5).
4 Positionsskizze der Normbohrung M6 (−40, ±20): Mittellinie entlang u, Symmetrie, Abstand 40, Rand 10; Ende der
  Mittellinie auf der linken Kante (kante) bzw. Längenmaß 50 (laenge). positionen_festlegen wird im Spike ersetzt.
5 Symmetrie zweier Kreise zu einer Mittellinie; Rechteck über Konstruktionsdiagonale + sgATMIDDLE am Ursprung bzw. über
  einen Skizzenpunkt mittig der Diagonale mit Lage zum Ursprung.
6 Handtest: Bohrung 10 mm vom rechten Rand (Schnitt, mit Fase, Bohrungsassistent), Breite 100 → 90, Achse bei x = 30?
7 Gespeichertes Teil aus 6a öffnen, Maße über Parameter(name).SystemValue lesen.

Nachgeschlagen mit `swki api methode` (2026-10-24) zusätzlich zu den Global Constraints des Plans:
ISketchManager.CreatePoint (3), CreateCenterLine (6), CreateLine (6), CreateCircleByRadius (4), InsertSketch (1),
ActiveSketch (Property); ISketch.RelationManager (Property), GetSketchPoints2 (0), GetSketchSegments (0);
ISketchRelationManager.GetRelations (1); ISketchRelation.GetRelationType (0), GetEntities (0), GetEntitiesType (0);
ISketchSegment.ConstructionGeometry (Property), GetType (0); ISketchLine.GetStartPoint2/GetEndPoint2 (0);
ISketchArc.GetCenterPoint2 (0); IDisplayDimension.GetDimension2 (1); IDimension.Name (Property),
GetSystemValue3 (2); IModelDoc2.ForceRebuild3 (1), ClearSelection2 (1), GetTitle (0); IFeature.GetFaces (0),
Select2 (2), GetSpecificFeature2 (0), GetFirstSubFeature (0), Name (Property); IEntity.Select4 (2);
IModelDocExtension.SaveAs3 (7); ISldWorks.OpenDoc6 (6), CloseDoc (1). Enum swConstraintType_e (Namen unten).

Aufruf: .venv\\Scripts\\python.exe -m spikes.s17_bemassungsbezug
"""

import traceback
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import feature_masse
from swki.bemassung import bezug_von
from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.anker import flaeche_in_richtung
from swki.compiler.handler import normbohrung as nb_modul
from swki.compiler.handler.extrusion import ENDE, schnitt
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.compiler.skizze import Skizzierer, ebene_aus_flaeche, positionsskizze
from swki.compiler.topologie import flaechen, kante_aus, loese_flaeche
from swki.konfig import lade_rechner
from swki.pruefung.messen import oeffne, rebuild_fehler
from swki.verbindung import verbinde

BLOCK = {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}}
DECK = {"feature": "f1", "flaeche": "+y"}
TEXT = 8.0  # Abstand der Maßtexte (mm)
# swConstraintType_e (swki api enum swConstraintType_e)
BEZIEHUNG = {1: "DISTANCE", 2: "ANGLE", 3: "RADIUS", 4: "HORIZONTAL", 5: "VERTICAL", 9: "COINCIDENT", 11: "SYMMETRIC",
             12: "ATMIDDLE", 14: "SAMELENGTH", 15: "DIAMETER", 25: "HORIZPOINTS", 26: "VERTPOINTS", 27: "COLINEAR",
             32: "USEEDGE"}
SG_ZU_TYP = {"sgCOINCIDENT": "COINCIDENT", "sgHORIZONTAL2D": "HORIZONTAL", "sgVERTICAL2D": "VERTICAL",
             "sgSYMMETRIC": "SYMMETRIC", "sgATMIDDLE": "ATMIDDLE", "sgHORIZONTALPOINTS2D": "HORIZPOINTS",
             "sgVERTICALPOINTS2D": "VERTPOINTS"}
MASS_TYPEN = {"DISTANCE", "ANGLE", "RADIUS", "DIAMETER"}


# --- Bausteine ---------------------------------------------------------------------------------------------------

@contextmanager
def _teil(app, r, *features):
    """Neues Teil, Block f1 (+ weitere Features) über den Compiler; liefert (ctx, fehler). Immer schließen."""
    spec = {"art": "teil", "name": "S17", "parameter": {}, "features": [BLOCK, *features]}
    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, Path("s17.yaml"), 0.1)
        protokoll = Protokoll("S17", "s17.yaml", 0, r.sw_jahr)
        yield ctx, baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
    finally:
        sw.schliesse(app, model)


@contextmanager
def _skizze(ctx, name: str):
    """Skizze auf der Deckfläche öffnen (AddToDB, ohne Maßeingabe-Dialog); danach schließen und benennen."""
    se = ebene_aus_flaeche(loese_flaeche(ctx, DECK))
    model, sm = ctx.model, ctx.model.SketchManager
    sw.auswahl_leeren(model)
    sw.waehle(model, se.objekt, 0)
    sm.InsertSketch(True)
    halter: dict = {}
    try:
        halter["sk"] = Skizzierer(ctx, se, sm.ActiveSketch)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            yield halter
    finally:
        sm.InsertSketch(True)
        feature = sw.letztes_feature(model)
        feature.Name = name
        halter["feature"] = feature


def _randkante(ctx, u: float):
    """Gerade Kante der Deckfläche parallel zu Z bei x = u (linke Kante u = −50, rechte u = +50)."""
    deck = loese_flaeche(ctx, DECK)
    for e in deck.objekt.GetEdges or ():
        k = kante_aus(e)
        if k.art == "linie" and abs(k.start[0] - u) < 1e-6 and abs(k.ende[0] - u) < 1e-6:
            return k
    raise RuntimeError(f"Randkante x = {u} nicht gefunden")


def _seitenflaeche(ctx, richtung: str):
    return flaeche_in_richtung(flaechen(ctx.ergebnis("f1").features[0]), richtung)


def _waehle(model, *objekte) -> None:
    sw.auswahl_leeren(model)
    for i, o in enumerate(objekte):
        sw.waehle(model, o, 0, anhaengen=i > 0)


def _beziehung(model, gesetzt: list, art: str, *objekte) -> None:
    _waehle(model, *objekte)
    model.SketchAddConstraints(art)
    sw.auswahl_leeren(model)
    gesetzt.append(art)


def _mass_info(anzeige, aufruf: str) -> dict:
    if anzeige is None:
        return {"aufruf": aufruf, "fehler": f"{aufruf} lieferte None", "mass": None}
    dim = anzeige.GetDimension2(0)
    return {"aufruf": aufruf, "fehler": None, "mass": dim.Name, "wert_mm": round(dim.SystemValue * 1000, 6),
            "driven_state": dim.DrivenState}


def _mass_achse(sk, achse: int, objekte: tuple, text_uv, namen: str) -> dict:
    """Achsparalleles Maß in Richtung der Spec-Achse `achse` (0 = u, 1 = v) zwischen den gewählten Objekten."""
    model = sk.model
    waagrecht = sk.x_von[0] == achse  # liegt die Spec-Achse auf Skizzen-x?
    _waehle(model, *objekte)
    text = sk._text(*text_uv)
    if waagrecht:
        anzeige, aufruf = model.AddHorizontalDimension2(*text), f"AddHorizontalDimension2({namen})"
    else:
        anzeige, aufruf = model.AddVerticalDimension2(*text), f"AddVerticalDimension2({namen})"
    sw.auswahl_leeren(model)
    return _mass_info(anzeige, aufruf)


def _mass_frei(sk, objekte: tuple, text_uv, namen: str) -> dict:
    _waehle(sk.model, *objekte)
    anzeige = sk.model.AddDimension2(*sk._text(*text_uv))
    sw.auswahl_leeren(sk.model)
    return _mass_info(anzeige, f"AddDimension2({namen})")


def _ausrichtung(sk, achse: int) -> str:
    """sg-Kennung, die zwei Punkte auf der Spec-Achse `achse` gleich setzt (gleiches Skizzen-x → VERTICALPOINTS)."""
    return "sgVERTICALPOINTS2D" if sk.x_von[0] == achse else "sgHORIZONTALPOINTS2D"


def _entlang(sk, achse: int) -> str:
    """sg-Kennung für eine Linie entlang der Spec-Achse `achse`."""
    return "sgHORIZONTAL2D" if sk.x_von[0] == achse else "sgVERTICAL2D"


def _beziehungen(skizze) -> list[str]:
    return [BEZIEHUNG.get(b.GetRelationType, str(b.GetRelationType))
            for b in skizze.RelationManager.GetRelations(0) or ()]


def _neu(vorher: list[str], nachher: list[str]) -> list[str]:
    return sorted((Counter(nachher) - Counter(vorher)).elements())


def _ueberzaehlig(neu: list[str], gesetzt: list[str]) -> list[str]:
    """Neue Beziehungen (ohne Maße), die nicht selbst gesetzt wurden."""
    erwartet = Counter(SG_ZU_TYP.get(g, g) for g in gesetzt)
    return sorted((Counter(b for b in neu if b not in MASS_TYPEN) - erwartet).elements())


def _status(feature) -> int:
    return feature.GetSpecificFeature2.GetConstrainedStatus


def _lage(sk, uv, achsen=(0, 1)) -> None:
    """Lage zum Ursprung wie früher Skizzierer.lage (seit dem Bemaßungsbezug: Kennpunkt + lagen_festlegen)."""
    sk.kennpunkt(tuple(uv), tuple(uv), bezug_von({}), None, "", achsen)
    sk.lagen_festlegen()


def _rechteck(sk, mitte, breite: float, hoehe: float, gesetzt: list) -> list:
    """Vier Linien (wie Skizzierer.element), Richtungen, Breite und Höhe. Rückgabe: Linien unten, rechts, oben, links."""
    mu_, mv = mitte
    ecken = [(mu_ - breite / 2, mv - hoehe / 2), (mu_ + breite / 2, mv - hoehe / 2),
             (mu_ + breite / 2, mv + hoehe / 2), (mu_ - breite / 2, mv + hoehe / 2)]
    seg = sk._linienzug([sk.zu_skizze(*e) for e in ecken])
    for i, linie in enumerate(seg):
        _beziehung(sk.model, gesetzt, _entlang(sk, 0 if i % 2 == 0 else 1), linie)
    sk.groesse(seg[0], (mu_, mv - hoehe / 2 - TEXT), breite)
    sk.groesse(seg[1], (mu_ + breite / 2 + TEXT, mv), hoehe)
    return seg


def _gleicher_punkt(a, b) -> bool:
    return tuple(a.GetID) == tuple(b.GetID)


def _diagonale(sk, seg, gesetzt: list) -> tuple:
    """Konstruktionsdiagonale von Ecke unten links nach oben rechts; Endpunkte an die Ecken binden, falls getrennt."""
    e0, e2 = seg[0].GetStartPoint2, seg[1].GetEndPoint2
    diag = sk.sm.CreateCenterLine(e0.X, e0.Y, 0.0, e2.X, e2.Y, 0.0)
    if diag is None:
        raise RuntimeError("CreateCenterLine (Diagonale) lieferte None")
    geteilt = []
    for ende, ecke in ((diag.GetStartPoint2, e0), (diag.GetEndPoint2, e2)):
        if _gleicher_punkt(ende, ecke):
            geteilt.append(True)
        else:
            geteilt.append(False)
            _beziehung(sk.model, gesetzt, "sgCOINCIDENT", ende, ecke)
    return diag, {"diagonale_konstruktion": bool(diag.ConstructionGeometry), "diagonale_teilt_ecken": geteilt}


def _achsen(feature) -> list[list[float]]:
    """Achslagen (x, z in mm) der Zylinderflächen eines Features (Achse parallel Y)."""
    lagen = {(round(f.punkt[0], 4), round(f.punkt[2], 4)) for f in flaechen(feature) if f.art == "zylinder"}
    return [list(p) for p in sorted(lagen)]


# --- 1, 2: Punkt zu Kante bzw. Seitenfläche ----------------------------------------------------------------------

def fall_punkt(app, r, ziel: str, methode: str) -> dict:
    with _teil(app, r) as (ctx, fehler):
        if fehler is not None:
            return {"fehler": repr(fehler)}
        bezug = _randkante(ctx, -50).objekt if ziel == "kante" else _seitenflaeche(ctx, "-x").objekt
        d: dict = {}
        with _skizze(ctx, "s_punkt") as h:
            sk = h["sk"]
            x, y = sk.zu_skizze(-40, 10)
            punkt = sk.sm.CreatePoint(x, y, 0.0)
            namen = f"Punkt, {'Kante' if ziel == 'kante' else 'Seitenfläche -x'}"
            if methode == "hv":
                d |= _mass_achse(sk, 0, (punkt, bezug), (-45, 10 + TEXT), namen)
            else:
                d |= _mass_frei(sk, (punkt, bezug), (-45, 10 + TEXT), namen)
            _lage(sk, (-40, 10), (1,))
            d["status"] = sk.skizze.GetConstrainedStatus
            d["beziehungen_neu"] = _beziehungen(sk.skizze)
        d["status_geschlossen"] = _status(h["feature"])
        d["masse"] = feature_masse(h["feature"])
        d["rebuild_fehler"] = rebuild_fehler(ctx.model)
        return d


# --- 3: Rechteckseite zu Kante -------------------------------------------------------------------------------------

def fall_linie_kante(app, r) -> dict:
    with _teil(app, r) as (ctx, fehler):
        if fehler is not None:
            return {"fehler": repr(fehler)}
        kante = _randkante(ctx, -50).objekt
        d: dict = {"rechteck": {"mitte": [-35, 10], "breite": 20, "hoehe": 10}}
        gesetzt: list = []
        with _skizze(ctx, "s_linie") as h:
            sk = h["sk"]
            seg = _rechteck(sk, (-35, 10), 20, 10, gesetzt)
            _lage(sk, (-45, 5), (1,))  # Ecke unten links: nur v zum Ursprung
            d["status_vor_randmass"] = sk.skizze.GetConstrainedStatus
            d |= _mass_frei(sk, (seg[3], kante), (-47.5, 10 + 2 * TEXT), "linke Rechteckseite, Kante")
            d["status"] = sk.skizze.GetConstrainedStatus
            d["beziehungen_neu"] = _beziehungen(sk.skizze)
        d["status_geschlossen"] = _status(h["feature"])
        d["masse"] = feature_masse(h["feature"])
        d["rebuild_fehler"] = rebuild_fehler(ctx.model)
        return d


# --- 4, 6c: Positionsskizze mit Rand und Symmetrie -----------------------------------------------------------------

def _positionen_mit_bezug(befund: dict, variante: str, seite: int):
    """Ersatz für skizze.positionen_festlegen: zweiter Punkt, Mittellinie entlang u durch den Ursprung bis zur Randkante
    (seite −1 links, +1 rechts; Ende deckungsgleich mit der Kante bzw. Längenmaß 50), Symmetrie, Abstand, Randmaß.
    Wirft nicht bei Status ≠ 3 (Befund statt Bauabbruch)."""

    def festlegen(ctx, feature, se, positionen, name, bezug=None, pfad=None) -> None:
        skizze_f = positionsskizze(feature)
        model, sm = ctx.model, ctx.model.SketchManager
        kante = _randkante(ctx, 50 * seite).objekt
        gesetzt: list = []
        sw.auswahl_leeren(model)
        skizze_f.Select2(False, 0)
        sm.InsertSketch(True)
        try:
            sk = Skizzierer(ctx, se, sm.ActiveSketch)
            with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
                befund["status_vorher"] = sk.skizze.GetConstrainedStatus
                vorher = _beziehungen(sk.skizze)
                (u1, v1), (u2, v2) = positionen
                p1 = sk._punkt(*sk.zu_skizze(u1, v1))
                x2, y2 = sk.zu_skizze(u2, v2)
                p2 = sm.CreatePoint(x2, y2, 0.0)
                xa, ya = sk.zu_skizze(0, 0)
                xb, yb = sk.zu_skizze(50 * seite, 0)
                ml = sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0)
                if p2 is None or ml is None:
                    raise RuntimeError(f"CreatePoint {p2 is not None} / CreateCenterLine {ml is not None}")
                _beziehung(model, gesetzt, "sgCOINCIDENT", ml.GetStartPoint2, sk.ursprung)
                _beziehung(model, gesetzt, _entlang(sk, 0), ml)
                if variante == "kante":
                    _beziehung(model, gesetzt, "sgCOINCIDENT", ml.GetEndPoint2, kante)
                    befund["mittellinie"] = {"aufruf": "SketchAddConstraints(sgCOINCIDENT) Endpunkt, Kante"}
                else:
                    befund["mittellinie"] = _mass_frei(sk, (ml,), (25 * seite, -TEXT), "Mittellinie (Länge 50)")
                befund["status_nach_mittellinie"] = sk.skizze.GetConstrainedStatus
                _beziehung(model, gesetzt, "sgSYMMETRIC", p1, p2, ml)
                befund["status_nach_symmetrie"] = sk.skizze.GetConstrainedStatus
                befund["abstand"] = _mass_achse(sk, 1, (p1, p2), (u1 + seite * TEXT, 0), "Punkt 1, Punkt 2")
                befund["rand"] = _mass_achse(sk, 0, (p1, kante), ((u1 + 50 * seite) / 2, v1 + TEXT), "Punkt 1, Kante")
                befund["status"] = sk.skizze.GetConstrainedStatus
                befund["gesetzt"] = gesetzt
                befund["beziehungen_neu"] = _neu(vorher, _beziehungen(sk.skizze))
                befund["ueberzaehlig"] = _ueberzaehlig(befund["beziehungen_neu"], gesetzt)
        finally:
            sm.InsertSketch(True)
        skizze_f.Name = name
        befund["status_geschlossen"] = _status(skizze_f)
        befund["masse"] = feature_masse(skizze_f)

    return festlegen


@contextmanager
def _ersetzt(funktion):
    alt = nb_modul.positionen_festlegen
    nb_modul.positionen_festlegen = funktion
    try:
        yield
    finally:
        nb_modul.positionen_festlegen = alt


def _normbohrung(positionen: list) -> dict:
    return {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": DECK,
            "positionen": positionen, "tiefe": 10, "gewindetiefe": 8}


def fall_positionsskizze(app, r, variante: str) -> dict:
    befund: dict = {}
    with _ersetzt(_positionen_mit_bezug(befund, variante, -1)), \
            _teil(app, r, _normbohrung([[-40, 20], [-40, -20]])) as (ctx, fehler):
        d = {"fehler": None if fehler is None else repr(fehler), "positionsskizze": befund}
        feature = ctx.model.FeatureByName("f2")
        if feature is not None:
            d["bohrungen_achsen_xz"] = _achsen(feature)
            d["bohrungen"] = len(d["bohrungen_achsen_xz"])
            d["rebuild_fehler"] = rebuild_fehler(ctx.model)
        return d


# --- 5: Symmetrie und Rechteck über die Mitte -----------------------------------------------------------------------

def fall_symmetrie_kreise(app, r) -> dict:
    with _teil(app, r) as (ctx, fehler):
        if fehler is not None:
            return {"fehler": repr(fehler)}
        d: dict = {}
        gesetzt: list = []
        with _skizze(ctx, "s_kreise") as h:
            sk = h["sk"]
            vorher = _beziehungen(sk.skizze)
            mitten = []
            for u in (30, -30):
                x, y = sk.zu_skizze(u, 0)
                kreis = sk.sm.CreateCircleByRadius(x, y, 0.0, 0.004)
                sk.groesse(kreis, (u + 4 + TEXT, TEXT), 8)
                mitten.append(sk._punkt(x, y))
            xa, ya = sk.zu_skizze(0, 0)
            xb, yb = sk.zu_skizze(0, 20)
            ml = sk.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0)
            _beziehung(sk.model, gesetzt, "sgCOINCIDENT", ml.GetStartPoint2, sk.ursprung)
            _beziehung(sk.model, gesetzt, _entlang(sk, 1), ml)
            d["mittellinie"] = _mass_frei(sk, (ml,), (-TEXT, 10), "Mittellinie (Länge 20)")
            _beziehung(sk.model, gesetzt, "sgSYMMETRIC", mitten[0], mitten[1], ml)
            d["abstand"] = _mass_achse(sk, 0, (mitten[0], mitten[1]), (0, -2 * TEXT), "Mitte 1, Mitte 2")
            _beziehung(sk.model, gesetzt, _ausrichtung(sk, 1), mitten[0], sk.ursprung)
            d["status"] = sk.skizze.GetConstrainedStatus
            d["gesetzt"] = gesetzt
            d["beziehungen_neu"] = _neu(vorher, _beziehungen(sk.skizze))
            d["ueberzaehlig"] = _ueberzaehlig(d["beziehungen_neu"], gesetzt)
        d["status_geschlossen"] = _status(h["feature"])
        d["masse"] = feature_masse(h["feature"])
        d["rebuild_fehler"] = rebuild_fehler(ctx.model)
        return d


def fall_rechteck(app, r, variante: str) -> dict:
    """diagonale: Rechteck 40 × 20 um (0, 0), sgATMIDDLE Ursprung–Diagonale.
    symmetrie: Rechteck 40 × 20 um (20, 10), Skizzenpunkt mittig der Diagonale (sgATMIDDLE), Lage 20/10 zum Ursprung."""
    mitte = (0, 0) if variante == "diagonale" else (20, 10)
    with _teil(app, r) as (ctx, fehler):
        if fehler is not None:
            return {"fehler": repr(fehler)}
        d: dict = {"rechteck": {"mitte": list(mitte), "breite": 40, "hoehe": 20}}
        gesetzt: list = []
        with _skizze(ctx, "s_rechteck") as h:
            sk = h["sk"]
            vorher = _beziehungen(sk.skizze)
            seg = _rechteck(sk, mitte, 40, 20, gesetzt)
            diag, info = _diagonale(sk, seg, gesetzt)
            d |= info
            if variante == "diagonale":
                _beziehung(sk.model, gesetzt, "sgATMIDDLE", sk.ursprung, diag)
            else:
                x, y = sk.zu_skizze(*mitte)
                punkt = sk.sm.CreatePoint(x, y, 0.0)
                _beziehung(sk.model, gesetzt, "sgATMIDDLE", punkt, diag)
                _lage(sk, mitte)
            d["status"] = sk.skizze.GetConstrainedStatus
            d["gesetzt"] = gesetzt
            d["beziehungen_neu"] = _neu(vorher, _beziehungen(sk.skizze))
            d["ueberzaehlig"] = _ueberzaehlig(d["beziehungen_neu"], gesetzt)
        d["status_geschlossen"] = _status(h["feature"])
        d["masse"] = feature_masse(h["feature"])
        d["rebuild_fehler"] = rebuild_fehler(ctx.model)
        return d


# --- 6, 7: Handtest und Lesen ---------------------------------------------------------------------------------------

def _breitenmass(model) -> str:
    """Name "<Maß>@f1_skizze" des Breitenmaßes 100 (feature_masse der Skizze von f1)."""
    skizze = model.FeatureByName("f1_skizze")
    treffer = [m["name"] for m in feature_masse(skizze) if abs(m["wert"] - 0.1) < 1e-9]
    if len(treffer) != 1:
        raise RuntimeError(f"Breitenmaß nicht eindeutig: {feature_masse(skizze)}")
    return f"{treffer[0]}@f1_skizze"


def _kreis_am_rand(ctx) -> dict:
    """Kreis Ø8 bei (40, 0), Mitte 10 mm zur rechten Kante (Weg aus Zeile 1), v = 0 per Ausrichtung; Schnitt durch alles."""
    kante = _randkante(ctx, 50).objekt
    d: dict = {}
    with _skizze(ctx, "f2_skizze") as h:
        sk = h["sk"]
        x, y = sk.zu_skizze(40, 0)
        kreis = sk.sm.CreateCircleByRadius(x, y, 0.0, 0.004)
        sk.groesse(kreis, (40, 4 + TEXT), 8)
        mitte = sk._punkt(x, y)
        d["rand"] = _mass_achse(sk, 0, (mitte, kante), (45, -TEXT), "Kreismitte, rechte Kante")
        _lage(sk, (40, 0), (1,))
        d["status"] = sk.skizze.GetConstrainedStatus
    sw.auswahl_leeren(ctx.model)
    h["feature"].Select2(False, 0)
    feature = schnitt(ctx.model, ENDE["durch_alles"], 0.0, False)
    sw.auswahl_leeren(ctx.model)
    if feature is None:
        raise RuntimeError("FeatureCut4 (durch alles) lieferte None")
    feature.Name = "f2"
    d["rebuild_fehler_bau"] = rebuild_fehler(ctx.model)
    return d


def _breite_aendern(ctx, d: dict, bohrung: str, skizze_name: str, randmass: str | None) -> None:
    model = ctx.model
    breite = _breitenmass(model)
    d["breitenmass"] = breite
    feature = model.FeatureByName(bohrung)
    d["achsen_vorher"] = _achsen(feature)
    d["set_system_value3"] = model.Parameter(breite).SetSystemValue3(0.09, 1, None)
    d["edit_rebuild3"] = model.EditRebuild3
    d["rebuild_fehler"] = rebuild_fehler(model)
    d["breite_nachher_mm"] = round(model.Parameter(breite).SystemValue * 1000, 6)
    d["achsen_nachher"] = _achsen(feature)
    d["x_ist"] = [a[0] for a in d["achsen_nachher"]]
    d["x_soll"] = 30.0
    d["x_abw_max"] = max((abs(x - 30.0) for x in d["x_ist"]), default=None)
    if randmass is not None:
        d["randmass_nachher_mm"] = round(model.Parameter(randmass).SystemValue * 1000, 6)
    skizze = model.FeatureByName(skizze_name)
    d["status_skizze_nachher"] = _status(skizze) if skizze is not None else None
    model.ForceRebuild3(True)
    d["achsen_nach_force"] = _achsen(feature)


def fall_handtest(app, r, fase: bool, lesen: dict | None = None) -> dict:
    with _teil(app, r) as (ctx, fehler):
        if fehler is not None:
            return {"fehler": repr(fehler)}
        d = _kreis_am_rand(ctx)
        if fase:
            alle_handler()["fase"](ctx, {"id": "f3", "typ": "fase", "kanten": [{"nahe": [50, 20, 0]}], "abstand": 1})
            d["fase_rebuild_fehler"] = rebuild_fehler(ctx.model)
        randmass = f"{d['rand']['mass']}@f2_skizze" if d["rand"].get("mass") else None
        if lesen is not None:
            pfad = lade_rechner().arbeitsordner / "S17" / "s17_6a.sldprt"
            if pfad.exists():
                pfad.unlink()
            sw.speichere(ctx.model, pfad, kopie=True)
            lesen |= {"pfad": str(pfad), "randmass": randmass, "breitenmass": _breitenmass(ctx.model)}
        _breite_aendern(ctx, d, "f2", "f2_skizze", randmass)
        return d


def fall_handtest_normbohrung(app, r, variante: str) -> dict:
    befund: dict = {}
    with _ersetzt(_positionen_mit_bezug(befund, variante, +1)), \
            _teil(app, r, _normbohrung([[40, 20], [40, -20]])) as (ctx, fehler):
        d = {"fehler": None if fehler is None else repr(fehler), "positionsskizze": befund}
        if fehler is not None:
            return d
        rand = befund.get("rand", {}).get("mass")
        _breite_aendern(ctx, d, "f2", "f2_positionen", f"{rand}@f2_positionen" if rand else None)
        d["bohrungen"] = len(d["achsen_nach_force"])
        return d


def fall_lesen(app, lesen: dict) -> dict:
    if "pfad" not in lesen:
        return {"fehler": "6a hat nichts gespeichert"}
    model = oeffne(app, Path(lesen["pfad"]))
    try:
        d = {"pfad": lesen["pfad"]}
        for schluessel, soll in (("randmass", 0.010), ("breitenmass", 0.100)):
            name = lesen.get(schluessel)
            parameter = model.Parameter(name) if name else None
            d[schluessel] = {"name": name, "soll": soll,
                             "system_value": None if parameter is None else parameter.SystemValue}
        return d
    finally:
        sw.schliesse(app, model)


def _sicher(d: dict, name: str, fn, *args) -> None:
    """Fall ausführen; ein Fehler (mit Aufrufkette) verliert die Befunde der anderen Fälle nicht (kein Wiederholen)."""
    try:
        d[name] = fn(*args)
    except Exception as e:
        d[name] = {"fehler_fall": repr(e), "aufrufkette": traceback.format_exc()}


def pruefen() -> dict:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    d: dict = {"einstellungen_vorher": [app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6)]}
    for ziel, nr in (("kante", 1), ("flaeche", 2)):
        for methode in ("hv", "dim2"):
            _sicher(d, f"{nr}_punkt_{ziel}_{methode}", fall_punkt, app, r, ziel, methode)
    _sicher(d, "3_linie_kante", fall_linie_kante, app, r)
    _sicher(d, "4_mittellinie_kante", fall_positionsskizze, app, r, "kante")
    _sicher(d, "4_mittellinie_laenge", fall_positionsskizze, app, r, "laenge")
    _sicher(d, "5_symmetrie_kreise", fall_symmetrie_kreise, app, r)
    _sicher(d, "5_rechteck_diagonale", fall_rechteck, app, r, "diagonale")
    _sicher(d, "5_rechteck_symmetrie", fall_rechteck, app, r, "symmetrie")
    lesen: dict = {}
    _sicher(d, "6a_handtest", fall_handtest, app, r, False, lesen)
    _sicher(d, "6b_handtest_fase", fall_handtest, app, r, True)
    _sicher(d, "6c_handtest_normbohrung", fall_handtest_normbohrung, app, r, "kante")
    _sicher(d, "6c_handtest_normbohrung_laenge", fall_handtest_normbohrung, app, r, "laenge")
    _sicher(d, "7_lesen", fall_lesen, app, lesen)
    d["einstellungen_nachher"] = [app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6)]
    return d


if __name__ == "__main__":
    lauf("s17_bemassungsbezug", pruefen)
