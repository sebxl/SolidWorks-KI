---
name: compiler-erweitern
description: Erweitert den swki-Compiler um einen Handler oder eine Handler-Option. Von Claude selbst auszulösen, wenn (a) eine Lücke zum zweiten Mal auftritt und ein bestandenes Notausgang-Skript existiert, (b) einem Handler eine Option fehlt oder (c) ein Handler wiederholt am selben Fehler scheitert.
---

# Compiler erweitern

Neue Feature-Typen laufen beim ersten Mal immer über den Notausgang (`typ: skript`). Erst danach wird erweitert.

## Ablauf
1. **Anlass festhalten**: welcher Auftrag, welches Skript bzw. welcher Fehlercode, welcher Handler.
2. **API nachschlagen**: jeden neuen Aufruf mit `swki api methode <Interface.Member>` / `swki api enum <Name>`;
   Muster aus `swki/wissen/pywin32-fallstricke.md` beachten (Late Binding: nullargumentige Member ohne `()`,
   `callout_leer()`, `r8_array()`, `byref_*`).
3. **Test zuerst**:
   - Schema/Validierung: Unit-Test unter `tests/spec/`.
   - Handler: Live-Test mit Minimalteil unter `tests/live/` (Marker `sw`), Erwartung über Volumen/Hüllquader/Achsen.
   Test laufen lassen und scheitern sehen.
4. **Umsetzen**: Schema (`schema/teil.schema.json`) und Handler (`swki/compiler/handler/`) – kleinste Änderung.
5. **Absichern** (alles muss bestehen, sonst Änderung verwerfen: `git restore` der eigenen Dateien):
   - `.venv\Scripts\python.exe -m pytest`
   - `.venv\Scripts\python.exe -m pytest -m sw`
   - Regressions-Suite `.venv\Scripts\python.exe -m pytest -m sw tests/referenz`
   - `.venv\Scripts\python.exe -m swki api pruefe-code` (nur API-Aufrufe aus SW 2025)
6. **Commit**: eigener lokaler Commit je Änderung, Message `compiler: <was>` mit Trailer
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Kein Push ohne Rückfrage.
7. **Spezifikation umstellen**: den Notausgang im auslösenden Auftrag durch den neuen Typ ersetzen (Bauweg-Änderung,
   keine neue Freigabe nötig) und neu bauen. Der Bericht listet die Compiler-Änderung automatisch (`swki bericht`).
