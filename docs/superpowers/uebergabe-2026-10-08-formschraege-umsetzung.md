# Übergabe: Umsetzung Paket Formschräge (Stand 2026-10-08)

## Auftrag der nächsten Sitzung
Plan **Paket Formschräge** mit **superpowers:subagent-driven-development** umsetzen: ein Implementer-Agent pro Task, Review
nach jedem Task, Gesamt-Review am Ende.

- Plan: `docs/superpowers/plans/2026-10-07-formschraege.md` (8 Tasks). Bindend sind die „Präzisierungen“ (11), die
  „Global Constraints“, der „Review Focus“ und die Tabelle „Abhängigkeiten vom Spike S16“ am Anfang.
- Spec: `docs/superpowers/specs/2026-10-07-formschraege-design.md` (mit dem Nutzer abgestimmt; bei der Planung
  nachgezogen: §4, §6.1, §6.3).

## Stand
- `main` steht auf `d9016a9` (Merge PR #13, Stufe 3c). Unit-Tests auf `main`: **960 passed, 141 deselected**.
- Branch `plan-formschraege` (von `main`, lokal, **nicht gepusht**): Spec, Plan, Spec-Nachzug, diese Übergabe; CLAUDE.md
  verweist hierher.
- **Plan-Code vorab geprüft (ohne SolidWorks):** alle 8 Tasks in einem frischen Wegwerf-Worktree mechanisch aus dem Plan
  eingespielt (Tests zuerst mit RED-Lauf, dann Umsetzung, GREEN-Lauf, ganze Suite, `swki api pruefe-code swki spikes
  tests/live`). Jede Ersetzung traf genau einmal; das Ergebnis stimmt Datei für Datei mit dem Entwicklungsstand überein
  (bis auf Zeilenenden). Testzahlen je Task stehen im Plan; Soll nach Task 8: **1021 passed, 152 deselected**. Die
  Referenz-Spec validiert ohne Befund und ohne Hinweis; das Sollvolumen 315014,796 mm³ ist unabhängig gerechnet und gegen
  `swki.formschraege` gegengeprüft.
- **Nicht vorab gelaufen:** alles mit SolidWorks – Spike S16 (Task 5), Live-Tests der Minimalteile (Task 6), Referenz,
  Prüfer und Negativfälle (Task 7), Regression (Task 8). Unsicherste Annahmen: Zuordnung `Ddir1` ↔ `kleiner`
  (`DDIR_KLEINER`, Spike-Zeile 1), Name des Winkelmaßes je Endbedingung (`WINKEL_MASS`, Zeile 4), Normale aus
  `EvaluateAtPoint`/`FaceInSurfaceSense` (Zeile 5).

## Nutzerentscheidungen (2026-10-07, Brainstorming)
- **Nur Option an `extrusion`/`schnitt`** (Formschräge beim Extrudieren). Ein eigenes Feature `formschraege`
  (`InsertMultiFaceDraft`) kommt erst, wenn es gebraucht wird.
- **Zweck: Gestaltungselement** (konischer Zapfen, Einführschräge, Trichter, verjüngter Steg) – keine Entformungsschräge,
  keine Mindestschräge, Winkel frei in (0°, 90°).
- Richtung über den **Querschnitt von der Skizze weg** (`kleiner`/`groesser`), Winkel als Parameter (vom Planer auf Wunsch
  des Nutzers selbst entschieden: „richte dich nach der bisherigen Vorgehensweise, nur echte Rückfragen“).
- Referenz **Zentrieraufnahme** (Zapfen, Einführtasche, Trichter-Durchbruch, Steg `mittig`). **Den Trichter braucht der
  Nutzer im nächsten Projekt** – auf dessen Ergebnis (Volumen, Winkel, Bild) im Abschlussbericht besonders eingehen.

## Abweichungen des Planers (dem Nutzer bei der Übergabe melden, Spec nachgezogen)
- Messung einheitlich für alle Flächenarten (Punkt und Normale je Fläche); die Kategorie „nicht messbar“ entfällt.
- Winkelmaß je Endbedingung (`D2` bzw. `D1` ohne Tiefenmaß) statt eines festen Namens.
- Kein eigener Bericht-Abschnitt; `formschraegen` steht wie `normbohrungen` unter den Prüfungen, mit `gemessen`.
- Negativfälle verfälschen über `monkeypatch` des Namens `schraege` im Handler (sonst stellt die Gleichung den Winkel beim
  Rebuild zurück); erwartete Mängelmenge je Fall `{formschraegen, volumen}`.
- Die Referenz bekommt `eingabe/beschreibung.md` als Eingabe für den Prüfer.

## Vorgaben des Nutzers
- Eigener Branch `formschraege`, angelegt von `plan-formschraege`. Am Ende ein Pull Request; **vor Push und Merge fragen**.
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; die Subagents ausdrücklich darauf
  anweisen.
- Kommunikation auf Deutsch. Fragen einzeln stellen, jede mit einer Empfehlung; nur fragen, was sich nicht aus Plan,
  Spec und bisheriger Vorgehensweise klären lässt.
- **SolidWorks-Neustarts übernimmt der Controller selbst** (Ablauf unten). **Keine künstliche CPU-Last ohne Rückfrage.**
- Ausrichtung: allgemeine Konstruktion, kein Werkzeugbau.

## Vor dem Start prüfen
- `git status` sauber (`auftraege/` ist ignoriert), `.venv\Scripts\python.exe -m pytest -q` → 960 passed, 141 deselected.
- `.superpowers/` ist lokal über `.git/info/exclude` ignoriert. SDD-Workspace über das Skript `sdd-workspace` des Skills.
- SOLIDWORKS 2025, **genau eine Instanz** (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`), keine Dokumente offen,
  Toggle 10 / Integer 6 = `False 1`.

## Ablauf mit Stopps
- **Tasks 1–4:** ohne SolidWorks, Plan-Code vollständig und vorab grün → günstiges Modell für die Implementer, mittleres
  für Reviews.
- **Task 5 (Spike S16, live):** Der Implementer schreibt und startet den Spike und wertet nur aus. Der **Controller**
  entscheidet je Zeile der Tabelle „Abhängigkeiten vom Spike S16“ und schreibt jede Entscheidung als Ruling in den Ledger,
  bevor Task 6 beginnt. Code-Nachzüge (z. B. `DDIR_KLEINER`, `WINKEL_MASS`, `punkt_und_normale`) als eigenen kleinen
  Fix-Auftrag mit Test vor Task 6 vergeben. Führt eine Zeile zu „Nutzer fragen/informieren“ (Zeile 1 Volumen, 2 und 3
  Ablehnung in `validieren`, 4 Gleichung): **Nutzer einbeziehen**.
- **Task 6 (live):** ein Implementer, Live-Tests einzeln über `tests\live_einzeln.py`. Nur Teile: bis ca. 4 GB Private Bytes
  in einer Sitzung, sonst BLOCKED → Neustart → per SendMessage fortsetzen.
- **Task 7 (live):** Referenz; Prüfer-Urteil durch den Controller (Auftrag `auftraege/REF-FS-ZENTRIERAUFNAHME/`, danach
  löschen); Negativfälle einzeln. Weicht eine Mängelmenge ab: Erwartung nicht abschwächen, der Controller entscheidet.
- **Task 8:** Doku, Regressions-Suite (Teile gemeinsam, Baugruppen-Referenzen je Test frisch: *Stehlager*,
  *Linearschlitten*, *Zahnstangentrieb*, *Motorhalter*), Ergebnisse; danach Gesamt-Review (stärkstes Modell), eine
  Fix-Welle, Abschluss per `superpowers:finishing-a-development-branch`.
- *Motorhalter* braucht die Herstellerdatei Nanotec GPLE60-2S-32 im Quellordner der `kaufteilbibliothek`; fehlt sie,
  meldet die Regression `KAUFTEIL_QUELLE_FEHLT` mit Download-URL → Nutzer fragen (CLAUDE.md, Kaufteile).

## SolidWorks-Neustart durch den Controller (bewährt in 3b–3c)
1. Genau eine Instanz prüfen (`tasklist`), per COM `GetDocumentCount` = 0 prüfen (sonst nicht neu starten, sondern klären).
2. `ExitApp` per COM (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); app.ExitApp()"`).
3. Warten, bis kein `SLDWORKS.exe` mehr läuft.
4. Start über `installationsordner` aus `config/rechner.yaml`: `Start-Process "<installationsordner>\SLDWORKS.exe"`.
5. Pollen, bis COM erreichbar und `app.Visible` true ist; dann eine Instanz und `False 1` bestätigen.

PowerShell-Skript im Scratchpad: **nur ASCII** (Windows PowerShell 5.1 liest Skripte ohne BOM als ANSI).

## Erfahrungen (wichtig für die Live-Tasks)
- **Speicher:** Private Bytes messen, nicht das Working Set. Teile 3–4 GB Spitze; der Spike baut 17 kleine Teile
  nacheinander – Private Bytes vorher und nachher notieren, über ca. 4 GB vor Task 6 neu starten.
- **Gleichungen:** Maße, die per Gleichung an Parameter gebunden sind, stellt ein Rebuild auf den Parameter zurück –
  Verfälschungen im Bau deshalb immer über die Spec-Werte, die der Handler liest (Präzisierung 8).
- **API:** vor jedem neuen Aufruf `swki api methode`/`enum`; Late Binding: nullargumentige Member ohne `()`
  (`FaceInSurfaceSense`, `IsCone`, `ConeParams2`, `GetBox`, `GetSurface`).
- **Spikes messen, Controller entscheidet:** Abweichungen je Zeile der Tabelle mit Ruling im Ledger; Messmethoden kritisch
  prüfen (z. B. ob `abw_normale_max` wirklich Ebenen vergleicht).
- **Nie zwei Implementer gleichzeitig**, solange SolidWorks läuft. Reviewer und Doku-Implementer können parallel arbeiten.
- **Modellwahl:** Abschrift mit vollständigem Code günstiges Modell, Live-Tasks und Reviews mittleres, Gesamt-Review
  stärkstes Modell.

## Dem Nutzer bei der Übergabe am Ende melden
- Testzahlen (Soll 1021 passed, 152 deselected), Spike-Ergebnisse S16 und Entscheidungen, Live-Ergebnisse (Minimalteile,
  Referenz Zentrieraufnahme mit Prüfer-Urteil, Negativfälle, Regression, Zeit und Speicher), **Ergebnis des Trichters**,
  Abweichungen vom Plan (Präzisierungen und alle Rulings).
- Nächste Schritte zur Wahl: Stufe 4c (Nut, Kurve), Paket „Messarten“, Paket Speicher; eigenes Feature `formschraege` bei
  Bedarf.
