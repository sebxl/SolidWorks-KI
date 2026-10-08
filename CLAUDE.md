# SolidWorks-KI – Regeln für Claude

Design: docs/superpowers/specs/2026-09-26-solidworks-ki-design.md
Stand: Paket Formschräge (Option an Extrusion und Schnitt) umgesetzt – Ergebnisse: docs/formschraege/ergebnisse.md
(davor 3c: docs/stufe3c/ergebnisse.md). Nächste Schritte zur Wahl: Stufe 4c (Nut- und Kurvenverknüpfung), Paket
„Messarten“ (Fasen, Gewinde durch, Lagerachse), Paket Speicher.

## Umgebung
- Python immer über `.venv\Scripts\python.exe`, swki über `.venv\Scripts\python.exe -m swki …` (Ausgabe JSON).
- SolidWorks-Version und Pfade stehen in `config/rechner.yaml` (pro Rechner, nicht im Git). Nie ein Jahr oder einen Pfad fest in Code schreiben.
  Pfade für Auftragsskripte ebenfalls dort: `blender`, `dateien: {<name>: <pfad>}`.
- Einrichten eines Rechners: `powershell -ExecutionPolicy Bypass -File setup\einrichten.ps1`.
- Werkzeuge (SolidWorks-Neustart, Live-Tests auf frischem SolidWorks, Teil-Diagnose, STL-Hüllquader, Kaufteil-Vorprüfung):
  `werkzeuge/` (Übersicht in `werkzeuge/__init__.py`, Aufruf `-m werkzeuge.<name>`). Ein Hilfsskript, das wiederkommt,
  dorthin übernehmen; Scratch ist Wegwerf. `*.py` in `auftraege/` ist versioniert, der Rest dort bleibt Arbeitsstand.

## SolidWorks
- Gebaut wird nur über `swki` bzw. Spikes/Skripte dieses Repos. Das MCP `solidworks-mcp` dient nur zum Ansehen (Feature-Baum, Masseeigenschaften).
- Vor jedem neuen SolidWorks-API-Aufruf im Code: `swki api methode <Interface.Member>` bzw. `swki api enum <Name>` nachschlagen. Nicht raten. Parameteranzahl und Enum-Werte aus dem Index sind verbindlich.
- Die API rechnet in Metern und Radiant. Spezifikationen und Ausgaben an den Nutzer in mm und Grad.
- Die Oberfläche ist deutsch: keine englischen Feature-/Ebenennamen verwenden; Ebenen über Position im Feature-Baum finden.
- Nur Dokumente anfassen, die selbst angelegt wurden. Nur im Arbeitsordner speichern (`arbeitsordner` aus `config/rechner.yaml`). Nie in Kundenordner oder Bibliotheks-Originale schreiben.
- Normteile: `swki normteil` kopiert selbst gebaute und geprüfte Teile in die `normteilbibliothek` (config/rechner.yaml) – sonst nichts dorthin schreiben.
- Compiler-Code nur mit API-Aufrufen, die in SW 2025 verfügbar sind (`swki api pruefe-code`).

## Konstruieren (Stufe 2)
- Spezifikation eines Teils: YAML nach `schema/teil.schema.json` im Auftragsordner (`auftraege/<auftrag>/`).
- `swki validieren <spec>` → `swki freigeben <spec>` (nur nach ausdrücklichem OK des Nutzers) → `swki bauen <spec>`.
- Anforderungsmaße als `parameter` führen; `validieren` meldet feste Zahlen in Features als `hinweise` (die Freigabe
  schützt sie nicht). `freigeben` legt `<spec>.freigegeben.yaml` ab – diese Kopie nie ändern.
- Nach der Freigabe nur noch den Bauweg ändern (Features, Anker, Reihenfolge, Skripte); Parameter, Material, Eigenschaften und
  `pruefung` sind tabu (`swki bauen` verweigert sonst mit FREIGABE_VERALTET).
- Was das Format nicht kann: `typ: skript` mit `luecke:` (Notausgang), nie still weglassen.
- Normbohrungen (`typ: normbohrung`) nur in Größen aus `swki/wissen/bohrungsnormen.yaml`; die Tabelle nur um Größen
  erweitern, die live gemessen sind (Muster: Spike S10, `spikes/s10_f3_normmasse.py`).
- Kompakter Feature-Baum: Modellierregeln im Skill `konstruieren`; `validieren` meldet Zusammenfassbares als
  `hinweise` mit `art: zusammenfassen`.
- Live-Tests einzeln mit Zeitlimit: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> …`.

## Normteile (Stufe 3a)
- Genormte Teile immer über `swki normteil hole` (Skill `normteile`), nie als STEP-Download oder freihändig konstruiert. Herstellerdaten nur für nicht genormte Kaufteile.
- Normtabellen (`swki/wissen/normteile/`) nur mit Abgleich erweitern: ≥ 2 unabhängige recherchierte Quellen je Wert; Widersprüche sperren und den Nutzer fragen.
- Bauvorlagen nur mit neuem Prüfer-Urteil (`swki normteil muster` → Prüfer → `swki normteil urteil`).

## Kaufteile (Stufe 3c)
- Nicht genormte Kaufteile über den Skill `kaufteile`: nur STEP, die Datei des Nutzers nur lesen (swki kopiert sie
  unverändert in den Quellordner der `kaufteilbibliothek`); keine Konten bei Herstellerportalen, keine Anmeldung.
  Downloads von Herstellerdateien nur öffentliche Direktlinks ohne Konto und nur mit ausdrücklichem OK des Nutzers je Datei
  (Name, Quelle, Größe nennen).
- Katalogeintrag `swki/wissen/kaufteile/<hersteller>/<bestellnummer>.yaml` (`art: kaufteil`): Kennmaße mit Beleg
  (Herstellerquelle oder Nutzer allein, Händler nur mit ≥ 2 Domains; Werte aus der STEP sind nie Kennmaße);
  `swki validieren` → Nutzer-OK → `swki freigeben` → `swki kaufteil muster` → Prüfer → `swki kaufteil urteil` →
  `swki kaufteil hole`.
- In die `kaufteilbibliothek` schreibt nur `swki kaufteil` (Quellordner nur Kopien, Cache je SW-Jahr). Importierte Geometrie
  nie reparieren, vereinfachen oder verschieben.
- Baugruppen: `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}`, Referenzen nur `EINBAU_*` und Gewindepositionen; die
  Baugruppen-Freigabe schützt den Eintrag mit (`FREIGABE_VERALTET` nennt das Kaufteil).
- Regressions-Suite enthält den Motorhalter mit Nanotec GPLE60-2S-32 (`tests/referenz/motorhalter/`). Die
  Herstellerdatei liegt nur im Quellordner der `kaufteilbibliothek`; fehlt sie, meldet die Regression
  `KAUFTEIL_QUELLE_FEHLT` mit der Download-URL (Nutzer fragen, dann `swki kaufteil untersuchen`). Speicher: Motorhalter
  Spitzen ~9,1–9,3 GB; Live-Läufe mit Kaufteilen wie Baugruppen je Test auf frischem SolidWorks.

## Baugruppen (Stufe 3b)
- Baugruppen über den Skill `baugruppe`: Baugruppen-Spec nach `schema/baugruppe.schema.json` und Teil-Specs im selben
  Auftragsordner; **eine** Freigabe (`swki freigeben <baugruppe.yaml>`) für alles. Verknüpfungen sind Bauweg.
- Normteile kommen über `swki normteil hole` und werden in den Lauf-Ordner kopiert; die Baugruppe verweist nie auf die
  Bibliothek.
- Die Spec ist die Quelle: `MANUELL_GEAENDERT` heißt, jemand hat gebaute Dateien geändert → `swki aenderungen`, Nutzer
  fragen: übernehmen → Spec ändern, validieren, Nutzer-OK, `swki freigeben`, dann `swki bauen --uebernommen` (nur mit
  Freigabe, die neuer als der Lauf ist); verwerfen → `swki bauen --verwerfen` nur auf ausdrückliche Anweisung. Gilt auch
  für Einzelteile.
- Regressions-Suite enthält das Stehlager (`tests/referenz/stehlager/`).

## Bewegungen (Stufe 4a)
- Bewegliche Komponenten: Grenzverknüpfung (`grenze_abstand`/`grenze_winkel`, bewegt wird Seite `a`, `min`/`max` als
  Parameter), `freiheitsgrade: 1`, eine Bewegung je Grenze; Scharnier mit Anlage. Regeln im Skill `baugruppe` (§6).
- `swki pruefen` prüft die Bewegungen mit; `SPEICHER_KNAPP` → SolidWorks selbst neu starten und erneut prüfen.
- Vor jedem Live-Lauf mit Bewegungen SolidWorks frisch starten (Spitzen bis ~11 GB Private Bytes: Stehlager 10,8 GB, Schlitten 9,9–10,2 GB; die Abfrage vor jedem Lauf sieht nur das Dauerniveau); `speicher_grenze_mb` 10000.
- Regressions-Suite enthält den Linearschlitten (`tests/referenz/schlitten/`).

## Verzahnung und Kopplungen (Stufe 4b)
- Zahnräder und Zahnstangen nur als `typ: verzahnung` (Evolvente, Bezugsprofil DIN 867, Modul DIN 780 Reihe 1,
  `zahndickenabmass` < 0); Regeln im Skill `konstruieren`. Die Modultabelle (`swki/wissen/module_din780.yaml`) nur mit
  Abgleich (≥ 2 Quellen) erweitern.
- Kopplungen `zahnrad`/`zahnstange` über den Skill `baugruppe` §7: Seite a `gekoppelt`, Kopplungen zuletzt, Endlagen der
  gekoppelten Wellen mit `pi`, Drehsinn aus der Geometrie.
- Regressions-Suite enthält den Zahnstangentrieb und seine Teile (`tests/referenz/zahnstangentrieb/`); Live-Läufe mit
  Kopplungen wie Bewegungen je Test auf frischem SolidWorks. Speicher: Zahnstangentrieb Spitzen ~9,8–10,3 GB (über
  `speicher_grenze_mb` 10000, ohne `SPEICHER_KNAPP`, weil die Abfrage nur das Dauerniveau sieht).

## Formschräge (Paket Formschräge)
- Schräge Wände nur als `formschraege` im `ende` von `extrusion`/`schnitt` (Regeln im Skill `konstruieren`): Winkel als
  Parameter, Richtung `kleiner`/`groesser` aus Sicht der Skizze. `swki pruefen` misst sie gegen die freigegebene Kopie.
- Ein eigenes Feature für Formschrägen an beliebigen Flächen (`InsertMultiFaceDraft`) gibt es nicht; erst bei Bedarf über
  den Skill `compiler-erweitern`.
- Regressions-Suite enthält die Zentrieraufnahme (`tests/referenz/zentrieraufnahme/`).

## Prüfen und Nachbessern (Stufe 2)
- Ablauf komplett im Skill `konstruieren`: `swki bauen` → `swki pruefen <spec>` → Prüfer-Agent `pruefer` (nur Eingabe,
  freigegebene Spezifikation, Prüfbericht, Screenshots) → Urteil unverändert (nur das JSON-Objekt, ohne Code-Fences) nach
  `protokolle/<spec>.lauf-<n>.pruefer.json` → `swki status <spec>` → nachbessern oder `swki bericht <spec>`.
- `swki pruefen` prüft Normbohrungen gegen die freigegebene Kopie (Größen sind Text, die Prüfsumme schützt sie nicht).
- Wiederholt sich eine Lücke oder ein Handlerfehler: Skill `compiler-erweitern` (Test zuerst, Regressions-Suite).
- Regressions-Suite: `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz` (SolidWorks geöffnet).

## Git
- Kein `git push` ohne Rückfrage.
- Erzeugte SolidWorks-Dateien kommen nicht ins Git (einzige Ausnahme: Test-STEP
  `tests/referenz/motorhalter/muster/gm42-10.step`, interne Testdatei). Herstellerdateien (STEP, Datenblätter) nie ins Git.

## Tests
- `.venv\Scripts\python.exe -m pytest` (ohne SolidWorks), `… -m sw` (mit geöffnetem SolidWorks).
