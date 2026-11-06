"""Spike S20 (Paket Konstruktionsstil): Muster mit Bohrung und Fase als Quelle, Verrundung in Spiegeln, Schrittweite und
Drehsinn des Kreismusters, Sweep, Definitionen der Muster-, Verrundungs- und Fasenfeatures. Kein Produktionscode.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s20_konstruktionsstil [a b c d e]  (SolidWorks muss laufen)
"""

import json
import math
import sys

from swki.compiler import sw
from swki.compiler.skizze import STANDARD
from swki.compiler.topologie import flaechen
from swki.pruefung.messen import rebuild_fehler
from swki.verbindung import in_mm
from tests.live.bauhilfe import gebautes_teil, volumen_mm3, zylinder_mm3

PLATTE = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
          "ende": {"typ": "blind", "tiefe": 20}}
VOLL = 100 * 60 * 20


def _spec(*features):
    return {"art": "teil", "name": "S20", "features": [PLATTE, *features]}


def _arten(feature) -> dict:
    zaehler: dict[str, int] = {}
    for f in flaechen(feature):
        zaehler[f.art] = zaehler.get(f.art, 0) + 1
    return zaehler


def _zylinder(feature) -> list:
    return sorted((round(z.punkt[0], 3), round(z.punkt[1], 3), round(z.punkt[2], 3), round(z.radius, 3))
                  for z in flaechen(feature) if z.art == "zylinder")


def definition(feature) -> dict:
    """Werte der Feature-Definition (Spike f); Late Binding ohne "()"."""
    typ = feature.GetTypeName2
    d = feature.GetDefinition
    aus: dict = {"typ": typ}
    try:
        if typ == "LPattern":
            aus |= {"n1": d.D1TotalInstances, "n2": d.D2TotalInstances, "a1": in_mm(d.D1Spacing),
                    "a2": in_mm(d.D2Spacing), "quellen": [q.Name for q in (d.PatternFeatureArray or ())],
                    "anzahl_quellen": d.GetPatternFeatureCount}
        elif typ == "CirPattern":
            aus |= {"n": d.TotalInstances, "winkel": math.degrees(d.Spacing), "gleich": d.EqualSpacing,
                    "quellen": [q.Name for q in (d.PatternFeatureArray or ())]}
        elif typ == "MirrorPattern":
            ebene = d.Plane
            aus |= {"quellen": [q.Name for q in (d.PatternFeatureArray or ())], "anzahl_quellen": d.GetPatternFeatureCount,
                    "ebene": getattr(ebene, "Name", str(type(ebene)))}
        elif typ == "Fillet":
            aus |= {"radius": in_mm(d.DefaultRadius)}
        elif typ == "Chamfer":
            aus |= {"chamfer_typ": d.Type, "abstand": in_mm(d.GetEdgeChamferDistance(0)),
                    "winkel": math.degrees(d.EdgeChamferAngle)}
    except Exception as e:  # Spike: Fehler beim Lesen festhalten
        aus["fehler"] = repr(e)
    aus["flaechen"] = feature.GetFaceCount
    return aus


def _bericht(ctx, fehler, ids) -> dict:
    return {"fehler": None if fehler is None else repr(fehler), "rebuild": rebuild_fehler(ctx.model),
            "volumen": round(volumen_mm3(ctx.model), 4),
            "features": {i: {"def": definition(ctx.ergebnis(i).features[-1]), "arten": _arten(ctx.ergebnis(i).features[-1])}
                         for i in ids if i in ctx.ergebnisse}}


def spike_a() -> dict:
    """Bohrung Ø 6,6 durch mit Senkung Ø 11 × 6,8, Fase 0,5 am Senkungsrand, Muster ×4 aus Bohrung und Fase."""
    bohrung = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[-40, 20]],
               "durchmesser": 6.6, "durch": True, "senkung": {"durchmesser": 11, "tiefe": 6.8}}
    fase = {"id": "f3", "typ": "fase", "kanten": [{"nahe": [-40 + 5.5, 20, -20]}], "abstand": 0.5}
    muster = {"id": "f4", "typ": "muster_linear", "features": ["f2", "f3"],
              "richtung1": {"achse": "x", "abstand": 20, "anzahl": 4}}
    with gebautes_teil(_spec(bohrung, fase, muster)) as (ctx, fehler, _):
        b = _bericht(ctx, fehler, ["f2", "f3", "f4"])
        c = 0.5
        b["soll_ohne_fase"] = VOLL - 4 * (zylinder_mm3(6.6, 20) + zylinder_mm3(11, 6.8) - zylinder_mm3(6.6, 6.8))
        b["fase_je_loch"] = math.pi * c * (5.5 * c + c * c / 3)
        b["soll_mit_fase"] = b["soll_ohne_fase"] - 4 * b["fase_je_loch"]
        b["zylinder_muster"] = _zylinder(ctx.ergebnis("f4").features[0])
        return b


def spike_b() -> dict:
    """Gewinde M8 Tiefe 15 / Gewinde 12, Fase 0,6 am Kernloch (Ansenkung auf Ø 8), Muster ×4."""
    gewinde = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8",
               "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[-40, 0]], "tiefe": 15, "gewindetiefe": 12}
    fase = {"id": "f3", "typ": "fase", "kanten": [{"nahe": [-40 + 3.4, 20, 0]}], "abstand": 0.6}
    muster = {"id": "f4", "typ": "muster_linear", "features": ["f2", "f3"],
              "richtung1": {"achse": "x", "abstand": 20, "anzahl": 4}}
    with gebautes_teil(_spec(gewinde, fase, muster)) as (ctx, fehler, _):
        b = _bericht(ctx, fehler, ["f2", "f3", "f4"])
        b["fase_je_loch"] = math.pi * 0.6 * (3.4 * 0.6 + 0.36 / 3)
        b["zylinder_muster"] = _zylinder(ctx.ergebnis("f4").features[0])
        b["kosmetisch"] = [f.Name for f in _alle_features(ctx.model) if "Gewinde" in f.Name or "Thread" in f.GetTypeName2]
        return b


def _alle_features(model):
    f = model.FirstFeature
    while f is not None:
        yield f
        sub = f.GetFirstSubFeature
        while sub is not None:
            yield sub
            sub = sub.GetNextSubFeature
        f = f.GetNextFeature


def spike_c() -> dict:
    """Tasche 30 × 20 × 8 bei u −25, Verrundung R 3 der senkrechten Kanten, Spiegeln von Tasche und Verrundung."""
    tasche = {"id": "t1", "typ": "schnitt", "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
              "elemente": [{"rechteck": {"mitte": [-25, 0], "breite": 30, "hoehe": 20}}]},
              "ende": {"typ": "blind", "tiefe": 8}}
    rund = {"id": "r1", "typ": "verrundung", "kanten": [{"feature": "t1", "auswahl": "senkrechte_kanten"}], "radius": 3}
    ergebnisse = {}
    for name, ebene in (("rechts", "rechts"), ("versatz", {"versatz": {"ebene": "rechts", "abstand": -5}})):
        spiegel = {"id": "s1", "typ": "spiegeln", "features": ["t1", "r1"], "ebene": ebene}
        with gebautes_teil(_spec(tasche, rund, spiegel)) as (ctx, fehler, _):
            b = _bericht(ctx, fehler, ["t1", "r1", "s1"])
            b["soll"] = VOLL - 2 * (600 - (4 - math.pi) * 9) * 8
            b["kopie_box_x"] = sorted({round(f.punkt[0], 3) for f in flaechen(ctx.ergebnis("s1").features[0])
                                       if f.art == "ebene" and abs(abs(f.normale[0]) - 1) < 1e-6})
            ergebnisse[name] = b
    return ergebnisse


def spike_d() -> dict:
    """Kreismuster: Schrittweite (360° und 90°, 4 Instanzen) und Drehsinn um +y und +z."""
    aus = {}
    faelle = {
        "y": ({"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 100}}]},
               "ende": {"typ": "blind", "tiefe": 10}}, [30, 0]),          # oben: Loch bei X 30, Z 0
        "z": ({"id": "f1", "typ": "extrusion", "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 100}}]},
               "ende": {"typ": "blind", "tiefe": 10}}, [30, 0]),          # vorne: Loch bei X 30, Y 0
    }
    flaeche = {"y": "+y", "z": "+z"}
    for achse, (scheibe, pos) in faelle.items():
        for winkel in (360, 90):
            loch = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": flaeche[achse]},
                    "positionen": [pos], "durchmesser": 8, "durch": True}
            muster = {"id": "f3", "typ": "muster_kreis", "features": ["f2"], "achse": achse, "anzahl": 4, "winkel": winkel}
            spec = {"art": "teil", "name": "S20d", "features": [scheibe, loch, muster]}
            with gebautes_teil(spec) as (ctx, fehler, _):
                pkt = _zylinder(ctx.ergebnis("f3").features[0])
                if achse == "y":
                    w = sorted(round(math.degrees(math.atan2(-z, x)), 2) for x, _, z, _ in pkt)  # Drehung um +y: X→−Z
                else:
                    w = sorted(round(math.degrees(math.atan2(y, x)), 2) for x, y, _, _ in pkt)   # Drehung um +z: X→+Y
                aus[f"{achse}_{winkel}"] = {"fehler": None if fehler is None else repr(fehler), "winkel_rechtsdrehend": w,
                                            "def": definition(ctx.ergebnis("f3").features[0]),
                                            "achse_richtung": list(ctx.achsen[achse][1])}
    return aus


def _skizze_auf(model, ebene: str):
    sw.auswahl_leeren(model)
    sw.waehle(model, sw.standardebenen(model)[STANDARD[ebene]], 0)
    model.SketchManager.InsertSketch(True)
    return model.SketchManager


def _skizze_zu(model):
    model.SketchManager.InsertSketch(True)
    return sw.letztes_feature(model)


def spike_e() -> dict:
    """Sweep Kreis Ø 8 (rechts, Ursprung) entlang Linie 40 – Viertelbogen R 20 – Linie 30 (oben), Aufsatz und Schnitt."""
    aus = {}
    m = 0.001
    laenge = 40 + 10 * math.pi + 30
    for art in ("aufsatz", "schnitt"):
        block = {"id": "f1", "typ": "extrusion",
                 "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [30, 25], "breite": 80, "hoehe": 70}}]},
                 "ende": {"typ": "mittig", "tiefe": 20}}
        spec = {"art": "teil", "name": "S20e", "features": [block] if art == "schnitt" else []}
        with gebautes_teil(spec) as (ctx, fehler, _):
            model = ctx.model
            v0 = volumen_mm3(model) if art == "schnitt" else 0.0
            sm = _skizze_auf(model, "rechts")
            sm.CreateCircleByRadius(0.0, 0.0, 0.0, 4 * m)
            profil = _skizze_zu(model)
            sm = _skizze_auf(model, "oben")
            sm.CreateLine(0.0, 0.0, 0.0, 40 * m, 0.0, 0.0)
            sm.CreateArc(40 * m, 20 * m, 0.0, 40 * m, 0.0, 0.0, 60 * m, 20 * m, 0.0, 1)
            sm.CreateLine(60 * m, 20 * m, 0.0, 60 * m, 50 * m, 0.0)
            pfad = _skizze_zu(model)
            sw.auswahl_leeren(model)
            profil.Select2(False, 1)
            pfad.Select2(True, 4)
            fm = model.FeatureManager
            if art == "aufsatz":
                f = fm.InsertProtrusionSwept4(False, False, 0, False, False, 0, 0, False, 0.0, 0.0, 0, 0, True, True, True,
                                              0.0, True, False, 0.0, 0)
            else:
                f = fm.InsertCutSwept5(False, False, 0, False, False, 0, 0, False, 0.0, 0.0, 0, 0, True, True, 0.0, True,
                                       False, False, False, False, 0.0, 0)
            sw.rebuild(model)
            v = volumen_mm3(model)
            aus[art] = {"feature": None if f is None else (f.Name, f.GetTypeName2), "rebuild": rebuild_fehler(model),
                        "volumen_aenderung": round(abs(v - v0), 4), "soll": round(math.pi * 16 * laenge, 4),
                        "box": [round(x, 3) for x in sw.huellquader_eng_mm(model)]}
    return aus


SPIKES = {"a": spike_a, "b": spike_b, "c": spike_c, "d": spike_d, "e": spike_e}

if __name__ == "__main__":
    wahl = sys.argv[1:] or list(SPIKES)
    ergebnis = {}
    for k in wahl:
        try:
            ergebnis[k] = SPIKES[k]()
        except Exception as e:  # Spike: weiter mit dem nächsten
            ergebnis[k] = {"abbruch": repr(e)}
        print(json.dumps({k: ergebnis[k]}, ensure_ascii=False, default=str), flush=True)
