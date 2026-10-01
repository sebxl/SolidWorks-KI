"""S10 Frage 4: Bohrungsassistent-Daten eines Features auslesen (für die Code-Prüfung normbohrungen).

Ein Teil mit fünf Normbohrungs-Features (je Art eines, Namen nb_<art>; dazu nb_stift_durch, per CreateDefinition
erzeugt), gespeichert im Arbeitsordner, geschlossen und mit OpenDoc6 wieder geöffnet (wie swki pruefen). Je Feature:
IFeature.GetDefinition → IWizardHoleFeatureData2 – Type, Standard2, FastenerType2, FastenerSize, EndCondition,
Depth/HoleDepth, ThreadDepth, GetSketchPointCount – einmal im gebauten und einmal im wieder geöffneten Teil;
"soll" nennt die Eingaben.
"""

import json

from spikes._gemeinsam import ERGEBNISSE, lauf
from spikes.s9a_gemeinsam import kasten_oben, start
from spikes.s10_gemeinsam import ARBEIT_S10, DICKE_MM, SW_BEFESTIGUNG, SW_WZD, bohrung, daten
from swki.compiler import sw
from swki.pruefung.messen import oeffne


def pruefen() -> dict:
    r, app = start()
    gewinner = json.loads((ERGEBNISSE / "s10_f1_bohrungsassistent.json").read_text(encoding="utf-8"))["gewinner"]
    eingaben = {
        "nb_gewinde": ("gewinde", gewinner["gewinde"]["M10"], [(-15.0, -15.0), (15.0, -15.0)],
                       {"tiefe_mm": 16, "gewindetiefe_mm": 12}),
        "nb_zylinderschraube": ("zylinderschraube", gewinner["zylinderschraube"]["M8"], [(-15.0, 15.0)], {}),
        "nb_senkschraube": ("senkschraube", gewinner["senkschraube"]["M6"], [(15.0, 15.0)], {}),
        "nb_stift": ("stift", gewinner["stift"]["8"], [(0.0, 0.0)], {"tiefe_mm": 20}),
        "nb_stift_durch": ("stift", gewinner["stift"]["8"], [(0.0, -25.0)], {}),  # CreateDefinition-Weg
    }
    pfad = ARBEIT_S10 / "s10_f4_auslesen.sldprt"
    d: dict = {"gebaut": {}, "geoeffnet": {}}
    d["soll"] = {
        name: {"Type": SW_WZD[art], "Standard2": 8, "FastenerType2": SW_BEFESTIGUNG[art], "FastenerSize": text,
               "EndCondition": 0 if "tiefe_mm" in kw else 1, "Depth_m": kw.get("tiefe_mm", 0) / 1000,
               "ThreadDepth_m": kw.get("gewindetiefe_mm", 0) / 1000, "GetSketchPointCount": len(pos)}
        for name, (art, text, pos, kw) in eingaben.items()
    }
    model = app.NewDocument(str(r.vorlage_teil), 0, 0, 0)
    try:
        kasten_oben(model, 60, 60, DICKE_MM)
        for name, (art, text, pos, kw) in eingaben.items():
            _, f = bohrung(model, art, text, pos, **kw)
            f.Name = name
            d["gebaut"][name] = daten(f)
        sw.speichere(model, pfad)
    finally:
        sw.schliesse(app, model)
    model = oeffne(app, pfad)
    try:
        for name in eingaben:
            f = model.FeatureByName(name)
            d["geoeffnet"][name] = {"typname": f.GetTypeName2, **daten(f)} if f is not None else "fehlt"
    finally:
        sw.schliesse(app, model)
    return d


if __name__ == "__main__":
    lauf("s10_f4_auslesen", pruefen)
