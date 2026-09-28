"""Handler "muster_linear", "muster_kreis" und "spiegeln" (Spike S9b, Bausteine 14–16).

Richtungen und Drehachsen sind Referenzachsen aus zwei Standardebenen (x = vorne∩oben, y = vorne∩rechts,
z = oben∩rechts); sie werden je Teil einmal angelegt ("achse_x" …). Die Musterrichtung folgt der Richtung
der Achse; zeigt sie gegen die Sollrichtung, wird umgekehrt.
"""

from swki.compiler import sw
from swki.compiler.anker import ACHSEN, differenz, laenge, skalar
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import STANDARD, ebene_aufloesen
from swki.verbindung import in_mm

SW_FM_CIRPATTERN = 5  # swFeatureNameID_e
SW_FM_LPATTERN = 6
_EBENEN_DER_ACHSE = {"x": ("vorne", "oben"), "y": ("vorne", "rechts"), "z": ("oben", "rechts")}


def referenzachse(ctx, achse: str):
    """Referenzachse (IFeature) und ihre Richtung als Einheitsvektor; je Teil nur einmal angelegt."""
    if achse in ctx.achsen:
        return ctx.achsen[achse]
    ebenen = sw.standardebenen(ctx.model)
    a, b = _EBENEN_DER_ACHSE[achse]
    sw.auswahl_leeren(ctx.model)
    sw.waehle(ctx.model, ebenen[STANDARD[a]], 0)
    sw.waehle(ctx.model, ebenen[STANDARD[b]], 0, anhaengen=True)
    if not ctx.model.InsertAxis2(True):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Referenzachse {achse} nicht erzeugt", schritt="achse")
    feature = sw.letztes_feature(ctx.model)
    feature.Name = f"achse_{achse}"
    sw.auswahl_leeren(ctx.model)
    feature.Select2(False, 0)
    ctx.model._FlagAsMethod("BlankRefGeom")
    ctx.model.BlankRefGeom()  # ausblenden, damit die Achse nicht in den Screenshots erscheint
    sw.auswahl_leeren(ctx.model)
    p = feature.GetSpecificFeature2.GetRefAxisParams  # (x1, y1, z1, x2, y2, z2) in m
    d = differenz(tuple(in_mm(v) for v in p[3:6]), tuple(in_mm(v) for v in p[0:3]))
    ctx.achsen[achse] = (feature, tuple(c / laenge(d) for c in d))
    return ctx.achsen[achse]


def _sw_features(ctx, ids: list[str]) -> list:
    return [feature for fid in ids for feature in ctx.ergebnis(fid).features]


def _umkehren(ctx, richtung: dict) -> bool:
    _, d = referenzachse(ctx, richtung["achse"])
    soll = skalar(d, ACHSEN[richtung["achse"]])
    return (soll < 0) != bool(richtung.get("umkehren", False))


@handler("muster_linear")
def muster_linear(ctx, f: dict) -> FeatureErgebnis:
    r1, r2 = f["richtung1"], f.get("richtung2")
    umkehren1 = _umkehren(ctx, r1)
    umkehren2 = _umkehren(ctx, r2) if r2 else False
    sw.auswahl_leeren(ctx.model)
    sw.waehle(ctx.model, referenzachse(ctx, r1["achse"])[0], 1)
    if r2:
        sw.waehle(ctx.model, referenzachse(ctx, r2["achse"])[0], 2, anhaengen=True)
    for feature in _sw_features(ctx, f["features"]):
        sw.waehle(ctx.model, feature, 4, anhaengen=True)
    fm = ctx.model.FeatureManager
    daten = fm.CreateDefinition(SW_FM_LPATTERN)  # liest die Vorselektion bei CreateFeature
    daten.D1TotalInstances = r1["anzahl"]
    daten.D1Spacing = ctx.m(r1["abstand"])
    daten.D1ReverseDirection = umkehren1
    if r2:
        daten.D2TotalInstances = r2["anzahl"]
        daten.D2Spacing = ctx.m(r2["abstand"])
        daten.D2ReverseDirection = umkehren2
    feature = fm.CreateFeature(daten)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"muster_linear {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    # Maße des Musters (live belegt): D1/D2 Anzahl, D3/D4 Abstand Richtung 1/2
    ctx.verknuepfe(f"D3@{f['id']}", r1["abstand"])
    if r2:
        ctx.verknuepfe(f"D4@{f['id']}", r2["abstand"])
    return FeatureErgebnis([feature])


@handler("muster_kreis")
def muster_kreis(ctx, f: dict) -> FeatureErgebnis:
    achse, richtung = referenzachse(ctx, f["achse"])
    sw.auswahl_leeren(ctx.model)
    sw.waehle(ctx.model, achse, 1)
    for feature in _sw_features(ctx, f["features"]):
        sw.waehle(ctx.model, feature, 4, anhaengen=True)
    fm = ctx.model.FeatureManager
    daten = fm.CreateDefinition(SW_FM_CIRPATTERN)
    daten.TotalInstances = f["anzahl"]
    daten.EqualSpacing = True  # zuerst: setzt Spacing auf 2π zurück (S9b)
    daten.Spacing = ctx.rad(f.get("winkel", 360))  # bei EqualSpacing = Gesamtwinkel
    feature = fm.CreateFeature(daten)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"muster_kreis {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    if "winkel" in f:
        ctx.verknuepfe(f"D3@{f['id']}", f["winkel"])  # D1 Anzahl, D3 Gesamtwinkel (live belegt)
    return FeatureErgebnis([feature], richtung=richtung)


@handler("spiegeln")
def spiegeln(ctx, f: dict) -> FeatureErgebnis:
    ebene = ebene_aufloesen(ctx, f["ebene"])
    sw.auswahl_leeren(ctx.model)
    for feature in _sw_features(ctx, f["features"]):
        sw.waehle(ctx.model, feature, 1, anhaengen=True)
    sw.waehle(ctx.model, ebene.objekt, 2, anhaengen=True)
    feature = ctx.model.FeatureManager.InsertMirrorFeature2(False, False, False, False, 0)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"spiegeln {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    return FeatureErgebnis([feature])
