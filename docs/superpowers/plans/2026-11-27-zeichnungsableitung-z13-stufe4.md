# Zeichnungsableitung Z1.3 Stufe 4 (Toleranzen, Passungen, Ⓔ, Rauheit, Form/Lage, Sammelangaben) – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `swki zeichnen` trägt die Anforderungen der Spec in die Zeichnung ein:
- Passungen und Abmaße an den Maßen, Ⓔ nur an Passmaßen,
- Rauheit an Merkmalen und als Sammelangabe,
- Form-/Lagetoleranzen mit Bezügen,
- Sammelangaben nahe dem Schriftfeld: Allgemeintoleranz ISO 2768-1 m mit Jahr, ISO 8015, Kanten, „Maßgebend ist die Zeichnung“, Behandlung, Halbzeug.

Ergebnis sind zwei PDFs (Referenzen `tests/referenz/zeichnung/`) zur Durchsicht durch den Nutzer.

**Architecture:**
- **Reine Teile ohne SolidWorks** zuerst (Tasks 1–3):
  - Texte und Werte in `swki/zeichnung/toleranzangaben.py`,
  - Zuordnung Anforderung → Maß/Merkmal im Maßplan,
  - Platz für die Sammelangaben in der Blattaufteilung,
  - Übergabe-JSON für Z1.4.
- **Live-Teile** (Tasks 4–6) erst, wenn SolidWorks frei ist (Organizer 27.11.: belegt durch eine andere Session; nicht nutzen, nicht neu starten, bis der Organizer es freigibt).
- **Task 4 ist ein Spike.** Er entscheidet, wie Toleranzen an Maße kommen. Der Ausweichweg steht fest (siehe Task 4).

**Tech Stack:** Python 3, pywin32/COM SolidWorks 2025, pytest, pymupdf.

**Spec:** `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md`
- §2 Entscheidungen:
  - „Sammelangaben | Rauheit Ra 3,2 (Fräsen/Drehen), Kanten ISO 13715 „−0,1 … −0,3““,
  - Allgemeintoleranz ISO 2768-1 Klasse m mit Ausgabejahr,
  - ISO 8015, Ⓔ nur an Passmaßen.
- §4.1 Felder, §4.3 Funktionstabelle, §5 Schritte 4–5, §7, §8.1 (Übergabe an Z1.4).
- Notiz `docs/zeichnungsableitung/haerteangabe.md` (Härteschreibweise).

Vorstufen: Pläne `2026-11-17-…-stufe1.md`, `…-stufe2.md`, `2026-11-19-…-stufe3.md`; Live-Lehren in
`docs/zeichnungsableitung/ergebnisse.md` und `spike-z1.md`. Referenzteile dieser Stufe: `tests/referenz/zeichnung/spannplatte_z.yaml`,
`buchse_z.yaml` (Commit f6f1c93; Geometrie wie die bisherigen Referenzen, die unverändert bleiben).

**Entscheidungen dieses Plans (Vorschlag, im Bericht an den Nutzer gekennzeichnet):**
- **Härtestil nach ISO 15787:2016 / DIN ISO 15787:2018** (Recherche-Vorschlag, Hausregel offen): „(60 ± 2) HRC“ mit Klammer und ±; einsatzgehärtet „CHD = (0,8 +0,4/0) mm“.
- **Ⓔ:** Eine Passung aus `toleranzen` je Parameter ist ein Passmaß und bekommt Ⓔ (Nutzer 16.11.: Ⓔ gezielt an Passmaßen). Reine Abmaße (`oben/unten`) bekommen kein Ⓔ.
- **Form/Lage an einer `extrusion`/`schnitt`** gilt für deren Endfläche (Extrusion: Oberseite; Tasche: Boden); das Schema hat dort keinen Flächenanker.
- **IT-Grad statt Zahl** (`form_lage: [{it: 4}]` aus `funktionen.yaml`): Es gibt noch keine ISO-286-Tabelle (≥ 2 Quellen nötig). Deshalb Meldung `FORM_LAGE_IT_OHNE_TABELLE`, kein Zahlenwert.
- **Unbestätigte Funktionswerte** (`bestaetigt: false`) werden gezeichnet, zusätzlich kommt die Meldung `FUNKTION_UNBESTAETIGT: <merkmal>: <felder>`.

**Nicht in Stufe 4:**
- Freistich und Zentrierbohrung (Z1.2), Positionstoleranz für Bohrbilder (`stiftbild`).
- „Wie Halbzeug“-Kennzeichnung einzelner Flächen (nur die Halbzeug-Zeile).
- Messstellen, Schriftfeld-Zuordnung der Firmenvorlage (Z1.5), Zeichnungsprüfung (Z1.4, eigener Plan).

## Global Constraints

- Python nur über `.venv\Scripts\python.exe` (im Worktree `../../../.venv/Scripts/python.exe`); nie `python -` oder andere
  Befehle, die auf stdin warten; Skripte mit dem Write-Tool anlegen.
- Vor jedem neuen SolidWorks-API-Aufruf `swki api methode <Interface.Member>` bzw. `swki api enum <Name>`; nur Aufrufe aus SW 2025.
- API in Metern und Radiant; Texte an den Nutzer in mm und Grad; Dezimalkomma, keine nachgestellten Nullen (`angaben.zahl`).
- SolidWorks nur, wenn der Controller es freigibt. Vor jedem Live-Lauf offene Dokumente prüfen. Fremde Dokumente heißen: kein Neustart, kein Lauf, Rückfrage an den Controller.
- Nur selbst angelegte Dokumente; nur im Arbeitsordner speichern; die Teildatei bleibt unverändert (SHA-Prüfung).
- Die Spec ist die Quelle; jede Lücke wird gemeldet (`meldungen`), nie still weggelassen.
- Keine neue Normtabelle ohne ≥ 2 Quellen; `bestaetigt` in `funktionen.yaml` nicht umstellen.
- Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; kein `git push`.

## Review Focus

1. Spec ohne Stufe-4-Felder (alte Referenzen) → Maßplan und Angaben wie vor Stufe 4; nur die immer geltenden
   Sammelangaben (ISO 2768-1, ISO 8015, Kanten, „Maßgebend …“, Ra 3,2) kommen dazu (Task 2, Test mit
   `tests/referenz/stil/spannplatte.yaml`).
2. Parameter in `toleranzen`, der kein Maß treibt → `TOLERANZ_OHNE_MASS: <parameter>` (Task 2, Test).
3. Ein Parameter treibt mehrere Maße → alle tragen die Toleranz, kein Doppel-Eintrag (Task 2, Test).
4. Form/Lage mit IT-Grad aus der Tabelle (Lagersitz) → `FORM_LAGE_IT_OHNE_TABELLE`, kein Absturz (Task 1, Test).
5. Funktion mit unbestätigten Werten → gezeichnet, `FUNKTION_UNBESTAETIGT` gemeldet (Task 2, Test mit spannplatte_z).

---

### Task 1: Texte und Werte der Anforderungen

**Files:**
- Create: `swki/zeichnung/toleranzangaben.py`
- Test: `tests/zeichnung/test_toleranzangaben.py`

**Interfaces:**
- Consumes: `swki.spec.funktionen.aufloesen(feature) -> dict` (Felder passung, toleranz, rauheit, form_lage, huelle,
  unbestaetigt); `swki.zeichnung.angaben.zahl`.
- Produces:
  - `@dataclass(frozen=True) class Toleranz: passung: str | None; oben: float | None; unten: float | None; huelle: bool`
  - `toleranz_aus(passung: str | None, toleranz: dict | None, huelle: bool) -> Toleranz | None` (None ohne Werte)
  - `toleranztext(t: Toleranz) -> str` – Passung „H7“, Abmaße „±0,02“ bzw. „+0,1/−0,05“, mit „ Ⓔ“ wenn `huelle`
  - `rauheitstext(rauheit: dict) -> str` – „Ra 0,8“ / „Rz 6,3“
  - `GTOL_SYMBOL: dict[str, str]` – Form/Lage-Art → SolidWorks-Code (`ebenheit` → „<IGTOL-FLAT>“, `rechtwinkligkeit` →
    „<IGTOL-PERP>“, `parallelitaet` → „<IGTOL-PARALLEL>“, `rundheit` → „<IGTOL-CIRC>“, `zylindrizitaet` → „<IGTOL-CYL>“,
    `position` → „<IGTOL-POSITION>“, `koaxialitaet` → „<IGTOL-CONC>“, `symmetrie` → „<IGTOL-SYM>“, `rundlauf` →
    „<IGTOL-CIRCRUNOUT>“, `gesamtlauf` → „<IGTOL-TOTALRUNOUT>“, `neigung` → „<IGTOL-ANGULAR>“, `geradheit` →
    „<IGTOL-STRAIGHT>“, `linienprofil` → „<IGTOL-LPROF>“, `flaechenprofil` → „<IGTOL-SPROF>“; Task 4 bestätigt die Codes live)
  - `@dataclass(frozen=True) class FormLage: merkmal: str; art: str; symbol: str; wert: str; bezug: tuple[str, ...]; mmr: bool`
  - `form_lage_angaben(merkmal: str, eintraege: list[dict]) -> tuple[list[FormLage], list[str]]`
  - `behandlungstext(b: dict) -> str`, `halbzeugtext(h: dict) -> str`
  - `sammelangaben(spec: dict) -> list[str]` (Zeilen in fester Reihenfolge), `SAMMEL_RAUHEIT = "Ra 3,2"`

- [ ] **Step 1: Tests schreiben**

```python
def test_toleranztext():
    assert toleranztext(Toleranz("H7", None, None, True)) == "H7 Ⓔ"
    assert toleranztext(Toleranz(None, 0.02, -0.02, False)) == "±0,02"
    assert toleranztext(Toleranz(None, 0.1, -0.05, False)) == "+0,1/−0,05"
    assert toleranz_aus(None, None, False) is None

def test_rauheit_und_formlage():
    assert rauheitstext({"Ra": 0.8}) == "Ra 0,8" and rauheitstext({"Rz": 6.3}) == "Rz 6,3"
    fl, meld = form_lage_angaben("t1", [{"art": "parallelitaet", "wert": 0.05, "bezug": ["A"]}])
    assert fl == [FormLage("t1", "parallelitaet", "<IGTOL-PARALLEL>", "0,05", ("A",), False)] and meld == []

def test_formlage_it_ohne_tabelle():          # Review Focus 4
    fl, meld = form_lage_angaben("f1", [{"art": "rundheit", "it": 4}])
    assert fl == [] and meld == ["FORM_LAGE_IT_OHNE_TABELLE: f1 rundheit IT4 – keine ISO-286-Tabelle"]

def test_behandlung_iso15787():
    b = {"art": "einsatzhaerten", "haerte": {"wert": 60, "plus": 2, "minus": 2, "verfahren": "HRC"},
         "tiefe": {"art": "CHD", "wert": 0.8, "plus": 0.4, "minus": 0, "grenzhaerte": "550 HV1"}, "zustand": "fertigteil"}
    assert behandlungstext(b) == "einsatzgehärtet und angelassen (60 ± 2) HRC, CHD = (0,8 +0,4/0) mm (550 HV1)"
    assert behandlungstext({"art": "bruenieren"}) == "brüniert"

def test_halbzeug():
    assert halbzeugtext({"art": "flach", "norm": "EN 10058", "masse": "120 x 20"}) == "Halbzeug: Flach EN 10058 – 120 × 20"

def test_sammelangaben_reihenfolge():
    spec = _lade("zeichnung/buchse_z.yaml")
    assert sammelangaben(spec) == [
        "Allgemeintoleranzen ISO 2768-1:1989 – m", "Tolerierung ISO 8015:2011", "Kanten ISO 13715 −0,1 … −0,3",
        "Maßgebend ist die Zeichnung",
        "einsatzgehärtet und angelassen (60 ± 2) HRC, CHD = (0,8 +0,4/0) mm (550 HV1)",
        "Halbzeug: Rund EN 10060 – 55"]
    assert sammelangaben(_lade("stil/spannplatte.yaml"))[:4] == sammelangaben(spec)[:4]
```

- [ ] **Step 2: Tests laufen lassen** – `../../../.venv/Scripts/python.exe -m pytest tests/zeichnung/test_toleranzangaben.py -q -p no:cacheprovider`; Expected: FAIL (Modul fehlt).

- [ ] **Step 3: Umsetzen**
  - Art-Wörter: haerten → „gehärtet“, haerten_anlassen → „gehärtet und angelassen“, vergueten → „vergütet“, einsatzhaerten → „einsatzgehärtet und angelassen“, randschichthaerten → „randschichtgehärtet“, nitrieren → „nitriert“, nitrocarburieren → „nitrocarburiert“, gluehen → „geglüht“, eloxieren → „eloxiert“, hartanodisieren → „hartanodisiert“, verzinken → „verzinkt“, bruenieren → „brüniert“, beschichten → „beschichtet“.
  - Härte „(w ± p) V“ bei plus == minus, sonst „(w +p/−m) V“, ohne Abmaße „≥ w V“.
  - Tiefe „<art> = (w +p/−m) mm“; „/0“, wenn minus 0 ist (wie im Test).
  - Grenzhärte in Klammern dahinter; `zustand: vor_schleifen` → Zusatz „(vor dem Schleifen)“; `schicht` → „, <norm> <bezeichnung>“.
  - Halbzeug: Art großgeschrieben, „x“ → „ × “, `toleranz`/`zustand` mit „, “ angehängt.

- [ ] **Step 4: Tests laufen lassen** – Expected: PASS.
- [ ] **Step 5: Commit.**

### Task 2: Anforderungen im Maßplan

**Files:**
- Modify: `swki/zeichnung/massplan.py` (`Mass`, `massplan`, `massplan_fraesteil`, `massplan_drehteil`, `massplan_meldungen`),
  `swki/zeichnung/angaben.py` (Bohrungsangabe mit Toleranz)
- Test: `tests/zeichnung/test_massplan.py`, `tests/zeichnung/test_angaben.py`

**Interfaces:**
- Consumes: Task 1; `swki.spec.funktionen.aufloesen`; `swki.spec.ausdruck` (Bezeichner in Ausdrücken).
- Produces:
  - `Mass.toleranz: Toleranz | None = None` (an Maßen der Quelle modell/neu).
  - Plan-Einträge (kein Maß, eigene `quelle`, `wert=0.0`):
    - `quelle="rauheit"`: `text` = `rauheitstext(...)`, `merkmal`, `achse`/`modus` wie die Angabe des Merkmals.
    - `quelle="form_lage"`: `text` = Wert, neues Feld `form_lage: FormLage`.
    - `quelle="bezug"`: `text` = Buchstabe, neues Feld `anker: dict` (Flächenanker aus `bezuege`).
  - Bohrungsangabe: Toleranz hinter dem Ø, z. B. „2 × Ø8 H7 Ⓔ – 15 tief“.
  - `massplan_meldungen` liefert zusätzlich `TOLERANZ_OHNE_MASS`, `FORM_LAGE_IT_OHNE_TABELLE` und `FUNKTION_UNBESTAETIGT`.

- [ ] **Step 1: Tests schreiben** (Fixture-Protokolle `tests/zeichnung/daten/spannplatte.protokoll.json` und
  `buchse.protokoll.json` gelten weiter; die Geometrie der `_z`-Specs ist gleich)

```python
def test_spannplatte_z_anforderungen():
    spec = _lade_ref("zeichnung/spannplatte_z.yaml"); plan = massplan(spec, _spannplatte_protokoll())
    stift = next(m for m in plan if m.quelle == "angabe" and m.merkmal == "st")
    assert stift.text.startswith("2 × Ø8 H7 Ⓔ – 15 tief")
    assert {(m.merkmal, m.text) for m in plan if m.quelle == "rauheit"} == {("st", "Ra 0,8"), ("t1", "Ra 1,6")}
    assert {(m.merkmal, m.form_lage.symbol, m.text) for m in plan if m.quelle == "form_lage"} == {
        ("f1", "<IGTOL-FLAT>", "0,02"), ("t1", "<IGTOL-PARALLEL>", "0,05")}
    assert sorted(m.text for m in plan if m.quelle == "bezug") == ["A", "B"]
    abstand = _nach_name(plan)["D1@st_positionen"]          # 150, Parameter A ±0,02
    assert abstand.toleranz == Toleranz(None, 0.02, -0.02, False)

def test_buchse_z_passungen():
    plan = massplan(_lade_ref("zeichnung/buchse_z.yaml"), _buchse_protokoll())
    d = {m.wert: m.toleranz for m in plan if m.art == "durchmesser"}
    assert d[20] == Toleranz("H7", None, None, True) and d[32] == Toleranz("k6", None, None, True)
    assert d[50] is None and d[30] is None

def test_toleranz_ohne_mass_gemeldet():          # Review Focus 2
    spec = {**_lade_ref("zeichnung/buchse_z.yaml")}
    spec["toleranzen"] = {**spec["toleranzen"], "L_bund": {"oben": 0.1, "unten": 0}, "GIBTSNICHT": {"passung": "h9"}}
    assert any(m == "TOLERANZ_OHNE_MASS: GIBTSNICHT" for m in massplan_meldungen(spec))

def test_ohne_anforderungen_wie_bisher():        # Review Focus 1
    plan = massplan(*_spannplatte())
    assert all(m.toleranz is None for m in plan) and not [m for m in plan if m.quelle in ("rauheit", "form_lage", "bezug")]

def test_funktion_unbestaetigt_gemeldet():       # Review Focus 5
    assert any(m.startswith("FUNKTION_UNBESTAETIGT: st") for m in massplan_meldungen(_lade_ref("zeichnung/spannplatte_z.yaml")))
```

Ein Parameter, der zwei Maße treibt, gibt beiden die Toleranz (Review Focus 3). Dafür einen eigenen Test mit einem
Minimal-Protokoll: zwei Maße mit `roh` „=A/2“ und „=A“.

Hilfsfunktionen in `test_massplan.py` neu: `_lade_ref(pfad)` liest `tests/referenz/<pfad>`,
`_spannplatte_protokoll()` liefert das Protokoll aus `_spannplatte()`; `_buchse_protokoll()` gibt es schon.

- [ ] **Step 2: Tests laufen lassen** – Expected: FAIL.
- [ ] **Step 3: Umsetzen**
  - **Toleranz je Parameter:**
    - Modellmaße: Ein Maß bekommt die Toleranz von P, wenn der Bezeichner P im `roh`-Ausdruck des Protokolleintrags vorkommt.
    - Drehteil-Ø (Quelle neu): Ein Ø-Maß mit Radius r bekommt sie, wenn ein Profilpunkt einer `rotation` eine Radialkoordinate hat, deren Ausdruck P enthält und zu r auswertet. Dafür die rohen Punkte aus der Spec lesen, nicht `profilpunkte`.
  - **Toleranz am Feature** (`aufloesen`):
    - `bohrung`/`normbohrung` → in die Bohrungsangabe.
    - An `extrusion`/`schnitt`/`rotation` hat ein Feature-Funktionswert kein eindeutiges Maß → Meldung `TOLERANZ_OHNE_MASS: <merkmal>`.
  - **Achse:** Rauheit und Form/Lage einer `bohrung`/`normbohrung` → Achse ihrer Angabe; eines `schnitt` mit Tiefe → Achse quer (Schnittansicht); einer `extrusion` → Achse der Skizze, Modus quer.

- [ ] **Step 4: Tests laufen lassen** – `tests/zeichnung` + `tests/test_cli.py` grün.
- [ ] **Step 5: Commit.**

### Task 3: Platz für Sammelangaben, Übergabe-JSON

**Files:**
- Modify: `swki/zeichnung/blatt.py` (`freiflaechen`), `swki/zeichnung/layout.py` (`anordnen`, `einzelheit_passt`),
  `swki/zeichnung/zeichnen.py` (Übergabe schreiben)
- Test: `tests/zeichnung/test_layout.py`, `tests/zeichnung/test_zeichnen_ohne_sw.py`

**Interfaces:**
- Produces:
  - `freiflaechen(format_: str, sammel_mm: float = 0.0)`: Das Rechteck über dem Schriftfeld beginnt `sammel_mm` höher.
  - `anordnen(groessen_1zu1, sammel_mm: float = 0.0)`, `einzelheit_passt(groessen, einzelheit, sammel_mm: float = 0.0)`.
  - `SAMMEL_ZEILE_MM = 5.0` (Zeilenhöhe der Sammelangaben, Hausregel bis Z1.5).
  - `uebergabe(plan: list[Mass], gesetzt: dict, sha_zeichnung: str, meldungen: list[str]) -> dict` in `zeichnen.py`, reine Funktion. `zeichnen` schreibt das Ergebnis als `zeichnung/zeichnung.json` in den Laufordner (Design §8.1, Eingabe für Z1.4).
    - Schlüssel: `plan` (Liste von `asdict`-Einträgen; Toleranz, FormLage als dict), `gesetzt`, `sha256_slddrw`, `meldungen`.

- [ ] **Step 1: Tests** –
  - Mit `sammel_mm=40` liegt keine Ansicht in Höhe Schriftfeld + 40 mm über dem Schriftfeld (Rechteck-Test wie `_pruefe`).
  - `einzelheit_passt` mit `sammel_mm` ist nie günstiger als ohne.
  - `uebergabe(...)` ist JSON-serialisierbar (`json.dumps`) und enthält die Toleranz eines Maßes als dict.
- [ ] **Step 2–4: rot, umsetzen, grün.**
- [ ] **Step 5: Commit.**

### Task 4: Spike – Toleranz, Ⓔ, Rauheit, Bezug, Form/Lage live (gesperrt bis SolidWorks frei)

**Files:**
- Use: `spikes/z1_diag_stufe4.py` (liegt vor, Controller)
- Modify: `docs/zeichnungsableitung/spike-z1.md` (Nachtrag „Stufe 4“)

**Vorgehen:**
- Spannplatte im Scratch-Auftrag bauen und zeichnen, dann das Skript ausführen.
- Es setzt Passung H7 + Zusatz „ Ⓔ“, Abmaße, Rauheit an einer Kreiskante, Bezugsdreieck, zwei Toleranzrahmen und einen Hinweis.
- Es speichert, schließt alles ohne Teil-Speichern, öffnet neu und liest zurück. Die Teil-SHA bleibt dabei unverändert.

**Entscheidung für Task 5:**
- Überleben Passung, Abmaße und Zusätze das Wiederöffnen: am eingefügten Modellmaß setzen (`IDimension.Tolerance`).
- Sonst Ausweichweg: das tolerierte Maß als Zeichnungsmaß über Kanten neu setzen (Weg der Drehteil-Maße, `setze_neu`), das Modellmaß löschen. Die Stufe-3-Zusätze ebenso prüfen.
- Bezugsdreieck und Toleranzrahmen: entstehen sie nur mit Dialog oder gar nicht, stattdessen Meldung `FORM_LAGE_NICHT_GESETZT` und den Nutzer fragen.

- [ ] **Step 1:** SolidWorks frei (Controller), offene Dokumente leer, dann bauen, zeichnen, Spike laufen lassen.
- [ ] **Step 2:** Befunde als Tabelle in `spike-z1.md` (Frage | Ergebnis | API | Lehre), PDF ansehen (Ⓔ sichtbar?).
- [ ] **Step 3:** Commit.

### Task 5: Anforderungen in die Zeichnung (gesperrt bis Task 4)

**Files:**
- Create: `swki/zeichnung/anforderungen_setzen.py` (COM, Muster wie die Hinweise in `zeichnen.py`), sonst wächst `zeichnen.py`
  weiter (Final Review Stufe 3, M7)
- Modify: `swki/zeichnung/zeichnen.py` (Aufrufe, Sammelangaben, Einstellungen), `tests/zeichnung/test_zeichnen_ohne_sw.py`

**Befund aus Task 4 (Spike 27.11., `docs/zeichnungsableitung/spike-z1.md` Nachtrag Stufe 4), verbindlich:**
- An Modellmaßen gesetzte Toleranz und Textzusätze gehen beim Wiederöffnen der SLDDRW verloren. Das betrifft auch die Stufe-3-Zusätze. Sie dürfen nur an **Zeichnungsmaßen** stehen.
- Abmaße an Zeichnungsmaßen werden mit `IDimensionTolerance.SetValues(min, max)` gesetzt, `SetValues2` scheitert dort. Passung: `Type = 7`, `SetFitValues(bohrung, welle)`, `FitDisplayStyle` bleibt 3.
- Ⓔ an Maßen immer als Symbol `<MOD-EP>`. Das Unicode-Zeichen lässt den ganzen Maßtext verschwinden. In Hinweisen (Bohrungsangabe) live prüfen und, wenn Unicode dort ebenfalls scheitert, auch dort `<MOD-EP>` verwenden.
- Rauheit: Der Text kommt an den dritten Textparameter (ProdMethod) von `InsertSurfaceFinishSymbol3`.
- Jede Anmerkung (Rauheit, Rahmen, Bezug, freie Hinweise) bekommt eine Lage über `IAnnotation.SetPosition2`.
- Parameterlose Methoden immer über `_ruf`.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces in `anforderungen_setzen.py`:
  - `dauerhaft_machen(drw, mu, views, plan) -> tuple[dict[str, str], list[str]]`. Jedes Plan-Maß (quelle `modell`) mit `toleranz`, `praefix` oder `suffix` wird ein Zeichnungsmaß:
    - Bezugspunkte des angezeigten Modellmaßes über `_bezuege(dd)` (Blatt-mm).
    - Je Punkt die sichtbare gerade Kante quer zur Messrichtung durch den Punkt (Toleranz 0,1 mm) oder die Kreiskante mit Mitte im Punkt (`_kanten`).
    - Beide wählen, `AddDimension2` an der Lage der Maßzahl. Ist der neue Wert innerhalb 0,005 mm gleich dem alten, wird das Modellmaß gelöscht (`_loesche`). Sonst wird das neue gelöscht, das Modellmaß bleibt, und es gibt die Meldung `MASS_NICHT_DAUERHAFT: <name> – <grund>`.
    - Rückgabe: alter Name → neuer Name, damit Mittellinien, Reihen und die Übergabe den neuen Namen kennen.
  - `toleranz_setzen(dd, toleranz: Toleranz) -> bool` (Passung bzw. `SetValues`, Ⓔ als Suffix `<MOD-EP>` vor einem vorhandenen Suffix). Für Drehteil-Maße (quelle `neu`) direkt, für Modellmaße nach `dauerhaft_machen`.
  - `zusaetze_setzen` ersetzt `zeichnen._zusaetze_setzen` und arbeitet auf den Zeichnungsmaßen.
  - `rauheit_setzen(drw, mu, views, plan, ...) -> list[str]`, `bezuege_setzen(...)`, `form_lage_setzen(...)`: Kante des Merkmals bzw. des Ankers in der Ansicht des Eintrags (`achse`/`modus` aus Task 2) wählen, einfügen, Lage setzen.
  - `sammelangaben_setzen(drw, zeilen, format_) -> list[str]`: ein Hinweis mit fester Lage im reservierten Band über dem Schriftfeld (Task 3).
  - Fehlt eine Kante oder ist ein Einfügen gescheitert, gibt es eine Meldung (`RAUHEIT_NICHT_GESETZT`, `FORM_LAGE_NICHT_GESETZT`, `BEZUG_NICHT_GESETZT`), nie stilles Weglassen.
  - Reihenfolge in `zeichnen`: `dauerhaft_machen` nach Mittellinien, Einzelheit und Bohrungsangaben, also nach allen Schritten, die nach `kurzname` suchen (grep `kurzname(`), und vor `_lesbar_anlegen`, weil die Toleranz die Zahl verbreitert.
  - Die Anmerkungen stellen sich der PDF-Prüfung wie die Hinweise. Hat eine Anmerkung einen Befund, wird sie versetzt, nicht die Maßreihen.
  - `_ruf`-Werte von Zeichnungsmaßen: `GetSystemValue3` liefert None, dann `GetSystemValue2("")`.

- [ ] **Step 1:** Fake-COM-Tests für die Meldungswege: Punkt ohne Kante, neuer Wert weicht ab, Rauheitskante fehlt, Rahmen nicht erzeugt. Dazu Test für `toleranz_setzen` (Passung → Typ 7, H7; Abmaße → `SetValues`; Hülle → Suffix `<MOD-EP>`).
- [ ] **Step 2:** Umsetzen. Live an beiden `_z`-Referenzen (Scratch-Aufträge) **und** an der alten Spannplatte (Stufe-3-Zusätze). Danach die SLDDRW schließen und wieder öffnen; Toleranzen und Zusätze müssen noch da sein. Die PDFs als Ganzes rendern und ansehen.
- [ ] **Step 3:** Tests grün, Commit.

### Task 6: Live-Test, PDFs, Ergebnisse

**Files:**
- Modify: `tests/live/test_live_zeichnen.py` (neue Fälle `zeichnung/spannplatte_z.yaml`, `zeichnung/buchse_z.yaml`; Ablage
  `<arbeitsordner>/Z1-STUFE4/`, damit die noch nicht durchgesehenen Stufe-3-PDFs in `Z1-STUFE1` bleiben),
  `docs/zeichnungsableitung/ergebnisse.md`

- [ ] **Step 1:** Live-Test erweitern. Im PDF-Text:
  - Spannplatte: „2 × Ø8 H7“, „– 15 tief“, „Ra 0,8“, „Ra 1,6“, „0,02“, „0,05“, „±0,02“, „4 × 30,00 (= 120)“.
  - Nach dem Wiederöffnen der SLDDRW (eigener Schritt im Test): Toleranzen und Zusätze am Zeichnungsmaß unverändert (Stufe-3-Befund vom 27.11.).
  - Buchse: „H7“, „k6“, „Ⓔ“, „einsatzgehärtet und angelassen (60 ± 2) HRC“.
  - Beide: die vier immer geltenden Sammelzeilen.
  - Keine Meldung `LESBARKEIT`/`ANGABE_*`/`FORM_LAGE_NICHT_GESETZT`; Ausnahme `FUNKTION_UNBESTAETIGT`.
- [ ] **Step 2:** Live auf frischem SolidWorks (nur nach Freigabe durch den Controller), beide neuen Fälle und die alten
  Fälle (Regression Stufe 1–3).
- [ ] **Step 3:** PDFs ansehen; ganze Suite ohne SolidWorks grün; Abschnitt „Z1.3 Stufe 4“ in `ergebnisse.md` mit den
  gekennzeichneten Vorschlägen (Härtestil, Ⓔ aus `toleranzen`, IT-Grad offen). Den Widerspruch zum vorgedruckten Text der
  ISO-Vorlage („ENTGRATEN UND SCHARFE KANTEN BRECHEN“, leere Toleranzfelder) für Z1.5 festhalten.
- [ ] **Step 4:** Commit.
