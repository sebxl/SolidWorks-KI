"""STL des geöffneten Modells für den Geometrie-Steckbrief (Messstand Umbau 1). Einstellungen nur temporär: binär,
nicht in den positiven Raum verschieben, Baugruppe in eine Datei, Qualität fein, mm.
API (swki api enum): swUserPreferenceToggle_e 69 swSTLBinaryFormat, 71 swSTLDontTranslateToPositive,
72 swSTLComponentsIntoOneFile; swUserPreferenceIntegerValue_e 78 swSTLQuality (swSTLQuality_e Fine = 2),
211 swExportStlUnits (swLengthUnit_e swMM = 0)."""

from pathlib import Path

from swki.compiler import sw

TOGGLES = {69: True, 71: True, 72: True}
INTEGER = {78: 2, 211: 0}


def exportiere_stl(app, model, ziel: Path) -> Path:
    alt_t = {k: app.GetUserPreferenceToggle(k) for k in TOGGLES}
    alt_i = {k: app.GetUserPreferenceIntegerValue(k) for k in INTEGER}
    try:
        for k, v in TOGGLES.items():
            app.SetUserPreferenceToggle(k, v)
        for k, v in INTEGER.items():
            app.SetUserPreferenceIntegerValue(k, v)
        sw.speichere(model, Path(ziel), kopie=True)
    finally:
        for k, v in alt_t.items():
            app.SetUserPreferenceToggle(k, bool(v))
        for k, v in alt_i.items():
            app.SetUserPreferenceIntegerValue(k, v)
    return Path(ziel)
