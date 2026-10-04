# Übergabe: Umsetzung Stufe 4a – Bewegungen (Stand 2026-10-04)

## Auftrag der nächsten Sitzung
Plan **Stufe 4a** mit **superpowers:subagent-driven-development** umsetzen: ein Implementer-Agent pro Task, Review nach
jedem Task, Gesamt-Review am Ende.

- Plan: `docs/superpowers/plans/2026-10-03-stufe-4a-bewegungen.md` (10 Tasks). Bindend sind die „Präzisierungen“, die
  „Global Constraints“ und die Tabelle „Abhängigkeiten vom Spike S13“ am Anfang des Plans.
- Spec: `docs/superpowers/specs/2026-10-03-stufe-4a-bewegungen-design.md` (mit dem Nutzer abgestimmt; bei der Planung
  nachgezogen: §4.2, §11.2, §12).

## Stand
- `main` steht auf `9a6a117` (Merge PR #9, Aufräumen nach 3b). Unit-Tests auf `main`: **622 passed, 109 deselected**.
- Branch `plan-stufe-4a` (von `main`, lokal, **nicht gepusht**): Spec, Plan, diese Übergabe; CLAUDE.md verweist hierher.
- **Plan-Code vorab geprüft (ohne SolidWorks):** Tasks 2–5 ganz, Task 6 Steps 1–9, Task 7 Steps 1–6, Task 8 Steps 1–8 im
  Wegwerf-Worktree eingespielt. RED-Fehlerbilder wie im Plan, `swki api pruefe-code` ohne Befund. Gefunden und im Plan
  korrigiert: die Anlagefläche `anlage_b` des Scharniers gehört zum Gegenstück, nicht zur Komponente von `b`
  (Task 3), dazu zwei Zählfehler. Soll nach Task 10: **696 passed, 116 deselected**.
- **Nicht vorab gelaufen:** alles mit SolidWorks – Spike S13 (Task 1), die SolidWorks-Schicht live (Task 6/7), Referenz
  Linearschlitten (Task 8), Negativfälle (Task 9), Regression (Task 10).

## Nutzerentscheidungen (2026-10-03, Brainstorming)
- Stufe 4 geteilt: **4a** Bewegungen, Grenzverknüpfungen, Scharnier, gezählte Freiheitsgrade, Bewegungsprüfung; **4b**
  mechanische Kopplungen (Zahnrad, Nut, Kurve; Kandidat Referenz *Schieber mit Schrägbolzen*).
- Referenz: **Linearschlitten mit Schwenkhebel** (allgemeine Konstruktion, kein Werkzeugbau).
- **Antrieb nur während der Prüfung:** das gebaute Modell ist innerhalb der Grenzen ziehbar und in Grundstellung
  gespeichert; `swki pruefen` legt treibende Verknüpfungen vorübergehend an und schließt ohne Speichern.
- Freigabe: `bewegungen` und gezählte `freiheitsgrade` sind Anforderung; Grenzwerte müssen Parameter sein; eine Bewegung
  läuft über den ganzen Bereich ihrer Grenze.
- Prüfung je Bewegung: automatisch Kollision je Schritt, „Grenze wirkt“, „Freiheitsgrad belegt“; ausdrücklich Endlagen.
- Kombination: **Paarläufe nur für Bewegungen mit sich schneidenden Räumen** (Nutzerfrage zur Förderstation mit 6–10
  bewegten Komponenten: „alle Ecken“ wüchse mit 2^(n−1) und skaliert nicht).
- Bilder: je Bewegung `min`/Mitte/`max` (Iso) plus ein Bild je Bewegungskollision.
- Vier Negativfälle; Architektur: Bewegungsprüfung in `swki pruefen` mit Speicherabbruch `SPEICHER_KNAPP`.

## Abweichungen des Planers (dem Nutzer am 2026-10-04 gemeldet, Spec nachgezogen)
- Scharnier = `konzentrisch` (ohne Drehsperre) + `deckungsgleich` der Anlage (`<id>.anlage`), kein SolidWorks-Scharnier.
- Negativfall 1 erwartet beide Paarlauf-Kollisionen; Fall 3 legt die Grenze an die Gegenseite (+x); Fall 4 lässt die
  seitliche Führung des Schlittens weg (`{freiheitsgrad:schlitten}`).
- Beim Abschluss erneut melden (Präzisierungen 1 und 13 des Plans).

## Vorgaben des Nutzers
- Eigener Branch `stufe-4a`, angelegt von `plan-stufe-4a`. Am Ende ein Pull Request; **vor Push und Merge fragen**.
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; die Subagents ausdrücklich darauf
  anweisen.
- Kommunikation auf Deutsch. Fragen einzeln stellen, jede mit einer Empfehlung.
- **SolidWorks-Neustarts übernimmt der Controller selbst** (Ablauf unten).

## Vor dem Start prüfen
- `git status` sauber (`auftraege/` ist ignoriert), `.venv\Scripts\python.exe -m pytest -q` → 622 passed, 109 deselected.
- `.superpowers/` ist lokal über `.git/info/exclude` ignoriert. SDD-Workspace über das Skript `sdd-workspace` des Skills.
- SOLIDWORKS 2025, **genau eine Instanz** (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`), keine Dokumente offen,
  Toggle 10 / Integer 6 = `False 1`.

## Ablauf mit Stopps
- **Task 1 (Spike S13, live):** Der Implementer wertet nur aus. Der **Controller** entscheidet je Zeile der Tabelle
  „Abhängigkeiten vom Spike S13“ (Annahme bestätigt oder Spalte „sonst“) und schreibt jede Entscheidung als Ruling in den
  Ledger, bevor Task 2 beginnt. Abweichungen, die Plan-Code ändern (z. B. `GRENZ_MASSE`, Drehsinn → Endlagen-Achse und
  Anschlag, Status der Mitfahrer → Negativfall 4, `bewegung_schritte`/`speicher_grenze_mb`), in die Dispatches der
  betroffenen Tasks mitgeben.
- **Tasks 2–5:** ohne SolidWorks, Plan-Code vollständig und vorab grün → günstiges Modell für die Implementer, mittleres
  für Reviews.
- **Tasks 6–7 (live):** ein Implementer, Live-Tests einzeln; ab ca. 3 GB Private Bytes BLOCKED → Neustart durch den
  Controller → per SendMessage fortsetzen.
- **Task 8:** Implementer bis Commit, dann Controller-Schritt 11 (Auftrag `auftraege/REF-schlitten/`, Prüfer-Agent,
  Urteil, danach Auftrag und Arbeitsordner löschen).
- **Task 9:** vier Negativfälle, je ein frisches SolidWorks. Weicht eine Mängelmenge ab: Erwartung nicht abschwächen,
  der Controller entscheidet.
- **Task 10:** Doku und Regression (5 Referenzen + 3b-Probe, frisches SolidWorks vor Stehlager und Schlitten); danach
  Gesamt-Review (stärkstes Modell), eine Fix-Welle, Abschluss per `superpowers:finishing-a-development-branch`.

## SolidWorks-Neustart durch den Controller (bewährt in 3b und im Aufräumen)
1. Genau eine Instanz prüfen (`tasklist`), per COM `GetDocumentCount` = 0 prüfen (sonst nicht neu starten, sondern klären).
2. `ExitApp` per COM (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); app.ExitApp()"`).
3. Warten, bis kein `SLDWORKS.exe` mehr läuft.
4. Start über `installationsordner` aus `config/rechner.yaml`: `Start-Process "<installationsordner>\SLDWORKS.exe"`.
5. Pollen, bis COM erreichbar und `app.Visible` true ist; dann eine Instanz und `False 1` bestätigen.

Bewährt hat sich ein PowerShell-Skript im Scratchpad, das die fünf Schritte ausführt (Abbruch bei ≠ 1 Instanz oder offenen
Dokumenten; Warten auf Ende mit Zeitlimit; Start; Pollen auf `Visible`; Ausgabe von Instanzen, Private Bytes und
Einstellungen). **Windows PowerShell 5.1 liest Skripte ohne BOM als ANSI: im Skript nur ASCII verwenden** (keine
Umlaute, kein Gedankenstrich), sonst Parserfehler.

## Erfahrungen (wichtig für die Live-Tasks)
- **Speicher:** Private Bytes messen, nicht das Working Set. Ein Stehlager-Lauf (Bau + Prüfen) kostet 3,0–3,8 GB, die
  3b-Probe-Baugruppe 0,5–0,9 GB. Die Bewegungsprüfung kommt dazu – wie viel je Schritt, misst Spike S13 Zeile 8.
- **Nie zwei Implementer gleichzeitig**, solange SolidWorks läuft. Reviewer und Doku-Implementer können parallel zu
  Live-Läufen arbeiten.
- `GetPathName` liefert bei selbst gebauten Teilen `.SLDPRT` groß – Dateinamen schreibungsunabhängig vergleichen.
- Der Implementer hält vor jedem Referenz- und Negativlauf an (BLOCKED Neustart); der Controller startet neu und schreibt
  „frisch neu gestartet“ mit PID, Private Bytes und Einstellungen in die Fortsetzungsnachricht.

## Dem Nutzer bei der Übergabe am Ende melden
- Testzahlen (Soll 696 passed, 116 deselected), Spike-S13-Ergebnisse und Entscheidungen, Live-Ergebnisse (Referenz,
  Negativfälle, Regression, Zeit und Speicher je Bewegungsschritt), Abweichungen vom Plan.
- Nächste Schritte zur Wahl: Stufe 4b (Kopplungen) oder Paket „Messarten“.
