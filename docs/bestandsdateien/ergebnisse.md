# Paket Bestandsdateien – Ergebnisse

Spec: [2026-10-25-bestandsdateien-design.md](../superpowers/specs/2026-10-25-bestandsdateien-design.md), Plan:
[2026-10-30-bestandsdateien-etappe-1.md](../superpowers/plans/2026-10-30-bestandsdateien-etappe-1.md).

## 1. Spike S18 (2026-10-31, live)

Rechner A, SW 2025 (33.5.0, Lizenztyp 2 = Student), Skripte `werkzeuge/bestand_muster.py` (damals `spikes/s18_muster.py`), `spikes/s18_bestand.py`, Rohdaten
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

Ein Anker `{nahe}` genau auf der Bohrung findet die Fläche jetzt, weil die Bohrung in der offenen Skizze zurückgerollt ist (live: `test_nahe_anker_genau_auf_einer_bohrung`).
Die Zweige „keine Fläche gefunden“ in `skizzenebene_in_positionsskizze` (vormals `skizzenebene_nach_bohrung`) bleiben als Absicherung.

### Gesamtregression (Task 11, live, 2026-10-31)

Stand: Commit „Bestandsdateien Etappe 1: Skill, Regeln, Ergebnisse“, Rechner A, jeder Test der Suite auf frischem SolidWorks (`-m werkzeuge.live_frisch tests/referenz`).

| Lauf | Ergebnis |
|---|---|
| `pytest` | 2179 bestanden, 185 abgewählt (`sw`) |
| `swki api pruefe-code` | ohne Befund, `max_jahr` 2025 |
| Regressions-Suite | 12 von 12, darunter Lagerdeckel 38,5 s, 3440 MB Spitze; größte Spitze Zahnstangentrieb 6262 MB, 88,4 s; Motorhalter mit der Herstellerdatei |
| `-m werkzeuge.schnellbau_abgleich --ohne-json` | alle Eigenteile `richtig`, nicht gespiegelt, Volumenabweichung höchstens 0,0008 %; Formplatte ohne Vergleich (`f10` ist `skript`, `SCHNELLBAU_NICHT_UNTERSTUETZT`, kein Gegenstück vorgesehen) |
| Live `test_live_bestand`, `test_live_bemassungsbezug`, `test_live_normbohrung` | 32 von 32 |

Der Live-Lauf des Lagerdeckels steht seither in `tests/referenz/test_bestand.py`, damit `tests/live_einzeln.py tests/referenz` ihn mitnimmt; die Suite davor sah ihn nicht.

### Abschlussreview (live, 2026-10-31)

- **`VersionHistory` und `GetDocumentDependencies2` laufen am Originalpfad, nur lesend, bewusst vor der Kopie:** Eine neuere oder referenzierende Datei hinterlässt so keine
  Aufnahme. Beide öffnen kein Dokument (Zeile b, `GetDocuments` bleibt leer); `OpenDoc6` läuft nur an der Kopie. Zeigt sich die Referenz erst im offenen Dokument (Gleichungsdatei, nächster
  Punkt), entfernt `aufnehmen` `bestand-<n>/` samt schreibgeschützter Kopie wieder; der Ordner machte sonst jede Spec auf die Aufnahme davor zu `BESTAND_VERALTET`.
- **Mit einer Datei verknüpfte Gleichungen sieht nur `IEquationMgr`:** An einer verknüpften Kopie des Musters liefern `GetDocumentDependencies2` und
  `ListExternalFileReferences` beide nichts, `LinkToFile` True und `FilePath` den gespeicherten Pfad. Vorher `False` und `""`. Gesetzt wird `FilePath` vor `LinkToFile`, wie der Index verlangt. Die Probe steht in `test_verknuepfte_gleichungen_lehnt_aufnehmen_ab`.
- **Einheiten:** `swUnitSystem_e`: 1 CGS, 2 MKS, 3 IPS, 4 Custom, 5 MMGS. Kopie des Musters im offenen Dokument auf IPS gestellt (`SetUserPreferenceInteger(263, 0, 3)`, nicht gespeichert):
  `Value` von `L` bleibt 100, nach dem Neuaufbau steht `D1@Skizze1` auf 2,54 m, also 100 Zoll. Gleichungen rechnen in der Einheit der Datei. `BESTAND_EINHEIT` selbst ist als Unit-Test belegt.
- **Gleichung auf eine Unterdrückung (Kopie des Musters, sichtbar, nicht gespeichert):** `"Fase1" = "suppressed"` wirkt, `"unsuppressed"` hebt wieder auf, der Text steht so im Gleichungsmanager. Am
  unsichtbaren Dokument lieferte derselbe `Add2`-Aufruf −1, nicht weiter untersucht. Wird die Gleichung gelöscht, bleibt das Feature unterdrückt. `"Fase1@Lagerdeckel.Part" = "unsuppressed"` und
  `"$STATE@Fase1" = "unsuppressed"` nimmt `Add2` an, sie hoben die Unterdrückung nicht auf. `validieren` erkennt das Feature links ohne Dokument und ohne Groß-/Kleinschreibung, `$STATE@` nicht.

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

- **Abnahme an einer echten Kollegen-Datei** (Spec §12): Stand 2026-10-31 gibt es keine; die Datei stellt der Nutzer bereit, Kennzahlen kommen hierher.
- **SW 2026:** Die Firmenrechner laufen mit SW 2026 und Vollversion (Nutzer 2026-10-31), alles hier ist unter SW 2025 gemessen. Ablauf:
  [inbetriebnahme-firmenrechner.md](inbetriebnahme-firmenrechner.md).
- Tabellengesteuerte Unterdrückungszustände ohne Excel erkennen (siehe Zeile b, Entscheidung F4).
- **`"$STATE@Fase1"`:** Die Probe im Abschlussreview sah nur, dass `Add2` die Schreibweise annimmt und sie einmal nichts aufhob. Das braucht eine saubere eigene Probe (frisches Dokument, beide
  Richtungen, Neuaufbau). Steuert sie doch, muss `validieren` sie erkennen; heute sähe es sie nicht, und der Neuaufbau nähme einen `unterdruecken`-Punkt zurück.
- Externe Referenzen außer abgeleitetem Teil und Gleichungsdatei (gespiegelt, im Kontext): `GetDocumentDependencies2` nur am abgeleiteten Teil gemessen. Verhalten bei geändertem Basisteil
  nicht geprüft; Etappe 1 lehnt solche Teile ab.
- **Laufzeit großer Dateien:** Aufnahme, Differenz und Prüfung nur bis 23 Flächen gemessen.
- **Mehrkörper:** Differenz nur an `gm42-10` (2 Körper, unverändert) gemessen; Änderungen an einem Mehrkörperteil sind nicht gelaufen.
- **Abgeleitete Konfigurationen:** Das Muster hat nur Konfigurationen auf gleicher Ebene; `GetConfigurationNames`, Umschalten und `alle` sind an Kind-Konfigurationen nicht gemessen.
- **What's-Wrong-Dialog an einer Datei mit Fehlern:** Das Muster öffnet fehlerfrei. Ob `OpenDoc6` Silent und das Lesen an einer Datei mit Neuaufbau-Fehlern ohne Dialog durchlaufen, ist nicht gemessen.
- Rechner A ist eine **Student-Lizenz** (Lizenztyp 2), die Firmenrechner nicht. Für den Firmenbetrieb ist die Frage damit erledigt. Offen bleibt nur, wie eine auf
  Rechner A gespeicherte Datei bei einer Vollversion erscheint (Wasserzeichen, Hinweis); `BESTAND_LIZENZ` warnt dort weiter.

## 2. Spike S19 (Etappe 2, live)

Rechner A, SW 2025, Skripte `werkzeuge/bestand_muster.py` (Hubeinheit), `spikes/s19_baugruppe.py`, Rohdaten `docs/bestandsdateien/s19_<zeile>.json`.
Alles an Kopien der selbst erzeugten Musterbaugruppe unter `<arbeitsordner>/S19/`, vor jeder Zeile frisches SolidWorks. Die Pflichtfragen
tragen ihre Nummer aus `FRAGEN` im Skript. Zeit und Speicher je Zeile: Sekunden, Private Bytes Start → Spitze.

### Musterbaugruppe Hubeinheit (2026-11-05)

`tests/referenz/bestand/muster/baugruppe/`: `Hubeinheit.SLDASM`, `teile/{Grundplatte,Schlitten,Anschlag}.SLDPRT`, dazu `Muster.SLDASM`,
`Lagerdeckel.SLDPRT`, `gm42-10.SLDPRT` byteweise wie in `muster/` (das `Save3` der neuen Baugruppe hat sie nicht angefasst). Erzeugung 54 s.
Erster Lauf abgelehnt: `Schlitten-1 hat Status 3 statt 2`. Am offenen Dokument gemessen: mit aktiver Grenze `Hub` ist der Schlitten 3, mit
unterdrückter 2, in beiden Konfigurationen; die Grenze zählt als Bindung wie in S13b (`docs/stufe4a/ergebnisse.md`, Ruling Z. 4). Die
Erwartung war falsch, nicht das Muster. Eine unterdrückte Unterbaugruppe meldet `GetConstrainedStatus` 5 (`swNoSolution`).

### Tabelle

| Zeile | Frage | Ergebnis | Weg | Zeit/Speicher |
|---|---|---|---|---|
| c | P.c1 Struktur `teile/` bei vorhandenem Original | **Aus der Kopie.** Kennzeichen (Grundplatte 17 mm, 272000 mm³) kommt an, Original am gespeicherten Pfad bleibt liegen; ohne Original ebenso | Kopie des als Original gespeicherten Ordners, `OpenDoc6` Option 1\|64 | 38 s, 436 → 4432 MB |
| c | P.c2 Datei flach daneben | **Flach geht**, auch wenn `teile/` fehlt; liegen beide da, gewinnt die flache neben der Baugruppe | wie P.c1 | |
| c | P.c3 Auflösung vor dem Öffnen gleich dem Öffnen | **Ja, in allen sieben Fällen.** Fehlt `teile/Schlitten.SLDPRT` in der Kopie, nennen `GetDocumentDependencies2(…, True, True, False)` und das Öffnen beide das Original: Sperre 1 sieht es vor dem Laden | `aufgeloeste_referenzen` gegen `GetPathName` aller Komponenten und neu offener Dokumente | |
| c | P.c4 Original im Speicher | **Das Offene gewinnt, die Auflösung sieht es auch:** Ist der Schlitten des Originals offen, lösen beide auf ihn auf; Sperre 1 sperrt | Original-Teil unsichtbar offen, dann Kopie | |
| c | P.c5, P.c7 zurückkopierte Baugruppe mit Lauf-Pfaden | **Lädt alles neben sich**, mit und ohne Lauf-Ordner, auch das flache Fremdteil; nur Warnung 32 | geänderte, im Lauf gespeicherte Baugruppe neben Kopie der Originale | |
| c | P.c6 Pfad-Fund schließt Nachgeladenes? | Bei Sperre 1 wird nichts geöffnet, danach 0 Dokumente offen | `oeffne_in` an der Kopie ohne Schlitten | |
| c | T8.9 `GetPathName` unterdrückter Komponenten | **Gespeicherter Pfad:** Muster-1 (unterdrückt, aktive Konfiguration „Ohne Antrieb“) nennt `original_b\Muster.SLDASM`, mit und ohne Option 64. Nach dem Umschalten auf Standard lädt sie aus der Kopie, Kinder ebenso. `oeffne_in` wirft deshalb `BESTAND_PFAD_FREMD` nach dem Öffnen, obwohl nichts vom Original geladen ist. **Halt**, entschieden (unten) | Original in „Ohne Antrieb“ gespeichert, Kopie geöffnet, dann `ShowConfiguration2` | |
| c | T8.10 als-gespeichert-Pfad nach Option 64 | **Bleibt.** Ohne 64 sind die übrigen leicht geladen (Zustand 1, kein Dokument), mit 64 voll (2) | wie T8.9 | |
| c | T8.11 Dateitypen in den Abhängigkeiten | Nur `.sldasm`, `.sldprt`; der STEP-Import `gm42-10` hat keine; das Teil mit Konstruktionstabelle aus S18t keine | `GetDocumentDependencies2` | |
| c | T8.23 Verdeckte Dokumente nach `CloseDoc` | **Keine.** Unsichtbare Baugruppe hält 7 Dokumente, nach `CloseDoc` 0; ein Teil daraus öffnet danach ohne Titelfehler | `oeffne_in` unsichtbar, `sw.schliesse` | |
| c | T10.7 Öffnen nach geändertem Teil | Warnung 32, kein Fehler, kein Dialog | | |
| c | T10.11 Sperre 1 am Lauf | Löst auf den Lauf-Ordner auf, `teile/` und flach | | |
| c | T11.8 `vorher_<rel>` | Abhängigkeiten leer, auch beim Lagerdeckel mit zwei Konfigurationen | | |
| c | T8.9 nach dem Umschalten (Entscheidung §8.1a) | **Gemessen:** Nach `ShowConfiguration2("Standard")` nennt `GetPathName` für Muster-1 und seine Kinder `Muster-1/Lagerdeckel-1`, `Muster-1/gm42-10-1` die Kopie (`kopie_b\…`), Zustand 2 bzw. 1, neu offen ist nur `kopie_b\Muster.SLDASM` | wie T8.9 | |
| b | T8.6, P.b1 Was ist `MateEntity(i).Reference`? | Fläche (`ReferenceType2` 2) bzw. Ebene (4), schon im Baugruppenkontext: `Select4` wählt die richtige Komponente. Ebenen gehen auch mit `Select2` (Feature), Flächen nur mit `Select4`. `EntitiesToMate` aus `GetDefinition` liefert dieselben. Ebene der Hauptbaugruppe: Komponente ist die Wurzel `Hubeinheit`, nicht `None` | Kopie nur lesend, unsichtbar | 80 s, 436 → 4068 MB |
| b | T8.22, P.b2 Zeiger über Neuaufbau | **Halten** `EditRebuild3`, Unterdrücken, `stelle`, Löschen des Antriebs und Umschalten der Konfiguration, **nicht `ForceRebuild3`**: danach `RPC_E_DISCONNECTED`. Aus der unterdrückten Grenze lassen sie sich auch nach `ForceRebuild3` frisch lesen | Handles einmal gelesen, dann Schritt für Schritt (Skript `zeiger.py`) | |
| b | P.b4 Fahrt an nur lesend geöffneter Kopie | **Über `mechanik_fuer` zuerst gar nicht:** `SwMechanik.status` ruft `ForceRebuild3`, jeder Antrieb scheitert mit `RPC_E_DISCONNECTED`. Mit frisch gelesenen Entitäten (Umgehung im Spike): mit Fenster 9 Stellungen, alle Prüfungen `ok`, Bilder da; unsichtbar `BauFehler` „Kollision in der Fahrt nicht lesbar“ (siehe d) | `fahre_bestand` wie `aufnehmen` | |
| b | T8.7 D1 der Grenze | Antrieb 10 → Schlitten bei −60, 20 → −50: Abstand in +X, wie die Grenze angelegt. D1 der unterdrückten Grenze bleibt auf dem gelesenen Wert (0), er folgt dem Antrieb nicht | | |
| b | P.b3 Flip | `AddMate5(…, Flip=True, …)` an der Grenze: `FlipDimension` bleibt `False`, Lage und Fahrt wie ohne Flip. An zwei gleich gerichteten, deckungsgleichen Flächen hat Flip keine Wirkung; die Frage bleibt für versetzte Flächen offen | Grenze gelöscht und mit Flip neu angelegt | |
| b | T8.8 Probeschritt | Nicht gebraucht: Grundplatte fixiert, Seite aus der Aufnahme; Lage danach unverändert | | |
| b | P.b5, T11.2 SHA-256, `CloseDoc` | Alle Dateien byteweise gleich, `CloseDoc` still in 0,05 s, kein Dokument offen | | |
| b | T11.1 Read-only-Lauf mit Fenster | Antrieb anlegen, stellen, löschen und Iso-Bild speichern gehen (3 Bewegungsbilder, `iso_ro.png`) | | |
| b | T11.12 Neuer Verknüpfungsfehler in der Fahrt | `StellungFehler`, nur diese Grenze: `AddMate5` des Antriebs meldet 5 (überbestimmt), `gefahren: false` mit Grund | Konflikt-Abstand nur im Speicher | |
| b | P.b6 Index in `als_verknuepfung` | Entität 0 ist Partner 0 (Schlitten-1), 1 ist Grundplatte-1 | | |
| a | T8.1, P.a1 Grenze erkennen | Grenze: Typname `MateLimitDistanceDim`, `IsAdvancedMate` wahr, Variation 0/25 mm. Normaler Abstand: `MateDistanceDim`, `IsAdvancedMate` falsch, Variation 0. **min = max legt SolidWorks als normalen Abstand an** (`MateDistanceDim`, Variation 0): kein Unterschied in der Datei | Kopie, `IMate2`, `GetDefinition` | 35 s, 437 → 3212 MB |
| a | P.a2, T8.2 Werte, D1 | `D1` an jedem Abstand (einziges Maß, `D1@<Name>@Hubeinheit.Assembly`), in m, `lies_verknuepfungen` gibt 15 mm. Deckungsgleich, Breite, Symmetrie tragen kein Maß | | |
| a | T8.3 Andere Typen | Breite (`MateWidth`, 11) und Symmetrie (`MateSymmetric`, 8) über `CreateMate` angelegt: kein `D1`, keine Werte; Breite hat 4, Symmetrie 3 Entitäten | | |
| a | T8.4, P.a3 Partner an einer Ebene der Hauptbaugruppe | **Nicht `None`:** `ReferenceComponent` ist die Wurzel mit `Name2` `Hubeinheit`. `lies_verknuepfungen` liest daher `["Muster-1", "Hubeinheit"]`. In der Unterbaugruppe: Namen ohne Präfix (`Lagerdeckel-1`, `gm42-10-1`); von der Hauptbaugruppe aus mit Präfix `Muster-1/Lagerdeckel-1` | | |
| a | T8.5, T8.26 Verknüpfung einer unterdrückten Komponente | In „Ohne Antrieb“ (Muster-1 unterdrückt) sind die Verknüpfungen von Muster-1 **nicht unterdrückt** (`IsSuppressed2` falsch in beiden Konfigurationen), Fehler 0, `D1` und Typ lesbar; der Partner in der Unterbaugruppe heißt dann `Hubeinheit` | | |
| a | P.a4 Vorzeichen | Nicht gemessen: Die Entitäten waren nach Löschen und `ForceRebuild3` getrennt (wie T8.22) | | |
| a | P.a5, P.a7 | Fehlercode 0 an allen fehlerfreien; `Solving` 0, `IsPatternInstance` lesbar | | |
| f | T8.17, P.f1 Typnamen | Komponente `Reference`, Verknüpfungen `MateCoincident`, `MateDistanceDim`, `MateLimitDistanceDim`, Ordner `MateGroup`; Komponentenmuster `LocalLPattern`, seine Instanz `ReferencePattern` (`IsPatternInstance` wahr) als Unterfeature; virtuelles Teil `Reference`, Name `Teil2^Hubeinheit-1`, Pfad unter `%TEMP%\swx…\VC~~\`, `IsVirtual` wahr | Kopie mit Fenster | 78 s, 437 → 3697 MB |
| f | P.f2 Virtuelles Teil in `GetDocumentDependencies2` | Steht drin, mit Temp-Pfad und `^` im Namen; `aufgeloeste_referenzen` filtert es, `oeffne_in` lässt die gespeicherte Baugruppe durch | `InsertNewVirtualPart(IRefPlane, …)`: mit dem `IFeature` statt `IRefPlane` Status 6 (`NotAFaceOrPlane`), mit `None` „Typenkonflikt“ | |
| f | T8.14 `GetComponents(False)` und Unterdrücktes | Unterdrückte Komponente steht drin (Zustand 0), ihre Kinder in dieser Konfiguration nicht | | |
| f | P.f3, T8.15 Namen und Lage in Unterbaugruppen | `Name2` mit `/`, `Transform2` bezogen auf die oberste Baugruppe; `IInterference.Components` und `ReferenceComponent` mit denselben Namen wie `GetComponents` | | |
| f | T8.16 `IsFixed` bei Kindern | Falsch, auch in der starren Unterbaugruppe | | |
| f | T8.18, T8.25, T8.24 Ordner unter den Verknüpfungen | **Flach:** `FtrFolder` steht in der Kette der Unterfeatures von `MateGroup`, die Verknüpfungen folgen ihm als Geschwister, dahinter `Ordner1___EndTag___` (`FtrFolder`). `sw_baugruppe.verknuepfungen` liest alle 12, die Gegenprobe über `GetFeatures(False)` warnt nicht und kennt keine weiteren `Mate…`-Typen | `InsertFeatureTreeFolder2(2)` | |
| f | T8.19, P.f4, T11.4 `ListExternalFileReferences` | An der Baugruppe leer, nennt keine Komponenten | | |
| f | T8.20 Antrieb am schreibgeschützten Dokument | Anlegen und Löschen gehen | | |
| f | T11.5 Reihenfolge | Neue Komponente und neue Verknüpfung ändern `reihenfolge`, `masse`, `skizzen` nicht. Aber `baum_ohne_glieder` nennt `Lokales lineares Muster1` und seine Instanz `Anschlag-3` | | |
| f | T11.13 Gegenprobe der Unterbaugruppe | Ohne Warnung, auch nach geändertem Kind | | |
| f | P.f8 `abdeckung` | Bestand still. Ohne `Schlitten Seite` ist der Schlitten unterbestimmt (2) mit weiteren freien Richtungen, `abdeckung` bleibt still (Minor aus Task 11 bestätigt) | | |
| d | P.d1, T8.12 Unsichtbar: Kollision | **Unsichtbar ist `InterferenceDetectionManager` `None`:** keine Kollision lesbar, `lies_kollisionen` gibt `None`, die Fahrt bricht ab. Mit Fenster: Zähler 1 = Länge der Liste, zweiter Zähler gleich, 6000 mm³ wie erwartet | Kollisionsstand gespeichert, nur lesend, je frisch geöffnet | 42 s, 436 → 1756 MB (Spitze Fenster 3803) |
| d | T8.13 `Done` | Nach `Done` wirft `IInterference.Volume` „Ausnahmefehler des Servers“: erst lesen, dann `Done` (so steht es im Code) | | |
| d | P.d1 Transform2, Status unsichtbar | Lesbar und gleich wie sichtbar | | |
| d | P.d2, T11.10 Zeit und Speicher | Öffnen 0,17 s statt 0,99 s, `lies_baugruppe` 2,55 s statt 7,81 s, Spitze +1 MB statt +2,9 GB | | |
| d | T11.11 `sw.schnell` | `lies_baugruppe` in `sw.schnell` 0,34 s statt 2,55 s (unsichtbar) bzw. 0,51 s statt 7,81 s (Fenster) | | |
| d | T11.3, T11.K1 `ForceRebuild3` am read-only Lauf | Wirkt: Grundplatte von außen 18 mm, der Schlitten steht nach dem Neuaufbau bei Z 18 in beiden Konfigurationen, schon nach `EditRebuild3` | | |
| d | T11.6, T11.7 Zweimal öffnen, Teil zuerst | Nach `CloseDoc` nichts offen, zweites Öffnen mit Fenster ohne Titelfehler, Pfadprüfung `ok`; `vergleich/vorher_*` wird nicht geladen | | |
| d | T11.9 Bilder | Gleiche aktive Konfiguration, Größen fast gleich (± 11 Byte), nicht byteweise gleich | | |
| d | T11.K3 `messe` unsichtbar, nur lesend | Geht, Volumen 12000 mm³ | | |
| d | T8.21 Auswahl im Bild | Bild mit gewählter Komponente unterscheidet sich vom Bild ohne | | |
| d | T11.K2 | Nicht messbar, von Hand | | |
| e | T9.1, P.e1 `AddComponent5` mit benannter Konfiguration | Wird genommen (`ReferencedConfiguration` „Variante B“) | Kopie mit Fenster, schreibbar, nichts gespeichert | e: 396 s, 439 → 7553 MB; e2: 102 s, 435 → 5205 MB |
| e | T9.2, T9.4 Neue Komponente in den übrigen Konfigurationen | **Nicht unterdrückt** (anders als ein neues Feature, S18c): aktiv in beiden, `GetComponents(False)` nennt sie überall | | |
| e | T9.3 `IComponent2.SetSuppression2` | Wirkt nur in der aktiven Konfiguration, Rückgabe 2 (`ChangeOk`) für 0, 2 und 3; 3 ergibt Zustand 2 | | |
| e | T9.5 `ReferencedConfiguration =` | Nur in der aktiven Konfiguration, ohne Neuaufbau lesbar | | |
| e | T9.6 `FixComponent` | **Wirkt in allen Konfigurationen**, in „Ohne Antrieb“ gesetzt, in Standard auch fixiert | | |
| e | T9.7 `wie` | Handler legt `Anschlag-3` an, keine andere Komponente bewegt sich; `wie: Muster-1` (Unterbaugruppe) geht, auch ohne aktive Instanz (aktiv „Ohne Antrieb“) | `komponente_neu` über den Handler | |
| e | T9.8, T10.8, T10.10 Unsichtbares Teil und Baugruppe | Das unsichtbare Teil bleibt offen, wenn die Baugruppe sichtbar öffnet; `AddComponent5` geht; nach `CloseDoc` der Baugruppe ist das Teil mit geschlossen, sein Handle wirft `AttributeError`, `sw.schliesse` fängt das | | |
| e | T9.9 `.sldprt` klein | `Name2` `klein-1`, `GetPathName` mit kleiner Endung wie die Datei | | |
| e | T9.10, P.e3, T9.11 Komponente löschen | `DeleteSelection2(0)` nimmt die Komponente und genau ihre Verknüpfungen, eine Unterbaugruppe samt Kindern, auch mit Verknüpfungen im Ordner; kein Dialog | Handler `komponente_entfernen` | |
| e | T9.12, T9.13, P.e2 `ReplaceComponents2` | Vorauswahl über `Select4` reicht; der alte Handle nennt danach den neuen `Name2` (`Zusatz-1`); Handler setzt `ersetzt` richtig | | |
| e | T9.14 `ConfigName` leer | Mit `MatchName` in beiden Konfigurationen die Konfiguration „Standard“ des Ersatzes | | |
| e | T9.15 Gültigkeit nach dem Ersetzen | Neues Dokument, `ctx.model` und die offenen Handles bleiben gültig | | |
| e | T9.16 Nicht zuzuordnende Verknüpfung | **Bleibt mit Namen, Fehlercode 48** (Flächen-Verknüpfungen nach dem Ersatz des Schlittens), Handler bricht mit Namen ab. An Standardebenen bleiben sie ohne Fehler | | |
| e | T9.17 Unterdrückte Instanz ersetzen | Geht, `alle_instanzen` ersetzt auch die unterdrückte | | |
| e | T9.18 Neue Verknüpfung in den übrigen Konfigurationen | Aktiv in beiden, fehlerfrei | Handler `verknuepfung_neu` | |
| e | T9.19 Partner in einer Konfiguration unterdrückt | Die neue Verknüpfung an `Muster-1/Lagerdeckel-1` gilt in „Ohne Antrieb“ **nicht** als unterdrückt, Fehler 0 (wie T8.5) | e2, neue Komponente ohne andere Bindung | |
| e | T9.20 Doppelter Name | Bleibt still alt (`Hub` statt `Schlitten Seite`), wie bei Features; `v1.anlage` als Name geht | | |
| e | T9.21 `GetModelDoc2` gegen `ReferencedConfiguration` | Das Dokument steht in der referenzierten Konfiguration, `nahe` trifft; die Fase gibt es in „Variante B“ nicht, der Anker meldet das | | |
| e | T9.22, T9.23 `GetCorrespondingEntity`, `FeatureByName` | Zweite Instanz und `Muster-1/Lagerdeckel-1` richtig gewählt; Standardebene über `FeatureByName` | | |
| e | T9.24 `SetSystemValue3` an `D1` | Option 2 setzt in allen, Option 3 mit Namen nur in der genannten (16 / 17 mm), nach `ForceRebuild3` gelesen | Handler `verknuepfung_wert` | |
| e | T9.25 `GetDefinition` | Direkt lesbar, `IsAdvancedMate` wahr an der Grenze, Werte absolut in m | | |
| e | T9.27, P.e4, T9.31 `ModifyDefinition` je Konfiguration | **Wirkt in allen Konfigurationen**, auch wenn nur in Standard gesetzt; Handler bricht dann richtig ab (Nachmessen). Ohne Neuaufbau schon in der anderen Konfiguration sichtbar. **Nach `ModifyDefinition` ist `Hub` in Standard unterdrückt**, das Nachmessen des Handlers prüft das nicht | | |
| e | T9.26 Grenze über `D1` hinaus | min 0 → 5 bei `D1` = 0: **wird nicht übernommen** (min bleibt 0), der Handler bricht richtig ab | | |
| e | T9.28 `ModifyDefinition(…, None)` | `None` gibt „Typenkonflikt“, `callout_leer()` geht; `AccessSelections` kennt der Index an dieser Schnittstelle nicht | | |
| e | T9.29 Fremde Verknüpfung löschen | `Select2` plus `EditDelete` geht, auch im Ordner, keine andere geht mit | | |
| e | T9.30 `IFeature` über Umschaltungen | Bleibt gültig (Name, 6 Flächen) | | |
| e3 | T9.27 wiederholt (Mini-Lauf, `spikes/s19_e3_grenze.py`, `s19_e3.json`) | **Bestätigt, mit Ursache:** `ModifyDefinition` einmal in Standard lässt `Hub` überall aktiv; einmal aus „Ohne Antrieb“ oder je Konfiguration (Handler) ist `Hub` danach in Standard unterdrückt. max steht in beiden auf 30 | je frische Kopie mit Fenster | 45 s, 440 → 1123 MB |
| e | T10.1 `Save3` der Baugruppe | **Schreibt die Baugruppe immer neu**, auch ohne Änderung (neue SHA-256, `GetSaveFlag` falsch); eine im Speicher geänderte Komponente schreibt es nicht mit | | |
| e | T10.2 Teil in der Unterbaugruppe geändert | Nur das Teil ändert sich auf der Platte, die Hauptbaugruppe zeigt das neue Volumen, ist dann aber `dirty` | e2 | |
| e | T10.3 Teil-Scheibe ohne Fenster | **Nein:** `normbohrung` meldet „Fläche an Position 1 nicht getroffen“; mit Fenster geht dieselbe Bohrung (−206,18 mm³), Spitze +2,3 GB | e2 | |
| e | T10.4, T10.5 `GetWhatsWrong` an Verknüpfungen | Nennt die Verknüpfung mit ihrem Namen, Code gleich `GetErrorCode2` (47 Fehler, 1 Warnung), dazu den Ordner „Verknüpfungen“ als Warnung; `ForceRebuild3` gibt trotzdem `True` | widersprüchlicher Abstand | |
| e | T10.6 `EditRebuild3` nach einem Punkt | Reicht für die Lage nach einer Teiländerung | | |
| e | T10.9 `CloseDoc` ungespeichert | Still, kein Dialog, Dateien gleich | | |
| e | T10.12, T10.13 Aktive Konfiguration | Öffnet in der gespeicherten aktiven; ein in anderer Konfiguration gespeichertes Teil ändert `ReferencedConfiguration` nicht | | |
| e | T10.14 `skript` an der Hauptbaugruppe | Läuft mit `ctx.model` als Baugruppe, Eigenschaft gesetzt | | |
| e | T10.15 Laufzeit | `lies_komponenten` plus `lies_verknuepfungen` 5,5 s für 7 Komponenten, je Handler zweimal | | |
| e | T10.16 Reihenfolge | Neue Komponente und Verknüpfung ändern `baum_ohne_glieder` nicht | | |
| e | T11.14, T11.K4 Name in `neue_dateien` | `GetPathName` gleich dem Protokoll, auch mit `ä` und `-`; Komponente heißt `Zusatz_ä-1-1` | | |
| v | P.a6 Scharnier | Zwei Verknüpfungen: `s1` konzentrisch (Bolzen, Hebel), `s1.anlage` deckungsgleich (Schlitten, Hebel) | Referenz Schlitten im Testauftrag `LIVE-S19-SCHLITTEN` gebaut, Kopie unter S19 | 134 s, 437 → 6094 MB |
| v | P.f5, P.f6, P.f7 Abgleich am unveränderten Lauf | `swki aenderungen`: nichts geändert, nichts fehlend, kein Fehlalarm | | |
| v | Fahrt der Referenz Schlitten | Unsichtbar `BauFehler` (Kollision, wie d); mit Fenster `g1` (Abstand 0…220) und `g2` (Winkel 0…90) je 9 Stellungen, alle Prüfungen `ok`, bewegte Mengen richtig (Schlitten nimmt Bolzen und Hebel mit), Kopie danach byteweise gleich | mit Spike-Umgehung T8.22 | |

### Halt nach Zeile c und Entscheidung

Die beiden Stopps des Plans (Task 12 Step 3) traten nicht ein: `teile/` trägt, und die Auflösung vor dem Öffnen ist in jedem Fall gleich dem
Öffnen. Gehalten hat Bedenken 1 aus Task 8 (T8.9): Eine in der aktiven Konfiguration unterdrückte Komponente zeigt den gespeicherten Pfad.
**Entscheidung des Auftraggebers (2026-11-05), neue Regel für §8.1a:** Eine unterdrückte Komponente ist nicht geladen, ihren Pfad sichert die
erste Sperre. Die zweite Sperre nimmt unterdrückte Komponenten aus, prüft aber deren Pfad gegen `aufgeloeste_referenzen`, und nach jedem
Konfigurationswechsel beim Lesen läuft die zweite Sperre erneut. Gemessen dazu (T8.9, Zeile c): Nach dem Umschalten nennt `GetPathName` für
Muster-1 und die Kinder `Muster-1/Lagerdeckel-1`, `Muster-1/gm42-10-1` die Kopie. Bestätigt in Zeile e: Ein noch offenes Teil gleichen
Namens aus einem anderen Ordner gewinnt beim Auflösen, die erste Sperre sieht es und sperrt (wie P.c4).

### Umgehungen im Spike (nicht im Code)

- `fahrt`: Entitäten der Grenze je Antrieb frisch aus der Grenze gelesen statt einmal in `mechanik_fuer` (T8.22).
- `f_neues_virtuelles`: `InsertNewVirtualPart` braucht das `IRefPlane` (`GetSpecificFeature2`), das Byref muss `VT_BYREF|VT_DISPATCH` sein und
  bleibt trotzdem leer; die neue Komponente wird über die Namensliste gefunden.
- Zeile e2: Nachlauf zu e, nachdem ein offen gebliebenes Teil (fehlendes `alle_zu` im Spike) den Abschnitt `e_speichern` sperrte; Zeile v fährt
  zusätzlich mit Fenster.

### Folgen für den Code

Umgesetzt 2026-11-05 (Task 12 Step 3, Bericht `.superpowers/sdd/2026-11-01-bestandsdateien-etappe-2/task-12b-report.md`): 1 bis 8 und
11 im Code, 9, 10, 12 als Kommentar, 13 bleibt Minor. Zu 7: Der Handler setzt eine Grenze einmal in der aktiven Konfiguration (e3).

1. **§8.1a, `swki/bestand/pfade.py:75–76` (`geladene_pfade`), `:101–120` (`oeffne_in`):** Regel oben umsetzen: unterdrückte Komponenten
   (`GetSuppression2` 0) aus der zweiten Sperre, ihren Pfad gegen `aufgeloeste_referenzen`; Sperre 2 nach jedem `schalte` beim Lesen
   (`sw_baugruppe_bestand._je_konfiguration:74–85`, auch `bau_baugruppe.pruefe_stand_baugruppe:183`). Test
   `test_heute_meldet_…_pfad_fremd` umdrehen.
2. **Kollision nur mit Fenster (P.d1, T8.12):** Unsichtbar ist `IAssemblyDoc.InterferenceDetectionManager` `None`. Betroffen:
   `swki/bestand/aufnahme_baugruppe.py:118–125` (Aufnahme liest Kollision und fährt unsichtbar: `kollisionen` `None`, die Fahrt bricht mit
   `BauFehler` ab, jede Aufnahme mit Grenze scheitert ohne `--ohne-bewegung`) und `swki/bestand/pruefen_baugruppe.py:137–143` (`kollision`
   am Lauf unsichtbar, immer `ok: None`). Weg: Kollision und Fahrt in der Phase mit Fenster.
3. **Zeiger nach `ForceRebuild3` (T8.22, P.b4):** `swki/bestand/sw_baugruppe_bestand.py:389–407` (`mechanik_fuer`) liest die Entitäten einmal;
   `SwMechanik.status` (`swki/baugruppe/sw_bewegung.py:66`) ruft `ForceRebuild3`, danach ist jeder Zeiger getrennt (`RPC_E_DISCONNECTED`),
   kein Antrieb lässt sich anlegen. Weg: in `entitaet()` frisch aus der Grenze lesen, das geht auch unterdrückt und nach `ForceRebuild3`.
   Gleiches gilt für jeden anderen Halter von `MateEntity(i).Reference`.
4. **Partner an einer Ebene der Hauptbaugruppe (T8.4):** `swki/bestand/sw_baugruppe_bestand.py:170–177` (`_partner`): `ReferenceComponent`
   ist die Wurzelkomponente mit `Name2` = Titel der Baugruppe (`Hubeinheit`), nicht `None`. `None` ergibt sich nie; `bewegung_bestand._partner`,
   `_seite_ohne_probe:128–145`, `spec_baugruppe._Bestand.haengt_dran` sehen eine Komponente `Hubeinheit`, die es nicht gibt. Weg: Name nicht
   in `GetComponents(False)` heißt `None`.
5. **Partner einer unterdrückten Komponente (T8.5):** In „Ohne Antrieb“ meldet `ReferenceComponent` für das unterdrückte `Muster-1/Lagerdeckel-1`
   ebenfalls die Wurzel. `_verknuepfung_stand:196–214` liest den Partner nur in der ersten Konfiguration (aktive zuerst): Ist die gespeicherte
   aktive Konfiguration eine mit unterdrücktem Partner, steht der falsche Partner in der Aufnahme. Die Verknüpfungen einer unterdrückten
   Komponente sind dabei nicht unterdrückt (`IsSuppressed2` falsch, T8.26, auch T9.19).
6. **Komponentenmuster im Baum (T11.5, P.f1):** `swki/bestand/sw_baugruppe_bestand.py:53` `GLIEDER` ohne `LocalLPattern` (und die übrigen
   `Local…Pattern`): `baum_ohne_glieder` nennt das Muster und über `GetFirstSubFeature` seine Instanzen (`Anschlag-3`), `_pruefe_baum` und
   `reihenfolge` sähen eine neue Musterinstanz als Feature.
7. **`ModifyDefinition` an Grenzen (T9.27, T9.26, T9.31):** wirkt in allen Konfigurationen; `konfigurationen` an einem Grenz-Punkt gehört in
   `validieren` (`swki/bestand/spec_baugruppe.py:265–286`) abgewiesen, der Handler bricht heute erst beim Nachmessen ab. Eine Grenze über `D1`
   hinaus (min 5 bei D1 0) übernimmt SolidWorks nicht. Nach dem Setzen war `Hub` in Standard unterdrückt:
   `punkte_baugruppe._nachmesse_wert:595–615` prüft `unterdrueckt` nicht, sollte es.
8. **Neue Komponente in den übrigen Konfigurationen aktiv (T9.2):** Die Annahme „wie ein Feature unterdrückt“ trifft nicht zu;
   `punkte_baugruppe._in_allen_aktiv:283–296` hebt nur auf, was nötig ist, schadet also nicht. `FixComponent` wirkt in allen Konfigurationen
   (T9.6), die Schleife je Konfiguration ist dafür unnötig, aber harmlos.
9. **`Save3` schreibt die Baugruppe immer neu (T10.1):** Die SHA-256 ändert sich auch ohne Änderung. Der Bau speichert nur bei
   `aenderung_an_haupt`, das passt; `vergleiche_dateien` darf eine unveränderte Hauptbaugruppe nach einem `Save3` nicht als „ungespeichert“
   lesen (heute nicht der Fall).
10. **Teil-Scheiben brauchen ein Fenster (T10.3):** `normbohrung` trifft ohne Fenster keine Fläche. `bau_baugruppe._aendere_scheibe:247`
    öffnet richtig sichtbar, so lassen.
11. **Laufzeit (T11.11, T10.15):** `lies_baugruppe` in `sw.schnell` 5- bis 15-mal schneller (2,55 s → 0,34 s unsichtbar); die Handler lesen je
    Punkt zweimal alle Konfigurationen (5,5 s bei 7 Komponenten). Für `lauf-30` in Task 16 messen, dann entscheiden.
12. **Grenze mit min = max (T8.1):** SolidWorks legt sie als normalen Abstand an, die Datei unterscheidet sie nicht; `_zahlen:180–193` liest das
    richtig als Abstand ohne Grenze.
13. **`abdeckung` (P.f8):** Ein Partner einer aktiven Grenze mit weiteren freien Richtungen bleibt still (Minor aus Task 11 bestätigt):
    `swki/bestand/bewegung_bestand.py:103–118`.
14. **`werkzeuge/bestand_muster.py` `HUB_STATUS`:** schon korrigiert (Commit `4a96e0e`).

## 3. Abnahme an lauf-30 der Prüfstation (Blindtest, live)

Rechner A, SW 2025. Der Nutzer hat `AP68-Pruefstation/lauf-30` am 01.11.2026 von Hand umgebaut und seine Liste zurückgehalten. Das Tool
hat die Handänderungen ohne diese Liste gefunden, der Nutzer bestätigte am 06.11.2026: „deine Liste passt“ (nichts übersehen, kein
Fehlalarm genannt). `lauf-30` wurde nie in SolidWorks geöffnet und ist nach Aufnahme und Abgleich byteweise gleich
(`lauf30-stand-vorher.json`).

| Schritt | Kennzahl |
|---|---|
| Aufnahme (`swki bestand aufnehmen`, Auftrag `AP68-Pruefstation-Rev1`, bestand-1) | 34 Dateien, 70 Komponenten, 168 Verknüpfungen, 2 Grenzen gefahren; Fahrt 268 s, Dateien 92 s, Spitze 4827 MB |
| Abgleich gegen Protokoll, Spec und Export mit `--referenzbau` (referenz-3) | rund 46 s; geänderte Eigenteile Anschlussplatte und Kanalträger aus der freigegebenen Spec gebaut und exakt verglichen |

Gefunden (Spec → lauf-30):

- **Dateien:** geändert Anschlussplatte, Kanalträger, Hauptbaugruppe; neu `Weichenzylinderhalter.SLDPRT` (kein swki-Teil); Zylinderhalter
  nicht mehr verwendet.
- **Anschlussplatte:** 397 → 300 mm (hinteres Ende Y 540 → 443); 4 Gewinde entfallen (Kanalträger-Flansch, Zylinderhalter), 2 neu bei Z −160.
- **Kanalträger:** Flansch und seine 2 Bohrungen entfernt; Steg in Y 25 → 100 mm; Kanalschrauben-Bohrungen 10 → 30 mm tief, neu als
  lineares Muster; neue Referenz im Kontext der Hauptbaugruppe.
- **Baugruppe:** Zylinderhalter → Weichenzylinderhalter (Winkel 40 × 40 × 8, ohne Material, Eigenschaften, Bohrungen, ohne eigene
  Verknüpfung); 2 × M5×16 und 2 × M5×12 samt 4 Verknüpfungen entfernt; 17 Verknüpfungen mit nicht zuordenbarem Partner (ohne Fehlercode);
  neue Verknüpfung `Platziert1`; unterbestimmt ADNGF, M5×20-10/11, M4×20-3/4, Weichenzylinderhalter.
- **Kollisionen:** M5×20-10/11 je 231 mm³ im Vollmaterial der Anschlussplatte (Gewindeeingriff sonst ~66 mm³); M4×20-3/4 je 101 mm³ im
  Weichenzylinderhalter.
- **Bewegungen:** beide fahren; beim Weichenhub ist die Zwischenplatte nicht mehr voll bestimmt. Übrige Lagen gleich (< 10 µm).

Im Tool aufgedeckt und behoben: Der erste Abgleich brach am Kanalträger mit `BESTAND_PFAD_FREMD` ab, weil der Referenzbau für die Referenz
im Kontext ein Dokument aus `lauf-30` geladen hätte; die Sperre hat das verhindert. Fix `281cdd1`: Bestandskopie vor dem Bau öffnen, sonst
Lücke.

Grenzen des Abgleichs: Skizzengeometrie ohne Maß und Endbedingungen nur über den Referenzbau (für beide geänderten Teile gelaufen); für ein
neues Fremdteil gibt es kein Soll, nur die Beschreibung; `fixiert` wird nicht verglichen. Unveränderte Dateien sind über die SHA-256 belegt.

Offen: neue Anforderungen des Nutzers über Skill `aendern` umsetzen (Freigabe, Prüfer); Punkte am Kanalträger weist `validieren` wegen der
Referenz im Kontext ab. Die Abnahme an einer echten Kollegen-Baugruppe auf SW 2026 bleibt eigene, offene Abnahme.

## Offene Kleinigkeiten aus den Reviews

Stand 2026-10-31, zurückgestellt, nichts davon führt zu einem falschen Bestanden. Teilweise inzwischen erledigt (Abschlusskorrekturen, siehe oben).

- Task 1: minor (deferred): CLAUDE.md-Ausnahme für Musterdateien (kommt in Task 11); Student-Lizenz der Musterdateien (Nutzer informiert 2026-10-31); 0,05 µm Volumenabweichung, HoleWzd-Formulierung.
- Task 1: minor (deferred): „beim Zug aktive Konfiguration“ ist stärker formuliert als belegt (gemessen: Standard beschädigt).
- Task 2: minor (deferred): SHA vom Original statt von der Kopie (Rennen beim Kopieren); Regel „eine Datei“ prüft nur jüngste Aufnahme; OSError/JSONDecodeError in pruefe_kopie, lade_aufnahme roh; lauf_kopie auf vorhandenes Ziel.
- Task 3: minor (deferred): Mengenfelder (bereiche, folgen, konfigurationen, kinder) werden in Listenreihenfolge gehasht; Punkt-Sortierung verliert Reihenfolge, die Wirkung haben kann (Task 6 beachten); Pfadprüfung für bestand.datei und skript.datei (Task 4/5 aufgreifen); groesse-Testfall.
- Task 3: minor (deferred): kein Test für umkehren als Anforderung.
- Task 4: minor (deferred): freies Gruppenmitglied mit gesteuertem Partner nicht abgewiesen; Klassifizierung nur über zustand (Task 5 muss absichern); gleichung-Punkt auf abhängige Variable (Task 6); skript.datei als Verzeichnis gibt PermissionError; uneinheitliche Codes; masse_pruefen akzeptiert name neuer Features (Task 8 beachten); Spec-Beispiel ohne gewindetiefe.
- Task 5: minor (deferred): Halbaufnahme ohne bestand.json (zeige nimmt nummern[-1], Sperre BESTAND_ANDERE_DATEI); whats_wrong-Fehlerpfad nur Attrappe; _wert/_punkte schlucken COM-Fehler; _schalte im finally verdeckt Ursache; zeige liest Konfiguration nicht zurück; zusammenfassung ohne feature/gruppe/einheit; links nicht normalisiert in folgen; privater Import _aufnahme; gleichungsgesteuerte Unterdrückung nicht erkannt; material nur aktive Konfiguration.
- Task 6: minor (deferred): hochgestuft True auch bei Fehlschlag; oeffne-Fehler ohne Protokoll; Hilfsfeature achse_x bei aktiver nicht erster Konfiguration; lizenz/hochgestuft in jedem Teil-Protokoll; --alles-neu und --hochstufen je still ignoriert; private Zugriffe über Modulgrenzen; bekannte-Fehler-Pfad nur an Attrappe (echte Datei mit Fehlern in der Abnahme beachten).
- Task 6: minor (deferred): sporadischer RPC_E_DISCONNECTED, einmal, keine Wiederholung eingebaut; Gleichungen je Konfiguration nur an Attrappe; Schließfehler nach Save3 meldet Lauf als Fehler; Maßpfad bei Skript-Abbruch bleibt features[n].
- Task 7: minor (deferred): gleichungen und skizzen nur aktive Konfiguration gelesen; datei.ordner muss Task 8 setzen; _skizzen_von erlaubt geteilte Skizzen; loeschen eines HoleWzd live prüfen; RED nachgestellt.
- Task 7: minor (deferred): Modul-Docstring vergleich.py:17-18 nennt noch „Name 2“ (Task 8 korrigiert); getriebene Maße mit None bleiben stumm; fehlender Gruppenpartner ergibt in punkt:mass None statt False; unter nur aktive Konfiguration.
- Task 8: minor (deferred): dicke unterschätzt spitze Formen; _volumen_delta ignoriert Konfiguration ohne Abweichung; _aktive_zurueck verdeckt Ursache; Bilanz-Toleranz wächst mit dem Teil; privater Import _schalte; punkt:p1 besteht bei Änderung von p2 in gemeinsamer Box (nur Prüfer unterscheidet); ausgabe muss aus protokoll.dateien arbeiten.
- Task 8: minor (deferred): features-Bereich als Hülle der berührten Boxen akzeptiert einen Körper, der zwei Features verbindet (Abschlussreview bewerten); zweiter Hinweistext geht beim Zusammenführen verloren; Skript muss Skizzen zurückgeben (Skill aendern, Task 11).
- Task 9: minor (deferred): Bericht schreibt „keine Abweichung“ bei nicht nachgewiesener Differenz (Task 10 korrigiert); fehlerhafte Kopie bleibt in ausgabe/ liegen; alte Dateien in ausgabe/; kaputtes Urteil alter Läufe blockiert; Namensvergleich case-sensitiv.
- Task 10: minor (deferred): „Bereich zu eng“ und „neuere Version“ nicht neu als Referenz-Tests, vorhandene decken sie ab; Fase plus L ergibt vermutlich zusammenhängenden Differenzkörper über zwei Bereiche (Skill-Hinweis); volumen_delta nur ein Soll für zwei Konfigurationen.
- Task 10: minor (deferred): bewerte mit leerem gemessen ergibt ok True (Praxis fängt konfigurationen); test_neue_normbohrung… belegt Freigabe-Soll nicht; privater Import _geometrie im Live-Test; test_bestand prüft nur Backslash-Pfade.
- Task 10a: minor (deferred): skizziere hält Fläche vor InsertSketch (Muster gemessen unauffällig, nicht mit Wächter); Mechanismus unbelegt, Fix empirisch; GetEdges erst nach allen CreatePoint; skript.punkte_festlegen altes Muster, nicht auslösbar; p1–p5/p6 uneinheitlich; WARTEZEITEN nicht nachstellbar. Stale-Texte zu {nahe} auf Bohrung: in Task 11.
- Task 11: minor (deferred): bemassungsbezug-Spec zitiert alte Meldung (historisch); Live-Fall {nahe} nicht RED nachgestellt.
- Task 11: minor (deferred): Hochstufen braucht eigenes OK statt Auftrags-OK (Skill Zeile 123); BESTAND_NICHT_LESBAR in Skill unvollständig; pruefer.md Zeile 99 als Pflicht formulieren; conftest-Fixture noch ohne Live-Lauf. → in den Fix-Wave des Abschlussreviews.
- Abschluss: parked: abgelehnte Aufnahme hinterlässt Ordner ohne bestand.json — Ruling: laut, ändert kein Ergebnis; mit Rest 3 billig mitzunehmen. parked: Feature samt Kind ergibt ok: None — Ruling: gewollt, Skill-Hinweis. parked: Docstrings ausgabe/Skill §7 zu BESTAND_VERALTET; bericht.py:71 Wortlaut.
