"""Handler "rotation" – Aufsatz oder Schnitt um die Mittellinie der Skizze (Spike S9a, Baustein 8)."""

from swki.compiler import sw
from swki.compiler.anker import differenz, laenge
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import modellpunkt, skizziere


def rotiere(model, schnitt: bool, winkel_rad: float):
    return model.FeatureManager.FeatureRevolve2(
        True, True, False, schnitt, False, False, 0, 0, winkel_rad, 0.0,
        False, False, 0.0, 0.0, 0, 0.0, 0.0, True, True, True,
    )


@handler("rotation")
def rotation(ctx, f: dict) -> FeatureErgebnis:
    skizze, se = skizziere(ctx, f["skizze"]["ebene"], f["skizze"]["elemente"], f"{f['id']}_skizze")
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)  # die einzige Mittellinie der Skizze wird automatisch Achse
    feature = rotiere(ctx.model, bool(f.get("schnitt", False)), ctx.rad(f.get("winkel", 360)))
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"rotation {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    if "winkel" in f:
        ctx.verknuepfe(f"D1@{f['id']}", f["winkel"])
    linie = next(e["mittellinie"] for e in f["skizze"]["elemente"] if "mittellinie" in e)
    a = modellpunkt(se.orientierung, ctx.wert(linie["von"][0]), ctx.wert(linie["von"][1]), se.lage)
    b = modellpunkt(se.orientierung, ctx.wert(linie["bis"][0]), ctx.wert(linie["bis"][1]), se.lage)
    d = differenz(b, a)
    return FeatureErgebnis([feature], richtung=tuple(c / laenge(d) for c in d))
