"""S16 (Paket Formschräge): Formschräge an FeatureExtrusion3/FeatureCut4 – Richtung, Endbedingungen, Maße, Messung.

Block 100 × 60 × 20 auf Ebene oben (Deckfläche y = 20); jeder Fall in einem eigenen Teil, gebaut mit dem Compiler
(Handler extrusion mit den Annahmen DDIR_KLEINER und WINKEL_MASS), gemessen mit swki.pruefung.messen.formschraegen.
1 Richtung: Aufsatz/Schnitt × kleiner/groesser (Kreis Ø20 auf der Deckfläche), dazu Aufsatz und Schnitt mit umkehren.
2 Endbedingungen: mittig (Steg frei über dem Block auf Ebene vorne), durch_alles (Trichter von der Unterseite,
  groesser), bis_flaeche und versatz_von_flaeche (Schnitt von der Deckfläche, kleiner).
3 Ring (Kreise Ø30 und Ø10, Aufsatz kleiner): Vorzeichen und Lage der inneren Seitenfläche; Volumen für beide Deutungen.
4 Maße je Feature (Namen, Werte) und Gleichungen.
5 Messung: punkt_und_normale gegen IFace2.Normal (Ebenen) und ISurface.ConeParams2 (Kegel); größte Winkelabweichung.
6 Rechteck 30 × 20 mit Eckradius 3, Schnitt kleiner, Tiefe 10: 16°, 17°, 20° (Einzug 2,87 / 3,06 / 3,64 mm).
7 Volumen gegen swki.formschraege.volumen: Kreis, Rechteck mit Eckradius (groesser), Sechseck (kleiner), mittig.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s16_formschraege
"""

import math
import traceback
from contextlib import contextmanager
from pathlib import Path

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import feature_masse
from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.handler.extrusion import DDIR_KLEINER, WINKEL_MASS
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.formschraege import querschnitt_koeffizienten, soll_vorzeichen, volumen
from swki.konfig import lade_rechner
from swki.pruefung.messen import formschraegen, punkt_und_normale
from swki.verbindung import in_mm3, verbinde

BLOCK = {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}}
V_BLOCK = 100 * 60 * 20
DECK, UNTEN = {"feature": "f1", "flaeche": "+y"}, {"feature": "f1", "flaeche": "-y"}
KREIS20 = {"kreis": {"mitte": [0, 0], "durchmesser": 20}}


def _f(typ: str, querschnitt: str, element: dict, ebene, ende_typ: str = "blind", **ende) -> dict:
    return {"id": "f2", "typ": typ, "skizze": {"ebene": ebene, "elemente": [element]},
            "ende": {"typ": ende_typ, **ende, "formschraege": {"winkel": "=W", "querschnitt": querschnitt}}}


def _v(element: dict, tiefe: float, winkel: float, querschnitt: str, mittig: bool = False) -> float:
    return volumen(querschnitt_koeffizienten(element, {}), tiefe, winkel, querschnitt, mittig)


@contextmanager
def _gebaut(app, r, f: dict, winkel: float):
    spec = {"art": "teil", "name": "S16", "parameter": {"W": winkel}, "features": [BLOCK, f]}
    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, Path("s16.yaml"), 0.1)
        globale_variablen(model, spec["parameter"])
        protokoll = Protokoll("S16", "s16.yaml", 0, r.sw_jahr)
        yield ctx, baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
    finally:
        sw.schliesse(app, model)


def _flaechen(feature, winkel: float) -> dict:
    """Frage 5: Normale aus punkt_und_normale gegen IFace2.Normal (Ebene) bzw. halben Kegelwinkel (ConeParams2)."""
    liste, abw_normale, abw_winkel = [], 0.0, 0.0
    for face in feature.GetFaces or ():
        s = face.GetSurface
        punkt, n = punkt_und_normale(face)
        e = {"punkt": [round(c, 4) for c in punkt], "n": [round(c, 6) for c in n]}
        if s.IsPlane:
            normal = tuple(face.Normal)
            e |= {"art": "ebene", "normal": [round(c, 6) for c in normal]}
            abw_normale = max(abw_normale, max(abs(a - b) for a, b in zip(n, normal)))
        elif s.IsCone:
            k = s.ConeParams2
            halb = math.degrees(k[7])
            e |= {"art": "kegel", "achse": [round(c, 6) for c in k[3:6]], "halber_winkel": round(halb, 6),
                  "radius_mm": round(k[6] * 1000, 4)}
            abw_winkel = max(abw_winkel, abs(halb - winkel))
        else:
            e["art"] = "sonstige"
        liste.append(e)
    return {"liste": liste, "abw_normale_max": abw_normale, "abw_kegelwinkel_max_grad": abw_winkel}


def fall(app, r, f: dict, winkel: float, soll_aenderung: float | None) -> dict:
    with _gebaut(app, r, f, winkel) as (ctx, fehler):
        d = {"fehler": None if fehler is None else repr(fehler)}
        if fehler is not None:
            return d
        model = ctx.model
        feature = model.FeatureByName(f["id"])
        ist = in_mm3(model.Extension.CreateMassProperty.Volume) - V_BLOCK
        d["volumen_aenderung"] = round(ist, 3)
        if soll_aenderung is not None:
            d["soll_aenderung"] = round(soll_aenderung, 3)
            d["volumen_abw_prozent"] = round(abs(ist - soll_aenderung) / abs(soll_aenderung) * 100, 5)
        d["koerper"] = len(model.GetBodies2(0, False) or ())
        d["masse"] = feature_masse(feature)
        g = model.GetEquationMgr
        d["gleichungen"] = [g.Equation(i) for i in range(g.GetCount)]
        d["soll_vorzeichen"] = soll_vorzeichen(f["typ"], f["ende"]["formschraege"]["querschnitt"])
        gemessen = formschraegen(ctx, ctx.spec)[f["id"]]
        d["gemessen"] = gemessen
        if isinstance(gemessen, dict):
            d["vorzeichen_passt"] = all(x["vorzeichen"] == d["soll_vorzeichen"] for x in gemessen["flaechen"])
            d["winkel_abw_max_grad"] = max((abs(x["winkel"] - winkel) for x in gemessen["flaechen"]), default=None)
        d["flaechen"] = _flaechen(feature, winkel)
        return d


def _sicher(d: dict, name: str, fn, *args) -> None:
    """Fall ausführen; ein Fehler (mit Aufrufkette) verliert die Befunde der anderen Fälle nicht (kein Wiederholen)."""
    try:
        d[name] = fn(*args)
    except Exception as e:
        d[name] = {"fehler_fall": repr(e), "aufrufkette": traceback.format_exc()}


def pruefen() -> dict:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    d: dict = {"annahmen": {"DDIR_KLEINER": DDIR_KLEINER, "WINKEL_MASS": WINKEL_MASS}}
    # 1 Richtung
    for typ in ("extrusion", "schnitt"):
        for q in ("kleiner", "groesser"):
            v = _v(KREIS20, 8, 10, q)
            _sicher(d, f"1_{typ}_{q}", fall, app, r, _f(typ, q, KREIS20, DECK, tiefe=8), 10,
                    v if typ == "extrusion" else -v)
    oben32 = {"versatz": {"ebene": "oben", "abstand": 32}}
    _sicher(d, "1_extrusion_kleiner_umkehren", fall, app, r,
            _f("extrusion", "kleiner", KREIS20, oben32, tiefe=12, umkehren=True), 10, _v(KREIS20, 12, 10, "kleiner"))
    unter5 = {"versatz": {"ebene": "oben", "abstand": -5}}
    _sicher(d, "1_schnitt_kleiner_umkehren", fall, app, r,
            _f("schnitt", "kleiner", KREIS20, unter5, tiefe=13, umkehren=True), 10,
            -(_v(KREIS20, 13, 10, "kleiner") - _v(KREIS20, 5, 10, "kleiner")))
    # 2 Endbedingungen
    steg = {"rechteck": {"mitte": [0, 40], "breite": 40, "hoehe": 12}}
    _sicher(d, "2_mittig", fall, app, r, _f("extrusion", "kleiner", steg, "vorne", "mittig", tiefe=8), 5,
            _v(steg, 8, 5, "kleiner", mittig=True))
    _sicher(d, "2_durch_alles", fall, app, r, _f("schnitt", "groesser", KREIS20, UNTEN, "durch_alles"), 10,
            -_v(KREIS20, 20, 10, "groesser"))
    _sicher(d, "2_bis_flaeche", fall, app, r, _f("schnitt", "kleiner", KREIS20, DECK, "bis_flaeche", flaeche=UNTEN), 10,
            -_v(KREIS20, 20, 10, "kleiner"))
    _sicher(d, "2_versatz_von_flaeche", fall, app, r,
            _f("schnitt", "kleiner", KREIS20, DECK, "versatz_von_flaeche", flaeche=UNTEN, abstand=5), 10,
            -_v(KREIS20, 15, 10, "kleiner"))
    # 3 Ring
    ring = _f("extrusion", "kleiner", {"kreis": {"mitte": [0, 0], "durchmesser": 30}}, DECK, tiefe=10)
    ring["skizze"]["elemente"].append({"kreis": {"mitte": [0, 0], "durchmesser": 10}})
    aussen = _v({"kreis": {"durchmesser": 30}}, 10, 10, "kleiner")
    d["3_ring_soll"] = {"innen_waechst": round(aussen - _v({"kreis": {"durchmesser": 10}}, 10, 10, "groesser"), 3),
                        "innen_schrumpft": round(aussen - _v({"kreis": {"durchmesser": 10}}, 10, 10, "kleiner"), 3)}
    _sicher(d, "3_ring", fall, app, r, ring, 10, None)
    # 6 Eckradius
    eck = {"rechteck": {"mitte": [0, 0], "breite": 30, "hoehe": 20, "radius": 3}}
    for w in (16, 17, 20):
        _sicher(d, f"6_eckradius_{w}", fall, app, r, _f("schnitt", "kleiner", eck, DECK, tiefe=10), w,
                -_v(eck, 10, w, "kleiner"))
    # 7 Volumen weiterer Profile
    eck_gross = {"rechteck": {"mitte": [0, 0], "breite": 30, "hoehe": 20, "radius": 3}}
    _sicher(d, "7_eckradius_groesser", fall, app, r, _f("extrusion", "groesser", eck_gross, DECK, tiefe=10), 10,
            _v(eck_gross, 10, 10, "groesser"))
    sechseck = {"polygon": {"punkte": [[round(20 / math.sqrt(3) * math.cos(math.radians(60 * k)), 6),
                                        round(20 / math.sqrt(3) * math.sin(math.radians(60 * k)), 6)] for k in range(6)]}}
    _sicher(d, "7_sechseck_kleiner", fall, app, r, _f("extrusion", "kleiner", sechseck, DECK, tiefe=10), 10,
            _v(sechseck, 10, 10, "kleiner"))
    return d


if __name__ == "__main__":
    lauf("s16_formschraege", pruefen)
