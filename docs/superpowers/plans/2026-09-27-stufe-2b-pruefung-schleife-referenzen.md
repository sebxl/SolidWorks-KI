# Stufe 2b: Prüfung, Prüfer-Agent, Schleife, Referenzteile – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein gebauter Lauf wird gemessen, gegen die Spezifikation bewertet und abgebildet (`swki pruefen`), ein unabhängiger Prüfer-Agent urteilt anhand von Eingabe, Spezifikation, Prüfbericht und Screenshots, `swki status` steuert die Nachbesserungsschleife, `swki bericht` fasst zusammen; die Referenzteile *Formplatte* und *Buchse* bestehen.

**Architecture:** `swki/pruefung/` trennt reine Bewertung (`geometrie.py`, `bewertung.py`, `schleife.py`, `bericht.py`, ohne SolidWorks testbar) von SolidWorks-Zugriff (`messen.py`, `bilder.py`) und Befehlen (`befehle.py`). Der Ablauf für Claude steht in den Skills `konstruieren` und `compiler-erweitern`, der Prüfer ist ein eigener Agent mit reinem Lesezugriff. Die Referenzteile unter `tests/referenz/` sind die Regressions-Suite (Spec §9, §12).

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 / 2026.

**Voraussetzung:** Plan [2026-09-27-stufe-2a-spezifikation-compiler.md](2026-09-27-stufe-2a-spezifikation-compiler.md) ist vollständig umgesetzt (`swki validieren|freigeben|bauen`, alle Live-Tests grün).

**Spec:** [docs/superpowers/specs/2026-09-26-solidworks-ki-design.md](../specs/2026-09-26-solidworks-ki-design.md) – §6 Prüfung und Nachbesserung, §9 Einbindung in Claude Code, §11 Stufe 2 („Referenzen *Formplatte* und *Buchse* bestehen auf SW 2025 **und** SW 2026“), §12 Tests.

**Herkunft des Codes:** Jede Datei wurde vor dem Schreiben des Plans implementiert und getestet (Unit-Tests grün; Live-Tests und beide Referenzteile mit SOLIDWORKS 2025 Rev. 33.5.0 grün, Screenshots gesichtet). Code **wörtlich** übernehmen; Abweichungen live nicht raten, sondern nachschlagen und im Task-Bericht dokumentieren.

## Global Constraints

- Alle Global Constraints aus Plan 2a gelten unverändert (Late Binding und seine Ausnahmen, mm/Grad, JSON-Ausgabe mit Exit 0/1, nur eigene Dokumente, Speichern nur im Arbeitsordner, Benutzereinstellungen nur über `sw.einstellung`, Live-Tests einzeln mit `tests\live_einzeln.py`, Deutsch, kein Push ohne Rückfrage, Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`).
- `swki pruefen` öffnet den gespeicherten Lauf mit `OpenDoc6`. Ist die Datei schon geöffnet (Warnung 128), **abbrechen** statt sie zu schließen – sie könnte dem Nutzer gehören (S9b).
- Anker werden im fertigen Teil **nicht** neu aufgelöst (der Ankerpunkt kann weggeschnitten sein). Bohrungsachsen kommen aus dem Bauprotokoll (`Knoten.punkte`), Flächen über die Feature-Namen (`IPartDoc.FeatureByName`, Features heißen wie ihre ID).
- Der Prüfer-Agent sieht nur Eingabe, freigegebene Spezifikation, Prüfbericht und Screenshots – nie Protokolle oder Skripte (Spec §6). Er hat nur Lesezugriff; sein Urteil schreibt Claude unverändert nach `protokolle/<spec>.lauf-<n>.pruefer.json`.
- Maximale Läufe = 1 + `max_nachbesserungen` (Vorrang: Spezifikation > Anweisung im Chat > `config/standard.yaml`). Abbruch ohne Fortschritt: sinkt die Zahl offener Mängel gegenüber dem Vorlauf nicht, anhalten (Spec §6).

## Dateistruktur nach diesem Plan

```
swki/pruefung/geometrie.py       Abstände Punkt/Achse/Ebene, analytisches Sollvolumen ("auto")
swki/pruefung/bewertung.py       Messwerte → Prüfungen + Mängel mit Knoten-IDs
swki/pruefung/schleife.py        Läufe lesen, maximale Läufe, Empfehlung
swki/pruefung/bericht.py         bericht.md als Markdown
swki/pruefung/messen.py          gespeicherten Lauf öffnen und messen (SolidWorks)
swki/pruefung/bilder.py          Screenshots iso/vorne/oben/rechts (SolidWorks)
swki/pruefung/befehle.py         swki pruefen | status | bericht
.claude/agents/pruefer.md        unabhängiger Prüfer (nur Read/Glob)
.claude/skills/konstruieren/SKILL.md, .claude/skills/compiler-erweitern/SKILL.md
tests/referenz/buchse/, tests/referenz/formplatte/ (+ skripte/), tests/referenz/test_referenzen.py
docs/stufe2/ergebnisse.md
```

## Dateien eines Laufs

- Arbeitsordner: `<arbeitsordner>/<auftrag>/lauf-<n>/` mit `<auftrag>_<name>.sldprt`, `.step`, `protokoll.json`, `pruefbericht.json`, `bilder/{iso,vorne,oben,rechts}.png`.
- Auftragsordner (im Repo bzw. `auftraege/<auftrag>/`): `protokolle/<spec>.lauf-<n>.protokoll.json`, `….pruefbericht.json`, `….pruefer.json` (`{"bestanden": bool, "maengel": [{"knoten": [...], "beschreibung": "..."}]}`), `bericht.md`.

---

### Task 1: Prüfgeometrie und analytisches Sollvolumen

**Files:**
- Create: `swki/pruefung/__init__.py` (leer), `swki/pruefung/geometrie.py`, `tests/pruefung/__init__.py` (leer), `tests/pruefung/test_geometrie.py`

**Interfaces:**
- Consumes: `Vektor`, `differenz`, `laenge`, `punkt_achse_abstand`, `skalar` (2a Task 5); `auswerten` (2a Task 1).
- Produces: `Messgeometrie(art: "punkt"|"achse"|"ebene", punkt, richtung=None)`; `NichtMessbar(ValueError)`; `abstand(a, b) -> float` (Achsen/Ebenen müssen parallel sein); `volumen_auto(spec) -> (volumen | None, grund)` (Spec §6 „Sollvolumen vorab analytisch, wo möglich“: Extrusion/Schnitt mit Rechteck/Kreis/Polygon, Rotation nach Pappus, Bohrung mit Tiefe, Muster, Spiegeln; `durch_alles`, `durch`, Verrundung, Fase, Skript → nicht berechenbar).

- [ ] **Step 1: Failing tests schreiben**

`tests/pruefung/test_geometrie.py`:

```python
import math

import pytest

from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand, volumen_auto

P = Messgeometrie("punkt", (0, 0, 0))
ACHSE_Y = Messgeometrie("achse", (125, 46, 100), (0, 1, 0))
ACHSE_Y2 = Messgeometrie("achse", (-125, 0, 100), (0, -1, 0))
EBENE_OBEN = Messgeometrie("ebene", (0, 46, 0), (0, 1, 0))
EBENE_UNTEN = Messgeometrie("ebene", (10, 0, 5), (0, -1, 0))


def test_abstaende():
    assert abstand(P, Messgeometrie("punkt", (3, 4, 0))) == pytest.approx(5)
    assert abstand(ACHSE_Y, ACHSE_Y2) == pytest.approx(250)
    assert abstand(P, ACHSE_Y) == pytest.approx(math.hypot(125, 100))
    assert abstand(EBENE_OBEN, EBENE_UNTEN) == pytest.approx(46)
    assert abstand(P, EBENE_OBEN) == pytest.approx(46)
    assert abstand(Messgeometrie("achse", (5, 0, 7), (1, 0, 0)), EBENE_OBEN) == pytest.approx(46)


def test_nicht_parallel():
    with pytest.raises(NichtMessbar):
        abstand(ACHSE_Y, Messgeometrie("achse", (0, 0, 0), (1, 0, 0)))
    with pytest.raises(NichtMessbar):
        abstand(EBENE_OBEN, Messgeometrie("ebene", (0, 0, 0), (1, 0, 0)))
    with pytest.raises(NichtMessbar):
        abstand(ACHSE_Y, EBENE_OBEN)


def _extr(fid, typ, elemente, tiefe):
    return {"id": fid, "typ": typ, "skizze": {"ebene": "oben", "elemente": elemente},
            "ende": {"typ": "blind", "tiefe": tiefe}}


def test_volumen_klotz_mit_tasche_und_bohrungen():
    spec = {"parameter": {"L": 100}, "features": [
        _extr("f1", "extrusion", [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}], 20),
        _extr("f2", "schnitt", [{"kreis": {"mitte": [0, 0], "durchmesser": 10}}], 5),
        {"id": "f3", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[1, 1], [2, 2]],
         "durchmesser": 4, "tiefe": 10, "senkung": {"durchmesser": 6, "tiefe": 2}},
        {"id": "f4", "typ": "muster_linear", "features": ["f3"], "richtung1": {"achse": "x", "abstand": 10, "anzahl": 3}},
        {"id": "f5", "typ": "spiegeln", "features": ["f2"], "ebene": "rechts"},
    ]}
    bohrung = math.pi * 4 * 10 + math.pi * (9 - 4) * 2
    erwartet = 100 * 60 * 20 - 2 * math.pi * 25 * 5 - 2 * bohrung * 3
    volumen, grund = volumen_auto(spec)
    assert grund == "analytisch" and volumen == pytest.approx(erwartet)


def test_volumen_rotation_nach_pappus():
    spec = {"features": [{
        "id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
            {"polygon": {"punkte": [[10, 0], [30, 0], [30, 40], [10, 40]]}},
            {"mittellinie": {"von": [0, -10], "bis": [0, 50]}}]},
    }, {
        "id": "f2", "typ": "rotation", "schnitt": True, "winkel": 180, "skizze": {"ebene": "vorne", "elemente": [
            {"polygon": {"punkte": [[25, 20], [30, 20], [30, 25], [25, 25]]}},
            {"mittellinie": {"von": [0, 0], "bis": [0, 1]}}]},
    }]}
    erwartet = math.pi * (30**2 - 10**2) * 40 - math.pi * (30**2 - 25**2) * 5 / 2
    assert volumen_auto(spec)[0] == pytest.approx(erwartet)


def test_volumen_kreismuster():
    spec = {"features": [
        _extr("f1", "extrusion", [{"polygon": {"punkte": [[0, 0], [10, 0], [0, 10]]}}], 2),
        {"id": "f2", "typ": "muster_kreis", "features": ["f1"], "achse": "y", "anzahl": 4},
    ]}
    assert volumen_auto(spec)[0] == pytest.approx(4 * 50 * 2)


@pytest.mark.parametrize(("feature", "grund"), [
    ({"id": "f2", "typ": "verrundung", "kanten": [{"nahe": [0, 0, 0]}], "radius": 1}, "f2: verrundung"),
    ({"id": "f2", "typ": "bohrung", "flaeche": {"nahe": [0, 0, 0]}, "positionen": [[0, 0]], "durchmesser": 4,
      "durch": True}, "f2: Bohrung durch"),
])
def test_volumen_nicht_berechenbar(feature, grund):
    spec = {"features": [_extr("f1", "extrusion", [{"rechteck": {"mitte": [0, 0], "breite": 1, "hoehe": 1}}], 1),
                         feature]}
    volumen, text = volumen_auto(spec)
    assert volumen is None and text.startswith(grund)
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung/test_geometrie.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementieren**

`swki/pruefung/geometrie.py`:

```python
"""Reine Geometrie für die Prüfung: Abstände zwischen Punkten, Achsen und Ebenen; analytisches Sollvolumen.

Alle Längen in mm.
"""

import math
from dataclasses import dataclass

from swki.compiler.anker import Vektor, differenz, laenge, punkt_achse_abstand, skalar
from swki.spec.ausdruck import auswerten

_PARALLEL = 1.0 - 1e-6


@dataclass
class Messgeometrie:
    art: str  # "punkt" | "achse" | "ebene"
    punkt: Vektor
    richtung: Vektor | None = None  # Achse: Richtung; Ebene: Normale (Einheitsvektoren)


class NichtMessbar(ValueError):
    pass


def abstand(a: Messgeometrie, b: Messgeometrie) -> float:
    """Kürzester Abstand; Achsen/Ebenen müssen zueinander parallel sein, sonst NichtMessbar."""
    if a.art == "punkt" and b.art == "punkt":
        return laenge(differenz(a.punkt, b.punkt))
    if a.art == "punkt" or b.art == "punkt":
        p, g = (a, b) if a.art == "punkt" else (b, a)
        if g.art == "achse":
            return punkt_achse_abstand(p.punkt, g.punkt, g.richtung)
        return abs(skalar(differenz(p.punkt, g.punkt), g.richtung))
    if a.art == "achse" and b.art == "achse":
        if abs(skalar(a.richtung, b.richtung)) < _PARALLEL:
            raise NichtMessbar("Achsen sind nicht parallel")
        return punkt_achse_abstand(a.punkt, b.punkt, b.richtung)
    if a.art == "ebene" and b.art == "ebene":
        if abs(skalar(a.richtung, b.richtung)) < _PARALLEL:
            raise NichtMessbar("Ebenen sind nicht parallel")
        return abs(skalar(differenz(a.punkt, b.punkt), a.richtung))
    achse, ebene = (a, b) if a.art == "achse" else (b, a)
    if abs(skalar(achse.richtung, ebene.richtung)) > 1e-6:
        raise NichtMessbar("Achse ist nicht parallel zur Ebene")
    return abs(skalar(differenz(achse.punkt, ebene.punkt), ebene.richtung))


def _flaeche(element: dict, p: dict) -> float | None:
    if "rechteck" in element:
        r = element["rechteck"]
        return auswerten(r["breite"], p) * auswerten(r["hoehe"], p)
    if "kreis" in element:
        return math.pi * auswerten(element["kreis"]["durchmesser"], p) ** 2 / 4
    if "polygon" in element:
        pts = [(auswerten(x, p), auswerten(y, p)) for x, y in element["polygon"]["punkte"]]
        return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2
    return None


def _pappus(f: dict, p: dict) -> float:
    elemente = f["skizze"]["elemente"]
    linie = next(e["mittellinie"] for e in elemente if "mittellinie" in e)
    a = (auswerten(linie["von"][0], p), auswerten(linie["von"][1], p))
    b = (auswerten(linie["bis"][0], p), auswerten(linie["bis"][1], p))
    d = (b[0] - a[0], b[1] - a[1])
    n = math.hypot(*d)
    volumen = 0.0
    for e in elemente:
        if "polygon" not in e:
            continue
        pts = [(auswerten(x, p), auswerten(y, p)) for x, y in e["polygon"]["punkte"]]
        a2 = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2
        cx = sum((x1 + x2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / (6 * a2)
        cy = sum((y1 + y2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / (6 * a2)
        r = abs(d[0] * (cy - a[1]) - d[1] * (cx - a[0])) / n
        volumen += abs(a2) * 2 * math.pi * r
    return volumen * auswerten(f.get("winkel", 360), p) / 360


def volumen_auto(spec: dict) -> tuple[float | None, str]:
    """Sollvolumen aus der Spezifikation, soweit analytisch möglich (Annahme: Schnitte liegen ganz im Material,
    Aufsätze überlappen nicht). Rückgabe (volumen, grund); volumen None = nicht berechenbar, grund sagt warum."""
    p = spec.get("parameter", {})
    beitrag: dict[str, float] = {}
    for f in spec["features"]:
        typ = f["typ"]
        if typ in ("extrusion", "schnitt"):
            ende = f["ende"]
            if ende["typ"] == "durch_alles":
                return None, f"{f['id']}: durch_alles"
            flaechen = [_flaeche(e, p) for e in f["skizze"]["elemente"]]
            v = sum(flaechen) * auswerten(ende["tiefe"], p)
            beitrag[f["id"]] = -v if typ == "schnitt" else v
        elif typ == "rotation":
            v = _pappus(f, p)
            beitrag[f["id"]] = -v if f.get("schnitt") else v
        elif typ == "bohrung":
            if f.get("durch"):
                return None, f"{f['id']}: Bohrung durch"
            d, t = auswerten(f["durchmesser"], p), auswerten(f["tiefe"], p)
            v = math.pi * d**2 / 4 * t
            if "senkung" in f:
                ds, ts = auswerten(f["senkung"]["durchmesser"], p), auswerten(f["senkung"]["tiefe"], p)
                v += math.pi * (ds**2 - d**2) / 4 * ts
            beitrag[f["id"]] = -v * len(f["positionen"])
        elif typ == "muster_linear":
            kopien = f["richtung1"]["anzahl"] * f.get("richtung2", {}).get("anzahl", 1) - 1
            beitrag[f["id"]] = kopien * sum(beitrag[q] for q in f["features"])
        elif typ == "muster_kreis":
            beitrag[f["id"]] = (f["anzahl"] - 1) * sum(beitrag[q] for q in f["features"])
        elif typ == "spiegeln":
            beitrag[f["id"]] = sum(beitrag[q] for q in f["features"])
        else:
            return None, f"{f['id']}: {typ} nicht analytisch berechenbar"
    return sum(beitrag.values()), "analytisch"
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung/test_geometrie.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```powershell
git add swki/pruefung tests/pruefung
git commit -m "pruefung: Abstände und analytisches Sollvolumen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 2: Bewertung der Messwerte

**Files:**
- Create: `swki/pruefung/bewertung.py`, `tests/pruefung/test_bewertung.py`

**Interfaces:**
- Consumes: `Messgeometrie`, `NichtMessbar`, `abstand`, `volumen_auto` (Task 1); `material_passt` (2a Task 7); `auswerten`.
- Produces: `Messwerte(rebuild_fehler, skizzen, box, volumen, schwerpunkt, material, eigenschaften, messpunkte)`; `messpunkt_schluessel(messpunkt) -> str`; `bewerte(spec, messwerte, standard) -> {bestanden, pruefungen, maengel}`. Prüfungen (Spec §6): `rebuild`, `skizzen` (voll bestimmt), `huellquader` [X, Y, Z], `volumen`, `mass:<was>`, `schwerpunkt` (Spiegel-/Vorzeichenfehler), `material`, `eigenschaften`. Jeder Mangel nennt die Knoten-IDs der Spezifikation (SW-Namen wie `f2_senkung`, `f10_2/Skizze7` werden der ID zugeordnet). Ein nicht berechenbares Sollvolumen ist ein Hinweis (`ok: null`), kein Mangel.

- [ ] **Step 1: Failing tests schreiben**

`tests/pruefung/test_bewertung.py`:

```python
import copy

import pytest

from swki.pruefung.bewertung import Messwerte, bewerte, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}}
VON = {"feature": "f2", "instanz": 1, "achse": True}
ZU = {"feature": "f2", "instanz": 2, "achse": True}
SPEC = {
    "art": "teil", "name": "P", "material": "1.2312", "eigenschaften": {"Benennung": "Platte"},
    "parameter": {"L": 100},
    "features": [
        {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
            {"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]}, "ende": {"typ": "blind", "tiefe": 20}},
    ],
    "pruefung": {
        "huellquader": ["=L", 20, 60],
        "volumen": {"soll": "auto"},
        "masse_pruefen": [{"was": "Achsabstand", "von": VON, "zu": ZU, "soll": 80}],
        "schwerpunkt": {"soll": [0, None, 0]},
    },
}


def _messwerte(**aenderungen) -> Messwerte:
    werte = dict(
        rebuild_fehler=[], skizzen={"f1_skizze": 3}, box=[-50, 0, -30, 50, 20, 30], volumen=120000.0,
        schwerpunkt=(0.0, 10.0, 0.0), material="1.2312 (40CrMnMoS8-6)", eigenschaften={"Benennung": "Platte", "Auftrag": "A"},
        messpunkte={
            messpunkt_schluessel(VON): Messgeometrie("achse", (-40, 20, 0), (0, 1, 0)),
            messpunkt_schluessel(ZU): Messgeometrie("achse", (40, 0, 0), (0, -1, 0)),
        },
    )
    werte.update(aenderungen)
    return Messwerte(**werte)


def test_alles_bestanden():
    bericht = bewerte(SPEC, _messwerte(), STANDARD)
    assert bericht["bestanden"] is True and bericht["maengel"] == []
    ids = [p["id"] for p in bericht["pruefungen"]]
    assert ids == ["rebuild", "skizzen", "huellquader", "volumen", "mass:Achsabstand", "schwerpunkt", "material",
                   "eigenschaften"]


def test_maengel_mit_knoten():
    spec = copy.deepcopy(SPEC)
    spec["features"].append({"id": "f2", "typ": "skript", "datei": "skripte/f2.py", "luecke": "Gewinde"})
    m = _messwerte(rebuild_fehler=["f2_senkung: Code 71"], skizzen={"f1/f1_skizze": 3, "f2_2/Skizze7": 2},
                   box=[-50, 0, -30, 50, 21, 30], volumen=118000.0)
    bericht = bewerte(spec, m, STANDARD)
    assert bericht["bestanden"] is False
    maengel = {x["pruefung"]: x for x in bericht["maengel"]}
    assert maengel["rebuild"]["knoten"] == ["f2"]
    assert maengel["skizzen"]["knoten"] == ["f2"]
    assert maengel["huellquader"]["beschreibung"] == "huellquader: ist [100, 21, 60] statt [100.0, 20.0, 60.0]"
    assert "volumen" not in maengel  # mit Skript ist das Sollvolumen nicht analytisch berechenbar (Hinweis, kein Mangel)


def test_masspruefung_falsch_und_nicht_messbar():
    m = _messwerte()
    m.messpunkte[messpunkt_schluessel(ZU)] = Messgeometrie("achse", (41, 0, 0), (0, 1, 0))
    [mangel] = bewerte(SPEC, m, STANDARD)["maengel"]
    assert mangel["knoten"] == ["f2"] and "ist 81" in mangel["beschreibung"]
    m.messpunkte[messpunkt_schluessel(ZU)] = "REFERENZ_NICHT_GEFUNDEN: keine Zylinderfläche für Instanz 2"
    [mangel] = bewerte(SPEC, m, STANDARD)["maengel"]
    assert "Instanz 2" in mangel["beschreibung"]


def test_volumen_nicht_berechenbar_ist_kein_mangel():
    spec = copy.deepcopy(SPEC)
    spec["features"].append({"id": "f2", "typ": "verrundung", "kanten": [{"nahe": [0, 0, 0]}], "radius": 2})
    bericht = bewerte(spec, _messwerte(), STANDARD)
    volumen = next(p for p in bericht["pruefungen"] if p["id"] == "volumen")
    assert volumen["ok"] is None and "f2: verrundung" in volumen["hinweis"]
    assert bericht["bestanden"] is True


def test_material_und_eigenschaften():
    bericht = bewerte(SPEC, _messwerte(material="Stahl", eigenschaften={}), STANDARD)
    assert {x["pruefung"] for x in bericht["maengel"]} == {"material", "eigenschaften"}


def test_schwerpunkt_spiegelfehler():
    [mangel] = bewerte(SPEC, _messwerte(schwerpunkt=(0.0, 10.0, -3.0)), STANDARD)["maengel"]
    assert mangel["pruefung"] == "schwerpunkt"


@pytest.mark.parametrize("mp", [VON, {"punkt": [0, 0, 0]}, {"feature": "f1", "flaeche": "+y"}])
def test_messpunkt_schluessel_stabil(mp):
    assert messpunkt_schluessel(mp) == messpunkt_schluessel(dict(reversed(list(mp.items()))))
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung/test_bewertung.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementieren**

`swki/pruefung/bewertung.py`:

```python
"""Bewertung der Messwerte gegen die Spezifikation (ohne SolidWorks) → Prüfungen und Mängel mit Knoten-IDs."""

from dataclasses import dataclass, field

from swki.compiler.eigenschaften import material_passt
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand, volumen_auto
from swki.spec.ausdruck import auswerten

SKIZZE_VOLL_BESTIMMT = 3  # swConstrainedStatus_e.swFullyConstrained
_TOL_HUELLQUADER = 0.01
_TOL_MASS = 0.01
_TOL_SCHWERPUNKT = 0.05


@dataclass
class Messwerte:
    rebuild_fehler: list[str]  # ["f3: Code 71"]
    skizzen: dict[str, int]  # Skizzenname → swConstrainedStatus_e
    box: list[float]  # [xmin, ymin, zmin, xmax, ymax, zmax] mm
    volumen: float  # mm³
    schwerpunkt: tuple[float, float, float]  # mm
    material: str
    eigenschaften: dict[str, str]
    messpunkte: dict[str, Messgeometrie | str] = field(default_factory=dict)  # Schlüssel → Geometrie oder Fehlertext


def messpunkt_schluessel(messpunkt: dict) -> str:
    return ",".join(f"{k}={messpunkt[k]}" for k in sorted(messpunkt))


def _knoten_aus(text: str, ids: list[str]) -> str:
    """SW-Name ("f2_senkung: Code 71", "f10_2/Skizze7", "f1_skizze") → Feature-ID der Spezifikation."""
    name = text.split(":")[0].split("/")[0].strip()
    passend = [i for i in ids if name == i or name.startswith(f"{i}_")]
    return max(passend, key=len) if passend else name


def _pruefung(pid: str, ok: bool | None, **daten) -> dict:
    return {"id": pid, "ok": ok, **daten}


def bewerte(spec: dict, m: Messwerte, standard: dict) -> dict:
    p = spec.get("parameter", {})
    pr = spec.get("pruefung", {})
    ergebnisse = []

    ids = [f["id"] for f in spec["features"]]
    knoten = sorted({_knoten_aus(t, ids) for t in m.rebuild_fehler})
    ergebnisse.append(_pruefung("rebuild", not m.rebuild_fehler, ist=m.rebuild_fehler, knoten=knoten))

    offen = {n: s for n, s in m.skizzen.items() if s != SKIZZE_VOLL_BESTIMMT}
    ergebnisse.append(_pruefung("skizzen", not offen, ist=offen, knoten=sorted({_knoten_aus(n, ids) for n in offen})))

    if "huellquader" in pr:
        soll = [auswerten(v, p) for v in pr["huellquader"]]
        ist = [round(m.box[i + 3] - m.box[i], 6) for i in range(3)]
        tol = pr.get("huellquader_tol", _TOL_HUELLQUADER)
        ok = all(abs(a - b) <= tol for a, b in zip(ist, soll))
        ergebnisse.append(_pruefung("huellquader", ok, ist=ist, soll=soll, tol=tol, knoten=[]))

    if "volumen" in pr:
        roh = pr["volumen"]["soll"]
        soll, grund = volumen_auto(spec) if roh == "auto" else (auswerten(roh, p), "vorgegeben")
        prozent = pr["volumen"].get("toleranz_prozent", standard["toleranzen"]["volumen_prozent"])
        if soll is None:
            ergebnisse.append(_pruefung("volumen", None, ist=m.volumen, hinweis=f"Sollvolumen nicht berechenbar ({grund})",
                                        knoten=[]))
        else:
            abweichung = abs(m.volumen - soll) / soll * 100
            ergebnisse.append(_pruefung("volumen", abweichung <= prozent, ist=round(m.volumen, 3), soll=round(soll, 3),
                                        abweichung_prozent=round(abweichung, 4), tol_prozent=prozent, knoten=[]))

    for mp in pr.get("masse_pruefen", []):
        von, zu = m.messpunkte.get(messpunkt_schluessel(mp["von"])), m.messpunkte.get(messpunkt_schluessel(mp["zu"]))
        knoten = sorted({x["feature"] for x in (mp["von"], mp["zu"]) if "feature" in x})
        soll, tol = auswerten(mp["soll"], p), mp.get("tol", _TOL_MASS)
        if isinstance(von, str) or isinstance(zu, str) or von is None or zu is None:
            fehler = next(x for x in (von, zu, "Messpunkt fehlt") if isinstance(x, str))
            ergebnisse.append(_pruefung(f"mass:{mp['was']}", False, soll=soll, hinweis=fehler, knoten=knoten))
            continue
        try:
            ist = round(abstand(von, zu), 6)
        except NichtMessbar as e:
            ergebnisse.append(_pruefung(f"mass:{mp['was']}", False, soll=soll, hinweis=str(e), knoten=knoten))
            continue
        ergebnisse.append(_pruefung(f"mass:{mp['was']}", abs(ist - soll) <= tol, ist=ist, soll=soll, tol=tol, knoten=knoten))

    if "schwerpunkt" in pr:
        soll = [None if v is None else auswerten(v, p) for v in pr["schwerpunkt"]["soll"]]
        tol = pr["schwerpunkt"].get("tol", _TOL_SCHWERPUNKT)
        ist = [round(v, 6) for v in m.schwerpunkt]
        ok = all(s is None or abs(i - s) <= tol for i, s in zip(ist, soll))
        ergebnisse.append(_pruefung("schwerpunkt", ok, ist=ist, soll=soll, tol=tol, knoten=[]))

    if "material" in spec:
        ergebnisse.append(_pruefung("material", material_passt(m.material, spec["material"]), ist=m.material, soll=spec["material"],
                                    knoten=[]))

    soll_eig = spec.get("eigenschaften", {})
    abweichend = {k: m.eigenschaften.get(k) for k, v in soll_eig.items() if m.eigenschaften.get(k) != v}
    ergebnisse.append(_pruefung("eigenschaften", not abweichend, ist=abweichend, soll=soll_eig, knoten=[]))

    maengel = [
        {"pruefung": e["id"], "knoten": e["knoten"], "beschreibung": _beschreibung(e)}
        for e in ergebnisse if e["ok"] is False
    ]
    return {"bestanden": not maengel, "pruefungen": ergebnisse, "maengel": maengel}


def _beschreibung(e: dict) -> str:
    if "hinweis" in e:
        return f"{e['id']}: {e['hinweis']}"
    if "soll" in e:
        return f"{e['id']}: ist {e.get('ist')} statt {e['soll']}"
    return f"{e['id']}: {e.get('ist')}"
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung/test_bewertung.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```powershell
git add swki/pruefung tests/pruefung
git commit -m "pruefung: Bewertung mit Mängeln je Knoten" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 3: Schleife und Bericht

**Files:**
- Create: `swki/pruefung/schleife.py`, `swki/pruefung/bericht.py`, `tests/pruefung/test_schleife.py`, `tests/pruefung/test_bericht.py`

**Interfaces:**
- Consumes: `lauf_datei`, `protokoll_ordner` (2a Task 4).
- Produces: `lies_laeufe(spec_pfad) -> list[dict]` (`{lauf, bau, dauer_s, code_maengel, pruefer, pruefer_maengel, offen, bestanden}`); `max_laeufe(spec, standard, anweisung=None) -> int`; `empfehlung(laeufe, maximal) -> (code, text)` mit `code` ∈ `bauen | pruefen | pruefer | bestanden | stopp_kein_fortschritt | stopp_max | nachbessern`; `bericht_markdown(spec, auftrag, laeufe, empfehlung, letzter_bericht, letztes_urteil, letztes_protokoll, compiler_aenderungen) -> str` (Spec §6: Status, Läufe, offene Punkte, Screenshots, Phasenzeiten, Compiler-Änderungen).

- [ ] **Step 1: Failing tests schreiben**

`tests/pruefung/test_schleife.py`:

```python
import json

import pytest

from swki.auftrag import lauf_datei
from swki.pruefung.schleife import empfehlung, lies_laeufe, max_laeufe

STANDARD = {"max_nachbesserungen": 3}


def _schreibe(spec_pfad, lauf, art, daten):
    pfad = lauf_datei(spec_pfad, lauf, art)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten), encoding="utf-8")


def _lauf(spec_pfad, n, bau="ok", code=None, pruefer=None):
    _schreibe(spec_pfad, n, "protokoll", {"status": bau, "dauer_s": 12.5})
    if code is not None:
        _schreibe(spec_pfad, n, "pruefbericht", {"bestanden": not code, "maengel": [{}] * code})
    if pruefer is not None:
        _schreibe(spec_pfad, n, "pruefer", {"bestanden": not pruefer, "maengel": [{}] * pruefer})


def test_laeufe_lesen(tmp_path):
    spec = tmp_path / "platte.yaml"
    _lauf(spec, 1, bau="fehler")
    _lauf(spec, 2, code=2, pruefer=1)
    _lauf(spec, 10, code=0, pruefer=0)
    _schreibe(tmp_path / "andere.yaml", 1, "protokoll", {"status": "ok", "dauer_s": 1})
    laeufe = lies_laeufe(spec)
    assert [x["lauf"] for x in laeufe] == [1, 2, 10]
    assert [x["offen"] for x in laeufe] == [1, 3, 0]
    assert laeufe[0]["pruefer"] == "ausstehend" and laeufe[1]["pruefer"] == "maengel"
    assert [x["bestanden"] for x in laeufe] == [False, False, True]


def test_keine_laeufe(tmp_path):
    assert lies_laeufe(tmp_path / "platte.yaml") == []
    assert empfehlung([], 4)[0] == "bauen"


def test_max_laeufe_vorrang():
    assert max_laeufe({}, STANDARD) == 4
    assert max_laeufe({}, STANDARD, anweisung=1) == 2
    assert max_laeufe({"max_nachbesserungen": 5}, STANDARD, anweisung=1) == 6


@pytest.mark.parametrize(("laeufe", "erwartet"), [
    ([dict(lauf=1, bau="ok", code_maengel=None, pruefer="ausstehend", offen=0, bestanden=False)], "pruefen"),
    ([dict(lauf=1, bau="ok", code_maengel=0, pruefer="ausstehend", offen=0, bestanden=False)], "pruefer"),
    ([dict(lauf=1, bau="ok", code_maengel=0, pruefer="bestanden", offen=0, bestanden=True)], "bestanden"),
    ([dict(lauf=1, bau="fehler", code_maengel=None, pruefer="ausstehend", offen=1, bestanden=False)], "nachbessern"),
    ([dict(lauf=1, bau="ok", code_maengel=2, pruefer="maengel", offen=3, bestanden=False),
      dict(lauf=2, bau="ok", code_maengel=2, pruefer="maengel", offen=3, bestanden=False)], "stopp_kein_fortschritt"),
    ([dict(lauf=1, bau="ok", code_maengel=3, pruefer="maengel", offen=4, bestanden=False),
      dict(lauf=2, bau="ok", code_maengel=1, pruefer="maengel", offen=2, bestanden=False)], "stopp_max"),
])
def test_empfehlung(laeufe, erwartet):
    assert empfehlung(laeufe, 2)[0] == erwartet
```

`tests/pruefung/test_bericht.py`:

```python
from swki.pruefung.bericht import bericht_markdown

LAEUFE = [
    {"lauf": 1, "bau": "fehler", "code_maengel": None, "pruefer": "ausstehend", "offen": 1, "dauer_s": 8.1},
    {"lauf": 2, "bau": "ok", "code_maengel": 0, "pruefer": "bestanden", "offen": 0, "dauer_s": 9.4},
]


def test_bestandener_auftrag():
    md = bericht_markdown(
        {"name": "Platte"}, "A-1", LAEUFE, ("bestanden", "Lauf 2 bestanden: Bericht schreiben"),
        {"maengel": [], "bilder": {"iso": "C:/arbeit/A-1/lauf-2/iso.png"}}, {"bestanden": True, "maengel": []},
        {"phasen": {"bauen": 6.2, "speichern": 1.1}, "fehler": None},
        ["abc1234 compiler: fase mit Tangentenfortsetzung"],
    )
    assert md.startswith("# Bericht Platte (Auftrag A-1)\n")
    assert "**Status:** bestanden" in md
    assert "| 1 | fehler | – | ausstehend | 1 | 8.1 |" in md
    assert "- iso: `C:/arbeit/A-1/lauf-2/iso.png`" in md
    assert "| bauen | 6.2 |" in md
    assert "- abc1234 compiler: fase mit Tangentenfortsetzung" in md
    assert "## Offene Punkte (letzter Lauf)\n\n- keine" in md


def test_offene_punkte_mit_knoten():
    md = bericht_markdown(
        {"name": "Platte"}, "A-1", LAEUFE[:1], ("stopp_max", "…"),
        {"maengel": [{"knoten": ["f2"], "beschreibung": "mass:Abstand: ist 81 statt 80"}]},
        {"bestanden": False, "maengel": [{"knoten": [], "beschreibung": "Fase fehlt oben"}]},
        {"phasen": {}, "fehler": {"code": "REFERENZ_MEHRDEUTIG", "meldung": "2 Kanten"}},
        [],
    )
    assert "**Status:** offen (stopp_max)" in md
    assert "- Bau abgebrochen: REFERENZ_MEHRDEUTIG – 2 Kanten" in md
    assert "- f2: mass:Abstand: ist 81 statt 80" in md
    assert "- Teil: Fase fehlt oben (Prüfer)" in md
    assert "## Compiler-Änderungen während des Auftrags\n\n- keine" in md
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung/test_schleife.py tests/pruefung/test_bericht.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementieren**

`swki/pruefung/schleife.py`:

```python
"""Stand der Nachbesserungsschleife eines Auftrags: Läufe, offene Mängel, Empfehlung für den nächsten Schritt.

Dateien je Lauf im Auftragsordner (protokolle/):
  <spec>.lauf-<n>.protokoll.json     (swki bauen)
  <spec>.lauf-<n>.pruefbericht.json  (swki pruefen)
  <spec>.lauf-<n>.pruefer.json       (Urteil des Prüfer-Agenten, von Claude geschrieben:
                                      {"bestanden": bool, "maengel": [{"knoten": [...], "beschreibung": "..."}]})
"""

import json
import re
from pathlib import Path

from swki.auftrag import lauf_datei, protokoll_ordner


def _lies(pfad: Path) -> dict | None:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else None


def lies_laeufe(spec_pfad: Path) -> list[dict]:
    muster = re.compile(rf"^{re.escape(spec_pfad.stem)}\.lauf-(\d+)\.protokoll\.json$")
    ordner = protokoll_ordner(spec_pfad)
    nummern = sorted(int(m.group(1)) for p in (ordner.iterdir() if ordner.is_dir() else ()) if (m := muster.match(p.name)))
    laeufe = []
    for n in nummern:
        protokoll = _lies(lauf_datei(spec_pfad, n, "protokoll"))
        bericht = _lies(lauf_datei(spec_pfad, n, "pruefbericht"))
        urteil = _lies(lauf_datei(spec_pfad, n, "pruefer"))
        bau_ok = protokoll["status"] == "ok"
        code_maengel = len(bericht["maengel"]) if bericht else None
        pruefer_maengel = len(urteil["maengel"]) if urteil else None
        offen = (0 if bau_ok else 1) + (code_maengel or 0) + (pruefer_maengel or 0)
        laeufe.append({
            "lauf": n,
            "bau": protokoll["status"],
            "dauer_s": protokoll["dauer_s"],
            "code_maengel": code_maengel,
            "pruefer": "ausstehend" if urteil is None else ("bestanden" if urteil["bestanden"] else "maengel"),
            "pruefer_maengel": pruefer_maengel,
            "offen": offen,
            "bestanden": bau_ok and bericht is not None and bericht["bestanden"] and urteil is not None
            and urteil["bestanden"],
        })
    return laeufe


def max_laeufe(spec: dict, standard: dict, anweisung: int | None = None) -> int:
    """Erster Lauf + Nachbesserungen; Vorrang: Spezifikation > Anweisung im Chat > config/standard.yaml."""
    nachbesserungen = spec.get("max_nachbesserungen") or anweisung or standard["max_nachbesserungen"]
    return 1 + nachbesserungen


def empfehlung(laeufe: list[dict], maximal: int) -> tuple[str, str]:
    if not laeufe:
        return "bauen", "Noch kein Lauf: swki bauen"
    letzter = laeufe[-1]
    if letzter["bau"] == "ok" and letzter["code_maengel"] is None:
        return "pruefen", f"Lauf {letzter['lauf']} prüfen: swki pruefen --lauf {letzter['lauf']}"
    if letzter["bau"] == "ok" and letzter["pruefer"] == "ausstehend":
        return "pruefer", f"Prüfer-Agent für Lauf {letzter['lauf']} starten und Urteil ablegen"
    if letzter["bestanden"]:
        return "bestanden", f"Lauf {letzter['lauf']} bestanden: Bericht schreiben"
    if len(laeufe) >= 2 and letzter["offen"] >= laeufe[-2]["offen"]:
        return "stopp_kein_fortschritt", (
            f"Offene Mängel {laeufe[-2]['offen']} → {letzter['offen']}: kein Fortschritt, anhalten und Nutzer informieren"
        )
    if len(laeufe) >= maximal:
        return "stopp_max", f"{len(laeufe)} von {maximal} Läufen verbraucht: anhalten und Nutzer informieren"
    return "nachbessern", f"Bauweg ändern und neu bauen (Lauf {letzter['lauf'] + 1} von höchstens {maximal})"
```

`swki/pruefung/bericht.py`:

```python
"""bericht.md eines Auftrags: Status, Läufe, offene Punkte, Screenshots, Phasenzeiten, Compiler-Änderungen."""


def _zelle(wert) -> str:
    return "–" if wert is None else str(wert)


def bericht_markdown(
    spec: dict, auftrag: str, laeufe: list[dict], empfehlung: tuple[str, str],
    letzter_bericht: dict | None, letztes_urteil: dict | None, letztes_protokoll: dict | None,
    compiler_aenderungen: list[str],
) -> str:
    code, text = empfehlung
    status = "bestanden" if code == "bestanden" else f"offen ({code})"
    zeilen = [
        f"# Bericht {spec['name']} (Auftrag {auftrag})",
        "",
        f"**Status:** {status} – {text}",
        "",
        "## Läufe",
        "",
        "| Lauf | Bau | Code-Mängel | Prüfer | Offen | Dauer (s) |",
        "|---|---|---|---|---|---|",
    ]
    for lauf in laeufe:
        zeilen.append(
            f"| {lauf['lauf']} | {lauf['bau']} | {_zelle(lauf['code_maengel'])} | {lauf['pruefer']} "
            f"| {lauf['offen']} | {lauf['dauer_s']} |"
        )
    zeilen += ["", "## Offene Punkte (letzter Lauf)", ""]
    offene = []
    if letztes_protokoll and letztes_protokoll.get("fehler"):
        f = letztes_protokoll["fehler"]
        offene.append(f"Bau abgebrochen: {f.get('code')} – {f.get('meldung')}")
    offene += [f"{', '.join(m['knoten']) or 'Teil'}: {m['beschreibung']}" for m in (letzter_bericht or {}).get("maengel", [])]
    offene += [f"{', '.join(m['knoten']) or 'Teil'}: {m['beschreibung']} (Prüfer)" for m in (letztes_urteil or {}).get("maengel", [])]
    zeilen += [f"- {o}" for o in offene] or ["- keine"]
    zeilen += ["", "## Screenshots (letzter Lauf)", ""]
    bilder = (letzter_bericht or {}).get("bilder", {})
    zeilen += [f"- {name}: `{pfad}`" for name, pfad in bilder.items()] or ["- keine"]
    zeilen += ["", "## Phasenzeiten (letzter Lauf)", "", "| Phase | s |", "|---|---|"]
    for phase, sekunden in (letztes_protokoll or {}).get("phasen", {}).items():
        zeilen.append(f"| {phase} | {sekunden} |")
    zeilen += ["", "## Compiler-Änderungen während des Auftrags", ""]
    zeilen += [f"- {c}" for c in compiler_aenderungen] or ["- keine"]
    return "\n".join(zeilen) + "\n"
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung -v`
Expected: alle grün (Schleife + Bericht: 11 passed).

- [ ] **Step 5: Commit**

```powershell
git add swki/pruefung tests/pruefung
git commit -m "pruefung: Nachbesserungsschleife und Bericht" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 4: Messen, Screenshots und `swki pruefen | status | bericht`

**Files:**
- Create: `swki/pruefung/messen.py`, `swki/pruefung/bilder.py`, `swki/pruefung/befehle.py`, `tests/live/test_live_pruefen.py`
- Modify: `swki/cli.py` (`_befehlsgruppen`)

**Interfaces:**
- Consumes: `sw.*`, `flaechen`, `flaeche_in_richtung`, `zylinder_zu_punkten`, `lies_eigenschaften`, `Kontext`, `FeatureErgebnis` (2a); `bewerte`, `Messwerte`, `messpunkt_schluessel` (Task 2); `lies_laeufe`, `max_laeufe`, `empfehlung`, `bericht_markdown` (Task 3).
- Produces (`messen.py`): `PruefFehler(SwkiFehler)`; `oeffne(app, pfad)` (bricht bei „bereits geöffnet“ ab); `skizzenstatus(model)` (auch Unterskizzen als `<Feature>/<Skizze>`); `rebuild_fehler(model)`; `kontext_aus_datei(app, model, spec, spec_pfad, tol_mm, protokoll)`; `messpunkte(ctx, spec)`; `messe(ctx) -> Messwerte`.
- Produces (`bilder.py`): `ANSICHTEN = {iso: 7, vorne: 1, oben: 5, rechts: 4}`; `screenshots(model, ordner) -> dict`.
- Befehle: `swki pruefen <spec> [--lauf N]` (Vorgabe letzter Lauf; Exit 0 auch bei Mängeln – `bestanden` steht im JSON), `swki status <spec> [--max N]`, `swki bericht <spec>` (schreibt `bericht.md`, Compiler-Änderungen aus `git log --since=<erster Lauf> -- swki/compiler schema`).

- [ ] **Step 1: Live-Tests schreiben**

`tests/live/test_live_pruefen.py`:

```python
"""Live: swki pruefen, status, bericht an einer kleinen Platte (SolidWorks muss laufen)."""

import json
import shutil

import pytest
import yaml

from swki.auftrag import lauf_datei
from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-PRUEFEN"
SPEC = {
    "art": "teil", "name": "Platte", "material": "1.2312", "eigenschaften": {"Benennung": "Prüfplatte"},
    "parameter": {"L": 100},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}},
        {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
         "positionen": [["=-L/2+15", 0], ["=L/2-15", 0]], "durchmesser": 8, "durch": True},
    ],
    "pruefung": {
        "huellquader": ["=L", 20, 60],
        "volumen": {"soll": 120000 - 2 * 3.141592653589793 * 16 * 20, "toleranz_prozent": 0.1},
        "masse_pruefen": [
            {"was": "Bohrungsabstand", "von": {"feature": "f2", "instanz": 1, "achse": True},
             "zu": {"feature": "f2", "instanz": 2, "achse": True}, "soll": 70},
            {"was": "Dicke", "von": {"feature": "f1", "flaeche": "-y"}, "zu": {"feature": "f1", "flaeche": "+y"},
             "soll": 20},
        ],
        "schwerpunkt": {"soll": [0, 10, 0]},
    },
}


@pytest.fixture
def spec_pfad(tmp_path):
    ordner = tmp_path / AUFTRAG
    ordner.mkdir()
    pfad = ordner / "platte.yaml"
    yield pfad
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _bauen(capsys, pfad, spec):
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, daten = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, daten


def test_pruefen_bestanden_und_status(capsys, spec_pfad):
    _bauen(capsys, spec_pfad, SPEC)
    assert _lauf(capsys, "status", str(spec_pfad))[1]["empfehlung"] == "pruefen"
    code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
    assert code == 0
    assert bericht["bestanden"] is True, bericht["maengel"]
    ergebnisse = {p["id"]: p for p in bericht["pruefungen"]}
    assert ergebnisse["mass:Bohrungsabstand"]["ist"] == pytest.approx(70)
    assert ergebnisse["material"]["ist"].startswith("1.2312")
    assert lauf_datei(spec_pfad, 1, "pruefbericht").exists()
    assert _lauf(capsys, "status", str(spec_pfad))[1]["empfehlung"] == "pruefer"
    lauf_datei(spec_pfad, 1, "pruefer").write_text('{"bestanden": true, "maengel": []}', encoding="utf-8")
    assert _lauf(capsys, "status", str(spec_pfad))[1]["empfehlung"] == "bestanden"
    code, daten = _lauf(capsys, "bericht", str(spec_pfad))
    assert code == 0 and daten["status"] == "bestanden"
    assert "**Status:** bestanden" in (spec_pfad.parent / "bericht.md").read_text(encoding="utf-8")


def test_pruefen_findet_mangel_mit_knoten(capsys, spec_pfad):
    falsch = json.loads(json.dumps(SPEC))
    falsch["pruefung"]["masse_pruefen"][0]["soll"] = 71
    _bauen(capsys, spec_pfad, falsch)
    code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
    assert code == 0 and bericht["bestanden"] is False
    assert bericht["maengel"] == [{
        "pruefung": "mass:Bohrungsabstand", "knoten": ["f2"],
        "beschreibung": "mass:Bohrungsabstand: ist 70.0 statt 71.0",
    }]
```

- [ ] **Step 2: Live-Tests fehlschlagen lassen (SolidWorks geöffnet)**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_pruefen.py`
Expected: 2× `FEHLER` (Befehl `status`/`pruefen` unbekannt).

- [ ] **Step 3: Implementieren**

`swki/pruefung/messen.py`:

```python
"""Messwerte eines gespeicherten Laufs aus SolidWorks lesen (Spike S9b, Bausteine 19 und 23)."""

from pathlib import Path

from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.anker import AnkerFehler, flaeche_in_richtung, laenge, zylinder_zu_punkten
from swki.compiler.eigenschaften import lies_eigenschaften
from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import FeatureErgebnis, Kontext
from swki.compiler.topologie import flaechen
from swki.pruefung.bewertung import Messwerte, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from swki.verbindung import byref_long, byref_str, in_mm, in_mm3

SW_DOC_PART = 1  # swDocumentTypes_e
SW_OPEN_SILENT = 1  # swOpenDocOptions_e
SW_WARNUNG_BEREITS_OFFEN = 128  # swFileLoadWarning_AlreadyOpen


class PruefFehler(SwkiFehler):
    pass


def oeffne(app, pfad: Path):
    """Öffnet ein gespeichertes Teil. Ist es schon offen (evtl. beim Nutzer), wird abgebrochen statt es zu schließen."""
    fehler, warnungen = byref_long(), byref_long()
    model = app.OpenDoc6(str(pfad), SW_DOC_PART, SW_OPEN_SILENT, "", fehler, warnungen)
    if model is None:
        raise PruefFehler(f"{pfad.name} ließ sich nicht öffnen (Fehler {fehler.value})")
    if warnungen.value & SW_WARNUNG_BEREITS_OFFEN:
        raise PruefFehler(f"{pfad.name} ist bereits in SolidWorks geöffnet – bitte schließen und erneut prüfen")
    return model


def skizzenstatus(model) -> dict[str, int]:
    """Bestimmtheitsstatus aller Skizzen. Von Features aufgenommene Skizzen heißen "<Feature>/<Skizze>",
    damit ein Mangel dem Knoten der Spezifikation zugeordnet werden kann (z. B. "f10/Skizze7")."""
    status = {}
    f = model.FirstFeature
    while f is not None:
        if f.GetTypeName2 == "ProfileFeature":
            status[f.Name] = f.GetSpecificFeature2.GetConstrainedStatus
        unter = f.GetFirstSubFeature
        while unter is not None:
            if unter.GetTypeName2 == "ProfileFeature":
                status[f"{f.Name}/{unter.Name}"] = unter.GetSpecificFeature2.GetConstrainedStatus
            unter = unter.GetNextSubFeature
        f = f.GetNextFeature
    return status


def rebuild_fehler(model) -> list[str]:
    try:
        sw.rebuild(model)
    except BauFehler as e:
        return [t.strip() for t in str(e).split(";")]
    return []


def kontext_aus_datei(app, model, spec: dict, spec_pfad: Path, tol_mm: float, protokoll: dict) -> Kontext:
    """Kontext für ein geöffnetes Teil: Features über ihre Namen (= Feature-IDs), Bohrungspunkte aus dem Bauprotokoll.

    Anker werden bewusst nicht neu aufgelöst: im fertigen Teil kann der Ankerpunkt weggeschnitten sein.
    """
    punkte = {k["id"]: k.get("punkte") or [] for k in protokoll["knoten"]}
    ctx = Kontext(app, model, spec, spec_pfad, tol_mm)
    for f in spec["features"]:
        feature = model.FeatureByName(f["id"])
        if feature is not None:
            ctx.ergebnisse[f["id"]] = FeatureErgebnis([feature], punkte=[tuple(p) for p in punkte.get(f["id"], [])])
    return ctx


def _messgeometrie(ctx, spec: dict, mp: dict) -> Messgeometrie:
    if "punkt" in mp:
        return Messgeometrie("punkt", tuple(ctx.wert(v) for v in mp["punkt"]))
    if mp["feature"] not in ctx.ergebnisse:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Feature {mp['feature']!r} fehlt im Teil")
    feature = ctx.ergebnis(mp["feature"]).features[0]
    if "flaeche" in mp:
        f = flaeche_in_richtung(flaechen(feature), mp["flaeche"])
        return Messgeometrie("ebene", f.punkt, f.normale)
    punkte = ctx.ergebnis(mp["feature"]).punkte
    if not punkte:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Feature {mp['feature']} hat keine Bohrungsinstanzen im Protokoll")
    if mp["instanz"] > len(punkte):
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Bohrung {mp['feature']} hat nur {len(punkte)} Instanzen")
    punkt = punkte[mp["instanz"] - 1]
    [zylinder] = zylinder_zu_punkten(flaechen(feature), [punkt], ctx.tol_mm)
    n = laenge(zylinder.achse)
    return Messgeometrie("achse", punkt, tuple(c / n for c in zylinder.achse))


def messpunkte(ctx, spec: dict) -> dict[str, Messgeometrie | str]:
    ergebnis = {}
    for mp in spec.get("pruefung", {}).get("masse_pruefen", []):
        for punkt in (mp["von"], mp["zu"]):
            try:
                ergebnis[messpunkt_schluessel(punkt)] = _messgeometrie(ctx, spec, punkt)
            except BauFehler as e:
                ergebnis[messpunkt_schluessel(punkt)] = f"{e.code}: {e}"
    return ergebnis


def messe(ctx) -> Messwerte:
    model = ctx.model
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return Messwerte(
        rebuild_fehler=rebuild_fehler(model),
        skizzen=skizzenstatus(model),
        box=sw.teilebox_mm(model),
        volumen=in_mm3(mp.Volume),
        schwerpunkt=tuple(in_mm(c) for c in mp.CenterOfMass),
        material=model.GetMaterialPropertyName2("", byref_str()) or "",
        eigenschaften=lies_eigenschaften(model),
        messpunkte=messpunkte(ctx, ctx.spec),
    )
```

`swki/pruefung/bilder.py`:

```python
"""Screenshots der Standardansichten (Spike S4/S9b): ShowNamedView2 + SaveAs3 als Kopie (.png)."""

from pathlib import Path

from swki.compiler import sw

ANSICHTEN = {"iso": 7, "vorne": 1, "oben": 5, "rechts": 4}  # swStandardViews_e


def screenshots(model, ordner: Path) -> dict[str, str]:
    # Nur als echter Methodenaufruf wird eingepasst; der reine Attributzugriff (S9b) zoomt nicht (Bild abgeschnitten).
    model._FlagAsMethod("ViewZoomtofit2")
    bilder = {}
    for name, ansicht in ANSICHTEN.items():
        model.ShowNamedView2("", ansicht)
        model.ViewZoomtofit2()
        pfad = ordner / f"{name}.png"
        sw.speichere(model, pfad, kopie=True)
        bilder[name] = str(pfad)
    return bilder
```

`swki/pruefung/befehle.py`:

```python
"""Befehle "swki pruefen", "swki status" und "swki bericht"."""

import json
import subprocess
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner, laeufe
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.konfig import PROJEKT, lade_rechner, lade_standard
from swki.pruefung.bericht import bericht_markdown
from swki.pruefung.bewertung import bewerte
from swki.pruefung.bilder import screenshots
from swki.pruefung.messen import kontext_aus_datei, messe, oeffne
from swki.pruefung.schleife import empfehlung, lies_laeufe, max_laeufe
from swki.spec.freigabe import pruefe_freigabe
from swki.spec.laden import lade_spec
from swki.verbindung import verbinde


def pruefen(spec_pfad: Path, lauf: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is None:
        bisher = laeufe(r, auftrag)
        if not bisher:
            raise SwkiFehler(f"Auftrag {auftrag} hat noch keinen Lauf. Zuerst: swki bauen")
        lauf = bisher[-1]
    ordner = lauf_ordner(r, auftrag, lauf)
    teil = ordner / f"{dateiname(spec, auftrag, standard)}.sldprt"
    if not teil.exists():
        raise SwkiFehler(f"{teil} fehlt (Lauf {lauf} ohne gespeichertes Teil)")
    app = verbinde(r.sw_jahr)
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    model = oeffne(app, teil)
    try:
        ctx = kontext_aus_datei(app, model, spec, spec_pfad, standard["toleranzen"]["anker_mm"], protokoll)
        messwerte = messe(ctx)
        bilder = screenshots(model, ordner / "bilder")
    finally:
        sw.schliesse(app, model)
    bericht = {
        "auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(teil),
        **bewerte(spec, messwerte, standard), "bilder": bilder,
    }
    text = json.dumps(bericht, indent=2, ensure_ascii=False) + "\n"
    (ordner / "pruefbericht.json").write_text(text, encoding="utf-8")
    ziel = lauf_datei(spec_pfad, lauf, "pruefbericht")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    return bericht


def status(spec_pfad: Path, anweisung: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    alle = lies_laeufe(spec_pfad)
    maximal = max_laeufe(spec, lade_standard(), anweisung)
    code, text = empfehlung(alle, maximal)
    return {"spec": spec_pfad.name, "laeufe": alle, "max_laeufe": maximal, "empfehlung": code, "text": text}


def _lies(pfad: Path) -> dict | None:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else None


def _compiler_aenderungen(seit: str) -> list[str]:
    ergebnis = subprocess.run(
        ["git", "log", f"--since={seit}", "--format=%h %s", "--", "swki/compiler", "schema"],
        cwd=PROJEKT, capture_output=True, text=True, encoding="utf-8",
    )
    return [z for z in ergebnis.stdout.splitlines() if z.strip()]


def bericht(spec_pfad: Path) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    stand = status(spec_pfad)
    alle = stand["laeufe"]
    letzter = alle[-1]["lauf"] if alle else None
    protokoll = _lies(lauf_datei(spec_pfad, letzter, "protokoll")) if letzter else None
    erstes = _lies(lauf_datei(spec_pfad, alle[0]["lauf"], "protokoll")) if alle else None
    text = bericht_markdown(
        spec, auftrag_name(spec_pfad), alle, (stand["empfehlung"], stand["text"]),
        _lies(lauf_datei(spec_pfad, letzter, "pruefbericht")) if letzter else None,
        _lies(lauf_datei(spec_pfad, letzter, "pruefer")) if letzter else None,
        protokoll,
        _compiler_aenderungen(erstes["gestartet"]) if erstes else [],
    )
    ziel = spec_pfad.parent / "bericht.md"
    ziel.write_text(text, encoding="utf-8")
    return {"bericht": str(ziel), "status": stand["empfehlung"]}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("pruefen", help="gespeicherten Lauf messen, bewerten, Screenshots (pruefbericht.json)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=int, help="Vorgabe: letzter Lauf")
    p.set_defaults(func=lambda a: pruefen(Path(a.spec), a.lauf))
    p = subparsers.add_parser("status", help="Stand der Nachbesserungsschleife und Empfehlung")
    p.add_argument("spec")
    p.add_argument("--max", type=int, help="maximale Nachbesserungen laut Anweisung im Chat")
    p.set_defaults(func=lambda a: status(Path(a.spec), a.max))
    p = subparsers.add_parser("bericht", help="bericht.md des Auftrags schreiben")
    p.add_argument("spec")
    p.set_defaults(func=lambda a: bericht(Path(a.spec)))
```

In `swki/cli.py` `_befehlsgruppen` ersetzen durch:

```python
def _befehlsgruppen() -> list:
    from swki import rechner
    from swki.api import bauen
    from swki.compiler import bauen as compiler_bauen
    from swki.pruefung import befehle as pruefung_befehle
    from swki.spec import befehle as spec_befehle

    return [rechner, bauen, spec_befehle, compiler_bauen, pruefung_befehle]
```

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle Unit-Tests grün.

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_pruefen.py`
Expected: 2× `OK` (bestanden mit Achsabstand 70, Material 1.2312, Empfehlungen pruefen → pruefer → bestanden, bericht.md; falsches Soll 71 → Mangel mit Knoten `f2`).

- [ ] **Step 5: Screenshots ansehen**

Die Live-Tests räumen ihren Arbeitsordner auf. Deshalb einmal per Hand einen Beispielauftrag anlegen (Ordner im Scratchpad mit der Spezifikation aus `test_live_pruefen.py`), `swki freigeben`, `swki bauen`, `swki pruefen` ausführen und die vier PNGs unter `<arbeitsordner>/<auftrag>/lauf-1/bilder/` mit dem Read-Tool öffnen: ganzes Teil sichtbar, keine Referenzachsen. Ergebnis im Task-Bericht festhalten, danach den Arbeitsordner dieses Auftrags löschen.

- [ ] **Step 6: Commit**

```powershell
git add swki/pruefung swki/cli.py tests/live
git commit -m "pruefung: swki pruefen, status, bericht" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 5: Prüfer-Agent

**Files:**
- Create: `.claude/agents/pruefer.md`

**Interfaces:**
- Produces: Agent `pruefer` (Tools `Read`, `Glob`), Antwort ausschließlich `{"bestanden": bool, "maengel": [{"knoten": [...], "beschreibung": "..."}]}` – genau das Format von `….pruefer.json` (Task 3).

- [ ] **Step 1: Agent anlegen**

`.claude/agents/pruefer.md`:

````markdown
---
name: pruefer
description: Unabhängiger Prüfer für gebaute SolidWorks-Teile. Bekommt Eingabe, freigegebene Spezifikation, Prüfbericht und Screenshots eines Laufs und urteilt "bestanden" oder liefert eine Mängelliste mit Knoten-IDs. Sieht keine Bauprotokolle und keine Skripte.
tools: Read, Glob
---

Du prüfst ein von SolidWorks-KI gebautes Teil unabhängig vom Konstrukteur. Du änderst nichts.

## Was du bekommst (Pfade in der Aufgabe)
- die Eingabe des Nutzers (Skizze, Beschreibung, Anweisungen) unter `auftraege/<auftrag>/eingabe/`
- die freigegebene Spezifikation (`*.yaml`) des Auftrags
- den Prüfbericht `protokolle/<spec>.lauf-<n>.pruefbericht.json`
- die Screenshots des Laufs (iso, vorne, oben, rechts – PNG, mit Read ansehen)

Lies **nicht** `protokolle/*.protokoll.json` und nichts unter `skripte/` – du beurteilst das Ergebnis, nicht den Bauweg.

## Checkliste
1. Jede Anforderung aus Eingabe und Spezifikation ist im Ergebnis belegt (Prüfbericht-Wert oder sichtbar im Screenshot).
2. Nichts ist ungebaut: jedes Feature der Spezifikation ist in den Bildern erkennbar (Bohrungen, Taschen, Fasen, Muster …).
3. Keine Spiegel- oder Vorzeichenfehler: Lage von Bohrungen, Taschen und Bund stimmt mit Eingabe und Spezifikation überein
   (Achsrichtungen: vorne → +Z, oben → +Y, rechts → +X); Schwerpunkt im Prüfbericht plausibel.
4. Alle Code-Prüfungen im Prüfbericht sind `ok: true` oder mit Hinweis begründet `ok: null`.
5. Plausibel: Proportionen, Wandstärken, keine offensichtlich unsinnigen Maße.

## Antwort (genau dieses JSON, sonst nichts)
```json
{"bestanden": true, "maengel": []}
```
oder
```json
{"bestanden": false, "maengel": [{"knoten": ["f3"], "beschreibung": "Tasche liegt auf der Unterseite statt oben (Bild oben)"}]}
```
`knoten` sind die Feature-IDs der Spezifikation (leer, wenn das ganze Teil betroffen ist). Beschreibe jeden Mangel so,
dass der Konstrukteur ihn ohne Rückfrage beheben kann, und nenne das Bild oder den Prüfbericht-Eintrag als Beleg.
````

- [ ] **Step 2: Trockentest**

In dieser Sitzung (Agent-Tool, `subagent_type: pruefer`, nach Neustart von Claude Code verfügbar; sonst general-purpose mit dem Inhalt der Datei als Anweisung) an einem Lauf aus Task 4 prüfen lassen: Eingabe (kurze Textbeschreibung der Prüfplatte), Spezifikation, Prüfbericht, Bilderordner. Erwartet: gültiges JSON, `bestanden: true`. Dann mit einer Spezifikation, deren Bohrungen gespiegelt sind (Positionen mit umgekehrtem Vorzeichen in u), prüfen: Erwartet ein Mangel mit Knoten `f2`. Beide Urteile im Task-Bericht dokumentieren.

- [ ] **Step 3: Commit**

```powershell
git add .claude/agents
git commit -m "pruefung: unabhängiger Prüfer-Agent" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 6: Skills `konstruieren` und `compiler-erweitern`, CLAUDE.md

**Files:**
- Create: `.claude/skills/konstruieren/SKILL.md`, `.claude/skills/compiler-erweitern/SKILL.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Spec §9: `konstruieren` = Eingabe → Spezifikation → validieren → Rückfragen → Freigabe → bauen → prüfen → nachbessern → Bericht; `compiler-erweitern` wird von Claude selbst ausgelöst (a) Lücke zum zweiten Mal mit bestandenem Skript, (b) fehlende Handler-Option, (c) wiederholter Handlerfehler – Test zuerst, Regressions-Suite, `pruefe-code`, eigener Commit, Eintrag im Bericht.

- [ ] **Step 1: Skills anlegen**

`.claude/skills/konstruieren/SKILL.md`:

```markdown
---
name: konstruieren
description: Konstruiert ein Einzelteil in SolidWorks aus Skizze, Beschreibung oder Anweisung – Spezifikation schreiben, validieren, Rückfragen, Freigabe durch den Nutzer, bauen, prüfen, unabhängiger Prüfer, nachbessern, Bericht. Verwenden, wenn der Nutzer ein Teil konstruiert, gebaut oder geändert haben will.
---

# Konstruieren (Einzelteil, Stufe 2)

Alle Befehle: `.venv\Scripts\python.exe -m swki …` (Ausgabe JSON, Exit 0 = ok). Längen in mm, Winkel in Grad.

## 1. Auftrag anlegen
- Ordner `auftraege/<auftrag>/` (Name wie vom Nutzer, sonst kurz und sprechend), Eingaben nach `eingabe/`.
- Ein Teil je Auftrag.

## 2. Spezifikation schreiben
- Datei `auftraege/<auftrag>/<name>.yaml` nach `schema/teil.schema.json`. Vorlagen: `tests/referenz/*/`.
- Maße, die zusammenhängen, als `parameter` und Ausdrücke (`"=L/2-20"`); sie werden SW-Gleichungen.
- Ebenen: `vorne` (Normale +Z), `oben` (+Y), `rechts` (+X). Skizzenkoordinaten (u, v): vorne X=u, Y=v · oben X=u, Z=−v ·
  rechts Z=−u, Y=v.
- Flächen/Kanten bevorzugt semantisch (`{feature, flaeche}`, `{feature, auswahl}`), sonst `{nahe: [x, y, z]}`.
- Schnitt geht standardmäßig gegen die Skizzennormale (von einer Deckfläche ins Material); `umkehren: true` dreht.
- Was das Schema nicht abbildet: `typ: skript` mit `luecke:` und Datei `skripte/<id>.py` (`def bauen(ctx)`), nie weglassen.
- `pruefung` immer füllen: `huellquader` [X, Y, Z], `volumen` (`auto` oder Wert), wichtige Maße unter `masse_pruefen`,
  `schwerpunkt` für Symmetrie/Spiegelfehler.

## 3. Validieren und Rückfragen
- `swki validieren <spec>` bis `"gueltig": true`.
- Unklarheiten in der Eingabe (fehlende Maße, Toleranzen, Material) gesammelt beim Nutzer erfragen, nicht raten.

## 4. Freigabe (einziger menschlicher Eingriff)
- Dem Nutzer die Anforderungen zeigen: Parameter, Material, Eigenschaften, Prüfwerte, Feature-Liste in Worten.
- Erst nach ausdrücklichem OK: `swki freigeben <spec>`.

## 5. Bauen, prüfen, Prüfer
- `swki bauen <spec>` → Lauf n (Protokoll unter `protokolle/`). Bei Bauabbruch: Fehlercode und Knoten lesen.
- `swki pruefen <spec> --lauf n` → Prüfbericht + Screenshots.
- Prüfer-Agent (`subagent_type: pruefer`) starten mit den Pfaden: Eingabeordner, Spezifikation, Prüfbericht,
  Screenshot-Ordner des Laufs. Keine Protokolle, keine Skripte übergeben.
- Sein JSON-Urteil unverändert nach `auftraege/<auftrag>/protokolle/<spec>.lauf-<n>.pruefer.json` schreiben.

## 6. Schleife
- `swki status <spec>` (optional `--max N`, wenn der Nutzer eine Zahl genannt hat) → `empfehlung`:
  - `nachbessern`: nur den Bauweg ändern (Anker, Reihenfolge, Handler-Optionen, Skripte). Anforderungen (Parameter,
    Material, Eigenschaften, Prüfwerte) sind tabu – `swki bauen` verweigert sonst (FREIGABE_VERALTET). Hält Claude eine
    Anforderung für falsch: Nutzer fragen. Dann neu bauen (Schritt 5).
  - `stopp_max` / `stopp_kein_fortschritt`: anhalten, Nutzer mit Bericht informieren.
  - `bestanden`: weiter mit 7.
- Wiederholt sich ein Compiler-Problem, Skill `compiler-erweitern` anwenden.

## 7. Bericht
- `swki bericht <spec>` → `auftraege/<auftrag>/bericht.md`; dem Nutzer Status, offene Punkte und Screenshots zeigen.
```

`.claude/skills/compiler-erweitern/SKILL.md`:

```markdown
---
name: compiler-erweitern
description: Erweitert den swki-Compiler um einen Handler oder eine Handler-Option. Von Claude selbst auszulösen, wenn (a) eine Lücke zum zweiten Mal auftritt und ein bestandenes Notausgang-Skript existiert, (b) einem Handler eine Option fehlt oder (c) ein Handler wiederholt am selben Fehler scheitert.
---

# Compiler erweitern

Neue Feature-Typen laufen beim ersten Mal immer über den Notausgang (`typ: skript`). Erst danach wird erweitert.

## Ablauf
1. **Anlass festhalten**: welcher Auftrag, welches Skript bzw. welcher Fehlercode, welcher Handler.
2. **API nachschlagen**: jeden neuen Aufruf mit `swki api methode <Interface.Member>` / `swki api enum <Name>`;
   Muster aus `swki/wissen/pywin32-fallstricke.md` beachten (Late Binding: nullargumentige Member ohne `()`,
   `callout_leer()`, `r8_array()`, `byref_*`).
3. **Test zuerst**:
   - Schema/Validierung: Unit-Test unter `tests/spec/`.
   - Handler: Live-Test mit Minimalteil unter `tests/live/` (Marker `sw`), Erwartung über Volumen/Hüllquader/Achsen.
   Test laufen lassen und scheitern sehen.
4. **Umsetzen**: Schema (`schema/teil.schema.json`) und Handler (`swki/compiler/handler/`) – kleinste Änderung.
5. **Absichern** (alles muss bestehen, sonst Änderung verwerfen: `git restore` der eigenen Dateien):
   - `.venv\Scripts\python.exe -m pytest`
   - `.venv\Scripts\python.exe -m pytest -m sw`
   - Regressions-Suite `.venv\Scripts\python.exe -m pytest -m sw tests/referenz`
   - `.venv\Scripts\python.exe -m swki api pruefe-code` (nur API-Aufrufe aus SW 2025)
6. **Commit**: eigener lokaler Commit je Änderung, Message `compiler: <was>` mit Trailer
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Kein Push ohne Rückfrage.
7. **Spezifikation umstellen**: den Notausgang im auslösenden Auftrag durch den neuen Typ ersetzen (Bauweg-Änderung,
   keine neue Freigabe nötig) und neu bauen. Der Bericht listet die Compiler-Änderung automatisch (`swki bericht`).
```

- [ ] **Step 2: `CLAUDE.md` ergänzen – nach dem Abschnitt `## Konstruieren (Stufe 2)` (aus Plan 2a) einfügen:**

```markdown
## Prüfen und Nachbessern (Stufe 2)
- Ablauf komplett im Skill `konstruieren`: `swki bauen` → `swki pruefen <spec>` → Prüfer-Agent `pruefer` (nur Eingabe,
  Spezifikation, Prüfbericht, Screenshots) → Urteil unverändert nach `protokolle/<spec>.lauf-<n>.pruefer.json` →
  `swki status <spec>` → nachbessern oder `swki bericht <spec>`.
- Wiederholt sich eine Lücke oder ein Handlerfehler: Skill `compiler-erweitern` (Test zuerst, Regressions-Suite).
- Regressions-Suite: `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz` (SolidWorks geöffnet).
```

- [ ] **Step 3: Prüfen**

Beide SKILL.md lesen und mit der Spec §9 abgleichen: jede Stufe des Ablaufs hat einen Befehl, jeder Befehl existiert (`swki validieren|freigeben|bauen|pruefen|status|bericht`, `swki api …`). Abweichungen im Task-Bericht nennen.

- [ ] **Step 4: Commit**

```powershell
git add .claude/skills CLAUDE.md
git commit -m "skills: konstruieren und compiler-erweitern" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 7: Referenzteil Buchse und Regressions-Suite

**Files:**
- Create: `tests/referenz/__init__.py` (leer), `tests/referenz/buchse/buchse.yaml`, `tests/referenz/test_referenzen.py`

**Interfaces:**
- Consumes: alle Befehle aus Plan 2a und Task 4.
- Buchse (Drehteil um Y): Rotation eines Halbschnitts mit Bund, Fase außen/innen, Nut als Rotationsschnitt, Befestigungsbohrung im Bund per Flächenanker `nahe` und 4er-Kreismuster; Werkstoff 1.7131 (16MnCr5). Sollvolumen analytisch 37425,1 mm³ (Rotationskörper 38679,29 − Fasen nach Pappus 49,22 + 7,98 − Nut 292,17 − 4 Bohrungen 904,78).
- Der Test kopiert den Auftrag nach `tmp_path` (keine Freigaben/Protokolle im Repo) und räumt den Arbeitsordner auf.

- [ ] **Step 1: Referenz anlegen**

`tests/referenz/buchse/buchse.yaml`:

```yaml
# Referenzteil Stufe 2: Führungsbuchse mit Bund (selbst definiert). Drehteil um die Modell-Y-Achse.
art: teil
name: Buchse
material: "1.7131"
eigenschaften: {Benennung: Führungsbuchse}
parameter: {D_innen: 20, D_schaft: 32, D_bund: 50, L: 60, L_bund: 8}
features:
  - id: f1            # Halbschnitt in Ebene vorne (u = Radius, v = axiale Lage)
    typ: rotation
    skizze:
      ebene: vorne
      elemente:
        - polygon:
            punkte:
              - ["=D_innen/2", 0]
              - ["=D_bund/2", 0]
              - ["=D_bund/2", "=L_bund"]
              - ["=D_schaft/2", "=L_bund"]
              - ["=D_schaft/2", "=L"]
              - ["=D_innen/2", "=L"]
        - mittellinie: {von: [0, -5], bis: [0, "=L+5"]}
  - id: f2            # Fase außen oben 1 × 45°
    typ: fase
    kanten: [{nahe: [0, "=L", "=D_schaft/2"]}]
    abstand: 1
  - id: f3            # Fase innen oben 0,5 × 45°
    typ: fase
    kanten: [{nahe: [0, "=L", "=D_innen/2"]}]
    abstand: 0.5
  - id: f4            # Nut 1 mm tief, 3 mm breit
    typ: rotation
    schnitt: true
    skizze:
      ebene: vorne
      elemente:
        - polygon: {punkte: [[15, 40], [17, 40], [17, 43], [15, 43]]}
        - mittellinie: {von: [0, -5], bis: [0, "=L+5"]}
  - id: f5            # Befestigungsbohrung im Bund
    typ: bohrung
    flaeche: {nahe: [20, "=L_bund", 0]}
    positionen: [[20, 0]]
    durchmesser: 6
    durch: true
  - id: f6
    typ: muster_kreis
    features: [f5]
    achse: y
    anzahl: 4
pruefung:
  huellquader: ["=D_bund", "=L", "=D_bund"]
  volumen:
    # analytisch: Rotationskörper − Fasen (Pappus) − Nut − 4 Bohrungen Ø6 × 8
    soll: 37425.1
    toleranz_prozent: 0.5
  masse_pruefen:
    - was: Lochkreis Bohrung 1 zur Achse
      von: {feature: f5, instanz: 1, achse: true}
      zu: {punkt: [0, 0, 0]}
      soll: 20
      tol: 0.01
    - was: Gesamtlänge
      von: {feature: f1, flaeche: "-y"}
      zu: {feature: f1, flaeche: "+y"}
      soll: "=L"
      tol: 0.01
  schwerpunkt: {soll: [0, null, 0], tol: 0.01}
```

- [ ] **Step 2: Regressionstest (vorerst nur Buchse)**

`tests/referenz/test_referenzen.py`:

```python
"""Regressions-Suite: Referenzteile freigeben, bauen, prüfen – müssen bestehen (SolidWorks muss laufen).

Die Aufträge werden in ein temporäres Verzeichnis kopiert, damit Freigaben und Protokolle nicht im Repo landen.
"""

import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
REFERENZEN = Path(__file__).parent


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.mark.parametrize(("ordner", "spec"), [("buchse", "buchse.yaml")])
def test_referenz_besteht(capsys, tmp_path, ordner, spec):
    auftrag = tmp_path / f"REF-{ordner}"
    shutil.copytree(REFERENZEN / ordner, auftrag)
    spec_pfad = auftrag / spec
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
        assert code == 0, bericht
        assert bericht["maengel"] == [], json.dumps(bericht["pruefungen"], indent=1, ensure_ascii=False)
        assert bericht["bestanden"] is True
        assert all(Path(p).stat().st_size > 0 for p in bericht["bilder"].values())
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / f"REF-{ordner}", ignore_errors=True)
```

- [ ] **Step 3: Validieren**

Run: `.venv\Scripts\python.exe -m swki validieren tests\referenz\buchse\buchse.yaml`
Expected: `"gueltig": true`, 6 Features.

- [ ] **Step 4: Live laufen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz\test_referenzen.py`
Expected: `OK` für `buchse` (Bau ok, alle Prüfungen ok, 4 Screenshots). Bei Mängeln: Prüfbericht lesen; nur den Bauweg ändern, nie die Prüfwerte an Messwerte anpassen – eine abweichende Prüfvorgabe mit Begründung im Task-Bericht melden.

- [ ] **Step 5: Commit**

```powershell
git add tests/referenz
git commit -m "referenz: Buchse und Regressions-Suite" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 8: Referenzteil Formplatte (mit Notausgang)

**Files:**
- Create: `tests/referenz/formplatte/formplatte_ds.yaml`, `tests/referenz/formplatte/skripte/f10_gewinde.py`
- Modify: `tests/referenz/test_referenzen.py` (Parameterliste um die Formplatte erweitern)

**Interfaces:**
- Formplatte DS 296 × 246 × 46 (Spec §4-Beispiel): 4 Führungsbohrungen Ø22 durch, Tasche 120 × 80 × 20, R5 außen, R6 Taschenecken, Fase 1 × 45° umlaufend über eine Kante, Senkbohrung M6 mit linearem Muster und Spiegeln, 2 × M8-Gewinde über den **Notausgang** (`typ: skript`, Bohrungsassistent, S9b Baustein 21; die Positionsskizze wird über `ctx.punkte_festlegen` voll bestimmt). Werkstoff 1.2312. Sollvolumen analytisch 3069574,5 mm³ (Rechnung im YAML-Kommentar). Maßprüfungen: Führungsbohrungen 250 und 200, Taschenboden 26 über Unterseite; Schwerpunkt X = Z = 0.

- [ ] **Step 1: Referenz und Skript anlegen**

`tests/referenz/formplatte/formplatte_ds.yaml`:

```yaml
# Referenzteil Stufe 2: Formplatte Düsenseite (selbst definiert, angelehnt an das Beispiel im Design §4)
# Platte 296 × 246 × 46 auf Ebene oben (wächst nach +Y), Mitte im Ursprung.
art: teil
name: Formplatte_DS
material: "1.2312"
eigenschaften: {Benennung: Formplatte DS}
parameter: {L: 296, B: 246, H: 46, T: 20}
features:
  - id: f1
    typ: extrusion
    skizze:
      ebene: oben
      elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]
    ende: {typ: blind, tiefe: "=H"}
  - id: f2            # Führungsbohrungen Ø22 durch, 23 mm vom Rand
    typ: bohrung
    flaeche: {feature: f1, flaeche: "+y"}
    positionen:
      - ["=-L/2+23", "=-B/2+23"]
      - ["=L/2-23", "=-B/2+23"]
      - ["=L/2-23", "=B/2-23"]
      - ["=-L/2+23", "=B/2-23"]
    durchmesser: 22
    durch: true
  - id: f3            # Tasche 120 × 80, Tiefe T
    typ: schnitt
    skizze:
      ebene: {feature: f1, flaeche: "+y"}
      elemente: [{rechteck: {mitte: [0, 0], breite: 120, hoehe: 80}}]
    ende: {typ: blind, tiefe: "=T"}
  - id: f4            # Außenecken R5
    typ: verrundung
    kanten: [{feature: f1, auswahl: senkrechte_kanten}]
    radius: 5
  - id: f5            # Taschenecken R6
    typ: verrundung
    kanten: [{feature: f3, auswahl: senkrechte_kanten}]
    radius: 6
  - id: f6            # Fase 1 × 45° umlaufend oben (eine Kante, setzt sich tangential fort)
    typ: fase
    kanten: [{nahe: ["=L/2", "=H", 0]}]
    abstand: 1
  - id: f7            # Durchgangsbohrung M6 mit Flachsenkung
    typ: bohrung
    flaeche: {feature: f1, flaeche: "+y"}
    positionen: [[-60, -110]]
    durchmesser: 6.6
    durch: true
    senkung: {durchmesser: 11, tiefe: 6.8}
  - id: f8
    typ: muster_linear
    features: [f7]
    richtung1: {achse: x, abstand: 40, anzahl: 4}
  - id: f9
    typ: spiegeln
    features: [f7, f8]
    ebene: vorne
  - id: f10
    typ: skript
    datei: skripte/f10_gewinde.py
    luecke: "Gewindebohrung M8 (Bohrungsassistent) – Gewinde kennt das Format noch nicht"
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen:
    # analytisch: Platte − 4 Führungsbohrungen − Tasche (mit R6-Ecken) − R5-Ecken − 8 Senkbohrungen
    #             − Fase (≈ 0,5 mm² × Umfang) − 2 × M8 (605,80 mm³ je Loch laut S9b)
    soll: 3069574.5
    toleranz_prozent: 0.5
  masse_pruefen:
    - was: Führungsbohrungen 1–2
      von: {feature: f2, instanz: 1, achse: true}
      zu: {feature: f2, instanz: 2, achse: true}
      soll: "=L-46"
      tol: 0.01
    - was: Führungsbohrungen 2–3
      von: {feature: f2, instanz: 2, achse: true}
      zu: {feature: f2, instanz: 3, achse: true}
      soll: "=B-46"
      tol: 0.01
    - was: Taschenboden über Unterseite
      von: {feature: f1, flaeche: "-y"}
      zu: {feature: f3, flaeche: "+y"}
      soll: "=H-T"
      tol: 0.01
  schwerpunkt: {soll: [0, null, 0], tol: 0.05}
```

`tests/referenz/formplatte/skripte/f10_gewinde.py`:

```python
"""Gewindebohrungen M8 über den Bohrungsassistenten.

Notausgang: Gewinde bildet das Spezifikationsformat in Stufe 2 noch nicht ab. Aufrufkette aus Spike S9b (Baustein 21).
"""

SW_WZD_TAP = 4  # swWzdGeneralHoleTypes_e
SW_STANDARD_ISO = 8  # swWzdHoleStandards_e
SW_ISO_TAPPED_HOLE = 147  # swWzdHoleStandardFastenerTypes_e
SW_SEL_FACES = 2  # swSelectType_e
POSITIONEN = [(-100, 0), (100, 0)]  # (u, v) auf der Deckfläche wie in der Spezifikation


def bauen(ctx):
    deckflaeche = ctx.ebene({"feature": "f1", "flaeche": "+y"})
    features = []
    for u, v in POSITIONEN:
        x, y, z = ctx.modellpunkt_m(deckflaeche, u, v)
        ctx.auswahl_leeren()
        ctx.model.Extension.SelectByRay(x, y + 0.01, z, 0.0, -1.0, 0.0, 0.0005, SW_SEL_FACES, False, 0, 0)
        features.append(ctx.model.FeatureManager.HoleWizard5(
            SW_WZD_TAP, SW_STANDARD_ISO, SW_ISO_TAPPED_HOLE, "M8", 0, -1, 0.016, -1,  # blind 16, Durchmesser -1 = Norm
            0.012, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1,  # Gewindetiefe 12, kosmetisches Gewinde
            "", False, False, True, False, True, False,
        ))
        ctx.punkte_festlegen(features[-1], {"feature": "f1", "flaeche": "+y"}, [(u, v)])  # Lage voll bestimmen
    return features
```

- [ ] **Step 2: Regressionstest erweitern – `tests/referenz/test_referenzen.py` vollständig:**

```python
"""Regressions-Suite: Referenzteile freigeben, bauen, prüfen – müssen bestehen (SolidWorks muss laufen).

Die Aufträge werden in ein temporäres Verzeichnis kopiert, damit Freigaben und Protokolle nicht im Repo landen.
"""

import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
REFERENZEN = Path(__file__).parent


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.mark.parametrize(("ordner", "spec"), [("buchse", "buchse.yaml"), ("formplatte", "formplatte_ds.yaml")])
def test_referenz_besteht(capsys, tmp_path, ordner, spec):
    auftrag = tmp_path / f"REF-{ordner}"
    shutil.copytree(REFERENZEN / ordner, auftrag)
    spec_pfad = auftrag / spec
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
        assert code == 0, bericht
        assert bericht["maengel"] == [], json.dumps(bericht["pruefungen"], indent=1, ensure_ascii=False)
        assert bericht["bestanden"] is True
        assert all(Path(p).stat().st_size > 0 for p in bericht["bilder"].values())
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / f"REF-{ordner}", ignore_errors=True)
```

- [ ] **Step 3: Validieren**

Run: `.venv\Scripts\python.exe -m swki validieren tests\referenz\formplatte\formplatte_ds.yaml`
Expected: `"gueltig": true`, 10 Features.

- [ ] **Step 4: Live laufen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz\test_referenzen.py`
Expected: 2× `OK` (Buchse und Formplatte bestehen alle Prüfungen).

- [ ] **Step 5: Sichtprüfung**

Formplatte einmal per Hand in einem Beispielauftrag bauen und prüfen, dann `bilder/iso.png` mit dem Read-Tool ansehen: Tasche mit gerundeten Ecken, 4 große Führungsbohrungen, 2 Reihen à 4 Senkbohrungen (Z = ±110), 2 kleine M8-Löcher (X = ±100), umlaufende Fase, keine Referenzachse. Danach den Prüfer-Agenten (Task 5) darüber urteilen lassen und das Urteil im Task-Bericht festhalten.

- [ ] **Step 6: Commit**

```powershell
git add tests/referenz
git commit -m "referenz: Formplatte DS mit Notausgang" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 9: Abschluss Stufe 2 (Rechner A und B)

**Files:**
- Create: `docs/stufe2/ergebnisse.md`

**Interfaces:**
- Spec §11: Stufe 2 ist fertig, wenn die Referenzen auf SW 2025 **und** SW 2026 bestehen.

- [ ] **Step 1: Gesamte Testsuite auf Rechner A**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: alle Unit-Tests grün.

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live tests\referenz`
Expected: alle `OK`.

Run: `.venv\Scripts\python.exe -m swki api pruefe-code`
Expected: keine Befunde.

- [ ] **Step 2: Ergebnisse festhalten – `docs/stufe2/ergebnisse.md` mit den tatsächlichen Werten aus den Prüfberichten füllen:**

```markdown
# Stufe 2 – Ergebnisse

| Referenz | SW 2025 (Rechner A) | SW 2026 (Rechner B) | Bemerkung |
|---|---|---|---|
| Buchse | … (Datum, Volumen ist/soll, Dauer) | … | |
| Formplatte DS | … | … | Notausgang f10 (M8-Gewinde) |

## Laufzeiten (Phasenzeiten aus dem Protokoll, Rechner A)
## Offene Punkte für Stufe 3
- …
```

- [ ] **Step 3: Commit**

```powershell
git add docs/stufe2
git commit -m "stufe2: Ergebnisse Rechner A" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Push und Rechner B (mit Nutzer)**

Den Nutzer fragen, ob gepusht werden soll (`git push origin main`). Danach auf Rechner B (SOLIDWORKS 2026): `git pull`, `powershell -ExecutionPolicy Bypass -File setup\einrichten.ps1`, SolidWorks 2026 öffnen, `.venv\Scripts\python.exe tests\live_einzeln.py tests\live tests\referenz`. Ergebnisse (auch Abweichungen) in `docs/stufe2/ergebnisse.md` eintragen und committen; Push wieder nur nach Rückfrage.

- [ ] **Step 5: Übergabe**

Dem Nutzer die Ergebnistabelle zeigen und vorschlagen, den Plan für Stufe 3 (Baugruppen, Normteile) zu schreiben.

---
