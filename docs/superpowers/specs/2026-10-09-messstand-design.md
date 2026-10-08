# Messstand: KPI-Messung der KI-Konstruktion und Optimierungsschleife

Stand 09.10.2026, Branch `messstand`. Auftrag des Nutzers: Test mit allen relevanten KPI ausarbeiten, mit dem aktuellen
Stand laufen lassen (Baseline), umbauen (zuerst mit `ezdxf`, `numpy`, `trimesh`), erneut messen. Deutlich besser → neue
Baseline, sonst verwerfen und neu überlegen. Ziel Score 7/10, höchstens 5 Umbau-Durchläufe. Der Nutzer hat alle
Festlegungen an Claude übergeben („Du entscheidest“) und den Baseline-Score auf **2/10** gesetzt. Eine einfache
Konstruktion muss **4× schneller** werden.

## 1. Was gemessen wird

Ein **Lauf** = ein frischer Konstruktions-Agent (Subagent `claude`, nicht verschachtelt in eine laufende Konstruktion)
bekommt eine Aufgabe (Text + Eingabedateien) und arbeitet sie mit den Skills `konstruieren` / `baugruppe` bis zum
bestandenen Prüfer und `swki bericht` ab – so wie im echten Betrieb, nur ohne Nutzer.

Ein **Durchgang** = alle Läufe eines Code-Stands (Baseline oder Umbau n).

### 1.1 Aufgaben (5 Läufe je Durchgang)

| ID | Aufgabe | Eingabe | Referenz (nur für die Bewertung) |
|---|---|---|---|
| `durchlicht` (2×) | Ersatzkörper Durchlicht AI BL-S050075 | Maßbild PNG + Aufgabentext | `AP68-Pruefstation` Lauf 8 (Prüfer bestanden) |
| `kamera` | Ersatzkörper Kamera Basler a2A2590 | Maßbild PNG + Aufgabentext | `AP68-Pruefstation` Kamera Lauf 5 |
| `zentrieraufnahme` | Platte mit vier Formschrägen | `beschreibung.md` | `tests/referenz/zentrieraufnahme` |
| `stehlager` | Baugruppe mit 3 Teilen + Normteilen | `beschreibung.md` | `tests/referenz/stehlager` |

Der Aufgabentext enthält die Entscheidungen, die der Nutzer damals im Dialog getroffen hat (Annahmen, Vereinfachungen,
Koordinaten), aber **nicht** die Deutung der Zeichnung (z. B. auf welcher Seite der Stecker sitzt). Die Fallen bleiben.

### 1.2 Isolation

- Je Lauf ein frischer `git worktree` des zu messenden Commits unter `<arbeitsordner>/MESSSTAND/wt/<lauf>`;
  `.venv` als Junction, `config/rechner.yaml` kopiert. Im Worktree werden die Referenz-Specs der Aufgaben gelöscht
  (`tests/referenz/zentrieraufnahme/`, `tests/referenz/stehlager/*.yaml`). `auftraege/` ist nicht im Git, die
  AP-6.8-Specs fehlen dort ohnehin.
- Auftragsordner im Worktree: `auftraege/MESS-<durchgang>-<aufgabe>-<n>/` (eindeutig, damit `<arbeitsordner>/<auftrag>`
  nicht kollidiert).
- **Leck-Prüfung:** Liest der Agent Pfade aus `SolidWorks-KI\auftraege\AP68-Pruefstation`,
  `.swki\arbeit\AP68-Pruefstation`, `tests\referenz\zentrieraufnahme`, `tests\referenz\stehlager` oder
  `MESSSTAND\referenz` des Hauptrepos, ist der Lauf ungültig und wird wiederholt.
- Vor jedem Lauf SolidWorks frisch starten (`werkzeuge.sw_neustart`).

### 1.3 Freigabe

Der Nutzer hat am 09.10.2026 die Freigabe **nur für Messstand-Aufträge** (`auftraege/MESS-*` im Messstand-Worktree)
erteilt. Der Agent gibt dort ohne Rückfrage frei; jede weitere Freigabe zählt als Fehler („Nutzerrunde“). Rückfragen
stellt der Agent nicht, er dokumentiert Annahmen in der Spec.

## 2. KPI je Lauf

Quelle: Transkript des Agenten und seiner Subagenten (`…/subagents/agent-<id>.jsonl`, Zeitstempel und `usage` je
Eintrag), Protokolle des Auftrags, Speicherabtastung.

| KPI | Definition |
|---|---|
| `zeit_s` | erster bis letzter Zeitstempel des Agenten-Transkripts (Wanduhr, inkl. Subagenten) |
| `zeit_anteile` | Tool-Dauer je Kategorie: `bauen`, `pruefen`, `validieren`, `freigeben`, `swki_sonst`, `pruefer` (Agent-Tool), `lesen` (Read/Grep/Glob), `schreiben` (Write/Edit), `sonst`; Rest = `modell` (Denken/Generieren) |
| `tool_aufrufe` | Anzahl `tool_use` im Agenten und allen Subagenten, je Werkzeug |
| `tokens` | Summe `usage` (input, cache_creation, cache_read, output) über alle Transkripte; `tokens_gewichtet` = input + 1,25·cache_creation + 0,1·cache_read + 5·output |
| `laeufe` | Anzahl `swki bauen` |
| `bauabbrueche` | `swki bauen` mit `status: fehler` |
| `pruefmaengel` | Summe der nicht bestandenen Prüfungen über alle geprüften Läufe |
| `pruefer_maengel` | Prüfer-Urteile mit Mängeln (Anzahl Mängel) |
| `freigaben` | erfolgreiche `swki freigeben` |
| `speicher_spitze_mb` | max. Private Bytes von `SLDWORKS.exe` (Abtastung 0,5 s) |
| `sw_neustarts` | Wechsel der SolidWorks-PID während des Laufs |
| `bestanden` | letzter Prüfer bestanden und `swki status` = `bestanden` |
| `richtig` | Ergebnis stimmt mit der Referenz überein (§3) |

## 3. Richtigkeit gegen die Referenz

- Ergebnis und Referenz werden als STL exportiert (fein, binär, mm, nicht in den positiven Raum verschoben;
  Baugruppen in eine Datei).
- Vergleich (numpy/scipy/trimesh): für jede der 24 eigentlichen Drehungen der Achsen (det = +1) Schwerpunkte
  übereinander, dann Oberflächenabstand beidseitig (Punktstichprobe → nächster Punkt der anderen Oberfläche).
  Beste Drehung zählt.
- `richtig` = Volumen ±0,5 %, Hüllquader-Kanten ±0,3 mm (sortiert nach Drehung), p99 des Oberflächenabstands ≤ 0,3 mm und
  größter Abstand ≤ 1,0 mm (festgelegt vor der ersten Bewertung: p99 allein übersieht eine fehlende kleine Bohrung).
- `gespiegelt` = keine eigentliche Drehung passt, aber eine uneigentliche (det = −1) erfüllt die Kriterien.

## 4. Score

Je KPI-Gruppe ein Verhältnis r zur Baseline (Mittel der Verhältnisse je Aufgabe; bei Fehlern Summen über alle Läufe):

| Gruppe | Gewicht | r | Ziel (7) | Ideal (10) |
|---|---|---|---|---|
| Zeit | 50 % | `zeit_s` / Baseline | 0,25 | 0,125 |
| Aufwand | 20 % | ½·(`tool_aufrufe`/B) + ½·(`tokens_gewichtet`/B) | 0,5 | 0,25 |
| Fehler | 20 % | Σ(`bauabbrueche` + `pruefmaengel` + `pruefer_maengel` + (`freigaben` − 1)) / B | 0,5 | 0 |
| Speicher | 10 % | `speicher_spitze_mb` / B (+0,25 je Neustart oder Hänger) | 0,7 | 0,5 |

Teilscore: r = 1 → 2; zwischen 1 und Ziel linear 2 → 7; zwischen Ziel und Ideal linear 7 → 10; r ≥ 2 → 0, zwischen 1
und 2 linear 2 → 0. Ist die Baseline-Summe der Fehler 0, gilt: 0 Fehler → 7, sonst 0.
Gesamtscore = gewichtetes Mittel, auf eine Nachkommastelle.

**Sperren:** Ein Lauf ohne `bestanden` oder ohne `richtig` zählt mit `zeit_s` = 1,5 × Baseline der Aufgabe. Ist im
Durchgang eine Aufgabe nicht `richtig`, ist der Gesamtscore höchstens 4,0. Läufe mit Leck sind ungültig.

**Deutlich besser:** Gesamtscore ≥ Score der aktuellen Baseline + 1,0, kein Teilscore mehr als 1,0 schlechter und
keine zusätzliche nicht-richtige Aufgabe. Dann wird der Stand neue Baseline (Merge in `messstand`), deren Kennzahlen
bleiben aber der Bezug des Scores (Score-Anker ist immer Durchgang 0). Sonst: Branch verwerfen, `messstand` bleibt.

Abbruch: Score ≥ 7,0 oder 5 Umbau-Durchläufe.

## 5. Ablauf

1. **Messstand bauen** (`werkzeuge/messstand/`, Unit-Tests ohne SolidWorks): `vorbereiten` (Worktree, Aufgabe, SW-
   Neustart, Speicher-Abtaster starten), `abschliessen` (Abtaster stoppen, Transkript + Protokolle auswerten, STL
   exportieren, mit Referenz vergleichen, `kpi.json`), `referenz` (Referenz-STL einmalig erzeugen), `score`
   (Durchgang gegen Baseline).
2. **Durchgang 0 (Baseline)** – Ergebnis `docs/messstand/ergebnisse.md` mit Zeitanteilen: wo die Zeit hängt.
3. **Umbau n** auf Branch `messstand-umbau-<n>` (ab `messstand`): Umbau 1 nutzt `ezdxf`/`numpy`/`trimesh`; Inhalt
   folgt aus den Zeitanteilen der Baseline. Unit-Tests grün, Regressions-Teilmenge live grün.
4. **Durchgang n** messen, Score, Entscheidung nach §4, in `docs/messstand/ergebnisse.md` festhalten.

## 6. Regeln

- Während eines Laufs läuft nichts anderes mit SolidWorks; Umbau-Code ohne SolidWorks darf parallel entstehen.
- Neue SolidWorks-API-Aufrufe (STL-Export, Ansichten) vorher mit `swki api methode`/`enum` nachschlagen, Code mit
  `swki api pruefe-code` prüfen; Benutzereinstellungen nur temporär umschalten und zurücksetzen.
- Messdaten (Transkript-Kopien, STL, `kpi.json`) liegen im Arbeitsordner unter `MESSSTAND/`, nicht im Git;
  Zusammenfassungen kommen nach `docs/messstand/`.
- Kein `git push`.
