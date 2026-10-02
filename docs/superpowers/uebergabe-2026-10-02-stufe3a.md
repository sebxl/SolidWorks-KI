# Übergabe für Stufe 3a – Normteile (Stand 2026-10-02)

## Auftrag der nächsten Sitzung
Plan **Stufe 3a Normteile** mit **superpowers:subagent-driven-development** umsetzen: ein Implementer-Agent pro Task,
Review nach jedem Task, Gesamt-Review am Ende.

- Plan: `docs/superpowers/plans/2026-10-02-stufe-3a-normteile.md` (12 Tasks). Bindend sind die „Präzisierungen
  gegenüber der Spec“ und die „Global Constraints“ am Anfang des Plans.
- Spec: `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md` (mit dem Nutzer abgestimmt)
- Kontext: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` (§8 Normteile, §11 Stufen)

## Stand
- Stufe 2a–2c und das Aufräum-Paket sind auf `main`: PR #1–#6, zuletzt Merge `5b9d774` (PR #6, 2026-10-02).
- Unit-Tests auf `main`: **349 passed, 55 deselected**.
- Live: Alle 55 Live-Tests sind auf SOLIDWORKS 2025 (Rechner A) grün, darunter Buchse, Formplatte und
  Auswerferhalteplatte.
- Spec und Plan liegen auf Branch `plan-stufe-3a`, lokal und nicht gepusht:
  - Commit `3179f46`: Spec
  - Commit `4673226`: Plan
  - Commit danach: diese Übergabe
  - Der Branch zweigt von `main` (`5b9d774`) ab.
- Der Remote-Branch `origin/aufraeumen` existiert noch, sein PR ist gemergt. Löschen nur nach Rückfrage.
- Rechner B (SOLIDWORKS 2026) ist zurückgestellt (Nutzer, 2026-10-01).

## Nutzerentscheidungen (2026-10-02)
- **Ausrichtung:** Das Projekt zielt auf allgemeine Konstruktion mit Volumenkörpern, nicht auf den Werkzeugbau.
  Gebraucht werden allgemeine Normteile wie Schrauben, Muttern, Scheiben und Stifte.
- **Zuschnitt:** Stufe 3 wird geteilt, 3a Normteile zuerst, danach 3b Baugruppen statisch. Die Referenz
  *Säulenführung* entfällt; 3b bekommt eine allgemeine Referenzbaugruppe, die in der Spec 3b festgelegt wird.
- **Herkunft:** Genormte Teile werden immer selbst konstruiert. Es gibt keine STEP-Daten von Herstellern und keine
  Toolbox. Herstellerdaten gelten nur für nicht genormte Kaufteile, und die gehören nicht zu 3a.
- **Normmaße:** Sie kommen aus Claudes Normwissen und werden per Web-Recherche abgeglichen. Für den Abgleich ist ein
  Workflow mit Agents freigegeben, aber **erst bei der Umsetzung** (Task 10).
  - Ein Wert gilt als abgeglichen, wenn mindestens 2 unabhängige recherchierte Quellen ihn bestätigen.
  - Claudes Wissen zählt dabei nicht als Quelle.
  - Sonst wird die Größe `gesperrt`, und der Widerspruch geht an den Nutzer.
- **Quelle der Wahrheit:** Normtabelle und Bauvorlage liegen im Git. Die Bibliothek ist nur ein Cache, lokal je
  Rechner und getrennt nach SW-Version.
- **Umfang:** ISO 4762, ISO 4032, ISO 7089, ISO 8734, jeweils M5–M16 bzw. Ø 4–12.
- **Gewinde:** Nenn-Ø ohne Darstellung. Das kosmetische Gewinde kommt später als Erweiterung zusammen mit Zeichnungen.
- **Freigabe:** Es gibt keine Nutzerfreigabe. Jedes Teil prüft sich vollständig selbst. Der Prüfer-Agent läuft nur je
  neuer Vorlagenversion.
- **Varianten:** Eine Bibliotheksdatei je Größe und Variante (Festigkeitsklasse/Werkstoff).
- **Einbaureferenzen:** Benannte Bezugsgeometrie aus der Vorlage (`EINBAU_ACHSE`, `EINBAU_EBENE` …).
- **Längen:** Nur Längen aus der Längenreihe der Norm sind zulässig.

## Vorgaben des Nutzers
- Eigener Branch `stufe-3a`, angelegt von `plan-stufe-3a`. Am Ende ein Pull Request; **vor Push und Merge fragen**.
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; die Subagents ausdrücklich darauf
  anweisen.
- Kommunikation auf Deutsch. Fragen einzeln stellen, jede mit einer Empfehlung.

## Vor dem Start prüfen
- `git status` ist sauber, `.venv\Scripts\python.exe -m pytest -q` ergibt 349 passed.
- `.superpowers/` ist lokal über `.git/info/exclude` ignoriert. Das SDD-Ledger kommt nach
  `.superpowers/sdd/2026-10-02-stufe-3a-normteile/`.
- **Mit SolidWorks:** Task 1, 2, 3 und 7–9 haben Live-Teile, dazu Task 11 und die Regression in Task 12.
  - SOLIDWORKS 2025 muss frisch gestartet sein, **genau eine Instanz**
    (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`).
  - Eine fremde Instanz nie beenden.
- **Ohne SolidWorks:** Task 4–6 und Task 10.
- Toggle 10 und Integer-Einstellung 6 vor und nach den Live-Läufen lesen. Den Befehl dafür nennen die Global
  Constraints des Plans; erwartet ist `False 1`.

## Ablauf mit Stopps für Controller und Nutzer
- **Nach Task 1 (Spike):** Fehlt ein Werkstoff (1.1191, 1.7225, 1.4301, 1.0038, 1.3505), entscheidet der Controller
  einen Ersatz und hält ihn im Ledger fest, bevor Task 7 beginnt. Baut die Mittellinie auf der Profilkante nicht,
  gilt für die Vorlagen die Ersatzform aus dem Spike.
- **Task 10:**
  - Der Controller startet den Recherche-Workflow und lädt vorher den Skill `workflow-authoring`.
  - Ein Implementer pflegt die Ergebnisse nach den Regeln im Plan in die Tabellen ein.
  - Widersprüche legt der Controller dem Nutzer vor, **eine Frage je Widerspruch, mit Empfehlung**. Eine Entscheidung
    wird als `entscheidung` in der Tabelle vermerkt.
- **Task 11:**
  - Der Implementer baut die Musterteile und hält danach an.
  - Der Controller startet je Norm den Prüfer-Agenten (`subagent_type: pruefer`) und legt jedes Urteil mit
    `swki normteil urteil` ab.
  - Danach geht es mit dem Implementer weiter: `hole` live und die Stichprobe mit 20 Teilen.

## Erfahrungen aus 2c und dem Aufräum-Paket (wichtig für die Live-Tasks)
- **Speicher:** SolidWorks wächst je Live-Testdatei um etwa 50–1250 MB **Private Bytes**. Das Working Set ist kein
  Maßstab.
  - Ab ca. 4 GB nach der laufenden Datei anhalten und den Nutzer um einen Neustart bitten. Im Aufräum-Paket waren dafür
    zwei Neustarts nötig.
  - Die Live-Suite deshalb **dateiweise** laufen lassen.
  - Ein Implementer, der wegen des Speichers anhält, wird nach dem Neustart per SendMessage fortgesetzt.
- **Neustart:** Das MCP `solidworks-mcp` kann per COM eine zweite, fensterlose Instanz starten (`-Embedding`,
  Kurzpfad `C:\PROGRA~1\…`). Vor jedem Live-Lauf die Instanzen prüfen; bei zwei Instanzen den Nutzer fragen.
- **Implementer-Agenten:** Mit SolidWorks läuft immer nur ein Agent gleichzeitig.
- **Modellwahl, die sich bewährt hat:**
  - Abschrift mit vollständigem Code → mittleres Modell, bei kleinen Tasks das günstigste.
  - Live-Tasks und Reviews → mittleres Modell.
  - Gesamt-Review → stärkstes Modell.
- **Fallstricke:** `swki/wissen/pywin32-fallstricke.md`, Abschnitt Stufe 2c.

## Noch offen, nicht Teil von 3a
- 3b Baugruppen statisch: eigene Spec, Weg wie gehabt (Brainstorming → Spec → Plan).
- Kaufteile von Herstellern: eigenes kleines Paket, sobald es einen echten Bedarf gibt.
- Kosmetisches Gewinde (mit Zeichnungen, Stufe 5) und weitere Normen (ISO 4017, ISO 10642, ISO 2338 …).
- Offene Punkte aus dem Aufräum-Paket stehen in `docs/stufe2c/ergebnisse.md` („Offene Punkte“):
  - `offen = 0` bei ungeprüftem Lauf im Bericht,
  - Regel-3-Text bei `muster_kreis` mit 360°,
  - Bohr- und Gewindetiefe von `normbohrung` ohne Gleichung,
  - Zwei-Körper-Fall bei `versatz_von_flaeche`.
- Rechner B (SW 2026).
