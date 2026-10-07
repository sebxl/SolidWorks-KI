# Übergabe: Umsetzung Stufe 3c – Kaufteile (STEP-Import) (Stand 2026-10-06)

## Auftrag der nächsten Sitzung
Plan **Stufe 3c** mit **superpowers:subagent-driven-development** umsetzen: ein Implementer-Agent pro Task, Review nach
jedem Task, Gesamt-Review am Ende.

- Plan: `docs/superpowers/plans/2026-10-06-kaufteile-step-import.md` (11 Tasks). Bindend sind die „Präzisierungen“ (22), die
  „Global Constraints“ und die Tabelle „Abhängigkeiten vom Spike S15“ am Anfang.
- Spec: `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` (mit dem Nutzer abgestimmt; bei der Planung
  nachgezogen: §4.1, §4.2, §4.3, §4.5, §5.1, §5.3, §6.1, §8.1, §10, §11, §12).

## Stand
- `main` steht auf `7f120d0` (Merge PR #12, Stufe 4b). Unit-Tests auf `main`: **847 passed, 133 deselected**; Live-Suite
  129/129 plus die vier Zahnstangentrieb-Negativfälle (2026-10-06).
- Branch `plan-kaufteile` (von `main`, lokal, **nicht gepusht**): Übergabe der Planungssitzung, Spec, Spec-Nachzug, Plan,
  diese Übergabe; CLAUDE.md verweist hierher.
- **Plan-Code vorab geprüft (ohne SolidWorks):** alle 11 Tasks zweimal in einem frischen Wegwerf-Worktree mechanisch aus dem
  Plan eingespielt (Tests zuerst mit RED-Lauf, dann Umsetzung, GREEN-Lauf, ganze Suite, `swki api pruefe-code swki spikes
  tests/live`). Jede Ersetzung traf genau einmal; das Ergebnis stimmt Datei für Datei mit dem Entwicklungsstand überein.
  Testzahlen je Task stehen im Plan; Soll nach Task 11: **918 passed, 141 deselected**. Muster- und Referenz-Specs validieren
  ohne Befund und ohne Hinweis; Task 7 lief mit einem simulierten Eintrag (Platzhalter für SHA-256 und Volumen).
- **Nicht vorab gelaufen:** alles mit SolidWorks – Spike S15 (Task 2, erzeugt auch die Test-STEP), SolidWorks-Schicht und
  Aufnahme live (Task 5), Muster-Eintrag mit Nutzerfreigabe und Prüfer (Task 7), Bau und Prüfen mit Kaufteilen (erst live in
  Task 10), Referenz und Negativfall (Task 10), Regression und Abnahme (Task 11).

## Nutzerentscheidungen (2026-10-06, Brainstorming)
- **Nur STEP** (AP203/214/242); Parasolid später, kein natives SLDPRT, kein IGES.
- **Eine STEP = ein Teil** (Baugruppen-STEP als Mehrkörperteil, Körperzahl geprüft); bewegliche Baueinheiten als getrennte
  STEP-Dateien.
- **Datei vom Nutzer, nur lesen**, unveränderte Kopie im Quellordner der `kaufteilbibliothek` (nicht im Git); Katalog im Git
  mit Herkunft und SHA-256. Claude legt keine Konten an.
- **Cache-Prinzip wie 3a:** Eintrag + Original sind die Quelle, `.sldprt` je SW-Jahr ein Cache.
- **Nutzerfreigabe je Eintrag** plus Prüfer-Urteil je Eintragsversion; Ablauf untersuchen → Eintrag → freigeben → muster/Prüfer
  → hole.
- **Punktanker plus Gegenprobe** für Einbaureferenzen, freie `EINBAU_*`-Namen, Drehlage als dritte Referenz.
- **STEP-Koordinaten unverändert** (keine Normalisierung).
- Prüfumfang mit **Volumen als Fingerabdruck**; **Material Pflicht, Masse aus dem Datenblatt überschreibt**.
- Baugruppe: `quelle: {kaufteil: …}`, **Baugruppen-Freigabe schützt den Eintrag mit**.
- **Streng:** Gewindegruppen im Eintrag, Gewindepaarung gilt mit, `je_position` auf Gewinde; jede andere Überlappung Mangel.
- Große Modelle: **nur messen und berichten**, keine Grenze.
- Referenz **Motorhalter** mit Muster-Getriebemotor; dazu eine **echte Herstellerdatei** des Nutzers als einmalige Abnahme.
- Befehle **`swki kaufteil`**, Paket `swki/kaufteile/`, Skill `kaufteile`, Schutzregel gegen genormte Teile.
- Einordnung **Stufe 3c**.
- Kennmaße: **Datenblatt, sonst selbst suchen, sonst nur Belegtes** (kein Mindestumfang); **Herstellerquelle allein genügt**,
  Händler nur mit ≥ 2 Domains, Widerspruch → Nutzer fragen.
- Bauweise **Eintrag = Spezifikation `art: kaufteil`** (Weiche in `validieren`/`freigeben`).
- **Test-STEP ins Git** (Ausnahme von „erzeugte SolidWorks-Dateien nicht ins Git“), 3D Interconnect beim Import aus,
  Importfehler nur erkennen, nicht reparieren (Bestätigung zur Spec, 2026-10-06).

## Abweichungen des Planers (dem Nutzer bei der Übergabe melden, Spec nachgezogen)
- Ortungsfehler und verfehlte Gegenproben sind **Mängel** `einbau:<name>`/`gewinde:<gruppe>` statt eines Codes
  `KAUFTEIL_EINBAU`; Körperfehler und Flächenkörper sind der Mangel `import`.
- `ImportDiagnosis` wird nie aufgerufen (repariert laut API-Hilfe); Diagnose über `IBody2.Check3`.
- Laufordner `KAUFTEILE/<schluessel>/lauf-<n>` auch für `untersuchen`; Katalogdateien klein geschrieben, Lageprüfung statt
  Kollisionsprüfung.
- Gewindepositionen nicht als Messpunkte von `masse_pruefen` der Baugruppe.
- „Original geändert“ und „Eintrag nach Baugruppen-Freigabe geändert“ als Unit-Tests statt live.

## Vorgaben des Nutzers
- Eigener Branch `stufe-3c`, angelegt von `plan-kaufteile`. Am Ende ein Pull Request; **vor Push und Merge fragen**.
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; die Subagents ausdrücklich darauf
  anweisen.
- Kommunikation auf Deutsch. Fragen einzeln stellen, jede mit einer Empfehlung.
- **Genormte Teile bleiben bei `swki normteil hole`**; STEP nur für nicht genormte Kaufteile.
- **Quelldateien des Nutzers nur lesen**; speichern nur im Arbeitsordner und in den Projektbibliotheken. **Keine Konten bei
  Herstellerportalen.**
- **SolidWorks-Neustarts übernimmt der Controller selbst** (Ablauf unten); vor jedem Live-Lauf mit Baugruppe frisch
  starten, **je Test**.
- **Keine künstliche CPU-Last ohne Rückfrage.**
- Ausrichtung: allgemeine Konstruktion, kein Werkzeugbau.

## Vor dem Start prüfen
- `git status` sauber (`auftraege/` ist ignoriert), `.venv\Scripts\python.exe -m pytest -q` → 847 passed, 133 deselected.
- `.superpowers/` ist lokal über `.git/info/exclude` ignoriert. SDD-Workspace über das Skript `sdd-workspace` des Skills.
- SOLIDWORKS 2025, **genau eine Instanz** (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`), keine Dokumente offen,
  Toggle 10 / Integer 6 = `False 1`; die drei Import-Optionen (Toggle 691, 690, Integer 579) notieren – nach jedem Live-Lauf
  müssen sie gleich sein.
- `config/rechner.yaml` hat noch keinen Eintrag `kaufteilbibliothek`: swki nimmt dann `%USERPROFILE%\.swki\kaufteile`
  (Vorgabe). Nicht von Hand anlegen.

## Ablauf mit Stopps
- **Tasks 1, 3, 4, 6, 8, 9:** ohne SolidWorks, Plan-Code vollständig und vorab grün → günstiges Modell für die Implementer,
  mittleres für Reviews.
- **Task 2 (Spike S15, live, frisches SolidWorks):** Der Implementer wertet nur aus. Der **Controller** entscheidet je Zeile
  der Tabelle „Abhängigkeiten vom Spike S15“, macht die Sichtprobe der Bilder (Zeile 13) und schreibt jede Entscheidung als
  Ruling in den Ledger, bevor Task 5 beginnt (Tasks 3 und 4 hängen nicht vom Spike ab und dürfen vorher laufen).
  Plan-Code-Änderungen (z. B. `OpenDoc6`, Ausrichtung `v4`, Drehlage über Hilfsachse) in die Dispatches der Tasks 5/7/10
  mitgeben. Weicht Zeile 4 (Verweis auf das Original) oder 9 (Masse) ab: **Nutzer informieren**.
- **Task 5 (live):** ein Implementer, Live-Tests einzeln; Teile bis ca. 4 GB Private Bytes in einer Sitzung, sonst BLOCKED →
  Neustart → per SendMessage fortsetzen.
- **Task 7 (live):** Step 3 ist die **Nutzerfreigabe** – der Controller zeigt dem Nutzer Eintrag, Bilder und Belege und fragt
  (eine Frage, Empfehlung „freigeben“); Step 4 Prüfer durch den Controller (Auftrag `auftraege/KAUFTEIL-MUSTER/`, danach
  löschen). Der Eintrag samt `freigabe.json`, Kopie und Urteil wird committet.
- **Task 10 (live):** Referenz je frisch; Prüfer-Urteil durch den Controller (Auftrag `auftraege/REF-3C-MOTORHALTER/`, danach
  löschen); Negativfall frisch. Weicht eine Mängelmenge ab: Erwartung nicht abschwächen, der Controller entscheidet.
- **Task 11:** Doku, Regression (Teile gemeinsam, Baugruppen je frisch), Abnahme mit der echten Herstellerdatei des Nutzers
  (den Nutzer darum bitten, Ablauf nach Skill `kaufteile`, Freigabe durch den Nutzer); danach Gesamt-Review (stärkstes
  Modell), eine Fix-Welle, Abschluss per `superpowers:finishing-a-development-branch`.

## SolidWorks-Neustart durch den Controller (bewährt in 3b, 4a, 4b)
1. Genau eine Instanz prüfen (`tasklist`), per COM `GetDocumentCount` = 0 prüfen (sonst nicht neu starten, sondern klären).
2. `ExitApp` per COM (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); app.ExitApp()"`).
3. Warten, bis kein `SLDWORKS.exe` mehr läuft.
4. Start über `installationsordner` aus `config/rechner.yaml`: `Start-Process "<installationsordner>\SLDWORKS.exe"`.
5. Pollen, bis COM erreichbar und `app.Visible` true ist; dann eine Instanz und `False 1` bestätigen.

PowerShell-Skript im Scratchpad: **nur ASCII** (Windows PowerShell 5.1 liest Skripte ohne BOM als ANSI).

## Erfahrungen (wichtig für die Live-Tasks)
- **Speicher:** Private Bytes messen, nicht das Working Set; Baugruppenläufe 8–11 GB Spitze (Stehlager bis 11,2 GB). Der
  Motorhalter ist statisch und kleiner (9 Komponenten) – Spitze mit 0,5-s-Abtastung messen und festhalten.
- **COM ist teuer** (~10–16 ms je Aufruf): Flächen großer Herstellermodelle lesen kostet Zeit (Spike-Zeile 12); die
  Vorauswahl vor `GetClosestPointOn` steht im Code.
- **Optionen:** Der Import verstellt drei SolidWorks-Optionen vorübergehend; ein hart abgebrochener Prozess kann sie verstellt
  lassen – nach jedem Abbruch prüfen und von Hand zurücksetzen (Werte aus „Vor dem Start“).
- **API:** vor jedem neuen Aufruf `swki api methode`/`enum`; Late Binding: nullargumentige Member ohne `()`.
- **Nie zwei Implementer gleichzeitig**, solange SolidWorks läuft. Reviewer und Doku-Implementer können parallel arbeiten.
- **Modellwahl:** Abschrift mit vollständigem Code günstiges/mittleres Modell, Live-Tasks und Reviews mittleres,
  Gesamt-Review stärkstes Modell.

## Dem Nutzer bei der Übergabe am Ende melden
- Testzahlen (Soll 918 passed, 141 deselected), Spike-Ergebnisse S15 und Entscheidungen, Muster-Eintrag (Freigabe, Prüfer),
  Live-Ergebnisse (Aufnahme, Referenz Motorhalter, Negativfälle, Regression, Zeit und Speicher), Abnahme mit der echten
  Herstellerdatei, Abweichungen vom Plan (Präzisierungen und alle Rulings).
- Nächste Schritte zur Wahl: Formschräge, Stufe 4c (Nut, Kurve), Paket „Messarten“, Paket Speicher.
