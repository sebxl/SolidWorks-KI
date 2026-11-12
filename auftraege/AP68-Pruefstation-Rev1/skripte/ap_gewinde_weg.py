"""Punkt ap3 (Anschlussplatte): die beiden Gewinde M5 für den Kanalträger (Y 293,75 / 368,75, Z −160) aus der
Bohrungsassistent-Bohrung `gewinde` entfernen (Nutzer 06.11.2026: „die alten Gewinde in der Anschlussplatte werden
entfernt“). Lücke: Das Format kennt keinen Punkt, der einzelne Positionen einer fremden Bohrung löscht.

Ablauf: Positionsskizze `gewinde_positionen` bearbeiten, die beiden Skizzenpunkte über ihre Modelllage wählen und löschen
(mit ihnen die Maße D5–D8), Skizze schließen, Neuaufbau. Läuft nach Punkt ap1 (Platte 33 nach +X): die Positionsskizze
liegt dann auf der Vorderseite X −212. Nachweis: Anzahl der Skizzenpunkte sinkt um genau 2.
API (swki api methode): IModelDoc2.EditSketch(0), IModelDocExtension.SelectByID2(9), IModelDoc2.EditDelete(0),
ISketchManager.InsertSketch(1), ISketch.GetSketchPoints2(0), IFeature.GetSpecificFeature2(0).
"""

X_VORNE = -212.0                      # Plattenvorderseite nach ap1 (mm, Modell)
ZIELE = [(-160.0, -293.75), (-160.0, -368.75)]   # (Modell y = Maschine Z, Modell z = −Maschine Y)


def _punkte(skizze):
    return list(skizze.GetSketchPoints2 or ())


def bauen(ctx):
    model = ctx.model
    feat = model.FeatureByName("gewinde_positionen")
    if feat is None:
        raise RuntimeError("Positionsskizze gewinde_positionen nicht gefunden")
    vorher = len(_punkte(feat.GetSpecificFeature2))
    model.ClearSelection2(True)
    feat.Select2(False, 0)
    model.EditSketch()
    callout = ctx.callout_leer() if hasattr(ctx, "callout_leer") else None
    for i, (y, z) in enumerate(ZIELE):
        if not model.Extension.SelectByID2("", "SKETCHPOINT", X_VORNE / 1000, y / 1000, z / 1000, i > 0, 0, callout, 0):
            model.SketchManager.InsertSketch(True)
            raise RuntimeError(f"Skizzenpunkt bei y {y}, z {z} nicht wählbar")
    model.EditDelete()
    model.SketchManager.InsertSketch(True)
    model.ForceRebuild3(False)
    nachher = len(_punkte(model.FeatureByName("gewinde_positionen").GetSpecificFeature2))
    if nachher != vorher - 2:
        raise RuntimeError(f"Positionsskizze hat {nachher} statt {vorher - 2} Punkte")
    return model.FeatureByName("gewinde")
