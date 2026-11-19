# Zeichnungsableitung – Ergebnisse

Design: `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md`. Plan Z1.0/Z1.1:
`docs/superpowers/plans/2026-11-16-zeichnungsableitung-z1-spike-spec.md`. Recherche: `recherche.md`, Härte und Halbzeug:
`haerteangabe.md`.

## Stand 17.11.2026

| Etappe | Stand |
|---|---|
| Z1.0 Spike (API live) | erledigt 17.11. (`spike-z1.md`): alles ohne Dialog außer Bohrungsangaben; Modellmaße nur gefiltert brauchbar |
| Z1.1 Spec-Erweiterung | umgesetzt (Branch `claude/zeichnungsableitung-recherche`) |
| Z1.2 Freistich, Zentrierbohrung | offen (Skill `compiler-erweitern`) |
| Z1.3 Zeichnen | Stufe 1 (Blatt, Ansichten) und Stufe 2 (Maße) umgesetzt 17.11.; Stufe 2 wartet auf Durchsicht der PDFs; Stufen 3–5 offen |
| Z1.4 Prüfen | offen |
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

## Härte und Halbzeug (Nachrecherche `haerteangabe.md`)

- Härteangabe nach DIN ISO 15787:2018-08 (= ISO 15787:2016): Wert mit Grenzabmaßen in Klammern, „(60 ± 2) HRC“;
  „58+4 HRC“ ist der alte Stil (DIN 6773). Schema: `haerte`/`kernhaerte` als `{wert, plus?, minus?, verfahren}`,
  `tiefe` als `{art: CHD|SHD|NHD|CLT, wert, plus?, minus?, grenzhaerte?}`, `zustand: fertigteil|vor_schleifen`,
  `schicht: {norm, bezeichnung, dicke_um?}` (z. B. DIN EN ISO 19598 „Fe//Zn8//Cn//T0“), optionale `id` für örtliche
  Behandlung. `halbzeug` ohne `werkstoff` (aus `material`), mit `toleranz`, `zustand`.
- Offen beim Nutzer: Härtestil als Hausregel (ISO 15787:2016 empfohlen oder DIN 6773); Angabe „darf nicht behandelt
  werden“ (z. B. weich bleibendes Gewinde) hat noch kein Feld; PDF-Kandidaten (iTeh-Auszug ISO 15787:2016) brauchen OK.

## Offen für Z1.3/Z1.4

- Bezugsvorschlag aus `deckungsgleich`-Verknüpfungen der Baugruppe (Design §4.1).
- Zahlenwert für `form_lage` mit `it` (Rundheit IT4/IT5) aus ISO 286 rechnen.
- Prüfung der Lage und Anzahl der Funktionsmerkmale am Modell (`ANFORDERUNG_GEAENDERT`, Design §4.2).
- Hinweis „Parameter in `toleranzen` treibt mehrere Maße“ (§4.1), Mindestradius beim Drahterodieren (§4.5).
- Kleinere Review-Punkte (Ledger „minor (deferred)“): weitere Plausibilitätsprüfungen der Toleranzfelder, Beleg je
  Feld im Hinweis, `lagersitz_gehaeuse` vom Nutzer bestätigen lassen, RWDR-Hinweis in der Auflösung.
