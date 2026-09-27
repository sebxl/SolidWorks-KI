# SolidWorks-KI – Regeln für Claude

Design: docs/superpowers/specs/2026-09-26-solidworks-ki-design.md
Aktueller Plan: docs/superpowers/plans/ – Übergabe zuerst lesen: docs/superpowers/uebergabe-2026-09-27-stufe2.md

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

## Git
- Kein `git push` ohne Rückfrage.
- Erzeugte SolidWorks-Dateien kommen nicht ins Git.

## Tests
- `.venv\Scripts\python.exe -m pytest` (ohne SolidWorks), `… -m sw` (mit geöffnetem SolidWorks).
