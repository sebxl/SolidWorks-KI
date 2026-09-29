# SolidWorks-KI – Regeln für Claude

Design: docs/superpowers/specs/2026-09-26-solidworks-ki-design.md
Aktueller Plan: docs/superpowers/plans/ – Übergabe zuerst lesen: docs/superpowers/uebergabe-2026-09-29-stufe2c.md

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
- Compiler-Code nur mit API-Aufrufen, die in SW 2025 verfügbar sind (`swki api pruefe-code`).

## Konstruieren (Stufe 2)
- Spezifikation eines Teils: YAML nach `schema/teil.schema.json` im Auftragsordner (`auftraege/<auftrag>/`).
- `swki validieren <spec>` → `swki freigeben <spec>` (nur nach ausdrücklichem OK des Nutzers) → `swki bauen <spec>`.
- Anforderungsmaße als `parameter` führen; `validieren` meldet feste Zahlen in Features als `hinweise` (die Freigabe
  schützt sie nicht). `freigeben` legt `<spec>.freigegeben.yaml` ab – diese Kopie nie ändern.
- Nach der Freigabe nur noch den Bauweg ändern (Features, Anker, Reihenfolge, Skripte); Parameter, Material, Eigenschaften und
  `pruefung` sind tabu (`swki bauen` verweigert sonst mit FREIGABE_VERALTET).
- Was das Format nicht kann: `typ: skript` mit `luecke:` (Notausgang), nie still weglassen.
- Live-Tests einzeln mit Zeitlimit: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> …`.

## Prüfen und Nachbessern (Stufe 2)
- Ablauf komplett im Skill `konstruieren`: `swki bauen` → `swki pruefen <spec>` → Prüfer-Agent `pruefer` (nur Eingabe,
  freigegebene Spezifikation, Prüfbericht, Screenshots) → Urteil unverändert (nur das JSON-Objekt, ohne Code-Fences) nach
  `protokolle/<spec>.lauf-<n>.pruefer.json` → `swki status <spec>` → nachbessern oder `swki bericht <spec>`.
- Wiederholt sich eine Lücke oder ein Handlerfehler: Skill `compiler-erweitern` (Test zuerst, Regressions-Suite).
- Regressions-Suite: `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz` (SolidWorks geöffnet).

## Git
- Kein `git push` ohne Rückfrage.
- Erzeugte SolidWorks-Dateien kommen nicht ins Git.

## Tests
- `.venv\Scripts\python.exe -m pytest` (ohne SolidWorks), `… -m sw` (mit geöffnetem SolidWorks).
