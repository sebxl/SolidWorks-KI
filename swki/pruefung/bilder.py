"""Screenshots der Standardansichten (Spike S4/S9b): ShowNamedView2 + SaveAs3 als Kopie (.png).

Fund 2026-09-29 (Task 4, Nachbesserung): "System Options > Export > TIF/PSD/JPG/PNG > Output as" muss auf
"Screen capture" stehen (swTiffScreenOrPrintCapture = 0). Steht sie auf "Print capture" (1, hier vorgefunden;
Papierformat Letter @ 300 dpi = 3300x2550 px, Seitenverhältnis 1,294), zoomt ViewZoomtofit2 zwar korrekt auf
das tatsächliche Grafikfenster (hier 1741x973 px, Seitenverhältnis 1,789), aber SaveAs3 rendert in das davon
abweichende Papier-Seitenverhältnis – bei schmal-langen Standardansichten (hier Vorne/Rechts eines flachen
Teils) mit sichtbarem Beschnitt rechts. Nur über ISldWorks lesbar/schreibbar (swki.verbindung.verbinde);
IModelDoc2.Get/SetUserPreferenceIntegerValue und IModelDocExtension.Get/SetUserPreferenceInteger liefern für
dieses System-Preference -1 bzw. False (live geprüft), weil es ein System Option ist, kein Document Property.
Deshalb während der Aufnahme auf "Screen capture" umschalten und danach den vorgefundenen Wert wiederherstellen
(siehe swki/wissen/pywin32-fallstricke.md).
"""

from pathlib import Path

from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.verbindung import verbinde

ANSICHTEN = {"iso": 7, "vorne": 1, "oben": 5, "rechts": 4}  # swStandardViews_e
SW_TIFF_SCREEN_OR_PRINT_CAPTURE = 6  # swUserPreferenceIntegerValue_e; 0 = Screen capture, 1 = Print capture


def screenshots(model, ordner: Path) -> dict[str, str]:
    # Nur als echter Methodenaufruf wird eingepasst; der reine Attributzugriff (S9b) zoomt nicht (Bild abgeschnitten).
    model._FlagAsMethod("ViewZoomtofit2")
    # Screen capture statt Print capture erzwingen, sonst bei schmal-langen Ansichten rechts abgeschnitten
    # (siehe Moduldocstring); danach immer den vorgefundenen Wert wiederherstellen.
    app = verbinde(lade_rechner().sw_jahr)
    vorher = app.GetUserPreferenceIntegerValue(SW_TIFF_SCREEN_OR_PRINT_CAPTURE)
    app.SetUserPreferenceIntegerValue(SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0)
    try:
        bilder = {}
        for name, ansicht in ANSICHTEN.items():
            model.ShowNamedView2("", ansicht)
            model.ViewZoomtofit2()
            pfad = ordner / f"{name}.png"
            sw.speichere(model, pfad, kopie=True)
            bilder[name] = str(pfad)
        return bilder
    finally:
        app.SetUserPreferenceIntegerValue(SW_TIFF_SCREEN_OR_PRINT_CAPTURE, vorher)
