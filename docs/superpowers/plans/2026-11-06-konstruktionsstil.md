# Paket Konstruktionsstil – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teile im Feature-Baum wie vom Konstrukteur: Formen gespiegelt, Reihen gemustert, Innenradien nach Fräserregel,
Fasen an Bohrungseintritten, Austragung entlang Pfad – ohne die Prüfung gegen die freigegebene Kopie zu schwächen.

**Architecture:**
- Regeln stehen im Skill `konstruieren`, die Hinweise in `swki/spec/hinweise.py`.
- Das Feld `fase` an Bohrungen baut der Compiler als eigenes SW-Feature `<id>_fase`.
- Instanzen gemusterter Bohrungen entstehen im Compiler. Sie werden an die Quelle angehängt (Protokoll-`punkte`,
  `FeatureErgebnis.traeger`).
- Neue Prüfungen `muster` und `kanten` lesen die Feature-Definitionen.

**Tech Stack:** Python 3, pywin32/COM SolidWorks 2025, pytest, jsonschema.

**Spec:** `docs/superpowers/specs/2026-11-01-konstruktionsstil-design.md`

## Global Constraints

- Jeder neue SW-API-Aufruf vorher mit `.venv\Scripts\python.exe -m swki api methode|enum …` nachschlagen; in SW 2025
  verfügbar (`swki api pruefe-code`).
- API in Metern und Radiant, Spec und Ausgaben in mm und Grad.
- Bohrungsfase: Stift, Durchgang, Zylinderschraube 0,5 × 45° (Wert in der Spec, Parameter oder Zahl); Gewinde `fase: nenn`
  = (Nenn-Ø − Kernloch-Ø)/2 × 45°. `senkschraube` mit `fase` lehnt `validieren` ab.
- Fräserregel: R ≥ T/5 (T = Frästiefe an der Ecke; Durchbruch: Dicke).
- Bohrbild: ≥ 3 Löcher auf einer Linie mit gleicher Teilung → Muster. Sonst bleiben 2–4 Löcher ein Knoten, Lochkreise
  bleiben `positionen`.
- Instanzreihenfolge: erst die Positionen der Quelle, dann die Kopien je Muster in Spec-Reihenfolge.
- Hinweise blockieren nie. Keine SW-Arbeit parallel zu einer anderen SW-Arbeit. Live-Tests einzeln mit
  `tests\live_einzeln.py`.
- Kein `git push`, kein Merge ohne Nutzer-OK. Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Lochreihe nachträglich zwischen `positionen` und Muster gewechselt.** `swki pruefen` muss bestehen, solange
   Anzahl und Art je Bohrbild gleich bleiben (Test in Task 8).
2. **Muster mit Bohrung, Senkung und Fase als Quelle.** Alle Kopien tragen die Fase. `kanten` misst sie. `instanz`
   über die Musterzahl hinaus liefert `REFERENZ_NICHT_GEFUNDEN` (Tests in Task 5 und Task 7).
3. **Spiegeln an einer Fläche statt an einer Standardebene.** Instanzpunkte werden an der echten Ebenenlage gespiegelt
   (Test in Task 7).
4. **`volumen: auto` mit Verrundung über `nahe`.** Bleibt nicht berechenbar, mit Grund; `validieren` lehnt `auto` ab
   statt falsch zu rechnen (Test in Task 6).
5. **Hinweis Fräserradius bei Schnitt mit `bis_flaeche` oder `versatz_von_flaeche`.** Tiefe unbekannt, also kein
   Hinweis und kein Absturz (Test in Task 2).

---

### Task 0: Spike S20 (live, vor Plan-Code)

**Files:** Create `spikes/s20_konstruktionsstil.py`; Ergebnisse als Abschnitt „Spike S20“ in
`docs/konstruktionsstil/ergebnisse.md`.

Je Frage ein neues Teil, Ergebnis als JSON. Die API vorher nachschlagen.

- [ ] **a.** Bohrung (Schnitt) Ø 6,6 mit Senkung, Fase 0,5 auf die Eintrittskante. `muster_linear` mit beiden plus
  Fase als Quellen. Prüfen: Haben die Kopien eine Fase, Flächenzahl, Volumen?
- [ ] **b.** `HoleWizard5` Gewinde M8, Fase 0,6 auf die Kernlochkante, Muster wie in a. Prüfen: Bleibt der kosmetische
  Gewindeaufbau fehlerfrei?
- [ ] **c.** Tasche (Rechteck) und `verrundung` `senkrechte_kanten`. `spiegeln` mit Tasche und Verrundung an `rechts`,
  danach an einer Fläche.
- [ ] **d.** `muster_kreis` mit 4 Instanzen bei 360° und bei 90°. Gemessen werden Schrittweite (360/n oder
  Winkel/(n − 1)) und Drehsinn um +x, +y, +z.
- [ ] **e.** Sweep: Kreisprofil auf `rechts`, offener Pfad auf `oben` (Linie, Bogen, Linie) als Aufsatz und als Schnitt
  mit `InsertProtrusionSwept4`/`InsertCutSwept5`. Auswahl-Marken für Profil und Pfad ermitteln.
- [ ] **f.** Definitionen lesen: lineares Muster, Kreismuster, Spiegeln, Verrundung, Fase. Gesucht sind Anzahl,
  Abstand bzw. Winkel, Quellen, Radius, Fasenabstand und Winkel.
- [ ] **Ende:** Commit „Spike S20“. Fällt a oder b durch, gilt der Rückweg aus Design §4: Fase hinter dem Muster auf alle
  Kopien (Task 5, Variante B).

### Task 1: Hinweise Regel 3 und 6 neu

**Files:**
- Modify: `swki/spec/hinweise.py` (`_REGEL_3` raus, neue Kandidaten, `_gruppen` ohne Quellen)
- Test: `tests/spec/test_hinweise_stil.py` (neu); bestehende Hinweis-Tests anpassen

**Interfaces:** Produces `muster_kandidaten(spec) -> list[dict]` (Einträge `art: zusammenfassen`, `knoten`, `meldung`
mit „(Regel 3)“).

- [ ] **Step 1: Tests.**
  - `test_lochreihe_3_wird_muster`: normbohrung mit `[[-20,0],[0,0],[20,0]]` → ein Hinweis, Meldung enthält
    „muster_linear“ und „Teilung 20“.
  - `test_eckbild_4_bleibt`: `[[±20,±10]]` (4 Ecken) → kein Hinweis.
  - `test_ungleiche_teilung`: `[0,10,25]` → kein Hinweis.
  - `test_zwei_spiegelbildliche_taschen`: zwei Schnitte, nur `mitte` u = ±30 → Hinweis „spiegeln“.
  - `test_drei_gleiche_formen`: drei Schnitte im Abstand 25 → Hinweis „muster_linear“.
  - `test_zwei_profile_einer_skizze`: zwei gleiche Kreise bei ±u → Hinweis „spiegeln“.
  - `test_muster_mit_festem_abstand_kein_hinweis_mehr`: der alte Hinweis aus Regel 3 fehlt.
  - `test_verrundung_in_musterquelle_nicht_zusammenfassen`: zwei gleiche Verrundungen, eine in `features` eines
    Musters → kein `zusammenfassen`.
- [ ] **Step 2:** `.venv\Scripts\python.exe -m pytest tests/spec -q` → neue Tests FAIL.
- [ ] **Step 3: Implementieren.** Reihen je Zeile und Spalte (gleiche v bzw. u, Toleranz 1e-6), ein Lauf ≥ 3 mit
  konstanter Teilung. Formen: Schlüssel = Feature ohne `id` und ohne `mitte` des einzigen Elements. Der Hinweistext der
  Regel 6 fällt ohne „am Ende des Baums“ aus.
- [ ] **Step 4:** pytest `tests/spec` → PASS.
- [ ] **Step 5:** Commit.

### Task 2: Hinweise `art: fertigung`

**Files:** Modify `swki/spec/hinweise.py`; Test `tests/spec/test_hinweise_fertigung.py`.

**Interfaces:**
- Consumes `_dicke` aus `swki/pruefung/geometrie.py`; spät importieren wie `huellquader_auto`.
- Produces `fertigung_hinweise(spec) -> list[dict]` mit `art: fertigung`. Aufgerufen wird es in `hinweise()` nach
  `zusammenfassen`.

- [ ] **Step 1: Tests.**
  - `test_tasche_scharf`: Rechteck-Schnitt mit Tiefe 15 ohne Radius → Meldung enthält „R ≥ 3“.
  - `test_tasche_radius_zu_klein`: Radius 2 bei Tiefe 15 → Hinweis.
  - `test_tasche_verrundung_knoten_ok`: `verrundung` `{feature: t1, auswahl: senkrechte_kanten}` mit Radius 3 → kein
    Hinweis.
  - `test_durchbruch_dicke`: `durch_alles` durch eine Platte mit T = 10 → „R ≥ 2“.
  - `test_bis_flaeche_still`: kein Hinweis, kein Fehler.
  - `test_polygon_konkav_extrusion`: L-Polygon ohne `radien` → ein Hinweis an der konkaven Ecke.
  - `test_kreis_langloch_still`.
  - `test_bohrung_ohne_fase`: je normbohrung `stift`, `gewinde`, `zylinderschraube` und `bohrung` ohne `fase` → Hinweis;
    `senkschraube` → keiner.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Implementieren.** Radien kommen aus `rechteck.radius`, `polygon.radien` (`swki/spec/konturen.py`) und
  Verrundungsknoten mit `senkrechte_kanten` auf dem Feature. Für `kontur` zählen Linie-Linie-Übergänge als Ecken.
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Commit.

### Task 3: Regeln in Skills, Review, CLAUDE.md

**Files:**
- `.claude/skills/konstruieren/SKILL.md`: Modellierregeln 3, 4, 6, neue Regel 8; Hinweis-Arten `fertigung`; Syntaxzeile
  `fase` an Bohrungen; `austragung` nach Task 11
- `.claude/skills/baugruppe/SKILL.md`: Instanzen gemusterter Bohrungen
- `.claude/skills/optimieren/SKILL.md`: Skizzen-Radius bis C3a
- `.claude/agents/konstruktionsreview.md`: Punkt 7
- `CLAUDE.md`: Abschnitt „Konstruktionsstil“

Texte aus Design §2 und §3. Werte wörtlich: R ≥ T/5, 0,5 × 45°, `nenn`, Reihen ≥ 3.

- [ ] Schreiben, dann den Skill `writing-for-agents` gegenlesen lassen. Commit.

### Task 4: Schema und `validieren` für das Feld `fase`

**Files:**
- `schema/teil.schema.json`: `f_bohrung` und `f_normbohrung` bekommen `"fase": {"oneOf": [wert, {"const": "nenn"}]}`
- `swki/spec/laden.py`: Befunde und reservierte Endung `_fase`
- Test: `tests/spec/test_fase_feld.py`

- [ ] **Step 1: Tests.**
  - `test_fase_nenn_nur_gewinde`: `nenn` an `stift` → Befund am Pfad `features[i].fase`.
  - `test_fase_an_senkschraube`: Befund.
  - `test_fase_negativ`: Befund.
  - `test_id_endung_fase_reserviert`: Feature-ID `f1_fase` wird abgelehnt.
  - `test_fase_ok`: `fase: "=FB"` an `bohrung` → gültig.
- [ ] **Step 2–4:** FAIL → implementieren → PASS.
- [ ] **Step 5:** Commit.

### Task 5: Compiler – Bohrungsfase

**Files:**
- `swki/compiler/handler/kanten.py`: neue Funktionen `eintrittskanten`, `bohrungsfase`
- `swki/compiler/handler/bohrung.py`, `normbohrung.py`: Aufruf am Ende
- `swki/pruefung/messen.py` (`kontext_aus_datei`): lädt `<id>_fase` mit
- Tests: `tests/compiler/test_eintrittskanten.py` (ohne SW), Live-Test `tests/live/test_live_bohrungsfase.py`

**Interfaces:**
- `fase_abstand(f: dict, parameter: dict) -> float | None` in `swki/spec/bohrungsfase.py` (neu). Rückgabe in mm;
  bei `nenn` aus `normmasse` als (Nenn − Kernloch)/2; None ohne `fase`. Wird auch von Task 6 und Task 9 genutzt.
- `eintrittskanten(kreise: list[tuple[Vektor, float, object]], punkte: list[Vektor], tol: float) -> list[object]`:
  je Punkt die Kreiskante mit Mitte ≈ Punkt und größtem Radius; ohne Treffer `BauFehler(REFERENZ_NICHT_GEFUNDEN)`.
- `bohrungsfase(ctx, f: dict, features: list, punkte: list) -> object | None` legt `<id>_fase` an, Maß `D1@<id>_fase`
  mit Pfad `features[i].fase`, art `abstand`; kein Maßeintrag bei `nenn`. Das Ergebnis kommt in
  `FeatureErgebnis.features` hinter Bohrung und Senkung.

- [ ] **Step 1: Tests ohne SW.**
  - `test_eintritt_groesster_kreis`: zwei Kreise an einem Punkt, Radius 3,3 und 5,5 → 5,5.
  - `test_eintritt_fehlt`: kein Kreis am Punkt → `REFERENZ_NICHT_GEFUNDEN`.
  - `test_fase_abstand_nenn_m8`: 0,6.
  - `test_fase_abstand_ohne`: None.
- [ ] **Step 2–4:** FAIL → implementieren → PASS.
- [ ] **Step 5: Live-Test (einzeln).**
  - Platte, M8 mit `fase: nenn`, Bohrung Ø 6,6 mit Senkung und `fase: 0.5`, Stift 8 mit `fase: 0.5`.
  - Erwartet: Features `f2_fase` usw. vorhanden, `rebuild_fehler` leer, Volumen = `volumen_auto` (nach Task 6).
- [ ] **Variante B** (nur wenn Spike a/b durchfällt): Muster-Handler legen die Fase der Quelle nach dem Muster auf alle
  Kopien (`<muster-id>_fase`).
- [ ] **Step 6:** Commit.

### Task 6: `volumen: auto` mit Verrundung und Bohrungsfase

**Files:** `swki/pruefung/geometrie.py` (`volumen_auto`); Test `tests/pruefung/test_volumen_stil.py`.

- [ ] **Step 1: Tests.**
  - `test_verrundung_tasche`: Rechteck 40 × 20, T 10, R 3. Erwartet −(800 − (4 − π)·9)·10.
  - `test_verrundung_polygon`: dasselbe über Polygon-Radien wie Skizzen-`radien`.
  - `test_verrundung_nahe_offen`: (None, Grund enthält „verrundung“).
  - `test_bohrungsfase_volumen`: Bohrung Ø 6 durch 10, fase 0,5, 2 Positionen. Erwartet
    −2·(π·9·10 + π·0,5·(3·0,5 + 0,5²/3)).
  - `test_muster_mit_fase`: Muster ×3 → dreifacher Beitrag.
- [ ] **Step 3: Implementieren.**
  - `verrundung` mit nur `{feature, auswahl: senkrechte_kanten}`-Ankern auf Features mit einem `rechteck`- oder
    `polygon`-Element wird vorab als Skizzen-Radius eingesetzt (Kopie der Spec).
  - Alle anderen Verrundungs- und Fase-Knoten bleiben „nicht analytisch“.
  - Fase-Feld: Beitrag π·c·(r·c + c²/3) je Position, r = Radius der Eintrittskante. Bei Gewinde ist das das
    Kernloch, bei Zylinderschraube der Senkungs-Ø, sonst der Bohrungs-Ø bzw. die Senkung.
- [ ] **Step 2/4/5:** FAIL → PASS → Commit.

### Task 7: Instanzen gemusterter Bohrungen

**Files:**
- Create `swki/spec/instanzen.py`
- Modify:
  - `swki/compiler/kontext.py`: `FeatureErgebnis.traeger: list`, `FeatureErgebnis.kopien: dict[str, list[Vektor]]`
  - `swki/compiler/handler/muster.py`
  - `swki/compiler/ablauf.py`: Protokoll-`punkte` der Quelle nach jedem Muster neu schreiben
  - `swki/pruefung/messen.py`: `kontext_aus_datei`, `messgeometrie` (Zylinder über `features[0]` und `traeger`)
  - `swki/baugruppe/referenzen.py` (`_bohrung`), `swki/baugruppe/aufloesen.py` (`anzahl_positionen`),
    `swki/baugruppe/plausibel.py` (Instanzgrenze)
- Tests: `tests/spec/test_instanzen.py`, `tests/compiler/test_muster_kopien.py`, Fälle in `tests/baugruppe`

**Interfaces:**
- `traeger(spec, fid) -> list[str]`: Muster und Spiegeln, die Instanzen von `fid` tragen, transitiv, in
  Spec-Reihenfolge.
- `anzahl_instanzen(spec, fid) -> int`. Beitrag eines Musters = (Faktor − 1) × Instanzen in seinen Quellen. Faktor:
  linear n1·n2, Kreis n, Spiegeln 2.
- `kopien_linear(punkte, achse: str, abstand: float, anzahl: int, umkehren: bool, richtung2: dict | None) -> list[Vektor]`
- `kopien_spiegeln(punkte, achse_index: int, lage: float) -> list[Vektor]`
- `kopien_kreis(...)`: Ergebnis aus Spike d. Ohne Klärung `NICHT_UNTERSTUETZT`; `validieren` meldet dann ein `instanz`
  über einem Kreismuster.

- [ ] **Step 1: Tests.**
  - `test_anzahl_reihe`: 1 Position, Muster 5 → 5.
  - `test_anzahl_formplatte`: f7 1, f8 ×4, f9 spiegeln [f7, f8] → 8.
  - `test_traeger_transitiv`: f9 nur [f8] → `traeger(f7) == [f8, f9]`, Anzahl 1 + 3 + 3.
  - `test_kopien_linear_umkehren`.
  - `test_kopien_spiegeln_flaeche_lage_25`.
  - Baugruppe: `test_plausibel_instanz_ueber_muster_ok` (instanz 5 bei 1 + Muster 5),
    `test_plausibel_instanz_zu_gross` (instanz 6 → Befund).
- [ ] **Step 2–4:** FAIL → implementieren → PASS.
- [ ] **Step 5: Live.** Lochreihe M6 als Muster. `masse_pruefen` von `{f2, instanz: 1}` zu `{f2, instanz: 5}` misst
  4 × Teilung.
- [ ] **Step 6:** Commit.

### Task 8: Prüfungen `muster`, `kanten`, `normbohrungen` nach Wirkung

**Files:**
- `swki/pruefung/messen.py`: `muster(model, spec)`, `kanten(model, spec)` → Ist-Werte aus Definitionen (Spike f)
- `swki/pruefung/bewertung.py`: Einträge `muster`, `kanten`, Umbau `normbohrungen`
- `Messwerte`: Felder `muster`, `kanten`
- Tests: `tests/pruefung/test_muster_kanten.py`

**Interfaces:**
- `muster_abweichungen(f_aktuell: dict, f_kopie: dict | None, ist: dict, p: dict) -> list[str]`
- `kanten_abweichungen(f_kopie: dict, ist: dict | str, p: dict) -> list[str]`
- `bohrbild_abweichungen(kopie: dict, aktuell: dict) -> list[str]`: Summe von `anzahl_instanzen` je
  (art, groesse, norm, durch/tiefe)

- [ ] **Step 1: Tests.**
  - `test_muster_anzahl_gebaut_falsch`: ist 4, aktuell 5 → Mangel.
  - `test_formmuster_fehlt_gegen_kopie` → Mangel.
  - `test_bohrmuster_darf_zu_positionen_werden`: Kopie Muster 5, aktuell 5 Positionen → kein Mangel.
  - `test_bohrbild_anzahl_weicht_ab`: 5 → 4 → Mangel.
  - `test_kanten_radius_falsch`: 2 statt 3 → Mangel.
  - `test_kanten_fase_feld_nenn`: Soll 0,6 bei M8.
  - `test_kanten_knoten_ohne_kopie_ungeprueft`.
  - `test_normbohrung_positionen_gegen_aktuell`.
- [ ] **Step 2–4:** FAIL → implementieren → PASS.
- [ ] **Step 5:** Commit.

### Task 9: Gewindeprüfung mit Ansenkung

**Files:** `swki/baugruppe/geometrie.py` (`ueberlappung_soll(..., ansenkung: float = 0.0)`), Aufrufer in
`swki/baugruppe/bewertung.py`; Test `tests/baugruppe/test_ueberlappung_ansenkung.py`.

- [ ] **Step 1: Test.** `test_ansenkung_m8`: d 8, p 1,25, kern 6,8, l 12, c 0,6. Erwartet Soll ohne Ansenkung
  − π·0,6·(3,4·0,6 + 0,6²/3). Bei l ≤ c gilt der volle Ring nicht, Ergebnis ≥ 0.
- [ ] **Step 2–4:** FAIL → implementieren (c aus `fase_abstand` des Gewindeknotens) → PASS.
- [ ] **Step 5:** Commit.

### Task 10: Schnellbau meldet statt still

**Files:** `swki/schnellbau/teil.py`; Test `tests/schnellbau/test_stil_meldungen.py`.

- [ ] **Tests.**
  - `test_fase_feld_meldung`: Bohrung mit `fase` → `meldungen` enthält „fase“.
  - `test_austragung_nicht_unterstuetzt`: `SCHNELLBAU_NICHT_UNTERSTUETZT`.
- [ ] FAIL → implementieren → PASS → Commit.

### Task 11: `typ: austragung`

**Files:**
- `schema/teil.schema.json`: `f_austragung` mit `profil` (skizze), `pfad` (`{ebene, start, segmente}` offen) und
  optional `schnitt`
- `swki/spec/laden.py`: Profil und Pfad nur auf Standard- oder Versatzebenen; Profilebene senkrecht zum ersten Segment;
  Profilmitte = Pfadanfang; Bogenradius > halbe Profilgröße
- `swki/compiler/handler/austragung.py` (neu, `@handler("austragung")`), `swki/compiler/skizze.py`: offener Linienzug
- `swki/pruefung/geometrie.py`: Volumen A × Pfadlänge für Kreis und Rechteck
- `swki/pruefung/huellquader.py`: `_Offen`
- Tests: `tests/spec/test_austragung.py`, `tests/pruefung/test_volumen_austragung.py`, Live
  `tests/live/test_live_austragung.py`

- [ ] **Step 1: Tests.**
  - `test_profil_nicht_senkrecht` → Befund.
  - `test_profil_nicht_am_start` → Befund.
  - `test_bogen_zu_eng` → Befund.
  - `test_volumen_kreis`: Ø 8, Linie 40 + Viertelbogen R 20 + Linie 30. Erwartet π·16·(70 + 10π).
- [ ] **Step 2–4:** FAIL → implementieren mit den Marken aus Spike e; Maße über `Kontext.mass` → PASS.
- [ ] **Step 5:** Live-Test Aufsatz und Schnitt.
- [ ] **Step 6:** Commit.

### Task 12: Referenzteile

**Files:**
- `tests/referenz/stehlager/unterteil.yaml`, `deckel.yaml`: `fase` an Gewinde, Durchgang, Stift
- `tests/referenz/stil/spannplatte.yaml`: neu, mit `eingabe/` und `sollvolumen.py`
- `tests/referenz/stil/vorher/spannplatte.yaml`: alter Stil, nur für den Vergleich, nicht in der Regression
- `tests/referenz/test_referenzen.py`: Eintrag `("stil", "spannplatte.yaml")`
- `tests/schnellbau/sw_referenz.json`: Stehlager-Werte nachziehen

Spannplatte 200 × 120 × 20, Material 1.0503:
- zwei Taschen 50 × 30 × 12 bei u ±55, R 4 (≥ 12/5), Tasche und Verrundung gespiegelt
- Reihe 5 × M6 mit `fase: nenn` als Muster (Teilung 30)
- 2 × Stift 8 mit `fase` 0,5 als Paar
- Kühlkanal Ø 8 als `austragung` (Schnitt)
- `pruefung` mit `volumen: auto`, `masse_pruefen` über `instanz` 1 und 5

- [ ] Validieren: `hinweise` ohne `fertigung` und ohne Kandidaten.
- [ ] Live einzeln: `stehlager`, `stil`.
- [ ] Prüfer-Agent auf die Spannplatte (Regel CLAUDE.md), Urteil ins Ergebnis.
- [ ] Commit.

### Task 13: Hinweislauf, Regression, Ergebnisse, PR

- [ ] `swki validieren` über alle 49 Specs (Skript `werkzeuge/stil_hinweise.py`): Hinweise je Art zählen, Fehlalarme
  beheben (zurück zu Task 1/2).
- [ ] `.venv\Scripts\python.exe -m pytest -q` grün.
- [ ] `tests\live_einzeln.py tests\referenz` grün; bei Speicher je Test frisches SolidWorks.
- [ ] Ausgangsmaß und Endmaß in `docs/konstruktionsstil/ergebnisse.md`: Knotenzahl je Typ, Bauzeiten, Hinweiszahlen.
  Dazu der Abschnitt „Für C3a“.
- [ ] CLAUDE.md „Stand“, Memory, PR gegen main ohne Push-Merge. Push nur nach Rückfrage.
