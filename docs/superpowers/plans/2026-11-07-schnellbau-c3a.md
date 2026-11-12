# Stufe C3a: Konstruktionsstil im Schnellbau – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Ziel:** Der Schnellbau (`swki/schnellbau/`) baut Bohrungsfasen, Verrundungen in Musterquellen und `austragung` wie der SolidWorks-Compiler und liefert dieselben Instanzpunkte gemusterter Bohrungen.

**Architektur:** Alles in `swki/schnellbau/teil.py` (Feature-Handler) und `swki/schnellbau/baugruppe.py` (Seiten der Verknüpfungen). Reine Geometrie aus `swki/spec/` (`bohrungsfase`, `instanzen`) wird wiederverwendet, nicht nachgebaut. Der Compiler bekommt nur einen Live-Test.

**Technik:** Python 3, build123d 0.13 (OCP), pytest; live SolidWorks 2025 über `tests/live/` und `-m werkzeuge.schnellbau_abgleich`.

**Spec:** `docs/superpowers/specs/2026-11-06-schnellbau-c3a-design.md` (freigegeben vom Nutzer 07.11.2026).

## Global Constraints

- Python nur über `.venv\Scripts\python.exe` (im Worktree: `..\..\..\.venv\Scripts\python.exe`, importiert `swki` aus dem Worktree). Keine Befehle, die auf stdin warten.
- Längen in mm, Winkel in Grad; Teilkoordinaten wie in SolidWorks.
- Was der Schnellbau nicht kann, meldet er (`SchnellbauFehler` bzw. `meldungen`), nie still weglassen.
- Keine neuen Spec-Felder, keine neuen Feature-Typen, keine Änderung am Compiler-Code.
- Referenzwerte: Volumen ≤ 1e-7 relativ, Hüllquader ≤ 1e-4 mm gegen `sw_referenz.json`; STL p99 ≤ 0,05 mm, max ≤ 0,1 mm.
- Live nur, wenn SolidWorks frei ist und keine andere Session es nutzt; nie zwei SolidWorks-Jobs gleichzeitig.
- Kein `git push` ohne Rückfrage; Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Muster aus Bohrung **und** ihrem Muster als Quellen (`spiegeln: [f2, m1]`): Kopien zählen Quellpositionen plus Musterkopien, ohne Doppelte → Test in Task 4 (Live-Fall aus `test_live_musterinstanzen.py`).
2. Verrundung an einer konvexen Kante als Musterquelle (Abtrag statt Zuwachs) → Test in Task 2.
3. Fase an Bohrung mit Senkung bzw. Zylinderschraube: Fase sitzt am Senkungsrand → Test in Task 1.
4. `bohrungen=False` (Simulation ohne Bohrungen) mit gemusterter Bohrung samt Fase: kein Abbruch, Muster übersprungen → Test in Task 1.
5. Instanz über der Anzahl in einer Baugruppe → `SchnellbauFehler(ANKER)` statt IndexError → Test in Task 4.

---

### Task 1: Bohrungsfase im Körper

**Files:**
- Modify: `swki/schnellbau/teil.py` (`bohrung`, Modul-Docstring)
- Modify: `tests/schnellbau/test_stil_meldungen.py` → umbenennen in `tests/schnellbau/test_stil.py` (gemeinsame Datei für Task 1–3)

**Interfaces:**
- Consumes: `swki.spec.bohrungsfase.fase_abstand(f, p) -> float | None`, `eintritt_radius(f, p) -> float`
- Produces: Bohrungswerkzeug enthält den Fasenkegel; keine `meldungen` mehr für `fase`.

- [ ] **Step 1: Tests schreiben** (in `tests/schnellbau/test_stil.py`, `PLATTE` 100 × 60 × 20 auf `oben` wie bisher)
  - `test_fase_bohrung_durch`: `bohrung` Ø 6 durch, `fase: 0.5` an zwei Positionen → Volumen = 100·60·20 − 2·(π·3²·20 + π·0,5·(3·0,5 + 0,5²/3)), rel 1e-9; `teil.meldungen == []`.
  - `test_fase_nenn_gewinde`: `normbohrung gewinde M8`, `tiefe 12`, `gewindetiefe 10`, `fase: nenn` → Volumen mit und ohne Feld unterscheidet sich um π·c·(r·c + c²/3), r = Kernloch/2 aus `normmasse`, c = (8 − Kernloch)/2.
  - `test_fase_zylinderschraube_am_senkungsrand`: `normbohrung zylinderschraube M6`, durch, `fase: 0.5` → Differenz mit r = `senkung_d`/2.
  - `test_fase_im_muster`: Bohrung Ø 6 durch mit `fase: 0.5` + `muster_linear` x 20 × 3 → Differenz zu ohne `fase` = 3·π·c·(r·c + c²/3).
  - `test_fase_ohne_bohrungen`: wie `test_fase_im_muster`, `baue(spec, bohrungen=False)` → Volumen = 100·60·20, `uebersprungen` enthält Bohrung und Muster.
- [ ] **Step 2:** `..\..\..\.venv\Scripts\python.exe -m pytest tests/schnellbau/test_stil.py -q` → die Fasen-Tests schlagen fehl (Volumen ohne Fase).
- [ ] **Step 3: Umsetzen** in `Schnellbau.bohrung`: c = `fase_abstand(f, self.p)`; ist c gesetzt, je Punkt `Solid.make_cone(r + c, r, c, Plane(origin=p, z_dir=d))` mit r = `eintritt_radius(f, self.p)` an das Werkzeug der Position vereinigen. Die `meldungen`-Zeile entfällt. Docstring: `fase` an Bohrungen erwähnen.
- [ ] **Step 4:** Tests aus Step 1 und `tests/schnellbau -q` grün, außer `test_referenzteil_wie_solidworks[stehlager/*]` (erwartet: alte Werte ohne Fase, bis Task 6). Die Fehlschläge notieren, nicht wegdrücken.
- [ ] **Step 5: Commit** `Schnellbau: Bohrungsfase im Körper (C3a)`

### Task 2: Verrundung und Fase-Knoten als Musterquelle

**Files:**
- Modify: `swki/schnellbau/teil.py` (`FeatureInfo`, `verrundung`, `fase`, `_werkzeuge`, `_muster_anwenden`)
- Test: `tests/schnellbau/test_stil.py`

**Interfaces:**
- Produces: `FeatureInfo.teile: list[tuple[Solid, str]] | None` – Werkzeuge mit Operation in Anwendungsreihenfolge (für Knoten mit Zuwachs und Abtrag). `_werkzeuge(ids) -> list[tuple[Solid, str]]` liefert flach in Quellreihenfolge.

- [ ] **Step 1: Tests schreiben**
  - `test_tasche_mit_verrundung_gespiegelt`: Tasche 30 × 20 × 12 bei u = −30 (rechteck auf `{feature: f1, flaeche: "+y"}`), `verrundung` R 3 `senkrechte_kanten`, `spiegeln [t1, r1]` an `rechts` → Volumen = 100·60·20 − 2·(30·20·12 − (4 − π)·9·12), rel 1e-9; ein Körper.
  - `test_tasche_mit_verrundung_gemustert`: dieselbe Tasche, `muster_linear [t1, r1]` x 40 × 2 → gleiches Volumen.
  - `test_aufsatz_kante_verrundet_gespiegelt`: Aufsatz 10 × 10 × 10 bei u = −30 auf der Platte, `verrundung` R 2 an `{feature: a1, kanten_an: "+y"}` (konvex, Abtrag), `spiegeln [a1, r1]` an `rechts` → Volumen beider Aufsätze gleich (Volumen − Platte = 2 × Volumen des einzeln gebauten verrundeten Aufsatzes).
  - `test_verrundung_ausserhalb_von_mustern_unveraendert`: bestehendes Verhalten, ohne Muster kein Differenzkörper (`info.teile is None`).
- [ ] **Step 2:** Tests laufen lassen → `NICHT_UNTERSTUETZT … lässt sich nicht mustern/spiegeln`.
- [ ] **Step 3: Umsetzen**
  - `verrundung`/`fase`: steht `f["id"]` in `features` eines späteren `muster_linear`/`muster_kreis`/`spiegeln` der Spec (`swki.spec.instanzen.MUSTER`), dann vorher/nachher merken: `teile = [(vorher − nachher, "minus"), (nachher − vorher, "plus")]`, nur Teile mit Volumen > `_VOLUMEN_EPS`.
  - `_werkzeuge`: Knoten mit `teile` liefern diese; sonst `(werkzeug, op)` wie bisher.
  - `_muster_anwenden`: Enthält eine Quelle `teile`, Kopien in Quellreihenfolge anwenden, aufeinanderfolgende gleicher Operation vereinigt. Sonst das bisherige „erst plus, dann minus“ (bestehende Referenzen bleiben gleich).
- [ ] **Step 4:** `tests/schnellbau -q` wie nach Task 1.
- [ ] **Step 5: Commit** `Schnellbau: Verrundung und Fase in Musterquellen (C3a)`

### Task 3: `austragung`

**Files:**
- Modify: `swki/schnellbau/teil.py` (neuer Handler `austragung`, `HANDLER`, Docstring)
- Test: `tests/schnellbau/test_stil.py`

**Interfaces:**
- Consumes: `drahtzuege(se, elemente)`, `_linie`, `_bogen(se, a, b, c, gegen_uhrzeigersinn)`, `ebene(e)`
- Produces: `FeatureInfo("austragung", werkzeug, "plus"|"minus", richtung=Tangente am Pfadanfang (Modell))`

- [ ] **Step 1: Tests schreiben**
  - `test_austragung_kreis_aufsatz`: ohne Platte; Profil `kreis` Ø 8 Mitte [0, 0] auf `rechts`, Pfad auf `vorne` start [0, 0], `linie [40, 0]`, `bogen [60, 20]` `mitte [40, 20]`, `linie [60, 60]` → Volumen = π·16·(40 + π·10 + 40), rel 1e-9.
  - `test_austragung_rechteck_schnitt_uhrzeigersinn`: Spannplatten-Nut ohne Bohrungen (f1 und k1 aus `tests/referenz/stil/spannplatte.yaml`, Parameter übernommen) → Volumen = L·B·H − NB·NT·(L/2 − XN + π·RN/2 + (B/2 − ZN − RN)), rel 1e-9.
  - `test_austragung_gespiegelt`: Aufsatz aus `test_austragung_kreis_aufsatz` + `spiegeln [k1]` an `vorne` → doppeltes Volumen.
  - `test_austragung_nicht_unterstuetzt` aus der alten Datei entfällt.
- [ ] **Step 2:** Tests laufen lassen → `Feature-Typ austragung hat im Schnellbau kein Gegenstück`.
- [ ] **Step 3: Umsetzen** `austragung(self, f)`: Profil = `Face(drahtzuege(ebene(profil.ebene), elemente)[0])`; Pfad = `Wire` aus Segmenten (`bogen`: `gegen_uhrzeigersinn = not s.get("uhrzeigersinn")`); `Solid.sweep(profil, pfad)`; Operation `minus` bei `schnitt: true`; `anwenden`.
- [ ] **Step 4:** `tests/schnellbau -q` wie nach Task 1.
- [ ] **Step 5: Commit** `Schnellbau: austragung (C3a)`

### Task 4: Instanzpunkte, Achsrichtungen, Drehsinn des Kreismusters

**Files:**
- Modify: `swki/spec/instanzen.py` (Konstante `BEZUGSACHSE`)
- Modify: `swki/schnellbau/teil.py` (`FeatureInfo.richtungen`, `FeatureInfo.kopien`, `bohrung`, `muster_linear`, `muster_kreis`, `spiegeln`)
- Modify: `swki/schnellbau/baugruppe.py` (`seite`)
- Test: `tests/schnellbau/test_instanzen.py` (neu), `tests/spec/test_instanzen.py` (Konstante)

**Interfaces:**
- Produces: `swki.spec.instanzen.BEZUGSACHSE: dict[str, tuple[float, float, float]] = {"x": (1.0, 0.0, 0.0), "y": (0.0, -1.0, 0.0), "z": (0.0, 0.0, 1.0)}` (Docstring: y, z Spike S20 d; x Annahme bis Live-Test Task 5).
- Produces: `FeatureInfo.richtungen: list[tuple] | None` (je Instanz, parallel zu `punkte`); `FeatureInfo.kopien: dict[str, tuple[list, list]]` (Bohrungs-ID → (Punkte, Richtungen) dieses Musters).

- [ ] **Step 1: Tests schreiben** (`tests/schnellbau/test_instanzen.py`)
  - `test_reihe_und_spiegel_wie_solidworks`: SPEC aus `tests/live/test_live_musterinstanzen.py` (Platte 120 × 60 × 20, M6 bei [−40, 10] mit `fase: nenn`, `muster_linear` x 20 × 5, `spiegeln [f2, m1]` an `vorne`) → `len(punkte) == 10`; Punkt 5 x 40 z −10; Punkt 6 x −40 z 10; Punkt 10 x 40 z 10; Punkt 9 x 20 (Live-Werte).
  - `test_punkte_wie_anzahl_instanzen`: für dieselbe Spec `len(punkte) == anzahl_instanzen(spec, "f2")`.
  - `test_kreismuster_dreht_um_bezugsachse`: Scheibe Ø 100 × 10 auf `oben`, Bohrung Ø 8 durch bei [30, 0], `muster_kreis` y, anzahl 2, winkel 90 → Punkt 2 ≈ (0, ·, 30); Körper hat bei (0, 5, 30) kein Material, bei (0, 5, −30) Material.
  - `test_richtung_gedrehter_kopie`: Bohrung auf `+x`-Fläche eines Würfels, `muster_kreis` y × 4 → `richtungen[1]` ≈ Drehung von (−1, 0, 0) um −y um 90°.
  - `test_instanz_ueber_anzahl_ist_ankerfehler` (Baugruppe: Komponente aus der Spec oben, Verknüpfung `konzentrisch` auf `instanz: 11`) → `SchnellbauFehler`, `code == ANKER`, Meldung nennt 11 und 10.
  - `test_instanz_auf_musterkopie`: dieselbe Baugruppe mit `instanz: 7` → `seite(...).punkt` = Punkt 7.
- [ ] **Step 2:** Tests laufen lassen → Fehlschläge (nur eine Instanz, IndexError, Drehsinn).
- [ ] **Step 3: Umsetzen**
  - `bohrung`: `richtungen = [richtung] * len(punkte)`.
  - Muster/Spiegeln: Quellen-Instanzen wie `swki/compiler/handler/muster.py::_instanzen_der_quellen` (Bohrung: erste `len(positionen)` Punkte und Richtungen; Muster: dessen `kopien`). Punkte über `kopien_linear`/`kopien_kreis(…, BEZUGSACHSE[achse], …)`/`kopien_spiegeln`; Richtungen: linear wiederholt in derselben Reihenfolge, Kreis über `kopien_kreis` (Vektor = Punkt bei Achse durch den Ursprung), Spiegeln über `kopien_spiegeln(richtungen, achse, 0.0)`. An die Bohrung anhängen, im Muster als `kopien` merken.
  - `muster_kreis`: Werkzeuge drehen um `Axis((0, 0, 0), BEZUGSACHSE[achse])`.
  - `baugruppe.seite`: Instanz n > `len(punkte)` → `SchnellbauFehler(ANKER, f"{kid}.{feature}: Instanz {n}, es gibt {len} ")`; Richtung `info.richtungen[n − 1]`, falls vorhanden.
- [ ] **Step 4:** `tests/schnellbau tests/spec -q` grün (bis auf die Stehlager-Sollwerte, s. Task 1).
- [ ] **Step 5: Commit** `Schnellbau: Instanzpunkte gemusterter Bohrungen, Kreismuster um die Bezugsachse (C3a)`

### Task 5: Referenzen, Skills, Live-Test der Achsen

**Files:**
- Modify: `tests/schnellbau/test_referenz.py` (Ausnahme für `austragung` entfällt, nur `skript` bleibt)
- Modify: `werkzeuge/schnellbau_abgleich.py` (`REFERENZEN` + `("stil", "spannplatte.yaml")`)
- Modify: `tests/live/test_live_musterinstanzen.py` (neu `test_bezugsachsen_wie_konstante`)
- Modify: `.claude/skills/konstruieren/SKILL.md` Regel 4, `.claude/skills/optimieren/SKILL.md` §1

- [ ] **Step 1:** `test_referenz.py`: `test_referenzteil_wie_eigene_pruefung[stil/spannplatte]` muss jetzt bauen und gegen `huellquader: auto` und `volumen: auto` bestehen. Laufen lassen → grün.
- [ ] **Step 2:** Live-Test `test_bezugsachsen_wie_konstante`: Teil mit Platte bauen, im Kontext `referenzachse(ctx, a)` für x, y, z → Richtung ≈ `BEZUGSACHSE[a]` (abs 1e-9). Markiert `sw`, läuft erst in Task 6.
- [ ] **Step 3:** Skills: Regel 4 ohne „und in Specs mit `optimierung` oder Simulation (…, Stufe C3a)“; `optimieren` §1 ohne die Sätze „Bis Stufe C3a … meldet der Schnellbau nur.“ Hinweis `fertigung` unverändert.
- [ ] **Step 4:** `..\..\..\.venv\Scripts\python.exe -m pytest -q` → grün bis auf `test_referenzteil_wie_solidworks[stehlager/*]`.
- [ ] **Step 5: Commit** `C3a: Referenzen, Skills ohne Übergangsregel, Live-Test der Bezugsachsen`

### Task 6: Live-Abgleich (hartes Tor)

- [ ] **Step 1:** Prüfen, dass SolidWorks frei ist (keine laufende Session mit SolidWorks-Job, `list_sessions linked`; sonst warten). SolidWorks frisch starten (`-m werkzeuge.sw_neustart`).
- [ ] **Step 2:** `..\..\..\.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_musterinstanzen.py` → grün (Achse x belegt). Schlägt x fehl: `BEZUGSACHSE["x"]` auf den gemessenen Wert setzen, Task 4 Tests nachziehen.
- [ ] **Step 3:** `..\..\..\.venv\Scripts\python.exe -m werkzeuge.schnellbau_abgleich --nur stehlager,stil` im Hintergrund → je Teil Volumen, Hüllquader, STL innerhalb der Grenzen; `sw_referenz.json` hat neue `stehlager/*` und `stil/spannplatte`.
- [ ] **Step 4:** `..\..\..\.venv\Scripts\python.exe -m pytest -q` → ganz grün.
- [ ] **Step 5: Commit** `C3a: sw_referenz.json für Stehlager (Fasen) und Spannplatte`

### Task 7: Abschluss

- [ ] **Step 1:** `docs/schnellbau-c3a/ergebnisse.md`: Umsetzung je Punkt, Abgleichwerte (Volumen, Hüllquader, STL p99/max), Bauzeit Schnellbau Spannplatte, Grenze kopierte Verrundung, Befund Achse x, pytest-Zahl.
- [ ] **Step 2:** `CLAUDE.md`: Stand-Zeile auf C3a; Abschnitt „Schnellbau und Simulation“: Schnellbau kann `fase`, Verrundung in Musterquellen, `austragung`. `docs/konstruktionsstil/ergebnisse.md` „Offen“: Schnellbau-Punkte als erledigt verweisen.
- [ ] **Step 3: Commit**, Review des Branches (Skill `superpowers:requesting-code-review`), Befunde einarbeiten.
- [ ] **Step 4:** PR gegen main nach Rückfrage zum Push. Kein Merge ohne OK.
