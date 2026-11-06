"""Handler "verrundung" und "fase" auf Kanten (Spike S9b, Bausteine 12 und 13) und die Fase am Bohrungseintritt (Feld
`fase` an bohrung/normbohrung, Paket Konstruktionsstil, Spike S20).

Beide setzen sich über tangentiale Kanten fort (eine Kante eines verrundeten Umrisses reicht).
"""

from swki.compiler import sw
from swki.compiler.anker import Vektor, differenz, laenge
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.topologie import kanten_roh, loese_kanten
from swki.spec.bohrungsfase import fase_abstand
from swki.verbindung import in_mm

SW_FM_FILLET = 1  # swFeatureNameID_e
SW_CONST_RADIUS_FILLET = 0  # swSimpleFilletType_e
SW_CHAMFER_ANGLE_DISTANCE = 1  # swChamferType_e
SW_CHAMFER_TANGENT_PROPAGATION = 4  # swFeatureChamferOption_e


def _waehle_kanten(ctx, f: dict) -> None:
    kanten = [k for anker in f["kanten"] for k in loese_kanten(ctx, anker)]
    sw.auswahl_leeren(ctx.model)
    for k in kanten:
        sw.waehle(ctx.model, k.objekt, 1, anhaengen=True)


@handler("verrundung")
def verrundung(ctx, f: dict) -> FeatureErgebnis:
    fm = ctx.model.FeatureManager
    daten = fm.CreateDefinition(SW_FM_FILLET)
    daten.Initialize(SW_CONST_RADIUS_FILLET)
    daten.DefaultRadius = ctx.m(f["radius"])
    daten.ConicTypeForCrossSectionProfile = 0  # kreisförmig
    daten.OverflowType = 0
    daten.PropagateToTangentFaces = True
    _waehle_kanten(ctx, f)
    feature = fm.CreateFeature(daten)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"verrundung {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    ctx.mass(f"D1@{f['id']}", f["radius"], f"{ctx.pfad(f['id'])}.radius", "radius")
    return FeatureErgebnis([feature])


def _fase_feature(ctx, abstand_mm: float, winkel_grad: float, name: str):
    """Fase Abstand-Winkel auf die gewählten Kanten; leeres Feature ohne Fehlermeldung ist möglich (S9b) → Fehler."""
    feature = ctx.model.FeatureManager.InsertFeatureChamfer(
        SW_CHAMFER_TANGENT_PROPAGATION, SW_CHAMFER_ANGLE_DISTANCE, ctx.m(abstand_mm), ctx.rad(winkel_grad), 0, 0, 0, 0,
    )
    if feature is None or not feature.GetFaces:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"fase {name} nicht erzeugt", schritt="feature")
    feature.Name = name
    return feature


@handler("fase")
def fase(ctx, f: dict) -> FeatureErgebnis:
    _waehle_kanten(ctx, f)
    feature = _fase_feature(ctx, f["abstand"], f.get("winkel", 45), f["id"])
    pfad = ctx.pfad(f["id"])
    ctx.mass(f"D1@{f['id']}", f["abstand"], f"{pfad}.abstand", "abstand")
    if "winkel" in f:
        ctx.mass(f"D2@{f['id']}", f["winkel"], f"{pfad}.winkel", "winkel")  # D2 = Winkel (live belegt)
    return FeatureErgebnis([feature])


def eintrittskanten(kreise: list[tuple[Vektor, float, object]], punkte: list[Vektor], tol: float) -> list[object]:
    """Je Bohrungspunkt (auf der Eintrittsfläche) die Kreiskante mit Mitte am Punkt und größtem Radius – bei einer
    Senkung deren Rand. kreise: (Mitte in mm, Radius in mm, Kante)."""
    gewaehlt = []
    for p in punkte:
        treffer = [(r, k) for m, r, k in kreise if laenge(differenz(m, p)) <= tol]
        if not treffer:
            raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"keine Kreiskante am Bohrungseintritt {tuple(round(c, 3) for c in p)}",
                            schritt="auswahl")
        gewaehlt.append(max(treffer, key=lambda t: t[0])[1])
    return gewaehlt


def _kreiskanten(ctx, features: list) -> list[tuple[Vektor, float, object]]:
    kreise = []
    for feature in features:
        for kante in kanten_roh(ctx.app, feature):
            kurve = kante.GetCurve
            if kurve.IsCircle:
                c = kurve.CircleParams  # (cx, cy, cz, ax, ay, az, r) in m
                kreise.append(((in_mm(c[0]), in_mm(c[1]), in_mm(c[2])), in_mm(c[6]), kante))
    return kreise


def bohrungsfase(ctx, f: dict, features: list, punkte: list[Vektor]):
    """Feld `fase` einer Bohrung: Fase c × 45° an der Eintrittskante jeder Position als Feature `<id>_fase` (None ohne
    Feld). Maß D1 ins Maßprotokoll, außer bei `nenn` (aus der Normtabelle, kein Spec-Wert)."""
    c = fase_abstand(f, ctx.spec.get("parameter", {}))
    if c is None:
        return None
    sw.auswahl_leeren(ctx.model)
    for kante in eintrittskanten(_kreiskanten(ctx, features), punkte, ctx.tol_mm):
        sw.waehle(ctx.model, kante, 1, anhaengen=True)
    name = f"{f['id']}_fase"
    feature = _fase_feature(ctx, c, 45, name)
    if f["fase"] != "nenn":
        ctx.mass(f"D1@{name}", f["fase"], f"{ctx.pfad(f['id'])}.fase", "abstand")
    return feature
