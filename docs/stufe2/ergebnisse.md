# Stufe 2 – Ergebnisse

Gesamte Testsuite auf Rechner A (SOLIDWORKS 2025) gelaufen: `pytest -v` 204 bestanden (28 abgewählt,
das sind die `sw`-markierten Live-/Referenztests), `tests/live_einzeln.py tests/live tests/referenz`
alle 28 Einzeltests `OK` (Prozess `SLDWORKS.exe` durchgehend stabil), `swki api pruefe-code` ohne
Befunde. Toggle 10 (`GetUserPreferenceToggle`) vor und nach dem gesamten Lauf unverändert `False`.
Speichernutzung `SLDWORKS.exe` nach dem Live-Lauf ca. 610 MB, nach den beiden manuellen
Referenzläufen ca. 621 MB – jeweils deutlich unter 4 GB.

Die Zahlen in der Tabelle stammen aus je einem manuellen Lauf (`validieren` → `freigeben` → `bauen`
→ `pruefen`) außerhalb der Regressions-Suite, da diese ihre Arbeitsordner und Protokolle nach dem
Test wieder löscht. Beide Läufe: `bestanden: true`, `maengel: []`.

| Referenz | SW 2025 (Rechner A) | SW 2026 (Rechner B) | Bemerkung |
|---|---|---|---|
| Buchse | 29.09.2026, Volumen ist 37425,139 mm³ / soll 37425,1 mm³ (Abw. 0,0001 %), Dauer 15,202 s | ausstehend | |
| Formplatte DS | 29.09.2026, Volumen ist 3069575,535 mm³ / soll 3069574,5 mm³ (Abw. 0,0000 %), Dauer 26,106 s | ausstehend | Notausgang f10 (M8-Gewinde) |

## Laufzeiten (Phasenzeiten aus dem Protokoll, Rechner A)

**Buchse** – gesamt 15,202 s: vorbereiten 0,713 s, bauen 13,987 s, speichern 0,412 s.
Je Feature: f1 Rotation 5,732 s, f2 Fase 0,462 s, f3 Fase 0,491 s, f4 Rotation 4,318 s,
f5 Bohrung 2,339 s, f6 Muster (Kreis) 0,64 s.

**Formplatte DS** – gesamt 26,106 s: vorbereiten 0,675 s, bauen 24,834 s, speichern 0,494 s.
Je Feature: f1 Extrusion 2,692 s, f2 Bohrung 4,297 s, f3 Schnitt 2,317 s, f4 Verrundung 2,466 s,
f5 Verrundung 1,299 s, f6 Fase 2,991 s, f7 Bohrung mit Senkung 3,33 s, f8 Muster (linear) 0,736 s,
f9 Spiegeln 0,52 s, f10 Skript (Notausgang, M8-Gewinde) 4,182 s.

## Offene Punkte für Stufe 3

- Rechner B (SOLIDWORKS 2026): Referenzen noch nicht gelaufen (Abschluss Stufe 2 laut Spec §11).
- Fehlalarme in `validieren`-`hinweise`: `mittellinie.von/bis`, Vollwinkel 360, `fase.winkel: 45`,
  jeder Polygonpunkt einzeln (Buchse: 14 Hinweise).
- `swki freigeben x.freigegeben.yaml` wird nicht abgelehnt; `freigeben` gibt den Pfad der Kopie
  nicht aus; Grenze „Vorzeichenwechsel beim Ebenenversatz → neu bauen“ nur im Code-Kommentar.
- Aus 2a geparkt: `swki bauen --lauf N` überschreibt bestehenden Lauf; `speichere` prüft den
  Arbeitsordner nicht; Einheiten der Teilevorlage ungeprüft (wichtig für Rechner B);
  Compiler-Namen (`<id>_skizze`, `<id>_senkung`, `achse_x|y|z`) als Feature-IDs nicht verboten;
  kein Unit-Test für `Kontext.verknuepfe`; Notausgang-Skripte können die statische Prüfung gezielt
  umgehen.
- Screenshots: Exportoption „Print capture“ wird während der Aufnahme auf „Screen capture“
  umgeschaltet (Fund 2026-09-29, über `sw.einstellung_int`); nach einem hart beendeten Prozess prüfen, ob sie
  zurückgesetzt ist.
- Prüfer-Agent antwortet trotz Anweisung mit Code-Fences; Claude legt nur das JSON-Objekt ab
  (Skill `konstruieren`).
- Baugruppen/Normteile: Befunde aus S5/S6 (Kollision, `AddComponent5` platziert die
  Bounding-Box-Mitte, `AddMate5`/`CreateMassProperty` obsolet) und S7 (Toolbox nur über
  Rückfallweg).
- Regel „kein Fortschritt" zählt einen Bauabbruch als genau einen Mangel (Entscheidung Nutzer offen).
- Spec §6 „Vorgabe 3" vs. Code 1 + 3 = 4 Läufe (Entscheidung Nutzer offen).
- `pruefen` prüft den Protokollstatus nicht: ein Teil nach Bauabbruch wird trotzdem gemessen.
- `pruefer.json` wird nicht auf Form geprüft.
- `_pappus` ignoriert Rechteck/Kreis in Rotationsskizzen; verschachtelte Profile werden addiert.
- `_compiler_aenderungen` ohne git-Fehlerbehandlung.
- `--max` akzeptiert negative Werte.
- Nach hart beendetem Prozess kann `swTiffScreenOrPrintCapture` auf 0 stehen bleiben (wie Toggle 10).
- Prüfer-Isolation nur per Anweisung.
- Buchse führt Nut/Lochkreis als feste Zahlen (Vorlage für den Skill).
