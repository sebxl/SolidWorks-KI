# Übergabe für die nächste Sitzung (Stand 2026-09-27)

## Auftrag der nächsten Sitzung
Plan **Stufe 2a** umsetzen, danach **Stufe 2b**:

1. `docs/superpowers/plans/2026-09-27-stufe-2a-spezifikation-compiler.md` (15 Tasks)
2. `docs/superpowers/plans/2026-09-27-stufe-2b-pruefung-schleife-referenzen.md` (9 Tasks, setzt 2a voraus)

Umsetzung mit **superpowers:subagent-driven-development** (ein Implementer-Agent pro Task, Review zwischen den Tasks).
Design: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`.

## Stand
- **Stufe 0 + 1 fertig**: Projektgerüst, `setup/einrichten.ps1`, MCP gepinnt und auf 20 Lese-Tools gesperrt
  (Wirksamkeit am 27.09. bestätigt), API-Nachschlagewerk (`swki api …`), Spikes S1–S9b, Ergebnisse in
  `docs/stufe0/ergebnisse.md`, geprüfte Muster in `swki/wissen/pywin32-fallstricke.md`.
- **Pläne 2a/2b**: Jede Datei darin wurde vorab implementiert und live gegen SOLIDWORKS 2025 geprüft
  (185 Unit-Tests, 29 Live-Tests, beide Referenzteile Formplatte und Buchse bestanden, Screenshots gesichtet).
  Code aus den Plänen **wörtlich** übernehmen.
- **Referenzimplementierung**: lokaler Branch `entwurf-plan-stufe2` (nur auf Rechner A, nicht gepusht, **nicht mergen**).
  Dient nur zum Vergleich, falls live etwas anders reagiert als im Plan.
- Rechercheunterlagen (nicht im Git): `%USERPROFILE%\.swki\plan-stufe2\` – API-Signaturen, live verifizierte
  Aufrufketten S9a/S9b (`s9a-aufrufketten.md`, `s9b-aufrufketten.md`).

## Vorgaben des Nutzers
- **Vor Downloads fragen**: In 2a Task 3 wird `jsonschema` von PyPI installiert.
- **Vor jedem `git push` fragen.**
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` – auch Subagents ausdrücklich so
  anweisen (sie setzen sonst ihr eigenes Modell ein).
- Bisher wurde direkt auf `main` gearbeitet (Entscheidung des Nutzers für Stufe 0/1) – vor dem Start kurz bestätigen lassen.
- Kommunikation auf Deutsch.

## Vor dem Start prüfen
- SOLIDWORKS 2025 **frisch gestartet** und geöffnet (lange Sitzungen mit vielen Testteilen wachsen auf 8–10 GB und werden
  träge; einmal hing SolidWorks dadurch minutenlang).
- Benutzereinstellung „Werte beim Erzeugen von Bemaßungen eingeben“ (`swInputDimValOnCreate`, Toggle 10) steht auf **AN**.
- `git status` sauber, `.venv\Scripts\python.exe -m pytest` grün.

## Wichtigste technische Befunde (Details in den Plänen und der Wissensdatei)
- **COM immer late-bound** (`swki.verbindung.verbinde`). Nullargumentige Member ohne `()`; Ausnahmen: `IBody2`-Methoden
  mit `()`; `CreatePoint`, `ViewZoomtofit2`, `BlankRefGeom`, `IMeasure.Calculate` nur nach `_FlagAsMethod` und mit `()`.
  Objekt-Parameter mit `callout_leer()`, Double-Arrays mit `r8_array()`.
- **Skizzen bestimmt der Compiler selbst voll**: `AddToDB=True`, eigene Maße für Größe **und** Lage jedes Kennpunkts zum
  Ursprung. `FullyDefineSketch` ist unzuverlässig. Rechtecke über `CreateCornerRectangle` (bei `CreateCenterRectangle`
  fehlte je nach Zustand der Mittelpunkt).
- **Skizzenkoordinaten**: vorne X=u, Y=v · oben X=u, Z=−v · rechts Z=−u, Y=v.
- **Schnitt** geht standardmäßig gegen die Skizzennormale; trifft er kein Material, kommt `None` ohne Fehlermeldung.
- **Lineare Muster** lassen Instanzen außerhalb des Körpers stillschweigend weg (nur die Volumenprüfung zeigt es).
- **Prüfung misst im fertigen Teil ohne Anker neu aufzulösen** (Bohrungsachsen aus dem Bauprotokoll), öffnet mit
  `OpenDoc6` und bricht ab, wenn die Datei schon offen ist.

## Arbeitsweise bei Live-Tests
- Immer einzeln mit Zeitlimit: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> …` (entsteht in 2a Task 7).
- Nach `ZEITLIMIT` oder hart beendetem Prozess: prüfen, ob SolidWorks reagiert, und Toggle 10 zurücksetzen
  (ein abgebrochener Prozess führt sein `finally` nicht mehr aus).
- Nie Prüfwerte an Messwerte anpassen; bei Abweichung Bauweg prüfen oder die Abweichung melden.

## Offen nach Stufe 2
- Abschluss erst, wenn die Referenzen auch auf **Rechner B (SOLIDWORKS 2026)** bestehen (2b Task 9, mit dem Nutzer).
- Prüfung vergleicht Volumen, nicht Oberfläche/Masse (Masse folgt aus Volumen und Material).
- Danach: Plan für Stufe 3 (Baugruppen, Normteile); Befunde aus S5/S6 (Kollision, `AddComponent5` platziert die
  Bounding-Box-Mitte, `AddMate5`/`CreateMassProperty` obsolet) und S7 (Toolbox nur über Rückfallweg) beachten.
