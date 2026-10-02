# Stufe 3a – Normteile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Genormte Verbindungselemente (ISO 4762, ISO 4032, ISO 7089, ISO 8734) entstehen auf Anforderung aus Normtabelle und Bauvorlage, prüfen sich vollständig selbst und füllen eine lokale Bibliothek.

**Architecture:** Neues Paket `swki/normteile` (Tabellen, Anfrage, Spezifikation erzeugen, Bau + Selbstprüfung, Bibliothek, Befehle `swki normteil …`). Der Teil-Compiler bekommt den Feature-Typ `referenz` (benannte Bezugsachse/-ebene), die Prüfung zwei neue Messarten (Messpunkt `referenz`, `durchmesser_pruefen`). Normtabellen und Vorlagen liegen unter `swki/wissen/normteile/` im Git; gebaute Teile liegen nur in der Bibliothek (Cache).

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) für Spike und Live-Tests.

**Spec:** `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md` (mit dem Nutzer abgestimmt, 2026-10-02). Kontext: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`.

## Präzisierungen gegenüber der Spec (vom Planer, bindend für diesen Plan)

1. **Verfälschungstest (Spec §11):** Ein verfälschter *Tabellenwert* kann die Selbstprüfung nicht scheitern lassen – das Teil wird aus genau diesem Wert gebaut und gegen ihn gemessen. Tabellenfehler fangen Abgleich und Regeln ab. Getestet wird deshalb (a) eine verfälschte **Vorlage** (Bauweg falsch, Prüfung unverändert) → Selbstprüfung scheitert, nichts wird abgelegt; (b) ein Tabellenwert, der eine Regel verletzt → `NORMTABELLE_UNGUELTIG`.
2. **Sollvolumen (Spec §5/§6):** statt einer handgeschriebenen Formel `pruefung.volumen.soll: auto` (analytisch aus der Spezifikation). Dafür liegen Fasen im Rotationsprofil statt als Fase-Features. Eine unabhängige Handrechnung je Norm sichert die Rechnung ab (Unit-Test).
3. **Prüfer-Ablauf (Spec §6):** zwei zusätzliche Befehle `swki normteil muster <norm>` (Musterteil mit Screenshots, keine Ablage) und `swki normteil urteil <norm> <datei> --vorlage-pruefsumme <x>` (Urteil zur aktuellen Vorlage ablegen). Den Prüfer-Agenten startet der Controller.
4. **Messarten:** Durchmesser und Bezugsgeometrie sind heute nicht messbar. Neu: Messpunkt `{referenz: <id>}` und `pruefung.durchmesser_pruefen` (Zylinderfläche durch einen Punkt, optional koaxial zu einer Bezugsachse). Beide gelten für alle Teile, nicht nur für Normteile.
5. **Mutter ISO 4032:** „Fasen beidseitig“ = 90°-Senkung an beiden Bohrungskanten (Senk-Ø 1,1·d); Eckfasen am Sechskant entfallen (vereinfachte Darstellung, wie das Gewinde).

## Global Constraints

- Genormte Teile werden immer selbst konstruiert (einheitlich); keine STEP-Daten von Herstellern, keine Toolbox.
- Umfang 3a: ISO 4762, ISO 4032, ISO 7089, ISO 8734; Größen M5, M6, M8, M10, M12, M16 bzw. Ø 4, 5, 6, 8, 10, 12.
- Gewinde: Nenn-Ø, keine Gewindedarstellung.
- Keine Nutzerfreigabe je Normteil; jedes Teil prüft sich vollständig selbst; Prüfer-Agent nur je neuer Vorlagenversion.
- Ein Tabellenwert gilt als abgeglichen, wenn ≥ 2 unabhängige recherchierte Quellen ihn bestätigen; Claudes Normwissen zählt nicht als Quelle; sonst Größe `gesperrt` und Abweichung an den Nutzer.
- Nur Längen aus der Längenreihe der Norm.
- Eine Bibliotheksdatei je Größe und Variante; Bibliothek lokal je Rechner, getrennt nach SW-Version, nicht im Git.
- Maßgeblich sind Normtabelle + Bauvorlage im Git; die `.sldprt` in der Bibliothek ist ein Cache.
- **Late Binding** (`swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()` (`GetTypeName2`, `GetSpecificFeature2`, `Transform`, `ArrayData`, `GetRefAxisParams`, `GetFaces` …); IBody2 mit `()`.
- **Einheiten:** Spezifikation und Ausgaben in mm und Grad; die API rechnet in m und rad.
- **Befehle** geben JSON aus, Exit 0 = ok, 1 = Fehler; fachliche Fehler sind `SwkiFehler` mit `daten = {"code": …}`.
- **Nur eigene Dokumente** anfassen; SolidWorks speichert nur im `arbeitsordner`; in die Normteilbibliothek wird nur kopiert, was `swki normteil` selbst gebaut und geprüft hat; nie ein SW-Jahr oder einen Pfad fest in Code.
- **API nachschlagen:** vor jedem neuen SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` bzw. `… api enum <Name>` (vorher `PYTHONIOENCODING=utf-8`). `swki api pruefe-code` muss ohne Befunde bleiben. Bereits nachgeschlagen: `IRefPlane.Transform` (MathTransform), `IMathTransform.ArrayData` (16 doubles: 9 Rotation, 3 Translation in m, 1 Skalierung, 3 unbenutzt), `IRefAxis.GetRefAxisParams` (Start- und Endpunkt, m), `IModelDoc2.InsertAxis2(AutoSize)`, `IFeatureManager.InsertRefPlane` (6 Parameter), `swRefPlaneReferenceConstraints_e`: Coincident = 4, Distance = 8, OptionFlip = 256.
- **Bestand bleibt:** Referenzen *Buchse*, *Formplatte*, *Auswerferhalteplatte* (`tests/referenz/`) bestehen weiter; Handler `bohrung` und `SkriptKontext` unverändert.
- **Prüfwerte nie an Messwerte anpassen.**
- **Sprache:** Code-Bezeichner, Docstrings, Kommentare, Commit-Messages, Berichte auf Deutsch.
- **Tests:** `.venv\Scripts\python.exe -m pytest -q` (ohne SolidWorks; Stand vor dem Plan: **349 passed, 55 deselected**). Jeder Task nennt, wie viele Tests er hinzufügt; maßgeblich ist „vorher + neu“, abweichende Zahlen im Bericht begründen. Live-Tests nur einzeln: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> --zeit 240` mit `PYTHONIOENCODING=utf-8`.
- **SolidWorks-Speicher (Live-Tasks):** Private Bytes von `SLDWORKS.exe` messen (`Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`), nicht das Working Set. Ab ca. 4 GB nach der laufenden Testdatei anhalten und den Nutzer um einen Neustart bitten. Genau eine Instanz (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`); nie eine fremde Instanz beenden. Toggle 10 und Integer-Einstellung 6 vor und nach Live-Läufen gleich (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); print(app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6))"`, erwartet `False 1`).
- **Git:** Branch `stufe-3a` (vom Stand nach Merge von PR #6 bzw. von `plan-stufe-3a`), kleine Commits je Task; Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **kein `git push` ohne Rückfrage**; nichts aus `auftraege/` committen; erzeugte SolidWorks-Dateien nie committen; immer gezielt `git add <dateien>`.
- **Subagents:** Implementer starten keine Subagents. Prüfer-Agent und Recherche-Workflow startet der Controller.

## Dateistruktur nach diesem Plan

```
schema/teil.schema.json                 + Feature-Typ referenz, Messpunkt {referenz}, pruefung.durchmesser_pruefen
schema/normtabelle.schema.json          neu: Schema der Normtabellen
swki/compiler/handler/referenz.py       neu: Handler "referenz"
swki/compiler/handler/muster.py         neue_referenzachse() herausgelöst
swki/compiler/handler/__init__.py       + referenz
swki/compiler/sw.py                     + ausblenden()
swki/compiler/topologie.py              + referenz_geometrie()
swki/compiler/anker.py                  + zylinder_durch_punkt()
swki/compiler/bauen.py                  _vorbereiten → vorbereiten (öffentlich, für normteile/bau.py)
swki/pruefung/geometrie.py              referenz trägt 0 zum Volumen bei
swki/pruefung/messen.py                 Messpunkt referenz, durchmesser()
swki/pruefung/bewertung.py              Messwerte.durchmesser, Prüfung durchmesser:<was>
swki/spec/laden.py                      Verweise über den Schlüssel "referenz"
swki/konfig.py, swki/rechner.py         + normteilbibliothek
swki/normteile/__init__.py              neu
swki/normteile/fehler.py                neu: Fehlercodes, NormteilFehler
swki/normteile/tabelle.py               neu: Normtabellen laden, prüfen, Regeln
swki/normteile/schluessel.py            neu: Anfrage auflösen
swki/normteile/erzeugen.py              neu: Spezifikation aus Vorlage, Prüfsummen, Befunde
swki/normteile/bau.py                   neu: Bau + Selbstprüfung in SolidWorks
swki/normteile/bibliothek.py            neu: Bibliothek (Cache)
swki/normteile/befehle.py               neu: swki normteil hole|tabellen-pruefen|liste|muster|urteil
swki/cli.py                             + Befehlsgruppe normteil
swki/wissen/normteile/iso4762.yaml …    Normtabellen (4)
swki/wissen/normteile/vorlagen/*.yaml   Bauvorlagen (4) + *.pruefer.json (Urteile)
spikes/s11_normteile.py                 Spike S11
docs/stufe3a/abgleich/<norm>.json       Rechercheergebnisse des Abgleichs
docs/stufe3a/ergebnisse.md              Ergebnisse 3a
.claude/skills/normteile/SKILL.md       neu
CLAUDE.md, config/rechner.beispiel.yaml, docs/superpowers/specs/2026-09-26-solidworks-ki-design.md (§8, §11)
tests/normteile/…, tests/live/test_live_referenz.py, test_live_durchmesser.py, test_live_normteile.py,
test_live_normteil_hole.py, test_live_normteile_stichprobe.py
```

`pyproject.toml` nimmt `swki/wissen/*.yaml` als Paketdaten; die Unterordner `wissen/normteile/**` werden in Task 4 ergänzt.

---

### Task 1: Spike S11 – Bezugsgeometrie, Messung am Schraubenbauweg, Werkstoffe (live)

**Files:**
- Create: `spikes/s11_normteile.py`
- Ergebnis: `docs/stufe0/ergebnisse/s11_normteile.json` (wird vom Spike geschrieben und committet)

**Interfaces:**
- Produces: Antworten auf vier Fragen, die Task 2, 3 und 7–9 voraussetzen: (1) Bezugsebene deckungsgleich (Constraint 4) und mit Abstand (8) lässt sich erzeugen; Normale = Elemente 6–8 von `Transform.ArrayData` (dritte Zeile), Ursprung = Elemente 9–11 (m); (2) Achse aus vorne ∩ rechts, `GetTypeName2` von Achse und Ebene; (3) der Schrauben-Bauweg (Rotation mit Mittellinie auf der Profilkante + Innensechskant) baut voll bestimmt und `flaeche_in_richtung` findet die Flächen für k, l, s, t eindeutig; (4) welche der Werkstoffe 1.1191, 1.7225, 1.4301, 1.0038, 1.3505 es gibt.

- [ ] **Step 1: Vorbedingungen prüfen**

SolidWorks 2025 läuft, genau eine Instanz, Einstellungen `False 1` (Befehle in den Global Constraints). Sonst anhalten und melden.

- [ ] **Step 2: `spikes/s11_normteile.py` schreiben**

```python
"""S11 (Stufe 3a): Bezugsgeometrie, Messung am Normteil-Bauweg, Werkstoffe.

Frage 1: Bezugsebene deckungsgleich zu "oben" (InsertRefPlane, swRefPlaneReferenceConstraint_Coincident = 4) und mit
         Abstand 12 mm (Distance = 8); Lage und Normale aus IRefPlane.Transform.ArrayData – ist die Normale die dritte
         Zeile (Elemente 6–8) und der Ursprung die Translation (Elemente 9–11, m)?
Frage 2: Bezugsachse aus vorne ∩ rechts (InsertAxis2), umbenannt und per FeatureByName wiedergefunden; GetTypeName2 von
         Achse und Ebene; GetRefAxisParams.
Frage 3: Bauweg ISO 4762 M8 x 30 (Rotation mit Mittellinie auf der Profilkante, Innensechskant als Schnitt): baut er
         voll bestimmt, und liefert flaeche_in_richtung die ebenen Flächen für k, l, s und t eindeutig?
Frage 4: Gibt es die Werkstoffe 1.1191, 1.7225, 1.4301, 1.0038, 1.3505 in den Materialdatenbanken?

Aufruf: .venv\\Scripts\\python.exe -m spikes.s11_normteile
"""

from pathlib import Path

from spikes._gemeinsam import lauf
from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.anker import AnkerFehler, flaeche_in_richtung
from swki.compiler.eigenschaften import finde_material, globale_variablen
from swki.compiler.fehler import fehler_dict
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.compiler.skizze import STANDARD
from swki.compiler.topologie import flaechen
from swki.konfig import lade_rechner
from swki.verbindung import in_mm, mm, verbinde

KOINZIDENT, ABSTAND = 4, 8  # swRefPlaneReferenceConstraints_e (swki api enum)
WERKSTOFFE = ["1.1191", "1.7225", "1.4301", "1.0038", "1.3505"]
W3 = "3**0.5"
M8X30 = {"d": 8, "dk": 13, "k": 8, "s": 6, "t": 4, "p": 1.25, "l": 30}
SCHRAUBE = [
    {"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [[0, "=-l"], ["=d/2-p", "=-l"], ["=d/2", "=p-l"], ["=d/2", 0], ["=dk/2", 0],
                                ["=dk/2", "=k-k/10"], ["=dk/2-k/10", "=k"], [0, "=k"]]}},
        {"mittellinie": {"von": [0, "=-l"], "bis": [0, "=k"]}}]}},
    {"id": "f2", "typ": "schnitt", "skizze": {"ebene": {"versatz": {"ebene": "oben", "abstand": "=k"}}, "elemente": [
        {"polygon": {"punkte": [["=s/2", f"=-s/(2*{W3})"], ["=s/2", f"=s/(2*{W3})"], [0, f"=s/{W3}"],
                                ["=-s/2", f"=s/(2*{W3})"], ["=-s/2", f"=-s/(2*{W3})"], [0, f"=-s/{W3}"]]}}]},
     "ende": {"typ": "blind", "tiefe": "=t"}},
]


def _ebene(model, art: int, abstand_mm: float, name: str) -> dict:
    sw.auswahl_leeren(model)
    sw.waehle(model, sw.standardebenen(model)[STANDARD["oben"]], 0)
    f = model.FeatureManager.InsertRefPlane(art, mm(abstand_mm), 0, 0.0, 0, 0.0)
    if f is None:
        return {"erzeugt": False}
    f.Name = name
    t = list(f.GetSpecificFeature2.Transform.ArrayData)
    return {"erzeugt": True, "typ": f.GetTypeName2, "wiedergefunden": model.FeatureByName(name) is not None,
            "array": t, "zeile3": t[6:9], "spalte3": [t[2], t[5], t[8]], "ursprung_mm": [in_mm(v) for v in t[9:12]]}


def _achse(model) -> dict:
    ebenen = sw.standardebenen(model)
    sw.auswahl_leeren(model)
    sw.waehle(model, ebenen[STANDARD["vorne"]], 0)
    sw.waehle(model, ebenen[STANDARD["rechts"]], 0, anhaengen=True)
    if not model.InsertAxis2(True):
        return {"erzeugt": False}
    f = sw.letztes_feature(model)
    f.Name = "EINBAU_ACHSE"
    p = list(f.GetSpecificFeature2.GetRefAxisParams)
    return {"erzeugt": True, "typ": f.GetTypeName2, "wiedergefunden": model.FeatureByName("EINBAU_ACHSE") is not None,
            "punkte_mm": [in_mm(v) for v in p]}


def _flaeche(fs, richtung: str) -> dict:
    try:
        f = flaeche_in_richtung(fs, richtung)
        return {"punkt": f.punkt, "normale": f.normale}
    except AnkerFehler as e:
        return {"fehler": str(e)}


def pruefen() -> dict:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    d: dict = {}
    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        d["frage1_deckungsgleich"] = _ebene(model, KOINZIDENT, 0.0, "EINBAU_EBENE")
        d["frage1_abstand_12"] = _ebene(model, ABSTAND, 12.0, "EINBAU_EBENE_2")
        d["frage2_achse"] = _achse(model)
    finally:
        sw.schliesse(app, model)

    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        spec = {"art": "teil", "name": "S11", "parameter": M8X30, "features": SCHRAUBE}
        ctx = Kontext(app, model, spec, Path("s11.yaml"), 0.1)
        globale_variablen(model, M8X30)
        fehler = baue_features(ctx, Protokoll("s11", "s11.yaml", 0, r.sw_jahr), alle_handler(), lambda c: sw.rebuild(c.model))
        d["frage3_fehler"] = fehler_dict(fehler) if fehler else None
        if fehler is None:
            f1, f2 = flaechen(ctx.ergebnis("f1").features[0]), flaechen(ctx.ergebnis("f2").features[0])
            d["frage3_flaechen"] = {"f1+y": _flaeche(f1, "+y"), "f1-y": _flaeche(f1, "-y"), "f2+x": _flaeche(f2, "+x"),
                                    "f2-x": _flaeche(f2, "-x"), "f2+y": _flaeche(f2, "+y")}
            d["frage3_zylinder_f1"] = sorted({round(z.radius, 6) for z in f1 if z.art == "zylinder"})
            d["frage3_erwartet"] = {"k": 8, "l": 30, "s": 6, "t": 4, "zylinderradien": [4.0, 6.5]}
    finally:
        sw.schliesse(app, model)

    datenbanken = list(app.GetMaterialDatabases or ())
    d["frage4_werkstoffe"] = {}
    for w in WERKSTOFFE:
        try:
            d["frage4_werkstoffe"][w] = finde_material(datenbanken, w)[1]
        except Exception as e:  # MATERIAL_UNBEKANNT
            d["frage4_werkstoffe"][w] = f"FEHLT: {e}"
    return d



if __name__ == "__main__":
    lauf("s11_normteile", pruefen)
```

- [ ] **Step 3: Spike ausführen**

```powershell
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe -m spikes.s11_normteile
```

Expected: `docs/stufe0/ergebnisse/s11_normteile.json` mit `"ok": true`.

- [ ] **Step 4: Auswerten und im Bericht beantworten**

Je Frage eine Zeile mit Beleg aus dem JSON:
1. Beide Ebenen erzeugt? `zeile3` der Ebene „oben“ = `[0, 1, 0]` (± 1e-9, Vorzeichen egal)? `ursprung_mm[1]` = 0 bzw. 12? Falls die Normale in `spalte3` statt `zeile3` steht: das ist die Antwort für Task 2 (dort die Indizes 2, 5, 8 verwenden).
2. `typ` der Achse und der Ebene (erwartet `"RefAxis"` und `"RefPlane"`), `wiedergefunden` true, Achse parallel zu Y durch x = z = 0.
3. `frage3_fehler` null; Abstand `f1+y` – Ursprung = 8 (k), `f1-y` – Ursprung = 30 (l), `f2+x`/`f2-x` 6 mm auseinander (s), `f1+y`/`f2+y` 4 mm (t); Zylinderradien von f1 = [4.0, 6.5]. Scheitert der Bau an der Mittellinie auf der Profilkante: die Mittellinie auf `von: [0, "=k"]`, `bis: [0, "=k+1"]` (außerhalb des Profils, kollinear) ändern, Spike erneut ausführen und das Ergebnis berichten – Task 7 übernimmt dann diese Form.
4. Je Werkstoff gefunden oder `FEHLT`. Fehlt einer: im Bericht Status DONE_WITH_CONCERNS mit der Liste; der Controller entscheidet einen Ersatz (Ledger) vor Task 7.

- [ ] **Step 5: Einstellungen nach dem Lauf lesen** (`False 1`), Private Bytes notieren.

- [ ] **Step 6: Commit**

```powershell
git add spikes/s11_normteile.py docs/stufe0/ergebnisse/s11_normteile.json
git commit -m "spike S11: Bezugsgeometrie, Messung am Schraubenbauweg, Werkstoffe" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Feature-Typ `referenz` (benannte Bezugsachse/-ebene)

**Files:**
- Modify: `schema/teil.schema.json` (Feature-`typ`-enum, `allOf`-Zweig, neues `$defs.f_referenz`)
- Create: `swki/compiler/handler/referenz.py`
- Modify: `swki/compiler/handler/__init__.py` (Import `referenz`), `swki/compiler/handler/muster.py` (`neue_referenzachse`), `swki/compiler/sw.py` (`ausblenden`), `swki/compiler/topologie.py` (`referenz_geometrie`), `swki/pruefung/geometrie.py` (`volumen_auto`)
- Test: `tests/spec/test_laden.py`, `tests/pruefung/test_geometrie.py`, `tests/live/test_live_referenz.py` (neu)

**Interfaces:**
- Consumes: Spike S11 Frage 1/2 (Indizes der Normale, Typnamen).
- Produces: Feature `{"id": <id>, "typ": "referenz", "achse": "x"|"y"|"z"}` oder `{"id", "typ": "referenz", "ebene": {"basis": "vorne"|"oben"|"rechts", "abstand"?: wert, "umkehren"?: bool}}`; der SW-Featurename ist die ID; `FeatureErgebnis([feature], richtung=<Einheitsvektor>)`. `topologie.referenz_geometrie(feature) -> tuple[str, Vektor, Vektor]` = `("achse", punkt_mm, richtung)` bzw. `("ebene", ursprung_mm, normale)`. `muster.neue_referenzachse(ctx, achse) -> (IFeature, richtung)`. `sw.ausblenden(model, feature)`.

- [ ] **Step 1: Failing tests – `tests/spec/test_laden.py` anhängen**

```python
@pytest.mark.parametrize("ref", [
    {"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"},
    {"id": "EINBAU_EBENE", "typ": "referenz", "ebene": {"basis": "oben"}},
    {"id": "EINBAU_EBENE_2", "typ": "referenz", "ebene": {"basis": "oben", "abstand": 20, "umkehren": True}},
])
def test_referenz_gueltig(tmp_path, ref):
    spec = _spec()
    spec["features"].append(ref)
    assert schema_befunde(spec) == [] and plausibel_befunde(spec, tmp_path) == []


@pytest.mark.parametrize("ref", [
    {"id": "R", "typ": "referenz"},                                             # weder achse noch ebene
    {"id": "R", "typ": "referenz", "achse": "y", "ebene": {"basis": "oben"}},   # beides
    {"id": "R", "typ": "referenz", "achse": "w"},
    {"id": "R", "typ": "referenz", "ebene": {"abstand": 5}},                    # basis fehlt
])
def test_referenz_ungueltig(ref):
    spec = _spec()
    spec["features"].append(ref)
    assert schema_befunde(spec) != []


def test_referenz_abstand_muss_positiv_sein(tmp_path):
    spec = _spec()
    spec["features"].append({"id": "R", "typ": "referenz", "ebene": {"basis": "oben", "abstand": -5}})
    assert any(b["pfad"].endswith("ebene.abstand") for b in plausibel_befunde(spec, tmp_path))
```

- [ ] **Step 2: Failing test – `tests/pruefung/test_geometrie.py` anhängen**

```python
def test_volumen_referenz_traegt_nichts_bei():
    spec = {"features": [
        {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
            {"rechteck": {"mitte": [0, 0], "breite": 10, "hoehe": 20}}]}, "ende": {"typ": "blind", "tiefe": 5}},
        {"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"},
        {"id": "EINBAU_EBENE", "typ": "referenz", "ebene": {"basis": "oben"}},
    ]}
    volumen, grund = volumen_auto(spec)
    assert volumen == pytest.approx(1000.0) and grund == "analytisch"
```

- [ ] **Step 3: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_laden.py tests/pruefung/test_geometrie.py -q`
Expected: FAIL (Schema kennt `referenz` nicht; `volumen_auto` meldet „referenz nicht analytisch berechenbar“).

- [ ] **Step 4: Schema**

In `schema/teil.schema.json` den Feature-`typ`-enum um `"referenz"` erweitern, im `allOf` des Features ergänzen:

```json
{"if": {"properties": {"typ": {"const": "referenz"}}}, "then": {"$ref": "#/$defs/f_referenz"}}
```

und unter `$defs`:

```json
"f_referenz": {
  "type": "object", "additionalProperties": false,
  "properties": {
    "id": true, "typ": true,
    "achse": {"enum": ["x", "y", "z"]},
    "ebene": {
      "type": "object", "required": ["basis"], "additionalProperties": false,
      "properties": {
        "basis": {"$ref": "#/$defs/standardebene"},
        "abstand": {"$ref": "#/$defs/wert"},
        "umkehren": {"type": "boolean"}
      }
    }
  },
  "oneOf": [{"required": ["achse"]}, {"required": ["ebene"]}]
}
```

- [ ] **Step 5: `volumen_auto`**

In `swki/pruefung/geometrie.py` in der Schleife von `volumen_auto` vor dem abschließenden `else`:

```python
        elif typ == "referenz":
            beitrag[f["id"]] = 0.0  # Bezugsgeometrie hat kein Volumen
```

- [ ] **Step 6: Unit-Tests grün**

Run: `.venv\Scripts\python.exe -m pytest tests/spec/test_laden.py tests/pruefung/test_geometrie.py -q` → PASS.

- [ ] **Step 7: `sw.ausblenden` und `muster.neue_referenzachse`**

In `swki/compiler/sw.py` (bei den übrigen Hilfen):

```python
def ausblenden(model, feature) -> None:
    """Bezugsgeometrie ausblenden, damit sie nicht in den Screenshots erscheint."""
    auswahl_leeren(model)
    feature.Select2(False, 0)
    model._FlagAsMethod("BlankRefGeom")
    model.BlankRefGeom()
    auswahl_leeren(model)
```

In `swki/compiler/handler/muster.py` `referenzachse` ersetzen durch:

```python
def neue_referenzachse(ctx, achse: str):
    """Referenzachse aus zwei Standardebenen anlegen und ausblenden; (IFeature, Richtung als Einheitsvektor)."""
    ebenen = sw.standardebenen(ctx.model)
    a, b = _EBENEN_DER_ACHSE[achse]
    sw.auswahl_leeren(ctx.model)
    sw.waehle(ctx.model, ebenen[STANDARD[a]], 0)
    sw.waehle(ctx.model, ebenen[STANDARD[b]], 0, anhaengen=True)
    if not ctx.model.InsertAxis2(True):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Referenzachse {achse} nicht erzeugt", schritt="achse")
    feature = sw.letztes_feature(ctx.model)
    sw.ausblenden(ctx.model, feature)
    p = feature.GetSpecificFeature2.GetRefAxisParams  # (x1, y1, z1, x2, y2, z2) in m
    d = differenz(tuple(in_mm(v) for v in p[3:6]), tuple(in_mm(v) for v in p[0:3]))
    return feature, tuple(c / laenge(d) for c in d)


def referenzachse(ctx, achse: str):
    """Referenzachse der Muster (IFeature, Richtung); je Teil nur einmal angelegt und "achse_<x|y|z>" benannt."""
    if achse not in ctx.achsen:
        feature, richtung = neue_referenzachse(ctx, achse)
        feature.Name = f"achse_{achse}"
        ctx.achsen[achse] = (feature, richtung)
    return ctx.achsen[achse]
```

- [ ] **Step 8: `topologie.referenz_geometrie`**

In `swki/compiler/topologie.py` (Importe `differenz`, `laenge`, `AnkerFehler` aus `swki.compiler.anker` und `REFERENZ_NICHT_GEFUNDEN` aus `swki.compiler.fehler` ergänzen, falls nicht vorhanden):

```python
REF_ACHSE, REF_EBENE = "RefAxis", "RefPlane"  # IFeature.GetTypeName2 (Spike S11 Frage 2)


def referenz_geometrie(feature) -> tuple[str, Vektor, Vektor]:
    """Bezugsachse → ("achse", Punkt, Richtung); Bezugsebene → ("ebene", Ursprung, Normale). Punkte in mm, Richtungen
    als Einheitsvektoren. Die Normale ist die dritte Zeile der Rotationsmatrix von IRefPlane.Transform (Spike S11)."""
    typ = feature.GetTypeName2
    if typ == REF_ACHSE:
        p = feature.GetSpecificFeature2.GetRefAxisParams
        a, b = _mm3(p[0:3]), _mm3(p[3:6])
        d = differenz(b, a)
        return "achse", a, tuple(c / laenge(d) for c in d)
    if typ == REF_EBENE:
        t = feature.GetSpecificFeature2.Transform.ArrayData
        n = (t[6], t[7], t[8])
        return "ebene", _mm3(t[9:12]), tuple(c / laenge(n) for c in n)
    raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"{feature.Name} ist keine Bezugsachse oder -ebene ({typ})")
```

Hat Spike S11 gezeigt, dass die Normale in der dritten Spalte steht oder die Typnamen anders heißen, die Werte aus dem Spike verwenden und den Kommentar anpassen. `Vektor` und `_mm3` gibt es in der Datei bzw. in `anker.py` – Import prüfen.

- [ ] **Step 9: Handler `swki/compiler/handler/referenz.py`**

```python
"""Handler "referenz" – benannte Bezugsachse oder -ebene, z. B. die Einbaureferenzen der Normteile (Spec 3a §5,
Spike S11). Achse: Schnitt zweier Standardebenen (wie die Musterachsen); Ebene: deckungsgleich zu einer Standardebene
oder mit Abstand. Beide werden ausgeblendet; der SW-Featurename ist die ID."""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.handler.muster import neue_referenzachse
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import NORMALE, REF_PLANE_ABSTAND, REF_PLANE_UMKEHREN, STANDARD

REF_PLANE_DECKUNGSGLEICH = 4  # swRefPlaneReferenceConstraint_Coincident (swki api enum)


def _ebene(ctx, f: dict):
    e = f["ebene"]
    sw.auswahl_leeren(ctx.model)
    sw.waehle(ctx.model, sw.standardebenen(ctx.model)[STANDARD[e["basis"]]], 0)
    if "abstand" in e:
        art = REF_PLANE_ABSTAND | (REF_PLANE_UMKEHREN if e.get("umkehren") else 0)
        feature = ctx.model.FeatureManager.InsertRefPlane(art, ctx.m(e["abstand"]), 0, 0.0, 0, 0.0)
    else:
        feature = ctx.model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0, 0, 0.0)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"referenz {f['id']}: Ebene nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    if "abstand" in e:
        ctx.verknuepfe(f"D1@{f['id']}", e["abstand"])
    normale = NORMALE[e["basis"]]
    return feature, tuple(-c for c in normale) if e.get("umkehren") else normale


@handler("referenz")
def referenz(ctx, f: dict) -> FeatureErgebnis:
    if "achse" in f:
        feature, richtung = neue_referenzachse(ctx, f["achse"])
        feature.Name = f["id"]
    else:
        feature, richtung = _ebene(ctx, f)
        sw.ausblenden(ctx.model, feature)
    return FeatureErgebnis([feature], richtung=richtung)
```

`swki/compiler/handler/__init__.py`: `referenz` in den Import aufnehmen (alphabetisch: `… normbohrung, referenz, rotation, skript`).

- [ ] **Step 10: Live-Test `tests/live/test_live_referenz.py` (neu)**

```python
import pytest

from swki.compiler.topologie import referenz_geometrie

from .bauhilfe import gebautes_teil

pytestmark = pytest.mark.sw


def test_referenzen_achse_und_ebenen():
    spec = {"art": "teil", "name": "T", "parameter": {"h": 20}, "features": [
        {"id": "f1", "typ": "extrusion", "skizze": {"ebene": "oben", "elemente": [
            {"rechteck": {"mitte": [0, 0], "breite": 40, "hoehe": 30}}]}, "ende": {"typ": "blind", "tiefe": "=h"}},
        {"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"},
        {"id": "EINBAU_EBENE", "typ": "referenz", "ebene": {"basis": "oben"}},
        {"id": "EINBAU_EBENE_2", "typ": "referenz", "ebene": {"basis": "oben", "abstand": "=h"}},
    ]}
    with gebautes_teil(spec) as (ctx, fehler, _):
        assert fehler is None
        art, punkt, richtung = referenz_geometrie(ctx.model.FeatureByName("EINBAU_ACHSE"))
        assert art == "achse" and abs(richtung[1]) == pytest.approx(1)
        assert punkt[0] == pytest.approx(0, abs=1e-6) and punkt[2] == pytest.approx(0, abs=1e-6)
        art, punkt, normale = referenz_geometrie(ctx.model.FeatureByName("EINBAU_EBENE"))
        assert art == "ebene" and abs(normale[1]) == pytest.approx(1) and punkt[1] == pytest.approx(0, abs=1e-6)
        art, punkt, normale = referenz_geometrie(ctx.model.FeatureByName("EINBAU_EBENE_2"))
        assert art == "ebene" and abs(normale[1]) == pytest.approx(1) and punkt[1] == pytest.approx(20, abs=1e-6)
        assert ctx.ergebnis("EINBAU_EBENE_2").richtung == pytest.approx((0, 1, 0))
```

(Falls `tests/live/` keine relativen Importe nutzt, den Import wie in den anderen Live-Dateien schreiben.)

- [ ] **Step 11: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → 349 + 9 = **358 passed** (3 gültig, 4 ungültig, 1 Abstand, 1 Volumen).
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → `"befunde": []`.
Live (SolidWorks): `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_referenz.py tests\live\test_live_muster.py --zeit 240` → alle OK (Musterachsen unverändert).

- [ ] **Step 12: Commit**

```powershell
git add schema/teil.schema.json swki/compiler/handler/referenz.py swki/compiler/handler/__init__.py swki/compiler/handler/muster.py swki/compiler/sw.py swki/compiler/topologie.py swki/pruefung/geometrie.py tests/spec/test_laden.py tests/pruefung/test_geometrie.py tests/live/test_live_referenz.py
git commit -m "compiler: Feature-Typ referenz (benannte Bezugsachse und -ebene)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Prüfung – Messpunkt `referenz` und `durchmesser_pruefen`

**Files:**
- Modify: `schema/teil.schema.json` (`messpunkt`, `pruefung`, neues `$defs.durchmesserpruefung`), `swki/spec/laden.py` (`_referenzen`), `swki/compiler/anker.py` (`zylinder_durch_punkt`), `swki/pruefung/bewertung.py`, `swki/pruefung/messen.py`
- Test: `tests/spec/test_laden.py`, `tests/compiler/test_anker.py`, `tests/pruefung/test_bewertung.py`, `tests/live/test_live_durchmesser.py` (neu)

**Interfaces:**
- Consumes: `topologie.referenz_geometrie` (Task 2).
- Produces: Messpunkt `{"referenz": <id>}` (Bezugsachse → Achse, Bezugsebene → Ebene) in `masse_pruefen`; `pruefung.durchmesser_pruefen: [{"was", "feature", "nahe": punkt3, "soll", "tol"?, "referenz"?: <id der Bezugsachse>}]` → Prüfung `durchmesser:<was>` mit `ist`, `soll`, `tol`, bei `referenz` zusätzlich `achsversatz`. `Messwerte.durchmesser: dict[str, dict | str]` (`{"durchmesser": float, "achse": Messgeometrie, "referenz"?: Messgeometrie}` oder Fehlertext). `anker.zylinder_durch_punkt(flaechen, punkt, tol_mm) -> Flaeche`.

- [ ] **Step 1: Failing tests – `tests/compiler/test_anker.py` anhängen** (Import `zylinder_durch_punkt`, `Flaeche`, `AnkerFehler` ergänzen)

```python
def _zyl(r, x=0.0):
    return Flaeche("zylinder", (x, 0.0, 0.0), achse=(0.0, 1.0, 0.0), radius=r)


def test_zylinder_durch_punkt():
    assert zylinder_durch_punkt([_zyl(4), _zyl(6.5)], (6.5, 10, 0), 0.1).radius == 6.5


def test_zylinder_durch_punkt_geteilte_flaeche():
    assert zylinder_durch_punkt([_zyl(4), _zyl(4)], (0, 3, 4), 0.1).radius == 4


def test_zylinder_durch_punkt_fehlt():
    with pytest.raises(AnkerFehler) as e:
        zylinder_durch_punkt([_zyl(4)], (5, 0, 0), 0.1)
    assert e.value.daten["code"] == REFERENZ_NICHT_GEFUNDEN


def test_zylinder_durch_punkt_mehrdeutig():
    with pytest.raises(AnkerFehler) as e:
        zylinder_durch_punkt([_zyl(4), _zyl(5, x=9)], (4, 0, 0), 0.1)
    assert e.value.daten["code"] == REFERENZ_MEHRDEUTIG
```

- [ ] **Step 2: Failing tests – `tests/pruefung/test_bewertung.py` anhängen**

```python
DM_SPEC = {**SPEC, "features": SPEC["features"] + [{"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"}],
           "pruefung": {"durchmesser_pruefen": [
               {"was": "d", "feature": "f1", "nahe": [5, 10, 0], "soll": 10, "referenz": "EINBAU_ACHSE"}]}}


def _dm(d=10.0, achspunkt=(0.0, 0.0, 0.0)):
    return {"d": {"durchmesser": d, "achse": Messgeometrie("achse", achspunkt, (0, 1, 0)),
                  "referenz": Messgeometrie("achse", (0, 5, 0), (0, -1, 0))}}


def test_durchmesser_ok():
    bericht = bewerte(DM_SPEC, _messwerte(durchmesser=_dm()), STANDARD)
    [p] = [p for p in bericht["pruefungen"] if p["id"] == "durchmesser:d"]
    assert bericht["bestanden"] and p["ok"] is True and p["ist"] == 10.0 and p["achsversatz"] == 0.0


@pytest.mark.parametrize("messung", [
    _dm(d=10.05),                                          # Durchmesser außerhalb 0,01
    _dm(achspunkt=(0.5, 0.0, 0.0)),                        # nicht koaxial zur Bezugsachse
    "REFERENZ_NICHT_GEFUNDEN: keine Zylinderfläche",       # Messung gescheitert
])
def test_durchmesser_mangel(messung):
    m = _messwerte(durchmesser=messung if isinstance(messung, dict) else {"d": messung})
    bericht = bewerte(DM_SPEC, m, STANDARD)
    assert [x["pruefung"] for x in bericht["maengel"]] == ["durchmesser:d"]
    assert bericht["maengel"][0]["knoten"] == ["f1"]
```

- [ ] **Step 3: Failing tests – `tests/spec/test_laden.py` anhängen**

```python
def test_pruefung_durchmesser_und_referenz_im_schema(tmp_path):
    spec = _spec()
    spec["features"].append({"id": "EINBAU_EBENE", "typ": "referenz", "ebene": {"basis": "oben"}})
    spec["pruefung"]["masse_pruefen"] = [
        {"was": "h", "von": {"referenz": "EINBAU_EBENE"}, "zu": {"feature": "f1", "flaeche": "+y"}, "soll": 20}]
    spec["pruefung"]["durchmesser_pruefen"] = [{"was": "d", "feature": "f2", "nahe": [0, 0, 0], "soll": 8}]
    assert schema_befunde(spec) == [] and plausibel_befunde(spec, tmp_path) == []


def test_unbekannte_referenz_in_pruefung(tmp_path):
    spec = _spec()
    spec["pruefung"]["masse_pruefen"] = [
        {"was": "x", "von": {"referenz": "EINBAU_EBENE"}, "zu": {"punkt": [0, 0, 0]}, "soll": 1}]
    spec["pruefung"]["durchmesser_pruefen"] = [{"was": "d", "feature": "f2", "nahe": [0, 0, 0], "soll": 8,
                                                "referenz": "EINBAU_ACHSE"}]
    meldungen = [b["meldung"] for b in plausibel_befunde(spec, tmp_path)]
    assert any("EINBAU_EBENE" in m for m in meldungen) and any("EINBAU_ACHSE" in m for m in meldungen)
```

Hinweis: In `GUELTIG` ist `f1` die Extrusion und `f2` eine Bohrung; passt ein Feature-Name nicht, den Namen korrigieren, nicht die Erwartung.

- [ ] **Step 4: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_anker.py tests/pruefung/test_bewertung.py tests/spec/test_laden.py -q`
Expected: FAIL (`ImportError: zylinder_durch_punkt`, `Messwerte` ohne `durchmesser`, Schema kennt `referenz`/`durchmesser_pruefen` nicht).

- [ ] **Step 5: Schema**

`$defs.messpunkt.oneOf` um eine vierte Form ergänzen:

```json
{"type": "object", "required": ["referenz"], "additionalProperties": false,
 "properties": {"referenz": {"$ref": "#/$defs/id"}}}
```

In `$defs.pruefung.properties`:

```json
"durchmesser_pruefen": {"type": "array", "items": {"$ref": "#/$defs/durchmesserpruefung"}}
```

und unter `$defs`:

```json
"durchmesserpruefung": {
  "type": "object", "required": ["was", "feature", "nahe", "soll"], "additionalProperties": false,
  "properties": {
    "was": {"type": "string", "minLength": 1},
    "feature": {"$ref": "#/$defs/id"},
    "nahe": {"$ref": "#/$defs/punkt3"},
    "soll": {"$ref": "#/$defs/wert"},
    "tol": {"type": "number", "exclusiveMinimum": 0},
    "referenz": {"$ref": "#/$defs/id"}
  }
}
```

- [ ] **Step 6: Verweise – `swki/spec/laden.py` `_referenzen`**

Die erste Bedingung erweitern, damit `referenz` (Messpunkt, Durchmesserprüfung) wie `feature` als Verweis gilt:

```python
            if k in ("feature", "referenz") and isinstance(v, str):
                yield [*pfad, k], v
```

Docstring: `"""Liefert (pfad, feature-id) für alle Verweise auf Features ("feature", "referenz" und "features")."""`

- [ ] **Step 7: `swki/compiler/anker.py` – `zylinder_durch_punkt`** (nach `zylinder_zu_punkten`)

```python
def zylinder_durch_punkt(flaechen: list[Flaeche], punkt: Vektor, tol_mm: float) -> Flaeche:
    """Zylinderfläche, auf deren Mantel `punkt` liegt (|Abstand Punkt–Achse − Radius| ≤ tol_mm). SolidWorks teilt einen
    Vollzylinder oft in zwei Flächen; Treffer mit gleichem Radius gelten als eine Fläche."""
    treffer = [f for f in flaechen if f.art == "zylinder"
               and abs(punkt_achse_abstand(punkt, f.punkt, f.achse) - f.radius) <= tol_mm]
    if not treffer:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine Zylinderfläche durch {punkt}")
    if len({round(f.radius, 6) for f in treffer}) > 1:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{len(treffer)} Zylinderflächen mit verschiedenen Radien durch {punkt}")
    return treffer[0]
```

- [ ] **Step 8: `swki/pruefung/bewertung.py`**

`Messwerte` um ein Feld nach `koerper` ergänzen:

```python
    durchmesser: dict[str, dict | str] = field(default_factory=dict)  # was → {"durchmesser", "achse", "referenz"?} oder Fehlertext
```

In `bewerte` direkt nach der Schleife über `masse_pruefen`:

```python
    for dp in pr.get("durchmesser_pruefen", []):
        pid, knoten = f"durchmesser:{dp['was']}", [dp["feature"]]
        soll, tol = auswerten(dp["soll"], p), dp.get("tol", _TOL_MASS)
        ist = m.durchmesser.get(dp["was"], "Messung fehlt")
        if isinstance(ist, str):
            ergebnisse.append(_pruefung(pid, False, soll=soll, hinweis=ist, knoten=knoten))
            continue
        ok = abs(ist["durchmesser"] - soll) <= tol
        daten = {"ist": ist["durchmesser"], "soll": soll, "tol": tol}
        if "referenz" in dp:
            try:
                daten["achsversatz"] = round(abstand(ist["achse"], ist["referenz"]), 6)
                ok = ok and daten["achsversatz"] <= tol
            except NichtMessbar as e:
                ok, daten["hinweis"] = False, f"nicht koaxial zu {dp['referenz']}: {e}"
        ergebnisse.append(_pruefung(pid, ok, **daten, knoten=knoten))
```

- [ ] **Step 9: `swki/pruefung/messen.py`**

Importe ergänzen: `zylinder_durch_punkt` (aus `swki.compiler.anker`), `referenz_geometrie` (aus `swki.compiler.topologie`).

In `_messgeometrie` direkt nach dem `punkt`-Zweig:

```python
    if "referenz" in mp:
        if mp["referenz"] not in ctx.ergebnisse:
            raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Referenz {mp['referenz']!r} fehlt im Teil")
        return Messgeometrie(*referenz_geometrie(ctx.ergebnis(mp["referenz"]).features[0]))
```

Neue Funktion nach `messpunkte`:

```python
def durchmesser(ctx, spec: dict) -> dict[str, dict | str]:
    """Durchmesser je pruefung.durchmesser_pruefen: Zylinderfläche des Features, auf deren Mantel `nahe` liegt; mit
    `referenz` zusätzlich die Bezugsachse (Koaxialität bewertet bewertung.bewerte)."""
    ergebnis = {}
    for dp in spec.get("pruefung", {}).get("durchmesser_pruefen", []):
        try:
            for fid in (dp["feature"], dp.get("referenz")):
                if fid is not None and fid not in ctx.ergebnisse:
                    raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Feature {fid!r} fehlt im Teil")
            nahe = tuple(ctx.wert(v) for v in dp["nahe"])
            z = zylinder_durch_punkt(flaechen(ctx.ergebnis(dp["feature"]).features[0]), nahe, ctx.tol_mm)
            n = laenge(z.achse)
            wert = {"durchmesser": round(2 * z.radius, 6),
                    "achse": Messgeometrie("achse", z.punkt, tuple(c / n for c in z.achse))}
            if "referenz" in dp:
                wert["referenz"] = Messgeometrie(*referenz_geometrie(ctx.ergebnis(dp["referenz"]).features[0]))
            ergebnis[dp["was"]] = wert
        except BauFehler as e:
            ergebnis[dp["was"]] = f"{e.code}: {e}"
    return ergebnis
```

In `messe` beim Erzeugen von `Messwerte` ergänzen: `durchmesser=durchmesser(ctx, ctx.spec),` (die Durchmesserprüfung gehört zum Bauweg, nicht zur Freigabe – daher `ctx.spec` wie bei `messpunkte`).

Prüfe, wie `BauFehler` den Code bereitstellt (`e.code` wird in `messpunkte` schon so benutzt).

- [ ] **Step 10: Unit-Tests grün**

Run: `.venv\Scripts\python.exe -m pytest tests/compiler/test_anker.py tests/pruefung tests/spec -q` → PASS.

- [ ] **Step 11: Live-Test `tests/live/test_live_durchmesser.py` (neu)**

```python
import copy

import pytest

from swki.pruefung.bewertung import bewerte
from swki.pruefung.messen import messe

from .bauhilfe import gebautes_teil

pytestmark = pytest.mark.sw
STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}}
SPEC = {"art": "teil", "name": "T", "parameter": {"d": 8, "D": 20, "h": 12}, "features": [
    {"id": "f1", "typ": "rotation", "skizze": {"ebene": "vorne", "elemente": [
        {"polygon": {"punkte": [["=d/2", 0], ["=D/2", 0], ["=D/2", "=h"], ["=d/2", "=h"]]}},
        {"mittellinie": {"von": [0, 0], "bis": [0, 10]}}]}},
    {"id": "EINBAU_ACHSE", "typ": "referenz", "achse": "y"},
    {"id": "EINBAU_EBENE", "typ": "referenz", "ebene": {"basis": "oben"}}],
    "pruefung": {
        "huellquader": ["=D", "=h", "=D"], "volumen": {"soll": "auto"},
        "masse_pruefen": [
            {"was": "h", "von": {"referenz": "EINBAU_EBENE"}, "zu": {"feature": "f1", "flaeche": "+y"}, "soll": "=h"}],
        "durchmesser_pruefen": [
            {"was": "d", "feature": "f1", "nahe": ["=d/2", "=h/2", 0], "soll": "=d", "referenz": "EINBAU_ACHSE"},
            {"was": "D", "feature": "f1", "nahe": ["=D/2", "=h/2", 0], "soll": "=D", "referenz": "EINBAU_ACHSE"}]}}


def test_durchmesser_und_referenzen_messen():
    with gebautes_teil(SPEC) as (ctx, fehler, _):
        assert fehler is None
        messwerte = messe(ctx)
    bericht = bewerte(SPEC, messwerte, STANDARD)
    assert bericht["bestanden"], bericht["maengel"]
    ids = {p["id"]: p["ok"] for p in bericht["pruefungen"]}
    assert all(ids[x] is True for x in ("durchmesser:d", "durchmesser:D", "mass:h", "huellquader", "volumen"))
    falsch = copy.deepcopy(SPEC)
    falsch["pruefung"]["durchmesser_pruefen"][0]["soll"] = "=d+0.1"
    assert [x["pruefung"] for x in bewerte(falsch, messwerte, STANDARD)["maengel"]] == ["durchmesser:d"]
```

- [ ] **Step 12: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → vorher + **10** (4 Anker, 1 + 3 Bewertung, 2 Laden).
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.
Live: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_durchmesser.py tests\live\test_live_pruefen.py --zeit 240` → alle OK.

- [ ] **Step 13: Commit**

```powershell
git add schema/teil.schema.json swki/spec/laden.py swki/compiler/anker.py swki/pruefung/bewertung.py swki/pruefung/messen.py tests/compiler/test_anker.py tests/pruefung/test_bewertung.py tests/spec/test_laden.py tests/live/test_live_durchmesser.py
git commit -m "pruefung: Messpunkt referenz und durchmesser_pruefen (koaxial zur Bezugsachse)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Konfiguration `normteilbibliothek` und Normtabellen-Modul

**Files:**
- Modify: `swki/konfig.py`, `swki/rechner.py`, `config/rechner.beispiel.yaml`, `pyproject.toml` (Paketdaten)
- Create: `schema/normtabelle.schema.json`, `swki/normteile/__init__.py`, `swki/normteile/fehler.py`, `swki/normteile/tabelle.py`
- Create (Testdaten): `tests/normteile/__init__.py`, `tests/normteile/daten/iso9999.yaml`, `tests/normteile/daten/vorlagen/iso9999.yaml`
- Test: `tests/test_konfig.py`, `tests/test_rechner.py`, `tests/normteile/test_tabelle.py`

**Interfaces:**
- Produces: `Rechner.normteilbibliothek: Path | None = None` (letztes Feld). Normtabellen-Feld `entscheidung` je Größe (Nutzerentscheidung ersetzt die Quellenpflicht). `swki/normteile/fehler.py`: Codes `NORMTEIL_UNBEKANNT`, `NORMLAENGE_UNGUELTIG`, `NORMVARIANTE_UNBEKANNT`, `NORMTEIL_GESPERRT`, `NORMTABELLE_UNGUELTIG`, `NORMVORLAGE_UNGEPRUEFT`, `NORMTEIL_PRUEFUNG`; `NormteilFehler(code, meldung, **daten)` mit `daten = {"code": code, **daten}`. `swki/normteile/tabelle.py`: `ORDNER`, `SCHEMA`, `norm_datei(norm) -> str`, `normen(ordner=ORDNER) -> list[str]`, `lade_normtabelle(norm, ordner=ORDNER) -> dict`, `regel_erfuellt(regel, masse) -> bool`, `tabellen_befunde(t, ordner=ORDNER) -> list[dict]`, `pruefe_tabelle(t, ordner=ORDNER) -> None`.

- [ ] **Step 1: Testdaten anlegen**

`tests/normteile/__init__.py` leer.

`tests/normteile/daten/iso9999.yaml`:

```yaml
# Testtabelle für Unit-Tests (keine echte Norm).
norm: ISO 9999
benennung: Testring
vorlage: vorlagen/iso9999.yaml
parameter: [a, b]
laenge: true
varianten:
  "8.8": {material: "1.1191"}
  A2: {material: "1.4301"}
vorgabe_variante: "8.8"
groessen:
  M5: {masse: {a: 5, b: 10}, laengen: [10, 12, 16], status: abgeglichen}
  M6: {masse: {a: 6, b: 12}, laengen: [10, 12, 16, 20], status: abgeglichen}
  M8: {masse: {a: 8, b: 16}, laengen: [12, 16, 20], status: gesperrt, grund: "b: Quelle X 16, Quelle Y 15"}
quellen:
  - {url: "https://beispiel.invalid/a", abgerufen: "2026-10-02", groessen: [M5, M6]}
  - {url: "https://beispiel.invalid/b", abgerufen: "2026-10-02", groessen: [M5, M6, M8]}
regeln: ["b > a"]
```

`tests/normteile/daten/vorlagen/iso9999.yaml` (wird erst ab Task 2 gültig; hier nur als Datei nötig):

```yaml
# Testvorlage: Rohr Innen-Ø a, Außen-Ø b, Länge l; Achse = Modell-Y.
art: teil
name: ISO9999_Muster
parameter: {a: 5, b: 10, l: 10}
features:
  - id: f1
    typ: rotation
    skizze:
      ebene: vorne
      elemente:
        - polygon: {punkte: [["=a/2", 0], ["=b/2", 0], ["=b/2", "=l"], ["=a/2", "=l"]]}
        - mittellinie: {von: [0, 0], bis: [0, 10]}
  - {id: EINBAU_ACHSE, typ: referenz, achse: y}
  - {id: EINBAU_EBENE, typ: referenz, ebene: {basis: oben}}
pruefung:
  huellquader: ["=b", "=l", "=b"]
  volumen: {soll: auto}
```

- [ ] **Step 2: Failing tests – `tests/normteile/test_tabelle.py` (neu)**

```python
import copy
from pathlib import Path

import pytest

from swki.normteile.fehler import NormteilFehler
from swki.normteile.tabelle import lade_normtabelle, norm_datei, regel_erfuellt, tabellen_befunde

DATEN = Path(__file__).parent / "daten"


def _tabelle():
    return lade_normtabelle("ISO 9999", DATEN)


@pytest.mark.parametrize("text", ["ISO 9999", "ISO9999", "iso9999", "iso-9999"])
def test_norm_datei(text):
    assert norm_datei(text) == "iso9999"


def test_laden_normalisiert_schluessel():
    t = _tabelle()
    assert list(t["groessen"]) == ["M5", "M6", "M8"]
    assert t["vorgabe_variante"] == "8.8" and set(t["varianten"]) == {"8.8", "A2"}
    assert t["quellen"][0]["abgerufen"] == "2026-10-02"


def test_unbekannte_norm():
    with pytest.raises(NormteilFehler) as e:
        lade_normtabelle("ISO 1", DATEN)
    assert e.value.daten["code"] == "NORMTEIL_UNBEKANNT" and "iso9999" in str(e.value)


def test_testtabelle_ohne_befund():
    assert tabellen_befunde(_tabelle(), DATEN) == []


@pytest.mark.parametrize(("regel", "masse", "ok"), [
    ("b > a", {"a": 5, "b": 10}, True),
    ("b > a", {"a": 10, "b": 10}, False),
    ("b >= a", {"a": 10, "b": 10}, True),
    ("a == b/2", {"a": 5, "b": 10}, True),
    ("a*2 < b", {"a": 5, "b": 10}, False),
    ("a <= 3**0.5", {"a": 1.7}, True),
])
def test_regel(regel, masse, ok):
    assert regel_erfuellt(regel, masse) is ok


def _befunde(aendern):
    t = copy.deepcopy(_tabelle())
    aendern(t)
    return tabellen_befunde(t, DATEN)


@pytest.mark.parametrize(("aendern", "pfad"), [
    (lambda t: t["groessen"]["M6"]["masse"].update(b=5), "groessen.M6.masse"),          # Regel b > a verletzt
    (lambda t: t["groessen"]["M6"]["masse"].pop("b"), "groessen.M6.masse"),             # Maß fehlt
    (lambda t: t["groessen"]["M6"].update(laengen=[12, 10]), "groessen.M6.laengen"),    # nicht aufsteigend
    (lambda t: t["groessen"]["M6"].pop("laengen"), "groessen.M6"),                      # laenge: true ohne laengen
    (lambda t: t["groessen"]["M6"]["masse"].update(a=4.5), "parameter.a"),              # fällt mit der Größe
    (lambda t: t.update(vorgabe_variante="10.9"), "vorgabe_variante"),
    (lambda t: t.update(vorlage="vorlagen/fehlt.yaml"), "vorlage"),
    (lambda t: t["quellen"].pop(0), "groessen.M5.status"),                              # nur noch 1 Quelle
    (lambda t: t["regeln"].append("a b"), "regeln"),
])
def test_tabellenbefunde(aendern, pfad):
    assert pfad in [b["pfad"] for b in _befunde(aendern)]


def test_gesperrt_braucht_grund():
    befunde = _befunde(lambda t: t["groessen"]["M8"].pop("grund"))
    assert befunde and befunde[0]["pfad"].startswith("groessen")


def test_nutzerentscheidung_ersetzt_quellen():
    def entscheiden(t):
        t["quellen"].pop(0)
        t["groessen"]["M5"]["entscheidung"] = "Nutzer 2026-10-05: b = 10 (Quelle A 10, Quelle B 10.5)"
    assert "groessen.M5.status" not in [b["pfad"] for b in _befunde(entscheiden)]
```

`tests/test_konfig.py` anhängen (Importe `Path`, `lade_rechner` prüfen):

```python
def test_normteilbibliothek_optional(tmp_path):
    pfad = tmp_path / "rechner.yaml"
    grund = "sw_jahr: 2025\ninstallationsordner: C:/SW\nvorlage_teil: C:/t.prtdot\narbeitsordner: C:/arbeit\n"
    pfad.write_text(grund, encoding="utf-8")
    assert lade_rechner(pfad).normteilbibliothek is None
    pfad.write_text(grund + "normteilbibliothek: C:/bib\n", encoding="utf-8")
    assert lade_rechner(pfad).normteilbibliothek == Path("C:/bib")
```

`tests/test_rechner.py`: im vorhandenen Test zu `erkenne` (bzw. `rechner init`) zusätzlich zusichern, dass `normteilbibliothek == arbeitsordner.parent / "normteile"` ist (der Arbeitsordner ist `swki_home() / "arbeit"`). Gibt es keinen solchen Test, einen kleinen ergänzen, der `erkenne` mit dem dort vorhandenen Registry-Fake aufruft.

- [ ] **Step 3: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/normteile tests/test_konfig.py tests/test_rechner.py -q`
Expected: FAIL (`ModuleNotFoundError: swki.normteile`, `Rechner` ohne `normteilbibliothek`).

- [ ] **Step 4: Konfiguration**

`swki/konfig.py`: in `Rechner` als letztes Feld `normteilbibliothek: Path | None = None`; `_PFADFELDER` um `"normteilbibliothek"` erweitern (die Schleife in `lade_rechner` setzt fehlende Schlüssel auf `None`).
`swki/rechner.py`: in `erkenne` neben `arbeitsordner=swki_home() / "arbeit",` die Zeile `normteilbibliothek=swki_home() / "normteile",` ergänzen.
`config/rechner.beispiel.yaml`: Zeile `normteilbibliothek: 'C:\Users\<Benutzer>\.swki\normteile'` ans Ende.
`pyproject.toml`: unter `[tool.setuptools.package-data]` `swki = [...]` um `"wissen/normteile/*.yaml", "wissen/normteile/vorlagen/*.yaml", "wissen/normteile/vorlagen/*.json"` ergänzen.

- [ ] **Step 5: `schema/normtabelle.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Normtabelle eines Normteils (swki/wissen/normteile/<norm>.yaml, Spec 3a §4)",
  "type": "object",
  "required": ["norm", "benennung", "vorlage", "parameter", "laenge", "varianten", "vorgabe_variante", "groessen",
               "quellen", "regeln"],
  "additionalProperties": false,
  "properties": {
    "norm": {"type": "string", "pattern": "^(ISO|DIN|EN) [0-9]+(-[0-9]+)?$"},
    "benennung": {"type": "string", "minLength": 1},
    "ersetzt": {"type": "string"},
    "vorlage": {"type": "string", "pattern": "^vorlagen/[a-z0-9]+\\.yaml$"},
    "parameter": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"}},
    "laenge": {"type": "boolean"},
    "varianten": {
      "type": "object", "minProperties": 1,
      "additionalProperties": {"type": "object", "required": ["material"], "additionalProperties": false,
                               "properties": {"material": {"type": "string", "minLength": 1}}}
    },
    "vorgabe_variante": {"type": "string"},
    "groessen": {"type": "object", "minProperties": 1, "additionalProperties": {"$ref": "#/$defs/groesse"}},
    "quellen": {"type": "array", "items": {"$ref": "#/$defs/quelle"}},
    "regeln": {"type": "array", "items": {"type": "string", "minLength": 3}},
    "hinweise": {"type": "array", "items": {"type": "string"}}
  },
  "$defs": {
    "groesse": {
      "type": "object", "required": ["masse", "status"], "additionalProperties": false,
      "properties": {
        "masse": {"type": "object", "minProperties": 1, "additionalProperties": {"type": "number", "exclusiveMinimum": 0}},
        "laengen": {"type": "array", "minItems": 1, "items": {"type": "number", "exclusiveMinimum": 0}},
        "status": {"enum": ["abgeglichen", "gesperrt"]},
        "grund": {"type": "string", "minLength": 1},
        "entscheidung": {"type": "string", "minLength": 1}
      },
      "allOf": [{"if": {"properties": {"status": {"const": "gesperrt"}}}, "then": {"required": ["grund"]}}]
    },
    "quelle": {
      "type": "object", "required": ["url", "abgerufen", "groessen"], "additionalProperties": false,
      "properties": {
        "url": {"type": "string", "pattern": "^https?://"},
        "titel": {"type": "string"},
        "abgerufen": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
        "groessen": {"type": "array", "items": {"type": "string"}}
      }
    }
  }
}
```

- [ ] **Step 6: `swki/normteile/__init__.py` und `swki/normteile/fehler.py`**

`__init__.py`: `"""Normteile: Normtabellen, Bauvorlagen, Selbstprüfung und Bibliothek (Spec 3a)."""`

`fehler.py`:

```python
"""Fehlercodes der Normteile (Spec 3a §8)."""

from swki.cli import SwkiFehler

NORMTEIL_UNBEKANNT = "NORMTEIL_UNBEKANNT"
NORMLAENGE_UNGUELTIG = "NORMLAENGE_UNGUELTIG"
NORMVARIANTE_UNBEKANNT = "NORMVARIANTE_UNBEKANNT"
NORMTEIL_GESPERRT = "NORMTEIL_GESPERRT"
NORMTABELLE_UNGUELTIG = "NORMTABELLE_UNGUELTIG"
NORMVORLAGE_UNGEPRUEFT = "NORMVORLAGE_UNGEPRUEFT"
NORMTEIL_PRUEFUNG = "NORMTEIL_PRUEFUNG"


class NormteilFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str, **daten):
        super().__init__(meldung)
        self.daten = {"code": code, **daten}
```

- [ ] **Step 7: `swki/normteile/tabelle.py`**

```python
"""Normtabellen der Normteile (swki/wissen/normteile/<norm>.yaml, Spec 3a §4): laden, Schema, Regeln, Quellen."""

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from swki.konfig import PROJEKT
from swki.normteile.fehler import NORMTABELLE_UNGUELTIG, NORMTEIL_UNBEKANNT, NormteilFehler
from swki.spec.ausdruck import AusdruckFehler, auswerten
from swki.spec.normen import groesse_text

ORDNER = PROJEKT / "swki" / "wissen" / "normteile"
SCHEMA = PROJEKT / "schema" / "normtabelle.schema.json"
_REGEL = re.compile(r"^(.+?)\s*(<=|>=|==|<|>)\s*(.+)$")
_EPS = 1e-9
_VERGLEICHE = {
    "<": lambda a, b: a < b - _EPS,
    "<=": lambda a, b: a <= b + _EPS,
    ">": lambda a, b: a > b + _EPS,
    ">=": lambda a, b: a >= b - _EPS,
    "==": lambda a, b: abs(a - b) <= _EPS,
}


def norm_datei(norm: str) -> str:
    """Dateiname ohne Endung: "ISO 4762", "ISO4762", "iso-4762" → "iso4762"."""
    return re.sub(r"[\s_-]+", "", norm).lower()


def normen(ordner: Path = ORDNER) -> list[str]:
    return sorted(p.stem for p in ordner.glob("*.yaml"))


def lade_normtabelle(norm: str, ordner: Path = ORDNER) -> dict:
    """Normtabelle; Größen, Varianten und Datumsangaben als Text (YAML liest 8, 8.8 und Daten sonst als Zahl/Datum)."""
    pfad = ordner / f"{norm_datei(norm)}.yaml"
    if not pfad.is_file():
        raise NormteilFehler(NORMTEIL_UNBEKANNT,
                             f"Norm {norm!r} unbekannt; vorhanden: {', '.join(normen(ordner)) or 'keine'}")
    t = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    t["groessen"] = {groesse_text(g): z for g, z in (t.get("groessen") or {}).items()}
    t["varianten"] = {str(v): w for v, w in (t.get("varianten") or {}).items()}
    if "vorgabe_variante" in t:
        t["vorgabe_variante"] = str(t["vorgabe_variante"])
    for q in t.get("quellen") or []:
        q["abgerufen"] = str(q.get("abgerufen"))
        q["groessen"] = [groesse_text(g) for g in q.get("groessen") or []]
    return t


def regel_erfuellt(regel: str, masse: dict) -> bool:
    """Regel wie "dk > d" über die Maße einer Größe (Ausdruckssyntax der Spezifikation, ohne führendes "=")."""
    treffer = _REGEL.match(regel.strip())
    if not treffer:
        raise AusdruckFehler(f"Regel {regel!r}: Vergleich (<, <=, >, >=, ==) fehlt")
    links, op, rechts = treffer.groups()
    return _VERGLEICHE[op](auswerten(f"={links}", masse), auswerten(f"={rechts}", masse))


def tabellen_befunde(t: dict, ordner: Path = ORDNER) -> list[dict]:
    """Schema, Vorlage, Varianten, Maßnamen, Längenreihen, Regeln, „Maße steigen mit der Größe“, Quellenpflicht
    (≥ 2 Quellen je abgeglichener Größe; eine dokumentierte Nutzerentscheidung `entscheidung` ersetzt sie)."""
    schema = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    befunde = [{"pfad": "/".join(map(str, f.absolute_path)) or "(wurzel)", "meldung": f.message}
               for f in schema.iter_errors(t)]
    if befunde:
        return befunde
    if not (ordner / t["vorlage"]).is_file():
        befunde.append({"pfad": "vorlage", "meldung": f"Vorlage {t['vorlage']} fehlt"})
    if t["vorgabe_variante"] not in t["varianten"]:
        befunde.append({"pfad": "vorgabe_variante", "meldung": f"{t['vorgabe_variante']!r} ist keine Variante"})
    regeln = []
    for regel in t["regeln"]:
        if _REGEL.match(regel.strip()):
            regeln.append(regel)
        else:
            befunde.append({"pfad": "regeln", "meldung": f"Regel {regel!r}: Vergleich (<, <=, >, >=, ==) fehlt"})
    namen = set(t["parameter"])
    for g, z in t["groessen"].items():
        pfad = f"groessen.{g}"
        if set(z["masse"]) != namen:
            befunde.append({"pfad": f"{pfad}.masse", "meldung": f"Maße {sorted(z['masse'])} ≠ parameter {sorted(namen)}"})
            continue
        if t["laenge"] != ("laengen" in z):
            befunde.append({"pfad": pfad, "meldung": "laengen " + ("fehlt" if t["laenge"] else "nur bei laenge: true")})
        laengen = z.get("laengen", [])
        if laengen != sorted(set(laengen)):
            befunde.append({"pfad": f"{pfad}.laengen", "meldung": "Längenreihe muss aufsteigend und ohne Doppel sein"})
        for regel in regeln:
            try:
                if not regel_erfuellt(regel, z["masse"]):
                    befunde.append({"pfad": f"{pfad}.masse", "meldung": f"Regel {regel!r} verletzt ({z['masse']})"})
            except AusdruckFehler as e:
                befunde.append({"pfad": f"{pfad}.masse", "meldung": str(e)})
    for name in sorted(namen):
        werte = [z["masse"].get(name) for z in t["groessen"].values()]
        if None not in werte and any(b < a for a, b in zip(werte, werte[1:])):
            befunde.append({"pfad": f"parameter.{name}", "meldung": f"{name} fällt mit der Größe: {werte}"})
    belegt: dict[str, int] = {}
    for q in t["quellen"]:
        for g in q["groessen"]:
            belegt[g] = belegt.get(g, 0) + 1
    for g, z in t["groessen"].items():
        if z["status"] == "abgeglichen" and belegt.get(g, 0) < 2 and not z.get("entscheidung"):
            befunde.append({"pfad": f"groessen.{g}.status",
                            "meldung": f"abgeglichen, aber nur {belegt.get(g, 0)} Quelle(n)"})
    return befunde


def pruefe_tabelle(t: dict, ordner: Path = ORDNER) -> None:
    if befunde := tabellen_befunde(t, ordner):
        raise NormteilFehler(NORMTABELLE_UNGUELTIG, f"Normtabelle {t.get('norm')}: {len(befunde)} Befund(e)",
                             befunde=befunde)
```

- [ ] **Step 8: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/normteile tests/test_konfig.py tests/test_rechner.py -q` → PASS.
Run: `.venv\Scripts\python.exe -m pytest -q` → vorher + **26** (4 + 1 + 1 + 1 + 6 Regeln + 9 Befunde + 1 gesperrt + 1 Entscheidung + 1 Konfig + 1 Rechner; tatsächliche Zahl berichten).

- [ ] **Step 9: Commit**

```powershell
git add swki/konfig.py swki/rechner.py config/rechner.beispiel.yaml pyproject.toml schema/normtabelle.schema.json swki/normteile/__init__.py swki/normteile/fehler.py swki/normteile/tabelle.py tests/normteile tests/test_konfig.py tests/test_rechner.py
git commit -m "normteile: Normtabellen (Schema, Regeln, Quellenpflicht), Konfiguration normteilbibliothek" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Anfrage auflösen und Spezifikation erzeugen

**Files:**
- Create: `swki/normteile/schluessel.py`, `swki/normteile/erzeugen.py`
- Test: `tests/normteile/test_erzeugen.py`

**Interfaces:**
- Consumes: `tabelle.lade_normtabelle`, `norm_datei`, `ORDNER` (Task 4); `spec.laden.schema_befunde`, `plausibel_befunde`; `spec.hinweise.feste_masse`.
- Produces: `schluessel.Anfrage(norm: str, groesse: str, laenge: float | None, variante: str)` (frozen) mit Properties `bezeichnung` („M8 x 30“) und `schluessel` („ISO4762_M8x30_8_8“); `naechste_laengen(laengen, laenge) -> {"darunter", "darueber"}`; `loese_auf(norm, groesse, variante=None, ordner=ORDNER) -> (tabelle, Anfrage)`. `erzeugen.vorlage_text(t, ordner=ORDNER) -> str`, `vorlage_pruefsumme(text) -> str`, `teil_pruefsumme(t, a, text) -> str`, `benennung(t, a) -> str`, `erzeuge_spec(t, a, text) -> dict`, `spec_befunde(spec, ordner=ORDNER) -> list[dict]`.

- [ ] **Step 1: Failing tests – `tests/normteile/test_erzeugen.py` (neu)**

```python
from pathlib import Path

import pytest

from swki.normteile.erzeugen import erzeuge_spec, spec_befunde, teil_pruefsumme, vorlage_pruefsumme, vorlage_text
from swki.normteile.fehler import NormteilFehler
from swki.normteile.schluessel import Anfrage, loese_auf, naechste_laengen

DATEN = Path(__file__).parent / "daten"


def test_aufloesen_mit_vorgabevariante():
    _, a = loese_auf("iso 9999", "M6 x 12", ordner=DATEN)
    assert a == Anfrage("ISO 9999", "M6", 12.0, "8.8")
    assert a.schluessel == "ISO9999_M6x12_8_8" and a.bezeichnung == "M6 x 12"


@pytest.mark.parametrize(("groesse", "variante", "code"), [
    ("M7x12", None, "NORMTEIL_UNBEKANNT"),
    ("Mx", None, "NORMTEIL_UNBEKANNT"),
    ("M6", None, "NORMLAENGE_UNGUELTIG"),
    ("M6x13", None, "NORMLAENGE_UNGUELTIG"),
    ("M6x12", "10.9", "NORMVARIANTE_UNBEKANNT"),
    ("M8x12", None, "NORMTEIL_GESPERRT"),
])
def test_aufloesen_fehler(groesse, variante, code):
    with pytest.raises(NormteilFehler) as e:
        loese_auf("ISO 9999", groesse, variante, DATEN)
    assert e.value.daten["code"] == code


def test_naechste_normlaengen():
    with pytest.raises(NormteilFehler) as e:
        loese_auf("ISO 9999", "M6x13", ordner=DATEN)
    assert e.value.daten["naechste"] == {"darunter": 12, "darueber": 16}
    assert naechste_laengen([10, 12], 30) == {"darunter": 12, "darueber": None}


def test_spec_aus_vorlage():
    t, a = loese_auf("ISO 9999", "M6x16", "A2", DATEN)
    spec = erzeuge_spec(t, a, vorlage_text(t, DATEN))
    assert spec["name"] == "ISO9999_M6x16_A2"
    assert spec["parameter"] == {"a": 6, "b": 12, "l": 16.0}
    assert spec["material"] == "1.4301"
    assert spec["eigenschaften"] == {"Benennung": "Testring ISO 9999 - M6 x 16 - A2", "Norm": "ISO 9999",
                                     "Groesse": "M6 x 16", "Festigkeitsklasse": "A2"}
    assert spec_befunde(spec, DATEN) == []


def test_feste_zahl_ist_befund():
    t, a = loese_auf("ISO 9999", "M6x16", ordner=DATEN)
    spec = erzeuge_spec(t, a, vorlage_text(t, DATEN))
    spec["features"][0]["skizze"]["elemente"][0]["polygon"]["punkte"][1] = [6, 0]
    assert [b["pfad"] for b in spec_befunde(spec, DATEN)] == ["features[0].skizze.elemente[0].polygon.punkte"]


def test_pruefsummen():
    t, a = loese_auf("ISO 9999", "M6x16", ordner=DATEN)
    text = vorlage_text(t, DATEN)
    summe = teil_pruefsumme(t, a, text)
    assert summe == teil_pruefsumme(t, a, text.replace("\n", "\r\n"))          # Zeilenenden zählen nicht
    assert summe != teil_pruefsumme(t, a, text + "\n# geändert\n")              # Vorlage zählt
    assert summe != teil_pruefsumme(t, Anfrage("ISO 9999", "M6", 12.0, "8.8"), text)
    t["groessen"]["M6"]["masse"]["b"] = 12.5
    assert summe != teil_pruefsumme(t, a, text)                                 # Tabellenwert zählt
    assert vorlage_pruefsumme("a\r\nb") == vorlage_pruefsumme("a\nb")
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/normteile/test_erzeugen.py -q`
Expected: FAIL (`ModuleNotFoundError: swki.normteile.schluessel`).

- [ ] **Step 3: `swki/normteile/schluessel.py`**

```python
"""Normteil-Anfrage: Norm, Größe, Länge und Variante auflösen und gegen die Normtabelle prüfen (Spec 3a §7, §8)."""

import re
from dataclasses import dataclass
from pathlib import Path

from swki.normteile.fehler import (
    NORMLAENGE_UNGUELTIG, NORMTEIL_GESPERRT, NORMTEIL_UNBEKANNT, NORMVARIANTE_UNBEKANNT, NormteilFehler,
)
from swki.normteile.tabelle import ORDNER, lade_normtabelle, norm_datei

_GROESSE = re.compile(r"^(M?\d+(?:\.\d+)?)(?:[xX×](\d+(?:\.\d+)?))?$")


@dataclass(frozen=True)
class Anfrage:
    norm: str              # wie in der Tabelle, z. B. "ISO 4762"
    groesse: str           # Tabellenschlüssel, z. B. "M8" oder "8"
    laenge: float | None   # mm; None bei Teilen ohne Länge
    variante: str

    @property
    def bezeichnung(self) -> str:
        """Größe wie in der Normbezeichnung: "M8 x 30", "M8", "8 x 30"."""
        return self.groesse if self.laenge is None else f"{self.groesse} x {self.laenge:g}"

    @property
    def schluessel(self) -> str:
        """Dateiname in der Bibliothek und Name der Spezifikation, z. B. "ISO4762_M8x30_8_8"."""
        groesse = self.groesse if self.laenge is None else f"{self.groesse}x{self.laenge:g}"
        return re.sub(r"[^A-Za-z0-9-]+", "_", f"{norm_datei(self.norm).upper()}_{groesse}_{self.variante}")


def naechste_laengen(laengen: list, laenge: float) -> dict:
    darunter = [x for x in laengen if x < laenge]
    darueber = [x for x in laengen if x > laenge]
    return {"darunter": max(darunter) if darunter else None, "darueber": min(darueber) if darueber else None}


def loese_auf(norm: str, groesse: str, variante: str | None = None, ordner: Path = ORDNER) -> tuple[dict, Anfrage]:
    """(Normtabelle, Anfrage) z. B. für ("ISO 4762", "M8x30", "10.9"); wirft NormteilFehler mit Code (Spec 3a §8)."""
    t = lade_normtabelle(norm, ordner)
    treffer = _GROESSE.match(re.sub(r"\s+", "", str(groesse)).replace(",", "."))
    if not treffer or treffer.group(1) not in t["groessen"]:
        raise NormteilFehler(NORMTEIL_UNBEKANNT,
                             f"{t['norm']}: Größe {groesse!r} unbekannt; vorhanden: {', '.join(t['groessen'])}",
                             vorhanden=list(t["groessen"]))
    g = treffer.group(1)
    zeile = t["groessen"][g]
    laenge = float(treffer.group(2)) if treffer.group(2) else None
    if t["laenge"]:
        if laenge is None:
            raise NormteilFehler(NORMLAENGE_UNGUELTIG, f"{t['norm']} {g}: Länge fehlt (z. B. {g}x{zeile['laengen'][0]:g})",
                                 laengen=zeile["laengen"])
        if laenge not in zeile["laengen"]:
            naechste = naechste_laengen(zeile["laengen"], laenge)
            raise NormteilFehler(NORMLAENGE_UNGUELTIG,
                                 f"{t['norm']} {g}: Länge {laenge:g} ist keine Normlänge (nächste: "
                                 f"{naechste['darunter']} / {naechste['darueber']})",
                                 naechste=naechste, laengen=zeile["laengen"])
    elif laenge is not None:
        raise NormteilFehler(NORMLAENGE_UNGUELTIG, f"{t['norm']} hat keine Länge (Größe {g})")
    variante = t["vorgabe_variante"] if variante is None else str(variante)
    if variante not in t["varianten"]:
        raise NormteilFehler(NORMVARIANTE_UNBEKANNT,
                             f"{t['norm']}: Variante {variante!r} unbekannt; vorhanden: {', '.join(t['varianten'])}",
                             vorhanden=list(t["varianten"]))
    if zeile["status"] != "abgeglichen":
        raise NormteilFehler(NORMTEIL_GESPERRT, f"{t['norm']} {g} ist gesperrt: {zeile.get('grund')}",
                             grund=zeile.get("grund"))
    return t, Anfrage(t["norm"], g, laenge, variante)
```

- [ ] **Step 4: `swki/normteile/erzeugen.py`**

```python
"""Spezifikation eines Normteils aus Bauvorlage und Tabellenzeile; Prüfsummen und Befunde (Spec 3a §5–§7)."""

import hashlib
import json
from pathlib import Path

import yaml

from swki.normteile.schluessel import Anfrage
from swki.normteile.tabelle import ORDNER
from swki.spec.hinweise import feste_masse
from swki.spec.laden import plausibel_befunde, schema_befunde


def vorlage_text(t: dict, ordner: Path = ORDNER) -> str:
    return (ordner / t["vorlage"]).read_text(encoding="utf-8")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def vorlage_pruefsumme(text: str) -> str:
    return _sha(text.replace("\r\n", "\n"))


def teil_pruefsumme(t: dict, a: Anfrage, text: str) -> str:
    """Prüfsumme über alles, was das Teil bestimmt: Norm, Benennung, Maße der Größe, Länge, Variante mit Werkstoff und
    Vorlage. Ändert sich eines davon, gilt die Bibliotheksdatei als veraltet."""
    inhalt = {"norm": t["norm"], "benennung": t["benennung"], "groesse": a.groesse,
              "masse": t["groessen"][a.groesse]["masse"], "laenge": a.laenge, "variante": a.variante,
              "material": t["varianten"][a.variante]["material"], "vorlage": vorlage_pruefsumme(text)}
    return _sha(json.dumps(inhalt, sort_keys=True, ensure_ascii=False))


def benennung(t: dict, a: Anfrage) -> str:
    return f"{t['benennung']} {t['norm']} - {a.bezeichnung} - {a.variante}"


def erzeuge_spec(t: dict, a: Anfrage, text: str) -> dict:
    """Vorlage mit den Parametern der Tabellenzeile (plus l), Name, Werkstoff und Eigenschaften; Features und Prüfung
    bleiben unverändert."""
    spec = yaml.safe_load(text)
    parameter = dict(t["groessen"][a.groesse]["masse"])
    if a.laenge is not None:
        parameter["l"] = a.laenge
    spec["name"] = a.schluessel
    spec["parameter"] = parameter
    spec["material"] = t["varianten"][a.variante]["material"]
    spec["eigenschaften"] = {"Benennung": benennung(t, a), "Norm": t["norm"], "Groesse": a.bezeichnung,
                             "Festigkeitsklasse": a.variante}
    return spec


def spec_befunde(spec: dict, ordner: Path = ORDNER) -> list[dict]:
    """Schema- und Plausibilitätsbefunde; feste Zahlen in Features gelten bei Normteilen als Befund (jedes Maß ist ein
    Ausdruck über die Tabellenwerte)."""
    befunde = schema_befunde(spec) or plausibel_befunde(spec, ordner)
    return befunde + [{"pfad": h["pfad"], "meldung": h["meldung"]} for h in feste_masse(spec)]
```

- [ ] **Step 5: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/normteile -q` → PASS.
Run: `.venv\Scripts\python.exe -m pytest -q` → vorher + **11** (1 + 6 + 1 + 1 + 1 + 1).

- [ ] **Step 6: Commit**

```powershell
git add swki/normteile/schluessel.py swki/normteile/erzeugen.py tests/normteile/test_erzeugen.py
git commit -m "normteile: Anfrage aufloesen, Spezifikation aus Vorlage, Pruefsummen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Bau mit Selbstprüfung, Bibliothek, Befehle `swki normteil`

**Files:**
- Modify: `swki/compiler/bauen.py` (`_vorbereiten` → `vorbereiten`, Aufruf anpassen), `swki/cli.py` (`_befehlsgruppen`)
- Create: `swki/normteile/bau.py`, `swki/normteile/bibliothek.py`, `swki/normteile/befehle.py`
- Test: `tests/normteile/test_befehle_normteile.py` (neu)

**Interfaces:**
- Consumes: Task 4 und 5; `compiler.ablauf.baue_features`, `pruefung.messen.messe`, `pruefung.bewertung.bewerte`, `pruefung.bilder.screenshots`, `pruefung.schleife.lies_urteil(pfad) -> dict | None`, `auftrag.laeufe`, `auftrag.lauf_ordner`.
- Produces: `bau.AUFTRAG = "NORMTEILE"`, `bau.baue_und_pruefe(spec, ordner, mit_bildern=False) -> {"bestanden", "pruefungen", "maengel", "teil", "bilder", "fehler"}`. `bibliothek.bibliotheksordner(r) -> Path`, `teil_pfad`, `lies_eintrag`, `ist_aktuell(ordner, schluessel, pruefsumme) -> bool`, `lege_ab(ordner, schluessel, quelle, eintrag) -> Path`, `eintraege(ordner) -> list[dict]`. `befehle.hole(norm, groesse, variante=None, wissen=ORDNER) -> dict` (`{"schluessel", "pfad", "gebaut", "pruefung", "lauf"?}`), `tabellen_pruefen(norm=None, wissen=ORDNER)`, `liste(nur_veraltet=False, wissen=ORDNER)`, `muster(norm, wissen=ORDNER)`, `urteil(norm, datei, vorlage_summe, wissen=ORDNER)`, `urteil_pfad(t, wissen)`, `vorlage_geprueft(t, text, wissen) -> bool`.

- [ ] **Step 1: Failing tests – `tests/normteile/test_befehle_normteile.py` (neu)**

```python
import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.konfig import Rechner
from swki.normteile import befehle
from swki.normteile.erzeugen import vorlage_pruefsumme, vorlage_text
from swki.normteile.fehler import NormteilFehler
from swki.normteile.tabelle import lade_normtabelle

DATEN = Path(__file__).parent / "daten"


@pytest.fixture
def wissen(tmp_path, monkeypatch):
    ziel = tmp_path / "wissen"
    shutil.copytree(DATEN, ziel)
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit", tmp_path / "bib")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    return ziel


@pytest.fixture
def gebaut(monkeypatch):
    aufrufe = []

    def fake(spec, ordner, mit_bildern=False):
        aufrufe.append((spec["name"], mit_bildern))
        teil = ordner / f"{spec['name']}.sldprt"
        teil.write_bytes(b"teil")
        bilder = {"iso": str(ordner / "bilder" / "iso.png")} if mit_bildern else {}
        return {"bestanden": True, "pruefungen": [{"id": "rebuild", "ok": True}], "maengel": [], "teil": str(teil),
                "bilder": bilder, "fehler": None}

    monkeypatch.setattr(befehle.bau, "baue_und_pruefe", fake)
    return aufrufe


def _urteil(wissen, tmp_path, bestanden=True):
    t = lade_normtabelle("ISO 9999", wissen)
    datei = tmp_path / "urteil.json"
    maengel = [] if bestanden else [{"knoten": ["f1"], "beschreibung": "Ring liegt falsch"}]
    datei.write_text(json.dumps({"bestanden": bestanden, "maengel": maengel}), encoding="utf-8")
    return befehle.urteil("ISO 9999", datei, vorlage_pruefsumme(vorlage_text(t, wissen)), wissen)


def test_hole_ohne_urteil(wissen, gebaut):
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMVORLAGE_UNGEPRUEFT" and gebaut == []


def test_hole_baut_legt_ab_und_trifft_den_cache(wissen, gebaut, tmp_path):
    _urteil(wissen, tmp_path)
    erst = befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    ziel = tmp_path / "bib" / "2025" / "ISO9999_M6x12_8_8.sldprt"
    assert erst["gebaut"] is True and Path(erst["pfad"]) == ziel and ziel.read_bytes() == b"teil"
    eintrag = json.loads(ziel.with_suffix(".json").read_text(encoding="utf-8"))
    assert eintrag["bestanden"] is True and eintrag["groesse"] == "M6" and eintrag["laenge"] == 12.0
    zweit = befehle.hole("ISO 9999", "M6 x 12", wissen=wissen)
    assert zweit["gebaut"] is False and zweit["pfad"] == str(ziel) and len(gebaut) == 1


def test_geaenderte_tabelle_baut_neu(wissen, gebaut, tmp_path):
    _urteil(wissen, tmp_path)
    befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    pfad = wissen / "iso9999.yaml"
    pfad.write_text(pfad.read_text(encoding="utf-8").replace("b: 12}", "b: 12.5}"), encoding="utf-8")
    assert befehle.liste(wissen=wissen)["teile"][0]["aktuell"] is False
    assert befehle.hole("ISO 9999", "M6x12", wissen=wissen)["gebaut"] is True and len(gebaut) == 2
    assert befehle.liste(nur_veraltet=True, wissen=wissen)["teile"] == []


def test_geaenderte_vorlage_braucht_neues_urteil(wissen, gebaut, tmp_path):
    _urteil(wissen, tmp_path)
    vorlage = wissen / "vorlagen" / "iso9999.yaml"
    vorlage.write_text(vorlage.read_text(encoding="utf-8") + "# geändert\n", encoding="utf-8")
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMVORLAGE_UNGEPRUEFT"


def test_nicht_bestandenes_urteil_sperrt(wissen, gebaut, tmp_path):
    _urteil(wissen, tmp_path, bestanden=False)
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMVORLAGE_UNGEPRUEFT"


def test_gescheiterte_pruefung_legt_nichts_ab(wissen, monkeypatch, tmp_path):
    _urteil(wissen, tmp_path)
    monkeypatch.setattr(befehle.bau, "baue_und_pruefe", lambda spec, ordner, mit_bildern=False: {
        "bestanden": False, "pruefungen": [], "teil": None, "bilder": {}, "fehler": None,
        "maengel": [{"pruefung": "mass:s", "knoten": ["f2"], "beschreibung": "s 6.2 statt 6"}]})
    with pytest.raises(NormteilFehler) as e:
        befehle.hole("ISO 9999", "M6x12", wissen=wissen)
    assert e.value.daten["code"] == "NORMTEIL_PRUEFUNG" and e.value.daten["maengel"][0]["pruefung"] == "mass:s"
    assert not (tmp_path / "bib").exists()
    assert (Path(e.value.daten["ordner"]) / "spec.yaml").is_file()


def test_urteil_zu_alter_vorlage_wird_abgelehnt(wissen, tmp_path):
    datei = tmp_path / "u.json"
    datei.write_text('{"bestanden": true, "maengel": []}', encoding="utf-8")
    with pytest.raises(NormteilFehler) as e:
        befehle.urteil("ISO 9999", datei, "0" * 64, wissen)
    assert e.value.daten["code"] == "NORMVORLAGE_UNGEPRUEFT"


def test_muster_baut_kleinste_groesse_mit_bildern(wissen, gebaut):
    m = befehle.muster("ISO 9999", wissen)
    assert m["schluessel"] == "ISO9999_M5x10_8_8" and gebaut == [("ISO9999_M5x10_8_8", True)]
    assert Path(m["spec"]).is_file() and m["bilder"] and m["bestanden"] is True


def test_tabellen_pruefen(wissen):
    e = befehle.tabellen_pruefen(wissen=wissen)
    assert e["gueltig"] is True and e["normen"]["ISO 9999"]["gesperrt"] == ["M8"]


def test_tabellen_pruefen_meldet_befunde(wissen):
    pfad = wissen / "iso9999.yaml"
    pfad.write_text(pfad.read_text(encoding="utf-8").replace("b: 12}", "b: 5}"), encoding="utf-8")
    with pytest.raises(NormteilFehler) as e:
        befehle.tabellen_pruefen(wissen=wissen)
    assert e.value.daten["code"] == "NORMTABELLE_UNGUELTIG"


def test_cli_unbekannte_norm(capsys):
    code = main(["normteil", "hole", "ISO 1", "M8x30"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 1 and daten["code"] == "NORMTEIL_UNBEKANNT"
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/normteile/test_befehle_normteile.py -q`
Expected: FAIL (`ImportError: swki.normteile.befehle`).

- [ ] **Step 3: `swki/compiler/bauen.py`**

`_vorbereiten` in `vorbereiten` umbenennen (Definition und den einen Aufruf in `bauen`); Docstring: `"""Parameter als Gleichungen, Werkstoff und Eigenschaften setzen (auch von swki.normteile.bau genutzt)."""`

- [ ] **Step 4: `swki/normteile/bibliothek.py`**

```python
"""Normteilbibliothek (Spec 3a §3, §7): <normteilbibliothek>/<sw_jahr>/<schluessel>.sldprt + .json; nicht im Git.
Die Bibliothek ist ein Cache: maßgeblich sind Normtabelle und Bauvorlage."""

import json
import shutil
from pathlib import Path

from swki.konfig import Rechner, swki_home


def bibliotheksordner(r: Rechner) -> Path:
    return (r.normteilbibliothek or swki_home() / "normteile") / str(r.sw_jahr)


def teil_pfad(ordner: Path, schluessel: str) -> Path:
    return ordner / f"{schluessel}.sldprt"


def lies_eintrag(ordner: Path, schluessel: str) -> dict | None:
    pfad = ordner / f"{schluessel}.json"
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.is_file() else None


def ist_aktuell(ordner: Path, schluessel: str, pruefsumme: str) -> bool:
    """Datei vorhanden, Eintrag mit gleicher Prüfsumme und bestandener Selbstprüfung."""
    eintrag = lies_eintrag(ordner, schluessel)
    return (eintrag is not None and eintrag.get("pruefsumme") == pruefsumme and eintrag.get("bestanden") is True
            and teil_pfad(ordner, schluessel).is_file())


def lege_ab(ordner: Path, schluessel: str, quelle: Path, eintrag: dict) -> Path:
    """Geprüftes Teil in die Bibliothek kopieren, danach den Eintrag schreiben (ohne Eintrag gilt eine Datei als veraltet)."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = teil_pfad(ordner, schluessel)
    shutil.copy2(quelle, ziel)
    text = json.dumps(eintrag, indent=2, ensure_ascii=False) + "\n"
    (ordner / f"{schluessel}.json").write_text(text, encoding="utf-8")
    return ziel


def eintraege(ordner: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ordner.glob("*.json"))]
```

- [ ] **Step 5: `swki/normteile/bau.py`**

```python
"""Bau und Selbstprüfung eines Normteils in SolidWorks (Spec 3a §6): neues Teil, Werkstoff und Eigenschaften, Features,
Messung und Bewertung im selben Dokument, Speichern im Arbeitsordner."""

from pathlib import Path

from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.bauen import vorbereiten
from swki.compiler.fehler import fehler_dict
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.bewertung import bewerte
from swki.pruefung.bilder import screenshots
from swki.pruefung.messen import messe
from swki.verbindung import verbinde

AUFTRAG = "NORMTEILE"


def baue_und_pruefe(spec: dict, ordner: Path, mit_bildern: bool = False) -> dict:
    """{"bestanden", "pruefungen", "maengel", "teil", "bilder", "fehler"}; ordner liegt im Arbeitsordner. Bei
    Bauabbruch: bestanden False, fehler gesetzt, nichts gemessen und nichts gespeichert."""
    r, standard = lade_rechner(), lade_standard()
    ordner.mkdir(parents=True, exist_ok=True)
    protokoll = Protokoll(AUFTRAG, f"{spec['name']}.yaml", 0, r.sw_jahr)
    app = verbinde(r.sw_jahr)
    model = sw.neues_teil(app, r.vorlage_teil)
    try:
        ctx = Kontext(app, model, spec, ordner / f"{spec['name']}.yaml", standard["toleranzen"]["anker_mm"])
        try:
            vorbereiten(app, model, spec, AUFTRAG)
            fehler = baue_features(ctx, protokoll, alle_handler(), lambda c: sw.rebuild(c.model))
        except Exception as e:  # z. B. MATERIAL_UNBEKANNT beim Vorbereiten
            fehler = e
        protokoll.schreibe(ordner / "protokoll.json")
        if fehler is not None:
            return {"bestanden": False, "pruefungen": [], "teil": None, "bilder": {}, "fehler": fehler_dict(fehler),
                    "maengel": [{"pruefung": "bau", "knoten": [], "beschreibung": str(fehler)}]}
        bericht = bewerte(spec, messe(ctx), standard)
        bilder = screenshots(app, model, ordner / "bilder") if mit_bildern else {}
        teil = ordner / f"{spec['name']}.sldprt"
        sw.speichere(model, teil)
        return {**bericht, "teil": str(teil), "bilder": bilder, "fehler": None}
    finally:
        sw.schliesse(app, model)
```

Prüfe `Protokoll.schreibe` (setzt es `status`/`dauer_s` voraus?). Falls ja, vor dem Schreiben `protokoll.status = "fehler" if fehler else "ok"` setzen wie in `bauen.py`.

- [ ] **Step 6: `swki/normteile/befehle.py`**

```python
"""Befehle "swki normteil hole|tabellen-pruefen|liste|muster|urteil" (Spec 3a §6, §7)."""

import json
from datetime import date
from pathlib import Path

import yaml

from swki.auftrag import laeufe, lauf_ordner
from swki.konfig import lade_rechner
from swki.normteile import bau
from swki.normteile.bibliothek import bibliotheksordner, eintraege, ist_aktuell, lege_ab, lies_eintrag, teil_pfad
from swki.normteile.erzeugen import erzeuge_spec, spec_befunde, teil_pruefsumme, vorlage_pruefsumme, vorlage_text
from swki.normteile.fehler import NORMTABELLE_UNGUELTIG, NORMTEIL_PRUEFUNG, NORMVORLAGE_UNGEPRUEFT, NormteilFehler
from swki.normteile.schluessel import Anfrage, loese_auf
from swki.normteile.tabelle import ORDNER, lade_normtabelle, norm_datei, normen, pruefe_tabelle, tabellen_befunde
from swki.pruefung.schleife import lies_urteil


def urteil_pfad(t: dict, wissen: Path = ORDNER) -> Path:
    return wissen / "vorlagen" / f"{norm_datei(t['norm'])}.pruefer.json"


def vorlage_geprueft(t: dict, text: str, wissen: Path = ORDNER) -> bool:
    """Bestandenes Prüfer-Urteil zur aktuellen Vorlage (Prüfsumme) vorhanden?"""
    pfad = urteil_pfad(t, wissen)
    if not pfad.is_file():
        return False
    u = json.loads(pfad.read_text(encoding="utf-8"))
    return u.get("vorlage_pruefsumme") == vorlage_pruefsumme(text) and u.get("bestanden") is True


def _laufordner(r, schluessel: str) -> Path:
    """Neuer Laufordner <arbeitsordner>/NORMTEILE/<schluessel>/lauf-<n> (bleibt zur Analyse stehen)."""
    auftrag = f"{bau.AUFTRAG}/{schluessel}"
    bisher = laeufe(r, auftrag)
    return lauf_ordner(r, auftrag, bisher[-1] + 1 if bisher else 1)


def _baue(t: dict, a: Anfrage, text: str, r, wissen: Path, mit_bildern: bool = False) -> tuple[Path, dict]:
    spec = erzeuge_spec(t, a, text)
    if befunde := spec_befunde(spec, wissen):
        raise NormteilFehler(NORMTEIL_PRUEFUNG, f"{a.schluessel}: erzeugte Spezifikation ungültig", befunde=befunde)
    lauf = _laufordner(r, a.schluessel)
    lauf.mkdir(parents=True, exist_ok=True)
    (lauf / "spec.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    ergebnis = bau.baue_und_pruefe(spec, lauf, mit_bildern)
    text_bericht = json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str) + "\n"
    (lauf / "pruefbericht.json").write_text(text_bericht, encoding="utf-8")
    return lauf, ergebnis


def hole(norm: str, groesse: str, variante: str | None = None, wissen: Path = ORDNER) -> dict:
    t, a = loese_auf(norm, groesse, variante, wissen)
    pruefe_tabelle(t, wissen)
    text = vorlage_text(t, wissen)
    summe = teil_pruefsumme(t, a, text)
    r = lade_rechner()
    bib = bibliotheksordner(r)
    if ist_aktuell(bib, a.schluessel, summe):
        eintrag = lies_eintrag(bib, a.schluessel)
        return {"schluessel": a.schluessel, "pfad": str(teil_pfad(bib, a.schluessel)), "gebaut": False,
                "pruefung": {"bestanden": True, "datum": eintrag.get("datum")}}
    if not vorlage_geprueft(t, text, wissen):
        raise NormteilFehler(NORMVORLAGE_UNGEPRUEFT,
                             f"{t['norm']}: kein bestandenes Prüfer-Urteil zur aktuellen Vorlage – swki normteil muster "
                             f"\"{t['norm']}\", Prüfer-Agent, swki normteil urteil",
                             norm=t["norm"], vorlage_pruefsumme=vorlage_pruefsumme(text))
    lauf, ergebnis = _baue(t, a, text, r, wissen)
    if not ergebnis["bestanden"]:
        raise NormteilFehler(NORMTEIL_PRUEFUNG,
                             f"{a.schluessel}: Selbstprüfung nicht bestanden ({len(ergebnis['maengel'])} Mängel)",
                             maengel=ergebnis["maengel"], ordner=str(lauf))
    eintrag = {"schluessel": a.schluessel, "norm": t["norm"], "groesse": a.groesse, "laenge": a.laenge,
               "variante": a.variante, "pruefsumme": summe, "bestanden": True,
               "pruefungen": [p["id"] for p in ergebnis["pruefungen"]], "datum": date.today().isoformat(),
               "sw_jahr": r.sw_jahr, "lauf": str(lauf)}
    pfad = lege_ab(bib, a.schluessel, Path(ergebnis["teil"]), eintrag)
    return {"schluessel": a.schluessel, "pfad": str(pfad), "gebaut": True, "lauf": str(lauf),
            "pruefung": {"bestanden": True, "pruefungen": len(ergebnis["pruefungen"])}}


def tabellen_pruefen(norm: str | None = None, wissen: Path = ORDNER) -> dict:
    """Tabellenbefunde und – wenn die Tabelle stimmt – Befunde jeder erzeugten Spezifikation (alle Größen und Längen)."""
    ergebnis = {}
    for name in [norm_datei(norm)] if norm else normen(wissen):
        t = lade_normtabelle(name, wissen)
        befunde = tabellen_befunde(t, wissen)
        if not befunde:
            text = vorlage_text(t, wissen)
            for g, z in t["groessen"].items():
                for laenge in z.get("laengen") or [None]:
                    a = Anfrage(t["norm"], g, None if laenge is None else float(laenge), t["vorgabe_variante"])
                    befunde += [{**b, "pfad": f"{a.schluessel}: {b['pfad']}"}
                                for b in spec_befunde(erzeuge_spec(t, a, text), wissen)]
        ergebnis[t["norm"]] = {"befunde": befunde, "groessen": len(t["groessen"]),
                               "gesperrt": [g for g, z in t["groessen"].items() if z["status"] == "gesperrt"]}
    if any(e["befunde"] for e in ergebnis.values()):
        raise NormteilFehler(NORMTABELLE_UNGUELTIG, "Normtabellen mit Befunden", normen=ergebnis)
    return {"gueltig": True, "normen": ergebnis}


def liste(nur_veraltet: bool = False, wissen: Path = ORDNER) -> dict:
    bib = bibliotheksordner(lade_rechner())
    teile = []
    for e in eintraege(bib):
        try:
            t = lade_normtabelle(e["norm"], wissen)
            a = Anfrage(t["norm"], e["groesse"], e["laenge"], e["variante"])
            aktuell = ist_aktuell(bib, e["schluessel"], teil_pruefsumme(t, a, vorlage_text(t, wissen)))
        except (NormteilFehler, KeyError):
            aktuell = False  # Norm, Größe oder Variante gibt es nicht mehr
        teile.append({"schluessel": e["schluessel"], "aktuell": aktuell, "datum": e.get("datum")})
    if nur_veraltet:
        teile = [x for x in teile if not x["aktuell"]]
    return {"ordner": str(bib), "teile": teile}


def muster(norm: str, wissen: Path = ORDNER) -> dict:
    """Musterteil (kleinste Größe, kürzeste Länge, Vorgabevariante) mit Screenshots für den Prüfer-Agenten; wird nicht
    abgelegt und braucht kein Urteil. Der Status der Größe zählt hier nicht – geprüft wird die Vorlage."""
    t = lade_normtabelle(norm, wissen)
    pruefe_tabelle(t, wissen)
    g, zeile = next(iter(t["groessen"].items()))
    a = Anfrage(t["norm"], g, float(zeile["laengen"][0]) if t["laenge"] else None, t["vorgabe_variante"])
    text = vorlage_text(t, wissen)
    lauf, ergebnis = _baue(t, a, text, lade_rechner(), wissen, mit_bildern=True)
    return {"norm": t["norm"], "schluessel": a.schluessel, "bestanden": ergebnis["bestanden"],
            "maengel": ergebnis["maengel"], "vorlage_pruefsumme": vorlage_pruefsumme(text),
            "spec": str(lauf / "spec.yaml"), "pruefbericht": str(lauf / "pruefbericht.json"),
            "bilder": ergebnis["bilder"], "tabelle": str(wissen / f"{norm_datei(t['norm'])}.yaml"),
            "vorlage": str(wissen / t["vorlage"])}


def urteil(norm: str, datei: Path, vorlage_summe: str, wissen: Path = ORDNER) -> dict:
    """Prüfer-Urteil (rohes JSON des Prüfer-Agenten) zur aktuellen Vorlage ablegen."""
    t = lade_normtabelle(norm, wissen)
    aktuell = vorlage_pruefsumme(vorlage_text(t, wissen))
    if vorlage_summe != aktuell:
        raise NormteilFehler(NORMVORLAGE_UNGEPRUEFT, f"{t['norm']}: Vorlage seit dem Musterteil geändert – neu prüfen",
                             vorlage_pruefsumme=aktuell)
    u = lies_urteil(datei)
    if u is None:
        raise NormteilFehler(NORMVORLAGE_UNGEPRUEFT, f"Urteil {datei} fehlt")
    inhalt = {"norm": t["norm"], "vorlage_pruefsumme": aktuell, "bestanden": u["bestanden"], "maengel": u["maengel"],
              "datum": date.today().isoformat()}
    ziel = urteil_pfad(t, wissen)
    ziel.write_text(json.dumps(inhalt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"datei": str(ziel), **inhalt}


def einrichten(subparsers) -> None:
    gruppe = subparsers.add_parser("normteil", help="Normteile abrufen, bauen und prüfen").add_subparsers(
        dest="unterbefehl", required=True)
    p = gruppe.add_parser("hole", help="Normteil aus der Bibliothek holen oder bauen, prüfen und ablegen")
    p.add_argument("norm")
    p.add_argument("groesse")
    p.add_argument("--variante")
    p.set_defaults(func=lambda a: hole(a.norm, a.groesse, a.variante))
    p = gruppe.add_parser("tabellen-pruefen", help="Normtabellen und erzeugte Spezifikationen prüfen (ohne SolidWorks)")
    p.add_argument("norm", nargs="?")
    p.set_defaults(func=lambda a: tabellen_pruefen(a.norm))
    p = gruppe.add_parser("liste", help="Bibliothek anzeigen")
    p.add_argument("--veraltet", action="store_true")
    p.set_defaults(func=lambda a: liste(a.veraltet))
    p = gruppe.add_parser("muster", help="Musterteil mit Screenshots für den Prüfer-Agenten bauen")
    p.add_argument("norm")
    p.set_defaults(func=lambda a: muster(a.norm))
    p = gruppe.add_parser("urteil", help="Prüfer-Urteil zur aktuellen Vorlage ablegen")
    p.add_argument("norm")
    p.add_argument("datei")
    p.add_argument("--vorlage-pruefsumme", required=True)
    p.set_defaults(func=lambda a: urteil(a.norm, Path(a.datei), a.vorlage_pruefsumme))
```

`swki/cli.py` `_befehlsgruppen`: `from swki.normteile import befehle as normteil_befehle` und `normteil_befehle` an die Liste anhängen.

- [ ] **Step 7: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/normteile -q` → PASS.
Run: `.venv\Scripts\python.exe -m pytest -q` → vorher + **11**.
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.

- [ ] **Step 8: Commit**

```powershell
git add swki/compiler/bauen.py swki/cli.py swki/normteile/bau.py swki/normteile/bibliothek.py swki/normteile/befehle.py tests/normteile/test_befehle_normteile.py
git commit -m "normteile: Bau mit Selbstpruefung, Bibliothek, Befehle swki normteil" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: ISO 4762 – Normtabelle, Bauvorlage, Tests (unit + live)

**Files:**
- Create: `swki/wissen/normteile/iso4762.yaml`, `swki/wissen/normteile/vorlagen/iso4762.yaml`
- Create: `tests/normteile/test_vorlagen.py` (generisch für alle Normen), `tests/normteile/test_volumen_normteile.py`, `tests/live/test_live_normteile.py`

**Interfaces:**
- Consumes: Tasks 2–6; Spike S11 (Mittellinie, Flächen, Werkstoffe – Ledger beachten).
- Produces: Norm „ISO 4762“ mit `parameter: [d, dk, k, s, t, p]`, `laenge: true`, Varianten `8.8` (Vorgabe), `10.9`, `12.9`, `A2-70`; Vorlage mit Features `f1` (Rotation), `f2` (Innensechskant), `EINBAU_ACHSE`, `EINBAU_EBENE`. Alle Größen `status: gesperrt` bis zum Abgleich (Task 10).

- [ ] **Step 1: `swki/wissen/normteile/iso4762.yaml`**

```yaml
# Normtabelle ISO 4762 – Zylinderschrauben mit Innensechskant (Spec 3a §4).
# Werte aus Claudes Normwissen; eine Größe ist erst nach dem Abgleich mit ≥ 2 recherchierten Quellen nutzbar
# (status: abgeglichen, Task 10). Maße in mm: d Nenndurchmesser, dk Kopfdurchmesser (Höchstmaß), k Kopfhöhe
# (Höchstmaß), s Schlüsselweite (Nennmaß), t Innensechskanttiefe (Mindestmaß), p Steigung des Regelgewindes (ISO 261,
# nur für die Fase am Schaftende).
norm: ISO 4762
benennung: Zylinderschraube mit Innensechskant
ersetzt: DIN 912
vorlage: vorlagen/iso4762.yaml
parameter: [d, dk, k, s, t, p]
laenge: true
varianten:
  "8.8": {material: "1.1191"}
  "10.9": {material: "1.7225"}
  "12.9": {material: "1.7225"}
  "A2-70": {material: "1.4301"}
vorgabe_variante: "8.8"
groessen:
  M5: {masse: {d: 5, dk: 8.5, k: 5, s: 4, t: 2.5, p: 0.8}, laengen: [8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50],
       status: gesperrt, grund: noch nicht abgeglichen}
  M6: {masse: {d: 6, dk: 10, k: 6, s: 5, t: 3, p: 1}, laengen: [10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60],
       status: gesperrt, grund: noch nicht abgeglichen}
  M8: {masse: {d: 8, dk: 13, k: 8, s: 6, t: 4, p: 1.25},
       laengen: [12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80], status: gesperrt, grund: noch nicht abgeglichen}
  M10: {masse: {d: 10, dk: 16, k: 10, s: 8, t: 5, p: 1.5},
        laengen: [16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100], status: gesperrt,
        grund: noch nicht abgeglichen}
  M12: {masse: {d: 12, dk: 18, k: 12, s: 10, t: 6, p: 1.75},
        laengen: [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100, 110, 120], status: gesperrt,
        grund: noch nicht abgeglichen}
  M16: {masse: {d: 16, dk: 24, k: 16, s: 14, t: 8, p: 2},
        laengen: [25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160], status: gesperrt,
        grund: noch nicht abgeglichen}
quellen: []
regeln: ["dk > d", "k == d", "s < d", "t < k", "p < d/4", "s/3**0.5 < dk/2 - k/10"]
hinweise:
  - "dk und k sind Höchstmaße, t ist das Mindestmaß; die vereinfachte Darstellung baut genau diese Werte."
```

Werkstoffe: Hat Spike S11 einen Werkstoff als `FEHLT` gemeldet, gilt der Ersatz aus dem Ledger (Ruling vor Task 7).

- [ ] **Step 2: `swki/wissen/normteile/vorlagen/iso4762.yaml`**

```yaml
# Bauvorlage ISO 4762 (Spec 3a §5) – vereinfachte Darstellung: Schaft mit Nenn-Ø d über die volle Länge, kein Gewinde,
# Innensechskant mit flachem Boden, Fase k/10 an der Kopfoberkante (die Norm legt sie nicht maßlich fest), Fase p × 45°
# am Schaftende. Lage: Achse = Modell-Y, Kopfunterseite in der Ebene oben (y = 0), Kopf in +y, Schaft in −y.
# Fasen liegen im Rotationsprofil, damit das Sollvolumen analytisch bleibt (volumen: auto).
# parameter: Musterwerte M5 x 8; swki normteil setzt die Werte der Tabellenzeile ein.
art: teil
name: ISO4762_Muster
parameter: {d: 5, dk: 8.5, k: 5, s: 4, t: 2.5, p: 0.8, l: 8}
features:
  - id: f1
    typ: rotation
    skizze:
      ebene: vorne
      elemente:
        - polygon:
            punkte: [[0, "=-l"], ["=d/2-p", "=-l"], ["=d/2", "=p-l"], ["=d/2", 0], ["=dk/2", 0],
                     ["=dk/2", "=k-k/10"], ["=dk/2-k/10", "=k"], [0, "=k"]]
        - mittellinie: {von: [0, "=-l"], bis: [0, "=k"]}
  - id: f2
    typ: schnitt
    skizze:
      ebene: {versatz: {ebene: oben, abstand: "=k"}}
      elemente:
        - polygon:
            punkte: [["=s/2", "=-s/(2*3**0.5)"], ["=s/2", "=s/(2*3**0.5)"], [0, "=s/3**0.5"],
                     ["=-s/2", "=s/(2*3**0.5)"], ["=-s/2", "=-s/(2*3**0.5)"], [0, "=-s/3**0.5"]]
    ende: {typ: blind, tiefe: "=t"}
  - {id: EINBAU_ACHSE, typ: referenz, achse: y}
  - {id: EINBAU_EBENE, typ: referenz, ebene: {basis: oben}}
pruefung:
  huellquader: ["=dk", "=k+l", "=dk"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: k, von: {feature: f1, flaeche: "+y"}, zu: {punkt: [0, 0, 0]}, soll: "=k"}
    - {was: l, von: {feature: f1, flaeche: "-y"}, zu: {punkt: [0, 0, 0]}, soll: "=l"}
    - {was: s, von: {feature: f2, flaeche: "+x"}, zu: {feature: f2, flaeche: "-x"}, soll: "=s"}
    - {was: t, von: {feature: f1, flaeche: "+y"}, zu: {feature: f2, flaeche: "+y"}, soll: "=t"}
    - {was: EINBAU_EBENE, von: {referenz: EINBAU_EBENE}, zu: {feature: f1, flaeche: "+y"}, soll: "=k"}
  durchmesser_pruefen:
    - {was: d, feature: f1, nahe: ["=d/2", "=-l/2", 0], soll: "=d", referenz: EINBAU_ACHSE}
    - {was: dk, feature: f1, nahe: ["=dk/2", "=k/2", 0], soll: "=dk", referenz: EINBAU_ACHSE}
```

Hat Spike S11 gezeigt, dass die Mittellinie auf der Profilkante nicht baut, die dort gefundene Form (`von: [0, "=k"]`, `bis: [0, "=k+1"]`) verwenden.

- [ ] **Step 3: `tests/normteile/test_vorlagen.py` (neu, gilt für alle Normtabellen im Repo)**

```python
"""Jede Normtabelle ist ohne Befund; jede Vorlage hat genau die Parameter ihrer Tabelle (plus l) und ist selbst gültig;
jede Größe und Länge ergibt eine gültige Spezifikation ohne feste Zahlen (Spec 3a §11)."""

import pytest
import yaml

from swki.normteile.erzeugen import erzeuge_spec, spec_befunde, vorlage_text
from swki.normteile.schluessel import Anfrage
from swki.normteile.tabelle import lade_normtabelle, normen, tabellen_befunde

NORMEN = normen()


def test_es_gibt_normtabellen():
    assert NORMEN


@pytest.mark.parametrize("norm", NORMEN)
def test_tabelle_ohne_befund(norm):
    assert tabellen_befunde(lade_normtabelle(norm)) == []


@pytest.mark.parametrize("norm", NORMEN)
def test_vorlage_passt_zur_tabelle(norm):
    t = lade_normtabelle(norm)
    vorlage = yaml.safe_load(vorlage_text(t))
    assert set(vorlage["parameter"]) == set(t["parameter"]) | ({"l"} if t["laenge"] else set())
    assert spec_befunde(vorlage) == []


@pytest.mark.parametrize("norm", NORMEN)
def test_jede_groesse_und_laenge_ergibt_gueltige_spec(norm):
    t = lade_normtabelle(norm)
    text = vorlage_text(t)
    fehler = {}
    for g, z in t["groessen"].items():
        for laenge in z.get("laengen") or [None]:
            a = Anfrage(t["norm"], g, None if laenge is None else float(laenge), t["vorgabe_variante"])
            if befunde := spec_befunde(erzeuge_spec(t, a, text)):
                fehler[a.schluessel] = befunde
    assert fehler == {}
```

- [ ] **Step 4: `tests/normteile/test_volumen_normteile.py` (neu)**

```python
"""Sollvolumen (volumen: auto) gegen eine unabhängige Handrechnung aus Zylindern, Prismen und 45°-Fasenringen."""

import math

import pytest

from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.schluessel import Anfrage
from swki.normteile.tabelle import lade_normtabelle
from swki.pruefung.geometrie import volumen_auto


def _volumen(norm, groesse, laenge=None):
    t = lade_normtabelle(norm)
    spec = erzeuge_spec(t, Anfrage(t["norm"], groesse, laenge, t["vorgabe_variante"]), vorlage_text(t))
    volumen, grund = volumen_auto(spec)
    assert grund == "analytisch"
    return volumen, t["groessen"][groesse]["masse"]


def fasenring(r_schwerpunkt: float, a: float) -> float:
    """45°-Fase als Ring: rechtwinkliges Dreieck mit Kathete a, Schwerpunkt im Abstand r von der Achse (Pappus)."""
    return 2 * math.pi * r_schwerpunkt * a * a / 2


def sechskant(s: float) -> float:
    """Fläche eines regelmäßigen Sechsecks mit Schlüsselweite s."""
    return 3**0.5 / 2 * s**2


@pytest.mark.parametrize(("groesse", "laenge"), [("M5", 8), ("M10", 40), ("M16", 160)])
def test_iso4762(groesse, laenge):
    v, m = _volumen("ISO 4762", groesse, laenge)
    d, dk, k, s, t, p = (m[x] for x in ("d", "dk", "k", "s", "t", "p"))
    a = k / 10
    kopf = math.pi * (dk / 2) ** 2 * k - fasenring(dk / 2 - a / 3, a)
    schaft = math.pi * (d / 2) ** 2 * laenge - fasenring(d / 2 - p / 3, p)
    assert v == pytest.approx(kopf + schaft - sechskant(s) * t, rel=1e-9)
```

- [ ] **Step 5: `tests/live/test_live_normteile.py` (neu)**

```python
"""Live: Normteile aus Tabelle und Vorlage bauen und selbst prüfen (ohne Status, Urteil und Bibliothek)."""

import copy
import shutil

import pytest

from swki.konfig import lade_rechner
from swki.normteile.bau import baue_und_pruefe
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.schluessel import Anfrage
from swki.normteile.tabelle import lade_normtabelle

pytestmark = pytest.mark.sw


def _spec(norm, groesse, laenge=None):
    t = lade_normtabelle(norm)
    return erzeuge_spec(t, Anfrage(t["norm"], groesse, laenge, t["vorgabe_variante"]), vorlage_text(t))


def _pruefe(spec):
    ordner = lade_rechner().arbeitsordner / "SWKI-LIVE-NORMTEILE" / spec["name"]
    try:
        return baue_und_pruefe(spec, ordner)
    finally:
        shutil.rmtree(ordner, ignore_errors=True)


def _ok(ergebnis, *ids):
    assert ergebnis["bestanden"], ergebnis["maengel"]
    ok = {p["id"]: p["ok"] for p in ergebnis["pruefungen"]}
    assert all(ok.get(i) is True for i in ("huellquader", "volumen", "material", "eigenschaften", *ids)), ok


@pytest.mark.parametrize(("groesse", "laenge"), [("M5", 8), ("M10", 40), ("M16", 160)])
def test_iso4762(groesse, laenge):
    _ok(_pruefe(_spec("ISO 4762", groesse, laenge)), "mass:k", "mass:l", "mass:s", "mass:t", "mass:EINBAU_EBENE",
        "durchmesser:d", "durchmesser:dk")


def test_verfaelschte_vorlage_scheitert():
    # Bauweg falsch (Innensechskant 10 % zu tief), Prüfung unverändert → die Selbstprüfung muss es finden.
    spec = copy.deepcopy(_spec("ISO 4762", "M8", 30))
    spec["features"][1]["ende"]["tiefe"] = "=t*1.1"
    ergebnis = _pruefe(spec)
    assert not ergebnis["bestanden"]
    assert {m["pruefung"] for m in ergebnis["maengel"]} >= {"mass:t", "volumen"}
```

- [ ] **Step 6: Unit-Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/normteile -q` → PASS.
Run: `.venv\Scripts\python.exe -m swki normteil tabellen-pruefen "ISO 4762"` → `"gueltig": true`, `gesperrt` = alle sechs Größen.
Run: `.venv\Scripts\python.exe -m pytest -q` → vorher + **7** (4 Vorlagentests, 3 Volumen).

- [ ] **Step 7: Live**

Vorbedingungen (eine Instanz, `False 1`), dann:
`.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_normteile.py --zeit 240` → alle OK. Private Bytes und Einstellungen danach notieren.

- [ ] **Step 8: Commit**

```powershell
git add swki/wissen/normteile/iso4762.yaml swki/wissen/normteile/vorlagen/iso4762.yaml tests/normteile/test_vorlagen.py tests/normteile/test_volumen_normteile.py tests/live/test_live_normteile.py
git commit -m "normteile: ISO 4762 (Tabelle, Bauvorlage, Selbstpruefung live)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: ISO 4032 – Normtabelle, Bauvorlage, Tests

**Files:**
- Create: `swki/wissen/normteile/iso4032.yaml`, `swki/wissen/normteile/vorlagen/iso4032.yaml`
- Modify: `tests/normteile/test_volumen_normteile.py`, `tests/live/test_live_normteile.py`

**Interfaces:**
- Produces: Norm „ISO 4032“ mit `parameter: [d, s, m]`, `laenge: false`, Varianten `8` (Vorgabe), `A2-70`; Vorlage mit `f1` (Sechskant-Extrusion), `f2` (Bohrung als Rotationsschnitt mit 90°-Senkungen), `EINBAU_ACHSE`, `EINBAU_EBENE`.

- [ ] **Step 1: `swki/wissen/normteile/iso4032.yaml`**

```yaml
# Normtabelle ISO 4032 – Sechskantmuttern Typ 1 (Spec 3a §4). Werte aus Claudes Normwissen, gültig erst nach Abgleich
# (Task 10). Maße in mm: d Nenndurchmesser, s Schlüsselweite (Nennmaß), m Mutterhöhe (Höchstmaß).
norm: ISO 4032
benennung: Sechskantmutter
ersetzt: DIN 934
vorlage: vorlagen/iso4032.yaml
parameter: [d, s, m]
laenge: false
varianten:
  "8": {material: "1.1191"}
  "A2-70": {material: "1.4301"}
vorgabe_variante: "8"
groessen:
  M5: {masse: {d: 5, s: 8, m: 4.7}, status: gesperrt, grund: noch nicht abgeglichen}
  M6: {masse: {d: 6, s: 10, m: 5.2}, status: gesperrt, grund: noch nicht abgeglichen}
  M8: {masse: {d: 8, s: 13, m: 6.8}, status: gesperrt, grund: noch nicht abgeglichen}
  M10: {masse: {d: 10, s: 16, m: 8.4}, status: gesperrt, grund: noch nicht abgeglichen}
  M12: {masse: {d: 12, s: 18, m: 10.8}, status: gesperrt, grund: noch nicht abgeglichen}
  M16: {masse: {d: 16, s: 24, m: 14.8}, status: gesperrt, grund: noch nicht abgeglichen}
quellen: []
regeln: ["s > d*1.1", "m < d"]
hinweise:
  - "ISO 4032 weicht bei M10 und M12 in der Schlüsselweite von DIN 934 ab (ISO 16/18, DIN 17/19) – beim Abgleich ISO-Werte verwenden."
```

- [ ] **Step 2: `swki/wissen/normteile/vorlagen/iso4032.yaml`**

```yaml
# Bauvorlage ISO 4032 (Spec 3a §5) – vereinfachte Darstellung: Sechskant (Schlüsselweite s, Flächen senkrecht zu x)
# mit Bohrung Nenn-Ø d und 90°-Senkung d/20 an beiden Bohrungskanten (Senk-Ø 1,1·d); ohne Eckfasen am Sechskant, kein
# Gewinde. Lage: Achse = Modell-Y, Auflagefläche in der Ebene oben (y = 0), Höhe m in +y.
art: teil
name: ISO4032_Muster
parameter: {d: 5, s: 8, m: 4.7}
features:
  - id: f1
    typ: extrusion
    skizze:
      ebene: oben
      elemente:
        - polygon:
            punkte: [["=s/2", "=-s/(2*3**0.5)"], ["=s/2", "=s/(2*3**0.5)"], [0, "=s/3**0.5"],
                     ["=-s/2", "=s/(2*3**0.5)"], ["=-s/2", "=-s/(2*3**0.5)"], [0, "=-s/3**0.5"]]
    ende: {typ: blind, tiefe: "=m"}
  - id: f2
    typ: rotation
    schnitt: true
    skizze:
      ebene: vorne
      elemente:
        - polygon:
            punkte: [[0, 0], ["=d/2+d/20", 0], ["=d/2", "=d/20"], ["=d/2", "=m-d/20"], ["=d/2+d/20", "=m"], [0, "=m"]]
        - mittellinie: {von: [0, 0], bis: [0, "=m"]}
  - {id: EINBAU_ACHSE, typ: referenz, achse: y}
  - {id: EINBAU_EBENE, typ: referenz, ebene: {basis: oben}}
pruefung:
  huellquader: ["=s", "=m", "=2*s/3**0.5"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: m, von: {feature: f1, flaeche: "+y"}, zu: {feature: f1, flaeche: "-y"}, soll: "=m"}
    - {was: s, von: {feature: f1, flaeche: "+x"}, zu: {feature: f1, flaeche: "-x"}, soll: "=s"}
    - {was: EINBAU_EBENE, von: {referenz: EINBAU_EBENE}, zu: {feature: f1, flaeche: "+y"}, soll: "=m"}
  durchmesser_pruefen:
    - {was: d, feature: f2, nahe: ["=d/2", "=m/2", 0], soll: "=d", referenz: EINBAU_ACHSE}
```

Mittellinie wie in Task 7 (Spike-Ergebnis): liegt sie auf der Profilkante und baut das nicht, die Form aus dem Spike übernehmen.

- [ ] **Step 3: Volumentest anhängen (`tests/normteile/test_volumen_normteile.py`)**

```python
@pytest.mark.parametrize("groesse", ["M5", "M10", "M16"])
def test_iso4032(groesse):
    v, m = _volumen("ISO 4032", groesse)
    d, s, h = m["d"], m["s"], m["m"]
    c = d / 20
    bohrung = math.pi * (d / 2) ** 2 * h + 2 * fasenring(d / 2 + c / 3, c)
    assert v == pytest.approx(sechskant(s) * h - bohrung, rel=1e-9)
```

- [ ] **Step 4: Live-Test anhängen (`tests/live/test_live_normteile.py`)**

```python
@pytest.mark.parametrize("groesse", ["M5", "M10", "M16"])
def test_iso4032(groesse):
    _ok(_pruefe(_spec("ISO 4032", groesse)), "mass:m", "mass:s", "mass:EINBAU_EBENE", "durchmesser:d")
```

- [ ] **Step 5: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → vorher + **6** (3 generische Vorlagentests für die neue Norm, 3 Volumen).
Run: `.venv\Scripts\python.exe -m swki normteil tabellen-pruefen` → `"gueltig": true`.
Live: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_normteile.py --zeit 240` → alle OK (Speicher/Einstellungen notieren).

- [ ] **Step 6: Commit**

```powershell
git add swki/wissen/normteile/iso4032.yaml swki/wissen/normteile/vorlagen/iso4032.yaml tests/normteile/test_volumen_normteile.py tests/live/test_live_normteile.py
git commit -m "normteile: ISO 4032 (Tabelle, Bauvorlage, Selbstpruefung live)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: ISO 7089 und ISO 8734 – Normtabellen, Bauvorlagen, Passung zu den Normbohrungen

**Files:**
- Create: `swki/wissen/normteile/iso7089.yaml`, `swki/wissen/normteile/vorlagen/iso7089.yaml`, `swki/wissen/normteile/iso8734.yaml`, `swki/wissen/normteile/vorlagen/iso8734.yaml`, `tests/normteile/test_passung.py`
- Modify: `tests/normteile/test_volumen_normteile.py`, `tests/live/test_live_normteile.py`

**Interfaces:**
- Consumes: `spec.normen.normmasse(art, groesse)` (Normbohrungen).
- Produces: „ISO 7089“ (`parameter: [d1, d2, h]`, `laenge: false`, Varianten `200 HV` (Vorgabe), `A2`); „ISO 8734“ (`parameter: [d, c]`, `laenge: true`, Variante `St`; Referenzen `EINBAU_ACHSE`, `EINBAU_EBENE_1`, `EINBAU_EBENE_2`).

- [ ] **Step 1: `swki/wissen/normteile/iso7089.yaml`**

```yaml
# Normtabelle ISO 7089 – Flache Scheiben, normale Reihe, Produktklasse A (Spec 3a §4). Werte aus Claudes Normwissen,
# gültig erst nach Abgleich (Task 10). Maße in mm: d1 Innendurchmesser (Mindestmaß), d2 Außendurchmesser (Höchstmaß),
# h Dicke (Nennmaß). Die Größe bezeichnet die zugehörige Schraube.
norm: ISO 7089
benennung: Scheibe
ersetzt: DIN 125-1
vorlage: vorlagen/iso7089.yaml
parameter: [d1, d2, h]
laenge: false
varianten:
  "200 HV": {material: "1.0038"}
  A2: {material: "1.4301"}
vorgabe_variante: "200 HV"
groessen:
  M5: {masse: {d1: 5.3, d2: 10, h: 1}, status: gesperrt, grund: noch nicht abgeglichen}
  M6: {masse: {d1: 6.4, d2: 12, h: 1.6}, status: gesperrt, grund: noch nicht abgeglichen}
  M8: {masse: {d1: 8.4, d2: 16, h: 1.6}, status: gesperrt, grund: noch nicht abgeglichen}
  M10: {masse: {d1: 10.5, d2: 20, h: 2}, status: gesperrt, grund: noch nicht abgeglichen}
  M12: {masse: {d1: 13, d2: 24, h: 2.5}, status: gesperrt, grund: noch nicht abgeglichen}
  M16: {masse: {d1: 17, d2: 30, h: 3}, status: gesperrt, grund: noch nicht abgeglichen}
quellen: []
regeln: ["d2 > d1", "h < d1"]
```

- [ ] **Step 2: `swki/wissen/normteile/vorlagen/iso7089.yaml`**

```yaml
# Bauvorlage ISO 7089 (Spec 3a §5): Ring Innen-Ø d1, Außen-Ø d2, Dicke h. Lage: Achse = Modell-Y, Auflagefläche in der
# Ebene oben (y = 0), Dicke in +y.
art: teil
name: ISO7089_Muster
parameter: {d1: 5.3, d2: 10, h: 1}
features:
  - id: f1
    typ: rotation
    skizze:
      ebene: vorne
      elemente:
        - polygon: {punkte: [["=d1/2", 0], ["=d2/2", 0], ["=d2/2", "=h"], ["=d1/2", "=h"]]}
        - mittellinie: {von: [0, 0], bis: [0, "=h"]}
  - {id: EINBAU_ACHSE, typ: referenz, achse: y}
  - {id: EINBAU_EBENE, typ: referenz, ebene: {basis: oben}}
pruefung:
  huellquader: ["=d2", "=h", "=d2"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: h, von: {feature: f1, flaeche: "+y"}, zu: {feature: f1, flaeche: "-y"}, soll: "=h"}
    - {was: EINBAU_EBENE, von: {referenz: EINBAU_EBENE}, zu: {feature: f1, flaeche: "+y"}, soll: "=h"}
  durchmesser_pruefen:
    - {was: d1, feature: f1, nahe: ["=d1/2", "=h/2", 0], soll: "=d1", referenz: EINBAU_ACHSE}
    - {was: d2, feature: f1, nahe: ["=d2/2", "=h/2", 0], soll: "=d2", referenz: EINBAU_ACHSE}
```

- [ ] **Step 3: `swki/wissen/normteile/iso8734.yaml`**

```yaml
# Normtabelle ISO 8734 – Zylinderstifte, gehärtet (Spec 3a §4). Werte aus Claudes Normwissen, gültig erst nach
# Abgleich (Task 10). Maße in mm: d Nenndurchmesser, c Fase (Richtwert). Die Größe ist der Nenndurchmesser.
norm: ISO 8734
benennung: Zylinderstift gehärtet
ersetzt: DIN 6325
vorlage: vorlagen/iso8734.yaml
parameter: [d, c]
laenge: true
varianten:
  St: {material: "1.3505"}
vorgabe_variante: St
groessen:
  "4": {masse: {d: 4, c: 0.63}, laengen: [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40],
        status: gesperrt, grund: noch nicht abgeglichen}
  "5": {masse: {d: 5, c: 0.8}, laengen: [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40, 45, 50],
        status: gesperrt, grund: noch nicht abgeglichen}
  "6": {masse: {d: 6, c: 1.2}, laengen: [12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40, 45, 50, 55, 60],
        status: gesperrt, grund: noch nicht abgeglichen}
  "8": {masse: {d: 8, c: 1.6},
        laengen: [14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80],
        status: gesperrt, grund: noch nicht abgeglichen}
  "10": {masse: {d: 10, c: 2},
         laengen: [18, 20, 22, 24, 26, 28, 30, 32, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95],
         status: gesperrt, grund: noch nicht abgeglichen}
  "12": {masse: {d: 12, c: 2.5},
         laengen: [22, 24, 26, 28, 30, 32, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100],
         status: gesperrt, grund: noch nicht abgeglichen}
quellen: []
regeln: ["c < d/4"]
```

- [ ] **Step 4: `swki/wissen/normteile/vorlagen/iso8734.yaml`**

```yaml
# Bauvorlage ISO 8734 (Spec 3a §5) – vereinfachte Darstellung: Zylinder Ø d, Länge l, Fase c × 45° an beiden Enden
# (die Norm sieht an einem Ende eine Kuppe vor). Lage: Achse = Modell-Y, eine Stirnseite in der Ebene oben (y = 0),
# Länge in +y.
art: teil
name: ISO8734_Muster
parameter: {d: 4, c: 0.63, l: 8}
features:
  - id: f1
    typ: rotation
    skizze:
      ebene: vorne
      elemente:
        - polygon: {punkte: [[0, 0], ["=d/2-c", 0], ["=d/2", "=c"], ["=d/2", "=l-c"], ["=d/2-c", "=l"], [0, "=l"]]}
        - mittellinie: {von: [0, 0], bis: [0, "=l"]}
  - {id: EINBAU_ACHSE, typ: referenz, achse: y}
  - {id: EINBAU_EBENE_1, typ: referenz, ebene: {basis: oben}}
  - {id: EINBAU_EBENE_2, typ: referenz, ebene: {basis: oben, abstand: "=l"}}
pruefung:
  huellquader: ["=d", "=l", "=d"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: l, von: {feature: f1, flaeche: "+y"}, zu: {feature: f1, flaeche: "-y"}, soll: "=l"}
    - {was: EINBAU_EBENE_1, von: {referenz: EINBAU_EBENE_1}, zu: {feature: f1, flaeche: "+y"}, soll: "=l"}
    - {was: EINBAU_EBENE_2, von: {referenz: EINBAU_EBENE_2}, zu: {feature: f1, flaeche: "-y"}, soll: "=l"}
  durchmesser_pruefen:
    - {was: d, feature: f1, nahe: ["=d/2", "=l/2", 0], soll: "=d", referenz: EINBAU_ACHSE}
```

Mittellinie wie in Task 7 (Spike-Ergebnis).

- [ ] **Step 5: Volumentests anhängen**

```python
@pytest.mark.parametrize("groesse", ["M5", "M10", "M16"])
def test_iso7089(groesse):
    v, m = _volumen("ISO 7089", groesse)
    assert v == pytest.approx(math.pi * ((m["d2"] / 2) ** 2 - (m["d1"] / 2) ** 2) * m["h"], rel=1e-9)


@pytest.mark.parametrize(("groesse", "laenge"), [("4", 8), ("8", 30), ("12", 100)])
def test_iso8734(groesse, laenge):
    v, m = _volumen("ISO 8734", groesse, laenge)
    d, c = m["d"], m["c"]
    assert v == pytest.approx(math.pi * (d / 2) ** 2 * laenge - 2 * fasenring(d / 2 - c / 3, c), rel=1e-9)
```

- [ ] **Step 6: `tests/normteile/test_passung.py` (neu)**

```python
"""Normteile passen zu den Normbohrungen aus Stufe 2c (swki/wissen/bohrungsnormen.yaml)."""

from swki.normteile.tabelle import lade_normtabelle
from swki.spec.normen import normmasse


def test_zylinderschraube_passt_in_ihre_normbohrung():
    t = lade_normtabelle("ISO 4762")
    gemeinsam = [g for g in t["groessen"] if normmasse("zylinderschraube", g)]
    assert len(gemeinsam) >= 4
    for g in gemeinsam:
        m, b = t["groessen"][g]["masse"], normmasse("zylinderschraube", g)
        assert m["d"] < b["durchgang"] and m["dk"] < b["senkung_d"] and m["k"] <= b["senkung_t"], g


def test_stift_passt_in_sein_stiftloch():
    t = lade_normtabelle("ISO 8734")
    gemeinsam = [g for g in t["groessen"] if normmasse("stift", g)]
    assert len(gemeinsam) >= 4
    for g in gemeinsam:
        assert t["groessen"][g]["masse"]["d"] == normmasse("stift", g)["durchmesser"], g
```

- [ ] **Step 7: Live-Tests anhängen**

```python
@pytest.mark.parametrize("groesse", ["M5", "M10", "M16"])
def test_iso7089(groesse):
    _ok(_pruefe(_spec("ISO 7089", groesse)), "mass:h", "mass:EINBAU_EBENE", "durchmesser:d1", "durchmesser:d2")


@pytest.mark.parametrize(("groesse", "laenge"), [("4", 8), ("8", 30), ("12", 100)])
def test_iso8734(groesse, laenge):
    _ok(_pruefe(_spec("ISO 8734", groesse, laenge)), "mass:l", "mass:EINBAU_EBENE_1", "mass:EINBAU_EBENE_2",
        "durchmesser:d")
```

- [ ] **Step 8: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → vorher + **14** (2 × 3 generische Vorlagentests, 6 Volumen, 2 Passung).
Run: `.venv\Scripts\python.exe -m swki normteil tabellen-pruefen` → `"gueltig": true` für vier Normen.
Live: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_normteile.py --zeit 240` → alle OK.

- [ ] **Step 9: Commit**

```powershell
git add swki/wissen/normteile/iso7089.yaml swki/wissen/normteile/vorlagen/iso7089.yaml swki/wissen/normteile/iso8734.yaml swki/wissen/normteile/vorlagen/iso8734.yaml tests/normteile/test_volumen_normteile.py tests/normteile/test_passung.py tests/live/test_live_normteile.py
git commit -m "normteile: ISO 7089 und ISO 8734 (Tabellen, Bauvorlagen, Passung zu Normbohrungen)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Abgleich der Normtabellen per Web-Recherche (Controller-Workflow + Implementer)

**Files:**
- Create: `docs/stufe3a/abgleich/iso4762.json`, `iso4032.json`, `iso7089.json`, `iso8734.json`
- Modify: die vier Normtabellen unter `swki/wissen/normteile/`

**Interfaces:**
- Consumes: Tabellen aus Task 7–9.
- Produces: Tabellen mit `quellen` und `status: abgeglichen` bzw. `gesperrt` mit Grund; Liste offener Widersprüche für den Nutzer.

- [ ] **Step 1 (Controller): Recherche-Workflow**

Der Nutzer hat den Workflow mit Agents für diesen Schritt freigegeben (2026-10-02). Vorher den Skill `workflow-authoring` laden. Je Norm ein Recherche-Agent (4 parallel, Modell mittel), Auftrag je Agent:

> Recherchiere für die Norm `<NORM>` (`<benennung>`) die Maße `<parameter>` und – falls `laenge: true` – die Längenreihe je Größe für die Größen `<liste>`. Nutze mindestens zwei voneinander unabhängige, öffentlich zugängliche Quellen je Größe (Herstellerdatenblätter oder Kataloge, z. B. Bossard, Würth, Fabory, Hoffmann, Kipp, Norelem; Normauszüge von Händlern). Zwei Seiten desselben Unternehmens oder Kopien derselben Tabelle zählen als eine Quelle. Achte auf ISO- gegen DIN-Werte (`<hinweise>`) und auf die Art des Maßes (Höchst-, Mindest-, Nennmaß wie im Tabellenkopf beschrieben). Rufe jede Seite selbst ab; übernimm nichts aus dem Gedächtnis. Gib nur JSON aus: `{"norm": …, "groessen": {"<g>": {"masse": {"<name>": [{"wert": <zahl>, "quelle": <url>}]}, "laengen": [{"werte": [...], "quelle": <url>}]}}, "quellen": [{"url", "titel", "abgerufen": "YYYY-MM-DD"}], "bemerkungen": [...]}`.

Ergebnis je Norm unverändert nach `docs/stufe3a/abgleich/<norm>.json` schreiben (nur das JSON-Objekt).

- [ ] **Step 2 (Implementer): Tabellen aktualisieren – Regeln**

Für jede Größe und jedes Maß:
- Bestätigen ≥ 2 unabhängige Quellen denselben Wert (auf 0,01 mm) und ist es der Tabellenwert → bleibt.
- Bestätigen ≥ 2 unabhängige Quellen übereinstimmend einen **anderen** Wert → diesen Wert übernehmen (Claudes Wissen zählt nicht) und im Bericht als Korrektur aufführen.
- Weichen die Quellen untereinander ab oder gibt es < 2 Quellen → Größe `status: gesperrt`, `grund: "<maß>: <quelle A> <wert>, <quelle B> <wert>"`.
- Längenreihe: übernommen werden nur Längen, die ≥ 2 Quellen nennen; fallen Längen weg oder kommen hinzu, im Bericht aufführen.
- Eine Größe ist `abgeglichen`, wenn alle Maße und die Längenreihe nach diesen Regeln stehen; dann `grund` entfernen.
- `quellen`: je benutzter Quelle `{url, titel, abgerufen, groessen}` (nur Größen, für die sie Werte geliefert hat).

Danach `.venv\Scripts\python.exe -m swki normteil tabellen-pruefen` → `"gueltig": true` (Regeln, „Maße steigen“, Quellenpflicht). Verletzt ein übernommener Wert eine Regel, die Größe sperren und im Bericht nennen – nicht die Regel ändern.

- [ ] **Step 3 (Implementer): Tests und Commit**

Run: `.venv\Scripts\python.exe -m pytest -q` → unverändert grün (Volumentests rechnen mit den Tabellenwerten).

```powershell
git add docs/stufe3a/abgleich swki/wissen/normteile/iso4762.yaml swki/wissen/normteile/iso4032.yaml swki/wissen/normteile/iso7089.yaml swki/wissen/normteile/iso8734.yaml
git commit -m "normteile: Normtabellen mit Web-Recherche abgeglichen (>= 2 Quellen je Wert)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4 (Controller): Widersprüche an den Nutzer**

Gesperrte Größen dem Nutzer vorlegen – **eine Frage je Widerspruch, mit Empfehlung** (globale Vorgabe des Nutzers).
Entscheidet der Nutzer einen Wert, setzt ein Implementer ihn ein, schreibt
`entscheidung: "Nutzer <Datum>: <maß> = <wert> (<Quellen und Werte>)"` in die Größe, setzt `status: abgeglichen` und
entfernt `grund` (die dokumentierte Entscheidung ersetzt die Quellenpflicht, Task 4). Ohne Entscheidung bleibt die Größe
gesperrt. Danach `swki normteil tabellen-pruefen`, `pytest`, Commit
`"normteile: Nutzerentscheidungen zu gesperrten Groessen"` mit Trailer.

---

### Task 11: Prüfer-Urteile je Vorlage, `hole` live, Stichprobe

**Files:**
- Create: `swki/wissen/normteile/vorlagen/iso4762.pruefer.json`, `iso4032.pruefer.json`, `iso7089.pruefer.json`, `iso8734.pruefer.json` (über `swki normteil urteil`)
- Create: `tests/live/test_live_normteil_hole.py`, `tests/live/test_live_normteile_stichprobe.py`

**Interfaces:**
- Consumes: abgeglichene Tabellen (Task 10), Befehle (Task 6).

- [ ] **Step 1 (Implementer): Musterteile bauen**

Vorbedingungen (eine Instanz, `False 1`). Je Norm:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe -m swki normteil muster "ISO 4762"
```

(ebenso ISO 4032, ISO 7089, ISO 8734). Erwartet je Norm `"bestanden": true`. Die Ausgaben (Pfade `spec`, `pruefbericht`, `bilder`, `tabelle`, `vorlage`, `vorlage_pruefsumme`) in den Bericht übernehmen und **anhalten** (Status DONE_WITH_CONCERNS „Urteile ausstehend“) – den Prüfer startet der Controller.

- [ ] **Step 2 (Controller): Prüfer-Agent je Norm**

Je Norm einen Prüfer-Agenten (`subagent_type: pruefer`) mit den Pfaden: Normtabelle (als Eingabe), erzeugte Spezifikation `spec.yaml` (als freigegebene Spezifikation), `pruefbericht.json`, Screenshot-Ordner. Zusatzhinweis an den Prüfer: „Normteil in vereinfachter Darstellung (Nenn-Ø ohne Gewinde, siehe Kommentar der Vorlage); prüfe Form, Lage (Achse = Y, Auflage auf y = 0) und dass jedes Tabellenmaß belegt ist.“ Das rohe JSON-Urteil in eine Datei schreiben und ablegen:

```powershell
.venv\Scripts\python.exe -m swki normteil urteil "ISO 4762" <urteil.json> --vorlage-pruefsumme <aus Step 1>
```

Ein nicht bestandenes Urteil: Mängel an einen Implementer zur Korrektur der Vorlage (neue Vorlage → neues Musterteil → neues Urteil).

- [ ] **Step 3 (Implementer, fortgesetzt): Live-Test `tests/live/test_live_normteil_hole.py`**

```python
"""Live: swki normteil hole baut, prüft und legt ab; zweiter Abruf ist ein Cache-Treffer (Bibliothek in tmp_path)."""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from swki.konfig import lade_rechner
from swki.normteile import befehle

pytestmark = pytest.mark.sw


@pytest.mark.parametrize(("norm", "groesse"), [("ISO 4762", "M8x30"), ("ISO 4032", "M8"), ("ISO 7089", "M8"),
                                               ("ISO 8734", "8x30")])
def test_hole_baut_und_trifft_den_cache(norm, groesse, tmp_path, monkeypatch):
    r = replace(lade_rechner(), normteilbibliothek=tmp_path / "bib")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    erst = befehle.hole(norm, groesse)
    try:
        assert erst["gebaut"] is True and Path(erst["pfad"]).is_file()
        zweit = befehle.hole(norm, groesse)
        assert zweit["gebaut"] is False and zweit["pfad"] == erst["pfad"]
    finally:
        shutil.rmtree(erst["lauf"], ignore_errors=True)
```

Ist eine der Größen nach Task 10 gesperrt, eine abgeglichene Größe derselben Norm wählen (im Bericht nennen).

- [ ] **Step 4: Live-Stichprobe `tests/live/test_live_normteile_stichprobe.py`**

```python
"""Live-Stichprobe (Spec 3a §12): 20 zufällig gewählte abgeglichene Normteile über alle Normen bestehen die
Selbstprüfung und werden abgelegt (Bibliothek in tmp_path; fester Seed, damit Wiederholungen dieselben Teile bauen)."""

import random
import shutil
from dataclasses import replace

import pytest

from swki.konfig import lade_rechner
from swki.normteile import befehle
from swki.normteile.tabelle import lade_normtabelle, normen

pytestmark = pytest.mark.sw


def _stichprobe(anzahl: int = 20, seed: int = 3) -> list[tuple[str, str, str]]:
    alle = []
    for name in normen():
        t = lade_normtabelle(name)
        for g, z in t["groessen"].items():
            if z["status"] != "abgeglichen":
                continue
            for laenge in z.get("laengen") or [None]:
                for v in t["varianten"]:
                    alle.append((t["norm"], g if laenge is None else f"{g}x{laenge:g}", v))
    return random.Random(seed).sample(alle, anzahl)


@pytest.mark.parametrize(("norm", "groesse", "variante"), _stichprobe())
def test_stichprobe(norm, groesse, variante, tmp_path, monkeypatch):
    r = replace(lade_rechner(), normteilbibliothek=tmp_path / "bib")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    ergebnis = befehle.hole(norm, groesse, variante)
    try:
        assert ergebnis["gebaut"] is True and ergebnis["pruefung"]["bestanden"] is True
    finally:
        shutil.rmtree(ergebnis["lauf"], ignore_errors=True)
```

- [ ] **Step 5: Live-Läufe**

```powershell
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_normteil_hole.py --zeit 240
.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_normteile_stichprobe.py --zeit 240
```

Private Bytes nach jeder Datei; bei ca. 4 GB anhalten (Status BLOCKED, erledigte und offene Tests nennen). Einstellungen danach `False 1`.

- [ ] **Step 6: Commit**

```powershell
git add swki/wissen/normteile/vorlagen/iso4762.pruefer.json swki/wissen/normteile/vorlagen/iso4032.pruefer.json swki/wissen/normteile/vorlagen/iso7089.pruefer.json swki/wissen/normteile/vorlagen/iso8734.pruefer.json tests/live/test_live_normteil_hole.py tests/live/test_live_normteile_stichprobe.py
git commit -m "normteile: Pruefer-Urteile je Vorlage, hole live, Stichprobe 20 Teile" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Skill `normteile`, CLAUDE.md, Design-Dokument, Ergebnisse, Regression

**Files:**
- Create: `.claude/skills/normteile/SKILL.md`, `docs/stufe3a/ergebnisse.md`
- Modify: `CLAUDE.md`, `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` (§8, §11), `.claude/skills/konstruieren/SKILL.md` (Verweis auf Normteile)

- [ ] **Step 1: `.claude/skills/normteile/SKILL.md`**

```markdown
---
name: normteile
description: Genormte Verbindungselemente (Schrauben, Muttern, Scheiben, Stifte) abrufen oder erstmals bauen lassen – immer über swki normteil, nie als STEP-Download oder freihändig konstruiert. Verwenden, wenn ein Teil, eine Baugruppe oder der Nutzer ein Normteil braucht oder eine neue Größe/Norm aufgenommen werden soll.
---

# Normteile

Genormte Teile kommen **immer** aus `swki normteil` (Spec `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md`).
Herstellerdaten (STEP) nur für nicht genormte Kaufteile.

## Abrufen
`.venv\Scripts\python.exe -m swki normteil hole "<Norm>" <Größe>[x<Länge>] [--variante <v>]`
- Vorhanden und aktuell → Pfad (`gebaut: false`). Sonst baut swki das Teil, prüft es vollständig selbst und legt es ab.
- Verfügbar: ISO 4762, ISO 4032, ISO 7089, ISO 8734 (`swki normteil tabellen-pruefen` zeigt Größen und gesperrte).

## Fehlercodes
| Code | Vorgehen |
|---|---|
| `NORMLAENGE_UNGUELTIG` | Nächste Normlänge (`naechste`) vorschlagen, nicht still ändern |
| `NORMTEIL_UNBEKANNT`, `NORMVARIANTE_UNBEKANNT` | Vorhandene Größen/Varianten nennen; neue Größe → „Erweitern“ |
| `NORMTEIL_GESPERRT` | Grund nennen; Nutzer entscheidet den Wert (eine Frage, mit Empfehlung) |
| `NORMVORLAGE_UNGEPRUEFT` | `swki normteil muster "<Norm>"` → Prüfer-Agent (`subagent_type: pruefer`) mit Tabelle, `spec`, `pruefbericht`, Bildern → Urteil als rohes JSON in Datei → `swki normteil urteil "<Norm>" <datei> --vorlage-pruefsumme <x>` |
| `NORMTABELLE_UNGUELTIG` | Befunde beheben (Tabelle), nie Regeln aufweichen |
| `NORMTEIL_PRUEFUNG` | Fehler in Vorlage oder Tabelle – melden, Laufordner nennen; Sollwerte nie an Messwerte anpassen |

## Erweitern (neue Größe oder Norm)
1. Tabelle `swki/wissen/normteile/<norm>.yaml` ergänzen (Werte aus Normwissen, `status: gesperrt`).
2. Abgleich: ≥ 2 unabhängige recherchierte Quellen je Wert (Claudes Wissen zählt nicht); Widersprüche → gesperrt, Nutzer fragen.
3. Neue Norm: Bauvorlage `vorlagen/<norm>.yaml` (alle Maße als Ausdrücke, Einbaureferenzen `EINBAU_*`, `pruefung` misst jedes Tabellenmaß), Unit-Tests (Volumen), Live-Test, Prüfer-Urteil.
4. `swki normteil tabellen-pruefen` und `pytest` grün.
```

- [ ] **Step 2: `CLAUDE.md`**

Im Abschnitt „## SolidWorks“ nach „Nur im Arbeitsordner speichern …“ ergänzen:

```markdown
- Normteile: `swki normteil` kopiert selbst gebaute und geprüfte Teile in die `normteilbibliothek` (config/rechner.yaml) – sonst nichts dorthin schreiben.
```

Neuer Abschnitt nach „## Konstruieren (Stufe 2)“:

```markdown
## Normteile (Stufe 3a)
- Genormte Teile immer über `swki normteil hole` (Skill `normteile`), nie als STEP-Download oder freihändig konstruiert. Herstellerdaten nur für nicht genormte Kaufteile.
- Normtabellen (`swki/wissen/normteile/`) nur mit Abgleich erweitern: ≥ 2 unabhängige recherchierte Quellen je Wert; Widersprüche sperren und den Nutzer fragen.
- Bauvorlagen nur mit neuem Prüfer-Urteil (`swki normteil muster` → Prüfer → `swki normteil urteil`).
```

- [ ] **Step 3: Design-Dokument**

`docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`:
- §8 Normteile: am Anfang ergänzen „**Stand Stufe 3a (2026-10-02):** Genormte Teile werden selbst konstruiert, aus Normtabelle und Bauvorlage, prüfen sich selbst und füllen eine lokale Bibliothek – siehe [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md). Katalog je Hersteller und `normteil aufnehmen` gelten nur noch für nicht genormte Kaufteile (eigenes Paket bei Bedarf); der Toolbox-Rückfall entfällt.“
- §11: Zeile „3“ ersetzen durch zwei Zeilen:
  - `| 3a | Normteile: Normtabellen mit Abgleich, Bauvorlagen, Selbstprüfung, Bibliothek (ISO 4762, 4032, 7089, 8734) – Design: [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md) | Tabellen abgeglichen oder begründet gesperrt, Prüfer-Urteile je Vorlage, Stichprobe 20 Teile besteht |`
  - `| 3b | Baugruppen statisch: Standardverknüpfungen, Bestimmtheit, statische Kollision | allgemeine Referenzbaugruppe besteht (Festlegung in der Spec 3b) |`

`.claude/skills/konstruieren/SKILL.md`: im Abschnitt zur Spezifikation eine Zeile „Braucht das Teil Normteile (Schrauben, Stifte …), diese über den Skill `normteile` holen.“

- [ ] **Step 4: `docs/stufe3a/ergebnisse.md`**

Abschnitte: Stand (Datum, Branch, Commits), Unit-Testzahl, Live-Ergebnis je Datei mit Speicher und Einstellungen, Spike S11 (Antworten), Abgleich (je Norm: Quellen, Korrekturen, gesperrte Größen mit Grund und Nutzerentscheidungen), Prüfer-Urteile, Stichprobe (Teile, Ergebnis), Präzisierungen gegenüber der Spec (siehe Kopf dieses Plans), offene Punkte (kosmetisches Gewinde, Kaufteile, weitere Normen, Rechner B).

- [ ] **Step 5: Gesamtlauf**

Run: `.venv\Scripts\python.exe -m pytest -q` → grün (Zahl berichten).
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.
Run: `.venv\Scripts\python.exe -m swki normteil tabellen-pruefen` → `"gueltig": true`.
Live-Regression (eine Instanz, `False 1`, dateiweise, Speicher beachten): `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz --zeit 240` → Buchse, Formplatte, Auswerferhalteplatte OK; dazu `tests\live\test_live_muster.py`, `test_live_pruefen.py`, `test_live_referenz.py`, `test_live_durchmesser.py` einzeln.

- [ ] **Step 6: Commit**

```powershell
git add .claude/skills/normteile/SKILL.md .claude/skills/konstruieren/SKILL.md CLAUDE.md docs/superpowers/specs/2026-09-26-solidworks-ki-design.md docs/stufe3a/ergebnisse.md
git commit -m "docs: Skill normteile, CLAUDE.md, Design §8/§11, Ergebnisse Stufe 3a" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Übergabe (mit Nutzer)**

Kein Push ohne Rückfrage: Testzahlen, Live-Ergebnis, Abgleich und gesperrte Größen zeigen und fragen, ob gepusht und ein Pull Request angelegt werden soll.

---

## Abdeckung (Selbstprüfung)

| Spec | Task |
|---|---|
| §2 Zuschnitt, Herkunft, Gewinde, Umfang | Global Constraints, 7–9 |
| §2/§4 Abgleich ≥ 2 Quellen, gesperrt + Nutzer | 4 (Quellenpflicht), 10 |
| §3 Bausteine, `normteilbibliothek` | 4, 6 |
| §4 Normtabelle (Format, Regeln, Quellen, `tabellen-pruefen`) | 4, 6 |
| §5 Bauvorlage, Eigenschaften, keine festen Zahlen | 5, 7–9 |
| §5 Einbaureferenzen | 2, 7–9 |
| §6 Selbstprüfung (Tabelle, Spec, Bau, Maße, Volumen, Referenzen) | 3, 5, 6, 7–9 |
| §6 Prüfer-Agent je Vorlagenversion, `NORMVORLAGE_UNGEPRUEFT` | 6, 11 |
| §7 Befehle `hole`, `tabellen-pruefen`, `liste` (+ `muster`, `urteil`) | 6 |
| §8 Fehlercodes | 4–6 |
| §9 Skill, CLAUDE.md, Design §8/§11, Passung Normbohrung | 9, 12 |
| §10 Spikes S11a–c | 1 |
| §11 Tests (unit, live, Verfälschung – präzisiert) | 2–9, 11 |
| §12 Fertig-Kriterium (Abgleich, Urteile, Stichprobe 20, Regression) | 10–12 |
| §13 Reihenfolge | Task-Reihenfolge |
