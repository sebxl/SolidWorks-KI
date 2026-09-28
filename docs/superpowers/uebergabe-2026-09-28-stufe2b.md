# Übergabe für die Umsetzung von Stufe 2b (Stand 2026-09-28)

## Auftrag der nächsten Sitzung
Plan **Stufe 2b** mit **superpowers:subagent-driven-development** umsetzen (ein Implementer-Agent pro Task, Review
zwischen den Tasks, Gesamt-Review am Ende):

- `docs/superpowers/plans/2026-09-27-stufe-2b-pruefung-schleife-referenzen.md` (9 Tasks)

Design: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` (§6 Prüfung und Nachbesserung, §9, §11, §12).

## Stand
- **Stufe 0 + 1** fertig (Projektgerüst, MCP gesperrt auf 20 Lese-Tools, API-Nachschlagewerk `swki api …`, Spikes).
- **Stufe 2a** fertig und auf `main` (PR #1): Spezifikation, Compiler mit 10 Feature-Typen, `swki validieren|freigeben|bauen`.
- **Nachtrag 2a** fertig (Plan `2026-09-28-stufe-2a-nachtrag-freigabe-parametrik.md`):
  - `swki freigeben` legt `<spec>.freigegeben.yaml` ab (SHA-256 in `freigabe.json`); `freigegebene_spec(spec_pfad)`
    liefert sie. Sie ist das Soll für den Prüfer-Agenten und für `volumen: auto`.
  - `swki validieren` meldet feste Zahlen in maßtragenden Feldern als `hinweise`.
  - Musterabstände, Kreismusterwinkel, Ebenenversatz und Fasenwinkel hängen per Gleichung an Parametern.
- Tests auf `main`: 174 Unit-Tests grün, alle Live-Tests grün (SOLIDWORKS 2025 Rev. 33.5.0).
- **Plan 2b ist bereits auf den Nachtrag angepasst** (Task 2 `bewerte(..., freigegeben)`, Task 4 `swki pruefen`,
  Task 5 Prüfer-Agent, Task 6 Skill `konstruieren`). Jede Datei darin wurde vorab implementiert und live geprüft,
  inklusive beider Referenzteile (Buchse, Formplatte). Code **wörtlich** übernehmen.

## Referenzimplementierung (nur Rechner A, lokal, nicht gepusht, **nicht mergen**)
- **`entwurf-2b-ergaenzung`** – maßgeblicher Vergleich für 2b: Stand 2a + Nachtrag + 2b-Dateien mit den Anpassungen.
  Live grün: 2a-Tests, `test_live_parametrik`, `test_live_pruefen`, `tests/referenz/test_referenzen.py` (beide Teile).
- `entwurf-plan-stufe2` – ursprüngliche Referenz von 2a/2b (vor dem Nachtrag).
- Nützlich vor dem Start: alle Code-Blöcke des Plans, vor denen ein Dateiname steht (`` `pfad`: ``), gegen
  `git show entwurf-2b-ergaenzung:<pfad>` vergleichen. Stand 2026-09-28: alle identisch; einzige erwartete Ausnahme
  ist `tests/referenz/test_referenzen.py` in Task 7 (Zwischenstand nur mit Buchse, Task 8 ergänzt die Formplatte).
  `.claude/agents/pruefer.md` und die beiden Skills liegen in keinem Branch (nur im Plan).
- Rechercheunterlagen (nicht im Git): `%USERPROFILE%\.swki\plan-stufe2\`.

## Vorgaben des Nutzers
- Arbeit auf einem **eigenen Branch** (z. B. `stufe-2b`), am Ende Pull Request; **vor jedem Push und vor dem Merge
  fragen** (bei 2a und dem Nachtrag hat der Nutzer PR + Merge + Branch löschen bestätigt).
- Vor Downloads fragen (2b braucht keine neuen Pakete).
- Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` – Subagents ausdrücklich so anweisen.
- Kommunikation auf Deutsch.

## Vor dem Start prüfen
- SOLIDWORKS 2025 **frisch gestartet** (unter 1 GB). Nach etwa fünf Live-Tasks wuchs es in 2a auf 5–6 GB – dann den
  Nutzer um einen Neustart bitten (Grenze laut Plan ~4 GB). Task 7 und 8 (Referenzteile) sind die schwersten Läufe.
- **Nur eine SolidWorks-Instanz**: Am 2026-09-28 lief zusätzlich eine fensterlose `SLDWORKS.exe` (vermutlich vom
  MCP-Server gestartet). `swki.verbindung.verbinde` startet nie selbst, sondern hängt sich an die in der ROT
  registrierte Instanz – bei zwei Instanzen ist unklar, welche. `tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`
  prüfen und den Nutzer fragen; keine fremde Instanz beenden.
- Toggle 10 (`swInputDimValOnCreate`): SolidWorks startet auf diesem Rechner mit **AUS**; per API gesetzte Werte
  überleben keinen Neustart. Das ist in Ordnung – der Compiler schaltet ihn beim Skizzieren selbst und stellt den Wert
  von vorher wieder her. Vor und nach Live-Tests prüfen, dass er unverändert ist.
- `git status` sauber, `.venv\Scripts\python.exe -m pytest` grün.

## Arbeitsweise (bewährt in 2a und im Nachtrag)
- Live-Tests immer einzeln mit Zeitlimit: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> …`
  (bei Umlauten in der Ausgabe `PYTHONIOENCODING=utf-8`). Nach `ZEITLIMIT` oder hart beendetem Prozess: SolidWorks
  prüfen und Toggle 10 auf den Wert von vorher zurücksetzen.
- Nie Prüfwerte an Messwerte anpassen; bei Abweichung Bauweg prüfen, mit dem Referenz-Branch vergleichen, melden.
- Modellwahl, die funktioniert hat: reine Abschrift ohne SolidWorks → günstigstes Modell; Tasks mit Live-Tests →
  mittleres Modell; Reviews mittleres Modell; Gesamt-Review das stärkste.
- Implementer sollen bei Compiler-Code `swki api pruefe-code <dateien>` laufen lassen und das im Bericht belegen.
- Neue Module nicht als leere Datei/Ordner vor dem RED-Lauf anlegen (Namespace-Paket verändert die Fehlermeldung).

## Hinweise zu einzelnen Tasks von 2b
- **Task 4** registriert `swki pruefen|status|bericht` in `swki/cli.py` (`_befehlsgruppen` mit `pruefung_befehle`).
- **Task 5** (Prüfer-Agent): `subagent_type: pruefer` steht erst nach einem Neustart von Claude Code zur Verfügung;
  sonst den Trockentest mit einem general-purpose-Agenten und dem Inhalt von `.claude/agents/pruefer.md` machen.
- **Task 7/8**: Die Referenzteile werden in `tmp_path` kopiert, Freigaben und Protokolle landen nicht im Repo.
- **Task 9**: Rechner B (SOLIDWORKS 2026) geht nur mit dem Nutzer. Auf Rechner A Step 1–3 erledigen, dann anhalten und
  den Nutzer bitten, auf Rechner B `git pull`, `setup\einrichten.ps1` und die Referenzen laufen zu lassen.

## Offene Punkte (vor oder während 2b entscheiden)
1. **Kopie ohne Kommentare**: `freigeben` schreibt die Kopie mit `yaml.safe_dump` aus dem geparsten Dict – YAML-
   Kommentare fallen weg, Flow-Listen werden Blocklisten. Der Prüfer sieht Anforderungen, die nur als Kommentar
   stehen, nicht. Optionen: Rohtext der Datei kopieren und hashen (Dump nur als Rückfall) **oder** im Skill
   `konstruieren` festlegen, dass Anforderungen nie nur als Kommentar stehen. Nutzer fragen.
2. **Fehlalarme in `hinweise`**: `mittellinie.von/bis`, Vollwinkel 360 und `fase.winkel: 45` werden gemeldet;
   jeder Polygonpunkt einzeln. Später `mittellinie` ausnehmen und 360 zulassen.
3. Kleinigkeiten aus dem Gesamt-Review des Nachtrags: `swki freigeben x.freigegeben.yaml` wird nicht abgelehnt;
   `freigeben` gibt den Pfad der Kopie nicht aus; Grenze „Vorzeichenwechsel beim Ebenenversatz → neu bauen“ steht nur
   im Code-Kommentar, nicht in der Wissensdatei.
4. Geparkt aus dem Gesamt-Review von 2a: `swki bauen --lauf N` überschreibt einen bestehenden Lauf; `speichere` ohne
   Prüfung auf den Arbeitsordner; Einheiten der Teilevorlage ungeprüft (wichtig für Rechner B); vom Compiler benutzte
   Namen (`<id>_skizze`, `<id>_senkung`, `achse_x|y|z`) als Feature-IDs nicht verboten; kein Unit-Test für
   `Kontext.verknuepfe`; Notausgang-Skripte können die statische Prüfung gezielt umgehen (Schutz nur vor Versehen).

## Nach Stufe 2
- Abschluss erst, wenn die Referenzen auch auf Rechner B (SOLIDWORKS 2026) bestehen (2b Task 9).
- Danach: Plan für Stufe 3 (Baugruppen, Normteile); Befunde aus S5/S6 (Kollision, `AddComponent5` platziert die
  Bounding-Box-Mitte, `AddMate5`/`CreateMassProperty` obsolet) und S7 (Toolbox nur über Rückfallweg) beachten.
