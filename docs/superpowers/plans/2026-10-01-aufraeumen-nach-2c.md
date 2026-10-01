# Aufräum-Paket nach Stufe 2c – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Nutzerentscheidungen zur Prüfschleife umsetzen und die offenen Punkte aus Stufe 2b/2c abarbeiten: Robustheit der Befehle, Validierung und Hinweise, fehlende Tests, zwei kleine Umbauten.

**Architecture:** Nur Änderungen an bestehendem Code, kein neues Teilsystem. Jede Gruppe (A–E) steckt in eigenen Tasks mit eigenen Unit-Tests. Live-Läufe gegen SolidWorks gibt es nur in Task 8. Reine Python-Tasks (1–7) brauchen kein SolidWorks.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) nur für Task 8.

**Spec:** kein eigenes Design-Dokument. Bindend sind die Nutzerentscheidungen unten und `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` §6 (Prüfung/Schleife). Quellen der offenen Punkte: `docs/stufe2/ergebnisse.md` („Offene Punkte für Stufe 3“), `docs/stufe2c/ergebnisse.md` („Offene Punkte“, Korrekturrunde).

## Nutzerentscheidungen (2026-10-01, bindend)

1. **Läufe:** 1 + 3 = höchstens 4 Läufe (erster Lauf plus 3 Nachbesserungen). Der Code macht das schon (`max_laeufe`); nur der Spec-Text „Vorgabe 3“ wird präzisiert.
2. **Regel „kein Fortschritt“ (Option A):** Ein Lauf mit Bauabbruch (`swki bauen` bricht an einem Feature ab, Protokollstatus `fehler`) wird **nicht verglichen**. Er verbraucht nur einen der Läufe. Die Regel vergleicht ausschließlich Läufe, die durchgebaut **und** geprüft sind (Prüfbericht und Prüfer-Urteil liegen vor), jeweils mit dem letzten solchen Lauf davor. Beispiel: Lauf 1 hat 5 Mängel, Lauf 2 bricht ab, Lauf 3 hat 6 Mängel → 6 ≥ 5 → Stopp.
3. **Rechner B (SW 2026)** steht nicht zur Verfügung: überspringen und in den Ergebnissen als zurückgestellt vermerken. Das Fertig-Kriterium in Spec §11 bleibt unverändert.
4. **Umfang:** Gruppen A–E vollständig (A Prüfschleife, B Robustheit der Befehle, C Validierung/Hinweise, D Tests nachziehen, E Code-Pflege).

## Global Constraints

- **Late Binding** (siehe `swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()`; IBody2 hat Typinfo → dort **mit** `()`.
- **Einheiten:** Spezifikation und Ausgaben in mm und Grad; die API rechnet in m und rad.
- **Befehle** geben JSON aus, Exit 0 = ok, 1 = Fehler. Fachliche Fehler sind `SwkiFehler` (optional mit `daten = {"code": …}`).
- **Nur eigene Dokumente** anfassen; speichern nur im `arbeitsordner` aus `config/rechner.yaml`; nie ein SolidWorks-Jahr oder einen Pfad fest in Code schreiben.
- **API nachschlagen:** vor jedem **neuen** SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` (vorher `PYTHONIOENCODING=utf-8`). `.venv\Scripts\python.exe -m swki api pruefe-code` muss ohne Befunde bleiben. (Dieser Plan führt keinen neuen API-Aufruf ein.)
- **Bestand bleibt:** Referenzen *Buchse*, *Formplatte*, *Auswerferhalteplatte* (`tests/referenz/`) werden nicht geändert und bestehen weiter. Handler `bohrung` und `SkriptKontext` bleiben unverändert.
- **Prüfwerte nie an Messwerte anpassen.**
- **Sprache:** Code-Bezeichner, Docstrings, Kommentare, Commit-Messages und Berichte auf Deutsch.
- **Tests:** `.venv\Scripts\python.exe -m pytest -q` (ohne SolidWorks; Stand vor dem Plan: **276 passed, 54 deselected**). Jeder Task nennt, wie viele Tests er hinzufügt; die Gesamtzahl ist „vorher + neu“. Live-Tests nur einzeln: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> …` mit `PYTHONIOENCODING=utf-8`.
- **SolidWorks-Speicher (Task 8):** Private Bytes von `SLDWORKS.exe` messen (PowerShell `Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`), nicht das Working Set. Ab ca. 4 GB nach der laufenden Testdatei anhalten und den Nutzer um einen Neustart bitten. Genau eine Instanz; nie eine fremde Instanz beenden. Toggle 10 und Integer-Einstellung 6 vor und nach Live-Läufen gleich (Befehl: `.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); print(app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6))"`, erwartet `False 1`).
- **Git:** eigener Branch (z. B. `aufraeumen`), kleine Commits je Task; Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **kein `git push` ohne Rückfrage**; nichts aus `auftraege/` committen; immer gezielt `git add <dateien>`.
- **Subagents:** Implementer starten keine Subagents.

## Dateistruktur nach diesem Plan

```
swki/pruefung/schleife.py      Regel „kein Fortschritt“ (Option A), Form-Prüfung pruefer.json
swki/pruefung/befehle.py       pruefen verweigert abgebrochene Läufe, --max ≥ 0, git-Fehler in _compiler_aenderungen
swki/pruefung/bericht.py       Spalte „Offen“ zeigt „–“ bei Bauabbruch
swki/auftrag.py                + lauf_belegt()
swki/compiler/bauen.py         --lauf N verweigert einen vorhandenen Lauf
swki/spec/befehle.py           freigeben lehnt *.freigegeben.yaml ab, gibt den Pfad der Kopie aus
swki/compiler/sw.py            speichere prüft den Arbeitsordner
swki/spec/laden.py             reservierte IDs, normbohrung (doppelte Positionen, Tiefe vs. Senkung), Kreissektor-Kontur
swki/spec/hinweise.py          feste_zahl ohne Fehlalarme, Sammelhinweis für Konturpunkte, Texte Regel 3
swki/pruefung/geometrie.py     _pappus für Rechteck/Kreis, mehrere Profile → nicht berechenbar
swki/spec/konturen.py          + eckradien_roh()
swki/compiler/skizze.py        Polygonradien über eckradien_roh()
swki/spec/normen.py            + SW_FM_HOLE_WZD, SW_BEFESTIGUNG_STIFT_DURCH, SW_LOCH_DURCH (von Handler/Bewertung hierher)
docs/superpowers/specs/2026-09-26-solidworks-ki-design.md  §6 Läufe und Regel „kein Fortschritt“
.claude/skills/konstruieren/SKILL.md                       Schleife: Bauabbruch, Prüfung abgebrochener Läufe
docs/stufe2/ergebnisse.md, docs/stufe2c/ergebnisse.md      offene Punkte abgehakt, Rechner B zurückgestellt
tests/…                        neue Unit-Tests je Task, tests/compiler/test_kontext.py (neu), Live-Test Zwei-Körper
```

---

### Task 1: Prüfschleife – Bauabbruch nicht vergleichen, abgebrochenen Lauf nicht prüfen, `--max ≥ 0`, Spec-Text

**Files:**
- Modify: `swki/pruefung/schleife.py` (`lies_laeufe`, `empfehlung`)
- Modify: `swki/pruefung/befehle.py` (`pruefen`, `einrichten`; neue Hilfen `LaufFehler`, `pruefe_lauf_gebaut`, `_nicht_negativ`)
- Modify: `swki/pruefung/bericht.py` (Spalte „Offen“)
- Modify: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` (§6, zwei Zeilen), `.claude/skills/konstruieren/SKILL.md` (Abschnitt 6 Schleife)
- Test: `tests/pruefung/test_schleife.py`, `tests/pruefung/test_bericht.py`, `tests/pruefung/test_befehle_pruefung.py` (neu)

**Interfaces:**
- Produces: Jeder Eintrag aus `lies_laeufe` bekommt `"vergleichbar": bool` (True genau dann, wenn `bau == "ok"`, ein Prüfbericht vorliegt und ein Prüfer-Urteil vorliegt). `offen` ist bei Bauabbruch `None` (statt 1). `pruefe_lauf_gebaut(protokoll: dict, lauf: int) -> None` wirft `LaufFehler` (Code `LAUF_ABGEBROCHEN`).
- Hinweis: Task 3 ändert `lies_laeufe` erneut (Form-Prüfung des Urteils). Task 3 baut auf diesem Stand auf.

- [ ] **Step 1: Failing tests – `tests/pruefung/test_schleife.py` anpassen und erweitern**

In `test_laeufe_lesen` die Zeile `assert [x["offen"] for x in laeufe] == [1, 3, 0]` ersetzen durch:

```python
    assert [x["offen"] for x in laeufe] == [None, 3, 0]
    assert [x["vergleichbar"] for x in laeufe] == [False, True, True]
```

Die Parametrierung von `test_empfehlung` vollständig ersetzen durch (jedes dict bekommt `vergleichbar`; Bauabbruch hat `offen=None`):

```python
def _l(lauf, bau="ok", code=None, pruefer="ausstehend", offen=None, bestanden=False):
    vergleichbar = bau == "ok" and code is not None and pruefer != "ausstehend"
    return dict(lauf=lauf, bau=bau, code_maengel=code, pruefer=pruefer, offen=offen, bestanden=bestanden,
                vergleichbar=vergleichbar)


@pytest.mark.parametrize(("laeufe", "erwartet"), [
    ([_l(1)], "pruefen"),
    ([_l(1, code=0, offen=0)], "pruefer"),
    ([_l(1, code=0, pruefer="bestanden", offen=0, bestanden=True)], "bestanden"),
    ([_l(1, bau="fehler")], "nachbessern"),
    ([_l(1, code=2, pruefer="maengel", offen=3), _l(2, code=2, pruefer="maengel", offen=3)], "stopp_kein_fortschritt"),
    ([_l(1, code=3, pruefer="maengel", offen=4), _l(2, code=1, pruefer="maengel", offen=2)], "stopp_max"),
])
def test_empfehlung(laeufe, erwartet):
    assert empfehlung(laeufe, 2)[0] == erwartet


def test_bauabbruch_nach_gebautem_lauf_ist_kein_stillstand():
    # Lauf 2 bricht ab: kein Vergleich, nur ein Lauf verbraucht → weiter nachbessern
    laeufe = [_l(1, code=4, pruefer="maengel", offen=5), _l(2, bau="fehler")]
    assert empfehlung(laeufe, 4)[0] == "nachbessern"


def test_gebauter_lauf_nach_bauabbruch_wird_nicht_mit_dem_abbruch_verglichen():
    # Lauf 1 bricht ab, Lauf 2 baut mit 3 Mängeln: früher 1 → 3 = „kein Fortschritt“, jetzt kein Vergleichslauf
    laeufe = [_l(1, bau="fehler"), _l(2, code=2, pruefer="maengel", offen=3)]
    assert empfehlung(laeufe, 4)[0] == "nachbessern"


def test_vergleich_ueberspringt_bauabbrueche():
    # Lauf 1: 5, Lauf 2: Abbruch, Lauf 3: 6 → 6 gegen 5 → Stopp
    laeufe = [_l(1, code=4, pruefer="maengel", offen=5), _l(2, bau="fehler"), _l(3, code=5, pruefer="maengel", offen=6)]
    code, text = empfehlung(laeufe, 4)
    assert code == "stopp_kein_fortschritt"
    assert "Lauf 1" in text and "Lauf 3" in text


def test_ungepruefte_laeufe_zaehlen_nicht_als_vergleich():
    # Lauf 1 gebaut, aber nie vom Prüfer beurteilt → nicht vergleichbar; Lauf 2 ist der erste Vergleichslauf
    laeufe = [_l(1, code=1, offen=1), _l(2, code=2, pruefer="maengel", offen=3)]
    assert empfehlung(laeufe, 4)[0] == "nachbessern"


def test_bauabbrueche_verbrauchen_laeufe():
    laeufe = [_l(1, bau="fehler"), _l(2, bau="fehler")]
    assert empfehlung(laeufe, 2)[0] == "stopp_max"
```

- [ ] **Step 2: Failing tests – `tests/pruefung/test_bericht.py`**

In `LAEUFE` beim ersten Eintrag `"offen": 1` durch `"offen": None` ersetzen und in `test_bestandener_auftrag` die Zusicherung

```python
    assert "| 1 | fehler | – | ausstehend | 1 | 8.1 |" in md
```

ersetzen durch

```python
    assert "| 1 | fehler | – | ausstehend | – | 8.1 |" in md
```

- [ ] **Step 3: Failing tests – `tests/pruefung/test_befehle_pruefung.py` (neu)**

```python
import json

import pytest

from swki.cli import main
from swki.pruefung.befehle import LaufFehler, pruefe_lauf_gebaut


def test_gebauter_lauf_darf_geprueft_werden():
    pruefe_lauf_gebaut({"status": "ok", "fehler": None}, 2)


def test_abgebrochener_lauf_wird_nicht_geprueft():
    protokoll = {"status": "fehler", "fehler": {"code": "SKIZZE_NICHT_BESTIMMT", "meldung": "f3_skizze: Status 2"}}
    with pytest.raises(LaufFehler) as e:
        pruefe_lauf_gebaut(protokoll, 2)
    assert e.value.daten == {"code": "LAUF_ABGEBROCHEN"}
    assert "Lauf 2" in str(e.value) and "SKIZZE_NICHT_BESTIMMT" in str(e.value)


def test_max_darf_nicht_negativ_sein(capsys, tmp_path):
    code = main(["status", str(tmp_path / "platte.yaml"), "--max", "-1"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 1 and "--max" in daten["fehler"]
```

- [ ] **Step 4: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung -q`
Expected: FAIL (`KeyError: 'vergleichbar'`, `ImportError: cannot import name 'LaufFehler'`, Bericht zeigt `None`/`1`).

- [ ] **Step 5: `swki/pruefung/schleife.py`**

In `lies_laeufe` die Zeilen ab `offen = …` bis zum Ende des `laeufe.append({...})` ersetzen durch:

```python
        offen = (code_maengel or 0) + (pruefer_maengel or 0) if bau_ok else None  # Bauabbruch: nicht zählbar
        laeufe.append({
            "lauf": n,
            "bau": protokoll["status"],
            "dauer_s": protokoll["dauer_s"],
            "code_maengel": code_maengel,
            "pruefer": "ausstehend" if urteil is None else ("bestanden" if urteil["bestanden"] else "maengel"),
            "pruefer_maengel": pruefer_maengel,
            "offen": offen,
            "vergleichbar": bau_ok and bericht is not None and urteil is not None,
            "bestanden": bau_ok and bericht is not None and bericht["bestanden"] and urteil is not None
            and urteil["bestanden"],
        })
```

In `empfehlung` den Block

```python
    if len(laeufe) >= 2 and letzter["offen"] >= laeufe[-2]["offen"]:
        return "stopp_kein_fortschritt", (
            f"Offene Mängel {laeufe[-2]['offen']} → {letzter['offen']}: kein Fortschritt, anhalten und Nutzer informieren"
        )
```

ersetzen durch

```python
    # Regel „kein Fortschritt“ (Nutzerentscheidung 2026-10-01, Option A): nur durchgebaute und geprüfte Läufe werden
    # verglichen, jeweils mit dem letzten solchen Lauf davor; ein Bauabbruch verbraucht nur einen Lauf.
    vorher = [lauf for lauf in laeufe[:-1] if lauf["vergleichbar"]]
    if letzter["vergleichbar"] and vorher and letzter["offen"] >= vorher[-1]["offen"]:
        return "stopp_kein_fortschritt", (
            f"Offene Mängel Lauf {vorher[-1]['lauf']} → Lauf {letzter['lauf']}: {vorher[-1]['offen']} → "
            f"{letzter['offen']}: kein Fortschritt, anhalten und Nutzer informieren"
        )
```

Den Modul-Docstring um einen Absatz ergänzen:

```
Regel „kein Fortschritt“: verglichen werden nur Läufe, die durchgebaut und geprüft sind (Prüfbericht und Prüfer-Urteil),
jeweils mit dem letzten solchen Lauf davor. Ein Bauabbruch (Protokollstatus "fehler") hat keine Mängelzahl (offen None)
und verbraucht nur einen der höchstens 1 + max_nachbesserungen Läufe.
```

- [ ] **Step 6: `swki/pruefung/bericht.py`**

In der Läufe-Tabelle `f"| {lauf['offen']} | {lauf['dauer_s']} |"` ersetzen durch `f"| {_zelle(lauf['offen'])} | {lauf['dauer_s']} |"` (`_zelle` gibt für `None` schon „–“ aus; sonst den Wert – im Code nachsehen und, falls `_zelle` anders arbeitet, `'–' if lauf['offen'] is None else lauf['offen']` verwenden).

- [ ] **Step 7: `swki/pruefung/befehle.py`**

Import ergänzen: `import argparse`. Nach den Imports einfügen:

```python
class LaufFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str):
        super().__init__(meldung)
        self.daten = {"code": code}


def pruefe_lauf_gebaut(protokoll: dict, lauf: int) -> None:
    """Ein abgebrochener Bau hinterlässt ein halbes Teil: nicht messen, sondern Bauweg nachbessern (Regel „kein
    Fortschritt“, Option A – der Lauf zählt nur als verbrauchter Lauf)."""
    if protokoll.get("status") != "ok":
        f = protokoll.get("fehler") or {}
        raise LaufFehler(
            "LAUF_ABGEBROCHEN",
            f"Lauf {lauf} ist beim Bau abgebrochen ({f.get('code')}: {f.get('meldung')}) – nicht prüfen, "
            "Bauweg nachbessern und neu bauen",
        )


def _nicht_negativ(text: str) -> int:
    wert = int(text)
    if wert < 0:
        raise argparse.ArgumentTypeError(f"--max muss ≥ 0 sein (ist {wert})")
    return wert
```

In `pruefen` die Zeile `protokoll = json.loads(…)` vor `app = verbinde(r.sw_jahr)` ziehen und direkt danach `pruefe_lauf_gebaut(protokoll, lauf)` aufrufen:

```python
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    pruefe_lauf_gebaut(protokoll, lauf)
    app = verbinde(r.sw_jahr)
```

In `einrichten` beim Befehl `status`: `p.add_argument("--max", type=_nicht_negativ, help=…)` (Hilfetext bleibt).

- [ ] **Step 8: Spec-Text und Skill**

`docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` §6: die zwei Zeilen

```
- Maximale Läufe: Spezifikation > Anweisung im Chat > `config/standard.yaml` (Vorgabe 3).
- Abbruch ohne Fortschritt: sinkt die Zahl offener Mängel gegenüber dem Vorlauf nicht, stoppt
  Claude und meldet sich.
```

ersetzen durch

```
- Maximale Nachbesserungen: Spezifikation > Anweisung im Chat > `config/standard.yaml` (Vorgabe 3), also höchstens
  1 + 3 = 4 Läufe.
- Abbruch ohne Fortschritt: sinkt die Zahl offener Mängel gegenüber dem letzten durchgebauten und geprüften Lauf nicht,
  stoppt Claude und meldet sich. Ein Bauabbruch wird nicht verglichen und verbraucht nur einen Lauf; `swki pruefen`
  verweigert einen abgebrochenen Lauf (LAUF_ABGEBROCHEN). (Nutzerentscheidung 2026-10-01)
```

`.claude/skills/konstruieren/SKILL.md`, Abschnitt „## 6. Schleife“: nach dem Punkt `nachbessern: …` ergänzen:

```markdown
  - Bauabbruch (`swki bauen` meldet `status: fehler`): nicht `swki pruefen` (verweigert mit LAUF_ABGEBROCHEN), sondern
    direkt den Bauweg nachbessern und neu bauen. Ein Abbruch verbraucht einen Lauf, wird aber nicht als Mängelzahl
    verglichen; „kein Fortschritt“ vergleicht nur durchgebaute und geprüfte Läufe (höchstens 1 + 3 = 4 Läufe).
```

- [ ] **Step 9: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung -q` → alle grün.
Run: `.venv\Scripts\python.exe -m pytest -q` → 276 + 8 = **284 passed** (5 neue Schleifentests, 3 in `test_befehle_pruefung.py`).

- [ ] **Step 10: Commit**

```powershell
git add swki/pruefung/schleife.py swki/pruefung/befehle.py swki/pruefung/bericht.py docs/superpowers/specs/2026-09-26-solidworks-ki-design.md .claude/skills/konstruieren/SKILL.md tests/pruefung/test_schleife.py tests/pruefung/test_bericht.py tests/pruefung/test_befehle_pruefung.py
git commit -m "pruefung: Bauabbruch nicht vergleichen, abgebrochenen Lauf nicht pruefen, --max >= 0" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Freigabe und Bauen – Kopie nicht freigeben, Pfad der Kopie ausgeben, vorhandenen Lauf nicht überschreiben

**Files:**
- Modify: `swki/spec/befehle.py` (`_freigeben`), `swki/auftrag.py` (+ `lauf_belegt`), `swki/compiler/bauen.py` (`bauen`)
- Test: `tests/spec/test_befehle.py`, `tests/test_auftrag.py`

**Interfaces:**
- Produces: `lauf_belegt(r: Rechner, auftrag: str, spec_pfad: Path, lauf: int) -> bool` in `swki/auftrag.py`. `swki freigeben` liefert zusätzlich `"kopie": "<Pfad der .freigegeben.yaml>"`. Ein Fehler beim Freigeben der Kopie hat den Code `FREIGABE_KOPIE`.

- [ ] **Step 1: Failing tests – `tests/spec/test_befehle.py` anhängen**

```python
def test_freigeben_nennt_die_kopie(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "freigeben", str(pfad))
    assert code == 0 and daten["kopie"] == str(tmp_path / "platte.freigegeben.yaml")


def test_freigabe_kopie_wird_nicht_freigegeben(capsys, tmp_path):
    pfad = tmp_path / "platte.freigegeben.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "freigeben", str(pfad))
    assert code == 1 and daten["code"] == "FREIGABE_KOPIE"
    assert "platte.yaml" in daten["fehler"]
    assert not (tmp_path / "freigabe.json").exists()
```

- [ ] **Step 2: Failing tests – `tests/test_auftrag.py` anhängen** (Import `lauf_belegt` in die Importzeile aufnehmen)

```python
def test_lauf_belegt(tmp_path):
    r = _rechner(tmp_path)
    spec = tmp_path / "auftraege" / "A" / "platte.yaml"
    assert not lauf_belegt(r, "A", spec, 1)
    lauf_ordner(r, "A", 1).mkdir(parents=True)
    assert lauf_belegt(r, "A", spec, 1)
    datei = lauf_datei(spec, 2, "protokoll")
    datei.parent.mkdir(parents=True)
    datei.write_text("{}", encoding="utf-8")
    assert lauf_belegt(r, "A", spec, 2)
```

- [ ] **Step 3: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_befehle.py tests/test_auftrag.py -q`
Expected: FAIL (`KeyError: 'kopie'`, Freigabe der Kopie gelingt, `ImportError: lauf_belegt`).

- [ ] **Step 4: `swki/spec/befehle.py`**

Imports: `from swki.spec.freigabe import FreigabeFehler, freigeben, kopie_pfad, pruefsumme`. `_freigeben` ersetzen:

```python
_KOPIE_ENDUNG = ".freigegeben.yaml"


def _freigeben(args) -> dict:
    pfad = Path(args.spec)
    if pfad.name.endswith(_KOPIE_ENDUNG):
        original = pfad.name.removesuffix(_KOPIE_ENDUNG) + ".yaml"
        raise FreigabeFehler("FREIGABE_KOPIE", f"{pfad.name} ist die Freigabe-Kopie; freigegeben wird die "
                                               f"Spezifikation selbst ({original})")
    spec = lade_spec(pfad)
    return {"spec": str(pfad), "kopie": str(kopie_pfad(pfad)), **freigeben(pfad, spec)}
```

- [ ] **Step 5: `swki/auftrag.py`** – nach `lauf_datei` einfügen:

```python
def lauf_belegt(r: Rechner, auftrag: str, spec_pfad: Path, lauf: int) -> bool:
    """Gibt es zu diesem Lauf schon einen Arbeitsordner oder ein Protokoll im Auftragsordner?"""
    return lauf_ordner(r, auftrag, lauf).exists() or lauf_datei(spec_pfad, lauf, "protokoll").exists()
```

- [ ] **Step 6: `swki/compiler/bauen.py`**

Import `lauf_belegt` aus `swki.auftrag` ergänzen und `SwkiFehler` aus `swki.cli` (falls nicht schon importiert). In `bauen` die Zeile `lauf = lauf or naechster_lauf(r, auftrag)` ersetzen durch:

```python
    if lauf is not None and lauf_belegt(r, auftrag, spec_pfad, lauf):
        raise SwkiFehler(f"Lauf {lauf} von {auftrag} existiert schon – ohne --lauf baut swki den nächsten freien Lauf")
    lauf = lauf or naechster_lauf(r, auftrag)
```

Die Prüfung steht vor `verbinde` (kein SolidWorks nötig, um den Fehler zu melden).

- [ ] **Step 7: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → 284 + 3 = **287 passed**.

- [ ] **Step 8: Commit**

```powershell
git add swki/spec/befehle.py swki/auftrag.py swki/compiler/bauen.py tests/spec/test_befehle.py tests/test_auftrag.py
git commit -m "befehle: Freigabe-Kopie nicht freigeben, Pfad der Kopie ausgeben, vorhandenen Lauf nicht ueberschreiben" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Prüfer-Urteil auf Form prüfen, git-Fehler im Bericht abfangen, `speichere` nur im Arbeitsordner

**Files:**
- Modify: `swki/pruefung/schleife.py` (`lies_laeufe`, neu `pruefe_urteil`), `swki/pruefung/befehle.py` (`_compiler_aenderungen`), `swki/compiler/sw.py` (`speichere`)
- Test: `tests/pruefung/test_schleife.py`, `tests/pruefung/test_befehle_pruefung.py`, `tests/compiler/test_sw.py`

**Interfaces:**
- Consumes: Stand von `lies_laeufe` aus Task 1 (`vergleichbar`, `offen None`).
- Produces: `pruefe_urteil(urteil, pfad: Path) -> None` wirft `SwkiFehler` mit `daten = {"code": "PRUEFER_URTEIL_UNGUELTIG"}`.

- [ ] **Step 1: Failing tests – `tests/pruefung/test_schleife.py`**

Im Helfer `_lauf` die Prüfer-Mängel als gültige Einträge schreiben – Zeile ersetzen durch:

```python
        _schreibe(spec_pfad, n, "pruefer", {"bestanden": not pruefer,
                                            "maengel": [{"knoten": [], "beschreibung": "x"}] * pruefer})
```

Anhängen (Import `pruefe_urteil` ergänzen, außerdem `from swki.cli import SwkiFehler`):

```python
@pytest.mark.parametrize("urteil", [
    {"bestanden": True, "maengel": []},
    {"bestanden": False, "maengel": [{"knoten": ["f2"], "beschreibung": "Fase fehlt"}]},
])
def test_gueltiges_urteil(urteil, tmp_path):
    pruefe_urteil(urteil, tmp_path / "x.pruefer.json")


@pytest.mark.parametrize("urteil", [
    [],                                                    # kein Objekt
    {"bestanden": "ja", "maengel": []},                    # bestanden kein bool
    {"bestanden": False},                                  # maengel fehlt
    {"bestanden": False, "maengel": [{"knoten": "f2", "beschreibung": "x"}]},  # knoten keine Liste
    {"bestanden": False, "maengel": [{"knoten": []}]},     # beschreibung fehlt
])
def test_ungueltiges_urteil(urteil, tmp_path):
    with pytest.raises(SwkiFehler) as e:
        pruefe_urteil(urteil, tmp_path / "platte.lauf-1.pruefer.json")
    assert e.value.daten == {"code": "PRUEFER_URTEIL_UNGUELTIG"}
    assert "platte.lauf-1.pruefer.json" in str(e.value)


def test_lies_laeufe_meldet_ungueltiges_urteil(tmp_path):
    spec = tmp_path / "platte.yaml"
    _lauf(spec, 1, code=0)
    _schreibe(spec, 1, "pruefer", {"ok": True})
    with pytest.raises(SwkiFehler):
        lies_laeufe(spec)
```

- [ ] **Step 2: Failing tests – `tests/pruefung/test_befehle_pruefung.py` anhängen**

```python
import subprocess

from swki.pruefung import befehle


def test_compiler_aenderungen_ohne_git(monkeypatch):
    def kein_git(*a, **k):
        raise FileNotFoundError("git")
    monkeypatch.setattr(befehle.subprocess, "run", kein_git)
    [zeile] = befehle._compiler_aenderungen("2026-10-01T10:00:00")
    assert zeile.startswith("(git nicht ausführbar")


def test_compiler_aenderungen_git_fehler(monkeypatch):
    monkeypatch.setattr(befehle.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 128, stdout="", stderr="fatal: kein Repo"))
    assert befehle._compiler_aenderungen("2026-10-01T10:00:00") == ["(git log fehlgeschlagen: fatal: kein Repo)"]
```

(Die Imports `import subprocess` und `from swki.pruefung import befehle` an den Dateianfang zu den übrigen Imports stellen.)

- [ ] **Step 3: Failing tests – `tests/compiler/test_sw.py` anhängen**

```python
from types import SimpleNamespace

from swki.compiler import sw
from swki.compiler.fehler import BauFehler


class _FakeExtension:
    def __init__(self):
        self.gespeichert = []

    def SaveAs3(self, pfad, version, optionen, a, b, fehler, warnungen):
        self.gespeichert.append(pfad)
        return True


def test_speichere_nur_im_arbeitsordner(monkeypatch, tmp_path):
    monkeypatch.setattr(sw, "lade_rechner", lambda: SimpleNamespace(arbeitsordner=tmp_path / "arbeit"))
    with pytest.raises(BauFehler) as e:
        sw.speichere(None, tmp_path / "kunde" / "teil.sldprt")
    assert "Arbeitsordner" in str(e.value)
    assert not (tmp_path / "kunde").exists()


def test_speichere_im_arbeitsordner(monkeypatch, tmp_path):
    monkeypatch.setattr(sw, "lade_rechner", lambda: SimpleNamespace(arbeitsordner=tmp_path / "arbeit"))
    model = SimpleNamespace(Extension=_FakeExtension())
    ziel = tmp_path / "arbeit" / "A" / "lauf-1" / "teil.sldprt"
    sw.speichere(model, ziel)
    assert model.Extension.gespeichert == [str(ziel)]
```

- [ ] **Step 4: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung tests/compiler/test_sw.py -q`
Expected: FAIL (`ImportError: pruefe_urteil`, `FileNotFoundError` nicht abgefangen, `AttributeError: lade_rechner`).

- [ ] **Step 5: `swki/pruefung/schleife.py`**

Import `from swki.cli import SwkiFehler` ergänzen. Vor `lies_laeufe` einfügen:

```python
_URTEIL_FORM = '{"bestanden": bool, "maengel": [{"knoten": [...], "beschreibung": "..."}]}'


def pruefe_urteil(urteil, pfad: Path) -> None:
    """Form des Prüfer-Urteils (vom Controller abgelegtes JSON des Prüfer-Agenten)."""
    maengel = urteil.get("maengel") if isinstance(urteil, dict) else None
    gueltig = (
        isinstance(urteil, dict) and isinstance(urteil.get("bestanden"), bool) and isinstance(maengel, list)
        and all(isinstance(m, dict) and isinstance(m.get("knoten"), list) and isinstance(m.get("beschreibung"), str)
                for m in maengel)
    )
    if not gueltig:
        fehler = SwkiFehler(f"{pfad.name}: kein gültiges Prüfer-Urteil – erwartet {_URTEIL_FORM}")
        fehler.daten = {"code": "PRUEFER_URTEIL_UNGUELTIG"}
        raise fehler
```

In `lies_laeufe` direkt nach `urteil = _lies(lauf_datei(spec_pfad, n, "pruefer"))` einfügen:

```python
        if urteil is not None:
            pruefe_urteil(urteil, lauf_datei(spec_pfad, n, "pruefer"))
```

- [ ] **Step 6: `swki/pruefung/befehle.py` – `_compiler_aenderungen` ersetzen**

```python
def _compiler_aenderungen(seit: str) -> list[str]:
    """Commits an Compiler und Schema seit dem ersten Lauf; ohne git eine Hinweiszeile statt eines Abbruchs."""
    try:
        ergebnis = subprocess.run(
            ["git", "log", f"--since={seit}", "--format=%h %s", "--", "swki/compiler", "schema"],
            cwd=PROJEKT, capture_output=True, text=True, encoding="utf-8",
        )
    except OSError as e:
        return [f"(git nicht ausführbar: {e})"]
    if ergebnis.returncode != 0:
        return [f"(git log fehlgeschlagen: {ergebnis.stderr.strip() or ergebnis.returncode})"]
    return [z for z in ergebnis.stdout.splitlines() if z.strip()]
```

- [ ] **Step 7: `swki/compiler/sw.py` – `speichere`**

Import `from swki.konfig import lade_rechner` zu den übrigen Imports (auf Zirkelimport achten: `swki.konfig` importiert `swki.compiler` nicht – prüfen). Am Anfang von `speichere` (vor `pfad.parent.mkdir`) einfügen:

```python
    arbeit = lade_rechner().arbeitsordner.resolve()
    if not pfad.resolve().is_relative_to(arbeit):
        raise BauFehler(SPEICHERN_FEHLGESCHLAGEN, f"{pfad} liegt nicht im Arbeitsordner {arbeit} (CLAUDE.md)",
                        schritt="speichern")
```

Den Docstring um „Gespeichert wird nur im Arbeitsordner aus config/rechner.yaml.“ ergänzen.

- [ ] **Step 8: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → 287 + 12 = **299 passed** (2 + 5 + 1 Urteil, 2 git, 2 speichere).

- [ ] **Step 9: Commit**

```powershell
git add swki/pruefung/schleife.py swki/pruefung/befehle.py swki/compiler/sw.py tests/pruefung/test_schleife.py tests/pruefung/test_befehle_pruefung.py tests/compiler/test_sw.py
git commit -m "pruefung/compiler: Pruefer-Urteil auf Form pruefen, git-Fehler abfangen, nur im Arbeitsordner speichern" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Validierung – reservierte IDs, Normbohrung (doppelte Positionen, Tiefe vs. Senkung), Kreissektor-Kontur, Ausdrucksfehler-Tests

**Files:**
- Modify: `swki/spec/laden.py` (`plausibel_befunde`, `_normbohrung_befunde`, `_kontur_befunde`, Konstanten)
- Test: `tests/spec/test_laden.py`

**Interfaces:**
- Consumes: `normmasse(art, groesse, norm)` aus `swki/spec/normen.py` (Felder `senkung_t` bei zylinderschraube, `durchgang`/`senkung_d`/`senkwinkel` bei senkschraube).
- Produces: neue Befunde, die `validieren` ablehnt.

- [ ] **Step 1: Failing tests – `tests/spec/test_laden.py` anhängen**

(Die Helfer `_spec`, `_mit_feature`, `_mit_element` und `NB` gibt es dort schon.)

```python
@pytest.mark.parametrize("fid", ["achse_x", "f1_skizze", "f2_senkung", "f3_positionen"])
def test_reservierte_ids(tmp_path, fid):
    spec = _spec()
    spec["features"][1] = spec["features"][1] | {"id": fid}
    spec["pruefung"]["masse_pruefen"] = []
    befunde = plausibel_befunde(spec, tmp_path)
    assert any(b["pfad"] == "features[1].id" and "reserviert" in b["meldung"] for b in befunde)


def test_id_eines_skript_zusatzfeatures_ist_reserviert(tmp_path):
    spec = _spec()
    skript = {"id": "f7", "typ": "skript", "datei": "f7.py", "luecke": "Test"}
    spec["features"] += [skript, {**spec["features"][3], "id": "f7_2"}]
    (tmp_path / "f7.py").write_text("def baue(ctx):\n    pass\n", encoding="utf-8")
    befunde = plausibel_befunde(spec, tmp_path)
    assert any(b["pfad"] == "features[7].id" and "reserviert" in b["meldung"] for b in befunde)


def test_normbohrung_doppelte_position(tmp_path):
    nb = NB | {"positionen": [["=-L/2+20", 0], [-30, 0]]}  # L = 100 → beide bei u = −30
    [befund] = plausibel_befunde(_mit_feature(nb), tmp_path)
    assert befund["pfad"] == "features[1].positionen[1]" and "doppelt" in befund["meldung"]


@pytest.mark.parametrize(("art", "groesse", "tiefe", "ok"), [
    ("zylinderschraube", "M8", 8, False),   # Senktiefe M8 laut Tabelle 8,6 mm
    ("zylinderschraube", "M8", 20, True),
    ("senkschraube", "M6", 3, False),       # Kegelhöhe M6: (13,44 − 6,6) / 2 / tan 45° = 3,42 mm
    ("senkschraube", "M6", 10, True),
])
def test_normbohrung_tiefe_gegen_senkung(tmp_path, art, groesse, tiefe, ok):
    nb = {k: v for k, v in NB.items() if k != "durch"} | {"art": art, "groesse": groesse, "tiefe": tiefe}
    befunde = plausibel_befunde(_mit_feature(nb), tmp_path)
    assert (befunde == []) is ok
    if not ok:
        assert befunde[0]["pfad"] == "features[1].tiefe" and "Senk" in befunde[0]["meldung"]


def test_kontur_kreissektor_wird_abgelehnt(tmp_path):
    # Viertelkreis: Mittelpunkt (0, 0) ist zugleich Eckpunkt der Kontur
    kontur = {"start": [0, 0], "segmente": [{"linie": [20, 0]}, {"bogen": [0, 20], "mitte": [0, 0]}, {"linie": [0, 0]}]}
    [befund] = plausibel_befunde(_mit_element({"kontur": kontur}), tmp_path)
    assert befund["pfad"] == "features[0].skizze.elemente[0].kontur.segmente[1]"
    assert "Konturpunkt" in befund["meldung"]


@pytest.mark.parametrize("element", [
    {"polygon": {"punkte": [[0, 0], [40, 0], [40, 40], [0, 40]], "radien": "=X"}},
    {"kontur": {"start": [0, 0], "segmente": [{"linie": ["=X", 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                              {"linie": [0, 30]}, {"linie": [0, 0]}]}},
])
def test_ausdrucksfehler_in_rundungen_genau_ein_befund(tmp_path, element):
    [befund] = plausibel_befunde(_mit_element(element), tmp_path)
    assert "unbekannter Parameter 'X'" in befund["meldung"]


def test_ausdrucksfehler_in_gewindetiefe_genau_ein_befund(tmp_path):
    nb = {k: v for k, v in NB.items() if k != "durch"} | {"art": "gewinde", "groesse": "M10", "tiefe": 16,
                                                         "gewindetiefe": "=X"}
    [befund] = plausibel_befunde(_mit_feature(nb), tmp_path)
    assert "unbekannter Parameter 'X'" in befund["meldung"]
```

Hinweis für den Implementer: Prüfe vor dem Schreiben, wie `_mit_feature`/`_mit_element` und `GUELTIG` (`tests/spec/beispiel.py`) aussehen. Der Index `features[1]` in `test_reservierte_ids` ist die Bohrung `f2` aus `GUELTIG`; `masse_pruefen` wird geleert, weil die Prüfung auf `f2` verweist. In `test_id_eines_skript_zusatzfeatures_ist_reserviert` ist `features[7]` der zweite angehängte Knoten. Passt ein Index nicht zur tatsächlichen Liste, den Index korrigieren, nicht die Erwartung an den Befund. Das Skript braucht eine Datei, die `pruefe_skript` ohne Befund durchlässt. Ist `def baue(ctx): pass` dafür nicht gültig, eine gültige Minimaldatei aus `tests/referenz/formplatte/` als Vorlage nehmen.

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_laden.py -q`
Expected: FAIL bei den neuen Fällen außer den drei Ausdrucksfehler-Tests (die dokumentieren bestehendes Verhalten und dürfen schon grün sein – im Bericht nennen).

- [ ] **Step 3: `swki/spec/laden.py`**

Import `import re` zu den Standard-Imports. Konstanten nach `_TOL_KONTUR_MM` ergänzen:

```python
_RESERVIERT = re.compile(r"^achse_[xyz]$")  # Referenzachsen der Muster (handler/muster.py)
_COMPILER_ENDUNGEN = ("_skizze", "_senkung", "_positionen")  # vom Compiler angelegte Skizzen/Features
```

In `plausibel_befunde` direkt nach der Schleife über doppelte IDs einfügen:

```python
    skripte = [f["id"] for f in features if f["typ"] == "skript"]
    for i, fid in enumerate(ids):
        zusatz = any(re.fullmatch(rf"{re.escape(s)}_\d+", fid) for s in skripte)  # weitere Features eines Skripts
        if _RESERVIERT.match(fid) or fid.endswith(_COMPILER_ENDUNGEN) or zusatz:
            befunde.append({"pfad": f"features[{i}].id",
                            "meldung": f"ID {fid!r} ist für vom Compiler angelegte Features reserviert "
                                       "(achse_x|y|z, <id>_skizze, <id>_senkung, <id>_positionen, <skript-id>_<n>)"})
```

In `_kontur_befunde` innerhalb der Schleife über die Segmente, direkt nach `mitte = (…)`, einfügen:

```python
        if any(_abstand2(mitte, q) <= _TOL_KONTUR_MM for q in punkte):
            befunde.append({"pfad": f"{pfad}.segmente[{k}]",
                            "meldung": "Bogenmittelpunkt liegt auf einem Konturpunkt (Kreissektor) – wird nicht "
                                       "unterstützt; Kontur anders aufteilen"})
            continue
```

`_normbohrung_befunde` am Ende (vor `return befunde`) erweitern:

```python
    try:
        pos = [(auswerten(u, p), auswerten(v, p)) for u, v in f["positionen"]]
        for k, q in enumerate(pos):
            gleich = next((j for j in range(k) if _abstand2(pos[j], q) <= _TOL_KONTUR_MM), None)
            if gleich is not None:
                befunde.append({"pfad": f"{pfad}.positionen[{k}]",
                                "meldung": f"Position {k + 1} ist doppelt (gleich Position {gleich + 1})"})
        masse = normmasse(f["art"], f["groesse"], norm)
        if "tiefe" in f and masse is not None:
            tiefe = auswerten(f["tiefe"], p)
            if f["art"] == "zylinderschraube":
                grenze, was = masse["senkung_t"], "Senktiefe"
            elif f["art"] == "senkschraube":
                grenze = (masse["senkung_d"] - masse["durchgang"]) / 2 / math.tan(math.radians(masse["senkwinkel"]) / 2)
                was = "Senkungshöhe"
            else:
                grenze = None
            if grenze is not None and tiefe <= grenze:
                befunde.append({"pfad": f"{pfad}.tiefe",
                                "meldung": f"tiefe {tiefe:g} muss größer als die {was} ({grenze:.4g} mm) sein"})
    except AusdruckFehler:
        pass  # bereits oben gemeldet
```

(`norm` ist am Anfang der Funktion schon gesetzt; `math` ist importiert.)

- [ ] **Step 4: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/spec -q` → grün.
Run: `.venv\Scripts\python.exe -m pytest -q` → 299 + 14 = **313 passed** (4 reserviert, 1 Skript, 1 doppelt, 4 Tiefe, 1 Kreissektor, 2 + 1 Ausdrucksfehler).
Run: `.venv\Scripts\python.exe -m swki validieren tests\referenz\auswerferhalteplatte\auswerferhalteplatte.yaml` (und `buchse/buchse.yaml`, `formplatte/formplatte_ds.yaml`) → jeweils `"gueltig": true`.

- [ ] **Step 5: Commit**

```powershell
git add swki/spec/laden.py tests/spec/test_laden.py
git commit -m "spec: reservierte IDs, Normbohrung doppelte Positionen und Tiefe gegen Senkung, Kreissektor-Kontur" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Hinweise – keine Fehlalarme bei `feste_zahl`, Sammelhinweis für Konturpunkte, Texte Regel 3, Randzweige testen

**Files:**
- Modify: `swki/spec/hinweise.py` (`feste_masse`, `zusammenfassen`)
- Test: `tests/spec/test_hinweise.py`

**Interfaces:**
- Produces: `feste_masse` meldet nicht mehr: alles unter `mittellinie`, `winkel` = 360, `winkel` = 45 bei `typ: fase`. Für `polygon.punkte` und ein ganzes `kontur`-Element gibt es **einen** Sammelhinweis (`pfad` = …`.punkte` bzw. …`.kontur`, Meldung „n feste Zahlen …“). Alle Meldungen zu Regel 3 enthalten weiter „Regel 3“.

- [ ] **Step 1: Failing tests – `tests/spec/test_hinweise.py` anhängen**

```python
def _rotation(**skizze):
    return {"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[0, 0], ["=R", 0], ["=R", "=H"], [0, "=H"]]}},
        {"mittellinie": {"von": [0, -5], "bis": [0, 5]}}, *skizze.get("weitere", [])]}}


def test_mittellinie_ist_kein_anforderungsmass():
    assert feste_masse({"features": [_rotation()]}) == []


def test_vollkreis_und_standardfase_sind_keine_hinweise():
    spec = {"features": [
        {"id": "f1", "typ": "muster_kreis", "features": ["f0"], "achse": "y", "anzahl": 6, "winkel": 360},
        {"id": "f2", "typ": "fase", "kanten": [{"nahe": [0, 0, 0]}], "abstand": "=F", "winkel": 45},
        {"id": "f3", "typ": "fase", "kanten": [{"nahe": [1, 0, 0]}], "abstand": "=F", "winkel": 30},
    ]}
    assert [h["pfad"] for h in feste_masse(spec)] == ["features[2].winkel"]


def test_polygonpunkte_als_ein_sammelhinweis():
    spec = {"features": [{"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"polygon": {"punkte": [[15, 40], [17, 40], [17, 43], [15, 43]]}}]}, "ende": {"typ": "blind", "tiefe": "=T"}}]}
    [h] = feste_masse(spec)
    assert h["pfad"] == "features[0].skizze.elemente[0].polygon.punkte"
    assert h["meldung"].startswith("8 feste Zahlen")


def test_kontur_als_ein_sammelhinweis():
    kontur = {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                            {"linie": [0, 30]}, {"linie": [0, 0]}]}
    spec = {"features": [{"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"kontur": kontur}]}, "ende": {"typ": "blind", "tiefe": "=T"}}]}
    [h] = feste_masse(spec)
    assert h["pfad"] == "features[0].skizze.elemente[0].kontur"
    assert h["meldung"].startswith("6 feste Zahlen")  # 40, 40, 30, 40, 15, 30 (Nullen zählen nicht)


def test_muster_mit_ausdruecken_kein_hinweis():
    spec = {"features": [
        _bohrung("f1"),
        {"id": "f2", "typ": "muster_linear", "features": ["f1"], "richtung1": {"achse": "x", "abstand": 20, "anzahl": 2},
         "richtung2": {"achse": "z", "abstand": "=A", "anzahl": 2}},
        {"id": "f3", "typ": "muster_kreis", "features": ["f1"], "achse": "y", "anzahl": 4, "winkel": "=W"},
    ]}
    assert zusammenfassen(spec) == []


def test_kreismuster_text_nennt_anzahl_als_zahl():
    spec = {"features": [_bohrung("f1"), {"id": "f2", "typ": "muster_kreis", "features": ["f1"], "achse": "y",
                                          "anzahl": 4}]}
    [h] = zusammenfassen(spec)
    assert "Regel 3" in h["meldung"] and "Anzahl ist immer eine Zahl" in h["meldung"]


def test_senkung_ohne_iso_treffer_und_mit_ausdrucksfehler():
    spec = {"parameter": {}, "features": [
        _bohrung("f1", durchmesser=9, senkung={"durchmesser": 16, "tiefe": 5}),      # Senkung passt zu keiner Größe
        _bohrung("f2", durchmesser="=X", senkung={"durchmesser": 15, "tiefe": 5}),   # unbekannter Parameter
    ]}
    assert [h for h in zusammenfassen(spec) if "ISO 4762" in h["meldung"]] == []
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_hinweise.py -q`
Expected: FAIL bei Mittellinie, Vollkreis/Fase, Sammelhinweisen und Kreismuster-Text; die Tests für Ausdrücke und den ISO-Negativfall dokumentieren bestehendes Verhalten und dürfen schon grün sein.

- [ ] **Step 3: `swki/spec/hinweise.py` – `feste_masse` ersetzen**

```python
_KEINE_MASSE = _ANKER | {"mittellinie"}  # Rotationsachse: Konstruktionslinie, kein Anforderungsmaß
_SAMMELN = frozenset({"punkte", "kontur"})  # viele Koordinaten einer Kontur → ein Hinweis statt einer je Zahl


def _feste_zahlen(wert) -> int:
    if isinstance(wert, dict):
        return sum(_feste_zahlen(v) for v in wert.values())
    if isinstance(wert, list):
        return sum(_feste_zahlen(v) for v in wert)
    return int(isinstance(wert, (int, float)) and not isinstance(wert, bool) and wert != 0)


def _standardwert(feature_typ: str, schluessel: str, wert) -> bool:
    """Werte, die keine Anforderung tragen: Vollkreis 360° (Muster, Rotation), Fase 45°."""
    return schluessel == "winkel" and (wert == 360 or (feature_typ == "fase" and wert == 45))


def feste_masse(spec: dict) -> list[dict]:
    """Feste Zahlen ≠ 0 in maßtragenden Feldern der Features als [{"art", "pfad", "meldung"}] (0 = Lage auf Achse/Ebene).
    Konturen (polygon.punkte, kontur) ergeben je Element einen Sammelhinweis; Mittellinien, 360° und Fase 45° nie."""
    hinweise = []

    def melde(pfad: str, meldung: str) -> None:
        hinweise.append({"art": "feste_zahl", "pfad": pfad, "meldung": meldung})

    def gehe(wert, pfad: str, mass: bool, typ: str) -> None:
        if isinstance(wert, dict):
            for k, v in wert.items():
                if k in _KEINE_MASSE or _standardwert(typ, k, v):
                    continue
                if k in _SAMMELN:
                    if n := _feste_zahlen(v):
                        melde(f"{pfad}.{k}", f"{n} feste Zahlen in {k}: als Parameter führen, wenn die Kontur eine "
                                             "Anforderung ist, sonst deckt die Freigabe sie nicht ab")
                    continue
                gehe(v, f"{pfad}.{k}", mass or k in MASS_FELDER, typ)
        elif isinstance(wert, list):
            for i, v in enumerate(wert):
                gehe(v, f"{pfad}[{i}]", mass, typ)
        elif mass and isinstance(wert, (int, float)) and not isinstance(wert, bool) and wert != 0:
            melde(pfad, f"feste Zahl {wert:g}: als Parameter führen, sonst deckt die Freigabe dieses Maß nicht ab")

    for i, feature in enumerate(spec.get("features", [])):
        gehe(feature, f"features[{i}]", False, feature.get("typ", ""))
    return hinweise
```

(`_ANKER` bleibt wie bisher definiert.)

- [ ] **Step 4: `zusammenfassen` – Texte je Typ**

Den Block mit `ergebnis.append(_hinweis([(i, f)], f"{f['typ']} mit festen Zahlen: …"))` ersetzen durch:

```python
        if fest:
            ergebnis.append(_hinweis([(i, f)], _REGEL_3[f["typ"]]))
```

und vor `zusammenfassen` definieren:

```python
_REGEL_3 = {
    "muster_linear": "muster_linear mit festen Abständen: Positionen direkt angeben, außer Anzahl und Abstand sind "
                     "Anforderungen – dann den Abstand als Parameter (Regel 3)",
    "muster_kreis": "muster_kreis mit festem Winkel: Positionen direkt angeben, außer die Teilung ist eine Anforderung – "
                    "dann den Winkel als Parameter; die Anzahl ist immer eine Zahl (Regel 3)",
    "spiegeln": "spiegeln nur von Bohrungen: Positionen direkt angeben, außer die Symmetrie ist eine Anforderung "
                "(Regel 3)",
}
```

- [ ] **Step 5: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/spec -q` → grün (die bestehenden Tests `test_feste_masse_im_beispiel`, `test_verschachtelte_masse`, `test_muster_und_spiegeln_mit_festen_zahlen` bleiben unverändert grün).
Run: `.venv\Scripts\python.exe -m pytest -q` → 313 + 7 = **320 passed**.
Run: `.venv\Scripts\python.exe -m swki validieren tests\referenz\buchse\buchse.yaml` → statt 14 jetzt 5 `feste_zahl`-Hinweise (zwei `abstand`, Sammelhinweis Polygon, `positionen`, `durchmesser`) – keine Mittellinien – plus `zusammenfassen` für `f6`. Im Bericht die tatsächliche Liste nennen.

- [ ] **Step 6: Commit**

```powershell
git add swki/spec/hinweise.py tests/spec/test_hinweise.py
git commit -m "spec: Hinweise ohne Fehlalarme (Mittellinie, 360, Fase 45), Sammelhinweis Konturpunkte, Texte Regel 3" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Sollvolumen für Rotation (Rechteck, Kreis, mehrere Profile) und Code-Pflege (`eckradien_roh`, Konstanten)

**Files:**
- Modify: `swki/pruefung/geometrie.py` (`_pappus`, Zweig `rotation` in `volumen_auto`)
- Modify: `swki/spec/konturen.py` (+ `eckradien_roh`), `swki/compiler/skizze.py` (Polygonradien)
- Modify: `swki/spec/normen.py` (+ 3 Konstanten), `swki/compiler/handler/normbohrung.py`, `swki/pruefung/bewertung.py` (Konstanten von dort importieren)
- Test: `tests/pruefung/test_geometrie.py`, `tests/spec/test_konturen.py`

**Interfaces:**
- Produces: `eckradien_roh(polygon: dict) -> list` (Rohwerte, Zahl oder Ausdruck, je Ecke); `normen.SW_FM_HOLE_WZD = 25`, `normen.SW_BEFESTIGUNG_STIFT_DURCH = -1`, `normen.SW_LOCH_DURCH = 25`. `_pappus(f, p) -> float | None` (None = mehrere Profile).

- [ ] **Step 1: Failing tests – `tests/pruefung/test_geometrie.py` anhängen**

```python
def _drehteil(*elemente):
    return {"features": [{"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        *elemente, {"mittellinie": {"von": [0, -10], "bis": [0, 10]}}]}}]}


def test_rotation_rechteck():
    # Ring: Querschnitt 10 × 20, Schwerpunkt 15 mm von der Achse
    spec = _drehteil({"rechteck": {"mitte": [15, 0], "breite": 10, "hoehe": 20}})
    assert volumen_auto(spec)[0] == pytest.approx(200 * 2 * math.pi * 15)


def test_rotation_kreis():
    # Torus: Kreis Ø4 im Abstand 20
    spec = _drehteil({"kreis": {"mitte": [20, 0], "durchmesser": 4}})
    assert volumen_auto(spec)[0] == pytest.approx(math.pi * 4 * 2 * math.pi * 20)


def test_rotation_mit_mehreren_profilen_nicht_berechenbar():
    spec = _drehteil({"rechteck": {"mitte": [15, 0], "breite": 10, "hoehe": 20}},
                     {"kreis": {"mitte": [15, 0], "durchmesser": 4}})
    volumen, grund = volumen_auto(spec)
    assert volumen is None and grund == "f1: Rotation mit mehreren Profilen nicht analytisch"
```

`tests/spec/test_konturen.py` – Import um `eckradien_roh` ergänzen und anhängen:

```python
def test_eckradien_roh():
    assert eckradien_roh({"punkte": DREIECK, "radien": "=R"}) == ["=R", "=R", "=R"]
    assert eckradien_roh({"punkte": DREIECK, "radien": [0, 1, "=R"]}) == [0, 1, "=R"]
    assert eckradien_roh({"punkte": DREIECK}) == [0, 0, 0]
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung/test_geometrie.py tests/spec/test_konturen.py -q`
Expected: FAIL (Rechteck/Kreis liefern 0, mehrere Profile werden addiert, `ImportError: eckradien_roh`).

- [ ] **Step 3: `swki/pruefung/geometrie.py` – `_pappus` ersetzen**

```python
def _flaeche_schwerpunkt(element: dict, p: dict) -> tuple[float, tuple[float, float]]:
    """Fläche (mm²) und Schwerpunkt (u, v) eines geschlossenen Skizzenelements ohne Rundungen."""
    if "rechteck" in element:
        r = element["rechteck"]
        return auswerten(r["breite"], p) * auswerten(r["hoehe"], p), _punkte([r["mitte"]], p)[0]
    if "kreis" in element:
        k = element["kreis"]
        return math.pi * auswerten(k["durchmesser"], p) ** 2 / 4, _punkte([k["mitte"]], p)[0]
    pts = _punkte(element["polygon"]["punkte"], p)
    a2 = _polygon_flaeche(pts)
    kreuz = [(x1 * y2 - x2 * y1, x1 + x2, y1 + y2) for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])]
    cx = sum(c * sx for c, sx, _ in kreuz) / (6 * a2)
    cy = sum(c * sy for c, _, sy in kreuz) / (6 * a2)
    return abs(a2), (cx, cy)


def _pappus(f: dict, p: dict) -> float | None:
    """Rotationsvolumen nach Pappus für genau ein Profil (Rechteck, Kreis oder Polygon); mehrere Profile → None
    (verschachtelte Profile zieht SolidWorks voneinander ab, das rechnet diese Formel nicht)."""
    elemente = f["skizze"]["elemente"]
    profile = [e for e in elemente if "mittellinie" not in e]
    if len(profile) != 1:
        return None
    linie = next(e["mittellinie"] for e in elemente if "mittellinie" in e)
    a, b = _punkte([linie["von"], linie["bis"]], p)
    d = (b[0] - a[0], b[1] - a[1])
    flaeche, (cx, cy) = _flaeche_schwerpunkt(profile[0], p)
    r = abs(d[0] * (cy - a[1]) - d[1] * (cx - a[0])) / math.hypot(*d)
    return flaeche * 2 * math.pi * r * auswerten(f.get("winkel", 360), p) / 360
```

(`_punkte` und `_polygon_flaeche` stehen schon in der Datei, vor `_pappus` – sonst die neuen Funktionen hinter sie verschieben.)

Im Zweig `rotation` von `volumen_auto` die Zeile `v = _pappus(f, p)` ersetzen durch:

```python
            v = _pappus(f, p)
            if v is None:
                return None, f"{f['id']}: Rotation mit mehreren Profilen nicht analytisch"
```

- [ ] **Step 4: `swki/spec/konturen.py` und `swki/compiler/skizze.py`**

In `konturen.py` `eckradien` ersetzen durch:

```python
def eckradien_roh(polygon: dict) -> list:
    """Radius je Ecke wie in der Spezifikation (Zahl oder Ausdruck): ein Wert für alle Ecken oder eine Liste je Ecke
    (0 = scharf); ohne radien 0."""
    roh = polygon.get("radien", 0)
    return list(roh) if isinstance(roh, list) else [roh] * len(polygon["punkte"])


def eckradien(polygon: dict, parameter: dict) -> list[float]:
    """Radius je Ecke in mm (ausgewertet)."""
    return [auswerten(r, parameter) for r in eckradien_roh(polygon)]
```

In `skizze.py` den Import um `eckradien_roh` erweitern (`from swki.spec.konturen import bogenende_koordinate, eckradien_roh, kontur_punkte_roh`) und im Polygon-Zweig

```python
            if "radien" in p:
                je_ecke = p["radien"] if isinstance(p["radien"], list) else [p["radien"]] * len(uv)
                for ecke, radius in zip(uv, je_ecke):
                    self.verrunde(linien, ecke, radius)
```

ersetzen durch

```python
            if "radien" in p:
                for ecke, radius in zip(uv, eckradien_roh(p)):
                    self.verrunde(linien, ecke, radius)
```

- [ ] **Step 5: Konstanten nach `swki/spec/normen.py`**

In `normen.py` nach `SW_END_DURCH_ALLES` ergänzen:

```python
SW_FM_HOLE_WZD = 25  # swFeatureNameID_e.swFmHoleWzd (IFeatureManager.CreateDefinition; Stift durch, Spike S10 Frage 1)
SW_BEFESTIGUNG_STIFT_DURCH = -1  # FastenerType2 eines über CreateDefinition gebauten Stiftlochs mit durch (S10 Frage 4)
SW_LOCH_DURCH = 25  # swWzdHoleTypes_e.swHoleThru: Type dieses Stiftlochs
```

In `swki/compiler/handler/normbohrung.py` die lokale Definition `SW_FM_HOLE_WZD = 25 …` entfernen und `SW_FM_HOLE_WZD` aus `swki.spec.normen` importieren. In `swki/pruefung/bewertung.py` die beiden lokalen Definitionen `SW_BEFESTIGUNG_STIFT_DURCH` und `SW_LOCH_DURCH` entfernen und aus `swki.spec.normen` importieren. Kein Verhaltenswechsel.

- [ ] **Step 6: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → 320 + 4 = **324 passed**.
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → `"befunde": []`.
Run: `.venv\Scripts\python.exe tests\referenz\auswerferhalteplatte\sollvolumen.py` → letzte Zeile unverändert `692653.890  Sollvolumen mm³`.

- [ ] **Step 7: Commit**

```powershell
git add swki/pruefung/geometrie.py swki/spec/konturen.py swki/compiler/skizze.py swki/spec/normen.py swki/compiler/handler/normbohrung.py swki/pruefung/bewertung.py tests/pruefung/test_geometrie.py tests/spec/test_konturen.py
git commit -m "pruefung/compiler: Pappus fuer Rechteck/Kreis, mehrere Profile nicht analytisch; eckradien_roh, Konstanten in normen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Tests ohne SolidWorks – `Kontext.verknuepfe`, Zylinderprüfung der Normbohrung

**Files:**
- Create: `tests/compiler/test_kontext.py`
- Modify: `tests/compiler/test_normbohrung.py`

**Interfaces:**
- Consumes: `Kontext(app, model, spec, spec_pfad, tol_mm)` und `Kontext.verknuepfe(masname, roh, vorzeichen=1)` (`swki/compiler/kontext.py`); `_bohrungen_pruefen(ctx, feature, fid, punkte)` und das Modul-Attribut `flaechen` in `swki/compiler/handler/normbohrung.py`; `Flaeche(art, punkt, normale=None, achse=None, radius=None, …)` aus `swki/compiler/anker.py`.

- [ ] **Step 1: `tests/compiler/test_kontext.py` (neu)**

```python
from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import Kontext


class _Gleichungen:
    def __init__(self, rueckgabe: int = 0):
        self.texte, self.rueckgabe = [], rueckgabe

    def Add2(self, index, text, loesen):
        self.texte.append(text)
        return self.rueckgabe


def _ctx(rueckgabe: int = 0) -> Kontext:
    model = SimpleNamespace(GetEquationMgr=_Gleichungen(rueckgabe))
    return Kontext(None, model, {"parameter": {"L": 100}}, Path("x.yaml"), 0.1)


def test_feste_zahl_wird_nicht_gebunden():
    ctx = _ctx()
    ctx.verknuepfe("D1@f1", 20)
    assert ctx.model.GetEquationMgr.texte == []


def test_ausdruck_wird_als_gleichung_gebunden():
    ctx = _ctx()
    ctx.verknuepfe("D1@f1", "=L")
    assert ctx.model.GetEquationMgr.texte == ['"D1@f1" = "L"']


def test_vorzeichen_negiert_den_ausdruck():
    ctx = _ctx()
    ctx.verknuepfe("D2@f1_skizze", "=L/2-20", -1)
    assert ctx.model.GetEquationMgr.texte == ['"D2@f1_skizze" = -(("L" / 2) - 20)']


def test_abgelehnte_gleichung_ist_baufehler():
    with pytest.raises(BauFehler) as e:
        _ctx(rueckgabe=-1).verknuepfe("D1@f1", "=L")
    assert "D1@f1" in str(e.value)
```

- [ ] **Step 2: `tests/compiler/test_normbohrung.py` anhängen**

```python
from types import SimpleNamespace

import pytest

from swki.compiler.anker import Flaeche
from swki.compiler.fehler import BauFehler
from swki.compiler.handler import normbohrung as nb


def _zylinder(x, z):
    return Flaeche("zylinder", (x, 10.0, z), achse=(0.0, 1.0, 0.0), radius=4.0)


def test_bohrungen_pruefen_findet_jede_position(monkeypatch):
    monkeypatch.setattr(nb, "flaechen", lambda feature: [_zylinder(-30, -10), _zylinder(30, -10),
                                                          Flaeche("ebene", (0, 20, 0), normale=(0, 1, 0))])
    nb._bohrungen_pruefen(SimpleNamespace(tol_mm=0.1), None, "f2", [(-30.0, 20.0, -10.0), (30.0, 20.0, -10.0)])


def test_bohrungen_pruefen_meldet_fehlende_position(monkeypatch):
    monkeypatch.setattr(nb, "flaechen", lambda feature: [_zylinder(-30, -10)])
    with pytest.raises(BauFehler) as e:
        nb._bohrungen_pruefen(SimpleNamespace(tol_mm=0.1), None, "f2", [(-30.0, 20.0, -10.0), (30.0, 20.0, -10.0)])
    assert "Position 2 fehlt" in str(e.value)
```

(Imports an den Dateianfang zu den vorhandenen Imports stellen; `Flaeche` ist eine Dataclass – Feldnamen in `swki/compiler/anker.py` prüfen und bei Abweichung die Konstruktoraufrufe anpassen, nicht die Erwartung.)

- [ ] **Step 3: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler -q` → grün (das sind Absicherungen bestehenden Verhaltens; schlägt einer fehl, ist das ein Befund – Ursache im Bericht nennen, nicht die Erwartung anpassen).
Run: `.venv\Scripts\python.exe -m pytest -q` → 324 + 6 = **330 passed**.

- [ ] **Step 4: Commit**

```powershell
git add tests/compiler/test_kontext.py tests/compiler/test_normbohrung.py
git commit -m "tests: Kontext.verknuepfe und Zylinderpruefung der Normbohrung ohne SolidWorks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Live – Zwei-Körper-Fall, Toleranzen in den Konturtests, Gesamtlauf und Doku

**Files:**
- Modify: `tests/live/test_live_endbedingungen.py` (1 neuer Live-Test), `tests/live/test_live_konturen.py` (Vergleiche der Achslagen mit Toleranz)
- Modify: `docs/stufe2/ergebnisse.md` (Abschnitt „Offene Punkte für Stufe 3“), `docs/stufe2c/ergebnisse.md` (neuer Abschnitt „Aufräum-Paket“, „Offene Punkte“)

**Interfaces:**
- Consumes: `messe(ctx)` (`swki/pruefung/messen.py`, Feld `koerper`), `gebautes_teil` (`tests/live/bauhilfe.py`).

- [ ] **Step 1: Live-Test – `tests/live/test_live_endbedingungen.py` anhängen**

```python
from swki.pruefung.messen import messe


def test_aufsatz_mit_versatz_bei_abgesetzter_skizze_ergibt_zwei_koerper():
    # Bekannte Einschränkung (Spike S10 Frage 6 d): Versatz zur Skizze hin → 5 mm Luft → getrennter Körper.
    # Die Code-Prüfung koerper muss das im echten Teil sehen.
    zapfen = {"id": "f2", "typ": "extrusion",
              "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": 40}},
                         "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 10}}]},
              "ende": {"typ": "versatz_von_flaeche", "flaeche": DECKFLAECHE, "abstand": 5, "umkehren": True}}
    with gebautes_teil(_spec(zapfen)) as (ctx, fehler, _):
        assert fehler is None
        assert messe(ctx).koerper == 2
```

(`DECKFLAECHE`, `_spec`, `gebautes_teil` gibt es in der Datei schon; den Import an den Dateianfang stellen.)

- [ ] **Step 2: Toleranzen – `tests/live/test_live_konturen.py`**

`pytest.approx` wendet bei Listen von Tupeln keine Toleranz an (exakter Vergleich). An beiden Stellen, an denen `_zylinder_lagen(ctx)` mit `pytest.approx(…)` verglichen wird, die Koordinaten flach vergleichen:

```python
def _flach(lagen) -> list[float]:
    return [c for lage in lagen for c in lage]
```

(Hilfsfunktion neben `_zylinder_lagen` einfügen) und

```python
        assert _flach(_zylinder_lagen(ctx)) == pytest.approx(_flach(mitten), abs=1e-6)
```

bzw.

```python
        assert _flach(_zylinder_lagen(ctx)) == pytest.approx(_flach(erwartet), abs=1e-6)
```

- [ ] **Step 3: Unit-Tests und API-Prüfung**

Run: `.venv\Scripts\python.exe -m pytest -q` → **330 passed** (Live-Tests sind abgewählt; die Zahl der abgewählten steigt um 1).
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → `"befunde": []`.

- [ ] **Step 4: Live-Suite dateiweise**

Voraussetzung: SOLIDWORKS 2025 frisch gestartet, genau eine Instanz, Toggle 10/Integer 6 = `False 1`. Dann jede Datei einzeln, Private Bytes nach jeder Datei lesen, ab ca. 4 GB anhalten und um Neustart bitten:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_endbedingungen.py --zeit 240
.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_konturen.py --zeit 240
```

danach alle übrigen Dateien unter `tests\live` und zuletzt `tests\referenz` (je ein Aufruf). Expected: alle `OK` (Buchse, Formplatte, Auswerferhalteplatte bestehen). Einstellungen nach dem letzten Lauf: `False 1`.

- [ ] **Step 5: Doku**

`docs/stufe2/ergebnisse.md`, Abschnitt „Offene Punkte für Stufe 3“: jeden Punkt, den dieses Paket erledigt, mit „– erledigt (Aufräum-Paket, <Commit>)“ markieren (Fehlalarme in Hinweisen, `freigeben`-Kopie/Pfad, `bauen --lauf`, `speichere`, Compiler-Namen als IDs, `verknuepfe`-Test, Regel „kein Fortschritt“, Spec §6 1 + 3, `pruefen` nach Bauabbruch, `pruefer.json`-Form, `_pappus`, `_compiler_aenderungen`, `--max`). Den Punkt Rechner B ergänzen um „zurückgestellt: Rechner steht nicht zur Verfügung (Nutzer, 2026-10-01)“.

`docs/stufe2c/ergebnisse.md`: neuen Abschnitt `## Aufräum-Paket (Stand <Datum>)` vor „Offene Punkte“ mit: Unit-Testzahl, Live-Ergebnis je Datei, Einstellungen, kurze Liste der Änderungen je Gruppe A–E. Unter „Offene Punkte“ erledigte Punkte entfernen bzw. markieren (Kreissektor, doppelte Positionen/Tiefe, Toleranz Konturtests, Zwei-Körper-Live-Test) und Rechner B als zurückgestellt markieren.

- [ ] **Step 6: Commit**

```powershell
git add tests/live/test_live_endbedingungen.py tests/live/test_live_konturen.py docs/stufe2/ergebnisse.md docs/stufe2c/ergebnisse.md
git commit -m "tests/docs: Zwei-Koerper-Fall live, Toleranzen Konturtests, Ergebnisse Aufraeum-Paket" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Übergabe (mit Nutzer)**

Kein Push ohne Rückfrage: dem Nutzer Testzahlen und Live-Ergebnis zeigen und fragen, ob gepusht und ein Pull Request angelegt werden soll.

---

## Abdeckung (Selbstprüfung)

| Punkt | Task |
|---|---|
| A: Bauabbruch nicht vergleichen (Option A) | 1 |
| A: `pruefen` verweigert abgebrochenen Lauf | 1 |
| A: Spec-Text 1 + 3, Skill-Text | 1 |
| A: `--max` ≥ 0 | 1 |
| B: `freigeben` lehnt Kopie ab, nennt Pfad der Kopie | 2 |
| B: `bauen --lauf N` überschreibt nicht | 2 |
| B: `pruefer.json` Form | 3 |
| B: git-Fehler in `_compiler_aenderungen` | 3 |
| B: `speichere` nur im Arbeitsordner | 3 |
| B: Compiler-Namen als IDs verboten | 4 |
| C: Fehlalarme `feste_zahl` (Mittellinie, 360, Fase 45, Polygonpunkte) | 5 |
| C: Text `muster_kreis` (Regel 3) | 5 |
| C: Normbohrung doppelte Positionen, Tiefe vs. Senkung | 4 |
| C: Kontur mit Bogenmitte auf Konturpunkt | 4 |
| C: `_pappus` Rechteck/Kreis, mehrere Profile | 6 |
| D: Ausdrucksfehler-Tests (Validierung) | 4 |
| D: Randzweige Hinweise (richtung2, Winkel-Ausdruck, ISO negativ/Ausdrucksfehler) | 5 |
| D: `verknuepfe`-Test | 7 |
| D: Zylinderprüfung ohne SolidWorks | 7 |
| D: Zwei-Körper live, Toleranzen Konturtests | 8 |
| E: Konstanten nach `normen.py`, `eckradien_roh` | 6 |
| Rechner B zurückgestellt (Doku) | 8 |
