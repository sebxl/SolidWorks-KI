"""Gewindebohrungen M8 über den Bohrungsassistenten.

Notausgang: Gewinde bildet das Spezifikationsformat in Stufe 2 noch nicht ab. Aufrufkette aus Spike S9b (Baustein 21).
"""

SW_WZD_TAP = 4  # swWzdGeneralHoleTypes_e
SW_STANDARD_ISO = 8  # swWzdHoleStandards_e
SW_ISO_TAPPED_HOLE = 147  # swWzdHoleStandardFastenerTypes_e
SW_SEL_FACES = 2  # swSelectType_e
POSITIONEN = [(-100, 0), (100, 0)]  # (u, v) auf der Deckfläche wie in der Spezifikation


def bauen(ctx):
    deckflaeche = ctx.ebene({"feature": "f1", "flaeche": "+y"})
    features = []
    for u, v in POSITIONEN:
        x, y, z = ctx.modellpunkt_m(deckflaeche, u, v)
        ctx.auswahl_leeren()
        ctx.model.Extension.SelectByRay(x, y + 0.01, z, 0.0, -1.0, 0.0, 0.0005, SW_SEL_FACES, False, 0, 0)
        features.append(ctx.model.FeatureManager.HoleWizard5(
            SW_WZD_TAP, SW_STANDARD_ISO, SW_ISO_TAPPED_HOLE, "M8", 0, -1, 0.016, -1,  # blind 16, Durchmesser -1 = Norm
            0.012, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1,  # Gewindetiefe 12, kosmetisches Gewinde
            "", False, False, True, False, True, False,
        ))
        ctx.punkte_festlegen(features[-1], {"feature": "f1", "flaeche": "+y"}, [(u, v)])  # Lage voll bestimmen
    return features
