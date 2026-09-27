"""Handler "bohrung" – zylindrische Bohrungen (durch oder blind) mit optionaler Flachsenkung (Spike S9a, Baustein 9).

Jede Position ist eine Instanz (1, 2, …) in Spezifikationsreihenfolge. Die Achspunkte werden aus der Skizze
berechnet (nicht aus der Flächenreihenfolge, die SolidWorks nicht stabil liefert).
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.handler.extrusion import ENDE, schnitt
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import ebene_aus_flaeche, modellpunkt, richtung, skizziere
from swki.compiler.topologie import loese_flaeche


def _kreisschnitt(ctx, f: dict, durchmesser, tiefe, name: str):
    se = ebene_aus_flaeche(loese_flaeche(ctx, f["flaeche"]))
    kreise = [{"kreis": {"mitte": p, "durchmesser": durchmesser}} for p in f["positionen"]]
    skizze, se = skizziere(ctx, se, kreise, f"{name}_skizze")
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)
    typ = ENDE["durch_alles"] if tiefe is None else ENDE["blind"]
    feature = schnitt(ctx.model, typ, 0.0 if tiefe is None else ctx.m(tiefe), False)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"bohrung {name} nicht erzeugt", schritt="feature")
    feature.Name = name
    if tiefe is not None:
        ctx.verknuepfe(f"D1@{name}", tiefe)
    return feature, se


@handler("bohrung")
def bohrung(ctx, f: dict) -> FeatureErgebnis:
    features = []
    feature, se = _kreisschnitt(ctx, f, f["durchmesser"], None if f.get("durch") else f["tiefe"], f["id"])
    features.append(feature)
    if "senkung" in f:
        s = f["senkung"]
        senkung, _ = _kreisschnitt(ctx, f, s["durchmesser"], s["tiefe"], f"{f['id']}_senkung")
        features.append(senkung)
    punkte = [modellpunkt(se.orientierung, ctx.wert(u), ctx.wert(v), se.lage) for u, v in f["positionen"]]
    return FeatureErgebnis(features, richtung=richtung(se, True), punkte=punkte)
