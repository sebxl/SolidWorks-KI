# Paket Bemaßungsbezug – Bezüge statt Gleichungen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** swki bemaßt Lagen in SolidWorks zu einem Bezug (Mitte, Randkante, Fläche), schreibt Maße als Zahlen, legt standardmäßig keine Gleichungen und globalen Variablen mehr an und liest Handänderungen über ein Maßprotokoll statt über globale Variablen zurück.

**Architecture:** Spike S17 klärt zuerst live, wie SolidWorks zu Modellkanten, Seitenflächen und symmetrisch bemaßt (auch in der Positionsskizze des Bohrungsassistenten) und ob eine Handänderung die Absicht erhält. Danach: Schalter `gleichungen` (Kontext, Teile, Baugruppen, Normteile), reine Rechnung `swki/bemassung.py` (Bezüge lesen, Paare für `mitte`, Maßplan ohne Überbestimmung, Rechteckseite) und `randkante` in `swki/compiler/anker.py`, Schema/`validieren`/Hinweis `bezug`, Maßprotokoll (`ctx.mass` ersetzt `ctx.verknuepfe`, Knoten `masse` im Bauprotokoll), Skizzierer mit Bezügen, Prüfung `gleichungen`, `swki aenderungen` über Maße, Live-Tests und Referenzen, Doku.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) für Spike und Live-Tests.

**Spec:** `docs/superpowers/specs/2026-10-23-bemassungsbezug-design.md` (mit dem Nutzer abgestimmt, 2026-10-23). Kontext: Gesamtdesign `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` (§4), Spec 2c `docs/superpowers/specs/2026-09-29-stufe-2c-design.md` (Hinweise, Normbohrung), Spec 3b §8 (Änderungserkennung).

## Präzisierungen gegenüber der Spec (vom Planer, bindend für diesen Plan)

1. **Module:** Reine Rechnung in `swki/bemassung.py` (ohne SolidWorks, ohne `swki.compiler`-Import); `randkante` in `swki/compiler/anker.py` neben `flaeche_in_richtung` (arbeitet auf `Kante`).
2. **Schalter:** `gleichungen_an(spec: dict, standard: dict) -> bool` in `swki/compiler/eigenschaften.py`: `spec["gleichungen"]` falls vorhanden, sonst `standard.get("gleichungen", False)`. `Kontext` bekommt das Feld `gleichungen: bool = False`; jeder Erzeuger von `Kontext` (`compiler/bauen.py`, `normteile/bau.py`, `pruefung/messen.py`) setzt es über `gleichungen_an`.
3. **Maßprotokoll:** `Kontext.verknuepfe` wird ersetzt durch `Kontext.mass(masname: str, roh, pfad: str, art: str, vorzeichen: int = 1, bezug=None) -> None`. Sie trägt `{"name", "pfad", "art", "bezug", "roh", "vorzeichen", "wert"}` in `ctx.masse[<feature-id>]` ein (`wert` = Betrag in mm bzw. Grad, `roh` = Spec-Rohwert, `bezug` = Text wie `"-rand"` oder `None`) und bindet nur bei `ctx.gleichungen` und Ausdruck per Gleichung – bei `bezug` ∉ (`None`, `"ursprung"`) nie (Spec §4). `art` ∈ `lage`, `groesse`, `tiefe`, `winkel`, `radius`, `abstand`, `versatz`. Die Feature-ID entnimmt `mass` dem Präfix nach `@` nicht – Handler rufen `ctx.mass` immer innerhalb ihres Knotens; `Kontext.knoten: str | None` setzt `baue_features` vor jedem Handler. Spec-Pfade beginnen mit `ctx.pfad(fid)` = `f"features[{index}]"`.
4. **Protokoll:** `Knoten.masse: list[dict] | None = None`; `baue_features` setzt `knoten.masse = ctx.masse.pop(f["id"], None)`.
5. **Zweiphasige Skizze:** `Skizzierer.element` legt Geometrie und Größenmaße sofort an, Lagen nur als `Kennpunkt` vorgemerkt; `Skizzierer.lagen_festlegen()` setzt danach alle Lagen nach `bemassung.massplan`. `skizziere(ctx, ebene, elemente, name, pfade: list[str])` und `positionen_festlegen(ctx, feature, se, positionen, name, bezug: dict | None, pfad: str)`; `pfade[k]` ist der Spec-Pfad des Elements k (bei `bohrung` `features[i].positionen[k]`).
6. **Kontur und Polygon:** laufen über denselben Kennpunkt-Weg mit Bezug `ursprung` (Spec §2: ohne Bezüge, ohne Gleichungen).
7. **Prüfung:** neuer Prüfpunkt `gleichungen` (nur bei `gleichungen_an` falsch): `ok` genau dann, wenn das Teil 0 Gleichungen hat; Mangeltext `GLEICHUNGEN_VORHANDEN: <n> Gleichungen`. Baugruppen: am Baugruppendokument in `bewerte_baugruppe`; Eigenteile prüft ihre Teilprüfung; Normteil- und Kaufteildokumente nie.
8. **aenderungen:** Protokolle mit `masse` → Maßweg; ohne (alte Läufe) → globale Variablen wie bisher. Ausgabe je Datei zusätzlich `masse` (Differenzen) und `vorschlaege`.
9. **Bestehende Gleichungs-Tests:** `tests/compiler/test_kontext.py` und die Live-Tests, die Gleichungen lesen (`test_live_aenderungen`, `test_live_endbedingungen`, `test_live_extrusion`, `test_live_formschraege`), setzen `gleichungen: true` in ihrer Spec bzw. ihrem Kontext – ihr Zweck bleibt; neue Tests decken den Weg ohne Gleichungen.

## Global Constraints

- **Umfang:** `bezug` an `rechteck`, `kreis`, `langloch`, `bohrung`, `normbohrung`; Werte `ursprung` (Vorgabe), `mitte`, `"-rand"`, `"+rand"`, `{flaeche: <flaechenanker>}`. Nicht: Bezüge für `polygon`/`kontur`/`mittellinie`, Kettenmaße, `mitte` um eine andere Mitte als den Ursprung, Messen oder symbolisches Rückrechnen in `aenderungen`, Nachrüsten alter Läufe und Bibliotheksteile.
- **Gleichungen:** `config/standard.yaml` `gleichungen: false`; je Spec `gleichungen: true` (Teil und Baugruppe). Nicht in `PRUEF_FELDER`/`PRUEF_FELDER_BAUGRUPPE` (Bauweg).
- **Freigabe:** `bezug` und `gleichungen` sind Bauweg – Prüfsummen bleiben gleich, bestehende Freigaben bleiben gültig.
- **Skizzen bleiben voll bestimmt** (`SKIZZE_NICHT_BESTIMMT` unverändert); keine automatischen Beziehungen (`AddToDB`, `ohne_inferenz` wie bisher).
- **`mitte`:** immer die Mittelebene durch den Ursprung; Symmetrie legt den Partner fest, nur ein Punkt je Gruppe bekommt Lage- und Abstandsmaße (Spec §5.2).
- **Late Binding** (`swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()` (`GetEdges`, `GetCount`, `SystemValue`, `DrivenState`, `GetConstrainedStatus`, `GetEquationMgr`).
- **API nachschlagen:** vor jedem **neuen** SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` (vorher `$env:PYTHONIOENCODING='utf-8'`). `.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` ohne Befund. Bereits nachgeschlagen (2026-10-23): `IModelDoc2.AddHorizontalDimension2`/`AddVerticalDimension2`/`AddDimension2` (je 3: X, Y, Z), `IModelDoc2.SketchAddConstraints` (1; Kennungen u. a. `sgSYMMETRIC`, `sgATMIDDLE`, `sgCOLINEAR`, `sgCOINCIDENT`, `sgHORIZONTALPOINTS2D`, `sgVERTICALPOINTS2D`), `IModelDoc2.Parameter` (1), `IDimension.SystemValue` (Property), `IDimension.SetSystemValue3` (3), `IDimension.DrivenState` (Property; `swDimensionDrivenState_e`: 0 unbekannt, 1 getrieben, 2 maßgebend), `IFace2.GetEdges` (0), `ISketch.GetConstrainedStatus` (0), `IModelDoc2.EditRebuild3` (0).
- **Einheiten:** Spec und Ausgaben mm und Grad; API m und rad.
- **Python:** im Worktree `C:\Users\User\Documents\Projekte\SolidWorks-KI\.venv\Scripts\python.exe` (das `.venv` liegt im Hauptcheckout; `swki` wird aus dem Worktree importiert). `config/rechner.yaml` ist in den Worktree kopiert (nicht im Git).
- **Tests:** `python -m pytest -q` (Stand vor dem Plan: **1191 passed, 154 deselected**); jeder Task nennt im Bericht die neue Zahl. Live-Tests nur einzeln: `python tests\live_einzeln.py <datei::test-id> --zeit 900` mit `$env:PYTHONIOENCODING='utf-8'`.
- **SolidWorks (Live-Tasks):** nur Teile (Task 1, 9) bzw. die Regressions-Suite (Task 9, Controller); genau eine Instanz; bis ca. 4 GB Private Bytes, darüber BLOCKED an den Controller (`-m werkzeuge.sw_neustart` startet nur der Controller). Einstellungen vor/nach Live-Läufen `False 1` (siehe Formschräge-Plan, Global Constraints). Keine künstliche CPU-Last.
- **Nur eigene Dokumente**; speichern nur im `arbeitsordner`; kein SolidWorks-Jahr, kein Pfad fest im Code.
- **Prüfwerte nie an Messwerte anpassen.** Weicht ein Live-Ergebnis von der Annahme ab: anhalten (NEEDS_CONTEXT) mit Auszug, der Controller entscheidet nach der Tabelle „Abhängigkeiten vom Spike S17“.
- **Sprache:** Bezeichner, Docstrings, Kommentare, Commits, Berichte deutsch mit Umlauten in Texten.
- **Git:** Branch `bemassungsbezug` (Worktree `.claude/worktrees/bemassungsbezug`), ein Commit je Task, gezielt `git add <dateien>`, Trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, **kein `git push` ohne Rückfrage**, keine SolidWorks-Dateien, nichts aus `auftraege/`. Ersetzungen in bestehenden Dateien mit dem Edit-Werkzeug (CRLF).
- **Subagents:** Implementer starten keine Subagents; nie zwei Implementer gleichzeitig, solange SolidWorks läuft.

## Review Focus

1. **Bezug auf einer Achse, auf der alle Positionen 0 sind** (`bezug: {u: "-rand"}`, alle u = 0 wäre unsinnig, aber `v: mitte` mit allen v = 0 ist normal): `mitte` mit Punkten auf 0 → Ausrichtung, kein Maß, keine Symmetrie – `test_mitte_alle_auf_null_nur_ausrichtung` (Task 3).
2. **Ungerades Lochbild mit `mitte`** (drei Bohrungen bei u = −20, 0, +20): ein Paar plus ein Punkt auf der Achse, keine Überbestimmung – `test_mitte_drei_punkte_paar_und_mittelpunkt` (Task 3).
3. **Senkung einer `bohrung` mit Bezug**: Senkungsskizze bekommt denselben Bezug und dieselben Pfade (`positionen[k]`), ihre Maße stehen unter der Feature-ID der Bohrung – `test_bohrung_senkung_erbt_bezug` (Task 6).
4. **Lauf aus der Zeit vor dem Paket** (Protokoll ohne `masse`, Datei mit globalen Variablen): `swki aenderungen` liest wie bisher die globalen Variablen – `test_alter_lauf_ohne_masse_liest_globale_variablen` (Task 8).
5. **Projektvorgabe ohne Schlüssel `gleichungen`** (älteres `config/standard.yaml`): gilt als aus, Prüfpunkt `gleichungen` läuft – `test_gleichungen_an_ohne_schluessel_ist_aus` (Task 2).

## Dateistruktur nach diesem Plan

```
spikes/s17_bemassungsbezug.py           Spike S17 (live)
docs/stufe0/ergebnisse/s17_bemassungsbezug.json, docs/bemassungsbezug/ergebnisse.md
swki/bemassung.py                       neu: bezug_von, paare_mitte, massplan, rechteck_kennkoordinate, Kennpunkt, Auftrag
swki/compiler/anker.py                  + randkante
swki/compiler/eigenschaften.py          + gleichungen_an
swki/compiler/kontext.py                gleichungen, knoten, masse, pfad(), mass() statt verknuepfe()
swki/compiler/protokoll.py, ablauf.py   Knoten.masse
swki/compiler/skizze.py                 Kennpunkte, lagen_festlegen, Bezüge, Rechteck über Mitte/Seite
swki/compiler/handler/*.py              ctx.mass statt ctx.verknuepfe; bohrung/normbohrung reichen bezug weiter
swki/compiler/bauen.py, normteile/bau.py, pruefung/messen.py   Kontext.gleichungen; vorbereiten nur bei an
swki/baugruppe/bau.py, sw_baugruppe.py  globale Variablen/Gleichungen nur bei an
schema/teil.schema.json, schema/baugruppe.schema.json, config/standard.yaml
swki/spec/laden.py, swki/spec/hinweise.py   Befunde und Hinweis bezug
swki/pruefung/{messen,bewertung}.py, swki/baugruppe/bewertung.py   Prüfpunkt gleichungen
swki/aenderungen.py                     Maßweg
tests/test_bemassung.py, tests/compiler/test_randkante.py, tests/spec/test_bezug_spec.py, tests/compiler/test_massprotokoll.py,
tests/compiler/test_skizze_bezug.py, tests/pruefung/test_gleichungen_pruefung.py, tests/test_aenderungen_masse.py,
tests/live/test_live_bemassungsbezug.py
tests/referenz/motorhalter/grundplatte.yaml, tests/referenz/zentrieraufnahme/zentrieraufnahme.yaml   + bezug
.claude/skills/konstruieren/SKILL.md, .claude/skills/baugruppe/SKILL.md, CLAUDE.md, Grundspec §4
```

## Abhängigkeiten vom Spike S17 (Task 1)

Tasks 6 und 9 setzen die Spalte „Annahme“ voraus. Weicht der Spike ab, entscheidet der Controller nach „sonst“ und hält es im Ledger und in `docs/bemassungsbezug/ergebnisse.md` fest, bevor Task 6 beginnt. Schlüssel = Fälle in `docs/stufe0/ergebnisse/s17_bemassungsbezug.json`.

| # | Frage | Annahme (Plan) | sonst | betrifft |
|---|---|---|---|---|
| 1 | Punkt zu Modellkante (`1_*`) | `1_punkt_kante_hv`: `AddHorizontalDimension2` mit Punkt + Kante gewählt liefert ein Maß, `driven_state` 2, `wert_mm` 10, Status 3 | nur `1_punkt_kante_dim2` klappt: überall `AddDimension2` für Rand-/Flächenbezüge (Ledger); keiner: Kante per `sgUSEEDGE` in die Skizze übernehmen (Konstruktion) und dazu bemaßen – Nutzer informieren | 6 |
| 2 | Punkt zu Seitenfläche (`2_*`) | wie Zeile 1 mit der Seitenfläche `-x` statt der Kante | `{flaeche}`-Bezug löst auf die Kante der Skizzenfläche auf, die in dieser Seitenfläche liegt; berührt sie die Skizzenfläche nicht: `validieren`/Bau lehnen ab (Spec §3 nachziehen, Nutzer informieren) | 4, 6 |
| 3 | Rechteckseite zu Kante (`3_linie_kante`) | `AddDimension2` mit Linie + Kante: Abstand 5, maßgebend, Status 3 | Seite über ihren Endpunkt zur Kante bemaßen (Punkt-Weg aus Zeile 1) | 6 |
| 4 | Positionsskizze (`4_*`) | Rand- und Symmetriemaße wie in Zeilen 1 und 5 auch in der Positionsskizze, beide Bohrungen vorhanden; Mittellinie über Endpunkt auf der Randkante (`4_mittellinie_kante`) voll bestimmt | Endpunkt-Variante scheitert, Längenmaß (`4_mittellinie_laenge`) klappt: Mittellinie mit Längenmaß (Ledger); Symmetrie dort gar nicht: Paare in Positionsskizzen je Punkt zur Mittelebene bemaßen (Abweichung von Spec §5.2, Nutzer informieren) | 6 |
| 5 | Symmetrie und Rechteck über Mitte (`5_*`) | `sgSYMMETRIC` (Punkt, Punkt, Mittellinie) + Abstandsmaß: Status 3, `beziehungen_neu` nur die gesetzten; Rechteck über Konstruktionsdiagonale + `sgATMIDDLE` (`5_rechteck_diagonale`) Status 3 | Diagonale scheitert: Mittelpunkt + Symmetrie gegenüberliegender Ecken (`5_rechteck_symmetrie`) (Ledger) | 6 |
| 6 | Handtest (`6_*`) | Breite 100 → 90: Bohrungsachse bei x = 30,00 ± 0,01 (10 mm vom rechten Rand), `rebuild_fehler` leer – ohne Fase, mit Fase an der Bezugskante, und für den Bohrungsassistenten | mit Fase gebrochen: Skill-Regel „Bezug an gefasten/verrundeten Kanten über die Seitenfläche (`{flaeche}`)“, Fall 2 muss dann tragen – Nutzer fragen | 6, 9, Skill |
| 7 | Lesen (`7_lesen`) | `Parameter("<maß>@<skizze>").SystemValue` nach Öffnen liefert den Wert in m | anderen Weg nachschlagen (`GetSystemValue3`), Task 8 anpassen (Ledger) | 8 |

---

### Task 1: Spike S17 – Bemaßen zu Kante, Fläche, symmetrisch; Handtest (live)

**Files:**
- Create: `spikes/s17_bemassungsbezug.py`
- Create: `docs/stufe0/ergebnisse/s17_bemassungsbezug.json` (schreibt `spikes._gemeinsam.lauf`)
- Create: `docs/bemassungsbezug/ergebnisse.md`

**Interfaces:**
- Consumes: `spikes._gemeinsam.lauf`, `spikes.s9a_gemeinsam.feature_masse`, `swki.compiler.ablauf.baue_features`, `swki.compiler.kontext.Kontext`, `swki.compiler.skizze.Skizzierer`/`ebene_aus_flaeche`, `swki.compiler.topologie.loese_flaeche`/`kante_aus`/`flaechen`, `swki.compiler.handler.normbohrung` (Modulattribut `positionen_festlegen` wird für Fall 4 und 6c im Spike ersetzt), `swki.pruefung.messen.oeffne`/`rebuild_fehler`.
- Produces: Ergebnis-JSON mit den Schlüsseln der Tabelle oben; je Fall `{"fehler", "aufruf", "mass", "wert_mm", "driven_state", "status", "beziehungen_neu", ...}`.

Aufbau wie `spikes/s16_formschraege.py` (`_sicher` je Fall, ein Teil je Fall, immer schließen). Block 100 × 60 × 20 auf Ebene oben über den Compiler (nur Zahlen, also ohne Gleichungen); Deckfläche y = 20, Skizze auf `{feature: f1, flaeche: "+y"}`: u = X, v = −Z; linke Kante u = −50, rechte u = +50.

- [ ] **Step 1: Nachschlagen** – jeden API-Aufruf des Spikes, der in den Global Constraints nicht steht, über `swki api methode` prüfen; Ergebnis als Kommentarzeile im Spike.
- [ ] **Step 2: Fälle schreiben** (`pruefen() -> dict`):
  - `1_punkt_kante_hv`: Punkt (−40, 10); Punkt + linke Kante (aus `GetEdges` der Deckfläche, Linie parallel zu Z bei x = −50) → `AddHorizontalDimension2`; v-Lage zum Ursprung → Status. `1_punkt_kante_dim2`: dasselbe mit `AddDimension2`.
  - `2_punkt_flaeche_hv` / `2_punkt_flaeche_dim2`: wie 1, gewählt die Seitenfläche `-x` von f1.
  - `3_linie_kante`: Rechteck 20 × 10, linke Seite bei u = −45; linke Seite + linke Kante → `AddDimension2` (Soll 5); übrige Maße → Status.
  - `4_mittellinie_kante` / `4_mittellinie_laenge`: Normbohrung M6, Positionen (−40, ±20) über den Handler, `positionen_festlegen` ersetzt: zweiter Punkt, Mittellinie entlang u durch den Ursprung (Anfang deckungsgleich Ursprung, waagrecht; Ende deckungsgleich mit der linken Kante bzw. Längenmaß 50), `sgSYMMETRIC`, Abstandsmaß 40, Punkt 1 zur linken Kante 10; danach Neuaufbau wie `_neu_aufbauen_bis_vollstaendig`. Erfassen: Status, Zahl der Bohrungen, Maße.
  - `5_symmetrie_kreise`: Kreise Ø8 bei (±30, 0), Mittellinie entlang v, `sgSYMMETRIC`, Abstand 60, Ausrichtung v. `5_rechteck_diagonale`: Rechteck 40 × 20 um (0, 0), Konstruktionsdiagonale, `sgATMIDDLE` Ursprung–Diagonale. `5_rechteck_symmetrie`: Rechteck 40 × 20 um (20, 10), Mittelpunkt als Skizzenpunkt mittig der Diagonale, Lage 20/10 zum Ursprung. Je Fall `beziehungen_neu` = Beziehungen nach − vor dem Fall (`RelationManager.GetRelations(0)`).
  - `6a_handtest`, `6b_handtest_fase`, `6c_handtest_normbohrung`: Kreis Ø8 bei (40, 0) 10 mm zur rechten Kante (Weg nach Zeile 1), Schnitt durch alles; 6b zusätzlich Fase 1 mm an der rechten Deckkante nach dem Schnitt; 6c Normbohrung M6 mit Positionen (40, ±20), Rand + Symmetrie. Dann Breitenmaß von f1 (`feature_masse`) per `Parameter(name).SetSystemValue3(0.09, 1, None)` auf 90, `EditRebuild3`, Bohrungsachse(n) aus der Zylinderfläche messen; Soll x = 30. Erfassen: `x_ist`, `rebuild_fehler`, Status.
  - `7_lesen`: 6a vor der Änderung im `arbeitsordner/S17/` speichern, schließen, `oeffne`, `Parameter("<randmaß>@<skizze>").SystemValue` (Soll 0,010) und Breite (0,100).
- [ ] **Step 3: Ausführen** – `python -m spikes.s17_bemassungsbezug` (SolidWorks offen, ≤ 4 GB). Erwartet: JSON geschrieben, kein `fehler_fall`.
- [ ] **Step 4: Auswerten** – `docs/bemassungsbezug/ergebnisse.md` „## 1. Spike S17 (SOLIDWORKS 2025, Rechner A, <Datum>)“: je Zeile der Abhängigkeitstabelle Annahme bestätigt/abweichend mit Wert. Abweichung → NEEDS_CONTEXT an den Controller.
- [ ] **Step 5: `python -m swki api pruefe-code spikes`** ohne Befund; Commit `Spike S17: Bemaßungsbezug (Kante, Fläche, Symmetrie, Handtest)`.

### Task 2: Schalter `gleichungen` (ohne SolidWorks)

**Files:**
- Modify: `config/standard.yaml` (+ `gleichungen: false  # Spec Bemaßungsbezug §4: keine globalen Variablen/Gleichungen; je Spec gleichungen: true`)
- Modify: `schema/teil.schema.json`, `schema/baugruppe.schema.json` (Top-Level `"gleichungen": {"type": "boolean"}`)
- Modify: `swki/compiler/eigenschaften.py`, `swki/compiler/kontext.py`, `swki/compiler/bauen.py`, `swki/normteile/bau.py`, `swki/pruefung/messen.py`, `swki/baugruppe/bau.py`, `swki/baugruppe/sw_baugruppe.py`
- Test: `tests/compiler/test_eigenschaften.py`, `tests/compiler/test_kontext.py`, `tests/baugruppe/test_referenzen.py`, `tests/spec/test_freigabe.py`

**Interfaces:**
- Produces: `gleichungen_an(spec: dict, standard: dict) -> bool`; `Kontext.gleichungen: bool = False`; `vorbereiten(app, model, spec, auftrag, gleichungen: bool)`; `sw_baugruppe.verknuepfe(..., gleichungen: bool = False)` (neuer letzter Parameter).

- [ ] **Step 1: Tests schreiben**
  - `test_gleichungen_an_spec_vor_standard`: `gleichungen_an({"gleichungen": True}, {"gleichungen": False}) is True`; `gleichungen_an({}, {"gleichungen": True}) is True`; `gleichungen_an({"gleichungen": False}, {"gleichungen": True}) is False`.
  - `test_gleichungen_an_ohne_schluessel_ist_aus`: `gleichungen_an({}, {}) is False`.
  - `test_kontext.py`: bestehende Tests setzen `gleichungen=True` (Präzisierung 9); neu `test_verknuepfe_ohne_gleichungen_legt_nichts_an` – Kontext mit `gleichungen=False`, Aufruf mit `"=L"` → `GetEquationMgr.texte == []` (in Task 5 auf `ctx.mass` umbenannt).
  - `test_vorbereiten_ohne_gleichungen_keine_globalen_variablen` (monkeypatch `globale_variablen` zählt Aufrufe → 0; mit `True` → 1).
  - Baugruppe: `verknuepfe` mit Ausdruck und `gleichungen=False` → keine `Add2`-Aufrufe (Muster `tests/baugruppe/test_referenzen.py:215`).
  - `test_gleichungen_aendert_pruefsumme_nicht`: `pruefsumme(spec) == pruefsumme(spec | {"gleichungen": True})` für Teil und Baugruppe.
- [ ] **Step 2: RED** – `python -m pytest -q tests/compiler tests/baugruppe tests/spec` → die neuen Tests scheitern.
- [ ] **Step 3: Umsetzen** – `vorbereiten` ruft `globale_variablen` nur bei `gleichungen`; `Kontext.verknuepfe` kehrt ohne `gleichungen` vor dem Gleichungsmanager zurück; `bau.py` ruft `globale_variablen` der Baugruppe nur bei `gleichungen_an(bg.spec, standard)` und reicht das Flag an `sw_baugruppe.verknuepfe`; Teile einer Baugruppe nehmen `gleichungen_an(teil_spec, standard)`.
- [ ] **Step 4: GREEN** – ganze Suite grün.
- [ ] **Step 5: Commit** `Gleichungen standardmäßig aus (Schalter gleichungen)`.

### Task 3: Reine Rechnung `swki/bemassung.py` und `randkante` (ohne SolidWorks)

**Files:**
- Create: `swki/bemassung.py`
- Modify: `swki/compiler/anker.py`
- Test: `tests/test_bemassung.py`, `tests/compiler/test_randkante.py`

**Interfaces:**
- Produces:
  - `bezug_von(obj: dict) -> dict[int, str | dict]` – `{0: wert_u, 1: wert_v}`, fehlende Achse = `"ursprung"`; Werte unverändert aus der Spec (`"mitte"`, `"-rand"`, `{"flaeche": …}`).
  - `@dataclass Kennpunkt: uv: tuple[float, float]; achsen: tuple[int, ...] = (0, 1); bezug: dict[int, str | dict] = <alle ursprung>; pfad: str = ""; roh: tuple = (None, None); gruppe: str = ""` – `gruppe` = Art und Größe des Elements (Paare nur innerhalb gleicher Gruppe; Positionen einer Liste haben dieselbe).
  - `@dataclass Auftrag: art: str; punkt: int; achse: int; partner: int | None = None; bezug: str | dict | None = None; wert: float | None = None` – `art` ∈ `ursprung` (Maß zum Ursprung), `ausrichtung` (Koordinate 0), `deckung` (Punkt im Ursprung, beide Achsen), `symmetrie` (punkt, partner, Mittellinie entlang der anderen Achse), `paarabstand` (punkt, partner, wert = Abstand), `bezug` (Rand/Fläche, wert = Abstand, bezug = Spec-Wert).
  - `paare_mitte(punkte: list[Kennpunkt], achse: int, tol: float) -> list[tuple[int, int]]`
  - `massplan(punkte: list[Kennpunkt], bezugslage: Callable[[int, int], float], tol: float) -> list[Auftrag]` – `bezugslage(punkt, achse)` liefert für Rand-/Flächenbezüge die Koordinate des Bezugs auf der Achse (der Compiler übergibt die gemessene Kantenlage).
  - `rechteck_kennkoordinate(mitte: float, groesse: float, bezug: str | dict, bezugslage: float | None) -> float` – Koordinate (Mitte oder Seite) des bemaßten Kennpunkts auf einer Achse (Spec §3).
  - `anker.randkante(kanten: list[Kante], achse_modell: Vektor, vorzeichen: int, punkt: Vektor, tol_mm: float) -> Kante`

Paar (`paare_mitte`): beide Punkte mit `mitte` auf Achse a, gleiche `gruppe`, Koordinate auf a entgegengesetzt gleich und ≠ 0 (|c| > tol), auf der anderen Achse gleich (± tol).

`massplan` (Spec §5.2, ohne Überbestimmung) – eine Symmetrie legt den Partner vollständig fest, das Abstandsmaß ersetzt die Lage des festlegenden Punkts:

```
kanten = [(i, j, a) für a in (0, 1) für (i, j) in paare_mitte(punkte, a, tol)]
Komponenten der Punkte über kanten; je Komponente Wurzel = kleinster Index;
Breitensuche ab der Wurzel (Kanten in der Reihenfolge von kanten): jede Baumkante (eltern, kind, a)
    → symmetrie(eltern, kind, a); kind ist bestimmt. Nicht-Baumkanten entfallen (gelten geometrisch).
Für jede Wurzel w und Achse a in punkte[w].achsen:
    hat w eine Baumkante (w, k, a) → paarabstand(w, k, a, wert=|u_w − u_k|) (erste solche Kante)
    sonst Bezug Rand/Fläche → bezug(w, a, wert=|u_w − bezugslage(w, a)|)
    sonst Koordinate 0 → ausrichtung, sonst ursprung (wert=|u_w|)
    Sonderfall: w auf beiden Achsen 0 ohne Paar und ohne Rand/Fläche → eine deckung statt zweier Ausrichtungen.
Bestimmte Punkte bekommen keine weiteren Aufträge.
```

- [ ] **Step 1: Tests schreiben** (`tests/test_bemassung.py`):
  - `test_bezug_von_vorgabe_ursprung`: `bezug_von({}) == {0: "ursprung", 1: "ursprung"}`; `bezug_von({"bezug": {"u": "-rand"}}) == {0: "-rand", 1: "ursprung"}`.
  - `test_mitte_zwei_bohrungen_rand_und_symmetrie` (Spec §3): Punkte (−70, 20), (−70, −20), Bezug `{0: "-rand", 1: "mitte"}`, Bezugslage u = −80 → Aufträge genau `[symmetrie(0, 1, 1), paarabstand(0, 1, 1, wert=40), bezug(0, 0, "-rand", wert=10)]` (Reihenfolge egal).
  - `test_mitte_2x2_ohne_ueberbestimmung`: Punkte (30, 20), (−30, 20), (30, −20), (−30, −20), beide Achsen `mitte` → genau 5 Aufträge: 3 Symmetrien (Baum ab Punkt 0), `paarabstand(0, 1, 0, 60)`, `paarabstand(0, 2, 1, 40)`; keine Lageaufträge.
  - `test_mitte_drei_punkte_paar_und_mittelpunkt`: u = −20, 0, 20 bei v = 5, `mitte` auf u, `ursprung` auf v → Paar (0, 2): Symmetrie + Abstand 40; Punkt 1: `ausrichtung` auf u; v: Punkt 0 und 1 je `ursprung` (wert 5), Punkt 2 nichts.
  - `test_mitte_alle_auf_null_nur_ausrichtung`: zwei Punkte (−10, 0), (10, 0), `mitte` auf beiden Achsen → auf v keine Symmetrie, nur `ausrichtung` für den Paar-Ersten.
  - `test_paare_nur_in_gleicher_gruppe`: Kreis Ø8 bei (−30, 0) und Kreis Ø10 bei (30, 0) → kein Paar.
  - `test_ursprung_beide_null_ist_deckung`.
  - `test_rechteck_kennkoordinate`: Mitte 0, 100, `mitte` → 0; Mitte 50, 100, `ursprung` → 0 (linke Seite auf 0); Mitte 0, 100, `ursprung` → 0 (Mitte); Mitte −60, 20, `"-rand"`, Lage −80 → −70; Mitte −60, 20, `"+rand"`, Lage 80 → −50.
  - `tests/compiler/test_randkante.py`: Deckfläche 100 × 60 (vier Linienkanten) → `randkante(..., (1, 0, 0), -1, punkt)` = Kante bei x = −50; unterbrochener Rand (zwei Kanten bei x = −50, z ∈ [−30, −5] und [5, 30]) → die zur Punkt-z nächste; Gleichstand → `AnkerFehler` mit „mehrdeutig“; keine Kante parallel → `AnkerFehler`.
- [ ] **Step 2: RED**, **Step 3: Umsetzen**, **Step 4: GREEN** (`python -m pytest -q tests/test_bemassung.py tests/compiler/test_randkante.py`, dann ganze Suite).
- [ ] **Step 5: Commit** `Bemaßungsbezug: reine Rechnung (Maßplan, Paare, Randkante)`.

### Task 4: Schema, `validieren` und Hinweis `bezug` (ohne SolidWorks)

**Files:**
- Modify: `schema/teil.schema.json` (`$defs.bezug`, an `rechteck`, `kreis`, `langloch`, `f_bohrung`, `f_normbohrung`)
- Modify: `swki/spec/laden.py` (`_bezug_befunde`), `swki/spec/hinweise.py` (`bezug_hinweise`, in `hinweise()` nach `feste_masse`)
- Test: `tests/spec/test_bezug_spec.py`

**Interfaces:**
- Consumes: `bemassung.bezug_von`.
- Produces: Hinweis `{"art": "bezug", "pfad", "meldung"}`; Befunde wie bisher `{"pfad", "meldung"}`.

`$defs.bezug`: Objekt mit `u`/`v` (mind. eins, sonst nichts), Wert `oneOf` `enum ["ursprung", "mitte", "-rand", "+rand"]` oder `{"flaeche": flaechenanker}`.

- [ ] **Step 1: Tests schreiben**
  - `test_schema_akzeptiert_bezug` für alle fünf Stellen; `test_schema_lehnt_bezug_an_polygon_ab`; `test_schema_lehnt_unbekannten_wert_ab` (`"links"`).
  - `test_rand_auf_standardebene_ist_befund`: Kreis in Skizze auf `oben` mit `bezug: {u: "-rand"}` → Befund am Pfad `features[0].skizze.elemente[0].kreis.bezug.u`, Meldung enthält „nur in Skizzen auf Flächen“. Auf `versatz`-Ebene ebenso; `{flaeche}` auf Standardebene erlaubt.
  - `test_bezug_flaeche_verweis_auf_spaeteres_feature_ist_befund` (über `_referenzen`).
  - `test_hinweis_bezug_bei_positionen_ohne_bezug`: Normbohrung mit Positionen (−70, ±20) ohne `bezug` → zwei Hinweise (`…positionen` u und v); mit `bezug: {u: "-rand", v: mitte}` → keiner; Positionen alle v = 0 ohne v-Bezug → nur u.
  - `test_hinweis_bezug_element_auf_flaeche`: Kreis auf `{feature: f1, flaeche: "+y"}` bei (20, 0) ohne Bezug → ein Hinweis (u); dasselbe auf Standardebene → keiner; `polygon` auf Fläche → keiner.
  - `test_bezug_ist_keine_feste_zahl` und `test_huellquader_auto_unveraendert_mit_bezug`.
- [ ] **Step 2: RED**, **Step 3: Umsetzen** (Meldung des Hinweises: „Lage ohne Bemaßungsbezug auf Achse u: bezug angeben (mitte oder rand), sonst wird zum Ursprung bemaßt“), **Step 4: GREEN**.
- [ ] **Step 5: Commit** `Bemaßungsbezug: Schema, validieren, Hinweis bezug`.

### Task 5: Maßprotokoll – `ctx.mass` statt `ctx.verknuepfe` (ohne SolidWorks)

**Files:**
- Modify: `swki/compiler/kontext.py`, `swki/compiler/ablauf.py`, `swki/compiler/protokoll.py`
- Modify: alle Aufrufer von `ctx.verknuepfe` (`skizze.py` 3×, `handler/bohrung.py`, `kanten.py` 3×, `extrusion.py` 3×, `muster.py` 3×, `referenz.py`, `rotation.py`, `verzahnung.py`)
- Test: `tests/compiler/test_massprotokoll.py`, `tests/compiler/test_kontext.py`

**Interfaces:**
- Produces: `Kontext.mass(masname, roh, pfad, art, vorzeichen=1, bezug=None) -> None`; `Kontext.pfad(fid: str) -> str`; `Kontext.knoten: str | None`; `Kontext.masse: dict[str, list[dict]]`; `Knoten.masse`.
- Pfade der Handler (Spec-Pfad unter `ctx.pfad(fid)`): Extrusion `…ende.tiefe`/`…ende.abstand`/`…ende.formschraege.winkel`; Bohrung `…tiefe`, Senkung `…senkung.tiefe`; Kanten `…radius`, `…abstand`, `…winkel`; Muster `…richtung1.abstand`, `…richtung2.abstand`, `…winkel`; Referenz `…ebene.abstand`; Rotation `…winkel`; Verzahnung `…breite`; versetzte Skizzenebene `…skizze.ebene.versatz.abstand`; Skizzenmaße `<pfad des Elements>.<feld>` (`breite`, `hoehe`, `durchmesser`, `laenge`, `radius`, `radien[k]`, `winkel`) bzw. für Lagen `<pfad des Elements>.mitte[a]` / `…punkte[k][a]` / `positionen[k][a]`.

- [ ] **Step 1: Tests schreiben**
  - `test_mass_traegt_ein_ohne_gleichung`: `ctx.knoten = "f2"`, `ctx.mass("D1@f2", "=T", "features[1].ende.tiefe", "tiefe")` mit `T = 8` → `ctx.masse["f2"] == [{"name": "D1@f2", "pfad": "features[1].ende.tiefe", "art": "tiefe", "bezug": None, "roh": "=T", "vorzeichen": 1, "wert": 8.0}]`, keine Gleichung.
  - `test_mass_mit_gleichungen_bindet_ausdruck` (wie bisheriger Kontext-Test, `gleichungen=True`); `test_mass_mit_bezug_rand_bindet_nie`.
  - `test_baue_features_schreibt_masse_in_knoten` (Fake-Handler ruft `ctx.mass`, Protokoll-Knoten hat `masse`; zweiter Knoten ohne Maße → `None`).
  - `test_protokoll_json_enthaelt_masse` (Serialisierung).
- [ ] **Step 2: RED**, **Step 3: Umsetzen** (`verknuepfe` entfällt; `swki api pruefe-code swki` bleibt ohne Befund), **Step 4: GREEN** (ganze Suite – bestehende Handler-Tests mit Fakes ggf. um `masse`/`knoten` ergänzen, nicht abschwächen).
- [ ] **Step 5: Commit** `Maßprotokoll im Bauprotokoll (ctx.mass)`.

### Task 6: Skizzierer mit Bezügen (ohne SolidWorks geprüft, live in Task 9)

Vor Beginn: Ledger-Entscheidungen zu Tabelle Zeilen 1–6 lesen.

**Files:**
- Modify: `swki/compiler/skizze.py`, `swki/compiler/handler/bohrung.py`, `swki/compiler/handler/normbohrung.py`, `swki/compiler/handler/extrusion.py`, `swki/compiler/handler/rotation.py` (Aufruf `skizziere` mit `pfade`)
- Test: `tests/compiler/test_skizze_bezug.py`

**Interfaces:**
- Consumes: `bemassung.massplan`, `bemassung.rechteck_kennkoordinate`, `bemassung.Kennpunkt`/`Auftrag`, `anker.randkante`, `topologie.kante_aus`/`loese_flaeche`, `ctx.mass`.
- Produces: `Skizzierer.kennpunkt(punkt_uv, roh_uv, bezug, pfad, gruppe, achsen=(0, 1))`, `Skizzierer.lagen_festlegen() -> None`, `skizziere(ctx, ebene, elemente, name, pfade)`, `positionen_festlegen(ctx, feature, se, positionen, name, bezug, pfad)`.

Umsetzung: `Skizzierer.lage` entfällt zugunsten von `kennpunkt` + `lagen_festlegen`; `lagen_festlegen` ruft `massplan` (Bezugslage aus `randkante` auf den Kanten der Skizzenfläche bzw. aus der Fläche des `{flaeche}`-Ankers) und setzt je `Auftrag` die Beziehung bzw. das Maß nach dem Weg aus dem Spike (Ledger), jedes Maß über `ctx.mass(..., art="lage", bezug=<Spec-Wert>)`. Mittellinien für Symmetrien: eine je Achse und Skizze (nach Spike Zeile 4). Rechteck: Kennpunkt je Achse nach `rechteck_kennkoordinate` – bei `mitte`/Mitte auf 0 der Diagonalen-Mittelpunkt (Spike Zeile 5), sonst die Seite (Spike Zeile 3). `_halb_weg` entfällt. `self.lage_bindbar` bleibt für `ursprung`-Lagen (ohne Gleichung bedeutungslos, mit Gleichung wie bisher). `bohrung` übergibt `f.get("bezug")` an Kreise und Senkungskreise, Pfade `features[i].positionen[k]`; `normbohrung` an `positionen_festlegen`.

- [ ] **Step 1: Tests schreiben** (Fake-Skizzierer-Umgebung wie `tests/compiler/test_normbohrung.py`: Modell-Fake zeichnet Aufrufe `SketchAddConstraints`, `AddHorizontalDimension2`, … mit gewählten Objekten auf):
  - `test_rechteck_um_ursprung_ueber_mitte`: Rechteck 100 × 60 um (0, 0) → Diagonale + Mittelpunkt-Beziehung zum Ursprung, Maße nur Breite und Höhe, keine Lage-Maße.
  - `test_kreise_mitte_paar_ueber_elemente`: zwei Kreise Ø8 bei (±30, 0) mit `bezug: {u: mitte}` in einer Skizze → eine `sgSYMMETRIC`, ein Abstandsmaß 60, Protokoll-Maß mit `pfad` des ersten Elements.
  - `test_bohrung_rand_maß_zur_kante`: Positionen (−40, 0) mit `bezug: {u: "-rand"}` → ausgewählt sind Punkt und die Kante bei x = −50, Maß 10 im Protokoll (`art: "lage"`, `bezug: "-rand"`, `pfad: "features[1].positionen[0][0]"`).
  - `test_bohrung_senkung_erbt_bezug`: Senkungsskizze erzeugt dieselben Lageaufträge, Maße stehen unter der Feature-ID der Bohrung.
  - `test_kontur_bleibt_koordinatenmass`: Polygon → nur `ursprung`-Maße/Ausrichtungen wie bisher.
- [ ] **Step 2: RED**, **Step 3: Umsetzen**, **Step 4: GREEN** (ganze Suite; `pruefe-code swki` ohne Befund).
- [ ] **Step 5: Commit** `Skizzierer bemaßt zu Bezügen (mitte, rand, flaeche)`.

### Task 7: Prüfpunkt `gleichungen` (ohne SolidWorks)

**Files:**
- Modify: `swki/pruefung/messen.py` (`gleichungen_anzahl(model) -> int`, Feld in `messe`), `swki/pruefung/bewertung.py` (`Messwerte.gleichungen: int = 0`, Eintrag in `bewerte`), `swki/baugruppe/bewertung.py` (Baugruppendokument; Messwert dort ergänzen, wo die Baugruppen-Messwerte gelesen werden)
- Test: `tests/pruefung/test_gleichungen_pruefung.py`

**Interfaces:**
- Consumes: `gleichungen_an`.
- Produces: Prüfpunkt `gleichungen` (`eintrag("gleichungen", ok, ist=<anzahl>)`), Mangeltext `GLEICHUNGEN_VORHANDEN: <n> Gleichungen`.

- [ ] **Step 1: Tests schreiben** – `test_ohne_gleichungen_ok` (0, aus → ok), `test_gleichungen_vorhanden_ist_mangel` (3, aus → nicht ok, Text wie oben), `test_mit_gleichungen_an_kein_pruefpunkt`, `test_baugruppe_prueft_nur_baugruppendokument` (Normteil-Komponente mit globalen Variablen erzeugt keinen Mangel).
- [ ] **Step 2: RED**, **Step 3: Umsetzen**, **Step 4: GREEN**.
- [ ] **Step 5: Commit** `Prüfung: keine Gleichungen im Modell (GLEICHUNGEN_VORHANDEN)`.

### Task 8: `swki aenderungen` über Maße (ohne SolidWorks)

**Files:**
- Modify: `swki/aenderungen.py`
- Test: `tests/test_aenderungen_masse.py` (bestehende `tests/test_aenderungen.py` bleibt grün)

**Interfaces:**
- Consumes: Protokoll-Knoten `masse` (Task 5); Spike Zeile 7.
- Produces:
  - `soll_masse(protokoll: dict, spec_pfad: Path, auftrag: str, standard: dict) -> dict[str, list[dict]]` – Dateiname im Lauf → Maßliste (Teil: alle Knoten; Baugruppe: je Teil aus `protokoll["teile"]`).
  - `lies_masse(model, masse: list[dict]) -> dict[str, float]` – Name → Wert in mm bzw. Grad (`art == "winkel"` → Grad).
  - `mass_differenz(masse: list[dict], ist: dict[str, float]) -> list[dict]` – `{name, pfad, art, bezug, roh, soll, ist, delta}` für |ist − soll| > 1e-6.
  - `vorschlaege(differenz: list[dict], parameter: dict) -> list[dict]` – `{"parameter": P, "neu": w}` wenn `roh` genau `=P` bzw. `=-P` (Wert/negiert) und `art != "lage"`; bei Lage mit Bezug `{"pfad", "bezug", "delta"}`; widersprüchliche Werte für denselben Parameter → `{"parameter": P, "konflikt": [w1, w2]}`.

- [ ] **Step 1: Tests schreiben**
  - `test_mass_differenz_meldet_nur_geaenderte`.
  - `test_vorschlag_direkter_parameter`: Größenmaß `roh "=L"`, soll 100, ist 90 → `{"parameter": "L", "neu": 90.0}`.
  - `test_lage_nie_als_parametervorschlag`: Lagemaß `roh "=-XG"` ohne Bezug, 10 → 12 → `{"pfad": …, "bezug": None, "delta": 2.0}`, kein Parametervorschlag.
  - `test_vorschlag_lage_mit_bezug_delta`: Randmaß 10 → 12 → `{"pfad": "features[1].positionen[0][0]", "bezug": "-rand", "delta": 2.0}`.
  - `test_konflikt_zwei_masse_ein_parameter`: zwei Maße `=B` mit 60 → 65 und 60 → 70 → Konflikt `[65.0, 70.0]`.
  - `test_alter_lauf_ohne_masse_liest_globale_variablen` (monkeypatch `lies_globale_variablen`, Protokoll ohne `masse`).
  - `test_aenderungen_ausgabe_mit_masse_und_vorschlaegen` (monkeypatch `oeffne`/`verbinde`/`lies_masse`).
- [ ] **Step 2: RED**, **Step 3: Umsetzen**, **Step 4: GREEN**.
- [ ] **Step 5: Commit** `swki aenderungen liest Maße statt globaler Variablen`.

### Task 9: Live-Tests, Referenzen, Regression (live)

**Files:**
- Create: `tests/live/test_live_bemassungsbezug.py`
- Modify: `tests/live/test_live_aenderungen.py`, `test_live_endbedingungen.py`, `test_live_extrusion.py`, `test_live_formschraege.py` (`gleichungen: true`, Präzisierung 9)
- Modify: `tests/referenz/motorhalter/grundplatte.yaml` (`bezug: {u: mitte, v: mitte}` an `f2`, Positionen unverändert), `tests/referenz/zentrieraufnahme/zentrieraufnahme.yaml` (Bezüge an Zapfen, Tasche, Trichter nach dem Stil der Spec §2; Koordinaten als Ausdruck des Bezugs nur, wo das die Werte nicht ändert)

**Interfaces:**
- Consumes: alles aus Tasks 2–8.

- [ ] **Step 1: Live-Tests schreiben** (`pytestmark = pytest.mark.sw`, Teile wie in `test_live_aenderungen.py` über `swki freigeben`/`bauen` in `tmp_path`):
  - `test_platte_mit_bezuegen_ohne_gleichungen`: Platte L 160 × B 100 × H 12 um den Ursprung, Normbohrung M6 bei (`=-L/2+RA`, `=±ZG`) mit `bezug: {u: "-rand", v: mitte}`, RA 10, ZG 20 → `GetEquationMgr.GetCount == 0`, alle Skizzen Status 3, Positionsskizze enthält Maße 10 und 40 (Werte über `feature_masse`), `swki pruefen` ohne Mangel.
  - `test_handaenderung_erhaelt_randabstand`: dieselbe Platte gebaut, Breitenmaß per `Parameter(...).SetSystemValue3` auf 150, speichern; Bohrungsachsen bei x = −65,00 ± 0,01; `swki aenderungen` meldet `L`-Vorschlag 150 und keine Lagedifferenz.
  - `test_handaenderung_randmass_ergibt_delta`: Randmaß 10 → 12 → `aenderungen` liefert Delta 2 am Pfad `features[1].positionen[0][0]`.
- [ ] **Step 2: Einzeln ausführen** – jeden Test mit `tests\live_einzeln.py … --zeit 900`; erwartet PASS. Abweichung → NEEDS_CONTEXT.
- [ ] **Step 3: Referenzen** – `swki validieren` beider geänderten Specs ohne Befund und ohne Hinweis `bezug`; Freigaben bleiben gültig (`swki status`).
- [ ] **Step 4: Regression (Controller, frisches SolidWorks je Baugruppe)** – `python tests\live_einzeln.py tests\referenz`; alle bestehen. Speicherspitzen wie in CLAUDE.md.
- [ ] **Step 5: Commit** `Live-Tests und Referenzen Bemaßungsbezug`.

### Task 10: Skills, CLAUDE.md, Grundspec, Ergebnisse

**Files:**
- Modify: `.claude/skills/konstruieren/SKILL.md` (Zeilen 24–25 und Abschnitt Freigabe-Vorlage: Regeln nach Spec §9, Bemaßungsstil des Nutzers, Bezüge in Worten in der Feature-Liste, Rückführung von Deltas aus `aenderungen` mit Nutzer-OK)
- Modify: `.claude/skills/baugruppe/SKILL.md` (Verknüpfungswerte ohne Gleichung als Zahl; `gleichungen: true` nur auf Wunsch des Nutzers)
- Modify: `CLAUDE.md` (Stand-Zeile; Abschnitt „Konstruieren“: `bezug`, Gleichungen standardmäßig aus)
- Modify: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` (§4: Kommentar `# werden SW-Gleichungen` und Regel „Parameter werden zu SW-Gleichungen“ auf Verweis auf diese Spec ändern)
- Modify: `docs/bemassungsbezug/ergebnisse.md` (§2 Live-Tests, §3 Regression mit Laufzeiten/Speicher)

- [ ] **Step 1: Texte ändern** (Skill-Regeln knapp im Stil der bestehenden; `writing-for-agents` beachten).
- [ ] **Step 2: `python -m pytest -q`** grün; `python -m swki api pruefe-code swki spikes tests/live` ohne Befund.
- [ ] **Step 3: Commit** `Doku Bemaßungsbezug: Skills, CLAUDE.md, Ergebnisse`.
