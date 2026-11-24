# Zeichnungsableitung Z1.3 Stufe 2 (Maßplan, Ansichten nach Maßbedarf, Maßanordnung) – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `swki zeichnen` bemaßt das Teil.
- Jedes Merkmal bekommt genau ein Maß aus dem Maßplan.
- Jedes Maß sitzt in einer Ansicht, in der es in wahrer Größe darstellbar ist.
- Keine Ansicht trägt mehr als `max_masse_je_ansicht` Maße.
- Fehlende Darstellbarkeit oder volle Ansichten führen zu weiteren Ansichten; meist sind es 3–4 (Nutzer 17.11.2026).
- Die Maße stehen ohne Überlappung im Maßrand.
- Ergebnis sind zwei PDFs (Buchse, Spannplatte) zur Durchsicht.

**Architecture:**
- Der Maßplan entsteht ohne SolidWorks in `swki/zeichnung/massplan.py`:
  - Frästeile übernehmen die protokollierten Anforderungsmaße (`protokoll.json`, `knoten[].masse`) als Quelle `modell`.
  - Drehteile bekommen Durchmesser und Längen ab einer Bezugsplanfläche, berechnet aus dem Rotationsprofil, als
    Quelle `neu`.
- Die Zuordnung Maß → Ansicht mit Obergrenze und Bedarf an weiteren Ansichten rechnet `swki/zeichnung/zuordnung.py`.
- `zeichnen.py` setzt das um:
  1. Ansichten-Grundsatz erzeugen.
  2. Modellmaße mit `InsertModelAnnotations4` (`HiddenFeatureDims=True`, Spike Z1.0) in alle Ansichten einfügen.
  3. Den Kandidatensatz je Maß aus den tatsächlich eingefügten Anzeigemaßen lesen.
  4. Zuordnen, Duplikate und Nicht-Plan-Maße löschen, bei Bedarf Ansichten ergänzen.
  5. Neue Maße über Kanten setzen und die Maße anordnen.

**Tech Stack:** Python 3, pywin32/COM SolidWorks 2025, pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md`
- §6.1: Ansichten nach Maßbedarf, Fassung vom 17.11.
- §6.2: Maßplan aus der Spec.

Vorstufe: Plan `2026-11-17-zeichnungsableitung-z13-stufe1.md`, Ergebnisse `docs/zeichnungsableitung/ergebnisse.md`.
Regeln: `docs/zeichnungsableitung/recherche.md` Kap. 4 (ISO 129-1) und Kap. 8 (fertigungsgerecht).

**Nicht in Stufe 2:**
- Bohrungsangaben und Gewinde als Angabe (Stufe 3).
- Toleranzen, Passungen und Sammelangaben (Stufe 4).
- Schnitt im Frästeil.
- Einzelheit.

## Global Constraints

- SW-API vor Gebrauch mit `swki api methode|enum` nachschlagen; verbindliche Live-Befunde aus Stufe 1 (`spike-z1.md`,
  Korrektur):
  - Skizzen in Ansichten in Ansichtskoordinaten (`_in_ansicht`).
  - `IView.Position` als double-Array.
  - Maßstab je Ansicht setzen.
  - `callout_leer()` statt `None`.
- Je Merkmal genau ein Maß, je Richtung ein Bezug, keine geschlossene Kette (R-Kap. 4/8 A).
- Drehteile: Ø statt Radius, Längen von einer Bezugsplanfläche.
- `max_masse_je_ansicht` aus `config/standard.yaml` (`zeichnung.max_masse_je_ansicht: 12`, selbst entschieden, Design §6.1).
- Ansichten: Frästeil-Grundsatz Haupt + Drauf + Seite (3); Drehteil Längsschnitt (oder Hauptansicht) + Stirnansicht.
  Weitere Projektionen nur bei Bedarf, ohne eigenes Maß entfällt eine Ansicht (außer der Hauptansicht).
- Nichts still weglassen: Maße ohne Ansicht und überfüllte Ansichten erscheinen in `meldungen`.
- Teildatei bleibt unverändert (SHA, wie Stufe 1); Modellmaße werden nur in der Zeichnung gelöscht, nie im Teil.
- Live-Tests einzeln (`tests\live_einzeln.py`), SolidWorks nur nach OK des Nutzers. Kein `git push`. Commits mit
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Frästeil mit vielen Bohrungen und Taschen von oben:** Die Draufsicht läuft über, Maße wandern in die
   Vorder-/Seitenansicht, wo sie darstellbar sind, oder lösen eine Meldung aus. Keine Ansicht trägt mehr als die
   Obergrenze (Test Task 3).
2. **Hilfsebenen- und Konstruktionsmaße** (`versatz`, `konstruktion`, Mittellinien, Normbohrungs-Interna) kommen nie
   auf die Zeichnung (Test Task 1).
3. **Drehteil mit Fasen und Einstichen:** Jeder Absatz-Ø genau einmal, Längen alle von derselben Bezugsfläche,
   keine Kette (Test Task 2).
4. **Ein Plan-Maß taucht in keiner Ansicht auf:** Meldung statt stiller Lücke (Test Task 3 und Live).
5. **Muster/Spiegeln:** Das Musterabstand-Maß ist ein Maß; gespiegelte Taschen werden nicht doppelt bemaßt (Test Task 1).

---

### Task 1: Maßplan für Frästeile aus dem Maßprotokoll (`massplan.py`)

**Files:**
- Create: `swki/zeichnung/massplan.py`
- Create: `tests/zeichnung/daten/spannplatte.protokoll.json` (aus dem Live-Lauf Z1SPIKE-stil, nur `knoten[].id`/`masse`)
- Test: `tests/zeichnung/test_massplan.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Mass(id: str, quelle: str, art: str, wert: float, merkmal: str, name: str | None = None,
    geometrie: dict | None = None)`:
    - `quelle`: `modell|neu`.
    - `art`: `laenge|durchmesser|radius|tiefe|lage|abstand|winkel|fase`.
    - `name`: SolidWorks-Maßname ohne Dokumentteil, z. B. `D3@t1_skizze`.
    - `geometrie`: nur bei `neu`.
  - `massplan_fraesteil(spec: dict, protokoll: dict) -> list[Mass]`
  - `WEG_ARTEN = {"versatz", "konstruktion", "skript"}`

- [ ] **Step 1: Failing tests** mit dem Spannplatten-Protokoll:
  - enthalten: `D1@f1_skizze` (200), `D2@f1_skizze` (120), `D1@f1` (20), `D3@t1_skizze` (lage, 20), `D1@t1`
    (tiefe 12), `D1@r1` (radius 4), `D1@g1_positionen` (40), `D2@g1_positionen` (20), `D3@m1` (abstand 30),
    `D1@st_positionen` (150), `D2@st_positionen` (20).
  - ausgeschlossen:
    - `D1@Ebene1`, `D1@Ebene2` (versatz)
    - `D1@st_fase` (Bohrungsfase → Stufe 3)
    - jedes Maß mit `mittellinie` im `pfad`
  - je `name` genau ein `Mass`; `merkmal` = Knoten-ID (`t1`, `g1` …).
  - Inline-Protokoll mit `art: konstruktion` → nicht enthalten.
- [ ] **Step 2: Test laufen lassen.** Erwartet: FAIL (ImportError).
- [ ] **Step 3: Implementieren.** Art-Abbildung: `groesse` → `laenge`, sonst die Protokoll-Art; Winkel in Grad.
  Bohrungsfasen (`pfad` endet auf `.fase`) und `pfad` mit `mittellinie` weglassen.
- [ ] **Step 4: Tests laufen lassen.** `.venv\Scripts\python.exe -m pytest tests/zeichnung -q` → PASS.
- [ ] **Step 5: Commit.**

### Task 2: Maßplan für Drehteile aus dem Profil (`massplan.py`)

**Files:**
- Modify: `swki/zeichnung/massplan.py`
- Test: `tests/zeichnung/test_massplan.py` (Buchse aus `tests/referenz/buchse/buchse.yaml`, Inline-Wellen)

**Interfaces:**
- Consumes: `_radien`/Achslage-Logik aus `ansichten.py` (Achse u/v, Radius quer dazu). Gemeinsame Hilfe dorthin ziehen,
  nicht kopieren.
- Produces: `massplan_drehteil(spec: dict) -> list[Mass]`, alle mit `quelle="neu"`:
  - `art="durchmesser"`, `geometrie={"radius": r, "achse_von": a0, "achse_bis": a1}`, Bereich auf der Achse für die
    Kantenwahl.
  - `art="laenge"`, `geometrie={"von": a_bezug, "bis": a}`: Lagen auf der Achse in mm, Modellkoordinate entlang der
    Achse.

  `massplan(spec, protokoll) -> list[Mass]` verteilt nach `ist_drehteil`. Rotation-Fasen (`typ: fase`) übernimmt der
  Drehteil-Plan aus dem Protokoll als `art="fase"` (`D1@f2`).

- [ ] **Step 1: Failing tests (Buchse)**
  - Außen-Ø 50 (Bund), 32 (Schaft), innen Ø 20, je genau einmal.
  - Längen ab der Bezugsfläche = Bundanlage-Stirnfläche bei Achslage 0: 8 (Bund) und 60 (Gesamt), Nut-Lage 40 und
    -breite 3, alle mit `von` = 0, keine Kette.
  - Nut-Grund-Ø 30 (Rotationsschnitt f4).
  - Fasen `D1@f2` (1), `D1@f3` (0,5) als `fase`.
  - Keine Maße aus `D*@f1_skizze`.
  - Bezugsfläche: `bezuege.A` der Spec, wenn sie eine Stirnfläche ist; sonst die Stirnfläche mit dem größten Ø
    (Anlage), bei Gleichstand die bei der kleinsten Achslage. Ledger-Ruling, wenn ein Fall unklar ist.
- [ ] **Step 2: Test laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Implementieren.**
  - Profilpunkte des ersten Rotationsprofils und der Rotationsschnitte → Absätze (Radius-Stufen) und Achslagen.
  - Ø je eindeutigem Radius > 0 mit Achsbereich.
  - Längen = je eindeutige Achslage ≠ Bezug, Abstand zum Bezug.
  - Schnittprofile (Einstiche): Lage zum Bezug, Breite, Grund-Ø.
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Commit.**

### Task 3: Zuordnung Maß → Ansicht (`zuordnung.py`)

**Files:**
- Create: `swki/zeichnung/zuordnung.py`
- Modify: `config/standard.yaml` (`zeichnung: {max_masse_je_ansicht: 12}`)
- Test: `tests/zeichnung/test_zuordnung.py`

**Interfaces:**
- Produces:
  - `@dataclass Zuordnung(je_ansicht: dict[str, list[str]], ohne_ansicht: list[str], weitere_ansicht: bool, meldungen: list[str])`
  - `ordne_zu(kandidaten: dict[str, list[str]], ansichten: list[str], max_je_ansicht: int) -> Zuordnung`:
    - `kandidaten` bildet je Maß-ID die Rollen ab, in denen das Maß darstellbar ist.
    - `ansichten` ist die Vorrang-Reihenfolge, Hauptansicht zuerst.

- [ ] **Step 1: Failing tests**
  - Jedes Maß genau einer seiner Kandidaten-Ansichten zugeordnet.
  - Maße mit nur einem Kandidaten zuerst; danach in die Ansicht mit den wenigsten Maßen, bei Gleichstand nach Vorrang.
  - Keine Ansicht über `max_je_ansicht`. Passt ein Maß nirgends mehr: `weitere_ansicht=True` und eine Meldung mit der ID.
  - Ein Maß ohne Kandidaten landet in `ohne_ansicht` mit Meldung.
  - Ansichten ohne Maß stehen in `je_ansicht` mit leerer Liste.
  - Beispiel: 15 Maße nur in `haupt`, Obergrenze 12 → 12 in `haupt`, 3 Meldungen, `weitere_ansicht=True`.
  - Beispiel: 15 Maße in `haupt`/`drauf` → Verteilung 8/7.
- [ ] **Step 2: Test laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Implementieren** (gierig, deterministisch nach Maß-ID sortiert).
  `lade_standard()["zeichnung"]["max_masse_je_ansicht"]`, Vorgabe 12, wenn der Schlüssel fehlt.
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Commit.**

### Task 4: Ansichten-Grundsatz und Schriftfeld-Kurzname (`ansichten.py`, `zeichnen.py`)

**Files:**
- Modify: `swki/zeichnung/ansichten.py`
  - Frästeil immer haupt + drauf + seite.
  - Funktion `weitere_rollen(spec) -> list[str]` = zusätzliche Projektionen in Reihenfolge: `seite_rechts` (links
    projiziert), `unter` (oberhalb projiziert).
- Modify: `swki/zeichnung/zeichnen.py`
  - Zeichnung und PDF unter `zeichnungsname(spec)` speichern.
  - `zeichnungsname(spec) -> str` = `eigenschaften.Zeichnungsnummer`, sonst `spec["name"]`.
- Modify: `swki/zeichnung/layout.py`: Rollen `seite_rechts` (links der Hauptansicht) und `unter` (über der Hauptansicht).
- Test: `tests/zeichnung/test_ansichten.py`, `test_layout.py`, `test_zeichnen_ohne_sw.py`

- [ ] **Step 1: Failing tests**
  - Spannplatte → Rollen `haupt`, `drauf`, `seite`.
  - `weitere_rollen` liefert für ein Frästeil `["seite_rechts", "unter"]`, für ein Drehteil `[]`.
  - `anordnen` mit `seite_rechts` → links der Hauptansicht, gleiche Höhe; mit `unter` → über der Hauptansicht,
    gleiches x; keine Überlappung.
  - `zeichnungsname({"name": "Buchse"}) == "Buchse"`; mit `eigenschaften.Zeichnungsnummer` diese.
  - Bisherige Tests angepasst (Spannplatte hatte haupt + drauf).
- [ ] **Step 2: Test laufen lassen.** Erwartet: FAIL.
- [ ] **Step 3: Implementieren.**
- [ ] **Step 4: Tests laufen lassen.** Erwartet: PASS.
- [ ] **Step 5: Commit.**

### Task 5: Maße in der Zeichnung (`zeichnen.py`, `bemassen.py`)

**Files:**
- Create: `swki/zeichnung/bemassen.py` (COM-Teil der Bemaßung)
- Modify: `swki/zeichnung/zeichnen.py` (Ablauf)
- Test: `tests/zeichnung/test_zeichnen_ohne_sw.py` (Fake-COM für den Ablauf), `tests/live/test_live_zeichnen.py`

**Interfaces:**
- Consumes: `massplan`, `ordne_zu`, `weitere_rollen`, `anordnen`.
- Produces:
  - `modellmasse_einfuegen(drw, views) -> dict[str, list]`: Rolle → Anzeigemaße. Ablauf: `SelectByID2` DRAWINGVIEW,
    `ActivateView`, `InsertModelAnnotations4(0, 32768, True, False, True, False, False, False)`.
  - `kandidaten(anzeige: dict[str, list], plan: list[Mass]) -> dict[str, list[str]]`: Abgleich über
    `FullName` ohne `@<Dokument>`.
  - `loesche_ausser(drw, anzeige, behalten: dict[str, list[str]]) -> int`: über `IAnnotation.Select3(True, callout_leer())`
    + `IModelDoc2.EditDelete`.
  - `setze_neu(drw, view, mass: Mass) -> bool`: Kanten über `GetVisibleEntities2(callout_leer(), 1)`.
    - Ø: zwei Linienkanten parallel zur Achse im Abstand ±r. Danach `AddDimension2` und Präfix Ø per
      `SetText(swDimensionTextPrefix=1, "<MOD-DIAM>")`; vorher prüfen, ob SolidWorks Ø selbst setzt.
    - Länge: zwei Kanten senkrecht zur Achse an `von`/`bis`.

    Geometrie aus `ICurve.LineParams` in Modellkoordinaten.
  - `ordne_masse_an(drw, view)`: `IModelDocExtension.AlignDimensions(swAlignDimensionType_AutoArrange=0, Abstand)`
    (2, 2011) für die Maße der Ansicht.
  - Ergebnis von `zeichnen` erweitert um
    `"masse": {"plan": n, "gesetzt": n, "je_ansicht": {rolle: n}, "ohne_ansicht": [...]}` und `meldungen`.

- [ ] **Step 1: API nachschlagen.**
  - `IModelDocExtension.AlignDimensions`, `swAlignDimensionType_e`
  - `IModelDoc2.EditDelete`, `IAnnotation.Select3`
  - `IDisplayDimension.SetText`, `swDimensionTextParts_e`
  - `ICurve.LineParams`, `IView.GetVisibleEntities2`, `IModelDoc2.AddDimension2`
  - für die Überlappungsprüfung `IAnnotation.GetDisplayData` → `IDisplayData`; sonst Meldung, Prüfung visuell durch den
    Prüfer (Z1.4)

  Funde als Kommentar.
- [ ] **Step 2: Failing tests mit Fake-COM**
  - Ablauf `kandidaten` → `ordne_zu` → `loesche_ausser`.
  - Der Fake meldet für jedes Maß die Ansichten, in die es „eingefügt“ wurde.
  - Gelöscht werden alle Duplikate und Nicht-Plan-Maße; je Plan-Maß bleibt genau eines.
  - Bei `weitere_ansicht` wird die nächste Rolle aus `weitere_rollen` erzeugt und neu eingefügt, höchstens zwei Runden.
- [ ] **Step 3: Test laufen lassen.** Erwartet: FAIL.
- [ ] **Step 4: Implementieren.** Reihenfolge in `zeichnen`:
  1. Ansichten-Grundsatz erzeugen (Stufe 1).
  2. Modellmaße einfügen (nur Frästeil bzw. Fasen).
  3. Kandidaten und Zuordnung.
  4. Bei Bedarf weitere Ansicht, dann erneut einfügen.
  5. Löschen.
  6. Leere Ansichten (außer haupt) löschen.
  7. Anordnen (Layout, Stufe 1).
  8. Neue Maße setzen (Drehteil).
  9. `AlignDimensions` je Ansicht.
  10. Speichern.
- [ ] **Step 5: Tests ohne SolidWorks laufen lassen.** Erwartet: PASS.
- [ ] **Step 6: Live-Test erweitern** (Nutzer-OK, frisches SolidWorks):
  - `z["masse"]["gesetzt"] == z["masse"]["plan"]` bzw. die Differenz steht vollständig in `meldungen`.
  - Keine Ansicht über der Obergrenze.
  - Teildatei unverändert.
  - Spannplatte: 3 Ansichten mit Maßen oder eine Meldung, warum weniger.
  - Buchse: Ø 50/32/20 vorhanden.

  `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_zeichnen.py --zeit 300` → beide OK.
- [ ] **Step 7: Commit;** beide PDFs selbst ansehen (PNG), dann dem Nutzer schicken.

### Task 6: Dokumentation, Review

**Files:** `docs/zeichnungsableitung/ergebnisse.md` (Stufe 2, Live-Befunde, Laufzeit), Skill `konstruieren` (Satz zu
`swki zeichnen`: Maße aus dem Maßplan), `CLAUDE.md` nur, falls sich eine Regel ändert.

- [ ] **Step 1: Texte**, ganze Suite ohne SolidWorks: `.venv\Scripts\python.exe -m pytest -q` → alle PASS.
- [ ] **Step 2: Commit**, dann Abschluss-Review (frischer Reviewer), Befunde einarbeiten, PDFs an den Nutzer.
