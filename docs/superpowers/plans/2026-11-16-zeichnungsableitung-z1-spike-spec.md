# Zeichnungsableitung Z1.0 (Spike) und Z1.1 (Spec-Erweiterung) – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Der Spike klärt, welche Teile der Zeichnungsableitung die SolidWorks-API ohne Dialog trägt. Die Teil-Spec bekommt
die Anforderungsfelder für Funktion, Toleranz, Rauheit, Form/Lage, Verfahren, Behandlung und Halbzeug. Diese Felder sind
durch die Freigabe nach Wirkung geschützt und werden in `validieren` geprüft.

**Architecture:**
- Neue Feldgruppe im Schema (`$defs`), dazu fünf Top-Level-Felder.
- Regeltabelle `swki/wissen/funktionen.yaml` mit Lader und Auflösung in `swki/spec/funktionen.py`.
- Die Prüfsumme in `swki/spec/freigabe.py` nimmt die neuen Top-Level-Felder optional auf. Dazu kommt eine sortierte,
  doppelfreie Liste der Anforderungs-Tupel ohne Feature-IDs.
- Befunde in `swki/spec/laden.py`, Hinweise in `swki/spec/hinweise.py`.
- Der Spike ist ein Wegwerfskript unter `spikes/` und schreibt eine Befundnotiz.

**Tech Stack:** Python 3, jsonschema, PyYAML, pytest; Spike: pywin32/COM SolidWorks 2025.

**Spec:** `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md`. Recherche:
`docs/zeichnungsableitung/recherche.md`.

**Nicht in diesem Plan:**
- Z1.2: `freistich`, `zentrierbohrung` über den Skill `compiler-erweitern`.
- Z1.3/Z1.4: Zeichnen und Prüfen. Ihr Plan folgt nach dem Spike.
- Z1.5: Firmenvorlage.

## Global Constraints

- Python nur über `.venv\Scripts\python.exe`; Tests `.venv\Scripts\python.exe -m pytest` (ohne SolidWorks).
- Jeder neue SW-API-Aufruf vorher mit `.venv\Scripts\python.exe -m swki api methode|enum <Name>` nachschlagen; in SW 2025
  verfügbar. SP-abhängige Methoden (`GetFirstDisplayDimension6` SP1, `GetAnnotationsByType` SP2) nur mit Ersatzweg.
- API in Metern und Radiant, Spec und Ausgaben in mm und Grad; Rauheit in µm.
- Bestehende Freigaben bleiben gültig: Eine Spec ohne die neuen Felder ergibt dieselbe Prüfsumme wie vorher.
- Funktion und Toleranz am Feature hängen nicht an Feature-IDs. Umbenennen, Zusammenfassen und der Wechsel zwischen
  `positionen` und Muster ändern die Prüfsumme nicht.
- Allgemeintoleranz Klasse m (ISO 2768-1 mit Ausgabejahr), Tolerierungsgrundsatz ISO 8015, Hülle Ⓔ nur an Passmaßen aus
  der Funktion (Nutzer).
- Werte mit Beleg C in `funktionen.yaml` tragen `bestaetigt: false`. `validieren` meldet sie, bis der Nutzer bestätigt.
- Hinweise blockieren nie. Befunde (`plausibel_befunde`) blockieren `validieren`.
- Kein SolidWorks ohne ausdrückliches OK des Nutzers (er arbeitet ggf. parallel); dann frischer Start
  (`-m werkzeuge.sw_neustart`), nur Dokumente aus dem Arbeitsordner.
- Kein `git push`, kein Merge ohne Nutzer-OK. Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Bestehende Specs und Freigaben.** Eine Referenz-Spec ohne neue Felder hat dieselbe Prüfsumme wie vor dem Umbau,
   sonst meldet jede alte Freigabe `FREIGABE_VERALTET` (fester Hash in Task 5).
2. **Nachbessern im Bauweg.** Zwei Stiftbohrungen mit gleicher Funktion werden zu einem Feature zusammengefasst oder
   umbenannt; die Prüfsumme bleibt gleich (Task 5).
3. **Durchmesser als Ausdruck.** `durchmesser: "=D_stift"` mit `funktion` geht ausgewertet ins Tupel. Bei einem
   Ausdrucksfehler geht der Rohtext ins Tupel, nichts stürzt ab (Task 5).
4. **Tippfehler.** Unbekannte `funktion`, ein `toleranzen`-Schlüssel ohne Parameter, ein Bezugsbuchstabe ohne `bezuege`
   melden einen Befund mit Pfad, keinen KeyError (Task 4).
5. **Freigegebene Kopie mit umbenannter Funktion.** `aufloesen` wirft `FUNKTION_UNBEKANNT` mit Namen statt eines
   KeyError, wenn die Tabelle die Funktion nicht mehr kennt (Task 3).

---

### Task 1: Spike Z1.0 – Zeichnung über die API (live, nur mit Nutzer-OK)

**Files:**
- Create: `spikes/z1_zeichnung.py` (Wegwerf, kein Test)
- Create: `docs/zeichnungsableitung/spike-z1.md` (Befundnotiz)

**Interfaces:**
- Consumes: gebaute Referenzteile aus dem Arbeitsordner (`swki bauen tests/referenz/buchse/buchse.yaml` und die
  Spannplatte aus `tests/referenz/stil/`), ISO-Zeichnungsvorlage von SolidWorks (`swDefaultTemplateDrawing`).
- Produces: `spike-z1.md` mit einer Antwort je Frage (ja/nein/Einschränkung, Methode, Parameterzahl, Laufzeit), auf die
  der Plan für Z1.3/Z1.4 baut.

- [ ] **Step 1: Nutzer-OK einholen.** Den Nutzer fragen: frischer SolidWorks-Start, zwei Referenzteile bauen, eine
  Zeichnung im Arbeitsordner. Ohne OK mit Task 2 weitermachen und den Spike später ausführen.
- [ ] **Step 2: API nachschlagen.** Mit `swki api methode` nachschlagen und die Parameterzahl in der Notiz festhalten:
  - `ISldWorks.NewDocument`, `IDrawingDoc.CreateDrawViewFromModelView3`, `CreateSectionViewAt5`, `CreateDetailViewAt4`
  - `InsertModelAnnotations3`, `InsertModelAnnotations4`
  - `IDisplayDimension.MarkedForDrawing`, `IModelDoc2.AddDimension2`, `IView.GetVisibleEntities2`, `IView.ModelToViewTransform`
  - `IDimensionTolerance.SetFitValues`, `InsertSurfaceFinishSymbol3`
  - `IView.GetFirstDisplayDimension5`, `IAnnotation.GetAttachedEntities3`, `IModelDocExtension.SaveAs` (PDF)
  - Enum `swDetailingSFSymbolStandard_e`, `ISldWorks.RevisionNumber`
- [ ] **Step 3: Skript schreiben und ausführen.** Nach `-m werkzeuge.sw_neustart` beantwortet `spikes/z1_zeichnung.py`
  diese Fragen. Jede Antwort wird ins Skript-Log geschrieben.
  1. Welches Service Pack hat Rechner A? Sind `GetFirstDisplayDimension6` und `GetAnnotationsByType` vorhanden?
  2. Kann swki eine Zeichnung aus der ISO-Vorlage anlegen und darin Erst-, Seiten- und Draufsicht nach Projektionsmethode 1 einfügen?
  3. Lassen sich eine Schnittansicht (Buchse längs) und eine Einzelheit ohne Dialog erzeugen?
  4. Was fügt `InsertModelAnnotations3/4` mit `swInsertDimensionsMarkedForDrawing` ein, Skizzenmaße oder Feature-Maße?
     Kommt die Bohrungsangabe (`swInsertholeCallout`) ohne Dialog?
  5. Ändert `MarkedForDrawing = False` an einem Teilmaß die SHA-256 der gespeicherten Teildatei? Und der Alternativweg:
     Alle Maße einfügen und nicht benötigte in der Zeichnung löschen oder ausblenden – bleibt die Teildatei dabei unverändert?
  6. Lässt sich ein neues Maß zwischen zwei Kanten einer Ansicht setzen (Auswahl über `GetVisibleEntities2`), etwa eine
     Länge der Buchse von der Bundfläche aus?
  7. Lassen sich Passung `H7` mit Hülle Ⓔ und eine Oberflächenangabe Ra 0,8 nach ISO 21920 (Norm-Option `21920_1`)
     setzen und als Text zurücklesen?
  8. Können Maße zurückgelesen werden: Wert, Toleranz, Passung, Klammer, angehängte Kanten, Hüllrechteck?
  9. Läuft der PDF-Export ohne Dialog, und wie lange dauert die ganze Zeichnung?
- [ ] **Step 4: Befundnotiz schreiben.** `docs/zeichnungsableitung/spike-z1.md` nach dem Muster früherer Spike-Notizen:
  - je Frage Ergebnis, Methode, Fallstrick
  - am Ende: „Folgen für Design Abschnitt 6.2“, also welcher Maßweg trägt
  - Neubau alter Teile nötig, ja oder nein
- [ ] **Step 5: SolidWorks schließen** (`-m werkzeuge.sw_neustart` oder Dokumente schließen), nichts außerhalb des
  Arbeitsordners gespeichert.
- [ ] **Step 6: Commit**

```bash
git add spikes/z1_zeichnung.py docs/zeichnungsableitung/spike-z1.md
git commit -m "Zeichnungsableitung Z1.0: Spike Zeichnung über die API, Befundnotiz"
```

### Task 2: Nachrecherche Härteangabe (ISO 15787) und Halbzeugbezeichnung

**Files:**
- Create: `docs/zeichnungsableitung/haerteangabe.md`

**Interfaces:**
- Produces: die Felder von `behandlung` und `halbzeug` für Task 3, mit Schreibweise auf der Zeichnung und Belegstärke.

- [ ] **Step 1: Recherche wie in `recherche.md`.** Nur öffentliche HTML-Quellen; keine PDFs ohne Nutzer-OK je Datei, keine
  Konten. Belegstärke A/B/C je Regel. Fragen:
  - Wie wird die Härte nach ISO 15787 angegeben (z. B. „gehärtet und angelassen 58+4 HRC“)?
  - Wie die Einsatzhärtetiefe (CHD/Eht mit Grenzhärte)?
  - Wie werden Messstellen gekennzeichnet, und wie sieht die Angabe bei örtlicher Behandlung aus (strichpunktierte breite Linie)?
  - Wie werden Beschichtung und Eloxal angegeben (z. B. ISO 7599)?
  - Wie wird Halbzeug bezeichnet (Flachstahl EN 10058, Rundstahl EN 10060, Alu-Flach EN 755), und wie die rohe Oberfläche
    („wie Halbzeug“ bzw. Symbol ohne Materialabtrag)?
- [ ] **Step 2: Notiz schreiben.** Sie enthält Regeln, Quellen, Belegstärke und einen Vorschlag für die Felder:
  `behandlung: [{art, haerte?, tiefe?, schicht?, flaechen?}]`, `halbzeug: {art, norm, masse}`.
- [ ] **Step 3: Commit**

```bash
git add docs/zeichnungsableitung/haerteangabe.md
git commit -m "Zeichnungsableitung Z1.1: Nachrecherche Härteangabe und Halbzeug"
```

### Task 3: Schema – Anforderungsfelder und Top-Level-Felder

**Files:**
- Modify: `schema/teil.schema.json` (`properties` Top-Level; `$defs`; `f_bohrung`, `f_normbohrung`, `f_extrusion`,
  `f_rotation`, `f_austragung`, `f_verrundung`, `f_fase`)
- Test: `tests/spec/test_zeichnung_schema.py`

**Interfaces:**
- Consumes: Feldvorschlag aus Task 2 für `behandlung`, `halbzeug`.
- Produces:
  - `$defs`: `passung`, `toleranz`, `rauheit`, `form_lage`.
  - Feature-Felder: `funktion`, `passung`, `toleranz`, `rauheit`, `form_lage`, `huelle`, `bearbeitung`, `behandlung`.
  - Top-Level: `verfahren`, `bezuege`, `toleranzen`, `behandlung`, `halbzeug`.
  - Später verwendete Konstante `ANFORDERUNG_FELDER` (Task 4).

- [ ] **Step 1: Failing tests schreiben**

```python
from swki.spec.laden import schema_befunde

BASIS = {"art": "teil", "name": "Platte", "parameter": {"D": 8, "A": 40},
         "features": [{"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
             {"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]}, "ende": {"typ": "blind", "tiefe": 20}}]}

def _mit(feature_zusatz=None, **oben):
    spec = {**BASIS, **oben}
    spec["features"] = [{**BASIS["features"][0], **(feature_zusatz or {})}]
    return spec

def test_funktion_und_passung_am_feature():
    assert schema_befunde(_mit({"funktion": "anlage", "passung": "H7", "huelle": True,
                                "rauheit": {"Ra": 0.8}, "bearbeitung": "schleifen"})) == []

def test_form_lage_mit_bezug():
    assert schema_befunde(_mit({"form_lage": [{"art": "rechtwinkligkeit", "wert": 0.02, "bezug": ["A"]}]},
                               bezuege={"A": {"feature": "f1", "flaeche": "-y"}})) == []

def test_top_level_felder():
    assert schema_befunde(_mit(verfahren="fraesen", toleranzen={"A": {"oben": 0.02, "unten": -0.02}},
                               halbzeug={"art": "flach", "norm": "EN 10058", "masse": "100 x 20"},
                               behandlung=[{"art": "bruenieren"}])) == []

@pytest.mark.parametrize("zusatz", [{"passung": "H77x"}, {"bearbeitung": "fraesen"}, {"rauheit": {"Ra": -1}},
                                    {"form_lage": [{"art": "gelb", "wert": 0.1}]}, {"toleranz": {"oben": 0.1}}])
def test_ungueltige_feldwerte(zusatz):
    assert schema_befunde(_mit(zusatz))

def test_verfahren_nur_fraesen_oder_drehen():
    assert schema_befunde(_mit(verfahren="schleifen"))
```

- [ ] **Step 2: Tests ausführen und Fehlschlag prüfen.** Befehl: `.venv\Scripts\python.exe -m pytest tests/spec/test_zeichnung_schema.py -v`.
  Erwartet: FAIL (additionalProperties).
- [ ] **Step 3: Schema erweitern.**
  - `passung`: String `^[A-Za-z]{1,2}[0-9]{1,2}$`.
  - `toleranz`: `{oben, unten}`, beide `wert` und Pflicht.
  - `rauheit`: Objekt mit genau einem Schlüssel `Ra` oder `Rz`, Zahl > 0 in µm.
  - `form_lage`: Liste von `{art, wert, bezug?, mmr?}` mit
    - `art` aus `geradheit, ebenheit, rundheit, zylindrizitaet, parallelitaet, rechtwinkligkeit, neigung, position,
      koaxialitaet, symmetrie, rundlauf, gesamtlauf, linienprofil, flaechenprofil`,
    - `wert` > 0,
    - `bezug` Liste aus 1–3 Buchstaben `^[A-Z]$`,
    - `mmr` boolean (Ⓜ).
  - Felder an den sieben Feature-Defs:
    - `funktion` (`^[a-z][a-z_]*$`), `passung`, `toleranz`, `rauheit`, `form_lage`
    - `huelle` (boolean), `bearbeitung` (`schleifen | erodieren`), `behandlung` (String = `art` eines Top-Level-Eintrags)
  - Top-Level:
    - `verfahren` (`fraesen | drehen`)
    - `bezuege` (Objekt, Schlüssel `^[A-Z]$`, Wert `flaechenanker`)
    - `toleranzen` (Schlüssel Parametername, Wert `toleranz` oder `{passung}`)
    - `behandlung` und `halbzeug` nach Task 2
  - Jeweils mit `description` und dem Verweis auf den Design-Abschnitt.
- [ ] **Step 4: Tests ausführen und Erfolg prüfen.** Befehle:
  - `.venv\Scripts\python.exe -m pytest tests/spec -q`. Erwartet: alle PASS.
  - Bestehende Specs: `.venv\Scripts\python.exe -m pytest tests/referenz/test_referenzen.py -q`, soweit ohne SolidWorks
    lauffähig. Erwartet: PASS.
- [ ] **Step 5: Commit**

```bash
git add schema/teil.schema.json tests/spec/test_zeichnung_schema.py
git commit -m "Zeichnungsableitung Z1.1: Schema – Funktion, Toleranz, Rauheit, Form/Lage, Verfahren, Behandlung, Halbzeug"
```

### Task 4: Regeltabelle `funktionen.yaml`, Auflösung und Befunde

**Files:**
- Create: `swki/wissen/funktionen.yaml`
- Create: `swki/spec/funktionen.py`
- Modify: `swki/spec/laden.py` (`plausibel_befunde` ruft `anforderung_befunde`)
- Test: `tests/spec/test_funktionen.py`

**Interfaces:**
- Consumes: Schema aus Task 3.
- Produces (in `swki/spec/funktionen.py`):
  - `ANFORDERUNG_FELDER = ("funktion", "passung", "toleranz", "rauheit", "form_lage", "huelle", "bearbeitung", "behandlung")`
  - `lade_funktionen(pfad: Path = TABELLE) -> dict[str, dict]`
  - `aufloesen(feature: dict, tabelle: dict | None = None) -> dict`. Liefert die aufgelösten Werte. Feature-Felder
    überschreiben Tabellenwerte. Schlüssel: `passung`, `toleranz`, `rauheit`, `form_lage`, `huelle`, `bearbeitung`,
    `behandlung`, `unbestaetigt: list[str]`.
  - `FunktionFehler(SwkiFehler)` mit `daten={"code": "FUNKTION_UNBEKANNT"}`.
  - `anforderung_befunde(spec: dict) -> list[dict]`. Befunde `{pfad, meldung}` wie in `laden.py`.

- [ ] **Step 1: Tabelle anlegen.** Werte aus Design 4.3; je Eintrag `quelle`, `beleg`, `bestaetigt` (true nur bei Beleg
  A/B für alle Werte des Eintrags):

| Schlüssel | passung | huelle | rauheit Ra | form_lage | beleg / bestaetigt |
|---|---|---|---|---|---|
| `stiftbohrung` | H7 | true | 0.8 | – | passung C, Ra C / false |
| `lagersitz_welle` | k6 | true | 0.8 | rundheit it 4 | passung C, Rest B / false |
| `lagersitz_gehaeuse` | H7 | true | 1.6 | rundheit it 5 | B / true |
| `gleitpassung_bohrung` | H7 | true | 0.8 | – | passung A, Ra C / false |
| `gleitpassung_welle` | g6 | true | 0.8 | – | passung A, Ra C / false |
| `festsitz_bohrung` | H7 | true | 0.8 | – | passung A/B, Ra C / false |
| `festsitz_welle` | p6 | true | 0.8 | – | passung A/B, Ra C / false |
| `uebergang_bohrung` | H7 | true | 1.6 | – | passung A/B, Ra C / false |
| `uebergang_welle` | k6 | true | 1.6 | – | passung A/B, Ra C / false |
| `dichtflaeche_rwdr` | h11 | false | 0.8 (drallfrei) | – | passung C, Ra B / false |
| `anlage` | – | false | 1.6 | – | Ra C / false |

  `form_lage` in der Tabelle mit `it` statt `wert`. Den Zahlenwert rechnet Z1.3 aus ISO 286; die Auflösung gibt `it`
  unverändert weiter.

- [ ] **Step 2: Failing tests schreiben**

```python
from swki.spec.funktionen import aufloesen, anforderung_befunde, FunktionFehler, lade_funktionen

def test_tabelle_vollstaendig():
    t = lade_funktionen()
    assert {"stiftbohrung", "lagersitz_welle", "gleitpassung_welle", "anlage"} <= set(t)
    assert all({"quelle", "beleg", "bestaetigt"} <= set(e) for e in t.values())

def test_aufloesen_aus_tabelle():
    a = aufloesen({"id": "f3", "typ": "normbohrung", "funktion": "stiftbohrung"})
    assert a["passung"] == "H7" and a["huelle"] is True and a["rauheit"] == {"Ra": 0.8}
    assert "passung" in a["unbestaetigt"]

def test_feature_ueberschreibt_tabelle():
    a = aufloesen({"id": "f3", "typ": "bohrung", "funktion": "stiftbohrung", "rauheit": {"Ra": 0.4}})
    assert a["rauheit"] == {"Ra": 0.4} and "rauheit" not in a["unbestaetigt"]

def test_ohne_funktion_nur_eigene_werte():
    assert aufloesen({"id": "f1", "typ": "extrusion", "toleranz": {"oben": 0.1, "unten": 0}})["toleranz"] == {"oben": 0.1, "unten": 0}

def test_unbekannte_funktion_fehler():
    with pytest.raises(FunktionFehler) as e:
        aufloesen({"id": "f1", "typ": "bohrung", "funktion": "lagersitz"})
    assert e.value.daten["code"] == "FUNKTION_UNBEKANNT" and "lagersitz" in str(e.value)

@pytest.mark.parametrize("spec, pfad", [
    ({"features": [{"id": "f1", "typ": "bohrung", "funktion": "gibtsnicht"}]}, "features[0].funktion"),
    ({"features": [{"id": "f1", "typ": "bohrung", "huelle": True}]}, "features[0].huelle"),
    ({"features": [{"id": "f1", "typ": "bohrung", "passung": "H7", "toleranz": {"oben": 0.1, "unten": 0}}]}, "features[0].toleranz"),
    ({"features": [{"id": "f1", "typ": "bohrung", "form_lage": [{"art": "position", "wert": 0.1, "bezug": ["A"]}]}]},
     "features[0].form_lage[0].bezug"),
    ({"parameter": {"L": 50}, "toleranzen": {"Lx": {"oben": 0.1, "unten": 0}}, "features": []}, "toleranzen.Lx"),
    ({"features": [{"id": "f1", "typ": "bohrung", "behandlung": "haerten"}]}, "features[0].behandlung"),
])
def test_befunde(spec, pfad):
    assert [b["pfad"] for b in anforderung_befunde(spec)] == [pfad]
```

- [ ] **Step 3: Tests ausführen und Fehlschlag prüfen.** Befehl: `.venv\Scripts\python.exe -m pytest tests/spec/test_funktionen.py -v`.
  Erwartet: FAIL (ImportError).
- [ ] **Step 4: Implementieren.**
  - `lade_funktionen` nach dem Muster `lade_tabelle` in `swki/spec/normen.py`.
  - `anforderung_befunde` prüft:
    - unbekannte Funktion;
    - `huelle` ohne Passung oder Toleranz nach der Auflösung;
    - `passung` und `toleranz` gleichzeitig;
    - Bezugsbuchstabe nicht in `bezuege`;
    - `toleranzen`-Schlüssel nicht in `parameter`;
    - Feature-`behandlung` ohne gleichnamige `art` im Top-Level `behandlung`.

    Aufgerufen wird es am Ende von `plausibel_befunde` in `laden.py`.
- [ ] **Step 5: Tests ausführen und Erfolg prüfen.** Befehl: `.venv\Scripts\python.exe -m pytest tests/spec -q`.
  Erwartet: alle PASS.
- [ ] **Step 6: Commit**

```bash
git add swki/wissen/funktionen.yaml swki/spec/funktionen.py swki/spec/laden.py tests/spec/test_funktionen.py
git commit -m "Zeichnungsableitung Z1.1: Regeltabelle funktionen.yaml, Auflösung, Befunde"
```

### Task 5: Prüfsumme nach Wirkung und aufgelöste Werte in der Freigabe

**Files:**
- Modify: `swki/spec/freigabe.py` (`pruefsumme`)
- Modify: `swki/spec/befehle.py` (`_freigeben`: `zusatz`)
- Create: `swki/spec/anforderungen.py`
- Test: `tests/spec/test_freigabe_anforderungen.py`

**Interfaces:**
- Consumes: `ANFORDERUNG_FELDER`, `aufloesen` (Task 4); `auswerten` (`swki/spec/ausdruck.py`); `groesse_text`
  (`swki/spec/normen.py`).
- Produces:
  - `anforderungs_tupel(spec: dict) -> list[list]`: sortierte, doppelfreie Liste
    `[typ_gruppe, nenngroesse, {feld: wert …}]` ohne Feature-IDs. `typ_gruppe`: `bohrung` für `bohrung`/`normbohrung`,
    sonst `typ`. `nenngroesse`: Ø ausgewertet, mit `round(x, 6)`; bei `normbohrung` `"<art> <groesse_text>"`; sonst `None`;
    bei `AusdruckFehler` der Rohtext.
  - `aufgeloeste_anforderungen(spec: dict) -> list[dict]`: `[{"feature": id, **aufloesen(f)}]` für Features mit
    Anforderung.
  - `OPTIONAL_TEIL = ("verfahren", "toleranzen", "behandlung", "halbzeug")` in `freigabe.py`.

- [ ] **Step 1: Alten Hash festhalten.** Mit dem Code vor der Änderung `pruefsumme(SPEC)` für `SPEC` aus
  `tests/spec/test_freigabe.py` berechnen (kleines Skript im Scratchpad, mit `.venv\Scripts\python.exe` ausführen). Den
  Wert als Konstante `ALTER_HASH` in den neuen Test übernehmen.
- [ ] **Step 2: Failing tests schreiben**

```python
from swki.spec.freigabe import pruefsumme
from swki.spec.anforderungen import anforderungs_tupel, aufgeloeste_anforderungen

ALTER_HASH = "<Wert aus Step 1>"
SPEC = {  # wie tests/spec/test_freigabe.py
    "art": "teil", "name": "Platte", "material": "1.2312", "parameter": {"L": 100},
    "features": [{"id": "f1", "typ": "extrusion"}], "pruefung": {"huellquader": [100, 20, 60]},
}
STIFT = {"typ": "normbohrung", "art": "stift", "groesse": "8", "funktion": "stiftbohrung"}

def test_ohne_neue_felder_unveraendert():
    assert pruefsumme(SPEC) == ALTER_HASH

def test_umbenennen_und_zusammenfassen_unveraendert():
    zwei = {**SPEC, "features": [*SPEC["features"], {"id": "s1", **STIFT}, {"id": "s2", **STIFT}]}
    eins = {**SPEC, "features": [*SPEC["features"], {"id": "stifte", **STIFT}]}
    assert pruefsumme(zwei) == pruefsumme(eins)

@pytest.mark.parametrize("aenderung", [{"passung": "H8"}, {"funktion": "gleitpassung_bohrung"}, {"huelle": False}])
def test_anforderung_aendert_summe(aenderung):
    a = {**SPEC, "features": [*SPEC["features"], {"id": "s1", **STIFT}]}
    b = {**SPEC, "features": [*SPEC["features"], {"id": "s1", **STIFT, **aenderung}]}
    assert pruefsumme(a) != pruefsumme(b)

@pytest.mark.parametrize("feld, wert", [("verfahren", "drehen"), ("toleranzen", {"L": {"oben": 0.1, "unten": 0}}),
                                        ("halbzeug", {"art": "flach", "norm": "EN 10058", "masse": "100 x 20"})])
def test_top_level_aendert_summe(feld, wert):
    assert pruefsumme({**SPEC, feld: wert}) != pruefsumme(SPEC)

def test_durchmesser_ausdruck():
    f = {"id": "b1", "typ": "bohrung", "durchmesser": "=D", "funktion": "stiftbohrung"}
    assert anforderungs_tupel({"parameter": {"D": 8}, "features": [f]})[0][1] == 8.0
    assert anforderungs_tupel({"parameter": {}, "features": [f]})[0][1] == "=D"

def test_aufgeloeste_anforderungen():
    [a] = aufgeloeste_anforderungen({"features": [{"id": "s1", **STIFT}]})
    assert a["feature"] == "s1" and a["passung"] == "H7"
```

- [ ] **Step 3: Tests ausführen und Fehlschlag prüfen.** Befehl: `.venv\Scripts\python.exe -m pytest tests/spec/test_freigabe_anforderungen.py -v`.
  Erwartet: FAIL.
- [ ] **Step 4: Implementieren.**
  - `pruefsumme` (nur `art: teil`):
    - `kern |= {f: spec[f] for f in OPTIONAL_TEIL if f in spec}`;
    - `kern["anforderungen"] = anforderungs_tupel(spec)` nur, wenn die Liste nicht leer ist.
  - `_freigeben` in `befehle.py` übergibt `zusatz={"anforderungen": aufgeloeste_anforderungen(spec)}`, wenn die Liste
    nicht leer ist. Damit liegen die Tabellenwerte zum Zeitpunkt der Freigabe in `freigabe.json`.
  - Baugruppen: Die Teil-Prüfsummen gehen schon in die Baugruppensumme ein (`teile`), sonst ist nichts zu tun.
- [ ] **Step 5: Tests ausführen und Erfolg prüfen.** Befehl: `.venv\Scripts\python.exe -m pytest -q` (ganze Suite ohne
  SolidWorks). Erwartet: alle PASS, insbesondere `tests/spec/test_freigabe.py` und `tests/baugruppe`.
- [ ] **Step 6: Commit**

```bash
git add swki/spec/freigabe.py swki/spec/befehle.py swki/spec/anforderungen.py tests/spec/test_freigabe_anforderungen.py
git commit -m "Zeichnungsableitung Z1.1: Prüfsumme nach Wirkung, aufgelöste Anforderungen in freigabe.json"
```

### Task 6: Hinweise für Verfahren, Bearbeitung und unbestätigte Werte

**Files:**
- Modify: `swki/spec/hinweise.py` (`fertigung_hinweise`, neue `funktion_hinweise`, `hinweise`)
- Test: `tests/spec/test_hinweise_zeichnung.py`

**Interfaces:**
- Consumes: `aufloesen` (Task 4).
- Produces: Hinweise `art: "fertigung"` (Bearbeitung) und `art: "funktion"` (unbestätigter Tabellenwert).

- [ ] **Step 1: Failing tests schreiben.** Spec-Bausteine `PLATTE`, `_tasche` wie in
  `tests/spec/test_hinweise_fertigung.py`.

```python
def test_erodieren_ohne_fraeserregel():
    t = {**_tasche({"typ": "blind", "tiefe": 15}), "bearbeitung": "erodieren"}
    assert not [h for h in fertigung_hinweise(_spec(t)) if "Regel 8" in h["meldung"]]

def test_schleifen_drehteil_ohne_freistich():
    spec = {"verfahren": "drehen", "features": [{"id": "f1", "typ": "rotation", "bearbeitung": "schleifen"}]}
    assert any("Freistich" in h["meldung"] and h["art"] == "fertigung" for h in fertigung_hinweise(spec))

def test_feine_rauheit_ohne_schleifen():
    spec = {"features": [{"id": "f1", "typ": "bohrung", "rauheit": {"Ra": 0.4}}]}
    assert any("Ra 0,4" in h["meldung"] and "schleifen" in h["meldung"] for h in fertigung_hinweise(spec))

def test_unbestaetigter_tabellenwert():
    [h] = funktion_hinweise({"features": [{"id": "s1", "typ": "normbohrung", "funktion": "stiftbohrung"}]})
    assert h["art"] == "funktion" and h["pfad"] == "features[0].funktion" and "Nutzer" in h["meldung"]

def test_bestaetigter_wert_ohne_hinweis():
    assert funktion_hinweise({"features": [{"id": "g", "typ": "bohrung", "funktion": "lagersitz_gehaeuse"}]}) == []
```

- [ ] **Step 2: Tests ausführen und Fehlschlag prüfen.** Befehl: `.venv\Scripts\python.exe -m pytest tests/spec/test_hinweise_zeichnung.py -v`.
  Erwartet: FAIL.
- [ ] **Step 3: Implementieren.**
  - `fertigung_hinweise` überspringt Regel 8 für Features mit `bearbeitung: erodieren`.
  - Neue Prüfungen dort:
    - `verfahren: drehen` mit `bearbeitung: schleifen` und ohne Feature `typ: freistich` ergibt den Hinweis
      „Schleifen am Drehteil ohne Freistich (DIN 509)“.
    - Ra < 0,8 µm ohne `bearbeitung: schleifen` ergibt einen Hinweis. Schwelle als Konstante `RA_SCHLEIFEN = 0.8`,
      Beleg C im Kommentar.
  - `funktion_hinweise(spec) -> list[dict]` meldet je Feature mit nicht leerem `unbestaetigt` einen Hinweis:
    „Wert aus funktionen.yaml unbestätigt (Beleg C): <Felder> – Nutzer vor der Freigabe fragen“.
  - `hinweise()` hängt `funktion_hinweise` an; die Docstrings beider Funktionen um die neuen Arten ergänzen.
- [ ] **Step 4: Tests ausführen und Erfolg prüfen.** Befehl: `.venv\Scripts\python.exe -m pytest tests/spec -q`.
  Erwartet: alle PASS.
- [ ] **Step 5: Commit**

```bash
git add swki/spec/hinweise.py tests/spec/test_hinweise_zeichnung.py
git commit -m "Zeichnungsableitung Z1.1: Hinweise für Erodieren, Schleifen, Rauheit und unbestätigte Funktionswerte"
```

### Task 7: Skill, CLAUDE.md und Abschluss Z1.1

**Files:**
- Modify: `.claude/skills/konstruieren/SKILL.md` (Abschnitt 2 Spezifikation: neue Felder; Abschnitt 4 Freigabe:
  unbestätigte Funktionswerte vorlegen)
- Modify: `CLAUDE.md` (neuer Abschnitt „Zeichnungsableitung (Stufe Z1)“, 3–5 Zeilen: Design, Felder, Schutz nach
  Wirkung, Rechnerregel)
- Create: `docs/zeichnungsableitung/ergebnisse.md` (Stand Z1.0/Z1.1, offene Etappen; offen u. a. Bezugsvorschlag aus `deckungsgleich`-Verknüpfungen, Design 4.1)

- [ ] **Step 1: Skill ergänzen.**
  - Wann `funktion` gesetzt wird: nur an Flächen mit Funktion, nie „sicherheitshalber“ eng.
  - Überschreiben einzelner Werte.
  - `bezuege` an den Anlageflächen.
  - `verfahren`, `bearbeitung`, `behandlung`, `halbzeug` und `toleranzen` je Parameter.
  - Ein kurzes YAML-Beispiel (Stiftbohrung mit Funktion).
- [ ] **Step 2: CLAUDE.md-Abschnitt schreiben.** Er nennt:
  - Design und Recherche;
  - Felder als Anforderung, Schutz nach Wirkung;
  - Tabelle nur mit Quellen erweitern;
  - Fertigungszeichnungen nur auf der Vollversion.
- [ ] **Step 3: Ganze Suite ohne SolidWorks ausführen.** Befehl: `.venv\Scripts\python.exe -m pytest -q`. Erwartet: alle
  PASS. Danach `-m werkzeuge.stil_zaehlung` über `tests/referenz`. Erwartet: keine neuen Befunde an bestehenden Specs.
- [ ] **Step 4: Commit**

```bash
git add .claude/skills/konstruieren/SKILL.md CLAUDE.md docs/zeichnungsableitung/ergebnisse.md
git commit -m "Zeichnungsableitung Z1.1: Skill konstruieren, CLAUDE.md, Ergebnisse"
```
