# Stufe 2c – Ergebnisse

Fertig-Kriterium Spec 2c §1 für Rechner A (SW 2025) erfüllt: Auswerferhalteplatte besteht (Prüfbericht und Prüfer), Buchse und
Formplatte bestehen weiter (Prüfbericht und Regressions-Suite; Prüfer-Agent dort nicht gestartet), 276 Unit-Tests grün.
Rechner B (SW 2026) offen.

Rechner A (SOLIDWORKS 2025), 01.10.2026: `pytest -v` 273 bestanden (48 abgewählt, das sind die `sw`-markierten
Live-/Referenztests; nach der Korrekturrunde unten: 276 bestanden, 54 abgewählt), `tests/live_einzeln.py tests/live tests/referenz` alle 48 Einzeltests `OK` (45 in `tests/live`, 3 in
`tests/referenz`; `test_sollvolumen.py` enthält keinen `sw`-Test), `swki api pruefe-code` ohne Befunde (`"befunde": []`), Toggle 10 (`GetUserPreferenceToggle`) vor und nach
dem Lauf `False`, Integer-Einstellung 6 vor und nach dem Lauf `1`.

Die Unit-Test-Zahl liegt um 1 über dem Plan (272): Task 9 hat einen Test ergänzt. Die Zahl der abgewählten Tests entspricht dem
Plan (48).

Weil der Speicher von `SLDWORKS.exe` bei Live-Läufen wächst (siehe unten), lief die Live-Suite dateiweise (`--zeit 240`) und
wurde nach 10 Dateien bei 4288 MB Private Bytes angehalten; SolidWorks wurde neu gestartet und die restlichen Dateien liefen
in der frischen Instanz weiter. Speicher nach den Läufen: Instanz 1: 430 MB nach der ersten Datei bis 4288 MB nach
`test_live_pruefen.py`; Instanz 2: 1116 MB nach `test_live_pruefen_normbohrung.py`, 1906 MB nach den Referenztests, nach den
beiden manuellen Läufen ca. 2150 MB (Stand am Ende 1951 MB).

Die Werte der Tabelle stammen aus je einem manuellen Lauf (`validieren` → `freigeben` → `bauen` → `pruefen`) in einem
Beispielauftrag unter `auftraege/` (`REF-AHP-2c`, `REF-BUCHSE-2c`, `REF-FORMPLATTE-2c`, nicht im Git), da die
Regressions-Suite ihre Protokolle wieder löscht. Alle drei Prüfberichte: `bestanden: true`, `maengel: []`.

| Referenz | SW 2025 (Rechner A) | Knoten / Features | SW 2026 (Rechner B) | Bemerkung |
|---|---|---|---|---|
| Auswerferhalteplatte | 01.10.2026, Volumen ist 692653,890 mm³ / soll 692653,890 mm³ (Abw. 0,0000 %), Dauer 47,516 s | 10 / 10 | ausstehend | Prüfer-Urteil bestanden (Task 11), `swki status`: Lauf 1 bestanden |
| Buchse | 01.10.2026, Volumen ist 37425,139 mm³ / soll 37425,1 mm³ (Abw. 0,0001 %), Dauer 18,518 s | 6 / 6 | ausstehend | Ergebnis unverändert gegenüber Stufe 2 (Dauer 18,5 s statt 15,2 s) |
| Formplatte DS | 01.10.2026, Volumen ist 3069575,535 mm³ / soll 3069574,5 mm³ (Abw. 0,0000 %), Dauer 35,072 s | 10 / 12 | ausstehend | Notausgang f10 unverändert (dort 26,106 s) |

Buchse und Formplatte hatten bei diesen manuellen Läufen noch kein Prüfer-Urteil (Prüfer-Agent nicht gestartet); `swki status`
zeigt daher „Prüfer ausstehend“. Maßgeblich ist der Prüfbericht von `swki pruefen` (alle Prüfpunkte `ok`).
Die Formplatte hat 12 Features bei 10 Knoten: f7 (Bohrung mit Senkung: `f7`, `f7_senkung`) und das Skript f10
(zwei Bohrungen: `f10`, `f10_2`) erzeugen je zwei.

## Spike S10

Befunde und Entscheidungen: `docs/stufe0/ergebnisse.md`, Abschnitt „Stufe 2c: Spike S10“ (Rohdaten
`docs/stufe0/ergebnisse/s10_f*.json`), Lehren für den Code in `swki/wissen/pywin32-fallstricke.md` (Abschnitt „Stufe 2c“).
Alle sechs Fragen wurden mit „geht“ beantwortet, Frage 6 mit einer Einschränkung (Aufsatz mit `versatz_von_flaeche` bei
abgesetzter Skizze ergibt einen getrennten Körper, siehe Offene Punkte). Abweichungen vom Plan:

- **Stift mit `durch`:** `HoleWizard5` liefert dafür nie ein Feature. Der Handler geht über `CreateDefinition(25)` →
  `InitializeHole(2, 8, 710, "Ø<d>.0", 1)` → Vorselektion per `SelectByRay` → `CreateFeature`. Danach liest
  `FastenerType2` −1 (nicht 710), `Type` = 25; das wird im Rücklesen akzeptiert (Entscheidung Controller, 2026-09-29).
- **`CreateFillet` legt selbst ein Radiusmaß an:** `verrunde` fügt kein eigenes `AddDimension2` hinzu, sondern findet das Maß
  über den Vergleich der Maßnamen vor/nach dem Aufruf und bindet es per Gleichung an den Parameter.
- **Langloch-Koinzidenz:** bei einem Langloch mit Winkel (z. B. 30°) wird der Hilfslinienanfang per `sgCOINCIDENT` an den
  Mittelpunkt des Langlochs gebunden; `sgMERGEPOINTS` legt keine Beziehung an und die Skizze bleibt unterbestimmt (Status 2).
- **`ForceRebuild3` statt `EditRebuild3`** nach dem Ändern der Positionsskizze; ohne `ForceRebuild3` baut sich das
  Bohrungsfeature nicht immer neu auf. Dazu die **Zylinderprüfung je Position:** `GetSketchPointCount` zählt Skizzenpunkte,
  nicht Bohrungen; der Handler prüft deshalb je Position eine Zylinderfläche mit Achse durch den Achspunkt. Beides ist in
  Task 8 entstanden (`swki/compiler/handler/normbohrung.py`, Regressionstest
  `tests/live/test_live_normbohrung.py::test_senkschraube_von_unten`), nicht im Spike.
- **`_verschmelze` entfällt bei der Kontur** (Entscheidung 5): die Bögen teilen ihre Endpunkte mit den Linien schon; das Verschmelzen
  bleibt nur für die Hilfslinie des Langlochs (dort als `sgCOINCIDENT`).
- **Bohrungsdaten lesen:** `Type` ist `swWzdHoleTypes_e` (Art und Ende zusammen), `Depth` liest immer 0. `messen.lies_normbohrung` liest
  `TapDrillDepth` (Gewinde) bzw. `HoleDepth` (sonst) als Bohrtiefe und `ThreadDepth` als Gewindetiefe. Bei `durch` wird keine
  Bohrtiefe verglichen (die Spezifikation hat dann kein `tiefe`); verglichen wird nur, was die Spezifikation angibt
  (`tiefe`, `gewindetiefe`).
- **Maßtabelle mit SolidWorks-Werten:** `bohrungsnormen.yaml` (25 Größen) enthält die vom Bohrungsassistenten gelieferten Maße;
  7 Größen weichen von den ISO-Vorwerten ab (ISO 4762 M8/M10/M12 Senktiefe, ISO 10642 M5–M10 Senkdurchmesser) und tragen das
  Feld `abweichung`.
- **Sollvolumen neu gerechnet:** `tests/referenz/auswerferhalteplatte/sollvolumen.py` liefert nach der Umstellung auf die SolidWorks-Maße der
  Tabelle 692653,890 mm³ statt des Planwerts 692845,209 mm³; der gebaute Wert stimmt auf 0,0000 % überein.

## Laufzeiten (Phasenzeiten aus dem Protokoll, Rechner A)

**Auswerferhalteplatte** – gesamt 47,516 s: vorbereiten 1,41 s, bauen 45,514 s, speichern 0,509 s.
Je Feature: f1 Extrusion 6,092 s, f2 Normbohrung (4 Positionen) 4,84 s, f3 Normbohrung 2,712 s, f4 Normbohrung 2,972 s,
f5 Normbohrung 2,257 s, f6 Normbohrung 2,522 s, f7 Schnitt 6,554 s, f8 Schnitt 4,136 s, f9 Schnitt 7,671 s, f10 Fase 5,754 s.

**Buchse** – gesamt 18,518 s: vorbereiten 1,01 s, bauen 16,963 s, speichern 0,448 s.
Je Feature: f1 Rotation 6,711 s, f2 Fase 0,685 s, f3 Fase 0,736 s, f4 Rotation 5,088 s, f5 Bohrung 2,773 s,
f6 Muster (Kreis) 0,965 s.

**Formplatte DS** – gesamt 35,072 s: vorbereiten 1,004 s, bauen 33,409 s, speichern 0,551 s.
Je Feature: f1 Extrusion 3,566 s, f2 Bohrung 5,76 s, f3 Schnitt 2,883 s, f4 Verrundung 3,545 s, f5 Verrundung 1,834 s,
f6 Fase 4,297 s, f7 Bohrung mit Senkung 4,244 s, f8 Muster (linear) 1,132 s, f9 Spiegeln 0,746 s,
f10 Skript (Notausgang, M8-Gewinde) 5,399 s.

Buchse und Formplatte laufen gegenüber Stufe 2 (15,2 s bzw. 26,1 s) etwa 20–35 % langsamer; beide Läufe fanden in einer
SolidWorks-Instanz mit rund 2 GB Private Bytes statt (Stufe 2: unter 700 MB). Eine Ursache wurde nicht untersucht.

## Korrekturrunde nach dem Gesamt-Review

- **W1 (belegt):** Der −1-Zweig der Bogenrichtung (`CreateArc`, Fläche mit gespiegeltem Skizzensystem) und Langlöcher mit
  Winkel in [90°, 180) sind jetzt live belegt (`tests/live/test_live_konturen.py`): Kontur mit Bögen auf der Unterseite `-y`
  und der Rückseite `-z` eines Grundklotzes (Volumen, Box und Achsenlage beider Bogenmitten stimmen) sowie Langloch 150°
  und 120° auf `+y`, 150° und 30° auf `-y` (Lage der Zylinderachsen). Der Compiler brauchte keine Korrektur.
- **W2:** neue Prüfung `koerper` in `swki/pruefung/bewertung.py` (Soll: genau 1 Volumenkörper, gemessen mit
  `topologie.koerper`); drei neue Unit-Tests, jetzt 276 Unit-Tests grün.
- **Live-Nachlauf (Rechner A, SW 2025, frische Instanz, einzeln mit Zeitlimit):** `test_live_konturen.py` 14 OK (davon 6 neu),
  `test_live_endbedingungen.py` 3 OK, `test_live_pruefen.py` 2 OK, `test_live_pruefen_normbohrung.py` 2 OK, `tests/referenz`
  3 OK (Buchse, Formplatte, Auswerferhalteplatte, jetzt mit der Prüfung `koerper`) – zusammen 24 Einzeltests, alle `OK`.
  Die übrigen Live-Dateien (54 `sw`-Tests insgesamt: 51 in `tests/live`, 3 in `tests/referenz`) liefen nach der Korrekturrunde
  nicht erneut; ihr Code wurde nicht geändert (Änderungen: Prüfung `koerper`, Fehlerprüfung in `_langloch`). Speicher
  Private Bytes: 429 MB nach Neustart, 2099 nach den Endbedingungen, 2463 nach `pruefen`, 2735 nach `pruefen_normbohrung`,
  3209 nach den Referenzen. Toggle 10 `False`, Integer-Einstellung 6 `1` nach dem Lauf.

## Aufräum-Paket (Stand 2026-10-02)

Branch `aufraeumen`, Commits 124fe29 bis 4a1aa7f und der Abschluss-Commit dieses Tasks. Nutzerentscheidungen (2026-10-01):
höchstens 4 Läufe (1 + 3), Bauabbruch-Läufe werden nicht verglichen, Rechner B zurückgestellt, Gruppen A–E vollständig.

- **Unit-Tests:** 330 passed, 55 deselected (vorher 276 passed, 54 deselected). `swki api pruefe-code`: keine Befunde.
- **Live (Rechner A, SW 2025, einzeln mit Zeitlimit 240 s):** alle Dateien `OK`, in drei SolidWorks-Sitzungen (zwei Neustarts
  wegen Speicher, jeweils genau eine Instanz).
  - Sitzung 1 (Start 419 MB): `test_live_endbedingungen.py` 4 OK (davon 1 neu: Zwei-Körper-Fall), 2187 MB danach;
    `test_live_konturen.py` 14 OK, 3137 MB; `test_live_api.py` 2 OK, 2887 MB; `test_live_bauen.py` 3 OK, 3312 MB;
    `test_live_extrusion.py` 5 OK, 3651 MB; `test_live_kanten.py` 3 OK, 3837 MB. Danach angehalten (Neustart).
  - Sitzung 2 (Start 425 MB): `test_live_muster.py` 3 OK, 1020 MB; `test_live_normbohrung.py` 6 OK, 1414 MB;
    `test_live_parametrik.py` 1 OK, 2570 MB; `test_live_pruefen.py` 2 OK, 2924 MB; `test_live_pruefen_normbohrung.py` 2 OK,
    3183 MB; `test_live_rotation_bohrung.py` 3 OK, 3365 MB; `test_live_skript.py` 2 OK, 3479 MB;
    `test_live_verbindung.py` 2 OK, 3240 MB. Vor `tests/referenz` angehalten (Neustart).
  - Sitzung 3 (Start 422 MB): `tests/referenz` 3 OK (Buchse, Formplatte, Auswerferhalteplatte), 1304 MB danach;
    `test_sollvolumen.py` läuft ohne SolidWorks (Unit-Test, grün).
  - Zusammen 54 `sw`-Tests + 1 neuer = 55 Live-Tests, alle `OK`. Höchster gemessener Speicher: 3837 MB (Private Bytes).
- **Einstellungen:** Toggle 10 / Integer 6 vor dem ersten Lauf `False 1`, nach dem letzten Lauf `False 1`.
- **Änderungen je Gruppe:**
  - **A Prüfschleife (124fe29):** Läufe mit Bauabbruch werden bei „kein Fortschritt“ nicht verglichen; `pruefen` verweigert
    einen abgebrochenen Lauf; `--max` nur ≥ 0; Spec-Text (Vorgabe 3, Regel) und Skill-Text präzisiert.
  - **B Robustheit (f5dd9d2, c51b1ee, 6d0d6a8):** `freigeben` lehnt die Freigabe-Kopie ab und nennt deren Pfad;
    `bauen --lauf N` überschreibt keinen vorhandenen Lauf; `pruefer.json` wird auf Form geprüft; git-Fehler in
    `_compiler_aenderungen` werden abgefangen; `speichere` nur im Arbeitsordner; Compiler-Namen als Feature-IDs verboten.
  - **C Validierung und Hinweise (6d0d6a8, 32e4882, 29cc9e3):** Normbohrung: doppelte Positionen und Tiefe gegen Senkung;
    Kontur mit Bogenmitte auf einem Konturpunkt (Kreissektor); keine Fehlalarme mehr bei Mittellinie, 360, Fase 45,
    Sammelhinweis für Konturpunkte; Text `muster_kreis` (Regel 3); `_pappus` für Rechteck/Kreis, mehrere Profile nicht
    analytisch.
  - **D Tests (6d0d6a8, 618944c, 4a1aa7f, dieser Commit):** Ausdrucksfehler der Validierung, Randzweige der Hinweise,
    Skript-Zusatzfeature, `Kontext.verknuepfe`, Zylinderprüfung der Normbohrung ohne SolidWorks; live: Zwei-Körper-Fall und
    Toleranzen (`_flach`, `abs=1e-6`) in den Konturtests.
  - **E Code-Pflege (29cc9e3):** Konstanten nach `swki/pruefung/normen.py`, `eckradien_roh`.

## Offene Punkte

- Bohr- und Gewindetiefe von `normbohrung` hängen nicht per Gleichung an Parametern (kein belegtes Maß am HoleWzd-Feature);
  die Prüfung `normbohrungen` erkennt Abweichungen gegenüber der Freigabe.
- Formplatte: Notausgang f10 (M8) ließe sich jetzt als `normbohrung` bauen – Referenz bleibt bewusst unverändert.
- Aufsatz mit `versatz_von_flaeche`, dessen Skizze abgesetzt über der Zielfläche liegt: der Versatz geht zur Skizze hin und
  ergibt dadurch einen getrennten Körper (zwei Körper; Spike S10, Frage 6 d). Bekannte Einschränkung, kein Sonderweg; seit der
  Korrekturrunde meldet die allgemeine Code-Prüfung `koerper` (Soll: genau 1 Volumenkörper) mehrere Körper als Mangel –
  Zwei-Körper-Live-Test erledigt (Aufräum-Paket, `test_aufsatz_mit_versatz_bei_abgesetzter_skizze_ergibt_zwei_koerper`).
  Erledigt im Aufräum-Paket außerdem: Kreissektor-Kontur, doppelte Positionen/Tiefe der Normbohrung, Toleranz in den
  Konturtests.
- SolidWorks-Speicher wächst bei Live-Läufen (gemessen je Testdatei etwa 50–1250 MB Private Bytes); Neustart ab ca. 4 GB, die Live-Suite deshalb
  dateiweise laufen lassen.
- `.gitignore` schließt unter `auftraege/` nur die SolidWorks-Dateien aus (`*.sldprt`, `*.sldasm`, `*.slddrw`); Spezifikationen,
  Protokolle und Prüfberichte sind nicht ausgeschlossen, `git status` zeigt `?? auftraege/`. Beispielaufträge nicht versehentlich committen.
- Rechner B (SOLIDWORKS 2026): alle Referenzen noch nicht gelaufen (Abschluss Stufe 2 laut Spec §11) – zurückgestellt:
  Rechner steht nicht zur Verfügung (Nutzer, 2026-10-01).
