"""S18 a–e, g: API-Wege für das Paket Bestandsdateien (Spec 2026-10-25 §11, Plan „Abhängigkeiten vom Spike S18").

Wegwerf-Qualität: entscheidet, welche Wege die späteren Tasks nehmen. Jede Zeile läuft einzeln, mit Zeitlimit von außen, weil
ein modaler Dialog COM hängen lassen kann; Zwischenstände stehen nach jedem Schritt in docs/bestandsdateien/s18_<zeile>.json.
Geöffnet werden nur Kopien der selbst erzeugten Musterdateien unter <arbeitsordner>/S18/.

Aufruf (SolidWorks offen, frei): timeout 300 ..\\..\\..\\.venv\\Scripts\\python.exe -m spikes.s18_bestand <zeile>
Zeilen: b a c c2 c3 d e e2 g t t2 (t, t2: Konstruktionstabelle, eigene Läufe; vor c2, c3, d, t2 SolidWorks neu starten).

API (swki api methode, Parameterzahl laut Index; Enums laut swki api enum):
  ISldWorks.VersionHistory(1), .GetDocumentDependencies2(4: Document, Traverseflag, Searchflag, AddReadOnlyInfo),
    .OpenDoc6(6), .CloseDoc(1), .GetDocuments(0), .GetDocumentCount(0), .ReplaceReferencedDocument(3)
  swOpenDocOptions_e: Silent 1, ReadOnly 2, LoadExternalReferencesInMemory 512
  swFileLoadWarning_e: IdMismatch 1, ReadOnly 2, NeedsRegen 32, AlreadyOpen 128, MissingExternalReferences 1048576
  swFileLoadError_e: swIdMatchError 4, swFileWithSameTitleAlreadyOpen 65536
  swComponentSuppressionState_e: swComponentInternalIdMismatch 5
  IModelDoc2.Save3(3), .ShowConfiguration2(1), .GetConfigurationNames(0), .GetEquationMgr(0), .Parameter(1),
    .ForceRebuild3(1), .VersionHistory(0), .GetDependencies2(3), .GetDesignTable(0), .InsertFamilyTableOpen(1)
  IModelDocExtension.SaveAs3(7), .DeleteSelection2(1: swDelete_Children 1, swDelete_Absorbed 2),
    .ListExternalFileReferences(9, alle Ausgabe), .GetWhatsWrong(3), .GetWhatsWrongCount(0), .ReorderFeature(3:
    swMoveToEnd 1, swMoveBefore 2, swMoveAfter 3), .GetPackAndGo(0), .SavePackAndGo(1), .CustomPropertyManager(1)
  IPartDoc.ReorderFeature(2), .InsertPart3(3: swInsertPartImportSolids 1)
  IFeature.GetParents(0), .GetChildren(0), .GetFirstDisplayDimension(0), .GetNextDisplayDimension(1),
    .SetSuppression2(3: swSuppressFeature 0, swUnSuppressFeature 1; swThisConfiguration 1, swAllConfiguration 2,
    swSpecifyConfiguration 3), .IsSuppressed2(2)
  IDisplayDimension.GetDimension2(1), .IsLinked, .GetLinkedText(0), .IsReferenceDim(0), .GetAnnotation(0)
  IDimension.DrivenState (swDimensionDriven 1, swDimensionDriving 2), .ReadOnly, .IsDesignTableDimension(0), .FullName,
    .Name, .GetSystemValue3(2), .SetSystemValue3(3: swSetValue_InThisConfiguration 1, _InAllConfigurations 2,
    _InSpecificConfigurations 3 → swSetValueReturnStatus_e), .ReferencePoints
  IEquationMgr.GetCount(0), .Equation(Index), .GlobalVariable(Index), .Value(Index), .Status, .EvaluateAll(0),
    .SetEquationAndConfigurationOption(4: Index, Equation, WhichConfigurations, ConfigNames)
  IBody2.Copy2(1: PreserveFaceIDs), .Operations2(3: SWBODYCUT 15902, ToolBody, ErrorCode; swBodyOperationError_e),
    .Check3, .GetBodyBox(0), .GetMassProperties(1), .Display3(3)
  IPackAndGo: über IDispatch nicht erreichbar, siehe zeile_g
  ICustomPropertyManager.GetAll3(5)
  IAnnotation.Color (Get/Put), .Select3(2: Append, Data), .Visible, .GetName(0)
  ISelectionMgr.CreateSelectData(0), .GetSelectedObjectCount2(1: Mark), .GetSelectedObjectType3(2: Index, Mark)
  ISldWorks.DocumentVisible(2: Visible, Type)
  IModelDocExtension.SetUserPreferenceToggle(3: UserPref, UserPrefOption, Value; swDisplayAnnotations 31,
    swDisplayFeatureDimensions 32), .GetUserPreferenceInteger(2: swUnitSystem 263), .HasDesignTable(0)
  IConfigurationManager.ActiveConfiguration (Property-Get), .AddConfiguration2(7)
  IFeature.GetFirstSubFeature(0), .GetNextSubFeature(0), .GetSpecificFeature2(0); ISketch.GetConstrainedStatus(0)
"""

import hashlib
import json
import shutil
import stat
import sys
import time
import traceback
from pathlib import Path

import pythoncom
import win32com.client

from swki.konfig import PROJEKT, lade_rechner
from swki.pruefung.messen import skizzenstatus
from swki.speicher import privat_mb
from swki.verbindung import byref_long, byref_str, byref_variant, callout_leer, mm, verbinde

R = lade_rechner()
S18 = R.arbeitsordner / "S18"
MUSTER = PROJEKT / "tests" / "referenz" / "bestand" / "muster"  # stammt aus werkzeuge/bestand_muster.py
ERGEBNIS = PROJEKT / "docs" / "bestandsdateien"
TEIL, ASM, STEPTEIL = "Lagerdeckel.SLDPRT", "Muster.SLDASM", "gm42-10.SLDPRT"
SW_OPEN_SILENT, SW_OPEN_READONLY = 1, 2
SW_DOC_PART, SW_DOC_ASSEMBLY = 1, 2
SW_SAVE_SILENT, SW_SAVE_COPY = 1, 2
SW_ALLE_KONF, SW_DIESE_KONF, SW_BENANNTE_KONF = 2, 1, 3   # swInConfigurationOpts_e
SW_WERT_DIESE, SW_WERT_ALLE, SW_WERT_BENANNT = 1, 2, 3    # swSetValueInConfiguration_e
SW_BODY_CUT = 15902
TAB = "Schnitt-Linear austragen1"   # Tasche; D1 = Tiefe 8


class Lauf:
    """Sammelt Ergebnisse einer Zeile und schreibt sie nach jedem Schritt weg (Hänger verlieren nichts)."""

    def __init__(self, app, zeile: str):
        self.app, self.zeile, self.d = app, zeile, {}
        self.pid = next(p for p in _sw_pid())
        self.t0 = time.monotonic()
        self.d["start_mb"] = round(privat_mb(self.pid))

    def __setitem__(self, k, v):
        self.d[k] = v
        self.schreibe()

    def __getitem__(self, k):
        return self.d[k]

    def schreibe(self):
        self.d["sekunden"] = round(time.monotonic() - self.t0, 1)
        self.d["ende_mb"] = round(privat_mb(self.pid))
        ERGEBNIS.mkdir(parents=True, exist_ok=True)
        (ERGEBNIS / f"s18_{self.zeile}.json").write_text(json.dumps(self.d, indent=1, ensure_ascii=False, default=str),
                                                         encoding="utf-8")


def _sw_pid():
    import subprocess
    aus = subprocess.run(["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe", "/FO", "CSV", "/NH"], capture_output=True,
                         text=True, encoding="oem").stdout
    return [int(z.split('","')[1]) for z in aus.splitlines() if "SLDWORKS" in z.upper()]


def frisch(name: str) -> Path:
    p = S18 / name
    if p.exists():
        for k in p.rglob("*"):
            if k.is_file():
                k.chmod(stat.S_IWRITE)
        shutil.rmtree(p)
    p.mkdir(parents=True)
    return p


def bestuecke(ordner: Path, *namen) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    for n in namen or (TEIL, ASM, STEPTEIL):
        shutil.copy2(MUSTER / n, ordner / n)
    return ordner


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def namen(liste):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, list(liste))


def oeffne(app, pfad: Path, optionen: int = SW_OPEN_SILENT, konf: str = ""):
    typ = SW_DOC_ASSEMBLY if pfad.suffix.lower() == ".sldasm" else SW_DOC_PART
    e, w = byref_long(), byref_long()
    t = time.monotonic()
    model = app.OpenDoc6(str(pfad), typ, optionen, konf, e, w)
    return model, {"fehler": e.value, "warnungen": w.value, "s": round(time.monotonic() - t, 2)}


def offene(app) -> list:
    return [d.GetPathName or d.GetTitle for d in (app.GetDocuments or ())]


def alle_zu(app) -> None:
    for _ in range(4):
        docs = app.GetDocuments or ()
        if not docs:
            return
        for d in docs:
            try:
                app.CloseDoc(d.GetTitle)
            except Exception:
                pass


def speichern(model) -> dict:
    e, w = byref_long(), byref_long()
    ok = model.Save3(SW_SAVE_SILENT, e, w)
    return {"ok": ok, "fehler": e.value, "warnungen": w.value}


def speichern_unter(model, pfad: Path, optionen=SW_SAVE_SILENT) -> dict:
    e, w = byref_long(), byref_long()
    ok = model.Extension.SaveAs3(str(pfad), 0, optionen, callout_leer(), callout_leer(), e, w)
    return {"ok": ok, "fehler": e.value, "warnungen": w.value}


def volumen(model) -> float:
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return round(mp.Volume * 1e9, 3)


def volumen_je_konfiguration(model) -> dict:
    aktiv = model.ConfigurationManager.ActiveConfiguration.Name
    aus = {}
    for k in model.GetConfigurationNames:
        model.ShowConfiguration2(k)
        model.EditRebuild3
        aus[k] = volumen(model)
    model.ShowConfiguration2(aktiv)
    return aus


def massname(dim) -> str:
    return dim.FullName.rsplit("@", 1)[0]


def alle_masse(model):
    f = model.FirstFeature
    while f is not None:
        dd = f.GetFirstDisplayDimension
        while dd is not None:
            yield f, dd
            dd = f.GetNextDisplayDimension(dd)
        f = f.GetNextFeature


def setze_tiefe(model, wert_mm: float) -> int:
    """Maß ändern für S18a: Tiefe der Tasche in allen Konfigurationen."""
    return model.Parameter(f"D1@{TAB}").SetSystemValue3(mm(wert_mm), SW_WERT_ALLE, callout_leer())


def fehlerliste(model) -> list:
    if not model.Extension.GetWhatsWrongCount:
        return []
    f, c, w = byref_variant(), byref_variant(), byref_variant()
    model.Extension.GetWhatsWrong(f, c, w)
    return [{"feature": x.Name, "code": y, "warnung": bool(z)}
            for x, y, z in zip(f.value or (), c.value or (), w.value or ())]


def baugruppe_probe(app, pfad: Path) -> dict:
    """Öffnet eine Baugruppe still und liest, was der Nutzer als ID-Warnung sähe."""
    asm, d = oeffne(app, pfad)
    if asm is None:
        return d | {"offen": False}
    d["bits"] = {"id_mismatch": bool(d["warnungen"] & 1), "needs_regen": bool(d["warnungen"] & 32),
                 "fehlt": bool(d["warnungen"] & 1048576)}
    d["komponenten"] = []
    for k in asm.GetComponents(True) or ():
        doc = k.GetModelDoc2
        d["komponenten"].append({"name": k.Name2, "pfad": k.GetPathName, "unterdrueckt": k.GetSuppression2,
                                 "volumen": volumen(doc) if doc is not None else None})
    d["neuaufbau"] = asm.EditRebuild3
    d["whats_wrong"] = fehlerliste(asm)
    alle_zu(app)
    return d


# ---------------------------------------------------------------------------------------------------- Zeile b


def lies(app, model) -> dict:
    """Probe der späteren Aufnahme: alles, was bestand.json braucht."""
    konf = list(model.GetConfigurationNames)
    t = time.monotonic()
    d: dict = {"konfigurationen": konf, "aktiv": model.ConfigurationManager.ActiveConfiguration.Name}
    baum, masse = [], {}
    for k in konf:
        model.ShowConfiguration2(k)
        for f, dd in alle_masse(model):
            dim = dd.GetDimension2(0)
            name = massname(dim)
            e = masse.setdefault(name, {"voll": dim.FullName, "feature": f.Name, "typ2": dd.Type2})
            e.setdefault("gelesen_in", []).append(k)
            e["werte"] = dim.GetSystemValue3(SW_WERT_BENANNT, namen(konf))
            e |= {"driven": dim.DrivenState, "readonly": dim.ReadOnly, "tabelle": dim.IsDesignTableDimension,
                  "linked": dd.IsLinked, "linked_text": dd.GetLinkedText, "referenz": dd.IsReferenceDim}
            try:
                e["punkte"] = [[round(x * 1000, 3) for x in p.ArrayData] for p in dim.ReferencePoints]
            except Exception as x:
                e["punkte"] = repr(x)
    model.ShowConfiguration2(d["aktiv"])
    f = model.FirstFeature
    while f is not None:
        unterdrueckt = f.IsSuppressed2(SW_BENANNTE_KONF, namen(konf))
        baum.append({"name": f.Name, "typ": f.GetTypeName2, "eltern": [p.Name for p in f.GetParents or ()],
                     "kinder": [c.Name for c in f.GetChildren or ()], "unterdrueckt": unterdrueckt})
        f = f.GetNextFeature
    d["baum"] = [b for b in baum if b["typ"] not in ORDNER]
    d["masse"] = masse
    gl = model.GetEquationMgr
    d["gleichungen"] = [{"i": i, "text": gl.Equation(i), "global": gl.GlobalVariable(i), "wert": gl.Value(i)}
                        for i in range(gl.GetCount)]
    d["skizzen"] = skizzenstatus(model)
    d["fehler"] = fehlerliste(model)
    d["extern"] = externe_referenzen(model)
    d["material"] = {k: model.GetMaterialPropertyName2(k, byref_str()) for k in konf}
    d["eigenschaften"] = {k: eigenschaften(model, k) for k in ("", *konf)}
    d["einheit"] = model.Extension.GetUserPreferenceInteger(263, 0)  # swUnitSystem: 5 = MMGS
    d["version"] = model.VersionHistory
    d["tabelle_vorhanden"] = model.GetDesignTable is not None
    d["lesen_s"] = round(time.monotonic() - t, 2)
    return d


ORDNER = {"CommentsFolder", "FavoriteFolder", "HistoryFolder", "SelectionSetFolder", "SensorFolder", "DocsFolder",
          "DetailCabinet", "SurfaceBodyFolder", "SolidBodyFolder", "EnvFolder", "InkMarkupFolder"}


def eigenschaften(model, konf: str) -> dict:
    a, b, c, e, g = byref_variant(), byref_variant(), byref_variant(), byref_variant(), byref_variant()
    model.Extension.CustomPropertyManager(konf).GetAll3(a, b, c, e, g)
    return dict(zip(a.value or (), c.value or ()))


def externe_referenzen(model) -> dict:
    a = [byref_variant() for _ in range(7)]
    co, cn = byref_long(), byref_str()
    model.Extension.ListExternalFileReferences(*a, co, cn)
    return {"modell": a[0].value, "komponente": a[1].value, "typ": a[3].value, "status": a[4].value,
            "entity": a[5].value, "konfig_option": co.value, "konfig": cn.value}


def zeile_b(app) -> None:
    lauf = Lauf(app, "b")
    basis = frisch("b")
    alle_zu(app)
    # 1 VersionHistory und Abhängigkeiten ohne Öffnen
    kopie = bestuecke(basis / "ruhend")
    t = time.monotonic()
    lauf["version_ohne_oeffnen"] = {"werte": app.VersionHistory(str(kopie / TEIL)),
                                    "s": round(time.monotonic() - t, 3), "offen_danach": offene(app),
                                    "letztes_kaufteil": app.VersionHistory(str(kopie / STEPTEIL))[-1:]}
    t = time.monotonic()
    lauf["abhaengigkeiten"] = {
        "tief_ohne_suche": app.GetDocumentDependencies2(str(kopie / ASM), True, False, False),
        "tief_mit_suche": app.GetDocumentDependencies2(str(kopie / ASM), True, True, False),
        "flach_ro": app.GetDocumentDependencies2(str(kopie / ASM), False, False, True),
        "teil": app.GetDocumentDependencies2(str(kopie / TEIL), True, False, False),
        "s": round(time.monotonic() - t, 3), "offen_danach": offene(app)}
    lauf["einstellungen"] = {
        "suchregeln": app.GetUserPreferenceToggle(0), "laden_extern": app.GetUserPreferenceIntegerValue(82),
        "refs_in_speicher": app.GetUserPreferenceToggle(641), "extern_nur_lesen": app.GetUserPreferenceToggle(14),
        "dokumentordner": app.GetUserPreferenceStringValue(1)}
    # 2 Aus welchem Ordner lädt OpenDoc6? Die gespeicherten Pfade zeigen auf S18/muster (dort: Tasche 8)
    herkunft = S18 / "muster"
    lauf["gespeicherter_pfad_vorhanden"] = (herkunft / TEIL).exists()
    vorher = {n: sha(herkunft / n) for n in (TEIL, ASM, STEPTEIL)}
    daneben = bestuecke(basis / "daneben")
    m, s = oeffne(app, daneben / TEIL)
    setze_tiefe(m, 10)
    m.EditRebuild3
    lauf["kennzeichen_daneben"] = {"oeffnen": s, "speichern": speichern(m), "volumen": volumen(m)}
    alle_zu(app)
    lauf["sibling_vor_altem_pfad"] = baugruppe_probe(app, daneben / ASM)
    # Teil fehlt neben der Baugruppe: fällt SolidWorks auf den Originalpfad zurück?
    ohne = bestuecke(basis / "ohne_teil", ASM)
    lauf["fehlt_neben_baugruppe"] = baugruppe_probe(app, ohne / ASM)
    lauf["herkunft_unveraendert"] = vorher == {n: sha(herkunft / n) for n in (TEIL, ASM, STEPTEIL)}
    # 3 Lesen einer schreibgeschützten Bestandskopie
    ro = bestuecke(basis / "ro", TEIL)
    (ro / TEIL).chmod(stat.S_IREAD)
    sha0 = sha(ro / TEIL)
    m, s = oeffne(app, ro / TEIL)
    lauf["oeffnen_schreibgeschuetzt"] = s | {"nur_lesen": m.IsOpenedReadOnly}
    lauf["lesen"] = lies(app, m)
    lauf["speichern_auf_ro"] = speichern(m)
    alle_zu(app)
    lauf["ro_unveraendert"] = sha0 == sha(ro / TEIL)
    # 4 Teil mit externer Referenz (abgeleitetes Teil)
    ext = bestuecke(basis / "ext" / "original", TEIL)
    a, s = app.NewDocument(str(R.vorlage_teil), 0, 0, 0), None
    f = a.InsertPart3(str(ext / TEIL), 1, "")
    lauf["abgeleitet"] = {"feature": f.GetTypeName2 if f is not None else None}
    pfad = ext / "Abgeleitet.SLDPRT"
    lauf["abgeleitet_speichern"] = speichern_unter(a, pfad)
    alle_zu(app)
    kopie_ext = bestuecke(basis / "ext" / "kopie")
    (kopie_ext / TEIL).unlink()
    (kopie_ext / ASM).unlink()
    (kopie_ext / STEPTEIL).unlink()
    shutil.copy2(pfad, kopie_ext / "Abgeleitet.SLDPRT")
    lauf["ext_abh_ohne_oeffnen"] = app.GetDocumentDependencies2(str(kopie_ext / "Abgeleitet.SLDPRT"), True, False, False)
    m, s = oeffne(app, kopie_ext / "Abgeleitet.SLDPRT")
    lauf["ext_oeffnen"] = s | {"offen": offene(app), "liste": externe_referenzen(m), "abh": m.GetDependencies2(True, False, False)}
    alle_zu(app)
    # 5 Neuaufbau-Fehler erzeugen und lesen (Tasche weg → Rippe ohne Boden)
    fehl = bestuecke(basis / "fehler", TEIL)
    m, s = oeffne(app, fehl / TEIL)
    lauf["fehler_vorher"] = fehlerliste(m)
    m.ClearSelection2(True)
    m.FeatureByName(TAB).Select2(False, 0)
    lauf["tasche_loeschen"] = m.Extension.DeleteSelection2(0)
    lauf["neuaufbau_nach_eingriff"] = {"ok": m.EditRebuild3, "fehler": fehlerliste(m),
                                       "baum": [b["name"] for b in lies(app, m)["baum"]]}
    alle_zu(app)


# ---------------------------------------------------------------------------------------------------- Zeile a


def zeile_a(app) -> None:
    lauf = Lauf(app, "a")
    basis = frisch("a")
    alle_zu(app)
    ruhend = S18 / "muster"
    weg = S18 / "muster_weg"
    if ruhend.exists():
        ruhend.rename(weg)   # die gespeicherten Pfade sollen ins Leere zeigen, die Baugruppe nur ihren Ordner finden
    try:
        def fall(name: str) -> Path:
            o = bestuecke(basis / name)
            a, s = oeffne(app, o / ASM)
            lauf[f"{name}_bereiten"] = s | {"pfade": [k.GetPathName for k in a.GetComponents(True) or ()],
                                            "speichern": speichern(a)}
            alle_zu(app)
            lauf[f"{name}_nachher_offen"] = offene(app)
            return o

        k = fall("kontrolle")
        lauf["kontrolle"] = baugruppe_probe(app, k / ASM)

        # An Ort und Stelle: Datei-Kopie → Kopie öffnen → Maß → Save3 → Datei-Kopie zurück
        o = fall("an_ort")
        arbeit = bestuecke(basis / "an_ort_arbeit", TEIL)
        m, s = oeffne(app, arbeit / TEIL)
        setze_tiefe(m, 9)
        m.EditRebuild3
        lauf["an_ort_aendern"] = s | {"speichern": speichern(m), "volumen": volumen(m)}
        alle_zu(app)
        vorher = sha(o / TEIL)
        shutil.copy2(arbeit / TEIL, o / TEIL)
        lauf["an_ort"] = {"sha_geaendert": vorher != sha(o / TEIL)} | baugruppe_probe(app, o / ASM)
        # Zweite Runde: Nochmal öffnen und speichern, dann erneut zurückkopieren (Nachbessern durch den Kollegen)
        m, s = oeffne(app, arbeit / TEIL)
        setze_tiefe(m, 10)
        m.EditRebuild3
        speichern(m)
        alle_zu(app)
        shutil.copy2(arbeit / TEIL, o / TEIL)
        lauf["an_ort_zweimal"] = baugruppe_probe(app, o / ASM)

        # Gegenprobe 1: SaveAs3 unter neuem Namen, Datei danach unter altem Namen zurück
        o = fall("saveas_neu")
        arbeit = bestuecke(basis / "saveas_neu_arbeit", TEIL)
        m, s = oeffne(app, arbeit / TEIL)
        setze_tiefe(m, 9)
        lauf["saveas_neu_speichern"] = speichern_unter(m, arbeit / "Neu.SLDPRT")
        alle_zu(app)
        shutil.copy2(arbeit / "Neu.SLDPRT", o / TEIL)
        lauf["saveas_neu"] = baugruppe_probe(app, o / ASM)

        # Gegenprobe 2: SaveAs3 gleicher Name, anderer Ordner
        o = fall("saveas_ordner")
        arbeit = bestuecke(basis / "saveas_ordner_arbeit", TEIL)
        (arbeit / "x").mkdir()
        m, s = oeffne(app, arbeit / TEIL)
        setze_tiefe(m, 9)
        lauf["saveas_ordner_speichern"] = speichern_unter(m, arbeit / "x" / TEIL)
        alle_zu(app)
        shutil.copy2(arbeit / "x" / TEIL, o / TEIL)
        lauf["saveas_ordner"] = baugruppe_probe(app, o / ASM)

        # Gegenprobe 3: SaveAs3 als Kopie (Option Copy)
        o = fall("saveas_kopie")
        arbeit = bestuecke(basis / "saveas_kopie_arbeit", TEIL)
        m, s = oeffne(app, arbeit / TEIL)
        setze_tiefe(m, 9)
        m.EditRebuild3
        lauf["saveas_kopie_speichern"] = speichern_unter(m, arbeit / "Kopie.SLDPRT", SW_SAVE_SILENT | SW_SAVE_COPY)
        alle_zu(app)
        shutil.copy2(arbeit / "Kopie.SLDPRT", o / TEIL)
        lauf["saveas_kopie"] = baugruppe_probe(app, o / ASM)

        # Kontrolle des Detektors: ein wirklich anderes Teil unter dem Originalnamen
        o = fall("fremd")
        neu = app.NewDocument(str(R.vorlage_teil), 0, 0, 0)
        ebene = next(_ebenen(neu))
        ebene.Select2(False, 0)
        neu.SketchManager.InsertSketch(True)
        neu.SketchManager.CreateCornerRectangle(-0.05, -0.03, 0, 0.05, 0.03, 0)
        neu.SketchManager.InsertSketch(True)
        neu.FeatureByPositionReverse(0).Select2(False, 0)
        neu.FeatureManager.FeatureExtrusion3(True, False, False, 0, 0, 0.02, 0.0, False, False, False, False, 0.0, 0.0,
                                             False, False, False, False, True, True, True, 0, 0.0, False)
        (basis / "fremd_arbeit").mkdir()
        lauf["fremd_speichern"] = speichern_unter(neu, basis / "fremd_arbeit" / TEIL)
        alle_zu(app)
        shutil.copy2(basis / "fremd_arbeit" / TEIL, o / TEIL)
        lauf["fremd"] = baugruppe_probe(app, o / ASM)
    finally:
        if weg.exists():
            weg.rename(ruhend)


def _ebenen(model):
    f = model.FirstFeature
    while f is not None:
        if f.GetTypeName2 == "RefPlane":
            yield f
        f = f.GetNextFeature


# ---------------------------------------------------------------------------------------------------- Zeile c


def wert_je_konf(model, name: str) -> dict:
    """Wert eines Maßes je Konfiguration, durch Umschalten (c1: GetSystemValue3 mit Namen taugt dafür nicht)."""
    aktiv = model.ConfigurationManager.ActiveConfiguration.Name
    aus = {}
    for k in model.GetConfigurationNames:
        model.ShowConfiguration2(k)
        p = model.Parameter(name)
        aus[k] = None if p is None else round(p.GetSystemValue3(SW_WERT_DIESE, None)[0] * 1000, 6)
    model.ShowConfiguration2(aktiv)
    return aus


def unterdrueckt(model, name: str) -> dict:
    f = model.FeatureByName(name)
    konf = list(model.GetConfigurationNames)
    return dict(zip(konf, f.IsSuppressed2(SW_BENANNTE_KONF, namen(konf))))


def baumnamen(model) -> list:
    aus, f = [], model.FirstFeature
    while f is not None:
        if f.GetTypeName2 not in ORDNER and f.GetTypeName2 not in ("RefPlane", "OriginProfileFeature", "MaterialFolder",
                                                                    "EqnFolder"):
            aus.append(f.Name)
        f = f.GetNextFeature
    return aus


def gleichungen(model) -> list:
    gl = model.GetEquationMgr
    return [gl.Equation(i) for i in range(gl.GetCount)]


def zeile_c(app) -> None:
    lauf = Lauf(app, "c")
    basis = frisch("c")
    alle_zu(app)

    def kopie(name: str):
        o = bestuecke(basis / name, TEIL)
        m, _ = oeffne(app, o / TEIL)
        return m, o

    # c1 Lesen je Konfiguration ohne Umschalten?
    m, _ = kopie("c1")
    p = m.Parameter(f"D1@{TAB}")
    beide = ["Standard", "Variante B"]
    g = {"aktiv_diese": p.GetSystemValue3(SW_WERT_DIESE, None), "alle": p.GetSystemValue3(SW_WERT_ALLE, None),
         "benannt_beide": p.GetSystemValue3(SW_WERT_BENANNT, namen(beide)),
         "benannt_andere": p.GetSystemValue3(SW_WERT_BENANNT, namen(["Variante B"]))}
    m.ShowConfiguration2("Variante B")
    g["aktiv_b_benannt_beide"] = m.Parameter(f"D1@{TAB}").GetSystemValue3(SW_WERT_BENANNT, namen(beide))
    m.ShowConfiguration2("Standard")
    g["fase_d1"] = wert_je_konf(m, "D1@Fase1")
    lauf["c1_lesen"] = g
    alle_zu(app)

    # c2 Maß in allen Konfigurationen, c3 in einer
    m, _ = kopie("c2")
    p = m.Parameter(f"D1@{TAB}")
    lauf["c2_alle"] = {"status": p.SetSystemValue3(mm(9), SW_WERT_ALLE, None), "rebuild": m.EditRebuild3,
                       "werte": wert_je_konf(m, f"D1@{TAB}"), "volumen": volumen_je_konfiguration(m)}
    p = m.Parameter(f"D1@{TAB}")
    lauf["c3_nur_b_von_standard"] = {
        "status": p.SetSystemValue3(mm(7), SW_WERT_BENANNT, namen(["Variante B"])), "rebuild": m.EditRebuild3,
        "werte": wert_je_konf(m, f"D1@{TAB}"), "volumen": volumen_je_konfiguration(m),
        "aktiv": m.ConfigurationManager.ActiveConfiguration.Name}
    p = m.Parameter(f"D1@{TAB}")
    lauf["c3_nur_aktiv"] = {"status": p.SetSystemValue3(mm(6), SW_WERT_DIESE, None),
                            "werte": wert_je_konf(m, f"D1@{TAB}")}
    alle_zu(app)

    # c4 Globale Variable: SetEquationAndConfigurationOption und Equation (Property-Put)
    m, _ = kopie("c4")
    gl = m.GetEquationMgr
    i = next(i for i in range(gl.GetCount) if gl.GlobalVariable(i))
    e = {"vorher": gleichungen(m), "index": i,
         "set_option": gl.SetEquationAndConfigurationOption(i, '"L" = 110', SW_ALLE_KONF, None)}
    e |= {"ausgewertet": gl.EvaluateAll, "status": gl.Status, "rebuild": m.EditRebuild3, "nachher": gleichungen(m),
          "d1": wert_je_konf(m, "D1@Skizze1"), "volumen": volumen_je_konfiguration(m)}
    lauf["c4_variable_option"] = e
    gl = m.GetEquationMgr
    dispid = gl._oleobj_.GetIDsOfNames("Equation")
    gl._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, i, '"L" = 120')
    lauf["c4_variable_put"] = {"status": gl.Status, "ausgewertet": gl.EvaluateAll, "rebuild": m.EditRebuild3,
                               "nachher": gleichungen(m), "d1": wert_je_konf(m, "D1@Skizze1"),
                               "volumen": volumen_je_konfiguration(m), "fehler": fehlerliste(m)}
    gl = m.GetEquationMgr
    j = next(j for j in range(gl.GetCount) if not gl.GlobalVariable(j))
    lauf["c4_gleichung"] = {"set": gl.SetEquationAndConfigurationOption(j, '"D1@Skizze1" = "L" + 5', SW_ALLE_KONF, None),
                            "ausgewertet": gl.EvaluateAll, "rebuild": m.EditRebuild3, "nachher": gleichungen(m),
                            "d1": wert_je_konf(m, "D1@Skizze1")}
    alle_zu(app)

    # c5 Maß an der Gleichung vorbei überschreiben: was passiert? Getriebenes Maß setzen
    m, _ = kopie("c5")
    p = m.Parameter("D1@Skizze1")
    lauf["c5_gesteuert"] = {"status": p.SetSystemValue3(mm(90), SW_WERT_ALLE, None),
                            "direkt": p.GetSystemValue3(SW_WERT_DIESE, None), "rebuild": m.EditRebuild3,
                            "nach_rebuild": wert_je_konf(m, "D1@Skizze1")}
    p = m.Parameter("D5@Skizze2")
    lauf["c5_getrieben"] = {"status": p.SetSystemValue3(mm(40), SW_WERT_ALLE, None), "rebuild": m.EditRebuild3,
                            "werte": wert_je_konf(m, "D5@Skizze2")}
    alle_zu(app)

    # c6 Verknüpfte Maße
    m, _ = kopie("c6")
    g = {"parameter_d1": m.Parameter("D1@Skizze3") is not None,
         "parameter_name": m.Parameter("Bohrung_D@Skizze3") is not None}
    p = m.Parameter("Bohrung_D@Skizze3")
    g |= {"status": p.SetSystemValue3(mm(10), SW_WERT_ALLE, None), "rebuild": m.EditRebuild3,
          "s3": wert_je_konf(m, "Bohrung_D@Skizze3"), "s4": wert_je_konf(m, "Bohrung_D@Skizze4"),
          "volumen": volumen_je_konfiguration(m)}
    lauf["c6_verknuepft"] = g
    alle_zu(app)

    # c7 Unterdrücken: swThisConfiguration mit altem und neuem IFeature, alle, benannt, Eltern mit Kindern
    m, _ = kopie("c7")
    z = "Schnitt-Linear austragen2"
    f = m.FeatureByName(z)
    m.ShowConfiguration2("Variante B")
    g = {"alt_diese": f.SetSuppression2(0, SW_DIESE_KONF, None), "aktiv": m.ConfigurationManager.ActiveConfiguration.Name}
    g["nach_alt"] = unterdrueckt(m, z)
    f.SetSuppression2(1, SW_ALLE_KONF, None)
    g["nach_aufheben_alle"] = unterdrueckt(m, z)
    g["neu_diese"] = m.FeatureByName(z).SetSuppression2(0, SW_DIESE_KONF, None)
    g["nach_neu"] = unterdrueckt(m, z)
    m.EditRebuild3
    g["volumen"] = volumen_je_konfiguration(m)
    m.FeatureByName(z).SetSuppression2(1, SW_ALLE_KONF, None)
    m.ShowConfiguration2("Standard")
    g["alle"] = m.FeatureByName(z).SetSuppression2(0, SW_ALLE_KONF, None)
    g["nach_alle"] = unterdrueckt(m, z)
    m.EditRebuild3
    g["volumen_alle"] = volumen_je_konfiguration(m)
    m.FeatureByName(z).SetSuppression2(1, SW_ALLE_KONF, None)
    g["benannt"] = m.FeatureByName(z).SetSuppression2(0, SW_BENANNTE_KONF, namen(["Variante B"]))
    g["nach_benannt"] = unterdrueckt(m, z)
    m.EditRebuild3
    g["volumen_benannt"] = volumen_je_konfiguration(m)
    g["fehler"] = fehlerliste(m)
    eltern = "Aufsatz-Linear austragen1"
    g["eltern_unterdruecken"] = m.FeatureByName(eltern).SetSuppression2(0, SW_DIESE_KONF, None)
    g["eltern_folgen"] = {n: unterdrueckt(m, n) for n in (eltern, "Schnitt-Linear austragen1", "Fase1",
                                                          "Verstärkungsrippe1")}
    lauf["c7_unterdruecken"] = g
    alle_zu(app)

    # c8 Löschen
    faelle = {"schnitt_0": ("Schnitt-Linear austragen2", 0), "schnitt_absorbiert": ("Schnitt-Linear austragen2", 2),
              "skizze_0": ("Skizze3", 0), "skizze_kinder": ("Skizze3", 1), "skizze_beides": ("Skizze3", 3),
              "aufsatz_0": ("Aufsatz-Linear austragen1", 0), "aufsatz_kinder": ("Aufsatz-Linear austragen1", 1),
              "schnitt_kinder_absorbiert": ("Schnitt-Linear austragen2", 3)}
    for name, (feat, option) in faelle.items():
        m, _ = kopie(f"c8_{name}")
        vorher = baumnamen(m)
        ok1 = m.FeatureByName(feat).Select2(False, 0)
        ok = m.Extension.DeleteSelection2(option)
        m.ClearSelection2(True)
        rb = m.EditRebuild3
        nachher = baumnamen(m)
        lauf[f"c8_{name}"] = {"auswahl": ok1, "geloescht": ok, "weg": [x for x in vorher if x not in nachher],
                              "rebuild": rb, "fehler": fehlerliste(m), "gleichungen": gleichungen(m)}
        alle_zu(app)


def je_konfiguration(model) -> dict:
    """Baum, Neuaufbau, Fehler und Volumen je Konfiguration; fehlerliste() allein sieht nur die aktive."""
    aktiv = model.ConfigurationManager.ActiveConfiguration.Name
    aus: dict = {"aktiv": aktiv}
    for k in model.GetConfigurationNames:
        model.ShowConfiguration2(k)
        z = {"rebuild": model.EditRebuild3, "fehler": fehlerliste(model), "volumen": volumen(model),
             "rippe_unterdrueckt": unterdrueckt(model, "Verstärkungsrippe1")}
        model.ForceRebuild3(False)
        z |= {"nach_force": {"fehler": fehlerliste(model), "volumen": volumen(model)}, "baum": baumnamen(model)}
        aus[k] = z
    model.ShowConfiguration2(aktiv)
    aus["baum"] = baumnamen(model)
    return aus


def unterskizzen(feature) -> list:
    aus, s = [], feature.GetFirstSubFeature
    while s is not None:
        spez = s.GetSpecificFeature2
        aus.append({"name": s.Name, "typ": s.GetTypeName2,
                    "status": spez.GetConstrainedStatus if s.GetTypeName2 == "ProfileFeature" else None})
        s = s.GetNextSubFeature
    return aus


def zeile_c3(app) -> None:
    """Prüft die Vermutung aus c11/c12: Beschädigt ein fehlgeschlagenes ReorderFeature still eine Konfiguration?"""
    from swki.compiler.handler.normbohrung import normbohrung
    from swki.compiler.kontext import Kontext
    lauf = Lauf(app, "c3")
    basis = frisch("c3")
    alle_zu(app)

    def bohrung(m, o):
        f = {"id": "neu1", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [45, 0, 20]},
             "positionen": [["=-50+RA", 24], ["=-50+RA", -24]], "bezug": {"u": "-rand", "v": "mitte"}, "tiefe": 10}
        ctx = Kontext(app, m, {"parameter": {"RA": 12}, "features": [f]}, o / "spec.yaml", 0.01)
        ctx.knoten = "neu1"
        normbohrung(ctx, f)
        return m.FeatureByName("neu1")

    def fall(name: str, mit_bohrung: bool, fehlschlag: bool, aktiv_beim_speichern: str, gute_zuege: bool = False) -> None:
        o = bestuecke(basis / name, TEIL)
        m, _ = oeffne(app, o / TEIL)
        d: dict = {"vorher": je_konfiguration(m)}
        if mit_bohrung:
            d["unterskizzen"] = unterskizzen(bohrung(m, o))
            d["nach_bohrung"] = je_konfiguration(m)
        if gute_zuege:
            d["guter_zug"] = m.Extension.ReorderFeature("neu1", "Schnitt-Linear austragen3", 3)
            d["ans_ende"] = m.Extension.ReorderFeature("neu1", "", 1)
        if fehlschlag:
            d["unmoeglich"] = m.Extension.ReorderFeature("Verstärkungsrippe1", "Skizze1", 2)
            d["baum_direkt"] = baumnamen(m)
            d["nach_zug"] = je_konfiguration(m)
        m.ShowConfiguration2(aktiv_beim_speichern)
        d["speichern"] = speichern(m)
        lauf[name] = d
        alle_zu(app)
        m, s = oeffne(app, o / TEIL)
        d["oeffnen"] = s
        d["nach_oeffnen"] = je_konfiguration(m)
        lauf[name] = d
        alle_zu(app)

    fall("kontrolle_bohrung_b", True, False, "Variante B", gute_zuege=True)
    fall("wie_c11", True, True, "Variante B", gute_zuege=True)
    fall("nur_fehlschlag_b", False, True, "Variante B")
    fall("nur_fehlschlag_standard", False, True, "Standard")


def zeile_c2(app) -> None:
    """Eigener Lauf: c9 schlug nach c1 bis c8 bei 5,4 GB Private Bytes mit RPC_E_DISCONNECTED fehl, frisch nie."""
    from swki.compiler.handler.normbohrung import normbohrung
    from swki.compiler.kontext import Kontext
    lauf = Lauf(app, "c2")
    basis = frisch("c2")
    alle_zu(app)

    def kopie(name: str):
        o = bestuecke(basis / name, TEIL)
        m, _ = oeffne(app, o / TEIL)
        return m, o

    # Neues Feature, während Variante B aktiv ist: gilt es in Standard?
    m, o = kopie("in_b")
    m.ShowConfiguration2("Variante B")
    f = {"id": "neu1", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [45, 0, 20]},
         "positionen": [[-38, 24]], "tiefe": 10}
    ctx = Kontext(app, m, {"parameter": {}, "features": [f]}, o / "spec.yaml", 0.01)
    ctx.knoten = "neu1"
    normbohrung(ctx, f)
    g = {"unterdrueckt": unterdrueckt(m, "neu1"), "aktiv": m.ConfigurationManager.ActiveConfiguration.Name}
    g["volumen"] = volumen_je_konfiguration(m)
    m.ShowConfiguration2("Standard")
    m.ForceRebuild3(False)
    g["standard_nach_force"] = volumen(m)
    g["aufheben_alle"] = m.FeatureByName("neu1").SetSuppression2(1, SW_ALLE_KONF, None)
    g["unterdrueckt_danach"] = unterdrueckt(m, "neu1")
    g["volumen_danach"] = volumen_je_konfiguration(m)
    lauf["c9_in_variante_b"] = g
    alle_zu(app)

    # c9 Handler Normbohrung (Randbezug) auf fremder Fläche, c10 Umbenennen, c11 Verschieben, c12 Speichern
    m, o = kopie("c9")
    f = {"id": "neu1", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [45, 0, 20]},
         "positionen": [["=-50+RA", 24], ["=-50+RA", -24]], "bezug": {"u": "-rand", "v": "mitte"}, "tiefe": 10}
    spec = {"parameter": {"RA": 12}, "features": [f]}
    v0 = volumen_je_konfiguration(m)
    ctx = Kontext(app, m, spec, o / "spec.yaml", 0.01)
    ctx.knoten = "neu1"
    t = time.monotonic()
    erg = normbohrung(ctx, f)
    g = {"s": round(time.monotonic() - t, 2), "punkte": erg.punkte, "baum": baumnamen(m), "v0": v0,
         "massprotokoll": ctx.masse, "volumen": volumen_je_konfiguration(m), "fehler": fehlerliste(m)}
    feat = m.FeatureByName("neu1")
    g["typ"] = feat.GetTypeName2
    lauf["c9_normbohrung"] = g
    feat.Name = "Gewinde M6 Deckel"
    g = {"name": feat.Name, "gefunden": m.FeatureByName("Gewinde M6 Deckel") is not None}
    fx = m.FeatureByName("Verstärkungsrippe1")
    try:
        fx.Name = "Fase1"
        g["doppelt"] = fx.Name
    except Exception as x:
        g["doppelt_fehler"] = repr(x)
    fx.Name = "Verstärkungsrippe1"
    lauf["c10_umbenennen"] = g | {"baum": baumnamen(m)}
    v1 = volumen_je_konfiguration(m)
    g = {"nach_schnitt3": m.Extension.ReorderFeature("Gewinde M6 Deckel", "Schnitt-Linear austragen3", 3)}
    g["baum_1"] = baumnamen(m)
    g["rebuild_1"] = m.EditRebuild3
    g["volumen_gleich"] = v1 == volumen_je_konfiguration(m)
    g["vor_tasche"] = m.Extension.ReorderFeature("Gewinde M6 Deckel", "Schnitt-Linear austragen1", 2)
    g["baum_2"] = baumnamen(m)
    g["ans_ende"] = m.Extension.ReorderFeature("Gewinde M6 Deckel", "", 1)
    g["baum_3"] = baumnamen(m)
    g["unmoeglich"] = m.Extension.ReorderFeature("Verstärkungsrippe1", "Skizze1", 2)
    g["baum_4"] = baumnamen(m)
    g["rebuild"] = m.EditRebuild3
    g["fehler"] = fehlerliste(m)
    lauf["c11_verschieben"] = g
    m.ShowConfiguration2("Variante B")
    g = {"speichern": speichern(m), "aktiv_vorher": m.ConfigurationManager.ActiveConfiguration.Name}
    alle_zu(app)
    m, s = oeffne(app, o / TEIL)
    g |= {"oeffnen": s, "aktiv_nachher": m.ConfigurationManager.ActiveConfiguration.Name, "baum": baumnamen(m),
          "volumen": volumen_je_konfiguration(m), "fehler": fehlerliste(m)}
    lauf["c12_speichern"] = g
    alle_zu(app)


# ---------------------------------------------------------------------------------------------------- Zeile d


def koerper(model) -> list:
    return list(model.GetBodies2(0, False) or ())


def beschreibe(b) -> dict:
    m = b.GetMassProperties(1.0)  # Dichte egal; [cx, cy, cz, Volumen, Fläche, Masse, …]
    box = b.GetBodyBox()
    return {"volumen_mm3": round(m[3] * 1e9, 6), "box_mm": [round(x * 1000, 4) for x in box],
            "flaechen": b.GetFaceCount()}


def minus(ziele_von, werkzeuge_von) -> dict:
    """Alle Körper von ziele_von minus alle Körper von werkzeuge_von, nur an Kopien."""
    t = time.monotonic()
    rest, codes = [k.Copy2(True) for k in koerper(ziele_von)], []
    for werkzeug in koerper(werkzeuge_von):
        neu = []
        for ziel in rest:
            sicherung = ziel.Copy2(True)   # Operations2 verbraucht beide Körper, auch wenn nichts getroffen wird
            # IBody2 kommt mit Typinfo: der Ausgabeparameter wird als Zahl übergeben und kommt als (Ergebnis, Code) zurück
            r, code = ziel.Operations2(SW_BODY_CUT, werkzeug.Copy2(True), 0)
            codes.append(code)
            if code == 0 and r:
                neu.extend(r)
            elif code == 0 and not r:
                pass             # leer: Ziel liegt ganz im Werkzeug bzw. beide gleich
            else:
                neu.append(sicherung)  # Code merken, Ziel unverändert weiterführen
        rest = neu
    return {"koerper": rest, "codes": codes, "s": round(time.monotonic() - t, 3)}


def differenz(a, b) -> dict:
    links, rechts = minus(a, b), minus(b, a)
    return {"a_minus_b": [beschreibe(k) for k in links["koerper"]], "b_minus_a": [beschreibe(k) for k in rechts["koerper"]],
            "codes": [links["codes"], rechts["codes"]], "s": [links["s"], rechts["s"]]}


def aendere_kleine_bohrung(app, model) -> None:
    """Ø1 × 2 bei (45, 25) von der Oberseite."""
    model.ClearSelection2(True)
    model.Extension.SelectByRay(mm(45), mm(25), mm(21), 0, 0, -1, 0.0005, 2, False, 0, 0)
    model.SketchManager.InsertSketch(True)
    sm = model.SketchManager
    mu = app.GetMathUtility
    mu._FlagAsMethod("CreatePoint")
    from swki.verbindung import r8_array
    u, v, _ = mu.CreatePoint(r8_array([mm(45), mm(25), mm(20)])).MultiplyTransform(sm.ActiveSketch.ModelToSketchTransform).ArrayData
    sm.CreateCircleByRadius(u, v, 0.0, mm(0.5))
    sm.InsertSketch(True)
    model.FeatureByPositionReverse(0).Select2(False, 0)
    f = model.FeatureManager.FeatureCut4(True, False, False, 0, 0, mm(2), 0.0, False, False, False, False, 0.0, 0.0, False,
                                         False, False, False, False, True, True, True, True, False, 0, 0.0, False, False)
    if f is None:
        raise RuntimeError("kleine Bohrung nicht erzeugt")


def setze_l(model, wert: float) -> None:
    gl = model.GetEquationMgr
    i = next(i for i in range(gl.GetCount) if gl.GlobalVariable(i))
    gl.SetEquationAndConfigurationOption(i, f'"L" = {wert}', SW_ALLE_KONF, None)
    model.EditRebuild3


def stl_abstand(app, a, b, ordner: Path, name: str) -> dict:
    """Rückfall ohne Ausrichtung: beidseitiger Oberflächenabstand aus je 30000 Stichprobenpunkten (mm)."""
    import numpy as np

    from swki.pruefung.stl import exportiere_stl
    from werkzeuge.messstand.vergleich import Oberflaeche, lade, stichprobe
    t = time.monotonic()
    pa = exportiere_stl(app, a, ordner / f"{name}_a.stl")
    pb = exportiere_stl(app, b, ordner / f"{name}_b.stl")
    t1 = time.monotonic()
    na, nb = lade(pa), lade(pb)
    rng = np.random.default_rng(0)
    dab = Oberflaeche(nb.triangles).abstand(stichprobe(na, 30000, rng))[0]
    dba = Oberflaeche(na.triangles).abstand(stichprobe(nb, 30000, rng))[0]
    d = np.concatenate([dab, dba])
    return {"max_mm": round(float(d.max()), 5), "p99_mm": round(float(np.percentile(d, 99)), 5),
            "ueber_0_01": int((d > 0.01).sum()), "export_s": round(t1 - t, 2), "abstand_s": round(time.monotonic() - t1, 2),
            "dreiecke": [len(na.faces), len(nb.faces)]}


def zeile_d(app) -> None:
    lauf = Lauf(app, "d")
    basis = frisch("d")
    alle_zu(app)
    vorher_ordner = bestuecke(basis / "bestand", TEIL)
    vorher = vorher_ordner / "vorher_Lagerdeckel.SLDPRT"
    shutil.copy2(vorher_ordner / TEIL, vorher)

    # Gleicher Titel: Bestand und Lauf gleichnamig zugleich öffnen?
    gleich = bestuecke(basis / "gleichname", TEIL)
    m1, s1 = oeffne(app, vorher_ordner / TEIL)
    m2, s2 = oeffne(app, gleich / TEIL)
    lauf["gleicher_titel"] = {"erstes": s1, "zweites": s2, "zweites_offen": m2 is not None, "offen": offene(app)}
    alle_zu(app)

    def probe(name: str, aendern, unsichtbar=True, konfig=None, stl=True) -> dict:
        o = bestuecke(basis / name, TEIL)
        m, s = oeffne(app, o / TEIL)
        if aendern:
            aendern(m)
            m.EditRebuild3
            speichern(m)
        alle_zu(app)
        if unsichtbar:
            app.DocumentVisible(False, SW_DOC_PART)
        try:
            a, sa = oeffne(app, vorher)
            b, sb = oeffne(app, o / TEIL)
        finally:
            app.DocumentVisible(True, SW_DOC_PART)
        d: dict = {"titel": [a.GetTitle, b.GetTitle], "oeffnen": [sa, sb], "mb_vor": round(privat_mb(lauf.pid))}
        for k in konfig or ("Standard",):
            a.ShowConfiguration2(k)
            b.ShowConfiguration2(k)
            d[k] = differenz(a, b) | {"volumen": [volumen(a), volumen(b)]}
        d["mb_nach"] = round(privat_mb(lauf.pid))
        lauf[name] = d
        alle_zu(app)
        if stl:   # STL-Export aus einem unsichtbaren Dokument bringt SolidWorks zum Absturz (RPC, zweimal belegt)
            a, _ = oeffne(app, vorher)
            b, _ = oeffne(app, o / TEIL)
            d["stl"] = stl_abstand(app, a, b, o, "st")
            lauf[name] = d
            alle_zu(app)
        return d

    probe("gleich", None, konfig=("Standard", "Variante B"))
    probe("gleich_gespeichert", lambda m: None)
    probe("bohrung", lambda m: aendere_kleine_bohrung(app, m), konfig=("Standard", "Variante B"))
    probe("flaeche_50um", lambda m: setze_l(m, 100.05))
    probe("flaeche_5um", lambda m: setze_l(m, 100.005))
    probe("flaeche_0_5um", lambda m: setze_l(m, 100.0005), stl=False)
    probe("flaeche_0_05um", lambda m: setze_l(m, 100.00005), stl=False)
    probe("loch_versetzt_20um", lambda m: m.Parameter("D2@Skizze3").SetSystemValue3(mm(40.02), SW_WERT_ALLE, None))
    probe("nur_variante_b", lambda m: m.Parameter(f"D1@{TAB}").SetSystemValue3(mm(9), SW_WERT_BENANNT, namen(["Variante B"])),
          konfig=("Standard", "Variante B"), stl=False)
    probe("sichtbar_gleich", None, unsichtbar=False, stl=False)
    alle_zu(app)

    # Mehrkörper-Teil mit vielen Flächen (importiertes gm42-10), gleich gegen gleich und gegen sich selbst geändert
    motor = bestuecke(basis / "motor", STEPTEIL)
    v2 = motor / "vorher_gm42.SLDPRT"
    shutil.copy2(motor / STEPTEIL, v2)
    app.DocumentVisible(False, SW_DOC_PART)
    try:
        a, sa = oeffne(app, v2)
        b, sb = oeffne(app, motor / STEPTEIL)
    finally:
        app.DocumentVisible(True, SW_DOC_PART)
    g = {"flaechen": [k.GetFaceCount() for k in koerper(a)], "volumen": volumen(a)}
    mb = privat_mb(lauf.pid)
    g["differenz"] = differenz(a, b)
    g["mehr_mb"] = round(privat_mb(lauf.pid) - mb)
    lauf["mehrkoerper_gleich"] = g
    alle_zu(app)

    # Bild mit Differenzkörpern
    o = S18 / "d" / "bohrung"
    a, _ = oeffne(app, vorher)
    b, _ = oeffne(app, o / TEIL)
    from swki.pruefung.bilder import _aufnahme
    from swki.compiler import sw
    rest = minus(b, a)["koerper"] + minus(a, b)["koerper"]
    b.ActiveView  # Ansicht vorhanden
    rot = 0x0000FF
    a_titel = a.GetTitle
    app.CloseDoc(a_titel)
    e = byref_long()
    b = app.ActivateDoc3(TEIL, False, 0, e)
    anzeigen = [k.Display3(b, rot, 0) for k in rest]
    b._FlagAsMethod("ViewZoomtofit2")
    with _aufnahme(app, b):
        b.ShowNamedView2("", 7)
        b.ViewZoomtofit2()
        sw.speichere(b, S18 / "d" / "differenz.png", kopie=True)
    lauf["bild"] = {"koerper": len(rest), "display": anzeigen, "pfad": str(S18 / "d" / "differenz.png")}
    del rest
    alle_zu(app)


# ---------------------------------------------------------------------------------------------------- Zeile e


def zeile_e(app) -> None:
    from swki.compiler import sw
    from swki.pruefung.bilder import _aufnahme
    lauf = Lauf(app, "e")
    basis = frisch("e")
    alle_zu(app)
    o = bestuecke(basis / "k", TEIL)
    m, s = oeffne(app, o / TEIL)
    m._FlagAsMethod("ViewZoomtofit2")
    m._FlagAsMethod("EditSketch")

    def bild(name: str) -> str:
        pfad = basis / f"{name}.png"
        sw.speichere(m, pfad, kopie=True)
        return str(pfad)

    with _aufnahme(app, m):
        m.ShowNamedView2("", 7)
        m.ViewZoomtofit2()
        d = {"ohne": bild("ohne")}
        m.FeatureByName("Schnitt-Linear austragen2").Select2(False, 0)
        d["feature"] = bild("feature")
        m.ClearSelection2(True)
        ok = m.Extension.SelectByID2(f"D2@Skizze3@{TEIL}", "DIMENSION", 0, 0, 0, False, 0, callout_leer(), 0)
        d["mass_auswahl"] = ok
        d["mass_nur_auswahl"] = bild("mass_nur_auswahl")
        m.ClearSelection2(True)
        # Beschriftungen einschalten (nur im offenen Dokument, es wird nicht gespeichert)
        d["toggles"] = [m.Extension.SetUserPreferenceToggle(31, 0, True), m.Extension.SetUserPreferenceToggle(32, 0, True)]
        f = m.FeatureByName("Skizze3")
        dd = f.GetFirstDisplayDimension
        while dd is not None and massname(dd.GetDimension2(0)) != "D2@Skizze3":
            dd = f.GetNextDisplayDimension(dd)
        ann = dd.GetAnnotation
        d["annotation"] = {"sichtbar": ann.Visible, "name": ann.GetName}
        d["ann_auswahl"] = ann.Select3(False, callout_leer())
        d["mass_annotation"] = bild("mass_annotation")
        m.ClearSelection2(True)
        # Skizze öffnen: Maße sind dort sichtbar
        f.Select2(False, 0)
        m.EditSketch()
        d["aktiv"] = m.SketchManager.ActiveSketch is not None
        m.ViewZoomtofit2()
        f2 = m.FeatureByName("Skizze3")
        dd = f2.GetFirstDisplayDimension
        while dd is not None and massname(dd.GetDimension2(0)) != "D2@Skizze3":
            dd = f2.GetNextDisplayDimension(dd)
        d["skizze_auswahl"] = dd.GetAnnotation.Select3(False, callout_leer())
        d["mass_in_skizze"] = bild("mass_in_skizze")
        m.ClearSelection2(True)
        m.SketchManager.InsertSketch(True)
        d["fehler_danach"] = fehlerliste(m)
        d["veraendert"] = m.GetSaveFlag
    lauf["bilder"] = d
    alle_zu(app)


def zeile_e2(app) -> None:
    """Zweiter Anlauf zu e: Beschriftungen an, Ansicht zur Skizzenebene, Auswahl auf beiden Wegen, dann Farbe."""
    from swki.compiler import sw
    from swki.pruefung.bilder import _aufnahme
    lauf = Lauf(app, "e2")
    basis = frisch("e2")
    alle_zu(app)
    o = bestuecke(basis / "k", TEIL)
    m, s = oeffne(app, o / TEIL)
    m._FlagAsMethod("ViewZoomtofit2")
    d = {"oeffnen": s, "toggles": [m.Extension.SetUserPreferenceToggle(31, 0, True),
                                   m.Extension.SetUserPreferenceToggle(32, 0, True)], "flag_vor": m.GetSaveFlag}

    def bild(name: str) -> str:
        pfad = basis / f"{name}.png"
        sw.speichere(m, pfad, kopie=True)
        return str(pfad)

    def anzeige(feature: str, name: str):
        f = m.FeatureByName(feature)
        dd = f.GetFirstDisplayDimension
        while dd is not None and massname(dd.GetDimension2(0)) != name:
            dd = f.GetNextDisplayDimension(dd)
        return dd

    with _aufnahme(app, m):
        m.ShowNamedView2("", 1)  # vorne: Blick auf die Skizzenebene der Platte
        m.ViewZoomtofit2()
        d["a_ohne_auswahl"] = bild("a_ohne_auswahl")
        d["selectbyid"] = m.Extension.SelectByID2(f"D2@Skizze3@{TEIL}", "DIMENSION", 0, 0, 0, False, 0, callout_leer(), 0)
        d["auswahl_anzahl_typ"] = [m.SelectionManager.GetSelectedObjectCount2(-1), m.SelectionManager.GetSelectedObjectType3(1, -1)]
        d["b_selectbyid"] = bild("b_selectbyid")
        m.ClearSelection2(True)
        ann = anzeige("Skizze3", "D2@Skizze3").GetAnnotation
        d["select3_leer"] = ann.Select3(False, callout_leer())
        m.ClearSelection2(True)
        d["select3_daten"] = ann.Select3(False, m.SelectionManager.CreateSelectData)
        d["c_select3"] = bild("c_select3")
        m.ClearSelection2(True)
        d["farbe_alt"] = ann.Color
        ann.Color = 0x0000FF
        d["farbe_neu"] = ann.Color
        d["d_farbe"] = bild("d_farbe")
        # Maß eines Features in der Isometrie
        m.ShowNamedView2("", 7)
        m.ViewZoomtofit2()
        ann2 = anzeige(TAB, f"D1@{TAB}").GetAnnotation
        ann2.Color = 0x0000FF
        d["e_feature_mass"] = bild("e_feature_mass")
        d["flag_nach"] = m.GetSaveFlag
        d["fehler"] = fehlerliste(m)
    lauf["bilder"] = d
    alle_zu(app)
    vorher = sha(MUSTER / TEIL)
    lauf["kopie_unveraendert"] = sha(o / TEIL) == vorher


# ---------------------------------------------------------------------------------------------------- Zeile g


def zeile_g(app) -> None:
    lauf = Lauf(app, "g")
    basis = frisch("g")
    alle_zu(app)
    orig = bestuecke(basis / "orig")
    a, s = oeffne(app, orig / ASM)
    lauf["vorbereiten"] = s | {"speichern": speichern(a), "pfade": [k.GetPathName for k in a.GetComponents(True) or ()]}
    alle_zu(app)
    dateien = (TEIL, ASM, STEPTEIL)
    sha_orig = {n: sha(orig / n) for n in dateien}

    # Weg 1: Datei-Kopie aller Dateien, Baugruppe liegt daneben; nur das geänderte Teil speichern
    w1 = basis / "weg1"
    w1.mkdir()
    for n in dateien:
        shutil.copy2(orig / n, w1 / n)
    d = {"abh_ohne_suche": app.GetDocumentDependencies2(str(w1 / ASM), True, False, False),
         "abh_mit_suche": app.GetDocumentDependencies2(str(w1 / ASM), True, True, False)}
    a, s = oeffne(app, w1 / ASM)
    d["oeffnen"] = s
    d["pfade"] = [k.GetPathName for k in a.GetComponents(True) or ()]
    d["offen"] = offene(app)
    deckel = next(k for k in a.GetComponents(True) if k.Name2.startswith("Lagerdeckel"))
    d["zustand"] = deckel.GetSuppression2
    teil = deckel.GetModelDoc2
    d["modelldoc_da"] = teil is not None
    if teil is None:   # leicht geladen: das Teil unter seinem Pfad im Lauf-Ordner öffnen
        teil, d["teil_oeffnen"] = oeffne(app, w1 / TEIL)
    d["setzen"] = teil.Parameter(f"D1@{TAB}").SetSystemValue3(mm(9), SW_WERT_ALLE, None)
    d["teil_rebuild"] = teil.EditRebuild3
    d["teil_speichern"] = speichern(teil)
    d["baugruppe_dirty"] = a.GetSaveFlag
    alle_zu(app)
    d["sha_gleich"] = {n: sha(w1 / n) == sha_orig[n] for n in dateien}
    d["orig_unveraendert"] = {n: sha(orig / n) == sha_orig[n] for n in dateien}
    d["erneut"] = baugruppe_probe(app, w1 / ASM)
    d["sha_nach_nur_lesen"] = {n: sha(w1 / n) == sha_orig[n] for n in dateien}
    lauf["weg1_dateikopie"] = d

    # Baugruppe speichern: was steht dann als Pfad drin, ändert sich ein Teil?
    a, s = oeffne(app, w1 / ASM)
    a.EditRebuild3
    v = {n: sha(w1 / n) for n in dateien}
    e = {"speichern": speichern(a)}
    alle_zu(app)
    e["geaendert"] = {n: v[n] != sha(w1 / n) for n in dateien}
    e["abh_ohne_suche"] = app.GetDocumentDependencies2(str(w1 / ASM), True, False, False)
    lauf["weg1_baugruppe_speichern"] = e

    # Zurückkopiert neben die alte Baugruppe: Kollege öffnet orig/Muster mit neuem Lagerdeckel (Etappe-2-Ausgabe)
    z = basis / "zurueck"
    z.mkdir()
    for n in dateien:
        shutil.copy2(orig / n, z / n)
    shutil.copy2(w1 / TEIL, z / TEIL)
    lauf["zurueckkopiert_neben_baugruppe"] = baugruppe_probe(app, z / ASM)

    # Weg 2: Pack and Go aus einer Bestandskopie (Quelle ist hier orig als Stellvertreter einer Bestandskopie)
    b = basis / "bestand"
    b.mkdir()
    for n in dateien:
        shutil.copy2(orig / n, b / n)
    a, s = oeffne(app, b / ASM)
    # GetPackAndGo hat laut Index 0 Parameter, per IDispatch meldet es aber in jeder Form „Parameter nicht optional"
    # (Methode, Property-Get, InvokeTypes). Weg 1 reicht und braucht kein geöffnetes Dokument: Pack and Go bleibt ungenutzt.
    ext = a.Extension
    dispid = ext._oleobj_.GetIDsOfNames("GetPackAndGo")
    versuche = {}
    for name, flags in (("methode", pythoncom.DISPATCH_METHOD), ("get", pythoncom.DISPATCH_PROPERTYGET)):
        try:
            versuche[name] = str(ext._oleobj_.Invoke(dispid, 0, flags, 1))
        except pythoncom.com_error as x:
            versuche[name] = x.strerror
    lauf["weg2_pack_and_go"] = versuche
    alle_zu(app)

    # Komponenten leicht geladen (Zustand 1, GetModelDoc2 = None)? Mit swOpenDocOptions_OverrideDefaultLoadLightweight = 64
    a, s = oeffne(app, basis / "weg1" / ASM, SW_OPEN_SILENT | 64)
    lauf["voll_laden"] = s | {"zustand": [(k.Name2, k.GetSuppression2, k.GetModelDoc2 is not None)
                                          for k in a.GetComponents(True) or ()], "standard_leicht": app.GetUserPreferenceToggle(25)}
    alle_zu(app)

    # Weg 3: Datei-Kopie, Pfade ohne Öffnen umbiegen (ReplaceReferencedDocument)
    w3 = basis / "weg3"
    w3.mkdir()
    for n in dateien:
        shutil.copy2(orig / n, w3 / n)
    d = {"ersetzen": [app.ReplaceReferencedDocument(str(w3 / ASM), str(orig / n), str(w3 / n)) for n in (TEIL, STEPTEIL)]}
    d["sha_asm_gleich"] = sha(w3 / ASM) == sha_orig[ASM]
    d["abh_ohne_suche"] = app.GetDocumentDependencies2(str(w3 / ASM), True, False, False)
    d["offen"] = offene(app)
    d["probe"] = baugruppe_probe(app, w3 / ASM)
    d["orig_unveraendert"] = {n: sha(orig / n) == sha_orig[n] for n in dateien}
    lauf["weg3_ersetzen"] = d


# ---------------------------------------------------------------------------------------------------- Zeile t


def zeile_t(app) -> None:
    """Konstruktionstabelle: im Haus unüblich (F4), aber swki muss sie erkennen, ohne Excel zu starten."""
    lauf = Lauf(app, "t")
    basis = frisch("t")
    alle_zu(app)
    o = bestuecke(basis / "k", TEIL)
    tabelle = basis / "tabelle.xlsx"
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    wb = excel.Workbooks.Add()
    ws = wb.Worksheets(1)
    ws.Cells(1, 2).Value = f"D1@{TAB}"
    ws.Cells(2, 1).Value = "Standard"
    ws.Cells(2, 2).Value = 8
    ws.Cells(3, 1).Value = "Variante B"
    ws.Cells(3, 2).Value = 6
    wb.SaveAs(str(tabelle), 51)
    wb.Close(False)
    excel.Quit()
    del ws, wb, excel
    time.sleep(2)
    m, s = oeffne(app, o / TEIL)
    d = {"vorher_hat_tabelle": m.Extension.HasDesignTable, "vorher_get": m.GetDesignTable is not None}
    d["einfuegen"] = m.InsertFamilyTableOpen(str(tabelle))
    lauf["einfuegen"] = d
    d["nachher_hat_tabelle"] = m.Extension.HasDesignTable
    d["baum"] = baumnamen(m)
    d["ordner"] = [f"{f.Name}|{f.GetTypeName2}" for f in _alle_features(m)][:14]
    lauf["einfuegen"] = d
    d["speichern"] = speichern(m)
    lauf["einfuegen"] = d
    alle_zu(app)
    time.sleep(1)
    excel_vor = _excel_prozesse()
    m, s = oeffne(app, o / TEIL)
    e = {"oeffnen": s, "hat_tabelle": m.Extension.HasDesignTable}
    e["masse"] = {}
    for k in m.GetConfigurationNames:
        m.ShowConfiguration2(k)
        p = m.Parameter(f"D1@{TAB}")
        e["masse"][k] = {"wert": p.GetSystemValue3(SW_WERT_DIESE, None), "tabelle": p.IsDesignTableDimension,
                         "driven": p.DrivenState, "readonly": p.ReadOnly}
    p2 = m.Parameter("D2@Skizze2")
    e["anderes_mass"] = {"tabelle": p2.IsDesignTableDimension}
    e["excel"] = [excel_vor, _excel_prozesse()]
    e["typen"] = sorted({f.GetTypeName2 for f in _alle_features(m)})
    lauf["lesen"] = e
    alle_zu(app)


def zeile_t2(app) -> None:
    """Nach `t` auf frischem SolidWorks: startet das Lesen Excel? Kopfzeile der Tabelle lesbar? Dazu: Wo bleiben die
    14 s von lies() (Zeile b), und geht lies() am unsichtbaren Dokument?"""
    lauf = Lauf(app, "t2")
    alle_zu(app)
    pfad = S18 / "t" / "k" / TEIL
    d = {"excel_vor": _excel_prozesse()}
    m, s = oeffne(app, pfad)
    d |= {"oeffnen": s, "hat": m.Extension.HasDesignTable, "tabelle_mass": m.Parameter(f"D1@{TAB}").IsDesignTableDimension,
          "excel_nach_oeffnen": _excel_prozesse()}
    lauf["lesen"] = d
    dt = m.GetDesignTable
    try:
        d["ohne_attach"] = {"spalten": dt.GetTotalColumnCount, "zeilen": dt.GetTotalRowCount}
    except Exception as x:
        d["ohne_attach"] = repr(x)
    d["excel_nach_zaehlen"] = _excel_prozesse()
    lauf["lesen"] = d
    try:
        d["kopf"] = [dt.GetHeaderText(i) for i in range(0, 3)]
    except Exception as x:
        d["kopf"] = repr(x)
    d["excel_nach_kopf"] = _excel_prozesse()
    lauf["lesen"] = d
    alle_zu(app)

    # Zeiten von lies(): sichtbar, dann unsichtbar
    o = bestuecke(frisch("t2") / "k", TEIL)
    for art in ("sichtbar", "unsichtbar"):
        if art == "unsichtbar":
            app.DocumentVisible(False, SW_DOC_PART)
        mb0 = privat_mb(lauf.pid)
        m, s = oeffne(app, o / TEIL)
        app.DocumentVisible(True, SW_DOC_PART)
        z = {"oeffnen": s, "mehr_mb": round(privat_mb(lauf.pid) - mb0)}
        t = time.monotonic()
        for k in ("Variante B", "Standard"):
            m.ShowConfiguration2(k)
        z["umschalten_2x_s"] = round(time.monotonic() - t, 3)
        t = time.monotonic()
        n = sum(1 for _ in alle_masse(m))
        z["masse_laufen_s"] = round(time.monotonic() - t, 3)
        z["anzahl"] = n
        t = time.monotonic()
        for f, dd in alle_masse(m):
            dd.GetDimension2(0).ReferencePoints
        z["referenzpunkte_s"] = round(time.monotonic() - t, 3)
        t = time.monotonic()
        skizzenstatus(m)
        z["skizzenstatus_s"] = round(time.monotonic() - t, 3)
        t = time.monotonic()
        lies(app, m)
        z["lies_s"] = round(time.monotonic() - t, 2)
        z["aktiv_danach"] = m.ConfigurationManager.ActiveConfiguration.Name
        lauf[art] = z
        alle_zu(app)


def _alle_features(model):
    f = model.FirstFeature
    while f is not None:
        yield f
        f = f.GetNextFeature


def _excel_prozesse() -> int:
    import subprocess
    aus = subprocess.run(["tasklist", "/FI", "IMAGENAME eq EXCEL.EXE", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                         encoding="oem").stdout
    return sum("EXCEL" in z.upper() for z in aus.splitlines())


ZEILEN = {"a": zeile_a, "b": zeile_b, "c": zeile_c, "c2": zeile_c2, "c3": zeile_c3, "d": zeile_d, "e": zeile_e, "e2": zeile_e2,
          "g": zeile_g, "t": zeile_t, "t2": zeile_t2}


def main() -> None:
    zeile = sys.argv[1]
    app = verbinde(R.sw_jahr)
    alt = app.GetUserPreferenceToggle(10)
    app.SetUserPreferenceToggle(10, False)  # swInputDimValOnCreate: kein Dialog beim Bemaßen
    try:
        ZEILEN[zeile](app)
    except Exception:
        print(traceback.format_exc())
        (ERGEBNIS / f"s18_{zeile}.fehler.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        app.SetUserPreferenceToggle(10, alt)
        alle_zu(app)
    print((ERGEBNIS / f"s18_{zeile}.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
