# Zeichnungsableitung Z1.3 Stufe 1 (Blatt und Ansichten) – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `swki zeichnen <spec>` erzeugt zu einem gebauten Teil eine Zeichnung ohne Maße. Sie hat ein passendes Format
und einen Vorzugsmaßstab, Ansichten nach Projektionsmethode 1 ohne Überlappung im Zeichenfeld und Mittellinien und
Mittelpunktmarken. Schnitt bzw. Einzelheit stehen dort, wo die Spec es verlangt; das Schriftfeld ist über Eigenschaften
gefüllt. Ausgabe sind SLDDRW, PDF und PNG im Laufordner.

**Architecture:**
- Reine Funktionen ohne SolidWorks in `swki/zeichnung/`: `blatt.py` wählt Format und Maßstab, `ansichten.py` wählt die
  Ansichten aus der Spec, `layout.py` ordnet sie an.
- `swki/zeichnung/zeichnen.py` setzt das über COM um (Muster aus Spike Z1.0).
- Die CLI-Gruppe kommt in `swki/zeichnung/befehle.py`.
- Stufe 1 endet mit zwei PDFs (Buchse, Spannplatte), die der Nutzer ansieht. Erst danach wird Stufe 2 (Maßplan und
  Anordnung) geplant.

**Tech Stack:** Python 3, pywin32/COM SolidWorks 2025, pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md` (§2, §5, §6.1, §7, §9 Z1.3 Stufe 1).
Spike: `docs/zeichnungsableitung/spike-z1.md`.
Regeln: `docs/zeichnungsableitung/recherche.md`
- Kap. 2: Formate, Ränder 20/10 mm, Maßstäbe der Vorzugsreihe
- Kap. 3: Projektionsmethode 1, Ansichtswahl, Schnitte

## Global Constraints

- Jeder neue SW-API-Aufruf vorher mit `swki api methode|enum` nachschlagen (Parameterzahl, Enum-Werte verbindlich); in SW 2025
  verfügbar. API in Metern, Spec und Ausgabe in mm.
- Spike-Befunde verbindlich:
  - Teil vor `Create1stAngleViews2`/`CreateDrawViewFromModelView3` mit `OpenDoc6` öffnen.
  - Blatt mit `SetupSheet5(name, papier, swDwgTemplateCustom=12, scale1, scale2, True, blattformat, b, h, "Standard", True)`
    setzen; die Standardvorlage ist US-Letter, 3. Winkel.
  - Leere Dispatch-Argumente mit `callout_leer()`, nie `None`.
  - Nullargumentige COM-Member liefert der dynamische Dispatch beim Zugriff: Prüfung auf `win32com.client.dynamic.CDispatch`.
  - Deutsche Modellansichtsnamen („*Vorderseite“, „*Oben“, „*Links“ …).
- Blattformat in Stufe 1: SW-2025-Kopien `vorlagen/zeichnung_sw2025/a3 - iso.slddrt`, `a4 - iso.slddrt` im Arbeitsordner.
  Die Formate des Nutzers (SW 2026) laden auf Rechner A nicht (Z1.5).
- Formate nur A4 hoch und A3 quer (die Formate des Nutzers: A4, A4 quer, A3 quer); A4 quer wählt Stufe 1 nicht. Ränder
  20 mm links, 10 mm sonst; Schriftfeld rechts unten, Breite 180 mm.
- Vorzugsmaßstäbe: 5:1, 2:1, 1:1, 1:2, 1:5, 1:10, 1:20 (R-Kap. 2 A).
- Projektionsmethode 1: Draufsicht unter der Vorderansicht, Seitenansicht von links rechts neben ihr.
- Nur Dateien im Arbeitsordner schreiben. Live-Tests einzeln mit `tests\live_einzeln.py`, SolidWorks nur nach OK des Nutzers.
- Kein `git push`. Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Langes, dünnes Teil** (Welle 400 × Ø 20): Format A3 quer mit 1:2, nicht A4 mit 1:5; Ansichten im Zeichenfeld
   (Test in Task 2).
2. **Sehr kleines Teil** (Stift 8 × 20): Maßstab 2:1 oder 5:1 statt 1:1 auf A4 (Test in Task 2).
3. **Frästeil mit Bohrungen nur von unten** (`-y`): Die Hauptansicht ist die Seite mit den meisten Features, nicht
   stur „oben“ (Test in Task 3).
4. **Teil ohne Innenkontur:** kein Schnitt (Test in Task 3).
5. **Ansicht ragt ins Schriftfeld:** `layout` verkleinert den Maßstab um eine Stufe oder wechselt das Format, statt
   zu überlappen (Test in Task 4).

---

### Task 1: Konfiguration der Blattformate

**Files:**
- Modify: `swki/konfig.py` (`Rechner`, `lade_rechner`)
- Modify: `config/rechner.yaml` auf Rechner A (nicht im Git): `zeichnung: {A4: …a4 - iso.slddrt, A3quer: …a3 - iso.slddrt}`
- Test: `tests/test_konfig.py`

**Interfaces:**
- Produces: `Rechner.zeichnung: dict[str, Path]` (Schlüssel `A4`, `A4quer`, `A3quer`; Vorgabe `{}`).

- [ ] **Step 1: Failing test** `test_zeichnung_blattformate`: Eine `rechner.yaml` mit `zeichnung: {A4: "C:/x/a4.slddrt"}`
  ergibt `lade_rechner(p).zeichnung == {"A4": Path("C:/x/a4.slddrt")}`; ohne den Schlüssel ist es `{}`.
- [ ] **Step 2: Test laufen lassen.** Erwartet: FAIL (unbekanntes Feld).
- [ ] **Step 3: Implementieren.** Feld `zeichnung: dict[str, Path] = field(default_factory=dict)`, Umwandlung wie bei `dateien`.
  Danach `config/rechner.yaml` auf Rechner A um die zwei Kopien ergänzen.
- [ ] **Step 4: Tests laufen lassen.** Befehl: `.venv\Scripts\python.exe -m pytest tests/test_konfig.py -q`. Erwartet: PASS.
- [ ] **Step 5: Commit** (`swki/konfig.py`, `tests/test_konfig.py`).

### Task 2: Format und Maßstab (`swki/zeichnung/blatt.py`)

**Files:**
- Create: `swki/zeichnung/__init__.py`, `swki/zeichnung/blatt.py`
- Test: `tests/zeichnung/test_blatt.py`

**Interfaces:**
- Produces:
  - `FORMATE: dict[str, tuple[float, float]]` = `{"A4": (210, 297), "A3quer": (420, 297)}`
  - `MASSSTAEBE: list[tuple[int, int]]` (5:1 … 1:20)
  - `zeichenfeld(format) -> tuple[float, float, float, float]` (x0, y0, x1, y1 in mm, ohne Rand)
  - `SCHRIFTFELD_MM = (180, 55)`
  - `waehle(platzbedarf_mm: tuple[float, float]) -> tuple[str, tuple[int, int]]` → (Format, Maßstab)

  `platzbedarf_mm` ist die Größe der angeordneten Ansichten im Maßstab 1:1 samt Rand für Maße (Task 4).

- [ ] **Step 1: Failing tests**
  - `waehle((150, 100)) == ("A4", (1, 1))`
  - `waehle((420, 60)) == ("A3quer", (1, 2))` (Welle)
  - `waehle((30, 25))[1] in ((2, 1), (5, 1))` (Stift)
  - `waehle((2000, 1500))[1] == (1, 10)`

  Die Wahl ist das kleinste Format, dann der größte Maßstab, bei dem der Bedarf ins Zeichenfeld ohne Schriftfeld passt.
  Größer als 1:1 nur, wenn auch der doppelte Bedarf noch auf A4 passt.
- [ ] **Step 2: Test laufen lassen.** Erwartet: FAIL (ImportError).
- [ ] **Step 3: Implementieren.** Freifläche = Zeichenfeld minus Schriftfeld-Rechteck; ein Bedarf passt, wenn er in eines
  der zwei Restrechtecke (über dem Schriftfeld oder links davon) oder in das ganze Feld oberhalb des Schriftfelds passt.
- [ ] **Step 4: Tests laufen lassen.** Befehl: `.venv\Scripts\python.exe -m pytest tests/zeichnung -q`. Erwartet: PASS.
- [ ] **Step 5: Commit.**

### Task 3: Ansichten aus der Spec (`swki/zeichnung/ansichten.py`)

**Files:**
- Create: `swki/zeichnung/ansichten.py`
- Test: `tests/zeichnung/test_ansichten.py` (Specs: `tests/referenz/buchse/buchse.yaml`, `tests/referenz/stil/spannplatte.yaml`
  und kleine Inline-Specs)

**Interfaces:**
- Produces:
  - `@dataclass Ansicht(rolle: str, modellansicht: str, schnitt: bool = False, winkel_grad: float = 0)`, mit
    rolle `haupt|seite|drauf`
  - `waehle_ansichten(spec: dict) -> list[Ansicht]`
  - `ist_drehteil(spec) -> bool`: `verfahren: drehen`, sonst das erste Feature ist `rotation`

- [ ] **Step 1: Failing tests**
  - Buchse (Drehteil, Achse Y, hohl, Bohrungen im Bund):
    - Hauptansicht `*Vorderseite`, `schnitt=True`, `winkel_grad=90` (Achse liegend).
    - Seitenansicht vorhanden, weil Bohrungen außerhalb der Achse liegen.
  - Volle Welle ohne Innenkontur und ohne außermittige Bohrungen: nur Hauptansicht, `schnitt=False`.
  - Spannplatte: Hauptansicht ist die Modellansicht der Seite mit den meisten Features (Flächenanker-Richtung zählen:
    `+y` → `*Oben`), dazu die Vorderansicht.
  - Inline-Platte mit Bohrungen nur auf `-y` → Hauptansicht `*Unten`.

  Mapping Richtung → Modellansicht: `+y` `*Oben`, `-y` `*Unten`, `+z` `*Vorderseite`, `-z` `*Rückseite`, `+x` `*Rechts`,
  `-x` `*Links` (Achsen: vorne → +Z, oben → +Y, rechts → +X, wie Prüfer-Agent).
- [ ] **Step 2: Test laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Implementieren.** Innenkontur für Drehteile:
  - `rotation` mit `schnitt: true`,
  - Polygonpunkt mit u > 0 auf der Innenseite (kleinster Radius > 0) des ersten Profils,
  - oder `bohrung` auf der Achse.

  Für Frästeile: Schnitt nur, wenn eine Tasche oder Bohrung blind von einer Seite kommt, die nicht die Hauptansicht ist.
  Das ist eine Stufe-1-Näherung; Ledger-Ruling, wenn ein Fall unklar ist.
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Commit.**

### Task 4: Anordnung (`swki/zeichnung/layout.py`)

**Files:**
- Create: `swki/zeichnung/layout.py`
- Test: `tests/zeichnung/test_layout.py`

**Interfaces:**
- Consumes: `Ansicht` (Task 3), `waehle`, `zeichenfeld`, `SCHRIFTFELD_MM` (Task 2).
- Produces:
  - `MASSRAND_MM = 25` (Platz um jede Ansicht für Maße der Stufe 2)
  - `@dataclass Platz(rolle, mitte_mm: tuple[float, float], groesse_mm: tuple[float, float])`
  - `anordnen(groessen_1zu1: dict[str, tuple[float, float]]) -> tuple[str, tuple[int, int], list[Platz]]`

  `groessen_1zu1` bildet je Rolle die Umrissgröße der Ansicht in mm bei 1:1 ab (aus SolidWorks nach Probeplatzierung,
  `GetOutline` ÷ Maßstab).

- [ ] **Step 1: Failing tests**
  - Projektionsmethode 1: Draufsicht-Mitte liegt unter der Hauptansicht (gleiches x), Seitenansicht rechts (gleiches y).
  - Keine zwei Rechtecke (Ansicht + MASSRAND) überlappen.
  - Alle liegen im Zeichenfeld und außerhalb des Schriftfelds.
  - Eine Hauptansicht, die bei 1:1 ins Schriftfeld ragen würde, führt zum nächsten Maßstab oder Format (Review Focus 5).
- [ ] **Step 2: Test laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Implementieren.** Bedarf = Summe der Breiten bzw. Höhen der Reihen samt Rand → `waehle` → Lage im
  Restrechteck über bzw. links vom Schriftfeld, zentriert.
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Commit.**

### Task 5: Zeichnen in SolidWorks (`swki/zeichnung/zeichnen.py`, `befehle.py`)

**Files:**
- Create: `swki/zeichnung/zeichnen.py`, `swki/zeichnung/befehle.py`
- Modify: `swki/cli.py` (`_befehlsgruppen`: `swki.zeichnung.befehle`)
- Test: `tests/live/test_live_zeichnen.py` (Marker `sw`), `tests/test_cli.py` (Befehl registriert)

**Interfaces:**
- Consumes: Tasks 1–4; `auftrag_name`, `laeufe`, `lauf_ordner`, `dateiname` (`swki/auftrag.py`); `pruefe_freigabe`,
  `lade_spec`; `verbinde` (`swki/verbindung.py`).
- Produces: `zeichnen(spec_pfad: Path, lauf: int | None = None) -> dict` mit den Schlüsseln `{"zeichnung", "pdf", "png",
  "format", "massstab", "ansichten": [{rolle, name, umriss_mm}], "dauer_s"}`; CLI `swki zeichnen <spec> [--lauf N]`.

- [ ] **Step 1: API nachschlagen** und im Code-Kommentar vermerken:
  - `IView.Angle` (put), `IDrawingDoc.SetupSheet5`
  - `ISheet.SetScale`, `CreateDrawViewFromModelView3`
  - `CreateUnfoldedViewAt3` (Projektionen), `CreateSectionViewAt5`
  - `IModelDocExtension.SetUserPreferenceToggle` mit `swDetailingAutoInsertCenterMarks=189`, `…CenterLines=190`,
    `…CenterMarksForHoles=308` vor dem Erzeugen der Ansichten
  - `IModelDocExtension.CustomPropertyManager("")` + `Add3`
  - `IView.SetDisplayMode4` (verdeckte Kanten aus)
- [ ] **Step 2: Failing tests.** `test_cli.py`: `swki zeichnen --help` liefert Code 0.
  Live-Test `test_zeichnen_buchse_und_spannplatte`:
  - Die Referenz-Auftragskopie wird mit `validieren`, `freigeben`, `bauen` gebaut, dann `zeichnen`.
  - Erwartet:
    - SLDDRW, PDF und PNG existieren.
    - Format und Maßstab wie `anordnen` (Task 4).
    - Buchse mit Schnittansicht.
    - Die Umrisse der Ansichten (`GetOutline`) überlappen nicht und liegen im Zeichenfeld außerhalb des Schriftfelds.
    - Die Teildatei-SHA ist unverändert.
- [ ] **Step 3: Test laufen lassen.** Erwartet: FAIL.
- [ ] **Step 4: Implementieren.** Ablauf:
  1. Teil öffnen.
  2. Zeichnung aus der Standardvorlage anlegen.
  3. `SetupSheet5` mit dem Format aus `Rechner.zeichnung`.
  4. Mittellinien-/Mittelpunkt-Toggles setzen.
  5. Ansichten probeweise bei 1:1 erzeugen und ihre Umrisse messen.
  6. `anordnen` aufrufen.
  7. Blattmaßstab setzen und die Ansichten an die Plätze verschieben (`IView.Position`).
  8. Schnitt über eine Linie durch die Achse wie im Spike.
  9. Eigenschaften setzen: Benennung und Werkstoff aus der Spec; Zeichnungsnummer aus `eigenschaften`, sonst Spec-Name.
  10. `EditRebuild3`.
  11. `SaveAs` SLDDRW und PDF; PNG über `werkzeuge.pdf_seiten` bzw. dieselbe Bibliothek.
  12. Teil schließen.

  Ablage: `<laufordner>/zeichnung/`.
- [ ] **Step 5: Live-Test einzeln laufen lassen** (Nutzer-OK, frisches SolidWorks). Befehl:
  `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_zeichnen.py`. Erwartet: PASS.
- [ ] **Step 6: Commit**, danach beide PNG dem Nutzer zur Durchsicht schicken (Ende Stufe 1). Befunde der Durchsicht gehen
  in den Plan der Stufe 2.

### Task 6: Dokumentation Stufe 1

**Files:** Modify: `docs/zeichnungsableitung/ergebnisse.md` (Stand Stufe 1, Befunde der Durchsicht), Skill
`konstruieren` (ein Absatz: `swki zeichnen`, Stufe 1 ohne Maße), `werkzeuge/__init__.py` nur falls ein Werkzeug entsteht.

- [ ] **Step 1: Texte ergänzen**, Suite ohne SolidWorks: `.venv\Scripts\python.exe -m pytest -q`. Erwartet: alle PASS.
- [ ] **Step 2: Commit.**
