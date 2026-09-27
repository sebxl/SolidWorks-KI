"""Handler "verrundung" und "fase" auf Kanten (Spike S9b, Bausteine 12 und 13).

Beide setzen sich über tangentiale Kanten fort (eine Kante eines verrundeten Umrisses reicht).
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.topologie import loese_kanten

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
    ctx.verknuepfe(f"D1@{f['id']}", f["radius"])
    return FeatureErgebnis([feature])


@handler("fase")
def fase(ctx, f: dict) -> FeatureErgebnis:
    _waehle_kanten(ctx, f)
    feature = ctx.model.FeatureManager.InsertFeatureChamfer(
        SW_CHAMFER_TANGENT_PROPAGATION, SW_CHAMFER_ANGLE_DISTANCE, ctx.m(f["abstand"]),
        ctx.rad(f.get("winkel", 45)), 0, 0, 0, 0,
    )
    if feature is None or not feature.GetFaces:
        # Leeres Fase-Feature ohne Fehlermeldung ist möglich (S9b) → als Fehler behandeln
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"fase {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    ctx.verknuepfe(f"D1@{f['id']}", f["abstand"])
    return FeatureErgebnis([feature])
