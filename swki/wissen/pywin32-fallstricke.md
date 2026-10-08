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

## Stufe 2a: Compiler (live belegt beim Schreiben des Plans und in den Live-Tests)

- **Voll bestimmte Skizzen ohne FullyDefineSketch:** Elemente mit `SketchManager.AddToDB = True` erzeugen und alle Maße selbst
  setzen (Größen per `AddDimension2`, Lage jedes Kennpunkts zum Ursprung per `AddHorizontalDimension2`/`AddVerticalDimension2`,
  bei 0 `SketchAddConstraints("sgVERTICALPOINTS2D"/"sgHORIZONTALPOINTS2D")`, bei (0,0) `"sgCOINCIDENT"`).
  `FullyDefineSketch` lässt mit AddToDB erzeugte Elemente unterbestimmt und bemaßt ohne Bezug relativ zu irgendeinem Element.
- **Ursprungspunkt sprachunabhängig:** Feature mit `GetTypeName2 == "OriginProfileFeature"`, dann
  `Extension.SelectByID2(f"Point1@{name}", "EXTSKETCHPOINT", 0, 0, 0, False, 0, callout_leer(), 0)` und
  `SelectionManager.GetSelectedObject6(1, -1)`.
- **`CreateCenterRectangle` legt den Mittelpunkt nicht verlässlich an** (je nach SolidWorks-Zustand fehlten Mittelpunkt und
  Diagonal-Beziehungen) → `CreateCornerRectangle` und die Ecke bemaßen.
- **`ViewZoomtofit2` und `BlankRefGeom`** nur nach `model._FlagAsMethod(...)` und mit `()`; der reine Attributzugriff passt die
  Ansicht nicht ein.
- **`IPartDoc.FeatureByName(name)`** findet Features im geöffneten Teil (Features heißen wie ihre Spezifikations-ID).
- **Abgebrochene Prozesse** (Zeitlimit, Kill) setzen umgeschaltete Benutzereinstellungen nicht zurück – nach einem Abbruch
  `swInputDimValOnCreate` (Toggle 10) prüfen. Live-Tests deshalb einzeln mit Zeitlimit (`tests/live_einzeln.py`).
- **Lineare Muster** lassen Instanzen außerhalb des Körpers ohne Meldung weg (nur Volumen/Achsen zeigen es).

## PNG-Screenshots: Print capture vs. Screen capture (live belegt 2026-09-29)

- `IModelDocExtension.SaveAs3` auf `.png` rendert je nach System Option "Export > TIF/PSD/JPG/PNG > Output as"
  entweder das tatsächliche Grafikfenster ("Screen capture", `swTiffScreenOrPrintCapture` = 0) oder eine
  Papierseite ("Print capture" = 1, Seitenformat/DPI aus `swTiffPrintPaperSize`/`swTiffPrintDPI`, hier
  vorgefunden: Letter @ 300 dpi = 3300×2550 px, Seitenverhältnis 1,294). `ViewZoomtofit2` zoomt immer auf das
  tatsächliche Grafikfenster (hier 1741×973 px, Seitenverhältnis 1,789) – steht die Export-Option auf "Print
  capture", weicht das gerenderte Bild-Seitenverhältnis vom gezoomten ab, und bei schmal-langen Standard­ansichten
  (z. B. Vorne/Rechts eines flachen, breiten Teils) wird das Teil sichtbar rechts abgeschnitten, obwohl
  `ViewZoomtofit2` korrekt gearbeitet hat. Reproduziert durch Vertauschen der Ansichtsreihenfolge (Beschnitt folgt
  der Teilegeometrie, nicht der Position in der Schleife) und durch testweises Umschalten auf "Screen capture"
  (Beschnitt verschwindet, Bildgröße ändert sich auf die tatsächliche Fenstergröße).
- `swTiffScreenOrPrintCapture` ist ein **System Option**, kein Document Property: `IModelDoc2.Get/SetUserPreferenceIntegerValue`
  (obsolet) und `IModelDocExtension.Get/SetUserPreferenceInteger` liefern dafür `-1` bzw. `False` (live geprüft) –
  nur `ISldWorks.Get/SetUserPreferenceIntegerValue` (App-Ebene, über `swki.verbindung.verbinde`) funktioniert.
  Vor der Bildaufnahme auf `0` setzen und danach den vorgefundenen Wert wiederherstellen (temporär, wie bei
  Toggle 10) – nicht dauerhaft umstellen, da es eine geteilte Einstellung der laufenden SolidWorks-Instanz ist.

## Maßnamen von Features (live belegt 2026-09-28)

- Lineares Muster: `D1`/`D2` Anzahl, `D3`/`D4` Abstand Richtung 1/2 (auch bei nur einer Richtung ist der Abstand `D3`).
- Kreismuster: `D1` Anzahl, `D3` Gesamtwinkel. Fase (Abstand-Winkel): `D1` Abstand, `D2` Winkel.
- Versetzte Referenzebene: `D1@<Ebenenname>`, Betrag; die Richtung steckt im Umkehren-Flag. Der Name ist sprachabhängig
  (`Ebene1`) → aus `IFeature.Name` lesen.
- Extrusion/Schnitt mit Formschräge: `D1` Tiefe bzw. Versatz, `D3` Winkel bei allen Endbedingungen (`D2` gibt es nicht);
  `Ddir1` False baut den Querschnitt „kleiner“ (Spike S16, 2026-10-08).
- Maße eines Features auflisten: `feature.GetFirstDisplayDimension`, `feature.GetNextDisplayDimension(dd)`,
  `dd.GetDimension2(0).FullName` bzw. `.SystemValue`; Wert eines Maßes: `model.Parameter("D3@f3").SystemValue`.

## Stufe 2c: Normbohrungen, Konturen, Endbedingungen (Spike S10, live belegt)

Rohdaten: `docs/stufe0/ergebnisse/s10_f*.json`, Spikes `spikes/s10_*.py`, Befunde und Entscheidungen in
`docs/stufe0/ergebnisse.md` („Stufe 2c: Spike S10“). Umsetzung: `swki/compiler/handler/normbohrung.py`,
`swki/compiler/skizze.py`, `swki/pruefung/messen.py`.

- **HoleWizard5 (27 Parameter):** Value1…Value12 sind je Bohrungsart anders belegt (−1 = Normwert). Rückgelesen und damit
  belegt: Gewinde Value1 = Gewindetiefe (`ThreadDepth` 0,012), Value7 = 2 kosmetisches Gewinde ohne Beschriftung
  (`CosmeticThreadType` 2), Value8 = Gewinde-Ende (0 blind, 1 durch; `ThreadEndCondition`); Zylinder- und Senkschraube
  Value4 = 1 Screw Fit normal (`HoleFit` 1). Durch alles: `EndType` 1 mit Tiefe 0 (`EndCondition` 1); Ausnahme Stift.
- **Stift mit `durch`:** `HoleWizard5` liefert dafür nie ein Feature (Tiefe 0/−1/0,03, Durchmesser −1/9 mm, Screw Fit, Bohrwinkel
  geprüft). Es geht über `FeatureManager.CreateDefinition(25)` (`swFmHoleWzd`) → `InitializeHole(2, 8, 710, "Ø8.0", 1)` →
  Vorselektion (`SelectByRay`) → `CreateFeature(definition)` (1507,964 mm³). Gelesen wird danach `FastenerType2` = −1 (nicht 710,
  per Late Binding nicht setzbar), `Type` = 25, `FastenerSize` „Ø8.0“. Beleg `s10_f1_bohrungsassistent.json`: `enden["stift 8 durch"]`, Entscheidung
  Teil A; Code `normbohrung._stiftloch_durch`.
- **Größen-Strings:** Regelgewinde, Zylinderschraube (ISO 4762) und Senkschraube (ISO 10642) „M8“; Feingewinde „M8x1.0“ (mit „.0“,
  ohne kein Feature), „M12x1.5“; Stift „Ø8.0“ (Ø = U+00D8). Jede andere Schreibweise („8“, „Ø8“, „8.0“, „D8“) liefert still kein
  Feature (`s10_f1_bohrungsassistent.json`: `groessen["stift 8"]`). Bei der Norm `swStandardISODrillSizes` (anderer Standard, wird nicht genutzt) ergibt „Ø8“ ein Loch mit Ø0,18 mm. Auf dem
  `CreateDefinition`-Weg hat ein ungültiger Text vermutlich einen Dialog ausgelöst und SolidWorks hängen lassen (Ursache nicht
  bewiesen) → dort nur Texte aus `swki/wissen/bohrungsnormen.yaml` (`sw_groesse`) verwenden.
- **Mehrere Positionen in einem Feature:** erste Position per `SelectByRay` (Marke 0), dann die Positionsskizze (Unterskizze
  ohne Segmente) mit `Select2` + `InsertSketch(True)` öffnen, weitere Punkte mit `CreatePoint` (`AddToDB = True`), alle Punkte
  zum Ursprung bemaßen und per Gleichung an Parameter binden; vorher Status 2, danach 3 (`s10_f2_positionen.json`: `b_positionsskizze`). Mehrere
  `SelectByRay` mit Marke 0 ergeben nur eine Bohrung. **Danach `ForceRebuild3(True)`:** `EditRebuild3` baut das HoleWzd-Feature
  nach der Skizzenänderung nicht immer neu auf (Messung: vorher 1, `EditRebuild3` 1, `ForceRebuild3` 2 Instanzen; Kommentar in `normbohrung.py`, Regressionstest `tests/live/test_live_normbohrung.py::test_senkschraube_von_unten`).
  `GetSketchPointCount` zählt Skizzenpunkte, nicht Bohrungen (lag bei 2 bei nur einer Bohrung) → der Handler prüft je Position
  eine Zylinderfläche mit Achse durch den Achspunkt. `SelectByRay` trifft die erste Fläche auf dem Strahl: der Treffer wird per
  `ISldWorks.IsSame(gewaehlt, flaeche) == 1` (`swObjectSame`) gegen die gemeinte Fläche geprüft (Absatz davor oder Position
  außerhalb).
- **Bohrungsdaten lesen:** `IFeature.GetDefinition` (ohne `()`) → `IWizardHoleFeatureData2`; auch nach Speichern, Schließen und
  `OpenDoc6` identisch lesbar (`s10_f4_auslesen.json`: `geoeffnet`). **`Type` ist `swWzdHoleTypes_e` (Art und Ende zusammen), nicht die
  allgemeine Lochart:** Gewinde blind 46 / durch 48, ISO 4762 blind 10 / durch 14, ISO 10642 blind 43 / durch 44, Stift blind 22 /
  durch 25. Besser `FastenerType2` (147/139/140/710; Stift-durch −1), `Standard2` (8), `FastenerSize` (Eingabetext),
  `EndCondition` (0 blind, 1 durch). **`Depth` liest immer 0.** Bohrungstiefe: bei blind Gewinde `TapDrillDepth`, sonst
  `HoleDepth`; bei durch ISO 4762/10642/Stift `ThruHoleDepth` (= Blockdicke), **Gewinde durch hat keine Tiefe**
  (`TapDrillDepth`, `HoleDepth`, `ThruHoleDepth` lesen 0; `messen.lies_normbohrung` liest für Gewinde `TapDrillDepth`);
  Gewindetiefe `ThreadDepth` (bei Gewinde durch nur, wenn angegeben); alles in m. Code `messen.lies_normbohrung`,
  `bewertung.normbohrung_abweichungen`.
- **Maße je Größe:** Bohrungstiefe zählt ab der Ansatzfläche, Bohrspitze 118° nur bei blind, Senkungen von der Fläche aus. Der
  Bohrungsassistent weicht in 7 Größen von den ISO-Vorwerten ab (ISO 4762 M8/M10/M12 Senktiefe, ISO 10642 M5–M10
  Senkdurchmesser); es gilt der SolidWorks-Wert (`bohrungsnormen.yaml`, Feld `abweichung`; `s10_f3_normmasse.json`: `abgleich`).
- **Skizzenverrundung:** die beiden Linien einer Ecke wählen (Marke 0), `CreateFillet(Radius, 1)` (1 =
  `swConstrainedCornerKeepGeometry`): Maße der Ecke bleiben am virtuellen Schnittpunkt, Status 3 direkt danach. **`CreateFillet`
  legt selbst ein maßgebendes Radiusmaß an** (`masse[].getrieben` = 2, je Ecke D5, D6, …); ein eigenes `AddDimension2` wäre nur
  referenzierend (`getrieben` = 1). Das Maß wird über den Vergleich der Maßnamen vor und nach dem Aufruf gefunden
  (`schritte[].masse_von_createfillet`) und dann per Gleichung an den Parameter gebunden (`"D5@s_skizze" = "R"`; `R` ändern →
  Volumen stimmt). Code `Skizzierer.verrunde`.
- **Langloch:** `CreateSketchSlot(1, 0, Breite, Mitte, Endbogenmitte, …, AddDimension = False)` (Mittelpunkt-Typ, Länge
  Mitte–Mitte); der erste Punkt ist die Mitte, der zweite die Mitte des Endbogens (Mitte + Länge/2 in Richtung des
  Winkels, nicht das Ende der Mittellinie – sonst wird das Langloch doppelt so lang; `skizze.py` `xe`/`ye`). Es entstehen zwei Linien, zwei Bögen, eine Konstruktions-Mittellinie und ein
  Mittelpunkt (`GetCenterPointHandle`); die Mittellinie misst den **ganzen Mittenabstand** (Länge). Breite = Maß zwischen den
  beiden Seitenlinien, Länge = Maß an der Mittellinie, Lage der Mitte zum Ursprung → Status 3. 0°/90° per Beziehung
  (horizontal/vertikal an der Mittellinie); sonst Hilfslinie vom Mittelpunkt (`CreateCenterLine`) plus Winkelmaß, **der
  Hilfslinienanfang wird per `sgCOINCIDENT` an `GetCenterPointHandle` gebunden** (`sgMERGEPOINTS` legt keine Beziehung an, Status
  bleibt 2; `c_langloch_mittelpunkt_30` gegen `…_koinzident`). Code `Skizzierer._langloch`, `_richtung_zu_u`.
- **Bögen (Kontur):** `CreateArc(Mitte, Start, Ende, 1)` (+1 = gegen den Uhrzeigersinn im Skizzensystem) ergab auf den drei
  Standardebenen `oben`, `vorne`, `rechts` die richtige Kontur (`schritte.gleichsinnig` = True). **Die Bögen teilen ihre
  Endpunkte mit den angrenzenden Linien schon** (6 Punkte vor und nach dem Verschmelzen) – `sgMERGEPOINTS` ist dafür nicht nötig.
  Bemaßung: Mittelpunkt der Bögen voll, Endpunkt nur in der Koordinate mit dem kleineren Abstand zum Mittelpunkt (`lage(nur=…)`),
  10 Maße, Status 3.
- **Endbedingungen bis/versatz Fläche:** Skizze mit Marke 0, Zielfläche per `Select4` mit Marke 1 anhängen, dann `FeatureCut4` /
  `FeatureExtrusion3` mit T1 = 4 (`swEndCondUpToSurface`) bzw. 5 (`swEndCondOffsetFromSurface`); Marke 2 und 32 wirken ebenso.
  `OffsetReverse1 = False` versetzt zur Skizze hin (Restwand 5 mm: Abnahme 6000 mm³), `True` darüber hinaus (8000 mm³). Das
  Versatzmaß heißt `D1@<Featurename>` (nicht `D1@<Skizze>`). Einschränkung: ein Aufsatz mit Versatz, dessen Skizze abgesetzt über
  der Zielfläche liegt (Testgeometrie: 5 mm Luft), ergibt zwei Körper (`d_aufsatz_versatz_5_offsetreverse_False.koerper`).
- **Speicher von SolidWorks:** bei Live-Läufen wachsen die Private Bytes um etwa 50–1250 MB je Testdatei (beobachtet bei den Live-Tests unter `tests/live/` und
  `tests/referenz/`, Stufe 2c). Neustart ab
  ca. 4 GB Private Bytes, bei Hängern oder „Ausnahmefehler des Servers“ (−2147417851; in der 7-GB-Instanz bei
  `ModelToSketchTransform`, `GetSlotPoints`, `CreateFillet`, in der frischen Instanz nicht, `s10_f5_skizzen.json`: `fehlversuche_serverfehler`)
  SolidWorks neu starten. Maßstab sind die Private Bytes, nicht das Working Set (blieb unter 700 MB).
