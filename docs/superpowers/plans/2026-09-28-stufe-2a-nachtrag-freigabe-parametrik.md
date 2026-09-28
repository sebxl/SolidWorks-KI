# Stufe 2a Nachtrag: Freigabe-Kopie und vollständige Parametrik – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Freigabe schützt den ganzen freigegebenen Stand (Kopie `<spec>.freigegeben.yaml` als Soll für Prüfer und Sollvolumen, Hinweise auf feste Maße), und alle Maße mit Ausdruck hängen per SW-Gleichung an Parametern – auch Musterabstände, Kreismusterwinkel, Ebenenversatz und Fasenwinkel.

**Architecture:** `swki/spec/freigabe.py` legt bei `freigeben` eine Kopie der Spezifikation ab und prüft sie in `pruefe_freigabe` per SHA-256 mit; `freigegebene_spec(spec_pfad)` liefert sie für Plan 2b (Sollvolumen, Prüfer-Agent). `swki/spec/hinweise.py` meldet feste Zahlen in maßtragenden Feature-Feldern, `swki validieren` gibt sie als `hinweise` aus (kein Fehler). Die Handler `muster_linear`, `muster_kreis`, `fase` und die versetzte Skizzenebene binden ihre Maße wie die übrigen Handler über `Kontext.verknuepfe`.

**Tech Stack:** Python ≥ 3.13, PyYAML, pywin32 (Late Binding), pytest; SOLIDWORKS 2025.

**Spec:** [docs/superpowers/specs/2026-09-26-solidworks-ki-design.md](../specs/2026-09-26-solidworks-ki-design.md) – §4 (Parameter als Gleichungen, Modelle bleiben änderbar), §6 (Freigabe; der Prüfer sieht die freigegebene Spezifikation). Anlass: Gesamt-Review von Stufe 2a (Important #2 und #3); Entscheidung des Nutzers vom 2026-09-28: Freigabe-Kopie plus Hinweise auf feste Maße, Maße per Gleichung nachziehen.

**Voraussetzung:** Plan [2026-09-27-stufe-2a-spezifikation-compiler.md](2026-09-27-stufe-2a-spezifikation-compiler.md) ist umgesetzt (auf `main`). Dieser Nachtrag kommt **vor** Plan 2b; Plan 2b ist bereits darauf angepasst (`bewerte(..., freigegeben)`, `freigegebene_spec` in `swki pruefen`, Prüfer-Agent und Skill `konstruieren`).

**Herkunft des Codes:** Jede Datei wurde vor dem Schreiben des Plans implementiert und getestet: Unit-Tests grün; `test_live_parametrik` gegen SOLIDWORKS 2025 Rev. 33.5.0 grün und ohne die Handler-Änderung rot; Regression `test_live_extrusion`, `test_live_muster`, `test_live_kanten`, `test_live_bauen` grün, zusammen mit dem angepassten Code aus Plan 2b außerdem `test_live_pruefen` und beide Referenzteile (Buchse, Formplatte). Code **wörtlich** übernehmen.

## Global Constraints

- Alle Global Constraints aus Plan 2a gelten unverändert (Late Binding und seine Ausnahmen, mm/Grad, JSON-Ausgabe mit Exit 0/1, nur eigene Dokumente, Speichern nur im Arbeitsordner, Benutzereinstellungen nur über `sw.einstellung`, Live-Tests einzeln mit `tests\live_einzeln.py`, Deutsch, kein Push ohne Rückfrage, Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`).
- Keine neue Abhängigkeit (PyYAML ist vorhanden).
- Maßnamen (live belegt 2026-09-28, gleich bei einer oder zwei Musterrichtungen): lineares Muster `D1`/`D2` = Anzahl, `D3`/`D4` = Abstand Richtung 1/2; Kreismuster `D1` = Anzahl, `D3` = Gesamtwinkel; Fase `D1` = Abstand, `D2` = Winkel; versetzte Ebene `D1@<Ebenenname>` (Betrag; die Richtung steckt im Umkehren-Flag). Der Ebenenname ist sprachabhängig (`Ebene1`) und wird deshalb aus `IFeature.Name` gelesen, nie fest geschrieben.
- Anzahlen (`anzahl`) sind laut Schema ganze Zahlen ohne Ausdruck und werden nicht gebunden.

## Dateistruktur nach diesem Plan

```
swki/spec/freigabe.py            + Kopie <spec>.freigegeben.yaml, kopie_pfad, freigegebene_spec, Prüfung der Kopie
swki/spec/hinweise.py            NEU: feste_masse(spec) – feste Zahlen in maßtragenden Feature-Feldern
swki/spec/befehle.py             validieren gibt "hinweise" aus
swki/compiler/skizze.py          versetzte Ebene: D1@<Ebene> per Gleichung
swki/compiler/handler/muster.py  muster_linear D3/D4, muster_kreis D3 per Gleichung
swki/compiler/handler/kanten.py  fase D2 (Winkel) per Gleichung
tests/spec/test_freigabe.py, tests/spec/test_hinweise.py, tests/spec/test_befehle.py, tests/live/test_live_parametrik.py
```

---

### Task 1: Freigabe-Kopie und Hinweise auf feste Maße

**Files:**
- Modify: `swki/spec/freigabe.py` (vollständig ersetzen), `swki/spec/befehle.py` (vollständig ersetzen), `tests/spec/test_freigabe.py` (vollständig ersetzen), `tests/spec/test_befehle.py`, `CLAUDE.md`, `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`
- Create: `swki/spec/hinweise.py`, `tests/spec/test_hinweise.py`

**Interfaces:**
- Consumes: `pruefsumme`, `freigabe_pfad`, `FreigabeFehler` (2a Task 4, Verhalten unverändert); `GUELTIG` aus `tests/spec/beispiel.py` (2a Task 3).
- Produces (`freigabe.py`): `kopie_pfad(spec_pfad) -> Path` (`<stem>.freigegeben.yaml` neben der Spezifikation); `freigeben(...)` schreibt die Kopie (`yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)`) und ergänzt im Eintrag `kopie_sha256`; `pruefe_freigabe(...)` wirft zusätzlich `FREIGABE_FEHLT` (Kopie fehlt) bzw. `FREIGABE_VERALTET` (Kopie verändert); `freigegebene_spec(spec_pfad) -> dict`. Plan 2b Task 4 ruft `freigegebene_spec` in `swki pruefen` auf.
- Produces (`hinweise.py`): `MASS_FELDER`; `feste_masse(spec) -> list[{"pfad", "meldung"}]` – Zahlen ≠ 0 unter `tiefe, durchmesser, radius, abstand, winkel, breite, hoehe, mitte, punkte, positionen, von, bis` in `features`; Anker (`nahe`, `kanten`, `flaeche`) und Anzahlen bleiben außen vor. Pfade im Format der Befunde (`features[4].richtung1.abstand`).
- `swki validieren <spec>` → zusätzlich `"hinweise": [...]` (Exit bleibt 0).

- [ ] **Step 1: Failing tests schreiben**

`tests/spec/test_freigabe.py` vollständig ersetzen:

```python
import copy
import json

import pytest

from swki.spec.freigabe import (
    FreigabeFehler, freigabe_pfad, freigeben, freigegebene_spec, kopie_pfad, pruefe_freigabe, pruefsumme,
)

SPEC = {
    "art": "teil", "name": "Platte", "material": "1.2312", "parameter": {"L": 100},
    "features": [{"id": "f1", "typ": "extrusion"}], "pruefung": {"huellquader": [100, 20, 60]},
}


def test_pruefsumme_ignoriert_bauweg():
    anders = copy.deepcopy(SPEC)
    anders["features"] = [{"id": "g1", "typ": "rotation"}]
    anders["max_nachbesserungen"] = 5
    assert pruefsumme(anders) == pruefsumme(SPEC)


@pytest.mark.parametrize("feld", ["parameter", "material", "pruefung", "name"])
def test_pruefsumme_erfasst_anforderungen(feld):
    anders = copy.deepcopy(SPEC)
    anders[feld] = {"x": 1} if feld in ("parameter", "pruefung") else "anders"
    assert pruefsumme(anders) != pruefsumme(SPEC)


def test_freigeben_und_pruefen(tmp_path):
    pfad = tmp_path / "platte.yaml"
    eintrag = freigeben(pfad, SPEC, zeitpunkt="2026-09-27T10:00:00")
    assert eintrag["pruefsumme"] == pruefsumme(SPEC) and eintrag["freigegeben"] == "2026-09-27T10:00:00"
    assert json.loads(freigabe_pfad(pfad).read_text(encoding="utf-8"))["platte.yaml"] == eintrag
    assert pruefe_freigabe(pfad, SPEC) == eintrag


def test_mehrere_specs_in_einer_freigabe(tmp_path):
    freigeben(tmp_path / "a.yaml", SPEC)
    freigeben(tmp_path / "b.yaml", {**SPEC, "name": "B"})
    assert set(json.loads(freigabe_pfad(tmp_path / "a.yaml").read_text(encoding="utf-8"))) == {"a.yaml", "b.yaml"}


def test_ohne_freigabe(tmp_path):
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(tmp_path / "platte.yaml", SPEC)
    assert e.value.daten["code"] == "FREIGABE_FEHLT"


def test_geaenderte_anforderung(tmp_path):
    pfad = tmp_path / "platte.yaml"
    freigeben(pfad, SPEC)
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(pfad, {**SPEC, "parameter": {"L": 101}})
    assert e.value.daten["code"] == "FREIGABE_VERALTET"


def test_freigabe_legt_kopie_ab(tmp_path):
    pfad = tmp_path / "platte.yaml"
    eintrag = freigeben(pfad, SPEC)
    assert kopie_pfad(pfad) == tmp_path / "platte.freigegeben.yaml"
    assert freigegebene_spec(pfad) == SPEC
    assert len(eintrag["kopie_sha256"]) == 64


def test_bauweg_aendern_laesst_kopie_unberuehrt(tmp_path):
    pfad = tmp_path / "platte.yaml"
    freigeben(pfad, SPEC)
    nachgebessert = {**SPEC, "features": [{"id": "f1", "typ": "extrusion"}, {"id": "f2", "typ": "fase"}]}
    pruefe_freigabe(pfad, nachgebessert)
    assert freigegebene_spec(pfad)["features"] == SPEC["features"]


def test_veraenderte_kopie(tmp_path):
    pfad = tmp_path / "platte.yaml"
    freigeben(pfad, SPEC)
    kopie_pfad(pfad).write_text("art: teil\n", encoding="utf-8")
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(pfad, SPEC)
    assert e.value.daten["code"] == "FREIGABE_VERALTET"


def test_fehlende_kopie(tmp_path):
    pfad = tmp_path / "platte.yaml"
    freigeben(pfad, SPEC)
    kopie_pfad(pfad).unlink()
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(pfad, SPEC)
    assert e.value.daten["code"] == "FREIGABE_FEHLT"
```

`tests/spec/test_hinweise.py`:

```python
from swki.spec.hinweise import feste_masse

from .beispiel import GUELTIG


def test_feste_masse_im_beispiel():
    # Null (Lage auf Achse/Ebene), Ausdrücke, Anzahlen und Anker ("nahe") bleiben unbeanstandet
    assert [h["pfad"] for h in feste_masse(GUELTIG)] == [
        "features[1].durchmesser", "features[2].radius", "features[3].abstand", "features[4].richtung1.abstand",
    ]


def test_verschachtelte_masse():
    spec = {"features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": -15}},
                    "elemente": [{"rechteck": {"mitte": [5, 0], "breite": "=L", "hoehe": 10}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}},
        {"id": "f2", "typ": "bohrung", "flaeche": {"nahe": [0, 20, 0]}, "positionen": [[12.5, "=B"]],
         "durchmesser": "=D", "tiefe": "=T", "senkung": {"durchmesser": 14, "tiefe": "=S"}},
    ]}
    hinweise = feste_masse(spec)
    assert [h["pfad"] for h in hinweise] == [
        "features[0].skizze.ebene.versatz.abstand", "features[0].skizze.elemente[0].rechteck.mitte[0]",
        "features[0].skizze.elemente[0].rechteck.hoehe", "features[1].positionen[0][0]",
        "features[1].senkung.durchmesser",
    ]
    assert "-15" in hinweise[0]["meldung"]


def test_nur_parameter_keine_hinweise():
    spec = {"features": [{"id": "f1", "typ": "fase", "kanten": [{"nahe": [50, 20, 0]}], "abstand": "=F",
                          "winkel": "=W"}]}
    assert feste_masse(spec) == []
```

In `tests/spec/test_befehle.py` in `test_validieren_ok` nach der Zeile `assert code == 0 and daten["gueltig"] is True and daten["features"] == 6` anfügen:

```python
    # feste Maße sind erlaubt, werden aber gemeldet (die Freigabe-Prüfsumme deckt sie nicht ab)
    assert [h["pfad"] for h in daten["hinweise"]][0] == "features[1].durchmesser"
```

- [ ] **Step 2: Tests laufen lassen – müssen fehlschlagen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec -v`
Expected: FAIL – Sammelfehler (`ImportError: cannot import name 'freigegebene_spec'` bzw. `ModuleNotFoundError: No module named 'swki.spec.hinweise'`).

- [ ] **Step 3: Implementieren**

`swki/spec/freigabe.py` vollständig ersetzen:

```python
"""Freigabe einer Spezifikation: Prüfsumme über die Anforderungen, gespeichert in freigabe.json.

Die Prüfsumme deckt nur die Anforderungen ab (Parameter, Material, Eigenschaften, Prüfwerte),
nicht den Bauweg (Features, Anker, Reihenfolge) – den darf Claude beim Nachbessern ändern.
Zusätzlich wird die ganze Spezifikation als <spec>.freigegeben.yaml abgelegt: Sie ist das Soll für den
Prüfer-Agenten und für das analytische Sollvolumen, auch wenn der Bauweg später nachgebessert wird.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import yaml

from swki.cli import SwkiFehler

PRUEF_FELDER = ("art", "name", "parameter", "material", "eigenschaften", "pruefung")


class FreigabeFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str):
        super().__init__(meldung)
        self.daten = {"code": code}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pruefsumme(spec: dict) -> str:
    kern = {feld: spec.get(feld) for feld in PRUEF_FELDER}
    text = json.dumps(kern, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _sha256(text)


def freigabe_pfad(spec_pfad: Path) -> Path:
    return spec_pfad.parent / "freigabe.json"


def kopie_pfad(spec_pfad: Path) -> Path:
    return spec_pfad.with_name(f"{spec_pfad.stem}.freigegeben.yaml")


def _lies(pfad: Path) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}


def freigeben(spec_pfad: Path, spec: dict, zeitpunkt: str | None = None) -> dict:
    pfad = freigabe_pfad(spec_pfad)
    daten = _lies(pfad)
    kopie = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)
    kopie_pfad(spec_pfad).write_text(kopie, encoding="utf-8")
    eintrag = {
        "pruefsumme": pruefsumme(spec),
        "freigegeben": zeitpunkt or datetime.now().isoformat(timespec="seconds"),
        "kopie_sha256": _sha256(kopie),
    }
    daten[spec_pfad.name] = eintrag
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return eintrag


def pruefe_freigabe(spec_pfad: Path, spec: dict) -> dict:
    """Wirft FreigabeFehler, wenn die Spezifikation nicht (mehr) freigegeben ist."""
    eintrag = _lies(freigabe_pfad(spec_pfad)).get(spec_pfad.name)
    if eintrag is None:
        raise FreigabeFehler("FREIGABE_FEHLT", f"{spec_pfad.name} ist nicht freigegeben. Zuerst: swki freigeben")
    if eintrag["pruefsumme"] != pruefsumme(spec):
        raise FreigabeFehler(
            "FREIGABE_VERALTET",
            f"Anforderungen in {spec_pfad.name} wurden nach der Freigabe geändert. Nutzer fragen und neu freigeben.",
        )
    kopie = kopie_pfad(spec_pfad)
    if not kopie.exists():
        raise FreigabeFehler("FREIGABE_FEHLT", f"{kopie.name} fehlt. Nutzer fragen und neu freigeben.")
    if _sha256(kopie.read_text(encoding="utf-8")) != eintrag.get("kopie_sha256"):
        raise FreigabeFehler(
            "FREIGABE_VERALTET", f"{kopie.name} wurde nach der Freigabe geändert. Nutzer fragen und neu freigeben.",
        )
    return eintrag


def freigegebene_spec(spec_pfad: Path) -> dict:
    """Die Spezifikation im Stand der Freigabe (Soll für Prüfer und Sollvolumen)."""
    return yaml.safe_load(kopie_pfad(spec_pfad).read_text(encoding="utf-8"))
```

`swki/spec/hinweise.py`:

```python
"""Hinweise zu einer gültigen Spezifikation, die nicht verhindern, dass sie gebaut wird.

Feste Zahlen in maßtragenden Feldern der Features deckt die Freigabe-Prüfsumme nicht ab (sie gehören zum Bauweg).
Anforderungsmaße sollen deshalb als Parameter geführt werden ("=Name"); validieren meldet die übrigen.
"""

MASS_FELDER = frozenset({
    "tiefe", "durchmesser", "radius", "abstand", "winkel", "breite", "hoehe", "mitte", "punkte", "positionen", "von", "bis",
})
_ANKER = frozenset({"nahe", "kanten", "flaeche"})  # Anker wählen Geometrie aus, sie sind keine Maße


def feste_masse(spec: dict) -> list[dict]:
    """Feste Zahlen ≠ 0 in maßtragenden Feldern der Features als [{"pfad", "meldung"}] (0 = Lage auf Achse/Ebene)."""
    hinweise = []

    def gehe(wert, pfad: str, mass: bool) -> None:
        if isinstance(wert, dict):
            for k, v in wert.items():
                if k not in _ANKER:
                    gehe(v, f"{pfad}.{k}", mass or k in MASS_FELDER)
        elif isinstance(wert, list):
            for i, v in enumerate(wert):
                gehe(v, f"{pfad}[{i}]", mass)
        elif mass and isinstance(wert, (int, float)) and not isinstance(wert, bool) and wert != 0:
            hinweise.append({
                "pfad": pfad,
                "meldung": f"feste Zahl {wert:g}: als Parameter führen, sonst deckt die Freigabe dieses Maß nicht ab",
            })

    for i, feature in enumerate(spec.get("features", [])):
        gehe(feature, f"features[{i}]", False)
    return hinweise
```

`swki/spec/befehle.py` vollständig ersetzen:

```python
"""Befehle "swki validieren <spec>" und "swki freigeben <spec>"."""

from pathlib import Path

from swki.spec.freigabe import freigeben, pruefsumme
from swki.spec.hinweise import feste_masse
from swki.spec.laden import lade_spec


def _validieren(args) -> dict:
    pfad = Path(args.spec)
    spec = lade_spec(pfad)
    return {
        "gueltig": True,
        "spec": str(pfad),
        "name": spec["name"],
        "features": len(spec["features"]),
        "pruefsumme": pruefsumme(spec),
        "hinweise": feste_masse(spec),
    }


def _freigeben(args) -> dict:
    pfad = Path(args.spec)
    spec = lade_spec(pfad)
    return {"spec": str(pfad), **freigeben(pfad, spec)}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("validieren", help="Schema und Plausibilität prüfen (ohne SolidWorks)")
    p.add_argument("spec")
    p.set_defaults(func=_validieren)
    p = subparsers.add_parser("freigeben", help="Anforderungen freigeben (schreibt freigabe.json)")
    p.add_argument("spec")
    p.set_defaults(func=_freigeben)
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle Unit-Tests grün (neu: 4 Tests in `test_freigabe.py`, 3 in `test_hinweise.py`).

- [ ] **Step 5: Doku anpassen**

In `CLAUDE.md`, Abschnitt `## Konstruieren (Stufe 2)`, direkt nach der Zeile, die mit `` - `swki validieren <spec>` → `` beginnt, einfügen:

```markdown
- Anforderungsmaße als `parameter` führen; `validieren` meldet feste Zahlen in Features als `hinweise` (die Freigabe
  schützt sie nicht). `freigeben` legt `<spec>.freigegeben.yaml` ab – diese Kopie nie ändern.
```

In `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` §6, Abschnitt „Nachbesserung“, direkt nach dem Punkt, der mit `` - `freigabe.json` enthält eine Prüfsumme `` beginnt (nach dessen letzter Zeile „… fragt es den Nutzer.“), einen neuen Punkt einfügen:

```markdown
- `swki freigeben` legt zusätzlich die Spezifikation als `<spec>.freigegeben.yaml` ab (Prüfsumme der Kopie in
  `freigabe.json`). Sie ist das Soll für den Prüfer-Agenten und für das Sollvolumen `auto`. Feste Zahlen in Features
  meldet `swki validieren` als Hinweis; Anforderungsmaße gehören in `parameter`.
```

- [ ] **Step 6: Commit**

```powershell
git add swki/spec tests/spec CLAUDE.md docs/superpowers/specs
git commit -m "spec: Freigabe legt Kopie ab, validieren meldet feste Maße" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Musterabstände, Kreismusterwinkel, Ebenenversatz und Fasenwinkel per Gleichung

**Files:**
- Modify: `swki/compiler/skizze.py`, `swki/compiler/handler/muster.py`, `swki/compiler/handler/kanten.py`, `swki/wissen/pywin32-fallstricke.md`
- Create: `tests/live/test_live_parametrik.py`

**Interfaces:**
- Consumes: `Kontext.verknuepfe(masname, roh, vorzeichen=1)` (2a Task 6; bindet nur, wenn `roh` ein Ausdruck ist); `gebautes_teil` aus `tests/live/bauhilfe.py` (2a Task 9); `sw.teilebox_mm`, `sw.rebuild` (2a Task 7).
- Produces: keine neuen Funktionen. Neue Gleichungen: `"D3@<id>"`/`"D4@<id>"` (muster_linear), `"D3@<id>"` (muster_kreis, nur mit `winkel`), `"D2@<id>"` (fase, nur mit `winkel`), `"D1@<Ebenenname>"` (versetzte Ebene, bei negativem Abstand negiert).

- [ ] **Step 1: Failing Live-Test schreiben**

`tests/live/test_live_parametrik.py`:

```python
"""Live: Musterabstände, Kreismusterwinkel, Ebenenversatz und Fasenwinkel hängen per Gleichung an Parametern."""

import math

import pythoncom
import pytest

from swki.compiler import sw

from .bauhilfe import gebautes_teil

pytestmark = pytest.mark.sw

PARAMETER = {"V": -15, "A1": 21, "A2": 13, "W": 300, "FW": 33}
SPEC = {"art": "teil", "name": "T", "parameter": PARAMETER, "features": [
    {"id": "f1", "typ": "extrusion",
     "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": "=V"}},
                "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
     "ende": {"typ": "blind", "tiefe": 20}},
    {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[-40, -20]], "durchmesser": 8, "durch": True},
    {"id": "f3", "typ": "muster_linear", "features": ["f2"],
     "richtung1": {"achse": "x", "abstand": "=A1", "anzahl": 4},
     "richtung2": {"achse": "z", "abstand": "=A2", "anzahl": 2, "umkehren": True}},
    {"id": "f4", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[10, 0]], "durchmesser": 6, "durch": True},
    {"id": "f5", "typ": "muster_kreis", "features": ["f4"], "achse": "y", "anzahl": 5, "winkel": "=W"},
    {"id": "f6", "typ": "fase", "kanten": [{"nahe": [50, 5, 0]}], "abstand": 1.5, "winkel": "=FW"},
]}


def _setze_parameter(model, name: str, wert: float) -> None:
    """Globale Variable ändern (Property-Put nur per Invoke, S9a), dann Gleichungen auswerten und neu aufbauen."""
    gleichungen = model.GetEquationMgr
    index = list(PARAMETER).index(name)  # globale Variablen stehen in Parameter-Reihenfolge vorne
    dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
    gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, f'"{name}" = {wert}')
    gleichungen.EvaluateAll
    sw.rebuild(model)


def _mass(model, name: str) -> float:
    return model.Parameter(name).SystemValue


def test_masse_folgen_parametern():
    with gebautes_teil(SPEC) as (ctx, fehler, _):
        assert fehler is None
        model = ctx.model
        gleichungen = model.GetEquationMgr
        texte = [gleichungen.Equation(i) for i in range(gleichungen.GetCount)]
        assert '"D3@f3" = "A1"' in texte and '"D4@f3" = "A2"' in texte
        assert '"D3@f5" = "W"' in texte and '"D2@f6" = "FW"' in texte
        # Ebenenname ist sprachabhängig ("Ebene1"); Maß = Betrag, daher negiert
        assert len([t for t in texte if t.startswith('"D1@') and t.endswith('= -("V")')]) == 1

        assert sw.teilebox_mm(model)[1] == pytest.approx(-15, abs=1e-6)
        _setze_parameter(model, "V", -25)
        assert sw.teilebox_mm(model)[1] == pytest.approx(-25, abs=1e-6)

        _setze_parameter(model, "A1", 22)
        _setze_parameter(model, "A2", 14)
        _setze_parameter(model, "W", 240)
        _setze_parameter(model, "FW", 40)
        assert _mass(model, "D3@f3") == pytest.approx(0.022)
        assert _mass(model, "D4@f3") == pytest.approx(0.014)
        assert _mass(model, "D3@f5") == pytest.approx(math.radians(240))
        assert _mass(model, "D2@f6") == pytest.approx(math.radians(40))
```

- [ ] **Step 2: Test laufen lassen – muss fehlschlagen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_parametrik.py`
Expected: `FEHLER` mit `assert ('"D3@f3" = "A1"' in ['"V" = -15', '"A1" = 21', '"A2" = 13', '"W" = 300', '"FW" = 33'])`.

- [ ] **Step 3: Implementieren**

In `swki/compiler/skizze.py`, Funktion `ebene_aufloesen`, ersetzen:

```python
            raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Versetzte Ebene {basis} {abstand:g} mm", schritt="ebene")
        return Skizzenebene(neu, basis, abstand, NORMALE[basis])
```

durch:

```python
            raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Versetzte Ebene {basis} {abstand:g} mm", schritt="ebene")
        # Das Maß ist der Betrag, die Richtung steckt im Umkehren-Flag (live belegt: D1@<Ebenenname>).
        # Wechselt der Parameter später das Vorzeichen, kippt die Ebene nicht mit – dann neu bauen.
        ctx.verknuepfe(f"D1@{neu.Name}", ebene["versatz"]["abstand"], -1 if abstand < 0 else 1)
        return Skizzenebene(neu, basis, abstand, NORMALE[basis])
```

In `swki/compiler/handler/muster.py`, Funktion `muster_linear`, ersetzen:

```python
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"muster_linear {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    return FeatureErgebnis([feature])
```

durch:

```python
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"muster_linear {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    # Maße des Musters (live belegt): D1/D2 Anzahl, D3/D4 Abstand Richtung 1/2
    ctx.verknuepfe(f"D3@{f['id']}", r1["abstand"])
    if r2:
        ctx.verknuepfe(f"D4@{f['id']}", r2["abstand"])
    return FeatureErgebnis([feature])
```

In derselben Datei, Funktion `muster_kreis`, ersetzen:

```python
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"muster_kreis {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    return FeatureErgebnis([feature], richtung=richtung)
```

durch:

```python
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"muster_kreis {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    if "winkel" in f:
        ctx.verknuepfe(f"D3@{f['id']}", f["winkel"])  # D1 Anzahl, D3 Gesamtwinkel (live belegt)
    return FeatureErgebnis([feature], richtung=richtung)
```

In `swki/compiler/handler/kanten.py`, Funktion `fase`, ersetzen:

```python
    feature.Name = f["id"]
    ctx.verknuepfe(f"D1@{f['id']}", f["abstand"])
    return FeatureErgebnis([feature])
```

durch:

```python
    feature.Name = f["id"]
    ctx.verknuepfe(f"D1@{f['id']}", f["abstand"])
    if "winkel" in f:
        ctx.verknuepfe(f"D2@{f['id']}", f["winkel"])  # D2 = Winkel (live belegt)
    return FeatureErgebnis([feature])
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m swki api pruefe-code swki/compiler/skizze.py swki/compiler/handler/muster.py swki/compiler/handler/kanten.py`
Expected: `{"max_jahr": 2025, "befunde": []}`

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle Unit-Tests grün.

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_parametrik.py tests\live\test_live_extrusion.py tests\live\test_live_muster.py tests\live\test_live_kanten.py tests\live\test_live_bauen.py`
Expected: alle `OK` (1 + 5 + 3 + 3 + 3 = 15).

- [ ] **Step 5: Wissensdatei ergänzen – an `swki/wissen/pywin32-fallstricke.md` anhängen:**

```markdown
## Maßnamen von Features (live belegt 2026-09-28)

- Lineares Muster: `D1`/`D2` Anzahl, `D3`/`D4` Abstand Richtung 1/2 (auch bei nur einer Richtung ist der Abstand `D3`).
- Kreismuster: `D1` Anzahl, `D3` Gesamtwinkel. Fase (Abstand-Winkel): `D1` Abstand, `D2` Winkel.
- Versetzte Referenzebene: `D1@<Ebenenname>`, Betrag; die Richtung steckt im Umkehren-Flag. Der Name ist sprachabhängig
  (`Ebene1`) → aus `IFeature.Name` lesen.
- Maße eines Features auflisten: `feature.GetFirstDisplayDimension`, `feature.GetNextDisplayDimension(dd)`,
  `dd.GetDimension2(0).FullName` bzw. `.SystemValue`; Wert eines Maßes: `model.Parameter("D3@f3").SystemValue`.
```

- [ ] **Step 6: Commit**

```powershell
git add swki/compiler swki/wissen tests/live/test_live_parametrik.py
git commit -m "compiler: Musterabstände, Kreismusterwinkel, Ebenenversatz und Fasenwinkel per Gleichung" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
