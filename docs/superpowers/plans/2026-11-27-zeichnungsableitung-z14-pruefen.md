# Zeichnungsableitung Z1.4 (Zeichnung prüfen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `swki zeichnung pruefen` liest eine von `swki zeichnen` erzeugte Zeichnung zurück und prüft sie maschinell gegen die freigegebene Spec, den Maßplan und `swki/wissen/zeichnungsregeln.yaml`. Danach urteilt der Agent `zeichnungspruefer`. `swki durchlauf --zeichnung` hängt beides an.

**Architecture:** Das Rücklesen (COM, `rueckleser.py`) erzeugt ein reines Ist-Modell (`ist.py`, als JSON ablegbar). Alle Prüfungen (`pruefen.py`) sind reine Funktionen über Ist, Maßplan, freigegebene Spec, Regelkatalog und PDF. Die Negativfälle aus Design §10 sind deshalb ohne SolidWorks testbar. Live kommen nur das Rücklesen und eine kleine Regression mit manipulierten Kopien dazu.

**Tech Stack:** Python 3, pywin32 (nur Task 4b/6), pymupdf (PDF-Texte), pytest, PyYAML.

**Spec:** `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md` §8 (Prüfen), §10 (Negativfälle); Recherche `docs/zeichnungsableitung/recherche.md` Kap. 2 (ISO 7200, ISO 5455), Kap. 4/8 (Überbestimmung), Kap. 7 (Sammelangaben).

## Global Constraints

- Kein SolidWorks in Task 1–3, 4a und 5. Task 4b und 6 erst, wenn der Organizer SolidWorks freigibt. Vor jedem Live-Lauf offene Dokumente prüfen; bei fremden Dokumenten nicht neu starten.
- Rücklesen ändert nichts: SHA-256 von SLDDRW und SLDPRT sind vor und nach `swki zeichnung pruefen` gleich. Geschlossen wird ohne Speichern (`CloseAllDocuments(True)` nur, wenn außer den eigenen Dokumenten nichts offen ist, sonst `sw.schliesse` je Dokument).
- Jeder neue SolidWorks-API-Aufruf wird vorher mit `swki api methode|enum` nachgeschlagen und muss in SW 2025 verfügbar sein (`swki api pruefe-code`).
- Prüfbericht: `protokolle/<spec>.lauf-<n>.zeichnung.pruefbericht.json` (Name wie Design §8.1), also `lauf_datei(spec, lauf, "zeichnung.pruefbericht")`. Prüfer-Urteil: `protokolle/<spec>.lauf-<n>.zeichnungspruefer.json`. Der Regex in `lauf_nummern_dateien` trifft keinen der beiden Namen, und `lies_laeufe` liest nur `pruefbericht` und `pruefer`. Ein Test hält das fest.
- Soll ist die freigegebene Spec, nicht nur der Maßplan. Was `massplan_meldungen(soll, protokoll)` als nicht gezeichnet meldet, ist in der Zeichnung ein Mangel und kein stiller Ausfall. `TOLERANZ_OHNE_MASS`, `TOLERANZ_MEHRDEUTIG` (der unterlegene Parameter) und `FORM_LAGE_IT_OHNE_TABELLE` werden zu `Z-TOL-1`, `MASS_NICHT_GEPLANT` zu `Z-VOLL-1`. `FUNKTION_UNBESTAETIGT` bleibt ein Hinweis.
- „Nicht prüfbar“ ist nie „ok“. Ein Ist-Feld mit `None` (z. B. `verdeckt`) ergibt in der betroffenen Prüfung `ok: null` mit Anzahl und Grund, außer die Prüfung hat schon einen harten Mangel.
- Der Prüfer wird nie übersprungen. Ein Lauf mit Zeichnung, aber ohne `zeichnungspruefer.json`, gilt in `swki bericht` als „Zeichnung ungeprüft“ (Meldung `ZEICHNUNGSPRUEFER_FEHLT`).
- Prüfungen haben die Form `{id, regeln: [IDs], ok: true|false|null, maengel: [{regel, merkmal, text}], hinweis?}`, wie im Teil-Prüfbericht. `ok: null` heißt Hinweisregel oder nicht prüfbar, immer mit Begründung.
- Ausgaben an den Nutzer in mm mit Dezimalkomma (`angaben.zahl`).

## Entscheidungen (selbst entschieden, im Ergebnisbericht als Vorschlag markiert)

1. **Abgleich Ist ↔ Plan** als Multimenge je `(Ist-Art, wert auf 0,01 mm)`, unabhängig von der Ansicht.
   - Plan-Art → Ist-Art: `laenge`, `lage`, `tiefe`, `abstand`, `paarabstand`, `fase` → `laenge`; `durchmesser` → `durchmesser`; `radius` → `radius`; `winkel` → `winkel`.
   - Das sind die Arten in den Plänen von Spannplatte Z und Buchse Z. Eine unbekannte Plan-Art ergibt einen Mangel `Z-VOLL-1` mit dem Text „Art <x> nicht prüfbar“, kein stilles Weglassen. Die Tabelle steht als Konstante `IST_ART` in `pruefen.py`.
   - Zum Wert: Bei `abstand` mit Präfix „n × “ wird die Teilung (Plan-`wert`) verglichen, nicht die Summe im Text. Bei `fase` die Fasenlänge. Weniger Ist als Plan → `fehlt`, mehr → `doppelt`. Angaben (Bohrung, Gewinde) werden über den Textanfang der Notiz abgeglichen. Der Abgleich nach Wirkung ist robust gegen Maßnamen, die SolidWorks beim Einfügen vergibt.
2. **Überbestimmt:** Der Maßgraph gilt je Ansicht und Richtung (`h`/`v`). Knoten sind Bezugskoordinaten (Blatt-mm, auf 0,05 mm gerundet), Kanten die linearen Maße ohne Klammer. Ein Zyklus bedeutet einen Mangel. Maße in verschiedenen Ansichten gelten als unabhängig, weil die Projektion keine gemeinsamen Blattkoordinaten hat. Diese Grenze ist bekannt und als Hinweis im Bericht vermerkt.
3. **Schriftfeld (ISO 7200, acht Pflichtfelder):**
   - Die Zuordnung Pflichtfeld → Eigenschaft steht in `config/standard.yaml` unter `zeichnung.schriftfeld`.
   - Hart geprüft werden Benennung, Sachnummer, Ersteller, Ausgabedatum, Dokumentart und Blatt.
   - Eigentümer ist nur ein Hinweis (`ok: null`), bis die Firmenvorlage (Z1.5) den Wert liefert. „Freigegeben“ bleibt leer, ein gefülltes Feld vor der Abnahme ist ein Mangel.
   - `swki zeichnen` setzt zusätzlich `Dokumentart: Einzelteilzeichnung` (Hausregel bis Z1.5).
4. **Lesbarkeit** prüft das PDF mit `lesbarkeit.pruefe_pdf` (wie beim Zeichnen). Die Regel ist ein Hinweis (Design §8.1: „R-Kap. 4 B (Hinweis)“): Befunde stehen in `maengel`, `ok` ist bei Befunden `null`, sonst `true`.
5. **Maßstab aus der Vorzugsreihe** (ISO 5455): 1:1, 1:2, 1:5, 1:10, 1:20, 1:50, 1:100, 2:1, 5:1, 10:1, 20:1, 50:1. Das gilt für das Blatt und jede Einzelheit.
6. **`durchlauf --zeichnung`** zeichnet den letzten bestandenen Lauf (Teil-Prüfer bestanden) und prüft ihn. Er baut nicht neu. Das Teil-Prüfer-Urteil ist Voraussetzung für `swki zeichnen` (Design §5), deshalb kann ein einziger Aufruf nicht bauen, prüfen und zeichnen. Der Auftrag des Organizers nennt `durchlauf --zeichnung`; diese Lesart wird als Vorschlag markiert.

## Review Focus

1. Ein Teil ohne jede Anforderung (alte Spec) besteht die Prüfung mit einem idealen Ist. Kein Mangel stammt aus Sammelangaben, die heute noch nicht gesetzt sind. → Test `test_ideal_ohne_anforderungen_bestanden` in Task 3.
2. Zwei Maße gleichen Werts (z. B. zweimal 20) an verschiedenen Merkmalen: Fehlt eines, wird es gemeldet; sind beide da, ist es kein Doppelmaß. → Test in Task 2.
3. Hilfsmaß in Klammern schließt eine Kette, ohne dass ein Mangel entsteht. → Test in Task 2.
4. Ⓔ an einem Maß, dessen Plan-Toleranz eine reine Abmaßtoleranz ist (keine Passung), ist ein Mangel. Ⓔ an einer Passung ist keiner. → Test in Task 3.
5. Die Zeichnung wurde nach `swki zeichnen` von Hand geändert (SHA ≠ `sha256_slddrw` der Übergabe). Die Prüfung läuft trotzdem und meldet `ZEICHNUNG_GEAENDERT` in `meldungen`. Sie bricht nicht ab und behauptet auch nicht still „bestanden“. → Test in Task 4a (`kopf_pruefung`).

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
    - Textzusätze (Advisor nach Spike 27.11.: Die Stufe-3-Zusätze fehlten in der wieder geöffneten SLDDRW): Ein zugeordnetes Ist-Maß muss Präfix und Suffix des Plans enthalten, Leerraum normalisiert. Plan „4 × “ / „ (= 120)“ und Ist ohne diese Zusätze → Mangel Z-VOLL-1 mit dem Text „Zusatz fehlt: 4 × 30 (= 120)“. Die Zuordnung je Plan-ID macht `zuordnen(ist, plan) -> dict[str, IstMass | None]`. Sie entsteht in diesem Task, Task 3 nutzt sie mit.
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
  - `test_zusatz_fehlt`: Beim Maß D3@m1 der Spannplatte Z fehlen im Ist Präfix und Suffix → `Z-VOLL-1` mit „Zusatz fehlt“. Bei der Fase (Buchse Z, Suffix „ × 45°“) gilt dasselbe.
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
  - `soll_luecken(meldungen_soll: list[str]) -> list[dict]`: Macht aus `massplan_meldungen(soll, protokoll)` Mängel nach den Global Constraints. Die Mängel landen in den Prüfungen `toleranzen` bzw. `vollstaendig`.
  - `bewerte(ist, plan, spec, standard, regeln, pdf=None, meldungen=(), meldungen_soll=()) -> dict`. Ergebnis: `{bestanden, pruefungen: [...9], maengel: [{pruefung, regel, merkmal, text}], meldungen}`.
    - `bestanden` ist True, wenn keine harte Prüfung `ok is False` hat.
    - Hinweisregeln (`art: hinweis`) machen nie `ok False`.
  - In `config/standard.yaml` unter `zeichnung:` kommt dazu: `schriftfeld: {eigentuemer: "", sachnummer: Zeichnungsnummer, titel: Benennung, ersteller: DrawnBy, ausgabedatum: DrawnDate, dokumentart: Dokumentart, blatt: Blatt, freigegeben: Freigegeben}`. Die Werte sind Eigenschaftsnamen der Zeichnung, `eigentuemer` ist leer bis Z1.5. Kommentar: Design §7, Z1.5 ersetzt die Namen. `blatt` liefert der Rückleser aus dem Blatt (Nummer/Anzahl), nicht aus einer Eigenschaft. *(Überholt, Review 4b M5 /
    Gesamtreview M1: der Rückleser erfindet kein Blatt; fehlt die Eigenschaft, ist das Feld bis Z1.5 nicht geprüft.)*
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
  - `test_soll_luecke_toleranz` (Advisor): `buchse_z` mit `toleranzen.GIBTSNICHT: {passung: h9}`. Die Meldungen kommen aus `massplan_meldungen`, das Ergebnis ist nicht bestanden, mit `Z-TOL-1` und „GIBTSNICHT“ im Text. Ebenso `TOLERANZ_MEHRDEUTIG` und `MASS_NICHT_GEPLANT` → `Z-VOLL-1`. `FUNKTION_UNBESTAETIGT` lässt bestanden True.
  - `test_verdeckt_unbekannt`: Alle Maße mit `verdeckt=None` → Prüfung `ansichten` `ok is None`, die Anzahl steht im Hinweis. bestanden bleibt True, der Bericht nennt die Lücke.
  - `test_lesbarkeit_ist_hinweis`: Mit einem PDF mit Befund (vorhandene Test-PDF aus `tests/zeichnung/daten`, falls es eine gibt, sonst `monkeypatch` von `pruefe_pdf`) gilt `ok is None` und bestanden bleibt True.
- [ ] **Step 2–4:** rot, umsetzen, grün (`pytest tests/zeichnung tests/test_konfig.py -q`).
- [ ] **Step 5:** Commit.

### Task 4a: `swki zeichnung pruefen` ohne Rückleser (rein, jetzt)

**Files:**
- Create: `swki/zeichnung/zeichnung_pruefen.py`
- Modify: `swki/zeichnung/befehle.py` (Unterbefehl `zeichnung pruefen`), `swki/zeichnung/zeichnen.py` (`_eigenschaften`: `Dokumentart`), `tests/zeichnung/test_zeichnen_ohne_sw.py`
- Test: `tests/zeichnung/test_zeichnung_pruefen.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:
  - Die Orchestrierung `zeichnung_pruefen(spec_pfad, lauf=None, leser=None)` (unten). `leser` hat die Signatur `(slddrw: Path, rollen: dict[str, str]) -> Ist`. Vorgabe `None` heißt: spät `rueckleser.lies_zeichnung` mit eigener COM-Verbindung (Task 4b). Tests übergeben einen Fake-Leser mit `ideal_ist`.
  - `kopf_pruefung` (unten).
  - CLI.
  - `Dokumentart` in `_eigenschaften`.

### Task 4b: Rückleser (live, gesperrt bis SolidWorks frei und Stufe 4 Task 5 fertig)

**Files:**
- Create: `swki/zeichnung/rueckleser.py`, `tests/live/test_live_zeichnung_pruefen.py`

**Interfaces:**
- Consumes: Task 4a; `zeichnen._bezuege(dd)` (Richtung und Bezugspunkte linearer Maße, schon live erprobt), `zeichnen._kanten`, `bemassen._anzeige`, `kurzname`.
- Produces:
  - `lies_zeichnung(slddrw: Path, rollen: dict[str, str], app=None) -> Ist` (COM).
    - `IView` je Blatt: Name, `ScaleDecimal` → „n:m“, Art. Die Schnittbezeichnung liest `IView.GetSection`/Label bzw. `IDetailCircle`, nachschlagen.
    - Maße mit Wert, `GetText(1/2)`, Klammer, `Tolerance` (Type, Fit, Werte) und `_bezuege`.
    - Toleranz im Ist (Review Task 3, M2): `unten` mit Vorzeichen (negativ unter Nennmaß), `oben`/`unten` in mm. ±0,02 ergibt `typ: symmetrisch, oben 0,02, unten −0,02`, nicht (0,02/0,02). Wert über `GetSystemValue3`, bei Zeichnungsmaßen None, dann `GetSystemValue2("")` (Spike Stufe 4). Ⓔ kommt als `<MOD-EP>` im Suffix. Jede Angabe bekommt ihr `merkmal`, soweit das Rücklesen es über die angehängte Kante bestimmen kann. Ohne Merkmal wird überzähliges nur gemeldet (Task 3) – überholt durch Nachtrag 3 (Review 4b): ohne Merkmal ist eine Angabe nicht zuordenbar, ein harter Mangel der Art.
    - `verdeckt`: Beide Bezugspunkte aus `_bezuege` werden gegen die sichtbaren Kanten der Ansicht (`_kanten`, Blatt-mm) geprüft, mit 0,1 mm Toleranz. Liegt ein Punkt auf keiner sichtbaren Kante und auf keiner Mittellinie, ist das Maß verdeckt bzw. ohne sichtbaren Bezug (Nutzer Stufe 2: „Maß ohne sichtbaren Bezug“). Nicht lineare Maße ergeben None.
    - Notizen (`GetFirstNote`/`GetNext`), `GetFirstGTOL`, `GetFirstDatumTag`, `GetFirstSFSymbol` (wie `spikes/z1_diag_stufe4.py`).
    - Eigenschaften über `CustomPropertyManager.Get6`.
    - Nachtrag nach Stufe 4 Task 5 (Review 28.11.), verbindlich für den Rückleser:
      - Rauheit: Text aus `ISFSymbol.GetText(8)` (Feld a). Steht Text in Platz 3 (Feld c), meldet der Rückleser das als „weicht ab“.
      - Ⓔ: als `<MOD-EP>` im Maß-Suffix und im Hinweistext. `normtext` übersetzt es.
      - Form/Lage-Instanzen: „n ד über dem Rahmen aus `IGtol.GetText(3)` in ein neues Feld `IstAngabe.anzahl`. Das Soll liefert `anforderungen_setzen.instanzen(spec, merkmal)`. `pruefe_toleranzen` prüft die Anzahl (Z-TOL-5).
      - `RAUHEIT_NUR_EINE_INSTANZ` und `FORM_LAGE_NUR_EINE_INSTANZ` aus den Zeichnungsmeldungen der Übergabe werden in `soll_luecken` zu Mängeln Z-TOL-4 bzw. Z-TOL-5. Eine Anforderung an nur einer von n Instanzen ist ein Mangel.
      - Ebenso wird `ANMERKUNG_KREUZT` aus der Übergabe zu Z-LES-1 (Hinweisregel), `MASS_NICHT_DAUERHAFT` zu Z-VOLL-1.
      - Nachtrag 2 (Runde C, 28.11.): Die Zuordnung Meldungscode → Regel steht als Tabelle `MELDUNG_REGEL` in
        `pruefen.py` (`ANMERKUNG_KREUZT`, `ANGABE_ZU_NAH`, `ANSATZ_NICHT_FREI`, `LESBARKEIT` → Z-LES-1;
        `*_NICHT_GESETZT` → Regel der Angabe (Z-TOL-1/2/4/5, Bezug Z-TOL-6); `*_NUR_EINE_INSTANZ` → Z-TOL-4/5;
        `MASS_NICHT_DAUERHAFT`, `TOLERANZ_OHNE_MASS`, `TOLERANZ_MEHRDEUTIG`, `MASS_NICHT_GEPLANT` → Z-VOLL-1 bzw. Z-TOL-1;
        `FUNKTION_UNBESTAETIGT` nur Hinweis). Test `test_jeder_meldungscode_hat_regel`: Er sammelt per Regex alle Codes
        `"[A-Z][A-Z_]+:` aus `swki/zeichnung/*.py` und verlangt für jeden einen Eintrag (oder einen Eintrag in einer
        ausdrücklichen Liste „nur Bericht“ mit Begründung). Ein unbekannter Code in einer Übergabe wird Mangel Z-VOLL-1
        mit dem Text „unbekannte Zeichnungsmeldung“, nie still. `ANMERKUNG_KREUZT` hat das Format
        `<merkmal> <art> „<text>“ – <was> (<n>), …`; `<was>` ∈ Maßlinie, Text, Kante, Schraffur, Hinweislinie,
        Rechteck auf Linie, eigenes Symbol. Seit Runde D (08e1e2f) zusätzlich: `ANMERKUNG_ZU_NAH` (Nähe: „Kante näher als
        3 mm“, „Ansatz näher als 4 mm“) → Z-LES-1 als Hinweis; `SCHRAFFUR_UNGELESEN` → Z-LES-1 (Prüfung der Anmerkungen
        unvollständig, `ok None`); `EINZELHEIT_BUCHSTABE` und `SCHNITT_BUCHSTABE` (Runde E) → Z-ANS-2 (Bezeichnung der Ansicht). Die Einzelheit heißt ab Z rückwärts, Schnitte ab A vorwärts ohne I, O, Q und ohne Bezugsbuchstaben (SpannplatteZ: SCHNITT C-C); die Schnittbezeichnung liest der Rückleser über `IView.GetSection` → `IDrSection.GetLabel`.
        Bohrungsangaben: Umbruch und „ – “ sind gleichwertig (`pruefen.angabentext`).
      - Rauheit und Form/Lage werden nach Merkmal (über `enthalten`, also inklusive Spiegel- und Musterinstanzen) und
        Inhalt abgeglichen; der Wechsel des Ansatzes an eine gleichwertige Instanz ist kein Mangel.
      - Merkmal je Angabe: über die angehängte Kante, mit derselben `enthalten`-Logik wie beim Setzen (Spiegel- und Musterinstanzen). Das Bezugsdreieck liefert das Merkmal nur über die angehängte Entität.
      - Maße: `zeichnungsmasse` aus der Übergabe (Modellmaß → `RD<n>@<Ansicht>`) ordnet umgewandelten Maßen den Plan-Namen zu.
      - Lesbarkeit: `pruefe_lesbarkeit` übergibt `pruefe_pdf` die gelegten Rahmen (`rahmen=`), mit dem Text der Form/Lage-Angaben und dem Rechteck aus dem PDF. Sonst gilt jede Rahmentrennlinie als Linie durch den Text.
      - `verdeckt`: dieselbe Streckenregel wie `anforderungen_setzen.kante_am_punkt`, also mit verlängerter Kante bei einer virtuellen Fasenecke. Bei nur 0,1 mm entstünde ein falscher Mangel „ohne sichtbaren Bezug“.
    - Öffnet die Zeichnung ohne Speichern und schließt sie wieder.
      - Nachtrag 3 (Review 4b, 28.11.): Ein Merkmal None ist nie ein Joker. Eine Angabe ohne Merkmal deckt keinen
        Plan-Eintrag und ist überzählig „ohne Merkmal, nicht zuordenbar“ (harter Mangel Z-TOL-4/5/6). Eine Kante
        zwischen mehreren Merkmalen, bei der der Inhalt nicht entscheidet, ergibt „a/b“; die Angabe deckt genau
        einen Eintrag eines dieser Merkmale. Rauheit, Form/Lage und Bezug ohne angehängte Kante meldet der
        Rückleser (`RUECKLESEN_UNVOLLSTAENDIG`), ebenso jedes lineare Maß mit unlesbaren Hilfslinien, mehrere
        Blätter und unlesbare Anmerkungen. `SAMMELANGABE_FEHLT` → Z-SAM-1, Sammelrauheit fehlt oder läuft über →
        Z-SAM-7, andere Zeile läuft über → Z-LES-1. „Blatt“ setzt der Rückleser nicht selbst; fehlt die
        Eigenschaft, ist das Feld nicht geprüft. Gedachte scharfe Ecke nur an einem tangentialen Bogen oder einer
        Fasenkante höchstens `mittellinien.ECKE_MM` von der Ecke. Geschlossen wird nur, was `OpenDoc6` geladen hat.

**Produces in Task 4a (Fortsetzung):**
  - `kopf_pruefung(sha_ist: str, uebergabe: dict) -> list[str]` (rein): Ist `sha_ist != uebergabe["sha256_slddrw"]`, entsteht `["ZEICHNUNG_GEAENDERT: <name> weicht von der Übergabe ab (Handänderung?) – swki aenderungen"]`. Bei fehlender Übergabe entsteht `ZEICHNUNG_UEBERGABE_FEHLT` und der Befehl bricht mit `ZeichnungFehler` ab.
  - `zeichnung_pruefen(spec_pfad: Path, lauf: int | None = None, leser=None) -> dict`:
    - Lauf wie `waehle_lauf`.
    - Liest `lauf-<n>/zeichnung/zeichnung.json` und die freigegebene Spec (`freigegebene_spec`).
    - Plan neu: `massplan(soll, protokoll)` und `massplan_meldungen(soll, protokoll)`. Weicht der Plan nach Wirkung vom Übergabe-Plan ab, kommt die Meldung `ZEICHNUNG_PLAN_VERALTET`.
    - Danach `leser(...)` und `bewerte(..., meldungen_soll=...)`. Das Ergebnis enthält zusätzlich `ist`, `pdf`, `png`, `zeichnung`. Es wird über `schreibe_uebergabe` als `lauf_datei(spec, lauf, "zeichnung.pruefbericht")` geschrieben.
    - SHA von SLDDRW und SLDPRT vor und nach dem Rücklesen sind gleich, sonst `ZeichnungFehler("ZEICHNUNG_PRUEFUNG_AENDERT", …)`.
  - CLI: `swki zeichnung pruefen <spec> [--lauf N]`. `swki zeichnen` bleibt unverändert.

Task 4a:
- [ ] **Step 1: Unit-Tests** (ohne SolidWorks; Laufordner und Protokolle in `tmp_path` wie in bestehenden Tests mit `lade_rechner`-Monkeypatch)
  - `kopf_pruefung` für SHA gleich, SHA abweichend (Review Focus 5) und fehlende Übergabe.
  - `zeichnung_pruefen` mit Fake-Leser (`ideal_ist`): Der Bericht liegt unter `…lauf-1.zeichnung.pruefbericht.json` und ist bestanden. `lies_laeufe` zählt ihn nicht als Teil-Prüfbericht.
  - Ein Fake-Leser, der eine Datei verändert → `ZEICHNUNG_PRUEFUNG_AENDERT`.
  - `_eigenschaften` setzt `Dokumentart`, geprüft mit einem Fake-CustomPropertyManager.
  - Der CLI-Parser kennt `zeichnung pruefen`.
- [ ] **Step 2–4:** rot, umsetzen, grün. **Step 5:** Commit.

Task 4b (gesperrt):
- [ ] **Step 1: API nachschlagen** für jeden neuen Aufruf (`swki api methode IView.GetFirstNote` usw.), Ergebnis in den Docstring.
- [ ] **Step 2: Umsetzen**, dann `swki api pruefe-code swki/zeichnung/rueckleser.py`.
- [ ] **Step 3: Live** (nur nach Freigabe):
  - `swki zeichnen` und `swki zeichnung pruefen` für Spannplatte Z und Buchse Z im Auftrag `Z1-STUFE4`.
  - Erwartet: bestanden oder nur echte Mängel. Jeder Mangel wird erklärt, ein Fehler im Rückleser wird behoben.
  - SHA-Prüfung grün.
  - `verdeckt` ist für alle linearen Maße bestimmt (kein None).
- [ ] **Step 4: Commit.**

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
  - `bericht`: Hat der letzte Lauf einen `zeichnung.pruefbericht`, kommt ein Abschnitt „Zeichnung“ dazu (PDF, maschinelles Ergebnis, Prüfer-Urteil). Fehlt `zeichnungspruefer.json`, steht dort `ZEICHNUNGSPRUEFER_FEHLT`, und der Status sagt „Zeichnung ungeprüft“.
- [ ] **Step 1: Tests** (monkeypatch wie in `tests/test_durchlauf.py`)
  - `--zeichnung` mit bestandenem letzten Lauf: kein Bauen, Zeichnen und Prüfen aufgerufen, der Auftrag enthält den Prüfbericht-Pfad und das PDF.
  - Ohne bestandenen Lauf: `naechstes` nennt den Prüfer.
  - Bericht mit Zeichnungs-Prüfbericht ohne Urteil → `ZEICHNUNGSPRUEFER_FEHLT` im Text.
  - Die Agent-Datei existiert, nennt `zeichnungsregeln.yaml` und hat `tools: Read, Glob`.
- [ ] **Step 2–4:** rot, umsetzen, grün (`pytest -q -x`).
- [ ] **Step 5:** Commit.

### Task 6: Live-Regression mit Negativfällen, Prüfer-Lauf, Ergebnisse (gesperrt wie Task 4b)

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
