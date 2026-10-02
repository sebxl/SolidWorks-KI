"""S11 (Stufe 3a): Bezugsgeometrie, Messung am Normteil-Bauweg, Werkstoffe.

Frage 1: Bezugsebene deckungsgleich zu "oben" (InsertRefPlane, swRefPlaneReferenceConstraint_Coincident = 4) und mit
         Abstand 12 mm (Distance = 8); Lage und Normale aus IRefPlane.Transform.ArrayData – ist die Normale die dritte
         Zeile (Elemente 6–8) und der Ursprung die Translation (Elemente 9–11, m)?
Frage 2: Bezugsachse aus vorne ∩ rechts (InsertAxis2), umbenannt und per FeatureByName wiedergefunden; GetTypeName2 von
         Achse und Ebene; GetRefAxisParams.
Frage 3: Bauweg ISO 4762 M8 x 30 (Rotation mit Mittellinie auf der Profilkante, Innensechskant als Schnitt): baut er
         voll bestimmt, und liefert flaeche_in_richtung die ebenen Flächen für k, l, s und t eindeutig?
Frage 4: Gibt es die Werkstoffe 1.1191, 1.7225, 1.4301, 1.0038, 1.3505 in den Materialdatenbanken?

Aufruf: .venv\\Scripts\\python.exe -m spikes.s11_normteile
"""

from pathlib import Path

from spikes._gemeinsam import lauf
from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.anker import AnkerFehler, flaeche_in_richtung
from swki.compiler.eigenschaften import finde_material, globale_variablen
from swki.compiler.fehler import fehler_dict
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.compiler.skizze import STANDARD
from swki.compiler.topologie import flaechen
from swki.konfig import lade_rechner
from swki.verbindung import in_mm, mm, verbinde

KOINZIDENT, ABSTAND = 4, 8  # swRefPlaneReferenceConstraints_e (swki api enum)
WERKSTOFFE = ["1.1191", "1.7225", "1.4301", "1.0038", "1.3505"]
W3 = "3**0.5"
M8X30 = {"d": 8, "dk": 13, "k": 8, "s": 6, "t": 4, "p": 1.25, "l": 30}
SCHRAUBE = [
    {"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[0, "=-l"], ["=d/2-p", "=-l"], ["=d/2", "=p-l"], ["=d/2", 0], ["=dk/2", 0],
                                ["=dk/2", "=k-k/10"], ["=dk/2-k/10", "=k"], [0, "=k"]]}},
        {"mittellinie": {"von": [0, "=-l-1"], "bis": [0, "=k+1"]}}]}},  # überragt das Profil an beiden Enden (siehe Bericht)
    {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": "=k"}}, "elemente": [
        {"polygon": {"punkte": [["=s/2", f"=-s/(2*{W3})"], ["=s/2", f"=s/(2*{W3})"], [0, f"=s/{W3}"],
                                ["=-s/2", f"=s/(2*{W3})"], ["=-s/2", f"=-s/(2*{W3})"], [0, f"=-s/{W3}"]]}}]},
     "ende": {"typ": "blind", "tiefe": "=t"}},
]


def _ebene(model, art: int, abstand_mm: float, name: str) -> dict:
    sw.auswahl_leeren(model)
    sw.waehle(model, sw.standardebenen(model)[STANDARD["oben"]], 0)
    f = model.FeatureManager.InsertRefPlane(art, mm(abstand_mm), 0, 0.0, 0, 0.0)
    if f is None:
        return {"erzeugt": False}
    f.Name = name
    t = list(f.GetSpecificFeature2.Transform.ArrayData)
    return {"erzeugt": True, "typ": f.GetTypeName2, "wiedergefunden": model.FeatureByName(name) is not None,
            "array": t, "zeile3": t[6:9], "spalte3": [t[2], t[5], t[8]], "ursprung_mm": [in_mm(v) for v in t[9:12]]}


def _achse(model) -> dict:
    ebenen = sw.standardebenen(model)
    sw.auswahl_leeren(model)
    sw.waehle(model, ebenen[STANDARD["vorne"]], 0)
    sw.waehle(model, ebenen[STANDARD["rechts"]], 0, anhaengen=True)
    if not model.InsertAxis2(True):
        return {"erzeugt": False}
    f = sw.letztes_feature(model)
    f.Name = "EINBAU_ACHSE"
    p = list(f.GetSpecificFeature2.GetRefAxisParams)
    return {"erzeugt": True, "typ": f.GetTypeName2, "wiedergefunden": model.FeatureByName("EINBAU_ACHSE") is not None,
            "punkte_mm": [in_mm(v) for v in p]}


def _flaeche(fs, richtung: str) -> dict:
    try:
        f = flaeche_in_richtung(fs, richtung)
        return {"punkt": f.punkt, "normale": f.normale}
    except AnkerFehler as e:
        return {"fehler": str(e)}


def pruefen() -> dict:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    d: dict = {}
    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        d["frage1_deckungsgleich"] = _ebene(model, KOINZIDENT, 0.0, "EINBAU_EBENE")
        d["frage1_abstand_12"] = _ebene(model, ABSTAND, 12.0, "EINBAU_EBENE_2")
        d["frage2_achse"] = _achse(model)
    finally:
        sw.schliesse(app, model)

    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        spec = {"art": "teil", "name": "S11", "parameter": M8X30, "features": SCHRAUBE}
        ctx = Kontext(app, model, spec, Path("s11.yaml"), 0.1)
        globale_variablen(model, M8X30)
        fehler = baue_features(ctx, Protokoll("s11", "s11.yaml", 0, r.sw_jahr), alle_handler(), lambda c: sw.rebuild(c.model))
        d["frage3_fehler"] = fehler_dict(fehler) if fehler else None
        if fehler is None:
            f1, f2 = flaechen(ctx.ergebnis("f1").features[0]), flaechen(ctx.ergebnis("f2").features[0])
            d["frage3_flaechen"] = {"f1+y": _flaeche(f1, "+y"), "f1-y": _flaeche(f1, "-y"), "f2+x": _flaeche(f2, "+x"),
                                    "f2-x": _flaeche(f2, "-x"), "f2+y": _flaeche(f2, "+y")}
            d["frage3_zylinder_f1"] = sorted({round(z.radius, 6) for z in f1 if z.art == "zylinder"})
            d["frage3_erwartet"] = {"k": 8, "l": 30, "s": 6, "t": 4, "zylinderradien": [4.0, 6.5]}
    finally:
        sw.schliesse(app, model)

    datenbanken = list(app.GetMaterialDatabases or ())
    d["frage4_werkstoffe"] = {}
    for w in WERKSTOFFE:
        try:
            d["frage4_werkstoffe"][w] = finde_material(datenbanken, w)[1]
        except Exception as e:  # MATERIAL_UNBEKANNT
            d["frage4_werkstoffe"][w] = f"FEHLT: {e}"
    return d


if __name__ == "__main__":
    lauf("s11_normteile", pruefen)
