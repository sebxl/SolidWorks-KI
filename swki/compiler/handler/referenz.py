"""Handler "referenz" – benannte Bezugsachse oder -ebene, z. B. die Einbaureferenzen der Normteile (Spec 3a §5,
Spike S11). Achse: Schnitt zweier Standardebenen (wie die Musterachsen); Ebene: deckungsgleich zu einer Standardebene
oder mit Abstand. Beide werden ausgeblendet; der SW-Featurename ist die ID."""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.handler.muster import neue_referenzachse
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import NORMALE, REF_PLANE_ABSTAND, REF_PLANE_UMKEHREN, STANDARD

REF_PLANE_DECKUNGSGLEICH = 4  # swRefPlaneReferenceConstraint_Coincident (swki api enum)


def _ebene(ctx, f: dict):
    e = f["ebene"]
    sw.auswahl_leeren(ctx.model)
    sw.waehle(ctx.model, sw.standardebenen(ctx.model)[STANDARD[e["basis"]]], 0)
    if "abstand" in e:
        art = REF_PLANE_ABSTAND | (REF_PLANE_UMKEHREN if e.get("umkehren") else 0)
        feature = ctx.model.FeatureManager.InsertRefPlane(art, ctx.m(e["abstand"]), 0, 0.0, 0, 0.0)
    else:
        feature = ctx.model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0, 0, 0.0)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"referenz {f['id']}: Ebene nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    if "abstand" in e:
        ctx.verknuepfe(f"D1@{f['id']}", e["abstand"])
    # Der Flip verschiebt nur die Lage auf die andere Seite, die Normale bleibt (wie in skizze.py, live belegt).
    return feature, NORMALE[e["basis"]]


@handler("referenz")
def referenz(ctx, f: dict) -> FeatureErgebnis:
    if "achse" in f:
        feature, richtung = neue_referenzachse(ctx, f["achse"])
        feature.Name = f["id"]
    else:
        feature, richtung = _ebene(ctx, f)
        sw.ausblenden(ctx.model, feature)
    return FeatureErgebnis([feature], richtung=richtung)
