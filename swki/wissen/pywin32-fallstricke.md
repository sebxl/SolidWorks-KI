# pywin32 + SolidWorks: geprüfte Muster

Stand: 2026-09-27, SW 2025, Python 3.14. Nur Einträge, die in `docs/stufe0/ergebnisse.md` und den
zugehörigen `docs/stufe0/ergebnisse/*.json` belegt sind.

## Verbindung

- An laufendes SolidWorks hängen: `win32com.client.GetActiveObject("SldWorks.Application.<rev>")`
  (`swki.verbindung.verbinde`).
- Binding: **Late Binding** (dynamischer Dispatch über `GetActiveObject`) funktioniert einwandfrei
  unter Python 3.14 (S1). **Early Binding** über `win32com.client.gencache.EnsureDispatch` auf ein
  bereits laufendes Objekt schlägt fehl (`TypeError("This COM object can not automate the makepy
  process - please run makepy manually for this object")`) – `gencache` kann für ein schon
  existierendes OLE-Objekt keine passende generierte Wrapperklasse automatisch erzeugen; müsste
  vorher explizit per `makepy`/`EnsureModule` generiert werden. Für Stufe 0/1/2 nicht nötig, da Late
  Binding ausreicht.
- **Echtes Early Binding (S8: `gencache.EnsureModule(sldworks.tlb)` + `CastTo`) wurde getestet und
  bringt keinen Vorteil:** `EnsureModule` selbst funktioniert (Cache unter `%TEMP%\gen_py\<py-version>`,
  ein echter Kaltstart dauert für `sldworks.tlb` ca. 2,2 s, für das kleinere `swconst.tlb` ca. 0,1 s;
  jeder weitere Aufruf im selben Prozess danach unter 5 ms). Aber: `CastTo(app, "ISldWorks")` auf das
  laufende Application-Objekt liefert scheinbar erfolgreich ein `ISldWorks`-Objekt, dessen `_oleobj_`
  jedoch fälschlich auf das CoClass-Objekt selbst zeigt (nicht auf einen echten IDispatch-Zeiger) –
  jeder Methodenaufruf darauf bricht mit `AttributeError("... object has no attribute
  'InvokeTypes'")`. Grund: `DispatchBaseClass.__init__` prüft nur `isinstance(oobj, (DispatchBaseClass,
  PyIDispatchType))`; ein CoClass-Objekt (wie das von `GetActiveObject` nach vorherigem `EnsureModule`
  automatisch getypt zurückgegebene `app`) erfüllt keine der beiden Bedingungen. Funktionierender
  Workaround: `CastTo(app._dispobj_, "ISldWorks")` (das intern vom CoClass-Wrapper gehaltene
  `DispatchBaseClass`-Objekt der Default-Schnittstelle). Wichtiger noch: `CastTo` auf **jedes**
  zurückgegebene Kindobjekt (z. B. `model = app.NewDocument(...)`, `IModelDocExtension`,
  `SketchManager`, `FeatureManager`) scheitert grundsätzlich mit demselben Fehler wie beim
  Application-Objekt in S1 (`can not automate the makepy process`), weil `CastTo` dafür intern
  `gencache.EnsureDispatch(ob)` aufruft, was `ob._oleobj_.GetTypeInfo()` braucht – und SOLIDWORKS-
  COM-Objekte liefern `GetTypeInfo()` grundsätzlich nicht nutzbar (nicht nur für die Application,
  für das gesamte Objektmodell). Diese Kindobjekte bleiben daher **immer** dynamisch (spät)
  gebunden, mit denselben Klammer-/VARIANT-Regeln wie bisher (siehe unten) – unabhängig davon, ob
  `EnsureModule` vorher aufgerufen wurde. Bei früh gebundenen Objekten (Application-Handle über den
  Workaround) gilt für nullargumentige Member die **umgekehrte** Regel: MIT `()` aufrufen (echte
  Python-`def`-Methoden, kein automatischer Attributzugriffs-Call). `swconst`-Enum-Konstanten sind
  nach `EnsureModule(swconst.tlb)` per Name nutzbar (`win32com.client.constants.swEndCondBlind` etc.,
  stimmen mit dem lokalen API-Index überein) – der einzige verifizierte Zusatznutzen, aber ohne
  `CastTo` erreichbar und mit geringem Mehrwert gegenüber `swki api enum`. Fazit: Late Binding bleibt
  gesetzt. Details/Rohdaten: `docs/stufe0/ergebnisse/s8_early_binding.json`.

## Einheiten

- API: Meter, Radiant, m³. Hilfen: `swki.verbindung.mm` / `in_mm` / `in_mm3` / `grad`.

## Auswahl ohne Namen (deutsche Oberfläche)

- Standardebenen: erste drei `RefPlane`-Features liefern sprachunabhängig „Ebene vorne“,
  „Ebene oben“, „Ebene rechts“ (S2).
- Flächen: `IModelDocExtension.SelectByRay` (S6).

## Parameter-Eigenheiten

- Callout: `callout_leer()` = `VARIANT(VT_DISPATCH, None)`. Nötig für `System.Object`-Parameter,
  die laut Doku optional sind: rohes Python-`None` löst dort `com_error(-2147352571,
  'Typenkonflikt.')` aus. Belegt für `ISketchManager.FullyDefineSketch` (`HorizontalDatumDisp`/
  `VerticalDatumDisp`, S3) und `IComponent2.Select4` (`Data`, S5).
- ByRef-long (z. B. `ErrorStatus`): `byref_long()`; Wert danach in `.value`.
- **Nullargumentige COM-Member ohne `()` aufrufen:** pywin32s dynamischer Dispatch ruft
  nullargumentige Member (unabhängig davon, ob die VBA-Doku sie als `Function` oder `Sub` führt und
  unabhängig vom Rückgabetyp) bereits beim reinen Attributzugriff auf. Ein zusätzliches `()` versucht
  dann, das bereits zurückgegebene Ergebnis selbst aufzurufen, und scheitert:
  - liefert der Member ein COM-Objekt: `com_error('Mitglied nicht gefunden.')`, weil jedes
    `win32com.client.CDispatch`-Objekt selbst `__call__` definiert (COM-Default-Member), das
    zurückgegebene Objekt aber keinen eigenen Default-Member hat. Belegt für
    `IModelDoc2.FirstFeature`, `IFeature.GetNextFeature` (S2/S3/S4), `IFeature.GetSpecificFeature2`
    (S3), `IModelDocExtension.CreateMassProperty` (S4), `IAssemblyDoc.InterferenceDetectionManager`
    (S5).
  - liefert der Member einen primitiven Wert (z. B. `bool`): `TypeError("'bool' object is not
    callable")`. Belegt für `IModelDoc2.EditRebuild3` (S6). `IModelDoc2.ViewZoomtofit2` (Sub ohne
    Argumente) wurde in S4 nur ohne `()` angesprochen (kein Aufruf mit `()` protokolliert, also
    keine Exception dafür belegt) – aus Vorsicht ebenfalls ohne `()` verwenden.

  **`swki.verbindung.wert()` ist für diesen Fall NICHT geeignet** (Ruling R11): `wert()` prüft nur
  `callable(x)`, und jedes COM-Objekt ist wegen `__call__` `callable` – auch ein bereits fertiges
  Ergebnis. `wert()` würde es also fälschlich nochmal aufrufen. `wert()` eignet sich nur für
  Getter/Properties mit **primitivem** Rückgabewert, bei denen kein COM-Objekt zurückkommt (z. B.
  `RevisionNumber`, `GetTitle`). Für nullargumentige Member, die ein COM-Objekt liefern, reinen
  Attributzugriff ohne `wert()` und ohne `()` verwenden, z. B. `model.FirstFeature` statt
  `wert(model.FirstFeature)` oder `model.FirstFeature()`.
- `IAssemblyDoc.AddComponent5` (`X`/`Y`/`Z`): positioniert laut API-Doku das **Zentrum der
  Bauteil-Bounding-Box**, nicht den Bauteil-Ursprung (S6, live per `Transform2` vor/nach dem Mate
  nachgemessen: konstanter Versatz von der halben Bauteiltiefe). Wer eine Komponente an einer
  bestimmten Ursprungsposition braucht, muss den Bounding-Box-Versatz selbst herausrechnen oder nach
  dem Einfügen per `Component2.Transform2`/Mates exakt positionieren.

## Aufrufketten Stufe 2 (S9a/S9b, live belegt)

Details und kopierfertige Aufrufe: `docs/stufe0/ergebnisse/s9a_b*.json`, `s9b_b*.json`, Spikes
`spikes/s9a_*.py`, `spikes/s9b_*.py`.

- **Late Binding erzwingen** (auch bei vorhandenem gen_py-Cache): `pythoncom.GetActiveObject(progid)` →
  `win32com.client.dynamic.Dispatch(unk.QueryInterface(pythoncom.IID_IDispatch))` (S9a-0).
- **Nicht jedes Objekt folgt der „ohne ()“-Regel:**
  - `IBody2` (aus `GetBodies2`) liefert Typinfo → nullargumentige Methoden **mit** `()`:
    `body.GetFaces()`, `body.GetType()`; ohne `()` nur gebundene Methode (S9b-14/19).
  - `IModelDoc2.EditSketch` ohne `()` → gebundene Methode, nichts passiert (S9b-19).
  - Methoden mit Argumenten, die SW auch argumentlos beantwortet, laufen schon beim Attributzugriff:
    `IMathUtility.CreatePoint` (S9a-2), `IMeasure.Calculate` (S9b-19) → vorher
    `obj._FlagAsMethod("Name")`.
  - Robuste Prüfung: `isinstance(x, types.MethodType)` → dann `x()`.
- **Arrays an COM immer als VARIANT:** `VARIANT(VT_ARRAY|VT_R8, …)` für Zahlen (rohe Liste liefert bei
  `CreatePoint` stillschweigend Müll, S9a-2), `VARIANT(VT_ARRAY|VT_DISPATCH, …)` für Objekte (rohe
  Liste bei `ISimpleFilletFeatureData2.Edges` wird ignoriert, S9b-12).
- ByRef-Ausgaben: `VARIANT(VT_BYREF|VT_VARIANT, None)` (Arrays, `GetWhatsWrong`), `…|VT_BOOL`
  (`GetErrorCode2`), `…|VT_I4` (`SaveAs3`/`OpenDoc6`), `…|VT_BSTR` (`Get6`,
  `GetMaterialPropertyName2`); Wert in `.value` (S9a-11, S9b).
- Parametrisierte Property-Put (`IEquationMgr.Equation`) nur per rohem
  `_oleobj_.Invoke(dispid, 0, DISPATCH_PROPERTYPUT, False, idx, wert)` (S9a-5).
- Selektion: `entity.Select4(append, selectData)` mit `SelectionManager.CreateSelectData` + `.Mark`
  funktioniert direkt auf Face/Edge/Feature/Skizzensegment (S9a-10). Marken: Fillet-Kanten 1,
  Muster Richtung 1/2 + Feature 4, Kreismuster Achse 1 + Feature 4, Spiegeln Feature 1 + Ebene 2
  (S9b-12…16). CreateDefinition-Muster lesen die **Vorselektion** bei `CreateFeature`; nur
  Properties ohne Selektion → `None` (S9b-14).
- `ISketchManager.AddToDB = True` beim Skizzieren (sonst ungewollte Inferenz-Relationen), im
  `finally` zurücksetzen (S9a-3).
- Äußere Flächennormale nur über `IFace2.Normal`, nicht `PlaneParams` (S9a-10). Maße und
  Zylinderflächen nie über Reihenfolge zuordnen (S9a-9/11).
- **Stille Fehlschläge** (Rückgabe prüfen, Ergebnis nachmessen):
  - `FeatureCut4` ohne Material → `None` (S9a-7).
  - `InsertFeatureChamfer` Typ 16 → leeres Feature, kein Fehlercode; DD-Abstände gehören in
    `Width`/`OtherDist`, nicht `VertexChamDist1/2` (S9b-13).
  - `ICircularPatternFeatureData.EqualSpacing = …` setzt `Spacing` auf 2π zurück → erst
    EqualSpacing, dann Spacing (S9b-15).
  - Muster-Instanzen außerhalb des Körpers: teils nur Warnung (Code 1), teils gar keine Meldung
    (S9b-14). Musterrichtung = `LineParams`-Richtung der Kante.
  - `IPartDoc.SetMaterialPropertyName2` liefert immer `None`; falscher Name → still nichts
    (S9b-17).
  - `HoleWizard5` mit `Diameter = 0.0` → falsches Loch (r 12,7) nur mit Warnung; Normmaß mit `-1`
    (S9b-21).
- `IMassProperty2.UseSystemUnits = False` wirkt erst nach `mp.Recalculate` (dann mm³/g) (S9b-19).
- `IModelDocExtension.SaveAs3` als `.sldprt` benennt das Dokument um → Titel für `CloseDoc` neu
  lesen; `.step`/`.png` nicht (S9b-20). `CloseDoc` schließt auch geänderte Dokumente ohne Dialog
  und ohne zu speichern (S9b-22). `OpenDoc6` auf bereits offene Datei → dasselbe Objekt,
  Warnung 128 `swFileLoadWarning_AlreadyOpen` (S9b-23).

## Bekannte Fehlschläge

- Early Binding (`gencache.EnsureDispatch`) auf ein bereits laufendes SolidWorks-Objekt (S1, siehe
  „Verbindung“ oben).
- `FullyDefineSketch` mit rohem Python-`None` für `HorizontalDatumDisp`/`VerticalDatumDisp`:
  `com_error` „Typenkonflikt“ (arg 6) (S3) → `callout_leer()` verwenden.
- `IComponent2.Select4` mit rohem Python-`None` für `Data`: derselbe „Typenkonflikt“-Fehler (S5) →
  `callout_leer()` verwenden.
- `IModelDoc2.EditRebuild3()` mit Klammern: `TypeError("'bool' object is not callable")` (S6) →
  ohne Klammern (`assy.EditRebuild3`).
- Toolbox-Teil aus Norm+Größe per API erzeugen: keine der fünf Member mit „Toolbox“ im Namen aus
  `sldworks.tlb`/`swconst.tlb` (`IAssemblyDoc.UpdateToolboxComponent`, `IModelDocExtension.ToolboxPartType`,
  `IPackAndGo.IncludeToolboxComponents`, `ISldWorks.Import-`/`ExportToolboxItem`) erzeugt ein Teil (S7).
  Die eigentliche Erzeugungsfunktionalität (Task-Pane, Norm/Größe wählen) liegt in einem eigenen
  Add-in mit eigener Typbibliothek (`SolidWorks.Interop.sldtoolboxconfigureaddin.dll`), die nicht in
  `TYPBIBLIOTHEKEN` steht und daher keine strukturierten `methode`/`enum`-Einträge liefert – **nicht**
  „nicht indiziert“: `toolboxapi.chm` ist als Hilfetext im Index durchsuchbar (`swki api suche`) und
  zeigt die Interfaces `IToolboxConfiguratorAddin`, `IToolBoxConfiguratorApplication`,
  `IPDMDocManager` – aber nur Konfigurator-/PDM-Hooks (`Connect`/`Disconnect`,
  `SetDocumentStatus`, …), keine Methode zum Erzeugen eines Teils (S7). Rückfallweg: manuell
  erzeugen, per `swki normteil aufnehmen` übernehmen.
