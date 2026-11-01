# Paket Bestandsdateien, Etappe 2 (Baugruppen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** swki ändert vorhandene `.sldasm` samt ihrer Dateien gezielt an einer Arbeitskopie, weist nach, dass sich nur die freigegebenen Stellen geändert haben und die Baugruppe noch fährt, und benennt Handänderungen an selbst gebauten Dateien von sich aus.

**Architecture:** Eine Baugruppen-Spec zerfällt in **Teil-Scheiben** (`scheibe(spec, datei)`: gewöhnliche Änderungs-Specs je Datei, Code von Etappe 1 unverändert) und **Baugruppen-Punkte** (neu). Vorher ist immer die Aufnahme, nachher wird der Lauf gleich gelesen; alle Bewertungen sind reine Funktionen über Dicts. Eine unveränderte Komponente beweist sich selbst: gleiche SHA-256 plus gleiche Transformation, also braucht nur eine geänderte Datei einen Körpervergleich. Bewegungen haben ihr Soll aus der Fahrt an der Bestandskopie, nicht aus einer Spec.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) für Spike und Live-Tests.

**Spec:** `docs/superpowers/specs/2026-10-25-bestandsdateien-design.md` (§4.1, §8 mit allen Nachträgen vom 2026-11-01, §9, §10, §11 S19, §12, §14). Muster: Plan Etappe 1. Messwerte und Fallen: `docs/bestandsdateien/ergebnisse.md`.

## Reihenfolge und SolidWorks-Sperre

Der Nutzer arbeitet gerade in `lauf-30`. Bis er **in dieser Session** meldet, dass er fertig ist, gilt: kein SolidWorks, kein Live-Test, kein Spike, kein `werkzeuge.sw_neustart`, keine Aufnahme, nichts öffnet `lauf-30`. Ein Neustart kann ungesicherte Arbeit vernichten. Danach nie zwei SolidWorks-Arbeiten zugleich; die Session Konstruktionsstil braucht SolidWorks auch, Etappe 2 hat Vorrang, abgestimmt wird über den Nutzer.

| Phase | Tasks | SolidWorks |
|---|---|---|
| A: rein | 1–7 | nein, jederzeit |
| B: COM-Schicht gegen Index und Attrappen | 8–11 | nein, ungemessen |
| C: live | 12–16 | erst nach der Meldung |

Phase B ist gegen den API-Index geschrieben, aber nicht gemessen: S19 kann sie korrigieren. Meldet sich der Nutzer früher, kommt Task 12 sofort dran, vor dem Rest von Phase B. Für den Blindtest reichen Tasks 1, 2, 6, 7, 8 und 12; der Rest ist für seine neuen Anforderungen nötig. Phase A ist rein bis auf den Lesezugriff von Task 7, der eine Attrappe nutzt.

**Rechnerdatei:** Der Worktree hat kein `config/rechner.yaml` (nicht im Git). Vor dem ersten `swki`-Aufruf aus dem Hauptordner hierher kopieren, sonst schlägt jeder Befehl fehl.

## Präzisierungen gegenüber der Spec (bindend für diesen Plan)

1. **`in_datei` statt `datei`** an Punkten und Bereichen: `skript` belegt `datei`.
2. **Flach statt `extern/` und `swki/`:** Belegt ist nur der Vorrang der Datei neben der Baugruppe (S18g). S19c darf das nachziehen, nicht der Code vorher.
3. **Jede Grenzverknüpfung der Hauptbaugruppe ist eine Bewegung**, die Spec trägt keinen Block `bewegungen`.
4. **`masse_pruefen` gilt nur für Teile** (mit `in_datei`). Baugruppenweite Messungen gehören nicht in diese Etappe; `lage`, `verknuepfungen` und der Prüfer tragen das.
5. **Keine Gewindepaarung gegen fremde Bohrungen:** `kollision_erlaubt` statt dessen (Spec §8.2).
6. **Teil-Scheiben laufen vor den Baugruppen-Punkten**, egal wie die Punkte in der Spec stehen: Eine neue Verknüpfung kann an einem neuen Feature hängen.
7. **Lauf-Ordner tragen alle Dateien**, auch ungeänderte; `protokoll.sha256` deckt sie alle ab. `protokoll.dateien` nennt `haupt` und `geaendert:<rel>`; ein Lauf eines einzelnen Teils bleibt bei `teil`.
8. **Ohne `in_datei` an einer Baugruppe nur `eigenschaft`, `skript` und Baugruppen-Punkte** (Spec §4.1, Grenzen). `mass`, `gleichung`, `unterdruecken`, `aufheben`, `loeschen`, `feature`, `material` dort: `BESTAND_REFERENZ`.
9. **`komponenten` trägt alle Ebenen**, die Mechanik und die Baugruppen-Punkte nur die oberste.
10. **Jedes Öffnen in Etappe 2 geht über `oeffne_in`**, auch einzelne Teile und `vorher_<name>`. Punkte auf Teile mit externer Referenz und auf Basisteile weist `validieren` ab, deshalb braucht `vorher_<name>` nie eine Referenz daneben.
11. **`swki aenderungen` öffnet einen Lauf mit Aufnahme nicht** (Spec §8.5).

## Global Constraints

- Python nur `.venv\Scripts\python.exe`; swki-Ausgabe JSON; Fehler über `SwkiFehler` mit `daten = {"code": …}`.
- Vor jedem neuen SolidWorks-API-Aufruf `swki api methode <Interface.Member>` bzw. `swki api enum <Name>`; Parameteranzahl und Enum-Werte aus dem Index sind verbindlich; nur Aufrufe aus SW 2025 (`swki api pruefe-code` ohne Befund). Geprüft sind schon: `IMate2.MateEntity(1)`, `.GetMateEntityCount(0)`, `.Type`, `.Alignment`, `.MaximumVariation`, `.MinimumVariation`, `IMateEntity2.Reference`, `.ReferenceComponent`, `IDistanceMateFeatureData.MaximumDistance`, `.MinimumDistance`, `.EntitiesToMate`, `IAngleMateFeatureData.MaximumAngle`, `.MinimumAngle`, `IAssemblyDoc.GetComponents(1)`, `.ReplaceComponents2(5)`, `IComponent2.IsVirtual`, `.ReferencedConfiguration`, `.GetSuppression2(0)`, `.SetSuppression2(1)`, `.GetPathName(0)`, `.Solving`, `.IsPatternInstance(0)`, `ISldWorks.GetDocuments(0)`, `IFeature.GetDefinition(0)`, `.ModifyDefinition(3)`.
- Die API rechnet in Metern und Radiant, Spezifikationen und Ausgaben in mm und Grad.
- Original und jeder fremde `lauf-<n>` nur lesen, nie in SolidWorks öffnen. swki öffnet und speichert nur unter `<arbeitsordner>/<auftrag>/`; die Bestandskopie nur lesend; gespeichert wird nur in `lauf-<n>/`, an Ort und Stelle.
- Nur speichern, was ein Punkt ändert. Nach einem Fehler wird nichts mehr gespeichert.
- swki räumt nichts auf. Rückgaben von SolidWorks beweisen nichts: nachmessen.
- `ok: None` heißt nicht bestanden. Ein Prüfmangel ist nie ein Anlass, Bereiche, `lage_folgen` oder `kollision_erlaubt` an Messwerte anzupassen; dann den Nutzer fragen.
- `swki freigeben` nur nach ausdrücklichem OK des Nutzers; Prüfer bleibt Pflicht.
- Kollegen-Dateien, Prüfstations-Dateien und ihre Maße kommen nicht ins Git; das Repository ist öffentlich. Neue Ausnahme nur die erzeugten Musterdateien unter `tests/referenz/bestand/muster/baugruppe/`.
- Kein `git push`, kein Merge ohne ausdrückliches OK. Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Virtuelle Komponente** (der Nutzer kann beim Umbau eine anlegen): Sie liegt unter einem Temp-Pfad. Erwartet: kein `BESTAND_PFAD_FREMD`, kein Absturz, kein Punkt auf sie (Tests in Task 2, 4).
2. **Mehrere Instanzen derselben Datei** (11 × M5×20 in der Prüfstation): Ein Teil-Punkt trifft alle; die Freigabe-Vorlage nennt die Anzahl, `lage` sieht jede Instanz einzeln (Tests in Task 4, 5).
3. **Datei fehlt in der Kopie, Original liegt noch am gespeicherten Pfad:** Es wird nichts vom Original geladen und kein Lauf gespeichert (Tests in Task 2, live in Task 13).
4. **Unterdrückte oder leicht geladene Komponente:** `GetModelDoc2` ist `None`. Weder Absturz noch falsche Abweichung (Tests in Task 5, 8).
5. **Der Bestand ist schon nicht sauber** (Verknüpfungsfehler, Überlappung, Grenze, die nicht fährt): Das fällt nicht dem Lauf zur Last, steht aber im Bericht (Tests in Task 5, 6).

## Dateistruktur nach diesem Plan

```
swki/bestand/ablage.py              erweitert: kopiere_baugruppe, dateien.json, lauf_kopie_alle, Herkunft
swki/bestand/pfade.py               neu: Pfadschutz (rein und COM)
swki/bestand/scheiben.py            neu: Spec in Teil-Scheiben und Baugruppen-Punkte zerlegen
swki/bestand/spec_baugruppe.py      neu: Validierung der Baugruppen-Punkte
swki/bestand/vergleich_baugruppe.py neu: §8.3 als reine Logik
swki/bestand/bewegung_bestand.py    neu: Grenze als Bewegung, Vergleich mit dem Bestand
swki/bestand/abgleich.py            neu: §8.6 als reine Logik
swki/bestand/sw_baugruppe_bestand.py neu: COM lesen und schreiben für Baugruppen
swki/bestand/punkte_baugruppe.py    neu: Punkt-Handler
swki/bestand/bau_baugruppe.py       neu: swki bauen für Baugruppen
swki/bestand/pruefen_baugruppe.py   neu: swki pruefen für Baugruppen
spikes/s19_baugruppe.py             neu
werkzeuge/bestand_muster.py         erweitert: Musterbaugruppe
werkzeuge/bestand_gross.py          neu
tests/bestand/…                     je Modul ein Test, Attrappe sw_attrappe_baugruppe.py
tests/referenz/bestand/             muster/baugruppe/, hubeinheit_rev.yaml
```

Geändert: `schema/aenderung.schema.json`, `swki/bestand/{fehler,befehle,bau,pruefen,spec,ausgabe}.py`, `swki/aenderungen.py`, `swki/pruefung/messen.py` (`oeffne(voll=…)`), `swki/baugruppe/pruefen.py` (`lagen` im Bericht), `.claude/skills/{aendern,baugruppe,konstruieren}/SKILL.md`, `.claude/agents/pruefer.md`, `CLAUDE.md`, `werkzeuge/__init__.py`, `docs/bestandsdateien/ergebnisse.md`.

## `bestand.json` einer Baugruppe (Schnittstelle zwischen allen Tasks)

```json
{"version": 2, "art": "baugruppe", "sw_jahr": 2025,
 "datei": {"name": "Haupt.SLDASM", "original": "D:\\…", "sha256": "…", "versionen": ["…"], "version_aelter": false},
 "konfigurationen": ["Standard"], "aktiv": "Standard", "einheitensystem": 5, "tabelle": false,
 "eigenschaften": {"datei": {}, "konfiguration": {"Standard": {}}}, "externe_referenzen": [], "gleichungen": [], "variablen": {},
 "features": [], "reihenfolge": {"Standard": []}, "masse": [], "neuaufbau": [], "skizzen": {}, "material": "", "materialien": {}, "geometrie": {},
 "komponenten": {"Teil-1": {"datei": "teile/Teil.SLDPRT", "konfiguration": "Standard", "virtuell": false, "muster": false, "loesen": 0,
                            "fixiert": {"Standard": true}, "unterdrueckt": {"Standard": false}, "status": {"Standard": 3},
                            "transform": {"Standard": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]}}},
 "verknuepfungen": {"Abstand1": {"typ": 5, "ausrichtung": 0, "wert": 12.0, "min": 0.0, "max": 25.0, "grenze": true, "gesteuert": false,
                                 "partner": ["Teil-1", "Teil-2"], "fehler": {"Standard": 0}, "unterdrueckt": {"Standard": false}}},
 "kollisionen": [{"paar": ["Teil-1", "Teil-2"], "volumen": 1.5}],
 "bewegungen": {"Abstand1": {"komponente": "Teil-2", "art": "abstand", "min": 0.0, "max": 25.0, "gefahren": true, "bewegt": ["Teil-2"],
                             "kollisionen": [], "pruefungen": [], "hinweis": null}},
 "dateien": {"teile/Teil.SLDPRT": {"original": "D:\\…", "sha256": "…", "art": "teil", "versionen": [], "version_aelter": false,
                                   "referenzen": []}},
 "warnungen": [], "messung": {"lesen": {"s": 1.2, "mb": 900}}}
```

Die Felder von `eigenschaften` bis `geometrie` sind die von Etappe 1, damit `vergleiche` die Baugruppe als Datei behandeln kann; `features`, `reihenfolge` und `masse` lassen Komponenten und Verknüpfungen aus. `aufnahme/<rel>.json` trägt jede weitere Datei, Teile im Format von Etappe 1, Unterbaugruppen in diesem; `datei.name` ist dort der relative Pfad. `dateien.<rel>.referenzen`: was die Datei selbst referenziert, bei Teilen leer, wenn sie frei ist. `komponenten` trägt alle Ebenen, `transform` ist `null`, wenn die Komponente unterdrückt ist. Werte in mm und Grad, `transform` wie `Transform2.ArrayData` (Verschiebung in m). `status`: swConstrainedStatus_e.

---

### Task 1: Ablage für Baugruppen, Herkunft, Fehlercodes

**Files:**
- Modify: `swki/bestand/fehler.py`, `swki/bestand/ablage.py`
- Test: `tests/bestand/test_ablage_baugruppe.py`

**Interfaces:**
- Produces in `fehler.py`: `BESTAND_PFAD_FREMD`, `BESTAND_AUFTRAG_BELEGT`, `BESTAND_REFERENZ_FEHLT`, `BESTAND_OFFEN`, `VERKNUEPFUNGEN_FEHLEN`, `NAME_BELEGT`.
- Produces in `ablage.py`:
  - `ordne_referenzen(haupt: Path, gespeichert: list[str]) -> dict[str, Path]`: relativer Pfad → Quelle. Datei neben der Hauptbaugruppe vor gespeichertem Pfad; im Ordner der Baugruppe relative Struktur; sonst flach. Virtuelle Teile (Name mit `^`) fehlen im Ergebnis. Wirft `BESTAND_REFERENZ_FEHLT` (`fehlen`) und `BESTAND_REFERENZ_EXTERN` (`gleiche_namen`).
  - `sperrdateien(quellen: dict[str, Path]) -> list[str]`.
  - `kopiere_baugruppe(r, auftrag: str, haupt: Path, quellen: dict[str, Path]) -> dict`: `{"nummer", "pfad", "sha256", "neu", "dateien": {rel: {"original", "sha256"}}}`, schreibt `dateien.json`, alles schreibgeschützt.
  - `lade_dateien(r, auftrag, nummer) -> dict`; `lauf_kopie_alle(ordner_bestand: Path, dateien: dict, lauf: Path) -> Path`.
  - `herkunft_von(r, original: Path) -> dict | None`: `{auftrag, lauf, spec}` aus `<lauf>/protokoll.json`.
  - `pruefe_auftrag_frei(r, auftrag, spec_laeufe: list[int]) -> None`: `BESTAND_AUFTRAG_BELEGT`.
  - `aufnahmen_aus_lauf(r, ordner: Path) -> list[dict]`: Aufnahmen mit dieser Herkunft, über `*/bestand-*/herkunft.json`.
  - `lade_datei_aufnahme(r, auftrag, nummer, rel) -> dict`, `schreibe_datei_aufnahme(r, auftrag, nummer, rel, daten) -> Path`.

- [ ] **Step 1: Tests schreiben** (mit `tmp_path`, Rechner-Attrappe wie `tests/bestand/test_ablage.py`)

```python
def test_datei_neben_der_baugruppe_hat_vorrang(tmp_path):
    # gespeicherter Pfad zeigt woandershin, Datei liegt auch daneben → Quelle ist die daneben
def test_unterordner_behalten_struktur(tmp_path):        # teile/A.SLDPRT → "teile/A.SLDPRT"
def test_fremder_ordner_liegt_flach(tmp_path):           # D:\norm\S.sldprt → "S.sldprt"
def test_gleiche_namen_aus_zwei_ordnern(tmp_path):       # BESTAND_REFERENZ_EXTERN, nennt beide
def test_fehlende_referenz(tmp_path):                    # BESTAND_REFERENZ_FEHLT, nennt alle fehlenden
def test_virtuelles_teil_fehlt_nicht(tmp_path):          # Review Focus 1: "Teil1^Haupt.sldprt" weder fehlend noch kopiert
def test_verwirf_entfernt_alle_schreibgeschuetzten(tmp_path):  # bisher nur die Hauptdatei, rmtree scheiterte an den übrigen
def test_sperrdatei_wird_gemeldet_nicht_kopiert(tmp_path):
    # ~$A.SLDPRT neben A.SLDPRT: sperrdateien nennt A.SLDPRT, im Bestand liegt keine ~$-Datei
def test_gleiche_shas_keine_neue_aufnahme(r, tmp_path):
def test_eine_geaenderte_datei_neue_aufnahme(r, tmp_path):  # nur ein Teil anders → nummer 2
def test_original_und_lauf_bleiben_unberuehrt(r, tmp_path): # Inhalt und mtime aller Quellen gleich, kein neuer Eintrag im Quellordner
def test_lauf_kopie_alle_ist_beschreibbar_mit_struktur(tmp_path):
def test_herkunft_aus_lauf_ordner(r, tmp_path):          # protokoll.json im Lauf → {auftrag, lauf, spec}
def test_herkunft_fehlt_ausserhalb(r, tmp_path):         # None
def test_auftrag_mit_spec_laeufen_ist_belegt(r):         # BESTAND_AUFTRAG_BELEGT
def test_aufnahmen_aus_lauf_findet_und_liest_nichts_im_lauf(r, tmp_path):
```

- [ ] **Step 2: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/bestand/test_ablage_baugruppe.py -q`. Expected: FAIL (Namen fehlen).
- [ ] **Step 3: Implementieren.** `_kopie_in` liest die Hauptdatei aus `dateien.json`, ohne sie wie bisher (Etappe-1-Aufnahmen bleiben gültig). Kopieren mit `shutil.copy2`, SHA-256 nach dem Kopieren gegenprüfen, dann `stat.S_IREAD`. Ein Teil läuft weiter über `kopiere_original`. `pruefe_format` bleibt bis Task 8 unverändert, dort fällt auch der `.sldasm`-Fall in `tests/bestand/test_ablage.py`, sonst nähme `aufnehmen` Baugruppen über den Teil-Weg an.
- [ ] **Step 4: Test laufen lassen.** Run wie Step 2, zusätzlich `tests/bestand/test_ablage.py`. Expected: PASS.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: Ablage für Baugruppen und Herkunft“).

### Task 2: Pfadschutz

**Files:**
- Create: `swki/bestand/pfade.py`
- Modify: `swki/pruefung/messen.py` (`oeffne(..., voll: bool = False)`, `SW_OPEN_VOLL = 64`, swOpenDocOptions_OverrideDefaultLoadLightweight, S18g)
- Test: `tests/bestand/test_pfade.py`

**Interfaces:**
- Produces: `fremde_pfade(eintraege: list[dict], wurzel: Path) -> list[dict]` (rein; Eintrag `{"name", "pfad", "virtuell"}`, Vergleich ohne Groß-/Kleinschreibung, virtuell zählt nicht); `aufgeloeste_referenzen(app, pfad: Path) -> list[str]` (ohne virtuelle Teile); `pruefe_vor_dem_oeffnen(app, pfad: Path, wurzel: Path) -> None`; `offene_dokumente(app) -> set[str]`; `geladene_pfade(app, model, vorher: set[str]) -> list[dict]`; `pruefe_geladen(app, model, wurzel: Path, vorher: set[str]) -> dict` (Prüfungseintrag `pfade`); `oeffne_in(app, pfad, wurzel, sichtbar=False, nur_lesen=True)`: vor dem Öffnen prüfen, Stand der offenen Dokumente merken, öffnen mit `voll=True`, nachher prüfen, bei Fund schließen ohne Speichern und `BESTAND_PFAD_FREMD` werfen. `wurzel` ist der Ordner `bestand-<n>` bzw. `lauf-<n>`.

- [ ] **Step 1: Tests schreiben**

```python
def test_alles_im_ordner_ist_leer(tmp_path): ...
def test_datei_ausserhalb_wird_genannt(tmp_path): ...
def test_gross_kleinschreibung_zaehlt_nicht(tmp_path): ...
def test_nachbarordner_mit_gleichem_praefix_ist_fremd(tmp_path):  # lauf-3 gegen lauf-30
def test_virtuelle_komponente_ist_nicht_fremd(tmp_path):          # Review Focus 1
def test_unterdrueckte_komponente_wird_mitgeprueft(tmp_path):
def test_schon_offenes_fremdes_dokument_ist_kein_fund(tmp_path):  # Stand vorher zählt nicht, nur neu Geladenes
def test_teil_ohne_komponenten_geht_durch(tmp_path):              # oeffne_in an .sldprt, kein GetComponents
def test_fund_schliesst_ohne_speichern(tmp_path):                 # Attrappe: Save3 nie gerufen, schliesse einmal, BESTAND_PFAD_FREMD mit Liste
def test_vorpruefung_oeffnet_nicht(tmp_path):                     # Attrappe: fremder Pfad → OpenDoc6 nie gerufen
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** `geladene_pfade`: Hauptdokument, `GetComponents(False)` mit `GetPathName` und `IsVirtual`, `app.GetDocuments` mit `GetPathName`. Vergleich mit `Path.is_relative_to` nach `resolve`, nie über Zeichenketten.
- [ ] **Step 4: Test laufen lassen.** Expected: PASS.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: Pfadschutz“).

### Task 3: Schema, Laden, Prüfsumme

**Files:**
- Modify: `schema/aenderung.schema.json`, `swki/bestand/spec.py` (`bauweg_frei`, `_plausibel_befunde`, `GEOMETRIE_TYPEN` bleibt)
- Test: `tests/bestand/test_spec_baugruppe.py`

**Interfaces:**
- Produces: Punkt-Typen laut Spec §4.1; `in_datei` an allen Punkten außer Baugruppen-Punkten auf oberster Ebene optional; `lage_folgen` an allen; `bereiche[].in_datei`; `pruefung.masse_pruefen[].in_datei`; Top-Level `kollision_erlaubt`. `BAUGRUPPEN_TYPEN = frozenset({"komponente_neu", "komponente_entfernen", "komponente_ersetzen", "verknuepfung_neu", "verknuepfung_wert", "verknuepfung_loeschen"})`.
- `quelle` in `komponente_neu` und `komponente_ersetzen` wie `#/$defs/quelle` im Baugruppen-Schema. `verknuepfung_neu.a|b`: `komponente` plus eines von `nahe`, `feature`+`flaeche`, `referenz`, `ebene`, `gewinde`+`instanz`+`achse`.

- [ ] **Step 1: Tests schreiben**

```python
def test_beispiel_baugruppe_ist_gueltig(tmp_path): ...
def test_wie_und_quelle_schliessen_sich_aus(tmp_path): ...
def test_grenze_nur_min_oder_max(tmp_path): ...
@pytest.mark.parametrize("feld", ["a", "b"])
def test_anker_einer_verknuepfung_sind_bauweg(feld): ...         # Prüfsumme gleich
@pytest.mark.parametrize("aenderung", ["neu", "alt", "lage_folgen", "kollision_erlaubt", "in_datei", "verknuepfungen", "quelle"])
def test_anforderung_aendert_pruefsumme(aenderung): ...
def test_teil_quelle_geht_in_die_pruefsumme(tmp_path): ...       # Änderung an der Teil-Spec eines komponente_neu → FREIGABE_VERALTET
def test_spec_ohne_in_datei_bleibt_wie_bisher(tmp_path): ...     # lagerdeckel_rev.yaml unverändert, gleiche Prüfsumme
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** `BAUWEG_SCHLUESSEL` um `a`, `b` nur für `verknuepfung_neu` ergänzen, sonst träfe es fremde Felder. Teil-Specs aus `quelle.teil` wie `swki/baugruppe/freigabe.py`: je eigene Freigabe, ihre Prüfsummen über das Argument `teile=` von `pruefsumme` und `pruefe_freigabe`, nicht über `zusatz` (das prüft niemand). `teil_summen_aenderung(spec, pfad) -> dict | None` liefert ohne Teil-Quelle `None`, `{}` änderte die Summe von Etappe 1 (`swki/spec/freigabe.py`). Jeder Aufruf von `pruefe_freigabe` in `bestand/bau.py`, `pruefen.py`, `ausgabe.py` gibt `teile` mit.
- [ ] **Step 4: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/bestand -q`. Expected: PASS, Etappe 1 unverändert grün.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: Schema der Baugruppen-Punkte“).

### Task 4: Scheiben und Validierung

**Files:**
- Create: `swki/bestand/scheiben.py`, `swki/bestand/spec_baugruppe.py`, `tests/bestand/beispiel_baugruppe.py` (Attrappe nach dem Format oben)
- Modify: `swki/bestand/spec.py` (`_geprueft`, `validieren`, `aufnahme_zu`: Weiche nach `aufnahme["art"]`)
- Test: `tests/bestand/test_scheiben.py`, `tests/bestand/test_validieren_baugruppe.py`

**Interfaces:**
- Produces in `scheiben.py`: `dateien_mit_punkten(spec: dict) -> list[str]` (Teile mit `in_datei`, Reihenfolge der ersten Nennung); `scheibe(spec: dict, datei: str) -> dict` (Teil-Änderungs-Spec: nur ihre Punkte, Bereiche, `masse_pruefen`, `in_datei` und `lage_folgen` entfernt, `bestand.datei` = `datei`, `bestand.sha256` aus `dateien`); `haupt_punkte(spec: dict) -> list[dict]` (Punkte ohne `in_datei`: Baugruppen-Punkte, `eigenschaft`, `skript`); `aenderung_an_haupt(spec: dict) -> bool` (ein Haupt-Punkt oder `lage_folgen` vorhanden: Hauptbaugruppe wird gespeichert).
- Produces in `spec_baugruppe.py`: `befunde_baugruppe(spec: dict, aufnahme: dict, datei_aufnahme: Callable[[str], dict], ordner: Path) -> tuple[list[dict], list[dict]]` (Befunde, Hinweise); `freigabe_angaben(spec, aufnahme) -> dict` je Punkt-ID (`instanzen`, `verknuepfungen`, `bewegungen`).

- [ ] **Step 1: Tests schreiben**

```python
def test_scheibe_enthaelt_nur_punkte_der_datei(): ...
def test_scheibe_laesst_sich_wie_etappe_1_validieren(): ...       # befunde_gegen_aufnahme(scheibe, teil_aufnahme) == []
def test_teil_punkt_mit_unbekannter_datei(): ...                  # BESTAND_REFERENZ, nennt die Dateien
def test_teil_punkt_auf_datei_mit_referenz(): ...                 # BESTAND_REFERENZ_EXTERN
def test_teil_punkt_auf_basisteil_eines_anderen(): ...            # BESTAND_REFERENZ_EXTERN
def test_teil_punkt_auf_virtuelles_teil(): ...                    # BESTAND_REFERENZ (Review Focus 1)
@pytest.mark.parametrize("typ", ["mass", "gleichung", "unterdruecken", "aufheben", "loeschen", "feature", "material"])
def test_teil_typ_ohne_in_datei_an_baugruppe(typ): ...            # BESTAND_REFERENZ, Präzisierung 8
def test_eigenschaft_ohne_in_datei_ist_erlaubt(): ...
def test_komponente_in_unterbaugruppe_als_ziel(): ...             # BESTAND_REFERENZ; als Partner einer Verknüpfung erlaubt
def test_verknuepfung_von_gleichung_gesteuert(): ...              # MASS_GESTEUERT, kein Punkt-Weg
def test_komponente_unbekannt(): ...                              # BESTAND_REFERENZ
def test_entfernen_nennt_nicht_alle_verknuepfungen(): ...         # VERKNUEPFUNGEN_FEHLEN, fehlen=[…]
def test_verknuepfung_wert_altwert(): ...                         # BESTAND_ALTWERT, auch für grenze: max
def test_verknuepfung_wert_ohne_zahl(): ...                       # konzentrisch → Befund
def test_neue_datei_heisst_wie_eine_im_bestand(): ...             # NAME_BELEGT
def test_wie_mit_gleicher_datei_ist_kein_name_belegt(): ...
def test_lage_folgen_unbekannt(): ...                             # BESTAND_REFERENZ
def test_kollision_erlaubt_nennt_unbekannte_komponente(): ...     # Punkt-ID eines komponente_neu ist erlaubt
def test_hinweis_instanzen(): ...                                 # Teil mit 11 Instanzen: Hinweis art instanzen, anzahl 11 (Review Focus 2)
def test_baugruppen_punkt_braucht_keinen_bereich(): ...
def test_teil_punkt_braucht_bereich(): ...                        # BEREICH_FEHLT wie Etappe 1
def test_validieren_nennt_grenzen_ohne_fahrt(): ...               # Hinweis, wenn die Aufnahme ohne Bewegung lief
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** `_geprueft` ruft für `art: baugruppe` je Datei `befunde_gegen_aufnahme(scheibe(...), teilaufnahme, ordner)` und `feature_befunde`, Pfade auf `punkte[i]` der ganzen Spec zurückgeführt. Die Baugruppen-Punkte prüft nur `befunde_baugruppe`. `validieren` nennt je Datei die `version_aelter`, die gespeichert werden müssen.
- [ ] **Step 4: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/bestand -q`. Expected: PASS.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: Scheiben und Validierung“).

### Task 5: Vergleich der Baugruppe (§8.3)

**Files:**
- Create: `swki/bestand/vergleich_baugruppe.py`
- Test: `tests/bestand/test_vergleich_baugruppe.py`

**Interfaces:**
- Consumes: `eintrag` aus `swki.pruefung.bewertung`, `ist_bewegt` aus `swki.baugruppe.bewegung`.
- Produces: `vergleiche_baugruppe(spec: dict, vorher: dict, nachher: dict, neue: dict[str, list[str]], ersetzt: dict[str, str]) -> list[dict]`; aus dem Protokoll: `neue`: Punkt-ID → SolidWorks-Namen (auch mehrere bei `alle_instanzen`), `ersetzt`: alter → neuer Name. Einträge `komponenten`, `verknuepfungen`, `bestimmtheit`, `kollision`, `lage`, `punkt:<id>`. `vergleiche_dateien(spec: dict, bestand: dict, ist: dict[str, str]) -> dict` (Eintrag `dateien`).

- [ ] **Step 1: Tests schreiben**

```python
def test_unveraendert_alles_ok(): ...
def test_komponente_weg_ohne_punkt_ist_mangel(): ...
def test_neue_komponente_aus_punkt_ist_ok(): ...
def test_andere_konfiguration_ist_mangel(): ...
def test_lage_verschoben_ohne_erlaubnis(): ...                    # 0,01 mm über TOL_BEWEGT_MM
def test_lage_folgen_erlaubt_nur_genannte(): ...
def test_jede_instanz_einzeln(): ...                              # Review Focus 2: M5-3 verschoben, M5-1 nicht
def test_kind_einer_unterbaugruppe_verschoben(): ...              # Datei der Unterbaugruppe gleich, "Sub-1/Teil-1" anders → Mangel lage
def test_ersetzte_komponente_ist_kein_fehlt_und_fremd(): ...      # Zuordnung ersetzt, auch mit alle_instanzen
def test_verknuepfung_weg_ohne_punkt(): ...
def test_verknuepfung_fehler_aus_dem_bestand_zaehlt_nicht(): ...  # Review Focus 5, steht im Eintrag
def test_neuer_verknuepfungsfehler_ist_mangel(): ...
def test_wert_geaendert_nur_mit_punkt(): ...
def test_bestimmtheit_schlechter_ist_mangel(): ...                # 3 → 2 ohne Punkt
def test_neue_komponente_muss_voll_bestimmt_sein(): ...
def test_alte_kollision_ist_kein_mangel_steht_aber_da(): ...
def test_neue_kollision_ist_mangel(): ...
def test_kollision_erlaubt_nimmt_nur_das_paar(): ...
def test_unterdrueckte_komponente_ohne_transform(): ...           # Review Focus 4: None → ok None nur, wenn sie aktiv ist; unterdrückt in beiden zählt nicht
def test_je_konfiguration(): ...                                  # Abweichung nur in Variante B fällt auf
def test_dateien_nur_erwartete_geaendert(): ...
def test_haupt_gleich_obwohl_punkt_verlangt(): ...                # Mangel: Punkt hat nichts gespeichert
def test_datei_fehlt_im_lauf(): ...
def test_neue_datei_ohne_punkt(): ...
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** Lageabweichung wie `ist_bewegt`, Schlüssel `(name, konfiguration)`. Nur Hochstufen des Status gilt nie als Mangel (Rang wie `SKIZZE_RANG`). `None` macht den Eintrag `ok: None`, ein Mangel hat Vorrang.
- [ ] **Step 4: Test laufen lassen.** Expected: PASS.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: Vergleich der Baugruppe“).

### Task 6: Bewegungen gegen den Bestand (§8.4)

**Files:**
- Create: `swki/bestand/bewegung_bestand.py`
- Test: `tests/bestand/test_bewegung_bestand.py`

**Interfaces:**
- Consumes: `Bewegung`, `Lauf`, `BewegungsMesswerte`, `bewerte_bewegungen`, `ist_bewegt` (`swki.baugruppe.bewegung`), `fahre`, `Mechanik` (`swki.baugruppe.bewegungslauf`), `Verknuepfung` (`swki.baugruppe.aufloesen`).
- Produces:
  - `grenze_als_bewegung(name: str, v: dict, komponente: str, schritte: int) -> Bewegung`; `grenzen_der_aufnahme(aufnahme: dict) -> dict[str, dict]` (nur Hauptbaugruppe, ohne unterdrückte).
  - `als_verknuepfung(name: str, v: dict) -> Verknuepfung`: `typ` `grenze_abstand`/`grenze_winkel`, `vorlage` = `id` = `name`, `drehung_sperren` False, `a`/`b` tragen `{"komponente", "index"}`, `ausrichtung` als Text: 0 `gleich`, 1 `entgegengesetzt`, 2 `None` (`AUSRICHTUNG`, `NAECHSTE` in `sw_baugruppe.py`; die Zahl aus der Aufnahme darf nicht durchgereicht werden).
  - `bewegte_seite(mech: Mechanik, name: str, v: dict, aufnahme: dict) -> str`: nicht fixierter Partner, sonst Probeschritt, beide bewegt: Seite a.
  - `fahre_bestand(mech, grenzen, schritte, bekannt, grenze_mb, tol_mm, start_mb) -> dict`: das Feld `bewegungen` der Aufnahme. Erst alle zusammen über `fahre`; scheitert das mit `StellungFehler`, die benannte Grenze als `gefahren: false` mit Grund vermerken und den Rest neu fahren. `min == max`: nicht gefahren, Grund nennen (sonst Division durch null in `_sollweg`).
  - `bekannte_paare(vorher: dict, spec: dict, neue: dict) -> set[frozenset]`: statische Kollisionen, Fahrt-Kollisionen des Bestands, `kollision_erlaubt` mit aufgelösten Punkt-IDs.
  - `vergleiche_bewegungen(vorher: dict, nachher: dict, spec: dict, neue: dict) -> list[dict]`, auch für `freiheitsgrad:<k>`.

- [ ] **Step 1: Tests schreiben** (Mechanik-Attrappe aus `tests/baugruppe`)

```python
def test_fixierter_partner_bewegt_sich_nicht(): ...
def test_probeschritt_findet_die_bewegte_seite(): ...
@pytest.mark.parametrize("zahl,text", [(0, "gleich"), (1, "entgegengesetzt"), (2, None)])
def test_ausrichtung_wird_uebernommen(zahl, text): ...
def test_eine_kaputte_grenze_kostet_nur_sie_selbst(): ...          # zwei Grenzen, eine StellungFehler → andere gefahren
def test_grenze_ohne_weg_wird_nicht_gefahren(): ...
def test_fahrt_an_der_aufnahme_haelt_ergebnis_fest(): ...
def test_gefahren_und_nachher_ohne_fehler_ok(): ...
def test_gefahren_und_nachher_fehler_ist_mangel(): ...
def test_im_bestand_nicht_gefahren_ist_kein_mangel(): ...          # Review Focus 5, Hinweis im Eintrag
def test_grenze_fehlt_ohne_punkt_ist_mangel(): ...
def test_grenze_geloescht_mit_punkt_ist_ok(): ...
def test_neuer_bereich_aus_punkt_gilt(): ...
def test_andere_menge_ist_mangel(): ...
def test_neue_schraube_am_bewegten_teil_darf_mitfahren(): ...
def test_neue_kollision_ist_mangel_bekannte_nicht(): ...
def test_kollision_erlaubt_gilt_auch_in_der_fahrt(): ...
def test_ohne_fahrt_in_der_aufnahme_ist_ok_none(): ...             # --ohne-bewegung
def test_unterbaugruppe_nur_hinweis(): ...
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** `bewerte_bewegungen(spec={"bewegungen": []}, …)` liefert die Einträge beider Stände. `vergleiche_bewegungen` hebt einen Eintrag, der schon im Bestand nicht `ok` war, auf `ok: True` mit `hinweis`, und ergänzt `bewegung_menge`. `bewegungen_oder_ersatz` passt nicht: Es fährt bei Bestandsfehlern gar nicht.
- [ ] **Step 4: Test laufen lassen.** Expected: PASS.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: Bewegungen gegen den Bestand“).

### Task 7: Abgleich und `swki aenderungen` (§8.5, §8.6)

**Files:**
- Create: `swki/bestand/abgleich.py`
- Modify: `swki/aenderungen.py`, `swki/baugruppe/pruefen.py` (Bericht trägt `lagen`)
- Test: `tests/bestand/test_abgleich.py`, `tests/test_aenderungen_baum.py`

**Interfaces:**
- Produces: `abgleich_teil(protokoll_teil: dict, spec_teil: dict, ist: dict) -> dict` (`features_neu`, `features_fehlen`, `masse`, `material`, `eigenschaften`); `abgleich_baugruppe(protokoll: dict, soll_werte: dict, ist: dict, lagen: dict | None) -> dict` (`komponenten_neu`, `komponenten_weg`, `andere_datei`, `verknuepfungen_neu`, `verknuepfungen_weg`, `werte`, `fehler`, `unterdrueckt`, `lagen`, `lage_geprueft`); `abgleich_dateien(soll: dict, ist: dict) -> dict`; `ist_erklaert(feature: dict, soll: set[str], alle: dict) -> bool`: im Soll, Vorlage (Ursprung, Standardebenen, Ordner) oder Skizze/Unterfeature eines Soll-Features.
- `swki aenderungen`: gibt je Teil zusätzlich `baum`; öffnet `sichtbar=False, nur_lesen=True`; ein Eintrag „Datei geändert, Maße gleich“ erscheint nur noch, wenn auch der Baum nichts erklärt, dann mit `nicht_erklaert: true`. Den Block `baugruppe` ergänzt Task 8, er braucht `lies_baugruppe`.
- **Lauf mit Aufnahme** (`aufnahmen_aus_lauf` nicht leer): `aenderungen` öffnet nichts, nennt `geaendert` per SHA-256 und `abgleich: "swki bestand abgleich <auftrag> --spec …"`.
- `AenderungFehler` von `pruefe_unveraendert` nennt `aufnahmen: [{auftrag, aufnahme}]` aus `aufnahmen_aus_lauf`, der Meldungstext den dritten Weg und bei einer Aufnahme `swki bestand abgleich` statt `swki aenderungen`.

- [ ] **Step 1: Tests schreiben**

```python
def test_unveraendertes_teil_nennt_nichts(): ...                  # Protokollform wie lauf-30: f1, winkel, gewinde
def test_neues_feature_wird_genannt(): ...
def test_umbenanntes_feature_ist_weg_und_neu(): ...
def test_skizze_eines_soll_features_ist_erklaert(): ...
def test_unterfeature_des_bohrungsassistenten_ist_erklaert(): ...
def test_vorlage_ist_erklaert(): ...
def test_neue_komponente_und_gleiche_datei(): ...                 # weitere Instanz derselben Datei
def test_umbenannte_komponente(): ...                             # Name anders, Datei gleich: nennt beides
def test_neue_verknuepfung_und_geaenderter_wert(): ...
def test_verknuepfung_mit_fehler(): ...
def test_lage_aus_export(): ...                                   # Format [{"name", "transform"}]
def test_ohne_lagen_steht_das_da(): ...                           # lage_geprueft False
def test_aenderungen_oeffnet_nur_lesend(monkeypatch): ...
def test_aenderungen_oeffnet_lauf_mit_aufnahme_nicht(monkeypatch, tmp_path): ...  # verbinde nie gerufen, Verweis in der Antwort
def test_manuell_geaendert_nennt_die_aufnahme(tmp_path): ...
def test_fremder_lauf_wird_nicht_beschrieben(tmp_path): ...       # Ordnerinhalt und mtimes vor/nach gleich
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** Soll-Features aus `knoten[].sw_name` bzw. `sw_namen`, Soll-Verknüpfungen aus Knoten mit Verknüpfungs-`typ`, Werte mit `soll_verknuepfungswerte`. `_TEXT_AENDERUNG` bleibt für `art: aenderung`.
- [ ] **Step 4: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/test_aenderungen.py tests/test_aenderungen_masse.py tests/test_aenderungen_baum.py tests/bestand/test_abgleich.py -q`. Expected: PASS.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: Abgleich gegen den Spec-Stand“).

### Task 8: Baugruppe lesen, `aufnehmen`, `abgleich`

**Files:**
- Create: `swki/bestand/sw_baugruppe_bestand.py`, `tests/bestand/sw_attrappe_baugruppe.py`
- Modify: `swki/bestand/ablage.py` (`pruefe_format` nimmt `.sldasm`), `tests/bestand/test_ablage.py` (`.sldasm`-Fall), `swki/bestand/befehle.py`, `swki/bestand/sw_bestand.py` (Helfer öffentlich, `speichere_an_ort(model, pfad, lauf: Path)` prüft „unter genau diesem Lauf-Ordner“, auch in Unterordnern), `swki/aenderungen.py` (Block `baugruppe`), `swki/baugruppe/sw_baugruppe.py` (`stelle(…, bekannt=frozenset())`: Fehler dieser Verknüpfungen zählen nicht), `swki/baugruppe/sw_bewegung.py` (`bekannte_fehler`; `_teilebox` fragt `GetPartBox` nur bei Teilen, Unterbaugruppe über `GetBox`)
- Test: `tests/bestand/test_aufnehmen_baugruppe.py`

**Interfaces:**
- Produces: `lies_komponenten(asm, konfigurationen) -> dict` (alle Ebenen, je Konfiguration nach Neuaufbau, unterdrückt: `transform` `null`), `lies_verknuepfungen(asm, konfigurationen) -> dict`, `lies_baugruppe(app, asm) -> dict` (Format oben ohne `datei`, `dateien`, `bewegungen`); `baum_ohne_glieder(model) -> list` (`baum_features` ohne Komponenten und Verknüpfungen, Typnamen aus S19f); `mechanik_fuer(app, asm, grenzen: dict, aufnahme: dict, ordner: Path | None) -> SwMechanik`: nur oberste Ebene, nur nicht unterdrückte Komponenten, liest die Entitäten der Grenzen **vor** `fahre`, das sie unterdrückt, und gibt die Verknüpfungsfehler der Aufnahme als `bekannte_fehler` mit.
- `swki bestand aufnehmen <pfad> --auftrag <a> [--ohne-bewegung]`: Ablauf Spec §8.1, Ausgabe `zusammenfassung` plus `komponenten`, `verknuepfungen`, `grenzen`, `kollisionen`, `dateien`, `warnungen`, `herkunft`, `messung`.
- `swki bestand abgleich <auftrag> --spec <pfad> [--aufnahme n] [--lagen <json>]`: öffnet nichts im Lauf-Ordner.
- `swki bestand zeige <auftrag> --komponente <name>`.
- `--referenzbau` (Nutzer 2026-11-01: ja) baut mit `baue_teil_dokument` die Eigenteile mit geänderter SHA-256 aus der freigegebenen Teil-Spec nach `<auftrag>/referenz-<n>/`, liest sie mit `lies_bestand`, vergleicht mit der Bestandskopie (`vergleiche` ohne Punkte, `koerper_differenz`) und meldet `features`, `masse`, `differenzen`. Test: `test_referenzbau_schreibt_nur_unter_referenz`, `test_referenzbau_baut_nur_geaenderte`.

- [ ] **Step 1: Tests schreiben** (Attrappe: Komponenten, Verknüpfungen, Grenze, Abhängigkeiten)

```python
def test_kopiert_alle_und_liest_jede_datei_einmal(r, attrappe): ...   # 11 Instanzen → eine Aufnahme
def test_liest_nach_dem_schliessen_der_baugruppe(r, attrappe): ...    # Reihenfolge der Aufrufe
def test_oeffnet_nie_das_original(r, attrappe): ...                   # alle OpenDoc6-Pfade unter bestand-<n>
def test_datei_aus_neuerem_jahr(r, attrappe): ...                     # BESTAND_VERSION_NEUER, keine Aufnahme bleibt
def test_lightweight_komponente(r, attrappe): ...                     # GetModelDoc2 None, Lesen geht (Review Focus 4)
def test_unterdrueckte_komponente(r, attrappe): ...
def test_warnung_offen(r, attrappe): ...                              # ~$-Datei → warnungen, Aufnahme läuft
def test_herkunft_und_belegter_auftrag(r, attrappe): ...
def test_ohne_bewegung(r, attrappe): ...                              # kein mech, gefahren False
def test_fahrt_speichert_nichts(r, attrappe): ...                     # Save3 nie, Hash der Kopie gleich
def test_abgleich_oeffnet_keinen_lauf_ordner(r, attrappe): ...
def test_speichere_an_ort_unterordner(r, tmp_path): ...               # lauf-3/teile/A.SLDPRT ok, bestand-1/… Fehler
def test_speichere_an_ort_fremder_auftrag(r, tmp_path): ...           # anderer Auftrag/lauf-30 → Fehler, auch bei gleicher Nummer
def test_einzelnes_teil_geht_ueber_oeffne_in(r, attrappe): ...        # Pfadschutz auch beim Lesen je Datei
def test_lies_baut_vor_den_lagen_neu_auf(attrappe): ...               # geändertes Teil, ungespeicherte Baugruppe: neue Lage
def test_alter_verknuepfungsfehler_stoppt_die_fahrt_nicht(attrappe):  # Review Focus 5: `stelle` kennt ihn, neuer Fehler stoppt
def test_mechanik_liest_entitaeten_vor_dem_unterdruecken(attrappe): ...
def test_unterbaugruppe_als_bewegte_komponente(attrappe): ...         # _teilebox ohne GetPartBox
def test_teil_wie_bisher(r, attrappe): ...                            # .sldprt-Aufnahme unverändert
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** Reihenfolge: `pruefe_format`, `pruefe_auftrag_frei`, Version und Abhängigkeiten am Original (wie Etappe 1, kein Dokument offen), `ordne_referenzen`, Version je Datei, `kopiere_baugruppe`, `oeffne_in` unsichtbar, `lies_baugruppe`, Kollision, Fahrt, schließen, je Datei einzeln lesen, Bild im Fenster. Zeit und Private Bytes je Phase in `messung` (`swki.speicher.privat_mb`). Abgelehnte Aufnahme entfernt ihren Ordner (Muster `verwirf_aufnahme`).
- [ ] **Step 4: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/bestand -q`. Expected: PASS.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: Baugruppe aufnehmen und abgleichen“).

### Task 9: Punkt-Handler der Baugruppe

**Files:**
- Create: `swki/bestand/punkte_baugruppe.py`
- Test: `tests/bestand/test_punkte_baugruppe.py`

**Interfaces:**
- Consumes: `sw_baugruppe.fuege_ein`, `.verknuepfe`, `.fixiere`, `.in_baugruppe`; `loese_im_teil`; `normteil_befehle.hole`, `kaufteil_befehle.hole`, `baue_teil_dokument`.
- Modify: `sw_baugruppe.fuege_ein(app, asm, pfad, box_mm, konfiguration: str = "")`: `AddComponent5` mit swAddComponentConfigOptions_e für eine benannte Konfiguration (Wert laut `swki api enum`).
- Produces: `BauKontext` (dataclass: `app`, `asm`, `spec`, `spec_pfad`, `ordner`, `aufnahme`, `standard`, `neue: dict[str, list]`, `ersetzt: dict[str, str]`, `kontexte: dict`); Handler `(b: BauKontext, p: dict) -> list[str]` je Typ über `@punkt`; `hole_neue_dateien(b, spec) -> dict[str, Path]`; `loesche_komponente(asm, komp) -> None` (`sw_baugruppe.loesche` kennt nur Verknüpfungen).

- [ ] **Step 1: Tests schreiben**

```python
def test_neu_aus_normteil_liegt_neben_der_baugruppe(tmp_path): ...
def test_neu_wie_komponente_gleiche_datei_gleiche_konfiguration(): ...
def test_neu_in_allen_konfigurationen_aktiv(): ...                  # S18c: sonst unterdrückt
def test_entfernen_prueft_die_mitgenommenen_verknuepfungen(): ...   # andere gehen mit → BauFehler
def test_ersetzen_ruft_mit_reattach_und_misst_nach(): ...
def test_ersetzen_nennt_verlorene_verknuepfungen(): ...
def test_ersetzen_fuehrt_alt_zu_neu(): ...                          # b.ersetzt, auch bei alle_instanzen
def test_verknuepfung_neu_loest_punkt_id_und_sw_name(): ...
def test_verknuepfung_wert_prueft_alt_live(): ...                   # BESTAND_ALTWERT
def test_grenze_aendern_misst_nach(): ...                           # ModifyDefinition, Rückgabe zählt nicht
def test_verknuepfung_loeschen_misst_nach(): ...
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** Jeder Handler misst nach dem Neuaufbau nach, nach `lies_verknuepfungen` bzw. `lies_komponenten`. Neue Verknüpfung über ein `Verknuepfung` mit `id` = gewünschtem Namen. Kontexte fremder Teile wie `punkte.kontext`, fremde Namen in `ctx.ergebnisse`.
- [ ] **Step 4: Test laufen lassen.** Expected: PASS.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: Punkte der Baugruppe“).

### Task 10: `swki bauen` für Baugruppen

**Files:**
- Create: `swki/bestand/bau_baugruppe.py`
- Modify: `swki/bestand/bau.py` (Weiche nach `aufnahme["art"]`; `_aendere_und_speichere` nimmt die Scheibe unverändert)
- Test: `tests/bestand/test_bau_baugruppe.py`

**Interfaces:**
- Produces: `bauen_baugruppe(spec_pfad, spec, aufnahme, lauf, verwerfen, uebernommen, hochstufen) -> dict`; Protokoll zusätzlich `dateien` (`haupt`, `geaendert:<rel>`), `neue` (Punkt-ID → SW-Namen), `ersetzt`, `messung`; `pruefe_stand_baugruppe(asm, aufnahme, spec, neue) -> None`.
- `--hochstufen` nur für Dateien, die gespeichert werden; `version_aelter` einer ungeänderten Datei stört nicht.

- [ ] **Step 1: Tests schreiben**

```python
def test_teil_scheiben_laufen_zuerst(): ...                         # Präzisierung 6
def test_nur_geaenderte_dateien_werden_gespeichert(): ...           # Save3 einmal, Hash der übrigen gleich
def test_haupt_bleibt_ungespeichert_ohne_baugruppen_punkt(): ...
def test_haupt_wird_gespeichert_mit_lage_folgen(): ...
def test_fehler_in_scheibe_speichert_die_baugruppe_nicht(): ...
def test_fehler_im_baugruppen_punkt_speichert_nicht(): ...
def test_neuer_verknuepfungsfehler_bricht_ab(): ...
def test_bekannter_verknuepfungsfehler_bricht_nicht_ab(): ...       # Review Focus 5
def test_pfadschutz_vor_dem_bau(): ...                              # fremder Pfad → kein Punkt läuft
def test_lauf_startet_immer_aus_dem_bestand(): ...
def test_protokoll_traegt_alle_shas(): ...
def test_aktive_konfiguration_wie_aufgenommen(): ...
def test_manuell_geaendert_gilt_wie_bisher(): ...
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** Ablauf: Freigabe, `aufnahme_zu`, alle Bestandsdateien gegen `dateien.json` (`BESTAND_ABWEICHEND`), `pruefe_unveraendert`, `lauf_kopie_alle`, Teil-Scheiben (jede über `oeffne_in`, Kern von Etappe 1), `hole_neue_dateien`, `oeffne_in` sichtbar, Haupt-Punkte über `durchlaufe`, `pruefe_stand_baugruppe` in allen Konfigurationen, speichern bei `aenderung_an_haupt`.
- [ ] **Step 4: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/bestand -q`. Expected: PASS.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: swki bauen für Baugruppen“).

### Task 11: `pruefen`, Ausgabe, Bericht

**Files:**
- Create: `swki/bestand/pruefen_baugruppe.py`
- Modify: `swki/bestand/pruefen.py` (Kern als `pruefe_teil(app, scheibe, freigegeben, spec_pfad, vorher, kopie, teil, ordner, tol_mm, standard, protokoll) -> dict`; `spec_pfad` braucht der Messkontext, das Öffnen geht über `oeffne_in`), `swki/bestand/ausgabe.py`, `swki/pruefung/bericht.py`, `swki/durchlauf.py`, `.claude/agents/pruefer.md`
- Test: `tests/bestand/test_pruefen_baugruppe.py`, `tests/bestand/test_ausgabe_baugruppe.py`

**Interfaces:**
- Produces: `pruefen_baugruppe(spec_pfad, spec, vorher, lauf, protokoll, standard, r) -> dict`. Bericht: `pruefungen` mit Präfix `<rel>/` für Teilprüfungen außer `punkt:<id>`, `differenzen` je Datei, `dateien`, `bewegungen`, `bilder`, `bilder_vorher`, `messung`.
- `ausgabe`: je Datei `neu: bool`; `original` aus `dateien.json`; neue Dateien neben die Hauptbaugruppe; Warnung `BESTAND_ORIGINAL_GEAENDERT` je Datei.

- [ ] **Step 1: Tests schreiben**

```python
def test_nur_geaenderte_teile_werden_verglichen(): ...              # 35 Dateien, 1 geändert → eine vorher_-Kopie
def test_bestand_und_lauf_nie_zugleich_offen(): ...
def test_ohne_mangel_bestanden(): ...
def test_ok_none_ist_nicht_bestanden(): ...
def test_bewegung_laeuft_und_steht_im_bericht(): ...
def test_speicher_knapp_bricht_ab(): ...
def test_pruefbericht_traegt_pfade_und_dateien(): ...
def test_kein_dokument_wird_gespeichert(): ...
def test_ausgabe_nur_geaenderte_und_neue(): ...
def test_ausgabe_liegt_nur_unter_ausgabe(): ...
def test_ausgabe_warnt_je_geaendertem_original(): ...
def test_ausgabe_aus_herkunft_schreibt_nicht_in_den_lauf(): ...
def test_teil_pruefen_bleibt_gleich(): ...                          # tests/bestand/test_pruefen.py unverändert grün
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.
- [ ] **Step 3: Implementieren.** `pruefer_auftrag` nennt Vorher-Bilder von Bestand und Lauf und die Bewegungsbilder. `pruefer.md`: Baugruppen-Abschnitt der Änderungs-Checkliste (Punkt an der gemeinten Stelle, `lage_folgen` plausibel, neue Komponente sitzt richtig, Kollisionsliste, Bewegungsbilder).
- [ ] **Step 4: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest -q`. Expected: PASS; `swki api pruefe-code` ohne Befund.
- [ ] **Step 5: Commit** („Bestandsdateien Etappe 2: prüfen, ausgeben, berichten“).

### Task 12: Spike S19 und Musterbaugruppe (live)

**Vor dem Start:** Meldung des Nutzers in dieser Session, `~$`-Dateien in `lauf-30` weg, keine andere SolidWorks-Arbeit. Erst danach `werkzeuge.sw_neustart`.

**Files:**
- Create: `spikes/s19_baugruppe.py`, `docs/bestandsdateien/s19_<zeile>.json`, `tests/referenz/bestand/muster/baugruppe/`
- Modify: `werkzeuge/bestand_muster.py`, `docs/bestandsdateien/ergebnisse.md`, Spec, dieser Plan

- [ ] **Step 1: Musterbaugruppe erzeugen.** Rohe API, ohne `swki.compiler`: `Hubeinheit.SLDASM` mit `teile/Grundplatte.SLDPRT`, `teile/Schlitten.SLDPRT`, Unterbaugruppe `Muster.SLDASM` (vorhanden), Grenzverknüpfung Schlitten 0…25 mm, Abstandsverknüpfung, zweite Konfiguration mit unterdrückter Komponente, zwei Instanzen derselben Datei, importierte Komponente. Ins Git unter `muster/baugruppe/`; `CLAUDE.md`-Ausnahme mitziehen.
- [ ] **Step 2: S19 an Kopien der Muster und der Referenz Schlitten ausführen**, je Zeile Ergebnis, Weg, Zeit, Private Bytes in `ergebnisse.md`:

| Zeile | Pflichtfrage |
|---|---|
| a | Woran erkennt man eine Grenzverknüpfung? `IMate2.Min/MaximumVariation` oder `GetDefinition`? Werte in mm? Partner bei Ebene der Baugruppe? |
| b | Ist `MateEntity(i).Reference` oder `EntitiesToMate` für `treibe` auswählbar? Überleben die Zeiger das Unterdrücken der Grenze und den Neuaufbau? Liegt der Antrieb bei umgekehrter Bemaßung auf der richtigen Seite (`verknuepfe` setzt Flip fest auf False)? Fährt das an nur lesend geöffneter Kopie? SHA-256 danach gleich? |
| c | Struktur `teile/` bei vorhandenem Original: aus der Kopie geladen? Datei flach daneben? Löst `GetDocumentDependencies2(…, True, True, False)` genauso auf wie das Öffnen, auch bei einem Original im Arbeitsordner? Zurückkopierte Baugruppe mit Lauf-Pfaden lädt was? |
| d | Baugruppe unsichtbar mit Option 1\|64\|2: Kollision, `Transform2`, Status lesbar? Zeit, Speicher gegenüber sichtbar? |
| e | Einfügen, `ReplaceComponents2` (bleibt `Name2`?), Löschen, Grenze über `ModifyDefinition` an fremder Baugruppe, je Konfiguration? |
| f | `GetTypeName2` von Komponente, Verknüpfung, Komponentenmuster, virtuellem Teil; wie erscheint ein virtuelles Teil in `GetDocumentDependencies2`; `Name2` und `Transform2` in Unterbaugruppen (Bezug oberste Baugruppe?); was meldet `ListExternalFileReferences` an einer Baugruppe? |

- [ ] **Step 3: Phase B und Spec nachziehen.** Weicht ein Weg ab, zuerst Tests, dann Code, Nachtrag „Nachgezogen“ in die Spec. **Hier anhalten und den Nutzer fragen, wenn S19c die Struktur `teile/` nicht trägt** (der Ausweg über `ReplaceReferencedDocument` ändert die SHA-256 der Baugruppe und damit „nur Geändertes ausgeben“) **oder wenn die Auflösung vor dem Öffnen anders ausfällt als das Öffnen** (dann ist die erste Sperre aus Spec §8.1a nichts wert und das Original könnte geladen werden, vor `lauf-30` zwingend zu klären).
- [ ] **Step 4: Commit** („Spike S19: Baugruppen live, Musterbaugruppe“).

### Task 13: Referenz und Negativfälle (live)

**Files:**
- Create: `tests/referenz/bestand/hubeinheit_rev.yaml`, `tests/referenz/bestand/eingabe/aufgabe_baugruppe.md`, `tests/live/test_live_bestand_baugruppe.py`
- Modify: `tests/referenz/test_bestand.py`, `tests/referenz/bestand/` Prüfer-Vorlage

- [ ] **Step 1: Änderungs-Spec schreiben:** `mass` mit `in_datei` und `lage_folgen`, `gleichung` in einem Teil, `komponente_neu` ISO 4762, zwei `verknuepfung_neu`, `verknuepfung_wert` (Grenze max), `komponente_entfernen`, `komponente_ersetzen`, `kollision_erlaubt`.
- [ ] **Step 2: Live-Tests schreiben und einzeln laufen lassen.** Run: `.venv\Scripts\python.exe -m werkzeuge.live_frisch tests/live/test_live_bestand_baugruppe.py tests/referenz/test_bestand.py --zeit 1500`. Expected: Referenz „bestanden“ (Code-Prüfungen, Prüfer), Originale per SHA-256 gleich, `ausgabe` nennt nur Geändertes und Neues.

| Negativfall | Erwartet |
|---|---|
| Datei fehlt im Lauf, Original am gespeicherten Pfad | `BESTAND_PFAD_FREMD`, nichts gespeichert, kein Dokument aus dem Original im Fehlerfall gespeichert |
| Komponente von Hand verschoben, kein Punkt | Mangel `lage` |
| Verknüpfung im Lauf gelöscht, kein Punkt | Mangel `verknuepfungen`, `bewegung:*` |
| neue Schraube kollidiert ohne `kollision_erlaubt` | Mangel `kollision` |
| Grenze blockiert durch neue Komponente | Mangel `bewegung_kollision` oder `bewegung` |
| unbeteiligtes Teil gespeichert | Mangel `dateien` |
| `komponente_entfernen` ohne alle Verknüpfungen | `VERKNUEPFUNGEN_FEHLEN` |
| Punkt auf Teil mit Referenz im Kontext | `BESTAND_REFERENZ_EXTERN` |
| Original nach der Aufnahme geändert | Warnung `BESTAND_ORIGINAL_GEAENDERT` |
| Rückweg: Ausgabe neben Kopie der Originale | keine Warnung außer 32, alle Pfade im Zielordner |

- [ ] **Step 3: Commit** („Bestandsdateien Etappe 2: Referenz Hubeinheit und Negativfälle“).

### Task 14: Größe messen (live)

**Files:**
- Create: `werkzeuge/bestand_gross.py`, Zeile in `werkzeuge/__init__.py`
- Modify: `docs/bestandsdateien/ergebnisse.md`

- [ ] **Step 1: Werkzeug schreiben.** Erzeugt im Arbeitsordner 40 Teile, 200 Komponenten, ein Teil mit rund 2000 Flächen (Bohrbild), Grenzverknüpfung; läuft `aufnehmen`, einen Bau mit einem Teil-Punkt und `pruefen`.
- [ ] **Step 2: Laufen lassen** auf frischem SolidWorks, je sichtbar und unsichtbar. Tabelle je Phase: Zeit, Private Bytes Spitze. Dazu Teil-Differenz bei 2000 Flächen.
- [ ] **Step 3: Bewerten.** Liegt eine Phase über `speicher_grenze_mb` oder braucht die Aufnahme mehr als zehn Minuten, im Ergebnis mit Ursache nennen und dem Nutzer vorlegen, nichts still abschalten.
- [ ] **Step 4: Commit** („Bestandsdateien Etappe 2: Größenmessung“).

### Task 15: Regeln, Skills, Regression

**Files:**
- Modify: `.claude/skills/aendern/SKILL.md`, `.claude/skills/baugruppe/SKILL.md`, `.claude/skills/konstruieren/SKILL.md`, `CLAUDE.md`, `docs/bestandsdateien/inbetriebnahme-firmenrechner.md`, Gesamtdesign §5/§11

- [ ] **Step 1: Skill `aendern` erweitern:** Baugruppen, drei Wege aus Spec §8.5, neuer Auftrag, `abgleich`, `in_datei`, `lage_folgen`, `kollision_erlaubt`, Bewegungen, Fehlercodes. Beschreibung: „fremde Baugruppen noch nicht“ raus. Skills `baugruppe`, `konstruieren`: dritter Weg bei `MANUELL_GEAENDERT`.
- [ ] **Step 2: `CLAUDE.md` nachziehen:** Etappe 2, Musterausnahme, neue Befehle.
- [ ] **Step 3: Volle Regression.** Run: `.venv\Scripts\python.exe -m pytest -q`, `.venv\Scripts\python.exe -m swki api pruefe-code`, `.venv\Scripts\python.exe -m werkzeuge.live_frisch tests/referenz --zeit 1500`. Expected: alle grün, kein Befund. Ausgabe in `ergebnisse.md`.
- [ ] **Step 4: Commit** („Bestandsdateien Etappe 2: Skill, Regeln, Regression“).

### Task 16: Abnahme an `lauf-30` (live)

**Voraussetzung:** Meldung des Nutzers. Seine Änderungsliste **nicht** erfragen. Auftrag `AP68-Pruefstation-Rev1`, Ordner `auftraege/AP68-Pruefstation-Rev1/` (nicht im Git), `auftraege/AP68-Pruefstation/` bleibt unverändert.

- [ ] **Step 1: Aufnehmen.** `swki bestand aufnehmen <lauf-30>/AP68-Pruefstation_Pruefstation.SLDASM --auftrag AP68-Pruefstation-Rev1`. Prüfen: SHA-256 aller Dateien in `lauf-30` vor und nach gleich, Herkunft richtig, Bewegungen gefahren.
- [ ] **Step 2: Blindtest.** `swki bestand abgleich AP68-Pruefstation-Rev1 --spec <…>/pruefstation.yaml --lagen <lauf-30>/export/AP68-Pruefstation_lauf30_protokollstand.komponenten.json --referenzbau`. Nicht `swki aenderungen`: Es öffnete den Lauf. Liste schriftlich festhalten und dem Nutzer vorlegen, **bevor** er seine Liste zeigt. Dann Abgleich: gefunden, übersehen, Fehlalarm, je mit Ursache. Übersehenes wird behoben oder als Grenze benannt, nicht wegdefiniert.
- [ ] **Step 3: Neue Anforderungen umsetzen.** Skill `aendern`: Punkte zuordnen, Spec, `validieren`, Freigabe-Vorlage, **Nutzer-OK**, `swki durchlauf <spec> --freigeben --neustart`, Prüfer, `swki bestand ausgabe`, `swki bericht`.
- [ ] **Step 4: Kennzahlen in `ergebnisse.md`:** Zeiten, Speicher, Differenzen, Befunde, Trefferquote des Blindtests. Maße und Dateien der Prüfstation bleiben dabei außerhalb des Git, soweit sie Kundendaten sind; im Zweifel fragen.
- [ ] **Step 5: Offenes benennen:** echte Kollegen-Baugruppe auf SW 2026 bleibt eigene Abnahme. Commit und PR-Entwurf, kein `git push` ohne OK.

## Selbstprüfung gegen den Auftrag

| Auftrag | Task |
|---|---|
| Aufnahme `.sldasm` samt Dateien | 1, 8 |
| sechs neue Punkt-Typen, Teil-Punkte mit `in_datei` | 3, 4, 9, 10 |
| Prüfungen `komponenten`, `verknuepfungen`, `bestimmtheit`, `kollision`, `lage` | 5, 11 |
| SHA-256 je Datei, Ausgabe nur Geändertes | 5, 11 |
| Lücke 1 Bewegungen | 6, 8, 11, 13 |
| Lücke 2 stilles Laden | 2, 13 |
| Lücke 3 Größe | 8, 14, 16 |
| Lücke 4 eigene Dateien | 1, 7, 15, 16 |
| Lücke 5 `swki aenderungen` | 7, 16 |
| Referenz, Negativfälle, Regression | 12, 13, 15 |
| Abnahme, Blindtest, PR | 16 |
