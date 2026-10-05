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

ANSICHTEN = {"iso": 7, "vorne": 1, "oben": 5, "rechts": 4}  # swStandardViews_e
SW_TIFF_SCREEN_OR_PRINT_CAPTURE = 6  # swUserPreferenceIntegerValue_e; 0 = Screen capture, 1 = Print capture


def screenshots(app, model, ordner: Path) -> dict[str, str]:
    # Nur als echter Methodenaufruf wird eingepasst; der reine Attributzugriff (S9b) zoomt nicht (Bild abgeschnitten).
    model._FlagAsMethod("ViewZoomtofit2")
    # Screen capture statt Print capture erzwingen, sonst bei schmal-langen Ansichten rechts abgeschnitten
    # (siehe Moduldocstring); danach immer den vorgefundenen Wert wiederherstellen.
    with sw.einstellung_int(app, SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0):
        bilder = {}
        for name, ansicht in ANSICHTEN.items():
            model.ShowNamedView2("", ansicht)
            model.ViewZoomtofit2()
            pfad = ordner / f"{name}.png"
            sw.speichere(model, pfad, kopie=True)
            bilder[name] = str(pfad)
        return bilder


ANSICHT_DER_ACHSE = {0: "rechts", 1: "oben", 2: "vorne"}  # Blick entlang x, y bzw. z


def kopplungsbild(app, model, pfad: Path, achse, komponenten: list) -> str:
    """Bild entlang einer Radachse (Standardansicht der größten Achskomponente), gezoomt auf die gekoppelten Komponenten
    (Spec 4b §5.7, Spike S14b Zeile 12); sonst wie screenshots()."""
    model._FlagAsMethod("ViewZoomToSelection")
    with sw.einstellung_int(app, SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0):
        model.ShowNamedView2("", ANSICHTEN[ANSICHT_DER_ACHSE[max(range(3), key=lambda i: abs(achse[i]))]])
        sw.auswahl_leeren(model)
        for komp in komponenten:
            komp.Select4(True, model.SelectionManager.CreateSelectData, False)
        model.ViewZoomToSelection()
        sw.auswahl_leeren(model)
        sw.speichere(model, pfad, kopie=True)
    return str(pfad)


def iso_bild(app, model, pfad: Path) -> str:
    """Ein Iso-Bild der aktuellen Stellung (Bewegungsprüfung, Spec 4a §8.3); gleiche Einstellungen wie screenshots()."""
    model._FlagAsMethod("ViewZoomtofit2")
    with sw.einstellung_int(app, SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0):
        model.ShowNamedView2("", ANSICHTEN["iso"])
        model.ViewZoomtofit2()
        sw.speichere(model, pfad, kopie=True)
    return str(pfad)
