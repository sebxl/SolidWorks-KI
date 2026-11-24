# Zeichnungsableitung Z1.3 Stufe 3 (Bohrungsangaben, Gewinde, Bohrbilder, Fasen) – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `swki zeichnen` schreibt an jede Bohrung und jedes Gewinde eine Bohrungsangabe mit Hinweislinie, bemaßt
Bohrreihen als „n × Teilung (= Gesamt)“, Lochkreise über den Teilkreis-Ø und Fasen als „… × 45°“. Ergebnis sind
zwei PDFs (Buchse, Spannplatte) zur Durchsicht durch den Nutzer.

**Architecture:**
- Texte und Anzahlen rechnet ein neues Modul `swki/zeichnung/angaben.py` ohne SolidWorks aus der Spec
  (`normbohrung`, `bohrung`, `muster_linear`, `muster_kreis`, `spiegeln`, `swki/wissen/bohrungsnormen.yaml`).
- Der Maßplan bekommt Einträge der Art `angabe` (Text, Merkmal) und Textzusätze (`praefix`, `suffix`) an vorhandenen
  Modellmaßen; Maße, die die Angabe ersetzt (Ø einer `bohrung`, Lageradius eines Lochkreises), entfallen.
- `zeichnen.py` setzt die Angaben als Hinweis (`IModelDoc2.InsertNote`) an einer ausgewählten Kreiskante der Bohrung
  in der Ansicht, die auf ihre Achse blickt, und die Zusätze per `IDisplayDimension.SetText`. Die Lage des Hinweises
  sucht eine reine Funktion frei von Kanten und Maßlinien; die PDF-Prüfung bleibt der Richter.

**Tech Stack:** Python 3, pywin32/COM SolidWorks 2025, pytest, pymupdf.

**Spec:** `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md`
- §6.2: „Nicht bemaßen: Normbohrungs-Details (Bohrungsangabe) … Fasen 0,5 × 45° an Bohrungen (Bohrungsangabe bzw.
  Sammelangabe)“; „Bohrbilder: Reihen mit Muster „n× Teilung (= Gesamt)“, Lochkreise „n× Ø … auf TK Ø …““;
  „Bohrungsangaben: … Folge-Spike in Z1.3 Stufe 3“.
- Entscheidungstabelle: „Bemaßungsstil | Fase „0,5 × 45°““.
- Recherche `docs/zeichnungsableitung/recherche.md` Kap. 4 (Bohrbilder), Kap. 5 (ISO 6410: „Gewindetiefe bemaßen,
  Bohrtiefe nur wenn funktional“), Notiz 05 („Fase an der Bohrungsangabe mitschreiben“).

Vorstufen: Pläne `2026-11-17-zeichnungsableitung-z13-stufe1.md`, `…-stufe2.md`; Stand und Live-Lehren in
`docs/zeichnungsableitung/ergebnisse.md`.

**Schreibweise (Vorschlag, Recherche-Frage 15 offen; Nutzer bestätigt mit diesem Plan):** Textform statt Symbole
(ISO-Status von ⌴/⌵/↧ unbelegt), Anzahl als „5 ×“, Dezimalkomma, keine nachgestellten Nullen:

| Bohrung | Zeile 1 | Zeile 2 |
|---|---|---|
| `normbohrung art: gewinde` M6, Gewindetiefe 10, `fase: nenn` | `5 × M6 – 10 tief` | `Senkung Ø6 × 90°` |
| `normbohrung art: stift` 8, Tiefe 15, `fase: 0.5` | `2 × Ø8 – 15 tief` | `Fase 0,5 × 45°` |
| `normbohrung art: zylinderschraube` M6, durch | `n × Ø6,6 – durch` | `Senkung Ø11 × 6,4 tief` |
| `normbohrung art: senkschraube` M6, durch | `n × Ø6,6 – durch` | `Senkung Ø<senkung_d> × 90°` |
| `bohrung` Ø6 durch, Kreismuster 4, Radius 20 | `4 × Ø6 – durch` | `TK Ø40` |

Anzahl 1: kein „1 ×“. Kernlochtiefe eines Gewindes steht nicht in der Angabe (Recherche Kap. 5).

**Nicht in Stufe 3:** Passungen (H7 am Stift), Toleranzen, Rauheit, Sammelangaben (Stufe 4); Bohrungstabelle /
Koordinatentabelle; Gewindedarstellung nach ISO 6410 selbst (SolidWorks' kosmetisches Gewinde bleibt); Bemaßung von
Austragungen (Bogenradius der Kabelnut fehlt im Maßplan – eigene Frage an den Nutzer); Dezimalstellen der Maßzahlen
(Normdatei der Firmenvorlage, Z1.5).

## Global Constraints

- Python nur über `.venv\Scripts\python.exe` (im Worktree `../../../.venv/Scripts/python.exe`); nie `python -` oder
  andere Befehle, die auf stdin warten; längere Skripte mit dem Write-Tool anlegen.
- Vor jedem neuen SolidWorks-API-Aufruf `swki api methode <Interface.Member>` bzw. `swki api enum <Name>`;
  Parameteranzahl und Enum-Werte aus dem Index sind verbindlich; nur Aufrufe, die es in SW 2025 gibt.
- Die API rechnet in Metern und Radiant; Ausgaben an den Nutzer in mm und Grad.
- Nur Dokumente anfassen, die swki selbst angelegt hat; nur im Arbeitsordner speichern; die Teildatei bleibt
  unverändert (SHA-Prüfung im Live-Test).
- Live-Läufe auf frisch gestartetem SolidWorks (`-m werkzeuge.sw_neustart`), einzeln mit Zeitlimit
  (`tests/live_einzeln.py … --zeit 400`).
- Die Spec ist die Quelle: Texte aus Spec und Normtabelle, nie aus SolidWorks' eigener Bohrungsbeschreibung.
- Jede Lücke wird gemeldet (`meldungen`), nie still weggelassen.
- Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; kein `git push`.

## Review Focus

1. Bohrung, deren Achse in keiner Ansicht als Kreis erscheint (Bohrung von der Seite, keine Seitenansicht mit Maßen) →
   Meldung `ANGABE_OHNE_ANSICHT`, kein Absturz (Task 4, Test mit Fake-Ansichten).
2. Normbohrung mit Art oder Größe, die die Normtabelle nicht kennt → Meldung `ANGABE_UNBEKANNT`, kein Absturz
   (Task 2, Test).
3. Muster mit zwei Richtungen und gespiegelte Bohrungen → Anzahl = Positionen × Anzahl1 × Anzahl2 (× 2 bei Spiegeln)
   (Task 2, Test).
4. Ausdrücke statt Zahlen (`"=GT"`, `"=B/2-GR"`) in Tiefe, Positionen, Teilung → ausgewertet über
   `swki.spec.ausdruck.auswerten` mit den Spec-Parametern (Task 2, Test mit Spannplatte).
5. Hinweistext, der eine Maßzahl oder Kante überdeckt → PDF-Prüfung meldet `LESBARKEIT`, die Lagesuche probiert
   andere Richtungen (Task 4, Test der reinen Lagefunktion; live über den Live-Test).

---

### Task 1: Spike – Hinweis an der Bohrungskante, Beschriftung „EINZELHEIT“

**Files:**
- Create: `spikes/z1_diag_bohrungsangabe.py`
- Modify: `docs/zeichnungsableitung/spike-z1.md` (Nachtrag „Stufe 3“)

**Interfaces:**
- Produces: Befunde für Task 4: Auswahlweg der Kreiskante, ob `InsertNote` die Hinweislinie an die Auswahl hängt,
  Schreibweise von Ø im Hinweistext (Unicode „Ø“ oder `<MOD-DIAM>`), Lage über `IAnnotation.SetPosition2`,
  Einstellungen für die Beschriftung der Einzelheit.

- [ ] **Step 1: API nachschlagen** – `IModelDoc2.InsertNote` (1), `INote.SetText` (1), `IView.SelectEntity` (2),
  `IAnnotation.GetLeaderCount`, `IAnnotation.GetAttachedEntities3`, `IAnnotation.SetPosition2` (3),
  `IModelDocExtension.SetUserPreferenceToggle/Integer/String` mit `swDetailingDetailViewLabels_PerStandard` (240),
  `swDetailingDetailViewLabels_Name` (241, `swDetailingViewLabelsName_custom` = 3),
  `swDetailingDetailViewLabels_CustomName` (81).

- [ ] **Step 2: Spike schreiben** – gespeicherte Spannplatten-Zeichnung öffnen (aus einem Lauf im Arbeitsordner);
  in der Hauptansicht die erste sichtbare Kreiskante, deren Fläche zum Feature `g1` oder `m1` gehört
  (`GetVisibleEntities2` + `GetTwoAdjacentFaces2` + `GetFeature`, wie `zeichnen._kanten`), mit `SelectEntity`
  wählen; `InsertNote("5 × M6 – 10 tief\nSenkung Ø6 × 90°")`; Hinweis per `SetPosition2` 20 mm rechts oben neben die
  Bohrung; Beschriftungs-Einstellungen setzen; als `<name>_angabe.pdf` speichern. Ausgabe: Hinweis erzeugt?
  Hinweislinien-Zahl, angehängte Kanten, Lage zurückgelesen, Text im PDF (pymupdf), Endpunkt der Hinweislinie im PDF
  am Kreis (≤ 0,5 mm), Text der Einzelheit-Beschriftung im PDF.

- [ ] **Step 3: Live laufen lassen** (SolidWorks frisch)

Run: `../../../.venv/Scripts/python.exe -m spikes.z1_diag_bohrungsangabe <Spannplatte.SLDDRW>`
Expected: Hinweis mit 1 Hinweislinie an 1 Kante, PDF enthält „5 × M6 – 10 tief“ und „Ø6“, Beschriftung „EINZELHEIT“.

- [ ] **Step 4: Befunde nachtragen** – Tabelle in `spike-z1.md` (Frage, Ergebnis, API, Lehre). Hängt `InsertNote`
  die Hinweislinie nicht an die Auswahl: Weg über `IAnnotation.SetLeader3` + `IAnnotation.SetAttachedEntities`
  nachschlagen und erproben; geht beides nicht, hier anhalten und den Nutzer fragen (kein `AddHoleCallout2`: wartet
  laut Hilfe auf einen Dialog).

- [ ] **Step 5: Commit** – `spikes/z1_diag_bohrungsangabe.py`, `docs/zeichnungsableitung/spike-z1.md`.

### Task 2: Angabetexte und Bohrbilder aus der Spec

**Files:**
- Create: `swki/zeichnung/angaben.py`
- Test: `tests/zeichnung/test_angaben.py`

**Interfaces:**
- Consumes: `swki.spec.ausdruck.auswerten(wert, parameter) -> float`; `swki/wissen/bohrungsnormen.yaml`
  (`normen.ISO.<art>.<groesse>`: `kernloch`, `durchgang`, `senkung_d`, `senkung_t`).
- Produces:
  - `zahl(x: float) -> str` – Dezimalkomma, ohne nachgestellte Nullen (`6.6 → "6,6"`, `10.0 → "10"`).
  - `@dataclass(frozen=True) class Bohrbild: merkmal: str; anzahl: int; teilkreis: float | None; teilung: float | None;
    reihe: str | None` – `reihe` ist die ID des `muster_linear`, das die Teilung trägt.
  - `bohrbilder(spec: dict) -> dict[str, Bohrbild]` – je `bohrung`/`normbohrung`-ID.
  - `bohrungsangabe(feature: dict, spec: dict, bild: Bohrbild) -> tuple[str, list[str]]` – (Text mit `\n` zwischen
    den Zeilen, Meldungen).
  - `reihenzusatz(bild: Bohrbild) -> tuple[str, str]` – (Präfix, Suffix) für das Teilungsmaß, z. B.
    `("4 × ", " (= 120)")`.
  - `FASE_SUFFIX = " × 45°"`.

- [ ] **Step 1: Tests schreiben**

```python
def test_zahl():
    assert (zahl(6.6), zahl(10.0), zahl(0.5)) == ("6,6", "10", "0,5")

def test_spannplatte_gewinde_reihe():
    spec = _lade("stil/spannplatte.yaml")
    b = bohrbilder(spec)["g1"]
    assert (b.anzahl, b.teilung, b.reihe, b.teilkreis) == (5, 30.0, "m1", None)
    text, meld = bohrungsangabe(_feature(spec, "g1"), spec, b)
    assert text == "5 × M6 – 10 tief\nSenkung Ø6 × 90°" and meld == []
    assert reihenzusatz(b) == ("4 × ", " (= 120)")

def test_spannplatte_stift():
    spec = _lade("stil/spannplatte.yaml")
    text, _ = bohrungsangabe(_feature(spec, "st"), spec, bohrbilder(spec)["st"])
    assert text == "2 × Ø8 – 15 tief\nFase 0,5 × 45°"

def test_buchse_lochkreis():
    spec = _lade("buchse/buchse.yaml")
    b = bohrbilder(spec)["f5"]
    assert (b.anzahl, b.teilkreis) == (4, 40.0)
    assert bohrungsangabe(_feature(spec, "f5"), spec, b)[0] == "4 × Ø6 – durch\nTK Ø40"

def test_zwei_richtungen_und_spiegeln():   # Review Focus 3
    spec = {"parameter": {}, "features": [
        {"id": "f1", "typ": "extrusion"},
        {"id": "b1", "typ": "bohrung", "durchmesser": 5, "durch": True, "positionen": [[0, 0]]},
        {"id": "m1", "typ": "muster_linear", "features": ["b1"], "richtung1": {"achse": "x", "abstand": 10, "anzahl": 3},
         "richtung2": {"achse": "z", "abstand": 10, "anzahl": 2}},
        {"id": "s1", "typ": "spiegeln", "features": ["m1"], "ebene": "rechts"}]}
    assert bohrbilder(spec)["b1"].anzahl == 12

def test_unbekannte_groesse_gemeldet():    # Review Focus 2
    f = {"id": "g9", "typ": "normbohrung", "art": "gewinde", "groesse": "M7", "positionen": [[0, 0]], "tiefe": 10}
    text, meld = bohrungsangabe(f, {"parameter": {}, "features": [f]}, Bohrbild("g9", 1, None, None, None))
    assert any(m.startswith("ANGABE_UNBEKANNT") for m in meld)
```

`_lade(pfad)` liest `tests/referenz/<pfad>`, `_feature(spec, id)` sucht das Feature.

- [ ] **Step 2: Tests laufen lassen** – `../../../.venv/Scripts/python.exe -m pytest tests/zeichnung/test_angaben.py -q`;
  Expected: FAIL (Modul fehlt).

- [ ] **Step 3: `angaben.py` umsetzen** – Anzahl = `len(positionen)` × Produkt der `anzahl` aller `muster_*`, die die
  Bohrung (direkt oder über ein Muster) enthalten, × 2 je `spiegeln`, das sie enthält. Teilkreis = 2 × Abstand der
  ersten Position von der Musterachse (Kreismuster; bei `achse: y` und Flächenkoordinaten `[u, v]` der Betrag von
  (u, v)). Teilung und `reihe` nur bei `muster_linear` mit einer Richtung. Gewindetiefe `gewindetiefe`, Stifttiefe
  `tiefe`, `durch: true` → „durch“; `fase: nenn` bei Gewinde → „Senkung Ø<Nenn-Ø> × 90°“, Zahl → „Fase <zahl> × 45°“.
  Größe/Art fehlt in der Normtabelle → Text ohne Normwerte und Meldung
  `ANGABE_UNBEKANNT: <id> <art> <groesse> nicht in bohrungsnormen.yaml`.

- [ ] **Step 4: Tests laufen lassen** – Expected: PASS.

- [ ] **Step 5: Commit** – `swki/zeichnung/angaben.py`, `tests/zeichnung/test_angaben.py`.

### Task 3: Maßplan mit Angaben und Textzusätzen

**Files:**
- Modify: `swki/zeichnung/massplan.py` (`Mass`, `massplan_fraesteil`, `massplan`)
- Create: `tests/zeichnung/daten/buchse.protokoll.json` (aus einem Live-Lauf der Buchse kopiert)
- Test: `tests/zeichnung/test_massplan.py`

**Interfaces:**
- Consumes: `angaben.bohrbilder`, `angaben.bohrungsangabe`, `angaben.reihenzusatz`, `angaben.FASE_SUFFIX`.
- Produces: `Mass` mit neuen Feldern `text: str | None = None`, `praefix: str = ""`, `suffix: str = ""`; Einträge
  `Mass(id=f"{merkmal}:angabe", quelle="angabe", art="angabe", wert=0.0, merkmal=<bohrung-id>, text=<Text>,
  achse=<Bohrungsachse 0|1|2>, modus="flach")`; `massplan_meldungen(spec)` liefert zusätzlich die Meldungen aus
  `bohrungsangabe`.

- [ ] **Step 1: Buchse-Protokoll ablegen** – Buchse live bauen (`swki bauen tests/referenz/buchse/buchse.yaml` in
  einem Scratch-Auftrag) und `protokolle/buchse.lauf-<n>.protokoll.json` nach
  `tests/zeichnung/daten/buchse.protokoll.json` kopieren.

- [ ] **Step 2: Tests schreiben**

```python
def test_angaben_spannplatte():
    plan = massplan_fraesteil(*_spannplatte())
    angaben = {m.merkmal: m for m in plan if m.quelle == "angabe"}
    assert set(angaben) == {"g1", "st"} and angaben["g1"].text.startswith("5 × M6")
    assert (angaben["g1"].achse, angaben["g1"].modus) == (1, "flach")
    teilung = _nach_name(plan)["D3@m1"]
    assert (teilung.praefix, teilung.suffix) == ("4 × ", " (= 120)")

def test_buchse_lochkreis_ersetzt_lage_und_durchmesser():
    plan = massplan(_buchse(), _buchse_protokoll())
    assert [m.text for m in plan if m.quelle == "angabe"] == ["4 × Ø6 – durch\nTK Ø40"]
    assert not [m for m in plan if m.merkmal == "f5" and m.quelle == "modell"]   # Ø6 und Radius 20 entfallen

def test_fase_mit_45_grad():
    plan = massplan(_buchse(), _buchse_protokoll())
    assert {m.suffix for m in plan if m.art == "fase"} == {" × 45°"}
```

`_buchse_protokoll()` liest `tests/zeichnung/daten/buchse.protokoll.json` (wie `_spannplatte()`).

- [ ] **Step 3: Tests laufen lassen** – Expected: FAIL.

- [ ] **Step 4: Umsetzen** – je `bohrung`/`normbohrung` ein `angabe`-Eintrag (Achse aus `_ebene_achse` der Fläche
  `flaeche`); Modellmaße eines `bohrung`-Features der Art `durchmesser`/`groesse` entfallen; Lagemaße einer Bohrung in
  einem Kreismuster mit Bezug `mitte`/`ursprung` entfallen (TK steht in der Angabe); das Teilungsmaß (`abstand`) des
  Reihen-Musters bekommt `reihenzusatz`; Maße der Art `fase` bekommen `FASE_SUFFIX`.

- [ ] **Step 5: Tests laufen lassen** – alle `tests/zeichnung` grün.

- [ ] **Step 6: Commit** – `massplan.py`, `test_massplan.py`, `daten/buchse.protokoll.json`.

### Task 4: Angaben und Zusätze in der Zeichnung

**Files:**
- Modify: `swki/zeichnung/angaben.py` (reine Lagefunktion), `swki/zeichnung/zeichnen.py`, `swki/zeichnung/bemassen.py`
  (Einträge `quelle: angabe` nicht zuordnen/zählen wie Modellmaße)
- Test: `tests/zeichnung/test_angaben.py`, `tests/zeichnung/test_zeichnen_ohne_sw.py`

**Interfaces:**
- Consumes: Task-1-Befunde; `zeichnen._kanten(mu, view)`, `zeichnen._strecken`, `blickachsen(...)`,
  `lesbarkeit.pruefe_pdf`.
- Produces:
  - `hinweis_lage(kreis: tuple[tuple[float, float], float], umriss: tuple[float, float, float, float],
    hindernisse: list[tuple], groesse: tuple[float, float]) -> tuple[float, float]` in `angaben.py` – Blatt-mm,
    Mitte des Hinweistexts; Richtungen 45°/135°/315°/225° (von der Ansichtsmitte weg zuerst), Abstände 12/18/25/35 mm
    ab Kreismitte; erste Lage, deren Textrechteck keine Strecke kreuzt und möglichst außerhalb des Umrisses liegt.
  - `_angaben_setzen(drw, mu, views, plan, achsen) -> list[str]` in `zeichnen.py` – setzt je `angabe` einen Hinweis in
    der ersten Ansicht, deren Blickachse gleich `Mass.achse` ist und die eine Kreiskante des Merkmals (oder seines
    Musters/Spiegels) zeigt; sonst `ANGABE_OHNE_ANSICHT: <merkmal>`.
  - `_zusaetze_setzen(views, plan) -> None` – `SetText(1, praefix)`, `SetText(2, suffix)` an den Anzeigemaßen mit
    passendem Namen.

- [ ] **Step 1: Tests schreiben** – `hinweis_lage`: Kreis bei (130, 240) r 1,5 in Umriss (105, 184, 217, 256),
  Hindernis waagrecht bei y 245 von 100 bis 220 → Textrechteck kreuzt sie nicht und liegt rechts oberhalb
  (x > 130); Fake-Zeichnung ohne passende Ansicht → `ANGABE_OHNE_ANSICHT` (Review Focus 1).
- [ ] **Step 2: Tests laufen lassen** – Expected: FAIL.
- [ ] **Step 3: Umsetzen** – Reihenfolge in `zeichnen`: nach `_mittellinien`, vor `_lesbar_anlegen`; Hinweistexte
  in die Hindernisse der Radiuszahlen aufnehmen; die Beschriftung der Einzelheit nach Task-1-Befund auf
  „EINZELHEIT“ stellen (Dokumenteinstellungen vor dem Anlegen der Ansichten). Ein PDF-Befund an einem Hinweis setzt
  ihn auf die nächste Lage aus `hinweis_lage` (wie `_kennbuchstabe`).
- [ ] **Step 4: Tests laufen lassen** – `tests/zeichnung` und `tests/test_cli.py` grün.
- [ ] **Step 5: Commit**.

### Task 5: Live-Test, PDFs, Ergebnisse

**Files:**
- Modify: `tests/live/test_live_zeichnen.py`, `docs/zeichnungsableitung/ergebnisse.md`

- [ ] **Step 1: Live-Test erweitern** – im PDF-Text (pymupdf): Spannplatte „5 × M6 – 10 tief“, „2 × Ø8 – 15 tief“,
  „4 × 30,00 (= 120)“ (Dezimalstellen der Maßzahl wie gesetzt), „EINZELHEIT“; Buchse „4 × Ø6 – durch“, „TK Ø40“,
  „× 45°“ zweimal; keine Meldung `ANGABE_*`; Lesbarkeit wie bisher.
- [ ] **Step 2: Live laufen lassen** – `tests/live_einzeln.py tests/live/test_live_zeichnen.py --zeit 400` auf frischem
  SolidWorks; Expected: beide OK.
- [ ] **Step 3: PDFs ansehen** – beide Blätter als Ganzes rendern und die Angaben, Hinweislinien und Zusätze prüfen;
  ganze Suite ohne SolidWorks grün.
- [ ] **Step 4: Ergebnisse** – Abschnitt „Stufe 3“ in `ergebnisse.md` (was gilt, Live-Lehren, offen).
- [ ] **Step 5: Commit**; PDFs aus `~/.swki/arbeit/Z1-STUFE1/` dem Nutzer schicken.
