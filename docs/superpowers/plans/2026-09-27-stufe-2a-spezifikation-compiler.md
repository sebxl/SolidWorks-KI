# Stufe 2a: Spezifikation und Compiler (Einzelteile) – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine YAML-Spezifikation eines Einzelteils wird validiert, freigegeben und von `swki bauen` in einem Durchlauf deterministisch in SolidWorks gebaut (10 Feature-Typen, Anker ohne Namen, Parameter als SW-Gleichungen, Notausgang), gespeichert und protokolliert.

**Architecture:** `swki/spec/` prüft und gibt frei (ohne SolidWorks), `swki/compiler/` baut: eine Handler-Registry (je Feature-Typ eine Funktion), ein Bauablauf, der nach jedem Knoten den Rebuild prüft und beim ersten Fehler anhält, Anker-Auflösung in zwei Schichten (reine Geometrie in `anker.py`, SolidWorks-Topologie in `topologie.py`) und voll bestimmte Skizzen mit eigenen Maßen (`skizze.py`). Plan 2b (Prüfung, Prüfer-Agent, Schleife, Referenzteile) baut darauf auf.

**Tech Stack:** Python ≥ 3.13 (Rechner A: 3.14), pywin32 (Late Binding), PyYAML, jsonschema (neu), pytest; SOLIDWORKS 2025 (Rechner A) / 2026 (Rechner B).

**Spec:** [docs/superpowers/specs/2026-09-26-solidworks-ki-design.md](../specs/2026-09-26-solidworks-ki-design.md) – §4 Spezifikationsformat, §5 Compiler, §12 Tests. Ergebnisse der Machbarkeitstests: [docs/stufe0/ergebnisse.md](../../stufe0/ergebnisse.md), [swki/wissen/pywin32-fallstricke.md](../../../swki/wissen/pywin32-fallstricke.md).

**Herkunft des Codes:** Jede Datei in diesem Plan wurde vor dem Schreiben des Plans vollständig implementiert und getestet (ohne SolidWorks: alle Unit-Tests grün; mit SOLIDWORKS 2025 Rev. 33.5.0: alle Live-Tests grün, jeweils einzeln). Die SolidWorks-Aufrufketten stammen aus den Spikes S9a/S9b und den dabei gefundenen Korrekturen (siehe „Befunde beim Planschreiben“). Code **wörtlich** übernehmen; weicht das Verhalten live ab, nicht raten, sondern mit `swki api methode …` nachschlagen und im Task-Bericht dokumentieren.

## Global Constraints

- Windows 11; SOLIDWORKS 2025 (Rechner A, deutsche Oberfläche) und 2026 (Rechner B). Kein Code verdrahtet ein Jahr oder einen Pfad; beides kommt aus `config/rechner.yaml`. `SWKI_HOME` nur für Tests.
- Python `>=3.13`. Einzige neue Abhängigkeit: `jsonschema>=4.23` (Task 3). **Vor dem Installieren den Nutzer fragen** (Download von PyPI).
- Kommandozeile: jeder `swki`-Befehl gibt genau ein JSON-Objekt auf stdout aus (UTF-8, `ensure_ascii=False`); Exit 0 = ok, 1 = Fehler. Fachliche Fehler sind `SwkiFehler`; ihr Attribut `daten` wird ins JSON übernommen.
- Spezifikation in mm und Grad; die API rechnet in m und rad. Umrechnen nur mit `swki.verbindung.mm`/`in_mm`/`in_mm3`/`grad`.
- COM immer **late-bound** (`swki.verbindung.verbinde` erzwingt dynamisches Dispatch). Nullargumentige Member ohne `()` (`model.FirstFeature`, `feature.GetFaces`). Ausnahmen, live belegt: `IBody2`-Methoden **mit** `()` (`body.GetFaces()`, `body.GetEdges()`); `IMathUtility.CreatePoint`, `IModelDoc2.ViewZoomtofit2`, `IModelDoc2.BlankRefGeom` nur nach `obj._FlagAsMethod("…")` und dann mit `()`. Objekt-Parameter mit `callout_leer()`, Double-Arrays mit `r8_array()`, ByRef mit `byref_long/bool/str/variant()`.
- Vor jedem **neuen** API-Aufruf `swki api methode <Interface.Member>` / `swki api enum <Name>` nachschlagen; Parameteranzahl und Enum-Werte aus dem Index sind verbindlich. Compiler-Code nur mit API-Aufrufen aus SW 2025 (`swki api pruefe-code` muss sauber sein).
- Nur selbst angelegte Dokumente anfassen und schließen. Speichern nur unter `<arbeitsordner>/<auftrag>/lauf-<n>/`. Benutzereinstellungen nur über `sw.einstellung(...)` umschalten (setzt im `finally` zurück).
- Live-Tests (Marker `sw`) **einzeln mit Zeitlimit** laufen lassen: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> …` (Task 7). Endet ein Lauf mit `ZEITLIMIT` oder wurde ein Prozess hart beendet: SolidWorks prüfen (reagiert es?) und die Benutzereinstellung `swInputDimValOnCreate` (Toggle 10) auf den Wert vor dem Lauf zurücksetzen – ein abgebrochener Prozess kann sein `finally` nicht mehr ausführen. Belegt SolidWorks mehr als ~4 GB Speicher, den Nutzer bitten, es neu zu starten.
- Sprache in Bezeichnern, Meldungen und Doku: Deutsch; SolidWorks-API-Namen englisch. Keine Auszüge aus der Dassault-Hilfe in Git.
- Kein `git push` ohne Rückfrage. Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (unabhängig vom ausführenden Modell). Erzeugte SolidWorks-Dateien nicht ins Git.

## Befunde beim Planschreiben (live belegt, gelten für alle Tasks)

1. **Skizzen werden selbst voll bestimmt.** `FullyDefineSketch` ist unzuverlässig: mit `AddToDB=True` erzeugte Elemente bleiben unterbestimmt, ohne `AddToDB` entstehen automatische Beziehungen, und ohne ausdrücklichen Bezug bemaßt es relativ zu einem beliebigen Element. Der Compiler erzeugt deshalb mit `AddToDB=True` (keine automatischen Beziehungen) und setzt **alle** Maße selbst: Größen (Breite, Höhe, Durchmesser) und die Lage jedes Kennpunkts zum Ursprung (`AddHorizontalDimension2`/`AddVerticalDimension2`; bei Wert 0 `sgVERTICALPOINTS2D`/`sgHORIZONTALPOINTS2D`, bei (0,0) `sgCOINCIDENT`). Damit hängen auch Lagen an Parametern.
2. **Rechtecke über `CreateCornerRectangle`.** `CreateCenterRectangle` legte den Mittelpunkt (und dessen Beziehungen) je nach SolidWorks-Zustand nicht an. Die Lage des Rechtecks wird über die Ecke (Mitte − Größe/2) bemaßt; der Ausdruck dafür wird aus Mitte und Größe zusammengesetzt.
3. **Ursprung als Skizzenpunkt:** Feature vom Typ `OriginProfileFeature` suchen, `SelectByID2("Point1@<Name>", "EXTSKETCHPOINT", …)`, Objekt über `GetSelectedObject6` holen – sprachunabhängig.
4. **`ViewZoomtofit2` nur als Methode:** reiner Attributzugriff passt nicht ein (Bild abgeschnitten); `_FlagAsMethod` + `()`.
5. **Referenzachsen ausblenden** (`BlankRefGeom`), sonst erscheinen sie in Screenshots.
6. **Lineare Muster lassen Instanzen außerhalb des Körpers stillschweigend weg** – nur die Volumenprüfung (Plan 2b) fängt das.
7. **MCP-Sperren wirksam** (Prüfpunkt aus Stufe 0 erledigt): In einer neu gestarteten Sitzung sind genau die 20 Lese-Tools von `solidworks-mcp` sichtbar, gesperrte Tools (`execute_macro`, `export_image`, …) fehlen, `list_open_documents` liefert Ergebnisse.

## Dateistruktur nach diesem Plan

```
schema/teil.schema.json            JSON-Schema der Teil-Spezifikation
swki/auftrag.py                    Auftragsordner, Läufe, Dateinamen, Protokollpfade
swki/spec/ausdruck.py              sichere Ausdrücke "=L/2-20" → Zahl bzw. SW-Gleichung
swki/spec/laden.py                 YAML laden, Schema- und Plausibilitätsprüfung
swki/spec/freigabe.py              Prüfsumme der Anforderungen, freigabe.json
swki/spec/befehle.py               swki validieren | freigeben
swki/compiler/fehler.py            BauFehler + Fehlercodes
swki/compiler/anker.py             Flächen/Kanten ohne Namen wählen (reine Geometrie)
swki/compiler/protokoll.py         protokoll.json (Knoten, Phasenzeiten)
swki/compiler/kontext.py           Baukontext, FeatureErgebnis, Gleichungen verknüpfen
swki/compiler/registry.py          @handler("typ")
swki/compiler/ablauf.py            Knoten der Reihe nach bauen, beim ersten Fehler anhalten
swki/compiler/skriptpruefung.py    statische Prüfung von Notausgang-Skripten
swki/compiler/sw.py                SolidWorks-Grundfunktionen (Dokument, Auswahl, Rebuild, Speichern)
swki/compiler/eigenschaften.py     globale Variablen, Material, benutzerdefinierte Eigenschaften
swki/compiler/topologie.py         SolidWorks-Flächen/Kanten → anker-Datenklassen, Anker auflösen
swki/compiler/skizze.py            Skizzenebenen, voll bestimmte Skizzen
swki/compiler/handler/*.py         extrusion/schnitt, rotation, bohrung, verrundung/fase, muster/spiegeln, skript
swki/compiler/bauen.py             swki bauen
tests/live_einzeln.py              Live-Tests einzeln mit Zeitlimit
tests/spec/, tests/compiler/, tests/test_auftrag.py, tests/live/*
```

## Spezifikationsformat (Kurzreferenz, verbindlich ist `schema/teil.schema.json`)

- Werte: Zahl oder Ausdruck `"=…"` mit Parametern und `+ - * / **`. Jeder Parameter wird eine globale SW-Variable; Maße mit Ausdruck werden per Gleichung daran gebunden.
- Ebenen: `vorne` (Normale +Z), `oben` (+Y), `rechts` (+X), `{versatz: {ebene, abstand}}`, `{feature: id, flaeche: "+y"}`, `{nahe: [x, y, z]}`.
- Skizzenkoordinaten (u, v) folgen der Standardebene gleicher Orientierung: vorne X=u, Y=v · oben X=u, Z=−v · rechts Z=−u, Y=v; die dritte Koordinate ist die Lage der Ebene (live belegt, S9a).
- Elemente: `rechteck {mitte, breite, hoehe}`, `kreis {mitte, durchmesser}`, `polygon {punkte}`, `mittellinie {von, bis}` (nur Rotation).
- Features: `extrusion`/`schnitt` (`ende: blind|durch_alles|mittig`, `umkehren`; Schnitt geht standardmäßig gegen die Skizzennormale), `rotation` (`winkel`, `schnitt`), `bohrung` (`flaeche`, `positionen`, `durchmesser`, `tiefe` oder `durch`, `senkung`), `verrundung`/`fase` (`kanten`: `{feature, auswahl: senkrechte_kanten|alle_kanten}`, `{feature, kanten_an: "+y"}`, `{nahe}`), `muster_linear` (`richtung1/2: {achse, abstand, anzahl, umkehren}`), `muster_kreis` (`achse`, `anzahl`, `winkel`), `spiegeln` (`features`, `ebene`), `skript` (`datei: skripte/<id>.py`, `luecke`).
- `pruefung`: `huellquader [X, Y, Z]`, `volumen {soll: Zahl|auto, toleranz_prozent}`, `masse_pruefen [{was, von, zu, soll, tol}]` mit Messpunkten `{feature, instanz, achse: true}` (Bohrungsachse), `{feature, flaeche}`, `{punkt}`, `schwerpunkt {soll: [x|null, …], tol}` – ausgewertet in Plan 2b.
- Die Prüfsumme der Freigabe deckt `art, name, parameter, material, eigenschaften, pruefung` ab (Spec §6), nicht den Bauweg.

---

### Task 1: Ausdrücke in Spezifikationen

**Files:**
- Create: `swki/spec/__init__.py` (leer), `swki/spec/ausdruck.py`, `tests/spec/__init__.py` (leer), `tests/spec/test_ausdruck.py`

**Interfaces:**
- Produces: `AusdruckFehler(SwkiFehler)`; `ist_ausdruck(wert) -> bool`; `namen(ausdruck: str) -> set[str]`; `auswerten(wert, parameter: dict | None = None) -> float`; `sw_ausdruck(ausdruck: str) -> str` (z. B. `'=L/2-20'` → `'("L" / 2) - 20'`).

- [ ] **Step 1: Failing tests schreiben**

`tests/spec/test_ausdruck.py`:

```python
import pytest

from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck, namen, sw_ausdruck


def test_zahl_bleibt_zahl():
    assert auswerten(296) == 296.0
    assert auswerten(2.5) == 2.5


def test_ausdruck_mit_parametern():
    assert auswerten("=L/2-20", {"L": 296}) == 128.0
    assert auswerten("=-(B+4)*2", {"B": 1}) == -10.0
    assert auswerten("=2**3") == 8.0


def test_ist_ausdruck():
    assert ist_ausdruck("=L")
    assert not ist_ausdruck("L")
    assert not ist_ausdruck(5)


def test_unbekannter_parameter_nennt_namen():
    with pytest.raises(AusdruckFehler, match="'X'"):
        auswerten("=X*2", {"L": 1})


@pytest.mark.parametrize("text", ["=__import__('os')", "=L.real", "=1 if L else 2", "=True", "=[1]", "=L(2)"])
def test_verbotene_konstrukte(text):
    with pytest.raises(AusdruckFehler):
        auswerten(text, {"L": 1})


def test_syntaxfehler():
    with pytest.raises(AusdruckFehler, match="ungültig"):
        auswerten("=L*/2", {"L": 1})


def test_division_durch_null():
    with pytest.raises(AusdruckFehler, match="Division durch 0"):
        auswerten("=L/(B-B)", {"L": 1, "B": 2})


def test_bool_und_text_sind_keine_werte():
    with pytest.raises(AusdruckFehler):
        auswerten(True)
    with pytest.raises(AusdruckFehler):
        auswerten("L")


def test_namen():
    assert namen("=L/2-B") == {"L", "B"}
    assert namen("=5") == set()


def test_sw_ausdruck():
    assert sw_ausdruck("=L/2-20") == '("L" / 2) - 20'
    assert sw_ausdruck("=L") == '"L"'
    assert sw_ausdruck("=-L*2**2") == '-"L" * (2 ^ 2)'
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_ausdruck.py -v`
Expected: FAIL (`ModuleNotFoundError: swki.spec`).

- [ ] **Step 3: Implementieren**

`swki/spec/ausdruck.py`:

```python
"""Sichere Auswertung von Ausdrücken wie "=L/2-20" in Spezifikationen.

Erlaubt sind Zahlen, Parameternamen, + - * / ** und Klammern. Alles andere wird abgewiesen.
"""

import ast
import operator

from swki.cli import SwkiFehler

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_SW_OPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Pow: "^"}
_ERLAUBT = (ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.USub, ast.UAdd, *_OPS)


class AusdruckFehler(SwkiFehler):
    pass


def ist_ausdruck(wert) -> bool:
    return isinstance(wert, str) and wert.startswith("=")


def _baum(ausdruck: str) -> ast.expr:
    text = ausdruck[1:] if ausdruck.startswith("=") else ausdruck
    try:
        baum = ast.parse(text.strip(), mode="eval").body
    except SyntaxError as e:
        raise AusdruckFehler(f"Ausdruck {ausdruck!r} ist ungültig: {e.msg}") from None
    for teil in ast.walk(baum):
        if isinstance(teil, _ERLAUBT):
            continue
        if isinstance(teil, ast.Constant) and type(teil.value) in (int, float):
            continue
        raise AusdruckFehler(f"Ausdruck {ausdruck!r}: {type(teil).__name__} ist nicht erlaubt")
    return baum


def namen(ausdruck: str) -> set[str]:
    return {k.id for k in ast.walk(_baum(ausdruck)) if isinstance(k, ast.Name)}


def _rechne(k: ast.expr, parameter: dict, ausdruck: str) -> float:
    if isinstance(k, ast.Constant):
        return float(k.value)
    if isinstance(k, ast.Name):
        if k.id not in parameter:
            raise AusdruckFehler(f"Ausdruck {ausdruck!r}: unbekannter Parameter {k.id!r}")
        return float(parameter[k.id])
    if isinstance(k, ast.UnaryOp):
        wert = _rechne(k.operand, parameter, ausdruck)
        return -wert if isinstance(k.op, ast.USub) else wert
    links = _rechne(k.left, parameter, ausdruck)
    rechts = _rechne(k.right, parameter, ausdruck)
    if isinstance(k.op, ast.Div) and rechts == 0:
        raise AusdruckFehler(f"Ausdruck {ausdruck!r}: Division durch 0")
    return float(_OPS[type(k.op)](links, rechts))


def auswerten(wert, parameter: dict | None = None) -> float:
    """Zahl oder "=Ausdruck" → float (mm bzw. Grad)."""
    if isinstance(wert, bool):
        raise AusdruckFehler(f"{wert!r} ist keine Zahl")
    if isinstance(wert, (int, float)):
        return float(wert)
    if not ist_ausdruck(wert):
        raise AusdruckFehler(f"{wert!r} ist weder Zahl noch Ausdruck (beginnt mit '=')")
    return _rechne(_baum(wert), parameter or {}, wert)


def _sw(k: ast.expr, oben: bool) -> str:
    if isinstance(k, ast.Constant):
        return repr(k.value)
    if isinstance(k, ast.Name):
        return f'"{k.id}"'
    if isinstance(k, ast.UnaryOp):
        innen = _sw(k.operand, False)
        return f"-{innen}" if isinstance(k.op, ast.USub) else innen
    text = f"{_sw(k.left, False)} {_SW_OPS[type(k.op)]} {_sw(k.right, False)}"
    return text if oben else f"({text})"


def sw_ausdruck(ausdruck: str) -> str:
    """Ausdruck in SolidWorks-Gleichungssyntax, z. B. '=L/2-20' → '("L" / 2) - 20'."""
    return _sw(_baum(ausdruck), True)
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_ausdruck.py -v`
Expected: 15 passed.

- [ ] **Step 5: Commit**

```powershell
git add swki/spec tests/spec
git commit -m "spec: sichere Ausdrücke und SW-Gleichungssyntax" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 2: Statische Prüfung von Notausgang-Skripten

**Files:**
- Create: `swki/compiler/__init__.py` (leer), `swki/compiler/skriptpruefung.py`, `tests/compiler/__init__.py` (leer), `tests/compiler/test_skriptpruefung.py`

**Interfaces:**
- Produces: `pruefe_skript(quelltext: str) -> list[dict]` (Befunde `{"zeile", "meldung"}`, leer = zulässig); Konstanten `ERLAUBTE_IMPORTE`, `VERBOTENE_NAMEN`, `VERBOTENE_ATTRIBUTE`.
- Spec §5 „skripte“: verbotene Importe/Aufrufe; hier strenger als Whitelist (nur `math`), zusätzlich keine Speicher-/Schließ-/Makro-Aufrufe der API – das erledigt der Compiler.

- [ ] **Step 1: Failing tests schreiben**

`tests/compiler/test_skriptpruefung.py`:

```python
import pytest

from swki.compiler.skriptpruefung import pruefe_skript

GUT = """
import math


def bauen(ctx):
    skizze, _ = ctx.skizze({"feature": "f1", "flaeche": "+y"}, [{"kreis": {"mitte": [0, 0], "durchmesser": "=D"}}])
    ctx.auswahl_leeren()
    skizze.Select2(False, 0)
    tiefe = ctx.m(5) * math.sqrt(2)
    return ctx.model.FeatureManager.FeatureCut4(
        True, False, False, 0, 0, tiefe, 0.0, False, False, False, False, 0.0, 0.0,
        False, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False)
"""


def test_zulaessiges_skript():
    assert pruefe_skript(GUT) == []


@pytest.mark.parametrize(
    ("quelle", "teil"),
    [
        ("import os\ndef bauen(ctx):\n    pass\n", "'os'"),
        ("from shutil import rmtree\ndef bauen(ctx):\n    pass\n", "'shutil'"),
        ("import subprocess as sp\ndef bauen(ctx):\n    pass\n", "'subprocess'"),
        ("def bauen(ctx):\n    eval('1')\n", "'eval'"),
        ("def bauen(ctx):\n    open('x', 'w')\n", "'open'"),
        ("def bauen(ctx):\n    ctx.__class__\n", "Dunder"),
        ("def bauen(ctx):\n    ctx.model.SaveAs3('x', 0, 1)\n", "'SaveAs3'"),
        ("def bauen(ctx):\n    ctx.app.CloseDoc('x')\n", "'CloseDoc'"),
        ("def bauen(ctx):\n    getattr(ctx, 'app')\n", "'getattr'"),
    ],
)
def test_verbotenes_wird_gemeldet(quelle, teil):
    befunde = pruefe_skript(quelle)
    assert any(teil in b["meldung"] for b in befunde), befunde


def test_zeilennummer():
    befunde = pruefe_skript("def bauen(ctx):\n    x = 1\n    eval('2')\n")
    assert befunde == [{"zeile": 3, "meldung": "'eval' ist nicht erlaubt"}]


def test_bauen_fehlt():
    assert pruefe_skript("def machen(ctx):\n    pass\n") == [{"zeile": 0, "meldung": "Funktion 'def bauen(ctx)' fehlt"}]


def test_syntaxfehler():
    [befund] = pruefe_skript("def bauen(ctx)\n    pass\n")
    assert befund["zeile"] == 1 and befund["meldung"].startswith("Syntaxfehler")
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_skriptpruefung.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementieren**

`swki/compiler/skriptpruefung.py`:

```python
"""Statische Prüfung von Notausgang-Skripten (typ: skript) vor dem Laden.

Ein Skript darf nur `math` importieren, muss `def bauen(ctx)` definieren und darf weder
gefährliche Builtins noch Dunder-Attribute noch Speicher-/Schließ-/Makro-Aufrufe der
SolidWorks-API verwenden. Speichern und Schließen übernimmt ausschließlich der Compiler.
"""

import ast

ERLAUBTE_IMPORTE = {"math"}
VERBOTENE_NAMEN = {
    "exec", "eval", "compile", "open", "__import__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "input", "breakpoint", "exit", "quit",
}
VERBOTENE_ATTRIBUTE = {
    "SaveAs", "SaveAs2", "SaveAs3", "Save", "Save2", "Save3", "SaveBMP",
    "CloseDoc", "CloseAllDocuments", "QuitDoc", "ExitApp",
    "OpenDoc", "OpenDoc6", "OpenDoc7", "LoadFile4",
    "RunMacro", "RunMacro2", "RunCommand",
    "DeleteFile", "SetUserPreferenceToggle", "SetUserPreferenceIntegerValue",
    "SetUserPreferenceDoubleValue", "SetUserPreferenceStringValue",
}


def _befund(knoten, meldung: str) -> dict:
    return {"zeile": getattr(knoten, "lineno", 0), "meldung": meldung}


def pruefe_skript(quelltext: str) -> list[dict]:
    """Liefert Befunde [{"zeile", "meldung"}]; leere Liste = Skript zulässig."""
    try:
        baum = ast.parse(quelltext)
    except SyntaxError as e:
        return [{"zeile": e.lineno or 0, "meldung": f"Syntaxfehler: {e.msg}"}]
    befunde = []
    for k in ast.walk(baum):
        if isinstance(k, ast.Import):
            for alias in k.names:
                if alias.name.split(".")[0] not in ERLAUBTE_IMPORTE:
                    befunde.append(_befund(k, f"Import {alias.name!r} nicht erlaubt (erlaubt: math)"))
        elif isinstance(k, ast.ImportFrom):
            if (k.module or "").split(".")[0] not in ERLAUBTE_IMPORTE:
                befunde.append(_befund(k, f"Import aus {k.module!r} nicht erlaubt (erlaubt: math)"))
        elif isinstance(k, ast.Name) and k.id in VERBOTENE_NAMEN:
            befunde.append(_befund(k, f"{k.id!r} ist nicht erlaubt"))
        elif isinstance(k, ast.Attribute):
            if k.attr.startswith("__"):
                befunde.append(_befund(k, f"Dunder-Attribut {k.attr!r} ist nicht erlaubt"))
            elif k.attr in VERBOTENE_ATTRIBUTE:
                befunde.append(_befund(k, f"API-Aufruf {k.attr!r} ist im Skript nicht erlaubt"))
    bauen = [
        k for k in baum.body
        if isinstance(k, ast.FunctionDef) and k.name == "bauen" and len(k.args.args) == 1
    ]
    if not bauen:
        befunde.append({"zeile": 0, "meldung": "Funktion 'def bauen(ctx)' fehlt"})
    return sorted(befunde, key=lambda b: b["zeile"])
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_skriptpruefung.py -v`
Expected: 13 passed.

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler tests/compiler
git commit -m "compiler: statische Prüfung von Notausgang-Skripten" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 3: Schema und Laden der Spezifikation

**Files:**
- Modify: `pyproject.toml` (Abhängigkeit `jsonschema`)
- Create: `schema/teil.schema.json`, `swki/spec/laden.py`, `tests/spec/beispiel.py`, `tests/spec/test_laden.py`

**Interfaces:**
- Consumes: `auswerten`, `ist_ausdruck`, `AusdruckFehler` (Task 1); `pruefe_skript` (Task 2); `swki.konfig.PROJEKT`.
- Produces: `SpecFehler(SwkiFehler)` mit `daten = {"befunde": [{"pfad", "meldung"}]}`; `lade_yaml(pfad) -> dict`; `schema_befunde(spec) -> list[dict]`; `plausibel_befunde(spec, auftrag_ordner: Path) -> list[dict]`; `lade_spec(pfad: Path) -> dict` (wirft `SpecFehler`). Befundpfade wie `features[2].kanten[0].feature`.

- [ ] **Step 1: Abhängigkeit ergänzen – **vorher den Nutzer fragen**: „`jsonschema` (und Abhängigkeiten `attrs`, `referencing`, `rpds-py`, `jsonschema-specifications`) wird von PyPI in die .venv geladen. Einverstanden?“ Erst nach Ja weiter.**

In `pyproject.toml` den Block `dependencies` ersetzen durch:

```toml
dependencies = [
  "pywin32>=311",
  "PyYAML>=6.0",
  "jsonschema>=4.23",
]
```

Run: `.venv\Scripts\python.exe -m pip install -e ".[dev]"`
Expected: Erfolgreich, `jsonschema` installiert.

- [ ] **Step 2: Failing tests schreiben**

`tests/spec/beispiel.py`:

```python
"""Gültige Beispiel-Spezifikation für Tests (selbst formuliert)."""

GUELTIG = {
    "art": "teil",
    "name": "Platte_1",
    "material": "1.2312",
    "eigenschaften": {"Benennung": "Platte"},
    "parameter": {"L": 100, "B": 60, "H": 20},
    "features": [
        {
            "id": "f1", "typ": "extrusion",
            "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
            "ende": {"typ": "blind", "tiefe": "=H"},
        },
        {
            "id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
            "positionen": [["=L/2-10", 0], ["=-L/2+10", 0]], "durchmesser": 8, "durch": True,
        },
        {"id": "f3", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": 3},
        {"id": "f4", "typ": "fase", "kanten": [{"nahe": [50, 20, 0]}], "abstand": 1},
        {"id": "f5", "typ": "muster_linear", "features": ["f2"],
         "richtung1": {"achse": "z", "abstand": 20, "anzahl": 2}},
        {"id": "f6", "typ": "spiegeln", "features": ["f5"], "ebene": "vorne"},
    ],
    "pruefung": {
        "huellquader": ["=L", "=H", "=B"],
        "volumen": {"soll": "auto", "toleranz_prozent": 0.5},
        "masse_pruefen": [
            {"was": "Abstand Bohrungen", "von": {"feature": "f2", "instanz": 1, "achse": True},
             "zu": {"feature": "f2", "instanz": 2, "achse": True}, "soll": 80, "tol": 0.01},
        ],
        "schwerpunkt": {"soll": [0, None, 0], "tol": 0.05},
    },
}
```

`tests/spec/test_laden.py`:

```python
import copy

import pytest
import yaml

from swki.spec.laden import SpecFehler, lade_spec, plausibel_befunde, schema_befunde

from .beispiel import GUELTIG


def _spec(**aenderungen):
    spec = copy.deepcopy(GUELTIG)
    spec.update(aenderungen)
    return spec


def test_gueltige_spec_hat_keine_befunde(tmp_path):
    assert schema_befunde(GUELTIG) == []
    assert plausibel_befunde(GUELTIG, tmp_path) == []


def test_lade_spec_aus_datei(tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    assert lade_spec(pfad)["name"] == "Platte_1"


def test_fehlende_datei(tmp_path):
    with pytest.raises(SpecFehler) as e:
        lade_spec(tmp_path / "fehlt.yaml")
    assert "fehlt" in e.value.daten["befunde"][0]["meldung"]


def test_unbekannte_art():
    assert schema_befunde(_spec(art="baugruppe"))[0]["pfad"] == "art"


def test_schema_meldet_pfad_und_grund():
    spec = _spec()
    del spec["features"][2]["radius"]
    [befund] = schema_befunde(spec)
    assert befund["pfad"] == "features[2]"
    assert "radius" in befund["meldung"]


def test_schema_meldet_unbekanntes_feld():
    spec = _spec()
    spec["features"][0]["farbe"] = "rot"
    assert any("farbe" in b["meldung"] for b in schema_befunde(spec))


def test_bohrung_braucht_tiefe_oder_durch():
    spec = _spec()
    del spec["features"][1]["durch"]
    assert schema_befunde(spec)


def test_doppelte_id(tmp_path):
    spec = _spec()
    spec["features"][1]["id"] = "f1"
    assert any("doppelt" in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_verweis_auf_spaeteres_feature(tmp_path):
    spec = _spec()
    spec["features"][2]["kanten"] = [{"feature": "f4", "auswahl": "alle_kanten"}]
    [befund] = plausibel_befunde(spec, tmp_path)
    assert befund["pfad"] == "features[2].kanten[0].feature"


def test_pruefung_verweist_auf_unbekanntes_feature(tmp_path):
    spec = _spec()
    spec["pruefung"]["masse_pruefen"][0]["zu"]["feature"] = "f9"
    assert any("f9" in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_unbekannter_parameter(tmp_path):
    spec = _spec()
    spec["features"][0]["ende"]["tiefe"] = "=T"
    [befund] = plausibel_befunde(spec, tmp_path)
    assert befund["pfad"] == "features[0].ende.tiefe" and "'T'" in befund["meldung"]


def test_masse_muessen_positiv_sein(tmp_path):
    spec = _spec()
    spec["features"][1]["durchmesser"] = "=B-60"
    [befund] = plausibel_befunde(spec, tmp_path)
    assert "durchmesser muss > 0" in befund["meldung"]


def test_versatz_darf_negativ_sein(tmp_path):
    spec = _spec()
    spec["features"][0]["skizze"]["ebene"] = {"versatz": {"ebene": "oben", "abstand": -5}}
    assert plausibel_befunde(spec, tmp_path) == []


def test_rotation_braucht_mittellinie(tmp_path):
    spec = _spec()
    spec["features"].append({
        "id": "f7", "typ": "rotation",
        "skizze": {"ebene": "vorne", "elemente": [{"polygon": {"punkte": [[1, 0], [2, 0], [2, 1]]}}]},
    })
    assert any("genau eine mittellinie" in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_senkung_muss_groesser_sein(tmp_path):
    spec = _spec()
    spec["features"][1]["senkung"] = {"durchmesser": 8, "tiefe": 2}
    assert any("Senkungsdurchmesser" in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_skript_wird_geprueft(tmp_path):
    (tmp_path / "skripte").mkdir()
    (tmp_path / "skripte" / "f7.py").write_text("import os\ndef bauen(ctx):\n    pass\n", encoding="utf-8")
    spec = _spec()
    spec["features"].append({"id": "f7", "typ": "skript", "datei": "skripte/f7.py", "luecke": "Gewinde"})
    [befund] = plausibel_befunde(spec, tmp_path)
    assert befund["pfad"] == "features[6].datei" and "'os'" in befund["meldung"]


def test_skript_fehlt(tmp_path):
    spec = _spec()
    spec["features"].append({"id": "f7", "typ": "skript", "datei": "skripte/f7.py", "luecke": "Gewinde"})
    assert "fehlt" in plausibel_befunde(spec, tmp_path)[0]["meldung"]
```

- [ ] **Step 3: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_laden.py -v`
Expected: FAIL (`ModuleNotFoundError: swki.spec.laden`).

- [ ] **Step 4: Schema anlegen**

`schema/teil.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "swki/teil.schema.json",
  "title": "SolidWorks-KI: Spezifikation eines Teils (Längen in mm, Winkel in Grad)",
  "type": "object",
  "required": ["art", "name", "features"],
  "additionalProperties": false,
  "properties": {
    "art": {"const": "teil"},
    "name": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]*$"},
    "material": {"type": "string", "minLength": 1},
    "eigenschaften": {"type": "object", "additionalProperties": {"type": "string"}},
    "parameter": {
      "type": "object",
      "propertyNames": {"pattern": "^[A-Za-z][A-Za-z0-9_]*$"},
      "additionalProperties": {"type": "number"}
    },
    "features": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/feature"}},
    "pruefung": {"$ref": "#/$defs/pruefung"},
    "max_nachbesserungen": {"type": "integer", "minimum": 1}
  },
  "$defs": {
    "wert": {"oneOf": [{"type": "number"}, {"type": "string", "pattern": "^=.+"}]},
    "punkt2": {"type": "array", "items": {"$ref": "#/$defs/wert"}, "minItems": 2, "maxItems": 2},
    "punkt3": {"type": "array", "items": {"$ref": "#/$defs/wert"}, "minItems": 3, "maxItems": 3},
    "richtung": {"enum": ["+x", "-x", "+y", "-y", "+z", "-z"]},
    "standardebene": {"enum": ["vorne", "oben", "rechts"]},
    "id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]*$"},
    "flaechenanker": {
      "oneOf": [
        {
          "type": "object", "required": ["feature", "flaeche"], "additionalProperties": false,
          "properties": {"feature": {"$ref": "#/$defs/id"}, "flaeche": {"$ref": "#/$defs/richtung"}}
        },
        {
          "type": "object", "required": ["nahe"], "additionalProperties": false,
          "properties": {"nahe": {"$ref": "#/$defs/punkt3"}}
        }
      ]
    },
    "ebene": {
      "oneOf": [
        {"$ref": "#/$defs/standardebene"},
        {
          "type": "object", "required": ["versatz"], "additionalProperties": false,
          "properties": {
            "versatz": {
              "type": "object", "required": ["ebene", "abstand"], "additionalProperties": false,
              "properties": {"ebene": {"$ref": "#/$defs/standardebene"}, "abstand": {"$ref": "#/$defs/wert"}}
            }
          }
        },
        {"$ref": "#/$defs/flaechenanker"}
      ]
    },
    "kantenanker": {
      "oneOf": [
        {
          "type": "object", "required": ["feature", "auswahl"], "additionalProperties": false,
          "properties": {"feature": {"$ref": "#/$defs/id"}, "auswahl": {"enum": ["senkrechte_kanten", "alle_kanten"]}}
        },
        {
          "type": "object", "required": ["feature", "kanten_an"], "additionalProperties": false,
          "properties": {"feature": {"$ref": "#/$defs/id"}, "kanten_an": {"$ref": "#/$defs/richtung"}}
        },
        {
          "type": "object", "required": ["nahe"], "additionalProperties": false,
          "properties": {"nahe": {"$ref": "#/$defs/punkt3"}}
        }
      ]
    },
    "element": {
      "oneOf": [
        {
          "type": "object", "required": ["rechteck"], "additionalProperties": false,
          "properties": {
            "rechteck": {
              "type": "object", "required": ["mitte", "breite", "hoehe"], "additionalProperties": false,
              "properties": {
                "mitte": {"$ref": "#/$defs/punkt2"}, "breite": {"$ref": "#/$defs/wert"}, "hoehe": {"$ref": "#/$defs/wert"}
              }
            }
          }
        },
        {
          "type": "object", "required": ["kreis"], "additionalProperties": false,
          "properties": {
            "kreis": {
              "type": "object", "required": ["mitte", "durchmesser"], "additionalProperties": false,
              "properties": {"mitte": {"$ref": "#/$defs/punkt2"}, "durchmesser": {"$ref": "#/$defs/wert"}}
            }
          }
        },
        {
          "type": "object", "required": ["polygon"], "additionalProperties": false,
          "properties": {
            "polygon": {
              "type": "object", "required": ["punkte"], "additionalProperties": false,
              "properties": {"punkte": {"type": "array", "minItems": 3, "items": {"$ref": "#/$defs/punkt2"}}}
            }
          }
        },
        {
          "type": "object", "required": ["mittellinie"], "additionalProperties": false,
          "properties": {
            "mittellinie": {
              "type": "object", "required": ["von", "bis"], "additionalProperties": false,
              "properties": {"von": {"$ref": "#/$defs/punkt2"}, "bis": {"$ref": "#/$defs/punkt2"}}
            }
          }
        }
      ]
    },
    "skizze": {
      "type": "object", "required": ["ebene", "elemente"], "additionalProperties": false,
      "properties": {
        "ebene": {"$ref": "#/$defs/ebene"},
        "elemente": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/element"}}
      }
    },
    "ende": {
      "type": "object", "required": ["typ"], "additionalProperties": false,
      "properties": {
        "typ": {"enum": ["blind", "durch_alles", "mittig"]},
        "tiefe": {"$ref": "#/$defs/wert"},
        "umkehren": {"type": "boolean"}
      },
      "if": {"properties": {"typ": {"enum": ["blind", "mittig"]}}},
      "then": {"required": ["tiefe"]}
    },
    "musterrichtung": {
      "type": "object", "required": ["achse", "abstand", "anzahl"], "additionalProperties": false,
      "properties": {
        "achse": {"enum": ["x", "y", "z"]},
        "abstand": {"$ref": "#/$defs/wert"},
        "anzahl": {"type": "integer", "minimum": 2},
        "umkehren": {"type": "boolean"}
      }
    },
    "featureliste": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/id"}},
    "f_extrusion": {
      "required": ["skizze", "ende"], "additionalProperties": false,
      "properties": {"id": true, "typ": true, "skizze": {"$ref": "#/$defs/skizze"}, "ende": {"$ref": "#/$defs/ende"}}
    },
    "f_rotation": {
      "required": ["skizze"], "additionalProperties": false,
      "properties": {
        "id": true, "typ": true, "skizze": {"$ref": "#/$defs/skizze"},
        "winkel": {"$ref": "#/$defs/wert"}, "schnitt": {"type": "boolean"}
      }
    },
    "f_bohrung": {
      "required": ["flaeche", "positionen", "durchmesser"], "additionalProperties": false,
      "properties": {
        "id": true, "typ": true,
        "flaeche": {"$ref": "#/$defs/flaechenanker"},
        "positionen": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/punkt2"}},
        "durchmesser": {"$ref": "#/$defs/wert"},
        "tiefe": {"$ref": "#/$defs/wert"},
        "durch": {"const": true},
        "senkung": {
          "type": "object", "required": ["durchmesser", "tiefe"], "additionalProperties": false,
          "properties": {"durchmesser": {"$ref": "#/$defs/wert"}, "tiefe": {"$ref": "#/$defs/wert"}}
        }
      },
      "oneOf": [{"required": ["tiefe"]}, {"required": ["durch"]}]
    },
    "f_verrundung": {
      "required": ["kanten", "radius"], "additionalProperties": false,
      "properties": {
        "id": true, "typ": true,
        "kanten": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/kantenanker"}},
        "radius": {"$ref": "#/$defs/wert"}
      }
    },
    "f_fase": {
      "required": ["kanten", "abstand"], "additionalProperties": false,
      "properties": {
        "id": true, "typ": true,
        "kanten": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/kantenanker"}},
        "abstand": {"$ref": "#/$defs/wert"},
        "winkel": {"$ref": "#/$defs/wert"}
      }
    },
    "f_muster_linear": {
      "required": ["features", "richtung1"], "additionalProperties": false,
      "properties": {
        "id": true, "typ": true, "features": {"$ref": "#/$defs/featureliste"},
        "richtung1": {"$ref": "#/$defs/musterrichtung"}, "richtung2": {"$ref": "#/$defs/musterrichtung"}
      }
    },
    "f_muster_kreis": {
      "required": ["features", "achse", "anzahl"], "additionalProperties": false,
      "properties": {
        "id": true, "typ": true, "features": {"$ref": "#/$defs/featureliste"},
        "achse": {"enum": ["x", "y", "z"]},
        "anzahl": {"type": "integer", "minimum": 2},
        "winkel": {"$ref": "#/$defs/wert"}
      }
    },
    "f_spiegeln": {
      "required": ["features", "ebene"], "additionalProperties": false,
      "properties": {
        "id": true, "typ": true, "features": {"$ref": "#/$defs/featureliste"}, "ebene": {"$ref": "#/$defs/ebene"}
      }
    },
    "f_skript": {
      "required": ["datei", "luecke"], "additionalProperties": false,
      "properties": {
        "id": true, "typ": true,
        "datei": {"type": "string", "pattern": "^skripte/[A-Za-z0-9_-]+\\.py$"},
        "luecke": {"type": "string", "minLength": 3}
      }
    },
    "feature": {
      "type": "object",
      "required": ["id", "typ"],
      "properties": {
        "id": {"$ref": "#/$defs/id"},
        "typ": {"enum": ["extrusion", "schnitt", "rotation", "bohrung", "verrundung", "fase",
                         "muster_linear", "muster_kreis", "spiegeln", "skript"]}
      },
      "allOf": [
        {"if": {"properties": {"typ": {"enum": ["extrusion", "schnitt"]}}}, "then": {"$ref": "#/$defs/f_extrusion"}},
        {"if": {"properties": {"typ": {"const": "rotation"}}}, "then": {"$ref": "#/$defs/f_rotation"}},
        {"if": {"properties": {"typ": {"const": "bohrung"}}}, "then": {"$ref": "#/$defs/f_bohrung"}},
        {"if": {"properties": {"typ": {"const": "verrundung"}}}, "then": {"$ref": "#/$defs/f_verrundung"}},
        {"if": {"properties": {"typ": {"const": "fase"}}}, "then": {"$ref": "#/$defs/f_fase"}},
        {"if": {"properties": {"typ": {"const": "muster_linear"}}}, "then": {"$ref": "#/$defs/f_muster_linear"}},
        {"if": {"properties": {"typ": {"const": "muster_kreis"}}}, "then": {"$ref": "#/$defs/f_muster_kreis"}},
        {"if": {"properties": {"typ": {"const": "spiegeln"}}}, "then": {"$ref": "#/$defs/f_spiegeln"}},
        {"if": {"properties": {"typ": {"const": "skript"}}}, "then": {"$ref": "#/$defs/f_skript"}}
      ]
    },
    "messpunkt": {
      "oneOf": [
        {
          "type": "object", "required": ["feature", "instanz", "achse"], "additionalProperties": false,
          "properties": {"feature": {"$ref": "#/$defs/id"}, "instanz": {"type": "integer", "minimum": 1}, "achse": {"const": true}}
        },
        {
          "type": "object", "required": ["feature", "flaeche"], "additionalProperties": false,
          "properties": {"feature": {"$ref": "#/$defs/id"}, "flaeche": {"$ref": "#/$defs/richtung"}}
        },
        {
          "type": "object", "required": ["punkt"], "additionalProperties": false,
          "properties": {"punkt": {"$ref": "#/$defs/punkt3"}}
        }
      ]
    },
    "massepruefung": {
      "type": "object", "required": ["was", "von", "zu", "soll"], "additionalProperties": false,
      "properties": {
        "was": {"type": "string", "minLength": 1},
        "von": {"$ref": "#/$defs/messpunkt"},
        "zu": {"$ref": "#/$defs/messpunkt"},
        "soll": {"$ref": "#/$defs/wert"},
        "tol": {"type": "number", "exclusiveMinimum": 0}
      }
    },
    "pruefung": {
      "type": "object", "additionalProperties": false,
      "properties": {
        "huellquader": {"type": "array", "items": {"$ref": "#/$defs/wert"}, "minItems": 3, "maxItems": 3},
        "huellquader_tol": {"type": "number", "exclusiveMinimum": 0},
        "volumen": {
          "type": "object", "required": ["soll"], "additionalProperties": false,
          "properties": {
            "soll": {"oneOf": [{"$ref": "#/$defs/wert"}, {"const": "auto"}]},
            "toleranz_prozent": {"type": "number", "exclusiveMinimum": 0}
          }
        },
        "masse_pruefen": {"type": "array", "items": {"$ref": "#/$defs/massepruefung"}},
        "schwerpunkt": {
          "type": "object", "required": ["soll"], "additionalProperties": false,
          "properties": {
            "soll": {
              "type": "array", "minItems": 3, "maxItems": 3,
              "items": {"oneOf": [{"$ref": "#/$defs/wert"}, {"type": "null"}]}
            },
            "tol": {"type": "number", "exclusiveMinimum": 0}
          }
        }
      }
    }
  }
}
```

- [ ] **Step 5: Implementieren**

`swki/spec/laden.py`:

```python
"""Laden einer Spezifikation (YAML) mit Schema- und Plausibilitätsprüfung."""

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from swki.cli import SwkiFehler
from swki.compiler.skriptpruefung import pruefe_skript
from swki.konfig import PROJEKT
from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck

SCHEMA_ORDNER = PROJEKT / "schema"
_POSITIV = {"breite", "hoehe", "durchmesser", "radius", "tiefe", "abstand"}
_WINKEL = {"winkel"}


class SpecFehler(SwkiFehler):
    def __init__(self, befunde: list[dict]):
        super().__init__(f"{len(befunde)} Befund(e) in der Spezifikation")
        self.daten = {"befunde": befunde}


def _pfad(teile) -> str:
    text = ""
    for t in teile:
        text += f"[{t}]" if isinstance(t, int) else (f".{t}" if text else str(t))
    return text or "(Wurzel)"


def lade_yaml(pfad: Path) -> dict:
    if not pfad.exists():
        raise SpecFehler([{"pfad": "(Datei)", "meldung": f"{pfad} fehlt"}])
    try:
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise SpecFehler([{"pfad": "(Datei)", "meldung": f"YAML-Fehler: {e}"}]) from None
    if not isinstance(daten, dict):
        raise SpecFehler([{"pfad": "(Wurzel)", "meldung": "Die Spezifikation muss ein YAML-Objekt sein"}])
    return daten


def schema_befunde(spec: dict) -> list[dict]:
    art = spec.get("art")
    datei = SCHEMA_ORDNER / f"{art}.schema.json"
    if art != "teil" or not datei.exists():
        return [{"pfad": "art", "meldung": f"Art {art!r} wird nicht unterstützt (Stufe 2: nur 'teil')"}]
    validator = Draft202012Validator(json.loads(datei.read_text(encoding="utf-8")))
    befunde = []
    for fehler in validator.iter_errors(spec):
        genau = best_match(fehler.context) if fehler.context else fehler
        befunde.append({"pfad": _pfad(genau.absolute_path), "meldung": genau.message})
    return sorted(befunde, key=lambda b: b["pfad"])


def _werte(obj, pfad: list, eltern: str | None = None):
    """Liefert (pfad, schlüssel, wert) für alle Zahlen und Ausdrücke unterhalb von obj."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _werte(v, [*pfad, k], k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _werte(v, [*pfad, i], eltern)
    elif (isinstance(obj, (int, float)) and not isinstance(obj, bool)) or ist_ausdruck(obj):
        yield pfad, eltern, obj


def _referenzen(obj, pfad: list):
    """Liefert (pfad, feature-id) für alle Verweise auf Features ("feature" und "features")."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "feature" and isinstance(v, str):
                yield [*pfad, k], v
            elif k == "features" and isinstance(v, list) and all(isinstance(x, str) for x in v):
                for i, x in enumerate(v):
                    yield [*pfad, k, i], x
            else:
                yield from _referenzen(v, [*pfad, k])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _referenzen(v, [*pfad, i])


def plausibel_befunde(spec: dict, auftrag_ordner: Path) -> list[dict]:
    befunde = []
    parameter = spec.get("parameter", {})
    features = spec["features"]

    ids = [f["id"] for f in features]
    for i, fid in enumerate(ids):
        if fid in ids[:i]:
            befunde.append({"pfad": f"features[{i}].id", "meldung": f"ID {fid!r} ist doppelt"})

    for i, f in enumerate(features):
        for pfad, ref in _referenzen({k: v for k, v in f.items() if k != "id"}, ["features", i]):
            if ref not in ids[:i]:
                befunde.append({"pfad": _pfad(pfad), "meldung": f"Verweis auf {ref!r}: kein früheres Feature"})
    for pfad, ref in _referenzen(spec.get("pruefung", {}), ["pruefung"]):
        if ref not in ids:
            befunde.append({"pfad": _pfad(pfad), "meldung": f"Verweis auf unbekanntes Feature {ref!r}"})

    for pfad, schluessel, roh in _werte({k: v for k, v in spec.items() if k != "parameter"}, []):
        try:
            wert = auswerten(roh, parameter)
        except AusdruckFehler as e:
            befunde.append({"pfad": _pfad(pfad), "meldung": str(e)})
            continue
        if schluessel in _POSITIV and "versatz" not in pfad and wert <= 0:
            befunde.append({"pfad": _pfad(pfad), "meldung": f"{schluessel} muss > 0 sein (ist {wert:g})"})
        if schluessel in _WINKEL and not 0 < wert <= 360:
            befunde.append({"pfad": _pfad(pfad), "meldung": f"winkel muss in (0, 360] liegen (ist {wert:g})"})

    for i, f in enumerate(features):
        elemente = f.get("skizze", {}).get("elemente", [])
        mittellinien = sum(1 for e in elemente if "mittellinie" in e)
        if f["typ"] == "rotation" and mittellinien != 1:
            befunde.append({"pfad": f"features[{i}].skizze.elemente", "meldung": "Rotation braucht genau eine mittellinie"})
        if f["typ"] != "rotation" and mittellinien:
            befunde.append({"pfad": f"features[{i}].skizze.elemente", "meldung": "mittellinie nur bei Rotation erlaubt"})
        if f["typ"] == "bohrung" and "senkung" in f:
            try:
                if auswerten(f["senkung"]["durchmesser"], parameter) <= auswerten(f["durchmesser"], parameter):
                    befunde.append({"pfad": f"features[{i}].senkung.durchmesser",
                                    "meldung": "Senkungsdurchmesser muss größer als der Bohrungsdurchmesser sein"})
            except AusdruckFehler:
                pass  # bereits oben gemeldet
        if f["typ"] == "skript":
            datei = auftrag_ordner / f["datei"]
            if not datei.exists():
                befunde.append({"pfad": f"features[{i}].datei", "meldung": f"{datei} fehlt"})
            else:
                for b in pruefe_skript(datei.read_text(encoding="utf-8")):
                    befunde.append({"pfad": f"features[{i}].datei", "meldung": f"Zeile {b['zeile']}: {b['meldung']}"})
    return befunde


def lade_spec(pfad: Path) -> dict:
    """Lädt und prüft eine Spezifikation; wirft SpecFehler mit allen Befunden."""
    spec = lade_yaml(pfad)
    befunde = schema_befunde(spec)
    if not befunde:
        befunde = plausibel_befunde(spec, pfad.parent)
    if befunde:
        raise SpecFehler(befunde)
    return spec
```

- [ ] **Step 6: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec -v`
Expected: alle grün (32 Tests in tests/spec).

- [ ] **Step 7: Commit**

```powershell
git add pyproject.toml schema swki/spec/laden.py tests/spec
git commit -m "spec: JSON-Schema, Laden und Plausibilitätsprüfung" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 4: Freigabe, Aufträge und Befehle `validieren`/`freigeben`

**Files:**
- Create: `swki/spec/freigabe.py`, `swki/auftrag.py`, `swki/spec/befehle.py`, `tests/spec/test_freigabe.py`, `tests/test_auftrag.py`, `tests/spec/test_befehle.py`
- Modify: `swki/cli.py` (`_befehlsgruppen`)

**Interfaces:**
- Consumes: `lade_spec`, `SpecFehler` (Task 3); `swki.konfig.Rechner`.
- Produces (`freigabe.py`): `PRUEF_FELDER`; `FreigabeFehler(SwkiFehler)` mit `daten["code"]` ∈ `FREIGABE_FEHLT`, `FREIGABE_VERALTET`; `pruefsumme(spec) -> str`; `freigabe_pfad(spec_pfad) -> Path`; `freigeben(spec_pfad, spec, zeitpunkt=None) -> dict`; `pruefe_freigabe(spec_pfad, spec) -> dict`.
- Produces (`auftrag.py`): `auftrag_name(spec_pfad)`, `auftrag_ordner(r, auftrag)`, `laeufe(r, auftrag) -> list[int]`, `naechster_lauf(r, auftrag)`, `lauf_ordner(r, auftrag, lauf)`, `dateiname(spec, auftrag, standard)`, `protokoll_ordner(spec_pfad)`, `lauf_datei(spec_pfad, lauf, art) -> Path` (`protokolle/<spec>.lauf-<n>.<art>.json`, art ∈ protokoll | pruefbericht | pruefer).
- Befehle: `swki validieren <spec>` → `{gueltig, spec, name, features, pruefsumme}`; `swki freigeben <spec>` → `{spec, pruefsumme, freigegeben}`.

- [ ] **Step 1: Failing tests schreiben**

`tests/spec/test_freigabe.py`:

```python
import copy
import json

import pytest

from swki.spec.freigabe import FreigabeFehler, freigabe_pfad, freigeben, pruefe_freigabe, pruefsumme

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
    assert eintrag == {"pruefsumme": pruefsumme(SPEC), "freigegeben": "2026-09-27T10:00:00"}
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
```

`tests/test_auftrag.py`:

```python
from pathlib import Path

from swki.auftrag import (
    auftrag_name, dateiname, lauf_datei, lauf_ordner, laeufe, naechster_lauf, protokoll_ordner,
)
from swki.konfig import Rechner


def _rechner(tmp_path) -> Rechner:
    return Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")


def test_auftrag_name(tmp_path):
    spec = tmp_path / "auftraege" / "A-4711" / "platte.yaml"
    assert auftrag_name(spec) == "A-4711"


def test_laeufe_und_naechster(tmp_path):
    r = _rechner(tmp_path)
    assert laeufe(r, "A") == [] and naechster_lauf(r, "A") == 1
    for n in (1, 2, 10):
        lauf_ordner(r, "A", n).mkdir(parents=True)
    (r.arbeitsordner / "A" / "lauf-x").mkdir()
    (r.arbeitsordner / "A" / "notiz.txt").write_text("x")
    assert laeufe(r, "A") == [1, 2, 10]
    assert naechster_lauf(r, "A") == 11


def test_dateiname():
    standard = {"namensschema": {"datei": "{auftrag}_{name}"}}
    assert dateiname({"name": "Formplatte_DS"}, "A-4711", standard) == "A-4711_Formplatte_DS"


def test_protokoll_ordner(tmp_path):
    assert protokoll_ordner(tmp_path / "a.yaml") == tmp_path / "protokolle"


def test_lauf_datei(tmp_path):
    assert lauf_datei(tmp_path / "platte.yaml", 2, "pruefbericht") == tmp_path / "protokolle" / "platte.lauf-2.pruefbericht.json"
```

`tests/spec/test_befehle.py`:

```python
import json

import yaml

from swki.cli import main

from .beispiel import GUELTIG


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_validieren_ok(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "validieren", str(pfad))
    assert code == 0 and daten["gueltig"] is True and daten["features"] == 6


def test_validieren_meldet_befunde(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump({**GUELTIG, "name": "mit Leerzeichen"}), encoding="utf-8")
    code, daten = _lauf(capsys, "validieren", str(pfad))
    assert code == 1
    assert daten["befunde"][0]["pfad"] == "name"


def test_freigeben(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "freigeben", str(pfad))
    assert code == 0 and len(daten["pruefsumme"]) == 64
    assert (tmp_path / "freigabe.json").exists()
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_freigabe.py tests/test_auftrag.py tests/spec/test_befehle.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementieren**

`swki/spec/freigabe.py`:

```python
"""Freigabe einer Spezifikation: Prüfsumme über die Anforderungen, gespeichert in freigabe.json.

Die Prüfsumme deckt nur die Anforderungen ab (Parameter, Material, Eigenschaften, Prüfwerte),
nicht den Bauweg (Features, Anker, Reihenfolge) – den darf Claude beim Nachbessern ändern.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from swki.cli import SwkiFehler

PRUEF_FELDER = ("art", "name", "parameter", "material", "eigenschaften", "pruefung")


class FreigabeFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str):
        super().__init__(meldung)
        self.daten = {"code": code}


def pruefsumme(spec: dict) -> str:
    kern = {feld: spec.get(feld) for feld in PRUEF_FELDER}
    text = json.dumps(kern, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def freigabe_pfad(spec_pfad: Path) -> Path:
    return spec_pfad.parent / "freigabe.json"


def _lies(pfad: Path) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}


def freigeben(spec_pfad: Path, spec: dict, zeitpunkt: str | None = None) -> dict:
    pfad = freigabe_pfad(spec_pfad)
    daten = _lies(pfad)
    eintrag = {
        "pruefsumme": pruefsumme(spec),
        "freigegeben": zeitpunkt or datetime.now().isoformat(timespec="seconds"),
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
    return eintrag
```

`swki/auftrag.py`:

```python
"""Aufträge: Ordner, Läufe und Dateinamen.

Ein Auftrag ist der Ordner, in dem die Spezifikation liegt (auftraege/<name>/ oder tests/referenz/<name>/).
Erzeugte Dateien landen je Lauf unter <arbeitsordner>/<auftrag>/lauf-<n>/.
"""

import re
from pathlib import Path

from swki.konfig import Rechner

_LAUF_RE = re.compile(r"^lauf-(\d+)$")


def auftrag_name(spec_pfad: Path) -> str:
    return spec_pfad.resolve().parent.name


def auftrag_ordner(r: Rechner, auftrag: str) -> Path:
    return r.arbeitsordner / auftrag


def laeufe(r: Rechner, auftrag: str) -> list[int]:
    ordner = auftrag_ordner(r, auftrag)
    if not ordner.is_dir():
        return []
    return sorted(int(m.group(1)) for p in ordner.iterdir() if p.is_dir() and (m := _LAUF_RE.match(p.name)))


def naechster_lauf(r: Rechner, auftrag: str) -> int:
    bisher = laeufe(r, auftrag)
    return bisher[-1] + 1 if bisher else 1


def lauf_ordner(r: Rechner, auftrag: str, lauf: int) -> Path:
    return auftrag_ordner(r, auftrag) / f"lauf-{lauf}"


def dateiname(spec: dict, auftrag: str, standard: dict) -> str:
    return standard["namensschema"]["datei"].format(auftrag=auftrag, name=spec["name"])


def protokoll_ordner(spec_pfad: Path) -> Path:
    return spec_pfad.parent / "protokolle"


def lauf_datei(spec_pfad: Path, lauf: int, art: str) -> Path:
    """protokolle/<spec>.lauf-<n>.<art>.json im Auftragsordner (art: protokoll | pruefbericht | pruefer)."""
    return protokoll_ordner(spec_pfad) / f"{spec_pfad.stem}.lauf-{lauf}.{art}.json"
```

`swki/spec/befehle.py`:

```python
"""Befehle "swki validieren <spec>" und "swki freigeben <spec>"."""

from pathlib import Path

from swki.spec.freigabe import freigeben, pruefsumme
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

In `swki/cli.py` `_befehlsgruppen` ersetzen durch:

```python
def _befehlsgruppen() -> list:
    from swki import rechner
    from swki.api import bauen
    from swki.spec import befehle as spec_befehle

    return [rechner, bauen, spec_befehle]
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle grün.

- [ ] **Step 5: Commit**

```powershell
git add swki/spec swki/auftrag.py swki/cli.py tests/spec tests/test_auftrag.py
git commit -m "spec: Freigabe mit Prüfsumme, Aufträge, swki validieren/freigeben" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 5: Bau-Fehler und Anker (reine Geometrie)

**Files:**
- Create: `swki/compiler/fehler.py`, `swki/compiler/anker.py`, `tests/compiler/test_anker.py`

**Interfaces:**
- Produces (`fehler.py`): Codes `REFERENZ_NICHT_GEFUNDEN`, `REFERENZ_MEHRDEUTIG`, `FEATURE_NICHT_ERZEUGT`, `REBUILD_FEHLER`, `SKIZZE_NICHT_BESTIMMT`, `SKRIPT_FEHLER`, `UNBEKANNTER_TYP`, `SPEICHERN_FEHLGESCHLAGEN`, `GLEICHUNG_FEHLER`, `SKIZZE_UNGUELTIG`, `MATERIAL_UNBEKANNT`; `BauFehler(code, meldung, schritt=None)` mit `.als_dict()`; `fehler_dict(e) -> dict`.
- Produces (`anker.py`): `Vektor`; `RICHTUNGEN`, `ACHSEN`; `AnkerFehler(BauFehler)`; Datenklassen `Flaeche(art, punkt, normale, achse, radius, abstand, objekt)`, `Kante(art, start, ende, richtung, abstand, objekt)`; `skalar`, `differenz`, `laenge`, `punkt_achse_abstand`; `flaeche_in_richtung(flaechen, richtung) -> Flaeche`; `senkrechte_kanten(kanten, richtung) -> list[Kante]`; `naechste(kandidaten, tol_mm, was)`; `zylinder_zu_punkten(zylinder, punkte, tol_mm) -> list[Flaeche]`. Spec §4: Toleranz 0,1 mm, `REFERENZ_NICHT_GEFUNDEN` mit nächstem Abstand, `REFERENZ_MEHRDEUTIG`.

- [ ] **Step 1: Failing tests schreiben**

`tests/compiler/test_anker.py`:

```python
import pytest

from swki.compiler.anker import (
    AnkerFehler, Flaeche, Kante, flaeche_in_richtung, naechste, punkt_achse_abstand, senkrechte_kanten,
    zylinder_zu_punkten,
)
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN

# Quader 100 x 20 x 60 (x, y, z), Unterseite auf y=0, Tasche mit Boden auf y=10
OBEN = Flaeche("ebene", (0, 20, 0), normale=(0, 1, 0))
TASCHENBODEN = Flaeche("ebene", (0, 10, 0), normale=(0, 1, 0))
UNTEN = Flaeche("ebene", (0, 0, 0), normale=(0, -1, 0))
RECHTS = Flaeche("ebene", (50, 10, 0), normale=(1, 0, 0))
ZYL = Flaeche("zylinder", (30, 0, 0), achse=(0, 1, 0), radius=4)


def test_flaeche_in_richtung_waehlt_aeusserste():
    assert flaeche_in_richtung([UNTEN, TASCHENBODEN, OBEN, ZYL], "+y") is OBEN
    assert flaeche_in_richtung([UNTEN, OBEN], "-y") is UNTEN


def test_flaeche_in_richtung_fehlt():
    with pytest.raises(AnkerFehler) as e:
        flaeche_in_richtung([OBEN, UNTEN], "+z")
    assert e.value.code == REFERENZ_NICHT_GEFUNDEN


def test_flaeche_in_richtung_mehrdeutig():
    zweite = Flaeche("ebene", (40, 20, 10), normale=(0, 1, 0))
    with pytest.raises(AnkerFehler) as e:
        flaeche_in_richtung([OBEN, zweite], "+y")
    assert e.value.code == REFERENZ_MEHRDEUTIG


def test_senkrechte_kanten():
    senkrecht = Kante("linie", (50, 0, 30), (50, 20, 30), richtung=(0, 1, 0))
    umgekehrt = Kante("linie", (-50, 20, 30), (-50, 0, 30), richtung=(0, -1, 0))
    waagrecht = Kante("linie", (-50, 20, 30), (50, 20, 30), richtung=(1, 0, 0))
    bogen = Kante("kreis", (0, 0, 0), (0, 0, 0))
    assert senkrechte_kanten([senkrecht, umgekehrt, waagrecht, bogen], (0, 1, 0)) == [senkrecht, umgekehrt]
    with pytest.raises(AnkerFehler):
        senkrechte_kanten([waagrecht], (0, 1, 0))


def test_naechste_eindeutig():
    a = Kante("linie", (0, 0, 0), (1, 0, 0), abstand=0.05)
    b = Kante("linie", (0, 0, 0), (0, 1, 0), abstand=3.0)
    assert naechste([b, a], 0.1, "Kante") is a


def test_naechste_nicht_gefunden_nennt_abstand():
    with pytest.raises(AnkerFehler, match="nächster Abstand 0.400 mm") as e:
        naechste([Kante("linie", (0, 0, 0), (1, 0, 0), abstand=0.4)], 0.1, "Kante")
    assert e.value.code == REFERENZ_NICHT_GEFUNDEN


def test_naechste_mehrdeutig():
    kanten = [Kante("linie", (0, 0, 0), (1, 0, 0), abstand=0.0), Kante("linie", (0, 0, 0), (0, 1, 0), abstand=0.0)]
    with pytest.raises(AnkerFehler) as e:
        naechste(kanten, 0.1, "Kante")
    assert e.value.code == REFERENZ_MEHRDEUTIG


def test_punkt_achse_abstand():
    assert punkt_achse_abstand((3, 7, 4), (0, 0, 0), (0, 1, 0)) == pytest.approx(5.0)


def test_zylinder_zu_punkten_in_positionsreihenfolge():
    senkung = Flaeche("zylinder", (30, 20, 0), achse=(0, 1, 0), radius=7)
    zweite = Flaeche("zylinder", (-30, 0, 0), achse=(0, -1, 0), radius=4)
    zugeordnet = zylinder_zu_punkten([zweite, senkung, ZYL], [(30, 20, 0), (-30, 20, 0)], 0.01)
    assert zugeordnet == [ZYL, zweite]


def test_zylinder_fehlt():
    with pytest.raises(AnkerFehler, match="Instanz 2"):
        zylinder_zu_punkten([ZYL], [(30, 20, 0), (0, 20, 0)], 0.01)
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_anker.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementieren**

`swki/compiler/fehler.py`:

```python
"""Fehler beim Bauen. Jeder Fehler trägt einen Code, der ins Protokoll geht."""

from swki.cli import SwkiFehler

REFERENZ_NICHT_GEFUNDEN = "REFERENZ_NICHT_GEFUNDEN"
REFERENZ_MEHRDEUTIG = "REFERENZ_MEHRDEUTIG"
FEATURE_NICHT_ERZEUGT = "FEATURE_NICHT_ERZEUGT"
REBUILD_FEHLER = "REBUILD_FEHLER"
SKIZZE_NICHT_BESTIMMT = "SKIZZE_NICHT_BESTIMMT"
SKRIPT_FEHLER = "SKRIPT_FEHLER"
UNBEKANNTER_TYP = "UNBEKANNTER_TYP"
SPEICHERN_FEHLGESCHLAGEN = "SPEICHERN_FEHLGESCHLAGEN"
GLEICHUNG_FEHLER = "GLEICHUNG_FEHLER"
SKIZZE_UNGUELTIG = "SKIZZE_UNGUELTIG"
MATERIAL_UNBEKANNT = "MATERIAL_UNBEKANNT"


class BauFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str, schritt: str | None = None):
        super().__init__(meldung)
        self.code = code
        self.schritt = schritt
        self.daten = {"code": code, "schritt": schritt}

    def als_dict(self) -> dict:
        return {"code": self.code, "schritt": self.schritt, "meldung": str(self)}


def fehler_dict(e: BaseException) -> dict:
    """Fehler als {"code", "schritt", "meldung"} für Protokolle; fremde Ausnahmen mit ihrem Typnamen als Code."""
    if isinstance(e, BauFehler):
        return e.als_dict()
    return {"code": type(e).__name__, "schritt": None, "meldung": str(e)}
```

`swki/compiler/anker.py`:

```python
"""Auswahl von Flächen und Kanten ohne Namen (reine Geometrie, ohne SolidWorks).

Die Kandidaten (Flaeche, Kante) liefert swki.compiler.topologie aus SolidWorks; alle Längen in mm.
"""

import math
from dataclasses import dataclass

from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN, BauFehler

Vektor = tuple[float, float, float]

RICHTUNGEN: dict[str, Vektor] = {
    "+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0),
    "+y": (0.0, 1.0, 0.0), "-y": (0.0, -1.0, 0.0),
    "+z": (0.0, 0.0, 1.0), "-z": (0.0, 0.0, -1.0),
}
ACHSEN: dict[str, Vektor] = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
_PARALLEL = 1.0 - 1e-6  # |cos| ab dem zwei Richtungen als parallel gelten
_GLEICH_MM = 1e-4       # Lageunterschied, unterhalb dessen zwei Kandidaten gleich weit liegen


class AnkerFehler(BauFehler):
    pass


@dataclass
class Flaeche:
    art: str  # "ebene" | "zylinder" | "sonstige"
    punkt: Vektor  # Ebene: Punkt auf der Fläche; Zylinder: Punkt auf der Achse
    normale: Vektor | None = None  # Ebene: Einheitsnormale, aus dem Material heraus
    achse: Vektor | None = None  # Zylinder: Einheitsrichtung der Achse
    radius: float | None = None
    abstand: float | None = None  # Abstand zu einem Anker-Punkt (von topologie gesetzt)
    objekt: object = None  # IFace2


@dataclass
class Kante:
    art: str  # "linie" | "kreis" | "sonstige"
    start: Vektor
    ende: Vektor
    richtung: Vektor | None = None  # Linie: Einheitsrichtung
    abstand: float | None = None
    objekt: object = None  # IEdge


def skalar(a: Vektor, b: Vektor) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def differenz(a: Vektor, b: Vektor) -> Vektor:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def laenge(a: Vektor) -> float:
    return math.sqrt(skalar(a, a))


def punkt_achse_abstand(punkt: Vektor, achspunkt: Vektor, achse: Vektor) -> float:
    d = differenz(punkt, achspunkt)
    t = skalar(d, achse)
    return math.sqrt(max(skalar(d, d) - t * t, 0.0))


def flaeche_in_richtung(flaechen: list[Flaeche], richtung: str) -> Flaeche:
    """Ebene Fläche mit Normale in `richtung`; bei mehreren die am weitesten in diese Richtung."""
    vek = RICHTUNGEN[richtung]
    passend = [f for f in flaechen if f.art == "ebene" and f.normale and skalar(f.normale, vek) > _PARALLEL]
    if not passend:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine ebene Fläche mit Normale {richtung}")
    passend.sort(key=lambda f: skalar(f.punkt, vek), reverse=True)
    if len(passend) > 1 and skalar(passend[0].punkt, vek) - skalar(passend[1].punkt, vek) < _GLEICH_MM:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{len(passend)} gleich weit außen liegende Flächen mit Normale {richtung}")
    return passend[0]


def senkrechte_kanten(kanten: list[Kante], richtung: Vektor) -> list[Kante]:
    """Gerade Kanten parallel zu `richtung` (z. B. Extrusionsrichtung)."""
    treffer = [k for k in kanten if k.art == "linie" and k.richtung and abs(skalar(k.richtung, richtung)) > _PARALLEL]
    if not treffer:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, "keine Kante parallel zur Feature-Richtung")
    return treffer


def naechste(kandidaten: list, tol_mm: float, was: str):
    """Genau ein Kandidat mit abstand <= tol_mm, sonst NICHT_GEFUNDEN bzw. MEHRDEUTIG."""
    if not kandidaten:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine {was} vorhanden")
    sortiert = sorted(kandidaten, key=lambda k: k.abstand)
    innerhalb = [k for k in sortiert if k.abstand <= tol_mm]
    if not innerhalb:
        raise AnkerFehler(
            REFERENZ_NICHT_GEFUNDEN,
            f"keine {was} innerhalb {tol_mm} mm (nächster Abstand {sortiert[0].abstand:.3f} mm)",
        )
    if len(innerhalb) > 1:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{len(innerhalb)} {was}n innerhalb {tol_mm} mm")
    return innerhalb[0]


def zylinder_zu_punkten(zylinder: list[Flaeche], punkte: list[Vektor], tol_mm: float) -> list[Flaeche]:
    """Ordnet jedem Punkt (z. B. Bohrungsposition) die Zylinderfläche zu, deren Achse durch ihn läuft.

    Bei mehreren passenden Zylindern (Bohrung mit Senkung) gewinnt der kleinste Radius.
    """
    ergebnis = []
    for i, p in enumerate(punkte, start=1):
        passend = [z for z in zylinder if z.art == "zylinder" and punkt_achse_abstand(p, z.punkt, z.achse) <= tol_mm]
        if not passend:
            raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine Zylinderfläche für Instanz {i} bei {p}")
        ergebnis.append(min(passend, key=lambda z: z.radius))
    return ergebnis
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_anker.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler tests/compiler
git commit -m "compiler: Fehlercodes und Anker-Auswahl ohne Namen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 6: Protokoll, Kontext, Handler-Registry und Bauablauf

**Files:**
- Create: `swki/compiler/protokoll.py`, `swki/compiler/kontext.py`, `swki/compiler/registry.py`, `swki/compiler/ablauf.py`, `tests/compiler/test_protokoll.py`, `tests/compiler/test_ablauf.py`

**Interfaces:**
- Consumes: `BauFehler`, `fehler_dict`, `UNBEKANNTER_TYP`, `GLEICHUNG_FEHLER` (Task 5); `Vektor` (Task 5); `auswerten`, `ist_ausdruck`, `sw_ausdruck` (Task 1); `swki.verbindung.mm`, `grad`.
- Produces: `Knoten(id, typ, status, dauer_s, sw_name, fehler, punkte)`; `Protokoll(auftrag, spec, lauf, sw_jahr, …)` mit `phase(name)`, `knoten_lauf(id, typ)`, `uebersprungen(id, typ)`, `als_dict()`, `schreibe(pfad)`; `FeatureErgebnis(features, richtung=None, punkte=[])` mit `.sw_name`; `Kontext(app, model, spec, spec_pfad, tol_mm, ergebnisse, achsen)` mit `wert(x)`, `m(x)`, `rad(x)`, `ergebnis(fid)`, `verknuepfe(masname, roh, vorzeichen=1)`; `HANDLER`, `handler(*typen)`, `alle_handler()` (importiert `swki.compiler.handler`, entsteht ab Task 9); `baue_features(ctx, protokoll, handler, nach_knoten) -> Exception | None`.
- `Knoten.punkte` trägt die Achspunkte von Bohrungsinstanzen ins Protokoll – Plan 2b misst daran, ohne Anker im fertigen Teil neu aufzulösen (der Ankerpunkt kann weggeschnitten sein).

- [ ] **Step 1: Failing tests schreiben**

`tests/compiler/test_protokoll.py`:

```python
import json

import pytest

from swki.compiler.fehler import REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.compiler.protokoll import Protokoll


def _protokoll() -> Protokoll:
    return Protokoll(auftrag="A", spec="platte.yaml", lauf=1, sw_jahr=2025)


def test_knoten_ok_mit_sw_name():
    p = _protokoll()
    with p.knoten_lauf("f1", "extrusion") as k:
        k.sw_name = "f1"
    [k] = p.knoten
    assert (k.id, k.status, k.sw_name) == ("f1", "ok", "f1")
    assert k.dauer_s >= 0


def test_knoten_fehler_wird_vermerkt_und_weitergereicht():
    p = _protokoll()
    with pytest.raises(BauFehler):
        with p.knoten_lauf("f2", "bohrung"):
            raise BauFehler(REFERENZ_NICHT_GEFUNDEN, "keine Fläche +y (nächster Abstand 0.4 mm)", schritt="flaeche")
    assert p.knoten[0].status == "fehler"
    assert p.knoten[0].fehler == {
        "code": REFERENZ_NICHT_GEFUNDEN, "schritt": "flaeche", "meldung": "keine Fläche +y (nächster Abstand 0.4 mm)",
    }


def test_fremde_ausnahme_wird_protokolliert():
    p = _protokoll()
    with pytest.raises(ValueError):
        with p.knoten_lauf("f3", "fase"):
            raise ValueError("kaputt")
    assert p.knoten[0].fehler == {"code": "ValueError", "schritt": None, "meldung": "kaputt"}


def test_phasen_summieren_sich():
    p = _protokoll()
    for _ in range(2):
        with p.phase("bauen"):
            pass
    assert list(p.phasen) == ["bauen"] and p.phasen["bauen"] >= 0


def test_schreiben(tmp_path):
    p = _protokoll()
    p.uebersprungen("f9", "skript")
    ziel = tmp_path / "lauf-1" / "protokoll.json"
    p.schreibe(ziel)
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    assert daten["auftrag"] == "A" and daten["knoten"][0]["status"] == "uebersprungen"
```

`tests/compiler/test_ablauf.py`:

```python
from dataclasses import dataclass, field

import pytest

from swki.compiler.ablauf import baue_features
from swki.compiler.fehler import REBUILD_FEHLER, UNBEKANNTER_TYP, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.protokoll import Protokoll


@dataclass
class _Feature:
    Name: str


@dataclass
class _Ctx:
    spec: dict
    ergebnisse: dict = field(default_factory=dict)


def _ok(ctx, f):
    return FeatureErgebnis([_Feature(f["id"])])


def _kaputt(ctx, f):
    raise BauFehler("REFERENZ_NICHT_GEFUNDEN", "keine Fläche +y", schritt="flaeche")


def _spec(*typen):
    return {"features": [{"id": f"f{i}", "typ": t} for i, t in enumerate(typen, start=1)]}


def _protokoll():
    return Protokoll("A", "a.yaml", 1, 2025)


def test_alle_knoten_ok():
    ctx, p, geprueft = _Ctx(_spec("extrusion", "fase")), _protokoll(), []
    fehler = baue_features(ctx, p, {"extrusion": _ok, "fase": _ok}, lambda c: geprueft.append(len(c.ergebnisse)))
    assert fehler is None
    assert [(k.id, k.status, k.sw_name) for k in p.knoten] == [("f1", "ok", "f1"), ("f2", "ok", "f2")]
    assert geprueft == [1, 2]  # nach jedem Knoten geprüft
    assert set(ctx.ergebnisse) == {"f1", "f2"}


def test_erster_fehler_stoppt_und_ueberspringt_rest():
    ctx, p = _Ctx(_spec("extrusion", "bohrung", "fase")), _protokoll()
    fehler = baue_features(ctx, p, {"extrusion": _ok, "bohrung": _kaputt, "fase": _ok}, lambda c: None)
    assert isinstance(fehler, BauFehler) and fehler.code == "REFERENZ_NICHT_GEFUNDEN"
    assert [k.status for k in p.knoten] == ["ok", "fehler", "uebersprungen"]
    assert p.knoten[1].fehler["schritt"] == "flaeche"


def test_unbekannter_typ():
    p = _protokoll()
    fehler = baue_features(_Ctx(_spec("gewinde")), p, {}, lambda c: None)
    assert fehler.code == UNBEKANNTER_TYP and p.knoten[0].status == "fehler"


def test_rebuildfehler_nach_knoten():
    def rebuild(ctx):
        raise BauFehler(REBUILD_FEHLER, "f1: Code 71", schritt="rebuild")

    p = _protokoll()
    fehler = baue_features(_Ctx(_spec("schnitt", "fase")), p, {"schnitt": _ok, "fase": _ok}, rebuild)
    assert fehler.code == REBUILD_FEHLER
    assert [k.status for k in p.knoten] == ["fehler", "uebersprungen"]


def test_com_fehler_wird_protokolliert():
    def com(ctx, f):
        raise OSError("Mitglied nicht gefunden")

    p = _protokoll()
    fehler = baue_features(_Ctx(_spec("extrusion")), p, {"extrusion": com}, lambda c: None)
    assert isinstance(fehler, OSError)
    assert p.knoten[0].fehler["code"] == "OSError"


@pytest.mark.parametrize("namen", [["f1"], ["f1", "f1_senkung"]])
def test_sw_name_mehrerer_features(namen):
    assert FeatureErgebnis([_Feature(n) for n in namen]).sw_name == ", ".join(namen)
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_protokoll.py tests/compiler/test_ablauf.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementieren**

`swki/compiler/protokoll.py`:

```python
"""Bauprotokoll (protokoll.json): Status und Dauer je Knoten, Phasenzeiten."""

import json
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from swki.compiler.fehler import fehler_dict


@dataclass
class Knoten:
    id: str
    typ: str
    status: str = "offen"  # offen | ok | fehler | uebersprungen
    dauer_s: float = 0.0
    sw_name: str | None = None
    fehler: dict | None = None
    punkte: list | None = None  # Bohrungsinstanzen: Achspunkte (mm), für die Prüfung


@dataclass
class Protokoll:
    auftrag: str
    spec: str
    lauf: int
    sw_jahr: int
    status: str = "laeuft"  # laeuft | ok | fehler
    gestartet: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    dauer_s: float = 0.0
    phasen: dict[str, float] = field(default_factory=dict)
    knoten: list[Knoten] = field(default_factory=list)
    dateien: dict[str, str] = field(default_factory=dict)
    fehler: dict | None = None

    @contextmanager
    def phase(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.phasen[name] = round(self.phasen.get(name, 0.0) + time.perf_counter() - t0, 3)

    @contextmanager
    def knoten_lauf(self, kid: str, typ: str):
        """Misst einen Knoten; Ausnahmen werden als Fehler vermerkt und weitergereicht."""
        k = Knoten(kid, typ)
        self.knoten.append(k)
        t0 = time.perf_counter()
        try:
            yield k
            k.status = "ok"
        except Exception as e:
            k.status = "fehler"
            k.fehler = fehler_dict(e)
            raise
        finally:
            k.dauer_s = round(time.perf_counter() - t0, 3)

    def uebersprungen(self, kid: str, typ: str) -> None:
        self.knoten.append(Knoten(kid, typ, status="uebersprungen"))

    def als_dict(self) -> dict:
        return asdict(self)

    def schreibe(self, pfad: Path) -> None:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps(self.als_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
```

`swki/compiler/kontext.py`:

```python
"""Baukontext: laufendes Dokument, Spezifikation und Ergebnisse der bereits gebauten Features."""

from dataclasses import dataclass, field
from pathlib import Path

from swki.compiler.anker import Vektor
from swki.compiler.fehler import GLEICHUNG_FEHLER, BauFehler
from swki.spec.ausdruck import auswerten, ist_ausdruck, sw_ausdruck
from swki.verbindung import grad, mm


@dataclass
class FeatureErgebnis:
    features: list  # erzeugte IFeature, das erste ist das Hauptfeature
    richtung: Vektor | None = None  # Extrusions-/Bohr-/Achsrichtung im Modell (für senkrechte_kanten)
    punkte: list[Vektor] = field(default_factory=list)  # Bohrungsinstanzen: Punkt auf der Achse (mm)

    @property
    def sw_name(self) -> str:
        return ", ".join(f.Name for f in self.features)


@dataclass
class Kontext:
    app: object
    model: object
    spec: dict
    spec_pfad: Path
    tol_mm: float
    ergebnisse: dict[str, FeatureErgebnis] = field(default_factory=dict)
    achsen: dict[str, tuple] = field(default_factory=dict)  # Referenzachsen je Teil (swki.compiler.handler.muster)

    def wert(self, x) -> float:
        """Zahl oder "=Ausdruck" → mm bzw. Grad."""
        return auswerten(x, self.spec.get("parameter", {}))

    def m(self, x) -> float:
        """Länge aus der Spezifikation (mm) → Meter für die API."""
        return mm(self.wert(x))

    def rad(self, x) -> float:
        return grad(self.wert(x))

    def ergebnis(self, fid: str) -> FeatureErgebnis:
        return self.ergebnisse[fid]

    def verknuepfe(self, masname: str, roh, vorzeichen: int = 1) -> None:
        """Maß per SW-Gleichung an Parameter binden, wenn roh ein Ausdruck ist (z. B. "=L").

        vorzeichen -1: das Maß (immer ein Betrag) entspricht dem negierten Ausdruck, z. B. Lage u = "=-L/2".
        """
        if not ist_ausdruck(roh):
            return
        rechts = sw_ausdruck(roh) if vorzeichen > 0 else f"-({sw_ausdruck(roh)})"
        if self.model.GetEquationMgr.Add2(-1, f'"{masname}" = {rechts}', True) < 0:
            raise BauFehler(GLEICHUNG_FEHLER, f"Gleichung für {masname} = {roh} abgelehnt", schritt="gleichung")
```

`swki/compiler/registry.py`:

```python
"""Handler-Registry: je Feature-Typ eine Funktion (ctx, feature_spec) -> FeatureErgebnis."""

from collections.abc import Callable

HANDLER: dict[str, Callable] = {}


def handler(*typen: str):
    def dekorator(funktion):
        for typ in typen:
            HANDLER[typ] = funktion
        return funktion

    return dekorator


def alle_handler() -> dict[str, Callable]:
    import swki.compiler.handler  # noqa: F401  (registriert alle Handler beim Import)

    return HANDLER
```

`swki/compiler/ablauf.py`:

```python
"""Bauablauf: Features in Reihenfolge bauen, nach jedem Knoten prüfen, beim ersten Fehler anhalten."""

from collections.abc import Callable

from swki.compiler.fehler import UNBEKANNTER_TYP, BauFehler
from swki.compiler.protokoll import Protokoll


def baue_features(ctx, protokoll: Protokoll, handler: dict[str, Callable], nach_knoten: Callable) -> Exception | None:
    """Baut alle Features; liefert den ersten Fehler (oder None). Folgende Knoten werden übersprungen."""
    fehler = None
    for f in ctx.spec["features"]:
        if fehler is not None:
            protokoll.uebersprungen(f["id"], f["typ"])
            continue
        try:
            with protokoll.knoten_lauf(f["id"], f["typ"]) as knoten:
                funktion = handler.get(f["typ"])
                if funktion is None:
                    raise BauFehler(UNBEKANNTER_TYP, f"Kein Handler für typ {f['typ']!r}", schritt="handler")
                ergebnis = funktion(ctx, f)
                ctx.ergebnisse[f["id"]] = ergebnis
                knoten.sw_name = ergebnis.sw_name
                knoten.punkte = [list(p) for p in ergebnis.punkte] or None
                nach_knoten(ctx)
        except Exception as e:  # jeder Fehler (auch COM) beendet den Lauf und steht im Protokoll
            fehler = e
    return fehler
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler -v`
Expected: alle grün.

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler tests/compiler
git commit -m "compiler: Protokoll, Kontext, Handler-Registry, Bauablauf" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 7: Late-bound Verbindung, SolidWorks-Grundfunktionen, Eigenschaften

**Files:**
- Modify: `swki/verbindung.py` (vollständig ersetzen), `tests/test_verbindung.py`, `tests/live/test_live_verbindung.py`
- Create: `swki/compiler/sw.py`, `swki/compiler/eigenschaften.py`, `tests/compiler/test_eigenschaften.py`, `tests/live_einzeln.py`

**Interfaces:**
- Produces (`verbindung.py`, zusätzlich zu Stufe 0/1): `byref_bool()`, `byref_str()`, `byref_variant()`, `r8_array(werte)`; `verbinde(jahr)` liefert immer `win32com.client.dynamic.CDispatch` (auch bei vorhandenem gen_py-Cache, S8/S9a).
- Produces (`sw.py`): Konstanten `SW_INPUT_DIM_VAL_ON_CREATE=10`, `SW_FULLY_CONSTRAINED=3`, `SW_SET_VALUE_IN_THIS_CONFIGURATION=1`, `SW_SAVEAS_*`; `neues_teil(app, vorlage)`, `schliesse(app, model)`, `standardebenen(model)`, `letztes_feature(model)`, `auswahl_leeren(model)`, `waehle(model, objekt, marke=0, anhaengen=False)`, `einstellung(app, toggle, wert)` (Kontextmanager), `ohne_inferenz(sketch_manager)` (Kontextmanager), `ursprung(model)`, `mathutil(app)`, `modell_zu_skizze(mu, skizze, punkt_mm)`, `teilebox_mm(model)`, `rebuild(model)` (wirft `REBUILD_FEHLER`), `speichere(model, pfad, kopie=False)`.
- Produces (`eigenschaften.py`): `globale_variablen(model, parameter)`, `material_passt(ist, soll)`, `materialien(datei)`, `finde_material(datenbanken, soll)`, `setze_material(app, model, soll) -> str`, `eigenschaften_fuer(spec, auftrag)`, `setze_eigenschaften(model, werte)`, `lies_eigenschaften(model)`.
- Material: `"1.2312"` passt zum Datenbanknamen `"1.2312 (40CrMnMoS8-6)"` (SolidWorks DIN Materials); `SetMaterialPropertyName2` meldet nie einen Fehler → immer zurücklesen (S9b).

- [ ] **Step 1: Failing tests schreiben**

`tests/test_verbindung.py` vollständig ersetzen:

```python
import math

from swki.verbindung import grad, in_mm, in_mm3, jahr_aus_revision, mm, wert


def test_jahr_aus_revision():
    assert jahr_aus_revision("33.2.0") == 2025
    assert jahr_aus_revision("34.0.1") == 2026


def test_einheiten():
    assert mm(1000) == 1.0
    assert in_mm(0.02) == 20.0
    assert in_mm3(1.2e-4) == 120000.0
    assert grad(180) == math.pi


def test_wert():
    assert wert(lambda: 5) == 5
    assert wert(5) == 5


def test_com_hilfen():
    import pythoncom

    from swki.verbindung import byref_bool, byref_str, byref_variant, r8_array

    a = r8_array([1, 2.5, -3])
    assert a.varianttype == pythoncom.VT_ARRAY | pythoncom.VT_R8 and a.value == [1.0, 2.5, -3.0]
    assert byref_bool().varianttype == pythoncom.VT_BYREF | pythoncom.VT_BOOL
    assert byref_variant().varianttype == pythoncom.VT_BYREF | pythoncom.VT_VARIANT
    assert byref_str().varianttype == pythoncom.VT_BYREF | pythoncom.VT_BSTR
```

`tests/live/test_live_verbindung.py` vollständig ersetzen:

```python
import pytest

from swki.konfig import lade_rechner
from swki.verbindung import jahr_aus_revision, verbinde, wert

pytestmark = pytest.mark.sw


def test_verbinde_mit_laufendem_solidworks():
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    assert jahr_aus_revision(wert(app.RevisionNumber)) == r.sw_jahr


def test_verbindung_ist_late_bound():
    import win32com.client.dynamic

    app = verbinde(lade_rechner().sw_jahr)
    assert type(app) is win32com.client.dynamic.CDispatch
    assert type(app.GetMathUtility) is win32com.client.dynamic.CDispatch  # auch Kindobjekte dynamisch
```

`tests/compiler/test_eigenschaften.py`:

```python
import pytest

from swki.compiler.eigenschaften import eigenschaften_fuer, finde_material, material_passt, materialien
from swki.compiler.fehler import MATERIAL_UNBEKANNT, BauFehler

XML = """<?xml version="1.0" encoding="UTF-16"?>
<mstns:materials xmlns:mstns="http://www.solidworks.com/sldmaterials" version="2008.03">
  <classification name="DIN Stahl (Kaltarbeitsstahl)">
    <material name="1.2312 (40CrMnMoS8-6)" matid="90"/>
    <material name="1.2379 (X153CrMoV12)" matid="91"/>
  </classification>
  <classification name="Sonstiges"><material name="1.2312" matid="1"/></classification>
</mstns:materials>
"""


def _db(tmp_path, name, text=XML):
    pfad = tmp_path / name
    pfad.write_bytes(text.encode("utf-16"))  # wie die echten *.sldmat: UTF-16 mit BOM
    return str(pfad)


def test_material_passt():
    assert material_passt("1.2312 (40CrMnMoS8-6)", "1.2312")
    assert material_passt("1.2312", "1.2312")
    assert not material_passt("1.23120", "1.2312")


def test_materialien_lesen(tmp_path):
    assert materialien(tmp_path.joinpath(_db(tmp_path, "din.sldmat"))) == [
        "1.2312 (40CrMnMoS8-6)", "1.2379 (X153CrMoV12)", "1.2312",
    ]


def test_exakter_name_gewinnt(tmp_path):
    db = _db(tmp_path, "din.sldmat")
    assert finde_material([db], "1.2312") == (db, "1.2312")


def test_eindeutiger_praefix(tmp_path):
    db = _db(tmp_path, "din.sldmat")
    assert finde_material([str(tmp_path / "fehlt.sldmat"), db], "1.2379") == (db, "1.2379 (X153CrMoV12)")


def test_unbekannt_und_mehrdeutig(tmp_path):
    db = _db(tmp_path, "din.sldmat")
    with pytest.raises(BauFehler) as e:
        finde_material([db], "1.4301")
    assert e.value.code == MATERIAL_UNBEKANNT
    zweite = _db(tmp_path, "zwei.sldmat", XML.replace('name="1.2312" matid="1"', 'name="1.2379 (anders)" matid="1"'))
    with pytest.raises(BauFehler, match="mehrdeutig"):
        finde_material([zweite], "1.2379")


def test_eigenschaften_fuer():
    spec = {"material": "1.2312", "eigenschaften": {"Benennung": "Platte", "Ersteller": "Konstrukteur"}}
    assert eigenschaften_fuer(spec, "A-1") == {
        "Ersteller": "Konstrukteur", "Auftrag": "A-1", "Material": "1.2312", "Benennung": "Platte",
    }
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_verbindung.py tests/compiler/test_eigenschaften.py -v`
Expected: FAIL (`ImportError: byref_str` bzw. `ModuleNotFoundError: swki.compiler.eigenschaften`).

- [ ] **Step 3: Implementieren**

`swki/verbindung.py` vollständig ersetzen:

```python
"""Anbindung an ein laufendes SolidWorks und Hilfen für pywin32."""

import math

from swki.cli import SwkiFehler

_REVISION_BASIS = 1992  # Revision 33 = SOLIDWORKS 2025, 34 = 2026


class SolidWorksNichtGestartet(SwkiFehler):
    pass


class FalscheVersion(SwkiFehler):
    pass


def jahr_aus_revision(revision: str) -> int:
    return int(str(revision).split(".")[0]) + _REVISION_BASIS


def mm(x: float) -> float:
    return x / 1000.0


def in_mm(x: float) -> float:
    return x * 1000.0


def in_mm3(x: float) -> float:
    return round(x * 1e9, 6)


def grad(x: float) -> float:
    return math.radians(x)


def wert(x):
    """Nur für Getter/Properties mit primitivem Rückgabewert (str, int, bool, …) geeignet:
    ist x nicht callable, wird x unverändert zurückgegeben; ist x callable, wird x() aufgerufen.

    Einschränkung (gefunden in Stufe 0, Spike S2/S3/S4, siehe docs/stufe0/ergebnisse): bei
    nullargumentigen Membern, die ein COM-Objekt liefern (z. B. IModelDoc2.FirstFeature,
    IFeature.GetNextFeature, IModelDocExtension.CreateMassProperty), ruft pywin32s dynamischer
    Dispatch den Member schon beim Attributzugriff auf – x ist dann bereits das Ergebnis, kein
    Methoden-Stub. Da jedes win32com.client.CDispatch-Objekt selbst __call__ definiert, ist auch
    dieses Ergebnis "callable", und wert() würde es fälschlich nochmal aufrufen
    (com_error 'Mitglied nicht gefunden'). Für solche Member reinen Attributzugriff ohne wert()
    verwenden, z. B. `model.FirstFeature` statt `wert(model.FirstFeature)`.
    """
    return x() if callable(x) else x


def callout_leer():
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)


def byref_long(start: int = 0):
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, start)


def byref_bool():
    """ByRef-bool-Ausgabeparameter (z. B. IFeature.GetErrorCode2); Wert danach in .value."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BOOL, False)


def byref_variant():
    """ByRef-Ausgabeparameter für Arrays/Objekte (z. B. GetWhatsWrong); Wert danach in .value."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, None)


def byref_str():
    """ByRef-String-Ausgabeparameter (z. B. GetMaterialPropertyName2, Get6); Wert danach in .value."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")


def r8_array(werte) -> object:
    """double-Array für COM. Eine rohe Python-Liste liefert bei IMathUtility.CreatePoint still falsche Werte."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(x) for x in werte])


def verbinde(jahr: int):
    """Hängt sich an ein laufendes SolidWorks (startet es nicht) und liefert es immer late-bound.

    win32com.client.GetActiveObject würde bei vorhandenem gen_py-Cache ein early-bound Objekt liefern,
    für das andere Aufrufregeln gelten (Spike S8/S9a). Der Weg über pythoncom + dynamic.Dispatch
    bleibt in jedem Fall dynamisch.
    """
    import pythoncom
    import win32com.client.dynamic

    major = jahr - _REVISION_BASIS
    unbekannt = None
    for progid in (f"SldWorks.Application.{major}", "SldWorks.Application"):
        try:
            unbekannt = pythoncom.GetActiveObject(progid)
            break
        except pythoncom.com_error:
            continue
    if unbekannt is None:
        raise SolidWorksNichtGestartet(f"SOLIDWORKS {jahr} läuft nicht. Bitte zuerst starten.")
    app = win32com.client.dynamic.Dispatch(unbekannt.QueryInterface(pythoncom.IID_IDispatch))
    ist = jahr_aus_revision(wert(app.RevisionNumber))
    if ist != jahr:
        raise FalscheVersion(f"Laufendes SOLIDWORKS ist {ist}, erwartet {jahr} (config/rechner.yaml).")
    return app
```

`swki/compiler/sw.py`:

```python
"""SolidWorks-Grundfunktionen für den Compiler (Late Binding, verifiziert in Spike S9a).

Regeln (siehe swki/wissen/pywin32-fallstricke.md): nullargumentige Member ohne "()",
Objekt-Parameter mit callout_leer(), Punkte/Arrays mit r8_array().
"""

from contextlib import contextmanager
from pathlib import Path

from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, REBUILD_FEHLER, SPEICHERN_FEHLGESCHLAGEN, BauFehler
from swki.verbindung import byref_long, byref_variant, callout_leer, in_mm, mm, r8_array

SW_INPUT_DIM_VAL_ON_CREATE = 10  # swUserPreferenceToggle_e.swInputDimValOnCreate
SW_FULLY_CONSTRAINED = 3  # swConstrainedStatus_e.swFullyConstrained
SW_SET_VALUE_IN_THIS_CONFIGURATION = 1  # swSetValueInConfiguration_e
SW_SAVEAS_CURRENT_VERSION = 0  # swSaveAsVersion_e
SW_SAVEAS_SILENT = 1  # swSaveAsOptions_e
SW_SAVEAS_COPY = 2


def neues_teil(app, vorlage: Path):
    model = app.NewDocument(str(vorlage), 0, 0, 0)
    if model is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"NewDocument mit {vorlage} fehlgeschlagen", schritt="dokument")
    return model


def schliesse(app, model) -> None:
    """Schließt genau dieses (selbst angelegte) Dokument."""
    app.CloseDoc(model.GetTitle)


def standardebenen(model) -> list:
    """[Ebene vorne, Ebene oben, Ebene rechts] – die ersten drei RefPlane-Features (sprachunabhängig)."""
    ebenen, f = [], model.FirstFeature
    while f is not None and len(ebenen) < 3:
        if f.GetTypeName2 == "RefPlane":
            ebenen.append(f)
        f = f.GetNextFeature
    return ebenen


def letztes_feature(model):
    return model.FeatureByPositionReverse(0)


def auswahl_leeren(model) -> None:
    model.ClearSelection2(True)


def waehle(model, objekt, marke: int = 0, anhaengen: bool = False) -> None:
    """Face, Edge, Feature oder Skizzensegment mit Marke selektieren (Select4 + SelectData)."""
    daten = model.SelectionManager.CreateSelectData
    daten.Mark = marke
    if not objekt.Select4(anhaengen, daten):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Auswahl mit Marke {marke} fehlgeschlagen", schritt="auswahl")


@contextmanager
def einstellung(app, toggle: int, wert: bool):
    """Benutzereinstellung nur vorübergehend umschalten; alter Wert wird immer wiederhergestellt."""
    alt = app.GetUserPreferenceToggle(toggle)
    app.SetUserPreferenceToggle(toggle, wert)
    try:
        yield
    finally:
        app.SetUserPreferenceToggle(toggle, alt)


@contextmanager
def ohne_inferenz(sketch_manager):
    """AddToDB=True: keine automatischen Beziehungen beim Erzeugen (S9a); danach immer zurück."""
    sketch_manager.AddToDB = True
    try:
        yield
    finally:
        sketch_manager.AddToDB = False


def ursprung(model):
    """Ursprungspunkt des Teils (Skizzenpunkt des Features "OriginProfileFeature"), sprachunabhängig.

    Bezug für die Lagemaße der Skizzen (swki.compiler.skizze).
    """
    f = model.FirstFeature
    while f is not None and f.GetTypeName2 != "OriginProfileFeature":
        f = f.GetNextFeature
    if f is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, "Ursprung nicht gefunden", schritt="skizze")
    auswahl_leeren(model)
    model.Extension.SelectByID2(f"Point1@{f.Name}", "EXTSKETCHPOINT", 0, 0, 0, False, 0, callout_leer(), 0)
    punkt = model.SelectionManager.GetSelectedObject6(1, -1)
    auswahl_leeren(model)
    if punkt is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, "Ursprungspunkt nicht auswählbar", schritt="skizze")
    return punkt


def mathutil(app):
    mu = app.GetMathUtility
    mu._FlagAsMethod("CreatePoint", "CreateVector", "CreateTransform")  # sonst Aufruf beim Attributzugriff
    return mu


def modell_zu_skizze(mu, skizze, punkt_mm) -> tuple[float, float]:
    """Modellpunkt (mm) → Skizzenkoordinaten (m) der offenen Skizze."""
    p = mu.CreatePoint(r8_array([mm(x) for x in punkt_mm]))
    u, v, _ = p.MultiplyTransform(skizze.ModelToSketchTransform).ArrayData
    return u, v


def teilebox_mm(model) -> list[float]:
    """[xmin, ymin, zmin, xmax, ymax, zmax] in mm."""
    return [in_mm(x) for x in model.GetPartBox(True)]


def rebuild(model) -> None:
    """Baut neu auf; wirft REBUILD_FEHLER mit Feature und Code, wenn SolidWorks Fehler meldet."""
    ok = model.EditRebuild3
    if model.Extension.GetWhatsWrongCount == 0 and ok:
        return
    features, codes, warnungen = byref_variant(), byref_variant(), byref_variant()
    model.Extension.GetWhatsWrong(features, codes, warnungen)
    fehler = [
        f"{f.Name}: Code {c}"
        for f, c, w in zip(features.value or (), codes.value or (), warnungen.value or ())
        if not w
    ]
    if fehler or not ok:
        raise BauFehler(REBUILD_FEHLER, "; ".join(fehler) or "EditRebuild3 meldet Fehler", schritt="rebuild")


def speichere(model, pfad: Path, kopie: bool = False) -> None:
    """IModelDocExtension.SaveAs3; Format über die Endung (.sldprt, .step, .png …).

    Ohne kopie wird das Dokument beim Speichern als .sldprt umbenannt (Titel danach neu lesen, S9b).
    """
    pfad.parent.mkdir(parents=True, exist_ok=True)
    fehler, warnungen = byref_long(), byref_long()
    optionen = SW_SAVEAS_SILENT | (SW_SAVEAS_COPY if kopie else 0)
    ok = model.Extension.SaveAs3(str(pfad), SW_SAVEAS_CURRENT_VERSION, optionen, callout_leer(), callout_leer(),
                                 fehler, warnungen)
    if not ok or fehler.value:
        raise BauFehler(SPEICHERN_FEHLGESCHLAGEN, f"{pfad.name}: Fehler {fehler.value}", schritt="speichern")
```

`swki/compiler/eigenschaften.py`:

```python
"""Globale Variablen (Parameter), Material und benutzerdefinierte Eigenschaften eines Teils (Spike S9a/S9b)."""

import xml.etree.ElementTree as ET
from pathlib import Path

from swki.compiler.fehler import GLEICHUNG_FEHLER, MATERIAL_UNBEKANNT, BauFehler
from swki.verbindung import byref_bool, byref_str

SW_CUSTOM_INFO_TEXT = 30  # swCustomInfoType_e.swCustomInfoText
SW_CUSTOM_PROPERTY_REPLACE_VALUE = 2  # swCustomPropertyAddOption_e
ERSTELLER = "SolidWorks-KI"


def globale_variablen(model, parameter: dict) -> None:
    """Jeder Parameter wird eine SW-Gleichung "Name" = Wert (Dokumenteinheit mm bzw. Grad, Spike S9a Baustein 5)."""
    gleichungen = model.GetEquationMgr
    for name, wert in parameter.items():
        if gleichungen.Add2(-1, f'"{name}" = {wert!r}', True) < 0:
            raise BauFehler(GLEICHUNG_FEHLER, f"Globale Variable {name} = {wert} abgelehnt", schritt="parameter")


def material_passt(ist: str, soll: str) -> bool:
    """"1.2312" passt zu "1.2312 (40CrMnMoS8-6)" (Name in der SW-Materialdatenbank)."""
    return ist == soll or ist.startswith(f"{soll} (")


def materialien(datei: Path) -> list[str]:
    """Materialnamen einer *.sldmat (XML, UTF-16 mit BOM – als Bytes parsen)."""
    return [m.get("name") for m in ET.fromstring(datei.read_bytes()).iter("material")]


def finde_material(datenbanken: list[str], soll: str) -> tuple[str, str]:
    """(Datenbankpfad, voller Materialname); exakter Name vor eindeutigem Präfix-Treffer."""
    treffer = [(db, name) for db in datenbanken if Path(db).exists() for name in materialien(Path(db))
               if material_passt(name, soll)]
    exakt = [t for t in treffer if t[1] == soll]
    if exakt:
        return exakt[0]
    namen = sorted({name for _, name in treffer})
    if len(namen) == 1:
        return treffer[0]
    grund = f"mehrdeutig: {namen}" if namen else "in keiner Materialdatenbank gefunden"
    raise BauFehler(MATERIAL_UNBEKANNT, f"Material {soll!r} {grund}", schritt="material")


def setze_material(app, model, soll: str) -> str:
    datenbank, name = finde_material(list(app.GetMaterialDatabases or ()), soll)
    model.SetMaterialPropertyName2("", datenbank, name)  # liefert immer None (S9b) → zurücklesen
    gesetzt = model.GetMaterialPropertyName2("", byref_str())
    if gesetzt != name:
        raise BauFehler(MATERIAL_UNBEKANNT, f"Material {name!r} ließ sich nicht zuweisen", schritt="material")
    return name


def eigenschaften_fuer(spec: dict, auftrag: str) -> dict[str, str]:
    werte = {"Ersteller": ERSTELLER, "Auftrag": auftrag}
    if "material" in spec:
        werte["Material"] = spec["material"]
    werte.update(spec.get("eigenschaften", {}))
    return werte


def setze_eigenschaften(model, werte: dict[str, str]) -> None:
    verwalter = model.Extension.CustomPropertyManager("")
    for name, wert in werte.items():
        if verwalter.Add3(name, SW_CUSTOM_INFO_TEXT, wert, SW_CUSTOM_PROPERTY_REPLACE_VALUE) != 0:
            raise BauFehler(GLEICHUNG_FEHLER, f"Eigenschaft {name} ließ sich nicht setzen", schritt="eigenschaften")


def lies_eigenschaften(model) -> dict[str, str]:
    verwalter = model.Extension.CustomPropertyManager("")
    werte = {}
    for name in verwalter.GetNames or ():
        wert, aufgeloest, war_cache, verknuepft = byref_str(), byref_str(), byref_bool(), byref_bool()
        verwalter.Get6(name, False, wert, aufgeloest, war_cache, verknuepft)
        werte[name] = aufgeloest.value
    return werte
```

`tests/live_einzeln.py`:

```python
"""Live-Tests einzeln mit Zeitlimit ausführen (ein hängendes SolidWorks blockiert sonst die ganze Suite).

Aufruf:  .venv\\Scripts\\python.exe tests\\live_einzeln.py tests\\live\\test_live_extrusion.py [weitere …] [--zeit 120]
Jeder Test läuft in einem eigenen pytest-Prozess. Beim ersten Zeitüberschreiten wird abgebrochen (Exit 2) –
dann SolidWorks prüfen (reagiert es?) und die Benutzereinstellung swInputDimValOnCreate kontrollieren,
weil ein hart beendeter Prozess sie nicht mehr zurücksetzen konnte.
"""

import argparse
import subprocess
import sys


def tests_in(pfad: str) -> list[str]:
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "sw", pfad, "--collect-only", "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True, encoding="utf-8",
    )
    return [z.strip() for z in ergebnis.stdout.splitlines() if "::" in z]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pfade", nargs="+")
    parser.add_argument("--zeit", type=int, default=120, help="Sekunden je Test")
    args = parser.parse_args()
    fehler = 0
    for pfad in args.pfade:
        for test in tests_in(pfad):
            try:
                lauf = subprocess.run(
                    [sys.executable, "-m", "pytest", "-m", "sw", test, "-q", "-p", "no:cacheprovider"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=args.zeit,
                )
            except subprocess.TimeoutExpired:
                print(f"ZEITLIMIT {test} – SolidWorks prüfen, Einstellungen kontrollieren", flush=True)
                return 2
            if lauf.returncode == 0:
                print(f"OK      {test}", flush=True)
            else:
                fehler += 1
                print(f"FEHLER  {test}", flush=True)
                print("\n".join(z for z in lauf.stdout.splitlines() if z.startswith("E ")), flush=True)
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Unit-Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle grün (ohne SolidWorks).

- [ ] **Step 5: Live-Test (SolidWorks 2025 geöffnet)**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_verbindung.py`
Expected: 2× `OK`; `test_verbindung_ist_late_bound` bestätigt dynamisches Dispatch.

- [ ] **Step 6: Commit**

```powershell
git add swki/verbindung.py swki/compiler tests/test_verbindung.py tests/live/test_live_verbindung.py tests/compiler tests/live_einzeln.py
git commit -m "compiler: late-bound Verbindung, SW-Grundfunktionen, Material und Eigenschaften" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 8: Topologie und voll bestimmte Skizzen

**Files:**
- Create: `swki/compiler/topologie.py`, `swki/compiler/skizze.py`, `tests/compiler/test_skizze_geometrie.py`

**Interfaces:**
- Consumes: `anker.*` (Task 5), `sw.*` (Task 7), `ist_ausdruck` (Task 1), `Kontext.verknuepfe` (Task 6).
- Produces (`topologie.py`): `flaeche_aus(face)`, `kante_aus(edge)`, `flaechen(feature)`, `kanten(app, feature)`, `koerper(model)`, `mit_abstand(kandidaten, punkt_mm)`, `loese_flaeche(ctx, anker) -> Flaeche`, `loese_kanten(ctx, anker) -> list[Kante]`.
- Produces (`skizze.py`): `STANDARD`, `NORMALE`; `Skizzenebene(objekt, orientierung, lage, normale)`; `modellpunkt(orientierung, u, v, lage)`; `orientierung_der_normale(normale)`; `ebene_aus_flaeche(flaeche)`; `ebene_aufloesen(ctx, ebene) -> Skizzenebene`; `Skizzierer(ctx, se, skizze)` mit `zu_skizze(u, v)`, `groesse(...)`, `hat_punkt(u, v)`, `lage(roh_uv, text_uv)`, `element(element)`; `skizziere(ctx, ebene, elemente, name) -> (feature, Skizzenebene)`; `richtung(se, umkehren)`.
- Siehe „Befunde beim Planschreiben“ 1–3: AddToDB=True, alle Maße selbst, Rechteck über CreateCornerRectangle, Lage zum Ursprung; Maße mit Ausdruck werden nach dem Umbenennen der Skizze per Gleichung gebunden (Maße sind Beträge → `vorzeichen`). Die SolidWorks-Teile werden live in Task 9 geprüft.

- [ ] **Step 1: Failing tests schreiben**

`tests/compiler/test_skizze_geometrie.py`:

```python
import pytest

from swki.compiler.anker import Flaeche
from swki.compiler.fehler import BauFehler
from swki.compiler.skizze import _halb_weg, ebene_aus_flaeche, modellpunkt, orientierung_der_normale
from swki.spec.ausdruck import auswerten


@pytest.mark.parametrize(
    ("orientierung", "erwartet"),
    [("vorne", (30, 10, 5)), ("oben", (30, 5, -10)), ("rechts", (5, 10, -30))],
)
def test_modellpunkt_wie_in_s9a(orientierung, erwartet):
    # S9a Baustein 1: vorne X=u,Y=v · oben X=u,Z=-v · rechts Z=-u,Y=v; Lage 5 auf der Normalenachse
    assert modellpunkt(orientierung, 30, 10, 5) == erwartet


@pytest.mark.parametrize(
    ("normale", "orientierung"),
    [((0, 1, 0), "oben"), ((0, -1, 0), "oben"), ((1, 0, 0), "rechts"), ((0, 0, -1), "vorne")],
)
def test_orientierung_der_normale(normale, orientierung):
    assert orientierung_der_normale(normale) == orientierung


def test_schraege_flaeche_wird_abgelehnt():
    with pytest.raises(BauFehler, match="nicht achsparallel"):
        orientierung_der_normale((0.0, 0.7071, 0.7071))


def test_ebene_aus_deckflaeche():
    se = ebene_aus_flaeche(Flaeche("ebene", (12, 46, -3), normale=(0, 1, 0)))
    assert (se.orientierung, se.lage, se.normale) == ("oben", 46, (0, 1, 0))


def test_zylinder_ist_keine_skizzenebene():
    with pytest.raises(BauFehler, match="ebenen Flächen"):
        ebene_aus_flaeche(Flaeche("zylinder", (0, 0, 0), achse=(0, 1, 0), radius=4))


@pytest.mark.parametrize(("mitte", "groesse", "erwartet"), [(0, 100, -50), (10, 20.5, -0.25), ("=M", 100, "=(M) - 100 / 2"),
                                                             (0, "=L", "=0 - (L) / 2"), ("=M+1", "=L", "=(M+1) - (L) / 2")])
def test_halb_weg(mitte, groesse, erwartet):
    ergebnis = _halb_weg(mitte, groesse)
    assert ergebnis == erwartet
    assert auswerten(ergebnis, {"M": 3, "L": 10}) == auswerten(mitte, {"M": 3}) - auswerten(groesse, {"L": 10}) / 2
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_skizze_geometrie.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementieren**

`swki/compiler/topologie.py`:

```python
"""SolidWorks-Topologie → Flaeche/Kante (swki.compiler.anker) und Auflösung der Anker aus der Spezifikation.

Formate verifiziert in Spike S9a: IFace2.Normal = äußere Normale (nicht PlaneParams verwenden),
CylinderParams = (ox, oy, oz, ax, ay, az, r), LineParams = (px, py, pz, dx, dy, dz),
CircleParams = (cx, cy, cz, ax, ay, az, r), GetClosestPointOn(x, y, z) → 5 Werte, die ersten 3 sind der Punkt.
"""

from swki.compiler.anker import (
    Flaeche, Kante, flaeche_in_richtung, laenge, naechste, senkrechte_kanten,
)
from swki.compiler.fehler import REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.verbindung import in_mm, mm

SW_SOLID_BODY = 0  # swBodyType_e.swSolidBody


def _mm3(werte) -> tuple[float, float, float]:
    return (in_mm(werte[0]), in_mm(werte[1]), in_mm(werte[2]))


def flaeche_aus(face) -> Flaeche:
    s = face.GetSurface
    if s.IsPlane:
        p = s.PlaneParams
        return Flaeche("ebene", _mm3(p[3:6]), normale=tuple(face.Normal), objekt=face)
    if s.IsCylinder:
        c = s.CylinderParams
        return Flaeche("zylinder", _mm3(c[0:3]), achse=tuple(c[3:6]), radius=in_mm(c[6]), objekt=face)
    box = face.GetBox
    mitte = ((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2)
    return Flaeche("sonstige", _mm3(mitte), objekt=face)


def kante_aus(edge) -> Kante:
    c = edge.GetCurve
    start_v, ende_v = edge.GetStartVertex, edge.GetEndVertex
    if c.IsLine:
        lp = c.LineParams
        return Kante("linie", _mm3(start_v.GetPoint), _mm3(ende_v.GetPoint), richtung=tuple(lp[3:6]), objekt=edge)
    if c.IsCircle:
        cp = c.CircleParams
        mitte = _mm3(cp[0:3])
        start = _mm3(start_v.GetPoint) if start_v is not None else mitte
        ende = _mm3(ende_v.GetPoint) if ende_v is not None else mitte
        return Kante("kreis", start, ende, richtung=tuple(cp[3:6]), objekt=edge)
    start = _mm3(start_v.GetPoint) if start_v is not None else (0.0, 0.0, 0.0)
    ende = _mm3(ende_v.GetPoint) if ende_v is not None else start
    return Kante("sonstige", start, ende, objekt=edge)


def flaechen(feature) -> list[Flaeche]:
    return [flaeche_aus(f) for f in (feature.GetFaces or ())]


def _eindeutig(app, edges) -> list:
    eindeutig = []
    for e in edges:
        if not any(app.IsSame(e, x) == 1 for x in eindeutig):  # 1 = swObjectSame
            eindeutig.append(e)
    return eindeutig


def kanten(app, feature) -> list[Kante]:
    edges = [e for f in (feature.GetFaces or ()) for e in (f.GetEdges or ())]
    return [kante_aus(e) for e in _eindeutig(app, edges)]


def koerper(model) -> list:
    """Volumenkörper. Achtung (S9b): IBody2 hat Typinfo – nullargumentige Methoden MIT () aufrufen."""
    return list(model.GetBodies2(SW_SOLID_BODY, False) or ())


def mit_abstand(kandidaten: list, punkt_mm) -> list:
    """Setzt .abstand (mm) jedes Kandidaten zum Punkt über GetClosestPointOn."""
    x, y, z = (mm(v) for v in punkt_mm)
    for k in kandidaten:
        q = k.objekt.GetClosestPointOn(x, y, z)
        k.abstand = laenge((in_mm(q[0]) - punkt_mm[0], in_mm(q[1]) - punkt_mm[1], in_mm(q[2]) - punkt_mm[2]))
    return kandidaten


def loese_flaeche(ctx, anker: dict) -> Flaeche:
    """{feature, flaeche: "+y"} oder {nahe: [x, y, z]} → Flaeche."""
    if "nahe" in anker:
        punkt = tuple(ctx.wert(v) for v in anker["nahe"])
        alle = [flaeche_aus(f) for b in koerper(ctx.model) for f in (b.GetFaces() or ())]
        return naechste(mit_abstand(alle, punkt), ctx.tol_mm, "Fläche")
    feature = ctx.ergebnis(anker["feature"]).features[0]
    return flaeche_in_richtung(flaechen(feature), anker["flaeche"])


def loese_kanten(ctx, anker: dict) -> list[Kante]:
    """{feature, auswahl}, {feature, kanten_an} oder {nahe} → Kanten."""
    if "nahe" in anker:
        punkt = tuple(ctx.wert(v) for v in anker["nahe"])
        alle = [kante_aus(e) for b in koerper(ctx.model) for e in (b.GetEdges() or ())]
        return [naechste(mit_abstand(alle, punkt), ctx.tol_mm, "Kante")]
    ergebnis = ctx.ergebnis(anker["feature"])
    feature = ergebnis.features[0]
    if "kanten_an" in anker:
        flaeche = flaeche_in_richtung(flaechen(feature), anker["kanten_an"])
        return [kante_aus(e) for e in (flaeche.objekt.GetEdges or ())]
    alle = kanten(ctx.app, feature)
    if anker["auswahl"] == "alle_kanten":
        return alle
    if ergebnis.richtung is None:
        raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"Feature {anker['feature']!r} hat keine Richtung für senkrechte_kanten")
    return senkrechte_kanten(alle, ergebnis.richtung)
```

`swki/compiler/skizze.py`:

```python
"""Skizzenebenen und voll bestimmte Skizzen aus der Spezifikation (verifiziert in Spike S9a, Bausteine 1–4).

2D-Koordinaten (u, v) einer Skizze folgen der Standardebene gleicher Orientierung:
vorne: X=u, Y=v · oben: X=u, Z=−v · rechts: Z=−u, Y=v. Die dritte Koordinate ist die Lage der Ebene.
Der Compiler rechnet (u, v) in einen Modellpunkt und von dort über ModelToSketchTransform in die Skizze um,
damit Skizzen auf Flächen und versetzten Ebenen genauso funktionieren.
"""

from dataclasses import dataclass

from swki.compiler import sw
from swki.compiler.anker import Flaeche, Vektor
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, SKIZZE_NICHT_BESTIMMT, SKIZZE_UNGUELTIG, BauFehler
from swki.compiler.topologie import loese_flaeche
from swki.spec.ausdruck import ist_ausdruck
from swki.verbindung import mm

STANDARD = {"vorne": 0, "oben": 1, "rechts": 2}  # Index in sw.standardebenen()
NORMALE = {"vorne": (0.0, 0.0, 1.0), "oben": (0.0, 1.0, 0.0), "rechts": (1.0, 0.0, 0.0)}
_ACHSE_ZU_ORIENTIERUNG = {0: "rechts", 1: "oben", 2: "vorne"}
_ORIENTIERUNG_ZU_ACHSE = {o: i for i, o in _ACHSE_ZU_ORIENTIERUNG.items()}
REF_PLANE_ABSTAND = 8  # swRefPlaneReferenceConstraint_Distance
REF_PLANE_UMKEHREN = 256  # swRefPlaneReferenceConstraint_OptionFlip
_MASS_ABSTAND_MM = 8.0  # Abstand der Maßtexte von der Geometrie


@dataclass
class Skizzenebene:
    objekt: object  # IFeature (Ebene) oder IFace2
    orientierung: str  # "vorne" | "oben" | "rechts"
    lage: float  # mm, Koordinate der Ebene auf ihrer Normalenachse
    normale: Vektor  # Richtung, in die ein Aufsatz standardmäßig wächst


def modellpunkt(orientierung: str, u: float, v: float, lage: float) -> Vektor:
    if orientierung == "vorne":
        return (u, v, lage)
    if orientierung == "oben":
        return (u, lage, -v)
    return (lage, v, -u)


def orientierung_der_normale(normale: Vektor) -> str:
    for i, c in enumerate(normale):
        if abs(c) > 1 - 1e-6:
            return _ACHSE_ZU_ORIENTIERUNG[i]
    raise BauFehler(SKIZZE_UNGUELTIG, f"Skizzenfläche ist nicht achsparallel (Normale {normale})", schritt="ebene")


def ebene_aus_flaeche(flaeche: Flaeche) -> Skizzenebene:
    if flaeche.art != "ebene":
        raise BauFehler(SKIZZE_UNGUELTIG, "Skizzen nur auf ebenen Flächen", schritt="ebene")
    orientierung = orientierung_der_normale(flaeche.normale)
    lage = flaeche.punkt[_ORIENTIERUNG_ZU_ACHSE[orientierung]]
    return Skizzenebene(flaeche.objekt, orientierung, lage, flaeche.normale)


def ebene_aufloesen(ctx, ebene) -> Skizzenebene:
    if isinstance(ebene, Skizzenebene):
        return ebene
    ebenen = sw.standardebenen(ctx.model)
    if isinstance(ebene, str):
        return Skizzenebene(ebenen[STANDARD[ebene]], ebene, 0.0, NORMALE[ebene])
    if "versatz" in ebene:
        basis = ebene["versatz"]["ebene"]
        abstand = ctx.wert(ebene["versatz"]["abstand"])
        sw.auswahl_leeren(ctx.model)
        sw.waehle(ctx.model, ebenen[STANDARD[basis]], 0)
        art = REF_PLANE_ABSTAND | (REF_PLANE_UMKEHREN if abstand < 0 else 0)
        neu = ctx.model.FeatureManager.InsertRefPlane(art, mm(abs(abstand)), 0, 0.0, 0, 0.0)
        if neu is None:
            raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Versetzte Ebene {basis} {abstand:g} mm", schritt="ebene")
        return Skizzenebene(neu, basis, abstand, NORMALE[basis])
    return ebene_aus_flaeche(loese_flaeche(ctx, ebene))


def _position_mm(se: Skizzenebene, u: float, v: float) -> Vektor:
    return modellpunkt(se.orientierung, u, v, se.lage)


def _halb_weg(mitte, groesse):
    """Wert "mitte - groesse/2" als Zahl oder Ausdruck (damit die Ecke eines Rechtecks an Parametern hängt)."""
    if not ist_ausdruck(mitte) and not ist_ausdruck(groesse):
        return mitte - groesse / 2

    def teil(x):
        return f"({x[1:]})" if ist_ausdruck(x) else repr(x)
    return f"={teil(mitte)} - {teil(groesse)} / 2"


def _vorzeichen(x: float) -> int:
    return -1 if x < 0 else 1


@dataclass
class _Mass:
    name: str  # z. B. "D3" (vor dem Umbenennen der Skizze)
    roh: object  # Zahl oder Ausdruck aus der Spezifikation
    vorzeichen: int = 1  # Maße sind Beträge: -1, wenn der Maßwert dem negierten Ausdruck entspricht


class Skizzierer:
    """Legt Skizzenelemente an und bestimmt sie voll: eigene Maße für Größen und für die Lage jedes Kennpunkts
    zum Ursprung (bei 0 eine Ausrichtungsbeziehung). Erzeugt mit AddToDB=True, damit keine automatischen
    Beziehungen entstehen, die eigene Maße überbestimmen würden (live geprüft beim Schreiben von Plan 2a)."""

    def __init__(self, ctx, se: Skizzenebene, skizze):
        self.ctx, self.se, self.model, self.skizze = ctx, se, ctx.model, skizze
        self.sm = ctx.model.SketchManager
        self.mu = sw.mathutil(ctx.app)
        self.ursprung = sw.ursprung(ctx.model)
        self.masse: list[_Mass] = []
        x0, y0 = self.zu_skizze(0, 0)
        # Skizzenursprung = Projektion des Modellursprungs? Nur dann entsprechen Lagemaße den (u, v)-Werten.
        self.lage_bindbar = abs(x0) < 1e-9 and abs(y0) < 1e-9
        xu, yu = self.zu_skizze(1, 0)
        xv, yv = self.zu_skizze(0, 1)
        # Welche Spezifikationskoordinate (0 = u, 1 = v) mit welchem Vorzeichen auf Skizzen-x bzw. -y liegt
        self.x_von = (0, _vorzeichen(xu - x0)) if abs(xu - x0) > 1e-6 else (1, _vorzeichen(xv - x0))
        self.y_von = (0, _vorzeichen(yu - y0)) if abs(yu - y0) > 1e-6 else (1, _vorzeichen(yv - y0))

    def zu_skizze(self, u: float, v: float) -> tuple[float, float]:
        return sw.modell_zu_skizze(self.mu, self.skizze, _position_mm(self.se, u, v))

    def _text(self, u: float, v: float) -> tuple[float, float, float]:
        return tuple(mm(c) for c in _position_mm(self.se, u, v))

    def _merke(self, anzeige, roh, vorzeichen: int = 1) -> None:
        if anzeige is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "Maß konnte nicht angelegt werden", schritt="skizze")
        self.masse.append(_Mass(anzeige.GetDimension2(0).Name, roh, vorzeichen))

    def groesse(self, segment, text_uv: tuple[float, float], roh) -> None:
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, segment, 0)
        self._merke(self.model.AddDimension2(*self._text(*text_uv)), roh)
        sw.auswahl_leeren(self.model)

    def hat_punkt(self, u, v) -> bool:
        x, y = self.zu_skizze(self.ctx.wert(u), self.ctx.wert(v))
        return any(abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8 for p in self.skizze.GetSketchPoints2 or ())

    def _punkt(self, x: float, y: float):
        for p in self.skizze.GetSketchPoints2 or ():
            if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8:
                return p
        raise BauFehler(SKIZZE_UNGUELTIG, f"Skizzenpunkt ({x}, {y}) nicht gefunden", schritt="skizze")

    def lage(self, roh_uv, text_uv: tuple[float, float]) -> None:
        """Kennpunkt (u, v) zum Ursprung festlegen: je Richtung Maß, bei 0 Ausrichtung, bei (0, 0) deckungsgleich."""
        uv = (self.ctx.wert(roh_uv[0]), self.ctx.wert(roh_uv[1]))
        x, y = self.zu_skizze(*uv)
        punkt = self._punkt(x, y)

        def auswahl():
            sw.auswahl_leeren(self.model)
            sw.waehle(self.model, punkt, 0)
            sw.waehle(self.model, self.ursprung, 0, anhaengen=True)

        if abs(x) < 1e-9 and abs(y) < 1e-9:
            auswahl()
            self.model.SketchAddConstraints("sgCOINCIDENT")
            sw.auswahl_leeren(self.model)
            return
        for wert, (index, richtung), waagrecht in ((x, self.x_von, True), (y, self.y_von, False)):
            auswahl()
            if abs(wert) < 1e-9:
                self.model.SketchAddConstraints("sgVERTICALPOINTS2D" if waagrecht else "sgHORIZONTALPOINTS2D")
                continue
            text = self._text(*text_uv)
            anzeige = self.model.AddHorizontalDimension2(*text) if waagrecht else self.model.AddVerticalDimension2(*text)
            roh = roh_uv[index] if self.lage_bindbar else wert
            self._merke(anzeige, roh, _vorzeichen(wert) * richtung)
        sw.auswahl_leeren(self.model)

    def element(self, element: dict) -> None:
        w = self.ctx.wert
        if "rechteck" in element:
            r = element["rechteck"]
            mu_, mv = w(r["mitte"][0]), w(r["mitte"][1])
            b, h = w(r["breite"]), w(r["hoehe"])
            x0, y0 = self.zu_skizze(mu_ - b / 2, mv - h / 2)
            x1, y1 = self.zu_skizze(mu_ + b / 2, mv + h / 2)
            # CreateCornerRectangle statt CreateCenterRectangle: der Mittelpunkt des Mittelpunktrechtecks wird je nach
            # SolidWorks-Zustand nicht angelegt (live beobachtet); die Ecke ist immer ein Skizzenpunkt.
            seg = self.sm.CreateCornerRectangle(x0, y0, 0.0, x1, y1, 0.0)
            if not seg:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCornerRectangle fehlgeschlagen", schritt="skizze")
            # seg[0], seg[1] sind benachbarte Seiten; Breite/Höhe über die Länge zuordnen (Skizzensystem kann gedreht sein)
            seite_b, seite_h = (seg[0], seg[1]) if abs(seg[0].GetLength - mm(b)) < 1e-9 else (seg[1], seg[0])
            self.groesse(seite_b, (mu_, mv - h / 2 - _MASS_ABSTAND_MM), r["breite"])
            self.groesse(seite_h, (mu_ - b / 2 - _MASS_ABSTAND_MM, mv), r["hoehe"])
            ecke = (_halb_weg(r["mitte"][0], r["breite"]), _halb_weg(r["mitte"][1], r["hoehe"]))
            self.lage(ecke, (mu_ - b / 2 - _MASS_ABSTAND_MM, mv - h / 2 - _MASS_ABSTAND_MM))
        elif "kreis" in element:
            k = element["kreis"]
            mu_, mv = w(k["mitte"][0]), w(k["mitte"][1])
            d = w(k["durchmesser"])
            x, y = self.zu_skizze(mu_, mv)
            seg = self.sm.CreateCircleByRadius(x, y, 0.0, mm(d / 2))
            if seg is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCircleByRadius fehlgeschlagen", schritt="skizze")
            self.groesse(seg, (mu_ + d / 2 + _MASS_ABSTAND_MM, mv + _MASS_ABSTAND_MM), k["durchmesser"])
            self.lage(k["mitte"], (mu_ - d / 2 - _MASS_ABSTAND_MM, mv - _MASS_ABSTAND_MM))
        elif "polygon" in element:
            roh = element["polygon"]["punkte"]
            punkte = [self.zu_skizze(w(p[0]), w(p[1])) for p in roh]
            for (xa, ya), (xb, yb) in zip(punkte, punkte[1:] + punkte[:1]):
                if self.sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0) is None:
                    raise BauFehler(SKIZZE_UNGUELTIG, "CreateLine fehlgeschlagen", schritt="skizze")
            for p in roh:
                self.lage(p, (w(p[0]) + _MASS_ABSTAND_MM, w(p[1]) + _MASS_ABSTAND_MM))
        else:
            m = element["mittellinie"]
            xa, ya = self.zu_skizze(w(m["von"][0]), w(m["von"][1]))
            xb, yb = self.zu_skizze(w(m["bis"][0]), w(m["bis"][1]))
            if self.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0) is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCenterLine fehlgeschlagen", schritt="skizze")
            for p in (m["von"], m["bis"]):
                self.lage(p, (w(p[0]) - _MASS_ABSTAND_MM, w(p[1]) + _MASS_ABSTAND_MM))


def skizziere(ctx, ebene, elemente: list[dict], name: str):
    """Erzeugt eine voll bestimmte Skizze und benennt sie. Rückgabe: (Skizzen-Feature, Skizzenebene).

    Alle Größen- und Lagemaße werden per Gleichung an Parameter gebunden, wenn der Wert ein Ausdruck ist.
    """
    se = ebene_aufloesen(ctx, ebene)
    model, sm = ctx.model, ctx.model.SketchManager
    sw.auswahl_leeren(model)
    sw.waehle(model, se.objekt, 0)
    sm.InsertSketch(True)
    status, masse = None, []
    try:
        skizzierer = Skizzierer(ctx, se, sm.ActiveSketch)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            for element in elemente:
                skizzierer.element(element)
        status, masse = sm.ActiveSketch.GetConstrainedStatus, skizzierer.masse
    finally:
        sm.InsertSketch(True)
    if status != sw.SW_FULLY_CONSTRAINED:
        raise BauFehler(SKIZZE_NICHT_BESTIMMT, f"Skizze {name}: Status {status} statt voll bestimmt", schritt="skizze")
    feature = sw.letztes_feature(model)
    feature.Name = name
    for m in masse:
        ctx.verknuepfe(f"{m.name}@{name}", m.roh, m.vorzeichen)
    return feature, se


def richtung(se: Skizzenebene, umkehren: bool) -> Vektor:
    return tuple(-c for c in se.normale) if umkehren else se.normale
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle grün (test_skizze_geometrie: 15 passed).

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler tests/compiler
git commit -m "compiler: Topologie, Skizzenebenen und voll bestimmte Skizzen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 9: Handler `extrusion` und `schnitt`

**Files:**
- Create: `swki/compiler/handler/__init__.py`, `swki/compiler/handler/extrusion.py`, `tests/live/bauhilfe.py`, `tests/live/test_live_extrusion.py`

**Interfaces:**
- Consumes: `skizziere`, `richtung` (Task 8), `handler` (Task 6), `FeatureErgebnis` (Task 6), `sw.auswahl_leeren` (Task 7).
- Produces: `ENDE = {"blind": 0, "durch_alles": 1, "mittig": 6}`; `aufsatz(model, typ, tiefe_m, umkehren)`, `schnitt(model, typ, tiefe_m, umkehren)` (auch für `bohrung`); Handler für `extrusion` und `schnitt`. Features heißen wie ihre ID (`f1`), Skizzen `<id>_skizze`; Tiefe mit Ausdruck → Gleichung `D1@<id>`.
- Testhilfe `tests/live/bauhilfe.py`: `gebautes_teil(spec, spec_pfad=…)` (neues Teil, globale Variablen, Bauablauf, Teil wird immer geschlossen), `volumen_mm3(model)`, `zylinder_mm3(d, h)`.

- [ ] **Step 1: Live-Tests schreiben**

`tests/live/bauhilfe.py`:

```python
"""Hilfen für Live-Tests der Handler: Minimalteil bauen, messen, wieder schließen."""

import math
from contextlib import contextmanager
from pathlib import Path

from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.konfig import lade_rechner
from swki.verbindung import in_mm3, verbinde


@contextmanager
def gebautes_teil(spec: dict, spec_pfad: Path = Path("live.yaml")):
    """Baut spec in einem neuen Teil; liefert (ctx, fehler, protokoll). Das Teil wird immer geschlossen."""
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, spec_pfad, 0.1)
        globale_variablen(model, spec.get("parameter", {}))
        protokoll = Protokoll("live", "live.yaml", 0, r.sw_jahr)
        fehler = baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
        yield ctx, fehler, protokoll
    finally:
        sw.schliesse(app, model)


def volumen_mm3(model) -> float:
    return in_mm3(model.Extension.CreateMassProperty.Volume)


def zylinder_mm3(d: float, h: float) -> float:
    return math.pi * (d / 2) ** 2 * h
```

`tests/live/test_live_extrusion.py`:

```python
"""Live: Extrusion und Schnitt (SolidWorks muss laufen)."""

import pythoncom
import pytest

from swki.compiler import sw

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": "=H"},
}


def _spec(*features, parameter=None):
    return {"art": "teil", "name": "T", "parameter": parameter or {"L": 100, "H": 20}, "features": [KLOTZ, *features]}


def test_extrusion_mit_parametern():
    with gebautes_teil(_spec()) as (ctx, fehler, _):
        assert fehler is None
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-50, 0, -30, 50, 20, 30], abs=1e-6)
        assert ctx.ergebnis("f1").richtung == (0.0, 1.0, 0.0)
        # Parameter sind SW-Gleichungen: "L", "H", Breite = "L", Lage der linken Ecke u = 0 - L/2 (Maß ist der Betrag,
        # daher negiert), Tiefe D1@f1 = "H"; Höhe 60 und Ecke v = -30 sind Zahlen und bekommen keine Gleichung
        gleichungen = ctx.model.GetEquationMgr
        assert [gleichungen.Equation(i) for i in range(gleichungen.GetCount)] == [
            '"L" = 100', '"H" = 20', '"D1@f1_skizze" = "L"', '"D3@f1_skizze" = -(0 - ("L" / 2))', '"D1@f1" = "H"',
        ]
        # L ändern (Property-Put nur per Invoke, S9a) → Teil wird länger
        dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
        gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, 0, '"L" = 120')
        gleichungen.EvaluateAll
        sw.rebuild(ctx.model)
        assert sw.teilebox_mm(ctx.model)[0:4:3] == pytest.approx([-60, 60], abs=1e-6)


def test_extrusion_mittig_und_umgekehrt():
    spec = {"art": "teil", "name": "T", "features": [{
        "id": "f1", "typ": "extrusion",
        "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [10, 5], "durchmesser": 8}}]},
        "ende": {"typ": "mittig", "tiefe": 30},
    }]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert sw.teilebox_mm(ctx.model) == pytest.approx([6, 1, -15, 14, 9, 15], abs=1e-6)


def test_schnitt_tasche_von_deckflaeche():
    tasche = {
        "id": "f2", "typ": "schnitt",
        "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                   "elemente": [{"rechteck": {"mitte": [10, 5], "breite": 20, "hoehe": 10}}]},
        "ende": {"typ": "blind", "tiefe": 5},
    }
    with gebautes_teil(_spec(tasche)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(100 * 60 * 20 - 20 * 10 * 5, abs=1e-3)
        assert ctx.ergebnis("f2").richtung == (0.0, -1.0, 0.0)


def test_schnitt_ohne_material_meldet_fehler():
    daneben = {
        "id": "f2", "typ": "schnitt",
        "skizze": {"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 5}}]},
        "ende": {"typ": "blind", "tiefe": 5},
    }
    with gebautes_teil(_spec(daneben)) as (_, fehler, protokoll):
        assert fehler.code == "FEATURE_NICHT_ERZEUGT"
        assert protokoll.knoten[1].status == "fehler"


def test_skizze_auf_versetzter_ebene():
    spec = {"art": "teil", "name": "T", "features": [{
        "id": "f1", "typ": "extrusion",
        "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": -15}},
                   "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 10, "hoehe": 10}}]},
        "ende": {"typ": "blind", "tiefe": 5},
    }]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-5, -15, -5, 5, -10, 5], abs=1e-6)
```

- [ ] **Step 2: Live-Tests fehlschlagen lassen (SolidWorks geöffnet)**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_extrusion.py`
Expected: 5× `FEHLER` (`ModuleNotFoundError: swki.compiler.handler`).

- [ ] **Step 3: Implementieren**

`swki/compiler/handler/__init__.py` (vollständig):

```python
"""Alle Feature-Handler; der Import registriert sie in swki.compiler.registry.HANDLER."""

from swki.compiler.handler import extrusion  # noqa: F401
```

`swki/compiler/handler/extrusion.py`:

```python
"""Handler "extrusion" (Aufsatz) und "schnitt" (verifiziert in Spike S9a, Bausteine 6 und 7).

Aufsatz wächst standardmäßig in Richtung der Skizzennormale, Schnitt standardmäßig dagegen
(von einer Deckfläche also ins Material). "umkehren" dreht die Richtung (3. Parameter Dir, nicht Flip).
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import richtung, skizziere

ENDE = {"blind": 0, "durch_alles": 1, "mittig": 6}  # swEndConditions_e


def aufsatz(model, typ: int, tiefe_m: float, umkehren: bool):
    return model.FeatureManager.FeatureExtrusion3(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, False, False, False, False, 0.0, 0.0,
        False, False, False, False, True, True, True, 0, 0.0, False,
    )


def schnitt(model, typ: int, tiefe_m: float, umkehren: bool):
    return model.FeatureManager.FeatureCut4(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, False, False, False, False, 0.0, 0.0,
        False, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False,
    )


@handler("extrusion", "schnitt")
def extrusion(ctx, f: dict) -> FeatureErgebnis:
    skizze, se = skizziere(ctx, f["skizze"]["ebene"], f["skizze"]["elemente"], f"{f['id']}_skizze")
    ende = f["ende"]
    typ = ENDE[ende["typ"]]
    tiefe = ctx.m(ende["tiefe"]) if "tiefe" in ende else 0.0
    umkehren = bool(ende.get("umkehren", False))
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)
    ist_schnitt = f["typ"] == "schnitt"
    feature = (schnitt if ist_schnitt else aufsatz)(ctx.model, typ, tiefe, umkehren)
    if feature is None:
        grund = " (trifft der Schnitt Material? ggf. umkehren)" if ist_schnitt else ""
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{f['typ']} {f['id']} nicht erzeugt{grund}", schritt="feature")
    feature.Name = f["id"]
    if "tiefe" in ende:
        ctx.verknuepfe(f"D1@{f['id']}", ende["tiefe"])
    return FeatureErgebnis([feature], richtung=richtung(se, umkehren != ist_schnitt))
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle Unit-Tests grün.

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_extrusion.py`
Expected: 5× `OK` (Extrusion mit Parametern und Gleichungsänderung, mittig, Tasche von Deckfläche, Schnitt ohne Material → `FEATURE_NICHT_ERZEUGT`, versetzte Ebene).

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/handler tests/live
git commit -m "compiler: Handler extrusion und schnitt" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 10: Handler `rotation` und `bohrung`

**Files:**
- Create: `swki/compiler/handler/rotation.py`, `swki/compiler/handler/bohrung.py`, `tests/live/test_live_rotation_bohrung.py`
- Modify: `swki/compiler/handler/__init__.py`

**Interfaces:**
- Consumes: `schnitt`, `ENDE` (Task 9); `skizziere`, `ebene_aus_flaeche`, `modellpunkt`, `richtung` (Task 8); `loese_flaeche` (Task 8).
- Produces: `rotiere(model, schnitt, winkel_rad)`; Handler `rotation` (Richtung = Mittellinie) und `bohrung` (Instanzen in Positionsreihenfolge; `FeatureErgebnis.punkte` = Achspunkte auf der Skizzenfläche in mm; Senkung als zweites Feature `<id>_senkung`).

- [ ] **Step 1: Live-Tests schreiben**

`tests/live/test_live_rotation_bohrung.py`:

```python
"""Live: Rotation und Bohrung, parametrische Lage (SolidWorks muss laufen)."""

import math

import pythoncom
import pytest

from swki.compiler import sw
from swki.compiler.topologie import flaechen

from .bauhilfe import gebautes_teil, volumen_mm3, zylinder_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
VOLL = 100 * 60 * 20
BOHRUNG = {
    "id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
    "positionen": [[-40, 20]], "durchmesser": 8, "durch": True,
}


def _spec(*features, **weiteres):
    return {"art": "teil", "name": "T", "features": [KLOTZ, *features], **weiteres}


def _achsen_xz(feature) -> list[tuple[float, float]]:
    return sorted((round(z.punkt[0], 4), round(z.punkt[2], 4)) for z in flaechen(feature) if z.art == "zylinder")


def test_rotation_rohr_und_nut():
    rohr = {
        "id": "f1", "typ": "rotation",
        "skizze": {"ebene": "vorne", "elemente": [
            {"polygon": {"punkte": [[10, 0], [30, 0], [30, 40], [10, 40]]}},
            {"mittellinie": {"von": [0, -10], "bis": [0, 50]}},
        ]},
    }
    nut = {
        "id": "f2", "typ": "rotation", "schnitt": True,
        "skizze": {"ebene": "vorne", "elemente": [
            {"polygon": {"punkte": [[25, 20], [31, 20], [31, 25], [25, 25]]}},
            {"mittellinie": {"von": [0, -10], "bis": [0, 50]}},
        ]},
    }
    spec = {"art": "teil", "name": "T", "features": [rohr, nut]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        erwartet = math.pi * (30**2 - 10**2) * 40 - math.pi * (30**2 - 25**2) * 5
        assert volumen_mm3(ctx.model) == pytest.approx(erwartet, abs=1e-3)
        assert ctx.ergebnis("f1").richtung == pytest.approx((0, 1, 0))


def test_bohrungen_mit_senkung():
    bohrung = {
        "id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
        "positionen": [[-30, 15], [30, -15]], "durchmesser": 8, "durch": True,
        "senkung": {"durchmesser": 14, "tiefe": 4},
    }
    with gebautes_teil(_spec(bohrung)) as (ctx, fehler, _):
        assert fehler is None
        erg = ctx.ergebnis("f2")
        assert [f.Name for f in erg.features] == ["f2", "f2_senkung"]
        assert erg.punkte == [(-30.0, 20.0, -15.0), (30.0, 20.0, 15.0)]
        erwartet = 100 * 60 * 20 - 2 * (zylinder_mm3(8, 20) + zylinder_mm3(14, 4) - zylinder_mm3(8, 4))
        assert volumen_mm3(ctx.model) == pytest.approx(erwartet, abs=1e-3)


def test_lage_haengt_an_parameter():
    spec = _spec({**BOHRUNG, "positionen": [["=-L/2+10", "=T"]]}, parameter={"L": 100, "T": 20})
    spec["features"][0] = {**KLOTZ, "skizze": {"ebene": "oben", "elemente": [
        {"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]}}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        gleichungen = ctx.model.GetEquationMgr
        dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
        texte = [gleichungen.Equation(i) for i in range(gleichungen.GetCount)]
        i_l = texte.index('"L" = 100')
        gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, i_l, '"L" = 140')
        gleichungen.EvaluateAll
        sw.rebuild(ctx.model)
        # Bohrung bleibt 10 mm vom linken Rand: X = -140/2 + 10 = -60; Z = -T = -20
        assert _achsen_xz(ctx.ergebnis("f2").features[0]) == [(-60.0, -20.0)]
```

- [ ] **Step 2: Live-Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_rotation_bohrung.py`
Expected: 3× `FEHLER` (`UNBEKANNTER_TYP`).

- [ ] **Step 3: Implementieren**

`swki/compiler/handler/rotation.py`:

```python
"""Handler "rotation" – Aufsatz oder Schnitt um die Mittellinie der Skizze (Spike S9a, Baustein 8)."""

from swki.compiler import sw
from swki.compiler.anker import differenz, laenge
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import modellpunkt, skizziere


def rotiere(model, schnitt: bool, winkel_rad: float):
    return model.FeatureManager.FeatureRevolve2(
        True, True, False, schnitt, False, False, 0, 0, winkel_rad, 0.0,
        False, False, 0.0, 0.0, 0, 0.0, 0.0, True, True, True,
    )


@handler("rotation")
def rotation(ctx, f: dict) -> FeatureErgebnis:
    skizze, se = skizziere(ctx, f["skizze"]["ebene"], f["skizze"]["elemente"], f"{f['id']}_skizze")
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)  # die einzige Mittellinie der Skizze wird automatisch Achse
    feature = rotiere(ctx.model, bool(f.get("schnitt", False)), ctx.rad(f.get("winkel", 360)))
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"rotation {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    if "winkel" in f:
        ctx.verknuepfe(f"D1@{f['id']}", f["winkel"])
    linie = next(e["mittellinie"] for e in f["skizze"]["elemente"] if "mittellinie" in e)
    a = modellpunkt(se.orientierung, ctx.wert(linie["von"][0]), ctx.wert(linie["von"][1]), se.lage)
    b = modellpunkt(se.orientierung, ctx.wert(linie["bis"][0]), ctx.wert(linie["bis"][1]), se.lage)
    d = differenz(b, a)
    return FeatureErgebnis([feature], richtung=tuple(c / laenge(d) for c in d))
```

`swki/compiler/handler/bohrung.py`:

```python
"""Handler "bohrung" – zylindrische Bohrungen (durch oder blind) mit optionaler Flachsenkung (Spike S9a, Baustein 9).

Jede Position ist eine Instanz (1, 2, …) in Spezifikationsreihenfolge. Die Achspunkte werden aus der Skizze
berechnet (nicht aus der Flächenreihenfolge, die SolidWorks nicht stabil liefert).
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.handler.extrusion import ENDE, schnitt
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import ebene_aus_flaeche, modellpunkt, richtung, skizziere
from swki.compiler.topologie import loese_flaeche


def _kreisschnitt(ctx, f: dict, durchmesser, tiefe, name: str):
    se = ebene_aus_flaeche(loese_flaeche(ctx, f["flaeche"]))
    kreise = [{"kreis": {"mitte": p, "durchmesser": durchmesser}} for p in f["positionen"]]
    skizze, se = skizziere(ctx, se, kreise, f"{name}_skizze")
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)
    typ = ENDE["durch_alles"] if tiefe is None else ENDE["blind"]
    feature = schnitt(ctx.model, typ, 0.0 if tiefe is None else ctx.m(tiefe), False)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"bohrung {name} nicht erzeugt", schritt="feature")
    feature.Name = name
    if tiefe is not None:
        ctx.verknuepfe(f"D1@{name}", tiefe)
    return feature, se


@handler("bohrung")
def bohrung(ctx, f: dict) -> FeatureErgebnis:
    features = []
    feature, se = _kreisschnitt(ctx, f, f["durchmesser"], None if f.get("durch") else f["tiefe"], f["id"])
    features.append(feature)
    if "senkung" in f:
        s = f["senkung"]
        senkung, _ = _kreisschnitt(ctx, f, s["durchmesser"], s["tiefe"], f"{f['id']}_senkung")
        features.append(senkung)
    punkte = [modellpunkt(se.orientierung, ctx.wert(u), ctx.wert(v), se.lage) for u, v in f["positionen"]]
    return FeatureErgebnis(features, richtung=richtung(se, True), punkte=punkte)
```

`swki/compiler/handler/__init__.py` (vollständig):

```python
"""Alle Feature-Handler; der Import registriert sie in swki.compiler.registry.HANDLER."""

from swki.compiler.handler import bohrung, extrusion, rotation  # noqa: F401
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_rotation_bohrung.py tests\live\test_live_extrusion.py`
Expected: 8× `OK` (Rohr mit Nut exakt nach Volumen, Bohrungen mit Senkung, Bohrungslage folgt Parameter L).

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/handler tests/live
git commit -m "compiler: Handler rotation und bohrung" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 11: Handler `verrundung` und `fase`

**Files:**
- Create: `swki/compiler/handler/kanten.py`, `tests/live/test_live_kanten.py`
- Modify: `swki/compiler/handler/__init__.py`

**Interfaces:**
- Consumes: `loese_kanten` (Task 8), `sw.waehle` (Task 7).
- Produces: Handler `verrundung` (`CreateDefinition(swFmFillet=1)` + `CreateFeature`, konstanter Radius, tangentiale Fortsetzung) und `fase` (`InsertFeatureChamfer`, Abstand-Winkel, Option Tangentenfortsetzung 4; leeres Fase-Feature gilt als Fehler, S9b).

- [ ] **Step 1: Live-Tests schreiben**

`tests/live/test_live_kanten.py`:

```python
"""Live: Verrundung und Fase (SolidWorks muss laufen)."""

import math

import pytest

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
VOLL = 100 * 60 * 20


def _spec(*features, **weiteres):
    return {"art": "teil", "name": "T", "features": [KLOTZ, *features], **weiteres}


def test_verrundung_senkrechte_kanten():
    f = {"id": "f2", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": 5}
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 4 * (1 - math.pi / 4) * 25 * 20, abs=1e-3)


def test_fase_mit_tangentenfortsetzung():
    rund = {"id": "f2", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": 5}
    fase = {"id": "f3", "typ": "fase", "kanten": [{"nahe": [50, 20, 0]}], "abstand": 1}
    with gebautes_teil(_spec(rund, fase)) as (ctx, fehler, _):
        assert fehler is None
        umfang = 2 * (100 - 10) + 2 * (60 - 10) + 2 * math.pi * 5
        vorher = VOLL - 4 * (1 - math.pi / 4) * 25 * 20
        # eine Kante gewählt, umlaufend gefast (Querschnitt 0,5 mm²); Eckbereiche weichen minimal ab
        assert volumen_mm3(ctx.model) == pytest.approx(vorher - 0.5 * umfang, abs=2.0)


def test_fase_mehrdeutiger_punkt():
    fase = {"id": "f2", "typ": "fase", "kanten": [{"nahe": [50, 20, 30]}], "abstand": 1}  # Ecke: 3 Kanten
    with gebautes_teil(_spec(fase)) as (_, fehler, _):
        assert fehler.code == "REFERENZ_MEHRDEUTIG"
```

- [ ] **Step 2: Live-Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_kanten.py`
Expected: FEHLER (`UNBEKANNTER_TYP`).

- [ ] **Step 3: Implementieren**

`swki/compiler/handler/kanten.py`:

```python
"""Handler "verrundung" und "fase" auf Kanten (Spike S9b, Bausteine 12 und 13).

Beide setzen sich über tangentiale Kanten fort (eine Kante eines verrundeten Umrisses reicht).
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.topologie import loese_kanten

SW_FM_FILLET = 1  # swFeatureNameID_e
SW_CONST_RADIUS_FILLET = 0  # swSimpleFilletType_e
SW_CHAMFER_ANGLE_DISTANCE = 1  # swChamferType_e
SW_CHAMFER_TANGENT_PROPAGATION = 4  # swFeatureChamferOption_e


def _waehle_kanten(ctx, f: dict) -> None:
    kanten = [k for anker in f["kanten"] for k in loese_kanten(ctx, anker)]
    sw.auswahl_leeren(ctx.model)
    for k in kanten:
        sw.waehle(ctx.model, k.objekt, 1, anhaengen=True)


@handler("verrundung")
def verrundung(ctx, f: dict) -> FeatureErgebnis:
    fm = ctx.model.FeatureManager
    daten = fm.CreateDefinition(SW_FM_FILLET)
    daten.Initialize(SW_CONST_RADIUS_FILLET)
    daten.DefaultRadius = ctx.m(f["radius"])
    daten.ConicTypeForCrossSectionProfile = 0  # kreisförmig
    daten.OverflowType = 0
    daten.PropagateToTangentFaces = True
    _waehle_kanten(ctx, f)
    feature = fm.CreateFeature(daten)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"verrundung {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    ctx.verknuepfe(f"D1@{f['id']}", f["radius"])
    return FeatureErgebnis([feature])


@handler("fase")
def fase(ctx, f: dict) -> FeatureErgebnis:
    _waehle_kanten(ctx, f)
    feature = ctx.model.FeatureManager.InsertFeatureChamfer(
        SW_CHAMFER_TANGENT_PROPAGATION, SW_CHAMFER_ANGLE_DISTANCE, ctx.m(f["abstand"]),
        ctx.rad(f.get("winkel", 45)), 0, 0, 0, 0,
    )
    if feature is None or not feature.GetFaces:
        # Leeres Fase-Feature ohne Fehlermeldung ist möglich (S9b) → als Fehler behandeln
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"fase {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    ctx.verknuepfe(f"D1@{f['id']}", f["abstand"])
    return FeatureErgebnis([feature])
```

`swki/compiler/handler/__init__.py` (vollständig):

```python
"""Alle Feature-Handler; der Import registriert sie in swki.compiler.registry.HANDLER."""

from swki.compiler.handler import bohrung, extrusion, kanten, rotation  # noqa: F401
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_kanten.py`
Expected: 3× `OK` (R5 exakt; Fase umlaufend über eine Kante; Ecke → `REFERENZ_MEHRDEUTIG`).

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/handler tests/live
git commit -m "compiler: Handler verrundung und fase" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 12: Handler `muster_linear`, `muster_kreis`, `spiegeln`

**Files:**
- Create: `swki/compiler/handler/muster.py`, `tests/live/test_live_muster.py`
- Modify: `swki/compiler/handler/__init__.py`

**Interfaces:**
- Consumes: `STANDARD`, `ebene_aufloesen` (Task 8), `ACHSEN`, `differenz`, `laenge`, `skalar` (Task 5), `Kontext.achsen` (Task 6).
- Produces: `referenzachse(ctx, achse) -> (IFeature, Richtung)` (x = vorne∩oben, y = vorne∩rechts, z = oben∩rechts; je Teil einmal, Name `achse_<x|y|z>`, ausgeblendet); Handler `muster_linear` (`CreateDefinition(6)`, Vorselektion Achse Marke 1/2, Features Marke 4), `muster_kreis` (`CreateDefinition(5)`, erst `EqualSpacing`, dann `Spacing`), `spiegeln` (`InsertMirrorFeature2`, Features Marke 1, Ebene Marke 2).

- [ ] **Step 1: Live-Tests schreiben**

`tests/live/test_live_muster.py`:

```python
"""Live: lineares Muster, Kreismuster, Spiegeln (SolidWorks muss laufen)."""

import pytest

from swki.compiler.topologie import flaechen

from .bauhilfe import gebautes_teil, volumen_mm3, zylinder_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
VOLL = 100 * 60 * 20
BOHRUNG = {
    "id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
    "positionen": [[-40, 20]], "durchmesser": 8, "durch": True,
}


def _spec(*features, **weiteres):
    return {"art": "teil", "name": "T", "features": [KLOTZ, *features], **weiteres}


def _achsen_xz(feature) -> list[tuple[float, float]]:
    return sorted((round(z.punkt[0], 4), round(z.punkt[2], 4)) for z in flaechen(feature) if z.art == "zylinder")


def test_muster_linear_zwei_richtungen():
    saat = {**BOHRUNG, "positionen": [[-40, -20]]}  # Modell X=-40, Z=+20
    muster = {"id": "f3", "typ": "muster_linear", "features": ["f2"],
              "richtung1": {"achse": "x", "abstand": 20, "anzahl": 4},
              "richtung2": {"achse": "z", "abstand": 15, "anzahl": 2, "umkehren": True}}
    with gebautes_teil(_spec(saat, muster)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 8 * zylinder_mm3(8, 20), abs=1e-3)
        # Richtung 1 nach +X, Richtung 2 umgekehrt nach -Z; das Muster-Feature enthält nur die 7 neuen Instanzen
        assert _achsen_xz(ctx.ergebnis("f3").features[0]) == sorted(
            (x, z) for x in (-40.0, -20.0, 0.0, 20.0) for z in (20.0, 5.0) if (x, z) != (-40.0, 20.0)
        )


def test_muster_kreis():
    scheibe = {
        "id": "f1", "typ": "extrusion",
        "skizze": {"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 100}}]},
        "ende": {"typ": "blind", "tiefe": 10},
    }
    loch = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
            "positionen": [[30, 0]], "durchmesser": 8, "durch": True}
    muster = {"id": "f3", "typ": "muster_kreis", "features": ["f2"], "achse": "y", "anzahl": 6}
    spec = {"art": "teil", "name": "T", "features": [scheibe, loch, muster]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(zylinder_mm3(100, 10) - 6 * zylinder_mm3(8, 10), abs=1e-3)


def test_spiegeln_an_ebene_vorne():
    spiegeln = {"id": "f3", "typ": "spiegeln", "features": ["f2"], "ebene": "vorne"}
    with gebautes_teil(_spec(BOHRUNG, spiegeln)) as (ctx, fehler, _):
        assert fehler is None
        assert _achsen_xz(ctx.ergebnis("f3").features[0]) == [(-40.0, 20.0)]
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 2 * zylinder_mm3(8, 20), abs=1e-3)
```

- [ ] **Step 2: Live-Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_muster.py`
Expected: FEHLER (`UNBEKANNTER_TYP`).

- [ ] **Step 3: Implementieren**

`swki/compiler/handler/muster.py`:

```python
"""Handler "muster_linear", "muster_kreis" und "spiegeln" (Spike S9b, Bausteine 14–16).

Richtungen und Drehachsen sind Referenzachsen aus zwei Standardebenen (x = vorne∩oben, y = vorne∩rechts,
z = oben∩rechts); sie werden je Teil einmal angelegt ("achse_x" …). Die Musterrichtung folgt der Richtung
der Achse; zeigt sie gegen die Sollrichtung, wird umgekehrt.
"""

from swki.compiler import sw
from swki.compiler.anker import ACHSEN, differenz, laenge, skalar
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import STANDARD, ebene_aufloesen
from swki.verbindung import in_mm

SW_FM_CIRPATTERN = 5  # swFeatureNameID_e
SW_FM_LPATTERN = 6
_EBENEN_DER_ACHSE = {"x": ("vorne", "oben"), "y": ("vorne", "rechts"), "z": ("oben", "rechts")}


def referenzachse(ctx, achse: str):
    """Referenzachse (IFeature) und ihre Richtung als Einheitsvektor; je Teil nur einmal angelegt."""
    if achse in ctx.achsen:
        return ctx.achsen[achse]
    ebenen = sw.standardebenen(ctx.model)
    a, b = _EBENEN_DER_ACHSE[achse]
    sw.auswahl_leeren(ctx.model)
    sw.waehle(ctx.model, ebenen[STANDARD[a]], 0)
    sw.waehle(ctx.model, ebenen[STANDARD[b]], 0, anhaengen=True)
    if not ctx.model.InsertAxis2(True):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Referenzachse {achse} nicht erzeugt", schritt="achse")
    feature = sw.letztes_feature(ctx.model)
    feature.Name = f"achse_{achse}"
    sw.auswahl_leeren(ctx.model)
    feature.Select2(False, 0)
    ctx.model._FlagAsMethod("BlankRefGeom")
    ctx.model.BlankRefGeom()  # ausblenden, damit die Achse nicht in den Screenshots erscheint
    sw.auswahl_leeren(ctx.model)
    p = feature.GetSpecificFeature2.GetRefAxisParams  # (x1, y1, z1, x2, y2, z2) in m
    d = differenz(tuple(in_mm(v) for v in p[3:6]), tuple(in_mm(v) for v in p[0:3]))
    ctx.achsen[achse] = (feature, tuple(c / laenge(d) for c in d))
    return ctx.achsen[achse]


def _sw_features(ctx, ids: list[str]) -> list:
    return [feature for fid in ids for feature in ctx.ergebnis(fid).features]


def _umkehren(ctx, richtung: dict) -> bool:
    _, d = referenzachse(ctx, richtung["achse"])
    soll = skalar(d, ACHSEN[richtung["achse"]])
    return (soll < 0) != bool(richtung.get("umkehren", False))


@handler("muster_linear")
def muster_linear(ctx, f: dict) -> FeatureErgebnis:
    r1, r2 = f["richtung1"], f.get("richtung2")
    umkehren1 = _umkehren(ctx, r1)
    umkehren2 = _umkehren(ctx, r2) if r2 else False
    sw.auswahl_leeren(ctx.model)
    sw.waehle(ctx.model, referenzachse(ctx, r1["achse"])[0], 1)
    if r2:
        sw.waehle(ctx.model, referenzachse(ctx, r2["achse"])[0], 2, anhaengen=True)
    for feature in _sw_features(ctx, f["features"]):
        sw.waehle(ctx.model, feature, 4, anhaengen=True)
    fm = ctx.model.FeatureManager
    daten = fm.CreateDefinition(SW_FM_LPATTERN)  # liest die Vorselektion bei CreateFeature
    daten.D1TotalInstances = r1["anzahl"]
    daten.D1Spacing = ctx.m(r1["abstand"])
    daten.D1ReverseDirection = umkehren1
    if r2:
        daten.D2TotalInstances = r2["anzahl"]
        daten.D2Spacing = ctx.m(r2["abstand"])
        daten.D2ReverseDirection = umkehren2
    feature = fm.CreateFeature(daten)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"muster_linear {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    return FeatureErgebnis([feature])


@handler("muster_kreis")
def muster_kreis(ctx, f: dict) -> FeatureErgebnis:
    achse, richtung = referenzachse(ctx, f["achse"])
    sw.auswahl_leeren(ctx.model)
    sw.waehle(ctx.model, achse, 1)
    for feature in _sw_features(ctx, f["features"]):
        sw.waehle(ctx.model, feature, 4, anhaengen=True)
    fm = ctx.model.FeatureManager
    daten = fm.CreateDefinition(SW_FM_CIRPATTERN)
    daten.TotalInstances = f["anzahl"]
    daten.EqualSpacing = True  # zuerst: setzt Spacing auf 2π zurück (S9b)
    daten.Spacing = ctx.rad(f.get("winkel", 360))  # bei EqualSpacing = Gesamtwinkel
    feature = fm.CreateFeature(daten)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"muster_kreis {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    return FeatureErgebnis([feature], richtung=richtung)


@handler("spiegeln")
def spiegeln(ctx, f: dict) -> FeatureErgebnis:
    ebene = ebene_aufloesen(ctx, f["ebene"])
    sw.auswahl_leeren(ctx.model)
    for feature in _sw_features(ctx, f["features"]):
        sw.waehle(ctx.model, feature, 1, anhaengen=True)
    sw.waehle(ctx.model, ebene.objekt, 2, anhaengen=True)
    feature = ctx.model.FeatureManager.InsertMirrorFeature2(False, False, False, False, 0)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"spiegeln {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    return FeatureErgebnis([feature])
```

`swki/compiler/handler/__init__.py` (vollständig):

```python
"""Alle Feature-Handler; der Import registriert sie in swki.compiler.registry.HANDLER."""

from swki.compiler.handler import bohrung, extrusion, kanten, muster, rotation  # noqa: F401
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_muster.py`
Expected: 3× `OK` (4×2-Muster mit umgekehrter zweiter Richtung, 6er-Kreismuster, Spiegeln an vorne).

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/handler tests/live
git commit -m "compiler: Handler muster_linear, muster_kreis, spiegeln" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 13: Handler `skript` (Notausgang)

**Files:**
- Create: `swki/compiler/handler/skript.py`, `tests/live/test_live_skript.py`
- Modify: `swki/compiler/handler/__init__.py`

**Interfaces:**
- Consumes: `pruefe_skript` (Task 2), `Skizzierer`, `ebene_aufloesen`, `modellpunkt`, `skizziere` (Task 8), `loese_flaeche`, `loese_kanten` (Task 8).
- Produces: `SkriptKontext` – das Einzige, was ein Skript bekommt: `app`, `model`, `callout_leer`, `byref_long`, `wert`, `m`, `rad`, `feature(fid)`, `flaeche(anker)`, `kanten(anker)`, `ebene(ebene)`, `skizze(ebene, elemente, name)`, `modellpunkt_m(skizzenebene, u, v)`, `punkte_festlegen(feature, ebene, punkte_uv)` (bemaßt nicht voll bestimmte Unterskizzen, z. B. die Positionsskizze des Bohrungsassistenten), `waehle`, `auswahl_leeren`. Handler `skript`: Datei relativ zum Auftrag, erst statisch prüfen, dann `bauen(ctx)` ausführen; Rückgabe IFeature oder Liste; Features heißen `<id>`, `<id>_2`, …

- [ ] **Step 1: Live-Tests schreiben**

`tests/live/test_live_skript.py`:

```python
"""Live: Notausgang (typ: skript) und Material/Eigenschaften (SolidWorks muss laufen)."""

import pytest

from swki.compiler.eigenschaften import lies_eigenschaften, setze_eigenschaften, setze_material

from .bauhilfe import gebautes_teil, volumen_mm3, zylinder_mm3

pytestmark = pytest.mark.sw

KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
VOLL = 100 * 60 * 20


def _spec(*features, **weiteres):
    return {"art": "teil", "name": "T", "features": [KLOTZ, *features], **weiteres}


def test_notausgang_skript(tmp_path):
    (tmp_path / "skripte").mkdir()
    (tmp_path / "skripte" / "f2.py").write_text(
        "def bauen(ctx):\n"
        "    skizze, _ = ctx.skizze({'feature': 'f1', 'flaeche': '+y'},\n"
        "                           [{'kreis': {'mitte': [0, 0], 'durchmesser': 10}}])\n"
        "    ctx.auswahl_leeren()\n"
        "    skizze.Select2(False, 0)\n"
        "    return ctx.model.FeatureManager.FeatureCut4(\n"
        "        True, False, False, 0, 0, ctx.m(5), 0.0, False, False, False, False, 0.0, 0.0,\n"
        "        False, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False)\n",
        encoding="utf-8",
    )
    skript = {"id": "f2", "typ": "skript", "datei": "skripte/f2.py", "luecke": "Test des Notausgangs"}
    with gebautes_teil(_spec(skript), spec_pfad=tmp_path / "t.yaml") as (ctx, fehler, _):
        assert fehler is None
        assert ctx.ergebnis("f2").sw_name == "f2"
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - zylinder_mm3(10, 5), abs=1e-3)


def test_material_und_eigenschaften():
    with gebautes_teil(_spec()) as (ctx, fehler, _):
        assert fehler is None
        assert setze_material(ctx.app, ctx.model, "1.2312").startswith("1.2312 (")
        setze_eigenschaften(ctx.model, {"Benennung": "Formplatte DS – Test", "Auftrag": "A-1"})
        assert lies_eigenschaften(ctx.model) == {"Benennung": "Formplatte DS – Test", "Auftrag": "A-1"}
```

- [ ] **Step 2: Live-Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_skript.py`
Expected: `test_notausgang_skript` FEHLER (`UNBEKANNTER_TYP`); der Materialtest ist bereits grün.

- [ ] **Step 3: Implementieren**

`swki/compiler/handler/skript.py`:

```python
"""Handler "skript" – kontrollierter Notausgang für Lücken im Spezifikationsformat.

Das Skript (auftraege/<auftrag>/skripte/<id>.py) wird vor dem Laden statisch geprüft (swki.compiler.skriptpruefung)
und bekommt nur einen SkriptKontext. `bauen(ctx)` muss das erzeugte IFeature oder eine Liste davon zurückgeben.
"""

from swki.compiler import sw
from swki.compiler.fehler import SKRIPT_FEHLER, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import Skizzierer, ebene_aufloesen, modellpunkt, skizziere
from swki.compiler.skriptpruefung import pruefe_skript
from swki.compiler.topologie import loese_flaeche, loese_kanten
from swki.verbindung import byref_long, callout_leer


class SkriptKontext:
    """Was ein Notausgang-Skript darf: SW-Objekte lesen/erzeugen, Anker auflösen, Skizzen anlegen."""

    def __init__(self, ctx, fid: str):
        self._ctx = ctx
        self._fid = fid
        self.app = ctx.app
        self.model = ctx.model
        self.callout_leer = callout_leer
        self.byref_long = byref_long

    def wert(self, x) -> float:
        return self._ctx.wert(x)

    def m(self, x) -> float:
        return self._ctx.m(x)

    def rad(self, x) -> float:
        return self._ctx.rad(x)

    def feature(self, fid: str):
        return self._ctx.ergebnis(fid).features[0]

    def flaeche(self, anker: dict):
        """Flächenanker → Flaeche (mit .objekt = IFace2, .punkt, .normale in mm)."""
        return loese_flaeche(self._ctx, anker)

    def kanten(self, anker: dict) -> list:
        return loese_kanten(self._ctx, anker)

    def ebene(self, ebene):
        """Ebene wie in der Spezifikation ("oben", {versatz}, {feature, flaeche}, {nahe}) → Skizzenebene."""
        return ebene_aufloesen(self._ctx, ebene)

    def skizze(self, ebene, elemente: list[dict], name: str = "skizze"):
        """Voll bestimmte Skizze wie in der Spezifikation; Rückgabe (Skizzen-Feature, Skizzenebene)."""
        return skizziere(self._ctx, ebene, elemente, f"{self._fid}_{name}")

    def modellpunkt_m(self, skizzenebene, u, v) -> tuple[float, float, float]:
        """Skizzenkoordinaten (mm) auf einer Skizzenebene → Modellpunkt in Metern (für API-Aufrufe)."""
        p = modellpunkt(skizzenebene.orientierung, self.wert(u), self.wert(v), skizzenebene.lage)
        return tuple(c / 1000.0 for c in p)

    def punkte_festlegen(self, feature, ebene, punkte_uv: list) -> None:
        """Nicht voll bestimmte Skizzen von feature (auch Unterskizzen, z. B. Positionsskizze des Bohrungsassistenten)
        öffnen und die Lage der Punkte (u, v) wie in der Spezifikation zum Ursprung bemaßen."""
        se = ebene_aufloesen(self._ctx, ebene)
        skizzen, unter = [], feature.GetFirstSubFeature
        while unter is not None:
            if unter.GetTypeName2 == "ProfileFeature":
                skizzen.append(unter)
            unter = unter.GetNextSubFeature
        sm = self.model.SketchManager
        for skizze in skizzen:
            if skizze.GetSpecificFeature2.GetConstrainedStatus == sw.SW_FULLY_CONSTRAINED:
                continue
            sw.auswahl_leeren(self.model)
            skizze.Select2(False, 0)
            sm.InsertSketch(True)  # öffnet die selektierte Skizze (S9b)
            try:
                skizzierer = Skizzierer(self._ctx, se, sm.ActiveSketch)
                with sw.einstellung(self.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False):
                    for u, v in punkte_uv:
                        if skizzierer.hat_punkt(u, v):
                            skizzierer.lage((u, v), (self.wert(u) + 8, self.wert(v) + 8))
            finally:
                sm.InsertSketch(True)

    def waehle(self, objekt, marke: int = 0, anhaengen: bool = False) -> None:
        sw.waehle(self.model, objekt, marke, anhaengen)

    def auswahl_leeren(self) -> None:
        sw.auswahl_leeren(self.model)


@handler("skript")
def skript(ctx, f: dict) -> FeatureErgebnis:
    datei = ctx.spec_pfad.parent / f["datei"]
    quelltext = datei.read_text(encoding="utf-8")
    befunde = pruefe_skript(quelltext)
    if befunde:
        raise BauFehler(SKRIPT_FEHLER, f"{datei.name}: {befunde[0]['meldung']} (Zeile {befunde[0]['zeile']})",
                        schritt="pruefung")
    namensraum: dict = {"__name__": f"swki_skript_{f['id']}"}
    exec(compile(quelltext, str(datei), "exec"), namensraum)  # nach statischer Prüfung erlaubt
    try:
        ergebnis = namensraum["bauen"](SkriptKontext(ctx, f["id"]))
    except BauFehler:
        raise
    except Exception as e:
        raise BauFehler(SKRIPT_FEHLER, f"{datei.name}: {type(e).__name__}: {e}", schritt="ausfuehren") from e
    features = ergebnis if isinstance(ergebnis, (list, tuple)) else [ergebnis]
    if not features or any(x is None for x in features):
        raise BauFehler(SKRIPT_FEHLER, f"{datei.name}: bauen(ctx) hat kein Feature zurückgegeben", schritt="ausfuehren")
    for i, feature in enumerate(features):
        feature.Name = f["id"] if i == 0 else f"{f['id']}_{i + 1}"
    return FeatureErgebnis(list(features))
```

`swki/compiler/handler/__init__.py` (vollständig):

```python
"""Alle Feature-Handler; der Import registriert sie in swki.compiler.registry.HANDLER."""

from swki.compiler.handler import bohrung, extrusion, kanten, muster, rotation, skript  # noqa: F401
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_skript.py`
Expected: 2× `OK`.

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/handler tests/live
git commit -m "compiler: Handler skript (Notausgang)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 14: `swki bauen`

**Files:**
- Create: `swki/compiler/bauen.py`, `tests/live/test_live_bauen.py`
- Modify: `swki/cli.py` (`_befehlsgruppen`)

**Interfaces:**
- Consumes: alles aus Task 3–13; `lade_rechner`, `lade_standard`.
- Produces: `BauAbbruch(SwkiFehler)` (daten = Ergebnis); `bauen(spec_pfad, lauf=None) -> dict` `{status, auftrag, lauf, ordner, dateien, knoten, fehler, dauer_s}`; Befehl `swki bauen <spec> [--lauf N]`.
- Ablauf (Spec §5): Spezifikation laden, Freigabe prüfen (sonst `FREIGABE_FEHLT`/`FREIGABE_VERALTET`), neuer Lauf, neues Teil aus Vorlage, globale Variablen, Material, Eigenschaften (Ersteller, Auftrag, Material, Spezifikation), Features bauen (Rebuild nach jedem Knoten, Halt beim ersten Fehler), **immer** speichern (`<auftrag>_<name>.sldprt` und `.step`, auch nach Fehler zur Diagnose), Teil schließen, Protokoll nach `lauf-<n>/protokoll.json` und `protokolle/<spec>.lauf-<n>.protokoll.json`. Bei Fehler Exit 1 mit Fehlercode und Knotenliste.

- [ ] **Step 1: Live-Tests schreiben**

`tests/live/test_live_bauen.py`:

```python
"""Live: swki freigeben + swki bauen Ende zu Ende (SolidWorks muss laufen)."""

import json
import shutil

import pytest
import yaml

from swki.auftrag import lauf_datei, lauf_ordner
from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw

SPEC = {
    "art": "teil", "name": "Platte", "material": "1.2312", "eigenschaften": {"Benennung": "Testplatte"},
    "parameter": {"L": 100},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}},
        {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [["=-L/2+15", 0], ["=L/2-15", 0]], "durchmesser": 8, "durch": True},
    ],
    "pruefung": {"huellquader": ["=L", 20, 60]},
}


@pytest.fixture
def auftrag(tmp_path):
    ordner = tmp_path / "SWKI-LIVE-BAUEN"
    ordner.mkdir()
    spec_pfad = ordner / "platte.yaml"
    spec_pfad.write_text(yaml.safe_dump(SPEC, allow_unicode=True), encoding="utf-8")
    yield spec_pfad
    shutil.rmtree(lade_rechner().arbeitsordner / "SWKI-LIVE-BAUEN", ignore_errors=True)


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_bauen_ohne_freigabe_verweigert(capsys, auftrag):
    code, daten = _lauf(capsys, "bauen", str(auftrag))
    assert code == 1 and daten["code"] == "FREIGABE_FEHLT"


def test_freigeben_und_bauen(capsys, auftrag):
    assert _lauf(capsys, "freigeben", str(auftrag))[0] == 0
    code, daten = _lauf(capsys, "bauen", str(auftrag))
    assert code == 0, daten
    assert daten["lauf"] == 1 and daten["status"] == "ok"
    assert [k["status"] for k in daten["knoten"]] == ["ok", "ok"]
    ordner = lauf_ordner(lade_rechner(), "SWKI-LIVE-BAUEN", 1)
    assert (ordner / "SWKI-LIVE-BAUEN_Platte.sldprt").stat().st_size > 0
    assert (ordner / "SWKI-LIVE-BAUEN_Platte.step").stat().st_size > 0
    protokoll = json.loads(lauf_datei(auftrag, 1, "protokoll").read_text(encoding="utf-8"))
    assert protokoll["status"] == "ok" and set(protokoll["phasen"]) == {"vorbereiten", "bauen", "speichern"}
    # zweiter Lauf baut frisch in lauf-2
    code, daten = _lauf(capsys, "bauen", str(auftrag))
    assert code == 0 and daten["lauf"] == 2


def test_bauabbruch_wird_protokolliert(capsys, auftrag):
    spec = {**SPEC, "features": [*SPEC["features"], {
        "id": "f3", "typ": "fase", "kanten": [{"nahe": [50, 20, 30]}], "abstand": 1}]}  # Ecke → mehrdeutig
    auftrag.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    _lauf(capsys, "freigeben", str(auftrag))
    code, daten = _lauf(capsys, "bauen", str(auftrag))
    assert code == 1
    assert daten["fehler"]["code"] == "REFERENZ_MEHRDEUTIG"
    assert [k["status"] for k in daten["knoten"]] == ["ok", "ok", "fehler"]
    assert daten["dateien"]["teil"].endswith(".sldprt")  # Teilstand wird zur Diagnose trotzdem gespeichert
```

- [ ] **Step 2: Live-Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_bauen.py`
Expected: FEHLER (Befehl `bauen` unbekannt → JSON-Fehler).

- [ ] **Step 3: Implementieren**

`swki/compiler/bauen.py`:

```python
"""swki bauen: freigegebene Spezifikation in einem frischen Lauf bauen, speichern und protokollieren."""

import time
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner, naechster_lauf
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.eigenschaften import eigenschaften_fuer, globale_variablen, setze_eigenschaften, setze_material
from swki.compiler.fehler import fehler_dict
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.konfig import lade_rechner, lade_standard
from swki.spec.freigabe import pruefe_freigabe
from swki.spec.laden import lade_spec
from swki.verbindung import verbinde


class BauAbbruch(SwkiFehler):
    def __init__(self, ergebnis: dict):
        f = ergebnis["fehler"]
        super().__init__(f"Bau abgebrochen: {f['code']} – {f['meldung']}")
        self.daten = ergebnis


def _vorbereiten(app, model, spec: dict, auftrag: str) -> None:
    globale_variablen(model, spec.get("parameter", {}))
    if "material" in spec:
        setze_material(app, model, spec["material"])
    setze_eigenschaften(model, eigenschaften_fuer(spec, auftrag))


def bauen(spec_pfad: Path, lauf: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    lauf = lauf or naechster_lauf(r, auftrag)
    ordner = lauf_ordner(r, auftrag, lauf)
    name = dateiname(spec, auftrag, standard)
    protokoll = Protokoll(auftrag, spec_pfad.name, lauf, r.sw_jahr)
    beginn = time.perf_counter()
    fehler = None

    app = verbinde(r.sw_jahr)
    with protokoll.phase("vorbereiten"):
        model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, spec_pfad, standard["toleranzen"]["anker_mm"])
        try:
            with protokoll.phase("vorbereiten"):
                _vorbereiten(app, model, spec, auftrag)
        except Exception as e:
            fehler = e
        if fehler is None:
            with protokoll.phase("bauen"):
                fehler = baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
        with protokoll.phase("speichern"):
            dateien = {"teil": ordner / f"{name}.sldprt", "step": ordner / f"{name}.step"}
            try:
                for pfad in dateien.values():
                    sw.speichere(model, pfad)
                protokoll.dateien = {art: str(pfad) for art, pfad in dateien.items()}
            except Exception as e:
                fehler = fehler or e
    finally:
        sw.schliesse(app, model)  # Titel wird hier neu gelesen (nach SaveAs geändert)

    protokoll.status = "fehler" if fehler else "ok"
    protokoll.fehler = fehler_dict(fehler) if fehler else None
    protokoll.dauer_s = round(time.perf_counter() - beginn, 3)
    protokoll.schreibe(ordner / "protokoll.json")
    protokoll.schreibe(lauf_datei(spec_pfad, lauf, "protokoll"))
    ergebnis = {
        "status": protokoll.status,
        "auftrag": auftrag,
        "lauf": lauf,
        "ordner": str(ordner),
        "dateien": protokoll.dateien,
        "knoten": [{"id": k.id, "status": k.status, "sw_name": k.sw_name} for k in protokoll.knoten],
        "fehler": protokoll.fehler,
        "dauer_s": protokoll.dauer_s,
    }
    if fehler:
        raise BauAbbruch(ergebnis)
    return ergebnis


def _bauen(args) -> dict:
    return bauen(Path(args.spec), args.lauf)


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("bauen", help="freigegebene Spezifikation in SolidWorks bauen (neuer Lauf)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=int, help="Laufnummer (Vorgabe: nächste freie)")
    p.set_defaults(func=_bauen)
```

In `swki/cli.py` `_befehlsgruppen` ersetzen durch:

```python
def _befehlsgruppen() -> list:
    from swki import rechner
    from swki.api import bauen
    from swki.compiler import bauen as compiler_bauen
    from swki.spec import befehle as spec_befehle

    return [rechner, bauen, spec_befehle, compiler_bauen]
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle Unit-Tests grün.

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_bauen.py`
Expected: 3× `OK` (ohne Freigabe verweigert; Lauf 1 und 2 mit .sldprt/.step/Protokoll; Abbruch mit `REFERENZ_MEHRDEUTIG` wird protokolliert, Teilstand gespeichert).

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/bauen.py swki/cli.py tests/live
git commit -m "compiler: swki bauen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 15: Abschluss Stufe 2a: Wissensdatei, CLAUDE.md, Gesamtprüfung

**Files:**
- Modify: `swki/wissen/pywin32-fallstricke.md` (Abschnitt anhängen), `CLAUDE.md` (Abschnitt ergänzen)

**Interfaces:**
- Keine neuen Schnittstellen.

- [ ] **Step 1: Wissensdatei ergänzen – an `swki/wissen/pywin32-fallstricke.md` anhängen:**

```markdown
## Stufe 2a: Compiler (live belegt beim Schreiben des Plans und in den Live-Tests)

- **Voll bestimmte Skizzen ohne FullyDefineSketch:** Elemente mit `SketchManager.AddToDB = True` erzeugen und alle Maße selbst
  setzen (Größen per `AddDimension2`, Lage jedes Kennpunkts zum Ursprung per `AddHorizontalDimension2`/`AddVerticalDimension2`,
  bei 0 `SketchAddConstraints("sgVERTICALPOINTS2D"/"sgHORIZONTALPOINTS2D")`, bei (0,0) `"sgCOINCIDENT"`).
  `FullyDefineSketch` lässt mit AddToDB erzeugte Elemente unterbestimmt und bemaßt ohne Bezug relativ zu irgendeinem Element.
- **Ursprungspunkt sprachunabhängig:** Feature mit `GetTypeName2 == "OriginProfileFeature"`, dann
  `Extension.SelectByID2(f"Point1@{name}", "EXTSKETCHPOINT", 0, 0, 0, False, 0, callout_leer(), 0)` und
  `SelectionManager.GetSelectedObject6(1, -1)`.
- **`CreateCenterRectangle` legt den Mittelpunkt nicht verlässlich an** (je nach SolidWorks-Zustand fehlten Mittelpunkt und
  Diagonal-Beziehungen) → `CreateCornerRectangle` und die Ecke bemaßen.
- **`ViewZoomtofit2` und `BlankRefGeom`** nur nach `model._FlagAsMethod(...)` und mit `()`; der reine Attributzugriff passt die
  Ansicht nicht ein.
- **`IPartDoc.FeatureByName(name)`** findet Features im geöffneten Teil (Features heißen wie ihre Spezifikations-ID).
- **Abgebrochene Prozesse** (Zeitlimit, Kill) setzen umgeschaltete Benutzereinstellungen nicht zurück – nach einem Abbruch
  `swInputDimValOnCreate` (Toggle 10) prüfen. Live-Tests deshalb einzeln mit Zeitlimit (`tests/live_einzeln.py`).
- **Lineare Muster** lassen Instanzen außerhalb des Körpers ohne Meldung weg (nur Volumen/Achsen zeigen es).
```

- [ ] **Step 2: `CLAUDE.md` ergänzen – nach dem Abschnitt `## SolidWorks` einfügen:**

```markdown
## Konstruieren (Stufe 2)
- Spezifikation eines Teils: YAML nach `schema/teil.schema.json` im Auftragsordner (`auftraege/<auftrag>/`).
- `swki validieren <spec>` → `swki freigeben <spec>` (nur nach ausdrücklichem OK des Nutzers) → `swki bauen <spec>`.
- Nach der Freigabe nur noch den Bauweg ändern (Features, Anker, Reihenfolge, Skripte); Parameter, Material, Eigenschaften und
  `pruefung` sind tabu (`swki bauen` verweigert sonst mit FREIGABE_VERALTET).
- Was das Format nicht kann: `typ: skript` mit `luecke:` (Notausgang), nie still weglassen.
- Live-Tests einzeln mit Zeitlimit: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> …`.
```

- [ ] **Step 3: API-Prüfung**

Run: `.venv\Scripts\python.exe -m swki api pruefe-code`
Expected: `{"max_jahr": 2025, "befunde": []}`, Exit 0.

- [ ] **Step 4: Gesamte Testsuite**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle Unit-Tests grün.

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live`
Expected: alle Live-Tests `OK` (Stufe 0/1 und 2a).

- [ ] **Step 5: Commit**

```powershell
git add swki/wissen CLAUDE.md
git commit -m "stufe2a: Wissensdatei und CLAUDE.md" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Übergabe**

Dem Nutzer berichten (Tests, Live-Ergebnisse, Abweichungen); weiter mit Plan `2026-09-27-stufe-2b-pruefung-schleife-referenzen.md`. Kein Push ohne Rückfrage.

---
