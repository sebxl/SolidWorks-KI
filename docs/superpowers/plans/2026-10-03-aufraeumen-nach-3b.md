# Aufräum-Paket nach Stufe 3b – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die offenen Punkte aus Stufe 3b mit Verhaltensrisiko beheben (Stückliste gegen die Freigabe, Dokumente immer schließen, Verknüpfungen bei fremden Ausnahmen aufräumen, `swki aenderungen` robuster, Kernpfade von `bau.py`), den Übernahme-Ablauf live belegen, die Negativtests schärfen und die Spec 3b an die Umsetzung angleichen.

**Architecture:** Nur Änderungen an bestehendem Code, kein neues Teilsystem. Tasks 1–5 sind reine Python-Tasks mit Unit-Tests (ohne SolidWorks). Task 6 ist der einzige Live-Task. Task 7 zieht Spec, Ergebnisse und CLAUDE.md nach.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) nur für Task 6.

**Spec:** kein eigenes Design-Dokument. Bindend sind die Nutzerentscheidungen unten und `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md`. Quelle der Punkte: `docs/stufe3b/ergebnisse.md` („Offene Punkte“).

## Nutzerentscheidungen (2026-10-03, bindend)

1. **Umfang:** nur Topf A („Aufräum-Paket vor Stufe 4“): die sieben Punkte dieses Plans plus das Nachziehen der Spec 3b.
2. **Nicht in diesem Paket (Topf B, späteres eigenes Paket „Messarten“):** Fasen messen (`c` bei ISO 8734, `p`/Kopffase bei ISO 4762), Volumen bei Gewinde `durch`, Achshöhe der Lagerbohrung im Stehlager.
3. **Bewusst liegen lassen (Topf C):** doppelter Code (Hüllquader-/Maßlogik, `komponente_von`), Docstrings und Testlücken ohne Verhaltensrisiko, die Commit-Message `b7ef5a6`, Rechner B, eine Speichergrenze im Compiler. Nur mitnehmen, wenn die Stelle ohnehin angefasst wird.
4. **Spec 3b nachziehen** ist freigegeben (§4.4, §11, §12; §8 ist schon nachgezogen).

## Global Constraints

- **Late Binding** (`swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()`; nullargumentige Aktionen über `_FlagAsMethod` (`sw_baugruppe.rufe`).
- **API nachschlagen:** vor jedem **neuen** SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` (vorher `PYTHONIOENCODING=utf-8`). Dieser Plan führt keinen neuen API-Aufruf ein. `.venv\Scripts\python.exe -m swki api pruefe-code` muss ohne Befunde bleiben.
- **Einheiten:** Spezifikation und Ausgaben in mm und Grad; die API rechnet in m und rad.
- **Befehle** geben JSON aus, Exit 0 = ok, 1 = Fehler. Fachliche Fehler sind `SwkiFehler` (mit `daten = {"code": …}`).
- **Nur eigene Dokumente** anfassen; speichern nur im `arbeitsordner` aus `config/rechner.yaml`; nie ein SolidWorks-Jahr oder einen Pfad fest in Code schreiben; nie in die Normteilbibliothek schreiben (außer `swki normteil` selbst).
- **Bestand bleibt:** Referenzen Buchse, Formplatte, Auswerferhalteplatte, Stehlager bestehen weiter. Verhalten von `swki bauen`/`pruefen` für Teile unverändert (Task 2 ändert nur den Fall einer unerwarteten Ausnahme).
- **Prüfwerte nie an Messwerte anpassen.** Testerwartungen der Negativfälle nie abschwächen; weicht ein Live-Ergebnis ab, anhalten und dem Controller melden.
- **Sprache:** Code-Bezeichner, Docstrings, Kommentare, Commit-Messages und Berichte auf Deutsch (mit Umlauten in Texten).
- **Tests:** `.venv\Scripts\python.exe -m pytest -q` (ohne SolidWorks; Stand vor dem Plan: **607 passed, 108 deselected**). Jeder Task nennt, wie viele Tests er hinzufügt; maßgeblich ist „vorher + neu“. Live-Tests nur einzeln: `.venv\Scripts\python.exe tests\live_einzeln.py <datei oder datei::test-id> --zeit 600` mit `PYTHONIOENCODING=utf-8`.
- **SolidWorks-Speicher (Task 6):** Private Bytes messen (`Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`), nicht das Working Set. Ein Stehlager-Lauf kostet 3,1–3,6 GB. Der Implementer hält ab ca. 3 GB vor dem nächsten Test an und meldet BLOCKED (Speicher); **der Controller startet SolidWorks neu** (Ablauf in der Übergabe). Genau eine Instanz (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`); Einstellungen vor und nach Live-Läufen `False 1` (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); print(app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6))"`).
- **Git:** Branch `aufraeumen-3b` (von `plan-aufraeumen-3b`), kleine Commits je Task; Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **kein `git push` ohne Rückfrage**; nichts aus `auftraege/` committen; immer gezielt `git add <dateien>`. Einige Dateien liegen mit CRLF vor: Zeilenenden beibehalten (in Git Bash ggf. über ein kleines Python-Hilfsskript statt sed bearbeiten; das Edit-Werkzeug erhält sie).
- **Subagents:** Implementer starten keine Subagents. Nie zwei Implementer gleichzeitig, solange SolidWorks läuft.

## Dateistruktur nach diesem Plan

```
swki/baugruppe/freigabe.py        + freigegebene_quellen()
swki/baugruppe/pruefen.py         Stückliste-Soll aus freigegebene_quellen()
swki/compiler/bauen.py            baue_teil_dokument schließt das Dokument bei unerwarteter Ausnahme
swki/baugruppe/sw_baugruppe.py    verknuepfe: fremde Ausnahmen löschen die neue Verknüpfung; Ausrichtung vor der Gleichung
swki/aenderungen.py               aenderungen: Lauf-Ordner fehlt → Hinweis; Soll erst bei Änderungen; Normteil-Kopien nicht öffnen
swki/baugruppe/bau.py             + _einfuege_reihenfolge(), _ueberspringe_komponenten()
tests/baugruppe/test_freigabe_baugruppe.py, tests/compiler/test_bauen.py, tests/baugruppe/test_referenzen.py,
tests/test_aenderungen.py, tests/baugruppe/test_bau_baugruppe.py           neue Unit-Tests (11)
tests/live/test_live_aenderungen.py   + test_uebernahme_am_teil
tests/live/test_live_stehlager.py     strengere Negativfälle
docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md   §4.4, §11, §12 nachgezogen
docs/stufe3b/ergebnisse.md, CLAUDE.md
```

---

### Task 1: Stückliste-Soll aus den Freigabe-Kopien

Die Positionen eines `je_position`-Features stehen in den `features` der Teil-Spec. `features` gehören nicht zur Teil-Prüfsumme (`PRUEF_FELDER = ("art", "name", "parameter", "material", "eigenschaften", "pruefung")`), sind also Bauweg. Bildet `swki pruefen` das Stückliste-Soll aus der aktuellen Teil-Spec, fällt eine nach der Freigabe zusätzlich eingetragene Position (= eine Schraube mehr) nicht auf. Das Soll kommt künftig aus den Freigabe-Kopien der Teil-Specs.

**Files:**
- Modify: `swki/baugruppe/freigabe.py`
- Modify: `swki/baugruppe/pruefen.py:11-12, 165`
- Test: `tests/baugruppe/test_freigabe_baugruppe.py`

**Interfaces:**
- Consumes: `Baugruppe`, `Quelle` (`swki/baugruppe/modell.py`), `freigegebene_teile(bg) -> dict[str, dict]`, `stueckliste_soll(spec, quellen, auftrag, standard) -> dict[str, int]` (`swki/baugruppe/bewertung.py`).
- Produces: `freigegebene_quellen(bg: Baugruppe) -> dict[str, Quelle]` – wie `bg.quellen`, aber bei `art == "teil"` mit der Teil-Spec im Stand der Freigabe.

- [ ] **Step 1: Failing test – an `tests/baugruppe/test_freigabe_baugruppe.py` anhängen**

```python
def test_stueckliste_soll_aus_der_freigabe(tmp_path):
    """Eine nach der Freigabe zusätzlich eingetragene Senkung (Bauweg) ändert das Soll der Stückliste nicht."""
    from swki.baugruppe.bewertung import stueckliste_soll
    from swki.baugruppe.freigabe import freigegebene_quellen
    from swki.konfig import lade_standard
    from tests.baugruppe.beispiel import DECKEL, kopie

    pfad = schreibe(tmp_path / "A")
    freigeben_baugruppe(lade_baugruppe(pfad))
    deckel = kopie(DECKEL)
    deckel["features"][1]["positionen"].append([0, 20])  # dritte Senkung nach der Freigabe
    schreibe(tmp_path / "A", deckel=deckel)
    bg = lade_baugruppe(pfad)
    standard = lade_standard()
    assert stueckliste_soll(bg.spec, bg.quellen, "A", standard)["ISO4762_M8x16_8_8.sldprt"] == 3
    assert stueckliste_soll(bg.spec, freigegebene_quellen(bg), "A", standard)["ISO4762_M8x16_8_8.sldprt"] == 2
```

(`schreibe`, `freigeben_baugruppe` und `lade_baugruppe` sind in der Datei schon importiert.)

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_freigabe_baugruppe.py::test_stueckliste_soll_aus_der_freigabe -q`
Expected: FAIL mit `ImportError: cannot import name 'freigegebene_quellen'`.

- [ ] **Step 3: `swki/baugruppe/freigabe.py` – Funktion ergänzen**

Import oben ergänzen: `from dataclasses import replace` und `from swki.baugruppe.modell import Baugruppe, Quelle` (statt nur `Baugruppe`). Am Dateiende:

```python
def freigegebene_quellen(bg: Baugruppe) -> dict[str, Quelle]:
    """Quellen mit den Teil-Specs im Stand der Freigabe. Soll der Stückliste: die Positionen der je_position-Features
    sind Bauweg der Teil-Spec (nicht in der Prüfsumme) und wären sonst nicht gegen die Freigabe geschützt."""
    soll = freigegebene_teile(bg)
    return {kid: replace(q, spec=soll[q.datei]) if q.art == "teil" else q for kid, q in bg.quellen.items()}
```

- [ ] **Step 4: `swki/baugruppe/pruefen.py` – Soll aus der Freigabe**

Import ändern: `from swki.baugruppe.freigabe import freigegebene_quellen, freigegebene_teile, pruefe_freigabe_baugruppe`. In `pruefen` die Zeile im `bericht`-Dict ersetzen:

```python
        **bewerte_baugruppe(bg.spec, bg.quellen, messwerte, standard,
                            stueckliste_soll(bg.spec, freigegebene_quellen(bg), auftrag, standard)),
```

- [ ] **Step 5: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe -q` → alle grün.
Run: `.venv\Scripts\python.exe -m pytest -q` → **608 passed** (607 + 1).

- [ ] **Step 6: Commit**

```powershell
git add swki/baugruppe/freigabe.py swki/baugruppe/pruefen.py tests/baugruppe/test_freigabe_baugruppe.py
git commit -m "baugruppe: Stückliste-Soll aus den Freigabe-Kopien der Teil-Specs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `baue_teil_dokument` schließt das Dokument bei unerwarteter Ausnahme

Heute wirft z. B. `Kontext(...)` oder ein Fehler außerhalb der Handler nach `sw.neues_teil` an `baue_teil_dokument` vorbei; das neue Teil bleibt in SolidWorks offen (der Aufrufer bekommt das `model` nie). Erwartete Fehler bleiben Rückgabewerte; der Aufrufer schließt wie bisher.

**Files:**
- Modify: `swki/compiler/bauen.py:37-52`
- Test: `tests/compiler/test_bauen.py`

**Interfaces:**
- Consumes: `sw.neues_teil(app, vorlage)`, `sw.schliesse(app, model)`, `Kontext`, `baue_features`.
- Produces: `baue_teil_dokument(app, r, standard, spec, spec_pfad, auftrag, protokoll) -> (model, ctx, fehler)` – unverändert; bei einer **unerwarteten** Ausnahme (nicht als `fehler` zurückgegeben) ist das Dokument geschlossen und die Ausnahme wird weitergereicht.

- [ ] **Step 1: Failing tests – an `tests/compiler/test_bauen.py` anhängen**

```python
def _teil_bau_attrappen(monkeypatch):
    from types import SimpleNamespace

    geschlossen = []
    model = SimpleNamespace(name="neues Teil")
    monkeypatch.setattr(bauen_modul.sw, "neues_teil", lambda app, vorlage: model)
    monkeypatch.setattr(bauen_modul.sw, "schliesse", lambda app, m: geschlossen.append(m))
    r = SimpleNamespace(vorlage_teil=Path("C:/t.prtdot"))
    return model, geschlossen, r


def test_baue_teil_dokument_schliesst_bei_unerwarteter_ausnahme(monkeypatch):
    model, geschlossen, r = _teil_bau_attrappen(monkeypatch)

    def kaputt(*args, **kwargs):
        raise RuntimeError("Kontext kaputt")

    monkeypatch.setattr(bauen_modul, "Kontext", kaputt)
    with pytest.raises(RuntimeError, match="Kontext kaputt"):
        bauen_modul.baue_teil_dokument(None, r, {"toleranzen": {"anker_mm": 0.01}}, {"name": "x"}, Path("x.yaml"),
                                       "A", Protokoll("A", "x.yaml", 1, 2025))
    assert geschlossen == [model]


def test_baue_teil_dokument_laesst_bei_erwartetem_fehler_offen(monkeypatch):
    model, geschlossen, r = _teil_bau_attrappen(monkeypatch)
    monkeypatch.setattr(bauen_modul, "Kontext", lambda *args: object())
    monkeypatch.setattr(bauen_modul, "vorbereiten", lambda *args: None)
    erwartet = RuntimeError("Feature f2 gescheitert")
    monkeypatch.setattr(bauen_modul, "baue_features", lambda *args: erwartet)
    m, _, fehler = bauen_modul.baue_teil_dokument(None, r, {"toleranzen": {"anker_mm": 0.01}}, {"name": "x"},
                                                  Path("x.yaml"), "A", Protokoll("A", "x.yaml", 1, 2025))
    assert (m, fehler, geschlossen) == (model, erwartet, [])  # der Aufrufer speichert und schließt
```

(`Path`, `pytest` und `bauen_modul` sind in der Datei schon importiert; oben ergänzen: `from swki.compiler.protokoll import Protokoll`.)

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_bauen.py -q -k baue_teil_dokument`
Expected: `test_baue_teil_dokument_schliesst_bei_unerwarteter_ausnahme` FAIL (`assert [] == [model]`); der zweite Test ist schon grün (er sichert das unveränderte Verhalten).

- [ ] **Step 3: `swki/compiler/bauen.py` – Funktion ersetzen**

```python
def baue_teil_dokument(app, r, standard: dict, spec: dict, spec_pfad: Path, auftrag: str, protokoll: Protokoll):
    """Neues Teil aus der Vorlage, Parameter/Werkstoff/Eigenschaften, Features (auch von swki.baugruppe.bau genutzt).
    Liefert (model, ctx, fehler); das Dokument bleibt offen – der Aufrufer speichert und schließt es. Bei einer
    unerwarteten Ausnahme (nicht als fehler zurückgegeben) wird das eigene Dokument geschlossen und die Ausnahme
    weitergereicht, damit kein Teil in SolidWorks offen bleibt."""
    with protokoll.phase("vorbereiten"):
        model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, spec_pfad, standard["toleranzen"]["anker_mm"])
        fehler = None
        try:
            with protokoll.phase("vorbereiten"):
                vorbereiten(app, model, spec, auftrag)
        except Exception as e:  # z. B. MATERIAL_UNBEKANNT
            fehler = e
        if fehler is None:
            with protokoll.phase("bauen"):
                fehler = baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
    except BaseException:
        sw.schliesse(app, model)
        raise
    return model, ctx, fehler
```

- [ ] **Step 4: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler -q` → alle grün.
Run: `.venv\Scripts\python.exe -m pytest -q` → **610 passed** (608 + 2).

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/bauen.py tests/compiler/test_bauen.py
git commit -m "bauen: Teil-Dokument bei unerwarteter Ausnahme schließen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `verknuepfe` räumt bei fremden Ausnahmen auf und prüft die Ausrichtung vor der Gleichung

Zwei Lücken in `swki/baugruppe/sw_baugruppe.py` `verknuepfe`: (a) Nur `BauFehler` löschen die neue Verknüpfung; ein COM-Fehler (z. B. beim Rücklesen von `IMate2.Alignment`) lässt sie stehen und kommt ohne Fehlercode heraus. (b) Die Rücklese-Prüfung der Ausrichtungen läuft erst nach `Add2` der Gleichung; bei einer Umkehr wird die Verknüpfung gelöscht, die Gleichung `"D1@<id>"` bleibt im Gleichungsmanager stehen.

**Files:**
- Modify: `swki/baugruppe/sw_baugruppe.py` (Funktion `verknuepfe`, Block `try … except` ab `if neu is None or status.value != SW_MATE_OK`)
- Test: `tests/baugruppe/test_referenzen.py`

**Interfaces:**
- Consumes: Attrappen-Fixture `asm` und Helfer `_v` in `tests/baugruppe/test_referenzen.py` (Abschnitt „verknuepfe mit Attrappen“).
- Produces: `verknuepfe(asm, v, a, b, parameter, gesetzt=None)` – unverändert in der Signatur; jede Ausnahme nach dem Anlegen löscht die neue Verknüpfung; fremde Ausnahmen werden zu `VERKNUEPFUNG_FEHLER` „`<id> (<typ>): <Typname>: <Meldung>`“; die Umkehr-Meldung bleibt „`<id> kehrt die Ausrichtung von <name> um`“.

- [ ] **Step 1: Failing tests – an `tests/baugruppe/test_referenzen.py` anhängen**

```python
def test_verknuepfe_fremde_ausnahme_loescht_die_neue_verknuepfung(asm, monkeypatch):
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "gleich"), None, None, {}, gesetzt)

    def kaputt(feature):
        raise RuntimeError("Alignment nicht lesbar")

    monkeypatch.setattr(sw_baugruppe, "ausrichtung_von", kaputt)
    with pytest.raises(BauFehler) as e:
        sw_baugruppe.verknuepfe(asm, _v("v2", "deckungsgleich", "gleich"), None, None, {}, gesetzt)
    assert e.value.code == "VERKNUEPFUNG_FEHLER"
    assert str(e.value) == "v2 (deckungsgleich): RuntimeError: Alignment nicht lesbar"
    assert asm.geloescht == ["v2"] and [m.Name for m in asm.mates] == ["v1"] and gesetzt == {"v1": 0}


def test_verknuepfe_prueft_die_ausrichtung_vor_der_gleichung(asm):
    from types import SimpleNamespace

    gleichungen: list[str] = []
    asm.GetEquationMgr = SimpleNamespace(Add2=lambda index, text, loesen: gleichungen.append(text) or 0)
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "gleich"), None, None, {}, gesetzt)
    asm.mates[0].GetSpecificFeature2.Alignment = 1  # v1 wird beim Anlegen von v2 still umgekehrt
    v2 = Verknuepfung("v2", "v2", "abstand", {}, {}, "gleich", "=S", False)
    with pytest.raises(BauFehler, match="v2 kehrt die Ausrichtung von v1 um"):
        sw_baugruppe.verknuepfe(asm, v2, None, None, {"S": 5}, gesetzt)
    assert gleichungen == [] and asm.geloescht == ["v2"]  # keine verwaiste Gleichung "D1@v2"
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_referenzen.py -q -k "fremde_ausnahme or vor_der_gleichung"`
Expected: beide FAIL – der erste mit `RuntimeError` statt `BauFehler`, der zweite mit `assert ['"D1@v2" = "S"'] == []` (die Gleichung wurde vor der Prüfung angelegt).

- [ ] **Step 3: `swki/baugruppe/sw_baugruppe.py` – Block in `verknuepfe` ersetzen**

Den Block von `try:` bis einschließlich `raise BauFehler(VERKNUEPFUNG_FEHLER, f"{v.id} ({v.typ}): {e}", schritt="verknuepfung") from e` ersetzen durch:

```python
    try:
        if neu is None or status.value != SW_MATE_OK:
            raise BauFehler(VERKNUEPFUNG_FEHLER, f"AddMate5 meldet Status {status.value}", schritt="verknuepfung")
        neu.Name = v.id
        sw.rebuild(asm)
        if fc := fehlercode(neu):
            raise BauFehler(VERKNUEPFUNG_FEHLER, f"Fehlercode {fc}", schritt="verknuepfung")
        if gesetzt:
            _pruefe_ausrichtungen(asm, v, gesetzt)  # vor der Gleichung: bei einer Umkehr bleibt keine Gleichung stehen
        if ist_ausdruck(v.wert):
            if asm.GetEquationMgr.Add2(-1, f'"{MASS_NAME}@{v.id}" = {sw_ausdruck(v.wert)}', True) < 0:
                raise BauFehler(GLEICHUNG_FEHLER, f"Gleichung für {v.id} = {v.wert} abgelehnt", schritt="gleichung")
            sw.rebuild(asm)
    except _Umkehr:
        _loesche(asm, neu)
        raise
    except Exception as e:  # auch fremde Ausnahmen (z. B. COM beim Rücklesen): die neue Verknüpfung nicht stehen lassen
        if neu is not None:
            _loesche(asm, neu)
        meldung = str(e) if isinstance(e, BauFehler) else f"{type(e).__name__}: {e}"
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"{v.id} ({v.typ}): {meldung}", schritt="verknuepfung") from e
```

Den Docstring von `verknuepfe` im ersten Absatz ergänzen: „Jede Ausnahme nach dem Anlegen löscht die neue Verknüpfung wieder.“

- [ ] **Step 4: Tests und Code-Prüfung**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe -q` → alle grün (die fünf bestehenden `verknuepfe`-Tests unverändert).
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.
Run: `.venv\Scripts\python.exe -m pytest -q` → **612 passed** (610 + 2).

- [ ] **Step 5: Commit**

```powershell
git add swki/baugruppe/sw_baugruppe.py tests/baugruppe/test_referenzen.py
git commit -m "baugruppe: verknuepfe löscht die Verknüpfung auch bei fremden Ausnahmen, Ausrichtung vor der Gleichung" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `swki aenderungen` robuster

Drei Punkte in `swki/aenderungen.py` `aenderungen`:
1. Fehlt der Lauf-Ordner (aufgeräumt), meldet der Befehl heute jede Datei als `fehlend`. Künftig: klarer Hinweis, nichts zu vergleichen.
2. Das Soll (`soll_parameter`, braucht eine gültige Freigabe) wird heute immer berechnet. Künftig nur, wenn Dateien geändert sind.
3. Geänderte Normteil-Kopien werden heute in SolidWorks geöffnet, obwohl es zu ihnen kein Soll gibt. Künftig wird nur geöffnet, was ein Soll hat.

**Files:**
- Modify: `swki/aenderungen.py` (Funktion `aenderungen`, ab `ordner = lauf_ordner(r, auftrag, lauf)`)
- Test: `tests/test_aenderungen.py`

**Interfaces:**
- Consumes: `abweichungen(ordner, soll)`, `soll_parameter(spec_pfad, auftrag, standard)`, `oeffne`, `verbinde`, Test-Helfer `_lauf(r, spec_pfad, n, …) -> Path` und Fixture `umgebung` in `tests/test_aenderungen.py`.
- Produces: `aenderungen(spec_pfad, lauf=None) -> dict` mit den Schlüsseln `spec`, `lauf`, `geaendert`, `fehlend` und – nur wenn der Lauf-Ordner fehlt oder es keinen Lauf gibt – `text`.

- [ ] **Step 1: Failing tests – an `tests/test_aenderungen.py` anhängen**

```python
def test_aenderungen_bei_aufgeraeumtem_lauf_ordner(umgebung, monkeypatch):
    import shutil

    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    shutil.rmtree(datei.parent)
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: pytest.fail("ohne Lauf-Ordner nichts vergleichen"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert (ergebnis["lauf"], ergebnis["geaendert"], ergebnis["fehlend"]) == (1, [], [])
    assert "Lauf-Ordner" in ergebnis["text"]


def test_aenderungen_ohne_aenderung_braucht_keine_freigabe(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    _lauf(r, spec_pfad, 1)  # keine Freigabe abgelegt
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: pytest.fail("ohne Änderung kein SolidWorks"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert (ergebnis["lauf"], ergebnis["geaendert"], ergebnis["fehlend"]) == (1, [], [])


def test_aenderungen_oeffnet_normteil_kopie_nicht(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    kopie = datei.parent / "ISO4762_M8x30_8_8.sldprt"
    kopie.write_bytes(b"normteil")
    protokoll_pfad = lauf_datei(spec_pfad, 1, "protokoll")
    protokoll = json.loads(protokoll_pfad.read_text(encoding="utf-8"))
    protokoll["sha256"] |= pruefsummen(datei.parent, [kopie])
    protokoll_pfad.write_text(json.dumps(protokoll), encoding="utf-8")
    kopie.write_bytes(b"von Hand geaendert")
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {datei.name: {"L": 100}})
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: pytest.fail("Normteil-Kopie ohne Soll nicht öffnen"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert ergebnis["geaendert"] == [{"datei": "ISO4762_M8x30_8_8.sldprt", "parameter": [],
                                      "hinweis": "keine Spezifikation zu dieser Datei (Normteil-Kopie)"}]
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_aenderungen.py -q -k "aufgeraeumtem or keine_freigabe or normteil_kopie"`
Expected: alle drei FAIL – der erste mit `pytest.fail` aus `soll_parameter` (bzw. `fehlend` ≠ `[]`), der zweite mit `FileNotFoundError` (fehlende `platte.freigegeben.yaml`) aus `soll_parameter`, der dritte mit „Normteil-Kopie ohne Soll nicht öffnen“.

- [ ] **Step 3: `swki/aenderungen.py` – Ende von `aenderungen` ersetzen**

Ab der Zeile `ordner = lauf_ordner(r, auftrag, lauf)` bis zum `return` der Funktion ersetzen durch:

```python
    ordner = lauf_ordner(r, auftrag, lauf)
    if not ordner.is_dir():
        return {"spec": spec_pfad.name, "lauf": lauf, "geaendert": [], "fehlend": [],
                "text": f"Lauf-Ordner {ordner} fehlt (aufgeräumt) – nichts auszulesen"}
    a = abweichungen(ordner, protokoll.get("sha256", {}))
    if not a["geaendert"]:
        return {"spec": spec_pfad.name, "lauf": lauf, "geaendert": [], "fehlend": a["fehlend"]}
    soll = soll_parameter(spec_pfad, auftrag, standard)  # erst jetzt: braucht eine gültige Freigabe
    ergebnis = []
    sw_dateien = [n for n in a["geaendert"] if n.lower().endswith(_SW_DATEIEN) and n in soll]
    if sw_dateien:
        app = verbinde(r.sw_jahr)
        for name in sw_dateien:
            model = oeffne(app, ordner / name)
            try:
                ist = lies_globale_variablen(model)
                if name.lower().endswith(".sldasm"):
                    from swki.baugruppe import sw_baugruppe  # spät importiert (Kreisimport)

                    ist |= {f"verknuepfung:{n}": w for n, w in sw_baugruppe.verknuepfungswerte(model).items()}
            finally:
                sw.schliesse(app, model)  # schließt ohne zu speichern (S9b)
            differenz = parameter_differenz(soll[name], ist)
            eintrag = {"datei": name, "parameter": differenz}
            if not differenz:
                eintrag["hinweis"] = "Datei geändert, Parameter gleich – den Nutzer fragen, was geändert wurde"
            ergebnis.append(eintrag)
    for n in a["geaendert"]:
        if n in sw_dateien:
            continue
        hinweis = ("keine Spezifikation zu dieser Datei (Normteil-Kopie)" if n.lower().endswith(_SW_DATEIEN)
                   else "Datei geändert (nicht ausgelesen)")
        ergebnis.append({"datei": n, "parameter": [], "hinweis": hinweis})
    return {"spec": spec_pfad.name, "lauf": lauf, "geaendert": ergebnis, "fehlend": a["fehlend"]}
```

Den Docstring der Funktion ergänzen: „Ohne Lauf-Ordner oder ohne geänderte Datei wird nichts geöffnet und keine Freigabe gebraucht; Normteil-Kopien (ohne Soll) werden nur genannt.“

- [ ] **Step 4: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_aenderungen.py -q` → alle grün (auch `test_aenderungen_ohne_geaenderte_datei`).
Run: `.venv\Scripts\python.exe -m pytest -q` → **615 passed** (612 + 3).

- [ ] **Step 5: Commit**

```powershell
git add swki/aenderungen.py tests/test_aenderungen.py
git commit -m "aenderungen: Hinweis bei aufgeräumtem Lauf, Soll nur bei Änderungen, Normteil-Kopien nicht öffnen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Kernpfade von `bau.py` – übersprungene Komponenten, Reihenfolge, Bibliothek

Bricht der Lauf vor oder beim Einfügen ab, stehen heute die Verknüpfungen als `uebersprungen` im Protokoll, die nicht eingefügten Komponenten aber gar nicht. Dazu fehlen Unit-Tests für zwei Kernzusagen: die fixierte Komponente wird zuerst eingefügt und fixiert, und `_hole_normteile` schreibt nichts in die Bibliothek.

**Files:**
- Modify: `swki/baugruppe/bau.py` (`_fuege_ein`, `bauen`; zwei neue Helfer)
- Test: `tests/baugruppe/test_bau_baugruppe.py`

**Interfaces:**
- Consumes: `Baulauf`, `Instanz`, `Protokoll.uebersprungen(kid, typ)`, Test-Helfer `_baulauf(pfad, tmp_path)`, `_kontexte(b, bg)` und Fixture `umgebung` in `tests/baugruppe/test_bau_baugruppe.py`.
- Produces: `_einfuege_reihenfolge(b: Baulauf, alle: list[Instanz]) -> list[Instanz]` (fixierte zuerst, sonst stabil); `_ueberspringe_komponenten(b: Baulauf, alle: list[Instanz]) -> None` (vermerkt jede Instanz ohne Knoten als `uebersprungen`, Typ `komponente`).

- [ ] **Step 1: Failing tests – an `tests/baugruppe/test_bau_baugruppe.py` anhängen**

```python
def test_abbruch_vor_dem_einfuegen_vermerkt_komponenten_als_uebersprungen(umgebung, monkeypatch):
    _, pfad, _ = umgebung
    bg = lade_baugruppe(pfad)
    freigeben_baugruppe(bg)
    monkeypatch.setattr(bau, "verbinde", lambda jahr: object())
    monkeypatch.setattr(bau, "_baue_teile",
                        lambda b, r_: bau.BauFehler("TEIL_BAU", "platte/f2: kaputt", schritt="teil"))
    monkeypatch.setattr(bau.sw, "schliesse", lambda app, model: None)
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(pfad)
    knoten = e.value.daten["knoten"]
    assert [k["id"] for k in knoten[:5]] == ["platte", "deckel", "schraube.1", "schraube.2", "stift"]
    assert {k["status"] for k in knoten} == {"uebersprungen"}
    assert len(knoten) == 5 + len(verknuepfungen(bg.spec, bg.quellen))


def test_fixierte_komponente_wird_zuerst_eingefuegt_und_fixiert(tmp_path, monkeypatch):
    from tests.baugruppe.beispiel import BAUGRUPPE, kopie

    spec = kopie(BAUGRUPPE)
    spec["komponenten"] = spec["komponenten"][1:] + spec["komponenten"][:1]  # fixierte Platte zuletzt in der Spec
    pfad = schreibe(tmp_path / "A", baugruppe=spec)
    b, bg = _baulauf(pfad, tmp_path)
    _kontexte(b, bg)
    for q in bg.quellen.values():
        b.dateien[f"teil:{q.datei}" if q.art == "teil" else f"normteil:{q.schluessel}"] = tmp_path / "x.sldprt"
    zaehler, fixiert = iter(range(1, 100)), []
    monkeypatch.setattr(bau.sw, "teilebox_mm", lambda model: [0] * 6)
    monkeypatch.setattr(bau.sw_baugruppe, "fuege_ein", lambda app, asm, p, box: SimpleNamespace(Name2=f"K-{next(zaehler)}"))
    monkeypatch.setattr(bau.sw_baugruppe, "fixiere", lambda asm, komp: fixiert.append(komp.Name2))
    assert bau._fuege_ein(b, instanzen(bg.spec, bg.quellen)) is None
    assert b.protokoll.komponenten[0]["id"] == "platte" and fixiert == ["K-1"]


def test_normteile_werden_kopiert_und_die_bibliothek_bleibt_unveraendert(umgebung, tmp_path, monkeypatch):
    r, pfad, _ = umgebung
    b, bg = _baulauf(pfad, tmp_path)
    bibliothek = tmp_path / "bibliothek"
    bibliothek.mkdir()
    pfade = {}
    for q in bg.quellen.values():
        if q.art == "normteil":
            pfade[(q.norm, q.hole_groesse)] = bibliothek / f"{q.schluessel}.sldprt"
            pfade[(q.norm, q.hole_groesse)].write_bytes(q.schluessel.encode())
    vorher = {p.name: p.read_bytes() for p in bibliothek.iterdir()}
    monkeypatch.setattr(bau.normteil_befehle, "hole",
                        lambda norm, groesse, variante: {"pfad": str(pfade[(norm, groesse)]), "gebaut": False})
    monkeypatch.setattr(bau, "bibliotheksordner", lambda r_: bibliothek)
    monkeypatch.setattr(bau, "lies_eintrag", lambda ordner, schluessel: {"pruefsumme": "abc"})
    monkeypatch.setattr(bau, "oeffne", lambda app, p: SimpleNamespace(pfad=Path(p)))
    monkeypatch.setattr(bau, "kontext_aus_datei", lambda app, model, spec, p, tol, prot: SimpleNamespace(model=model))
    assert bau._hole_normteile(b, r, 0.01) is None
    assert {p.name: p.read_bytes() for p in bibliothek.iterdir()} == vorher  # nichts in die Bibliothek geschrieben
    assert {p.name for p in b.ordner.iterdir()} == set(vorher)               # Kopien im Lauf-Ordner
    assert all(m.pfad.parent == b.ordner for m in b.offen)                  # geöffnet werden nur die Kopien
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bau_baugruppe.py -q -k "uebersprungen or zuerst or bibliothek"`
Expected: `test_abbruch_vor_dem_einfuegen_vermerkt_komponenten_als_uebersprungen` FAIL (die ersten Knoten sind Verknüpfungen, `v1` statt `platte`); die beiden anderen sind schon grün (sie sichern bestehendes Verhalten ab).

- [ ] **Step 3: `swki/baugruppe/bau.py` – Helfer und Einbau**

Vor `_fuege_ein` einfügen:

```python
def _einfuege_reihenfolge(b: Baulauf, alle: list[Instanz]) -> list[Instanz]:
    """Die fixierte Komponente zuerst, sonst Spec-Reihenfolge, Instanzen in Positionsreihenfolge (stabil sortiert)."""
    fixiert = {k["id"] for k in b.bg.spec["komponenten"] if k.get("fixiert")}
    return sorted(alle, key=lambda x: x.komponente not in fixiert)


def _ueberspringe_komponenten(b: Baulauf, alle: list[Instanz]) -> None:
    """Komponenten ohne Knoten (Abbruch vor oder beim Einfügen) als übersprungen vermerken – wie die Verknüpfungen."""
    erfasst = {k.id for k in b.protokoll.knoten}
    for i in _einfuege_reihenfolge(b, alle):
        if i.id not in erfasst:
            b.protokoll.uebersprungen(i.id, "komponente")
```

In `_fuege_ein` die ersten beiden Zeilen

```python
    fixiert = {k["id"] for k in b.bg.spec["komponenten"] if k.get("fixiert")}
    for i in sorted(alle, key=lambda x: x.komponente not in fixiert):  # stabil: die fixierte zuerst
```

ersetzen durch

```python
    fixiert = {k["id"] for k in b.bg.spec["komponenten"] if k.get("fixiert")}
    for i in _einfuege_reihenfolge(b, alle):
```

In `bauen` direkt vor `with protokoll.phase("verknuepfen"):` (gleiche Einrückung wie dieses `with`) einfügen:

```python
        if fehler is not None:
            _ueberspringe_komponenten(b, alle_instanzen)
```

- [ ] **Step 4: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe -q` → alle grün (auch die Schließ- und Fehlertests).
Run: `.venv\Scripts\python.exe -m pytest -q` → **618 passed** (615 + 3).

- [ ] **Step 5: Commit**

```powershell
git add swki/baugruppe/bau.py tests/baugruppe/test_bau_baugruppe.py
git commit -m "baugruppe: nicht eingefügte Komponenten als übersprungen, Tests für Reihenfolge und Bibliothek" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Live – Übernahme am Teil, strengere Negativfälle, Regression

**Files:**
- Modify: `tests/live/test_live_aenderungen.py` (neuer Test)
- Modify: `tests/live/test_live_stehlager.py` (vier Tests schärfer)

**Interfaces:**
- Consumes: `swki bauen --uebernommen` (Fehlercode `UEBERNAHME_OHNE_NEUE_FREIGABE`, Protokollfeld `uebernommen`), Helfer `_lauf`, `_setze_parameter`, `SPEC`, `AUFTRAG` in `tests/live/test_live_aenderungen.py`; Helfer `_aendere`, `_komponente`, `_baue_und_pruefe`, `_maengel`, `AUFTRAG` in `tests/live/test_live_stehlager.py`.
- Produces: Live-Beleg für den Übernahme-Ablauf (Spec 3b §8) und Negativfälle ohne Zusatzmängel.

- [ ] **Step 1: Vorbedingungen**

SolidWorks 2025 läuft, genau eine Instanz, keine fremden offenen Dokumente, `False 1`, Private Bytes notieren (Befehle in den Global Constraints). Sonst anhalten und melden.

- [ ] **Step 2: `tests/live/test_live_aenderungen.py` – Test anhängen**

```python
def test_uebernahme_am_teil(capsys, tmp_path):
    """Spec 3b §8 „übernehmen“: Handänderung in die Spec übernehmen, neu freigeben, mit --uebernommen bauen."""
    spec_pfad = tmp_path / AUFTRAG / "platte.yaml"
    spec_pfad.parent.mkdir()
    spec_pfad.write_text(yaml.safe_dump(SPEC, allow_unicode=True), encoding="utf-8")
    try:
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        _setze_parameter(lauf_ordner(lade_rechner(), AUFTRAG, 1) / f"{AUFTRAG}_Platte.sldprt", "L", 120)
        code, daten = _lauf(capsys, "bauen", str(spec_pfad), "--uebernommen")  # noch nicht neu freigegeben
        assert code == 1 and daten["code"] == "UEBERNAHME_OHNE_NEUE_FREIGABE", daten
        uebernommen = {**SPEC, "parameter": {**SPEC["parameter"], "L": 120}}
        spec_pfad.write_text(yaml.safe_dump(uebernommen, allow_unicode=True), encoding="utf-8")
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad), "--uebernommen")
        assert code == 0 and bau["lauf"] == 2, bau
        protokoll = json.loads((spec_pfad.parent / "protokolle" / "platte.lauf-2.protokoll.json").read_text(encoding="utf-8"))
        assert protokoll["uebernommen"]["lauf"] == 1 and not protokoll.get("verworfen"), protokoll
        code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
        assert code == 0 and bericht["maengel"] == [], bericht["maengel"]
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))  # Lauf 2 ist unverändert: ohne Schalter
        assert code == 0 and bau["lauf"] == 3, bau
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)
```

- [ ] **Step 3: `tests/live/test_live_stehlager.py` – Negativfälle schärfer**

`_maengel` und die vier Tests so ersetzen (Begründung je Fall im Kommentar; die Erwartung ist die vollständige Mängelmenge, nicht nur ein Vorkommen):

```python
def _maengel(bericht: dict) -> dict:
    assert bericht["bestanden"] is False, bericht
    return {m["pruefung"]: m for m in bericht["maengel"]}


def test_zu_lange_deckelschraube(capsys, auftrag):
    # M8 × 40 statt × 35: Einschraublänge 18,6 mm > Gewindetiefe 16 mm, an beiden Deckelschrauben; sonst nichts
    pfad = _aendere(auftrag, lambda s: _komponente(s, "deckelschraube").update(quelle={"normteil": "ISO 4762 M8x40"}))
    maengel = _maengel(_baue_und_pruefe(capsys, pfad))
    assert set(maengel) == {"gewinde:deckelschraube.1", "gewinde:deckelschraube.2"}, maengel
    for i in (1, 2):
        assert "Einschraublänge 18.60" in maengel[f"gewinde:deckelschraube.{i}"]["beschreibung"], maengel


def test_ueberlappung(capsys, auftrag):
    # Stift 8 × 40 statt × 30: beide Stifte ragen 8 mm über die Stiftbohrungen (Tiefe 12) in den Fuß des Unterteils
    pfad = _aendere(auftrag, lambda s: _komponente(s, "stift").update(quelle={"normteil": "ISO 8734 8x40"}))
    maengel = _maengel(_baue_und_pruefe(capsys, pfad))
    assert set(maengel) == {"kollision"}, maengel
    assert {"stift.1", "stift.2", "unterteil"} <= set(maengel["kollision"]["knoten"]), maengel


def test_unterbestimmte_komponente(capsys, auftrag):
    # ohne v3 (parallel) dreht das Unterteil frei um die Stiftachse
    pfad = _aendere(auftrag, lambda s: s.update(verknuepfungen=[v for v in s["verknuepfungen"] if v["id"] != "v3"]))
    maengel = _maengel(_baue_und_pruefe(capsys, pfad))
    assert set(maengel) == {"bestimmtheit"}, maengel
    assert "unterteil" in maengel["bestimmtheit"]["knoten"], maengel


def test_manuelle_aenderung_in_der_baugruppe(capsys, auftrag):
    pfad = auftrag / "stehlager.yaml"
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, bau
    _setze_parameter(lauf_ordner(lade_rechner(), AUFTRAG, 1) / f"{AUFTRAG}_Grundplatte.sldprt", "L", 210)
    code, daten = _lauf(capsys, "bauen", str(pfad))
    assert code == 1 and daten["code"] == "MANUELL_GEAENDERT", daten
    code, daten = _lauf(capsys, "aenderungen", str(pfad))
    assert code == 0, daten
    assert [e["datei"] for e in daten["geaendert"]] == [f"{AUFTRAG}_Grundplatte.sldprt"], daten  # nur die Grundplatte
    assert daten["geaendert"][0]["parameter"] == [{"name": "L", "soll": 200, "ist": 210.0}]
    assert daten["fehlend"] == [], daten
```

Weicht live die Mängelmenge eines Negativfalls ab (z. B. ein zusätzlicher Mangel): **nicht** die Erwartung anpassen, sondern anhalten (NEEDS_CONTEXT) und Prüfbericht-Auszug melden – der Controller entscheidet, ob die Erwartung oder der Code falsch ist.

- [ ] **Step 4: Unit-Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → **618 passed, 109 deselected** (ein neuer Live-Test).

- [ ] **Step 5: Live – einzeln, Speicher nach jedem Test messen**

Je Test-ID mit `--zeit 600`; ab ca. 3 GB vor dem nächsten Test anhalten (BLOCKED Speicher, offene Test-IDs nennen):

1. `tests\live\test_live_aenderungen.py` (beide Tests)
2. `tests\live\test_live_bauen.py` (Task 2 hat `baue_teil_dokument` geändert)
3. `tests\live\test_live_baugruppe.py::test_probe_besteht_pruefung` (Task 1, Stückliste)
4. `tests\referenz\test_referenzen.py::test_referenz_besteht[stehlager-stehlager.yaml]` (frisches SolidWorks)
5. die vier Tests aus `tests\live\test_live_stehlager.py` (je ein frisches SolidWorks)

Erwartet: alle OK.

- [ ] **Step 6: Commit**

```powershell
git add tests/live/test_live_aenderungen.py tests/live/test_live_stehlager.py
git commit -m "live: Übernahme am Teil belegt, Negativfälle am Stehlager mit vollständiger Mängelmenge" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Im Bericht: je Test OK/Fehler, Private Bytes vorher → nachher, Instanzen und Einstellungen am Ende.

---

### Task 7: Spec 3b nachziehen, Ergebnisse, CLAUDE.md

**Files:**
- Modify: `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md` (Kopf, §4.4, §11, §12)
- Modify: `docs/stufe3b/ergebnisse.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: Ergebnisse von Task 1–6 (Commits, Testzahlen, Live-Ergebnisse aus den Berichten).
- Produces: Spec und Ergebnisse im Stand der Umsetzung.

- [ ] **Step 1: Spec-Kopf**

Den Satz „Stand 2026-10-03, mit dem Nutzer abgestimmt.“ ergänzen zu: „Stand 2026-10-03, mit dem Nutzer abgestimmt; nach der Umsetzung nachgezogen (Aufräumen nach 3b): §4.4, §8, §11, §12.“

- [ ] **Step 2: §4.4 – Ausrichtung bei `konzentrisch`**

Den Aufzählungspunkt, der mit „`ausrichtung: gleich | entgegengesetzt` ist Pflicht bei“ beginnt, vollständig ersetzen durch:

```markdown
- `ausrichtung: gleich | entgegengesetzt` ist Pflicht bei `deckungsgleich`, `parallel`, `abstand` und `winkel`; `validieren`
  meldet das Fehlen. Bei `konzentrisch` ist sie optional: Ohne Angabe legt swki die Verknüpfung mit „nächstliegend“
  (swMateAlignCLOSEST) an; nach einer vorherigen Ebenen-Verknüpfung mit Ausrichtung ist das die schon festgelegte Richtung der
  Komponente (Regel „Ebene vor Achse“ im Skill `baugruppe`). Als Wert der Spezifikation gibt es „nächstliegend“ nicht.
  SolidWorks kehrt die Ausrichtung einer früheren Verknüpfung still um, wenn eine spätere widerspricht (Spike S12 Zeile 5,
  ohne Status oder Fehlercode); swki liest deshalb nach jeder Verknüpfung die ausdrücklich gesetzten Ausrichtungen zurück und
  bricht bei einer Umkehr mit `VERKNUEPFUNG_FEHLER` „<id> kehrt die Ausrichtung von <name> um“ ab.
```

- [ ] **Step 3: §11 – zwei Zeilen in der Tabelle**

Nach der Zeile `| \`MANUELL_GEAENDERT\` | …` einfügen:

```markdown
| `UEBERNAHME_OHNE_NEUE_FREIGABE` | `swki bauen --uebernommen`, aber die Freigabe ist nicht neuer als der verglichene Lauf (§8) | Lauf, geänderte bzw. fehlende Dateien |
| `SCHLIESSEN_FEHLER` | ein Dokument ließ sich nach dem Bau nicht schließen (ohne früheren Fehler) | Typ und Meldung der Ausnahme |
```

- [ ] **Step 4: §12 – ISO 8734**

Den zweizeiligen Aufzählungspunkt „**ISO 8734:** neue Vorlagenversion: …“ (Umbruch nach „und `c` direkt“, endet mit „neues Prüfer-Urteil.“) vollständig ersetzen durch:

```markdown
- **ISO 8734:** neue Vorlagenversion: `EINBAU_EBENE_2` gegen +y mit Soll 0 gemessen (statt nur als Betrag); `c` bleibt über
  das Volumen belegt, weil es keine Messart für Fasen gibt (Präzisierung 3 der Umsetzung; eine Messart für Fasen ist ein
  späteres eigenes Paket); neues Prüfer-Urteil.
```

- [ ] **Step 5: `docs/stufe3b/ergebnisse.md`**

1. Neuen Abschnitt vor „## Offene Punkte“ einfügen: „## Aufräumen nach 3b (Stand <Datum>)“ mit je Task 1–7 einer Zeile (Inhalt, Commit), Unit-Tests vorher → nachher (607 → 618, 108 → 109 deselected), Live-Ergebnisse aus Task 6 (je Test, Private Bytes).
2. In „## Offene Punkte“ die erledigten Punkte durchstreichen und mit „(erledigt: Aufräumen nach 3b, Task N)“ markieren: Spec 3b nicht nachgezogen; `c` bei ISO 8734 (nur den Teil „Spec nachgezogen“ vermerken, die Messart bleibt offen); Stückliste-Soll aus den Freigabe-Kopien; `aenderungen` öffnet Normteil-Kopien; Task-5-Minors `baue_teil_dokument` schließt nicht, `aenderungen` braucht immer eine Freigabe, aufgeräumter Lauf-Ordner; Task-7-Minors Ausrichtungsprüfung nach `Add2`, nur `BauFehler` gefangen; Task-8-Minors fehlende Kernpfad-Tests, nicht eingefügte Komponenten nicht als `uebersprungen`; Task-11-Minors „prüfen nur das Vorkommen“, „nur `deckelschraube.1`“, „Test der Änderungserkennung prüft nur die Grundplatte“; „Live-Test übernehmen fehlt“, falls dort genannt.
3. Neuen Punkt unter „## Offene Punkte“ ergänzen: „**Messarten (eigenes Paket, Nutzerentscheidung 2026-10-03):** Fasen (`c` ISO 8734, `p`/Kopffase ISO 4762), Volumen bei Gewinde `durch`, Achshöhe der Lagerbohrung im Stehlager.“

- [ ] **Step 6: `CLAUDE.md`**

Den „Stand:“-Absatz (ab Zeile 4 „Stand: Stufe 3b …“ bis „… Danach: Stufe 4 (mechanische Abläufe).“, drei Zeilen, auf dem Branch `plan-aufraeumen-3b` mit dem Verweis auf diese Übergabe) ersetzen durch folgende drei Zeilen; die Leerzeile vor „## Umgebung“ bleibt:

```markdown
Stand: Stufe 3b (Baugruppen statisch) umgesetzt, Aufräumen nach 3b umgesetzt – Ergebnisse: docs/stufe3b/ergebnisse.md.
Nächster Schritt: Stufe 4 (mechanische Abläufe): Brainstorming → Spec → Plan. Danach (oder vorher, nach Nutzerwunsch):
Paket „Messarten“ (Fasen, Gewinde durch, Lagerachse).
```

- [ ] **Step 7: Gesamtlauf**

Run: `.venv\Scripts\python.exe -m pytest -q` → **618 passed, 109 deselected**.
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.

- [ ] **Step 8: Commit**

```powershell
git add docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md docs/stufe3b/ergebnisse.md CLAUDE.md
git commit -m "docs: Spec 3b nachgezogen (§4.4, §11, §12), Ergebnisse und CLAUDE.md nach dem Aufräumen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Abdeckung (Selbstprüfung)

| Punkt aus Topf A | Task |
|---|---|
| A1 Stückliste-Soll aus der Freigabe | 1 |
| A2 Dokumente immer schließen | 2 |
| A3 Rücklese-Fehler sauber abbrechen (+ Ausrichtung vor der Gleichung) | 3 |
| A4 `aenderungen` robuster | 4 |
| A5 Live-Test „übernehmen“ | 6 |
| A6 schärfere Negativtests | 6 |
| A7 Kernpfad-Tests `bau.py` | 5 |
| A8 Spec 3b nachziehen | 7 |
