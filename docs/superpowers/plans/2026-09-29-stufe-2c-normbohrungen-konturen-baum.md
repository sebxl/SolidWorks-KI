# Stufe 2c: Normbohrungen, runde Konturen, Endbedingungen, kompakter Feature-Baum – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Werkzeugbau-Einzelteile ohne Notausgang bauen: neuer Feature-Typ `normbohrung` (Bohrungsassistent, ISO), Eckradien/Langlöcher/Konturen mit Bögen in Skizzen, Endbedingungen `bis_flaeche`/`versatz_von_flaeche`, Hinweise für einen kompakten Feature-Baum, Code-Prüfung der Normbohrungen und die neue Referenz *Auswerferhalteplatte*.

**Architecture:** Zuerst klärt Spike S10 (Task 1–2) live, wie SolidWorks 2025 Bohrungsassistent, Skizzenverrundung, Langloch, Bögen und die neuen Endbedingungen verlangt; daraus entsteht die Maßtabelle `swki/wissen/bohrungsnormen.yaml`. Danach folgen die reinen Teile ohne SolidWorks (Schema/Validierung, Sollvolumen, Hinweise; Task 3–5), die Compiler-Teile mit Live-Tests (Skizze, Endbedingungen, Handler `normbohrung`; Task 6–8), die Prüfung (Task 9), Skill/Doku (Task 10), die Referenz (Task 11) und der Abschluss (Task 12). Pure Hilfen liegen in `swki/spec/normen.py` und `swki/spec/konturen.py`, damit Validierung, Compiler und Prüfung dieselben Regeln nutzen.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A).

**Spec:** [docs/superpowers/specs/2026-09-29-stufe-2c-design.md](../specs/2026-09-29-stufe-2c-design.md) (bindend) – Kontext: [2026-09-26-solidworks-ki-design.md](../specs/2026-09-26-solidworks-ki-design.md) §4 Spezifikation, §5 Compiler, §6 Prüfung, §9 Skills, §12 Tests.

**Voraussetzung:** Stufe 2b ist auf `main` (PR #3): `swki validieren|freigeben|bauen|pruefen|status|bericht`, Freigabe-Kopie `<spec>.freigegeben.yaml`, Referenzen Buchse und Formplatte grün, 206 Unit-Tests grün.

**Herkunft des Codes:** Anders als in Plan 2b ist der Code dieses Plans **nicht** vorab live gelaufen. Unit-Test-Code und reine Funktionen sind vollständig und ohne SolidWorks prüfbar. Code, der von einem Spike-Befund abhängt, ist mit `# Abhängig von S10 Frage n` markiert; er ist der beste Stand aus API-Index und S9b. Die ausführende Sitzung passt genau diese Stellen an die Befunde aus Task 1–2 an, **rät nicht** und nennt jede Abweichung im Task-Bericht und in `docs/stufe0/ergebnisse.md`.

## Global Constraints

- **Late Binding** (siehe `swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()` (`model.FirstFeature`, `feature.GetDefinition`, `daten.GetSketchPointCount`); Ausnahmen `IBody2` (mit `()`), `EditSketch`; `ViewZoomtofit2`/`BlankRefGeom` nur nach `_FlagAsMethod` mit `()`. Objekt-Parameter mit `callout_leer()`, Zahlen-Arrays mit `r8_array()`, Objekt-Arrays als `VARIANT(VT_ARRAY|VT_DISPATCH)`, ByRef mit `byref_long|bool|str|variant()`.
- **Einheiten:** Spezifikation und Ausgaben an den Nutzer in mm und Grad; die API rechnet in m und rad (`mm()`, `in_mm()`, `in_mm3()`, `grad()` aus `swki.verbindung`).
- **Befehle** geben JSON aus, Exit 0 = ok, 1 = Fehler.
- **Nur eigene Dokumente** anfassen (selbst mit `NewDocument` angelegt bzw. eigener Lauf). Speichern nur im `arbeitsordner` aus `config/rechner.yaml`. Nie ein SolidWorks-Jahr oder einen Pfad fest in Code schreiben.
- **Benutzereinstellungen** nur vorübergehend über `sw.einstellung` / `sw.einstellung_int` (alter Wert wird immer wiederhergestellt). Toggle 10 (`swInputDimValOnCreate`) und Integer-Einstellung 6 (`swTiffScreenOrPrintCapture`) müssen nach jedem Live-Lauf denselben Wert haben wie vorher. Prüfen mit:
  `.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); print(app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6))"`
- **API nachschlagen:** Vor jedem neuen SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` bzw. `… api enum <Name>` (vorher `$env:PYTHONIOENCODING = "utf-8"`). Parameteranzahl und Enum-Werte aus dem Index sind verbindlich. Compiler-Code nur mit APIs aus SW 2025: `.venv\Scripts\python.exe -m swki api pruefe-code` ohne Befunde.
- **Live-Tests** immer einzeln mit Zeitlimit: `.venv\Scripts\python.exe tests\live_einzeln.py <datei|ordner> …`. Nur eine `SLDWORKS.exe` (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`), Speicher unter ca. 4 GB, sonst den Nutzer um einen Neustart von SolidWorks bitten.
- **Deutsche Oberfläche:** keine englischen Feature-/Ebenennamen; Features heißen wie ihre Spezifikations-ID, Standardebenen über ihre Position im Baum.
- **Sprache:** Code-Bezeichner, Docstrings, Kommentare, Commit-Messages und Berichte auf Deutsch.
- **Git:** eigener Branch (z. B. `stufe-2c`), kleine Commits je Task; Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **kein `git push` ohne Rückfrage**; erzeugte SolidWorks-Dateien nicht ins Git.
- **Prüfwerte nie an Messwerte anpassen.** Weicht ein Messwert ab: Bauweg prüfen; ist eine Prüfvorgabe falsch, mit Begründung im Task-Bericht melden.
- **Bestand bleibt:** Referenzen *Buchse* und *Formplatte* (`tests/referenz/buchse/`, `tests/referenz/formplatte/`) werden nicht geändert und müssen nach jedem Compiler-Task weiter bestehen. Handler `bohrung` und `SkriptKontext` (`swki/compiler/handler/bohrung.py`, `…/skript.py`) bleiben unverändert.
- **Subagents:** Implementer starten keine Subagents. Den Prüfer-Agenten (`subagent_type: pruefer`) startet nur der Controller (Task 11).

## Abhängigkeiten vom Spike S10

| Frage (Spec §7) | Befund, von dem Code abhängt | Betroffene Stellen |
|---|---|---|
| 1 HoleWizard5 je Art | Größen-Strings (`sw_groesse`), Belegung Value1…Value12 (Screw Fit, kosmetisches Gewinde, Gewinde-Ende), durch = EndType 1 mit Depth 0 | `bohrungsnormen.yaml`, `swki/spec/normen.py` (`SW_*`), `normbohrung.hole_werte` |
| 2 Mehrere Positionen | Positionsskizze erkennbar (Unterskizze ohne Segmente), öffnen per `Select2`+`InsertSketch`, weitere Punkte per `CreatePoint`, voll bestimmt, Gleichungen an Parameter | `skizze.positionsskizze`, `skizze.positionen_festlegen`, Handler `normbohrung` |
| 3 Maße je Größe | Maße, Tiefenbezug (ab Fläche), Bohrspitze 118° nur bei blind | `bohrungsnormen.yaml`, `geometrie.normbohrung_volumen`, `tests/referenz/auswerferhalteplatte/sollvolumen.py` |
| 4 Daten auslesen | `GetDefinition` → `Type`, `Standard2`, `FastenerType2`, `FastenerSize`, `EndCondition`, `Depth`, `ThreadDepth`, `GetSketchPointCount`; Text von `FastenerSize` | `messen.lies_normbohrung`, `bewertung.normbohrung_abweichungen`, Tabellenfeld `gelesen` |
| 5 Skizzen | `CreateFillet` (Linienpaar, Marke 0, Aktion 1, kein Auto-Maß), `CreateSketchSlot` Typ 1 (Segmente, Mittelpunkt, Mittellinie = Mittenabstand), Winkelmaß, `CreateArc`-Richtung, Punkte verschmelzen, Bogenende mit einem Maß | `skizze.py`: `verrunde`, `_langloch`, `_richtung_zu_u`, `_verschmelze`, `_kontur`, `lage(nur=…)` |
| 6 Endbedingungen | Zielfläche mit Marke 1, `OffsetReverse1 = False` = Versatz zur Skizze hin, Versatzmaß `D1` | `extrusion.py`: `MARKE_ZIELFLAECHE`, `VERSATZ_WEG_VON_SKIZZE`, `VERSATZ_MASS` |

**Entscheidungsregel (Spec §7):** Beantwortet der Spike eine Frage nicht mit „geht, und zwar so“ (kein Feature, falsches Volumen, Skizze nicht voll bestimmt, Daten nicht lesbar), hält der Implementer an und meldet den Befund mit JSON-Auszug an den Controller. Der Controller entscheidet **mit dem Nutzer** (Notausgang oder Umfang kürzen), bevor Task 3 ff. beginnen.

## Auslegungen der Spec (im Plan entschieden)

- §6.2 Regel 3: `muster_linear` wird gemeldet, wenn alle Abstände feste Zahlen sind, `muster_kreis` bei festem oder fehlendem Winkel (die Anzahl ist laut Schema immer eine Zahl); `spiegeln`, wenn alle gespiegelten Knoten Bohrungen/Normbohrungen sind (dann lassen sich die Positionen direkt angeben).
- §6.2 ISO-4762-Hinweis: Vergleich von Durchgangs- und Senkungsdurchmesser mit der Tabelle (±0,01 mm); die Senkungstiefe wird nicht verglichen.
- §4 Radiusregel wörtlich: Radius < halbe kürzere Nachbarkante (Rechteck: halbe kürzere Seite).
- §4 Langloch: `winkel` in [0, 180) (ein Langloch ist punktsymmetrisch); 0°/90° über Beziehungen, sonst Winkelmaß zu einer Hilfslinie.
- §5 `versatz_von_flaeche`: der Versatz geht immer zur Skizze hin (Restwandstärke); ein Versatz über die Zielfläche hinaus ist nicht vorgesehen.
- §3.3 `volumen_auto`: `normbohrung` mit `durch` ist wie `bohrung` mit `durch` nicht berechenbar (Materialdicke unbekannt) → Hinweis statt Mangel.
- §3.1 Parametrik: die Lage der Positionen hängt per Gleichung an Parametern, Bohr- und Gewindetiefe nicht (kein belegtes Maß am HoleWzd-Feature); die Prüfung `normbohrungen` vergleicht sie mit der Freigabe.
- §6.3 Kennzahl: erzeugte Features aus dem Bauprotokoll (`sw_name` je Knoten), nicht aus dem SolidWorks-Baum.
- §7 Spike: auf zwei Tasks verteilt (Bohrungsassistent; Skizzen und Endbedingungen), damit jeder Teil einzeln prüfbar ist.

## Dateistruktur nach diesem Plan

```
swki/wissen/bohrungsnormen.yaml       Maßtabelle Normbohrungen (ISO), live gemessen in S10
swki/spec/normen.py                   Tabelle laden, Größen, Zuordnung zum Bohrungsassistenten (Enum-Werte)
swki/spec/konturen.py                 Eckradien, Konturpunkte, Koordinate eines Bogenendpunkts (rein)
swki/spec/laden.py                    + Validierung normbohrung, Rundungen, Kontur, Langloch, Endbedingungen
swki/spec/hinweise.py                 hinweise(): art feste_zahl | zusammenfassen
swki/spec/befehle.py                  validieren gibt hinweise() aus
swki/compiler/skizze.py               + Eckradius, Langloch, Kontur, lage(nur), positionen_festlegen
swki/compiler/handler/extrusion.py    + bis_flaeche, versatz_von_flaeche
swki/compiler/handler/normbohrung.py  neuer Handler (HoleWizard5, alle Positionen in einem Feature)
swki/pruefung/geometrie.py            + Flächen mit Rundungen, Langloch, Kontur, normbohrung_volumen
swki/pruefung/bewertung.py            + Prüfung normbohrungen, baum_kennzahl
swki/pruefung/messen.py               + lies_normbohrung, normbohrungen, messe(ctx, freigegeben)
swki/pruefung/befehle.py, bericht.py  + "baum" im Prüfbericht, Abschnitt Feature-Baum in bericht.md
schema/teil.schema.json, config/standard.yaml (bohrungsnorm: ISO), pyproject.toml (wissen/*.yaml)
spikes/s10_*.py, docs/stufe0/ergebnisse/s10_*.json, docs/stufe0/ergebnisse.md
tests/spec/test_normen.py, tests/spec/test_konturen.py, tests/compiler/test_normbohrung.py
tests/live/test_live_konturen.py, test_live_endbedingungen.py, test_live_normbohrung.py,
tests/live/test_live_pruefen_normbohrung.py
tests/referenz/auswerferhalteplatte/ (auswerferhalteplatte.yaml, sollvolumen.py), tests/referenz/test_sollvolumen.py
.claude/skills/konstruieren/SKILL.md, CLAUDE.md, swki/wissen/pywin32-fallstricke.md
docs/stufe2c/ergebnisse.md
```

---

### Task 1: Spike S10 Teil A – Bohrungsassistent (Fragen 1–4) und Maßtabelle

**Files:**
- Create: `spikes/s10_gemeinsam.py`, `spikes/s10_f1_bohrungsassistent.py`, `spikes/s10_f2_positionen.py`, `spikes/s10_f3_normmasse.py`, `spikes/s10_f4_auslesen.py`
- Create (durch die Läufe): `docs/stufe0/ergebnisse/s10_f1_bohrungsassistent.json`, `…/s10_f2_positionen.json`, `…/s10_f3_normmasse.json`, `…/s10_f4_auslesen.json`
- Create: `swki/wissen/bohrungsnormen.yaml`
- Modify: `docs/stufe0/ergebnisse.md` (Zeile S10a in der Tabelle, Abschnitt „Stufe 2c: Spike S10“)

**Interfaces:**
- Consumes: `spikes._gemeinsam.lauf`, `ERGEBNISSE`; `spikes.s9a_gemeinsam.start|teil|kasten_oben|volumen_mm3|feature_masse|flaeche_mit_normale`; `spikes.s9b_gemeinsam.whatswrong`; Produktionscode `swki.compiler.skizze.Skizzierer|ebene_aus_flaeche`, `swki.compiler.topologie.flaeche_aus`, `swki.compiler.kontext.Kontext`, `swki.compiler.eigenschaften.globale_variablen`, `swki.compiler.sw`, `swki.pruefung.messen.oeffne`.
- Produces: JSON-Befunde zu Frage 1–4; `docs/stufe0/ergebnisse/s10_f1_bohrungsassistent.json` enthält `"gewinner": {art: {groesse: sw_text}}` (von f3/f4 gelesen); `swki/wissen/bohrungsnormen.yaml` im Format unten (Schlüssel `bohrspitze_grad`, `normen.ISO.<art>.<groesse>` mit `sw_groesse` und den Maßen `kernloch` | `durchgang`+`senkung_d`+`senkung_t` | `durchgang`+`senkung_d`+`senkwinkel` | `durchmesser`, optional `gelesen`, `abweichung`). Task 3 liest die Tabelle über `swki.spec.normen`.

- [ ] **Step 1: Voraussetzungen prüfen**

SOLIDWORKS 2025 frisch gestartet (unter 1 GB), genau eine Instanz, `git status` sauber, `.venv\Scripts\python.exe -m pytest` → 206 passed. Toggle 10 und Integer-Einstellung 6 mit dem Befehl aus den Global Constraints lesen und notieren.

- [ ] **Step 2: API-Werte bestätigen**

```powershell
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe -m swki api methode IFeatureManager.HoleWizard5
.venv\Scripts\python.exe -m swki api enum swWzdGeneralHoleTypes_e
.venv\Scripts\python.exe -m swki api enum swWzdHoleStandardFastenerTypes_e
.venv\Scripts\python.exe -m swki api enum swWzdHoleScrewClearanceTypes_e
.venv\Scripts\python.exe -m swki api enum swWzdHoleCosmeticThreadTypes_e
.venv\Scripts\python.exe -m swki api enum swWzdHoleThreadEndCondition_e
.venv\Scripts\python.exe -m swki api methode IModelDocExtension.SelectByRay
.venv\Scripts\python.exe -m swki api methode IFeature.GetDefinition
.venv\Scripts\python.exe -m swki api methode IWizardHoleFeatureData2.GetSketchPointCount
.venv\Scripts\python.exe -m swki api methode ISketchManager.CreatePoint
```

Expected (Stand beim Schreiben des Plans): HoleWizard5 27 Parameter (GenericHoleType, StandardIndex, FastenerTypeIndex, SSize, EndType, Diameter, Depth, Length, Value1…Value12, ThreadClass, RevDir, FeatureScope, AutoSelect, AssemblyFeatureScope, AutoSelectComponents, PropagateFeatureToParts); `swWzdCounterBore 0`, `swWzdCounterSink 1`, `swWzdHole 2`, `swWzdTap 4`; `swStandardISOSocketHeadCap 139`, `swStandardISOSocketCTSKFlatHead 140`, `swStandardISOTappedHole 147`, `swStandardISODowelHole 710`; `swScrewClearanceNormal 1`; `swCosmeticThreadWithoutCallout 2`; `swEndThreadTypeBLIND 0`, `swEndThreadTypeTHROUGH_ALL 1`; SelectByRay 11 Parameter; GetDefinition, GetSketchPointCount je 0 Parameter; CreatePoint 3 Parameter. Weicht etwas ab: Konstanten in Step 3 anpassen und im Bericht nennen.

- [ ] **Step 3: Gemeinsame Hilfen – `spikes/s10_gemeinsam.py`**

```python
"""Gemeinsame Hilfen für Spike S10 (Stufe 2c: Normbohrungen, runde Konturen, Endbedingungen). Kein Produktionscode.

Baut auf spikes/s9a_gemeinsam.py und spikes/s9b_gemeinsam.py auf (Late Binding erzwungen, eigenes Teil, Marken).
Enum-Werte laut `swki api enum` (2026-09-29); Belegung von Value1…Value12 laut API-Hilfe zu HoleWizard5 (Remarks).
"""

import math
from pathlib import Path

from swki.compiler.kontext import Kontext
from swki.konfig import lade_rechner

SW_STANDARD_ISO = 8  # swWzdHoleStandards_e.swStandardISO
SW_WZD = {"zylinderschraube": 0, "senkschraube": 1, "stift": 2, "gewinde": 4}  # swWzdGeneralHoleTypes_e
SW_BEFESTIGUNG = {  # swWzdHoleStandardFastenerTypes_e
    "zylinderschraube": 139,  # swStandardISOSocketHeadCap
    "senkschraube": 140,  # swStandardISOSocketCTSKFlatHead
    "stift": 710,  # swStandardISODowelHole
    "gewinde": 147,  # swStandardISOTappedHole
}
SW_END_BLIND, SW_END_DURCH_ALLES = 0, 1  # swEndConditions_e
SW_SCHRAUBE_NORMAL = 1  # swWzdHoleScrewClearanceTypes_e.swScrewClearanceNormal
SW_KOSMETISCH_OHNE_BESCHRIFTUNG = 2  # swWzdHoleCosmeticThreadTypes_e.swCosmeticThreadWithoutCallout
SW_GEWINDE_BLIND, SW_GEWINDE_DURCH = 0, 1  # swWzdHoleThreadEndCondition_e
SW_SEL_FACES = 2  # swSelectType_e.swSelFACES
DICKE_MM = 30.0  # Prüfblock 60 × 60 × 30 mm (Y 0…30), Bohrungen von der Deckfläche
ARBEIT_S10 = lade_rechner().arbeitsordner / "stufe0" / "s10"
_DATEN = (
    "Type", "Standard2", "FastenerType2", "FastenerSize", "EndCondition", "Depth", "HoleDepth", "HoleDiameter",
    "Diameter", "ThreadDepth", "ThreadDiameter", "ThreadEndCondition", "TapDrillDiameter", "TapDrillDepth",
    "CounterBoreDiameter", "CounterBoreDepth", "CounterSinkDiameter", "CounterSinkAngle", "NearCounterSinkDiameter",
    "ThruHoleDiameter", "ThruHoleDepth", "DrillAngle", "HoleFit", "CosmeticThreadType", "GetSketchPointCount",
)


def werte(art: str, gewindetiefe_m: float | None) -> list[float]:
    """Value1…Value12 von HoleWizard5 je Art (API-Hilfe, Remarks; −1 = Normwert/ungenutzt)."""
    v = [-1.0] * 12
    if art == "gewinde":
        v[0] = -1.0 if gewindetiefe_m is None else gewindetiefe_m  # Tap Thread Depth
        v[6] = SW_KOSMETISCH_OHNE_BESCHRIFTUNG  # Cosmetic Thread Type
        v[7] = SW_GEWINDE_DURCH if gewindetiefe_m is None else SW_GEWINDE_BLIND  # Thread End Condition
    elif art in ("zylinderschraube", "senkschraube"):
        v[3] = SW_SCHRAUBE_NORMAL  # Screw Fit
    return v


def bohrung(model, art, groesse, positionen_mm, tiefe_mm=None, gewindetiefe_mm=None, deckflaeche_y_mm=DICKE_MM):
    """Bohrungsassistent von der Deckfläche (Normale +Y) an den Positionen (x, z) in mm; jede Position per SelectByRay
    mit Marke 0 (API-Hilfe HoleWizard5: „SelectByRay with Mark = 0 for each location“). tiefe_mm None = durch alles."""
    model.ClearSelection2(True)
    y = (deckflaeche_y_mm + 1.0) / 1000
    treffer = [
        model.Extension.SelectByRay(x / 1000, y, z / 1000, 0.0, -1.0, 0.0, 0.0005, SW_SEL_FACES, i > 0, 0, 0)
        for i, (x, z) in enumerate(positionen_mm)
    ]
    f = model.FeatureManager.HoleWizard5(
        SW_WZD[art], SW_STANDARD_ISO, SW_BEFESTIGUNG[art], groesse,
        SW_END_DURCH_ALLES if tiefe_mm is None else SW_END_BLIND, -1,
        0.0 if tiefe_mm is None else tiefe_mm / 1000, -1,
        *werte(art, None if gewindetiefe_mm is None else gewindetiefe_mm / 1000),
        "", False, False, True, False, True, False,
    )
    model.ClearSelection2(True)
    return treffer, f


def unterfeatures(f) -> list[dict]:
    """Unterfeatures (Positions-/Profilskizze, kosmetisches Gewinde) mit Bestimmtheit, Punkt- und Segmentzahl."""
    out, s = [], f.GetFirstSubFeature
    while s is not None:
        eintrag = {"name": s.Name, "typ": s.GetTypeName2}
        if eintrag["typ"] == "ProfileFeature":
            sk = s.GetSpecificFeature2
            eintrag.update(status=sk.GetConstrainedStatus, punkte=len(sk.GetSketchPoints2 or ()),
                           segmente=len(sk.GetSketchSegments or ()))
        out.append(eintrag)
        s = s.GetNextSubFeature
    return out


def geometrie(f) -> dict:
    """Zylinder- und Kegelflächen des Features (mm): Radius, Achslage (x, z), Box [xmin, ymin, zmin, xmax, ymax, zmax]."""
    zylinder, kegel = [], []
    for fc in f.GetFaces or ():
        s = fc.GetSurface
        box = [round(c * 1000, 4) for c in fc.GetBox]
        if s.IsCylinder:
            c = s.CylinderParams
            zylinder.append({"r": round(c[6] * 1000, 4), "achse_xz": [round(c[0] * 1000, 4), round(c[2] * 1000, 4)],
                             "box": box})
        elif s.IsCone:
            kegel.append({"params": [round(x, 6) for x in s.ConeParams], "box": box})
    return {"zylinder": zylinder, "kegel": kegel}


def daten(f) -> dict:
    """IWizardHoleFeatureData2 über IFeature.GetDefinition (nullargumentig, ohne "()"); Längen roh in Metern."""
    d = f.GetDefinition
    out = {}
    for name in _DATEN:
        try:
            out[name] = getattr(d, name)
        except Exception as e:  # Spike: jeden Lesefehler festhalten
            out[name] = f"FEHLER {e!r}"
    return out


def kontext(app, model, parameter: dict | None = None) -> Kontext:
    """Baukontext für Produktionshilfen (Skizzierer, skizziere, verknuepfe) im Spike-Teil."""
    return Kontext(app, model, {"parameter": parameter or {}}, Path("s10.yaml"), 0.1)


def soll_volumen(art: str, m: dict, tiefe: float | None, dicke: float, spitze_grad: float = 118.0) -> float:
    """Erwartetes Volumen (mm³) einer Normbohrung – dieselbe Formel wie geometrie.normbohrung_volumen (Task 4):
    Tiefe = zylindrischer Teil ab der Fläche, darunter bei blind die Bohrspitze; Senkungen von der Fläche aus."""
    d = m.get("kernloch") or m.get("durchgang") or m["durchmesser"]
    v = math.pi * d**2 / 4 * (dicke if tiefe is None else tiefe)
    if tiefe is not None:
        v += math.pi * d**2 / 12 * (d / 2) / math.tan(math.radians(spitze_grad) / 2)
    if art == "zylinderschraube":
        v += math.pi * (m["senkung_d"] ** 2 - d**2) / 4 * m["senkung_t"]
    elif art == "senkschraube":
        ds = m["senkung_d"]
        h = (ds - d) / 2 / math.tan(math.radians(m["senkwinkel"]) / 2)
        v += math.pi * h / 12 * (ds**2 + ds * d + d**2) - math.pi * d**2 / 4 * h
    return v
```

- [ ] **Step 4: Frage 1 – `spikes/s10_f1_bohrungsassistent.py` schreiben und laufen lassen**

```python
"""S10 Frage 1: HoleWizard5 für die vier Arten (ISO) – Größen-Strings, Endbedingung durch/blind, Gewindetiefe.

Prüfblock 60 × 60 × 30 (Y 0…30), Bohrung von der Deckfläche bei (X 0, Z 0), je Fall ein neues Teil.
a) Größen-Strings: je Größe werden Schreibweisen probiert (durch alles); die erste mit fehlerfreiem Feature und
   Volumenabnahme ist der „gewinner“ (Frage 2–4 und bohrungsnormen.yaml verwenden ihn).
b) Endbedingungen: blind/durch je Art, Gewinde blind mit Gewindetiefe, durch mit durchgehendem bzw. begrenztem Gewinde.
Soll Gewinde M8 blind 16 (S9b Baustein 21): 605,80 mm³.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import feature_masse, kasten_oben, start, teil, volumen_mm3
from spikes.s9b_gemeinsam import whatswrong
from spikes.s10_gemeinsam import DICKE_MM, bohrung, daten, geometrie, unterfeatures

SCHREIBWEISEN = {
    "gewinde": {
        **{f"M{d}": [f"M{d}"] for d in (5, 6, 8, 10, 12, 16)},
        **{f"M{d}x{p:g}": [f"M{d}x{p:g}", f"M{d}x{p:.1f}", f"M{d} x {p:.1f}", f"M{d}x{p:.2f}"]
           for d, p in ((8, 1), (10, 1), (12, 1.5), (16, 1.5))},
    },
    "zylinderschraube": {f"M{d}": [f"M{d}"] for d in (5, 6, 8, 10, 12)},
    "senkschraube": {f"M{d}": [f"M{d}"] for d in (5, 6, 8, 10)},
    "stift": {f"{d}": [f"{d}", f"D{d}", f"Ø{d}", f"Ø{d}.0", f"{d}.0", f"{d} mm"] for d in (4, 5, 6, 8, 10, 12)},
}


def fall(app, r, art, groesse, **kw) -> dict:
    with teil(app, r) as model:
        kasten_oben(model, 60, 60, DICKE_MM)
        v0 = volumen_mm3(model)
        try:
            treffer, f = bohrung(model, art, groesse, [(0.0, 0.0)], **kw)
        except Exception as e:  # Spike: alles protokollieren
            return {"fehler": repr(e)}
        out = {"selectbyray": treffer, "feature": f.Name if f else None, "typ": f.GetTypeName2 if f else None,
               "abnahme_mm3": round(v0 - volumen_mm3(model), 3), "whatswrong": whatswrong(model)}
        if f:
            out.update(unterfeatures=unterfeatures(f), geometrie=geometrie(f), masse=feature_masse(f), daten=daten(f))
        return out


def gelungen(e: dict) -> bool:
    return bool(e.get("feature")) and e.get("abnahme_mm3", 0) > 0 and e.get("whatswrong", {}).get("anzahl", 1) == 0


def pruefen() -> dict:
    r, app = start()
    d: dict = {"gewinner": {}, "groessen": {}, "enden": {}}
    for art, groessen in SCHREIBWEISEN.items():
        for groesse, kandidaten in groessen.items():
            versuche = {}
            for text in kandidaten:
                versuche[text] = fall(app, r, art, text)
                if gelungen(versuche[text]):
                    d["gewinner"].setdefault(art, {})[groesse] = text
                    break
            d["groessen"][f"{art} {groesse}"] = versuche
    faelle = {
        "gewinde M8 blind 16, Gewinde 12 (Soll 605,80)": ("gewinde", "M8", {"tiefe_mm": 16, "gewindetiefe_mm": 12}),
        "gewinde M8 durch, Gewinde durch": ("gewinde", "M8", {}),
        "gewinde M8 durch, Gewinde 12": ("gewinde", "M8", {"gewindetiefe_mm": 12}),
        "zylinderschraube M8 blind 20": ("zylinderschraube", "M8", {"tiefe_mm": 20}),
        "zylinderschraube M8 durch": ("zylinderschraube", "M8", {}),
        "senkschraube M6 blind 20": ("senkschraube", "M6", {"tiefe_mm": 20}),
        "senkschraube M6 durch": ("senkschraube", "M6", {}),
    }
    stift8 = d["gewinner"].get("stift", {}).get("8")
    if stift8:
        faelle |= {"stift 8 blind 20": ("stift", stift8, {"tiefe_mm": 20}), "stift 8 durch": ("stift", stift8, {})}
    for name, (art, groesse, kw) in faelle.items():
        d["enden"][name] = fall(app, r, art, groesse, **kw)
        d["enden"][name]["gelungen"] = gelungen(d["enden"][name])
    return d


if __name__ == "__main__":
    lauf("s10_f1_bohrungsassistent", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s10_f1_bohrungsassistent` (Laufzeit einige Minuten, ca. 60 Teile)
Expected: `"ok": true`; `gewinner` enthält alle 10 Gewinde-, 5 Zylinderschrauben-, 4 Senkschrauben- und 6 Stiftgrößen; alle `enden.*.gelungen` = true; `gewinde M8 blind 16 …` → `abnahme_mm3` 605.8; bei Gewinde ein Unterfeature `CosmeticThread`. Die Maße unter `masse` (Maßnamen des HoleWzd-Features) im Bericht nennen.

- [ ] **Step 5: Frage 2 – `spikes/s10_f2_positionen.py` schreiben und laufen lassen**

```python
"""S10 Frage 2: mehrere Positionen in einem Bohrungsassistent-Feature, Positionsskizze voll bestimmt.

Block 100 × 60 × 30 (Y 0…30), Gewinde M8 blind 16 / Gewinde 12 an (u, v) = (−30, 10), (0, 10), (30, 10) auf der
Deckfläche (Modell X = u, Z = −v). Soll je Loch 605,80 mm³ (S9b).
A) alle Positionen per SelectByRay (Marke 0, angehängt) vor HoleWizard5.
B) eine Position per SelectByRay, danach die Positionsskizze öffnen (Select2 + InsertSketch, wie S9b), die übrigen
   Punkte mit CreatePoint anlegen (AddToDB) und alle Punkte mit dem Skizzierer des Compilers zum Ursprung bemaßen;
   Maße per Gleichung an L binden, dann L = 120 → äußere Achsen bei X = ±40.
Je Variante: Positionsskizze erkennbar (Unterskizze ohne Segmente?), Punktzahl (GetSketchPointCount), Bestimmtheit,
Volumenabnahme, Achslagen.
"""

import pythoncom

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import flaeche_mit_normale, kasten_oben, start, teil, volumen_mm3
from spikes.s9b_gemeinsam import whatswrong
from spikes.s10_gemeinsam import DICKE_MM, bohrung, geometrie, kontext, unterfeatures
from swki.compiler import sw
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.skizze import Skizzierer, ebene_aus_flaeche
from swki.compiler.topologie import flaeche_aus

POSITIONEN = [["=-L/2+20", 10], [0, 10], ["=L/2-20", 10]]
SOLL_JE_LOCH = 605.80


def _achsen(f) -> list:
    return sorted({tuple(z["achse_xz"]) for z in geometrie(f)["zylinder"]})


def variante_a(app, r) -> dict:
    with teil(app, r) as model:
        kasten_oben(model, 100, 60, DICKE_MM)
        v0 = volumen_mm3(model)
        treffer, f = bohrung(model, "gewinde", "M8", [(-30.0, -10.0), (0.0, -10.0), (30.0, -10.0)],
                             tiefe_mm=16, gewindetiefe_mm=12)
        if f is None:
            return {"selectbyray": treffer, "feature": None, "whatswrong": whatswrong(model)}
        return {"selectbyray": treffer, "feature": f.Name, "punkte": f.GetDefinition.GetSketchPointCount,
                "abnahme_mm3": round(v0 - volumen_mm3(model), 3), "soll_mm3": round(3 * SOLL_JE_LOCH, 2),
                "achsen_xz": _achsen(f), "unterfeatures": unterfeatures(f), "whatswrong": whatswrong(model)}


def _positionsskizze(f):
    s = f.GetFirstSubFeature
    while s is not None:
        if s.GetTypeName2 == "ProfileFeature" and not (s.GetSpecificFeature2.GetSketchSegments or ()):
            return s
        s = s.GetNextSubFeature
    return None


def variante_b(app, r) -> dict:
    with teil(app, r) as model:
        kasten = kasten_oben(model, 100, 60, DICKE_MM)
        globale_variablen(model, {"L": 100})
        ctx = kontext(app, model, {"L": 100})
        v0 = volumen_mm3(model)
        _, f = bohrung(model, "gewinde", "M8", [(-30.0, -10.0)], tiefe_mm=16, gewindetiefe_mm=12)
        d: dict = {"unterfeatures_vorher": unterfeatures(f)}
        skizze = _positionsskizze(f)
        if skizze is None:
            return {**d, "fehler": "keine Unterskizze ohne Segmente"}
        se = ebene_aus_flaeche(flaeche_aus(flaeche_mit_normale(kasten, (0.0, 1.0, 0.0))))
        sm = model.SketchManager
        model.ClearSelection2(True)
        skizze.Select2(False, 0)
        sm.InsertSketch(True)  # öffnet die selektierte Skizze (S9b)
        masse = []
        try:
            sk = Skizzierer(ctx, se, sm.ActiveSketch)
            with sw.einstellung(app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
                d["createpoint"] = []
                for u, v in POSITIONEN[1:]:
                    x, y = sk.zu_skizze(ctx.wert(u), ctx.wert(v))
                    d["createpoint"].append(sm.CreatePoint(x, y, 0.0) is not None)
                for p in POSITIONEN:
                    sk.lage(p, (ctx.wert(p[0]) + 8, ctx.wert(p[1]) + 8))
            d["status_offen"] = sm.ActiveSketch.GetConstrainedStatus
            masse = sk.masse
        except Exception as e:  # Spike: alles protokollieren
            d["fehler"] = repr(e)
        finally:
            sm.InsertSketch(True)
        skizze.Name = "f2_positionen"
        for m in masse:
            ctx.verknuepfe(f"{m.name}@f2_positionen", m.roh, m.vorzeichen)
        d["rebuild"] = model.EditRebuild3
        d["status"] = skizze.GetSpecificFeature2.GetConstrainedStatus
        d["punkte"] = f.GetDefinition.GetSketchPointCount
        d["abnahme_mm3"] = round(v0 - volumen_mm3(model), 3)
        d["soll_mm3"] = round(3 * SOLL_JE_LOCH, 2)
        d["achsen_xz"] = _achsen(f)
        d["masse"] = [f"{m.name}@f2_positionen = {m.roh}" for m in masse]
        g = model.GetEquationMgr
        texte = [g.Equation(i) for i in range(g.GetCount)]
        d["gleichungen"] = texte
        dispid = g._oleobj_.GetIDsOfNames("Equation")
        g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, texte.index('"L" = 100'), '"L" = 120')
        g.EvaluateAll
        d["rebuild_l120"] = model.EditRebuild3
        d["achsen_xz_l120"] = _achsen(f)  # Soll: (−40, −10), (0, −10), (40, −10)
        d["whatswrong"] = whatswrong(model)
        d["unterfeatures_nachher"] = unterfeatures(f)
        return d


def pruefen() -> dict:
    r, app = start()
    return {"a_selectbyray_mehrfach": variante_a(app, r), "b_positionsskizze": variante_b(app, r)}


if __name__ == "__main__":
    lauf("s10_f2_positionen", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s10_f2_positionen`
Expected (Weg des Plans = Variante B): `b_positionsskizze.status` = 3 (voll bestimmt), `punkte` = 3, `abnahme_mm3` ≈ 1817.40, `achsen_xz` = [[-30,-10],[0,-10],[30,-10]], `achsen_xz_l120` = [[-40,-10],[0,-10],[40,-10]], Gleichungen mit `@f2_positionen` und `"L"`. Variante A nur festhalten (liefert sie 3 Punkte, ist das ein alternativer Weg; der Plan bleibt bei B, weil die Positionsskizze ohnehin voll bestimmt werden muss). Scheitert B: Entscheidungsregel.

- [ ] **Step 6: Frage 3 – `spikes/s10_f3_normmasse.py` schreiben und laufen lassen**

```python
"""S10 Frage 3: Maße, die der Bohrungsassistent je Größe erzeugt → swki/wissen/bohrungsnormen.yaml.

Für jede Größe mit Schreibweise aus Frage 1 (gewinner in docs/stufe0/ergebnisse/s10_f1_bohrungsassistent.json) im
Prüfblock 60 × 60 × 30: durch alles und blind 20 (Gewinde: Gewindetiefe 12). Gemessen: Zylinder-Radien, Kegel,
Box der Flächen, Volumenabnahme; gelesen: IWizardHoleFeatureData2. Daraus je Größe ein Tabellenvorschlag und der
Abgleich mit der Formel soll_volumen (Tiefe ab Fläche, Bohrspitze 118° nur bei blind):
- gewinde: kernloch = 2·r (Zylinder)
- zylinderschraube: durchgang = 2·r_min, senkung_d = 2·r_max, senkung_t = Deckfläche − Unterkante des großen Zylinders
- senkschraube: durchgang = 2·r_min, senkung_d = X-Ausdehnung der Kegelfläche, senkwinkel aus der Kegelhöhe
- stift: durchmesser = 2·r
"""

import json
import math

from spikes._gemeinsam import ERGEBNISSE, lauf
from spikes.s9a_gemeinsam import kasten_oben, start, teil, volumen_mm3
from spikes.s10_gemeinsam import DICKE_MM, bohrung, daten, geometrie, soll_volumen

TIEFE_MM, GEWINDETIEFE_MM = 20.0, 12.0


def _messen(app, r, art, text, blind: bool) -> dict:
    with teil(app, r) as model:
        kasten_oben(model, 60, 60, DICKE_MM)
        v0 = volumen_mm3(model)
        kw = {"tiefe_mm": TIEFE_MM, "gewindetiefe_mm": GEWINDETIEFE_MM if art == "gewinde" else None} if blind else {}
        _, f = bohrung(model, art, text, [(0.0, 0.0)], **kw)
        if f is None:
            return {"fehler": "kein Feature"}
        return {"abnahme_mm3": round(v0 - volumen_mm3(model), 4), "geometrie": geometrie(f), "daten": daten(f)}


def vorschlag(art: str, text: str, durch: dict) -> dict:
    zylinder = durch["geometrie"]["zylinder"]
    r_min, r_max = min(z["r"] for z in zylinder), max(z["r"] for z in zylinder)
    m: dict = {"sw_groesse": text}
    if art == "gewinde":
        m["kernloch"] = round(2 * r_min, 4)
    elif art == "stift":
        m["durchmesser"] = round(2 * r_min, 4)
    elif art == "zylinderschraube":
        gross = next(z for z in zylinder if z["r"] == r_max)
        m |= {"durchgang": round(2 * r_min, 4), "senkung_d": round(2 * r_max, 4),
              "senkung_t": round(DICKE_MM - gross["box"][1], 4)}
    else:
        box = durch["geometrie"]["kegel"][0]["box"]
        ds, h = box[3] - box[0], DICKE_MM - box[1]
        m |= {"durchgang": round(2 * r_min, 4), "senkung_d": round(ds, 4),
              "senkwinkel": round(2 * math.degrees(math.atan((ds / 2 - r_min) / h)), 4)}
    gelesen = durch["daten"].get("FastenerSize")
    if isinstance(gelesen, str) and gelesen != text:
        m["gelesen"] = gelesen
    return m


def pruefen() -> dict:
    r, app = start()
    gewinner = json.loads((ERGEBNISSE / "s10_f1_bohrungsassistent.json").read_text(encoding="utf-8"))["gewinner"]
    d: dict = {"messungen": {}, "tabelle": {}, "abgleich": {}}
    for art, groessen in gewinner.items():
        for groesse, text in groessen.items():
            durch, blind = _messen(app, r, art, text, False), _messen(app, r, art, text, True)
            d["messungen"][f"{art} {groesse}"] = {"durch": durch, "blind": blind}
            if "fehler" in durch or "fehler" in blind:
                continue
            m = vorschlag(art, text, durch)
            d["tabelle"].setdefault(art, {})[groesse] = m
            soll_durch = soll_volumen(art, m, None, DICKE_MM)
            soll_blind = soll_volumen(art, m, TIEFE_MM, DICKE_MM)
            d["abgleich"][f"{art} {groesse}"] = {
                "durch_ist": durch["abnahme_mm3"], "durch_soll": round(soll_durch, 4),
                "blind_ist": blind["abnahme_mm3"], "blind_soll": round(soll_blind, 4),
                "passt": abs(durch["abnahme_mm3"] - soll_durch) <= 1e-3 * soll_durch
                and abs(blind["abnahme_mm3"] - soll_blind) <= 1e-3 * soll_blind,
            }
    return d


if __name__ == "__main__":
    lauf("s10_f3_normmasse", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s10_f3_normmasse`
Expected: `tabelle` enthält jede Größe aus `gewinner`; `abgleich.*.passt` = true überall (M8-Gewinde: `kernloch` 6.8). Passt `blind` bei Senkungen nicht, liegt die Bohrungstiefe anders als „ab Fläche“: den Bezug aus `daten` (`Depth`, `HoleDepth`, `ThruHoleDepth`) und den Zylinder-Boxen ableiten, `soll_volumen` in `spikes/s10_gemeinsam.py` entsprechend korrigieren, erneut laufen lassen und die Korrektur als Vorgabe für `geometrie.normbohrung_volumen` (Task 4) und `sollvolumen.py` (Task 11) im Bericht festhalten (Abhängig von S10 Frage 3).

- [ ] **Step 7: Frage 4 – `spikes/s10_f4_auslesen.py` schreiben und laufen lassen**

```python
"""S10 Frage 4: Bohrungsassistent-Daten eines Features auslesen (für die Code-Prüfung normbohrungen).

Ein Teil mit vier Normbohrungs-Features (eine je Art, Namen nb_<art>), gespeichert im Arbeitsordner, geschlossen und
mit OpenDoc6 wieder geöffnet (wie swki pruefen). Je Feature: IFeature.GetDefinition → IWizardHoleFeatureData2 –
Type, Standard2, FastenerType2, FastenerSize, EndCondition, Depth/HoleDepth, ThreadDepth, GetSketchPointCount –
einmal im gebauten und einmal im wieder geöffneten Teil; "soll" nennt die Eingaben.
"""

import json

from spikes._gemeinsam import ERGEBNISSE, lauf
from spikes.s9a_gemeinsam import kasten_oben, start
from spikes.s10_gemeinsam import ARBEIT_S10, DICKE_MM, SW_BEFESTIGUNG, SW_WZD, bohrung, daten
from swki.compiler import sw
from swki.pruefung.messen import oeffne


def pruefen() -> dict:
    r, app = start()
    gewinner = json.loads((ERGEBNISSE / "s10_f1_bohrungsassistent.json").read_text(encoding="utf-8"))["gewinner"]
    eingaben = {
        "nb_gewinde": ("gewinde", gewinner["gewinde"]["M10"], [(-15.0, -15.0), (15.0, -15.0)],
                       {"tiefe_mm": 16, "gewindetiefe_mm": 12}),
        "nb_zylinderschraube": ("zylinderschraube", gewinner["zylinderschraube"]["M8"], [(-15.0, 15.0)], {}),
        "nb_senkschraube": ("senkschraube", gewinner["senkschraube"]["M6"], [(15.0, 15.0)], {}),
        "nb_stift": ("stift", gewinner["stift"]["8"], [(0.0, 0.0)], {"tiefe_mm": 20}),
    }
    pfad = ARBEIT_S10 / "s10_f4_auslesen.sldprt"
    d: dict = {"gebaut": {}, "geoeffnet": {}}
    d["soll"] = {
        name: {"Type": SW_WZD[art], "Standard2": 8, "FastenerType2": SW_BEFESTIGUNG[art], "FastenerSize": text,
               "EndCondition": 0 if "tiefe_mm" in kw else 1, "Depth_m": kw.get("tiefe_mm", 0) / 1000,
               "ThreadDepth_m": kw.get("gewindetiefe_mm", 0) / 1000, "GetSketchPointCount": len(pos)}
        for name, (art, text, pos, kw) in eingaben.items()
    }
    model = app.NewDocument(str(r.vorlage_teil), 0, 0, 0)
    try:
        kasten_oben(model, 60, 60, DICKE_MM)
        for name, (art, text, pos, kw) in eingaben.items():
            _, f = bohrung(model, art, text, pos, **kw)
            f.Name = name
            d["gebaut"][name] = daten(f)
        sw.speichere(model, pfad)
    finally:
        sw.schliesse(app, model)
    model = oeffne(app, pfad)
    try:
        for name in eingaben:
            f = model.FeatureByName(name)
            d["geoeffnet"][name] = {"typname": f.GetTypeName2, **daten(f)} if f is not None else "fehlt"
    finally:
        sw.schliesse(app, model)
    return d


if __name__ == "__main__":
    lauf("s10_f4_auslesen", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s10_f4_auslesen`
Expected: für alle vier Features in `geoeffnet`: `typname` = `HoleWzd`, `Type`/`Standard2`/`FastenerType2`/`EndCondition` = `soll`, `Depth` = `soll.Depth_m` bei blind, `ThreadDepth` = 0.012 bei `nb_gewinde`, `GetSketchPointCount` = Anzahl der Positionen (bei `nb_gewinde` 2, sofern Variante A in Frage 2 mehrere Punkte liefert; sonst 1 – dann im Bericht vermerken). Liefert `FastenerSize` einen anderen Text als die Eingabe (z. B. „M8x1.25“ für „M8“), kommt dieser Text als `gelesen` in die Tabelle (Step 8). Liest `Depth` 0 bei blind, aber `HoleDepth` den Wert: in Task 9 `HoleDepth` verwenden (Abhängig von S10 Frage 4).

- [ ] **Step 8: Maßtabelle `swki/wissen/bohrungsnormen.yaml` anlegen**

Grundgerüst mit den ISO-Werten, die vor dem Spike bekannt sind. **Jeden Wert** (`sw_groesse` und Maße) durch den Wert aus `s10_f3_normmasse.json` → `tabelle` ersetzen (auf 4 Nachkommastellen, Nullen weglassen). Weicht ein gemessener Wert vom ISO-Wert unten ab, bleibt der SolidWorks-Wert, und die Zeile bekommt `abweichung: "ISO <iso-wert>, SolidWorks <gemessen>"`. Liefert `tabelle` ein `gelesen`, übernehmen. Größen ohne Messung (kein `gewinner` oder `passt` false) **entfernen** (Spec §3.3: nur live geprüfte Größen). Die Referenz (Task 11) braucht: zylinderschraube M8, stift 8, gewinde M10 und M12x1.5, senkschraube M6 – fehlt eine davon: Entscheidungsregel.

```yaml
# Maßtabelle der Normbohrungen: Maße, die der SOLIDWORKS-Bohrungsassistent (HoleWizard5) je Norm, Art und Größe
# erzeugt. Erste Fassung aus Spike S10 (docs/stufe0/ergebnisse/s10_f3_normmasse.json, SOLIDWORKS 2025).
# Nur live geprüfte Größen aufnehmen (Spec 2c §3.3). Weicht SolidWorks von der ISO-Norm ab, gilt der SolidWorks-Wert;
# die Abweichung steht dann unter "abweichung".
# Längen in mm, Winkel in Grad. Bohrungstiefe = zylindrischer Teil ab der Ansatzfläche; bei blind darunter die
# Bohrspitze (bohrspitze_grad). Gewinde sind kosmetisch (kein Volumen), gebohrt wird das Kernloch.
# sw_groesse: Text für HoleWizard5 (SSize); gelesen: Text aus IWizardHoleFeatureData2.FastenerSize, falls anders.
# Größen-Schlüssel als Text schreiben (Stift: "8").
bohrspitze_grad: 118
normen:
  ISO:
    gewinde:                 # ISO-Gewindebohrung (swStandardISOTappedHole), Kernloch nach ISO 2306
      M5:      {sw_groesse: "M5",      kernloch: 4.2}
      M6:      {sw_groesse: "M6",      kernloch: 5.0}
      M8:      {sw_groesse: "M8",      kernloch: 6.8}      # bestätigt in S9b Baustein 21
      M10:     {sw_groesse: "M10",     kernloch: 8.5}
      M12:     {sw_groesse: "M12",     kernloch: 10.2}
      M16:     {sw_groesse: "M16",     kernloch: 14.0}
      M8x1:    {sw_groesse: "M8x1.0",  kernloch: 7.0}
      M10x1:   {sw_groesse: "M10x1.0", kernloch: 9.0}
      M12x1.5: {sw_groesse: "M12x1.5", kernloch: 10.5}
      M16x1.5: {sw_groesse: "M16x1.5", kernloch: 14.5}
    zylinderschraube:        # ISO 4762 (swStandardISOSocketHeadCap), Durchgang "normal", Flachsenkung
      M5:  {sw_groesse: "M5",  durchgang: 5.5,  senkung_d: 10.0, senkung_t: 5.4}
      M6:  {sw_groesse: "M6",  durchgang: 6.6,  senkung_d: 11.0, senkung_t: 6.4}
      M8:  {sw_groesse: "M8",  durchgang: 9.0,  senkung_d: 15.0, senkung_t: 8.4}
      M10: {sw_groesse: "M10", durchgang: 11.0, senkung_d: 18.0, senkung_t: 10.4}
      M12: {sw_groesse: "M12", durchgang: 13.5, senkung_d: 20.0, senkung_t: 12.4}
    senkschraube:            # ISO 10642 (swStandardISOSocketCTSKFlatHead), Durchgang "normal", Kegelsenkung
      M5:  {sw_groesse: "M5",  durchgang: 5.5,  senkung_d: 10.4, senkwinkel: 90}
      M6:  {sw_groesse: "M6",  durchgang: 6.6,  senkung_d: 12.4, senkwinkel: 90}
      M8:  {sw_groesse: "M8",  durchgang: 9.0,  senkung_d: 16.4, senkwinkel: 90}
      M10: {sw_groesse: "M10", durchgang: 11.0, senkung_d: 20.4, senkwinkel: 90}
    stift:                   # Passbohrung H7 für Zylinderstifte (swStandardISODowelHole), Nennmaß
      "4":  {sw_groesse: "Ø4",  durchmesser: 4.0}
      "5":  {sw_groesse: "Ø5",  durchmesser: 5.0}
      "6":  {sw_groesse: "Ø6",  durchmesser: 6.0}
      "8":  {sw_groesse: "Ø8",  durchmesser: 8.0}
      "10": {sw_groesse: "Ø10", durchmesser: 10.0}
      "12": {sw_groesse: "Ø12", durchmesser: 12.0}
```

Prüfen, dass die Datei gültiges YAML ist:
Run: `.venv\Scripts\python.exe -c "import yaml, pathlib; d = yaml.safe_load(pathlib.Path('swki/wissen/bohrungsnormen.yaml').read_text(encoding='utf-8')); print(sorted(d['normen']['ISO']), d['bohrspitze_grad'])"`
Expected: `['gewinde', 'senkschraube', 'stift', 'zylinderschraube'] 118`

- [ ] **Step 9: Entscheidungsregel anwenden**

Frage 1–4 einzeln bewerten: 1 = alle vier Arten erzeugen ein fehlerfreies Feature mit Normgröße, durch und blind, Gewindetiefe wirkt; 2 = Variante B voll bestimmt mit 3 Punkten und parametrischer Lage; 3 = `abgleich.passt` überall (ggf. nach Korrektur des Tiefenbezugs); 4 = alle Felder im wieder geöffneten Teil lesbar. Ist eine Frage nicht erfüllt: anhalten und melden (siehe „Entscheidungsregel“ oben).

- [ ] **Step 10: Ergebnisse dokumentieren – `docs/stufe0/ergebnisse.md`**

In die Tabelle oben eine Zeile nach S9b einfügen, Spalten wie bei S9b (Frage | Ergebnis | Folge für Stufe 2c), Inhalt aus den vier JSON-Dateien: welche Größen-Strings gewonnen haben, ob Variante A und/oder B mehrere Positionen liefert, Tiefenbezug und Abgleich der Volumina (größte Abweichung), welche Datenfelder lesbar sind und welcher `FastenerSize`-Text zurückkommt, Maßnamen am HoleWzd-Feature:

```markdown
| S10a | Stufe 2c, Bohrungsassistent (Fragen 1–4): HoleWizard5 ISO für Gewinde, ISO 4762, ISO 10642, Stift; mehrere Positionen in einem Feature; Maße je Größe; Daten auslesen | (Befunde aus `ergebnisse/s10_f1…f4*.json`) | (Folgen für Task 3–9 des Plans 2c) |
```

Darunter einen neuen Abschnitt `## Stufe 2c: Spike S10 (Rechner A, SW 2025)` mit je einem Unterabschnitt `### Frage 1` … `### Frage 4` (je 3–6 Zeilen: was probiert, was gemessen, Entscheidung, Abweichungen vom Plan mit Codestelle).

- [ ] **Step 11: Einstellungen prüfen**

Toggle 10 und Integer-Einstellung 6 wie in Step 1 lesen. Expected: unverändert.

- [ ] **Step 12: Commit**

```powershell
git add spikes/s10_gemeinsam.py spikes/s10_f1_bohrungsassistent.py spikes/s10_f2_positionen.py spikes/s10_f3_normmasse.py spikes/s10_f4_auslesen.py docs/stufe0/ergebnisse swki/wissen/bohrungsnormen.yaml docs/stufe0/ergebnisse.md
git commit -m "spike S10a: Bohrungsassistent, Positionen, Normmaße, Auslesen; Maßtabelle" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 2: Spike S10 Teil B – Skizzen und Endbedingungen (Fragen 5–6)

**Files:**
- Create: `spikes/s10_f5_skizzen.py`, `spikes/s10_f6_endbedingungen.py`
- Create (durch die Läufe): `docs/stufe0/ergebnisse/s10_f5_skizzen.json`, `docs/stufe0/ergebnisse/s10_f6_endbedingungen.json`
- Modify: `docs/stufe0/ergebnisse.md` (Zeile S10b, Unterabschnitte Frage 5 und 6, Gesamtentscheidung)

**Interfaces:**
- Consumes: `spikes.s10_gemeinsam.kontext`; `spikes.s9a_gemeinsam.start|teil|volumen_mm3|kasten_oben|feature_masse|flaeche_mit_normale`; `spikes.s9b_gemeinsam.whatswrong`; Produktionscode `swki.compiler.skizze.Skizzierer|ebene_aufloesen|ebene_aus_flaeche|skizziere`, `swki.compiler.topologie.flaeche_aus`, `swki.compiler.sw`, `swki.verbindung.mm`.
- Produces: Befunde zu Frage 5 (Grundlage für Task 6: `verrunde`, `_langloch`, `_richtung_zu_u`, `_verschmelze`, `_kontur`, `lage(nur=…)`) und Frage 6 (Grundlage für Task 7: `MARKE_ZIELFLAECHE`, `VERSATZ_WEG_VON_SKIZZE`, `VERSATZ_MASS`). Die Hilfsfunktionen dieses Spikes sind die Vorlage für die Methoden in Task 6.

- [ ] **Step 1: API-Werte bestätigen**

```powershell
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe -m swki api methode ISketchManager.CreateFillet
.venv\Scripts\python.exe -m swki api methode ISketchManager.CreateSketchSlot
.venv\Scripts\python.exe -m swki api methode ISketchManager.CreateArc
.venv\Scripts\python.exe -m swki api methode ISketchManager.CreateCenterLine
.venv\Scripts\python.exe -m swki api methode ISketchSlot.GetSlotPoints
.venv\Scripts\python.exe -m swki api methode ISketchSlot.GetCenterPointHandle
.venv\Scripts\python.exe -m swki api methode IModelDoc2.SketchAddConstraints
.venv\Scripts\python.exe -m swki api enum swConstrainedCornerAction_e
.venv\Scripts\python.exe -m swki api enum swSketchSlotCreationType_e
.venv\Scripts\python.exe -m swki api enum swSketchSlotLengthType_e
.venv\Scripts\python.exe -m swki api enum swSketchSegments_e
.venv\Scripts\python.exe -m swki api methode IFeatureManager.FeatureCut4
.venv\Scripts\python.exe -m swki api methode IFeatureManager.FeatureExtrusion3
.venv\Scripts\python.exe -m swki api enum swEndConditions_e
```

Expected: CreateFillet 2 (Radius, ConstrainedCorners), CreateSketchSlot 14, CreateArc 10 (Direction +1 = gegen den Uhrzeigersinn), CreateCenterLine 6, GetSlotPoints/GetCenterPointHandle je 0, SketchAddConstraints 1; `swConstrainedCornerKeepGeometry 1`; `swSketchSlotCreationType_line 0`, `…_center_line 1`; `swSketchSlotLengthType_CenterCenter 0`; `swSketchLINE 0`, `swSketchARC 1`; FeatureCut4 27 (14. Parameter `OffsetReverse1`), FeatureExtrusion3 23 (14. Parameter `OffsetReverse1`); `swEndCondUpToSurface 4`, `swEndCondOffsetFromSurface 5`.

- [ ] **Step 2: Frage 5 – `spikes/s10_f5_skizzen.py` schreiben und laufen lassen**

```python
"""S10 Frage 5: runde Konturen in Skizzen – CreateFillet, CreateSketchSlot, CreateArc – jeweils voll bestimmt.

Skizzen mit dem Skizzierer des Compilers (Lagemaße zum Ursprung, AddToDB, Toggle 10 aus) auf einer Standardebene,
danach Extrusion blind 10 und Volumenabgleich mit der analytischen Fläche. Je Fall: Rückgaben, Segmente/Punkte,
Maße (Name, Wert), Bestimmtheit vor dem Schließen, Volumen ist/soll.
a) Rechteck 60 × 40 mit Eckradius 5: CreateFillet(0,005, swConstrainedCornerKeepGeometry = 1) nach Auswahl der beiden
   Linien einer Ecke („linien“) bzw. des Eckpunkts („punkt“); danach Radiusmaß per AddDimension2 auf den Bogen.
   Frage: bleiben Breite/Höhe/Lage am virtuellen Schnittpunkt erhalten? Legt CreateFillet selbst ein Maß an?
b) L-Polygon mit konkaver Ecke (Radien 3/5) wie a) „linien“.
c) Langloch Mitte (10, 5), Länge 30, Breite 8: CreateSketchSlot Typ 1 (Mittelpunkt) und Typ 0 (Linie), Länge
   Mitte–Mitte, ohne Auto-Maße; neue Segmente (Typ, Konstruktion, Endpunkte), GetSlotPoints, Mittelpunkt; Maße:
   Breite = Abstand der geraden Seiten, Länge = Mittellinie, Richtung = Beziehung (0°, 90°) bzw. Winkelmaß zu einer
   u-parallelen Hilfslinie (30°), Lage der Mitte.
d) Kontur 80 × 20 mit zwei Halbkreisen (R 10) aus CreateLine/CreateArc auf oben, vorne, rechts: Richtung +1/−1 je
   nach Drehsinn der (u, v)-Abbildung, gemeinsame Endpunkte (Punktzahl vor/nach sgMERGEPOINTS), Bögen: Mittelpunkt
   voll, Endpunkt nur in der Koordinate mit kleinerem Abstand zum Mittelpunkt bemaßt.
"""

import math

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import start, teil, volumen_mm3
from spikes.s10_gemeinsam import kontext
from swki.compiler import sw
from swki.compiler.skizze import Skizzierer, ebene_aufloesen
from swki.verbindung import mm

SW_ECKE_BEHALTEN = 1  # swConstrainedCornerAction_e.swConstrainedCornerKeepGeometry
SW_NUT = {"mittelpunkt": 1, "linie": 0}  # swSketchSlotCreationType_e (center_line, line)
SW_NUT_MITTE_MITTE = 0  # swSketchSlotLengthType_e.swSketchSlotLengthType_CenterCenter
SW_LINIE, SW_BOGEN = 0, 1  # swSketchSegments_e
L_FORM = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (20.0, 20.0), (20.0, 40.0), (0.0, 40.0)]
L_RADIEN = [3.0, 3.0, 3.0, 5.0, 3.0, 3.0]


def _p(p) -> list:
    return [round(p.X * 1000, 4), round(p.Y * 1000, 4)]


def _segmente(skizze, ab: int = 0) -> list[dict]:
    out = []
    for s in list(skizze.GetSketchSegments or ())[ab:]:
        e = {"typ": s.GetType, "konstruktion": bool(s.ConstructionGeometry)}
        if e["typ"] == SW_LINIE:
            e |= {"start": _p(s.GetStartPoint2), "ende": _p(s.GetEndPoint2)}
        elif e["typ"] == SW_BOGEN:
            e |= {"mitte": _p(s.GetCenterPoint2), "radius": round(s.GetRadius * 1000, 4)}
        out.append(e)
    return out


def _masse(skizze_feature) -> list[dict]:
    out, dd = [], skizze_feature.GetFirstDisplayDimension
    while dd is not None:
        dim = dd.GetDimension2(0)
        out.append({"name": dim.Name, "wert": round(dim.SystemValue, 9)})
        dd = skizze_feature.GetNextDisplayDimension(dd)
    return out


def gleichsinnig(sk) -> bool:
    """Erhält die Abbildung (u, v) → Skizze den Drehsinn? (Determinante > 0)"""
    x0, y0 = sk.zu_skizze(0, 0)
    xu, yu = sk.zu_skizze(1, 0)
    xv, yv = sk.zu_skizze(0, 1)
    return (xu - x0) * (yv - y0) - (xv - x0) * (yu - y0) > 0


def verschmelzen(sk, x: float, y: float) -> int:
    """Mehrere Skizzenpunkte an (x, y) mit sgMERGEPOINTS zu einem machen; Rückgabe: Anzahl vorher."""
    gleich = [p for p in sk.skizze.GetSketchPoints2 or () if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8]
    for p in gleich[1:]:
        sw.auswahl_leeren(sk.model)
        sw.waehle(sk.model, gleich[0], 0)
        sw.waehle(sk.model, p, 0, anhaengen=True)
        sk.model.SketchAddConstraints("sgMERGEPOINTS")
    sw.auswahl_leeren(sk.model)
    return len(gleich)


def lage_nur(sk, uv, text_uv, nur: int) -> None:
    """Wie Skizzierer.lage, aber nur die u- (0) oder v-Lage (1) – Task 6 übernimmt das als lage(..., nur=…)."""
    x, y = sk.zu_skizze(*uv)
    punkt = sk._punkt(x, y)
    for wert, (index, _), waagrecht in ((x, sk.x_von, True), (y, sk.y_von, False)):
        if index != nur:
            continue
        sw.auswahl_leeren(sk.model)
        sw.waehle(sk.model, punkt, 0)
        sw.waehle(sk.model, sk.ursprung, 0, anhaengen=True)
        if abs(wert) < 1e-9:
            sk.model.SketchAddConstraints("sgVERTICALPOINTS2D" if waagrecht else "sgHORIZONTALPOINTS2D")
            continue
        t = sk._text(*text_uv)
        sk._merke(sk.model.AddHorizontalDimension2(*t) if waagrecht else sk.model.AddVerticalDimension2(*t), uv[index])
    sw.auswahl_leeren(sk.model)


def _linien_an(linien, x: float, y: float) -> list:
    return [s for s in linien for p in (s.GetStartPoint2, s.GetEndPoint2)
            if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8]


def verrunden(sk, linien, ecken_uv, radius_mm: float, art: str) -> list[dict]:
    schritte = []
    for u, v in ecken_uv:
        x, y = sk.zu_skizze(u, v)
        sw.auswahl_leeren(sk.model)
        if art == "linien":
            for i, s in enumerate(_linien_an(linien, x, y)):
                sw.waehle(sk.model, s, 0, anhaengen=i > 0)
        else:
            sw.waehle(sk.model, sk._punkt(x, y), 0)
        bogen = sk.sm.CreateFillet(mm(radius_mm), SW_ECKE_BEHALTEN)
        sw.auswahl_leeren(sk.model)
        eintrag = {"ecke": [u, v], "bogen": bogen is not None, "status_nach_fillet": sk.skizze.GetConstrainedStatus}
        if bogen is not None:
            sk.groesse(bogen, (u + 8, v + 8), radius_mm)
            eintrag |= {"radiusmass": sk.masse[-1].name, "status_nach_mass": sk.skizze.GetConstrainedStatus}
        schritte.append(eintrag)
    return schritte


def richtung_zu_u(sk, linie, mitte_uv, winkel: float) -> str:
    u_ist_x = sk.x_von[0] == 0
    w = winkel % 180
    sw.auswahl_leeren(sk.model)
    if w in (0, 90):
        sw.waehle(sk.model, linie, 0)
        sk.model.SketchAddConstraints("sgHORIZONTAL2D" if (w == 0) == u_ist_x else "sgVERTICAL2D")
        sw.auswahl_leeren(sk.model)
        return "beziehung"
    mu, mv = mitte_uv
    xa, ya = sk.zu_skizze(mu, mv)
    xb, yb = sk.zu_skizze(mu + 16, mv)
    hilfe = sk.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0)
    verschmelzen(sk, xa, ya)
    sw.waehle(sk.model, hilfe, 0)
    sk.model.SketchAddConstraints("sgHORIZONTAL2D" if u_ist_x else "sgVERTICAL2D")
    sw.auswahl_leeren(sk.model)
    sk.groesse(hilfe, (mu + 8, mv - 8), 16)
    sw.waehle(sk.model, linie, 0)
    sw.waehle(sk.model, hilfe, 0, anhaengen=True)
    halb = math.radians(w) / 2
    sk._merke(sk.model.AddDimension2(*sk._text(mu + 24 * math.cos(halb), mv + 24 * math.sin(halb))), w)
    sw.auswahl_leeren(sk.model)
    return "winkelmass"


def rechteck(art: str):
    def zeichnen(sk, ctx) -> list:
        sk.element({"rechteck": {"mitte": [0, 0], "breite": 60, "hoehe": 40}})
        linien = list(sk.skizze.GetSketchSegments or ())
        return verrunden(sk, linien, [(-30, -20), (30, -20), (30, 20), (-30, 20)], 5.0, art)
    return zeichnen


def polygon(sk, ctx) -> list:
    sk.element({"polygon": {"punkte": [list(p) for p in L_FORM]}})
    linien = list(sk.skizze.GetSketchSegments or ())
    return [s for ecke, r in zip(L_FORM, L_RADIEN) for s in verrunden(sk, linien, [ecke], r, "linien")]


def langloch(typ: str, winkel: float):
    def zeichnen(sk, ctx) -> dict:
        mu, mv, laenge, breite = 10.0, 5.0, 30.0, 8.0
        w = math.radians(winkel)
        ende = (mu + laenge / 2 * math.cos(w), mv + laenge / 2 * math.sin(w))
        anfang = (mu, mv) if typ == "mittelpunkt" else (mu - laenge / 2 * math.cos(w), mv - laenge / 2 * math.sin(w))
        (x1, y1), (x2, y2) = sk.zu_skizze(*anfang), sk.zu_skizze(*ende)
        vorher = len(sk.skizze.GetSketchSegments or ())
        nut = sk.sm.CreateSketchSlot(SW_NUT[typ], SW_NUT_MITTE_MITTE, mm(breite), x1, y1, 0.0, x2, y2, 0.0,
                                     0.0, 0.0, 0.0, 1, False)
        d: dict = {"nut": nut is not None}
        if nut is None:
            return d
        neu = list(sk.skizze.GetSketchSegments or ())[vorher:]
        mitte = nut.GetCenterPointHandle
        d |= {"neue_segmente": _segmente(sk.skizze, vorher), "slotpunkte": [_p(p) for p in nut.GetSlotPoints or ()],
              "mittelpunkt": _p(mitte) if mitte is not None else None,
              "laenge_breite_mm": [round(nut.Length * 1000, 4), round(nut.Width * 1000, 4)]}
        seiten = [s for s in neu if s.GetType == SW_LINIE and not s.ConstructionGeometry]
        achsen = [s for s in neu if s.GetType == SW_LINIE and s.ConstructionGeometry]
        d["seiten_achsen"] = [len(seiten), len(achsen)]
        if len(seiten) != 2 or not achsen:
            return d
        sw.auswahl_leeren(sk.model)
        sw.waehle(sk.model, seiten[0], 0)
        sw.waehle(sk.model, seiten[1], 0, anhaengen=True)
        sk._merke(sk.model.AddDimension2(*sk._text(mu, mv + 12)), breite)
        sw.auswahl_leeren(sk.model)
        sk.groesse(achsen[0], (mu, mv - 12), laenge)
        d["richtung"] = richtung_zu_u(sk, achsen[0], (mu, mv), winkel)
        try:
            sk.lage([mu, mv], (mu - 25, mv - 8))
            d["lage_mitte"] = True
        except Exception as e:  # Spike: Typ 0 hat evtl. keinen Mittelpunkt
            d["lage_mitte"] = repr(e)
        d["masse_merk"] = [m.name for m in sk.masse]
        return d
    return zeichnen


def kontur(sk, ctx) -> dict:
    ecken = [(-40.0, 25.0), (40.0, 25.0), (40.0, 45.0), (-40.0, 45.0)]
    segmente = [("linie", None), ("bogen", (40.0, 35.0)), ("linie", None), ("bogen", (-40.0, 35.0))]
    d: dict = {"gleichsinnig": gleichsinnig(sk), "erzeugt": []}
    richtung = 1 if d["gleichsinnig"] else -1
    for i, (art, mitte) in enumerate(segmente):
        (xa, ya), (xb, yb) = sk.zu_skizze(*ecken[i]), sk.zu_skizze(*ecken[(i + 1) % 4])
        if art == "linie":
            seg = sk.sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)
        else:
            xm, ym = sk.zu_skizze(*mitte)
            seg = sk.sm.CreateArc(xm, ym, 0.0, xa, ya, 0.0, xb, yb, 0.0, richtung)
        d["erzeugt"].append(seg is not None)
    d["punkte_vor_verschmelzen"] = len(sk.skizze.GetSketchPoints2 or ())
    d["verschmolzen"] = [verschmelzen(sk, *sk.zu_skizze(*e)) for e in ecken]
    d["punkte_nach_verschmelzen"] = len(sk.skizze.GetSketchPoints2 or ())
    for i, (art, mitte) in enumerate(segmente):
        ende = ecken[(i + 1) % 4]
        if art == "bogen":
            sk.lage(list(mitte), (mitte[0] + 8, mitte[1] + 8))
            nur = 0 if abs(ende[0] - mitte[0]) <= abs(ende[1] - mitte[1]) else 1
            lage_nur(sk, ende, (ende[0] + 8, ende[1] + 8), nur)
        else:
            sk.lage(list(ende), (ende[0] + 8, ende[1] + 8))
    return d


def _fall(app, r, ebene: str, zeichnen, soll_flaeche: float) -> dict:
    """Skizze auf ebene mit zeichnen(sk, ctx) (Skizze offen), schließen, Extrusion blind 10, Volumen."""
    with teil(app, r) as model:
        ctx = kontext(app, model)
        se = ebene_aufloesen(ctx, ebene)
        sm = model.SketchManager
        sw.auswahl_leeren(model)
        sw.waehle(model, se.objekt, 0)
        sm.InsertSketch(True)
        d: dict = {}
        try:
            sk = Skizzierer(ctx, se, sm.ActiveSketch)
            try:
                with sw.einstellung(app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
                    d["schritte"] = zeichnen(sk, ctx)
            except Exception as e:  # Spike: alles protokollieren
                d["fehler"] = repr(e)
            d["status"] = sm.ActiveSketch.GetConstrainedStatus
            d["punkte"] = len(sm.ActiveSketch.GetSketchPoints2 or ())
            d["segmente"] = _segmente(sm.ActiveSketch)
        finally:
            sm.InsertSketch(True)
        skizze = sw.letztes_feature(model)
        d["masse"] = _masse(skizze)
        sw.auswahl_leeren(model)
        skizze.Select2(False, 0)
        f = model.FeatureManager.FeatureExtrusion3(
            True, False, False, 0, 0, 0.010, 0.0, False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, True, True, 0, 0.0, False,
        )
        d["extrusion"] = f is not None
        d["volumen_ist"] = volumen_mm3(model)
        d["volumen_soll"] = round(soll_flaeche * 10, 3)
        d["box"] = [round(c * 1000, 4) for c in model.GetPartBox(True)]
        return d


def pruefen() -> dict:
    r, app = start()
    flaeche_rechteck = 2400 - (4 - math.pi) * 25
    flaeche_l = 1200 - 5 * (9 - 9 * math.pi / 4) + (25 - 25 * math.pi / 4)
    flaeche_nut = 30 * 8 + math.pi * 16
    flaeche_kontur = 1600 + 100 * math.pi
    return {
        "a_rechteck_linien": _fall(app, r, "oben", rechteck("linien"), flaeche_rechteck),
        "a_rechteck_punkt": _fall(app, r, "oben", rechteck("punkt"), flaeche_rechteck),
        "b_polygon_konkav": _fall(app, r, "vorne", polygon, flaeche_l),
        "c_langloch_mittelpunkt_0": _fall(app, r, "oben", langloch("mittelpunkt", 0), flaeche_nut),
        "c_langloch_linie_0": _fall(app, r, "oben", langloch("linie", 0), flaeche_nut),
        "c_langloch_mittelpunkt_90": _fall(app, r, "oben", langloch("mittelpunkt", 90), flaeche_nut),
        "c_langloch_mittelpunkt_30": _fall(app, r, "oben", langloch("mittelpunkt", 30), flaeche_nut),
        **{f"d_kontur_{e}": _fall(app, r, e, kontur, flaeche_kontur) for e in ("oben", "vorne", "rechts")},
    }


if __name__ == "__main__":
    lauf("s10_f5_skizzen", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s10_f5_skizzen`
Expected (Weg des Plans): `a_rechteck_linien`, `b_polygon_konkav`, `c_langloch_mittelpunkt_0|90|30` und alle `d_kontur_*` mit `status` 3 und `volumen_ist` = `volumen_soll` (±0,001). Für Task 6 festhalten: (a) ob `status_nach_fillet` schon 3 ist (dann legt CreateFillet selbst ein Maß/eine Beziehung an → `verrunde` darf kein Radiusmaß ergänzen, sondern bindet das vorhandene) und ob Breite/Höhe weiter 60/40 messen (`masse`); (c) `seiten_achsen` = [2, 1] (sonst Auswahl in `_langloch` anpassen), ob die Länge der Mittellinie 30 oder 15 ist, ob es einen `mittelpunkt` gibt; (d) `punkte_vor_verschmelzen` (8 = Bögen legen eigene Endpunkte an, 6 = sie teilen sie) und das Vorzeichen von `gleichsinnig` je Ebene. Scheitert eine Variante des Plans, aber eine andere geht (z. B. „punkt“ statt „linien“, Typ 0 statt 1): die funktionierende in Task 6 übernehmen und im Bericht nennen. Scheitern alle Varianten eines Elements: Entscheidungsregel.

- [ ] **Step 3: Frage 6 – `spikes/s10_f6_endbedingungen.py` schreiben und laufen lassen**

```python
"""S10 Frage 6: FeatureCut4/FeatureExtrusion3 mit swEndCondUpToSurface (4) und swEndCondOffsetFromSurface (5).

Block 100 × 60 × 20 (Y 0…20). Skizzen mit skizziere() des Compilers, Zielfläche mit Select4 und Marke angehängt.
a) Schnitt Quadrat 20 × 20 von der Deckfläche bis zur Unterseite, Marke 1, 2 bzw. 32 (Hilfe FeatureExtrusion3:
   „End condition reference entity – 1“); Soll-Abnahme 8000 mm³.
b) Schnitt versatz 5 mm von der Unterseite, OffsetReverse1 False bzw. True; Soll (False = zur Skizze hin): Restwand 5
   → 6000 mm³; Maße des Features (Name des Versatzmaßes).
c) Aufsatz Kreis Ø10 von einer Ebene 40 über oben (umgekehrt) bis zur Deckfläche; Soll +π·25·20 = 1570,796 mm³.
d) Aufsatz wie c) mit Versatz 5 von der Deckfläche, OffsetReverse1 False/True: welche Seite, wie viele Körper?
"""

import math

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import feature_masse, flaeche_mit_normale, kasten_oben, start, teil, volumen_mm3
from spikes.s9b_gemeinsam import whatswrong
from spikes.s10_gemeinsam import kontext
from swki.compiler import sw
from swki.compiler.skizze import ebene_aufloesen, ebene_aus_flaeche, skizziere
from swki.compiler.topologie import flaeche_aus

BIS_FLAECHE, VERSATZ = 4, 5  # swEndConditions_e


def _schnitt(model, typ: int, d1_m: float, versatz_weg: bool):
    return model.FeatureManager.FeatureCut4(
        True, False, False, typ, 0, d1_m, 0.0, False, False, False, False, 0.0, 0.0,
        versatz_weg, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False,
    )


def _aufsatz(model, typ: int, d1_m: float, versatz_weg: bool, umkehren: bool):
    return model.FeatureManager.FeatureExtrusion3(
        True, False, umkehren, typ, 0, d1_m, 0.0, False, False, False, False, 0.0, 0.0,
        versatz_weg, False, False, False, True, True, True, 0, 0.0, False,
    )


def fall_schnitt(app, r, typ: int, marke: int, d1_mm: float = 0.0, versatz_weg: bool = False) -> dict:
    with teil(app, r) as model:
        kasten = kasten_oben(model, 100, 60, 20)
        ctx = kontext(app, model)
        oben = ebene_aus_flaeche(flaeche_aus(flaeche_mit_normale(kasten, (0.0, 1.0, 0.0))))
        unten = flaeche_mit_normale(kasten, (0.0, -1.0, 0.0))
        skizze, _ = skizziere(ctx, oben, [{"rechteck": {"mitte": [0, 0], "breite": 20, "hoehe": 20}}], "s_skizze")
        v0 = volumen_mm3(model)
        sw.auswahl_leeren(model)
        skizze.Select2(False, 0)
        sw.waehle(model, unten, marke, anhaengen=True)
        f = _schnitt(model, typ, d1_mm / 1000, versatz_weg)
        return {"feature": f is not None, "abnahme_mm3": round(v0 - volumen_mm3(model), 3),
                "masse": feature_masse(f) if f else None, "whatswrong": whatswrong(model)}


def fall_aufsatz(app, r, typ: int, marke: int, d1_mm: float = 0.0, versatz_weg: bool = False) -> dict:
    with teil(app, r) as model:
        kasten = kasten_oben(model, 100, 60, 20)
        ctx = kontext(app, model)
        deck = flaeche_mit_normale(kasten, (0.0, 1.0, 0.0))
        ebene = ebene_aufloesen(ctx, {"versatz": {"ebene": "oben", "abstand": 40}})
        skizze, _ = skizziere(ctx, ebene, [{"kreis": {"mitte": [0, 0], "durchmesser": 10}}], "z_skizze")
        v0 = volumen_mm3(model)
        sw.auswahl_leeren(model)
        skizze.Select2(False, 0)
        sw.waehle(model, deck, marke, anhaengen=True)
        f = _aufsatz(model, typ, d1_mm / 1000, versatz_weg, True)
        return {"feature": f is not None, "zunahme_mm3": round(volumen_mm3(model) - v0, 3),
                "box": [round(c * 1000, 4) for c in model.GetPartBox(True)],
                "koerper": len(model.GetBodies2(0, False) or ()),
                "masse": feature_masse(f) if f else None, "whatswrong": whatswrong(model)}


def pruefen() -> dict:
    r, app = start()
    d: dict = {"soll": {"a_mm3": 8000, "b_false_mm3": 6000, "c_mm3": round(math.pi * 25 * 20, 3)}}
    for marke in (1, 2, 32):
        d[f"a_schnitt_bis_flaeche_marke_{marke}"] = fall_schnitt(app, r, BIS_FLAECHE, marke)
    for weg in (False, True):
        d[f"b_schnitt_versatz_5_offsetreverse_{weg}"] = fall_schnitt(app, r, VERSATZ, 1, 5.0, weg)
        d[f"d_aufsatz_versatz_5_offsetreverse_{weg}"] = fall_aufsatz(app, r, VERSATZ, 1, 5.0, weg)
    d["c_aufsatz_bis_flaeche_marke_1"] = fall_aufsatz(app, r, BIS_FLAECHE, 1)
    return d


if __name__ == "__main__":
    lauf("s10_f6_endbedingungen", pruefen)
```

Run: `.venv\Scripts\python.exe -m spikes.s10_f6_endbedingungen`
Expected (Weg des Plans): `a_…_marke_1` Abnahme 8000; `b_…_False` Abnahme 6000, Versatzmaß heißt `D1` (`masse`); `c_…` Zunahme 1570.796, Box oben 40. Funktioniert Marke 1 nicht, aber 2 oder 32: b–d mit der funktionierenden Marke neu laufen lassen (Konstante in `fall_schnitt`/`fall_aufsatz`-Aufrufen ändern) und diese Marke in Task 7 verwenden. Ist `False` die falsche Seite (Abnahme 10000 oder Fehler), gilt `True` für „zur Skizze hin“.

- [ ] **Step 4: Entscheidungsregel und Dokumentation**

Frage 5 ist erfüllt, wenn je Element (Eckradius, konkave Ecke, Langloch 0°/90°/schräg, Kontur auf drei Ebenen) eine Variante voll bestimmt und volumengenau ist; Frage 6, wenn bis_flaeche und versatz_von_flaeche für Schnitt und Aufsatz das Sollvolumen liefern. Sonst anhalten (Entscheidungsregel). In `docs/stufe0/ergebnisse.md` eine Zeile S10b nach S10a (gleiches Format) und die Unterabschnitte `### Frage 5`, `### Frage 6` ergänzen; am Ende des Abschnitts `### Entscheidung` mit einer Liste „Plan unverändert“ bzw. „geändert: <Konstante/Methode> → <Wert/Verhalten>, Beleg <JSON-Schlüssel>“ für jede Zeile der Tabelle „Abhängigkeiten vom Spike S10“.

- [ ] **Step 5: Einstellungen prüfen**

Toggle 10 und Integer-Einstellung 6 lesen. Expected: unverändert gegenüber Task 1 Step 1.

- [ ] **Step 6: Commit**

```powershell
git add spikes/s10_f5_skizzen.py spikes/s10_f6_endbedingungen.py docs/stufe0/ergebnisse docs/stufe0/ergebnisse.md
git commit -m "spike S10b: Skizzenverrundung, Langloch, Bögen, Endbedingungen bis/versatz Fläche" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 3: Normtabelle, Schema und Validierung (ohne SolidWorks)

**Files:**
- Create: `swki/spec/normen.py`, `swki/spec/konturen.py`, `tests/spec/test_normen.py`, `tests/spec/test_konturen.py`
- Modify: `schema/teil.schema.json` (`$defs.element`, neu `$defs.segment`, `$defs.ende`, neu `$defs.f_normbohrung`, `$defs.feature`)
- Modify: `swki/spec/laden.py` (Imports, `_POSITIV`, Winkelprüfung, neue Befunde)
- Modify: `config/standard.yaml` (`bohrungsnorm: ISO`), `pyproject.toml` (package-data `wissen/*.yaml`)
- Test: `tests/spec/test_laden.py` (18 neue Tests), `tests/test_konfig.py` (eine Zeile)

**Interfaces:**
- Consumes: `swki/wissen/bohrungsnormen.yaml` (Task 1); `swki.konfig.PROJEKT`, `lade_standard`; `swki.spec.ausdruck.auswerten`, `AusdruckFehler`.
- Produces (`swki/spec/normen.py`): `TABELLE: Path`; `ARTEN = ("gewinde", "zylinderschraube", "senkschraube", "stift")`; `SW_ART: dict[str, int]`, `SW_NORM: dict[str, int]`, `SW_BEFESTIGUNG: dict[str, int]`, `SW_END_BLIND = 0`, `SW_END_DURCH_ALLES = 1`; `lade_tabelle(pfad: Path = TABELLE) -> dict` (gecacht, Größen-Schlüssel als Text); `groesse_text(groesse) -> str`; `norm_von(f: dict, standard: dict | None = None) -> str`; `verfuegbare_groessen(art: str, norm: str = "ISO") -> list[str]`; `normmasse(art: str, groesse, norm: str = "ISO") -> dict | None`; `bohrspitze_grad() -> float`.
- Produces (`swki/spec/konturen.py`): `eckradien(polygon: dict, parameter: dict) -> list[float]`; `kontur_punkte_roh(kontur: dict) -> list`; `kontur_punkte(kontur: dict, parameter: dict) -> list[tuple[float, float]]`; `bogenende_koordinate(ende, mitte) -> int` (0 = u, 1 = v).
- Produces (Schema): Elemente `rechteck.radius`, `polygon.radien` (Wert oder Liste je Ecke, 0 = scharf), `langloch {mitte, laenge, breite, winkel?}`, `kontur {start, segmente: [{linie: [u, v]} | {bogen: [u, v], mitte: [u, v]}]}`; `ende.typ` zusätzlich `bis_flaeche` (`flaeche`) und `versatz_von_flaeche` (`flaeche`, `abstand`); Feature-Typ `normbohrung {art, groesse, norm?, flaeche, positionen, durch | tiefe, gewindetiefe?}`.

- [ ] **Step 1: Failing tests – `tests/spec/test_konturen.py`**

```python
import pytest

from swki.spec.konturen import bogenende_koordinate, eckradien, kontur_punkte, kontur_punkte_roh

DREIECK = [[0, 0], [10, 0], [0, 10]]


def test_eckradien_ein_wert_fuer_alle():
    assert eckradien({"punkte": DREIECK, "radien": "=R"}, {"R": 2}) == [2.0, 2.0, 2.0]


def test_eckradien_je_ecke():
    assert eckradien({"punkte": DREIECK, "radien": [0, 1, "=R"]}, {"R": 2}) == [0.0, 1.0, 2.0]


def test_eckradien_ohne_angabe_scharf():
    assert eckradien({"punkte": DREIECK}, {}) == [0.0, 0.0, 0.0]


def test_kontur_punkte():
    kontur = {"start": [0, 0], "segmente": [{"linie": ["=A", 0]}, {"bogen": ["=A", 30], "mitte": ["=A", 15]},
                                            {"linie": [0, 30]}, {"linie": [0, 0]}]}
    assert kontur_punkte_roh(kontur) == [[0, 0], ["=A", 0], ["=A", 30], [0, 30], [0, 0]]
    assert kontur_punkte(kontur, {"A": 40}) == [(0.0, 0.0), (40.0, 0.0), (40.0, 30.0), (0.0, 30.0), (0.0, 0.0)]


@pytest.mark.parametrize(("ende", "mitte", "index"), [
    ((40, 30), (40, 15), 0),   # Ende senkrecht über dem Mittelpunkt: u festlegen, v folgt aus dem Radius
    ((55, 15), (40, 15), 1),   # Ende rechts vom Mittelpunkt: v festlegen
    ((50, 25), (40, 15), 0),   # 45°: gleich weit – u
])
def test_bogenende_koordinate(ende, mitte, index):
    assert bogenende_koordinate(ende, mitte) == index
```

- [ ] **Step 2: Failing tests – `tests/spec/test_normen.py`**

```python
import pytest

from swki.spec.normen import ARTEN, groesse_text, lade_tabelle, norm_von, normmasse, verfuegbare_groessen


def test_tabelle_hat_alle_arten():
    tabelle = lade_tabelle()
    assert tabelle["bohrspitze_grad"] == 118
    assert set(tabelle["normen"]["ISO"]) == set(ARTEN)


def test_m8_kernloch_wie_s9b():
    assert normmasse("gewinde", "M8")["kernloch"] == pytest.approx(6.8)  # S9b Baustein 21: Zylinder r 3,4


@pytest.mark.parametrize(("groesse", "text"), [("M8", "M8"), (8, "8"), (8.0, "8")])
def test_groesse_text(groesse, text):
    assert groesse_text(groesse) == text


def test_groessen_der_referenz_vorhanden():
    for art, groesse in (("zylinderschraube", "M8"), ("stift", 8), ("gewinde", "M10"), ("gewinde", "M12x1.5"),
                         ("senkschraube", "M6")):
        assert normmasse(art, groesse) is not None, (art, groesse)
    assert "M8" in verfuegbare_groessen("gewinde")


def test_unbekannte_groesse_und_norm():
    assert normmasse("gewinde", "M7") is None
    assert verfuegbare_groessen("gewinde", "DIN") == []


@pytest.mark.parametrize(("feature", "standard", "norm"), [
    ({}, None, "ISO"),                              # Vorgabe aus config/standard.yaml
    ({}, {"bohrungsnorm": "DIN"}, "DIN"),
    ({"norm": "ISO"}, {"bohrungsnorm": "DIN"}, "ISO"),  # je Bohrung überschreibbar
])
def test_norm_von(feature, standard, norm):
    assert norm_von(feature, standard) == norm
```

- [ ] **Step 3: Failing tests – an `tests/spec/test_laden.py` anhängen**

```python
NB = {
    "id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8",
    "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [["=-L/2+20", 0], ["=L/2-20", 0]], "durch": True,
}
TASCHE = {
    "id": "f7", "typ": "schnitt",
    "skizze": {"ebene": {"feature": "f1", "flaeche": "+y"},
               "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 20, "hoehe": 10}}]},
    "ende": {"typ": "versatz_von_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}, "abstand": 5},
}


def _mit_feature(*features):
    spec = _spec()
    spec["features"] = [spec["features"][0], *features]
    spec["pruefung"] = {"huellquader": ["=L", "=H", "=B"]}
    return spec


def _mit_element(element):
    spec = _spec()
    spec["features"][0]["skizze"]["elemente"] = [element]
    return spec


def test_normbohrung_gueltig(tmp_path):
    gewinde = {k: v for k, v in NB.items() if k != "durch"} | {"id": "f3", "art": "gewinde", "groesse": "M10",
                                                               "tiefe": 16, "gewindetiefe": 12}
    stift = NB | {"id": "f4", "art": "stift", "groesse": 8}
    spec = _mit_feature(NB, gewinde, stift)
    assert schema_befunde(spec) == []
    assert plausibel_befunde(spec, tmp_path) == []


@pytest.mark.parametrize(("art", "groesse"), [("gewinde", "M7"), ("stift", "M8")])
def test_normbohrung_groesse_nicht_in_tabelle(tmp_path, art, groesse):
    [befund] = plausibel_befunde(_mit_feature(NB | {"art": art, "groesse": groesse}), tmp_path)
    assert befund["pfad"] == "features[1].groesse"
    assert "nicht in der Maßtabelle" in befund["meldung"] and "verfügbar:" in befund["meldung"]


@pytest.mark.parametrize(("aenderung", "meldung"), [
    ({"gewindetiefe": 10}, "nur bei art: gewinde"),
    ({"art": "gewinde", "groesse": "M10", "durch": None, "tiefe": 16}, "Pflicht"),
    ({"art": "gewinde", "groesse": "M10", "durch": None, "tiefe": 16, "gewindetiefe": 20}, "nicht größer als tiefe"),
])
def test_gewindetiefe_regeln(tmp_path, aenderung, meldung):
    nb = {k: v for k, v in (NB | aenderung).items() if v is not None}
    spec = _mit_feature(nb)
    assert schema_befunde(spec) == []
    assert any(meldung in b["meldung"] for b in plausibel_befunde(spec, tmp_path))


def test_normbohrung_braucht_tiefe_oder_durch():
    assert schema_befunde(_mit_feature({k: v for k, v in NB.items() if k != "durch"}))


def test_runde_skizzenelemente_gueltig(tmp_path):
    spec = _spec()
    spec["features"][0]["skizze"]["elemente"] = [
        {"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B", "radius": 6}},
        {"polygon": {"punkte": [[0, 0], [40, 0], [40, 20], [20, 20], [20, 40], [0, 40]], "radien": [0, 3, 3, 5, 3, 3]}},
        {"langloch": {"mitte": [10, 5], "laenge": 30, "breite": 8, "winkel": 0}},
        {"kontur": {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                                  {"linie": [0, 30]}, {"linie": [0, 0]}]}},
    ]
    assert schema_befunde(spec) == []
    assert plausibel_befunde(spec, tmp_path) == []


@pytest.mark.parametrize(("element", "pfad"), [
    ({"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 20, "radius": 10}}, "rechteck.radius"),
    ({"polygon": {"punkte": [[0, 0], [40, 0], [40, 10], [0, 10]], "radien": 5}}, "polygon.radien"),
])
def test_eckradius_zu_gross(tmp_path, element, pfad):
    befunde = plausibel_befunde(_mit_element(element), tmp_path)
    assert befunde and all(b["pfad"].startswith(f"features[0].skizze.elemente[0].{pfad}") for b in befunde)
    assert "halbe" in befunde[0]["meldung"]


def test_radien_passen_nicht_zur_eckenzahl(tmp_path):
    element = {"polygon": {"punkte": [[0, 0], [40, 0], [40, 40], [0, 40]], "radien": [1, 2, 3]}}
    [befund] = plausibel_befunde(_mit_element(element), tmp_path)
    assert "3 Werte für 4 Ecken" in befund["meldung"]


def test_kontur_bogen_ungleich_weit(tmp_path):
    kontur = {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 31], "mitte": [40, 15]},
                                            {"linie": [0, 31]}, {"linie": [0, 0]}]}
    [befund] = plausibel_befunde(_mit_element({"kontur": kontur}), tmp_path)
    assert befund["pfad"] == "features[0].skizze.elemente[0].kontur.segmente[1]"
    assert "ungleich weit" in befund["meldung"]


def test_kontur_nicht_geschlossen(tmp_path):
    kontur = {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                            {"linie": [0, 30]}]}
    [befund] = plausibel_befunde(_mit_element({"kontur": kontur}), tmp_path)
    assert "nicht geschlossen" in befund["meldung"]


def test_langloch_winkel_bereich(tmp_path):
    spec = _mit_element({"langloch": {"mitte": [0, 0], "laenge": 30, "breite": 8, "winkel": 0}})
    assert plausibel_befunde(spec, tmp_path) == []
    spec["features"][0]["skizze"]["elemente"][0]["langloch"]["winkel"] = 180
    [befund] = plausibel_befunde(spec, tmp_path)
    assert "[0, 180)" in befund["meldung"]


def test_ende_bis_flaeche_und_versatz_gueltig(tmp_path):
    spec = _spec()
    spec["features"] += [TASCHE, TASCHE | {"id": "f8", "ende": {"typ": "bis_flaeche",
                                                               "flaeche": {"feature": "f7", "flaeche": "+y"}}}]
    assert schema_befunde(spec) == []
    assert plausibel_befunde(spec, tmp_path) == []


def test_ende_versatz_braucht_abstand():
    spec = _spec()
    spec["features"].append(TASCHE | {"ende": {"typ": "versatz_von_flaeche",
                                               "flaeche": {"feature": "f1", "flaeche": "-y"}}})
    assert schema_befunde(spec)


def test_ende_flaeche_nur_auf_fruehere_features(tmp_path):
    spec = _spec()
    spec["features"].append(TASCHE | {"ende": TASCHE["ende"] | {"flaeche": {"feature": "f9", "flaeche": "-y"}}})
    [befund] = plausibel_befunde(spec, tmp_path)
    assert befund["pfad"] == "features[6].ende.flaeche.feature"


def test_ende_felder_passen_zum_typ(tmp_path):
    spec = _spec()
    spec["features"] += [
        TASCHE | {"ende": {"typ": "blind", "tiefe": 5, "flaeche": {"feature": "f1", "flaeche": "-y"}}},
        TASCHE | {"id": "f8", "ende": {"typ": "bis_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}, "tiefe": 5}},
    ]
    meldungen = [b["meldung"] for b in plausibel_befunde(spec, tmp_path)]
    assert any("flaeche gilt nur" in m for m in meldungen)
    assert any("tiefe gilt nicht" in m for m in meldungen)
```

In `tests/test_konfig.py`, `test_standard_projektdatei` um eine Zeile ergänzen:

```python
    assert daten["bohrungsnorm"] == "ISO"
```

- [ ] **Step 4: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec tests/test_konfig.py -q`
Expected: FAIL – `ModuleNotFoundError: swki.spec.konturen` / `swki.spec.normen`, Schemafehler für die neuen Elemente, `KeyError: 'bohrungsnorm'`.

- [ ] **Step 5: `swki/spec/normen.py` anlegen**

```python
"""Maßtabelle der Normbohrungen (swki/wissen/bohrungsnormen.yaml, Spike S10) und Zuordnung zum Bohrungsassistenten.

Enum-Werte laut `swki api enum` (Spec 2c §3.2); der Handler normbohrung und die Prüfung normbohrungen nutzen dieselben
Konstanten.
"""

from functools import cache
from pathlib import Path

import yaml

from swki.konfig import PROJEKT, lade_standard

TABELLE = PROJEKT / "swki" / "wissen" / "bohrungsnormen.yaml"
ARTEN = ("gewinde", "zylinderschraube", "senkschraube", "stift")
SW_ART = {"zylinderschraube": 0, "senkschraube": 1, "stift": 2, "gewinde": 4}  # swWzdGeneralHoleTypes_e
SW_NORM = {"ISO": 8}  # swWzdHoleStandards_e.swStandardISO
SW_BEFESTIGUNG = {  # swWzdHoleStandardFastenerTypes_e (Abhängig von S10 Frage 1)
    "zylinderschraube": 139,  # swStandardISOSocketHeadCap
    "senkschraube": 140,  # swStandardISOSocketCTSKFlatHead
    "stift": 710,  # swStandardISODowelHole
    "gewinde": 147,  # swStandardISOTappedHole
}
SW_END_BLIND = 0  # swEndConditions_e.swEndCondBlind
SW_END_DURCH_ALLES = 1  # swEndConditions_e.swEndCondThroughAll


def groesse_text(groesse) -> str:
    """Größe aus der Spezifikation als Tabellenschlüssel: "M8", "M10x1"; Stift-Nenndurchmesser 8 → "8"."""
    if isinstance(groesse, (int, float)) and not isinstance(groesse, bool):
        return f"{groesse:g}"
    return str(groesse)


@cache
def lade_tabelle(pfad: Path = TABELLE) -> dict:
    """Maßtabelle; Größen-Schlüssel immer als Text (YAML liest 8 sonst als Zahl). Nicht verändern (gecacht)."""
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    daten["normen"] = {
        norm: {art: {groesse_text(g): m for g, m in groessen.items()} for art, groessen in arten.items()}
        for norm, arten in daten["normen"].items()
    }
    return daten


def norm_von(f: dict, standard: dict | None = None) -> str:
    """Norm einer Bohrung: eigene Angabe, sonst bohrungsnorm aus config/standard.yaml, sonst ISO."""
    return f.get("norm") or (standard if standard is not None else lade_standard()).get("bohrungsnorm", "ISO")


def verfuegbare_groessen(art: str, norm: str = "ISO") -> list[str]:
    return list(lade_tabelle()["normen"].get(norm, {}).get(art, {}))


def normmasse(art: str, groesse, norm: str = "ISO") -> dict | None:
    """Maße (mm) einer Normbohrung laut Tabelle oder None, wenn Norm, Art oder Größe fehlen."""
    return lade_tabelle()["normen"].get(norm, {}).get(art, {}).get(groesse_text(groesse))


def bohrspitze_grad() -> float:
    return float(lade_tabelle()["bohrspitze_grad"])
```

- [ ] **Step 6: `swki/spec/konturen.py` anlegen**

```python
"""Reine Hilfen für runde Konturen in Skizzen (Spec 2c §4): Eckradien, Konturpunkte, Bogenendpunkte. Längen in mm."""

from swki.spec.ausdruck import auswerten


def eckradien(polygon: dict, parameter: dict) -> list[float]:
    """Radius je Ecke eines Polygons: ein Wert für alle Ecken oder eine Liste je Ecke (0 = scharf); ohne radien 0."""
    roh = polygon.get("radien", 0)
    if isinstance(roh, list):
        return [auswerten(r, parameter) for r in roh]
    return [auswerten(roh, parameter)] * len(polygon["punkte"])


def kontur_punkte_roh(kontur: dict) -> list:
    """Eckpunkte wie in der Spezifikation: start, dann der Endpunkt jedes Segments (bei geschlossener Kontur = start)."""
    return [kontur["start"], *(s["linie"] if "linie" in s else s["bogen"] for s in kontur["segmente"])]


def kontur_punkte(kontur: dict, parameter: dict) -> list[tuple[float, float]]:
    return [(auswerten(u, parameter), auswerten(v, parameter)) for u, v in kontur_punkte_roh(kontur)]


def bogenende_koordinate(ende, mitte) -> int:
    """Welche Koordinate (0 = u, 1 = v) den Endpunkt eines Bogens festlegt, dessen Mittelpunkt und Anfang bestimmt sind:
    die mit dem kleineren Abstand zum Mittelpunkt – die andere folgt aus dem Radius (S10 Frage 5)."""
    return 0 if abs(ende[0] - mitte[0]) <= abs(ende[1] - mitte[1]) else 1
```

- [ ] **Step 7: Schema erweitern – `schema/teil.schema.json`**

`$defs.element` vollständig ersetzen und direkt dahinter `$defs.segment` einfügen:

```json
    "element": {
      "oneOf": [
        {
          "type": "object", "required": ["rechteck"], "additionalProperties": false,
          "properties": {
            "rechteck": {
              "type": "object", "required": ["mitte", "breite", "hoehe"], "additionalProperties": false,
              "properties": {
                "mitte": {"$ref": "#/$defs/punkt2"}, "breite": {"$ref": "#/$defs/wert"}, "hoehe": {"$ref": "#/$defs/wert"},
                "radius": {"$ref": "#/$defs/wert"}
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
              "properties": {
                "punkte": {"type": "array", "minItems": 3, "items": {"$ref": "#/$defs/punkt2"}},
                "radien": {"oneOf": [
                  {"$ref": "#/$defs/wert"},
                  {"type": "array", "minItems": 3, "items": {"$ref": "#/$defs/wert"}}
                ]}
              }
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
        },
        {
          "type": "object", "required": ["langloch"], "additionalProperties": false,
          "properties": {
            "langloch": {
              "type": "object", "required": ["mitte", "laenge", "breite"], "additionalProperties": false,
              "properties": {
                "mitte": {"$ref": "#/$defs/punkt2"}, "laenge": {"$ref": "#/$defs/wert"}, "breite": {"$ref": "#/$defs/wert"},
                "winkel": {"$ref": "#/$defs/wert"}
              }
            }
          }
        },
        {
          "type": "object", "required": ["kontur"], "additionalProperties": false,
          "properties": {
            "kontur": {
              "type": "object", "required": ["start", "segmente"], "additionalProperties": false,
              "properties": {
                "start": {"$ref": "#/$defs/punkt2"},
                "segmente": {"type": "array", "minItems": 2, "items": {"$ref": "#/$defs/segment"}}
              }
            }
          }
        }
      ]
    },
    "segment": {
      "oneOf": [
        {
          "type": "object", "required": ["linie"], "additionalProperties": false,
          "properties": {"linie": {"$ref": "#/$defs/punkt2"}}
        },
        {
          "type": "object", "required": ["bogen", "mitte"], "additionalProperties": false,
          "properties": {"bogen": {"$ref": "#/$defs/punkt2"}, "mitte": {"$ref": "#/$defs/punkt2"}}
        }
      ]
    },
```

`$defs.ende` vollständig ersetzen:

```json
    "ende": {
      "type": "object", "required": ["typ"], "additionalProperties": false,
      "properties": {
        "typ": {"enum": ["blind", "durch_alles", "mittig", "bis_flaeche", "versatz_von_flaeche"]},
        "tiefe": {"$ref": "#/$defs/wert"},
        "umkehren": {"type": "boolean"},
        "flaeche": {"$ref": "#/$defs/flaechenanker"},
        "abstand": {"$ref": "#/$defs/wert"}
      },
      "allOf": [
        {"if": {"properties": {"typ": {"enum": ["blind", "mittig"]}}}, "then": {"required": ["tiefe"]}},
        {"if": {"properties": {"typ": {"const": "bis_flaeche"}}}, "then": {"required": ["flaeche"]}},
        {"if": {"properties": {"typ": {"const": "versatz_von_flaeche"}}}, "then": {"required": ["flaeche", "abstand"]}}
      ]
    },
```

Nach `$defs.f_bohrung` einfügen:

```json
    "f_normbohrung": {
      "required": ["art", "groesse", "flaeche", "positionen"], "additionalProperties": false,
      "properties": {
        "id": true, "typ": true,
        "art": {"enum": ["gewinde", "zylinderschraube", "senkschraube", "stift"]},
        "groesse": {"oneOf": [
          {"type": "string", "pattern": "^M[0-9]+(x[0-9]+(\\.[0-9]+)?)?$"},
          {"type": "number", "exclusiveMinimum": 0}
        ]},
        "norm": {"enum": ["ISO"]},
        "flaeche": {"$ref": "#/$defs/flaechenanker"},
        "positionen": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/punkt2"}},
        "durch": {"const": true},
        "tiefe": {"$ref": "#/$defs/wert"},
        "gewindetiefe": {"$ref": "#/$defs/wert"}
      },
      "oneOf": [{"required": ["tiefe"]}, {"required": ["durch"]}]
    },
```

In `$defs.feature` das `typ`-Enum um `"normbohrung"` erweitern (nach `"bohrung"`) und in `allOf` nach der Zeile für `bohrung` einfügen:

```json
        {"if": {"properties": {"typ": {"const": "normbohrung"}}}, "then": {"$ref": "#/$defs/f_normbohrung"}},
```

- [ ] **Step 8: Validierung – `swki/spec/laden.py`**

Imports ergänzen (nach `from swki.spec.ausdruck import …`):

```python
import math

from swki.spec.konturen import eckradien, kontur_punkte
from swki.spec.normen import groesse_text, norm_von, normmasse, verfuegbare_groessen
```

(`import math` zu den Standard-Imports oben stellen.) `_POSITIV` ersetzen und Konstante ergänzen:

```python
_POSITIV = {"breite", "hoehe", "durchmesser", "radius", "tiefe", "abstand", "laenge", "gewindetiefe"}
_WINKEL = {"winkel"}
_TOL_KONTUR_MM = 1e-6
```

In `plausibel_befunde` die Winkelprüfung

```python
        if schluessel in _WINKEL and not 0 < wert <= 360:
            befunde.append({"pfad": _pfad(pfad), "meldung": f"winkel muss in (0, 360] liegen (ist {wert:g})"})
```

ersetzen durch

```python
        if schluessel in _WINKEL and "langloch" in pfad:
            if not 0 <= wert < 180:
                befunde.append({"pfad": _pfad(pfad), "meldung": f"langloch.winkel muss in [0, 180) liegen (ist {wert:g})"})
        elif schluessel in _WINKEL and not 0 < wert <= 360:
            befunde.append({"pfad": _pfad(pfad), "meldung": f"winkel muss in (0, 360] liegen (ist {wert:g})"})
```

In der Schleife `for i, f in enumerate(features):` (die mit den Mittellinien) am Ende des Schleifenkörpers, nach dem `skript`-Block, ergänzen:

```python
        for k, e in enumerate(elemente):
            befunde += _element_befunde(e, f"features[{i}].skizze.elemente[{k}]", parameter)
        if "ende" in f:
            befunde += _ende_befunde(f["ende"], f"features[{i}].ende")
        if f["typ"] == "normbohrung":
            befunde += _normbohrung_befunde(f, f"features[{i}]", parameter)
```

Vor `plausibel_befunde` die neuen Funktionen einfügen:

```python
def _abstand2(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _radien_befunde(polygon: dict, pfad: str, p: dict) -> list[dict]:
    pts = [(auswerten(u, p), auswerten(v, p)) for u, v in polygon["punkte"]]
    roh, n = polygon["radien"], len(pts)
    if isinstance(roh, list) and len(roh) != n:
        return [{"pfad": f"{pfad}.radien", "meldung": f"radien: {len(roh)} Werte für {n} Ecken"}]
    befunde = []
    for k, r in enumerate(eckradien(polygon, p)):
        stelle = f"{pfad}.radien[{k}]" if isinstance(roh, list) else f"{pfad}.radien"
        kante = min(_abstand2(pts[k], pts[k - 1]), _abstand2(pts[k], pts[(k + 1) % n]))
        if r < 0:
            befunde.append({"pfad": stelle, "meldung": f"Radius an Ecke {k + 1} muss ≥ 0 sein (ist {r:g})"})
        elif r > 0 and r >= kante / 2:
            befunde.append({"pfad": stelle, "meldung": f"Radius {r:g} an Ecke {k + 1} muss kleiner als die halbe "
                                                       f"kürzere Nachbarkante ({kante / 2:g}) sein"})
    return befunde


def _kontur_befunde(kontur: dict, pfad: str, p: dict) -> list[dict]:
    punkte = kontur_punkte(kontur, p)
    befunde = []
    for k, s in enumerate(kontur["segmente"]):
        if "bogen" not in s:
            continue
        mitte = (auswerten(s["mitte"][0], p), auswerten(s["mitte"][1], p))
        ra, rb = _abstand2(punkte[k], mitte), _abstand2(punkte[k + 1], mitte)
        if abs(ra - rb) > _TOL_KONTUR_MM:
            befunde.append({"pfad": f"{pfad}.segmente[{k}]",
                            "meldung": f"Bogen: Anfang und Ende ungleich weit vom Mittelpunkt ({ra:g} / {rb:g} mm)"})
        elif _abstand2(punkte[k], punkte[k + 1]) <= _TOL_KONTUR_MM:
            befunde.append({"pfad": f"{pfad}.segmente[{k}]",
                            "meldung": "Bogen: Anfang = Ende (Vollkreis als kreis angeben)"})
    if _abstand2(punkte[0], punkte[-1]) > _TOL_KONTUR_MM:
        befunde.append({"pfad": f"{pfad}.segmente", "meldung": "Kontur ist nicht geschlossen: letzter Endpunkt muss start sein"})
    return befunde


def _element_befunde(e: dict, pfad: str, p: dict) -> list[dict]:
    """Eckradien, Kontur (Spec 2c §4); Langloch-Maße prüft die allgemeine Positiv-/Winkelprüfung."""
    try:
        if "rechteck" in e and "radius" in e["rechteck"]:
            r = e["rechteck"]
            if auswerten(r["radius"], p) >= min(auswerten(r["breite"], p), auswerten(r["hoehe"], p)) / 2:
                return [{"pfad": f"{pfad}.rechteck.radius",
                         "meldung": "radius muss kleiner als die halbe kürzere Seite sein"}]
        if "polygon" in e and "radien" in e["polygon"]:
            return _radien_befunde(e["polygon"], f"{pfad}.polygon", p)
        if "kontur" in e:
            return _kontur_befunde(e["kontur"], f"{pfad}.kontur", p)
    except AusdruckFehler:
        pass  # bereits oben gemeldet
    return []


def _ende_befunde(ende: dict, pfad: str) -> list[dict]:
    typ, befunde = ende["typ"], []
    if "flaeche" in ende and typ not in ("bis_flaeche", "versatz_von_flaeche"):
        befunde.append({"pfad": f"{pfad}.flaeche",
                        "meldung": f"flaeche gilt nur bei bis_flaeche/versatz_von_flaeche (typ ist {typ})"})
    if "abstand" in ende and typ != "versatz_von_flaeche":
        befunde.append({"pfad": f"{pfad}.abstand", "meldung": f"abstand gilt nur bei versatz_von_flaeche (typ ist {typ})"})
    if "tiefe" in ende and typ in ("bis_flaeche", "versatz_von_flaeche"):
        befunde.append({"pfad": f"{pfad}.tiefe", "meldung": f"tiefe gilt nicht bei {typ} (die Tiefe folgt aus der Fläche)"})
    return befunde


def _normbohrung_befunde(f: dict, pfad: str, p: dict) -> list[dict]:
    befunde = []
    norm = norm_von(f)
    if normmasse(f["art"], f["groesse"], norm) is None:
        verfuegbar = ", ".join(verfuegbare_groessen(f["art"], norm)) or "keine"
        befunde.append({"pfad": f"{pfad}.groesse",
                        "meldung": f"Größe {groesse_text(f['groesse'])!r} für {f['art']} ({norm}) nicht in der "
                                   f"Maßtabelle swki/wissen/bohrungsnormen.yaml; verfügbar: {verfuegbar}"})
    if "gewindetiefe" in f and f["art"] != "gewinde":
        befunde.append({"pfad": f"{pfad}.gewindetiefe", "meldung": "gewindetiefe nur bei art: gewinde"})
    if f["art"] == "gewinde" and not f.get("durch") and "gewindetiefe" not in f:
        befunde.append({"pfad": pfad, "meldung": "gewindetiefe ist Pflicht bei einer Gewindebohrung mit tiefe"})
    if "gewindetiefe" in f and "tiefe" in f:
        try:
            if auswerten(f["gewindetiefe"], p) > auswerten(f["tiefe"], p):
                befunde.append({"pfad": f"{pfad}.gewindetiefe", "meldung": "gewindetiefe darf nicht größer als tiefe sein"})
        except AusdruckFehler:
            pass  # bereits oben gemeldet
    return befunde
```

- [ ] **Step 9: Konfiguration**

`config/standard.yaml` – nach `max_nachbesserungen: 3` einfügen:

```yaml
bohrungsnorm: ISO   # Vorgabe für normbohrung (je Bohrung mit "norm" überschreibbar; Tabelle swki/wissen/bohrungsnormen.yaml)
```

`pyproject.toml` – in `[tool.setuptools.package-data]`:

```toml
swki = ["wissen/*.md", "wissen/*.yaml"]
```

- [ ] **Step 10: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec tests/test_konfig.py -q`
Expected: alle grün.

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 241 passed, 28 deselected (206 + 7 Konturen + 10 Normen + 18 Laden).

Run: `.venv\Scripts\python.exe -m swki validieren tests\referenz\formplatte\formplatte_ds.yaml`
Expected: `"gueltig": true`, 10 Features (Bestand unverändert gültig).

- [ ] **Step 11: Commit**

```powershell
git add swki/spec/normen.py swki/spec/konturen.py swki/spec/laden.py schema/teil.schema.json config/standard.yaml pyproject.toml tests/spec/test_normen.py tests/spec/test_konturen.py tests/spec/test_laden.py tests/test_konfig.py
git commit -m "spec: normbohrung, runde Skizzenelemente, Endbedingungen bis/versatz Fläche" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 4: Analytisches Sollvolumen für Rundungen, Langloch, Kontur und Normbohrungen (ohne SolidWorks)

**Files:**
- Modify: `swki/pruefung/geometrie.py` (Imports, `_flaeche`, neue Hilfen, `volumen_auto`)
- Test: `tests/pruefung/test_geometrie.py` (13 neue Tests)

**Interfaces:**
- Consumes: `eckradien`, `kontur_punkte` (Task 3, `swki.spec.konturen`); `normmasse`, `norm_von`, `bohrspitze_grad` (Task 3, `swki.spec.normen`).
- Produces: `bohrspitze(d: float, winkel_grad: float = 118.0) -> float` (mm³); `normbohrung_volumen(art: str, masse: dict, tiefe: float | None, dicke: float | None = None, spitze_grad: float = 118.0) -> float` (mm³; `tiefe` = Bohrungstiefe ab Fläche bei blind, `dicke` = Materialdicke bei durch); `volumen_auto(spec)` kennt zusätzlich `rechteck.radius`, `polygon.radien` (konvexe und konkave Ecken), `langloch`, `kontur`, `normbohrung` mit `tiefe`; liefert `None` mit Grund für `normbohrung` durch (`"<id>: Normbohrung durch"`), Endbedingungen `bis_flaeche`/`versatz_von_flaeche` (`"<id>: ende <typ> …"`) und Rotationen mit neuen Elementen (`"<id>: Rotation mit Rundungen …"`). Task 8 und Task 11 nutzen `normbohrung_volumen` bzw. dieselbe Formel.

- [ ] **Step 1: Failing tests – an `tests/pruefung/test_geometrie.py` anhängen**

Import-Zeile oben ersetzen durch:

```python
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand, normbohrung_volumen, volumen_auto
from swki.spec.normen import normmasse
```

In der Parameterliste von `test_volumen_nicht_berechenbar` drei Fälle ergänzen:

```python
    ({"id": "f2", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"nahe": [0, 0, 0]},
      "positionen": [[0, 0]], "durch": True}, "f2: Normbohrung durch"),
    ({"id": "f2", "typ": "schnitt", "skizze": {"ebene": "oben", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 0.5}}]},
      "ende": {"typ": "versatz_von_flaeche", "flaeche": {"feature": "f1", "flaeche": "-y"}, "abstand": 0.2}},
     "f2: ende versatz_von_flaeche"),
    ({"id": "f2", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"langloch": {"mitte": [5, 0], "laenge": 2, "breite": 1}}, {"mittellinie": {"von": [0, -1], "bis": [0, 1]}}]}},
     "f2: Rotation mit Rundungen"),
```

Am Dateiende anhängen:

```python
def _platte(*elemente, tiefe=10, parameter=None):
    return {"parameter": parameter or {}, "features": [_extr("f1", "extrusion", list(elemente), tiefe)]}


def test_volumen_rechteck_mit_eckradius():
    rechteck = {"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60, "radius": "=R"}}
    assert volumen_auto(_platte(rechteck, parameter={"R": 6}))[0] == pytest.approx((6000 - (4 - math.pi) * 36) * 10)


def test_volumen_polygon_mit_radien_konvex():
    quadrat = {"polygon": {"punkte": [[0, 0], [40, 0], [40, 40], [0, 40]], "radien": 5}}
    assert volumen_auto(_platte(quadrat))[0] == pytest.approx((1600 - 4 * (25 - 25 * math.pi / 4)) * 10)


L_FORM = [[0, 0], [40, 0], [40, 20], [20, 20], [20, 40], [0, 40]]


@pytest.mark.parametrize("umlauf", [1, -1])
def test_volumen_polygon_mit_konkaver_ecke(umlauf):
    # 5 konvexe Ecken R3 nehmen Material weg, die konkave Ecke (20, 20) R5 fügt hinzu – unabhängig vom Umlaufsinn
    polygon = {"polygon": {"punkte": L_FORM[::umlauf], "radien": [3, 3, 3, 5, 3, 3][::umlauf]}}
    erwartet = (1200 - 5 * (9 - 9 * math.pi / 4) + (25 - 25 * math.pi / 4)) * 10
    assert volumen_auto(_platte(polygon))[0] == pytest.approx(erwartet)


def test_volumen_langloch():
    langloch = {"langloch": {"mitte": [10, 5], "laenge": 30, "breite": 8, "winkel": 30}}
    assert volumen_auto(_platte(langloch))[0] == pytest.approx((30 * 8 + math.pi * 16) * 10)


def test_volumen_kontur_mit_bogen():
    kontur = {"kontur": {"start": [0, 0], "segmente": [{"linie": [40, 0]}, {"bogen": [40, 30], "mitte": [40, 15]},
                                                       {"linie": [0, 30]}, {"linie": [0, 0]}]}}
    assert volumen_auto(_platte(kontur))[0] == pytest.approx((1200 + math.pi * 225 / 2) * 10)


def _mit_normbohrung(**nb):
    return {"features": [
        _extr("f1", "extrusion", [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}], 20),
        {"id": "f2", "typ": "normbohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, **nb},
    ]}


def test_volumen_gewinde_m8_wie_s9b():
    spec = _mit_normbohrung(art="gewinde", groesse="M8", positionen=[[-20, 0], [20, 0]], tiefe=16, gewindetiefe=12)
    volumen, grund = volumen_auto(spec)
    assert grund == "analytisch"
    assert volumen == pytest.approx(120000 - 2 * 605.80, abs=0.02)  # S9b Baustein 21: 605,80 mm³ je Loch


def test_volumen_stift_blind():
    d = normmasse("stift", 8)["durchmesser"]
    spec = _mit_normbohrung(art="stift", groesse=8, positionen=[[0, 0]], tiefe=10)
    spitze = math.pi * d**2 / 12 * (d / 2) / math.tan(math.radians(59))
    assert volumen_auto(spec)[0] == pytest.approx(120000 - (math.pi * d**2 / 4 * 10 + spitze))


@pytest.mark.parametrize(("art", "masse", "erwartet"), [
    ("zylinderschraube", {"durchgang": 9, "senkung_d": 15, "senkung_t": 9}, math.pi / 4 * (81 * 22 + (225 - 81) * 9)),
    ("senkschraube", {"durchgang": 6.6, "senkung_d": 12.4, "senkwinkel": 90},
     math.pi / 4 * 6.6**2 * (22 - 2.9) + math.pi * 2.9 / 12 * (12.4**2 + 12.4 * 6.6 + 6.6**2)),
])
def test_normbohrung_volumen_durch(art, masse, erwartet):
    assert normbohrung_volumen(art, masse, None, dicke=22) == pytest.approx(erwartet)
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung/test_geometrie.py -q`
Expected: FAIL (`ImportError: cannot import name 'normbohrung_volumen'`).

- [ ] **Step 3: Implementieren – `swki/pruefung/geometrie.py`**

Imports ergänzen:

```python
from swki.spec.konturen import eckradien, kontur_punkte
from swki.spec.normen import bohrspitze_grad, norm_von, normmasse
```

`_flaeche` vollständig ersetzen und die neuen Hilfen davor einfügen:

```python
def _punkte(roh, p: dict) -> list[tuple[float, float]]:
    return [(auswerten(x, p), auswerten(y, p)) for x, y in roh]


def _polygon_flaeche(pts) -> float:
    """Vorzeichenbehaftete Fläche (Gaußsche Trapezformel): > 0 gegen den Uhrzeigersinn."""
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2


def _eckkorrektur(a, b, c, r: float) -> float:
    """Flächenänderung durch Eckradius r an Ecke b (Nachbarn a, c) eines gegen den Uhrzeigersinn umlaufenden
    Polygons: an konvexen Ecken wird Material weggenommen, an konkaven hinzugefügt."""
    if r == 0:
        return 0.0
    v1, v2 = (a[0] - b[0], a[1] - b[1]), (c[0] - b[0], c[1] - b[1])
    phi = math.acos(max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2)))))
    betrag = r * r / math.tan(phi / 2) - r * r * (math.pi - phi) / 2  # Drachen aus Tangenten − Kreissektor
    links = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) > 0
    return -betrag if links else betrag


def _polygon_mit_radien(pts, radien) -> float:
    if _polygon_flaeche(pts) < 0:
        pts, radien = pts[::-1], radien[::-1]
    n = len(pts)
    return _polygon_flaeche(pts) + sum(_eckkorrektur(pts[k - 1], pts[k], pts[(k + 1) % n], radien[k]) for k in range(n))


def _kontur_flaeche(kontur: dict, p: dict) -> float:
    """Fläche einer geschlossenen Kontur (Greenscher Satz; Bögen gegen den Uhrzeigersinn)."""
    pts = kontur_punkte(kontur, p)
    summe = 0.0
    for k, s in enumerate(kontur["segmente"]):
        (xa, ya), (xb, yb) = pts[k], pts[k + 1]
        if "linie" in s:
            summe += (xa * yb - xb * ya) / 2
            continue
        mx, my = auswerten(s["mitte"][0], p), auswerten(s["mitte"][1], p)
        r = math.hypot(xa - mx, ya - my)
        winkel = (math.atan2(yb - my, xb - mx) - math.atan2(ya - my, xa - mx)) % (2 * math.pi)
        summe += (r * r * winkel + mx * (yb - ya) - my * (xb - xa)) / 2
    return abs(summe)


def _flaeche(element: dict, p: dict) -> float | None:
    if "rechteck" in element:
        r = element["rechteck"]
        return auswerten(r["breite"], p) * auswerten(r["hoehe"], p) - (4 - math.pi) * auswerten(r.get("radius", 0), p) ** 2
    if "kreis" in element:
        return math.pi * auswerten(element["kreis"]["durchmesser"], p) ** 2 / 4
    if "polygon" in element:
        return abs(_polygon_mit_radien(_punkte(element["polygon"]["punkte"], p), eckradien(element["polygon"], p)))
    if "langloch" in element:
        breite = auswerten(element["langloch"]["breite"], p)
        return auswerten(element["langloch"]["laenge"], p) * breite + math.pi * breite**2 / 4
    if "kontur" in element:
        return _kontur_flaeche(element["kontur"], p)
    return None


def _hat_rundung(element: dict) -> bool:
    return ("radius" in element.get("rechteck", {}) or "radien" in element.get("polygon", {})
            or "langloch" in element or "kontur" in element)


def bohrspitze(d: float, winkel_grad: float = 118.0) -> float:
    """Volumen (mm³) der kegeligen Bohrspitze eines Bohrers mit Durchmesser d und Spitzenwinkel."""
    return math.pi * d**2 / 12 * (d / 2) / math.tan(math.radians(winkel_grad) / 2)


def normbohrung_volumen(art: str, masse: dict, tiefe: float | None, dicke: float | None = None,
                        spitze_grad: float = 118.0) -> float:
    """Volumen (mm³) einer Normbohrung aus der Maßtabelle (Spec 2c §3.3, Tiefenbezug laut S10 Frage 3).

    tiefe: Bohrungstiefe ab der Ansatzfläche (zylindrischer Teil, darunter die Bohrspitze) – blind.
    dicke: Materialdicke bei durchgehender Bohrung (tiefe None). Gewinde sind kosmetisch → Kernloch.
    """
    d = masse.get("kernloch") or masse.get("durchgang") or masse["durchmesser"]
    volumen = math.pi * d**2 / 4 * (dicke if tiefe is None else tiefe)
    if tiefe is not None:
        volumen += bohrspitze(d, spitze_grad)
    if art == "zylinderschraube":
        volumen += math.pi * (masse["senkung_d"] ** 2 - d**2) / 4 * masse["senkung_t"]
    elif art == "senkschraube":
        ds = masse["senkung_d"]
        h = (ds - d) / 2 / math.tan(math.radians(masse["senkwinkel"]) / 2)
        volumen += math.pi * h / 12 * (ds**2 + ds * d + d**2) - math.pi * d**2 / 4 * h
    return volumen
```

In `volumen_auto` den Zweig `extrusion`/`schnitt`, den Zweig `rotation` und einen neuen Zweig `normbohrung` so fassen (übrige Zweige unverändert):

```python
        if typ in ("extrusion", "schnitt"):
            ende = f["ende"]
            if ende["typ"] == "durch_alles":
                return None, f"{f['id']}: durch_alles"
            if ende["typ"] in ("bis_flaeche", "versatz_von_flaeche"):
                return None, f"{f['id']}: ende {ende['typ']} (Tiefe hängt von der Geometrie ab)"
            flaechen = [_flaeche(e, p) for e in f["skizze"]["elemente"]]
            v = sum(flaechen) * auswerten(ende["tiefe"], p)
            beitrag[f["id"]] = -v if typ == "schnitt" else v
        elif typ == "rotation":
            if any(_hat_rundung(e) for e in f["skizze"]["elemente"]):
                return None, f"{f['id']}: Rotation mit Rundungen (Eckradius, Langloch, Kontur) nicht analytisch"
            v = _pappus(f, p)
            beitrag[f["id"]] = -v if f.get("schnitt") else v
        elif typ == "normbohrung":
            if f.get("durch"):
                return None, f"{f['id']}: Normbohrung durch"
            masse = normmasse(f["art"], f["groesse"], norm_von(f))
            v = normbohrung_volumen(f["art"], masse, auswerten(f["tiefe"], p), spitze_grad=bohrspitze_grad())
            beitrag[f["id"]] = -v * len(f["positionen"])
```

Den Docstring von `volumen_auto` um „Rundungen, Langloch, Kontur, Normbohrung mit Tiefe; bis_flaeche/versatz_von_flaeche und Normbohrung durch → nicht berechenbar“ ergänzen.

- [ ] **Step 4: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung/test_geometrie.py -v`
Expected: 20 passed.

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 254 passed, 28 deselected.

- [ ] **Step 5: Commit**

```powershell
git add swki/pruefung/geometrie.py tests/pruefung/test_geometrie.py
git commit -m "pruefung: Sollvolumen für Rundungen, Langloch, Kontur und Normbohrungen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 5: Hinweise `feste_zahl` und `zusammenfassen` (ohne SolidWorks)

**Files:**
- Modify: `swki/spec/hinweise.py` (vollständig ersetzen), `swki/spec/befehle.py`
- Test: `tests/spec/test_hinweise.py` (6 neue Tests), `tests/spec/test_befehle.py` (Zusicherung zu `art`)

**Interfaces:**
- Consumes: `lade_tabelle` (Task 3); `auswerten`, `AusdruckFehler`, `ist_ausdruck`.
- Produces: `feste_masse(spec) -> list[dict]` mit `{"art": "feste_zahl", "pfad", "meldung"}` (bisheriges Verhalten plus `art`); `zusammenfassen(spec) -> list[dict]` mit `{"art": "zusammenfassen", "pfad": "features[i], features[j]", "knoten": [ids], "meldung"}` nach den vier Regeln aus Spec §6.2; `hinweise(spec) -> list[dict]` = `feste_masse` + `zusammenfassen` (in dieser Reihenfolge). `swki validieren` gibt `hinweise(spec)` aus; Hinweise blockieren nie.

- [ ] **Step 1: Failing tests – `tests/spec/test_hinweise.py` Import ersetzen und Tests anhängen**

Import-Zeilen oben ersetzen durch:

```python
from swki.spec.hinweise import feste_masse, hinweise, zusammenfassen
from swki.spec.normen import normmasse

from .beispiel import GUELTIG
```

Anhängen:

```python
FLAECHE = {"feature": "f1", "flaeche": "+y"}


def _nb(fid, groesse="M8", **weiteres):
    return {"id": fid, "typ": "normbohrung", "art": "zylinderschraube", "groesse": groesse, "flaeche": FLAECHE,
            "positionen": [["=-L/2+20", 0]], "durch": True, **weiteres}


def _bohrung(fid, **weiteres):
    return {"id": fid, "typ": "bohrung", "flaeche": FLAECHE, "positionen": [[1, 1]], "durchmesser": "=D",
            "durch": True, **weiteres}


def test_feste_zahl_hat_art():
    assert {h["art"] for h in feste_masse(GUELTIG)} == {"feste_zahl"}


def test_gleiche_bohrungen_zusammenfassen():
    spec = {"features": [_nb("f2"), _nb("f3", positionen=[[10, 10]]), _nb("f4", groesse="M10"),
                         _bohrung("f5"), _bohrung("f6", positionen=[[5, 1]])]}
    ergebnis = zusammenfassen(spec)
    assert [h["knoten"] for h in ergebnis] == [["f2", "f3"], ["f5", "f6"]]
    assert ergebnis[0]["pfad"] == "features[0], features[1]"
    assert all(h["art"] == "zusammenfassen" and "Regel 2" in h["meldung"] for h in ergebnis)


def test_gleiche_kantenmasse_zusammenfassen():
    spec = {"features": [
        {"id": "f1", "typ": "fase", "kanten": [{"nahe": [0, 0, 0]}], "abstand": 1},
        {"id": "f2", "typ": "fase", "kanten": [{"nahe": [1, 0, 0]}], "abstand": 1},
        {"id": "f3", "typ": "fase", "kanten": [{"nahe": [2, 0, 0]}], "abstand": 2},
        {"id": "f4", "typ": "verrundung", "kanten": [{"nahe": [3, 0, 0]}], "radius": "=R"},
        {"id": "f5", "typ": "verrundung", "kanten": [{"nahe": [4, 0, 0]}], "radius": "=R"},
    ]}
    ergebnis = zusammenfassen(spec)
    assert [h["knoten"] for h in ergebnis] == [["f1", "f2"], ["f4", "f5"]]
    assert all("Regel 6" in h["meldung"] for h in ergebnis)


def test_muster_und_spiegeln_mit_festen_zahlen():
    klotz = {"id": "f2", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
        {"kreis": {"mitte": [0, 0], "durchmesser": 5}}]}, "ende": {"typ": "blind", "tiefe": 5}}
    spec = {"features": [
        _bohrung("f1"), klotz,
        {"id": "f3", "typ": "muster_linear", "features": ["f1"], "richtung1": {"achse": "x", "abstand": 20, "anzahl": 3}},
        {"id": "f4", "typ": "muster_linear", "features": ["f1"], "richtung1": {"achse": "x", "abstand": "=A", "anzahl": 3}},
        {"id": "f5", "typ": "muster_kreis", "features": ["f1"], "achse": "y", "anzahl": 4},
        {"id": "f6", "typ": "spiegeln", "features": ["f1"], "ebene": "vorne"},
        {"id": "f7", "typ": "spiegeln", "features": ["f2"], "ebene": "vorne"},
    ]}
    ergebnis = zusammenfassen(spec)
    assert [h["knoten"] for h in ergebnis] == [["f3"], ["f5"], ["f6"]]
    assert all("Regel 3" in h["meldung"] for h in ergebnis)


def test_senkung_wie_iso_4762():
    m8 = normmasse("zylinderschraube", "M8")
    spec = {"features": [_bohrung("f1", durchmesser=m8["durchgang"],
                                  senkung={"durchmesser": m8["senkung_d"], "tiefe": 5})]}
    [h] = zusammenfassen(spec)
    assert h["knoten"] == ["f1"] and "ISO 4762 M8" in h["meldung"] and "normbohrung" in h["meldung"]


def test_hinweise_erst_feste_zahlen_dann_zusammenfassen():
    alle = hinweise(GUELTIG)
    fest = feste_masse(GUELTIG)
    assert alle[: len(fest)] == fest
    assert [h["knoten"] for h in alle[len(fest):]] == [["f5"]]  # muster_linear mit festem Abstand 20
```

In `tests/spec/test_befehle.py`, `test_validieren_ok`, nach der letzten Zusicherung ergänzen:

```python
    assert daten["hinweise"][0]["art"] == "feste_zahl"
    assert any(h["art"] == "zusammenfassen" for h in daten["hinweise"])
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_hinweise.py tests/spec/test_befehle.py -q`
Expected: FAIL (`ImportError: cannot import name 'hinweise'`).

- [ ] **Step 3: `swki/spec/hinweise.py` vollständig ersetzen**

```python
"""Hinweise zu einer gültigen Spezifikation, die nicht verhindern, dass sie gebaut wird (Spec 2c §6.2).

art "feste_zahl": feste Zahlen in maßtragenden Feldern der Features deckt die Freigabe-Prüfsumme nicht ab (sie gehören
zum Bauweg). Anforderungsmaße sollen deshalb als Parameter geführt werden ("=Name"); validieren meldet die übrigen.
art "zusammenfassen": Knoten, die sich nach den Modellierregeln (Skill konstruieren) für einen kompakteren
Feature-Baum zusammenfassen lassen.
"""

import json

from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck
from swki.spec.normen import lade_tabelle

MASS_FELDER = frozenset({
    "tiefe", "durchmesser", "radius", "abstand", "winkel", "breite", "hoehe", "mitte", "punkte", "positionen", "von", "bis",
    "gewindetiefe", "laenge", "radien", "start", "linie", "bogen",
})
_ANKER = frozenset({"nahe", "kanten", "flaeche"})  # Anker wählen Geometrie aus, sie sind keine Maße
_TOL_NORM_MM = 0.01


def feste_masse(spec: dict) -> list[dict]:
    """Feste Zahlen ≠ 0 in maßtragenden Feldern der Features als [{"art", "pfad", "meldung"}] (0 = Lage auf Achse/Ebene)."""
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
                "art": "feste_zahl",
                "pfad": pfad,
                "meldung": f"feste Zahl {wert:g}: als Parameter führen, sonst deckt die Freigabe dieses Maß nicht ab",
            })

    for i, feature in enumerate(spec.get("features", [])):
        gehe(feature, f"features[{i}]", False)
    return hinweise


def _gruppen(features: list[dict], typen: tuple[str, ...], ohne: str) -> list[list[tuple[int, dict]]]:
    """Knoten gleichen Typs, die sich nur in id und dem Feld `ohne` unterscheiden (Reihenfolge des ersten Auftretens)."""
    gruppen: dict[str, list] = {}
    for i, f in enumerate(features):
        if f["typ"] in typen:
            schluessel = json.dumps({k: v for k, v in f.items() if k not in ("id", ohne)}, sort_keys=True, ensure_ascii=False)
            gruppen.setdefault(schluessel, []).append((i, f))
    return [g for g in gruppen.values() if len(g) > 1]


def _hinweis(eintraege: list[tuple[int, dict]], meldung: str) -> dict:
    return {"art": "zusammenfassen", "pfad": ", ".join(f"features[{i}]" for i, _ in eintraege),
            "knoten": [f["id"] for _, f in eintraege], "meldung": meldung}


def _iso_4762(f: dict, parameter: dict) -> str | None:
    """Größe, deren ISO-4762-Senkung (Durchgang und Senkungs-Ø laut Maßtabelle) die Bohrung mit Senkung trifft."""
    try:
        d, ds = auswerten(f["durchmesser"], parameter), auswerten(f["senkung"]["durchmesser"], parameter)
    except AusdruckFehler:
        return None
    for groesse, m in lade_tabelle()["normen"].get("ISO", {}).get("zylinderschraube", {}).items():
        if abs(d - m["durchgang"]) <= _TOL_NORM_MM and abs(ds - m["senkung_d"]) <= _TOL_NORM_MM:
            return groesse
    return None


def zusammenfassen(spec: dict) -> list[dict]:
    """Spec 2c §6.2: gleiche Bohrungen (Regel 2), gleiche Kantenmaße (Regel 6), Muster/Spiegeln mit festen Zahlen
    (Regel 3), Bohrung mit ISO-4762-Senkung (→ normbohrung, Regel 2)."""
    features = spec.get("features", [])
    parameter = spec.get("parameter", {})
    ergebnis = [_hinweis(g, "gleiche Bohrungen auf derselben Fläche: in einen Knoten mit mehreren positionen "
                            "zusammenfassen (Regel 2)")
                for g in _gruppen(features, ("bohrung", "normbohrung"), "positionen")]
    ergebnis += [_hinweis(g, "gleiches Maß: Kanten in einem Knoten zusammenfassen, am Ende des Baums (Regel 6)")
                 for g in _gruppen(features, ("fase", "verrundung"), "kanten")]
    typ_von = {f["id"]: f["typ"] for f in features}
    for i, f in enumerate(features):
        if f["typ"] == "muster_linear":
            fest = all(not ist_ausdruck(f[r]["abstand"]) for r in ("richtung1", "richtung2") if r in f)
        elif f["typ"] == "muster_kreis":
            fest = not ist_ausdruck(f.get("winkel", 360))
        elif f["typ"] == "spiegeln":
            fest = all(typ_von.get(q) in ("bohrung", "normbohrung") for q in f["features"])
        else:
            continue
        if fest:
            ergebnis.append(_hinweis([(i, f)], f"{f['typ']} mit festen Zahlen: Positionen direkt angeben, außer Anzahl, "
                                               "Abstand oder Symmetrie sind Anforderungen – dann als Parameter (Regel 3)"))
    for i, f in enumerate(features):
        if f["typ"] == "bohrung" and "senkung" in f and (groesse := _iso_4762(f, parameter)):
            ergebnis.append(_hinweis([(i, f)], f"Bohrung mit Senkung entspricht ISO 4762 {groesse}: als normbohrung "
                                               f"(art: zylinderschraube, groesse: {groesse}) führen (Regel 2)"))
    return ergebnis


def hinweise(spec: dict) -> list[dict]:
    """Alle Hinweise für swki validieren: erst feste Zahlen, dann Zusammenfassbares. Hinweise blockieren nie."""
    return feste_masse(spec) + zusammenfassen(spec)
```

- [ ] **Step 4: `swki/spec/befehle.py` umstellen**

Import `from swki.spec.hinweise import feste_masse` ersetzen durch `from swki.spec.hinweise import hinweise`; in `_validieren` die Zeile `"hinweise": feste_masse(spec),` ersetzen durch `"hinweise": hinweise(spec),`.

- [ ] **Step 5: Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec -q`
Expected: alle grün (test_hinweise.py: 9 passed).

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 260 passed, 28 deselected.

Run: `.venv\Scripts\python.exe -m swki validieren tests\referenz\formplatte\formplatte_ds.yaml`
Expected: `"gueltig": true`; unter `hinweise` zuerst `feste_zahl`-Einträge, dann `zusammenfassen` für `f8` (muster_linear, fester Abstand 40) und – falls die Tabelle für ISO 4762 M6 Durchgang 6,6 und Senkung 11 hat – für `f7`. Kein Hinweis für `f9` (spiegelt auch das Muster `f8`, nicht nur Bohrungen). Die Formplatte bleibt unverändert – Hinweise blockieren nicht.

- [ ] **Step 6: Commit**

```powershell
git add swki/spec/hinweise.py swki/spec/befehle.py tests/spec/test_hinweise.py tests/spec/test_befehle.py
git commit -m "spec: hinweise mit art feste_zahl und zusammenfassen (Modellierregeln)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 6: Skizzenelemente Eckradius, Langloch, Kontur (live)

**Files:**
- Modify: `swki/compiler/skizze.py` (Imports/Konstanten, `Skizzierer.__init__`, `Skizzierer.lage`, neue Methoden, `Skizzierer.element`)
- Test: `tests/live/test_live_konturen.py` (neu, 8 Live-Tests)

**Interfaces:**
- Consumes: Befunde S10 Frage 5 (Task 2); `bogenende_koordinate`, `kontur_punkte_roh` (Task 3); bestehend `Skizzierer.groesse|_merke|_punkt|_text|zu_skizze`, `sw.waehle|auswahl_leeren`, `ctx.verknuepfe` (über `skizziere`).
- Produces: `Skizzierer.gleichsinnig: bool`; `Skizzierer.lage(roh_uv, text_uv, nur: int | None = None)`; `Skizzierer.verrunde(linien: list, ecke_uv: tuple[float, float], roh_radius) -> None`; `Skizzierer._verschmelze(x: float, y: float) -> None`; `Skizzierer._langloch(l: dict)`, `Skizzierer._richtung_zu_u(linie, mitte_uv, roh_winkel)`, `Skizzierer._kontur(k: dict)`; `element()` kennt `rechteck.radius`, `polygon.radien`, `langloch`, `kontur`. Alle Maße bleiben per Gleichung an Parameter gebunden (wie bisher über `skizziere`), die Skizze ist voll bestimmt oder `skizziere` wirft `SKIZZE_NICHT_BESTIMMT`.

- [ ] **Step 1: Live-Test schreiben – `tests/live/test_live_konturen.py`**

```python
"""Live: runde Konturen in Skizzen – Eckradius, konkave Ecke, Langloch, Kontur mit Bögen (SolidWorks muss laufen)."""

import math

import pythoncom
import pytest

from swki.compiler import sw

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
KONTUR = {"start": [-40, 25], "segmente": [
    {"linie": [40, 25]}, {"bogen": [40, 45], "mitte": [40, 35]},
    {"linie": [-40, 45]}, {"bogen": [-40, 25], "mitte": [-40, 35]},
]}


def _platte(element, ebene="oben", parameter=None):
    return {"art": "teil", "name": "T", "parameter": parameter or {}, "features": [{
        "id": "f1", "typ": "extrusion", "skizze": {"ebene": ebene, "elemente": [element]},
        "ende": {"typ": "blind", "tiefe": 10},
    }]}


def _gleichungen(model) -> list[str]:
    g = model.GetEquationMgr
    return [g.Equation(i) for i in range(g.GetCount)]


def _setze(model, alt: str, neu: str) -> None:
    """Gleichung ersetzen (Property-Put nur per Invoke, S9a), auswerten, neu aufbauen."""
    g = model.GetEquationMgr
    dispid = g._oleobj_.GetIDsOfNames("Equation")
    g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, _gleichungen(model).index(alt), neu)
    g.EvaluateAll
    sw.rebuild(model)


def test_rechteck_mit_eckradius_haengt_an_parametern():
    spec = _platte({"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60, "radius": "=R"}},
                   parameter={"L": 100, "R": 6})
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert sw.teilebox_mm(ctx.model) == pytest.approx([-50, 0, -30, 50, 10, 30], abs=1e-6)
        assert volumen_mm3(ctx.model) == pytest.approx((6000 - (4 - math.pi) * 36) * 10, abs=1e-3)
        assert sum(1 for t in _gleichungen(ctx.model) if t.endswith('= "R"')) == 4  # je Ecke ein Radiusmaß
        _setze(ctx.model, '"R" = 6', '"R" = 8')
        _setze(ctx.model, '"L" = 100', '"L" = 120')
        assert sw.teilebox_mm(ctx.model)[0:4:3] == pytest.approx([-60, 60], abs=1e-6)
        assert volumen_mm3(ctx.model) == pytest.approx((7200 - (4 - math.pi) * 64) * 10, abs=1e-3)


def test_polygon_mit_konvexen_und_konkaver_ecke():
    punkte = [[0, 0], [40, 0], [40, 20], [20, 20], [20, 40], [0, 40]]
    spec = _platte({"polygon": {"punkte": punkte, "radien": [3, 3, 3, 5, 3, 3]}}, ebene="vorne")
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        erwartet = (1200 - 5 * (9 - 9 * math.pi / 4) + (25 - 25 * math.pi / 4)) * 10
        assert volumen_mm3(ctx.model) == pytest.approx(erwartet, abs=1e-3)
        assert sw.teilebox_mm(ctx.model) == pytest.approx([0, 0, 0, 40, 40, 10], abs=1e-6)


@pytest.mark.parametrize(("winkel", "box"), [
    (0, [-9, 0, -9, 29, 10, -1]),     # oben: X = u, Z = −v
    (90, [6, 0, -24, 14, 10, 14]),
    (30, None),
])
def test_langloch(winkel, box):
    spec = _platte({"langloch": {"mitte": [10, 5], "laenge": 30, "breite": 8, "winkel": winkel}})
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx((30 * 8 + 16 * math.pi) * 10, abs=1e-3)
        ist = sw.teilebox_mm(ctx.model)
        if box is not None:
            assert ist == pytest.approx(box, abs=1e-6)
        else:  # schräg: Mitte bleibt (X 10, Z −5), Ausdehnung in X = 30·cos 30° + 8
            assert ((ist[0] + ist[3]) / 2, (ist[2] + ist[5]) / 2) == pytest.approx((10, -5), abs=1e-6)
            assert ist[3] - ist[0] == pytest.approx(30 * math.cos(math.radians(30)) + 8, abs=1e-6)


@pytest.mark.parametrize(("ebene", "box"), [
    ("oben", [-50, 0, -45, 50, 10, -25]),     # X = u, Z = −v
    ("vorne", [-50, 25, 0, 50, 45, 10]),      # X = u, Y = v
    ("rechts", [0, 25, -50, 10, 45, 50]),     # Z = −u, Y = v
])
def test_kontur_mit_boegen(ebene, box):
    with gebautes_teil(_platte({"kontur": KONTUR}, ebene=ebene)) as (ctx, fehler, _):
        assert fehler is None
        # Bögen gegen den Uhrzeigersinn in (u, v) wölben sich nach außen: Fläche 80·20 + π·10²
        assert volumen_mm3(ctx.model) == pytest.approx((1600 + 100 * math.pi) * 10, abs=1e-3)
        assert sw.teilebox_mm(ctx.model) == pytest.approx(box, abs=1e-6)
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_konturen.py`
Expected: 8× `FEHLER` (Rundungen fehlen: Volumen/Box falsch bzw. `KeyError` für `langloch`/`kontur` im Element-Zweig `mittellinie`).

- [ ] **Step 3: API-Aufrufe nachschlagen**

`swki api methode` für `ISketchManager.CreateFillet`, `ISketchManager.CreateSketchSlot`, `ISketchManager.CreateArc`, `ISketchManager.CreateCenterLine`, `ISketch.GetSketchSegments`, `ISketchSegment.ConstructionGeometry`, `ISketchSegment.GetType`, `IModelDoc2.SketchAddConstraints`, `IModelDoc2.AddDimension2` (Werte wie in Task 2 Step 1). Dazu die Entscheidungen aus `docs/stufe0/ergebnisse.md` → „Entscheidung“ (Task 2) lesen und die mit `Abhängig von S10 Frage 5` markierten Stellen unten danach setzen.

- [ ] **Step 4: Implementieren – `swki/compiler/skizze.py`**

Imports und Konstanten oben ergänzen (bestehende bleiben):

```python
import math

from swki.spec.konturen import bogenende_koordinate, kontur_punkte_roh

SW_ECKE_BEHALTEN = 1  # swConstrainedCornerAction_e.swConstrainedCornerKeepGeometry – Abhängig von S10 Frage 5
SW_NUT_MITTELPUNKT = 1  # swSketchSlotCreationType_e.swSketchSlotCreationType_center_line – Abhängig von S10 Frage 5
SW_NUT_MITTE_MITTE = 0  # swSketchSlotLengthType_e.swSketchSlotLengthType_CenterCenter
SW_SKIZZE_LINIE = 0  # swSketchSegments_e.swSketchLINE
SW_GEGEN_UHRZEIGERSINN = 1  # CreateArc/CreateSketchSlot Direction: +1 = gegen den Uhrzeigersinn (Skizzensystem)
```

(`import math` zu `from dataclasses import dataclass` stellen, den `swki.spec.konturen`-Import zu den übrigen `swki`-Imports.)

In `Skizzierer.__init__` nach der Zeile `self.y_von = …` ergänzen:

```python
        # Drehsinn: die Abbildung (u, v) → Skizze erhält ihn, wenn ihre Determinante positiv ist (Bögen, S10 Frage 5)
        self.gleichsinnig = (xu - x0) * (yv - y0) - (xv - x0) * (yu - y0) > 0
```

`Skizzierer.lage` vollständig ersetzen:

```python
    def lage(self, roh_uv, text_uv: tuple[float, float], nur: int | None = None) -> None:
        """Kennpunkt (u, v) zum Ursprung festlegen: je Richtung Maß, bei 0 Ausrichtung, bei (0, 0) deckungsgleich.

        nur = 0 bzw. 1: nur die u- bzw. v-Lage (Endpunkt eines Bogens, dessen Radius schon feststeht; S10 Frage 5).
        """
        uv = (self.ctx.wert(roh_uv[0]), self.ctx.wert(roh_uv[1]))
        x, y = self.zu_skizze(*uv)
        punkt = self._punkt(x, y)

        def auswahl():
            sw.auswahl_leeren(self.model)
            sw.waehle(self.model, punkt, 0)
            sw.waehle(self.model, self.ursprung, 0, anhaengen=True)

        if nur is None and abs(x) < 1e-9 and abs(y) < 1e-9:
            auswahl()
            self.model.SketchAddConstraints("sgCOINCIDENT")
            sw.auswahl_leeren(self.model)
            return
        for wert, (index, richtung), waagrecht in ((x, self.x_von, True), (y, self.y_von, False)):
            if nur is not None and index != nur:
                continue
            auswahl()
            if abs(wert) < 1e-9:
                self.model.SketchAddConstraints("sgVERTICALPOINTS2D" if waagrecht else "sgHORIZONTALPOINTS2D")
                continue
            text = self._text(*text_uv)
            anzeige = self.model.AddHorizontalDimension2(*text) if waagrecht else self.model.AddVerticalDimension2(*text)
            roh = roh_uv[index] if self.lage_bindbar else wert
            self._merke(anzeige, roh, _vorzeichen(wert) * richtung)
        sw.auswahl_leeren(self.model)
```

Nach `lage` die neuen Methoden einfügen:

```python
    def _verschmelze(self, x: float, y: float) -> None:
        """Mehrere Skizzenpunkte an derselben Stelle zu einem machen (sgMERGEPOINTS) – Abhängig von S10 Frage 5."""
        gleich = [p for p in self.skizze.GetSketchPoints2 or () if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8]
        for p in gleich[1:]:
            sw.auswahl_leeren(self.model)
            sw.waehle(self.model, gleich[0], 0)
            sw.waehle(self.model, p, 0, anhaengen=True)
            self.model.SketchAddConstraints("sgMERGEPOINTS")
        sw.auswahl_leeren(self.model)

    @staticmethod
    def _linien_an(linien: list, x: float, y: float) -> list:
        """Die Linien, die im Skizzenpunkt (x, y) beginnen oder enden."""
        return [s for s in linien for p in (s.GetStartPoint2, s.GetEndPoint2)
                if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8]

    def verrunde(self, linien: list, ecke_uv: tuple[float, float], roh_radius) -> None:
        """Ecke (u, v) mit Skizzenverrundung runden und den Radius bemaßen. Die beiden Linien der Ecke werden gewählt;
        Maße der Ecke bleiben am virtuellen Schnittpunkt (swConstrainedCornerKeepGeometry) – Abhängig von S10 Frage 5."""
        if self.ctx.wert(roh_radius) == 0:
            return
        x, y = self.zu_skizze(*ecke_uv)
        paar = self._linien_an(linien, x, y)
        if len(paar) != 2:
            raise BauFehler(SKIZZE_UNGUELTIG, f"Ecke {ecke_uv}: {len(paar)} statt 2 Linien", schritt="skizze")
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, paar[0], 0)
        sw.waehle(self.model, paar[1], 0, anhaengen=True)
        bogen = self.sm.CreateFillet(mm(self.ctx.wert(roh_radius)), SW_ECKE_BEHALTEN)
        sw.auswahl_leeren(self.model)
        if bogen is None:
            raise BauFehler(SKIZZE_UNGUELTIG, f"CreateFillet an Ecke {ecke_uv} fehlgeschlagen", schritt="skizze")
        self.groesse(bogen, (ecke_uv[0] + _MASS_ABSTAND_MM, ecke_uv[1] + _MASS_ABSTAND_MM), roh_radius)

    def _richtung_zu_u(self, linie, mitte_uv: tuple[float, float], roh_winkel) -> None:
        """Richtung einer Linie zur u-Achse: 0°/90° über Beziehungen, sonst Winkelmaß zu einer u-parallelen
        Hilfslinie durch mitte_uv – Abhängig von S10 Frage 5."""
        winkel = self.ctx.wert(roh_winkel) % 180
        u_ist_x = self.x_von[0] == 0
        sw.auswahl_leeren(self.model)
        if abs(winkel) < 1e-9 or abs(winkel - 90) < 1e-9:
            parallel_u = abs(winkel) < 1e-9
            sw.waehle(self.model, linie, 0)
            self.model.SketchAddConstraints("sgHORIZONTAL2D" if parallel_u == u_ist_x else "sgVERTICAL2D")
            sw.auswahl_leeren(self.model)
            return
        mu_, mv = mitte_uv
        xa, ya = self.zu_skizze(mu_, mv)
        xb, yb = self.zu_skizze(mu_ + 2 * _MASS_ABSTAND_MM, mv)
        hilfe = self.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0)
        if hilfe is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "Hilfslinie für den Langlochwinkel nicht erzeugt", schritt="skizze")
        self._verschmelze(xa, ya)
        sw.waehle(self.model, hilfe, 0)
        self.model.SketchAddConstraints("sgHORIZONTAL2D" if u_ist_x else "sgVERTICAL2D")
        sw.auswahl_leeren(self.model)
        self.groesse(hilfe, (mu_ + _MASS_ABSTAND_MM, mv - _MASS_ABSTAND_MM), 2 * _MASS_ABSTAND_MM)
        sw.waehle(self.model, linie, 0)
        sw.waehle(self.model, hilfe, 0, anhaengen=True)
        halb = math.radians(winkel) / 2
        text = (mu_ + 3 * _MASS_ABSTAND_MM * math.cos(halb), mv + 3 * _MASS_ABSTAND_MM * math.sin(halb))
        self._merke(self.model.AddDimension2(*self._text(*text)), roh_winkel)
        sw.auswahl_leeren(self.model)

    def _langloch(self, l: dict) -> None:
        """Langloch (CreateSketchSlot, Mittelpunkt-Typ, Länge Mitte–Mitte): Breite = Abstand der geraden Seiten,
        Länge = Mittellinie, Richtung zu u, Lage der Mitte – Abhängig von S10 Frage 5."""
        w = self.ctx.wert
        mu_, mv = w(l["mitte"][0]), w(l["mitte"][1])
        laenge, breite = w(l["laenge"]), w(l["breite"])
        winkel = math.radians(w(l.get("winkel", 0)))
        xm, ym = self.zu_skizze(mu_, mv)
        xe, ye = self.zu_skizze(mu_ + laenge / 2 * math.cos(winkel), mv + laenge / 2 * math.sin(winkel))
        vorher = len(self.skizze.GetSketchSegments or ())
        nut = self.sm.CreateSketchSlot(SW_NUT_MITTELPUNKT, SW_NUT_MITTE_MITTE, mm(breite), xm, ym, 0.0, xe, ye, 0.0,
                                       0.0, 0.0, 0.0, SW_GEGEN_UHRZEIGERSINN, False)
        if nut is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "CreateSketchSlot fehlgeschlagen", schritt="skizze")
        neu = list(self.skizze.GetSketchSegments or ())[vorher:]
        seiten = [s for s in neu if s.GetType == SW_SKIZZE_LINIE and not s.ConstructionGeometry]
        achsen = [s for s in neu if s.GetType == SW_SKIZZE_LINIE and s.ConstructionGeometry]
        if len(seiten) != 2 or len(achsen) != 1:
            raise BauFehler(SKIZZE_UNGUELTIG, f"Langloch: {len(seiten)} Seiten, {len(achsen)} Mittellinien",
                            schritt="skizze")
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, seiten[0], 0)
        sw.waehle(self.model, seiten[1], 0, anhaengen=True)
        self._merke(self.model.AddDimension2(*self._text(mu_, mv + breite / 2 + _MASS_ABSTAND_MM)), l["breite"])
        sw.auswahl_leeren(self.model)
        self.groesse(achsen[0], (mu_, mv - breite / 2 - _MASS_ABSTAND_MM), l["laenge"])
        self._richtung_zu_u(achsen[0], (mu_, mv), l.get("winkel", 0))
        self.lage(l["mitte"], (mu_ - laenge / 2 - _MASS_ABSTAND_MM, mv - _MASS_ABSTAND_MM))

    def _kontur(self, k: dict) -> None:
        """Geschlossener Linienzug aus Linien und Bögen (Bögen gegen den Uhrzeigersinn in (u, v)). Bestimmung:
        Eckpunkte und Bogenmittelpunkte zum Ursprung; der Endpunkt eines Bogens nur in einer Koordinate
        (bogenende_koordinate), die andere folgt aus dem Radius – Abhängig von S10 Frage 5."""
        w = self.ctx.wert
        roh = kontur_punkte_roh(k)
        uv = [(w(p[0]), w(p[1])) for p in roh]
        richtung = SW_GEGEN_UHRZEIGERSINN if self.gleichsinnig else -SW_GEGEN_UHRZEIGERSINN
        for i, s in enumerate(k["segmente"]):
            (xa, ya), (xb, yb) = self.zu_skizze(*uv[i]), self.zu_skizze(*uv[i + 1])
            if "linie" in s:
                seg = self.sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)
            else:
                xm, ym = self.zu_skizze(w(s["mitte"][0]), w(s["mitte"][1]))
                seg = self.sm.CreateArc(xm, ym, 0.0, xa, ya, 0.0, xb, yb, 0.0, richtung)
            if seg is None:
                raise BauFehler(SKIZZE_UNGUELTIG, f"Kontur: Segment {i + 1} nicht erzeugt", schritt="skizze")
        for x, y in {self.zu_skizze(*q) for q in uv}:
            self._verschmelze(x, y)
        bemasst: set[tuple[float, float]] = set()

        def festlegen(p_roh, nur: int | None = None) -> None:
            q = (w(p_roh[0]), w(p_roh[1]))
            schluessel = (round(q[0], 6), round(q[1], 6))
            if schluessel in bemasst:
                return
            bemasst.add(schluessel)
            self.lage(p_roh, (q[0] + _MASS_ABSTAND_MM, q[1] + _MASS_ABSTAND_MM), nur)

        for i, s in enumerate(k["segmente"]):
            if "bogen" in s:
                festlegen(s["mitte"])
                mitte = (w(s["mitte"][0]), w(s["mitte"][1]))
                festlegen(roh[i + 1], bogenende_koordinate(uv[i + 1], mitte))
            else:
                festlegen(roh[i + 1])
```

`Skizzierer.element` vollständig ersetzen:

```python
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
            if "radius" in r:
                for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    self.verrunde(list(seg), (mu_ + du * b / 2, mv + dv * h / 2), r["radius"])
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
            p = element["polygon"]
            uv = [(w(q[0]), w(q[1])) for q in p["punkte"]]
            punkte = [self.zu_skizze(*q) for q in uv]
            linien = []
            for (xa, ya), (xb, yb) in zip(punkte, punkte[1:] + punkte[:1]):
                linie = self.sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)
                if linie is None:
                    raise BauFehler(SKIZZE_UNGUELTIG, "CreateLine fehlgeschlagen", schritt="skizze")
                linien.append(linie)
            for q in p["punkte"]:
                self.lage(q, (w(q[0]) + _MASS_ABSTAND_MM, w(q[1]) + _MASS_ABSTAND_MM))
            if "radien" in p:
                je_ecke = p["radien"] if isinstance(p["radien"], list) else [p["radien"]] * len(uv)
                for ecke, radius in zip(uv, je_ecke):
                    self.verrunde(linien, ecke, radius)
        elif "langloch" in element:
            self._langloch(element["langloch"])
        elif "kontur" in element:
            self._kontur(element["kontur"])
        else:
            m = element["mittellinie"]
            xa, ya = self.zu_skizze(w(m["von"][0]), w(m["von"][1]))
            xb, yb = self.zu_skizze(w(m["bis"][0]), w(m["bis"][1]))
            if self.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0) is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCenterLine fehlgeschlagen", schritt="skizze")
            for q in (m["von"], m["bis"]):
                self.lage(q, (w(q[0]) - _MASS_ABSTAND_MM, w(q[1]) + _MASS_ABSTAND_MM))
```

Weicht ein Spike-Befund ab, nur die markierten Stellen anpassen und den JSON-Schlüssel als Beleg im Bericht nennen. Bekannte Alternativen:
1. CreateFillet braucht den Eckpunkt statt der Linien (`a_rechteck_punkt` gelingt, `a_rechteck_linien` nicht): in `verrunde` die beiden `sw.waehle`-Zeilen ersetzen durch `sw.waehle(self.model, self._punkt(x, y), 0)` (`paar`-Prüfung entfällt).
2. CreateFillet legt selbst ein Radiusmaß oder eine Gleichheitsbeziehung an (`status_nach_fillet` = 3): anhalten und melden (Entscheidungsregel) – wie das automatisch angelegte Maß an den Parameter gebunden wird, muss erst nachgeschlagen und im Spike belegt werden.
3. Die Mittellinie des Langlochs misst die halbe Länge (`c_langloch_mittelpunkt_0.masse`: 15 statt 30): in `_langloch` vor `self.groesse(achsen[0], …)` `halbe = l["laenge"] / 2 if not ist_ausdruck(l["laenge"]) else f"=({l['laenge'][1:]}) / 2"` setzen und `halbe` statt `l["laenge"]` übergeben.
4. Bögen teilen die Endpunkte schon (`punkte_vor_verschmelzen` = 6): nichts ändern, `_verschmelze` findet dann keine doppelten Punkte.

- [ ] **Step 5: API-Prüfung und Unit-Tests**

Run: `.venv\Scripts\python.exe -m swki api pruefe-code`
Expected: `"befunde": []`.

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 260 passed, 28 deselected.

- [ ] **Step 6: Live-Tests**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_konturen.py`
Expected: 8× `OK`.

Run (Bestand, Skizzierer geändert): `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_extrusion.py tests\live\test_live_rotation_bohrung.py tests\live\test_live_parametrik.py tests\live\test_live_skript.py tests\referenz`
Expected: alle `OK` (Buchse und Formplatte bestehen unverändert).

Toggle 10 und Integer-Einstellung 6 prüfen: unverändert.

- [ ] **Step 7: Commit**

```powershell
git add swki/compiler/skizze.py tests/live/test_live_konturen.py
git commit -m "compiler: Eckradius, Langloch und Kontur mit Bögen in Skizzen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 7: Endbedingungen `bis_flaeche` und `versatz_von_flaeche` (live)

**Files:**
- Modify: `swki/compiler/handler/extrusion.py` (vollständig ersetzen)
- Test: `tests/live/test_live_endbedingungen.py` (neu, 3 Live-Tests)

**Interfaces:**
- Consumes: Befunde S10 Frage 6 (Task 2); `loese_flaeche(ctx, anker) -> Flaeche` (`.objekt` = IFace2); `sw.waehle`; `ctx.verknuepfe`.
- Produces: `ENDE` mit `bis_flaeche: 4`, `versatz_von_flaeche: 5`; `MARKE_ZIELFLAECHE`, `VERSATZ_WEG_VON_SKIZZE`, `VERSATZ_MASS`; `aufsatz(model, typ, tiefe_m, umkehren)` und `schnitt(model, typ, tiefe_m, umkehren)` mit **unveränderter Signatur** (der Handler `bohrung` importiert `ENDE` und `schnitt`). Versatzmaß per Gleichung an `abstand` gebunden.

- [ ] **Step 1: Live-Test schreiben – `tests/live/test_live_endbedingungen.py`**

```python
"""Live: Endbedingungen bis_flaeche und versatz_von_flaeche (SolidWorks muss laufen)."""

import math

import pythoncom
import pytest

from swki.compiler import sw
from swki.compiler.anker import flaeche_in_richtung
from swki.compiler.topologie import flaechen

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
VOLL = 100 * 60 * 20
KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
DECKFLAECHE = {"feature": "f1", "flaeche": "+y"}
UNTERSEITE = {"feature": "f1", "flaeche": "-y"}


def _spec(*features, parameter=None):
    return {"art": "teil", "name": "T", "parameter": parameter or {}, "features": [KLOTZ, *features]}


def test_tasche_mit_restwandstaerke():
    tasche = {"id": "f2", "typ": "schnitt",
              "skizze": {"ebene": DECKFLAECHE, "elemente": [{"rechteck": {"mitte": [0, 0], "breite": 20, "hoehe": 20}}]},
              "ende": {"typ": "versatz_von_flaeche", "flaeche": UNTERSEITE, "abstand": "=RW"}}
    with gebautes_teil(_spec(tasche, parameter={"RW": 5})) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 400 * 15, abs=1e-3)
        boden = flaeche_in_richtung(flaechen(ctx.ergebnis("f2").features[0]), "+y")
        assert boden.punkt[1] == pytest.approx(5, abs=1e-6)
        g = ctx.model.GetEquationMgr
        texte = [g.Equation(i) for i in range(g.GetCount)]
        assert '"D1@f2" = "RW"' in texte
        dispid = g._oleobj_.GetIDsOfNames("Equation")
        g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, texte.index('"RW" = 5'), '"RW" = 8')
        g.EvaluateAll
        sw.rebuild(ctx.model)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 400 * 12, abs=1e-3)


def test_durchbruch_bis_flaeche():
    durchbruch = {"id": "f2", "typ": "schnitt",
                  "skizze": {"ebene": DECKFLAECHE, "elemente": [{"kreis": {"mitte": [10, 5], "durchmesser": 10}}]},
                  "ende": {"typ": "bis_flaeche", "flaeche": UNTERSEITE}}
    with gebautes_teil(_spec(durchbruch)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - math.pi * 25 * 20, abs=1e-3)


def test_aufsatz_bis_flaeche():
    zapfen = {"id": "f2", "typ": "extrusion",
              "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": 40}},
                         "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 10}}]},
              "ende": {"typ": "bis_flaeche", "flaeche": DECKFLAECHE, "umkehren": True}}
    with gebautes_teil(_spec(zapfen)) as (ctx, fehler, _):
        assert fehler is None
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL + math.pi * 25 * 20, abs=1e-3)
        assert sw.teilebox_mm(ctx.model)[4] == pytest.approx(40, abs=1e-6)
```

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_endbedingungen.py`
Expected: 3× `FEHLER` (`KeyError: 'bis_flaeche'` / `'versatz_von_flaeche'` in `ENDE`).

- [ ] **Step 3: Implementieren – `swki/compiler/handler/extrusion.py` vollständig ersetzen**

```python
"""Handler "extrusion" (Aufsatz) und "schnitt" (verifiziert in Spike S9a, Bausteine 6 und 7; Endbedingungen
bis_flaeche und versatz_von_flaeche in Spike S10, Frage 6).

Aufsatz wächst standardmäßig in Richtung der Skizzennormale, Schnitt standardmäßig dagegen
(von einer Deckfläche also ins Material). "umkehren" dreht die Richtung (3. Parameter Dir, nicht Flip).
Die Zielfläche von bis_flaeche/versatz_von_flaeche wird über den Flächenanker aufgelöst und mit Marke 1 zur Skizze
gewählt; der Versatz geht zur Skizze hin (z. B. Restwandstärke über der Zielfläche).
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import richtung, skizziere
from swki.compiler.topologie import loese_flaeche

ENDE = {"blind": 0, "durch_alles": 1, "bis_flaeche": 4, "versatz_von_flaeche": 5, "mittig": 6}  # swEndConditions_e
MARKE_ZIELFLAECHE = 1  # Endbedingungs-Referenz (Hilfe FeatureExtrusion3: Marke 1) – Abhängig von S10 Frage 6
VERSATZ_WEG_VON_SKIZZE = False  # OffsetReverse1: False = Versatz zur Skizze hin – Abhängig von S10 Frage 6
VERSATZ_MASS = "D1"  # Maß des Versatzes am Feature – Abhängig von S10 Frage 6


def aufsatz(model, typ: int, tiefe_m: float, umkehren: bool):
    return model.FeatureManager.FeatureExtrusion3(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, False, False, False, False, 0.0, 0.0,
        VERSATZ_WEG_VON_SKIZZE, False, False, False, True, True, True, 0, 0.0, False,
    )


def schnitt(model, typ: int, tiefe_m: float, umkehren: bool):
    return model.FeatureManager.FeatureCut4(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, False, False, False, False, 0.0, 0.0,
        VERSATZ_WEG_VON_SKIZZE, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False,
    )


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
    feature = (schnitt if ist_schnitt else aufsatz)(ctx.model, typ, tiefe, umkehren)
    if feature is None:
        grund = " (trifft der Schnitt Material? ggf. umkehren)" if ist_schnitt else ""
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{f['typ']} {f['id']} nicht erzeugt{grund}", schritt="feature")
    feature.Name = f["id"]
    if "tiefe" in ende:
        ctx.verknuepfe(f"D1@{f['id']}", ende["tiefe"])
    if "abstand" in ende:
        ctx.verknuepfe(f"{VERSATZ_MASS}@{f['id']}", ende["abstand"])
    return FeatureErgebnis([feature], richtung=richtung(se, umkehren != ist_schnitt))
```

- [ ] **Step 4: API-Prüfung und Tests**

Run: `.venv\Scripts\python.exe -m swki api pruefe-code`
Expected: `"befunde": []`.

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 260 passed, 28 deselected.

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_endbedingungen.py tests\live\test_live_extrusion.py tests\live\test_live_rotation_bohrung.py tests\referenz`
Expected: alle `OK`.

Toggle 10 und Integer-Einstellung 6 prüfen: unverändert.

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/handler/extrusion.py tests/live/test_live_endbedingungen.py
git commit -m "compiler: Endbedingungen bis_flaeche und versatz_von_flaeche" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 8: Handler `normbohrung` – ein Bohrungsassistent-Feature je Knoten (live)

**Files:**
- Create: `swki/compiler/handler/normbohrung.py`, `tests/compiler/test_normbohrung.py`, `tests/live/test_live_normbohrung.py`
- Modify: `swki/compiler/handler/__init__.py` (Import), `swki/compiler/skizze.py` (`positionsskizze`, `positionen_festlegen`)

**Interfaces:**
- Consumes: Befunde S10 Frage 1–2 (Task 1); `SW_ART`, `SW_NORM`, `SW_BEFESTIGUNG`, `SW_END_BLIND`, `SW_END_DURCH_ALLES`, `norm_von`, `normmasse`, `groesse_text` (Task 3); `Skizzierer`, `Skizzenebene`, `ebene_aus_flaeche`, `modellpunkt`, `richtung` (`skizze.py`); `loese_flaeche`; `normbohrung_volumen` (Task 4, nur im Live-Test).
- Produces: `hole_werte(art: str, gewindetiefe_m: float | None) -> list[float]` (Value1…Value12); Handler `normbohrung(ctx, f) -> FeatureErgebnis(features=[HoleWzd-Feature namens <id>], richtung=Bohrrichtung ins Material, punkte=[Achspunkt je Position in mm, Reihenfolge der Positionen])`; `skizze.positionsskizze(feature)` und `skizze.positionen_festlegen(ctx, feature, se: Skizzenebene, positionen: list, name: str) -> None` (weitere Punkte anlegen, alle bemaßen, Skizze `<id>_positionen` benennen, Maße per Gleichung an Parameter binden). Das Bauprotokoll bekommt `punkte` wie bei `bohrung` (für `masse_pruefen`).
- Bewusst nicht gebunden: Bohr- und Gewindetiefe der Normbohrung (kein belegtes Maß am HoleWzd-Feature); eine Abweichung erkennt die Prüfung `normbohrungen` (Task 9) über den Vergleich mit der freigegebenen Kopie.

- [ ] **Step 1: Failing unit test – `tests/compiler/test_normbohrung.py`**

```python
from swki.compiler.handler.normbohrung import hole_werte


def test_gewinde_mit_gewindetiefe():
    assert hole_werte("gewinde", 0.012) == [0.012, -1, -1, -1, -1, -1, 2, 0, -1, -1, -1, -1]


def test_gewinde_durchgehend():
    werte = hole_werte("gewinde", None)
    assert werte[0] == -1 and werte[6] == 2 and werte[7] == 1


def test_zylinderschraube_normale_passung():
    assert hole_werte("zylinderschraube", None) == [-1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1]


def test_stift_nur_normwerte():
    assert hole_werte("stift", None) == [-1.0] * 12
```

- [ ] **Step 2: Live-Test schreiben – `tests/live/test_live_normbohrung.py`**

```python
"""Live: Normbohrungen über den Bohrungsassistenten – alle Positionen in einem Feature (SolidWorks muss laufen)."""

import pythoncom
import pytest

from swki.compiler import sw
from swki.compiler.anker import zylinder_zu_punkten
from swki.compiler.topologie import flaechen
from swki.pruefung.geometrie import normbohrung_volumen
from swki.spec.normen import normmasse

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
VOLL = 100 * 60 * 20
KLOTZ = {
    "id": "f1", "typ": "extrusion",
    "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
    "ende": {"typ": "blind", "tiefe": 20},
}
DECKFLAECHE = {"feature": "f1", "flaeche": "+y"}


def _spec(nb):
    return {"art": "teil", "name": "T", "parameter": {"L": 100}, "features": [KLOTZ, nb]}


def _achsen_xz(feature) -> list:
    return sorted({(round(z.punkt[0], 4), round(z.punkt[2], 4)) for z in flaechen(feature) if z.art == "zylinder"})


def test_gewinde_mit_drei_positionen_in_einem_feature():
    nb = {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": DECKFLAECHE,
          "positionen": [["=-L/2+20", 10], [0, 10], ["=L/2-20", 10]], "tiefe": 16, "gewindetiefe": 12}
    with gebautes_teil(_spec(nb)) as (ctx, fehler, protokoll):
        assert fehler is None
        erg = ctx.ergebnis("f2")
        assert [f.Name for f in erg.features] == ["f2"]
        assert erg.punkte == [(-30.0, 20.0, -10.0), (0.0, 20.0, -10.0), (30.0, 20.0, -10.0)]
        assert protokoll.knoten[1].punkte == [[-30.0, 20.0, -10.0], [0.0, 20.0, -10.0], [30.0, 20.0, -10.0]]
        assert erg.features[0].GetDefinition.GetSketchPointCount == 3
        einzeln = normbohrung_volumen("gewinde", normmasse("gewinde", "M8"), 16)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 3 * einzeln, abs=1e-2)
        assert _achsen_xz(erg.features[0]) == [(-30.0, -10.0), (0.0, -10.0), (30.0, -10.0)]
        # Lage der Positionen hängt an L (Gleichungen an der Positionsskizze f2_positionen)
        g = ctx.model.GetEquationMgr
        texte = [g.Equation(i) for i in range(g.GetCount)]
        assert any("@f2_positionen" in t and '"L"' in t for t in texte)
        dispid = g._oleobj_.GetIDsOfNames("Equation")
        g._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, texte.index('"L" = 100'), '"L" = 140')
        g.EvaluateAll
        sw.rebuild(ctx.model)
        assert _achsen_xz(erg.features[0]) == [(-50.0, -10.0), (0.0, -10.0), (50.0, -10.0)]


@pytest.mark.parametrize(("art", "groesse"), [
    ("zylinderschraube", "M8"), ("senkschraube", "M6"), ("stift", 8), ("gewinde", "M12x1.5"),
])
def test_arten_durch(art, groesse):
    nb = {"id": "f2", "typ": "normbohrung", "art": art, "groesse": groesse, "flaeche": DECKFLAECHE,
          "positionen": [[-20, 0], [20, 0]], "durch": True}
    with gebautes_teil(_spec(nb)) as (ctx, fehler, _):
        assert fehler is None
        erg = ctx.ergebnis("f2")
        einzeln = normbohrung_volumen(art, normmasse(art, groesse), None, dicke=20)
        assert volumen_mm3(ctx.model) == pytest.approx(VOLL - 2 * einzeln, abs=1e-2)
        zylinder = zylinder_zu_punkten(flaechen(erg.features[0]), erg.punkte, 0.1)
        assert [round(z.punkt[0], 4) for z in zylinder] == [-20.0, 20.0]


def test_senkschraube_von_unten():
    nb = {"id": "f2", "typ": "normbohrung", "art": "senkschraube", "groesse": "M6",
          "flaeche": {"feature": "f1", "flaeche": "-y"}, "positionen": [[10, 5]], "durch": True}
    with gebautes_teil(_spec(nb)) as (ctx, fehler, _):
        assert fehler is None
        erg = ctx.ergebnis("f2")
        assert erg.punkte == [(10.0, 0.0, -5.0)]
        assert erg.richtung == (0.0, 1.0, 0.0)  # ins Material = gegen die Flächennormale −y
        kegel = [fc for fc in erg.features[0].GetFaces if fc.GetSurface.IsCone]
        assert kegel and all(abs(fc.GetBox[1]) < 1e-9 for fc in kegel)  # Senkung an der Unterseite (Y = 0)
```

- [ ] **Step 3: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_normbohrung.py -q`
Expected: FAIL (`ModuleNotFoundError: swki.compiler.handler.normbohrung`).

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_normbohrung.py`
Expected: 6× `FEHLER` (`UNBEKANNTER_TYP: Kein Handler für typ 'normbohrung'`).

- [ ] **Step 4: Positionsskizze – in `swki/compiler/skizze.py` ergänzen**

Import `REFERENZ_NICHT_GEFUNDEN` zu den Fehler-Importen hinzufügen:

```python
from swki.compiler.fehler import (
    FEATURE_NICHT_ERZEUGT, REFERENZ_NICHT_GEFUNDEN, SKIZZE_NICHT_BESTIMMT, SKIZZE_UNGUELTIG, BauFehler,
)
```

Nach `skizziere` einfügen:

```python
def positionsskizze(feature):
    """Positionsskizze eines Bohrungsassistent-Features: die Unterskizze ohne Skizzensegmente (nur Punkte) –
    Abhängig von S10 Frage 2."""
    unter = feature.GetFirstSubFeature
    while unter is not None:
        if unter.GetTypeName2 == "ProfileFeature" and not (unter.GetSpecificFeature2.GetSketchSegments or ()):
            return unter
        unter = unter.GetNextSubFeature
    raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"{feature.Name}: keine Positionsskizze gefunden", schritt="skizze")


def positionen_festlegen(ctx, feature, se: Skizzenebene, positionen: list, name: str) -> None:
    """Die erste Position steht schon (SelectByRay); weitere als Skizzenpunkte in die Positionsskizze einfügen, alle
    Punkte zum Ursprung bemaßen, die Skizze benennen und die Maße an Parameter binden (S10 Frage 2)."""
    skizze = positionsskizze(feature)
    model, sm = ctx.model, ctx.model.SketchManager
    sw.auswahl_leeren(model)
    skizze.Select2(False, 0)
    sm.InsertSketch(True)  # öffnet die selektierte Skizze (S9b)
    status, masse = None, []
    try:
        skizzierer = Skizzierer(ctx, se, sm.ActiveSketch)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            for u, v in positionen[1:]:
                x, y = skizzierer.zu_skizze(ctx.wert(u), ctx.wert(v))
                if sm.CreatePoint(x, y, 0.0) is None:
                    raise BauFehler(SKIZZE_UNGUELTIG, f"Positionspunkt ({u}, {v}) nicht angelegt", schritt="skizze")
            for p in positionen:
                skizzierer.lage(p, (ctx.wert(p[0]) + _MASS_ABSTAND_MM, ctx.wert(p[1]) + _MASS_ABSTAND_MM))
        status, masse = sm.ActiveSketch.GetConstrainedStatus, skizzierer.masse
    finally:
        sm.InsertSketch(True)
    if status != sw.SW_FULLY_CONSTRAINED:
        raise BauFehler(SKIZZE_NICHT_BESTIMMT, f"Positionsskizze {name}: Status {status} statt voll bestimmt",
                        schritt="skizze")
    skizze.Name = name
    for m in masse:
        ctx.verknuepfe(f"{m.name}@{name}", m.roh, m.vorzeichen)
```

- [ ] **Step 5: Handler – `swki/compiler/handler/normbohrung.py`**

```python
"""Handler "normbohrung" – Bohrungsassistent (IFeatureManager.HoleWizard5, ISO) mit allen Positionen in einem Feature
(Spec 2c §3; Aufrufkette wie S9b Baustein 21, Positionen laut Spike S10 Frage 2).

Die erste Position wird per SelectByRay auf der Fläche gewählt; die übrigen kommen als Skizzenpunkte in die
Positionsskizze, die danach voll bestimmt wird (Lagemaße zum Ursprung, per Gleichung an Parameter). Gewinde immer
kosmetisch, Größen und Normmaße aus swki/wissen/bohrungsnormen.yaml. Instanzen 1, 2, … in Reihenfolge der Positionen;
ihre Achspunkte gehen ins Bauprotokoll (masse_pruefen).
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import ebene_aus_flaeche, modellpunkt, positionen_festlegen, richtung
from swki.compiler.topologie import loese_flaeche
from swki.spec.normen import (
    SW_ART, SW_BEFESTIGUNG, SW_END_BLIND, SW_END_DURCH_ALLES, SW_NORM, groesse_text, norm_von, normmasse,
)
from swki.verbindung import mm

SW_SCHRAUBE_NORMAL = 1  # swWzdHoleScrewClearanceTypes_e.swScrewClearanceNormal
SW_GEWINDE_KOSMETISCH = 2  # swWzdHoleCosmeticThreadTypes_e.swCosmeticThreadWithoutCallout
SW_GEWINDE_BLIND = 0  # swWzdHoleThreadEndCondition_e.swEndThreadTypeBLIND
SW_GEWINDE_DURCH = 1  # swWzdHoleThreadEndCondition_e.swEndThreadTypeTHROUGH_ALL
SW_SEL_FACES = 2  # swSelectType_e.swSelFACES
_STRAHL_MM = 1.0  # Start des Auswahlstrahls über der Fläche
_STRAHL_RADIUS_M = 0.0005


def hole_werte(art: str, gewindetiefe_m: float | None) -> list[float]:
    """Value1…Value12 von HoleWizard5 je Art (API-Hilfe, Remarks; −1 = Normwert/ungenutzt) – Abhängig von S10 Frage 1."""
    v = [-1.0] * 12
    if art == "gewinde":
        v[0] = -1.0 if gewindetiefe_m is None else gewindetiefe_m  # Tap Thread Depth
        v[6] = SW_GEWINDE_KOSMETISCH  # Cosmetic Thread Type
        v[7] = SW_GEWINDE_DURCH if gewindetiefe_m is None else SW_GEWINDE_BLIND  # Thread End Condition
    elif art in ("zylinderschraube", "senkschraube"):
        v[3] = SW_SCHRAUBE_NORMAL  # Screw Fit
    return v


@handler("normbohrung")
def normbohrung(ctx, f: dict) -> FeatureErgebnis:
    norm = norm_von(f)
    masse = normmasse(f["art"], f["groesse"], norm)
    if masse is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"normbohrung {f['id']}: Größe {groesse_text(f['groesse'])} fehlt in der "
                                               "Maßtabelle", schritt="feature")
    flaeche = loese_flaeche(ctx, f["flaeche"])
    se = ebene_aus_flaeche(flaeche)
    punkte = [modellpunkt(se.orientierung, ctx.wert(u), ctx.wert(v), se.lage) for u, v in f["positionen"]]
    n = flaeche.normale
    x, y, z = (mm(c + _STRAHL_MM * nc) for c, nc in zip(punkte[0], n))
    sw.auswahl_leeren(ctx.model)
    if not ctx.model.Extension.SelectByRay(x, y, z, -n[0], -n[1], -n[2], _STRAHL_RADIUS_M, SW_SEL_FACES, False, 0, 0):
        raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"normbohrung {f['id']}: Fläche an Position 1 nicht getroffen",
                        schritt="auswahl")
    durch = bool(f.get("durch"))
    gewindetiefe = ctx.m(f["gewindetiefe"]) if "gewindetiefe" in f else None
    feature = ctx.model.FeatureManager.HoleWizard5(
        SW_ART[f["art"]], SW_NORM[norm], SW_BEFESTIGUNG[f["art"]], masse["sw_groesse"],
        SW_END_DURCH_ALLES if durch else SW_END_BLIND, -1, 0.0 if durch else ctx.m(f["tiefe"]), -1,
        *hole_werte(f["art"], gewindetiefe),
        "", False, False, True, False, True, False,
    )
    sw.auswahl_leeren(ctx.model)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"normbohrung {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    positionen_festlegen(ctx, feature, se, f["positionen"], f"{f['id']}_positionen")
    sw.rebuild(ctx.model)
    anzahl = feature.GetDefinition.GetSketchPointCount
    if anzahl != len(f["positionen"]):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"normbohrung {f['id']}: {anzahl} statt {len(f['positionen'])} Positionen",
                        schritt="feature")
    return FeatureErgebnis([feature], richtung=richtung(se, True), punkte=punkte)
```

`swki/compiler/handler/__init__.py` – Importzeile ersetzen:

```python
from swki.compiler.handler import bohrung, extrusion, kanten, muster, normbohrung, rotation, skript  # noqa: F401
```

- [ ] **Step 6: API-Prüfung und Unit-Tests**

Run: `.venv\Scripts\python.exe -m swki api pruefe-code`
Expected: `"befunde": []`.

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 264 passed, 28 deselected.

- [ ] **Step 7: Live-Tests**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_normbohrung.py tests\live\test_live_skript.py tests\referenz`
Expected: alle `OK` (6 Normbohrungstests, Notausgang und beide Referenzen unverändert).

Toggle 10 und Integer-Einstellung 6 prüfen: unverändert.

- [ ] **Step 8: Commit**

```powershell
git add swki/compiler/handler/normbohrung.py swki/compiler/handler/__init__.py swki/compiler/skizze.py tests/compiler/test_normbohrung.py tests/live/test_live_normbohrung.py
git commit -m "compiler: Handler normbohrung (Bohrungsassistent, alle Positionen in einem Feature)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 9: Prüfung `normbohrungen` und Baum-Kennzahl

**Files:**
- Modify: `swki/pruefung/bewertung.py` (`Messwerte`, neue Funktionen, `bewerte`), `swki/pruefung/messen.py` (`lies_normbohrung`, `normbohrungen`, `messe`), `swki/pruefung/befehle.py` (`pruefen`), `swki/pruefung/bericht.py` (Abschnitt Feature-Baum)
- Test: `tests/pruefung/test_bewertung.py` (6 neue Tests), `tests/pruefung/test_bericht.py` (1 neuer Test), `tests/live/test_live_pruefen_normbohrung.py` (neu, 2 Live-Tests)

**Interfaces:**
- Consumes: `SW_ART`, `SW_BEFESTIGUNG`, `SW_NORM`, `SW_END_BLIND`, `SW_END_DURCH_ALLES`, `norm_von`, `normmasse`, `groesse_text` (Task 3); Befund S10 Frage 4 (welches Tiefenfeld, `FastenerSize`-Text); `freigegebene_spec(spec_pfad)` (2b).
- Produces: `Messwerte.normbohrungen: dict[str, dict | str]` (Vorgabe `{}`; Werte `{"art", "befestigung", "norm", "groesse", "ende", "tiefe", "gewindetiefe", "positionen"}` in mm oder Fehlertext); `normbohrung_abweichungen(f: dict, ist: dict, parameter: dict) -> list[str]`; `baum_kennzahl(spec: dict, protokoll: dict | None) -> {"knoten": int, "features": int}`; Prüfung `normbohrungen` direkt nach `skizzen`, nur wenn die freigegebene Kopie `normbohrung`-Knoten hat, `knoten` = abweichende IDs; `messen.lies_normbohrung(feature) -> dict`, `messen.normbohrungen(model, soll_spec) -> dict`, `messen.messe(ctx, freigegeben: dict | None = None)`; Prüfbericht mit Schlüssel `"baum"`; `bericht.md` mit Abschnitt „Feature-Baum (letzter Lauf)“.

- [ ] **Step 1: Failing tests – an `tests/pruefung/test_bewertung.py` anhängen**

Import-Zeile ersetzen durch:

```python
from swki.pruefung.bewertung import Messwerte, baum_kennzahl, bewerte, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from swki.spec.normen import normmasse
```

Anhängen:

```python
NB = {"id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8",
      "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [["=-L/2+10", 0], ["=L/2-10", 0]], "durch": True}
SPEC_NB = {**SPEC, "features": [*SPEC["features"], NB]}
IST_NB = {"art": 0, "befestigung": 139, "norm": 8, "groesse": normmasse("zylinderschraube", "M8")["sw_groesse"],
          "ende": 1, "tiefe": 0.0, "gewindetiefe": 0.0, "positionen": 2}


def test_normbohrung_passt():
    bericht = bewerte(SPEC_NB, _messwerte(normbohrungen={"f2": IST_NB}), STANDARD)
    assert bericht["bestanden"] is True
    assert [p["id"] for p in bericht["pruefungen"]][:3] == ["rebuild", "skizzen", "normbohrungen"]


def test_normbohrung_groesse_weicht_ab():
    [mangel] = bewerte(SPEC_NB, _messwerte(normbohrungen={"f2": IST_NB | {"groesse": "M10"}}), STANDARD)["maengel"]
    assert mangel["pruefung"] == "normbohrungen" and mangel["knoten"] == ["f2"]
    assert "groesse: ist M10" in mangel["beschreibung"]


def test_normbohrung_fehlt_im_teil():
    [mangel] = bewerte(SPEC_NB, _messwerte(normbohrungen={"f2": "Feature f2 fehlt im Teil"}), STANDARD)["maengel"]
    assert mangel["knoten"] == ["f2"] and "fehlt" in mangel["beschreibung"]


def test_normbohrung_soll_aus_freigegebener_kopie():
    # Nachgebessert auf M10 (Text, von der Prüfsumme nicht geschützt): gebaut ist M10, Soll bleibt M8
    nachgebessert = copy.deepcopy(SPEC_NB)
    nachgebessert["features"][1]["groesse"] = "M10"
    ist = IST_NB | {"groesse": normmasse("zylinderschraube", "M10")["sw_groesse"]}
    bericht = bewerte(nachgebessert, _messwerte(normbohrungen={"f2": ist}), STANDARD, freigegeben=SPEC_NB)
    assert [m["pruefung"] for m in bericht["maengel"]] == ["normbohrungen"]


def test_normbohrung_tiefen():
    gewinde = {k: v for k, v in NB.items() if k != "durch"} | {"art": "gewinde", "groesse": "M10", "tiefe": "=T",
                                                               "gewindetiefe": 12}
    ohne_volumen = {k: v for k, v in SPEC["pruefung"].items() if k != "volumen"}  # Sackloch: Soll wäre berechenbar
    spec = {**SPEC, "parameter": {"L": 100, "T": 16}, "features": [SPEC["features"][0], gewinde], "pruefung": ohne_volumen}
    ist = IST_NB | {"art": 4, "befestigung": 147, "groesse": normmasse("gewinde", "M10")["sw_groesse"], "ende": 0,
                    "tiefe": 16.0, "gewindetiefe": 11.0}
    [mangel] = bewerte(spec, _messwerte(normbohrungen={"f2": ist}), STANDARD)["maengel"]
    assert mangel["beschreibung"] == "normbohrungen: {'f2': ['gewindetiefe: ist 11 statt 12']}"


def test_baum_kennzahl():
    protokoll = {"knoten": [{"id": "f1", "sw_name": "f1"}, {"id": "f2", "sw_name": "f2, f2_senkung"},
                            {"id": "f3", "sw_name": None}]}
    assert baum_kennzahl(SPEC_NB, protokoll) == {"knoten": 2, "features": 3}
    assert baum_kennzahl(SPEC_NB, None) == {"knoten": 2, "features": 0}
```

An `tests/pruefung/test_bericht.py` anhängen:

```python
def test_feature_baum():
    md = bericht_markdown(
        {"name": "Platte"}, "A-1", LAEUFE, ("bestanden", "Lauf 2 bestanden"),
        {"maengel": [], "bilder": {}, "baum": {"knoten": 10, "features": 10}}, None, None, [],
    )
    assert ("## Feature-Baum (letzter Lauf)\n\n- Knoten der Spezifikation: 10\n"
            "- erzeugte Features (ohne Skizzen, Ebenen, Achsen): 10") in md
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung -q`
Expected: FAIL (`ImportError: cannot import name 'baum_kennzahl'`).

- [ ] **Step 3: `swki/pruefung/bewertung.py` erweitern**

Imports ergänzen:

```python
from swki.spec.normen import (
    SW_ART, SW_BEFESTIGUNG, SW_END_BLIND, SW_END_DURCH_ALLES, SW_NORM, groesse_text, norm_von, normmasse,
)
```

Konstante nach `_TOL_SCHWERPUNKT` ergänzen: `_TOL_TIEFE = 0.01`

In `Messwerte` als letztes Feld ergänzen:

```python
    normbohrungen: dict[str, dict | str] = field(default_factory=dict)  # ID → Bohrungsassistent-Daten oder Fehlertext
```

Nach `_pruefung` einfügen:

```python
def normbohrung_abweichungen(f: dict, ist: dict, parameter: dict) -> list[str]:
    """Spec 2c §3.4: normbohrung-Knoten (freigegebene Kopie) gegen die Bohrungsassistent-Daten des gleichnamigen
    Features (swki.pruefung.messen.lies_normbohrung, Längen in mm). Leere Liste = passt."""
    norm = norm_von(f)
    soll = {"art": SW_ART[f["art"]], "befestigung": SW_BEFESTIGUNG[f["art"]], "norm": SW_NORM.get(norm),
            "positionen": len(f["positionen"]), "ende": SW_END_DURCH_ALLES if f.get("durch") else SW_END_BLIND}
    abweichungen = [f"{k}: ist {ist.get(k)} statt {v}" for k, v in soll.items() if ist.get(k) != v]
    masse = normmasse(f["art"], f["groesse"], norm) or {}
    if ist.get("groesse") not in {masse.get("sw_groesse"), masse.get("gelesen")} - {None}:
        abweichungen.append(f"groesse: ist {ist.get('groesse')} statt {masse.get('sw_groesse', groesse_text(f['groesse']))}")
    for feld in ("tiefe", "gewindetiefe"):
        if feld in f:
            wert = auswerten(f[feld], parameter)
            if abs(ist.get(feld, 0.0) - wert) > _TOL_TIEFE:
                abweichungen.append(f"{feld}: ist {ist.get(feld, 0.0):g} statt {wert:g}")
    return abweichungen


def baum_kennzahl(spec: dict, protokoll: dict | None) -> dict:
    """Spec 2c §6.3: Knoten der Spezifikation und vom Bau erzeugte Features (Namen aus dem Bauprotokoll; Skizzen,
    Ebenen und Achsen legt der Compiler nebenbei an und zählen nicht)."""
    namen = [n for k in (protokoll or {}).get("knoten", []) if k.get("sw_name") for n in k["sw_name"].split(", ")]
    return {"knoten": len(spec["features"]), "features": len(namen)}
```

In `bewerte` direkt nach der Zeile `ergebnisse.append(_pruefung("skizzen", …))` einfügen:

```python
    soll_spec = freigegeben or spec
    soll_normbohrungen = [f for f in soll_spec["features"] if f["typ"] == "normbohrung"]
    if soll_normbohrungen:
        p_soll = soll_spec.get("parameter", {})
        abweichend = {}
        for f in soll_normbohrungen:
            ist = m.normbohrungen.get(f["id"])
            if not isinstance(ist, dict):
                abweichend[f["id"]] = [ist or f"Feature {f['id']} fehlt im Teil"]
            elif fehler := normbohrung_abweichungen(f, ist, p_soll):
                abweichend[f["id"]] = fehler
        ergebnisse.append(_pruefung("normbohrungen", not abweichend, ist=abweichend, knoten=sorted(abweichend)))
```

Docstring von `bewerte` um „Normbohrungen werden gegen die freigegebene Kopie geprüft (Größen sind Text, die Prüfsumme schützt sie nicht).“ ergänzen.

- [ ] **Step 4: `swki/pruefung/bericht.py` – Abschnitt Feature-Baum**

In `bericht_markdown` direkt vor `zeilen += ["", "## Screenshots (letzter Lauf)", ""]` einfügen:

```python
    baum = (letzter_bericht or {}).get("baum")
    if baum:
        zeilen += ["", "## Feature-Baum (letzter Lauf)", "", f"- Knoten der Spezifikation: {baum['knoten']}",
                   f"- erzeugte Features (ohne Skizzen, Ebenen, Achsen): {baum['features']}"]
```

- [ ] **Step 5: Unit-Tests laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/pruefung -q`
Expected: alle grün (test_bewertung.py 16, test_bericht.py 3).

- [ ] **Step 6: `swki/pruefung/messen.py` – Daten lesen**

Nach `rebuild_fehler` einfügen:

```python
def lies_normbohrung(feature) -> dict:
    """Bohrungsassistent-Daten eines Features (IFeature.GetDefinition → IWizardHoleFeatureData2, beides ohne "()";
    Längen in mm) – Feldwahl Abhängig von S10 Frage 4."""
    d = feature.GetDefinition
    return {
        "art": d.Type, "befestigung": d.FastenerType2, "norm": d.Standard2, "groesse": d.FastenerSize,
        "ende": d.EndCondition, "tiefe": round(in_mm(d.Depth), 6), "gewindetiefe": round(in_mm(d.ThreadDepth), 6),
        "positionen": d.GetSketchPointCount,
    }


def normbohrungen(model, soll_spec: dict) -> dict[str, dict | str]:
    """Für jeden normbohrung-Knoten der Soll-Spezifikation die Daten des gleichnamigen Features oder einen Fehlertext."""
    ergebnis = {}
    for f in soll_spec["features"]:
        if f["typ"] != "normbohrung":
            continue
        feature = model.FeatureByName(f["id"])
        if feature is None:
            ergebnis[f["id"]] = f"Feature {f['id']} fehlt im Teil"
        elif feature.GetTypeName2 != "HoleWzd":
            ergebnis[f["id"]] = f"Feature {f['id']} ist {feature.GetTypeName2}, kein Bohrungsassistent"
        else:
            try:
                ergebnis[f["id"]] = lies_normbohrung(feature)
            except Exception as e:  # COM-Fehler beim Lesen → Mangel statt Abbruch der Prüfung
                ergebnis[f["id"]] = f"Bohrungsassistent-Daten von {f['id']} nicht lesbar: {e}"
    return ergebnis
```

`messe` ersetzen:

```python
def messe(ctx, freigegeben: dict | None = None) -> Messwerte:
    """freigegeben: Spezifikation im Stand der Freigabe (Soll der Prüfung normbohrungen); ohne Angabe ctx.spec."""
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
        normbohrungen=normbohrungen(model, freigegeben or ctx.spec),
    )
```

- [ ] **Step 7: `swki/pruefung/befehle.py` – `pruefen`**

Import `from swki.pruefung.bewertung import bewerte` ersetzen durch `from swki.pruefung.bewertung import baum_kennzahl, bewerte`. In `pruefen` den Block von `app = verbinde(r.sw_jahr)` bis zum Ende der `bericht = {…}`-Zuweisung ersetzen durch:

```python
    app = verbinde(r.sw_jahr)
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    soll = freigegebene_spec(spec_pfad)
    model = oeffne(app, teil)
    try:
        ctx = kontext_aus_datei(app, model, spec, spec_pfad, standard["toleranzen"]["anker_mm"], protokoll)
        messwerte = messe(ctx, soll)
        bilder = screenshots(app, model, ordner / "bilder")
    finally:
        sw.schliesse(app, model)
    bericht = {
        "auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(teil),
        **bewerte(spec, messwerte, standard, soll), "baum": baum_kennzahl(spec, protokoll), "bilder": bilder,
    }
```

- [ ] **Step 8: Live-Test – `tests/live/test_live_pruefen_normbohrung.py`**

```python
"""Live: Code-Prüfung normbohrungen gegen die freigegebene Kopie und Baum-Kennzahl (SolidWorks muss laufen)."""

import json
import shutil

import pytest
import yaml

from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-NORMBOHRUNG"
SPEC = {
    "art": "teil", "name": "Platte", "material": "1.1191", "eigenschaften": {"Benennung": "Prüfplatte Normbohrung"},
    "parameter": {"L": 100, "A": 15},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": 60}}]},
         "ende": {"typ": "blind", "tiefe": 20}},
        {"id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8",
         "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [["=-L/2+A", 0], ["=L/2-A", 0]], "durch": True},
    ],
    "pruefung": {
        "huellquader": ["=L", 20, 60],
        "masse_pruefen": [{"was": "Schraubenabstand", "von": {"feature": "f2", "instanz": 1, "achse": True},
                           "zu": {"feature": "f2", "instanz": 2, "achse": True}, "soll": "=L-2*A"}],
        "schwerpunkt": {"soll": [0, None, 0]},
    },
}


@pytest.fixture
def spec_pfad(tmp_path):
    ordner = tmp_path / AUFTRAG
    ordner.mkdir()
    yield ordner / "platte.yaml"
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _schreibe(pfad, spec) -> None:
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")


def test_normbohrung_bestanden_mit_baum(capsys, spec_pfad):
    _schreibe(spec_pfad, SPEC)
    assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(spec_pfad))
    assert code == 0, bau
    code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
    assert code == 0 and bericht["bestanden"] is True, bericht["maengel"]
    ergebnisse = {p["id"]: p for p in bericht["pruefungen"]}
    assert ergebnisse["normbohrungen"]["ok"] is True
    assert ergebnisse["mass:Schraubenabstand"]["ist"] == pytest.approx(70)
    assert bericht["baum"] == {"knoten": 2, "features": 2}
    assert _lauf(capsys, "bericht", str(spec_pfad))[0] == 0
    assert "## Feature-Baum (letzter Lauf)" in (spec_pfad.parent / "bericht.md").read_text(encoding="utf-8")


def test_groesse_nach_freigabe_geaendert_ist_mangel(capsys, spec_pfad):
    _schreibe(spec_pfad, SPEC)
    assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
    geaendert = json.loads(json.dumps(SPEC))
    geaendert["features"][1]["groesse"] = "M10"  # Bauweg geändert – die Prüfsumme bemerkt es nicht
    _schreibe(spec_pfad, geaendert)
    code, bau = _lauf(capsys, "bauen", str(spec_pfad))
    assert code == 0, bau
    code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
    assert code == 0 and bericht["bestanden"] is False
    [mangel] = [m for m in bericht["maengel"] if m["pruefung"] == "normbohrungen"]
    assert mangel["knoten"] == ["f2"] and "groesse" in mangel["beschreibung"]
```

- [ ] **Step 9: Alles laufen lassen**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 271 passed, 28 deselected.

Run: `.venv\Scripts\python.exe -m swki api pruefe-code`
Expected: `"befunde": []`.

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_pruefen_normbohrung.py tests\live\test_live_pruefen.py tests\referenz`
Expected: alle `OK` (2 neue, 2 bestehende Prüftests, beide Referenzen).

Toggle 10 und Integer-Einstellung 6 prüfen: unverändert.

- [ ] **Step 10: Commit**

```powershell
git add swki/pruefung/bewertung.py swki/pruefung/messen.py swki/pruefung/befehle.py swki/pruefung/bericht.py tests/pruefung/test_bewertung.py tests/pruefung/test_bericht.py tests/live/test_live_pruefen_normbohrung.py
git commit -m "pruefung: Normbohrungen gegen die freigegebene Kopie, Baum-Kennzahl im Bericht" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 10: Skill `konstruieren`, CLAUDE.md und Wissensdatei

**Files:**
- Modify: `.claude/skills/konstruieren/SKILL.md`, `CLAUDE.md`, `swki/wissen/pywin32-fallstricke.md`

**Interfaces:**
- Consumes: Formate aus Task 3 (`normbohrung`, Skizzenelemente, Endbedingungen), Hinweise aus Task 5, Prüfung aus Task 9, Befunde aus Task 1–2 (`docs/stufe0/ergebnisse.md`, `docs/stufe0/ergebnisse/s10_*.json`).
- Produces: Modellierregeln (Spec §6.1) im Skill; Projektregeln in CLAUDE.md; live belegte API-Muster aus S10 in der Wissensdatei.

- [ ] **Step 1: `.claude/skills/konstruieren/SKILL.md`**

Überschrift `# Konstruieren (Einzelteil, Stufe 2)` ersetzen durch `# Konstruieren (Einzelteil, Stufe 2/2c)`.

In Abschnitt „## 2. Spezifikation schreiben“ nach dem Punkt „Schnitt geht standardmäßig gegen die Skizzennormale …“ einfügen:

```markdown
- Bohrungen für Schrauben, Gewinde und Stifte als `typ: normbohrung` (`art: gewinde | zylinderschraube |
  senkschraube | stift`, `groesse` wie „M8“, „M10x1“ bzw. Stift-Nenndurchmesser `8`, `durch: true` oder `tiefe`,
  bei Gewinde mit `tiefe` auch `gewindetiefe` ≤ `tiefe`). Nur Größen aus `swki/wissen/bohrungsnormen.yaml`; `validieren`
  nennt die verfügbaren. Gewinde werden kosmetisch gebaut. `bohrung` bleibt für freie Durchmesser.
- Skizzenelemente: `rechteck` (optional `radius`), `polygon` (optional `radien`: ein Wert oder je Ecke, 0 = scharf,
  Radius < halbe kürzere Nachbarkante), `langloch` (`mitte`, `laenge` = Mittenabstand der Bögen, `breite`, `winkel`
  zu u in [0, 180)), `kontur` (`start`, `segmente` aus `{linie: [u, v]}` und `{bogen: [u, v], mitte: [u, v]}`, Bögen
  gegen den Uhrzeigersinn in (u, v), letzter Endpunkt = `start`), `kreis`, `mittellinie`.
- Endbedingungen: `blind`, `durch_alles`, `mittig`, `bis_flaeche` (`flaeche`), `versatz_von_flaeche` (`flaeche`,
  `abstand`; der Versatz geht zur Skizze hin – z. B. Restwandstärke über der Unterseite).

### Modellierregeln (kompakter Feature-Baum)
Änderbarkeit zuerst, sonst so wenige Features wie möglich:
1. Drehteile als eine Rotation eines Halbschnitts.
2. Gleiche Bohrungen auf derselben Fläche in **einen** Knoten (mehrere `positionen`); `normbohrung` statt Bohrung +
   Senkung, sobald eine Schraube, ein Gewinde oder ein Stift gemeint ist.
3. Muster und Spiegeln nur, wenn Anzahl, Abstand oder Symmetrie eine Anforderung ist (dann als Parameter); sonst
   Positionen direkt.
4. Runde Konturen in der Skizze (Eckradius, Langloch, Kontur) statt nachträglicher Verrundung senkrechter Kanten, wenn
   die Kontur nur einmal vorkommt.
5. Tiefen, die sich auf eine andere Fläche beziehen (Restwandstärke, bis zum Boden), mit `versatz_von_flaeche` /
   `bis_flaeche`, nicht als gerechnete Zahl.
6. Kantenverrundungen und Fasen gleichen Maßes in einem Knoten, am Ende des Baums.
```

In Abschnitt „## 3. Validieren und Rückfragen“ den Punkt „`hinweise` aus `validieren` (feste Zahlen …) …“ ersetzen durch:

```markdown
- `hinweise` aus `validieren` vor der Freigabe abarbeiten (sie blockieren nie):
  - `art: feste_zahl` – feste Zahl in einem maßtragenden Feld: meist als Parameter führen, sonst dem Nutzer bei der
    Freigabe ausdrücklich nennen.
  - `art: zusammenfassen` – Knoten (`knoten`) lassen sich nach den Modellierregeln zusammenfassen: umbauen oder dem
    Nutzer begründen, warum nicht (z. B. Anzahl und Abstand sind Anforderungen).
```

In Abschnitt „## 5. Bauen, prüfen, Prüfer“ nach dem Punkt zu `swki pruefen` ergänzen:

```markdown
- Der Prüfbericht vergleicht Normbohrungen (Art, Größe, Norm, Positionen, durch/Tiefe) mit der freigegebenen Kopie
  (Prüfung `normbohrungen`) und nennt unter `baum` Knoten- und Featurezahl.
```

- [ ] **Step 2: `CLAUDE.md`**

Im Abschnitt „## Konstruieren (Stufe 2)“ nach dem Punkt „Was das Format nicht kann …“ einfügen:

```markdown
- Normbohrungen (`typ: normbohrung`) nur in Größen aus `swki/wissen/bohrungsnormen.yaml`; die Tabelle nur um Größen
  erweitern, die live gemessen sind (Muster: Spike S10, `spikes/s10_f3_normmasse.py`).
- Kompakter Feature-Baum: Modellierregeln im Skill `konstruieren`; `validieren` meldet Zusammenfassbares als
  `hinweise` mit `art: zusammenfassen`.
```

Im Abschnitt „## Prüfen und Nachbessern (Stufe 2)“ nach dem ersten Punkt einfügen:

```markdown
- `swki pruefen` prüft Normbohrungen gegen die freigegebene Kopie (Größen sind Text, die Prüfsumme schützt sie nicht).
```

- [ ] **Step 3: `swki/wissen/pywin32-fallstricke.md`**

Am Dateiende den folgenden Abschnitt anhängen. **Jeden Punkt** gegen `docs/stufe0/ergebnisse/s10_*.json` und den Abschnitt „Entscheidung“ in `docs/stufe0/ergebnisse.md` prüfen: bestätigte Punkte übernehmen, abweichende mit dem gemessenen Befund umschreiben, nicht belegte streichen (die Datei enthält nur live Belegtes).

```markdown
## Stufe 2c: Normbohrungen, Konturen, Endbedingungen (Spike S10, live belegt)

Rohdaten: `docs/stufe0/ergebnisse/s10_f*.json`, Spikes `spikes/s10_*.py`.

- **HoleWizard5 (27 Parameter):** Value1…Value12 sind je Bohrungsart anders belegt (API-Hilfe, Remarks); −1 = Normwert.
  Gewinde: Value1 Gewindetiefe, Value7 kosmetisches Gewinde (2 = ohne Beschriftung), Value8 Gewinde-Ende (0 blind,
  1 durch). Zylinder- und Senkschraube: Value4 Screw Fit (1 = normal). Durch alles: EndType 1, Depth 0 (S10 F1).
- **Größen-Strings:** Regelgewinde und Schrauben „M8“; Feingewinde- und Stift-Schreibweise stehen als `sw_groesse` in
  `swki/wissen/bohrungsnormen.yaml`. Eine unbekannte Schreibweise liefert still kein Feature (S9b, S10 F1).
- **Mehrere Positionen in einem Feature:** erste Position per `SelectByRay` (Marke 0), dann die Positionsskizze
  (Unterskizze ohne Segmente) mit `Select2` + `InsertSketch(True)` öffnen, weitere Punkte mit `CreatePoint` (AddToDB),
  alle Punkte zum Ursprung bemaßen; nach dem Neuaufbau meldet `GetSketchPointCount` alle Punkte (S10 F2).
- **Bohrungsdaten lesen:** `IFeature.GetDefinition` (ohne `()`) → `IWizardHoleFeatureData2`; `Type`, `Standard2`,
  `FastenerType2`, `FastenerSize`, `EndCondition`, `Depth` (m), `ThreadDepth` (m), `GetSketchPointCount` (ohne `()`)
  sind ohne `AccessSelections` lesbar, auch nach `OpenDoc6` (S10 F4).
- **Maße je Größe:** Bohrungstiefe zählt ab der Ansatzfläche, Bohrspitze 118° nur bei blind, Senkungen von der Fläche
  aus; die Maßtabelle hält die gemessenen Werte (S10 F3).
- **Skizzenverrundung:** die beiden Linien einer Ecke wählen, `CreateFillet(Radius, 1)` (1 =
  `swConstrainedCornerKeepGeometry`): Maße der Ecke bleiben am virtuellen Schnittpunkt, der Bogen bekommt kein eigenes
  Maß – Radius per `AddDimension2` auf den Bogen (S10 F5).
- **Langloch:** `CreateSketchSlot(1, 0, Breite, Mitte, Ende der Mittellinie, 0, 0, 0, 1, False)` (Mittelpunkt-Typ,
  Länge Mitte–Mitte, ohne Auto-Maße) legt zwei Linien, zwei Bögen, eine Konstruktions-Mittellinie (Länge =
  Mittenabstand) und einen Mittelpunkt an; die neuen Segmente stehen hinten in `GetSketchSegments` (S10 F5).
- **Bögen:** `CreateArc(Mitte, Start, Ende, Richtung)` mit +1 = gegen den Uhrzeigersinn im Skizzensystem; kehrt die
  (u, v)-Abbildung einer Ebene den Drehsinn um (Determinante < 0), −1. Doppelte Punkte an Segmentenden verschmilzt
  `SketchAddConstraints("sgMERGEPOINTS")`. Ein Bogenendpunkt ist mit einem Lagemaß (Koordinate mit kleinerem Abstand
  zum Mittelpunkt) voll bestimmt, wenn Mittelpunkt und Anfang bestimmt sind (S10 F5).
- **Endbedingungen bis/versatz Fläche:** Skizze mit Marke 0, Zielfläche mit Marke 1 anhängen, dann `FeatureCut4` /
  `FeatureExtrusion3` mit T1 = 4 bzw. 5; `OffsetReverse1 = False` versetzt zur Skizze hin (Restwandstärke), das
  Versatzmaß heißt `D1` (S10 F6).
```

- [ ] **Step 4: Abgleich**

`SKILL.md` gegen Spec 2c §6.1 lesen: alle sechs Regeln stehen wortgleich im Sinn da; jeder genannte Befehl und jedes Feld existiert (`swki validieren|freigeben|bauen|pruefen|status|bericht`, Schema aus Task 3). Abweichungen im Task-Bericht nennen.

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: 271 passed, 28 deselected (nur Doku geändert).

- [ ] **Step 5: Commit**

```powershell
git add .claude/skills/konstruieren/SKILL.md CLAUDE.md swki/wissen/pywin32-fallstricke.md
git commit -m "skills: Modellierregeln kompakter Baum, Normbohrung, Endbedingungen; Wissen aus S10" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 11: Referenzteil *Auswerferhalteplatte*

**Files:**
- Create: `tests/referenz/auswerferhalteplatte/auswerferhalteplatte.yaml`, `tests/referenz/auswerferhalteplatte/sollvolumen.py`, `tests/referenz/test_sollvolumen.py`
- Modify: `tests/referenz/test_referenzen.py` (Parameterliste)

**Interfaces:**
- Consumes: alle Befehle; Handler aus Task 6–8; Prüfung aus Task 9; `normmasse`, `bohrspitze_grad` (Task 3).
- Referenz (Spec §8): Platte L 246 × B 156 × H 22 auf Ebene oben, Mitte im Ursprung, Werkstoff 1.1191 (C45E); Grundplatte als Rechteck mit Eckradius R6; Befestigung ISO 4762 M8 (4×, durch); Stiftbohrungen Ø8 (2×, durch); Gewinde M10 (Regel, Sackloch Bohrtiefe 16, Gewinde 12, 2×); Gewinde M12x1,5 (Fein, durch, 1×); Senkschraube ISO 10642 M6 (2×, durch); Tasche 120 × 60 mit R8 und `versatz_von_flaeche` (Restwandstärke 6 über der Unterseite); Langloch 40 × 12 im Taschenboden mit `bis_flaeche` (Unterseite); Aussparung als `kontur` mit zwei Bögen R10 (80 × 20, Tiefe 8); Fase 1 × 45° umlaufend oben. Die Anordnung ist in u symmetrisch → Schwerpunkt X = 0.
- Sollvolumen analytisch aus Parametern und Maßtabelle (`sollvolumen.py`, unabhängig von Compiler und `geometrie.py`). Mit den vorläufigen Tabellenwerten aus Task 1 Step 8 ergibt sich 692845,209 mm³; **nach dem Spike neu rechnen**, wenn die Tabelle andere Werte hat – nie an einen Messwert anpassen.

- [ ] **Step 1: Referenz anlegen – `tests/referenz/auswerferhalteplatte/auswerferhalteplatte.yaml`**

```yaml
# Referenzteil Stufe 2c: Auswerferhalteplatte (selbst definiert, angelehnt an eine Auswerferhalteplatte im Formenbau).
# Nutzt jedes neue Element mindestens einmal: Rechteck mit Eckradius, normbohrung (ISO 4762, Stift, M-Regel- und
# M-Feingewinde, ISO 10642), Tasche mit Eckradius und versatz_von_flaeche, Langloch mit bis_flaeche, kontur mit Bögen,
# umlaufende Fase. Platte L × B × H auf Ebene oben (wächst nach +Y), Mitte im Ursprung; (u, v) auf der Deckfläche:
# X = u, Z = −v. Alle Bohrungen und Aussparungen liegen symmetrisch zu u = 0 (Schwerpunkt X = 0).
art: teil
name: Auswerferhalteplatte
material: "1.1191"
eigenschaften: {Benennung: Auswerferhalteplatte}
parameter:
  L: 246      # Länge (X)
  B: 156      # Breite (Z)
  H: 22       # Dicke (Y)
  R: 6        # Eckradius der Platte
  A: 20       # Randabstand der Befestigung und der Stifte
  F: 1        # Fase umlaufend oben
  TL: 120     # Tasche Länge
  TB: 60      # Tasche Breite
  TR: 8       # Tasche Eckradius
  RW: 6       # Restwandstärke unter der Tasche
  LL: 40      # Langloch Mittenabstand
  LB: 12      # Langloch Breite
  KB: 80      # Aussparung: Mittenabstand der Bögen
  KH: 20      # Aussparung: Breite (= 2 × Bogenradius)
  KV: 25      # Aussparung: Lage der Unterkante (v)
  KT: 8       # Aussparung: Tiefe
  BT: 16      # Gewinde M10: Bohrtiefe
  GT: 12      # Gewinde M10: Gewindetiefe
features:
  - id: f1            # Grundplatte mit Eckradius
    typ: extrusion
    skizze:
      ebene: oben
      elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B", radius: "=R"}}]
    ende: {typ: blind, tiefe: "=H"}
  - id: f2            # Befestigung ISO 4762 M8, 4×
    typ: normbohrung
    art: zylinderschraube
    groesse: M8
    flaeche: {feature: f1, flaeche: "+y"}
    positionen:
      - ["=-L/2+A", "=-B/2+A"]
      - ["=L/2-A", "=-B/2+A"]
      - ["=L/2-A", "=B/2-A"]
      - ["=-L/2+A", "=B/2-A"]
    durch: true
  - id: f3            # Stiftbohrungen Ø8 H7, 2×
    typ: normbohrung
    art: stift
    groesse: 8
    flaeche: {feature: f1, flaeche: "+y"}
    positionen: [["=-L/2+A", 0], ["=L/2-A", 0]]
    durch: true
  - id: f4            # Gewinde M10 (Regelgewinde), Sackloch
    typ: normbohrung
    art: gewinde
    groesse: M10
    flaeche: {feature: f1, flaeche: "+y"}
    positionen: [[-70, 50], [70, 50]]
    tiefe: "=BT"
    gewindetiefe: "=GT"
  - id: f5            # Gewinde M12x1,5 (Feingewinde, z. B. Kühlanschluss), durch
    typ: normbohrung
    art: gewinde
    groesse: M12x1.5
    flaeche: {feature: f1, flaeche: "+y"}
    positionen: [[0, 62]]
    durch: true
  - id: f6            # Senkschrauben ISO 10642 M6, 2×
    typ: normbohrung
    art: senkschraube
    groesse: M6
    flaeche: {feature: f1, flaeche: "+y"}
    positionen: [[-80, -60], [80, -60]]
    durch: true
  - id: f7            # Tasche mit Eckradius, Restwandstärke RW über der Unterseite
    typ: schnitt
    skizze:
      ebene: {feature: f1, flaeche: "+y"}
      elemente: [{rechteck: {mitte: [0, -20], breite: "=TL", hoehe: "=TB", radius: "=TR"}}]
    ende: {typ: versatz_von_flaeche, flaeche: {feature: f1, flaeche: "-y"}, abstand: "=RW"}
  - id: f8            # Langloch-Durchbruch im Taschenboden bis zur Unterseite
    typ: schnitt
    skizze:
      ebene: {feature: f7, flaeche: "+y"}
      elemente: [{langloch: {mitte: [0, -20], laenge: "=LL", breite: "=LB", winkel: 0}}]
    ende: {typ: bis_flaeche, flaeche: {feature: f1, flaeche: "-y"}}
  - id: f9            # Aussparung als Kontur mit zwei Bögen
    typ: schnitt
    skizze:
      ebene: {feature: f1, flaeche: "+y"}
      elemente:
        - kontur:
            start: ["=-KB/2", "=KV"]
            segmente:
              - {linie: ["=KB/2", "=KV"]}
              - {bogen: ["=KB/2", "=KV+KH"], mitte: ["=KB/2", "=KV+KH/2"]}
              - {linie: ["=-KB/2", "=KV+KH"]}
              - {bogen: ["=-KB/2", "=KV"], mitte: ["=-KB/2", "=KV+KH/2"]}
    ende: {typ: blind, tiefe: "=KT"}
  - id: f10           # Fase F × 45° umlaufend oben (eine Kante, setzt sich tangential fort)
    typ: fase
    kanten: [{nahe: ["=L/2", "=H", 0]}]
    abstand: "=F"
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen:
    # analytisch (tests/referenz/auswerferhalteplatte/sollvolumen.py, Normmaße aus swki/wissen/bohrungsnormen.yaml):
    #   Platte (L·B − (4 − π)·R²)·H                                      843592,141
    # − Fase F²/2 · (2(L − 2R) + 2(B − 2R) + 2π(R − F/3))                     395,802
    # − Tasche f7 (TL·TB − (4 − π)·TR²)·(H − RW)                         114320,991
    # − Langloch f8 (LL·LB + π·LB²/4)·RW                                   3558,584
    # − Aussparung f9 (KB·KH + π·(KH/2)²)·KT                              15313,274
    # − f2 4 × ISO 4762 M8 durch (Ø9, Senkung Ø15 × 8,4)                   9398,389
    # − f3 2 × Stift Ø8 durch                                              2211,681
    # − f4 2 × M10, Kernloch Ø8,5 × BT + Bohrspitze 118°                   1912,445
    # − f5 1 × M12x1,5 durch, Kernloch Ø10,5                               1904,983
    # − f6 2 × ISO 10642 M6 durch (Ø6,6, Senkung Ø12,4 × 90°)              1730,783
    # = 692845,209 mm³   (Normmaße Stand Task 1; bei geänderter Tabelle neu rechnen)
    soll: 692845.209
    toleranz_prozent: 0.05
  masse_pruefen:
    - was: Befestigung 1–2
      von: {feature: f2, instanz: 1, achse: true}
      zu: {feature: f2, instanz: 2, achse: true}
      soll: "=L-2*A"
      tol: 0.01
    - was: Befestigung 2–3
      von: {feature: f2, instanz: 2, achse: true}
      zu: {feature: f2, instanz: 3, achse: true}
      soll: "=B-2*A"
      tol: 0.01
    - was: Stiftabstand
      von: {feature: f3, instanz: 1, achse: true}
      zu: {feature: f3, instanz: 2, achse: true}
      soll: "=L-2*A"
      tol: 0.01
    - was: Gewinde M10 Abstand
      von: {feature: f4, instanz: 1, achse: true}
      zu: {feature: f4, instanz: 2, achse: true}
      soll: 140
      tol: 0.01
    - was: Senkschrauben Abstand
      von: {feature: f6, instanz: 1, achse: true}
      zu: {feature: f6, instanz: 2, achse: true}
      soll: 160
      tol: 0.01
    - was: Gewinde M12x1,5 zur Plattenmitte
      von: {feature: f5, instanz: 1, achse: true}
      zu: {punkt: [0, 0, 0]}
      soll: 62
      tol: 0.01
    - was: Restwandstärke unter der Tasche
      von: {feature: f1, flaeche: "-y"}
      zu: {feature: f7, flaeche: "+y"}
      soll: "=RW"
      tol: 0.01
  schwerpunkt: {soll: [0, null, null], tol: 0.05}
```

- [ ] **Step 2: Rechnung – `tests/referenz/auswerferhalteplatte/sollvolumen.py`**

```python
"""Analytisches Sollvolumen der Referenz Auswerferhalteplatte (Stufe 2c) aus Parametern und Maßtabelle.

Aufruf: .venv\\Scripts\\python.exe tests\\referenz\\auswerferhalteplatte\\sollvolumen.py
Rechnet unabhängig vom Compiler und von swki.pruefung.geometrie; nur die Normmaße kommen aus
swki/wissen/bohrungsnormen.yaml (live gemessen in Spike S10). Das Ergebnis gehört nach pruefung.volumen.soll in
auswerferhalteplatte.yaml (samt Kommentar) – nie ein Messwert.
"""

import math
from pathlib import Path

import yaml

from swki.spec.normen import bohrspitze_grad, normmasse

SPEC = Path(__file__).with_name("auswerferhalteplatte.yaml")


def _bohrung(art: str, groesse, tiefe: float | None, dicke: float) -> float:
    """Eine Normbohrung: zylindrischer Teil ab der Fläche (blind mit Bohrspitze), Senkung von der Fläche aus."""
    m = normmasse(art, groesse)
    d = m.get("kernloch") or m.get("durchgang") or m["durchmesser"]
    v = math.pi * d**2 / 4 * (dicke if tiefe is None else tiefe)
    if tiefe is not None:
        v += math.pi * d**2 / 12 * (d / 2) / math.tan(math.radians(bohrspitze_grad()) / 2)
    if art == "zylinderschraube":
        v += math.pi * (m["senkung_d"] ** 2 - d**2) / 4 * m["senkung_t"]
    elif art == "senkschraube":
        ds = m["senkung_d"]
        h = (ds - d) / 2 / math.tan(math.radians(m["senkwinkel"]) / 2)
        v += math.pi * h / 12 * (ds**2 + ds * d + d**2) - math.pi * d**2 / 4 * h
    return v


def rechnung() -> dict[str, float]:
    p = yaml.safe_load(SPEC.read_text(encoding="utf-8"))["parameter"]
    L, B, H, R, F, RW = (p[k] for k in ("L", "B", "H", "R", "F", "RW"))
    return {
        "Platte (L·B − (4 − π)·R²)·H": (L * B - (4 - math.pi) * R**2) * H,
        "− Fase F²/2 · (2(L − 2R) + 2(B − 2R) + 2π(R − F/3))":
            -F**2 / 2 * (2 * (L - 2 * R) + 2 * (B - 2 * R) + 2 * math.pi * (R - F / 3)),
        "− Tasche f7 (TL·TB − (4 − π)·TR²)·(H − RW)": -(p["TL"] * p["TB"] - (4 - math.pi) * p["TR"] ** 2) * (H - RW),
        "− Langloch f8 (LL·LB + π·LB²/4)·RW": -(p["LL"] * p["LB"] + math.pi * p["LB"] ** 2 / 4) * RW,
        "− Aussparung f9 (KB·KH + π·(KH/2)²)·KT": -(p["KB"] * p["KH"] + math.pi * (p["KH"] / 2) ** 2) * p["KT"],
        "− f2 4 × ISO 4762 M8 durch": -4 * _bohrung("zylinderschraube", "M8", None, H),
        "− f3 2 × Stift Ø8 durch": -2 * _bohrung("stift", 8, None, H),
        "− f4 2 × M10, Bohrtiefe BT": -2 * _bohrung("gewinde", "M10", p["BT"], H),
        "− f5 1 × M12x1,5 durch": -_bohrung("gewinde", "M12x1.5", None, H),
        "− f6 2 × ISO 10642 M6 durch": -2 * _bohrung("senkschraube", "M6", None, H),
    }


if __name__ == "__main__":
    teile = rechnung()
    for text, wert in teile.items():
        print(f"{wert:14.3f}  {text}")
    print(f"{sum(teile.values()):14.3f}  Sollvolumen mm³")
```

- [ ] **Step 3: Sollvolumen rechnen und eintragen**

Run: `.venv\Scripts\python.exe tests\referenz\auswerferhalteplatte\sollvolumen.py`
Expected mit den Tabellenwerten aus Task 1 Step 8 (vor dem Ersetzen durch Messwerte): letzte Zeile `692845.209  Sollvolumen mm³`. Hat Task 1 Werte geändert (z. B. Senkungstiefe M8), weicht die Summe ab: dann `soll` und die Zahlen im Kommentar in `auswerferhalteplatte.yaml` auf die ausgegebenen Werte setzen (auf 3 Nachkommastellen) und die Normmaße in den Kommentarzeilen f2–f6 an die Tabelle angleichen. Hat Task 1 den Tiefenbezug korrigiert (Frage 3), `_bohrung` hier genauso korrigieren.

- [ ] **Step 4: Unit-Test für die Rechnung – `tests/referenz/test_sollvolumen.py`**

```python
"""Das Sollvolumen der Referenz Auswerferhalteplatte passt zur Maßtabelle (ohne SolidWorks).

Schlägt fehl, wenn swki/wissen/bohrungsnormen.yaml geändert wurde, ohne soll neu zu rechnen (sollvolumen.py).
"""

import importlib.util
from pathlib import Path

import pytest
import yaml

ORDNER = Path(__file__).parent / "auswerferhalteplatte"


def test_sollvolumen_aus_tabelle():
    modul_spec = importlib.util.spec_from_file_location("sollvolumen", ORDNER / "sollvolumen.py")
    modul = importlib.util.module_from_spec(modul_spec)
    modul_spec.loader.exec_module(modul)
    soll = yaml.safe_load((ORDNER / "auswerferhalteplatte.yaml").read_text(encoding="utf-8"))["pruefung"]["volumen"]["soll"]
    assert sum(modul.rechnung().values()) == pytest.approx(soll, abs=0.001)
```

Run: `.venv\Scripts\python.exe -m pytest tests/referenz/test_sollvolumen.py -v`
Expected: 1 passed.

- [ ] **Step 5: Validieren**

Run: `.venv\Scripts\python.exe -m swki validieren tests\referenz\auswerferhalteplatte\auswerferhalteplatte.yaml`
Expected: `"gueltig": true`, 10 Features; `hinweise` nur `feste_zahl` (Positionen von f4–f6, Taschen- und Langlochmitte), kein `zusammenfassen`.

- [ ] **Step 6: Regressions-Suite erweitern – `tests/referenz/test_referenzen.py`**

Die Parametrierung ersetzen durch:

```python
@pytest.mark.parametrize(("ordner", "spec"), [
    ("buchse", "buchse.yaml"),
    ("formplatte", "formplatte_ds.yaml"),
    ("auswerferhalteplatte", "auswerferhalteplatte.yaml"),
])
```

- [ ] **Step 7: Live laufen lassen**

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz\test_referenzen.py --zeit 240`
Expected: 3× `OK` (Buchse, Formplatte, Auswerferhalteplatte bestehen alle Prüfungen; bei der Auswerferhalteplatte auch `normbohrungen`). Bei Mängeln: Prüfbericht lesen, nur den Bauweg ändern; nie Prüfwerte an Messwerte anpassen – eine falsche Prüfvorgabe mit Begründung im Task-Bericht melden. Toggle 10 und Integer-Einstellung 6 prüfen.

- [ ] **Step 8: Sichtprüfung und Prüfer-Agent**

Freigabe eines Auftrags nur nach ausdrücklichem OK des Nutzers (CLAUDE.md): der Controller holt es vor diesem Schritt ein (Anforderungen = die Referenz oben).

Implementer: Auftrag `auftraege/REF-AHP-2c/` anlegen (nicht committen), `auswerferhalteplatte.yaml` hineinkopieren und `auftraege/REF-AHP-2c/eingabe/beschreibung.md` mit diesem Text schreiben:

```markdown
Auswerferhalteplatte 246 × 156 × 22, Werkstoff 1.1191, Ecken R6, oben umlaufend Fase 1 × 45°.
4 × Befestigung ISO 4762 M8 durch, 20 mm vom Rand; 2 × Stiftbohrung Ø8 H7 durch auf der Mittellinie, 20 mm vom Rand.
2 × Gewinde M10, Bohrtiefe 16, Gewindetiefe 12 (bei u = ±70, v = 50); 1 × Gewinde M12x1,5 durch (u = 0, v = 62);
2 × Senkung ISO 10642 M6 durch (u = ±80, v = −60).
Tasche 120 × 60, Ecken R8, Mitte (0, −20), Restwandstärke 6; im Taschenboden Langloch 40 × 12 durch.
Aussparung 80 × 20 mit Halbkreisenden R10 (v 25…45), Tiefe 8.
```

Dann `validieren` → `freigeben` → `bauen` → `pruefen` für `auftraege/REF-AHP-2c/auswerferhalteplatte.yaml` und `bilder/iso.png` des Laufs mit dem Read-Tool ansehen: gerundete Plattenecken, 4 Senkbohrungen in den Ecken, 2 kleine Stiftbohrungen auf der Mittellinie, 2 M10- und 1 M12-Gewindebohrung, 2 Kegelsenkungen, Tasche mit gerundeten Ecken und Langloch im Boden, Aussparung mit runden Enden, umlaufende Fase, keine Referenzachse. Pfade (Eingabeordner, `auswerferhalteplatte.freigegeben.yaml`, Prüfbericht `protokolle/auswerferhalteplatte.lauf-1.pruefbericht.json`, Screenshot-Ordner) im Task-Bericht nennen.

Controller: den Prüfer-Agenten (`subagent_type: pruefer`) mit genau diesen Pfaden starten, sein JSON-Urteil unverändert (nur das JSON-Objekt, ohne Code-Fences) nach `auftraege/REF-AHP-2c/protokolle/auswerferhalteplatte.lauf-1.pruefer.json` schreiben, `swki status` und `swki bericht` laufen lassen und das Urteil im Task-Bericht festhalten. Mängel des Prüfers führen zur Nachbesserung des Bauwegs (Skill `konstruieren`), nie zu geänderten Prüfwerten.

- [ ] **Step 9: Commit**

```powershell
git add tests/referenz/auswerferhalteplatte tests/referenz/test_referenzen.py tests/referenz/test_sollvolumen.py
git commit -m "referenz: Auswerferhalteplatte (Stufe 2c)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 12: Abschluss Stufe 2c (Rechner A)

**Files:**
- Create: `docs/stufe2c/ergebnisse.md`

**Interfaces:**
- Spec §1: 2c ist fertig, wenn die Referenz *Auswerferhalteplatte* auf SW 2025 besteht, Buchse und Formplatte unverändert bestehen und alle Unit-Tests grün sind (SW 2026 zusammen mit dem Abschluss von Stufe 2 auf Rechner B).

- [ ] **Step 1: Gesamte Testsuite**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: 272 passed, 48 deselected (206 + 66 neue Unit-Tests; 28 + 20 Live-/Referenztests abgewählt: 8 Konturen, 3 Endbedingungen, 6 Normbohrung, 2 Prüfen Normbohrung, 1 Referenz).

Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live tests\referenz --zeit 240`
Expected: alle `OK`.

Run: `.venv\Scripts\python.exe -m swki api pruefe-code`
Expected: `"befunde": []`.

Toggle 10 und Integer-Einstellung 6: unverändert gegenüber Task 1 Step 1. Speicher von `SLDWORKS.exe` notieren.

- [ ] **Step 2: Ergebnisse festhalten – `docs/stufe2c/ergebnisse.md`**

Mit den tatsächlichen Werten aus einem manuellen Lauf je Referenz füllen (`validieren` → `freigeben` → `bauen` → `pruefen` in einem Beispielauftrag unter `auftraege/`, nicht committen, da die Regressions-Suite ihre Protokolle löscht; Freigabe nach OK des Nutzers über den Controller):

```markdown
# Stufe 2c – Ergebnisse

Rechner A (SOLIDWORKS 2025): `pytest -v` … bestanden (… abgewählt), `tests/live_einzeln.py tests/live tests/referenz`
alle … Einzeltests `OK`, `swki api pruefe-code` ohne Befunde, Toggle 10 und Integer-Einstellung 6 unverändert.

| Referenz | SW 2025 (Rechner A) | Knoten / Features | SW 2026 (Rechner B) | Bemerkung |
|---|---|---|---|---|
| Auswerferhalteplatte | Datum, Volumen ist/soll, Dauer | 10 / 10 | ausstehend | Prüfer-Urteil aus Task 11 |
| Buchse | Datum, Volumen ist/soll, Dauer | 6 / 6 | ausstehend | unverändert |
| Formplatte DS | Datum, Volumen ist/soll, Dauer | 10 / 12 | ausstehend | Notausgang f10 unverändert |

## Spike S10
Kurzfassung der Entscheidungen (Verweis auf `docs/stufe0/ergebnisse.md`, Abschnitt „Stufe 2c“), Abweichungen vom Plan.

## Laufzeiten (Phasenzeiten aus dem Protokoll, Rechner A)

## Offene Punkte
- Bohr- und Gewindetiefe von `normbohrung` hängen nicht per Gleichung an Parametern (kein belegtes Maß am HoleWzd-Feature);
  die Prüfung `normbohrungen` erkennt Abweichungen gegenüber der Freigabe.
- Formplatte: Notausgang f10 (M8) ließe sich jetzt als `normbohrung` bauen – Referenz bleibt bewusst unverändert.
- Rechner B (SOLIDWORKS 2026): alle Referenzen noch nicht gelaufen.
```

`Knoten / Features` kommt aus `baum` im Prüfbericht (Formplatte: f7 mit Senkung und das Skript f10 mit zwei Bohrungen erzeugen je zwei Features, daher 12 – den tatsächlichen Wert eintragen). Alle Platzhalterwörter („Datum“, „…“) durch Messwerte ersetzen.

- [ ] **Step 3: Commit**

```powershell
git add docs/stufe2c/ergebnisse.md
git commit -m "stufe2c: Ergebnisse Rechner A" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Übergabe (mit Nutzer)**

Kein Push ohne Rückfrage: dem Nutzer die Ergebnistabelle zeigen und fragen, ob gepusht und ein Pull Request angelegt werden soll. Rechner B (SW 2026) läuft zusammen mit dem Abschluss von Stufe 2 (Spec §1).

---

## Abdeckung der Spec (Selbstprüfung)

| Spec 2c | Umsetzung |
|---|---|
| §1 Ziel, Fertig-Kriterium | Task 11 (Referenz besteht, Buchse/Formplatte weiter grün), Task 12 (alle Tests) |
| §2 Entscheidungen (Umfang, Arten, ISO-Vorgabe, Baum-Regel, Format A, Absicherung) | Task 3 (`normbohrung`, `bohrungsnorm: ISO`, `norm` je Bohrung), Task 8, Task 10, Task 11; Rohrgewinde fehlt bewusst in Tabelle und Schema |
| §3.1 Format normbohrung | Task 3 (Schema, Regeln durch/tiefe/gewindetiefe), Task 8 (ein Feature je Knoten, Name = ID, kosmetisches Gewinde, Positionen voll bestimmt) |
| §3.2 Zuordnung HoleWizard5 | Task 1 (live bestätigt), Task 3 (`SW_ART`, `SW_BEFESTIGUNG`, `SW_NORM`), Task 8 |
| §3.3 Maßtabelle, Größenprüfung, Sollvolumen | Task 1 (`bohrungsnormen.yaml`), Task 3 (`validieren` lehnt unbekannte Größen mit Liste ab), Task 4 (`normbohrung_volumen`, 118°-Spitze) |
| §3.4 Prüfung normbohrungen, Achsen | Task 9 (gegen freigegebene Kopie), Task 8 (Protokoll `punkte`, Achse aus Zylinder, Senkungen koaxial) |
| §4 runde Konturen, Validierung, volumen_auto | Task 2 (Spike), Task 3 (Schema/Validierung), Task 4 (Flächen, Pappus → None), Task 6 (Compiler) |
| §5 Endbedingungen | Task 2 (Spike), Task 3 (Schema/Validierung), Task 4 (None), Task 5 (`abstand` als feste Zahl gemeldet), Task 7 (Compiler, Gleichung D1) |
| §6.1 Modellierregeln | Task 10 (Skill) |
| §6.2 Hinweise feste_zahl/zusammenfassen | Task 5 |
| §6.3 Kennzahl | Task 9 (`baum` im Prüfbericht und in bericht.md) |
| §7 Spike S10 (6 Fragen, Entscheidung mit Nutzer) | Task 1 (Fragen 1–4), Task 2 (Fragen 5–6), Entscheidungsregel oben |
| §8 Referenzteil | Task 11 |
| §9 Nicht in 2c | kein Task (Rohrgewinde, Formschräge, schräge/gekrümmte Bohrungen, Muster über Skizzenpunkte, variable Verrundung, Austragung/Loft, Gravur, offene Punkte aus 2b) |
