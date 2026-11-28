# Zeichnungsableitung – Ergebnisse

Design: `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md`. Plan Z1.0/Z1.1:
`docs/superpowers/plans/2026-11-16-zeichnungsableitung-z1-spike-spec.md`. Recherche: `recherche.md`, Härte und Halbzeug:
`haerteangabe.md`.

## Stand 28.11.2026

| Etappe | Stand |
|---|---|
| Z1.0 Spike (API live) | erledigt 17.11. (`spike-z1.md`): alles ohne Dialog außer Bohrungsangaben; Modellmaße nur gefiltert brauchbar |
| Z1.1 Spec-Erweiterung | umgesetzt (Branch `claude/zeichnungsableitung-recherche`) |
| Z1.2 Freistich, Zentrierbohrung | offen (Skill `compiler-erweitern`) |
| Z1.3 Zeichnen | umgesetzt: Stufe 1 (Blatt, Ansichten) und 2 (Maße) 17.11., Stufe 3 (Bohrungsangaben) 19.11., Stufe 4 (Toleranzen, Rauheit, Form/Lage, Sammelangaben) und 5 (Übergabe an Z1.4, `zeichnung/zeichnung.json`) 28.11.; Nutzerentscheidungen 28.11. umgesetzt (Stiftbohrung ohne Rauheit, Rauheitsfeld, R-Maß frei) |
| Z1.4 Prüfen | umgesetzt 28.11. (Abschnitt Z1.4), Fix-Welle nach dem Gesamtreview 28.11. (Abschnitt „Gesamtreview“) |
| Z1.5 Firmenvorlage | wartet auf die Vorlage des Nutzers; Fertigungszeichnungen nur auf dem Firmenrechner |

## Z1.1 – was jetzt gilt

- Schema `teil.schema.json`: am Feature (`extrusion`/`schnitt`, `rotation`, `austragung`, `bohrung`, `normbohrung`,
  `verrundung`, `fase`) `funktion`, `passung`, `toleranz`, `rauheit`, `form_lage`, `huelle`, `bearbeitung`,
  `behandlung`; Top-Level `verfahren`, `bezuege`, `toleranzen`, `behandlung`, `halbzeug`.
- Regeltabelle `swki/wissen/funktionen.yaml` (11 Funktionen) mit Quelle, Beleg je Wert, `bestaetigt`. Nur
  `lagersitz_gehaeuse` ist ohne C-Wert; alle anderen meldet `validieren` als Hinweis `funktion`, bis der Nutzer bestätigt.
- `swki/spec/funktionen.py`: `aufloesen` (eigene Werte vor Tabelle, eigene Toleranz ersetzt Tabellenpassung),
  `anforderung_befunde` (blockierend in `validieren`).
- Prüfsumme: `verfahren`, `toleranzen`, `behandlung`, `halbzeug` nur wenn vorhanden; Anforderungen an Features als
  sortierte Tupel [Art, Nenngröße, Felder, Anzahl Instanzen] ohne Feature-IDs. Specs ohne neue Felder: Prüfsumme unverändert
  (fester Hash im Test). `bezuege` sind Bauweg (Anker auf ein unbekanntes Feature ist ein Befund). Jeder Freigabeweg legt die
  aufgelösten Werte in `freigabe.json` (`anforderungen`) ab.
- Hinweise: Regel 8 entfällt bei `bearbeitung: erodieren`; Ra < 0,8 ohne Schleifen; geschliffenes Drehteil ohne
  Freistich.

## Z1.3 Stufe 1 – Blatt und Ansichten (17.11.2026)

- `swki zeichnen <spec> [--lauf N]` (`swki/zeichnung/`): Format A4 hoch oder A3 quer und Vorzugsmaßstab (`blatt.py`),
  Ansichten aus der Spec (`ansichten.py`), Anordnung nach Projektionsmethode 1 mit 25 mm Maßrand (`layout.py`),
  Umsetzung in SolidWorks (`zeichnen.py`); Ausgabe SLDDRW, PDF, PNG unter `<laufordner>/zeichnung/`, Teildatei unverändert.
- Drehteil mit Innenkontur: Stirnansicht als Modellansicht, Hauptansicht = Vollschnitt A-A daraus. Ohne Innenkontur:
  Hauptansicht mit liegender Achse, Stirnansicht projiziert bei Bohrungen. Frästeil: Hauptansicht von der Seite mit den
  meisten Features, Dickenansicht projiziert darunter, Seitenansicht bei Features quer dazu.
- Mittellinien und Mittelpunktmarken über die Dokumentoptionen (automatisch beim Erzeugen der Ansichten).
- Schriftfeld über Eigenschaften der Zeichnung (Gezeichnet, Datum, Werkstoff); das SW-2025-Muster liest Benennung als
  `$PRPSHEET:"Description"` aus dem Modell und die Zeichnungsnummer aus dem Dateinamen – Zuordnung erst mit den
  Formaten des Nutzers (Z1.5).
- Live-Befunde (korrigieren Spike Z1.0): Skizzen in Ansichten liegen in Ansichtskoordinaten ((Blatt − Position) ÷
  Maßstab); in gedrehten Ansichten zusätzlich gedreht, ein Ausbruch dort wirkt nicht. Neue Ansichten sind automatisch
  skaliert; der Maßstab wird je Ansicht gesetzt. `IView.Position` nur als double-Array.
- Laufzeit 39–58 s je Zeichnung (Ursache offen). PDFs zur Durchsicht: `<arbeitsordner>/Z1-STUFE1/`.
- Gezeichnet wird der letzte bestandene Lauf; `--lauf N` erlaubt einen ungeprüften Lauf mit Meldung
  `LAUF_NICHT_BESTANDEN` (nur zur Ansicht). Das Ergebnis führt `meldungen`, wo die Ansichtswahl rät oder ein Schnitt
  nicht erzeugt wird (`SCHNITT_NICHT_UNTERSTUETZT`: Schnitt im Frästeil folgt später).
- **Live ungeprüft:** Drehteil ohne Innenkontur (gedrehte Hauptansicht über `IView.Angle`, Projektion daraus) – nur
  in den reinen Funktionen getestet. Ebenfalls offen: axiale Bohrung als Innenkontur eines Drehteils, Schnitt im
  Frästeil, Hauptseite bei `nahe`-Ankern; kleinere Review-Punkte siehe Ledger („minor (deferred)“).

## Z1.3 Stufe 2 – Maßplan, Ansichten nach Maßbedarf (17.11.2026)

- Maßplan (`massplan.py`): Frästeil = protokollierte Anforderungsmaße des Baus (ohne Hilfsebenen, Konstruktionsmaße,
  Mittellinien, Bohrungsfasen); Drehteil = Ø je Absatz und Längen ab der Stirnfläche mit dem größten Ø, bei Gleichstand der äußeren (Bezug; Nutzer
  18.11.2026: Außenstirn bleibt Bezug, bei der Buchse die Bund-Außenstirn), dazu die
  Modellmaße der übrigen Features (Fasen, Bohrungen).
- Ansichten nach Maßbedarf (Nutzer 17.11.): Frästeil startet mit drei Ansichten; Zuordnung (`zuordnung.py`) mit
  Obergrenze `zeichnung.max_masse_je_ansicht: 12` (`config/standard.yaml`) und Vorzugsansicht (Grundkörper und Merkmale
  der Hauptseite, Muster erben die Richtung ihrer Quelle); volle Ansicht oder Maß ohne Ansicht → weitere Projektion
  (links/oben, höchstens zwei Runden), Ansicht ohne Maß entfällt (außer Haupt- und Basisansicht).
- Umsetzung (`bemassen.py`): `InsertModelAnnotations4` mit `swInsertDimensionsMarkedForDrawing |
  swInsertHoleWizardLocationDimensions`, `HiddenFeatureDims=True`; Kandidaten aus den tatsächlich eingefügten Maßen;
  Duplikate und Nicht-Plan-Maße löschen über `IAnnotation.Select2(False, 0)` + `DeleteSelection2(0)` (Select3 mit leerem
  Dispatch wählt nichts aus, `spikes/z1_diag_loeschen.py`); Drehteil-Ø und -Längen über Kanten (`LineParams` in
  Modellkoordinaten) und `AddDimension2`, Ø-Präfix per `SetText`; danach `AlignDimensions(AutoArrange)` je Ansicht.
- Zeichnung und PDF heißen wie die Zeichnungsnummer (Schriftfeld des ISO-Musters zeigt den Dateinamen groß).
- Live (frisches SolidWorks): Buchse 12/12, Spannplatte 26/26 Plan-Maße, höchstens 10 je Ansicht, 8–30 s je Zeichnung.
- Offen für Stufe 3/4: Fasen ohne „× 45°“, Lochkreis als Radius statt TK Ø, Bohrungs-/Gewindeangaben, Pfadmaße von
  Austragungen (Kabelnut) unruhig, Dezimalstellen aus der Normdatei; Bezug `bezuege.A` beim Drehteil noch nicht
  ausgewertet; Achslage für Drehteile auf der Ebene „rechts“ ungeprüft.

### Nachtrag Lesbarkeit (Nutzer 18.11.2026)

Befund des Nutzers an den Stufe-2-PDFs: Maß auf der Schnittkennzeichnung „A“, 47 und 27 doppelt (Spannplatte), Maßzahlen
von Linien gekreuzt, Maße in der Dickenansicht an Merkmalen, die dort nicht sichtbar sind. Der Live-Test hatte das nicht
erkannt, weil er nur Zahlen und Obergrenzen prüfte.

- Prüfung am PDF (`lesbarkeit.py`, pymupdf): Text auf Text (Kern gegen Kern) und Linie durch eine achsparallele
  Maßzahl; Rand, Rahmen und Schriftfeld ausgenommen. Der Live-Test schlägt bei jedem `LESBARKEIT`-Befund fehl.
- Doppelte Punktmaße: gleiche Lagemaße eines Merkmals (Punkte des Nutpfads auf gleicher Höhe) nur einmal.
- Blickachse: Skizzenmaße nur in der Ansicht senkrecht zur Skizzenebene, Tiefenmaße nur quer dazu (`Mass.achse`,
  `Mass.modus`, `ansichten.blickachsen`).
- Pflichtmaße werden nie verworfen: Zeigt keine Ansicht mit Platz das Merkmal, kommt das Maß über der Obergrenze in die
  passende Ansicht (`ANSICHT_DICHT`). Spannplatte: Hauptansicht 16 Maße, weil nur sie auf die Skizzenebene blickt.
- Reihenanlage (`reihen.py`) statt Nachschieben (Live-Diagnose: Schieben um 6 mm landete im nächsten Konflikt, 30 und
  120 sogar auf derselben Stelle): je Ansichtsseite kurze Spannen innen, lange außen, Spanne samt Zahl nie überlappend;
  Zahl mittig oder außen daneben, möglichst in der Ansichtsbreite; keine Hilfslinie eines äußeren Maßes durch die Zahl;
  klemmt eine Zahl, rückt ihr Maß nach außen, wenn danach weniger klemmen. Spannen und Textlage aus `IDisplayData`
  (`spikes/z1_diag_masslinien.py`), Lage per `IAnnotation.SetPosition2` (Maßlinie folgt der Zahl).
- Beschriftungen von SolidWorks („SCHNITT A-A“, Kennbuchstabe der Schnittlinie) kennt die Reihenanlage nicht: Befund am
  PDF → alle Reihen dieser Ansichtsseite einen Reihenabstand (8 mm) nach außen, neu prüfen, höchstens drei Runden.
- Live (frisches SolidWorks): Buchse 12/12, Spannplatte 22/22 Plan-Maße, beide ohne Lesbarkeitsbefund.
- Offen: Tiefenmaß der Tasche (12) in der Dickenansicht zeigt auf eine dort unsichtbare Kante (braucht Schnitt, Stufe 3);
  Maße vom Ursprung (24, 27 der Kabelnut) ohne gezeichnete Mittellinie; Hinweislinie von R4 läuft quer durch die
  Hauptansicht; außen stehende Zahlen können weit von ihrer Spanne liegen („27,00“ der Spannplatte); Reihen rücken nicht
  gegen Nachbaransichten ab (Maßrand fest 25 mm).

### Nachtrag Einzelheit (Nutzer 18.11.2026: „Detailansicht“ statt dichter Hauptansicht)

- Bleibt eine Ansicht über der Obergrenze, lagert `bemasse` das Merkmal mit den meisten Maßen dort (mindestens 3, nie
  der Grundkörper) in eine Einzelheit aus; seine Maße bekommen die Einzelheit als Vorzug (`EINZELHEIT: k1 …`).
- Bereich als Rechteck-Profil in der Elternansicht skizziert (zuerst um die Hilfslinien-Anfänge, jetzt um die Kanten)
  (`CreateCornerRectangle`, bleibt ausgewählt) → `CreateDetailViewAt4` mit `swDetCirclePROFILE`
  (`spikes/z1_diag_einzelheit.py`). SolidWorks fügt dort die Maße der Merkmale im Bereich ein.
- Nutzer 18.11.2026 (Durchsicht): „Details werden in der Regel vergrößert, sonst braucht man kein Detail.“ Deshalb
  nur mit dem kleinsten Normmaßstab, der mindestens doppelt vergrößert, und nur, wenn Format und Blattmaßstab dabei
  bleiben (`layout.einzelheit_passt`, mit den Ansichten, die Maße bekommen); sonst `EINZELHEIT_ZU_GROSS`, die Ansicht
  bleibt dicht. Lage in der Ecke unter der Seitenansicht oder rechts daneben.
- Bereich aus den sichtbaren Kanten des Merkmals (`IFace2.GetFeature` je Kante, `IView.ModelToViewTransform` liefert
  Blattkoordinaten samt Maßstab, `spikes/z1_diag_merkmalskanten.py`), 2 mm Rand – nicht aus den Bezugspunkten seiner
  Maße (die Nut samt linker Kante und Plattenmitte war 132 × 72 mm und passte vergrößert nicht, ihre Kanten 113 × 36).
  Maße, deren Bezüge außerhalb liegen (100, 10 der Nut), bleiben in der Elternansicht.
- Live-Lehren (`spikes/z1_diag_einzelheit_lage.py`): `IView.Position` einer Einzelheit ist derselbe Modellpunkt wie in
  der Elternansicht (nicht die Rahmenmitte); `GetOutline` folgt einem neuen `ScaleDecimal` nicht, auch nicht nach
  `EditRebuild3`/`ForceRebuild3`/`GraphicsRedraw2`, und trägt rund 12 mm Rand → Größe und Lage selbst gerechnet.
- Mittelpunktkreuze an Taschenecken (Nutzer 18.11.): Vorlagenwert `swDetailingAutoInsertCenterMarksForFillets` war an,
  SolidWorks setzt die Marken beim Anlegen einer Einzelheit in allen Ansichten neu → für Verrundungen und Langlöcher
  ausdrücklich aus; Bohrungen behalten Kreuz und Mittellinie (Buchse jetzt mit Achse und Lochkreis).
- Radiusmaß (Nutzer 18.11.: Pfeil zeigte auf das Kreuz statt auf den Radius – die Zahl stand innen, die Maßlinie lief
  über den Mittelpunkt auf die gedachte Verlängerung des Bogens): Zahl außen auf einem Strahl durch den Bogen
  (`reihen.radius_zahl_frei`), frei von sichtbaren Kanten, den Linien der übrigen Maße und dem Rahmen der Einzelheit;
  unter den freien Lagen die, deren Hinweislinie am wenigsten kreuzt. Bogen über seinen Mittelpunkt (Ende der letzten
  Linie aus `IDisplayData`).
- Lesbarkeitsprüfung: schräge Texte (R, Ø an Hinweislinien) jetzt mit gedrehtem Kernrechteck; nur Linien parallel zur
  Schrift (die eigene Hinweislinie) zählen nicht. Vorher waren schräge Texte ganz ausgenommen.
- Live Spannplatte (18.11.): Blatt 1:2, Einzelheit A 1:1 (Kabelnut), Hauptansicht 12, Einzelheit 4 Maße – die Nutmaße
  27/47/60 zeigten dort aber auf die Plattenmitte außerhalb des Rahmens (überholt, siehe unten).

### Nachtrag Mittellinien (Nutzer 19.11.2026: „Ja, Mittellinien“)

- Mittellinie nur, wo das Maßprotokoll einen Mittenbezug führt (`bezug: ursprung`/`mitte`, jetzt `Mass.bezug`) und
  die Hilfslinie an einem Punkt ohne Kante ansetzt (`mittellinien.ohne_kante`): Bezugspunkt = Anfang der Hilfslinie
  minus 1 mm Lücke; eine gerade Kante legt ihn nur fest, wenn sie nicht parallel zur Messrichtung läuft oder er auf
  ihrem Eckpunkt liegt (Live: „24,00“ in halber Höhe der senkrechten Plattenkante); gedachte scharfe Ecken gerundeter
  Kanten zählen als Kante (50/30 der Tasche). Linie über den Körper + 3 mm, `ISketchManager.CreateCenterLine`
  (im PDF Strichpunkt 0,18 mm, `spikes/z1_diag_mittellinie.py`); die Hilfslinie am Mittenbezug wird mit
  `IDisplayDimension.SetExtensionLineAsCenterline` selbst Mittellinie (lag sonst als Volllinie auf ihr).
- Andere Bezüge ohne Kante werden gemeldet, nicht verziert: `BEZUG_OHNE_KANTE` (Spannplatte: Taschentiefe 12 in der
  Dickenansicht, verdeckter Boden).
- Einzelheit: nur Maße, deren beide Bezüge im Rahmen liegen und die keinen Mittenbezug haben; das Merkmal wird nach der
  Zahl solcher Maße gewählt, Verrundung/Fase zählen zu ihrem Merkmal. Spannplatte: Kabelnut 0 Maße → Tasche t1 mit
  50, 30, R4 (Einzelheit A 1:1). Kennbuchstabe wandert um den Rahmen, bis die PDF-Prüfung ihn frei findet
  (`IDetailCircle.SetLabelPosition`, Blatt-m, `spikes/z1_diag_detailbuchstabe.py`).
- Live: Buchse unverändert, Spannplatte mit Mittellinien in Haupt- (waagrecht, senkrecht) und Seitenansicht, kein
  Lesbarkeitsbefund; Hauptansicht 13 Maße (`ANSICHT_DICHT` für „60,00“ der Nut).
- Entschieden (Nutzer 19.11.2026: „13 Maße hinnehmen“): „60,00“ der Nut (ab Mittellinie die halbe Plattenhöhe, Wiederholung
  von 120/2) bleibt, die Hauptansicht der Spannplatte hat 13 Maße; `ANSICHT_DICHT` bleibt als Hinweis, Spec unverändert.
- Offen: Beschriftung „DETAIL A“ aus der Vorlage (Norm: Einzelheit).

### Nachtrag Schnitt durch Taschen (Nutzer 19.11.2026: „Ggf. solltest du die untere Seitenansicht zu einer
Schnittansicht anpassen“)

- Befund: „12,00“ in der unteren Ansicht war die Taschentiefe auf den dort verdeckten Boden; eine lesbare
  Tiefenangabe fehlte.
- Blinde Taschen (`typ: schnitt` mit Tiefe) in der Hauptfläche machen die untere Ansicht zum Schnitt A-A
  (`Ansicht.durch`); blinde Bohrungen nicht (Tiefe steht in der Bohrungsangabe, Stufe 3). Schnittlinie waagrecht durch
  die Mitte der ersten Tasche (ihre sichtbaren Kanten), `CreateSectionViewAt5` ohne `ChangeDirection`: Pfeile nach
  unten, Taschenöffnung unten wie in der Projektion nach Methode 1 (`spikes/z1_diag_frässchnitt.py`; mit
  `ChangeDirection` stand die Öffnung oben, spiegelverkehrt). Einzelheit heißt dann B.
- Kreisbezug: SolidWorks beginnt Hilfslinien an Bohrungen außen am Kreis; ein Kreismittelpunkt auf der Achse der
  Hilfslinie, höchstens Radius + Lücke entfernt, gilt als Bezug (sonst falsche `BEZUG_OHNE_KANTE`).
- Live: Spannplatte mit Schnitt A-A, Taschentiefe 12 am sichtbaren Boden, kein `BEZUG_OHNE_KANTE`; Buchse unverändert.

## Z1.3 Stufe 3 – Bohrungsangaben, Textzusätze, Beschriftung (19.11.2026)

- Was gilt: Bohrungen und Bohrbilder bekommen statt Ø- und Lagemaßen eine Angabe als Hinweis mit Hinweislinie am
  Kreis (`ANGABE_*`-Meldungen bei Lücken): „5 × M6 – 10 tief / Senkung Ø6 × 90°“, „2 × Ø8 – 15 tief / Fase 0,5 × 45°“
  (Spannplatte), „4 × Ø6 – durch / TK Ø40“ (Buchse; Lochkreis als TK Ø statt Radius). `masse` zählt nur noch Maße
  (Buchse 10 statt 12), neu `angaben = {plan, gesetzt}` (Spannplatte 2/2, Buchse 1/1).
- Textzusätze an Maßen: Reihenmaß „4 × 30,00 (= 120)“, Fasen „× 45°“ (Buchse 1,00 × 45° und 0,50 × 45°); Beschriftung
  „EINZELHEIT B“ statt „DETAIL B“, über der Ansicht.
- Live-Lehren (Spike `spike-z1.md` „Stufe 3“): `SelectEntity` auf die Kante lässt den Pfeil auf der Gegenseite des
  Kreises enden, die Hinweislinie läuft quer durch die Bohrung; `SelectByID2` mit einem Blattpunkt auf dem Kreis zum Text
  hin setzt den Pfeil dorthin (Soll 45°/135°, Ist 49°/137°). Ø, ×, –, ° als Unicode schreiben (`<MOD-DIAM>` zerlegt den
  PDF-Text); `\n` wird in SolidWorks `\r\n`. Größe des Hinweises am PDF vermessen, nicht über `GetExtent`.
  Beschriftung unter der Einzelheit lag auf der Maßreihe; über der Ansicht kein Befund
  (`swDetailingDetailViewLabels_AboveView` vor dem Anlegen setzen).
- Live (frisches SolidWorks, SW 2025): beide Läufe OK (`tests/live/test_live_zeichnen.py`), im PDF jede Zeile der Angaben,
  „4 × 30,00 (= 120)“, „EINZELHEIT“ und zweimal „× 45°“ gefunden, keine `ANGABE_*`-Meldung, `LESBARKEIT` leer.
  Durchsicht der Blätter: Hinweislinien enden am Kreis, keine Überlagerungen.
- Offen: Hinweislinien, die Bauteilkanten kreuzen, werden nicht geprüft (Spannplatte: die Hinweislinie des Ø8 läuft über die Plattenecke unten rechts;
  sie liest sich, ist aber nicht geprüft); Beschriftung „EINZELHEIT“ über der Ansicht braucht das
  OK des Nutzers.
- Offen: Die Hinweislinie ist beim Verschieben der Hinweise kein Hindernis-Kriterium.
- Offen: Ein Befund zwischen zwei Zeilen desselben Hinweises rückt die Reihen.
- Offen: Gewindeangabe nur mit dem Nenndurchmesser aus der Normtabelle; eine unbekannte Größe meldet `ANGABE_UNBEKANNT`.
- Bohrungsangabe (Review): „1 ×“ entfällt bei einer Bohrung, Steigung als „M12 × 1,5“, Senkung einer `bohrung` als Zeile,
  Tiefe, Senkung und Fasenwinkel stehen nur im Angabetext bzw. Suffix (kein zweites Maß); eine Lochkreisposition mit zwei
  Komponenten ungleich 0 meldet `ANGABE_UNVOLLSTAENDIG` (Winkellage).

## Z1.3 Stufe 4 – Toleranzen, Rauheit, Form/Lage, Sammelangaben (28.11.2026)

Plan `docs/superpowers/plans/2026-11-27-zeichnungsableitung-z13-stufe4.md`, Spike `spike-z1.md` (Nachträge Stufe 4,
a–i), Referenzen `tests/referenz/zeichnung/spannplatte_z.yaml` und `buchse_z.yaml`.

Was jetzt gilt:
- **Toleranz und Passung am Zeichnungsmaß.** An einem eingefügten Modellmaß gingen Toleranz und Textzusatz beim
  Wiederöffnen der SLDDRW verloren (Spike a). Das betraf auch die Zusätze der Stufe 3: „4 × 30,00 (= 120)“ stand im
  PDF, fehlte aber in der wieder geöffneten Zeichnung. Jedes Plan-Maß mit Toleranz oder Zusatz wird deshalb über die
  Bezugspunkte seiner Hilfslinien ein Zeichnungsmaß `RD<n>@<Ansicht>` (`anforderungen_setzen.dauerhaft_machen`). Gelingt
  das nicht, bleibt das Modellmaß stehen, ohne Zusatz und mit `MASS_NICHT_DAUERHAFT`. Drehteilmaße sind schon
  Zeichnungsmaße. Abmaße setzt `SetValues`, Passungen `Type = 7` mit `SetFitValues`, Anzeige einzeilig „20,00 H7“.
- **Ⓔ nur an Passmaßen**, immer als Symbol `<MOD-EP>`, auch in der Bohrungsangabe („2 × Ø8 H7 Ⓔ“). Das Unicode-Zeichen
  lässt den ganzen Maßtext verschwinden (Spike e/f). pymupdf liest das Symbol als alleinstehendes „E“ mit Ring.
- **Rauheit** im Feld a unter dem Strich nach ISO 1302:2002 (`ISFSymbol.SetText(8)`). Die Zeichnung wird dafür von
  ISO 21920-1 (Vorlage) auf ISO 1302:2002 umgestellt (Spike g). Die Hinweislinie setzt an der Kante des Merkmals an.
- **Form/Lage** als Toleranzrahmen mit Bezug, an mehreren Instanzen mit „n ד über dem Rahmen. Bezugsdreiecke stehen
  auf der Fläche oder ihrer Verlängerung (ISO 5459). Form/Lage an einer `extrusion`/`schnitt` gilt für deren Endfläche.
  `form_lage` mit IT-Grad meldet `FORM_LAGE_IT_OHNE_TABELLE` (keine ISO-286-Tabelle).
- **Sammelangaben** als Hinweis im Band über dem Schriftfeld:
  - immer: Allgemeintoleranzen ISO 2768-1:1989 – m, Tolerierung ISO 8015:2011, Kanten ISO 13715 −0,1 … −0,3,
    „Maßgebend ist die Zeichnung“;
  - dazu Behandlung und Halbzeug aus der Spec;
  - rechts daneben „Oberflächen ohne Angabe: Ra 3,2“.
- **Buchstaben:** Schnitte ab A ohne I, O, Q und ohne Bezugsbuchstaben (SpannplatteZ: Schnitt C-C, weil A und B
  Bezüge sind). Einzelheiten ab Z rückwärts.
- Anmerkungen (Rauheit, Rahmen, Bezüge) stellen sich der PDF-Prüfung wie die Hinweise. Was keine freie Lage findet,
  wird gemeldet (`ANMERKUNG_KREUZT`, `ANMERKUNG_ZU_NAH`), nie still hingenommen.
- `swki zeichnen` schreibt die Übergabe `zeichnung/zeichnung.json` für die Zeichnungsprüfung Z1.4. Sie enthält Plan,
  Gesetztes, SHA-256 der SLDDRW, Meldungen, Ansichten und die umgewandelten Maße.

Live 28.11.2026 (frisches SolidWorks 2025, `tests/live/test_live_zeichnen.py`, 4/4 grün). Jede Zeichnung wurde danach
schreibgeschützt wieder geöffnet (Rückleser Z1.4). Toleranzen, Zusätze, Ⓔ und Bohrungsangaben waren erhalten,
Teil- und Zeichnungs-SHA unverändert, danach keine Dokumente offen.

| Zeichnung | Blatt | Ansichten | Restmeldungen |
|---|---|---|---|
| SpannplatteZ | A3 quer 1:2 | Haupt, Schnitt C-C, Seite, Einzelheit Z 1:1 | `RAUHEIT_NUR_EINE_INSTANZ` (t1 Ra 1,6; st Ra 0,8), `ANMERKUNG_KREUZT: st rauheit „Ra 0,8“` (Linie, 2 Maßlinien, Kante), `FUNKTION_UNBESTAETIGT: st: passung, rauheit`, `ANSICHT_DICHT` (D9@k1_pfad), `EINZELHEIT: t1`, `EINZELHEIT_NICHT_FUER: k1`, `LAUF_NICHT_BESTANDEN` |
| BuchseZ | A3 quer 1:1 | Stirnansicht, Schnitt A-A | nur `LAUF_NICHT_BESTANDEN` |
| Spannplatte (Stufe 3) | A3 quer 1:2 | Haupt, Schnitt A-A, Seite, Einzelheit Z 1:1 | `ANSICHT_DICHT`, `EINZELHEIT: t1`, `EINZELHEIT_NICHT_FUER: k1`, `LAUF_NICHT_BESTANDEN` |
| Buchse (Stufe 3) | A3 quer 1:1 | Stirnansicht, Schnitt A-A | nur `LAUF_NICHT_BESTANDEN` |

- `LAUF_NICHT_BESTANDEN` kommt nur, weil der Test ohne Prüfer-Urteil zeichnet.
- Im PDF gefunden:
  - SpannplatteZ: „2 × Ø8 H7 Ⓔ“ / „15 tief“ / „Fase 0,5 × 45°“ (dreizeilig, ohne Strich am Zeilenende),
    „150,00 ±0,02“, „Ra 0,8“, „Ra 1,6“, „▱ 0,02“, „2 ×“ über „// 0,05 A“, „SCHNITT C-C“, „EINZELHEIT Z“;
  - BuchseZ: „Ø32,00 k6 Ⓔ“, „Ø20,00 H7 Ⓔ“, „einsatzgehärtet und angelassen (60 ± 2) HRC, CHD = (0,8 +0,4/0) mm
    (550 HV1)“, „Halbzeug: Rund EN 10060 – 55“;
  - alle vier: die Sammelzeilen.
- Durchsicht der Blätter (PNG, Ausschnitte):
  - Rahmen, Bezüge A/B und Ra 1,6 im Schnitt C-C stehen frei. Die Hinweislinien laufen durch die Taschenöffnung, nicht
    durch die Schraffur. Die Hinweislinie von Ra 1,6 schneidet dabei die Übergangslinie des Eckradius der eigenen
    Tasche (r1). Gemeldet ist das nicht, vermutlich weil die Öffnung des eigenen Merkmals als frei gilt
    (Nachbesserung C). Das ist ungeprüft.
  - Ra 0,8 (Stiftbohrung) steht links neben der Hauptansicht auf der Maßlinie 27,00. Seine Hinweislinie kreuzt die
    Plattenkante und die Kabelnut, das ist gemeldet.
  - BuchseZ: Die Ø-Maße mit Passung stehen unter dem Schnitt, ihre Maßlinien sind dafür weit nach unten verlängert.
    Das ist lesbar, aber ungewohnt. Die Mittellinie im Schnitt A-A fehlte in einem Lauf und war im letzten da; die
    Ursache ist offen.
  - Das Schriftfeld zeigt keine Benennung (Zuordnung Z1.5).
- 20-mm-Reserve für die Sammelangaben: In jedem echten Lauf sind es mindestens vier Pflichtzeilen à 5 mm
  (`SAMMEL_ZEILE_MM`). Die Ansichten haben dadurch weniger Platz über dem Schriftfeld. Format, Maßstab oder die
  Einzelheit können kippen; `einzelheit_passt` ist mit Reserve nie günstiger. In den Tests ohne SolidWorks
  (`tests/zeichnung/test_layout.py`) verdrängen 40 mm Reserve einen Platzbedarf von 100 × 190 mm vom A4 auf A3 quer, und
  eine Einzelheit, die ohne Reserve passt, gilt mit Reserve nicht mehr als passend. Live hat nur die Spannplatte einen Vorher-Wert: Blatt 1:2 und Einzelheit 1:1
  wie am 18.11. (damals die Kabelnut, seit 19.11. die Tasche). Für die Buchse gibt es keinen dokumentierten Vorher-Wert.
- Die Stufe-3-PDFs in `<arbeitsordner>/Z1-STUFE1/` sind mit diesem Lauf neu geschrieben, jetzt mit Sammelangaben und
  Einzelheit Z. Die Stufe-4-PDFs liegen in `Z1-STUFE4/`, mit `<name>.zeichnung.json` (Meldungen).

Vorschläge – Nutzer entscheidet:
- **Härtestil** nach ISO 15787:2016 / DIN ISO 15787:2018 („(60 ± 2) HRC“, „CHD = (0,8 +0,4/0) mm“) statt DIN 6773
  („58+4 HRC“). Der Normtext liegt uns nicht vor (`haerteangabe.md`).
- **Ⓔ aus `toleranzen`:** Jede Passung aus `toleranzen` gilt als Passmaß und bekommt Ⓔ, reine Abmaße nicht. Das ist
  eine feste Regel: `toleranzen` kennt nur `passung` bzw. Abmaße, ein Feld `huelle` gibt es nur am Feature.
  Alternative: `huelle` auch in `toleranzen` zulassen.
- **IT-Grad für Form/Lage** (`{it: 4}` aus `funktionen.yaml`) bleibt ohne Zahl, bis eine ISO-286-Tabelle mit ≥ 2
  Quellen vorliegt (`FORM_LAGE_IT_OHNE_TABELLE`).
- **Symbolnorm Rauheit** – *entschieden 28.11.2026:* ISO 1302:2002 statt ISO 21920-1 der Vorlage. Mit 21920-1
  zeichnet SolidWorks über jedes Symbol einen losen Strich (Spike g), für den Nutzer unbrauchbar.
- **Wortlaut** „Oberflächen ohne Angabe: Ra 3,2“ – *entschieden 28.11.2026:* ersetzt durch das Rauheitsfeld (Symbol
  „Ra 3,2“ und „Alle Flächen ohne andere Angabe“), siehe „Nutzerentscheidungen 28.11.2026“.
- **Schnittbezeichnung C-C** bei Bezügen A/B, damit Schnitt- und Bezugsbuchstaben verschieden sind.
- **Rauheit an nur einer von n Instanzen:** SolidWorks setzt bei Mehrfachauswahl nur eine Hinweislinie (Spike h).
  Optionen: je Instanz ein eigenes Symbol, oder hinnehmen (heute `RAUHEIT_NUR_EINE_INSTANZ`, in Z1.4 ein Mangel).
- **Ra 0,8 an den Stiftbohrungen** findet keine freie Lage (`ANMERKUNG_KREUZT`) – *entschieden 28.11.2026:*
  Stiftbohrungen bekommen keine eigene Rauheit, die Sammelrauheit gilt.

Offen:
- Z1.5: Die ISO-Vorlage druckt „ENTGRATEN UND SCHARFE KANTEN BRECHEN“ und leere Felder „OBERFLÄCHENGÜTE“,
  „TOLERANZEN: LINEAR / WINKEL“. Das widerspricht den Sammelangaben (Kanten ISO 13715 −0,1 … −0,3, ISO 2768-1 m,
  Ra 3,2). Mit dem Firmenformat entscheiden, ob die Werte in die Felder kommen oder der Vordruck entfällt. Ebenso fehlt
  die Benennung im Schriftfeld.
- Stufe-3-Hinweislagen sind nicht neu bewertet (Review Task 5, I-1/M10 zurückgestellt). Live sind sie unverändert.
- Kleinere Punkte aus dem Review der Nachbesserung E (M-2 Umhängen leeren, M-4 zwei Schnitte mit gleichem
  Buchstaben) sind mit der Fix-Welle nach dem Gesamtreview erledigt (siehe unten).

## Nutzerentscheidungen 28.11.2026

- **Stiftbohrung ohne eigene Rauheit.** `funktionen.yaml`: `stiftbohrung` ohne `rauheit` (auch nicht im `beleg`), Quelle
  „Nutzer 28.11.2026“. Passung H7 bleibt C und unbestätigt (`FUNKTION_UNBESTAETIGT: st: passung`). Bestehende Freigaben
  mit `stiftbohrung` melden jetzt `FUNKTIONEN_VERALTET` (Tabellenstand ≠ Freigabe), also neu freigeben. Damit entfallen
  an der SpannplatteZ „Ra 0,8“, `ANMERKUNG_KREUZT` und `RAUHEIT_NUR_EINE_INSTANZ` an st.
- **Rauheitsfeld statt Textzeile.** Rechts oben im Band über dem Schriftfeld ein Kasten 71 × 14 mm mit dem
  Rauheitssymbol (Grundsymbol, Feld a „Ra 3,2“, ohne Hinweislinie) und dem Hinweis „Alle Flächen ohne andere Angabe“
  (zwei Zeilen). Er ersetzt „Oberflächen ohne Angabe: Ra 3,2“. Die Sammelzeilen stehen links daneben, der Kasten
  beginnt an der ersten Zeile, ab der drei Zeilen höchstens 42 Zeichen haben; das Band wird bei den Referenzen nicht
  höher (SpannplatteZ 5, BuchseZ 7 Zeilen). Rahmen als Blattskizze mit Farbe Schwarz (Spike: Blattskizzen folgen dem
  Blattmaßstab und kämen sonst blau ins PDF). Grundsymbol statt „Bearbeitung verlangt“, weil Halbzeugflächen roh
  bleiben dürfen. Geometrie ohne SolidWorks in `swki/zeichnung/sammelfeld.py`, genutzt von Zeichnen, PDF-Prüfung
  (`sammel_pruefen`: Texte im Kasten, keine Sammelzeile darüber) und Zeichnungsprüfung. Spike: `spike-z1.md`, Nachtrag
  Rauheitsfeld.
  - Prüfung: Ein Rauheitssymbol ohne Kante mit Lage (Spitze) im Band ist die Sammelrauheit (Z-SAM-7: genau ein Symbol
    mit Feld a „Ra 3,2“ und der Hinweis), keine Merkmalsrauheit. Außerhalb des Bands bleibt es eine Rauheit ohne
    Merkmal (Z-TOL-4, hart). Die alte Textzeile genügt nicht mehr. Der Rückleser liest die Lage aller Rauheitssymbole
    und meldet ein freies Symbol auf dem Blatt nicht als `RUECKLESEN_UNVOLLSTAENDIG`. Den Regeltext von Z-SAM-7 („nahe
    dem Schriftfeld“) braucht es dafür nicht zu ändern.
- **Symbolnorm ISO 1302:2002** (entschieden). Mit ISO 21920-1 zeigt SolidWorks über jedem Symbol einen losen Strich.
- **R-Maß in der Einzelheit frei.** „R4,00“ in der Einzelheit Z wurde vom Rahmen der Einzelheit durchbrochen. Ursache:
  Hindernis der Radiuszahl war nur der Rahmen in der Elternansicht, nicht der eigene Rahmen in der Einzelheit
  (`zeichnen._radius_rahmen`). Die PDF-Prüfung übersah es, weil SolidWorks diesen Rahmen als Viereck (`qu`) ins PDF
  schreibt und `pruefe_pdf` nur Linien und Rechtecke las; jetzt zählen Vierecke mit (Test mit den Live-Zahlen). Am
  alten PDF findet die Prüfung den Befund jetzt (SpannplatteZ und Spannplatte).
- **Beschriftung „EINZELHEIT Z“ über der Ansicht** bleibt.

Live 28.11.2026 nach den Entscheidungen (je Datei frisches SolidWorks 2025): `tests/live/test_live_zeichnen.py` 4/4,
`tests/live/test_live_zeichnung_pruefen.py` 6/6 grün, darunter neu `test_rauheitssymbol_ausserhalb_des_felds` (Symbol
der Kopie links oben aufs Blatt gesetzt: genau Z-SAM-7 „fehlt“ und Z-TOL-4 „überzählig, ohne Merkmal“). Restmeldungen
der SpannplatteZ jetzt nur `RAUHEIT_NUR_EINE_INSTANZ: t1 Ra 1,6`, `FUNKTION_UNBESTAETIGT: st: passung`,
`ANSICHT_DICHT`, `EINZELHEIT: t1`, `EINZELHEIT_NICHT_FUER: k1`, `LAUF_NICHT_BESTANDEN`; kein `ANMERKUNG_KREUZT`, kein
„Ra 0,8“ im PDF. BuchseZ, Buchse, Spannplatte unverändert bis auf das Rauheitsfeld. „R4,00“ steht in beiden
Spannplatten außerhalb des Rahmens der Einzelheit, nur die Hinweislinie kreuzt ihn. Das Rauheitsfeld steht rechts oben
im Band, schwarz, ohne Überlappung mit den Sammelzeilen; das Band ist so hoch wie vorher (Format und Maßstab gleich).

## Z1.4 – Zeichnungsprüfung (28.11.2026)

Plan `docs/superpowers/plans/2026-11-27-zeichnungsableitung-z14-pruefen.md`, Design §8 (Prüfen) und §10
(Negativfälle). Live-Test `tests/live/test_live_zeichnung_pruefen.py`.

Befehle:
- `swki zeichnung pruefen <spec> [--lauf N]` liest die von `swki zeichnen` gespeicherte SLDDRW schreibgeschützt zurück
  (`swki/zeichnung/rueckleser.py`, Ist-Modell `ist.py`). Danach prüft er sie gegen die Spec (Arbeitsdatei nach
  geprüfter Freigabe, wie `swki zeichnen`), den neu gerechneten Maßplan und den Regelkatalog (`pruefen.py`, rein, ohne
  SolidWorks). Der Bericht steht unter
  `protokolle/<spec>.lauf-<n>.zeichnung.pruefbericht.json`.
  - Kopfprüfung: Weicht die SHA-256 der Zeichnung von der Übergabe `zeichnung/zeichnung.json` ab, kommt
    `ZEICHNUNG_GEAENDERT` (Handänderung). Weicht der Maßplan ab, kommt `ZEICHNUNG_PLAN_VERALTET`; gelten die Werte
    aus `funktionen.yaml` nicht mehr wie bei der Freigabe, `FUNKTIONEN_VERALTET`. Das heißt nie „bestanden“, und das
    PDF wird dann verworfen.
  - Ändert das Rücklesen Teil oder Zeichnung (SHA vorher ≠ nachher), bricht der Befehl ab
    (`ZEICHNUNG_PRUEFUNG_AENDERT`).
  - Geschlossen wird nur, was das Öffnen geladen hat. Bleibt etwas offen, kommt `RUECKLESEN_NICHT_GESCHLOSSEN`.
- `swki durchlauf <spec> --zeichnung` zeichnet den letzten bestandenen Lauf (Teil-Prüfer bestanden), prüft die
  Zeichnung und gibt den fertigen Auftrag für den Agenten aus (`zeichnungspruefer_auftrag`). Es baut nicht neu.
- Agent `zeichnungspruefer` (`.claude/agents/zeichnungspruefer.md`, nur Read und Glob). Er bekommt Eingabe,
  freigegebene Spec, Prüfbericht, PDF/PNG und Regelkatalog, aber keine Bauprotokolle und keinen Maßplan als Maßstab. Sein
  Urteil liegt in `protokolle/<spec>.lauf-<n>.zeichnungspruefer.json`. Fehlt es, meldet `swki bericht`
  `ZEICHNUNGSPRUEFER_FEHLT` („Zeichnung ungeprüft“).

Regelkatalog `swki/wissen/zeichnungsregeln.yaml`:
- 25 Regeln für die neun Prüfungen aus Design §8.1: vollständig 2, überbestimmt 1, Toleranzen 6, Sammelangaben 7,
  Schriftfeld 3, Ansichten 3, Lesbarkeit 1, Gewinde 1, Drehteil 1.
- 24 Regeln sind hart. Nur Z-LES-1 (Lesbarkeit) ist ein Hinweis.
- Belegstärke: 10 × A, 10 × B, 5 × C.
- Herkunft: 17 × `norm`, 8 × `projekt` (Z-TOL-1, Z-TOL-2, Z-SAM-2, Z-SAM-4, Z-SAM-5, Z-SCH-2, Z-ANS-1, Z-GEW-1).
- Der Lader erzwingt: Eine harte Regel hat Beleg A/B oder `herkunft: projekt` mit Quelle (Nutzer bzw. Design und Datum).
  Alle fünf C-Regeln (Z-TOL-1, Z-SAM-4, Z-SAM-5, Z-SCH-2, Z-ANS-1) sind Projektregeln.

Meldungscode → Regel (`MELDUNG_REGEL` in `pruefen.py`):
- Die Meldungen der Übergabe (`swki zeichnen`) und des Rücklesers werden zu Mängeln der Regel, zu der sie gehören.
  `test_jeder_meldungscode_hat_regel` sammelt alle Codes aus `swki/zeichnung/*.py` über den Syntaxbaum.
- Ein unbekannter Code wird Mangel Z-VOLL-1 („unbekannte Zeichnungsmeldung“), nie still.

| Meldungen | Regel |
|---|---|
| `MASS_NICHT_DAUERHAFT`, `MASS_NICHT_GEPLANT`, `MASS_NICHT_GESETZT`, `MASS_OHNE_ANSICHT`, `ANGABE_*` (nicht gesetzt, ohne Ansicht/Hinweislinie/Achse, unbekannt, unvollständig), `RUECKLESEN_UNVOLLSTAENDIG` | Z-VOLL-1 |
| `ANGABE_DOPPELT`, `ANMERKUNG_DOPPELT`, `MASS_NICHT_GELOESCHT` | Z-VOLL-2 |
| `TOLERANZ_NICHT_GESETZT`, `TOLERANZ_OHNE_MASS`, `TOLERANZ_MEHRDEUTIG`, `FORM_LAGE_IT_OHNE_TABELLE`, `FUNKTION_UNBEKANNT` | Z-TOL-1 |
| `RAUHEIT_NICHT_GESETZT`, `RAUHEIT_NUR_EINE_INSTANZ` | Z-TOL-4 |
| `FORM_LAGE_NICHT_GESETZT`, `FORM_LAGE_NUR_EINE_INSTANZ` | Z-TOL-5 |
| `BEZUG_NICHT_GESETZT` | Z-TOL-6 |
| `SAMMELANGABE_FEHLT`, `SAMMELANGABEN_NICHT_GESETZT` | Z-SAM-1 (Zeile der Sammelrauheit: Z-SAM-7) |
| `EINZELHEIT_BUCHSTABE`, `SCHNITT_BUCHSTABE` | Z-ANS-2 |
| `BEZUG_OHNE_KANTE`, `MITTELLINIE_NICHT_GEZEICHNET` | Z-ANS-1 |
| `ANMERKUNG_KREUZT`, `ANMERKUNG_ZU_NAH`, `ANGABE_ZU_NAH`, `ANSATZ_NICHT_FREI`, `LESBARKEIT`, `LESBARKEIT_UNGEPRUEFT`, `SCHRAFFUR_UNGELESEN`, `ANMERKUNG_NICHT_UMGEHAENGT`, `MASSE_NICHT_ANGEORDNET`, `HILFSLINIE_NICHT_MITTELLINIE`, `SAMMELANGABE_UEBERLAUF` | Z-LES-1 (Hinweis); Überlauf der Sammelrauheit: Z-SAM-7 |
| `FUNKTION_UNBESTAETIGT`, `LAUF_NICHT_BESTANDEN`, `ANSICHT_DICHT`/`_VOLL`, `EINZELHEIT*` (Ansichtswahl), `ANSICHT_GERATEN`, `ANSICHT_NICHT_GELOESCHT`, `SCHNITT_NICHT_*`, `RUECKLESEN_NICHT_GESCHLOSSEN`, `ZEICHNUNG_GEAENDERT`, `ZEICHNUNG_PLAN_VERALTET`, `PDF_VERWORFEN` | nur Bericht, mit Begründung (`NUR_BERICHT`); Kopfmeldungen setzen bestanden False |

Live 28.11.2026 (frisches SolidWorks 2025): `swki zeichnung pruefen <spec> --lauf 1` auf den Läufen der Stufe 4
(`<arbeitsordner>/Z1S4-spz`, `Z1S4-bz`, `Z1S4-stil`). Teil- und Zeichnungs-SHA waren vorher und nachher gleich.
`GetDocuments` war vorher und nachher leer.

| Zeichnung | Ergebnis | Mängel und Hinweise |
|---|---|---|
| SpannplatteZ | nicht bestanden | 2 × Z-TOL-4 aus `RAUHEIT_NUR_EINE_INSTANZ` (t1 Ra 1,6; st Ra 0,8), Hinweis Z-LES-1 (`ANMERKUNG_KREUZT` st Ra 0,8) |
| BuchseZ | bestanden (seit der Fix-Welle: nicht bestanden, Z-SCH-1 Schriftfeld, s. u.) | – |
| Spannplatte (Stufe 3) | bestanden (seit der Fix-Welle: nicht bestanden, Z-SCH-1 Schriftfeld, s. u.) | – |

- Die Prüfberichte liegen unter `protokolle/<spec>.lauf-1.zeichnung.pruefbericht.json` neben den Arbeits-Specs der
  drei Läufe. Diese Specs liegen im Scratchpad der Sitzung, nicht im Repo; die Berichte sind also temporär.
- SpannplatteZ ist nicht bestanden, weil die Regel hart bleibt: Eine Rauheit an nur einer von n Instanzen ist ein
  Mangel (Vorschlag Stufe 4, Entscheidung des Nutzers offen). Der Rückleser selbst verursacht keinen harten Mangel.
- Nachweise zur Nachbesserung 4b (Commits c16a541, 3c9676d):
  - Alle sechs Anforderungen der SpannplatteZ hängen an einer Kante mit Merkmal: Ra 0,8 → st, ▱ 0,02 → f1,
    „2 ד // 0,05 A → t1, Bezüge A und B → f1, Ra 1,6 → t1. Es gibt kein „ohne Merkmal“ und kein
    `RUECKLESEN_UNVOLLSTAENDIG`, die Meldungen des Rücklesers sind in allen drei Läufen leer.
  - BuchseZ: Die vier linearen Ø-Maße im Längsschnitt (Präfix `<MOD-DIAM>`, Ø50, Ø32 k6, Ø20 H7, Ø30) haben lesbare
    Hilfslinien, `verdeckt` ist bestimmt (False).
  - Einzelheit Z (Tasche 50 × 30 mit R4) in SpannplatteZ und Spannplatte: 50 und 30 sind nicht verdeckt, die gedachte
    Ecke wird erkannt. Die Prüfung `ansichten` ist ok, es gibt keinen Z-ANS-1. Das R4-Maß selbst hat `verdeckt` None
    (Radiusmaß, bekannte Grenze).
  - Kein lineares Maß hat `verdeckt` None.
  - Eine Eigenschaft „Blatt“ gibt es nicht. Das Schriftfeld-Feld Blatt ist deshalb „nicht geprüft“ (Prüfung
    `schriftfeld` ok None, zusammen mit dem Hinweis Eigentümer leer). Vor der Nachbesserung stand „Blatt: 1/1“ im Ist,
    das hatte der Rückleser selbst gesetzt (M5).
- `tests/live/test_live_zeichnung_pruefen.py` sichert diese Nachweise für SpannplatteZ und BuchseZ zu (Merkmal je
  Anforderung, lineare Ø-Maße, `ansichten` und `ueberbestimmt` ok, Blatt „nicht gelesen“). Die Stufe-3-Spannplatte
  ist nur über die CLI gelaufen, nicht im Test. Ganze Datei über `tests\live_einzeln.py --zeit 1500` auf frischem
  SolidWorks: 5/5 „OK“. Davon ist der Sammelnotiz-Fall ein xfail (siehe unten); `live_einzeln` zeigt einen xfail als
  „OK“ an. *(Stand vor dem Gesamtreview; seither echt grün, Abschnitt „Gesamtreview“.)*

Negativfälle live (Kopie der Zeichnung im Laufordner per COM verändert und gespeichert, geprüft über dieselbe Kette
wie `swki zeichnung pruefen`). Verglichen wird mit dem Bericht des unveränderten Originals. Teil und Original-Zeichnung
haben vor und nach der Prüfung dieselbe SHA.

| Kopie | Manipulation | neue Mängel (genau diese) |
|---|---|---|
| SpannplatteZ | Maß 27 (Kabelnut k1) gelöscht | Z-VOLL-1 k1 „fehlt: 27 (k1)“ |
| | Bohrungsangabe „2 × Ø8 H7 Ⓔ“ → H8 | Z-VOLL-1 st „fehlt: Angabe 2 × Ø8 H7 Ⓔ – 15 tief“ (seit dem Gesamtreview: Z-TOL-1 st) |
| | „ <MOD-EP>“ (Ⓔ) an 150 ±0,02 | Z-TOL-2 st „150: Ⓔ an einem Maß ohne Passung“ |
| | Notiz „ISO 2768-mK“ | Z-SAM-3 „verboten: ISO 2768-mK“ |
| | Eigenschaft Benennung geleert | Z-SCH-1 „Pflichtfeld Benennung leer (Eigenschaft Benennung)“ |
| BuchseZ | Ø20: Passung H7 → H8 (`SetFitValues`) | Z-TOL-1 f1 „Ø20: Toleranz H8 statt H7“ |
| SpannplatteZ | Sammelangaben-Notiz per `SetPosition2` unter das Blatt (y = −50 mm) | **keiner** (Befund, xfail; seit dem Gesamtreview: Z-SAM-1) |

- Abweichungen vom Plan (Task 6, Step 1):
  - **Passung H7 → H8 an der SpannplatteZ** ergibt Z-VOLL-1, nicht Z-TOL-1. Die Passung der Stiftbohrung steht nur in
    der Bohrungsangabe (Plan-Quelle `angabe`, kein Maß mit Passung). Angaben werden über den Textanfang abgeglichen
    (Entscheidung 1). Der Mangel ist hart und dem Merkmal st zugeordnet, der Text nennt das Soll H7.
  - Für Z-TOL-1 an einem Passmaß deshalb eine zweite Kopie, die BuchseZ (Ø20 H7, Zeichnungsmaß).
  - Ob eine falsche Passung in einer Bohrungsangabe als Z-TOL-1 gemeldet werden soll: Vorschlag – Nutzer entscheidet.
- **Befund Sammelangabe außerhalb des Blatts:** Die Prüfung meldet nichts. Der Rückleser liest Text, keine Lage, und
  `pruefe_sammelangaben` prüft nur den Text. Die Lage auf dem Blatt prüft nur `swki zeichnen` am PDF
  (`SAMMELANGABE_FEHLT` → Z-SAM-1, `SAMMELANGABE_UEBERLAUF` → Z-LES-1).
  - Im CLI-Weg hält eine solche Handänderung nur die Kopfprüfung auf (`ZEICHNUNG_GEAENDERT`, SHA ≠ Übergabe), keine
    Regel.
  - Der Test `test_sammelnotiz_ausserhalb_des_blatts` endet als xfail, solange kein Mangel entsteht. Er erwartet Z-SAM-1.
- „Geschlossene Kette“ (Z-UEB-1) und „Maß an verdeckter Kante“ (Z-ANS-1) sind nur Unit-Tests
  (`tests/zeichnung/test_pruefen_masse.py`).
  - `swki zeichnen` erzeugt keines von beiden.
  - Die Regeln sind reine Funktionen über das Ist und dort getestet.
  - Live gezeigt ist der Anteil des Rücklesers: Bezugspunkte, Richtung und `verdeckt` sind für jedes lineare Maß
    bestimmt, `ueberbestimmt` und `ansichten` sind auf den drei Referenzen ok.
  - Ein Live-Negativfall bräuchte ein per COM neu gesetztes Maß an einer Kette bzw. einer verdeckten Kante. Das ist
    nicht gemacht.

Grenzen:
- Gelesen wird nur das aktuelle Blatt. Hat eine Zeichnung mehrere Blätter, kommt `RUECKLESEN_UNVOLLSTAENDIG`.
- Merkmal einer Angabe ist das Feature der angehängten Kante (über die Nachbarflächen), nicht die Fläche. Eine Kante
  zwischen zwei Merkmalen ergibt „a/b“ und deckt genau einen Plan-Eintrag. Ohne Merkmal ist eine Angabe nie ein Joker,
  sondern überzählig.
- Die Instanzzahl der Rauheit kennt die Prüfung nur aus der Übergabe (`RAUHEIT_NUR_EINE_INSTANZ`). Das Rauheitssymbol
  hat kein „n ד wie der Toleranzrahmen.
- Z-DRE-1 an Linearmaßen des Längsschnitts: Dort kommt Ø als Präfix `<MOD-DIAM>`, und der Rückleser liest die Maßart
  aus dem Präfix (`rueckleser.massart`). Fehlt dort das Ø, ist das Maß eine Länge. Laut Code (nicht live) kommt dann
  Z-VOLL-1 „fehlt: Ø…“ und Z-VOLL-2 „überzählig“, nicht Z-DRE-1. Hart bleibt es trotzdem.
- `verdeckt` gibt es nur für lineare Maße. Ø-, R- und Winkelmaße haben None und werden nicht als Mangel gezählt; die
  Darstellung beurteilt der Zeichnungsprüfer.
- Die Lage von Anmerkungen und Sammelangaben prüft nur das PDF aus `swki zeichnen`, nicht der Rückleser (Befund oben).
- Überbestimmung gilt je Ansicht und Richtung (Entscheidung 2). Maße verschiedener Ansichten gelten als unabhängig, das
  steht als Hinweis in der Prüfung `ueberbestimmt`.

Vorschläge – Nutzer entscheidet (Plan „Entscheidungen“):
1. **Abgleich Ist ↔ Plan** als Multimenge je (Ist-Art, Wert auf 0,01 mm), unabhängig von der Ansicht. Angaben werden je
   Merkmal der Hinweislinie mit ganzem Text abgeglichen (seit dem Gesamtreview), Zusätze („4 × “, „ (= 120)“) exakt
   verglichen.
2. **Überbestimmt** je Ansicht und Richtung als Maßgraph. Hilfsmaße in Klammern schließen eine Kette ohne Mangel.
3. **Schriftfeld:** acht Pflichtfelder nach ISO 7200, Zuordnung zu den Eigenschaften in `config/standard.yaml`
   (`zeichnung.schriftfeld`).
   - Eigentümer leer ist nur ein Hinweis bis Z1.5.
   - „Freigegeben“ bleibt leer.
   - Dokumentart „Einzelteilzeichnung“ als Hausregel.
   - Blatt nicht geprüft, solange keine Eigenschaft da ist.
4. **Lesbarkeit** (Z-LES-1) ist nur ein Hinweis. Die PDF-Prüfung bekommt die gelegten Toleranzrahmen mit.
5. **Maßstab aus der Vorzugsreihe** nach ISO 5455 für Blatt und Einzelheit.
6. **Lesart von `durchlauf --zeichnung`:** zeichnet und prüft den letzten bestandenen Lauf, baut nicht neu. Das
   Teil-Prüfer-Urteil ist Voraussetzung für `swki zeichnen`, deshalb kann ein Aufruf nicht bauen, prüfen und zeichnen.

### Urteile des Agenten `zeichnungspruefer` (28.11.2026, Lauf 1 der Referenzen, Urteil unverändert abgelegt)

Beide Urteile lauten „maengel“. Der Agent findet, was die Maschine nicht sieht: Die Maschine vergleicht die Zeichnung mit
dem **Maßplan**, der Agent mit der **Spezifikation**. Fehlt ein Maß schon im Maßplan, bemerkt es nur der Agent.

| Zeichnung | Mängel (Regel) | Herkunft |
|---|---|---|
| BuchseZ | Benennung nicht im Schriftfeld, Dokumentart nirgends auf dem Blatt (Z-SCH-1) | Vorlage SW 2025 → Z1.5; seit der Fix-Welle auch maschinell |
| SpannplatteZ | Radius R20 des Nutbogens und Lage des auslaufenden Schenkels fehlen (Z-VOLL-1, k1) | Maßplan Stufe 2 |
| | Kernlochtiefe 12 fehlt, nur „M6 – 10 tief“ (Z-GEW-1, g1/m1) | Bohrungsangabe Stufe 3 |
| | 16 + 4 = 20 über Seitenansicht und Schnitt geschlossen (Z-UEB-1, k1) | Maßplan Stufe 2 (Kette über Ansichten) |
| | Nutlage doppelt: 27 (Hauptansicht) und 24 + 6/2 (Seitenansicht) (Z-VOLL-2, k1) | Maßplan Stufe 2 |
| | Rechte Tasche (Spiegelung s1) ohne „2 ד bzw. Symmetriekennzeichen (Z-VOLL-1, s1) | Maßplan Stufe 2/3 |
| | Benennung/Dokumentart wie bei der Buchse (Z-SCH-1) | Z1.5 |

Hinweise des Agenten u. a.: Fasenmaße der Buchse als senkrechte Maße schwer lesbar (besser Hinweislinie), zwei
Nachkommastellen überall (Vorschlag: ohne Nachkommanullen), Passflächen ohne eigene Rauheit (Spec verlangt keine).
Die Maßplan-Lücken sind Folgearbeit (nicht Teil von Stufe 4/Z1.4); die maschinelle Prüfung wird sie erst finden, wenn sie
auch gegen die Spec statt nur gegen den Maßplan prüft (Vorschlag: Ketten über Ansichten, Kernlochtiefe aus `tiefe` ≠
`gewindetiefe`, Radien aller Bögen).

## Gesamtreview Z1.3 Stufe 4 + Z1.4 – Fix-Welle (28.11.2026)

Befund `c2cb853..2013662`, eine Fix-Welle:
- **C1** `funktionen_veraltet` (`swki/spec/freigabe.py`): die aufgelösten Anforderungen in `freigabe.json` gegen die
  heutige Auflösung der freigegebenen Kopie (Mehrfachmenge ohne Feature-ID; fehlt der Schlüssel: keine). `swki zeichnen`
  bricht mit `FUNKTIONEN_VERALTET` ab, `swki zeichnung pruefen` setzt es als Kopfmangel.
- **I1** `zeichnung pruefen` nimmt die Arbeitsdatei und prüft die Freigabe (wie `zeichnen`); eine Bauweg-Umbenennung
  nach der Freigabe macht den Plan nicht mehr „veraltet“.
- **I2** `swki bericht`: Zeichnung im letzten Lauf ohne Prüfbericht → `ZEICHNUNG_PRUEFBERICHT_FEHLT`, „Zeichnung ungeprüft“.
- **I3/M4** Bohrungs- und Gewindeangaben je Merkmal der Hinweislinie, ganzer Text: nur die Toleranz anders → Z-TOL-1
  („H8 Ⓔ statt H7 Ⓔ“), sonst „weicht ab“ (Z-VOLL-1); eine Angabe an fremder Hinweislinie fehlt am Soll-Merkmal (Z-VOLL-1)
  und ist dort überzählig (Z-VOLL-2); passender Text ohne angehängte Kante → `RUECKLESEN_UNVOLLSTAENDIG` (Z-VOLL-1).
- **I4** `swki zeichnen` ohne Extra pdf: `SAMMELANGABE_FEHLT … ungeprüft – pymupdf fehlt` statt ImportError.
- **(a)** Jeder Schnitt bekommt den nächsten freien Buchstaben; zwei gleiche Schnittbezeichnungen sind Z-ANS-2.
- **(b)** Umhängen einer Anmerkung leert die gewählte Lage; scheitert es zum Ort der besten Runde, verfällt deren Lage.
- **(c)** Lage der Sammelangaben: der Rückleser liest `IAnnotation.GetPosition` je Notiz (`IstAngabe.lage`); jede Notiz
  mit einer Sammelzeile steht mit ihrem Ankerpunkt im Band über dem Schriftfeld (±1 mm), sonst Z-SAM-1 … bzw. Z-SAM-7.
- **M2** Position und Koaxialität (Ø-Zone, theoretisch exakte Maße fehlen): `FORM_LAGE_NICHT_UNTERSTUETZT` (Z-TOL-5),
  `validieren` meldet sie als Hinweis art `zeichnung`.
- **M3** Rückleser: beide Passungswerte gesetzt → „H7/g6“ (an einer Bohrung mit H7 ein Z-TOL-1).
- **Schriftfeld (Controller)** Ein gesetztes Pflichtfeld muss mit seinem Wert im Schriftfeld des PDFs stehen (ganzes
  Wort, Mehrfachmenge), sonst Z-SCH-1 „nicht auf dem Blatt“; ohne PDF nicht geprüft. Die SW-2025-Vorlage zeigt
  BENENNUNG und die Dokumentart nicht: die Referenzen fallen damit durch, bis das Schriftfeld des Nutzers kommt (Z1.5).

Live 28.11. (frisches SolidWorks): `tests/live/test_live_zeichnung_pruefen.py` 5/5 grün, auch
`test_sammelnotiz_ausserhalb_des_blatts` (vorher xfail; jetzt genau ein neuer Mangel Z-SAM-1); im Negativfall der
Spannplatte Z ist H7 → H8 im Hinweis jetzt Z-TOL-1 an st. Die Buchse Z liest H7 an Ø20 ohne Wellenwert (M3 ohne
Fehlalarm). `swki zeichnung pruefen --lauf 1` auf den drei Referenzen: Kopf ok, alle nicht bestanden durch Z-SCH-1
Benennung und Dokumentart „nicht auf dem Blatt“; die Spannplatte Z hat dazu wie bisher RAUHEIT_NUR_EINE_INSTANZ (t1, st,
Z-TOL-4). Teil- und Zeichnungs-SHA unverändert.

Kurzreview der Fix-Welle (28.11.), bewusst so gelassen bzw. offen:
- Eine Freigabe ohne gespeicherten Tabellenstand (vor Z1.1, 17.11.) bei Specs mit `funktion` gilt als
  `FUNKTIONEN_VERALTET`: Die Tabellenwerte sind dann nie freigegeben worden, also neu freigeben. Praktisch betrifft das
  keine Spec, weil `funktion` erst mit Z1.1 kam.
- Schriftfeld am PDF: Werte, die die Vorlage umbricht oder anders formatiert (Datum), würden als „nicht auf dem Blatt“
  gemeldet; kurze Werte könnten eine fremde Zeile treffen. Mit dem Firmenschriftfeld (Z1.5) nachschärfen.
- Lage der Sammelangaben: Jede Hinweisnotiz mit „Ra 3,2“ muss im Band stehen (seit 28.11.: der Hinweis des Rauheitsfelds und die Spitze des Symbols). Geprüft wird nur der Ankerpunkt, also links
  oben; bei anderer Textausrichtung passt das nicht. `_angaben_abgleich` läuft doppelt. Alles Minor.

## Härte und Halbzeug (Nachrecherche `haerteangabe.md`)

- Härteangabe nach DIN ISO 15787:2018-08 (= ISO 15787:2016): Wert mit Grenzabmaßen in Klammern, „(60 ± 2) HRC“;
  „58+4 HRC“ ist der alte Stil (DIN 6773). Schema: `haerte`/`kernhaerte` als `{wert, plus?, minus?, verfahren}`,
  `tiefe` als `{art: CHD|SHD|NHD|CLT, wert, plus?, minus?, grenzhaerte?}`, `zustand: fertigteil|vor_schleifen`,
  `schicht: {norm, bezeichnung, dicke_um?}` (z. B. DIN EN ISO 19598 „Fe//Zn8//Cn//T0“), optionale `id` für örtliche
  Behandlung. `halbzeug` ohne `werkstoff` (aus `material`), mit `toleranz`, `zustand`.
- Offen beim Nutzer: Härtestil als Hausregel (ISO 15787:2016 empfohlen oder DIN 6773); Angabe „darf nicht behandelt
  werden“ (z. B. weich bleibendes Gewinde) hat noch kein Feld; PDF-Kandidaten (iTeh-Auszug ISO 15787:2016) brauchen OK.

## Offen für Z1.3/Z1.4

- **Maßplan-Lücken (Urteile des Zeichnungsprüfers, 28.11.):** Radius R20 und Schenkellage der Kabelnut, Kette
  16 + 4 = 20 über Seitenansicht und Schnitt, Nutlage doppelt (27 und 24 + 6/2), gespiegelte Tasche ohne „2 ד bzw.
  Symmetrie, Kernlochtiefe der Gewinde (nur „M6 – 10 tief“, Bohrtiefe 12 fehlt). Eigene Folgeaufgabe (Stufe 2/3).
- **Z-GEW-1 maschinell zu schwach (bekannter Fehlschluss):** `pruefe_gewinde` prüft nur Bezeichnung und „tief“ gegen
  den Maßplan, nicht die getrennte Bohrtiefe, die der Regeltext verlangt. Die SpannplatteZ besteht Z-GEW-1 deshalb
  maschinell, obwohl die Kernlochtiefe fehlt; nur der Agent findet es. Mit der Folgeaufgabe oben beheben.
- **Z-SCH-1 am PDF (Vorschlag – Nutzer entscheidet):** Bis zum Firmenschriftfeld (Z1.5) fällt damit jede Zeichnung
  durch, weil die SW-2025-Vorlage Benennung und Dokumentart nicht zeigt (auch an der Prüfstation). Alternative: bis
  Z1.5 nur als Hinweis führen.
- Bezugsvorschlag aus `deckungsgleich`-Verknüpfungen der Baugruppe (Design §4.1).
- Zahlenwert für `form_lage` mit `it` (Rundheit IT4/IT5) aus ISO 286 rechnen.
- Prüfung der Lage und Anzahl der Funktionsmerkmale am Modell (`ANFORDERUNG_GEAENDERT`, Design §4.2).
- Hinweis „Parameter in `toleranzen` treibt mehrere Maße“ (§4.1), Mindestradius beim Drahterodieren (§4.5).
- Kleinere Review-Punkte (Ledger „minor (deferred)“): weitere Plausibilitätsprüfungen der Toleranzfelder, Beleg je
  Feld im Hinweis, `lagersitz_gehaeuse` vom Nutzer bestätigen lassen, RWDR-Hinweis in der Auflösung.
