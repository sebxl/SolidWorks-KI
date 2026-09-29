# Übergabe für die Umsetzung von Stufe 2c (Stand 2026-09-29)

## Auftrag der nächsten Sitzung
Plan **Stufe 2c** mit **superpowers:subagent-driven-development** umsetzen (ein Implementer-Agent pro Task, Review
nach jedem Task, Gesamt-Review am Ende):

- Plan: `docs/superpowers/plans/2026-09-29-stufe-2c-normbohrungen-konturen-baum.md` (12 Tasks)
- Spec (bindend): `docs/superpowers/specs/2026-09-29-stufe-2c-design.md`; Kontext: `2026-09-26-solidworks-ki-design.md`

Inhalt: Feature-Typ `normbohrung` (Bohrungsassistent, ISO: M-Regel-/Feingewinde, ISO 4762, ISO 10642, Stiftbohrung),
Eckradien/Langloch/Kontur mit Bögen in Skizzen, Endbedingungen `bis_flaeche`/`versatz_von_flaeche`, Hinweise für einen
kompakten Feature-Baum, Code-Prüfung `normbohrungen`, Referenz *Auswerferhalteplatte*.

## Stand
- Stufe 2a, Nachtrag 2a und 2b sind auf `main` (PR #1–#3). 206 Unit-Tests, 28/28 Live-Tests inkl. Buchse und
  Formplatte grün auf SOLIDWORKS 2025 (Rechner A). Ergebnisse: `docs/stufe2/ergebnisse.md`.
- Rechner B (SOLIDWORKS 2026) ist für Stufe 2 noch offen – der Nutzer macht das später.

## Wichtig: Anders als bei 2b ist der Plan-Code nicht vorab live gelaufen
- Reine Teile (Task 3–5, Unit-Tests) wurden beim Schreiben des Plans in einer Kopie des Repos durchgespielt
  (241 → 254 → 260 → 272 Tests) und können wörtlich übernommen werden.
- SolidWorks-Code (Task 6–9) ist bester Stand aus API-Index und Spike S9b; Stellen mit `# Abhängig von S10 Frage n`
  werden an die Befunde des Spikes (Task 1–2) angepasst. Nicht raten: nachschlagen, messen, Abweichung im
  Task-Bericht und in `docs/stufe0/ergebnisse.md` nennen.
- **Entscheidungsregel:** Beantwortet der Spike eine Frage nicht mit „geht, und zwar so“, anhalten und mit dem Nutzer
  entscheiden (Notausgang oder Umfang kürzen), bevor Task 3 ff. beginnen.
- Das Sollvolumen der Auswerferhalteplatte (vorläufig 692845,209 mm³) hängt an der Maßtabelle
  `swki/wissen/bohrungsnormen.yaml`; ändert der Spike Tabellenwerte, wird es mit `sollvolumen.py` neu gerechnet –
  nie an einen Messwert angepasst.

## Vorgaben des Nutzers
- Eigener Branch (z. B. `stufe-2c`), am Ende Pull Request; **vor Push und Merge fragen**.
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` – Subagents ausdrücklich so anweisen.
- Kommunikation auf Deutsch. Fragen einzeln stellen, jeweils mit Empfehlung.

## Vor dem Start prüfen
- SOLIDWORKS 2025 frisch gestartet, **nur eine Instanz** (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`); nie eine
  fremde Instanz beenden. Speicher im Blick behalten (> 4 GB → Nutzer um Neustart bitten).
- Toggle 10 (`swInputDimValOnCreate`, startet mit AUS) und Integer-Einstellung 6 (`swTiffScreenOrPrintCapture`) vor
  und nach Live-Läufen gleich (Befehl in den Global Constraints des Plans).
- `git status` sauber, `.venv\Scripts\python.exe -m pytest` grün (206).

## Arbeitsweise (bewährt in 2a/2b)
- Live-Tests nur einzeln: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> …` (`PYTHONIOENCODING=utf-8`).
- Modellwahl: reine Abschrift → günstigstes Modell; Live-Tasks und Spike → mittleres Modell; Reviews mittleres Modell;
  Gesamt-Review das stärkste.
- Implementer starten keine Subagents. Den Prüfer-Agenten startet der Controller mit `subagent_type: pruefer`
  (jetzt verfügbar); das Urteil kommt oft in Code-Fences – nur das JSON-Objekt ablegen.
- Aufgaben, die dieselben Dateien berühren, nicht parallel laufen lassen (`git add swki/pruefung` sammelt fremde
  Änderungen ein).
- Bekannte Fallstricke: `swki/wissen/pywin32-fallstricke.md` (u. a. Print capture vs. Screen capture bei PNGs).

## Offen, nicht Teil von 2c
- Zwei Spec-Entscheidungen des Nutzers: Regel „kein Fortschritt“ bei Bauabbruch; Spec §6 „Vorgabe 3“ vs. 1 + 3 = 4 Läufe.
- Kleine Punkte aus 2b: `docs/stufe2/ergebnisse.md`, Abschnitt „Offene Punkte für Stufe 3“.
- Danach: Plan für Stufe 3 (Baugruppen, Normteile).
