# Paket Formschräge – Option an Extrusion und Schnitt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `extrusion` und `schnitt` bekommen die Option `formschraege: {winkel, querschnitt: kleiner | groesser}`; swki baut die schrägen Wände mit `FeatureExtrusion3`/`FeatureCut4`, `validieren` fängt zusammenfallende Profile und unbrauchbare Anker ab, und `swki pruefen` misst Winkel und Richtung jeder Seitenfläche gegen die freigegebene Kopie.

**Architecture:** Reine Rechnung in `swki/formschraege.py` (Richtung r, Soll-Vorzeichen, versetzter Querschnitt A(d) = A + P·d + K·d², Zusammenfall, Seitenflächen aus Punkt und Normale); darauf bauen Schema und `validieren` (`swki/spec/laden.py`), das Sollvolumen (`swki/pruefung/geometrie.py`), der Handler (`swki/compiler/handler/extrusion.py`, nur drei Parameter mehr) und die Prüfung `formschraegen` (`swki/pruefung/messen.py` liest je Fläche Punkt und Normale, `swki/pruefung/bewertung.py` bewertet). Spike S16 belegt die Annahmen des Handlers und der Messung, danach Live-Tests, Referenz *Zentrieraufnahme* mit zwei Negativfällen und Doku.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) für Spike und Live-Tests.

**Spec:** `docs/superpowers/specs/2026-10-07-formschraege-design.md` (mit dem Nutzer abgestimmt, 2026-10-07; bei der Planung nachgezogen: §4, §6.1, §6.3). Kontext: Gesamtdesign `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`, Spec 2c `docs/superpowers/specs/2026-09-29-stufe-2c-design.md` (Endbedingungen, Sollvolumen, Modellierregeln).

**Vorab geprüft (2026-10-07):** Der gesamte Plan-Code wurde in einem Wegwerf-Worktree Task für Task angewendet (erst die Tests, RED-Lauf, dann die Umsetzung, GREEN-Lauf, ganze Suite, `swki api pruefe-code swki spikes tests/live`). Jede Ersetzung traf genau einmal, alle Testzahlen unten sind gemessen, `pruefe-code` blieb ohne Befund. Die Referenz-Spec validiert ohne Befund und ohne Hinweis. Ungeprüft (braucht SolidWorks): der Spike, der Handler am echten Modell, die Messung und alle Live-Tests – dafür die Tabelle „Abhängigkeiten vom Spike S16“.

## Präzisierungen gegenüber der Spec (vom Planer, bindend für diesen Plan)

1. **Modul:** Die reine Rechnung steht in `swki/formschraege.py` (Spec nennt keine Datei). Handler, `validieren`, Sollvolumen, Messung und Spike nutzen dieselben Funktionen (`schraege`, `skizzennormale`, `extrusionsrichtung`, `soll_vorzeichen`, `seitenflaechen` …).
2. **Messung (Spec §6.1):** Jede Fläche des Features wird gleich gemessen: Punkt nahe der Mitte ihrer Box (`IFace2.GetClosestPointOn`), Normale der Trägerfläche dort (`ISurface.EvaluateAtPoint`, die ersten drei Werte), umgedreht wenn `IFace2.FaceInSurfaceSense` True ist. Das gilt für Ebenen, Kegel und jede andere Flächenart; die Kategorie „nicht messbar“ entfällt. Scheitert das Lesen, wird der ganze Knoten ein Fehlertext (Mangel). Seitenflächen sind alle Flächen mit |n·r| ≤ 1 − 1e-6.
3. **Winkelmaß (Spec §4):** Der Name des Winkelmaßes hängt von der Endbedingung ab: `WINKEL_MASS = {"blind": "D2", "mittig": "D2", "versatz_von_flaeche": "D2", "durch_alles": "D1", "bis_flaeche": "D1"}` (ohne Tiefenmaß ist der Winkel das erste Maß) – Annahme, Spike S16 Zeile 4.
4. **Richtung im Handler:** `DDIR_KLEINER = {"extrusion": True, "schnitt": True}` (`Ddir1` True = „nach innen“ heißt `kleiner` für Aufsatz und Schnitt, unabhängig von `umkehren`) – Annahme, Spike S16 Zeile 1.
5. **Bericht (Spec §6.3):** kein eigener Abschnitt. Die Prüfung `formschraegen` steht wie `normbohrungen` im Prüfbericht: `ist` = Abweichungen je Knoten, `gemessen` = gemessene Winkel je Knoten (für den Prüfer), `knoten` = abweichende Knoten; Mängel erscheinen mit Knoten in der Mängelliste und in `bericht.md`.
6. **Ankerprüfung (Spec §5.3):** geprüft werden alle Objekte mit einem Feature-Verweis `feature` unter `features` und `pruefung` (auch `masse_pruefen`), Schlüssel `flaeche` und `kanten_an` sowie `auswahl: senkrechte_kanten`. Liegt die Skizze des schrägen Features auf `{nahe}`, ist die Extrusionsrichtung ohne Modell unbekannt: keine Prüfung.
7. **Zusammenfall (Spec §5.2):** Rechteck mit Eckradius: Grenze ist der Eckradius (er ist immer kleiner als die halbe kürzere Seite). Den Winkelbereich (0, 90) prüft die allgemeine Winkelprüfung von `plausibel_befunde` (neuer Zweig für Pfade mit `formschraege`).
8. **Negativfälle (Spec §9):** verfälscht wird über `monkeypatch` des Namens `schraege` im Modul `swki.compiler.handler.extrusion` (nur Knoten `zapfen`): Fall 1 `querschnitt: groesser`, Fall 2 `winkel: "=WZ+3"`. Ein verfälschter Zahlenwert allein würde beim Rebuild von der Gleichung am Feature zurückgestellt. Erwartete Mängelmenge je Fall `{formschraegen, volumen}`.
9. **Referenz *Zentrieraufnahme* (Spec §9, „Plan legt fest“):** Platte 160 × 100 × 20, Eckradius 8, Werkstoff 1.0038. Zapfen Ø30 × 25, 10° `kleiner`, bei u = −50. Tasche 40 × 30 R6, Tiefe 12, 8° `kleiner`, bei (45, 22). Trichter von der Unterseite, Auslauf Ø10, 30° `groesser`, `durch_alles`, bei (45, −25), oben Ø33,09. Steg auf Ebene vorne, Profil 40 × 12 mit Mitte (−5, 24) (ragt 2 mm in die Platte), Dicke 10 `mittig`, 5° `kleiner`. Alle Lagen als Parameter. Prüfung: Hüllquader [L, H + HZ, B], Sollvolumen 315014,796 mm³ (`sollvolumen.py`, unabhängig gerechnet, Toleranz 0,05 %), Zapfenhöhe und Taschenboden über der Unterseite (Anker parallel zur Extrusion).
10. **Live-Minimalteile (Spec §10):** Block 100 × 60 × 20; Kreis Ø20 blind 8 für Aufsatz/Schnitt × kleiner/groesser, Tasche mit Eckradius samt Gleichungsänderung W 10 → 15, Aufsatz mit `umkehren`, Steg `mittig` frei über dem Block, Trichter `durch_alles` von der Unterseite – zusammen 8 Tests.
11. **Toleranz:** `toleranzen.winkel_grad: 0.01` in `config/standard.yaml` (Spike S16 Zeile 5).

## Global Constraints

- **Umfang:** Option `formschraege` an `extrusion`/`schnitt` mit allen fünf Endbedingungen; Prüfung `formschraegen`; Sollvolumen für ein Profil (Kreis, Rechteck, Rechteck mit Eckradius, Langloch, konvexes Polygon) bei `blind`/`mittig`. Nicht: eigenes Feature (`InsertMultiFaceDraft`), Formschräge an `rotation`/`verzahnung`/`normbohrung`, Entformungsanalyse, unterschiedliche Winkel je Seite bei `mittig`, Rechner B.
- **Bestand bleibt:** Ohne `formschraege` sind die Aufrufe von `FeatureExtrusion3`/`FeatureCut4` unverändert (`Dchk1 = False`, Winkel 0). Referenzen *Buchse*, *Formplatte*, *Auswerferhalteplatte*, *Stehlager*, *Linearschlitten*, *Zahnstangentrieb* samt Teilen und *Motorhalter* bestehen weiter.
- **Freigabe:** Prüfsumme unverändert (Features sind Bauweg). `querschnitt` ist Text und von der Prüfsumme nicht geschützt – die Prüfung `formschraegen` misst deshalb gegen die freigegebene Kopie; der Winkel gehört als Parameter in die Spec (`validieren` meldet feste Winkel als `feste_zahl`).
- **Late Binding** (`swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()` (`GetFaces`, `GetBox`, `GetSurface`, `FaceInSurfaceSense`, `IsPlane`, `IsCone`, `ConeParams2`, `Normal`, `GetEquationMgr`, `GetCount`).
- **API nachschlagen:** vor jedem **neuen** SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` (vorher `$env:PYTHONIOENCODING='utf-8'`). `.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` muss ohne Befunde bleiben. Bereits nachgeschlagen (2026-10-07): `IFeatureManager.FeatureExtrusion3` (23 Parameter; `Dchk1` 7, `Ddir1` 9 „True for first draft angle to be inward“, `Dang1` 11), `IFeatureManager.FeatureCut4` (27 Parameter; dieselben Indizes), `ISurface.EvaluateAtPoint` (3; Rückgabe 11 Werte, zuerst die Flächennormale), `IFace2.FaceInSurfaceSense` (0; True = Fläche entgegen der Trägerfläche), `IFace2.GetClosestPointOn` (3; X, Y, Z, U, V), `ISurface.ConeParams2` (Property, seit 2015; Ursprung, Achse, Radius, halber Winkel in rad, Bezugsrichtung), `ISurface.IsCone` (0), `IFace2.Normal` (Property).
- **Einheiten:** Spezifikation und Ausgaben in mm und Grad; die API rechnet in m und rad (`ctx.rad`, `in_mm`).
- **Prüfwerte nie an Messwerte anpassen.** Erwartungen der Negativfälle nie abschwächen; weicht ein Live-Ergebnis ab, anhalten (NEEDS_CONTEXT) und dem Controller den Prüfbericht-Auszug melden. Das Sollvolumen der Referenz kommt nur aus `sollvolumen.py`.
- **Sprache:** Code-Bezeichner, Docstrings, Kommentare, Commit-Messages, Berichte auf Deutsch (mit Umlauten in Texten).
- **Tests:** `.venv\Scripts\python.exe -m pytest -q` (ohne SolidWorks; Stand vor dem Plan: **960 passed, 141 deselected**). Jeder Task nennt die erwarteten Zahlen (vorab gemessen); abweichende Zahlen im Bericht begründen. Live-Tests nur einzeln: `.venv\Scripts\python.exe tests\live_einzeln.py <datei::test-id> --zeit 900` mit `$env:PYTHONIOENCODING='utf-8'`.
- **SolidWorks (Live-Tasks):** nur Teile, keine Baugruppen – Teil-Live-Tests dürfen bis ca. 4 GB Private Bytes in einer Sitzung laufen (`Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`), darüber BLOCKED (Neustart) an den Controller. Genau eine Instanz (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`); Einstellungen vor und nach Live-Läufen `False 1` (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); print(app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6))"`). Implementer starten oder beenden SolidWorks nie. Keine künstliche CPU-Last.
- **Nur eigene Dokumente** anfassen; speichern nur im `arbeitsordner` aus `config/rechner.yaml`; nie ein SolidWorks-Jahr oder einen Pfad fest in Code schreiben.
- **Git:** Branch `formschraege` (von `plan-formschraege`), kleine Commits je Task; Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **kein `git push` ohne Rückfrage**; nichts aus `auftraege/` committen; erzeugte SolidWorks-Dateien nie committen; immer gezielt `git add <dateien>`. `core.autocrlf` ist `true`: neue Dateien und Volltext-Ersetzungen dürfen LF schreiben; Ersetzungen in bestehenden Dateien mit dem Edit-Werkzeug (kein sed auf CRLF-Dateien).
- **Ersetzungen:** „In `<datei>` ersetzen“ heißt: den Block exakt (ohne Zeilenende-Unterschiede) einmal finden und ersetzen. Trifft er nicht genau einmal, anhalten und melden (der Plan wurde so geprüft, dass jeder Block genau einmal trifft).
- **Subagents:** Implementer starten keine Subagents. Prüfer-Agenten startet der Controller. Nie zwei Implementer gleichzeitig, solange SolidWorks läuft.

## Review Focus

Eingaben und Zustände, die die Spec nahelegt, die aber kein Kernfall abdeckt – je mit dem Test, der sie festhält:

1. **Unbekannter Parameter im Winkel** (`winkel: "=WX"`): `validieren` meldet nur den Ausdrucksfehler am Winkel, keine Folgefehler aus der Zusammenfallprüfung – `test_unbekannter_parameter_im_winkel` (Task 2).
2. **Skizze des schrägen Features auf `{nahe}`**: ohne Modell ist die Extrusionsrichtung unbekannt; `validieren` lässt die Anker unbeanstandet statt abzustürzen – `test_skizze_auf_nahe_ohne_ankerpruefung` (Task 2).
3. **Mehrere Profile mit `kleiner`** (Ring): keine Vorabprüfung des Zusammenfalls, kein falscher Befund – `test_ring_mit_kleiner_ohne_vorabpruefung` (Task 2).
4. **Teil ohne Formschräge mit älterer Projektvorgabe** (`toleranzen` ohne `winkel_grad`): die Bewertung braucht die Toleranz nur, wenn es schräge Features gibt – `test_ohne_formschraege_braucht_keine_winkeltoleranz` (Task 4).
5. **COM-Fehler beim Lesen einer Fläche**: der Knoten wird ein Fehlertext (Mangel) statt die ganze Prüfung abzubrechen – `test_messfehler_wird_fehlertext` (Task 4).

## Dateistruktur nach diesem Plan

```
swki/formschraege.py                    neu: Richtung, Soll-Vorzeichen, Querschnitt, Volumen, Zusammenfall, Seitenflächen
schema/teil.schema.json                 + ende.formschraege
swki/spec/laden.py                      Winkelbereich, Zusammenfall, Anker an schrägen Features
swki/pruefung/geometrie.py              volumen_auto mit Formschräge
swki/compiler/handler/extrusion.py      Dchk1/Ddir1/Dang1, DDIR_KLEINER, WINKEL_MASS, schraege_sw
swki/pruefung/{messen,bewertung}.py     Prüfung formschraegen (punkt_und_normale, formschraegen, formschraege_abweichungen)
config/standard.yaml                    + toleranzen.winkel_grad
spikes/s16_formschraege.py              Spike S16
tests/test_formschraege.py, tests/spec/test_formschraege_spec.py, tests/compiler/test_extrusion_schraege.py,
tests/pruefung/test_formschraege_pruefung.py, tests/referenz/test_zentrieraufnahme.py
tests/live/test_live_formschraege.py, tests/live/test_live_zentrieraufnahme.py
tests/referenz/zentrieraufnahme/        Referenz: zentrieraufnahme.yaml, sollvolumen.py
.claude/skills/konstruieren/SKILL.md, .claude/agents/pruefer.md, CLAUDE.md, Design §11
docs/formschraege/ergebnisse.md
```

## Abhängigkeiten vom Spike S16 (Task 5)

Der Plan-Code setzt die Spalte „Annahme“ voraus. Weicht der Spike ab, entscheidet der Controller nach der Spalte „sonst“ und hält es im Ledger fest, bevor der betroffene Task beginnt. Schlüssel = Fälle in `docs/stufe0/ergebnisse/s16_formschraege.json`.

| # | Frage | Annahme (Plan-Code) | sonst | betrifft |
|---|---|---|---|---|
| 1 | Richtung (`1_*`) | alle sechs Fälle: `fehler` null, `vorzeichen_passt` true, `volumen_abw_prozent` < 0,01 | alle Fälle eines Typs mit falschem Vorzeichen: `DDIR_KLEINER[typ]` umkehren (Ledger); nur die Fälle mit `umkehren` falsch: Ddir hängt von `umkehren` ab → `schraege_sw` liefert `(DDIR_KLEINER[typ] == kleiner) != umkehren` (Ledger, Test in Task 3 nachziehen); Vorzeichen richtig, Volumen falsch: Nutzer fragen | 3, 6, 7 |
| 2 | Endbedingungen (`2_*`) | `mittig`, `durch_alles`, `bis_flaeche`, `versatz_von_flaeche` gebaut, Vorzeichen passt, Volumen < 0,01 % (bei `mittig` beide Seiten geschrägt) | `mittig` nur eine Seite geschrägt: `Dchk2`/`Ddir2`/`Dang2` wie Seite 1 setzen (Ledger, Task 3 nachziehen); eine Endbedingung baut mit Formschräge nicht: `validieren` lehnt `formschraege` dort ab (Befund in Task 2, Spec §2 nachziehen, Nutzer informieren) | 2, 3, 6, 7 |
| 3 | Ring (`3_ring`) | `volumen_aenderung` = `3_ring_soll.innen_waechst` ± 0,01 %, alle gemessenen Vorzeichen +1 (der Innenrand rückt nach außen) | Innenrand schrumpft mit (`innen_schrumpft`): `validieren` lehnt `formschraege` bei mehreren Profilen ab (Befund in Task 2, Spec §3 nachziehen, Nutzer informieren) | 2, 4 |
| 4 | Maße (`masse`, `gleichungen`) | Winkelmaß heißt wie `WINKEL_MASS[ende]` und hat den Winkel als Wert; Gleichung `"<Maß>@f2" = "W"` steht in `gleichungen` | anderer Name: `WINKEL_MASS` anpassen (Ledger); Gleichung abgelehnt (`GLEICHUNG_FEHLER`): Nutzer fragen | 3, 6 |
| 5 | Messung (`flaechen`, `winkel_abw_max_grad`) | `abw_normale_max` < 1e-9 (Ebenen), `abw_kegelwinkel_max_grad` < 1e-6 (Kegel), `winkel_abw_max_grad` < 0,001 | Normale aus `EvaluateAtPoint` weicht ab: `punkt_und_normale` nimmt bei Ebenen `face.Normal` und bei Kegeln `ConeParams2` mit `FaceInSurfaceSense` (Ledger, Code und Test in Task 4 nachziehen); größere Winkelabweichung: `winkel_grad` auf das Doppelte der größten Abweichung, höchstens 0,1 (Ledger) | 4, 6, 7 |
| 6 | Eckradius (`6_eckradius_*`) | 16° gebaut, Volumen < 0,01 %; 17° und 20° nicht gebaut oder Volumen ≠ Formel | 17°/20° bauen mit passendem Volumen: die Regel in `validieren` ist nur vorsichtig – sie bleibt (Ledger) | 2 |
| 7 | Volumen weiterer Profile (`7_*`) | Rechteck mit Eckradius `groesser` und Sechseck `kleiner`: Volumen < 0,01 % | `querschnitt_koeffizienten` für das Profil prüfen; ohne Lösung liefert es dort `None` (Ledger, Task 1 nachziehen) | 1, 2 |

---

### Task 1: Reine Rechnung (`swki/formschraege.py`, ohne SolidWorks)

**Files:**
- Create: `swki/formschraege.py`
- Test: `tests/test_formschraege.py`

**Interfaces:**
- Consumes: `swki.compiler.anker` (`RICHTUNGEN`, `Vektor`, `differenz`, `skalar`), `swki.spec.ausdruck.auswerten`.
- Produces (von allen späteren Tasks genutzt):
  - `TYPEN = ("extrusion", "schnitt")`, `STANDARDNORMALE`.
  - `schraege(f) -> dict | None`, `skizzennormale(ebene) -> Vektor | None`,
    `extrusionsrichtung(normale, typ, umkehren) -> Vektor`, `soll_vorzeichen(typ, querschnitt) -> int`,
    `quer_zur_richtung(richtung, normale) -> bool`.
  - `feste_tiefe(ende, parameter) -> float | None`, `grenze_kleiner(element, parameter) -> tuple[float, str] | None`.
  - `querschnitt_koeffizienten(element, parameter) -> tuple[float, float, float] | None`,
    `volumen(koeffizienten, tiefe, winkel, querschnitt, mittig=False) -> float`,
    `volumen_feature(f, parameter) -> tuple[float | None, str]`.
  - `seitenflaechen(messungen: list[(Punkt, Normale)], r, ebenenpunkt=None) -> list[{"winkel", "vorzeichen"}]`.

- [ ] **Step 1: Test schreiben**

`tests/test_formschraege.py` anlegen:

```python
"""Reine Rechnung der Formschräge (swki.formschraege, ohne SolidWorks)."""

import math

import pytest

from swki.formschraege import (
    extrusionsrichtung, feste_tiefe, grenze_kleiner, quer_zur_richtung, querschnitt_koeffizienten, schraege,
    seitenflaechen, skizzennormale, soll_vorzeichen, volumen, volumen_feature,
)


def _feature(element, ende, typ="extrusion"):
    return {"id": "f2", "typ": typ, "skizze": {"ebene": "oben", "elemente": [element]}, "ende": ende}


def test_schraege_nur_bei_extrusion_und_schnitt():
    s = {"winkel": 5, "querschnitt": "kleiner"}
    assert schraege(_feature({"kreis": {}}, {"typ": "blind", "tiefe": 5, "formschraege": s})) == s
    assert schraege(_feature({"kreis": {}}, {"typ": "blind", "tiefe": 5})) is None
    assert schraege({"id": "r", "typ": "rotation", "skizze": {}}) is None


@pytest.mark.parametrize(("ebene", "normale"), [
    ("oben", (0.0, 1.0, 0.0)),
    ({"versatz": {"ebene": "rechts", "abstand": 20}}, (1.0, 0.0, 0.0)),
    ({"feature": "f1", "flaeche": "-y"}, (0.0, -1.0, 0.0)),
    ({"nahe": [0, 0, 0]}, None),
])
def test_skizzennormale(ebene, normale):
    assert skizzennormale(ebene) == normale


@pytest.mark.parametrize(("typ", "umkehren", "r"), [
    ("extrusion", False, (0.0, 1.0, 0.0)),
    ("extrusion", True, (0.0, -1.0, 0.0)),
    ("schnitt", False, (0.0, -1.0, 0.0)),
    ("schnitt", True, (0.0, 1.0, 0.0)),
])
def test_extrusionsrichtung_wie_handler(typ, umkehren, r):
    assert extrusionsrichtung((0.0, 1.0, 0.0), typ, umkehren) == r


@pytest.mark.parametrize(("typ", "querschnitt", "vorzeichen"), [
    ("extrusion", "kleiner", 1), ("extrusion", "groesser", -1), ("schnitt", "kleiner", -1), ("schnitt", "groesser", 1),
])
def test_soll_vorzeichen(typ, querschnitt, vorzeichen):
    assert soll_vorzeichen(typ, querschnitt) == vorzeichen


def test_quer_zur_richtung():
    assert quer_zur_richtung("+x", (0.0, 1.0, 0.0))
    assert quer_zur_richtung("-z", (0.0, 1.0, 0.0))
    assert not quer_zur_richtung("+y", (0.0, 1.0, 0.0))
    assert not quer_zur_richtung("-y", (0.0, 1.0, 0.0))


def test_feste_tiefe():
    p = {"T": 12}
    assert feste_tiefe({"typ": "blind", "tiefe": "=T"}, p) == 12
    assert feste_tiefe({"typ": "mittig", "tiefe": "=T"}, p) == 6
    assert feste_tiefe({"typ": "durch_alles"}, p) is None
    assert feste_tiefe({"typ": "bis_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}}, p) is None


def test_grenze_kleiner():
    assert grenze_kleiner({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {}) == (10, "halber Durchmesser")
    assert grenze_kleiner({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}, {}) == (15, "halbe kürzere Seite")
    assert grenze_kleiner({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30, "radius": 4}}, {}) == (4, "Eckradius")
    assert grenze_kleiner({"langloch": {"mitte": [0, 0], "laenge": 30, "breite": 8}}, {}) == (4, "halbe Breite")
    assert grenze_kleiner({"polygon": {"punkte": [[0, 0], [10, 0], [0, 10]]}}, {}) is None


def _flaeche_versetzt(element, d: float) -> float:
    a, p, k = querschnitt_koeffizienten(element, {})
    return a + p * d + k * d * d


def test_koeffizienten_rechteck_kreis_langloch():
    assert _flaeche_versetzt({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}, 2) == pytest.approx(44 * 34)
    assert _flaeche_versetzt({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, -3) == pytest.approx(math.pi * 49)
    r = {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30, "radius": 5}}
    assert _flaeche_versetzt(r, -2) == pytest.approx(36 * 26 - (4 - math.pi) * 9)
    langloch = {"langloch": {"mitte": [0, 0], "laenge": 30, "breite": 10}}
    assert _flaeche_versetzt(langloch, 1) == pytest.approx(30 * 12 + math.pi * 36)


def test_koeffizienten_polygon():
    rho = 10.0  # Inkreisradius eines regelmäßigen Sechsecks
    ecken = [(2 * rho / math.sqrt(3) * math.cos(math.radians(60 * k)), 2 * rho / math.sqrt(3) * math.sin(math.radians(60 * k)))
             for k in range(6)]
    sechseck = {"polygon": {"punkte": [list(e) for e in ecken]}}
    assert _flaeche_versetzt(sechseck, 2) == pytest.approx(2 * math.sqrt(3) * 12**2)
    quadrat = {"polygon": {"punkte": [[0, 0], [0, 10], [10, 10], [10, 0]]}}  # im Uhrzeigersinn
    assert _flaeche_versetzt(quadrat, -1) == pytest.approx(64)
    assert querschnitt_koeffizienten({"polygon": {"punkte": [[0, 0], [10, 0], [10, 10]], "radien": 2}}, {}) is None
    konkav = {"polygon": {"punkte": [[0, 0], [10, 0], [10, 10], [5, 3], [0, 10]]}}
    assert querschnitt_koeffizienten(konkav, {}) is None
    kontur = {"kontur": {"start": [0, 0], "segmente": [{"linie": [10, 0]}, {"linie": [0, 0]}]}}
    assert querschnitt_koeffizienten(kontur, {}) is None


def test_volumen_kegelstumpf_und_prismatoid():
    t = math.tan(math.radians(15))
    r1, r2 = 10, 10 - 12 * t
    kreis = querschnitt_koeffizienten({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {})
    assert volumen(kreis, 12, 15, "kleiner") == pytest.approx(math.pi * 12 / 3 * (r1 * r1 + r1 * r2 + r2 * r2))
    rechteck = querschnitt_koeffizienten({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}, {})
    d = 8 * math.tan(math.radians(10))
    a1, am, a2 = 40 * 30, (40 + d) * (30 + d), (40 + 2 * d) * (30 + 2 * d)
    assert volumen(rechteck, 8, 10, "groesser") == pytest.approx(8 / 6 * (a1 + 4 * am + a2))


def test_volumen_mittig_zwei_haelften():
    k = querschnitt_koeffizienten({"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}, {})
    assert volumen(k, 20, 5, "kleiner", mittig=True) == pytest.approx(2 * volumen(k, 10, 5, "kleiner"))


def test_volumen_feature():
    s = {"winkel": "=W", "querschnitt": "kleiner"}
    f = _feature({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {"typ": "blind", "tiefe": 12, "formschraege": s})
    v, grund = volumen_feature(f, {"W": 15})
    assert grund == "analytisch"
    kreis = querschnitt_koeffizienten({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {})
    assert v == pytest.approx(volumen(kreis, 12, 15, "kleiner"))
    f["ende"] = {"typ": "durch_alles", "formschraege": s}
    assert volumen_feature(f, {"W": 15}) == (None, "f2: ende durch_alles mit Formschräge (Tiefe hängt von der Geometrie ab)")
    f["ende"] = {"typ": "blind", "tiefe": 12, "formschraege": s}
    f["skizze"]["elemente"].append({"kreis": {"mitte": [0, 0], "durchmesser": 8}})
    assert volumen_feature(f, {"W": 15})[0] is None


def _normale(winkel: float, nach_oben: bool) -> tuple[float, float, float]:
    """Äußere Normale einer um winkel geneigten Seitenwand mit Blick nach +x; r = +y."""
    a = math.radians(winkel)
    return (math.cos(a), math.sin(a) if nach_oben else -math.sin(a), 0.0)


def test_seitenflaechen_ohne_deckflaechen():
    r = (0.0, 1.0, 0.0)
    messungen = [((10.0, 5.0, 0.0), _normale(15, True)), ((0.0, 12.0, 0.0), (0.0, 1.0, 0.0)),
                 ((0.0, 0.0, 0.0), (0.0, -1.0, 0.0)), ((-10.0, 5.0, 0.0), _normale(15, False))]
    assert seitenflaechen(messungen, r) == [{"winkel": pytest.approx(15), "vorzeichen": 1},
                                            {"winkel": pytest.approx(15), "vorzeichen": -1}]


def test_seitenflaechen_gerade_wand():
    assert seitenflaechen([((10.0, 5.0, 0.0), (1.0, 0.0, 0.0))], (0.0, 1.0, 0.0)) == [{"winkel": 0.0, "vorzeichen": 0}]


def test_seitenflaechen_mittig_misst_je_seite_von_der_ebene_weg():
    r = (0.0, 1.0, 0.0)
    oben = ((10.0, 4.0, 0.0), _normale(5, True))  # verjüngt sich nach +y
    unten = ((10.0, -4.0, 0.0), _normale(5, False))  # verjüngt sich nach −y
    assert [x["vorzeichen"] for x in seitenflaechen([oben, unten], r, (0.0, 0.0, 0.0))] == [1, 1]
    assert [x["vorzeichen"] for x in seitenflaechen([oben, unten], r)] == [1, -1]
```

- [ ] **Step 2: Test laufen lassen, er scheitert**

Run: `.venv\Scripts\python.exe -m pytest -q tests\test_formschraege.py`
Expected: FAIL – `1 error` (`ModuleNotFoundError: No module named 'swki.formschraege'`).

- [ ] **Step 3: Modul schreiben**

`swki/formschraege.py` anlegen:

```python
"""Formschräge an Extrusion und Schnitt (Paket Formschräge, Spec 2026-10-07): Richtung, Soll-Vorzeichen, versetzter
Querschnitt, Zusammenfall des Profils. Reine Rechnung ohne SolidWorks; Längen in mm, Winkel in Grad.

Bedeutung (Spec §3): r zeigt von der Skizzenebene weg ins Feature (Aufsatz: Wachstumsrichtung, Schnitt: Schnittrichtung).
querschnitt "kleiner": der extrudierte Bereich (Material beim Aufsatz, Aussparung beim Schnitt) wird entlang r kleiner,
"groesser": er wächst.
"""

import math

from swki.compiler.anker import RICHTUNGEN, Vektor, differenz, skalar
from swki.spec.ausdruck import auswerten

TYPEN = ("extrusion", "schnitt")
STANDARDNORMALE: dict[str, Vektor] = {"vorne": (0.0, 0.0, 1.0), "oben": (0.0, 1.0, 0.0), "rechts": (1.0, 0.0, 0.0)}
_QUER = 1e-6  # |cos| unter dem eine Richtung quer zur Extrusionsrichtung liegt
_PARALLEL = 1.0 - 1e-6  # |cos| ab dem eine Flächennormale parallel zu r liegt (Deck- und Bodenfläche)


def schraege(f: dict) -> dict | None:
    """formschraege-Angabe eines extrusion-/schnitt-Knotens, sonst None."""
    if f.get("typ") not in TYPEN:
        return None
    return f.get("ende", {}).get("formschraege")


def skizzennormale(ebene) -> Vektor | None:
    """Normale der Skizzenebene aus der Spezifikation (Standardebene, Versatzebene, Flächenanker mit Richtung);
    None bei {nahe: …} – die Normale kennt dann erst das Modell."""
    if isinstance(ebene, str):
        return STANDARDNORMALE[ebene]
    if "versatz" in ebene:
        return STANDARDNORMALE[ebene["versatz"]["ebene"]]
    if "flaeche" in ebene:
        return RICHTUNGEN[ebene["flaeche"]]
    return None


def extrusionsrichtung(normale: Vektor, typ: str, umkehren: bool) -> Vektor:
    """r: ein Aufsatz wächst mit der Skizzennormale, ein Schnitt geht dagegen; umkehren dreht beides (wie der Handler)."""
    gegen = (typ == "schnitt") != bool(umkehren)
    return tuple(-c for c in normale) if gegen else tuple(normale)


def soll_vorzeichen(typ: str, querschnitt: str) -> int:
    """Soll-Vorzeichen von n·r je Seitenfläche (n äußere Normale des Körpers), Spec §6.1: Aufsatz kleiner +1,
    Aufsatz groesser −1, Schnitt kleiner −1, Schnitt groesser +1."""
    return 1 if (querschnitt == "kleiner") == (typ == "extrusion") else -1


def quer_zur_richtung(richtung: str, normale: Vektor) -> bool:
    """True, wenn die Achsrichtung "+x" … "-z" senkrecht zur Extrusionsrichtung steht (Seitenfläche)."""
    return abs(skalar(RICHTUNGEN[richtung], normale)) < _QUER


def feste_tiefe(ende: dict, parameter: dict) -> float | None:
    """Tiefe T einer Seite: blind = tiefe, mittig = tiefe/2; bei anderen Endbedingungen hängt sie von der Geometrie ab."""
    if ende["typ"] == "blind":
        return auswerten(ende["tiefe"], parameter)
    if ende["typ"] == "mittig":
        return auswerten(ende["tiefe"], parameter) / 2
    return None


def grenze_kleiner(element: dict, parameter: dict) -> tuple[float, str] | None:
    """Größter Einzug (mm), bevor ein Profil bei querschnitt "kleiner" zusammenfällt, und das maßgebende Maß (Spec §5.2);
    None für Profile ohne Vorabprüfung (Polygon, Kontur)."""
    if "kreis" in element:
        return auswerten(element["kreis"]["durchmesser"], parameter) / 2, "halber Durchmesser"
    if "rechteck" in element:
        r = element["rechteck"]
        radius = auswerten(r.get("radius", 0), parameter)
        if radius > 0:
            return radius, "Eckradius"
        return min(auswerten(r["breite"], parameter), auswerten(r["hoehe"], parameter)) / 2, "halbe kürzere Seite"
    if "langloch" in element:
        return auswerten(element["langloch"]["breite"], parameter) / 2, "halbe Breite"
    return None


def _konvexes_polygon(punkte: list[tuple[float, float]]) -> tuple[float, float, float] | None:
    """A, P, K eines konvexen Polygons mit scharfen Ecken; K = Σ tan(θᵢ/2) mit dem Außenwinkel θᵢ je Ecke."""
    n = len(punkte)
    kreuz = []
    for k in range(n):
        (xa, ya), (xb, yb), (xc, yc) = punkte[k - 1], punkte[k], punkte[(k + 1) % n]
        kreuz.append((xb - xa) * (yc - yb) - (yb - ya) * (xc - xb))
    if not (all(c > 0 for c in kreuz) or all(c < 0 for c in kreuz)):
        return None
    flaeche = abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(punkte, punkte[1:] + punkte[:1]))) / 2
    umfang = sum(math.dist(punkte[k], punkte[(k + 1) % n]) for k in range(n))
    k_summe = 0.0
    for k in range(n):
        a, b, c = punkte[k - 1], punkte[k], punkte[(k + 1) % n]
        v1, v2 = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
        cos_theta = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))
        k_summe += math.tan(math.acos(max(-1.0, min(1.0, cos_theta))) / 2)
    return flaeche, umfang, k_summe


def querschnitt_koeffizienten(element: dict, parameter: dict) -> tuple[float, float, float] | None:
    """A, P, K des um d nach außen versetzten Querschnitts A(d) = A + P·d + K·d² (Spec §6.2); None, wenn das Profil
    nicht analytisch ist (Kontur, Polygon mit Radien oder nicht konvex)."""
    p = parameter
    if "kreis" in element:
        d = auswerten(element["kreis"]["durchmesser"], p)
        return math.pi * d * d / 4, math.pi * d, math.pi
    if "rechteck" in element:
        r = element["rechteck"]
        b, h, radius = auswerten(r["breite"], p), auswerten(r["hoehe"], p), auswerten(r.get("radius", 0), p)
        k = math.pi if radius > 0 else 4.0
        return b * h - (4 - math.pi) * radius**2, 2 * (b + h) - (8 - 2 * math.pi) * radius, k
    if "langloch" in element:
        laenge, breite = auswerten(element["langloch"]["laenge"], p), auswerten(element["langloch"]["breite"], p)
        return laenge * breite + math.pi * breite**2 / 4, 2 * laenge + math.pi * breite, math.pi
    if "polygon" in element:
        poly = element["polygon"]
        radien = poly.get("radien", 0)
        if any(auswerten(r, p) != 0 for r in (radien if isinstance(radien, list) else [radien])):
            return None
        return _konvexes_polygon([(auswerten(u, p), auswerten(v, p)) for u, v in poly["punkte"]])
    return None


def volumen(koeffizienten: tuple[float, float, float], tiefe: float, winkel: float, querschnitt: str,
            mittig: bool = False) -> float:
    """Volumen (mm³) eines geschrägten Features: ∫ A(±h·tan α) dh über die Tiefe; bei mittig zwei Hälften tiefe/2."""
    a, p, k = koeffizienten
    t = math.tan(math.radians(winkel))
    s = 1 if querschnitt == "groesser" else -1

    def seite(h: float) -> float:
        return a * h + s * p * t * h * h / 2 + k * t * t * h**3 / 3

    return 2 * seite(tiefe / 2) if mittig else seite(tiefe)


def volumen_feature(f: dict, parameter: dict) -> tuple[float | None, str]:
    """Sollvolumen eines extrusion-/schnitt-Knotens mit formschraege (blind oder mittig); (None, Grund) sonst."""
    s, ende = schraege(f), f["ende"]
    if ende["typ"] not in ("blind", "mittig"):
        return None, f"{f['id']}: ende {ende['typ']} mit Formschräge (Tiefe hängt von der Geometrie ab)"
    elemente = f["skizze"]["elemente"]
    if len(elemente) != 1:
        return None, f"{f['id']}: Formschräge mit mehreren Profilen nicht analytisch"
    koeffizienten = querschnitt_koeffizienten(elemente[0], parameter)
    if koeffizienten is None:
        return None, f"{f['id']}: Formschräge mit diesem Profil nicht analytisch (Kreis, Rechteck, Langloch, konvexes Polygon)"
    v = volumen(koeffizienten, auswerten(ende["tiefe"], parameter), auswerten(s["winkel"], parameter), s["querschnitt"],
                mittig=ende["typ"] == "mittig")
    return v, "analytisch"


def seitenflaechen(messungen: list[tuple[Vektor, Vektor]], r: Vektor, ebenenpunkt: Vektor | None = None) -> list[dict]:
    """Winkel (Grad) und Vorzeichen von n·r je Seitenfläche aus (Punkt in mm, äußere Einheitsnormale) – Spec §6.1.
    Flächen mit Normale parallel zu r (Deck- und Bodenflächen) zählen nicht. ebenenpunkt (nur bei mittig): Punkt der
    Skizzenebene; Flächen hinter der Skizzenebene messen gegen −r. Vorzeichen 0 = Wand ohne Schräge."""
    ergebnis = []
    for punkt, n in messungen:
        c = skalar(n, r)
        if abs(c) > _PARALLEL:
            continue
        if ebenenpunkt is not None and skalar(differenz(punkt, ebenenpunkt), r) < 0:
            c = -c
        ergebnis.append({"winkel": round(math.degrees(math.asin(min(1.0, abs(c)))), 6),
                         "vorzeichen": 0 if abs(c) < 1e-9 else (1 if c > 0 else -1)})
    return ergebnis
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\test_formschraege.py` → `24 passed`. Ganze Suite: **984 passed, 141 deselected**.

- [ ] **Step 5: Commit**

```powershell
git add swki/formschraege.py tests/test_formschraege.py
git commit -m "formschraege: reine Rechnung – Richtung, Soll-Vorzeichen, versetzter Querschnitt, Seitenflächen (Task 1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Schema, `validieren` und Sollvolumen (ohne SolidWorks)

**Files:**
- Modify: `schema/teil.schema.json`, `swki/spec/laden.py`, `swki/pruefung/geometrie.py`
- Test: `tests/spec/test_formschraege_spec.py`

**Interfaces:**
- Consumes: Task 1 (`schraege`, `skizzennormale`, `quer_zur_richtung`, `feste_tiefe`, `grenze_kleiner`, `volumen_feature`).
- Produces: Schema-Eigenschaft `ende.formschraege` (`winkel`, `querschnitt`); Befunde in `plausibel_befunde`
  (Winkelbereich, `Profil fällt zusammen`, Anker an schrägen Features); `volumen_auto` mit Formschräge.

- [ ] **Step 1: Test schreiben**

`tests/spec/test_formschraege_spec.py` anlegen:

```python
"""Format und Validieren der Option formschraege (Spec Formschräge §3, §5), Hinweise und Sollvolumen (§6.2)."""

import copy
import math

import pytest

from swki.formschraege import querschnitt_koeffizienten, volumen
from swki.pruefung.geometrie import volumen_auto
from swki.spec.hinweise import feste_masse
from swki.spec.laden import plausibel_befunde, schema_befunde

PLATTE = {
    "art": "teil", "name": "Aufnahme", "material": "1.0503", "eigenschaften": {"Benennung": "Aufnahme"},
    "parameter": {"L": 100, "B": 60, "H": 20, "DZ": 20, "HZ": 12, "WZ": 15},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}},
        {"id": "zapfen", "typ": "extrusion",
         "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                    "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": "=DZ"}}]},
         "ende": {"typ": "blind", "tiefe": "=HZ", "formschraege": {"winkel": "=WZ", "querschnitt": "kleiner"}}},
    ],
    "pruefung": {"volumen": {"soll": "auto"}},
}


def _mit(*features, **parameter) -> dict:
    neu = copy.deepcopy(PLATTE)
    neu["features"] += list(features)
    neu["parameter"].update(parameter)
    return neu


def _schraege(**ende) -> dict:
    neu = copy.deepcopy(PLATTE)
    neu["features"][1]["ende"]["formschraege"].update(ende)
    return neu


def _meldungen(spec: dict, tmp_path) -> list[str]:
    return [b["meldung"] for b in schema_befunde(spec) + plausibel_befunde(spec, tmp_path)]


def test_gueltige_formschraege(tmp_path):
    assert _meldungen(PLATTE, tmp_path) == []


def test_schema_querschnitt_und_pflichtfelder():
    assert schema_befunde(_schraege(querschnitt="innen"))
    ohne_winkel = copy.deepcopy(PLATTE)
    del ohne_winkel["features"][1]["ende"]["formschraege"]["winkel"]
    assert schema_befunde(ohne_winkel)
    assert schema_befunde(_schraege(neutral="oben"))


@pytest.mark.parametrize("winkel", [0, 90, 120, -5])
def test_winkel_ausserhalb(tmp_path, winkel):
    spec = _mit(WZ=winkel)
    befunde = plausibel_befunde(spec, tmp_path)
    assert [b["pfad"] for b in befunde if "(0, 90)" in b["meldung"]] == ["features[1].ende.formschraege.winkel"]


def test_profil_faellt_zusammen_kreis(tmp_path):
    # Einzug 12 · tan 40° = 10,07 mm ≥ halber Durchmesser 10 mm
    befunde = plausibel_befunde(_mit(WZ=40), tmp_path)
    assert [b["pfad"] for b in befunde] == ["features[1].ende.formschraege"]
    assert "halber Durchmesser 10 mm" in befunde[0]["meldung"]
    assert plausibel_befunde(_mit(WZ=39), tmp_path) == []
    assert plausibel_befunde(_schraege(querschnitt="groesser", winkel=60), tmp_path) == []


def test_profil_faellt_zusammen_eckradius_und_mittig(tmp_path):
    tasche = {"id": "tasche", "typ": "schnitt",
              "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                         "elemente": [{"rechteck": {"mitte": [30, 0], "breite": 30, "hoehe": 20, "radius": 3}}]},
              "ende": {"typ": "blind", "tiefe": 10, "formschraege": {"winkel": 20, "querschnitt": "kleiner"}}}
    befunde = plausibel_befunde(_mit(tasche), tmp_path)  # 10 · tan 20° = 3,64 ≥ Eckradius 3
    assert [b["pfad"] for b in befunde] == ["features[2].ende.formschraege"]
    assert "Eckradius 3 mm" in befunde[0]["meldung"]
    steg = copy.deepcopy(tasche) | {"id": "steg", "typ": "extrusion"}
    steg["ende"] = {"typ": "mittig", "tiefe": 16, "formschraege": {"winkel": 20, "querschnitt": "kleiner"}}
    assert plausibel_befunde(_mit(steg), tmp_path) == []  # je Seite 8 · tan 20° = 2,91 < 3
    durch = copy.deepcopy(tasche)
    durch["ende"] = {"typ": "durch_alles", "formschraege": {"winkel": 20, "querschnitt": "kleiner"}}
    assert plausibel_befunde(_mit(durch), tmp_path) == []  # Tiefe unbekannt: keine Vorabprüfung


def test_anker_quer_zur_extrusion(tmp_path):
    fase = {"id": "fase", "typ": "fase", "kanten": [{"feature": "zapfen", "kanten_an": "+x"}], "abstand": 1}
    rundung = {"id": "rund", "typ": "verrundung", "kanten": [{"feature": "zapfen", "auswahl": "senkrechte_kanten"}],
               "radius": 1}
    bohrung = {"id": "b1", "typ": "bohrung", "flaeche": {"feature": "zapfen", "flaeche": "-z"}, "positionen": [[0, 5]],
               "durchmesser": 3, "tiefe": 2}
    befunde = plausibel_befunde(_mit(fase, rundung, bohrung), tmp_path)
    assert [b["pfad"] for b in befunde] == ["features[2].kanten[0].kanten_an", "features[3].kanten[0].auswahl",
                                             "features[4].flaeche.flaeche"]
    assert "{nahe: [x, y, z]}" in befunde[0]["meldung"]
    assert "Eckradius in der Skizze" in befunde[1]["meldung"]


def test_anker_parallel_und_ohne_formschraege_bleiben_erlaubt(tmp_path):
    deckel = {"id": "b1", "typ": "bohrung", "flaeche": {"feature": "zapfen", "flaeche": "+y"}, "positionen": [[0, 0]],
              "durchmesser": 3, "tiefe": 2}
    seite_f1 = {"id": "b2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+x"}, "positionen": [[0, 10]],
                "durchmesser": 3, "tiefe": 2}
    rundung = {"id": "rund", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}],
               "radius": 1}
    assert plausibel_befunde(_mit(deckel, seite_f1, rundung), tmp_path) == []


def test_anker_in_pruefung(tmp_path):
    spec = _mit()
    spec["pruefung"]["masse_pruefen"] = [{"was": "Seite", "von": {"feature": "zapfen", "flaeche": "+z"},
                                          "zu": {"feature": "f1", "flaeche": "-z"}, "soll": 10}]
    befunde = plausibel_befunde(spec, tmp_path)
    assert [b["pfad"] for b in befunde] == ["pruefung.masse_pruefen[0].von.flaeche"]


def test_fester_winkel_ist_hinweis():
    spec = _schraege(winkel=15)
    assert [h["pfad"] for h in feste_masse(spec) if "formschraege" in h["pfad"]] == [
        "features[1].ende.formschraege.winkel"]
    assert [h for h in feste_masse(PLATTE) if "formschraege" in h["pfad"]] == []


def test_sollvolumen_mit_formschraege():
    v, grund = volumen_auto(PLATTE)
    assert grund == "analytisch"
    t = math.tan(math.radians(15))
    r1, r2 = 10, 10 - 12 * t
    assert v == pytest.approx(100 * 60 * 20 + math.pi * 12 / 3 * (r1 * r1 + r1 * r2 + r2 * r2))


def test_sollvolumen_mittig_und_schnitt():
    steg = {"id": "steg", "typ": "extrusion",
            "skizze": {"ebene": "vorne", "elemente": [{"rechteck": {"mitte": [0, 30], "breite": 40, "hoehe": 10}}]},
            "ende": {"typ": "mittig", "tiefe": 8, "formschraege": {"winkel": 5, "querschnitt": "kleiner"}}}
    tasche = {"id": "tasche", "typ": "schnitt",
              "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                         "elemente": [{"rechteck": {"mitte": [30, 0], "breite": 30, "hoehe": 20, "radius": 4}}]},
              "ende": {"typ": "blind", "tiefe": 8, "formschraege": {"winkel": 10, "querschnitt": "kleiner"}}}
    v, _ = volumen_auto(_mit(steg, tasche))
    zapfen = volumen(querschnitt_koeffizienten({"kreis": {"mitte": [0, 0], "durchmesser": 20}}, {}), 12, 15, "kleiner")
    k_steg = querschnitt_koeffizienten(steg["skizze"]["elemente"][0], {})
    k_tasche = querschnitt_koeffizienten(tasche["skizze"]["elemente"][0], {})
    erwartet = 100 * 60 * 20 + zapfen + volumen(k_steg, 8, 5, "kleiner", mittig=True) - volumen(k_tasche, 8, 10, "kleiner")
    assert v == pytest.approx(erwartet)


def test_sollvolumen_nicht_analytisch():
    trichter = {"id": "trichter", "typ": "schnitt",
                "skizze": {"ebene": {"feature": "f1", "flaeche": "-y"},
                           "elemente": [{"kreis": {"mitte": [-30, 0], "durchmesser": 8}}]},
                "ende": {"typ": "durch_alles", "formschraege": {"winkel": 20, "querschnitt": "groesser"}}}
    assert volumen_auto(_mit(trichter)) == (None, "trichter: durch_alles")
    ring = copy.deepcopy(PLATTE)
    ring["features"][1]["skizze"]["elemente"].append({"kreis": {"mitte": [0, 0], "durchmesser": 6}})
    assert volumen_auto(ring) == (None, "zapfen: Formschräge mit mehreren Profilen nicht analytisch")


def test_unbekannter_parameter_im_winkel(tmp_path):
    befunde = plausibel_befunde(_schraege(winkel="=WX"), tmp_path)
    assert [b["pfad"] for b in befunde] == ["features[1].ende.formschraege.winkel"]
    assert "WX" in befunde[0]["meldung"]


def test_skizze_auf_nahe_ohne_ankerpruefung(tmp_path):
    spec = _mit({"id": "fase", "typ": "fase", "kanten": [{"feature": "zapfen", "kanten_an": "+x"}], "abstand": 1})
    spec["features"][1]["skizze"]["ebene"] = {"nahe": [0, 20, 0]}  # Normale erst im Modell bekannt
    assert plausibel_befunde(spec, tmp_path) == []


def test_ring_mit_kleiner_ohne_vorabpruefung(tmp_path):
    ring = copy.deepcopy(PLATTE)
    ring["features"][1]["skizze"]["elemente"].append({"kreis": {"mitte": [0, 0], "durchmesser": 6}})
    ring["parameter"]["WZ"] = 45  # beim einzelnen Kreis fiele das Profil zusammen
    assert plausibel_befunde(ring, tmp_path) == []
```

- [ ] **Step 2: Test laufen lassen, er scheitert**

Run: `.venv\Scripts\python.exe -m pytest -q tests\spec\test_formschraege_spec.py`
Expected: FAIL – `12 failed, 6 passed` (Schema kennt `formschraege` nicht; die sechs bestehenden Tests sichern ab, dass
gültige Anker, der Hinweis `feste_zahl` und Ausdrucksfehler schon heute richtig laufen).

- [ ] **Step 3: Schema**

In `schema/teil.schema.json` ersetzen:

```json
        "abstand": {"$ref": "#/$defs/wert"}
      },
      "allOf": [
        {"if": {"properties": {"typ": {"enum": ["blind", "mittig"]}}}, "then": {"required": ["tiefe"]}},
```

durch:

```json
        "abstand": {"$ref": "#/$defs/wert"},
        "formschraege": {
          "type": "object", "required": ["winkel", "querschnitt"], "additionalProperties": false,
          "properties": {"winkel": {"$ref": "#/$defs/wert"}, "querschnitt": {"enum": ["kleiner", "groesser"]}}
        }
      },
      "allOf": [
        {"if": {"properties": {"typ": {"enum": ["blind", "mittig"]}}}, "then": {"required": ["tiefe"]}},
```

- [ ] **Step 4: `validieren`**

In `swki/spec/laden.py` ersetzen:

```python
from swki.compiler.skriptpruefung import pruefe_skript
from swki.konfig import PROJEKT
```

durch:

```python
from swki.compiler.anker import RICHTUNGEN
from swki.compiler.skriptpruefung import pruefe_skript
from swki.formschraege import feste_tiefe, grenze_kleiner, quer_zur_richtung, schraege, skizzennormale
from swki.konfig import PROJEKT
```

In `swki/spec/laden.py` ersetzen:

```python
def _normbohrung_befunde(f: dict, pfad: str, p: dict) -> list[dict]:
```

durch:

```python
def _formschraege_befunde(f: dict, pfad: str, p: dict) -> list[dict]:
    """Spec Formschräge §5.2: Bei querschnitt "kleiner" und bekannter Tiefe darf ein einzelnes Profil (Kreis, Rechteck,
    Langloch) nicht zusammenfallen. Den Winkelbereich prüft die allgemeine Winkelprüfung."""
    s = schraege(f)
    if s is None or s["querschnitt"] != "kleiner" or len(f["skizze"]["elemente"]) != 1:
        return []
    try:
        winkel, tiefe = auswerten(s["winkel"], p), feste_tiefe(f["ende"], p)
        grenze = grenze_kleiner(f["skizze"]["elemente"][0], p)
    except AusdruckFehler:
        return []  # bereits oben gemeldet
    if tiefe is None or grenze is None or not 0 < winkel < 90:
        return []
    einzug = tiefe * math.tan(math.radians(winkel))
    if einzug < grenze[0]:
        return []
    return [{"pfad": f"{pfad}.ende.formschraege",
             "meldung": f"Profil fällt zusammen: Einzug {einzug:.4g} mm (Tiefe {tiefe:g} · tan {winkel:g}°) erreicht "
                        f"{grenze[1]} {grenze[0]:g} mm – Winkel oder Tiefe verkleinern"}]


def _anker(obj, pfad: list):
    """Liefert (pfad, anker) für alle Objekte mit einem Feature-Verweis "feature" (Flächen-, Kanten-, Messanker)."""
    if isinstance(obj, dict):
        if isinstance(obj.get("feature"), str):
            yield pfad, obj
        for k, v in obj.items():
            yield from _anker(v, [*pfad, k])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _anker(v, [*pfad, i])


def _schraege_anker_befunde(spec: dict) -> list[dict]:
    """Spec Formschräge §5.3: Seitenflächen eines Features mit Formschräge sind nicht achsparallel – Richtungsanker quer
    zur Extrusionsrichtung und senkrechte_kanten finden dort nichts."""
    normalen = {f["id"]: n for f in spec["features"]
                if schraege(f) is not None and (n := skizzennormale(f["skizze"]["ebene"])) is not None}
    befunde = []
    for pfad, anker in _anker({k: v for k, v in spec.items() if k in ("features", "pruefung")}, []):
        fid = anker["feature"]
        if fid not in normalen:
            continue
        for schluessel in ("flaeche", "kanten_an"):
            richtung = anker.get(schluessel)
            if richtung in RICHTUNGEN and quer_zur_richtung(richtung, normalen[fid]):
                befunde.append({"pfad": _pfad([*pfad, schluessel]),
                                "meldung": f"{fid} hat eine Formschräge: seine Seitenflächen sind geschrägt, {richtung!r} "
                                           "findet keine Fläche – die Fläche mit {nahe: [x, y, z]} ansprechen"})
        if anker.get("auswahl") == "senkrechte_kanten":
            befunde.append({"pfad": _pfad([*pfad, "auswahl"]),
                            "meldung": f"{fid} hat eine Formschräge: es gibt keine senkrechten Kanten – Ecken mit "
                                       "Eckradius in der Skizze runden oder alle_kanten/kanten_an/nahe verwenden"})
    return befunde


def _normbohrung_befunde(f: dict, pfad: str, p: dict) -> list[dict]:
```

In `swki/spec/laden.py` ersetzen:

```python
        elif schluessel in _WINKEL and _in_verzahnung(spec, pfad):
```

durch:

```python
        elif schluessel in _WINKEL and "formschraege" in pfad:
            if not 0 < wert < 90:
                befunde.append({"pfad": _pfad(pfad), "meldung": f"formschraege.winkel muss in (0, 90) liegen (ist {wert:g})"})
        elif schluessel in _WINKEL and _in_verzahnung(spec, pfad):
```

In `swki/spec/laden.py` ersetzen:

```python
        if "ende" in f:
            befunde += _ende_befunde(f["ende"], f"features[{i}].ende")
```

durch:

```python
        if "ende" in f:
            befunde += _ende_befunde(f["ende"], f"features[{i}].ende")
            befunde += _formschraege_befunde(f, f"features[{i}]", parameter)
```

In `swki/spec/laden.py` ersetzen:

```python
                                       "deckungsgleich zur Basisebene)"})
    return befunde
```

durch:

```python
                                       "deckungsgleich zur Basisebene)"})
    befunde += _schraege_anker_befunde(spec)
    return befunde
```

- [ ] **Step 5: Sollvolumen**

In `swki/pruefung/geometrie.py` ersetzen:

```python
from swki.compiler.anker import Vektor, differenz, laenge, punkt_achse_abstand, skalar
from swki.spec.ausdruck import auswerten
```

durch:

```python
from swki.compiler.anker import Vektor, differenz, laenge, punkt_achse_abstand, skalar
from swki.formschraege import schraege, volumen_feature
from swki.spec.ausdruck import auswerten
```

In `swki/pruefung/geometrie.py` ersetzen:

```python
    Kennt Rundungen, Langloch, Kontur, Normbohrung mit Tiefe; bis_flaeche/versatz_von_flaeche und Normbohrung durch
    sind nicht berechenbar."""
```

durch:

```python
    Kennt Rundungen, Langloch, Kontur, Normbohrung mit Tiefe, Formschräge an einem Profil (swki.formschraege);
    bis_flaeche/versatz_von_flaeche und Normbohrung durch sind nicht berechenbar."""
```

In `swki/pruefung/geometrie.py` ersetzen:

```python
            if ende["typ"] in ("bis_flaeche", "versatz_von_flaeche"):
                return None, f"{f['id']}: ende {ende['typ']} (Tiefe hängt von der Geometrie ab)"
            flaechen = [_flaeche(e, p) for e in f["skizze"]["elemente"]]
            v = sum(flaechen) * auswerten(ende["tiefe"], p)
```

durch:

```python
            if ende["typ"] in ("bis_flaeche", "versatz_von_flaeche"):
                return None, f"{f['id']}: ende {ende['typ']} (Tiefe hängt von der Geometrie ab)"
            if schraege(f) is not None:
                v, grund = volumen_feature(f, p)
                if v is None:
                    return None, grund
            else:
                v = sum(_flaeche(e, p) for e in f["skizze"]["elemente"]) * auswerten(ende["tiefe"], p)
```

- [ ] **Step 6: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\spec\test_formschraege_spec.py` → `18 passed`. Ganze Suite: **1002 passed, 141 deselected**.

- [ ] **Step 7: Commit**

```powershell
git add schema/teil.schema.json swki/spec/laden.py swki/pruefung/geometrie.py tests/spec/test_formschraege_spec.py
git commit -m "spec: Option formschraege – Schema, Winkelbereich, Zusammenfall, Anker an schrägen Features, Sollvolumen (Task 2)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Handler `extrusion`/`schnitt` (ohne SolidWorks geprüft)

**Files:**
- Modify: `swki/compiler/handler/extrusion.py` (vollständig ersetzen; `aufsatz`/`schnitt` behalten ihre bisherige Signatur, der neue Parameter hat eine Vorgabe – `bohrung.py`, `verzahnung.py`, `spikes/s14a_verzahnung.py` bleiben unverändert)
- Test: `tests/compiler/test_extrusion_schraege.py`

**Interfaces:**
- Consumes: Task 1 (`schraege`), `Kontext.rad`, `Kontext.verknuepfe`.
- Produces: `DDIR_KLEINER`, `WINKEL_MASS` (je Endbedingung), `OHNE_SCHRAEGE = (False, False, 0.0)`,
  `aufsatz(model, typ, tiefe_m, umkehren, schraege_sw=OHNE_SCHRAEGE)`, `schnitt(…)` gleich,
  `schraege_sw(ctx, f) -> (Dchk1, Ddir1, Dang1)`. Das Modul importiert `schraege` als eigenen Namen – die Negativfälle
  (Task 7) setzen dort per monkeypatch an.

- [ ] **Step 1: Test schreiben**

`tests/compiler/test_extrusion_schraege.py` anlegen:

```python
"""Formschräge im Handler extrusion/schnitt: Parameter an FeatureExtrusion3/FeatureCut4 (ohne SolidWorks)."""

import math
from pathlib import Path

import pytest

from swki.compiler.handler.extrusion import (
    DDIR_KLEINER, ENDE, OHNE_SCHRAEGE, WINKEL_MASS, aufsatz, schnitt, schraege_sw,
)
from swki.compiler.kontext import Kontext


class _FeatureManager:
    def __init__(self):
        self.aufrufe = []

    def FeatureExtrusion3(self, *args):  # noqa: N802 – Name der SolidWorks-API
        self.aufrufe.append(("FeatureExtrusion3", args))
        return "feature"

    def FeatureCut4(self, *args):  # noqa: N802 – Name der SolidWorks-API
        self.aufrufe.append(("FeatureCut4", args))
        return "feature"


class _Model:
    def __init__(self):
        self.FeatureManager = _FeatureManager()


def _ctx(**parameter) -> Kontext:
    return Kontext(None, _Model(), {"parameter": parameter}, Path("t.yaml"), 0.1)


def _f(typ: str, querschnitt: str | None) -> dict:
    ende = {"typ": "blind", "tiefe": 10}
    if querschnitt:
        ende["formschraege"] = {"winkel": "=W", "querschnitt": querschnitt}
    return {"id": "f2", "typ": typ, "skizze": {"ebene": "oben", "elemente": []}, "ende": ende}


@pytest.mark.parametrize(("aufruf", "name", "anzahl"), [(aufsatz, "FeatureExtrusion3", 23), (schnitt, "FeatureCut4", 27)])
def test_schraege_an_index_7_9_11(aufruf, name, anzahl):
    model = _Model()
    aufruf(model, ENDE["blind"], 0.01, False, (True, True, 0.25))
    [(gerufen, args)] = model.FeatureManager.aufrufe
    assert gerufen == name and len(args) == anzahl
    assert (args[7], args[8], args[9], args[10], args[11], args[12]) == (True, False, True, False, 0.25, 0.0)


@pytest.mark.parametrize("aufruf", [aufsatz, schnitt])
def test_ohne_schraege_unveraendert(aufruf):
    model = _Model()
    aufruf(model, ENDE["blind"], 0.01, True)
    [(_, args)] = model.FeatureManager.aufrufe
    assert (args[2], args[7], args[9], args[11]) == (True, False, False, 0.0)


def test_schraege_sw():
    ctx = _ctx(W=15)
    assert schraege_sw(ctx, _f("extrusion", None)) == OHNE_SCHRAEGE
    dchk, ddir, dang = schraege_sw(ctx, _f("extrusion", "kleiner"))
    assert (dchk, ddir) == (True, DDIR_KLEINER["extrusion"]) and dang == pytest.approx(math.radians(15))
    assert schraege_sw(ctx, _f("schnitt", "groesser"))[1] is (not DDIR_KLEINER["schnitt"])


def test_winkelmass_fuer_jede_endbedingung():
    assert set(WINKEL_MASS) == set(ENDE)
```

- [ ] **Step 2: Test laufen lassen, er scheitert**

Run: `.venv\Scripts\python.exe -m pytest -q tests\compiler\test_extrusion_schraege.py`
Expected: FAIL – `1 error` (`ImportError: cannot import name 'DDIR_KLEINER'`).

- [ ] **Step 3: Handler**

`swki/compiler/handler/extrusion.py` vollständig ersetzen durch:

```python
"""Handler "extrusion" (Aufsatz) und "schnitt" (verifiziert in Spike S9a, Bausteine 6 und 7; Endbedingungen
bis_flaeche und versatz_von_flaeche in Spike S10, Frage 6).

Aufsatz wächst standardmäßig in Richtung der Skizzennormale, Schnitt standardmäßig dagegen
(von einer Deckfläche also ins Material). "umkehren" dreht die Richtung (3. Parameter Dir, nicht Flip).
Die Zielfläche von bis_flaeche/versatz_von_flaeche wird über den Flächenanker aufgelöst und mit Marke 1 zur Skizze
gewählt; der Versatz geht zur Skizze hin (z. B. Restwandstärke über der Zielfläche).

Bekannte Einschränkung: Ein Aufsatz mit versatz_von_flaeche, dessen Skizze abgesetzt über der Zielfläche liegt, ergibt
einen getrennten Körper. Der Bau meldet das nicht; die allgemeine Code-Prüfung "koerper" (swki.pruefung.bewertung)
meldet es als Mangel ("2 Volumenkörper statt 1").

Formschräge (Paket Formschräge, Spike S16): Dchk1/Ddir1/Dang1 (Index 7, 9, 11 bei beiden Aufrufen); querschnitt
"kleiner"/"groesser" aus Sicht der Skizze (swki.formschraege), der Winkel per Gleichung an WINKEL_MASS[ende] gebunden.
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import richtung, skizziere
from swki.compiler.topologie import loese_flaeche
from swki.formschraege import schraege

ENDE = {"blind": 0, "durch_alles": 1, "bis_flaeche": 4, "versatz_von_flaeche": 5, "mittig": 6}  # swEndConditions_e
MARKE_ZIELFLAECHE = 1  # Endbedingungs-Referenz (Spike S10, Frage 6)
VERSATZ_WEG_VON_SKIZZE = False  # OffsetReverse1: False = Versatz zur Skizze hin (Spike S10, Frage 6)
VERSATZ_MASS = "D1"  # Maß des Versatzes am Feature (Spike S10, Frage 6)
DDIR_KLEINER = {"extrusion": True, "schnitt": True}  # Ddir1 (True = nach innen) für querschnitt "kleiner" (Spike S16, Frage 1)
# Maß des Formschrägenwinkels am Feature je Endbedingung: ohne Tiefenmaß ist er das erste Maß (Spike S16, Frage 4)
WINKEL_MASS = {"blind": "D2", "mittig": "D2", "versatz_von_flaeche": "D2", "durch_alles": "D1", "bis_flaeche": "D1"}
OHNE_SCHRAEGE = (False, False, 0.0)  # (Dchk1, Ddir1, Dang1 in rad)


def aufsatz(model, typ: int, tiefe_m: float, umkehren: bool, schraege_sw: tuple = OHNE_SCHRAEGE):
    dchk, ddir, dang = schraege_sw
    return model.FeatureManager.FeatureExtrusion3(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, dchk, False, ddir, False, dang, 0.0,
        VERSATZ_WEG_VON_SKIZZE, False, False, False, True, True, True, 0, 0.0, False,
    )


def schnitt(model, typ: int, tiefe_m: float, umkehren: bool, schraege_sw: tuple = OHNE_SCHRAEGE):
    dchk, ddir, dang = schraege_sw
    return model.FeatureManager.FeatureCut4(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, dchk, False, ddir, False, dang, 0.0,
        VERSATZ_WEG_VON_SKIZZE, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False,
    )


def schraege_sw(ctx, f: dict) -> tuple:
    """(Dchk1, Ddir1, Dang1) eines extrusion-/schnitt-Knotens; ohne formschraege OHNE_SCHRAEGE."""
    s = schraege(f)
    if s is None:
        return OHNE_SCHRAEGE
    kleiner = s["querschnitt"] == "kleiner"
    return True, DDIR_KLEINER[f["typ"]] == kleiner, ctx.rad(s["winkel"])


@handler("extrusion", "schnitt")
def extrusion(ctx, f: dict) -> FeatureErgebnis:
    skizze, se = skizziere(ctx, f["skizze"]["ebene"], f["skizze"]["elemente"], f"{f['id']}_skizze")
    ende = f["ende"]
    typ = ENDE[ende["typ"]]
    mass = ende.get("tiefe", ende.get("abstand"))  # blind/mittig: Tiefe; versatz_von_flaeche: Versatz
    tiefe = ctx.m(mass) if mass is not None else 0.0
    ziel = loese_flaeche(ctx, ende["flaeche"]) if "flaeche" in ende else None
    umkehren = bool(ende.get("umkehren", False))
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)
    if ziel is not None:
        sw.waehle(ctx.model, ziel.objekt, MARKE_ZIELFLAECHE, anhaengen=True)
    ist_schnitt = f["typ"] == "schnitt"
    schraege_f = schraege_sw(ctx, f)
    feature = (schnitt if ist_schnitt else aufsatz)(ctx.model, typ, tiefe, umkehren, schraege_f)
    if feature is None:
        grund = " (trifft der Schnitt Material? ggf. umkehren)" if ist_schnitt else ""
        if schraege_f[0]:
            grund += " (Formschräge zu groß für das Profil?)"
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{f['typ']} {f['id']} nicht erzeugt{grund}", schritt="feature")
    feature.Name = f["id"]
    if "tiefe" in ende:
        ctx.verknuepfe(f"D1@{f['id']}", ende["tiefe"])
    if "abstand" in ende:
        ctx.verknuepfe(f"{VERSATZ_MASS}@{f['id']}", ende["abstand"])
    if "formschraege" in ende:
        ctx.verknuepfe(f"{WINKEL_MASS[ende['typ']]}@{f['id']}", schraege(f)["winkel"])
    return FeatureErgebnis([feature], richtung=richtung(se, umkehren != ist_schnitt))
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\compiler\test_extrusion_schraege.py` → `6 passed`. Ganze Suite: **1008 passed, 141 deselected**. `.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` → `"befunde": []`.

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/handler/extrusion.py tests/compiler/test_extrusion_schraege.py
git commit -m "compiler: Formschräge an Extrusion und Schnitt (Dchk1/Ddir1/Dang1, Winkel per Gleichung) (Task 3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Prüfung `formschraegen` (ohne SolidWorks geprüft)

**Files:**
- Modify: `swki/pruefung/bewertung.py`, `swki/pruefung/messen.py`, `config/standard.yaml`
- Test: `tests/pruefung/test_formschraege_pruefung.py`

**Interfaces:**
- Consumes: Task 1 (`TYPEN`, `schraege`, `skizzennormale`, `extrusionsrichtung`, `soll_vorzeichen`, `seitenflaechen`),
  `swki.compiler.topologie.loese_flaeche`, `flaeche_in_richtung`.
- Produces: `Messwerte.formschraegen: dict[str, dict | str]`; `formschraege_abweichungen(f, ist, parameter, tol_grad)
  -> list[str]`; in `bewerte` der Eintrag `formschraegen` (`ok`, `ist`, `gemessen`, `knoten`);
  `messen.punkt_und_normale(face) -> (Punkt mm, Einheitsnormale)`, `messen.formschraegen(ctx, soll_spec, aktuell_spec=None)`;
  `toleranzen.winkel_grad`.

- [ ] **Step 1: Test schreiben**

`tests/pruefung/test_formschraege_pruefung.py` anlegen:

```python
"""Prüfung formschraegen (Spec Formschräge §6.1) ohne SolidWorks: Bewertung und Messung mit Ersatzobjekten."""

import math
from pathlib import Path

import pytest

from swki.compiler.kontext import FeatureErgebnis, Kontext
from swki.pruefung.bewertung import Messwerte, bewerte, formschraege_abweichungen
from swki.pruefung.messen import formschraegen, punkt_und_normale

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5, "winkel_grad": 0.01}}
ZAPFEN = {"id": "zapfen", "typ": "extrusion",
          "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                     "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 20}}]},
          "ende": {"typ": "blind", "tiefe": 12, "formschraege": {"winkel": "=WZ", "querschnitt": "kleiner"}}}
TASCHE = {"id": "tasche", "typ": "schnitt",
          "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                     "elemente": [{"rechteck": {"mitte": [30, 0], "breite": 30, "hoehe": 20}}]},
          "ende": {"typ": "blind", "tiefe": 8, "formschraege": {"winkel": 10, "querschnitt": "kleiner"}}}
P = {"WZ": 15}


def _ist(*paare) -> dict:
    return {"flaechen": [{"winkel": w, "vorzeichen": v} for w, v in paare]}


def test_passt():
    assert formschraege_abweichungen(ZAPFEN, _ist((15.0, 1)), P, 0.01) == []
    assert formschraege_abweichungen(TASCHE, _ist(*[(10.004, -1)] * 4), P, 0.01) == []


def test_winkel_und_richtung_falsch():
    fehler = formschraege_abweichungen(TASCHE, _ist((10.0, -1), (12.0, -1), (10.0, 1), (12.0, 1)), P, 0.01)
    assert fehler == ["Winkel 12° statt 10° (2 von 4 Seitenflächen)", "Querschnitt nicht kleiner (2 von 4 Seitenflächen)"]


def test_gerade_wand_und_keine_flaeche():
    assert formschraege_abweichungen(ZAPFEN, _ist((0.0, 0)), P, 0.01) == [
        "Winkel 0° statt 15° (1 von 1 Seitenflächen)", "Querschnitt nicht kleiner (1 von 1 Seitenflächen)"]
    assert formschraege_abweichungen(ZAPFEN, _ist(), P, 0.01) == ["keine geschrägte Seitenfläche gefunden"]


def _messwerte(formschraegen: dict) -> Messwerte:
    return Messwerte(rebuild_fehler=[], skizzen={}, box=[0] * 6, volumen=1.0, schwerpunkt=(0, 0, 0), material="",
                     eigenschaften={}, formschraegen=formschraegen)


def _spec(*features) -> dict:
    return {"art": "teil", "name": "T", "parameter": dict(P), "features": list(features)}


def test_bewerte_gegen_freigegebene_kopie():
    freigegeben = _spec(ZAPFEN, TASCHE)
    nachgebessert = _spec(ZAPFEN, TASCHE | {"ende": {"typ": "blind", "tiefe": 8}})  # Bauweg ohne Schräge
    bericht = bewerte(nachgebessert, _messwerte({"zapfen": _ist((15.0, 1)), "tasche": _ist((0.0, 0))}), STANDARD,
                      freigegeben=freigegeben)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "formschraegen")
    assert pruefung["ok"] is False and pruefung["knoten"] == ["tasche"]
    assert pruefung["gemessen"] == {"zapfen": [15.0], "tasche": [0.0]}
    assert [m["knoten"] for m in bericht["maengel"] if m["pruefung"] == "formschraegen"] == [["tasche"]]


def test_bewerte_fehlendes_feature_und_ohne_formschraege():
    bericht = bewerte(_spec(ZAPFEN), _messwerte({"zapfen": "Feature zapfen fehlt im Teil"}), STANDARD)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "formschraegen")
    assert pruefung["ist"] == {"zapfen": ["Feature zapfen fehlt im Teil"]}
    ohne = _spec(TASCHE | {"ende": {"typ": "blind", "tiefe": 8}})
    assert all(p["id"] != "formschraegen" for p in bewerte(ohne, _messwerte({}), STANDARD)["pruefungen"])


class _Flaeche:
    """Ersatz für IFace2/ISurface: eine Ebene mit äußerer Normale n durch den Punkt q (Meter)."""

    def __init__(self, q, n, umgekehrt=False):
        self.q, self.n, self.FaceInSurfaceSense = q, n, umgekehrt
        self.GetBox = [q[0] - 0.001, q[1] - 0.001, q[2] - 0.001, q[0] + 0.001, q[1] + 0.001, q[2] + 0.001]
        self.GetSurface = self
        self.IsPlane, self.PlaneParams, self.Normal = True, (*n, *q), n  # für swki.compiler.topologie.flaeche_aus

    def GetClosestPointOn(self, x, y, z):  # noqa: N802 – Name der SolidWorks-API
        return (*self.q, 0.0, 0.0)

    def EvaluateAtPoint(self, x, y, z):  # noqa: N802 – Name der SolidWorks-API
        n = tuple(-c for c in self.n) if self.FaceInSurfaceSense else self.n  # Trägerfläche zeigt entgegen
        return (*n, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


class _Feature:
    def __init__(self, faces):
        self.GetFaces = faces


class _Model:
    def __init__(self, features: dict):
        self.features = features

    def FeatureByName(self, name):  # noqa: N802 – Name der SolidWorks-API
        return self.features.get(name)


def test_punkt_und_normale_beachtet_flaechensinn():
    a = math.radians(15)
    for umgekehrt in (False, True):
        punkt, n = punkt_und_normale(_Flaeche((0.01, 0.025, 0.0), (math.cos(a), math.sin(a), 0.0), umgekehrt))
        assert punkt == pytest.approx((10.0, 25.0, 0.0))
        assert n == pytest.approx((math.cos(a), math.sin(a), 0.0))


def test_formschraegen_misst_seitenflaechen():
    a = math.radians(15)
    zapfen = _Feature([_Flaeche((0.01, 0.025, 0.0), (math.cos(a), math.sin(a), 0.0), True),
                       _Flaeche((0.0, 0.032, 0.0), (0.0, 1.0, 0.0))])
    ctx = Kontext(None, _Model({"zapfen": zapfen}), _spec(ZAPFEN), Path("t.yaml"), 0.1)
    ergebnis = formschraegen(ctx, _spec(ZAPFEN, TASCHE))
    assert ergebnis["zapfen"] == {"flaechen": [{"winkel": pytest.approx(15), "vorzeichen": 1}]}
    assert ergebnis["tasche"] == "Feature tasche fehlt im Teil"


def test_formschraegen_mittig_braucht_ebenenpunkt():
    steg = {"id": "steg", "typ": "extrusion",
            "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
                       "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 10}}]},
            "ende": {"typ": "mittig", "tiefe": 8, "formschraege": {"winkel": 5, "querschnitt": "kleiner"}}}
    ctx = Kontext(None, _Model({"steg": _Feature([])}), _spec(steg), Path("t.yaml"), 0.1)
    assert formschraegen(ctx, _spec(steg))["steg"].startswith("REFERENZ_NICHT_GEFUNDEN")
    ctx.ergebnisse["f1"] = FeatureErgebnis([_Feature([_Flaeche((0.0, 0.02, 0.0), (0.0, 1.0, 0.0))])])
    assert formschraegen(ctx, _spec(steg))["steg"] == {"flaechen": []}


def test_ohne_formschraege_braucht_keine_winkeltoleranz():
    standard = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}}
    ohne = _spec(TASCHE | {"ende": {"typ": "blind", "tiefe": 8}})
    assert bewerte(ohne, _messwerte({}), standard)["bestanden"] is True


class _Kaputt(_Flaeche):
    def EvaluateAtPoint(self, x, y, z):  # noqa: N802 – Name der SolidWorks-API
        raise RuntimeError("COM-Fehler")


def test_messfehler_wird_fehlertext():
    zapfen = _Feature([_Kaputt((0.01, 0.025, 0.0), (1.0, 0.0, 0.0))])
    ctx = Kontext(None, _Model({"zapfen": zapfen}), _spec(ZAPFEN), Path("t.yaml"), 0.1)
    assert formschraegen(ctx, _spec(ZAPFEN))["zapfen"] == "Formschräge zapfen nicht messbar: COM-Fehler"
```

- [ ] **Step 2: Test laufen lassen, er scheitert**

Run: `.venv\Scripts\python.exe -m pytest -q tests\pruefung\test_formschraege_pruefung.py`
Expected: FAIL – `1 error` (`ImportError: cannot import name 'formschraege_abweichungen'`).

- [ ] **Step 3: Bewertung**

In `swki/pruefung/bewertung.py` ersetzen:

```python
from swki.compiler.eigenschaften import material_passt
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand, volumen_auto
```

durch:

```python
from swki.compiler.eigenschaften import material_passt
from swki.formschraege import schraege, soll_vorzeichen
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand, volumen_auto
```

In `swki/pruefung/bewertung.py` ersetzen:

```python
    verzahnungen: dict[str, dict | str] = field(default_factory=dict)  # ID → Messwerte der Verzahnung oder Fehlertext
```

durch:

```python
    verzahnungen: dict[str, dict | str] = field(default_factory=dict)  # ID → Messwerte der Verzahnung oder Fehlertext
    formschraegen: dict[str, dict | str] = field(default_factory=dict)  # ID → {"flaechen": [...]} oder Fehlertext
```

In `swki/pruefung/bewertung.py` ersetzen:

```python
def baum_kennzahl(spec: dict, protokoll: dict | None) -> dict:
```

durch:

```python
def formschraege_abweichungen(f: dict, ist: dict, parameter: dict, tol_grad: float) -> list[str]:
    """Spec Formschräge §6.1: Seitenflächen des Features (swki.pruefung.messen.formschraegen) gegen Winkel und Richtung des
    Knotens der freigegebenen Kopie. Leere Liste = passt."""
    s = schraege(f)
    flaechen = ist["flaechen"]
    if not flaechen:
        return ["keine geschrägte Seitenfläche gefunden"]
    winkel, vorzeichen = auswerten(s["winkel"], parameter), soll_vorzeichen(f["typ"], s["querschnitt"])
    fehler = []
    falsch = [x["winkel"] for x in flaechen if abs(x["winkel"] - winkel) > tol_grad]
    if falsch:
        werte = ", ".join(f"{w:g}" for w in sorted({round(w, 3) for w in falsch}))
        fehler.append(f"Winkel {werte}° statt {winkel:g}° ({len(falsch)} von {len(flaechen)} Seitenflächen)")
    gegen = sum(1 for x in flaechen if x["vorzeichen"] != vorzeichen)
    if gegen:
        fehler.append(f"Querschnitt nicht {s['querschnitt']} ({gegen} von {len(flaechen)} Seitenflächen)")
    return fehler


def baum_kennzahl(spec: dict, protokoll: dict | None) -> dict:
```

In `swki/pruefung/bewertung.py` ersetzen:

```python
    damit ein nachgebesserter Bauweg das Soll nicht mitverschiebt. Normbohrungen werden gegen die freigegebene Kopie
    geprüft (Größen sind Text, die Prüfsumme schützt sie nicht)."""
```

durch:

```python
    damit ein nachgebesserter Bauweg das Soll nicht mitverschiebt. Normbohrungen und Formschrägen werden gegen die
    freigegebene Kopie geprüft (Größen und Richtungen sind Text, die Prüfsumme schützt sie nicht)."""
```

In `swki/pruefung/bewertung.py` ersetzen:

```python
        ergebnisse.append(eintrag("verzahnungen", not abweichend, ist=abweichend, knoten=sorted(abweichend)))
```

durch:

```python
        ergebnisse.append(eintrag("verzahnungen", not abweichend, ist=abweichend, knoten=sorted(abweichend)))

    soll_schraegen = [f for f in soll_spec["features"] if schraege(f) is not None]
    if soll_schraegen:
        p_soll, tol = soll_spec.get("parameter", {}), standard["toleranzen"]["winkel_grad"]
        abweichend, gemessen = {}, {}
        for f in soll_schraegen:
            ist = m.formschraegen.get(f["id"])
            if not isinstance(ist, dict):
                abweichend[f["id"]] = [ist or f"Feature {f['id']} fehlt im Teil"]
                continue
            gemessen[f["id"]] = sorted({round(x["winkel"], 3) for x in ist["flaechen"]})
            if fehler := formschraege_abweichungen(f, ist, p_soll, tol):
                abweichend[f["id"]] = fehler
        ergebnisse.append(eintrag("formschraegen", not abweichend, ist=abweichend, gemessen=gemessen,
                                  knoten=sorted(abweichend)))
```

- [ ] **Step 4: Messung**

In `swki/pruefung/messen.py` ersetzen:

```python
from swki.compiler.topologie import flaechen, koerper, referenz_geometrie
from swki.pruefung.bewertung import Messwerte, messpunkt_schluessel
```

durch:

```python
from swki.compiler.topologie import flaechen, koerper, loese_flaeche, referenz_geometrie
from swki.formschraege import TYPEN, extrusionsrichtung, schraege, seitenflaechen, skizzennormale
from swki.pruefung.bewertung import Messwerte, messpunkt_schluessel
```

In `swki/pruefung/messen.py` ersetzen:

```python
def kontext_aus_datei(app, model, spec: dict, spec_pfad: Path, tol_mm: float, protokoll: dict) -> Kontext:
```

durch:

```python
def punkt_und_normale(face) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Punkt (mm) und äußere Einheitsnormale einer Fläche nahe der Mitte ihrer Box (Spike S16, Frage 5):
    ISurface.EvaluateAtPoint liefert zuerst die Normale der Trägerfläche; FaceInSurfaceSense True = die Fläche zeigt
    entgegen. Gilt für Ebenen und Kegel gleich."""
    box = face.GetBox
    q = face.GetClosestPointOn((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2)
    werte = face.GetSurface.EvaluateAtPoint(q[0], q[1], q[2])
    n = (werte[0], werte[1], werte[2])
    if face.FaceInSurfaceSense:
        n = (-n[0], -n[1], -n[2])
    betrag = laenge(n)
    return (in_mm(q[0]), in_mm(q[1]), in_mm(q[2])), (n[0] / betrag, n[1] / betrag, n[2] / betrag)


def _skizzenebene(ctx, ebene, mit_punkt: bool) -> tuple[tuple, tuple | None]:
    """(Normale, Punkt in mm oder None) der Skizzenebene eines Knotens im fertigen Teil; den Punkt braucht nur mittig."""
    normale = skizzennormale(ebene)
    if normale is None:  # {nahe}: Normale und Punkt aus dem Modell
        flaeche = loese_flaeche(ctx, ebene)
        if flaeche.art != "ebene":
            raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", "Skizzenfläche ist nicht eben")
        return flaeche.normale, flaeche.punkt
    if not mit_punkt or isinstance(ebene, str):
        return normale, (0.0, 0.0, 0.0)
    if "versatz" in ebene:
        abstand_ = ctx.wert(ebene["versatz"]["abstand"])
        return normale, tuple(abstand_ * c for c in normale)
    if ebene["feature"] not in ctx.ergebnisse:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Feature {ebene['feature']!r} fehlt im Teil")
    flaeche = flaeche_in_richtung(flaechen(ctx.ergebnis(ebene["feature"]).features[0]), ebene["flaeche"])
    return normale, flaeche.punkt


def formschraegen(ctx, soll_spec: dict, aktuell_spec: dict | None = None) -> dict[str, dict | str]:
    """Spec Formschräge §6.1: je extrusion-/schnitt-Knoten mit formschraege (Soll: freigegebene Kopie) die Seitenflächen
    des gleichnamigen Features als {"flaechen": [{"winkel", "vorzeichen"}]} oder einen Fehlertext. Skizzenebene,
    umkehren und Endbedingung sind Bauweg und kommen aus der aktuellen Spezifikation."""
    aktuell = {f["id"]: f for f in (aktuell_spec or soll_spec)["features"]}
    ergebnis = {}
    for f in soll_spec["features"]:
        if schraege(f) is None:
            continue
        g = aktuell.get(f["id"])
        g = g if g is not None and g["typ"] in TYPEN else f
        feature = ctx.model.FeatureByName(f["id"])
        if feature is None:
            ergebnis[f["id"]] = f"Feature {f['id']} fehlt im Teil"
            continue
        try:
            mittig = g["ende"]["typ"] == "mittig"
            normale, punkt = _skizzenebene(ctx, g["skizze"]["ebene"], mittig)
            r = extrusionsrichtung(normale, g["typ"], g["ende"].get("umkehren", False))
            messungen = [punkt_und_normale(face) for face in (feature.GetFaces or ())]
            ergebnis[f["id"]] = {"flaechen": seitenflaechen(messungen, r, punkt if mittig else None)}
        except BauFehler as e:
            ergebnis[f["id"]] = f"{e.code}: {e}"
        except Exception as e:  # COM-Fehler beim Lesen → Mangel statt Abbruch der Prüfung
            ergebnis[f["id"]] = f"Formschräge {f['id']} nicht messbar: {e}"
    return ergebnis


def kontext_aus_datei(app, model, spec: dict, spec_pfad: Path, tol_mm: float, protokoll: dict) -> Kontext:
```

In `swki/pruefung/messen.py` ersetzen:

```python
        verzahnungen=verzahnungen(model, freigegeben or ctx.spec, ctx.tol_mm, ctx.app, ctx.spec),
    )
```

durch:

```python
        verzahnungen=verzahnungen(model, freigegeben or ctx.spec, ctx.tol_mm, ctx.app, ctx.spec),
        formschraegen=formschraegen(ctx, freigegeben or ctx.spec, ctx.spec),
    )
```

- [ ] **Step 5: Toleranz**

In `config/standard.yaml` ersetzen:

```yaml
  verzahnung_mm: 0.005  # Kreise, Zahnweite, Teilung, Zahndicke (Spec 4b §4.5; Wert nach Spike S14a Zeile 3)
```

durch:

```yaml
  verzahnung_mm: 0.005  # Kreise, Zahnweite, Teilung, Zahndicke (Spec 4b §4.5; Wert nach Spike S14a Zeile 3)
  winkel_grad: 0.01  # Formschräge: Winkel der Seitenflächen (Spec Formschräge §6.1; Wert nach Spike S16 Zeile 5)
```

- [ ] **Step 6: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\pruefung\test_formschraege_pruefung.py` → `10 passed`. Ganze Suite: **1018 passed, 141 deselected**. `pruefe-code` → `"befunde": []`.

- [ ] **Step 7: Commit**

```powershell
git add swki/pruefung/bewertung.py swki/pruefung/messen.py config/standard.yaml tests/pruefung/test_formschraege_pruefung.py
git commit -m "pruefung: formschraegen – Winkel und Richtung je Seitenfläche gegen die freigegebene Kopie (Task 4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Spike S16 – Richtung, Endbedingungen, Maße, Messung (live)

**Files:**
- Create: `spikes/s16_formschraege.py`, `docs/formschraege/ergebnisse.md`
- Ergebnis: `docs/stufe0/ergebnisse/s16_formschraege.json` (schreibt der Spike; wird committet)

**Interfaces:**
- Consumes: Tasks 1–4 (Handler mit den Annahmen `DDIR_KLEINER`/`WINKEL_MASS`, `formschraegen`, `punkt_und_normale`),
  `spikes._gemeinsam.lauf`, `spikes.s9a_gemeinsam.feature_masse`.
- Produces: Antworten auf die Zeilen 1–7 der Tabelle „Abhängigkeiten vom Spike S16“; Abschnitt 1 von
  `docs/formschraege/ergebnisse.md`.

- [ ] **Step 1: Vorbedingungen prüfen**

SolidWorks 2025 läuft, genau eine Instanz, keine fremden offenen Dokumente, Einstellungen `False 1`, Private Bytes notieren
(über ca. 4 GB: BLOCKED Neustart an den Controller).

- [ ] **Step 2: Spike schreiben**

`spikes/s16_formschraege.py` anlegen:

```python
"""S16 (Paket Formschräge): Formschräge an FeatureExtrusion3/FeatureCut4 – Richtung, Endbedingungen, Maße, Messung.

Block 100 × 60 × 20 auf Ebene oben (Deckfläche y = 20); jeder Fall in einem eigenen Teil, gebaut mit dem Compiler
(Handler extrusion mit den Annahmen DDIR_KLEINER und WINKEL_MASS), gemessen mit swki.pruefung.messen.formschraegen.
1 Richtung: Aufsatz/Schnitt × kleiner/groesser (Kreis Ø20 auf der Deckfläche), dazu Aufsatz und Schnitt mit umkehren.
2 Endbedingungen: mittig (Steg frei über dem Block auf Ebene vorne), durch_alles (Trichter von der Unterseite,
  groesser), bis_flaeche und versatz_von_flaeche (Schnitt von der Deckfläche, kleiner).
3 Ring (Kreise Ø30 und Ø10, Aufsatz kleiner): Vorzeichen und Lage der inneren Seitenfläche; Volumen für beide Deutungen.
4 Maße je Feature (Namen, Werte) und Gleichungen.
5 Messung: punkt_und_normale gegen IFace2.Normal (Ebenen) und ISurface.ConeParams2 (Kegel); größte Winkelabweichung.
6 Rechteck 30 × 20 mit Eckradius 3, Schnitt kleiner, Tiefe 10: 16°, 17°, 20° (Einzug 2,87 / 3,06 / 3,64 mm).
7 Volumen gegen swki.formschraege.volumen: Kreis, Rechteck mit Eckradius (groesser), Sechseck (kleiner), mittig.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s16_formschraege
"""

import math
import traceback
from contextlib import contextmanager
from pathlib import Path

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import feature_masse
from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.handler.extrusion import DDIR_KLEINER, WINKEL_MASS
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.formschraege import querschnitt_koeffizienten, soll_vorzeichen, volumen
from swki.konfig import lade_rechner
from swki.pruefung.messen import formschraegen, punkt_und_normale
from swki.verbindung import in_mm3, verbinde

BLOCK = {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}}
V_BLOCK = 100 * 60 * 20
DECK, UNTEN = {"feature": "f1", "flaeche": "+y"}, {"feature": "f1", "flaeche": "-y"}
KREIS20 = {"kreis": {"mitte": [0, 0], "durchmesser": 20}}


def _f(typ: str, querschnitt: str, element: dict, ebene, ende_typ: str = "blind", **ende) -> dict:
    return {"id": "f2", "typ": typ, "skizze": {"ebene": ebene, "elemente": [element]},
            "ende": {"typ": ende_typ, **ende, "formschraege": {"winkel": "=W", "querschnitt": querschnitt}}}


def _v(element: dict, tiefe: float, winkel: float, querschnitt: str, mittig: bool = False) -> float:
    return volumen(querschnitt_koeffizienten(element, {}), tiefe, winkel, querschnitt, mittig)


@contextmanager
def _gebaut(app, r, f: dict, winkel: float):
    spec = {"art": "teil", "name": "S16", "parameter": {"W": winkel}, "features": [BLOCK, f]}
    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, Path("s16.yaml"), 0.1)
        globale_variablen(model, spec["parameter"])
        protokoll = Protokoll("S16", "s16.yaml", 0, r.sw_jahr)
        yield ctx, baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
    finally:
        sw.schliesse(app, model)


def _flaechen(feature, winkel: float) -> dict:
    """Frage 5: Normale aus punkt_und_normale gegen IFace2.Normal (Ebene) bzw. halben Kegelwinkel (ConeParams2)."""
    liste, abw_normale, abw_winkel = [], 0.0, 0.0
    for face in feature.GetFaces or ():
        s = face.GetSurface
        punkt, n = punkt_und_normale(face)
        e = {"punkt": [round(c, 4) for c in punkt], "n": [round(c, 6) for c in n]}
        if s.IsPlane:
            normal = tuple(face.Normal)
            e |= {"art": "ebene", "normal": [round(c, 6) for c in normal]}
            abw_normale = max(abw_normale, max(abs(a - b) for a, b in zip(n, normal)))
        elif s.IsCone:
            k = s.ConeParams2
            halb = math.degrees(k[7])
            e |= {"art": "kegel", "achse": [round(c, 6) for c in k[3:6]], "halber_winkel": round(halb, 6),
                  "radius_mm": round(k[6] * 1000, 4)}
            abw_winkel = max(abw_winkel, abs(halb - winkel))
        else:
            e["art"] = "sonstige"
        liste.append(e)
    return {"liste": liste, "abw_normale_max": abw_normale, "abw_kegelwinkel_max_grad": abw_winkel}


def fall(app, r, f: dict, winkel: float, soll_aenderung: float | None) -> dict:
    with _gebaut(app, r, f, winkel) as (ctx, fehler):
        d = {"fehler": None if fehler is None else repr(fehler)}
        if fehler is not None:
            return d
        model = ctx.model
        feature = model.FeatureByName(f["id"])
        ist = in_mm3(model.Extension.CreateMassProperty.Volume) - V_BLOCK
        d["volumen_aenderung"] = round(ist, 3)
        if soll_aenderung is not None:
            d["soll_aenderung"] = round(soll_aenderung, 3)
            d["volumen_abw_prozent"] = round(abs(ist - soll_aenderung) / abs(soll_aenderung) * 100, 5)
        d["koerper"] = len(model.GetBodies2(0, False) or ())
        d["masse"] = feature_masse(feature)
        g = model.GetEquationMgr
        d["gleichungen"] = [g.Equation(i) for i in range(g.GetCount)]
        d["soll_vorzeichen"] = soll_vorzeichen(f["typ"], f["ende"]["formschraege"]["querschnitt"])
        gemessen = formschraegen(ctx, ctx.spec)[f["id"]]
        d["gemessen"] = gemessen
        if isinstance(gemessen, dict):
            d["vorzeichen_passt"] = all(x["vorzeichen"] == d["soll_vorzeichen"] for x in gemessen["flaechen"])
            d["winkel_abw_max_grad"] = max((abs(x["winkel"] - winkel) for x in gemessen["flaechen"]), default=None)
        d["flaechen"] = _flaechen(feature, winkel)
        return d


def _sicher(d: dict, name: str, fn, *args) -> None:
    """Fall ausführen; ein Fehler (mit Aufrufkette) verliert die Befunde der anderen Fälle nicht (kein Wiederholen)."""
    try:
        d[name] = fn(*args)
    except Exception as e:
        d[name] = {"fehler_fall": repr(e), "aufrufkette": traceback.format_exc()}


def pruefen() -> dict:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    d: dict = {"annahmen": {"DDIR_KLEINER": DDIR_KLEINER, "WINKEL_MASS": WINKEL_MASS}}
    # 1 Richtung
    for typ in ("extrusion", "schnitt"):
        for q in ("kleiner", "groesser"):
            v = _v(KREIS20, 8, 10, q)
            _sicher(d, f"1_{typ}_{q}", fall, app, r, _f(typ, q, KREIS20, DECK, tiefe=8), 10,
                    v if typ == "extrusion" else -v)
    oben32 = {"versatz": {"ebene": "oben", "abstand": 32}}
    _sicher(d, "1_extrusion_kleiner_umkehren", fall, app, r,
            _f("extrusion", "kleiner", KREIS20, oben32, tiefe=12, umkehren=True), 10, _v(KREIS20, 12, 10, "kleiner"))
    unter5 = {"versatz": {"ebene": "oben", "abstand": -5}}
    _sicher(d, "1_schnitt_kleiner_umkehren", fall, app, r,
            _f("schnitt", "kleiner", KREIS20, unter5, tiefe=13, umkehren=True), 10,
            -(_v(KREIS20, 13, 10, "kleiner") - _v(KREIS20, 5, 10, "kleiner")))
    # 2 Endbedingungen
    steg = {"rechteck": {"mitte": [0, 40], "breite": 40, "hoehe": 12}}
    _sicher(d, "2_mittig", fall, app, r, _f("extrusion", "kleiner", steg, "vorne", "mittig", tiefe=8), 5,
            _v(steg, 8, 5, "kleiner", mittig=True))
    _sicher(d, "2_durch_alles", fall, app, r, _f("schnitt", "groesser", KREIS20, UNTEN, "durch_alles"), 10,
            -_v(KREIS20, 20, 10, "groesser"))
    _sicher(d, "2_bis_flaeche", fall, app, r, _f("schnitt", "kleiner", KREIS20, DECK, "bis_flaeche", flaeche=UNTEN), 10,
            -_v(KREIS20, 20, 10, "kleiner"))
    _sicher(d, "2_versatz_von_flaeche", fall, app, r,
            _f("schnitt", "kleiner", KREIS20, DECK, "versatz_von_flaeche", flaeche=UNTEN, abstand=5), 10,
            -_v(KREIS20, 15, 10, "kleiner"))
    # 3 Ring
    ring = _f("extrusion", "kleiner", {"kreis": {"mitte": [0, 0], "durchmesser": 30}}, DECK, tiefe=10)
    ring["skizze"]["elemente"].append({"kreis": {"mitte": [0, 0], "durchmesser": 10}})
    aussen = _v({"kreis": {"durchmesser": 30}}, 10, 10, "kleiner")
    d["3_ring_soll"] = {"innen_waechst": round(aussen - _v({"kreis": {"durchmesser": 10}}, 10, 10, "groesser"), 3),
                        "innen_schrumpft": round(aussen - _v({"kreis": {"durchmesser": 10}}, 10, 10, "kleiner"), 3)}
    _sicher(d, "3_ring", fall, app, r, ring, 10, None)
    # 6 Eckradius
    eck = {"rechteck": {"mitte": [0, 0], "breite": 30, "hoehe": 20, "radius": 3}}
    for w in (16, 17, 20):
        _sicher(d, f"6_eckradius_{w}", fall, app, r, _f("schnitt", "kleiner", eck, DECK, tiefe=10), w,
                -_v(eck, 10, w, "kleiner"))
    # 7 Volumen weiterer Profile
    eck_gross = {"rechteck": {"mitte": [0, 0], "breite": 30, "hoehe": 20, "radius": 3}}
    _sicher(d, "7_eckradius_groesser", fall, app, r, _f("extrusion", "groesser", eck_gross, DECK, tiefe=10), 10,
            _v(eck_gross, 10, 10, "groesser"))
    sechseck = {"polygon": {"punkte": [[round(20 / math.sqrt(3) * math.cos(math.radians(60 * k)), 6),
                                        round(20 / math.sqrt(3) * math.sin(math.radians(60 * k)), 6)] for k in range(6)]}}
    _sicher(d, "7_sechseck_kleiner", fall, app, r, _f("extrusion", "kleiner", sechseck, DECK, tiefe=10), 10,
            _v(sechseck, 10, 10, "kleiner"))
    return d


if __name__ == "__main__":
    lauf("s16_formschraege", pruefen)
```

Run: `.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` → `"befunde": []`; ganze Suite unverändert **1018 passed, 141 deselected**.

- [ ] **Step 3: Spike laufen lassen**

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m spikes.s16_formschraege`
Expected: `"ok": true` in `docs/stufe0/ergebnisse/s16_formschraege.json`; 17 Teile werden gebaut und ungespeichert geschlossen.
Private Bytes danach notieren.

- [ ] **Step 4: Auswerten (Controller entscheidet)**

Je Zeile der Tabelle „Abhängigkeiten vom Spike S16“ Annahme gegen Messung vergleichen und dem Controller melden (Zeile,
Messwert, Annahme getroffen ja/nein). Bei Abweichung **nicht selbst umbauen**: NEEDS_CONTEXT mit dem JSON-Auszug; der
Controller entscheidet nach der Spalte „sonst“, hält es im Ledger fest und gibt den Code-Nachzug vor. Prüfwerte und
Erwartungen der Tests nie an die Messung anpassen, außer der Controller ordnet es nach der Spalte „sonst“ an.

- [ ] **Step 5: Ergebnisse festhalten**

`docs/formschraege/ergebnisse.md` anlegen mit:

```markdown
# Paket Formschräge – Ergebnisse

Spec: docs/superpowers/specs/2026-10-07-formschraege-design.md · Plan: docs/superpowers/plans/2026-10-07-formschraege.md

## 1. Spike S16 (SOLIDWORKS 2025, Rechner A, <Datum>)

Rohdaten: docs/stufe0/ergebnisse/s16_formschraege.json

| # | Frage | Annahme | gemessen | getroffen | Entscheidung (Ledger) |
|---|---|---|---|---|---|
| 1 | Richtung | … | … | ja/nein | … |
```

und für jede der Zeilen 1–7 eine Tabellenzeile mit den gemessenen Werten (Vorzeichen, Volumenabweichung in %, Maßnamen,
größte Normalen- und Winkelabweichung, Ergebnis der Eckradius-Fälle) und der Entscheidung des Controllers.

- [ ] **Step 6: Commit**

```powershell
git add spikes/s16_formschraege.py docs/stufe0/ergebnisse/s16_formschraege.json docs/formschraege/ergebnisse.md
git commit -m "spikes: S16 Formschräge – Richtung, Endbedingungen, Maße, Messung (Task 5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Live-Tests der Formschräge an Minimalteilen (live)

**Files:**
- Create: `tests/live/test_live_formschraege.py`

**Interfaces:**
- Consumes: Tasks 1–5 (mit den Ledger-Entscheidungen aus Task 5), `tests/live/bauhilfe.py` (`gebautes_teil`,
  `volumen_mm3`).
- Produces: 8 Live-Tests (Marker `sw`).

- [ ] **Step 1: Tests schreiben**

`tests/live/test_live_formschraege.py` anlegen:

```python
"""Live: Formschräge an Aufsatz und Schnitt (Paket Formschräge) – Volumen, Messung der Seitenflächen, Gleichung
(SolidWorks muss laufen)."""

import pythoncom
import pytest

from swki.compiler import sw
from swki.formschraege import querschnitt_koeffizienten, volumen
from swki.pruefung.bewertung import formschraege_abweichungen
from swki.pruefung.messen import formschraegen

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
VOLL = 100 * 60 * 20
KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
DECKFLAECHE = {"feature": "f1", "flaeche": "+y"}
KREIS = {"kreis": {"mitte": [0, 0], "durchmesser": 20}}
TOL_WINKEL = 0.01


def _spec(*features, **parameter):
    return {"art": "teil", "name": "T", "parameter": {"W": 10, **parameter}, "features": [KLOTZ, *features]}


def _schraeg(typ: str, querschnitt: str, element=KREIS, ebene=DECKFLAECHE, ende_typ="blind", **ende) -> dict:
    tiefe = {"tiefe": 8} if ende_typ in ("blind", "mittig") else {}
    ende = {"typ": ende_typ, **tiefe, **ende, "formschraege": {"winkel": "=W", "querschnitt": querschnitt}}
    return {"id": "f2", "typ": typ, "skizze": {"ebene": ebene, "elemente": [element]}, "ende": ende}


def _pruefe(ctx, f: dict) -> None:
    ist = formschraegen(ctx, ctx.spec)[f["id"]]
    assert isinstance(ist, dict), ist
    assert ist["flaechen"], ist
    assert formschraege_abweichungen(f, ist, ctx.spec["parameter"], TOL_WINKEL) == [], ist


@pytest.mark.parametrize(("typ", "querschnitt"), [
    ("extrusion", "kleiner"), ("extrusion", "groesser"), ("schnitt", "kleiner"), ("schnitt", "groesser"),
])
def test_kreis_blind(typ, querschnitt):
    f = _schraeg(typ, querschnitt)
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        v = volumen(querschnitt_koeffizienten(KREIS, {}), 8, 10, querschnitt)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL + (v if typ == "extrusion" else -v), rel=1e-6)
        _pruefe(ctx, f)


def test_tasche_mit_eckradius_und_gleichung():
    element = {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30, "radius": 5}}
    f = _schraeg("schnitt", "kleiner", element)
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        k = querschnitt_koeffizienten(element, {})
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - volumen(k, 8, 10, "kleiner"), rel=1e-6)
        _pruefe(ctx, f)
        g = ctx.model.GetEquationMgr
        texte = [g.Equation(i) for i in range(g.GetCount)]
        assert '"D2@f2" = "W"' in texte
        dispid = g._oleobj_.GetIDsOfNames("Equation")
        g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, texte.index('"W" = 10'), '"W" = 15')
        g.EvaluateAll
        sw.rebuild(ctx.model)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - volumen(k, 8, 15, "kleiner"), rel=1e-6)


def test_aufsatz_umgekehrt():
    # Skizze 12 mm über der Deckfläche, der Zapfen wächst nach unten bis auf die Deckfläche und verjüngt sich dabei
    f = _schraeg("extrusion", "kleiner", ebene={"versatz": {"ebene": "oben", "abstand": 32}}, tiefe=12, umkehren=True)
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL + volumen(querschnitt_koeffizienten(KREIS, {}), 12, 10, "kleiner"),
                                                       rel=1e-6)
        _pruefe(ctx, f)


def test_steg_mittig():
    # Steg frei über der Platte (y 34 … 46, z ± 4): zweiter Körper, dafür ist sein Volumen exakt bekannt
    element = {"rechteck": {"mitte": [0, 40], "breite": 40, "hoehe": 12}}
    f = _schraeg("extrusion", "kleiner", element, ebene="vorne", ende_typ="mittig")
    with gebautes_teil(_spec(f, W=5)) as (ctx, fehler, _):
        assert fehler is None
        v = volumen(querschnitt_koeffizienten(element, {}), 8, 5, "kleiner", mittig=True)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL + v, rel=1e-6)
        _pruefe(ctx, f)


def test_trichter_durch_alles():
    f = _schraeg("schnitt", "groesser", ebene={"feature": "f1", "flaeche": "-y"}, ende_typ="durch_alles")
    with gebautes_teil(_spec(f)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - volumen(querschnitt_koeffizienten(KREIS, {}), 20, 10, "groesser"),
                                                       rel=1e-6)
        _pruefe(ctx, f)
```

Ganze Suite ohne SolidWorks: **1018 passed, 149 deselected**; `pruefe-code` → `"befunde": []`.

- [ ] **Step 2: Live laufen lassen (einzeln)**

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_formschraege.py --zeit 900`
Expected: alle 8 `OK`. Private Bytes danach notieren. Scheitert ein Test: Prüfbericht-/Assert-Auszug an den Controller
(NEEDS_CONTEXT), Erwartungen nicht abschwächen.

- [ ] **Step 3: Commit**

```powershell
git add tests/live/test_live_formschraege.py
git commit -m "tests: Live-Tests Formschräge – Aufsatz/Schnitt, kleiner/groesser, umkehren, mittig, durch_alles, Gleichung (Task 6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Referenz *Zentrieraufnahme* mit Prüfer und Negativfällen (live)

**Files:**
- Create: `tests/referenz/zentrieraufnahme/zentrieraufnahme.yaml`, `tests/referenz/zentrieraufnahme/sollvolumen.py`,
  `tests/referenz/zentrieraufnahme/eingabe/beschreibung.md`, `tests/referenz/test_zentrieraufnahme.py`,
  `tests/live/test_live_zentrieraufnahme.py`
- Modify: `tests/referenz/test_referenzen.py`

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: Referenz *Zentrieraufnahme* in der Regressions-Suite; Negativfälle „Richtung vertauscht“ und „Winkel verfälscht“.

- [ ] **Step 1: Tests schreiben**

`tests/referenz/test_zentrieraufnahme.py` anlegen:

```python
"""Referenz Zentrieraufnahme (Paket Formschräge) ohne SolidWorks: gültig ohne Hinweis, Sollvolumen passt zur Rechnung."""

import importlib.util
from pathlib import Path

import pytest

from swki.formschraege import querschnitt_koeffizienten, volumen
from swki.spec.hinweise import hinweise
from swki.spec.laden import lade_spec

ORDNER = Path(__file__).parent / "zentrieraufnahme"


def _rechnung() -> dict[str, float]:
    modul_spec = importlib.util.spec_from_file_location("sollvolumen_zentrieraufnahme", ORDNER / "sollvolumen.py")
    modul = importlib.util.module_from_spec(modul_spec)
    modul_spec.loader.exec_module(modul)
    return modul.rechnung()


def test_gueltig_ohne_hinweis():
    spec = lade_spec(ORDNER / "zentrieraufnahme.yaml")
    assert hinweise(spec) == []
    assert [f["id"] for f in spec["features"]] == ["f1", "zapfen", "tasche", "trichter", "steg"]


def test_sollvolumen_aus_rechnung():
    spec = lade_spec(ORDNER / "zentrieraufnahme.yaml")
    assert sum(_rechnung().values()) == pytest.approx(spec["pruefung"]["volumen"]["soll"], abs=0.001)


def test_sollvolumen_unabhaengig_von_swki_formschraege():
    # Zapfen, Tasche und Trichter rechnet sollvolumen.py mit eigenen Formeln; sie müssen swki.formschraege bestätigen
    p = lade_spec(ORDNER / "zentrieraufnahme.yaml")["parameter"]
    teile = list(_rechnung().values())
    zapfen = querschnitt_koeffizienten({"kreis": {"durchmesser": p["DZ"]}}, {})
    tasche = querschnitt_koeffizienten({"rechteck": {"breite": p["TL"], "hoehe": p["TB"], "radius": p["TR"]}}, {})
    trichter = querschnitt_koeffizienten({"kreis": {"durchmesser": p["DR"]}}, {})
    assert teile[1] == pytest.approx(volumen(zapfen, p["HZ"], p["WZ"], "kleiner"))
    assert teile[3] == pytest.approx(-volumen(tasche, p["TT"], p["WT"], "kleiner"))
    assert teile[4] == pytest.approx(-volumen(trichter, p["H"], p["WR"], "groesser"))
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\referenz\test_zentrieraufnahme.py`
Expected: FAIL – `3 failed` (`zentrieraufnahme.yaml fehlt` bzw. `sollvolumen.py` fehlt).

- [ ] **Step 3: Referenz-Spec, Sollvolumen, Regression, Negativfälle**

`tests/referenz/zentrieraufnahme/zentrieraufnahme.yaml` anlegen:

```yaml
# Referenzteil Paket Formschräge: Zentrieraufnahme (selbst definiert, allgemeine Konstruktion).
# Nutzt die Formschräge an Aufsatz und Schnitt, in beiden Richtungen und mit vier Endbedingungen: konischer Zentrierzapfen
# (Aufsatz, kleiner, blind), Einführtasche mit Eckradius (Schnitt, kleiner, blind), Trichter-Durchbruch von der
# Unterseite (Schnitt, groesser, durch_alles) und beidseitig verjüngter Steg (Aufsatz auf Ebene vorne, kleiner, mittig;
# der Steg ragt 2 mm in die Platte). Platte L × B × H auf Ebene oben (wächst nach +Y), Mitte im Ursprung; (u, v) auf
# Deck- und Unterseite: X = u, Z = −v.
art: teil
name: Zentrieraufnahme
material: "1.0038"
eigenschaften: {Benennung: Zentrieraufnahme}
parameter:
  L: 160      # Länge (X)
  B: 100      # Breite (Z)
  H: 20       # Dicke (Y)
  R: 8        # Eckradius der Platte
  DZ: 30      # Zentrierzapfen: Fuß-Ø
  HZ: 25      # Zentrierzapfen: Höhe
  WZ: 10      # Zentrierzapfen: Schräge (Grad)
  XZ: -50     # Zentrierzapfen: Lage (u)
  TL: 40      # Einführtasche: Länge (X) an der Deckfläche
  TB: 30      # Einführtasche: Breite (Z) an der Deckfläche
  TR: 6       # Einführtasche: Eckradius an der Deckfläche
  TT: 12      # Einführtasche: Tiefe
  WT: 8       # Einführtasche: Schräge (Grad)
  XT: 45      # Einführtasche: Lage (u)
  VT: 22      # Einführtasche: Lage (v)
  DR: 10      # Trichter: Auslauf-Ø an der Unterseite
  WR: 30      # Trichter: Schräge (Grad), oben weit
  XR: 45      # Trichter: Lage (u)
  VR: -25     # Trichter: Lage (v) auf der Unterseite
  SL: 40      # Steg: Länge (X)
  SH: 12      # Steg: Höhe des Profils (Y), ragt SY − SH/2 bis H in die Platte
  SY: 24      # Steg: Mitte des Profils (Y)
  SX: -5      # Steg: Mitte des Profils (X)
  ST: 10      # Steg: Dicke (Z), mittig zur Ebene vorne
  WS: 5       # Steg: Schräge (Grad) zu beiden Seiten
features:
  - id: f1            # Grundplatte mit Eckradius
    typ: extrusion
    skizze:
      ebene: oben
      elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B", radius: "=R"}}]
    ende: {typ: blind, tiefe: "=H"}
  - id: zapfen        # Zentrierzapfen, verjüngt sich nach oben
    typ: extrusion
    skizze:
      ebene: {feature: f1, flaeche: "+y"}
      elemente: [{kreis: {mitte: ["=XZ", 0], durchmesser: "=DZ"}}]
    ende: {typ: blind, tiefe: "=HZ", formschraege: {winkel: "=WZ", querschnitt: kleiner}}
  - id: tasche        # Einführtasche, wird zum Boden hin enger
    typ: schnitt
    skizze:
      ebene: {feature: f1, flaeche: "+y"}
      elemente: [{rechteck: {mitte: ["=XT", "=VT"], breite: "=TL", hoehe: "=TB", radius: "=TR"}}]
    ende: {typ: blind, tiefe: "=TT", formschraege: {winkel: "=WT", querschnitt: kleiner}}
  - id: trichter      # Trichter, von der engen Unterseite aus skizziert, oben weit
    typ: schnitt
    skizze:
      ebene: {feature: f1, flaeche: "-y"}
      elemente: [{kreis: {mitte: ["=XR", "=VR"], durchmesser: "=DR"}}]
    ende: {typ: durch_alles, formschraege: {winkel: "=WR", querschnitt: groesser}}
  - id: steg          # Steg auf Ebene vorne, zu beiden Seiten verjüngt
    typ: extrusion
    skizze:
      ebene: vorne
      elemente: [{rechteck: {mitte: ["=SX", "=SY"], breite: "=SL", hoehe: "=SH"}}]
    ende: {typ: mittig, tiefe: "=ST", formschraege: {winkel: "=WS", querschnitt: kleiner}}
pruefung:
  huellquader: ["=L", "=H+HZ", "=B"]
  volumen:
    # analytisch (tests/referenz/zentrieraufnahme/sollvolumen.py):
    #   Platte (L·B − (4 − π)·R²)·H                                      318901,239
    # + Zapfen, Kegelstumpf Ø DZ → DZ − 2·HZ·tan WZ                       12986,929
    # + Steg über der Platte, 2 × ∫ (SL − 2d)·(SY + SH/2 − d − H)          3870,043
    # − Tasche, ∫ Rechteck mit Eckradius nach innen versetzt              12752,492
    # − Trichter, Kegelstumpf Ø DR → DR + 2·H·tan WR                       7990,922
    # = 315014,796 mm³   (bei geänderten Parametern neu rechnen)
    soll: 315014.796
    toleranz_prozent: 0.05
  masse_pruefen:
    - was: Zapfenhöhe über der Unterseite
      von: {feature: f1, flaeche: "-y"}
      zu: {feature: zapfen, flaeche: "+y"}
      soll: "=H+HZ"
      tol: 0.01
    - was: Taschenboden über der Unterseite
      von: {feature: f1, flaeche: "-y"}
      zu: {feature: tasche, flaeche: "+y"}
      soll: "=H-TT"
      tol: 0.01
```

`tests/referenz/zentrieraufnahme/sollvolumen.py` anlegen:

```python
"""Analytisches Sollvolumen der Referenz Zentrieraufnahme (Paket Formschräge) aus den Parametern.

Aufruf: .venv\\Scripts\\python.exe tests\\referenz\\zentrieraufnahme\\sollvolumen.py
Rechnet unabhängig vom Compiler und von swki.formschraege/swki.pruefung.geometrie (Kegelstümpfe und das Integral des
versetzten Querschnitts je Element). Das Ergebnis gehört nach pruefung.volumen.soll in zentrieraufnahme.yaml (samt
Kommentar) – nie ein Messwert.
"""

import math
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).with_name("zentrieraufnahme.yaml")


def _kegelstumpf(r1: float, r2: float, h: float) -> float:
    return math.pi * h / 3 * (r1 * r1 + r1 * r2 + r2 * r2)


def _integral(flaeche, tiefe: float) -> float:
    """∫₀^tiefe flaeche(h) dh mit der Simpsonregel – exakt, weil flaeche(h) ein Polynom höchstens 2. Grades ist."""
    return tiefe / 6 * (flaeche(0) + 4 * flaeche(tiefe / 2) + flaeche(tiefe))


def rechnung() -> dict[str, float]:
    p = yaml.safe_load(SPEC.read_text(encoding="utf-8"))["parameter"]
    t = {k: math.tan(math.radians(p[k])) for k in ("WZ", "WT", "WR", "WS")}
    zapfen_r1 = p["DZ"] / 2
    trichter_r1 = p["DR"] / 2

    def tasche(h: float) -> float:  # Rechteck mit Eckradius, um d = h·tan WT nach innen versetzt
        d = h * t["WT"]
        return (p["TL"] - 2 * d) * (p["TB"] - 2 * d) - (4 - math.pi) * (p["TR"] - d) ** 2

    def steg_ueber_platte(h: float) -> float:  # Steg im Abstand h von der Ebene vorne, nur der Teil über y = H
        d = h * t["WS"]
        return (p["SL"] - 2 * d) * (p["SY"] + p["SH"] / 2 - d - p["H"])

    return {
        "Platte (L·B − (4 − π)·R²)·H": (p["L"] * p["B"] - (4 - math.pi) * p["R"] ** 2) * p["H"],
        "+ Zapfen, Kegelstumpf Ø DZ → DZ − 2·HZ·tan WZ": _kegelstumpf(zapfen_r1, zapfen_r1 - p["HZ"] * t["WZ"], p["HZ"]),
        "+ Steg über der Platte, 2 × ∫ (SL − 2d)·(SY + SH/2 − d − H)": 2 * _integral(steg_ueber_platte, p["ST"] / 2),
        "− Tasche, ∫ Rechteck mit Eckradius nach innen versetzt": -_integral(tasche, p["TT"]),
        "− Trichter, Kegelstumpf Ø DR → DR + 2·H·tan WR": -_kegelstumpf(trichter_r1, trichter_r1 + p["H"] * t["WR"], p["H"]),
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Konsole unter cp1252: sonst brechen "³", "π" und "−" die Ausgabe ab
    teile = rechnung()
    for text, wert in teile.items():
        print(f"{wert:14.3f}  {text}")
    print(f"{sum(teile.values()):14.3f}  Sollvolumen mm³")
```

`tests/referenz/zentrieraufnahme/eingabe/beschreibung.md` anlegen:

```markdown
# Zentrieraufnahme (Referenz Paket Formschräge)

Grundplatte 160 × 100 × 20 mit Eckradius 8 (Stahl S235, 1.0038), Mitte im Ursprung. Darauf und darin vier Elemente mit
schrägen Wänden (Formschräge als Gestaltungselement, kein Gussteil):

- Zentrierzapfen auf der Oberseite, 50 links der Mitte: Fuß Ø 30, 25 hoch, verjüngt sich mit 10° nach oben (oben etwa
  Ø 21,2).
- Einführtasche in der Oberseite, rechts hinten (Mitte 45 rechts, 22 nach hinten): oben 40 × 30 mit Eckradius 6, 12 tief,
  wird mit 8° zum Boden hin enger.
- Trichter rechts vorn (Mitte 45 rechts, 25 nach vorn) durch die ganze Platte: unten Ø 10, mit 30° nach oben weit (oben
  etwa Ø 33,1). Maßgebend ist der Auslauf Ø 10 an der Unterseite.
- Steg längs auf der Mittelebene der Platte (Ebene vorne): 40 lang (Mitte 5 links der Plattenmitte), oben 10 über
  der Platte, 10 dick; er verjüngt sich mit 5° zu beiden Seiten der Mittelebene und geht ohne Spalt in die Platte über.
- Ein Körper; Elemente berühren sich nicht.
```

In `tests/referenz/test_referenzen.py` ersetzen:

```python
    ("motorhalter", "motorhalter.yaml"),
])
```

durch:

```python
    ("motorhalter", "motorhalter.yaml"),
    ("zentrieraufnahme", "zentrieraufnahme.yaml"),
])
```

`tests/live/test_live_zentrieraufnahme.py` anlegen:

```python
"""Live: Negativfälle an der Zentrieraufnahme (Spec Formschräge §9) – Richtung vertauscht, Winkel verfälscht. Jeder Fall
verfälscht nur den Bau des Zapfens (monkeypatch auf den Namen schraege, den der Handler importiert), die Spec bleibt
gültig und unverändert; die Prüfung formschraegen misst gegen die freigegebene Kopie und meldet den Zapfen."""

import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.compiler.handler import extrusion
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-ZENTRIER"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "zentrieraufnahme"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def spec(tmp_path):
    ordner = tmp_path / AUFTRAG
    shutil.copytree(REFERENZ, ordner)
    yield ordner / "zentrieraufnahme.yaml"
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _verfaelsche_zapfen(monkeypatch, aenderung: dict) -> None:
    original = extrusion.schraege

    def schraege(f: dict):
        s = original(f)
        return {**s, **aenderung} if s is not None and f["id"] == "zapfen" else s

    monkeypatch.setattr(extrusion, "schraege", schraege)


def _formschraegen(capsys, spec: Path) -> tuple[dict, dict]:
    """validieren, freigeben, bauen, pruefen; liefert die Prüfung formschraegen und die Mängel je Prüfung."""
    assert _lauf(capsys, "validieren", str(spec))[0] == 0
    assert _lauf(capsys, "freigeben", str(spec))[0] == 0
    code, ergebnis = _lauf(capsys, "bauen", str(spec))
    assert code == 0, ergebnis
    code, bericht = _lauf(capsys, "pruefen", str(spec))
    assert code in (0, 1) and "maengel" in bericht, bericht
    assert bericht["bestanden"] is False, bericht
    return next(p for p in bericht["pruefungen"] if p["id"] == "formschraegen"), {m["pruefung"]: m for m in bericht["maengel"]}


def test_richtung_vertauscht(capsys, spec, monkeypatch):
    # Der Zapfen wird nach oben weiter statt enger: alle Seitenflächen zeigen das falsche Vorzeichen; das Volumen
    # wächst mit (Mangel volumen), der Hüllquader nicht (der Zapfen bleibt im Grundriss der Platte)
    _verfaelsche_zapfen(monkeypatch, {"querschnitt": "groesser"})
    pruefung, maengel = _formschraegen(capsys, spec)
    assert pruefung["ok"] is False and pruefung["knoten"] == ["zapfen"], pruefung
    assert [t.split(" (")[0] for t in pruefung["ist"]["zapfen"]] == ["Querschnitt nicht kleiner"], pruefung
    assert set(maengel) == {"formschraegen", "volumen"}, maengel


def test_winkel_verfaelscht(capsys, spec, monkeypatch):
    # Der Zapfen wird mit WZ + 3° gebaut (die Gleichung am Feature folgt mit, ein Rebuild stellt nichts zurück)
    _verfaelsche_zapfen(monkeypatch, {"winkel": "=WZ+3"})
    pruefung, maengel = _formschraegen(capsys, spec)
    assert pruefung["ok"] is False and pruefung["knoten"] == ["zapfen"], pruefung
    assert [t.split(" (")[0] for t in pruefung["ist"]["zapfen"]] == ["Winkel 13° statt 10°"], pruefung
    assert pruefung["gemessen"]["zapfen"] == [13.0], pruefung
    assert set(maengel) == {"formschraegen", "volumen"}, maengel
```

- [ ] **Step 4: Ohne SolidWorks prüfen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\referenz\test_zentrieraufnahme.py` → `3 passed`;
`.venv\Scripts\python.exe tests\referenz\zentrieraufnahme\sollvolumen.py` → `315014.796  Sollvolumen mm³`;
`.venv\Scripts\python.exe -m swki validieren tests\referenz\zentrieraufnahme\zentrieraufnahme.yaml` → `"gueltig": true`,
`"hinweise": []`. Ganze Suite: **1021 passed, 152 deselected**; `pruefe-code` → `"befunde": []`.

- [ ] **Step 5: Referenz live**

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m pytest -m sw "tests/referenz/test_referenzen.py::test_referenz_besteht[zentrieraufnahme-zentrieraufnahme.yaml]" -q`
Expected: `1 passed`. Private Bytes und Dauer notieren. Mängel: Bauweg nachbessern (Ebenen, Lage, Reihenfolge), nie
Prüfwerte oder das Sollvolumen; weicht `volumen` ab, NEEDS_CONTEXT mit Ist und Soll.

- [ ] **Step 6: Prüfer-Urteil (Controller)**

Auftrag `auftraege/REF-FS-ZENTRIERAUFNAHME/` (Kopie von `tests/referenz/zentrieraufnahme/` samt `eingabe/`),
`swki validieren`, `freigeben`,
`bauen`, `pruefen`; der **Controller** startet den Prüfer-Agenten mit Eingabe, freigegebener Spec, Prüfbericht und Bildern;
Urteil unverändert nach `protokolle/zentrieraufnahme.lauf-<n>.pruefer.json`; `swki status`. Erwartet
`{"bestanden": true, "maengel": []}`. Auftrag und Arbeitsordner danach löschen.

- [ ] **Step 7: Negativfälle (einzeln)**

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_zentrieraufnahme.py --zeit 900`
Expected: beide `OK` (je genau `{formschraegen, volumen}`, Knoten `zapfen`). Abweichung: Erwartung nicht abschwächen,
NEEDS_CONTEXT.

- [ ] **Step 8: Commit**

```powershell
git add tests/referenz/zentrieraufnahme tests/referenz/test_zentrieraufnahme.py tests/referenz/test_referenzen.py tests/live/test_live_zentrieraufnahme.py
git commit -m "referenz: Zentrieraufnahme mit Formschrägen, Regression, Negativfälle Richtung und Winkel (Task 7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Skill, Prüfer, CLAUDE.md, Design, Ergebnisse, Regression

**Files:**
- Modify: `.claude/skills/konstruieren/SKILL.md`, `.claude/agents/pruefer.md`, `CLAUDE.md`,
  `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`, `docs/formschraege/ergebnisse.md`

**Interfaces:**
- Consumes: Tasks 1–7 (Ledger-Entscheidungen aus Task 5 fließen in Skill und Ergebnisse ein).
- Produces: Regeln für Konstrukteur und Prüfer, Stand in CLAUDE.md, Zeile im Design §11, Abschlussbericht.

- [ ] **Step 1: Skill `konstruieren`**

In `.claude/skills/konstruieren/SKILL.md` ersetzen:

```markdown
  `koerper`: „2 Volumenkörper statt 1“).
```

durch:

```markdown
  `koerper`: „2 Volumenkörper statt 1“).
- Schräge Wände eines extrudierten Elements (konischer Zapfen, Einführschräge, Trichter, verjüngter Steg) als
  `formschraege` im `ende` von `extrusion`/`schnitt` (Paket Formschräge, Vorlage `tests/referenz/zentrieraufnahme/`):
  `formschraege: {winkel: "=W", querschnitt: kleiner | groesser}`. Der Winkel (Grad, 0 < winkel < 90) zählt gegen die
  Extrusionsrichtung und ist ein Parameter. `querschnitt` gilt von der Skizze weg für den extrudierten Bereich
  (Material beim Aufsatz, Aussparung beim Schnitt): `kleiner` = Zapfen verjüngt sich, Tasche wird zum Boden enger;
  `groesser` = wird weiter. Bei `mittig` gilt das zu beiden Seiten. Ein Trichter wird von der Seite skizziert, deren
  Durchmesser Anforderung ist (enge Seite → `groesser`, weite Seite → `kleiner`). Seitenflächen eines schrägen
  Features sind nicht achsparallel: nicht mit `{feature, flaeche: "+x"}`/`kanten_an` quer zur Extrusion und nicht
  mit `senkrechte_kanten` ansprechen (`validieren` lehnt das ab), sondern mit `nahe`; Ecken als Eckradius in der
  Skizze (wird mitgeschrägt). `validieren` meldet, wenn das Profil bei `kleiner` zusammenfällt (Kreis, Rechteck,
  Eckradius, Langloch). `swki pruefen` misst Winkel und Richtung jeder Seitenfläche selbst (`formschraegen`);
  `volumen: auto` rechnet Kreis, Rechteck (auch mit Eckradius), Langloch und konvexe Polygone bei `blind`/`mittig`.
```

In `.claude/skills/konstruieren/SKILL.md` ersetzen:

```markdown
6. Kantenverrundungen und Fasen gleichen Maßes in einem Knoten, am Ende des Baums.
```

durch:

```markdown
6. Kantenverrundungen und Fasen gleichen Maßes in einem Knoten, am Ende des Baums.
7. Schräge Wände als `formschraege` an der Extrusion, die das Element erzeugt – nicht als eigenes Feature, nicht als
   Rotation eines Trapezes und nicht als Schnitt mit schräger Skizze.
```

- [ ] **Step 2: Prüfer**

In `.claude/agents/pruefer.md` ersetzen:

```markdown
## Antwort (genau dieses JSON, sonst nichts)
```

durch:

```markdown
## Zusätzlich bei Formschrägen (`formschraege` an `extrusion`/`schnitt`)

- Die Richtung passt zu `querschnitt` (Bilder `vorne`/`rechts`, Blick quer zur Extrusion): `kleiner` – der Zapfen
  verjüngt sich von der Skizze weg, die Tasche wird zum Boden hin enger; `groesser` – der Bereich wird weiter (Trichter
  von der engen Seite aus). Bei `mittig` verjüngt sich das Element zu beiden Seiten.
- Das schräge Element sitzt richtig an: ein Zapfen steht auf der Fläche, ein Steg geht ohne Spalt in die Platte über, eine
  Tasche hat keinen Hinterschnitt.
- `formschraegen` im Prüfbericht ist ok (Winkel je Seitenfläche unter `gemessen`); sonst steht es schon als Mangel im
  Prüfbericht.

## Antwort (genau dieses JSON, sonst nichts)
```

- [ ] **Step 3: CLAUDE.md und Design**

In `CLAUDE.md` ersetzen:

```markdown
Stand: Stufe 3c (Kaufteile, STEP-Import) umgesetzt – Ergebnisse: docs/stufe3c/ergebnisse.md (davor 4b:
docs/stufe4b/ergebnisse.md). Nächste Schritte zur Wahl: Formschräge, Stufe 4c (Nut- und Kurvenverknüpfung), Paket
„Messarten“ (Fasen, Gewinde durch, Lagerachse), Paket Speicher.
```

durch:

```markdown
Stand: Paket Formschräge (Option an Extrusion und Schnitt) umgesetzt – Ergebnisse: docs/formschraege/ergebnisse.md
(davor 3c: docs/stufe3c/ergebnisse.md). Nächste Schritte zur Wahl: Stufe 4c (Nut- und Kurvenverknüpfung), Paket
„Messarten“ (Fasen, Gewinde durch, Lagerachse), Paket Speicher.
```

In `CLAUDE.md` ersetzen:

```markdown
  `speicher_grenze_mb` 10000, ohne `SPEICHER_KNAPP`, weil die Abfrage nur das Dauerniveau sieht).
```

durch:

```markdown
  `speicher_grenze_mb` 10000, ohne `SPEICHER_KNAPP`, weil die Abfrage nur das Dauerniveau sieht).

## Formschräge (Paket Formschräge)
- Schräge Wände nur als `formschraege` im `ende` von `extrusion`/`schnitt` (Regeln im Skill `konstruieren`): Winkel als
  Parameter, Richtung `kleiner`/`groesser` aus Sicht der Skizze. `swki pruefen` misst sie gegen die freigegebene Kopie.
- Ein eigenes Feature für Formschrägen an beliebigen Flächen (`InsertMultiFaceDraft`) gibt es nicht; erst bei Bedarf über
  den Skill `compiler-erweitern`.
- Regressions-Suite enthält die Zentrieraufnahme (`tests/referenz/zentrieraufnahme/`).
```

In `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` ersetzen:

```markdown
| 5 | Zeitauswertung + Jev; optional `swki` als MCP; Blech, Schweiß, Flächen, Formschräge, Zeichnungen | je Erweiterung eigene Referenz |
```

durch:

```markdown
| Formschräge | Option `formschraege` an Extrusion und Schnitt (Richtung über den Querschnitt, Prüfung der Seitenflächen) – Design: [2026-10-07-formschraege-design.md](2026-10-07-formschraege-design.md) | Referenz *Zentrieraufnahme* besteht (Code-Prüfungen und Prüfer), zwei Negativfälle; bisherige Referenzen bestehen weiter |
| 5 | Zeitauswertung + Jev; optional `swki` als MCP; Blech, Schweiß, Flächen, Formschräge an beliebigen Flächen (eigenes Feature), Zeichnungen | je Erweiterung eigene Referenz |
```

Ganze Suite: **1021 passed, 152 deselected**.

- [ ] **Step 4: Regressions-Suite (live)**

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py tests\referenz --zeit 1800`
(Baugruppen-Referenzen je Test auf frischem SolidWorks wie bisher: BLOCKED Neustart an den Controller vor *Stehlager*,
*Linearschlitten*, *Zahnstangentrieb* und *Motorhalter*.) Expected: alle Referenzen `OK`, auch *Zentrieraufnahme*.
Dazu die Live-Suite der berührten Bereiche: `tests\live\test_live_extrusion.py`, `test_live_endbedingungen.py`,
`test_live_pruefen.py`, `test_live_verzahnung.py` → alle `OK` (der Handler ohne `formschraege` ist unverändert).

- [ ] **Step 5: Ergebnisse abschließen**

`docs/formschraege/ergebnisse.md` um diese Abschnitte ergänzen (gemessene Werte eintragen):
- **2. Live-Tests** – Tabelle der 8 Tests aus Task 6 mit Ergebnis, Volumenabweichung und gemessenen Winkeln.
- **3. Referenz Zentrieraufnahme** – Prüfbericht-Auszug (`volumen` Ist/Soll, `formschraegen.gemessen`), Prüfer-Urteil,
  Dauer, Private Bytes (Spitze).
- **4. Negativfälle** – je Fall die Mängelmenge und den Text aus `formschraegen.ist`.
- **5. Regression** – Liste der Referenzen mit Ergebnis; Testzahlen (`pytest -q`: 1021 passed, 152 deselected).
- **6. Abweichungen vom Plan** – jede Ledger-Entscheidung aus Task 5 bis 7 mit Begründung.
- **7. Offene Punkte** – z. B. eigenes Feature `formschraege` (InsertMultiFaceDraft) bei Bedarf, Formschräge an Rotation.

- [ ] **Step 6: Commit**

```powershell
git add .claude/skills/konstruieren/SKILL.md .claude/agents/pruefer.md CLAUDE.md docs/superpowers/specs/2026-09-26-solidworks-ki-design.md docs/formschraege/ergebnisse.md
git commit -m "docs: Paket Formschräge – Skill, Prüfer, CLAUDE.md, Design §11, Ergebnisse (Task 8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
