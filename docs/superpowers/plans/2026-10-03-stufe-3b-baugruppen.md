# Stufe 3b – Baugruppen statisch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** swki baut aus einer freigegebenen Baugruppen-Spezifikation eine statische Baugruppe aus Eigenteilen und Normteilen, verknüpft sie voll bestimmt, prüft Verknüpfungen, Bestimmtheit, Kollision (mit Gewindepaarungen), Lage und jedes Eigenteil und erkennt manuelle Änderungen an gebauten Dateien vor jedem neuen Lauf.

**Architecture:** Neues Paket `swki/baugruppe/` (Modell, Laden und Auflösen von `je_position`, Plausibilität und Passung, Freigabe, Referenzauflösung, SolidWorks-Helfer, Bau, Bewertung, Prüfen). Die vorhandenen Befehle `validieren`, `freigeben`, `bauen`, `pruefen`, `status`, `bericht` verzweigen nach `art`. Neues Modul `swki/aenderungen.py` (SHA-256 je gespeicherter Datei im Protokoll, Verweigern bei Abweichung, Befehl `swki aenderungen`) gilt für Teile und Baugruppen. Der Teil-Bau wird als Funktion `baue_teil_dokument` herausgelöst und von der Baugruppe wiederverwendet.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) für Spike und Live-Tests.

**Spec:** `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md` (mit dem Nutzer abgestimmt, 2026-10-03). Kontext: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`, `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md`.

## Präzisierungen gegenüber der Spec (vom Planer, bindend für diesen Plan)

1. **Gewindepaarung über die Lage (Spec §9.3):** Eine Gewindepaarung ist eine ISO-4762-Instanz, deren Achse (aus `EINBAU_EBENE`: Ursprung und Normale) durch den Eintrittspunkt einer `normbohrung` `art: gewinde` einer Eigenteil-Instanz läuft (Abstand ≤ `toleranzen.anker_mm`). In der Praxis wird die Schraube auf die Senkung im Deckel verknüpft, nicht auf das Gewinde im Unterteil; die Zuordnung über die Verknüpfung fände sie nicht. Eintrittspunkte stammen aus dem Bauprotokoll (`punkte` der Bohrungsinstanzen), die Einschraublänge ist `l − |(Eintritt − Kopfauflage) · Achse|`.
2. **Gewinde `durch`:** Das Volumen wird nicht gegen ein Soll geprüft (Prüfung `ok: null` mit Hinweis), weil die Bohrungslänge nicht in der Spezifikation steht. Die Stehlager-Referenz nutzt Gewinde mit `tiefe`.
3. **ISO 8734 `c` (Spec §12):** Für Fasen gibt es keine Messart (`masse_pruefen` misst Ebenen, Achsen, Punkte; `durchmesser_pruefen` nur Zylinder). `c` bleibt wie in 3a über das Volumen belegt; die neue Vorlagenversion misst nur `EINBAU_EBENE_2` gegen +y mit Soll 0. **Dem Nutzer bei der Übergabe als Abweichung von Spec §12 melden.**
4. **Teilprüfung:** je Teil-Spec eine Teilprüfung (nicht je Instanz); Präfix und Knoten nennen die erste Komponente mit dieser Teil-Spec (`unterteil: mass:…`, Knoten `unterteil/f5`).
5. **Messpunkte der Baugruppe (`pruefung.masse_pruefen`):** `{punkt}` in Baugruppenkoordinaten oder `komponente` (bei `je_position`-Komponenten die Instanz, z. B. `stift.1`) plus ein Messpunkt des Teil-Formats (`referenz`, `{feature, flaeche}`, `{feature, instanz, achse}`). Standardebenen, `nahe` und Instanzflächen gibt es nur in Verknüpfungen. Gemessen wird im Teildokument, übertragen mit `IComponent2.Transform2`.
6. **Gesamtmasse** in kg (`pruefung.masse.soll`).
7. **Bestimmtheit und Kollision** sind je eine Prüfung (`bestimmtheit`, `kollision`) mit allen abweichenden Komponenten als Knoten (Instanz-IDs); Gewindepaarungen sind je Schraube eine Prüfung `gewinde:<instanz>`.
8. **Änderungserkennung:** Verglichen wird der höchste Lauf mit Protokollstatus `ok`. Hat er keine Prüfsummen (vor 3b gebaut) oder fehlt sein Lauf-Ordner ganz (aufgeräumt), wird nicht verweigert. `swki aenderungen` vergleicht `.sldprt`/`.sldasm` inhaltlich (globale Variablen; bei Baugruppen zusätzlich Abstands-/Winkelverknüpfungen); andere geänderte Dateien (STEP) werden nur genannt.
9. **Konzentrisch ohne `ausrichtung`:** swki versucht `gleich`, bei Fehler (Status, Fehlercode oder Rebuild) löscht es die Verknüpfung und versucht `entgegengesetzt`. Der Skill empfiehlt „Ebene vor Achse“ (erst die axiale Verknüpfung mit `ausrichtung`, dann `konzentrisch`).
10. **Huellquader der Baugruppe** über `IAssemblyDoc.GetBox(0)`; ob er eng anliegt, klärt Spike S12 (sonst Toleranz nach Ledger-Entscheidung, siehe „Abhängigkeiten vom Spike“).

## Global Constraints

- **Umfang 3b statisch:** Standardverknüpfungen (`deckungsgleich`, `konzentrisch`, `parallel`, `senkrecht`, `abstand`, `winkel`), Bestimmtheit, statische Kollision. Keine Bewegungen, keine treibenden oder mechanischen Verknüpfungen, keine gezählten Freiheitsgrade (Stufe 4), keine Unterbaugruppen, keine Konfigurationen, keine SW-Komponentenmuster.
- **Eine Freigabe** für Baugruppe und alle Teil-Specs; jeder Baugruppen-Lauf baut alle Eigenteile frisch.
- **Normteile** nur über `swki normteil hole`; die Datei wird in den Lauf-Ordner kopiert; die Baugruppe verweist nie auf die Bibliothek und schreibt nie dorthin.
- **Bestimmtheit:** jede Komponente voll bestimmt (`swFullyConstrained` = 3), außer `freiheitsgrade: {<komponente|gruppe>: unterbestimmt}`; überbestimmt ist immer ein Mangel. Konzentrische Verknüpfungen mit Normteil: `drehung_sperren` Vorgabe `true`.
- **Kollision:** Berührung ist keine Kollision (`TreatCoincidenceAsInterference = False`); jede Überlappung außer einer Gewindepaarung ist ein Mangel. Gewindepaarung: Ring zwischen Nenn-Ø und Kernloch-Ø (`swki/wissen/bohrungsnormen.yaml`, `kernloch`) über die Einschraublänge, abzüglich der Endfase `p` der Schraube; Toleranz `TOL_GEWINDE_PROZENT = 1.0` (nach Spike S12 bestätigen); Mangel, wenn die Einschraublänge `gewindetiefe` oder `tiefe` übersteigt.
- **Spec bleibt Quelle:** manuelle Änderungen werden erkannt (`MANUELL_GEAENDERT`), nie automatisch übernommen; Übernahme nur nach Bestätigung des Nutzers mit neuer Freigabe; `swki bauen --verwerfen` nur auf ausdrückliche Anweisung. `swki pruefen` und `swki aenderungen` speichern nie.
- **Freigabe-Prüfsumme der Baugruppe:** `art, name, parameter, eigenschaften, komponenten, freiheitsgrade, pruefung` plus `teile` = {Dateiname: Prüfsumme der Teil-Spec}. **Verknüpfungen sind Bauweg.**
- **Late Binding** (`swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()` (`Transform2`, `ArrayData`, `GetConstrainedStatus`, `IsFixed`, `Name2`, `GetPathName`, `GetFirstSubFeature`, `GetSpecificFeature2`, `GetInterferences`, `Components`, `Volume`, `GetCount` …). Nullargumentige **Aktionen** (`FixComponent`, `EditDelete`, `IInterferenceDetectionMgr.Done`) immer über `_FlagAsMethod(name)` und dann mit `()` aufrufen (S5 rief `EditDelete()`/`Done()` als Methode auf, S9a `EditRebuild3` ohne – die Markierung macht es eindeutig).
- **Einheiten:** Spezifikation und Ausgaben in mm und Grad; die API rechnet in m und rad (`mm()`, `grad()`, `in_mm()`, `in_mm3()` aus `swki.verbindung`).
- **API nachschlagen:** vor jedem neuen SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` bzw. `… api enum <Name>` (vorher `PYTHONIOENCODING=utf-8`). `swki api pruefe-code` muss ohne Befunde bleiben. Bereits nachgeschlagen (2026-10-03): `IAssemblyDoc.AddComponent5` (8: CompName, ConfigOption, NewConfigName, UseConfigForPartReferences, ExistingConfigName, X, Y, Z), `IAssemblyDoc.AddMate5` (15: MateTypeFromEnum, AlignFromEnum, Flip, Distance, DistanceAbsUpperLimit, DistanceAbsLowerLimit, GearRatioNumerator, GearRatioDenominator, Angle, AngleAbsUpperLimit, AngleAbsLowerLimit, ForPositioningOnly, LockRotation, WidthMateOption, ErrorStatus), `IAssemblyDoc.CreateMate` (1, seit 2018, nicht verwendet), `IAssemblyDoc.FixComponent` (0), `IAssemblyDoc.GetComponents` (1: ToplevelOnly), `IAssemblyDoc.GetBox` (1: Options), `IAssemblyDoc.InterferenceDetectionManager` (Property), `IAssemblyDoc.ResolveAllLightWeightComponents` (1: WarnUser), `IComponent2.GetCorrespondingEntity` (1), `IComponent2.FeatureByName` (1), `IComponent2.Transform2` (Property), `IComponent2.SetTransformAndSolve2` (1), `IComponent2.Select4` (3: Append, Data, ShowPopup), `IComponent2.GetConstrainedStatus` (0), `IComponent2.IsFixed` (0), `IComponent2.Name2`, `IComponent2.GetPathName` (0), `IInterferenceDetectionMgr.GetInterferences` (0), `.TreatCoincidenceAsInterference` (Property), `.Done` (0), `IInterference.Components`, `IInterference.Volume` (m³), `IFeature.GetErrorCode2` (1: IsWarning, ByRef), `IFeature.Select2` (2: Append, Mark), `IFeature.Parameter` (1: Name), `IDimension.SystemValue`, `IEntity.Select4` (2: Append, Data), `IMate2.Type`, `IEquationMgr.Add2` (3), `.Value`/`.Equation`/`.GlobalVariable` (1: Index), `.GetCount` (0), `IMathUtility.CreateTransform` (1), `IModelDoc2.EditDelete` (0), `ISldWorks.OpenDoc6` (6). Enums: `swMateType_e` COINCIDENT 0, CONCENTRIC 1, PERPENDICULAR 2, PARALLEL 3, DISTANCE 5, ANGLE 6; `swMateAlign_e` ALIGNED 0, ANTI_ALIGNED 1, CLOSEST 2; `swAddMateError_e` NoError **1** (0 = unbekannter Fehler), OverDefinedAssembly 5; `swConstrainedStatus_e` Under 2, Fully 3, Over 4; `swDocumentTypes_e` PART 1, ASSEMBLY 2.
- **Bestand bleibt:** Referenzen *Buchse*, *Formplatte*, *Auswerferhalteplatte* bestehen weiter; Verhalten von `swki bauen`/`pruefen` für Teile unverändert bis auf Prüfsummen, Änderungserkennung und `--verwerfen`.
- **Prüfwerte nie an Messwerte anpassen.**
- **Sprache:** Code-Bezeichner, Docstrings, Kommentare, Commit-Messages, Berichte auf Deutsch.
- **Tests:** `.venv\Scripts\python.exe -m pytest -q` (ohne SolidWorks; Stand vor dem Plan: **456 passed, 95 deselected**). Jeder Task nennt, wie viele Tests er hinzufügt; maßgeblich ist „vorher + neu“, abweichende Zahlen im Bericht begründen. Live-Tests nur einzeln: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> --zeit 300` mit `PYTHONIOENCODING=utf-8`.
- **SolidWorks-Speicher (Live-Tasks):** Private Bytes von `SLDWORKS.exe` messen (`Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`), nicht das Working Set. Ab ca. 4 GB startet **der Controller** SolidWorks neu (Nutzervorgabe 2026-10-03): genau eine Instanz, keine fremden offenen Dokumente, `ExitApp`, Start über `installationsordner` aus `config/rechner.yaml`; danach prüfen: eine Instanz, Fenster sichtbar, Toggle 10 / Integer 6 = `False 1`. Implementer halten bei ca. 4 GB nach der laufenden Testdatei an und melden das. Genau eine Instanz (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`); nie eine fremde Instanz beenden. Einstellungen vor und nach Live-Läufen: `.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); print(app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6))"` → `False 1`. Eine Stehlager-Baugruppe kostet grob 0,6–1 GB; Live-Dateien mit mehreren Baugruppen bei Bedarf zwischen den Dateien neu starten.
- **Git:** Branch `stufe-3b` (von `plan-stufe-3b`), kleine Commits je Task; Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **kein `git push` ohne Rückfrage**; nichts aus `auftraege/` committen; erzeugte SolidWorks-Dateien nie committen; immer gezielt `git add <dateien>`.
- **Subagents:** Implementer starten keine Subagents. Prüfer-Agenten startet der Controller. Nie zwei Implementer gleichzeitig, solange SolidWorks läuft.

## Dateistruktur nach diesem Plan

```
schema/baugruppe.schema.json            neu: Schema der Baugruppen-Spezifikation
swki/spec/laden.py                      schema_befunde(spec, erwartet), art_der_datei()
swki/spec/freigabe.py                   Prüffelder Baugruppe, Teil-Prüfsummen (teile=…)
swki/spec/befehle.py                    validieren/freigeben verzweigen nach art
swki/baugruppe/__init__.py              neu
swki/baugruppe/fehler.py                neu: TEIL_BAU, KOMPONENTE_FEHLER, VERKNUEPFUNG_FEHLER
swki/baugruppe/modell.py                neu: Quelle, Baugruppe, dokument_name()
swki/baugruppe/aufloesen.py             neu: Instanz, Verknuepfung, instanzen(), verknuepfungen()
swki/baugruppe/laden.py                 neu: lade_baugruppe() (Schema, Teil-Specs, Normteile, Plausibilität)
swki/baugruppe/plausibel.py             neu: Plausibilität (Spec 3b §5)
swki/baugruppe/passung.py               neu: Passung Normteil ↔ Bohrung
swki/baugruppe/hinweise.py              neu: Hinweise (nahe, feste Zahlen, Teil-Hinweise)
swki/baugruppe/freigabe.py              neu: freigeben_baugruppe(), pruefe_freigabe_baugruppe()
swki/baugruppe/befehle.py               neu: validieren(), freigeben() für die Weichen
swki/baugruppe/referenzen.py            neu: TeilReferenz, loese_im_teil(), flaeche_der_instanz()
swki/baugruppe/sw_baugruppe.py          neu: SolidWorks-Helfer (einfügen, fixieren, verknüpfen, lesen)
swki/baugruppe/bau.py                   neu: bauen() für Baugruppen
swki/baugruppe/geometrie.py             neu: transformiere(), einschraublaenge(), ueberlappung_soll()
swki/baugruppe/bewertung.py             neu: BaugruppenMesswerte, gewindepaarungen(), bewerte_baugruppe()
swki/baugruppe/pruefen.py               neu: pruefen() für Baugruppen
swki/aenderungen.py                     neu: Prüfsummen, Änderungserkennung, swki aenderungen
swki/compiler/protokoll.py              + sha256, verworfen, teile, komponenten, normteile
swki/compiler/bauen.py                  baue_teil_dokument() herausgelöst, Prüfsummen, --verwerfen, Weiche
swki/pruefung/messen.py                 oeffne() nach Endung, messgeometrie() öffentlich
swki/pruefung/befehle.py                Weichen pruefen/status/bericht, schreibe_pruefbericht()
swki/pruefung/bericht.py                Abschnitte Stückliste, Normteile, Gewindepaarungen, Teilprüfungen
swki/cli.py                             + Befehlsgruppe aenderungen
swki/wissen/normteile/vorlagen/iso7089.yaml, iso8734.yaml (+ neue *.pruefer.json)
spikes/s12_baugruppe.py                 Spike S12
tests/baugruppe/…                       Unit-Tests; tests/test_aenderungen.py
tests/live/test_live_baugruppe.py, test_live_aenderungen.py, test_live_stehlager.py
tests/referenz/stehlager/               Referenz Stehlager (4 Specs) + Eintrag in test_referenzen.py
.claude/skills/baugruppe/SKILL.md       neu; konstruieren, normteile, .claude/agents/pruefer.md, CLAUDE.md, Design §4/§6/§11
docs/stufe3b/ergebnisse.md              Ergebnisse 3b
```

## Abhängigkeiten vom Spike S12 (Task 1)

Der Plan-Code setzt die Spalte „Annahme“ voraus. Weicht der Spike ab, entscheidet der Controller nach der Spalte „sonst“ und hält es im Ledger fest, bevor der betroffene Task beginnt.

| # | Frage | Annahme (Plan-Code) | sonst | betrifft |
|---|---|---|---|---|
| 1 | `AddComponent5` mit Boxzentrum → Ursprung im Baugruppenursprung | ja (Translation ≈ 0); `fuege_ein` setzt bei Abweichung zusätzlich die Identität per `SetTransformAndSolve2` | nur Identität setzen (Box weglassen) | 7 |
| 2 | `FixComponent` (als Methode markiert) → `IsFixed` | `True` | anderen Weg im Ledger (z. B. erste Komponente schon fixiert) | 7 |
| 3 | Auswahl in der Komponente | Bezugs-/Standardebenen und -achsen über `IComponent2.FeatureByName` + `Select2(…, 1)`; Flächen über `GetCorrespondingEntity` + `Select4` mit Marke 1 | `SelectByID2("<Name>@<Name2>@<Baugruppe>", "PLANE"/"AXIS", …)` | 7 |
| 4 | `AddMate5` für die sechs Typen | Status 1, Mate ≠ None, Feature umbenennbar, `GetSpecificFeature2.Type` = Typ | betroffenen Typ im Ledger sperren und dem Nutzer melden | 7, 8 |
| 5 | Bedeutung der Ausrichtung | `gleich` (ALIGNED) = Normalen nach dem Verknüpfen gleichgerichtet, auch bei Bezugsebene ↔ Fläche | Abbildung `AUSRICHTUNG` in `sw_baugruppe.py` tauschen; die Spec-Bedeutung „Normalen gleich-/gegensinnig“ bleibt | 7, 11 |
| 6 | `LockRotation` | Schraube mit Sperre Status 3, Stift ohne Sperre Status 2 | Spec-Frage an den Nutzer (Bestimmtheit) | 9, 11 |
| 7 | Status der fixierten Komponente | beliebig; geprüft wird nur `IsFixed` | – | 9 |
| 8 | Maß der Abstands-/Winkelverknüpfung | `Parameter("D1")`, Gleichung `"D1@<Name>" = "S"` bindet und verschiebt nach Änderung von `S` | Namen in `MASS_NAME` ändern | 7, 10 |
| 9 | Kollision | Stift Ø 8 in Ø 8 und Schraubenkopf auf Fläche: keine Interferenz; Schraube in Gewinde: genau ein Paar, Volumen innerhalb 1 % des Ring-Solls | Kleinstvolumen für Berührungen messen → Schwelle `KOLLISION_MIN_MM3` (Ledger); Toleranz `TOL_GEWINDE_PROZENT` anpassen nur mit Begründung aus dem Spike | 9 |
| 10 | Wieder öffnen | nach `OpenDoc6` (Typ 2) + `ResolveAllLightWeightComponents(False)` gleiche Interferenzen, Status und Mate-Namen | Abweichung → Ledger, Prüfen ggf. vor dem Schließen im Bau | 10 |
| 11 | Rücklesen | `IEquationMgr.Value` der globalen Variablen in mm (wie S9a); SHA-256 nach Öffnen und Schließen ohne Speichern unverändert (Teil und Baugruppe) | ändert sich der Hash schon beim Öffnen: Änderungserkennung auf Zeitstempel + Größe umstellen (Ledger, Nutzer informieren) | 5 |
| 12 | Transform-Konvention | Zeilenvektor: `ArrayData[0:3]` = Bild der x-Achse (wie die Ebenennormale `ArrayData[6:9]` in S11); Normale der Fläche im Baugruppenkontext = gedrehte Teilnormale | Spaltenkonvention: Indizes in `transformiere` tauschen | 9 |
| 13 | Ebene + zwei konzentrische | Status 3 oder 4 wird festgehalten | bei 4: Skill-Regel „zweite Bohrung über `parallel` statt `konzentrisch`“ (Stehlager nutzt ohnehin `parallel`) | 12 |
| 14 | `GetBox(0)` | eng (± 0,01 mm zum Soll) | `huellquader_tol` der Stehlager-Referenz nach Messwert (Ledger) | 11 |

---

### Task 1: Spike S12 – Einfügen, Auswahl, Verknüpfungen, Kollision, Rücklesen, Messen (live)

**Files:**
- Create: `spikes/s12_baugruppe.py`
- Ergebnis: `docs/stufe0/ergebnisse/s12_baugruppe.json` (wird vom Spike geschrieben und committet)

**Interfaces:**
- Consumes: Compiler (`baue_features`, Handler), `swki normteil hole` (ISO 4762, ISO 8734 mit den Vorlagen aus 3a), `swki.pruefung.messen.oeffne`/`kontext_aus_datei`.
- Produces: Antworten auf die 14 Zeilen der Tabelle „Abhängigkeiten vom Spike S12“.

- [ ] **Step 1: Vorbedingungen prüfen**

SolidWorks 2025 läuft, genau eine Instanz, keine fremden offenen Dokumente, Einstellungen `False 1` (Befehle in den Global Constraints). Private Bytes notieren. `config/rechner.yaml` hat `vorlage_baugruppe`. Sonst anhalten und melden.

- [ ] **Step 2: `spikes/s12_baugruppe.py` schreiben**

```python
"""S12 (Stufe 3b): Baugruppen – Einfügen, Auswahl in Komponenten, Verknüpfungen, Kollision, Rücklesen, Messen.

a Einfügen: AddComponent5 mit dem Boxzentrum des Teils → liegt der Ursprung im Baugruppenursprung (Transform2)? Mit
  Bezugsebenen im Teil (Normteil); SetTransformAndSolve2(Identität); FixComponent (als Methode markiert) → IsFixed.
b Auswahl: IComponent2.FeatureByName(<Bezugsebene>) bzw. GetCorrespondingEntity(<Fläche>) liefern auswählbare Objekte
  (Select2 bzw. Select4, Marke 1).
c Verknüpfungen: AddMate5 für deckungsgleich, konzentrisch, parallel, senkrecht, abstand, winkel; Status
  (swAddMateError_e, 1 = ok); Ausrichtung bei Bezugsebene ↔ Fläche; LockRotation → Status 3 statt 2; Status der
  fixierten Komponente; Mate-Feature umbenennen; IMate2.Type; Maß "D1" und Gleichung "D1@<Name>" = "S"; Ebene + zwei
  konzentrische (überbestimmt?).
d Kollision: TreatCoincidenceAsInterference = False: Stift Ø 8 in Ø 8 → keine Interferenz; Schraube M8 (Nenn-Ø) in
  Gewinde M8 → ein Paar, Volumen gegen das Ring-Soll; nach Speichern und OpenDoc6 dieselben Werte.
e Rücklesen: globale Variablen eines gespeicherten Teils, SHA-256 vor/nach Öffnen und Schließen ohne Speichern.
f Messen: Transform-Konvention (Zeilen- oder Spaltenvektor) über die Normale einer Fläche im Baugruppenkontext;
  GetBox(0) gegen die bekannte Hülle.
g Speicher: Private Bytes notiert der Ausführende vor und nach dem Lauf.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s12_baugruppe
"""

import hashlib
import math
import shutil
from pathlib import Path

import pythoncom

from spikes._gemeinsam import lauf
from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.anker import zylinder_zu_punkten
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.compiler.topologie import flaechen, loese_flaeche
from swki.konfig import lade_rechner
from swki.normteile import befehle as normteil_befehle
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.schluessel import loese_auf
from swki.pruefung.messen import kontext_aus_datei, oeffne
from swki.verbindung import byref_bool, byref_long, grad, in_mm, in_mm3, mm, r8_array, verbinde

MATE = {"deckungsgleich": 0, "konzentrisch": 1, "senkrecht": 2, "parallel": 3, "abstand": 5, "winkel": 6}  # swMateType_e
GLEICH, ENTGEGEN = 0, 1  # swMateAlign_e: ALIGNED, ANTI_ALIGNED
IDENT = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]


def _block(name, laenge, breite, hoehe, weitere):
    return {"art": "teil", "name": name, "parameter": {"L": laenge, "B": breite, "H": hoehe}, "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}}, *weitere]}


SOCKEL = _block("S12_Sockel", 100, 60, 20, [
    {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[0, 0]], "tiefe": 16, "gewindetiefe": 12},
    {"id": "f3", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[30, 0]], "durch": True},
    {"id": "OBEN", "typ": "referenz", "ebene": {"basis": "oben", "abstand": "=H"}},
])
LASCHE = _block("S12_Lasche", 80, 60, 10, [
    {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 0]],
     "durchmesser": 9, "durch": True},
    {"id": "f3", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[30, 0]], "durch": True},
])


def _teil(app, r, spec, ordner):
    model = sw.neues_teil(app, r.vorlage_teil)
    ctx = Kontext(app, model, spec, ordner / f"{spec['name']}.yaml", 0.1)
    globale_variablen(model, spec["parameter"])
    fehler = baue_features(ctx, Protokoll("S12", spec["name"], 0, r.sw_jahr), alle_handler(), lambda c: sw.rebuild(c.model))
    if fehler is not None:
        raise fehler
    sw.speichere(model, ordner / f"{spec['name']}.sldprt")
    return model, ctx


def _normteil(app, norm, groesse, ordner):
    quelle = Path(normteil_befehle.hole(norm, groesse)["pfad"])
    ziel = ordner / quelle.name
    shutil.copy2(quelle, ziel)
    t, a = loese_auf(norm, groesse)
    model = oeffne(app, ziel)
    spec = erzeuge_spec(t, a, vorlage_text(t))
    return model, kontext_aus_datei(app, model, spec, ziel.with_suffix(".yaml"), 0.1, {"knoten": []})


def _neue_baugruppe(app, r):
    asm = app.NewDocument(str(r.vorlage_baugruppe), 0, 0, 0)
    if asm is None:
        raise RuntimeError(f"NewDocument {r.vorlage_baugruppe} fehlgeschlagen")
    return asm


def _einfuegen(app, asm, model, identitaet_setzen=False):
    box = sw.teilebox_mm(model)
    komp = asm.AddComponent5(model.GetPathName, 0, "", False, "", *[mm((box[i] + box[i + 3]) / 2) for i in range(3)])
    nach_einfuegen = [round(x, 9) for x in komp.Transform2.ArrayData]
    if identitaet_setzen:
        komp.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(IDENT)))
    return komp, {"box_mm": box, "transform_nach_einfuegen": nach_einfuegen,
                  "transform": [round(x, 9) for x in komp.Transform2.ArrayData]}


def _fixiere(asm, komp):
    asm.ClearSelection2(True)
    komp.Select4(False, asm.SelectionManager.CreateSelectData, False)
    asm._FlagAsMethod("FixComponent")
    asm.FixComponent()
    asm.ClearSelection2(True)
    return bool(komp.IsFixed)


def _entitaet(komp, ctx, seite):
    """(Objekt im Baugruppenkontext, ist_feature) für eine Referenz wie in Spec 3b §4.3."""
    if "referenz" in seite:
        return komp.FeatureByName(ctx.ergebnis(seite["referenz"]).features[0].Name), True
    if "instanz" in seite:
        ergebnis = ctx.ergebnis(seite["feature"])
        [zylinder] = zylinder_zu_punkten(flaechen(ergebnis.features[0]), [ergebnis.punkte[seite["instanz"] - 1]], 0.1)
        return komp.GetCorrespondingEntity(zylinder.objekt), False
    return komp.GetCorrespondingEntity(loese_flaeche(ctx, seite).objekt), False


def _mates(asm):
    f = asm.FirstFeature
    while f is not None and f.GetTypeName2 != "MateGroup":
        f = f.GetNextFeature
    ergebnis, unter = [], (f.GetFirstSubFeature if f is not None else None)
    while unter is not None:
        ergebnis.append(unter)
        unter = unter.GetNextSubFeature
    return ergebnis


def _mate(asm, name, typ, ausrichtung, a, b, sperren=False, wert=0.0):
    asm.ClearSelection2(True)
    auswahl = []
    for (objekt, ist_feature), anhaengen in ((a, False), (b, True)):
        if objekt is None:
            auswahl.append(None)
        elif ist_feature:
            auswahl.append(bool(objekt.Select2(anhaengen, 1)))
        else:
            daten = asm.SelectionManager.CreateSelectData
            daten.Mark = 1
            auswahl.append(bool(objekt.Select4(anhaengen, daten)))
    status = byref_long()
    abstand = mm(wert) if typ == "abstand" else 0.0
    winkel = grad(wert) if typ == "winkel" else 0.0
    mate = asm.AddMate5(MATE[typ], ausrichtung, False, abstand, abstand, abstand, 1, 1, winkel, winkel, winkel, False,
                        sperren, 0, status)
    asm.ClearSelection2(True)
    ergebnis = {"auswahl": auswahl, "mate_none": mate is None, "status": status.value}
    if mate is not None:
        feature = _mates(asm)[-1]
        feature.Name = name
        ergebnis["name_gesetzt"] = feature.Name
        ergebnis["rebuild"] = bool(asm.EditRebuild3)
        ergebnis["fehlercode"] = int(feature.GetErrorCode2(byref_bool()))
        try:
            ergebnis["imate2_typ"] = feature.GetSpecificFeature2.Type
        except Exception as e:  # Spike: Fehler festhalten
            ergebnis["imate2_typ"] = repr(e)
        if typ in ("abstand", "winkel"):
            try:
                mass = feature.Parameter("D1")
                ergebnis["d1_systemwert"] = None if mass is None else mass.SystemValue
            except Exception as e:
                ergebnis["d1_systemwert"] = repr(e)
    return ergebnis


def _lage(komp):
    t = list(komp.Transform2.ArrayData)
    return {"translation_mm": [round(in_mm(x), 6) for x in t[9:12]], "rotation": [round(x, 9) for x in t[:9]],
            "skalierung": t[12], "status": komp.GetConstrainedStatus, "fixiert": bool(komp.IsFixed)}


def _interferenzen(asm):
    idm = asm.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    try:
        return [{"komponenten": [k.Name2 for k in (i.Components or ())], "volumen_mm3": in_mm3(i.Volume)}
                for i in (idm.GetInterferences or ())]
    finally:
        idm._FlagAsMethod("Done")
        idm.Done()


def _sha(pfad):
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


def _soll_gewinde(d, p, kernloch, laenge):
    """Ring Nenn-Ø/Kernloch-Ø über die Einschraublänge, abzüglich der 45°-Endfase p (wie Task 9)."""
    rn, rk = d / 2, kernloch / 2
    a = rn - p
    s_von, s_bis = max(rk - a, 0.0), min(p, laenge)
    v = math.pi * (((a + s_bis) ** 3 - (a + s_von) ** 3) / 3 - rk ** 2 * (s_bis - s_von)) if s_bis > s_von else 0.0
    return v + (math.pi * (rn ** 2 - rk ** 2) * (laenge - p) if laenge > p else 0.0)


def _baugruppe_1(app, r, ordner, sockel, lasche, schraube, stift):
    asm = _neue_baugruppe(app, r)
    try:
        e = {}
        k_so, e["einfuegen_sockel"] = _einfuegen(app, asm, sockel[0])
        e["sockel_fixiert"] = _fixiere(asm, k_so)
        k_la, e["einfuegen_lasche"] = _einfuegen(app, asm, lasche[0])
        k_sc, e["einfuegen_schraube_mit_bezugsgeometrie"] = _einfuegen(app, asm, schraube[0])
        k_st, e["einfuegen_stift_identitaet"] = _einfuegen(app, asm, stift[0], identitaet_setzen=True)
        so, la, sc, st = sockel[1], lasche[1], schraube[1], stift[1]
        e["mates"] = {
            "v1.1": _mate(asm, "v1.1", "deckungsgleich", ENTGEGEN, _entitaet(k_la, la, {"feature": "f1", "flaeche": "-y"}),
                          _entitaet(k_so, so, {"referenz": "OBEN"})),
            "v2": _mate(asm, "v2", "konzentrisch", GLEICH, _entitaet(k_la, la, {"feature": "f2", "instanz": 1}),
                        _entitaet(k_so, so, {"feature": "f2", "instanz": 1})),
            "v3": _mate(asm, "v3", "parallel", GLEICH, _entitaet(k_la, la, {"feature": "f1", "flaeche": "+x"}),
                        _entitaet(k_so, so, {"feature": "f1", "flaeche": "+x"})),
            "v4": _mate(asm, "v4", "deckungsgleich", GLEICH, _entitaet(k_sc, sc, {"referenz": "EINBAU_EBENE"}),
                        _entitaet(k_la, la, {"feature": "f1", "flaeche": "+y"})),
            "v5": _mate(asm, "v5", "konzentrisch", GLEICH, _entitaet(k_sc, sc, {"referenz": "EINBAU_ACHSE"}),
                        _entitaet(k_la, la, {"feature": "f2", "instanz": 1}), sperren=True),
            "v6": _mate(asm, "v6", "deckungsgleich", ENTGEGEN, _entitaet(k_st, st, {"referenz": "EINBAU_EBENE_1"}),
                        _entitaet(k_so, so, {"feature": "f1", "flaeche": "-y"})),
            "v7": _mate(asm, "v7", "konzentrisch", GLEICH, _entitaet(k_st, st, {"referenz": "EINBAU_ACHSE"}),
                        _entitaet(k_so, so, {"feature": "f3", "instanz": 1}), sperren=False),
        }
        e["lage"] = {n: _lage(k) for n, k in (("sockel", k_so), ("lasche", k_la), ("schraube", k_sc), ("stift", k_st))}
        e["erwartet"] = {"lasche_y_mm": 20, "schraube_y_mm": 30, "stift_y_mm": 0, "schraube_status": 3, "stift_status": 2}
        e["mate_namen"] = [f.Name for f in _mates(asm)]
        e["interferenzen"] = _interferenzen(asm)
        e["soll_gewinde_mm3"] = round(_soll_gewinde(8, 1.25, 6.8, 10.0), 4)  # Kopf auf y = 30, l = 20, Eintritt y = 20
        e["getbox_mm"] = [round(in_mm(x), 4) for x in asm.GetBox(0)]
        e["soll_box_mm"] = [-50, 0, -30, 50, 38, 30]  # Sockel 100 × 60, Schraubenkopf bis 30 + k 8
        sw.speichere(asm, ordner / "S12_B1.sldasm")
        return e
    finally:
        sw.schliesse(app, asm)


def _baugruppe_2(app, r, sockel, lasche):
    """Abstand 15 und Winkel 30°; Transform-Konvention; Gleichung bindet das Abstandsmaß."""
    asm = _neue_baugruppe(app, r)
    try:
        k_so, _ = _einfuegen(app, asm, sockel[0])
        _fixiere(asm, k_so)
        k_la, _ = _einfuegen(app, asm, lasche[0])
        la, so = lasche[1], sockel[1]
        e = {"w1": _mate(asm, "w1", "abstand", ENTGEGEN, _entitaet(k_la, la, {"feature": "f1", "flaeche": "-y"}),
                         _entitaet(k_so, so, {"feature": "f1", "flaeche": "+y"}), wert=15),
             "w2": _mate(asm, "w2", "winkel", GLEICH, _entitaet(k_la, la, {"feature": "f1", "flaeche": "+x"}),
                         _entitaet(k_so, so, {"feature": "f1", "flaeche": "+x"}), wert=30)}
        e["lage"] = _lage(k_la)
        e["erwartet_y_mm"] = 35
        t = list(k_la.Transform2.ArrayData)
        flaeche, _ = _entitaet(k_la, la, {"feature": "f1", "flaeche": "+x"})
        e["normale_plus_x_im_baugruppenkontext"] = [round(c, 9) for c in flaeche.Normal]
        e["bild_x_zeilenvektor"] = [round(c, 9) for c in t[0:3]]
        e["bild_x_spaltenvektor"] = [round(t[0], 9), round(t[3], 9), round(t[6], 9)]
        gleichungen = asm.GetEquationMgr
        e["add_S"] = gleichungen.Add2(-1, '"S" = 15', True)
        e["add_D1"] = gleichungen.Add2(-1, '"D1@w1" = "S"', True)
        index = next(i for i in range(gleichungen.GetCount) if gleichungen.Equation(i).startswith('"S"'))
        dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
        gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, '"S" = 25')
        gleichungen.EvaluateAll
        e["rebuild_nach_S_25"] = bool(asm.EditRebuild3)
        e["lage_nach_S_25"] = _lage(k_la)
        e["erwartet_y_nach_S_25_mm"] = 45
        return e
    finally:
        sw.schliesse(app, asm)


def _baugruppe_3(app, r, sockel, lasche):
    """Senkrecht allein: Status der Verknüpfung, Lasche bleibt unterbestimmt."""
    asm = _neue_baugruppe(app, r)
    try:
        k_so, _ = _einfuegen(app, asm, sockel[0])
        _fixiere(asm, k_so)
        k_la, _ = _einfuegen(app, asm, lasche[0])
        e = {"s1": _mate(asm, "s1", "senkrecht", GLEICH, _entitaet(k_la, lasche[1], {"feature": "f1", "flaeche": "+x"}),
                         _entitaet(k_so, sockel[1], {"feature": "f1", "flaeche": "+y"}))}
        e["lage"] = _lage(k_la)
        return e
    finally:
        sw.schliesse(app, asm)


def _baugruppe_4(app, r, sockel, lasche):
    """Ebene + zwei konzentrische Bohrungen: überbestimmt gemeldet?"""
    asm = _neue_baugruppe(app, r)
    try:
        k_so, _ = _einfuegen(app, asm, sockel[0])
        _fixiere(asm, k_so)
        k_la, _ = _einfuegen(app, asm, lasche[0])
        la, so = lasche[1], sockel[1]
        e = {"k1": _mate(asm, "k1", "deckungsgleich", ENTGEGEN, _entitaet(k_la, la, {"feature": "f1", "flaeche": "-y"}),
                         _entitaet(k_so, so, {"referenz": "OBEN"})),
             "k2": _mate(asm, "k2", "konzentrisch", GLEICH, _entitaet(k_la, la, {"feature": "f2", "instanz": 1}),
                         _entitaet(k_so, so, {"feature": "f2", "instanz": 1})),
             "k3": _mate(asm, "k3", "konzentrisch", GLEICH, _entitaet(k_la, la, {"feature": "f3", "instanz": 1}),
                         _entitaet(k_so, so, {"feature": "f3", "instanz": 1}))}
        e["lage"] = _lage(k_la)
        return e
    finally:
        sw.schliesse(app, asm)


def _wieder_oeffnen(app, pfad):
    vorher = _sha(pfad)
    fehler, warnungen = byref_long(), byref_long()
    asm = app.OpenDoc6(str(pfad), 2, 1, "", fehler, warnungen)  # swDocASSEMBLY, swOpenDocOptions_Silent
    try:
        asm.ResolveAllLightWeightComponents(False)
        e = {"fehler": fehler.value, "warnungen": warnungen.value, "interferenzen": _interferenzen(asm),
             "komponenten": [{"name": k.Name2, "datei": Path(k.GetPathName).name, **_lage(k)}
                             for k in (asm.GetComponents(True) or ())],
             "mates": [[f.Name, int(f.GetErrorCode2(byref_bool()))] for f in _mates(asm)]}
    finally:
        sw.schliesse(app, asm)
    e["sha_unveraendert"] = vorher == _sha(pfad)
    return e


def _ruecklesen(app, pfad):
    vorher = _sha(pfad)
    model = oeffne(app, pfad)
    try:
        gleichungen = model.GetEquationMgr
        werte = [{"text": gleichungen.Equation(i), "wert": gleichungen.Value(i), "global": bool(gleichungen.GlobalVariable(i))}
                 for i in range(gleichungen.GetCount)]
    finally:
        sw.schliesse(app, model)
    return {"gleichungen": werte, "sha_unveraendert": vorher == _sha(pfad)}


def pruefen() -> dict:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    ordner = r.arbeitsordner / "stufe3b" / "s12"
    ordner.mkdir(parents=True, exist_ok=True)
    ergebnis, offen = {}, []
    try:
        sockel = _teil(app, r, SOCKEL, ordner)
        offen.append(sockel[0])
        lasche = _teil(app, r, LASCHE, ordner)
        offen.append(lasche[0])
        schraube = _normteil(app, "ISO 4762", "M8x20", ordner)
        offen.append(schraube[0])
        stift = _normteil(app, "ISO 8734", "8x16", ordner)
        offen.append(stift[0])
        ergebnis["baugruppe_1"] = _baugruppe_1(app, r, ordner, sockel, lasche, schraube, stift)
        ergebnis["baugruppe_2_werte"] = _baugruppe_2(app, r, sockel, lasche)
        ergebnis["baugruppe_3_senkrecht"] = _baugruppe_3(app, r, sockel, lasche)
        ergebnis["baugruppe_4_zwei_konzentrische"] = _baugruppe_4(app, r, sockel, lasche)
    finally:
        for model in reversed(offen):
            sw.schliesse(app, model)
    ergebnis["wieder_geoeffnet"] = _wieder_oeffnen(app, ordner / "S12_B1.sldasm")
    ergebnis["ruecklesen_sockel"] = _ruecklesen(app, ordner / "S12_Sockel.sldprt")
    return ergebnis


if __name__ == "__main__":
    lauf("s12_baugruppe", pruefen)
```

- [ ] **Step 3: Spike ausführen**

```powershell
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe -m spikes.s12_baugruppe
```

Expected: `docs/stufe0/ergebnisse/s12_baugruppe.json` mit `"ok": true`. Bricht der Spike ab (`"ok": false`): Ursache im `trace` lesen, den Spike so weit anpassen, dass er alle Fragen beantwortet (z. B. eine Auswahl über `SelectByID2` statt `FeatureByName`), und die Anpassung im Bericht nennen.

- [ ] **Step 4: Auswerten und im Bericht beantworten**

Je Zeile der Tabelle „Abhängigkeiten vom Spike S12“ eine Zeile mit Beleg aus dem JSON:
1. `einfuegen_*.transform_nach_einfuegen[9:12]` ≈ 0 (Sockel, Lasche, Schraube mit Bezugsgeometrie)? `einfuegen_stift_identitaet.transform` = Identität?
2. `sockel_fixiert` true?
3. `mates.*.auswahl` alle true (Bezugsebene über `FeatureByName`, Flächen und Zylinder über `GetCorrespondingEntity`)?
4. Je Mate `status` = 1, `mate_none` false, `name_gesetzt` = Name, `fehlercode` 0, `imate2_typ` = Typnummer; `mate_namen` in Reihenfolge.
5. `lage.lasche.translation_mm[1]` = 20 (Lasche auf der Bezugsebene, also `entgegengesetzt` für Fläche −y ↔ Ebene +y); `lage.schraube.translation_mm[1]` = 30 (`gleich` für Kopfauflage ↔ Fläche +y); `lage.stift.translation_mm[1]` = 0. Weicht eine Lage ab: Bedeutung der Ausrichtung ist umgekehrt → Zeile 5 „sonst“.
6. `lage.schraube.status` = 3, `lage.stift.status` = 2.
7. `lage.sockel.status` notieren.
8. `baugruppe_2_werte.w1.d1_systemwert` = 0,015; `add_D1` ≥ 0; `lage_nach_S_25.translation_mm[1]` = 45.
9. `baugruppe_1.interferenzen`: genau ein Eintrag (Schraube + Sockel); `volumen_mm3` gegen `soll_gewinde_mm3` (Abweichung in %); kein Eintrag für Stift oder Kopf/Lasche.
10. `wieder_geoeffnet`: gleiche Interferenz, gleiche Mate-Namen mit Fehlercode 0, gleiche Status; `sha_unveraendert` true.
11. `ruecklesen_sockel.gleichungen`: globale Variablen `L`, `B`, `H` mit `wert` 100, 60, 20; `sha_unveraendert` true.
12. `normale_plus_x_im_baugruppenkontext` gleich `bild_x_zeilenvektor` (Zeilenkonvention) oder `bild_x_spaltenvektor`?
13. `baugruppe_4_zwei_konzentrische`: Status der Mates und `lage.status` (3 oder 4).
14. `getbox_mm` gegen `soll_box_mm` (Abweichung je Wert).

Dazu `baugruppe_3_senkrecht.s1.status` und `lage.status` (erwartet 1 und 2). Weicht eine Annahme ab: Status DONE_WITH_CONCERNS mit der Zeilennummer; der Controller entscheidet nach Spalte „sonst“ (Ledger) vor Task 7.

- [ ] **Step 5: Einstellungen nach dem Lauf lesen** (`False 1`), Private Bytes vorher/nachher in den Bericht (Zeile g).

- [ ] **Step 6: Commit**

```powershell
git add spikes/s12_baugruppe.py docs/stufe0/ergebnisse/s12_baugruppe.json
git commit -m "spike S12: Baugruppen – Einfügen, Auswahl, Verknüpfungen, Kollision, Rücklesen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Schema, Datenmodell, Laden und Auflösen von `je_position` (ohne SolidWorks)

**Files:**
- Create: `schema/baugruppe.schema.json`
- Modify: `swki/spec/laden.py` (`schema_befunde(spec, erwartet)`, `art_der_datei`)
- Create: `swki/baugruppe/__init__.py`, `swki/baugruppe/fehler.py`, `swki/baugruppe/modell.py`, `swki/baugruppe/aufloesen.py`, `swki/baugruppe/laden.py`
- Create: `tests/baugruppe/__init__.py`, `tests/baugruppe/beispiel.py`, `tests/baugruppe/test_schema_baugruppe.py`, `tests/baugruppe/test_aufloesen.py`, `tests/baugruppe/test_laden_baugruppe.py`

**Interfaces:**
- Consumes: `swki.spec.laden.lade_yaml`, `lade_spec`, `SpecFehler`; `swki.normteile.schluessel.loese_auf`; `swki.normteile.tabelle.lade_normtabelle`, `pruefe_tabelle`; `swki.normteile.erzeugen.erzeuge_spec`, `vorlage_text`; `swki.auftrag.dateiname`.
- Produces:
  - `schema_befunde(spec: dict, erwartet: str = "teil") -> list[dict]`, `art_der_datei(pfad: Path) -> str | None`
  - `Quelle(art, spec, datei=None, norm=None, groesse=None, laenge=None, variante=None, schluessel=None, masse={})` mit `.referenzen: set[str]`, `.schluessel_dokument: str`, `.hole_groesse: str`
  - `Baugruppe(pfad, spec, quellen: dict[str, Quelle], teile: dict[str, dict])` mit `.komponente_von(datei) -> str`
  - `dokument_name(q: Quelle, auftrag: str, standard: dict) -> str`
  - `Instanz(id, komponente, position)`, `Verknuepfung(id, vorlage, typ, a, b, ausrichtung, wert, drehung_sperren)`
  - `basis(instanz_id) -> str`, `je_position(spec, kid) -> dict | None`, `anzahl_positionen(spec, quellen, kid) -> int`, `instanzen(spec, quellen) -> list[Instanz]`, `verknuepfungen(spec, quellen) -> list[Verknuepfung]`
  - `teile_normteil(text) -> tuple[str, str]`, `lade_quellen(spec, ordner) -> (quellen, teile, befunde)`, `lade_baugruppe(pfad) -> Baugruppe` (wirft `SpecFehler`)
  - `tests/baugruppe/beispiel.py`: `PLATTE`, `DECKEL`, `BAUGRUPPE`, `schreibe(ordner, baugruppe=None, platte=None, deckel=None) -> Path`

- [ ] **Step 1: Testbeispiel `tests/baugruppe/beispiel.py` (und leeres `tests/baugruppe/__init__.py`)**

```python
"""Kleine gültige Baugruppe für Tests (selbst formuliert): Platte mit Gewinde, Stiftloch und Durchgangsbohrung, Deckel
mit Zylinderschrauben-Senkung, zwei Schrauben ISO 4762 M8 x 16 je Senkung, ein Stift ISO 8734 8 x 16.

Lage: Platte y 0…20 (fixiert), Deckel y 20…35, Senkungsgrund y = 35 − 8,6 = 26,4, Schraubenende y = 10,4,
Einschraublänge im Gewinde 9,6 mm (Gewindetiefe 12)."""

import copy
from pathlib import Path

import yaml


def _block(name: str, hoehe: float, weitere: list) -> dict:
    return {
        "art": "teil", "name": name, "material": "1.0038", "eigenschaften": {"Benennung": name},
        "parameter": {"L": 100, "B": 60, "H": hoehe, "A": 60},
        "features": [
            {"id": "f1", "typ": "extrusion",
             "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
             "ende": {"typ": "blind", "tiefe": "=H"}},
            *weitere,
        ],
        "pruefung": {"huellquader": ["=L", "=H", "=B"]},
    }


PLATTE = _block("Platte", 20, [
    {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [["=-A/2", 0], ["=A/2", 0]], "tiefe": 16, "gewindetiefe": 12},
    {"id": "f3", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[0, 15]], "durch": True},
    {"id": "f4", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, -15]],
     "durchmesser": 11, "durch": True},
    {"id": "OBEN", "typ": "referenz", "ebene": {"basis": "oben", "abstand": "=H"}},
])
DECKEL = _block("Deckel", 15, [
    {"id": "f2", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8",
     "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [["=-A/2", 0], ["=A/2", 0]], "durch": True},
])
BAUGRUPPE = {
    "art": "baugruppe", "name": "Probe", "eigenschaften": {"Benennung": "Probe"}, "parameter": {"ABST": 35},
    "komponenten": [
        {"id": "platte", "quelle": {"teil": "platte.yaml"}, "fixiert": True},
        {"id": "deckel", "quelle": {"teil": "deckel.yaml"}},
        {"id": "schraube", "quelle": {"normteil": "ISO 4762 M8x16"}, "je_position": {"komponente": "deckel", "feature": "f2"}},
        {"id": "stift", "quelle": {"normteil": "ISO 8734 8x16"}},
    ],
    "verknuepfungen": [
        {"id": "v1", "typ": "deckungsgleich", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "-y"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v2", "typ": "konzentrisch", "a": {"komponente": "deckel", "feature": "f2", "instanz": 1, "achse": True},
         "b": {"komponente": "platte", "feature": "f2", "instanz": 1, "achse": True}},
        {"id": "v3", "typ": "parallel", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "+x"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+x"}, "ausrichtung": "gleich"},
        {"id": "v4", "typ": "deckungsgleich", "a": {"komponente": "schraube", "referenz": "EINBAU_EBENE"},
         "b": {"komponente": "deckel", "feature": "f2", "instanz": "je", "flaeche": "+y"}, "ausrichtung": "gleich"},
        {"id": "v5", "typ": "konzentrisch", "a": {"komponente": "schraube", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "deckel", "feature": "f2", "instanz": "je", "achse": True}},
        {"id": "v6", "typ": "deckungsgleich", "a": {"komponente": "stift", "referenz": "EINBAU_EBENE_1"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "-y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v7", "typ": "konzentrisch", "a": {"komponente": "stift", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "platte", "feature": "f3", "instanz": 1, "achse": True}},
    ],
    "pruefung": {"masse_pruefen": [
        {"was": "Gesamthöhe", "von": {"komponente": "platte", "feature": "f1", "flaeche": "-y"},
         "zu": {"komponente": "deckel", "feature": "f1", "flaeche": "+y"}, "soll": "=ABST"},
    ]},
}


def kopie(spec: dict) -> dict:
    return copy.deepcopy(spec)


def schreibe(ordner: Path, baugruppe: dict | None = None, platte: dict | None = None, deckel: dict | None = None) -> Path:
    """Schreibt platte.yaml, deckel.yaml und probe.yaml nach ordner; liefert den Pfad der Baugruppen-Spec."""
    ordner.mkdir(parents=True, exist_ok=True)
    for name, spec in (("platte.yaml", platte or PLATTE), ("deckel.yaml", deckel or DECKEL),
                       ("probe.yaml", baugruppe or BAUGRUPPE)):
        (ordner / name).write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ordner / "probe.yaml"
```

- [ ] **Step 2: Failing tests – `tests/baugruppe/test_schema_baugruppe.py` (neu)**

```python
from swki.spec.laden import schema_befunde
from tests.baugruppe.beispiel import BAUGRUPPE, PLATTE, kopie


def test_beispiel_ist_gueltig():
    assert schema_befunde(BAUGRUPPE, "baugruppe") == []


def test_teil_schema_lehnt_baugruppe_ab():
    assert schema_befunde(BAUGRUPPE)[0]["pfad"] == "art"


def test_baugruppen_schema_lehnt_teil_ab():
    assert schema_befunde(PLATTE, "baugruppe")[0]["pfad"] == "art"


def test_unbekannter_verknuepfungstyp():
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][0]["typ"] = "tangential"
    assert schema_befunde(spec, "baugruppe")


def test_komponenten_id_ohne_punkt():
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][1]["id"] = "deckel.1"
    assert schema_befunde(spec, "baugruppe")


def test_instanz_je_nicht_in_messpunkten():
    spec = kopie(BAUGRUPPE)
    spec["pruefung"]["masse_pruefen"][0]["von"] = {"komponente": "deckel", "feature": "f2", "instanz": "je", "achse": True}
    assert schema_befunde(spec, "baugruppe")


def test_normteil_quelle_braucht_norm_und_groesse():
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][3]["quelle"] = {"normteil": "ISO8734"}
    assert schema_befunde(spec, "baugruppe")
```

- [ ] **Step 3: Failing tests – `tests/baugruppe/test_aufloesen.py` (neu)**

```python
import pytest

from swki.baugruppe.aufloesen import basis, instanzen, verknuepfungen
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.modell import dokument_name
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe

STANDARD = {"namensschema": {"datei": "{auftrag}_{name}"}}


@pytest.fixture
def bg(tmp_path):
    return lade_baugruppe(schreibe(tmp_path / "A"))


def test_instanzen(bg):
    assert [i.id for i in instanzen(bg.spec, bg.quellen)] == ["platte", "deckel", "schraube.1", "schraube.2", "stift"]
    assert basis("schraube.2") == "schraube" and basis("platte") == "platte"


def test_verknuepfungen_vervielfaeltigt(bg):
    vs = verknuepfungen(bg.spec, bg.quellen)
    assert [v.id for v in vs] == ["v1", "v2", "v3", "v4.1", "v4.2", "v5.1", "v5.2", "v6", "v7"]
    v = next(v for v in vs if v.id == "v4.2")
    assert v.vorlage == "v4" and v.a["komponente"] == "schraube.2"
    assert v.b == {"komponente": "deckel", "feature": "f2", "instanz": 2, "flaeche": "+y"}


def test_drehung_sperren_vorgabe(bg):
    sperren = {v.id: v.drehung_sperren for v in verknuepfungen(bg.spec, bg.quellen)}
    assert sperren["v5.1"] and sperren["v7"]          # konzentrisch mit Normteil
    assert not sperren["v2"] and not sperren["v1"]    # zwei Eigenteile bzw. nicht konzentrisch
    spec = kopie(bg.spec)
    spec["verknuepfungen"][6]["drehung_sperren"] = False
    assert not {v.id: v.drehung_sperren for v in verknuepfungen(spec, bg.quellen)}["v7"]


def test_gepaarte_je_komponenten(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"].append({"id": "scheibe", "quelle": {"normteil": "ISO 7089 M8"},
                                "je_position": {"komponente": "deckel", "feature": "f2"}})
    spec["verknuepfungen"].append({"id": "v8", "typ": "deckungsgleich", "a": {"komponente": "schraube", "referenz": "EINBAU_EBENE"},
                                   "b": {"komponente": "scheibe", "referenz": "EINBAU_EBENE"}, "ausrichtung": "gleich"})
    bg = lade_baugruppe(schreibe(tmp_path / "A", baugruppe=spec))
    v8 = [v for v in verknuepfungen(bg.spec, bg.quellen) if v.vorlage == "v8"]
    assert [(v.id, v.a["komponente"], v.b["komponente"]) for v in v8] == [
        ("v8.1", "schraube.1", "scheibe.1"), ("v8.2", "schraube.2", "scheibe.2")]


def test_dokument_name(bg):
    assert dokument_name(bg.quellen["platte"], "A", STANDARD) == "A_Platte.sldprt"
    assert dokument_name(bg.quellen["schraube"], "A", STANDARD) == "ISO4762_M8x16_8_8.sldprt"
```

Hinweis: `test_gepaarte_je_komponenten` braucht vor Task 3 keine Plausibilitätsregel für `scheibe` (in Task 3 bleibt der Fall gültig: gleiches `je_position`, Scheibe kommt in `v8` vor).

- [ ] **Step 4: Failing tests – `tests/baugruppe/test_laden_baugruppe.py` (neu)**

```python
import pytest

from swki.baugruppe.laden import lade_baugruppe
from swki.spec.laden import SpecFehler, art_der_datei
from tests.baugruppe.beispiel import BAUGRUPPE, PLATTE, kopie, schreibe


def _befunde(pfad) -> list[dict]:
    with pytest.raises(SpecFehler) as e:
        lade_baugruppe(pfad)
    return e.value.daten["befunde"]


def test_laedt_quellen(tmp_path):
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    q = bg.quellen["schraube"]
    assert (q.art, q.norm, q.groesse, q.laenge, q.variante) == ("normteil", "ISO 4762", "M8", 16.0, "8.8")
    assert q.schluessel == "ISO4762_M8x16_8_8" and q.hole_groesse == "M8x16" and q.masse["p"] == 1.25
    assert {"EINBAU_ACHSE", "EINBAU_EBENE_1", "EINBAU_EBENE_2"} <= bg.quellen["stift"].referenzen
    assert list(bg.teile) == ["platte.yaml", "deckel.yaml"] and bg.quellen["platte"].datei == "platte.yaml"
    assert bg.komponente_von("deckel.yaml") == "deckel"


def test_normlaenge_ungueltig(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][2]["quelle"] = {"normteil": "ISO 4762 M8x17"}
    [b] = _befunde(schreibe(tmp_path / "A", baugruppe=spec))
    assert b["pfad"] == "komponenten.schraube.quelle" and "NORMLAENGE_UNGUELTIG" in b["meldung"]


def test_teil_datei_fehlt(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][1]["quelle"] = {"teil": "fehlt.yaml"}
    [b] = _befunde(schreibe(tmp_path / "A", baugruppe=spec))
    assert b["pfad"].startswith("deckel: ") and "fehlt" in b["meldung"]


def test_befund_in_teil_spec_mit_komponente(tmp_path):
    platte = kopie(PLATTE)
    platte["features"][1]["groesse"] = "M7"
    befunde = _befunde(schreibe(tmp_path / "A", platte=platte))
    assert any(b["pfad"] == "platte: features[1].groesse" for b in befunde)


def test_art_der_datei(tmp_path):
    pfad = schreibe(tmp_path / "A")
    assert art_der_datei(pfad) == "baugruppe"
    assert art_der_datei(pfad.parent / "platte.yaml") == "teil"
    assert art_der_datei(pfad.parent / "fehlt.yaml") is None
```

- [ ] **Step 5: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe -q`
Expected: FAIL (ImportError `swki.baugruppe`, `art_der_datei`).

- [ ] **Step 6: `schema/baugruppe.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "swki/baugruppe.schema.json",
  "title": "SolidWorks-KI: Spezifikation einer Baugruppe (Längen in mm, Winkel in Grad)",
  "type": "object",
  "required": ["art", "name", "komponenten", "verknuepfungen"],
  "additionalProperties": false,
  "properties": {
    "art": {"const": "baugruppe"},
    "name": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]*$"},
    "eigenschaften": {"type": "object", "additionalProperties": {"type": "string"}},
    "parameter": {"type": "object", "propertyNames": {"pattern": "^[A-Za-z][A-Za-z0-9_]*$"},
                  "additionalProperties": {"type": "number"}},
    "komponenten": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/komponente"}},
    "verknuepfungen": {"type": "array", "items": {"$ref": "#/$defs/verknuepfung"}},
    "freiheitsgrade": {"type": "object", "propertyNames": {"$ref": "#/$defs/instanz_id"},
                       "additionalProperties": {"const": "unterbestimmt"}},
    "pruefung": {"$ref": "#/$defs/pruefung"},
    "max_nachbesserungen": {"type": "integer", "minimum": 1}
  },
  "$defs": {
    "wert": {"oneOf": [{"type": "number"}, {"type": "string", "pattern": "^=.+"}]},
    "punkt3": {"type": "array", "items": {"$ref": "#/$defs/wert"}, "minItems": 3, "maxItems": 3},
    "richtung": {"enum": ["+x", "-x", "+y", "-y", "+z", "-z"]},
    "standardebene": {"enum": ["vorne", "oben", "rechts"]},
    "id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]*$"},
    "instanz_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]*(\\.[1-9][0-9]*)?$"},
    "instanz": {"oneOf": [{"type": "integer", "minimum": 1}, {"const": "je"}]},
    "quelle": {"oneOf": [
      {"type": "object", "required": ["teil"], "additionalProperties": false,
       "properties": {"teil": {"type": "string", "pattern": "^[^/\\\\]+\\.yaml$"}}},
      {"type": "object", "required": ["normteil"], "additionalProperties": false,
       "properties": {"normteil": {"type": "string", "pattern": "^\\S.*\\s\\S+$"},
                      "variante": {"type": "string", "minLength": 1}}}
    ]},
    "komponente": {
      "type": "object", "required": ["id", "quelle"], "additionalProperties": false,
      "properties": {
        "id": {"$ref": "#/$defs/id"},
        "quelle": {"$ref": "#/$defs/quelle"},
        "fixiert": {"type": "boolean"},
        "je_position": {"type": "object", "required": ["komponente", "feature"], "additionalProperties": false,
                        "properties": {"komponente": {"$ref": "#/$defs/id"}, "feature": {"$ref": "#/$defs/id"}}},
        "gruppe": {"$ref": "#/$defs/id"}
      }
    },
    "referenz": {"oneOf": [
      {"type": "object", "required": ["komponente", "referenz"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/id"}, "referenz": {"$ref": "#/$defs/id"}}},
      {"type": "object", "required": ["komponente", "feature", "flaeche"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/id"}, "feature": {"$ref": "#/$defs/id"},
                      "instanz": {"$ref": "#/$defs/instanz"}, "flaeche": {"$ref": "#/$defs/richtung"}}},
      {"type": "object", "required": ["komponente", "feature", "instanz", "achse"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/id"}, "feature": {"$ref": "#/$defs/id"},
                      "instanz": {"$ref": "#/$defs/instanz"}, "achse": {"const": true}}},
      {"type": "object", "required": ["komponente", "ebene"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/id"}, "ebene": {"$ref": "#/$defs/standardebene"}}},
      {"type": "object", "required": ["komponente", "nahe"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/id"}, "nahe": {"$ref": "#/$defs/punkt3"}}}
    ]},
    "verknuepfung": {
      "type": "object", "required": ["id", "typ", "a", "b"], "additionalProperties": false,
      "properties": {
        "id": {"$ref": "#/$defs/id"},
        "typ": {"enum": ["deckungsgleich", "konzentrisch", "parallel", "senkrecht", "abstand", "winkel"]},
        "a": {"$ref": "#/$defs/referenz"},
        "b": {"$ref": "#/$defs/referenz"},
        "ausrichtung": {"enum": ["gleich", "entgegengesetzt"]},
        "wert": {"$ref": "#/$defs/wert"},
        "drehung_sperren": {"type": "boolean"}
      }
    },
    "messpunkt": {"oneOf": [
      {"type": "object", "required": ["punkt"], "additionalProperties": false,
       "properties": {"punkt": {"$ref": "#/$defs/punkt3"}}},
      {"type": "object", "required": ["komponente", "referenz"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/instanz_id"}, "referenz": {"$ref": "#/$defs/id"}}},
      {"type": "object", "required": ["komponente", "feature", "flaeche"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/instanz_id"}, "feature": {"$ref": "#/$defs/id"},
                      "flaeche": {"$ref": "#/$defs/richtung"}}},
      {"type": "object", "required": ["komponente", "feature", "instanz", "achse"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/instanz_id"}, "feature": {"$ref": "#/$defs/id"},
                      "instanz": {"type": "integer", "minimum": 1}, "achse": {"const": true}}}
    ]},
    "massepruefung": {
      "type": "object", "required": ["was", "von", "zu", "soll"], "additionalProperties": false,
      "properties": {"was": {"type": "string", "minLength": 1}, "von": {"$ref": "#/$defs/messpunkt"},
                     "zu": {"$ref": "#/$defs/messpunkt"}, "soll": {"$ref": "#/$defs/wert"},
                     "tol": {"type": "number", "exclusiveMinimum": 0}}
    },
    "pruefung": {
      "type": "object", "additionalProperties": false,
      "properties": {
        "huellquader": {"type": "array", "items": {"$ref": "#/$defs/wert"}, "minItems": 3, "maxItems": 3},
        "huellquader_tol": {"type": "number", "exclusiveMinimum": 0},
        "masse_pruefen": {"type": "array", "items": {"$ref": "#/$defs/massepruefung"}},
        "masse": {"type": "object", "required": ["soll"], "additionalProperties": false,
                  "properties": {"soll": {"$ref": "#/$defs/wert"},
                                 "toleranz_prozent": {"type": "number", "exclusiveMinimum": 0}}}
      }
    }
  }
}
```

- [ ] **Step 7: `swki/spec/laden.py`** – `schema_befunde` mit erwarteter Art, neue Funktion `art_der_datei` (nach `lade_yaml`)

```python
def schema_befunde(spec: dict, erwartet: str = "teil") -> list[dict]:
    """Schemabefunde; die Spezifikation muss die erwartete Art haben (teil bzw. baugruppe)."""
    art = spec.get("art")
    datei = SCHEMA_ORDNER / f"{art}.schema.json"
    if art != erwartet or not datei.exists():
        return [{"pfad": "art", "meldung": f"Art {art!r} wird hier nicht unterstützt (erwartet {erwartet!r})"}]
    validator = Draft202012Validator(json.loads(datei.read_text(encoding="utf-8")))
    befunde = []
    for fehler in validator.iter_errors(spec):
        genau = best_match(fehler.context) if fehler.context else fehler
        befunde.append({"pfad": _pfad(genau.absolute_path), "meldung": genau.message})
    return sorted(befunde, key=lambda b: b["pfad"])


def art_der_datei(pfad: Path) -> str | None:
    """Wert von "art" einer Spezifikationsdatei (Weiche der Befehle); None, wenn die Datei fehlt oder kein Objekt ist."""
    try:
        return lade_yaml(pfad).get("art")
    except SpecFehler:
        return None
```

- [ ] **Step 8: `swki/baugruppe/__init__.py`, `swki/baugruppe/fehler.py`**

```python
"""Baugruppen (Stufe 3b): Spezifikation laden, auflösen, prüfen, freigeben, bauen und prüfen."""
```

```python
"""Fehlercodes der Baugruppen (Spec 3b §11). Geworfen werden sie als swki.compiler.fehler.BauFehler, damit sie wie
Teilfehler ins Protokoll gehen."""

TEIL_BAU = "TEIL_BAU"
KOMPONENTE_FEHLER = "KOMPONENTE_FEHLER"
VERKNUEPFUNG_FEHLER = "VERKNUEPFUNG_FEHLER"
```

- [ ] **Step 9: `swki/baugruppe/modell.py`**

```python
"""Datenmodell einer geladenen Baugruppe (Spec 3b §4): Quellen der Komponenten und Dateinamen im Lauf."""

from dataclasses import dataclass, field
from pathlib import Path

from swki.auftrag import dateiname


@dataclass
class Quelle:
    art: str                       # "teil" | "normteil"
    spec: dict                     # Teil-Spezifikation bzw. aus der Bauvorlage erzeugte Normteil-Spezifikation
    datei: str | None = None       # teil: Dateiname der Teil-Spec im Auftragsordner
    norm: str | None = None        # normteil: Norm wie in der Tabelle, z. B. "ISO 4762"
    groesse: str | None = None     # normteil: Tabellenschlüssel, z. B. "M8" oder "8"
    laenge: float | None = None    # normteil: mm; None bei Teilen ohne Länge
    variante: str | None = None
    schluessel: str | None = None  # normteil: Bibliotheksschlüssel, z. B. "ISO4762_M8x30_8_8"
    masse: dict = field(default_factory=dict)  # normteil: Normmaße der Größe

    @property
    def referenzen(self) -> set[str]:
        """IDs der referenz-Features (bei Normteilen die Einbaureferenzen EINBAU_*)."""
        return {f["id"] for f in self.spec["features"] if f["typ"] == "referenz"}

    @property
    def schluessel_dokument(self) -> str:
        """Schlüssel des Quelldokuments: Dateiname der Teil-Spec bzw. Bibliotheksschlüssel."""
        return self.datei if self.art == "teil" else self.schluessel

    @property
    def hole_groesse(self) -> str:
        """Größe für swki normteil hole: "M8x30", "M8", "8x30"."""
        return self.groesse if self.laenge is None else f"{self.groesse}x{self.laenge:g}"


@dataclass
class Baugruppe:
    pfad: Path                     # Baugruppen-Spezifikation
    spec: dict
    quellen: dict[str, Quelle]     # Komponenten-ID → Quelle
    teile: dict[str, dict]         # Dateiname → Teil-Spezifikation, in Reihenfolge der ersten Verwendung

    def komponente_von(self, datei: str) -> str:
        """Erste Komponente mit der Teil-Spec `datei` (Präfix der Teilprüfung, Knoten bei TEIL_BAU)."""
        return next(k for k, q in self.quellen.items() if q.datei == datei)


def dokument_name(q: Quelle, auftrag: str, standard: dict) -> str:
    """Dateiname im Lauf-Ordner: <auftrag>_<name>.sldprt (Eigenteil) bzw. <schluessel>.sldprt (Normteil-Kopie)."""
    return f"{dateiname(q.spec, auftrag, standard)}.sldprt" if q.art == "teil" else f"{q.schluessel}.sldprt"
```

- [ ] **Step 10: `swki/baugruppe/aufloesen.py`**

```python
"""je_position auflösen (Spec 3b §4.2): Instanzen der Komponenten und vervielfältigte Verknüpfungen.

Setzt eine plausible Spezifikation voraus (swki.baugruppe.plausibel prüft vorher)."""

from dataclasses import dataclass

from swki.baugruppe.modell import Quelle


@dataclass(frozen=True)
class Instanz:
    id: str               # "platte" bzw. "schraube.2"
    komponente: str       # Komponenten-ID der Spezifikation
    position: int | None  # Position im Feature von je_position (1 …), sonst None


@dataclass(frozen=True)
class Verknuepfung:
    id: str                 # "v1" bzw. "v4.2"
    vorlage: str            # ID in der Spezifikation
    typ: str
    a: dict                 # Referenz mit komponente = Instanz-ID und konkreter instanz
    b: dict
    ausrichtung: str | None
    wert: object            # Zahl, "=Ausdruck" oder None
    drehung_sperren: bool


def basis(instanz_id: str) -> str:
    """Komponenten-ID einer Instanz: "schraube.2" → "schraube"."""
    return instanz_id.split(".")[0]


def je_position(spec: dict, kid: str) -> dict | None:
    return next((k.get("je_position") for k in spec["komponenten"] if k["id"] == kid), None)


def anzahl_positionen(spec: dict, quellen: dict[str, Quelle], kid: str) -> int:
    je = je_position(spec, kid)
    feature = next(f for f in quellen[je["komponente"]].spec["features"] if f["id"] == je["feature"])
    return len(feature["positionen"])


def instanzen(spec: dict, quellen: dict[str, Quelle]) -> list[Instanz]:
    ergebnis = []
    for k in spec["komponenten"]:
        if k.get("je_position"):
            n = anzahl_positionen(spec, quellen, k["id"])
            ergebnis += [Instanz(f"{k['id']}.{i}", k["id"], i) for i in range(1, n + 1)]
        else:
            ergebnis.append(Instanz(k["id"], k["id"], None))
    return ergebnis


def _drehung_sperren(v: dict, quellen: dict[str, Quelle]) -> bool:
    """Vorgabe true bei konzentrisch mit einem Normteil (Spec 3b §4.4), sonst false; ausdrücklich angegeben gilt."""
    if "drehung_sperren" in v:
        return v["drehung_sperren"]
    return v["typ"] == "konzentrisch" and any(quellen[v[s]["komponente"]].art == "normteil" for s in ("a", "b"))


def _setze(seite: dict, je: set[str], i: int) -> dict:
    neu = dict(seite)
    if neu["komponente"] in je:
        neu["komponente"] = f"{neu['komponente']}.{i}"
    if neu.get("instanz") == "je":
        neu["instanz"] = i
    return neu


def verknuepfungen(spec: dict, quellen: dict[str, Quelle]) -> list[Verknuepfung]:
    ergebnis = []
    for v in spec.get("verknuepfungen", []):
        je = {v[s]["komponente"] for s in ("a", "b") if je_position(spec, v[s]["komponente"])}
        sperren = _drehung_sperren(v, quellen)
        if not je:
            ergebnis.append(Verknuepfung(v["id"], v["id"], v["typ"], dict(v["a"]), dict(v["b"]), v.get("ausrichtung"),
                                         v.get("wert"), sperren))
            continue
        for i in range(1, anzahl_positionen(spec, quellen, next(iter(je))) + 1):
            ergebnis.append(Verknuepfung(f"{v['id']}.{i}", v["id"], v["typ"], _setze(v["a"], je, i), _setze(v["b"], je, i),
                                         v.get("ausrichtung"), v.get("wert"), sperren))
    return ergebnis
```

- [ ] **Step 11: `swki/baugruppe/laden.py`**

```python
"""Baugruppen-Spezifikation laden (Spec 3b §5): Schema, Teil-Specs, Normteile. Die Plausibilität kommt in Task 3 dazu."""

from pathlib import Path

from swki.baugruppe.modell import Baugruppe, Quelle
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.fehler import NormteilFehler
from swki.normteile.schluessel import loese_auf
from swki.normteile.tabelle import lade_normtabelle, pruefe_tabelle
from swki.spec.laden import SpecFehler, lade_spec, lade_yaml, schema_befunde


def teile_normteil(text: str) -> tuple[str, str]:
    """"ISO 4762 M8x30" → ("ISO 4762", "M8x30"): das letzte Wort ist die Größe."""
    norm, _, groesse = text.strip().rpartition(" ")
    return norm.strip(), groesse


def _normteil(kid: str, quelle: dict) -> tuple[Quelle | None, list[dict]]:
    norm, groesse = teile_normteil(quelle["normteil"])
    try:
        pruefe_tabelle(lade_normtabelle(norm))
        t, a = loese_auf(norm, groesse, quelle.get("variante"))
    except NormteilFehler as e:
        return None, [{"pfad": f"komponenten.{kid}.quelle", "meldung": f"{e.daten['code']}: {e}"}]
    spec = erzeuge_spec(t, a, vorlage_text(t))
    return Quelle("normteil", spec, norm=t["norm"], groesse=a.groesse, laenge=a.laenge, variante=a.variante,
                  schluessel=a.schluessel, masse=dict(t["groessen"][a.groesse]["masse"])), []


def _teil(kid: str, datei: str, ordner: Path, cache: dict) -> tuple[Quelle | None, list[dict]]:
    if datei not in cache:
        try:
            cache[datei] = lade_spec(ordner / datei)
        except SpecFehler as e:
            cache[datei] = None
            return None, [{"pfad": f"{kid}: {b['pfad']}", "meldung": b["meldung"]} for b in e.daten["befunde"]]
    if cache[datei] is None:
        return None, []  # Befunde stehen schon bei der ersten Komponente mit dieser Datei
    return Quelle("teil", cache[datei], datei=datei), []


def lade_quellen(spec: dict, ordner: Path) -> tuple[dict[str, Quelle], dict[str, dict], list[dict]]:
    quellen, cache, befunde = {}, {}, []
    for k in spec["komponenten"]:
        q = k["quelle"]
        quelle, b = _teil(k["id"], q["teil"], ordner, cache) if "teil" in q else _normteil(k["id"], q)
        befunde += b
        if quelle is not None:
            quellen[k["id"]] = quelle
    return quellen, {d: s for d, s in cache.items() if s is not None}, befunde


def lade_baugruppe(pfad: Path) -> Baugruppe:
    """Lädt und prüft eine Baugruppen-Spezifikation; wirft SpecFehler mit allen Befunden."""
    spec = lade_yaml(pfad)
    befunde = schema_befunde(spec, "baugruppe")
    quellen, teile = {}, {}
    if not befunde:
        quellen, teile, befunde = lade_quellen(spec, pfad.parent)
    if befunde:
        raise SpecFehler(befunde)
    return Baugruppe(pfad, spec, quellen, teile)
```

`lade_normtabelle` meldet eine unbekannte Norm als `NormteilFehler` (`NORMTEIL_UNBEKANNT`); falls nicht (Implementer prüft `swki/normteile/tabelle.py`), zusätzlich `FileNotFoundError` fangen und als Befund mit Code `NORMTEIL_UNBEKANNT` melden.

- [ ] **Step 12: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: grün, **473 passed** (456 + 17: Schema 7, Auflösen 5, Laden 5).

- [ ] **Step 13: Commit**

```powershell
git add schema/baugruppe.schema.json swki/spec/laden.py swki/baugruppe tests/baugruppe
git commit -m "baugruppe: Schema, Datenmodell, Laden und Auflösen von je_position" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Plausibilität, Passung, Hinweise, `swki validieren` für Baugruppen

**Files:**
- Create: `swki/baugruppe/plausibel.py`, `swki/baugruppe/passung.py`, `swki/baugruppe/hinweise.py`, `swki/baugruppe/befehle.py`
- Modify: `swki/baugruppe/laden.py` (Plausibilität aufrufen), `swki/spec/befehle.py` (Weiche in `_validieren`)
- Create: `tests/baugruppe/test_plausibel.py`, `tests/baugruppe/test_passung.py`, `tests/baugruppe/test_befehle_baugruppe.py`

**Interfaces:**
- Consumes: Task 2 (`Quelle`, `aufloesen`, `lade_quellen`); `swki.spec.ausdruck.auswerten`; `swki.spec.normen.groesse_text`; `swki.spec.hinweise.hinweise`.
- Produces: `plausibel_befunde(spec, quellen) -> list[dict]`, `referenz_befunde(seite, pfad, quellen, spec, instanz_id_erlaubt=False) -> list[dict]`; `passt(q: Quelle, feature: dict, parameter: dict) -> str | None`, `passung_befunde(spec, quellen) -> list[dict]`; `hinweise_baugruppe(bg) -> list[dict]`; `swki.baugruppe.befehle.validieren(pfad: Path) -> dict`.

- [ ] **Step 1: Failing tests – `tests/baugruppe/test_plausibel.py` (neu)**

```python
import pytest

from swki.baugruppe.laden import lade_quellen
from swki.baugruppe.plausibel import plausibel_befunde
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe


def _befunde(tmp_path, spec) -> list[dict]:
    pfad = schreibe(tmp_path / "A", baugruppe=spec)
    quellen, _, befunde = lade_quellen(spec, pfad.parent)
    assert befunde == []
    return plausibel_befunde(spec, quellen)


def _meldungen(befunde) -> str:
    return " | ".join(f"{b['pfad']}: {b['meldung']}" for b in befunde)


def test_beispiel_ohne_befunde(tmp_path):
    assert _befunde(tmp_path, kopie(BAUGRUPPE)) == []


@pytest.mark.parametrize("fixiert", [[], ["platte", "deckel"]])
def test_genau_eine_fixiert(tmp_path, fixiert):
    spec = kopie(BAUGRUPPE)
    for k in spec["komponenten"]:
        k.pop("fixiert", None)
        if k["id"] in fixiert:
            k["fixiert"] = True
    assert "genau eine Komponente" in _meldungen(_befunde(tmp_path, spec))


def test_je_position_auf_extrusion(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][2]["je_position"] = {"komponente": "deckel", "feature": "f1"}
    assert "keine normbohrung/bohrung" in _meldungen(_befunde(tmp_path, spec))


def test_normteil_nur_einbaureferenzen(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][6]["a"] = {"komponente": "stift", "feature": "f1", "flaeche": "+y"}
    assert "nur über Einbaureferenzen" in _meldungen(_befunde(tmp_path, spec))


def test_unbekannte_einbaureferenz(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][3]["a"]["referenz"] = "EINBAU_EBENE_2"   # ISO 4762 hat nur EINBAU_EBENE
    assert "keine Einbaureferenz 'EINBAU_EBENE_2'" in _meldungen(_befunde(tmp_path, spec))


def test_instanz_zu_gross(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][1]["b"]["instanz"] = 3
    assert "hat nur 2 Positionen" in _meldungen(_befunde(tmp_path, spec))


def test_ausrichtung_pflicht(tmp_path):
    spec = kopie(BAUGRUPPE)
    del spec["verknuepfungen"][0]["ausrichtung"]
    assert "ausrichtung" in _meldungen(_befunde(tmp_path, spec))


def test_wert_pflicht_und_verboten(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][0]["typ"] = "abstand"          # ohne wert
    spec["verknuepfungen"][2]["wert"] = 5                 # parallel mit wert
    text = _meldungen(_befunde(tmp_path, spec))
    assert "wert ist bei abstand Pflicht" in text and "wert gilt nur bei abstand/winkel" in text


def test_instanz_je_ohne_je_komponente(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][1]["b"]["instanz"] = "je"
    assert "instanz: je nur zusammen mit" in _meldungen(_befunde(tmp_path, spec))


def test_verschiedene_je_positionen(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"].append({"id": "mutter", "quelle": {"normteil": "ISO 4032 M8"},
                                "je_position": {"komponente": "platte", "feature": "f2"}})
    spec["verknuepfungen"].append({"id": "v8", "typ": "deckungsgleich", "a": {"komponente": "mutter", "referenz": "EINBAU_EBENE"},
                                   "b": {"komponente": "schraube", "referenz": "EINBAU_EBENE"}, "ausrichtung": "gleich"})
    assert "verschiedenem je_position" in _meldungen(_befunde(tmp_path, spec))


def test_komponente_ohne_verknuepfung(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"] = spec["verknuepfungen"][:5]   # Stift ohne Verknüpfung
    assert "stift kommt in keiner Verknüpfung vor" in _meldungen(_befunde(tmp_path, spec))


@pytest.mark.parametrize(("komponente", "gueltig"), [("schraube", False), ("schraube.3", False), ("schraube.1", True)])
def test_messpunkt_instanzen(tmp_path, komponente, gueltig):
    spec = kopie(BAUGRUPPE)
    spec["pruefung"]["masse_pruefen"][0]["zu"] = {"komponente": komponente, "referenz": "EINBAU_EBENE"}
    assert (_befunde(tmp_path, spec) == []) is gueltig


def test_freiheitsgrade_unbekannt(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["freiheitsgrade"] = {"rad": "unterbestimmt"}
    assert "freiheitsgrade" in _meldungen(_befunde(tmp_path, spec))
```

- [ ] **Step 2: Failing tests – `tests/baugruppe/test_passung.py` (neu)**

```python
import pytest

from swki.baugruppe.laden import _normteil, lade_quellen
from swki.baugruppe.passung import passt, passung_befunde
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe

FAELLE = [
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "zylinderschraube", "groesse": "M8"}, True),
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "gewinde", "groesse": "M8"}, True),
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "gewinde", "groesse": "M10"}, False),
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "gewinde", "groesse": "M8x1"}, False),
    ("ISO 4762 M8x16", {"typ": "normbohrung", "art": "stift", "groesse": 8}, False),
    ("ISO 4762 M10x50", {"typ": "bohrung", "durchmesser": 11}, True),
    ("ISO 4762 M10x50", {"typ": "bohrung", "durchmesser": 10}, False),
    ("ISO 8734 8x16", {"typ": "normbohrung", "art": "stift", "groesse": 8}, True),
    ("ISO 8734 8x16", {"typ": "normbohrung", "art": "stift", "groesse": 10}, False),
    ("ISO 8734 8x16", {"typ": "bohrung", "durchmesser": 8}, False),
    ("ISO 7089 M10", {"typ": "bohrung", "durchmesser": 10.5}, True),
    ("ISO 7089 M10", {"typ": "bohrung", "durchmesser": 10}, False),
    ("ISO 4032 M10", {"typ": "normbohrung", "art": "zylinderschraube", "groesse": "M10"}, True),
]


@pytest.mark.parametrize(("normteil", "bohrung", "erwartet"), FAELLE)
def test_passt(normteil, bohrung, erwartet):
    quelle, befunde = _normteil("x", {"normteil": normteil})
    assert befunde == []
    assert (passt(quelle, bohrung, {}) is None) is erwartet


def test_passung_befund_im_beispiel(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][2]["quelle"] = {"normteil": "ISO 4762 M10x16"}
    quellen, _, befunde = lade_quellen(spec, schreibe(tmp_path / "A", baugruppe=spec).parent)
    assert befunde == []
    [b] = passung_befunde(spec, quellen)
    assert b["pfad"] == "verknuepfungen[4]" and "M10" in b["meldung"] and "zylinderschraube M8" in b["meldung"]
```

- [ ] **Step 3: Failing tests – `tests/baugruppe/test_befehle_baugruppe.py` (neu)**

```python
import json

import yaml

from swki.cli import main
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe
from tests.spec.beispiel import GUELTIG


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_validieren_baugruppe(capsys, tmp_path):
    code, daten = _lauf(capsys, "validieren", str(schreibe(tmp_path / "A")))
    assert code == 0, daten
    assert (daten["gueltig"], daten["art"], daten["komponenten"], daten["verknuepfungen"]) == (True, "baugruppe", 5, 9)


def test_validieren_hinweise(capsys, tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][2]["b"] = {"komponente": "platte", "nahe": [50, 10, 0]}
    code, daten = _lauf(capsys, "validieren", str(schreibe(tmp_path / "A", baugruppe=spec)))
    assert code == 0, daten
    arten = {(h["art"], h["pfad"].split(":")[0]) for h in daten["hinweise"]}
    assert ("feste_zahl", "platte") in arten               # tiefe 16 in der Platte
    assert ("nahe", "verknuepfungen[2].b") in arten


def test_validieren_teil_unveraendert(capsys, tmp_path):
    pfad = tmp_path / "platte.yaml"
    pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    code, daten = _lauf(capsys, "validieren", str(pfad))
    assert code == 0 and daten["features"] == len(GUELTIG["features"]) and "art" not in daten
```

- [ ] **Step 4: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe -q`
Expected: FAIL (ImportError `plausibel`, `passung`; `validieren` meldet für die Baugruppe einen Schema-Befund `art`).

- [ ] **Step 5: `swki/baugruppe/passung.py`**

```python
"""Passung Normteil ↔ Bohrung bei konzentrischen Verknüpfungen (Spec 3b §5.7), ohne SolidWorks."""

from swki.baugruppe.modell import Quelle
from swki.spec.ausdruck import AusdruckFehler, auswerten
from swki.spec.normen import groesse_text

INNEN = {"ISO 4762": "d", "ISO 4032": "d", "ISO 7089": "d1"}  # Schaft- bzw. Innen-Ø je Norm (Tabellenmaß)


def passt(q: Quelle, f: dict, parameter: dict) -> str | None:
    """None, wenn Normteil q auf die Bohrung f passt; sonst eine Meldung."""
    norm, groesse = q.norm, q.groesse
    if f["typ"] == "normbohrung":
        art, g = f["art"], groesse_text(f["groesse"])
        if norm == "ISO 4762":
            ok = art in ("zylinderschraube", "gewinde") and g == groesse
        elif norm == "ISO 8734":
            ok = art == "stift" and g == groesse
        elif norm in ("ISO 7089", "ISO 4032"):
            ok = art != "stift" and g == groesse
        else:
            ok = False
        return None if ok else f"{norm} {groesse} passt nicht auf normbohrung {art} {g}"
    if norm not in INNEN:
        return f"{norm} {groesse} gehört nicht in eine freie Bohrung (nur normbohrung stift)"
    try:
        d = auswerten(f["durchmesser"], parameter)
    except AusdruckFehler:
        return None  # meldet die Prüfung der Teil-Spec
    innen = q.masse[INNEN[norm]]
    ok = d > innen if norm == "ISO 4762" else d >= innen
    return None if ok else f"{norm} {groesse}: Bohrung Ø {d:g} zu klein (Schaft-/Innen-Ø {innen:g})"


def _paar(v: dict, quellen: dict[str, Quelle]):
    """(Normteil, Eigenteil, Seite des Eigenteils), wenn v die EINBAU_ACHSE eines Normteils mit einer Bohrungsachse
    verbindet; sonst None."""
    for n, t in (("a", "b"), ("b", "a")):
        qn, qt = quellen.get(v[n]["komponente"]), quellen.get(v[t]["komponente"])
        if (qn is not None and qt is not None and qn.art == "normteil" and v[n].get("referenz") == "EINBAU_ACHSE"
                and qt.art == "teil" and v[t].get("achse")):
            return qn, qt, v[t]
    return None


def passung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    for i, v in enumerate(spec.get("verknuepfungen", [])):
        if v["typ"] != "konzentrisch" or (paar := _paar(v, quellen)) is None:
            continue
        qn, qt, seite = paar
        f = next((x for x in qt.spec["features"] if x["id"] == seite["feature"]), None)
        if f is None or f["typ"] not in ("normbohrung", "bohrung"):
            continue
        if meldung := passt(qn, f, qt.spec.get("parameter", {})):
            befunde.append({"pfad": f"verknuepfungen[{i}]", "meldung": f"Passung: {meldung}"})
    return befunde
```

- [ ] **Step 6: `swki/baugruppe/plausibel.py`**

```python
"""Plausibilität einer Baugruppen-Spezifikation (Spec 3b §5), ohne SolidWorks."""

from swki.baugruppe.aufloesen import anzahl_positionen, basis, je_position
from swki.baugruppe.modell import Quelle
from swki.baugruppe.passung import passung_befunde
from swki.spec.ausdruck import AusdruckFehler, auswerten

MIT_AUSRICHTUNG = ("deckungsgleich", "parallel", "abstand", "winkel")
MIT_WERT = ("abstand", "winkel")
BOHRUNGEN = ("normbohrung", "bohrung")


def _b(pfad: str, meldung: str) -> dict:
    return {"pfad": pfad, "meldung": meldung}


def _features(q: Quelle) -> dict:
    return {f["id"]: f for f in q.spec["features"]}


def _instanz_befunde(kid: str, k: str, pfad: str, spec: dict, quellen: dict) -> list[dict]:
    je = je_position(spec, k)
    if je and kid == k:
        return [_b(f"{pfad}.komponente", f"{k} hat je_position: Instanz angeben ({k}.1 …)")]
    if not je and kid != k:
        return [_b(f"{pfad}.komponente", f"{k} hat keine Instanzen (ohne .<n> angeben)")]
    if je and int(kid.split(".")[1]) > anzahl_positionen(spec, quellen, k):
        return [_b(f"{pfad}.komponente", f"{kid}: {je['komponente']}.{je['feature']} hat nicht so viele Positionen")]
    return []


def referenz_befunde(seite: dict, pfad: str, quellen: dict[str, Quelle], spec: dict,
                     instanz_id_erlaubt: bool = False) -> list[dict]:
    """Befunde einer Referenz (Verknüpfung) bzw. eines Messpunkts (instanz_id_erlaubt: komponente = Instanz-ID)."""
    kid = seite["komponente"]
    k = basis(kid) if instanz_id_erlaubt else kid
    if k not in quellen:
        return [_b(f"{pfad}.komponente", f"Komponente {kid!r} unbekannt")]
    befunde = _instanz_befunde(kid, k, pfad, spec, quellen) if instanz_id_erlaubt else []
    q = quellen[k]
    if q.art == "normteil":
        vorhanden = ", ".join(sorted(q.referenzen))
        if "referenz" not in seite:
            return befunde + [_b(pfad, f"{k} ist ein Normteil: nur über Einbaureferenzen ({vorhanden})")]
        if seite["referenz"] not in q.referenzen:
            return befunde + [_b(f"{pfad}.referenz",
                                 f"{q.norm} hat keine Einbaureferenz {seite['referenz']!r} (vorhanden: {vorhanden})")]
        return befunde
    features = _features(q)
    if "referenz" in seite:
        f = features.get(seite["referenz"])
        if f is None or f["typ"] != "referenz":
            befunde.append(_b(f"{pfad}.referenz", f"{q.datei} hat kein referenz-Feature {seite['referenz']!r}"))
    elif "feature" in seite:
        f = features.get(seite["feature"])
        if f is None:
            befunde.append(_b(f"{pfad}.feature", f"{q.datei} hat kein Feature {seite['feature']!r}"))
        elif "instanz" in seite:
            if f["typ"] not in BOHRUNGEN:
                befunde.append(_b(f"{pfad}.instanz", f"instanz nur bei normbohrung/bohrung ({seite['feature']} ist {f['typ']})"))
            elif isinstance(seite["instanz"], int) and seite["instanz"] > len(f["positionen"]):
                befunde.append(_b(f"{pfad}.instanz", f"{seite['feature']} hat nur {len(f['positionen'])} Positionen"))
    return befunde


def _komponenten_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    ids = [k["id"] for k in spec["komponenten"]]
    for i, kid in enumerate(ids):
        if kid in ids[:i]:
            befunde.append(_b(f"komponenten[{i}].id", f"ID {kid!r} ist doppelt"))
    fix = [k["id"] for k in spec["komponenten"] if k.get("fixiert")]
    if len(fix) != 1:
        befunde.append(_b("komponenten", f"genau eine Komponente muss fixiert sein (sind {len(fix)}: {', '.join(fix) or 'keine'})"))
    for i, k in enumerate(spec["komponenten"]):
        je = k.get("je_position")
        if not je:
            continue
        pfad = f"komponenten[{i}].je_position"
        if k.get("fixiert"):
            befunde.append(_b(pfad, "eine Komponente mit je_position kann nicht fixiert sein"))
        q = quellen.get(je["komponente"])
        if q is None or q.art != "teil" or je_position(spec, je["komponente"]):
            befunde.append(_b(f"{pfad}.komponente", f"{je['komponente']!r} ist kein Eigenteil ohne je_position"))
            continue
        f = _features(q).get(je["feature"])
        if f is None or f["typ"] not in BOHRUNGEN:
            befunde.append(_b(f"{pfad}.feature", f"{q.datei}: {je['feature']!r} ist keine normbohrung/bohrung"))
    return befunde


def _je_befunde(v: dict, pfad: str, spec: dict) -> list[dict]:
    je = {s: je_position(spec, v[s]["komponente"]) for s in ("a", "b") if je_position(spec, v[s]["komponente"])}
    befunde = []
    if len(je) == 2 and je["a"] != je["b"]:
        befunde.append(_b(pfad, "zwei Komponenten mit verschiedenem je_position: Instanzen lassen sich nicht paaren"))
    for s in ("a", "b"):
        if v[s].get("instanz") != "je":
            continue
        ziel = {"komponente": v[s]["komponente"], "feature": v[s].get("feature")}
        if not je:
            befunde.append(_b(f"{pfad}.{s}.instanz", "instanz: je nur zusammen mit einer Komponente mit je_position"))
        elif ziel not in je.values():
            befunde.append(_b(f"{pfad}.{s}.instanz", "instanz: je nur auf das Feature des je_position "
                                                     f"({', '.join(f'{x['komponente']}.{x['feature']}' for x in je.values())})"))
    return befunde


def _verknuepfung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    vs = spec.get("verknuepfungen", [])
    ids = [v["id"] for v in vs]
    p = spec.get("parameter", {})
    for i, v in enumerate(vs):
        pfad = f"verknuepfungen[{i}]"
        if v["id"] in ids[:i]:
            befunde.append(_b(f"{pfad}.id", f"ID {v['id']!r} ist doppelt"))
        for s in ("a", "b"):
            befunde += referenz_befunde(v[s], f"{pfad}.{s}", quellen, spec)
        if v["a"]["komponente"] == v["b"]["komponente"]:
            befunde.append(_b(pfad, "a und b gehören zur selben Komponente"))
        if v["typ"] in MIT_AUSRICHTUNG and "ausrichtung" not in v:
            befunde.append(_b(f"{pfad}.ausrichtung", f"ausrichtung (gleich | entgegengesetzt) ist bei {v['typ']} Pflicht"))
        if v["typ"] in MIT_WERT and "wert" not in v:
            befunde.append(_b(f"{pfad}.wert", f"wert ist bei {v['typ']} Pflicht"))
        if v["typ"] not in MIT_WERT and "wert" in v:
            befunde.append(_b(f"{pfad}.wert", "wert gilt nur bei abstand/winkel"))
        if "drehung_sperren" in v and v["typ"] != "konzentrisch":
            befunde.append(_b(f"{pfad}.drehung_sperren", "drehung_sperren gilt nur bei konzentrisch"))
        if "wert" in v:
            try:
                w = auswerten(v["wert"], p)
                if v["typ"] == "abstand" and w < 0:
                    befunde.append(_b(f"{pfad}.wert", f"abstand muss ≥ 0 sein (ist {w:g})"))
                if v["typ"] == "winkel" and not 0 <= w <= 180:
                    befunde.append(_b(f"{pfad}.wert", f"winkel muss in [0, 180] liegen (ist {w:g})"))
            except AusdruckFehler as e:
                befunde.append(_b(f"{pfad}.wert", str(e)))
        befunde += _je_befunde(v, pfad, spec)
    genannt = {v[s]["komponente"] for v in vs for s in ("a", "b")}
    for k in spec["komponenten"]:
        if not k.get("fixiert") and k["id"] not in genannt:
            befunde.append(_b("verknuepfungen", f"{k['id']} kommt in keiner Verknüpfung vor"))
    return befunde


def _freiheitsgrade_befunde(spec: dict) -> list[dict]:
    bekannt = {k["id"] for k in spec["komponenten"]} | {k["gruppe"] for k in spec["komponenten"] if k.get("gruppe")}
    return [_b(f"freiheitsgrade.{n}", f"{n!r} ist weder Komponente noch Gruppe")
            for n in spec.get("freiheitsgrade", {}) if n.split(".")[0] not in bekannt]


def _pruefung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    pr = spec.get("pruefung", {})
    p = spec.get("parameter", {})
    werte = [("pruefung.huellquader", w) for w in pr.get("huellquader", [])]
    if "masse" in pr:
        werte.append(("pruefung.masse.soll", pr["masse"]["soll"]))
    for i, mp in enumerate(pr.get("masse_pruefen", [])):
        werte.append((f"pruefung.masse_pruefen[{i}].soll", mp["soll"]))
        for s in ("von", "zu"):
            if "komponente" in mp[s]:
                befunde += referenz_befunde(mp[s], f"pruefung.masse_pruefen[{i}].{s}", quellen, spec, instanz_id_erlaubt=True)
            else:
                werte += [(f"pruefung.masse_pruefen[{i}].{s}.punkt", w) for w in mp[s]["punkt"]]
    for pfad, w in werte:
        try:
            auswerten(w, p)
        except AusdruckFehler as e:
            befunde.append(_b(pfad, str(e)))
    return befunde


def plausibel_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Alle Plausibilitätsbefunde; Komponentenfehler zuerst (sonst lassen sich Instanzen nicht zählen)."""
    befunde = _komponenten_befunde(spec, quellen)
    if befunde:
        return befunde
    befunde = _verknuepfung_befunde(spec, quellen) + _freiheitsgrade_befunde(spec) + _pruefung_befunde(spec, quellen)
    return befunde + passung_befunde(spec, quellen)
```

- [ ] **Step 7: `swki/baugruppe/laden.py`** – Plausibilität aufrufen (Import `from swki.baugruppe.plausibel import plausibel_befunde`; Docstring „Die Plausibilität kommt in Task 3 dazu.“ durch „…, Plausibilität.“ ersetzen)

```python
    if not befunde:
        quellen, teile, befunde = lade_quellen(spec, pfad.parent)
        if not befunde:
            befunde = plausibel_befunde(spec, quellen)
```

- [ ] **Step 8: `swki/baugruppe/hinweise.py`**

```python
"""Hinweise zu einer gültigen Baugruppen-Spezifikation (Spec 3b §5.8); sie blockieren nie."""

from swki.baugruppe.modell import Baugruppe
from swki.spec.hinweise import hinweise as teil_hinweise


def hinweise_baugruppe(bg: Baugruppe) -> list[dict]:
    ergebnis = []
    for datei, teil in bg.teile.items():
        komponente = bg.komponente_von(datei)
        ergebnis += [{**h, "pfad": f"{komponente}: {h['pfad']}"} for h in teil_hinweise(teil)]
    for i, v in enumerate(bg.spec.get("verknuepfungen", [])):
        for s in ("a", "b"):
            if "nahe" in v[s]:
                ergebnis.append({"art": "nahe", "pfad": f"verknuepfungen[{i}].{s}",
                                 "meldung": "Punktanker in einer Verknüpfung: bevorzugt referenz, {feature, flaeche} "
                                            "oder Bohrungsachse"})
        w = v.get("wert")
        if isinstance(w, (int, float)) and not isinstance(w, bool) and w != 0:
            ergebnis.append({"art": "feste_zahl", "pfad": f"verknuepfungen[{i}].wert",
                             "meldung": f"feste Zahl {w:g}: als Parameter führen, wenn der Wert eine Anforderung ist "
                                        "(sonst deckt die Freigabe ihn nicht ab)"})
    return ergebnis
```

- [ ] **Step 9: `swki/baugruppe/befehle.py`**

```python
"""Baugruppen-Zweige der Befehle validieren und freigeben (Weiche in swki.spec.befehle)."""

from pathlib import Path

from swki.baugruppe.aufloesen import instanzen, verknuepfungen
from swki.baugruppe.hinweise import hinweise_baugruppe
from swki.baugruppe.laden import lade_baugruppe


def validieren(pfad: Path) -> dict:
    bg = lade_baugruppe(pfad)
    return {
        "gueltig": True, "spec": str(pfad), "art": "baugruppe", "name": bg.spec["name"],
        "komponenten": len(instanzen(bg.spec, bg.quellen)),
        "verknuepfungen": len(verknuepfungen(bg.spec, bg.quellen)),
        "hinweise": hinweise_baugruppe(bg),
    }
```

- [ ] **Step 10: `swki/spec/befehle.py`** – Weiche (Import `from swki.spec.laden import art_der_datei, lade_spec`)

```python
def _validieren(args) -> dict:
    pfad = Path(args.spec)
    if art_der_datei(pfad) == "baugruppe":
        from swki.baugruppe.befehle import validieren  # spät importiert: swki.baugruppe nutzt swki.spec

        return validieren(pfad)
    spec = lade_spec(pfad)
    return {
        "gueltig": True,
        "spec": str(pfad),
        "name": spec["name"],
        "features": len(spec["features"]),
        "pruefsumme": pruefsumme(spec),
        "hinweise": hinweise(spec),
    }
```

- [ ] **Step 11: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: grün, **506 passed** (473 + 33: Plausibilität 16, Passung 14, Befehle 3).

- [ ] **Step 12: Commit**

```powershell
git add swki/baugruppe swki/spec/befehle.py tests/baugruppe
git commit -m "baugruppe: Plausibilität, Passung Normteil–Bohrung, Hinweise, validieren" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Freigabe der Baugruppe (eine Freigabe für Baugruppe und Teile)

**Files:**
- Modify: `swki/spec/freigabe.py` (Prüffelder Baugruppe, Parameter `teile`)
- Create: `swki/baugruppe/freigabe.py`
- Modify: `swki/baugruppe/befehle.py` (`freigeben`, Prüfsumme in `validieren`), `swki/spec/befehle.py` (Weiche in `_freigeben`)
- Create: `tests/baugruppe/test_freigabe_baugruppe.py`

**Interfaces:**
- Consumes: Task 2/3 (`lade_baugruppe`, `Baugruppe`).
- Produces: `pruefsumme(spec, teile: dict[str, str] | None = None)`, `freigeben(spec_pfad, spec, zeitpunkt=None, teile=None)`, `pruefe_freigabe(spec_pfad, spec, teile=None)`; `teil_summen(bg) -> dict[str, str]`, `freigeben_baugruppe(bg, zeitpunkt=None) -> dict`, `pruefe_freigabe_baugruppe(bg) -> dict`, `freigegebene_teile(bg) -> dict[str, dict]`; `swki.baugruppe.befehle.freigeben(pfad) -> dict`.

- [ ] **Step 1: Failing tests – `tests/baugruppe/test_freigabe_baugruppe.py` (neu)**

```python
import json

import pytest
import yaml

from swki.baugruppe.freigabe import freigeben_baugruppe, freigegebene_teile, pruefe_freigabe_baugruppe, teil_summen
from swki.baugruppe.laden import lade_baugruppe
from swki.cli import main
from swki.spec.freigabe import FreigabeFehler, freigabe_pfad, pruefsumme
from tests.baugruppe.beispiel import BAUGRUPPE, PLATTE, kopie, schreibe


def test_pruefsumme_ignoriert_verknuepfungen():
    anders = kopie(BAUGRUPPE)
    anders["verknuepfungen"][2]["ausrichtung"] = "entgegengesetzt"
    anders["verknuepfungen"].pop()
    assert pruefsumme(anders, {"a.yaml": "1"}) == pruefsumme(BAUGRUPPE, {"a.yaml": "1"})


def test_pruefsumme_erfasst_komponenten():
    anders = kopie(BAUGRUPPE)
    anders["komponenten"][2]["quelle"] = {"normteil": "ISO 4762 M8x20"}
    assert pruefsumme(anders, {}) != pruefsumme(BAUGRUPPE, {})


def test_pruefsumme_erfasst_teile():
    assert pruefsumme(BAUGRUPPE, {"platte.yaml": "1"}) != pruefsumme(BAUGRUPPE, {"platte.yaml": "2"})


def test_freigeben_schreibt_alle_specs(tmp_path):
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    eintrag = freigeben_baugruppe(bg, zeitpunkt="2026-10-03T10:00:00")
    daten = json.loads(freigabe_pfad(bg.pfad).read_text(encoding="utf-8"))
    assert set(daten) == {"probe.yaml", "platte.yaml", "deckel.yaml"}
    assert eintrag["teile"] == {"platte.yaml": daten["platte.yaml"], "deckel.yaml": daten["deckel.yaml"]}
    assert (tmp_path / "A" / "platte.freigegeben.yaml").exists() and (tmp_path / "A" / "probe.freigegeben.yaml").exists()
    assert pruefe_freigabe_baugruppe(bg)["pruefsumme"] == pruefsumme(bg.spec, teil_summen(bg))
    assert freigegebene_teile(bg)["platte.yaml"]["name"] == "Platte"


def test_geaenderte_teil_anforderung_nennt_teil(tmp_path):
    pfad = schreibe(tmp_path / "A")
    freigeben_baugruppe(lade_baugruppe(pfad))
    platte = kopie(PLATTE)
    platte["parameter"]["L"] = 110
    (pfad.parent / "platte.yaml").write_text(yaml.safe_dump(platte, allow_unicode=True), encoding="utf-8")
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe_baugruppe(lade_baugruppe(pfad))
    assert e.value.daten["code"] == "FREIGABE_VERALTET" and "platte.yaml" in str(e.value)


def test_geaenderte_verknuepfung_bleibt_freigegeben(tmp_path):
    pfad = schreibe(tmp_path / "A")
    freigeben_baugruppe(lade_baugruppe(pfad))
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][2]["b"] = {"komponente": "platte", "feature": "f1", "flaeche": "-x"}
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    pruefe_freigabe_baugruppe(lade_baugruppe(pfad))


def test_freigeben_befehl(capsys, tmp_path):
    code = main(["freigeben", str(schreibe(tmp_path / "A"))])
    daten = json.loads(capsys.readouterr().out)
    assert code == 0, daten
    assert set(daten["teile"]) == {"platte.yaml", "deckel.yaml"} and daten["art"] == "baugruppe"
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_freigabe_baugruppe.py -q`
Expected: FAIL (ImportError `swki.baugruppe.freigabe`; `pruefsumme` kennt `teile` nicht).

- [ ] **Step 3: `swki/spec/freigabe.py`** – Prüffelder je Art, Teil-Prüfsummen (Docstring um „Baugruppen: zusätzlich die Prüfsummen der Teil-Specs (Spec 3b §6).“ ergänzen)

```python
PRUEF_FELDER = ("art", "name", "parameter", "material", "eigenschaften", "pruefung")
PRUEF_FELDER_BAUGRUPPE = ("art", "name", "parameter", "eigenschaften", "komponenten", "freiheitsgrade", "pruefung")


def pruefsumme(spec: dict, teile: dict[str, str] | None = None) -> str:
    """Prüfsumme der Anforderungen; bei Baugruppen zusätzlich über die Prüfsummen der Teil-Specs (Dateiname → Summe)."""
    felder = PRUEF_FELDER_BAUGRUPPE if spec.get("art") == "baugruppe" else PRUEF_FELDER
    kern = {feld: spec.get(feld) for feld in felder}
    if teile is not None:
        kern["teile"] = teile
    text = json.dumps(kern, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _sha256(text)
```

`freigeben` und `pruefe_freigabe` bekommen den Parameter `teile` und reichen ihn an `pruefsumme` weiter (sonst unverändert):

```python
def freigeben(spec_pfad: Path, spec: dict, zeitpunkt: str | None = None, teile: dict[str, str] | None = None) -> dict:
    pfad = freigabe_pfad(spec_pfad)
    daten = _lies(pfad)
    kopie = _rohtext_oder_dump(spec_pfad, spec)
    kopie_pfad(spec_pfad).write_text(kopie, encoding="utf-8")
    eintrag = {
        "pruefsumme": pruefsumme(spec, teile),
        "freigegeben": zeitpunkt or datetime.now().isoformat(timespec="seconds"),
        "kopie_sha256": _sha256(kopie),
    }
    daten[spec_pfad.name] = eintrag
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return eintrag


def pruefe_freigabe(spec_pfad: Path, spec: dict, teile: dict[str, str] | None = None) -> dict:
    """Wirft FreigabeFehler, wenn die Spezifikation nicht (mehr) freigegeben ist."""
    eintrag = _lies(freigabe_pfad(spec_pfad)).get(spec_pfad.name)
    if eintrag is None:
        raise FreigabeFehler("FREIGABE_FEHLT", f"{spec_pfad.name} ist nicht freigegeben. Zuerst: swki freigeben")
    if eintrag["pruefsumme"] != pruefsumme(spec, teile):
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
```

- [ ] **Step 4: `swki/baugruppe/freigabe.py`**

```python
"""Eine Freigabe für Baugruppe und Teil-Specs (Spec 3b §6). Jede Teil-Spec bekommt ihren Eintrag in freigabe.json und
ihre Freigabe-Kopie; die Baugruppe zusätzlich eine Prüfsumme über die Prüfsummen der Teile."""

import yaml

from swki.baugruppe.modell import Baugruppe
from swki.spec.freigabe import freigeben, kopie_pfad, pruefe_freigabe, pruefsumme


def teil_summen(bg: Baugruppe) -> dict[str, str]:
    return {datei: pruefsumme(spec) for datei, spec in bg.teile.items()}


def freigeben_baugruppe(bg: Baugruppe, zeitpunkt: str | None = None) -> dict:
    teile = {datei: freigeben(bg.pfad.parent / datei, spec, zeitpunkt) for datei, spec in bg.teile.items()}
    return {**freigeben(bg.pfad, bg.spec, zeitpunkt, teile=teil_summen(bg)), "teile": teile}


def pruefe_freigabe_baugruppe(bg: Baugruppe) -> dict:
    """Erst jede Teil-Spec (die Meldung nennt das Teil), dann die Baugruppe; wirft FreigabeFehler."""
    for datei, spec in bg.teile.items():
        pruefe_freigabe(bg.pfad.parent / datei, spec)
    return pruefe_freigabe(bg.pfad, bg.spec, teile=teil_summen(bg))


def freigegebene_teile(bg: Baugruppe) -> dict[str, dict]:
    """Teil-Specs im Stand der Freigabe (Soll der Teilprüfungen)."""
    return {datei: yaml.safe_load(kopie_pfad(bg.pfad.parent / datei).read_text(encoding="utf-8")) for datei in bg.teile}
```

- [ ] **Step 5: `swki/baugruppe/befehle.py`** – `freigeben` und Prüfsumme in `validieren`

```python
from swki.baugruppe.freigabe import freigeben_baugruppe, teil_summen
from swki.spec.freigabe import kopie_pfad, pruefsumme


def validieren(pfad: Path) -> dict:
    bg = lade_baugruppe(pfad)
    return {
        "gueltig": True, "spec": str(pfad), "art": "baugruppe", "name": bg.spec["name"],
        "komponenten": len(instanzen(bg.spec, bg.quellen)),
        "verknuepfungen": len(verknuepfungen(bg.spec, bg.quellen)),
        "pruefsumme": pruefsumme(bg.spec, teil_summen(bg)),
        "hinweise": hinweise_baugruppe(bg),
    }


def freigeben(pfad: Path) -> dict:
    bg = lade_baugruppe(pfad)
    return {"spec": str(pfad), "art": "baugruppe", "kopie": str(kopie_pfad(pfad)), **freigeben_baugruppe(bg)}
```

- [ ] **Step 6: `swki/spec/befehle.py`** – Weiche in `_freigeben` (nach der Prüfung auf die Kopie-Endung)

```python
    if art_der_datei(pfad) == "baugruppe":
        from swki.baugruppe.befehle import freigeben as freigeben_baugruppe  # spät importiert (Kreisimport)

        return freigeben_baugruppe(pfad)
    spec = lade_spec(pfad)
```

- [ ] **Step 7: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: grün, **513 passed** (506 + 7).

- [ ] **Step 8: Commit**

```powershell
git add swki/spec/freigabe.py swki/spec/befehle.py swki/baugruppe/freigabe.py swki/baugruppe/befehle.py tests/baugruppe/test_freigabe_baugruppe.py
git commit -m "baugruppe: eine Freigabe für Baugruppe und Teil-Specs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Änderungserkennung für Teile und Baugruppen (Prüfsummen, Verweigern, `swki aenderungen`)

**Files:**
- Create: `swki/aenderungen.py`
- Modify: `swki/compiler/protokoll.py` (Felder), `swki/compiler/bauen.py` (`baue_teil_dokument`, Prüfsummen, Änderungserkennung, `--verwerfen`, Weiche), `swki/pruefung/messen.py` (`oeffne` nach Endung), `swki/cli.py` (Befehlsgruppe)
- Create: `tests/test_aenderungen.py`, `tests/live/test_live_aenderungen.py`
- Modify: `tests/compiler/test_bauen.py`

**Interfaces:**
- Consumes: Task 2/4 (`lade_baugruppe`, `freigegebene_teile`, `dokument_name`); `swki.auftrag`; `swki.spec.freigabe.freigegebene_spec`.
- Produces:
  - `Protokoll` + `sha256: dict[str, str]`, `verworfen: dict | None`, `teile: dict[str, dict]`, `komponenten: list[dict]`, `normteile: dict[str, dict]`
  - `baue_teil_dokument(app, r, standard, spec, spec_pfad, auftrag, protokoll) -> (model, ctx, fehler)`; `bauen(spec_pfad, lauf=None, verwerfen=False)`
  - `oeffne(app, pfad)` öffnet `.sldasm` als Baugruppe
  - `MANUELL_GEAENDERT`, `AenderungFehler`, `sha256_datei(pfad)`, `pruefsummen(ordner, dateien) -> dict[str, str]`, `letzter_gebauter_lauf(spec_pfad) -> (int, dict) | None`, `abweichungen(ordner, soll) -> {"geaendert", "fehlend"}`, `pruefe_unveraendert(r, auftrag, spec_pfad, verwerfen=False) -> dict | None`, `parameter_differenz(soll, ist) -> list[dict]`, `lies_globale_variablen(model) -> dict[str, float]`, `soll_parameter(spec_pfad, auftrag, standard) -> dict[str, dict]`, `aenderungen(spec_pfad, lauf=None) -> dict`

- [ ] **Step 1: Failing tests – `tests/test_aenderungen.py` (neu)**

```python
import json
from pathlib import Path

import pytest
import yaml

from swki import aenderungen
from swki.aenderungen import (
    MANUELL_GEAENDERT, AenderungFehler, abweichungen, letzter_gebauter_lauf, parameter_differenz, pruefe_unveraendert,
    pruefsummen, sha256_datei,
)
from swki.auftrag import lauf_datei, lauf_ordner
from swki.konfig import Rechner
from swki.spec.freigabe import freigeben
from tests.spec.beispiel import GUELTIG


@pytest.fixture
def umgebung(tmp_path):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    spec_pfad = tmp_path / "auftraege" / "A" / "platte.yaml"
    spec_pfad.parent.mkdir(parents=True)
    spec_pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    return r, spec_pfad


def _lauf(r, spec_pfad, n: int, status: str = "ok", inhalt: bytes | None = b"teil", mit_summen: bool = True) -> Path:
    ordner = lauf_ordner(r, "A", n)
    ordner.mkdir(parents=True)
    datei = ordner / "A_Platte_1.sldprt"
    summen = {}
    if inhalt is not None:
        datei.write_bytes(inhalt)
        summen = pruefsummen(ordner, [datei])
    protokoll = {"status": status, **({"sha256": summen} if mit_summen else {})}
    ziel = lauf_datei(spec_pfad, n, "protokoll")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(protokoll), encoding="utf-8")
    return datei


def test_sha256_datei(tmp_path):
    (tmp_path / "x").write_bytes(b"abc")
    assert sha256_datei(tmp_path / "x") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_pruefsummen_relativ(tmp_path):
    (tmp_path / "bilder").mkdir()
    (tmp_path / "bilder" / "iso.png").write_bytes(b"1")
    (tmp_path / "a.sldprt").write_bytes(b"2")
    summen = pruefsummen(tmp_path, [tmp_path / "a.sldprt", tmp_path / "bilder" / "iso.png", tmp_path / "fehlt.step"])
    assert set(summen) == {"a.sldprt", "bilder/iso.png"}


def test_letzter_gebauter_lauf(umgebung):
    r, spec_pfad = umgebung
    _lauf(r, spec_pfad, 1)
    _lauf(r, spec_pfad, 2, status="fehler")
    assert letzter_gebauter_lauf(spec_pfad)[0] == 1
    _lauf(r, spec_pfad, 3, mit_summen=False)          # vor Stufe 3b gebaut
    assert letzter_gebauter_lauf(spec_pfad) is None


def test_abweichungen(tmp_path):
    (tmp_path / "a").write_bytes(b"1")
    (tmp_path / "b").write_bytes(b"2")
    soll = pruefsummen(tmp_path, [tmp_path / "a", tmp_path / "b"])
    (tmp_path / "a").write_bytes(b"geaendert")
    (tmp_path / "b").unlink()
    assert abweichungen(tmp_path, soll) == {"geaendert": ["a"], "fehlend": ["b"]}


def test_geaenderter_lauf_wird_verweigert(umgebung):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    assert pruefe_unveraendert(r, "A", spec_pfad) is None
    datei.write_bytes(b"von Hand geaendert")
    with pytest.raises(AenderungFehler) as e:
        pruefe_unveraendert(r, "A", spec_pfad)
    assert e.value.daten["code"] == MANUELL_GEAENDERT and e.value.daten["lauf"] == 1
    assert e.value.daten["geaendert"] == ["A_Platte_1.sldprt"] and "--verwerfen" in str(e.value)
    assert pruefe_unveraendert(r, "A", spec_pfad, verwerfen=True)["geaendert"] == ["A_Platte_1.sldprt"]


def test_aufgeraeumter_lauf_wird_nicht_verweigert(umgebung):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    for p in datei.parent.iterdir():
        p.unlink()
    datei.parent.rmdir()
    assert pruefe_unveraendert(r, "A", spec_pfad) is None


def test_parameter_differenz():
    assert parameter_differenz({"L": 100, "B": 60, "H": 20}, {"L": 120.0, "B": 60.0, "T": 5.0}) == [
        {"name": "H", "soll": 20, "ist": None}, {"name": "L", "soll": 100, "ist": 120.0},
        {"name": "T", "soll": None, "ist": 5.0}]


def test_aenderungen_ohne_geaenderte_datei(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    freigeben(spec_pfad, GUELTIG)
    _lauf(r, spec_pfad, 1)
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: pytest.fail("ohne Änderung kein SolidWorks"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert (ergebnis["lauf"], ergebnis["geaendert"], ergebnis["fehlend"]) == (1, [], [])
```

- [ ] **Step 2: Failing tests – `tests/compiler/test_bauen.py` anhängen**

```python
def _gebauter_lauf(r, spec_pfad, inhalt: bytes) -> Path:
    from swki.aenderungen import pruefsummen

    ordner = lauf_ordner(r, "A", 1)
    ordner.mkdir(parents=True)
    datei = ordner / "A_platte.sldprt"
    datei.write_bytes(b"gebaut")
    protokoll = lauf_datei(spec_pfad, 1, "protokoll")
    protokoll.parent.mkdir(parents=True, exist_ok=True)
    protokoll.write_text(json.dumps({"status": "ok", "sha256": pruefsummen(ordner, [datei])}), encoding="utf-8")
    datei.write_bytes(inhalt)
    return datei


def test_manuelle_aenderung_wird_vor_solidworks_verweigert(umgebung):
    r, spec_pfad, aufrufe = umgebung
    _gebauter_lauf(r, spec_pfad, b"von Hand geaendert")
    with pytest.raises(SwkiFehler) as e:
        bauen_modul.bauen(spec_pfad)
    assert e.value.daten["code"] == "MANUELL_GEAENDERT" and aufrufe["verbinde"] == 0


def test_verwerfen_baut_trotzdem(umgebung):
    r, spec_pfad, aufrufe = umgebung
    _gebauter_lauf(r, spec_pfad, b"von Hand geaendert")
    with pytest.raises(_KeinSolidWorks):
        bauen_modul.bauen(spec_pfad, verwerfen=True)
    assert aufrufe["protokoll_lauf"] == 2
```

(Import `import json` am Dateianfang ergänzen.)

- [ ] **Step 3: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_aenderungen.py tests/compiler/test_bauen.py -q`
Expected: FAIL (ImportError `swki.aenderungen`; `bauen()` kennt `verwerfen` nicht).

- [ ] **Step 4: `swki/compiler/protokoll.py`** – Felder nach `fehler` ergänzen

```python
    fehler: dict | None = None
    sha256: dict[str, str] = field(default_factory=dict)  # gespeicherte Dateien (relativ zum Lauf-Ordner) → SHA-256
    verworfen: dict | None = None  # Befund der Änderungserkennung, den swki bauen --verwerfen übergangen hat
    teile: dict[str, dict] = field(default_factory=dict)  # Baugruppe: Teil-Spec → Protokoll des Teil-Baus
    komponenten: list[dict] = field(default_factory=list)  # Baugruppe: [{"id", "sw_name", "datei"}]
    normteile: dict[str, dict] = field(default_factory=dict)  # Baugruppe: Schlüssel → {"bibliothek", "gebaut", "pruefsumme"}
```

- [ ] **Step 5: `swki/pruefung/messen.py`** – `oeffne` nach Endung

```python
SW_DOC_PART = 1  # swDocumentTypes_e
SW_DOC_ASSEMBLY = 2


def oeffne(app, pfad: Path):
    """Öffnet ein gespeichertes Teil oder eine Baugruppe (Typ nach der Endung). Ist das Dokument schon offen (evtl. beim
    Nutzer), wird abgebrochen statt es zu schließen."""
    typ = SW_DOC_ASSEMBLY if pfad.suffix.lower() == ".sldasm" else SW_DOC_PART
    fehler, warnungen = byref_long(), byref_long()
    model = app.OpenDoc6(str(pfad), typ, SW_OPEN_SILENT, "", fehler, warnungen)
    if model is None:
        raise PruefFehler(f"{pfad.name} ließ sich nicht öffnen (Fehler {fehler.value})")
    if warnungen.value & SW_WARNUNG_BEREITS_OFFEN:
        raise PruefFehler(f"{pfad.name} ist bereits in SolidWorks geöffnet – bitte schließen und erneut prüfen")
    return model
```

- [ ] **Step 6: `swki/aenderungen.py`**

```python
"""Änderungserkennung (Spec 3b §8): manuelle Änderungen an gebauten Dateien erkennen, bevor ein neuer Lauf sie still
verliert.

swki bauen schreibt den SHA-256 jeder gespeicherten Datei ins Protokoll (Feld sha256). Vor dem nächsten Bau vergleicht
pruefe_unveraendert den höchsten durchgebauten Lauf (Protokollstatus ok) damit. Läufe ohne Prüfsummen (vor Stufe 3b) und
ganz entfernte Lauf-Ordner gelten als unverändert. swki aenderungen liest die Parameter geänderter Dateien aus (mit
SolidWorks, nur lesend) und vergleicht sie mit der freigegebenen Spezifikation."""

import hashlib
import json
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_nummern_dateien, lauf_ordner
from swki.cli import SwkiFehler, ganzzahl_ab
from swki.compiler import sw
from swki.konfig import Rechner, lade_rechner, lade_standard
from swki.pruefung.messen import oeffne
from swki.spec.freigabe import freigegebene_spec
from swki.spec.laden import art_der_datei
from swki.verbindung import verbinde

MANUELL_GEAENDERT = "MANUELL_GEAENDERT"
_TOL = 1e-6
_SW_DATEIEN = (".sldprt", ".sldasm")


class AenderungFehler(SwkiFehler):
    def __init__(self, meldung: str, **daten):
        super().__init__(meldung)
        self.daten = {"code": MANUELL_GEAENDERT, **daten}


def sha256_datei(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pruefsummen(ordner: Path, dateien) -> dict[str, str]:
    """{Pfad relativ zum Lauf-Ordner: SHA-256} der vorhandenen Dateien."""
    return {Path(d).relative_to(ordner).as_posix(): sha256_datei(Path(d)) for d in dateien if Path(d).is_file()}


def letzter_gebauter_lauf(spec_pfad: Path) -> tuple[int, dict] | None:
    """(Nummer, Protokoll) des höchsten Laufs mit Status ok, wenn er Prüfsummen hat; sonst None."""
    for n in sorted(lauf_nummern_dateien(spec_pfad), reverse=True):
        try:
            protokoll = json.loads(lauf_datei(spec_pfad, n, "protokoll").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(protokoll, dict) and protokoll.get("status") == "ok":
            return (n, protokoll) if protokoll.get("sha256") else None
    return None


def abweichungen(ordner: Path, soll: dict[str, str]) -> dict[str, list[str]]:
    geaendert, fehlend = [], []
    for name, summe in sorted(soll.items()):
        pfad = ordner / name
        if not pfad.is_file():
            fehlend.append(name)
        elif sha256_datei(pfad) != summe:
            geaendert.append(name)
    return {"geaendert": geaendert, "fehlend": fehlend}


def befund(r: Rechner, auftrag: str, spec_pfad: Path) -> dict | None:
    letzter = letzter_gebauter_lauf(spec_pfad)
    if letzter is None:
        return None
    n, protokoll = letzter
    ordner = lauf_ordner(r, auftrag, n)
    if not ordner.is_dir():
        return None  # Lauf-Ordner aufgeräumt: es gibt nichts, was verloren gehen könnte
    a = abweichungen(ordner, protokoll["sha256"])
    return {"lauf": n, **a} if a["geaendert"] or a["fehlend"] else None


def pruefe_unveraendert(r: Rechner, auftrag: str, spec_pfad: Path, verwerfen: bool = False) -> dict | None:
    """Wirft AenderungFehler, wenn Dateien des letzten durchgebauten Laufs geändert wurden oder fehlen; mit verwerfen
    wird der Befund nur zurückgegeben (fürs Protokoll)."""
    b = befund(r, auftrag, spec_pfad)
    if b is not None and not verwerfen:
        raise AenderungFehler(
            f"Lauf {b['lauf']} wurde nach dem Bau verändert ({', '.join(b['geaendert'] + b['fehlend'])}). "
            "swki aenderungen zeigt die Parameter; Nutzer fragen: übernehmen (Spezifikation ändern, neu freigeben) "
            "oder verwerfen (swki bauen --verwerfen)", **b)
    return b


def parameter_differenz(soll: dict, ist: dict) -> list[dict]:
    """Parameter, die fehlen, neu sind oder sich um mehr als 1e-6 unterscheiden (alphabetisch)."""
    differenz = []
    for name in sorted(set(soll) | set(ist)):
        s, i = soll.get(name), ist.get(name)
        if s is None or i is None or abs(float(s) - float(i)) > _TOL:
            differenz.append({"name": name, "soll": s, "ist": i})
    return differenz


def lies_globale_variablen(model) -> dict[str, float]:
    """Globale Variablen (Name → Wert in mm bzw. Grad; IEquationMgr.Value wie in Spike S9a Baustein 5)."""
    gleichungen = model.GetEquationMgr
    werte = {}
    for i in range(gleichungen.GetCount):
        if gleichungen.GlobalVariable(i):
            werte[gleichungen.Equation(i).split('"')[1]] = float(gleichungen.Value(i))
    return werte


def soll_parameter(spec_pfad: Path, auftrag: str, standard: dict) -> dict[str, dict]:
    """Dateiname im Lauf → Parameter der freigegebenen Spezifikation (Teil bzw. Baugruppe und ihre Teile)."""
    soll = freigegebene_spec(spec_pfad)
    ergebnis = {}
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.freigabe import freigegebene_teile  # spät importiert: swki.baugruppe nutzt swki.compiler
        from swki.baugruppe.laden import lade_baugruppe
        from swki.baugruppe.modell import dokument_name

        bg = lade_baugruppe(spec_pfad)
        ergebnis[f"{dateiname(soll, auftrag, standard)}.sldasm"] = soll.get("parameter", {})
        for datei, teil in freigegebene_teile(bg).items():
            ergebnis[dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard)] = teil.get("parameter", {})
    else:
        ergebnis[f"{dateiname(soll, auftrag, standard)}.sldprt"] = soll.get("parameter", {})
    return ergebnis


def aenderungen(spec_pfad: Path, lauf: int | None = None) -> dict:
    """Geänderte Dateien eines Laufs mit Parameterdifferenz zur Freigabe; öffnet SolidWorks nur bei geänderten
    .sldprt/.sldasm und speichert nie."""
    spec_pfad = spec_pfad.resolve()
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is None:
        letzter = letzter_gebauter_lauf(spec_pfad)
        if letzter is None:
            return {"spec": spec_pfad.name, "lauf": None, "geaendert": [], "fehlend": [],
                    "text": "kein durchgebauter Lauf mit Prüfsummen"}
        lauf, protokoll = letzter
    else:
        protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    ordner = lauf_ordner(r, auftrag, lauf)
    a = abweichungen(ordner, protokoll.get("sha256", {}))
    soll = soll_parameter(spec_pfad, auftrag, standard)
    ergebnis = []
    sw_dateien = [n for n in a["geaendert"] if n.lower().endswith(_SW_DATEIEN)]
    if sw_dateien:
        app = verbinde(r.sw_jahr)
        for name in sw_dateien:
            model = oeffne(app, ordner / name)
            try:
                ist = lies_globale_variablen(model)
            finally:
                sw.schliesse(app, model)  # schließt ohne zu speichern (S9b)
            if name not in soll:
                ergebnis.append({"datei": name, "parameter": [], "hinweis": "keine Spezifikation zu dieser Datei (Normteil-Kopie)"})
                continue
            differenz = parameter_differenz(soll[name], ist)
            eintrag = {"datei": name, "parameter": differenz}
            if not differenz:
                eintrag["hinweis"] = "Datei geändert, Parameter gleich – den Nutzer fragen, was geändert wurde"
            ergebnis.append(eintrag)
    ergebnis += [{"datei": n, "parameter": [], "hinweis": "Datei geändert (nicht ausgelesen)"}
                 for n in a["geaendert"] if n not in sw_dateien]
    return {"spec": spec_pfad.name, "lauf": lauf, "geaendert": ergebnis, "fehlend": a["fehlend"]}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("aenderungen", help="manuelle Änderungen am letzten Lauf auslesen (nur lesend)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Vorgabe: letzter durchgebauter Lauf")
    p.set_defaults(func=lambda a: aenderungen(Path(a.spec), a.lauf))
```

- [ ] **Step 7: `swki/cli.py`** – Befehlsgruppe ergänzen

```python
def _befehlsgruppen() -> list:
    from swki import aenderungen, rechner
    from swki.api import bauen
    from swki.compiler import bauen as compiler_bauen
    from swki.normteile import befehle as normteil_befehle
    from swki.pruefung import befehle as pruefung_befehle
    from swki.spec import befehle as spec_befehle

    return [rechner, bauen, spec_befehle, compiler_bauen, pruefung_befehle, normteil_befehle, aenderungen]
```

- [ ] **Step 8: `swki/compiler/bauen.py`** – `baue_teil_dokument` herauslösen, Prüfsummen, Änderungserkennung, `--verwerfen`, Weiche

Imports ergänzen: `from swki.aenderungen import pruefe_unveraendert, pruefsummen`, `from swki.spec.laden import art_der_datei, lade_spec`. Dann:

```python
def baue_teil_dokument(app, r, standard: dict, spec: dict, spec_pfad: Path, auftrag: str, protokoll: Protokoll):
    """Neues Teil aus der Vorlage, Parameter/Werkstoff/Eigenschaften, Features (auch von swki.baugruppe.bau genutzt).
    Liefert (model, ctx, fehler); das Dokument bleibt offen – der Aufrufer speichert und schließt es."""
    with protokoll.phase("vorbereiten"):
        model = sw.neues_teil(app, r.vorlage_teil)
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
    return model, ctx, fehler


def bauen(spec_pfad: Path, lauf: int | None = None, verwerfen: bool = False) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is not None and lauf_belegt(r, auftrag, spec_pfad, lauf):
        raise SwkiFehler(f"Lauf {lauf} von {auftrag} existiert schon – ohne --lauf baut swki den nächsten freien Lauf")
    verworfen = pruefe_unveraendert(r, auftrag, spec_pfad, verwerfen)
    if lauf is None:
        lauf = naechster_lauf(r, auftrag, spec_pfad)
    ordner = lauf_ordner(r, auftrag, lauf)
    name = dateiname(spec, auftrag, standard)
    protokoll = Protokoll(auftrag, spec_pfad.name, lauf, r.sw_jahr)
    beginn = time.perf_counter()

    app = verbinde(r.sw_jahr)
    protokoll.verworfen = verworfen
    model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, spec_pfad, auftrag, protokoll)
    dateien = {"teil": ordner / f"{name}.sldprt", "step": ordner / f"{name}.step"}
    try:
        with protokoll.phase("speichern"):
            try:
                for pfad in dateien.values():
                    sw.speichere(model, pfad)
                protokoll.dateien = {art: str(pfad) for art, pfad in dateien.items()}
            except Exception as e:
                fehler = fehler or e
    finally:
        sw.schliesse(app, model)  # Titel wird hier neu gelesen (nach SaveAs geändert)
    protokoll.sha256 = pruefsummen(ordner, dateien.values())

    protokoll.status = "fehler" if fehler else "ok"
    # … ab hier unverändert (fehler_dict, dauer_s, schreiben, ergebnis, BauAbbruch)


def _bauen(args) -> dict:
    pfad = Path(args.spec)
    if art_der_datei(pfad) == "baugruppe":
        from swki.baugruppe.bau import bauen as baugruppe_bauen  # spät importiert (Kreisimport); Modul aus Task 8

        return baugruppe_bauen(pfad, args.lauf, args.verwerfen)
    return bauen(pfad, args.lauf, args.verwerfen)


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("bauen", help="freigegebene Spezifikation in SolidWorks bauen (neuer Lauf)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=ganzzahl_ab(1, "--lauf"), help="Laufnummer ≥ 1 (Vorgabe: nächste freie)")
    p.add_argument("--verwerfen", action="store_true",
                   help="manuelle Änderungen am letzten Lauf ausdrücklich verwerfen (nur auf Anweisung des Nutzers)")
    p.set_defaults(func=_bauen)
```

`protokoll.verworfen` wird erst nach `verbinde` gesetzt: die Unit-Tests ersetzen `Protokoll` durch eine Attrappe ohne Attribute und erwarten den Abbruch in `verbinde`. Bis Task 8 existiert `swki.baugruppe.bau` nicht; `swki bauen` mit einer Baugruppe scheitert bis dahin mit `ModuleNotFoundError` (kein Test erwartet etwas anderes).

- [ ] **Step 9: Unit-Tests**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: grün, **523 passed** (513 + 10: Änderungserkennung 8, Bauen 2).

- [ ] **Step 10: Live-Test `tests/live/test_live_aenderungen.py` (neu)**

```python
"""Live: manuelle Parameteränderung an einem gebauten Teil wird vor dem nächsten Lauf erkannt (Spec 3b §8)."""

import json
import shutil

import pythoncom
import pytest
import yaml

from swki.auftrag import lauf_ordner
from swki.cli import main
from swki.compiler import sw
from swki.konfig import lade_rechner
from swki.pruefung.messen import oeffne
from swki.verbindung import verbinde

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-AENDERUNGEN"
SPEC = {
    "art": "teil", "name": "Platte", "material": "1.0038", "eigenschaften": {"Benennung": "Testplatte"},
    "parameter": {"L": 100, "B": 60},
    "features": [{"id": "f1", "typ": "extrusion",
                  "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
                  "ende": {"typ": "blind", "tiefe": 10}}],
    "pruefung": {"huellquader": ["=L", 10, "=B"]},
}


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def _setze_parameter(pfad, name: str, wert: float) -> None:
    """Wie ein Anwender: Teil öffnen, globale Variable ändern (Property-Put per Invoke, S9a), speichern, schließen."""
    app = verbinde(lade_rechner().sw_jahr)
    model = oeffne(app, pfad)
    try:
        gleichungen = model.GetEquationMgr
        index = next(i for i in range(gleichungen.GetCount) if gleichungen.Equation(i).startswith(f'"{name}"'))
        dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
        gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, f'"{name}" = {wert}')
        gleichungen.EvaluateAll
        sw.rebuild(model)
        sw.speichere(model, pfad)
    finally:
        sw.schliesse(app, model)


def test_manuelle_aenderung_am_teil(capsys, tmp_path):
    spec_pfad = tmp_path / AUFTRAG / "platte.yaml"
    spec_pfad.parent.mkdir()
    spec_pfad.write_text(yaml.safe_dump(SPEC, allow_unicode=True), encoding="utf-8")
    try:
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        _setze_parameter(lauf_ordner(lade_rechner(), AUFTRAG, 1) / f"{AUFTRAG}_Platte.sldprt", "L", 120)
        code, daten = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 1 and daten["code"] == "MANUELL_GEAENDERT" and daten["lauf"] == 1, daten
        code, daten = _lauf(capsys, "aenderungen", str(spec_pfad))
        assert code == 0, daten
        [eintrag] = daten["geaendert"]
        assert eintrag["datei"] == f"{AUFTRAG}_Platte.sldprt"
        assert eintrag["parameter"] == [{"name": "L", "soll": 100, "ist": 120.0}]
        code, bau = _lauf(capsys, "bauen", str(spec_pfad), "--verwerfen")
        assert code == 0 and bau["lauf"] == 2, bau
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)
```

- [ ] **Step 11: Live**

Vorbedingungen (eine Instanz, `False 1`). Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_aenderungen.py tests\live\test_live_bauen.py --zeit 300` → alle OK. Spike-Zeile 11: ändert sich der Hash schon beim Öffnen ohne Speichern (S12 `sha_unveraendert` false), anhalten und melden. Private Bytes vorher/nachher berichten.

- [ ] **Step 12: Commit**

```powershell
git add swki/aenderungen.py swki/cli.py swki/compiler/protokoll.py swki/compiler/bauen.py swki/pruefung/messen.py tests/test_aenderungen.py tests/compiler/test_bauen.py tests/live/test_live_aenderungen.py
git commit -m "aenderungen: Prüfsummen je Lauf, MANUELL_GEAENDERT, swki aenderungen, bauen --verwerfen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Neue Vorlagenversionen ISO 7089 und ISO 8734 (Einbauebene 2) mit Prüfer-Urteilen

**Files:**
- Modify: `swki/wissen/normteile/vorlagen/iso7089.yaml`, `swki/wissen/normteile/vorlagen/iso8734.yaml`
- Modify: `tests/normteile/test_vorlagen.py`, `tests/live/test_live_normteile.py`
- Create (über `swki normteil urteil`): neue `iso7089.pruefer.json`, `iso8734.pruefer.json`

**Interfaces:**
- Produces: ISO 7089 mit `EINBAU_EBENE_2` (y = h, gemessen gegen +y mit Soll 0); ISO 8734 misst `EINBAU_EBENE_2` gegen +y mit Soll 0. Beide Vorlagen haben ein bestandenes Urteil zur neuen Prüfsumme – Voraussetzung für `swki normteil hole` in Task 8 und 11.

- [ ] **Step 1: Failing test – `tests/normteile/test_vorlagen.py` anhängen**

```python
@pytest.mark.parametrize("norm", ["iso7089", "iso8734"])
def test_einbauebene_2_fuer_baugruppen(norm):
    """Spec 3b §12: zweite Einbauebene auf der Gegenseite, gegen die Fläche +y mit Soll 0 gemessen."""
    vorlage = yaml.safe_load((ORDNER / "vorlagen" / f"{norm}.yaml").read_text(encoding="utf-8"))
    ebene = next(f for f in vorlage["features"] if f["id"] == "EINBAU_EBENE_2")
    assert ebene["ebene"] == {"basis": "oben", "abstand": "=h" if norm == "iso7089" else "=l"}
    messung = next(m for m in vorlage["pruefung"]["masse_pruefen"] if m["was"] == "EINBAU_EBENE_2")
    assert messung["von"] == {"referenz": "EINBAU_EBENE_2"} and messung["zu"] == {"feature": "f1", "flaeche": "+y"}
    assert messung["soll"] == 0
```

(Imports `yaml`, `pytest` und `ORDNER` aus `swki.normteile.tabelle` ergänzen, falls nicht vorhanden.)

- [ ] **Step 2: Test fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/normteile/test_vorlagen.py -q`
Expected: FAIL (ISO 7089 ohne `EINBAU_EBENE_2`, ISO 8734 misst gegen −y).

- [ ] **Step 3: `swki/wissen/normteile/vorlagen/iso7089.yaml`** – Kopfkommentar und Referenz/Messung ergänzen

```yaml
# Bauvorlage ISO 7089 (Spec 3a §5): Ring Innen-Ø d1, Außen-Ø d2, Dicke h. Lage: Achse = Modell-Y, Auflagefläche in der
# Ebene oben (y = 0), Dicke in +y. EINBAU_EBENE_2 liegt auf der Gegenseite (y = h): darauf sitzen Schraubenkopf bzw.
# Mutter in einer Baugruppe (Spec 3b §12).
```

Nach `EINBAU_EBENE`:

```yaml
  - {id: EINBAU_EBENE_2, typ: referenz, ebene: {basis: oben, abstand: "=h"}}
```

In `masse_pruefen` nach der Messung `EINBAU_EBENE`:

```yaml
    - {was: EINBAU_EBENE_2, von: {referenz: EINBAU_EBENE_2}, zu: {feature: f1, flaeche: "+y"}, soll: 0}
```

- [ ] **Step 4: `swki/wissen/normteile/vorlagen/iso8734.yaml`** – Messung `EINBAU_EBENE_2` ersetzen

```yaml
    - {was: EINBAU_EBENE_2, von: {referenz: EINBAU_EBENE_2}, zu: {feature: f1, flaeche: "+y"}, soll: 0}
```

Kopfkommentar um den Satz ergänzen: „`EINBAU_EBENE_2` wird gegen die Stirnfläche +y mit Soll 0 gemessen (Lage, nicht nur Betrag; Spec 3b §12). `c` ist nur über das Volumen belegt (keine Messart für Fasen).“

- [ ] **Step 5: `tests/live/test_live_normteile.py`** – ISO 7089 prüft die neue Messung

```python
@pytest.mark.parametrize("groesse", ["M5", "M10", "M16"])
def test_iso7089(groesse):
    _ok(_pruefe(_spec("ISO 7089", groesse)), "mass:h", "mass:EINBAU_EBENE", "mass:EINBAU_EBENE_2", "durchmesser:d1",
        "durchmesser:d2")
```

- [ ] **Step 6: Unit-Tests und Tabellenprüfung**

Run: `.venv\Scripts\python.exe -m pytest -q` → **525 passed** (523 + 2).
Run: `.venv\Scripts\python.exe -m swki normteil tabellen-pruefen` → `"gueltig": true`.

- [ ] **Step 7: Live**

Vorbedingungen (eine Instanz, `False 1`). Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_normteile.py --zeit 300` → alle 13 OK (die Tests für ISO 4762/4032 laufen unverändert mit).

- [ ] **Step 8 (Implementer): Musterteile, dann anhalten**

```powershell
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe -m swki normteil muster "ISO 7089"
.venv\Scripts\python.exe -m swki normteil muster "ISO 8734"
```

Erwartet je `"bestanden": true`. Ausgaben (`spec`, `pruefbericht`, `bilder`, `tabelle`, `vorlage`, `vorlage_pruefsumme`) in den Bericht; Status DONE_WITH_CONCERNS „Urteile ausstehend“.

- [ ] **Step 9 (Controller): Prüfer-Agent je Norm**

Wie Plan 3a Task 11 Step 2: je Norm `subagent_type: pruefer` mit Normtabelle (als Eingabe), `spec.yaml` (als freigegebene Spezifikation), `pruefbericht.json`, Screenshot-Ordner; Zusatz: „Normteil in vereinfachter Darstellung; prüfe Form, Lage (Achse = Y, Auflage auf y = 0) und dass jedes Tabellenmaß belegt ist; neu ist die zweite Einbauebene auf der Gegenseite (Messung `mass:EINBAU_EBENE_2`, Soll 0).“ Urteil als rohes JSON in eine Datei, dann:

```powershell
.venv\Scripts\python.exe -m swki normteil urteil "ISO 7089" <urteil.json> --vorlage-pruefsumme <aus Step 8>
.venv\Scripts\python.exe -m swki normteil urteil "ISO 8734" <urteil.json> --vorlage-pruefsumme <aus Step 8>
```

- [ ] **Step 10: Commit**

```powershell
git add swki/wissen/normteile/vorlagen/iso7089.yaml swki/wissen/normteile/vorlagen/iso8734.yaml swki/wissen/normteile/vorlagen/iso7089.pruefer.json swki/wissen/normteile/vorlagen/iso8734.pruefer.json tests/normteile/test_vorlagen.py tests/live/test_live_normteile.py
git commit -m "normteile: Einbauebene 2 für ISO 7089 und ISO 8734 gemessen, neue Prüfer-Urteile" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Referenzauflösung im Teil und SolidWorks-Helfer für Baugruppen

**Files:**
- Create: `swki/baugruppe/referenzen.py`, `swki/baugruppe/sw_baugruppe.py`
- Create: `tests/baugruppe/test_referenzen.py`

**Interfaces:**
- Consumes: `swki.compiler.topologie` (`flaechen`, `loese_flaeche`, `mit_abstand`, `referenz_geometrie`), `swki.compiler.anker` (`zylinder_zu_punkten`, `RICHTUNGEN`, `skalar`, `laenge`, `AnkerFehler`), `swki.compiler.skizze.STANDARD`, `swki.pruefung.geometrie.Messgeometrie`, Task 2 (`Verknuepfung`); Spike-Zeilen 1–5, 8.
- Produces:
  - `TeilReferenz(objekt, geometrie: Messgeometrie, ist_feature: bool)`, `flaeche_der_instanz(kandidaten, richtung) -> Flaeche`, `loese_im_teil(ctx, seite) -> TeilReferenz` (`seite` ohne `komponente`)
  - `sw_baugruppe`: `MATE_TYP`, `AUSRICHTUNG`, `SW_MATE_OK`, `MASS_NAME`, `ausrichtungen(v) -> list[int]`, `rufe(objekt, name)`, `neue_baugruppe(app, vorlage)`, `fuege_ein(app, asm, pfad, box_mm)`, `fixiere(asm, komp)`, `in_baugruppe(komp, ref) -> (objekt, ist_feature)`, `waehle(asm, entitaet, anhaengen)`, `verknuepfungen(asm) -> list`, `fehlercode(feature) -> int`, `verknuepfe(asm, v, a, b, parameter) -> feature`, `komponenten(asm)`, `transform(komp) -> list[float]`, `status(komp) -> int`, `ist_fixiert(komp) -> bool`, `interferenzen(asm) -> list[(list[str], float)]`, `huellquader(asm) -> list[float]`, `masse_kg(asm) -> float`, `aufloesen(asm)`, `verknuepfungswerte(asm) -> dict[str, float]`

- [ ] **Step 1: Failing tests – `tests/baugruppe/test_referenzen.py` (neu)**

```python
from pathlib import Path

import pytest

from swki.baugruppe import referenzen, sw_baugruppe
from swki.baugruppe.aufloesen import Verknuepfung
from swki.baugruppe.referenzen import flaeche_der_instanz, loese_im_teil
from swki.compiler.anker import AnkerFehler, Flaeche
from swki.compiler.kontext import FeatureErgebnis, Kontext


class _Feature:
    def __init__(self, name):
        self.Name = name


def _ctx(ergebnisse=None) -> Kontext:
    return Kontext(None, None, {"parameter": {}}, Path("teil.yaml"), 0.1, ergebnisse=ergebnisse or {})


def _ebene(y, normale=(0.0, 1.0, 0.0), abstand=None):
    return Flaeche("ebene", (0.0, y, 0.0), normale=normale, abstand=abstand, objekt=f"ebene{y}")


def test_flaeche_der_instanz_naechste():
    kandidaten = [_ebene(26.4, abstand=3.0), _ebene(26.4, abstand=60.1), _ebene(0, (0.0, -1.0, 0.0), abstand=26.0)]
    assert flaeche_der_instanz(kandidaten, "+y").objekt == "ebene26.4"


def test_flaeche_der_instanz_mehrdeutig_und_fehlend():
    with pytest.raises(AnkerFehler) as e:
        flaeche_der_instanz([_ebene(1, abstand=3.0), _ebene(2, abstand=3.0)], "+y")
    assert e.value.code == "REFERENZ_MEHRDEUTIG"
    with pytest.raises(AnkerFehler) as e:
        flaeche_der_instanz([_ebene(1, abstand=3.0)], "-y")
    assert e.value.code == "REFERENZ_NICHT_GEFUNDEN"


def test_standardebene(monkeypatch):
    ebenen = [_Feature("Ebene vorne"), _Feature("Ebene oben"), _Feature("Ebene rechts")]
    monkeypatch.setattr(referenzen.sw, "standardebenen", lambda model: ebenen)
    ref = loese_im_teil(_ctx(), {"ebene": "oben"})
    assert ref.ist_feature and ref.objekt is ebenen[1]
    assert (ref.geometrie.art, ref.geometrie.punkt, ref.geometrie.richtung) == ("ebene", (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))


def test_referenz_fehlt():
    with pytest.raises(AnkerFehler) as e:
        loese_im_teil(_ctx(), {"referenz": "TRENNEBENE"})
    assert e.value.code == "REFERENZ_NICHT_GEFUNDEN"


def test_bohrungsachse_der_instanz(monkeypatch):
    zylinder = [Flaeche("zylinder", (-30.0, 0.0, 0.0), achse=(0.0, -1.0, 0.0), radius=3.4, objekt="z1"),
                Flaeche("zylinder", (30.0, 0.0, 0.0), achse=(0.0, -1.0, 0.0), radius=3.4, objekt="z2")]
    monkeypatch.setattr(referenzen, "flaechen", lambda feature: zylinder)
    ctx = _ctx({"f2": FeatureErgebnis([_Feature("f2")], punkte=[(-30.0, 20.0, 0.0), (30.0, 20.0, 0.0)])})
    ref = loese_im_teil(ctx, {"feature": "f2", "instanz": 2, "achse": True})
    assert not ref.ist_feature and ref.objekt == "z2"
    assert ref.geometrie.art == "achse" and ref.geometrie.richtung == (0.0, -1.0, 0.0)


def test_instanz_zu_gross():
    ctx = _ctx({"f2": FeatureErgebnis([_Feature("f2")], punkte=[(0.0, 20.0, 0.0)])})
    with pytest.raises(AnkerFehler) as e:
        loese_im_teil(ctx, {"feature": "f2", "instanz": 2, "achse": True})
    assert "nur 1 Instanzen" in str(e.value)


@pytest.mark.parametrize(("typ", "ausrichtung", "erwartet"), [
    ("deckungsgleich", "gleich", [0]), ("parallel", "entgegengesetzt", [1]), ("konzentrisch", None, [0, 1])])
def test_ausrichtungen(typ, ausrichtung, erwartet):
    v = Verknuepfung("v1", "v1", typ, {}, {}, ausrichtung, None, False)
    assert sw_baugruppe.ausrichtungen(v) == erwartet
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_referenzen.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: `swki/baugruppe/referenzen.py`**

```python
"""Referenzen einer Verknüpfung im Teil auflösen (Spec 3b §4.3): Geometrie im Teildokument finden. Die Übertragung in
den Baugruppenkontext übernimmt swki.baugruppe.sw_baugruppe.in_baugruppe."""

from dataclasses import dataclass

from swki.compiler import sw
from swki.compiler.anker import RICHTUNGEN, AnkerFehler, Flaeche, laenge, skalar, zylinder_zu_punkten
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN
from swki.compiler.skizze import STANDARD
from swki.compiler.topologie import flaechen, loese_flaeche, mit_abstand, referenz_geometrie
from swki.pruefung.geometrie import Messgeometrie

_PARALLEL = 1.0 - 1e-6
_GLEICH_MM = 1e-4
NORMALE = {"vorne": (0.0, 0.0, 1.0), "oben": (0.0, 1.0, 0.0), "rechts": (1.0, 0.0, 0.0)}


@dataclass
class TeilReferenz:
    objekt: object             # IFace2 oder IFeature im Teildokument
    geometrie: Messgeometrie   # in Teilkoordinaten (mm)
    ist_feature: bool          # Bezugs-/Standardebene oder -achse: Auswahl über IComponent2.FeatureByName


def _einheit(v) -> tuple[float, float, float]:
    n = laenge(v)
    return tuple(c / n for c in v)


def _geometrie(f: Flaeche) -> Messgeometrie:
    if f.art == "ebene":
        return Messgeometrie("ebene", f.punkt, f.normale)
    if f.art == "zylinder":
        return Messgeometrie("achse", f.punkt, _einheit(f.achse))
    raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, "Fläche ist weder eben noch zylindrisch")


def flaeche_der_instanz(kandidaten: list[Flaeche], richtung: str) -> Flaeche:
    """Ebene Fläche mit Normale `richtung`, die der Bohrungsposition am nächsten liegt (abstand von mit_abstand), z. B.
    der Senkungsgrund genau dieser Instanz."""
    vek = RICHTUNGEN[richtung]
    passend = sorted((f for f in kandidaten if f.art == "ebene" and f.normale and skalar(f.normale, vek) > _PARALLEL),
                     key=lambda f: f.abstand)
    if not passend:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine ebene Fläche mit Normale {richtung} an der Bohrung")
    if len(passend) > 1 and passend[1].abstand - passend[0].abstand < _GLEICH_MM:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{len(passend)} Flächen mit Normale {richtung} gleich nah an der Bohrung")
    return passend[0]


def _bohrung(ctx, fid: str, instanz: int):
    if fid not in ctx.ergebnisse:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Feature {fid!r} fehlt im Teil")
    ergebnis = ctx.ergebnis(fid)
    if instanz > len(ergebnis.punkte):
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Bohrung {fid} hat nur {len(ergebnis.punkte)} Instanzen")
    return ergebnis.features[0], ergebnis.punkte[instanz - 1]


def loese_im_teil(ctx, seite: dict) -> TeilReferenz:
    """seite ohne "komponente": {referenz} | {ebene} | {nahe} | {feature, instanz, achse} | {feature, instanz, flaeche} |
    {feature, flaeche}. ctx ist der Kontext des Teildokuments (Bau: Features des Laufs; Normteil: aus der Datei)."""
    if "referenz" in seite:
        if seite["referenz"] not in ctx.ergebnisse:
            raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Referenz {seite['referenz']!r} fehlt im Teil")
        feature = ctx.ergebnis(seite["referenz"]).features[0]
        return TeilReferenz(feature, Messgeometrie(*referenz_geometrie(feature)), True)
    if "ebene" in seite:
        feature = sw.standardebenen(ctx.model)[STANDARD[seite["ebene"]]]
        return TeilReferenz(feature, Messgeometrie("ebene", (0.0, 0.0, 0.0), NORMALE[seite["ebene"]]), True)
    if "nahe" in seite:
        f = loese_flaeche(ctx, {"nahe": seite["nahe"]})
        return TeilReferenz(f.objekt, _geometrie(f), False)
    if "instanz" in seite:
        feature, punkt = _bohrung(ctx, seite["feature"], seite["instanz"])
        if seite.get("achse"):
            [zylinder] = zylinder_zu_punkten(flaechen(feature), [punkt], ctx.tol_mm)
            return TeilReferenz(zylinder.objekt, _geometrie(zylinder), False)
        eben = mit_abstand([f for f in flaechen(feature) if f.art == "ebene"], punkt)
        f = flaeche_der_instanz(eben, seite["flaeche"])
        return TeilReferenz(f.objekt, _geometrie(f), False)
    if seite["feature"] not in ctx.ergebnisse:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Feature {seite['feature']!r} fehlt im Teil")
    f = loese_flaeche(ctx, {"feature": seite["feature"], "flaeche": seite["flaeche"]})
    return TeilReferenz(f.objekt, _geometrie(f), False)
```

- [ ] **Step 4: `swki/baugruppe/sw_baugruppe.py`**

```python
"""SolidWorks-Grundfunktionen für Baugruppen (Late Binding, Spike S12; Konstanten aus dem API-Index).

Nullargumentige Member ohne "()"; nullargumentige Aktionen (FixComponent, EditDelete, Done) über rufe(), das sie als
Methode markiert – so ist es egal, ob pywin32 sie beim Attributzugriff schon ausführen würde (S9a) oder nicht (S5)."""

import math
from pathlib import Path

from swki.baugruppe.fehler import KOMPONENTE_FEHLER, VERKNUEPFUNG_FEHLER
from swki.compiler import sw
from swki.compiler.anker import AnkerFehler
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, GLEICHUNG_FEHLER, REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.spec.ausdruck import auswerten, ist_ausdruck, sw_ausdruck
from swki.verbindung import byref_bool, byref_long, grad, in_mm, in_mm3, mm, r8_array

MATE_TYP = {"deckungsgleich": 0, "konzentrisch": 1, "senkrecht": 2, "parallel": 3, "abstand": 5, "winkel": 6}  # swMateType_e
AUSRICHTUNG = {"gleich": 0, "entgegengesetzt": 1}  # swMateAlign_e ALIGNED / ANTI_ALIGNED (Spike S12 Zeile 5)
SW_MATE_OK = 1  # swAddMateError_e.swAddMateError_NoError
MARKE = 1  # Auswahlmarke für AddMate5 (Spike S6/S12)
MASS_NAME = "D1"  # Maß einer Abstands-/Winkelverknüpfung (Spike S12 Zeile 8)
IDENTITAET = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
_TOL_LAGE = 1e-9


def ausrichtungen(v) -> list[int]:
    """Ausrichtungen, die nacheinander versucht werden: die angegebene; ohne Angabe (nur konzentrisch) gleich, dann
    entgegengesetzt (Präzisierung 9)."""
    if v.ausrichtung:
        return [AUSRICHTUNG[v.ausrichtung]]
    return [AUSRICHTUNG["gleich"], AUSRICHTUNG["entgegengesetzt"]]


def rufe(objekt, name: str):
    """Nullargumentige COM-Methode sicher aufrufen."""
    objekt._FlagAsMethod(name)
    return getattr(objekt, name)()


def neue_baugruppe(app, vorlage: Path):
    asm = app.NewDocument(str(vorlage), 0, 0, 0)
    if asm is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"NewDocument mit {vorlage} fehlgeschlagen", schritt="dokument")
    return asm


def fuege_ein(app, asm, pfad: Path, box_mm: list[float]):
    """Komponente mit Ursprung im Baugruppenursprung, ohne Drehung. AddComponent5 setzt das Zentrum der Bounding-Box
    (Spike S6) – deshalb das Boxzentrum übergeben; liegt der Ursprung trotzdem nicht im Nullpunkt, Identität setzen."""
    mitte = [mm((box_mm[i] + box_mm[i + 3]) / 2) for i in range(3)]
    komp = asm.AddComponent5(str(pfad), 0, "", False, "", *mitte)
    if komp is None:
        raise BauFehler(KOMPONENTE_FEHLER, f"AddComponent5 {pfad.name} fehlgeschlagen", schritt="einfuegen")
    t = komp.Transform2.ArrayData
    if any(abs(t[i] - IDENTITAET[i]) > _TOL_LAGE for i in range(12)):
        komp.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(IDENTITAET)))
    return komp


def fixiere(asm, komp) -> None:
    sw.auswahl_leeren(asm)
    if not komp.Select4(False, asm.SelectionManager.CreateSelectData, False):
        raise BauFehler(KOMPONENTE_FEHLER, f"{komp.Name2}: Auswahl zum Fixieren fehlgeschlagen", schritt="fixieren")
    rufe(asm, "FixComponent")
    sw.auswahl_leeren(asm)
    if not komp.IsFixed:
        raise BauFehler(KOMPONENTE_FEHLER, f"{komp.Name2} ließ sich nicht fixieren", schritt="fixieren")


def in_baugruppe(komp, ref) -> tuple[object, bool]:
    """Entität im Baugruppenkontext: Bezugs-/Standardgeometrie über IComponent2.FeatureByName, Flächen über
    GetCorrespondingEntity (Spike S12 Zeile 3)."""
    objekt = komp.FeatureByName(ref.objekt.Name) if ref.ist_feature else komp.GetCorrespondingEntity(ref.objekt)
    if objekt is None:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"{komp.Name2}: Referenz im Baugruppenkontext nicht gefunden")
    return objekt, ref.ist_feature


def waehle(asm, entitaet: tuple[object, bool], anhaengen: bool) -> None:
    objekt, ist_feature = entitaet
    if ist_feature:
        ok = objekt.Select2(anhaengen, MARKE)
    else:
        daten = asm.SelectionManager.CreateSelectData
        daten.Mark = MARKE
        ok = objekt.Select4(anhaengen, daten)
    if not ok:
        raise BauFehler(VERKNUEPFUNG_FEHLER, "Auswahl für die Verknüpfung fehlgeschlagen", schritt="auswahl")


def verknuepfungen(asm) -> list:
    """Verknüpfungs-Features (Unterfeatures des Ordners vom Typ MateGroup) in Baumreihenfolge."""
    f = asm.FirstFeature
    while f is not None and f.GetTypeName2 != "MateGroup":
        f = f.GetNextFeature
    ergebnis, unter = [], (f.GetFirstSubFeature if f is not None else None)
    while unter is not None:
        ergebnis.append(unter)
        unter = unter.GetNextSubFeature
    return ergebnis


def fehlercode(feature) -> int:
    return int(feature.GetErrorCode2(byref_bool()))


def _loesche(asm, feature) -> None:
    sw.auswahl_leeren(asm)
    feature.Select2(False, 0)
    rufe(asm, "EditDelete")
    sw.auswahl_leeren(asm)


def verknuepfe(asm, v, a: tuple[object, bool], b: tuple[object, bool], parameter: dict):
    """Verknüpfung v anlegen (AddMate5), als v.id benennen, neu aufbauen, Wert ggf. per Gleichung an die Parameter
    binden. Eine gescheiterte Verknüpfung wird wieder gelöscht; ohne ausrichtung folgt der zweite Versuch."""
    wert = auswerten(v.wert, parameter) if v.wert is not None else 0.0
    abstand = mm(wert) if v.typ == "abstand" else 0.0
    winkel = grad(wert) if v.typ == "winkel" else 0.0
    letzter = None
    for code in ausrichtungen(v):
        vorher = len(verknuepfungen(asm))
        sw.auswahl_leeren(asm)
        waehle(asm, a, False)
        waehle(asm, b, True)
        status = byref_long()
        mate = asm.AddMate5(MATE_TYP[v.typ], code, False, abstand, abstand, abstand, 1, 1, winkel, winkel, winkel,
                            False, v.drehung_sperren, 0, status)
        sw.auswahl_leeren(asm)
        alle = verknuepfungen(asm)
        neu = alle[-1] if mate is not None and len(alle) > vorher else None
        try:
            if neu is None or status.value != SW_MATE_OK:
                raise BauFehler(VERKNUEPFUNG_FEHLER, f"AddMate5 meldet Status {status.value}", schritt="verknuepfung")
            neu.Name = v.id
            sw.rebuild(asm)
            if fc := fehlercode(neu):
                raise BauFehler(VERKNUEPFUNG_FEHLER, f"Fehlercode {fc}", schritt="verknuepfung")
            if ist_ausdruck(v.wert):
                if asm.GetEquationMgr.Add2(-1, f'"{MASS_NAME}@{v.id}" = {sw_ausdruck(v.wert)}', True) < 0:
                    raise BauFehler(GLEICHUNG_FEHLER, f"Gleichung für {v.id} = {v.wert} abgelehnt", schritt="gleichung")
                sw.rebuild(asm)
            return neu
        except BauFehler as e:
            letzter = e
            if neu is not None:
                _loesche(asm, neu)
    raise BauFehler(VERKNUEPFUNG_FEHLER, f"{v.id} ({v.typ}): {letzter}", schritt="verknuepfung")


def komponenten(asm) -> list:
    return list(asm.GetComponents(True) or ())


def transform(komp) -> list[float]:
    return list(komp.Transform2.ArrayData)


def status(komp) -> int:
    return int(komp.GetConstrainedStatus)


def ist_fixiert(komp) -> bool:
    return bool(komp.IsFixed)


def interferenzen(asm) -> list[tuple[list[str], float]]:
    """Überlappungen als ([Name2 der Komponenten], Volumen in mm³); Berührung zählt nicht (Spec 3b §9.3)."""
    idm = asm.InterferenceDetectionManager
    try:
        idm.TreatCoincidenceAsInterference = False
        return [([k.Name2 for k in (i.Components or ())], in_mm3(i.Volume)) for i in (idm.GetInterferences or ())]
    finally:
        rufe(idm, "Done")


def huellquader(asm) -> list[float]:
    """[xmin, ymin, zmin, xmax, ymax, zmax] in mm (IAssemblyDoc.GetBox, ohne Bezugsgeometrie)."""
    return [in_mm(x) for x in asm.GetBox(0)]


def masse_kg(asm) -> float:
    mp = asm.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return float(mp.Mass)


def aufloesen(asm) -> None:
    """Leichtgewichtige Komponenten auflösen (nach OpenDoc6), damit Kollision und Geometrie vollständig sind."""
    asm.ResolveAllLightWeightComponents(False)


def verknuepfungswerte(asm) -> dict[str, float]:
    """Wert jeder Abstands- (mm) und Winkelverknüpfung (Grad) nach Feature-Namen."""
    werte = {}
    for f in verknuepfungen(asm):
        typ = f.GetSpecificFeature2.Type
        if typ in (MATE_TYP["abstand"], MATE_TYP["winkel"]) and (mass := f.Parameter(MASS_NAME)) is not None:
            werte[f.Name] = in_mm(mass.SystemValue) if typ == MATE_TYP["abstand"] else math.degrees(mass.SystemValue)
    return werte
```

Hinweis zu `fixiere`: `IComponent2.Select4` erwartet `SelectData`; ein rohes `None` löst „Typenkonflikt“ aus (Spike S5). `CreateSelectData` ist ein nullargumentiger Member (ohne `()`).

- [ ] **Step 5: Tests und Code-Prüfung**

Run: `.venv\Scripts\python.exe -m pytest -q` → **534 passed** (525 + 9: sechs Einzeltests, `test_ausrichtungen` × 3).
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.

- [ ] **Step 6: Commit**

```powershell
git add swki/baugruppe/referenzen.py swki/baugruppe/sw_baugruppe.py tests/baugruppe/test_referenzen.py
git commit -m "baugruppe: Referenzen im Teil auflösen, SolidWorks-Helfer für Baugruppen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Bau der Baugruppe (`swki bauen`) mit Live-Minimaltests

**Files:**
- Create: `swki/baugruppe/bau.py`
- Create: `tests/baugruppe/test_bau_baugruppe.py`, `tests/live/test_live_baugruppe.py`

**Interfaces:**
- Consumes: Task 2–7 (`lade_baugruppe`, `pruefe_freigabe_baugruppe`, `instanzen`, `verknuepfungen`, `basis`, `dokument_name`, `loese_im_teil`, `sw_baugruppe`), Task 5 (`baue_teil_dokument`, `pruefe_unveraendert`, `pruefsummen`, Protokollfelder), `swki.normteile.befehle.hole`, `swki.normteile.bibliothek.bibliotheksordner`/`lies_eintrag`, `swki.pruefung.messen.oeffne`/`kontext_aus_datei`, `swki.compiler.bauen.BauAbbruch`.
- Produces: `bauen(spec_pfad, lauf=None, verwerfen=False) -> dict` (Ergebnis wie beim Teil plus `"art": "baugruppe"`; wirft `BauAbbruch`). Protokoll: `teile[datei]` (Protokoll des Teil-Baus inkl. `knoten[].punkte`), `normteile[schluessel]`, `komponenten` ([{"id", "sw_name", "datei"}]), Knoten je Komponente (`typ: komponente`) und je Verknüpfung, `sha256` aller Dateien, `dateien` (`teil:<datei>`, `normteil:<schluessel>`, `baugruppe`).

- [ ] **Step 1: Failing tests – `tests/baugruppe/test_bau_baugruppe.py` (neu)**

```python
import json
from dataclasses import replace
from pathlib import Path

import pytest

from swki.auftrag import lauf_datei, lauf_ordner
from swki.baugruppe import bau
from swki.baugruppe.freigabe import freigeben_baugruppe
from swki.baugruppe.laden import lade_baugruppe
from swki.cli import SwkiFehler, main
from swki.konfig import Rechner
from tests.baugruppe.beispiel import schreibe


class _KeinSolidWorks(Exception):
    pass


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), Path("C:/b.asmdot"), None, tmp_path / "arbeit")
    pfad = schreibe(tmp_path / "A")
    aufrufe = {"verbinde": 0}

    def verbinde(jahr):
        aufrufe["verbinde"] += 1
        raise _KeinSolidWorks

    monkeypatch.setattr(bau, "lade_rechner", lambda: r)
    monkeypatch.setattr(bau, "verbinde", verbinde)
    return r, pfad, aufrufe


def test_ohne_freigabe(umgebung):
    _, pfad, aufrufe = umgebung
    with pytest.raises(SwkiFehler) as e:
        bau.bauen(pfad)
    assert e.value.daten["code"] == "FREIGABE_FEHLT" and aufrufe["verbinde"] == 0


def test_ohne_baugruppenvorlage(umgebung, monkeypatch):
    r, pfad, aufrufe = umgebung
    freigeben_baugruppe(lade_baugruppe(pfad))
    monkeypatch.setattr(bau, "lade_rechner", lambda: replace(r, vorlage_baugruppe=None))
    with pytest.raises(SwkiFehler, match="vorlage_baugruppe"):
        bau.bauen(pfad)
    assert aufrufe["verbinde"] == 0


def test_manuelle_aenderung_vor_solidworks(umgebung):
    r, pfad, aufrufe = umgebung
    freigeben_baugruppe(lade_baugruppe(pfad))
    ordner = lauf_ordner(r, "A", 1)
    ordner.mkdir(parents=True)
    (ordner / "A_Probe.sldasm").write_bytes(b"gebaut")
    from swki.aenderungen import pruefsummen

    protokoll = lauf_datei(pfad, 1, "protokoll")
    protokoll.parent.mkdir(parents=True, exist_ok=True)
    protokoll.write_text(json.dumps({"status": "ok", "sha256": pruefsummen(ordner, [ordner / "A_Probe.sldasm"])}),
                         encoding="utf-8")
    (ordner / "A_Probe.sldasm").write_bytes(b"geaendert")
    with pytest.raises(SwkiFehler) as e:
        bau.bauen(pfad)
    assert e.value.daten["code"] == "MANUELL_GEAENDERT" and aufrufe["verbinde"] == 0
    with pytest.raises(_KeinSolidWorks):
        bau.bauen(pfad, verwerfen=True)


def test_weiche_in_swki_bauen(capsys, umgebung, monkeypatch):
    _, pfad, _ = umgebung
    monkeypatch.setattr(bau, "bauen", lambda p, lauf, verwerfen: {"art": "baugruppe", "lauf": lauf, "verwerfen": verwerfen})
    assert main(["bauen", str(pfad), "--lauf", "3", "--verwerfen"]) == 0
    assert json.loads(capsys.readouterr().out) == {"art": "baugruppe", "lauf": 3, "verwerfen": True}
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bau_baugruppe.py -q`
Expected: FAIL (ModuleNotFoundError `swki.baugruppe.bau`).

- [ ] **Step 3: `swki/baugruppe/bau.py`**

```python
"""swki bauen für Baugruppen (Spec 3b §7): Eigenteile frisch bauen und speichern, Normteile holen und in den Lauf
kopieren, Komponenten einfügen (Ursprung auf Ursprung, die fixierte zuerst), Verknüpfungen setzen, speichern,
protokollieren. Der Lauf-Ordner ist in sich geschlossen; die Bibliothek wird nur gelesen."""

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from swki.aenderungen import pruefe_unveraendert, pruefsummen
from swki.auftrag import auftrag_name, dateiname, lauf_belegt, lauf_datei, lauf_ordner, naechster_lauf
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import Instanz, Verknuepfung, basis, instanzen, verknuepfungen
from swki.baugruppe.fehler import TEIL_BAU
from swki.baugruppe.freigabe import pruefe_freigabe_baugruppe
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.modell import Baugruppe, dokument_name
from swki.baugruppe.referenzen import loese_im_teil
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.bauen import BauAbbruch, baue_teil_dokument
from swki.compiler.eigenschaften import eigenschaften_fuer, globale_variablen, setze_eigenschaften
from swki.compiler.fehler import BauFehler, fehler_dict
from swki.compiler.protokoll import Protokoll
from swki.konfig import lade_rechner, lade_standard
from swki.normteile import befehle as normteil_befehle
from swki.normteile.bibliothek import bibliotheksordner, lies_eintrag
from swki.normteile.fehler import NormteilFehler
from swki.pruefung.messen import kontext_aus_datei, oeffne
from swki.verbindung import verbinde


@dataclass
class Baulauf:
    app: object
    bg: Baugruppe
    auftrag: str
    ordner: Path
    standard: dict
    protokoll: Protokoll
    asm: object = None
    kontexte: dict = field(default_factory=dict)     # Quelldokument (Teil-Spec bzw. Normteil-Schlüssel) → Kontext
    offen: list = field(default_factory=list)        # selbst geöffnete Teildokumente, am Ende schließen
    dateien: dict = field(default_factory=dict)      # "teil:<datei>" | "normteil:<schluessel>" | "baugruppe" → Pfad
    komponenten: dict = field(default_factory=dict)  # Instanz-ID → IComponent2


def _baue_teile(b: Baulauf, r) -> Exception | None:
    for datei, teil_spec in b.bg.teile.items():
        tp = Protokoll(b.auftrag, datei, b.protokoll.lauf, r.sw_jahr)
        model, ctx, fehler = baue_teil_dokument(b.app, r, b.standard, teil_spec, b.bg.pfad.parent / datei, b.auftrag, tp)
        b.offen.append(model)
        b.kontexte[datei] = ctx
        ziel = b.ordner / dokument_name(b.bg.quellen[b.bg.komponente_von(datei)], b.auftrag, b.standard)
        try:
            sw.speichere(model, ziel)  # auch nach einem Fehler: Teilstand zur Diagnose
            b.dateien[f"teil:{datei}"] = ziel
        except Exception as e:
            fehler = fehler or e
        tp.status = "fehler" if fehler else "ok"
        tp.fehler = fehler_dict(fehler) if fehler else None
        b.protokoll.teile[datei] = tp.als_dict()
        if fehler is not None:
            knoten = next((k.id for k in tp.knoten if k.status == "fehler"), "speichern")
            f = fehler_dict(fehler)
            return BauFehler(TEIL_BAU, f"{b.bg.komponente_von(datei)}/{knoten}: {f['code']} – {f['meldung']}", schritt="teil")
    return None


def _hole_normteile(b: Baulauf, r, tol_mm: float) -> Exception | None:
    erledigt = set()
    for kid, q in b.bg.quellen.items():
        if q.art != "normteil" or q.schluessel in erledigt:
            continue
        erledigt.add(q.schluessel)
        try:
            ergebnis = normteil_befehle.hole(q.norm, q.hole_groesse, q.variante)
        except NormteilFehler as e:
            return BauFehler(e.daten["code"], f"{kid}: {e}", schritt="normteil")
        ziel = b.ordner / dokument_name(q, b.auftrag, b.standard)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ergebnis["pfad"], ziel)
        eintrag = lies_eintrag(bibliotheksordner(r), q.schluessel) or {}
        b.protokoll.normteile[q.schluessel] = {"bibliothek": ergebnis["pfad"], "gebaut": ergebnis["gebaut"],
                                               "pruefsumme": eintrag.get("pruefsumme")}
        b.dateien[f"normteil:{q.schluessel}"] = ziel
        model = oeffne(b.app, ziel)
        b.offen.append(model)
        b.kontexte[q.schluessel] = kontext_aus_datei(b.app, model, q.spec, ziel.with_suffix(".yaml"), tol_mm, {"knoten": []})
    return None


def _fuege_ein(b: Baulauf, alle: list[Instanz]) -> Exception | None:
    fixiert = {k["id"] for k in b.bg.spec["komponenten"] if k.get("fixiert")}
    for i in sorted(alle, key=lambda x: x.komponente not in fixiert):  # stabil: die fixierte zuerst
        try:
            with b.protokoll.knoten_lauf(i.id, "komponente") as knoten:
                model = b.kontexte[b.bg.quellen[i.komponente].schluessel_dokument].model
                pfad = Path(model.GetPathName)
                komp = sw_baugruppe.fuege_ein(b.app, b.asm, pfad, sw.teilebox_mm(model))
                if i.komponente in fixiert:
                    sw_baugruppe.fixiere(b.asm, komp)
                knoten.sw_name = komp.Name2
                b.komponenten[i.id] = komp
                b.protokoll.komponenten.append({"id": i.id, "sw_name": komp.Name2, "datei": pfad.name})
        except Exception as e:
            return e
    return None


def _entitaet(b: Baulauf, seite: dict) -> tuple[object, bool]:
    ctx = b.kontexte[b.bg.quellen[basis(seite["komponente"])].schluessel_dokument]
    ref = loese_im_teil(ctx, {k: v for k, v in seite.items() if k != "komponente"})
    return sw_baugruppe.in_baugruppe(b.komponenten[seite["komponente"]], ref)


def _verknuepfe(b: Baulauf, alle: list[Verknuepfung]) -> Exception | None:
    fehler = None
    for v in alle:
        if fehler is not None:
            b.protokoll.uebersprungen(v.id, v.typ)
            continue
        try:
            with b.protokoll.knoten_lauf(v.id, v.typ) as knoten:
                feature = sw_baugruppe.verknuepfe(b.asm, v, _entitaet(b, v.a), _entitaet(b, v.b),
                                                  b.bg.spec.get("parameter", {}))
                knoten.sw_name = feature.Name
        except Exception as e:  # jeder Fehler (auch COM) beendet den Lauf und steht im Protokoll
            fehler = e
    return fehler


def bauen(spec_pfad: Path, lauf: int | None = None, verwerfen: bool = False) -> dict:
    spec_pfad = spec_pfad.resolve()
    bg = lade_baugruppe(spec_pfad)
    pruefe_freigabe_baugruppe(bg)
    r, standard = lade_rechner(), lade_standard()
    if r.vorlage_baugruppe is None:
        raise SwkiFehler("config/rechner.yaml: vorlage_baugruppe fehlt (swki rechner init)")
    auftrag = auftrag_name(spec_pfad)
    if lauf is not None and lauf_belegt(r, auftrag, spec_pfad, lauf):
        raise SwkiFehler(f"Lauf {lauf} von {auftrag} existiert schon – ohne --lauf baut swki den nächsten freien Lauf")
    verworfen = pruefe_unveraendert(r, auftrag, spec_pfad, verwerfen)
    if lauf is None:
        lauf = naechster_lauf(r, auftrag, spec_pfad)
    ordner = lauf_ordner(r, auftrag, lauf)
    protokoll = Protokoll(auftrag, spec_pfad.name, lauf, r.sw_jahr)
    protokoll.verworfen = verworfen
    alle_instanzen, alle_verknuepfungen = instanzen(bg.spec, bg.quellen), verknuepfungen(bg.spec, bg.quellen)
    beginn = time.perf_counter()
    b = Baulauf(verbinde(r.sw_jahr), bg, auftrag, ordner, standard, protokoll)
    fehler = None
    try:
        with protokoll.phase("teile"):
            fehler = _baue_teile(b, r)
        if fehler is None:
            with protokoll.phase("normteile"):
                fehler = _hole_normteile(b, r, standard["toleranzen"]["anker_mm"])
        if fehler is None:
            with protokoll.phase("einfuegen"):
                b.asm = sw_baugruppe.neue_baugruppe(b.app, r.vorlage_baugruppe)
                globale_variablen(b.asm, bg.spec.get("parameter", {}))
                setze_eigenschaften(b.asm, eigenschaften_fuer(bg.spec, auftrag))
                fehler = _fuege_ein(b, alle_instanzen)
        with protokoll.phase("verknuepfen"):
            if fehler is None:
                fehler = _verknuepfe(b, alle_verknuepfungen)
            else:
                for v in alle_verknuepfungen:
                    protokoll.uebersprungen(v.id, v.typ)
        if b.asm is not None:
            with protokoll.phase("speichern"):
                ziel = ordner / f"{dateiname(bg.spec, auftrag, standard)}.sldasm"
                try:
                    sw.speichere(b.asm, ziel)  # auch nach einem Fehler: Stand zur Diagnose
                    b.dateien["baugruppe"] = ziel
                except Exception as e:
                    fehler = fehler or e
    except Exception as e:  # z. B. Vorlage, Gleichungen oder Eigenschaften der Baugruppe
        fehler = fehler or e
    finally:
        if b.asm is not None:
            sw.schliesse(b.app, b.asm)
        for model in reversed(b.offen):
            sw.schliesse(b.app, model)
    protokoll.dateien = {art: str(p) for art, p in b.dateien.items()}
    protokoll.sha256 = pruefsummen(ordner, b.dateien.values())
    protokoll.status = "fehler" if fehler else "ok"
    protokoll.fehler = fehler_dict(fehler) if fehler else None
    protokoll.dauer_s = round(time.perf_counter() - beginn, 3)
    protokoll.schreibe(ordner / "protokoll.json")
    protokoll.schreibe(lauf_datei(spec_pfad, lauf, "protokoll"))
    ergebnis = {
        "status": protokoll.status, "art": "baugruppe", "auftrag": auftrag, "lauf": lauf, "ordner": str(ordner),
        "dateien": protokoll.dateien,
        "knoten": [{"id": k.id, "status": k.status, "sw_name": k.sw_name} for k in protokoll.knoten],
        "fehler": protokoll.fehler, "dauer_s": protokoll.dauer_s,
    }
    if fehler:
        raise BauAbbruch(ergebnis)
    return ergebnis
```

Hinweis: In `test_weiche_in_swki_bauen` wird `bau.bauen` ersetzt; die Weiche in `swki/compiler/bauen.py` (Task 5) importiert das Modul erst beim Aufruf und findet so die Attrappe.

- [ ] **Step 4: Unit-Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → **538 passed** (534 + 4).

- [ ] **Step 5: Live-Test `tests/live/test_live_baugruppe.py` (neu)**

```python
"""Live: Baugruppen bauen (Spec 3b §7) – Probe aus tests/baugruppe/beispiel.py, Werte-Verknüpfungen, Fehlerpfad."""

import json
import shutil

import pytest
import yaml

from swki.cli import main
from swki.konfig import lade_rechner
from tests.baugruppe.beispiel import BAUGRUPPE, kopie, schreibe

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-BAUGRUPPE"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def auftrag(tmp_path):
    yield tmp_path / AUFTRAG
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _baue(capsys, ordner, spec=None):
    pfad = schreibe(ordner, baugruppe=spec)
    assert _lauf(capsys, "validieren", str(pfad))[0] == 0
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    return pfad, *_lauf(capsys, "bauen", str(pfad))


def test_probe_baut(capsys, auftrag):
    pfad, code, bau = _baue(capsys, auftrag)
    assert code == 0, bau
    assert [k["id"] for k in bau["knoten"]] == ["platte", "deckel", "schraube.1", "schraube.2", "stift",
                                                "v1", "v2", "v3", "v4.1", "v4.2", "v5.1", "v5.2", "v6", "v7"]
    assert all(k["status"] == "ok" for k in bau["knoten"])
    protokoll = json.loads((pfad.parent / "protokolle" / "probe.lauf-1.protokoll.json").read_text(encoding="utf-8"))
    assert set(protokoll["sha256"]) == {f"{AUFTRAG}_Platte.sldprt", f"{AUFTRAG}_Deckel.sldprt", f"{AUFTRAG}_Probe.sldasm",
                                        "ISO4762_M8x16_8_8.sldprt", "ISO8734_8x16_St.sldprt"}
    assert set(protokoll["teile"]) == {"platte.yaml", "deckel.yaml"} and len(protokoll["komponenten"]) == 5


def test_werte_verknuepfungen(capsys, auftrag):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"] = spec["komponenten"][:2]
    spec["parameter"] = {"S": 5, "W": 30}
    spec["freiheitsgrade"] = {"deckel": "unterbestimmt"}
    spec["pruefung"] = {}
    spec["verknuepfungen"] = [
        {"id": "w1", "typ": "abstand", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "-y"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt", "wert": "=S"},
        {"id": "w2", "typ": "winkel", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "+x"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+x"}, "ausrichtung": "gleich", "wert": "=W"},
    ]
    _, code, bau = _baue(capsys, auftrag, spec)
    assert code == 0, bau
    assert [k["status"] for k in bau["knoten"]] == ["ok"] * 4


def test_senkrecht(capsys, auftrag):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"] = spec["komponenten"][:2]
    spec["freiheitsgrade"] = {"deckel": "unterbestimmt"}
    spec["pruefung"] = {}
    spec["verknuepfungen"] = [
        {"id": "s1", "typ": "senkrecht", "a": {"komponente": "deckel", "feature": "f1", "flaeche": "+x"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+y"}}]
    _, code, bau = _baue(capsys, auftrag, spec)
    assert code == 0, bau


def test_fehlende_referenz_bricht_ab(capsys, auftrag):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][3]["b"]["flaeche"] = "-y"   # die Senkung hat keine Fläche −y
    pfad, code, bau = _baue(capsys, auftrag, spec)
    assert code == 1 and bau["fehler"]["code"] == "REFERENZ_NICHT_GEFUNDEN", bau
    status = {k["id"]: k["status"] for k in bau["knoten"]}
    assert status["v4.1"] == "fehler" and status["v7"] == "uebersprungen"
    assert bau["dateien"]["baugruppe"].endswith(".sldasm")  # Stand zur Diagnose gespeichert
```

- [ ] **Step 6: Live**

Vorbedingungen (eine Instanz, `False 1`, Private Bytes). Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_baugruppe.py --zeit 300` → 4/4 OK. Scheitert eine Ausrichtung (Spike-Zeile 5): Controller fragen, nicht die Testerwartung ändern. Private Bytes vorher/nachher; ab ca. 4 GB anhalten und melden.

- [ ] **Step 7: Commit**

```powershell
git add swki/baugruppe/bau.py tests/baugruppe/test_bau_baugruppe.py tests/live/test_live_baugruppe.py
git commit -m "baugruppe: swki bauen – Teile, Normteile, Komponenten, Verknüpfungen, Protokoll" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Bewertung der Baugruppe (ohne SolidWorks)

**Files:**
- Create: `swki/baugruppe/geometrie.py`, `swki/baugruppe/bewertung.py`
- Create: `tests/baugruppe/test_geometrie_baugruppe.py`, `tests/baugruppe/test_bewertung_baugruppe.py`

**Interfaces:**
- Consumes: Task 2 (`instanzen`, `verknuepfungen`, `basis`, `dokument_name`), `swki.pruefung.bewertung` (`_pruefung`, `_beschreibung`, `messpunkt_schluessel`), `swki.pruefung.geometrie` (`Messgeometrie`, `abstand`, `NichtMessbar`), `swki.spec.normen` (`normmasse`, `norm_von`); Spike-Zeilen 9 und 12.
- Produces:
  - `transformiere(g: Messgeometrie, t) -> Messgeometrie`, `einschraublaenge(l, kopfauflage, eintritt) -> float`, `ueberlappung_soll(d, p, kernloch, einschraub) -> float`
  - `BaugruppenMesswerte(rebuild_fehler, verknuepfungen, komponenten, stueckliste, interferenzen, box, masse_kg, eigenschaften={}, messpunkte={}, schrauben={}, gewindebohrungen=[], teilberichte={})`
  - `Gewindepaarung(schraube, teil, feature, instanz, kopfauflage, eintritt)`, `gewindepaarungen(schrauben, bohrungen, tol_mm) -> list[Gewindepaarung]`, `stueckliste_soll(spec, quellen, auftrag, standard) -> dict[str, int]`, `bewerte_baugruppe(spec, quellen, m, standard, soll_stueckliste) -> dict` (`bestanden`, `pruefungen`, `maengel`, `stueckliste`, `gewindepaarungen`, `teilpruefungen`, `masse_kg`)

Messwert-Formate (`swki.baugruppe.pruefen` füllt sie in Task 10): `verknuepfungen` {Feature-Name: Fehlercode}; `komponenten` {Instanz-ID: {"status": int, "fixiert": bool}}; `stueckliste` {Dateiname: Anzahl}; `interferenzen` [{"paar": [Instanz-ID, Instanz-ID], "volumen": mm³}]; `box` [xmin, ymin, zmin, xmax, ymax, zmax] mm; `messpunkte` {messpunkt_schluessel(Messpunkt der Baugruppe): Messgeometrie in Baugruppenkoordinaten oder Fehlertext}; `schrauben` {Instanz-ID einer ISO-4762-Komponente: EINBAU_EBENE in Baugruppenkoordinaten oder Fehlertext}; `gewindebohrungen` [{"teil": Instanz-ID, "feature", "instanz", "eintritt": Messgeometrie("punkt") in Baugruppenkoordinaten}]; `teilberichte` {Dateiname der Teil-Spec: Ergebnis von `swki.pruefung.bewertung.bewerte`}.

- [ ] **Step 1: Failing tests – `tests/baugruppe/test_geometrie_baugruppe.py` (neu)**

```python
import math

import pytest

from swki.baugruppe.geometrie import einschraublaenge, transformiere, ueberlappung_soll
from swki.pruefung.geometrie import Messgeometrie

IDENT = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]


def _numerisch(d, p, kernloch, laenge, schritte=200000):
    """Mittelpunktsumme über den Schaft hinter dem Eintritt; s = Abstand von der Spitze."""
    rn, rk, h = d / 2, kernloch / 2, laenge / schritte
    summe = 0.0
    for k in range(schritte):
        s = (k + 0.5) * h
        r = rn - p + s if s < p else rn
        summe += math.pi * max(r * r - rk * rk, 0.0) * h
    return summe


def test_transform_identitaet():
    g = transformiere(Messgeometrie("ebene", (1.0, 2.0, 3.0), (0.0, 1.0, 0.0)), IDENT)
    assert (g.art, g.punkt, g.richtung) == ("ebene", (1.0, 2.0, 3.0), (0.0, 1.0, 0.0))


def test_transform_verschiebung():
    t = IDENT[:9] + [0.01, 0.02, 0.03] + IDENT[12:]
    g = transformiere(Messgeometrie("achse", (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)), t)
    assert g.punkt == pytest.approx((11.0, 20.0, 30.0)) and g.richtung == (0.0, 0.0, 1.0)


def test_transform_drehung_um_y():
    # +90° um Y: Bild der x-Achse = (0, 0, −1), Bild der z-Achse = (1, 0, 0) (Zeilen 0 und 2)
    t = [0.0, 0.0, -1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    g = transformiere(Messgeometrie("achse", (1.0, 0.0, 0.0), (0.0, 0.0, 2.0)), t)
    assert g.punkt == pytest.approx((0.0, 0.0, -1.0)) and g.richtung == pytest.approx((1.0, 0.0, 0.0))


def test_einschraublaenge():
    kopf = Messgeometrie("ebene", (-30.0, 26.4, 0.0), (0.0, 1.0, 0.0))
    assert einschraublaenge(16.0, kopf, Messgeometrie("punkt", (-30.0, 20.0, 0.0))) == pytest.approx(9.6)


def test_ueberlappung_gegen_numerik():
    assert ueberlappung_soll(8, 1.25, 6.8, 13.6) == pytest.approx(_numerisch(8, 1.25, 6.8, 13.6), rel=1e-6)


def test_ueberlappung_nur_fase():
    assert ueberlappung_soll(8, 1.25, 6.8, 0.9) == pytest.approx(_numerisch(8, 1.25, 6.8, 0.9), rel=1e-6)


def test_ueberlappung_ohne_eingriff():
    assert ueberlappung_soll(8, 1.25, 6.8, 0.0) == 0.0 and ueberlappung_soll(8, 1.25, 6.8, -2.0) == 0.0
```

- [ ] **Step 2: Failing tests – `tests/baugruppe/test_bewertung_baugruppe.py` (neu)**

```python
import pytest

from swki.baugruppe.aufloesen import verknuepfungen
from swki.baugruppe.bewertung import BaugruppenMesswerte, bewerte_baugruppe, gewindepaarungen, stueckliste_soll
from swki.baugruppe.geometrie import ueberlappung_soll
from swki.baugruppe.laden import lade_baugruppe
from swki.pruefung.bewertung import messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from tests.baugruppe.beispiel import schreibe

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}, "namensschema": {"datei": "{auftrag}_{name}"}}
SOLL_GEWINDE = ueberlappung_soll(8, 1.25, 6.8, 9.6)
Y = (0.0, 1.0, 0.0)


@pytest.fixture
def bg(tmp_path):
    return lade_baugruppe(schreibe(tmp_path / "A"))


def _messwerte(bg, **aenderungen) -> BaugruppenMesswerte:
    mp = bg.spec["pruefung"]["masse_pruefen"][0]
    werte = dict(
        rebuild_fehler=[],
        verknuepfungen={v.id: 0 for v in verknuepfungen(bg.spec, bg.quellen)},
        komponenten={i: {"status": 3, "fixiert": i == "platte"}
                     for i in ("platte", "deckel", "schraube.1", "schraube.2", "stift")},
        stueckliste=stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD),
        interferenzen=[{"paar": ["platte", "schraube.1"], "volumen": SOLL_GEWINDE},
                       {"paar": ["platte", "schraube.2"], "volumen": SOLL_GEWINDE}],
        box=[-50.0, 0.0, -30.0, 50.0, 35.0, 30.0], masse_kg=1.2, eigenschaften={"Benennung": "Probe"},
        messpunkte={messpunkt_schluessel(mp["von"]): Messgeometrie("ebene", (0.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
                    messpunkt_schluessel(mp["zu"]): Messgeometrie("ebene", (0.0, 35.0, 0.0), Y)},
        schrauben={"schraube.1": Messgeometrie("ebene", (-30.0, 26.4, 0.0), Y),
                   "schraube.2": Messgeometrie("ebene", (30.0, 26.4, 0.0), Y)},
        gewindebohrungen=[
            {"teil": "platte", "feature": "f2", "instanz": 1, "eintritt": Messgeometrie("punkt", (-30.0, 20.0, 0.0))},
            {"teil": "platte", "feature": "f2", "instanz": 2, "eintritt": Messgeometrie("punkt", (30.0, 20.0, 0.0))}],
        teilberichte={d: {"bestanden": True, "pruefungen": [{"id": "rebuild", "ok": True, "knoten": []}], "maengel": []}
                      for d in ("platte.yaml", "deckel.yaml")},
    )
    werte.update(aenderungen)
    return BaugruppenMesswerte(**werte)


def _bewerte(bg, m) -> dict:
    return bewerte_baugruppe(bg.spec, bg.quellen, m, STANDARD, stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD))


def _maengel(bericht) -> dict:
    return {m["pruefung"]: m for m in bericht["maengel"]}


def test_alles_ok(bg):
    bericht = _bewerte(bg, _messwerte(bg))
    assert bericht["bestanden"], bericht["maengel"]
    assert [g["einschraublaenge"] for g in bericht["gewindepaarungen"]] == [9.6, 9.6]
    assert bericht["teilpruefungen"] == {"platte": {"bestanden": True, "maengel": 0},
                                         "deckel": {"bestanden": True, "maengel": 0}}
    ids = {p["id"] for p in bericht["pruefungen"]}
    assert {"rebuild", "verknuepfungen", "bestimmtheit", "stueckliste", "kollision", "gewinde:schraube.1",
            "mass:Gesamthöhe", "eigenschaften", "platte: rebuild"} <= ids


def test_fehlende_verknuepfung(bg):
    m = _messwerte(bg)
    del m.verknuepfungen["v5.2"]
    assert _maengel(_bewerte(bg, m))["verknuepfungen"]["knoten"] == ["v5.2"]


def test_unterbestimmt_ist_mangel(bg):
    m = _messwerte(bg)
    m.komponenten["deckel"]["status"] = 2
    mangel = _maengel(_bewerte(bg, m))["bestimmtheit"]
    assert mangel["knoten"] == ["deckel"] and "unterbestimmt" in mangel["beschreibung"]


def test_unterbestimmt_erlaubt(bg):
    bg.spec["freiheitsgrade"] = {"deckel": "unterbestimmt"}
    m = _messwerte(bg)
    m.komponenten["deckel"]["status"] = 2
    assert _bewerte(bg, m)["bestanden"]


def test_ueberbestimmt(bg):
    m = _messwerte(bg)
    m.komponenten["stift"]["status"] = 4
    assert "überbestimmt" in _maengel(_bewerte(bg, m))["bestimmtheit"]["beschreibung"]


def test_fixierte_komponente_nicht_fixiert(bg):
    m = _messwerte(bg)
    m.komponenten["platte"]["fixiert"] = False
    assert "nicht fixiert" in _maengel(_bewerte(bg, m))["bestimmtheit"]["beschreibung"]


def test_stueckliste(bg):
    m = _messwerte(bg)
    m.stueckliste["ISO4762_M8x16_8_8.sldprt"] = 1
    assert "stueckliste" in _maengel(_bewerte(bg, m))


def test_fremde_kollision(bg):
    m = _messwerte(bg)
    m.interferenzen.append({"paar": ["deckel", "stift"], "volumen": 5.0})
    maengel = _maengel(_bewerte(bg, m))
    assert maengel["kollision"]["knoten"] == ["deckel", "stift"]
    assert not any(p.startswith("gewinde:") for p in maengel)


def test_gewinde_zu_lang(bg):
    m = _messwerte(bg)
    m.gewindebohrungen[0]["eintritt"] = Messgeometrie("punkt", (-30.0, 24.4, 0.0))   # Einschraublänge 14 > 12
    m.interferenzen[0]["volumen"] = ueberlappung_soll(8, 1.25, 6.8, 14.0)
    mangel = _maengel(_bewerte(bg, m))["gewinde:schraube.1"]
    assert "Einschraublänge 14.00" in mangel["beschreibung"] and mangel["knoten"] == ["schraube.1", "platte"]


def test_gewinde_volumen_falsch(bg):
    m = _messwerte(bg)
    m.interferenzen[1]["volumen"] = SOLL_GEWINDE * 1.05
    assert "gewinde:schraube.2" in _maengel(_bewerte(bg, m))


def test_teilbericht_mit_praefix(bg):
    m = _messwerte(bg)
    m.teilberichte["platte.yaml"] = {"bestanden": False, "maengel": [{}], "pruefungen": [
        {"id": "mass:A", "ok": False, "ist": 59.0, "soll": 60.0, "knoten": ["f2"]}]}
    mangel = _maengel(_bewerte(bg, m))["platte: mass:A"]
    assert mangel["knoten"] == ["platte/f2"] and "ist 59.0 statt 60.0" in mangel["beschreibung"]


def test_mass_ausserhalb_toleranz(bg):
    mp = bg.spec["pruefung"]["masse_pruefen"][0]
    m = _messwerte(bg)
    m.messpunkte[messpunkt_schluessel(mp["zu"])] = Messgeometrie("ebene", (0.0, 35.5, 0.0), Y)
    assert _maengel(_bewerte(bg, m))["mass:Gesamthöhe"]["knoten"] == ["deckel", "platte"]


def test_gewindepaarung_ueber_die_lage():
    schrauben = {"s.1": Messgeometrie("ebene", (0.0, 30.0, 0.0), Y)}
    bohrungen = [{"teil": "t", "feature": "f2", "instanz": 1, "eintritt": Messgeometrie("punkt", (0.05, 20.0, 0.0))},
                 {"teil": "t", "feature": "f2", "instanz": 2, "eintritt": Messgeometrie("punkt", (1.0, 20.0, 0.0))}]
    assert [(g.schraube, g.instanz) for g in gewindepaarungen(schrauben, bohrungen, 0.1)] == [("s.1", 1)]


def test_stueckliste_soll(bg):
    assert stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD) == {
        "A_Platte.sldprt": 1, "A_Deckel.sldprt": 1, "ISO4762_M8x16_8_8.sldprt": 2, "ISO8734_8x16_St.sldprt": 1}
```

- [ ] **Step 3: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_geometrie_baugruppe.py tests/baugruppe/test_bewertung_baugruppe.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 4: `swki/baugruppe/geometrie.py`**

```python
"""Geometrie der Baugruppenprüfung (ohne SolidWorks): Teil- → Baugruppenkoordinaten, Einschraublänge, Soll-Überlappung
einer Gewindepaarung. Längen in mm."""

import math

from swki.compiler.anker import differenz, laenge, skalar
from swki.pruefung.geometrie import Messgeometrie
from swki.verbindung import in_mm


def transformiere(g: Messgeometrie, t) -> Messgeometrie:
    """Teil- → Baugruppenkoordinaten mit IComponent2.Transform2.ArrayData: [0:9] Drehung (Zeile i = Bild der Achse i,
    Zeilenvektor-Konvention wie die Ebenennormale ArrayData[6:9] in Spike S11), [9:12] Verschiebung in m, [12] Maßstab
    (Spike S12 Zeile 12)."""
    skala = t[12] if len(t) > 12 and t[12] else 1.0

    def dreh(v):
        return tuple(v[0] * t[i] + v[1] * t[3 + i] + v[2] * t[6 + i] for i in range(3))

    p = dreh(g.punkt)
    punkt = tuple(skala * p[i] + in_mm(t[9 + i]) for i in range(3))
    richtung = None
    if g.richtung is not None:
        r = dreh(g.richtung)
        n = laenge(r)
        richtung = tuple(c / n for c in r)
    return Messgeometrie(g.art, punkt, richtung)


def einschraublaenge(laenge_schraube: float, kopfauflage: Messgeometrie, eintritt: Messgeometrie) -> float:
    """Schaftlänge hinter dem Eintrittspunkt der Gewindebohrung: l − Abstand Kopfauflage–Eintritt entlang der Achse."""
    return laenge_schraube - abs(skalar(differenz(eintritt.punkt, kopfauflage.punkt), kopfauflage.richtung))


def ueberlappung_soll(d: float, p: float, kernloch: float, einschraub: float) -> float:
    """Soll-Überlappung Schraube (Nenn-Ø d, Endfase p × 45°) ↔ Kernloch (mm³): Ring Nenn-Ø/Kernloch-Ø über die
    Einschraublänge; im Fasenbereich nur der Teil, der über das Kernloch ragt."""
    if einschraub <= 0:
        return 0.0
    rn, rk = d / 2, kernloch / 2
    a = rn - p  # Radius an der Spitze
    v = 0.0
    s_von, s_bis = max(rk - a, 0.0), min(p, einschraub)  # s: Abstand von der Spitze innerhalb der Fase
    if s_bis > s_von:
        v += math.pi * (((a + s_bis) ** 3 - (a + s_von) ** 3) / 3 - rk ** 2 * (s_bis - s_von))
    if einschraub > p:
        v += math.pi * (rn ** 2 - rk ** 2) * (einschraub - p)
    return v
```

- [ ] **Step 5: `swki/baugruppe/bewertung.py`**

```python
"""Bewertung einer Baugruppe (Spec 3b §9) ohne SolidWorks: Messwerte → Prüfungen und Mängel mit Knoten-IDs
(Instanz-, Verknüpfungs- oder Teil-Knoten wie "deckelschraube.2", "v11.1", "deckel/f4")."""

from dataclasses import dataclass, field

from swki.baugruppe.aufloesen import basis, instanzen, verknuepfungen
from swki.baugruppe.geometrie import einschraublaenge, ueberlappung_soll
from swki.baugruppe.modell import Quelle, dokument_name
from swki.compiler.anker import punkt_achse_abstand
from swki.pruefung.bewertung import _beschreibung, _pruefung, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand
from swki.spec.ausdruck import auswerten
from swki.spec.normen import norm_von, normmasse

STATUS_TEXT = {1: "unbekannt", 2: "unterbestimmt", 3: "voll bestimmt", 4: "überbestimmt", 5: "keine Lösung",
               6: "ungültige Lösung", 7: "Lösen ausgeschaltet"}  # swConstrainedStatus_e
VOLL_BESTIMMT, UNTERBESTIMMT = 3, 2
TOL_GEWINDE_PROZENT = 1.0  # Spike S12 Zeile 9
TOL_LAENGE = 0.01
_TOL_HUELLQUADER = 0.01
_TOL_MASS = 0.01


@dataclass
class BaugruppenMesswerte:
    rebuild_fehler: list[str]
    verknuepfungen: dict[str, int]
    komponenten: dict[str, dict]
    stueckliste: dict[str, int]
    interferenzen: list[dict]
    box: list[float]
    masse_kg: float
    eigenschaften: dict[str, str] = field(default_factory=dict)
    messpunkte: dict[str, Messgeometrie | str] = field(default_factory=dict)
    schrauben: dict[str, Messgeometrie | str] = field(default_factory=dict)
    gewindebohrungen: list[dict] = field(default_factory=list)
    teilberichte: dict[str, dict] = field(default_factory=dict)


@dataclass
class Gewindepaarung:
    schraube: str
    teil: str
    feature: str
    instanz: int
    kopfauflage: Messgeometrie
    eintritt: Messgeometrie


def gewindepaarungen(schrauben: dict, bohrungen: list[dict], tol_mm: float) -> list[Gewindepaarung]:
    """Gepaart sind Schraube und Gewindebohrung, deren Eintrittspunkt auf der Schraubenachse liegt (Präzisierung 1)."""
    paare = []
    for sid, ebene in schrauben.items():
        if isinstance(ebene, str):
            continue
        for b in bohrungen:
            if punkt_achse_abstand(b["eintritt"].punkt, ebene.punkt, ebene.richtung) <= tol_mm:
                paare.append(Gewindepaarung(sid, b["teil"], b["feature"], b["instanz"], ebene, b["eintritt"]))
    return paare


def stueckliste_soll(spec: dict, quellen: dict[str, Quelle], auftrag: str, standard: dict) -> dict[str, int]:
    soll = {}
    for i in instanzen(spec, quellen):
        name = dokument_name(quellen[i.komponente], auftrag, standard)
        soll[name] = soll.get(name, 0) + 1
    return soll


def _paar(a: str, b: str) -> frozenset:
    return frozenset((a, b))


def _gewinde(g: Gewindepaarung, quellen: dict[str, Quelle], m: BaugruppenMesswerte) -> tuple[dict, dict] | None:
    qs, qt = quellen[basis(g.schraube)], quellen[basis(g.teil)]
    f = next(x for x in qt.spec["features"] if x["id"] == g.feature)
    laenge = einschraublaenge(qs.laenge, g.kopfauflage, g.eintritt)
    ist = sum(i["volumen"] for i in m.interferenzen if frozenset(i["paar"]) == _paar(g.schraube, g.teil))
    if laenge <= 0 and ist == 0:
        return None  # die Schraube erreicht diese Bohrung nicht
    pid, knoten = f"gewinde:{g.schraube}", [g.schraube, g.teil]
    bericht = {"schraube": g.schraube, "teil": g.teil, "bohrung": f"{g.feature}.{g.instanz}",
               "einschraublaenge": round(laenge, 3), "volumen": round(ist, 3)}
    if f.get("durch"):
        return _pruefung(pid, None, ist=round(ist, 3), einschraublaenge=round(laenge, 3), knoten=knoten,
                         hinweis="Gewinde durch: Volumen nicht geprüft (Präzisierung 2)"), bericht
    tp = qt.spec.get("parameter", {})
    tiefe, gewindetiefe = auswerten(f["tiefe"], tp), auswerten(f["gewindetiefe"], tp)
    kernloch = normmasse("gewinde", f["groesse"], norm_von(f))["kernloch"]
    soll = ueberlappung_soll(qs.masse["d"], qs.masse["p"], kernloch, laenge)
    bericht |= {"soll": round(soll, 3), "gewindetiefe": gewindetiefe, "tiefe": tiefe}
    daten = {"ist": round(ist, 3), "soll": round(soll, 3), "einschraublaenge": round(laenge, 3),
             "gewindetiefe": gewindetiefe, "tiefe": tiefe, "knoten": knoten}
    ok = abs(ist - soll) <= soll * TOL_GEWINDE_PROZENT / 100
    if laenge > min(gewindetiefe, tiefe) + TOL_LAENGE:
        ok = False
        daten["hinweis"] = (f"Einschraublänge {laenge:.2f} mm größer als Gewindetiefe {gewindetiefe:g} bzw. "
                            f"Bohrtiefe {tiefe:g} mm")
    return _pruefung(pid, ok, **daten), bericht


def _erlaubt_unterbestimmt(spec: dict, instanz_id: str) -> bool:
    fg = spec.get("freiheitsgrade", {})
    k = basis(instanz_id)
    gruppe = next((x.get("gruppe") for x in spec["komponenten"] if x["id"] == k), None)
    return any(fg.get(s) == "unterbestimmt" for s in (instanz_id, k, gruppe) if s)


def _bestimmtheit(spec: dict, quellen: dict[str, Quelle], m: BaugruppenMesswerte) -> dict:
    fix = {k["id"] for k in spec["komponenten"] if k.get("fixiert")}
    offen = {}
    for i in instanzen(spec, quellen):
        w = m.komponenten.get(i.id)
        if w is None:
            grund = "fehlt in der Baugruppe"
        elif i.komponente in fix:
            grund = None if w["fixiert"] else "nicht fixiert"
        elif w["fixiert"]:
            grund = "unerwartet fixiert"
        elif w["status"] == VOLL_BESTIMMT or (w["status"] == UNTERBESTIMMT and _erlaubt_unterbestimmt(spec, i.id)):
            grund = None
        else:
            grund = STATUS_TEXT.get(w["status"], str(w["status"]))
        if grund:
            offen[i.id] = grund
    return _pruefung("bestimmtheit", not offen, ist=offen, knoten=sorted(offen))


def _verknuepfungen(spec: dict, quellen: dict[str, Quelle], m: BaugruppenMesswerte) -> dict:
    soll = [v.id for v in verknuepfungen(spec, quellen)]
    fehlend = [n for n in soll if n not in m.verknuepfungen]
    fehlerhaft = {n: c for n, c in m.verknuepfungen.items() if c}
    fremd = [n for n in m.verknuepfungen if n not in soll]
    knoten = sorted({*fehlend, *fehlerhaft, *fremd})
    return _pruefung("verknuepfungen", not knoten, ist={"fehlend": fehlend, "fehlerhaft": fehlerhaft, "fremd": fremd},
                     soll=len(soll), knoten=knoten)


def _masse_pruefen(pr: dict, p: dict, m: BaugruppenMesswerte) -> list[dict]:
    ergebnisse = []
    for mp in pr.get("masse_pruefen", []):
        pid = f"mass:{mp['was']}"
        von, zu = m.messpunkte.get(messpunkt_schluessel(mp["von"])), m.messpunkte.get(messpunkt_schluessel(mp["zu"]))
        knoten = sorted({x["komponente"] for x in (mp["von"], mp["zu"]) if "komponente" in x})
        soll, tol = auswerten(mp["soll"], p), mp.get("tol", _TOL_MASS)
        if not isinstance(von, Messgeometrie) or not isinstance(zu, Messgeometrie):
            hinweis = next((x for x in (von, zu) if isinstance(x, str)), "Messpunkt fehlt")
            ergebnisse.append(_pruefung(pid, False, soll=soll, hinweis=hinweis, knoten=knoten))
            continue
        try:
            ist = round(abstand(von, zu), 6)
        except NichtMessbar as e:
            ergebnisse.append(_pruefung(pid, False, soll=soll, hinweis=str(e), knoten=knoten))
            continue
        ergebnisse.append(_pruefung(pid, abs(ist - soll) <= tol, ist=ist, soll=soll, tol=tol, knoten=knoten))
    return ergebnisse


def bewerte_baugruppe(spec: dict, quellen: dict[str, Quelle], m: BaugruppenMesswerte, standard: dict,
                      soll_stueckliste: dict[str, int]) -> dict:
    p = spec.get("parameter", {})
    pr = spec.get("pruefung", {})
    ergebnisse = [_pruefung("rebuild", not m.rebuild_fehler, ist=m.rebuild_fehler, knoten=[]),
                  _verknuepfungen(spec, quellen, m), _bestimmtheit(spec, quellen, m)]

    abweichend = {n: {"ist": m.stueckliste.get(n, 0), "soll": s} for n, s in soll_stueckliste.items()
                  if m.stueckliste.get(n, 0) != s}
    abweichend |= {n: {"ist": c, "soll": 0} for n, c in m.stueckliste.items() if n not in soll_stueckliste}
    ergebnisse.append(_pruefung("stueckliste", not abweichend, ist=abweichend, knoten=[]))

    gewinde_bericht, gepaart = [], set()
    for sid, ebene in m.schrauben.items():
        if isinstance(ebene, str):
            ergebnisse.append(_pruefung(f"gewinde:{sid}", False, hinweis=ebene, knoten=[sid]))
    for g in gewindepaarungen(m.schrauben, m.gewindebohrungen, standard["toleranzen"]["anker_mm"]):
        if (e := _gewinde(g, quellen, m)) is not None:
            ergebnisse.append(e[0])
            gewinde_bericht.append(e[1])
            gepaart.add(_paar(g.schraube, g.teil))
    kollisionen = [i for i in m.interferenzen if frozenset(i["paar"]) not in gepaart]
    ergebnisse.append(_pruefung("kollision", not kollisionen, ist=kollisionen,
                                knoten=sorted({k for i in kollisionen for k in i["paar"]})))

    if "huellquader" in pr:
        soll = [auswerten(v, p) for v in pr["huellquader"]]
        ist = [round(m.box[i + 3] - m.box[i], 6) for i in range(3)]
        tol = pr.get("huellquader_tol", _TOL_HUELLQUADER)
        ergebnisse.append(_pruefung("huellquader", all(abs(a - b) <= tol for a, b in zip(ist, soll)), ist=ist,
                                    soll=soll, tol=tol, knoten=[]))
    if "masse" in pr:
        soll = auswerten(pr["masse"]["soll"], p)
        prozent = pr["masse"].get("toleranz_prozent", standard["toleranzen"]["volumen_prozent"])
        abw = abs(m.masse_kg - soll) / soll * 100
        ergebnisse.append(_pruefung("masse", abw <= prozent, ist=round(m.masse_kg, 4), soll=soll,
                                    abweichung_prozent=round(abw, 4), tol_prozent=prozent, knoten=[]))
    ergebnisse += _masse_pruefen(pr, p, m)
    soll_eig = spec.get("eigenschaften", {})
    abw_eig = {k: m.eigenschaften.get(k) for k, v in soll_eig.items() if m.eigenschaften.get(k) != v}
    ergebnisse.append(_pruefung("eigenschaften", not abw_eig, ist=abw_eig, soll=soll_eig, knoten=[]))

    teilpruefungen = {}
    for datei, tb in m.teilberichte.items():
        komp = next(k for k, q in quellen.items() if q.datei == datei)
        teilpruefungen[komp] = {"bestanden": tb["bestanden"], "maengel": len(tb["maengel"])}
        ergebnisse += [{**e, "id": f"{komp}: {e['id']}", "knoten": [f"{komp}/{k}" for k in e["knoten"]] or [komp]}
                       for e in tb["pruefungen"]]

    maengel = [{"pruefung": e["id"], "knoten": e["knoten"], "beschreibung": _beschreibung(e)}
               for e in ergebnisse if e["ok"] is False]
    return {"bestanden": not maengel, "pruefungen": ergebnisse, "maengel": maengel, "stueckliste": m.stueckliste,
            "gewindepaarungen": gewinde_bericht, "teilpruefungen": teilpruefungen, "masse_kg": round(m.masse_kg, 4)}
```

- [ ] **Step 6: Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → **559 passed** (538 + 21: Geometrie 7, Bewertung 14).

- [ ] **Step 7: Commit**

```powershell
git add swki/baugruppe/geometrie.py swki/baugruppe/bewertung.py tests/baugruppe/test_geometrie_baugruppe.py tests/baugruppe/test_bewertung_baugruppe.py
git commit -m "baugruppe: Bewertung – Verknüpfungen, Bestimmtheit, Kollision, Gewindepaarungen, Lage" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: `swki pruefen` für Baugruppen, `status`/`bericht`, Verknüpfungswerte in `swki aenderungen`

**Files:**
- Create: `swki/baugruppe/pruefen.py`
- Modify: `swki/pruefung/messen.py` (`_messgeometrie` → `messgeometrie`), `swki/pruefung/befehle.py` (Weichen, `schreibe_pruefbericht`, `lade_spec_beliebig`), `swki/pruefung/bericht.py` (Abschnitte), `swki/aenderungen.py` (Verknüpfungswerte)
- Create: `tests/baugruppe/test_pruefen_baugruppe.py`
- Modify: `tests/live/test_live_baugruppe.py`

**Interfaces:**
- Consumes: Task 2–9; `swki.pruefung.messen` (`oeffne`, `kontext_aus_datei`, `messe`, `rebuild_fehler`), `swki.pruefung.bewertung.bewerte`, `swki.pruefung.bilder.screenshots`, `swki.compiler.eigenschaften.lies_eigenschaften`; Spike-Zeilen 10, 12.
- Produces: `swki.baugruppe.pruefen.pruefen(spec_pfad, lauf=None) -> dict`, `teil_messpunkte(bg)`, `gewindebohrungen_teil(teil_spec, protokoll_teil)`; `schreibe_pruefbericht(spec_pfad, lauf, ordner, bericht)`, `lade_spec_beliebig(spec_pfad) -> dict`; `messgeometrie(ctx, spec, messpunkt)`; `soll_verknuepfungswerte(spec, quellen) -> dict[str, float]`.

- [ ] **Step 1: Failing tests – `tests/baugruppe/test_pruefen_baugruppe.py` (neu)**

```python
import json

from swki.aenderungen import soll_verknuepfungswerte
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.pruefen import gewindebohrungen_teil, teil_messpunkte
from swki.pruefung.befehle import schreibe_pruefbericht, status
from swki.pruefung.bericht import bericht_markdown
from tests.baugruppe.beispiel import BAUGRUPPE, PLATTE, kopie, schreibe


def test_gewindebohrungen_aus_dem_protokoll():
    protokoll = {"knoten": [{"id": "f1", "punkte": None}, {"id": "f2", "punkte": [[-30, 20, 0], [30, 20, 0]]},
                            {"id": "f3", "punkte": [[0, 20, -15]]}]}
    assert gewindebohrungen_teil(PLATTE, protokoll) == [{"feature": "f2", "instanz": 1, "punkt": (-30, 20, 0)},
                                                        {"feature": "f2", "instanz": 2, "punkt": (30, 20, 0)}]


def test_teil_messpunkte(tmp_path):
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    bedarf = teil_messpunkte(bg)
    assert bedarf["platte.yaml"] == [{"feature": "f1", "flaeche": "-y"}]
    assert bedarf["deckel.yaml"] == [{"feature": "f1", "flaeche": "+y"}]
    assert bedarf["ISO4762_M8x16_8_8"] == [{"referenz": "EINBAU_EBENE"}]


def test_pruefbericht_verwirft_altes_urteil(tmp_path):
    spec_pfad = tmp_path / "A" / "probe.yaml"
    urteil = spec_pfad.parent / "protokolle" / "probe.lauf-1.pruefer.json"
    urteil.parent.mkdir(parents=True)
    urteil.write_text("{}", encoding="utf-8")
    ordner = tmp_path / "lauf-1"
    ordner.mkdir()
    schreibe_pruefbericht(spec_pfad, 1, ordner, bericht := {"bestanden": True, "maengel": []})
    assert not urteil.exists() and bericht["pruefer_urteil_verworfen"] is True
    assert json.loads((ordner / "pruefbericht.json").read_text(encoding="utf-8"))["bestanden"] is True


def test_status_einer_baugruppe(tmp_path):
    assert status(schreibe(tmp_path / "A"))["empfehlung"] == "bauen"


def test_bericht_abschnitte():
    bericht = {"maengel": [], "bilder": {}, "stueckliste": {"A_Platte.sldprt": 1},
               "normteile": {"ISO4762_M8x16_8_8": {"gebaut": False, "pruefsumme": "abc"}},
               "gewindepaarungen": [{"schraube": "schraube.1", "teil": "platte", "bohrung": "f2.1",
                                     "einschraublaenge": 9.6, "volumen": 133.1, "soll": 133.0, "gewindetiefe": 12}],
               "teilpruefungen": {"platte": {"bestanden": True, "maengel": 0}}}
    text = bericht_markdown(BAUGRUPPE, "A", [], ("pruefen", "…"), bericht, None, None, [])
    for teil in ("## Stückliste", "| A_Platte.sldprt | 1 |", "## Normteile", "## Gewindepaarungen", "| schraube.1 |",
                 "## Teilprüfungen", "| platte | ja | 0 |"):
        assert teil in text


def test_soll_verknuepfungswerte(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][0] = {**spec["verknuepfungen"][0], "typ": "abstand", "wert": "=ABST/7"}
    bg = lade_baugruppe(schreibe(tmp_path / "A", baugruppe=spec))
    assert soll_verknuepfungswerte(bg.spec, bg.quellen) == {"v1": 5.0}
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_pruefen_baugruppe.py -q`
Expected: FAIL (ImportError `swki.baugruppe.pruefen`, `schreibe_pruefbericht`, `soll_verknuepfungswerte`).

- [ ] **Step 3: `swki/pruefung/messen.py`** – `_messgeometrie` in `messgeometrie` umbenennen (Definition und Aufruf in `messpunkte`); Verhalten unverändert.

- [ ] **Step 4: `swki/pruefung/befehle.py`** – Weichen und gemeinsames Schreiben (Import `from swki.spec.laden import art_der_datei, lade_spec`)

```python
def lade_spec_beliebig(spec_pfad: Path) -> dict:
    """Geprüfte Spezifikation eines Teils oder einer Baugruppe (für status und bericht)."""
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.laden import lade_baugruppe  # spät importiert (Kreisimport)

        return lade_baugruppe(spec_pfad).spec
    return lade_spec(spec_pfad)


def schreibe_pruefbericht(spec_pfad: Path, lauf: int, ordner: Path, bericht: dict) -> None:
    """Prüfbericht in den Lauf-Ordner und nach protokolle/. Ein Prüfer-Urteil gehört zum vorherigen Bericht dieses Laufs
    und wird verworfen; sonst könnte status ein veraltetes "bestanden" melden."""
    pruefer_datei = lauf_datei(spec_pfad, lauf, "pruefer")
    if pruefer_datei.exists():
        pruefer_datei.unlink()
        bericht["pruefer_urteil_verworfen"] = True
    text = json.dumps(bericht, indent=2, ensure_ascii=False, default=str) + "\n"
    (ordner / "pruefbericht.json").write_text(text, encoding="utf-8")
    ziel = lauf_datei(spec_pfad, lauf, "pruefbericht")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
```

In `pruefen` am Anfang verzweigen und am Ende `schreibe_pruefbericht` nutzen:

```python
def pruefen(spec_pfad: Path, lauf: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    if art_der_datei(spec_pfad) == "baugruppe":
        from swki.baugruppe.pruefen import pruefen as baugruppe_pruefen  # spät importiert (Kreisimport)

        return baugruppe_pruefen(spec_pfad, lauf)
    spec = lade_spec(spec_pfad)
    # … unverändert bis zur Zusammenstellung von bericht …
    schreibe_pruefbericht(spec_pfad, lauf, ordner, bericht)
    return bericht
```

In `status` und `bericht` `lade_spec(spec_pfad)` durch `lade_spec_beliebig(spec_pfad)` ersetzen.

- [ ] **Step 5: `swki/pruefung/bericht.py`** – nach dem Block „Feature-Baum (letzter Lauf)“ einfügen

```python
    letzter = letzter_bericht or {}
    if letzter.get("stueckliste"):
        zeilen += ["", "## Stückliste (letzter Lauf)", "", "| Datei | Anzahl |", "|---|---|"]
        zeilen += [f"| {n} | {c} |" for n, c in sorted(letzter["stueckliste"].items())]
    if letzter.get("normteile"):
        zeilen += ["", "## Normteile", "", "| Schlüssel | neu gebaut | Bibliotheksprüfsumme |", "|---|---|---|"]
        zeilen += [f"| {s} | {'ja' if e.get('gebaut') else 'nein'} | {_zelle(e.get('pruefsumme'))} |"
                   for s, e in sorted(letzter["normteile"].items())]
    if letzter.get("gewindepaarungen"):
        zeilen += ["", "## Gewindepaarungen", "",
                   "| Schraube | Teil | Bohrung | Einschraublänge (mm) | Gewindetiefe (mm) | Volumen ist / soll (mm³) |",
                   "|---|---|---|---|---|---|"]
        zeilen += [f"| {g['schraube']} | {g['teil']} | {g['bohrung']} | {g['einschraublaenge']} | "
                   f"{_zelle(g.get('gewindetiefe'))} | {g['volumen']} / {_zelle(g.get('soll'))} |"
                   for g in letzter["gewindepaarungen"]]
    if letzter.get("teilpruefungen"):
        zeilen += ["", "## Teilprüfungen (letzter Lauf)", "", "| Komponente | bestanden | Mängel |", "|---|---|---|"]
        zeilen += [f"| {k} | {'ja' if t['bestanden'] else 'nein'} | {t['maengel']} |"
                   for k, t in sorted(letzter["teilpruefungen"].items())]
```

- [ ] **Step 6: `swki/aenderungen.py`** – Verknüpfungswerte (Spec 3b §8)

Neue Funktion und Erweiterungen (Import `from swki.spec.ausdruck import auswerten`):

```python
def soll_verknuepfungswerte(spec: dict, quellen: dict) -> dict[str, float]:
    """Abstands- und Winkelwerte der aufgelösten Verknüpfungen (mm bzw. Grad) nach Verknüpfungs-ID."""
    from swki.baugruppe.aufloesen import verknuepfungen  # spät importiert (Kreisimport)

    p = spec.get("parameter", {})
    return {v.id: auswerten(v.wert, p) for v in verknuepfungen(spec, quellen) if v.wert is not None}
```

In `soll_parameter` die Baugruppen-Zeile erweitern:

```python
        ergebnis[f"{dateiname(soll, auftrag, standard)}.sldasm"] = {
            **soll.get("parameter", {}),
            **{f"verknuepfung:{n}": w for n, w in soll_verknuepfungswerte(bg.spec, bg.quellen).items()}}
```

In `aenderungen` beim Auslesen einer `.sldasm` die Verknüpfungswerte ergänzen (innerhalb des `try`, vor dem Schließen):

```python
            try:
                ist = lies_globale_variablen(model)
                if name.lower().endswith(".sldasm"):
                    from swki.baugruppe import sw_baugruppe  # spät importiert (Kreisimport)

                    ist |= {f"verknuepfung:{n}": w for n, w in sw_baugruppe.verknuepfungswerte(model).items()}
            finally:
                sw.schliesse(app, model)  # schließt ohne zu speichern (S9b)
```

- [ ] **Step 7: `swki/baugruppe/pruefen.py`**

```python
"""swki pruefen für Baugruppen (Spec 3b §9): erst jedes Eigenteil (Teilprüfung, Geometrie für die Baugruppenmessung),
dann die Normteil-Kopien (Kopfauflagen, Messpunkte), zuletzt die Baugruppe (Verknüpfungen, Bestimmtheit, Kollision,
Stückliste, Lage, Screenshots). Öffnet Dateien nur und speichert nie."""

import json
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner, laeufe
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import basis, instanzen
from swki.baugruppe.bewertung import BaugruppenMesswerte, bewerte_baugruppe, stueckliste_soll
from swki.baugruppe.freigabe import freigegebene_teile, pruefe_freigabe_baugruppe
from swki.baugruppe.geometrie import transformiere
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.modell import Baugruppe, dokument_name
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.eigenschaften import lies_eigenschaften
from swki.compiler.fehler import BauFehler
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.befehle import pruefe_lauf_gebaut, schreibe_pruefbericht
from swki.pruefung.bewertung import bewerte, messpunkt_schluessel
from swki.pruefung.bilder import screenshots
from swki.pruefung.geometrie import Messgeometrie
from swki.pruefung.messen import kontext_aus_datei, messe, messgeometrie, oeffne, rebuild_fehler
from swki.spec.ausdruck import auswerten
from swki.verbindung import verbinde

KOPFAUFLAGE = {"referenz": "EINBAU_EBENE"}


def _ohne_komponente(p: dict) -> dict:
    return {k: v for k, v in p.items() if k != "komponente"}


def teil_messpunkte(bg: Baugruppe) -> dict[str, list[dict]]:
    """Teil-Messpunkte je Quelldokument: Messpunkte von masse_pruefen und die Kopfauflage jeder Schraube ISO 4762."""
    bedarf: dict[str, list[dict]] = {}
    for mp in bg.spec.get("pruefung", {}).get("masse_pruefen", []):
        for p in (mp["von"], mp["zu"]):
            if "komponente" in p:
                punkte = bedarf.setdefault(bg.quellen[basis(p["komponente"])].schluessel_dokument, [])
                if _ohne_komponente(p) not in punkte:
                    punkte.append(_ohne_komponente(p))
    for q in bg.quellen.values():
        if q.norm == "ISO 4762" and KOPFAUFLAGE not in bedarf.setdefault(q.schluessel, []):
            bedarf[q.schluessel].append(KOPFAUFLAGE)
    return bedarf


def gewindebohrungen_teil(teil_spec: dict, protokoll_teil: dict) -> list[dict]:
    """Eintrittspunkte (Teilkoordinaten) aller Gewinde-Normbohrungen aus dem Bauprotokoll des Teils."""
    punkte = {k["id"]: k.get("punkte") or [] for k in protokoll_teil.get("knoten", [])}
    return [{"feature": f["id"], "instanz": i, "punkt": tuple(p)}
            for f in teil_spec["features"] if f["typ"] == "normbohrung" and f["art"] == "gewinde"
            for i, p in enumerate(punkte.get(f["id"], []), start=1)]


def _geometrie(ctx, punkte: list[dict]) -> dict:
    ergebnis = {}
    for p in punkte:
        try:
            ergebnis[messpunkt_schluessel(p)] = messgeometrie(ctx, ctx.spec, p)
        except BauFehler as e:
            ergebnis[messpunkt_schluessel(p)] = f"{e.code}: {e}"
    return ergebnis


def _in_baugruppe(geo, t):
    return geo if isinstance(geo, str) else transformiere(geo, t)


def _messe_baugruppe(asm, bg: Baugruppe, protokoll: dict, geometrie: dict, teilberichte: dict) -> BaugruppenMesswerte:
    namen = {k["sw_name"]: k["id"] for k in protokoll.get("komponenten", [])}
    transformationen, zustand, stueckliste = {}, {}, {}
    for komp in sw_baugruppe.komponenten(asm):
        datei = Path(komp.GetPathName).name
        stueckliste[datei] = stueckliste.get(datei, 0) + 1
        iid = namen.get(komp.Name2, komp.Name2)
        transformationen[iid] = sw_baugruppe.transform(komp)
        zustand[iid] = {"status": sw_baugruppe.status(komp), "fixiert": sw_baugruppe.ist_fixiert(komp)}
    parameter = bg.spec.get("parameter", {})
    messpunkte = {}
    for mp in bg.spec.get("pruefung", {}).get("masse_pruefen", []):
        for p in (mp["von"], mp["zu"]):
            if "punkt" in p:
                messpunkte[messpunkt_schluessel(p)] = Messgeometrie("punkt", tuple(auswerten(v, parameter) for v in p["punkt"]))
            elif p["komponente"] not in transformationen:
                messpunkte[messpunkt_schluessel(p)] = f"Komponente {p['komponente']} fehlt in der Baugruppe"
            else:
                quelle = bg.quellen[basis(p["komponente"])].schluessel_dokument
                geo = geometrie.get(quelle, {}).get(messpunkt_schluessel(_ohne_komponente(p)), "Messpunkt fehlt")
                messpunkte[messpunkt_schluessel(p)] = _in_baugruppe(geo, transformationen[p["komponente"]])
    schrauben, bohrungen = {}, []
    for i in instanzen(bg.spec, bg.quellen):
        q = bg.quellen[i.komponente]
        if i.id not in transformationen:
            continue
        if q.norm == "ISO 4762":
            geo = geometrie.get(q.schluessel, {}).get(messpunkt_schluessel(KOPFAUFLAGE), "Kopfauflage fehlt")
            schrauben[i.id] = _in_baugruppe(geo, transformationen[i.id])
        elif q.art == "teil":
            for b in gewindebohrungen_teil(q.spec, protokoll["teile"][q.datei]):
                bohrungen.append({"teil": i.id, "feature": b["feature"], "instanz": b["instanz"],
                                  "eintritt": transformiere(Messgeometrie("punkt", b["punkt"]), transformationen[i.id])})
    interferenzen = [{"paar": sorted(namen.get(n, n) for n in paar), "volumen": volumen}
                     for paar, volumen in sw_baugruppe.interferenzen(asm)]
    return BaugruppenMesswerte(
        rebuild_fehler=rebuild_fehler(asm),
        verknuepfungen={f.Name: sw_baugruppe.fehlercode(f) for f in sw_baugruppe.verknuepfungen(asm)},
        komponenten=zustand, stueckliste=stueckliste, interferenzen=interferenzen,
        box=sw_baugruppe.huellquader(asm), masse_kg=sw_baugruppe.masse_kg(asm), eigenschaften=lies_eigenschaften(asm),
        messpunkte=messpunkte, schrauben=schrauben, gewindebohrungen=bohrungen, teilberichte=teilberichte)


def pruefen(spec_pfad: Path, lauf: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    bg = lade_baugruppe(spec_pfad)
    pruefe_freigabe_baugruppe(bg)
    r, standard = lade_rechner(), lade_standard()
    tol = standard["toleranzen"]["anker_mm"]
    auftrag = auftrag_name(spec_pfad)
    if lauf is None:
        bisher = laeufe(r, auftrag)
        if not bisher:
            raise SwkiFehler(f"Auftrag {auftrag} hat noch keinen Lauf. Zuerst: swki bauen")
        lauf = bisher[-1]
    ordner = lauf_ordner(r, auftrag, lauf)
    asm_pfad = ordner / f"{dateiname(bg.spec, auftrag, standard)}.sldasm"
    if not asm_pfad.exists():
        raise SwkiFehler(f"{asm_pfad} fehlt (Lauf {lauf} ohne gespeicherte Baugruppe)")
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    pruefe_lauf_gebaut(protokoll, lauf)
    soll_teile = freigegebene_teile(bg)
    bedarf = teil_messpunkte(bg)
    app = verbinde(r.sw_jahr)
    teilberichte, geometrie = {}, {}
    for datei, teil_spec in bg.teile.items():
        model = oeffne(app, ordner / dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard))
        try:
            ctx = kontext_aus_datei(app, model, teil_spec, bg.pfad.parent / datei, tol, protokoll["teile"][datei])
            teilberichte[datei] = bewerte(teil_spec, messe(ctx, soll_teile[datei]), standard, soll_teile[datei])
            geometrie[datei] = _geometrie(ctx, bedarf.get(datei, []))
        finally:
            sw.schliesse(app, model)
    for q in {q.schluessel: q for q in bg.quellen.values() if q.art == "normteil"}.values():
        if q.schluessel not in bedarf:
            continue
        pfad = ordner / dokument_name(q, auftrag, standard)
        model = oeffne(app, pfad)
        try:
            ctx = kontext_aus_datei(app, model, q.spec, pfad.with_suffix(".yaml"), tol, {"knoten": []})
            geometrie[q.schluessel] = _geometrie(ctx, bedarf[q.schluessel])
        finally:
            sw.schliesse(app, model)
    asm = oeffne(app, asm_pfad)
    try:
        sw_baugruppe.aufloesen(asm)
        messwerte = _messe_baugruppe(asm, bg, protokoll, geometrie, teilberichte)
        bilder = screenshots(app, asm, ordner / "bilder")
    finally:
        sw.schliesse(app, asm)
    bericht = {
        "auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(asm_pfad), "art": "baugruppe",
        **bewerte_baugruppe(bg.spec, bg.quellen, messwerte, standard, stueckliste_soll(bg.spec, bg.quellen, auftrag, standard)),
        "normteile": protokoll.get("normteile", {}), "bilder": bilder,
    }
    schreibe_pruefbericht(spec_pfad, lauf, ordner, bericht)
    return bericht
```

- [ ] **Step 8: Unit-Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → **565 passed** (559 + 6).
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.

- [ ] **Step 9: Live-Tests in `tests/live/test_live_baugruppe.py` ergänzen**

`test_probe_baut` bleibt; `test_werte_verknuepfungen` bekommt eine Lageprüfung, und zwei Tests kommen dazu:

```python
def test_probe_besteht_pruefung(capsys, auftrag):
    pfad, code, bau = _baue(capsys, auftrag)
    assert code == 0, bau
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    assert code == 0, bericht
    assert bericht["maengel"] == [], json.dumps(bericht["pruefungen"], indent=1, ensure_ascii=False)
    assert [g["einschraublaenge"] for g in bericht["gewindepaarungen"]] == pytest.approx([9.6, 9.6], abs=0.01)
    assert all(pathlib.Path(p).stat().st_size > 0 for p in bericht["bilder"].values())


def test_kollision_wird_gemeldet(capsys, auftrag):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"][3]["quelle"] = {"normteil": "ISO 8734 8x30"}   # Stift ragt 10 mm in den Deckel
    pfad, code, bau = _baue(capsys, auftrag, spec)
    assert code == 0, bau
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    maengel = {m["pruefung"]: m for m in bericht["maengel"]}
    assert maengel["kollision"]["knoten"] == ["deckel", "stift"], bericht["maengel"]
```

In `test_werte_verknuepfungen` statt `spec["pruefung"] = {}`:

```python
    spec["pruefung"] = {"masse_pruefen": [
        {"was": "Abstand", "von": {"komponente": "platte", "feature": "f1", "flaeche": "+y"},
         "zu": {"komponente": "deckel", "feature": "f1", "flaeche": "-y"}, "soll": "=S"}]}
```

und am Ende:

```python
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    assert code == 0 and bericht["maengel"] == [], bericht["maengel"]
```

(`pfad` dafür aus `_baue` übernehmen statt `_`; Import `import pathlib` ergänzen.)

- [ ] **Step 10: Live**

Vorbedingungen (eine Instanz, `False 1`, Private Bytes). Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_baugruppe.py --zeit 300` → 6/6 OK. Danach `tests\live\test_live_pruefen.py` und `tests\live\test_live_aenderungen.py` einzeln (Regression der geänderten Prüf-/Änderungspfade). Weicht die Gewindepaarung ab (Volumen außerhalb 1 %): Messwerte melden, Controller entscheidet nach Spike-Zeile 9 – nie die Toleranz ohne Beleg ändern.

- [ ] **Step 11: Commit**

```powershell
git add swki/baugruppe/pruefen.py swki/pruefung/messen.py swki/pruefung/befehle.py swki/pruefung/bericht.py swki/aenderungen.py tests/baugruppe/test_pruefen_baugruppe.py tests/live/test_live_baugruppe.py
git commit -m "baugruppe: swki pruefen, status und bericht für Baugruppen, Verknüpfungswerte in aenderungen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Referenz Stehlager, Prüfer-Urteil, Negativfälle (live)

**Files:**
- Create: `tests/referenz/stehlager/stehlager.yaml`, `grundplatte.yaml`, `unterteil.yaml`, `deckel.yaml`, `eingabe/beschreibung.md`
- Modify: `tests/referenz/test_referenzen.py` (Eintrag Stehlager)
- Create: `tests/baugruppe/test_stehlager_spec.py`, `tests/live/test_live_stehlager.py`

**Interfaces:**
- Consumes: alle vorherigen Tasks; Normteile ISO 4762 M8×35 und M10×55, ISO 7089 M10, ISO 4032 M10, ISO 8734 8×30 (Urteile aus 3a bzw. Task 6).
- Produces: die Referenzbaugruppe des Fertig-Kriteriums (Spec 3b §16) und die Negativfälle (Spec 3b §14).

Geometrie (Baugruppenkoordinaten, mm): Grundplatte 200 × 100 × 20 (y 0…20, fixiert). Lagerunterteil: Fuß 160 × 60 × 20 auf der Grundplatte (y 20…40), Lagerkörper 90 × 50 bis zur Trennebene y = 70 (Achshöhe `H` = 70 über der Grundplatten-Unterseite), Lagerbohrung Ø 40 als Halbschale. Lagerdeckel 90 × 50 × 30 auf der Trennebene (y 70…100) mit Halbschale. Deckel → Unterteil: 2 × ISO 4762 M8 × 35 in Senkungen (Senkungsgrund y = 91,4) und Gewinde M8 (Tiefe 20, Gewindetiefe 16) → Einschraublänge 13,6. Unterteil → Grundplatte: 2 × ISO 4762 M10 × 55 durch Ø 11 mit ISO 7089 M10 unter Kopf (y 40…42) und unter der Mutter (y 0…−2) und ISO 4032 M10 (y −2…−10,4), Schraubenende y = −13. 2 × ISO 8734 8 × 30 durch die Grundplatte (bündig unten) 10 mm in Stiftbohrungen des Fußes (Tiefe 12). Hülle 200 × 113 × 100.

- [ ] **Step 1: `tests/referenz/stehlager/grundplatte.yaml`**

```yaml
# Referenz Stehlager (Spec 3b): Grundplatte, fixiert. Ursprung Mitte Unterseite, Oberseite y = H.
art: teil
name: Grundplatte
material: "1.0038"
eigenschaften: {Benennung: Grundplatte Stehlager}
parameter: {L: 200, B: 100, H: 20, A: 120, DG: 11, AS: 70}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: bohrung, flaeche: {feature: f1, flaeche: "+y"}, positionen: [["=-A/2", 0], ["=A/2", 0]],
     durchmesser: "=DG", durch: true}
  - {id: f3, typ: normbohrung, art: stift, groesse: 8, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=-AS/2", 0], ["=AS/2", 0]], durch: true}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: Abstand Durchgangsbohrungen, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true}, soll: "=A"}
    - {was: Abstand Stiftbohrungen, von: {feature: f3, instanz: 1, achse: true}, zu: {feature: f3, instanz: 2, achse: true}, soll: "=AS"}
```

- [ ] **Step 2: `tests/referenz/stehlager/unterteil.yaml`**

```yaml
# Referenz Stehlager (Spec 3b): Lagerunterteil. Fuß y 0…HF, Lagerkörper bis zur Trennebene y = AH (Lagerachse).
# Die Gewinde für den Deckel werden vor der Lagerbohrung gebohrt (Fläche +y von f2 ist dann noch ungeteilt);
# die Trennebene ist eine benannte Referenz, weil die Fläche nach der Lagerbohrung zweigeteilt ist.
# Der Lagerkörper (TK) ist schmaler als der Fuß (TF), damit die Fußoberseite eine zusammenhängende Fläche bleibt.
art: teil
name: Lagerunterteil
material: "1.0038"
eigenschaften: {Benennung: Lagerunterteil Stehlager}
parameter: {LF: 160, TF: 60, HF: 20, LK: 90, TK: 50, AH: 50, DB: 40, AB: 65, A: 120, DG: 11, AS: 70, TG: 20, GT: 16, TS: 12}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=LF", hoehe: "=TF"}}]}
    ende: {typ: blind, tiefe: "=HF"}
  - id: f2
    typ: extrusion
    skizze: {ebene: {versatz: {ebene: oben, abstand: "=HF"}}, elemente: [{rechteck: {mitte: [0, 0], breite: "=LK", hoehe: "=TK"}}]}
    ende: {typ: blind, tiefe: "=AH-HF"}
  - {id: f3, typ: normbohrung, art: gewinde, groesse: M8, flaeche: {feature: f2, flaeche: "+y"},
     positionen: [["=-AB/2", 0], ["=AB/2", 0]], tiefe: "=TG", gewindetiefe: "=GT"}
  - id: f4
    typ: schnitt
    skizze: {ebene: vorne, elemente: [{kreis: {mitte: [0, "=AH"], durchmesser: "=DB"}}]}
    ende: {typ: mittig, tiefe: "=TK"}
  - {id: f5, typ: bohrung, flaeche: {feature: f1, flaeche: "+y"}, positionen: [["=-A/2", 0], ["=A/2", 0]],
     durchmesser: "=DG", durch: true}
  - {id: f6, typ: normbohrung, art: stift, groesse: 8, flaeche: {feature: f1, flaeche: "-y"},
     positionen: [["=-AS/2", 0], ["=AS/2", 0]], tiefe: "=TS"}
  - {id: TRENNEBENE, typ: referenz, ebene: {basis: oben, abstand: "=AH"}}
pruefung:
  huellquader: ["=LF", "=AH", "=TF"]
  masse_pruefen:
    - {was: Abstand Gewinde, von: {feature: f3, instanz: 1, achse: true}, zu: {feature: f3, instanz: 2, achse: true}, soll: "=AB"}
    - {was: Abstand Durchgangsbohrungen, von: {feature: f5, instanz: 1, achse: true}, zu: {feature: f5, instanz: 2, achse: true}, soll: "=A"}
    - {was: Abstand Stiftbohrungen, von: {feature: f6, instanz: 1, achse: true}, zu: {feature: f6, instanz: 2, achse: true}, soll: "=AS"}
    - {was: Achshöhe, von: {referenz: TRENNEBENE}, zu: {feature: f1, flaeche: "-y"}, soll: "=AH"}
  durchmesser_pruefen:
    - {was: Lagerbohrung, feature: f4, nahe: [0, "=AH-DB/2", 0], soll: "=DB"}
```

- [ ] **Step 3: `tests/referenz/stehlager/deckel.yaml`**

```yaml
# Referenz Stehlager (Spec 3b): Lagerdeckel. Unterseite (Trennebene) y = 0, Oberseite y = HD, Halbschale um die
# Lagerachse in y = 0. Senkungen für ISO 4762 M8 vor der Halbschale.
art: teil
name: Lagerdeckel
material: "1.0038"
eigenschaften: {Benennung: Lagerdeckel Stehlager}
parameter: {LK: 90, TK: 50, HD: 30, AB: 65, DB: 40}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=LK", hoehe: "=TK"}}]}
    ende: {typ: blind, tiefe: "=HD"}
  - {id: f2, typ: normbohrung, art: zylinderschraube, groesse: M8, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=-AB/2", 0], ["=AB/2", 0]], durch: true}
  - id: f3
    typ: schnitt
    skizze: {ebene: vorne, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=DB"}}]}
    ende: {typ: mittig, tiefe: "=TK"}
  - {id: TRENNEBENE, typ: referenz, ebene: {basis: oben}}
pruefung:
  huellquader: ["=LK", "=HD", "=TK"]
  masse_pruefen:
    - {was: Abstand Schraubenbohrungen, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true}, soll: "=AB"}
  durchmesser_pruefen:
    - {was: Lagerbohrung, feature: f3, nahe: [0, "=DB/2", 0], soll: "=DB"}
```

- [ ] **Step 4: `tests/referenz/stehlager/stehlager.yaml`**

Ausrichtungen nach Spike-Zeile 5 („gleich“ = Normalen gleichgerichtet; Bezugsebenen haben die Normale +y ihrer Basis, Flächennormalen zeigen aus dem Material). Reihenfolge je Normteil: Ebene vor Achse (Präzisierung 9).

```yaml
# Referenz Stehlager (Spec 3b §2, §16): Grundplatte, Lagerunterteil, Lagerdeckel; Deckel mit 2 × ISO 4762 M8 × 35 in
# Gewinde, Unterteil mit 2 Durchsteckverschraubungen ISO 4762 M10 × 55 + 2 × ISO 7089 + ISO 4032, zentriert mit
# 2 × ISO 8734 8 × 30. Achshöhe H über der Grundplatten-Unterseite.
art: baugruppe
name: Stehlager
eigenschaften: {Benennung: Stehlager}
parameter: {H: 70}
komponenten:
  - {id: grundplatte, quelle: {teil: grundplatte.yaml}, fixiert: true}
  - {id: unterteil, quelle: {teil: unterteil.yaml}}
  - {id: deckel, quelle: {teil: deckel.yaml}}
  - {id: stift, quelle: {normteil: "ISO 8734 8x30"}, je_position: {komponente: grundplatte, feature: f3}}
  - {id: deckelschraube, quelle: {normteil: "ISO 4762 M8x35"}, je_position: {komponente: deckel, feature: f2}}
  - {id: scheibe_kopf, quelle: {normteil: "ISO 7089 M10"}, je_position: {komponente: unterteil, feature: f5}}
  - {id: fussschraube, quelle: {normteil: "ISO 4762 M10x55"}, je_position: {komponente: unterteil, feature: f5}}
  - {id: scheibe_mutter, quelle: {normteil: "ISO 7089 M10"}, je_position: {komponente: unterteil, feature: f5}}
  - {id: mutter, quelle: {normteil: "ISO 4032 M10"}, je_position: {komponente: unterteil, feature: f5}}
verknuepfungen:
  # Unterteil auf der Grundplatte: Fuß aufliegend, Stiftbohrung 1 über Stiftbohrung 1, Seiten parallel
  - {id: v1, typ: deckungsgleich, a: {komponente: unterteil, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v2, typ: konzentrisch, a: {komponente: unterteil, feature: f6, instanz: 1, achse: true},
     b: {komponente: grundplatte, feature: f3, instanz: 1, achse: true}}
  - {id: v3, typ: parallel, a: {komponente: unterteil, feature: f1, flaeche: "+x"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+x"}, ausrichtung: gleich}
  # Deckel auf der Trennebene, Schraubenbohrung 1 über Gewinde 1, Seiten parallel
  - {id: v4, typ: deckungsgleich, a: {komponente: deckel, referenz: TRENNEBENE},
     b: {komponente: unterteil, referenz: TRENNEBENE}, ausrichtung: gleich}
  - {id: v5, typ: konzentrisch, a: {komponente: deckel, feature: f2, instanz: 1, achse: true},
     b: {komponente: unterteil, feature: f3, instanz: 1, achse: true}}
  - {id: v6, typ: parallel, a: {komponente: deckel, feature: f1, flaeche: "+x"},
     b: {komponente: unterteil, feature: f2, flaeche: "+x"}, ausrichtung: gleich}
  # Stifte bündig mit der Grundplatten-Unterseite
  - {id: v10, typ: deckungsgleich, a: {komponente: stift, referenz: EINBAU_EBENE_1},
     b: {komponente: grundplatte, feature: f1, flaeche: "-y"}, ausrichtung: entgegengesetzt}
  - {id: v11, typ: konzentrisch, a: {komponente: stift, referenz: EINBAU_ACHSE},
     b: {komponente: grundplatte, feature: f3, instanz: je, achse: true}}
  # Deckelschrauben: Kopf auf dem Senkungsgrund
  - {id: v20, typ: deckungsgleich, a: {komponente: deckelschraube, referenz: EINBAU_EBENE},
     b: {komponente: deckel, feature: f2, instanz: je, flaeche: "+y"}, ausrichtung: gleich}
  - {id: v21, typ: konzentrisch, a: {komponente: deckelschraube, referenz: EINBAU_ACHSE},
     b: {komponente: deckel, feature: f2, instanz: je, achse: true}}
  # Durchsteckverschraubung: Scheibe auf dem Fuß, Kopf auf der Scheibe, Scheibe und Mutter unter der Grundplatte
  - {id: v30, typ: deckungsgleich, a: {komponente: scheibe_kopf, referenz: EINBAU_EBENE},
     b: {komponente: unterteil, feature: f1, flaeche: "+y"}, ausrichtung: gleich}
  - {id: v31, typ: konzentrisch, a: {komponente: scheibe_kopf, referenz: EINBAU_ACHSE},
     b: {komponente: unterteil, feature: f5, instanz: je, achse: true}}
  - {id: v32, typ: deckungsgleich, a: {komponente: fussschraube, referenz: EINBAU_EBENE},
     b: {komponente: scheibe_kopf, referenz: EINBAU_EBENE_2}, ausrichtung: gleich}
  - {id: v33, typ: konzentrisch, a: {komponente: fussschraube, referenz: EINBAU_ACHSE},
     b: {komponente: unterteil, feature: f5, instanz: je, achse: true}}
  - {id: v34, typ: deckungsgleich, a: {komponente: scheibe_mutter, referenz: EINBAU_EBENE},
     b: {komponente: grundplatte, feature: f1, flaeche: "-y"}, ausrichtung: gleich}
  - {id: v35, typ: konzentrisch, a: {komponente: scheibe_mutter, referenz: EINBAU_ACHSE},
     b: {komponente: unterteil, feature: f5, instanz: je, achse: true}}
  - {id: v36, typ: deckungsgleich, a: {komponente: mutter, referenz: EINBAU_EBENE},
     b: {komponente: scheibe_mutter, referenz: EINBAU_EBENE_2}, ausrichtung: gleich}
  - {id: v37, typ: konzentrisch, a: {komponente: mutter, referenz: EINBAU_ACHSE},
     b: {komponente: unterteil, feature: f5, instanz: je, achse: true}}
pruefung:
  huellquader: [200, 113, 100]
  masse_pruefen:
    - {was: Achshöhe Unterteil, von: {komponente: grundplatte, feature: f1, flaeche: "-y"}, zu: {komponente: unterteil, referenz: TRENNEBENE}, soll: "=H"}
    - {was: Deckel auf der Trennebene, von: {komponente: deckel, referenz: TRENNEBENE}, zu: {komponente: grundplatte, feature: f1, flaeche: "-y"}, soll: "=H"}
    - {was: Stift bündig, von: {komponente: stift.1, referenz: EINBAU_EBENE_1}, zu: {komponente: grundplatte, feature: f1, flaeche: "-y"}, soll: 0}
```

- [ ] **Step 5: `tests/referenz/stehlager/eingabe/beschreibung.md`**

```markdown
# Stehlager (Referenz Stufe 3b)

Geteiltes Stehlager für eine Welle Ø 40 auf einer Grundplatte 200 × 100 × 20 (Stahl S235, 1.0038).

- Lagerunterteil: Fuß 160 × 60 × 20, Lagerkörper 90 × 50, Lagerachse 50 über der Fußunterseite, also 70 über der
  Grundplatten-Unterseite. Lagerbohrung Ø 40 je zur Hälfte in Unterteil und Deckel.
- Lagerdeckel 90 × 50 × 30, mit zwei Zylinderschrauben ISO 4762 M8 × 35 (Abstand 65) in Gewinde M8 des Unterteils
  (Gewindetiefe 16), Köpfe versenkt.
- Unterteil auf der Grundplatte: zwei Durchsteckverschraubungen ISO 4762 M10 × 55 (Abstand 120) mit je einer Scheibe
  ISO 7089 unter Kopf und Mutter und einer Mutter ISO 4032; zentriert mit zwei Zylinderstiften ISO 8734 8 × 30
  (Abstand 70), bündig mit der Grundplatten-Unterseite.
- Alle Teile voll bestimmt, keine Überlappung außer den Gewindepaarungen, Einschraublänge nicht über der Gewindetiefe.
```

- [ ] **Step 6: Unit-Test `tests/baugruppe/test_stehlager_spec.py` (neu)**

```python
import json
from pathlib import Path

from swki.cli import main

STEHLAGER = Path(__file__).resolve().parents[1] / "referenz" / "stehlager" / "stehlager.yaml"


def test_stehlager_ist_gueltig(capsys):
    code = main(["validieren", str(STEHLAGER)])
    daten = json.loads(capsys.readouterr().out)
    assert code == 0, daten
    assert (daten["komponenten"], daten["verknuepfungen"]) == (15, 30)
```

Run: `.venv\Scripts\python.exe -m pytest -q` → **566 passed** (565 + 1).

- [ ] **Step 7: `tests/referenz/test_referenzen.py`** – Stehlager aufnehmen

```python
@pytest.mark.parametrize(("ordner", "spec"), [
    ("buchse", "buchse.yaml"),
    ("formplatte", "formplatte_ds.yaml"),
    ("auswerferhalteplatte", "auswerferhalteplatte.yaml"),
    ("stehlager", "stehlager.yaml"),
])
```

- [ ] **Step 8: Live – Referenz**

Vorbedingungen (eine Instanz, `False 1`, Private Bytes; bei > 3 GB vorher Neustart durch den Controller). Run: `.venv\Scripts\python.exe tests\live_einzeln.py tests\referenz\test_referenzen.py --zeit 600` → 4/4 OK.

Schlägt das Stehlager fehl: nur den **Bauweg** nachbessern (Verknüpfungsreferenzen, Ausrichtungen, Reihenfolge, Feature-Reihenfolge der Teile), nie Parameter, Normteile oder `pruefung` (Freigabe). Jede Änderung mit Grund in den Bericht. Bleibt ein Mangel, der eine Anforderung betrifft (z. B. Hülle wegen Spike-Zeile 14): anhalten, Controller entscheidet.

- [ ] **Step 9: Live – Negativfälle `tests/live/test_live_stehlager.py` (neu)**

```python
"""Live: Negativfälle am Stehlager (Spec 3b §14) – zu lange Schraube, Überlappung, unterbestimmte Komponente, manuelle
Änderung an einem gebauten Teil der Baugruppe."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from swki.auftrag import lauf_ordner
from swki.cli import main
from swki.konfig import lade_rechner
from tests.live.test_live_aenderungen import _setze_parameter

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-STEHLAGER"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "stehlager"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def auftrag(tmp_path):
    ordner = tmp_path / AUFTRAG
    shutil.copytree(REFERENZ, ordner)
    yield ordner
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _aendere(ordner: Path, aendern) -> Path:
    pfad = ordner / "stehlager.yaml"
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    aendern(spec)
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def _komponente(spec: dict, kid: str) -> dict:
    return next(k for k in spec["komponenten"] if k["id"] == kid)


def _baue_und_pruefe(capsys, pfad: Path) -> dict:
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, bau
    return _lauf(capsys, "pruefen", str(pfad))[1]


def _maengel(bericht: dict) -> dict:
    return {m["pruefung"]: m for m in bericht["maengel"]}


def test_zu_lange_deckelschraube(capsys, auftrag):
    pfad = _aendere(auftrag, lambda s: _komponente(s, "deckelschraube").update(quelle={"normteil": "ISO 4762 M8x40"}))
    maengel = _maengel(_baue_und_pruefe(capsys, pfad))
    assert "Einschraublänge 18.60" in maengel["gewinde:deckelschraube.1"]["beschreibung"], maengel


def test_ueberlappung(capsys, auftrag):
    pfad = _aendere(auftrag, lambda s: _komponente(s, "stift").update(quelle={"normteil": "ISO 8734 8x40"}))
    maengel = _maengel(_baue_und_pruefe(capsys, pfad))
    assert {"stift.1", "unterteil"} <= set(maengel["kollision"]["knoten"]), maengel


def test_unterbestimmte_komponente(capsys, auftrag):
    pfad = _aendere(auftrag, lambda s: s.update(verknuepfungen=[v for v in s["verknuepfungen"] if v["id"] != "v3"]))
    maengel = _maengel(_baue_und_pruefe(capsys, pfad))
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
    eintrag = next(e for e in daten["geaendert"] if e["datei"] == f"{AUFTRAG}_Grundplatte.sldprt")
    assert eintrag["parameter"] == [{"name": "L", "soll": 200, "ist": 210.0}]
```

Run (Dateien einzeln, zwischen den Tests Speicher prüfen; der Controller startet SolidWorks bei ca. 4 GB neu): `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_stehlager.py --zeit 600` → 4/4 OK.

- [ ] **Step 10: Commit (Implementer), dann anhalten**

```powershell
git add tests/referenz/stehlager tests/referenz/test_referenzen.py tests/baugruppe/test_stehlager_spec.py tests/live/test_live_stehlager.py
git commit -m "referenz: Stehlager (Stufe 3b) mit Negativfällen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Status DONE_WITH_CONCERNS „Prüfer-Urteil ausstehend“; im Bericht: Lauf-Ergebnisse, Gewindepaarungen (Einschraublänge, Volumen ist/soll), Private Bytes, jede Bauweg-Änderung.

- [ ] **Step 11 (Controller): Stehlager als Auftrag mit Prüfer-Urteil**

1. `tests/referenz/stehlager/` nach `auftraege/REF-stehlager/` kopieren (nicht ins Git).
2. `swki validieren` → `swki freigeben` → `swki bauen` → `swki pruefen` (je mit `auftraege/REF-stehlager/stehlager.yaml`).
3. Prüfer-Agent (`subagent_type: pruefer`) mit: Eingabeordner `auftraege/REF-stehlager/eingabe/`, freigegebene Specs (`stehlager.freigegeben.yaml`, `grundplatte.freigegeben.yaml`, `unterteil.freigegeben.yaml`, `deckel.freigegeben.yaml`), Prüfbericht `protokolle/stehlager.lauf-<n>.pruefbericht.json`, Screenshot-Ordner des Laufs. Urteil unverändert nach `protokolle/stehlager.lauf-<n>.pruefer.json`.
4. `swki status` → `bestanden`; sonst nachbessern (Implementer, nur Bauweg) bis zur Laufgrenze. `swki bericht` → `bericht.md`.
5. Ergebnis (Urteil, Läufe, Screenshots-Pfade) in den Bericht für Task 12.

---

### Task 12: Skills, Prüfer, CLAUDE.md, Design, Ergebnisse, Regression

**Files:**
- Create: `.claude/skills/baugruppe/SKILL.md`, `docs/stufe3b/ergebnisse.md`
- Modify: `.claude/skills/konstruieren/SKILL.md`, `.claude/skills/normteile/SKILL.md`, `.claude/agents/pruefer.md`, `CLAUDE.md`, `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`

- [ ] **Step 1: `.claude/skills/baugruppe/SKILL.md` (neu)**

```markdown
---
name: baugruppe
description: Konstruiert eine statische Baugruppe in SolidWorks aus Eigenteilen und Normteilen – Teil-Specs und Baugruppen-Spec schreiben, validieren, eine Freigabe, bauen, prüfen (Verknüpfungen, Bestimmtheit, Kollision, Gewinde, Lage, Teilprüfungen), Prüfer, nachbessern, Bericht. Verwenden, wenn der Nutzer mehrere Teile zusammenbauen, verschrauben, verstiften oder eine Baugruppe ändern will.
---

# Baugruppe (statisch, Stufe 3b)

Spec: `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md`. Befehle wie beim Teil
(`.venv\Scripts\python.exe -m swki …`, JSON). Längen mm, Winkel Grad. Vorlage: `tests/referenz/stehlager/`.

## 1. Auftrag
- `auftraege/<auftrag>/` mit `eingabe/`, einer Baugruppen-Spec und den Teil-Specs der Eigenteile (Teil-Format,
  Regeln aus dem Skill `konstruieren`, Abschnitt 2).
- Normteile nie als Teil-Spec: in der Baugruppe als `quelle: {normteil: "<Norm> <Größe>"}` (Skill `normteile`).

## 2. Baugruppen-Spec
- `komponenten`: `id`, `quelle` (`{teil: <datei.yaml>}` | `{normteil: "ISO 4762 M8x30", variante?}`), genau eine
  `fixiert: true` (ihr Ursprung = Baugruppenursprung), `je_position: {komponente, feature}` für eine Instanz je
  Position einer `normbohrung`/`bohrung` (Instanzen `<id>.1 …`).
- `verknuepfungen`: `deckungsgleich`, `konzentrisch`, `parallel`, `senkrecht`, `abstand` (`wert`), `winkel` (`wert`).
  `ausrichtung: gleich | entgegengesetzt` (Normalen nach dem Verknüpfen gleich- bzw. gegensinnig; Flächennormalen
  zeigen aus dem Material, Bezugsebenen haben die Normale ihrer Basis) – Pflicht außer bei `konzentrisch`.
- Referenzen: `{komponente, referenz}` (bei Normteilen nur `EINBAU_*`, Tabelle im Skill `normteile`),
  `{komponente, feature, flaeche}`, `{komponente, feature, instanz, achse}`, `{komponente, feature, instanz, flaeche}`
  (z. B. Senkungsgrund), `{komponente, ebene}`, `{komponente, nahe}` (Teilkoordinaten, nur als Rückfall).
  `instanz: je` = Position der jeweiligen Instanz.
- Flächen, die ein späteres Feature teilt (Trennfläche mit Lagerbohrung), über ein benanntes `referenz`-Feature der
  Teil-Spec ansprechen.
- Je Normteil: **Ebene vor Achse** (erst die Auflage mit `ausrichtung`, dann `konzentrisch`); `drehung_sperren` ist
  bei Normteilen Vorgabe – jede Komponente muss voll bestimmt sein (sonst `freiheitsgrade: {<id>: unterbestimmt}`
  mit Begründung beim Nutzer).
- Ein Eigenteil richtet man mit Auflage + **eine** konzentrische Bohrung + `parallel` aus (eine zweite konzentrische
  Bohrung kann überbestimmen, Spike S12).
- Anforderungen als `parameter` (`wert: "=S"`); `pruefung`: `huellquader`, `masse_pruefen` (Messpunkte mit
  `komponente`, bei `je_position` die Instanz `stift.1`), optional `masse` (kg). Kollision, Bestimmtheit, Stückliste
  und Teilprüfungen laufen immer.

## 3. Validieren, Freigabe
- `swki validieren <baugruppe.yaml>` (prüft auch alle Teil-Specs, die Normteile und die Passung Normteil ↔ Bohrung)
  bis `"gueltig": true`; `hinweise` abarbeiten wie beim Teil.
- Dem Nutzer zeigen: Teile (Parameter, Material), Normteile (Norm, Größe, Variante, Anzahl), Verknüpfungen in Worten,
  Prüfwerte. Erst nach ausdrücklichem OK: `swki freigeben <baugruppe.yaml>` – **eine** Freigabe für alles.
- Verknüpfungen sind Bauweg (nachbesserbar); Komponenten, Parameter, `freiheitsgrade`, `pruefung` und die
  Anforderungen der Teil-Specs nicht (sonst `FREIGABE_VERALTET`).

## 4. Bauen, prüfen, Prüfer
- `swki bauen <baugruppe.yaml>`: baut alle Eigenteile frisch, holt die Normteile, kopiert sie in den Lauf, fügt ein,
  verknüpft. Fehlercodes: `TEIL_BAU` (Knoten `<komponente>/<feature>` – Bauweg der Teil-Spec nachbessern),
  `KOMPONENTE_FEHLER`, `VERKNUEPFUNG_FEHLER` / `REFERENZ_*` (Knoten `v<n>[.<i>]` – Referenz, Ausrichtung oder
  Reihenfolge nachbessern), Normteil-Codes wie im Skill `normteile`.
- **`MANUELL_GEAENDERT`:** jemand hat Dateien des letzten Laufs geändert. `swki aenderungen <spec>` zeigt die
  Parameterdifferenz. Dem Nutzer zeigen und fragen (eine Frage, Empfehlung „übernehmen“): übernehmen → Spec ändern,
  validieren, neu freigeben; verwerfen → nur auf ausdrückliche Anweisung `swki bauen --verwerfen`.
- `swki pruefen <baugruppe.yaml>` → Prüfbericht mit `verknuepfungen`, `bestimmtheit`, `stueckliste`, `kollision`,
  `gewinde:<schraube>` (Einschraublänge, Volumen ist/soll), `mass:*`, `huellquader`, Teilprüfungen
  `<komponente>: <prüfung>`.
- Prüfer-Agent (`subagent_type: pruefer`) mit Eingabeordner, allen freigegebenen Specs (Baugruppe und Teile),
  Prüfbericht und Screenshot-Ordner; Urteil unverändert nach `protokolle/<spec>.lauf-<n>.pruefer.json`.

## 5. Schleife und Bericht
- `swki status <spec>` und `swki bericht <spec>` wie beim Teil (Skill `konstruieren`, Abschnitte 6–7).
- Nachbessern nur am Bauweg; hält Claude eine Anforderung für falsch (z. B. Schraube zu lang), den Nutzer fragen.
```

- [ ] **Step 2: `.claude/skills/konstruieren/SKILL.md`**

Unter „## 1. Auftrag anlegen“ ergänzen: „- Mehrere Teile, die zusammengebaut werden: Skill `baugruppe` (eine Freigabe für Baugruppe und Teile).“
Unter „## 5. Bauen, prüfen, Prüfer“ als ersten Punkt ergänzen: „- Meldet `swki bauen` **`MANUELL_GEAENDERT`**, hat jemand die Dateien des letzten Laufs geändert: `swki aenderungen <spec>` zeigt die Parameterdifferenz; dem Nutzer zeigen und fragen (übernehmen → Spec ändern, neu freigeben; verwerfen → nur auf ausdrückliche Anweisung `swki bauen --verwerfen`). Nie still neu bauen.“

- [ ] **Step 3: `.claude/skills/normteile/SKILL.md`** – Abschnitt nach „## Abrufen“

```markdown
## Einbaureferenzen (für Baugruppen)
Achse = Modell-Y, Auflage auf y = 0; Bezugsebenen haben die Normale +y.

| Norm | Körper | Referenzen |
|---|---|---|
| ISO 4762 | Kopf y 0…k, Schaft y < 0 | `EINBAU_ACHSE`, `EINBAU_EBENE` (Kopfunterseite) |
| ISO 4032 | y 0…m | `EINBAU_ACHSE`, `EINBAU_EBENE` (eine Auflagefläche; beide Seiten gleich) |
| ISO 7089 | y 0…h | `EINBAU_ACHSE`, `EINBAU_EBENE` (y = 0), `EINBAU_EBENE_2` (y = h, Gegenseite: Kopf/Mutter) |
| ISO 8734 | y 0…l | `EINBAU_ACHSE`, `EINBAU_EBENE_1` (y = 0), `EINBAU_EBENE_2` (y = l) |
```

- [ ] **Step 4: `.claude/agents/pruefer.md`**

`description` um „… gebaute SolidWorks-Teile und Baugruppen …“ ergänzen. Nach „## Checkliste“ einen Abschnitt einfügen:

```markdown
## Zusätzlich bei Baugruppen (`art: baugruppe`)
Du bekommst alle freigegebenen Specs (Baugruppe und Teile). Knoten sind Instanzen (`deckelschraube.2`),
Verknüpfungen (`v11.1`) oder Teil-Knoten (`deckel/f4`).
1. Jede Komponente ist vorhanden und plausibel gelegen (Bilder, `stueckliste`, `mass:*`); nichts schwebt oder steckt
   verdreht bzw. spiegelverkehrt.
2. Verbindungen vollständig: Kopf auf Auflage bzw. Scheibe, Scheibe unter Kopf und Mutter, Mutter auf der Scheibe,
   Stifte eingesteckt; keine Schraube ohne Gegenstück.
3. `gewinde:*`: Einschraublänge fachlich ausreichend (Stahl etwa ≥ 1·d, Grauguss ≥ 1,25·d, Aluminium ≥ 2·d) und nicht
   über der Gewindetiefe.
4. `bestimmtheit` und `kollision` ok; jede Teilprüfung (`<komponente>: …`) ok.
```

- [ ] **Step 5: `CLAUDE.md`**

Kopfzeile „Stand:“ ersetzen durch: „Stand: Stufe 3b (Baugruppen statisch) umgesetzt – Ergebnisse: docs/stufe3b/ergebnisse.md. Nächster Schritt: Stufe 4 (mechanische Abläufe): Brainstorming → Spec → Plan.“ Und nach „## Normteile (Stufe 3a)“ einfügen:

```markdown
## Baugruppen (Stufe 3b)
- Baugruppen über den Skill `baugruppe`: Baugruppen-Spec nach `schema/baugruppe.schema.json` und Teil-Specs im selben
  Auftragsordner; **eine** Freigabe (`swki freigeben <baugruppe.yaml>`) für alles. Verknüpfungen sind Bauweg.
- Normteile kommen über `swki normteil hole` und werden in den Lauf-Ordner kopiert; die Baugruppe verweist nie auf die
  Bibliothek.
- Die Spec ist die Quelle: `MANUELL_GEAENDERT` heißt, jemand hat gebaute Dateien geändert → `swki aenderungen`, Nutzer
  fragen; `swki bauen --verwerfen` nur auf ausdrückliche Anweisung. Gilt auch für Einzelteile.
- Regressions-Suite enthält das Stehlager (`tests/referenz/stehlager/`).
```

- [ ] **Step 6: Design-Dokument `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`**

- §4 „### Baugruppe“: Vorspann „**Stand Stufe 3b (2026-10-03):** Format, Referenzen und `je_position` siehe [2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md); `bewegungen`, `treibend` und gezählte `freiheitsgrade` folgen in Stufe 4.“ vor das Beispiel setzen; das Beispiel bleibt als Ausblick auf Stufe 4.
- §6 Baugruppe-Zeile ergänzen: „(Stand 3b: Gewindepaarungen über das Ringvolumen, Teilprüfung je Eigenteil, Lage über `masse_pruefen`; Änderungserkennung vor jedem Lauf.)“
- §11 Zeile 3b: Inhalt „Baugruppen statisch: Standardverknüpfungen, Bestimmtheit, statische Kollision, Änderungserkennung – Design: [2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md)“; Fertig, wenn „Referenz *Stehlager* besteht (Code-Prüfungen und Prüfer); Buchse, Formplatte und Auswerferhalteplatte bestehen weiter“.

- [ ] **Step 7: `docs/stufe3b/ergebnisse.md` (neu)**

Aufbau wie `docs/stufe3a/ergebnisse.md`: Fertig-Kriterium (Spec 3b §16) mit Beleg; Stand und Commits je Task; Unit-Tests (Zahl je Task, Endstand); Live-Ergebnisse je Datei mit Private Bytes vorher → nachher; Spike S12 (je Tabellenzeile Antwort und Beleg); Stehlager (Läufe, Gewindepaarungen mit Einschraublänge und Volumen ist/soll, Prüfer-Urteil); Präzisierungen gegenüber der Spec (die zehn aus dem Plan, mit Bestätigung oder Abweichung); Entscheidungen während der Umsetzung (Ledger); Offene Punkte (u. a. `c` bei ISO 8734 nur über das Volumen, Gewinde `durch` ohne Volumenprüfung, Rechner B, Stufe 4).

- [ ] **Step 8: Gesamtlauf**

Run: `.venv\Scripts\python.exe -m pytest -q` → grün (566 passed; Zahl berichten).
Run: `.venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.
Run: `.venv\Scripts\python.exe -m swki normteil tabellen-pruefen` → `"gueltig": true`.
Live-Regression (eine Instanz, `False 1`, dateiweise, Speicher beachten, Neustarts durch den Controller): `tests\referenz` (4), `tests\live\test_live_baugruppe.py`, `test_live_aenderungen.py`, `test_live_bauen.py`, `test_live_pruefen.py`, `test_live_muster.py`, `test_live_referenz.py`, `test_live_durchmesser.py` → alle OK.

- [ ] **Step 9: Commit**

```powershell
git add .claude/skills/baugruppe/SKILL.md .claude/skills/konstruieren/SKILL.md .claude/skills/normteile/SKILL.md .claude/agents/pruefer.md CLAUDE.md docs/superpowers/specs/2026-09-26-solidworks-ki-design.md docs/stufe3b/ergebnisse.md
git commit -m "docs: Skill baugruppe, Prüfer, CLAUDE.md, Design §4/§6/§11, Ergebnisse Stufe 3b" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 10: Übergabe (mit Nutzer)**

Kein Push ohne Rückfrage: Testzahlen, Live-Ergebnis, Stehlager-Urteil, Präzisierungen (besonders Nr. 3: `c` bei ISO 8734 nicht direkt gemessen) zeigen und fragen, ob gepusht und ein Pull Request angelegt werden soll.

---

## Abdeckung (Selbstprüfung)

| Spec | Task |
|---|---|
| §2 Referenz Stehlager | 11 |
| §2/§6 eine Freigabe, Verknüpfungen als Bauweg | 4 |
| §2/§7 Normteile in den Lauf kopiert, Bibliothek nur gelesen | 8 |
| §2/§4.2 `je_position` | 2, 3 |
| §2/§4.3 Referenzarten (inkl. Instanzfläche) | 2 (Schema), 3 (Plausibilität), 7 (Auflösung) |
| §2/§8 Änderungserkennung (Teile und Baugruppen), `swki aenderungen`, `--verwerfen` | 5, 10 (Verknüpfungswerte), 11 (live Baugruppe) |
| §2 Bestimmtheit, Drehung sperren | 2 (Vorgabe), 7 (AddMate5), 9 (Bewertung) |
| §2/§9.3 Kollision, Gewindepaarung | 9, 10 (präzisiert: über die Lage) |
| §2/§9 Umfang der Prüfung, ein Prüfer | 9, 10, 11, 12 (pruefer.md) |
| §2 Skill `baugruppe` | 12 |
| §3 Bausteine, Weichen nach `art` | 2–5, 8, 10 |
| §4 Format (Komponenten, Verknüpfungen, `freiheitsgrade`, `parameter`, `pruefung`) | 2, 3, 9 |
| §5 Validieren (Teil-Specs, Normteile, Passung, Hinweise) | 2, 3 |
| §7 Bauen (Ablauf, Fehlercodes, Protokoll, SHA-256) | 5, 7, 8 |
| §9 Prüfen (Verknüpfungen, Bestimmtheit, Kollision, Stückliste, Teilprüfung, Lage, Screenshots) | 9, 10 |
| §10 Prüfer, Schleife, Bericht | 10, 11, 12 |
| §11 Fehlercodes | 2 (Konstanten), 5, 7, 8 |
| §12 Folgen für die Normteile | 6 (präzisiert: `c` nur über das Volumen) |
| §13 Spike S12 | 1 |
| §14 Tests (unit, live, Negativfälle) | 2–11 |
| §15 Einbindung (Skills, Prüfer, CLAUDE.md, Design, Ergebnisse) | 12 |
| §16 Fertig-Kriterium | 11, 12 |
| §17 Reihenfolge | Task-Reihenfolge (Bewertung als eigener Task vor dem Prüfen) |
| §18 Nicht in 3b | Global Constraints |
