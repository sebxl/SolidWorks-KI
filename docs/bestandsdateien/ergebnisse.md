# Paket Bestandsdateien – Ergebnisse

Spec: [2026-10-25-bestandsdateien-design.md](../superpowers/specs/2026-10-25-bestandsdateien-design.md), Plan:
[2026-10-30-bestandsdateien-etappe-1.md](../superpowers/plans/2026-10-30-bestandsdateien-etappe-1.md).

## 1. Spike S18 (2026-10-31, live)

Rechner A, SW 2025 (33.5.0, Lizenztyp 2 = Student), Skripte `spikes/s18_muster.py`, `spikes/s18_bestand.py`, Rohdaten
`docs/bestandsdateien/s18_<zeile>.json`. Alles an selbst erzeugten Dateien unter `<arbeitsordner>/S18/`. Zeit und Speicher je
Lauf: Sekunden, Private Bytes vorher → nachher (mit sichtbaren Fenstern, wenn nicht anders genannt). Maße in mm, Volumen in mm³.

### Musterdateien (S18f)

`tests/referenz/bestand/muster/`: `Lagerdeckel.SLDPRT`, `Muster.SLDASM`, zusätzlich `gm42-10.SLDPRT` (importiertes
`gm42-10.step`, ohne das die Baugruppe nicht öffnet). Volumen Standard 106239,381 (mit Fase), Variante B 106439,381 (Fase
unterdrückt), Soll aus den Maßen stimmt. Öffnen ohne Neuaufbau-Fehler, Warnungen 0. Erzeugung 15 s.

| Merkmal | Im Muster |
|---|---|
| Baum | Skizze1, Aufsatz-Linear austragen1, Skizze2, Schnitt-Linear austragen1 (Tasche), Skizze3, Schnitt-Linear austragen2, Skizze4, Schnitt-Linear austragen3 (Bohrungen), Skizze5, Verstärkungsrippe1 (`Rib`), Fase1 |
| Gesteuert | globale Variable `L` = 100, Gleichung `"D1@Skizze1" = "L"` |
| Verknüpft | Durchmesser beider Bohrungen, Name `Bohrung_D`: `Bohrung_D@Skizze3`, `Bohrung_D@Skizze4` |
| Getrieben | Referenzmaß `D5@Skizze2` (zusätzlich zum Plan, §12 verlangt, dass das Muster diese Fälle abdeckt) |
| Unterbestimmt | Skizze5 (Status 2), alle übrigen Status 3 |
| Konfigurationen | Standard (aktiv), Variante B; Eigenschaft `Bemerkung` nur in Variante B |
| Eigenschaften, Material | Benennung, Revision A; `1.0038 (S235JRG2)` |
| Baugruppe | Lagerdeckel-1 fixiert, gm42-10-1, Deckungsgleich1 auf die Unterseite des Lagerdeckels |

Die Platte liegt in X −50…50, Y −30…30, Z 0…20; `D3`/`D4@Skizze1` binden die linke untere Ecke, `L` schiebt also nur die rechte
Fläche. Git-Ignore greift nicht auf die Muster.

### Tabelle

| Zeile | Frage | Ergebnis | Weg | Zeit/Speicher |
|---|---|---|---|---|
| a | Bleibt die Baugruppe intakt nach Kopie, Änderung, `Save3`, Zurückkopieren? | **Ja.** Warnung 32 (NeedsRegen, normal, Teil neuer als Baugruppe), kein IdMismatch, Komponente nicht `InternalIdMismatch`, neues Volumen da, Verknüpfung gültig; auch nach zweiter Runde | Datei-Kopie, `OpenDoc6`, `SetSystemValue3`, `IModelDoc2.Save3(1, e, w)`, Datei-Kopie zurück | 15 s, 2142 → 3401 MB |
| a | Gegenprobe: bricht `SaveAs3` die ID? | **Nein, Vermutung der Spec falsch.** Neuer Name, gleicher Name in anderem Ordner, Option Copy: alle drei wie oben ohne IdMismatch. Nur ein wirklich neues Dokument unter dem Originalnamen liefert Warnung 33 (Bit 1 IdMismatch), Neuaufbau False, `Deckungsgleich1` Code 48. Der Detektor spricht also an | wie oben, `SaveAs3`; Kontrolle `NewDocument` | im selben Lauf |
| b | Version ohne Öffnen? | Ja, 6 ms, kein Dokument offen: `['18000[2025/268]']`. Neuestes Element vor `[` gegen `GetLatestSupportedFileVersion` (18000) | `ISldWorks.VersionHistory` | 32 s, 1885 → 3432 MB |
| b | Abhängigkeiten ohne Öffnen? | Ja, 10 ms, `GetDocuments` bleibt leer. Liefert Paare Titel/Pfad, `None` bei einem Teil ohne Referenz. `Searchflag` False: gespeicherte Pfade; True: nach Suchregeln aufgelöst; Traverse True für Unterbaugruppen. Abgeleitetes Teil: Basisteil steht drin | `GetDocumentDependencies2(pfad, True, False, False)` | |
| b | Lädt `OpenDoc6` Referenzen vom Originalpfad? | **Baugruppe:** Datei neben der Baugruppe hat Vorrang vor dem gespeicherten Pfad. **Fehlt sie dort, lädt SolidWorks still vom gespeicherten Pfad (Warnung 0).** Deshalb nach dem Öffnen jeden `GetPathName` prüfen. **Abgeleitetes Teil:** Kopie öffnet ohne Warnung, offen ist nur die Kopie, Basisteil nicht geladen, `ListExternalFileReferences` meldet Status 4 (OutOfContext). Ein geändertes Basisteil wurde nicht geprüft | `OpenDoc6` Silent, Suchregeln an (Toggle 0), Laden extern 0 | |
| b | Baum | Name, `GetTypeName2`, `GetParents`, `GetChildren`, `IsSuppressed2(3, Namen)` je Konfiguration gehen. Skizze ist Elter ihres Features. **`GetChildren` kennt nur erklärte Abhängigkeiten:** Rippe steht nicht unter der Tasche, obwohl sie ohne Tasche scheitert | Feature-Kette; Unterskizzen von `HoleWzd` stehen nicht in der Kette (über `GetFirstSubFeature`: `neu1_positionen`, `Skizze6`, je Gewinde `Bohrungsgewinde<n>`, Lauf `c3`) | |
| b | Maße je Konfiguration | `GetSystemValue3(3, Namen)` liefert **0.0 für jede nicht aktive Konfiguration**, nur Umschalten ist verlässlich. Maße unterdrückter Features sind lesbar (`D1@Fase1` in Variante B: 2,0), `null` kommt nicht vor. Maße einer Skizze erscheinen unter Skizze und Feature (Dubletten) | `ShowConfiguration2` + `GetSystemValue3(1, None)` | |
| b | Gesteuert, getrieben | `DrivenState` = 1 bei **beiden**, Gleichung und Referenzmaß; `ReadOnly` 0, `IsReferenceDim` False bei beiden. Trennung nur so: linke Seite einer Gleichung → gesteuert, sonst `DrivenState` 1 → getrieben, sonst treibend | Gleichungen plus `DrivenState` | |
| b | Verknüpft | `IsLinked` True, `GetLinkedText` = Gruppenname. **Maßname wird zum Gruppennamen:** `Bohrung_D@Skizze3`, `Parameter("D1@Skizze3")` liefert `None`. `FullName` endet auf `@Lagerdeckel.Part` bzw. `@Teil8.Part`, also letztes `@…` abschneiden | wie Plan | |
| b | Lage eines Maßes | `IDimension.ReferencePoints` (drei `IMathPoint`): Modellkoordinaten, Punkt 1 und 2 sind die Enden; Abweichung bis 0,1 mm von der Geometrie (z. B. Z 20,1 auf Z = 20) | | 0,09 s je Maß sichtbar, 0,007 s unsichtbar |
| b | Gleichungen, Fehler, Referenzen, Eigenschaften | `Equation(i)`, `GlobalVariable(i)`, `Value(i)` gehen; Text des Bestands `"L"= 100`. `GetWhatsWrong`: Feature, Code, Warnung. `ListExternalFileReferences` geht mit 9 Ausgabeparametern (7 Variant, Long, BSTR). `GetAll3` je Konfiguration. `Extension.GetUserPreferenceInteger(263, 0)` = 5 (MMGS) | | |
| b | Schreibgeschützte Kopie | Öffnet still mit Warnung 2, `IsOpenedReadOnly` True, Lesen geht, `Save3` scheitert mit Fehler 2, SHA-256 unverändert | Attribut auf der Datei | |
| b | Konstruktionstabelle (Lauf `t`, `t2`) | `Extension.HasDesignTable` True, `IsDesignTableDimension` True nur am Tabellenmaß, `DrivenState` 2. **Lesen startet Excel nicht** (0 → 0 Prozesse, frisches SolidWorks). `GetDesignTable` ist auch ohne Tabelle nicht `None`, taugt nicht als Test. **Offen:** Tabellengesteuerte Unterdrückung; ohne `Attach` liefert die Tabelle −2 Spalten und leere Köpfe, `Attach` startet Excel und wurde nicht geprüft | `InsertFamilyTableOpen` nur für den Testaufbau | 17 s + 19 s |
| b | Lesen, Dauer und Speicher (`t2`) | `lies()` komplett: sichtbar 5,3 s, unsichtbar 1,4 s; Fenster +2278 MB, unsichtbar +0 MB. Lesen und Konfigurationswechsel gehen am unsichtbaren Dokument | `DocumentVisible(False, 1)` | |
| c | Maß in allen Konfigurationen | Status 0, beide Konfigurationen neu | `SetSystemValue3(w, 2, None)` | 31 s, 3101 → 5444 MB |
| c | Maß in einer Konfiguration | Status 0, nur die genannte ändert sich, aktive bleibt | `SetSystemValue3(w, 3, Array)`, Array `VT_ARRAY\|VT_BSTR`; Option 1 wirkt auf die aktive | |
| c | Globale Variable, Gleichung | Beide Wege wirken in beiden Konfigurationen, auch mit zwei Konfigurationen. Rückgabe ist kein Status (0 bzw. 1 = Index); `EvaluateAll` und `Status` lieferten teils −1 trotz Erfolg. Maß und Volumen nachmessen | `SetEquationAndConfigurationOption(i, '"L" = 110', 2, None)`, sonst Property-Put per `_oleobj_.Invoke` | |
| c | Gesteuertes Maß direkt gesetzt | **Status 0 (Erfolg), Wert 90, nach `EditRebuild3` wieder 100.** Stiller Fehlschlag, `MASS_GESTEUERT` ist nötig. Getrieben: Status 3, unverändert | | |
| c | Verknüpftes Maß setzen | Partner folgt in allen Konfigurationen | `Parameter("Bohrung_D@Skizze3")`, Option 2 | |
| c | Unterdrücken | `SetSuppression2(0, 2, None)` und `(0, 3, Array)` wirken wie erwartet. **`(0, 1, None)` trifft bei einem vor dem Umschalten geholten `IFeature` die alte Konfiguration:** in Variante B aktiv wurde Standard unterdrückt; neu geholtes Objekt trifft die aktive. Immer Option 3 mit Namen. Nach Option 3 auf die aktive Konfiguration zeigte das Volumen den alten Stand, bis umgeschaltet wurde. Unterdrückt man die Grundplatte, gehen Tasche und Fase mit, die Rippe nicht | `FeatureByName` nach jedem Wechsel | |
| c | Löschen | Schnitt Option 0: Skizze bleibt. Option 2 (Absorbed) oder 3: Skizze mit weg. Skizze mit Kind: `False`, nichts gelöscht, auch mit Children. Grundplatte Option 0: **Fase geht trotzdem mit**, Rest mit Fehlern; Option 1: alle Kinder weg, Rippe bleibt mit Fehler 1. Gleichung `D1@Skizze1` bleibt. Tasche gelöscht: Rippe Code 1 | `Select2`, `DeleteSelection2(3)`, kein Dialog; Baum vorher/nachher vergleichen | |
| c | Handler auf fremder Fläche | `normbohrung` M6 mit `-rand`/`mitte` und `flaeche: {nahe}` baut im Muster: Achsen bei X −38, Y ±24, Maße 12 und 48, Volumen stimmt, keine Fehler, 6,6 s. Beide Unterskizzen Status 3 (`unterskizzen` in `s18_c3.json`) | `Kontext`, `normbohrung(ctx, f)` | 30 s, 440 → 2437 MB |
| c | Neues Feature und Konfigurationen | Gebaut in Standard: in beiden aktiv. **Gebaut in Variante B: in Standard unterdrückt.** `SetSuppression2(1, 2, None)` holt es zurück. Punkt `feature` setzt das darum immer ausdrücklich | | |
| c | Umbenennen | `feature.Name = …` geht, Umlaute und Leerzeichen ok. **Doppelter Name: keine Ausnahme, Name bleibt still alt.** Zurücklesen | | |
| c | Verschieben (`nach`) | `IModelDocExtension.ReorderFeature(name, ziel, 3)` geht (2 = davor, 1 = ans Ende mit Ziel `""`), Volumen gleich, Datei danach sauber (`kontrolle_bohrung_b`). **Unmöglicher Zug (Rippe vor Skizze1) beschädigt die beim Zug aktive Konfiguration still und dauerhaft:** Rückgabe False, aber in Standard steht die Rippe vorn, Neuaufbau False, Code 1, Volumen −450. Variante B bleibt heil: eigene Reihenfolge, 0 Fehler, Volumen gleich. **Die Feature-Reihenfolge gilt je Konfiguration.** `Save3` meldet 0/0, nach dem Öffnen ist der Schaden unverändert da, auch `ForceRebuild3` heilt ihn nicht. Mit Variante B aktiv sehen Baum und `fehlerliste` nichts: daher `fehler: []` in c12 trotz fehlender Rippe. Dreimal gemessen, auch ohne Bohrung und mit Standard aktiv beim Speichern. Nach `False` Lauf verwerfen, jede Prüfung je Konfiguration | Lauf `c3`, `je_konfiguration` | 74 s, 433 → 3512 MB |
| c | Speichern | `Save3`: aktive Konfiguration bleibt die zur Speicherzeit aktive. Lauf muss also vor dem Speichern auf `aktiv` zurückschalten | | |
| c | Sporadisch | Einmal `RPC_E_DISCONNECTED` im Handler bei 5,4 GB Private Bytes (`GetEdges` einer Fläche). Auf frischem SolidWorks in zwölf Aufrufen nicht wiederholbar, auch nicht nach Konfigurationswechseln. Ursache später gefunden: dieselbe Stelle wie in „Trennung: Ursache“ unten | | |
| d | Kopie aus zwei Dokumenten kombinierbar? | **Ja.** `Copy2(True)` aus zwei offenen Dokumenten, `Operations2` geht; Original bleibt unverändert. Mit Typinfo: `r, code = ziel.Operations2(15902, werkzeug, 0)`, Rohzahl statt ByRef | zwei Richtungen, je Körper | 37 s, 719 → 4790 MB (davon 3200 MB ein sichtbarer Vergleich) |
| d | Unveränderte Geometrie | **Leer, keine Splitter:** `(None, 0)` in beiden Richtungen und Konfigurationen, auch nach öffnen und `Save3` | | 0,04–0,07 s |
| d | Kleine Bohrung Ø1 × 2 | Ein Körper, Volumen 1,570796 (Soll 1,5708), Hüllquader exakt (44,5…45,5 / 24,5…25,5 / 18…20), in beiden Konfigurationen | | 0,05 s |
| d | Verschobene Fläche | +50 µm: 59,9; +5 µm: 5,99; +0,5 µm: 0,599; +0,05 µm: 0,0409, Box 0,1 µm. Alles sicher unter der Toleranz sichtbar | | je 0,05 s |
| d | Bohrung 20 µm versetzt | Je Richtung ein Sichelkörper 3,2, Volumen gesamt gleich: nur die Differenz findet das | | |
| d | Nur eine Konfiguration | Standard leer, Variante B zwei Körper je 705 | je `ShowConfiguration2` in beiden, Körper neu holen | |
| d | Mehrkörper, 23 Flächen | Importiertes `gm42-10` (2 Körper): leer, Codes 0, 0,24 + 0,13 s, +0 MB. Größere Teile nicht gemessen, die Abnahme an der Kollegen-Datei liefert den Wert | jedes Ziel minus alle Werkzeuge | |
| d | Gleiche Titel | Zweites Dokument gleichen Namens: `None`, Fehler 65536. Präzisierung 5 bleibt: `vorher_<name>` als Datei-Kopie | | |
| d | Unsichtbar | Differenz am unsichtbaren Dokument geht (+0 MB, gegen +3,2 GB für zwei Fenster). **STL-Export am unsichtbaren Dokument: SolidWorks stürzt ab (RPC-Fehler, zweimal reproduziert).** Sichtbar geht er | | |
| d | STL ohne Ausrichtung | **Taugt nicht als gleichwertiger Rückfall:** Gleiche Geometrie zeigt 0,030 mm Abstand (1799 von 60000 Punkten über 0,01), Ø1-Bohrung und 50-µm-Fläche ändern das nicht. Die Vorgabe 0,01 mm ist so nicht prüfbar | `exportiere_stl`, `Oberflaeche.abstand` | 0,5 s |
| d | Bild mit Differenzkörpern | Geht: Dokument bleibt offen, Körper halten, `Display3(model, 0x0000FF, 0)`, `SaveAs3` als PNG; Ø1 ist im Gesamtbild nur ein Punkt | Beleg `S18/d/differenz.png` | |
| e | Feature hervorheben | `Select2` genügt, PNG zeigt die Flächen farbig | `Select2`, `sw.speichere(kopie=True)` | 9 s, 436 → 3094 MB |
| e | Maß hervorheben | Bloße Auswahl zeigt nichts, das Maß ist unsichtbar (Lauf `e`). Mit `Extension.SetUserPreferenceToggle(31, 0, True)` und `(32, 0, True)` (Beschriftungen, Feature-Maße) sind die Maße sichtbar. Dann **`ann.Color = 0x0000FF`** (Farbe 0 → 255): rot, deutlich, in Vorne wie Isometrie. Auswahl per `SelectByID2(f"D2@Skizze3@{TEIL}", "DIMENSION", …)` (1 Objekt, Typ 14) oder `Select3(False, CreateSelectData)`: hellblau, schwach, Feature-Maße sind von Haus aus blau. `Select3(False, callout_leer())`: False. `GetSaveFlag` bleibt False, Datei unverändert (SHA-256 gleich). `ViewZoomtofit2` passt nur die Geometrie ein, unten fehlte ein Maß (`50,00`); in der Isometrie überlagern sich viele Maße, die Skizzen-Ansicht ist die bessere | Lauf `e2`, Beleg `s18_e2.json`, `S18/e2/d_farbe.png` | 8 s, 434 → 915 MB |
| g | Datei-Kopie als Lauf-Ordner | **Trägt:** Alles kopiert, `OpenDoc6` lädt aus dem Lauf-Ordner, Original bleibt byteweise gleich. Nur das Teil speichern: nur dessen SHA-256 ändert sich, Baugruppe und STEP-Teil bleiben gleich, `GetSaveFlag` der Baugruppe False. Nur öffnen ändert nichts. Baugruppe speichern ändert nur sie und schreibt die Lauf-Pfade hinein | Weg 1 | 11 s, 2746 → 4031 MB |
| g | Geändertes Teil neben die alte Baugruppe | Warnung 32, kein IdMismatch, Verknüpfung gültig: Der Rückweg von Etappe 2 braucht die Baugruppe nur, wenn ein Punkt sie ändert | | |
| g | Komponente leicht geladen | Nach `sw_neustart` Zustand 1, `GetModelDoc2` = `None` (Toggle 25 an); im ersten, nicht neu gestarteten Lauf Zustand 2. Mit `OpenDoc6`-Option 64 (OverrideDefaultLoadLightweight): Zustand 2, Dokument da | Option 1\|64, sonst Teil unter seinem Pfad öffnen | |
| g | `ReplaceReferencedDocument` | Geht ohne Öffnen, Pfade danach im Lauf-Ordner, keine Warnung, **ändert aber die SHA-256 der Baugruppe**. Für Etappe 2 unnötig, solange alle Dateien daneben liegen | Weg 3 | |
| g | Pack and Go | **Nicht erreichbar.** `GetPackAndGo` hat laut Index 0 Parameter, per IDispatch „Parameter nicht optional" bzw. „Unzulässige Parameteranzahl" (Methode, Property-Get, `InvokeTypes`). Bräuchte außerdem ein offenes Dokument. Nicht nötig | | |

### Nachträge aus Task 5 (live, 2026-10-31)

- **`IsSuppressed2(3, Namen)` liefert in Dokumentreihenfolge, die Reihenfolge der Namen zählt nicht:** `['Variante B', 'Standard']`
  und `['Standard', 'Variante B']` geben beide `(False, True)` für die in Variante B unterdrückte Fase. Im Spike fiel das nicht auf,
  weil dort Dokumentreihenfolge gefragt wurde. Je Name einzeln fragen.
- **PNG-Name:** `SaveAs3` lehnt `@` im Dateinamen ab (Fehler 8, `swFileNameContainsAtSign`), und `@` steht in jedem Maßnamen.
- **Maßbild:** Schattiert verdeckt der Körper Maße im Innern, von der Tiefe der Tasche (`D1@Schnitt-Linear austragen1`) blieben in
  der Isometrie nur Pfeilreste ohne Zahl. Mit `ViewDisplayWireframe` ist die rote Zahl lesbar, auch die Skizzen-Ansicht bleibt klar.
- Bestand mit `HoleWzd` (Lauf `c3`): Unterfeatures, ihre Skizzen und Maße werden gelesen. Bestand mit Tabelle (Lauf `t`):
  `tabelle` True, Tabellenmaß gesteuert mit Werten 8 und 6, kein Excel-Prozess danach. Öffnen mit Option 2 (ReadOnly) und PNG aus dem
  nur lesend geöffneten Dokument gehen.

### Nachträge aus Task 6 (live, 2026-10-31)

Sonde an Kopien des Musters unter `<arbeitsordner>/S18-T6/`. Skript und Rohdaten sind Wegwerf, der Ordner darf gelöscht werden.

- **`ReorderFeature` wirkt nur in der aktiven Konfiguration, auch bei Erfolg:** Rückgabe True, Standard hat die neue Reihenfolge,
  Variante B behält die alte. Mit Variante B aktiv wirkt derselbe Zug dort, nach Speichern und Öffnen stimmen beide. Punkt
  `feature` mit `nach` läuft darum je Konfiguration und prüft den Baum je Konfiguration; False heißt weiterhin Abbruch, nie speichern.
- **Aufgenommene Skizzen sind Unterfeatures:** `GetFirstSubFeature` eines Schnitts liefert seine Skizze, beim Verschieben geht sie
  mit (`neu1_skizze`, `neu1`). `loeschen` erlaubt deshalb die Unterfeatures des Features und der `kinder`.
- **Aufheben mit Option 3:** `SetSuppression2(1, 3, alle Namen)` holt ein in Variante B entstandenes Feature in Standard zurück, seine
  Unterfeatures folgen (`neu1_positionen`, `Skizze6`, `Bohrungsgewinde1`), Volumen stimmt. Option 2 ist nicht nötig.
- **Veraltetes Volumen nach Option 3 (Zeile c) ließ sich nicht wiederholen:** Unterdrücken in der aktiven Standard zeigte sofort das
  neue Volumen, auch nach Neuaufbau, `ForceRebuild3` und Umschalten gleich. `pruefe_stand` prüft die aktive trotzdem zuletzt.
- **Material gilt je Konfiguration:** `SetMaterialPropertyName2("", …)` trifft nur die aktive, Variante B behält das alte. Mit Namen
  gesetzt wirken beide, `""` beim Lesen meint ebenfalls die aktive. Punkt `material` setzt je Name, die Aufnahme liest `materialien`.
- **Eigenschaften:** `Add3` liefert 0, `Delete2` 0, bei fehlender Eigenschaft 1. Zurücklesen statt Rückgabe auswerten.
- **Lizenz:** `ISldWorks.GetCurrentLicenseType` gilt der Sitzung, `IModelDocExtension.GetLicenseType` der Datei (laut Index bei
  kommerziellen Lizenzen immer 0). Hier beide 2, vor und nach `Save3`. Das Protokoll führt beide (`lizenz.sitzung`, `lizenz.datei`),
  Task 9 wertet `sitzung` aus.
- **`RPC_E_DISCONNECTED` zum zweiten Mal, wieder sporadisch:** einmal im Punkt `feature` (Normbohrung) des ersten Bau-Laufs einer
  SolidWorks-Sitzung, bei unter 1 GB Private Bytes, also nicht am Speicher allein. Nicht wiederholbar: zwölf Folgen p1 bis p5 ohne
  Aufnahme, zweimal der Live-Test in derselben Sitzung, einmal auf frischem SolidWorks. Vermutet und widerlegt: altes `IFeature` nach
  dem Umschalten, erster Einsatz des Bohrungsassistenten in der Sitzung. Die Stelle ist unbekannt, der Lauf hatte keinen Traceback. Der
  Bau brach sauber ab: nichts gespeichert, Dokument geschlossen, der nächste Lauf ging. Keine Wiederholung eingebaut.
  Überholt, siehe „Trennung: Ursache“ unten.

### Nachträge aus Task 8 (live, 2026-10-31)

Sonde an einer Kopie des Musters, nur lesend und unsichtbar geöffnet; Vergleichskörper aus `IModeler.CreateBodyFromBox3`. Skript ist
Wegwerf.

- **Getrennte Körper liefern das Ziel unverändert, Code 0,** ob sich die Hüllquader überlappen (Quader in der Tasche, Platte minus
  Quader und Quader minus Platte) oder nicht (Quader 500 mm entfernt). `(None, 0)` kommt nur bei gleichen Körpern. Damit trägt „jedes
  Ziel minus alle Werkzeuge" aus Zeile d ohne Paaren nach Lage: Ein Körper auf nur einer Seite ist von selbst als Ganzes eine
  Abweichung, ein zerschnittener Körper braucht keinen Sonderfall. Der Enum kennt `swBodyOperationDisjointBodies` (5) und
  `swBodyOperationNoIntersect` (1067), beide kamen hier nicht vor; ein Code ungleich 0 heißt „nicht nachgewiesen".
- **Differenz geht auch an nur lesend geöffneten Dokumenten** (`Copy2`, `Operations2`, `GetMassProperties`).
- **Toleranz:** Sicher unter der Toleranz ist nur eine kleinste Box-Kante darunter. `dicke` schätzt daneben `2 · 2·Volumen/Fläche`: `2V/A` ist
  die mittlere Dicke, die größte liegt bis zum Doppelten darüber (Sichel 20 µm aus Zeile d: im Mittel 12,7 µm). Das Mittel gilt aber für den
  ganzen Körper: 1 µm auf 100 × 60 plus Buckel 2 × 3 × 3 mm ergibt 0,008. Außerhalb aller Bereiche heißt „nur im Mittel dünn" darum
  `ok: None`. Live: Fläche +5 µm: Volumen 5,99, Dicke 0,005, zählt nicht. Sichel 20 µm: Fläche und Dicke wie gerechnet, Mangel; 4 µm: offen.
- **Bilanz:** `koerper_differenz` vergleicht die Summe der Differenzkörper mit der Volumenänderung beider Stände; ein stilles leeres
  Ergebnis wäre sonst ein falsches „ok". Flächenkörper sieht `Operations2` hier nicht, sie machen die Konfiguration „nicht nachgewiesen".

### Nachträge aus Task 10 (live, 2026-10-31)

Referenz `tests/referenz/bestand/lagerdeckel_rev.yaml`, sechs Punkte, 12,7 s Bau, 21 Prüfungen. **Bestanden in Lauf 3**, Prüfer „bestanden“ ohne Mängel,
`swki status` „bestanden“. Lauf 1: Code-Prüfungen ohne Mangel, Prüfer verlangte den Beleg für p5. Lauf 2: Abbruch im Bau, `RPC_E_DISCONNECTED`.

Ausgabe: nur `Lagerdeckel.SLDPRT` unter dem Originalnamen in `<auftrag>/ausgabe/`, SHA-256 gleich Lauf 3 (65df85ba…), nichts unverändert. Warnung
`BESTAND_LIZENZ` wie erwartet (Sitzung und Datei `swLicenseType_Student`), keine `BESTAND_ORIGINAL_GEAENDERT`. Das Muster ist unverändert (048eed27…,
`git status` leer). `swki bericht`: Status bestanden, Ausgabeliste, Lizenz, „Wirkung auf Baugruppen nicht geprüft“. Die Baugruppenprobe nimmt eine Ausgabedatei
eines eigenen, kleineren Laufs (`test_datei_id_bleibt`), nicht die dieser Referenz.

- **Volumen vorab gerechnet, gemessen auf 0,001 genau:** Variante B +10603,567, Standard +10583,567 mm³. Die Differenz sind die 20 mm³
  der Fase auf der Verlängerung, `volumen_delta` trägt darum die Mitte mit 0,2 %.
- **Differenzkörper können verschmelzen (überlegt, nicht gemessen):** Fase unterdrückt und `L` zugleich ergäbe vermutlich einen Körper über
  beide Stellen, die Fase läuft bis an die rechte Stirnfläche. Er passte in keinen engen Bereich. Die Referenz unterdrückt deshalb die
  Rippe. Für echte Dateien: Stoßen zwei Punkte aneinander, brauchen sie einen gemeinsamen Bereich.
- **Prüfer, Lauf 1 nicht bestanden:** `punkt:p5` belegte nur, dass das Feature da ist; Gewindegröße und -tiefe zeigen weder Differenz noch
  Bild. Neue Features werden seither gegen die freigegebene Kopie gemessen, je Konfiguration (`swki/bestand/feature_messung.py`),
  Achsen gegen `positionen` (Toleranz 0,01 mm). `masse_pruefen` kennt keinen Messpunkt auf einer Bohrungsachse, `{punkt}` gegen eine
  Fläche prüft nur die Fläche. Live belegt: Normbohrung (auch versetzt als Mangel), Formschräge, Stirnrad; Zahnstange nur als Baustein
  des Teils.
- **`RPC_E_DISCONNECTED` beim ersten Bau nach `sw_neustart`, jetzt nachstellbar:** Referenz Lauf 2 brach in p5 (Normbohrung) ab, SolidWorks lief weiter,
  nichts gespeichert, kein Dokument offen. Probe, je Versuch Neustart und dann ein Bau: ok, Fehler, ok, ok. Ohne Neustart lief derselbe Bau sofort durch
  (Lauf 3). Das passt zum Fall aus Task 6 (erster Bau der Sitzung, unter 1 GB) und widerspricht dem dortigen Schluss, es sei nicht wiederholbar. Ursache
  offen; Stelle im Punkt `feature`. Trifft auch `swki durchlauf --neustart`. Ein Fehlversuch zählt als Lauf. Überholt: Am Neustart lag es nicht, siehe
  „Trennung: Ursache“.
- **Eine Variable, eine Folge:** Das Muster hat nur `"D1@Skizze1" = "L"`, ein `gleichung`-Punkt auf `L` hat genau eine Folge. Die zweite
  Folge der Referenz kommt aus dem verknüpften Maß (`Bohrung_D@Skizze4`).
- **S18a am Ergebnis (`test_datei_id_bleibt`):** Ausgabe neben einer Kopie der Musterbaugruppe: kein IdMismatch, keine fehlende
  Referenz, Neuaufbau ohne Fehler, neues Volumen in der Komponente.

### Trennung: Ursache (Task 10a, live, 2026-10-31)

**Ursache:** `normbohrung` holte die Skizzenfläche vor dem Öffnen der Positionsskizze als `IFace2` und benutzte sie erst darin
(`Skizzierer._flaechenkanten`: `GetEdges`). Dazwischen liegt `InsertSketch(True)`, und das Öffnen rollt den Körper zurück (20 auf 18 Flächen).
Über Neuaufbauten gültig bleibt laut Hilfe nur eine Safe Entity (`IEntity.GetSafeEntity`). Mit Wächter wurde die Fläche **in jedem Lauf** getrennt, nur der
Zeitpunkt wechselt. Fällt er auf das Öffnen, reißt `GetEdges`; fällt er auf das Schließen oder auf `ForceRebuild3`, merkt es niemand, weil die Fläche dann nicht
mehr gebraucht wird. Skript: `spikes/s18_trennung.py`, Bau wie `swki.bestand.bau` an einer Kopie des Musters, Trace je Versuch.

**Stelle (Frage 1):** In allen 10 Abbrüchen derselbe Stacktrace: `positionen_festlegen` → `lagen_festlegen` → `massplan` → `_bezugskante` →
`_flaechenkanten`, `self.se.flaeche.objekt.GetEdges`. Das ist die Stelle aus S18c („`GetEdges` einer Fläche“, gleicher Fall `-rand`) und vermutlich die
aus Task 6 (auch p5, dort ohne Traceback). Der Wächter fragt vor jedem weiteren COM-Zugriff die Fläche (`GetBox`) und grenzt so den Aufruf ein, der sie trennte
(„Schließen“: `InsertSketch` oder das Umbenennen der Skizze danach, das läuft nicht über die Spur):

| Fall | Neustart | Läufe | getrennt beim Öffnen, Bau bricht ab | beim Schließen | bei `ForceRebuild3` |
|---|---|---|---|---|---|
| Referenz p1 bis p6 | ja | 14 | 1 | 0 | 13 |
| Referenz p1 bis p6 | nein | 10 | 1 | 0 | 9 |
| Referenz, ohne `sw.schnell` | ja | 12 | 3 | 0 | 9 |
| nur p5 | ja | 12 | 0 | 6 | 6 |
| neues Teil, Klotz und Normbohrung `-rand` | ja | 12 | 0 | 0 | 12 |

Ohne Wächter: 21 Läufe der Referenz mit Neustart, 5 Abbrüche. Zusammen 10 Abbrüche in 57 Läufen der Referenz (18 %).

**Woran es nicht liegt (Frage 2):**

- **Neustart:** Ohne Neustart 1 von 10. Die Probe aus Task 10 (ok, Fehler, ok, ok) war Zufall bei kleiner Zahl. Auch der Speicher nicht: Abbrüche ab 430 MB, S18c bei 5,4 GB.
- **`sw.schnell`:** ohne ihn 3 von 12.
- **Normbohrung allein oder Fremddatei allein:** Getrennt wird auch im neuen Teil und bei nur p5, dort aber nie beim Öffnen (je 0 von 12). Es braucht offenbar die
  Punkte davor. Welcher von p1 bis p4 das bewirkt und warum der Zeitpunkt springt, ist **nicht** geklärt und für die Behebung nicht nötig. 0 von 12 schließt bei 18 % wenig
  aus (Zufall 9 %): Ein Abbruch im normalen Teilebau mit Randbezug ist nicht belegt, aber auch nicht ausgeschlossen. Die Behebung gilt für ihn mit.
- **Zeit:** Die Fläche überlebt `HoleWizard5` (dieselbe `IFace2` liefert danach 11 statt 10 Kanten) und in Fall `min` drei Sekunden in der offenen Skizze. Warten allein trennt nicht.

**Kleinste Reproduktion (Frage 3):** Für die Trennung selbst genügt das neue Teil: eine Normbohrung mit `bezug: -rand`, Wächter auf der Fläche, 12 von 12 getrennt.
Für den Abbruch ist die kleinste bekannte Folge die Referenz p1 bis p5 (`--fall voll_alt`). Ohne Skizzierer (Fall `min`: Fläche holen, Bohrung, Fläche holen, Skizze öffnen,
sofort oder nach bis zu 3 s fragen, Skizze schließen) kam in 39 Proben keine Trennung; dort ändert sich die Skizze nicht und `ForceRebuild3` fehlt.

**Behebung:** `positionen_festlegen` bekommt die Ebene als Funktion und ruft sie erst in der offenen Skizze auf. Dort sind die Kanten ohnehin die der ungebohrten Fläche
(10, alt und frisch gleich). `{flaeche}`-Bezüge lösten schon immer dort auf. Danach **30 von 30** Läufen der Referenz mit Neustart ohne Abbruch; bei 18 % wäre das Zufall mit
0,3 %. Der Wächter auf der frischen Fläche: 30-mal lebend bis `ForceRebuild3`. Gegenprobe auf demselben Code, nur die Ebene wieder vor dem Öffnen geholt (`--fall voll_alt`):
4 Abbrüche in 10 Läufen. Keine Wiederholung, kein Abfangen: Ein Bau, der abbricht, speichert weiter nichts.

Ein Anker `{nahe}` genau auf der Bohrung findet die Fläche jetzt, weil die Bohrung in der offenen Skizze zurückgerollt ist. Die Zweige „keine Fläche gefunden“ in
`skizzenebene_nach_bohrung` bleiben als Absicherung.

### Folgen für die Tasks

- **Task 5 (Aufnahme):** Werte durch Umschalten lesen, Dubletten zusammenlegen, `zustand` wie oben ableiten, Namen ohne letztes
  `@…`. Unsichtbar öffnen spart 2,3 GB; `HoleWzd` über Unterfeatures. Tabelle: `HasDesignTable`, nie `GetDesignTable is None`.
  Baum und Fehler je Konfiguration lesen (`neuaufbau` trägt die Konfiguration): `fehlerliste` sieht nur die aktive, die
  Feature-Reihenfolge kann je Konfiguration abweichen.
- **Task 6 (Bau):** Unterdrückung beim Nachmessen je Konfiguration einzeln lesen (Nachträge aus Task 5). `alt` und `neu` nach Neuaufbau nachmessen (Status 0 beweist nichts), nach jedem Konfigurationswechsel
  `FeatureByName` und `GetEquationMgr` neu holen, Unterdrücken nur mit Option 3, neue Features ausdrücklich in allen
  Konfigurationen aufheben, Namen zurücklesen, Baum nach `loeschen`/`nach` vergleichen, vor dem Speichern auf `aktiv` zurück. **Vor dem Speichern und nach
  jedem Fehlschlag Volumen, Fehler und Baum in allen Konfigurationen prüfen, nicht nur in der aktiven:** `ReorderFeature` = False
  beschädigt die aktive Konfiguration dauerhaft (Lauf `c3`), `Save3` meldet Erfolg. Dann Lauf abbrechen, nie speichern; der nächste
  Lauf beginnt ohnehin ab der Bestandskopie.
- **Task 7:** `kinder` aus `GetChildren` erfassen nicht alles; Tasche → Rippe zeigt erst der Neuaufbau-Vergleich.
- **Task 8:** Differenz in `koerper_differenz` wie oben, beide Dokumente unsichtbar. Toleranz über die Dicke: Der Körper einer um
  5 µm verschobenen Fläche ist exakt und muss unter 0,01 mm als „unter Toleranz" gelten (Vorschlag: `2·Volumen/Fläche` oder
  kleinste Box-Kante). STL-Rückfall nur mit sichtbaren Dokumenten und nur als Hinweis, nicht als Nachweis.

### Offen

- Tabellengesteuerte Unterdrückungszustände ohne Excel erkennen (siehe Zeile b, Entscheidung F4).
- Externe Referenzen außer abgeleitetem Teil (gespiegelt, im Kontext, Gleichungsdatei): `GetDocumentDependencies2` nur am
  abgeleiteten Teil gemessen. Verhalten bei geändertem Basisteil nicht geprüft; Etappe 1 lehnt solche Teile ab.
- Differenz an großen Teilen: Laufzeit und Speicher nur bis 23 Flächen gemessen.
- Die Datei läuft hier durch eine **Student-Lizenz** (Lizenztyp 2). Ob eine so gespeicherte Datei beim Kollegen mit Vollversion
  anders erscheint (Wasserzeichen, Hinweis), lässt sich auf diesem Rechner nicht messen; `Save3` und ID-Probe sagen dazu nichts.
