# Übergabe: Umsetzung Stufe 4b – Verzahnung und Kopplungen (Stand 2026-10-05)

## Auftrag der nächsten Sitzung
Plan **Stufe 4b** mit **superpowers:subagent-driven-development** umsetzen: ein Implementer-Agent pro Task, Review nach
jedem Task, Gesamt-Review am Ende.

- Plan: `docs/superpowers/plans/2026-10-05-stufe-4b-verzahnung-kopplungen.md` (15 Tasks in zwei Etappen). Bindend sind die
  „Präzisierungen“ (22), die „Global Constraints“ und die Tabellen „Abhängigkeiten vom Spike S14a/S14b“ am Anfang.
- Spec: `docs/superpowers/specs/2026-10-05-stufe-4b-verzahnung-kopplungen-design.md` (mit dem Nutzer abgestimmt; bei der
  Planung nachgezogen: §3, §4.2, §4.3, §4.5, §4.6, §5.4, §5.5, §8).

## Stand
- `main` steht auf `91a62f3` (Merge PR #11). Unit-Tests auf `main`: **711 passed, 117 deselected**; Live-Suite 112/112,
  Regressions-Suite 5/5 (2026-10-05).
- Branch `plan-stufe-4b` (von `main`, lokal, **nicht gepusht**): Übergabe der Planungssitzung, Spec, Plan, diese Übergabe;
  CLAUDE.md verweist hierher.
- **Plan-Code vorab geprüft (ohne SolidWorks):** alle 15 Tasks in einem frischen Wegwerf-Worktree Task für Task
  eingespielt (Tests zuerst mit RED-Lauf, dann Umsetzung, GREEN-Lauf, ganze Suite, `swki api pruefe-code swki spikes
  tests/live`). Jede Ersetzung traf genau einmal; das Ergebnis stimmt mit dem Entwicklungsstand überein. Testzahlen je Task
  stehen im Plan; Soll nach Task 15: **827 passed, 133 deselected**. Referenz-Specs und Getriebeprobe validieren ohne Befund
  und ohne Hinweis.
- **Nicht vorab gelaufen:** alles mit SolidWorks – Spikes S14a (Task 2) und S14b (Task 8), Handler und Messung live
  (Tasks 4/5), Teil-Referenzen und E1 (Task 6), Bau und Prüfen der Kopplungen live (Tasks 11/12), Referenz (Task 13),
  Negativfälle (Task 14), Regression (Task 15).

## Nutzerentscheidungen (2026-10-05, Brainstorming)
- Referenz **Zahnstangentrieb** statt *Schieber mit Schrägbolzen* (Werkzeugbau); 4b = Zahnrad + Zahnstange, **Nut und Kurve
  werden 4c**.
- **Echte Evolvente** (Bezugsprofil DIN 867, gerade Außenverzahnung + Zahnstange, Modul DIN 780 Reihe 1, ohne
  Profilverschiebung, z ≥ 17, Flankenspiel über **Zahndickenabmaß je Rad** als Parameter).
- **Eine Spec, ein Plan, zwei Etappen**; Etappe 2 beginnt erst, wenn Etappe 1 live besteht.
- Referenz-Aufbau: Linearschlitten aus 4a **ohne Hebel**, Zahnstange am Schlitten, Lagerbock, Antriebswelle (Rad z1) und
  Ritzelwelle (Rad z2 + Ritzel), eine Bewegung.
- **Sollweg je Stellung für alle Bewegungen** (schließt den offenen 4a-Punkt); Eingriff **streng** auf Kollision geprüft.
- Teilprüfung automatisch: Kopf-/Fußkreis, Zähnezahl, **Zahnweite**.
- Übersetzung **aus den Verzahnungen abgeleitet**; Endlagen der gekoppelten Wellen in der Bewegung, `validieren`
  vergleicht beide.
- Negativfälle: Zahnweite (E1), Zahnphase versetzt, Drehrichtung umgekehrt, Kopplung fehlt (`{verknuepfungen}`; dazu meldet
  `verknuepfungen` künftig unterdrückte Verknüpfungen), Übersetzung verfälscht.
- 4a-Reste mitnehmen: Bericht (Grenz-ID, Bereich, Endlagen/Sollweg), abgebrochene Läufe einheitlich `ok=None`,
  `GRENZE_REFERENZ`, privater Import. Speicherpaket und Deferred Minors bleiben eigene Pakete.

## Abweichungen des Planers (dem Nutzer bei der Übergabe melden, Spec nachgezogen)
- Zahnstange als **eine Kontur je Zahn** (eine Kontur entartet); der Rücken muss genau bis an die Fußlinie reichen.
  Teilprüfung misst bei der Zahnstange die Kopflinie statt der Zahnhöhe.
- Vereinfachter Zahnfuß: Evolvente ab `r_start = max(r_b, √(r_f² + 2·r_f·ρ_f))`, Fußrundung an der radialen Linie.
- Zusätzlicher Befund `VERZAHNUNG_GEOMETRIE`; `pi` schon in Etappe 1; Modultabelle 0,05 … 20 mm (25 … 50 gesperrt, nur eine
  Quelle).
- Zahnphase über `SetTransformAndSolve2`; Richtung als Konstante `REVERSE` je Typ (Annahme `False`, Spike S14b Zeile 6).
- Referenz: HUB 120, Zahnstange z 30, zwei Lagerböcke auf den Leisten (unverschraubt), Wellen übereinander; Minimalprobe
  „Getriebeprobe“ für Spike S14b und die Live-Tests der Tasks 11/12.

## Vorgaben des Nutzers
- Eigener Branch `stufe-4b`, angelegt von `plan-stufe-4b`. Am Ende ein Pull Request; **vor Push und Merge fragen**.
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; die Subagents ausdrücklich darauf
  anweisen.
- Kommunikation auf Deutsch. Fragen einzeln stellen, jede mit einer Empfehlung.
- **SolidWorks-Neustarts übernimmt der Controller selbst** (Ablauf unten); vor jedem Live-Lauf mit Baugruppe frisch
  starten, **je Test**.
- **Keine künstliche CPU-Last ohne Rückfrage.**
- Ausrichtung: allgemeine Konstruktion, kein Werkzeugbau.

## Vor dem Start prüfen
- `git status` sauber (`auftraege/` ist ignoriert), `.venv\Scripts\python.exe -m pytest -q` → 711 passed, 117 deselected.
- `.superpowers/` ist lokal über `.git/info/exclude` ignoriert. SDD-Workspace über das Skript `sdd-workspace` des Skills.
- SOLIDWORKS 2025, **genau eine Instanz** (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`), keine Dokumente offen,
  Toggle 10 / Integer 6 = `False 1`.

## Ablauf mit Stopps
- **Task 1, 3, 7, 9, 10:** ohne SolidWorks, Plan-Code vollständig und vorab grün → günstiges Modell für die Implementer,
  mittleres für Reviews.
- **Task 2 (Spike S14a, live):** Der Implementer wertet nur aus. Der **Controller** entscheidet je Zeile der Tabelle
  „Abhängigkeiten vom Spike S14a“ und schreibt jede Entscheidung als Ruling in den Ledger, bevor Task 4 beginnt (Task 3
  hängt nicht vom Spike ab und darf vorher laufen). Plan-Code-Änderungen (z. B. Polylinie, `verzahnung_mm`) in die
  Dispatches der Tasks 4/5 mitgeben.
- **Tasks 4–6 (live):** ein Implementer, Live-Tests einzeln; Teile bis ca. 4 GB Private Bytes in einer Sitzung, sonst
  BLOCKED → Neustart → per SendMessage fortsetzen. Task 6: Prüfer-Urteile der drei Teil-Referenzen durch den Controller.
  **Etappe 1 abgeschlossen** erst nach Task 6 Steps 5–8 – Ledger-Eintrag, dann Task 7.
- **Task 8 (Spike S14b, live):** wie Task 2; Rulings zu den Zeilen 6–13 vor Task 11. Weicht Zeile 9 (Scheinkollision im
  Eingriff, Zeit/Speicher) oder 13 (Datei nach Speichern unbrauchbar) ab: **Nutzer fragen**.
- **Tasks 11–12 (live):** Getriebeprobe je Test auf frischem SolidWorks.
- **Task 13:** Referenz live, dann Prüfer-Urteil durch den Controller (Auftrag `auftraege/REF-4B-TRIEB/`, danach löschen).
  `SPEICHER_KNAPP` auch auf frischem SolidWorks: Nutzer fragen (keine stille Anhebung von `speicher_grenze_mb`).
- **Task 14:** vier Negativfälle, je ein frisches SolidWorks. Weicht eine Mängelmenge ab: Erwartung nicht abschwächen, der
  Controller entscheidet (Muster 4a).
- **Task 15:** Doku und Regression (Teile gemeinsam, Baugruppen je frisch, dazu die vier Schlitten-Negativfälle mit dem
  neuen Sollweg); danach Gesamt-Review (stärkstes Modell), eine Fix-Welle, Abschluss per
  `superpowers:finishing-a-development-branch`.

## SolidWorks-Neustart durch den Controller (bewährt in 3b und 4a)
1. Genau eine Instanz prüfen (`tasklist`), per COM `GetDocumentCount` = 0 prüfen (sonst nicht neu starten, sondern klären).
2. `ExitApp` per COM (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); app.ExitApp()"`).
3. Warten, bis kein `SLDWORKS.exe` mehr läuft.
4. Start über `installationsordner` aus `config/rechner.yaml`: `Start-Process "<installationsordner>\SLDWORKS.exe"`.
5. Pollen, bis COM erreichbar und `app.Visible` true ist; dann eine Instanz und `False 1` bestätigen.

PowerShell-Skript im Scratchpad: **nur ASCII** (Windows PowerShell 5.1 liest Skripte ohne BOM als ANSI).

## Erfahrungen (wichtig für die Live-Tasks)
- **Speicher:** Private Bytes messen, nicht das Working Set; Baugruppenläufe mit Bewegungen 7–11 GB Spitze (Stehlager
  10,8 GB, Schlitten 9,9–10,2 GB). Der Zahnstangentrieb hat mehr Eigenteile (7 Specs) – Spitzen mit 0,5-s-Abtastung messen
  und in den Ergebnissen festhalten.
- **Neustart je Bewegungslauf:** zwei Bewegungs-Negativfälle nacheinander in einer Sitzung scheiterten in 4a; je Test frisch.
- **Sporadische Fehler:** Schleife „Neustart + n × `swki bauen`“ mit Diagnose nur im Fehlerzweig (Werkzeuge in
  `auftraege/REPRO-NB/diagnose/`, gitignored); keine künstliche CPU-Last ohne Rückfrage.
- **API:** vor jedem neuen Aufruf `swki api methode`/`enum`; Late Binding: nullargumentige Member ohne `()`.
- **Nie zwei Implementer gleichzeitig**, solange SolidWorks läuft. Reviewer und Doku-Implementer können parallel arbeiten.
- **Modellwahl:** Abschrift mit vollständigem Code günstiges/mittleres Modell, Live-Tasks und Reviews mittleres,
  Gesamt-Review stärkstes Modell.

## Dem Nutzer bei der Übergabe am Ende melden
- Testzahlen (Soll 827 passed, 133 deselected), Spike-Ergebnisse S14a/S14b und Entscheidungen, Live-Ergebnisse (Teil-
  Referenzen, Zahnstangentrieb, fünf Negativfälle, Regression einschließlich Schlitten-Negativfälle mit Sollweg, Zeit und
  Speicher), Abweichungen vom Plan (Präzisierungen 3, 4, 7, 9, 15–17 und alle Rulings).
- Nächste Schritte zur Wahl: Stufe 4c (Nut, Kurve), Paket „Messarten“, Paket Speicher.
