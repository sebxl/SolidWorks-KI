# Paket Bestandsdateien, Etappe 1 (Einzelteile) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** swki ändert fremde `.sldprt`-Dateien gezielt an einer Arbeitskopie: `swki bestand aufnehmen`, Änderungs-Spec `art: aenderung`, eine Freigabe, Bau ab unveränderter Kopie, Vorher/nachher-Prüfung mit Bereichen, Prüfer, `swki bestand ausgabe`.

**Architecture:** Spike S18 klärt zuerst live die offenen API-Wege und erzeugt die Musterdateien (auch S18b/g für Baugruppen, damit Etappe 1 nichts verbaut). Danach entsteht das Paket `swki/bestand/` von innen nach außen: Ablage und Fehlercodes, Schema und Validierung gegen die Aufnahme `bestand.json`, Aufnahme in SolidWorks, Punkte und Bau, Vergleich zweier Aufnahmen, Körper-Differenz mit Bereichen, Weichen `pruefen`/`status`/`bericht`/`durchlauf`, `ausgabe`, Referenz. **Eine Funktion liest Bestand und Lauf** (`lies_bestand`), sodass §7.1 der Spec reine Logik über zwei Dicts ist.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, numpy/trimesh (nur Rückfall STL), pytest; SOLIDWORKS 2025 (Rechner A) für Spike und Live-Tests.

**Spec:** `docs/superpowers/specs/2026-10-25-bestandsdateien-design.md` (vom Nutzer abgenommen, 2026-10-30). Kontext: Gesamtdesign §5/§6, Spec 3c (Kopie mit SHA-256, Messpunkte), Bemaßungsbezug (Maßprotokoll, Bezüge), Spec 3b §8 (Änderungserkennung). Etappe 2 (Baugruppen, Spec §8) bekommt nach Etappe 1 einen eigenen Plan.

## Voraussetzung vor Task 1

Erledigt am 2026-10-31: Der Branch ist mit origin/main ab61b21 abgeglichen (Merge 75a3995). Der Plan wurde gegen b2401c9 geschrieben; #22 (C2, `swki optimiere`) ändert `swki/spec/befehle.py`, `swki/spec/freigabe.py`, `swki/spec/laden.py` und `swki/compiler/bauen.py` nur an anderen Stellen. Zwei Folgen: Die Weiche `aenderung` in `_freigeben` steht hinter dem Zweig `--im-raum`, und `_bauen` liest `hochstufen` mit `getattr(args, "hochstufen", False)`, weil `swki durchlauf` ein eigenes `Namespace` ohne dieses Feld übergibt.

## Präzisierungen gegenüber der Spec (vom Planer, bindend für diesen Plan)

1. **Verknüpfte Maße (gemeinsamer Wert) sind treibend, nicht gesteuert.** SolidWorks kennt kein führendes Maß einer Verknüpfung; jedes Mitglied setzt alle. Ein `mass`-Punkt auf ein Mitglied ist gültig, die übrigen Mitglieder stehen in `folgen`. `MASS_GESTEUERT` gilt für Gleichung, globale Variable und Konstruktionstabelle.
2. **`pruefung.volumen_delta.soll` ist in Etappe 1 nur eine Zahl.** `auto` entfällt zunächst: `volumen_auto` rechnet ein ganzes Teil aus Features und kennt den fremden Bestand nicht. Die Differenzliste nennt das Volumen ohnehin. Spec §4/§7.2 beim Nachziehen anpassen.
3. **Ein Auftrag nimmt genau eine Datei auf.** Ein anderes Original im selben Auftrag → neuer Code `BESTAND_ANDERE_DATEI`.
4. **Neuer Code `BESTAND_NICHT_LESBAR`:** Original fehlt oder ist gesperrt (`OSError` beim Lesen).
5. **Vergleich öffnet „vorher“ unter anderem Namen.** SolidWorks kann zwei gleichnamige Dokumente nicht zugleich öffnen; `pruefen` kopiert die Bestandskopie nach `<lauf>/vergleich/vorher_<name>` und öffnet diese (Änderung, falls S18d einen besseren Weg findet).
6. **Punkt `skript` benennt nichts um.** Der Compiler-Handler `skript` setzt `feature.Name`; bei einem Eingriff in ein fremdes Feature wäre das ein Anti-Ziel. `bauen(ctx)` darf hier `None` liefern, es gilt nur `pruefe_skript`.
7. **`gleichung`-Punkt:** Form `{typ: gleichung, variable: <Name>, alt: <Zahl>, neu: <Zahl|=Ausdruck>}` oder `{typ: gleichung, gleichung: <linke Seite>, alt: <Text>, neu: <Text>}`.
8. **Fremde Feature-Namen in `feature`-Punkten:** Der Teil-Schema-Typ `id` erlaubt nur `[A-Za-z][A-Za-z0-9_]*`. `validieren` ersetzt fremde Namen in einer Kopie durch Platzhalter `bestand_<n>` und ruft `plausibel_befunde(..., fremde=…)`.

## Global Constraints

- Python nur `.venv\Scripts\python.exe`; swki-Ausgabe JSON; Fehler über `SwkiFehler` mit `daten = {"code": …}`.
- Vor jedem neuen SolidWorks-API-Aufruf `swki api methode <Interface.Member>` bzw. `swki api enum <Name>`; Parameteranzahl und Enum-Werte aus dem Index sind verbindlich; nur Aufrufe aus SW 2025 (`swki api pruefe-code` ohne Befund).
- Die API rechnet in Metern und Radiant, Spezifikationen und Ausgaben in mm und Grad.
- Keine englischen Feature-/Ebenennamen; nie ein SW-Jahr oder einen Pfad fest in Code.
- Original nur lesen, nie in SolidWorks öffnen. swki öffnet und speichert nur unter `<arbeitsordner>/<auftrag>/`; die Bestandskopie nur lesend; gespeichert wird nur in `lauf-<n>/`, an Ort und Stelle (`Save3`; `SaveAs3` hält die Datei-ID zwar auch, S18a, schreibt aber woandershin).
- swki räumt nichts auf: keine neuen Gleichungen oder globalen Variablen, kein Umbenennen, kein Bestimmen fremder Skizzen, außer ein Punkt verlangt es.
- Live-Läufe nur nach Freigabe durch den Nutzer und nie parallel zu einer anderen SolidWorks-Arbeit; Live-Tests einzeln mit `tests\live_einzeln.py`.
- Bestandsdateien bekommen nie das Namensschema `<auftrag>_<name>`.
- Kundendateien kommen nicht ins Git; einzige neue Ausnahme: die erzeugten Musterdateien unter `tests/referenz/bestand/muster/`.
- Kein `git push` ohne Rückfrage. Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Bestand und Lauf tragen denselben Dateinamen**, SolidWorks öffnet zwei gleichnamige Dokumente nicht zugleich: Der Vergleich darf nicht mit „bereits geöffnet“ scheitern (Test in Task 8).
2. **Die Datei hat schon Neuaufbau-Fehler**, wie sie in echten Kollegen-Dateien vorkommen: Handler rufen intern `sw.rebuild`, das bei jedem Fehler abbricht. Bekannte Fehler dürfen den Bau nicht stoppen, neue schon (Test in Task 6).
3. **Original gesperrt oder verschwunden** (Kollege hat es offen, Laufwerk nicht da): sauberer Code bei `aufnehmen`, Warnung statt Absturz bei `ausgabe` (Tests in Task 2 und Task 9).
4. **Mehrere Konfigurationen:** Das Lesen schaltet sie durch; die gespeicherte Datei muss dieselbe aktive Konfiguration haben wie vorher, sonst öffnet der Kollege eine andere Variante (Tests in Task 5 und Task 7).
5. **Unterdrückte Features:** Ihre Maße sind in manchen Konfigurationen nicht lesbar (`None`). Das darf weder als Änderung noch als Absturz enden (Test in Task 7).

## Dateistruktur nach diesem Plan

```
schema/aenderung.schema.json          Schema der Änderungs-Spec
swki/bestand/__init__.py
swki/bestand/fehler.py                Codes, BestandFehler
swki/bestand/ablage.py                Ordner, Kopien, SHA-256, Aufnahme laden (ohne SolidWorks)
swki/bestand/spec.py                  lade_aenderung, Validierung gegen bestand.json, Freigabe
swki/bestand/folgen.py                Folgeänderungen aus der Aufnahme berechnen
swki/bestand/sw_bestand.py            COM: lies_bestand, Maß/Variable setzen, Unterdrücken, Löschen, Speichern, Bild
swki/bestand/punkte.py                Punkt-Handler
swki/bestand/bau.py                   swki bauen für art: aenderung
swki/bestand/vergleich.py             §7.1: zwei Aufnahmen vergleichen (rein)
swki/bestand/differenz.py             §7.2: Bereiche (rein) und Körper-Differenz (COM)
swki/bestand/pruefen.py               swki pruefen für art: aenderung
swki/bestand/ausgabe.py               swki bestand ausgabe
swki/bestand/befehle.py               Befehlsgruppe swki bestand
spikes/s18_muster.py, spikes/s18_bestand.py
tests/bestand/…                       Unit-Tests
tests/live/test_live_bestand.py       Live-Tests
tests/referenz/bestand/               Muster, Änderungs-Spec, Referenz
.claude/skills/aendern/SKILL.md       neuer Skill
```

Geändert: `swki/cli.py`, `swki/spec/befehle.py`, `swki/spec/freigabe.py`, `swki/spec/laden.py`, `swki/compiler/bauen.py`, `swki/compiler/sw.py`, `swki/pruefung/befehle.py`, `swki/pruefung/messen.py`, `swki/pruefung/bericht.py`, `swki/kaufteile/sw_kaufteil.py`, `swki/durchlauf.py`, `swki/aenderungen.py`, `.claude/agents/pruefer.md`, `CLAUDE.md`, Gesamtdesign.

## `bestand.json` (Schnittstelle zwischen allen Tasks)

```json
{"version": 1, "sw_jahr": 2025,
 "datei": {"name": "Lagerdeckel.SLDPRT", "original": "D:\\…", "sha256": "…", "versionen": ["…"], "version_aelter": false},
 "konfigurationen": ["Standard", "Variante B"], "aktiv": "Standard",
 "material": "1.0038", "eigenschaften": {"datei": {"Benennung": "…"}, "konfiguration": {"Standard": {}}},
 "externe_referenzen": [],
 "gleichungen": [{"index": 0, "text": "\"D1@Skizze1\" = \"L\" * 2", "links": "D1@Skizze1", "global": false}],
 "variablen": {"L": 100.0},
 "features": [{"name": "Bohrung2", "typ": "Cut", "eltern": ["Skizze4"], "kinder": ["Fase3"],
               "unterdrueckt": {"Standard": false, "Variante B": false}, "tabelle": false}],
 "skizzen": {"Skizze4": 2},
 "masse": [{"name": "D2@Skizze4", "feature": "Skizze4", "werte": {"Standard": 40.0, "Variante B": null}, "einheit": "mm",
            "zustand": "treibend", "quelle": null, "gruppe": null, "punkte": [[-10.0, 0.0, 20.0]]}],
 "neuaufbau": [{"konfiguration": "Standard", "feature": "Fase3", "code": 12, "warnung": false}],
 "geometrie": {"Standard": {"koerper": 1, "volumen": 12345.6, "box": [0,0,0,1,1,1], "schwerpunkt": [0,0,0]}},
 "tabelle": false}
```

`zustand`: `treibend` | `gesteuert` | `getrieben`. `quelle` bei gesteuert: `{"art": "gleichung"|"variable"|"tabelle", "name": …}`. `gruppe`: Name des gemeinsamen Werts verknüpfter Maße. `werte[k]` ist auch bei unterdrückten Features eine Zahl (S18b); `null` nur, wenn SolidWorks nichts liefert. Zusätzlich `reihenfolge` je Konfiguration und `einheitensystem` (Task 5). Einheiten mm, Grad, mm³.

## Abhängigkeiten vom Spike S18 (Task 1)

| Spike | Entscheidet | Weg (gemessen 2026-10-31, `docs/bestandsdateien/ergebnisse.md` §1) |
|---|---|---|
| S18a | Datei-ID beim Speichern an Ort und Stelle | `IModelDoc2.Save3(1, e, w)`, Baugruppe findet die Datei ohne IdMismatch. `SaveAs3` hält die ID ebenfalls, Save3 bleibt trotzdem der Weg. Prüfgröße: Warnung Bit 1 |
| S18b | Externe Referenzen ohne Öffnen; verknüpfte, tabellengesteuerte Maße erkennen | `GetDocumentDependencies2(pfad, True, False, False)` an der Kopie; `IsDesignTableDimension`, `HasDesignTable`, `IsLinked`, `GetLinkedText`. **Abweichung:** `DrivenState` = 1 bei Gleichung und Referenzmaß, gesteuert aus der linken Gleichungsseite. `GetSystemValue3` mit Namen nur für die aktive Konfiguration brauchbar, also umschalten. `IsReferenceDim`, `GetDesignTable is None` taugen nicht. Maß-Name verknüpft: `Bohrung_D@Skizze3` |
| S18c | Setzen je Konfiguration, Löschen, Handler auf fremder Fläche | `SetSystemValue3` mit 2 bzw. 3 und BSTR-Array; `SetEquationAndConfigurationOption(i, text, 2, None)`; `SetSuppression2` **nur mit Option 2/3** (Option 1 trifft bei altem `IFeature` die falsche Konfiguration); `DeleteSelection2(3)`; `ReorderFeature(name, ziel, 3)`; Handler laufen. Neue Features in allen Konfigurationen aufheben, Status und Rückgaben nicht glauben, nachmessen. `ReorderFeature` = False: Lauf abbrechen, die aktive Konfiguration ist dauerhaft beschädigt; vor dem Speichern Fehler, Volumen, Baum je Konfiguration prüfen (`c3`) |
| S18d | Differenz | `Copy2(True)` + `r, code = Operations2(15902, werkzeug, 0)` beidseitig an unsichtbaren Dokumenten; unverändert `(None, 0)`. Toleranz über die Körperdicke. STL nur als Hinweis (Rauschen 0,03 mm, unsichtbar Absturz) |
| S18e | Bild mit hervorgehobenem Maß | Toggle 31, 32, Ansicht zur Skizzenebene, `IAnnotation.Color` rot, `sw.speichere(kopie=True)`, nicht speichern; Feature: `Select2` |
| S18f | Musterdateien | erzeugt, zusätzlich `gm42-10.SLDPRT` und Referenzmaß `D5@Skizze2` |
| S18g | Baugruppe | Datei-Kopie, Option 64, jeden `GetPathName` prüfen (fehlende Datei lädt still vom Original), nur Geändertes speichern; Pack and Go über IDispatch nicht erreichbar |

Folgen im Schema `bestand.json`: `werte[k]` ist auch bei unterdrückten Features eine Zahl, Code bleibt robust gegen `null`. `punkte` weichen bis 0,1 mm ab. `kinder` nennt nur erklärte Abhängigkeiten. `neuaufbau` braucht das Feld `konfiguration`, `features` ist die Reihenfolge der aktiven Konfiguration; Fehler und Reihenfolge je Konfiguration lesen.

Weicht ein Weg ab, zieht Task 1 die Spec und diesen Abschnitt nach, bevor der betroffene Task beginnt. Fällt die exakte Differenz aus, ändert sich nur `koerper_differenz` (Task 8).

---

### Task 1: Spike S18 und Musterdateien (live)

**Vor dem Start:** Nutzer-OK für den Live-Lauf einholen, prüfen, dass keine andere SolidWorks-Arbeit läuft.

**Files:**
- Create: `spikes/s18_muster.py`, `spikes/s18_bestand.py`, `docs/bestandsdateien/ergebnisse.md`, `tests/referenz/bestand/muster/` (Dateien)
- Modify: `docs/superpowers/specs/2026-10-25-bestandsdateien-design.md` (Nachträge „Nachgezogen bei der Umsetzung“)

**Interfaces:**
- Produces: `tests/referenz/bestand/muster/Lagerdeckel.SLDPRT`, `Muster.SLDASM`; Tabelle der Ergebnisse je Zeile der Spike-Tabelle oben.

- [ ] **Step 1: API-Aufrufe nachschlagen** und Signaturen als Kommentar in die Spike-Skripte übernehmen: alle Aufrufe der Tabelle oben, dazu `IConfigurationManager`, `IModelDoc2.ShowConfiguration2`, `IModelDoc2.GetConfigurationNames`, `IEquationMgr.Equation`, `.GlobalVariable`, `.SetEquationAndConfigurationOption` (4 Parameter), `IFeature.GetParents`, `.GetChildren`, `.GetFirstDisplayDimension`, `.GetNextDisplayDimension`, `IModelDocExtension.DeleteSelection2`, `.ListExternalFileReferences`, `.GetWhatsWrong`, `ISldWorks.VersionHistory`.

- [ ] **Step 2: `spikes/s18_muster.py` schreiben und ausführen.** Über rohe API, ohne `swki.compiler`: Teil *Lagerdeckel* (Grundplatte 100 × 60 × 20, Tasche, zwei Bohrungen, Fase, Rippe oder Wandung als Feature-Typ, den swki nicht kennt), globale Variable `L` mit Gleichung `"D1@Skizze1" = "L"`, ein verknüpftes Maßpaar, zwei Konfigurationen mit unterschiedlich unterdrückter Fase, eine unterbestimmte Skizze, Eigenschaften Benennung/Revision, Material. Dazu Baugruppe *Muster* mit dem Lagerdeckel und einer importierten STEP-Komponente (`tests/referenz/motorhalter/muster/gm42-10.step`). Gespeichert im Arbeitsordner, dann nach `tests/referenz/bestand/muster/` kopiert.
  Erwartet: Dateien öffnen ohne Neuaufbau-Fehler; `git add -f` nötig, falls ein Ignore-Muster greift.

- [ ] **Step 3: `spikes/s18_bestand.py` Zeilen a–e und g ausführen**, je Zeile Ergebnis (Weg, Werte, Zeit, Private Bytes) nach `docs/bestandsdateien/ergebnisse.md` §1.
  Pflichtfragen: S18a: Baugruppe öffnet eine zurückkopierte, an Ort und Stelle gespeicherte Kopie ohne ID-Warnung, Gegenprobe `SaveAs3` zeigt sie. S18d: Differenz unveränderter Geometrie (leer oder Splitter?), kleine Bohrung, verschobene Fläche, Temporärkörper aus zwei Dokumenten kombinierbar? S18b: geht `GetDocumentDependencies2` ohne Öffnen, und lädt `OpenDoc6` Referenzen vom Originalpfad?

- [ ] **Step 4: Spec und Abhängigkeits-Tabelle nachziehen** (Nachträge wie in früheren Specs); Abweichungen, die Entscheidungen des Nutzers berühren, ihm vorlegen.

- [ ] **Step 5: Commit**

```bash
git add spikes/s18_*.py docs/bestandsdateien/ergebnisse.md docs/superpowers tests/referenz/bestand/muster
git commit -m "Spike S18: Bestandsdateien live, Musterdateien in fremdem Stil"
```

### Task 2: Ablage und Fehlercodes

**Files:**
- Create: `swki/bestand/__init__.py`, `swki/bestand/fehler.py`, `swki/bestand/ablage.py`
- Test: `tests/bestand/test_ablage.py`

**Interfaces:**
- Produces: in `fehler.py` `class BestandFehler(SwkiFehler)` mit `__init__(self, code: str, meldung: str, **daten)` und Konstanten `BESTAND_FORMAT`, `BESTAND_VERSION_NEUER`, `BESTAND_NICHT_LESBAR`, `BESTAND_ANDERE_DATEI`, `BESTAND_REFERENZ_EXTERN`, `BESTAND_UNBEKANNT`, `BESTAND_VERALTET`, `BESTAND_ABWEICHEND`, `BESTAND_ORIGINAL_GEAENDERT`, `LAUF_NICHT_BESTANDEN`.
- Produces: in `ablage.py`
  - `bestand_ordner(r: Rechner, auftrag: str, nummer: int) -> Path` (`<arbeitsordner>/<auftrag>/bestand-<n>`)
  - `aufnahmen(r, auftrag) -> list[int]`
  - `kopiere_original(r, auftrag, original: Path) -> dict` → `{"nummer", "pfad": Path, "sha256", "neu": bool}`
  - `lade_aufnahme(r, auftrag, nummer) -> dict`, `schreibe_aufnahme(r, auftrag, nummer, daten) -> Path`
  - `lauf_kopie(quelle: Path, ordner: Path) -> Path`
  - `pruefe_kopie(aufnahme: dict, pfad: Path) -> None`

- [ ] **Step 1: Tests schreiben** (mit `tmp_path`, Rechner-Attrappe wie `tests/kaufteile`)

```python
def test_kopie_liest_original_nur_und_ist_schreibgeschuetzt(r, tmp_path):
    original = tmp_path / "Lager deckel.SLDPRT"; original.write_bytes(b"abc")
    stempel = original.stat().st_mtime_ns
    k = kopiere_original(r, "a1", original)
    assert k["nummer"] == 1 and k["neu"] and k["pfad"].name == "Lager deckel.SLDPRT"
    assert k["sha256"] == hashlib.sha256(b"abc").hexdigest()
    assert original.stat().st_mtime_ns == stempel and original.read_bytes() == b"abc"
    assert not os.access(k["pfad"], os.W_OK)

def test_gleiche_datei_keine_neue_aufnahme(r, tmp_path): ...      # zweiter Aufruf: nummer 1, neu False
def test_geaenderte_datei_neue_aufnahme(r, tmp_path): ...         # anderer Inhalt: nummer 2, neu True
def test_anderes_original_im_auftrag_wird_abgelehnt(r, tmp_path): ...   # BESTAND_ANDERE_DATEI
def test_endung_grossgeschrieben_geht_step_nicht(r, tmp_path): ...      # .SLDPRT ok, .step → BESTAND_FORMAT, .sldasm → BESTAND_FORMAT
def test_original_fehlt_oder_gesperrt(r, tmp_path, monkeypatch): ...    # fehlt und PermissionError beim Lesen → BESTAND_NICHT_LESBAR, kein Traceback
def test_lauf_kopie_hebt_schreibschutz_auf(tmp_path): ...
def test_pruefe_kopie_erkennt_aenderung(tmp_path): ...                  # BESTAND_ABWEICHEND mit beiden SHA-256
```

- [ ] **Step 2: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/bestand/test_ablage.py -q`. Expected: FAIL (Modul fehlt).

- [ ] **Step 3: Implementieren.** `sha256_datei` aus `swki.aenderungen`; Kopie mit `shutil.copy2`, dann `os.chmod(pfad, stat.S_IREAD)`; `lauf_kopie` setzt `stat.S_IWRITE`. Vergleich „gleiche Datei“ über Dateiname ohne Beachtung der Groß-/Kleinschreibung, die SHA-256 der jüngsten Aufnahme.

- [ ] **Step 4: Test laufen lassen.** Expected: PASS.

- [ ] **Step 5: Commit** (`git add swki/bestand tests/bestand`, Nachricht „Bestandsdateien: Ablage und Fehlercodes“).

### Task 3: Schema, Laden, Freigabe, Weichen

**Files:**
- Create: `schema/aenderung.schema.json`, `swki/bestand/spec.py`
- Modify: `swki/spec/freigabe.py` (`pruefsumme`), `swki/spec/befehle.py` (Weichen), `swki/spec/laden.py` (`plausibel_befunde`)
- Test: `tests/bestand/test_spec.py`

**Interfaces:**
- Produces: `lade_aenderung(pfad: Path) -> dict` (Schema, sonst `SpecFehler`); `bauweg_frei(spec: dict) -> dict`; `validieren(pfad: Path) -> dict`; `freigeben(pfad: Path) -> dict`.
- Produces: `plausibel_befunde(spec, auftrag_ordner, fremde: frozenset[str] = frozenset())`: Verweise auf `fremde` gelten als früheres Feature.

- [ ] **Step 1: Tests schreiben**

```python
def test_beispiel_der_spec_ist_gueltig(tmp_path): ...       # Beispiel §4 ohne volumen_delta auto
def test_schema_lehnt_unbekannten_punkt_typ_ab(tmp_path): ...
def test_schema_verlangt_alt_bei_mass(tmp_path): ...
def test_volumen_delta_auto_ist_befund(tmp_path): ...       # Präzisierung 2

def test_bauweg_aendert_pruefsumme_nicht():
    a = spec_mit_feature(flaeche={"nahe": [0, 30, 20]}, bezug={"u": "-rand"})
    b = spec_mit_feature(flaeche={"nahe": [1, 30, 20]}, bezug={"u": "+rand"})
    assert pruefsumme(a) == pruefsumme(b)

def test_reihenfolge_der_punkte_aendert_pruefsumme_nicht(): ...
@pytest.mark.parametrize("aenderung", ["neu", "alt", "folgen", "bereiche", "positionen", "tiefe", "bestand.sha256"])
def test_anforderung_aendert_pruefsumme(aenderung): ...

def test_freigabe_weiche_legt_kopie_an(tmp_path): ...       # swki freigeben <aenderung.yaml>, <name>.freigegeben.yaml und freigabe.json
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.

- [ ] **Step 3: Schema schreiben.** Top-Level Pflicht `art` (`const: aenderung`), `name`, `bestand` (`datei`, `sha256`, `aufnahme`), `punkte` (minItems 1), `bereiche`; optional `parameter`, `pruefung`, `max_nachbesserungen`. `punkte.items` als `oneOf` je `typ` wie Spec §4.1 und Präzisierung 7, gemeinsam `id` (`^[A-Za-z][A-Za-z0-9_]*$`), `was`, `folgen`. `feature.feature` nur `{"type": "object"}` (Inhalt prüft Task 4). `bereiche.items`: `punkte` plus genau eines von `box {min, max}`, `features`. `pruefung`: `masse_pruefen` (Messpunkte `punkt`, `flaeche {nahe, normale}`, `feature`+`flaeche`), `volumen_delta {soll: Zahl, toleranz_prozent}`.

- [ ] **Step 4: `pruefsumme` erweitern.** Für `art == "aenderung"`: `kern = bauweg_frei(spec)`; Import spät wegen Kreisimport. `bauweg_frei`: Kopie aus `art`, `name`, `bestand`, `parameter`, `bereiche`, `pruefung`, `punkte` nach `id` sortiert; in `punkte` rekursiv die Schlüssel `nach`, `bezug`, `flaeche`, `ebene`, `kanten` und bei `typ: skript` `datei` entfernt.

- [ ] **Step 5: Weichen in `swki/spec/befehle.py`** (`validieren`, `freigeben`) nach dem Muster `kaufteil`. `freigeben` nutzt `swki.spec.freigabe.freigeben(pfad, spec)`.

- [ ] **Step 6: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/bestand/test_spec.py tests/spec -q`. Expected: PASS.

- [ ] **Step 7: Commit** („Bestandsdateien: Schema, Laden, Freigabe“).

### Task 4: Validierung gegen die Aufnahme

**Files:**
- Create: `swki/bestand/folgen.py`, `tests/bestand/beispiel_aufnahme.py` (Attrappe nach dem Format oben)
- Modify: `swki/bestand/spec.py`
- Test: `tests/bestand/test_validieren.py`, `tests/bestand/test_folgen.py`

**Interfaces:**
- Produces: `folgen_von(punkt: dict, aufnahme: dict) -> list[str]` (sortiert; Namen der Maße, die mitgehen); `kinder_von(feature: str, aufnahme: dict) -> list[str]` (transitiv); `befunde_gegen_aufnahme(spec: dict, aufnahme: dict) -> list[dict]`; `feature_befunde(spec: dict, aufnahme: dict, ordner: Path) -> tuple[list[dict], list[dict]]` (Befunde, Hinweise); `validieren` gibt `gueltig`, `befunde` über `SpecFehler`, `hinweise`, `pruefsumme`, `folgen`, `version_aelter` aus.

- [ ] **Step 1: Tests schreiben** (Attrappe: Maße `D1@Skizze1` gesteuert über Variable `L`, `D3@Skizze2` = `"D1@Skizze1" + 5`, Paar `D1@S5`/`D2@S6` Gruppe `Spalt`, `D2@Skizze4` frei, `D7@Skizze9` getrieben, `D8@Skizze9` Tabelle)

```python
def test_folgen_ueber_variable_transitiv():
    p = {"typ": "gleichung", "variable": "L", "alt": 100, "neu": 110}
    assert folgen_von(p, AUFNAHME) == ["D1@Skizze1", "D3@Skizze2"]

def test_folgen_verknuepftes_paar():
    assert folgen_von({"typ": "mass", "mass": "D1@S5"}, AUFNAHME) == ["D2@S6"]

@pytest.mark.parametrize("name,code", [
    ("D1@Skizze1", "MASS_GESTEUERT"), ("D8@Skizze9", "MASS_GESTEUERT"), ("D7@Skizze9", "MASS_GESTEUERT"),
    ("D9@Weg", "BESTAND_REFERENZ")])
def test_mass_punkt_befunde(name, code): ...

def test_altwert_abweichend(): ...              # BESTAND_ALTWERT, nennt Wert je Konfiguration
def test_alt_in_unterdrueckter_konfiguration(): ...   # werte None zählt nicht als Abweichung
def test_folgen_abweichend(): ...               # zu wenig und zu viel → FOLGEN_ABWEICHEND
def test_getriebene_nie_in_folgen(): ...
def test_loeschen_ohne_kinder(): ...            # KINDER_FEHLEN
def test_tabelle_sperrt_unterdruecken(): ...    # MASS_GESTEUERT für unterdruecken/aufheben bei feature.tabelle
def test_bereich_fehlt_nur_bei_geometrie(): ... # material/eigenschaft brauchen keinen Bereich
def test_bereich_nennt_unbekannten_punkt(): ...
def test_feature_punkt_wie_teil(): ...          # falsche Normbohrungsgröße → Befund am Pfad punkte[2].feature…
def test_feature_verweist_auf_fremdes_feature(): ...   # {feature: "Schnitt-Linear1", flaeche: "+y"} gültig, unbekannter Name Befund
def test_id_darf_kein_featurename_sein(): ...
def test_skript_datei_fehlt(): ...              # plus pruefe_skript-Befund
def test_aufnahme_veraltet(): ...               # neuere Aufnahme vorhanden → BESTAND_VERALTET
def test_version_aelter_ist_hinweis(): ...
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.

- [ ] **Step 3: `folgen.py` implementieren.** Namen in Gleichungen per Regex `"([^"]+)"` aus `text`; Abhängigkeit „links hängt von Name ab“; Hülle von `variable` bzw. `mass` aus. Verknüpft: alle Maße derselben `gruppe` außer dem Punkt selbst. Getriebene nie.

- [ ] **Step 4: `spec.py` ergänzen.** `feature_befunde`: je `feature`-Punkt `{"id": p["id"], **p["feature"]}`, fremde Namen durch `bestand_<n>` ersetzt, Teil-Spec `{"art": "teil", "name": spec["name"], "parameter": spec.get("parameter", {}), "features": […]}`, dann `schema_befunde`, `plausibel_befunde(..., fremde=…)`, `hinweise`. Pfade auf `punkte[i].feature…` zurückabbilden. Ohne Aufnahme → `BESTAND_UNBEKANNT`.

- [ ] **Step 5: Test laufen lassen.** Expected: PASS.

- [ ] **Step 6: Commit** („Bestandsdateien: Validierung gegen die Aufnahme, Folgen“).

### Task 5: Aufnahme in SolidWorks, `swki bestand aufnehmen`, `zeige`

**Files:**
- Create: `swki/bestand/sw_bestand.py`, `swki/bestand/befehle.py`
- Modify: `swki/cli.py` (`_befehlsgruppen`), `swki/pruefung/messen.py` (`oeffne(app, pfad, sichtbar=True, nur_lesen=False)`)
- Test: `tests/bestand/test_aufnehmen.py`, `tests/live/test_live_bestand.py`

**Interfaces:**
- Consumes: `kopiere_original`, `schreibe_aufnahme`.
- Produces: `lies_bestand(app, model) -> dict` (Format oben ohne `datei`, Schlüssel `sw_jahr` setzt der Aufrufer); `externe_referenzen(app, pfad: Path) -> list[str]`; `aufnehmen(original: Path, auftrag: str) -> dict` (kompakte Zusammenfassung); `zeige(auftrag: str, mass: str | None, feature: str | None) -> dict`; CLI `swki bestand aufnehmen <pfad> --auftrag <a>`, `swki bestand zeige <auftrag> (--mass|--feature)`.

- [ ] **Step 1: Unit-Tests schreiben** (`aufnehmen` mit Attrappen für `verbinde`, `oeffne`, `lies_bestand`)

```python
def test_version_neuer_bricht_vor_dem_oeffnen_ab(...): ...      # BESTAND_VERSION_NEUER; oeffne nie aufgerufen
def test_externe_referenzen_lehnt_ab(...): ...                  # BESTAND_REFERENZ_EXTERN mit Liste, nicht geöffnet
def test_oeffnet_nur_die_kopie_nur_lesend(...): ...             # Pfad liegt unter bestand-1, nur_lesen=True
def test_schliesst_auch_bei_fehler(...): ...
def test_zusammenfassung_kompakt(...): ...                      # Zähler, Maße (Name, Wert, Zustand), Features, Konfigurationen; keine Punkte, keine Rohdaten
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.

- [ ] **Step 3: `lies_bestand` nach den Wegen aus S18b implementieren.** Aktive Konfiguration merken, Konfigurationen mit `ShowConfiguration2` durchschalten, im `finally` die aktive wiederherstellen. Skizzenstatus aus `skizzenstatus`. Neuaufbau über neue `whats_wrong(model) -> list[dict]` in `sw_bestand.py` (`{feature, code, warnung}`). Neuaufbau nur im Speicher; das Dokument wird nie gespeichert.

- [ ] **Step 4: `aufnehmen` und `zeige` implementieren.** Reihenfolge: `pruefe_format`, `VersionHistory`, `externe_referenzen`, `kopiere_original`, öffnen, lesen, Bilder nach `bestand-<n>/bilder`, Vorher-STL nach `bestand-<n>/stl/<konfig>.stl` (nur falls der Rückfall gebraucht wird), schließen, `schreibe_aufnahme`. Ist die Aufnahme schon da und die SHA-256 gleich, nichts neu lesen.

- [ ] **Step 5: Unit-Tests laufen lassen.** Expected: PASS.

- [ ] **Step 6: Live-Test.** `test_aufnahme_musterteil`: Musterteil aufnehmen; Assertions: 2 Konfigurationen, `D1@Skizze1` gesteuert durch `L`, das verknüpfte Paar in einer `gruppe`, Fase in einer Konfiguration unterdrückt mit `werte = None` für ihre Maße, unterbestimmte Skizze im Status, SHA-256 der Musterdatei vorher = nachher, aktive Konfiguration unverändert (Review Focus 4).
  Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_bestand.py`. Expected: `OK`.

- [ ] **Step 7: Commit** („Bestandsdateien: Aufnahme, swki bestand aufnehmen und zeige“).

### Task 6: Punkte und Bau

**Files:**
- Create: `swki/bestand/punkte.py`, `swki/bestand/bau.py`
- Modify: `swki/bestand/sw_bestand.py`, `swki/compiler/sw.py`, `swki/compiler/bauen.py` (`_bauen`-Weiche)
- Test: `tests/bestand/test_punkte.py`, `tests/bestand/test_bau.py`, `tests/compiler/test_sw_rebuild.py` (ergänzen oder neu)

**Interfaces:**
- Consumes: `lauf_kopie`, `pruefe_kopie`, `lade_aufnahme`, `alle_handler`, `Kontext`, `FeatureErgebnis`, `Protokoll`, `pruefsummen`, `pruefe_unveraendert`.
- Produces: `sw.bekannte_fehler(features: set[str])` (Kontextmanager: `sw.rebuild` ignoriert What's-Wrong-Fehler dieser Features); `punkt_handler(typ: str)` mit Registry `PUNKTE`, Signatur `(ctx: Kontext, p: dict, aufnahme: dict) -> list[str]` (Liste der betroffenen SW-Namen fürs Protokoll); `bauen(spec_pfad, lauf=None, verwerfen=False, uebernommen=False, hochstufen=False) -> dict` wie `swki.compiler.bauen.bauen`; `speichere_an_ort(model, pfad: Path) -> None` in `sw_bestand.py`; Feld `hochstufen` im CLI `swki bauen`.

- [ ] **Step 1: Tests schreiben**

```python
def test_rebuild_ignoriert_bekannte_fehler():     # Review Focus 2
    model = model_mit_fehler("Fase3", code=12)
    with sw.bekannte_fehler({"Fase3"}):
        sw.rebuild(model)
    with pytest.raises(BauFehler):
        sw.rebuild(model)

def test_rebuild_neuer_fehler_trotz_bekannter(): ...

def test_mass_prueft_alt_live_und_setzt_in_meter():
    dim = DimAttrappe(0.040)
    punkt_handler("mass")(ctx(dim), {"typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45, "konfigurationen": "alle"}, AUFNAHME)
    assert dim.gesetzt == [(0.045, 2, None)]     # swSetValue_InAllConfigurations

def test_mass_altwert_weicht_im_bau_ab(): ...    # BauFehler BESTAND_ALTWERT
def test_mass_in_benannten_konfigurationen(): ...   # (0.045, 3, ["Variante B"])
def test_feature_punkt_benennt_um(): ...         # p3 → "Gewinde M6 Deckel", p3_positionen → "Gewinde M6 Deckel Skizze", p3_senkung → "… Senkung"
def test_feature_punkt_name_doppelt(): ...       # Name existiert im Bestand → BauFehler
def test_feature_punkt_kennt_fremdes_feature(): ...  # ctx.ergebnisse["Schnitt-Linear1"] aus FeatureByName
def test_loeschen_nennt_kinder(): ...            # nach dem Löschen fehlt ein nicht genanntes Feature → BauFehler
def test_skript_ohne_umbenennen(): ...           # Präzisierung 6: bauen(ctx) -> None erlaubt, Namen bleiben

def test_bau_startet_ab_bestand_und_speichert_an_ort(...): ...   # lauf_kopie vor oeffne; Save3 statt SaveAs3
def test_bau_stoppt_beim_ersten_neuen_fehler(...): ...           # Rest uebersprungen, BauAbbruch mit Punkt-ID
def test_bau_ohne_freigabe(...): ...                             # FREIGABE_FEHLT
def test_bau_kopie_veraendert(...): ...                          # BESTAND_ABWEICHEND
def test_version_aelter_ohne_hochstufen(...): ...                # verweigert; mit hochstufen=True gebaut und im Protokoll vermerkt
def test_speichern_nur_im_arbeitsordner(...): ...
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.

- [ ] **Step 3: `sw.bekannte_fehler` implementieren.** Modulvariable in `swki/compiler/sw.py`; `rebuild` filtert nach `f.Name`. Ohne Kontextmanager unverändert.

- [ ] **Step 4: Punkt-Handler implementieren.** `Kontext` mit `spec = {"parameter": …, "features": [feature-Punkte als Features]}`; `ctx.ergebnisse` vorab mit allen in Punkten und `pruefung` genannten fremden Features. `feature`: `alle_handler()[typ](ctx, {"id": p["id"], **p["feature"]})`, `ctx.ergebnisse[p["id"]] = ergebnis`, umbenennen, optional `nach` (Feature im Baum verschieben, Weg aus S18c). `ctx.gleichungen = False`. Maßprotokoll über `ctx.mass`, `knoten.masse` wie `baue_features`.

- [ ] **Step 5: `bau.py` implementieren** nach `swki.compiler.bauen.bauen`: Freigabe, `pruefe_unveraendert`, `pruefe_kopie`, `lauf_kopie`, öffnen (nicht `nur_lesen`), `sw.bekannte_fehler({e["feature"] for e in aufnahme["neuaufbau"] if not e["warnung"]})`, Punkte in Reihenfolge über `protokoll.knoten_lauf(p["id"], p["typ"])`, nach jedem Punkt `sw.rebuild`, `speichere_an_ort`, schließen, `protokoll.sha256`, `protokoll.dateien = {"teil": …}`, gleiche Rückgabe und `BauAbbruch`. Aktive Konfiguration der Aufnahme vor dem Speichern wiederherstellen.

- [ ] **Step 6: Weiche in `_bauen`** für `art_der_datei(pfad) == "aenderung"`; Option `--hochstufen`.

- [ ] **Step 7: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/bestand tests/compiler -q`. Expected: PASS.

- [ ] **Step 8: Live-Test** `test_bau_mass_und_normbohrung`: Musterteil-Spec mit `mass`, `gleichung`, `unterdruecken`, `feature` (Normbohrung mit `-rand`) bauen; Datei im Lauf neu geöffnet zeigt die Werte, Teil heißt wie das Original, Musterdatei unverändert.
  Expected: `OK`.

- [ ] **Step 9: Commit** („Bestandsdateien: Punkte und Bau ab unveränderter Kopie“).

### Task 7: Vergleich vorher/nachher (§7.1)

**Files:**
- Create: `swki/bestand/vergleich.py`
- Test: `tests/bestand/test_vergleich.py`

**Interfaces:**
- Consumes: Aufnahme-Format, `folgen_von`, `kinder_von`.
- Produces: `vergleiche(spec: dict, vorher: dict, nachher: dict, parameter: dict) -> list[dict]` — Einträge `{"id", "ok": bool | None, …}` im Format `swki.pruefung.bewertung.eintrag`. IDs: `punkt:<id>`, `baum`, `masse`, `gleichungen`, `konfigurationen`, `eigenschaften`, `material`, `neuaufbau`, `skizzen`, `externe_referenzen`.

- [ ] **Step 1: Tests schreiben**

```python
def test_unveraendert_alles_ok(): ...
def test_fremdes_mass_geaendert_ist_mangel():
    n = kopie(VORHER); n["masse"][2]["werte"]["Standard"] = 41.0
    e = eintraege(vergleiche(SPEC_LEER, VORHER, n, {}))
    assert e["masse"]["ok"] is False and "D2@Skizze4" in str(e["masse"])

def test_folgen_sind_erlaubt(): ...
def test_getriebenes_mass_nur_berichtet(): ...          # ok True, abweichungen im Eintrag unter "getrieben"
def test_unterdruecktes_mass_none_ist_keine_aenderung(): ...   # Review Focus 5: None/None und None/Wert bei unterdruecken-Punkt
def test_wert_tauscht_nur_in_genannter_konfiguration(): ...    # Mangel, wenn "Standard" mitging
def test_punkt_mass_nicht_umgesetzt(): ...              # punkt:p1 False, ist/soll
def test_punkt_neu_als_ausdruck(): ...                  # neu "=A_neu" wird aufgelöst
def test_baum_neues_feature_erlaubt_nur_mit_punkt(): ...
def test_baum_umbenannt_ist_mangel(): ...
def test_baum_reihenfolge_ist_mangel(): ...
def test_aktive_konfiguration_geaendert_ist_mangel(): ...      # Review Focus 4
def test_neuer_neuaufbau_fehler(): ...                  # vorhandener bleibt ok, neuer Mangel, Warnung zählt
def test_skizze_schlechter_ist_mangel(): ...            # unterbestimmte bleibt ok
def test_material_eigenschaften_nur_ueber_punkte(): ...
def test_gleichung_geaendert_ohne_punkt(): ...
def test_neue_externe_referenz(): ...
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.

- [ ] **Step 3: Implementieren** (rein, ohne SolidWorks). Vergleichstoleranz 1e-6 mm; Skizzenstatus-Reihenfolge laut `swConstrainedStatus_e` aus dem Index (schlechter = niedrigere Bestimmtheit), eine Tabelle im Modul.

- [ ] **Step 4: Test laufen lassen.** Expected: PASS.

- [ ] **Step 5: Commit** („Bestandsdateien: Vergleich vorher/nachher“).

### Task 8: Geometrie-Differenz, Bereiche, `swki pruefen`

**Files:**
- Create: `swki/bestand/differenz.py`, `swki/bestand/pruefen.py`
- Modify: `swki/pruefung/befehle.py` (Weichen in `pruefen`, `lade_spec_beliebig`), `swki/kaufteile/sw_kaufteil.py` (`_messpunkt` → öffentlich `messpunkt`, Aufrufer anpassen)
- Test: `tests/bestand/test_differenz.py`, `tests/bestand/test_pruefen.py`

**Interfaces:**
- Consumes: `vergleiche`, `lies_bestand`, `lauf_datei`, `schreibe_pruefbericht`, `screenshots`, `pruefe_lauf_gebaut`.
- Produces:
  - `@dataclass Abweichung: art: str ("entfernt" | "hinzu"), box: list[float], volumen: float`
  - `bewerte_bereiche(spec: dict, abweichungen: dict[str, list[Abweichung]], feature_boxen: dict[str, list[float]], toleranz: float = 0.01) -> list[dict]`
  - `koerper_differenz(app, model_vorher, model_nachher, konfiguration: str) -> list[Abweichung]`
  - `pruefen(spec_pfad: Path, lauf: int | None = None) -> dict` (Bericht mit `bestanden`, `maengel`, `pruefungen`, `differenzen`, `bilder`, `bilder_vorher`, `datei`)

- [ ] **Step 1: Tests schreiben**

```python
def test_abweichung_im_bereich_ok():
    a = {"Standard": [Abweichung("entfernt", [-40, 10, 10, -30, 20, 20], 500.0)]}
    assert alle_ok(bewerte_bereiche(SPEC_BOX, a, {}))

def test_abweichung_ausserhalb_ist_mangel(): ...       # id "bereich", nennt Lage und Volumen, Konfiguration
def test_box_grenze_mit_toleranz(): ...                # 0,005 mm über Rand ok, 0,02 mm Mangel
def test_splitter_unter_toleranz_zaehlt_nicht(): ...   # Ausdehnung < 0,01 mm in allen Achsen
def test_bereich_features_aus_boxen(): ...
def test_punkt_ohne_wirkung_ist_mangel(): ...          # kein Differenzkörper im Bereich von p1 → punkt:p1
def test_volumen_delta(): ...

def test_pruefen_oeffnet_vorher_unter_anderem_namen(...):   # Review Focus 1
    ...
    assert vorher_pfad.name != lauf_pfad.name and vorher_pfad.parent == ordner / "vergleich"

def test_pruefen_lehnt_abgebrochenen_lauf_ab(...): ...  # LAUF_ABGEBROCHEN
def test_masse_pruefen_soll_als_ausdruck(...): ...      # soll "=RA"
def test_schliesst_beide_dokumente(...): ...
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.

- [ ] **Step 3: `bewerte_bereiche` rein implementieren** (ein Eintrag je Konfiguration; zählt nur Abweichungen über der Toleranz).

- [ ] **Step 4: `koerper_differenz` nach S18d implementieren.** Je Konfiguration beide Dokumente schalten, Körper vorher und nachher nach Lage paaren (bei mehreren Körpern: größte Überlappung der Hüllquader), `Copy2(False)`, `Operations2(15902, …)` in beide Richtungen, je Ergebnis Volumen und Hüllquader in mm. Ein nur vorher oder nur nachher vorhandener Körper ist als Ganzes eine Abweichung. Aktive Konfiguration am Ende zurück.

- [ ] **Step 5: `pruefen` implementieren.** Freigabe, letzter Lauf, `pruefe_lauf_gebaut`; vorher = `lade_aufnahme(…)`; Lauf nur lesen über `lies_bestand` (`nur_lesen=True`); Bestandskopie nach `<lauf>/vergleich/vorher_<name>` kopieren (Schreibschutz weg, sonst Warnung beim Öffnen) und mit dem Lauf zusammen öffnen; `koerper_differenz`; Messpunkte über `messpunkt` (3c) und `messgeometrie`, `abstand`; `screenshots` für Lauf und Vorher-Kopie (aktive Konfiguration); `bewerte`-Form: `{"bestanden", "maengel", "pruefungen"}` aus `vergleiche` + `bewerte_bereiche` + `mass:<was>`; `schreibe_pruefbericht`. Keine Speicherung, beide im `finally` schließen, die Vorher-Kopie bleibt liegen (zur Analyse).

- [ ] **Step 6: Weichen setzen** in `pruefen` und `lade_spec_beliebig` (Rückgabe `lade_aenderung`).

- [ ] **Step 7: Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/bestand tests/pruefung tests/kaufteile -q`. Expected: PASS.

- [ ] **Step 8: Live-Test** `test_pruefen_besteht_und_zu_enger_bereich`: Lauf aus Task 6 prüfen, ohne Mangel; zweite Spec mit zu engem Bereich → Mangel `bereich`.
  Expected: `OK`.

- [ ] **Step 9: Commit** („Bestandsdateien: Differenz, Bereiche, swki pruefen“).

### Task 9: Status, Bericht, Durchlauf, Ausgabe

**Files:**
- Create: `swki/bestand/ausgabe.py`
- Modify: `swki/bestand/befehle.py`, `swki/durchlauf.py`, `swki/pruefung/bericht.py`, `swki/aenderungen.py`
- Test: `tests/bestand/test_ausgabe.py`, `tests/bestand/test_durchlauf.py`

**Interfaces:**
- Consumes: `lies_laeufe`, `bericht_markdown`, `lade_aufnahme`, `sha256_datei`.
- Produces: `ausgabe(spec_pfad: Path, lauf: int | None = None) -> dict` → `{"dateien": [{"datei", "original", "ausgabe", "sha256"}], "unveraendert": [...], "warnung": str | None, "code": str | None}`; CLI `swki bestand ausgabe <spec> [--lauf n]`.

- [ ] **Step 1: Tests schreiben**

```python
def test_ausgabe_kopiert_nur_geaenderte_unter_originalnamen(...): ...
def test_ausgabe_verlangt_bestandenen_lauf(...): ...          # ohne Prüfer-Urteil verweigert, Code LAUF_NICHT_BESTANDEN
def test_ausgabe_warnt_wenn_original_neuer(...): ...          # BESTAND_ORIGINAL_GEAENDERT, kopiert trotzdem in ausgabe/
def test_ausgabe_warnt_wenn_original_weg(...): ...            # Review Focus 3: warnung, kein Absturz
def test_ausgabe_schreibt_nie_ausserhalb_des_arbeitsordners(...): ...
def test_status_und_bericht_mit_aenderung(...): ...           # art aenderung; Bericht nennt Punkte, Folgen, Differenzen, „Wirkung auf Baugruppen nicht geprüft“
def test_durchlauf_mit_aenderung(...): ...                    # validieren → bauen → prüfen, Attrappen; pruefer_auftrag nennt Vorher-Bilder
def test_aenderungen_verweist_auf_neuen_lauf(...): ...        # swki aenderungen: art aenderung → sagt, dass ein Lauf nur ab Bestand entsteht, Befund bleibt MANUELL_GEAENDERT
```

- [ ] **Step 2: Test laufen lassen.** Expected: FAIL.

- [ ] **Step 3: Implementieren.** Ausgabe nach `<arbeitsordner>/<auftrag>/ausgabe/<name>`; bestanden heißt `lies_laeufe(...)[…]["bestanden"]`. Bericht: neuer Abschnitt in `bericht_markdown`, wenn `spec["art"] == "aenderung"` (`punkte`, `folgen`, `differenzen`, Ausgabeliste). `pruefer_auftrag`: bei `art: aenderung` zusätzlich die Vorher-Bilder. `swki aenderungen`: für `art: aenderung` nur die SHA-Abweichung melden, kein Lesen von Maßen (Abhilfe: Nutzer fragen, Punkt ergänzen, `--uebernommen`, oder `--verwerfen`).

- [ ] **Step 4: Test laufen lassen.** Expected: PASS.

- [ ] **Step 5: Commit** („Bestandsdateien: Status, Bericht, Durchlauf, Ausgabe“).

### Task 10: Referenz und Negativfälle (live)

**Files:**
- Create: `tests/referenz/bestand/lagerdeckel_rev.yaml`, `tests/referenz/bestand/eingabe/aufgabe.md`, `tests/referenz/test_bestand.py`
- Modify: `tests/live/test_live_bestand.py`

**Interfaces:**
- Consumes: alle Befehle.

- [ ] **Step 1: Referenz-Spec schreiben** mit `mass` (frei), `gleichung` (Variable `L`, zwei Folgen), `unterdruecken`, `feature` (Normbohrung mit `-rand`), `eigenschaft` (Revision), enge Bereiche, `masse_pruefen`, `volumen_delta` als Zahl. Unit-Test `test_referenz_gueltig`: `validieren` ohne Befund, mit eingecheckter Attrappe der Aufnahme (`tests/referenz/bestand/bestand.json`, aus Task 5 erzeugt, ohne Rechnerpfade).

- [ ] **Step 2: Unit-Test laufen lassen.** Run: `.venv\Scripts\python.exe -m pytest tests/referenz/test_bestand.py -q`. Expected: PASS.

- [ ] **Step 3: Referenz live durchlaufen:** `aufnehmen`, `validieren`, Nutzer-OK für diese Testfreigabe, `freigeben`, `durchlauf`. Prüfer-Agent `pruefer` mit `pruefer_auftrag`, Urteil nach `protokolle/`, `status` „bestanden“, `ausgabe`, `bericht`.

- [ ] **Step 4: Negativfälle als Live- bzw. Unit-Tests:** falscher Altwert (`BESTAND_ALTWERT`), `mass` auf gesteuertes Maß (`MASS_GESTEUERT`), Bereich zu eng (Mangel `bereich`), Änderung in einer Konfiguration verlangt, in allen umgesetzt (Mangel `masse`/`punkt`, per Skript-Punkt herbeigeführt), Original zwischen Aufnahme und Ausgabe geändert (`BESTAND_ORIGINAL_GEAENDERT`), neuere Dateiversion (Attrappe).
  Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_bestand.py`. Expected: alle `OK`.

- [ ] **Step 5: S18a-Prüfung als Live-Test** `test_datei_id_bleibt`: Ausgabe-Datei in eine Kopie der Musterbaugruppe legen, Baugruppe öffnet ohne ID-Warnung und Neuaufbau-Fehler.

- [ ] **Step 6: Commit** („Bestandsdateien: Referenz Lagerdeckel, Negativfälle“).

### Task 11: Einbindung, Regression, Abnahme

**Files:**
- Create: `.claude/skills/aendern/SKILL.md`
- Modify: `CLAUDE.md`, `.claude/agents/pruefer.md`, `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` (§5 Schutzregel, §11 Zeile), `docs/bestandsdateien/ergebnisse.md`, `werkzeuge/__init__.py` nur, falls ein Spike-Skript bleibt

**Interfaces:**
- Consumes: alle Befehle; Spec §13.

- [ ] **Step 1: Skill `aendern` schreiben** (Skill `writing-for-agents` beachten): wann (fremde Datei, nicht von swki), Abgrenzung zu `konstruieren`/`baugruppe`, Ablauf aufnehmen → Zuordnung der Nutzerpunkte (`zeige`) → Spec → validieren → Freigabe-Vorlage (je Punkt: Stelle, alt → neu, Folgen, Konfigurationen, Bereich, Bild) → Nutzer-OK → freigeben → durchlauf → Prüfer → nachbessern → ausgabe. Regeln: nichts aufräumen, an der Quelle ändern, Bereiche eng, Soll nie an Messwerte anpassen, bei Zweifel an der Zuordnung fragen. Die Datei liegt unter einem geschützten Pfad; falls der Sandkasten das Schreiben sperrt, Nutzer um Freigabe bitten.

- [ ] **Step 2: `CLAUDE.md` ändern.** Grundregel wörtlich: „Nur Dokumente anfassen, die selbst angelegt oder über `swki bestand aufnehmen` als Arbeitskopie aufgenommen wurden.“ Neuer Abschnitt „Bestandsdateien“: Skill `aendern`, Original nur lesen, Ausgabe im Arbeitsordner, Nutzer kopiert zurück, Regression enthält den Lagerdeckel. „Stand“-Zeile aktualisieren. Git-Abschnitt: Ausnahme `tests/referenz/bestand/muster/`.

- [ ] **Step 3: `.claude/agents/pruefer.md`** um „Zusätzlich bei Änderungen (`art: aenderung`)“ ergänzen: Eingabe (Auftrag, freigegebene Änderungs-Spec, Prüfbericht, Vorher- und Nachher-Bilder), jeder Punkt sichtbar umgesetzt und an der gemeinten Stelle; nichts sonst verändert (Bilder, Differenzliste); Folgen plausibel; nichts aufgeräumt.

- [ ] **Step 4: Gesamtregression.** Run: `.venv\Scripts\python.exe -m pytest` und `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz` (SolidWorks geöffnet, frisch) und `.venv\Scripts\python.exe -m swki api pruefe-code`. Expected: alles grün, `pruefe-code` ohne Befund.

- [ ] **Step 5: Abnahme vorbereiten.** Nutzer bittet, eine beliebige echte Kollegen-Datei und zwei bis drei echte Revisionspunkte zu nennen. Ablauf vollständig über den Skill; Kennzahlen (Zeiten, Private Bytes, Differenzen, Befunde) nach `docs/bestandsdateien/ergebnisse.md`. Datei und Spec bleiben unter `auftraege/` (nicht im Git). Trifft sie auf eine Lücke: begründeter Befund, dann Skill `compiler-erweitern` nach Wiederholung.

- [ ] **Step 6: Memory und Commit.** Memory `bestandsdateien-stand.md` anlegen und in `MEMORY.md` verlinken; Commit („Bestandsdateien Etappe 1: Skill, Regeln, Ergebnisse“).

## Self-Review

- **Spec-Abdeckung:** §4 Tasks 3–4, §5 Tasks 2 und 5, §6 Task 6, §7.1 Task 7, §7.2/7.3 Tasks 8, 9, 11, §9 Task 9, §10 Tasks 2–9, §11 Task 1, §12 Task 10, §13 Task 11. §8 und die Baugruppen-Punkte gehören in den Plan Etappe 2; S18g liefert die Grundlage.
- **Abweichungen von der Spec** stehen in den Präzisierungen 1–8 und werden in Task 1 bzw. beim Nachziehen in die Spec übertragen.
