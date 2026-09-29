# Stufe 0 – Ergebnisse (Rechner A, SW 2025)

Alle Spikes liefen live gegen SOLIDWORKS 2025 (Revision 33.5.0), Prozess `SLDWORKS.exe` durchgehend
stabil, keine Abstürze. Rohdaten je Spike: `docs/stufe0/ergebnisse/*.json`.

| Spike | Frage | Ergebnis | Folge für Stufe 2+ |
|---|---|---|---|
| S1 | pywin32 3.14 ↔ SW, Early Binding | Verbindung per Late Binding (`win32com.client.GetActiveObject`, dynamischer Dispatch) funktioniert einwandfrei (Rev. 33.5.0, SW 2025, sichtbar). `gencache.EnsureDispatch` auf das bereits laufende Objekt scheitert: `TypeError("This COM object can not automate the makepy process - please run makepy manually for this object")`. Getestet wurde nur `EnsureDispatch` auf das laufende Objekt, **nicht** `gencache.EnsureModule(<sldworks.tlb>)` + `CastTo` (echtes Early Binding über eine vorab generierte Wrapperklasse) – das bleibt ungetestet. | Late Binding fest für `swki.verbindung`; Design korrigiert (war „Early Binding über makepy“, siehe Abschnitt „Designanpassungen“ unten). Vorsichtig formuliert, da `EnsureModule` + `CastTo` als Alternative nicht ausgeschlossen ist (siehe „Offene Punkte“ unten). |
| S2 | Ebenen sprachunabhängig | Die ersten drei `RefPlane`-Features liefern auf deutscher Oberfläche exakt „Ebene vorne“, „Ebene oben“, „Ebene rechts“; auf allen drei ließ sich problemlos eine Skizze einfügen. | Anker-Auflöser kann Standardebenen positionsbasiert (erste drei RefPlane-Features) statt namensbasiert auflösen. |
| S3 | Voll bestimmte Skizze + Extrusion | Variante A (`FullyDefineSketch` mit allen Relations-Flags + Bemaßungsschema) reicht aus: Rückgabe 0, Status danach `swFullyConstrained`, Extrusion „Aufsatz-Linear austragen1“ erfolgreich, `rebuild_fehler: 0`. Variante B (Einzelmaße + Preference-Toggle) war nicht nötig. | Handler „skizze“ nutzt Variante A als Standardweg; Variante B bleibt Rückfallplan bei Fehlschlag von A. |
| S4 | Masse, Hüllquader, Screenshots | Volumen exakt 120000 mm³ (= Soll), Hüllquader-Ausdehnung 100×20×60 mm (passt zum Sollteil). Alle 8 Bilder (4 Standardansichten × png/jpg, über `ShowNamedView2` + `SaveAs3`) fehlerfrei erzeugt und mit plausibler Größe; Sichtprüfung bestätigt korrekte Ansichten (Iso/Vorne/Oben/Rechts). | Prüfung in Stufe 2 kann `CreateMassProperty`, `GetPartBox`, `ShowNamedView2`+`SaveAs3` direkt nutzen. Bildexport (png und jpg) läuft über `swki`, nicht über MCP (siehe MCP-Zeile / Designanpassungen). |
| S5 | Kollisionsprüfung | `AddComponent5` + `InterferenceDetectionManager`/`GetInterferenceCount` funktionieren; eine bewusst überlappende Komponentenpaarung wird korrekt als 1 Kollision erkannt, eine freie Paarung als 0. | Baugruppen-Prüfung (Code-Prüfungen) kann `InterferenceDetectionManager` direkt verwenden. |
| S6 | Abstand verstellen, Position messen | `AddMate5` (swMateDISTANCE) legt eine Abstandsverknüpfung an, `IDimension.SetSystemValue3` verstellt sie schrittweise, die Komponentenposition lässt sich über `Transform2` exakt nachmessen. Nach Korrektur der Erwartungsformel (siehe unten) stimmen alle drei Messungen exakt. | Bewegungsprüfung kann `AddMate5`/`SetSystemValue3`/`Transform2` nutzen; muss den Bounding-Box-Zentrum-Versatz von `AddComponent5` (siehe Abweichungen) einrechnen. |
| S7 | Toolbox per API | Keine der fünf Member mit „Toolbox“ im Namen aus den indizierten Typbibliotheken `sldworks.tlb`/`swconst.tlb` erzeugt ein Toolbox-Teil aus Norm+Größe (geprüft: `IAssemblyDoc.UpdateToolboxComponent`, `IModelDocExtension.ToolboxPartType`, `IPackAndGo.IncludeToolboxComponents`, `ISldWorks.Import-`/`ExportToolboxItem`). Die Erzeugungsfunktionalität (Task-Pane, Norm/Größe wählen) liegt in einem eigenen Add-in mit eigener Typbibliothek (`SolidWorks.Interop.sldtoolboxconfigureaddin.dll`), die nicht in `TYPBIBLIOTHEKEN` steht und daher keine strukturierten `methode`/`enum`-Einträge liefert. Nicht „nicht indiziert“: `toolboxapi.chm` ist als Hilfetext im Index durchsuchbar und zeigt die Interfaces `IToolboxConfiguratorAddin`, `IToolBoxConfiguratorApplication`, `IPDMDocManager` – aber nur Konfigurator-/PDM-Hooks (`Connect`/`Disconnect`, `SetDocumentStatus`, …), keine Methode zum Erzeugen eines Teils. Toolbox-Datenordner wurde per Registry ermittelt (`HKCU\...\SOLIDWORKS 2025\General\Toolbox Data Location`), nicht hartkodiert. | Normteile: Toolbox-Erzeugung immer über Rückfallweg (Größe manuell erzeugen, per `swki normteil aufnehmen` übernehmen). Design korrigiert (siehe unten). |
| S8 | Early Binding über `EnsureModule` + `CastTo` | `gencache.EnsureModule` funktioniert für `sldworks.tlb`/`swconst.tlb` (Cache unter `%TEMP%\gen_py\3.14`; echter Kaltstart 2,2 s bzw. 0,1 s, danach <5 ms). `CastTo(app, "ISldWorks")` liefert scheinbar ein Objekt, das aber bei jedem Aufruf mit `AttributeError` bricht (`_oleobj_` zeigt fälschlich auf das CoClass-Objekt selbst, nicht auf einen echten IDispatch-Zeiger); nur der Umweg `CastTo(app._dispobj_, "ISldWorks")` funktioniert. `CastTo` auf **jedes** zurückgegebene Kindobjekt (Modell, Feature, SketchManager, FeatureManager, Extension) scheitert grundsätzlich mit demselben Fehler wie in S1 (`can not automate the makepy process`), weil SOLIDWORKS-COM-Objekte `GetTypeInfo()` nicht nutzbar implementieren – nicht nur das Application-Objekt betroffen, sondern das gesamte Objektmodell. Bei früh gebundenen Objekten müssen nullargumentige Member MIT `()` aufgerufen werden (Gegenteil der späten Bindung), aber da alle Kindobjekte dynamisch bleiben, gilt dort weiterhin die alte Regel ohne `()`. `FullyDefineSketch` mit rohem `None` scheitert weiterhin (`Typenkonflikt`), `callout_leer()` bleibt nötig. swconst-Konstanten (`win32com.client.constants.swEndCondBlind` usw.) funktionieren nach `EnsureModule(swconst.tlb)` und stimmen mit dem API-Index überein. | Späte Bindung bleibt für `swki.verbindung` gesetzt; `EnsureModule`+`CastTo` wird nicht eingeführt (siehe „Offene Punkte“ unten, jetzt beantwortet). Nebenwirkung: Sobald der gen_py-Cache einmal existiert (auch aus einem früheren Prozess), liefert `GetActiveObject` künftig automatisch ein getyptes `app`-Handle statt eines rein dynamischen – unschädlich, da bestehender Code app-seitige Nullargument-Zugriffe ausschließlich über `wert()` macht. |
| S9a | Aufrufketten Stufe-2-Compiler, Teil A (Bausteine 0–11) | Alle 12 Bausteine live ok (`spikes/s9a_b*.py`, `ergebnisse/s9a_b*.json`). Late Binding erzwingbar per `pythoncom.GetActiveObject` + `dynamic.Dispatch(QueryInterface(IID_IDispatch))`, auch bei vorhandenem gen_py-Cache (Cache danach wieder entfernt). Ebenenabbildung: vorne (u,v)→(X=u,Y=v,+Z), oben →(X=u,Z=−v,+Y), rechts →(Z=−u,Y=v,+X). Modell→Skizze über `ModelToSketchTransform` exakt, aber nur mit `_FlagAsMethod("CreatePoint")` und `VARIANT(VT_ARRAY\|VT_R8)` (rohe Liste liefert stillschweigend falsche Werte). Maße per `AddDimension2` mit `swInputDimValOnCreate` aus, `FullyDefineSketch` → voll bestimmt; Umbenennen wirkt auf `FullName`. Gleichungen `'"L" = 296'` / `'"D1@f1" = "L" / 10'` wirken nach `EditRebuild3`; Ändern nur per rohem `Invoke(PROPERTYPUT)`. Extrusion/Schnitt/Rotation/Bohrungen maß- und volumengenau; Schnittrichtung = gegen Skizzennormale, Schnitt ohne Material → `None`. Rebuild-Fehler über `EditRebuild3`=False, `GetWhatsWrong` (ByRef-VARIANTs, Code 71) und `GetErrorCode2(byref bool)`. | Aufrufketten in Implementierungsplan Stufe 2 übernehmen; `AddToDB=True` beim Skizzieren (sonst Inferenz-Relationen, z. B. ungewollt tangential); Maße und Zylinderflächen nie über Reihenfolge, sondern über FullName bzw. Position zuordnen (`GetFirstDisplayDimension` liefert u. U. Maße von Elternfeatures, Flächenreihenfolge kann sich umkehren); äußere Flächennormale nur über `IFace2.Normal` (nicht `PlaneParams`). |
| S9b | Aufrufketten Stufe-2-Compiler, Teil B (Bausteine 12–24) | Alle Bausteine live ok (`spikes/s9b_b*.py`, `ergebnisse/s9b_b*.json`), volumengenau nachgemessen. Verrundung, lineares und Kreismuster: `CreateDefinition`/`CreateFeature` (Vorselektion mit Marken, Kanten auch als `VARIANT(VT_ARRAY\|VT_DISPATCH)`) und die obsoleten `FeatureFillet3`/`FeatureLinearPattern5`/`FeatureCircularPattern5` liefern identische Ergebnisse. Fase nur über `InsertFeatureChamfer` (`CreateDefinition(swFmChamfer)` → None); Abstand-Abstand braucht `Width`/`OtherDist` statt der dokumentierten `VertexChamDist1/2`, Typ 16 erzeugt still ein leeres Feature. Spiegeln nur über `InsertMirrorFeature2` (kein CreateDefinition-Weg). Material „1.2312 (40CrMnMoS8-6)“ aus „SolidWorks DIN Materials“ (0,942 kg), Eigenschaften `Add3`/`Get6`, Prüfwerte über `CreateMassProperty2`/`CylinderParams`/`IMeasure`, `IModelDocExtension.SaveAs3` (.sldprt/.step/.png), HoleWizard5 M8 ISO, `CloseDoc` schließt geänderte Dokumente ohne Dialog, `OpenDoc6` auf offene Datei → dasselbe Objekt + Warnung 128. Neue Bindungs-Ausnahme: `IBody2` hat Typinfo → `GetFaces()` mit `()`. | CreateDefinition/CreateFeature für Verrundung und Muster, `InsertFeatureChamfer`/`InsertMirrorFeature2` für Fase/Spiegeln in den Plan übernehmen; Ergebnisse jedes Features nachmessen (mehrere stille Fehlschläge, siehe Wissensdatei); bei Kreismuster erst `EqualSpacing`, dann `Spacing` setzen; Musterrichtung aus `LineParams` der Kante ableiten; „swki pruefen“ muss erkennen, ob das Teil schon offen war (Warnung 128), bevor es schließt. |
| S10a | Stufe 2c, Bohrungsassistent (Fragen 1–4): HoleWizard5 ISO für Gewinde, ISO 4762, ISO 10642, Stift; mehrere Positionen in einem Feature; Maße je Größe; Daten auslesen | Alle vier Fragen beantwortet (`ergebnisse/s10_f1…f4*.json`). (1) Alle 25 Größen (10 Gewinde, 5 ISO 4762, 4 ISO 10642, 6 Stift) erzeugen ein fehlerfreies Feature, durch und blind, Gewindetiefe wirkt; M8 blind 16 = 605,8 mm³. Größen-Strings meist „M8“, Feingewinde „M8x1.0“, Stift „Ø8.0“ (Ø = U+00D8). Stift + durch liefert mit `HoleWizard5` nie ein Feature, geht aber über `CreateDefinition(25)` → `InitializeHole` → `SelectByRay` → `CreateFeature`. (2) Mehrere Positionen: Variante B (Positionsskizze öffnen, `CreatePoint`, bemaßen, an Gleichungen binden) voll bestimmt, 3 Punkte, 1817,399 mm³, mit L = 120 wandern die Achsen auf ±40; Variante A (mehrfach `SelectByRay`) liefert nur 1 Loch. (3) Alle 25 Größen: Volumen durch/blind stimmt mit `soll_volumen` überein (größte Abweichung 0,0005 mm³); Tiefe ab Fläche, Bohrspitze 118° nur bei blind. (4) `GetDefinition` liest nach `OpenDoc6` alles genauso wie im gebauten Teil; `FastenerSize` liefert den Eingabetext. | Task 3: Tabelle `bohrungsnormen.yaml` (25 Größen, SolidWorks-Werte, 7 mit `abweichung`). Task 8: Stift + durch über CreateDefinition; mehrere Positionen über Variante B. Task 9: Lesefelder je Art siehe Abschnitt „Stufe 2c: Spike S10“, Frage 4. |
| MCP | Lese-Tools sichtbar, Sperren wirksam | Verifiziert in dieser Sitzung: 133 Tools von `session.list_tools()` gemeldet, erhoben im Mock-Modus (`setup/mcp_tools_auflisten.py`, ohne SolidWorks) – die Tool-Registrierung (`register_tools` in `tools/__init__.py` von SolidworksMCP-python) läuft unbedingt und ist in Mock- und Real-Modus identisch, nur der darunterliegende Adapter unterscheidet sich; die Zahl gilt daher auch für den laufenden Server. 20 Lese-Tools erlaubt in `config/mcp-lesetools.txt`, 113 gesperrt in `.claude/settings.json` (inkl. der 6 Pflicht-Sperren `execute_macro`, `batch_execute_macros`, `pack_and_go_assembly`, `batch_file_operations`, `execute_workflow`, `batch_process_files`, sowie `export_image`). **Noch nicht verifiziert:** Wirksamkeit innerhalb von Claude Code nach einem Neustart. | **Ausstehend: Prüfung durch Nutzer nach Neustart von Claude Code.** Checkliste: (1) Server `solidworks-mcp` ist verbunden; (2) von den 133 Tools sind nur die 20 aus `config/mcp-lesetools.txt` sichtbar/nutzbar, gesperrte Tools (u. a. `execute_macro`, `export_image`) werden abgewiesen; (3) ein lesender Aufruf (z. B. `get_model_info` oder `list_features`) bei geöffnetem Testteil liefert ein sinnvolles Ergebnis. |

`export_image` ist bewusst gesperrt: der reale Adapter fällt beim Bild-Export auf
`SaveAs3(pfad, 0, 2)` zurück, sobald die Bitmap-Capture-Methoden scheitern – `SaveAs3` speichert
dabei das komplette Dokument an einem vom Aufrufer bestimmten Pfad (auch überschreibend), nicht nur
ein Bild. Das verletzt „MCP nur lesend“. Screenshots werden stattdessen über `swki` erzeugt (S4:
`ShowNamedView2` + `SaveAs3` auf `.png`/`.jpg` funktioniert einwandfrei). Folge für Stufe 2+:
Screenshot-/Bildexport ist eine `swki`-Funktion, nicht MCP.

## Stufe 1: API-Nachschlagewerk (Kriterium erfüllt)

- `swki api methode IFeatureManager.FeatureExtrusion3` → 23 Parameter, seit 2014.
- `swki api enum swEndConditions_e` → `swEndCondBlind = 0`, `swEndCondThroughAll = 1`.
- Index-Umfang: 15.909 Members, 8.199 Enum-Werte, 18.722 Seiten.
- `hh.exe` (CHM-Dekompilierung) braucht ein gesetztes Arbeitsverzeichnis (cwd) und relative Pfade;
  Pfade mit Leerzeichen scheitern lautlos (kein Fehlercode, einfach keine Ausgabe).
- CHM-Seiten liegen als UTF-8 mit BOM vor.

## Abweichungen von erwarteten Signaturen/Enum-Werten

Keine. Alle in S1–S7 vorab nachgeschlagenen Parameterzahlen und Enum-Werte (u. a.
`ISketchManager.FullyDefineSketch`: 10 Parameter, `swConstrainedStatus_e.swFullyConstrained = 3`,
`IAssemblyDoc.AddComponent5`: 8 Parameter, `IAssemblyDoc.AddMate5`: 15 Parameter,
`swMateType_e.swMateDISTANCE = 5`) stimmten exakt mit dem lokalen API-Index überein. Die
tatsächlich aufgetretenen Abweichungen betreffen die **pywin32-Bindungsart** und die **Semantik von
`AddComponent5`** (Zentrum statt Ursprung), nicht Signaturen oder Enum-Werte selbst – Details in
`swki/wissen/pywin32-fallstricke.md`.

Zusätzliche, nicht signaturbezogene Abweichung bei der MCP-Installation: Im MCP-Venv sind
`openai`/`anthropic` (transitiv über die Kernabhängigkeit `pydantic-ai`) sowie `uvicorn` (Kernab-
hängigkeit) installiert, obwohl `pip install -e .` ohne Extras lief. Keine Extras (`ui`, `rag`,
`vision`) wurden installiert. Die API-Schlüssel (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) bleiben in
`.mcp.json` leer, wodurch die Agenten-Schicht des Servers inaktiv bleibt (der Server legt nur bei
gesetztem `OPENAI_API_KEY` einen Agenten an). Keine Aktion nötig, nur zur Kenntnis.

## Designanpassungen (aus den Ergebnissen)

- **§5 (`verbindung`)**: „Early Binding über makepy“ war falsch angenommen; S1 zeigt, dass Early
  Binding auf ein bereits laufendes SolidWorks-Objekt fehlschlägt und Late Binding
  (`GetActiveObject`) der tragfähige Weg ist. Spec korrigiert.
- **§2/§9 (MCP)**: MCP wurde als Quelle für Screenshots gelistet; laut R9 ist `export_image`
  gesperrt (Rückfall auf `SaveAs3` kann Dokumente überschreiben). Spec korrigiert: Screenshots
  laufen über `swki`, nicht über MCP.
- **§8 (Toolbox)**: „Machbarkeit per API wird in Stufe 0 geklärt“ war als offene Frage formuliert;
  S7 klärt sie abschließend (kein Erzeugungsweg im indizierten API-Bereich). Spec präzisiert:
  Rückfallweg ist der einzige Weg, nicht nur eine Eventualität.

## Offene Punkte für den Plan von Stufe 2

- MCP-Wirksamkeitsprüfung nach Neustart von Claude Code steht noch aus (siehe Checkliste oben).
- `IModelDocExtension.CreateMassProperty` ist laut SW-Hilfetext *Obsolete* (ersetzt durch
  `CreateMassProperty2`); funktioniert weiterhin fehlerfrei (S4). Für Produktionscode in Stufe 2
  entscheiden, ob die alte oder neue Methode verwendet wird.
- `IAssemblyDoc.AddMate5` ist laut SW-Hilfetext ebenfalls *Obsolete* (ersetzt durch `CreateMate`);
  funktioniert weiterhin fehlerfrei (S6). Gleiche Entscheidung nötig wie bei `CreateMassProperty`.
- `IAssemblyDoc.AddComponent5` positioniert das **Zentrum der Bauteil-Bounding-Box**, nicht den
  Ursprung (S6, live per `Transform2` bestätigt). Der Compiler-Handler „baugruppe“ muss diesen
  Versatz beim Platzieren konsequent herausrechnen oder nach dem Einfügen per `Transform2`/Mates
  exakt nachpositionieren.
- Toolbox-Normteile (`quelle: toolbox` im Katalogschema) werden nie automatisch aus der API
  erzeugt; jede Toolbox-Größe muss einmalig manuell erzeugt und wie ein eigenes Normteil
  aufgenommen werden (S7).
- Die pywin32-Bindungs-Eigenart (nullargumentige Member ohne `()` aufrufen; `wert()` dafür nicht
  geeignet) betrifft potenziell jeden neuen COM-Aufruf in Stufe 2+ – vor jedem neuen, noch nicht in
  `swki/wissen/pywin32-fallstricke.md` verzeichneten Member-Typ mit Vorsicht prüfen (siehe
  Wissensdatei).
- **Erledigt (S8):** `gencache.EnsureModule(<sldworks.tlb>)` + `CastTo` wurde getestet. Ergebnis:
  kein Vorteil gegenüber Late Binding, im Gegenteil zusätzliche Fallstricke – `CastTo` scheitert auf
  dem Application-Objekt scheinbar erfolgreich, liefert aber ein bei jedem Zugriff brechendes
  Objekt (funktionierender Workaround nur über `app._dispobj_`), und scheitert auf jedem
  zurückgegebenen Kindobjekt (Modell, Feature, Manager) grundsätzlich mit demselben
  makepy-Automatisierungsfehler wie in S1. Late Binding bleibt für Stufe 2 gesetzt. Details:
  `docs/stufe0/ergebnisse/s8_early_binding.json`, `swki/wissen/pywin32-fallstricke.md`.

## Stufe 2c: Spike S10 (Rechner A, SW 2025)

Teil A (Bohrungsassistent, Fragen 1–4). Skripte `spikes/s10_gemeinsam.py`, `spikes/s10_f1…f4_*.py`, Rohdaten
`docs/stufe0/ergebnisse/s10_f1…f4_*.json`, Maßtabelle `swki/wissen/bohrungsnormen.yaml`. Teil B (Fragen 5–6) folgt in Task 2.

### Frage 1

- `HoleWizard5` mit den Werten des Plans (`swWzdTap 4`, `swWzdCounterBore 0`, `swWzdCounterSink 1`, `swWzdHole 2`; Standard ISO 8;
  Befestigung 147/139/140/710) erzeugt für alle 25 Größen ein fehlerfreies Feature (`whatswrong` 0), blind und durch; Gewinde blind 16 /
  Gewindetiefe 12 = 605,80 mm³, Unterfeature `Bohrungsgewinde1` (`CosmeticThread`), Positionsskizze `Skizze3` (1 Punkt, 0 Segmente).
- Größen-Strings: Regelgewinde, ISO 4762 und ISO 10642 „M<d>“; Feingewinde „M8x1.0“, „M10x1.0“, „M12x1.5“, „M16x1.5“ (ohne „.0“ bei
  M8x1/M10x1 kein Feature); Stift „Ø<d>.0“ (Ø = U+00D8), alle anderen Schreibweisen („8“, „Ø8“, „8.0“, „D8“) liefern still kein Feature.
  Vorsicht: bei ISO-Bohrergrößen (`swStandardISODrillSizes`) ergibt „Ø8“ ein Loch mit Ø0,18 mm.
- Maßnamen am HoleWzd-Feature (m/rad): Gewinde `D2` (Nenn-Ø), `D1` (Gewindetiefe, nur wenn angegeben), `Bohrerdurchmesser`, `Bohrungstiefe`,
  `Spitzenwinkel` (nur blind); ISO 4762 `Bohrerdurchmesser`, `Bohrungstiefe`, `Senkdurchmesser2`, `Senktiefe2`; ISO 10642 `Bohrerdurchmesser`,
  `Bohrungstiefe`, `Senkdurchmesser (Oben)`, `Senkwinkel (Oben)`; Stift `Bohrerdurchmesser` bzw. `Bohrungstiefe` analog.
- **Abweichung vom Plan (Stift + durch):** `HoleWizard5` mit `swWzdHole` und `EndType` 1 liefert immer `None` (getestet: Tiefe 0/−1/0,03,
  Durchmesser −1/9 mm, Screw Fit, Bohrwinkel). Blind geht. Durch geht über `fm.CreateDefinition(25)` (`swFmHoleWzd`) →
  `d.InitializeHole(2, 8, 710, "Ø8.0", 1)` → Vorselektion per `SelectByRay` → `fm.CreateFeature(d)` (1507,964 mm³ = π·4²·30). Es bleibt der
  Bohrungsassistent. Codestelle: `s10_gemeinsam.bohrung`, Zweig `art == "stift" and tiefe_mm is None`. Nachteil: `FastenerType2` liest danach −1
  (nicht 710) und lässt sich per Late Binding nicht setzen; `Type` = 25 (`swHoleThru`). Vorgabe für den Handler `normbohrung` (Task 8):
  Stift + durch immer über diesen Weg, den Größen-Text aus der Tabelle (ein ungültiger Text im CreateDefinition-Weg hat vermutlich einen
  Dialog ausgelöst und SolidWorks hängen lassen – Ursache nicht bewiesen).
- Ablaufanpassung f1: die Größen-Erkennung läuft blind (Tiefe 20, Gewindetiefe 12), damit nur bekannte Stifttexte den CreateDefinition-Weg erreichen.

### Frage 2

- Variante A (drei `SelectByRay` mit Marke 0, angehängt, dann `HoleWizard5`): nur 1 Punkt/1 Loch (605,8 mm³), kein Weg für mehrere Positionen.
- Variante B (Plan): erste Position per `SelectByRay`, Positionsskizze (Unterskizze ohne Segmente) mit `Select2` + `InsertSketch(True)` öffnen,
  zwei Punkte mit `CreatePoint`, alle Punkte mit dem Skizzierer bemaßen (`lage`), Maße per Gleichung an `L` binden: Status 3,
  `GetSketchPointCount` 3, 1817,399 mm³ (Soll 1817,40), Achsen (−30/0/30, −10); mit `L = 120` (`EvaluateAll`) Achsen (−40/0/40, −10),
  3 Gewinde-Unterfeatures, `whatswrong` 0. Gleichungen: `"D1@f2_positionen" = -((-"L" / 2) + 20)`, `"D4@f2_positionen" = ("L" / 2) - 20`.
- Vor dem Bemaßen hat die Positionsskizze Status 2 (unterbestimmt). Keine Abweichung vom Plan.

### Frage 3

- Alle 25 Größen (durch und blind 20, Gewinde 12) gemessen: Zylinder-/Kegelflächen, Box, Volumen. `abgleich.passt` überall; größte Abweichung 0,0005 mm³.
- Tiefenbezug: Bohrungstiefe = zylindrischer Teil ab Ansatzfläche, Bohrspitze 118° nur bei blind, Senkungen von der Fläche aus; „durch“ =
  Blockdicke (30 mm). `soll_volumen` blieb unverändert, gilt damit für `geometrie.normbohrung_volumen` (Task 4) und `sollvolumen.py` (Task 11).
  Stift + durch (CreateDefinition-Weg) passt ebenso (Ø8: 1507,964 mm³).
- SolidWorks weicht von den ISO-Vorwerten des Plans ab bei ISO 4762 M8/M10/M12 (`senkung_t` 8,6/10,6/12,6 statt 8,4/10,4/12,4) und ISO 10642 M5–M10
  (`senkung_d` 11,2/13,44/17,92/22,4 statt 10,4/12,4/16,4/20,4); es gilt der SolidWorks-Wert, in der Tabelle unter `abweichung`. Kernlöcher,
  Durchgänge und Stiftmaße stimmen mit den ISO-Vorwerten überein.

### Frage 4

- `IFeature.GetDefinition` (ohne `()`) → `IWizardHoleFeatureData2`; nach Speichern, Schließen und `OpenDoc6` sind alle Felder identisch zum gebauten Teil
  lesbar (`typname` = `HoleWzd`, `Standard2` = 8, `FastenerType2` = 147/139/140/710, `FastenerSize` = Eingabetext, also kein `gelesen` in der Tabelle).
- `Type` ist nicht der Eingabetyp, sondern `swWzdHoleTypes_e` (Art + Endbedingung): Gewinde blind 46 (`swTapBlindCosmeticThread`), Gewinde durch 48,
  ISO 4762 blind 10 / durch 14, ISO 10642 blind 43 / durch 44, Stift blind 22 (`swHoleBlind`) / durch 25 (`swHoleThru`). Zur Prüfung besser
  `FastenerType2` (außer Stift-durch) und `EndCondition` (0 blind, 1 durch) verwenden.
- Tiefenfelder je Art: blind Gewinde `TapDrillDepth` (= Bohrungstiefe) und `ThreadDepth` (Gewindetiefe); blind ISO 4762/10642/Stift `HoleDepth`;
  `Depth` liest immer 0; durch ISO 4762/10642/Stift `ThruHoleDepth` (= Blockdicke), Gewinde durch keine Tiefe. Durchmesser: `TapDrillDiameter`
  (Gewinde), `HoleDiameter` (blind), `ThruHoleDiameter` (durch).
- `GetSketchPointCount`: 1 bei einer Position; bei zwei per `SelectByRay` gewählten Positionen ebenfalls 1 (Frage 2, Variante A); nach Variante B = Anzahl der Punkte.
- Stift + durch (CreateDefinition): identisch lesbar, aber `FastenerType2` = −1 (`Standard2` 8, `FastenerSize` „Ø8.0“, `Type` 25, `EndCondition` 1,
  `ThruHoleDiameter` 0,008). Die Prüfung erkennt ihn an `FastenerSize`/`Type`/`ThruHoleDiameter`; Frage 4 ist damit auch für diesen Weg erfüllt.

### Entscheidungen (Teil A)

- Stift + durch: Bohrungsassistent über `CreateDefinition(25)`/`InitializeHole`/`CreateFeature` (Entscheidung Controller, 2026-09-29);
  `FastenerType2` = −1 im Rücklesen akzeptiert.
- Tabelle: SolidWorks-Werte gelten, Abweichungen zu ISO stehen als `abweichung` (Spec §3.3); keine Größe entfernt.
- Mehrere Positionen: Variante B (Positionsskizze); Variante A entfällt.
