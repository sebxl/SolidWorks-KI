# Stufe 0 – Ergebnisse (Rechner A, SW 2025)

Alle Spikes liefen live gegen SOLIDWORKS 2025 (Revision 33.5.0), Prozess `SLDWORKS.exe` durchgehend
stabil, keine Abstürze. Rohdaten je Spike: `docs/stufe0/ergebnisse/*.json`.

| Spike | Frage | Ergebnis | Folge für Stufe 2+ |
|---|---|---|---|
| S1 | pywin32 3.14 ↔ SW, Early Binding | Verbindung per Late Binding (`win32com.client.GetActiveObject`, dynamischer Dispatch) funktioniert einwandfrei (Rev. 33.5.0, SW 2025, sichtbar). Early Binding über `gencache.EnsureDispatch` auf das bereits laufende Objekt schlägt fehl: `TypeError("This COM object can not automate the makepy process - please run makepy manually for this object")`. | Late Binding fest für `swki.verbindung`; Design korrigiert (war „Early Binding über makepy“, siehe Abschnitt „Designanpassungen“ unten). |
| S2 | Ebenen sprachunabhängig | Die ersten drei `RefPlane`-Features liefern auf deutscher Oberfläche exakt „Ebene vorne“, „Ebene oben“, „Ebene rechts“; auf allen drei ließ sich problemlos eine Skizze einfügen. | Anker-Auflöser kann Standardebenen positionsbasiert (erste drei RefPlane-Features) statt namensbasiert auflösen. |
| S3 | Voll bestimmte Skizze + Extrusion | Variante A (`FullyDefineSketch` mit allen Relations-Flags + Bemaßungsschema) reicht aus: Rückgabe 0, Status danach `swFullyConstrained`, Extrusion „Aufsatz-Linear austragen1“ erfolgreich, `rebuild_fehler: 0`. Variante B (Einzelmaße + Preference-Toggle) war nicht nötig. | Handler „skizze“ nutzt Variante A als Standardweg; Variante B bleibt Rückfallplan bei Fehlschlag von A. |
| S4 | Masse, Hüllquader, Screenshots | Volumen exakt 120000 mm³ (= Soll), Hüllquader-Ausdehnung 100×20×60 mm (passt zum Sollteil). Alle 8 Bilder (4 Standardansichten × png/jpg, über `ShowNamedView2` + `SaveAs3`) fehlerfrei erzeugt und mit plausibler Größe; Sichtprüfung bestätigt korrekte Ansichten (Iso/Vorne/Oben/Rechts). | Prüfung in Stufe 2 kann `CreateMassProperty`, `GetPartBox`, `ShowNamedView2`+`SaveAs3` direkt nutzen. Bildexport (png und jpg) läuft über `swki`, nicht über MCP (siehe MCP-Zeile / Designanpassungen). |
| S5 | Kollisionsprüfung | `AddComponent5` + `InterferenceDetectionManager`/`GetInterferenceCount` funktionieren; eine bewusst überlappende Komponentenpaarung wird korrekt als 1 Kollision erkannt, eine freie Paarung als 0. | Baugruppen-Prüfung (Code-Prüfungen) kann `InterferenceDetectionManager` direkt verwenden. |
| S6 | Abstand verstellen, Position messen | `AddMate5` (swMateDISTANCE) legt eine Abstandsverknüpfung an, `IDimension.SetSystemValue3` verstellt sie schrittweise, die Komponentenposition lässt sich über `Transform2` exakt nachmessen. Nach Korrektur der Erwartungsformel (siehe unten) stimmen alle drei Messungen exakt. | Bewegungsprüfung kann `AddMate5`/`SetSystemValue3`/`Transform2` nutzen; muss den Bounding-Box-Zentrum-Versatz von `AddComponent5` (siehe Abweichungen) einrechnen. |
| S7 | Toolbox per API | Keine Methode im indizierten API-Bereich (`sldworks.tlb`/`swconst.tlb`) erzeugt ein Toolbox-Teil aus Norm+Größe (geprüft: `UpdateToolboxComponent`, `ToolboxPartType`, `Import/ExportToolboxItem`). Die Erzeugungsfunktionalität (Task-Pane, Norm/Größe wählen) liegt in einem eigenen, nicht indizierten Add-in (`SolidWorks.Interop.sldtoolboxconfigureaddin.dll`). Toolbox-Datenordner wurde per Registry ermittelt (`HKCU\...\SOLIDWORKS 2025\General\Toolbox Data Location`), nicht hartkodiert. | Normteile: Toolbox-Erzeugung immer über Rückfallweg (Größe manuell erzeugen, per `swki normteil aufnehmen` übernehmen). Design korrigiert (siehe unten). |
| MCP | Lese-Tools sichtbar, Sperren wirksam | Verifiziert in dieser Sitzung: 133 Tools real vom laufenden Server gemeldet (`session.list_tools()`); 20 Lese-Tools erlaubt in `config/mcp-lesetools.txt`, 113 gesperrt in `.claude/settings.json` (inkl. der 6 Pflicht-Sperren `execute_macro`, `batch_execute_macros`, `pack_and_go_assembly`, `batch_file_operations`, `execute_workflow`, `batch_process_files`, sowie `export_image`). **Noch nicht verifiziert:** Wirksamkeit innerhalb von Claude Code nach einem Neustart. | **Ausstehend: Prüfung durch Nutzer nach Neustart von Claude Code.** Checkliste: (1) Server `solidworks-mcp` ist verbunden; (2) von den 133 Tools sind nur die 20 aus `config/mcp-lesetools.txt` sichtbar/nutzbar, gesperrte Tools (u. a. `execute_macro`, `export_image`) werden abgewiesen; (3) ein lesender Aufruf (z. B. `get_model_info` oder `list_features`) bei geöffnetem Testteil liefert ein sinnvolles Ergebnis. |

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
