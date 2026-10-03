# SolidWorks-KI – Regeln für Claude

Design: docs/superpowers/specs/2026-09-26-solidworks-ki-design.md
Stand: Stufe 3b (Baugruppen statisch) umgesetzt – Ergebnisse: docs/stufe3b/ergebnisse.md. Nächster Schritt: Stufe 4 (mechanische Abläufe): Brainstorming → Spec → Plan.

## Umgebung
- Python immer über `.venv\Scripts\python.exe`, swki über `.venv\Scripts\python.exe -m swki …` (Ausgabe JSON).
- SolidWorks-Version und Pfade stehen in `config/rechner.yaml` (pro Rechner, nicht im Git). Nie ein Jahr oder einen Pfad fest in Code schreiben.
- Einrichten eines Rechners: `powershell -ExecutionPolicy Bypass -File setup\einrichten.ps1`.

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

## Prüfen und Nachbessern (Stufe 2)
- Ablauf komplett im Skill `konstruieren`: `swki bauen` → `swki pruefen <spec>` → Prüfer-Agent `pruefer` (nur Eingabe,
  freigegebene Spezifikation, Prüfbericht, Screenshots) → Urteil unverändert (nur das JSON-Objekt, ohne Code-Fences) nach
  `protokolle/<spec>.lauf-<n>.pruefer.json` → `swki status <spec>` → nachbessern oder `swki bericht <spec>`.
- `swki pruefen` prüft Normbohrungen gegen die freigegebene Kopie (Größen sind Text, die Prüfsumme schützt sie nicht).
- Wiederholt sich eine Lücke oder ein Handlerfehler: Skill `compiler-erweitern` (Test zuerst, Regressions-Suite).
- Regressions-Suite: `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz` (SolidWorks geöffnet).

## Git
- Kein `git push` ohne Rückfrage.
- Erzeugte SolidWorks-Dateien kommen nicht ins Git.

## Tests
- `.venv\Scripts\python.exe -m pytest` (ohne SolidWorks), `… -m sw` (mit geöffnetem SolidWorks).
