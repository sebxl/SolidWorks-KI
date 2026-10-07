# Stufe 3c – Ergebnisse (Kaufteile, STEP-Import)

Fertig-Kriterium Spec 3c §15 für Rechner A (SW 2025): Das Kaufteil **Nanotec GPLE60-2S-32** (echte Herstellerdatei, Datenblatt
mit Seitenangaben) ist aufgenommen (Nutzerfreigabe, Prüfer-Urteil „bestanden“ im dritten Durchgang, `hole` mit Cache) und die
Referenz *Motorhalter* besteht mit Code-Prüfungen ohne Mangel und Prüfer-Urteil „bestanden“ (Abschnitt 5). Der Negativfall
„zu lange Flanschschraube“ liefert genau die erwartete Mängelmenge (Abschnitt 6). Die Aufnahme des GPLE60 gilt nach
Nutzerentscheidung als Abnahme mit echter Herstellerdatei (Abschnitt 7). Regression: **141 von 141 Live-Tests OK** (Nr. 0–140,
darunter alle zehn Referenzen; Abschnitt 8). Unit-Tests 847 → **960 bestanden** (937 vor der Fix-Welle), abgewählt (Live,
`sw`-markiert) 133 → **141**. Gesamt-Review (Verdict „With fixes“) und Fix-Welle: Abschnitt 9. Rechner B (SW 2026) ist nicht
Gegenstand von 3c.

## 1. Kurzfassung

Was 3c kann:

- **Katalogeintrag `art: kaufteil`** (`swki/wissen/kaufteile/<hersteller>/<bestellnummer>.yaml`, Schema
  `schema/kaufteil.schema.json`): Kennmaße mit Beleg (Belegregel: Hersteller, Datenblatt oder Nutzer allein, Händler nur mit
  mindestens zwei Domains), Schutzregel gegen genormte Teile (`KAUFTEIL_GENORMT`), Einbaureferenzen `EINBAU_*`
  (`zylinder`, `ebene`, `ebene_durch_achse`), Gewindegruppen, Prüfung (Hüllquader, Volumen, Durchmesser, Maße); Freigabe über
  `swki freigeben` (Prüfsumme über den ganzen Eintrag); Prüfer-Urteil `<eintrag>.pruefer.json` gebunden an die Freigabe.
- **Befehle `swki kaufteil untersuchen | muster | urteil | hole | liste`:** STEP-Import als Mehrkörperteil (Strukturabbildung 2,
  3D Interconnect und Importdiagnose nur für den Import aus, Optionen werden zurückgestellt), Diagnose nur lesend
  (`Check3`, Flächenkörper; nie `ImportDiagnosis`), Bezugsachsen und -ebenen an den Importflächen, Massenüberschreibung aus dem
  Datenblatt, Cache je SW-Jahr in der `kaufteilbibliothek` (Quellordner nur Kopien; SHA-256 des Originals vor dem Import).
- **Gewindegruppen:** Gegenprobe im Ø-Bereich D1 (ISO 724) bis Tabellen-Kernloch (Modell `kernloch`) oder Nenn-Ø (Modell
  `nenn`); der gemessene Ø steht im Cache und rechnet die Gewindepaarung (Task G, Befund G1).
- **Baugruppen:** Komponentenquelle `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}`, Referenzen `EINBAU_*` und
  Gewindepositionen (`je_position`), Gewindepaarung im Kaufteil, Freigabe der Baugruppe schützt den Eintrag mit
  (`FREIGABE_VERALTET` nennt das Kaufteil), Bericht mit Abschnitt „Kaufteile“ (Spalte „Gewindemodell (Ø mm)“).
- **Flächenmodelle ohne Absturz:** reine Flächenmodelle ergeben den Mangel `import` statt eines `AttributeError` (Fix-N).
- **Prüfbericht** nennt die gelesenen Eigenschaften (Fix-E) und die Diagnose-Kennzahlen (Dateigröße, Flächen, Importzeit,
  Speicherspitze); Durchmesserprüfung findet auch die Senkung einer Bohrung (10N-1/10N-2).
- Skill `kaufteile`, Prüfer-Checkliste Kaufteil (`.claude/agents/pruefer.md`), Skill `baugruppe` §8, CLAUDE.md, Design,
  Referenz `tests/referenz/motorhalter/` (Grundplatte, Motorbock, Motorhalter mit Nanotec GPLE60-2S-32).

Testzahlen: Unit-Tests 847 → **937 bestanden** (+90), abgewählt 133 → **141** (+8: fünf Live-Tests der Aufnahme in Task 5, je ein
Test `hole` und Motorhalter-Negativfall und ein Referenzeintrag; Aufschlüsselung in Abschnitt 10). `swki api pruefe-code`: keine
Befunde. Zuwachs je Task: Abschnitt 10.

## 2. Nutzerentscheidungen 2026-10-06/07

Alle aus dem Ledger (`.superpowers/sdd/2026-10-06-kaufteile-step-import/progress.md`, nicht versioniert); sie standen vor dem
jeweiligen Task fest.

| Nr. | Entscheidung | Folge |
|---|---|---|
| 1 | **Muster-Eintrag nicht freigegeben** („Besorg eine echte stp Datei von einem Hersteller mit Datenblatt“), 2026-10-06, Task 7 gestoppt | Muster-Getriebemotor wird kein Katalogeintrag; nicht freigegebener Eintrag, Quellkopie und Laufordner gelöscht (Ruling N2); Specs, `gm42-10.step` und `.gitattributes` bleiben als interne Testdatei (Ruling N1); Tasks 7, 10, 11 neu geplant (Plan-Nachtrag) |
| 2 | **Downloads nur mit OK je Datei:** öffentliche Direktlinks, kein Konto, Name, Quelle und Größe vorher nennen (zuerst für ST4118M1804-A, dann für weitere Kandidaten bis zu 2 MB, dann GPLE60) | als Regel in Skill `kaufteile` und CLAUDE.md |
| 3 | **Herstellerdateien (STEP, Datenblatt) nicht ins Git;** der Eintrag nennt `original.bezug: {art: url, url, datum}` plus SHA-256; die Regression nimmt die Kopie aus dem Quellordner, sonst `KAUFTEIL_QUELLE_FEHLT` mit Download-URL | CLAUDE.md-Ausnahme nur für die Test-STEP `tests/referenz/motorhalter/muster/gm42-10.step`; Task G (URL in der Meldung) |
| 4 | **Nanotec GPLE60-2S-32** (Planetengetriebe) ersetzt das Muster als Katalogeintrag (Task 7N) und in der Referenz Motorhalter (Task 10N) | Abschnitte 4 und 5 |
| 5 | **Gewinde-Ø-Bereich (Befund G1):** Modell `kernloch` für jeden Ø von D1 (ISO 724: D − 1,0825·P) bis Tabellen-Kernloch, je ± 0,01 mm; gemessener Ø in den Cache; Gewindepaarung rechnet mit dem gemessenen Ø; Nenn-Ø bleibt `nenn`; Spec §4.3/§6.4 nachziehen | Task G (`df87806`), `IMPORTWEG_VERSION` 2 |
| 6 | **Abnahme = GPLE60:** die Aufnahme gilt als Abnahme mit echter Herstellerdatei (zusätzlich das Flächenmodell ST4118M1804-A als dokumentierter Fehlschlag) | Abschnitt 7 |
| 7 | **Drehlage `EINBAU_DREHLAGE` des GPLE60** als Symmetrieebene des Lochbilds (Mitte einer □-60-Seite), nicht durch eine Gewindeposition (Präzisierung 26); mit der Freigabe 7N entschieden | nur so passen „parallel zu `vorne`“ und aufrecht stehendes Getriebe zusammen |
| 8 | **Zylinder-Achsrichtung ist kein Prüferkriterium** (Spec §4.2: Zylinderachse ohne Orientierungsforderung; `konzentrisch` nutzt die nächste Ausrichtung; die Normale einer `ebene_durch_achse` ebenfalls nicht; Orientierung nur für Ebenennormalen, `bezug.richtung`) | Prüfer-Checkliste Punkt 1 präzisiert; Prüfer 3 bestand (Abschnitt 4.3) |
| 9 | **Prüfbericht zeigt die gelesenen Eigenschaften** unter `ist` (nicht nur Abweichungen) | Fix-E (`ebdd960`) |
| 10 | **Freigaben:** Eintrag GPLE60 (einschließlich Drehlage), Referenz Motorhalter im Auftrag `REF-3C-MOTORHALTER` (jeweils ausdrückliches OK vor `swki freigeben`) | Prüfsumme Eintrag `a696adb0…6c7f` |
| 11 | **Weitere Herstellerdateien probeweise laden,** bis ein Volumenmodell vorliegt (je < 2 MB, Direktlinks, ohne Konto) | führte zu DB42 und GPLE60 (Abschnitt 3) |
| 12 | 2026-10-07 00:21: nach Abschluss der laufenden Aufgaben stoppen; Regression bei 77/141 abgebrochen | Abschnitt 8, Fortsetzung am 2026-10-07 |

## 3. Verworfene Kandidaten

- **Nanotec ST4118M1804-A** (Schrittmotor NEMA 17; `ST4118M1804-A.stp` 325 237 Byte, SHA-256 `d0b04c5f…c74f`; PDF 90 049 Byte;
  Download mit Nutzer-OK). Die STEP enthält keinen einzigen Volumenkörper (0 × `MANIFOLD_SOLID_BREP`, 9 ×
  `SHELL_BASED_SURFACE_MODEL` auf `OPEN_SHELL`, 157 `ADVANCED_FACE`). SolidWorks importiert 8 Flächenkörper, 0 Volumenkörper;
  `CreateMassProperty2` liefert dann `None` und `diagnose` stürzte mit `AttributeError: 'NoneType' … UseSystemUnits` ab, statt
  den Mangel `import` zu melden (Ursachenanalyse `diag-nanotec-report.md`). **Fix-N** (`4d41434`): Masseneigenschaften
  `None`-sicher, `untersuchen` meldet Flächenkörper (`koerper` 0, `flaechenkoerper` 8, Exit 0, Spitze 3965 MB), `baue_und_pruefe`
  → Mangel `import`; `koerperfehler` prüft zusätzlich Flächenkörper (`Check3`, Schlüssel `F1` …); +4 Unit-Tests. Ruling N5/N6:
  als Kaufteil unbrauchbar (Spec: nicht reparieren, anderes Modell beim Hersteller). Dateien und Quellkopien danach gelöscht.
- **Nanotec DB42Sxx** (`DB42Sxx.stp`, 9 Volumenkörper, Inventor 2021; `DB42S03.pdf`): Volumenmodell, aber **M3**-Flanschgewinde
  (NEMA 17); M3 fehlt in `swki/wissen/bohrungsnormen.yaml` (Gewinde, Zylinderschraube) und in `swki/wissen/normteile/iso4762.yaml`
  (Tabelle beginnt bei M5). Nur mit M3-Tabellenerweiterung nutzbar (Erweiterung nur mit Abgleich und Live-Messung, CLAUDE.md);
  verworfen, Dateien gelöscht. **Offener Punkt** (Abschnitt 11).
- Der Muster-Getriebemotor GM42-10 (fiktiv) bleibt nur als interne Testdatei (Abschnitt 2, Nr. 1).

## 4. Katalogeintrag Nanotec GPLE60-2S-32 (Task 7N)

### 4.1 Quelle und Diagnose

Herstellerquelle (Download 2026-10-06 mit Nutzer-OK): `…/Datenblaetter/Getriebe/Planetengetriebe_GPLE60/GPLE60-2S.stp`
(85 716 Byte, 3 × `MANIFOLD_SOLID_BREP`, Inventor 2016) und Baureihenübersicht `Product_Overview_GPLE60.pdf` (157 478 Byte,
Seiten 248/249); beide liegen nur im Quellordner `quellen/nanotec/` der `kaufteilbibliothek`, nicht im Git. Eintrag:
`swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml` mit `freigabe.json`, `gple60-2s-32.freigegeben.yaml` und
`gple60-2s-32.pruefer.json`.

Diagnose `swki kaufteil untersuchen` (lauf-1, `gple60-untersuchen.json`):

| Kennzahl | Wert |
|---|---|
| Dateigröße | 0,082 MB |
| Körper | 3 Volumenkörper, 0 Flächenkörper, `Check3` 0/0/0 |
| Flächen | 55 (20 Zylindergruppen, 19 Ebenengruppen) |
| Importzeit | 5,278 s (erster Import nach SolidWorks-Neustart) |
| Dauer gesamt | 12,801 s |
| Private Bytes (vorher → Spitze → nachher) | 424,9 → 3239,6 → 940,2 MB |
| Volumen | 258 960,557 mm³ |
| SHA-256 Original | `b240fd16…6aea` |
| Hüllquader | x 0…60, y 0…60, z −94,5…24 (mm) |
| Optionen vorher | 3D Interconnect an, Importdiagnose an, Strukturabbildung 0 (nachher unverändert) |

Geometrie aus der Diagnose: Achse bei (30, 30) parallel z. Abtriebsflansch z = −59,5 (Normale −z), Zentrierbund Ø 40 (z −59,5 …
−62,5), Absatz Ø 17 bis −64,5, Welle Ø 14 bis −94,5 (35 ab Flansch), Passfedernut b 5, Grund x = 21 (t 16), Länge 25 (z −67 … −92);
4 Gewindelöcher Ø 4,134 (= D1 nach ISO 724 für M5, nicht Bohrer 4,2) auf Lochkreis Ø 52 unter 45°. Antriebsseite: Quadrat 60
(z 0 … 24), Ø 38,1, Ø 6,35, 4 × Ø 3,242 auf □ 47,14.

Der Eintrag nennt `material: "1.0503"` (Hersteller ohne Angabe, Welle/Verzahnung Stahl angenommen) und `masse` 1,1 kg aus dem
Datenblatt (überschreibt die Masse aus dem Material). Die **Gewindetiefe** 10 nennt das Datenblatt nicht; sie stammt aus der
Mantellänge des Gewindezylinders in der STEP (Hinweis `nicht_belegt gewinde.flansch`). Step 1 der Aufnahme belegte Mantel
z −59,5 … −49,5 (viermal) und einen Kegelboden bei z = −48,879 (Kegelspitze, keine ebene Fläche); die Brief-Erwartung (≈ −50,1)
war ein Vorzeichenfehler (Ruling 7N-1: das Loch geht in +z; Tiefe 10 und Boden ohne Ebene bestätigt, keine Eintragsänderung).

### 4.2 Freigabe und Gewindemodell

`swki validieren`: gültig, Prüfsumme `a696adb08133ba2507dae5b38699365d62c8c07c478892cf683a6084366c6c7f`, ein Hinweis
(`nicht_belegt` für `gewinde.flansch`), keine Befunde. Nutzerfreigabe (einschließlich Drehlage als Symmetrieebene) → `swki
freigeben`. Das Gewindemodell der Aufnahme ist `kernloch` mit gemessenem **Ø 4,134** an allen vier Positionen (Task G).

### 4.3 Drei Prüferdurchgänge

| Durchgang | Lauf | Urteil | Befund | Behandlung |
|---|---|---|---|---|
| 1 | `muster` lauf-2 (bestanden, 0 Mängel), Checkliste Fassung 11N | bestanden **false** | Mangel `eigenschaften`: der Prüfbericht zeigte `ok: true` mit `ist: {}` (die Bewertung listete unter `ist` nur Abweichungen, wie die Teil-Bewertung); die Eigenschaften waren im Teil korrekt gesetzt | Nutzerentscheidung: Bericht korrigieren. **Fix-E** (`ebdd960`, 932/138, +2 Tests): unter `ist` stehen die gelesenen Werte aller Soll-Eigenschaften, bei Abweichung ein Feld `hinweis` („abweichend: <Schlüssel> ist … statt …“). Eintrag und Freigabe unverändert; neues Musterteil |
| 2 | `muster` lauf-3 (SolidWorks frisch, bestanden, 0 Mängel) | bestanden **false** | Mangel `einbau:EINBAU_ACHSE`: Achsrichtung +z statt Abtriebsrichtung −z | Nutzerentscheidung: kein Mangel (Spec §4.2: SolidWorks legt die Richtung einer Zylinder-Bezugsachse fest, Gegenprobe ist Lage und Ø); Checkliste präzisiert (Orientierung nur für Ebenennormalen, `bezug.richtung`; `konzentrisch` nutzt die nächste Ausrichtung). Kein Code, Eintrag unverändert |
| 3 | dasselbe Musterteil, präzisierte Checkliste | **bestanden, 0 Mängel** | – | `swki kaufteil urteil` legte `gple60-2s-32.pruefer.json` ab |

`bezug.richtung` im Muster-Lauf: `EINBAU_ACHSE` [0, 0, +1], `EINBAU_FLANSCH` [0, 0, −1].

### 4.4 `hole` und Cache

Live-Test `tests/live/test_live_kaufteil_hole.py`: OK (Private Bytes 431 → 1989 MB). Echter Cache: `swki kaufteil hole` →
`gebaut: true`, `gewinde_modell {flansch: kernloch, 4.134}`, Cache-Prüfsumme `794ff907d99b034ee30557f5343d32c5df63608d9e2daf6c51e6cf59c22caa3e`,
lauf-5, 23 Prüfungen bestanden; zweiter Aufruf `gebaut: false` (Cache-Treffer). `kaufteil liste`: freigegeben, geprüft,
Cache vorhanden. Private Bytes danach 2453 MB, 0 Dokumente. Regression Nr. 40: 10,3 s, Spitze 3633 MB.

## 5. Referenz Motorhalter (Task 10N)

`tests/referenz/motorhalter/`: Grundplatte (160 × 100 × 12 mit 2 × M6), Motorbock (Fuß und Wand, Zentrierbohrung Ø 40 × 5 als
Senkung einer Bohrung Ø 20 durch, 4 × M5 Senkung, 2 × M6 Senkung), `motorhalter.yaml` (Grundplatte fixiert, Motorbock, Kaufteil
Nanotec GPLE60-2S-32, 4 × ISO 4762 M5 × 12 durch die Wand in die Flanschgewinde, 2 × M6 × 10 im Fuß; Achshöhe 62, Hüllquader
[160, 102, 100], Drehlage `parallel` zu `vorne` des Bocks), `eingabe/beschreibung.md`. Statisch.

**Step 5 (live) in drei Läufen** (`test_referenz_besteht[motorhalter-motorhalter.yaml]`, jeweils SolidWorks frisch):

| Lauf | Ergebnis | Dauer | Private Bytes vorher → Spitze → nachher (MB) | Ursache |
|---|---|---|---|---|
| 1 | 1 Mangel `bock: durchmesser:Zentrierbohrung` (`REFERENZ_NICHT_GEFUNDEN`, keine Zylinderfläche durch (7,5; 70; 0)) | 161 s | 431,8 → 9289 → 3734,5 | **10N-1:** `messen.durchmesser` suchte nur in `features[0]` (Durchgang Ø 20); der Ø 40 ist das zweite Feature `f3_senkung` des Handlers `bohrung`. Fix `0802a4b` (alle Features des Ergebnisses, +2 Tests) |
| 2 | derselbe Mangel | 117 s | 426,2 → 9076,7 → 3558,7 | **10N-2:** `kontext_aus_datei` legt je Spec-Feature nur `FeatureByName(<id>)` ab, `<id>_senkung` fehlte im Kontext. Fix `87b18cc` (bei `bohrung` mit `senkung` zweites Feature, +1 Test) |
| 3 | **bestanden**, `maengel: []`, Ø 40 ist 40,0 (soll 40,0, tol 0,01) | 116,5 s | 425,3 → 9050,9 → 3521,3 | – |

Einzelwerte (Lauf 3): Flanschschrauben 1–4 Einschraublänge 7,4, ist = soll 42,305, Gewindetiefe 10, Tiefe 10; Fußschrauben
1–2 Einschraublänge 6,4, 48,747, Gewindetiefe 8,0, Tiefe 10,0; `kollision: []`; Kaufteil `Nanotec_GPLE60-2S-32` gebaut false (Cache),
`gewinde_modell {flansch: {modell kernloch, durchmesser 4.134}}`, Masse 1,1 kg (Datenblatt), Kennmaße belegt; Hüllquader
[160, 102, 100]; Achshöhe 62,0; Flansch an der Wand 0,0; Verknüpfungen 18/18; Bestimmtheit ok; Gesamtmasse 3,2559 kg; Teilprüfungen
`grundplatte` und `bock` bestanden. Verknüpfungen `v4` (`entgegengesetzt`), `v5` (ohne `ausrichtung`) und `v6` liefen ohne
Nachbesserung (Spike S15-7: Flanschnormale −z wie erwartet).

**Prüferlauf** im Auftrag `REF-3C-MOTORHALTER` (nach Nutzer-OK `validieren` → `freigeben` → `bauen` → `pruefen`, SolidWorks frisch):
bauen 97,4 s laut `swki status`, Prüfbericht bestanden, `maengel: []`, Masse 3,2559 kg; **Prüfer-Urteil `bestanden`, 0 Mängel**.
Spitze dieses Laufs: nicht gemessen. Auftrag und Arbeitsordner danach gelöscht.

Speicher: Spitzen Motorhalter 9,05–9,3 GB (9289, 9077, 9051 MB in Step 5; 9059 MB in der Regression Nr. 9; Negativfall 9238 und
9110 MB), also über `speicher_grenze_mb` 10000 nicht erreicht, aber nahe an den 9,8–11,2 GB der anderen Baugruppen.

## 6. Negativfälle

**Live** (je einzeln auf frischem SolidWorks):

| Fall | Erwartete Mängelmenge (= gemessen) | Dauer | Spitze Private Bytes |
|---|---|---|---|
| `test_live_motorhalter.py::test_zu_lange_flanschschraube` (M5 × 16, Einschraublänge 11,4 > Gewindetiefe 10 = Bohrtiefe 10) | genau `gewinde:flanschschraube.1-4` (Einschraublänge 11,40 > Gewindetiefe 10) | 137,4 s (Step 7); Regression Nr. 62: 115,6 s | 9238 MB (Step 7); 9110 MB (Regression) |
| `test_live_kaufteile.py::test_negativfaelle[durchmesser]` (falscher Ø in der Gegenprobe von `EINBAU_ACHSE`, Testeintrag Muster) | genau `{einbau:EINBAU_ACHSE}` | 8,8 s (Regression Nr. 44) | 3628 MB |
| `test_live_kaufteile.py::test_negativfaelle[koerper]` (Körperzahl 1 statt 2) | genau `{koerper}` | 9,1 s (Regression Nr. 45) | 3671 MB |

Außerdem live nachgewiesen: Flächenmodell ST4118M1804-A (Fix-N) über `untersuchen` an der Nanotec-Kopie: `koerper 0`,
`flaechenkoerper 8`, Exit 0 (der Mangel `import` in `baue_und_pruefe` ist nur per Unit-Test mit Attrappe belegt).

**Unit (ohne SolidWorks):** Original geändert (`KAUFTEIL_QUELLE_ABWEICHEND`, SHA-256-Prüfung vor dem Import);
`KAUFTEIL_QUELLE_FEHLT` mit Download-URL und Datum; Eintrag nach der Baugruppen-Freigabe geändert (`FREIGABE_VERALTET` mit
Kaufteil); Schutzregel (`KAUFTEIL_GENORMT`); Belegregel (`BELEG_UNZUREICHEND`); `KAUFTEIL_UNGEPRUEFT` vor dem Cache-Treffer
(Ruling B5); `KAUFTEIL_UNBEKANNT`, `KAUFTEIL_NICHT_FREIGEGEBEN`; Gewinde-Ø im Bereich, am Rand, Nenn-Ø und uneinheitliche
Gruppen (Task G); Gewindepaarung `kernloch`/`nenn`/unbekannt; `drehlage_doppelt` nur bei Einbaureferenzen, nicht bei
Gewindepositionen (Ruling T8-1); Flächenmodell → Mangel `import` (Fix-N); Eigenschaften im Prüfbericht (Fix-E).

## 7. Abnahme mit echter Herstellerdatei

Nutzerentscheidung (Abschnitt 2, Nr. 6): Die Aufnahme des Nanotec GPLE60-2S-32 erfüllt die Abnahme nach Spec §11/§15. Voller
Ablauf: untersuchen → Belege aus dem Datenblatt → Eintrag → validieren → Nutzerfreigabe → freigeben → muster → Prüfer (drei
Durchgänge) → urteil → hole. Kennzahlen: Abschnitt 4.1 (0,082 MB, 55 Flächen, 3 Körper, Import 5,3 s, Dauer 12,8 s, Private
Bytes 425 → 3240 → 940 MB). Zeit je Fläche: der erste Import nach SolidWorks-Neustart dauerte beim Muster 4,9 s (23 Flächen) und beim
GPLE60 5,3 s (55 Flächen); warm waren es beim Muster 0,75–0,78 s (Task 5), im Spike 1,19 s. Die Zeit wird also von der
Erstladung des STEP-Übersetzers bestimmt, nicht von der Flächenzahl; das größere Modell (Spec S15g) ist mit 55 Flächen klein,
Zeit je 1000 Flächen deshalb nur aus dem Spike (0,0297 s je Fläche, ≈ 30 s).

Befunde der Abnahme: G1 (Gewinde-Ø D1 statt Bohrer, Abschnitt 11 und 12), Gewindetiefe nicht im Datenblatt (aus der STEP, nicht
belegt), Kegelboden der Gewindelöcher, Flächenmodell des ersten Kandidaten (Fix-N), M3-Lücke beim zweiten (Abschnitt 3), zwei
Prüferbefunde (Abschnitt 4.3), zwei Messcode-Lücken im Motorhalter (Abschnitt 5). Zoll-STEP: nicht getestet (Abschnitt 13).

## 8. Regression (Task 11N Step 4)

Je Test einzeln (Controller-Skript `regression.py`: `pytest -m sw <Test-ID>`), SolidWorks vor Kaufteil- und
Baugruppen-Tests frisch, sonst Neustart ab 3000 MB Private Bytes; Private Bytes von `SLDWORKS.exe` vorher → Spitze (Abtastung
alle 0,5 s) → nachher. Rohdaten: `.superpowers/sdd/2026-10-06-kaufteile-step-import/regression.jsonl` (nicht versioniert).
Code-Stand: `a7f61b5`. Die Live-Suite hat 141 Tests; der Lauf wurde am 2026-10-07 um 00:56 nach Nutzerwunsch bei 77/141
unterbrochen („Schluss für heute“) und am 2026-10-07 ab 19:05 fortgesetzt und zu Ende geführt (8.2).

### 8.1 Nr. 0–76 (77 Tests)

Ergebnis: **77 von 77 OK**; Summe der Testzeiten 2995 s (≈ 50 min), größte Spitze **11 240 MB** (Stehlager).

Referenzen (alle zehn):

| Nr. | Test | Dauer | Private Bytes Spitze (MB) | vorher → nachher (MB) |
|---|---|---|---|---|
| 0 | Buchse | 29,9 s | 3467 | 415,9 → 1019,7 |
| 1 | Formplatte | 43,2 s | 3602 | 1019,7 → 1237,2 |
| 2 | Auswerferhalteplatte | 73,1 s | 3829 | 1237,2 → 1469,0 |
| 3 | Stehlager | 193,5 s | 11 240 | 414,2 → 4261,4 |
| 4 | Linearschlitten | 250,5 s | 9928 | 413,5 → 4502,8 |
| 5 | Zahnstange | 35,8 s | 3397 | 417,0 → 1066,6 |
| 6 | Ritzelwelle | 65,7 s | 4166 | 1066,6 → 2426,6 |
| 7 | Antriebswelle | 58,5 s | 4522 | 2426,6 → 2743,0 |
| 8 | Zahnstangentrieb | 479,9 s | 10 271 | 415,2 → 4618,6 |
| 9 | **Motorhalter** (Nanotec GPLE60-2S-32) | 115,7 s | 9059 | 415,6 → 3536,8 |

Übrige Tests (alle OK, nach Dateien gruppiert):

| Nr. | Datei | Tests | Dauer je Test | Spitze (MB) |
|---|---|---|---|---|
| 10–11 | `test_live_aenderungen` | 2 | 17,1–27,3 s | 3435–3580 |
| 12–13 | `test_live_api` | 2 | 0,4 s | 1385 |
| 14–16 | `test_live_bauen` | 3 | 0,6–16,7 s | 1385–3848 |
| 17–23 | `test_live_baugruppe` | 7 | 33,2–65,8 s | 3733–7001 |
| 24–25 | `test_live_bewegung` | 2 | 48,9 s, 116,1 s | 5579, 7598 |
| 26 | `test_live_durchmesser` | 1 | 8,7 s | 5476 |
| 27–30 | `test_live_endbedingungen` | 4 | 7,4–11,6 s | 3093–5270 |
| 31–36 | `test_live_extrusion` | 6 | 3,7–8,3 s | 3473–4415 |
| 37–39 | `test_live_kanten` | 3 | 6,5–9,7 s | 3124–4204 |
| 40 | `test_live_kaufteil_hole` (GPLE60) | 1 | 10,3 s | 3633 |
| 41–45 | `test_live_kaufteile` (Muster: Import, untersuchen, baue_und_pruefe, 2 Negativfälle) | 5 | 6,1–19,5 s | 3092–4087 |
| 46–59 | `test_live_konturen` | 14 | 4,6–14,1 s | 3093–4154 |
| 60–61 | `test_live_kopplung` (Getriebeprobe bauen, prüfen) | 2 | 197,9 s, 300,4 s | 4985, 6775 |
| 62 | `test_live_motorhalter` (Negativfall) | 1 | 115,6 s | 9110 |
| 63–65 | `test_live_muster` | 3 | 7,1–12,9 s | 3082–3337 |
| 66–71 | `test_live_normbohrung` | 6 | 8,1–9,7 s | 3463–3975 |
| 72–75 | `test_live_normteil_hole` | 4 | 12,4–22,2 s | 3460–4566 |
| 76 | `test_live_normteile` (erster Test, M5 × 8) | 1 | 22,8 s | 3756 |

Hinweise:

- **Formplatte** (Ruling 10N-2: Bohrung mit Senkung hat jetzt zwei Features im Kontext): Nr. 1 OK, 43,2 s; das Risiko hat sich nicht
  gezeigt (Review: keine `durchmesser_pruefen` auf `f7`).
- **Speicher:** Spitzen Stehlager 11,2 GB, Zahnstangentrieb 10,3 GB, Schlitten 9,9 GB, Motorhalter 9,1 GB; kein `SPEICHER_KNAPP`,
  kein Absturz.
- **Nanotec-Herstellerdatei** lag im Quellordner; `KAUFTEIL_QUELLE_FEHLT` trat nicht auf.

### 8.2 Regression ab Nr. 77

Ergebnis: **64 von 64 OK** (Nr. 77–140, Summe 4903 s ≈ 82 min); gesamt mit 8.1 **141 von 141 OK**, Summe der Testzeiten ≈ 132 min,
größte Spitze **11 240 MB** (Stehlager, Nr. 3). Größte Spitze ab Nr. 77: 11 156 MB (Stehlager `test_ueberlappung`). Die
Zahnstangentrieb-Negativfälle (Nr. 137–140) brauchten 446–576 s bei Spitzen um 10,3 GB; kein `SPEICHER_KNAPP`, kein Absturz.
Code-Stand wie in 8.1: `a7f61b5` (die Fix-Welle aus Abschnitt 9 ist danach entstanden und wurde nicht erneut komplett
gegen die Live-Suite gefahren, siehe Abschnitt 9).

| Nr. | Test | Dauer (s) | Spitze (MB) |
|---|---|---|---|
| 77 | `test_live_normteile.py::test_iso4762[M10-40]` | 26,1 | 2 643 |
| 78 | `test_live_normteile.py::test_iso4762[M16-160]` | 22,7 | 2 942 |
| 79 | `test_live_normteile.py::test_iso4032[M5]` | 19,8 | 2 780 |
| 80 | `test_live_normteile.py::test_iso4032[M10]` | 19,3 | 2 848 |
| 81 | `test_live_normteile.py::test_iso4032[M16]` | 19,7 | 2 918 |
| 82 | `test_live_normteile.py::test_verfaelschte_vorlage_scheitert` | 24,0 | 3 004 |
| 83 | `test_live_normteile.py::test_iso7089[M5]` | 10,3 | 3 062 |
| 84 | `test_live_normteile.py::test_iso7089[M10]` | 10,4 | 3 130 |
| 85 | `test_live_normteile.py::test_iso7089[M16]` | 10,9 | 3 190 |
| 86 | `test_live_normteile.py::test_iso8734[4-8]` | 12,1 | 3 256 |
| 87 | `test_live_normteile.py::test_iso8734[8-30]` | 12,3 | 3 310 |
| 88 | `test_live_normteile.py::test_iso8734[12-100]` | 12,1 | 3 382 |
| 89 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M8x30-10.9]` | 22,5 | 3 453 |
| 90 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M16x45-A2-70]` | 23,1 | 3 763 |
| 91 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M12x110-12.9]` | 23,1 | 3 752 |
| 92 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M6x16-12.9]` | 23,1 | 3 655 |
| 93 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M10x50-10.9]` | 24,3 | 3 723 |
| 94 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 8734-10x70-St]` | 12,0 | 3 786 |
| 95 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M16x55-10.9]` | 23,0 | 3 859 |
| 96 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M12x45-12.9]` | 28,6 | 3 467 |
| 97 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M16x70-8.8]` | 24,3 | 3 661 |
| 98 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M16x40-10.9]` | 23,6 | 3 839 |
| 99 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M5x25-10.9]` | 24,0 | 4 020 |
| 100 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M16x55-12.9]` | 23,6 | 4 195 |
| 101 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4032-M10-8]` | 20,7 | 4 373 |
| 102 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 8734-10x50-St]` | 13,4 | 4 485 |
| 103 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 8734-6x70-St]` | 17,2 | 3 463 |
| 104 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M12x45-8.8]` | 20,4 | 3 588 |
| 105 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M8x45-8.8]` | 22,4 | 3 791 |
| 106 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M12x120-12.9]` | 22,3 | 4 012 |
| 107 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M8x25-A2-70]` | 20,9 | 4 187 |
| 108 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 4762-M6x55-12.9]` | 24,0 | 4 355 |
| 109 | `test_live_normteile_stichprobe.py::test_stichprobe[ISO 7089-M16-A2]` | 10,4 | 4 534 |
| 110 | `test_live_parametrik.py::test_masse_folgen_parametern` | 17,0 | 3 555 |
| 111 | `test_live_pruefen.py::test_pruefen_bestanden_und_status` | 24,2 | 3 602 |
| 112 | `test_live_pruefen.py::test_pruefen_findet_mangel_mit_knoten` | 15,5 | 3 818 |
| 113 | `test_live_pruefen_normbohrung.py::test_normbohrung_bestanden_mit_baum` | 15,8 | 4 008 |
| 114 | `test_live_pruefen_normbohrung.py::test_groesse_nach_freigabe_geaendert_ist_mangel` | 15,5 | 4 218 |
| 115 | `test_live_referenz.py::test_referenzen_achse_und_ebenen` | 6,9 | 4 505 |
| 116 | `test_live_rotation_bohrung.py::test_rotation_rohr_und_nut` | 14,6 | 3 094 |
| 117 | `test_live_rotation_bohrung.py::test_bohrungen_mit_senkung` | 11,2 | 3 260 |
| 118 | `test_live_rotation_bohrung.py::test_lage_haengt_an_parameter` | 8,1 | 3 392 |
| 119 | `test_live_schlitten.py::test_stellungskollision` | 289,6 | 9 753 |
| 120 | `test_live_schlitten.py::test_grenze_im_modell_zu_weit` | 230,4 | 9 419 |
| 121 | `test_live_schlitten.py::test_umgekehrte_richtung` | 272,0 | 8 338 |
| 122 | `test_live_schlitten.py::test_zweiter_freiheitsgrad` | 274,0 | 9 662 |
| 123 | `test_live_skript.py::test_notausgang_skript` | 12,0 | 3 093 |
| 124 | `test_live_skript.py::test_material_und_eigenschaften` | 5,4 | 3 264 |
| 125 | `test_live_stehlager.py::test_zu_lange_deckelschraube` | 232,7 | 10 830 |
| 126 | `test_live_stehlager.py::test_ueberlappung` | 173,7 | 11 156 |
| 127 | `test_live_stehlager.py::test_unterbestimmte_komponente` | 191,4 | 10 816 |
| 128 | `test_live_stehlager.py::test_manuelle_aenderung_in_der_baugruppe` | 178,2 | 10 822 |
| 129 | `test_live_verbindung.py::test_verbinde_mit_laufendem_solidworks` | 0,4 | 2 282 |
| 130 | `test_live_verbindung.py::test_verbindung_ist_late_bound` | 0,4 | 2 282 |
| 131 | `test_live_verzahnung.py::test_stirnrad_auf_welle` | 11,7 | 4 991 |
| 132 | `test_live_verzahnung.py::test_zahnstange_auf_ruecken` | 12,5 | 3 032 |
| 133 | `test_live_verzahnung.py::test_stirnrad_oben_mit_winkel_und_umkehren` | 17,1 | 3 591 |
| 134 | `test_live_verzahnung.py::test_messung_der_verzahnung[stirnrad]` | 22,0 | 3 732 |
| 135 | `test_live_verzahnung.py::test_messung_der_verzahnung[zahnstange]` | 12,2 | 3 501 |
| 136 | `test_live_verzahnung.py::test_negativ_zahnweite` | 75,5 | 4 429 |
| 137 | `test_live_zahnstangentrieb.py::test_zahnphase_versetzt` | 522,0 | 10 220 |
| 138 | `test_live_zahnstangentrieb.py::test_drehrichtung_umgekehrt` | 573,0 | 10 287 |
| 139 | `test_live_zahnstangentrieb.py::test_kopplung_fehlt` | 445,5 | 9 777 |
| 140 | `test_live_zahnstangentrieb.py::test_uebersetzung_verfaelscht` | 576,1 | 10 278 |

## 9. Gesamt-Review und Fix-Welle

**Gesamt-Review** (Opus, Bereich `7f120d0..a7f61b5`, d. h. `main` bis Task 11N; Bericht `gesamt-review.md` im Ledger-Ordner): Verdict
**„With fixes“** – kein Critical, drei Important, elf Minor. Stärken: saubere Schichtung (reine Module getrennt von der
SolidWorks-Schicht), Datensicherheit (Nutzerdatei nur gelesen, Kopie unveränderlich), Cache-Protokoll, Rückstellung der
Importoptionen, Freigabe mit Kaufteil-Prüfsumme, Rückwärtskompatibilität der Baugruppen ohne Kaufteile.

Fix-Welle (Ruling F1, eine Welle nach Ende der Regression; Ruling F2: `IMPORTWEG_VERSION` bleibt 2, weil der echte GPLE60-Eintrag die
Flanschebene mit `bezug.richtung` [0, 0, −1] = Soll hat und die schärfere Prüfung besteht):

| Befund | Behoben durch | Commit |
|---|---|---|
| Important 1: Orientierung der `ebene`-Bezugsebenen im Code nicht geprüft | `einbau:<name>` verlangt `bezug.richtung` gleichsinnig zur Soll-Normale (Skalarprodukt > 0); `zylinder` und `ebene_durch_achse` bleiben ohne Richtungsforderung (Nutzerentscheidung); Spec §4.2 und Skill nachgezogen | e2ace71 |
| Important 2: `gewinde_referenz` ohne Test, in Skills beworben | Attrappen-Tests (Instanz, kleinster Radius, `REFERENZ_NICHT_GEFUNDEN`), Flächenliste je Kontext einmal gesammelt (Minor 4, Teil); Vermerk „noch nicht live erprobt“ in Skill `kaufteile` §6 und `baugruppe` §8 | b729ffa |
| Important 3: Schutzregel umgehbar (`DIN 912-12`) | beide Lesarten (mit und ohne Größe) werden gegen die Normtabellen geprüft; `DIN 625` bleibt erlaubt | 6106e4c |
| Minor 1: URL ohne Schema → leere Domain | Schema `pattern: ^https?://` für alle URL-Felder | c17852c |
| Minor 2: `cache.lies` | `except (OSError, ValueError)`, Nicht-Objekt → `None` | d348dfb |
| `Spitzenmessung.__exit__` | OSError der Abschlussmessung überdeckt den Originalfehler nicht | 4ae924b |
| Minor 7: Spike überschreibt Test-STEP | nur mit `--step-neu` | 1da3b0c |
| Minor 5, 6, 11, `pruefer.md`, Codetabelle, Ergebnisse | Dokumentationscommit (Spec §4.3/§6.3, Skills `baugruppe` und `kaufteile`, `pruefer.md`, dieses Dokument) | siehe `git log` |

Unit-Suite nach der Welle: **960 bestanden**, 141 abgewählt (+23 gegenüber 937: Ebenenorientierung 2, `gewinde_referenz` 3, Schutzregel 6, URL 3,
Cache 7, Speicher 2). `swki api pruefe-code swki spikes tests/live` ohne Befund. Die Live-Nachweise nach der Welle (`test_live_kaufteile`,
`test_live_kaufteil_hole`, Referenzen Motorhalter und Stehlager wegen `referenzen.py`) folgen auf frischem SolidWorks durch den Controller.

**Offen gelassen** (Triage des Reviews, Details in Abschnitt 13): Minor 3 (`pruefung.volumen` Pflicht – die Live-Negativfälle hängen daran),
Minor 8 (Datenblatt-Dateiname kann kollidieren), Minor 9 (`liste` nur für das aktuelle SW-Jahr), Minor 10 (G1-Bereich: ISO 965-1 lässt für
M5-6H D1 bis 4,334 zu – beim nächsten Befund dieser Art den Nutzer mit dieser Zahl fragen), Refactor der Duplikate (B6), Busy-Loop-Test (B13),
Zylinderlänge in der Diagnose (B12) sowie die kosmetischen Task-Minors.

## 10. Testzahlen je Task

Unit-Suite (`pytest -q`): Soll laut Plan (Hauptplan, ab G laut Nachtrag) gegen Ist; abgewählt = Live-Tests (`sw`-markiert).

| Task | Inhalt | Soll (bestanden/abgewählt) | Ist | Zuwachs Ist | Commit |
|---|---|---|---|---|---|
| – | Stand vor dem Plan | 847 / 133 | 847 / 133 | – | – |
| 1 | Muster-Getriebemotor (Specs) | 850 / 133 | 850 / 133 | +3 | a892825 |
| 2 | Spike S15 (live) | 850 / 133 | 850 / 133 | 0 | 6b04437 |
| 3 | Konfiguration, Schema, Katalog, Eintrag | 874 / 133 | 874 / 133 | +24 | 4038626 |
| 4 | Ortung, Bewertung, Diagnose, Spitzenmessung | 893 / 133 | 893 / 133 | +19 | 2a17ff2 |
| 5 | SolidWorks-Schicht, Aufnahme (live) | 893 / 138 | 893 / 138 | 0 (+5 Live) | 81d7ba6 |
| 6 | Quelle, Cache, Befehle | 903 / 138 | 903 / 138 | +10 | 20b8bd4 |
| 7 | Muster-Eintrag (ersetzt durch 7N, nie freigegeben) | 903 / 139 | entfällt | – | – |
| 8 | Baugruppen: Format bis Freigabe | 912 / 139 | 912 / 138 (Task 7 zurückgestellt, Ruling N4) | +9 | 648fc83 |
| Fix-N | Flächenmodelle ohne Absturz | – | 916 / 138 | +4 | 4d41434 |
| 8 Fix 1 | `drehlage_doppelt` (Ruling T8-1) | – | 918 / 138 | +2 | 36ca23b |
| 9 | Baugruppen: Bau, Prüfen, Bericht | 917 / 139 | 923 / 138 (Plan rechnete mit anderem Stand) | +5 | 5ee0086 |
| G | Gewinde-Ø-Bereich, `IMPORTWEG_VERSION` 2, QUELLE_FEHLT mit URL | 930 / 138 (Nachtrag) | 930 / 138 | +7 | df87806 |
| Fix-E | Prüfbericht nennt gelesene Eigenschaften | – | 932 / 138 | +2 | ebdd960 |
| 7N | Eintrag GPLE60, Freigabe, Prüfer, `hole` (live) | 931 / 139 | 933 / 139 | +1 (+1 Live) | 2babeef |
| 10N | Referenz Motorhalter (live) | 932 / 141 | 937 / 141 | +4 (+2 Live) | 0802a4b, 87b18cc, 8e80b1d |
| 11N | Skill, Prüfer, CLAUDE.md, Design, Ergebnisse, Regression | 932 / 141 | 937 / 141 | 0 | a7f61b5, Ergebnisse (Dokumentationscommit der Fix-Welle) |
| Fix-Welle | Gesamt-Review: Ebenenorientierung, `gewinde_referenz`, Schutzregel, URL-Schema, `cache.lies`, `Spitzenmessung` | – | 960 / 141 | +23 | e2ace71, b729ffa, 6106e4c, c17852c, d348dfb, 4ae924b |

Abweichungen gegen den Plan: Task 8 (912 statt 912/139, weil Task 7 zurückgestellt wurde), Task 9 (923 statt 917, die Rechnung des
Plans galt für einen anderen Stand), 7N (933 statt 931: +2 aus Fix-E), 10N (937 statt 932: +2 aus Fix-E, +3 aus den
Messcode-Fixes 10N-1 [2 Tests] und 10N-2 [1 Test]; Etappe 1 selbst +1). Tasks 2 und 11N ohne neue Unit-Tests. Abgewählt: +5 Task 5
(Live der Aufnahme), +1 Task 7N (`hole`), +2 Task 10N (Referenzeintrag Motorhalter, Negativfall) = 133 → 141.

## 11. Spike S15 (Task 2) – Ergebnis und Entscheidung je Zeile

Messwerte: `docs/stufe0/ergebnisse/s15_kaufteile.json`; Bericht `task-2-report.md` (Ledger-Ordner). SolidWorks 2025, `spikes/s15_kaufteile.py`
lief beim ersten Versuch durch (`ok: true`), keine Korrektur. Die Rulings standen vorab im Ledger.

| Z. | Frage | Ergebnis (gemessen) | Entscheidung (Ruling) | Wenn falsch / Kosten |
|---|---|---|---|---|
| 1 | Test-STEP (e): Export der Muster-Baugruppe, Reproduzierbarkeit | `cli` [0, 0, 0], Baugruppen-STEP geschrieben (1238 Zeilen, 83,5 KB). **Abweichend:** zwei Exporte unterscheiden sich in 1221 von 1238 Zeilen (Entitätsreihenfolge, nicht nur Kopfzeilen); nicht byte-reproduzierbar. SHA-256 der committeten Datei `40d8f4fd…5716`, CRLF | S15-1: Test-STEP committen, `.gitattributes` mit `*.step -text`/`*.stp -text` (B2); Datei nie neu erzeugen, Spike S15 nicht erneut laufen lassen (B4) | Neulauf würde SHA-256 in Eintrag und Urteil entwerten (dann `git checkout` der STEP); sonst keine |
| 2 | Import (a): `GetImportFileData`, `LoadFile4`, Strukturabbildung 2 | bestätigt: `LoadFile4` liefert das Dokument (Fehler 0, 1,191 s) ohne `OpenDoc6`, 2 Volumenkörper | S15-2: Plan-Code bleibt | `OpenDoc6` im selben Optionsblock |
| 3 | Optionen (a) | bestätigt: während {Interconnect aus, Diagnose aus, Abbildung 2}, nachher = vorher {an, an, 0} | S15-3: bleibt | `importoptionen` korrigieren |
| 4 | Ohne Original (a, d) | bestätigt: keine Features mit `Is3DInterconnectFeature` (Importiert1/2 sind `BaseBody`); nach Löschen der Kopie öffnet das Teil mit 2 Körpern und allen `EINBAU_*` | S15-4: bleibt | Optionen 791–793 untersuchen, Paket anhalten |
| 5 | Diagnose (b) | bestätigt: `Check3` liefert ein Objekt mit `Count` 0 (nicht `None`; der Code zählt `Count`), 0 Flächenkörper, Hüllquader [60, 107, 60] umfasst beide Körper, Volumen 220 530,906 mm³, 23 Flächen | S15-5: unverändert | Box je Körper über `GetBodyBox` |
| 6 | Achse (c) | bestätigt: `InsertAxis2` ok, Bezugsachse (`RefAxis`) auf der y-Achse, Richtung −y | S15-6: bleibt | Achse über zwei Kreiskanten |
| 7 | Ebene (c) | bestätigt: Punkt (0, 0, 0), Normale der Bezugsebene −y = Flächennormale | S15-7: Motorhalter `v4` bleibt `entgegengesetzt` | `v4` auf `ausrichtung: gleich` |
| 8 | Drehlage (c) | bestätigt: Ebene über einen 3D-Skizzenpunkt, Normale ±x, Rebuild ok, alle drei Namen vorhanden | S15-8: bleibt | Hilfsachse durch ein Gewindeloch |
| 9 | Masse (d) | **abweichend:** Überschreibung wirkt wie im Plan-Code nicht (`override` false, Masse 0,2205 statt 1,2 kg; `GetOverrideOptions` liefert bei jedem Aufruf ein neues Objekt). Sonde: wirkt, wenn **alle Volumenkörper ausgewählt** sind (`IBody2.Select2(append, None)`), dann `CreateMassProperty2` → `GetOverrideOptions` → `OverrideMass = True` → `SetOverrideMassValue(kg)` → `mp.SetOverrideOptions(opts, 1 [swThisConfiguration], pythoncom.Empty)` → Auswahl leeren; bleibt nach Speichern/Neuöffnen und in der Baugruppe (1,2 kg) | S15-9: Task 5 setzt die Überschreibung so um (`setze_masse`); die Spec-Entscheidung „Masse aus dem Datenblatt überschreibt“ bleibt erfüllt; Nutzer informiert. Live belegt: Muster 1,2 kg (Task 5), GPLE60 1,1 kg bei 3 Körpern (Task 7N/10N) | Prüfung `masse` scheitert live → Spalte „sonst“ (nur Material, `ok: None`) |
| 10 | Kernloch (c) | bestätigt für das Muster: `gewinde_d` [4,2] → Modell `kernloch`. Für den GPLE60 gilt das **nicht** (Ø 4,134 = D1, Befund G1) | S15-10 für das Muster; die Weiche entfällt durch Task G (Ø-Bereich D1 … Kernloch) | – |
| 11 | Baugruppe (f) | bestätigt: `FeatureByName` für alle drei `EINBAU_*`, Gewindeentität gewählt; Masse der Baugruppe 0,2205 (folgt Z. 9; mit funktionierender Überschreibung 1,2 kg) | S15-11: bleibt | Auswahl per `SelectByID2("<name>@<komponente>@<baugruppe>")` |
| 12 | Zeit und Speicher (g) | Import 1,19 s (< 10 s), 0,0297 s je Fläche (< 0,05). **Abweichend:** Private Bytes 1099,3 → 2942,2 MB, Zuwachs **1843 MB** (> 1 GB) beim ersten Import der Sitzung; von der Erstladung des STEP-Übersetzers nicht getrennt (nicht gemessen) | S15-12: Hinweis im Skill `kaufteile` (erster STEP-Import ~1,8–3 GB Spitze, Zeit je 1000 Flächen ~30 s), Nutzer informiert, vor Live-Tasks frischer Start, 4-GB-Grenze je Sitzung | mehr Neustarts |
| 13 | Bilder (h) | Bilder erzeugt (iso 247 727, vorne 151 692, oben 172 573, rechts 165 042 Byte); Sichtprobe des Controllers: `EINBAU_ACHSE`, `EINBAU_FLANSCH`, `EINBAU_DREHLAGE` sichtbar und beschriftet | S15-13: bestätigt, `zeige_bezuege` bleibt (B1: Bilder erst nach der Sichtprobe gelöscht) | Bilder ohne Bezüge, Prüfer stützt sich auf `bezug` im Prüfbericht |

Speicher des Spikes: Start 278,4 MB, nach den Testdaten 1099,3, nach dem Import 2942,2, Ende 2794,0 MB; nach den Zusatzsonden
3062–3354 MB. Laufzeit rund 2 Minuten (Bau der Muster-Baugruppe 30,9 s). Einstellungen vorher und nachher `False 1`; Import-Optionen
`True True 0`.

## 12. Abweichungen von der Spec

Präzisierungen und Rulings aus dem Ledger. **Dieser Abschnitt ist der dauerhafte Nachweis:** der Ledger
(`.superpowers/sdd/2026-10-06-kaufteile-step-import/`) ist nicht versioniert. Die Spec 3c trägt „*Nachgezogen bei der Planung*“
(Plan) und „*Nachgezogen bei der Umsetzung*“ an den betroffenen Stellen (§2, §4.2, §4.3, §5.3, §6.1, §6.3, §6.4, §9, §11, §12,
§15). Je Ruling: Entscheidung, Grund, Kosten falls falsch.

**Preflight (vor Task 1, 19 Befunde, `preflight-scan.md`)**

- **B1:** Task 2 löscht `S15/bilder` nicht; der Controller macht die Sichtprobe und löscht danach. Kosten: keine.
- **B2:** `.gitattributes` mit `*.step -text`, `*.stp -text`, mit der Test-STEP committet (`core.autocrlf=true` würde die Bytes und damit die
  SHA-256 je Rechner verändern können). Kosten: eine Zeile zu viel.
- **B3:** Prüfer-Checkliste Kaufteil gibt der Controller in Task 7 und 10 im Prüfer-Auftrag mit; `pruefer.md` selbst in Task 11
  (Agent-Definitionen werden evtl. erst bei Sitzungsstart geladen). Kosten: keine.
- **B4:** Spike S15 nach dem Commit nicht erneut laufen lassen. Kosten: Neulauf entwertet Eintrag und Urteil.
- **B5:** `hole` prüft das Prüfer-Urteil **vor** dem Cache-Treffer (Spec §5.3 Schritt 1 bindend); betroffene Plan-Tests mit Urteil
  versorgt, ein Test ergänzt. Kosten: gering.
- **B6:** eigenes `swki/kaufteile/bewertung.py` (Prüfungen `einbau`/`gewinde`/`import`/`koerper` passen nicht in die Teil-Bewertung);
  Duplikate (`_masse_pruefen` u. a.) → Gesamt-Review. Kosten: späterer Refactor.
- **B7:** Spike-Lücken: Kollision Schraube ↔ Kaufteil deckt Task 10 live ab; **Zoll-STEP wird nicht getestet** (offener Punkt,
  Abschnitt 13). *Präzisiert im Gesamt-Review:* das „größere Modell“ als Abnahmedatei entfiel mit dem GPLE60 (nur 55 Flächen); für
  Hersteller-STEP mit Tausenden Flächen sind Zeit und Speicher der Flächenschleifen (mehrere COM-Aufrufe je Fläche) ungemessen. Ein
  Zoll-Maßstabsfehler wird von der Volumenprüfung **nicht** gefangen (Soll und Ist stammen aus demselben Import); nur ein belegtes
  Kennmaß (Hüllquader, Durchmesser, Maß) würde ihn melden. Kosten: Maßstabsfehler erst im Einsatz bzw. bei unbelegten Kennmaßen nie.
- **B8:** Referenz `gewinde` und `je_position` auf Kaufteil-Gewinde laufen bisher **nur in Unit-Tests** (nach der Fix-Welle auch
  `gewinde_referenz` mit Attrappen), nicht live; keine Planänderung, offener Punkt (Abschnitt 13). Der Motorhalter positioniert die
  Schrauben über die Bohrungen des Bocks (`je_position` auf `bock.f4`), nicht über die Gewindepositionen des Kaufteils. Erster Einsatz
  mit Prüfer und Sichtprobe, danach als Live-Test in die Suite. Kosten: Live-Fehler erst beim ersten Einsatz.
- **B9:** Vor Task 10 Step 6 und jedem Baugruppen-Live-Lauf startet der Controller SolidWorks neu. Kosten: keine.
- **B10:** Muster-Masse 1,2 kg bleibt (Datenblatt-Wert, Massenüberschreibung). Kosten: evtl. ein Prüfer-Mangel (durch den GPLE60
  gegenstandslos).
- **B11:** Verweis im Skill `baugruppe` auf den eigenen Abschnitt 8 korrigiert. Kosten: keine.
- **B12:** fehlende Zylinder-„Länge“ in `diagnose.uebersicht` → deferred Minor. *Abweichung von Spec §5.1:* die Diagnose nennt die Länge eines
  Zylinders nicht; der Skill `kaufteile` umgeht das mit „Fläche / (π·Ø)“ für die Gewindetiefe.
- **B13/B14/B15:** Busy-Wait-Test, wörtliche Duplikate, mögliches falsches `drehlage_doppelt` den Task-Reviews überlassen; B15 wurde in
  Task 8 gefunden (T8-1).
- **B16:** CLAUDE.md-Ausnahme „Test-STEP“ bei „Erzeugte SolidWorks-Dateien kommen nicht ins Git“. Kosten: keine.
- **B17–B19:** kein Befund.

**Spike und Nutzerentscheidungen:** S15-1 … S15-13 (Abschnitt 11); N1–N8 (Abschnitt 2 und folgende):

- **N1:** Muster-Specs, `gm42-10.step`, `.gitattributes` bleiben als interne Testdaten (Spike S15, `test_live_kaufteile.py`, Unit-Beispiele).
  Kosten: tote Testdaten, später löschbar.
- **N2:** nicht freigegebenen Muster-Eintrag, Quellkopie und Laufordner gelöscht (selbst angelegt). Kosten: keine.
- **N3/N7:** Tasks 7, 10, 11 neu geplant; Reihenfolge Task 9 → Task G → 7N → 10N → 11N; Plan-Nachtrag
  `docs/superpowers/plans/2026-10-06-kaufteile-nachtrag-gple60.md` (Planer-Agent). Kosten falls falsch: Nacharbeit am Nachtrag.
- **N4:** Task 8 lief parallel zur Diagnose (kein SolidWorks, eigener Test-Eintrag); Soll 912/138. Kosten: keine.
- **N5:** Fix-N als eigener Fix-Task nach Task 8. Kosten: gering.
- **N6:** ST4118M1804-A als Kaufteil unbrauchbar, Nutzer gefragt (Abschnitt 3).
- **N8:** Planer-Entscheidungen übernommen: Material 1.0503 (Masse überschrieben 1,1 kg); h7 als ±IT7 (0,018/0,025); Zentrierbohrung Ø 40 × 5
  plus Durchgang Ø 20; Name Motorhalter bleibt; fehlende Herstellerdatei → Live-Test schlägt fehl (kein Skip); Untergrenze 0,01 mm³
  absolut für `nenn`. Kosten falls falsch: Anpassung in 7N/10N.

**Präzisierungen des Nachtrags (bindend für G, 7N, 10N, 11N)**

- **Präz. 12 / `IMPORTWEG_VERSION`:** 1 → **2**: Gewinde-Ø-Bereich und Gewindemodell mit gemessenem Ø; alte Cache-Einträge gelten als veraltet
  (es gab noch keinen echten Eintrag). Kosten: keine.
- **Präz. 16 / `gewinde_modell`:** `{gruppe: {modell: kernloch | nenn, durchmesser: <Ø, 4 Stellen>}}` in Aufnahme, Cache, `hole`-Rückgabe,
  Bauprotokoll; alte Textform → „Gewindemodell unbekannt“ (`ok: null`); Modell und Ø je Gruppe einheitlich, sonst Mangel `gewinde:<gruppe>`.
- **Präz. 17:** Muster nur interne Testdatei; Katalogeintrag ist `nanotec/gple60-2s-32.yaml`.
- **Präz. 18/19:** Motorhalter mit GPLE60 (Lochkreis 52 unter 45°, Zentrierbohrung Ø 40 × 5 als Senkung einer Bohrung Ø 20, Gewindetiefe/Bohrtiefe 10,
  Achshöhe 62, Hüllquader [160, 102, 100]); Negativfall M5 × 16 (11,4 > 10).
- **Präz. 20:** Herstellerdateien nie ins Git; **Präz. 21:** `bereite_vor` prüft nur noch (`KAUFTEIL_QUELLE_FEHLT`, kein Skip).
- **Präz. 22:** Bericht mit Spalte „Gewindemodell (Ø mm)“.
- **Präz. 23:** Gewinde-Gegenprobe Bereich D1 − 0,01 ≤ Ø ≤ Kernloch + 0,01; Steigung bei Feingewinde aus der Größe, bei Regelgewinde aus der
  Normtabelle ISO 4762 (Spalte `p`); ohne Steigung nur das Tabellen-Kernloch. Keine neue Tabelle.
- **Präz. 24:** `KAUFTEIL_QUELLE_FEHLT` nennt bei `original.bezug.art: url` URL und Datum (Meldung und `daten.url`) sowie den Befehl `untersuchen`.
- **Präz. 25:** Gewindepaarung Toleranz `max(1 % des Solls, 0,01 mm³)` (`TOL_GEWINDE_MIN_MM3`): Task-9-Review fand, dass bei Modell `nenn` (Soll 0, relative
  Toleranz) jedes Rauschvolumen > 0 ein Mangel wäre. **Gemessenes Rauschen:** der Motorhalter nutzt Modell `kernloch`; Rauschvolumen bei `nenn`
  live nicht gemessen; die Kollision Zentrierbund Ø 40 ↔ Tasche im Motorhalter blieb leer (`kollision: []`). Wird die Untergrenze live
  überschritten: nicht still erhöhen, Nutzer fragen.
- **Präz. 26:** Drehlage des GPLE60 = Symmetrieebene des Lochbilds (Nutzerentscheidung, Abschnitt 2, Nr. 7).

**Rulings zu den Tasks**

- **T8-1 (Task-8-Review, Vorab-Befund B15):** `drehlage_doppelt` nur, wenn die konzentrische Verknüpfung auf der Kaufteil-Seite eine `referenz`
  (EINBAU_*) nutzt, nicht bei Gewindepositionen (Spec §8.1); der Plan-Code hätte jede Flanschverschraubung mit Hinweis belegt; +2 Tests. Kosten:
  ein fehlender Hinweis in einem Sonderfall.
- **Befund G1 / Task G:** siehe Abschnitt 2, Nr. 5. Spec §4.3, §5.3, §6.4, §10 nachgezogen.
- **7N-1:** Vorzeichenfehler der Brief-Erwartung zum Boden der Gewindelöcher (Abschnitt 4.1); keine Eintragsänderung. Kosten: keine.
- **10N-1:** `swki/pruefung/messen.py` `durchmesser` sucht die Zylinderfläche über alle Features des Ergebnisses statt nur `features[0]`; verworfen: „auf
  Durchgang umstellen“ (die Passung des Zentrierbunds ist das wichtigste Maß) und „Bauweg in zwei Bohrungen teilen“ (würde den Hinweis
  „zusammenfassen“ auslösen). Erweiterung, schwächt nichts. Kosten falls falsch: `REFERENZ_MEHRDEUTIG` in einem Sonderfall.
- **10N-2:** `kontext_aus_datei` hängt `<id>_senkung` an. Risiko Formplatte `f7` (Regression Nr. 1 OK). Kosten falls falsch: Regression Formplatte.
- **Fix-N, Fix-E:** Abschnitt 3 bzw. 4.3.
- **Nutzer 2026-10-07 00:21 (Stopp):** Regression bei 77/141 unterbrochen, am 2026-10-07 fortgesetzt (Abschnitt 8).

**Spec-Nachzüge dieser Stufe** (in `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md`): §2 Referenz und Download-Regel,
§4.2 Achsrichtung und Drehlage, §4.3 Ø-Bereich, §5.3 Quelle fehlt und Cache-Eintrag, §6.1 Flächenmodelle (Fix-N), §6.3 Masse-Weg
(Ruling S15-9), Prüfbericht-Eigenschaften (Fix-E) und Durchmesser über alle Features (10N), §6.4 gemessener Ø und Untergrenze, §9 Checkliste, §10 Quelle fehlt,
§11 Katalogeintrag GPLE60, Abnahme und Motorhalter, §12 Masse-Weg und Ergebnisse des Spikes, §15 Fertig-Kriterium.

## 13. Offene Punkte

- **Zoll-STEP ungetestet (B7):** der Maßstab eines Zoll-STEP (Spec S15a) wurde nicht gemessen. Einen Maßstabsfehler fängt nur ein
  **belegtes Kennmaß** (Hüllquader, Durchmesser, Maß), nicht die Volumenprüfung (Soll und Ist kommen aus demselben Import). Zeit und
  Speicher für Hersteller-STEP mit Tausenden Flächen sind ungemessen (der GPLE60 hat 55 Flächen); vor dem ersten großen Modell messen.
- **Referenz `gewinde` und `je_position` auf Kaufteil-Gewinde nur Unit (B8):** die Referenzform `{komponente, gewinde, instanz, achse}` und
  `je_position` mit `gewinde:` laufen nur in Unit-Tests; der Motorhalter belegt live nur die Gewindepaarung im Kaufteil (Prüfung
  `gewinde:flanschschraube.<i>`) und `je_position` über die Bock-Bohrungen. `gewinde_referenz` hat seit der Fix-Welle einen
  Attrappen-Unit-Test (Instanzwahl, kleinster Radius, kein Treffer), ist aber **nie live gelaufen** (der Motorhalter benutzt sie nicht;
  der in Task 9 angekündigte Nachweis in 10N fand nicht statt). Erster Einsatz mit Prüfer und Sichtprobe, danach als Live-Test in die Suite.
- **M3 fehlt** in `swki/wissen/bohrungsnormen.yaml` (Gewinde, Zylinderschraube) und `swki/wissen/normteile/iso4762.yaml` (ab M5). NEMA-17-Motoren
  (ST4118, DB42) haben M3-Flanschgewinde und sind erst nach einer abgeglichenen und live gemessenen Erweiterung aufnehmbar.
- **Speicher:** Spitzen Baugruppen 9–11,2 GB (Motorhalter 9,05–9,3 GB; Stehlager 11,2, Zahnstangentrieb 10,3, Schlitten 9,9 GB); Aufnahme mit
  Bildern bis ~5,4 GB, erster STEP-Import einer Sitzung ~1,8–3 GB Spitze (Spike +1843 MB, nicht von der Erstladung des Übersetzers getrennt gemessen).
  Das Paket Speicher bleibt offen.
- **Rechner B (SW 2026)** nicht Teil von 3c; Cache je SW-Jahr ist vorbereitet, aber nicht getestet.
- **Deferred Minors** (Ledger, nach Task gruppiert):
  - *Task 1:* `datenblatt.md` sagt „Werte folgen aus den Specs“, Masse 1,2 kg tut das nicht (≈ 1,7 kg massiv; Ruling B10); Tests prüfen nur Gültigkeit
    (plan-mandated, Geometrie sichert der Spike); Welle Ø 10 in Bohrung Ø 10 ohne Spiel (Präz. 17).
  - *Task 2:* Masse-Sonden nur im Scratchpad (Task 5/7N belegen die Überschreibung live); Speicherzuwachs 1843 MB nicht von der Erstladung getrennt.
  - *Task 3:* ~~Schutzregel umgehbar (`DIN 912-12`)~~ und ~~`_domain` bei URL ohne Schema leer~~ (beide in der Fix-Welle behoben, Abschnitt 9); `katalog.geprueft` ohne Test,
    defektes `pruefer.json` wirft `JSONDecodeError`; `art_der_datei` liest YAML mehrfach, ACME/Acme gleicher Ordner (Präz. 8), `$defs/zahl` unbenutzt.
  - *Task 4:* Duplikate in `kaufteile/bewertung.py` gegenüber `pruefung/bewertung.py` (`_masse_pruefen`, `_durchmesser`, Hüllquader/Volumen/Material/Eigenschaften,
    `maengel`) und in `ortung.py` (`einheit`/`kreuz`/`winkel_grad`; Ruling B6); ~~`Spitzenmessung.__exit__` ruft `messen` ungeschützt~~ (behoben in der Fix-Welle; der Messfaden stirbt bei einem
    Fehler weiterhin still); `test_spitzenmessung_mit_attrappe` mit Busy-Loop ohne Zeitlimit (B13); `orte_gewinde` prüft nur die unendliche Achse;
    Winkeltoleranzen 1e-9/1e-6/0,01° uneinheitlich; `normmasse` `None` ungeschützt; `round(…, 4)`-Schlüssel an Rundungsgrenzen; `einbau`-Mangel ohne strukturiertes
    `soll`; `_gewinde` prüft nicht einheitliches Modell je Gruppe (inzwischen durch Task G); Testlücken (`durchmesser`/`huellquader`/`masse`-Abweichung, Lagefehler
    Bezugsgeometrie, keine Kandidaten); Zeile > 120 Zeichen `ortung.py:357`; Zylinderlänge fehlt (B12).
  - *Task 5:* `auswahl_leeren` im `finally` kann den Originalfehler überdecken; `_abbruch` verliert Kennzahlen; Fehler aus `messe`/`bewerte`/`screenshots`/`speichere` als rohe
    Exceptions; 3D-Skizze bleibt bei Fehler in `CreatePoint` offen (plan-mandated); kein Live-Test `KAUFTEIL_IMPORT`; Herkunft der Speicherspitze (Bilder?) nicht untersucht.
  - *Task 6:* ~~`cache.lies` fängt `UnicodeDecodeError`/Nicht-Dict nicht~~ (behoben in der Fix-Welle); Datenblatt behält den Dateinamen des Nutzers, gleiche Namen
    zweier Produkte eines Herstellers kollidieren (Review-Minor 8); `liste` zeigt nur den Cache des aktuellen SW-Jahrs (Minor 9);
    `lege_ab` ohne Schutz gegen Dateisperren (roher `PermissionError`), JSON ohne `default=str`; `--neue-version` legt inhaltsgleiche Zweitkopie an; geändertes
    Datenblatt ohne Weg; Testlücken (`.STP`, Original unverändert, defekter Cache); `hole`-Rückgabe beider Zweige uneinheitlich.
  - *Task 8:* `kaufteil_summen(bg)` doppelt in `freigeben_baugruppe`; `setdefault` nimmt nur die erste Drehlage-Verknüpfung; Meldungstext bei ISO 7089/4032 auf
    Kaufteil-Gewinde nennt nicht die Norm.
  - *Fix-N:* Gerüst von `untersuchen` hat `volumen.soll null` bei reinen Flächenmodellen (Eintrag dann schemawidrig; besser Block weglassen);
    Kommentar `bewertung.py:29` (Körperschlüssel `F1` …); Attrappe `Check3` Count 0 nicht abgedeckt; die Nanotec-Datei hat 9 Flächenmodelle, SolidWorks liefert 8 Körper (nicht untersucht).
  - *Task 9:* Modell `nenn` mit relativer Toleranz (durch Task G behoben); `bau.py`-Dict nennt bei mehrfachem Kaufteil die letzte Komponenten-ID; Protokoll wird vor `oeffne`
    geschrieben; ~~`gewinde_referenz` ohne Unit-Test~~ (Unit-Test in der Fix-Welle, live weiter offen).
  - *Task G:* untere Grenze 4,124 wegen Gleitkomma nicht inklusiv (Epsilon und Grenzwerttests fehlen); Gruppen-Ø = Ø der ersten Position statt Mittel; Feingewinde-Zweig in
    `steigung` für Kaufteile toter Code.
  - *Fix-E:* Teile- und Baugruppen-Prüfung haben weiter `ist` = nur Abweichungen (gleicher Eindruck für den Prüfer); Backslash-Ausdruck `bewertung.py:193`.
  - *Task 7N:* Maß „Wellenachse bis Passfederrücken 9“ abgeleitet (16 − 7) aus `d1`, freigegeben; `freigegeben.yaml` im Arbeitsbaum CRLF (Prüfung normalisiert); URLs ohne Netz nicht geprüft.
  - *Task 10N:* Docstring `kontext_aus_datei` ohne Senkungs-Hinweis; fehlende `<id>_senkung` wird still übersprungen; `skript`-Features nur `features[0]` im Dateikontext (Bestand).
  - *Task 11N Doku:* Verweis auf `docs/stufe3c/ergebnisse.md` hing bis zum Ergebnisse-Commit; ~~`pruefer.md` zitiert Spec §4.2~~ und ~~Codetabelle im Skill §5 ohne
    `KAUFTEIL_GENORMT`/`KAUFTEIL_NICHT_FREIGEGEBEN`~~ (beide in der Fix-Welle behoben); Design §9 Altlast „Normteile nur 2025“.
  - *Gesamt-Review, offen gelassen:* `pruefung.volumen` ist nicht Pflicht (Minor 3; der Fingerabdruck dient der Neuaufnahme auf anderer SW-Version, die Live-Negativfälle löschen
    `volumen`); G1-Bereich: ISO 965-1 lässt für M5-6H D1 bis 4,334 zu, ein Hersteller mit D1max oder Bohrer 4,3 fiele als Mangel auf (Minor 10; beim nächsten Befund den Nutzer mit
    dieser Zahl fragen); Teile- und Baugruppen-`ist` nur Abweichungen (Fix-E); Feingewinde-Zweig in `ortung.steigung` ohne Wirkung (das Schema kennt nur Regelgewinde).
- **Kandidaten nach 3c:** Formschräge, Stufe 4c (Nut- und Kurvenverknüpfung), Paket „Messarten“ (Fasen, Gewinde durch, Lagerachse), Paket Speicher – der Nutzer wählt.

## Stand

- Datum: 06./07.10.2026, Rechner A (SOLIDWORKS 2025), Branch `stufe-3c` (von `plan-kaufteile` @ 96beee2). Ohne Push. Commits seit `main`:
  `git log --oneline main..HEAD`. 960 Unit-Tests grün (nach der Fix-Welle; 937 bei `a7f61b5`).

| Task | Inhalt | Commit |
|---|---|---|
| Plan | Spec, Plan, Übergabe | d1894a6, cd57249, ff6576b, 96beee2 |
| 1 | Muster-Getriebemotor als Specs | a892825 |
| 2 | Spike S15, Test-STEP | 6b04437 |
| 3 | Konfiguration, Schema, Katalog, Eintrag | 4038626 |
| 4 | Ortung, Bewertung, Diagnose, Spitzenmessung | 2a17ff2 |
| 5 | SolidWorks-Schicht, Aufnahme | 81d7ba6 |
| 6 | Quelle, Cache, Befehle | 20b8bd4 |
| 8 | Baugruppen: Format bis Freigabe | 648fc83 |
| Fix-N | Flächenmodelle ohne Absturz | 4d41434 |
| 8 Fix 1 | `drehlage_doppelt` nur für Einbaureferenzen | 36ca23b |
| 9 | Baugruppen: Bau, Prüfen, Bericht | 5ee0086 |
| Nachtrag | Plan-Nachtrag GPLE60 | 3c3aa02 |
| G | Gewinde-Ø-Bereich, Gewindemodell mit gemessenem Ø | df87806 |
| Fix-E | Prüfbericht nennt die gelesenen Eigenschaften | ebdd960 |
| 7N | Katalogeintrag GPLE60, Freigabe, Urteil, Live-Test `hole` | 2babeef |
| 10N | Messcode (Senkung) und Referenz Motorhalter | 0802a4b, 87b18cc, 8e80b1d |
| 11N | Skill `kaufteile`, Prüfer, CLAUDE.md, Design, Spec-Nachzug | a7f61b5 |
| 11N | Ergebnisse (dieses Dokument), Regression 141/141 | Dokumentationscommit der Fix-Welle |
| Fix-Welle | Gesamt-Review: Ebenenorientierung, `gewinde_referenz`, Schutzregel, URL-Schema, `cache.lies`, `Spitzenmessung`, Spike-Schutz | e2ace71, b729ffa, 6106e4c, c17852c, d348dfb, 4ae924b, 1da3b0c |
