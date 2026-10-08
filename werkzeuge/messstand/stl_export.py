"""Teil oder Baugruppe als STL exportieren (für den Vergleich mit der Referenz). Einstellungen werden temporär gesetzt
und danach zurückgesetzt: binär, nicht in den positiven Raum verschieben, Baugruppe in eine Datei, Qualität fein, mm.
API nachgeschlagen (swki api enum): swUserPreferenceToggle_e 69/71/72, swUserPreferenceIntegerValue_e 78 (swSTLQuality,
swSTLQuality_e Fine = 2), 211 (swExportStlUnits, swLengthUnit_e swMM = 0)."""

from pathlib import Path

from swki.compiler.sw import schliesse, speichere
from swki.konfig import lade_rechner
from swki.pruefung.messen import oeffne
from swki.verbindung import verbinde

TOGGLES = {69: True, 71: True, 72: True}   # binär, nicht verschieben, Komponenten in eine Datei
INTEGER = {78: 2, 211: 0}                  # Qualität fein, Einheit mm


def exportiere(modell: Path, ziel: Path) -> Path:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    alt_t = {k: app.GetUserPreferenceToggle(k) for k in TOGGLES}
    alt_i = {k: app.GetUserPreferenceIntegerValue(k) for k in INTEGER}
    model = None
    try:
        for k, v in TOGGLES.items():
            app.SetUserPreferenceToggle(k, v)
        for k, v in INTEGER.items():
            app.SetUserPreferenceIntegerValue(k, v)
        model = oeffne(app, Path(modell))
        speichere(model, Path(ziel), kopie=True)
    finally:
        if model is not None:
            schliesse(app, model)
        for k, v in alt_t.items():
            app.SetUserPreferenceToggle(k, bool(v))
        for k, v in alt_i.items():
            app.SetUserPreferenceIntegerValue(k, v)
    if not Path(ziel).exists():
        raise RuntimeError(f"STL {ziel} wurde nicht geschrieben")
    return Path(ziel)
