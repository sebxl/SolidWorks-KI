# Stufe 3c – Kaufteile (STEP-Import) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** swki nimmt nicht genormte Kaufteile als STEP des Herstellers in einen Katalog auf (untersuchen, Eintrag `art: kaufteil` mit belegten Kennmaßen, Nutzerfreigabe, Prüfer-Urteil, Cache je SW-Jahr) und Baugruppen verwenden sie über `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}` mit Einbaureferenzen, Gewindepositionen und Gewindepaarung.

**Architecture:** Neues Paket `swki/kaufteile/`: reine Teile (Katalog, Eintrag mit Belegregel und Schutzregel, Ortung und Gegenprobe auf Flächenlisten, Bewertung, Diagnose-Übersicht, Quelle mit SHA-256, Cache) und eine SolidWorks-Schicht (`sw_kaufteil.py`: Import mit vorübergehenden Optionen, Check3, Bezugsgeometrie, Massenüberschreibung, Messen; `aufnahme.py`: untersuchen, baue_und_pruefe) unter den Befehlen `swki kaufteil untersuchen|muster|urteil|hole|liste`. Validieren und Freigeben des Eintrags laufen über die vorhandenen Befehle (Weiche nach `art`). Die Baugruppe bekommt die Komponentenquelle `kaufteil` (Teilansicht mit `referenz`-Features und Gewindegruppen), Referenz- und `je_position`-Form `gewinde`, Passung, Freigabe mit Eintragsprüfsumme, Kopie in den Lauf-Ordner und die Gewindepaarung im Kaufteil-Gewinde.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) für Spike und Live-Tests.

**Spec:** `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` (mit dem Nutzer abgestimmt, 2026-10-06; bei der Planung nachgezogen: §4.1, §4.2, §4.3, §4.5, §5.1, §5.3, §6.1, §8.1, §10, §11, §12). Kontext: Spec 3a `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md`, Spec 3b `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md`, Gesamtdesign `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`.

**Vorab geprüft (2026-10-06):** Der gesamte Plan-Code ohne SolidWorks wurde in einem frischen Wegwerf-Worktree Task für Task mechanisch aus diesem Dokument eingespielt (erst die Tests, RED-Lauf, dann die Umsetzung, GREEN-Lauf, ganze Suite, `swki api pruefe-code swki spikes tests/live`). Jede Ersetzung traf genau einmal, alle Testzahlen unten sind gemessen, `pruefe-code` blieb ohne Befund. Muster- und Referenz-Specs validieren ohne Befund und ohne Hinweis. Ungeprüft (braucht SolidWorks): der Spike, die SolidWorks-Schicht, die Aufnahme, Bau und Prüfen mit Kaufteilen und alle Live-Tests – dafür die Tabelle „Abhängigkeiten vom Spike S15“. Task 7 wurde mit einem simulierten Eintrag (Platzhalter statt SHA-256 und Volumen, Freigabe und Urteil per Skript) durchgespielt.

## Präzisierungen gegenüber der Spec (vom Planer, bindend für diesen Plan)

1. **Paket und Module:** `swki/kaufteile/` mit `fehler`, `katalog` (Namen, Finden, Prüfer-Urteil), `eintrag` (Laden, Validieren, Hinweise, Eigenschaften, Weiche), `ortung` (Gegenproben, rein), `bewertung` (rein), `diagnose` (Flächenübersicht, rein), `sw_kaufteil` (SolidWorks), `aufnahme` (untersuchen, baue_und_pruefe), `quelle`, `cache`, `befehle`. Die Speicherspitze misst `swki.speicher.Spitzenmessung` (Thread, 0,5 s).
2. **Laufordner:** `untersuchen`, `muster` und `hole` legen `<arbeitsordner>/KAUFTEILE/<Bibliotheksschlüssel>/lauf-<n>/` an (statt `untersuchung-<n>`, Spec §5.1 nachgezogen); dort `diagnose.json` bzw. `pruefbericht.json`.
3. **Ortung ist Prüfung:** Kein Treffer, mehrere Treffer und verfehlte Gegenproben werden Mängel `einbau:<name>` bzw. `gewinde:<gruppe>`; `hole` meldet `KAUFTEIL_PRUEFUNG`. `KAUFTEIL_EINBAU` entfällt (Spec §4.2/§10 nachgezogen). Toleranzen: Ø 0,01 mm, Winkel 0,01°, Lage der Bezugsgeometrie 0,01 mm, Ortung `toleranzen.anker_mm` (0,1 mm).
4. **Vorauswahl:** Vor dem echten Abstand (`GetClosestPointOn`, ein COM-Aufruf je Fläche) wählt `ortung.kandidaten` rein geometrisch die Flächen, deren unendliche Fläche höchstens die Ortungstoleranz vom Punkt liegt.
5. **Import:** `GetImportFileData` + `LoadFile4(pfad, "r", daten, fehler)` mit 3D Interconnect aus (691), automatischer Importdiagnose aus (690) und Strukturabbildung Mehrkörperteil (579 = 2); vorgefundene Werte über `sw.einstellung`/`sw.einstellung_int` wiederhergestellt. `ImportDiagnosis` wird nie aufgerufen (repariert); Diagnose über `IBody2.Check3` und die Zahl der Flächenkörper, beides Prüfung `import` (Spec §6.1 nachgezogen).
6. **Bezugsgeometrie:** Achse per `InsertAxis2(True)` mit ausgewählter Zylinderfläche, Ebene per `InsertRefPlane(4, …)` mit ausgewählter ebener Fläche, Drehlage per 3D-Skizzenpunkt `<name>_punkt` und `InsertRefPlane(4, 0, 4, 0, 0, 0)` (Achse Marke 0, Punkt Marke 1). Bezugsgeometrie wird **nicht** ausgeblendet; `muster` blendet Achsen und Ebenen im eigenen Dokument ein (`IModelDocExtension.SetUserPreferenceToggle(4|5, 0, True)`).
7. **Massenüberschreibung:** `IMassProperty2.GetOverrideOptions` → `OverrideMass = True`, `SetOverrideMassValue(kg)`; Prüfung `masse` vergleicht relativ 1e-6 und verlangt `OverrideMass`. Ohne `masse` im Eintrag: `ok: None`, „Masse aus Material geschätzt“.
8. **Katalog:** Ordner `ordnername(hersteller)` (`[a-z0-9-]`), Datei `dateiname(bestellnummer)` (`[a-z0-9_-]`), beide klein; statt einer Kollisionsprüfung meldet `validieren` eine falsche Lage der Datei (Spec §4.1 nachgezogen). Bibliotheksschlüssel `<Hersteller>_<Bestellnummer>` auf `[A-Za-z0-9-]`. Datumsangaben im Eintrag sind Text in Anführungszeichen (Schema).
9. **Belegregel:** je Kennmaß (`masse`, `pruefung.huellquader`, jedes `durchmesser_pruefen`, jedes `masse_pruefen`, jede Gewindegruppe) – `hersteller`, `datenblatt` oder `nutzer` genügt allein, sonst ≥ 2 `haendler`-Belege mit verschiedenen Domains (ohne `www.`). `hersteller` und `haendler` brauchen `url` und `abgerufen`, `datenblatt` braucht `datei` oder `url`.
10. **Schutzregel:** Muster `ISO|DIN|EN <Nummer>[-<Teil>]` in Benennung oder Bestellnummer gegen `norm` und `ersetzt` aller Normtabellen, auch ohne Teilnummer (`DIN 125-1` und `DIN 125`); andere Normen (z. B. DIN 625 für Wälzlager) bleiben erlaubt.
11. **Prüfung `einbau:<name>`:** Gegenprobe aus der Ortung plus Lage der angelegten Bezugsgeometrie (Achse auf der Zylinderachse, Ebene auf der Fläche, `ebene_durch_achse` enthält Achse und `nahe`) und `senkrecht_zu`. Der Prüfbericht nennt `bezug.richtung` – daraus folgt die `ausrichtung` in Baugruppen.
12. **Cache:** `IMPORTWEG_VERSION = 1`; Cache-Prüfsumme über Freigabe-Prüfsumme, `original.sha256` und Importweg; der Cache-Eintrag hält zusätzlich `sldprt_sha256` (Spec §7) und wird atomar geschrieben. Ein defekter Cache-Eintrag gilt als fehlend.
13. **Prüfer-Urteil** liegt als `<datei>.pruefer.json` neben dem Eintrag, gebunden an die Freigabe-Prüfsumme (`katalog.geprueft`). `swki kaufteil freigeben` gibt es nicht; freigegeben wird mit `swki freigeben <eintrag.yaml>`.
14. **Baugruppe:** Quelle `art: kaufteil` mit Teilansicht `{art: teil, name: <Bibliotheksschlüssel>, features: [{id: EINBAU_*, typ: referenz}], gewinde: …}`; Befunde `KAUFTEIL_UNBEKANNT`, `KAUFTEIL_NICHT_FREIGEGEBEN`, `KAUFTEIL_UNGEPRUEFT`; `drehung_sperren` Vorgabe `true` bei Kaufteilen; Hinweis `drehlage_doppelt`; Gewindepositionen nur in Verknüpfungen und `je_position`, nicht in `pruefung.masse_pruefen` der Baugruppe (Spec §8.1 nachgezogen).
15. **Freigabe der Baugruppe:** `teil_summen` enthält `kaufteil:<Schlüssel>` → Freigabe-Prüfsumme des Eintrags; `freigabe.json` der Baugruppe hält zusätzlich `kaufteile`, damit `FREIGABE_VERALTET` das geänderte Kaufteil nennt (`swki.spec.freigabe.freigeben(…, zusatz=…)`, `freigabe_eintrag`). Baugruppen ohne Kaufteile behalten ihre Prüfsumme.
16. **Gewindepaarung im Kaufteil:** Eintrittspunkte aus dem Eintrag (STEP- = Teilkoordinaten), Gewindemodell aus dem Bauprotokoll (`protokoll.kaufteile[<schluessel>].gewinde_modell`): `kernloch` → Ringvolumen, `nenn` → Soll 0, unbekannt → `ok: None` mit Hinweis; eine zu lange Schraube bleibt immer ein Mangel.
17. **Muster-Getriebemotor (Spec §11, Plan legt fest):** `SWKI-MUSTER GM42-10`, fiktiv. Gehäuse (1.0038): Flansch 60 × 60 × 12 (Flanschfläche y = 0, Normale −y), Körper Ø 56 × 70, Zentrierbund Ø 40 × 3, Wellenbohrung Ø 10 × 8, 4 × M5 auf Lochkreis Ø 60 (Bohrtiefe 10, Gewindetiefe 8); Welle (1.0503) Ø 10 × 30, freies Ende y = −25. STEP-Koordinaten = Gehäusekoordinaten, Hüllquader [60, 107, 60]. Eintrag: Material 1.0038, Masse 1,2 kg (Muster-Datenblatt `tests/referenz/motorhalter/muster/datenblatt.md`), `EINBAU_ACHSE` (Welle, ⟂ Flansch), `EINBAU_FLANSCH`, `EINBAU_DREHLAGE` (Ebene x = 0 durch die Achse), Gewindegruppe `flansch`.
18. **Referenz Motorhalter (Spec §11, Plan legt fest):** Grundplatte 160 × 100 × 12 mit 2 × M6 (Gewindetiefe 8, Bohrtiefe 10); Motorbock: Fuß x 0…75, y 0…10, z ±30, Wand x 0…10, y 0…90; Zentrierbohrung Ø 40 in Achshöhe 50, 4 × M5 Senkung auf der Wandrückseite, 2 × M6 Senkung im Fuß; Flanschschrauben ISO 4762 M5 × 12 (Einschraublänge 7,4), Fußschrauben M6 × 10 (6,4); Achshöhe 62, Hüllquader [160, 102, 100]; Drehlage `parallel` zu `vorne` des Bocks. Negativfall M5 × 16 (11,4 mm > Gewindetiefe 8).
19. **Negativfälle:** Ø-Gegenprobe und Körperzahl laufen live über `aufnahme.baue_und_pruefe` mit einem Testeintrag (Task 5); „Original geändert“ und „Eintrag nach der Baugruppen-Freigabe geändert“ sind Unit-Tests (Tasks 6 und 8; Spec §11 nachgezogen).
20. **Test-STEP:** Spike S15 baut die Muster-Baugruppe, exportiert sie und schreibt `tests/referenz/motorhalter/muster/gm42-10.step`; die Datei wird committet (Nutzerentscheidung 2026-10-06, Ausnahme von „erzeugte SolidWorks-Dateien nicht ins Git“).
21. **Regression:** `tests/referenz/test_referenzen.py` bekommt `("motorhalter", "motorhalter.yaml")` und `bereite_vor(ordner)`: für den Motorhalter kopiert sie das Muster-Original in den Quellordner (ohne SolidWorks).
22. **Bericht:** Prüfbericht der Baugruppe mit `kaufteile` (aus dem Protokoll: Schlüssel, Cache, gebaut, Cache-Prüfsumme, Gewindemodell, Masse, Kennmaße belegt/nicht belegt); `bericht.md` mit Abschnitt „Kaufteile“; `swki aenderungen` nennt Kopien „Normteil- oder Kaufteil-Kopie“.

## Global Constraints

- **Umfang 3c:** nur STEP; ein Teil je STEP (Mehrkörper); Katalogeintrag `art: kaufteil` mit Nutzerfreigabe und Prüfer-Urteil; Cache je SW-Jahr; Komponentenquelle `kaufteil`; Gewindepaarung im Kaufteil. Nicht: Parasolid, IGES, natives SLDPRT/SLDASM, Unterbaugruppen, Reparieren/Vereinfachen/Normalisieren/Aufteilen importierter Geometrie, Größengrenzen, Varianten eines Kaufteils, erlaubte Überlappungen außer Gewindepaarungen, genormte Teile als STEP, Rechner B.
- **Genormte Teile** (Schrauben, Muttern, Scheiben, Stifte) immer über `swki normteil hole`; nie als STEP.
- **Dateien des Nutzers nur lesen;** kopiert wird unverändert in `<kaufteilbibliothek>/quellen/<hersteller>/`, nie überschrieben. In `<kaufteilbibliothek>/<sw_jahr>/` schreibt nur `swki kaufteil hole`. **Keine Konten bei Herstellerportalen, keine Anmeldung, keine Downloads durch Claude.**
- **Freigabe:** Ein Kaufteil-Eintrag wird nur nach ausdrücklichem OK des Nutzers freigegeben (`swki freigeben <eintrag.yaml>`, Task 7: der Controller fragt den Nutzer). Die Prüfsumme deckt den ganzen Eintrag. Baugruppen: Prüfsumme wie 3b/4a plus `kaufteil:<Schlüssel>`.
- **Late Binding** (`swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()` (`GetOverrideOptions`, `Check3`, `Count`, `Is3DInterconnectFeature`, `GetBox`, `GetArea`, `FirstFeature`, `GetNextFeature`, `GetTypeName2`, `CreateMassProperty2`, `Mass`); `IBody2`-Methoden mit `()` (`GetFaces()`), wie in `swki.compiler.topologie`.
- **API nachschlagen:** vor jedem **neuen** SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` bzw. `… api enum <Name>` (vorher `PYTHONIOENCODING=utf-8`). `.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` muss ohne Befunde bleiben. Bereits nachgeschlagen (2026-10-06): `ISldWorks.GetImportFileData` (1: FileName; seit 2005), `ISldWorks.LoadFile4` (4: FileName, ArgString, ImportData, Errors-aus; seit 2006), `IImportStepData.MapConfigurationData` (Property, seit 2008; nicht benutzt), `ISldWorks.SetUserPreferenceToggle` (2), `ISldWorks.GetUserPreferenceIntegerValue` (1), `swUserPreferenceToggle_e` (swMultiCAD_Enable3DInterconnect 691, swImportNeutralRunDiagnostics 690, swDisplayAxes 4, swDisplayPlanes 5), `swUserPreferenceIntegerValue_e` (swImportNeutralAssemblyStructureMapping 579), `swImportNeutralAssemblyStructureMapping_e` (Default 0, MultipleParts 1, MultibodyPart 2), `IPartDoc.GetBodies2` (2; `swBodyType_e`: Solid 0, Sheet 1), `IBody2.Check3` (Property, liefert `IFaultEntity` oder nichts; seit 2004), `IFaultEntity.Count` (Property, seit 2004), `IFeature.Is3DInterconnectFeature` (Property, seit 2020), `IModelDoc2.InsertAxis2` (1: AutoSize), `IFeatureManager.InsertRefPlane` (6; `swRefPlaneReferenceConstraints_e` Coincident 4), `ISketchManager.Insert3DSketch` (1), `ISketchManager.CreatePoint` (3), `IModelDocExtension.CreateMassProperty2` (0, seit 2020), `IMassProperty2.GetOverrideOptions` (0, seit 2020), `IMassPropertyOverrideOptions.OverrideMass` (Property, seit 2020), `IMassPropertyOverrideOptions.SetOverrideMassValue` (1, seit 2020), `IMassPropertyOverrideOptions.GetOverrideMassValue` (0, seit 2020), `IMassProperty2.Mass` (Property, seit 2020), `IModelDocExtension.SetUserPreferenceToggle` (3: UserPref, Option, Value; seit 2009), `IModelDocExtension.GetUserPreferenceToggle` (2), `IFeature.Select2` (2). `IPartDoc.ImportDiagnosis` (4) repariert und wird **nicht** benutzt.
- **Einheiten:** Eintrag und Ausgaben in mm, Grad, kg; die API rechnet in m und rad (`mm()`, `in_mm()`, `in_mm3()` aus `swki.verbindung`).
- **Bestand bleibt:** Referenzen *Buchse*, *Formplatte*, *Auswerferhalteplatte*, *Stehlager*, *Linearschlitten*, *Zahnstangentrieb* bestehen weiter; Baugruppen ohne Kaufteile verhalten sich wie bisher (gleiche Freigabe-Prüfsumme).
- **Prüfwerte nie an Messwerte anpassen** (Ausnahme: `pruefung.volumen` des Eintrags kommt per Definition aus `untersuchen`, und nur vor der Freigabe). Erwartungen der Negativfälle nie abschwächen; weicht ein Live-Ergebnis ab, anhalten (NEEDS_CONTEXT) und dem Controller den Prüfbericht-Auszug melden.
- **Sprache:** Code-Bezeichner, Docstrings, Kommentare, Commit-Messages, Berichte auf Deutsch (mit Umlauten in Texten).
- **Tests:** `.venv\Scripts\python.exe -m pytest -q` (ohne SolidWorks; Stand vor dem Plan: **847 passed, 133 deselected**). Jeder Task nennt die erwarteten Zahlen (vorab gemessen); abweichende Zahlen im Bericht begründen. Live-Tests nur einzeln: `.venv\Scripts\python.exe tests\live_einzeln.py <datei> --zeit 600` mit `PYTHONIOENCODING=utf-8`.
- **SolidWorks-Speicher (Live-Tasks):** Private Bytes messen (`Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`), nicht das Working Set. Vor **jedem** Live-Test mit Baugruppe (Spike-Teil e, Motorhalter, Negativfall) frisches SolidWorks: der Implementer meldet BLOCKED (Neustart) mit der Test-ID, **der Controller startet SolidWorks neu** (Ablauf in `docs/superpowers/uebergabe-2026-10-05-stufe4b-umsetzung.md`). Teil-Live-Tests bis ca. 4 GB Private Bytes in einer Sitzung. Genau eine Instanz (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`); Einstellungen vor und nach Live-Läufen `False 1` (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); print(app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6))"`) und die drei Import-Optionen unverändert (`… print(app.GetUserPreferenceToggle(691), app.GetUserPreferenceToggle(690), app.GetUserPreferenceIntegerValue(579))`, Werte vor dem ersten Live-Lauf notieren). Implementer starten oder beenden SolidWorks nie. Keine künstliche CPU-Last.
- **Nur eigene Dokumente** anfassen; speichern nur im `arbeitsordner` aus `config/rechner.yaml`; nie ein SolidWorks-Jahr oder einen Pfad fest in Code schreiben; nie in die Normteilbibliothek schreiben (außer `swki normteil`).
- **Git:** Branch `stufe-3c` (von `plan-kaufteile`), kleine Commits je Task; Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **kein `git push` ohne Rückfrage**; nichts aus `auftraege/` committen; erzeugte SolidWorks-Dateien nie committen – einzige Ausnahme die Test-STEP `tests/referenz/motorhalter/muster/gm42-10.step` (Präzisierung 20); immer gezielt `git add <dateien>`. `core.autocrlf` ist `true`: neue Dateien und Volltext-Ersetzungen dürfen LF schreiben; Ersetzungen in bestehenden Dateien mit dem Edit-Werkzeug (kein sed auf CRLF-Dateien).
- **Ersetzungen:** „In `<datei>` ersetzen“ heißt: den Block exakt (ohne Zeilenende-Unterschiede) einmal finden und ersetzen. Trifft er nicht genau einmal, anhalten und melden (der Plan wurde so geprüft, dass jeder Block genau einmal trifft).
- **Subagents:** Implementer starten keine Subagents. Prüfer-Agenten startet der Controller. Nie zwei Implementer gleichzeitig, solange SolidWorks läuft.

## Dateistruktur nach diesem Plan

```
schema/kaufteil.schema.json                       neu: Katalogeintrag (art: kaufteil)
schema/baugruppe.schema.json                      + quelle kaufteil, je_position/Referenz gewinde
swki/kaufteile/{__init__,fehler,katalog,eintrag,ortung,bewertung,diagnose,sw_kaufteil,aufnahme,quelle,cache,befehle}.py
swki/wissen/kaufteile/swki-muster/                gm42-10.yaml, freigabe.json, gm42-10.freigegeben.yaml, gm42-10.pruefer.json
swki/{konfig,rechner,cli,speicher,aenderungen}.py, swki/spec/{befehle,freigabe}.py, swki/compiler/protokoll.py
swki/baugruppe/{modell,laden,aufloesen,plausibel,passung,freigabe,hinweise,bau,referenzen,pruefen,bewertung}.py
swki/pruefung/bericht.py
spikes/s15_kaufteile.py, docs/stufe0/ergebnisse/s15_kaufteile.json
tests/kaufteile/{beispiel,test_eintrag,test_ortung,test_bewertung,test_diagnose,test_befehle_kaufteile}.py
tests/baugruppe/{beispiel_kaufteil,test_kaufteil_baugruppe,test_kaufteil_bau_pruefen}.py
tests/live/{test_live_kaufteile,test_live_kaufteil_hole,test_live_motorhalter}.py
tests/referenz/motorhalter/                       muster/ (gehaeuse, welle, gm42, datenblatt, gm42-10.step), grundplatte,
                                                  motorbock, motorhalter, eingabe/beschreibung.md
tests/referenz/{test_motorhalter_muster,test_motorhalter,test_referenzen}.py
config/rechner.beispiel.yaml, .claude/skills/{kaufteile,baugruppe,normteile}/SKILL.md, .claude/agents/pruefer.md,
CLAUDE.md, Design §3/§5/§8/§9/§11, docs/stufe3c/ergebnisse.md
```

## Abhängigkeiten vom Spike S15 (Task 2)

Der Plan-Code setzt die Spalte „Annahme“ voraus. Weicht der Spike ab, entscheidet der Controller nach der Spalte „sonst“ und hält es im Ledger fest, bevor der betroffene Task beginnt.

| # | Frage | Annahme (Plan-Code) | sonst | betrifft |
|---|---|---|---|---|
| 1 | Test-STEP (e) | `swki bauen` der Muster-Baugruppe gelingt (`cli` = [0, 0, 0]); `SaveAs3` schreibt eine Baugruppen-STEP; zwei Exporte unterscheiden sich höchstens in Kopfzeilen | Export scheitert: Gehäuse und Welle als Mehrkörperteil-Spec (Ledger, Task 1 nachziehen); mehr Unterschiede: nur vermerken (die Datei wird committet) | 5, 7, 10 |
| 2 | Import (a) | `GetImportFileData` liefert Daten, `LoadFile4(…, "r", …)` ein Teil mit 2 Volumenkörpern bei Strukturabbildung 2 | `LoadFile4` liefert nichts: `OpenDoc6(pfad, 1, 1, "", e, w)` im selben Optionsblock (Ledger, `sw_kaufteil.importiere`); 1 Körper oder eine Baugruppe: Option `swImportStepConfigData` (183) bzw. andere Abbildung prüfen (Ledger); ohne Lösung Nutzer fragen | 5 |
| 3 | Optionen (a) | während: `3d_interconnect` False, `importdiagnose` False, `strukturabbildung` 2; nachher = vorher | Wiederherstellung defekt: `importoptionen` korrigieren (Ledger) | 5 |
| 4 | Ohne Original (a, d) | keine Features mit `Is3DInterconnectFeature`; nach Löschen der Import-Kopie öffnet das gespeicherte Teil mit 2 Körpern und allen `EINBAU_*` | Verweis bleibt: Optionen 791–793 (`swMultiCAD_3DInterconnect…`) untersuchen, Nutzer informieren; ohne Lösung Paket anhalten | 5, 9 |
| 5 | Diagnose (b) | `check3` = [None, None], 0 Flächenkörper; `box` umfasst beide Körper ([60, 107, 60]); Volumen > 0 | `Check3` liefert ein Objekt mit `Count` 0: unverändert (der Code zählt `Count`); Box nur eines Körpers: Box aus `IBody2.GetBodyBox` je Körper (Ledger, neue Funktion in `sw_kaufteil`) | 4, 5 |
| 6 | Achse (c) | `insertaxis2` True; Bezugsachse auf der y-Achse | sonst: Achse über zwei Kreiskanten der Welle (Ledger, `_bezugsachse`) | 5 |
| 7 | Ebene (c) | `ebene.erzeugt`; Ursprung y = 0; Normale der Bezugsebene parallel zur Flächennormale (0, −1, 0) – Vorzeichen notieren | Normale +y: Bewertung bleibt (prüft nur Parallelität), Motorhalter `v4` auf `ausrichtung: gleich` (Ledger, Task 10), Skill-Regel „Ausrichtung nach `bezug.richtung`“ bleibt | 5, 10 |
| 8 | Drehlage (c) | `punkt`, `punkt_gewaehlt`, `erzeugt` true; Normale der Ebene ±x | Auswahl oder Ebene scheitert: Hilfsachse durch ein Gewindeloch (`InsertAxis2` mit dessen Zylinderfläche, Name `<name>_achse`) und Ebene durch zwei Achsen (Ledger, `_ebene_durch_achse`, Präzisierung 6) | 5 |
| 9 | Masse (d) | `masse_kg` 1,2 und `override` true sofort und nach dem Neuöffnen; Baugruppe 1,2 kg | wirkt nicht oder geht verloren: nur Material, Prüfung `masse` `ok: None` mit Hinweis (Ledger), Nutzer informieren (Spec §2) | 5, 9 |
| 10 | Kernloch (c) | `gewinde_d` = [4,2] an Position 1 | Ø 5: Gewindemodell `nenn` (der Code kann beides), Erwartung `gewinde_modell` in den Tests der Tasks 5 und 7 auf `nenn` (Ledger) | 5, 7, 10 |
| 11 | Baugruppe (f) | `feature_by_name` alle true, `gewinde_entitaet` true, `masse_baugruppe_kg` 1,2 | `FeatureByName` liefert nichts: Auswahl per `SelectByID2("<name>@<komponente>@<baugruppe>", "AXIS"/"PLANE", …)` (Ledger, `sw_baugruppe.in_baugruppe`) | 9, 10 |
| 12 | Zeit und Speicher (g) | Import < 10 s, Zuwachs < 1 GB Private Bytes; `s_je_flaeche` < 0,05 | darüber: Hinweis im Skill `kaufteile` (Zeit je 1000 Flächen), Nutzer informieren; die Vorauswahl (Präzisierung 4) steht schon im Code | 5, 11 |
| 13 | Bilder (h) | Bezugsachsen und -ebenen in den PNG sichtbar (Sichtprobe des Controllers) | unsichtbar: Bilder ohne Bezüge, Prüfer stützt sich auf `bezug` im Prüfbericht (Ledger, `zeige_bezuege` entfällt) | 5, 7 |

## Reihenfolge und Testzahlen (vorab gemessen)

| Task | Inhalt | passed | deselected |
|---|---|---|---|
| – | Stand vor dem Plan | 847 | 133 |
| 1 | Muster-Getriebemotor (Specs) | 850 | 133 |
| 2 | Spike S15 (live) | 850 | 133 |
| 3 | Konfiguration, Schema, Katalog, Eintrag | 874 | 133 |
| 4 | Ortung, Bewertung, Diagnose, Spitzenmessung | 893 | 133 |
| 5 | SolidWorks-Schicht, Aufnahme (live) | 893 | 138 |
| 6 | Quelle, Cache, Befehle | 903 | 138 |
| 7 | Muster-Eintrag, Freigabe, Prüfer, hole (live) | 903 | 139 |
| 8 | Baugruppen: Format bis Freigabe | 912 | 139 |
| 9 | Baugruppen: Bau, Prüfen, Bericht | 917 | 139 |
| 10 | Referenz Motorhalter (live) | 918 | 141 |
| 11 | Doku, Regression, Abnahme | 918 | 141 |

---

### Task 1: Muster-Getriebemotor als Specs (ohne SolidWorks)

**Files:**
- Create: `tests/referenz/motorhalter/muster/gehaeuse.yaml`, `welle.yaml`, `gm42.yaml`, `datenblatt.md`
- Test: `tests/referenz/test_motorhalter_muster.py`

**Interfaces:**
- Consumes: `swki.spec.laden.lade_spec`, `swki.spec.hinweise.hinweise`, `swki.baugruppe.befehle.validieren`.
- Produces: die Muster-Baugruppe `gm42.yaml` (Spike S15 baut sie und erzeugt daraus `gm42-10.step`), das Muster-Datenblatt
  (Beleg `d1` des Katalogeintrags in Task 7). Lage: Flanschfläche y = 0, Welle bis y = −25, Lochkreis Ø 60 (Präzisierung 17).

- [ ] **Step 1: Tests schreiben**

`tests/referenz/test_motorhalter_muster.py` anlegen:

```python
"""Muster-Getriebemotor der Referenz Motorhalter (Spec 3c §11): die Specs, aus denen die Test-STEP entsteht, sind gültig."""

from pathlib import Path

import pytest

from swki.baugruppe.befehle import validieren as validieren_baugruppe
from swki.spec.hinweise import hinweise
from swki.spec.laden import lade_spec

MUSTER = Path(__file__).parent / "motorhalter" / "muster"


@pytest.mark.parametrize("datei", ["gehaeuse.yaml", "welle.yaml"])
def test_muster_teile_gueltig_ohne_hinweis(datei):
    assert hinweise(lade_spec(MUSTER / datei)) == []


def test_muster_baugruppe_gueltig():
    v = validieren_baugruppe(MUSTER / "gm42.yaml")
    assert (v["komponenten"], v["verknuepfungen"], v["hinweise"]) == (2, 2, [])
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\referenz\test_motorhalter_muster.py`
Expected: FAIL – `3 failed` (`SpecFehler: die Muster-Specs fehlen noch`).

- [ ] **Step 3: Umsetzen**

`tests/referenz/motorhalter/muster/gehaeuse.yaml` anlegen:

```yaml
# Muster-Getriebemotor GM42-10 (Spec 3c §11), Gehäuse – Quelle der Test-STEP gm42-10.step, kein echtes Herstellerteil.
# Flanschfläche (Anlage) y = 0, Flansch y 0…FD, Motorkörper y FD…FD+LM, Zentrierbund y −HZ…0 mit Wellenbohrung,
# 4 × M5 auf dem Lochkreis LK in der Flanschfläche (Kernloch, Gewinde kosmetisch).
art: teil
name: GM42_Gehaeuse
material: "1.0038"
eigenschaften: {Benennung: Muster-Getriebemotor GM42 Gehäuse}
parameter: {FB: 60, FD: 12, DM: 56, LM: 70, DZ: 40, HZ: 3, DW: 10, TW: 8, LK: 60, GT: 10, GG: 8}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=FB", hoehe: "=FB"}}]}
    ende: {typ: blind, tiefe: "=FD"}
  - id: f2
    typ: extrusion
    skizze: {ebene: {feature: f1, flaeche: "+y"}, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=DM"}}]}
    ende: {typ: blind, tiefe: "=LM"}
  - id: f3
    typ: extrusion
    skizze: {ebene: {feature: f1, flaeche: "-y"}, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=DZ"}}]}
    ende: {typ: blind, tiefe: "=HZ"}
  - {id: f4, typ: bohrung, flaeche: {feature: f3, flaeche: "-y"}, positionen: [[0, 0]], durchmesser: "=DW", tiefe: "=TW"}
  - {id: f5, typ: normbohrung, art: gewinde, groesse: M5, flaeche: {feature: f1, flaeche: "-y"},
     positionen: [["=LK/8**0.5", "=LK/8**0.5"], ["=-LK/8**0.5", "=LK/8**0.5"], ["=-LK/8**0.5", "=-LK/8**0.5"],
                  ["=LK/8**0.5", "=-LK/8**0.5"]],
     tiefe: "=GT", gewindetiefe: "=GG"}
pruefung:
  huellquader: ["=FB", "=HZ+FD+LM", "=FB"]
```

`tests/referenz/motorhalter/muster/welle.yaml` anlegen:

```yaml
# Muster-Getriebemotor GM42-10 (Spec 3c §11), Abtriebswelle Ø DW × LW, Achse = Modell-Y (Bezugsachse ACHSE).
art: teil
name: GM42_Welle
material: "1.0503"
eigenschaften: {Benennung: Muster-Getriebemotor GM42 Welle}
parameter: {DW: 10, LW: 30}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=DW"}}]}
    ende: {typ: blind, tiefe: "=LW"}
  - {id: ACHSE, typ: referenz, achse: y}
pruefung:
  huellquader: ["=DW", "=LW", "=DW"]
```

`tests/referenz/motorhalter/muster/gm42.yaml` anlegen:

```yaml
# Muster-Getriebemotor GM42-10 (Spec 3c §11): Gehäuse (fixiert, Ursprung = Baugruppenursprung) und Welle in der
# Wellenbohrung (Wellenende y = 5 an deren Grund, freies Ende y = −25). Aus dieser Baugruppe entsteht per SaveAs3 die
# Test-STEP gm42-10.step (Baugruppen-STEP mit 2 Körpern; Spike S15e).
art: baugruppe
name: GM42
eigenschaften: {Benennung: Muster-Getriebemotor GM42-10}
komponenten:
  - {id: gehaeuse, quelle: {teil: gehaeuse.yaml}, fixiert: true}
  - {id: welle, quelle: {teil: welle.yaml}}
verknuepfungen:
  - {id: v1, typ: deckungsgleich, a: {komponente: welle, feature: f1, flaeche: "+y"},
     b: {komponente: gehaeuse, feature: f4, instanz: 1, flaeche: "-y"}, ausrichtung: entgegengesetzt}
  - {id: v2, typ: konzentrisch, a: {komponente: welle, referenz: ACHSE},
     b: {komponente: gehaeuse, feature: f4, instanz: 1, achse: true}, drehung_sperren: true}
```

`tests/referenz/motorhalter/muster/datenblatt.md` anlegen:

~~~markdown
# Datenblatt Muster-Getriebemotor GM42-10 (fiktiv, SWKI-MUSTER)

Testdatenblatt für Stufe 3c (Spec 3c §11). Kein echtes Produkt; die Werte folgen aus den Specs `gehaeuse.yaml`,
`welle.yaml` und `gm42.yaml` in diesem Ordner. Seite 1:

| Merkmal | Wert |
|---|---|
| Flansch | 60 × 60 mm, Dicke 12 mm |
| Zentrierbund | Ø 40 mm, Höhe 3 mm |
| Abtriebswelle | Ø 10 mm, Überstand ab Flanschfläche 25 mm |
| Befestigung | 4 × M5 auf Lochkreis Ø 60 mm, Gewindetiefe 8 mm, Bohrtiefe 10 mm |
| Gehäuse | Ø 56 mm, Länge ab Flanschfläche 82 mm |
| Außenmaße | 60 × 107 × 60 mm |
| Masse | 1,2 kg |
~~~

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\referenz\test_motorhalter_muster.py`
Expected: `3 passed`. Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **850 passed, 133 deselected**.

- [ ] **Step 5: Commit**

```powershell
git add tests/referenz/motorhalter/muster tests/referenz/test_motorhalter_muster.py
git commit -m "referenz: Muster-Getriebemotor GM42-10 als Specs und Datenblatt (Stufe 3c, Task 1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Spike S15 – STEP-Import, Bezugsgeometrie, Masse (live)

**Files:**
- Create: `spikes/s15_kaufteile.py`
- Ergebnis: `docs/stufe0/ergebnisse/s15_kaufteile.json` (schreibt der Spike), `tests/referenz/motorhalter/muster/gm42-10.step` (Test-STEP, Präzisierung 20) – beide werden committet

**Interfaces:**
- Consumes: Task 1 (`gm42.yaml`), `swki.cli.main`, `sw.einstellung`/`einstellung_int`, `flaeche_aus`, `koerper`,
  `referenz_geometrie`, `screenshots`, `oeffne`, `privat_mb`.
- Produces: Antworten auf die Zeilen 1–13 der Tabelle „Abhängigkeiten vom Spike S15“ und die Test-STEP.

- [ ] **Step 1: Vorbedingungen prüfen**

SolidWorks 2025 läuft **frisch** (der Spike baut eine Baugruppe; BLOCKED Neustart an den Controller, falls nicht), genau eine
Instanz, keine fremden offenen Dokumente, Einstellungen `False 1`, Import-Optionen (691, 690, 579) notieren. Private Bytes
notieren.

- [ ] **Step 2: Spike schreiben**

`spikes/s15_kaufteile.py` anlegen:

```python
"""S15 (Stufe 3c): STEP-Import nicht genormter Kaufteile – Testdaten, Import, Diagnose, Bezugsgeometrie, Masse,
Baugruppe, Zeit und Speicher, Bilder (Spec 3c §12). Kein Produktionscode; die Aufrufe sind im API-Index nachgeschlagen.

e Testdaten: Muster-Baugruppe tests/referenz/motorhalter/muster/gm42.yaml in einer Kopie validieren, freigeben, bauen;
  zweimal per SaveAs3 als STEP exportieren und vergleichen; erste Datei → muster/gm42-10.step (wird committet).
a Import: GetImportFileData + LoadFile4 (4 Parameter), 3D Interconnect aus, Strukturabbildung Mehrkörperteil (2),
  keine automatische Importdiagnose; Optionen vorher/während/nachher; Rückfall OpenDoc6.
b Diagnose: Körper, IBody2.Check3, Flächenkörper, Features (Typ, Is3DInterconnectFeature), GetPartBox, Volumen, Zeit je
  Fläche (flaeche_aus).
c Bezugsgeometrie: Achse aus der Wellen-Zylinderfläche (InsertAxis2), Ebene deckungsgleich zur Flanschfläche
  (InsertRefPlane 4) mit ihrer Normale, Ebene durch die Achse und einen 3D-Skizzenpunkt.
d Masse: IMassProperty2.GetOverrideOptions → OverrideMass, SetOverrideMassValue(1,2); nach Speichern und Neuöffnen
  (Original-Kopie vorher gelöscht).
f Baugruppe: Komponente aus dem gespeicherten Teil, FeatureByName der Bezugsgeometrie, GetCorrespondingEntity einer
  Gewindefläche, Masse der Baugruppe.
g Speicher (Private Bytes) je Schritt.
h Bilder mit eingeblendeten Bezugsachsen/-ebenen (swDisplayAxes 4, swDisplayPlanes 5 am eigenen Dokument).

Aufruf: .venv\\Scripts\\python.exe -m spikes.s15_kaufteile
"""

import shutil
import tempfile
import time
from pathlib import Path

from spikes._gemeinsam import lauf
from swki.aenderungen import sha256_datei
from swki.cli import main
from swki.compiler import sw
from swki.compiler.anker import punkt_achse_abstand
from swki.compiler.topologie import flaeche_aus, koerper, referenz_geometrie
from swki.konfig import PROJEKT, lade_rechner
from swki.pruefung.bilder import screenshots
from swki.pruefung.messen import oeffne
from swki.speicher import privat_mb
from swki.verbindung import byref_long, callout_leer, in_mm3, mm, verbinde

MUSTER = PROJEKT / "tests" / "referenz" / "motorhalter" / "muster"
AUFTRAG = "S15-MUSTER"
SW_3D_INTERCONNECT, SW_IMPORT_DIAGNOSE, SW_IMPORT_STRUKTUR = 691, 690, 579
STRUKTUR_MEHRKOERPER = 2
SW_SHEET_BODY = 1
REF_PLANE_DECKUNGSGLEICH = 4
L = 21.2132


def _mb(app) -> float:
    return privat_mb(int(app.GetProcessID))


def _optionen(app) -> dict:
    return {"3d_interconnect": app.GetUserPreferenceToggle(SW_3D_INTERCONNECT),
            "importdiagnose": app.GetUserPreferenceToggle(SW_IMPORT_DIAGNOSE),
            "strukturabbildung": app.GetUserPreferenceIntegerValue(SW_IMPORT_STRUKTUR)}


def _testdaten(app, r) -> dict:
    e = {"privat_mb_vorher": _mb(app)}
    auftrag = Path(tempfile.mkdtemp()) / AUFTRAG
    shutil.copytree(MUSTER, auftrag, ignore=shutil.ignore_patterns("*.step", "*.md"))
    spec = str(auftrag / "gm42.yaml")
    e["cli"] = [main([befehl, spec]) for befehl in ("validieren", "freigeben", "bauen")]
    asm = sorted((r.arbeitsordner / AUFTRAG).glob("lauf-*/*.sldasm"))[-1]
    model = oeffne(app, asm)
    exporte = []
    try:
        for i in (1, 2):
            ziel = r.arbeitsordner / "S15" / f"gm42-10_{i}.step"
            sw.speichere(model, ziel, kopie=True)
            exporte.append(ziel)
            time.sleep(1.5)  # Zeitstempel im STEP-Kopf sollen sich unterscheiden können
    finally:
        sw.schliesse(app, model)
    a, b = (p.read_text(encoding="latin-1").splitlines() for p in exporte)
    unterschiede = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
    ziel = MUSTER / "gm42-10.step"
    shutil.copy2(exporte[0], ziel)
    e |= {"zeilen": len(a), "unterschiede": len(unterschiede) + abs(len(a) - len(b)), "beispiele": unterschiede[:5],
          "datei": str(ziel), "groesse_kb": round(ziel.stat().st_size / 1024, 1), "sha256": sha256_datei(ziel),
          "privat_mb_nachher": _mb(app)}
    return e


def _importiere(app, pfad: Path):
    e = {"vorher": _optionen(app), "privat_mb_vorher": _mb(app)}
    with sw.einstellung(app, SW_3D_INTERCONNECT, False), sw.einstellung(app, SW_IMPORT_DIAGNOSE, False), \
            sw.einstellung_int(app, SW_IMPORT_STRUKTUR, STRUKTUR_MEHRKOERPER):
        e["waehrend"] = _optionen(app)
        daten = app.GetImportFileData(str(pfad))
        e["importdaten"] = daten is not None
        fehler = byref_long()
        beginn = time.perf_counter()
        model = app.LoadFile4(str(pfad), "r", daten, fehler)
        e["loadfile4"] = {"dokument": model is not None, "fehler": fehler.value, "s": round(time.perf_counter() - beginn, 3)}
        if model is None:
            fehler2, warnungen = byref_long(), byref_long()
            model = app.OpenDoc6(str(pfad), 1, 1, "", fehler2, warnungen)
            e["opendoc6"] = {"dokument": model is not None, "fehler": fehler2.value, "warnungen": warnungen.value}
    e["nachher"] = _optionen(app)
    e["privat_mb_nachher"] = _mb(app)
    return model, e


def _diagnose(model) -> tuple[dict, list]:
    koerper_ = koerper(model)
    e = {"koerper": len(koerper_), "flaechenkoerper": len(model.GetBodies2(SW_SHEET_BODY, False) or ())}
    e["check3"] = [None if (c := b.Check3) is None else c.Count for b in koerper_]
    features, f = [], model.FirstFeature
    while f is not None:
        features.append([f.Name, f.GetTypeName2, bool(f.Is3DInterconnectFeature)])
        f = f.GetNextFeature
    e["features"] = features
    e["box"] = sw.teilebox_mm(model)
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    e["volumen"], e["masse_kg"] = round(in_mm3(mp.Volume), 3), mp.Mass
    beginn = time.perf_counter()
    flaechen = [flaeche_aus(x) for b in koerper_ for x in (b.GetFaces() or ())]
    e["flaechen"] = len(flaechen)
    e["s_je_flaeche"] = round((time.perf_counter() - beginn) / max(len(flaechen), 1), 4)
    e["zylinder_d"] = sorted({round(2 * x.radius, 4) for x in flaechen if x.art == "zylinder"})
    return e, flaechen


def _bezuege(model, flaechen: list) -> dict:
    e = {}
    welle = [f for f in flaechen if f.art == "zylinder" and abs(f.radius - 5) < 1e-6
             and abs(punkt_achse_abstand((5.0, -15.0, 0.0), f.punkt, f.achse) - 5) < 0.01]
    e["wellenflaechen"] = len(welle)
    sw.auswahl_leeren(model)
    sw.waehle(model, welle[0].objekt, 0)
    e["insertaxis2"] = bool(model.InsertAxis2(True))
    achse = sw.letztes_feature(model)
    achse.Name = "EINBAU_ACHSE"
    e["achse"] = {"typ": achse.GetTypeName2, "geometrie": referenz_geometrie(achse)}
    flansch = [f for f in flaechen if f.art == "ebene" and f.normale[1] < -0.999 and abs(f.punkt[1]) < 1e-6]
    e["flanschflaechen"] = [{"punkt": f.punkt, "normale": f.normale} for f in flansch]
    sw.auswahl_leeren(model)
    sw.waehle(model, flansch[0].objekt, 0)
    ebene = model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0, 0, 0.0)
    e["ebene"] = {"erzeugt": ebene is not None}
    if ebene is not None:
        ebene.Name = "EINBAU_FLANSCH"
        e["ebene"]["geometrie"] = referenz_geometrie(ebene)
    sm = model.SketchManager
    sw.auswahl_leeren(model)
    sm.Insert3DSketch(True)
    with sw.ohne_inferenz(sm):
        punkt = sm.CreatePoint(mm(0.0), mm(0.0), mm(25.0))
    sm.Insert3DSketch(True)
    skizze = sw.letztes_feature(model)
    skizze.Name = "EINBAU_DREHLAGE_punkt"
    sw.auswahl_leeren(model)
    achse.Select2(False, 0)
    gewaehlt = model.Extension.SelectByID2("Point1@EINBAU_DREHLAGE_punkt", "EXTSKETCHPOINT", 0, 0, 0, True, 1,
                                           callout_leer(), 0)
    drehlage = model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0)
    e["drehlage"] = {"punkt": punkt is not None, "punkt_gewaehlt": bool(gewaehlt), "erzeugt": drehlage is not None}
    if drehlage is not None:
        drehlage.Name = "EINBAU_DREHLAGE"
        e["drehlage"]["geometrie"] = referenz_geometrie(drehlage)
    sw.auswahl_leeren(model)
    try:
        sw.rebuild(model)
        e["rebuild"] = "ok"
    except Exception as ex:
        e["rebuild"] = str(ex)
    e["namen"] = {n: model.FeatureByName(n) is not None for n in ("EINBAU_ACHSE", "EINBAU_FLANSCH", "EINBAU_DREHLAGE")}
    gewinde = [f for f in flaechen if f.art == "zylinder" and punkt_achse_abstand((L, 0.0, L), f.punkt, f.achse) < 0.1]
    e["gewinde_d"] = sorted(round(2 * f.radius, 4) for f in gewinde)
    return e


def _masse(model) -> dict:
    mp = model.Extension.CreateMassProperty2
    optionen = mp.GetOverrideOptions
    optionen.OverrideMass = True
    optionen.SetOverrideMassValue(1.2)
    neu = model.Extension.CreateMassProperty2
    neu.UseSystemUnits = True
    return {"masse_kg": neu.Mass, "override": bool(neu.GetOverrideOptions.OverrideMass),
            "override_wert": neu.GetOverrideOptions.GetOverrideMassValue}


def _bilder(app, model, ordner: Path) -> dict:
    vorher = {t: model.Extension.GetUserPreferenceToggle(t, 0) for t in (4, 5)}
    for t in (4, 5):
        model.Extension.SetUserPreferenceToggle(t, 0, True)
    bilder = screenshots(app, model, ordner)
    return {"vorher": vorher, "bilder": {n: Path(p).stat().st_size for n, p in bilder.items()}, "pfade": bilder}


def _neu_oeffnen(app, teil: Path) -> dict:
    model = oeffne(app, teil)
    try:
        mp = model.Extension.CreateMassProperty2
        mp.UseSystemUnits = True
        features, f = [], model.FirstFeature
        while f is not None:
            features.append([f.Name, bool(f.Is3DInterconnectFeature)])
            f = f.GetNextFeature
        return {"koerper": len(koerper(model)), "masse_kg": mp.Mass, "override": bool(mp.GetOverrideOptions.OverrideMass),
                "namen": {n: model.FeatureByName(n) is not None for n in ("EINBAU_ACHSE", "EINBAU_FLANSCH", "EINBAU_DREHLAGE")},
                "interconnect": [n for n, i in features if i]}
    finally:
        sw.schliesse(app, model)


def _baugruppe(app, r, teil: Path) -> dict:
    model = oeffne(app, teil)
    asm = app.NewDocument(str(r.vorlage_baugruppe), 0, 0, 0)
    try:
        komp = asm.AddComponent5(str(teil), 0, "", False, "", 0.0, 0.0, 0.0)
        e = {"komponente": komp is not None}
        e["feature_by_name"] = {n: komp.FeatureByName(n) is not None for n in ("EINBAU_ACHSE", "EINBAU_FLANSCH", "EINBAU_DREHLAGE")}
        gewinde = [f for b in koerper(model) for f in (flaeche_aus(x) for x in (b.GetFaces() or ()))
                   if f.art == "zylinder" and punkt_achse_abstand((L, 0.0, L), f.punkt, f.achse) < 0.1]
        e["gewinde_entitaet"] = komp.GetCorrespondingEntity(gewinde[0].objekt) is not None if gewinde else None
        mp = asm.Extension.CreateMassProperty2
        mp.UseSystemUnits = True
        e["masse_baugruppe_kg"] = mp.Mass
        return e
    finally:
        sw.schliesse(app, asm)
        sw.schliesse(app, model)


def _untersuche() -> dict:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    ergebnis = {"privat_mb_start": _mb(app), "e_testdaten": _testdaten(app, r)}
    kopie = r.arbeitsordner / "S15" / "gm42-10_import.step"
    shutil.copy2(MUSTER / "gm42-10.step", kopie)
    model, ergebnis["a_import"] = _importiere(app, kopie)
    if model is None:
        return ergebnis
    teil = r.arbeitsordner / "S15" / "SWKI-MUSTER_GM42-10.sldprt"
    try:
        ergebnis["b_diagnose"], flaechen = _diagnose(model)
        ergebnis["c_bezuege"] = _bezuege(model, flaechen)
        ergebnis["d_masse"] = _masse(model)
        ergebnis["h_bilder"] = _bilder(app, model, r.arbeitsordner / "S15" / "bilder")
        sw.speichere(model, teil)
    finally:
        sw.schliesse(app, model)
    kopie.unlink()  # das Teil darf das Original nicht mehr brauchen
    ergebnis["d_neu_geoeffnet"] = _neu_oeffnen(app, teil)
    ergebnis["f_baugruppe"] = _baugruppe(app, r, teil)
    ergebnis["g_privat_mb_ende"] = _mb(app)
    ergebnis["optionen_ende"] = _optionen(app)
    return ergebnis


if __name__ == "__main__":
    lauf("s15_kaufteile", _untersuche)
```

- [ ] **Step 3: Spike laufen lassen**

Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m spikes.s15_kaufteile`
Expected: `"ok": true`, `docs/stufe0/ergebnisse/s15_kaufteile.json` und `tests/referenz/motorhalter/muster/gm42-10.step`.
Bricht der Spike ab: Fehler und Trace im JSON lesen, den Spike (nicht Produktionscode) korrigieren, erneut laufen lassen
(vorher den Arbeitsordner `S15`, `S15-MUSTER` aufräumen); jede Korrektur im Bericht nennen. Danach Private Bytes, eine
Instanz, `False 1`, Import-Optionen wie vorher, keine offenen Dokumente.

- [ ] **Step 4: Auswertung in den Bericht**

Für jede Zeile 1–13 der Tabelle „Abhängigkeiten vom Spike S15“: Annahme bestätigt / abweichend, mit den Werten aus dem
JSON (Zeile 1 `e_testdaten.cli`, `unterschiede`, `beispiele`, `groesse_kb`, `sha256`; 2 `a_import.importdaten`, `loadfile4`,
ggf. `opendoc6`, `b_diagnose.koerper`; 3 `vorher`/`waehrend`/`nachher`; 4 `b_diagnose.features` (Interconnect-Spalte),
`d_neu_geoeffnet`; 5 `check3`, `flaechenkoerper`, `box`, `volumen`; 6 `c_bezuege.insertaxis2`, `achse`; 7 `ebene`,
`flanschflaechen`; 8 `drehlage`; 9 `d_masse`, `d_neu_geoeffnet.masse_kg`/`override`, `f_baugruppe.masse_baugruppe_kg`;
10 `c_bezuege.gewinde_d`; 11 `f_baugruppe`; 12 `a_import.loadfile4.s`, Private Bytes, `s_je_flaeche`; 13 die Bilder aus
`h_bilder.pfade` ansehen lassen – der Controller macht die Sichtprobe). Keine Entscheidung treffen – die trifft der Controller.
Arbeitsordner `S15` und `S15-MUSTER` danach löschen.

- [ ] **Step 5: Commit**

```powershell
git add spikes/s15_kaufteile.py docs/stufe0/ergebnisse/s15_kaufteile.json tests/referenz/motorhalter/muster/gm42-10.step
git commit -m "spike: S15 Kaufteile – Test-STEP, Import, Bezugsgeometrie, Masse, Zeit und Speicher" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Status DONE_WITH_CONCERNS, wenn eine Zeile abweicht (Controller entscheidet nach der Spalte „sonst“).

---

### Task 3: Konfiguration, Schema, Katalog und Eintrag (ohne SolidWorks)

**Files:**
- Create: `schema/kaufteil.schema.json`, `swki/kaufteile/__init__.py`, `swki/kaufteile/fehler.py`, `swki/kaufteile/katalog.py`,
  `swki/kaufteile/eintrag.py`
- Modify: `swki/konfig.py`, `swki/rechner.py`, `config/rechner.beispiel.yaml`, `swki/spec/freigabe.py`, `swki/spec/befehle.py`
- Test: `tests/kaufteile/__init__.py`, `tests/kaufteile/beispiel.py`, `tests/kaufteile/test_eintrag.py`, `tests/test_konfig.py`,
  `tests/test_rechner.py`

**Interfaces:**
- Consumes: `swki.spec.laden.lade_yaml`/`schema_befunde`/`SpecFehler`, `swki.spec.freigabe.freigeben`/`pruefsumme`/`kopie_pfad`,
  `swki.normteile.tabelle` (Normtabellen), `swki.spec.normen.normmasse`, `swki.compiler.eigenschaften.ERSTELLER`.
- Produces (von späteren Tasks genutzt):
  - `Rechner.kaufteilbibliothek: Path | None` (Vorgabe in `swki rechner init`: `%SWKI_HOME%\kaufteile`).
  - `swki.kaufteile.fehler`: Codes `KAUFTEIL_FORMAT`, `KAUFTEIL_UNBEKANNT`, `KAUFTEIL_QUELLE_FEHLT`, `KAUFTEIL_QUELLE_ABWEICHEND`,
    `KAUFTEIL_IMPORT`, `KAUFTEIL_UNGEPRUEFT`, `KAUFTEIL_PRUEFUNG`; `KaufteilFehler(code, meldung, **daten)`.
  - `swki.kaufteile.katalog`: `ORDNER`, `ordnername(h)`, `dateiname(b)`, `schluessel(h, b)`, `bibliotheksschluessel(h, b)`,
    `teile_schluessel(text) -> (h, b)`, `eintrag_pfad(h, b, katalog=None)`, `eintraege(katalog=None) -> list[Path]`,
    `vorhandene(katalog=None)`, `finde(text, katalog=None) -> Path`, `urteil_pfad(pfad)`, `geprueft(pfad, spec) -> bool`.
    Funktionen mit `katalog=None` lesen `katalog.ORDNER` zur Laufzeit (Tests biegen es per monkeypatch um).
  - `swki.kaufteile.eintrag`: `kennmasse(spec) -> list[(pfad, beleg|None)]`, `beleg_befunde`, `genormte_normen`,
    `genormt_befunde`, `plausibel_befunde(spec, pfad=None)`, `eintrag_befunde(spec, pfad=None)`, `lade_eintrag(pfad) -> dict`,
    `hinweise_eintrag(spec)`, `eigenschaften(spec) -> dict[str, str]`, `angaben_fuer_bericht(spec) -> {"masse", "kennmasse"}`,
    `validieren(pfad)`, `freigeben(pfad)`.
  - `pruefsumme(spec)` deckt bei `art: kaufteil` den ganzen Eintrag; `swki validieren`/`swki freigeben` verzweigen nach `art`.
  - Testhilfe `tests/kaufteile/beispiel.py`: `EINTRAG` (Muster-Eintrag mit Platzhalter-SHA), `L`, `kopie(spec=None)`,
    `schreibe(katalog, spec=None) -> Path`.

- [ ] **Step 1: Tests schreiben**

`tests/kaufteile/__init__.py` anlegen:

```python

```

`tests/kaufteile/beispiel.py` anlegen:

```python
"""Gültiger Katalogeintrag für Tests (Muster-Getriebemotor wie die Referenz Motorhalter, Spec 3c §11; selbst
formuliert). STEP-Koordinaten: Flanschfläche y = 0 (Normale −y), Zentrierbund y −3…0, Welle Ø 10 bis y = −25, Gehäuse
bis y = 82; 4 × M5 auf Lochkreis Ø 60."""

import copy
from pathlib import Path

import yaml

from swki.kaufteile.katalog import eintrag_pfad

SHA = "0123456789abcdef" * 4
L = 21.2132  # Lochkreis Ø 60 / √8

EINTRAG = {
    "art": "kaufteil", "hersteller": "SWKI-MUSTER", "bestellnummer": "GM42-10",
    "benennung": "Getriebemotor GM42, i = 10 (Muster)",
    "original": {"datei": "gm42-10.step", "sha256": SHA, "bezug": {"art": "nutzer", "datum": "2026-10-07"}},
    "datenblatt": {"datei": "datenblatt.md"},
    "koerper": 2, "material": "1.0038", "masse": {"kg": 1.2, "beleg": ["d1"]},
    "eigenschaften": {"Benennung": "Getriebemotor GM42-10"},
    "belege": {"d1": {"art": "datenblatt", "datei": "datenblatt.md", "seite": 1}},
    "einbau": {
        "EINBAU_ACHSE": {"zylinder": {"nahe": [5, -15, 0], "durchmesser": 10, "senkrecht_zu": "EINBAU_FLANSCH"}},
        "EINBAU_FLANSCH": {"ebene": {"nahe": [25, 0, 25], "normale": [0, -1, 0]}},
        "EINBAU_DREHLAGE": {"ebene_durch_achse": {"achse": "EINBAU_ACHSE", "nahe": [0, 0, 25]}},
    },
    "gewinde": {"flansch": {"groesse": "M5", "gewindetiefe": 8, "tiefe": 10, "normale": [0, -1, 0], "beleg": ["d1"],
                            "positionen": [[L, 0, L], [-L, 0, L], [-L, 0, -L], [L, 0, -L]]}},
    "pruefung": {
        "huellquader": {"soll": [60, 107, 60], "tol": 0.1, "beleg": ["d1"]},
        "volumen": {"soll": 220000.0, "toleranz_prozent": 0.01},
        "durchmesser_pruefen": [
            {"was": "Wellen-Ø", "nahe": [5, -15, 0], "soll": 10, "referenz": "EINBAU_ACHSE", "beleg": ["d1"]},
            {"was": "Zentrierbund-Ø", "nahe": [20, -1.5, 0], "soll": 40, "referenz": "EINBAU_ACHSE", "beleg": ["d1"]},
        ],
        "masse_pruefen": [
            {"was": "Wellenüberstand", "von": {"referenz": "EINBAU_FLANSCH"},
             "zu": {"flaeche": {"nahe": [0, -25, 0], "normale": [0, -1, 0]}}, "soll": 25, "tol": 0.05, "beleg": ["d1"]},
            {"was": "Lochabstand", "von": {"gewinde": "flansch", "instanz": 1}, "zu": {"gewinde": "flansch", "instanz": 2},
             "soll": 42.4264, "tol": 0.05, "beleg": ["d1"]},
        ],
    },
}


def kopie(spec: dict | None = None) -> dict:
    return copy.deepcopy(spec or EINTRAG)


def schreibe(katalog: Path, spec: dict | None = None) -> Path:
    """Schreibt den Eintrag an seinen Platz im Katalog und liefert den Pfad."""
    spec = spec or EINTRAG
    pfad = eintrag_pfad(spec["hersteller"], spec["bestellnummer"], katalog)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad
```

`tests/kaufteile/test_eintrag.py` anlegen:

```python
import json

import pytest
import yaml

from swki.cli import main
from swki.kaufteile import katalog
from swki.kaufteile.eintrag import eintrag_befunde, hinweise_eintrag, lade_eintrag
from swki.kaufteile.fehler import KaufteilFehler
from swki.spec.freigabe import FreigabeFehler, pruefe_freigabe, pruefsumme
from swki.spec.laden import SpecFehler
from tests.kaufteile.beispiel import EINTRAG, kopie, schreibe


def _meldungen(spec, pfad=None) -> list[str]:
    return [f"{b['pfad']}: {b['meldung']}" for b in eintrag_befunde(spec, pfad)]


def test_namen_im_katalog():
    assert katalog.ordnername("SWKI Muster/AG") == "swki-muster-ag"
    assert katalog.dateiname("GM42-10/A") == "gm42-10_a"
    assert katalog.bibliotheksschluessel("SWKI-MUSTER", "GM42 10.1") == "SWKI-MUSTER_GM42_10_1"
    assert katalog.teile_schluessel(" SWKI-MUSTER  GM42 10 ") == ("SWKI-MUSTER", "GM42 10")


def test_finde_und_unbekannt(tmp_path):
    pfad = schreibe(tmp_path)
    assert pfad == tmp_path / "swki-muster" / "gm42-10.yaml"
    assert katalog.finde("SWKI-MUSTER GM42-10", tmp_path) == pfad
    assert katalog.vorhandene(tmp_path) == ["SWKI-MUSTER GM42-10"]
    with pytest.raises(KaufteilFehler) as e:
        katalog.finde("SWKI-MUSTER GM42-20", tmp_path)
    assert e.value.daten["code"] == "KAUFTEIL_UNBEKANNT" and e.value.daten["vorhanden"] == ["SWKI-MUSTER GM42-10"]
    with pytest.raises(KaufteilFehler):
        katalog.finde("swki-muster gm42-10", tmp_path)  # Schreibweise des Eintrags zählt


def test_gueltiger_eintrag(tmp_path):
    pfad = schreibe(tmp_path)
    assert lade_eintrag(pfad) == EINTRAG
    assert hinweise_eintrag(EINTRAG) == []


def test_lage_im_katalog(tmp_path):
    spec = kopie()
    pfad = schreibe(tmp_path, spec)
    falsch = pfad.with_name("anders.yaml")
    pfad.rename(falsch)
    assert _meldungen(spec, falsch) == ["(Datei): Eintrag gehört nach swki-muster/gm42-10.yaml (Hersteller und Bestellnummer)"]


def test_datum_muss_text_sein():
    spec = kopie()
    spec["original"]["bezug"]["datum"] = yaml.safe_load("d: 2026-10-07")["d"]
    [meldung] = _meldungen(spec)
    assert meldung.startswith("original.bezug.datum")


def test_einbau_bezuege():
    spec = kopie()
    spec["einbau"]["EINBAU_ACHSE"]["zylinder"]["senkrecht_zu"] = "EINBAU_ACHSE"
    spec["einbau"]["EINBAU_DREHLAGE"]["ebene_durch_achse"]["achse"] = "EINBAU_FLANSCH"
    spec["einbau"]["EINBAU_FLANSCH"]["ebene"]["normale"] = [0, 0, 0]
    assert _meldungen(spec) == [
        "einbau.EINBAU_ACHSE.zylinder.senkrecht_zu: 'EINBAU_ACHSE' ist keine ebene-Referenz dieses Eintrags",
        "einbau.EINBAU_FLANSCH.ebene.normale: Normale darf nicht der Nullvektor sein",
        "einbau.EINBAU_DREHLAGE.ebene_durch_achse.achse: 'EINBAU_FLANSCH' ist keine zylinder-Referenz dieses Eintrags",
    ]


def test_gewinde_befunde():
    spec = kopie()
    g = spec["gewinde"]["flansch"]
    g["groesse"], g["gewindetiefe"] = "M7", 12
    g["positionen"].append(list(g["positionen"][0]))
    assert _meldungen(spec) == [
        "gewinde.flansch.groesse: Gewinde M7 nicht in swki/wissen/bohrungsnormen.yaml",
        "gewinde.flansch.gewindetiefe: gewindetiefe darf nicht größer als tiefe sein",
        "gewinde.flansch.positionen[4]: Position 5 ist doppelt",
    ]


def test_messpunkte_und_namen():
    spec = kopie()
    pr = spec["pruefung"]
    pr["durchmesser_pruefen"][0]["referenz"] = "EINBAU_FLANSCH"
    pr["masse_pruefen"][0]["von"] = {"referenz": "EINBAU_FEHLT"}
    pr["masse_pruefen"][1]["zu"] = {"gewinde": "flansch", "instanz": 5}
    pr["durchmesser_pruefen"][1]["was"] = "Wellen-Ø"
    assert _meldungen(spec) == [
        "pruefung.durchmesser_pruefen[0].referenz: 'EINBAU_FLANSCH' ist keine zylinder-Referenz dieses Eintrags",
        "pruefung.masse_pruefen[0].von.referenz: Einbaureferenz 'EINBAU_FEHLT' fehlt unter einbau",
        "pruefung.masse_pruefen[1].zu.instanz: flansch hat nur 4 Positionen",
        "pruefung.durchmesser_pruefen[1].was: was 'Wellen-Ø' ist doppelt",
    ]


@pytest.mark.parametrize(("belege", "befund"), [
    ({"h1": {"art": "hersteller", "url": "https://hersteller.de/gm42", "abgerufen": "2026-10-07"}}, None),
    ({"h1": {"art": "nutzer", "hinweis": "im Chat"}}, None),
    ({"h1": {"art": "haendler", "url": "https://shop-a.de/x", "abgerufen": "2026-10-07"}}, "BELEG_UNZUREICHEND"),
    ({"h1": {"art": "haendler", "url": "https://www.shop-a.de/x", "abgerufen": "2026-10-07"},
      "h2": {"art": "haendler", "url": "https://shop-a.de/y", "abgerufen": "2026-10-07"}}, "BELEG_UNZUREICHEND"),
    ({"h1": {"art": "haendler", "url": "https://shop-a.de/x", "abgerufen": "2026-10-07"},
      "h2": {"art": "haendler", "url": "https://shop-b.com/y", "abgerufen": "2026-10-07"}}, None),
])
def test_belegregel(belege, befund):
    spec = kopie()
    spec["belege"] = belege
    spec["masse"]["beleg"] = list(belege)
    meldungen = [m for m in _meldungen(spec) if m.startswith("masse.")]
    if befund is None:
        assert meldungen == []
    else:
        [m] = meldungen
        assert befund in m


def test_beleg_fehlt_unter_belege():
    spec = kopie()
    spec["pruefung"]["huellquader"]["beleg"] = ["x9"]
    assert _meldungen(spec) == ["pruefung.huellquader.beleg: Beleg x9 fehlt unter belege"]


@pytest.mark.parametrize(("feld", "text", "genormt"), [
    ("benennung", "Zylinderschraube DIN 912 M5", True),
    ("bestellnummer", "ISO4762-M5x12", True),
    ("benennung", "Scheibe DIN 125-1 A", True),
    ("benennung", "Rillenkugellager DIN 625 6001-2RS", False),
])
def test_schutzregel(feld, text, genormt):
    spec = kopie()
    spec[feld] = text
    meldungen = [m for m in _meldungen(spec) if "KAUFTEIL_GENORMT" in m]
    assert bool(meldungen) is genormt


def test_hinweise_ohne_belege_und_masse():
    spec = kopie()
    del spec["masse"]
    for d in (spec["pruefung"]["huellquader"], *spec["pruefung"]["durchmesser_pruefen"],
              *spec["pruefung"]["masse_pruefen"], spec["gewinde"]["flansch"]):
        del d["beleg"]
    arten = [h["art"] for h in hinweise_eintrag(spec)]
    assert arten == ["nicht_belegt"] * 6 + ["kennmasse_nicht_belegt", "masse_aus_material"]


def _cli(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_validieren_und_freigeben_ueber_die_weiche(tmp_path, capsys):
    pfad = schreibe(tmp_path)
    code, v = _cli(capsys, "validieren", str(pfad))
    assert code == 0 and v["art"] == "kaufteil" and v["schluessel"] == "SWKI-MUSTER GM42-10" and v["hinweise"] == []
    code, f = _cli(capsys, "freigeben", str(pfad))
    assert code == 0 and f["pruefsumme"] == pruefsumme(EINTRAG) == v["pruefsumme"]
    assert (pfad.parent / "freigabe.json").is_file() and (pfad.parent / "gm42-10.freigegeben.yaml").is_file()
    pruefe_freigabe(pfad, EINTRAG)


def test_freigabe_deckt_den_ganzen_eintrag(tmp_path):
    pfad = schreibe(tmp_path)
    main(["freigeben", str(pfad)])
    anders = kopie()
    anders["einbau"]["EINBAU_FLANSCH"]["ebene"]["nahe"] = [26, 0, 25]
    assert pruefsumme(anders) != pruefsumme(EINTRAG)
    schreibe(tmp_path, anders)
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(pfad, lade_eintrag(pfad))
    assert e.value.daten["code"] == "FREIGABE_VERALTET"


def test_ungueltiger_eintrag_meldet_befunde(tmp_path, capsys):
    spec = kopie()
    spec["koerper"] = 0
    pfad = schreibe(tmp_path, spec)
    with pytest.raises(SpecFehler):
        lade_eintrag(pfad)
    code, v = _cli(capsys, "validieren", str(pfad))
    assert code == 1 and v["befunde"][0]["pfad"] == "koerper"


def test_eigenschaften_und_angaben_fuer_bericht():
    from swki.kaufteile.eintrag import angaben_fuer_bericht, eigenschaften

    assert eigenschaften(EINTRAG) == {"Ersteller": "SolidWorks-KI", "Benennung": "Getriebemotor GM42-10",
                                      "Hersteller": "SWKI-MUSTER", "Bestellnummer": "GM42-10"}
    assert angaben_fuer_bericht(EINTRAG) == {"masse": "1.2 kg (Datenblatt)", "kennmasse": "belegt"}
    ohne = kopie()
    del ohne["masse"]
    for d in (ohne["pruefung"]["huellquader"], *ohne["pruefung"]["durchmesser_pruefen"],
              *ohne["pruefung"]["masse_pruefen"], ohne["gewinde"]["flansch"]):
        del d["beleg"]
    assert angaben_fuer_bericht(ohne) == {"masse": "aus Material geschätzt", "kennmasse": "nicht belegt"}
```

In `tests/test_konfig.py` ersetzen:

```python
    assert lade_rechner(pfad).normteilbibliothek == Path("C:/bib")
```

durch:

```python
    assert lade_rechner(pfad).normteilbibliothek == Path("C:/bib")


def test_kaufteilbibliothek_optional(tmp_path):
    pfad = tmp_path / "rechner.yaml"
    grund = "sw_jahr: 2025\ninstallationsordner: C:/SW\nvorlage_teil: C:/t.prtdot\narbeitsordner: C:/arbeit\n"
    pfad.write_text(grund, encoding="utf-8")
    assert lade_rechner(pfad).kaufteilbibliothek is None
    pfad.write_text(grund + "kaufteilbibliothek: C:/kauf\n", encoding="utf-8")
    assert lade_rechner(pfad).kaufteilbibliothek == Path("C:/kauf")
```

In `tests/test_rechner.py` ersetzen:

```python
    assert r.arbeitsordner == swki_home / "arbeit"
    assert r.normteilbibliothek == r.arbeitsordner.parent / "normteile" == swki_home / "normteile"
```

durch:

```python
    assert r.arbeitsordner == swki_home / "arbeit"
    assert r.normteilbibliothek == r.arbeitsordner.parent / "normteile" == swki_home / "normteile"
    assert r.kaufteilbibliothek == swki_home / "kaufteile"
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile tests\test_konfig.py tests\test_rechner.py`
Expected: FAIL – `1 error` (`ModuleNotFoundError: No module named 'swki.kaufteile'`).

- [ ] **Step 3: Umsetzen**

In `swki/konfig.py` ersetzen:

```python
    arbeitsordner: Path
    normteilbibliothek: Path | None = None


_PFADFELDER = ("installationsordner", "vorlage_teil", "vorlage_baugruppe", "materialdatenbank", "arbeitsordner",
               "normteilbibliothek")
```

durch:

```python
    arbeitsordner: Path
    normteilbibliothek: Path | None = None
    kaufteilbibliothek: Path | None = None


_PFADFELDER = ("installationsordner", "vorlage_teil", "vorlage_baugruppe", "materialdatenbank", "arbeitsordner",
               "normteilbibliothek", "kaufteilbibliothek")
```

In `swki/rechner.py` ersetzen:

```python
        arbeitsordner=swki_home() / "arbeit",
        normteilbibliothek=swki_home() / "normteile",
    )
```

durch:

```python
        arbeitsordner=swki_home() / "arbeit",
        normteilbibliothek=swki_home() / "normteile",
        kaufteilbibliothek=swki_home() / "kaufteile",
    )
```

In `config/rechner.beispiel.yaml` ersetzen:

```yaml
arbeitsordner: 'C:\Users\<Benutzer>\.swki\arbeit'
normteilbibliothek: 'C:\Users\<Benutzer>\.swki\normteile'
```

durch:

```yaml
arbeitsordner: 'C:\Users\<Benutzer>\.swki\arbeit'
normteilbibliothek: 'C:\Users\<Benutzer>\.swki\normteile'
kaufteilbibliothek: 'C:\Users\<Benutzer>\.swki\kaufteile'
```

`schema/kaufteil.schema.json` anlegen:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Katalogeintrag eines Kaufteils (Spec 3c §4)",
  "type": "object",
  "required": ["art", "hersteller", "bestellnummer", "benennung", "original", "koerper", "material", "einbau"],
  "additionalProperties": false,
  "properties": {
    "art": {"const": "kaufteil"},
    "hersteller": {"type": "string", "pattern": "^\\S+$"},
    "bestellnummer": {"type": "string", "pattern": "^\\S(.*\\S)?$"},
    "benennung": {"type": "string", "minLength": 1},
    "original": {
      "type": "object", "required": ["datei", "sha256", "bezug"], "additionalProperties": false,
      "properties": {
        "datei": {"type": "string", "pattern": "^[^/\\\\]+\\.(step|stp|STEP|STP)$"},
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "bezug": {
          "type": "object", "required": ["art", "datum"], "additionalProperties": false,
          "properties": {
            "art": {"enum": ["nutzer", "url"]},
            "url": {"type": "string", "minLength": 1},
            "datum": {"$ref": "#/$defs/datum"},
            "hinweis": {"type": "string"}
          },
          "if": {"properties": {"art": {"const": "url"}}}, "then": {"required": ["url"]}
        }
      }
    },
    "datenblatt": {
      "type": "object", "minProperties": 1, "additionalProperties": false,
      "properties": {"datei": {"type": "string", "pattern": "^[^/\\\\]+$"}, "url": {"type": "string", "minLength": 1}}
    },
    "koerper": {"type": "integer", "minimum": 1},
    "material": {"type": "string", "minLength": 1},
    "masse": {
      "type": "object", "required": ["kg"], "additionalProperties": false,
      "properties": {"kg": {"type": "number", "exclusiveMinimum": 0}, "beleg": {"$ref": "#/$defs/beleg"}}
    },
    "eigenschaften": {"type": "object", "additionalProperties": {"type": "string"}},
    "belege": {"type": "object", "propertyNames": {"$ref": "#/$defs/id"}, "additionalProperties": {"$ref": "#/$defs/quelle"}},
    "einbau": {
      "type": "object", "minProperties": 1, "propertyNames": {"$ref": "#/$defs/einbauname"},
      "additionalProperties": {"$ref": "#/$defs/einbau"}
    },
    "gewinde": {"type": "object", "propertyNames": {"$ref": "#/$defs/id"}, "additionalProperties": {"$ref": "#/$defs/gewindegruppe"}},
    "pruefung": {"$ref": "#/$defs/pruefung"}
  },
  "$defs": {
    "id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]*$"},
    "einbauname": {"type": "string", "pattern": "^EINBAU_[A-Z0-9_]+$"},
    "datum": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
    "zahl": {"type": "number"},
    "punkt3": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
    "beleg": {"type": "array", "items": {"$ref": "#/$defs/id"}, "minItems": 1, "uniqueItems": true},
    "quelle": {
      "type": "object", "required": ["art"], "additionalProperties": false,
      "properties": {
        "art": {"enum": ["hersteller", "datenblatt", "haendler", "nutzer"]},
        "url": {"type": "string", "minLength": 1},
        "datei": {"type": "string", "minLength": 1},
        "seite": {"type": ["integer", "string"]},
        "abgerufen": {"$ref": "#/$defs/datum"},
        "hinweis": {"type": "string"}
      },
      "allOf": [
        {"if": {"properties": {"art": {"enum": ["hersteller", "haendler"]}}}, "then": {"required": ["url", "abgerufen"]}},
        {"if": {"properties": {"art": {"const": "datenblatt"}}}, "then": {"anyOf": [{"required": ["datei"]}, {"required": ["url"]}]}}
      ]
    },
    "einbau": {
      "oneOf": [
        {"type": "object", "required": ["zylinder"], "additionalProperties": false,
         "properties": {"zylinder": {
           "type": "object", "required": ["nahe", "durchmesser"], "additionalProperties": false,
           "properties": {"nahe": {"$ref": "#/$defs/punkt3"}, "durchmesser": {"type": "number", "exclusiveMinimum": 0},
                          "senkrecht_zu": {"$ref": "#/$defs/einbauname"}}}}},
        {"type": "object", "required": ["ebene"], "additionalProperties": false,
         "properties": {"ebene": {
           "type": "object", "required": ["nahe", "normale"], "additionalProperties": false,
           "properties": {"nahe": {"$ref": "#/$defs/punkt3"}, "normale": {"$ref": "#/$defs/punkt3"}}}}},
        {"type": "object", "required": ["ebene_durch_achse"], "additionalProperties": false,
         "properties": {"ebene_durch_achse": {
           "type": "object", "required": ["achse", "nahe"], "additionalProperties": false,
           "properties": {"achse": {"$ref": "#/$defs/einbauname"}, "nahe": {"$ref": "#/$defs/punkt3"}}}}}
      ]
    },
    "gewindegruppe": {
      "type": "object", "required": ["groesse", "gewindetiefe", "tiefe", "normale", "positionen"], "additionalProperties": false,
      "properties": {
        "groesse": {"type": "string", "pattern": "^M\\d+(\\.\\d+)?$"},
        "gewindetiefe": {"type": "number", "exclusiveMinimum": 0},
        "tiefe": {"type": "number", "exclusiveMinimum": 0},
        "normale": {"$ref": "#/$defs/punkt3"},
        "positionen": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/punkt3"}},
        "beleg": {"$ref": "#/$defs/beleg"}
      }
    },
    "messpunkt": {
      "oneOf": [
        {"type": "object", "required": ["referenz"], "additionalProperties": false,
         "properties": {"referenz": {"$ref": "#/$defs/einbauname"}}},
        {"type": "object", "required": ["gewinde", "instanz"], "additionalProperties": false,
         "properties": {"gewinde": {"$ref": "#/$defs/id"}, "instanz": {"type": "integer", "minimum": 1}}},
        {"type": "object", "required": ["flaeche"], "additionalProperties": false,
         "properties": {"flaeche": {
           "type": "object", "required": ["nahe", "normale"], "additionalProperties": false,
           "properties": {"nahe": {"$ref": "#/$defs/punkt3"}, "normale": {"$ref": "#/$defs/punkt3"}}}}},
        {"type": "object", "required": ["punkt"], "additionalProperties": false,
         "properties": {"punkt": {"$ref": "#/$defs/punkt3"}}}
      ]
    },
    "pruefung": {
      "type": "object", "additionalProperties": false,
      "properties": {
        "huellquader": {
          "type": "object", "required": ["soll"], "additionalProperties": false,
          "properties": {
            "soll": {"type": "array", "items": {"type": "number", "exclusiveMinimum": 0}, "minItems": 3, "maxItems": 3},
            "tol": {"type": "number", "exclusiveMinimum": 0}, "beleg": {"$ref": "#/$defs/beleg"}
          }
        },
        "volumen": {
          "type": "object", "required": ["soll"], "additionalProperties": false,
          "properties": {"soll": {"type": "number", "exclusiveMinimum": 0},
                         "toleranz_prozent": {"type": "number", "exclusiveMinimum": 0}}
        },
        "durchmesser_pruefen": {
          "type": "array",
          "items": {
            "type": "object", "required": ["was", "nahe", "soll"], "additionalProperties": false,
            "properties": {
              "was": {"type": "string", "minLength": 1}, "nahe": {"$ref": "#/$defs/punkt3"},
              "soll": {"type": "number", "exclusiveMinimum": 0}, "tol": {"type": "number", "exclusiveMinimum": 0},
              "referenz": {"$ref": "#/$defs/einbauname"}, "beleg": {"$ref": "#/$defs/beleg"}
            }
          }
        },
        "masse_pruefen": {
          "type": "array",
          "items": {
            "type": "object", "required": ["was", "von", "zu", "soll"], "additionalProperties": false,
            "properties": {
              "was": {"type": "string", "minLength": 1}, "von": {"$ref": "#/$defs/messpunkt"},
              "zu": {"$ref": "#/$defs/messpunkt"}, "soll": {"type": "number", "minimum": 0},
              "tol": {"type": "number", "exclusiveMinimum": 0}, "beleg": {"$ref": "#/$defs/beleg"}
            }
          }
        }
      }
    }
  }
}
```

`swki/kaufteile/__init__.py` anlegen:

```python
"""Kaufteile (Stufe 3c): STEP-Import nicht genormter Kaufteile, Katalog, Cache je SW-Version."""
```

`swki/kaufteile/fehler.py` anlegen:

```python
"""Fehlercodes der Kaufteile (Spec 3c §10)."""

from swki.cli import SwkiFehler

KAUFTEIL_FORMAT = "KAUFTEIL_FORMAT"
KAUFTEIL_UNBEKANNT = "KAUFTEIL_UNBEKANNT"
KAUFTEIL_QUELLE_FEHLT = "KAUFTEIL_QUELLE_FEHLT"
KAUFTEIL_QUELLE_ABWEICHEND = "KAUFTEIL_QUELLE_ABWEICHEND"
KAUFTEIL_IMPORT = "KAUFTEIL_IMPORT"
KAUFTEIL_UNGEPRUEFT = "KAUFTEIL_UNGEPRUEFT"
KAUFTEIL_PRUEFUNG = "KAUFTEIL_PRUEFUNG"


class KaufteilFehler(SwkiFehler):
    def __init__(self, code: str, meldung: str, **daten):
        super().__init__(meldung)
        self.daten = {"code": code, **daten}
```

`swki/kaufteile/katalog.py` anlegen:

```python
"""Katalog der Kaufteile (Spec 3c §3, §4.1): je Kaufteil eine Datei swki/wissen/kaufteile/<hersteller>/<bestellnummer>.yaml
(art: kaufteil) im Git; daneben freigabe.json, <datei>.freigegeben.yaml und <datei>.pruefer.json.
Schlüssel "<Hersteller> <Bestellnummer>" (der Hersteller hat kein Leerzeichen)."""

import json
import re
from pathlib import Path

import yaml

from swki.kaufteile.fehler import KAUFTEIL_UNBEKANNT, KaufteilFehler
from swki.konfig import PROJEKT
from swki.spec.freigabe import pruefsumme

ORDNER = PROJEKT / "swki" / "wissen" / "kaufteile"
_KOPIE = ".freigegeben.yaml"


def _katalog(katalog: Path | None) -> Path:
    return ORDNER if katalog is None else katalog


def ordnername(hersteller: str) -> str:
    """Ordner des Herstellers: Kleinbuchstaben, alle Zeichen außer [a-z0-9-] → "-"."""
    return re.sub(r"[^a-z0-9-]+", "-", hersteller.lower()).strip("-")


def dateiname(bestellnummer: str) -> str:
    """Dateiname des Eintrags ohne Endung: Kleinbuchstaben, alle Zeichen außer [a-z0-9_-] → "_"."""
    return re.sub(r"[^a-z0-9_-]+", "_", bestellnummer.lower()).strip("_")


def schluessel(hersteller: str, bestellnummer: str) -> str:
    return f"{hersteller} {bestellnummer}"


def bibliotheksschluessel(hersteller: str, bestellnummer: str) -> str:
    """Dateiname im Cache und im Lauf-Ordner, z. B. "SWKI-MUSTER_GM42-10"."""
    return re.sub(r"[^A-Za-z0-9-]+", "_", f"{hersteller}_{bestellnummer}").strip("_")


def teile_schluessel(text: str) -> tuple[str, str]:
    """"SWKI-MUSTER GM42-10" → ("SWKI-MUSTER", "GM42-10"): der Hersteller endet am ersten Leerzeichen."""
    hersteller, _, bestellnummer = text.strip().partition(" ")
    return hersteller, bestellnummer.strip()


def eintrag_pfad(hersteller: str, bestellnummer: str, katalog: Path | None = None) -> Path:
    return _katalog(katalog) / ordnername(hersteller) / f"{dateiname(bestellnummer)}.yaml"


def eintraege(katalog: Path | None = None) -> list[Path]:
    """Alle Eintragsdateien (ohne Freigabe-Kopien), sortiert."""
    return sorted(p for p in _katalog(katalog).glob("*/*.yaml") if not p.name.endswith(_KOPIE))


def _kopf(pfad: Path) -> tuple[str, str] | None:
    """(hersteller, bestellnummer) einer Eintragsdatei ohne Prüfung; None, wenn sie nicht lesbar ist."""
    try:
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(daten, dict):
        return None
    return str(daten.get("hersteller")), str(daten.get("bestellnummer"))


def vorhandene(katalog: Path | None = None) -> list[str]:
    """Schlüssel aller lesbaren Einträge."""
    return [schluessel(*k) for p in eintraege(katalog) if (k := _kopf(p)) is not None]


def finde(text: str, katalog: Path | None = None) -> Path:
    """Pfad des Eintrags zum Schlüssel; KAUFTEIL_UNBEKANNT mit den vorhandenen Schlüsseln."""
    hersteller, bestellnummer = teile_schluessel(text)
    pfad = eintrag_pfad(hersteller, bestellnummer, katalog) if bestellnummer else None
    if pfad is not None and pfad.is_file() and _kopf(pfad) == (hersteller, bestellnummer):
        return pfad
    alle = vorhandene(katalog)
    gleich = [s for s in alle if teile_schluessel(s)[0] == hersteller]
    raise KaufteilFehler(KAUFTEIL_UNBEKANNT,
                         f"Kaufteil {text!r} unbekannt; vorhanden: {', '.join(gleich or alle) or 'keine'}",
                         vorhanden=gleich or alle)


def urteil_pfad(pfad: Path) -> Path:
    """Prüfer-Urteil neben dem Eintrag: <datei>.pruefer.json."""
    return pfad.with_name(f"{pfad.stem}.pruefer.json")


def geprueft(pfad: Path, spec: dict) -> bool:
    """Bestandenes Prüfer-Urteil zur aktuellen Freigabe-Prüfsumme des Eintrags vorhanden?"""
    datei = urteil_pfad(pfad)
    if not datei.is_file():
        return False
    u = json.loads(datei.read_text(encoding="utf-8"))
    return u.get("freigabe_pruefsumme") == pruefsumme(spec) and u.get("bestanden") is True
```

`swki/kaufteile/eintrag.py` anlegen:

```python
"""Katalogeintrag eines Kaufteils laden und prüfen (Spec 3c §4.5): Schema, Lage im Katalog, Einbaureferenzen,
Gewindegruppen, Messpunkte, Belegregel, Schutzregel gegen genormte Teile; Hinweise; Weiche für validieren und
freigeben."""

import math
import re
from pathlib import Path
from urllib.parse import urlparse

from swki.compiler.eigenschaften import ERSTELLER
from swki.kaufteile.katalog import dateiname, ordnername, schluessel
from swki.normteile.tabelle import ORDNER as NORMTABELLEN, lade_normtabelle, norm_datei, normen
from swki.spec.freigabe import freigeben as spec_freigeben, kopie_pfad, pruefsumme
from swki.spec.laden import SpecFehler, lade_yaml, schema_befunde
from swki.spec.normen import normmasse

HERSTELLERQUELLEN = ("hersteller", "datenblatt", "nutzer")  # eine davon genügt als Beleg (Spec 3c §2)
_NORM = re.compile(r"\b(ISO|DIN|EN)\s*-?\s*(\d+(?:-\d+)?)\b", re.IGNORECASE)
_TOL_LAENGE = 1e-9


def _b(pfad: str, meldung: str) -> dict:
    return {"pfad": pfad, "meldung": meldung}


def _null(v) -> bool:
    return math.sqrt(sum(c * c for c in v)) < _TOL_LAENGE


def kennmasse(spec: dict) -> list[tuple[str, list | None]]:
    """(Pfad, Beleg-IDs oder None) aller Kennmaße: Masse, Hüllquader, Durchmesser, Maße, Gewindegruppen."""
    pr = spec.get("pruefung", {})
    ergebnis = []
    if "masse" in spec:
        ergebnis.append(("masse", spec["masse"].get("beleg")))
    if "huellquader" in pr:
        ergebnis.append(("pruefung.huellquader", pr["huellquader"].get("beleg")))
    ergebnis += [(f"pruefung.durchmesser_pruefen[{i}]", d.get("beleg")) for i, d in enumerate(pr.get("durchmesser_pruefen", []))]
    ergebnis += [(f"pruefung.masse_pruefen[{i}]", m.get("beleg")) for i, m in enumerate(pr.get("masse_pruefen", []))]
    ergebnis += [(f"gewinde.{g}", w.get("beleg")) for g, w in spec.get("gewinde", {}).items()]
    return ergebnis


def _domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc.removeprefix("www.")


def beleg_befunde(spec: dict) -> list[dict]:
    """Belegregel (Spec 3c §2): eine Herstellerquelle (hersteller, datenblatt) oder nutzer genügt allein; sonst ≥ 2
    Händlerquellen mit verschiedenen Domains. Kennmaße ohne Beleg sind erlaubt (Hinweis nicht_belegt)."""
    belege = spec.get("belege", {})
    befunde = []
    for pfad, ids in kennmasse(spec):
        if not ids:
            continue
        fehlend = [i for i in ids if i not in belege]
        if fehlend:
            befunde.append(_b(f"{pfad}.beleg", f"Beleg {', '.join(fehlend)} fehlt unter belege"))
            continue
        if {belege[i]["art"] for i in ids} & set(HERSTELLERQUELLEN):
            continue
        domains = {_domain(belege[i]["url"]) for i in ids}
        if len(domains) < 2:
            befunde.append(_b(f"{pfad}.beleg", f"BELEG_UNZUREICHEND: nur Händlerquellen ({', '.join(sorted(domains))}); "
                                               "nötig: Herstellerquelle, Datenblatt, Nutzer oder ≥ 2 Händler mit "
                                               "verschiedenen Domains"))
    return befunde


def genormte_normen(wissen: Path = NORMTABELLEN) -> dict[str, str]:
    """Norm und ersetzte Norm jeder Normtabelle in Dateischreibweise → Norm der Tabelle ("din912" → "ISO 4762"); bei
    Normen mit Teilnummer auch ohne sie ("DIN 125-1" → "din1251" und "din125")."""
    ergebnis = {}
    for name in normen(wissen):
        t = lade_normtabelle(name, wissen)
        for n in (t.get("norm"), t.get("ersetzt")):
            if n:
                for schreibweise in {str(n), str(n).split("-")[0]}:
                    ergebnis[norm_datei(schreibweise)] = str(t.get("norm"))
    return ergebnis


def genormt_befunde(spec: dict, wissen: Path = NORMTABELLEN) -> list[dict]:
    """Schutzregel (Spec 3c §4.5): Benennung oder Bestellnummer nennen eine Norm einer Normtabelle."""
    bekannt = genormte_normen(wissen)
    befunde = []
    for feld in ("benennung", "bestellnummer"):
        for treffer in _NORM.finditer(spec[feld]):
            norm = norm_datei(f"{treffer.group(1)} {treffer.group(2)}")
            if norm in bekannt:
                befunde.append(_b(feld, f"KAUFTEIL_GENORMT: {treffer.group(0)} ist ein Normteil ({bekannt[norm]}) – "
                                        "genormte Teile über swki normteil hole, nie als STEP"))
    return befunde


def _messpunkt_befunde(mp: dict, pfad: str, spec: dict) -> list[dict]:
    einbau, gewinde = spec["einbau"], spec.get("gewinde", {})
    if "referenz" in mp and mp["referenz"] not in einbau:
        return [_b(f"{pfad}.referenz", f"Einbaureferenz {mp['referenz']!r} fehlt unter einbau")]
    if "gewinde" in mp:
        g = gewinde.get(mp["gewinde"])
        if g is None:
            return [_b(f"{pfad}.gewinde", f"Gewindegruppe {mp['gewinde']!r} fehlt unter gewinde")]
        if mp["instanz"] > len(g["positionen"]):
            return [_b(f"{pfad}.instanz", f"{mp['gewinde']} hat nur {len(g['positionen'])} Positionen")]
    if "flaeche" in mp and _null(mp["flaeche"]["normale"]):
        return [_b(f"{pfad}.flaeche.normale", "Normale darf nicht der Nullvektor sein")]
    return []


def plausibel_befunde(spec: dict, pfad: Path | None = None) -> list[dict]:
    befunde = []
    if pfad is not None and (pfad.parent.name, pfad.stem) != (ordnername(spec["hersteller"]), dateiname(spec["bestellnummer"])):
        befunde.append(_b("(Datei)", f"Eintrag gehört nach {ordnername(spec['hersteller'])}/"
                                     f"{dateiname(spec['bestellnummer'])}.yaml (Hersteller und Bestellnummer)"))
    einbau = spec["einbau"]
    arten = {n: next(iter(e)) for n, e in einbau.items()}
    for n, e in einbau.items():
        art, w = next(iter(e.items()))
        stelle = f"einbau.{n}.{art}"
        if art == "zylinder" and "senkrecht_zu" in w and arten.get(w["senkrecht_zu"]) != "ebene":
            befunde.append(_b(f"{stelle}.senkrecht_zu", f"{w['senkrecht_zu']!r} ist keine ebene-Referenz dieses Eintrags"))
        if art == "ebene" and _null(w["normale"]):
            befunde.append(_b(f"{stelle}.normale", "Normale darf nicht der Nullvektor sein"))
        if art == "ebene_durch_achse" and arten.get(w["achse"]) != "zylinder":
            befunde.append(_b(f"{stelle}.achse", f"{w['achse']!r} ist keine zylinder-Referenz dieses Eintrags"))
    for g, w in spec.get("gewinde", {}).items():
        stelle = f"gewinde.{g}"
        if normmasse("gewinde", w["groesse"], "ISO") is None:
            befunde.append(_b(f"{stelle}.groesse", f"Gewinde {w['groesse']} nicht in swki/wissen/bohrungsnormen.yaml"))
        if w["gewindetiefe"] > w["tiefe"]:
            befunde.append(_b(f"{stelle}.gewindetiefe", "gewindetiefe darf nicht größer als tiefe sein"))
        if _null(w["normale"]):
            befunde.append(_b(f"{stelle}.normale", "Normale darf nicht der Nullvektor sein"))
        for k, p in enumerate(w["positionen"]):
            if any(math.dist(p, q) <= 1e-6 for q in w["positionen"][:k]):
                befunde.append(_b(f"{stelle}.positionen[{k}]", f"Position {k + 1} ist doppelt"))
    pr = spec.get("pruefung", {})
    for i, d in enumerate(pr.get("durchmesser_pruefen", [])):
        if "referenz" in d and arten.get(d["referenz"]) != "zylinder":
            befunde.append(_b(f"pruefung.durchmesser_pruefen[{i}].referenz",
                              f"{d['referenz']!r} ist keine zylinder-Referenz dieses Eintrags"))
    for i, m in enumerate(pr.get("masse_pruefen", [])):
        for s in ("von", "zu"):
            befunde += _messpunkt_befunde(m[s], f"pruefung.masse_pruefen[{i}].{s}", spec)
    for liste in ("durchmesser_pruefen", "masse_pruefen"):
        namen = [x["was"] for x in pr.get(liste, [])]
        for i, n in enumerate(namen):
            if n in namen[:i]:
                befunde.append(_b(f"pruefung.{liste}[{i}].was", f"was {n!r} ist doppelt"))
    return befunde


def eintrag_befunde(spec: dict, pfad: Path | None = None, wissen: Path = NORMTABELLEN) -> list[dict]:
    befunde = schema_befunde(spec, "kaufteil")
    if befunde:
        return befunde
    return plausibel_befunde(spec, pfad) + beleg_befunde(spec) + genormt_befunde(spec, wissen)


def lade_eintrag(pfad: Path) -> dict:
    """Lädt und prüft einen Katalogeintrag; wirft SpecFehler mit allen Befunden."""
    spec = lade_yaml(pfad)
    if befunde := eintrag_befunde(spec, pfad):
        raise SpecFehler(befunde)
    return spec


def hinweise_eintrag(spec: dict) -> list[dict]:
    """Hinweise (blockieren nie): Kennmaße ohne Beleg, keine belegten Kennmaße, Masse aus dem Material."""
    alle = kennmasse(spec)
    ergebnis = [{"art": "nicht_belegt", "pfad": p, "meldung": "Kennmaß ohne Beleg: wird geprüft, gilt im Bericht als "
                                                                "„nicht belegt“"} for p, ids in alle if not ids]
    if not any(ids for _, ids in alle):
        ergebnis.append({"art": "kennmasse_nicht_belegt", "pfad": "pruefung",
                         "meldung": "keine belegten Kennmaße: geprüft werden nur Import, Körperzahl, Volumen und "
                                    "Einbaureferenzen („Kennmaße nicht belegt“)"})
    if "masse" not in spec:
        ergebnis.append({"art": "masse_aus_material", "pfad": "masse",
                         "meldung": "keine Masse aus dem Datenblatt: die Masse wird aus dem Material geschätzt"})
    return ergebnis


def eigenschaften(spec: dict) -> dict[str, str]:
    """Eigenschaften im Teil (Spec 3c §5.3): Ersteller, Benennung, Hersteller, Bestellnummer, dazu die des Eintrags."""
    return {"Ersteller": ERSTELLER, "Benennung": spec["benennung"], "Hersteller": spec["hersteller"],
            "Bestellnummer": spec["bestellnummer"], **spec.get("eigenschaften", {})}


def angaben_fuer_bericht(spec: dict) -> dict[str, str]:
    """Masse und Belegstand eines Kaufteils für Protokoll und Bericht der Baugruppe (Spec 3c §8.4)."""
    masse = f"{spec['masse']['kg']:g} kg (Datenblatt)" if "masse" in spec else "aus Material geschätzt"
    belegt = any(ids for _, ids in kennmasse(spec))
    return {"masse": masse, "kennmasse": "belegt" if belegt else "nicht belegt"}


def validieren(pfad: Path) -> dict:
    spec = lade_eintrag(pfad)
    return {"gueltig": True, "spec": str(pfad), "art": "kaufteil",
            "schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "pruefsumme": pruefsumme(spec),
            "hinweise": hinweise_eintrag(spec)}


def freigeben(pfad: Path) -> dict:
    """Freigabe des ganzen Eintrags (Spec 3c §4.6) – nur nach ausdrücklichem OK des Nutzers."""
    spec = lade_eintrag(pfad)
    return {"spec": str(pfad), "art": "kaufteil", "kopie": str(kopie_pfad(pfad)), **spec_freigeben(pfad, spec)}
```

In `swki/spec/freigabe.py` ersetzen:

```python
Baugruppen: zusätzlich die Prüfsummen der Teil-Specs (Spec 3b §6).
Die Kopie
```

durch:

```python
Baugruppen: zusätzlich die Prüfsummen der Teil-Specs (Spec 3b §6). Kaufteile: der ganze Eintrag (Spec 3c §4.6; ein
Kaufteil hat keinen Bauweg).
Die Kopie
```

In `swki/spec/freigabe.py` ersetzen:

```python
    felder = PRUEF_FELDER_BAUGRUPPE if spec.get("art") == "baugruppe" else PRUEF_FELDER
    kern = {feld: spec.get(feld) for feld in felder}
```

durch:

```python
    felder = PRUEF_FELDER_BAUGRUPPE if spec.get("art") == "baugruppe" else PRUEF_FELDER
    kern = dict(spec) if spec.get("art") == "kaufteil" else {feld: spec.get(feld) for feld in felder}
```

In `swki/spec/befehle.py` ersetzen:

```python

        return validieren(pfad)
    spec = lade_spec(pfad)
    return {
```

durch:

```python

        return validieren(pfad)
    if art_der_datei(pfad) == "kaufteil":
        from swki.kaufteile.eintrag import validieren as validieren_kaufteil  # spät importiert (Kreisimport)

        return validieren_kaufteil(pfad)
    spec = lade_spec(pfad)
    return {
```

In `swki/spec/befehle.py` ersetzen:

```python

        return freigeben_baugruppe(pfad)
    spec = lade_spec(pfad)
    return {"spec": str(pfad), "kopie": str(kopie_pfad(pfad)), **freigeben(pfad, spec)}
```

durch:

```python

        return freigeben_baugruppe(pfad)
    if art_der_datei(pfad) == "kaufteil":
        from swki.kaufteile.eintrag import freigeben as freigeben_kaufteil  # spät importiert (Kreisimport)

        return freigeben_kaufteil(pfad)
    spec = lade_spec(pfad)
    return {"spec": str(pfad), "kopie": str(kopie_pfad(pfad)), **freigeben(pfad, spec)}
```

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile tests\test_konfig.py tests\test_rechner.py`
Expected: `35 passed`. Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **874 passed, 133 deselected**.

- [ ] **Step 5: Commit**

```powershell
git add schema/kaufteil.schema.json swki/kaufteile swki/konfig.py swki/rechner.py config/rechner.beispiel.yaml swki/spec/freigabe.py swki/spec/befehle.py tests/kaufteile tests/test_konfig.py tests/test_rechner.py
git commit -m "kaufteile: Katalog, Eintrag art: kaufteil, Belegregel, Schutzregel, Weiche validieren/freigeben (Stufe 3c, Task 3)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Ortung, Bewertung, Diagnose-Übersicht, Spitzenmessung (ohne SolidWorks)

**Files:**
- Create: `swki/kaufteile/ortung.py`, `swki/kaufteile/bewertung.py`, `swki/kaufteile/diagnose.py`
- Modify: `swki/speicher.py`
- Test: `tests/kaufteile/test_ortung.py`, `tests/kaufteile/test_bewertung.py`, `tests/kaufteile/test_diagnose.py`,
  `tests/test_speicher.py`

**Interfaces:**
- Consumes: `swki.compiler.anker` (`Flaeche`, `AnkerFehler`, `punkt_achse_abstand`, `skalar`, `laenge`, `differenz`),
  `swki.pruefung.bewertung` (`eintrag`, `beschreibung`, `messpunkt_schluessel`), `swki.pruefung.geometrie` (`Messgeometrie`,
  `abstand`, `NichtMessbar`), `swki.compiler.eigenschaften.material_passt`, `swki.kaufteile.eintrag.eigenschaften` (Task 3).
- Produces:
  - `swki.kaufteile.ortung`: `TOL_DURCHMESSER`, `TOL_WINKEL_GRAD`, `ABSTAND_ACHSE_MIN`, `Ortung(name, art, flaeche, ist,
    abweichung)`, `einheit`, `kreuz`, `winkel_grad`, `kandidaten(flaechen, art, punkt, tol)`, `orte_zylinder(flaechen, name, w,
    tol)`, `orte_ebene(…)`, `ebene_durch_achse(name, achse_punkt, achse_richtung, nahe)`, `nenn_durchmesser(groesse)`,
    `orte_gewinde(flaechen, gruppe, w, tol) -> list[Ortung]` (`ist`: `durchmesser`, `modell`, `achse`, `punkt`).
  - `swki.kaufteile.bewertung`: `KaufteilMesswerte(rebuild_fehler, koerper, flaechenkoerper, koerperfehler, box, volumen,
    masse_kg, masse_ueberschrieben, material, eigenschaften, einbau, gewinde, messpunkte, durchmesser)`,
    `bewerte_kaufteil(spec, m) -> {"bestanden", "pruefungen", "maengel"}`, `NICHT_BELEGT`.
  - `swki.kaufteile.diagnose.uebersicht(saetze, grenze=50) -> {"zylinder", "ebenen", "zylinder_gesamt", "ebenen_gesamt"}`.
  - `swki.speicher.Spitzenmessung(pid, takt_s=0.5, messen=privat_mb)` (Kontext; `.vorher`, `.spitze`, `.nachher`, `als_dict()`).

- [ ] **Step 1: Tests schreiben**

`tests/kaufteile/test_ortung.py` anlegen:

```python
import pytest

from swki.compiler.anker import AnkerFehler, Flaeche
from swki.kaufteile.ortung import (ebene_durch_achse, kandidaten, nenn_durchmesser, orte_ebene, orte_gewinde,
                                   orte_zylinder)

Y = (0.0, 1.0, 0.0)


def _zyl(punkt, achse, radius, abstand=0.0):
    return Flaeche("zylinder", punkt, achse=achse, radius=radius, abstand=abstand)


def _ebene(punkt, normale, abstand=0.0):
    return Flaeche("ebene", punkt, normale=normale, abstand=abstand)


def test_zylinder_gleicher_achse_gilt_als_eine_flaeche():
    welle, bohrung = _zyl((0, -10, 0), Y, 5.0), _zyl((0, 2, 0), (0, -1, 0), 5.0, 0.05)
    o = orte_zylinder([welle, bohrung, _zyl((30, 0, 0), Y, 5.0, 4.0)], "EINBAU_ACHSE",
                      {"nahe": [5, -15, 0], "durchmesser": 10}, 0.1)
    assert o.flaeche is welle and o.abweichung is None and o.ist["durchmesser"] == 10.0


def test_zylinder_gegenprobe_und_fehler():
    o = orte_zylinder([_zyl((0, 0, 0), Y, 6.0)], "EINBAU_ACHSE", {"nahe": [6, 0, 0], "durchmesser": 10}, 0.1)
    assert o.abweichung == "Ø 12.0000 statt 10"
    with pytest.raises(AnkerFehler) as e:
        orte_zylinder([_zyl((0, 0, 0), Y, 6.0, 0.4)], "EINBAU_ACHSE", {"nahe": [6, 0, 0], "durchmesser": 12}, 0.1)
    assert e.value.code == "REFERENZ_NICHT_GEFUNDEN" and "nächste 0.400 mm" in str(e.value)
    with pytest.raises(AnkerFehler) as e:
        orte_zylinder([_zyl((0, 0, 0), Y, 6.0), _zyl((0, 0, 0), Y, 8.0, 0.05)], "EINBAU_ACHSE",
                      {"nahe": [6, 0, 0], "durchmesser": 12}, 0.1)
    assert e.value.code == "REFERENZ_MEHRDEUTIG"


def test_ebene_mit_normale_unter_mehreren():
    vorne, hinten = _ebene((0, 0, 0), (0, -1, 0)), _ebene((0, 0, 0), (0, 1, 0), 0.0)
    o = orte_ebene([hinten, vorne], "EINBAU_FLANSCH", {"nahe": [25, 0, 25], "normale": [0, -1, 0]}, 0.1)
    assert o.flaeche is vorne and o.abweichung is None


def test_ebene_gegenprobe_normale():
    o = orte_ebene([_ebene((0, 0, 0), Y)], "EINBAU_FLANSCH", {"nahe": [25, 0, 25], "normale": [0, -1, 0]}, 0.1)
    assert o.abweichung == "Normale [0.0, 1.0, 0.0] statt [0, -1, 0] (180.000°)"


def test_ebene_mehrdeutig():
    with pytest.raises(AnkerFehler) as e:
        orte_ebene([_ebene((0, 0, 0), Y), _ebene((0, 0.08, 0), Y, 0.08)], "E", {"nahe": [0, 0, 0], "normale": [0, 1, 0]}, 0.1)
    assert e.value.code == "REFERENZ_MEHRDEUTIG"


def test_ebene_durch_achse():
    o = ebene_durch_achse("EINBAU_DREHLAGE", (0, 0, 0), (0, 2, 0), (0, 0, 25))
    assert o.abweichung is None and o.ist["normale"] == (1.0, 0.0, 0.0) and o.ist["abstand_achse"] == 25.0
    assert ebene_durch_achse("E", (0, 0, 0), Y, (0, 7, 0.5)).abweichung.startswith("nahe liegt 0.500 mm von der Achse")


def test_gewinde_kernloch_nenn_und_falsch():
    w = {"groesse": "M5", "normale": [0, -1, 0], "positionen": [[21, 0, 21], [-21, 0, 21], [0, 0, 30]]}
    flaechen = [_zyl((21, 3, 21), Y, 2.1), _zyl((21, 3, 21), Y, 5.0), _zyl((-21, 5, 21), (0, -1, 0), 2.5),
                _zyl((0, 0, 30), Y, 3.0)]
    a, b, c = orte_gewinde(flaechen, "flansch", w, 0.1)
    assert (a.name, a.ist["modell"], a.abweichung) == ("flansch.1", "kernloch", None)
    assert b.ist["modell"] == "nenn" and c.ist["modell"] is None
    assert c.abweichung == "Ø 6.0000: weder Kernloch 4.2 noch Nenn-Ø 5 (M5)"
    with pytest.raises(AnkerFehler):
        orte_gewinde(flaechen, "flansch", {**w, "positionen": [[50, 0, 0]]}, 0.1)
    assert nenn_durchmesser("M10x1") == 10.0


def test_kandidaten_vorauswahl():
    flaechen = [_ebene((0, 0, 0), (0, -1, 0)), _ebene((0, 5, 0), (0, 1, 0)), _zyl((0, 0, 0), Y, 5.0),
                _zyl((0, 0, 0), Y, 8.0)]
    assert kandidaten(flaechen, "ebene", (25, 0.05, 25), 0.1) == [flaechen[0]]
    assert kandidaten(flaechen, "zylinder", (0, 40, 5.05), 0.1) == [flaechen[2]]
```

`tests/kaufteile/test_bewertung.py` anlegen:

```python
from dataclasses import replace

from swki.kaufteile.bewertung import KaufteilMesswerte, bewerte_kaufteil
from swki.kaufteile.eintrag import eigenschaften
from swki.pruefung.bewertung import messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from tests.kaufteile.beispiel import EINTRAG, L, kopie

Y = (0.0, 1.0, 0.0)


def _messwerte() -> KaufteilMesswerte:
    """Messwerte, wie sie das Muster ohne Mangel liefert."""
    achse = Messgeometrie("achse", (0.0, 0.0, 0.0), Y)
    flansch = Messgeometrie("ebene", (0.0, 0.0, 0.0), (0.0, -1.0, 0.0))
    drehlage = Messgeometrie("ebene", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    pr = EINTRAG["pruefung"]
    mp = {
        messpunkt_schluessel(pr["masse_pruefen"][0]["von"]): flansch,
        messpunkt_schluessel(pr["masse_pruefen"][0]["zu"]): Messgeometrie("ebene", (0.0, -25.0, 0.0), (0.0, -1.0, 0.0)),
        messpunkt_schluessel(pr["masse_pruefen"][1]["von"]): Messgeometrie("achse", (L, 0.0, L), Y),
        messpunkt_schluessel(pr["masse_pruefen"][1]["zu"]): Messgeometrie("achse", (-L, 0.0, L), Y),
    }
    gewinde = {f"flansch.{i}": {"ist": {"durchmesser": 4.2, "modell": "kernloch"}, "abweichung": None} for i in range(1, 5)}
    return KaufteilMesswerte(
        rebuild_fehler=[], koerper=2, flaechenkoerper=0, koerperfehler={"1": 0, "2": 0},
        box=[-30, -25, -30, 30, 82, 30], volumen=220010.0, masse_kg=1.2, masse_ueberschrieben=True,
        material="1.0038 (S235JRG2)", eigenschaften=eigenschaften(EINTRAG),
        einbau={
            "EINBAU_ACHSE": {"ist": {"durchmesser": 10.0, "achse": Y, "punkt": (0.0, -10.0, 0.0)}, "abweichung": None,
                             "bezug": achse},
            "EINBAU_FLANSCH": {"ist": {"normale": (0.0, -1.0, 0.0), "punkt": (25.0, 0.0, 25.0)}, "abweichung": None,
                               "bezug": flansch},
            "EINBAU_DREHLAGE": {"ist": {"abstand_achse": 25.0, "normale": (1.0, 0.0, 0.0)}, "abweichung": None,
                                "bezug": drehlage},
        },
        gewinde=gewinde, messpunkte=mp,
        durchmesser={"Wellen-Ø": {"durchmesser": 10.0, "achse": achse, "referenz": achse},
                     "Zentrierbund-Ø": {"durchmesser": 40.0, "achse": achse, "referenz": achse}},
    )


def _ids(bericht, ok) -> list[str]:
    return [e["id"] for e in bericht["pruefungen"] if e["ok"] is ok]


def test_muster_besteht():
    b = bewerte_kaufteil(EINTRAG, _messwerte())
    assert b["maengel"] == [] and b["bestanden"] is True
    assert _ids(b, True) == ["rebuild", "import", "koerper", "huellquader", "volumen", "einbau:EINBAU_ACHSE",
                             "einbau:EINBAU_FLANSCH", "einbau:EINBAU_DREHLAGE", "gewinde:flansch", "durchmesser:Wellen-Ø",
                             "durchmesser:Zentrierbund-Ø", "mass:Wellenüberstand", "mass:Lochabstand", "material",
                             "eigenschaften", "masse"]
    huelle = next(e for e in b["pruefungen"] if e["id"] == "huellquader")
    assert huelle["ist"] == [60, 107, 60] and huelle["beleg"] == ["d1"]
    flansch = next(e for e in b["pruefungen"] if e["id"] == "einbau:EINBAU_FLANSCH")
    assert flansch["bezug"]["richtung"] == [0.0, -1.0, 0.0]


def test_koerper_import_und_volumen():
    m = replace(_messwerte(), koerper=1, flaechenkoerper=1, koerperfehler={"1": 2}, volumen=230000.0)
    assert {"import", "koerper", "volumen"} <= set(_ids(bewerte_kaufteil(EINTRAG, m), False))


def test_gegenprobe_und_lage_der_referenzen():
    m = _messwerte()
    m.einbau["EINBAU_ACHSE"]["abweichung"] = "Ø 12.0000 statt 10"
    m.einbau["EINBAU_DREHLAGE"]["bezug"] = Messgeometrie("ebene", (0.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    b = bewerte_kaufteil(EINTRAG, m)
    assert _ids(b, False) == ["einbau:EINBAU_ACHSE", "einbau:EINBAU_DREHLAGE"]
    texte = [x["beschreibung"] for x in b["maengel"]]
    assert texte[0] == "einbau:EINBAU_ACHSE: Ø 12.0000 statt 10"
    assert "enthält EINBAU_ACHSE nicht" in texte[1]


def test_senkrecht_zu():
    m = _messwerte()
    m.einbau["EINBAU_FLANSCH"]["bezug"] = Messgeometrie("ebene", (0.0, 0.0, 0.0), (0.0, -0.9998, 0.02))
    m.einbau["EINBAU_FLANSCH"]["ist"]["normale"] = (0.0, -0.9998, 0.02)
    b = bewerte_kaufteil(EINTRAG, m)
    assert "Achse nicht senkrecht zu EINBAU_FLANSCH" in next(x for x in b["maengel"]
                                                             if x["pruefung"] == "einbau:EINBAU_ACHSE")["beschreibung"]


def test_einbau_fehlt_und_gewinde_falsch():
    m = _messwerte()
    m.einbau["EINBAU_FLANSCH"] = "REFERENZ_NICHT_GEFUNDEN: keine ebene Fläche"
    m.gewinde["flansch.3"] = {"ist": {"durchmesser": 6.0, "modell": None}, "abweichung": "Ø 6.0000: weder …"}
    b = bewerte_kaufteil(EINTRAG, m)
    assert {"einbau:EINBAU_FLANSCH", "gewinde:flansch"} <= set(_ids(b, False))


def test_masse_ohne_ueberschreibung_und_ohne_angabe():
    assert "masse" in _ids(bewerte_kaufteil(EINTRAG, replace(_messwerte(), masse_ueberschrieben=False)), False)
    ohne = kopie()
    del ohne["masse"]
    masse = next(e for e in bewerte_kaufteil(ohne, _messwerte())["pruefungen"] if e["id"] == "masse")
    assert masse["ok"] is None and masse["hinweis"] == "Masse aus Material geschätzt"


def test_nicht_belegte_kennmasse_im_bericht():
    spec = kopie()
    del spec["pruefung"]["masse_pruefen"][0]["beleg"]
    mass = next(e for e in bewerte_kaufteil(spec, _messwerte())["pruefungen"] if e["id"] == "mass:Wellenüberstand")
    assert mass["ok"] is True and mass["beleg"] == "nicht belegt"


def test_messpunkt_fehlt_und_eigenschaften():
    m = _messwerte()
    m.messpunkte.pop(next(iter(m.messpunkte)))
    m.eigenschaften = {**m.eigenschaften, "Hersteller": "anders"}
    assert {"mass:Wellenüberstand", "eigenschaften"} <= set(_ids(bewerte_kaufteil(EINTRAG, m), False))
```

`tests/kaufteile/test_diagnose.py` anlegen:

```python
from swki.kaufteile.diagnose import uebersicht


def _zyl(punkt, achse, radius, auf, flaeche):
    return {"art": "zylinder", "punkt": punkt, "achse": achse, "radius": radius, "auf": auf, "flaeche_mm2": flaeche}


def _ebene(punkt, normale, auf, flaeche):
    return {"art": "ebene", "punkt": punkt, "normale": normale, "auf": auf, "flaeche_mm2": flaeche}


def test_zylinder_gleicher_achse_zusammengefasst():
    saetze = [_zyl((0, -10, 0), (0, 1, 0), 5.0, (5, -10, 0), 200.0),
              _zyl((0, 3, 0), (0, -1, 0), 5.0, (0, 3, 5), 300.0),   # gleiche Achse, Gegenrichtung
              _zyl((21.2, 0, 21.2), (0, 1, 0), 2.1, (23.3, 5, 21.2), 50.0)]
    u = uebersicht(saetze)
    assert u["zylinder_gesamt"] == 2
    welle = u["zylinder"][0]
    assert welle == {"durchmesser": 10.0, "achspunkt": [0.0, 0.0, 0.0], "richtung": [0.0, 1.0, 0.0],
                     "nahe": [0.0, 3.0, 5.0], "flaechen": 2, "flaeche_mm2": 500.0}
    assert u["zylinder"][1]["durchmesser"] == 4.2


def test_ebenen_nach_groesse_und_grenze():
    saetze = [_ebene((0, 0, 0), (0, -1, 0), (25, 0, 25), 1000.0), _ebene((0, 0, 9), (0, -1, 0), (-25, 0, 25), 800.0),
              _ebene((0, -25, 0), (0, -1, 0), (0, -25, 0), 78.5), _ebene((30, 0, 0), (1, 0, 0), (30, 5, 0), 900.0)]
    u = uebersicht(saetze, grenze=2)
    assert u["ebenen_gesamt"] == 3
    assert [e["flaeche_mm2"] for e in u["ebenen"]] == [1800.0, 900.0]
    assert u["ebenen"][0] == {"normale": [0.0, -1.0, 0.0], "abstand": 0.0, "nahe": [25.0, 0.0, 25.0], "flaechen": 2,
                              "flaeche_mm2": 1800.0}
```

In `tests/test_speicher.py` ersetzen:

```python
import os

from swki.speicher import privat_mb
```

durch:

```python
import os

from swki.speicher import Spitzenmessung, privat_mb
```

In `tests/test_speicher.py` ersetzen:

```python
    assert 1 < privat_mb(os.getpid()) < 100_000
```

durch:

```python
    assert 1 < privat_mb(os.getpid()) < 100_000


def test_spitzenmessung_mit_attrappe():
    werte = iter([100.0, 900.0, 400.0] + [300.0] * 1000)
    with Spitzenmessung(1, takt_s=0.001, messen=lambda pid: next(werte)) as s:
        while s.spitze < 900.0:
            pass
    assert s.vorher == 100.0 and s.spitze == 900.0 and 300.0 <= s.nachher <= 400.0
    assert s.als_dict() == {"vorher": 100.0, "spitze": 900.0, "nachher": s.nachher}
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile\test_ortung.py tests\kaufteile\test_bewertung.py tests\kaufteile\test_diagnose.py tests\test_speicher.py`
Expected: FAIL – `4 errors` (`ModuleNotFoundError: No module named 'swki.kaufteile.ortung'`).

- [ ] **Step 3: Umsetzen**

`swki/kaufteile/ortung.py` anlegen:

```python
"""Einbaureferenzen und Gewindepositionen in fremder Geometrie orten und gegenprüfen (Spec 3c §4.2, §4.3).

Reine Geometrie auf den Flächen aller Körper (swki.compiler.anker.Flaeche, mm). Für zylinder und ebene setzt die
SolidWorks-Schicht vorher .abstand jeder Fläche zum Punkt `nahe` (swki.compiler.topologie.mit_abstand, echter Abstand
zur begrenzten Fläche); Gewindepositionen brauchen nur die Achslage."""

import math
from dataclasses import dataclass, field

from swki.compiler.anker import AnkerFehler, Flaeche, Vektor, differenz, laenge, punkt_achse_abstand, skalar
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN
from swki.spec.normen import normmasse

TOL_DURCHMESSER = 0.01   # mm, Gegenprobe Ø (Spec 3c §4.2)
TOL_WINKEL_GRAD = 0.01   # Gegenprobe Normale, Lage der Referenzen zueinander
ABSTAND_ACHSE_MIN = 1.0  # mm: ebene_durch_achse braucht einen Punkt neben der Achse
_GLEICH_MM = 1e-4


@dataclass
class Ortung:
    name: str                 # EINBAU_* bzw. "<gruppe>.<i>"
    art: str                  # zylinder | ebene | ebene_durch_achse | gewinde
    flaeche: Flaeche | None   # geortete Fläche (ebene_durch_achse: None)
    ist: dict = field(default_factory=dict)  # gemessene Werte (durchmesser, normale, punkt, modell …)
    abweichung: str | None = None            # Gegenprobe verfehlt; None = bestanden


def einheit(v: Vektor) -> Vektor:
    n = laenge(v)
    return tuple(c / n for c in v)


def kreuz(a: Vektor, b: Vektor) -> Vektor:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def winkel_grad(a: Vektor, b: Vektor) -> float:
    """Winkel zwischen zwei Richtungen (0 … 180°)."""
    c = skalar(einheit(a), einheit(b))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def kandidaten(flaechen: list[Flaeche], art: str, punkt: Vektor, tol_mm: float) -> list[Flaeche]:
    """Flächen der Art (ebene | zylinder), deren unendliche Fläche höchstens tol_mm vom Punkt liegt: Vorauswahl, bevor
    die SolidWorks-Schicht den echten Abstand misst (ein COM-Aufruf je Fläche)."""
    if art == "ebene":
        return [f for f in flaechen if f.art == "ebene" and abs(skalar(differenz(punkt, f.punkt), f.normale)) <= tol_mm]
    return [f for f in flaechen if f.art == "zylinder"
            and abs(punkt_achse_abstand(punkt, f.punkt, einheit(f.achse)) - f.radius) <= tol_mm]


def _innerhalb(kandidaten: list[Flaeche], tol_mm: float, was: str, punkt) -> list[Flaeche]:
    if not kandidaten:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine {was} innerhalb {tol_mm:g} mm um {list(punkt)}")
    innen = [f for f in kandidaten if f.abstand <= tol_mm]
    if not innen:
        naechste = min(f.abstand for f in kandidaten)
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine {was} innerhalb {tol_mm:g} mm um {list(punkt)} "
                                                   f"(nächste {naechste:.3f} mm)")
    return innen


def orte_zylinder(flaechen: list[Flaeche], name: str, w: dict, tol_mm: float) -> Ortung:
    """Zylinderfläche durch `nahe`; Flächen gleicher Achse und gleichen Radius (geteilter Mantel, Welle in Bohrung)
    gelten als eine. Gegenprobe Ø."""
    innen = _innerhalb([f for f in flaechen if f.art == "zylinder"], tol_mm, "Zylinderfläche", w["nahe"])
    erste = innen[0]
    for f in innen[1:]:
        gleich = (abs(f.radius - erste.radius) <= _GLEICH_MM and abs(abs(skalar(einheit(f.achse), einheit(erste.achse))) - 1) < 1e-9
                  and punkt_achse_abstand(f.punkt, erste.punkt, einheit(erste.achse)) <= _GLEICH_MM)
        if not gleich:
            raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{name}: {len(innen)} verschiedene Zylinderflächen innerhalb "
                                                   f"{tol_mm:g} mm um {list(w['nahe'])}")
    d = 2 * erste.radius
    abweichung = None if abs(d - w["durchmesser"]) <= TOL_DURCHMESSER else f"Ø {d:.4f} statt {w['durchmesser']:g}"
    return Ortung(name, "zylinder", erste, {"durchmesser": round(d, 6), "achse": einheit(erste.achse),
                                            "punkt": erste.punkt}, abweichung)


def orte_ebene(flaechen: list[Flaeche], name: str, w: dict, tol_mm: float) -> Ortung:
    """Ebene Fläche durch `nahe`. Unter mehreren nahen Flächen zählen die mit passender Normale (zwei Körper können
    sich in einer Ebene berühren); passt keine, ist die nächste mit abweichender Normale das Ergebnis der Gegenprobe."""
    innen = _innerhalb([f for f in flaechen if f.art == "ebene"], tol_mm, "ebene Fläche", w["nahe"])
    soll = einheit(tuple(w["normale"]))
    passend = [f for f in innen if winkel_grad(f.normale, soll) <= TOL_WINKEL_GRAD]
    ebenen = {round(skalar(f.punkt, soll), 4) for f in passend}
    if len(ebenen) > 1:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{name}: {len(passend)} ebene Flächen mit Normale {list(w['normale'])} "
                                               f"in verschiedenen Ebenen um {list(w['nahe'])}")
    f = passend[0] if passend else min(innen, key=lambda x: x.abstand)
    abweichung = None if passend else (f"Normale {[round(c, 4) for c in f.normale]} statt {list(w['normale'])} "
                                       f"({winkel_grad(f.normale, soll):.3f}°)")
    return Ortung(name, "ebene", f, {"normale": tuple(round(c, 6) for c in f.normale), "punkt": f.punkt}, abweichung)


def ebene_durch_achse(name: str, achse_punkt: Vektor, achse_richtung: Vektor, nahe: Vektor) -> Ortung:
    """Ebene, die die Achse enthält und durch `nahe` geht: Normale = Achse × (nahe − Achspunkt)."""
    abstand = punkt_achse_abstand(tuple(nahe), achse_punkt, einheit(achse_richtung))
    ist = {"abstand_achse": round(abstand, 6)}
    if abstand <= ABSTAND_ACHSE_MIN:
        return Ortung(name, "ebene_durch_achse", None, ist,
                      f"nahe liegt {abstand:.3f} mm von der Achse (mindestens {ABSTAND_ACHSE_MIN:g} mm)")
    ist["normale"] = einheit(kreuz(einheit(achse_richtung), differenz(tuple(nahe), achse_punkt)))
    return Ortung(name, "ebene_durch_achse", None, ist)


def nenn_durchmesser(groesse: str) -> float:
    """"M5" → 5.0, "M10x1" → 10.0."""
    return float(groesse[1:].lower().split("x")[0])


def orte_gewinde(flaechen: list[Flaeche], gruppe: str, w: dict, tol_mm: float) -> list[Ortung]:
    """Je Position die Zylinderfläche, deren Achse durch den Eintrittspunkt läuft und parallel zu `normale` ist
    (der kleinste Radius gewinnt, wie bei Bohrungen mit Senkung); Gegenprobe Ø = Kernloch (modell kernloch) oder
    Nenn-Ø (modell nenn)."""
    n = einheit(tuple(w["normale"]))
    kern = normmasse("gewinde", w["groesse"], "ISO")["kernloch"]
    nenn = nenn_durchmesser(w["groesse"])
    ergebnis = []
    for i, p in enumerate(w["positionen"], start=1):
        name = f"{gruppe}.{i}"
        passend = [f for f in flaechen if f.art == "zylinder" and abs(abs(skalar(einheit(f.achse), n)) - 1) < 1e-6
                   and punkt_achse_abstand(tuple(p), f.punkt, einheit(f.achse)) <= tol_mm]
        if not passend:
            raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Gewinde {name}: keine Zylinderfläche mit Achse durch {list(p)}")
        f = min(passend, key=lambda x: x.radius)
        d = 2 * f.radius
        modell = "kernloch" if abs(d - kern) <= TOL_DURCHMESSER else "nenn" if abs(d - nenn) <= TOL_DURCHMESSER else None
        abweichung = None if modell else f"Ø {d:.4f}: weder Kernloch {kern:g} noch Nenn-Ø {nenn:g} ({w['groesse']})"
        ergebnis.append(Ortung(name, "gewinde", f, {"durchmesser": round(d, 6), "modell": modell,
                                                    "achse": einheit(f.achse), "punkt": f.punkt}, abweichung))
    return ergebnis
```

`swki/kaufteile/bewertung.py` anlegen:

```python
"""Bewertung eines aufgenommenen Kaufteils (Spec 3c §6.3) ohne SolidWorks: Messwerte → Prüfungen und Mängel.

Prüfungs-IDs: rebuild, import, koerper, huellquader, volumen, einbau:<name>, gewinde:<gruppe>, durchmesser:<was>,
mass:<was>, material, eigenschaften, masse. Kennmaße tragen ihren Beleg (Liste der Beleg-IDs) oder "nicht belegt"."""

import math
from dataclasses import dataclass, field

from swki.compiler.anker import punkt_achse_abstand
from swki.compiler.eigenschaften import material_passt
from swki.kaufteile.eintrag import eigenschaften
from swki.kaufteile.ortung import TOL_WINKEL_GRAD, winkel_grad
from swki.pruefung.bewertung import beschreibung, eintrag, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand

TOL_HUELLQUADER = 0.1      # mm, Vorgabe (Spec 3c §4.4)
TOL_MASS = 0.01            # mm, Vorgabe für durchmesser_pruefen und masse_pruefen
TOL_VOLUMEN_PROZENT = 0.01  # Fingerabdruck: gleiche Datei, gleicher Import
TOL_MASSE_RELATIV = 1e-6   # überschriebene Masse
TOL_LAGE_MM = 0.01         # Bezugsgeometrie auf der georteten Fläche
NICHT_BELEGT = "nicht belegt"


@dataclass
class KaufteilMesswerte:
    rebuild_fehler: list[str]
    koerper: int                       # Volumenkörper
    flaechenkoerper: int
    koerperfehler: dict[str, int]      # Körper (1 …) → Anzahl Fehler laut IBody2.Check3
    box: list[float]                   # [xmin, ymin, zmin, xmax, ymax, zmax] in mm
    volumen: float                     # mm³
    masse_kg: float
    masse_ueberschrieben: bool
    material: str
    eigenschaften: dict[str, str]
    einbau: dict = field(default_factory=dict)       # Name → {"ist", "abweichung", "bezug": Messgeometrie} | Fehlertext
    gewinde: dict = field(default_factory=dict)      # "<gruppe>.<i>" → {"ist", "abweichung"} | Fehlertext
    messpunkte: dict = field(default_factory=dict)   # messpunkt_schluessel → Messgeometrie | Fehlertext
    durchmesser: dict = field(default_factory=dict)  # was → {"durchmesser", "achse", "referenz"?} | Fehlertext


def _beleg(daten: dict) -> list | str:
    return daten.get("beleg") or NICHT_BELEGT


def _parallel(a, b) -> float:
    """Winkel zwischen zwei Geraden (0 … 90°), Richtung egal."""
    w = winkel_grad(a, b)
    return min(w, 180.0 - w)


def _punkt_ebene(punkt, ebene: Messgeometrie) -> float:
    return abstand(Messgeometrie("punkt", tuple(punkt)), ebene)


def _einbau_fehler(art: str, soll: dict, messung: dict, bezug: Messgeometrie, alle: dict) -> list[str]:
    ist = messung.get("ist", {})
    fehler = []
    if art == "zylinder":
        if _parallel(bezug.richtung, ist["achse"]) > TOL_WINKEL_GRAD or \
                punkt_achse_abstand(bezug.punkt, ist["punkt"], ist["achse"]) > TOL_LAGE_MM:
            fehler.append("Bezugsachse liegt nicht auf der Zylinderachse")
        if "senkrecht_zu" in soll:
            andere = alle.get(soll["senkrecht_zu"])
            if not isinstance(andere, dict) or not isinstance(andere.get("bezug"), Messgeometrie):
                fehler.append(f"{soll['senkrecht_zu']} fehlt für senkrecht_zu")
            elif (w := _parallel(bezug.richtung, andere["bezug"].richtung)) > TOL_WINKEL_GRAD:
                fehler.append(f"Achse nicht senkrecht zu {soll['senkrecht_zu']} ({w:.3f}° Abweichung)")
    elif art == "ebene":
        if _parallel(bezug.richtung, ist["normale"]) > TOL_WINKEL_GRAD or _punkt_ebene(ist["punkt"], bezug) > TOL_LAGE_MM:
            fehler.append("Bezugsebene liegt nicht auf der Fläche")
    else:
        achse = alle.get(soll["achse"])
        if not isinstance(achse, dict) or not isinstance(achse.get("bezug"), Messgeometrie):
            return [f"{soll['achse']} fehlt für ebene_durch_achse"]
        a = achse["bezug"]
        if abs(90.0 - winkel_grad(bezug.richtung, a.richtung)) > TOL_WINKEL_GRAD or _punkt_ebene(a.punkt, bezug) > TOL_LAGE_MM:
            fehler.append(f"Bezugsebene enthält {soll['achse']} nicht")
        if _punkt_ebene(soll["nahe"], bezug) > TOL_LAGE_MM:
            fehler.append("Bezugsebene geht nicht durch nahe")
    return fehler


def _einbau(name: str, w: dict, m: KaufteilMesswerte) -> dict:
    pid = f"einbau:{name}"
    messung = m.einbau.get(name, "Einbaureferenz nicht angelegt")
    if isinstance(messung, str):
        return eintrag(pid, False, hinweis=messung, knoten=[name])
    art, soll = next(iter(w.items()))
    fehler = [messung["abweichung"]] if messung.get("abweichung") else []
    bezug = messung.get("bezug")
    daten = {"ist": {k: v for k, v in messung.get("ist", {}).items() if k not in ("achse", "punkt")}}
    erwartet = "achse" if art == "zylinder" else "ebene"
    if not isinstance(bezug, Messgeometrie) or bezug.art != erwartet:
        fehler.append(f"Bezugsgeometrie ist keine {erwartet}")
    else:
        daten["bezug"] = {"punkt": [round(c, 4) for c in bezug.punkt], "richtung": [round(c, 6) for c in bezug.richtung]}
        if not fehler:
            fehler += _einbau_fehler(art, soll, messung, bezug, m.einbau)
    if fehler:
        daten["hinweis"] = "; ".join(fehler)
    return eintrag(pid, not fehler, **daten, knoten=[name])


def _gewinde(gruppe: str, w: dict, m: KaufteilMesswerte) -> dict:
    ist, fehler = {}, []
    for i in range(1, len(w["positionen"]) + 1):
        messung = m.gewinde.get(f"{gruppe}.{i}", "Position nicht geortet")
        if isinstance(messung, str):
            fehler.append(f"{i}: {messung}")
            continue
        ist[str(i)] = {k: v for k, v in messung["ist"].items() if k in ("durchmesser", "modell")}
        if messung.get("abweichung"):
            fehler.append(f"{i}: {messung['abweichung']}")
    daten = {"ist": ist, "beleg": _beleg(w)}
    if fehler:
        daten["hinweis"] = "; ".join(fehler)
    return eintrag(f"gewinde:{gruppe}", not fehler, **daten, knoten=[gruppe])


def _masse_pruefen(pr: dict, m: KaufteilMesswerte) -> list[dict]:
    ergebnisse = []
    for mp in pr.get("masse_pruefen", []):
        pid, soll, tol = f"mass:{mp['was']}", mp["soll"], mp.get("tol", TOL_MASS)
        von, zu = m.messpunkte.get(messpunkt_schluessel(mp["von"])), m.messpunkte.get(messpunkt_schluessel(mp["zu"]))
        if not isinstance(von, Messgeometrie) or not isinstance(zu, Messgeometrie):
            fehler = next((x for x in (von, zu) if isinstance(x, str)), "Messpunkt fehlt")
            ergebnisse.append(eintrag(pid, False, soll=soll, hinweis=fehler, beleg=_beleg(mp), knoten=[]))
            continue
        try:
            ist = round(abstand(von, zu), 6)
        except NichtMessbar as e:
            ergebnisse.append(eintrag(pid, False, soll=soll, hinweis=str(e), beleg=_beleg(mp), knoten=[]))
            continue
        ergebnisse.append(eintrag(pid, abs(ist - soll) <= tol, ist=ist, soll=soll, tol=tol, beleg=_beleg(mp), knoten=[]))
    return ergebnisse


def _durchmesser(pr: dict, m: KaufteilMesswerte) -> list[dict]:
    ergebnisse = []
    for dp in pr.get("durchmesser_pruefen", []):
        pid, soll, tol = f"durchmesser:{dp['was']}", dp["soll"], dp.get("tol", TOL_MASS)
        ist = m.durchmesser.get(dp["was"], "Messung fehlt")
        if isinstance(ist, str):
            ergebnisse.append(eintrag(pid, False, soll=soll, hinweis=ist, beleg=_beleg(dp), knoten=[]))
            continue
        ok = abs(ist["durchmesser"] - soll) <= tol
        daten = {"ist": ist["durchmesser"], "soll": soll, "tol": tol, "beleg": _beleg(dp)}
        if "referenz" in dp:
            try:
                daten["achsversatz"] = round(abstand(ist["achse"], ist["referenz"]), 6)
                ok = ok and daten["achsversatz"] <= tol
            except (NichtMessbar, KeyError) as e:
                ok, daten["hinweis"] = False, f"nicht koaxial zu {dp['referenz']}: {e}"
        ergebnisse.append(eintrag(pid, ok, **daten, knoten=[]))
    return ergebnisse


def bewerte_kaufteil(spec: dict, m: KaufteilMesswerte) -> dict:
    pr = spec.get("pruefung", {})
    ergebnisse = [eintrag("rebuild", not m.rebuild_fehler, ist=m.rebuild_fehler, knoten=[])]
    import_ok = m.flaechenkoerper == 0 and not any(m.koerperfehler.values())
    ergebnisse.append(eintrag("import", import_ok, ist={"flaechenkoerper": m.flaechenkoerper,
                                                         "koerperfehler": m.koerperfehler}, knoten=[]))
    ergebnisse.append(eintrag("koerper", m.koerper == spec["koerper"], ist=m.koerper, soll=spec["koerper"], knoten=[]))
    if "huellquader" in pr:
        h = pr["huellquader"]
        ist = [round(m.box[i + 3] - m.box[i], 6) for i in range(3)]
        tol = h.get("tol", TOL_HUELLQUADER)
        ergebnisse.append(eintrag("huellquader", all(abs(a - b) <= tol for a, b in zip(ist, h["soll"])), ist=ist,
                                    soll=h["soll"], tol=tol, beleg=_beleg(h), knoten=[]))
    if "volumen" in pr:
        soll = pr["volumen"]["soll"]
        prozent = pr["volumen"].get("toleranz_prozent", TOL_VOLUMEN_PROZENT)
        abw = abs(m.volumen - soll) / soll * 100
        ergebnisse.append(eintrag("volumen", abw <= prozent, ist=round(m.volumen, 3), soll=soll,
                                    abweichung_prozent=round(abw, 4), tol_prozent=prozent, knoten=[]))
    ergebnisse += [_einbau(n, w, m) for n, w in spec["einbau"].items()]
    ergebnisse += [_gewinde(g, w, m) for g, w in spec.get("gewinde", {}).items()]
    ergebnisse += _durchmesser(pr, m) + _masse_pruefen(pr, m)
    ergebnisse.append(eintrag("material", material_passt(m.material, spec["material"]), ist=m.material,
                                soll=spec["material"], knoten=[]))
    soll_eig = eigenschaften(spec)
    abweichend = {k: m.eigenschaften.get(k) for k, v in soll_eig.items() if m.eigenschaften.get(k) != v}
    ergebnisse.append(eintrag("eigenschaften", not abweichend, ist=abweichend, soll=soll_eig, knoten=[]))
    if "masse" in spec:
        kg = spec["masse"]["kg"]
        ok = m.masse_ueberschrieben and math.isclose(m.masse_kg, kg, rel_tol=TOL_MASSE_RELATIV)
        ergebnisse.append(eintrag("masse", ok, ist=round(m.masse_kg, 6), soll=kg, ueberschrieben=m.masse_ueberschrieben,
                                    beleg=_beleg(spec["masse"]), knoten=[]))
    else:
        ergebnisse.append(eintrag("masse", None, ist=round(m.masse_kg, 6), hinweis="Masse aus Material geschätzt",
                                    knoten=[]))
    maengel = [{"pruefung": e["id"], "knoten": e["knoten"], "beschreibung": beschreibung(e)}
               for e in ergebnisse if e["ok"] is False]
    return {"bestanden": not maengel, "pruefungen": ergebnisse, "maengel": maengel}
```

`swki/kaufteile/diagnose.py` anlegen:

```python
"""Übersicht der Flächen eines importierten Kaufteils für `swki kaufteil untersuchen` (Spec 3c §5.1), ohne SolidWorks.

Eingabe: je ebener oder zylindrischer Fläche ein Datensatz der SolidWorks-Schicht {"art", "punkt", "normale" | "achse",
"radius", "auf" (Punkt auf der begrenzten Fläche), "flaeche_mm2"}. Ausgabe: Zylinder gleicher Achse und gleichen Radius
bzw. Ebenen gleicher Lage und Normale zusammengefasst, die größten zuerst, je Art höchstens `grenze` Einträge. Die
Punkte "nahe" taugen als Ankerpunkte für den Katalogeintrag."""

from swki.compiler.anker import laenge, skalar


def _r(v, n: int = 4) -> list[float]:
    return [round(c, n) + 0.0 for c in v]


def _richtung(v) -> tuple:
    """Einheitsvektor mit festem Vorzeichen (erste Komponente ≠ 0 positiv): Achsen ohne Richtungssinn vergleichen."""
    n = laenge(v)
    e = tuple(c / n for c in v)
    erste = next(c for c in e if abs(c) > 1e-9)
    return tuple(-c for c in e) if erste < 0 else e


def _fusspunkt(punkt, richtung) -> tuple:
    """Punkt der Achse, der dem Ursprung am nächsten liegt (gleiche Achse → gleicher Fußpunkt)."""
    t = skalar(punkt, richtung)
    return tuple(punkt[i] - t * richtung[i] for i in range(3))


def uebersicht(saetze: list[dict], grenze: int = 50) -> dict:
    zylinder: dict[tuple, dict] = {}
    ebenen: dict[tuple, dict] = {}
    for s in saetze:
        if s["art"] == "zylinder":
            richtung = _richtung(s["achse"])
            schluessel = (round(s["radius"], 4), *_r(richtung, 6), *_r(_fusspunkt(s["punkt"], richtung), 3))
            z = zylinder.setdefault(schluessel, {"durchmesser": round(2 * s["radius"], 4),
                                                 "achspunkt": _r(_fusspunkt(s["punkt"], richtung)),
                                                 "richtung": _r(richtung, 6), "nahe": _r(s["auf"]), "flaechen": 0,
                                                 "flaeche_mm2": 0.0, "_groesste": 0.0})
        else:
            n = tuple(s["normale"])
            schluessel = (*_r(n, 6), round(skalar(s["punkt"], n), 3))
            z = ebenen.setdefault(schluessel, {"normale": _r(n, 6), "abstand": round(skalar(s["punkt"], n), 4),
                                               "nahe": _r(s["auf"]), "flaechen": 0, "flaeche_mm2": 0.0, "_groesste": 0.0})
        z["flaechen"] += 1
        z["flaeche_mm2"] += s["flaeche_mm2"]
        if s["flaeche_mm2"] > z["_groesste"]:
            z["_groesste"], z["nahe"] = s["flaeche_mm2"], _r(s["auf"])

    def liste(gruppen: dict) -> list[dict]:
        sortiert = sorted(gruppen.values(), key=lambda g: g["flaeche_mm2"], reverse=True)[:grenze]
        return [{**{k: v for k, v in g.items() if k != "_groesste"}, "flaeche_mm2": round(g["flaeche_mm2"], 2)}
                for g in sortiert]

    return {"zylinder": liste(zylinder), "ebenen": liste(ebenen), "zylinder_gesamt": len(zylinder),
            "ebenen_gesamt": len(ebenen)}
```

In `swki/speicher.py` ersetzen:

```python
"""Private Bytes eines Prozesses (Windows, ctypes): SolidWorks-Speicher für die Speichergrenze der Bewegungsprüfung
(Spec 4a §8.4). Gemessen wird PrivateUsage aus PROCESS_MEMORY_COUNTERS_EX, nicht das Working Set."""

import ctypes
from ctypes import wintypes
```

durch:

```python
"""Private Bytes eines Prozesses (Windows, ctypes): SolidWorks-Speicher für die Speichergrenze der Bewegungsprüfung
(Spec 4a §8.4) und die Speicherspitze beim Import eines Kaufteils (Spec 3c §5.1). Gemessen wird PrivateUsage aus
PROCESS_MEMORY_COUNTERS_EX, nicht das Working Set."""

import ctypes
import threading
from ctypes import wintypes
```

In `swki/speicher.py` ersetzen:

```python
        k32.CloseHandle(h)
```

durch:

```python
        k32.CloseHandle(h)


class Spitzenmessung:
    """Kontext: Private Bytes vor, höchstens alle `takt_s` Sekunden während und nach dem Block (MB); danach stehen
    .vorher, .spitze und .nachher fest. `messen` ist austauschbar (Tests)."""

    def __init__(self, pid: int, takt_s: float = 0.5, messen=privat_mb):
        self.pid, self.takt_s, self.messen = pid, takt_s, messen
        self.vorher = self.spitze = self.nachher = 0.0
        self._halt = threading.Event()
        self._faden: threading.Thread | None = None

    def _laufe(self) -> None:
        while not self._halt.wait(self.takt_s):
            self.spitze = max(self.spitze, self.messen(self.pid))

    def __enter__(self):
        self.vorher = self.spitze = self.messen(self.pid)
        self._faden = threading.Thread(target=self._laufe, daemon=True)
        self._faden.start()
        return self

    def __exit__(self, *_):
        self._halt.set()
        self._faden.join()
        self.nachher = self.messen(self.pid)
        self.spitze = max(self.spitze, self.nachher)
        return False

    def als_dict(self) -> dict:
        return {"vorher": self.vorher, "spitze": self.spitze, "nachher": self.nachher}
```

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile\test_ortung.py tests\kaufteile\test_bewertung.py tests\kaufteile\test_diagnose.py tests\test_speicher.py`
Expected: `20 passed`. Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **893 passed, 133 deselected**.

- [ ] **Step 5: Commit**

```powershell
git add swki/kaufteile/ortung.py swki/kaufteile/bewertung.py swki/kaufteile/diagnose.py swki/speicher.py tests/kaufteile/test_ortung.py tests/kaufteile/test_bewertung.py tests/kaufteile/test_diagnose.py tests/test_speicher.py
git commit -m "kaufteile: Ortung und Gegenprobe, Bewertung, Flächenübersicht, Spitzenmessung (Stufe 3c, Task 4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: SolidWorks-Schicht und Aufnahme (live)

**Files:**
- Create: `swki/kaufteile/sw_kaufteil.py`, `swki/kaufteile/aufnahme.py`
- Test: `tests/live/test_live_kaufteile.py`

**Interfaces:**
- Consumes: Tasks 3/4; Spike-Rulings zu den Zeilen 2–13; `sw.einstellung`/`einstellung_int`, `sw.teilebox_mm`, `sw.rebuild`,
  `sw.speichere`, `sw.schliesse`, `flaeche_aus`, `koerper`, `mit_abstand`, `referenz_geometrie`, `setze_material`,
  `setze_eigenschaften`, `lies_eigenschaften`, `rebuild_fehler`, `screenshots`, `verbinde`.
- Produces:
  - `swki.kaufteile.sw_kaufteil`: `optionen(app) -> dict`, `importoptionen(app)` (Kontext), `importiere(app, pfad)` (Dokument;
    `BauFehler(KAUFTEIL_IMPORT)`), `interconnect_features(model)`, `alle_flaechen(model)`, `koerperfehler(model)`,
    `flaechenkoerper(model)`, `diagnose(model, flaechen)`, `datensaetze(flaechen)`, `lege_einbau_an(model, spec, flaechen, tol)`,
    `orte_gewinde_alle(spec, flaechen, tol)`, `setze_masse(model, kg)`, `richte_ein(app, model, spec, tol) -> (flaechen,
    einbau, gewinde)`, `messe(model, spec, flaechen, einbau, gewinde, tol) -> KaufteilMesswerte`, `zeige_bezuege(model)`.
  - `swki.kaufteile.aufnahme`: `untersuche(original, ordner) -> dict` (Diagnose), `baue_und_pruefe(spec, original, ordner,
    mit_bildern=False) -> {"bestanden", "pruefungen", "maengel", "teil", "bilder", "fehler", "gewinde_modell", "kennzahlen"}`.

- [ ] **Step 1: Live-Tests schreiben**

`tests/live/test_live_kaufteile.py` anlegen:

```python
"""Live-Tests der Kaufteil-Aufnahme am Muster-Getriebemotor (Spec 3c §6, §11): Import, Diagnose, Bau und Prüfung,
Negativfälle Gegenprobe und Körperzahl. SolidWorks muss laufen; gespeichert wird nur im Arbeitsordner."""

import shutil
from pathlib import Path

import pytest

from swki.aenderungen import sha256_datei
from swki.compiler import sw
from swki.compiler.topologie import koerper
from swki.kaufteile import aufnahme, sw_kaufteil
from swki.konfig import PROJEKT, lade_rechner
from swki.verbindung import verbinde
from tests.kaufteile.beispiel import kopie

pytestmark = pytest.mark.sw
STEP = PROJEKT / "tests" / "referenz" / "motorhalter" / "muster" / "gm42-10.step"
AUFTRAG = "LIVE-KAUFTEIL"


@pytest.fixture
def ordner():
    pfad = lade_rechner().arbeitsordner / AUFTRAG
    yield pfad
    shutil.rmtree(pfad, ignore_errors=True)


def _eintrag(volumen: float | None = None) -> dict:
    spec = kopie()
    spec["original"]["sha256"] = sha256_datei(STEP)
    if volumen is None:
        del spec["pruefung"]["volumen"]
    else:
        spec["pruefung"]["volumen"]["soll"] = volumen
    return spec


def test_import_ohne_interconnect_und_optionen_zurueck():
    app = verbinde(lade_rechner().sw_jahr)
    vorher = sw_kaufteil.optionen(app)
    model = sw_kaufteil.importiere(app, STEP)
    try:
        assert len(koerper(model)) == 2 and sw_kaufteil.flaechenkoerper(model) == 0
        assert sw_kaufteil.interconnect_features(model) == []
        assert all(n == 0 for n in sw_kaufteil.koerperfehler(model).values())
    finally:
        sw.schliesse(app, model)
    assert sw_kaufteil.optionen(app) == vorher


def test_untersuche_muster(ordner):
    d = aufnahme.untersuche(STEP, ordner / "untersuchung")
    assert (d["koerper"], d["flaechenkoerper"], d["interconnect"]) == (2, 0, [])
    assert {10.0, 40.0, 56.0, 4.2} <= {z["durchmesser"] for z in d["zylinder"]}
    box = d["huellquader"]
    assert [round(box[i + 3] - box[i], 3) for i in range(3)] == [60.0, 107.0, 60.0]
    assert d["volumen"] > 0 and all(Path(p).stat().st_size > 0 for p in d["bilder"].values())


def test_baue_und_pruefe_muster(ordner):
    volumen = aufnahme.untersuche(STEP, ordner / "untersuchung")["volumen"]
    e = aufnahme.baue_und_pruefe(_eintrag(volumen), STEP, ordner / "lauf", mit_bildern=True)
    assert e["fehler"] is None and e["maengel"] == [], e["maengel"]
    assert e["gewinde_modell"] == {"flansch": "kernloch"} and Path(e["teil"]).is_file()
    assert all(Path(p).stat().st_size > 0 for p in e["bilder"].values())


@pytest.mark.parametrize(("aenderung", "erwartet"), [
    ("durchmesser", {"einbau:EINBAU_ACHSE"}),
    ("koerper", {"koerper"}),
])
def test_negativfaelle(ordner, aenderung, erwartet):
    spec = _eintrag()
    if aenderung == "durchmesser":
        spec["einbau"]["EINBAU_ACHSE"]["zylinder"]["durchmesser"] = 12
    else:
        spec["koerper"] = 1
    e = aufnahme.baue_und_pruefe(spec, STEP, ordner / "lauf")
    assert {m["pruefung"] for m in e["maengel"]} == erwartet, e["maengel"]
```

- [ ] **Step 2: Sammeln prüfen**

Run: `.venv\Scripts\python.exe -m pytest -q -m sw tests\live\test_live_kaufteile.py --co`
Expected: FAIL – `no tests collected, 1 error` (`ImportError: cannot import name 'aufnahme' from 'swki.kaufteile'`).

- [ ] **Step 3: Umsetzen**

`swki/kaufteile/sw_kaufteil.py` anlegen:

```python
"""SolidWorks-Schicht der Kaufteile (Spec 3c §6, Spike S15): STEP importieren (Optionen nur für den Import, danach
wiederhergestellt), Diagnose ohne Reparatur, Bezugsgeometrie an Importflächen, Massenüberschreibung, Messwerte.

Late Binding (swki/wissen/pywin32-fallstricke.md): nullargumentige Member ohne "()"; IBody2 hat Typinfo – seine
Methoden mit "()", Properties (Check3) ohne (S9b)."""

from contextlib import contextmanager
from pathlib import Path

from swki.compiler import sw
from swki.compiler.anker import AnkerFehler, Flaeche
from swki.compiler.eigenschaften import lies_eigenschaften, setze_eigenschaften, setze_material
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.topologie import flaeche_aus, koerper, mit_abstand, referenz_geometrie
from swki.kaufteile.bewertung import KaufteilMesswerte
from swki.kaufteile.eintrag import eigenschaften
from swki.kaufteile.fehler import KAUFTEIL_IMPORT
from swki.kaufteile.ortung import (Ortung, ebene_durch_achse, kandidaten, orte_ebene, orte_gewinde, orte_zylinder)
from swki.pruefung.bewertung import messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from swki.pruefung.messen import rebuild_fehler
from swki.verbindung import byref_long, byref_str, callout_leer, in_mm, in_mm3, mm

SW_3D_INTERCONNECT = 691      # swUserPreferenceToggle_e.swMultiCAD_Enable3DInterconnect
SW_IMPORT_DIAGNOSE = 690      # swUserPreferenceToggle_e.swImportNeutralRunDiagnostics
SW_IMPORT_STRUKTUR = 579      # swUserPreferenceIntegerValue_e.swImportNeutralAssemblyStructureMapping
STRUKTUR_MEHRKOERPER = 2      # swImportNeutralAssemblyStructureMapping_e.…_MultibodyPart
SW_SHEET_BODY = 1             # swBodyType_e.swSheetBody
REF_PLANE_DECKUNGSGLEICH = 4  # swRefPlaneReferenceConstraints_e.swRefPlaneReferenceConstraint_Coincident
SW_ANZEIGE_ACHSEN, SW_ANZEIGE_EBENEN = 4, 5  # swUserPreferenceToggle_e.swDisplayAxes / swDisplayPlanes
SW_OHNE_OPTION = 0            # swUserPreferenceOption_e.swDetailingNoOptionSpecified


def optionen(app) -> dict:
    """Die Import-Optionen, die importiere() vorübergehend setzt, im vorgefundenen Stand (fürs Protokoll)."""
    return {"3d_interconnect": bool(app.GetUserPreferenceToggle(SW_3D_INTERCONNECT)),
            "importdiagnose": bool(app.GetUserPreferenceToggle(SW_IMPORT_DIAGNOSE)),
            "strukturabbildung": int(app.GetUserPreferenceIntegerValue(SW_IMPORT_STRUKTUR))}


@contextmanager
def importoptionen(app):
    """3D Interconnect aus (sonst behält das Teil einen Verweis auf das Original), keine automatische Importdiagnose
    (sie repariert bzw. fragt), Baugruppen-STEP als Mehrkörperteil; danach immer der vorgefundene Stand."""
    with sw.einstellung(app, SW_3D_INTERCONNECT, False), sw.einstellung(app, SW_IMPORT_DIAGNOSE, False), \
            sw.einstellung_int(app, SW_IMPORT_STRUKTUR, STRUKTUR_MEHRKOERPER):
        yield


def importiere(app, pfad: Path):
    """STEP-Datei als neues Teil (ungespeichert); KAUFTEIL_IMPORT, wenn SolidWorks kein Dokument liefert."""
    with importoptionen(app):
        daten = app.GetImportFileData(str(pfad))
        fehler = byref_long()
        model = app.LoadFile4(str(pfad), "r", daten, fehler)
    if model is None:
        raise BauFehler(KAUFTEIL_IMPORT, f"{pfad.name}: Import gescheitert (swFileLoadError {fehler.value})",
                        schritt="import")
    return model


def interconnect_features(model) -> list[str]:
    """Namen der Features, die noch über 3D Interconnect an der Originaldatei hängen (Soll: keine)."""
    namen, f = [], model.FirstFeature
    while f is not None:
        if f.Is3DInterconnectFeature:
            namen.append(f.Name)
        f = f.GetNextFeature
    return namen


def alle_flaechen(model) -> list[Flaeche]:
    return [flaeche_aus(f) for b in koerper(model) for f in (b.GetFaces() or ())]


def koerperfehler(model) -> dict[str, int]:
    """Fehlerzahl je Volumenkörper laut IBody2.Check3 (ohne Reparatur)."""
    ergebnis = {}
    for i, b in enumerate(koerper(model), start=1):
        fehler = b.Check3
        ergebnis[str(i)] = 0 if fehler is None else int(fehler.Count)
    return ergebnis


def flaechenkoerper(model) -> int:
    return len(model.GetBodies2(SW_SHEET_BODY, False) or ())


def _datensatz(f: Flaeche) -> dict:
    """Datensatz für diagnose.uebersicht: Punkt auf der begrenzten Fläche (nächster zur Mitte der Box) und Fläche."""
    box = f.objekt.GetBox
    q = f.objekt.GetClosestPointOn((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2)
    satz = {"art": f.art, "punkt": f.punkt, "auf": tuple(in_mm(c) for c in q[:3]),
            "flaeche_mm2": f.objekt.GetArea * 1e6}
    return satz | ({"normale": f.normale} if f.art == "ebene" else {"achse": f.achse, "radius": f.radius})


def diagnose(model, flaechen: list[Flaeche]) -> dict:
    """Kennzahlen des importierten Teils (Spec 3c §5.1) ohne die Flächenübersicht."""
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return {"koerper": len(koerper(model)), "flaechenkoerper": flaechenkoerper(model), "koerperfehler": koerperfehler(model),
            "flaechen": len(flaechen), "huellquader": sw.teilebox_mm(model), "volumen": round(in_mm3(mp.Volume), 3),
            "schwerpunkt": [round(in_mm(c), 4) for c in mp.CenterOfMass], "interconnect": interconnect_features(model)}


def datensaetze(flaechen: list[Flaeche]) -> list[dict]:
    return [_datensatz(f) for f in flaechen if f.art in ("ebene", "zylinder")]


def _bezugsachse(model, flaeche: Flaeche, name: str):
    sw.auswahl_leeren(model)
    sw.waehle(model, flaeche.objekt, 0)
    if not model.InsertAxis2(True):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Bezugsachse nicht erzeugt", schritt="einbau")
    feature = sw.letztes_feature(model)
    feature.Name = name
    return feature


def _bezugsebene(model, flaeche: Flaeche, name: str):
    sw.auswahl_leeren(model)
    sw.waehle(model, flaeche.objekt, 0)
    feature = model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0, 0, 0.0)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Bezugsebene nicht erzeugt", schritt="einbau")
    feature.Name = name
    return feature


def _ebene_durch_achse(model, achse, nahe, name: str):
    """Bezugsebene durch eine Bezugsachse und einen Punkt; der Punkt ist ein 3D-Skizzenpunkt <name>_punkt (Spike S15c)."""
    sm = model.SketchManager
    sw.auswahl_leeren(model)
    sm.Insert3DSketch(True)
    with sw.ohne_inferenz(sm):
        punkt = sm.CreatePoint(*(mm(c) for c in nahe))
    sm.Insert3DSketch(True)
    if punkt is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Skizzenpunkt nicht erzeugt", schritt="einbau")
    skizze = sw.letztes_feature(model)
    skizze.Name = f"{name}_punkt"
    sw.auswahl_leeren(model)
    achse.Select2(False, 0)
    if not model.Extension.SelectByID2(f"Point1@{skizze.Name}", "EXTSKETCHPOINT", 0, 0, 0, True, 1, callout_leer(), 0):
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Skizzenpunkt nicht auswählbar", schritt="einbau")
    feature = model.FeatureManager.InsertRefPlane(REF_PLANE_DECKUNGSGLEICH, 0.0, REF_PLANE_DECKUNGSGLEICH, 0.0, 0, 0.0)
    sw.auswahl_leeren(model)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{name}: Bezugsebene durch Achse und Punkt nicht erzeugt",
                        schritt="einbau")
    feature.Name = name
    return feature


def _geortet(flaechen: list[Flaeche], art: str, punkt, tol_mm: float) -> list[Flaeche]:
    """Vorauswahl (rein geometrisch) und echter Abstand zur begrenzten Fläche (COM) nur für die Kandidaten."""
    return mit_abstand(kandidaten(flaechen, art, tuple(punkt), tol_mm), tuple(punkt))


def _messung(o: Ortung, feature) -> dict:
    bezug = Messgeometrie(*referenz_geometrie(feature)) if feature is not None else None
    return {"ist": o.ist, "abweichung": o.abweichung, "bezug": bezug}


def lege_einbau_an(model, spec: dict, flaechen: list[Flaeche], tol_mm: float) -> dict:
    """Einbaureferenzen orten, gegenprüfen und als benannte Bezugsgeometrie anlegen (zuerst zylinder und ebene, dann
    ebene_durch_achse). Ortungsfehler werden Messwerte (Text), keine Abbrüche: die Prüfung meldet sie als Mangel."""
    ergebnis: dict[str, dict | str] = {}
    reihenfolge = sorted(spec["einbau"].items(), key=lambda kv: "ebene_durch_achse" in kv[1])
    for name, w in reihenfolge:
        art, soll = next(iter(w.items()))
        try:
            if art == "zylinder":
                o = orte_zylinder(_geortet(flaechen, "zylinder", soll["nahe"], tol_mm), name, soll, tol_mm)
                ergebnis[name] = _messung(o, _bezugsachse(model, o.flaeche, name))
            elif art == "ebene":
                o = orte_ebene(_geortet(flaechen, "ebene", soll["nahe"], tol_mm), name, soll, tol_mm)
                ergebnis[name] = _messung(o, _bezugsebene(model, o.flaeche, name))
            else:
                achse = ergebnis.get(soll["achse"])
                if not isinstance(achse, dict) or achse["bezug"] is None:
                    ergebnis[name] = f"{soll['achse']} fehlt"
                    continue
                o = ebene_durch_achse(name, achse["bezug"].punkt, achse["bezug"].richtung, soll["nahe"])
                feature = None if o.abweichung else _ebene_durch_achse(model, model.FeatureByName(soll["achse"]),
                                                                       soll["nahe"], name)
                ergebnis[name] = _messung(o, feature)
        except AnkerFehler as e:
            ergebnis[name] = f"{e.code}: {e}"
    return ergebnis


def orte_gewinde_alle(spec: dict, flaechen: list[Flaeche], tol_mm: float) -> dict:
    ergebnis: dict[str, dict | str] = {}
    for gruppe, w in spec.get("gewinde", {}).items():
        try:
            for o in orte_gewinde(flaechen, gruppe, w, tol_mm):
                ergebnis[o.name] = {"ist": o.ist, "abweichung": o.abweichung}
        except AnkerFehler as e:
            for i in range(1, len(w["positionen"]) + 1):
                ergebnis.setdefault(f"{gruppe}.{i}", f"{e.code}: {e}")
    return ergebnis


def setze_masse(model, kg: float) -> None:
    """Massenüberschreibung (IMassPropertyOverrideOptions, seit SW 2020; Spike S15d)."""
    mp = model.Extension.CreateMassProperty2
    optionen_masse = mp.GetOverrideOptions
    optionen_masse.OverrideMass = True
    optionen_masse.SetOverrideMassValue(kg)


def richte_ein(app, model, spec: dict, tol_mm: float) -> tuple[list[Flaeche], dict, dict]:
    """Material, Eigenschaften, Einbaureferenzen, Gewindepositionen, Masse; danach Rebuild. Liefert (Flächen, einbau,
    gewinde)."""
    setze_material(app, model, spec["material"])
    setze_eigenschaften(model, eigenschaften(spec))
    flaechen = alle_flaechen(model)
    einbau = lege_einbau_an(model, spec, flaechen, tol_mm)
    gewinde = orte_gewinde_alle(spec, flaechen, tol_mm)
    if "masse" in spec:
        setze_masse(model, spec["masse"]["kg"])
    sw.rebuild(model)
    return flaechen, einbau, gewinde


def _messpunkt(mp: dict, einbau: dict, gewinde: dict, flaechen: list[Flaeche], tol_mm: float) -> Messgeometrie | str:
    if "punkt" in mp:
        return Messgeometrie("punkt", tuple(mp["punkt"]))
    if "referenz" in mp:
        m = einbau.get(mp["referenz"], f"{mp['referenz']} fehlt")
        return m if isinstance(m, str) else (m["bezug"] or f"{mp['referenz']}: keine Bezugsgeometrie")
    if "gewinde" in mp:
        m = gewinde.get(f"{mp['gewinde']}.{mp['instanz']}", "Gewindeposition fehlt")
        return m if isinstance(m, str) else Messgeometrie("achse", m["ist"]["punkt"], m["ist"]["achse"])
    w = mp["flaeche"]
    try:
        o = orte_ebene(_geortet(flaechen, "ebene", w["nahe"], tol_mm), "flaeche", w, tol_mm)
    except AnkerFehler as e:
        return f"{e.code}: {e}"
    return o.abweichung or Messgeometrie("ebene", o.flaeche.punkt, o.flaeche.normale)


def _durchmesser(spec: dict, einbau: dict, flaechen: list[Flaeche], tol_mm: float) -> dict:
    ergebnis: dict[str, dict | str] = {}
    for dp in spec.get("pruefung", {}).get("durchmesser_pruefen", []):
        try:
            o = orte_zylinder(_geortet(flaechen, "zylinder", dp["nahe"], tol_mm), dp["was"],
                              {"nahe": dp["nahe"], "durchmesser": dp["soll"]}, tol_mm)
        except AnkerFehler as e:
            ergebnis[dp["was"]] = f"{e.code}: {e}"
            continue
        wert = {"durchmesser": o.ist["durchmesser"], "achse": Messgeometrie("achse", o.ist["punkt"], o.ist["achse"])}
        if "referenz" in dp and isinstance(einbau.get(dp["referenz"]), dict) and einbau[dp["referenz"]]["bezug"]:
            wert["referenz"] = einbau[dp["referenz"]]["bezug"]
        ergebnis[dp["was"]] = wert
    return ergebnis


def messe(model, spec: dict, flaechen: list[Flaeche], einbau: dict, gewinde: dict, tol_mm: float) -> KaufteilMesswerte:
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    pr = spec.get("pruefung", {})
    punkte = {messpunkt_schluessel(p): _messpunkt(p, einbau, gewinde, flaechen, tol_mm)
              for m in pr.get("masse_pruefen", []) for p in (m["von"], m["zu"])}
    return KaufteilMesswerte(
        rebuild_fehler=rebuild_fehler(model), koerper=len(koerper(model)), flaechenkoerper=flaechenkoerper(model),
        koerperfehler=koerperfehler(model), box=sw.teilebox_mm(model), volumen=in_mm3(mp.Volume), masse_kg=mp.Mass,
        masse_ueberschrieben=bool(mp.GetOverrideOptions.OverrideMass),
        material=model.GetMaterialPropertyName2("", byref_str()) or "", eigenschaften=lies_eigenschaften(model),
        einbau=einbau, gewinde=gewinde, messpunkte=punkte, durchmesser=_durchmesser(spec, einbau, flaechen, tol_mm))


def zeige_bezuege(model) -> None:
    """Bezugsachsen und -ebenen im eigenen Dokument einblenden (Bilder für Nutzer und Prüfer, Spike S15h)."""
    for toggle in (SW_ANZEIGE_ACHSEN, SW_ANZEIGE_EBENEN):
        model.Extension.SetUserPreferenceToggle(toggle, SW_OHNE_OPTION, True)
```

`swki/kaufteile/aufnahme.py` anlegen:

```python
"""Aufnahme eines Kaufteils in SolidWorks (Spec 3c §5.1, §5.3, §6): untersuchen (Import und Diagnose, nichts wird
abgelegt) und baue_und_pruefe (Import, Einbaureferenzen, Prüfung, Speichern im Laufordner). Beide schließen ihr
Dokument immer; gespeichert wird nur im Arbeitsordner."""

import time
from pathlib import Path

from swki.compiler import sw
from swki.compiler.fehler import fehler_dict
from swki.kaufteile import sw_kaufteil
from swki.kaufteile.bewertung import bewerte_kaufteil
from swki.kaufteile.diagnose import uebersicht
from swki.kaufteile.katalog import bibliotheksschluessel
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.bilder import screenshots
from swki.speicher import Spitzenmessung
from swki.verbindung import verbinde


def _pid(app) -> int:
    return int(app.GetProcessID)


def untersuche(original: Path, ordner: Path) -> dict:
    """Diagnose einer STEP-Datei (Kopie im Quellordner): Kennzahlen, Flächenübersicht, Bilder, Zeit, Speicher."""
    r = lade_rechner()
    ordner.mkdir(parents=True, exist_ok=True)
    app = verbinde(r.sw_jahr)
    optionen = sw_kaufteil.optionen(app)
    with Spitzenmessung(_pid(app)) as speicher:
        beginn = time.perf_counter()
        model = sw_kaufteil.importiere(app, original)
        import_s = round(time.perf_counter() - beginn, 3)
        try:
            flaechen = sw_kaufteil.alle_flaechen(model)
            kennzahlen = sw_kaufteil.diagnose(model, flaechen)
            liste = uebersicht(sw_kaufteil.datensaetze(flaechen))
            bilder = screenshots(app, model, ordner / "bilder")
        finally:
            sw.schliesse(app, model)
    return {"datei": original.name, "dateigroesse_mb": round(original.stat().st_size / 2 ** 20, 3), "import_s": import_s,
            "dauer_s": round(time.perf_counter() - beginn, 3), "privat_mb": speicher.als_dict(),
            "optionen_vorher": optionen, **kennzahlen, **liste, "bilder": bilder}


def baue_und_pruefe(spec: dict, original: Path, ordner: Path, mit_bildern: bool = False) -> dict:
    """{"bestanden", "pruefungen", "maengel", "teil", "bilder", "fehler", "gewinde_modell", "kennzahlen"}. Ein Import- oder
    Einrichtungsfehler ergibt bestanden False mit fehler (nichts gemessen, nichts gespeichert)."""
    r, standard = lade_rechner(), lade_standard()
    tol = standard["toleranzen"]["anker_mm"]
    ordner.mkdir(parents=True, exist_ok=True)
    app = verbinde(r.sw_jahr)
    kennzahlen = {"optionen_vorher": sw_kaufteil.optionen(app)}
    with Spitzenmessung(_pid(app)) as speicher:
        beginn = time.perf_counter()
        try:
            model = sw_kaufteil.importiere(app, original)
        except Exception as e:
            return _abbruch(e)
        try:
            kennzahlen["import_s"] = round(time.perf_counter() - beginn, 3)
            try:
                flaechen, einbau, gewinde = sw_kaufteil.richte_ein(app, model, spec, tol)
            except Exception as e:  # z. B. MATERIAL_UNBEKANNT, Bezugsgeometrie nicht erzeugt
                return _abbruch(e)
            bericht = bewerte_kaufteil(spec, sw_kaufteil.messe(model, spec, flaechen, einbau, gewinde, tol))
            kennzahlen |= {"flaechen": len(flaechen), "interconnect": sw_kaufteil.interconnect_features(model)}
            bilder = {}
            if mit_bildern:
                sw_kaufteil.zeige_bezuege(model)
                bilder = screenshots(app, model, ordner / "bilder")
            teil = ordner / f"{bibliotheksschluessel(spec['hersteller'], spec['bestellnummer'])}.sldprt"
            sw.speichere(model, teil)
        finally:
            sw.schliesse(app, model)
    kennzahlen |= {"dauer_s": round(time.perf_counter() - beginn, 3), "privat_mb": speicher.als_dict()}
    modelle = {}
    for name, g in gewinde.items():
        if isinstance(g, dict) and g["ist"].get("modell"):
            modelle.setdefault(name.rsplit(".", 1)[0], g["ist"]["modell"])
    return {**bericht, "teil": str(teil), "bilder": bilder, "fehler": None, "gewinde_modell": modelle,
            "kennzahlen": kennzahlen}


def _abbruch(e: Exception) -> dict:
    f = fehler_dict(e)
    return {"bestanden": False, "pruefungen": [], "teil": None, "bilder": {}, "fehler": f, "gewinde_modell": {},
            "kennzahlen": {}, "maengel": [{"pruefung": "bau", "knoten": [], "beschreibung": f"{f['code']}: {f['meldung']}"}]}
```

- [ ] **Step 4: Unit-Tests und API-Prüfung**

Run: `.venv\Scripts\python.exe -m pytest -q` → **893 passed, 138 deselected**; `.venv\Scripts\python.exe -m pytest -q -m sw tests\live\test_live_kaufteile.py --co` → `5 tests collected`;
`.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` → `"befunde": []`.

- [ ] **Step 5: Live-Tests**

Vorbedingungen wie Task 2 Step 1 (Teil-Live-Tests; frisch nicht nötig). Run:
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_kaufteile.py --zeit 600`
Expected: `OK` für alle 5 Tests. Danach Import-Optionen wie vorher, `False 1`, Private Bytes notieren; Arbeitsordner
`LIVE-KAUFTEIL` ist aufgeräumt. Weicht `test_negativfaelle` ab: Erwartung nicht abschwächen, NEEDS_CONTEXT mit der Mängelliste.

- [ ] **Step 6: Commit**

```powershell
git add swki/kaufteile/sw_kaufteil.py swki/kaufteile/aufnahme.py tests/live/test_live_kaufteile.py
git commit -m "kaufteile: STEP-Import, Diagnose, Bezugsgeometrie, Masse, Aufnahme mit Prüfung (Stufe 3c, Task 5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Quelle, Cache, Befehle `swki kaufteil` (ohne SolidWorks)

**Files:**
- Create: `swki/kaufteile/quelle.py`, `swki/kaufteile/cache.py`, `swki/kaufteile/befehle.py`
- Modify: `swki/cli.py`
- Test: `tests/kaufteile/test_befehle_kaufteile.py`

**Interfaces:**
- Consumes: Tasks 3–5 (`katalog`, `eintrag.lade_eintrag`, `aufnahme.untersuche`/`baue_und_pruefe`), `swki.aenderungen.sha256_datei`,
  `swki.auftrag.laeufe`/`lauf_ordner`, `swki.pruefung.schleife.lies_urteil`, `swki.spec.freigabe`.
- Produces:
  - `swki.kaufteile.quelle`: `ENDUNGEN`, `bibliothek(r)`, `quellordner(r, h)`, `pruefe_format(pfad)`, `uebernimm(r, quelle, h, b,
    eintrag=None, neue_version=False) -> {"datei", "pfad", "sha256", "kopiert"}`, `uebernimm_datenblatt(r, quelle, h)`,
    `original(r, spec) -> Path`.
  - `swki.kaufteile.cache`: `IMPORTWEG_VERSION`, `cacheordner(r)`, `cache_pruefsumme(spec)`, `teil_pfad`, `lies`, `ist_aktuell`,
    `lege_ab`.
  - `swki.kaufteile.befehle`: `AUFTRAG = "KAUFTEILE"`, `geruest(…)`, `untersuchen(step, h, b, datenblatt=None, neue_version=False,
    katalog=None)`, `hole(text, katalog=None) -> {"schluessel", "pfad", "gebaut", "pruefsumme", "gewinde_modell", "pruefung", …}`,
    `muster(text, katalog=None)`, `urteil(text, datei, freigabe_summe, katalog=None)`, `liste(nur_veraltet=False, katalog=None)`;
    CLI `swki kaufteil untersuchen|muster|urteil|hole|liste`.

- [ ] **Step 1: Tests schreiben**

`tests/kaufteile/test_befehle_kaufteile.py` anlegen:

```python
import json
from pathlib import Path

import pytest

from swki.aenderungen import sha256_datei
from swki.cli import main
from swki.kaufteile import befehle, cache, katalog as kat
from swki.kaufteile.fehler import KaufteilFehler
from swki.konfig import Rechner
from swki.spec.freigabe import FreigabeFehler, pruefsumme
from tests.kaufteile.beispiel import kopie, schreibe

SCHLUESSEL = "SWKI-MUSTER GM42-10"


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit", None, tmp_path / "kauf")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    step = tmp_path / "download" / "GM42-10.STEP"
    step.parent.mkdir()
    step.write_bytes(b"ISO-10303-21;\nHEADER;\n")
    blatt = tmp_path / "download" / "datenblatt.md"
    blatt.write_text("# Datenblatt GM42\n", encoding="utf-8")
    return r, tmp_path / "katalog", step, blatt


@pytest.fixture
def sw(monkeypatch):
    aufrufe = []

    def untersuche(original, ordner):
        aufrufe.append(("untersuche", original.name))
        return {"koerper": 2, "volumen": 220123.456, "flaechen": 40}

    def baue_und_pruefe(spec, original, ordner, mit_bildern=False):
        aufrufe.append(("bau", mit_bildern))
        ordner.mkdir(parents=True, exist_ok=True)
        teil = ordner / "SWKI-MUSTER_GM42-10.sldprt"
        teil.write_bytes(b"teil")
        return {"bestanden": True, "pruefungen": [{"id": "rebuild", "ok": True}], "maengel": [], "teil": str(teil),
                "bilder": {"iso": "iso.png"} if mit_bildern else {}, "fehler": None,
                "gewinde_modell": {"flansch": "kernloch"}, "kennzahlen": {"flaechen": 40}}

    monkeypatch.setattr(befehle.aufnahme, "untersuche", untersuche)
    monkeypatch.setattr(befehle.aufnahme, "baue_und_pruefe", baue_und_pruefe)
    return aufrufe


def _eintrag(katalog, step) -> Path:
    spec = kopie()
    spec["original"] = {"datei": "gm42-10.step", "sha256": sha256_datei(step), "bezug": {"art": "nutzer", "datum": "2026-10-07"}}
    return schreibe(katalog, spec)


def _urteil(pfad, tmp_path, katalog, bestanden=True):
    datei = tmp_path / "urteil.json"
    datei.write_text(json.dumps({"bestanden": bestanden, "maengel": []}), encoding="utf-8")
    spec = befehle.lade_eintrag(pfad)
    return befehle.urteil(SCHLUESSEL, datei, pruefsumme(spec), katalog)


def test_nur_step(umgebung):
    with pytest.raises(KaufteilFehler) as e:
        befehle.untersuchen(Path("motor.igs"), "SWKI-MUSTER", "GM42-10")
    assert e.value.daten["code"] == "KAUFTEIL_FORMAT"


def test_untersuchen_kopiert_und_liefert_geruest(umgebung, sw):
    r, katalog, step, blatt = umgebung
    erg = befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", blatt, katalog=katalog)
    kopie_step = r.kaufteilbibliothek / "quellen" / "swki-muster" / "gm42-10.step"
    assert erg["original"] == {"datei": "gm42-10.step", "pfad": str(kopie_step), "sha256": sha256_datei(step), "kopiert": True}
    assert kopie_step.read_bytes() == step.read_bytes() and (kopie_step.parent / "datenblatt.md").is_file()
    assert erg["geruest"]["original"]["sha256"] == sha256_datei(step) and erg["geruest"]["koerper"] == 2
    assert erg["geruest"]["pruefung"]["volumen"] == {"soll": 220123.456, "toleranz_prozent": 0.01}
    assert erg["geruest"]["datenblatt"] == {"datei": "datenblatt.md"} and erg["eintrag_vorhanden"] is False
    assert json.loads((Path(erg["lauf"]) / "diagnose.json").read_text(encoding="utf-8"))["flaechen"] == 40
    assert sw == [("untersuche", "gm42-10.step")]
    assert befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)["original"]["kopiert"] is False
    assert Path(befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)["lauf"]).name == "lauf-3"


def test_anderer_inhalt_ueberschreibt_nie(umgebung, sw):
    _, katalog, step, _ = umgebung
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    step.write_bytes(b"ISO-10303-21;\nANDERS;\n")
    with pytest.raises(KaufteilFehler) as e:
        befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    assert e.value.daten["code"] == "KAUFTEIL_QUELLE_ABWEICHEND"


def test_eintrag_mit_anderem_original_und_neue_version(umgebung, sw):
    r, katalog, step, _ = umgebung
    _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    alt = r.kaufteilbibliothek / "quellen" / "swki-muster" / "gm42-10.step"
    step.write_bytes(b"ISO-10303-21;\nNEU;\n")
    with pytest.raises(KaufteilFehler) as e:
        befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    assert e.value.daten["code"] == "KAUFTEIL_QUELLE_ABWEICHEND"
    neu = befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", neue_version=True, katalog=katalog)["original"]
    assert neu["datei"] == f"gm42-10.{sha256_datei(step)[:8]}.step" and alt.is_file()


def test_stellt_original_eines_eintrags_wieder_her(umgebung, sw):
    r, katalog, step, _ = umgebung
    _eintrag(katalog, step)
    erg = befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    assert erg["eintrag_vorhanden"] is True and erg["original"]["kopiert"] is True


def test_hole_braucht_quelle_freigabe_und_urteil(umgebung, sw, tmp_path):
    r, katalog, step, _ = umgebung
    pfad = _eintrag(katalog, step)
    with pytest.raises(FreigabeFehler):
        befehle.hole(SCHLUESSEL, katalog)
    main(["freigeben", str(pfad)])
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_UNGEPRUEFT"
    _urteil(pfad, tmp_path, katalog)
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_QUELLE_FEHLT"
    assert sw == []


def test_hole_legt_ab_und_trifft_den_cache(umgebung, sw, tmp_path):
    r, katalog, step, _ = umgebung
    pfad = _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    main(["freigeben", str(pfad)])
    _urteil(pfad, tmp_path, katalog)
    erst = befehle.hole(SCHLUESSEL, katalog)
    ziel = r.kaufteilbibliothek / "2025" / "SWKI-MUSTER_GM42-10.sldprt"
    assert erst["gebaut"] is True and Path(erst["pfad"]) == ziel and erst["gewinde_modell"] == {"flansch": "kernloch"}
    eintrag = json.loads(ziel.with_suffix(".json").read_text(encoding="utf-8"))
    assert eintrag["sldprt_sha256"] == sha256_datei(ziel) and eintrag["pruefsumme"] == erst["pruefsumme"]
    zweit = befehle.hole(SCHLUESSEL, katalog)
    assert zweit["gebaut"] is False and zweit["gewinde_modell"] == {"flansch": "kernloch"}
    ziel.write_bytes(b"von Hand geaendert")
    assert befehle.hole(SCHLUESSEL, katalog)["gebaut"] is True
    assert [a for a in sw if a[0] == "bau"] == [("bau", False), ("bau", False)]


def test_hole_pruefung_oder_import_scheitert(umgebung, sw, tmp_path, monkeypatch):
    r, katalog, step, _ = umgebung
    pfad = _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    main(["freigeben", str(pfad)])
    _urteil(pfad, tmp_path, katalog)
    mangel = {"bestanden": False, "pruefungen": [], "maengel": [{"pruefung": "koerper", "knoten": [], "beschreibung": "x"}],
              "teil": None, "bilder": {}, "fehler": None, "gewinde_modell": {}, "kennzahlen": {}}
    monkeypatch.setattr(befehle.aufnahme, "baue_und_pruefe", lambda *a, **k: mangel)
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_PRUEFUNG" and e.value.daten["maengel"][0]["pruefung"] == "koerper"
    fehler = {**mangel, "fehler": {"code": "KAUFTEIL_IMPORT", "schritt": "import", "meldung": "Import gescheitert"}}
    monkeypatch.setattr(befehle.aufnahme, "baue_und_pruefe", lambda *a, **k: fehler)
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_IMPORT"
    assert not (r.kaufteilbibliothek / "2025").exists()


def test_urteil_zur_alten_freigabe_und_muster(umgebung, sw, tmp_path):
    r, katalog, step, blatt = umgebung
    pfad = _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", blatt, katalog=katalog)
    main(["freigeben", str(pfad)])
    datei = tmp_path / "u.json"
    datei.write_text(json.dumps({"bestanden": True, "maengel": []}), encoding="utf-8")
    with pytest.raises(KaufteilFehler) as e:
        befehle.urteil(SCHLUESSEL, datei, "0" * 64, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_UNGEPRUEFT"
    m = befehle.muster(SCHLUESSEL, katalog)
    assert m["bestanden"] is True and m["bilder"] == {"iso": "iso.png"} and m["eintrag"].endswith("gm42-10.freigegeben.yaml")
    assert m["datenblatt"] == str(r.kaufteilbibliothek / "quellen" / "swki-muster" / "datenblatt.md")
    assert ("bau", True) in sw and not (r.kaufteilbibliothek / "2025").exists()


def test_liste_markiert_veralteten_cache(umgebung, sw, tmp_path, monkeypatch, capsys):
    r, katalog, step, _ = umgebung
    pfad = _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    main(["freigeben", str(pfad)])
    _urteil(pfad, tmp_path, katalog)
    befehle.hole(SCHLUESSEL, katalog)
    [t] = befehle.liste(katalog=katalog)["teile"]
    assert t == {"schluessel": SCHLUESSEL, "gueltig": True, "freigegeben": True, "geprueft": True, "cache": True}
    assert befehle.liste(nur_veraltet=True, katalog=katalog)["teile"] == []
    monkeypatch.setattr(cache, "IMPORTWEG_VERSION", cache.IMPORTWEG_VERSION + 1)
    assert befehle.liste(nur_veraltet=True, katalog=katalog)["teile"][0]["cache"] is False
    monkeypatch.setattr(kat, "ORDNER", katalog)
    capsys.readouterr()
    assert main(["kaufteil", "liste"]) == 0 and json.loads(capsys.readouterr().out)["teile"][0]["cache"] is False
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile\test_befehle_kaufteile.py`
Expected: FAIL – `1 error` (`ImportError: cannot import name 'befehle' from 'swki.kaufteile'`).

- [ ] **Step 3: Umsetzen**

`swki/kaufteile/quelle.py` anlegen:

```python
"""Originale der Kaufteile (Spec 3c §5.1, §7): unveränderte Kopien im Quellordner
<kaufteilbibliothek>/quellen/<hersteller>/. Dateien des Nutzers werden nur gelesen; im Quellordner wird nie etwas
überschrieben (eine neue Herstellerversion bekommt einen eigenen Namen)."""

import shutil
from pathlib import Path

from swki.aenderungen import sha256_datei
from swki.kaufteile.fehler import KAUFTEIL_FORMAT, KAUFTEIL_QUELLE_ABWEICHEND, KAUFTEIL_QUELLE_FEHLT, KaufteilFehler
from swki.kaufteile.katalog import dateiname, ordnername
from swki.konfig import Rechner, swki_home

ENDUNGEN = (".step", ".stp")


def bibliothek(r: Rechner) -> Path:
    return r.kaufteilbibliothek or swki_home() / "kaufteile"


def quellordner(r: Rechner, hersteller: str) -> Path:
    return bibliothek(r) / "quellen" / ordnername(hersteller)


def pruefe_format(pfad: Path) -> None:
    if pfad.suffix.lower() not in ENDUNGEN:
        raise KaufteilFehler(KAUFTEIL_FORMAT, f"{pfad.name}: nur STEP ({', '.join(ENDUNGEN)}) – andere Formate beim "
                                              "Hersteller als STEP holen", erlaubt=list(ENDUNGEN))


def _kopiere(quelle: Path, ziel: Path, sha: str) -> bool:
    """Kopie anlegen, wenn sie fehlt; liegt dort schon eine Datei, muss sie gleich sein (nie überschreiben)."""
    if ziel.exists():
        vorhanden = sha256_datei(ziel)
        if vorhanden != sha:
            raise KaufteilFehler(KAUFTEIL_QUELLE_ABWEICHEND, f"{ziel.name} liegt schon im Quellordner mit anderem "
                                                             "Inhalt", pfad=str(ziel), vorhanden=vorhanden, neu=sha)
        return False
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(quelle, ziel)
    return True


def uebernimm(r: Rechner, quelle: Path, hersteller: str, bestellnummer: str, eintrag: dict | None = None,
              neue_version: bool = False) -> dict:
    """Original in den Quellordner kopieren. Mit vorhandenem Katalogeintrag muss die Datei dessen SHA-256 haben (so
    stellt ein anderer Rechner das Original wieder her); --neue-version legt sie als <datei>.<sha8>.<endung> ab."""
    pruefe_format(quelle)
    if not quelle.is_file():
        raise KaufteilFehler(KAUFTEIL_QUELLE_FEHLT, f"{quelle} fehlt", pfad=str(quelle))
    sha = sha256_datei(quelle)
    ordner = quellordner(r, hersteller)
    endung = quelle.suffix.lower()
    if neue_version:
        ziel = ordner / f"{dateiname(bestellnummer)}.{sha[:8]}{endung}"
    elif eintrag is not None:
        if sha != eintrag["original"]["sha256"]:
            raise KaufteilFehler(KAUFTEIL_QUELLE_ABWEICHEND,
                                 f"{quelle.name} weicht vom Katalogeintrag ab – neue Herstellerversion? Nutzer fragen; "
                                 "dann swki kaufteil untersuchen … --neue-version",
                                 eintrag=eintrag["original"]["sha256"], neu=sha)
        ziel = ordner / eintrag["original"]["datei"]
    else:
        ziel = ordner / f"{dateiname(bestellnummer)}{endung}"
    kopiert = False if quelle.resolve() == ziel.resolve() else _kopiere(quelle, ziel, sha)
    return {"datei": ziel.name, "pfad": str(ziel), "sha256": sha, "kopiert": kopiert}


def uebernimm_datenblatt(r: Rechner, quelle: Path, hersteller: str) -> dict:
    if not quelle.is_file():
        raise KaufteilFehler(KAUFTEIL_QUELLE_FEHLT, f"{quelle} fehlt", pfad=str(quelle))
    ziel = quellordner(r, hersteller) / quelle.name
    sha = sha256_datei(quelle)
    kopiert = False if quelle.resolve() == ziel.resolve() else _kopiere(quelle, ziel, sha)
    return {"datei": ziel.name, "pfad": str(ziel), "sha256": sha, "kopiert": kopiert}


def original(r: Rechner, spec: dict) -> Path:
    """Original eines Eintrags im Quellordner; fehlt es oder weicht es ab, Fehler mit Code."""
    pfad = quellordner(r, spec["hersteller"]) / spec["original"]["datei"]
    if not pfad.is_file():
        raise KaufteilFehler(KAUFTEIL_QUELLE_FEHLT, f"{pfad} fehlt – Nutzer gibt die Datei erneut: swki kaufteil "
                                                    "untersuchen <step> --hersteller … --bestellnummer …", pfad=str(pfad))
    if (sha := sha256_datei(pfad)) != spec["original"]["sha256"]:
        raise KaufteilFehler(KAUFTEIL_QUELLE_ABWEICHEND, f"{pfad.name} im Quellordner weicht vom Eintrag ab",
                             pfad=str(pfad), eintrag=spec["original"]["sha256"], vorhanden=sha)
    return pfad
```

`swki/kaufteile/cache.py` anlegen:

```python
"""Cache der Kaufteile (Spec 3c §5.3, §7): <kaufteilbibliothek>/<sw_jahr>/<schluessel>.sldprt + .json, nicht im Git.
Maßgeblich sind Katalogeintrag und Original; die Datei ist jederzeit neu erzeugbar. Gültig ist ein Cache-Eintrag nur
mit gleicher Cache-Prüfsumme, bestandener Prüfung und unveränderter .sldprt (SHA-256)."""

import hashlib
import json
import os
import shutil
from pathlib import Path

from swki.aenderungen import sha256_datei
from swki.kaufteile.quelle import bibliothek
from swki.konfig import Rechner
from swki.spec.freigabe import pruefsumme

IMPORTWEG_VERSION = 1  # bei jeder Änderung an Import, Ortung oder Bezugsgeometrie erhöhen (Spec 3c §5.3)


def cacheordner(r: Rechner) -> Path:
    return bibliothek(r) / str(r.sw_jahr)


def cache_pruefsumme(spec: dict) -> str:
    inhalt = {"freigabe": pruefsumme(spec), "original": spec["original"]["sha256"], "importweg": IMPORTWEG_VERSION}
    return hashlib.sha256(json.dumps(inhalt, sort_keys=True).encode("utf-8")).hexdigest()


def teil_pfad(ordner: Path, schluessel: str) -> Path:
    return ordner / f"{schluessel}.sldprt"


def lies(ordner: Path, schluessel: str) -> dict | None:
    pfad = ordner / f"{schluessel}.json"
    if not pfad.is_file():
        return None
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None  # defekter Eintrag gilt als fehlend: neu aufnehmen


def ist_aktuell(ordner: Path, schluessel: str, summe: str) -> bool:
    e = lies(ordner, schluessel)
    teil = teil_pfad(ordner, schluessel)
    return (e is not None and e.get("pruefsumme") == summe and e.get("bestanden") is True and teil.is_file()
            and sha256_datei(teil) == e.get("sldprt_sha256"))


def lege_ab(ordner: Path, schluessel: str, teil: Path, eintrag: dict) -> Path:
    """Geprüftes Teil in den Cache kopieren, dann den Eintrag atomar schreiben (ohne Eintrag gilt die Datei als veraltet)."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = teil_pfad(ordner, schluessel)
    shutil.copy2(teil, ziel)
    daten = {**eintrag, "sldprt_sha256": sha256_datei(ziel)}
    tmp = ordner / f"{schluessel}.json.tmp"
    tmp.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, ordner / f"{schluessel}.json")
    return ziel
```

`swki/kaufteile/befehle.py` anlegen:

```python
"""Befehle "swki kaufteil untersuchen|muster|urteil|hole|liste" (Spec 3c §5). Validieren und Freigeben des Eintrags
laufen über die gemeinsamen Befehle (Weiche nach art in swki.spec.befehle)."""

import json
from datetime import date
from pathlib import Path

from swki.auftrag import laeufe, lauf_ordner
from swki.kaufteile import aufnahme, cache, katalog as kat, quelle
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.fehler import KAUFTEIL_PRUEFUNG, KAUFTEIL_UNGEPRUEFT, KaufteilFehler
from swki.kaufteile.katalog import (bibliotheksschluessel, eintrag_pfad, eintraege, finde, geprueft, schluessel,
                                    urteil_pfad)
from swki.konfig import lade_rechner
from swki.pruefung.schleife import lies_urteil
from swki.spec.freigabe import FreigabeFehler, kopie_pfad, pruefe_freigabe, pruefsumme
from swki.spec.laden import SpecFehler, lade_yaml

AUFTRAG = "KAUFTEILE"


def _laufordner(r, bib_schluessel: str) -> tuple[Path, int]:
    """(Ordner, Nummer) des neuen Laufs <arbeitsordner>/KAUFTEILE/<schluessel>/lauf-<n> (bleibt zur Analyse stehen)."""
    auftrag = f"{AUFTRAG}/{bib_schluessel}"
    bisher = laeufe(r, auftrag)
    nummer = bisher[-1] + 1 if bisher else 1
    return lauf_ordner(r, auftrag, nummer), nummer


def _schreibe_json(pfad: Path, daten: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def geruest(hersteller: str, bestellnummer: str, original: dict, datenblatt: dict | None, diagnose: dict) -> dict:
    """Anfang eines Katalogeintrags aus der Diagnose; Claude ergänzt Benennung, Material, Belege, Einbau, Prüfwerte."""
    g = {"art": "kaufteil", "hersteller": hersteller, "bestellnummer": bestellnummer, "benennung": "",
         "original": {"datei": original["datei"], "sha256": original["sha256"],
                      "bezug": {"art": "nutzer", "datum": date.today().isoformat()}}}
    if datenblatt is not None:
        g["datenblatt"] = {"datei": datenblatt["datei"]}
    return g | {"koerper": diagnose["koerper"], "material": "", "einbau": {},
                "pruefung": {"volumen": {"soll": diagnose["volumen"], "toleranz_prozent": 0.01}}}


def untersuchen(step: Path, hersteller: str, bestellnummer: str, datenblatt: Path | None = None,
                neue_version: bool = False, katalog: Path | None = None) -> dict:
    """Original (und Datenblatt) in den Quellordner kopieren, importieren und diagnostizieren; schreibt nichts in den
    Katalog und nichts in den Cache (Spec 3c §5.1)."""
    quelle.pruefe_format(step)
    r = lade_rechner()
    pfad = eintrag_pfad(hersteller, bestellnummer, katalog)
    vorhanden = lade_yaml(pfad) if pfad.is_file() else None
    original = quelle.uebernimm(r, step, hersteller, bestellnummer, None if neue_version else vorhanden, neue_version)
    blatt = quelle.uebernimm_datenblatt(r, datenblatt, hersteller) if datenblatt is not None else None
    lauf, _ = _laufordner(r, bibliotheksschluessel(hersteller, bestellnummer))
    diagnose = aufnahme.untersuche(Path(original["pfad"]), lauf)
    _schreibe_json(lauf / "diagnose.json", diagnose)
    return {"schluessel": schluessel(hersteller, bestellnummer), "eintrag": str(pfad), "eintrag_vorhanden": vorhanden is not None,
            "original": original, "datenblatt": blatt, "lauf": str(lauf), "diagnose": diagnose,
            "geruest": geruest(hersteller, bestellnummer, original, blatt, diagnose)}


def _freigegeben(text: str, katalog: Path | None) -> tuple[Path, dict]:
    pfad = finde(text, katalog)
    spec = lade_eintrag(pfad)
    pruefe_freigabe(pfad, spec)
    return pfad, spec


def _baue(spec: dict, r, mit_bildern: bool) -> tuple[Path, dict]:
    original = quelle.original(r, spec)
    lauf, _ = _laufordner(r, bibliotheksschluessel(spec["hersteller"], spec["bestellnummer"]))
    ergebnis = aufnahme.baue_und_pruefe(spec, original, lauf, mit_bildern)
    _schreibe_json(lauf / "pruefbericht.json", ergebnis)
    return lauf, ergebnis


def hole(text: str, katalog: Path | None = None) -> dict:
    """Kaufteil aus dem Cache oder neu aufnehmen, prüfen und ablegen (Spec 3c §5.3)."""
    pfad, spec = _freigegeben(text, katalog)
    r = lade_rechner()
    ordner = cache.cacheordner(r)
    bib = bibliotheksschluessel(spec["hersteller"], spec["bestellnummer"])
    summe = cache.cache_pruefsumme(spec)
    if cache.ist_aktuell(ordner, bib, summe):
        e = cache.lies(ordner, bib)
        return {"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "pfad": str(cache.teil_pfad(ordner, bib)),
                "gebaut": False, "pruefsumme": summe, "gewinde_modell": e.get("gewinde_modell", {}),
                "pruefung": {"bestanden": True, "datum": e.get("datum")}}
    if not geprueft(pfad, spec):
        raise KaufteilFehler(KAUFTEIL_UNGEPRUEFT, f"{text}: kein bestandenes Prüfer-Urteil zur aktuellen Freigabe – "
                                                  f"swki kaufteil muster \"{text}\", Prüfer-Agent, swki kaufteil urteil",
                             freigabe_pruefsumme=pruefsumme(spec))
    lauf, ergebnis = _baue(spec, r, mit_bildern=False)
    if ergebnis["fehler"] is not None:
        f = ergebnis["fehler"]
        raise KaufteilFehler(f["code"], f"{text}: {f['meldung']}", ordner=str(lauf))
    if not ergebnis["bestanden"]:
        raise KaufteilFehler(KAUFTEIL_PRUEFUNG, f"{text}: Prüfung nicht bestanden ({len(ergebnis['maengel'])} Mängel)",
                             maengel=ergebnis["maengel"], ordner=str(lauf))
    eintrag = {"schluessel": bib, "hersteller": spec["hersteller"], "bestellnummer": spec["bestellnummer"],
               "pruefsumme": summe, "bestanden": True, "pruefungen": [p["id"] for p in ergebnis["pruefungen"]],
               "gewinde_modell": ergebnis["gewinde_modell"], "kennzahlen": ergebnis["kennzahlen"],
               "datum": date.today().isoformat(), "sw_jahr": r.sw_jahr, "lauf": str(lauf)}
    ziel = cache.lege_ab(ordner, bib, Path(ergebnis["teil"]), eintrag)
    return {"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "pfad": str(ziel), "gebaut": True,
            "pruefsumme": summe, "gewinde_modell": ergebnis["gewinde_modell"], "lauf": str(lauf),
            "pruefung": {"bestanden": True, "pruefungen": len(ergebnis["pruefungen"])}}


def muster(text: str, katalog: Path | None = None) -> dict:
    """Musterteil mit Bildern für den Prüfer-Agenten; braucht die Freigabe, kein Urteil, legt nichts im Cache ab."""
    pfad, spec = _freigegeben(text, katalog)
    r = lade_rechner()
    lauf, ergebnis = _baue(spec, r, mit_bildern=True)
    blatt = spec.get("datenblatt", {}).get("datei")
    return {"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "bestanden": ergebnis["bestanden"],
            "maengel": ergebnis["maengel"], "fehler": ergebnis["fehler"], "freigabe_pruefsumme": pruefsumme(spec),
            "eintrag": str(kopie_pfad(pfad)), "pruefbericht": str(lauf / "pruefbericht.json"), "bilder": ergebnis["bilder"],
            "datenblatt": str(quelle.quellordner(r, spec["hersteller"]) / blatt) if blatt else None}


def urteil(text: str, datei: Path, freigabe_summe: str, katalog: Path | None = None) -> dict:
    """Prüfer-Urteil (rohes JSON des Prüfer-Agenten) zur aktuellen Freigabe ablegen."""
    pfad, spec = _freigegeben(text, katalog)
    aktuell = pruefsumme(spec)
    if freigabe_summe != aktuell:
        raise KaufteilFehler(KAUFTEIL_UNGEPRUEFT, f"{text}: Eintrag seit dem Musterteil geändert – neu prüfen",
                             freigabe_pruefsumme=aktuell)
    u = lies_urteil(datei)
    if u is None:
        raise KaufteilFehler(KAUFTEIL_UNGEPRUEFT, f"Urteil {datei} fehlt")
    inhalt = {"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "freigabe_pruefsumme": aktuell,
              "bestanden": u["bestanden"], "maengel": u["maengel"], "datum": date.today().isoformat()}
    _schreibe_json(urteil_pfad(pfad), inhalt)
    return {"datei": str(urteil_pfad(pfad)), **inhalt}


def liste(nur_veraltet: bool = False, katalog: Path | None = None) -> dict:
    r = lade_rechner()
    ordner = cache.cacheordner(r)
    teile = []
    for pfad in eintraege(katalog):
        try:
            spec = lade_eintrag(pfad)
        except SpecFehler as e:
            teile.append({"datei": str(pfad), "gueltig": False, "befunde": len(e.daten["befunde"])})
            continue
        try:
            pruefe_freigabe(pfad, spec)
            frei = True
        except FreigabeFehler:
            frei = False
        bib = bibliotheksschluessel(spec["hersteller"], spec["bestellnummer"])
        im_cache = cache.lies(ordner, bib) is not None
        teile.append({"schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "gueltig": True,
                      "freigegeben": frei, "geprueft": geprueft(pfad, spec),
                      "cache": cache.ist_aktuell(ordner, bib, cache.cache_pruefsumme(spec)) if im_cache else None})
    if nur_veraltet:
        teile = [t for t in teile if t.get("cache") is False]
    return {"katalog": str(kat.ORDNER if katalog is None else katalog), "cache": str(ordner), "teile": teile}


def einrichten(subparsers) -> None:
    gruppe = subparsers.add_parser("kaufteil", help="Kaufteile (STEP) untersuchen, prüfen, holen").add_subparsers(
        dest="unterbefehl", required=True)
    p = gruppe.add_parser("untersuchen", help="STEP in den Quellordner kopieren, importieren, Diagnose (schreibt nichts in den Katalog)")
    p.add_argument("step")
    p.add_argument("--hersteller", required=True)
    p.add_argument("--bestellnummer", required=True)
    p.add_argument("--datenblatt")
    p.add_argument("--neue-version", action="store_true", help="neue Herstellerversion neben dem alten Original ablegen")
    p.set_defaults(func=lambda a: untersuchen(Path(a.step), a.hersteller, a.bestellnummer,
                                              Path(a.datenblatt) if a.datenblatt else None, a.neue_version))
    p = gruppe.add_parser("muster", help="Musterteil mit Bildern für den Prüfer-Agenten (freigegebener Eintrag)")
    p.add_argument("schluessel")
    p.set_defaults(func=lambda a: muster(a.schluessel))
    p = gruppe.add_parser("urteil", help="Prüfer-Urteil zur aktuellen Freigabe ablegen")
    p.add_argument("schluessel")
    p.add_argument("datei")
    p.add_argument("--freigabe-pruefsumme", required=True)
    p.set_defaults(func=lambda a: urteil(a.schluessel, Path(a.datei), a.freigabe_pruefsumme))
    p = gruppe.add_parser("hole", help="Kaufteil aus dem Cache holen oder aufnehmen, prüfen und ablegen")
    p.add_argument("schluessel")
    p.set_defaults(func=lambda a: hole(a.schluessel))
    p = gruppe.add_parser("liste", help="Katalog und Cache anzeigen")
    p.add_argument("--veraltet", action="store_true")
    p.set_defaults(func=lambda a: liste(a.veraltet))
```

In `swki/cli.py` ersetzen:

```python
    from swki.api import bauen
    from swki.compiler import bauen as compiler_bauen
    from swki.normteile import befehle as normteil_befehle
    from swki.pruefung import befehle as pruefung_befehle
    from swki.spec import befehle as spec_befehle

    return [rechner, bauen, spec_befehle, compiler_bauen, pruefung_befehle, normteil_befehle, aenderungen]
```

durch:

```python
    from swki.api import bauen
    from swki.compiler import bauen as compiler_bauen
    from swki.kaufteile import befehle as kaufteil_befehle
    from swki.normteile import befehle as normteil_befehle
    from swki.pruefung import befehle as pruefung_befehle
    from swki.spec import befehle as spec_befehle

    return [rechner, bauen, spec_befehle, compiler_bauen, pruefung_befehle, normteil_befehle, kaufteil_befehle,
            aenderungen]
```

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile\test_befehle_kaufteile.py`
Expected: `10 passed`. Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **903 passed, 138 deselected**;
`.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` → `"befunde": []`.

- [ ] **Step 5: Commit**

```powershell
git add swki/kaufteile/quelle.py swki/kaufteile/cache.py swki/kaufteile/befehle.py swki/cli.py tests/kaufteile/test_befehle_kaufteile.py
git commit -m "kaufteile: Quellordner, Cache, Befehle swki kaufteil untersuchen|muster|urteil|hole|liste (Stufe 3c, Task 6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Muster-Eintrag aufnehmen – untersuchen, Nutzerfreigabe, Prüfer, hole (live)

**Files:**
- Create: `swki/wissen/kaufteile/swki-muster/gm42-10.yaml` (dazu von swki: `freigabe.json`, `gm42-10.freigegeben.yaml`,
  `gm42-10.pruefer.json`)
- Test: `tests/live/test_live_kaufteil_hole.py`

**Interfaces:**
- Consumes: Tasks 1–6, die Test-STEP aus Task 2.
- Produces: den freigegebenen und geprüften Katalogeintrag `SWKI-MUSTER GM42-10` (Tasks 9–11 brauchen ihn), den Live-Test für
  `hole` mit Cache-Treffer.

- [ ] **Step 1: Untersuchen (live)**

Vorbedingungen wie Task 5 Step 5. Run:
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m swki kaufteil untersuchen tests\referenz\motorhalter\muster\gm42-10.step --hersteller SWKI-MUSTER --bestellnummer GM42-10 --datenblatt tests\referenz\motorhalter\muster\datenblatt.md`
Expected: `original.kopiert` true (erster Lauf), `diagnose.koerper` 2, `flaechenkoerper` 0, `interconnect` [], Zylinder Ø 10 / 40 /
56 / 4,2 in `diagnose.zylinder`. Aus `geruest` notieren: `original.sha256` und `pruefung.volumen.soll`. Bilder unter `lauf`
ansehen (Sichtprobe).

- [ ] **Step 2: Eintrag anlegen**

`swki/wissen/kaufteile/swki-muster/gm42-10.yaml` anlegen – **`<SHA256>` und `<VOLUMEN>` durch die Werte aus Step 1 ersetzen**
(SHA-256 in Anführungszeichen, Volumen als Zahl mit drei Nachkommastellen); sonst nichts ändern:

```yaml
# Muster-Getriebemotor (fiktiv, Spec 3c §11): Testeintrag der Stufe 3c. Original: tests/referenz/motorhalter/muster/gm42-10.step
# (aus gm42.yaml per SaveAs3), Datenblatt: muster/datenblatt.md. STEP-Koordinaten: Flanschfläche y = 0 (Normale −y),
# Zentrierbund y −3…0, Welle Ø 10 bis y = −25, Gehäuse bis y = 82; 4 × M5 auf Lochkreis Ø 60.
art: kaufteil
hersteller: SWKI-MUSTER
bestellnummer: GM42-10
benennung: Getriebemotor GM42, i = 10 (Muster)
original:
  datei: gm42-10.step
  sha256: "<SHA256>"
  bezug: {art: nutzer, datum: "2026-10-07", hinweis: "Test-STEP aus tests/referenz/motorhalter/muster (Spike S15)"}
datenblatt: {datei: datenblatt.md}
koerper: 2
material: "1.0038"
masse: {kg: 1.2, beleg: [d1]}
eigenschaften: {Benennung: Getriebemotor GM42-10}
belege:
  d1: {art: datenblatt, datei: datenblatt.md, seite: 1}
einbau:
  EINBAU_ACHSE: {zylinder: {nahe: [5, -15, 0], durchmesser: 10, senkrecht_zu: EINBAU_FLANSCH}}
  EINBAU_FLANSCH: {ebene: {nahe: [25, 0, 25], normale: [0, -1, 0]}}
  EINBAU_DREHLAGE: {ebene_durch_achse: {achse: EINBAU_ACHSE, nahe: [0, 0, 25]}}
gewinde:
  flansch:
    groesse: M5
    gewindetiefe: 8
    tiefe: 10
    normale: [0, -1, 0]
    beleg: [d1]
    positionen: [[21.2132, 0, 21.2132], [-21.2132, 0, 21.2132], [-21.2132, 0, -21.2132], [21.2132, 0, -21.2132]]
pruefung:
  huellquader: {soll: [60, 107, 60], tol: 0.1, beleg: [d1]}
  volumen: {soll: <VOLUMEN>, toleranz_prozent: 0.01}
  durchmesser_pruefen:
    - {was: Wellen-Ø, nahe: [5, -15, 0], soll: 10, referenz: EINBAU_ACHSE, beleg: [d1]}
    - {was: Zentrierbund-Ø, nahe: [20, -1.5, 0], soll: 40, referenz: EINBAU_ACHSE, beleg: [d1]}
  masse_pruefen:
    - {was: Wellenüberstand, von: {referenz: EINBAU_FLANSCH}, zu: {flaeche: {nahe: [0, -25, 0], normale: [0, -1, 0]}},
       soll: 25, tol: 0.05, beleg: [d1]}
    - {was: Lochabstand, von: {gewinde: flansch, instanz: 1}, zu: {gewinde: flansch, instanz: 2}, soll: 42.4264, tol: 0.05,
       beleg: [d1]}
```

Run: `.venv\Scripts\python.exe -m swki validieren swki\wissen\kaufteile\swki-muster\gm42-10.yaml`
Expected: `"gueltig": true`, `"art": "kaufteil"`, `"hinweise": []`.

- [ ] **Step 3: Nutzerfreigabe (Controller)**

BLOCKED an den Controller: Der **Controller legt dem Nutzer** Eintrag, Diagnosebilder und Belege vor (Kennmaße mit Beleg `d1`,
Bedeutung der drei Einbaureferenzen, Masse 1,2 kg) und fragt nach dem OK – eine Frage, Empfehlung „freigeben“. Erst nach
ausdrücklichem OK: `.venv\Scripts\python.exe -m swki freigeben swki\wissen\kaufteile\swki-muster\gm42-10.yaml`.

- [ ] **Step 4: Musterteil und Prüfer (Controller)**

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m swki kaufteil muster "SWKI-MUSTER GM42-10"`
Expected: `bestanden` true, `maengel` [], `fehler` null, Bilder vorhanden. Der **Controller** startet den Prüfer-Agenten
(`subagent_type: pruefer`) mit `eintrag`, `datenblatt`, `pruefbericht` und den Bildern aus der Ausgabe und schreibt sein Urteil
unverändert (nur das JSON-Objekt) in `auftraege/KAUFTEIL-MUSTER/urteil.json`; dann
`.venv\Scripts\python.exe -m swki kaufteil urteil "SWKI-MUSTER GM42-10" auftraege\KAUFTEIL-MUSTER\urteil.json --freigabe-pruefsumme <freigabe_pruefsumme aus muster>`.
Mängel des Prüfers: Eintrag nach Rücksprache mit dem Nutzer korrigieren (neue Freigabe), nie still.

- [ ] **Step 5: Live-Test `hole`**

`tests/live/test_live_kaufteil_hole.py` anlegen:

```python
"""Live: swki kaufteil hole am freigegebenen und geprüften Muster-Eintrag (Spec 3c §5.3) mit eigenem Cache; der
zweite Aufruf ist ein Cache-Treffer."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from swki.kaufteile import befehle, quelle
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.katalog import finde
from swki.konfig import PROJEKT, lade_rechner

pytestmark = pytest.mark.sw
STEP = PROJEKT / "tests" / "referenz" / "motorhalter" / "muster" / "gm42-10.step"
SCHLUESSEL = "SWKI-MUSTER GM42-10"


def test_hole_baut_und_trifft_den_cache(tmp_path, monkeypatch):
    r = replace(lade_rechner(), kaufteilbibliothek=tmp_path / "kauf")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    quelle.uebernimm(r, STEP, "SWKI-MUSTER", "GM42-10", lade_eintrag(finde(SCHLUESSEL)))
    erst = befehle.hole(SCHLUESSEL)
    assert erst["gebaut"] is True and erst["gewinde_modell"] == {"flansch": "kernloch"}
    eintrag = json.loads(Path(erst["pfad"]).with_suffix(".json").read_text(encoding="utf-8"))
    assert eintrag["bestanden"] is True and eintrag["kennzahlen"]["interconnect"] == []
    zweit = befehle.hole(SCHLUESSEL)
    assert zweit["gebaut"] is False and zweit["pfad"] == erst["pfad"]
```

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_kaufteil_hole.py --zeit 600`
Expected: `OK`. Danach `.venv\Scripts\python.exe -m swki kaufteil hole "SWKI-MUSTER GM42-10"` (echter Cache: `gebaut` true,
zweiter Aufruf false) und `.venv\Scripts\python.exe -m swki kaufteil liste` (`freigegeben`, `geprueft`, `cache` true).
Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **903 passed, 139 deselected**.

- [ ] **Step 6: Commit**

```powershell
git add swki/wissen/kaufteile tests/live/test_live_kaufteil_hole.py
git commit -m "kaufteile: Muster-Eintrag SWKI-MUSTER GM42-10 mit Freigabe und Prüfer-Urteil (Stufe 3c, Task 7)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Baugruppen – Format, Laden, Plausibilität, Passung, Freigabe (ohne SolidWorks)

**Files:**
- Modify: `schema/baugruppe.schema.json`, `swki/baugruppe/modell.py`, `swki/baugruppe/laden.py`, `swki/baugruppe/aufloesen.py`,
  `swki/baugruppe/plausibel.py`, `swki/baugruppe/passung.py`, `swki/baugruppe/freigabe.py`, `swki/baugruppe/hinweise.py`,
  `swki/spec/freigabe.py`
- Test: `tests/baugruppe/beispiel_kaufteil.py`, `tests/baugruppe/test_kaufteil_baugruppe.py`

**Interfaces:**
- Consumes: Task 3 (`katalog.finde`/`geprueft`/`bibliotheksschluessel`/`urteil_pfad`, `eintrag.lade_eintrag`/`freigeben`),
  Testhilfe `tests/kaufteile/beispiel.py`.
- Produces:
  - `Quelle.eintrag`, `Quelle.eintrag_pfad`, `Quelle.kaufteil` (Schlüssel-Text); Quelle `art: kaufteil` mit Teilansicht
    `laden.kaufteil_spec(eintrag)`.
  - Referenz `{komponente, gewinde, instanz, achse: true}`, `je_position: {komponente, gewinde}`; `aufloesen.anzahl_positionen`
    für Gewindegruppen; `plausibel.je_ziel(je)`.
  - `freigabe.kaufteil_summen(bg)`, `teil_summen(bg)` mit `kaufteil:<Schlüssel>`; `swki.spec.freigabe.freigeben(…, zusatz=None)`,
    `freigabe_eintrag(spec_pfad)`.
  - Testhilfe `tests/baugruppe/beispiel_kaufteil.py`: `HALTER`, `BAUGRUPPE`, `L`, `kopie`, `katalog(ordner, monkeypatch,
    eintrag=None, geprueft=True) -> Path`, `schreibe(ordner, baugruppe=None) -> Path`.

- [ ] **Step 1: Tests schreiben**

`tests/baugruppe/beispiel_kaufteil.py` anlegen:

```python
"""Kleine Baugruppe mit Kaufteil für Tests (selbst formuliert): Halter (fixiert) mit Zentrierbohrung Ø 40 und
4 Senkungen M5, Muster-Getriebemotor aus dem Katalog (tests/kaufteile/beispiel.py), 4 × ISO 4762 M5 x 12 je Senkung.
Der Katalog liegt in einem Testordner; katalog() schreibt den Eintrag, gibt ihn frei und legt ein Prüfer-Urteil ab."""

import copy
import json
from pathlib import Path

import yaml

from swki.kaufteile import katalog as kat
from swki.kaufteile.eintrag import freigeben
from swki.spec.freigabe import pruefsumme
from tests.kaufteile.beispiel import EINTRAG, schreibe as schreibe_eintrag

L = 21.2132
HALTER = {
    "art": "teil", "name": "Halter", "material": "1.0038", "eigenschaften": {"Benennung": "Halter"},
    "parameter": {"B": 80, "H": 10, "Z": 40, "LK": 60},
    "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=B", "hoehe": "=B"}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}},
        {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 0]],
         "durchmesser": "=Z", "durch": True},
        {"id": "f3", "typ": "normbohrung", "art": "zylinderschraube", "groesse": "M5",
         "flaeche": {"feature": "f1", "flaeche": "-y"},
         "positionen": [["=LK/8**0.5", "=LK/8**0.5"], ["=-LK/8**0.5", "=LK/8**0.5"], ["=-LK/8**0.5", "=-LK/8**0.5"],
                        ["=LK/8**0.5", "=-LK/8**0.5"]], "durch": True},
    ],
}
BAUGRUPPE = {
    "art": "baugruppe", "name": "Motorprobe", "eigenschaften": {"Benennung": "Motorprobe"},
    "komponenten": [
        {"id": "halter", "quelle": {"teil": "halter.yaml"}, "fixiert": True},
        {"id": "motor", "quelle": {"kaufteil": "SWKI-MUSTER GM42-10"}},
        {"id": "schraube", "quelle": {"normteil": "ISO 4762 M5x12"}, "je_position": {"komponente": "halter", "feature": "f3"}},
    ],
    "verknuepfungen": [
        {"id": "v1", "typ": "deckungsgleich", "a": {"komponente": "motor", "referenz": "EINBAU_FLANSCH"},
         "b": {"komponente": "halter", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v2", "typ": "konzentrisch", "a": {"komponente": "motor", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "halter", "feature": "f2", "instanz": 1, "achse": True}, "drehung_sperren": False},
        {"id": "v3", "typ": "parallel", "a": {"komponente": "motor", "referenz": "EINBAU_DREHLAGE"},
         "b": {"komponente": "halter", "ebene": "vorne"}, "ausrichtung": "gleich"},
        {"id": "v4", "typ": "deckungsgleich", "a": {"komponente": "schraube", "referenz": "EINBAU_EBENE"},
         "b": {"komponente": "halter", "feature": "f3", "instanz": "je", "flaeche": "-y"}, "ausrichtung": "gleich"},
        {"id": "v5", "typ": "konzentrisch", "a": {"komponente": "schraube", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "halter", "feature": "f3", "instanz": "je", "achse": True}},
    ],
}


def kopie(spec: dict | None = None) -> dict:
    return copy.deepcopy(spec or BAUGRUPPE)


def katalog(ordner: Path, monkeypatch, eintrag: dict | None = None, geprueft: bool = True) -> Path:
    """Eintrag schreiben und freigeben, bestandenes Urteil ablegen, Katalog umbiegen; liefert den Eintragspfad."""
    pfad = schreibe_eintrag(ordner, eintrag or EINTRAG)
    freigeben(pfad)
    if geprueft:
        urteil = {"freigabe_pruefsumme": pruefsumme(eintrag or EINTRAG), "bestanden": True, "maengel": []}
        kat.urteil_pfad(pfad).write_text(json.dumps(urteil), encoding="utf-8")
    monkeypatch.setattr(kat, "ORDNER", ordner)
    return pfad


def schreibe(ordner: Path, baugruppe: dict | None = None) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    for name, spec in (("halter.yaml", HALTER), ("motorprobe.yaml", baugruppe or BAUGRUPPE)):
        (ordner / name).write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ordner / "motorprobe.yaml"
```

`tests/baugruppe/test_kaufteil_baugruppe.py` anlegen:

```python
import json

import pytest
import yaml

from swki.baugruppe.aufloesen import instanzen, verknuepfungen
from swki.baugruppe.freigabe import freigeben_baugruppe, pruefe_freigabe_baugruppe, teil_summen
from swki.baugruppe.hinweise import hinweise_baugruppe
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.modell import dokument_name
from swki.kaufteile.eintrag import freigeben as freigeben_eintrag
from swki.spec.freigabe import FreigabeFehler, freigabe_pfad, pruefsumme
from swki.spec.laden import SpecFehler
from tests.baugruppe.beispiel_kaufteil import katalog, kopie, schreibe
from tests.kaufteile.beispiel import EINTRAG, kopie as eintrag_kopie, schreibe as schreibe_eintrag


def _befunde(pfad) -> list[str]:
    with pytest.raises(SpecFehler) as e:
        lade_baugruppe(pfad)
    return [f"{b['pfad']}: {b['meldung']}" for b in e.value.daten["befunde"]]


def test_laedt_kaufteil(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    q = bg.quellen["motor"]
    assert (q.art, q.schluessel, q.kaufteil) == ("kaufteil", "SWKI-MUSTER_GM42-10", "SWKI-MUSTER GM42-10")
    assert q.referenzen == {"EINBAU_ACHSE", "EINBAU_FLANSCH", "EINBAU_DREHLAGE"} and q.eintrag == EINTRAG
    assert list(q.spec["gewinde"]) == ["flansch"] and list(bg.teile) == ["halter.yaml"]
    assert dokument_name(q, "A", {"namensschema": {"datei": "{auftrag}_{name}"}}) == "SWKI-MUSTER_GM42-10.sldprt"
    assert hinweise_baugruppe(bg) == []


def test_unbekannt_nicht_freigegeben_ungeprueft(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch, geprueft=False)
    spec = kopie()
    [b] = _befunde(schreibe(tmp_path / "A", spec))
    assert b.startswith("komponenten.motor.quelle: KAUFTEIL_UNGEPRUEFT")
    spec["komponenten"][1]["quelle"] = {"kaufteil": "SWKI-MUSTER GM99"}
    [b] = _befunde(schreibe(tmp_path / "B", spec))
    assert b.startswith("komponenten.motor.quelle: KAUFTEIL_UNBEKANNT")
    anders = eintrag_kopie()
    anders["koerper"] = 3
    schreibe_eintrag(tmp_path / "kat", anders)  # geändert, nicht neu freigegeben
    [b] = _befunde(schreibe(tmp_path / "C"))
    assert b.startswith("komponenten.motor.quelle: KAUFTEIL_NICHT_FREIGEGEBEN")


def test_kaufteil_nur_ueber_einbau_und_gewinde(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    spec = kopie()
    spec["verknuepfungen"][0]["a"] = {"komponente": "motor", "feature": "f1", "flaeche": "+y"}
    spec["verknuepfungen"][1]["a"] = {"komponente": "motor", "referenz": "EINBAU_FEHLT"}
    spec["verknuepfungen"][2]["b"] = {"komponente": "halter", "gewinde": "flansch", "instanz": 1, "achse": True}
    befunde = _befunde(schreibe(tmp_path / "A", spec))
    assert befunde[0].startswith("verknuepfungen[0].a: motor ist ein Kaufteil: nur über Einbaureferenzen")
    assert befunde[1].startswith("verknuepfungen[1].a.referenz: SWKI-MUSTER GM42-10 hat keine Einbaureferenz 'EINBAU_FEHLT'")
    assert befunde[2] == "verknuepfungen[2].b.gewinde: halter ist kein Kaufteil: Gewindepositionen nur bei Kaufteilen"


def _ins_gewinde(spec: dict, groesse: str = "M5x12") -> dict:
    spec["komponenten"][2] = {"id": "schraube", "quelle": {"normteil": f"ISO 4762 {groesse}"},
                              "je_position": {"komponente": "motor", "gewinde": "flansch"}}
    spec["verknuepfungen"][3]["b"] = {"komponente": "halter", "feature": "f1", "flaeche": "-y"}
    spec["verknuepfungen"][4]["b"] = {"komponente": "motor", "gewinde": "flansch", "instanz": "je", "achse": True}
    return spec


def test_je_position_auf_kaufteil_gewinde(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    assert [i.id for i in instanzen(bg.spec, bg.quellen)][2:] == ["schraube.1", "schraube.2", "schraube.3", "schraube.4"]
    v = {x.id: x for x in verknuepfungen(bg.spec, bg.quellen)}
    assert v["v5.3"].b == {"komponente": "motor", "gewinde": "flansch", "instanz": 3, "achse": True}
    assert v["v5.3"].drehung_sperren is True and v["v2"].drehung_sperren is False


def test_gewinde_befunde(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    spec = _ins_gewinde(kopie())
    spec["komponenten"][2]["je_position"] = {"komponente": "halter", "gewinde": "flansch"}
    assert "komponenten[2].je_position.komponente: 'halter' ist kein Kaufteil (gewinde)" in _befunde(schreibe(tmp_path / "A", spec))
    spec = _ins_gewinde(kopie())
    spec["komponenten"][2]["je_position"]["gewinde"] = "fuss"
    assert _befunde(schreibe(tmp_path / "B", spec))[0] == ("komponenten[2].je_position.gewinde: SWKI-MUSTER GM42-10 hat "
                                                         "keine Gewindegruppe 'fuss'")


def test_passung_im_kaufteil_gewinde(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    [b] = _befunde(schreibe(tmp_path / "A", _ins_gewinde(kopie(), "M6x12")))
    assert b == "verknuepfungen[4]: Passung: ISO 4762 M6 passt nicht in Gewinde M5 von SWKI-MUSTER GM42-10"


def test_hinweis_drehlage_doppelt(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    spec = kopie()
    del spec["verknuepfungen"][1]["drehung_sperren"]
    [h] = hinweise_baugruppe(lade_baugruppe(schreibe(tmp_path / "A", spec)))
    assert (h["art"], h["pfad"]) == ("drehlage_doppelt", "verknuepfungen[1].drehung_sperren")


def test_freigabe_schuetzt_den_eintrag(tmp_path, monkeypatch):
    eintrag_pfad = katalog(tmp_path / "kat", monkeypatch)
    pfad = schreibe(tmp_path / "A")
    bg = lade_baugruppe(pfad)
    assert teil_summen(bg)["kaufteil:SWKI-MUSTER GM42-10"] == pruefsumme(EINTRAG)
    freigeben_baugruppe(bg)
    daten = json.loads(freigabe_pfad(pfad).read_text(encoding="utf-8"))
    assert daten["motorprobe.yaml"]["kaufteile"] == {"kaufteil:SWKI-MUSTER GM42-10": pruefsumme(EINTRAG)}
    pruefe_freigabe_baugruppe(bg)
    anders = eintrag_kopie()
    anders["pruefung"]["huellquader"]["tol"] = 0.2
    schreibe_eintrag(tmp_path / "kat", anders)
    freigeben_eintrag(eintrag_pfad)  # der Eintrag ist neu freigegeben, die Baugruppe nicht
    katalog(tmp_path / "kat", monkeypatch, anders)
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe_baugruppe(lade_baugruppe(pfad))
    assert e.value.daten["code"] == "FREIGABE_VERALTET" and str(e.value).startswith("SWKI-MUSTER GM42-10: Katalogeintrag")


def test_baugruppe_ohne_kaufteile_unveraendert(tmp_path):
    from tests.baugruppe.beispiel import schreibe as schreibe_probe

    pfad = schreibe_probe(tmp_path / "A")
    eintrag = freigeben_baugruppe(lade_baugruppe(pfad))
    assert "kaufteile" not in json.loads(freigabe_pfad(pfad).read_text(encoding="utf-8"))["probe.yaml"]
    assert set(eintrag) == {"pruefsumme", "freigegeben", "kopie_sha256", "teile"}
    assert yaml.safe_load((tmp_path / "A" / "probe.freigegeben.yaml").read_text(encoding="utf-8"))["name"] == "Probe"
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_kaufteil_baugruppe.py`
Expected: FAIL – `8 failed, 1 passed` (`SpecFehler: das Schema kennt quelle: kaufteil noch nicht`).

- [ ] **Step 3: Umsetzen**

In `schema/baugruppe.schema.json` ersetzen:

```json
      {"type": "object", "required": ["normteil"], "additionalProperties": false,
       "properties": {"normteil": {"type": "string", "pattern": "^\\S.*\\s\\S+$"},
                      "variante": {"type": "string", "minLength": 1}}}
    ]},
    "komponente": {
```

durch:

```json
      {"type": "object", "required": ["normteil"], "additionalProperties": false,
       "properties": {"normteil": {"type": "string", "pattern": "^\\S.*\\s\\S+$"},
                      "variante": {"type": "string", "minLength": 1}}},
      {"type": "object", "required": ["kaufteil"], "additionalProperties": false,
       "properties": {"kaufteil": {"type": "string", "pattern": "^\\S+\\s+\\S(.*\\S)?$"}}}
    ]},
    "komponente": {
```

In `schema/baugruppe.schema.json` ersetzen:

```json
        "quelle": {"$ref": "#/$defs/quelle"},
        "fixiert": {"type": "boolean"},
        "je_position": {"type": "object", "required": ["komponente", "feature"], "additionalProperties": false,
                        "properties": {"komponente": {"$ref": "#/$defs/id"}, "feature": {"$ref": "#/$defs/id"}}},
        "gruppe": {"$ref": "#/$defs/id"}
      }
```

durch:

```json
        "quelle": {"$ref": "#/$defs/quelle"},
        "fixiert": {"type": "boolean"},
        "je_position": {"oneOf": [
          {"type": "object", "required": ["komponente", "feature"], "additionalProperties": false,
           "properties": {"komponente": {"$ref": "#/$defs/id"}, "feature": {"$ref": "#/$defs/id"}}},
          {"type": "object", "required": ["komponente", "gewinde"], "additionalProperties": false,
           "properties": {"komponente": {"$ref": "#/$defs/id"}, "gewinde": {"$ref": "#/$defs/id"}}}
        ]},
        "gruppe": {"$ref": "#/$defs/id"}
      }
```

In `schema/baugruppe.schema.json` ersetzen:

```json
      {"type": "object", "required": ["komponente", "feature", "instanz", "achse"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/id"}, "feature": {"$ref": "#/$defs/id"},
                      "instanz": {"$ref": "#/$defs/instanz"}, "achse": {"const": true}}},
      {"type": "object", "required": ["komponente", "ebene"], "additionalProperties": false,
```

durch:

```json
      {"type": "object", "required": ["komponente", "feature", "instanz", "achse"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/id"}, "feature": {"$ref": "#/$defs/id"},
                      "instanz": {"$ref": "#/$defs/instanz"}, "achse": {"const": true}}},
      {"type": "object", "required": ["komponente", "gewinde", "instanz", "achse"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/id"}, "gewinde": {"$ref": "#/$defs/id"},
                      "instanz": {"$ref": "#/$defs/instanz"}, "achse": {"const": true}}},
      {"type": "object", "required": ["komponente", "ebene"], "additionalProperties": false,
```

In `swki/baugruppe/modell.py` ersetzen:

```python
@dataclass
class Quelle:
    art: str                       # "teil" | "normteil"
    spec: dict                     # Teil-Spezifikation bzw. aus der Bauvorlage erzeugte Normteil-Spezifikation
    datei: str | None = None       # teil: Dateiname der Teil-Spec im Auftragsordner
    norm: str | None = None        # normteil: Norm wie in der Tabelle, z. B. "ISO 4762"
```

durch:

```python
@dataclass
class Quelle:
    art: str                       # "teil" | "normteil" | "kaufteil"
    spec: dict                     # Teil-Spezifikation, aus der Bauvorlage erzeugte Normteil-Spezifikation bzw. Teilansicht
                                   # des Kaufteils (Einbaureferenzen als referenz-Features, Gewindegruppen)
    datei: str | None = None       # teil: Dateiname der Teil-Spec im Auftragsordner
    norm: str | None = None        # normteil: Norm wie in der Tabelle, z. B. "ISO 4762"
```

In `swki/baugruppe/modell.py` ersetzen:

```python
    laenge: float | None = None    # normteil: mm; None bei Teilen ohne Länge
    variante: str | None = None
    schluessel: str | None = None  # normteil: Bibliotheksschlüssel, z. B. "ISO4762_M8x30_8_8"
    masse: dict = field(default_factory=dict)  # normteil: Normmaße der Größe

    @property
    def referenzen(self) -> set[str]:
        """IDs der referenz-Features (bei Normteilen die Einbaureferenzen EINBAU_*)."""
        return {f["id"] for f in self.spec["features"] if f["typ"] == "referenz"}
```

durch:

```python
    laenge: float | None = None    # normteil: mm; None bei Teilen ohne Länge
    variante: str | None = None
    schluessel: str | None = None  # normteil/kaufteil: Bibliotheksschlüssel, z. B. "ISO4762_M8x30_8_8", "SWKI-MUSTER_GM42-10"
    masse: dict = field(default_factory=dict)  # normteil: Normmaße der Größe
    eintrag: dict | None = None    # kaufteil: Katalogeintrag (art: kaufteil)
    eintrag_pfad: Path | None = None  # kaufteil: Datei des Katalogeintrags

    @property
    def kaufteil(self) -> str | None:
        """Schlüssel "<Hersteller> <Bestellnummer>" eines Kaufteils (für swki kaufteil hole)."""
        return f"{self.eintrag['hersteller']} {self.eintrag['bestellnummer']}" if self.eintrag else None

    @property
    def referenzen(self) -> set[str]:
        """IDs der referenz-Features (bei Norm- und Kaufteilen die Einbaureferenzen EINBAU_*)."""
        return {f["id"] for f in self.spec["features"] if f["typ"] == "referenz"}
```

In `swki/baugruppe/modell.py` ersetzen:

```python

def dokument_name(q: Quelle, auftrag: str, standard: dict) -> str:
    """Dateiname im Lauf-Ordner: <auftrag>_<name>.sldprt (Eigenteil) bzw. <schluessel>.sldprt (Normteil-Kopie)."""
    return f"{dateiname(q.spec, auftrag, standard)}.sldprt" if q.art == "teil" else f"{q.schluessel}.sldprt"
```

durch:

```python

def dokument_name(q: Quelle, auftrag: str, standard: dict) -> str:
    """Dateiname im Lauf-Ordner: <auftrag>_<name>.sldprt (Eigenteil) bzw. <schluessel>.sldprt (Norm-/Kaufteil-Kopie)."""
    return f"{dateiname(q.spec, auftrag, standard)}.sldprt" if q.art == "teil" else f"{q.schluessel}.sldprt"
```

In `swki/baugruppe/laden.py` ersetzen:

```python
"""Baugruppen-Spezifikation laden (Spec 3b §5): Schema, Teil-Specs, Normteile, Plausibilität."""

from pathlib import Path
```

durch:

```python
"""Baugruppen-Spezifikation laden (Spec 3b §5, 3c §8.2): Schema, Teil-Specs, Normteile, Kaufteile, Plausibilität."""

from pathlib import Path
```

In `swki/baugruppe/laden.py` ersetzen:

```python
from swki.baugruppe.modell import Baugruppe, Quelle
from swki.baugruppe.plausibel import plausibel_befunde
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.fehler import NormteilFehler
from swki.normteile.schluessel import loese_auf
from swki.normteile.tabelle import lade_normtabelle, pruefe_tabelle
from swki.spec.laden import SpecFehler, lade_spec, lade_yaml, schema_befunde
```

durch:

```python
from swki.baugruppe.modell import Baugruppe, Quelle
from swki.baugruppe.plausibel import plausibel_befunde
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.fehler import KaufteilFehler
from swki.kaufteile.katalog import bibliotheksschluessel, finde, geprueft
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.fehler import NormteilFehler
from swki.normteile.schluessel import loese_auf
from swki.normteile.tabelle import lade_normtabelle, pruefe_tabelle
from swki.spec.freigabe import FreigabeFehler, pruefe_freigabe
from swki.spec.laden import SpecFehler, lade_spec, lade_yaml, schema_befunde
```

In `swki/baugruppe/laden.py` ersetzen:

```python


def _teil(kid: str, datei: str, ordner: Path, cache: dict) -> tuple[Quelle | None, list[dict]]:
    if datei not in cache:
```

durch:

```python


def kaufteil_spec(eintrag: dict) -> dict:
    """Teilansicht eines Kaufteils für die Baugruppe: die Einbaureferenzen als referenz-Features (Auswahl per Name wie
    bei Normteilen) und die Gewindegruppen; die fremde Geometrie selbst wird nie über Features angesprochen."""
    return {"art": "teil", "name": bibliotheksschluessel(eintrag["hersteller"], eintrag["bestellnummer"]),
            "features": [{"id": n, "typ": "referenz"} for n in eintrag["einbau"]], "gewinde": eintrag.get("gewinde", {})}


def _kaufteil(kid: str, quelle: dict) -> tuple[Quelle | None, list[dict]]:
    """Kaufteil aus dem Katalog (Spec 3c §8.2): Eintrag vorhanden und gültig; freigegeben und geprüft sind Befunde."""
    pfad_befund = f"komponenten.{kid}.quelle"
    try:
        pfad = finde(quelle["kaufteil"])
        eintrag = lade_eintrag(pfad)
    except KaufteilFehler as e:
        return None, [{"pfad": pfad_befund, "meldung": f"{e.daten['code']}: {e}"}]
    except SpecFehler as e:
        return None, [{"pfad": pfad_befund, "meldung": f"Katalogeintrag {quelle['kaufteil']} ungültig: {b['pfad']}: "
                                                       f"{b['meldung']}"} for b in e.daten["befunde"]]
    befunde = []
    try:
        pruefe_freigabe(pfad, eintrag)
    except FreigabeFehler as e:
        befunde.append({"pfad": pfad_befund, "meldung": f"KAUFTEIL_NICHT_FREIGEGEBEN: {e}"})
    if not befunde and not geprueft(pfad, eintrag):
        befunde.append({"pfad": pfad_befund, "meldung": f"KAUFTEIL_UNGEPRUEFT: {quelle['kaufteil']} hat kein bestandenes "
                                                        "Prüfer-Urteil zur aktuellen Freigabe"})
    q = Quelle("kaufteil", kaufteil_spec(eintrag), schluessel=bibliotheksschluessel(eintrag["hersteller"],
                                                                                     eintrag["bestellnummer"]),
               eintrag=eintrag, eintrag_pfad=pfad)
    return q, befunde


def _teil(kid: str, datei: str, ordner: Path, cache: dict) -> tuple[Quelle | None, list[dict]]:
    if datei not in cache:
```

In `swki/baugruppe/laden.py` ersetzen:

```python
    for k in spec["komponenten"]:
        q = k["quelle"]
        quelle, b = _teil(k["id"], q["teil"], ordner, cache) if "teil" in q else _normteil(k["id"], q)
        befunde += b
        if quelle is not None:
```

durch:

```python
    for k in spec["komponenten"]:
        q = k["quelle"]
        if "teil" in q:
            quelle, b = _teil(k["id"], q["teil"], ordner, cache)
        elif "kaufteil" in q:
            quelle, b = _kaufteil(k["id"], q)
        else:
            quelle, b = _normteil(k["id"], q)
        befunde += b
        if quelle is not None:
```

In `swki/baugruppe/aufloesen.py` ersetzen:

```python

def anzahl_positionen(spec: dict, quellen: dict[str, Quelle], kid: str) -> int:
    je = je_position(spec, kid)
    feature = next(f for f in quellen[je["komponente"]].spec["features"] if f["id"] == je["feature"])
    return len(feature["positionen"])
```

durch:

```python

def anzahl_positionen(spec: dict, quellen: dict[str, Quelle], kid: str) -> int:
    """Positionen des je_position: Bohrungs-Feature eines Eigenteils oder Gewindegruppe eines Kaufteils (Spec 3c §8.1)."""
    je = je_position(spec, kid)
    if "gewinde" in je:
        return len(quellen[je["komponente"]].spec["gewinde"][je["gewinde"]]["positionen"])
    feature = next(f for f in quellen[je["komponente"]].spec["features"] if f["id"] == je["feature"])
    return len(feature["positionen"])
```

In `swki/baugruppe/aufloesen.py` ersetzen:

```python

def _drehung_sperren(v: dict, quellen: dict[str, Quelle]) -> bool:
    """Vorgabe true bei konzentrisch mit einem Normteil (Spec 3b §4.4), sonst false; ausdrücklich angegeben gilt."""
    if "drehung_sperren" in v:
        return v["drehung_sperren"]
    return v["typ"] == "konzentrisch" and any(quellen[v[s]["komponente"]].art == "normteil" for s in ("a", "b"))
```

durch:

```python

def _drehung_sperren(v: dict, quellen: dict[str, Quelle]) -> bool:
    """Vorgabe true bei konzentrisch mit einem Norm- oder Kaufteil (Spec 3b §4.4, 3c §8.1), sonst false; ausdrücklich
    angegeben gilt."""
    if "drehung_sperren" in v:
        return v["drehung_sperren"]
    return v["typ"] == "konzentrisch" and any(quellen[basis(v[s]["komponente"])].art in ("normteil", "kaufteil")
                                              for s in ("a", "b"))
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
"""Plausibilität einer Baugruppen-Spezifikation (Spec 3b §5, 4a §5, 4b §5.2), ohne SolidWorks."""

import math
```

durch:

```python
"""Plausibilität einer Baugruppen-Spezifikation (Spec 3b §5, 4a §5, 4b §5.2, 3c §8.2), ohne SolidWorks."""

import math
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python


def _instanz_befunde(kid: str, k: str, pfad: str, spec: dict, quellen: dict) -> list[dict]:
    je = je_position(spec, k)
```

durch:

```python


def je_ziel(je: dict) -> str:
    """"deckel.f4" bzw. "motor.flansch" (Gewindegruppe eines Kaufteils) für Meldungen."""
    return f"{je['komponente']}.{je.get('feature', je.get('gewinde'))}"


def _instanz_befunde(kid: str, k: str, pfad: str, spec: dict, quellen: dict) -> list[dict]:
    je = je_position(spec, k)
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
        return [_b(f"{pfad}.komponente", f"{k} hat keine Instanzen (ohne .<n> angeben)")]
    if je and int(kid.split(".")[1]) > anzahl_positionen(spec, quellen, k):
        return [_b(f"{pfad}.komponente", f"{kid}: {je['komponente']}.{je['feature']} hat nicht so viele Positionen")]
    return []
```

durch:

```python
        return [_b(f"{pfad}.komponente", f"{k} hat keine Instanzen (ohne .<n> angeben)")]
    if je and int(kid.split(".")[1]) > anzahl_positionen(spec, quellen, k):
        return [_b(f"{pfad}.komponente", f"{kid}: {je_ziel(je)} hat nicht so viele Positionen")]
    return []


def _kaufteil_referenz_befunde(seite: dict, pfad: str, q: Quelle, k: str) -> list[dict]:
    """Kaufteile nur über Einbaureferenzen oder Gewindepositionen (Spec 3c §8.1), nie über fremde Geometrie."""
    vorhanden = ", ".join(sorted(q.referenzen))
    if "referenz" in seite:
        if seite["referenz"] not in q.referenzen:
            return [_b(f"{pfad}.referenz", f"{q.kaufteil} hat keine Einbaureferenz {seite['referenz']!r} "
                                           f"(vorhanden: {vorhanden})")]
        return []
    if "gewinde" in seite:
        g = q.spec["gewinde"].get(seite["gewinde"])
        if g is None:
            return [_b(f"{pfad}.gewinde", f"{q.kaufteil} hat keine Gewindegruppe {seite['gewinde']!r} "
                                          f"(vorhanden: {', '.join(q.spec['gewinde']) or 'keine'})")]
        if isinstance(seite["instanz"], int) and seite["instanz"] > len(g["positionen"]):
            return [_b(f"{pfad}.instanz", f"{seite['gewinde']} hat nur {len(g['positionen'])} Positionen")]
        return []
    return [_b(pfad, f"{k} ist ein Kaufteil: nur über Einbaureferenzen ({vorhanden}) oder Gewindepositionen "
                     "({komponente, gewinde, instanz, achse: true})")]
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
    befunde = _instanz_befunde(kid, k, pfad, spec, quellen) if instanz_id_erlaubt else []
    q = quellen[k]
    if q.art == "normteil":
        vorhanden = ", ".join(sorted(q.referenzen))
```

durch:

```python
    befunde = _instanz_befunde(kid, k, pfad, spec, quellen) if instanz_id_erlaubt else []
    q = quellen[k]
    if q.art == "kaufteil":
        return befunde + _kaufteil_referenz_befunde(seite, pfad, q, k)
    if q.art == "normteil":
        vorhanden = ", ".join(sorted(q.referenzen))
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
        if f is None or f["typ"] != "referenz":
            befunde.append(_b(f"{pfad}.referenz", f"{q.datei} hat kein referenz-Feature {seite['referenz']!r}"))
    elif "feature" in seite:
        f = features.get(seite["feature"])
```

durch:

```python
        if f is None or f["typ"] != "referenz":
            befunde.append(_b(f"{pfad}.referenz", f"{q.datei} hat kein referenz-Feature {seite['referenz']!r}"))
    elif "gewinde" in seite:
        befunde.append(_b(f"{pfad}.gewinde", f"{k} ist kein Kaufteil: Gewindepositionen nur bei Kaufteilen"))
    elif "feature" in seite:
        f = features.get(seite["feature"])
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
            befunde.append(_b(pfad, "eine Komponente mit je_position kann nicht fixiert sein"))
        q = quellen.get(je["komponente"])
        if q is None or q.art != "teil" or je_position(spec, je["komponente"]):
            befunde.append(_b(f"{pfad}.komponente", f"{je['komponente']!r} ist kein Eigenteil ohne je_position"))
```

durch:

```python
            befunde.append(_b(pfad, "eine Komponente mit je_position kann nicht fixiert sein"))
        q = quellen.get(je["komponente"])
        if "gewinde" in je:
            if q is None or q.art != "kaufteil":
                befunde.append(_b(f"{pfad}.komponente", f"{je['komponente']!r} ist kein Kaufteil (gewinde)"))
            elif je["gewinde"] not in q.spec["gewinde"]:
                befunde.append(_b(f"{pfad}.gewinde", f"{q.kaufteil} hat keine Gewindegruppe {je['gewinde']!r}"))
            continue
        if q is None or q.art != "teil" or je_position(spec, je["komponente"]):
            befunde.append(_b(f"{pfad}.komponente", f"{je['komponente']!r} ist kein Eigenteil ohne je_position"))
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
    if "referenz" in seite:
        q = quellen[basis(seite["komponente"])]
        if q.art == "normteil":
            return "ACHSE" not in seite["referenz"]
```

durch:

```python
    if "referenz" in seite:
        q = quellen[basis(seite["komponente"])]
        if q.art == "kaufteil":
            w = q.eintrag["einbau"].get(seite["referenz"])
            return w is not None and "zylinder" not in w
        if q.art == "normteil":
            return "ACHSE" not in seite["referenz"]
```

In `swki/baugruppe/plausibel.py` ersetzen:

```python
        if v[s].get("instanz") != "je":
            continue
        ziel = {"komponente": v[s]["komponente"], "feature": v[s].get("feature")}
        if not je:
            befunde.append(_b(f"{pfad}.{s}.instanz", "instanz: je nur zusammen mit einer Komponente mit je_position"))
        elif ziel not in je.values():
            befunde.append(_b(f"{pfad}.{s}.instanz", "instanz: je nur auf das Feature des je_position "
                                                     f"({', '.join(f'{x['komponente']}.{x['feature']}' for x in je.values())})"))
    return befunde
```

durch:

```python
        if v[s].get("instanz") != "je":
            continue
        art = "gewinde" if "gewinde" in v[s] else "feature"
        ziel = {"komponente": v[s]["komponente"], art: v[s].get(art)}
        if not je:
            befunde.append(_b(f"{pfad}.{s}.instanz", "instanz: je nur zusammen mit einer Komponente mit je_position"))
        elif ziel not in je.values():
            befunde.append(_b(f"{pfad}.{s}.instanz", "instanz: je nur auf das Feature bzw. die Gewindegruppe des "
                                                     f"je_position ({', '.join(je_ziel(x) for x in je.values())})"))
    return befunde
```

In `swki/baugruppe/passung.py` ersetzen:

```python
"""Passung Normteil ↔ Bohrung bei konzentrischen Verknüpfungen (Spec 3b §5.7), ohne SolidWorks."""

from swki.baugruppe.modell import Quelle
```

durch:

```python
"""Passung Normteil ↔ Bohrung bzw. Gewinde eines Kaufteils bei konzentrischen Verknüpfungen (Spec 3b §5.7, 3c §8.2),
ohne SolidWorks."""

from swki.baugruppe.modell import Quelle
```

In `swki/baugruppe/passung.py` ersetzen:

```python


def passung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    for i, v in enumerate(spec.get("verknuepfungen", [])):
        if v["typ"] not in ("konzentrisch", "scharnier") or (paar := _paar(v, quellen)) is None:
            continue
```

durch:

```python


def _gewinde_paar(v: dict, quellen: dict[str, Quelle]) -> str | None:
    """Meldung, wenn v die EINBAU_ACHSE eines Normteils mit einer Gewindeposition eines Kaufteils verbindet und die
    Größe nicht passt (nur ISO 4762 derselben Größe); sonst None."""
    for n, t in (("a", "b"), ("b", "a")):
        qn, qt = quellen.get(v[n]["komponente"]), quellen.get(v[t]["komponente"])
        if (qn is None or qt is None or qn.art != "normteil" or v[n].get("referenz") != "EINBAU_ACHSE"
                or qt.art != "kaufteil" or "gewinde" not in v[t]):
            continue
        g = qt.spec["gewinde"].get(v[t]["gewinde"])
        if g is None:
            return None  # meldet referenz_befunde
        if qn.norm != "ISO 4762" or qn.groesse != g["groesse"]:
            return f"{qn.norm} {qn.groesse} passt nicht in Gewinde {g['groesse']} von {qt.kaufteil}"
    return None


def passung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    for i, v in enumerate(spec.get("verknuepfungen", [])):
        if v["typ"] == "konzentrisch" and (meldung := _gewinde_paar(v, quellen)):
            befunde.append({"pfad": f"verknuepfungen[{i}]", "meldung": f"Passung: {meldung}"})
            continue
        if v["typ"] not in ("konzentrisch", "scharnier") or (paar := _paar(v, quellen)) is None:
            continue
```

In `swki/spec/freigabe.py` ersetzen:

```python


def freigeben(spec_pfad: Path, spec: dict, zeitpunkt: str | None = None, teile: dict[str, str] | None = None) -> dict:
    pfad = freigabe_pfad(spec_pfad)
    daten = _lies(pfad)
```

durch:

```python


def freigeben(spec_pfad: Path, spec: dict, zeitpunkt: str | None = None, teile: dict[str, str] | None = None,
              zusatz: dict | None = None) -> dict:
    """zusatz: weitere Angaben im Eintrag von freigabe.json (Baugruppe: Prüfsummen der Kaufteile, Spec 3c §8.3)."""
    pfad = freigabe_pfad(spec_pfad)
    daten = _lies(pfad)
```

In `swki/spec/freigabe.py` ersetzen:

```python
        "freigegeben": zeitpunkt or datetime.now().isoformat(timespec="seconds"),
        "kopie_sha256": _sha256(kopie),
    }
    daten[spec_pfad.name] = eintrag
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return eintrag
```

durch:

```python
        "freigegeben": zeitpunkt or datetime.now().isoformat(timespec="seconds"),
        "kopie_sha256": _sha256(kopie),
        **(zusatz or {}),
    }
    daten[spec_pfad.name] = eintrag
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return eintrag


def freigabe_eintrag(spec_pfad: Path) -> dict | None:
    """Eintrag der Spezifikation in freigabe.json (None, wenn nicht freigegeben)."""
    return _lies(freigabe_pfad(spec_pfad)).get(spec_pfad.name)
```

In `swki/baugruppe/freigabe.py` ersetzen:

```python
"""Eine Freigabe für Baugruppe und Teil-Specs (Spec 3b §6). Jede Teil-Spec bekommt ihren Eintrag in freigabe.json und
ihre Freigabe-Kopie; die Baugruppe zusätzlich eine Prüfsumme über die Prüfsummen der Teile."""

from dataclasses import replace
```

durch:

```python
"""Eine Freigabe für Baugruppe und Teil-Specs (Spec 3b §6). Jede Teil-Spec bekommt ihren Eintrag in freigabe.json und
ihre Freigabe-Kopie; die Baugruppe zusätzlich eine Prüfsumme über die Prüfsummen der Teile und der Katalogeinträge ihrer
Kaufteile (Spec 3c §8.3; die Einträge selbst gibt der Nutzer je Kaufteil frei)."""

from dataclasses import replace
```

In `swki/baugruppe/freigabe.py` ersetzen:

```python

from swki.baugruppe.modell import Baugruppe, Quelle
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
```

durch:

```python

from swki.baugruppe.modell import Baugruppe, Quelle
from swki.spec.freigabe import FreigabeFehler, freigabe_eintrag, freigeben, kopie_pfad, pruefe_freigabe, pruefsumme


def kaufteil_summen(bg: Baugruppe) -> dict[str, str]:
    """"kaufteil:<Hersteller> <Bestellnummer>" → Freigabe-Prüfsumme des Katalogeintrags."""
    return {f"kaufteil:{q.kaufteil}": pruefsumme(q.eintrag) for q in bg.quellen.values() if q.art == "kaufteil"}


def teil_summen(bg: Baugruppe) -> dict[str, str]:
    return {datei: pruefsumme(spec) for datei, spec in bg.teile.items()} | kaufteil_summen(bg)


def freigeben_baugruppe(bg: Baugruppe, zeitpunkt: str | None = None) -> dict:
    teile = {datei: freigeben(bg.pfad.parent / datei, spec, zeitpunkt) for datei, spec in bg.teile.items()}
    zusatz = {"kaufteile": kaufteil_summen(bg)} if kaufteil_summen(bg) else None
    return {**freigeben(bg.pfad, bg.spec, zeitpunkt, teile=teil_summen(bg), zusatz=zusatz), "teile": teile}


def pruefe_freigabe_baugruppe(bg: Baugruppe) -> dict:
    """Erst jede Teil-Spec und jeden Kaufteil-Eintrag (die Meldung nennt das Teil), dann die Baugruppe; wirft
    FreigabeFehler."""
    for datei, spec in bg.teile.items():
        pruefe_freigabe(bg.pfad.parent / datei, spec)
    for q in {q.kaufteil: q for q in bg.quellen.values() if q.art == "kaufteil"}.values():
        pruefe_freigabe(q.eintrag_pfad, q.eintrag)
    frueher = (freigabe_eintrag(bg.pfad) or {}).get("kaufteile", {})
    for name, summe in kaufteil_summen(bg).items():
        if name in frueher and frueher[name] != summe:
            raise FreigabeFehler("FREIGABE_VERALTET", f"{name.removeprefix('kaufteil:')}: Katalogeintrag nach der "
                                                      f"Freigabe von {bg.pfad.name} geändert. Nutzer fragen und die "
                                                      "Baugruppe neu freigeben.")
    return pruefe_freigabe(bg.pfad, bg.spec, teile=teil_summen(bg))
```

In `swki/baugruppe/hinweise.py` ersetzen:

```python
"""Hinweise zu einer gültigen Baugruppen-Spezifikation (Spec 3b §5.8); sie blockieren nie."""

from swki.baugruppe.modell import Baugruppe
from swki.konfig import lade_standard
```

durch:

```python
"""Hinweise zu einer gültigen Baugruppen-Spezifikation (Spec 3b §5.8); sie blockieren nie."""

from swki.baugruppe.aufloesen import basis
from swki.baugruppe.modell import Baugruppe
from swki.konfig import lade_standard
```

In `swki/baugruppe/hinweise.py` ersetzen:

```python

PRUEFAUFWAND_AB = 4  # Bewegungen; Spec 4a §4.4
```

durch:

```python

PRUEFAUFWAND_AB = 4  # Bewegungen; Spec 4a §4.4


def _drehlage_hinweise(bg: Baugruppe) -> list[dict]:
    """Konzentrisch mit Drehsperre (Vorgabe bei Kaufteilen) und dazu eine Verknüpfung der Drehlage desselben Kaufteils
    (Einbaureferenz ebene_durch_achse) wäre überbestimmt (Spec 3c §8.1)."""
    vs = bg.spec.get("verknuepfungen", [])
    drehlage = {}
    for v in vs:
        for s in ("a", "b"):
            q = bg.quellen.get(basis(v[s]["komponente"]))
            if q is not None and q.art == "kaufteil" and \
                    "ebene_durch_achse" in q.eintrag["einbau"].get(v[s].get("referenz"), {}):
                drehlage.setdefault(basis(v[s]["komponente"]), v["id"])
    ergebnis = []
    for i, v in enumerate(vs):
        if v["typ"] != "konzentrisch" or v.get("drehung_sperren") is False:
            continue
        for s in ("a", "b"):
            k = basis(v[s]["komponente"])
            if k in drehlage:
                ergebnis.append({"art": "drehlage_doppelt", "pfad": f"verknuepfungen[{i}].drehung_sperren",
                                 "meldung": f"{k}: Drehlage über {drehlage[k]} verknüpft – hier drehung_sperren: false "
                                            "setzen, sonst überbestimmt"})
    return ergebnis
```

In `swki/baugruppe/hinweise.py` ersetzen:

```python
                             "meldung": f"feste Zahl {w:g}: als Parameter führen, wenn der Wert eine Anforderung ist "
                                        "(sonst deckt die Freigabe ihn nicht ab)"})
    bws = bg.spec.get("bewegungen", [])
    if len(bws) >= PRUEFAUFWAND_AB:
```

durch:

```python
                             "meldung": f"feste Zahl {w:g}: als Parameter führen, wenn der Wert eine Anforderung ist "
                                        "(sonst deckt die Freigabe ihn nicht ab)"})
    ergebnis += _drehlage_hinweise(bg)
    bws = bg.spec.get("bewegungen", [])
    if len(bws) >= PRUEFAUFWAND_AB:
```

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_kaufteil_baugruppe.py`
Expected: `9 passed`. Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **912 passed, 139 deselected**.

- [ ] **Step 5: Commit**

```powershell
git add schema/baugruppe.schema.json swki/baugruppe/modell.py swki/baugruppe/laden.py swki/baugruppe/aufloesen.py swki/baugruppe/plausibel.py swki/baugruppe/passung.py swki/baugruppe/freigabe.py swki/baugruppe/hinweise.py swki/spec/freigabe.py tests/baugruppe/beispiel_kaufteil.py tests/baugruppe/test_kaufteil_baugruppe.py
git commit -m "baugruppe: Komponentenquelle kaufteil, Gewinde-Referenz und je_position, Passung, Freigabe mit Eintragsprüfsumme (Stufe 3c, Task 8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Baugruppen – Bau, Prüfen, Gewindepaarung im Kaufteil, Bericht (ohne SolidWorks)

**Files:**
- Modify: `swki/compiler/protokoll.py`, `swki/baugruppe/bau.py`, `swki/baugruppe/referenzen.py`, `swki/baugruppe/pruefen.py`,
  `swki/baugruppe/bewertung.py`, `swki/pruefung/bericht.py`, `swki/aenderungen.py`
- Test: `tests/baugruppe/test_kaufteil_bau_pruefen.py`, `tests/test_aenderungen.py`

**Interfaces:**
- Consumes: Task 6 (`kaufteil_befehle.hole`), Task 3 (`eintrag.angaben_fuer_bericht`), Task 4 (`ortung.orte_gewinde`), Task 8.
- Produces: `Protokoll.kaufteile`; `bau._hole_kaufteile(b, tol_mm)` (Phase `kaufteile` zwischen `normteile` und `einfuegen`);
  `referenzen.gewinde_referenz(ctx, gruppe, instanz)`; `pruefen.gewindebohrungen_kaufteil(teil_spec)`;
  `BaugruppenMesswerte.gewinde_modelle`; Prüfbericht `kaufteile`; `bericht.md` Abschnitt „Kaufteile“.

- [ ] **Step 1: Tests schreiben**

`tests/baugruppe/test_kaufteil_bau_pruefen.py` anlegen:

```python
from pathlib import Path
from types import SimpleNamespace

from swki.baugruppe import bau
from swki.baugruppe.aufloesen import instanzen, verknuepfungen
from swki.baugruppe.bewertung import BaugruppenMesswerte, bewerte_baugruppe, stueckliste_soll
from swki.baugruppe.geometrie import ueberlappung_soll
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.pruefen import gewindebohrungen_kaufteil
from swki.compiler.protokoll import Protokoll
from swki.kaufteile.fehler import KaufteilFehler
from swki.konfig import lade_standard
from swki.pruefung.bericht import bericht_markdown
from swki.pruefung.geometrie import Messgeometrie
from tests.baugruppe.beispiel_kaufteil import L, katalog, kopie, schreibe

STANDARD = {"toleranzen": {"anker_mm": 0.1, "volumen_prozent": 0.5}, "namensschema": {"datei": "{auftrag}_{name}"}}
Y = (0.0, 1.0, 0.0)


def _ins_gewinde(spec: dict) -> dict:
    spec["komponenten"][2] = {"id": "schraube", "quelle": {"normteil": "ISO 4762 M5x12"},
                              "je_position": {"komponente": "motor", "gewinde": "flansch"}}
    spec["verknuepfungen"][3]["b"] = {"komponente": "halter", "feature": "f1", "flaeche": "-y"}
    spec["verknuepfungen"][4]["b"] = {"komponente": "motor", "gewinde": "flansch", "instanz": "je", "achse": True}
    return spec


def _baulauf(pfad, tmp_path):
    bg = lade_baugruppe(pfad)
    return bau.Baulauf(app=None, bg=bg, auftrag="A", ordner=tmp_path / "lauf", standard=lade_standard(),
                       protokoll=Protokoll("A", pfad.name, 1, 2025)), bg


def test_kaufteile_werden_kopiert(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    b, bg = _baulauf(schreibe(tmp_path / "A"), tmp_path)
    cache = tmp_path / "cache" / "SWKI-MUSTER_GM42-10.sldprt"
    cache.parent.mkdir()
    cache.write_bytes(b"kaufteil")
    aufrufe = []

    def hole(text):
        aufrufe.append(text)
        return {"pfad": str(cache), "gebaut": False, "pruefsumme": "abc", "gewinde_modell": {"flansch": "kernloch"}}

    monkeypatch.setattr(bau.kaufteil_befehle, "hole", hole)
    monkeypatch.setattr(bau, "oeffne", lambda app, p: SimpleNamespace(pfad=Path(p)))
    monkeypatch.setattr(bau, "kontext_aus_datei", lambda app, model, spec, p, tol, prot: SimpleNamespace(model=model, spec=spec))
    assert bau._hole_kaufteile(b, 0.1) is None
    kopie_datei = b.ordner / "SWKI-MUSTER_GM42-10.sldprt"
    assert aufrufe == ["SWKI-MUSTER GM42-10"] and kopie_datei.read_bytes() == b"kaufteil" and cache.read_bytes() == b"kaufteil"
    assert b.dateien == {"kaufteil:SWKI-MUSTER_GM42-10": kopie_datei} and b.offen[0].pfad == kopie_datei
    assert b.protokoll.kaufteile["SWKI-MUSTER_GM42-10"] == {
        "kaufteil": "SWKI-MUSTER GM42-10", "cache": str(cache), "gebaut": False, "pruefsumme": "abc",
        "gewinde_modell": {"flansch": "kernloch"}, "masse": "1.2 kg (Datenblatt)", "kennmasse": "belegt"}
    assert b.kontexte["SWKI-MUSTER_GM42-10"].spec["gewinde"]["flansch"]["groesse"] == "M5"


def test_kaufteilfehler_beim_holen(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    b, _ = _baulauf(schreibe(tmp_path / "A"), tmp_path)

    def hole(text):
        raise KaufteilFehler("KAUFTEIL_QUELLE_FEHLT", "Original fehlt")

    monkeypatch.setattr(bau.kaufteil_befehle, "hole", hole)
    fehler = bau._hole_kaufteile(b, 0.1)
    assert fehler.code == "KAUFTEIL_QUELLE_FEHLT" and str(fehler) == "motor: Original fehlt"


def test_gewindebohrungen_des_kaufteils(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    liste = gewindebohrungen_kaufteil(bg.quellen["motor"].spec)
    assert [(b["feature"], b["instanz"]) for b in liste] == [("flansch", i) for i in range(1, 5)]
    assert liste[1]["punkt"] == (-L, 0, L)


def _messwerte(bg, laenge_im_gewinde: float, volumen: float, modell: str | None = "kernloch") -> BaugruppenMesswerte:
    """Schraube.1 sitzt mit der Kopfauflage 12 − laenge vor dem Eintritt (Flansch y = 0, Normale −y) der Position 1."""
    vs = verknuepfungen(bg.spec, bg.quellen)
    ids = [i.id for i in instanzen(bg.spec, bg.quellen)]
    return BaugruppenMesswerte(
        rebuild_fehler=[], verknuepfungen={v.id: 0 for v in vs},
        komponenten={i: {"status": 3, "fixiert": i == "halter"} for i in ids},
        stueckliste=stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD),
        interferenzen=[{"paar": ["motor", "schraube.1"], "volumen": volumen}], box=[0, 0, 0, 1, 1, 1], masse_kg=1.0,
        eigenschaften={"Benennung": "Motorprobe"},
        schrauben={"schraube.1": Messgeometrie("ebene", (L, -(12 - laenge_im_gewinde), L), Y)},
        gewindebohrungen=[{"teil": "motor", "feature": "flansch", "instanz": 1,
                           "eintritt": Messgeometrie("punkt", (L, 0.0, L))}],
        teilberichte={"halter.yaml": {"bestanden": True, "pruefungen": [], "maengel": []}},
        gewinde_modelle={"SWKI-MUSTER_GM42-10": {"flansch": modell}} if modell else {})


def _gewinde(bg, m) -> dict:
    bericht = bewerte_baugruppe(bg.spec, bg.quellen, m, STANDARD, stueckliste_soll(bg.spec, bg.quellen, "A", STANDARD))
    return next(e for e in bericht["pruefungen"] if e["id"] == "gewinde:schraube.1")


def test_gewindepaarung_im_kaufteil(tmp_path, monkeypatch):
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    soll = ueberlappung_soll(5, 0.8, 4.2, 7.4)
    ok = _gewinde(bg, _messwerte(bg, 7.4, soll))
    assert ok["ok"] is True and ok["soll"] == round(soll, 3) and ok["gewindetiefe"] == 8 and ok["tiefe"] == 10
    zu_lang = _gewinde(bg, _messwerte(bg, 9.0, ueberlappung_soll(5, 0.8, 4.2, 9.0)))
    assert zu_lang["ok"] is False and "Einschraublänge 9.00 mm größer als Gewindetiefe 8" in zu_lang["hinweis"]
    nenn = _gewinde(bg, _messwerte(bg, 7.4, 0.0, "nenn"))
    assert nenn["ok"] is True and nenn["soll"] == 0.0
    assert _gewinde(bg, _messwerte(bg, 7.4, 3.0, "nenn"))["ok"] is False
    unbekannt = _gewinde(bg, _messwerte(bg, 7.4, soll, None))
    assert unbekannt["ok"] is None and "Gewindemodell" in unbekannt["hinweis"]


def test_bericht_nennt_kaufteile():
    pruefbericht = {"maengel": [], "kaufteile": {"SWKI-MUSTER_GM42-10": {
        "kaufteil": "SWKI-MUSTER GM42-10", "gebaut": True, "pruefsumme": "abc", "masse": "1.2 kg (Datenblatt)",
        "kennmasse": "nicht belegt"}}}
    text = bericht_markdown({"name": "Motorprobe"}, "A", [], ("WEITER", "x"), pruefbericht, None, None, [])
    assert "| SWKI-MUSTER GM42-10 | ja | abc | 1.2 kg (Datenblatt) | nicht belegt |" in text
```

In `tests/test_aenderungen.py` ersetzen:

```python
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert ergebnis["geaendert"] == [{"datei": "ISO4762_M8x30_8_8.sldprt", "parameter": [],
                                      "hinweis": "keine Spezifikation zu dieser Datei (Normteil-Kopie)"}]
```

durch:

```python
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert ergebnis["geaendert"] == [{"datei": "ISO4762_M8x30_8_8.sldprt", "parameter": [],
                                      "hinweis": "keine Spezifikation zu dieser Datei (Normteil- oder Kaufteil-Kopie)"}]
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_kaufteil_bau_pruefen.py tests\test_aenderungen.py`
Expected: FAIL – `1 error` (`ImportError: cannot import name 'gewindebohrungen_kaufteil' from 'swki.baugruppe.pruefen'`).

- [ ] **Step 3: Umsetzen**

In `swki/compiler/protokoll.py` ersetzen:

```python
    komponenten: list[dict] = field(default_factory=list)  # Baugruppe: [{"id", "sw_name", "datei"}]
    normteile: dict[str, dict] = field(default_factory=dict)  # Baugruppe: Schlüssel → {"bibliothek", "gebaut", "pruefsumme"}

    @contextmanager
```

durch:

```python
    komponenten: list[dict] = field(default_factory=list)  # Baugruppe: [{"id", "sw_name", "datei"}]
    normteile: dict[str, dict] = field(default_factory=dict)  # Baugruppe: Schlüssel → {"bibliothek", "gebaut", "pruefsumme"}
    kaufteile: dict[str, dict] = field(default_factory=dict)  # Baugruppe: Schlüssel → {"kaufteil", "cache", "gebaut", …}

    @contextmanager
```

In `swki/baugruppe/bau.py` ersetzen:

```python
from swki.compiler.fehler import BauFehler, fehler_dict
from swki.compiler.protokoll import Protokoll
from swki.konfig import lade_rechner, lade_standard
from swki.normteile import befehle as normteil_befehle
```

durch:

```python
from swki.compiler.fehler import BauFehler, fehler_dict
from swki.compiler.protokoll import Protokoll
from swki.kaufteile import befehle as kaufteil_befehle
from swki.kaufteile.eintrag import angaben_fuer_bericht
from swki.kaufteile.fehler import KaufteilFehler
from swki.konfig import lade_rechner, lade_standard
from swki.normteile import befehle as normteil_befehle
```

In `swki/baugruppe/bau.py` ersetzen:

```python
    protokoll: Protokoll
    asm: object = None
    kontexte: dict = field(default_factory=dict)     # Quelldokument (Teil-Spec bzw. Normteil-Schlüssel) → Kontext
    offen: list = field(default_factory=list)        # selbst geöffnete Teildokumente, am Ende schließen
    dateien: dict = field(default_factory=dict)      # "teil:<datei>" | "normteil:<schluessel>" | "baugruppe" → Pfad
    komponenten: dict = field(default_factory=dict)  # Instanz-ID → IComponent2 (aus AddComponent5, nie über GetComponents)
    gesetzt: dict = field(default_factory=dict)      # Verknüpfungs-ID → ausdrücklich gesetzte Ausrichtung, ein Dict je Lauf
```

durch:

```python
    protokoll: Protokoll
    asm: object = None
    kontexte: dict = field(default_factory=dict)     # Quelldokument (Teil-Spec bzw. Norm-/Kaufteil-Schlüssel) → Kontext
    offen: list = field(default_factory=list)        # selbst geöffnete Teildokumente, am Ende schließen
    dateien: dict = field(default_factory=dict)      # "teil:<datei>" | "normteil:…" | "kaufteil:…" | "baugruppe" → Pfad
    komponenten: dict = field(default_factory=dict)  # Instanz-ID → IComponent2 (aus AddComponent5, nie über GetComponents)
    gesetzt: dict = field(default_factory=dict)      # Verknüpfungs-ID → ausdrücklich gesetzte Ausrichtung, ein Dict je Lauf
```

In `swki/baugruppe/bau.py` ersetzen:

```python


def _gespeichert(b: Baulauf, q: Quelle) -> Path:
    """Pfad, unter dem swki die Quelldatei im Lauf-Ordner gespeichert hat (GetPathName schreibt .SLDPRT groß, Spike S12)."""
    return b.dateien[f"teil:{q.datei}" if q.art == "teil" else f"normteil:{q.schluessel}"]
```

durch:

```python


def _hole_kaufteile(b: Baulauf, tol_mm: float) -> Exception | None:
    """Je Kaufteil swki kaufteil hole (Cache oder Neuaufnahme) und Kopie in den Lauf-Ordner (Spec 3c §8.4); die
    Baugruppe verweist nie auf Cache oder Quellordner."""
    for kid, q in {q.schluessel: (k, q) for k, q in b.bg.quellen.items() if q.art == "kaufteil"}.values():
        try:
            ergebnis = kaufteil_befehle.hole(q.kaufteil)
        except KaufteilFehler as e:
            return BauFehler(e.daten["code"], f"{kid}: {e}", schritt="kaufteil")
        ziel = b.ordner / dokument_name(q, b.auftrag, b.standard)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ergebnis["pfad"], ziel)
        b.protokoll.kaufteile[q.schluessel] = {"kaufteil": q.kaufteil, "cache": ergebnis["pfad"], "gebaut": ergebnis["gebaut"],
                                               "pruefsumme": ergebnis["pruefsumme"],
                                               "gewinde_modell": ergebnis["gewinde_modell"], **angaben_fuer_bericht(q.eintrag)}
        b.dateien[f"kaufteil:{q.schluessel}"] = ziel
        model = oeffne(b.app, ziel)
        b.offen.append(model)
        b.kontexte[q.schluessel] = kontext_aus_datei(b.app, model, q.spec, ziel.with_suffix(".yaml"), tol_mm, {"knoten": []})
    return None


def _gespeichert(b: Baulauf, q: Quelle) -> Path:
    """Pfad, unter dem swki die Quelldatei im Lauf-Ordner gespeichert hat (GetPathName schreibt .SLDPRT groß, Spike S12)."""
    return b.dateien[f"teil:{q.datei}" if q.art == "teil" else f"{q.art}:{q.schluessel}"]
```

In `swki/baugruppe/bau.py` ersetzen:

```python
                fehler = _hole_normteile(b, r, standard["toleranzen"]["anker_mm"])
        if fehler is None:
            with protokoll.phase("einfuegen"):
                b.asm = sw_baugruppe.neue_baugruppe(b.app, r.vorlage_baugruppe)
```

durch:

```python
                fehler = _hole_normteile(b, r, standard["toleranzen"]["anker_mm"])
        if fehler is None:
            with protokoll.phase("kaufteile"):
                fehler = _hole_kaufteile(b, standard["toleranzen"]["anker_mm"])
        if fehler is None:
            with protokoll.phase("einfuegen"):
                b.asm = sw_baugruppe.neue_baugruppe(b.app, r.vorlage_baugruppe)
```

In `swki/baugruppe/referenzen.py` ersetzen:

```python
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN
from swki.compiler.skizze import STANDARD
from swki.compiler.topologie import flaechen, kante_aus, loese_flaeche, mit_abstand, referenz_geometrie
from swki.pruefung.geometrie import Messgeometrie
from swki.verzahnung import verzahnung_im_teil
```

durch:

```python
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN
from swki.compiler.skizze import STANDARD
from swki.compiler.topologie import (flaeche_aus, flaechen, kante_aus, koerper, loese_flaeche, mit_abstand,
                                     referenz_geometrie)
from swki.kaufteile.ortung import orte_gewinde
from swki.pruefung.geometrie import Messgeometrie
from swki.verzahnung import verzahnung_im_teil
```

In `swki/baugruppe/referenzen.py` ersetzen:

```python


def loese_im_teil(ctx, seite: dict) -> TeilReferenz:
    """seite ohne "komponente": {referenz} | {ebene} | {nahe} | {feature, instanz, achse} | {feature, instanz, flaeche} |
    {feature, flaeche}. ctx ist der Kontext des Teildokuments (Bau: Features des Laufs; Normteil: aus der Datei)."""
    if "referenz" in seite:
        if seite["referenz"] not in ctx.ergebnisse:
```

durch:

```python


def gewinde_referenz(ctx, gruppe: str, instanz: int) -> TeilReferenz:
    """Zylinderfläche der Gewindeposition eines Kaufteils (Spec 3c §8.1): Achse durch den Eintrittspunkt der Gruppe aus
    der Teilansicht (ctx.spec["gewinde"]), gesucht über die Flächen aller Körper."""
    g = ctx.spec["gewinde"][gruppe]
    w = {**g, "positionen": [g["positionen"][instanz - 1]]}
    alle = [flaeche_aus(f) for b in koerper(ctx.model) for f in (b.GetFaces() or ())]
    [o] = orte_gewinde(alle, gruppe, w, ctx.tol_mm)
    return TeilReferenz(o.flaeche.objekt, _geometrie(o.flaeche), False)


def loese_im_teil(ctx, seite: dict) -> TeilReferenz:
    """seite ohne "komponente": {referenz} | {ebene} | {nahe} | {feature, instanz, achse} | {feature, instanz, flaeche} |
    {feature, flaeche} | {gewinde, instanz, achse} (Kaufteil). ctx ist der Kontext des Teildokuments (Bau: Features des
    Laufs; Norm- und Kaufteil: aus der Datei)."""
    if "gewinde" in seite:
        return gewinde_referenz(ctx, seite["gewinde"], seite["instanz"])
    if "referenz" in seite:
        if seite["referenz"] not in ctx.ergebnisse:
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python


def _geometrie(ctx, punkte: list[dict]) -> dict:
    ergebnis = {}
```

durch:

```python


def gewindebohrungen_kaufteil(teil_spec: dict) -> list[dict]:
    """Eintrittspunkte (STEP-Koordinaten = Teilkoordinaten) aller Gewindepositionen eines Kaufteils (Spec 3c §6.4)."""
    return [{"feature": g, "instanz": i, "punkt": tuple(p)}
            for g, w in teil_spec.get("gewinde", {}).items() for i, p in enumerate(w["positionen"], start=1)]


def _geometrie(ctx, punkte: list[dict]) -> dict:
    ergebnis = {}
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
            geo = geometrie.get(q.schluessel, {}).get(messpunkt_schluessel(KOPFAUFLAGE), "Kopfauflage fehlt")
            schrauben[i.id] = _in_baugruppe(geo, transformationen[i.id])
        elif q.art == "teil":
            for b in gewindebohrungen_teil(q.spec, protokoll["teile"][q.datei]):
                bohrungen.append({"teil": i.id, "feature": b["feature"], "instanz": b["instanz"],
                                  "eintritt": transformiere(Messgeometrie("punkt", b["punkt"]), transformationen[i.id])})
```

durch:

```python
            geo = geometrie.get(q.schluessel, {}).get(messpunkt_schluessel(KOPFAUFLAGE), "Kopfauflage fehlt")
            schrauben[i.id] = _in_baugruppe(geo, transformationen[i.id])
        elif q.art in ("teil", "kaufteil"):
            liste = (gewindebohrungen_teil(q.spec, protokoll["teile"][q.datei]) if q.art == "teil"
                     else gewindebohrungen_kaufteil(q.spec))
            for b in liste:
                bohrungen.append({"teil": i.id, "feature": b["feature"], "instanz": b["instanz"],
                                  "eintritt": transformiere(Messgeometrie("punkt", b["punkt"]), transformationen[i.id])})
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
        box=sw_baugruppe.huellquader(asm), masse_kg=sw_baugruppe.masse_kg(asm), eigenschaften=lies_eigenschaften(asm),
        messpunkte=messpunkte, schrauben=schrauben, gewindebohrungen=bohrungen, teilberichte=teilberichte,
        lagen=transformationen, kopplungen=gelesen, unterdrueckt=[f.Name for f in mates if sw_baugruppe.ist_unterdrueckt(f)])
```

durch:

```python
        box=sw_baugruppe.huellquader(asm), masse_kg=sw_baugruppe.masse_kg(asm), eigenschaften=lies_eigenschaften(asm),
        messpunkte=messpunkte, schrauben=schrauben, gewindebohrungen=bohrungen, teilberichte=teilberichte,
        lagen=transformationen, kopplungen=gelesen, unterdrueckt=[f.Name for f in mates if sw_baugruppe.ist_unterdrueckt(f)],
        gewinde_modelle={s: k.get("gewinde_modell", {}) for s, k in protokoll.get("kaufteile", {}).items()})
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
                if not behalten:
                    sw.schliesse(app, model)
        for q in {q.schluessel: q for q in bg.quellen.values() if q.art == "normteil"}.values():
            if q.schluessel not in bedarf and q.schluessel not in offen_halten:
                continue
```

durch:

```python
                if not behalten:
                    sw.schliesse(app, model)
        for q in {q.schluessel: q for q in bg.quellen.values() if q.art in ("normteil", "kaufteil")}.values():
            if q.schluessel not in bedarf and q.schluessel not in offen_halten:
                continue
```

In `swki/baugruppe/pruefen.py` ersetzen:

```python
                            stueckliste_soll(bg.spec, freigegebene_quellen(bg), auftrag, standard)),
        "normteile": protokoll.get("normteile", {}), "bilder": bilder,
    }
    if bewegung is not None:
```

durch:

```python
                            stueckliste_soll(bg.spec, freigegebene_quellen(bg), auftrag, standard)),
        "normteile": protokoll.get("normteile", {}), "bilder": bilder,
        **({"kaufteile": protokoll["kaufteile"]} if protokoll.get("kaufteile") else {}),
    }
    if bewegung is not None:
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python
    kopplungen: dict[str, dict | str] = field(default_factory=dict)   # Kopplungs-ID → gelesene Werte oder Fehlertext
    unterdrueckt: list[str] = field(default_factory=list)             # unterdrückte Verknüpfungen (Spec 4b §5.5)
```

durch:

```python
    kopplungen: dict[str, dict | str] = field(default_factory=dict)   # Kopplungs-ID → gelesene Werte oder Fehlertext
    unterdrueckt: list[str] = field(default_factory=list)             # unterdrückte Verknüpfungen (Spec 4b §5.5)
    gewinde_modelle: dict[str, dict] = field(default_factory=dict)    # Kaufteil-Schlüssel → {Gruppe: kernloch | nenn}
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python


def _gewinde(g: Gewindepaarung, quellen: dict[str, Quelle], m: BaugruppenMesswerte) -> tuple[dict, dict] | None:
    qs, qt = quellen[basis(g.schraube)], quellen[basis(g.teil)]
    f = next(x for x in qt.spec["features"] if x["id"] == g.feature)
    laenge = einschraublaenge(qs.laenge, g.kopfauflage, g.eintritt)
    ist = sum(i["volumen"] for i in m.interferenzen if frozenset(i["paar"]) == _paar(g.schraube, g.teil))
```

durch:

```python


def _gewinde_soll(g: Gewindepaarung, qs: Quelle, qt: Quelle, m: BaugruppenMesswerte, laenge: float) \
        -> tuple[float, float, float | None, str | None]:
    """(tiefe, gewindetiefe, Soll des Überlappungsvolumens, Hinweis): Eigenteil aus der normbohrung, Kaufteil aus der
    Gewindegruppe des Eintrags mit dem Modell aus der Aufnahme (Spec 3c §6.4: kernloch → Ring, nenn → 0)."""
    if qt.art == "kaufteil":
        w = qt.spec["gewinde"][g.feature]
        modell = m.gewinde_modelle.get(qt.schluessel, {}).get(g.feature)
        if modell == "nenn":
            return w["tiefe"], w["gewindetiefe"], 0.0, None
        if modell != "kernloch":
            return w["tiefe"], w["gewindetiefe"], None, f"Gewindemodell von {qt.kaufteil}.{g.feature} unbekannt"
        kernloch = normmasse("gewinde", w["groesse"], "ISO")["kernloch"]
        return w["tiefe"], w["gewindetiefe"], ueberlappung_soll(qs.masse["d"], qs.masse["p"], kernloch, laenge), None
    f = next(x for x in qt.spec["features"] if x["id"] == g.feature)
    tp = qt.spec.get("parameter", {})
    kernloch = normmasse("gewinde", f["groesse"], norm_von(f))["kernloch"]
    return (auswerten(f["tiefe"], tp), auswerten(f["gewindetiefe"], tp),
            ueberlappung_soll(qs.masse["d"], qs.masse["p"], kernloch, laenge), None)


def _gewinde(g: Gewindepaarung, quellen: dict[str, Quelle], m: BaugruppenMesswerte) -> tuple[dict, dict] | None:
    qs, qt = quellen[basis(g.schraube)], quellen[basis(g.teil)]
    laenge = einschraublaenge(qs.laenge, g.kopfauflage, g.eintritt)
    ist = sum(i["volumen"] for i in m.interferenzen if frozenset(i["paar"]) == _paar(g.schraube, g.teil))
```

In `swki/baugruppe/bewertung.py` ersetzen:

```python
    bericht = {"schraube": g.schraube, "teil": g.teil, "bohrung": f"{g.feature}.{g.instanz}",
               "einschraublaenge": round(laenge, 3), "volumen": round(ist, 3)}
    if f.get("durch"):
        return eintrag(pid, None, ist=round(ist, 3), einschraublaenge=round(laenge, 3), knoten=knoten,
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
```

durch:

```python
    bericht = {"schraube": g.schraube, "teil": g.teil, "bohrung": f"{g.feature}.{g.instanz}",
               "einschraublaenge": round(laenge, 3), "volumen": round(ist, 3)}
    if qt.art == "teil" and next(x for x in qt.spec["features"] if x["id"] == g.feature).get("durch"):
        return eintrag(pid, None, ist=round(ist, 3), einschraublaenge=round(laenge, 3), knoten=knoten,
                         hinweis="Gewinde durch: Volumen nicht geprüft (Präzisierung 2)"), bericht
    tiefe, gewindetiefe, soll, hinweis = _gewinde_soll(g, qs, qt, m, laenge)
    bericht |= {"soll": None if soll is None else round(soll, 3), "gewindetiefe": gewindetiefe, "tiefe": tiefe}
    daten = {"ist": round(ist, 3), "soll": None if soll is None else round(soll, 3), "einschraublaenge": round(laenge, 3),
             "gewindetiefe": gewindetiefe, "tiefe": tiefe, "knoten": knoten, **({"hinweis": hinweis} if hinweis else {})}
    ok = None if soll is None else abs(ist - soll) <= soll * TOL_GEWINDE_PROZENT / 100
    if laenge > min(gewindetiefe, tiefe) + TOL_LAENGE:
        ok = False
```

In `swki/pruefung/bericht.py` ersetzen:

```python
        zeilen += [f"| {s} | {'ja' if e.get('gebaut') else 'nein'} | {_zelle(e.get('pruefsumme'))} |"
                   for s, e in sorted(letzter["normteile"].items())]
    if letzter.get("gewindepaarungen"):
        zeilen += ["", "## Gewindepaarungen", "",
```

durch:

```python
        zeilen += [f"| {s} | {'ja' if e.get('gebaut') else 'nein'} | {_zelle(e.get('pruefsumme'))} |"
                   for s, e in sorted(letzter["normteile"].items())]
    if letzter.get("kaufteile"):
        zeilen += ["", "## Kaufteile", "", "| Kaufteil | neu aufgenommen | Cache-Prüfsumme | Masse | Kennmaße |",
                   "|---|---|---|---|---|"]
        zeilen += [f"| {e.get('kaufteil', s)} | {'ja' if e.get('gebaut') else 'nein'} | {_zelle(e.get('pruefsumme'))} | "
                   f"{_zelle(e.get('masse'))} | {_zelle(e.get('kennmasse'))} |" for s, e in sorted(letzter["kaufteile"].items())]
    if letzter.get("gewindepaarungen"):
        zeilen += ["", "## Gewindepaarungen", "",
```

In `swki/aenderungen.py` ersetzen:

```python
        if n in sw_dateien:
            continue
        hinweis = ("keine Spezifikation zu dieser Datei (Normteil-Kopie)" if n.lower().endswith(_SW_DATEIEN)
                   else "Datei geändert (nicht ausgelesen)")
        ergebnis.append({"datei": n, "parameter": [], "hinweis": hinweis})
```

durch:

```python
        if n in sw_dateien:
            continue
        hinweis = ("keine Spezifikation zu dieser Datei (Normteil- oder Kaufteil-Kopie)" if n.lower().endswith(_SW_DATEIEN)
                   else "Datei geändert (nicht ausgelesen)")
        ergebnis.append({"datei": n, "parameter": [], "hinweis": hinweis})
```

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\baugruppe\test_kaufteil_bau_pruefen.py tests\test_aenderungen.py`
Expected: `23 passed`. Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **917 passed, 139 deselected**;
`.venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` → `"befunde": []`.

- [ ] **Step 5: Commit**

```powershell
git add swki/compiler/protokoll.py swki/baugruppe/bau.py swki/baugruppe/referenzen.py swki/baugruppe/pruefen.py swki/baugruppe/bewertung.py swki/pruefung/bericht.py swki/aenderungen.py tests/baugruppe/test_kaufteil_bau_pruefen.py tests/test_aenderungen.py
git commit -m "baugruppe: Kaufteile holen und kopieren, Gewinde-Referenz, Gewindepaarung im Kaufteil, Bericht (Stufe 3c, Task 9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Referenz Motorhalter mit Prüfer und Negativfall (live)

**Files:**
- Create: `tests/referenz/motorhalter/grundplatte.yaml`, `motorbock.yaml`, `motorhalter.yaml`, `eingabe/beschreibung.md`,
  `tests/referenz/test_motorhalter.py`, `tests/live/test_live_motorhalter.py`
- Modify: `tests/referenz/test_referenzen.py`

**Interfaces:**
- Consumes: Tasks 1–9 (Muster-Eintrag aus Task 7, Test-STEP aus Task 2).
- Produces: Referenz Motorhalter in der Regressions-Suite (`bereite_vor`), Negativfall „zu lange Flanschschraube“.

- [ ] **Step 1: Tests schreiben**

`tests/referenz/test_motorhalter.py` anlegen:

```python
"""Referenz Motorhalter (Spec 3c §11) ohne SolidWorks: gültig mit dem freigegebenen und geprüften Katalogeintrag des
Muster-Motors aus dem Repo, ohne Hinweis; 9 Komponenten, 18 Verknüpfungen."""

from pathlib import Path

from swki.baugruppe.befehle import validieren

MOTORHALTER = Path(__file__).parent / "motorhalter" / "motorhalter.yaml"


def test_motorhalter_gueltig_ohne_hinweis():
    v = validieren(MOTORHALTER)
    assert (v["komponenten"], v["verknuepfungen"], v["hinweise"]) == (9, 18, [])
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\referenz\test_motorhalter.py`
Expected: FAIL – `1 failed` (`SpecFehler: motorhalter.yaml fehlt noch`).

- [ ] **Step 3: Referenz-Specs und Live-Tests**

`tests/referenz/motorhalter/grundplatte.yaml` anlegen:

```yaml
# Referenz Motorhalter (Spec 3c §11): Grundplatte, Oberseite y = H, zwei Gewinde M6 für den Fuß des Motorbocks.
art: teil
name: Grundplatte
material: "1.0038"
eigenschaften: {Benennung: Grundplatte Motorhalter}
parameter: {L: 160, B: 100, H: 12, XG: 20, ZG: 20, GT: 10, GG: 8}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: normbohrung, art: gewinde, groesse: M6, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=-XG", "=ZG"], ["=-XG", "=-ZG"]], tiefe: "=GT", gewindetiefe: "=GG"}
pruefung:
  huellquader: ["=L", "=H", "=B"]
```

`tests/referenz/motorhalter/motorbock.yaml` anlegen:

```yaml
# Referenz Motorhalter (Spec 3c §11): Motorbock als Winkel. Fuß x 0…LF, y 0…HF; Wand x 0…DW, y 0…HW; Motorachse
# parallel zu x in Höhe AH. Zentrierbohrung DZ für den Bund des Motors, 4 Senkungen M5 auf der Rückseite (x = 0) für
# die Flanschschrauben, 2 Senkungen M6 im Fuß für die Befestigung auf der Grundplatte.
art: teil
name: Motorbock
material: "1.0038"
eigenschaften: {Benennung: Motorbock}
parameter: {LF: 75, BF: 60, HF: 10, DW: 10, HW: 90, AH: 50, DZ: 40, LK: 60, XS: 45, ZS: 20}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: ["=LF/2", 0], breite: "=LF", hoehe: "=BF"}}]}
    ende: {typ: blind, tiefe: "=HF"}
  - id: f2
    typ: extrusion
    skizze: {ebene: rechts, elemente: [{rechteck: {mitte: [0, "=HW/2"], breite: "=BF", hoehe: "=HW"}}]}
    ende: {typ: blind, tiefe: "=DW"}
  - {id: f3, typ: bohrung, flaeche: {feature: f2, flaeche: "+x"}, positionen: [[0, "=AH"]], durchmesser: "=DZ",
     durch: true}
  - {id: f4, typ: normbohrung, art: zylinderschraube, groesse: M5, flaeche: {nahe: [0, "=HW-5", 0]},
     positionen: [["=LK/8**0.5", "=AH+LK/8**0.5"], ["=-LK/8**0.5", "=AH+LK/8**0.5"], ["=-LK/8**0.5", "=AH-LK/8**0.5"],
                  ["=LK/8**0.5", "=AH-LK/8**0.5"]],
     durch: true}
  - {id: f5, typ: normbohrung, art: zylinderschraube, groesse: M6, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=XS", "=ZS"], ["=XS", "=-ZS"]], durch: true}
pruefung:
  huellquader: ["=LF", "=HW", "=BF"]
  masse_pruefen:
    - {was: Achshöhe Zentrierbohrung, von: {feature: f1, flaeche: "-y"}, zu: {feature: f3, instanz: 1, achse: true},
       soll: "=AH"}
```

`tests/referenz/motorhalter/motorhalter.yaml` anlegen:

```yaml
# Referenz Motorhalter (Spec 3c §11): Grundplatte (fixiert), Motorbock, Muster-Getriebemotor als Kaufteil aus dem
# Katalog (swki/wissen/kaufteile/swki-muster/gm42-10.yaml), 4 × ISO 4762 M5 × 12 durch die Wand in die Flanschgewinde
# des Motors, 2 × ISO 4762 M6 × 10 vom Fuß in die Grundplatte. Statisch; Motorachse ACHSHOEHE über der Unterseite.
art: baugruppe
name: Motorhalter
eigenschaften: {Benennung: Motorhalter}
parameter: {ACHSHOEHE: 62}
komponenten:
  - {id: grundplatte, quelle: {teil: grundplatte.yaml}, fixiert: true}
  - {id: bock, quelle: {teil: motorbock.yaml}}
  - {id: motor, quelle: {kaufteil: "SWKI-MUSTER GM42-10"}}
  - {id: flanschschraube, quelle: {normteil: "ISO 4762 M5x12"}, je_position: {komponente: bock, feature: f4}}
  - {id: fussschraube, quelle: {normteil: "ISO 4762 M6x10"}, je_position: {komponente: bock, feature: f5}}
verknuepfungen:
  - {id: v1, typ: deckungsgleich, a: {komponente: bock, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v2, typ: konzentrisch, a: {komponente: bock, feature: f5, instanz: 1, achse: true},
     b: {komponente: grundplatte, feature: f2, instanz: 1, achse: true}}
  - {id: v3, typ: parallel, a: {komponente: bock, feature: f1, flaeche: "+x"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+x"}, ausrichtung: gleich}
  - {id: v4, typ: deckungsgleich, a: {komponente: motor, referenz: EINBAU_FLANSCH},
     b: {komponente: bock, feature: f2, flaeche: "+x"}, ausrichtung: entgegengesetzt}
  - {id: v5, typ: konzentrisch, a: {komponente: motor, referenz: EINBAU_ACHSE},
     b: {komponente: bock, feature: f3, instanz: 1, achse: true}, drehung_sperren: false}
  - {id: v6, typ: parallel, a: {komponente: motor, referenz: EINBAU_DREHLAGE}, b: {komponente: bock, ebene: vorne},
     ausrichtung: gleich}
  - {id: v7, typ: deckungsgleich, a: {komponente: flanschschraube, referenz: EINBAU_EBENE},
     b: {komponente: bock, feature: f4, instanz: je, flaeche: "-x"}, ausrichtung: gleich}
  - {id: v8, typ: konzentrisch, a: {komponente: flanschschraube, referenz: EINBAU_ACHSE},
     b: {komponente: bock, feature: f4, instanz: je, achse: true}}
  - {id: v9, typ: deckungsgleich, a: {komponente: fussschraube, referenz: EINBAU_EBENE},
     b: {komponente: bock, feature: f5, instanz: je, flaeche: "+y"}, ausrichtung: gleich}
  - {id: v10, typ: konzentrisch, a: {komponente: fussschraube, referenz: EINBAU_ACHSE},
     b: {komponente: bock, feature: f5, instanz: je, achse: true}}
pruefung:
  huellquader: [160, 102, 100]
  masse_pruefen:
    - {was: Achshöhe, von: {komponente: grundplatte, feature: f1, flaeche: "-y"},
       zu: {komponente: motor, referenz: EINBAU_ACHSE}, soll: "=ACHSHOEHE"}
```

`tests/referenz/motorhalter/eingabe/beschreibung.md` anlegen:

~~~markdown
# Motorhalter (Referenz Stufe 3c)

Getriebemotor (Kaufteil, hier der fiktive Muster-Motor SWKI-MUSTER GM42-10, Datenblatt `muster/datenblatt.md`) auf
einem Motorbock, der auf einer Grundplatte 160 × 100 × 12 sitzt (Stahl S235, 1.0038).

- Motorbock als Winkel: Fuß 75 × 10 × 60, Wand 10 × 90 × 60. Motorachse waagerecht, 50 über der Fußunterseite, also
  62 über der Grundplatten-Unterseite.
- Der Motor liegt mit der Flanschfläche an der Wand an, der Zentrierbund Ø 40 sitzt in einer Zentrierbohrung Ø 40,
  die Welle ragt hinten durch die Wand. Die Lochbilder von Motor und Wand fluchten.
- Befestigung Motor: 4 × ISO 4762 M5 × 12 von der Wandrückseite in die Flanschgewinde M5 des Motors, Köpfe versenkt.
- Befestigung Bock: 2 × ISO 4762 M6 × 10 vom Fuß in Gewinde M6 der Grundplatte (Gewindetiefe 8), Köpfe versenkt.
- Alle Teile voll bestimmt, keine Überlappung außer den Gewindepaarungen, Einschraublänge nicht über der Gewindetiefe.
~~~

In `tests/referenz/test_referenzen.py` ersetzen:

```python
pytestmark = pytest.mark.sw
REFERENZEN = Path(__file__).parent
```

durch:

```python
pytestmark = pytest.mark.sw
REFERENZEN = Path(__file__).parent
MUSTER_STEP = REFERENZEN / "motorhalter" / "muster" / "gm42-10.step"
```

In `tests/referenz/test_referenzen.py` ersetzen:

```python
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)
```

durch:

```python
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def bereite_vor(ordner: str) -> None:
    """Vorbereitung ohne SolidWorks: der Motorhalter braucht das Original des Muster-Kaufteils im Quellordner der
    Kaufteil-Bibliothek (Spec 3c §11; nur eine Kopie, nie überschrieben)."""
    if ordner == "motorhalter":
        from swki.kaufteile import quelle  # spät importiert: nur diese Referenz braucht Kaufteile
        from swki.kaufteile.eintrag import lade_eintrag
        from swki.kaufteile.katalog import finde

        eintrag = lade_eintrag(finde("SWKI-MUSTER GM42-10"))
        quelle.uebernimm(lade_rechner(), MUSTER_STEP, "SWKI-MUSTER", "GM42-10", eintrag)
```

In `tests/referenz/test_referenzen.py` ersetzen:

```python
    ("zahnstangentrieb", "antriebswelle.yaml"),
    ("zahnstangentrieb", "zahnstangentrieb.yaml"),
])
def test_referenz_besteht(capsys, tmp_path, ordner, spec):
```

durch:

```python
    ("zahnstangentrieb", "antriebswelle.yaml"),
    ("zahnstangentrieb", "zahnstangentrieb.yaml"),
    ("motorhalter", "motorhalter.yaml"),
])
def test_referenz_besteht(capsys, tmp_path, ordner, spec):
```

In `tests/referenz/test_referenzen.py` ersetzen:

```python
    shutil.copytree(REFERENZEN / ordner, auftrag)
    spec_pfad = auftrag / spec
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
```

durch:

```python
    shutil.copytree(REFERENZEN / ordner, auftrag)
    spec_pfad = auftrag / spec
    bereite_vor(ordner)
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
```

`tests/live/test_live_motorhalter.py` anlegen:

```python
"""Live-Negativfall der Referenz Motorhalter (Spec 3c §11): zu lange Flanschschrauben ISO 4762 M5 × 16 – die
Einschraublänge (11,4 mm) überschreitet Gewindetiefe 8 und Bohrtiefe 10 des Kaufteil-Gewindes. Erwartet genau die vier
Mängel gewinde:flanschschraube.<i>; sonst nichts."""

import json
import shutil

import pytest
import yaml

from swki.cli import main
from swki.konfig import lade_rechner
from tests.referenz.test_referenzen import REFERENZEN, bereite_vor

pytestmark = pytest.mark.sw


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_zu_lange_flanschschraube(capsys, tmp_path):
    auftrag = tmp_path / "NEG-MOTORHALTER"
    shutil.copytree(REFERENZEN / "motorhalter", auftrag)
    spec_pfad = auftrag / "motorhalter.yaml"
    spec = yaml.safe_load(spec_pfad.read_text(encoding="utf-8"))
    spec["komponenten"][3]["quelle"] = {"normteil": "ISO 4762 M5x16"}
    spec_pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    bereite_vor("motorhalter")
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
        assert code == 0, bericht
        assert {m["pruefung"] for m in bericht["maengel"]} == {f"gewinde:flanschschraube.{i}" for i in range(1, 5)}, \
            bericht["maengel"]
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / "NEG-MOTORHALTER", ignore_errors=True)
```

- [ ] **Step 4: Validieren ohne SolidWorks**

Run: `.venv\Scripts\python.exe -m pytest -q tests\referenz\test_motorhalter.py` → `1 passed`; `.venv\Scripts\python.exe -m swki validieren tests\referenz\motorhalter\grundplatte.yaml` und
`… motorbock.yaml` → `"gueltig": true`, `"hinweise": []`. Ganze Suite: **918 passed, 141 deselected**.

- [ ] **Step 5: Referenz live (frisches SolidWorks)**

BLOCKED Neustart an den Controller, dann:
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m pytest -m sw "tests/referenz/test_referenzen.py::test_referenz_besteht[motorhalter-motorhalter.yaml]" -q`
Expected: passed. Private Bytes (Spitze, 0,5 s) und Dauer notieren. Mängel: Bauweg nachbessern (Verknüpfungen, Reihenfolge,
Ausrichtung nach `bezug.richtung` im Prüfbericht des Kaufteils – Spike-Zeile 7), nie Prüfwerte.

- [ ] **Step 6: Prüfer-Urteil (Controller)**

Auftrag `auftraege/REF-3C-MOTORHALTER/` (Kopie von `tests/referenz/motorhalter/`), `swki validieren`, `freigeben`, `bauen`,
`pruefen`; der **Controller** startet den Prüfer-Agenten mit Eingabe, allen freigegebenen Specs, dem Eintrag
`swki/wissen/kaufteile/swki-muster/gm42-10.freigegeben.yaml`, Prüfbericht und Bildern; Urteil unverändert nach
`protokolle/motorhalter.lauf-<n>.pruefer.json`; `swki status`. Erwartet `{"bestanden": true, "maengel": []}`. Auftrag und
Arbeitsordner danach löschen.

- [ ] **Step 7: Negativfall (frisches SolidWorks)**

BLOCKED Neustart an den Controller, dann:
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_motorhalter.py --zeit 900`
Expected: `OK` (genau die Mängel `gewinde:flanschschraube.1` … `.4`). Abweichung: Erwartung nicht abschwächen, NEEDS_CONTEXT.

- [ ] **Step 8: Commit**

```powershell
git add tests/referenz/motorhalter tests/referenz/test_motorhalter.py tests/referenz/test_referenzen.py tests/live/test_live_motorhalter.py
git commit -m "referenz: Motorhalter mit Muster-Getriebemotor, Regression, Negativfall zu lange Flanschschraube (Stufe 3c, Task 10)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Skills, Prüfer, CLAUDE.md, Design, Ergebnisse, Regression, Abnahme

**Files:**
- Create: `.claude/skills/kaufteile/SKILL.md`, `docs/stufe3c/ergebnisse.md`
- Modify: `.claude/skills/baugruppe/SKILL.md`, `.claude/skills/normteile/SKILL.md`, `.claude/agents/pruefer.md`, `CLAUDE.md`,
  `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`, Spec 3c (Nachzug nach der Umsetzung)

- [ ] **Step 1: Skills und Prüfer**

`.claude/skills/kaufteile/SKILL.md` anlegen:

~~~markdown
---
name: kaufteile
description: Nicht genormte Kaufteile von Herstellern (Motor mit Flansch, Kugellager, Pneumatikzylinder, Führungswagen …) als STEP aufnehmen – untersuchen, Belege für Kennmaße, Katalogeintrag, Freigabe durch den Nutzer, Prüfer, holen – und in Baugruppen verwenden. Verwenden, wenn der Nutzer eine Herstellerdatei gibt oder eine Baugruppe ein nicht genormtes Kaufteil braucht. Genormte Schrauben, Muttern, Scheiben, Stifte nie hierüber (Skill normteile).
---

# Kaufteile (Stufe 3c)

Spec: `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` (Abweichungen der Umsetzung:
`docs/stufe3c/ergebnisse.md`). Befehle `.venv\Scripts\python.exe -m swki …` (JSON). Vorlage: Muster-Getriebemotor
`swki/wissen/kaufteile/swki-muster/gm42-10.yaml`, Referenz `tests/referenz/motorhalter/`.

## 1. Abgrenzung
- **Nur nicht genormte Kaufteile.** Genormte Verbindungselemente kommen immer über `swki normteil hole` (Skill
  `normteile`); `validieren` weist Einträge ab, deren Benennung oder Bestellnummer eine Norm der Normtabellen nennt
  (`KAUFTEIL_GENORMT`). Fehlt eine Normgröße: Normtabelle erweitern, nie eine STEP holen.
- **Nur STEP** (`.step`/`.stp`). Andere Formate: den Nutzer bitten, beim Hersteller die STEP zu laden.
- **Dateien kommen vom Nutzer.** Claude lädt nichts von Herstellerportalen, legt keine Konten an und meldet sich nirgends
  an. Die Datei des Nutzers wird nur gelesen; swki kopiert sie unverändert in den Quellordner der Kaufteil-Bibliothek.
- Eine STEP wird **ein Teil** (Mehrkörper erlaubt). Bewegliche Baueinheiten (Schiene + Wagen, Zylinder + Kolbenstange)
  braucht es als getrennte STEP-Dateien – sonst den Nutzer darum bitten.

## 2. Untersuchen
`swki kaufteil untersuchen <step> --hersteller <H> --bestellnummer <B> [--datenblatt <datei>]`
- Hersteller ohne Leerzeichen (z. B. `NANOTEC`, `SKF`), Bestellnummer genau wie beim Hersteller.
- Ausgabe: `diagnose` (Körper, Flächenkörper, `koerperfehler`, Hüllquader, Volumen, `zylinder`/`ebenen` mit Punkten
  `nahe`, Dateigröße, Importzeit, Speicherspitze, Bilder) und `geruest` des Eintrags. Bilder ansehen.
- `KAUFTEIL_IMPORT` oder Flächenkörper/Körperfehler: nicht reparieren – den Nutzer um ein anderes Modell bitten.
- `KAUFTEIL_QUELLE_ABWEICHEND`: Die Datei unterscheidet sich vom Original im Quellordner bzw. im Eintrag. Den Nutzer fragen:
  neue Herstellerversion als **eigener Eintrag** oder **Eintrag ändern** (`--neue-version` legt die Datei neben das alte
  Original; dann `original` im Eintrag anpassen, neu validieren, Nutzer-OK, freigeben, neues Prüfer-Urteil).
- Große Modelle (viele Flächen, lange Importzeit) sind erlaubt; Kennzahlen dem Nutzer nennen.

## 3. Belege für Kennmaße und Masse
1. Datenblatt vom Nutzer → daraus (`belege: {d1: {art: datenblatt, datei: <name>, seite: n}}`, Datei mit
   `--datenblatt` in den Quellordner).
2. Sonst selbst suchen, nur öffentliche Seiten ohne Anmeldung, Herstellerseite zuerst. In Suchanfragen nur Hersteller und
   Bestellnummer, keine Daten des Nutzers.
3. Belegregel: eine Herstellerquelle (`hersteller` mit `url` und `abgerufen`, oder `datenblatt`) oder `nutzer` genügt
   allein; Händler- und Drittseiten (`haendler`) nur mit ≥ 2 verschiedenen Domains. Widersprechen sich Quellen: den Wert
   nicht übernehmen, den Nutzer fragen (eine Frage, mit Empfehlung).
4. Nichts gefunden: nur das Belegte prüfen; der Rest bleibt ohne `beleg` („nicht belegt“ in Eintrag und Bericht).
   **Werte aus der STEP-Diagnose sind nie Kennmaße** – nur Ankerpunkte, `pruefung.volumen` und unbelegte Gewindetiefen.

## 4. Eintrag schreiben
`swki/wissen/kaufteile/<hersteller-ordner>/<bestellnummer-datei>.yaml` (Ordner und Datei kleingeschrieben, wie
`untersuchen` sie in `eintrag` nennt). Aus dem `geruest`, dazu:
- `benennung`, `material` (Name der SW-Materialdatenbank, Pflicht), `masse: {kg, beleg}` wenn bekannt, `eigenschaften`.
- `einbau` mit `EINBAU_<NAME>`: `zylinder: {nahe, durchmesser, senkrecht_zu?}` (Achse), `ebene: {nahe, normale}`
  (Anlagefläche, Normale aus dem Material), `ebene_durch_achse: {achse, nahe}` (Drehlage, z. B. durch eine Lochmitte).
  `nahe` liegt auf der Fläche (Punkte aus der Diagnose); Ø und Normale sind die Gegenprobe.
- `gewinde: {<gruppe>: {groesse, gewindetiefe, tiefe, normale, positionen, beleg?}}` für Gewindelöcher, in die Normteile
  geschraubt werden (Eintrittspunkte, `normale` aus dem Material).
- `pruefung`: `huellquader {soll, tol, beleg}`, `volumen` aus dem Gerüst, `durchmesser_pruefen`, `masse_pruefen` (Messpunkte
  `referenz`, `gewinde`+`instanz`, `flaeche {nahe, normale}`, `punkt`).
- Datumsangaben in Anführungszeichen (`"2026-10-07"`).
`swki validieren <eintrag.yaml>` bis `gueltig`; `hinweise` (`nicht_belegt`, `masse_aus_material`) dem Nutzer nennen.

## 5. Freigabe, Prüfer, holen
- Dem Nutzer zeigen: Eintrag (Kennmaße mit Belegen), Diagnosebilder, was jede Einbaureferenz bedeutet. Erst nach
  ausdrücklichem OK: `swki freigeben <eintrag.yaml>` (deckt den ganzen Eintrag ab).
- `swki kaufteil muster "<H> <B>"` → Prüfer-Agent (`subagent_type: pruefer`) mit `eintrag` (freigegebene Kopie),
  `datenblatt`, `pruefbericht`, Bildern → Urteil als rohes JSON in eine Datei →
  `swki kaufteil urteil "<H> <B>" <datei> --freigabe-pruefsumme <x>` (`freigabe_pruefsumme` aus `muster`).
- `swki kaufteil hole "<H> <B>"` → Cache-Treffer (`gebaut: false`) oder Aufnahme mit Prüfung. `swki kaufteil liste
  [--veraltet]` zeigt Freigabe, Urteil, Cache.

| Code | Vorgehen |
|---|---|
| `KAUFTEIL_FORMAT` | nur STEP; Nutzer um STEP bitten |
| `KAUFTEIL_UNBEKANNT` | vorhandene Schlüssel nennen; neues Kaufteil → Abschnitt 2 |
| `KAUFTEIL_QUELLE_FEHLT` | Nutzer gibt die Datei erneut (`untersuchen` stellt das Original wieder her, SHA-256 muss passen) |
| `KAUFTEIL_QUELLE_ABWEICHEND` | Abschnitt 2 |
| `KAUFTEIL_IMPORT` | Modell defekt oder nicht importierbar – Nutzer fragen |
| `KAUFTEIL_UNGEPRUEFT` | Prüfer-Ablauf oben |
| `KAUFTEIL_PRUEFUNG` | Mängel lesen: `einbau:<name>` / `gewinde:<gruppe>` (Punkt falsch oder Gegenprobe verfehlt), `koerper`, `huellquader`, `mass:*` – Eintrag nach Rücksprache korrigieren (Nutzer-OK, neue Freigabe); Sollwerte nie an Messwerte anpassen |
| `FREIGABE_FEHLT` / `FREIGABE_VERALTET` | Nutzer fragen, neu freigeben |

## 6. In Baugruppen
- `quelle: {kaufteil: "<H> <B>"}`; Referenzen nur `{komponente, referenz: EINBAU_*}` und
  `{komponente, gewinde, instanz, achse: true}`; `je_position: {komponente, gewinde}` für Schrauben je Gewindeposition.
- Ausrichtung: Flächen- und Bezugsebenen-Normalen wie im Prüfbericht des Kaufteils (`einbau:<name>` → `bezug.richtung`).
- `drehung_sperren` ist bei Kaufteilen Vorgabe; wer die Drehlage über eine `ebene_durch_achse` verknüpft, setzt an der
  konzentrischen Verknüpfung `drehung_sperren: false` (Hinweis `drehlage_doppelt`).
- Die Baugruppen-Freigabe schützt den Eintrag mit: Ändert sich ein Eintrag, meldet `bauen` `FREIGABE_VERALTET` mit dem
  Kaufteil – Nutzer fragen, Baugruppe neu freigeben.
- Schrauben im Kaufteil-Gewinde: Gewindepaarung wie bei Eigenteilen (Modell `kernloch` → Ringvolumen, `nenn` → keine
  Überlappung); jede andere Überlappung ist ein Mangel.
~~~

In `.claude/skills/normteile/SKILL.md` ersetzen:

~~~markdown

Genormte Teile kommen **immer** aus `swki normteil` (Spec `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md`).
Herstellerdaten (STEP) nur für nicht genormte Kaufteile.

## Abrufen
~~~

durch:

~~~markdown

Genormte Teile kommen **immer** aus `swki normteil` (Spec `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md`).
Herstellerdaten (STEP) nur für nicht genormte Kaufteile (Skill `kaufteile`); fehlt eine Normgröße, die Normtabelle
erweitern (unten), nie eine STEP holen.

## Abrufen
~~~

In `.claude/skills/baugruppe/SKILL.md` ersetzen:

~~~markdown
---

# Baugruppe (Stufe 3b, Bewegungen Stufe 4a, Kopplungen Stufe 4b)

Spec: `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md` (Abweichungen der Umsetzung: `docs/stufe3b/ergebnisse.md`).
~~~

durch:

~~~markdown
---

# Baugruppe (Stufe 3b, Kaufteile Stufe 3c, Bewegungen Stufe 4a, Kopplungen Stufe 4b)

Spec: `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md` (Abweichungen der Umsetzung: `docs/stufe3b/ergebnisse.md`).
~~~

In `.claude/skills/baugruppe/SKILL.md` ersetzen:

~~~markdown
  Regeln aus dem Skill `konstruieren`, Abschnitt 2).
- Normteile nie als Teil-Spec: in der Baugruppe als `quelle: {normteil: "<Norm> <Größe>"}` (Skill `normteile`).

## 2. Baugruppen-Spec
~~~

durch:

~~~markdown
  Regeln aus dem Skill `konstruieren`, Abschnitt 2).
- Normteile nie als Teil-Spec: in der Baugruppe als `quelle: {normteil: "<Norm> <Größe>"}` (Skill `normteile`).
- Nicht genormte Kaufteile nie als Teil-Spec: `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}` aus dem Katalog
  (Skill `kaufteile`, Abschnitt 8 unten).

## 2. Baugruppen-Spec
~~~

In `.claude/skills/baugruppe/SKILL.md` ersetzen:

~~~markdown
- Speicher und Neustart wie §6: Live-Läufe mit Kopplungen je Test auf frischem SolidWorks.
~~~

durch:

~~~markdown
- Speicher und Neustart wie §6: Live-Läufe mit Kopplungen je Test auf frischem SolidWorks.

## 8. Kaufteile (Stufe 3c)

Nicht genormte Kaufteile kommen aus dem Katalog (Skill `kaufteile`). Spec:
`docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md`. Vorlage: `tests/referenz/motorhalter/`.

- `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}`; der Eintrag muss freigegeben sein und ein bestandenes
  Prüfer-Urteil haben (`KAUFTEIL_NICHT_FREIGEGEBEN`, `KAUFTEIL_UNGEPRUEFT` als Befunde von `validieren`).
- Referenzen nur `{komponente, referenz: EINBAU_*}` (Namen aus dem Eintrag) und `{komponente, gewinde, instanz, achse: true}`
  (Achse einer Gewindeposition); nie `feature`, `ebene` oder `nahe` in fremder Geometrie. `je_position: {komponente,
  gewinde}` erzeugt eine Instanz je Gewindeposition; meist genügt aber `je_position` auf die Bohrungen des Gegenstücks.
- Reihenfolge wie bei Normteilen: Anlagefläche (`deckungsgleich` mit `ausrichtung`), dann Achse (`konzentrisch`), dann die
  Drehlage (`parallel`/`winkel` auf die `ebene_durch_achse`). Mit Drehlage `drehung_sperren: false` an der Achse.
- Passung: ISO 4762 nur in Kaufteil-Gewinde gleicher Größe (`validieren`). `pruefen` rechnet die Gewindepaarung mit der
  Gewindetiefe des Eintrags; Kaufteile bekommen keine Teilprüfung (sie wurden bei der Aufnahme geprüft), der Bericht nennt
  Cache-Prüfsumme, Masse (Datenblatt oder Material) und Belegstand.
- Ändert sich ein Eintrag nach der Baugruppen-Freigabe: `FREIGABE_VERALTET` mit dem Kaufteil – Nutzer fragen, neu freigeben.
~~~

In `.claude/agents/pruefer.md` ersetzen:

~~~markdown
   über der Gewindetiefe.
4. `bestimmtheit` und `kollision` ok; jede Teilprüfung (`<komponente>: …`) ok.

## Zusätzlich bei Bewegungen (`bewegungen` in der Spezifikation)
~~~

durch:

~~~markdown
   über der Gewindetiefe.
4. `bestimmtheit` und `kollision` ok; jede Teilprüfung (`<komponente>: …`) ok.

## Zusätzlich bei Kaufteilen (`art: kaufteil`, Aufnahme eines Katalogeintrags)
Du bekommst den freigegebenen Eintrag (`<datei>.freigegeben.yaml`), das Datenblatt (falls vorhanden), den Prüfbericht
und die Bilder des Musterteils (Bezugsachsen und -ebenen eingeblendet). Knoten sind `einbau:<name>`, `gewinde:<gruppe>`
oder die Prüfungs-ID.
1. Jede Einbaureferenz sitzt auf der Fläche, die der Eintrag meint (Wellenachse auf der Welle, Flanschebene auf der
   Anlagefläche hinter dem Zentrierbund, Drehlage durch das Lochbild); Normalen und Achsen sind fachlich sinnvoll
   orientiert (`einbau:*` → `bezug.richtung`).
2. Kennmaße passen zum Datenblatt (Wert und Beleg); „nicht belegt“ ist kein Mangel, wenn der Eintrag es so ausweist.
3. Masse plausibel (Datenblatt bzw. Material), Körperzahl plausibel, Hüllquader wie im Datenblatt.
4. Kein genormtes Verbindungselement (Schraube, Mutter, Scheibe, Stift) – das gehört zu den Normteilen.
In Baugruppen werden Kaufteile wie Normteile nur auf Lage und Verbindung beurteilt (Checkliste Baugruppen).

## Zusätzlich bei Bewegungen (`bewegungen` in der Spezifikation)
~~~

- [ ] **Step 2: CLAUDE.md und Design**

In `CLAUDE.md` ersetzen:

~~~markdown
Stand: Stufe 4b (Verzahnung und Kopplungen) umgesetzt – Ergebnisse: docs/stufe4b/ergebnisse.md. Nächster Schritt
(Nutzerwahl): Stufe 3c Kaufteile (STEP-Import) umsetzen – Plan docs/superpowers/plans/2026-10-06-kaufteile-step-import.md,
Übergabe docs/superpowers/uebergabe-2026-10-06-kaufteile-umsetzung.md. Danach zur Wahl: Formschräge, Stufe 4c (Nut- und
Kurvenverknüpfung), Paket „Messarten“ (Fasen, Gewinde durch, Lagerachse), Paket Speicher.
~~~

durch:

~~~markdown
Stand: Stufe 3c (Kaufteile, STEP-Import) umgesetzt – Ergebnisse: docs/stufe3c/ergebnisse.md (davor 4b:
docs/stufe4b/ergebnisse.md). Nächster Schritt nach Nutzerwahl: Formschräge, Stufe 4c (Nut- und Kurvenverknüpfung), Paket
„Messarten“ (Fasen, Gewinde durch, Lagerachse), Paket Speicher.
~~~

In `CLAUDE.md` ersetzen:

~~~markdown
- Bauvorlagen nur mit neuem Prüfer-Urteil (`swki normteil muster` → Prüfer → `swki normteil urteil`).

## Baugruppen (Stufe 3b)
~~~

durch:

~~~markdown
- Bauvorlagen nur mit neuem Prüfer-Urteil (`swki normteil muster` → Prüfer → `swki normteil urteil`).

## Kaufteile (Stufe 3c)
- Nicht genormte Kaufteile über den Skill `kaufteile`: nur STEP, die Datei des Nutzers nur lesen (swki kopiert sie
  unverändert in den Quellordner der `kaufteilbibliothek`); keine Konten bei Herstellerportalen, keine Anmeldung, keine
  Downloads durch Claude.
- Katalogeintrag `swki/wissen/kaufteile/<hersteller>/<bestellnummer>.yaml` (`art: kaufteil`): Kennmaße mit Beleg
  (Herstellerquelle oder Nutzer allein, Händler nur mit ≥ 2 Domains; Werte aus der STEP sind nie Kennmaße);
  `swki validieren` → Nutzer-OK → `swki freigeben` → `swki kaufteil muster` → Prüfer → `swki kaufteil urteil` →
  `swki kaufteil hole`.
- In die `kaufteilbibliothek` schreibt nur `swki kaufteil` (Quellordner nur Kopien, Cache je SW-Jahr). Importierte Geometrie
  nie reparieren, vereinfachen oder verschieben.
- Baugruppen: `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}`, Referenzen nur `EINBAU_*` und Gewindepositionen; die
  Baugruppen-Freigabe schützt den Eintrag mit (`FREIGABE_VERALTET` nennt das Kaufteil).
- Regressions-Suite enthält den Motorhalter (`tests/referenz/motorhalter/`, Test-STEP `muster/gm42-10.step` im Git).

## Baugruppen (Stufe 3b)
~~~

In `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` ersetzen:

~~~markdown
- Die Spezifikation ist die Quelle; SolidWorks-Dateien aus Aufträgen kommen nicht ins Git.
- Eigene Normteil-Dateien werden nur auf dem 2025-Rechner gespeichert (2026-Dateien sind in 2025
  nicht lesbar). `swki normteil aufnehmen` verweigert das Speichern in die Bibliothek unter SW > 2025.
- Compiler-Code verwendet nur API-Aufrufe, die in SW 2025 verfügbar sind (siehe 7).
- Namensschema für Dateien und Custom Properties ist in `config/standard.yaml` konfigurierbar
~~~

durch:

~~~markdown
- Die Spezifikation ist die Quelle; SolidWorks-Dateien aus Aufträgen kommen nicht ins Git.
- Eigene Normteil-Dateien werden nur auf dem 2025-Rechner gespeichert (2026-Dateien sind in 2025
  nicht lesbar). **Stand 3a/3c:** Normteil- und Kaufteil-Bibliothek sind Caches getrennt je SW-Jahr
  (`<bibliothek>/<sw_jahr>/`); maßgeblich sind Normtabelle/Vorlage bzw. Katalogeintrag und Original
  (`config/rechner.yaml`: `normteilbibliothek`, `kaufteilbibliothek`).
- Compiler-Code verwendet nur API-Aufrufe, die in SW 2025 verfügbar sind (siehe 7).
- Namensschema für Dateien und Custom Properties ist in `config/standard.yaml` konfigurierbar
~~~

In `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` ersetzen:

~~~markdown
python -m swki bauen      <spec> [--lauf n]
python -m swki pruefen    <spec> --lauf n
python -m swki normteil suchen|aufnehmen ...
python -m swki api suche|methode|enum|pruefe-code ...
```
~~~

durch:

~~~markdown
python -m swki bauen      <spec> [--lauf n]
python -m swki pruefen    <spec> --lauf n
python -m swki normteil hole|tabellen-pruefen|liste|muster|urteil ...
python -m swki kaufteil untersuchen|muster|urteil|hole|liste ...   # Stufe 3c
python -m swki api suche|methode|enum|pruefe-code ...
```
~~~

In `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` ersetzen:

~~~markdown
**Stand Stufe 3a (2026-10-02):** Genormte Teile werden selbst konstruiert, aus Normtabelle und Bauvorlage, prüfen sich selbst und füllen eine lokale Bibliothek – siehe [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md). Katalog je Hersteller und `normteil aufnehmen` gelten nur noch für nicht genormte Kaufteile (eigenes Paket bei Bedarf); der Toolbox-Rückfall entfällt.

- Katalog `normteile/katalog/<hersteller>.yaml`: `id`, `benennung`, `typ`, `kennmasse`,
  `quelle` (`datei` oder `toolbox`), `einbau` (Zuordnung Einbaureferenz → Geometrie im Teil),
~~~

durch:

~~~markdown
**Stand Stufe 3a (2026-10-02):** Genormte Teile werden selbst konstruiert, aus Normtabelle und Bauvorlage, prüfen sich selbst und füllen eine lokale Bibliothek – siehe [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md). Katalog je Hersteller und `normteil aufnehmen` gelten nur noch für nicht genormte Kaufteile (eigenes Paket bei Bedarf); der Toolbox-Rückfall entfällt.

**Stand Stufe 3c:** Nicht genormte Kaufteile kommen als STEP des Herstellers in einen Katalog (je Kaufteil ein Eintrag `art: kaufteil` unter `swki/wissen/kaufteile/`, Nutzerfreigabe je Eintrag, Prüfer-Urteil, Cache je SW-Jahr) – siehe [2026-10-06-kaufteile-step-import-design.md](2026-10-06-kaufteile-step-import-design.md). `swki normteil aufnehmen` entfällt; die Befehle heißen `swki kaufteil …`. Die Absätze unten sind der Ausgangsentwurf.

- Katalog `normteile/katalog/<hersteller>.yaml`: `id`, `benennung`, `typ`, `kennmasse`,
  `quelle` (`datei` oder `toolbox`), `einbau` (Zuordnung Einbaureferenz → Geometrie im Teil),
~~~

In `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` ersetzen:

~~~markdown
  - `konstruieren`: Eingabe → Spezifikation → validieren → Rückfragen → Freigabe → bauen →
    prüfen → nachbessern → Bericht.
  - `normteile`: suchen, nachfragen, aufnehmen.
  - `compiler-erweitern` – **wird von Claude selbst ausgelöst**, wenn (a) eine Lücke zum zweiten
    Mal auftritt und ein bestandenes Skript existiert, (b) einem Handler eine Option fehlt,
~~~

durch:

~~~markdown
  - `konstruieren`: Eingabe → Spezifikation → validieren → Rückfragen → Freigabe → bauen →
    prüfen → nachbessern → Bericht.
  - `normteile`: abrufen, nachfragen, Normtabellen erweitern (Stufe 3a).
  - `kaufteile`: STEP untersuchen, Belege, Katalogeintrag, Freigabe, Prüfer, holen (Stufe 3c).
  - `compiler-erweitern` – **wird von Claude selbst ausgelöst**, wenn (a) eine Lücke zum zweiten
    Mal auftritt und ein bestandenes Skript existiert, (b) einem Handler eine Option fehlt,
~~~

In `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` ersetzen:

~~~markdown
| 3a | Normteile: Normtabellen mit Abgleich, Bauvorlagen, Selbstprüfung, Bibliothek (ISO 4762, 4032, 7089, 8734) – Design: [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md) | Tabellen abgeglichen oder begründet gesperrt, Prüfer-Urteile je Vorlage, Stichprobe 20 Teile besteht |
| 3b | Baugruppen statisch: Standardverknüpfungen, Bestimmtheit, statische Kollision, Änderungserkennung – Design: [2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md) | Referenz *Stehlager* besteht (Code-Prüfungen und Prüfer); Buchse, Formplatte und Auswerferhalteplatte bestehen weiter |
| 4a | Bewegungen: Grenzverknüpfungen, Scharnier, gezählte Freiheitsgrade, `bewegungen`, Bewegungsprüfung (Kollision je Stellung, Grenze, Freiheitsgrad, Endlagen, Paarläufe) – Design: [2026-10-03-stufe-4a-bewegungen-design.md](2026-10-03-stufe-4a-bewegungen-design.md) | Referenz *Linearschlitten* besteht (Code-Prüfungen und Prüfer), vier Negativfälle; Buchse, Formplatte, Auswerferhalteplatte, Stehlager bestehen weiter |
| 4b | Verzahnung (Feature `verzahnung`: Evolventen-Stirnrad, Zahnstange) und Kopplungen (Zahnrad-, Zahnstangenverknüpfung), Sollweg je Stellung – Design: [2026-10-05-stufe-4b-verzahnung-kopplungen-design.md](2026-10-05-stufe-4b-verzahnung-kopplungen-design.md) | Teil-Referenzen *Zahnstange*, *Ritzelwelle*, *Antriebswelle* und Referenz *Zahnstangentrieb* bestehen (Code-Prüfungen und Prüfer), fünf Negativfälle; Buchse, Formplatte, Auswerferhalteplatte, Stehlager, Linearschlitten bestehen weiter |
~~~

durch:

~~~markdown
| 3a | Normteile: Normtabellen mit Abgleich, Bauvorlagen, Selbstprüfung, Bibliothek (ISO 4762, 4032, 7089, 8734) – Design: [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md) | Tabellen abgeglichen oder begründet gesperrt, Prüfer-Urteile je Vorlage, Stichprobe 20 Teile besteht |
| 3b | Baugruppen statisch: Standardverknüpfungen, Bestimmtheit, statische Kollision, Änderungserkennung – Design: [2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md) | Referenz *Stehlager* besteht (Code-Prüfungen und Prüfer); Buchse, Formplatte und Auswerferhalteplatte bestehen weiter |
| 3c | Kaufteile: STEP-Import nicht genormter Kaufteile, Katalog (`art: kaufteil`, Belege, Freigabe je Eintrag, Prüfer), Cache je SW-Jahr, Komponentenquelle `kaufteil`, Gewindepaarung im Kaufteil – Design: [2026-10-06-kaufteile-step-import-design.md](2026-10-06-kaufteile-step-import-design.md) | Muster-Getriebemotor aufgenommen und Referenz *Motorhalter* besteht (Code-Prüfungen und Prüfer), Negativfälle, Abnahme mit echter Herstellerdatei dokumentiert; bisherige Referenzen bestehen weiter |
| 4a | Bewegungen: Grenzverknüpfungen, Scharnier, gezählte Freiheitsgrade, `bewegungen`, Bewegungsprüfung (Kollision je Stellung, Grenze, Freiheitsgrad, Endlagen, Paarläufe) – Design: [2026-10-03-stufe-4a-bewegungen-design.md](2026-10-03-stufe-4a-bewegungen-design.md) | Referenz *Linearschlitten* besteht (Code-Prüfungen und Prüfer), vier Negativfälle; Buchse, Formplatte, Auswerferhalteplatte, Stehlager bestehen weiter |
| 4b | Verzahnung (Feature `verzahnung`: Evolventen-Stirnrad, Zahnstange) und Kopplungen (Zahnrad-, Zahnstangenverknüpfung), Sollweg je Stellung – Design: [2026-10-05-stufe-4b-verzahnung-kopplungen-design.md](2026-10-05-stufe-4b-verzahnung-kopplungen-design.md) | Teil-Referenzen *Zahnstange*, *Ritzelwelle*, *Antriebswelle* und Referenz *Zahnstangentrieb* bestehen (Code-Prüfungen und Prüfer), fünf Negativfälle; Buchse, Formplatte, Auswerferhalteplatte, Stehlager, Linearschlitten bestehen weiter |
~~~

- [ ] **Step 3: Regression (Controller fährt sie per Skript)**

Je Test einzeln (`pytest -m sw <Test-ID>`), SolidWorks vor jedem Baugruppen-Test neu gestartet, vor Teil-Tests bei > 3000 MB;
Private Bytes vorher → Spitze (0,5 s) → nachher. Umfang: `tests\referenz` (alle zehn Referenzen inklusive Motorhalter), die
Live-Tests der Kaufteile (`test_live_kaufteile`, `test_live_kaufteil_hole`, `test_live_motorhalter`) und die übrige
Live-Suite. Erwartet alle OK; Soll Unit-Suite **918 passed, 141 deselected**.

- [ ] **Step 4: Abnahme mit echter Herstellerdatei**

Den Nutzer um eine STEP-Datei eines realen Kaufteils seiner Wahl bitten (z. B. Motor oder Lager), dazu das Datenblatt, falls
vorhanden. Ablauf nach Skill `kaufteile` (untersuchen, Belege, Eintrag, Nutzerfreigabe, muster, Prüfer, urteil, hole). Der
Eintrag bleibt lokal (nicht committen), außer der Nutzer will ihn im Repo; Datei nie ins Git. Diagnose-Kennzahlen (Dateigröße,
Flächen, Körper, Importzeit, Speicherspitze), Befunde und Zeiten in die Ergebnisse.

- [ ] **Step 5: Ergebnisse und Spec-Nachzug**

`docs/stufe3c/ergebnisse.md` nach dem Muster `docs/stufe4b/ergebnisse.md`: Kurzfassung, Spike S15 je Zeile (Ergebnis,
Ruling, wenn falsch), Muster-Eintrag (Freigabe, Prüfer), Referenz Motorhalter (Dauer, Spitze, Prüfer), Negativfälle,
Abnahme mit echter Datei, Regression, Testzahlen je Task, Abweichungen von der Spec (Präzisierungen und Rulings), offene
Punkte. Die Spec an den Stellen nachziehen, an denen Rulings sie ändern („*Nachgezogen bei der Umsetzung*“).

- [ ] **Step 6: Commit**

```powershell
git add .claude/skills/kaufteile .claude/skills/baugruppe/SKILL.md .claude/skills/normteile/SKILL.md .claude/agents/pruefer.md CLAUDE.md docs/superpowers/specs/2026-09-26-solidworks-ki-design.md docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md docs/stufe3c/ergebnisse.md
git commit -m "docs: Stufe 3c – Skill kaufteile, Prüfer, CLAUDE.md, Design, Ergebnisse (Task 11)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Danach Gesamt-Review (stärkstes Modell), eine Fix-Welle, Abschluss per `superpowers:finishing-a-development-branch`.

---

## Abdeckung (Selbstprüfung gegen die Spec 3c)

| Spec | Task |
|---|---|
| §2 Formate nur STEP (`KAUFTEIL_FORMAT`), ein Teil je STEP, Mehrkörper | 5 (`importiere`, Strukturabbildung), 6 (`pruefe_format`) |
| §2/§3 Herkunft, Quellordner, nur lesen, nie überschreiben, `--neue-version` | 6 (`quelle`), Unit-Tests |
| §3 `kaufteilbibliothek` in `config/rechner.yaml`, `einrichten` | 3 |
| §4.1–§4.4 Eintrag, Einbaureferenzen, Gewindegruppen, `pruefung` | 3 (Schema, Plausibilität), 4 (Ortung, Bewertung) |
| §4.5 Validieren: Belege, Schutzregel, Hinweise | 3 |
| §4.6 Freigabe des ganzen Eintrags | 3 (`pruefsumme`), 7 (Nutzer-OK) |
| §5.1 `untersuchen` (Diagnose, Gerüst, Kopie) | 4 (`diagnose`), 5 (`aufnahme.untersuche`), 6 (`befehle.untersuchen`), 7 |
| §5.2 Belege, Prüfer je Eintragsversion | 6 (`muster`, `urteil`), 7, 11 (Skill) |
| §5.3 `hole`, Cache, `liste` | 6, 7 |
| §6.1 Import mit Optionen, kein Interconnect, Diagnose ohne Reparatur | 2, 5 |
| §6.2 Bezugsgeometrie an Importflächen | 2, 5 |
| §6.3 Prüfung (alle IDs), Masse | 4, 5 |
| §6.4 Gewindepaarung mit Kaufteilen | 9 |
| §7 neue Herstellerversion, Cache-SHA der .sldprt | 6 |
| §8.1–§8.4 Baugruppe (Format, Validieren, Freigabe, Bau, Prüfen, Bericht) | 8, 9 |
| §9 Prüfer-Checkliste | 11 |
| §10 Fehlerfälle | 3, 5, 6, 8 |
| §11 Referenz Motorhalter, Muster-Motor, Negativfälle, Abnahme | 1, 2, 5, 7, 10, 11 |
| §12 Spike S15 a–h | 2 |
| §13 Tests | 1, 3–10 |
| §14 Einbindung | 11 |
| §15 Fertig, wenn | 7, 10, 11 |

