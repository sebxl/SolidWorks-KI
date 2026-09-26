# Stufe 0 + 1: Fundament, Machbarkeit und API-Nachschlagewerk – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein lauffähiges, auf SW 2025 und 2026 einrichtbares Projektgerüst mit gesperrtem Lese-MCP, einem lokalen SolidWorks-API-Nachschlagewerk und dokumentierten Machbarkeitstests, auf deren Basis Stufe 2 (Einzelteile) geplant wird.

**Architecture:** Python-Paket `swki` mit Kommandozeile (`python -m swki …`, Ausgabe JSON). Rechnerspezifisches steht in `config/rechner.yaml` (nicht im Git) und unter `%USERPROFILE%\.swki\`. Das API-Nachschlagewerk liest Signaturen und Enums verbindlich aus den Typbibliotheken (`sldworks.tlb`, `swconst.tlb`) und ergänzt Beschreibungen und „verfügbar seit“ aus der lokal entpackten CHM-Hilfe; alles landet in einem SQLite-FTS5-Index. Machbarkeitstests sind Skripte unter `spikes/`, die JSON-Ergebnisse schreiben.

**Tech Stack:** Python ≥ 3.13 (Rechner A: 3.14), pywin32, PyYAML, pytest, SQLite FTS5 (Standardbibliothek), PowerShell 5.1, Git/GitHub CLI, SolidworksMCP-python (Commit `600624fc93dad959600366bd0f3d281e4eeeacf5`).

**Spec:** [docs/superpowers/specs/2026-09-26-solidworks-ki-design.md](../specs/2026-09-26-solidworks-ki-design.md)

**Reihenfolge:** Abweichend von der Stufennummerierung der Spec kommt das API-Nachschlagewerk (Stufe 1, Tasks 8–12) **vor** den Machbarkeitstests (Stufe 0, Tasks 13–15), damit die Spikes Signaturen und Enum-Werte nachschlagen statt raten. Pläne für Stufe 2–4 folgen nach Auswertung von Task 15.

## Global Constraints

- Windows 11; SOLIDWORKS 2025 (Rechner A, deutsche Oberfläche) und SOLIDWORKS 2026 (Rechner B) – kein Code darf ein Jahr fest verdrahten; das Jahr kommt aus `config/rechner.yaml`.
- Python `requires-python = ">=3.13"`.
- Keine festen Pfade im Git. Rechnerspezifisches nur in `config/rechner.yaml` (gitignored) und `%USERPROFILE%\.swki\` (überschreibbar über Umgebungsvariable `SWKI_HOME`, nur für Tests).
- SolidworksMCP-python gepinnt auf `600624fc93dad959600366bd0f3d281e4eeeacf5`, installiert mit `pip install -e .` ohne Extras; keine UI-/Agenten-Schicht; `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GH_TOKEN` in der Server-Umgebung leer.
- MCP nur lesend: alle schreibenden Tools per `permissions.deny`; mindestens gesperrt `execute_macro`, `batch_execute_macros`, `pack_and_go_assembly`, `batch_file_operations`, `execute_workflow`, `batch_process_files`.
- Der API-Index (Dassault-Dokumentation) bleibt lokal unter `%USERPROFILE%\.swki\api\<jahr>\`; ins Git kommt nur Code. Testfixtures sind selbst geschrieben, keine Auszüge aus der Hilfe.
- Compiler-Code darf später nur API-Aufrufe nutzen, die in SW 2025 verfügbar sind (`max_jahr_compiler: 2025`).
- Spikes und Live-Tests fassen nur selbst angelegte Dokumente an und speichern nur im Arbeitsordner (`%USERPROFILE%\.swki\arbeit\`).
- Kommandozeile: alle `swki`-Befehle geben genau ein JSON-Objekt auf stdout aus (UTF-8, `ensure_ascii=False`); Exit-Code 0 = ok, 1 = Fehler.
- Tests: `pytest` läuft standardmäßig ohne SolidWorks (`-m "not sw"`); Live-Tests tragen den Marker `sw` und laufen mit `pytest -m sw` bei geöffnetem SolidWorks.
- Kein `git push` ohne Rückfrage beim Nutzer. Commits mit Trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Sprache in Code-Bezeichnern, Meldungen und Doku: Deutsch; SolidWorks-API-Namen bleiben englisch.

## Dateistruktur nach diesem Plan

```
SolidWorks-KI/
  CLAUDE.md
  pyproject.toml
  .gitignore                        (existiert)
  .mcp.json
  .claude/settings.json
  config/standard.yaml
  config/rechner.beispiel.yaml
  config/mcp-tools-alle.json        (generiert, committet)
  config/mcp-lesetools.txt
  setup/einrichten.ps1
  setup/mcp_tools_auflisten.py      (läuft in der venv des MCP-Servers)
  setup/mcp_sperren.py
  swki/__init__.py
  swki/__main__.py
  swki/cli.py                       Argumente, JSON-Ausgabe, Befehls-Dispatch
  swki/konfig.py                    Rechner-Dataclass, Laden/Schreiben der YAML-Konfiguration
  swki/rechner.py                   Registry-Zugriff, SW-Erkennung
  swki/verbindung.py                Anbindung an laufendes SolidWorks, Einheiten, VARIANT-Hilfen
  swki/api/__init__.py
  swki/api/typbib.py                Typbibliothek lesen (Member, Parameter, Enums)
  swki/api/chm.py                   CHM entpacken, HTML-Seiten lesen
  swki/api/index.py                 SQLite-Index bauen und abfragen
  swki/api/bauen.py                 Index aus lokaler SW-Installation erzeugen
  swki/api/codepruefung.py          Code auf API-Aufrufe jünger als max_jahr prüfen
  swki/wissen/pywin32-fallstricke.md
  spikes/_gemeinsam.py
  spikes/s1_verbinden.py … s7_toolbox.py
  docs/stufe0/ergebnisse/*.json
  docs/stufe0/ergebnisse.md
  tests/conftest.py
  tests/test_cli.py
  tests/test_konfig.py
  tests/test_rechner.py
  tests/test_verbindung.py
  tests/test_mcp_sperren.py
  tests/api/test_typbib.py
  tests/api/test_chm.py
  tests/api/test_index.py
  tests/api/test_codepruefung.py
  tests/api/test_cli_api.py
  tests/live/test_live_verbindung.py
  tests/live/test_live_api.py
```

---

### Task 1: Projektgerüst, Git-Identität, CLAUDE.md

**Files:**
- Create: `pyproject.toml`, `swki/__init__.py`, `swki/__main__.py`, `swki/cli.py`, `tests/conftest.py`, `tests/test_cli.py`, `CLAUDE.md`

**Interfaces:**
- Produces: `swki.cli.main(argv: list[str] | None = None) -> int`; `swki.cli.ausgabe(daten: dict) -> None` (druckt JSON); `swki.cli.registriere(unterparser_fn)`-Muster: jede Befehlsgruppe liefert `def einrichten(subparsers) -> None` und setzt `func` auf eine Funktion `(args) -> dict`. `swki.__version__ = "0.1.0"`.

- [x] **Step 1: Git-Identität** – erledigt in der Planungssitzung (repo-lokal `user.name = sebXL`, `user.email = etti.etienne@gmail.com`; Design, Tool-Prüfung und dieser Plan sind committet). Nur prüfen: `git config user.email` → `etti.etienne@gmail.com`.

- [ ] **Step 2: `pyproject.toml` anlegen**

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "swki"
version = "0.1.0"
description = "SolidWorks-KI: Spezifikation, Compiler und Prüfung für Claude Code"
requires-python = ">=3.13"
dependencies = [
  "pywin32>=311",
  "PyYAML>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.setuptools.packages.find]
include = ["swki*"]

[tool.setuptools.package-data]
swki = ["wissen/*.md"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m \"not sw\""
markers = ["sw: benötigt ein laufendes SolidWorks"]
```

- [ ] **Step 3: Failing test schreiben** – `tests/test_cli.py`

```python
import json
import subprocess
import sys

from swki.cli import main


def test_version_als_json(capsys):
    assert main(["version"]) == 0
    daten = json.loads(capsys.readouterr().out)
    assert daten == {"version": "0.1.0"}


def test_modulaufruf():
    ergebnis = subprocess.run(
        [sys.executable, "-m", "swki", "version"], capture_output=True, text=True, encoding="utf-8"
    )
    assert ergebnis.returncode == 0
    assert json.loads(ergebnis.stdout)["version"] == "0.1.0"


def test_unbekannter_befehl_gibt_fehler(capsys):
    assert main(["gibtsnicht"]) != 0
```

`tests/conftest.py`:

```python
import pytest


@pytest.fixture
def swki_home(tmp_path, monkeypatch):
    """Isoliertes SWKI_HOME für Tests."""
    monkeypatch.setenv("SWKI_HOME", str(tmp_path / "swki_home"))
    return tmp_path / "swki_home"
```

- [ ] **Step 4: venv anlegen und Test fehlschlagen lassen**

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest tests/test_cli.py -v
```

Expected: FAIL mit `ModuleNotFoundError: No module named 'swki'` bzw. `ImportError`.

- [ ] **Step 5: Implementierung**

`swki/__init__.py`:

```python
__version__ = "0.1.0"
```

`swki/__main__.py`:

```python
from swki.cli import main

raise SystemExit(main())
```

`swki/cli.py`:

```python
"""Kommandozeile von swki. Jeder Befehl liefert ein dict, das als JSON ausgegeben wird."""

import argparse
import json
import sys

from swki import __version__


class SwkiFehler(Exception):
    """Fachlicher Fehler, der als JSON {"fehler": ...} gemeldet wird."""


def ausgabe(daten: dict) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(daten, ensure_ascii=False, indent=2, default=str))


def _version(args) -> dict:
    return {"version": __version__}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swki")
    sub = parser.add_subparsers(dest="befehl", required=True)
    p = sub.add_parser("version")
    p.set_defaults(func=_version)
    for modul in _befehlsgruppen():
        modul.einrichten(sub)
    return parser


def _befehlsgruppen() -> list:
    """Module mit einer Funktion einrichten(subparsers). Wird in späteren Tasks ergänzt."""
    return []


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 2)
    try:
        ausgabe(args.func(args))
        return 0
    except SwkiFehler as e:
        ausgabe({"fehler": str(e)})
        return 1
```

- [ ] **Step 6: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: 3 passed.

- [ ] **Step 7: `CLAUDE.md` anlegen** (Stand Stufe 0/1; wird in Stufe 2 erweitert)

```markdown
# SolidWorks-KI – Regeln für Claude

Design: docs/superpowers/specs/2026-09-26-solidworks-ki-design.md
Aktueller Plan: docs/superpowers/plans/

## Umgebung
- Python immer über `.venv\Scripts\python.exe`, swki über `.venv\Scripts\python.exe -m swki …` (Ausgabe JSON).
- SolidWorks-Version und Pfade stehen in `config/rechner.yaml` (pro Rechner, nicht im Git). Nie ein Jahr oder einen Pfad fest in Code schreiben.
- Einrichten eines Rechners: `powershell -ExecutionPolicy Bypass -File setup\einrichten.ps1`.

## SolidWorks
- Gebaut wird nur über `swki` bzw. Spikes/Skripte dieses Repos. Das MCP `solidworks-mcp` dient nur zum Ansehen (Feature-Baum, Masseeigenschaften, Screenshots).
- Vor jedem neuen SolidWorks-API-Aufruf im Code: `swki api methode <Interface.Member>` bzw. `swki api enum <Name>` nachschlagen. Nicht raten. Parameteranzahl und Enum-Werte aus dem Index sind verbindlich.
- Die API rechnet in Metern und Radiant. Spezifikationen und Ausgaben an den Nutzer in mm und Grad.
- Die Oberfläche ist deutsch: keine englischen Feature-/Ebenennamen verwenden; Ebenen über Position im Feature-Baum finden.
- Nur Dokumente anfassen, die selbst angelegt wurden. Nur im Arbeitsordner speichern (`arbeitsordner` aus `config/rechner.yaml`). Nie in Kundenordner oder Bibliotheks-Originale schreiben.
- Compiler-Code nur mit API-Aufrufen, die in SW 2025 verfügbar sind (`swki api pruefe-code`).

## Git
- Kein `git push` ohne Rückfrage.
- Erzeugte SolidWorks-Dateien kommen nicht ins Git.

## Tests
- `.venv\Scripts\python.exe -m pytest` (ohne SolidWorks), `… -m sw` (mit geöffnetem SolidWorks).
```

- [ ] **Step 8: Commit**

```powershell
git add pyproject.toml swki tests CLAUDE.md
git commit -m "swki: Projektgerüst mit JSON-Kommandozeile" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Konfiguration (`standard.yaml`, `rechner.yaml`)

**Files:**
- Create: `swki/konfig.py`, `config/standard.yaml`, `config/rechner.beispiel.yaml`, `tests/test_konfig.py`

**Interfaces:**
- Consumes: `swki.cli.SwkiFehler`
- Produces:
  - `PROJEKT: Path` (Repo-Wurzel)
  - `class KonfigFehler(SwkiFehler)`
  - `@dataclass(frozen=True) class Rechner: sw_jahr: int; installationsordner: Path; vorlage_teil: Path; vorlage_baugruppe: Path | None; materialdatenbank: Path | None; arbeitsordner: Path`
  - `swki_home() -> Path`
  - `rechner_pfad() -> Path` (= `PROJEKT / "config" / "rechner.yaml"`)
  - `lade_standard(pfad: Path | None = None) -> dict`
  - `lade_rechner(pfad: Path | None = None) -> Rechner`
  - `schreibe_rechner(r: Rechner, pfad: Path | None = None) -> None`
  - `rechner_als_dict(r: Rechner) -> dict` (Pfade als str)

- [ ] **Step 1: Failing tests** – `tests/test_konfig.py`

```python
from pathlib import Path

import pytest

from swki import konfig
from swki.konfig import KonfigFehler, Rechner, lade_rechner, lade_standard, rechner_als_dict, schreibe_rechner


def _rechner(tmp_path):
    return Rechner(
        sw_jahr=2025,
        installationsordner=Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS"),
        vorlage_teil=Path(r"C:\ProgramData\SolidWorks\SOLIDWORKS 2025\templates\Teil.prtdot"),
        vorlage_baugruppe=None,
        materialdatenbank=None,
        arbeitsordner=tmp_path / "arbeit",
    )


def test_rechner_fehlt_nennt_befehl(tmp_path):
    with pytest.raises(KonfigFehler, match="rechner init"):
        lade_rechner(tmp_path / "rechner.yaml")


def test_rechner_rundreise(tmp_path):
    pfad = tmp_path / "rechner.yaml"
    r = _rechner(tmp_path)
    schreibe_rechner(r, pfad)
    assert lade_rechner(pfad) == r


def test_rechner_als_dict_hat_strings(tmp_path):
    d = rechner_als_dict(_rechner(tmp_path))
    assert d["sw_jahr"] == 2025
    assert isinstance(d["vorlage_teil"], str)
    assert d["vorlage_baugruppe"] is None


def test_standard_projektdatei():
    daten = lade_standard()
    assert daten["max_nachbesserungen"] == 3
    assert daten["api"]["max_jahr_compiler"] == 2025


def test_swki_home_aus_umgebung(swki_home):
    assert konfig.swki_home() == swki_home
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_konfig.py -v`
Expected: FAIL (`ModuleNotFoundError: swki.konfig`).

- [ ] **Step 3: Implementierung** – `swki/konfig.py`

```python
"""Projekt- und Rechnerkonfiguration."""

import os
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from swki.cli import SwkiFehler

PROJEKT = Path(__file__).resolve().parent.parent


class KonfigFehler(SwkiFehler):
    pass


@dataclass(frozen=True)
class Rechner:
    sw_jahr: int
    installationsordner: Path
    vorlage_teil: Path
    vorlage_baugruppe: Path | None
    materialdatenbank: Path | None
    arbeitsordner: Path


_PFADFELDER = ("installationsordner", "vorlage_teil", "vorlage_baugruppe", "materialdatenbank", "arbeitsordner")


def swki_home() -> Path:
    return Path(os.environ.get("SWKI_HOME", Path.home() / ".swki"))


def rechner_pfad() -> Path:
    return PROJEKT / "config" / "rechner.yaml"


def lade_standard(pfad: Path | None = None) -> dict:
    pfad = pfad or PROJEKT / "config" / "standard.yaml"
    with open(pfad, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rechner_als_dict(r: Rechner) -> dict:
    d = asdict(r)
    for feld in _PFADFELDER:
        d[feld] = str(d[feld]) if d[feld] is not None else None
    return d


def schreibe_rechner(r: Rechner, pfad: Path | None = None) -> None:
    pfad = pfad or rechner_pfad()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("# Rechnerspezifisch – nicht ins Git. Erzeugt von: swki rechner init\n")
        yaml.safe_dump(rechner_als_dict(r), f, allow_unicode=True, sort_keys=False)


def lade_rechner(pfad: Path | None = None) -> Rechner:
    pfad = pfad or rechner_pfad()
    if not pfad.exists():
        raise KonfigFehler(f"{pfad} fehlt. Zuerst ausführen: python -m swki rechner init")
    with open(pfad, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    for feld in _PFADFELDER:
        d[feld] = Path(d[feld]) if d.get(feld) else None
    return Rechner(**d)
```

`config/standard.yaml`:

```yaml
# Projektweite Voreinstellungen (im Git)
max_nachbesserungen: 3
namensschema:
  datei: "{auftrag}_{name}"
  eigenschaften: [Benennung, Material, Ersteller, Auftrag]
toleranzen:
  anker_mm: 0.1
  volumen_prozent: 0.5
api:
  max_jahr_compiler: 2025
```

`config/rechner.beispiel.yaml`:

```yaml
# Vorlage – echte Datei wird von "python -m swki rechner init" erzeugt (config/rechner.yaml, nicht im Git)
sw_jahr: 2025
installationsordner: 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS'
vorlage_teil: 'C:\ProgramData\SolidWorks\SOLIDWORKS 2025\templates\Teil.prtdot'
vorlage_baugruppe: 'C:\ProgramData\SolidWorks\SOLIDWORKS 2025\templates\Baugruppe.asmdot'
materialdatenbank: 'C:\ProgramData\SolidWorks\SOLIDWORKS 2024\Benutzerdefinierte Materialien'
arbeitsordner: 'C:\Users\<Benutzer>\.swki\arbeit'
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_konfig.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add swki/konfig.py config tests/test_konfig.py
git commit -m "swki: Projekt- und Rechnerkonfiguration" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: SolidWorks-Erkennung und `swki rechner init|zeigen`

**Files:**
- Create: `swki/rechner.py`, `tests/test_rechner.py`
- Modify: `swki/cli.py` (`_befehlsgruppen` gibt `[rechner]` zurück)

**Interfaces:**
- Consumes: `Rechner`, `KonfigFehler`, `swki_home()`, `schreibe_rechner`, `lade_rechner`, `rechner_pfad`, `rechner_als_dict`
- Produces:
  - `class Registry(Protocol)`: `unterschluessel(pfad: str) -> list[str]`, `wert(pfad: str, name: str) -> str | None` – Pfade mit Präfix `HKLM\` oder `HKCU\`
  - `class WinRegistry` (winreg-Implementierung)
  - `sw_jahre(reg: Registry) -> list[int]`
  - `erkenne(reg: Registry, jahr: int | None = None) -> Rechner`
  - `einrichten(subparsers)` mit Befehlen `rechner init [--jahr N] [--neu]` und `rechner zeigen`

- [ ] **Step 1: Failing tests** – `tests/test_rechner.py`

```python
import pytest

from swki.konfig import KonfigFehler
from swki.rechner import erkenne, sw_jahre


class FakeRegistry:
    def __init__(self, schluessel: dict[str, list[str]], werte: dict[str, dict[str, str]]):
        self.schluessel = schluessel
        self.werte = {k.lower(): {n.lower(): v for n, v in w.items()} for k, w in werte.items()}

    def unterschluessel(self, pfad):
        return self.schluessel.get(pfad, [])

    def wert(self, pfad, name):
        return self.werte.get(pfad.lower(), {}).get(name.lower())


def _reg(tmp_path, teil="", baugruppe=""):
    vorlagen = tmp_path / "templates"
    vorlagen.mkdir()
    (vorlagen / "Teil.prtdot").write_text("x")
    (vorlagen / "Baugruppe.asmdot").write_text("x")
    return FakeRegistry(
        {r"HKLM\SOFTWARE\SolidWorks": ["AddIns", "SOLIDWORKS 2025", "SOLIDWORKS 2026", "Licenses"]},
        {
            r"HKLM\SOFTWARE\SolidWorks\SOLIDWORKS 2025\Setup": {"SolidWorks Folder": "C:\\SW25\\"},
            r"HKLM\SOFTWARE\SolidWorks\SOLIDWORKS 2026\Setup": {"SolidWorks Folder": "C:\\SW26\\"},
            r"HKCU\Software\SolidWorks\SOLIDWORKS 2025\Document Templates": {
                "Default Part template": teil, "Default Assembly Template": baugruppe,
            },
            r"HKCU\Software\SolidWorks\SOLIDWORKS 2025\ExtReferences": {
                "Document Template Folders": str(vorlagen),
                "Material Database Folders": r"C:\Mat\Eigene;C:\Mat\Zweite",
            },
        },
    ), vorlagen


def test_sw_jahre(tmp_path):
    reg, _ = _reg(tmp_path)
    assert sw_jahre(reg) == [2025, 2026]


def test_erkenne_jahr_und_vorlagen(tmp_path, swki_home):
    reg, vorlagen = _reg(tmp_path, teil=str(tmp_path / "templates" / "Teil.prtdot"))
    r = erkenne(reg, jahr=2025)
    assert r.sw_jahr == 2025
    assert str(r.installationsordner) == r"C:\SW25"
    assert r.vorlage_teil == vorlagen / "Teil.prtdot"
    assert r.vorlage_baugruppe == vorlagen / "Baugruppe.asmdot"   # Rückfall: Suche im Vorlagenordner
    assert str(r.materialdatenbank) == r"C:\Mat\Eigene"
    assert r.arbeitsordner == swki_home / "arbeit"


def test_ohne_jahr_neuestes(tmp_path, swki_home):
    reg, _ = _reg(tmp_path)
    reg.werte[r"hkcu\software\solidworks\solidworks 2026\extreferences"] = {
        "document template folders": str(tmp_path / "templates")
    }
    assert erkenne(reg).sw_jahr == 2026


def test_unbekanntes_jahr(tmp_path):
    reg, _ = _reg(tmp_path)
    with pytest.raises(KonfigFehler, match="2019"):
        erkenne(reg, jahr=2019)


def test_kein_solidworks():
    with pytest.raises(KonfigFehler, match="Kein SOLIDWORKS"):
        erkenne(FakeRegistry({}, {}))
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_rechner.py -v`
Expected: FAIL (`ModuleNotFoundError: swki.rechner`).

- [ ] **Step 3: Implementierung** – `swki/rechner.py`

```python
"""Erkennung der lokalen SolidWorks-Installation und Befehle "swki rechner …"."""

import re
from pathlib import Path
from typing import Protocol

from swki.konfig import (
    KonfigFehler, Rechner, lade_rechner, rechner_als_dict, rechner_pfad, schreibe_rechner, swki_home,
)

_BASIS = r"HKLM\SOFTWARE\SolidWorks"
_JAHR_RE = re.compile(r"^SOLIDWORKS (\d{4})$")


class Registry(Protocol):
    def unterschluessel(self, pfad: str) -> list[str]: ...
    def wert(self, pfad: str, name: str) -> str | None: ...


class WinRegistry:
    def _oeffne(self, pfad: str):
        import winreg

        hive_name, _, rest = pfad.partition("\\")
        hive = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}[hive_name]
        return winreg.OpenKey(hive, rest)

    def unterschluessel(self, pfad: str) -> list[str]:
        import winreg

        try:
            with self._oeffne(pfad) as k:
                anzahl = winreg.QueryInfoKey(k)[0]
                return [winreg.EnumKey(k, i) for i in range(anzahl)]
        except OSError:
            return []

    def wert(self, pfad: str, name: str) -> str | None:
        import winreg

        try:
            with self._oeffne(pfad) as k:
                return str(winreg.QueryValueEx(k, name)[0])
        except OSError:
            return None


def sw_jahre(reg: Registry) -> list[int]:
    jahre = [int(m.group(1)) for s in reg.unterschluessel(_BASIS) if (m := _JAHR_RE.match(s))]
    return sorted(jahre)


def _erstes(liste: str | None) -> str | None:
    if not liste:
        return None
    teil = liste.split(";")[0].strip()
    return teil or None


def _suche(ordner: str | None, muster: str) -> Path | None:
    if not ordner or not Path(ordner).is_dir():
        return None
    treffer = sorted(Path(ordner).glob(muster))
    return treffer[0] if treffer else None


def erkenne(reg: Registry, jahr: int | None = None) -> Rechner:
    jahre = sw_jahre(reg)
    if not jahre:
        raise KonfigFehler("Kein SOLIDWORKS in der Registry gefunden (HKLM\\SOFTWARE\\SolidWorks).")
    jahr = jahr or jahre[-1]
    if jahr not in jahre:
        raise KonfigFehler(f"SOLIDWORKS {jahr} nicht installiert. Gefunden: {jahre}")
    basis = f"SOLIDWORKS {jahr}"
    ordner = reg.wert(rf"{_BASIS}\{basis}\Setup", "SolidWorks Folder")
    if not ordner:
        raise KonfigFehler(f"Installationsordner von {basis} nicht gefunden.")
    vorlagen_schl = rf"HKCU\Software\SolidWorks\{basis}\Document Templates"
    ext_schl = rf"HKCU\Software\SolidWorks\{basis}\ExtReferences"
    vorlagen_ordner = _erstes(reg.wert(ext_schl, "Document Template Folders"))
    teil = reg.wert(vorlagen_schl, "Default Part Template")
    baugruppe = reg.wert(vorlagen_schl, "Default Assembly Template")
    teil_pfad = Path(teil) if teil else _suche(vorlagen_ordner, "*.prtdot")
    if teil_pfad is None:
        raise KonfigFehler(f"Keine Teilevorlage für {basis} gefunden.")
    baugruppe_pfad = Path(baugruppe) if baugruppe else _suche(vorlagen_ordner, "*.asmdot")
    mat = _erstes(reg.wert(ext_schl, "Material Database Folders"))
    return Rechner(
        sw_jahr=jahr,
        installationsordner=Path(ordner.rstrip("\\")),
        vorlage_teil=teil_pfad,
        vorlage_baugruppe=baugruppe_pfad,
        materialdatenbank=Path(mat) if mat else None,
        arbeitsordner=swki_home() / "arbeit",
    )


def _init(args) -> dict:
    pfad = rechner_pfad()
    if pfad.exists() and not args.neu:
        return {"unveraendert": True, "pfad": str(pfad), **rechner_als_dict(lade_rechner(pfad))}
    r = erkenne(WinRegistry(), args.jahr)
    schreibe_rechner(r, pfad)
    r.arbeitsordner.mkdir(parents=True, exist_ok=True)
    return {"unveraendert": False, "pfad": str(pfad), **rechner_als_dict(r)}


def _zeigen(args) -> dict:
    return rechner_als_dict(lade_rechner())


def einrichten(subparsers) -> None:
    gruppe = subparsers.add_parser("rechner").add_subparsers(dest="unterbefehl", required=True)
    p = gruppe.add_parser("init")
    p.add_argument("--jahr", type=int)
    p.add_argument("--neu", action="store_true", help="vorhandene rechner.yaml überschreiben")
    p.set_defaults(func=_init)
    gruppe.add_parser("zeigen").set_defaults(func=_zeigen)
```

In `swki/cli.py` `_befehlsgruppen` ersetzen:

```python
def _befehlsgruppen() -> list:
    from swki import rechner

    return [rechner]
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle Tests grün (Task 1–3).

- [ ] **Step 5: Real ausführen**

Run: `.venv\Scripts\python.exe -m swki rechner init`
Expected: JSON mit `"sw_jahr": 2025`, `vorlage_teil` = `…\templates\Teil.prtdot`, `vorlage_baugruppe` = `…\Baugruppe.ASMDOT`; Datei `config/rechner.yaml` existiert, `git status` zeigt sie **nicht** (gitignored).

- [ ] **Step 6: Commit**

```powershell
git add swki/rechner.py swki/cli.py tests/test_rechner.py
git commit -m "swki: SolidWorks-Erkennung und rechner init/zeigen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Verbindung zu SolidWorks

**Files:**
- Create: `swki/verbindung.py`, `tests/test_verbindung.py`, `tests/live/__init__.py`, `tests/live/test_live_verbindung.py`

**Interfaces:**
- Consumes: `SwkiFehler`
- Produces:
  - `jahr_aus_revision(revision: str) -> int` (`"33.2.0"` → 2025)
  - `mm(x: float) -> float` (mm→m), `in_mm(x: float) -> float` (m→mm), `in_mm3(x: float) -> float` (m³→mm³), `grad(x: float) -> float` (Grad→Rad)
  - `wert(x)` – ruft `x()` auf, wenn aufrufbar, sonst `x` (pywin32 liefert je nach Binding Methode oder Wert)
  - `callout_leer()` – `VARIANT(VT_DISPATCH, None)`
  - `byref_long(start: int = 0)` – `VARIANT(VT_BYREF | VT_I4, start)`
  - `class SolidWorksNichtGestartet(SwkiFehler)`, `class FalscheVersion(SwkiFehler)`
  - `verbinde(jahr: int)` – COM-Objekt der laufenden SolidWorks-Instanz

- [ ] **Step 1: Failing tests** – `tests/test_verbindung.py`

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
```

`tests/live/test_live_verbindung.py`:

```python
import pytest

from swki.konfig import lade_rechner
from swki.verbindung import jahr_aus_revision, verbinde, wert

pytestmark = pytest.mark.sw


def test_verbinde_mit_laufendem_solidworks():
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    assert jahr_aus_revision(wert(app.RevisionNumber)) == r.sw_jahr
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_verbindung.py -v`
Expected: FAIL (`ModuleNotFoundError: swki.verbindung`).

- [ ] **Step 3: Implementierung** – `swki/verbindung.py`

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
    return x() if callable(x) else x


def callout_leer():
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)


def byref_long(start: int = 0):
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, start)


def verbinde(jahr: int):
    """Hängt sich an ein laufendes SolidWorks. Startet SolidWorks nicht selbst."""
    import pythoncom
    import win32com.client

    major = jahr - _REVISION_BASIS
    app = None
    for progid in (f"SldWorks.Application.{major}", "SldWorks.Application"):
        try:
            app = win32com.client.GetActiveObject(progid)
            break
        except pythoncom.com_error:
            continue
    if app is None:
        raise SolidWorksNichtGestartet(f"SOLIDWORKS {jahr} läuft nicht. Bitte zuerst starten.")
    ist = jahr_aus_revision(wert(app.RevisionNumber))
    if ist != jahr:
        raise FalscheVersion(f"Laufendes SOLIDWORKS ist {ist}, erwartet {jahr} (config/rechner.yaml).")
    return app
```

`tests/live/__init__.py`: leere Datei.

- [ ] **Step 4: Unit-Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_verbindung.py -v`
Expected: 3 passed.

- [ ] **Step 5: Live-Test (SolidWorks 2025 geöffnet)**

Run: `.venv\Scripts\python.exe -m pytest -m sw tests/live/test_live_verbindung.py -v`
Expected: 1 passed. Falls `SolidWorksNichtGestartet`: SolidWorks starten, wiederholen. Falls ein anderer Fehler (z. B. `RevisionNumber` liefert kein String): Fehlermeldung in `docs/stufe0/ergebnisse.md` notieren (Datei in Task 15 angelegt; bis dahin im Task-Bericht) und `wert()`/`verbinde()` minimal anpassen.

- [ ] **Step 6: Commit**

```powershell
git add swki/verbindung.py tests/test_verbindung.py tests/live
git commit -m "swki: Verbindung zu laufendem SolidWorks und Einheitenhilfen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Einrichtungsskript und MCP-Server (gepinnt)

**Files:**
- Create: `setup/einrichten.ps1`, `.mcp.json`

**Interfaces:**
- Consumes: `python -m swki rechner init|zeigen`
- Produces: Benutzer-Umgebungsvariable `SWKI_SW_YEAR`; MCP-Server unter `%USERPROFILE%\.swki\SolidworksMCP-python` (venv unter `.venv`); `.mcp.json` mit Servername `solidworks-mcp`. Parameter `-Jahr <int>`, `-OhneMcp`, `-OhneApi` (Letzteres wird in Task 12 benutzt).

- [ ] **Step 1: `setup/einrichten.ps1` schreiben**

```powershell
# Richtet SolidWorks-KI auf diesem Rechner ein. Idempotent: mehrfach ausführbar.
# Aufruf: powershell -ExecutionPolicy Bypass -File setup\einrichten.ps1 [-Jahr 2025] [-OhneMcp] [-OhneApi]
param(
    [int]$Jahr = 0,
    [switch]$OhneMcp,
    [switch]$OhneApi
)
$ErrorActionPreference = "Stop"
$Projekt = Split-Path -Parent $PSScriptRoot
$SwkiHome = Join-Path $env:USERPROFILE ".swki"
$McpRepo = "https://github.com/andrewbartels1/SolidworksMCP-python.git"
$McpCommit = "600624fc93dad959600366bd0f3d281e4eeeacf5"

function Pruefe([string]$Schritt) {
    if ($LASTEXITCODE -ne 0) { throw "Fehlgeschlagen: $Schritt (Exit-Code $LASTEXITCODE)" }
}

function Finde-Python {
    foreach ($kandidat in @("python", "py")) {
        $cmd = Get-Command $kandidat -ErrorAction SilentlyContinue
        if ($cmd) {
            $version = & $cmd.Source -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
            $teile = $version.Split(".")
            if ([int]$teile[0] -eq 3 -and [int]$teile[1] -ge 13) { return $cmd.Source }
        }
    }
    throw "Python >= 3.13 nicht gefunden."
}

Write-Host "== 1/5 Python-Umgebung des Projekts"
$Python = Finde-Python
$VenvPy = Join-Path $Projekt ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) { & $Python -m venv (Join-Path $Projekt ".venv"); Pruefe "venv anlegen" }
& $VenvPy -m pip install --quiet -e "$Projekt[dev]"; Pruefe "pip install swki"

Write-Host "== 2/5 Rechnerkonfiguration"
New-Item -ItemType Directory -Force -Path $SwkiHome | Out-Null
$initArgs = @("-m", "swki", "rechner", "init")
if ($Jahr -gt 0) { $initArgs += @("--jahr", "$Jahr") }
& $VenvPy @initArgs; Pruefe "swki rechner init"
$Rechner = (& $VenvPy -m swki rechner zeigen) -join "`n" | ConvertFrom-Json
Pruefe "swki rechner zeigen"

Write-Host "== 3/5 Umgebungsvariable SWKI_SW_YEAR = $($Rechner.sw_jahr)"
[Environment]::SetEnvironmentVariable("SWKI_SW_YEAR", "$($Rechner.sw_jahr)", "User")
$env:SWKI_SW_YEAR = "$($Rechner.sw_jahr)"

if (-not $OhneMcp) {
    Write-Host "== 4/5 MCP-Server SolidworksMCP-python @ $McpCommit"
    $McpDir = Join-Path $SwkiHome "SolidworksMCP-python"
    if (-not (Test-Path (Join-Path $McpDir ".git"))) { git clone --quiet $McpRepo $McpDir; Pruefe "git clone" }
    git -C $McpDir fetch --quiet origin; Pruefe "git fetch"
    git -C $McpDir checkout --quiet $McpCommit; Pruefe "git checkout"
    $McpPy = Join-Path $McpDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $McpPy)) { & $Python -m venv (Join-Path $McpDir ".venv"); Pruefe "MCP-venv anlegen" }
    & $McpPy -m pip install --quiet -e $McpDir; Pruefe "pip install MCP-Server (ohne Extras)"
}

if (-not $OhneApi) {
    Write-Host "== 5/5 API-Nachschlagewerk"
    Write-Host "   (folgt in Task 12)"
}

Write-Host "Fertig. Claude Code neu starten, damit SWKI_SW_YEAR wirkt."
```

- [ ] **Step 2: `.mcp.json` schreiben**

```json
{
  "mcpServers": {
    "solidworks-mcp": {
      "command": "${USERPROFILE}\\.swki\\SolidworksMCP-python\\.venv\\Scripts\\python.exe",
      "args": [
        "${USERPROFILE}\\.swki\\SolidworksMCP-python\\src\\utils\\start_local_server_claude.py",
        "--real",
        "--year",
        "${SWKI_SW_YEAR}"
      ],
      "env": {
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "GH_TOKEN": ""
      }
    }
  }
}
```

- [ ] **Step 3: Nutzer um Freigabe für Downloads bitten**

Vor der ersten Ausführung den Nutzer fragen: „Das Skript klont SolidworksMCP-python von GitHub (Commit `600624f`) nach `%USERPROFILE%\.swki\` und lädt die Abhängigkeiten von PyPI. Einverstanden?“ Erst nach Ja weiter.

- [ ] **Step 4: Skript ausführen (zweimal, Idempotenz)**

Run: `powershell -ExecutionPolicy Bypass -File setup\einrichten.ps1`
Expected: endet mit „Fertig.“; `%USERPROFILE%\.swki\SolidworksMCP-python\.venv\Scripts\python.exe` existiert; `git -C $env:USERPROFILE\.swki\SolidworksMCP-python rev-parse HEAD` = `600624fc93dad959600366bd0f3d281e4eeeacf5`.
Zweiter Lauf: ebenfalls „Fertig.“, `rechner init` meldet `"unveraendert": true`.

- [ ] **Step 5: Prüfen, dass keine Extras installiert sind**

Run: `& "$env:USERPROFILE\.swki\SolidworksMCP-python\.venv\Scripts\python.exe" -m pip list`
Expected: keine Pakete `openai`, `anthropic`, `gradio`, `fastapi`, `uvicorn` aus den Extras `[ui,rag,vision]` (Kernabhängigkeiten wie `mcp`, `pywin32`, `pydantic`, `httpx2` sind ok). Abweichungen im Task-Bericht nennen.

- [ ] **Step 6: Commit**

```powershell
git add setup/einrichten.ps1 .mcp.json
git commit -m "setup: Einrichtungsskript und MCP-Einbindung (gepinnt)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: MCP auf Lese-Tools beschränken

**Files:**
- Create: `setup/mcp_tools_auflisten.py`, `setup/mcp_sperren.py`, `config/mcp-tools-alle.json` (generiert), `config/mcp-lesetools.txt`, `.claude/settings.json`, `tests/test_mcp_sperren.py`

**Interfaces:**
- Produces (`setup/mcp_sperren.py`):
  - `PRAEFIX = "mcp__solidworks-mcp__"`
  - `PFLICHT_GESPERRT = {"execute_macro", "batch_execute_macros", "pack_and_go_assembly", "batch_file_operations", "execute_workflow", "batch_process_files"}`
  - `sperrliste(alle: list[str], erlaubt: list[str]) -> list[str]` – wirft `ValueError`, wenn `erlaubt` unbekannte Namen oder Pflicht-gesperrte enthält
  - `aktualisiere_settings(settings: dict, deny: list[str]) -> dict` – ersetzt nur Einträge mit `PRAEFIX`, andere `deny`/`allow`/`ask` bleiben

- [ ] **Step 1: Failing tests** – `tests/test_mcp_sperren.py`

```python
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "mcp_sperren", Path(__file__).resolve().parent.parent / "setup" / "mcp_sperren.py"
)
mcp_sperren = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcp_sperren)


def test_sperrliste_alles_ausser_erlaubt():
    alle = ["list_features", "get_mass_properties", "create_extrusion", "execute_macro"]
    deny = mcp_sperren.sperrliste(alle, ["list_features", "get_mass_properties"])
    assert deny == ["mcp__solidworks-mcp__create_extrusion", "mcp__solidworks-mcp__execute_macro"]


def test_unbekanntes_erlaubtes_tool():
    with pytest.raises(ValueError, match="gibtsnicht"):
        mcp_sperren.sperrliste(["a"], ["gibtsnicht"])


def test_pflichtsperre_nicht_erlaubbar():
    with pytest.raises(ValueError, match="execute_macro"):
        mcp_sperren.sperrliste(["execute_macro"], ["execute_macro"])


def test_settings_behaelt_fremde_regeln():
    settings = {"permissions": {"deny": ["Bash(rm:*)", "mcp__solidworks-mcp__alt"], "ask": ["Bash(git push:*)"]}}
    neu = mcp_sperren.aktualisiere_settings(settings, ["mcp__solidworks-mcp__x"])
    assert neu["permissions"]["deny"] == ["Bash(rm:*)", "mcp__solidworks-mcp__x"]
    assert neu["permissions"]["ask"] == ["Bash(git push:*)"]
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_mcp_sperren.py -v`
Expected: FAIL (Datei `setup/mcp_sperren.py` fehlt).

- [ ] **Step 3: `setup/mcp_sperren.py` implementieren**

```python
"""Erzeugt permissions.deny für alle nicht-lesenden Tools von solidworks-mcp.

Aufruf: .venv\\Scripts\\python.exe setup\\mcp_sperren.py
Liest config/mcp-tools-alle.json und config/mcp-lesetools.txt, schreibt .claude/settings.json.
"""

import json
from pathlib import Path

PRAEFIX = "mcp__solidworks-mcp__"
PFLICHT_GESPERRT = {
    "execute_macro", "batch_execute_macros", "pack_and_go_assembly",
    "batch_file_operations", "execute_workflow", "batch_process_files",
}
PROJEKT = Path(__file__).resolve().parent.parent


def sperrliste(alle: list[str], erlaubt: list[str]) -> list[str]:
    unbekannt = sorted(set(erlaubt) - set(alle))
    if unbekannt:
        raise ValueError(f"Unbekannte Tools in mcp-lesetools.txt: {unbekannt}")
    verboten = sorted(set(erlaubt) & PFLICHT_GESPERRT)
    if verboten:
        raise ValueError(f"Diese Tools müssen gesperrt bleiben: {verboten}")
    return sorted(PRAEFIX + t for t in alle if t not in set(erlaubt))


def aktualisiere_settings(settings: dict, deny: list[str]) -> dict:
    perms = settings.setdefault("permissions", {})
    fremd = [r for r in perms.get("deny", []) if not r.startswith(PRAEFIX)]
    perms["deny"] = fremd + deny
    return settings


def main() -> None:
    alle = json.loads((PROJEKT / "config" / "mcp-tools-alle.json").read_text(encoding="utf-8"))
    erlaubt = [
        z.strip() for z in (PROJEKT / "config" / "mcp-lesetools.txt").read_text(encoding="utf-8").splitlines()
        if z.strip() and not z.startswith("#")
    ]
    pfad = PROJEKT / ".claude" / "settings.json"
    settings = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}
    deny = sperrliste(alle, erlaubt)
    pfad.parent.mkdir(exist_ok=True)
    pfad.write_text(json.dumps(aktualisiere_settings(settings, deny), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"erlaubt": len(erlaubt), "gesperrt": len(deny)}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_mcp_sperren.py -v`
Expected: 4 passed.

- [ ] **Step 5: `setup/mcp_tools_auflisten.py` schreiben** (läuft mit der Python-Umgebung des MCP-Servers, Mock-Modus, ohne SolidWorks)

```python
"""Listet alle Tool-Namen von solidworks-mcp (Mock-Modus, ohne SolidWorks).

Aufruf:
  & "$env:USERPROFILE\\.swki\\SolidworksMCP-python\\.venv\\Scripts\\python.exe" setup\\mcp_tools_auflisten.py
Schreibt config/mcp-tools-alle.json.
"""

import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJEKT = Path(__file__).resolve().parent.parent
MCP_DIR = Path(os.environ["USERPROFILE"]) / ".swki" / "SolidworksMCP-python"


async def liste() -> list[str]:
    params = StdioServerParameters(
        command=str(MCP_DIR / ".venv" / "Scripts" / "python.exe"),
        args=[str(MCP_DIR / "src" / "utils" / "start_local_server_claude.py")],  # ohne --real = Mock
        env={**os.environ, "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": "", "GH_TOKEN": ""},
    )
    async with stdio_client(params) as (lesen, schreiben):
        async with ClientSession(lesen, schreiben) as sitzung:
            await sitzung.initialize()
            antwort = await sitzung.list_tools()
            return sorted(t.name for t in antwort.tools)


if __name__ == "__main__":
    namen = asyncio.run(liste())
    ziel = PROJEKT / "config" / "mcp-tools-alle.json"
    ziel.write_text(json.dumps(namen, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"anzahl": len(namen), "datei": str(ziel)}))
```

Run: `& "$env:USERPROFILE\.swki\SolidworksMCP-python\.venv\Scripts\python.exe" setup\mcp_tools_auflisten.py`
Expected: `{"anzahl": <ca. 130>, ...}`. Falls die `mcp`-Client-API der installierten Version abweicht (ImportError/AttributeError): Rückfall – Tool-Namen aus dem Quellcode lesen:

```powershell
Get-ChildItem "$env:USERPROFILE\.swki\SolidworksMCP-python\src" -Recurse -Filter *.py |
  Select-String -Pattern '@mcp\.tool' -Context 0,2 |
  ForEach-Object { if ($_.Context.PostContext -join "`n" -match 'def\s+(\w+)') { $Matches[1] } } |
  Sort-Object -Unique | ConvertTo-Json | Set-Content -Encoding utf8 config\mcp-tools-alle.json
```

und im Task-Bericht vermerken, welcher Weg genutzt wurde.

- [ ] **Step 6: `config/mcp-lesetools.txt` anlegen**

Aus `config/mcp-tools-alle.json` genau die Tools übernehmen, die **nichts am Modell oder im Dateisystem ändern** außer dem Schreiben eines Bildes: Namen, die mit `get_`, `list_`, `check_`, `analyze_`, `measure_` beginnen, sowie Screenshot-/Bild-Export (`export_image` o. ä.). Im Zweifel ein Tool **nicht** aufnehmen und im Task-Bericht nennen. Format:

```
# Lesende Tools von solidworks-mcp (Commit 600624f). Alle anderen sind gesperrt.
# Eine Zeile je Tool. Erzeugt/geprüft am 2026-09-26.
<tool_name_1>
<tool_name_2>
```

(Die Platzhalter `<tool_name_n>` sind durch die tatsächlichen Namen aus Schritt 5 zu ersetzen; die Liste enthält erwartungsgemäß 8–20 Einträge, darunter Feature-Baum, Masseeigenschaften, Modellinfo und Bild-Export.)

- [ ] **Step 7: `.claude/settings.json` erzeugen**

Zuerst die Grunddatei anlegen:

```json
{
  "permissions": {
    "allow": [
      "Bash(.venv/Scripts/python.exe -m swki:*)",
      "Bash(.venv/Scripts/python.exe -m pytest:*)",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)"
    ],
    "ask": [
      "Bash(git push:*)"
    ],
    "deny": []
  }
}
```

Dann: `.venv\Scripts\python.exe setup\mcp_sperren.py`
Expected: `{"erlaubt": <n>, "gesperrt": <alle-n>}`; `.claude/settings.json` enthält in `deny` u. a. `mcp__solidworks-mcp__execute_macro` und `mcp__solidworks-mcp__pack_and_go_assembly`.

- [ ] **Step 8: Wirksamkeit prüfen (Nutzer)**

Den Nutzer bitten, Claude Code in diesem Projekt neu zu starten (damit `.mcp.json`, `SWKI_SW_YEAR` und die Sperren greifen), SolidWorks vorher zu öffnen und die Freigabe des Projekt-MCP-Servers `solidworks-mcp` zu bestätigen. In der neuen Sitzung prüfen:
- Server `solidworks-mcp` ist verbunden.
- Sichtbar sind nur die Tools aus `mcp-lesetools.txt` (gesperrte Tools erscheinen nicht bzw. werden abgewiesen).
- Ein lesender Aufruf (z. B. Modellinfo bei geöffnetem Testteil) funktioniert.
Ergebnis im Task-Bericht und später in `docs/stufe0/ergebnisse.md` festhalten.

- [ ] **Step 9: Commit**

```powershell
git add setup/mcp_tools_auflisten.py setup/mcp_sperren.py config/mcp-tools-alle.json config/mcp-lesetools.txt .claude/settings.json tests/test_mcp_sperren.py
git commit -m "setup: solidworks-mcp auf lesende Tools beschränkt" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Privates GitHub-Repo

**Files:** keine

- [x] **Step 1: Repo angelegt** – erledigt in der Planungssitzung: privates Repo `sebXL/SolidWorks-KI`, Remote `origin`, Branch `main`.

- [ ] **Step 2: Stand pushen (mit Rückfrage)**

Nach Task 6 den Nutzer fragen, ob der Stand gepusht werden soll; bei Ja:

```powershell
git push origin main
```

Expected: `git status` meldet „up to date with 'origin/main'“.

---

### Task 8: Typbibliothek lesen

**Files:**
- Create: `swki/api/__init__.py`, `swki/api/typbib.py`, `tests/api/__init__.py`, `tests/api/test_typbib.py`

**Interfaces:**
- Produces:
  - `@dataclass class Parameter: name: str; aus: bool; optional: bool`
  - `@dataclass class Member: interface: str; name: str; art: str; parameter: list[Parameter]` – `art` ∈ `{"methode", "property_get", "property_put", "property_putref", "property"}`
  - `@dataclass class EnumWert: enum: str; name: str; wert: int`
  - `lese_typbibliothek(pfad: Path) -> tuple[list[Member], list[EnumWert]]`

- [ ] **Step 1: Failing tests** – `tests/api/test_typbib.py`

`stdole2.tlb` gehört zu Windows und ist ein stabiles Testobjekt.

```python
from pathlib import Path

import pytest

from swki.api.typbib import lese_typbibliothek

STDOLE = Path(r"C:\Windows\System32\stdole2.tlb")
pytestmark = pytest.mark.skipif(not STDOLE.exists(), reason="stdole2.tlb fehlt")


@pytest.fixture(scope="module")
def stdole():
    return lese_typbibliothek(STDOLE)


def test_enum_werte(stdole):
    _, enums = stdole
    werte = {(e.enum, e.name): e.wert for e in enums}
    assert werte[("OLE_TRISTATE", "Unchecked")] == 0
    assert werte[("OLE_TRISTATE", "Checked")] == 1
    assert werte[("OLE_TRISTATE", "Gray")] == 2


def test_dispatch_methode_mit_parameter(stdole):
    members, _ = stdole
    m = next(m for m in members if m.interface == "FontEvents" and m.name == "FontChanged")
    assert m.art == "methode"
    assert [p.name for p in m.parameter] == ["PropertyName"]


def test_dispinterface_property(stdole):
    members, _ = stdole
    assert any(m.interface == "Font" and m.name == "Name" for m in members)


def test_idispatch_methoden_ausgefiltert(stdole):
    members, _ = stdole
    assert not any(m.name in ("QueryInterface", "Invoke") for m in members)
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/api/test_typbib.py -v`
Expected: FAIL (`ModuleNotFoundError: swki.api`).

- [ ] **Step 3: Implementierung** – `swki/api/typbib.py` (`swki/api/__init__.py` und `tests/api/__init__.py` leer)

```python
"""Liest Interfaces, Member, Parameter und Enums aus einer COM-Typbibliothek (.tlb)."""

from dataclasses import dataclass, field
from pathlib import Path

# Stabile COM-Konstanten (oaidl.h)
TKIND_ENUM, TKIND_INTERFACE, TKIND_DISPATCH = 0, 3, 4
INVOKE_ART = {1: "methode", 2: "property_get", 4: "property_put", 8: "property_putref"}
PARAMFLAG_FOUT, PARAMFLAG_FRETVAL, PARAMFLAG_FOPT = 0x2, 0x8, 0x10
_BASIS_METHODEN = {"QueryInterface", "AddRef", "Release", "GetTypeInfoCount", "GetTypeInfo", "GetIDsOfNames", "Invoke"}


@dataclass
class Parameter:
    name: str
    aus: bool
    optional: bool


@dataclass
class Member:
    interface: str
    name: str
    art: str
    parameter: list[Parameter] = field(default_factory=list)


@dataclass
class EnumWert:
    enum: str
    name: str
    wert: int


def _parameter(ti, fd) -> list[Parameter]:
    namen = list(ti.GetNames(fd.memid))[1:]
    ergebnis = []
    for i, arg in enumerate(fd.args):
        flags = arg[1]
        if flags & PARAMFLAG_FRETVAL:
            continue
        name = namen[i] if i < len(namen) else ("Wert" if i == len(fd.args) - 1 else f"p{i + 1}")
        ergebnis.append(Parameter(name, bool(flags & PARAMFLAG_FOUT), bool(flags & PARAMFLAG_FOPT)))
    return ergebnis


def lese_typbibliothek(pfad: Path) -> tuple[list[Member], list[EnumWert]]:
    import pythoncom

    tlb = pythoncom.LoadTypeLib(str(pfad))
    members: list[Member] = []
    enums: list[EnumWert] = []
    for i in range(tlb.GetTypeInfoCount()):
        ti = tlb.GetTypeInfo(i)
        attr = ti.GetTypeAttr()
        typname = tlb.GetDocumentation(i)[0]
        if attr.typekind == TKIND_ENUM:
            for k in range(attr.cVars):
                vd = ti.GetVarDesc(k)
                enums.append(EnumWert(typname, ti.GetNames(vd.memid)[0], int(vd.value)))
        elif attr.typekind in (TKIND_INTERFACE, TKIND_DISPATCH):
            for j in range(attr.cFuncs):
                fd = ti.GetFuncDesc(j)
                name = ti.GetNames(fd.memid)[0]
                if name in _BASIS_METHODEN:
                    continue
                members.append(Member(typname, name, INVOKE_ART.get(fd.invkind, "methode"), _parameter(ti, fd)))
            if attr.typekind == TKIND_DISPATCH:
                for k in range(attr.cVars):
                    vd = ti.GetVarDesc(k)
                    members.append(Member(typname, ti.GetNames(vd.memid)[0], "property"))
    return members, enums
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/api/test_typbib.py -v`
Expected: 4 passed. Falls `attr.typekind`/`cFuncs` in der installierten pywin32-Version als Tupel statt Attribute kommen: auf Indexzugriff laut pywin32-Doku `PyTYPEATTR` umstellen und im Task-Bericht vermerken.

- [ ] **Step 5: Commit**

```powershell
git add swki/api tests/api
git commit -m "api: Typbibliothek lesen (Member, Parameter, Enums)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: CHM-Hilfe entpacken und lesen

**Files:**
- Create: `swki/api/chm.py`, `tests/api/test_chm.py`

**Interfaces:**
- Produces:
  - `CHM_DATEIEN = ["sldworksapi.chm", "swconst.chm", "sldworksapiprogguide.chm", "toolboxapi.chm"]`
  - `@dataclass class Seite: datei: str; titel: str; interface: str | None; member: str | None; art: str | None; seit: int | None; text: str`
  - `lese_seite(pfad: Path) -> Seite`
  - `lese_ordner(ordner: Path) -> list[Seite]`
  - `entpacke(chm: Path, ziel: Path, neu: bool = False) -> Path`

- [ ] **Step 1: Echte Seitenstruktur ansehen (nur lesen, nichts committen)**

```powershell
New-Item -ItemType Directory -Force "$env:TEMP\swki-chm-probe" | Out-Null
Start-Process hh.exe -ArgumentList "-decompile", "$env:TEMP\swki-chm-probe", "`"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\sldworksapi.chm`"" -Wait
Get-ChildItem "$env:TEMP\swki-chm-probe" -Recurse -Filter "*FeatureExtrusion3*"
```

Eine gefundene Datei öffnen und notieren: Aufbau des `<title>` (erwartet: `FeatureExtrusion3 Method (IFeatureManager)`) und wie der Abschnitt „Availability“ formuliert ist (erwartet: `SOLIDWORKS 20xx …, Revision Number …`). Weicht es ab, die Regex in Schritt 3 **und** die synthetische Fixture in Schritt 2 entsprechend anpassen (Fixture bleibt selbst formuliert).

- [ ] **Step 2: Failing tests** – `tests/api/test_chm.py`

```python
from swki.api.chm import lese_ordner, lese_seite

SEITE = """<html><head><title>BeispielMethode Method (IBeispielManager)</title>
<script>var x = 1;</script></head><body>
<h1>BeispielMethode Method (IBeispielManager)</h1>
<p>Erzeugt ein Beispiel-Feature.</p>
<h4>Availability</h4><p>SOLIDWORKS 2014 FCS, Revision Number 22.0</p>
</body></html>"""

ENUM = """<html><head><title>swBeispiel_e Enumeration</title></head><body>
<p>Werte für Beispiele.</p></body></html>"""


def test_methode(tmp_path):
    p = tmp_path / "a.htm"
    p.write_text(SEITE, encoding="utf-8")
    s = lese_seite(p)
    assert (s.member, s.art, s.interface, s.seit) == ("BeispielMethode", "Method", "IBeispielManager", 2014)
    assert "Erzeugt ein Beispiel-Feature." in s.text
    assert "var x" not in s.text


def test_enum_ohne_interface(tmp_path):
    p = tmp_path / "e.html"
    p.write_text(ENUM, encoding="utf-8")
    s = lese_seite(p)
    assert (s.member, s.art, s.interface, s.seit) == ("swBeispiel_e", "Enumeration", None, None)


def test_cp1252(tmp_path):
    p = tmp_path / "c.htm"
    p.write_bytes(SEITE.replace("Erzeugt", "Größe").encode("cp1252"))
    assert "Größe" in lese_seite(p).text


def test_ordner_rekursiv(tmp_path):
    (tmp_path / "unter").mkdir()
    (tmp_path / "unter" / "a.htm").write_text(SEITE, encoding="utf-8")
    (tmp_path / "b.html").write_text(ENUM, encoding="utf-8")
    (tmp_path / "bild.gif").write_bytes(b"GIF")
    assert len(lese_ordner(tmp_path)) == 2
```

- [ ] **Step 3: Test fehlschlagen lassen, dann implementieren** – `swki/api/chm.py`

Run first: `.venv\Scripts\python.exe -m pytest tests/api/test_chm.py -v` → FAIL (`ModuleNotFoundError`).

```python
"""Entpackt die lokale SolidWorks-API-Hilfe (CHM) und liest die HTML-Seiten."""

import re
import subprocess
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

CHM_DATEIEN = ["sldworksapi.chm", "swconst.chm", "sldworksapiprogguide.chm", "toolboxapi.chm"]
_TITEL_RE = re.compile(
    r"^(?P<member>[\w]+)\s+(?P<art>Method|Property|Event|Enumeration|Interface)(?:\s+\((?P<iface>\w+)\))?"
)
_SEIT_RE = re.compile(r"SOLIDWORKS\s+(\d{4})", re.IGNORECASE)


@dataclass
class Seite:
    datei: str
    titel: str
    interface: str | None
    member: str | None
    art: str | None
    seit: int | None
    text: str


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.titel, self.teile, self._in_titel, self._ueberspringen = "", [], False, 0

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_titel = True
        elif tag in ("script", "style"):
            self._ueberspringen += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_titel = False
        elif tag in ("script", "style") and self._ueberspringen:
            self._ueberspringen -= 1

    def handle_data(self, data):
        if self._in_titel:
            self.titel += data
        elif not self._ueberspringen and data.strip():
            self.teile.append(data.strip())


def _dekodiere(roh: bytes) -> str:
    try:
        return roh.decode("utf-8")
    except UnicodeDecodeError:
        return roh.decode("cp1252", errors="replace")


def lese_seite(pfad: Path) -> Seite:
    p = _Text()
    p.feed(_dekodiere(pfad.read_bytes()))
    titel = " ".join(p.titel.split())
    text = " ".join(p.teile)
    m = _TITEL_RE.match(titel)
    seit = None
    pos = text.find("Availability")
    if pos >= 0 and (s := _SEIT_RE.search(text, pos, pos + 300)):
        seit = int(s.group(1))
    return Seite(
        datei=str(pfad),
        titel=titel,
        interface=m.group("iface") if m else None,
        member=m.group("member") if m else None,
        art=m.group("art") if m else None,
        seit=seit,
        text=text,
    )


def lese_ordner(ordner: Path) -> list[Seite]:
    return [lese_seite(p) for p in sorted(ordner.rglob("*")) if p.suffix.lower() in (".htm", ".html")]


def entpacke(chm: Path, ziel: Path, neu: bool = False) -> Path:
    if ziel.exists() and any(ziel.rglob("*.htm*")) and not neu:
        return ziel
    ziel.mkdir(parents=True, exist_ok=True)
    subprocess.run(["hh.exe", "-decompile", str(ziel), str(chm)], check=False, timeout=900)
    if not any(ziel.rglob("*.htm*")):
        raise RuntimeError(f"Entpacken fehlgeschlagen: {chm}")
    return ziel
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/api/test_chm.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add swki/api/chm.py tests/api/test_chm.py
git commit -m "api: CHM-Hilfe entpacken und Seiten lesen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: SQLite-Index

**Files:**
- Create: `swki/api/index.py`, `tests/api/test_index.py`

**Interfaces:**
- Consumes: `Member`, `Parameter`, `EnumWert` (Task 8), `Seite` (Task 9)
- Produces:
  - `baue(db: Path, members: list[Member], enums: list[EnumWert], seiten: list[Seite], jahr: int) -> dict` (Statistik `{"member": n, "enums": n, "seiten": n}`; ersetzt vorhandene Datei)
  - `methode(db: Path, qualifiziert: str) -> list[dict]` – alle Einträge zu `Interface.Member` (mehrere bei property_get/put); jeder: `{"interface", "name", "art", "parameter": [{"name","aus","optional"}], "anzahl_parameter", "seit", "text"}` (`text` max. 4000 Zeichen)
  - `enum(db: Path, name: str) -> list[dict]` – `[{"name", "wert"}]` nach Wert sortiert
  - `suche(db: Path, anfrage: str, limit: int = 10) -> list[dict]` – `[{"schluessel", "titel", "auszug"}]`
  - `seit_je_member(db: Path) -> dict[str, int]` – Membername → kleinstes bekanntes `seit`
  - `meta(db: Path) -> dict`

- [ ] **Step 1: Failing tests** – `tests/api/test_index.py`

```python
import pytest

from swki.api.chm import Seite
from swki.api.index import baue, enum, meta, methode, seit_je_member, suche
from swki.api.typbib import EnumWert, Member, Parameter


@pytest.fixture
def db(tmp_path):
    members = [
        Member("IFeatureManager", "FeatureExtrusion3", "methode", [Parameter(f"p{i}", False, False) for i in range(23)]),
        Member("IFeatureManager", "FeatureExtrusion4", "methode", [Parameter("Sd", False, False)]),
        Member("ISketch", "Name", "property_get"),
        Member("ISketch", "Name", "property_put", [Parameter("Wert", False, False)]),
    ]
    enums = [EnumWert("swEndConditions_e", "swEndCondThroughAll", 1), EnumWert("swEndConditions_e", "swEndCondBlind", 0)]
    seiten = [
        Seite("a.htm", "FeatureExtrusion3 Method (IFeatureManager)", "IFeatureManager", "FeatureExtrusion3",
              "Method", 2014, "Creates an extruded feature with blind end condition."),
        Seite("b.htm", "FeatureExtrusion4 Method (IFeatureManager)", "IFeatureManager", "FeatureExtrusion4",
              "Method", 2026, "Newer extrusion."),
        Seite("c.htm", "Programmieranleitung", None, None, None, None, "Allgemeiner Text über Makros."),
    ]
    pfad = tmp_path / "api.sqlite"
    stat = baue(pfad, members, enums, seiten, 2025)
    assert stat == {"member": 4, "enums": 2, "seiten": 3}
    return pfad


def test_methode(db):
    [m] = methode(db, "IFeatureManager.FeatureExtrusion3")
    assert m["anzahl_parameter"] == 23
    assert m["seit"] == 2014
    assert "extruded" in m["text"]


def test_property_get_und_put(db):
    assert {m["art"] for m in methode(db, "ISketch.Name")} == {"property_get", "property_put"}


def test_methode_unbekannt(db):
    assert methode(db, "IGibts.Nicht") == []


def test_enum_sortiert(db):
    assert enum(db, "swEndConditions_e") == [
        {"name": "swEndCondBlind", "wert": 0}, {"name": "swEndCondThroughAll", "wert": 1},
    ]


def test_suche_findet_text(db):
    treffer = suche(db, "extruded blind")
    assert treffer[0]["schluessel"] == "IFeatureManager.FeatureExtrusion3"


def test_suche_oder_rueckfall(db):
    assert suche(db, "makros gibtsnichtwort")[0]["titel"] == "Programmieranleitung"


def test_suche_sonderzeichen(db):
    suche(db, 'extrusion "blind" (AND) -')  # darf nicht werfen


def test_seit_je_member(db):
    s = seit_je_member(db)
    assert s["FeatureExtrusion3"] == 2014 and s["FeatureExtrusion4"] == 2026


def test_meta(db):
    assert meta(db)["jahr"] == "2025"
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/api/test_index.py -v`
Expected: FAIL (`ModuleNotFoundError: swki.api.index`).

- [ ] **Step 3: Implementierung** – `swki/api/index.py`

```python
"""SQLite-Index für die SolidWorks-API (Member, Enums, Hilfeseiten) mit FTS5-Volltextsuche."""

import json
import re
import sqlite3
from datetime import date
from pathlib import Path

from swki.api.chm import Seite
from swki.api.typbib import EnumWert, Member

_SCHEMA = """
CREATE TABLE member(interface TEXT, name TEXT, art TEXT, parameter TEXT, seit INTEGER, text TEXT,
                    PRIMARY KEY (interface, name, art));
CREATE TABLE enum(enum TEXT, name TEXT, wert INTEGER, PRIMARY KEY (enum, name));
CREATE VIRTUAL TABLE suchindex USING fts5(schluessel, titel, text);
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
"""


def _verbinde(db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


def baue(db: Path, members: list[Member], enums: list[EnumWert], seiten: list[Seite], jahr: int) -> dict:
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()
    zu_seite = {(s.interface, s.member): s for s in seiten if s.interface and s.member}
    with _verbinde(db) as con:
        con.executescript(_SCHEMA)
        for m in members:
            s = zu_seite.get((m.interface, m.name))
            params = json.dumps([p.__dict__ for p in m.parameter], ensure_ascii=False)
            con.execute(
                "INSERT OR REPLACE INTO member VALUES (?,?,?,?,?,?)",
                (m.interface, m.name, m.art, params, s.seit if s else None, s.text if s else ""),
            )
        con.executemany("INSERT OR REPLACE INTO enum VALUES (?,?,?)", [(e.enum, e.name, e.wert) for e in enums])
        for s in seiten:
            schluessel = f"{s.interface}.{s.member}" if s.interface and s.member else (s.member or s.datei)
            con.execute("INSERT INTO suchindex VALUES (?,?,?)", (schluessel, s.titel, s.text))
        con.executemany(
            "INSERT INTO meta VALUES (?,?)", [("jahr", str(jahr)), ("erstellt", date.today().isoformat())]
        )
    return {"member": len(members), "enums": len(enums), "seiten": len(seiten)}


def methode(db: Path, qualifiziert: str) -> list[dict]:
    interface, _, name = qualifiziert.partition(".")
    with _verbinde(db) as con:
        zeilen = con.execute(
            "SELECT * FROM member WHERE interface=? AND name=? ORDER BY art", (interface, name)
        ).fetchall()
    ergebnis = []
    for z in zeilen:
        params = json.loads(z["parameter"])
        ergebnis.append({
            "interface": z["interface"], "name": z["name"], "art": z["art"], "parameter": params,
            "anzahl_parameter": len(params), "seit": z["seit"], "text": (z["text"] or "")[:4000],
        })
    return ergebnis


def enum(db: Path, name: str) -> list[dict]:
    with _verbinde(db) as con:
        zeilen = con.execute("SELECT name, wert FROM enum WHERE enum=? ORDER BY wert, name", (name,)).fetchall()
    return [{"name": z["name"], "wert": z["wert"]} for z in zeilen]


def _fts(anfrage: str, verbinder: str) -> str:
    woerter = re.findall(r"\w+", anfrage)
    return f" {verbinder} ".join(f'"{w}"' for w in woerter)


def suche(db: Path, anfrage: str, limit: int = 10) -> list[dict]:
    with _verbinde(db) as con:
        for verbinder in ("AND", "OR"):
            ausdruck = _fts(anfrage, verbinder)
            if not ausdruck:
                return []
            zeilen = con.execute(
                "SELECT schluessel, titel, snippet(suchindex, 2, '[', ']', ' … ', 20) AS auszug "
                "FROM suchindex WHERE suchindex MATCH ? ORDER BY bm25(suchindex) LIMIT ?",
                (ausdruck, limit),
            ).fetchall()
            if zeilen:
                return [dict(z) for z in zeilen]
    return []


def seit_je_member(db: Path) -> dict[str, int]:
    with _verbinde(db) as con:
        zeilen = con.execute(
            "SELECT name, MIN(seit) AS seit FROM member WHERE seit IS NOT NULL GROUP BY name"
        ).fetchall()
    return {z["name"]: z["seit"] for z in zeilen}


def meta(db: Path) -> dict:
    with _verbinde(db) as con:
        return {z["k"]: z["v"] for z in con.execute("SELECT k, v FROM meta")}
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/api/test_index.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```powershell
git add swki/api/index.py tests/api/test_index.py
git commit -m "api: SQLite-Index mit Volltextsuche" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Code-Prüfung auf zu neue API-Aufrufe

**Files:**
- Create: `swki/api/codepruefung.py`, `tests/api/test_codepruefung.py`

**Interfaces:**
- Produces:
  - `finde_api_namen(quelltext: str) -> list[tuple[str, int]]` – (Attributname, Zeile) für Attributzugriffe, deren Name mit Großbuchstaben beginnt
  - `pruefe(pfade: list[Path], seit: dict[str, int], max_jahr: int) -> list[dict]` – `[{"datei", "zeile", "name", "seit"}]` für alle `seit > max_jahr`

- [ ] **Step 1: Failing tests** – `tests/api/test_codepruefung.py`

```python
from swki.api.codepruefung import finde_api_namen, pruefe

QUELLE = """
fm = model.FeatureManager
f = fm.FeatureExtrusion3(True)
g = fm.FeatureExtrusion4(True)
x = daten.lower()
"""


def test_finde_api_namen():
    namen = finde_api_namen(QUELLE)
    assert ("FeatureExtrusion4", 4) in namen
    assert ("FeatureManager", 2) in namen
    assert not any(n == "lower" for n, _ in namen)


def test_pruefe_meldet_zu_neue(tmp_path):
    datei = tmp_path / "handler.py"
    datei.write_text(QUELLE, encoding="utf-8")
    befunde = pruefe([datei], {"FeatureExtrusion3": 2014, "FeatureExtrusion4": 2026}, 2025)
    assert befunde == [{"datei": str(datei), "zeile": 4, "name": "FeatureExtrusion4", "seit": 2026}]


def test_pruefe_ordner_rekursiv(tmp_path):
    (tmp_path / "unter").mkdir()
    (tmp_path / "unter" / "a.py").write_text(QUELLE, encoding="utf-8")
    assert len(pruefe([tmp_path], {"FeatureExtrusion4": 2026}, 2025)) == 1
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/api/test_codepruefung.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementierung** – `swki/api/codepruefung.py`

```python
"""Findet SolidWorks-API-Aufrufe im Code, die erst nach max_jahr verfügbar sind."""

import ast
from pathlib import Path


def finde_api_namen(quelltext: str) -> list[tuple[str, int]]:
    return [
        (knoten.attr, knoten.lineno)
        for knoten in ast.walk(ast.parse(quelltext))
        if isinstance(knoten, ast.Attribute) and knoten.attr[:1].isupper()
    ]


def _dateien(pfade: list[Path]) -> list[Path]:
    ergebnis = []
    for p in pfade:
        ergebnis.extend(sorted(p.rglob("*.py")) if p.is_dir() else [p])
    return ergebnis


def pruefe(pfade: list[Path], seit: dict[str, int], max_jahr: int) -> list[dict]:
    befunde = []
    for datei in _dateien(pfade):
        for name, zeile in finde_api_namen(datei.read_text(encoding="utf-8")):
            jahr = seit.get(name)
            if jahr is not None and jahr > max_jahr:
                befunde.append({"datei": str(datei), "zeile": zeile, "name": name, "seit": jahr})
    return sorted(befunde, key=lambda b: (b["datei"], b["zeile"]))
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/api/test_codepruefung.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add swki/api/codepruefung.py tests/api/test_codepruefung.py
git commit -m "api: Prüfung auf API-Aufrufe jünger als SW 2025" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: `swki api …` und Index-Aufbau im Einrichtungsskript

**Files:**
- Create: `swki/api/bauen.py`, `tests/api/test_cli_api.py`, `tests/live/test_live_api.py`
- Modify: `swki/cli.py` (`_befehlsgruppen`), `setup/einrichten.ps1` (Schritt 5)

**Interfaces:**
- Consumes: `lade_rechner`, `lade_standard`, `swki_home`, `PROJEKT`, `entpacke`, `lese_ordner`, `CHM_DATEIEN`, `lese_typbibliothek`, `baue`, `methode`, `enum`, `suche`, `seit_je_member`, `meta`, `pruefe`
- Produces:
  - `api_db(jahr: int) -> Path` (= `swki_home()/"api"/str(jahr)/"api.sqlite"`)
  - `baue_index(r: Rechner, ziel: Path | None = None, neu: bool = False) -> dict`
  - Befehle: `swki api bauen [--neu]`, `swki api suche <text> [--limit N]`, `swki api methode <Interface.Member>`, `swki api enum <Name>`, `swki api pruefe-code [pfade…]` (Vorgabe: `swki/`), `swki api info`; alle mit optionalem `--db <pfad>`

- [ ] **Step 1: Failing tests** – `tests/api/test_cli_api.py`

```python
import json

import pytest

from swki.api.chm import Seite
from swki.api.index import baue
from swki.api.typbib import EnumWert, Member, Parameter
from swki.cli import main


@pytest.fixture
def db(tmp_path):
    pfad = tmp_path / "api.sqlite"
    baue(
        pfad,
        [Member("IFeatureManager", "FeatureExtrusion4", "methode", [Parameter("Sd", False, False)])],
        [EnumWert("swEndConditions_e", "swEndCondBlind", 0)],
        [Seite("a.htm", "FeatureExtrusion4 Method (IFeatureManager)", "IFeatureManager", "FeatureExtrusion4",
               "Method", 2026, "Creates an extrusion.")],
        2026,
    )
    return pfad


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_methode(capsys, db):
    code, daten = _lauf(capsys, "api", "methode", "IFeatureManager.FeatureExtrusion4", "--db", str(db))
    assert code == 0 and daten["treffer"][0]["seit"] == 2026


def test_methode_unbekannt_ist_fehler(capsys, db):
    code, daten = _lauf(capsys, "api", "methode", "IX.Y", "--db", str(db))
    assert code == 1 and "IX.Y" in daten["fehler"]


def test_enum(capsys, db):
    _, daten = _lauf(capsys, "api", "enum", "swEndConditions_e", "--db", str(db))
    assert daten["werte"] == [{"name": "swEndCondBlind", "wert": 0}]


def test_suche(capsys, db):
    _, daten = _lauf(capsys, "api", "suche", "extrusion", "--db", str(db))
    assert daten["treffer"][0]["schluessel"] == "IFeatureManager.FeatureExtrusion4"


def test_pruefe_code(capsys, db, tmp_path):
    code_datei = tmp_path / "h.py"
    code_datei.write_text("fm.FeatureExtrusion4(True)\n", encoding="utf-8")
    code, daten = _lauf(capsys, "api", "pruefe-code", str(code_datei), "--db", str(db))
    assert code == 1
    assert daten["befunde"][0]["name"] == "FeatureExtrusion4"


def test_fehlender_index(capsys, tmp_path):
    code, daten = _lauf(capsys, "api", "info", "--db", str(tmp_path / "fehlt.sqlite"))
    assert code == 1 and "swki api bauen" in daten["fehler"]
```

`tests/live/test_live_api.py`:

```python
import pytest

from swki.api.bauen import api_db
from swki.api.index import enum, methode
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw


@pytest.fixture(scope="module")
def db():
    pfad = api_db(lade_rechner().sw_jahr)
    if not pfad.exists():
        pytest.fail("Index fehlt – zuerst: python -m swki api bauen")
    return pfad


def test_feature_extrusion3_hat_23_parameter(db):
    [m] = methode(db, "IFeatureManager.FeatureExtrusion3")
    assert m["anzahl_parameter"] == 23
    assert m["seit"] is not None and m["seit"] <= 2025


def test_end_conditions(db):
    werte = {e["name"]: e["wert"] for e in enum(db, "swEndConditions_e")}
    assert werte["swEndCondBlind"] == 0
    assert werte["swEndCondThroughAll"] == 1
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/api/test_cli_api.py -v`
Expected: FAIL (Befehl `api` unbekannt → `SystemExit`/Exit-Code 2, JSON-Dekodierung schlägt fehl).

- [ ] **Step 3: Implementierung** – `swki/api/bauen.py`

```python
"""Baut den API-Index aus der lokalen SolidWorks-Installation; Befehle "swki api …"."""

from pathlib import Path

from swki.api.chm import CHM_DATEIEN, entpacke, lese_ordner
from swki.api.codepruefung import pruefe
from swki.api.index import baue, enum, meta, methode, seit_je_member, suche
from swki.api.typbib import lese_typbibliothek
from swki.cli import SwkiFehler
from swki.konfig import PROJEKT, Rechner, lade_rechner, lade_standard, swki_home

TYPBIBLIOTHEKEN = ["sldworks.tlb", "swconst.tlb"]


def api_db(jahr: int) -> Path:
    return swki_home() / "api" / str(jahr) / "api.sqlite"


def baue_index(r: Rechner, ziel: Path | None = None, neu: bool = False) -> dict:
    ziel = ziel or api_db(r.sw_jahr)
    seiten, fehlend = [], []
    for name in CHM_DATEIEN:
        chm = r.installationsordner / "api" / name
        if not chm.exists():
            fehlend.append(name)
            continue
        seiten.extend(lese_ordner(entpacke(chm, ziel.parent / "html" / chm.stem, neu)))
    members, enums = [], []
    for name in TYPBIBLIOTHEKEN:
        m, e = lese_typbibliothek(r.installationsordner / name)
        members += m
        enums += e
    statistik = baue(ziel, members, enums, seiten, r.sw_jahr)
    return {"db": str(ziel), "fehlende_chm": fehlend, **statistik}


def _db(args) -> Path:
    pfad = Path(args.db) if args.db else api_db(lade_rechner().sw_jahr)
    if not pfad.exists():
        raise SwkiFehler(f"API-Index {pfad} fehlt. Zuerst ausführen: python -m swki api bauen")
    return pfad


def _bauen(args) -> dict:
    return baue_index(lade_rechner(), Path(args.db) if args.db else None, args.neu)


def _suche(args) -> dict:
    return {"treffer": suche(_db(args), args.text, args.limit)}


def _methode(args) -> dict:
    treffer = methode(_db(args), args.name)
    if not treffer:
        raise SwkiFehler(f"{args.name} nicht im Index. Mit 'swki api suche' nach dem richtigen Namen suchen.")
    return {"treffer": treffer}


def _enum(args) -> dict:
    werte = enum(_db(args), args.name)
    if not werte:
        raise SwkiFehler(f"Enum {args.name} nicht im Index.")
    return {"enum": args.name, "werte": werte}


def _pruefe_code(args) -> dict:
    max_jahr = lade_standard()["api"]["max_jahr_compiler"]
    pfade = [Path(p) for p in args.pfade] or [PROJEKT / "swki"]
    befunde = pruefe(pfade, seit_je_member(_db(args)), max_jahr)
    if befunde:
        raise _Befunde(max_jahr, befunde)
    return {"max_jahr": max_jahr, "befunde": []}


class _Befunde(SwkiFehler):
    def __init__(self, max_jahr, befunde):
        super().__init__(f"{len(befunde)} API-Aufruf(e) jünger als SW {max_jahr}")
        self.daten = {"max_jahr": max_jahr, "befunde": befunde}


def _info(args) -> dict:
    return meta(_db(args))


def einrichten(subparsers) -> None:
    gruppe = subparsers.add_parser("api").add_subparsers(dest="unterbefehl", required=True)

    def neu(name, func):
        p = gruppe.add_parser(name)
        p.add_argument("--db")
        p.set_defaults(func=func)
        return p

    neu("bauen", _bauen).add_argument("--neu", action="store_true")
    p = neu("suche", _suche)
    p.add_argument("text")
    p.add_argument("--limit", type=int, default=10)
    neu("methode", _methode).add_argument("name", help="Interface.Member, z. B. IFeatureManager.FeatureExtrusion3")
    neu("enum", _enum).add_argument("name")
    neu("pruefe-code", _pruefe_code).add_argument("pfade", nargs="*")
    neu("info", _info)
```

In `swki/cli.py`: Fehlerausgabe um Zusatzdaten erweitern und Gruppe registrieren.

```python
def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 2)
    try:
        ausgabe(args.func(args))
        return 0
    except SwkiFehler as e:
        ausgabe({"fehler": str(e), **getattr(e, "daten", {})})
        return 1


def _befehlsgruppen() -> list:
    from swki import rechner
    from swki.api import bauen

    return [rechner, bauen]
```

In `setup/einrichten.ps1` den Block `if (-not $OhneApi) { … }` ersetzen durch:

```powershell
if (-not $OhneApi) {
    Write-Host "== 5/5 API-Nachschlagewerk (kann einige Minuten dauern)"
    & $VenvPy -m swki api bauen; Pruefe "swki api bauen"
}
```

- [ ] **Step 4: Unit-Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle Tests grün.

- [ ] **Step 5: Index real bauen und Live-Test**

Run: `.venv\Scripts\python.exe -m swki api bauen`
Expected: JSON mit `member` > 5000, `enums` > 5000, `seiten` > 10000, `fehlende_chm` = `[]`.
Dann: `.venv\Scripts\python.exe -m pytest -m sw tests/live/test_live_api.py -v` → 2 passed.
Dann: `.venv\Scripts\python.exe -m swki api methode IFeatureManager.FeatureExtrusion3` → 23 Parameter mit Namen (`Sd`, `Flip`, `Dir`, `T1`, `T2`, `D1`, `D2`, …, `FlipStartOffset`).
Falls `seit` überall `null` ist: die „Availability“-Formulierung aus Task 9 Schritt 1 prüfen und `_SEIT_RE` anpassen (inkl. Test).

- [ ] **Step 6: Commit**

```powershell
git add swki/api/bauen.py swki/cli.py setup/einrichten.ps1 tests/api/test_cli_api.py tests/live/test_live_api.py
git commit -m "api: Befehle swki api und Index-Aufbau beim Einrichten" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Gemeinsame Spike-Hilfen und Spikes S1–S4 (Teil)

Spikes sind Machbarkeitstests: Sie beantworten Fragen, ihr Code ist nicht Produktionscode. Jeder Spike schreibt `docs/stufe0/ergebnisse/<name>.json` mit `ok`, Messwerten und ggf. Fehler + Traceback. **Vor jedem API-Aufruf, dessen Signatur hier nicht schon durch Task 12 bestätigt ist, mit `swki api methode` nachschlagen** und Abweichungen im Ergebnis vermerken. SolidWorks 2025 muss geöffnet sein.

**Files:**
- Create: `spikes/__init__.py` (leer), `spikes/_gemeinsam.py`, `spikes/s1_verbinden.py`, `spikes/s2_ebenen.py`, `spikes/s3_skizze_extrusion.py`, `spikes/s4_masse_screenshot.py`

**Interfaces:**
- Consumes: `lade_rechner`, `PROJEKT`, `verbinde`, `mm`, `in_mm`, `in_mm3`, `wert`, `callout_leer`, `byref_long`, `api_db`, `methode`, `enum`
- Produces (`spikes/_gemeinsam.py`):
  - `ERGEBNISSE: Path`
  - `start() -> tuple[Rechner, app]`
  - `neues_teil(app, r) -> model`, `neue_baugruppe(app, r) -> model`
  - `standardebenen(model) -> list` (die ersten drei `RefPlane`-Features: Vorne, Oben, Rechts)
  - `letztes_feature(model)`
  - `kasten(model, ebene, breite, hoehe, tiefe, mitte=(0.0, 0.0)) -> feature` (mm)
  - `speichere(model, pfad: Path) -> int` (Fehlercode von `SaveAs3`)
  - `schliesse(app, model) -> None`
  - `lauf(name: str, fn) -> dict` (führt `fn()` aus, schreibt JSON, druckt es)

- [ ] **Step 1: `spikes/_gemeinsam.py`**

```python
"""Hilfen für Machbarkeitstests (Stufe 0). Kein Produktionscode."""

import json
import traceback
from pathlib import Path

from swki.konfig import PROJEKT, lade_rechner
from swki.verbindung import mm, verbinde, wert

ERGEBNISSE = PROJEKT / "docs" / "stufe0" / "ergebnisse"


def start():
    r = lade_rechner()
    return r, verbinde(r.sw_jahr)


def neues_teil(app, r):
    model = app.NewDocument(str(r.vorlage_teil), 0, 0, 0)
    if model is None:
        raise RuntimeError(f"NewDocument mit {r.vorlage_teil} fehlgeschlagen")
    return model


def neue_baugruppe(app, r):
    if r.vorlage_baugruppe is None:
        raise RuntimeError("Keine Baugruppenvorlage in config/rechner.yaml")
    model = app.NewDocument(str(r.vorlage_baugruppe), 0, 0, 0)
    if model is None:
        raise RuntimeError(f"NewDocument mit {r.vorlage_baugruppe} fehlgeschlagen")
    return model


def standardebenen(model) -> list:
    ebenen = []
    f = model.FirstFeature()
    while f is not None and len(ebenen) < 3:
        if wert(f.GetTypeName2) == "RefPlane":
            ebenen.append(f)
        f = f.GetNextFeature()
    return ebenen


def letztes_feature(model):
    return model.FeatureByPositionReverse(0)


def kasten(model, ebene, breite, hoehe, tiefe, mitte=(0.0, 0.0)):
    """Rechteck-Skizze auf ebene + Extrusion blind (alle Maße in mm)."""
    model.ClearSelection2(True)
    ebene.Select2(False, 0)
    sm = model.SketchManager
    sm.InsertSketch(True)
    sm.CreateCenterRectangle(mm(mitte[0]), mm(mitte[1]), 0.0, mm(mitte[0] + breite / 2), mm(mitte[1] + hoehe / 2), 0.0)
    sm.InsertSketch(True)
    skizze = letztes_feature(model)
    model.ClearSelection2(True)
    skizze.Select2(False, 0)
    feat = model.FeatureManager.FeatureExtrusion3(
        True, False, False, 0, 0, mm(tiefe), 0.0, False, False, False, False, 0.0, 0.0,
        False, False, False, False, True, True, True, 0, 0.0, False,
    )
    if feat is None:
        raise RuntimeError("FeatureExtrusion3 lieferte None")
    return feat


def speichere(model, pfad: Path) -> int:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    return int(model.SaveAs3(str(pfad), 0, 1))  # swSaveAsCurrentVersion, swSaveAsOptions_Silent


def schliesse(app, model) -> None:
    app.CloseDoc(wert(model.GetTitle))


def lauf(name: str, fn) -> dict:
    try:
        ergebnis = {"ok": True, **fn()}
    except Exception as e:  # Spike: alles protokollieren
        ergebnis = {"ok": False, "fehler": repr(e), "trace": traceback.format_exc()}
    ERGEBNISSE.mkdir(parents=True, exist_ok=True)
    (ERGEBNISSE / f"{name}.json").write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str))
    return ergebnis
```

- [ ] **Step 2: `spikes/s1_verbinden.py`** – Frage: Klappt pywin32 unter Python 3.14 mit SW; Late oder Early Binding?

```python
"""S1: Verbindung, Revision, Early Binding (makepy)."""

from spikes._gemeinsam import lauf, start
from swki.verbindung import jahr_aus_revision, wert


def pruefen() -> dict:
    r, app = start()
    rev = wert(app.RevisionNumber)
    daten = {"revision": rev, "jahr": jahr_aus_revision(rev), "sichtbar": bool(wert(app.Visible))}
    try:
        import win32com.client

        early = win32com.client.gencache.EnsureDispatch(app._oleobj_)
        daten["early_binding"] = "ok"
        daten["early_revision"] = early.RevisionNumber()
    except Exception as e:
        daten["early_binding"] = repr(e)
    return daten


if __name__ == "__main__":
    lauf("s1_verbinden", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s1_verbinden`
Expected: `"ok": true`, `"jahr": 2025`. `early_binding` beantwortet die Frage (Ergebnis ist in jedem Fall gültig).

- [ ] **Step 3: `spikes/s2_ebenen.py`** – Frage: Liefern die ersten drei `RefPlane`-Features in deutscher Oberfläche Vorne/Oben/Rechts, und ist eine Skizze auf jeder möglich?

```python
"""S2: Sprachunabhängige Standardebenen."""

from spikes._gemeinsam import lauf, letztes_feature, neues_teil, schliesse, standardebenen, start
from swki.verbindung import wert


def pruefen() -> dict:
    r, app = start()
    model = neues_teil(app, r)
    try:
        ebenen = standardebenen(model)
        namen = [wert(e.Name) for e in ebenen]
        skizzen = []
        for e in ebenen:
            model.ClearSelection2(True)
            e.Select2(False, 0)
            model.SketchManager.InsertSketch(True)
            model.SketchManager.CreateCircleByRadius(0.0, 0.0, 0.0, 0.01)
            model.SketchManager.InsertSketch(True)
            skizzen.append(wert(letztes_feature(model).Name))
        return {"ebenen": namen, "anzahl": len(ebenen), "skizzen": skizzen}
    finally:
        schliesse(app, model)


if __name__ == "__main__":
    lauf("s2_ebenen", pruefen)
```

Vorher `swki api methode ISketchManager.CreateCircleByRadius` prüfen (erwartet 4 Parameter: Xc, Yc, Zc, Radius).
Run: `.venv\Scripts\python.exe -m spikes.s2_ebenen`
Expected: `"anzahl": 3`, `ebenen` ≈ `["Ebene vorne", "Ebene oben", "Ebene rechts"]`, drei Skizzennamen.

- [ ] **Step 4: `spikes/s3_skizze_extrusion.py`** – Frage: Extrusion per `FeatureExtrusion3` und wie wird eine Skizze voll bestimmt (Maße + Beziehungen) ohne Dialoge?

Vorher nachschlagen und die Ausgaben in den Spike-Bericht übernehmen:

```powershell
.venv\Scripts\python.exe -m swki api methode ISketchManager.FullyDefineSketch
.venv\Scripts\python.exe -m swki api methode ISketch.GetConstrainedStatus
.venv\Scripts\python.exe -m swki api enum swConstrainedStatus_e
.venv\Scripts\python.exe -m swki api suche "FullyDefineSketch"
```

Dann die Aufrufe in Variante A an die Parameterliste aus dem Index anpassen (Reihenfolge und Anzahl sind verbindlich; Enum-Werte für „alle Beziehungen“ und das Bemaßungsschema aus den dort genannten Enums ermitteln).

```python
"""S3: Rechteck-Skizze voll bestimmt + Extrusion."""

from spikes._gemeinsam import lauf, letztes_feature, neues_teil, schliesse, standardebenen, start
from swki.api.bauen import api_db
from swki.api.index import enum
from swki.verbindung import mm, wert


def _status(model, skizze_feat, db) -> str:
    skizze = skizze_feat.GetSpecificFeature2()
    code = wert(skizze.GetConstrainedStatus)
    namen = {e["wert"]: e["name"] for e in enum(db, "swConstrainedStatus_e")}
    return namen.get(code, str(code))


def pruefen() -> dict:
    r, app = start()
    db = api_db(r.sw_jahr)
    model = neues_teil(app, r)
    daten = {}
    try:
        oben = standardebenen(model)[1]
        oben.Select2(False, 0)
        sm = model.SketchManager
        sm.InsertSketch(True)
        sm.CreateCenterRectangle(0.0, 0.0, 0.0, mm(50), mm(30), 0.0)
        # Variante A: FullyDefineSketch – Argumente gemäß "swki api methode ISketchManager.FullyDefineSketch"
        try:
            relations_alle = sum(e["wert"] for e in enum(db, "swSketchFullyDefineRelationType_e"))
            daten["variante_a_rueckgabe"] = sm.FullyDefineSketch(
                True, True, relations_alle, True, 1, None, 1, None, 1, 1
            )
        except Exception as e:
            daten["variante_a_fehler"] = repr(e)
        sm.InsertSketch(True)
        skizze = letztes_feature(model)
        daten["status_nach_a"] = _status(model, skizze, db)
        model.ClearSelection2(True)
        skizze.Select2(False, 0)
        feat = model.FeatureManager.FeatureExtrusion3(
            True, False, False, 0, 0, mm(20), 0.0, False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True, 0, 0.0, False,
        )
        daten["extrusion"] = wert(feat.Name) if feat is not None else None
        daten["rebuild_fehler"] = wert(model.Extension.GetWhatsWrongCount) if hasattr(model.Extension, "GetWhatsWrongCount") else "n/a"
        return daten
    finally:
        schliesse(app, model)


if __name__ == "__main__":
    lauf("s3_skizze_extrusion", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s3_skizze_extrusion`
Expected (Erfolgskriterium): `extrusion` ist ein Name (nicht `null`). Für die voll bestimmte Skizze gilt als Ergebnis entweder `status_nach_a` = voll bestimmt (Enum-Name mit „Fully“) **oder** ein dokumentierter Fehlschlag von Variante A. Bei Fehlschlag Variante B ergänzen und erneut laufen lassen:

```python
        # Variante B: Maße einzeln per AddDimension2, Eingabedialog vorher abschalten
        # swInputDimValOnCreate per "swki api enum swUserPreferenceToggle_e" ermitteln
        toggle = {e["name"]: e["wert"] for e in enum(db, "swUserPreferenceToggle_e")}["swInputDimValOnCreate"]
        alt = app.GetUserPreferenceToggle(toggle)
        app.SetUserPreferenceToggle(toggle, False)
        try:
            segmente = sm.CreateCenterRectangle(0.0, 0.0, 0.0, mm(50), mm(30), 0.0)
            model.ClearSelection2(True)
            segmente[0].Select4(False, None)
            model.AddDimension2(0.0, mm(40), 0.0)
            model.ClearSelection2(True)
            segmente[1].Select4(False, None)
            model.AddDimension2(mm(60), 0.0, 0.0)
        finally:
            app.SetUserPreferenceToggle(toggle, alt)
```

Für jede Variante im Ergebnis-JSON festhalten, was funktioniert hat.

- [ ] **Step 5: `spikes/s4_masse_screenshot.py`** – Frage: Liefern Masseeigenschaften und Hüllquader die erwarteten Werte, und lassen sich Standardansichten als Bild speichern?

Vorher: `swki api methode IModelDocExtension.CreateMassProperty`, `IPartDoc.GetPartBox`, `IModelDoc2.ShowNamedView2`, `swki api enum swStandardViews_e`.

```python
"""S4: Volumen, Hüllquader, Screenshots der Standardansichten."""

from spikes._gemeinsam import kasten, lauf, neues_teil, schliesse, standardebenen, start
from swki.api.bauen import api_db
from swki.api.index import enum
from swki.verbindung import in_mm, in_mm3, wert


def pruefen() -> dict:
    r, app = start()
    db = api_db(r.sw_jahr)
    ansichten = {e["name"]: e["wert"] for e in enum(db, "swStandardViews_e")}
    model = neues_teil(app, r)
    try:
        kasten(model, standardebenen(model)[1], 100, 60, 20)
        mp = model.Extension.CreateMassProperty()
        box = [in_mm(v) for v in model.GetPartBox(True)]
        ordner = r.arbeitsordner / "stufe0" / "s4"
        ordner.mkdir(parents=True, exist_ok=True)
        bilder = {}
        for name, enum_name in [("iso", "swIsometricView"), ("vorne", "swFrontView"),
                                ("oben", "swTopView"), ("rechts", "swRightView")]:
            model.ShowNamedView2("", ansichten[enum_name])
            model.ViewZoomtofit2()
            for endung in ("png", "jpg"):
                pfad = ordner / f"{name}.{endung}"
                fehler = int(model.SaveAs3(str(pfad), 0, 3))  # Silent | Copy
                bilder[f"{name}.{endung}"] = {"fehler": fehler, "bytes": pfad.stat().st_size if pfad.exists() else 0}
        return {
            "volumen_mm3": in_mm3(wert(mp.Volume)),
            "volumen_soll_mm3": 120000.0,
            "oberflaeche_mm2": round(wert(mp.SurfaceArea) * 1e6, 3),
            "huellquader_mm": box,
            "bilder": bilder,
            "ordner": str(ordner),
        }
    finally:
        schliesse(app, model)


if __name__ == "__main__":
    lauf("s4_masse_screenshot", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s4_masse_screenshot`
Expected: `volumen_mm3` = 120000.0 (±0,001); Hüllquader-Ausdehnung 100 × 20 × 60 mm (Reihenfolge laut Rückgabe `[xmin,ymin,zmin,xmax,ymax,zmax]`); mindestens ein Bildformat mit `bytes` > 0. Die Bilder öffnen und prüfen, ob die Ansichten stimmen.

- [ ] **Step 6: Commit**

```powershell
git add spikes docs/stufe0/ergebnisse
git commit -m "stufe0: Spikes S1–S4 (Verbindung, Ebenen, Skizze/Extrusion, Masse/Screenshots)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Spikes S5–S7 (Baugruppe, Bewegung, Toolbox)

**Files:**
- Create: `spikes/s5_kollision.py`, `spikes/s6_abstand_verstellen.py`, `spikes/s7_toolbox.py`

**Interfaces:**
- Consumes: alles aus `spikes/_gemeinsam.py` (Task 13), `byref_long`, `api_db`, `enum`, `suche`

- [ ] **Step 1: `spikes/s5_kollision.py`** – Frage: Komponenten per API einfügen und Kollisionen zählen.

Vorher: `swki api methode IAssemblyDoc.AddComponent5`, `IAssemblyDoc.InterferenceDetectionManager`, `IInterferenceDetectionMgr.GetInterferenceCount`, `swki api enum swAddComponentConfigOptions_e`.

```python
"""S5: Zwei Kästen in Baugruppe, überlappend und nicht überlappend, Kollisionsprüfung."""

from spikes._gemeinsam import kasten, lauf, neue_baugruppe, neues_teil, schliesse, speichere, standardebenen, start
from swki.verbindung import mm, wert


def _teil(app, r, pfad):
    model = neues_teil(app, r)
    kasten(model, standardebenen(model)[1], 100, 60, 20)
    fehler = speichere(model, pfad)
    if fehler:
        raise RuntimeError(f"Speichern {pfad}: Fehler {fehler}")
    return model


def _zaehle(assy) -> int:
    idm = assy.InterferenceDetectionManager
    try:
        return int(wert(idm.GetInterferenceCount))
    finally:
        idm.Done()


def pruefen() -> dict:
    r, app = start()
    ordner = r.arbeitsordner / "stufe0" / "s5"
    teil = _teil(app, r, ordner / "kasten.sldprt")  # bleibt geöffnet, AddComponent braucht es im Speicher
    assy = neue_baugruppe(app, r)
    try:
        pfad = str(ordner / "kasten.sldprt")
        c1 = assy.AddComponent5(pfad, 0, "", False, "", 0.0, 0.0, 0.0)
        c2 = assy.AddComponent5(pfad, 0, "", False, "", mm(50), 0.0, 0.0)
        ueberlappend = _zaehle(assy)
        c2.Select4(False, None, False)
        assy.EditDelete()
        c3 = assy.AddComponent5(pfad, 0, "", False, "", mm(150), 0.0, 0.0)
        frei = _zaehle(assy)
        return {
            "komponenten_ok": all(c is not None for c in (c1, c2, c3)),
            "kollisionen_ueberlappend": ueberlappend,
            "kollisionen_frei": frei,
        }
    finally:
        schliesse(app, assy)
        schliesse(app, teil)


if __name__ == "__main__":
    lauf("s5_kollision", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s5_kollision`
Expected: `komponenten_ok: true`, `kollisionen_ueberlappend` ≥ 1, `kollisionen_frei` = 0.

- [ ] **Step 2: `spikes/s6_abstand_verstellen.py`** – Frage: Abstandsverknüpfung anlegen, schrittweise verstellen, Position der Komponente nachmessen.

Vorher: `swki api methode IModelDocExtension.SelectByRay`, `IAssemblyDoc.AddMate5`, `IMate2.DisplayDimension2`, `IDimension.SetSystemValue3`, `swki api enum swMateType_e`, `swMateAlign_e`, `swSelectType_e`, `swSetValueInConfiguration_e`. Parameterreihenfolge von `AddMate5` aus dem Index übernehmen; der Aufruf unten entspricht der erwarteten Signatur (15 Parameter, letzter = ErrorStatus als ByRef).

```python
"""S6: Abstandsverknüpfung zwischen zwei Kästen verstellen und Position messen."""

from spikes._gemeinsam import kasten, lauf, neue_baugruppe, neues_teil, schliesse, speichere, standardebenen, start
from swki.api.bauen import api_db
from swki.api.index import enum
from swki.verbindung import byref_long, in_mm, mm, wert


def _e(db, name):
    return {e["name"]: e["wert"] for e in enum(db, name)}


def pruefen() -> dict:
    r, app = start()
    db = api_db(r.sw_jahr)
    mate, align, sel = _e(db, "swMateType_e"), _e(db, "swMateAlign_e"), _e(db, "swSelectType_e")
    ordner = r.arbeitsordner / "stufe0" / "s6"
    teil = neues_teil(app, r)
    kasten(teil, standardebenen(teil)[1], 40, 40, 20)       # Kasten von y=0 bis y=20 mm
    speichere(teil, ordner / "block.sldprt")
    assy = neue_baugruppe(app, r)
    try:
        pfad = str(ordner / "block.sldprt")
        unten = assy.AddComponent5(pfad, 0, "", False, "", 0.0, 0.0, 0.0)          # erste = fixiert
        oben = assy.AddComponent5(pfad, 0, "", False, "", 0.0, mm(50), 0.0)        # y=50..70 mm
        ext = assy.Extension
        assy.ClearSelection2(True)
        a = ext.SelectByRay(mm(5), mm(30), mm(5), 0.0, -1.0, 0.0, mm(0.5), sel["swSelFACES"], False, 1, 0)
        b = ext.SelectByRay(mm(5), mm(40), mm(5), 0.0, 1.0, 0.0, mm(0.5), sel["swSelFACES"], True, 1, 0)
        fehler = byref_long()
        m = assy.AddMate5(mate["swMateDISTANCE"], align["swMateAlignCLOSEST"], False, mm(30), mm(30), mm(30),
                          1, 1, 0.0, 0.0, 0.0, False, False, 0, fehler)
        messungen = []
        for soll in (30, 10, 60):
            dim = m.DisplayDimension2(0).GetDimension2(0)
            dim.SetSystemValue3(mm(soll), 1, None)
            assy.EditRebuild3()
            y_mm = in_mm(oben.Transform2.ArrayData[10])
            messungen.append({"soll_abstand": soll, "y_ursprung_oben_mm": round(y_mm, 4), "erwartet": 20 + soll})
        return {"auswahl": [bool(a), bool(b)], "mate_ok": m is not None, "fehlerstatus": fehler.value,
                "messungen": messungen, "unten_fixiert": bool(wert(unten.IsFixed))}
    finally:
        schliesse(app, assy)
        schliesse(app, teil)


if __name__ == "__main__":
    lauf("s6_abstand_verstellen", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s6_abstand_verstellen`
Expected: `mate_ok: true`; für jede Messung `y_ursprung_oben_mm` ≈ `erwartet` (±0,001). Abweichende Signaturen oder Werte (z. B. `swSetValue_InThisConfiguration` ≠ 1) im Ergebnis vermerken und den Aufruf nach Index korrigieren.

- [ ] **Step 3: `spikes/s7_toolbox.py`** – Frage: Lässt sich ein Toolbox-Teil (z. B. DIN 912 M8×30) per API erzeugen?

```python
"""S7: Toolbox – Bestandsaufnahme (Daten, Add-in, API-Doku)."""

from pathlib import Path

from spikes._gemeinsam import lauf, start
from swki.api.bauen import api_db
from swki.api.index import suche


def pruefen() -> dict:
    r, app = start()
    db = api_db(r.sw_jahr)
    daten_ordner = Path(r"C:\SOLIDWORKS Data")
    return {
        "toolbox_daten": daten_ordner.exists(),
        "normen": sorted(p.name for p in (daten_ordner / "browser").iterdir()) if daten_ordner.exists() else [],
        "interop_configure_addin": (r.installationsordner / "api" / "redist" /
                                    "SolidWorks.Interop.sldtoolboxconfigureaddin.dll").exists(),
        "doku_toolbox": suche(db, "Toolbox component create", 15),
        "doku_toolbox_konfig": suche(db, "Toolbox configure size", 15),
    }


if __name__ == "__main__":
    lauf("s7_toolbox", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s7_toolbox`
Danach die Treffer lesen (`swki api methode …` für jede gefundene Toolbox-Methode). Wenn eine Methode existiert, die ein Toolbox-Teil mit Norm/Größe erzeugt: einen Versuch für DIN 912 M8×30 als Funktion `versuch_erzeugen()` in `s7_toolbox.py` ergänzen, ausführen und Ergebnis (`erzeugt: true/false`, Pfad, Fehler) in `docs/stufe0/ergebnisse/s7_toolbox.json` ergänzen. Existiert keine: `"entscheidung": "Rückfallweg"` eintragen (Größe manuell erzeugen, per `swki normteil aufnehmen` übernehmen – Stufe 3).

- [ ] **Step 4: Commit**

```powershell
git add spikes docs/stufe0/ergebnisse
git commit -m "stufe0: Spikes S5–S7 (Kollision, Abstand verstellen, Toolbox)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Auswertung Stufe 0 und Wissensdatei

**Files:**
- Create: `docs/stufe0/ergebnisse.md`, `swki/wissen/pywin32-fallstricke.md`
- Modify: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` (nur falls Ergebnisse das Design ändern)

- [ ] **Step 1: `docs/stufe0/ergebnisse.md` schreiben**

Gliederung (alle Abschnitte mit den tatsächlichen Werten aus `docs/stufe0/ergebnisse/*.json` füllen):

```markdown
# Stufe 0 – Ergebnisse (Rechner A, SW 2025)

| Spike | Frage | Ergebnis | Folge für Stufe 2+ |
|---|---|---|---|
| S1 | pywin32 3.14 ↔ SW, Early Binding | … | Late/Early Binding festlegen |
| S2 | Ebenen sprachunabhängig | … | Anker-Auflöser |
| S3 | Voll bestimmte Skizze + Extrusion | Variante A/B … | Handler „skizze“ |
| S4 | Masse, Hüllquader, Screenshots | … | Prüfung Stufe 1+2, Bildformat |
| S5 | Kollisionsprüfung | … | Baugruppen-Prüfung |
| S6 | Abstand verstellen, Position messen | … | Bewegungsprüfung |
| S7 | Toolbox per API | … | Normteile: Toolbox-Weg oder Rückfall |
| MCP | Lese-Tools sichtbar, Sperren wirksam | … | – |

## Abweichungen von erwarteten Signaturen/Enum-Werten
## Offene Punkte für den Plan von Stufe 2
```

- [ ] **Step 2: `swki/wissen/pywin32-fallstricke.md` anlegen**

Nur **verifizierte** Punkte aus S1–S7 aufnehmen. Grundgerüst:

```markdown
# pywin32 + SolidWorks: geprüfte Muster

Stand: <Datum>, SW <Jahr>, Python <Version>. Nur Einträge, die in docs/stufe0 belegt sind.

## Verbindung
- An laufendes SolidWorks hängen: `win32com.client.GetActiveObject("SldWorks.Application.<rev>")` (swki.verbindung.verbinde).
- Binding: <Ergebnis S1>

## Einheiten
- API: Meter, Radiant, m³. Hilfen: swki.verbindung.mm / in_mm / in_mm3 / grad.

## Auswahl ohne Namen (deutsche Oberfläche)
- Standardebenen: erste drei RefPlane-Features (S2).
- Flächen: IModelDocExtension.SelectByRay (S6).

## Parameter-Eigenheiten
- Callout: `callout_leer()` = VARIANT(VT_DISPATCH, None).
- ByRef-long (z. B. ErrorStatus): `byref_long()`; Wert danach in `.value`.
- <weitere Befunde aus S3–S6>

## Bekannte Fehlschläge
- <z. B. FullyDefineSketch-Variante, Bildformat>
```

- [ ] **Step 3: Design anpassen, falls nötig**

Wenn ein Ergebnis eine Annahme im Design widerlegt (z. B. Toolbox nur per Rückfallweg, Screenshots nur als JPG, Skizzen nur per Variante B voll bestimmbar), die betroffene Stelle in der Spec knapp korrigieren und in `ergebnisse.md` unter „Folge“ darauf verweisen.

- [ ] **Step 4: Gesamte Testsuite**

Run: `.venv\Scripts\python.exe -m pytest -v; .venv\Scripts\python.exe -m pytest -m sw -v`
Expected: alle Unit-Tests grün; alle Live-Tests grün.

- [ ] **Step 5: Commit**

```powershell
git add docs/stufe0 swki/wissen docs/superpowers/specs
git commit -m "stufe0: Auswertung und geprüfte pywin32-Muster" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Übergabe**

Dem Nutzer die Ergebnistabelle zeigen und vorschlagen: (a) Plan für Stufe 2 schreiben, (b) optional jetzt schon `setup\einrichten.ps1` auf dem SW-2026-Rechner ausführen und `pytest -m sw` dort laufen lassen (Push nur nach Rückfrage).
