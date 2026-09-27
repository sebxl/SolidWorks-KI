"""Handler "extrusion" (Aufsatz) und "schnitt" (verifiziert in Spike S9a, Bausteine 6 und 7).

Aufsatz wächst standardmäßig in Richtung der Skizzennormale, Schnitt standardmäßig dagegen
(von einer Deckfläche also ins Material). "umkehren" dreht die Richtung (3. Parameter Dir, nicht Flip).
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import richtung, skizziere

ENDE = {"blind": 0, "durch_alles": 1, "mittig": 6}  # swEndConditions_e


def aufsatz(model, typ: int, tiefe_m: float, umkehren: bool):
    return model.FeatureManager.FeatureExtrusion3(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, False, False, False, False, 0.0, 0.0,
        False, False, False, False, True, True, True, 0, 0.0, False,
    )


def schnitt(model, typ: int, tiefe_m: float, umkehren: bool):
    return model.FeatureManager.FeatureCut4(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, False, False, False, False, 0.0, 0.0,
        False, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False,
    )


@handler("extrusion", "schnitt")
def extrusion(ctx, f: dict) -> FeatureErgebnis:
    skizze, se = skizziere(ctx, f["skizze"]["ebene"], f["skizze"]["elemente"], f"{f['id']}_skizze")
    ende = f["ende"]
    typ = ENDE[ende["typ"]]
    tiefe = ctx.m(ende["tiefe"]) if "tiefe" in ende else 0.0
    umkehren = bool(ende.get("umkehren", False))
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)
    ist_schnitt = f["typ"] == "schnitt"
    feature = (schnitt if ist_schnitt else aufsatz)(ctx.model, typ, tiefe, umkehren)
    if feature is None:
        grund = " (trifft der Schnitt Material? ggf. umkehren)" if ist_schnitt else ""
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{f['typ']} {f['id']} nicht erzeugt{grund}", schritt="feature")
    feature.Name = f["id"]
    if "tiefe" in ende:
        ctx.verknuepfe(f"D1@{f['id']}", ende["tiefe"])
    return FeatureErgebnis([feature], richtung=richtung(se, umkehren != ist_schnitt))
