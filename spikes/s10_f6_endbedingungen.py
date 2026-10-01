"""S10 Frage 6: FeatureCut4/FeatureExtrusion3 mit swEndCondUpToSurface (4) und swEndCondOffsetFromSurface (5).

Block 100 × 60 × 20 (Y 0…20). Skizzen mit skizziere() des Compilers, Zielfläche mit Select4 und Marke angehängt.
a) Schnitt Quadrat 20 × 20 von der Deckfläche bis zur Unterseite, Marke 1, 2 bzw. 32 (Hilfe FeatureExtrusion3:
   „End condition reference entity – 1“); Soll-Abnahme 8000 mm³.
b) Schnitt versatz 5 mm von der Unterseite, OffsetReverse1 False bzw. True; Soll (False = zur Skizze hin): Restwand 5
   → 6000 mm³; Maße des Features (Name des Versatzmaßes).
c) Aufsatz Kreis Ø10 von einer Ebene 40 über oben (umgekehrt) bis zur Deckfläche; Soll +π·25·20 = 1570,796 mm³.
d) Aufsatz wie c) mit Versatz 5 von der Deckfläche, OffsetReverse1 False/True: welche Seite, wie viele Körper?
"""

import math
import traceback

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import feature_masse, flaeche_mit_normale, kasten_oben, start, teil, volumen_mm3
from spikes.s9b_gemeinsam import whatswrong
from spikes.s10_gemeinsam import kontext
from swki.compiler import sw
from swki.compiler.skizze import ebene_aufloesen, ebene_aus_flaeche, skizziere
from swki.compiler.topologie import flaeche_aus

BIS_FLAECHE, VERSATZ = 4, 5  # swEndConditions_e


def _schnitt(model, typ: int, d1_m: float, versatz_weg: bool):
    return model.FeatureManager.FeatureCut4(
        True, False, False, typ, 0, d1_m, 0.0, False, False, False, False, 0.0, 0.0,
        versatz_weg, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False,
    )


def _aufsatz(model, typ: int, d1_m: float, versatz_weg: bool, umkehren: bool):
    return model.FeatureManager.FeatureExtrusion3(
        True, False, umkehren, typ, 0, d1_m, 0.0, False, False, False, False, 0.0, 0.0,
        versatz_weg, False, False, False, True, True, True, 0, 0.0, False,
    )


def fall_schnitt(app, r, typ: int, marke: int, d1_mm: float = 0.0, versatz_weg: bool = False) -> dict:
    with teil(app, r) as model:
        kasten = kasten_oben(model, 100, 60, 20)
        ctx = kontext(app, model)
        oben = ebene_aus_flaeche(flaeche_aus(flaeche_mit_normale(kasten, (0.0, 1.0, 0.0))))
        unten = flaeche_mit_normale(kasten, (0.0, -1.0, 0.0))
        skizze, _ = skizziere(ctx, oben, [{"rechteck": {"mitte": [0, 0], "breite": 20, "hoehe": 20}}], "s_skizze")
        v0 = volumen_mm3(model)
        sw.auswahl_leeren(model)
        skizze.Select2(False, 0)
        sw.waehle(model, unten, marke, anhaengen=True)
        f = _schnitt(model, typ, d1_mm / 1000, versatz_weg)
        return {"feature": f is not None, "abnahme_mm3": round(v0 - volumen_mm3(model), 3),
                "masse": feature_masse(f) if f else None, "whatswrong": whatswrong(model)}


def fall_aufsatz(app, r, typ: int, marke: int, d1_mm: float = 0.0, versatz_weg: bool = False) -> dict:
    with teil(app, r) as model:
        kasten = kasten_oben(model, 100, 60, 20)
        ctx = kontext(app, model)
        deck = flaeche_mit_normale(kasten, (0.0, 1.0, 0.0))
        ebene = ebene_aufloesen(ctx, {"versatz": {"ebene": "oben", "abstand": 40}})
        skizze, _ = skizziere(ctx, ebene, [{"kreis": {"mitte": [0, 0], "durchmesser": 10}}], "z_skizze")
        v0 = volumen_mm3(model)
        sw.auswahl_leeren(model)
        skizze.Select2(False, 0)
        sw.waehle(model, deck, marke, anhaengen=True)
        f = _aufsatz(model, typ, d1_mm / 1000, versatz_weg, True)
        return {"feature": f is not None, "zunahme_mm3": round(volumen_mm3(model) - v0, 3),
                "box": [round(c * 1000, 4) for c in model.GetPartBox(True)],
                "koerper": len(model.GetBodies2(0, False) or ()),
                "masse": feature_masse(f) if f else None, "whatswrong": whatswrong(model)}


def _sicher(d: dict, name: str, fn, *args, **kw) -> None:
    """Fall ausführen; ein Fehler (mit Aufrufkette) verliert die Befunde der anderen Fälle nicht (kein Wiederholen)."""
    try:
        d[name] = fn(*args, **kw)
    except Exception as e:
        d[name] = {"fehler_fall": repr(e), "aufrufkette": traceback.format_exc()}


def pruefen() -> dict:
    r, app = start()
    d: dict = {"soll": {"a_mm3": 8000, "b_false_mm3": 6000, "c_mm3": round(math.pi * 25 * 20, 3)}}
    for marke in (1, 2, 32):
        _sicher(d, f"a_schnitt_bis_flaeche_marke_{marke}", fall_schnitt, app, r, BIS_FLAECHE, marke)
    for weg in (False, True):
        _sicher(d, f"b_schnitt_versatz_5_offsetreverse_{weg}", fall_schnitt, app, r, VERSATZ, 1, 5.0, weg)
        _sicher(d, f"d_aufsatz_versatz_5_offsetreverse_{weg}", fall_aufsatz, app, r, VERSATZ, 1, 5.0, weg)
    _sicher(d, "c_aufsatz_bis_flaeche_marke_1", fall_aufsatz, app, r, BIS_FLAECHE, 1)
    return d


if __name__ == "__main__":
    lauf("s10_f6_endbedingungen", pruefen)
