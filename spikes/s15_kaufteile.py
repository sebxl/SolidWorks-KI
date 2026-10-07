"""S15 (Stufe 3c): STEP-Import nicht genormter Kaufteile – Testdaten, Import, Diagnose, Bezugsgeometrie, Masse,
Baugruppe, Zeit und Speicher, Bilder (Spec 3c §12). Kein Produktionscode; die Aufrufe sind im API-Index nachgeschlagen.

e Testdaten: Muster-Baugruppe tests/referenz/motorhalter/muster/gm42.yaml in einer Kopie validieren, freigeben, bauen;
  zweimal per SaveAs3 als STEP exportieren und vergleichen; erste Datei → muster/gm42-10.step (wird committet; eine
  vorhandene Datei bleibt unangetastet, überschrieben wird sie nur mit --step-neu).
a Import: GetImportFileData + LoadFile4 (4 Parameter), 3D Interconnect aus, Strukturabbildung Mehrkörperteil (2),
  keine automatische Importdiagnose; Optionen vorher/während/nachher; Rückfall OpenDoc6.
b Diagnose: Körper, IBody2.Check3, Flächenkörper, Features (Typ, Is3DInterconnectFeature), GetPartBox, Volumen, Zeit je
  Fläche (flaeche_aus).
c Bezugsgeometrie: Achse aus der Wellen-Zylinderfläche (InsertAxis2), Ebene deckungsgleich zur Flanschfläche
  (InsertRefPlane 4) mit ihrer Normale, Ebene durch die Achse und einen 3D-Skizzenpunkt.
d Masse: IMassProperty2.GetOverrideOptions → OverrideMass, SetOverrideMassValue(1,2); nach Speichern und Neuöffnen
  (Original-Kopie vorher gelöscht).
f Baugruppe: Komponente aus dem gespeicherten Teil, FeatureByName der Bezugsgeometrie, GetCorrespondingEntity einer
  Gewindefläche, Masse der Baugruppe.
g Speicher (Private Bytes) je Schritt.
h Bilder mit eingeblendeten Bezugsachsen/-ebenen (swDisplayAxes 4, swDisplayPlanes 5 am eigenen Dokument).

Aufruf: .venv\\Scripts\\python.exe -m spikes.s15_kaufteile [--step-neu]
"""

import shutil
import sys
import tempfile
import time
from pathlib import Path

from spikes._gemeinsam import lauf
from swki.aenderungen import sha256_datei
from swki.cli import main
from swki.compiler import sw
from swki.compiler.anker import punkt_achse_abstand
from swki.compiler.topologie import flaeche_aus, koerper, referenz_geometrie
from swki.konfig import PROJEKT, lade_rechner
from swki.pruefung.bilder import screenshots
from swki.pruefung.messen import oeffne
from swki.speicher import privat_mb
from swki.verbindung import byref_long, callout_leer, in_mm3, mm, verbinde

MUSTER = PROJEKT / "tests" / "referenz" / "motorhalter" / "muster"
AUFTRAG = "S15-MUSTER"
SW_3D_INTERCONNECT, SW_IMPORT_DIAGNOSE, SW_IMPORT_STRUKTUR = 691, 690, 579
STRUKTUR_MEHRKOERPER = 2
SW_SHEET_BODY = 1
REF_PLANE_DECKUNGSGLEICH = 4
L = 21.2132


def _mb(app) -> float:
    return privat_mb(int(app.GetProcessID))


def _optionen(app) -> dict:
    return {"3d_interconnect": app.GetUserPreferenceToggle(SW_3D_INTERCONNECT),
            "importdiagnose": app.GetUserPreferenceToggle(SW_IMPORT_DIAGNOSE),
            "strukturabbildung": app.GetUserPreferenceIntegerValue(SW_IMPORT_STRUKTUR)}


def _testdaten(app, r) -> dict:
    e = {"privat_mb_vorher": _mb(app)}
    auftrag = Path(tempfile.mkdtemp()) / AUFTRAG
    shutil.copytree(MUSTER, auftrag, ignore=shutil.ignore_patterns("*.step", "*.md"))
    spec = str(auftrag / "gm42.yaml")
    e["cli"] = [main([befehl, spec]) for befehl in ("validieren", "freigeben", "bauen")]
    asm = sorted((r.arbeitsordner / AUFTRAG).glob("lauf-*/*.sldasm"))[-1]
    model = oeffne(app, asm)
    exporte = []
    try:
        for i in (1, 2):
            ziel = r.arbeitsordner / "S15" / f"gm42-10_{i}.step"
            sw.speichere(model, ziel, kopie=True)
            exporte.append(ziel)
            time.sleep(1.5)  # Zeitstempel im STEP-Kopf sollen sich unterscheiden können
    finally:
        sw.schliesse(app, model)
    a, b = (p.read_text(encoding="latin-1").splitlines() for p in exporte)
    unterschiede = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
    ziel = MUSTER / "gm42-10.step"
    if ziel.exists() and "--step-neu" not in sys.argv:
        e["step_nicht_ueberschrieben"] = True  # committete Test-STEP (B4) schützen
    else:
        shutil.copy2(exporte[0], ziel)
    e |= {"zeilen": len(a), "unterschiede": len(unterschiede) + abs(len(a) - len(b)), "beispiele": unterschiede[:5],
          "datei": str(ziel), "groesse_kb": round(ziel.stat().st_size / 1024, 1), "sha256": sha256_datei(ziel),
          "privat_mb_nachher": _mb(app)}
    return e


def _importiere(app, pfad: Path):
    e = {"vorher": _optionen(app), "privat_mb_vorher": _mb(app)}
    with sw.einstellung(app, SW_3D_INTERCONNECT, False), sw.einstellung(app, SW_IMPORT_DIAGNOSE, False), \
            sw.einstellung_int(app, SW_IMPORT_STRUKTUR, STRUKTUR_MEHRKOERPER):
        e["waehrend"] = _optionen(app)
        daten = app.GetImportFileData(str(pfad))
        e["importdaten"] = daten is not None
        fehler = byref_long()
        beginn = time.perf_counter()
        model = app.LoadFile4(str(pfad), "r", daten, fehler)
        e["loadfile4"] = {"dokument": model is not None, "fehler": fehler.value, "s": round(time.perf_counter() - beginn, 3)}
        if model is None:
            fehler2, warnungen = byref_long(), byref_long()
            model = app.OpenDoc6(str(pfad), 1, 1, "", fehler2, warnungen)
            e["opendoc6"] = {"dokument": model is not None, "fehler": fehler2.value, "warnungen": warnungen.value}
    e["nachher"] = _optionen(app)
    e["privat_mb_nachher"] = _mb(app)
    return model, e


def _diagnose(model) -> tuple[dict, list]:
    koerper_ = koerper(model)
    e = {"koerper": len(koerper_), "flaechenkoerper": len(model.GetBodies2(SW_SHEET_BODY, False) or ())}
    e["check3"] = [None if (c := b.Check3) is None else c.Count for b in koerper_]
    features, f = [], model.FirstFeature
    while f is not None:
        features.append([f.Name, f.GetTypeName2, bool(f.Is3DInterconnectFeature)])
        f = f.GetNextFeature
    e["features"] = features
    e["box"] = sw.teilebox_mm(model)
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    e["volumen"], e["masse_kg"] = round(in_mm3(mp.Volume), 3), mp.Mass
    beginn = time.perf_counter()
    flaechen = [flaeche_aus(x) for b in koerper_ for x in (b.GetFaces() or ())]
    e["flaechen"] = len(flaechen)
    e["s_je_flaeche"] = round((time.perf_counter() - beginn) / max(len(flaechen), 1), 4)
    e["zylinder_d"] = sorted({round(2 * x.radius, 4) for x in flaechen if x.art == "zylinder"})
    return e, flaechen


def _bezuege(model, flaechen: list) -> dict:
    e = {}
    welle = [f for f in flaechen if f.art == "zylinder" and abs(f.radius - 5) < 1e-6
             and abs(punkt_achse_abstand((5.0, -15.0, 0.0), f.punkt, f.achse) - 5) < 0.01]
    e["wellenflaechen"] = len(welle)
    sw.auswahl_leeren(model)
    sw.waehle(model, welle[0].objekt, 0)
    e["insertaxis2"] = bool(model.InsertAxis2(True))
    achse = sw.letztes_feature(model)
    achse.Name = "EINBAU_ACHSE"
    e["achse"] = {"typ": achse.GetTypeName2, "geometrie": referenz_geometrie(achse)}
    flansch = [f for f in flaechen if f.art == "ebene" and f.normale[1] < -0.999 and abs(f.punkt[1]) < 1e-6]
    e["flanschflaechen"] = [{"punkt": f.punkt, "normale": f.normale} for f in flansch]
    sw.auswahl_leeren(model)
    sw.waehle(model, flansch[0].objekt, 0)
    ebene = model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0, 0, 0.0)
    e["ebene"] = {"erzeugt": ebene is not None}
    if ebene is not None:
        ebene.Name = "EINBAU_FLANSCH"
        e["ebene"]["geometrie"] = referenz_geometrie(ebene)
    sm = model.SketchManager
    sw.auswahl_leeren(model)
    sm.Insert3DSketch(True)
    with sw.ohne_inferenz(sm):
        punkt = sm.CreatePoint(mm(0.0), mm(0.0), mm(25.0))
    sm.Insert3DSketch(True)
    skizze = sw.letztes_feature(model)
    skizze.Name = "EINBAU_DREHLAGE_punkt"
    sw.auswahl_leeren(model)
    achse.Select2(False, 0)
    gewaehlt = model.Extension.SelectByID2("Point1@EINBAU_DREHLAGE_punkt", "EXTSKETCHPOINT", 0, 0, 0, True, 1,
                                           callout_leer(), 0)
    drehlage = model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0)
    e["drehlage"] = {"punkt": punkt is not None, "punkt_gewaehlt": bool(gewaehlt), "erzeugt": drehlage is not None}
    if drehlage is not None:
        drehlage.Name = "EINBAU_DREHLAGE"
        e["drehlage"]["geometrie"] = referenz_geometrie(drehlage)
    sw.auswahl_leeren(model)
    try:
        sw.rebuild(model)
        e["rebuild"] = "ok"
    except Exception as ex:
        e["rebuild"] = str(ex)
    e["namen"] = {n: model.FeatureByName(n) is not None for n in ("EINBAU_ACHSE", "EINBAU_FLANSCH", "EINBAU_DREHLAGE")}
    gewinde = [f for f in flaechen if f.art == "zylinder" and punkt_achse_abstand((L, 0.0, L), f.punkt, f.achse) < 0.1]
    e["gewinde_d"] = sorted(round(2 * f.radius, 4) for f in gewinde)
    return e


def _masse(model) -> dict:
    mp = model.Extension.CreateMassProperty2
    optionen = mp.GetOverrideOptions
    optionen.OverrideMass = True
    optionen.SetOverrideMassValue(1.2)
    neu = model.Extension.CreateMassProperty2
    neu.UseSystemUnits = True
    return {"masse_kg": neu.Mass, "override": bool(neu.GetOverrideOptions.OverrideMass),
            "override_wert": neu.GetOverrideOptions.GetOverrideMassValue}


def _bilder(app, model, ordner: Path) -> dict:
    vorher = {t: model.Extension.GetUserPreferenceToggle(t, 0) for t in (4, 5)}
    for t in (4, 5):
        model.Extension.SetUserPreferenceToggle(t, 0, True)
    bilder = screenshots(app, model, ordner)
    return {"vorher": vorher, "bilder": {n: Path(p).stat().st_size for n, p in bilder.items()}, "pfade": bilder}


def _neu_oeffnen(app, teil: Path) -> dict:
    model = oeffne(app, teil)
    try:
        mp = model.Extension.CreateMassProperty2
        mp.UseSystemUnits = True
        features, f = [], model.FirstFeature
        while f is not None:
            features.append([f.Name, bool(f.Is3DInterconnectFeature)])
            f = f.GetNextFeature
        return {"koerper": len(koerper(model)), "masse_kg": mp.Mass, "override": bool(mp.GetOverrideOptions.OverrideMass),
                "namen": {n: model.FeatureByName(n) is not None for n in ("EINBAU_ACHSE", "EINBAU_FLANSCH", "EINBAU_DREHLAGE")},
                "interconnect": [n for n, i in features if i]}
    finally:
        sw.schliesse(app, model)


def _baugruppe(app, r, teil: Path) -> dict:
    model = oeffne(app, teil)
    asm = app.NewDocument(str(r.vorlage_baugruppe), 0, 0, 0)
    try:
        komp = asm.AddComponent5(str(teil), 0, "", False, "", 0.0, 0.0, 0.0)
        e = {"komponente": komp is not None}
        e["feature_by_name"] = {n: komp.FeatureByName(n) is not None for n in ("EINBAU_ACHSE", "EINBAU_FLANSCH", "EINBAU_DREHLAGE")}
        gewinde = [f for b in koerper(model) for f in (flaeche_aus(x) for x in (b.GetFaces() or ()))
                   if f.art == "zylinder" and punkt_achse_abstand((L, 0.0, L), f.punkt, f.achse) < 0.1]
        e["gewinde_entitaet"] = komp.GetCorrespondingEntity(gewinde[0].objekt) is not None if gewinde else None
        mp = asm.Extension.CreateMassProperty2
        mp.UseSystemUnits = True
        e["masse_baugruppe_kg"] = mp.Mass
        return e
    finally:
        sw.schliesse(app, asm)
        sw.schliesse(app, model)


def _untersuche() -> dict:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    ergebnis = {"privat_mb_start": _mb(app), "e_testdaten": _testdaten(app, r)}
    kopie = r.arbeitsordner / "S15" / "gm42-10_import.step"
    shutil.copy2(MUSTER / "gm42-10.step", kopie)
    model, ergebnis["a_import"] = _importiere(app, kopie)
    if model is None:
        return ergebnis
    teil = r.arbeitsordner / "S15" / "SWKI-MUSTER_GM42-10.sldprt"
    try:
        ergebnis["b_diagnose"], flaechen = _diagnose(model)
        ergebnis["c_bezuege"] = _bezuege(model, flaechen)
        ergebnis["d_masse"] = _masse(model)
        ergebnis["h_bilder"] = _bilder(app, model, r.arbeitsordner / "S15" / "bilder")
        sw.speichere(model, teil)
    finally:
        sw.schliesse(app, model)
    kopie.unlink()  # das Teil darf das Original nicht mehr brauchen
    ergebnis["d_neu_geoeffnet"] = _neu_oeffnen(app, teil)
    ergebnis["f_baugruppe"] = _baugruppe(app, r, teil)
    ergebnis["g_privat_mb_ende"] = _mb(app)
    ergebnis["optionen_ende"] = _optionen(app)
    return ergebnis


if __name__ == "__main__":
    lauf("s15_kaufteile", _untersuche)
