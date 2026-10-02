# Übergabe für das Aufräum-Paket nach Stufe 2c (Stand 2026-10-01)

## Auftrag der nächsten Sitzung
Plan **Aufräum-Paket** mit **superpowers:subagent-driven-development** umsetzen: ein Implementer-Agent pro Task,
Review nach jedem Task, Gesamt-Review am Ende.

- Plan: `docs/superpowers/plans/2026-10-01-aufraeumen-nach-2c.md` (8 Tasks)
- Bindend: die Nutzerentscheidungen am Anfang des Plans; Kontext `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` §6
- Quellen der Punkte: `docs/stufe2/ergebnisse.md` („Offene Punkte für Stufe 3“), `docs/stufe2c/ergebnisse.md` („Offene Punkte“)

Inhalt in fünf Gruppen:
- **A Prüfschleife:** Bauabbruch nicht vergleichen; `pruefen` verweigert abgebrochene Läufe; Spec-Text „1 + 3“; `--max` ≥ 0.
- **B Robustheit:** Freigabe-Kopie, `bauen --lauf`, `pruefer.json`-Form, git-Fehler, `speichere` nur im Arbeitsordner, reservierte IDs.
- **C Validierung und Hinweise:** Fehlalarme bei `feste_zahl`, Regel-3-Texte, Normbohrung (doppelte Positionen, Tiefe gegen Senkung), Kreissektor, `_pappus`.
- **D Tests:** Ausdrucksfehler, Hinweis-Randzweige, `verknuepfe`, Zylinderprüfung, Zwei-Körper live, Toleranzen.
- **E Code-Pflege:** `eckradien_roh`, Konstanten nach `normen.py`.

Danach steht **Stufe 3** an (Baugruppen statisch und Normteile, Referenz *Säulenführung*). Dafür gibt es noch keine Spec.
Der Weg ist wie bei 2c: Brainstorming → Spec → Plan.

## Stand
- Stufe 2a, 2b und 2c sind auf `main` (PR #1–#5, zuletzt Merge f2fdcd3).
- Unit-Tests: 276 passed, 54 deselected.
- Auf SOLIDWORKS 2025 (Rechner A) sind alle Live- und Referenztests grün: Buchse, Formplatte, Auswerferhalteplatte.
  Ergebnisse stehen in `docs/stufe2c/ergebnisse.md`.
- Rechner B (SOLIDWORKS 2026) steht nicht zur Verfügung und wird übersprungen (Nutzer, 2026-10-01).

## Nutzerentscheidungen (2026-10-01)
- Läufe: 1 + 3 = höchstens 4.
- Regel „kein Fortschritt“, Option A: Ein Lauf mit Bauabbruch wird nicht verglichen und verbraucht nur einen Lauf.
  Verglichen werden nur Läufe, die durchgebaut und geprüft sind, jeweils mit dem letzten solchen Lauf.
- Umfang des Aufräum-Pakets: die Gruppen A–E vollständig.

## Vorgaben des Nutzers
- Eigener Branch, z. B. `aufraeumen`. Am Ende ein Pull Request; **vor Push und Merge fragen**.
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; die Subagents ausdrücklich darauf anweisen.
- Kommunikation auf Deutsch. Fragen einzeln stellen, jede mit einer Empfehlung.

## Vor dem Start prüfen
- `git status` ist sauber, `.venv\Scripts\python.exe -m pytest -q` ergibt 276 passed.
- Task 1–7 laufen **ohne SolidWorks**. Erst Task 8 braucht SOLIDWORKS 2025: frisch gestartet, **genau eine Instanz**
  (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`). Eine fremde Instanz nie beenden.
- Toggle 10 und Integer-Einstellung 6 vor und nach den Live-Läufen lesen (Befehl steht in den Global Constraints des
  Plans); erwartet ist `False 1`.

## Erfahrungen aus 2c (wichtig für Task 8)
- **Speicher:** SolidWorks wächst bei Live-Läufen je Testdatei um etwa 50–1250 MB **Private Bytes**. Das Working Set im
  Task-Manager bleibt unauffällig, ist also kein Maßstab. Ab ca. 4 GB nach der laufenden Datei anhalten und den Nutzer um
  einen Neustart bitten; die Live-Suite deshalb **dateiweise** laufen lassen. Bei über 7 GB hing SolidWorks zweimal und
  lieferte „Ausnahmefehler des Servers“.
- **Neustart:** Beim Neustart von SolidWorks kann das MCP `solidworks-mcp` per COM eine zweite Instanz ohne Fenster
  starten (Kurzpfad `C:\PROGRA~1\…`). Vor jedem Live-Lauf die Instanzen prüfen; bei zwei Instanzen den Nutzer fragen.
- **Implementer-Agenten:** Mit SolidWorks immer nur ein Agent gleichzeitig. Ein Agent, der wegen des Speichers anhält,
  wird nach dem Neustart per SendMessage fortgesetzt; sein Kontext bleibt erhalten.
- Modellwahl, die sich bewährt hat: Abschrift mit vollständigem Code → günstigstes Modell; Live-Tasks → mittleres Modell;
  Reviews → mittleres Modell (Doku-Nachprüfungen auch günstigstes); Gesamt-Review → stärkstes Modell.
- Bekannte Fallstricke: `swki/wissen/pywin32-fallstricke.md`, darin der Abschnitt Stufe 2c.

## Noch offen, nicht Teil dieses Pakets
- Bohr- und Gewindetiefe von `normbohrung` hängen nicht per Gleichung an Parametern; die Prüfung `normbohrungen`
  erkennt aber Abweichungen gegenüber der Freigabe.
- Aufsatz mit `versatz_von_flaeche` und abgesetzter Skizze ergibt zwei Körper. Das ist eine bekannte Einschränkung;
  die Code-Prüfung `koerper` meldet es.
- Nur Position 1 einer Normbohrung wird gegen die Fläche geprüft (`IsSame`).
- `norm_von` liest `config/standard.yaml` bei jedem Aufruf neu.
- `auftraege/` ist laut Design versioniert. Beispiel- und Testaufträge nicht committen bzw. nach dem Lauf löschen.
- Rechner B (SW 2026).
