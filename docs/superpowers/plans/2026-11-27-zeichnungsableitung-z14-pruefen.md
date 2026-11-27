# Zeichnungsableitung Z1.4 (Zeichnung prüfen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `swki zeichnung pruefen` liest eine von `swki zeichnen` erzeugte Zeichnung zurück und prüft sie maschinell gegen die freigegebene Spec, den Maßplan und `swki/wissen/zeichnungsregeln.yaml`. Danach urteilt der Agent `zeichnungspruefer`. `swki durchlauf --zeichnung` hängt beides an.

**Architecture:** Das Rücklesen (COM, `rueckleser.py`) erzeugt ein reines Ist-Modell (`ist.py`, als JSON ablegbar). Alle Prüfungen (`pruefen.py`) sind reine Funktionen über Ist, Maßplan, freigegebene Spec, Regelkatalog und PDF. Die Negativfälle aus Design §10 sind deshalb ohne SolidWorks testbar. Live kommen nur das Rücklesen und eine kleine Regression mit manipulierten Kopien dazu.

**Tech Stack:** Python 3, pywin32 (nur Task 4/6), pymupdf (PDF-Texte), pytest, PyYAML.

**Spec:** `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md` §8 (Prüfen), §10 (Negativfälle); Recherche `docs/zeichnungsableitung/recherche.md` Kap. 2 (ISO 7200, ISO 5455), Kap. 4/8 (Überbestimmung), Kap. 7 (Sammelangaben).

## Global Constraints

- Kein SolidWorks in Task 1–3 und 5. Task 4 und 6 erst, wenn der Organizer SolidWorks freigibt. Vor jedem Live-Lauf offene Dokumente prüfen; bei fremden Dokumenten nicht neu starten.
- Rücklesen ändert nichts: SHA-256 von SLDDRW und SLDPRT sind vor und nach `swki zeichnung pruefen` gleich. Geschlossen wird ohne Speichern (`CloseAllDocuments(True)` nur, wenn außer den eigenen Dokumenten nichts offen ist, sonst `sw.schliesse` je Dokument).
- Jeder neue SolidWorks-API-Aufruf wird vorher mit `swki api methode|enum` nachgeschlagen und muss in SW 2025 verfügbar sein (`swki api pruefe-code`).
- Prüfbericht: `protokolle/<spec>.lauf-<n>.zeichnung-pruefbericht.json`. Prüfer-Urteil: `protokolle/<spec>.lauf-<n>.zeichnungspruefer.json`. Art-Namen mit Bindestrich, damit `lauf_nummern_dateien` sie nicht als Teil-Lauf zählt.
- Der Prüfer wird nie übersprungen. Ein Lauf mit Zeichnung, aber ohne `zeichnungspruefer.json`, gilt in `swki bericht` als „Zeichnung ungeprüft“ (Meldung `ZEICHNUNGSPRUEFER_FEHLT`).
- Prüfungen haben die Form `{id, regel, ok: true|false|null, maengel: [{merkmal, text}], hinweis?}`, wie im Teil-Prüfbericht. `ok: null` heißt Hinweisregel oder nicht prüfbar, immer mit Begründung.
- Ausgaben an den Nutzer in mm mit Dezimalkomma (`angaben.zahl`).

## Entscheidungen (selbst entschieden, im Ergebnisbericht als Vorschlag markiert)

1. **Abgleich Ist ↔ Plan** als Multimenge je `(Ansichtsrolle egal, art, wert auf 0,01 mm)`. Weniger Ist als Plan → `fehlt`, mehr → `doppelt`. Angaben (Bohrung, Gewinde) werden über den Textanfang der Notiz abgeglichen. Der Abgleich nach Wirkung ist robust gegen Maßnamen, die SolidWorks beim Einfügen vergibt.
2. **Überbestimmt:** Der Maßgraph gilt je Ansicht und Richtung (`h`/`v`). Knoten sind Bezugskoordinaten (Blatt-mm, auf 0,05 mm gerundet), Kanten die linearen Maße ohne Klammer. Ein Zyklus bedeutet einen Mangel. Maße in verschiedenen Ansichten gelten als unabhängig, weil die Projektion keine gemeinsamen Blattkoordinaten hat. Diese Grenze ist bekannt und als Hinweis im Bericht vermerkt.
3. **Schriftfeld (ISO 7200, acht Pflichtfelder):**
   - Die Zuordnung Pflichtfeld → Eigenschaft steht in `config/standard.yaml` unter `zeichnung.schriftfeld`.
   - Hart geprüft werden Benennung, Sachnummer, Ersteller, Ausgabedatum, Dokumentart und Blatt.
   - Eigentümer ist nur ein Hinweis (`ok: null`), bis die Firmenvorlage (Z1.5) den Wert liefert. „Freigegeben“ bleibt leer, ein gefülltes Feld vor der Abnahme ist ein Mangel.
   - `swki zeichnen` setzt zusätzlich `Dokumentart: Einzelteilzeichnung` (Hausregel bis Z1.5).
4. **Lesbarkeit** prüft das PDF mit `lesbarkeit.pruefe_pdf` (wie beim Zeichnen). Die Regel ist ein Hinweis (Design §8.1: „R-Kap. 4 B (Hinweis)“): Befunde stehen in `maengel`, `ok` ist bei Befunden `null`, sonst `true`.
5. **Maßstab aus der Vorzugsreihe** (ISO 5455): 1:1, 1:2, 1:5, 1:10, 1:20, 1:50, 1:100, 2:1, 5:1, 10:1, 20:1, 50:1. Das gilt für das Blatt und jede Einzelheit.

## Review Focus

1. Ein Teil ohne jede Anforderung (alte Spec) besteht die Prüfung mit einem idealen Ist. Kein Mangel stammt aus Sammelangaben, die heute noch nicht gesetzt sind. → Test `test_ideal_ohne_anforderungen_bestanden` in Task 3.
2. Zwei Maße gleichen Werts (z. B. zweimal 20) an verschiedenen Merkmalen: Fehlt eines, wird es gemeldet; sind beide da, ist es kein Doppelmaß. → Test in Task 2.
3. Hilfsmaß in Klammern schließt eine Kette, ohne dass ein Mangel entsteht. → Test in Task 2.
4. Ⓔ an einem Maß, dessen Plan-Toleranz eine reine Abmaßtoleranz ist (keine Passung), ist ein Mangel. Ⓔ an einer Passung ist keiner. → Test in Task 3.
5. Die Zeichnung wurde nach `swki zeichnen` von Hand geändert (SHA ≠ `sha256_slddrw` der Übergabe). Die Prüfung läuft trotzdem und meldet `ZEICHNUNG_GEAENDERT` in `meldungen`. Sie bricht nicht ab und behauptet auch nicht still „bestanden“. → Test in Task 4 (reiner Teil `kopf_pruefung`).

---

### Task 1: Regelkatalog und Ist-Modell

**Files:**
- Create: `swki/wissen/zeichnungsregeln.yaml`, `swki/zeichnung/regeln.py`, `swki/zeichnung/ist.py`
- Test: `tests/zeichnung/test_regeln.py`, `tests/zeichnung/test_ist.py`

**Interfaces:**
- Produces:
  - `zeichnungsregeln.yaml`: Liste von Einträgen `{id, pruefung, text, quelle, beleg: A|B|C, art: hart|hinweis}`. `pruefung` ist eine der neun Prüfungen aus Design §8.1: vollstaendig, ueberbestimmt, toleranzen, sammelangaben, schriftfeld, ansichten, lesbarkeit, gewinde, drehteil. Mindestens diese IDs:
    - `Z-VOLL-1` (jedes Merkmal genau einmal), `Z-VOLL-2` (kein Doppelmaß)
    - `Z-UEB-1`
    - `Z-TOL-1` (Passung/Abmaße wie Spec), `Z-TOL-2` (Ⓔ nur an Passmaßen), `Z-TOL-3` (Toleranz ohne Funktion), `Z-TOL-4` (Rauheit), `Z-TOL-5` (Form/Lage), `Z-TOL-6` (Bezüge)
    - `Z-SAM-1` (ISO 2768-1 mit Jahr und Klasse), `Z-SAM-2` (ISO 8015), `Z-SAM-3` (kein „2768-…K“, kein „DIN 7167“), `Z-SAM-4` (Maßgebend ist die Zeichnung), `Z-SAM-5` (Behandlung/Halbzeug wie Spec), `Z-SAM-6` (Kanten ISO 13715), `Z-SAM-7` (Sammelrauheit)
    - `Z-SCH-1` (Pflichtfelder), `Z-SCH-2` (Freigegeben leer), `Z-SCH-3` (Maßstab Vorzugsreihe)
    - `Z-ANS-1` (kein Maß an verdeckter Kante), `Z-ANS-2` (Schnittbezeichnung), `Z-ANS-3` (Einzelheit mit Maßstab)
    - `Z-LES-1` (hinweis)
    - `Z-GEW-1` (Gewinde mit Bezeichnung und Tiefe)
    - `Z-DRE-1` (Ø an Durchmessern)
  - Quelle und Beleg übernimmst du aus der Herkunftsspalte von Design §8.1 und der Recherche („Nutzer 16.11.2026“, „R-Kap. 4 A“ …). Erfinde keine Normstellen.
  - `regeln.py`: `@dataclass(frozen=True) Regel(id, pruefung, text, quelle, beleg, art)`. Dazu `lade_regeln(pfad=None) -> list[Regel]` und `regel(regeln, id) -> Regel` (KeyError mit ID im Text).
  - `ist.py` (alles frozen dataclasses, Werte in mm, Winkel in Grad):
    - `IstToleranz(typ: str, passung: str | None, oben: float | None, unten: float | None)` mit typ ∈ keine, bilateral, grenz, symmetrisch, passung.
    - `IstMass(name, ansicht, art, wert, praefix, suffix, klammer: bool, toleranz: IstToleranz, richtung: str | None, punkte: tuple | None, verdeckt: bool | None)` mit art ∈ laenge, durchmesser, radius, winkel; richtung h/v nur bei laenge; punkte = zwei Bezugspunkte in Blatt-mm.
    - `IstAngabe(art, ansicht, text, symbol: str | None, wert: str | None, bezug: tuple[str, ...])` mit art ∈ hinweis, rauheit, form_lage, bezug.
    - `IstAnsicht(name, rolle: str | None, art, massstab: str, beschriftung: str | None)` mit art ∈ ansicht, schnitt, einzelheit.
    - `Ist(format_, massstab, ansichten, masse, angaben, eigenschaften: dict[str, str], sha256_slddrw)`.
    - `ist_zu_dict(ist) -> dict` und `ist_aus_dict(d) -> Ist` (Rundreise, Tupel ↔ Listen).

- [ ] **Step 1: Tests**
  - `test_regeln_vollstaendig`: Jede der neun Prüfungen hat mindestens eine Regel. Die IDs sind eindeutig. Jede Regel hat nicht leere `quelle` und `text`. `art` ∈ {hart, hinweis}. `Z-LES-1` ist hinweis.
  - `test_regel_unbekannt`: `regel(lade_regeln(), "Z-XX-9")` wirft KeyError mit „Z-XX-9“ im Text.
  - `test_ist_rundreise`: Ein Ist mit je einem Maß (Toleranz Passung H7, Suffix „ Ⓔ“, Punkte), einer Angabe je Art und zwei Ansichten. Es gilt `ist_aus_dict(json.loads(json.dumps(ist_zu_dict(ist)))) == ist`.
- [ ] **Step 2–4:** rot, umsetzen, grün (`pytest tests/zeichnung -q`).
- [ ] **Step 5:** Commit.

### Task 2: Prüfungen der Maße und Ansichten

**Files:**
- Create: `swki/zeichnung/pruefen.py`, `tests/zeichnung/ist_bau.py` (Testhelfer), `tests/zeichnung/test_pruefen_masse.py`

**Interfaces:**
- Consumes: Task 1, `massplan.Mass` (Felder siehe `swki/zeichnung/massplan.py`), `Toleranz`/`toleranztext` aus `toleranzangaben.py`, `angaben.zahl`.
- Produces in `pruefen.py` (jede Funktion gibt ein Prüfungs-dict der Form aus den Global Constraints zurück):
  - `pruefe_vollstaendig(ist: Ist, plan: list[Mass], regeln) -> dict` (Entscheidung 1).
    - Plan-Einträge mit quelle modell/neu werden gegen `ist.masse` abgeglichen, Einträge mit quelle angabe gegen Notizen (`IstAngabe.art == "hinweis"`, `text.startswith(m.text)`).
    - Abgleich laenge ↔ laenge, durchmesser ↔ durchmesser, radius ↔ radius, winkel ↔ winkel. Ist-Maße in Klammern zählen nicht.
    - Mängel: `{merkmal, text: "fehlt: Ø8 (st)"}` mit Regel Z-VOLL-1 bzw. `"doppelt: 150"` mit Regel Z-VOLL-2.
  - `pruefe_ueberbestimmt(ist, regeln) -> dict` (Entscheidung 2). Union-Find oder DFS je (ansicht, richtung). Knoten sind `round(koordinate / 0.05)` der Messrichtung (`h` → x der Punkte, `v` → y).
  - `pruefe_ansichten(ist, regeln) -> dict`:
    - `verdeckt is True` → Mangel Z-ANS-1.
    - Schnittansicht ohne `beschriftung` → Mangel Z-ANS-2.
    - Einzelheit ohne Maßstab oder mit Maßstab außerhalb der Vorzugsreihe → Mangel Z-ANS-3.
  - `pruefe_drehteil(ist, plan, regeln) -> dict`: Jedes Ist-Maß der art durchmesser beginnt im angezeigten Text mit „Ø“ (Präfix oder Teil des Werts laut Rücklesen). Ist das Teil kein Drehteil, gilt `ok: null` mit Hinweis „kein Drehteil“.
  - `pruefe_gewinde(ist, plan, regeln) -> dict`: Jede Plan-Angabe eines Gewindes (Text beginnt mit `M` oder enthält „ × M“) hat eine Notiz mit Bezeichnung und „tief“.
  - `VORZUGSMASSSTAEBE: tuple[str, ...]` (Entscheidung 5).
- `tests/zeichnung/ist_bau.py`: `ideal_ist(plan: list[Mass], ansichten: dict[str, str] | None = None) -> Ist` baut ein Ist so, wie die Zeichnung sein soll.
  - Je Maß ein `IstMass` mit Toleranz aus `m.toleranz` und Präfix „Ø“ bei Durchmessern.
  - Je Angabe eine Notiz mit `m.text`.
  - Bezugspunkte so, dass jede Richtung eine Bezugsbemaßung ist: alle Maße einer Richtung starten bei 0.
- Nutze die Fixture-Protokolle aus `tests/zeichnung/test_massplan.py` (`_spannplatte_protokoll()`, `_buchse_protokoll()`, `_lade_ref`). Lege sie bei Bedarf als Funktionen in `ist_bau.py` neu an. Kopiere keine Plan-Werte von Hand.

- [ ] **Step 1: Tests** (Negativfälle Design §10)
  - `test_ideal_vollstaendig`: Der Plan der Spannplatte Z ergibt mit `ideal_ist(plan)` `ok is True`.
  - `test_fehlendes_mass`: Ein lineares Maß wird entfernt → `ok is False` und ein Mangel mit Regel `Z-VOLL-1`, der Wert steht im Text.
  - `test_doppeltes_mass`: Ein Maß wird dupliziert (andere Ansicht) → `Z-VOLL-2`.
  - `test_gleicher_wert_zwei_merkmale` (Review Focus 2): Zwei Plan-Maße mit Wert 20 und beide im Ist → ok. Fehlt eines → `Z-VOLL-1`.
  - `test_geschlossene_kette`: In Ansicht „haupt“, Richtung h, liegen 0–50, 50–80 und 0–80, alle ohne Klammer → `pruefe_ueberbestimmt` `ok is False` mit `Z-UEB-1`.
  - `test_hilfsmass_in_klammern` (Review Focus 3): wie oben, 0–80 mit `klammer=True` → ok.
  - `test_mass_an_verdeckter_kante`: Ein Maß mit `verdeckt=True` → `Z-ANS-1`.
  - `test_schnitt_ohne_bezeichnung` und `test_einzelheit_massstab_3zu1`: jeweils ein Mangel.
  - `test_durchmesser_ohne_zeichen`: Bei der Buchse Z fehlt an einem Ø-Maß „Ø“ → `Z-DRE-1`.
  - `test_gewinde_ohne_tiefe`: Aus der Gewinde-Notiz der Spannplatte Z wird „tief“ entfernt → `Z-GEW-1`.
- [ ] **Step 2–4:** rot, umsetzen, grün.
- [ ] **Step 5:** Commit.

### Task 3: Prüfungen der Angaben, Gesamturteil

**Files:**
- Modify: `swki/zeichnung/pruefen.py`, `tests/zeichnung/ist_bau.py`, `config/standard.yaml` (`zeichnung.schriftfeld`)
- Test: `tests/zeichnung/test_pruefen_angaben.py`

**Interfaces:**
- Consumes: Task 1, Task 2, `sammelangaben(spec)` und `SAMMEL_RAUHEIT` aus `toleranzangaben.py`.
- Produces:
  - `pruefe_toleranzen(ist, plan, regeln) -> dict`. Plan-Maße mit Toleranz werden über den Abgleich aus Task 2 einem Ist-Maß zugeordnet. Die Hilfsfunktion `zuordnen(ist, plan) -> dict[str, IstMass | None]` gilt je Plan-ID; Task 2 nutzt sie mit.
    - `Z-TOL-1`: Passung oder Abmaße weichen ab (Vergleich auf 0,0005 mm).
    - `Z-TOL-2`: Das Suffix enthält „Ⓔ“, aber die Plan-Toleranz hat `huelle` False oder ist None.
    - `Z-TOL-3`: Ein Ist-Maß hat eine Toleranz (`typ` ≠ keine), das zugeordnete Plan-Maß hat keine.
    - `Z-TOL-4/5/6`: Rauheit, Form/Lage (Symbol, Wert, Bezug) und Bezüge (Buchstabe) aus den Plan-Einträgen der quelle rauheit, form_lage und bezug fehlen in `ist.angaben` oder weichen ab. Der Abgleich läuft je Merkmal, nicht über die Ansicht.
  - `pruefe_sammelangaben(ist, spec, regeln) -> dict`. Der Text aller Notizen, whitespace-normalisiert, muss jede Zeile von `sammelangaben(spec)` enthalten (`Z-SAM-1/2/4/5/6`) sowie `SAMMEL_RAUHEIT` (`Z-SAM-7`).
    - Verboten (`Z-SAM-3`) sind `re.search(r"2768-\s*\d?\s*[fmcv]?\s*K", text)` und „DIN 7167“.
  - `pruefe_schriftfeld(ist, standard: dict, regeln) -> dict` (Entscheidung 3). Die Werte kommen aus `ist.eigenschaften` über `standard["zeichnung"]["schriftfeld"]`.
    - `Z-SCH-1`: Ein Pflichtfeld ist leer. Eigentümer leer ist nur ein Hinweis.
    - `Z-SCH-2`: „Freigegeben“ ist gefüllt.
    - `Z-SCH-3`: Der Blatt-Maßstab liegt nicht in `VORZUGSMASSSTAEBE`.
  - `pruefe_lesbarkeit(pdf: Path | None, format_: str, regeln) -> dict` (Entscheidung 4). Ohne PDF gilt `ok: null`.
  - `bewerte(ist, plan, spec, standard, regeln, pdf=None, meldungen=()) -> dict`. Ergebnis: `{bestanden, pruefungen: [...9], maengel: [{pruefung, regel, merkmal, text}], meldungen}`.
    - `bestanden` ist True, wenn keine harte Prüfung `ok is False` hat.
    - Hinweisregeln (`art: hinweis`) machen nie `ok False`.
  - In `config/standard.yaml` unter `zeichnung:` kommt dazu: `schriftfeld: {eigentuemer: "", sachnummer: Zeichnungsnummer, titel: Benennung, ersteller: DrawnBy, ausgabedatum: DrawnDate, dokumentart: Dokumentart, blatt: Blatt, freigegeben: Freigegeben}`. Die Werte sind Eigenschaftsnamen der Zeichnung, `eigentuemer` ist leer bis Z1.5. Kommentar: Design §7, Z1.5 ersetzt die Namen. `blatt` liefert der Rückleser aus dem Blatt (Nummer/Anzahl), nicht aus einer Eigenschaft.
  - `ideal_ist` bekommt `spec` und `eigenschaften` als optionale Parameter. Daraus setzt es Sammelangaben-Notizen und Schriftfeld-Eigenschaften.

- [ ] **Step 1: Tests**
  - `test_ideal_spannplatte_z_bestanden` und `test_ideal_buchse_z_bestanden`: `bewerte(ideal_ist(...), plan, spec, standard, regeln)["bestanden"] is True`.
  - `test_ideal_ohne_anforderungen_bestanden` (Review Focus 1): Für `stil/spannplatte.yaml` gilt bestanden. `sammelangaben` liefert hier die vier festen Zeilen.
  - `test_falsche_passung`: H7 → H8 am Ist von D_innen (Buchse Z) ergibt `Z-TOL-1`, der Text nennt beide Werte.
  - `test_huelle_an_nicht_passmass` (Review Focus 4): „ Ⓔ“ an das Maß mit Abmaß ±0,02 (Spannplatte Z, Parameter A) → `Z-TOL-2`. An H7 kein Mangel.
  - `test_toleranz_ohne_funktion`: Ein untoleriertes Plan-Maß hat im Ist ±0,1 → `Z-TOL-3`.
  - `test_rauheit_fehlt`, `test_form_lage_falscher_wert` (0,02 → 0,05), `test_bezug_fehlt`.
  - `test_iso_2768_mk`: Notiz „Allgemeintoleranzen ISO 2768-mK“ → `Z-SAM-3`. Varianten „ISO 2768-1 mK“ und „2768 - mK“ ebenfalls. „ISO 2768-1:1989 – m“ ist kein Treffer.
  - `test_pflichtfeld_fehlt`: Benennung leer → `Z-SCH-1`. Eigentümer leer → nur Hinweis, bestanden bleibt True.
  - `test_freigegeben_gefuellt` und `test_massstab_3zu1`.
  - `test_lesbarkeit_ist_hinweis`: Mit einem PDF mit Befund (vorhandene Test-PDF aus `tests/zeichnung/daten`, falls es eine gibt, sonst `monkeypatch` von `pruefe_pdf`) gilt `ok is None` und bestanden bleibt True.
- [ ] **Step 2–4:** rot, umsetzen, grün (`pytest tests/zeichnung tests/test_konfig.py -q`).
- [ ] **Step 5:** Commit.

### Task 4: Rückleser und `swki zeichnung pruefen` (live, gesperrt bis SolidWorks frei und Stufe 4 Task 5 fertig)

**Files:**
- Create: `swki/zeichnung/rueckleser.py`, `tests/live/test_live_zeichnung_pruefen.py`
- Modify: `swki/zeichnung/befehle.py` (Unterbefehl `zeichnung pruefen`), `swki/zeichnung/zeichnen.py` (`_eigenschaften`: `Dokumentart`), `tests/zeichnung/test_zeichnen_ohne_sw.py`

**Interfaces:**
- Consumes: Tasks 1–3; `zeichnen._bezuege(dd)` (Richtung und Bezugspunkte linearer Maße, schon live erprobt), `bemassen._anzeige`, `kurzname`.
- Produces:
  - `lies_zeichnung(app, slddrw: Path, rollen: dict[str, str]) -> Ist` (COM).
    - `IView` je Blatt: Name, `ScaleDecimal` → „n:m“, Art. Die Schnittbezeichnung liest `IView.GetSection`/Label bzw. `IDetailCircle`, nachschlagen.
    - Maße mit Wert, `GetText(1/2)`, Klammer, `Tolerance` (Type, Fit, Werte) und `_bezuege`. `verdeckt` aus den angehängten Entitäten gegen `GetVisibleEntities2`. Ist das nicht bestimmbar, gilt None.
    - Notizen (`GetFirstNote`/`GetNext`), `GetFirstGTOL`, `GetFirstDatumTag`, `GetFirstSFSymbol` (wie `spikes/z1_diag_stufe4.py`).
    - Eigenschaften über `CustomPropertyManager.Get6`.
    - Öffnet die Zeichnung ohne Speichern und schließt sie wieder.
  - `kopf_pruefung(sha_ist: str, uebergabe: dict) -> list[str]` (rein): Ist `sha_ist != uebergabe["sha256_slddrw"]`, entsteht `["ZEICHNUNG_GEAENDERT: <name> weicht von der Übergabe ab (Handänderung?) – swki aenderungen"]`. Bei fehlender Übergabe entsteht `ZEICHNUNG_UEBERGABE_FEHLT` und der Befehl bricht mit `ZeichnungFehler` ab.
  - `zeichnung_pruefen(spec_pfad: Path, lauf: int | None = None) -> dict`:
    - Lauf wie `waehle_lauf`.
    - Liest `lauf-<n>/zeichnung/zeichnung.json` und die freigegebene Spec (`freigegebene_spec`).
    - Plan neu: `massplan(soll, protokoll)`. Weicht er nach Wirkung vom Übergabe-Plan ab, kommt die Meldung `ZEICHNUNG_PLAN_VERALTET`.
    - Danach `lies_zeichnung` und `bewerte`. Das Ergebnis enthält zusätzlich `ist`, `pdf`, `png`, `zeichnung`. Es wird über `schreibe_uebergabe` als `lauf_datei(spec, lauf, "zeichnung-pruefbericht")` geschrieben.
    - SHA von SLDDRW und SLDPRT vor und nach dem Rücklesen sind gleich, sonst `ZeichnungFehler("ZEICHNUNG_PRUEFUNG_AENDERT", …)`.
  - CLI: `swki zeichnung pruefen <spec> [--lauf N]`. `swki zeichnen` bleibt unverändert.
- [ ] **Step 1: Unit-Tests** (ohne SolidWorks)
  - `kopf_pruefung` für SHA gleich, SHA abweichend (Review Focus 5) und fehlende Übergabe.
  - `_eigenschaften` setzt `Dokumentart`, geprüft mit einem Fake-CustomPropertyManager.
  - Der CLI-Parser kennt `zeichnung pruefen`.
- [ ] **Step 2: API nachschlagen** für jeden neuen Aufruf (`swki api methode IView.GetFirstNote` usw.); Ergebnis in den Docstring.
- [ ] **Step 3: Umsetzen**, dann `swki api pruefe-code swki/zeichnung/rueckleser.py`.
- [ ] **Step 4: Live** (nur nach Freigabe):
  - `swki zeichnen` und `swki zeichnung pruefen` für Spannplatte Z und Buchse Z im Auftrag `Z1-STUFE4`.
  - Erwartet: bestanden oder nur echte Mängel. Jeder Mangel wird erklärt, ein Fehler im Rückleser wird behoben.
  - SHA-Prüfung grün.
- [ ] **Step 5: Commit.**

### Task 5: Agent `zeichnungspruefer`, `durchlauf --zeichnung`, Bericht

**Files:**
- Create: `.claude/agents/zeichnungspruefer.md`
- Modify: `swki/durchlauf.py`, `swki/pruefung/befehle.py` (`bericht`), `swki/pruefung/bericht*.py` (dort, wo `bericht_markdown` liegt), `.claude/skills/konstruieren/SKILL.md` (Abschnitt Zeichnung), `CLAUDE.md` (Abschnitt Zeichnungsableitung, eine Zeile)
- Test: `tests/test_durchlauf.py`, `tests/pruefung/…` (zum Bericht passend)

**Interfaces:**
- Produces:
  - Agent-Datei nach dem Muster von `.claude/agents/pruefer.md`, Werkzeuge nur Read und Glob.
    - Eingaben: Eingabe des Nutzers, freigegebene Spec, Zeichnungs-Prüfbericht, PDF bzw. PNG, `swki/wissen/zeichnungsregeln.yaml`. Keine Bauprotokolle, kein `zeichnung.json`-Plan als Maßstab, nur als Liste.
    - Checkliste aus Design §8.2: fertigen und prüfen ohne Rückfrage; kein Maß zu rechnen; keine Toleranz ohne Funktion; Darstellung eindeutig.
    - Mängel, die schon im Prüfbericht stehen, werden nicht wiederholt.
    - Urteil nur als JSON-Objekt: `{"urteil": "bestanden" | "maengel", "maengel": [{"merkmal", "regel", "text"}], "hinweise": [...]}`.
  - `zeichnungspruefer_auftrag(spec_pfad: Path, lauf: int, bericht: dict) -> str` in `durchlauf.py`. Fertiger Prompt wie `pruefer_auftrag`, Pfade als Dateien, Ende: „Antworte nur mit dem JSON-Urteil.“
  - `durchlauf(..., zeichnung: bool = False)`:
    - Nach bestandener Teil-Prüfung kommt *kein* automatisches Zeichnen. Das Teil braucht zuerst das Prüfer-Urteil (`waehle_lauf`).
    - Deshalb gilt: Ist der letzte Lauf bestanden (inkl. Prüfer), zeichnet `durchlauf --zeichnung` diesen Lauf und prüft die Zeichnung, ohne neu zu bauen.
    - Sonst läuft der normale Durchlauf, und `naechstes` nennt „Prüfer-Agent, danach swki durchlauf --zeichnung“.
    - Ergebnis: `zeichnung: {pdf, bestanden, maengel, meldungen}`, `zeichnungspruefer_auftrag`, `naechstes`.
    - Option `--zeichnung` in `einrichten`.
  - `bericht`: Hat der letzte Lauf einen `zeichnung-pruefbericht`, kommt ein Abschnitt „Zeichnung“ dazu (PDF, maschinelles Ergebnis, Prüfer-Urteil). Fehlt `zeichnungspruefer.json`, steht dort `ZEICHNUNGSPRUEFER_FEHLT`, und der Status sagt „Zeichnung ungeprüft“.
- [ ] **Step 1: Tests** (monkeypatch wie in `tests/test_durchlauf.py`)
  - `--zeichnung` mit bestandenem letzten Lauf: kein Bauen, Zeichnen und Prüfen aufgerufen, der Auftrag enthält den Prüfbericht-Pfad und das PDF.
  - Ohne bestandenen Lauf: `naechstes` nennt den Prüfer.
  - Bericht mit Zeichnungs-Prüfbericht ohne Urteil → `ZEICHNUNGSPRUEFER_FEHLT` im Text.
  - Die Agent-Datei existiert, nennt `zeichnungsregeln.yaml` und hat `tools: Read, Glob`.
- [ ] **Step 2–4:** rot, umsetzen, grün (`pytest -q -x`).
- [ ] **Step 5:** Commit.

### Task 6: Live-Regression mit Negativfällen, Prüfer-Lauf, Ergebnisse (gesperrt wie Task 4)

**Files:**
- Modify: `tests/live/test_live_zeichnung_pruefen.py`, `docs/zeichnungsableitung/ergebnisse.md`, `tests/referenz` (Regressions-Einträge, wie beim Zeichnen-Live-Test)

- [ ] **Step 1:** Live-Negativtest: Eine Kopie der Spannplatten-Zeichnung im Laufordner wird per COM manipuliert:
  - Maß löschen, Passung H7 → H8, „ Ⓔ“ an das ±0,02-Maß.
  - Notiz „ISO 2768-mK“ einfügen, `Benennung` leeren.
  - Die Kopie speichern und mit `lies_zeichnung` + `bewerte` prüfen.
  - Erwartet: `Z-VOLL-1`, `Z-TOL-1`, `Z-TOL-2`, `Z-SAM-3`, `Z-SCH-1`. Das Original bleibt unverändert (SHA).
  - Die Fälle „Kette“ und „verdeckte Kante“ sind nur als Unit-Tests abgedeckt; das wird begründet.
- [ ] **Step 2:** `zeichnungspruefer` auf beiden Referenzzeichnungen laufen lassen, Urteil unverändert nach `protokolle/<spec>.lauf-<n>.zeichnungspruefer.json`.
- [ ] **Step 3:** PDFs selbst ansehen und dann `docs/zeichnungsableitung/ergebnisse.md` ergänzen:
  - Z1.4-Abschnitt: Befehle, Regeln, Negativfälle, Grenzen (Entscheidung 2).
  - markierte Vorschläge (Entscheidungen 1–5).
  - Effekt der 20-mm-Reserve aus Stufe 4.
- [ ] **Step 4:** Commit.
