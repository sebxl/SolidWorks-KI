"""Screenshots der Standardansichten (Spike S4/S9b): ShowNamedView2 + SaveAs3 als Kopie (.png)."""

from pathlib import Path

from swki.compiler import sw

ANSICHTEN = {"iso": 7, "vorne": 1, "oben": 5, "rechts": 4}  # swStandardViews_e


def screenshots(model, ordner: Path) -> dict[str, str]:
    # Nur als echter Methodenaufruf wird eingepasst; der reine Attributzugriff (S9b) zoomt nicht (Bild abgeschnitten).
    model._FlagAsMethod("ViewZoomtofit2")
    bilder = {}
    for name, ansicht in ANSICHTEN.items():
        model.ShowNamedView2("", ansicht)
        model.ViewZoomtofit2()
        pfad = ordner / f"{name}.png"
        sw.speichere(model, pfad, kopie=True)
        bilder[name] = str(pfad)
    return bilder
