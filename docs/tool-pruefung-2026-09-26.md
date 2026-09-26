# Prüfung SolidWorks-Tools für Claude Code (26.09.2026)

Umgebung: Windows 11, SOLIDWORKS 2025, Python 3.14 (C:\Python314), Node.js, kein uv, kein Bun.
Geprüft wurde nur durch Lesen von Code und Metadaten (gh api, PyPI) – nichts installiert oder ausgeführt.

## Ergebnis

| Projekt | Zweck | Urteil |
|---|---|---|
| andrewbartels1/SolidworksMCP-python | SolidWorks steuern (MCP, ~133 Tools) | **installieren mit Auflagen** |
| Lokale API-Hilfe SW 2025 (`sldworksapi.chm`, `swconst.chm`) | API-Signaturen, Enums | **eigenes Nachschlage-Tool daraus bauen** |
| kilwizac/solidworks-api-mcp | API-Doku-Suche (MCP) | technisch sauber, aber keine Lizenz, SW-Version unbekannt, braucht Bun → nur Übergangslösung |
| haunchen/solidworks-mcp | Zeichnungen | später ggf. ergänzend, **nur an 127.0.0.1 binden** (Standard 0.0.0.0:8080 ohne Auth) |
| vespo92/SolidworksMCP-TS | SolidWorks steuern (Node) | Fallback, falls der Python-Server unter SW 2025 scheitert (nicht im Detail geprüft) |
| guoleizhen717/solidworks-api-skill | API-Wissen als Skill | **nicht installieren** – falsche Enums (`swEndCondBlind`=1 statt 0) und Signaturen, halb Tunnelbau-Inhalt |
| zunyiqingfeng-code/skills (solidworks-automation) | Python-COM-Skill | **nicht verwenden** – veraltete Kopie, 21 statt 23 Parameter bei `FeatureExtrusion3`, Stubs |
| wzyn20051216/solidworks-automation-skill | Skill + MCP + C#-Add-in | nicht ohne eigene Prüfung – Add-in mit Adminrechten, Desktop-App mit Auto-Update |
| eyfel/mcp-server-solidworks | Zwischendarstellung + Compiler | **Ideenquelle** – SW 2026 ist *keine* harte Voraussetzung (Neubau gegen 2025-Interop möglich), aber AGPL-3.0, Alpha, C#-EXE + REST ohne Auth auf Port 5000 → Konzepte nachbauen, keinen Code übernehmen (Details unten) |
| alisamsam/Solidworks-MCP | SolidWorks steuern (MCP, 25 Tools) | **nicht verwenden** – `execute_python` führt beliebigen Code per `exec()` aus, keine Masseeigenschaften/Screenshots, `requirements.txt` kaputt, feste englische Ebenennamen, seit 03/2026 inaktiv, API-Key im Repo |

## Konzepte aus eyfel/mcp-server-solidworks (nur nachbauen, kein Code – AGPL)

Architektur: Python-MCP → Python-Compiler → REST localhost:5000 → C#-EXE (.NET 4.8) → COM. Stand 10.09.2026.

1. **Spezifikations-Schema** (`cad-planner/contracts/feature-graph.schema.json`): Knoten-IDs in Bau-Reihenfolge,
   Skizze und Operation getrennt, Parametertabelle, ausdrückliches `VOCABULARY_GAP` statt stillem Weglassen.
2. **Zweistufige Prüfung** (`ir_schema.py`): Struktur vor dem Bau prüfen – bei Fehlern wird nichts ausgeführt.
3. **Kanten-/Flächen-Anker** (`resolver.py`): Kante über Mittelpunkt `near:[x,y,z]` + 0,1 mm Toleranz;
   laute Fehler `REFERENCE_UNRESOLVED` (mit Abstand) bzw. `REFERENCE_AMBIGUOUS`. Stabil bei Neuaufbau, nicht bei Maßänderung.
4. **Fehlermodell** (`compiler.py`): Protokoll pro Knoten, Fehlercode + Schritt, bei Fehler neu im frischen Dokument statt flicken.
5. **Prüfregeln** (`cad-planner/recipe-usage.md` R13–R15, `compare_parts`): Sollvolumen *vor* dem Bau rechnen,
   Spiegel-/Vorzeichenfehler per Koordinaten-Rücklesung, Nicht-Gebautes ausdrücklich melden; Toleranz Volumen/Oberfläche 1 %.
6. **Sprachunabhängige Ebenenwahl** (`SolidWorksService.cs:1028`): erst Name, sonst die ersten drei RefPlanes im Baum.
7. **Bauregeln**: Vorne → +Z, Oben → +Y, Rechts → +X; Schnitt in −Normale; bei Fehler einmal Richtung umkehren.

Bewusst nicht übernehmen: Skizzen ohne Beziehungen/Bemaßung (Werkzeugbau braucht änderbare Skizzen),
Meter in der freigegebenen Spezifikation (dort mm), mitgelieferte Binär-EXE, REST ohne Auth, `close_all` ohne Speichern.

Option für später: `submit_feature_graph` in Testumgebung auf SW 2025 ausprobieren (Neubau aus Quellcode, ca. 1–2 Tage).
Nicht parallel mit SolidworksMCP-python an derselben SolidWorks-Instanz betreiben.

## Offener Punkt: deutsche SolidWorks-Oberfläche

alisamsam scheitert an fest kodierten Ebenennamen („Front Plane“ statt „Ebene vorne“). Beim Test von
SolidworksMCP-python prüfen, ob Skizzen auf Standardebenen in der deutschen Lokalisierung funktionieren.

## Auflagen für SolidworksMCP-python

1. Auf festen Commit pinnen (Stand 23.09.2026), nur `pip install -e .` – keine Extras `[ui,rag,vision]`.
2. UI-/Agenten-Schicht nicht starten; in der Server-Umgebung keine `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GH_TOKEN`
   (`server.py:347` legt sonst einen OpenAI-Agenten an).
3. In Claude Code per `deny` sperren: `execute_macro`, `batch_execute_macros`, `pack_and_go_assembly`
   (löscht Zielordner per `rmtree`), `batch_file_operations`, `execute_workflow`, `batch_process_files`.
4. Export/Screenshot/SaveAs überschreiben ohne Nachfrage → nur in eigenem Arbeits-/Ausgabeordner mit Kopien arbeiten.
5. Server außerhalb dieses Projekts ablegen und per absolutem Pfad einbinden (Repo bringt eigene `CLAUDE.md`,
   `.claude/skills` und `.mcp.json` mit), Start mit `--real --year 2025`.
6. Erst mit einem Testteil prüfen, ob Skizze, Extrusion, Feature-Baum, Masseeigenschaften und Export unter SW 2025 laufen
   (Autor testet live vor allem mit SW 2026). Rund 40 Tools sind im pywin32-Adapter nicht implementiert.
