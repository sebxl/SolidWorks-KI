# Übergabe: Aufräum-Paket nach Stufe 3b (Stand 2026-10-03)

## Auftrag der nächsten Sitzung
Plan **Aufräumen nach 3b** mit **superpowers:subagent-driven-development** umsetzen: ein Implementer-Agent pro Task, Review
nach jedem Task, Gesamt-Review am Ende.

- Plan: `docs/superpowers/plans/2026-10-03-aufraeumen-nach-3b.md` (7 Tasks). Bindend sind die „Nutzerentscheidungen“ und die
  „Global Constraints“ am Anfang des Plans.
- Grundlage: Spec 3b `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md`, Ergebnisse
  `docs/stufe3b/ergebnisse.md` (Abschnitt „Offene Punkte“).

## Stand
- `main` steht auf `b3be4a1` (Merge PR #8, Stufe 3b). Unit-Tests auf `main`: **607 passed, 108 deselected**; Regression
  live 22/22; Stehlager bestanden (Code-Prüfungen und Prüfer).
- Branch `plan-aufraeumen-3b` (von `main`, lokal, **nicht gepusht**): Plan und diese Übergabe; CLAUDE.md verweist hierher.
- **Plan-Code vorab geprüft (ohne SolidWorks):** Tasks 1–5 wurden in einem Wegwerf-Worktree eingespielt (Ergebnis siehe
  Abschnitt „Vorabprüfung“ unten). Task 6 (live) und Task 7 (Doku) sind nicht vorab gelaufen.

## Nutzerentscheidungen (2026-10-03)
- Offene Punkte aus 3b in Töpfe sortiert: **A** jetzt als Aufräum-Paket (dieser Plan), **B** später als eigenes Paket
  „Messarten“ (Fasen `c`/`p`, Volumen bei Gewinde `durch`, Achshöhe der Lagerbohrung), **C** liegen lassen (doppelter
  Code, Docstrings, Testlücken ohne Verhaltensrisiko, Commit-Message `b7ef5a6`, Rechner B, Speichergrenze im Compiler),
  **D** Stufe 4.
- Spec 3b wird nachgezogen (§4.4, §11, §12) – freigegeben.

## Vorgaben des Nutzers
- Eigener Branch `aufraeumen-3b`, angelegt von `plan-aufraeumen-3b`. Am Ende ein Pull Request; **vor Push und Merge fragen**.
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; die Subagents ausdrücklich darauf anweisen.
- Kommunikation auf Deutsch. Fragen einzeln stellen, jede mit einer Empfehlung.
- **SolidWorks-Neustarts übernimmt der Controller selbst** (Ablauf unten).

## Vor dem Start mit dem Nutzer klären (eine Frage je Runde, mit Empfehlung)
1. **`auftraege/` ins `.gitignore`?** Heute sind dort nur SolidWorks-Dateien ignoriert; Auftragsordner tauchen als
   untracked auf. Empfehlung: ja, `auftraege/` ganz ignorieren – Aufträge sind Arbeitsstände, die Referenzen liegen in
   `tests/referenz/`. (Wenn ja: als kleiner Commit in Task 7 mitnehmen.)
2. **Testauftrag `auftraege/REF-stehlager/` löschen?** Er war der Beleg für das Prüfer-Urteil in 3b (Ergebnis steht in
   `docs/stufe3b/ergebnisse.md`). Empfehlung: löschen, wie nach 2c die REF-*-Aufträge; die Lauf-Dateien unter
   `%USERPROFILE%\.swki\arbeit\REF-stehlager\` gleich mit.

## Vor dem Start prüfen
- `git status` sauber (bis auf `auftraege/`), `.venv\Scripts\python.exe -m pytest -q` → 607 passed, 108 deselected.
- `.superpowers/` ist lokal über `.git/info/exclude` ignoriert. SDD-Workspace über das Skript `sdd-workspace` des Skills.
- **Mit SolidWorks:** nur Task 6. SOLIDWORKS 2025, **genau eine Instanz** (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`),
  Toggle 10 / Integer 6 = `False 1`.
- **Ohne SolidWorks:** Tasks 1–5 und 7.

## Ablauf mit Stopps
- Tasks 1–5: reine Python-Tasks, Plan-Code vollständig (Abschrift → günstiges bis mittleres Modell; Reviews mittleres Modell).
- **Task 6 (live):** Der Implementer lässt jeden Test einzeln laufen (`tests\live_einzeln.py <datei>::<test> --zeit 600`) und
  hält ab ca. 3 GB Private Bytes vor dem nächsten Test an (BLOCKED Speicher). Der Controller startet neu und setzt den
  Implementer per SendMessage fort. Rechne mit etwa 5–6 Neustarts (Stehlager-Referenz und je Negativfall ein frisches
  SolidWorks). Weicht die Mängelmenge eines Negativfalls ab: Erwartung nicht abschwächen, der Controller entscheidet.
- Task 7: Doku; danach Gesamt-Review (stärkstes Modell), eine Fix-Welle, Abschluss per
  `superpowers:finishing-a-development-branch` (Push/PR nur nach Rückfrage).

## SolidWorks-Neustart durch den Controller (bewährt in 3b)
1. Genau eine Instanz prüfen (`tasklist`), per COM `GetDocumentCount` = 0 prüfen (sonst nicht neu starten, sondern klären).
2. `ExitApp` per COM (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); app.ExitApp()"`).
3. Warten, bis kein `SLDWORKS.exe` mehr läuft (Monitor/until-Schleife, kein langes `sleep`).
4. Start über `installationsordner` aus `config/rechner.yaml`: `Start-Process "<installationsordner>\SLDWORKS.exe"`.
5. Pollen, bis COM erreichbar und `app.Visible` true ist (direkt nach dem Start kann `Visible` kurz `False` melden –
   erneut prüfen); dann eine Instanz und `False 1` bestätigen. Das MCP `solidworks-mcp` kann beim Neustart eine zweite,
   fensterlose Instanz starten – Instanzen danach zählen.

## Erfahrungen aus 3b (wichtig für Task 6)
- **Speicher:** Private Bytes messen, nicht das Working Set. Ein Stehlager-Lauf (Bau + Prüfen) kostet 3,1–3,6 GB, eine
  kleine Probe-Baugruppe 0,5–0,9 GB, ein Teil 80–160 MB.
- **Nie zwei Implementer gleichzeitig**, solange SolidWorks läuft. Ein Implementer, der wegen Speicher anhält, wird nach
  dem Neustart per SendMessage fortgesetzt.
- Reviewer können parallel zu Live-Läufen arbeiten (sie brauchen kein SolidWorks).
- `GetPathName` liefert bei selbst gebauten Teilen `.SLDPRT` groß – Dateinamen schreibungsunabhängig vergleichen.

## Dem Nutzer bei der Übergabe am Ende melden
- Testzahlen (Soll 618 passed, 109 deselected), Live-Ergebnisse von Task 6, Abweichungen vom Plan.
- Was aus Topf A erledigt ist; Topf B (Messarten) und Stufe 4 als nächste Schritte zur Wahl.

## Vorabprüfung des Plan-Codes
Tasks 1–5 im Wegwerf-Worktree auf `main` eingespielt (2026-10-03): RED/GREEN je Task wie im Plan beschrieben,
Testzahlen 608 → 610 → 612 → 615 → 618 passed (108 deselected unverändert), `swki api pruefe-code` ohne Befund, CRLF
erhalten. Drei Textstellen des Plans danach korrigiert (Fehlerbild in Task 4 Step 2, Zitat §12 und CLAUDE.md-Zeile in
Task 7). Für Task 6/7 geprüft: alle genannten Test-Helfer, Test-IDs und Spec-/Ergebnis-Textstellen existieren.
