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
