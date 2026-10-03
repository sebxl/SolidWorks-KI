# Übergabe für die Umsetzung von Stufe 3b – Baugruppen statisch (Stand 2026-10-03)

## Auftrag der nächsten Sitzung
Plan **Stufe 3b Baugruppen statisch** mit **superpowers:subagent-driven-development** umsetzen: ein Implementer-Agent
pro Task, Review nach jedem Task, Gesamt-Review am Ende.

- Plan: `docs/superpowers/plans/2026-10-03-stufe-3b-baugruppen.md` (12 Tasks). Bindend sind die „Präzisierungen
  gegenüber der Spec“, die „Global Constraints“ und die Tabelle „Abhängigkeiten vom Spike S12“ am Anfang des Plans.
- Spec: `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md` (mit dem Nutzer abgestimmt)
- Kontext: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`, Spec 3a, `docs/stufe3a/ergebnisse.md`

## Stand
- `main` steht auf `04d0c1c` (Merge PR #7, Stufe 3a). Unit-Tests auf `main`: **456 passed, 95 deselected**.
- Branch `plan-stufe-3b` (von `main`, lokal, **nicht gepusht**):
  - `4947267` Übergabe für Spec und Plan
  - `dbf00cf` Spec 3b
  - `b5e6020` Plan 3b
  - danach: diese Übergabe
- **Plan-Code vorab geprüft (ohne SolidWorks):** Alle vollständigen Module und Tests des Plans wurden in einem
  Wegwerf-Worktree eingespielt (die Änderungen an bestehenden Dateien nach den Plan-Schritten). Ergebnis: **566 passed**
  (genau die Endzahl des Plans), `swki api pruefe-code` ohne Befund, auch für `swki/baugruppe` und `swki/aenderungen.py`.
  Der SolidWorks-Code (Spike, `sw_baugruppe`, `bau`, `pruefen`, Live-Tests) ist **nicht** live gelaufen – das
  klärt Spike S12 in Task 1.

## Nutzerentscheidungen (Brainstorming 2026-10-03)
- **Referenz:** Stehlager – Grundplatte (fixiert), Lagerunterteil, Lagerdeckel; Deckel mit 2 × ISO 4762 M8 in Gewinde,
  Unterteil mit 2 Durchsteckverschraubungen ISO 4762 M10 + 2 × ISO 7089 + ISO 4032, 2 × ISO 8734 zum Zentrieren.
- **Eine Freigabe** für Baugruppe und Teil-Specs; jeder Lauf baut alle Eigenteile frisch.
- **Normteile** werden in den Lauf-Ordner kopiert; die Baugruppe verweist nie auf die Bibliothek.
- **Wiederholungen** über `je_position` (aufgelöst in Einzelinstanzen und Einzelverknüpfungen).
- **Referenzen** bei Eigenteilen: alle Teil-Anker (`referenz`, `{feature, flaeche}`, Bohrungsachse, Instanzfläche,
  Standardebene, `nahe` mit Hinweis).
- **Manuelle Änderungen:** Spec bleibt Quelle; swki erkennt Änderungen vor jedem Lauf (`MANUELL_GEAENDERT`), liest
  Parameter aus (`swki aenderungen`), Übernahme nur nach Bestätigung mit neuer Freigabe, Verwerfen nur auf Anweisung
  (`swki bauen --verwerfen`). Gilt **auch für Einzelteile**.
- **Bestimmtheit:** Drehung sperren bei konzentrischen Verknüpfungen mit Normteilen; alles voll bestimmt.
- **Kollision:** Gewindepaarung erkennen und über das Ringvolumen nachrechnen; sonst jede Überlappung ein Mangel.
- **Prüfung vollständig** (inkl. Teilprüfung je Eigenteil, Passung in `validieren`, Lage über `masse_pruefen`), ein
  Prüfer.
- **Eigener Skill `baugruppe`**; gleiche Befehle mit Weiche nach `art`; Verknüpfungen sind Bauweg.
- **Keine Unterbaugruppen** in 3b.

## Dem Nutzer bei der Übergabe am Ende melden
- **Präzisierung 3 (Abweichung von Spec §12):** `c` bei ISO 8734 wird nicht direkt gemessen (es gibt keine Messart für
  Fasen); die neue Vorlagenversion misst nur `EINBAU_EBENE_2` gegen +y. Wenn der Nutzer die direkte Messung will, ist
  das eine neue Messart (eigener kleiner Task).
- Präzisierung 1: Gewindepaarungen werden über die Lage erkannt (Schraubenachse durch den Gewinde-Eintrittspunkt),
  nicht über die Verknüpfung – die Schraube wird ja an der Senkung im Deckel verknüpft.
- Präzisierung 2: Gewinde `durch` ohne Volumen-Soll (Prüfung `ok: null`).

## Vorgaben des Nutzers
- Eigener Branch `stufe-3b`, angelegt von `plan-stufe-3b`. Am Ende ein Pull Request; **vor Push und Merge fragen**.
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; die Subagents ausdrücklich darauf
  anweisen.
- Kommunikation auf Deutsch. Fragen einzeln stellen, jede mit einer Empfehlung.
- **SolidWorks-Neustarts übernimmt der Controller selbst** bei ca. 4 GB Private Bytes (Ablauf in den Global
  Constraints des Plans): genau eine Instanz, keine fremden offenen Dokumente, `ExitApp`, Start über
  `installationsordner`, danach eine Instanz, Fenster sichtbar, `False 1`.

## Vor dem Start prüfen
- `git status` sauber, `.venv\Scripts\python.exe -m pytest -q` → 456 passed.
- `.superpowers/` ist lokal über `.git/info/exclude` ignoriert. SDD-Ledger nach
  `.superpowers/sdd/2026-10-03-stufe-3b-baugruppen/`.
- **Mit SolidWorks:** Task 1 (Spike), 5 (Live Änderungserkennung), 6 (Vorlagen live + Prüfer), 8, 10, 11, Regression in
  Task 12. SOLIDWORKS 2025 frisch gestartet, **genau eine Instanz** (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`),
  Toggle 10 / Integer 6 = `False 1`.
- **Ohne SolidWorks:** Task 2, 3, 4, 7, 9 (und die Unit-Teile der übrigen).

## Ablauf mit Stopps für Controller und Nutzer
- **Nach Task 1 (Spike S12):** jede der 14 Zeilen der Tabelle „Abhängigkeiten vom Spike S12“ gegen das JSON prüfen.
  Weicht eine Annahme ab, entscheidet der Controller nach Spalte „sonst“ und hält es im Ledger fest, bevor Task 7
  beginnt. Zeile 6 (LockRotation wirkt nicht) und Zeile 11 (Hash ändert sich schon beim Öffnen) sind Fragen an den
  Nutzer.
- **Task 6:** Der Implementer baut die Musterteile ISO 7089 und ISO 8734 und hält an; der Controller startet je Norm den
  Prüfer-Agenten und legt die Urteile mit `swki normteil urteil` ab. Erst danach Task 8 (braucht ISO 8734 über `hole`).
- **Task 11:** Der Implementer committet Referenz und Negativfälle und hält an; der Controller baut das Stehlager als
  Auftrag `auftraege/REF-stehlager/` (nicht ins Git), startet den Prüfer-Agenten, legt das Urteil ab, `swki status`
  → `bestanden`, `swki bericht`.
- Nachbessern am Stehlager nur am **Bauweg** (Verknüpfungen, Ausrichtung, Reihenfolge, Feature-Reihenfolge); nie
  Parameter, Normteile oder `pruefung`.

## Erfahrungen (wichtig für die Live-Tasks)
- **Speicher:** Private Bytes messen, nicht das Working Set. Erster Bau nach einem Neustart ca. +1,6 GB, danach
  80–160 MB je Teil; eine Stehlager-Baugruppe grob 0,6–1 GB. Live-Dateien **einzeln** laufen lassen
  (`tests\live_einzeln.py <datei> --zeit 300` bzw. `600` für das Stehlager).
- **Nie zwei Implementer gleichzeitig**, solange SolidWorks läuft. Ein Implementer, der wegen Speicher anhält, wird
  nach dem Neustart per SendMessage fortgesetzt.
- **Bewährtes Muster:** Unit-Teile committen, Live-Teile nachholen, sobald SolidWorks frei ist.
- **Modellwahl:** Abschrift mit vollständigem Code → mittleres Modell (kleine Tasks das günstigste); Live-Tasks und
  Reviews → mittleres Modell; Gesamt-Review → stärkstes Modell.
- **API:** vor jedem neuen Aufruf `swki api methode` / `swki api enum`; Late Binding (nullargumentige Member ohne `()`),
  nullargumentige Aktionen über `_FlagAsMethod` (Plan: `sw_baugruppe.rufe`). `swAddMateError_NoError` ist **1**.
- Das MCP `solidworks-mcp` kann beim Neustart per COM eine zweite, fensterlose Instanz starten – vor jedem Live-Lauf die
  Instanzen prüfen.

## Nicht Teil von 3b
Bewegungen, treibende und mechanische Verknüpfungen, gezählte Freiheitsgrade (Stufe 4); Unterbaugruppen;
Konfigurationen; SW-Komponentenmuster; Verbindungssatz-Makro; fremde Teile (`quelle: datei`); vollständige
Rückführung manueller Geometrieänderungen; kosmetisches Gewinde; Kaufteile; weitere Normen; Rechner B; die übrigen
3a-Kleinbefunde (Liste in `docs/stufe3a/ergebnisse.md`).
