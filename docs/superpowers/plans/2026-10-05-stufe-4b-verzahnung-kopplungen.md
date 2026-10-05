# Stufe 4b – Verzahnung und Kopplungen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** swki baut Teile mit Evolventenverzahnung (geradverzahntes Außen-Stirnrad, Zahnstange; Feature `verzahnung`) und prüft sie (Kopf-/Fußkreis, Zähnezahl, Zahnweite); Baugruppen koppeln Bewegungen über Zahnrad- und Zahnstangenverknüpfungen (Zahnphase beim Bau, Übersetzung aus den Zähnezahlen), und `swki pruefen` belegt Eingriff, gekoppelte Freiheitsgrade, strenge Kollision im Eingriff und den Sollweg je Stellung für alle Bewegungen.

**Architecture:** Etappe 1 (Tasks 1–6): reines Geometrie-Modul `swki/verzahnung.py` (Bezugsprofil DIN 867, Profil aus Linien/Bögen/Splines, Zahnweite, Lage im Teil), Schema und `validieren`, Handler `swki/compiler/handler/verzahnung.py` (Skizze mit fixierten Elementen + Aufsatz), Teilprüfung `verzahnungen` (IMeasure). Etappe 2 (Tasks 7–15): reine Kopplungsrechnung `swki/baugruppe/kopplung.py` (Graph, Übersetzung, Zahnphase, Eingriff, Drehung), Format und Plausibilität, Sollweg in `swki/baugruppe/bewegung.py`, SolidWorks-Schicht (`CreateMate` mit Gear-/RackPinion-FeatureData, `SetTransformAndSolve2` für die Phase), Prüfen (`eingriff:<id>`, unterdrückte Verknüpfungen, Bilder je Kopplung), Referenz *Zahnstangentrieb*, Negativfälle, Doku.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) für Spikes und Live-Tests.

**Spec:** `docs/superpowers/specs/2026-10-05-stufe-4b-verzahnung-kopplungen-design.md` (mit dem Nutzer abgestimmt, 2026-10-05). Kontext: Spec 4a `docs/superpowers/specs/2026-10-03-stufe-4a-bewegungen-design.md`, Ergebnisse 4a `docs/stufe4a/ergebnisse.md`, Spec 3b, Gesamtdesign `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`.

**Vorab geprüft (2026-10-05):** Der gesamte Plan-Code ohne SolidWorks wurde in einem Wegwerf-Worktree Task für Task angewendet (erst die Tests, RED-Lauf, dann die Umsetzung, GREEN-Lauf, ganze Suite, `swki api pruefe-code swki spikes tests/live`). Jede Ersetzung traf genau einmal, alle Testzahlen unten sind gemessen, `pruefe-code` blieb ohne Befund. Die Referenz-Specs und die Getriebeprobe validieren ohne Befund und ohne Hinweis. Ungeprüft (braucht SolidWorks): die Spikes, der Handler, die Messung, die SolidWorks-Schicht der Kopplungen und alle Live-Tests – dafür die Tabellen „Abhängigkeiten vom Spike“.

## Präzisierungen gegenüber der Spec (vom Planer, bindend für diesen Plan)

1. **Modulnamen:** Das Geometrie-Modul heißt `swki/verzahnung.py` (nicht `swki/wissen/…`: `wissen/` hält nur Daten); es enthält auch das Lagemodell `Verzahnung`/`verzahnung_im_teil` (Teilkoordinaten aus der Spec). Die Kopplungsrechnung steht in `swki/baugruppe/kopplung.py`.
2. **Reihenfolge:** Die reine Rechnung kommt vor ihren Spike (Task 1 vor S14a, Task 7 vor S14b), weil die Spikes sie brauchen und sie von keiner Spike-Antwort abhängt. Spike S14b läuft vor Format und Plausibilität der Baugruppe (Task 9); er lädt die Probe deshalb ohne `lade_baugruppe`.
3. **Zahnfuß vereinfacht (Spec §4.2):** Die Evolvente beginnt bei `r_start = max(r_b, √(r_f² + 2·r_f·ρ_f))`. Darunter läuft die Flanke radial bis zum Berührpunkt der Fußrundung; die Fußrundung (ρ_f = 0,38·m) berührt die radiale Linie und den Fußkreis. Liegt `r_start` über `r_b` (z ≥ 42), entsteht dort ein flacher Knick; er liegt unter dem aktiven Profil der Referenzpaarungen. Die Profilfläche wird mit 200 Stützpunkten je Flanke gerechnet.
4. **Zahnstange (Spec §4.2):** Das Zahnband besteht aus **einer geschlossenen Kontur je Zahn** (Fußlinie unter dem Zahn, Fußrundungen, Flanken, Kopflinie). Eine einzige Kontur entartet, weil die Fußlinien zwischen den Zähnen mit der Schlusslinie zusammenfallen; diese Fußlinien gehören zum Rücken. Der Rücken muss deshalb genau bis an die Fußlinie reichen, sonst meldet `koerper` zwei Körper (Skill `konstruieren`). Die Teilprüfung misst bei der Zahnstange die **Kopflinie** statt der Zahnhöhe (die Fußlinie ist eine Fläche des Rückens).
5. **Zusätzlicher Befund `VERZAHNUNG_GEOMETRIE`** in `validieren`, wenn das vereinfachte Profil nicht konstruierbar ist (Zahn spitz, Lücke zu eng). Zusätzlich zu Spec §4.3: `winkel` nur beim Stirnrad (Bereich [0, 360)), `kopf` nur bei der Zahnstange.
6. **`pi` schon in Etappe 1 (Task 3):** Die Länge der Zahnstange braucht sie (`=Z*pi*M`). `pi` ist kein Parametername (Befund in Teil und Baugruppe).
7. **Zahnphase (Spec §5.4.2):** Seite a wird mit `SetTransformAndSolve2` auf die mit `kopplung.drehe` gerechnete Lage gesetzt (Annahme Spike S14b Zeile 7; `AddMate5 … ForPositioningOnly` ist die Alternative). Nachgerechnet wird mit `TOL_PHASE = 1e-3` Teilung.
8. **Entitäten der Kopplung:** Stirnrad → koaxiale Zylinderfläche (Fußkreis), aufgelöst wie `{feature, instanz: 1, achse: true}`; Zahnstange → gerade Kante einer Kopffläche entlang der Zahnreihe. Zahnrad: `GearRatioNumerator`/`Denominator` = Teilkreis-Ø der Seiten a/b in m (wie das API-Beispiel); Zahnstange: Vorauswahl Zahnstange Marke 64, Ritzel Marke 128, `DiameterType` 0 (Teilkreis), `DiameterVal` = m·z_a.
9. **Richtung (Spec §5.4.4):** `sw_baugruppe.REVERSE = {"zahnrad": False, "zahnstange": False}` – Annahme Spike S14b Zeile 6: SolidWorks rechnet mit `Reverse = False` die physikalisch richtige Richtung (Außenräder gegensinnig, Ritzel rollt ab). Weicht der Spike ab, setzt der Ledger die Konstante bzw. eine Formel aus der Geometrie.
10. **Gekoppelte Freiheitsgrade (Spec §5.6.1):** `Bewegung.gekoppelt` kommt aus dem Kopplungsgraph (`kopplung.gekoppelte` ab der bewegten Komponente samt Gruppe); `fahre` liest den Status ohnehin für alle Instanzen.
11. **Sollweg (Spec §5.6.2/§5.6.3):** je Komponente **eine** Prüfung `sollweg:<Bewegung>:<k>` (Weg der bewegten Komponente, Verschiebungen, Drehungen). Eine Drehung besteht, wenn die Drehmatrix **und** die aufsummierte Drehung um die Endlagen-Achse innerhalb 0,01° liegen. `endlage:` vergleicht zusätzlich die aufsummierte Drehung; `ist` behält `winkel` (0…180°, aus der Matrix) und bekommt `aufsummiert`.
12. **Eingriff (Spec §5.5):** Das Rücklesen steht in `eingriff:<id>`. Fehlt die Kopplung im Modell, prüft `eingriff` nur die Geometrie – sonst stünde Negativfall 3 doppelt da (`verknuepfungen` meldet sie). `Reverse` wird nicht gegen eine Erwartung geprüft; die Richtung belegen Sollweg und Endlage.
13. **`drehmatrix`** wandert nach `swki/baugruppe/geometrie.py` (sonst Kreisimport `bewegung` → `bewertung` → `kopplung` → `bewegung`); `swki.baugruppe.bewegung` importiert sie, der öffentliche Name bleibt.
14. **Unterdrückte Verknüpfungen (Spec §5.5):** `BaugruppenMesswerte.unterdrueckt`; `verknuepfungen` meldet sie als `fehlerhaft: "unterdrückt"`, und `_statisch_fehlerhaft` zählt sie mit (die Bewegungsprüfung läuft dann nicht).
15. **Referenz *Zahnstangentrieb* (Spec §5.1, „Plan legt fest“):** HUB 120, Zahnstange m 2 / z 30, Ritzel z 20 (Ø 40), Räder z 25 und z 50, Achsabstand 75; zwei Lagerböcke (40 × 165 × 20) stehen auf den Leisten, die Wellen liegen übereinander (Achshöhen 77,5 und 152,5 mm), die Räder liegen an der Innenseite des rechten Lagerbocks an (Anlage der Scharniere). Die Lagerböcke sind nicht verschraubt (Spec nennt keine Befestigung, Speicher). Grundplatte und Leisten wie 4a. Werkstoff der Zahnteile 1.0503 (C45, in der SolidWorks-DIN-Datenbank vorhanden).
16. **Minimalprobe „Getriebeprobe“ (Spec §10):** Platte, Zahnstange, ein Lagerbock und beide Wellen der Referenz (`tests/live/getriebeprobe/`); sie deckt beide Kopplungstypen in einer Probe ab und dient Spike S14b und den Live-Tests der Tasks 11/12.
17. **Negativfälle (Spec §10):** monkeypatch der Namen, die `swki.baugruppe.bau` importiert: Fall 1 `phasenwinkel` (+ halbe Teilung an der Antriebswelle) und `TOL_PHASE` (1,0), Fall 2 `sw_baugruppe.REVERSE["zahnrad"]`, Fall 3 `verknuepfungen` (ohne `k2`), Fall 4 `teilkreise` (Zähler × 1,1). E1 verfälscht `swki.compiler.handler.verzahnung.aus_feature` um −0,05 mm an der **Antriebswelle** (Volumen ändert sich nur um −0,13 %, unter der Toleranz 0,5 %).
18. **Bilder je Kopplung (Spec §5.7):** Standardansicht entlang der größten Komponente der Radachse von Seite a, Zoom mit `ViewZoomToSelection` auf beide Komponenten; Name `<kopplung>-eingriff`.
19. **Hüllquader:** Die Referenz prüft [300, 210, 120]; bestimmt von Grundplatte, Lagerböcken und Wellenenden, nicht von Zahnköpfen (deren Box hängt von der Lage der Zähne ab). Teile mit Rädern haben deshalb keinen `huellquader`.
20. **4a-Rest „privater Import“ (Spec §6.4):** In `swki.pruefung.bewertung` heißen die Helfer `eintrag` und `beschreibung` (statt `_pruefung`/`_beschreibung`); die drei Module, die sie nutzen, werden mitgezogen.
21. **Bericht (Spec §5.8, §6.1):** Lauf-Bericht mit `grenz_id` und `bereich`; `bericht.md` mit den Spalten Grenze und Bereich, den Abschnitten „Endlagen und Sollweg“ und „Kopplungen“; der Prüfbericht hat `kopplungen` (je Kopplung Soll, Gelesenes, Achsabstand, Überdeckung).
22. **Modultabelle DIN 780:** Reihe 1 von 0,05 bis 20 mm, abgeglichen mit zwei Quellen; 25 … 50 nur in einer Quelle gelesen und deshalb gesperrt (Kommentar in der Tabelle).

## Global Constraints

- **Umfang 4b:** Feature `verzahnung` (`art: stirnrad | zahnstange`, Bezugsprofil DIN 867, α = 20°, ohne Profilverschiebung, z ≥ 17 beim Stirnrad, Modul DIN 780 Reihe 1, `zahndickenabmass` < 0); Kopplungen `zahnrad` und `zahnstange`; `freiheitsgrade: gekoppelt`; Sollweg je Stellung für alle Bewegungen; 4a-Reste Bericht, abgebrochene Läufe `ok=None`, `GRENZE_REFERENZ`, privater Import. Nicht: Nut, Kurve (4c), Schräg-/Innen-/Kegel-/Schneckenverzahnung, Profilverschiebung, Trochoide, Schraub-/Linearkoppler, Reibrad, Kräfte, Motion-Studien, Speicherpaket, Deferred Minors aus 4a, Rechner B.
- **Etappen:** Etappe 2 (ab Task 7) beginnt erst, wenn Etappe 1 live besteht (Task 6 abgeschlossen, Controller-Entscheidung im Ledger).
- **Freigabe:** Prüfsumme wie 3b/4a (Baugruppe: `art, name, parameter, eigenschaften, komponenten, freiheitsgrade, pruefung`, `bewegungen` wenn vorhanden, plus `teile`). Features, Verknüpfungen und Kopplungen sind Bauweg. Die Verzahnungswerte (Modul, Zähnezahl, Abmaß) schützt die Prüfung `verzahnungen` gegen die freigegebene Kopie.
- **Kein Antrieb beim Bau** (Spike S13c): `bauen` legt keine treibenden Verknüpfungen an; die Zahnphase entsteht durch `SetTransformAndSolve2` vor dem Anlegen der Kopplung. `pruefen` und `aenderungen` speichern nie.
- **Late Binding** (`swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()` (`Transform2`, `GetConstrainedStatus`, `Name2`, `GetDefinition`, `IsSuppressed`, `GetSketchSegments`, `GetEdges`, `GetCurve`, `Distance`, `CreateMeasure` …); nullargumentige Aktionen über `sw_baugruppe.rufe` bzw. `_FlagAsMethod` (`ViewZoomToSelection`).
- **API nachschlagen:** vor jedem **neuen** SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` bzw. `… api enum <Name>` (vorher `PYTHONIOENCODING=utf-8`). `.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` muss ohne Befunde bleiben. Bereits nachgeschlagen (2026-10-05): `ISketchManager.CreateSpline2` (2: PointData, SimulateNaturalEnds; seit 2009, „obsolete“ aber verfügbar), `IAssemblyDoc.CreateMateData` (1: Type; seit 2018), `IAssemblyDoc.CreateMate` (1: MateData; seit 2018), `IGearMateFeatureData.EntitiesToMate/GearRatioNumerator/GearRatioDenominator/Reverse` (Properties, seit 2019), `IRackPinionMateFeatureData.DiameterType/DiameterVal/Reverse` (Properties, seit 2019; `EntitiesToMate` nur mit Index – stattdessen Vorauswahl mit Marke 64 Zahnstange / 128 Ritzel laut API-Hilfe), `swRackPinionMateDistanceOptions_e` (swPinionPitchDiameter 0, swRackTravelPerRevolution 1), `swMateType_e` (swMateGEAR 10, swMateRACKPINION 13), `IModelDocExtension.CreateMeasure` (0), `IMeasure.Calculate` (1: Entities; NULL = Auswahl), `IMeasure.Distance` (Property, −1 wenn ungültig), `IComponent2.SetTransformAndSolve2` (1: XformIn), `IFeature.GetDefinition` (0), `IFeature.IsSuppressed` (0), `IModelDoc2.ViewZoomToSelection` (0).
- **Einheiten:** Spezifikation und Ausgaben in mm und Grad; die API rechnet in m und rad (`mm()`, `grad()`, `in_mm()` aus `swki.verbindung`).
- **Bestand bleibt:** Referenzen *Buchse*, *Formplatte*, *Auswerferhalteplatte*, *Stehlager*, *Linearschlitten* bestehen weiter; Teile ohne Verzahnung und Baugruppen ohne Kopplungen verhalten sich wie bisher (Ausnahmen: die neue Prüfung `sollweg:` je Bewegung, die einheitliche Bewertung abgebrochener Läufe und der Befund `GRENZE_REFERENZ`).
- **Prüfwerte nie an Messwerte anpassen.** Testerwartungen der Negativfälle nie abschwächen; weicht ein Live-Ergebnis ab, anhalten (NEEDS_CONTEXT) und dem Controller den Prüfbericht-Auszug melden. Den Drehsinn der Endlagen nie nachträglich an die Messung anpassen.
- **Sprache:** Code-Bezeichner, Docstrings, Kommentare, Commit-Messages, Berichte auf Deutsch (mit Umlauten in Texten).
- **Tests:** `.venv\Scripts\python.exe -m pytest -q` (ohne SolidWorks; Stand vor dem Plan: **711 passed, 117 deselected**). Jeder Task nennt die erwarteten Zahlen (vorab gemessen); abweichende Zahlen im Bericht begründen. Live-Tests nur einzeln: `.venv\Scripts\python.exe tests\live_einzeln.py <datei::test-id> --zeit 900` mit `PYTHONIOENCODING=utf-8`.
- **SolidWorks-Speicher (Live-Tasks):** Private Bytes messen (`Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`), nicht das Working Set. Vor **jedem** Live-Test mit Baugruppe (Probe, Referenz, Negativfall) frisches SolidWorks: der Implementer meldet BLOCKED (Neustart) mit der Test-ID, **der Controller startet SolidWorks neu** (Ablauf in `docs/superpowers/uebergabe-2026-10-04-stufe4a.md`). Teil-Live-Tests dürfen bis ca. 4 GB Private Bytes in einer Sitzung laufen. Genau eine Instanz (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`); Einstellungen vor und nach Live-Läufen `False 1` (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); print(app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6))"`). Implementer starten oder beenden SolidWorks nie. Keine künstliche CPU-Last.
- **Nur eigene Dokumente** anfassen; speichern nur im `arbeitsordner` aus `config/rechner.yaml`; nie ein SolidWorks-Jahr oder einen Pfad fest in Code schreiben; nie in die Normteilbibliothek schreiben (außer `swki normteil`).
- **Git:** Branch `stufe-4b` (von `plan-stufe-4b`), kleine Commits je Task; Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **kein `git push` ohne Rückfrage**; nichts aus `auftraege/` committen; erzeugte SolidWorks-Dateien nie committen; immer gezielt `git add <dateien>`. `core.autocrlf` ist `true`: neue Dateien und Volltext-Ersetzungen dürfen LF schreiben; Ersetzungen in bestehenden Dateien mit dem Edit-Werkzeug (kein sed auf CRLF-Dateien).
- **Ersetzungen:** „In `<datei>` ersetzen“ heißt: den Block exakt (ohne Zeilenende-Unterschiede) einmal finden und ersetzen. Trifft er nicht genau einmal, anhalten und melden (der Plan wurde so geprüft, dass jeder Block genau einmal trifft).
- **Subagents:** Implementer starten keine Subagents. Prüfer-Agenten startet der Controller. Nie zwei Implementer gleichzeitig, solange SolidWorks läuft.

## Dateistruktur nach diesem Plan

```
swki/verzahnung.py                      neu: Bezugsprofil, Stirnrad/Zahnstange, Profil, Zahnweite, Fläche, Lage im Teil
swki/wissen/module_din780.yaml          neu: Modulreihe 1 (abgeglichen)
schema/teil.schema.json                 + verzahnung (ebene_fest)
swki/spec/{ausdruck,laden,hinweise}.py  pi; Befunde der Verzahnung; Hinweise modul/zaehne/abmass_gross
swki/pruefung/geometrie.py              volumen auto mit Verzahnung
swki/compiler/handler/verzahnung.py     neu: Handler
swki/pruefung/{messen,bewertung}.py     Prüfung verzahnungen; eintrag/beschreibung öffentlich
config/standard.yaml                    + toleranzen.verzahnung_mm
swki/baugruppe/kopplung.py              neu: Graph, Übersetzung, Zahnphase, Eingriff, drehe
swki/baugruppe/geometrie.py             + drehmatrix (aus bewegung.py)
schema/baugruppe.schema.json            + zahnrad, zahnstange, {komponente, feature}, gekoppelt
swki/baugruppe/plausibel.py             Kopplungsbefunde, GRENZE_REFERENZ, pi
swki/baugruppe/bewegung.py              gekoppelte Freiheitsgrade, Sollweg, aufsummierte Drehung, 4a-Reste
swki/pruefung/bericht.py                Grenze/Bereich, Endlagen und Sollweg, Kopplungen
swki/verbindung.py                      + dispatch_array
swki/baugruppe/sw_baugruppe.py          kopple, lies_kopplung, ist_unterdrueckt, setze_lage, REVERSE
swki/baugruppe/{fehler,referenzen,bau}.py   ZAHNPHASE_FEHLER, kopplung_referenz, Zahnphase und Kopplung beim Bau
swki/baugruppe/{bewertung,pruefen,bewegungslauf}.py, swki/pruefung/bilder.py   eingriff, unterdrückt, Bilder
spikes/s14a_verzahnung.py, spikes/s14b_kopplung.py
tests/test_verzahnung.py, tests/test_verzahnung_lage.py, tests/spec/test_verzahnung_spec.py,
tests/pruefung/test_verzahnung_pruefung.py, tests/baugruppe/{test_kopplung,beispiel_kopplung,test_kopplung_plausibel,
test_sollweg,test_sw_kopplung,test_eingriff}.py
tests/live/test_live_verzahnung.py, tests/live/getriebeprobe/, tests/live/test_live_kopplung.py,
tests/live/test_live_zahnstangentrieb.py
tests/referenz/zahnstangentrieb/         Referenz: 7 Teil-Specs, zahnstangentrieb.yaml, eingabe/beschreibung.md
.claude/agents/pruefer.md, .claude/skills/{konstruieren,baugruppe}/SKILL.md, CLAUDE.md, Design §11, Spec 4b (Nachzug)
docs/stufe4b/ergebnisse.md
```

## Abhängigkeiten vom Spike S14a (Task 2)

Der Plan-Code setzt die Spalte „Annahme“ voraus. Weicht der Spike ab, entscheidet der Controller nach der Spalte „sonst“ und hält es im Ledger fest, bevor der betroffene Task beginnt.

| # | Frage | Annahme (Plan-Code) | sonst | betrifft |
|---|---|---|---|---|
| 1 | Spline gegen Polylinie | `CreateSpline2` durch die Punkte, alle Segmente mit `sgFIXED`: Skizzenstatus 3, Aufsatz ok, 1 Körper; größte Abweichung der Flankenfläche von der Soll-Evolvente < 0,002 mm | Status ≠ 3: statt der Segmente alle Skizzenpunkte fixieren (`GetSketchPoints2`); Aufsatz scheitert an offener Kontur (Endpunkte von Spline und Bogen nicht verschmolzen): je Stoßstelle die beiden Punkte mit `sgMERGEPOINTS` verbinden (Ledger); Spline unbrauchbar oder Abweichung ≥ 0,002 mm: Polylinie (`zeichne` erzeugt einen Linienzug, Messung der Zahnweite über die Flächen beider Flanken, Ledger) | 4, 5 |
| 2 | Ganzes Profil in einer Skizze | z = 80: Skizze + Aufsatz < 60 s; Private Bytes je Rad < 300 MB | Lücke + Kreismuster als Handlerweg (Ledger, neuer Plan-Code im Task 4) | 4, 6 |
| 3 | Messung | koaxiale Zylinder: z Kopf- und z Fußflächen; IMeasure-Abstand der Außenflanken = W_k ± 0,005 mm; Zahnstange: z Kopfflächen, je z linke und rechte Flankenebenen, Teilung und Zahndicke ± 0,005 mm | `verzahnung_mm` auf das Doppelte der gemessenen Abweichung, höchstens 0,02 mm (Ledger); darüber: Nutzer fragen | 5 |
| 4 | Radachse als Referenz | `zylinder_zu_punkten(Flächen des Features, [Achspunkt])` liefert die Fußkreisfläche (r 17,5 bei m 2, z 20) | Bezugsachse im Handler anlegen und `{feature, instanz: 1, achse: true}` darauf lenken (Ledger) | 4, 11 |
| 5 | Zeit und Speicher je Radbau | < 15 s und < 300 MB je Rad bis z = 50 | Hinweis im Skill zu großen Zähnezahlen; Referenz bleibt (Ledger) | 6 |
| 6 | Zahnband auf dem Rücken | eine Kontur je Zahn, Rücken bis zur Fußlinie: 1 Volumenkörper | Zahnband 0,01 mm in den Rücken verlängern (Ledger, `Zahnstange.profil`) | 4, 6 |

## Abhängigkeiten vom Spike S14b (Task 8)

| # | Frage | Annahme (Plan-Code) | sonst | betrifft |
|---|---|---|---|---|
| 6 | `CreateMate` | beide Kopplungen angelegt, `IMate2.Type` 13 bzw. 10, Fehlercode 0; `GetDefinition` liefert DiameterVal 40 / DiameterType 0 bzw. Zähler 100 / Nenner 50; mit `Reverse = False` dreht die Ritzelwelle um +z, wenn die Zahnstange nach +x fährt, und die Antriebswelle gegensinnig | Drehsinn falsch: `REVERSE[typ] = True` (Ledger); hängt er von den Entitäten ab: Formel aus der Geometrie (Ledger, Nutzer informieren); `GetDefinition` leer: `lies_kopplung` über `IMate2`-Parameter oder ohne Rücklesen (Ledger, Spec-Nachzug §5.5) | 11, 12 |
| 7 | Zahnphase | `SetTransformAndSolve2` dreht Seite a um ihre Achse; Phasenfehler danach < 1e-3 Teilung | `AddMate5` mit `ForPositioningOnly` und Winkel an zwei Ebenen (Ledger) | 11 |
| 8 | Bestimmtheit mit Kopplungen | Grenze unterdrückt, ohne Antrieb: Zahnstange, Ritzel- und Antriebswelle 2; mit Antrieb: 3 | wie 4a: Mitfahrer melden wie ihr Träger; meldet eine Welle trotz Kopplung 2 mit Antrieb: Nutzer fragen | 10, 12 |
| 9 | Kollision im Eingriff, Zeit, Speicher | in Phase keine Paare über alle 9 Stellungen; halbe Teilung an der Antriebswelle: Paar Antriebswelle/Ritzelwelle mit Volumen > 0; < 3 s und < 50 MB je Schritt | Scheinkollision: Nutzer fragen (Spec-Entscheidung „streng“, Alternativen Abmaß −0,1 oder Volumenschwelle); Zeit/Speicher darüber: Nutzer fragen (Spec §9.9) | 12, 13 |
| 10 | Grenze wirkt durch die Kette | Schritt auf HUB + 3,75: Meldung ≠ None, Zahnstange bleibt bei HUB | wie 4a: Kriterium über die Lage (unverändert) | 12 |
| 11 | Aufsummierte Drehung | Ritzelwelle +171,89° (60/20 rad), Antriebswelle −85,94° bei HUB 60, ± 0,01° | Konvention prüfen, Nutzer informieren | 10, 12 |
| 12 | Bild entlang der Radachse | PNG > 0 Byte, Zoom auf die Auswahl | `ViewZoomtofit2` statt Zoom auf die Auswahl (Ledger) | 12 |
| 13 | Speichern und Öffnen | Kopplungen vorhanden; Zahnstange 30 mm weiter → Ritzelwelle +85,94° ± 0,01° | Nutzer fragen (Datei nach dem Speichern unbrauchbar, vgl. S13c) | 11–13 |

---

# Etappe 1 – Verzahnung im Teil

### Task 1: Geometrie der Verzahnung (`swki/verzahnung.py`, ohne SolidWorks)

**Files:**
- Create: `swki/verzahnung.py`, `swki/wissen/module_din780.yaml`
- Test: `tests/test_verzahnung.py`, `tests/test_verzahnung_lage.py`

**Interfaces:**
- Consumes: `swki.spec.ausdruck.auswerten` (spät importiert in `aus_feature`/`verzahnung_im_teil`).
- Produces (von allen späteren Tasks genutzt):
  - `ALPHA` (rad), `KOPFHOEHE`, `FUSSHOEHE`, `FUSSRUNDUNG` (× m), `Z_MIN = 17`, `FLANKENPUNKTE = 10`, `inv(a)`.
  - `class VerzahnungFehler(ValueError)`.
  - Segmente `Linie(a, b)`, `Bogen(mitte, a, b, gegen_uhrzeigersinn)`, `Spline(punkte)` – Punkte `(u, v)` in mm.
  - `Stirnrad(m, z, abmass)`: `r, rb, ra, rf, rho, tau, s, r_beruehr, r_start, delta`, `psi(rho)`, `pruefe()`,
    `messzaehnezahl()`, `zahnweite()`, `zahnmitte(j, winkel)`, `flankenpunkt(j, seite, rho, mitte, winkel)`,
    `profil(mitte, winkel, n) -> list[list[Segment]]` (eine Kontur), `flaeche()`.
  - `Zahnstange(m, z, abmass)`: `p, s, rho`, `pruefe()`, `zahnmitte(j, u0)`, `profil(mitte, kopf) -> list[list[Segment]]`
    (eine Kontur je Zahn), `flankenmitte(j, seite, u0)`, `flaeche()`.
  - `genormte_module() -> tuple[float, ...]`, `ist_genormt(m) -> bool`, `aus_feature(f, parameter) -> Stirnrad | Zahnstange`.
  - `Verzahnung` (Lage im Teil: `id, geo, mitte, winkel, kopf, ursprung, u, v, normale, breite`; `modell(q)`,
    `richtung(q)`, `bezugspunkt`, `zahnrichtung`, `kopfrichtung`) und `verzahnung_im_teil(f, parameter) -> Verzahnung`.

- [ ] **Step 1: Tests schreiben**

`tests/test_verzahnung.py` anlegen:

```python
"""Geometrie der Evolventenverzahnung (Spec 4b §4.2, §4.5) ohne SolidWorks."""

import math

import pytest

from swki.verzahnung import (ALPHA, Bogen, Linie, Spline, Stirnrad, VerzahnungFehler, Zahnstange, aus_feature,
                             genormte_module, inv, ist_genormt)


def _enden(s):
    return (s.punkte[0], s.punkte[-1]) if isinstance(s, Spline) else (s.a, s.b)


def _geschlossen(kontur, tol=1e-9):
    for s, t in zip(kontur, kontur[1:] + kontur[:1]):
        assert math.dist(_enden(s)[1], _enden(t)[0]) <= tol, (s, t)


def _dicht(kontur, n=400):
    """Kontur als dichter Polygonzug (Bögen fein abgetastet) – unabhängige Flächenrechnung für die Tests."""
    pts = []
    for s in kontur:
        if isinstance(s, Spline):
            pts += list(s.punkte[:-1])
        elif isinstance(s, Linie):
            pts.append(s.a)
        else:
            r = math.dist(s.mitte, s.a)
            wa = math.atan2(s.a[1] - s.mitte[1], s.a[0] - s.mitte[0])
            wb = math.atan2(s.b[1] - s.mitte[1], s.b[0] - s.mitte[0])
            d = (wb - wa) % (2 * math.pi) if s.gegen_uhrzeigersinn else -((wa - wb) % (2 * math.pi))
            pts += [(s.mitte[0] + r * math.cos(wa + d * i / n), s.mitte[1] + r * math.sin(wa + d * i / n))
                    for i in range(n)]
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


def test_evolventenfunktion():
    assert inv(ALPHA) == pytest.approx(0.014904383867, rel=1e-9)


@pytest.mark.parametrize(("z", "k", "w"), [(17, 2, 4.6663), (20, 3, 7.6604), (50, 6, 16.9370)])
def test_zahnweite_tabellenwerte_modul_1(z, k, w):
    # Zahnweiten für m = 1, α = 20°, x = 0 (Tabellenwerte z. B. DIN 3960 / KHK-Tafeln)
    rad = Stirnrad(1.0, z)
    assert rad.messzaehnezahl() == k
    assert rad.zahnweite() == pytest.approx(w, abs=1e-4)


def test_zahnweite_mit_abmass_und_modul():
    ohne, mit = Stirnrad(2.0, 20), Stirnrad(2.0, 20, -0.05)
    assert ohne.zahnweite() == pytest.approx(2 * 7.66044, abs=1e-4)
    assert mit.zahnweite() - ohne.zahnweite() == pytest.approx(-0.05 * math.cos(ALPHA), abs=1e-12)


def test_kreise_stirnrad():
    rad = Stirnrad(2.0, 20)
    assert (2 * rad.r, 2 * rad.ra, 2 * rad.rf) == pytest.approx((40.0, 44.0, 35.0))
    assert 2 * rad.rb == pytest.approx(37.5877, abs=1e-4)
    assert rad.tau == pytest.approx(math.radians(18))


@pytest.mark.parametrize("z", [17, 20, 25, 41, 42, 50, 80])
def test_profil_stirnrad_geschlossen_und_auf_der_evolvente(z):
    rad = Stirnrad(2.0, z, -0.05)
    [kontur] = rad.profil(mitte=(5.0, -3.0), winkel=10.0)
    _geschlossen(kontur)
    splines = [s for s in kontur if isinstance(s, Spline)]
    assert len(splines) == 2 * z
    kopf = [s for s in kontur if isinstance(s, Bogen) and s.mitte == (5.0, -3.0)
            and abs(math.dist(s.mitte, s.a) - rad.ra) < 1e-9]
    assert len(kopf) == z
    for q in splines[0].punkte:  # rechte Flanke von Zahn 1: Winkel zur Zahnmitte = −psi(ρ)
        rho = math.dist(q, (5.0, -3.0))
        phi = math.atan2(q[1] + 3.0, q[0] - 5.0)
        assert phi == pytest.approx(math.radians(10.0) - rad.psi(rho), abs=1e-12)


def test_zahndicke_am_teilkreis():
    rad = Stirnrad(2.0, 20, -0.05)
    links, rechts = rad.flankenpunkt(1, "links", rad.r), rad.flankenpunkt(1, "rechts", rad.r)
    bogen = rad.r * (math.atan2(links[1], links[0]) - math.atan2(rechts[1], rechts[0]))
    assert bogen == pytest.approx(math.pi + -0.05, abs=1e-12)


def test_flaeche_stirnrad_gegen_dichten_polygonzug():
    rad = Stirnrad(2.0, 20, -0.05)
    [kontur] = rad.profil(n=200)
    assert rad.flaeche() == pytest.approx(_dicht(kontur), rel=1e-5)
    assert math.pi * rad.rf ** 2 < rad.flaeche() < math.pi * rad.ra ** 2


def test_radiale_verlaengerung_nur_unter_dem_grundkreis():
    assert any(isinstance(s, Linie) for s in Stirnrad(2.0, 20).profil()[0])   # Grundkreis über der Fußrundung
    assert not any(isinstance(s, Linie) for s in Stirnrad(2.0, 50).profil()[0])  # Evolvente ab der Fußrundung


def test_stirnrad_nicht_konstruierbar():
    with pytest.raises(VerzahnungFehler, match="spitz"):
        Stirnrad(1.0, 20, -1.5).pruefe()
    with pytest.raises(VerzahnungFehler, match="Lücke"):
        Stirnrad(1.0, 20, 1.0).pruefe()


def test_zahnstange_profil():
    st = Zahnstange(2.0, 5, -0.05)
    konturen = st.profil(mitte=(10.0, 20.0))
    assert len(konturen) == 5
    for j, k in enumerate(konturen, start=1):
        _geschlossen(k)
        kopf = k[3]
        assert kopf.a[1] == pytest.approx(22.0) and kopf.b[1] == pytest.approx(22.0)  # Kopflinie v0 + m
        assert k[0].a[1] == pytest.approx(17.5)                                         # Fußlinie v0 − 1,25 m
        assert (kopf.a[0] + kopf.b[0]) / 2 == pytest.approx(10.0 + (j - 1) * 2 * math.pi)
    assert st.flankenmitte(1, "rechts", 10.0) - st.flankenmitte(1, "links", 10.0) == pytest.approx(math.pi - 0.05)
    assert st.flankenmitte(2, "links") - st.flankenmitte(1, "links") == pytest.approx(2 * math.pi)


def test_zahnstange_fussrundung_beruehrt_flanke():
    st = Zahnstange(2.0, 1)
    c, t1, t2 = st._fussrundung(0.0, 1)
    assert math.dist(c, t1) == pytest.approx(st.rho) and math.dist(c, t2) == pytest.approx(st.rho)
    # t1 liegt auf der rechten Flanke u = s/2 − v·tan α
    assert t1[0] == pytest.approx(st.s / 2 - t1[1] * math.tan(ALPHA))
    assert t1[1] == pytest.approx(-2.0, abs=1e-3)  # DIN 867: die Fußrundung endet etwa bei −m


def test_zahnstange_flaeche_und_spiegelung():
    st = Zahnstange(2.0, 3, -0.05)
    assert st.flaeche() == pytest.approx(sum(_dicht(k) for k in st.profil()), rel=1e-6)
    unten = st.profil(mitte=(0.0, 0.0), kopf="-v")
    assert unten[0][3].a[1] == pytest.approx(-2.0)
    assert sum(_dicht(k) for k in unten) == pytest.approx(st.flaeche(), rel=1e-6)


def test_zahnstange_spitz():
    with pytest.raises(VerzahnungFehler, match="spitz"):
        Zahnstange(1.0, 3, -1.3).pruefe()


def test_genormte_module():
    assert genormte_module()[0] == 0.05 and 20.0 in genormte_module()
    assert ist_genormt(2) and ist_genormt(0.7) and not ist_genormt(2.25) and not ist_genormt(25)


def test_aus_feature():
    p = {"M": 2, "Z": 20, "AS": -0.05}
    rad = aus_feature({"art": "stirnrad", "modul": "=M", "zaehne": "=Z", "zahndickenabmass": "=AS"}, p)
    assert rad == Stirnrad(2.0, 20, -0.05)
    st = aus_feature({"art": "zahnstange", "modul": 2, "zaehne": 9, "zahndickenabmass": -0.05}, {})
    assert st == Zahnstange(2.0, 9, -0.05)
```

`tests/test_verzahnung_lage.py` anlegen:

```python
"""Lage eines verzahnung-Features im Teil (swki.verzahnung.verzahnung_im_teil), ohne SolidWorks."""

import pytest

from swki.compiler.skizze import modellpunkt
from swki.verzahnung import Stirnrad, Zahnstange, verzahnung_im_teil

RAD = {"id": "z1", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": 30}}, "mitte": [5, -2],
       "modul": 2, "zaehne": 20, "breite": 16, "zahndickenabmass": -0.05, "winkel": 90}


@pytest.mark.parametrize("orientierung", ["vorne", "oben", "rechts"])
def test_modell_wie_skizze(orientierung):
    f = {**RAD, "ebene": {"versatz": {"ebene": orientierung, "abstand": 30}}}
    vz = verzahnung_im_teil(f, {})
    assert vz.modell((5, -2)) == pytest.approx(modellpunkt(orientierung, 5, -2, 30))


def test_stirnrad():
    vz = verzahnung_im_teil(RAD, {})
    assert vz.geo == Stirnrad(2, 20, -0.05)
    assert vz.bezugspunkt == pytest.approx((5, -2, 30))
    assert vz.zahnrichtung == pytest.approx((0, 1, 0))  # winkel 90°: Zahn 1 auf +v
    assert vz.normale == (0.0, 0.0, 1.0) and vz.breite == (30, 46)


def test_umkehren_dreht_den_breitenbereich():
    assert verzahnung_im_teil({**RAD, "umkehren": True}, {}).breite == (14, 30)


def test_zahnstange_oben_kopf_unten():
    f = {"id": "z2", "art": "zahnstange", "ebene": "oben", "mitte": ["=A", 0], "modul": 2, "zaehne": 9, "breite": 20,
         "zahndickenabmass": -0.05, "kopf": "-v"}
    vz = verzahnung_im_teil(f, {"A": 7})
    assert vz.geo == Zahnstange(2, 9, -0.05)
    assert vz.bezugspunkt == pytest.approx((7, 0, 0))
    assert vz.zahnrichtung == (1.0, 0.0, 0.0)
    assert vz.kopfrichtung == pytest.approx((0, 0, 1))  # oben: v = −z, Kopf −v = +z
```


- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\test_verzahnung.py tests\test_verzahnung_lage.py`
Expected: FAIL – `2 errors` beim Sammeln (`ImportError`, Modul `swki.verzahnung` fehlt).

- [ ] **Step 3: Umsetzen**

`swki/verzahnung.py` anlegen:

```python
"""Evolventenverzahnung (Spec 4b §4.2): geradverzahntes Außen-Stirnrad und Zahnstange mit dem Bezugsprofil DIN 867
(α = 20°, Kopfhöhe m, Fußhöhe 1,25 m, Fußrundung 0,38 m), ohne Profilverschiebung. Reine Geometrie ohne SolidWorks:
Kreise, Zahnweite, Profil als Konturen aus Linien, Bögen und Splines, Profilfläche, Lage der Flanken.

Längen in mm, Winkel im Bogenmaß (Ausnahme: `winkel` der Spec in Grad). Koordinaten (u, v) wie die Skizzen des
Compilers (swki.compiler.skizze). Die Trochoide des Fußes wird vereinfacht: unter dem Grundkreis läuft die Flanke radial
weiter, die Fußrundung ρ_f berührt die radiale Verlängerung und den Fußkreis (Präzisierung 3 des Plans)."""

import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

ALPHA = math.radians(20.0)                           # Eingriffswinkel des Bezugsprofils (DIN 867)
KOPFHOEHE, FUSSHOEHE, FUSSRUNDUNG = 1.0, 1.25, 0.38  # × Modul (DIN 867)
Z_MIN = 17                                           # unterschnittfrei ohne Profilverschiebung
FLANKENPUNKTE = 10                                   # Stützpunkte je Evolventenflanke (Spike S14a Zeile 1)
FLAECHE_PUNKTE = 200                                 # Stützpunkte je Flanke für die Profilfläche
_MODULE = Path(__file__).parent / "wissen" / "module_din780.yaml"

Punkt = tuple[float, float]


class VerzahnungFehler(ValueError):
    """Das Profil lässt sich mit diesen Werten nicht konstruieren (z. B. keine Fußlücke, Zahn spitz)."""


@dataclass(frozen=True)
class Linie:
    a: Punkt
    b: Punkt


@dataclass(frozen=True)
class Bogen:
    mitte: Punkt
    a: Punkt
    b: Punkt
    gegen_uhrzeigersinn: bool  # von a nach b in (u, v)


@dataclass(frozen=True)
class Spline:
    punkte: tuple[Punkt, ...]  # durch alle Punkte, von punkte[0] nach punkte[-1]


Segment = Linie | Bogen | Spline


def inv(a: float) -> float:
    """Evolventenfunktion inv α = tan α − α."""
    return math.tan(a) - a


@cache
def genormte_module() -> tuple[float, ...]:
    """Modulreihe 1 nach DIN 780 (swki/wissen/module_din780.yaml)."""
    return tuple(float(m) for m in yaml.safe_load(_MODULE.read_text(encoding="utf-8"))["reihe_1"])


def ist_genormt(m: float) -> bool:
    return any(abs(m - n) < 1e-9 for n in genormte_module())


def _polar(mitte: Punkt, r: float, phi: float) -> Punkt:
    return (mitte[0] + r * math.cos(phi), mitte[1] + r * math.sin(phi))


def _gegen_uhrzeigersinn(mitte: Punkt, a: Punkt, b: Punkt) -> bool:
    """Drehsinn des kürzeren Bogens von a nach b um mitte (Bögen der Profile sind < 180°)."""
    return (a[0] - mitte[0]) * (b[1] - mitte[1]) - (a[1] - mitte[1]) * (b[0] - mitte[0]) > 0


def _bogen(mitte: Punkt, a: Punkt, b: Punkt) -> Bogen:
    return Bogen(mitte, a, b, _gegen_uhrzeigersinn(mitte, a, b))


@dataclass(frozen=True)
class Stirnrad:
    """Geradverzahntes Außen-Stirnrad: Modul m, Zähnezahl z, Zahndickenabmaß abmass (mm, < 0 für Flankenspiel)."""
    m: float
    z: int
    abmass: float = 0.0

    @property
    def r(self) -> float:
        return self.m * self.z / 2

    @property
    def rb(self) -> float:
        return self.r * math.cos(ALPHA)

    @property
    def ra(self) -> float:
        return self.r + KOPFHOEHE * self.m

    @property
    def rf(self) -> float:
        return self.r - FUSSHOEHE * self.m

    @property
    def rho(self) -> float:
        return FUSSRUNDUNG * self.m

    @property
    def tau(self) -> float:
        """Teilungswinkel 2π/z."""
        return 2 * math.pi / self.z

    @property
    def s(self) -> float:
        """Zahndicke am Teilkreis (Bogen) mit Abmaß."""
        return math.pi * self.m / 2 + self.abmass

    @property
    def r_beruehr(self) -> float:
        """Radius, an dem die Fußrundung die radiale Flankenverlängerung berührt."""
        return math.sqrt(self.rf ** 2 + 2 * self.rf * self.rho)

    @property
    def r_start(self) -> float:
        """Beginn der Evolvente: Grundkreis oder, wenn die Fußrundung höher reicht, deren Berührradius."""
        return max(self.rb, self.r_beruehr)

    def psi(self, rho: float) -> float:
        """Halber Zahndickenwinkel am Radius rho ≥ rb (Winkel von der Zahnmitte zur Flanke)."""
        return self.s / (2 * self.r) + inv(ALPHA) - inv(math.acos(self.rb / rho))

    @property
    def delta(self) -> float:
        """Winkel zwischen der radialen Flankenverlängerung und dem Mittelpunkt der Fußrundung."""
        return math.asin(self.rho / (self.rf + self.rho))

    def pruefe(self) -> None:
        """VerzahnungFehler, wenn das vereinfachte Profil nicht konstruierbar ist."""
        if self.z < 1 or self.m <= 0:
            raise VerzahnungFehler(f"Modul {self.m:g} und Zähnezahl {self.z} ergeben kein Rad")
        if self.r_start >= self.ra:
            raise VerzahnungFehler("die Fußrundung reicht bis an den Kopfkreis")
        if self.psi(self.ra) <= 0:
            raise VerzahnungFehler("der Zahn wird spitz (Kopfdicke ≤ 0)")
        if self.tau - 2 * (self.psi(self.r_start) + self.delta) <= 0:
            raise VerzahnungFehler("zwischen den Fußrundungen bleibt kein Fußkreis (Lücke zu eng)")

    def messzaehnezahl(self) -> int:
        """Messzähnezahl k = round(z·α/π + 0,5) (α im Bogenmaß)."""
        return max(1, round(self.z * ALPHA / math.pi + 0.5))

    def zahnweite(self) -> float:
        """Zahnweite W_k = m·cos α·[π·(k − 0,5) + z·inv α] + A_s·cos α."""
        k = self.messzaehnezahl()
        return self.m * math.cos(ALPHA) * (math.pi * (k - 0.5) + self.z * inv(ALPHA)) + self.abmass * math.cos(ALPHA)

    def zahnmitte(self, j: int, winkel: float = 0.0) -> float:
        """Winkel der Mitte von Zahn j (1 …) gegen +u; winkel = Lage von Zahn 1 in Grad."""
        return math.radians(winkel) + (j - 1) * self.tau

    def flankenpunkt(self, j: int, seite: str, rho: float, mitte: Punkt = (0.0, 0.0), winkel: float = 0.0) -> Punkt:
        """Punkt der Flanke von Zahn j am Radius rho; seite "links" (gegen den Uhrzeigersinn) bzw. "rechts"."""
        phi = self.zahnmitte(j, winkel) + (1 if seite == "links" else -1) * self.psi(rho)
        return _polar(mitte, rho, phi)

    def _flanke(self, theta: float, vorzeichen: int, mitte: Punkt, n: int) -> list[Punkt]:
        """Flanke von r_start bis ra (Wälzwinkel gleichmäßig verteilt); vorzeichen +1 links, −1 rechts."""
        t0 = math.sqrt(max((self.r_start / self.rb) ** 2 - 1, 0.0))
        t1 = math.sqrt((self.ra / self.rb) ** 2 - 1)
        punkte = []
        for i in range(n):
            rho = self.rb * math.sqrt(1 + (t0 + (t1 - t0) * i / (n - 1)) ** 2)
            punkte.append(_polar(mitte, rho, theta + vorzeichen * self.psi(rho)))
        return punkte

    def profil(self, mitte: Punkt = (0.0, 0.0), winkel: float = 0.0, n: int = FLANKENPUNKTE) -> list[list[Segment]]:
        """Eine geschlossene Kontur gegen den Uhrzeigersinn: je Zahn rechte Fußrundung, radiale Verlängerung (falls
        die Evolvente am Grundkreis beginnt), rechte Flanke, Kopfbogen, linke Flanke, Verlängerung, linke Fußrundung,
        Fußbogen bis zum nächsten Zahn."""
        self.pruefe()
        ps, d = self.psi(self.r_start), self.delta
        kontur: list[Segment] = []
        for j in range(1, self.z + 1):
            th = self.zahnmitte(j, winkel)
            th_naechst = self.zahnmitte(j + 1, winkel)
            # rechte Seite (im Uhrzeigersinn neben der Zahnmitte), von unten nach oben
            c_r = _polar(mitte, self.rf + self.rho, th - ps - d)
            t2_r, t1_r = _polar(mitte, self.rf, th - ps - d), _polar(mitte, self.r_beruehr, th - ps)
            kontur.append(_bogen(c_r, t2_r, t1_r))
            if self.r_start > self.r_beruehr + 1e-9:
                kontur.append(Linie(t1_r, _polar(mitte, self.r_start, th - ps)))
            rechts = self._flanke(th, -1, mitte, n)
            kontur.append(Spline(tuple(rechts)))
            links = self._flanke(th, 1, mitte, n)
            kontur.append(_bogen(mitte, rechts[-1], links[-1]))
            kontur.append(Spline(tuple(reversed(links))))
            t1_l = _polar(mitte, self.r_beruehr, th + ps)
            if self.r_start > self.r_beruehr + 1e-9:
                kontur.append(Linie(_polar(mitte, self.r_start, th + ps), t1_l))
            c_l = _polar(mitte, self.rf + self.rho, th + ps + d)
            t2_l = _polar(mitte, self.rf, th + ps + d)
            kontur.append(_bogen(c_l, t1_l, t2_l))
            kontur.append(_bogen(mitte, t2_l, _polar(mitte, self.rf, th_naechst - ps - d)))
        return [kontur]

    def flaeche(self) -> float:
        """Profilfläche (mm²), aus der Kontur mit fein abgetasteten Flanken."""
        return sum(_flaeche(k) for k in self.profil(n=FLAECHE_PUNKTE))


@dataclass(frozen=True)
class Zahnstange:
    """Zahnstange mit dem Bezugsprofil: Modul m, Zähnezahl z, Zahndickenabmaß abmass (mm)."""
    m: float
    z: int
    abmass: float = 0.0

    @property
    def p(self) -> float:
        return math.pi * self.m

    @property
    def s(self) -> float:
        """Zahndicke auf der Profilmittellinie mit Abmaß."""
        return self.p / 2 + self.abmass

    @property
    def rho(self) -> float:
        return FUSSRUNDUNG * self.m

    def _fussrundung(self, uc: float, seite: int) -> tuple[Punkt, Punkt, Punkt]:
        """(Mittelpunkt, Berührpunkt Flanke, Berührpunkt Fußlinie) der Fußrundung links (seite −1) bzw. rechts (+1)
        von Zahn mit Mitte uc; Profilmittellinie v = 0, Kopf nach +v."""
        hf, rho = FUSSHOEHE * self.m, self.rho
        cy = -hf + rho
        cx = uc + seite * (self.s / 2 + (rho - cy * math.sin(ALPHA)) / math.cos(ALPHA))
        n = (seite * math.cos(ALPHA), math.sin(ALPHA))  # Normale der Flanke aus dem Zahn heraus
        return (cx, cy), (cx - rho * n[0], cy - rho * n[1]), (cx, -hf)

    def pruefe(self) -> None:
        if self.z < 1 or self.m <= 0:
            raise VerzahnungFehler(f"Modul {self.m:g} und Zähnezahl {self.z} ergeben keine Zahnstange")
        if self.s / 2 - KOPFHOEHE * self.m * math.tan(ALPHA) <= 0:
            raise VerzahnungFehler("der Zahn wird spitz (Kopfdicke ≤ 0)")
        breite_fuss = self._fussrundung(0.0, 1)[2][0] - self._fussrundung(0.0, -1)[2][0]
        if breite_fuss >= self.p:
            raise VerzahnungFehler("zwischen den Fußrundungen bleibt keine Fußlinie (Lücke zu eng)")

    def zahnmitte(self, j: int, u0: float = 0.0) -> float:
        return u0 + (j - 1) * self.p

    def profil(self, mitte: Punkt = (0.0, 0.0), kopf: str = "+v") -> list[list[Segment]]:
        """Je Zahn eine geschlossene Kontur (Zahnband ohne Rücken, Spec 4b §4.2): Fußlinie unter dem Zahn, rechte
        Fußrundung, rechte Flanke, Kopflinie, linke Flanke, linke Fußrundung. Die Fußlinien zwischen den Zähnen gehören
        zum Rücken (Präzisierung 4 des Plans). kopf "-v" spiegelt an der Profilmittellinie."""
        self.pruefe()
        u0, v0 = mitte
        vz = 1.0 if kopf == "+v" else -1.0
        ha, tan_a = KOPFHOEHE * self.m, math.tan(ALPHA)

        def p(q: Punkt) -> Punkt:
            return (q[0], v0 + vz * q[1])

        def bogen(c: Punkt, a: Punkt, b: Punkt) -> Bogen:
            return _bogen(p(c), p(a), p(b))

        konturen = []
        for j in range(1, self.z + 1):
            uc = self.zahnmitte(j, u0)
            c_l, t1_l, t2_l = self._fussrundung(uc, -1)
            c_r, t1_r, t2_r = self._fussrundung(uc, 1)
            kopf_r, kopf_l = (uc + self.s / 2 - ha * tan_a, ha), (uc - self.s / 2 + ha * tan_a, ha)
            konturen.append([Linie(p(t2_l), p(t2_r)), bogen(c_r, t2_r, t1_r), Linie(p(t1_r), p(kopf_r)),
                             Linie(p(kopf_r), p(kopf_l)), Linie(p(kopf_l), p(t1_l)), bogen(c_l, t1_l, t2_l)])
        return konturen

    def flankenmitte(self, j: int, seite: str, u0: float = 0.0) -> float:
        """u des Schnittpunkts der Flanke von Zahn j mit der Profilmittellinie."""
        return self.zahnmitte(j, u0) + (-1 if seite == "links" else 1) * self.s / 2

    def flaeche(self) -> float:
        return sum(_flaeche(k) for k in self.profil())


def _flaeche(kontur: list[Segment]) -> float:
    """Betrag der Fläche einer geschlossenen Kontur (Gaußsche Formel; Bögen exakt über das Kreissegment)."""
    summe = 0.0
    for s in kontur:
        if isinstance(s, Spline):
            pts = s.punkte
        else:
            pts = (s.a, s.b)
        summe += sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:]))
        if isinstance(s, Bogen):
            r = math.dist(s.mitte, s.a)
            sehne = math.dist(s.a, s.b)
            w = 2 * math.asin(min(1.0, sehne / (2 * r)))
            segment = r * r * (w - math.sin(w)) / 2
            summe += 2 * segment if s.gegen_uhrzeigersinn else -2 * segment
    return abs(summe) / 2


def aus_feature(f: dict, parameter: dict) -> Stirnrad | Zahnstange:
    """Geometrie eines verzahnung-Features der Spec (Werte ausgewertet; zaehne gerundet, validieren prüft Ganzzahl)."""
    from swki.spec.ausdruck import auswerten

    m, z = auswerten(f["modul"], parameter), round(auswerten(f["zaehne"], parameter))
    abmass = auswerten(f["zahndickenabmass"], parameter)
    return Stirnrad(m, z, abmass) if f["art"] == "stirnrad" else Zahnstange(m, z, abmass)


Vektor = tuple[float, float, float]
# Skizzenachsen (u, v) und Normale der Standardebenen wie swki.compiler.skizze.modellpunkt:
# vorne (u, v, lage), oben (u, lage, −v), rechts (lage, v, −u)
_ACHSEN: dict[str, tuple[Vektor, Vektor, Vektor]] = {
    "vorne": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "oben": ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    "rechts": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
}


def _plus(a: Vektor, b: Vektor, f: float = 1.0) -> Vektor:
    return (a[0] + f * b[0], a[1] + f * b[1], a[2] + f * b[2])


def _mal(a: Vektor, f: float) -> Vektor:
    return (a[0] * f, a[1] * f, a[2] * f)


@dataclass(frozen=True)
class Verzahnung:
    """Ein verzahnung-Feature im Teil (Teilkoordinaten, mm): Geometrie, Skizzenebene und Bezug (Spec 4b §4.2)."""
    id: str
    geo: Stirnrad | Zahnstange
    mitte: Punkt          # (u, v) aus der Spec
    winkel: float         # Grad, Lage von Zahn 1 (Stirnrad)
    kopf: str             # "+v" | "-v" (Zahnstange)
    ursprung: Vektor      # Ursprung der Skizzenebene
    u: Vektor
    v: Vektor
    normale: Vektor       # Normale der Skizzenebene; die Extrusion läuft in Richtung normale·(−1 bei umkehren)
    breite: tuple[float, float]  # Bereich der Zahnbreite entlang normale (Skalarprodukt mit normale)

    def modell(self, q: Punkt) -> Vektor:
        """Skizzenpunkt (u, v) → Teilkoordinaten."""
        return _plus(_plus(self.ursprung, self.u, q[0]), self.v, q[1])

    def richtung(self, q: Punkt) -> Vektor:
        """Skizzenrichtung (u, v) → Teilkoordinaten."""
        return _plus(_mal(self.u, q[0]), self.v, q[1])

    @property
    def bezugspunkt(self) -> Vektor:
        """Stirnrad: Radachse in der Skizzenebene; Zahnstange: Mitte von Zahn 1 auf der Profilmittellinie."""
        return self.modell(self.mitte)

    @property
    def zahnrichtung(self) -> Vektor:
        """Stirnrad: von der Achse zur Mitte von Zahn 1; Zahnstange: Richtung der Zahnreihe (+u)."""
        if isinstance(self.geo, Zahnstange):
            return self.u
        w = math.radians(self.winkel)
        return self.richtung((math.cos(w), math.sin(w)))

    @property
    def kopfrichtung(self) -> Vektor:
        """Zahnstange: Richtung, in die die Zähne zeigen."""
        return self.v if self.kopf == "+v" else _mal(self.v, -1.0)


def verzahnung_im_teil(f: dict, parameter: dict) -> Verzahnung:
    """Lage eines verzahnung-Features aus der Spec (ebene nur Standardebene oder versatz, Spec 4b §4.1)."""
    from swki.spec.ausdruck import auswerten

    ebene = f["ebene"]
    if isinstance(ebene, str):
        orientierung, lage = ebene, 0.0
    else:
        orientierung, lage = ebene["versatz"]["ebene"], auswerten(ebene["versatz"]["abstand"], parameter)
    u, v, n = _ACHSEN[orientierung]
    mitte = (auswerten(f["mitte"][0], parameter), auswerten(f["mitte"][1], parameter))
    b = auswerten(f["breite"], parameter) * (-1.0 if f.get("umkehren") else 1.0)
    return Verzahnung(f["id"], aus_feature(f, parameter), mitte, auswerten(f.get("winkel", 0), parameter),
                      f.get("kopf", "+v"), _mal(n, lage), u, v, n, (min(lage, lage + b), max(lage, lage + b)))
```

`swki/wissen/module_din780.yaml` anlegen:

```yaml
# Modulreihe 1 nach DIN 780-1 (mm), Spec 4b §4.3: validieren meldet andere Module als MODUL_NICHT_GENORMT.
# Abgleich (2 unabhängige Quellen je Wert, 2026-10-05):
#   A: https://de.wikipedia.org/wiki/Modul_(Zahnrad) (Reihe I, 0,05 … 50)
#   B: eAssistant-Handbuch Kap. 8.2.1, https://www.eassistant.eu/fileadmin/dokumente/eassistant/etc/HTMLHandbuch/de/eAssistantHandbch8.html
#      (Reihe 1 unter 1 mm), und https://technische-antriebselemente.de/en/guides/gear-module-calculation/ (Reihe 1, 1 … 20)
# Gesperrt (nur eine Quelle gelesen): 25, 32, 40, 50 – erst nach weiterem Abgleich aufnehmen.
reihe_1: [0.05, 0.06, 0.08, 0.1, 0.12, 0.16, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9,
          1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20]
```


- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\test_verzahnung.py tests\test_verzahnung_lage.py`
Expected: `29 passed`. Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **740 passed, 117 deselected**.

- [ ] **Step 5: Commit**

```powershell
git add swki/verzahnung.py swki/wissen/module_din780.yaml tests/test_verzahnung.py tests/test_verzahnung_lage.py
git commit -m "verzahnung: Bezugsprofil DIN 867, Evolventenprofil, Zahnweite, Lage im Teil (Stufe 4b, Task 1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Spike S14a – Verzahnung im Teil (live)

**Files:**
- Create: `spikes/s14a_verzahnung.py`
- Ergebnis: `docs/stufe0/ergebnisse/s14a_verzahnung.json` (schreibt der Spike; wird committet)

**Interfaces:**
- Consumes: `swki.verzahnung` (Task 1), `baue_teil_dokument`, `Skizzierer`, `ebene_aufloesen`, `aufsatz`, `flaechen`,
  `koerper`, `zylinder_zu_punkten`, `privat_mb`.
- Produces: Antworten auf die Zeilen 1–6 der Tabelle „Abhängigkeiten vom Spike S14a“.

- [ ] **Step 1: Vorbedingungen prüfen**

SolidWorks 2025 läuft frisch (BLOCKED Neustart an den Controller, falls nicht), genau eine Instanz, keine fremden offenen
Dokumente, Einstellungen `False 1` (Befehle in den Global Constraints). Private Bytes notieren.

- [ ] **Step 2: Spike schreiben**

`spikes/s14a_verzahnung.py` anlegen:

```python
"""S14a (Stufe 4b, Etappe 1): Evolventenverzahnung im Teil – Skizze aus berechneten Punkten, Messung, Zeit, Speicher.

1 Profil eines Stirnrads (m 2, z 20) als Splines (CreateSpline2) bzw. als Polylinie, alle Elemente fixiert (sgFIXED):
  Skizzenstatus, Segmente, Aufsatz, Flächen; Abweichung der Flankenfläche von der Soll-Evolvente (GetClosestPointOn an
  Sollpunkten der rechten Flanke von Zahn 1, mittlere Breite); Zeit.
2 Ganzes Profil (Splines) für z = 17, 25, 50, 80: Zeit für Skizze und Aufsatz, Flächen, Private Bytes vorher/nachher.
3 Messung am Rad z 20: koaxiale Zylinder (Radien, Anzahl), Flanken über die Mitte der Box, IMeasure-Abstand der
  Außenflanken über k Zähne gegen W_k; Zahnstange (z 5 auf Rücken): Kopfflächen, Flankenebenen, Teilung, Zahndicke.
4 Achse: zylinder_zu_punkten(Flächen des Features, [Achspunkt]) findet eine koaxiale Zylinderfläche.
5 Zahnstange als Zahnband (eine Kontur je Zahn) auf einem Rücken bis zur Fußlinie: ein Volumenkörper.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s14a_verzahnung
"""

import math
import time

from spikes._gemeinsam import lauf
from swki.compiler import sw
from swki.compiler.anker import punkt_achse_abstand, skalar, zylinder_zu_punkten
from swki.compiler.bauen import baue_teil_dokument
from swki.compiler.fehler import BauFehler
from swki.compiler.handler.extrusion import ENDE, aufsatz
from swki.compiler.protokoll import Protokoll
from swki.compiler.skizze import SW_GEGEN_UHRZEIGERSINN, Skizzierer, ebene_aufloesen, modellpunkt
from swki.compiler.topologie import flaechen, koerper
from swki.konfig import lade_rechner, lade_standard
from swki.speicher import privat_mb
from swki.verbindung import callout_leer, in_mm, mm, r8_array, verbinde
from swki.verzahnung import ALPHA, Bogen, Linie, Spline, Stirnrad, Zahnstange

AUFTRAG = "S14A"


def _privat_mb(app) -> float:
    return privat_mb(int(app.GetProcessID))


def _welle(name: str, laenge: float) -> dict:
    return {"art": "teil", "name": name, "material": "1.0503", "eigenschaften": {"Benennung": name},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 12}}]},
                          "ende": {"typ": "blind", "tiefe": laenge}}]}


def _ruecken(st: Zahnstange, breite: float) -> dict:
    return {"art": "teil", "name": "S14a_Stange", "material": "1.0503", "eigenschaften": {"Benennung": "Stange"},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "vorne", "elemente": [{"rechteck": {
                              "mitte": [(st.z - 1) * st.p / 2, -1.25 * st.m - 5], "breite": st.z * st.p, "hoehe": 10}}]},
                          "ende": {"typ": "blind", "tiefe": breite}}]}


def _zeichne(sk, segment, polylinie: bool) -> list:
    sm = sk.sm
    if isinstance(segment, Linie):
        (xa, ya), (xb, yb) = sk.zu_skizze(*segment.a), sk.zu_skizze(*segment.b)
        return [sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)]
    if isinstance(segment, Bogen):
        (xm, ym), (xa, ya), (xb, yb) = (sk.zu_skizze(*q) for q in (segment.mitte, segment.a, segment.b))
        drehsinn = SW_GEGEN_UHRZEIGERSINN if segment.gegen_uhrzeigersinn == sk.gleichsinnig else -SW_GEGEN_UHRZEIGERSINN
        return [sm.CreateArc(xm, ym, 0.0, xa, ya, 0.0, xb, yb, 0.0, drehsinn)]
    punkte = [sk.zu_skizze(*q) for q in segment.punkte]
    if polylinie:
        return [sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0) for (xa, ya), (xb, yb) in zip(punkte, punkte[1:])]
    return [sm.CreateSpline2(r8_array([c for x, y in punkte for c in (x, y, 0.0)]), False)]


def _verzahnung(ctx, ebene, konturen, breite: float, name: str, polylinie: bool = False) -> dict:
    """Skizze mit fixierten Elementen und Aufsatz (wie der spätere Handler); liefert Messwerte und das Feature."""
    e = {}
    se = ebene_aufloesen(ctx, ebene)
    model, sm = ctx.model, ctx.model.SketchManager
    beginn = time.perf_counter()
    sw.auswahl_leeren(model)
    sw.waehle(model, se.objekt, 0)
    sm.InsertSketch(True)
    try:
        sk = Skizzierer(ctx, se, sm.ActiveSketch)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            erzeugt = [s for k in konturen for seg in k for s in _zeichne(sk, seg, polylinie)]
            e["segmente_none"] = sum(1 for s in erzeugt if s is None)
            segmente = list(sm.ActiveSketch.GetSketchSegments or ())
            e["segmente"] = len(segmente)
            e["punkte"] = len(sm.ActiveSketch.GetSketchPoints2 or ())
            sw.auswahl_leeren(model)
            for s in segmente:
                sw.waehle(model, s, 0, anhaengen=True)
            model.SketchAddConstraints("sgFIXED")
            sw.auswahl_leeren(model)
        e["status"] = sm.ActiveSketch.GetConstrainedStatus
    finally:
        sm.InsertSketch(True)
    e["s_skizze"] = round(time.perf_counter() - beginn, 3)
    skizze = sw.letztes_feature(model)
    skizze.Name = f"{name}_skizze"
    sw.auswahl_leeren(model)
    skizze.Select2(False, 0)
    beginn = time.perf_counter()
    feature = aufsatz(model, ENDE["blind"], mm(breite), False)
    e["aufsatz"] = feature is not None
    try:
        sw.rebuild(model)
        e["rebuild"] = "ok"
    except BauFehler as ex:
        e["rebuild"] = str(ex)
    e["s_aufsatz"] = round(time.perf_counter() - beginn, 3)
    if feature is not None:
        feature.Name = name
        e["flaechen"] = len(flaechen(feature))
        e["koerper"] = len(koerper(model))
    return e, feature, se


def _abweichung(rad: Stirnrad, se, feature, lage_z: float) -> dict:
    """Abstand von 40 Sollpunkten der rechten Flanke von Zahn 1 (mittlere Breite) zur nächsten Fläche des Features."""
    rho = [rad.r_start + (rad.ra - rad.r_start) * (i + 0.5) / 40 for i in range(40)]
    sonstige = [f for f in flaechen(feature) if f.art == "sonstige"]
    werte = []
    for r in rho:
        u, v = rad.flankenpunkt(1, "rechts", r)
        p = modellpunkt(se.orientierung, u, v, lage_z)
        best = None
        for f in sonstige:
            q = f.objekt.GetClosestPointOn(mm(p[0]), mm(p[1]), mm(p[2]))
            d = math.dist(p, tuple(in_mm(c) for c in q[:3]))
            best = d if best is None else min(best, d)
        werte.append(best)
    return {"max_mm": round(max(werte), 6), "mittel_mm": round(sum(werte) / len(werte), 6), "flankenflaechen": len(sonstige)}


def _messe_rad(model, rad: Stirnrad, feature, achse_punkt, normale) -> dict:
    faces = flaechen(feature)
    koax = [f for f in faces if f.art == "zylinder" and abs(skalar(f.achse, normale)) > 1 - 1e-6
            and punkt_achse_abstand(achse_punkt, f.punkt, f.achse) <= 0.1]
    radien = sorted({round(f.radius, 4) for f in koax})
    e = {"radien": radien, "anzahl_je_radius": {r: sum(1 for f in koax if abs(f.radius - r) < 1e-3) for r in radien},
         "arten": {a: sum(1 for f in faces if f.art == a) for a in ("ebene", "zylinder", "sonstige")}}
    k, rho = rad.messzaehnezahl(), (rad.r_start + rad.ra) / 2
    sonstige = [f for f in faces if f.art == "sonstige"]

    def flanke(j, seite):
        u, v = rad.flankenpunkt(j, seite, rho)
        p = (u, v, achse_punkt[2])
        return min(sonstige, key=lambda f: math.hypot(f.punkt[0] - p[0], f.punkt[1] - p[1]))

    rechts, links = flanke(1, "rechts"), flanke(k, "links")
    sw.auswahl_leeren(model)
    sw.waehle(model, rechts.objekt, 0)
    sw.waehle(model, links.objekt, 0, anhaengen=True)
    messung = model.Extension.CreateMeasure
    e["calculate"] = bool(messung.Calculate(callout_leer()))
    e["zahnweite_ist"] = round(in_mm(messung.Distance), 6)
    e["zahnweite_soll"] = round(rad.zahnweite(), 6)
    e["k"] = k
    sw.auswahl_leeren(model)
    e["achse_zylinder_radius"] = round(zylinder_zu_punkten(faces, [achse_punkt], 0.1)[0].radius, 4)
    return e


def _messe_stange(st: Zahnstange, feature) -> dict:
    faces = flaechen(feature)
    kopf = [f for f in faces if f.art == "ebene" and f.normale[1] > 1 - 1e-6]
    links_n = (-math.cos(ALPHA), math.sin(ALPHA), 0.0)
    rechts_n = (math.cos(ALPHA), math.sin(ALPHA), 0.0)

    def u_bei_v0(f):
        return skalar(f.punkt, f.normale) / f.normale[0]

    links = sorted(u_bei_v0(f) for f in faces if f.art == "ebene" and skalar(f.normale, links_n) > 1 - 1e-6)
    rechts = sorted(u_bei_v0(f) for f in faces if f.art == "ebene" and skalar(f.normale, rechts_n) > 1 - 1e-6)
    return {"kopfflaechen": len(kopf), "kopf_y": sorted({round(f.punkt[1], 4) for f in kopf}),
            "teilung": [round(b - a, 5) for a, b in zip(links, links[1:])], "teilung_soll": round(st.p, 5),
            "zahndicke": [round(b - a, 5) for a, b in zip(links, rechts)], "zahndicke_soll": round(st.s, 5)}


def _rad(app, r, standard, z: int, polylinie: bool = False) -> dict:
    spec = _welle(f"S14a_z{z}{'_poly' if polylinie else ''}", 10)
    model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, r.arbeitsordner / AUFTRAG / "w.yaml", AUFTRAG,
                                            Protokoll(AUFTRAG, "w.yaml", 0, r.sw_jahr))
    try:
        if fehler is not None:
            raise fehler
        rad = Stirnrad(2.0, z, -0.05)
        vorher = _privat_mb(app)
        ebene = {"versatz": {"ebene": "vorne", "abstand": 10}}
        e, feature, se = _verzahnung(ctx, ebene, rad.profil(), 16, "z1", polylinie)
        e["privat_mb"] = [vorher, _privat_mb(app)]
        if feature is not None and z == 20:
            e["abweichung"] = _abweichung(rad, se, feature, 18.0)
            e["messung"] = _messe_rad(model, rad, feature, (0.0, 0.0, 10.0), (0.0, 0.0, 1.0))
        return e
    finally:
        sw.schliesse(app, model)


def _stange(app, r, standard) -> dict:
    st = Zahnstange(2.0, 5, -0.05)
    spec = _ruecken(st, 20)
    model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, r.arbeitsordner / AUFTRAG / "s.yaml", AUFTRAG,
                                            Protokoll(AUFTRAG, "s.yaml", 0, r.sw_jahr))
    try:
        if fehler is not None:
            raise fehler
        e, feature, _ = _verzahnung(ctx, "vorne", st.profil(), 20, "z1")
        if feature is not None:
            e["messung"] = _messe_stange(st, feature)
        return e
    finally:
        sw.schliesse(app, model)


def _untersuche() -> dict:
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    ergebnis = {"privat_mb_start": _privat_mb(app)}
    ergebnis["1_spline_z20"] = _rad(app, r, standard, 20)
    ergebnis["1_polylinie_z20"] = _rad(app, r, standard, 20, polylinie=True)
    ergebnis["2_ganzes_profil"] = {z: _rad(app, r, standard, z) for z in (17, 25, 50, 80)}
    ergebnis["5_zahnstange"] = _stange(app, r, standard)
    ergebnis["privat_mb_ende"] = _privat_mb(app)
    return ergebnis


if __name__ == "__main__":
    lauf("s14a_verzahnung", _untersuche)
```


- [ ] **Step 3: Spike laufen lassen**

Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m spikes.s14a_verzahnung`
Expected: `"ok": true` und `docs/stufe0/ergebnisse/s14a_verzahnung.json`. Bricht der Spike ab: Fehler und Trace im JSON lesen,
den Spike (nicht Produktionscode) korrigieren, erneut laufen lassen; jede Korrektur im Bericht nennen. Danach Private Bytes,
eine Instanz, `False 1`, keine offenen Dokumente.

- [ ] **Step 4: Auswertung in den Bericht**

Für jede Zeile 1–6 der Tabelle „Abhängigkeiten vom Spike S14a“: Annahme bestätigt / abweichend, mit den Werten aus dem
JSON: Zeile 1 `status`, `segmente_none`, `koerper`, `abweichung.max_mm` für Spline und Polylinie; Zeile 2 `s_skizze` +
`s_aufsatz` und `privat_mb` je z; Zeile 3 `messung.radien`/`anzahl_je_radius`, `zahnweite_ist` gegen `zahnweite_soll`,
Zahnstange `kopfflaechen`, `teilung`, `zahndicke` gegen ihre Soll; Zeile 4 `achse_zylinder_radius`; Zeile 5 Zeiten und
Speicher; Zeile 6 `koerper` der Zahnstange. Keine Entscheidung treffen – die trifft der Controller.

- [ ] **Step 5: Commit**

```powershell
git add spikes/s14a_verzahnung.py docs/stufe0/ergebnisse/s14a_verzahnung.json
git commit -m "spike: S14a Verzahnung im Teil – Spline, Messung, Zeit und Speicher" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Status DONE_WITH_CONCERNS, wenn eine Zeile abweicht (Controller entscheidet nach der Spalte „sonst“).

---

### Task 3: Format und Validieren der Verzahnung (ohne SolidWorks)

**Files:**
- Modify: `schema/teil.schema.json`, `swki/spec/ausdruck.py`, `swki/spec/laden.py`, `swki/spec/hinweise.py`,
  `swki/pruefung/geometrie.py`
- Test: `tests/spec/test_verzahnung_spec.py` (neu), `tests/spec/test_ausdruck.py`

**Interfaces:**
- Consumes: `swki.verzahnung` (`Z_MIN`, `VerzahnungFehler`, `aus_feature`, `ist_genormt`).
- Produces: Schema-Typ `verzahnung` (`$defs/f_verzahnung`, `$defs/ebene_fest`); `swki.spec.ausdruck.PI = "pi"` (Konstante in
  `auswerten`/`sw_ausdruck`, nicht in `namen`); Befunde mit Präfix `MODUL_NICHT_GENORMT`, `UNTERSCHNITT`, `ZAEHNE_UNGANZ`,
  `FLANKENSPIEL_FEHLT`, `VERZAHNUNG_GEOMETRIE` sowie „pi ist die Kreiszahl und kein Parametername“;
  `swki.spec.hinweise.verzahnung_hinweise(spec)` (Hinweis `abmass_gross`), `ABMASS_GROSS = 0.1`; `volumen_auto` kennt
  `verzahnung` (Profilfläche × Breite).

- [ ] **Step 1: Tests schreiben**

`tests/spec/test_verzahnung_spec.py` anlegen:

```python
"""Format und Validieren des Features verzahnung (Spec 4b §4.1, §4.3), Hinweise und Sollvolumen."""

import copy
import math

import pytest

from swki.pruefung.geometrie import volumen_auto
from swki.spec.hinweise import hinweise
from swki.spec.laden import plausibel_befunde, schema_befunde
from swki.verzahnung import Stirnrad, Zahnstange

RAD = {
    "art": "teil", "name": "Rad", "material": "1.0038", "eigenschaften": {"Benennung": "Rad"},
    "parameter": {"M": 2, "Z": 20, "B": 16, "AS": -0.05, "D": 12, "L": 20},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": "=D"}}]},
         "ende": {"typ": "blind", "tiefe": "=L"}},
        {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": "=L"}},
         "mitte": [0, 0], "modul": "=M", "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
    "pruefung": {"volumen": {"soll": "auto"}},
}
STANGE = {
    "art": "teil", "name": "Stange", "parameter": {"M": 2, "Z": 9, "B": 20, "AS": -0.05, "H": 15},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [
             {"rechteck": {"mitte": ["=(Z-1)*pi*M/2", "=-1.25*M-H/2"], "breite": "=Z*pi*M", "hoehe": "=H"}}]},
         "ende": {"typ": "blind", "tiefe": "=B"}},
        {"id": "z1", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": "=M",
         "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS", "kopf": "+v"},
    ],
}


def _mit(spec: dict, **verzahnung) -> dict:
    neu = copy.deepcopy(spec)
    neu["features"][1].update(verzahnung)
    return neu


def _meldungen(spec: dict, tmp_path) -> list[str]:
    return [b["meldung"] for b in schema_befunde(spec) + plausibel_befunde(spec, tmp_path)]


def test_gueltige_verzahnungen(tmp_path):
    assert _meldungen(RAD, tmp_path) == []
    assert _meldungen(STANGE, tmp_path) == []


def test_ebene_nur_standard_oder_versatz():
    befunde = schema_befunde(_mit(RAD, ebene={"feature": "f1", "flaeche": "+z"}))
    assert [b["pfad"] for b in befunde] == ["features[1].ebene"]


def test_pflichtfelder():
    spec = copy.deepcopy(RAD)
    del spec["features"][1]["zahndickenabmass"]
    assert any("zahndickenabmass" in b["meldung"] for b in schema_befunde(spec))


@pytest.mark.parametrize(("aenderung", "code"), [
    ({"modul": 2.25}, "MODUL_NICHT_GENORMT"),
    ({"zaehne": 20.5}, "ZAEHNE_UNGANZ"),
    ({"zaehne": 16}, "UNTERSCHNITT"),
    ({"zahndickenabmass": 0}, "FLANKENSPIEL_FEHLT"),
    ({"zahndickenabmass": 0.8}, "FLANKENSPIEL_FEHLT"),
    ({"zahndickenabmass": -1.6, "modul": 1}, "VERZAHNUNG_GEOMETRIE"),
])
def test_befunde_stirnrad(tmp_path, aenderung, code):
    meldungen = _meldungen(_mit(RAD, **aenderung), tmp_path)
    assert any(m.startswith(code) for m in meldungen), meldungen


def test_zahnstange_ohne_unterschnittgrenze(tmp_path):
    assert _meldungen(_mit(STANGE, zaehne=3), tmp_path) == []


def test_winkel_und_kopf_je_art(tmp_path):
    assert _meldungen(_mit(RAD, winkel=0), tmp_path) == []
    assert _meldungen(_mit(RAD, winkel=359), tmp_path) == []
    assert any("[0, 360)" in m for m in _meldungen(_mit(RAD, winkel=360), tmp_path))
    assert "kopf gilt nur bei art: zahnstange" in _meldungen(_mit(RAD, kopf="-v"), tmp_path)
    assert "winkel gilt nur bei art: stirnrad" in _meldungen(_mit(STANGE, winkel=10), tmp_path)


def test_modul_und_zaehne_positiv(tmp_path):
    assert any("modul muss > 0" in m for m in _meldungen(_mit(RAD, modul=-2), tmp_path))


def test_hinweise_feste_zahlen_und_abmass():
    arten = {(h["art"], h["pfad"]) for h in hinweise(_mit(RAD, modul=2, zaehne=20, zahndickenabmass=-0.3))}
    assert ("feste_zahl", "features[1].modul") in arten
    assert ("feste_zahl", "features[1].zaehne") in arten
    assert ("abmass_gross", "features[1].zahndickenabmass") in arten
    assert not any(h["art"] == "abmass_gross" for h in hinweise(RAD))


def test_volumen_auto_mit_verzahnung():
    volumen, grund = volumen_auto(RAD)
    assert grund == "analytisch"
    assert volumen == pytest.approx(math.pi * 36 * 20 + Stirnrad(2, 20, -0.05).flaeche() * 16)
    volumen, _ = volumen_auto(STANGE)
    assert volumen == pytest.approx(9 * math.pi * 2 * 15 * 20 + Zahnstange(2, 9, -0.05).flaeche() * 20)


def test_pi_ist_kein_parametername(tmp_path):
    spec = copy.deepcopy(RAD)
    spec["parameter"]["pi"] = 3
    assert "pi ist die Kreiszahl und kein Parametername" in _meldungen(spec, tmp_path)
```

In `tests/spec/test_ausdruck.py` ersetzen:

```python
import pytest

from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck, namen, sw_ausdruck
```

durch:

```python
import math

import pytest

from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck, namen, sw_ausdruck
```

In `tests/spec/test_ausdruck.py` ersetzen:

```python
    assert sw_ausdruck("=-L*2**2") == '-"L" * (2 ^ 2)'
```

durch:

```python
    assert sw_ausdruck("=-L*2**2") == '-"L" * (2 ^ 2)'


def test_konstante_pi():
    assert auswerten("=pi*M", {"M": 2}) == pytest.approx(2 * math.pi)
    assert sw_ausdruck("=HUB*360/(pi*40)") == '("HUB" * 360) / (pi * 40)'
    assert namen("=pi*M/Z") == {"M", "Z"}
```


- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\spec\test_verzahnung_spec.py tests\spec\test_ausdruck.py`
Expected: FAIL – `16 failed, 15 passed` (Schema: `'verzahnung' is not one of […]`; `pi` unbekannter Parameter).

- [ ] **Step 3: Umsetzen**

In `schema/teil.schema.json` ersetzen:

```json
    "f_skript": {
```

durch:

```json
    "ebene_fest": {
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
        }
      ]
    },
    "f_verzahnung": {
      "required": ["art", "ebene", "mitte", "modul", "zaehne", "breite", "zahndickenabmass"],
      "additionalProperties": false,
      "properties": {
        "id": true, "typ": true,
        "art": {"enum": ["stirnrad", "zahnstange"]},
        "ebene": {"$ref": "#/$defs/ebene_fest"},
        "mitte": {"$ref": "#/$defs/punkt2"},
        "modul": {"$ref": "#/$defs/wert"},
        "zaehne": {"$ref": "#/$defs/wert"},
        "breite": {"$ref": "#/$defs/wert"},
        "zahndickenabmass": {"$ref": "#/$defs/wert"},
        "umkehren": {"type": "boolean"},
        "winkel": {"$ref": "#/$defs/wert"},
        "kopf": {"enum": ["+v", "-v"]}
      }
    },
    "f_skript": {
```

In `schema/teil.schema.json` ersetzen:

```json
                         "muster_linear", "muster_kreis", "spiegeln", "skript", "referenz"]}
```

durch:

```json
                         "muster_linear", "muster_kreis", "spiegeln", "skript", "referenz", "verzahnung"]}
```

In `schema/teil.schema.json` ersetzen:

```json
        {"if": {"properties": {"typ": {"const": "referenz"}}}, "then": {"$ref": "#/$defs/f_referenz"}}
      ]
```

durch:

```json
        {"if": {"properties": {"typ": {"const": "referenz"}}}, "then": {"$ref": "#/$defs/f_referenz"}},
        {"if": {"properties": {"typ": {"const": "verzahnung"}}}, "then": {"$ref": "#/$defs/f_verzahnung"}}
      ]
```

In `swki/spec/ausdruck.py` ersetzen:

```python
Erlaubt sind Zahlen, Parameternamen, + - * / ** und Klammern. Alles andere wird abgewiesen.
"""

import ast
import operator
```

durch:

```python
Erlaubt sind Zahlen, Parameternamen, die Konstante pi, + - * / ** und Klammern. Alles andere wird abgewiesen.
"""

import ast
import math
import operator
```

In `swki/spec/ausdruck.py` ersetzen:

```python
_ERLAUBT = (ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.USub, ast.UAdd, *_OPS)
```

durch:

```python
_ERLAUBT = (ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.USub, ast.UAdd, *_OPS)
PI = "pi"  # Kreiszahl (Spec 4b §5.1), in SolidWorks-Gleichungen ebenfalls pi; kein Parametername
```

In `swki/spec/ausdruck.py` ersetzen:

```python
def namen(ausdruck: str) -> set[str]:
    return {k.id for k in ast.walk(_baum(ausdruck)) if isinstance(k, ast.Name)}
```

durch:

```python
def namen(ausdruck: str) -> set[str]:
    """Parameternamen eines Ausdrucks (ohne die Konstante pi)."""
    return {k.id for k in ast.walk(_baum(ausdruck)) if isinstance(k, ast.Name) and k.id != PI}
```

In `swki/spec/ausdruck.py` ersetzen:

```python
    if isinstance(k, ast.Name):
        if k.id not in parameter:
```

durch:

```python
    if isinstance(k, ast.Name):
        if k.id == PI:
            return math.pi
        if k.id not in parameter:
```

In `swki/spec/ausdruck.py` ersetzen:

```python
    if isinstance(k, ast.Name):
        return f'"{k.id}"'
```

durch:

```python
    if isinstance(k, ast.Name):
        return PI if k.id == PI else f'"{k.id}"'
```

In `swki/spec/hinweise.py` ersetzen:

```python
    "gewindetiefe", "laenge", "radien", "start", "linie", "bogen",
})
```

durch:

```python
    "gewindetiefe", "laenge", "radien", "start", "linie", "bogen", "modul", "zaehne", "zahndickenabmass",
})
```

In `swki/spec/hinweise.py` ersetzen:

```python
def hinweise(spec: dict) -> list[dict]:
    """Alle Hinweise für swki validieren: erst feste Zahlen, dann Zusammenfassbares. Hinweise blockieren nie."""
    return feste_masse(spec) + zusammenfassen(spec)
```

durch:

```python
ABMASS_GROSS = 0.1  # × Modul (Spec 4b §4.3)


def verzahnung_hinweise(spec: dict) -> list[dict]:
    """Spec 4b §4.3: auffällig großes Zahndickenabmaß (|A_s| > 0,1·m) als Hinweis art "abmass_gross"."""
    ergebnis = []
    p = spec.get("parameter", {})
    for i, f in enumerate(spec.get("features", [])):
        if f.get("typ") != "verzahnung":
            continue
        try:
            m, a = auswerten(f["modul"], p), auswerten(f["zahndickenabmass"], p)
        except AusdruckFehler:
            continue
        if abs(a) > ABMASS_GROSS * m:
            ergebnis.append({"art": "abmass_gross", "pfad": f"features[{i}].zahndickenabmass",
                             "meldung": f"Zahndickenabmaß {a:g} mm ist größer als {ABMASS_GROSS:g}·m ({ABMASS_GROSS * m:g} "
                                        "mm) – Flankenspiel prüfen"})
    return ergebnis


def hinweise(spec: dict) -> list[dict]:
    """Alle Hinweise für swki validieren: erst feste Zahlen, dann Zusammenfassbares, dann Verzahnung. Hinweise
    blockieren nie."""
    return feste_masse(spec) + zusammenfassen(spec) + verzahnung_hinweise(spec)
```

In `swki/pruefung/geometrie.py` ersetzen:

```python
from swki.spec.normen import bohrspitze_grad, norm_von, normmasse
```

durch:

```python
from swki.spec.normen import bohrspitze_grad, norm_von, normmasse
from swki.verzahnung import aus_feature
```

In `swki/pruefung/geometrie.py` ersetzen:

```python
        elif typ == "referenz":
            beitrag[f["id"]] = 0.0  # Bezugsgeometrie hat kein Volumen
```

durch:

```python
        elif typ == "referenz":
            beitrag[f["id"]] = 0.0  # Bezugsgeometrie hat kein Volumen
        elif typ == "verzahnung":
            beitrag[f["id"]] = aus_feature(f, p).flaeche() * auswerten(f["breite"], p)
```

In `swki/spec/laden.py` ersetzen:

```python
from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck
from swki.spec.konturen import eckradien, kontur_punkte
from swki.spec.normen import groesse_text, norm_von, normmasse, verfuegbare_groessen

SCHEMA_ORDNER = PROJEKT / "schema"
_POSITIV = {"breite", "hoehe", "durchmesser", "radius", "tiefe", "abstand", "laenge", "gewindetiefe"}
```

durch:

```python
from swki.spec.ausdruck import PI, AusdruckFehler, auswerten, ist_ausdruck
from swki.spec.konturen import eckradien, kontur_punkte
from swki.spec.normen import groesse_text, norm_von, normmasse, verfuegbare_groessen
from swki.verzahnung import Z_MIN, VerzahnungFehler, aus_feature, ist_genormt

SCHEMA_ORDNER = PROJEKT / "schema"
_POSITIV = {"breite", "hoehe", "durchmesser", "radius", "tiefe", "abstand", "laenge", "gewindetiefe", "modul", "zaehne"}
```

In `swki/spec/laden.py` ersetzen:

```python
def plausibel_befunde(spec: dict, auftrag_ordner: Path) -> list[dict]:
    befunde = []
    parameter = spec.get("parameter", {})
    features = spec["features"]
```

durch:

```python
def _in_verzahnung(spec: dict, pfad: list) -> bool:
    """Liegt der Wert (Pfad aus _werte) in einem verzahnung-Feature?"""
    return (len(pfad) > 1 and pfad[0] == "features" and isinstance(pfad[1], int)
            and spec["features"][pfad[1]].get("typ") == "verzahnung")


def _verzahnung_befunde(f: dict, pfad: str, p: dict) -> list[dict]:
    """Spec 4b §4.3: Modul DIN 780 Reihe 1, ganze Zähnezahl, unterschnittfrei, Flankenspiel, konstruierbares Profil;
    winkel nur beim Stirnrad, kopf nur bei der Zahnstange."""
    befunde = []
    if f["art"] == "zahnstange" and "winkel" in f:
        befunde.append({"pfad": f"{pfad}.winkel", "meldung": "winkel gilt nur bei art: stirnrad"})
    if f["art"] == "stirnrad" and "kopf" in f:
        befunde.append({"pfad": f"{pfad}.kopf", "meldung": "kopf gilt nur bei art: zahnstange"})
    try:
        m, z = auswerten(f["modul"], p), auswerten(f["zaehne"], p)
        abmass = auswerten(f["zahndickenabmass"], p)
    except AusdruckFehler:
        return befunde  # bereits oben gemeldet
    if m > 0 and not ist_genormt(m):
        befunde.append({"pfad": f"{pfad}.modul", "meldung": f"MODUL_NICHT_GENORMT: Modul {m:g} ist nicht in DIN 780 "
                                                            "Reihe 1 (swki/wissen/module_din780.yaml)"})
    if abs(z - round(z)) > 1e-9 or z < 1:
        befunde.append({"pfad": f"{pfad}.zaehne", "meldung": f"ZAEHNE_UNGANZ: zaehne = {z:g} ist keine ganze Zahl ≥ 1"})
        return befunde
    if f["art"] == "stirnrad" and z < Z_MIN:
        befunde.append({"pfad": f"{pfad}.zaehne", "meldung": f"UNTERSCHNITT: z = {z:g} < {Z_MIN} – ohne "
                                                             "Profilverschiebung unterschnitten"})
    if abmass >= 0:
        befunde.append({"pfad": f"{pfad}.zahndickenabmass",
                        "meldung": f"FLANKENSPIEL_FEHLT: zahndickenabmass = {abmass:g} muss < 0 sein (Flankenspiel)"})
    if m > 0 and not befunde:
        try:
            aus_feature(f, p).pruefe()
        except VerzahnungFehler as e:
            befunde.append({"pfad": pfad, "meldung": f"VERZAHNUNG_GEOMETRIE: {e}"})
    return befunde


def plausibel_befunde(spec: dict, auftrag_ordner: Path) -> list[dict]:
    befunde = []
    parameter = spec.get("parameter", {})
    features = spec["features"]
    if PI in parameter:
        befunde.append({"pfad": f"parameter.{PI}", "meldung": f"{PI} ist die Kreiszahl und kein Parametername"})
```

In `swki/spec/laden.py` ersetzen:

```python
        elif schluessel in _WINKEL and not 0 < wert <= 360:
```

durch:

```python
        elif schluessel in _WINKEL and _in_verzahnung(spec, pfad):
            if not 0 <= wert < 360:
                befunde.append({"pfad": _pfad(pfad), "meldung": f"verzahnung.winkel muss in [0, 360) liegen (ist {wert:g})"})
        elif schluessel in _WINKEL and not 0 < wert <= 360:
```

In `swki/spec/laden.py` ersetzen:

```python
        if f["typ"] == "normbohrung":
            befunde += _normbohrung_befunde(f, f"features[{i}]", parameter)
```

durch:

```python
        if f["typ"] == "normbohrung":
            befunde += _normbohrung_befunde(f, f"features[{i}]", parameter)
        if f["typ"] == "verzahnung":
            befunde += _verzahnung_befunde(f, f"features[{i}]", parameter)
```


- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\spec\test_verzahnung_spec.py tests\spec\test_ausdruck.py`
Expected: `31 passed`. Ganze Suite → **756 passed, 117 deselected**. `.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` ohne Befund.

- [ ] **Step 5: Commit**

```powershell
git add schema/teil.schema.json swki/spec/ausdruck.py swki/spec/laden.py swki/spec/hinweise.py swki/pruefung/geometrie.py tests/spec/test_verzahnung_spec.py tests/spec/test_ausdruck.py
git commit -m "spec: Feature verzahnung – Schema, Befunde, Hinweise, Sollvolumen, Konstante pi (Stufe 4b, Task 3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Handler `verzahnung` (live)

**Files:**
- Create: `swki/compiler/handler/verzahnung.py`
- Modify: `swki/compiler/handler/__init__.py`
- Test: `tests/live/test_live_verzahnung.py` (neu, drei Live-Tests)

**Interfaces:**
- Consumes: `swki.verzahnung` (`aus_feature`, `Stirnrad`, Segmente), `Skizzierer`, `ebene_aufloesen`, `modellpunkt`,
  `richtung`, `SW_GEGEN_UHRZEIGERSINN`, `aufsatz`, `ENDE`.
- Produces: Handler `verzahnung` (Feature-Name = ID, Skizze `<id>_skizze`, Maß `D1@<id>` = `breite`);
  `FeatureErgebnis(features=[feature], richtung=…, punkte=[Achspunkt] beim Stirnrad, [] bei der Zahnstange)`;
  `zeichne(sk, segment)`, `profilskizze(ctx, se, konturen, name)`, `FIXIERT = "sgFIXED"`.

**Vor dem Task:** Ledger-Entscheidungen zu S14a Zeilen 1, 2, 4 und 6. Weichen sie ab, gilt die Spalte „sonst“ (z. B.
Polylinie statt Spline in `zeichne`).

- [ ] **Step 1: Live-Tests schreiben**

`tests/live/test_live_verzahnung.py` anlegen:

```python
"""Live: Feature verzahnung (Spec 4b §4) – Stirnrad auf einer Welle, Zahnstange auf einem Rücken, Achse als Referenz,
Messung der Verzahnung und Negativfall Zahnweite (SolidWorks muss laufen)."""

import pytest

from swki.compiler.anker import zylinder_zu_punkten
from swki.compiler.topologie import flaechen, koerper
from swki.pruefung.geometrie import volumen_auto

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
RAD = {
    "art": "teil", "name": "Rad", "parameter": {"M": 2, "Z": 20, "B": 16, "AS": -0.05, "L": 20},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 12}}]},
         "ende": {"typ": "blind", "tiefe": "=L"}},
        {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": "=L"}},
         "mitte": [0, 0], "modul": "=M", "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
}
STANGE = {
    "art": "teil", "name": "Stange", "parameter": {"M": 2, "Z": 9, "B": 20, "AS": -0.05, "H": 15},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "vorne", "elemente": [
             {"rechteck": {"mitte": ["=(Z-1)*pi*M/2", "=-1.25*M-H/2"], "breite": "=Z*pi*M", "hoehe": "=H"}}]},
         "ende": {"typ": "blind", "tiefe": "=B"}},
        {"id": "z1", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": "=M",
         "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
}


def test_stirnrad_auf_welle():
    with gebautes_teil(RAD) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        erg = ctx.ergebnis("z1")
        assert [f.Name for f in erg.features] == ["z1"] and erg.punkte == [(0.0, 0.0, 20.0)]
        assert erg.richtung == (0.0, 0.0, 1.0)
        assert len(koerper(ctx.model)) == 1
        assert volumen_mm3(ctx.model) == pytest.approx(volumen_auto(RAD)[0], rel=1e-3)
        [achse] = zylinder_zu_punkten(flaechen(erg.features[0]), erg.punkte, 0.1)  # Radachse als Referenz
        assert achse.radius == pytest.approx(17.5, abs=1e-3)                       # Fußkreis d_f = 35


def test_zahnstange_auf_ruecken():
    with gebautes_teil(STANGE) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        assert len(koerper(ctx.model)) == 1
        assert volumen_mm3(ctx.model) == pytest.approx(volumen_auto(STANGE)[0], rel=1e-3)
        assert ctx.ergebnis("z1").punkte == []


def test_stirnrad_oben_mit_winkel_und_umkehren():
    spec = {**RAD, "features": [RAD["features"][0] | {"skizze": {"ebene": "oben", "elemente": [
        {"kreis": {"mitte": [0, 0], "durchmesser": 12}}]}},
        RAD["features"][1] | {"ebene": {"versatz": {"ebene": "oben", "abstand": 0}}, "winkel": 9, "umkehren": True}]}
    with gebautes_teil(spec) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        assert ctx.ergebnis("z1").richtung == (0.0, -1.0, 0.0) and len(koerper(ctx.model)) == 1
```


- [ ] **Step 2: Sammeln prüfen**

Run: `.venv\Scripts\python.exe -m pytest -m sw tests\live\test_live_verzahnung.py --collect-only -q`
Expected: 3 Tests gesammelt. (Ohne Handler scheitern sie live mit `UNBEKANNTER_TYP` – nicht eigens laufen lassen.)

- [ ] **Step 3: Umsetzen**

`swki/compiler/handler/verzahnung.py` anlegen:

```python
"""Handler "verzahnung" (Spec 4b §4.4): Evolventen-Stirnrad oder Zahnstange aus dem berechneten Profil
(swki.verzahnung). Die Skizze enthält die Konturen als Linien, Bögen und Splines durch die berechneten Punkte; alle
Elemente sind fixiert (keine Maße, keine Gleichungen – die Werte schützt die Prüfung gegen die freigegebene Kopie).
Danach Aufsatz um breite, verschmolzen mit vorhandenen Körpern (Spike S14a Zeilen 1, 2).

Ein Stirnrad trägt einen Achspunkt (FeatureErgebnis.punkte): {feature, instanz: 1, achse: true} wählt dann die
koaxiale Zylinderfläche (Fußkreis), wie bei einer Bohrung."""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, SKIZZE_NICHT_BESTIMMT, SKIZZE_UNGUELTIG, BauFehler
from swki.compiler.handler.extrusion import ENDE, aufsatz
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import SW_GEGEN_UHRZEIGERSINN, Skizzierer, ebene_aufloesen, modellpunkt, richtung
from swki.verbindung import r8_array
from swki.verzahnung import Bogen, Linie, Stirnrad, aus_feature

FIXIERT = "sgFIXED"  # Skizzenbeziehung "Fixieren" (SketchAddConstraints, Spike S14a Zeile 1)


def zeichne(sk: Skizzierer, segment):
    """Ein Profilsegment in die offene Skizze; liefert das Skizzensegment oder None."""
    sm = sk.sm
    if isinstance(segment, Linie):
        (xa, ya), (xb, yb) = sk.zu_skizze(*segment.a), sk.zu_skizze(*segment.b)
        return sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)
    if isinstance(segment, Bogen):
        (xm, ym), (xa, ya), (xb, yb) = (sk.zu_skizze(*q) for q in (segment.mitte, segment.a, segment.b))
        drehsinn = SW_GEGEN_UHRZEIGERSINN if segment.gegen_uhrzeigersinn == sk.gleichsinnig else -SW_GEGEN_UHRZEIGERSINN
        return sm.CreateArc(xm, ym, 0.0, xa, ya, 0.0, xb, yb, 0.0, drehsinn)
    werte = [c for q in segment.punkte for c in (*sk.zu_skizze(*q), 0.0)]
    return sm.CreateSpline2(r8_array(werte), False)


def profilskizze(ctx, se, konturen: list, name: str):
    """Skizze mit allen Konturen, alle Elemente fixiert; BauFehler, wenn ein Segment fehlt oder die Skizze nicht voll
    bestimmt ist. Rückgabe: Skizzen-Feature (benannt)."""
    model, sm = ctx.model, ctx.model.SketchManager
    sw.auswahl_leeren(model)
    sw.waehle(model, se.objekt, 0)
    sm.InsertSketch(True)
    status = None
    try:
        sk = Skizzierer(ctx, se, sm.ActiveSketch)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            for k, kontur in enumerate(konturen, start=1):
                for i, segment in enumerate(kontur, start=1):
                    if zeichne(sk, segment) is None:
                        raise BauFehler(SKIZZE_UNGUELTIG, f"{name}: Kontur {k}, Segment {i} nicht erzeugt", schritt="skizze")
            sw.auswahl_leeren(model)
            for segment in sm.ActiveSketch.GetSketchSegments or ():
                sw.waehle(model, segment, 0, anhaengen=True)
            model.SketchAddConstraints(FIXIERT)
            sw.auswahl_leeren(model)
        status = sm.ActiveSketch.GetConstrainedStatus
    finally:
        sm.InsertSketch(True)
    if status != sw.SW_FULLY_CONSTRAINED:
        raise BauFehler(SKIZZE_NICHT_BESTIMMT, f"Skizze {name}: Status {status} statt voll bestimmt", schritt="skizze")
    skizze = sw.letztes_feature(model)
    skizze.Name = name
    return skizze


@handler("verzahnung")
def verzahnung(ctx, f: dict) -> FeatureErgebnis:
    geo = aus_feature(f, ctx.spec.get("parameter", {}))
    mitte = (ctx.wert(f["mitte"][0]), ctx.wert(f["mitte"][1]))
    if isinstance(geo, Stirnrad):
        konturen = geo.profil(mitte, ctx.wert(f.get("winkel", 0)))
    else:
        konturen = geo.profil(mitte, f.get("kopf", "+v"))
    se = ebene_aufloesen(ctx, f["ebene"])
    skizze = profilskizze(ctx, se, konturen, f"{f['id']}_skizze")
    umkehren = bool(f.get("umkehren", False))
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)
    feature = aufsatz(ctx.model, ENDE["blind"], ctx.m(f["breite"]), umkehren)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"verzahnung {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    ctx.verknuepfe(f"D1@{f['id']}", f["breite"])
    punkte = [modellpunkt(se.orientierung, *mitte, se.lage)] if isinstance(geo, Stirnrad) else []
    return FeatureErgebnis([feature], richtung=richtung(se, umkehren), punkte=punkte)
```

In `swki/compiler/handler/__init__.py` ersetzen:

```python
from swki.compiler.handler import bohrung, extrusion, kanten, muster, normbohrung, referenz, rotation, skript  # noqa: F401
```

durch:

```python
from swki.compiler.handler import (  # noqa: F401
    bohrung, extrusion, kanten, muster, normbohrung, referenz, rotation, skript, verzahnung,
)
```


- [ ] **Step 4: Unit-Tests und API-Prüfung**

Run: `.venv\Scripts\python.exe -m pytest -q` → **756 passed, 120 deselected**;
`.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` ohne Befund.

- [ ] **Step 5: Live-Tests**

SolidWorks frisch oder < 4 GB Private Bytes. Run (PowerShell):
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_verzahnung.py --zeit 300`
Expected: `OK` für `test_stirnrad_auf_welle`, `test_zahnstange_auf_ruecken`, `test_stirnrad_oben_mit_winkel_und_umkehren`.
Scheitert ein Test: Fehlerbild melden (NEEDS_CONTEXT), nicht die Erwartung ändern. Danach Private Bytes, `False 1`.

- [ ] **Step 6: Commit**

```powershell
git add swki/compiler/handler/verzahnung.py swki/compiler/handler/__init__.py tests/live/test_live_verzahnung.py
git commit -m "compiler: Handler verzahnung – Profilskizze mit fixierten Elementen, Aufsatz, Radachse (Stufe 4b, Task 4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Teilprüfung `verzahnungen` (ohne SolidWorks und live)

**Files:**
- Modify: `swki/pruefung/messen.py`, `swki/pruefung/bewertung.py`, `config/standard.yaml`, `tests/live/test_live_verzahnung.py`
- Test: `tests/pruefung/test_verzahnung_pruefung.py` (neu)

**Interfaces:**
- Consumes: `swki.verzahnung` (`ALPHA`, `KOPFHOEHE`, `Stirnrad`, `Verzahnung`, `verzahnung_im_teil`, `aus_feature`),
  `flaechen`, `punkt_achse_abstand`, `skalar`.
- Produces: `Messwerte.verzahnungen: dict[str, dict | str]`; `swki.pruefung.messen.verzahnungen(model, soll_spec, tol_mm)`,
  `waehle_flanke(kandidaten, erwartet, normale, tol_mm) -> Flaeche`; `swki.pruefung.bewertung.verzahnung_abweichungen(f,
  ist, parameter, tol_mm) -> list[str]`; Prüfung `verzahnungen` (Knoten = Feature-IDs); `toleranzen.verzahnung_mm`
  (Vorgabe 0.005, Ledger nach S14a Zeile 3).
- Messwerte eines Stirnrads: `{"art", "kopfkreis", "fusskreis", "zaehne", "k", "zahnweite"}` (mm), einer Zahnstange:
  `{"art", "zaehne", "kopflinie": [...], "teilung": [...], "zahndicke": [...]}`; Messfehler als `"fehler"`.

- [ ] **Step 1: Tests schreiben**

`tests/pruefung/test_verzahnung_pruefung.py` anlegen:

```python
"""Prüfung verzahnungen am Teil (Spec 4b §4.5) ohne SolidWorks: Soll gegen Messwerte, Flankenwahl."""

import math

import pytest

from swki.compiler.anker import AnkerFehler, Flaeche
from swki.pruefung.bewertung import Messwerte, bewerte, verzahnung_abweichungen
from swki.pruefung.messen import waehle_flanke
from swki.verzahnung import Stirnrad, Zahnstange

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5, "verzahnung_mm": 0.005}}
RAD = {"id": "z1", "typ": "verzahnung", "art": "stirnrad", "ebene": "vorne", "mitte": [0, 0], "modul": "=M",
       "zaehne": "=Z", "breite": 10, "zahndickenabmass": "=AS"}
STANGE = {"id": "z2", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": 2,
          "zaehne": 3, "breite": 10, "zahndickenabmass": -0.05}
P = {"M": 2, "Z": 20, "AS": -0.05}


def _rad_ist(**aenderungen) -> dict:
    rad = Stirnrad(2, 20, -0.05)
    ist = {"art": "stirnrad", "kopfkreis": 2 * rad.ra, "fusskreis": 2 * rad.rf, "zaehne": 20, "k": 3,
           "zahnweite": rad.zahnweite()}
    return ist | aenderungen


def _stange_ist(**aenderungen) -> dict:
    st = Zahnstange(2, 3, -0.05)
    ist = {"art": "zahnstange", "zaehne": 3, "kopflinie": [2.0], "teilung": [st.p, st.p], "zahndicke": [st.s] * 3}
    return ist | aenderungen


def test_stirnrad_passt():
    assert verzahnung_abweichungen(RAD, _rad_ist(), P, 0.005) == []


def test_stirnrad_abweichungen():
    soll = Stirnrad(2, 20, -0.05).zahnweite()
    fehler = verzahnung_abweichungen(RAD, _rad_ist(zahnweite=soll + 0.01, zaehne=19), P, 0.005)
    assert fehler == [f"zaehne: ist 19 statt 20", f"zahnweite W3: ist {soll + 0.01} statt {round(soll, 6)}"]
    assert verzahnung_abweichungen(RAD, _rad_ist(kopfkreis=44.01), P, 0.005) == ["kopfkreis: ist 44.01 statt 44.0"]


def test_stirnrad_messfehler_ist_abweichung():
    ist = _rad_ist(fehler="Zahnweite nicht messbar: keine Flankenflächen")
    del ist["zahnweite"]
    assert verzahnung_abweichungen(RAD, ist, P, 0.005) == ["Zahnweite nicht messbar: keine Flankenflächen"]


def test_zahnstange():
    assert verzahnung_abweichungen(STANGE, _stange_ist(), {}, 0.005) == []
    fehler = verzahnung_abweichungen(STANGE, _stange_ist(teilung=[2 * math.pi, 2 * math.pi + 0.02]), {}, 0.005)
    assert len(fehler) == 1 and fehler[0].startswith("teilung:")
    assert verzahnung_abweichungen(STANGE, _stange_ist(kopflinie=[2.0, 2.1]), {}, 0.005)[0].startswith("kopflinie:")


def _spec(*features) -> dict:
    return {"art": "teil", "name": "R", "parameter": P, "features": list(features)}


def _messwerte(verzahnungen: dict) -> Messwerte:
    return Messwerte(rebuild_fehler=[], skizzen={}, box=[0] * 6, volumen=1.0, schwerpunkt=(0, 0, 0), material="",
                     eigenschaften={}, verzahnungen=verzahnungen)


def test_bewerte_mit_verzahnung():
    spec = _spec(RAD, STANGE)
    bericht = bewerte(spec, _messwerte({"z1": _rad_ist(), "z2": _stange_ist()}), STANDARD)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "verzahnungen")
    assert pruefung["ok"] is True and pruefung["knoten"] == []
    bericht = bewerte(spec, _messwerte({"z1": _rad_ist(fusskreis=34.9), "z2": "Feature z2 fehlt im Teil"}), STANDARD)
    pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "verzahnungen")
    assert pruefung["ok"] is False and pruefung["knoten"] == ["z1", "z2"]
    assert any(m["pruefung"] == "verzahnungen" for m in bericht["maengel"])


def test_ohne_verzahnung_keine_pruefung():
    spec = _spec({"id": "f1", "typ": "referenz", "achse": "z"})
    assert all(p["id"] != "verzahnungen" for p in bewerte(spec, _messwerte({}), STANDARD)["pruefungen"])


def test_waehle_flanke():
    a = Flaeche("sonstige", (10.0, 1.0, 5.0))
    b = Flaeche("sonstige", (10.0, -1.0, 5.0))
    assert waehle_flanke([a, b], (10.05, 0.9, 0.0), (0.0, 0.0, 1.0), 0.5) is a  # z (Achsrichtung) zählt nicht
    with pytest.raises(AnkerFehler, match="keine Flanke"):
        waehle_flanke([a, b], (12.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.5)
```

In `tests/live/test_live_verzahnung.py` ersetzen:

```python
from swki.compiler.topologie import flaechen, koerper
from swki.pruefung.geometrie import volumen_auto
```

durch:

```python
from swki.compiler.topologie import flaechen, koerper
from swki.pruefung.bewertung import verzahnung_abweichungen
from swki.pruefung.geometrie import volumen_auto
from swki.pruefung.messen import verzahnungen
```

In `tests/live/test_live_verzahnung.py` ersetzen:

```python
         "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
}
```

durch:

```python
         "zaehne": "=Z", "breite": "=B", "zahndickenabmass": "=AS"},
    ],
}
TOL = 0.005  # toleranzen.verzahnung_mm (config/standard.yaml)
```

In `tests/live/test_live_verzahnung.py` ersetzen:

```python
        assert ctx.ergebnis("z1").richtung == (0.0, -1.0, 0.0) and len(koerper(ctx.model)) == 1
```

durch:

```python
        assert ctx.ergebnis("z1").richtung == (0.0, -1.0, 0.0) and len(koerper(ctx.model)) == 1


@pytest.mark.parametrize("spec", [RAD, STANGE], ids=["stirnrad", "zahnstange"])
def test_messung_der_verzahnung(spec):
    with gebautes_teil(spec) as (ctx, fehler, protokoll):
        assert fehler is None, fehler
        ist = verzahnungen(ctx.model, spec, 0.1)["z1"]
        assert isinstance(ist, dict), ist
        assert verzahnung_abweichungen(spec["features"][1], ist, spec["parameter"], TOL) == [], ist
```


- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\pruefung\test_verzahnung_pruefung.py`
Expected: FAIL – `1 error` beim Sammeln (`ImportError: cannot import name 'verzahnung_abweichungen'`).

- [ ] **Step 3: Umsetzen**

In `swki/pruefung/messen.py` ersetzen:

```python
from pathlib import Path

from swki.cli import SwkiFehler
```

durch:

```python
import math
from pathlib import Path

from swki.cli import SwkiFehler
```

In `swki/pruefung/messen.py` ersetzen:

```python
from swki.compiler.anker import AnkerFehler, flaeche_in_richtung, laenge, zylinder_durch_punkt, zylinder_zu_punkten
```

durch:

```python
from swki.compiler.anker import (AnkerFehler, Flaeche, flaeche_in_richtung, laenge, punkt_achse_abstand, skalar,
                                 zylinder_durch_punkt, zylinder_zu_punkten)
```

In `swki/pruefung/messen.py` ersetzen:

```python
from swki.verbindung import byref_long, byref_str, in_mm, in_mm3
```

durch:

```python
from swki.verbindung import byref_long, byref_str, callout_leer, in_mm, in_mm3
from swki.verzahnung import ALPHA, Stirnrad, Verzahnung, verzahnung_im_teil
```

In `swki/pruefung/messen.py` ersetzen:

```python
def kontext_aus_datei(
```

durch:

```python
_PARALLEL = 1.0 - 1e-6


def _in_ebene(d, normale) -> float:
    """Länge des Anteils von d senkrecht zu normale."""
    t = skalar(d, normale)
    return laenge(tuple(d[i] - t * normale[i] for i in range(3)))


def waehle_flanke(kandidaten: list[Flaeche], erwartet, normale, tol_mm: float) -> Flaeche:
    """Die Fläche, deren Mittelpunkt (Flaeche.punkt, Mitte der Box) senkrecht zur Radachse dem erwarteten Flankenpunkt
    am nächsten liegt; AnkerFehler, wenn keine innerhalb tol_mm liegt (Spike S14a Zeile 3)."""
    if not kandidaten:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", "keine Flankenflächen")
    beste = min(kandidaten, key=lambda f: _in_ebene(tuple(f.punkt[i] - erwartet[i] for i in range(3)), normale))
    abstand = _in_ebene(tuple(beste.punkt[i] - erwartet[i] for i in range(3)), normale)
    if abstand > tol_mm:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"keine Flanke innerhalb {tol_mm:g} mm (nächste {abstand:.3f} mm)")
    return beste


def _abstand_flaechen(model, a, b) -> float:
    """Kürzester Abstand zweier Flächen (IMeasure, mm)."""
    sw.auswahl_leeren(model)
    sw.waehle(model, a, 0)
    sw.waehle(model, b, 0, anhaengen=True)
    messung = model.Extension.CreateMeasure
    try:
        if not messung.Calculate(callout_leer()) or messung.Distance < 0:
            raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", "IMeasure liefert keinen Abstand der Flanken")
        return round(in_mm(messung.Distance), 6)
    finally:
        sw.auswahl_leeren(model)


def _stirnrad(model, vz: Verzahnung, faces: list[Flaeche], tol_mm: float) -> dict:
    rad: Stirnrad = vz.geo
    achse = vz.bezugspunkt
    koaxial = [f for f in faces if f.art == "zylinder" and abs(skalar(f.achse, vz.normale)) / laenge(f.achse) > _PARALLEL
               and punkt_achse_abstand(achse, f.punkt, tuple(c / laenge(f.achse) for c in f.achse)) <= tol_mm]
    if not koaxial:
        return {"art": "stirnrad", "fehler": "keine koaxialen Zylinderflächen (Kopf-/Fußkreis)"}
    ra = max(f.radius for f in koaxial)
    ergebnis = {"art": "stirnrad", "kopfkreis": round(2 * ra, 6), "fusskreis": round(2 * min(f.radius for f in koaxial), 6),
                "zaehne": sum(1 for f in koaxial if abs(f.radius - ra) <= tol_mm), "k": rad.messzaehnezahl()}
    flanken = [f for f in faces if f.art == "sonstige"]
    rho = (rad.r_start + rad.ra) / 2
    try:
        rechts = waehle_flanke(flanken, vz.modell(rad.flankenpunkt(1, "rechts", rho, vz.mitte, vz.winkel)), vz.normale,
                               0.25 * rad.m)
        links = waehle_flanke(flanken, vz.modell(rad.flankenpunkt(ergebnis["k"], "links", rho, vz.mitte, vz.winkel)),
                              vz.normale, 0.25 * rad.m)
        ergebnis["zahnweite"] = _abstand_flaechen(model, rechts.objekt, links.objekt)
    except BauFehler as e:
        ergebnis["fehler"] = f"Zahnweite nicht messbar: {e}"
    return ergebnis


def _zahnstange(vz: Verzahnung, faces: list[Flaeche]) -> dict:
    kopf, t = vz.kopfrichtung, vz.u
    q = vz.bezugspunkt
    koepfe = [f for f in faces if f.art == "ebene" and skalar(f.normale, kopf) > _PARALLEL]
    n_links = tuple(-math.cos(ALPHA) * t[i] + math.sin(ALPHA) * kopf[i] for i in range(3))
    n_rechts = tuple(math.cos(ALPHA) * t[i] + math.sin(ALPHA) * kopf[i] for i in range(3))

    def schnitt(f: Flaeche) -> float:
        """u des Schnitts der Flankenebene mit der Profilmittellinie (durch q in Richtung t)."""
        return skalar(tuple(f.punkt[i] - q[i] for i in range(3)), f.normale) / skalar(t, f.normale)

    links = sorted(schnitt(f) for f in faces if f.art == "ebene" and skalar(f.normale, n_links) > _PARALLEL)
    rechts = sorted(schnitt(f) for f in faces if f.art == "ebene" and skalar(f.normale, n_rechts) > _PARALLEL)
    ergebnis = {"art": "zahnstange", "zaehne": len(koepfe),
                "kopflinie": sorted({round(skalar(tuple(f.punkt[i] - q[i] for i in range(3)), kopf), 6) for f in koepfe}),
                "teilung": [round(b - a, 6) for a, b in zip(links, links[1:])]}
    if len(links) == len(rechts):
        ergebnis["zahndicke"] = [round(b - a, 6) for a, b in zip(links, rechts)]
    else:
        ergebnis["fehler"] = f"{len(links)} linke und {len(rechts)} rechte Flanken"
    return ergebnis


def verzahnungen(model, soll_spec: dict, tol_mm: float) -> dict[str, dict | str]:
    """Für jedes verzahnung-Feature der Soll-Spezifikation die Messwerte des gleichnamigen Features (Spec 4b §4.5)
    oder einen Fehlertext. Lage aus der Soll-Spezifikation (swki.verzahnung.verzahnung_im_teil)."""
    ergebnis: dict[str, dict | str] = {}
    p = soll_spec.get("parameter", {})
    for f in soll_spec["features"]:
        if f["typ"] != "verzahnung":
            continue
        feature = model.FeatureByName(f["id"])
        if feature is None:
            ergebnis[f["id"]] = f"Feature {f['id']} fehlt im Teil"
            continue
        try:
            vz = verzahnung_im_teil(f, p)
            faces = flaechen(feature)
            ergebnis[f["id"]] = (_stirnrad(model, vz, faces, tol_mm) if isinstance(vz.geo, Stirnrad)
                                 else _zahnstange(vz, faces))
        except Exception as e:  # COM-Fehler beim Lesen → Mangel statt Abbruch der Prüfung
            ergebnis[f["id"]] = f"Verzahnung {f['id']} nicht messbar: {e}"
    return ergebnis


def kontext_aus_datei(
```

In `swki/pruefung/messen.py` ersetzen:

```python
def messe(ctx, freigegeben: dict | None = None) -> Messwerte:
    """freigegeben: Spezifikation im Stand der Freigabe (Soll der Prüfung normbohrungen); ohne Angabe ctx.spec."""
```

durch:

```python
def messe(ctx, freigegeben: dict | None = None) -> Messwerte:
    """freigegeben: Spezifikation im Stand der Freigabe (Soll der Prüfungen normbohrungen und verzahnungen); ohne Angabe
    ctx.spec."""
```

In `swki/pruefung/messen.py` ersetzen:

```python
        durchmesser=durchmesser(ctx, ctx.spec),
    )
```

durch:

```python
        durchmesser=durchmesser(ctx, ctx.spec),
        verzahnungen=verzahnungen(model, freigegeben or ctx.spec, ctx.tol_mm),
    )
```

In `swki/pruefung/bewertung.py` ersetzen:

```python
    norm_von, normmasse,
)
```

durch:

```python
    norm_von, normmasse,
)
from swki.verzahnung import KOPFHOEHE, Stirnrad, aus_feature
```

In `swki/pruefung/bewertung.py` ersetzen:

```python
    durchmesser: dict[str, dict | str] = field(default_factory=dict)  # was → {"durchmesser", "achse", "referenz"?} oder Fehlertext
```

durch:

```python
    durchmesser: dict[str, dict | str] = field(default_factory=dict)  # was → {"durchmesser", "achse", "referenz"?} oder Fehlertext
    verzahnungen: dict[str, dict | str] = field(default_factory=dict)  # ID → Messwerte der Verzahnung oder Fehlertext
```

In `swki/pruefung/bewertung.py` ersetzen:

```python
def baum_kennzahl(
```

durch:

```python
def verzahnung_abweichungen(f: dict, ist: dict, parameter: dict, tol_mm: float) -> list[str]:
    """Spec 4b §4.5: verzahnung-Knoten (freigegebene Kopie) gegen die Messwerte des gleichnamigen Features
    (swki.pruefung.messen.verzahnungen, mm). Leere Liste = passt."""
    geo = aus_feature(f, parameter)
    abweichungen = [ist["fehler"]] if "fehler" in ist else []
    if ist.get("zaehne") != geo.z:
        abweichungen.append(f"zaehne: ist {ist.get('zaehne')} statt {geo.z}")

    def vergleiche(name: str, wert, soll: float) -> None:
        werte = wert if isinstance(wert, list) else [wert]
        falsch = [w for w in werte if w is None or abs(w - soll) > tol_mm]
        if falsch or not werte:
            abweichungen.append(f"{name}: ist {wert} statt {round(soll, 6)}")

    if isinstance(geo, Stirnrad):
        vergleiche("kopfkreis", ist.get("kopfkreis"), 2 * geo.ra)
        vergleiche("fusskreis", ist.get("fusskreis"), 2 * geo.rf)
        if "zahnweite" in ist:
            vergleiche(f"zahnweite W{geo.messzaehnezahl()}", ist["zahnweite"], geo.zahnweite())
    else:
        vergleiche("kopflinie", ist.get("kopflinie"), KOPFHOEHE * geo.m)
        vergleiche("teilung", ist.get("teilung"), geo.p)
        if "zahndicke" in ist:
            vergleiche("zahndicke", ist["zahndicke"], geo.s)
    return abweichungen


def baum_kennzahl(
```

In `swki/pruefung/bewertung.py` ersetzen:

```python
    # Allgemeine Prüfung: ein Teil ist ein Volumenkörper.
```

durch:

```python
    soll_verzahnungen = [f for f in soll_spec["features"] if f["typ"] == "verzahnung"]
    if soll_verzahnungen:
        p_soll, tol = soll_spec.get("parameter", {}), standard["toleranzen"]["verzahnung_mm"]
        abweichend = {}
        for f in soll_verzahnungen:
            ist = m.verzahnungen.get(f["id"])
            if not isinstance(ist, dict):
                abweichend[f["id"]] = [ist or f"Feature {f['id']} fehlt im Teil"]
            elif fehler := verzahnung_abweichungen(f, ist, p_soll, tol):
                abweichend[f["id"]] = fehler
        ergebnisse.append(_pruefung("verzahnungen", not abweichend, ist=abweichend, knoten=sorted(abweichend)))

    # Allgemeine Prüfung: ein Teil ist ein Volumenkörper.
```

In `config/standard.yaml` ersetzen:

```yaml
  volumen_prozent: 0.5
```

durch:

```yaml
  volumen_prozent: 0.5
  verzahnung_mm: 0.005  # Kreise, Zahnweite, Teilung, Zahndicke (Spec 4b §4.5; Wert nach Spike S14a Zeile 3)
```


- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\pruefung\test_verzahnung_pruefung.py` → `7 passed`.
Ganze Suite → **763 passed, 122 deselected**; `pruefe-code` ohne Befund.

- [ ] **Step 5: Live-Tests der Messung**

Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py "tests\live\test_live_verzahnung.py::test_messung_der_verzahnung" --zeit 300`
Expected: `OK` für `[stirnrad]` und `[zahnstange]`. Abweichung über `verzahnung_mm`: Werte melden (NEEDS_CONTEXT), die
Toleranz nicht selbst ändern.

- [ ] **Step 6: Commit**

```powershell
git add swki/pruefung/messen.py swki/pruefung/bewertung.py config/standard.yaml tests/pruefung/test_verzahnung_pruefung.py tests/live/test_live_verzahnung.py
git commit -m "pruefung: verzahnungen – Kopf-/Fußkreis, Zähnezahl, Zahnweite, Teilung, Zahndicke (Stufe 4b, Task 5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Teil-Referenzen, Negativfall Zahnweite, Prüfer, Zwischenstand (live)

**Files:**
- Create: `tests/referenz/zahnstangentrieb/{grundplatte,leiste,schlitten,zahnstange,lagerbock,ritzelwelle,antriebswelle}.yaml`,
  `tests/referenz/zahnstangentrieb/eingabe/beschreibung.md`, `docs/stufe4b/ergebnisse.md`
- Modify: `tests/referenz/test_referenzen.py`, `tests/live/test_live_verzahnung.py`, `.claude/agents/pruefer.md`,
  `.claude/skills/konstruieren/SKILL.md`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: Teil-Specs der Referenz (Task 13 nutzt sie für die Baugruppe), Referenzeinträge `zahnstangentrieb-zahnstange.yaml`,
  `-ritzelwelle.yaml`, `-antriebswelle.yaml`, Live-Negativfall `test_negativ_zahnweite`, Prüfer-Checkliste „Verzahnungen“,
  Skill-Regel `verzahnung`.

- [ ] **Step 1: Tests anpassen**

In `tests/referenz/test_referenzen.py` ersetzen:

```python
    ("schlitten", "linearschlitten.yaml"),
])
```

durch:

```python
    ("schlitten", "linearschlitten.yaml"),
    ("zahnstangentrieb", "zahnstange.yaml"),
    ("zahnstangentrieb", "ritzelwelle.yaml"),
    ("zahnstangentrieb", "antriebswelle.yaml"),
])
```

In `tests/live/test_live_verzahnung.py` ersetzen:

```python
import pytest

from swki.compiler.anker import zylinder_zu_punkten
from swki.compiler.topologie import flaechen, koerper
from swki.pruefung.bewertung import verzahnung_abweichungen
from swki.pruefung.geometrie import volumen_auto
from swki.pruefung.messen import verzahnungen

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
```

durch:

```python
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from swki.cli import main
from swki.compiler.anker import zylinder_zu_punkten
from swki.compiler.handler import verzahnung as handler_verzahnung
from swki.compiler.topologie import flaechen, koerper
from swki.konfig import lade_rechner
from swki.pruefung.bewertung import verzahnung_abweichungen
from swki.pruefung.geometrie import volumen_auto
from swki.pruefung.messen import verzahnungen

from .bauhilfe import gebautes_teil, volumen_mm3

pytestmark = pytest.mark.sw
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "zahnstangentrieb"
```

In `tests/live/test_live_verzahnung.py` ersetzen:

```python
        assert verzahnung_abweichungen(spec["features"][1], ist, spec["parameter"], TOL) == [], ist
```

durch:

```python
        assert verzahnung_abweichungen(spec["features"][1], ist, spec["parameter"], TOL) == [], ist


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_negativ_zahnweite(capsys, tmp_path, monkeypatch):
    # Negativfall E1 (Spec 4b §4.6): der Bau verfälscht das Zahndickenabmaß um −0,05 mm (die Spec bleibt gültig und
    # unverändert) → genau der Mangel verzahnungen (Zahnweite); das Volumen bleibt in der Toleranz (−0,13 %)
    original = handler_verzahnung.aus_feature
    monkeypatch.setattr(handler_verzahnung, "aus_feature",
                        lambda f, p: replace(original(f, p), abmass=original(f, p).abmass - 0.05))
    auftrag = tmp_path / "SWKI-LIVE-ZAHNWEITE"
    shutil.copytree(REFERENZ, auftrag)
    spec = auftrag / "antriebswelle.yaml"
    try:
        assert _lauf(capsys, "validieren", str(spec))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec))
        assert code == 0, bau
        code, bericht = _lauf(capsys, "pruefen", str(spec))
        maengel = {m["pruefung"]: m for m in bericht["maengel"]}
        assert set(maengel) == {"verzahnungen"}, maengel
        assert maengel["verzahnungen"]["knoten"] == ["z1"]
        pruefung = next(p for p in bericht["pruefungen"] if p["id"] == "verzahnungen")
        assert any(t.startswith("zahnweite W6") for t in pruefung["ist"]["z1"]), pruefung
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / "SWKI-LIVE-ZAHNWEITE", ignore_errors=True)
```


- [ ] **Step 2: Referenz-Specs, Prüfer und Skill**

`tests/referenz/zahnstangentrieb/grundplatte.yaml` anlegen:

```yaml
# Referenz Zahnstangentrieb (Spec 4b): Grundplatte, fixiert – wie im Linearschlitten (4a). Ursprung Mitte Unterseite,
# Oberseite y = H. Gewinde M8 für die Führungsleisten: zwei je Leiste auf deren Mittellinie (z = ±ZL).
art: teil
name: Grundplatte
material: "1.0038"
eigenschaften: {Benennung: Grundplatte Zahnstangentrieb}
parameter: {L: 300, B: 100, H: 20, AL: 200, ZL: 40, TG: 16, GT: 12}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: normbohrung, art: gewinde, groesse: M8, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=-AL/2", "=ZL"], ["=AL/2", "=ZL"], ["=-AL/2", "=-ZL"], ["=AL/2", "=-ZL"]], tiefe: "=TG", gewindetiefe: "=GT"}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: Abstand Gewinde in x, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true}, soll: "=AL"}
```

`tests/referenz/zahnstangentrieb/leiste.yaml` anlegen:

```yaml
# Referenz Zahnstangentrieb (Spec 4b): Führungsleiste (zweimal verwendet) – wie im Linearschlitten (4a). Ursprung Mitte
# Unterseite; Senkungen für ISO 4762 M8 auf der Mittellinie.
art: teil
name: Leiste
material: "1.0038"
eigenschaften: {Benennung: Führungsleiste Zahnstangentrieb}
parameter: {L: 300, B: 20, H: 25, AL: 200}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: normbohrung, art: zylinderschraube, groesse: M8, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=-AL/2", 0], ["=AL/2", 0]], durch: true}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: Abstand Senkungen, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true}, soll: "=AL"}
```

`tests/referenz/zahnstangentrieb/schlitten.yaml` anlegen:

```yaml
# Referenz Zahnstangentrieb (Spec 4b): Schlitten zwischen den Leisten (wie 4a, ohne Drehbolzen). Ursprung Mitte
# Unterseite. Zwei Senkungen von unten für ISO 4762 M5, mit denen die Zahnstange auf dem Schlitten verschraubt ist.
art: teil
name: Schlitten
material: "1.0038"
eigenschaften: {Benennung: Schlitten Zahnstangentrieb}
parameter: {L: 80, B: 60, H: 25, XS: 25}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: normbohrung, art: zylinderschraube, groesse: M5, flaeche: {feature: f1, flaeche: "-y"},
     positionen: [["=-XS", 0], ["=XS", 0]], durch: true}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  masse_pruefen:
    - {was: Abstand Senkungen, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true}, soll: "=2*XS"}
```

`tests/referenz/zahnstangentrieb/zahnstange.yaml` anlegen:

```yaml
# Referenz Zahnstangentrieb (Spec 4b): Zahnstange m = M, Z Zähne, Breite B. Ursprung = Mitte von Zahn 1 auf der
# Profilmittellinie; die Zähne reihen sich entlang +x, Kopf nach +y. Rücken (Höhe H) bis zur Fußlinie y = −1,25·M,
# darunter zwei Gewinde M5 von unten im Abstand AB (Verschraubung mit dem Schlitten).
art: teil
name: Zahnstange
material: "1.0503"
eigenschaften: {Benennung: Zahnstange m2 Zahnstangentrieb}
parameter: {M: 2, Z: 30, AS: -0.05, H: 10, B: 20, XS: 10, AB: 50, TG: 8, GT: 6}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: vorne, elemente: [{rechteck: {mitte: ["=(Z-1)*pi*M/2", "=-1.25*M-H/2"], breite: "=Z*pi*M",
                                                  hoehe: "=H"}}]}
    ende: {typ: blind, tiefe: "=B"}
  - {id: z1, typ: verzahnung, art: zahnstange, ebene: vorne, mitte: [0, 0], modul: "=M", zaehne: "=Z", breite: "=B",
     zahndickenabmass: "=AS", kopf: "+v"}
  - {id: f2, typ: normbohrung, art: gewinde, groesse: M5, flaeche: {feature: f1, flaeche: "-y"},
     positionen: [["=XS", "=-B/2"], ["=XS+AB", "=-B/2"]], tiefe: "=TG", gewindetiefe: "=GT"}
pruefung:
  huellquader: ["=Z*pi*M", "=H+2.25*M", "=B"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: Abstand Gewinde, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true}, soll: "=AB"}
```

`tests/referenz/zahnstangentrieb/lagerbock.yaml` anlegen:

```yaml
# Referenz Zahnstangentrieb (Spec 4b): Lagerbock (zweimal verwendet, je einer auf jeder Führungsleiste). Ursprung Mitte
# Unterseite, Höhe HL in y, Dicke T in z. Zwei Lagerbohrungen DL für Ritzelwelle (YR) und Antriebswelle (YA); ihr
# Abstand ist der Achsabstand der Stirnradstufe m·(z1 + z2)/2 = 75.
art: teil
name: Lagerbock
material: "1.0038"
eigenschaften: {Benennung: Lagerbock Zahnstangentrieb}
parameter: {B: 40, HL: 165, T: 20, YR: 32.5, YA: 107.5, DL: 12.5}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: vorne, elemente: [{rechteck: {mitte: [0, "=HL/2"], breite: "=B", hoehe: "=HL"}}]}
    ende: {typ: blind, tiefe: "=T"}
  - {id: f2, typ: bohrung, flaeche: {feature: f1, flaeche: "+z"}, positionen: [[0, "=YR"], [0, "=YA"]],
     durchmesser: "=DL", durch: true}
pruefung:
  huellquader: ["=B", "=HL", "=T"]
  masse_pruefen:
    - {was: Achsabstand Lagerbohrungen, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true}, soll: "=YA-YR"}
```

`tests/referenz/zahnstangentrieb/ritzelwelle.yaml` anlegen:

```yaml
# Referenz Zahnstangentrieb (Spec 4b): Ritzelwelle – Welle Ø D entlang z (Länge 2·LW, mittig), Ritzel ZR Zähne
# (Breite BR, mittig) und Rad Z2 Zähne (Breite B2, ab z = ZA), beide m = M. Die Wellenabschnitte sparen die Räder aus
# (volumen auto). Achse = Bezugsachse ACHSE (z).
art: teil
name: Ritzelwelle
material: "1.0503"
eigenschaften: {Benennung: Ritzelwelle Zahnstangentrieb}
parameter: {M: 2, ZR: 20, Z2: 25, AS: -0.05, D: 12, LW: 60, BR: 20, ZA: 18, B2: 12}
features:
  - {id: z1, typ: verzahnung, art: stirnrad, ebene: {versatz: {ebene: vorne, abstand: "=-BR/2"}}, mitte: [0, 0],
     modul: "=M", zaehne: "=ZR", breite: "=BR", zahndickenabmass: "=AS"}
  - {id: z2, typ: verzahnung, art: stirnrad, ebene: {versatz: {ebene: vorne, abstand: "=ZA"}}, mitte: [0, 0],
     modul: "=M", zaehne: "=Z2", breite: "=B2", zahndickenabmass: "=AS"}
  - id: f1
    typ: extrusion
    skizze: {ebene: {versatz: {ebene: vorne, abstand: "=-LW"}}, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=D"}}]}
    ende: {typ: blind, tiefe: "=LW-BR/2"}
  - id: f2
    typ: extrusion
    skizze: {ebene: {versatz: {ebene: vorne, abstand: "=BR/2"}}, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=D"}}]}
    ende: {typ: blind, tiefe: "=ZA-BR/2"}
  - id: f3
    typ: extrusion
    skizze: {ebene: {versatz: {ebene: vorne, abstand: "=ZA+B2"}}, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=D"}}]}
    ende: {typ: blind, tiefe: "=LW-ZA-B2"}
  - {id: ACHSE, typ: referenz, achse: z}
pruefung:
  volumen: {soll: auto}
  masse_pruefen:
    - {was: Ritzel koaxial zur Achse, von: {feature: z1, instanz: 1, achse: true}, zu: {referenz: ACHSE}, soll: 0}
    - {was: Rad koaxial zur Achse, von: {feature: z2, instanz: 1, achse: true}, zu: {referenz: ACHSE}, soll: 0}
```

`tests/referenz/zahnstangentrieb/antriebswelle.yaml` anlegen:

```yaml
# Referenz Zahnstangentrieb (Spec 4b): Antriebswelle – Welle Ø D entlang z (Länge 2·LW, mittig) mit Rad Z1 Zähne
# (Breite B1, ab z = ZA), m = M. Die Wellenabschnitte sparen das Rad aus (volumen auto). Achse = Bezugsachse ACHSE (z).
art: teil
name: Antriebswelle
material: "1.0503"
eigenschaften: {Benennung: Antriebswelle Zahnstangentrieb}
parameter: {M: 2, Z1: 50, AS: -0.05, D: 12, LW: 60, ZA: 18, B1: 12}
features:
  - {id: z1, typ: verzahnung, art: stirnrad, ebene: {versatz: {ebene: vorne, abstand: "=ZA"}}, mitte: [0, 0],
     modul: "=M", zaehne: "=Z1", breite: "=B1", zahndickenabmass: "=AS"}
  - id: f1
    typ: extrusion
    skizze: {ebene: {versatz: {ebene: vorne, abstand: "=-LW"}}, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=D"}}]}
    ende: {typ: blind, tiefe: "=LW+ZA"}
  - id: f2
    typ: extrusion
    skizze: {ebene: {versatz: {ebene: vorne, abstand: "=ZA+B1"}}, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=D"}}]}
    ende: {typ: blind, tiefe: "=LW-ZA-B1"}
  - {id: ACHSE, typ: referenz, achse: z}
pruefung:
  volumen: {soll: auto}
  masse_pruefen:
    - {was: Rad koaxial zur Achse, von: {feature: z1, instanz: 1, achse: true}, zu: {referenz: ACHSE}, soll: 0}
```

`tests/referenz/zahnstangentrieb/eingabe/beschreibung.md` anlegen:

```markdown
# Zahnstangentrieb (Referenz Stufe 4b)

Auf einer Grundplatte 300 × 100 × 20 mm laufen wie beim Linearschlitten zwei Führungsleisten (300 × 20 × 25, je zwei
Zylinderschrauben ISO 4762 M8 in Gewinde der Grundplatte) und dazwischen ein Schlitten (80 × 60 × 25), der über einen
Hub von 120 mm von einem Ende der Grundplatte zur Mitte fährt. Auf dem Schlitten ist eine Zahnstange (Modul 2, 30 Zähne,
20 mm breit, Rücken 10 mm hoch) von unten mit zwei Zylinderschrauben ISO 4762 M5 verschraubt.

In der Mitte der Grundplatte steht auf jeder Leiste ein Lagerbock (40 × 165 × 20). In den Lagerböcken laufen zwei Wellen
Ø 12 übereinander: unten die Ritzelwelle mit einem Ritzel (20 Zähne, 20 mm breit) über der Zahnstange und einem Rad
(25 Zähne), darüber die Antriebswelle mit einem Rad (50 Zähne), Achsabstand 75 mm. Die Räder sind 12 mm breit und
liegen an der Innenseite des rechten Lagerbocks an. Alle Verzahnungen: Evolvente, Bezugsprofil DIN 867, Modul 2,
Zahndickenabmaß −0,05 mm (Flankenspiel).

Anforderungen: Hub 120 mm, begrenzt; fährt der Schlitten nach +x, dreht die Ritzelwelle um +z um 120·360/(π·40) ≈ 343,8°
und die Antriebswelle gegensinnig um die Hälfte; die Räder stehen Zahn in Lücke und laufen über den ganzen Hub
kollisionsfrei; Achsabstand 75 mm; die Achse der Ritzelwelle liegt 77,5 mm über der Unterseite der Grundplatte.
```

In `.claude/agents/pruefer.md` ersetzen:

```markdown
## Antwort (genau dieses JSON, sonst nichts)
```

durch:

```markdown
## Zusätzlich bei Verzahnungen (`typ: verzahnung` in einer Teil-Spec)

- Die Verzahnung ist vollständig: Zähnezahl wie in der Spezifikation, keine fehlenden, verschmolzenen oder spitzen Zähne
  (Bild senkrecht zur Radebene, meist `vorne`).
- Die Zahnform ist symmetrisch, Kopf- und Fußkreis sind erkennbar; das Rad sitzt an der richtigen Stelle der Welle
  (Abstände entlang der Achse wie in der Spezifikation).
- `verzahnungen` im Prüfbericht ist ok (Kopf-/Fußkreis, Zähnezahl, Zahnweite bzw. Kopflinie, Teilung, Zahndicke). Der
  Zahnfuß ist vereinfacht (radiale Verlängerung und Fußrundung statt Trochoide) – das ist kein Mangel.

## Antwort (genau dieses JSON, sonst nichts)
```

In `.claude/skills/konstruieren/SKILL.md` ersetzen:

```markdown
  muss auf der gemeinten `flaeche` liegen (kein Absatz davor, sonst Abbruch).
```

durch:

```markdown
  muss auf der gemeinten `flaeche` liegen (kein Absatz davor, sonst Abbruch).
- Zahnräder und Zahnstangen als `typ: verzahnung` (Spec 4b, Vorlage `tests/referenz/zahnstangentrieb/`): `art:
  stirnrad | zahnstange`, `ebene` (Standardebene oder `versatz`, keine Fläche), `mitte` (Stirnrad: Radachse;
  Zahnstange: Mitte von Zahn 1 auf der Profilmittellinie), `modul` (DIN 780 Reihe 1), `zaehne` (Stirnrad ≥ 17),
  `breite`, `zahndickenabmass` (< 0 für Flankenspiel, z. B. −0,05 bei m 2); Stirnrad optional `winkel` (Zahn 1 gegen
  +u), Zahnstange optional `kopf: "-v"`; Anforderungswerte als Parameter. Das Feature baut das ganze Rad bzw. nur das
  Zahnband der Zahnstange: den Rücken als eigene Extrusion genau bis an die Fußlinie (1,25·m unter der
  Profilmittellinie), sonst entstehen zwei Körper. Wellen mit Rädern: Räder als `verzahnung`, die Wellenabschnitte
  zwischen ihnen als Kreis-Extrusionen ohne Überlappung (Ausnahme von Modellierregel 1, sonst stimmt `volumen: auto`
  nicht). Radachse: `{feature: <id>, instanz: 1, achse: true}`. In Ausdrücken ist `pi` erlaubt (Zahnstangenlänge
  `=Z*pi*M`). `swki pruefen` prüft Kopf-/Fußkreis, Zähnezahl und Zahnweite bzw. Teilung und Zahndicke selbst
  (`verzahnungen`); `huellquader` bei Rädern weglassen (die Box hängt von der Lage der Zähne ab).
```


- [ ] **Step 3: Validieren ohne SolidWorks**

Run (PowerShell, im Projekt): für `zahnstange.yaml`, `ritzelwelle.yaml`, `antriebswelle.yaml`, `lagerbock.yaml`,
`schlitten.yaml` je `.venv\Scripts\python.exe -m swki validieren tests\referenz\zahnstangentrieb\<datei>`
Expected: `"gueltig": true`, `"hinweise": []` (vorab geprüft). Die Freigabe-Dateien entstehen erst im Test (Kopie in
`tmp_path`) – im Repo-Ordner nicht freigeben.

- [ ] **Step 4: Ganze Suite**

`.venv\Scripts\python.exe -m pytest -q` → **763 passed, 126 deselected**.

- [ ] **Step 5: Teil-Referenzen live**

SolidWorks frisch. Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py "tests\referenz\test_referenzen.py::test_referenz_besteht[zahnstangentrieb-zahnstange.yaml]" "tests\referenz\test_referenzen.py::test_referenz_besteht[zahnstangentrieb-ritzelwelle.yaml]" "tests\referenz\test_referenzen.py::test_referenz_besteht[zahnstangentrieb-antriebswelle.yaml]" --zeit 600`
Expected: 3 × `OK`. Ein Mangel heißt: Bauweg der Teil-Spec nachbessern (Features, Reihenfolge), nie Parameter, Material,
Eigenschaften oder `pruefung` (Freigabe-Regel), und nie die Erwartung. Je Lauf Dauer und Private Bytes notieren.

- [ ] **Step 6: Prüfer-Urteile (Controller)**

Für jede der drei Teil-Referenzen einen Lauf in `auftraege/REF-4B-<teil>/` anlegen (Kopie des Referenzordners, `validieren`,
`freigeben`, `bauen`, `pruefen`), dann meldet der Implementer BLOCKED (Prüfer). Der Controller startet den Prüfer-Agenten
(`subagent_type: pruefer`) mit Eingabe (`eingabe/`), freigegebener Spec, Prüfbericht und Bildern; das Urteil wird
unverändert nach `protokolle/<spec>.lauf-<n>.pruefer.json` geschrieben, `swki status` muss „bestanden“ zeigen. Aufträge
danach löschen (`auftraege/` wird nicht committet).

- [ ] **Step 7: Negativfall E1**

SolidWorks frisch. Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py "tests\live\test_live_verzahnung.py::test_negativ_zahnweite" --zeit 600`
Expected: `OK` (genau `{verzahnungen}`, Knoten `z1`, Abweichung „zahnweite W6“).

- [ ] **Step 8: Regression der Teile**

SolidWorks frisch. `buchse`, `formplatte`, `auswerferhalteplatte` aus `tests/referenz/test_referenzen.py` einzeln
(`--zeit 600`) → 3 × `OK`.

- [ ] **Step 9: Zwischenstand**

`docs/stufe4b/ergebnisse.md` anlegen und die Messwerte eintragen:

```markdown
# Stufe 4b – Ergebnisse (Verzahnung und Kopplungen)

Fertig-Kriterium Spec 4b §12 für Rechner A (SW 2025). Rechner B (SW 2026) offen.

## 1. Etappe 1 – Verzahnung (Zwischenstand <Datum>)

- Spike S14a (`docs/stufe0/ergebnisse/s14a_verzahnung.json`): Tabelle je Zeile 1–6 mit Ergebnis (gemessen) und
  Entscheidung (Ruling) wie in `docs/stufe4a/ergebnisse.md` Abschnitt 2.
- Testzahlen: Unit-Tests 711 → 763 bestanden, abgewählt 117 → 126 (Zuwachs je Task).
- Teil-Referenzen Zahnstange, Ritzelwelle, Antriebswelle: Dauer, Private Bytes vorher → Spitze → nachher, Prüfer-Urteil.
- Negativfall E1: Mängelmenge, Dauer.
- Regression Buchse, Formplatte, Auswerferhalteplatte.
- Abweichungen von der Spec (Rulings mit „Wenn falsch“) und offene Punkte.
```

- [ ] **Step 10: Commit**

```powershell
git add tests/referenz/zahnstangentrieb tests/referenz/test_referenzen.py tests/live/test_live_verzahnung.py .claude/agents/pruefer.md .claude/skills/konstruieren/SKILL.md docs/stufe4b/ergebnisse.md
git commit -m "referenz: Teile des Zahnstangentriebs, Negativfall Zahnweite, Prüfer und Skill für Verzahnungen (Stufe 4b, Task 6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Etappe 1 abgeschlossen**, wenn Steps 5–8 bestanden haben. Der Controller hält das im Ledger fest; erst dann beginnt Task 7.

---

# Etappe 2 – Kopplungen in der Baugruppe

### Task 7: Kopplungsrechnung (`swki/baugruppe/kopplung.py`, ohne SolidWorks)

**Files:**
- Create: `swki/baugruppe/kopplung.py`
- Modify: `swki/baugruppe/geometrie.py` (neu `drehmatrix`), `swki/baugruppe/bewegung.py` (importiert sie)
- Test: `tests/baugruppe/test_kopplung.py`

**Interfaces:**
- Consumes: `swki.verzahnung` (`Stirnrad`, `Zahnstange`, `Verzahnung`, `verzahnung_im_teil`), `drehmatrix`.
- Produces: `KOPPLUNGEN = ("zahnrad", "zahnstange")`, `GEKOPPELT = "gekoppelt"`; `Rad(punkt, achse, zahn, geo, breite)`,
  `Stange(punkt, reihe, kopf, achse, geo, breite)`; `winkel_um(a, b, n)`, `in_baugruppe(vz, t) -> Rad | Stange`,
  `verzahnung_der_seite(quellen, seite) -> Verzahnung`, `teilkreise(a, b) -> (zaehler_mm, nenner_mm)`,
  `phasenfehler(a, b) -> float` (Anteil der Teilung in (−0,5; 0,5]), `phasenwinkel(a, b) -> float` (Grad),
  `drehe(t, punkt, achse, winkel) -> list[float]` (Transform2.ArrayData), `eingriff(a, b) -> dict` (`achsen_parallel`,
  `achsabstand`, `soll`, `ueberdeckung`, `im_bereich`), `kopplungen(spec)`, `mitglieder(spec, name)`,
  `antriebsmenge(spec, kid)`, `gekoppelte(spec, start) -> list[str]`, `soll_drehungen(spec, quellen, bewegt, art, bereich,
  wege) -> dict[str, float]`, `endlagen_wege(bewegung, p)`; `swki.baugruppe.geometrie.drehmatrix(achse, winkel)`.

- [ ] **Step 1: Tests schreiben**

`tests/baugruppe/test_kopplung.py` anlegen:

```python
"""Kopplungsrechnung ohne SolidWorks (Spec 4b §5): Lage, Zahnphase, Abrollen, Drehung, Eingriff, Graph, Übersetzung."""

import math

import pytest

from swki.baugruppe.bewegung import drehmatrix
from swki.baugruppe.kopplung import (Rad, Stange, drehe, eingriff, endlagen_wege, gekoppelte, in_baugruppe,
                                     phasenfehler, phasenwinkel, soll_drehungen, teilkreise, winkel_um)
from swki.baugruppe.modell import Quelle
from swki.verzahnung import Stirnrad, Zahnstange, verzahnung_im_teil

Z = (0.0, 0.0, 1.0)
EINS = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]


def _dreh(v, winkel, achse=Z):
    q = drehmatrix(achse, winkel)
    return tuple(sum(q[i][k] * v[k] for k in range(3)) for i in range(3))


def _rad(z, punkt=(0.0, 0.0, 0.0), zahn_grad=0.0, achse=Z, breite=(0.0, 10.0)):
    zahn = _dreh((1.0, 0.0, 0.0), zahn_grad, Z)
    return Rad(punkt, achse, zahn, Stirnrad(2.0, z, -0.05), breite)


def _stange(punkt=(0.0, 0.0, 0.0), z=20):
    return Stange(punkt, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), Z, Zahnstange(2.0, z, -0.05), (0.0, 20.0))


def test_winkel_um():
    assert math.degrees(winkel_um((1, 0, 0), (0, 1, 0), Z)) == pytest.approx(90)
    assert math.degrees(winkel_um((1, 0, 0), (0, -1, 0), Z)) == pytest.approx(-90)
    assert math.degrees(winkel_um((1, 0, 5), (0, 1, -3), Z)) == pytest.approx(90)  # Anteile entlang der Achse zählen nicht


def test_zahnrad_zahn_in_luecke():
    a = _rad(50)                                                   # Zahn 1 zeigt zu b
    b = _rad(25, punkt=(75.0, 0.0, 0.0), zahn_grad=180 + 360 / 50)  # Lücke von b zeigt zu a (halbe Teilung von b = 7,2°)
    assert phasenfehler(a, b) == pytest.approx(0.0, abs=1e-12)


def test_zahnrad_zahn_auf_zahn_halbe_teilung():
    a, b = _rad(50), _rad(25, punkt=(75.0, 0.0, 0.0), zahn_grad=180)
    assert abs(phasenfehler(a, b)) == pytest.approx(0.5)
    assert abs(phasenwinkel(a, b)) == pytest.approx(3.6)


@pytest.mark.parametrize(("za", "zb", "lage", "zahn_a", "zahn_b"), [
    (50, 25, (75.0, 0.0, 0.0), 13.0, 41.0), (20, 40, (0.0, 60.0, 5.0), -100.0, 3.0), (17, 23, (-28.0, -28.0, 0.0), 0.0, 0.0)])
def test_zahnrad_phase_herstellen_und_abrollen(za, zb, lage, zahn_a, zahn_b):
    a, b = _rad(za, zahn_grad=zahn_a), _rad(zb, punkt=lage, zahn_grad=zahn_b)
    w = phasenwinkel(a, b)
    a = Rad(a.punkt, a.achse, _dreh(a.zahn, w), a.geo, a.breite)
    assert phasenfehler(a, b) == pytest.approx(0.0, abs=1e-9)
    for theta in (5.0, 33.0, 400.0):  # Abrollen: a um +θ, b gegensinnig um θ·za/zb
        a2 = Rad(a.punkt, a.achse, _dreh(a.zahn, theta), a.geo, a.breite)
        b2 = Rad(b.punkt, b.achse, _dreh(b.zahn, -theta * za / zb), b.geo, b.breite)
        assert abs(phasenfehler(a2, b2)) == pytest.approx(0.0, abs=1e-9)


def test_zahnrad_gegenlaeufige_achse_misst_um_a():
    a = _rad(50)
    b = _rad(25, punkt=(75.0, 0.0, 0.0), zahn_grad=180 + 360 / 50, achse=(0.0, 0.0, -1.0))
    assert phasenfehler(a, b) == pytest.approx(0.0, abs=1e-12)


def test_zahnstange_zahn_in_luecke_und_abrollen():
    st = _stange()
    a = _rad(20, punkt=(0.0, 20.0, 0.0), zahn_grad=-90 + 9)  # Lücke des Ritzels (Teilung 18°) zeigt zur Zahnstange
    assert phasenfehler(a, st) == pytest.approx(0.0, abs=1e-12)
    for s in (3.0, 25.0, 130.0):  # Zahnstange um s nach +x, Ritzel rollt um s/r gegen den Uhrzeigersinn (σ = +1)
        st2 = _stange(punkt=(s, 0.0, 0.0))
        a2 = Rad(a.punkt, a.achse, _dreh(a.zahn, math.degrees(s / 20)), a.geo, a.breite)
        assert abs(phasenfehler(a2, st2)) == pytest.approx(0.0, abs=1e-9)


def test_zahnstange_phase_herstellen():
    st = _stange(punkt=(1.3, 0.0, 0.0))
    a = _rad(20, punkt=(40.0, 20.0, 7.0), zahn_grad=11.0)
    a = Rad(a.punkt, a.achse, _dreh(a.zahn, phasenwinkel(a, st)), a.geo, a.breite)
    assert phasenfehler(a, st) == pytest.approx(0.0, abs=1e-9)


def test_drehe_um_achse_durch_punkt():
    t = drehe(EINS, (10.0, 0.0, 0.0), Z, 90)
    assert t[0:3] == pytest.approx([0, 1, 0])        # Bild der x-Achse
    assert t[9:12] == pytest.approx([0.01, -0.01, 0])  # Ursprung (m): (0,0,0) um (10,0,0) gedreht
    assert t[12:] == EINS[12:]


def test_in_baugruppe_mit_lage():
    f = {"id": "z1", "art": "stirnrad", "ebene": {"versatz": {"ebene": "vorne", "abstand": 30}}, "mitte": [0, 0],
         "modul": 2, "zaehne": 20, "breite": 16, "zahndickenabmass": -0.05}
    t = drehe(EINS, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90)  # Teil um y gedreht: Teil-z → Baugruppe +x
    t[9:12] = [0.1, 0.0, 0.0]
    rad = in_baugruppe(verzahnung_im_teil(f, {}), t)
    assert rad.punkt == pytest.approx((130.0, 0.0, 0.0))
    assert rad.achse == pytest.approx((1.0, 0.0, 0.0))
    assert rad.breite == pytest.approx((130.0, 146.0))


def test_eingriff_zahnrad():
    a, b = _rad(50), _rad(25, punkt=(75.0, 0.0, 5.0), breite=(5.0, 20.0))
    e = eingriff(a, b)
    assert e == {"achsen_parallel": True, "achsabstand": 75.0, "soll": 75.0, "ueberdeckung": 5.0, "im_bereich": True}
    assert eingriff(a, _rad(25, punkt=(75.0, 0.0, 0.0), breite=(-8.0, 0.0), achse=(0.0, 0.0, -1.0)))["ueberdeckung"] == 8.0


def test_eingriff_zahnstange():
    st = _stange(z=20)
    e = eingriff(_rad(20, punkt=(30.0, 20.0, 0.0), breite=(2.0, 18.0)), st)
    assert e == {"achsen_parallel": True, "achsabstand": 20.0, "soll": 20.0, "ueberdeckung": 16.0, "im_bereich": True}
    assert eingriff(_rad(20, punkt=(200.0, 20.0, 0.0)), st)["im_bereich"] is False


def test_teilkreise():
    assert teilkreise(Stirnrad(2, 50), Stirnrad(2, 25)) == (100, 50)
    assert teilkreise(Stirnrad(2, 20), Zahnstange(2, 9)) == (40, 0.0)


def _rad_spec(name, *zaehne):
    return {"art": "teil", "name": name, "features": [
        {"id": f"z{i}", "typ": "verzahnung", "art": "stirnrad", "ebene": "vorne", "mitte": [0, 0], "modul": 2,
         "zaehne": z, "breite": 10, "zahndickenabmass": -0.05} for i, z in enumerate(zaehne, start=1)]}


STANGE_SPEC = {"art": "teil", "name": "S", "features": [
    {"id": "z1", "typ": "verzahnung", "art": "zahnstange", "ebene": "vorne", "mitte": [0, 0], "modul": 2, "zaehne": 40,
     "breite": 10, "zahndickenabmass": -0.05}]}
TRIEB = {
    "komponenten": [{"id": "grundplatte", "fixiert": True}, {"id": "schlitten", "gruppe": "schieber"},
                    {"id": "zahnstange", "gruppe": "schieber"}, {"id": "ritzelwelle"}, {"id": "antriebswelle"}],
    "verknuepfungen": [
        {"id": "k1", "typ": "zahnstange", "a": {"komponente": "ritzelwelle", "feature": "z1"},
         "b": {"komponente": "zahnstange", "feature": "z1"}},
        {"id": "k2", "typ": "zahnrad", "a": {"komponente": "antriebswelle", "feature": "z1"},
         "b": {"komponente": "ritzelwelle", "feature": "z2"}}],
    "freiheitsgrade": {"schieber": 1, "ritzelwelle": "gekoppelt", "antriebswelle": "gekoppelt"},
}
QUELLEN = {"ritzelwelle": Quelle("teil", _rad_spec("R", 20, 25)), "antriebswelle": Quelle("teil", _rad_spec("A", 50)),
           "zahnstange": Quelle("teil", STANGE_SPEC)}


def test_gekoppelte():
    assert gekoppelte(TRIEB, {"schlitten", "zahnstange"}) == ["ritzelwelle", "antriebswelle"]
    assert gekoppelte(TRIEB, {"grundplatte"}) == []


def test_soll_drehungen_aus_der_uebersetzung():
    soll = soll_drehungen(TRIEB, QUELLEN, {"schlitten", "zahnstange"}, "abstand", 220.0, {})
    assert soll["ritzelwelle"] == pytest.approx(220 * 360 / (math.pi * 40))
    assert soll["antriebswelle"] == pytest.approx(220 * 360 / (math.pi * 40) * 25 / 50)


def test_soll_drehungen_mit_weg_aus_endlage():
    soll = soll_drehungen(TRIEB, QUELLEN, {"schlitten"}, "abstand", 220.0, {"zahnstange": 110.0})
    assert soll["ritzelwelle"] == pytest.approx(110 * 360 / (math.pi * 40))


def test_endlagen_wege():
    b = {"erwartet": {"endlagen": [{"komponente": "zahnstange", "verschiebung": ["=HUB", 0, 0]},
                                   {"komponente": "ritzelwelle", "drehung": {"achse": [0, 0, 1], "winkel": 5}}]}}
    assert endlagen_wege(b, {"HUB": 220}) == {"zahnstange": 220.0}
```


- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_kopplung.py`
Expected: FAIL – `1 error` beim Sammeln (`ModuleNotFoundError: swki.baugruppe.kopplung`).

- [ ] **Step 3: Umsetzen**

`swki/baugruppe/kopplung.py` anlegen:

```python
"""Kopplungen über Verzahnungen (Spec 4b §5) ohne SolidWorks: Kopplungsgraph, abgeleitete Übersetzung, Zahnphase,
Eingriff und die Drehung einer Komponente um ihre Achse.

Lagen in Baugruppenkoordinaten (mm) aus der Teil-Lage (swki.verzahnung.Verzahnung) und Transform2.ArrayData
(Zeilenvektor-Konvention wie swki.baugruppe.geometrie.transformiere, Verschiebung in m)."""

import math
from dataclasses import dataclass

from swki.baugruppe.geometrie import drehmatrix
from swki.spec.ausdruck import auswerten
from swki.verbindung import in_mm, mm
from swki.verzahnung import Stirnrad, Verzahnung, Zahnstange, verzahnung_im_teil

KOPPLUNGEN = ("zahnrad", "zahnstange")
GEKOPPELT = "gekoppelt"
_PARALLEL = 1.0 - 1e-6

Vektor = tuple[float, float, float]


def _sk(a: Vektor, b: Vektor) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _kreuz(a: Vektor, b: Vektor) -> Vektor:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _diff(a: Vektor, b: Vektor) -> Vektor:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _einheit(a: Vektor) -> Vektor:
    n = math.sqrt(_sk(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def _senkrecht(a: Vektor, n: Vektor) -> Vektor:
    """Anteil von a senkrecht zur Einheitsrichtung n."""
    t = _sk(a, n)
    return (a[0] - t * n[0], a[1] - t * n[1], a[2] - t * n[2])


def winkel_um(a: Vektor, b: Vektor, n: Vektor) -> float:
    """Vorzeichenbehafteter Winkel (rad) von a nach b um die Einheitsachse n (Rechte-Hand-Regel)."""
    a, b = _senkrecht(a, n), _senkrecht(b, n)
    return math.atan2(_sk(n, _kreuz(a, b)), _sk(a, b))


def _bruch(x: float) -> float:
    """Anteil in [0, 1)."""
    return x - math.floor(x)


def _gefaltet(x: float) -> float:
    """Anteil in (−0,5; 0,5]."""
    x = _bruch(x)
    return x - 1.0 if x > 0.5 else x


# --- Lage in der Baugruppe -----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Rad:
    """Stirnrad in Baugruppenkoordinaten."""
    punkt: Vektor     # Punkt auf der Radachse (mm)
    achse: Vektor     # Einheitsrichtung (Normale der Skizzenebene)
    zahn: Vektor      # Einheitsrichtung von der Achse zur Mitte von Zahn 1
    geo: Stirnrad
    breite: tuple[float, float]  # Bereich entlang achse (Skalarprodukt mit achse, mm)


@dataclass(frozen=True)
class Stange:
    """Zahnstange in Baugruppenkoordinaten."""
    punkt: Vektor     # Mitte von Zahn 1 auf der Profilmittellinie (mm)
    reihe: Vektor     # Einheitsrichtung der Zahnreihe
    kopf: Vektor      # Einheitsrichtung der Zähne
    achse: Vektor     # Breitenrichtung (Normale der Skizzenebene)
    geo: Zahnstange
    breite: tuple[float, float]


def _punkt(p: Vektor, t) -> Vektor:
    return tuple(p[0] * t[i] + p[1] * t[3 + i] + p[2] * t[6 + i] + in_mm(t[9 + i]) for i in range(3))


def _richtung(v: Vektor, t) -> Vektor:
    return _einheit(tuple(v[0] * t[i] + v[1] * t[3 + i] + v[2] * t[6 + i] for i in range(3)))


def in_baugruppe(vz: Verzahnung, t) -> Rad | Stange:
    """Verzahnung (Teilkoordinaten) mit der Lage t der Komponente in Baugruppenkoordinaten."""
    achse = _richtung(vz.normale, t)
    versatz = _sk(tuple(in_mm(t[9 + i]) for i in range(3)), achse)  # Drehung erhält Skalarprodukte, die Verschiebung nicht
    breite = (vz.breite[0] + versatz, vz.breite[1] + versatz)
    if isinstance(vz.geo, Stirnrad):
        return Rad(_punkt(vz.bezugspunkt, t), achse, _richtung(vz.zahnrichtung, t), vz.geo, breite)
    return Stange(_punkt(vz.bezugspunkt, t), _richtung(vz.zahnrichtung, t), _richtung(vz.kopfrichtung, t), achse, vz.geo,
                  breite)


def verzahnung_der_seite(quellen: dict, seite: dict) -> Verzahnung:
    """Verzahnung, auf die eine Kopplungsseite {komponente, feature} zeigt (Teil-Spec der Quelle)."""
    from swki.baugruppe.aufloesen import basis

    spec = quellen[basis(seite["komponente"])].spec
    f = next(x for x in spec["features"] if x["id"] == seite["feature"])
    return verzahnung_im_teil(f, spec.get("parameter", {}))


# --- Übersetzung ---------------------------------------------------------------------------------------------------


def teilkreise(a: Stirnrad, b: Stirnrad | Zahnstange) -> tuple[float, float]:
    """Zähler/Nenner der Zahnradverknüpfung (Teilkreis-Ø in mm, wie IGearMateFeatureData) bzw. (Teilkreis-Ø des Ritzels,
    0) bei der Zahnstange."""
    return (a.m * a.z, b.m * b.z) if isinstance(b, Stirnrad) else (a.m * a.z, 0.0)


# --- Zahnphase -----------------------------------------------------------------------------------------------------


def phasenfehler(a: Rad, b: Rad | Stange) -> float:
    """Phasenfehler von a gegenüber b als Anteil der Teilung von a in (−0,5; 0,5] (0 = Zahn in Lücke, Spec 4b §5.4).

    Zahnrad: fa + fb ≡ 0,5 mit fa = Lage der Zahnmitte von a zur Mittenlinie a→b und fb = Lage von b zur Gegenrichtung,
    beide um a.achse gemessen. Zahnstange: fa − σ·fr ≡ 0,5 mit fr = Lage der Zahnstange am Wälzpunkt (Teilung) und
    σ = (achse × e)·reihe (Abrollsinn); e zeigt von der Radachse zum Wälzpunkt."""
    n, tau_a = a.achse, 2 * math.pi / a.geo.z
    if isinstance(b, Rad):
        e = _einheit(_senkrecht(_diff(b.punkt, a.punkt), n))
        fa = _bruch(winkel_um(a.zahn, e, n) / tau_a)
        fb = _bruch(winkel_um(b.zahn, (-e[0], -e[1], -e[2]), n) / (2 * math.pi / b.geo.z))
        return _gefaltet(fa - (0.5 - fb))
    w = tuple(b.punkt[i] + b.reihe[i] * _sk(_diff(a.punkt, b.punkt), b.reihe) for i in range(3))
    e = _einheit(_senkrecht(_diff(w, a.punkt), n))
    fr = _bruch(_sk(_diff(w, b.punkt), b.reihe) / b.geo.p)
    sigma = 1.0 if _sk(_kreuz(n, e), b.reihe) > 0 else -1.0
    fa = _bruch(winkel_um(a.zahn, e, n) / tau_a)
    return _gefaltet(fa - (0.5 + sigma * fr))


def phasenwinkel(a: Rad, b: Rad | Stange) -> float:
    """Drehung von a um a.achse in Grad (Rechte-Hand-Regel), die den Phasenfehler aufhebt."""
    return phasenfehler(a, b) * 360.0 / a.geo.z


def drehe(t, punkt: Vektor, achse: Vektor, winkel: float) -> list[float]:
    """Transform2.ArrayData nach einer Drehung der Komponente um die Achse (punkt in mm, achse) um winkel Grad."""
    q = drehmatrix(achse, winkel)
    c = [[t[3 * j + i] for j in range(3)] for i in range(3)]
    neu_c = [[sum(q[i][k] * c[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    v = [in_mm(t[9 + i]) - punkt[i] for i in range(3)]
    neu_v = [sum(q[i][k] * v[k] for k in range(3)) + punkt[i] for i in range(3)]
    return [neu_c[k % 3][k // 3] for k in range(9)] + [mm(x) for x in neu_v] + list(t[12:16])


# --- Eingriff ------------------------------------------------------------------------------------------------------


def _ueberdeckung(a: tuple[float, float], b: tuple[float, float], gleichsinnig: bool) -> float:
    """Länge der Überdeckung zweier Bereiche entlang derselben Achse (b ggf. gespiegelt)."""
    b = b if gleichsinnig else (-b[1], -b[0])
    return min(a[1], b[1]) - max(a[0], b[0])


def eingriff(a: Rad, b: Rad | Stange) -> dict:
    """Ist-Werte des Eingriffs (Spec 4b §5.5): parallel/senkrecht, Abstand, Soll, Breitenüberdeckung, Wälzpunkt."""
    if isinstance(b, Rad):
        cos = _sk(a.achse, b.achse)
        d = _senkrecht(_diff(b.punkt, a.punkt), a.achse)
        abstand = math.sqrt(_sk(d, d))
        return {"achsen_parallel": abs(cos) > _PARALLEL, "achsabstand": round(abstand, 6),
                "soll": round(a.geo.m * (a.geo.z + b.geo.z) / 2, 6),
                "ueberdeckung": round(_ueberdeckung(a.breite, b.breite, cos > 0), 6), "im_bereich": True}
    senkrecht = abs(_sk(a.achse, b.reihe)) < 1e-6 and abs(_sk(a.achse, b.kopf)) < 1e-6
    lage = _sk(_diff(a.punkt, b.punkt), b.reihe)
    return {"achsen_parallel": senkrecht, "achsabstand": round(_sk(_diff(a.punkt, b.punkt), b.kopf), 6),
            "soll": round(a.geo.r, 6), "ueberdeckung": round(_ueberdeckung(a.breite, b.breite, _sk(a.achse, b.achse) > 0), 6),
            "im_bereich": -b.geo.p / 2 <= lage <= (b.geo.z - 0.5) * b.geo.p}


# --- Kopplungsgraph ------------------------------------------------------------------------------------------------


def kopplungen(spec: dict) -> list[dict]:
    return [v for v in spec.get("verknuepfungen", []) if v["typ"] in KOPPLUNGEN]


def mitglieder(spec: dict, name: str) -> set[str]:
    """Komponente bzw. alle Mitglieder der Gruppe name."""
    gruppe = {k["id"] for k in spec["komponenten"] if k.get("gruppe") == name}
    return gruppe or {name}


def antriebsmenge(spec: dict, kid: str) -> set[str]:
    """Bewegte Komponente einer Bewegung samt ihrer Gruppe, wenn die Gruppe den Freiheitsgrad trägt."""
    gruppe = next((k.get("gruppe") for k in spec["komponenten"] if k["id"] == kid), None)
    return mitglieder(spec, gruppe) if gruppe and spec.get("freiheitsgrade", {}).get(gruppe) == 1 else {kid}


def gekoppelte(spec: dict, start: set[str]) -> list[str]:
    """Komponenten mit freiheitsgrade: gekoppelt, die über Kopplungen von start aus erreichbar sind (Spec-Reihenfolge der
    Komponenten). Weitergereicht wird nur über gekoppelte Komponenten."""
    fg = spec.get("freiheitsgrade", {})
    erreicht, neu = set(start), set(start)
    while neu:
        weiter = set()
        for v in kopplungen(spec):
            ka, kb = v["a"]["komponente"], v["b"]["komponente"]
            for von, nach in ((ka, kb), (kb, ka)):
                if von in neu and nach not in erreicht and fg.get(nach) == GEKOPPELT:
                    weiter.add(nach)
        erreicht |= weiter
        neu = weiter
    return [k["id"] for k in spec["komponenten"] if k["id"] in erreicht - set(start)]


def soll_drehungen(spec: dict, quellen: dict, bewegt: set[str], art: str, bereich: float,
                   wege: dict[str, float]) -> dict[str, float]:
    """Betrag der Drehung (Grad) jeder über Kopplungen getriebenen Komponente für eine Bewegung (Spec 4b §5.2,
    UEBERSETZUNG_WIDERSPRUCH). bewegt: Mitglieder der bewegten Komponente bzw. Gruppe; art/bereich der Bewegung
    (Abstand mm bzw. Winkel Grad); wege: Betrag der Endlage-Verschiebung je Komponente (mm, für Zahnstangen außerhalb
    der bewegten Menge)."""
    drehung = {k: bereich for k in bewegt} if art == "winkel" else {}
    weg = {k: bereich for k in bewegt} if art == "abstand" else {}
    weg |= {k: w for k, w in wege.items() if k not in weg}
    geaendert = True
    while geaendert:
        geaendert = False
        for v in kopplungen(spec):
            ka, kb = v["a"]["komponente"], v["b"]["komponente"]
            a = verzahnung_der_seite(quellen, v["a"]).geo
            b = verzahnung_der_seite(quellen, v["b"]).geo
            if v["typ"] == "zahnstange":
                if ka not in drehung and kb in weg:
                    drehung[ka] = weg[kb] * 360.0 / (math.pi * a.m * a.z)
                    geaendert = True
            else:
                for x, gx, y, gy in ((ka, a, kb, b), (kb, b, ka, a)):
                    if x in drehung and y not in drehung:
                        drehung[y] = drehung[x] * gx.z / gy.z
                        geaendert = True
    return {k: w for k, w in drehung.items() if k not in bewegt}


def endlagen_wege(bewegung: dict, p: dict) -> dict[str, float]:
    """Betrag der erwarteten Verschiebung je Komponente aus erwartet.endlagen (mm)."""
    ergebnis = {}
    for e in bewegung.get("erwartet", {}).get("endlagen", []):
        if "verschiebung" in e:
            ergebnis[e["komponente"]] = math.sqrt(sum(auswerten(w, p) ** 2 for w in e["verschiebung"]))
    return ergebnis
```

In `swki/baugruppe/bewegung.py` diesen Block entfernen:

```python
def drehmatrix(achse, winkel: float) -> list[list[float]]:
    """Drehung um achse (wird normiert) um winkel Grad nach der Rechte-Hand-Regel, Spaltenform (Rodrigues)."""
    n = math.sqrt(sum(c * c for c in achse))
    x, y, z = (c / n for c in achse)
    a = math.radians(winkel)
    c, s = math.cos(a), math.sin(a)
    k = 1 - c
    return [[c + x * x * k, x * y * k - z * s, x * z * k + y * s],
            [y * x * k + z * s, c + y * y * k, y * z * k - x * s],
            [z * x * k - y * s, z * y * k + x * s, c + z * z * k]]
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
from swki.baugruppe.bewertung import STATUS_TEXT, UNTERBESTIMMT, VOLL_BESTIMMT
```

durch:

```python
from swki.baugruppe.bewertung import STATUS_TEXT, UNTERBESTIMMT, VOLL_BESTIMMT
from swki.baugruppe.geometrie import drehmatrix
```

In `swki/baugruppe/geometrie.py` ersetzen:

```python
def einschraublaenge(
```

durch:

```python
def drehmatrix(achse, winkel: float) -> list[list[float]]:
    """Drehung um achse (wird normiert) um winkel Grad nach der Rechte-Hand-Regel, Spaltenform (Rodrigues)."""
    n = math.sqrt(sum(c * c for c in achse))
    x, y, z = (c / n for c in achse)
    a = math.radians(winkel)
    c, s = math.cos(a), math.sin(a)
    k = 1 - c
    return [[c + x * x * k, x * y * k - z * s, x * z * k + y * s],
            [y * x * k + z * s, c + y * y * k, y * z * k - x * s],
            [z * x * k - y * s, z * y * k + x * s, c + z * z * k]]


def einschraublaenge(
```


- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_kopplung.py` → `18 passed`. Ganze Suite → **781 passed,
126 deselected**; `pruefe-code` ohne Befund.

- [ ] **Step 5: Commit**

```powershell
git add swki/baugruppe/kopplung.py swki/baugruppe/geometrie.py swki/baugruppe/bewegung.py tests/baugruppe/test_kopplung.py
git commit -m "baugruppe: Kopplungsrechnung – Zahnphase, Abrollen, Eingriff, Übersetzung, Kopplungsgraph (Stufe 4b, Task 7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Spike S14b – Kopplungen an der Getriebeprobe (live)

**Files:**
- Create: `spikes/s14b_kopplung.py`, `tests/live/getriebeprobe/platte.yaml`, `tests/live/getriebeprobe/getriebeprobe.yaml`
- Ergebnis: `docs/stufe0/ergebnisse/s14b_kopplung.json`

**Interfaces:**
- Consumes: Task 1–7 (Handler, Teil-Specs der Referenz, `kopplung`), `sw_baugruppe` (`neue_baugruppe`, `fuege_ein`,
  `fixiere`, `verknuepfe`, `treibe`, `stelle`, `loesche`, `unterdruecke`, `interferenzen`, `status`, `transform`),
  `loese_im_teil`, `aufloesen.verknuepfungen/instanzen`.
- Produces: Antworten auf die Zeilen 6–13 der Tabelle „Abhängigkeiten vom Spike S14b“; die Getriebeprobe (Tasks 11/12).

- [ ] **Step 1: Vorbedingungen prüfen** (wie Task 2, SolidWorks frisch)

- [ ] **Step 2: Probe und Spike schreiben**

`spikes/s14b_kopplung.py` anlegen:

```python
"""S14b (Stufe 4b, Etappe 2): Zahnrad- und Zahnstangenverknüpfung an der Getriebeprobe (tests/live/getriebeprobe/).

6 CreateMate mit IRackPinionMateFeatureData (Vorauswahl Marke 64/128) und IGearMateFeatureData (EntitiesToMate):
  Rückgabe, IMate2.Type, Fehlercode, Rücklesen über IFeature.GetDefinition (DiameterVal/-Type, Zähler/Nenner, Reverse);
  Drehsinn bei Reverse = False (Ritzel um +z, wenn die Zahnstange nach +x fährt; Antriebswelle gegensinnig).
7 Zahnphase: Phasenfehler vor/nach SetTransformAndSolve2 mit kopplung.drehe (Seite a um ihre Achse).
8 GetConstrainedStatus mit Kopplungen: Grenze unterdrückt ohne Antrieb, mit Antrieb auf 0.
9 Kollision je Stellung (9 Stellungen 0 … HUB) in Phase: Paare und Volumen; Zeit und Private Bytes je Schritt; danach
  k2 gelöscht, Antriebswelle um eine halbe Teilung gedreht: wird Zahn auf Zahn als Kollision erkannt?
10 Grenze wirkt durch die Kette: Schritt auf HUB + 3,75.
11 Aufsummierte Drehung der Wellen um z aus Transform2 gegen die Übersetzung.
12 Bild entlang der Radachse (Ansicht vorne, Zoom auf die Auswahl).
13 Speichern, Schließen, Öffnen: Kopplungen vorhanden, Antrieb auf 30 dreht die Ritzelwelle um 30/20 rad.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s14b_kopplung
"""

import math
import shutil
import time
from pathlib import Path

import pythoncom
import win32com.client

from spikes._gemeinsam import lauf
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import basis, instanzen, verknuepfungen
from swki.baugruppe.kopplung import KOPPLUNGEN, drehe, in_baugruppe, phasenfehler, phasenwinkel, verzahnung_der_seite
from swki.baugruppe.modell import Quelle
from swki.baugruppe.referenzen import loese_im_teil
from swki.compiler import sw
from swki.compiler.bauen import baue_teil_dokument
from swki.compiler.fehler import BauFehler
from swki.compiler.protokoll import Protokoll
from swki.compiler.topologie import flaechen
from swki.konfig import PROJEKT, lade_rechner, lade_standard
from swki.pruefung.bilder import ANSICHTEN, SW_TIFF_SCREEN_OR_PRINT_CAPTURE
from swki.pruefung.messen import oeffne
from swki.spec.laden import lade_spec, lade_yaml
from swki.speicher import privat_mb
from swki.verbindung import in_mm, mm, r8_array, verbinde

AUFTRAG = "S14B"
TYP = {"zahnrad": 10, "zahnstange": 13}  # swMateType_e swMateGEAR / swMateRACKPINION
PROBE = PROJEKT / "tests" / "live" / "getriebeprobe"
REFERENZ = PROJEKT / "tests" / "referenz" / "zahnstangentrieb"


def _rebuild(asm) -> str:
    try:
        sw.rebuild(asm)
        return "ok"
    except BauFehler as e:
        return str(e)


def _drehwinkel_z(t0, t1) -> float:
    """Drehung um +z (Grad, −180 … 180) aus dem Bild der Teil-x-Achse."""
    d = math.degrees(math.atan2(t1[1], t1[0]) - math.atan2(t0[1], t0[0]))
    return (d + 180) % 360 - 180


class _Probe:
    """Baugruppe der Probe ohne lade_baugruppe (Schema und Plausibilität der Kopplungen kommen mit Task 9)."""

    def __init__(self, ordner: Path):
        self.spec = lade_yaml(ordner / "getriebeprobe.yaml")
        self.teile = {k["quelle"]["teil"]: lade_spec(ordner / k["quelle"]["teil"]) for k in self.spec["komponenten"]}
        self.quellen = {k["id"]: Quelle("teil", self.teile[k["quelle"]["teil"]], datei=k["quelle"]["teil"])
                        for k in self.spec["komponenten"]}


def _teile(app, r, standard, bg, ordner) -> dict:
    kontexte = {}
    for datei, spec in bg.teile.items():
        model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, ordner / datei, AUFTRAG,
                                                Protokoll(AUFTRAG, datei, 0, r.sw_jahr))
        if fehler is not None:
            raise fehler
        sw.speichere(model, ordner / f"{spec['name']}.sldprt")
        kontexte[datei] = ctx
    return kontexte


def _kopple(asm, v, a, b, wert_a, wert_b) -> tuple[object, dict]:
    """Kopplung direkt über CreateMate (der Handler kommt mit Task 11)."""
    e = {}
    vorher = len(sw_baugruppe.verknuepfungen(asm))
    sw.auswahl_leeren(asm)
    daten = asm.CreateMateData(TYP[v.typ])
    e["mate_data"] = daten is not None
    if v.typ == "zahnrad":
        daten.EntitiesToMate = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, [a[0], b[0]])
        daten.GearRatioNumerator = mm(wert_a)
        daten.GearRatioDenominator = mm(wert_b)
    else:
        daten_b = asm.SelectionManager.CreateSelectData
        daten_b.Mark = 64
        b[0].Select4(False, daten_b)
        daten_a = asm.SelectionManager.CreateSelectData
        daten_a.Mark = 128
        a[0].Select4(True, daten_a)
        daten.DiameterType = 0
        daten.DiameterVal = mm(wert_a)
    daten.Reverse = False
    mate = asm.CreateMate(daten)
    sw.auswahl_leeren(asm)
    alle = sw_baugruppe.verknuepfungen(asm)
    neu = alle[-1] if mate is not None and len(alle) > vorher else None
    e["angelegt"] = neu is not None
    if neu is not None:
        neu.Name = v.id
        e["rebuild"] = _rebuild(asm)
        e["fehlercode"] = sw_baugruppe.fehlercode(neu)
        e["typ"] = int(neu.GetSpecificFeature2.Type)
        try:
            d = neu.GetDefinition
            e["gelesen"] = ({"zaehler": in_mm(d.GearRatioNumerator), "nenner": in_mm(d.GearRatioDenominator),
                             "reverse": bool(d.Reverse)} if v.typ == "zahnrad"
                            else {"durchmesser": in_mm(d.DiameterVal), "art": d.DiameterType, "reverse": bool(d.Reverse)})
        except Exception as ex:  # Spike: festhalten
            e["gelesen"] = repr(ex)
    return neu, e


def _phase(app, asm, bg, komponenten, v) -> dict:
    def lagen():
        return [in_baugruppe(verzahnung_der_seite(bg.quellen, s), sw_baugruppe.transform(komponenten[s["komponente"]]))
                for s in (v.a, v.b)]

    a, b = lagen()
    e = {"fehler_vorher": round(phasenfehler(a, b), 6), "winkel": round(phasenwinkel(a, b), 6)}
    komp = komponenten[v.a["komponente"]]
    t = drehe(sw_baugruppe.transform(komp), a.punkt, a.achse, phasenwinkel(a, b))
    e["set_transform"] = bool(komp.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(t))))
    e["rebuild"] = _rebuild(asm)
    a, b = lagen()
    e["fehler_nachher"] = round(phasenfehler(a, b), 9)
    return e


def _status(komponenten) -> dict:
    return {k: sw_baugruppe.status(x) for k, x in komponenten.items()}


def _untersuche() -> dict:
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    ordner = r.arbeitsordner / AUFTRAG
    shutil.rmtree(ordner, ignore_errors=True)
    ordner.mkdir(parents=True)
    for quelle in [*PROBE.glob("*.yaml"), *(REFERENZ / n for n in ("zahnstange.yaml", "lagerbock.yaml", "ritzelwelle.yaml",
                                                                    "antriebswelle.yaml"))]:
        shutil.copy2(quelle, ordner / quelle.name)
    bg = _Probe(ordner)
    ergebnis = {"privat_mb_start": privat_mb(int(app.GetProcessID))}
    kontexte = _teile(app, r, standard, bg, ordner)
    asm = None
    try:
        asm = sw_baugruppe.neue_baugruppe(app, r.vorlage_baugruppe)
        komponenten = {}
        for i in instanzen(bg.spec, bg.quellen):
            model = kontexte[bg.quellen[i.komponente].datei].model
            komponenten[i.id] = sw_baugruppe.fuege_ein(app, asm, Path(model.GetPathName), sw.teilebox_mm(model))
        sw_baugruppe.fixiere(asm, komponenten["platte"])

        def ent(seite):
            ctx = kontexte[bg.quellen[basis(seite["komponente"])].datei]
            ref = loese_im_teil(ctx, {k: w for k, w in seite.items() if k != "komponente"})
            return sw_baugruppe.in_baugruppe(komponenten[seite["komponente"]], ref)

        def ent_kopplung(seite):
            ctx = kontexte[bg.quellen[basis(seite["komponente"])].datei]
            f = next(x for x in ctx.spec["features"] if x["id"] == seite["feature"])
            if f["art"] == "stirnrad":
                return ent({"komponente": seite["komponente"], "feature": seite["feature"], "instanz": 1, "achse": True})
            for kopf in flaechen(ctx.ergebnis(seite["feature"]).features[0]):  # gerade Kante einer Kopffläche entlang x
                if kopf.art == "ebene" and kopf.normale[1] > 1 - 1e-6:
                    for kante in kopf.objekt.GetEdges or ():
                        c = kante.GetCurve
                        if c.IsLine and abs(c.LineParams[3]) > 1 - 1e-6:
                            return sw_baugruppe.in_baugruppe(komponenten[seite["komponente"]],
                                                             type("Ref", (), {"objekt": kante, "ist_feature": False})())
            raise RuntimeError("keine Kante der Zahnstange")

        gesetzt: dict[str, int] = {}
        p = bg.spec.get("parameter", {})
        for v in verknuepfungen(bg.spec, bg.quellen):
            if v.typ in KOPPLUNGEN:
                ergebnis[f"7_phase_{v.id}"] = _phase(app, asm, bg, komponenten, v)
                a, b = (verzahnung_der_seite(bg.quellen, s).geo for s in (v.a, v.b))
                werte = (a.m * a.z, b.m * b.z) if v.typ == "zahnrad" else (a.m * a.z, 0.0)
                _, ergebnis[f"6_kopplung_{v.id}"] = _kopple(asm, v, ent_kopplung(v.a), ent_kopplung(v.b), *werte)
            else:
                sw_baugruppe.verknuepfe(asm, v, ent(v.a), ent(v.b), p, gesetzt)
        g1 = next(v for v in verknuepfungen(bg.spec, bg.quellen) if v.id == "g1")
        grenze = next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "g1")
        sw_baugruppe.unterdruecke(asm, grenze, True)
        ergebnis["8_status_ohne_antrieb"] = _status(komponenten)
        antrieb = sw_baugruppe.treibe(asm, g1, ent(g1.a), ent(g1.b), 0.0)
        ergebnis["8_status_mit_antrieb"] = _status(komponenten)
        sw_baugruppe.unterdruecke(asm, grenze, False)

        hub = p["HUB"]
        start = {k: sw_baugruppe.transform(komponenten[k]) for k in ("ritzelwelle", "antriebswelle")}
        vorige = dict(start)
        summe = {k: 0.0 for k in start}
        schritte = []
        pid = int(app.GetProcessID)
        for i in range(9):
            wert = hub * i / 8
            t = time.perf_counter()
            meldung = sw_baugruppe.stelle(asm, antrieb, "abstand", wert)
            stellen = time.perf_counter() - t
            t = time.perf_counter()
            paare = sw_baugruppe.interferenzen(asm)
            kollision = time.perf_counter() - t
            for k in summe:
                jetzt = sw_baugruppe.transform(komponenten[k])
                summe[k] += _drehwinkel_z(vorige[k], jetzt)
                vorige[k] = jetzt
            schritte.append({"wert": wert, "meldung": meldung, "paare": [[sorted(n), round(vol, 4)] for n, vol in paare],
                             "s_stellen": round(stellen, 3), "s_kollision": round(kollision, 3),
                             "drehung_z": {k: round(w, 4) for k, w in summe.items()}, "privat_mb": privat_mb(pid)})
        ergebnis["9_11_schritte"] = schritte
        ergebnis["11_soll"] = {"ritzelwelle": round(math.degrees(hub / 20), 4),
                               "antriebswelle": round(-math.degrees(hub / 20) * 25 / 50, 4)}
        ergebnis["10_grenze"] = {"meldung": sw_baugruppe.stelle(asm, antrieb, "abstand", hub + 3.75),
                                 "x_zahnstange_mm": round(in_mm(sw_baugruppe.transform(komponenten["zahnstange"])[9]), 4)}
        ergebnis["10_zurueck"] = sw_baugruppe.stelle(asm, antrieb, "abstand", 0.0)

        model = asm
        model._FlagAsMethod("ViewZoomToSelection")
        with sw.einstellung_int(app, SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0):
            model.ShowNamedView2("", ANSICHTEN["vorne"])
            sw.auswahl_leeren(model)
            for k in ("antriebswelle", "ritzelwelle"):
                komponenten[k].Select4(True, model.SelectionManager.CreateSelectData, False)
            model.ViewZoomToSelection()
            sw.auswahl_leeren(model)
            (ordner / "bilder").mkdir(exist_ok=True)
            sw.speichere(model, ordner / "bilder" / "k2-eingriff.png", kopie=True)
        ergebnis["12_bild_bytes"] = (ordner / "bilder" / "k2-eingriff.png").stat().st_size

        sw_baugruppe.loesche(asm, antrieb)
        sw.speichere(asm, ordner / "Getriebeprobe.sldasm")

        k2 = next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "k2")
        sw_baugruppe.loesche(asm, k2)
        komp = komponenten["antriebswelle"]
        a = in_baugruppe(verzahnung_der_seite(bg.quellen, {"komponente": "antriebswelle", "feature": "z1"}),
                         sw_baugruppe.transform(komp))
        t = drehe(sw_baugruppe.transform(komp), a.punkt, a.achse, 180 / 50)
        komp.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(t)))
        _rebuild(asm)
        ergebnis["9_halbe_teilung_paare"] = [[sorted(n), round(vol, 4)] for n, vol in sw_baugruppe.interferenzen(asm)]
    finally:
        if asm is not None:
            sw.schliesse(app, asm)
    asm = oeffne(app, ordner / "Getriebeprobe.sldasm")
    try:
        sw_baugruppe.aufloesen(asm)
        namen = [f.Name for f in sw_baugruppe.verknuepfungen(asm)]
        ergebnis["13_verknuepfungen"] = namen
        komps = {k.Name2.split("-")[0]: k for k in sw_baugruppe.komponenten(asm)}
        ergebnis["13_komponenten"] = sorted(komps)
        ritzel = next(k for n, k in komps.items() if "Ritzelwelle" in n)
        t0 = sw_baugruppe.transform(ritzel)
        grenze = next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "g1")
        stange = next(k for n, k in komps.items() if "Zahnstange" in n)
        dx = sw_baugruppe.transform(stange)[9]
        # Lage der Zahnstange über SetTransformAndSolve2 um 30 mm in +x verschieben (ohne Antrieb, nur Neuöffnen prüfen)
        t = sw_baugruppe.transform(stange)
        t[9] = dx + mm(30)
        stange.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(t)))
        ergebnis["13_rebuild"] = _rebuild(asm)
        ergebnis["13_ritzel_drehung_z"] = round(_drehwinkel_z(t0, sw_baugruppe.transform(ritzel)), 4)
        ergebnis["13_soll"] = round(math.degrees(30 / 20), 4)
        ergebnis["13_grenze_fehlercode"] = sw_baugruppe.fehlercode(grenze)
    finally:
        sw.schliesse(app, asm)
    for ctx in reversed(list(kontexte.values())):
        sw.schliesse(app, ctx.model)
    ergebnis["privat_mb_ende"] = privat_mb(int(app.GetProcessID))
    return ergebnis


if __name__ == "__main__":
    lauf("s14b_kopplung", _untersuche)
```

`tests/live/getriebeprobe/platte.yaml` anlegen:

```yaml
# Getriebeprobe (Spec 4b §10): Platte, fixiert. Ursprung Mitte Unterseite, Oberseite y = H. Die Zahnstange gleitet auf
# der Platte, der Lagerbock steht auf ihr.
art: teil
name: Probeplatte
material: "1.0038"
eigenschaften: {Benennung: Platte Getriebeprobe}
parameter: {L: 200, B: 60, H: 20}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen: {soll: auto}
```

`tests/live/getriebeprobe/getriebeprobe.yaml` anlegen:

```yaml
# Getriebeprobe (Spec 4b §10, Minimalprobe beider Kopplungstypen): Platte (fixiert); die Zahnstange der Referenz gleitet
# auf ihr (Abstandsgrenze 0 … HUB); ein Lagerbock der Referenz steht in der Mitte; darin Ritzelwelle (Ritzel über der
# Zahnstange) und Antriebswelle wie im Zahnstangentrieb. Teile außer der Platte aus tests/referenz/zahnstangentrieb/.
art: baugruppe
name: Getriebeprobe
eigenschaften: {Benennung: Getriebeprobe}
parameter: {HUB: 60, ZL: 40}
komponenten:
  - {id: platte, quelle: {teil: platte.yaml}, fixiert: true}
  - {id: zahnstange, quelle: {teil: zahnstange.yaml}}
  - {id: lagerbock, quelle: {teil: lagerbock.yaml}}
  - {id: ritzelwelle, quelle: {teil: ritzelwelle.yaml}}
  - {id: antriebswelle, quelle: {teil: antriebswelle.yaml}}
verknuepfungen:
  - {id: v1, typ: deckungsgleich, a: {komponente: zahnstange, feature: f1, flaeche: "-y"},
     b: {komponente: platte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v2, typ: deckungsgleich, a: {komponente: zahnstange, feature: f1, flaeche: "-z"},
     b: {komponente: platte, feature: f1, flaeche: "-z"}, ausrichtung: gleich}
  - {id: g1, typ: grenze_abstand, a: {komponente: zahnstange, feature: f1, flaeche: "-x"},
     b: {komponente: platte, feature: f1, flaeche: "-x"}, ausrichtung: gleich, min: 0, max: "=HUB"}
  - {id: v3, typ: deckungsgleich, a: {komponente: lagerbock, feature: f1, flaeche: "-y"},
     b: {komponente: platte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v4, typ: deckungsgleich, a: {komponente: lagerbock, ebene: rechts}, b: {komponente: platte, ebene: rechts},
     ausrichtung: gleich}
  - {id: v5, typ: abstand, a: {komponente: lagerbock, feature: f1, flaeche: "-z"},
     b: {komponente: platte, feature: f1, flaeche: "-z"}, ausrichtung: gleich, wert: "=ZL"}
  - {id: s1, typ: scharnier, a: {komponente: ritzelwelle, referenz: ACHSE},
     b: {komponente: lagerbock, feature: f2, instanz: 1, achse: true},
     anlage_a: {komponente: ritzelwelle, feature: z2, flaeche: "+z"}, anlage_b: {komponente: lagerbock, feature: f1, flaeche: "-z"}}
  - {id: s2, typ: scharnier, a: {komponente: antriebswelle, referenz: ACHSE},
     b: {komponente: lagerbock, feature: f2, instanz: 2, achse: true},
     anlage_a: {komponente: antriebswelle, feature: z1, flaeche: "+z"}, anlage_b: {komponente: lagerbock, feature: f1, flaeche: "-z"}}
  - {id: k1, typ: zahnstange, a: {komponente: ritzelwelle, feature: z1}, b: {komponente: zahnstange, feature: z1}}
  - {id: k2, typ: zahnrad, a: {komponente: antriebswelle, feature: z1}, b: {komponente: ritzelwelle, feature: z2}}
freiheitsgrade: {zahnstange: 1, ritzelwelle: gekoppelt, antriebswelle: gekoppelt}
bewegungen:
  - name: Hub
    grenze: g1
    erwartet:
      endlagen:
        - {komponente: zahnstange, verschiebung: ["=HUB", 0, 0]}
        - {komponente: ritzelwelle, drehung: {achse: [0, 0, 1], winkel: "=HUB*360/(pi*40)"}}
        - {komponente: antriebswelle, drehung: {achse: [0, 0, -1], winkel: "=HUB*360/(pi*40)*25/50"}}
pruefung:
  huellquader: [200, 185, 120]
  masse_pruefen:
    - {was: Achsabstand der Wellen, von: {komponente: ritzelwelle, referenz: ACHSE},
       zu: {komponente: antriebswelle, referenz: ACHSE}, soll: 75}
```


- [ ] **Step 3: Spike laufen lassen**

Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m spikes.s14b_kopplung`
Expected: `"ok": true` und `docs/stufe0/ergebnisse/s14b_kopplung.json`. Abbruch: wie Task 2 Step 3.

- [ ] **Step 4: Auswertung in den Bericht**

Je Zeile 6–13: Zeile 6 `6_kopplung_k1/k2` (`angelegt`, `typ`, `fehlercode`, `gelesen`) und der Drehsinn aus
`9_11_schritte[*].drehung_z` (Ritzelwelle > 0, Antriebswelle < 0?); Zeile 7 `7_phase_*` (`fehler_vorher`, `set_transform`,
`fehler_nachher`); Zeile 8 `8_status_*`; Zeile 9 `9_11_schritte[*].paare`, `s_stellen`, `s_kollision`, `privat_mb`,
`9_halbe_teilung_paare`; Zeile 10 `10_grenze`; Zeile 11 letzte `drehung_z` gegen `11_soll`; Zeile 12 `12_bild_bytes`;
Zeile 13 `13_*`. Keine Entscheidung treffen.

- [ ] **Step 5: Commit**

```powershell
git add spikes/s14b_kopplung.py tests/live/getriebeprobe docs/stufe0/ergebnisse/s14b_kopplung.json
git commit -m "spike: S14b Zahnrad- und Zahnstangenverknüpfung an der Getriebeprobe" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Status DONE_WITH_CONCERNS, wenn eine Zeile abweicht.

---

### Task 9: Format und Plausibilität der Kopplungen (ohne SolidWorks)

**Files:**
- Modify: `schema/baugruppe.schema.json`, `swki/baugruppe/plausibel.py`, `swki/baugruppe/bewertung.py`
- Test: `tests/baugruppe/beispiel_kopplung.py` (neu), `tests/baugruppe/test_kopplung_plausibel.py` (neu)

**Interfaces:**
- Consumes: `swki.baugruppe.kopplung` (`GEKOPPELT`, `KOPPLUNGEN`, `antriebsmenge`, `endlagen_wege`, `gekoppelte`,
  `soll_drehungen`, `verzahnung_der_seite`), `swki.konfig.lade_standard`, `swki.spec.ausdruck.PI`.
- Produces: Schema (Typen `zahnrad`/`zahnstange`, Referenzform `{komponente, feature}`, `freiheitsgrade: gekoppelt`);
  Befunde `KOPPLUNG_ART`, `MODUL_UNGLEICH`, `KOPPLUNG_REIHENFOLGE`, `GEKOPPELT_OHNE_ANTRIEB`, `ENDLAGE_FEHLT`,
  `UEBERSETZUNG_WIDERSPRUCH`, `SCHRITTE_ZU_GROB`, `GRENZE_REFERENZ`, „pi ist die Kreiszahl …“, Radachse
  `{feature, instanz: 1, achse: true}` einer Verzahnung als Referenz; `_erlaubt_unterbestimmt` kennt `gekoppelt`.
  `tests/baugruppe/beispiel_kopplung.py`: `TEILE`, `SPEC`, `quellen(teile=None)`, `spec()`, `v(spec, id)`.

- [ ] **Step 1: Tests schreiben**

`tests/baugruppe/beispiel_kopplung.py` anlegen:

```python
"""Zahnstangentrieb als Beispiel für die Kopplungen (Spec 4b §5.1) – nur für Tests ohne SolidWorks (Plausibilität,
Bewegungen, Bewertung). Die echte Referenz liegt in tests/referenz/zahnstangentrieb/."""

import copy

from swki.baugruppe.modell import Quelle


def _block(name: str, *weitere) -> dict:
    return {"art": "teil", "name": name, "parameter": {"L": 100, "B": 60, "H": 20},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "oben",
                                     "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
                          "ende": {"typ": "blind", "tiefe": "=H"}}, *weitere]}


def _verzahnung(fid: str, art: str, zaehne: int, abstand: float = 0) -> dict:
    return {"id": fid, "typ": "verzahnung", "art": art, "ebene": {"versatz": {"ebene": "vorne", "abstand": abstand}},
            "mitte": [0, 0], "modul": "=M", "zaehne": zaehne, "breite": 10, "zahndickenabmass": -0.05}


def _welle(name: str, *verzahnungen) -> dict:
    return {"art": "teil", "name": name, "parameter": {"M": 2},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 12}}]},
                          "ende": {"typ": "blind", "tiefe": 80}},
                         *verzahnungen, {"id": "ACHSE", "typ": "referenz", "achse": "z"}]}


TEILE = {
    "grundplatte": _block("Grundplatte"),
    "schlitten": _block("Schlitten"),
    "zahnstange": {**_block("Zahnstange"), "parameter": {"L": 100, "B": 60, "H": 20, "M": 2},
                   "features": [*_block("Zahnstange")["features"], _verzahnung("z1", "zahnstange", 40)]},
    "lagerbock": _block("Lagerbock", {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
                                      "positionen": [[-30, 0], [30, 0]], "durchmesser": 12.5, "durch": True}),
    "ritzelwelle": _welle("Ritzelwelle", _verzahnung("z1", "stirnrad", 20, 10), _verzahnung("z2", "stirnrad", 25, 40)),
    "antriebswelle": _welle("Antriebswelle", _verzahnung("z1", "stirnrad", 50, 40)),
}


def _v(vid, typ, a, b, **weitere) -> dict:
    return {"id": vid, "typ": typ, "a": a, "b": b, **weitere}


def _f(k: str, flaeche: str, feature: str = "f1") -> dict:
    return {"komponente": k, "feature": feature, "flaeche": flaeche}


SPEC = {
    "art": "baugruppe", "name": "Trieb", "parameter": {"HUB": 220},
    "komponenten": [
        {"id": "grundplatte", "quelle": {"teil": "grundplatte.yaml"}, "fixiert": True},
        {"id": "schlitten", "quelle": {"teil": "schlitten.yaml"}, "gruppe": "schieber"},
        {"id": "zahnstange", "quelle": {"teil": "zahnstange.yaml"}, "gruppe": "schieber"},
        {"id": "lagerbock", "quelle": {"teil": "lagerbock.yaml"}},
        {"id": "ritzelwelle", "quelle": {"teil": "ritzelwelle.yaml"}},
        {"id": "antriebswelle", "quelle": {"teil": "antriebswelle.yaml"}},
    ],
    "verknuepfungen": [
        _v("v1", "deckungsgleich", _f("schlitten", "-y"), _f("grundplatte", "+y"), ausrichtung="entgegengesetzt"),
        _v("v2", "deckungsgleich", _f("schlitten", "-z"), _f("grundplatte", "-z"), ausrichtung="gleich"),
        _v("g1", "grenze_abstand", _f("schlitten", "-x"), _f("grundplatte", "-x"), ausrichtung="gleich", min=0,
           max="=HUB"),
        _v("v3", "deckungsgleich", _f("zahnstange", "-y"), _f("schlitten", "+y"), ausrichtung="entgegengesetzt"),
        _v("v4", "deckungsgleich", _f("zahnstange", "-x"), _f("schlitten", "-x"), ausrichtung="gleich"),
        _v("v5", "deckungsgleich", _f("zahnstange", "-z"), _f("schlitten", "-z"), ausrichtung="gleich"),
        _v("v6", "deckungsgleich", _f("lagerbock", "-y"), _f("grundplatte", "+y"), ausrichtung="entgegengesetzt"),
        _v("v7", "deckungsgleich", _f("lagerbock", "-x"), _f("grundplatte", "-x"), ausrichtung="gleich"),
        _v("v8", "deckungsgleich", _f("lagerbock", "+z"), _f("grundplatte", "+z"), ausrichtung="gleich"),
        _v("s1", "scharnier", {"komponente": "ritzelwelle", "referenz": "ACHSE"},
           {"komponente": "lagerbock", "feature": "f2", "instanz": 1, "achse": True},
           anlage_a=_f("ritzelwelle", "-z"), anlage_b=_f("lagerbock", "+y")),
        _v("s2", "scharnier", {"komponente": "antriebswelle", "referenz": "ACHSE"},
           {"komponente": "lagerbock", "feature": "f2", "instanz": 2, "achse": True},
           anlage_a=_f("antriebswelle", "-z"), anlage_b=_f("lagerbock", "+y")),
        _v("k1", "zahnstange", {"komponente": "ritzelwelle", "feature": "z1"}, {"komponente": "zahnstange", "feature": "z1"}),
        _v("k2", "zahnrad", {"komponente": "antriebswelle", "feature": "z1"}, {"komponente": "ritzelwelle", "feature": "z2"}),
    ],
    "freiheitsgrade": {"schieber": 1, "ritzelwelle": "gekoppelt", "antriebswelle": "gekoppelt"},
    "bewegungen": [{"name": "Schlittenhub", "grenze": "g1", "erwartet": {"endlagen": [
        {"komponente": "schlitten", "verschiebung": ["=HUB", 0, 0]},
        {"komponente": "zahnstange", "verschiebung": ["=HUB", 0, 0]},
        {"komponente": "ritzelwelle", "drehung": {"achse": [0, 0, -1], "winkel": "=HUB*360/(pi*40)"}},
        {"komponente": "antriebswelle", "drehung": {"achse": [0, 0, 1], "winkel": "=HUB*360/(pi*40)*25/50"}},
    ]}}],
}


def quellen(teile: dict | None = None) -> dict[str, Quelle]:
    teile = teile or TEILE
    return {k["id"]: Quelle("teil", teile[k["id"]], datei=k["quelle"]["teil"]) for k in SPEC["komponenten"]}


def spec() -> dict:
    return copy.deepcopy(SPEC)


def v(s: dict, vid: str) -> dict:
    return next(x for x in s["verknuepfungen"] if x["id"] == vid)
```

`tests/baugruppe/test_kopplung_plausibel.py` anlegen:

```python
"""Format und Plausibilität der Kopplungen (Spec 4b §5.1, §5.2), Bestimmtheit gekoppelter Komponenten."""

import copy

import pytest

from swki.baugruppe.bewertung import _erlaubt_unterbestimmt
from swki.baugruppe.plausibel import plausibel_befunde
from swki.spec.laden import schema_befunde

from .beispiel_kopplung import TEILE, quellen, spec, v


def _meldungen(s: dict, teile: dict | None = None) -> list[str]:
    return [b["meldung"] for b in plausibel_befunde(s, quellen(teile))]


def _hat(meldungen: list[str], code: str) -> bool:
    return any(m.startswith(code) for m in meldungen)


def test_beispiel_ist_gueltig():
    assert schema_befunde(spec(), "baugruppe") == []
    assert _meldungen(spec()) == []


def test_schema_kennt_kopplung_und_gekoppelt():
    s = spec()
    s["freiheitsgrade"]["ritzelwelle"] = "frei"
    assert [b["pfad"] for b in schema_befunde(s, "baugruppe")] == ["freiheitsgrade.ritzelwelle"]


def test_kopplung_art():
    s = spec()
    v(s, "k1")["b"] = {"komponente": "ritzelwelle", "feature": "z2"}
    assert _hat(_meldungen(s), "KOPPLUNG_ART")
    s = spec()
    v(s, "k2")["a"] = {"komponente": "antriebswelle", "feature": "f1"}
    assert _hat(_meldungen(s), "KOPPLUNG_ART")


def test_modul_ungleich():
    teile = copy.deepcopy(TEILE)
    teile["antriebswelle"]["parameter"]["M"] = 2.5
    assert _hat(_meldungen(spec(), teile), "MODUL_UNGLEICH")


def test_reihenfolge_seite_b_steht_noch_nicht_fest():
    s = spec()
    k1, k2 = v(s, "k1"), v(s, "k2")
    s["verknuepfungen"] = [x for x in s["verknuepfungen"] if x["id"] not in ("k1", "k2")] + [k2, k1]
    meldungen = _meldungen(s)
    assert any(m.startswith("KOPPLUNG_REIHENFOLGE: ritzelwelle steht beim Anlegen noch nicht fest") for m in meldungen)


def test_reihenfolge_kopplung_vor_anderer_verknuepfung():
    s = spec()
    s2 = v(s, "s2")
    s["verknuepfungen"] = [x for x in s["verknuepfungen"] if x["id"] != "s2"] + [s2]
    assert any("danach noch: s2" in m for m in _meldungen(s))


def test_reihenfolge_seite_a_nicht_gekoppelt():
    s = spec()
    s["freiheitsgrade"]["antriebswelle"] = "unterbestimmt"
    assert any(m.startswith("KOPPLUNG_REIHENFOLGE: antriebswelle wird beim Bau in Phase gedreht") for m in _meldungen(s))


def test_gekoppelt_ohne_antrieb():
    s = spec()
    s["verknuepfungen"] = [x for x in s["verknuepfungen"] if x["id"] != "k2"]
    s["bewegungen"][0]["erwartet"]["endlagen"].pop()
    assert _hat(_meldungen(s), "GEKOPPELT_OHNE_ANTRIEB")


def test_endlage_fehlt():
    s = spec()
    s["bewegungen"][0]["erwartet"]["endlagen"].pop()
    assert any(m == "ENDLAGE_FEHLT: antriebswelle ist gekoppelt und braucht in Schlittenhub eine Endlage drehung"
               for m in _meldungen(s))


def test_uebersetzung_widerspruch():
    s = spec()
    s["bewegungen"][0]["erwartet"]["endlagen"][3]["drehung"]["winkel"] = "=HUB*360/(pi*40)*25/49"
    meldungen = _meldungen(s)
    assert _hat(meldungen, "UEBERSETZUNG_WIDERSPRUCH: antriebswelle dreht laut Übersetzung 315.1268°")


def test_schritte_zu_grob():
    s = spec()
    s["bewegungen"][0]["schritte"] = 3
    assert any(m.startswith("SCHRITTE_ZU_GROB") and m.endswith("mindestens 4 Schritte") for m in _meldungen(s))


def test_nur_feature_ausserhalb_einer_kopplung():
    s = spec()
    v(s, "v1")["a"] = {"komponente": "schlitten", "feature": "f1"}
    assert any(m.startswith("{komponente, feature} nur bei zahnrad/zahnstange") for m in _meldungen(s))


def test_radachse_als_referenz():
    s = spec()
    v(s, "s1")["a"] = {"komponente": "ritzelwelle", "feature": "z1", "instanz": 1, "achse": True}
    assert _meldungen(s) == []
    v(s, "s1")["a"] = {"komponente": "ritzelwelle", "feature": "z1", "instanz": 2, "achse": True}
    assert any("nur die Radachse eines Stirnrads" in m for m in _meldungen(s))


@pytest.mark.parametrize("seite", [{"komponente": "lagerbock", "feature": "f2", "instanz": 1, "achse": True},
                                   {"komponente": "schlitten", "nahe": [0, 0, 0]}])
def test_grenze_referenz(seite):
    s = spec()
    v(s, "g1")["a"] = seite
    assert _hat(_meldungen(s), "GRENZE_REFERENZ")


def test_pi_ist_kein_parametername():
    s = spec()
    s["parameter"]["pi"] = 3
    assert "pi ist die Kreiszahl und kein Parametername" in _meldungen(s)


def test_gekoppelt_darf_unterbestimmt_sein():
    assert _erlaubt_unterbestimmt(spec(), "ritzelwelle") is True
    assert _erlaubt_unterbestimmt(spec(), "lagerbock") is False
```


- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_kopplung_plausibel.py`
Expected: FAIL – `17 failed` (Schema kennt `zahnrad`/`gekoppelt` nicht).

- [ ] **Step 3: Umsetzen**

In `schema/baugruppe.schema.json` ersetzen:

```json
                       "additionalProperties": {"oneOf": [{"const": "unterbestimmt"},
                                                           {"type": "integer", "minimum": 1}]}},
```

durch:

```json
                       "additionalProperties": {"oneOf": [{"enum": ["unterbestimmt", "gekoppelt"]},
                                                           {"type": "integer", "minimum": 1}]}},
```

In `schema/baugruppe.schema.json` ersetzen:

```json
      {"type": "object", "required": ["komponente", "ebene"], "additionalProperties": false,
```

durch:

```json
      {"type": "object", "required": ["komponente", "feature"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/id"}, "feature": {"$ref": "#/$defs/id"}}},
      {"type": "object", "required": ["komponente", "ebene"], "additionalProperties": false,
```

In `schema/baugruppe.schema.json` ersetzen:

```json
                         "grenze_abstand", "grenze_winkel", "scharnier"]},
```

durch:

```json
                         "grenze_abstand", "grenze_winkel", "scharnier", "zahnrad", "zahnstange"]},
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
"""Plausibilität einer Baugruppen-Spezifikation (Spec 3b §5), ohne SolidWorks."""

from swki.baugruppe.aufloesen import GRENZEN, anzahl_positionen, basis, je_position
from swki.baugruppe.modell import Quelle
from swki.baugruppe.passung import passung_befunde
from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck
```

durch:

```python
"""Plausibilität einer Baugruppen-Spezifikation (Spec 3b §5, 4a §5, 4b §5.2), ohne SolidWorks."""

import math

from swki.baugruppe.aufloesen import GRENZEN, anzahl_positionen, basis, je_position
from swki.baugruppe.kopplung import (GEKOPPELT, KOPPLUNGEN, antriebsmenge, endlagen_wege, gekoppelte, soll_drehungen,
                                     verzahnung_der_seite)
from swki.baugruppe.modell import Quelle
from swki.baugruppe.passung import passung_befunde
from swki.konfig import lade_standard
from swki.spec.ausdruck import PI, AusdruckFehler, auswerten, ist_ausdruck
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
        elif "instanz" in seite:
            if f["typ"] not in BOHRUNGEN:
                befunde.append(_b(f"{pfad}.instanz", f"instanz nur bei normbohrung/bohrung ({seite['feature']} ist {f['typ']})"))
```

durch:

```python
        elif "instanz" in seite and f["typ"] == "verzahnung":
            if f["art"] != "stirnrad" or seite["instanz"] != 1 or not seite.get("achse"):
                befunde.append(_b(f"{pfad}.instanz", f"{seite['feature']}: nur die Radachse eines Stirnrads "
                                                     "({feature, instanz: 1, achse: true})"))
        elif "instanz" in seite:
            if f["typ"] not in BOHRUNGEN:
                befunde.append(_b(f"{pfad}.instanz", f"instanz nur bei normbohrung/bohrung ({seite['feature']} ist {f['typ']})"))
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
def _grenze_befunde(v: dict, pfad: str, p: dict) -> list[dict]:
    """min/max einer Grenzverknüpfung: Pflicht, 0 oder Parameter-Ausdruck (GRENZE_FESTE_ZAHL), min < max, Bereich."""
    if v["typ"] not in GRENZEN:
        return [_b(f"{pfad}.{s}", "min/max gelten nur bei grenze_abstand/grenze_winkel") for s in ("min", "max") if s in v]
    befunde, werte = [], {}
```

durch:

```python
def _ist_eben(seite: dict, quellen: dict[str, Quelle]) -> bool:
    """Referenz einer Grenze ist eine ebene Fläche bzw. Ebene (Spec 4a §4.1, 4b §6.3): Fläche, Standardebene oder
    referenz-Ebene; nicht Achse, nicht Punktanker."""
    if "flaeche" in seite or "ebene" in seite:
        return True
    if "referenz" in seite:
        q = quellen[basis(seite["komponente"])]
        if q.art == "normteil":
            return "ACHSE" not in seite["referenz"]
        f = next((x for x in q.spec["features"] if x["id"] == seite["referenz"]), None)
        return f is not None and "ebene" in f
    return False


def _grenze_befunde(v: dict, pfad: str, p: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """min/max einer Grenzverknüpfung: Pflicht, 0 oder Parameter-Ausdruck (GRENZE_FESTE_ZAHL), min < max, Bereich;
    a und b ebene Flächen (GRENZE_REFERENZ)."""
    if v["typ"] not in GRENZEN:
        return [_b(f"{pfad}.{s}", "min/max gelten nur bei grenze_abstand/grenze_winkel") for s in ("min", "max") if s in v]
    befunde, werte = [], {}
    for s in ("a", "b"):
        if basis(v[s]["komponente"]) in quellen and not _ist_eben(v[s], quellen):
            befunde.append(_b(f"{pfad}.{s}", f"GRENZE_REFERENZ: {s} einer {v['typ']} ist eine ebene Fläche (flaeche, ebene "
                                             "oder referenz-Ebene), keine Achse und kein Punktanker"))
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
        befunde += _grenze_befunde(v, pfad, p) + _scharnier_befunde(v, pfad, spec, quellen)
        if v["typ"] in (*GRENZEN, "scharnier") and any(je_position(spec, v[s]["komponente"]) for s in ("a", "b")):
```

durch:

```python
        befunde += _grenze_befunde(v, pfad, p, quellen) + _scharnier_befunde(v, pfad, spec, quellen)
        if v["typ"] in (*GRENZEN, "scharnier", *KOPPLUNGEN) and any(je_position(spec, v[s]["komponente"]) for s in ("a", "b")):
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
def plausibel_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Alle Plausibilitätsbefunde; Komponentenfehler zuerst (sonst lassen sich Instanzen nicht zählen)."""
    befunde = _komponenten_befunde(spec, quellen)
    if befunde:
        return befunde
    befunde = (_verknuepfung_befunde(spec, quellen) + _freiheitsgrade_befunde(spec) + _pruefung_befunde(spec, quellen)
               + _bewegungen_befunde(spec, quellen))
    return befunde + passung_befunde(spec, quellen)
```

durch:

```python
def _nur_feature(seite: dict) -> bool:
    """Referenzform {komponente, feature} (Verzahnung einer Kopplung)."""
    return set(seite) == {"komponente", "feature"}


def _verzahnung(seite: dict, quellen: dict[str, Quelle]) -> dict | None:
    q = quellen.get(basis(seite["komponente"]))
    if q is None or q.art != "teil" or not _nur_feature(seite):
        return None
    f = next((x for x in q.spec["features"] if x["id"] == seite["feature"]), None)
    return f if f is not None and f["typ"] == "verzahnung" else None


def _kopplung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Spec 4b §5.2: Art der Seiten (KOPPLUNG_ART), gleiche Module (MODUL_UNGLEICH), Reihenfolge und feste Seite b
    (KOPPLUNG_REIHENFOLGE); {komponente, feature} nur bei Kopplungen."""
    befunde = []
    vs = spec.get("verknuepfungen", [])
    fg = spec.get("freiheitsgrade", {})
    seite_a: dict[str, int] = {}  # Komponente → Index der Kopplung, in der sie Seite a ist
    for i, v in enumerate(vs):
        pfad = f"verknuepfungen[{i}]"
        if v["typ"] not in KOPPLUNGEN:
            befunde += [_b(f"{pfad}.{s}", "{komponente, feature} nur bei zahnrad/zahnstange; sonst flaeche, achse oder "
                                          "referenz angeben") for s in ("a", "b") if _nur_feature(v[s])]
            continue
        arten = {"a": "stirnrad", "b": "stirnrad" if v["typ"] == "zahnrad" else "zahnstange"}
        moduln = {}
        for s, art in arten.items():
            f = _verzahnung(v[s], quellen)
            if f is None or f["art"] != art:
                befunde.append(_b(f"{pfad}.{s}", f"KOPPLUNG_ART: {v['typ']}: {s} ist eine Verzahnung art: {art} "
                                                 "({komponente, feature})"))
            else:
                moduln[s] = verzahnung_der_seite(quellen, v[s]).geo.m
        if len(moduln) == 2 and abs(moduln["a"] - moduln["b"]) > 1e-9:
            befunde.append(_b(pfad, f"MODUL_UNGLEICH: Modul {moduln['a']:g} (a) und {moduln['b']:g} (b)"))
        ka, kb = v["a"]["komponente"], v["b"]["komponente"]
        if fg.get(ka) != GEKOPPELT:
            befunde.append(_b(f"{pfad}.a", f"KOPPLUNG_REIHENFOLGE: {ka} wird beim Bau in Phase gedreht und braucht "
                                           "freiheitsgrade: gekoppelt"))
        if ka in seite_a:
            befunde.append(_b(f"{pfad}.a", f"KOPPLUNG_REIHENFOLGE: {ka} ist schon Seite a von {vs[seite_a[ka]]['id']}"))
        seite_a.setdefault(ka, i)
        if fg.get(kb) == GEKOPPELT and seite_a.get(kb, i) >= i:
            befunde.append(_b(f"{pfad}.b", f"KOPPLUNG_REIHENFOLGE: {kb} steht beim Anlegen noch nicht fest (gekoppelt, "
                                           "aber nicht Seite a einer früheren Kopplung)"))
        spaeter = [w["id"] for w in vs[i + 1:] if w["typ"] not in KOPPLUNGEN
                   and {ka, kb} & {w[s]["komponente"] for s in ("a", "b", "anlage_a", "anlage_b") if s in w}]
        if spaeter:
            befunde.append(_b(pfad, f"KOPPLUNG_REIHENFOLGE: Kopplungen nach den übrigen Verknüpfungen von {ka} und {kb} "
                                    f"(danach noch: {', '.join(spaeter)})"))
    return befunde


def _kopplung_bewegung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Spec 4b §5.2: GEKOPPELT_OHNE_ANTRIEB, ENDLAGE_FEHLT, UEBERSETZUNG_WIDERSPRUCH, SCHRITTE_ZU_GROB."""
    befunde = []
    p = spec.get("parameter", {})
    vorgabe = lade_standard()["bewegung_schritte"]
    getrieben: set[str] = set()
    grenzen = {v["id"]: v for v in spec.get("verknuepfungen", []) if v["typ"] in GRENZEN}
    for i, b in enumerate(spec.get("bewegungen", [])):
        pfad = f"bewegungen[{i}]"
        kid = bewegte_komponente(spec, b)
        if kid is None:
            continue
        menge = antriebsmenge(spec, kid)
        treibt = gekoppelte(spec, menge)
        getrieben |= set(treibt)
        endlagen = b.get("erwartet", {}).get("endlagen", [])
        drehungen = {e["komponente"] for e in endlagen if "drehung" in e}
        for k in treibt:
            if k not in drehungen:
                befunde.append(_b(f"{pfad}.erwartet.endlagen", f"ENDLAGE_FEHLT: {k} ist gekoppelt und braucht in "
                                                               f"{b['name']} eine Endlage drehung"))
        g = grenzen[b["grenze"]]
        if "min" not in g or "max" not in g:
            continue  # bereits bei den Grenzen gemeldet
        try:
            bereich = auswerten(g["max"], p) - auswerten(g["min"], p)
            soll = soll_drehungen(spec, quellen, menge, "abstand" if g["typ"] == "grenze_abstand" else "winkel", bereich,
                                  endlagen_wege(b, p))
            schritte = b.get("schritte", vorgabe)
            for j, e in enumerate(endlagen):
                if "drehung" not in e:
                    continue
                winkel = abs(auswerten(e["drehung"]["winkel"], p))
                epfad = f"{pfad}.erwartet.endlagen[{j}]"
                if e["komponente"] in soll and abs(winkel - soll[e["komponente"]]) > 0.01:
                    befunde.append(_b(epfad, f"UEBERSETZUNG_WIDERSPRUCH: {e['komponente']} dreht laut Übersetzung "
                                             f"{soll[e['komponente']]:.4f}°, erwartet sind {winkel:g}°"))
                if winkel / schritte >= 180:
                    befunde.append(_b(epfad, f"SCHRITTE_ZU_GROB: {winkel:g}° in {schritte} Schritten – mindestens "
                                             f"{math.floor(winkel / 180) + 1} Schritte"))
        except AusdruckFehler:
            continue  # bereits bei den Bewegungen gemeldet
    for n, w in spec.get("freiheitsgrade", {}).items():
        if w == GEKOPPELT and n not in getrieben:
            befunde.append(_b(f"freiheitsgrade.{n}", f"GEKOPPELT_OHNE_ANTRIEB: {n} erreicht über Kopplungen keine "
                                                     "Komponente oder Gruppe mit freiheitsgrade: 1 und Bewegung"))
    return befunde


def plausibel_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Alle Plausibilitätsbefunde; Komponentenfehler zuerst (sonst lassen sich Instanzen nicht zählen)."""
    befunde = _komponenten_befunde(spec, quellen)
    if PI in spec.get("parameter", {}):
        befunde.append(_b(f"parameter.{PI}", f"{PI} ist die Kreiszahl und kein Parametername"))
    if befunde:
        return befunde
    befunde = (_verknuepfung_befunde(spec, quellen) + _freiheitsgrade_befunde(spec) + _pruefung_befunde(spec, quellen)
               + _bewegungen_befunde(spec, quellen))
    kopplung = _kopplung_befunde(spec, quellen)
    befunde += kopplung
    if not kopplung:
        befunde += _kopplung_bewegung_befunde(spec, quellen)
    return befunde + passung_befunde(spec, quellen)
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python
    return any(fg.get(s) in ("unterbestimmt", 1) for s in (instanz_id, k, gruppe) if s)  # 1: Spec 4a §8.1
```

durch:

```python
    return any(fg.get(s) in ("unterbestimmt", 1, "gekoppelt") for s in (instanz_id, k, gruppe) if s)  # Spec 4a §8.1, 4b §5.5
```


- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_kopplung_plausibel.py` → `17 passed`. Ganze Suite →
**798 passed, 126 deselected** (die bestehenden Tests bleiben grün: `GRENZE_REFERENZ` trifft keine bestehende Referenz).

- [ ] **Step 5: Getriebeprobe validieren**

In einem Wegwerfordner (`$env:TEMP`) die Probe mit den vier Teil-Specs der Referenz zusammenlegen und validieren:
`.venv\Scripts\python.exe -m swki validieren <ordner>\getriebeprobe.yaml` → `"gueltig": true`, `"hinweise": []`.

- [ ] **Step 6: Commit**

```powershell
git add schema/baugruppe.schema.json swki/baugruppe/plausibel.py swki/baugruppe/bewertung.py tests/baugruppe/beispiel_kopplung.py tests/baugruppe/test_kopplung_plausibel.py
git commit -m "baugruppe: Format und Plausibilität der Kopplungen, gekoppelt, GRENZE_REFERENZ (Stufe 4b, Task 9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Sollweg, gekoppelte Freiheitsgrade, Reste aus 4a (ohne SolidWorks)

**Files:**
- Modify: `swki/pruefung/bewertung.py`, `swki/baugruppe/bewertung.py` (Umbenennung), `swki/baugruppe/bewegung.py`
  (Umbenennung und Sollweg), `swki/pruefung/bericht.py`, `tests/baugruppe/test_bewegung.py`,
  `tests/baugruppe/test_pruefen_baugruppe.py`
- Test: `tests/baugruppe/test_sollweg.py` (neu)

**Interfaces:**
- Consumes: `kopplung.antriebsmenge`, `kopplung.gekoppelte`.
- Produces: `swki.pruefung.bewertung.eintrag(pid, ok, **daten)` und `beschreibung(e)` (öffentlich, ersetzen
  `_pruefung`/`_beschreibung`); `Bewegung.gekoppelt: tuple[str, ...] = ()`; `drehung_um(q, achse) -> float`,
  `aufsummiert(lagen, kid, achse) -> list[float] | None`; Prüfungen `freiheitsgrad:<k>` auch für gekoppelte Komponenten,
  `sollweg:<Bewegung>:<k>` (Reihenfolge je Bewegung: freiheitsgrad…, bewegung, bewegung_kollision, grenze, endlage…,
  sollweg…); `endlage`/`sollweg`/`grenze` bei abgebrochenem Lauf `ok=None`; Lauf-Bericht mit `grenz_id`, `bereich`;
  `bericht.md` mit Grenze/Bereich und „Endlagen und Sollweg“.

- [ ] **Step 1: Tests schreiben bzw. anpassen**

`tests/baugruppe/test_sollweg.py` anlegen:

```python
"""Sollweg je Stellung, aufsummierte Drehung, gekoppelte Freiheitsgrade (Spec 4b §5.6) ohne SolidWorks."""

import pytest

from swki.baugruppe.bewegung import (Bewegung, BewegungsMesswerte, Lauf, aufsummiert, bewegungen, bewerte_bewegungen,
                                     drehmatrix, drehung_um)
from tests.baugruppe.beispiel_kopplung import spec as trieb_spec

EINS = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
UNTEN = [0, 0, -1]


def _t(c, v=(0.0, 0.0, 0.0)) -> list[float]:
    return [c[k % 3][k // 3] for k in range(9)] + [x / 1000 for x in v] + [1.0, 0.0, 0.0, 0.0]


def _spec(endlagen: list[dict]) -> dict:
    return {"parameter": {}, "bewegungen": [{"name": "Hub", "grenze": "g1", "erwartet": {"endlagen": endlagen}}]}


HUB = Bewegung("Hub", "g1", "abstand", "schlitten", 0.0, 200.0, 4, ("rad",))


def _lauf(schlitten_x, rad_winkel, fehler=None) -> Lauf:
    stellungen = [0.0, 50.0, 100.0, 150.0, 200.0]
    lagen = [{"schlitten": _t(EINS, (x, 0, 0)), "rad": _t(drehmatrix(UNTEN, w))} for x, w in zip(schlitten_x, rad_winkel)]
    return Lauf("Hub", stellungen=stellungen, lagen=lagen, fehler=fehler, grenze={"oben": False, "unten": None})


def _bewerte(lauf: Lauf, endlagen: list[dict], frei=None, gehalten=None) -> dict:
    m = BewegungsMesswerte(frei or {"schlitten": 2, "rad": 2}, gehalten or {"schlitten": 3, "rad": 3}, [lauf], [])
    pruefungen, _ = bewerte_bewegungen(_spec(endlagen), [HUB], m, 0.1)
    return {p["id"]: p for p in pruefungen}


RAD_ENDLAGE = {"komponente": "rad", "drehung": {"achse": UNTEN, "winkel": 630}}
LINEAR = ([0, 50, 100, 150, 200], [0, 157.5, 315, 472.5, 630])


def test_drehung_um():
    assert drehung_um(drehmatrix((0, 0, 1), 30), (0, 0, 1)) == pytest.approx(30)
    assert drehung_um(drehmatrix((0, 0, 1), 30), (0, 0, -1)) == pytest.approx(-30)
    assert drehung_um(drehmatrix((0, 0, 1), 170), (0, 0, 1)) == pytest.approx(170)


def test_aufsummiert_ueber_360():
    lagen = [{"rad": _t(drehmatrix(UNTEN, w))} for w in LINEAR[1]]
    assert aufsummiert(lagen, "rad", UNTEN) == pytest.approx(LINEAR[1])
    assert aufsummiert(lagen, "fehlt", UNTEN) is None


def test_sollweg_und_endlage_ueber_360_bestanden():
    p = _bewerte(_lauf(*LINEAR), [{"komponente": "schlitten", "verschiebung": [200, 0, 0]}, RAD_ENDLAGE])
    assert p["sollweg:Hub:schlitten"]["ok"] is True and p["sollweg:Hub:rad"]["ok"] is True
    assert p["endlage:Hub:rad"]["ok"] is True and p["endlage:Hub:rad"]["ist"]["aufsummiert"] == pytest.approx(630)


def test_sollweg_findet_rutschen_in_der_mitte():
    x = [0, 50, 90, 150, 200]  # Endlagen stimmen, Stellung 100 nicht
    p = _bewerte(_lauf(x, LINEAR[1]), [{"komponente": "schlitten", "verschiebung": [200, 0, 0]}, RAD_ENDLAGE])
    assert p["endlage:Hub:schlitten"]["ok"] is True
    s = p["sollweg:Hub:schlitten"]
    assert s["ok"] is False and s["knoten"] == ["schlitten"]
    assert s["ist"]["erste_abweichung"]["stellung"] == 100.0 and s["ist"]["erste_abweichung"]["was"] == "weg"


def test_sollweg_falsche_uebersetzung():
    winkel = [0, 160, 320, 480, 640]  # 160° statt 157,5° je Schritt
    p = _bewerte(_lauf(LINEAR[0], winkel), [RAD_ENDLAGE])
    assert p["sollweg:Hub:rad"]["ok"] is False and p["sollweg:Hub:rad"]["ist"]["erste_abweichung"]["stellung"] == 50.0
    assert p["endlage:Hub:rad"]["ok"] is False and p["endlage:Hub:rad"]["ist"]["aufsummiert"] == pytest.approx(640)


def test_sollweg_falsche_drehrichtung():
    p = _bewerte(_lauf(LINEAR[0], [-w for w in LINEAR[1]]), [RAD_ENDLAGE])
    assert p["sollweg:Hub:rad"]["ok"] is False and p["endlage:Hub:rad"]["ok"] is False


def test_verschiebung_in_winkelbewegung_nur_am_ende():
    schwenk = Bewegung("Hub", "g1", "winkel", "rad", 0.0, 90.0, 2)
    lagen = [{"rad": _t(drehmatrix(UNTEN, w), (0, 0, 0))} for w in (0, 45, 90)]
    lauf = Lauf("Hub", stellungen=[0.0, 45.0, 90.0], lagen=lagen, grenze={"oben": False, "unten": None})
    spec = _spec([{"komponente": "rad", "verschiebung": [5, 0, 0]}])
    pruefungen, _ = bewerte_bewegungen(spec, [schwenk], BewegungsMesswerte({"rad": 2}, {"rad": 3}, [lauf], []), 0.1)
    p = {x["id"]: x for x in pruefungen}
    assert p["sollweg:Hub:rad"]["ok"] is True and p["endlage:Hub:rad"]["ok"] is False


def test_abgebrochener_lauf_nicht_geprueft():
    p = _bewerte(_lauf(*LINEAR, fehler={"stellung": 50.0, "meldung": "x"}), [RAD_ENDLAGE])
    assert p["sollweg:Hub:rad"]["ok"] is None and p["endlage:Hub:rad"]["ok"] is None and p["grenze:Hub"]["ok"] is None


def test_freiheitsgrad_gekoppelt():
    p = _bewerte(_lauf(*LINEAR), [RAD_ENDLAGE], frei={"schlitten": 2, "rad": 2}, gehalten={"schlitten": 3, "rad": 2})
    assert p["freiheitsgrad:schlitten"]["ok"] is True
    assert p["freiheitsgrad:rad"]["ok"] is False and "mehr als ein Freiheitsgrad" in p["freiheitsgrad:rad"]["hinweis"]


def test_bewegungen_kennen_die_gekoppelten():
    [hub] = bewegungen(trieb_spec(), {"bewegung_schritte": 8})
    assert hub.komponente == "schlitten" and hub.gekoppelt == ("ritzelwelle", "antriebswelle")


def test_laufbericht_mit_grenze_und_bereich():
    m = BewegungsMesswerte({"schlitten": 2, "rad": 2}, {"schlitten": 3, "rad": 3}, [_lauf(*LINEAR)], [])
    _, bericht = bewerte_bewegungen(_spec([]), [HUB], m, 0.1)
    assert bericht["laeufe"][0]["grenz_id"] == "g1" and bericht["laeufe"][0]["bereich"] == [0.0, 200.0]
```

In `tests/baugruppe/test_bewegung.py` ersetzen:

```python
        "freiheitsgrad:schieber", "bewegung:Hub", "bewegung_kollision:Hub", "grenze:Hub", "endlage:Hub:schieber",
        "endlage:Hub:hebel", "freiheitsgrad:hebel", "bewegung:Schwenk", "bewegung_kollision:Schwenk", "grenze:Schwenk",
        "endlage:Schwenk:hebel"]
```

durch:

```python
        "freiheitsgrad:schieber", "bewegung:Hub", "bewegung_kollision:Hub", "grenze:Hub", "endlage:Hub:schieber",
        "endlage:Hub:hebel", "sollweg:Hub:schieber", "sollweg:Hub:hebel", "freiheitsgrad:hebel", "bewegung:Schwenk",
        "bewegung_kollision:Schwenk", "grenze:Schwenk", "endlage:Schwenk:hebel", "sollweg:Schwenk:hebel"]
```

In `tests/baugruppe/test_bewegung.py` ersetzen:

```python
    assert p["endlage:Hub:schieber"]["ok"] is False and "abgebrochen" in p["endlage:Hub:schieber"]["hinweis"]
```

durch:

```python
    # 4a-Rest (Spec 4b §6.2): abgebrochene Läufe einheitlich nicht geprüft
    assert p["endlage:Hub:schieber"]["ok"] is None and "abgebrochen" in p["endlage:Hub:schieber"]["hinweis"]
    assert p["sollweg:Hub:schieber"]["ok"] is None
```

In `tests/baugruppe/test_pruefen_baugruppe.py` ersetzen:

```python
    laeufe = [{"bewegung": "Hub", "gegen": {}, "stellungen": 17, "bewegt": ["schlitten", "hebel"], "kollisionen": 0,
               "grenze": {"oben": False, "unten": None}, "dauer_s": 12.5},
              {"bewegung": "Hub", "gegen": {"Schwenk": "max"}, "stellungen": 17, "bewegt": [], "kollisionen": 1,
               "grenze": {}, "dauer_s": 9.0}]
    bericht = {"maengel": [], "bilder": {},
               "bewegungen": {"laeufe": laeufe, "paare": [{"bewegungen": ["Hub", "Schwenk"], "schnitt": [0] * 6}]}}
    text = bericht_markdown(BAUGRUPPE, "A", [], ("pruefen", "…"), bericht, None, None, [])
    for teil in ("## Bewegungen (letzter Lauf)", "| Hub | Grundstellung | 17 | schlitten, hebel | 0 | wirkt / – | 12.5 |",
                 "| Hub | Schwenk auf max | 17 | – | 1 | – / – | 9.0 |", "Paarläufe für: Hub × Schwenk"):
        assert teil in text, text
```

durch:

```python
    laeufe = [{"bewegung": "Hub", "grenz_id": "g1", "bereich": [0.0, 220.0], "gegen": {}, "stellungen": 17,
               "bewegt": ["schlitten", "hebel"], "kollisionen": 0, "grenze": {"oben": False, "unten": None}, "dauer_s": 12.5},
              {"bewegung": "Hub", "gegen": {"Schwenk": "max"}, "stellungen": 17, "bewegt": [], "kollisionen": 1,
               "grenze": {}, "dauer_s": 9.0}]
    pruefungen = [{"id": "endlage:Hub:schlitten", "ok": True, "knoten": []},
                  {"id": "sollweg:Hub:schlitten", "ok": False, "ist": {"erste_abweichung": {"stellung": 55.0}},
                   "hinweis": "weg bei 55", "knoten": ["schlitten"]},
                  {"id": "sollweg:Hub:hebel", "ok": None, "hinweis": "Lauf abgebrochen", "knoten": []}]
    bericht = {"maengel": [], "bilder": {}, "pruefungen": pruefungen,
               "bewegungen": {"laeufe": laeufe, "paare": [{"bewegungen": ["Hub", "Schwenk"], "schnitt": [0] * 6}]}}
    text = bericht_markdown(BAUGRUPPE, "A", [], ("pruefen", "…"), bericht, None, None, [])
    for teil in ("## Bewegungen (letzter Lauf)",
                 "| Hub | g1 | 0 … 220 | Grundstellung | 17 | schlitten, hebel | 0 | wirkt / – | 12.5 |",
                 "| Hub | – | – | Schwenk auf max | 17 | – | 1 | – / – | 9.0 |", "Paarläufe für: Hub × Schwenk",
                 "## Endlagen und Sollweg (letzter Lauf)", "| endlage:Hub:schlitten | bestanden | – |",
                 "| sollweg:Hub:schlitten | Mangel | sollweg:Hub:schlitten: weg bei 55 |",
                 "| sollweg:Hub:hebel | nicht geprüft | sollweg:Hub:hebel: Lauf abgebrochen |"):
        assert teil in text, text
```


- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_sollweg.py tests\baugruppe\test_bewegung.py tests\baugruppe\test_pruefen_baugruppe.py`
Expected: FAIL – `1 error` beim Sammeln von `test_sollweg.py` (`ImportError: cannot import name 'aufsummiert'`).

- [ ] **Step 3: Private Helfer öffentlich machen (4a-Rest)**

Run (PowerShell):

```powershell
@'
import re
from pathlib import Path

for datei in ("swki/pruefung/bewertung.py", "swki/baugruppe/bewertung.py", "swki/baugruppe/bewegung.py"):
    p = Path(datei)
    t = p.read_bytes().decode("utf-8")
    t = re.sub(r"\b_pruefung\b", "eintrag", t)
    t = re.sub(r"\b_beschreibung\b", "beschreibung", t)
    p.write_bytes(t.encode("utf-8"))
'@ | .venv\Scripts\python.exe -
```

Danach `git diff --stat`: nur diese drei Dateien; `grep -rn "_pruefung\b\|_beschreibung\b" swki` findet nichts mehr.

- [ ] **Step 4: Umsetzen**

In `swki/baugruppe/bewegung.py` ersetzen:

```python
from swki.baugruppe.geometrie import drehmatrix
```

durch:

```python
from swki.baugruppe.geometrie import drehmatrix
from swki.baugruppe.kopplung import antriebsmenge, gekoppelte
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
"""Bewegungsprüfung ohne SolidWorks (Spec 4a §8.2): Bewegungen aus der Spezifikation, Lagevergleich aus
Transformationen, überstrichene Räume, Paare, Endlagen und die Bewertung zu Prüfungen und Mängeln.
```

durch:

```python
"""Bewegungsprüfung ohne SolidWorks (Spec 4a §8.2, 4b §5.6): Bewegungen aus der Spezifikation, Lagevergleich aus
Transformationen, überstrichene Räume, Paare, Endlagen, Sollweg je Stellung (aufsummierte Drehung) und die Bewertung
zu Prüfungen und Mängeln.
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
    max: float
    schritte: int
```

durch:

```python
    max: float
    schritte: int
    gekoppelt: tuple[str, ...] = ()  # über Kopplungen getriebene Komponenten (Spec 4b §5.6.1)
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
    """Bewegungen der Spezifikation mit ausgewerteten Grenzen (setzt eine plausible Spezifikation voraus)."""
    p = spec.get("parameter", {})
```

durch:

```python
    """Bewegungen der Spezifikation mit ausgewerteten Grenzen und den gekoppelten Komponenten (setzt eine plausible
    Spezifikation voraus)."""
    p = spec.get("parameter", {})
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
        ergebnis.append(Bewegung(b["name"], b["grenze"], "abstand" if v["typ"] == "grenze_abstand" else "winkel",
                                 v["a"]["komponente"], auswerten(v["min"], p), auswerten(v["max"], p),
                                 b.get("schritte", standard["bewegung_schritte"])))
```

durch:

```python
        kid = v["a"]["komponente"]
        ergebnis.append(Bewegung(b["name"], b["grenze"], "abstand" if v["typ"] == "grenze_abstand" else "winkel",
                                 kid, auswerten(v["min"], p), auswerten(v["max"], p),
                                 b.get("schritte", standard["bewegung_schritte"]),
                                 tuple(gekoppelte(spec, antriebsmenge(spec, kid)))))
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
def ist_bewegt(t0, t1) -> bool:
```

durch:

```python
def drehung_um(q, achse) -> float:
    """Vorzeichenbehafteter Drehwinkel (Grad, −180 … 180) der Drehmatrix q um die Einheitsachse achse (Rechte-Hand-
    Regel): sin = (v·achse)/2 mit v aus dem schiefsymmetrischen Anteil, cos = (Spur − 1)/2."""
    v = (q[2][1] - q[1][2], q[0][2] - q[2][0], q[1][0] - q[0][1])
    return math.degrees(math.atan2(sum(v[i] * achse[i] for i in range(3)) / 2, (q[0][0] + q[1][1] + q[2][2] - 1) / 2))


def _einheit(achse) -> tuple[float, float, float]:
    n = math.sqrt(sum(c * c for c in achse))
    return tuple(c / n for c in achse)


def aufsummiert(lagen: list[dict[str, list[float]]], kid: str, achse) -> list[float] | None:
    """Drehwinkel (Grad) von kid um achse je Stellung gegenüber der ersten, Schritt für Schritt aufsummiert (Spec 4b
    §5.6.3; jede Teildrehung < 180°). None, wenn kid in einer Stellung fehlt."""
    if any(kid not in lage for lage in lagen):
        return None
    n = _einheit(achse)
    werte = [0.0]
    for vor, nach in zip(lagen, lagen[1:]):
        werte.append(werte[-1] + drehung_um(relative_drehung(vor[kid], nach[kid]), n))
    return werte


def ist_bewegt(t0, t1) -> bool:
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
def _freiheitsgrad(b: Bewegung, frei: dict[str, int], gehalten: dict[str, int]) -> dict:
    """Freiheitsgrad belegt: mit unterdrückten Grenzen ohne Antrieb unterbestimmt, mit Antrieb auf min voll bestimmt
    (die aktive Grenze zählt für GetConstrainedStatus schon als Bindung, Spike S13/S13b)."""
    vorher = frei.get(b.komponente)
    nachher = gehalten.get(b.komponente)
```

durch:

```python
def _freiheitsgrad(kid: str, frei: dict[str, int], gehalten: dict[str, int]) -> dict:
    """Freiheitsgrad belegt: mit unterdrückten Grenzen ohne Antrieb unterbestimmt, mit Antrieb auf min voll bestimmt
    (die aktive Grenze zählt für GetConstrainedStatus schon als Bindung, Spike S13/S13b). Für die bewegte Komponente
    und jede gekoppelte Komponente der Bewegung (Spec 4b §5.6.1)."""
    vorher = frei.get(kid)
    nachher = gehalten.get(kid)
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
    return eintrag(f"freiheitsgrad:{b.komponente}", not gruende,
                     ist={"ohne_antrieb": vorher, "mit_antrieb": nachher}, knoten=[b.komponente],
```

durch:

```python
    return eintrag(f"freiheitsgrad:{kid}", not gruende,
                     ist={"ohne_antrieb": vorher, "mit_antrieb": nachher}, knoten=[kid],
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
    if grund is None or grund.fehler is not None or not grund.lagen:
        return eintrag(pid, False, hinweis="Lauf abgebrochen – Endlage nicht messbar", knoten=[kid])
```

durch:

```python
    if grund is None or grund.fehler is not None or not grund.lagen:
        return eintrag(pid, None, hinweis="Lauf abgebrochen – Endlage nicht geprüft", knoten=[kid])
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
    achse = [auswerten(w, p) for w in e["drehung"]["achse"]]
    winkel = auswerten(e["drehung"]["winkel"], p)
    q = relative_drehung(erste, letzte)
    abweichung = winkel_grad(_mal(q, _transponiert(drehmatrix(achse, winkel))))
    ist_achse, ist_winkel = achse_winkel(q)
    return eintrag(pid, abweichung <= TOL_WINKEL_GRAD,
                     ist={"achse": [round(c, 6) for c in ist_achse] if ist_achse else None, "winkel": round(ist_winkel, 4)},
                     soll={"achse": achse, "winkel": winkel}, abweichung_grad=round(abweichung, 4), knoten=[kid])
```

durch:

```python
    achse = [auswerten(w, p) for w in e["drehung"]["achse"]]
    winkel = auswerten(e["drehung"]["winkel"], p)
    q = relative_drehung(erste, letzte)
    abweichung = winkel_grad(_mal(q, _transponiert(drehmatrix(achse, winkel))))
    ist_achse, ist_winkel = achse_winkel(q)
    summe = aufsummiert(grund.lagen, kid, achse)
    ok = abweichung <= TOL_WINKEL_GRAD and (summe is None or abs(summe[-1] - winkel) <= TOL_WINKEL_GRAD)
    return eintrag(pid, ok,
                   ist={"achse": [round(c, 6) for c in ist_achse] if ist_achse else None, "winkel": round(ist_winkel, 4),
                        "aufsummiert": None if summe is None else round(summe[-1], 4)},
                   soll={"achse": achse, "winkel": winkel}, abweichung_grad=round(abweichung, 4), knoten=[kid])


def _sollweg(b: Bewegung, kid: str, eintraege: list[dict], grund: Lauf | None, p: dict, tol_mm: float) -> dict:
    """Sollweg je Stellung (Spec 4b §5.6.2): die bewegte Komponente erreicht den befohlenen Wert; jede Endlage drehung
    und jede verschiebung einer Abstandsbewegung steht in jeder Stellung auf ihrem Anteil (lineare Kopplungen).
    Gemeldet wird die erste abweichende Stellung."""
    pid = f"sollweg:{b.name}:{kid}"
    if grund is None or grund.fehler is not None or not grund.lagen:
        return eintrag(pid, None, hinweis="Lauf abgebrochen – Sollweg nicht geprüft", knoten=[kid])
    if any(kid not in lage for lage in grund.lagen):
        return eintrag(pid, False, hinweis=f"Komponente {kid} fehlt in der Baugruppe", knoten=[kid])
    summen = {i: aufsummiert(grund.lagen, kid, [auswerten(w, p) for w in e["drehung"]["achse"]])
              for i, e in enumerate(eintraege) if "drehung" in e}
    t0 = grund.lagen[0][kid]
    abweichungen = []
    for s, (w, lage) in enumerate(zip(grund.stellungen, grund.lagen)):
        anteil = (w - b.min) / (b.max - b.min)
        t = lage[kid]
        if kid == b.komponente:
            ist, soll = weg(b, t0, t), soll_weg(b, w)
            if abs(ist - soll) > (tol_mm if b.art == "abstand" else TOL_WINKEL_GRAD):
                abweichungen.append({"stellung": w, "was": "weg", "soll": round(soll, 4), "ist": round(ist, 4)})
        for i, e in enumerate(eintraege):
            if "verschiebung" in e:
                if b.art != "abstand":
                    continue  # Bogen: nur die Endlage (Spec 4b §5.6.2)
                soll_v = [anteil * auswerten(x, p) for x in e["verschiebung"]]
                ist_v = verschiebung_mm(t0, t)
                if any(abs(a - c) > tol_mm for a, c in zip(ist_v, soll_v)):
                    abweichungen.append({"stellung": w, "was": "verschiebung", "soll": [round(c, 4) for c in soll_v],
                                         "ist": [round(c, 4) for c in ist_v]})
            else:
                achse = [auswerten(x, p) for x in e["drehung"]["achse"]]
                soll_w = anteil * auswerten(e["drehung"]["winkel"], p)
                q = relative_drehung(t0, t)
                rest = winkel_grad(_mal(q, _transponiert(drehmatrix(achse, soll_w))))
                if rest > TOL_WINKEL_GRAD or abs(summen[i][s] - soll_w) > TOL_WINKEL_GRAD:
                    abweichungen.append({"stellung": w, "was": "drehung", "soll": round(soll_w, 4),
                                         "ist": round(summen[i][s], 4), "abweichung_grad": round(rest, 4)})
    return eintrag(pid, not abweichungen, ist={"erste_abweichung": abweichungen[0] if abweichungen else None,
                                                "abweichende_stellungen": len({a["stellung"] for a in abweichungen})},
                   stellungen=len(grund.stellungen), knoten=[kid] if abweichungen else [])
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
def _lauf_bericht(lauf: Lauf) -> dict:
    return {"bewegung": lauf.bewegung, "gegen": lauf.gegen, "stellungen": len(lauf.stellungen), "bewegt": lauf.bewegt,
```

durch:

```python
def _lauf_bericht(lauf: Lauf, b: Bewegung) -> dict:
    return {"bewegung": lauf.bewegung, "grenz_id": b.grenze, "bereich": [b.min, b.max], "gegen": lauf.gegen,
            "stellungen": len(lauf.stellungen), "bewegt": lauf.bewegt,
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
    """Prüfungen je Bewegung (Spec 4a §8.2): freiheitsgrad, bewegung, bewegung_kollision, grenze, endlage; dazu der
    Bewegungsteil des Prüfberichts (Spec 4a §8.5). Der Freiheitsgrad kommt aus den Messwerten (status_frei,
    status_gehalten), nicht aus der statischen Prüfung."""
```

durch:

```python
    """Prüfungen je Bewegung (Spec 4a §8.2, 4b §5.6): freiheitsgrad (bewegte und gekoppelte Komponenten), bewegung,
    bewegung_kollision, grenze, endlage, sollweg; dazu der Bewegungsteil des Prüfberichts (Spec 4a §8.5, 4b §6.1). Der
    Freiheitsgrad kommt aus den Messwerten (status_frei, status_gehalten), nicht aus der statischen Prüfung."""
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
        pruefungen.append(_freiheitsgrad(b, m.status_frei, m.status_gehalten))
```

durch:

```python
        pruefungen += [_freiheitsgrad(k, m.status_frei, m.status_gehalten) for k in (b.komponente, *b.gekoppelt)]
```

In `swki/baugruppe/bewegung.py` ersetzen:

```python
        pruefungen += [_endlage(b, e, grund, p, tol_mm) for e in erwartet.get(b.name, {}).get("endlagen", [])]
    return pruefungen, {"laeufe": [_lauf_bericht(lauf) for lauf in m.laeufe], "paare": m.paare}
```

durch:

```python
        endlagen = erwartet.get(b.name, {}).get("endlagen", [])
        pruefungen += [_endlage(b, e, grund, p, tol_mm) for e in endlagen]
        for kid in dict.fromkeys([b.komponente, *(e["komponente"] for e in endlagen)]):
            pruefungen.append(_sollweg(b, kid, [e for e in endlagen if e["komponente"] == kid], grund, p, tol_mm))
    nach_name = {b.name: b for b in bws}
    return pruefungen, {"laeufe": [_lauf_bericht(lauf, nach_name[lauf.bewegung]) for lauf in m.laeufe], "paare": m.paare}
```

In `swki/pruefung/bericht.py` ersetzen:

```python
"""bericht.md eines Auftrags: Status, Läufe, offene Punkte, Screenshots, Phasenzeiten, Compiler-Änderungen."""
```

durch:

```python
"""bericht.md eines Auftrags: Status, Läufe, offene Punkte, Screenshots, Phasenzeiten, Compiler-Änderungen."""

from swki.pruefung.bewertung import beschreibung

_ERGEBNIS = {True: "bestanden", False: "Mangel", None: "nicht geprüft"}
```

In `swki/pruefung/bericht.py` ersetzen:

```python
        zeilen += ["", "## Bewegungen (letzter Lauf)", "",
                   "| Bewegung | Lauf | Stellungen | bewegt | Kollisionen | Grenze oben / unten | Dauer (s) |",
                   "|---|---|---|---|---|---|---|"]
        for lauf in bewegungen["laeufe"]:
            gegen = ", ".join(f"{n} auf {s}" for n, s in lauf["gegen"].items()) or "Grundstellung"
            grenze = " / ".join(_grenze_text(lauf["grenze"].get(s)) for s in ("oben", "unten"))
            zeilen.append(f"| {lauf['bewegung']} | {gegen} | {lauf['stellungen']} | {', '.join(lauf['bewegt']) or '–'} | "
                          f"{lauf['kollisionen']} | {grenze} | {lauf['dauer_s']} |")
        if bewegungen.get("paare"):
            zeilen += ["", "Paarläufe für: " + "; ".join(" × ".join(p["bewegungen"]) for p in bewegungen["paare"])]
```

durch:

```python
        zeilen += ["", "## Bewegungen (letzter Lauf)", "",
                   "| Bewegung | Grenze | Bereich | Lauf | Stellungen | bewegt | Kollisionen | Grenze oben / unten | "
                   "Dauer (s) |",
                   "|---|---|---|---|---|---|---|---|---|"]
        for lauf in bewegungen["laeufe"]:
            gegen = ", ".join(f"{n} auf {s}" for n, s in lauf["gegen"].items()) or "Grundstellung"
            grenze = " / ".join(_grenze_text(lauf["grenze"].get(s)) for s in ("oben", "unten"))
            bereich = " … ".join(f"{w:g}" for w in lauf["bereich"]) if lauf.get("bereich") else "–"
            zeilen.append(f"| {lauf['bewegung']} | {lauf.get('grenz_id', '–')} | {bereich} | {gegen} | {lauf['stellungen']} | "
                          f"{', '.join(lauf['bewegt']) or '–'} | {lauf['kollisionen']} | {grenze} | {lauf['dauer_s']} |")
        if bewegungen.get("paare"):
            zeilen += ["", "Paarläufe für: " + "; ".join(" × ".join(p["bewegungen"]) for p in bewegungen["paare"])]
        wege = [e for e in letzter.get("pruefungen", []) if e["id"].startswith(("endlage:", "sollweg:"))]
        if wege:
            zeilen += ["", "## Endlagen und Sollweg (letzter Lauf)", "", "| Prüfung | Ergebnis | Befund |", "|---|---|---|"]
            zeilen += [f"| {e['id']} | {_ERGEBNIS[e['ok']]} | {'–' if e['ok'] else beschreibung(e)} |" for e in wege]
```


- [ ] **Step 5: Tests laufen lassen, sie bestehen**

Run: wie Step 2 → `39 passed`. Ganze Suite → **809 passed, 126 deselected**; `pruefe-code` ohne Befund.

- [ ] **Step 6: Commit**

```powershell
git add swki/pruefung/bewertung.py swki/baugruppe/bewertung.py swki/baugruppe/bewegung.py swki/pruefung/bericht.py tests/baugruppe/test_sollweg.py tests/baugruppe/test_bewegung.py tests/baugruppe/test_pruefen_baugruppe.py
git commit -m "bewegung: Sollweg je Stellung, aufsummierte Drehung, gekoppelte Freiheitsgrade, Reste aus 4a (Stufe 4b, Task 10)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: SolidWorks-Schicht und Bau der Kopplungen (ohne SolidWorks und live)

**Files:**
- Modify: `swki/verbindung.py`, `swki/baugruppe/sw_baugruppe.py`, `swki/baugruppe/fehler.py`, `swki/baugruppe/referenzen.py`,
  `swki/baugruppe/bau.py`
- Test: `tests/baugruppe/test_sw_kopplung.py` (neu), `tests/live/test_live_kopplung.py` (neu, ein Live-Test)

**Interfaces:**
- Consumes: `kopplung` (`KOPPLUNGEN`, `drehe`, `in_baugruppe`, `phasenfehler`, `phasenwinkel`, `teilkreise`,
  `verzahnung_der_seite`), `verzahnung_im_teil`, `kante_aus`.
- Produces: `swki.verbindung.dispatch_array(objekte)`; `sw_baugruppe.MATE_KOPPLUNG`, `REVERSE`, `MARKE_ZAHNSTANGE`,
  `MARKE_RITZEL`, `SW_RITZEL_TEILKREIS`, `waehle(asm, entitaet, anhaengen, marke=MARKE)`, `kopple(asm, v, a, b, zaehler_mm,
  nenner_mm, umkehren)`, `lies_kopplung(feature) -> dict`, `ist_unterdrueckt(feature) -> bool`, `setze_lage(app, asm, komp,
  t)`; `fehler.ZAHNPHASE_FEHLER`; `referenzen.kopplung_referenz(ctx, fid) -> TeilReferenz`; in `bau`: `TOL_PHASE`,
  `_verzahnungen`, `_zahnphase` (Knoten `zahnphase:<id>`), `_entitaet_kopplung`, `_kopple`; `_verknuepfe` legt Kopplungen
  über `_kopple` an.

**Vor dem Task:** Ledger-Entscheidungen zu S14b Zeilen 6, 7 und 13.

- [ ] **Step 1: Tests schreiben**

`tests/baugruppe/test_sw_kopplung.py` anlegen:

```python
"""Stufe 4b: SolidWorks-Schicht der Kopplungen mit Attrappen – CreateMate, Rücklesen, Unterdrückung, Zahnphase und
Kopplung beim Bau (Spec 4b §5.4)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.baugruppe import bau, sw_baugruppe
from swki.baugruppe.aufloesen import Verknuepfung, verknuepfungen
from swki.baugruppe.fehler import ZAHNPHASE_FEHLER
from swki.baugruppe.kopplung import in_baugruppe, phasenfehler, verzahnung_der_seite
from swki.baugruppe.modell import Baugruppe
from swki.compiler.fehler import BauFehler
from swki.compiler.protokoll import Protokoll
from tests.baugruppe.beispiel_kopplung import TEILE, quellen, spec


class _Mate:
    def __init__(self, typ: int):
        self.Name = "Mate1"
        self.GetSpecificFeature2 = SimpleNamespace(Type=typ)


class _Asm:
    def __init__(self):
        self.mates: list[_Mate] = []
        self.daten: list[SimpleNamespace] = []
        self.anlegen = True

    def CreateMateData(self, typ):  # noqa: N802 (SolidWorks-Name)
        self.daten.append(SimpleNamespace(typ=typ))
        return self.daten[-1]

    def CreateMate(self, daten):  # noqa: N802 (SolidWorks-Name)
        if not self.anlegen:
            return None
        self.mates.append(_Mate(daten.typ))
        return self.mates[-1]


@pytest.fixture
def asm(monkeypatch):
    a = _Asm()
    a.auswahl = []
    monkeypatch.setattr(sw_baugruppe, "verknuepfungen", lambda _asm: list(a.mates))
    monkeypatch.setattr(sw_baugruppe, "waehle", lambda asm_, ent, anhaengen, marke=1: a.auswahl.append((ent, marke)))
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda feature: 0)
    monkeypatch.setattr(sw_baugruppe, "dispatch_array", list)
    monkeypatch.setattr(sw_baugruppe.sw, "auswahl_leeren", lambda model: None)
    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", lambda model: None)
    return a


def _v(vid: str, typ: str) -> Verknuepfung:
    return Verknuepfung(vid, vid, typ, {}, {}, None, None, False)


def test_kopple_zahnrad(asm):
    feature = sw_baugruppe.kopple(asm, _v("k2", "zahnrad"), ("A", False), ("B", False), 100.0, 50.0, True)
    [d] = asm.daten
    assert d.typ == 10 and d.EntitiesToMate == ["A", "B"] and d.Reverse is True
    assert d.GearRatioNumerator == pytest.approx(0.1) and d.GearRatioDenominator == pytest.approx(0.05)
    assert feature.Name == "k2" and asm.auswahl == []


def test_kopple_zahnstange_mit_vorauswahl(asm):
    sw_baugruppe.kopple(asm, _v("k1", "zahnstange"), ("Ritzel", False), ("Stange", False), 40.0, 0.0, False)
    [d] = asm.daten
    assert d.typ == 13 and d.DiameterType == 0 and d.DiameterVal == pytest.approx(0.04) and d.Reverse is False
    assert asm.auswahl == [(("Stange", False), 64), (("Ritzel", False), 128)]


def test_kopple_ohne_verknuepfung(asm):
    asm.anlegen = False
    with pytest.raises(BauFehler, match="k2 \\(zahnrad\\): CreateMate legt keine Verknüpfung an"):
        sw_baugruppe.kopple(asm, _v("k2", "zahnrad"), ("A", False), ("B", False), 100.0, 50.0, False)


def test_kopple_mit_fehlercode_loescht_wieder(asm, monkeypatch):
    geloescht = []
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda feature: 47)
    monkeypatch.setattr(sw_baugruppe, "_loesche_still", lambda asm_, f: geloescht.append(f.Name))
    with pytest.raises(BauFehler, match="Fehlercode 47"):
        sw_baugruppe.kopple(asm, _v("k2", "zahnrad"), ("A", False), ("B", False), 100.0, 50.0, False)
    assert geloescht == ["k2"]


def test_lies_kopplung():
    zahnrad = SimpleNamespace(GetSpecificFeature2=SimpleNamespace(Type=10),
                              GetDefinition=SimpleNamespace(GearRatioNumerator=0.1, GearRatioDenominator=0.05, Reverse=0))
    assert sw_baugruppe.lies_kopplung(zahnrad) == {"zaehler": 100.0, "nenner": 50.0, "umkehren": False}
    stange = SimpleNamespace(GetSpecificFeature2=SimpleNamespace(Type=13),
                             GetDefinition=SimpleNamespace(DiameterVal=0.04, DiameterType=0, Reverse=True))
    assert sw_baugruppe.lies_kopplung(stange) == {"durchmesser": 40.0, "art": 0, "umkehren": True}


def test_ist_unterdrueckt():
    assert sw_baugruppe.ist_unterdrueckt(SimpleNamespace(IsSuppressed=True)) is True


# --- Bau: Zahnphase und Kopplung ---------------------------------------------------------------------------------

EINS = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]


def _lage(x, y, z=0.0) -> list[float]:
    return EINS[:9] + [x / 1000, y / 1000, z / 1000] + EINS[12:]


@pytest.fixture
def baulauf(monkeypatch, tmp_path):
    s = spec()
    bg = Baugruppe(Path(tmp_path / "trieb.yaml"), s, quellen(), {f"{k}.yaml": t for k, t in TEILE.items()})
    lagen = {"zahnstange": _lage(0, 0), "ritzelwelle": _lage(37.3, 20.0), "antriebswelle": _lage(112.3, 20.0)}
    b = bau.Baulauf(object(), bg, "A", tmp_path, {}, Protokoll("A", "trieb.yaml", 1, 2025), asm=object())
    b.komponenten = {k: SimpleNamespace(name=k, Name2=k) for k in lagen}
    monkeypatch.setattr(sw_baugruppe, "transform", lambda komp: list(lagen[komp.name]))
    monkeypatch.setattr(sw_baugruppe, "setze_lage", lambda app, asm, komp, t: lagen.__setitem__(komp.name, t))
    b.lagen = lagen
    return b


def _kopplung(b, vid: str) -> Verknuepfung:
    return next(v for v in verknuepfungen(b.bg.spec, b.bg.quellen) if v.id == vid)


def _fehler(b, v) -> float:
    a, g = (in_baugruppe(verzahnung_der_seite(b.bg.quellen, s), b.lagen[s["komponente"]]) for s in (v.a, v.b))
    return phasenfehler(a, g)


def test_zahnphase_dreht_seite_a_in_die_luecke(baulauf):
    for vid in ("k1", "k2"):
        v = _kopplung(baulauf, vid)
        bau._zahnphase(baulauf, v)
        assert _fehler(baulauf, v) == pytest.approx(0.0, abs=1e-9)
    assert [k.id for k in baulauf.protokoll.knoten] == ["zahnphase:k1", "zahnphase:k2"]
    assert baulauf.lagen["zahnstange"] == _lage(0, 0)  # Seite b bleibt


def test_zahnphase_nicht_erreicht(baulauf, monkeypatch):
    monkeypatch.setattr(sw_baugruppe, "setze_lage", lambda app, asm, komp, t: None)  # SolidWorks dreht nicht
    v = _kopplung(baulauf, "k1")
    assert abs(_fehler(baulauf, v)) > bau.TOL_PHASE  # Vorbedingung: die Ausgangslage ist nicht in Phase
    with pytest.raises(BauFehler) as e:
        bau._zahnphase(baulauf, v)
    assert e.value.code == ZAHNPHASE_FEHLER and "Zahnphase k1" in str(e.value)


def test_kopple_mit_teilkreisen_und_richtung(baulauf, monkeypatch):
    aufrufe = []
    monkeypatch.setattr(bau, "_entitaet_kopplung", lambda b, seite: seite["komponente"])
    monkeypatch.setattr(sw_baugruppe, "kopple", lambda *args: aufrufe.append(args[1:]) or SimpleNamespace(Name="k"))
    bau._kopple(baulauf, _kopplung(baulauf, "k2"))
    bau._kopple(baulauf, _kopplung(baulauf, "k1"))
    assert [a[1:] for a in aufrufe] == [("antriebswelle", "ritzelwelle", 100.0, 50.0, False),
                                       ("ritzelwelle", "zahnstange", 40.0, 0.0, False)]
```

`tests/live/test_live_kopplung.py` anlegen:

```python
"""Live: Getriebeprobe (Spec 4b §10) – Zahnstangen- und Zahnradverknüpfung bauen (Zahnphase, Kopplung) und prüfen
(Eingriff, Sollweg, gekoppelte Freiheitsgrade, Bilder). SolidWorks muss laufen, frisch gestartet."""

import json
import shutil
from pathlib import Path

import pytest

from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-GETRIEBE"
PROBE = Path(__file__).resolve().parent / "getriebeprobe"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "zahnstangentrieb"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def probe(tmp_path):
    ordner = tmp_path / AUFTRAG
    ordner.mkdir()
    for quelle in [*PROBE.glob("*.yaml"), *(REFERENZ / n for n in ("zahnstange.yaml", "lagerbock.yaml",
                                                                    "ritzelwelle.yaml", "antriebswelle.yaml"))]:
        shutil.copy2(quelle, ordner / quelle.name)
    yield ordner / "getriebeprobe.yaml"
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _baue(capsys, spec: Path) -> dict:
    assert _lauf(capsys, "validieren", str(spec))[0] == 0
    assert _lauf(capsys, "freigeben", str(spec))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(spec))
    assert code == 0, bau
    return bau


def test_getriebeprobe_bauen(capsys, probe):
    bau = _baue(capsys, probe)
    knoten = {k["id"]: k["status"] for k in bau["knoten"]}
    assert [k for k in knoten if k.startswith("zahnphase:")] == ["zahnphase:k1", "zahnphase:k2"]
    assert all(knoten[k] == "ok" for k in ("zahnphase:k1", "k1", "zahnphase:k2", "k2", "grundstellung:Hub")), knoten
```


- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_sw_kopplung.py`
Expected: FAIL – `1 error` beim Sammeln (`ImportError: cannot import name 'ZAHNPHASE_FEHLER'`).

- [ ] **Step 3: Umsetzen**

In `swki/verbindung.py` ersetzen:

```python
def r8_array(werte) -> object:
```

durch:

```python
def dispatch_array(objekte) -> object:
    """Array von COM-Objekten (z. B. IGearMateFeatureData.EntitiesToMate)."""
    import pythoncom
    import win32com.client

    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, list(objekte))


def r8_array(werte) -> object:
```

In `swki/baugruppe/sw_baugruppe.py` ersetzen:

```python
from swki.verbindung import byref_bool, byref_long, grad, in_mm, in_mm3, mm, r8_array
```

durch:

```python
from swki.verbindung import byref_bool, byref_long, dispatch_array, grad, in_mm, in_mm3, mm, r8_array
```

In `swki/baugruppe/sw_baugruppe.py` ersetzen:

```python
IDENTITAET = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
```

durch:

```python
IDENTITAET = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
MATE_KOPPLUNG = {"zahnrad": 10, "zahnstange": 13}  # swMateType_e swMateGEAR / swMateRACKPINION (Spec 4b §5.4.3)
REVERSE = {"zahnrad": False, "zahnstange": False}  # IGear-/IRackPinionMateFeatureData.Reverse (Spike S14b Zeile 6)
MARKE_ZAHNSTANGE, MARKE_RITZEL = 64, 128  # Vorauswahl der Zahnstangenverknüpfung (API-Hilfe EntitiesToMate)
SW_RITZEL_TEILKREIS = 0  # swRackPinionMateDistanceOptions_e.swPinionPitchDiameter
```

In `swki/baugruppe/sw_baugruppe.py` ersetzen:

```python
def waehle(asm, entitaet: tuple[object, bool], anhaengen: bool) -> None:
    objekt, ist_feature = entitaet
    if ist_feature:
        ok = objekt.Select2(anhaengen, MARKE)
    else:
        daten = asm.SelectionManager.CreateSelectData
        daten.Mark = MARKE
        ok = objekt.Select4(anhaengen, daten)
```

durch:

```python
def waehle(asm, entitaet: tuple[object, bool], anhaengen: bool, marke: int = MARKE) -> None:
    objekt, ist_feature = entitaet
    if ist_feature:
        ok = objekt.Select2(anhaengen, marke)
    else:
        daten = asm.SelectionManager.CreateSelectData
        daten.Mark = marke
        ok = objekt.Select4(anhaengen, daten)
```

In `swki/baugruppe/sw_baugruppe.py` ersetzen:

```python
def komponenten(asm) -> list:
```

durch:

```python
def kopple(asm, v, a: tuple[object, bool], b: tuple[object, bool], zaehler_mm: float, nenner_mm: float,
           umkehren: bool):
    """Zahnrad- bzw. Zahnstangenverknüpfung über CreateMate (Spec 4b §5.4.3), als v.id benannt und neu aufgebaut.
    Zahnrad: EntitiesToMate = [a, b], Übersetzung als Teilkreis-Ø zaehler : nenner; Zahnstange: Vorauswahl Zahnstange
    (Marke 64) und Ritzel (Marke 128), DiameterVal = Teilkreis-Ø des Ritzels. Jede Ausnahme nach dem Anlegen löscht die
    neue Verknüpfung wieder."""
    vorher = len(verknuepfungen(asm))
    sw.auswahl_leeren(asm)
    daten = asm.CreateMateData(MATE_KOPPLUNG[v.typ])
    if daten is None:
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"{v.id} ({v.typ}): CreateMateData liefert nichts", schritt="verknuepfung")
    if v.typ == "zahnrad":
        daten.EntitiesToMate = dispatch_array([a[0], b[0]])
        daten.GearRatioNumerator = mm(zaehler_mm)
        daten.GearRatioDenominator = mm(nenner_mm)
    else:
        waehle(asm, b, False, MARKE_ZAHNSTANGE)
        waehle(asm, a, True, MARKE_RITZEL)
        daten.DiameterType = SW_RITZEL_TEILKREIS
        daten.DiameterVal = mm(zaehler_mm)
    daten.Reverse = umkehren
    mate = asm.CreateMate(daten)
    sw.auswahl_leeren(asm)
    alle = verknuepfungen(asm)
    neu = alle[-1] if mate is not None and len(alle) > vorher else None
    try:
        if neu is None:
            raise BauFehler(VERKNUEPFUNG_FEHLER, "CreateMate legt keine Verknüpfung an", schritt="verknuepfung")
        neu.Name = v.id
        sw.rebuild(asm)
        if fc := fehlercode(neu):
            raise BauFehler(VERKNUEPFUNG_FEHLER, f"Fehlercode {fc}", schritt="verknuepfung")
    except Exception as e:
        if neu is not None:
            _loesche_still(asm, neu)
        meldung = str(e) if isinstance(e, BauFehler) else f"{type(e).__name__}: {e}"
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"{v.id} ({v.typ}): {meldung}", schritt="verknuepfung") from e
    return neu


def lies_kopplung(feature) -> dict:
    """Werte einer Zahnrad- bzw. Zahnstangenverknüpfung (IFeature.GetDefinition, mm; Spike S14b Zeile 6)."""
    d = feature.GetDefinition
    if int(feature.GetSpecificFeature2.Type) == MATE_KOPPLUNG["zahnrad"]:
        return {"zaehler": round(in_mm(d.GearRatioNumerator), 6), "nenner": round(in_mm(d.GearRatioDenominator), 6),
                "umkehren": bool(d.Reverse)}
    return {"durchmesser": round(in_mm(d.DiameterVal), 6), "art": int(d.DiameterType), "umkehren": bool(d.Reverse)}


def ist_unterdrueckt(feature) -> bool:
    return bool(feature.IsSuppressed)


def setze_lage(app, asm, komp, t: list[float]) -> None:
    """Lage einer Komponente setzen (SetTransformAndSolve2; die Verknüpfungen bleiben erfüllt) und neu aufbauen."""
    if not komp.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(t))):
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"{komp.Name2}: Lage ließ sich nicht setzen", schritt="zahnphase")
    sw.rebuild(asm)


def komponenten(asm) -> list:
```

In `swki/baugruppe/fehler.py` ersetzen:

```python
GRUNDSTELLUNG_FEHLER = "GRUNDSTELLUNG_FEHLER"  # Spec 4a §7.2/§10: eine Stellung ließ sich nicht herstellen
```

durch:

```python
GRUNDSTELLUNG_FEHLER = "GRUNDSTELLUNG_FEHLER"  # Spec 4a §7.2/§10: eine Stellung ließ sich nicht herstellen
ZAHNPHASE_FEHLER = "ZAHNPHASE_FEHLER"  # Spec 4b §5.4.2/§8: Zahn-in-Lücke nach dem Drehen nicht erreicht
```

In `swki/baugruppe/referenzen.py` ersetzen:

```python
from swki.compiler.topologie import flaechen, loese_flaeche, mit_abstand, referenz_geometrie
from swki.pruefung.geometrie import Messgeometrie
```

durch:

```python
from swki.compiler.topologie import flaechen, kante_aus, loese_flaeche, mit_abstand, referenz_geometrie
from swki.pruefung.geometrie import Messgeometrie
from swki.verzahnung import verzahnung_im_teil
```

In `swki/baugruppe/referenzen.py` ersetzen:

```python
def loese_im_teil(ctx, seite: dict) -> TeilReferenz:
```

durch:

```python
def kopplung_referenz(ctx, fid: str) -> TeilReferenz:
    """Entität einer Kopplungsseite im Teil (Spec 4b §5.4.3; Spike S14b Zeile 6): Stirnrad – koaxiale Zylinderfläche
    (wie die Radachse {feature, instanz: 1, achse: true}); Zahnstange – gerade Kante einer Kopffläche entlang der
    Zahnreihe."""
    f = next(x for x in ctx.spec["features"] if x["id"] == fid)
    if f["art"] == "stirnrad":
        return loese_im_teil(ctx, {"feature": fid, "instanz": 1, "achse": True})
    if fid not in ctx.ergebnisse:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Feature {fid!r} fehlt im Teil")
    vz = verzahnung_im_teil(f, ctx.spec.get("parameter", {}))
    for kopf in flaechen(ctx.ergebnis(fid).features[0]):
        if kopf.art != "ebene" or skalar(kopf.normale, vz.kopfrichtung) <= _PARALLEL:
            continue
        for e in kopf.objekt.GetEdges or ():
            k = kante_aus(e)
            if k.art == "linie" and abs(skalar(k.richtung, vz.u)) > _PARALLEL:
                return TeilReferenz(e, Messgeometrie("achse", k.start, vz.u), False)
    raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"{fid}: keine Kante entlang der Zahnreihe")


def loese_im_teil(ctx, seite: dict) -> TeilReferenz:
```

In `swki/baugruppe/bau.py` ersetzen:

```python
from swki.baugruppe.fehler import (GRUNDSTELLUNG_FEHLER, KOMPONENTE_FEHLER, SCHLIESSEN_FEHLER, TEIL_BAU,
                                   VERKNUEPFUNG_FEHLER)
```

durch:

```python
from swki.baugruppe.fehler import (GRUNDSTELLUNG_FEHLER, KOMPONENTE_FEHLER, SCHLIESSEN_FEHLER, TEIL_BAU,
                                   VERKNUEPFUNG_FEHLER, ZAHNPHASE_FEHLER)
```

In `swki/baugruppe/bau.py` ersetzen:

```python
from swki.baugruppe.freigabe import pruefe_freigabe_baugruppe
```

durch:

```python
from swki.baugruppe.freigabe import pruefe_freigabe_baugruppe
from swki.baugruppe.kopplung import (KOPPLUNGEN, drehe, in_baugruppe, phasenfehler, phasenwinkel, teilkreise,
                                     verzahnung_der_seite)
```

In `swki/baugruppe/bau.py` ersetzen:

```python
from swki.baugruppe.referenzen import loese_im_teil
```

durch:

```python
from swki.baugruppe.referenzen import kopplung_referenz, loese_im_teil
```

In `swki/baugruppe/bau.py` ersetzen:

```python
from swki.verbindung import verbinde
```

durch:

```python
from swki.verbindung import verbinde

TOL_PHASE = 1e-3  # Phasenfehler nach dem Drehen, Anteil der Teilung (Spec 4b §5.4.2)
```

In `swki/baugruppe/bau.py` ersetzen:

```python
def _verknuepfe(b: Baulauf, alle: list[Verknuepfung]) -> Exception | None:
    fehler = None
    for v in alle:
        if fehler is not None:
            b.protokoll.uebersprungen(v.id, v.typ)
            continue
        try:
            with b.protokoll.knoten_lauf(v.id, v.typ) as knoten:
                try:
                    feature = sw_baugruppe.verknuepfe(b.asm, v, _entitaet(b, v.a), _entitaet(b, v.b),
                                                      b.bg.spec.get("parameter", {}), b.gesetzt)
                    knoten.sw_name = feature.Name
```

durch:

```python
def _verzahnungen(b: Baulauf, v: Verknuepfung):
    """Beide Verzahnungen einer Kopplung in Baugruppenkoordinaten (aktuelle Lage der Komponenten)."""
    return tuple(in_baugruppe(verzahnung_der_seite(b.bg.quellen, s), sw_baugruppe.transform(b.komponenten[s["komponente"]]))
                 for s in (v.a, v.b))


def _zahnphase(b: Baulauf, v: Verknuepfung) -> None:
    """Seite a um ihre Achse drehen, bis Zahn in Lücke steht, und nachrechnen (Spec 4b §5.4.2, Knoten zahnphase:<id>)."""
    with b.protokoll.knoten_lauf(f"zahnphase:{v.id}", "zahnphase"):
        try:
            a, gegen = _verzahnungen(b, v)
            winkel = phasenwinkel(a, gegen)
            if abs(winkel) > 1e-9:
                komp = b.komponenten[v.a["komponente"]]
                sw_baugruppe.setze_lage(b.app, b.asm, komp, drehe(sw_baugruppe.transform(komp), a.punkt, a.achse, winkel))
                a, gegen = _verzahnungen(b, v)
            if abs(rest := phasenfehler(a, gegen)) > TOL_PHASE:
                raise BauFehler(ZAHNPHASE_FEHLER, f"Phase {rest * 360 / a.geo.z:+.4f}° statt 0 nach Drehung um "
                                                  f"{winkel:.4f}°", schritt="zahnphase")
        except Exception as e:
            raise _mit_kontext(e, ZAHNPHASE_FEHLER, f"Zahnphase {v.id}", "zahnphase") from e


def _entitaet_kopplung(b: Baulauf, seite: dict) -> tuple[object, bool]:
    try:
        ctx = b.kontexte[b.bg.quellen[basis(seite["komponente"])].schluessel_dokument]
        return sw_baugruppe.in_baugruppe(b.komponenten[seite["komponente"]], kopplung_referenz(ctx, seite["feature"]))
    except Exception as e:
        raise _mit_kontext(e, VERKNUEPFUNG_FEHLER, f"Komponente {seite['komponente']}", "referenz") from e


def _kopple(b: Baulauf, v: Verknuepfung):
    """Kopplung anlegen (Spec 4b §5.4.3): Übersetzung aus den Teilkreisen, Richtung nach sw_baugruppe.REVERSE."""
    a, gegen = (verzahnung_der_seite(b.bg.quellen, s).geo for s in (v.a, v.b))
    return sw_baugruppe.kopple(b.asm, v, _entitaet_kopplung(b, v.a), _entitaet_kopplung(b, v.b), *teilkreise(a, gegen),
                               sw_baugruppe.REVERSE[v.typ])


def _verknuepfe(b: Baulauf, alle: list[Verknuepfung]) -> Exception | None:
    fehler = None
    for v in alle:
        if fehler is not None:
            b.protokoll.uebersprungen(v.id, v.typ)
            continue
        try:
            if v.typ in KOPPLUNGEN:
                try:
                    _zahnphase(b, v)
                except Exception:
                    b.protokoll.uebersprungen(v.id, v.typ)
                    raise
            with b.protokoll.knoten_lauf(v.id, v.typ) as knoten:
                try:
                    if v.typ in KOPPLUNGEN:
                        feature = _kopple(b, v)
                    else:
                        feature = sw_baugruppe.verknuepfe(b.asm, v, _entitaet(b, v.a), _entitaet(b, v.b),
                                                          b.bg.spec.get("parameter", {}), b.gesetzt)
                    knoten.sw_name = feature.Name
```


- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_sw_kopplung.py` → `9 passed`. Ganze Suite → **818 passed,
127 deselected**; `pruefe-code` ohne Befund.

- [ ] **Step 5: Live-Bau der Getriebeprobe**

SolidWorks frisch (BLOCKED Neustart). Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py "tests\live\test_live_kopplung.py::test_getriebeprobe_bauen" --zeit 900`
Expected: `OK` (Knoten `zahnphase:k1`, `k1`, `zahnphase:k2`, `k2`, `grundstellung:Hub` ok). Danach Private Bytes notieren.

- [ ] **Step 6: Commit**

```powershell
git add swki/verbindung.py swki/baugruppe/sw_baugruppe.py swki/baugruppe/fehler.py swki/baugruppe/referenzen.py swki/baugruppe/bau.py tests/baugruppe/test_sw_kopplung.py tests/live/test_live_kopplung.py
git commit -m "baugruppe: Kopplungen bauen – Zahnphase, CreateMate, Rücklesen (Stufe 4b, Task 11)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Prüfen der Kopplungen – Eingriff, unterdrückte Verknüpfungen, Bilder, Bericht (ohne SolidWorks und live)

**Files:**
- Modify: `swki/baugruppe/bewertung.py`, `swki/baugruppe/pruefen.py`, `swki/baugruppe/bewegungslauf.py`,
  `swki/pruefung/bilder.py`, `swki/pruefung/bericht.py`, `tests/baugruppe/test_bewegungslauf.py`,
  `tests/live/test_live_kopplung.py`
- Test: `tests/baugruppe/test_eingriff.py` (neu)

**Interfaces:**
- Consumes: `kopplung` (`eingriff`, `in_baugruppe`, `kopplungen`, `teilkreise`, `verzahnung_der_seite`),
  `sw_baugruppe.lies_kopplung/ist_unterdrueckt`.
- Produces: `BaugruppenMesswerte.lagen`, `.kopplungen`, `.unterdrueckt`; `bewertung.TOL_UEBERSETZUNG`,
  `bewertung._eingriff(spec, quellen, m, tol_mm) -> (pruefungen, bericht)`; Prüfung `eingriff:<id>`; Prüfbericht
  `kopplungen`; `bilder.ANSICHT_DER_ACHSE`, `bilder.kopplungsbild(app, model, pfad, achse, komponenten)`;
  `pruefen._kopplungsbilder(...)` (Bilder `<id>-eingriff`); `bericht.md` Abschnitt „Kopplungen“.

- [ ] **Step 1: Tests schreiben bzw. anpassen**

`tests/baugruppe/test_eingriff.py` anlegen:

```python
"""Prüfung eingriff:<kopplung> und unterdrückte Verknüpfungen (Spec 4b §5.5), Kopplungen im Bericht – ohne SolidWorks."""

import pytest

from swki.baugruppe.bewertung import BaugruppenMesswerte, _eingriff, _verknuepfungen
from swki.pruefung.bericht import bericht_markdown
from tests.baugruppe.beispiel_kopplung import quellen, spec

EINS = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
GELESEN = {"k1": {"durchmesser": 40.0, "art": 0, "umkehren": False},
           "k2": {"zaehler": 100.0, "nenner": 50.0, "umkehren": False}}


def _lage(x, y, z=0.0) -> list[float]:
    return EINS[:9] + [x / 1000, y / 1000, z / 1000] + EINS[12:]


def _messwerte(lagen=None, gelesen=None, **weitere) -> BaugruppenMesswerte:
    lagen = {"zahnstange": _lage(0, 0, 10), "ritzelwelle": _lage(37.3, 20), "antriebswelle": _lage(112.3, 20)} | (lagen or {})
    return BaugruppenMesswerte(rebuild_fehler=[], verknuepfungen={}, komponenten={}, stueckliste={}, interferenzen=[],
                               box=[0.0] * 6, masse_kg=1.0, lagen=lagen,
                               kopplungen=GELESEN if gelesen is None else gelesen, **weitere)


def _pruefe(m) -> tuple[dict, list[dict]]:
    pruefungen, bericht = _eingriff(spec(), quellen(), m, 0.005)
    return {p["id"]: p for p in pruefungen}, bericht


def test_eingriff_in_ordnung():
    p, bericht = _pruefe(_messwerte())
    assert p["eingriff:k1"]["ok"] is True and p["eingriff:k2"]["ok"] is True
    assert p["eingriff:k1"]["ist"]["achsabstand"] == pytest.approx(20.0)
    assert [(b["kopplung"], b["soll"], b["achsabstand"], b["ueberdeckung"]) for b in bericht] == [
        ("k1", "Ø 40", 20.0, 10.0), ("k2", "100:50", 75.0, 10.0)]


def test_achsabstand_falsch():
    p, _ = _pruefe(_messwerte({"antriebswelle": _lage(112.4, 20)}))
    assert p["eingriff:k2"]["ok"] is False and p["eingriff:k2"]["knoten"] == ["k2"]
    assert "Achsabstand 75.1 statt 75 mm" in p["eingriff:k2"]["hinweis"]


def test_uebersetzung_und_teilkreis_falsch():
    gelesen = {"k1": {"durchmesser": 40.5, "art": 0, "umkehren": False},
               "k2": {"zaehler": 110.0, "nenner": 50.0, "umkehren": False}}
    p, _ = _pruefe(_messwerte(gelesen=gelesen))
    assert p["eingriff:k1"]["hinweis"] == "Teilkreis 40.5 statt 40 mm"
    assert p["eingriff:k2"]["hinweis"] == "Übersetzung 110:50 statt 100:50"


def test_fehlende_kopplung_meldet_nur_verknuepfungen():
    p, _ = _pruefe(_messwerte(gelesen={"k1": GELESEN["k1"]}))
    assert p["eingriff:k2"]["ok"] is True


def test_waelzpunkt_und_breite():
    p, _ = _pruefe(_messwerte({"ritzelwelle": _lage(300, 20), "antriebswelle": _lage(375, 20)}))
    assert p["eingriff:k1"]["hinweis"] == "Wälzpunkt außerhalb der Zahnstange" and p["eingriff:k2"]["ok"] is True
    p, _ = _pruefe(_messwerte({"zahnstange": _lage(0, 0, 30)}))
    assert p["eingriff:k1"]["hinweis"] == "Zahnbreiten überdecken sich nicht"


def test_komponente_fehlt():
    m = _messwerte()
    del m.lagen["antriebswelle"]
    p, _ = _pruefe(m)
    assert p["eingriff:k2"]["ok"] is False and p["eingriff:k2"]["hinweis"] == "Komponente fehlt in der Baugruppe"


def test_unterdrueckte_verknuepfung_ist_fehlerhaft():
    s = spec()
    m = _messwerte(unterdrueckt=["k2"])
    m.verknuepfungen = {v["id"]: 0 for v in s["verknuepfungen"]} | {"s1.anlage": 0, "s2.anlage": 0}
    e = _verknuepfungen(s, quellen(), m)
    assert e["ok"] is False and e["ist"]["fehlerhaft"] == {"k2": "unterdrückt"} and e["knoten"] == ["k2"]


def test_bericht_kopplungen():
    zeilen = [{"kopplung": "k1", "typ": "zahnstange", "a": "ritzelwelle", "b": "zahnstange", "soll": "Ø 40",
               "gelesen": GELESEN["k1"], "achsabstand": 20.0, "achsabstand_soll": 20.0, "ueberdeckung": 10.0},
              {"kopplung": "k2", "typ": "zahnrad", "a": "antriebswelle", "b": "ritzelwelle", "soll": "100:50",
               "gelesen": "Kopplung k2 nicht lesbar: x", "achsabstand": 75.0, "achsabstand_soll": 75.0, "ueberdeckung": 10.0}]
    text = bericht_markdown(spec(), "A", [], ("pruefen", "…"), {"maengel": [], "bilder": {}, "kopplungen": zeilen},
                            None, None, [])
    assert "## Kopplungen (letzter Lauf)" in text
    assert "| k1 | zahnstange | ritzelwelle → zahnstange | Ø 40 | Ø 40 | 20 / 20 | 10 |" in text
    assert "| k2 | zahnrad | antriebswelle → ritzelwelle | 100:50 | Kopplung k2 nicht lesbar: x | 75 / 75 | 10 |" in text
```

In `tests/baugruppe/test_bewegungslauf.py` ersetzen:

```python
    messwerte = statisch or SimpleNamespace(rebuild_fehler=[], verknuepfungen={"g1": 0, "g2": 0})
```

durch:

```python
    messwerte = statisch or SimpleNamespace(rebuild_fehler=[], verknuepfungen={"g1": 0, "g2": 0}, unterdrueckt=[])
```

In `tests/baugruppe/test_bewegungslauf.py` ersetzen:

```python
@pytest.mark.parametrize("statisch", [{"rebuild_fehler": ["Skizze1: Fehler"], "verknuepfungen": {"g1": 0}},
                                      {"rebuild_fehler": [], "verknuepfungen": {"g1": 0, "g2": 3}}])
```

durch:

```python
@pytest.mark.parametrize("statisch", [{"rebuild_fehler": ["Skizze1: Fehler"], "verknuepfungen": {"g1": 0}, "unterdrueckt": []},
                                      {"rebuild_fehler": [], "verknuepfungen": {"g1": 0, "g2": 3}, "unterdrueckt": []},
                                      {"rebuild_fehler": [], "verknuepfungen": {"g1": 0, "g2": 0}, "unterdrueckt": ["g2"]}])
```

In `tests/live/test_live_kopplung.py` ersetzen:

```python
    assert all(knoten[k] == "ok" for k in ("zahnphase:k1", "k1", "zahnphase:k2", "k2", "grundstellung:Hub")), knoten
```

durch:

```python
    assert all(knoten[k] == "ok" for k in ("zahnphase:k1", "k1", "zahnphase:k2", "k2", "grundstellung:Hub")), knoten


def test_getriebeprobe_besteht_pruefung(capsys, probe):
    _baue(capsys, probe)
    code, bericht = _lauf(capsys, "pruefen", str(probe))
    assert code == 0 and bericht["maengel"] == [], json.dumps(bericht["maengel"], indent=1, ensure_ascii=False)
    p = {x["id"]: x for x in bericht["pruefungen"]}
    for pid in ("eingriff:k1", "eingriff:k2", "freiheitsgrad:zahnstange", "freiheitsgrad:ritzelwelle",
                "freiheitsgrad:antriebswelle", "sollweg:Hub:zahnstange", "sollweg:Hub:ritzelwelle",
                "sollweg:Hub:antriebswelle", "endlage:Hub:ritzelwelle", "endlage:Hub:antriebswelle", "kollision"):
        assert p[pid]["ok"] is True, p[pid]
    assert p["endlage:Hub:ritzelwelle"]["ist"]["aufsummiert"] == pytest.approx(60 * 360 / (3.141592653589793 * 40), abs=0.01)
    assert {"k1-eingriff", "k2-eingriff"} <= set(bericht["bilder"])
    assert all(Path(x).stat().st_size > 0 for x in bericht["bilder"].values())
    assert [k["kopplung"] for k in bericht["kopplungen"]] == ["k1", "k2"]
```


- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_eingriff.py tests\baugruppe\test_bewegungslauf.py`
Expected: FAIL – `1 error` beim Sammeln (`ImportError: cannot import name '_eingriff'`).

- [ ] **Step 3: Umsetzen**

In `swki/baugruppe/bewertung.py` ersetzen:

```python
from swki.baugruppe.geometrie import einschraublaenge, ueberlappung_soll
```

durch:

```python
from swki.baugruppe.geometrie import einschraublaenge, ueberlappung_soll
from swki.baugruppe.kopplung import eingriff, in_baugruppe, kopplungen, teilkreise, verzahnung_der_seite
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python
_TOL_HUELLQUADER = 0.01
```

durch:

```python
TOL_UEBERSETZUNG = 1e-6  # relativ, zurückgelesene Übersetzung (Spec 4b §5.5)
_TOL_HUELLQUADER = 0.01
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python
    teilberichte: dict[str, dict] = field(default_factory=dict)
```

durch:

```python
    teilberichte: dict[str, dict] = field(default_factory=dict)
    lagen: dict[str, list[float]] = field(default_factory=dict)       # Instanz-ID → Transform2.ArrayData (Spec 4b §5.5)
    kopplungen: dict[str, dict | str] = field(default_factory=dict)   # Kopplungs-ID → gelesene Werte oder Fehlertext
    unterdrueckt: list[str] = field(default_factory=list)             # unterdrückte Verknüpfungen (Spec 4b §5.5)
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python
    fehlerhaft = {n: c for n, c in m.verknuepfungen.items() if c}
```

durch:

```python
    fehlerhaft = {n: c for n, c in m.verknuepfungen.items() if c} | {n: "unterdrückt" for n in m.unterdrueckt}
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python
def _masse_pruefen(pr: dict, p: dict, m: BaugruppenMesswerte) -> list[dict]:
```

durch:

```python
def _eingriff(spec: dict, quellen: dict[str, Quelle], m: BaugruppenMesswerte, tol_mm: float) -> tuple[list[dict], list[dict]]:
    """Spec 4b §5.5: je Kopplung eingriff:<id> – Achslage, Achsabstand, Breitenüberdeckung, Wälzpunkt auf der Zahnstange
    und die zurückgelesene Übersetzung bzw. der Teilkreis. Fehlt die Kopplung im Modell, meldet das verknuepfungen;
    hier zählt dann nur die Geometrie. Dazu je Kopplung eine Zeile für den Prüfbericht."""
    pruefungen, bericht = [], []
    for v in kopplungen(spec):
        pid, ka, kb = f"eingriff:{v['id']}", v["a"]["komponente"], v["b"]["komponente"]
        if ka not in m.lagen or kb not in m.lagen:
            pruefungen.append(eintrag(pid, False, hinweis="Komponente fehlt in der Baugruppe", knoten=[v["id"]]))
            continue
        a = in_baugruppe(verzahnung_der_seite(quellen, v["a"]), m.lagen[ka])
        b = in_baugruppe(verzahnung_der_seite(quellen, v["b"]), m.lagen[kb])
        ist = eingriff(a, b)
        gruende = []
        if not ist["achsen_parallel"]:
            gruende.append("Achsen nicht parallel" if v["typ"] == "zahnrad" else "Radachse nicht senkrecht zur Zahnstange")
        if abs(ist["achsabstand"] - ist["soll"]) > tol_mm:
            gruende.append(f"Achsabstand {ist['achsabstand']:g} statt {ist['soll']:g} mm")
        if ist["ueberdeckung"] <= 0:
            gruende.append("Zahnbreiten überdecken sich nicht")
        if not ist["im_bereich"]:
            gruende.append("Wälzpunkt außerhalb der Zahnstange")
        zaehler, nenner = teilkreise(a.geo, b.geo)
        gelesen = m.kopplungen.get(v["id"])
        if isinstance(gelesen, str):
            gruende.append(gelesen)
        elif isinstance(gelesen, dict) and v["typ"] == "zahnrad":
            soll_u, ist_u = zaehler / nenner, gelesen["zaehler"] / gelesen["nenner"]
            if abs(ist_u - soll_u) > TOL_UEBERSETZUNG * soll_u:
                gruende.append(f"Übersetzung {gelesen['zaehler']:g}:{gelesen['nenner']:g} statt {zaehler:g}:{nenner:g}")
        elif isinstance(gelesen, dict) and abs(gelesen["durchmesser"] - zaehler) > tol_mm:
            gruende.append(f"Teilkreis {gelesen['durchmesser']:g} statt {zaehler:g} mm")
        pruefungen.append(eintrag(pid, not gruende, ist={**ist, "kopplung": gelesen}, knoten=[v["id"]] if gruende else [],
                                  **({"hinweis": "; ".join(gruende)} if gruende else {})))
        bericht.append({"kopplung": v["id"], "typ": v["typ"], "a": ka, "b": kb,
                        "soll": f"{zaehler:g}:{nenner:g}" if v["typ"] == "zahnrad" else f"Ø {zaehler:g}",
                        "gelesen": gelesen, "achsabstand": ist["achsabstand"], "achsabstand_soll": ist["soll"],
                        "ueberdeckung": ist["ueberdeckung"]})
    return pruefungen, bericht


def _masse_pruefen(pr: dict, p: dict, m: BaugruppenMesswerte) -> list[dict]:
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python
    ergebnisse.append(eintrag("kollision", not kollisionen, ist=kollisionen,
                                knoten=sorted({k for i in kollisionen for k in i["paar"]})))
```

durch:

```python
    ergebnisse.append(eintrag("kollision", not kollisionen, ist=kollisionen,
                                knoten=sorted({k for i in kollisionen for k in i["paar"]})))
    eingriffe, kopplungsbericht = (_eingriff(spec, quellen, m, standard["toleranzen"]["verzahnung_mm"])
                                   if kopplungen(spec) else ([], []))
    ergebnisse += eingriffe
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python
    return {"bestanden": not maengel, "pruefungen": ergebnisse, "maengel": maengel, "stueckliste": m.stueckliste,
            "gewindepaarungen": gewinde_bericht, "teilpruefungen": teilpruefungen, "masse_kg": round(m.masse_kg, 4)}
```

durch:

```python
    return {"bestanden": not maengel, "pruefungen": ergebnisse, "maengel": maengel, "stueckliste": m.stueckliste,
            "gewindepaarungen": gewinde_bericht, "teilpruefungen": teilpruefungen, "masse_kg": round(m.masse_kg, 4),
            **({"kopplungen": kopplungsbericht} if kopplungsbericht else {})}
```

In `swki/baugruppe/bewegungslauf.py` ersetzen:

```python
def _statisch_fehlerhaft(messwerte) -> bool:
    """Rebuildfehler oder eine Verknüpfung mit Fehlercode ≠ 0 in den statischen Messwerten (die Felder, aus denen die
    Mängel rebuild und verknuepfungen entstehen)."""
    return bool(messwerte.rebuild_fehler) or any(messwerte.verknuepfungen.values())
```

durch:

```python
def _statisch_fehlerhaft(messwerte) -> bool:
    """Rebuildfehler, eine Verknüpfung mit Fehlercode ≠ 0 oder eine unterdrückte Verknüpfung in den statischen
    Messwerten (die Felder, aus denen die Mängel rebuild und verknuepfungen entstehen)."""
    return bool(messwerte.rebuild_fehler) or any(messwerte.verknuepfungen.values()) or bool(messwerte.unterdrueckt)
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
from swki.baugruppe.geometrie import transformiere
```

durch:

```python
from swki.baugruppe.geometrie import transformiere
from swki.baugruppe.kopplung import in_baugruppe, kopplungen, verzahnung_der_seite
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
from swki.pruefung.bilder import screenshots
```

durch:

```python
from swki.pruefung.bilder import kopplungsbild, screenshots
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
    interferenzen = [{"paar": sorted(namen.get(n, n) for n in paar), "volumen": volumen}
                     for paar, volumen in sw_baugruppe.interferenzen(asm)]
```

durch:

```python
    interferenzen = [{"paar": sorted(namen.get(n, n) for n in paar), "volumen": volumen}
                     for paar, volumen in sw_baugruppe.interferenzen(asm)]
    mates = sw_baugruppe.verknuepfungen(asm)
    ids = {v["id"] for v in kopplungen(bg.spec)}
    gelesen: dict[str, dict | str] = {}
    for f in mates:
        if f.Name in ids:
            try:
                gelesen[f.Name] = sw_baugruppe.lies_kopplung(f)
            except Exception as e:  # COM-Fehler beim Lesen → Mangel statt Abbruch der Prüfung
                gelesen[f.Name] = f"Kopplung {f.Name} nicht lesbar: {e}"
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
        verknuepfungen={f.Name: sw_baugruppe.fehlercode(f) for f in sw_baugruppe.verknuepfungen(asm)},
```

durch:

```python
        verknuepfungen={f.Name: sw_baugruppe.fehlercode(f) for f in mates},
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
        messpunkte=messpunkte, schrauben=schrauben, gewindebohrungen=bohrungen, teilberichte=teilberichte)
```

durch:

```python
        messpunkte=messpunkte, schrauben=schrauben, gewindebohrungen=bohrungen, teilberichte=teilberichte,
        lagen=transformationen, kopplungen=gelesen, unterdrueckt=[f.Name for f in mates if sw_baugruppe.ist_unterdrueckt(f)])


def _kopplungsbilder(app, asm, bg: Baugruppe, protokoll: dict, messwerte: BaugruppenMesswerte, ordner: Path) -> dict:
    """Je Kopplung ein Bild entlang der Radachse von Seite a, gezoomt auf beide Komponenten (Spec 4b §5.7)."""
    komponenten = _komponenten(asm, protokoll)
    bilder = {}
    for v in kopplungen(bg.spec):
        ka, kb = v["a"]["komponente"], v["b"]["komponente"]
        if ka not in komponenten or kb not in komponenten:
            continue
        achse = in_baugruppe(verzahnung_der_seite(bg.quellen, v["a"]), messwerte.lagen[ka]).achse
        name = f"{v['id']}-eingriff"
        bilder[name] = kopplungsbild(app, asm, ordner / f"{name}.png", achse, [komponenten[ka], komponenten[kb]])
    return bilder
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
            bilder = screenshots(app, asm, ordner / "bilder")
```

durch:

```python
            bilder = screenshots(app, asm, ordner / "bilder")
            bilder |= _kopplungsbilder(app, asm, bg, protokoll, messwerte, ordner / "bilder")
```

In `swki/pruefung/bilder.py` ersetzen:

```python
def iso_bild(app, model, pfad: Path) -> str:
```

durch:

```python
ANSICHT_DER_ACHSE = {0: "rechts", 1: "oben", 2: "vorne"}  # Blick entlang x, y bzw. z


def kopplungsbild(app, model, pfad: Path, achse, komponenten: list) -> str:
    """Bild entlang einer Radachse (Standardansicht der größten Achskomponente), gezoomt auf die gekoppelten Komponenten
    (Spec 4b §5.7, Spike S14b Zeile 12); sonst wie screenshots()."""
    model._FlagAsMethod("ViewZoomToSelection")
    with sw.einstellung_int(app, SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0):
        model.ShowNamedView2("", ANSICHTEN[ANSICHT_DER_ACHSE[max(range(3), key=lambda i: abs(achse[i]))]])
        sw.auswahl_leeren(model)
        for komp in komponenten:
            komp.Select4(True, model.SelectionManager.CreateSelectData, False)
        model.ViewZoomToSelection()
        sw.auswahl_leeren(model)
        sw.speichere(model, pfad, kopie=True)
    return str(pfad)


def iso_bild(app, model, pfad: Path) -> str:
```

In `swki/pruefung/bericht.py` ersetzen:

```python
    bewegungen = letzter.get("bewegungen")
```

durch:

```python
    if letzter.get("kopplungen"):
        zeilen += ["", "## Kopplungen (letzter Lauf)", "",
                   "| Kopplung | Typ | a → b | Übersetzung soll | gelesen | Achsabstand ist / soll (mm) | Überdeckung (mm) |",
                   "|---|---|---|---|---|---|---|"]
        for k in letzter["kopplungen"]:
            g = k["gelesen"]
            gelesen = (f"{g['zaehler']:g}:{g['nenner']:g}" if "zaehler" in g else f"Ø {g['durchmesser']:g}"
                       ) if isinstance(g, dict) else _zelle(g)
            zeilen.append(f"| {k['kopplung']} | {k['typ']} | {k['a']} → {k['b']} | {k['soll']} | {gelesen} | "
                          f"{k['achsabstand']:g} / {k['achsabstand_soll']:g} | {k['ueberdeckung']:g} |")
    bewegungen = letzter.get("bewegungen")
```


- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: wie Step 2 → `24 passed`. Ganze Suite → **827 passed, 128 deselected**; `pruefe-code` ohne Befund.

- [ ] **Step 5: Live-Prüfung der Getriebeprobe**

SolidWorks frisch. Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py "tests\live\test_live_kopplung.py::test_getriebeprobe_besteht_pruefung" --zeit 900`
Expected: `OK` (keine Mängel, Eingriff/Sollweg/Freiheitsgrade/Endlagen ok, Bilder `k1-eingriff`, `k2-eingriff`). Dauer,
Private Bytes vorher → Spitze (0,5-s-Abtastung) → nachher notieren.

- [ ] **Step 6: Commit**

```powershell
git add swki/baugruppe/bewertung.py swki/baugruppe/pruefen.py swki/baugruppe/bewegungslauf.py swki/pruefung/bilder.py swki/pruefung/bericht.py tests/baugruppe/test_eingriff.py tests/baugruppe/test_bewegungslauf.py tests/live/test_live_kopplung.py
git commit -m "pruefen: Eingriff je Kopplung, unterdrückte Verknüpfungen, Bilder, Bericht (Stufe 4b, Task 12)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Referenz Zahnstangentrieb mit Prüfer-Urteil (live)

**Files:**
- Create: `tests/referenz/zahnstangentrieb/zahnstangentrieb.yaml`
- Modify: `tests/referenz/test_referenzen.py`, `.claude/agents/pruefer.md`

**Interfaces:**
- Consumes: Tasks 6 (Teil-Specs, Eingabe) und 7–12.
- Produces: Referenzeintrag `zahnstangentrieb-zahnstangentrieb.yaml`; Prüfer-Checkliste „Kopplungen“.

- [ ] **Step 1: Referenz und Prüfer-Checkliste**

In `tests/referenz/test_referenzen.py` ersetzen:

```python
    ("zahnstangentrieb", "antriebswelle.yaml"),
])
```

durch:

```python
    ("zahnstangentrieb", "antriebswelle.yaml"),
    ("zahnstangentrieb", "zahnstangentrieb.yaml"),
])
```


`tests/referenz/zahnstangentrieb/zahnstangentrieb.yaml` anlegen:

```yaml
# Referenz Zahnstangentrieb (Spec 4b §2, §12): Linearschlitten aus 4a ohne Hebel. Grundplatte (fixiert), zwei verschraubte
# Führungsleisten, Schlitten mit Abstandsgrenze 0 … HUB. Auf dem Schlitten die Zahnstange (m 2, 30 Zähne), von unten mit
# 2 × ISO 4762 M5 × 25 verschraubt (Gruppe schieber). Auf jeder Leiste ein Lagerbock; darin die Ritzelwelle (Ritzel
# z = 20 über der Zahnstange, Rad z = 25) und darüber die Antriebswelle (Rad z = 50), Achsabstand 75.
# Grundstellung: Schlitten am Ende −x. Fährt der Schlitten nach +x, dreht das Ritzel um +z und die Antriebswelle um −z.
art: baugruppe
name: Zahnstangentrieb
eigenschaften: {Benennung: Zahnstangentrieb}
parameter: {HUB: 120}
komponenten:
  - {id: grundplatte, quelle: {teil: grundplatte.yaml}, fixiert: true}
  - {id: leiste_links, quelle: {teil: leiste.yaml}}
  - {id: leiste_rechts, quelle: {teil: leiste.yaml}}
  - {id: schraube_links, quelle: {normteil: "ISO 4762 M8x25"}, je_position: {komponente: leiste_links, feature: f2}}
  - {id: schraube_rechts, quelle: {normteil: "ISO 4762 M8x25"}, je_position: {komponente: leiste_rechts, feature: f2}}
  - {id: schlitten, quelle: {teil: schlitten.yaml}, gruppe: schieber}
  - {id: zahnstange, quelle: {teil: zahnstange.yaml}, gruppe: schieber}
  - {id: stangenschraube, quelle: {normteil: "ISO 4762 M5x25"}, je_position: {komponente: schlitten, feature: f2}}
  - {id: lagerbock_links, quelle: {teil: lagerbock.yaml}}
  - {id: lagerbock_rechts, quelle: {teil: lagerbock.yaml}}
  - {id: ritzelwelle, quelle: {teil: ritzelwelle.yaml}}
  - {id: antriebswelle, quelle: {teil: antriebswelle.yaml}}
verknuepfungen:
  # Führungsleisten bündig an den Enden und Außenseiten der Grundplatte, verschraubt (wie 4a)
  - {id: v1, typ: deckungsgleich, a: {komponente: leiste_links, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v2, typ: deckungsgleich, a: {komponente: leiste_links, feature: f1, flaeche: "-x"},
     b: {komponente: grundplatte, feature: f1, flaeche: "-x"}, ausrichtung: gleich}
  - {id: v3, typ: deckungsgleich, a: {komponente: leiste_links, feature: f1, flaeche: "-z"},
     b: {komponente: grundplatte, feature: f1, flaeche: "-z"}, ausrichtung: gleich}
  - {id: v4, typ: deckungsgleich, a: {komponente: leiste_rechts, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v5, typ: deckungsgleich, a: {komponente: leiste_rechts, feature: f1, flaeche: "-x"},
     b: {komponente: grundplatte, feature: f1, flaeche: "-x"}, ausrichtung: gleich}
  - {id: v6, typ: deckungsgleich, a: {komponente: leiste_rechts, feature: f1, flaeche: "+z"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+z"}, ausrichtung: gleich}
  - {id: v10, typ: deckungsgleich, a: {komponente: schraube_links, referenz: EINBAU_EBENE},
     b: {komponente: leiste_links, feature: f2, instanz: je, flaeche: "+y"}, ausrichtung: gleich}
  - {id: v11, typ: konzentrisch, a: {komponente: schraube_links, referenz: EINBAU_ACHSE},
     b: {komponente: leiste_links, feature: f2, instanz: je, achse: true}}
  - {id: v12, typ: deckungsgleich, a: {komponente: schraube_rechts, referenz: EINBAU_EBENE},
     b: {komponente: leiste_rechts, feature: f2, instanz: je, flaeche: "+y"}, ausrichtung: gleich}
  - {id: v13, typ: konzentrisch, a: {komponente: schraube_rechts, referenz: EINBAU_ACHSE},
     b: {komponente: leiste_rechts, feature: f2, instanz: je, achse: true}}
  # Schlitten: auf der Grundplatte, seitlich an der linken Leiste; Hub über die Grenze g1
  - {id: v20, typ: deckungsgleich, a: {komponente: schlitten, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v21, typ: deckungsgleich, a: {komponente: schlitten, feature: f1, flaeche: "-z"},
     b: {komponente: leiste_links, feature: f1, flaeche: "+z"}, ausrichtung: entgegengesetzt}
  - {id: g1, typ: grenze_abstand, a: {komponente: schlitten, feature: f1, flaeche: "-x"},
     b: {komponente: grundplatte, feature: f1, flaeche: "-x"}, ausrichtung: gleich, min: 0, max: "=HUB"}
  # Zahnstange auf dem Schlitten: Rücken auf der Oberseite, Gewinde 1 über Senkung 1, Seiten parallel; Schrauben von unten
  - {id: v30, typ: deckungsgleich, a: {komponente: zahnstange, feature: f1, flaeche: "-y"},
     b: {komponente: schlitten, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v31, typ: konzentrisch, a: {komponente: zahnstange, feature: f2, instanz: 1, achse: true},
     b: {komponente: schlitten, feature: f2, instanz: 1, achse: true}}
  - {id: v32, typ: parallel, a: {komponente: zahnstange, feature: f1, flaeche: "-z"},
     b: {komponente: schlitten, feature: f1, flaeche: "-z"}, ausrichtung: gleich}
  - {id: v33, typ: deckungsgleich, a: {komponente: stangenschraube, referenz: EINBAU_EBENE},
     b: {komponente: schlitten, feature: f2, instanz: je, flaeche: "-y"}, ausrichtung: gleich}
  - {id: v34, typ: konzentrisch, a: {komponente: stangenschraube, referenz: EINBAU_ACHSE},
     b: {komponente: schlitten, feature: f2, instanz: je, achse: true}}
  # Lagerböcke auf den Leisten, in der Mitte der Grundplatte (x = 0), bündig mit den Außenseiten der Leisten
  - {id: v40, typ: deckungsgleich, a: {komponente: lagerbock_links, feature: f1, flaeche: "-y"},
     b: {komponente: leiste_links, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v41, typ: deckungsgleich, a: {komponente: lagerbock_links, ebene: rechts},
     b: {komponente: grundplatte, ebene: rechts}, ausrichtung: gleich}
  - {id: v42, typ: deckungsgleich, a: {komponente: lagerbock_links, feature: f1, flaeche: "-z"},
     b: {komponente: leiste_links, feature: f1, flaeche: "-z"}, ausrichtung: gleich}
  - {id: v43, typ: deckungsgleich, a: {komponente: lagerbock_rechts, feature: f1, flaeche: "-y"},
     b: {komponente: leiste_rechts, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v44, typ: deckungsgleich, a: {komponente: lagerbock_rechts, ebene: rechts},
     b: {komponente: grundplatte, ebene: rechts}, ausrichtung: gleich}
  - {id: v45, typ: deckungsgleich, a: {komponente: lagerbock_rechts, feature: f1, flaeche: "+z"},
     b: {komponente: leiste_rechts, feature: f1, flaeche: "+z"}, ausrichtung: gleich}
  # Wellen drehbar in den Lagerbohrungen des rechten Lagerbocks; die Räder liegen an dessen Innenseite an
  - {id: s1, typ: scharnier, a: {komponente: ritzelwelle, referenz: ACHSE},
     b: {komponente: lagerbock_rechts, feature: f2, instanz: 1, achse: true},
     anlage_a: {komponente: ritzelwelle, feature: z2, flaeche: "+z"},
     anlage_b: {komponente: lagerbock_rechts, feature: f1, flaeche: "-z"}}
  - {id: s2, typ: scharnier, a: {komponente: antriebswelle, referenz: ACHSE},
     b: {komponente: lagerbock_rechts, feature: f2, instanz: 2, achse: true},
     anlage_a: {komponente: antriebswelle, feature: z1, flaeche: "+z"},
     anlage_b: {komponente: lagerbock_rechts, feature: f1, flaeche: "-z"}}
  # Kopplungen zuletzt: Ritzel ↔ Zahnstange, dann Antriebsrad ↔ Rad der Ritzelwelle (Seite a wird in Phase gedreht)
  - {id: k1, typ: zahnstange, a: {komponente: ritzelwelle, feature: z1}, b: {komponente: zahnstange, feature: z1}}
  - {id: k2, typ: zahnrad, a: {komponente: antriebswelle, feature: z1}, b: {komponente: ritzelwelle, feature: z2}}
freiheitsgrade: {schieber: 1, ritzelwelle: gekoppelt, antriebswelle: gekoppelt}
bewegungen:
  - name: Schlittenhub
    grenze: g1
    erwartet:
      endlagen:
        - {komponente: schlitten, verschiebung: ["=HUB", 0, 0]}
        - {komponente: zahnstange, verschiebung: ["=HUB", 0, 0]}
        # Ritzel: Teilkreis-Ø m·z = 40, die Zahnstange (Wälzpunkt unter der Achse) fährt nach +x → Drehung um +z
        - {komponente: ritzelwelle, drehung: {achse: [0, 0, 1], winkel: "=HUB*360/(pi*40)"}}
        # Antriebswelle: gegensinnig, Übersetzung z2/z1 = 25/50
        - {komponente: antriebswelle, drehung: {achse: [0, 0, -1], winkel: "=HUB*360/(pi*40)*25/50"}}
pruefung:
  huellquader: [300, 210, 120]
  masse_pruefen:
    - {was: Achsabstand der Wellen, von: {komponente: ritzelwelle, referenz: ACHSE},
       zu: {komponente: antriebswelle, referenz: ACHSE}, soll: 75}
    - {was: Ritzelachse über der Grundplatte, von: {komponente: grundplatte, feature: f1, flaeche: "-y"},
       zu: {komponente: ritzelwelle, referenz: ACHSE}, soll: 77.5}
```

In `.claude/agents/pruefer.md` ersetzen:

```markdown
## Antwort (genau dieses JSON, sonst nichts)
```

durch:

```markdown
## Zusätzlich bei Kopplungen (`zahnrad`, `zahnstange` in der Baugruppe)

- Bilder `<kopplung>-eingriff` (Blick entlang der Radachse): Zahn steht in Lücke, keine sichtbare Durchdringung; das
  Ritzel greift in die Zahnstange, die Räder greifen ineinander.
- Drehrichtungen plausibel (Bilder `<Bewegung>-min|mitte|max`): Außenräder drehen gegensinnig; das Ritzel rollt auf der
  Zahnstange ab (Fahrrichtung und Drehsinn passen zusammen).
- Die Zahnstange überdeckt das Ritzel über den ganzen Hub (Bilder `min` und `max`).
- `eingriff:*` (Achsabstand, Überdeckung, Übersetzung), `sollweg:*` und `freiheitsgrad:*` (auch der gekoppelten
  Wellen) sind ok; sie stehen sonst schon als Mängel im Prüfbericht.

## Antwort (genau dieses JSON, sonst nichts)
```


- [ ] **Step 2: Validieren und Suite**

`.venv\Scripts\python.exe -m swki validieren tests\referenz\zahnstangentrieb\zahnstangentrieb.yaml` → `"gueltig": true`,
`"hinweise": []` (vorab geprüft). Ganze Suite → **827 passed, 129 deselected**.

- [ ] **Step 3: Referenz live**

SolidWorks frisch. Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py "tests\referenz\test_referenzen.py::test_referenz_besteht[zahnstangentrieb-zahnstangentrieb.yaml]" --zeit 900`
Expected: `OK`. Ein Mangel heißt: Bauweg nachbessern (Verknüpfungen, Reihenfolge, Referenzen), nie Parameter, Teil-Anforderungen,
`freiheitsgrade`, `bewegungen` oder `pruefung` – hält der Implementer eine Anforderung für falsch, NEEDS_CONTEXT. Dauer und
Private Bytes (0,5-s-Abtastung) notieren; `SPEICHER_KNAPP` → BLOCKED (Neustart, Controller), erneut; scheitert es auch
frisch: NEEDS_CONTEXT (Controller fragt den Nutzer, keine stille Anhebung der Grenze).

- [ ] **Step 4: Prüfer-Urteil (Controller)**

Lauf in `auftraege/REF-4B-TRIEB/` (Kopie des Referenzordners, `validieren`, `freigeben`, `bauen`, `pruefen` auf frischem
SolidWorks), BLOCKED (Prüfer). Der Controller startet den Prüfer-Agenten mit Eingabe, allen freigegebenen Specs (Baugruppe und
Teile), Prüfbericht und Bildern; Urteil unverändert nach `protokolle/zahnstangentrieb.lauf-<n>.pruefer.json`; `swki status`
→ bestanden. Mängel des Prüfers: Bauweg nachbessern, neuer Lauf. Auftrag danach löschen.

- [ ] **Step 5: Commit**

```powershell
git add tests/referenz/zahnstangentrieb/zahnstangentrieb.yaml tests/referenz/test_referenzen.py .claude/agents/pruefer.md
git commit -m "referenz: Zahnstangentrieb mit Kopplungen, Prüfer-Checkliste Kopplungen (Stufe 4b, Task 13)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Negativfälle am Zahnstangentrieb (live)

**Files:**
- Test: `tests/live/test_live_zahnstangentrieb.py` (neu)

**Interfaces:**
- Consumes: Referenz (Task 13); monkeypatch auf `swki.baugruppe.bau.phasenwinkel`, `bau.TOL_PHASE`,
  `sw_baugruppe.REVERSE`, `bau.verknuepfungen`, `bau.teilkreise`.
- Produces: vier Live-Negativfälle.

- [ ] **Step 1: Tests schreiben**

`tests/live/test_live_zahnstangentrieb.py` anlegen:

```python
"""Live: Negativfälle am Zahnstangentrieb (Spec 4b §10) – Zahnphase versetzt, Drehrichtung umgekehrt, Kopplung fehlt,
Übersetzung verfälscht. Jeder Fall verfälscht nur den Bau (monkeypatch), die Spec bleibt gültig und unverändert; jeder
Fall liefert genau seine Mängelmenge. Je Fall frisches SolidWorks (Controller)."""

import json
import shutil
from pathlib import Path

import pytest

from swki.baugruppe import bau, sw_baugruppe
from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-TRIEB"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "zahnstangentrieb"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def spec(tmp_path):
    ordner = tmp_path / AUFTRAG
    shutil.copytree(REFERENZ, ordner)
    yield ordner / "zahnstangentrieb.yaml"
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _maengel(capsys, spec: Path) -> tuple[dict, dict]:
    assert _lauf(capsys, "validieren", str(spec))[0] == 0
    assert _lauf(capsys, "freigeben", str(spec))[0] == 0
    code, ergebnis = _lauf(capsys, "bauen", str(spec))
    assert code == 0, ergebnis
    code, bericht = _lauf(capsys, "pruefen", str(spec))
    assert code in (0, 1) and "maengel" in bericht, bericht
    assert bericht["bestanden"] is False, bericht
    return {m["pruefung"]: m for m in bericht["maengel"]}, bericht


def test_zahnphase_versetzt(capsys, spec, monkeypatch):
    # Die Antriebswelle (z 50) wird um eine halbe Teilung zu weit gedreht und die Phasenprüfung des Baus abgeschaltet:
    # Zahn auf Zahn schon in Grundstellung (statische Kollision); die Bewegung meldet dasselbe Paar nicht noch einmal
    original = bau.phasenwinkel
    monkeypatch.setattr(bau, "phasenwinkel", lambda a, b: original(a, b) + (180 / a.geo.z if a.geo.z == 50 else 0.0))
    monkeypatch.setattr(bau, "TOL_PHASE", 1.0)
    maengel, _ = _maengel(capsys, spec)
    assert set(maengel) == {"kollision"}, maengel
    assert set(maengel["kollision"]["knoten"]) == {"antriebswelle", "ritzelwelle"}, maengel


def test_drehrichtung_umgekehrt(capsys, spec, monkeypatch):
    # Zahnradverknüpfung mit umgekehrtem Reverse: die Antriebswelle dreht falsch herum, die Zähne laufen aufeinander
    monkeypatch.setitem(sw_baugruppe.REVERSE, "zahnrad", not sw_baugruppe.REVERSE["zahnrad"])
    maengel, _ = _maengel(capsys, spec)
    assert set(maengel) == {"bewegung_kollision:Schlittenhub", "sollweg:Schlittenhub:antriebswelle",
                            "endlage:Schlittenhub:antriebswelle"}, maengel


def test_kopplung_fehlt(capsys, spec, monkeypatch):
    # k2 wird beim Bau nicht angelegt: die statische Prüfung meldet sie als fehlend, die Bewegungsprüfung läuft nicht
    original = bau.verknuepfungen
    monkeypatch.setattr(bau, "verknuepfungen", lambda s, q: [v for v in original(s, q) if v.id != "k2"])
    maengel, bericht = _maengel(capsys, spec)
    assert set(maengel) == {"verknuepfungen"}, maengel
    assert maengel["verknuepfungen"]["knoten"] == ["k2"]
    assert next(p for p in bericht["pruefungen"] if p["id"] == "bewegung:Schlittenhub")["ok"] is None


def test_uebersetzung_verfaelscht(capsys, spec, monkeypatch):
    # Zähler der Zahnradverknüpfung um 10 % zu groß: die Antriebswelle dreht 156° statt 172°, die Zähne laufen
    # innerhalb des Hubs aufeinander; das Rücklesen zeigt die falsche Übersetzung
    original = bau.teilkreise
    monkeypatch.setattr(bau, "teilkreise", lambda a, b: (lambda z, n: (z * 1.1, n) if n else (z, n))(*original(a, b)))
    maengel, _ = _maengel(capsys, spec)
    assert set(maengel) == {"eingriff:k2", "sollweg:Schlittenhub:antriebswelle", "endlage:Schlittenhub:antriebswelle",
                            "bewegung_kollision:Schlittenhub"}, maengel
```


- [ ] **Step 2: Sammeln und Suite**

`.venv\Scripts\python.exe -m pytest -m sw tests\live\test_live_zahnstangentrieb.py --collect-only -q` → 4 Tests;
`.venv\Scripts\python.exe -m pytest -q` → **827 passed, 133 deselected**.

- [ ] **Step 3: Negativfälle live, je mit frischem SolidWorks**

Vor jedem Fall BLOCKED (Neustart). Run (PowerShell) je Fall: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py "tests\live\test_live_zahnstangentrieb.py::<fall>" --zeit 900`
mit `<fall>` = `test_zahnphase_versetzt`, `test_drehrichtung_umgekehrt`, `test_kopplung_fehlt`, `test_uebersetzung_verfaelscht`.
Expected: je `OK` mit genau der Menge im Test. Weicht eine Menge ab: anhalten (NEEDS_CONTEXT) mit `maengel` und den
Prüfungen aus dem Bericht; Erwartungen nie selbst ändern (der Controller entscheidet nach dem Muster aus 4a, Präzisierung
13 dort). Je Fall Dauer und Private Bytes vorher → Spitze → nachher.

- [ ] **Step 4: Commit**

```powershell
git add tests/live/test_live_zahnstangentrieb.py
git commit -m "test: Negativfälle am Zahnstangentrieb – Zahnphase, Drehrichtung, Kopplung fehlt, Übersetzung (Stufe 4b, Task 14)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Skill, CLAUDE.md, Design, Spec-Nachzug, Ergebnisse, Regression

**Files:**
- Modify: `.claude/skills/baugruppe/SKILL.md`, `CLAUDE.md`, `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`,
  `docs/superpowers/specs/2026-10-05-stufe-4b-verzahnung-kopplungen-design.md`, `docs/stufe4b/ergebnisse.md`

**Interfaces:**
- Consumes: alle Tasks, Ledger.
- Produces: Doku; Regression.

- [ ] **Step 1: Skill `baugruppe`**

In `.claude/skills/baugruppe/SKILL.md` ersetzen:

```markdown
# Baugruppe (Stufe 3b, Bewegungen Stufe 4a)
```

durch:

```markdown
# Baugruppe (Stufe 3b, Bewegungen Stufe 4a, Kopplungen Stufe 4b)
```

und am Dateiende anfügen:

```markdown

## 7. Kopplungen (Stufe 4b)

Zahnrad- und Zahnstangenverknüpfung koppeln die Drehung von Wellen an eine Bewegung.
Spec: `docs/superpowers/specs/2026-10-05-stufe-4b-verzahnung-kopplungen-design.md` (Abweichungen der Umsetzung:
`docs/stufe4b/ergebnisse.md`). Vorlage: `tests/referenz/zahnstangentrieb/`.

- `zahnrad` (a und b Stirnräder) und `zahnstange` (a Ritzel, b Zahnstange); beide Seiten als `{komponente, feature}` auf
  ein Verzahnungs-Feature, gleiche Module. Keine Übersetzung angeben: swki leitet sie aus den Zähnezahlen ab.
- Seite `a` wird beim Bau um ihre Achse gedreht, bis Zahn in Lücke steht: `a` braucht `freiheitsgrade: gekoppelt` und
  ist Seite a nur einer Kopplung; `b` steht fest (fixiert, Teil der bewegten Gruppe oder Seite a einer früheren
  Kopplung). Kopplungen stehen nach allen anderen Verknüpfungen ihrer Komponenten (`KOPPLUNG_REIHENFOLGE`).
- Gekoppelte Wellen: Scharnier (Achse + Anlage) im Lager und `freiheitsgrade: {<welle>: gekoppelt}`; eine Zahnstange, die
  mit dem Schlitten fährt, kommt mit ihm in eine Gruppe mit `1`.
- Endlagen: jede gekoppelte Komponente braucht in der treibenden Bewegung eine Endlage `drehung` (`ENDLAGE_FEHLT`), Winkel
  als Ausdruck mit `pi` – Zahnstange: Weg·360/(π·m·z), Zahnrad: Winkel·z_a/z_b. `validieren` vergleicht die Beträge mit der
  Übersetzung (`UEBERSETZUNG_WIDERSPRUCH`). Den Drehsinn aus der Geometrie ableiten (Außenräder gegensinnig; Ritzel:
  Rechte-Hand-Regel mit der Fahrrichtung am Wälzpunkt) und nie nachträglich an eine Messung anpassen. Je Schritt weniger als
  180° Drehung (`SCHRITTE_ZU_GROB` nennt die nötige Schrittzahl).
- `bauen`: Knoten `zahnphase:<id>` vor jeder Kopplung, Fehler `ZAHNPHASE_FEHLER` (Phase nicht herstellbar – Lage der
  Komponenten bzw. Achsen prüfen).
- `pruefen`: `eingriff:<id>` (Achslage, Achsabstand, Überdeckung der Zahnbreiten, Wälzpunkt auf der Zahnstange,
  zurückgelesene Übersetzung), Kollision im Eingriff streng (Flankenspiel kommt aus `zahndickenabmass`),
  `freiheitsgrad:<welle>`, `sollweg:<Bewegung>:<k>` je Stellung (für alle Bewegungen, auch ohne Kopplung), Bilder
  `<id>-eingriff`. Unterdrückte Verknüpfungen meldet `verknuepfungen` als fehlerhaft.
- Speicher und Neustart wie §6: Live-Läufe mit Kopplungen je Test auf frischem SolidWorks.
```

- [ ] **Step 2: CLAUDE.md**

In `CLAUDE.md` ersetzen:

```markdown
Stand: Stufe 4a (Bewegungen) umgesetzt – Ergebnisse: docs/stufe4a/ergebnisse.md. Nächster Schritt: Stufe 4b (Verzahnung und
Kopplungen) umsetzen – Übergabe docs/superpowers/uebergabe-2026-10-05-stufe4b-umsetzung.md (Spec und Plan liegen vor).
```

durch:

```markdown
Stand: Stufe 4b (Verzahnung und Kopplungen) umgesetzt – Ergebnisse: docs/stufe4b/ergebnisse.md. Nächster Schritt nach
Nutzerwahl: Stufe 4c (Nut- und Kurvenverknüpfung), Paket „Messarten“ (Fasen, Gewinde durch, Lagerachse) oder Paket Speicher.
```

und vor `## Prüfen und Nachbessern (Stufe 2)` einfügen:

```markdown
## Verzahnung und Kopplungen (Stufe 4b)
- Zahnräder und Zahnstangen nur als `typ: verzahnung` (Evolvente, Bezugsprofil DIN 867, Modul DIN 780 Reihe 1,
  `zahndickenabmass` < 0); Regeln im Skill `konstruieren`. Die Modultabelle (`swki/wissen/module_din780.yaml`) nur mit
  Abgleich (≥ 2 Quellen) erweitern.
- Kopplungen `zahnrad`/`zahnstange` über den Skill `baugruppe` §7: Seite a `gekoppelt`, Kopplungen zuletzt, Endlagen der
  gekoppelten Wellen mit `pi`, Drehsinn aus der Geometrie.
- Regressions-Suite enthält den Zahnstangentrieb und seine Teile (`tests/referenz/zahnstangentrieb/`); Live-Läufe mit
  Kopplungen wie Bewegungen je Test auf frischem SolidWorks.

```

- [ ] **Step 3: Gesamtdesign §11**

In `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` ersetzen:

```markdown
| 4b | Mechanische Kopplungen: Zahnrad-, Nut-, Kurvenverknüpfung | Referenz *Schieber mit Schrägbolzen* (Kandidat) besteht |
```

durch:

```markdown
| 4b | Verzahnung (Feature `verzahnung`: Evolventen-Stirnrad, Zahnstange) und Kopplungen (Zahnrad-, Zahnstangenverknüpfung), Sollweg je Stellung – Design: [2026-10-05-stufe-4b-verzahnung-kopplungen-design.md](2026-10-05-stufe-4b-verzahnung-kopplungen-design.md) | Teil-Referenzen *Zahnstange*, *Ritzelwelle*, *Antriebswelle* und Referenz *Zahnstangentrieb* bestehen (Code-Prüfungen und Prüfer), fünf Negativfälle; Buchse, Formplatte, Auswerferhalteplatte, Stehlager, Linearschlitten bestehen weiter |
| 4c | Mechanische Kopplungen: Nut- und Kurvenverknüpfung | Referenz offen (allgemeine Konstruktion, z. B. Kulisse mit Nut oder Nocken mit Stößel) |
```

- [ ] **Step 4: Spec 4b nachziehen**

Jede Abweichung der Umsetzung (Ledger-Rulings zu S14a/S14b, Live-Funde der Tasks 4–14) an ihrer Stelle in der Spec als
„*Nachgezogen bei der Umsetzung, <Datum>:* …“ vermerken, wie in Spec 4a; die Präzisierungen dieses Plans stehen dort schon
(„Nachgezogen bei der Planung, 2026-10-05“).

- [ ] **Step 5: Regression (live)**

Je Fall einzeln mit `--zeit 900` und `PYTHONIOENCODING=utf-8`, Private Bytes vorher → Spitze (0,5-s-Abtastung) → nachher:
- SolidWorks frisch: `buchse`, `formplatte`, `auswerferhalteplatte`, `zahnstangentrieb-zahnstange`, `-ritzelwelle`,
  `-antriebswelle` (Teile, eine Sitzung bis ca. 4 GB);
- je frisch: `stehlager`, `schlitten-linearschlitten`, `zahnstangentrieb-zahnstangentrieb`;
- je frisch: die vier Negativfälle des Linearschlittens (`tests/live/test_live_schlitten.py`). Sie bekommen jetzt
  zusätzlich `sollweg:`-Prüfungen; kommt dabei ein Mangel hinzu, anhalten (NEEDS_CONTEXT) – der Controller entscheidet über
  die Erwartung (Spec 4b §10: „Erwartung nach Live-Lauf, nicht vorab angepasst“);
- je frisch: `tests/live/test_live_baugruppe.py::test_probe_besteht_pruefung`, `tests/live/test_live_bewegung.py`.
Alle müssen `OK` sein. Danach die volle Live-Suite (`.venv\Scripts\python.exe tests\live_einzeln.py tests\live --zeit 900`,
Neustarts wie oben durch den Controller) und `.venv\Scripts\python.exe -m pytest -q` → **827 passed, 133 deselected**
(zuzüglich der vom Controller entschiedenen Abweichungen).

- [ ] **Step 6: Ergebnisse**

`docs/stufe4b/ergebnisse.md` vervollständigen nach dem Muster von `docs/stufe4a/ergebnisse.md`: Kurzfassung, Spike S14a/S14b
(Tabellen mit Ergebnis und Ruling je Zeile), Referenzen (Teile und Zahnstangentrieb, Läufe, Prüfer-Urteile), Negativfälle
(Tabelle mit Mengen, Dauer, Speicher), Regression (Tabelle), Abweichungen von der Spec (Rulings mit „Wenn falsch“),
offene Punkte, Stand (Tasks und Commits).

- [ ] **Step 7: Commit**

```powershell
git add .claude/skills/baugruppe/SKILL.md CLAUDE.md docs/superpowers/specs/2026-09-26-solidworks-ki-design.md docs/superpowers/specs/2026-10-05-stufe-4b-verzahnung-kopplungen-design.md docs/stufe4b/ergebnisse.md
git commit -m "docs: Stufe 4b – Skill, CLAUDE.md, Design §11, Spec-Nachzug, Ergebnisse, Regression" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Abdeckung (Selbstprüfung gegen die Spec 4b)

| Spec | Inhalt | Task |
|---|---|---|
| §4.1 | Format `verzahnung`, Radachse als Referenz | 3, 4 |
| §4.2 | Geometrie Stirnrad/Zahnstange, Bezug Zahn 1 | 1 (Präzisierungen 3, 4) |
| §4.3 | Befunde, Hinweis `abmass_gross`, Modultabelle | 1, 3 (Präzisierung 5, 22) |
| §4.4 | Bau, Schutz über die freigegebene Kopie | 4, 5 |
| §4.5 | Prüfung `verzahnungen`, `verzahnung_mm`, `volumen: auto` | 3, 5 |
| §4.6 | Teil-Referenzen, Negativfall E1 | 6 |
| §5.1 | Format Kopplungen, `gekoppelt`, `pi` | 3, 9 |
| §5.2 | Befunde der Kopplungen | 9 |
| §5.3 | Freigabe (unverändert) | – |
| §5.4 | Bau: Reihenfolge, Zahnphase, CreateMate, Richtung, keine Hilfsverknüpfungen | 11 (Präzisierungen 7–9) |
| §5.5 | Statische Prüfung: Bestimmtheit, `eingriff`, unterdrückte Verknüpfungen, strenge Kollision | 9, 12 (Präzisierungen 12, 14) |
| §5.6 | Freiheitsgrad gekoppelt, Sollweg, aufsummierte Drehung | 10 (Präzisierungen 10, 11) |
| §5.7 | Bilder je Kopplung | 12 (Präzisierung 18) |
| §5.8 | Prüfbericht | 10, 12 (Präzisierung 21) |
| §6 | Reste aus 4a | 9, 10 (Präzisierung 20) |
| §7 | Prüfer, Bericht | 6, 10, 12, 13 |
| §8 | Fehlerfälle | 3, 9, 11 |
| §9 | Spikes S14a/S14b | 2, 8 |
| §10 | Tests, Negativfälle, Regression | alle; 14, 15 |
| §11 | Einbindung (Skills, Config, CLAUDE.md, Design) | 5, 6, 15 |
| §12 | Fertig, wenn | 6, 13, 14, 15 |
| §13 | Reihenfolge | Tasks 1–15 (Präzisierung 2) |
