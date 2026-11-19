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
