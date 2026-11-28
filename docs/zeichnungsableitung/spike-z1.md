# Spike Z1.0 – Zeichnung über die SolidWorks-API

Datum: 2026-11-17 · Rechner A, SolidWorks 2025 **SP5** (Revision 33.5.0, Studentenversion), frisch gestartet ·
Skripte: `spikes/z1_zeichnung.py` (Fragen 1–9), `spikes/z1_diag_modellmasse.py` (Diagnose zu Frage 4) ·
Teile: Referenz Buchse (Drehteil) und Spannplatte (Frästeil), mit `swki bauen` gebaut (Aufträge `Z1SPIKE-buchse`,
`Z1SPIKE-stil` im Arbeitsordner). Ergebnis-JSON, SLDDRW und PDF: `<arbeitsordner>/Z1SPIKE/`.

## Kurzfassung

- **Trägt ohne Dialog:**
  - Zeichnung anlegen; Blatt auf A3, 1:1, Projektionsmethode 1 umstellen.
  - Drei Standardansichten, Schnitt A-A, Einzelheit.
  - Markierte Modellmaße übernehmen, ein neues Maß zwischen zwei Kanten setzen.
  - Passung H7 und Ⓔ als Maßzusatz; Oberflächensymbol nach ISO 21920.
  - Alle Maße mit Name, Wert, Toleranz und Kanten zurücklesen; SLDDRW und PDF speichern.

  Eine Zeichnung braucht dafür wenige Sekunden.
- **Nicht gelöst:** Bohrungsangaben kommen über `InsertModelAnnotations4` mit `swInsertholeCallout` **nicht** (0 Stück);
  `AddHoleCallout2` braucht einen Dialog (Recherche Kap. 10). Bohrungsangaben brauchen einen eigenen Weg (Abschnitt Folgen).
- **Modellmaße roh sind unbrauchbar** (PDF `buchse_spike.pdf`):
  - Sie landen mehrfach, in jeder Ansicht, in der die Skizze sichtbar ist (Buchse: 74 Maße, 28 davon doppelt).
  - Sie enthalten Skizzen-Konstruktionsmaße, z. B. die Mittellinie von −5 bis 65 und die Fasenwinkel.
  - Sie überlappen sich.

  Der Weg „Modellmaße übernehmen“ trägt nur, wenn swki vorher gezielt markiert (nur protokollierte Anforderungsmaße)
  und je Maß die Ansicht festlegt.
- **Die Studentenversion setzt das Wasserzeichen** „SOLIDWORKS Lehrprodukt – Nur für Lehrzwecke.“ in das PDF. Das bestätigt
  die Entscheidung, Fertigungszeichnungen nur auf der Vollversion zu erzeugen.
- **Service Pack:** SP5 – `GetFirstDisplayDimension6` und `GetAnnotationsByType` (SP1/SP2) sind vorhanden. Die
  SP-Abhängigkeiten aus der Recherche sind auf Rechner A kein Hindernis; Ersatzwege bleiben für andere Rechner.

## Antworten je Frage

| # | Frage | Ergebnis | Methode (n Parameter, seit) | Fallstrick |
|---|---|---|---|---|
| 1 | Service Pack | 2025 SP5 | `ISldWorks.RevisionNumber` | – |
| 2 | Zeichnung, Projektionsmethode 1, Standardansichten | ja, 3,4 s inkl. Öffnen | `NewDocument` (4), `ISheet.SetProperties2` (8, 2016): A3 = 8, Vorlage 13 (keine), 1:1, `FirstAngle` true, 0,42 × 0,297 m; `Create1stAngleViews2` (1) | Standardvorlage `Zeichnung.drwdot` ist **US-Letter, 3. Winkel, 1:5**; ohne Blatt-Setup falsch. `Create1stAngleViews2` liefert `False` und keine Ansichten, wenn das Teil nur gespeichert, nicht geöffnet ist → Teil vorher `OpenDoc6` (silent). Modellansichten heißen deutsch („*Vorderseite“, „*Oben“ …). |
| 3 | Schnitt und Einzelheit ohne Dialog | ja | Ansicht aktivieren, `SketchManager.CreateLine` (6) in Blattkoordinaten, `CreateSectionViewAt5` (7) → „Schnittansicht A-A“; `CreateCircleByRadius` (4), `CreateDetailViewAt4` (12, 2017) → „Detailansicht Z (2 : 1)“ | Lage der neuen Ansichten selbst rechnen (überlappt sonst, ragt über das Blatt). Der Einzelheiten-Kreis muss auf Geometrie liegen, sonst ist die Einzelheit leer. |
| 4 | Markierte Modellmaße übernehmen | ja, 74 Maße (Buchse) / 80 (Spannplatte) in < 0,4 s | `IDrawingDoc.InsertModelAnnotations4` (8, 2024): `(0, swInsertDimensionsMarkedForDrawing=32768, AllViews=True, DuplicateDims=False, HiddenFeatureDims=True, …False)`, vorher Ansicht per `SelectByID2(name, "DRAWINGVIEW")` wählen, `ActivateView`, Auswahl leeren (Hilfe-Beispiel Insert_Model_Annotations) | **`HiddenFeatureDims=True` ist Pflicht**: swki blendet die Skizzen aus, sonst 0 Maße (Diagnose: `InsertModelAnnotations3` je Ansicht und `IView.ImportAnnotations` (5, 2025) → 0; IMA4 ohne Hidden → 1 je Ansicht). Ergebnis roh: Duplikate über Ansichten, Konstruktionsmaße, Überlappung. |
| 4 | Bohrungsangabe (`swInsertholeCallout`) | **nein**, 0 Stück (Buchse und Spannplatte mit Bohrungsassistent-Gewinden) | IMA4 mit 1048576 | Offen; `AddHoleCallout2` braucht laut Hilfe einen Dialog. |
| 5 | Ändert `MarkedForDrawing` die Teildatei? | **ja** (Kopie: SHA ändert sich nach `Save3`). Buchse: 56 Maße, 55 markiert (Vorgabe von SolidWorks) | `IDisplayDimension.MarkedForDrawing` (put, 2004), `IFeature.GetFirstDisplayDimension`/`GetNextDisplayDimension` | Alternative ohne Teiländerung: in der Zeichnung löschen. `IAnnotation.Select3(False, callout_leer())` + `EditDelete` löscht das Maß in der Zeichnung; die SLDPRT bleibt unverändert (SHA geprüft nach `SaveAs` der Zeichnung). |
| 6 | Neues Maß zwischen zwei Kanten | ja: Länge 60 mm der Buchse von der Bundfläche | `IView.GetVisibleEntities2(callout_leer(), swViewEntityType_Edge=1)` (2, 2014) → 6 sichtbare Kanten; Kreiskanten über `ICurve.CircleParams` (Modellkoordinaten in m) erkannt; `IView.SelectEntity` (2) × 2; `IModelDoc2.AddDimension2(x, y, 0)` (3) → Anzeigemaß „RD1@Zeichenansicht1“ (Referenzmaß der Zeichnung), 2 Kanten angehängt | `GetVisibleEntities2` braucht einen leeren Dispatch statt `None` (Typenkonflikt). Placement in Blattkoordinaten (m). |
| 7 | Passung H7, Hülle Ⓔ, Oberfläche ISO 21920 | ja | `IDimension.Tolerance` → `Type = swTolFIT (7)`, `SetFitValues("H7", "")` (2, 2006) → zurück: Typ 7, `GetHoleFitValue` = „H7“; Ⓔ als Maßzusatz `IDisplayDimension.SetText(swDimensionTextSuffix=2, " Ⓔ")`, Text zurücklesbar; Norm-Option `swDetailingSFSymbolStandard` (629) stand in der Vorlage schon auf `21920_1` (2); `IModelDocExtension.InsertSurfaceFinishSymbol3` (14, 2005) mit Typ `swSFMachining_Req` → Text „Ra 0,8“ in Feld 5 zurück | Ⓔ hat keine API (Suffix-Text; Darstellung im PDF prüfen). Maße nach **Name** wählen (Maßprotokoll), nicht nach Wert: Die Suche nach „20 mm“ traf ein Lagemaß statt des Ø 20. Symbol ohne Auswahl landet frei auf dem Blatt. |
| 8 | Zurücklesen | ja | `GetFirstDisplayDimension5`/`GetNext5`, `GetDimension2(0)`, `FullName`, `SystemValue`, `Tolerance.Type`, `GetHoleFitValue`, `GetText(2)`, `ShowParenthesis`, `Inspection`, `GetAnnotation` → `GetAttachedEntities3` (Kantenzahl), `GetPosition`; `GetFirstDisplayDimension6` und `GetAnnotationsByType` vorhanden (SP5) | `GetSystemValue3(1, None)` liefert für Zeichnungsmaße `None`; `SystemValue` nehmen. Nullargumentige COM-Member liefert der dynamische Dispatch schon beim Zugriff (`EditRebuild3`, `GetCurrentSheet`): Prüfung auf `win32com.client.dynamic.CDispatch`, nicht `win32com.client.CDispatch`. |
| 9 | Speichern, PDF, Zeit | ja: SLDDRW 0,5–2,4 s, PDF 0,5–2,6 s, 58 KB, Fehler 0 | `IModelDocExtension.SaveAs` (6) mit `swSaveAsOptions_Silent` und `ExportData = callout_leer()` (mit `None`: Typenkonflikt) | Teildatei bleibt unverändert (SHA). Wasserzeichen der Studentenversion im PDF. |

## Folgen für Design Abschnitt 6.2 (Maße aus dem Modell oder neu)

1. **Modellmaße tragen nur gefiltert.** swki setzt beim Bau `MarkedForDrawing` nur an Maßen, die im Maßprotokoll
   (`Kontext.mass`) als Anforderungsmaß stehen (art `lage`, `paarabstand`, `groesse`, `radius`, `tiefe`, `winkel` mit
   Bezug oder Größe), und nimmt es allen anderen (Konstruktionsmaße, Mittellinien, Fasenwinkel aus Normfasen).
   Teile vor Z1 brauchen dafür **einen Neubau**: Nachträgliches Markieren ändert die Teildatei (Frage 5).
   Alternative ohne Neubau: alle Maße einfügen und die nicht gewollten in der Zeichnung löschen. Sie trägt laut Frage 5
   auch, ist aber über die Zahl der Löschungen langsamer und anfälliger.
2. **Je Maß eine Ansicht.** `AllViews=True` verteilt jedes Maß auf alle passenden Ansichten. swki muss nach dem Einfügen
   die Duplikate löschen und dabei je Maß die Ansicht behalten, die der Maßplan nennt (Name über `FullName` → Maßprotokoll).
3. **Neu setzen trägt.** Kantenauswahl über `GetVisibleEntities2` + Geometrie (Kreismittelpunkt, Linienlage in
   Modellkoordinaten) + `AddDimension2`. Damit lassen sich Drehteil-Längen von der Bezugsfläche, Gesamtmaße und
   Lagemaße zu `bezuege` setzen. Diese Maße sind Referenzmaße der Zeichnung (`RD…`), Toleranzen gehen trotzdem.
4. **Anordnen ist eigene Arbeit.** Ansichten und Maße überlappen, ohne Platzierung ist die Zeichnung unlesbar.
   Ansichtslage aus den Umrissen (`GetOutline`) rechnen; Maße mit `AlignDimensions` bzw. eigener Platzierung. Das gehört
   in den Plan Z1.3 und in die Prüfung `lesbarkeit` (Hüllrechtecke).
5. **Bohrungsangaben brauchen einen eigenen Weg** – Kandidaten für einen Folge-Spike in Z1.3:
   (a) Bohrungstabelle `IView.InsertHoleTable2/3` (Recherche Kap. 10, braucht Auswahl);
   (b) Bohrungsangabe als Notiz mit Text aus der Spec (Normbohrung kennt Größe und Tiefe) und Hinweislinie an der Kante;
   (c) `InsertModelAnnotations4` mit `swInsertHoleWizardProfileDimensions` / `…LocationDimensions`.
6. **Blatt und Norm kommen aus der Vorlage.** Die Standardvorlage ist US-Letter, 3. Winkel, 1:5, ohne Rahmen. Die
   Maße zeigen zwei Nachkommastellen („10,00“). Bis die Firmenvorlage da ist, setzt swki das Blatt per API. Genauigkeit und
   Maßstil gehören in die Normdatei der Vorlage (Z1.5).

## Neubau alter Teile

Ja, für den Weg „markierte Modellmaße“ (Folge 1). Eine Ausnahme gilt, wenn Z1.3 den Löschweg wählt.

## Nicht geprüft

- Darstellung von Ⓔ im PDF: Der Text ist gesetzt, ob die Schrift das Zeichen zeigt, ist nicht geprüft.
- Bohrungstabelle, Mittellinien und Mittelpunktmarken.
- `AlignDimensions`, Schriftfeld über Eigenschaften (wartet auf die Vorlage).
- Speicherverbrauch über viele Zeichnungen.
- Laufzeit auf dem Firmenrechner (SW 2026).

## Nachtrag: Blattformate des Nutzers (17.11.2026)

- Die drei Formate „A3 Quer / A4 / A4 Quer DIN EN ISO 7200.slddrt“ sind mit **SolidWorks 2026** gespeichert
  (`ISldWorks.VersionHistory` → `19000[2026/225]`; Teile von Rechner A: `18000[2025/268]`). SW 2025 lädt sie nicht und
  meldet nichts: `SetupSheet5(…, swDwgTemplateCustom=12, Pfad, …)` gibt `True`, das Blatt bleibt leer,
  `GetSheetFormatName` ist leer. Kopien liegen im Arbeitsordner unter `vorlagen/zeichnung/`, das Original bleibt unberührt.
- Mit den mitgelieferten SW-2025-Formaten (`a3 - iso.slddrt`, `a4 - iso.slddrt`, Kopien unter `vorlagen/zeichnung_sw2025/`)
  lädt `SetupSheet5` das Format; die Notizen des Blattformats sind über die erste Ansicht (`IDrawingDoc.GetFirstView`
  → `GetNotes`) lesbar, samt Verknüpfung (`INote.PropertyLinkedText`, z. B. `$PRP:"DrawnBy"`, `$PRPSHEET:"Material"`,
  `MASSSTAB:$PRP:"SW-Sheet Scale"`). Das SW-Format ist ein Muster, kein Schriftfeld nach ISO 7200.
- Skript: `spikes/z1_blattformat_lesen.py`. Folge: Entwicklung bis Z1.4 mit dem SW-2025-Format, die Formate des Nutzers
  in Z1.5 auf dem Firmenrechner (SW 2026); dort dieselbe Leseroutine für die Feldnamen.

## Korrektur (17.11.2026, Z1.3 Stufe 1)

Frage 3 ist falsch beantwortet: Skizzen in einer aktiven Zeichenansicht liegen **nicht** in Blattkoordinaten, sondern
relativ zum Ansichtsursprung (`IView.Position`) und im Modellmaßstab (÷ `IView.ScaleDecimal`). Der Spike hat nur geprüft,
dass eine Schnittansicht zurückkam; die Linie lag neben dem Teil, der Schnitt hatte keine Schraffur, die Einzelheit war
leer. In gedrehten Ansichten (`IView.Angle`) landen Skizzen zusätzlich gedreht; ein Ausbruch (`CreateBreakOutSection`)
dort meldete Erfolg ohne sichtbare Wirkung. `swki zeichnen` rechnet deshalb um (`_in_ansicht`) und erzeugt den
Längsschnitt eines Drehteils aus der ungedrehten Stirnansicht.

## Nachtrag: Stufe 3 – Bohrungsangabe als Hinweis (19.11.2026)

Spike `spikes/z1_diag_bohrungsangabe.py` auf der Spannplatten-Zeichnung (SW 2025, frisch gestartet); gemessen im PDF mit pymupdf.

| Frage | Ergebnis | API | Lehre |
|---|---|---|---|
| Kreiskante wählen | Sichtbare Kante aus `GetVisibleEntities2(…, 1)` mit `GetCurve.IsCircle` und Nachbarfläche aus `g1`/`m1` (hier `f1`, `m1`); Auswahl gelingt, Auswahlzahl 1 | `IView.SelectEntity(kante, False)` | Die Kante selbst (nicht ihre Geometrie) auswählen, vorher `ClearSelection2(True)` |
| Hängt `InsertNote` die Hinweislinie an die Auswahl? | Ja: 1 Hinweislinie, 1 angehängte Entität, Linienende im PDF 0,03 mm vom Kreis; kein Fallback nötig | `IModelDoc2.InsertNote(text)` → `INote.GetAnnotation` → `GetLeaderCount`, `GetAttachedEntities3` | Auswahl vor `InsertNote`, danach `ClearSelection2(True)` |
| Ø im Text | Unicode „Ø“ erscheint im PDF als „Ø6“; `<MOD-DIAM>` zerlegt den PDF-Text („Senkung “ / „6 × 90°“), also Unicode nehmen. Zeilenumbruch `\n` wird zu `\r\n` | `INote.GetText` | Ø, ×, –, ° direkt als Unicode schreiben |
| Lage | `SetPosition2` setzt die Notiz in Blattkoordinaten (m) exakt (Soll 166/260 mm, Ist 166,00/260,00); die Hinweislinie bleibt an der Kante (1 Linie). Vor dem Setzen lag die Notiz bei (158,7/252,2); `GetPosition` liefert ein z von 5 mm, `SetPosition2(x, y, 0)` stört das nicht | `IAnnotation.SetPosition2(x, y, 0)`, `GetPosition` | Position = linke obere Ecke der Notiz in Blatt-m; Hinweislinie zieht mit |
| Beschriftung der Einzelheit | „EINZELHEIT B“ statt „DETAIL B“ in der bestehenden Ansicht nach `EditRebuild3` | `SetUserPreferenceToggle(240, 0, False)`, `SetUserPreferenceInteger(241, 0, 3)`, `SetUserPreferenceString(81, 0, "EINZELHEIT")` | Reihenfolge: PerStandard aus, Name = custom, CustomName; wirkt auch auf schon vorhandene Einzelheiten |
| Ansatz der Hinweislinie am Kreis (Task 4, `spikes/z1_diag_hinweis_ansatz.py`) | Nach `SelectEntity(kante)` endet der Pfeil auf der Gegenseite des Kreises (Spannplatte und Buchse unten links), die Hinweislinie läuft quer durch die Bohrung. `SelectByID2("", "EDGE", x, y, 0, …)` mit einem Blattpunkt auf dem Kreis wählt Ansicht (Typ 12) und Kante (Typ 1); der Pfeil sitzt dann an diesem Punkt (Soll 45°/135°, Ist 49°/137°) | `IModelDocExtension.SelectByID2` (9), `ISelectionMgr.GetSelectedObjectType3` (2), `GetSelectedObject6` (2) | Kreispunkt zum Text hin wählen; dreht die Lage um mehr als 30°, Hinweis neu einfügen |
| Größe und Bezugspunkt des Hinweises (Task 4) | `INote.GetExtent` gleich nach `InsertNote`: 53 × 13,5 mm, 13,5 mm links vor dem Text (Hinweislinie eingerechnet); im PDF 39,8 × 10,9 mm. `IAnnotation.GetPosition` = linke obere Ecke, Textoberkante im PDF 1,4 mm darüber | `INote.GetExtent`, `IAnnotation.GetPosition` | Größe am PDF vermessen (`lesbarkeit.texte`), nicht über `GetExtent` |
| Beschriftung über der Einzelheit (Task 4) | Unter der Ansicht lag „EINZELHEIT B“ (8,5 mm Schrift) auf der unteren Maßreihe; die Reihen rückten aus dem Zeichenfeld. Über der Ansicht kein Befund | `SetUserPreferenceToggle(337, 0, True)` (`swDetailingDetailViewLabels_AboveView`) | in jeder Zeichnung vor dem Anlegen der Einzelheit setzen |

## Nachtrag: Stufe 4 – Toleranzen, Ⓔ, Rauheit, Bezug, Form/Lage (27.11.2026)

Spikes `spikes/z1_diag_stufe4.py` (a) bis `z1_diag_stufe4f.py` (f) auf der Spannplatten-Zeichnung aus `swki zeichnen`
(Lauf 1, SW 2025). Jeder Spike speichert eine Kopie der Zeichnung, schließt sie ohne das Teil zu speichern, öffnet sie
neu und liest zurück. Bewertet wurde nach PDF-Text und Ausschnitt-PNG, nicht nur nach der Rücklesung. Die Teil-SHA blieb
in allen Läufen gleich.

| Frage | Ergebnis | API | Lehre |
|---|---|---|---|
| Passung/Abmaße/Zusätze an **eingefügten Modellmaßen** (a) | Gehen beim Wiederöffnen verloren (Typ 0, Präfix/Suffix leer). Sie hängen am Maß des Teils, und das Teil wird nie gespeichert (SHA-Regel). Das betrifft auch die Stufe-3-Zusätze: „4 × 30,00 (= 120)“ steht im PDF aus `swki zeichnen`, fehlt aber in der wieder geöffneten SLDDRW. Das PDF stimmt, weil es vor dem Schließen entsteht. | `IDimension.Tolerance`, `IDisplayDimension.SetText` | Toleranz und Zusatz nie am Modellmaß, sondern am **Zeichnungsmaß** |
| Modellmaß in Zeichnungsmaß umwandeln über die angehängten Entitäten (b) | Geht nicht: `GetAttachedEntities3` liefert Typ 11 (Skizzenelemente, in der Ansicht nicht wählbar); `D3@m1` (Musterabstand) hat keine Entitäten | `IAnnotation.GetAttachedEntities3`, `GetAttachedEntityTypes` | Umwandeln über die **Bezugspunkte der Hilfslinien** (`_bezuege`) und die sichtbaren Kanten oder Kreise an diesen Punkten |
| Zeichnungsmaß über zwei Kanten (c, d) | Bleibt erhalten: Passung (Typ 7, „H7“), Präfix/Suffix, Abmaße. Name `RD<n>@<Ansicht>` | `IView.SelectEntity` ×2, `IModelDoc2.AddDimension2` | Zeichnungsmaß = dauerhafter Träger aller Anforderungen am Maß |
| Wert eines Zeichnungsmaßes (c) | `GetSystemValue3(1, None)` liefert None; `GetSystemValue2("")` liefert den Wert | `IDimension.GetSystemValue2` | beide Wege, Modellmaß zuerst |
| Abmaße setzen (d) | `SetValues2(min, max, w, None)` liefert für w = −1, 0, 1, 2 False und zeigt „0,00/0,00“. `SetValues(min, max)` liefert True, im PDF „120,00 +0,10 −0,05“, nach dem Wiederöffnen gleich | `IDimensionTolerance.SetValues` (2) | an Zeichnungsmaßen `SetValues` |
| Passung darstellen (e) | `FitDisplayStyle` 3 (Vorgabe): „200,00 H7“ in einer Zeile; 1 und 2: H7 hochgestellt; Typ 8 (FITWITHTOL): „200,00 H7 +0,05/0,00“ | `IDimensionTolerance.Type = 7`, `SetFitValues("H7", "")`, `FitDisplayStyle` | Typ 7, Stil 3 |
| Hülle Ⓔ (e, f) | Das Unicode-Zeichen „Ⓔ“ (U+24BA) im Suffix lässt den **ganzen Maßtext** verschwinden; im Spike a fehlte deshalb die 200. Das Symbol `<MOD-EP>` (Symboldatei `lang/german/gtol97.sym`, „Encompassing“, Kreis mit E) ergibt „200,00 H7 Ⓔ“ | `IDisplayDimension.SetText(2, " <MOD-EP>")` | Ⓔ an Maßen immer als `<MOD-EP>`, Rücklesen liefert den Tag |
| Rauheitssymbol (a, c, d) | An einer Kreiskante gewählt, entsteht das Symbol mit Hinweislinie. Von den sieben Textparametern erscheint im PDF nur der dritte (ProdMethod) über dem Symbol. „Ra 0,8“ dort ist sichtbar. Ohne `SetPosition2` liegt das Symbol irgendwo. `GetText(2)` liefert den Text zurück | `IModelDocExtension.InsertSurfaceFinishSymbol3` (14), `ISFSymbol.GetText`, `GetNext` | Text an Platz 3, Lage immer setzen |
| Bezugsdreieck, Toleranzrahmen (a) | Beide entstehen ohne Dialog an einer gewählten Kante und bleiben nach dem Wiederöffnen erhalten („⊥ 0,02 A“ im PDF). Ohne `SetPosition2` liegt ein Rahmen am Blattursprung, und `IView.GetFirstGTOL` der Ansicht findet nur die an die Ansicht gebundenen | `IModelDoc2.InsertDatumTag2`, `IDatumTag.SetLabel`, `IModelDoc2.InsertGtol`, `IGtol.SetFrameSymbols2` (9), `SetFrameValues2` (6), `GetNextGTOL` | Lage immer setzen; Rückleser geht auch über die Blattansicht |
| Freier Hinweis (a, b) | `InsertNote` ohne Auswahl legt den Hinweis unter das Blatt (y = −18,8 mm). Nach `SetPosition2` steht „Tolerierung ISO 8015:2011“ im PDF | `IModelDoc2.InsertNote`, `IAnnotation.SetPosition2` | Sammelangaben mit fester Lage |
| Aufrufe ohne Parameter | `drw.InsertDatumTag2()` → „Mitglied nicht gefunden“; über `_ruf(drw, "InsertDatumTag2")` geht es | pywin32 dynamic | Methoden ohne Parameter immer über `_ruf` |

Folge für Stufe 4 Task 5:
- Jedes Plan-Maß mit Toleranz oder Textzusatz wird zum Zeichnungsmaß. Die Zusätze aus Stufe 3 sind eingeschlossen, damit die SLDDRW dem PDF entspricht.
- Fall Modellmaß: umwandeln an denselben Bezugspunkten. Wo das nicht gelingt, bleibt das Modellmaß stehen, mit der Meldung `MASS_NICHT_DAUERHAFT`.
- Fall Drehteil-Maß (`neu`): Es ist schon ein Zeichnungsmaß, Toleranz und Zusatz kommen direkt daran.

## Nachtrag: Stufe 4, Teil g und h – Rauheitstext und Hinweislinien (28.11.2026)

Spikes `spikes/z1_diag_stufe4g.py` (g) und `z1_diag_stufe4h.py` (h) auf der SpannplatteZ (Review Task 5, I6, C2, I4).

| Frage | Ergebnis | API | Lehre |
|---|---|---|---|
| Wo erscheinen die Textplätze von `InsertSurfaceFinishSymbol3`? (g) | Vorlage: Norm 2 = ISO 21920-1. Dort und bei ISO 1302:2002 zeigt nur Platz 3 (ProdMethod) Text, **über** dem Strich (Feld c); 1302:2002 zeigt dazu Platz 1 links. ISO 1302:1992 zeigt alle sieben | `swDetailingSFSymbolStandard` (629), `swDetailingSFSymbolStandard_e` 0/1/2 | Text an Platz 3 ist das Fertigungsverfahren, nicht die Anforderung |
| Feld a unter dem Strich (g) | `ISFSymbol.SetText(swSFSymbolRoughnessValue1 = 8, "Ra 0,8")` setzt den Text unter den Strich, bei 1302:2002 und 21920-1 | `ISFSymbol.SetText` (2), `swSurfaceFinishSymbolText_e` | Anforderung über `SetText(8)` |
| Loser Strich über dem Dreieck (g) | Erscheint nur bei Norm 2 (ISO 21920-1), an jedem Symbol; bei 1302:2002 nicht | `SetUserPreferenceInteger(629, 0, 1)` | `zeichnen` stellt die Zeichnung auf ISO 1302:2002 (Abweichung von der Vorlage, im Bericht) |
| Kante am Punkt wählen (h) | `SelectByID2("", "EDGE", x, y, …)` wählt die Kante; Hinweislinie von Rauheit und Rahmen endet am Punkt (102,53 statt 102,56 mm). Bezugsdreieck: `GetLeaderPointsAtIndex` liefert keine Punkte | `IModelDocExtension.SelectByID2` (9), `IAnnotation.GetLeaderPointsAtIndex` (1) | Ansatz wählbar und rücklesbar (letzter Punkt) |
| Mehrfachauswahl vor dem Einfügen (h) | Zwei Kreiskanten bzw. zwei Taschenböden gewählt: eine Hinweislinie | `IAnnotation.GetLeaderCount` | Rahmen: „2 ×“ darüber (`IGtol.SetText(swGTolTextCalloutAbove = 3)`, gelesen „2 ×“); Rauheit: Meldung `RAUHEIT_NUR_EINE_INSTANZ` |

## Nachtrag: Stufe 4, Teil i – Lagen und Hindernisse im Schnitt (28.11.2026)

Spike `spikes/z1_diag_stufe4i.py` auf einer Kopie der SpannplatteZ (Nachbesserung C, Task 5). Die Teil-SHA blieb gleich.

| Frage | Ergebnis | API | Lehre |
|---|---|---|---|
| Bezugsdreieck über das Kantenende hinaus (i) | Bezug B an der linken Kante im Schnitt (x = 75,06, y 122,56–132,56). Mit `SetPosition2` auf (69,06; 139,06) bzw. (69,06; 116,06) liest `GetPosition` dieselbe Lage zurück. SolidWorks zieht die Verlängerung der Kante bis zum Dreieck selbst (PDF), über und unter dem Teil | `IAnnotation.SetPosition2` (3), `GetPosition` | Lagen auf der Verlängerung der Fläche (ISO 5459) sind setzbar; die Verlängerung zählt wie eine Hinweislinie |
| Schraffierte Schnittfläche (i) | Eine `IFaceHatch` im Schnitt A-A; ihre Fläche liefert zwölf Kanten, gleich den Kanten der Schnittfläche (die `sichtbare_kanten` zusätzlich mit Feature „Schnitt1“ führt). Der Rand der Taschenöffnung hinter dem Schnitt gehört nicht dazu | `IView.GetFaceHatches` (0, 2003), `IFaceHatch.Face` (2003), `IFace2.GetEdges` (0, 2001) | „Hinweislinie durch die Schraffur“ ist prüfbar (Punkt in der Fläche), sprachunabhängig |
| Eckpunkte über `ModelToViewTransform` (i) | Alle 20 Eckpunkte des Schnitts liegen 54–89 mm neben dem nächsten Kantenende; in der Hauptansicht stimmt y, x ist um 62,5 mm versetzt | `IView.GetVisibleEntities2` (2), `IVertex.GetPoint` | Eckpunktlagen nicht für Umriss oder Wahl am Punkt verwenden (offen: richtige Umrechnung) |
