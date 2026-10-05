# Stufe 4b – Ergebnisse (Verzahnung und Kopplungen)

Fertig-Kriterium Spec 4b §12 für Rechner A (SW 2025): Die Teil-Referenzen *Zahnstange*, *Ritzelwelle* und *Antriebswelle* und die
Referenz *Zahnstangentrieb* (Zahnstange m 2 / z 30, Ritzel z 20, Räder z 25 und z 50) bestehen ohne Code-Mangel mit Prüfer-Urteil
„bestanden“; Negativfall E1 und die vier Negativfälle der Kopplungen liefern genau ihre erwartete Mängelmenge (Fall 3 mit
erweiterter Erwartung, Ruling T14-1); Buchse, Formplatte, Auswerferhalteplatte, Stehlager und Linearschlitten bestehen weiter
(Abschnitt 6, Regression **folgt**). 835 Unit-Tests grün. Rechner B (SW 2026) offen.

## 1. Kurzfassung

Was 4b kann:

- **Feature `verzahnung`** (`typ: verzahnung`, `art: stirnrad | zahnstange`): Evolventen-Stirnrad (Bezugsprofil DIN 867, α = 20°,
  ohne Profilverschiebung, z ≥ 17, Modul DIN 780 Reihe 1, `zahndickenabmass` < 0) und Zahnband der Zahnstange; Evolvente als Spline
  durch berechnete Punkte, ganzes Profil in einer Skizze mit fixierten Segmenten; Geometrie in `swki/verzahnung.py`, Modultabelle
  `swki/wissen/module_din780.yaml` (Reihe 1, 0,05 … 20 mm, abgeglichen; 25 … 50 gesperrt).
- **Teilprüfung `verzahnungen`** gegen die freigegebene Kopie: Kopf-/Fußkreis, Zähnezahl, Zahnweite (Strahl entlang der
  Grundkreistangente) bzw. Kopflinie, Teilung und Zahndicke der Zahnstange; `volumen: auto` mit Verzahnung; Konstante `pi` in
  Ausdrücken.
- **Kopplungen** `zahnrad` und `zahnstange` (`{komponente, feature}`), `freiheitsgrade: gekoppelt`; `bauen` dreht Seite `a` in
  Phase (`zahnphase:<id>`, `SetTransformAndSolve2`), legt die Kopplung per `CreateMate` an und liest sie zurück; Endlagen mit `pi`,
  Befunde `KOPPLUNG_ART`, `MODUL_UNGLEICH`, `GEKOPPELT_OHNE_ANTRIEB`, `KOPPLUNG_REIHENFOLGE`, `ENDLAGE_FEHLT`,
  `UEBERSETZUNG_WIDERSPRUCH`, `SCHRITTE_ZU_GROB`, `ZAHNPHASE_FEHLER`.
- **Prüfen:** `eingriff:<id>` (Achslage, Achsabstand, Überdeckung, Übersetzung), unterdrückte und fehlende Verknüpfungen,
  strenge Kollision im Eingriff, **Sollweg je Stellung** (`sollweg:<Bewegung>:<k>`, für alle Bewegungen) mit aufsummierter
  Drehung, Bilder `<id>-eingriff` (übrige Komponenten ausgeblendet), Bericht mit Grenze, Bereich, Endlagen, Sollweg und Kopplungen.
- **Reste aus 4a:** abgebrochene Läufe einheitlich `ok=None`, `GRENZE_REFERENZ`, öffentliche Helfer `eintrag`/`beschreibung`.
- Skill `baugruppe` §7, Skill `konstruieren` (Verzahnung, Bauzeit), Prüfer-Checkliste, Referenz `tests/referenz/zahnstangentrieb/`.

Testzahlen: Unit-Tests 711 → **835 bestanden**, abgewählt (Live, `sw`-markiert) 117 → **133**. Zuwachs je Task (bestanden):
Task 1 +29 (740), Task 3 +16 (756), Task 5 +7 (763), Task 7 +19 (782, darunter +1 für σ = −1), Tasks 9 und 10 zusammen +28 (810),
Task 11 +9 (819), Task 12 +11 (830, darunter +1 für T12-1 und +1 für T12-2), Task 13 +1 (831, Ruling T13-1), Task 12b +4 (835);
Tasks 2, 4, 6, 8, 14 ohne neue Unit-Tests. Abgewählt: +3 Task 4, +2 Task 5, +4 Task 6, +1 Task 11, +1 Task 12, +1 Task 13, +4 Task 14
(117 → 133). Gegenüber dem Plan (827/133) sind es 8 zusätzliche Unit-Tests: Task 7 σ = −1, T12-1, T12-2, T13-1 und 4 × Task 12b.
`swki api pruefe-code`: keine Befunde.

## 2. Spike S14a (Task 2) – Ergebnis und Entscheidung je Zeile

Messwerte: `docs/stufe0/ergebnisse/s14a_verzahnung.json`, `s14a_verzahnung_nachmessung.json`, `s14a_verzahnung_zeit.json`,
`s14a_verzahnung_zahnweite.json`. Alle Entscheidungen standen vorab im Ledger („Ruling“). SolidWorks 2025.

| Z. | Frage | Ergebnis (gemessen) | Entscheidung (Ruling) | Wenn falsch |
|---|---|---|---|---|
| 1 | Spline gegen Polylinie | bestätigt: Spline z 20 Status 3, 160 Segmente, Aufsatz ok, 1 Körper, größte Abweichung von der Soll-Evolvente 0,000114 mm (Polylinie 0,006084 mm) | Spline (`CreateSpline2`, alle Segmente `sgFIXED`) wie Plan-Code (S14a-Z1) | keine Kosten |
| 2 | Ganzes Profil in einer Skizze | abweichend: z 80 Skizze 108 s (im Nachtrag 267 s, Streuung Faktor 2,5 ungeklärt), +597 MB je Rad; Zeit entsteht im COM-Overhead je Punkt (Zeichnen 75–91 % der Skizzenzeit, ~0,3 s je Segment), nicht in der Skizzengröße | Ganzes Profil bleibt; Handler bekommt zwei Beschleunigungen: affine Abbildung (u, v) → Skizze (drei `zu_skizze`-Aufrufe kalibriert, Gegenprobe, Abweichung > 1e-9 m → `BauFehler`) und Auswahl aller Segmente in einem `MultiSelect2`-Aufruf (Auswählen z 80: 36,6 → 3,4 s) (S14a-Z2/Z5, T4-1) | Radbau bleibt langsam (~1–2 min je Rad), Live-Läufe länger; Lücke + Kreismuster erst nach erneuter Entscheidung |
| 3 | Messung | Zylinder (Kopf-/Fußflächen) und Zahnstange (Teilung 6,28319, Zahndicke 3,09159) bestätigt; Zahnweite abweichend: `IMeasure` zwischen ganzen Flanken 14,85701 statt 15,273894 mm (−0,417 mm, misst den Mindestabstand an den Flankenenden) | Zahnweite per Strahl entlang der Grundkreistangente (`IFace2.GetProjectedPointOn`, Spannmitte φ_m = winkel + (k − 1)·180°/z): Genauigkeit ≤ 0,00001 mm in vier Fällen (z 20/25/50, Abmaß −0,05/−0,10); `verzahnung_mm` bleibt 0,005 (S14a-Z3, T5-1) | Zahnweite misst falsch; fiele in Task 5/6 live auf (bestätigt: Zahnweite W3 live 15,273894 = Soll) |
| 4 | Radachse als Referenz | bestätigt: koaxiale Fußkreis-Zylinderfläche, r 17,5 (Spline und Polylinie) | wie Plan-Code, keine Bezugsachse im Handler (S14a-Z4); Spec-Nachzug §4.4 | Bezugsachse im Handler anlegen |
| 5 | Zeit und Speicher je Radbau | abweichend: z 17–50 im Spike 56–112 s und +294…+382 MB je Rad (Zeit in der Skizze) | nach den Beschleunigungen aus Z. 2 live: Rad z 20 14–24 s, z 50 19,7 s (Ziel < 15 s verfehlt, Abschnitt 4.5); Hinweis im Skill `konstruieren` (S14a-Z5-Folge) | nur ein Hinweistext |
| 6 | Zahnband auf dem Rücken | bestätigt: Zahnstange z 5 Status 3, 30 Segmente, Aufsatz ok, 1 Körper | eine Kontur je Zahn, Rücken genau bis zur Fußlinie wie Plan-Code (S14a-Z6) | Zahnband 0,01 mm in den Rücken verlängern |

Weitere Entscheidungen: T4-2 `dispatch_array` kommt schon in Task 4 nach `swki/verbindung.py` (Task 11 überspringt die Ersetzung);
T5-1 die Messgerade liegt auf halber Zahnbreite, kein Treffer → `REFERENZ_NICHT_GEFUNDEN` („Zahnweite nicht messbar“).

## 3. Spike S14b (Task 8) – Ergebnis und Entscheidung je Zeile

Spike `spikes/s14b_kopplung.py` an der Getriebeprobe (`tests/live/getriebeprobe/`; Platte, Zahnstange, Lagerbock, beide Wellen),
Messwerte `docs/stufe0/ergebnisse/s14b_kopplung.json` und `s14b_kopplung_neuoeffnen.json` (Nachtrag Zeile 13). SolidWorks 2025.

| Z. | Frage | Ergebnis (gemessen) | Entscheidung (Ruling) | Wenn falsch |
|---|---|---|---|---|
| 6 | `CreateMate` mit Zahnrad-/Zahnstangendaten | beide angelegt, Typ 13 (k1) / 10 (k2), Fehlercode 0. Bewegung richtig (Hub 0 → 60: Ritzelwelle +171,8873°, Antriebswelle −85,9437°). Rücklesen abweichend: k1 `Reverse` gelesen `true` (gesetzt `False`), k2 Zähler/Nenner vertauscht (gesetzt 100/50, gelesen 50/100); `DiameterVal` 40, `DiameterType` 0 bestätigt | `REVERSE = {zahnrad: False, zahnstange: False}` bleibt; `eingriff` vergleicht die Übersetzung als **ungeordnetes Paar** (sortierte Teilkreise, relativ 1e-6), `Reverse` wird nur berichtet (S14b-Z6, T11-Vorgabe, T12-1) | eine vertauschte Übersetzung meldet nicht `eingriff`, sondern Sollweg/Endlage (Negativfall 4 bleibt erkennbar, da × 1,1 das Paar ändert) |
| 7 | Zahnphase | bestätigt: `SetTransformAndSolve2` dreht Seite a um ihre Achse; Phasenfehler k1 0,0845 → 0, k2 0,1444 → 0 (Teilung) | Plan-Code bleibt (S14b-Z7) | `AddMate5` mit `ForPositioningOnly` |
| 8 | Bestimmtheit mit Kopplungen | bestätigt: Grenze unterdrückt, ohne Antrieb Zahnstange, Ritzel- und Antriebswelle 2 (Platte, Lagerbock 3); mit Antrieb alle 3 | Plan-Code bleibt (S14b-Z8) | Mitfahrer melden wie ihr Träger |
| 9 | Kollision im Eingriff, Zeit, Speicher | Kollision und Zeit bestätigt: in Phase keine Paare über 9 Stellungen; halbe Teilung an der Antriebswelle 4 Paare mit 109,95 / 80,54 / 58,45 / 0,34 mm³; je Schritt höchstens 2,07 s. Speicher abweichend: +364 und +123 MB in den ersten zwei Schritten, danach flach | strenge Kollision bleibt; einmaliger Anstieg ~0,5 GB je Bewegungsprüfung dokumentiert; `SPEICHER_KNAPP` der Referenz auf frischem SolidWorks → Nutzer erneut fragen (**Nutzer 2026-10-05: „Annehmen, weiter“**, S14b-Z9) | Scheinkollision: Alternativen Abmaß −0,1 oder Volumenschwelle |
| 10 | „Grenze wirkt“ durch die Kette | bestätigt: Schritt auf HUB + 3,75 meldet Code 47, Zahnstange bleibt bei HUB | Kriterium über die Lage unverändert (S14b-Z10) | – |
| 11 | Aufsummierte Drehung | bestätigt: 171,8873° / −85,9437° bei HUB 60, Abweichung 0,0000° | Plan-Code bleibt (S14b-Z11) | Konvention prüfen |
| 12 | Bild entlang der Radachse | bestätigt: PNG 278 769 Byte, `ViewZoomToSelection` ohne Fehler | Plan-Code bleibt (S14b-Z12); der Zoom zeigte im Referenzlauf aber den Eingriff nicht (Task 12b, Abschnitt 8) | `ViewZoomtofit2` |
| 13 | Speichern und Neuöffnen | bestätigt: Kopplungen vorhanden, mit dem Antriebsweg der Prüfung Zahnstange +30/+60 mm → Ritzelwelle +85,9437°/+171,8873°, Antriebswelle −42,9718°/−85,9437°, Abweichung 0; Status 3/2/2/3/2 ohne, alle 3 mit Antrieb. Die erste Messung (Vorzeichen entgegengesetzt) war ein Artefakt der Probe `SetTransformAndSolve2` an der Zahnstange | bestätigt (S14b-Z13), keine Nutzerfrage nötig | Datei nach Speichern unbrauchbar (vgl. S13c) |

Speicher des Spikes (nicht frisch: 1908 MB Vorlast): Spitze 4826 MB beim Neuöffnen; Nachtrag Zeile 13: 426 → Spitze 5052 MB (Öffnen
426 → 4884 MB).

## 4. Teile (Etappe 1)

### 4.1 Teil-Referenzen Zahnstangentrieb (Task 6)

`tests/referenz/zahnstangentrieb/` (sieben Teil-Specs: Grundplatte, Leiste, Schlitten, Zahnstange, Lagerbock, Ritzelwelle,
Antriebswelle; Eingabe `eingabe/beschreibung.md`). `validieren` aller sieben: `gueltig: true`, `hinweise: []`. Keine
Bauweg-Änderung nötig: alle drei Teile bestanden im ersten Anlauf.

Regressionstest `test_referenz_besteht` je Teil einzeln (`--zeit 600`), Private Bytes vorher → Spitze → nachher:

| Teil | Ergebnis | Dauer | Private Bytes (MB) |
|---|---|---|---|
| Zahnstange (m 2, z 30) | OK | 39 s | 418 → 3423 → 1065 |
| Ritzelwelle (Ritzel z 20, Rad z 25) | OK | 68 s | 889 → 4281 → 2527 |
| Antriebswelle (Rad z 50) | OK | 64 s | 426 → 4002 → 2246 |

Prüfer-Läufe (`swki bauen` + `swki pruefen`, je Lauf 1, Urteil durch den Prüfer-Agenten): `bestanden: true`, 0 Mängel, Urteil je
`{"bestanden": true, "maengel": []}`; `swki status` je Teil: Lauf 1 `pruefer: bestanden`. Sichtprobe Ritzelwelle (iso): Verzahnung
sauber. Aufträge und Arbeitsordner danach gelöscht.

| Teil | Bauen | Bauen + Prüfen | Private Bytes (MB) vor → nach Bauen → nach Prüfen | Prüfer-Urteil |
|---|---|---|---|---|
| Zahnstange | 25 s | 36 s | 426 → 1005 → 1042 | bestanden |
| Ritzelwelle | 36 s | 65 s | 892 → 2286 → 2482 | bestanden |
| Antriebswelle | 39 s | 65 s | 429 → 2043 → 2239 | bestanden |

### 4.2 Negativfall E1 (Zahnweite)

`tests/live/test_live_verzahnung.py::test_negativ_zahnweite`: der Bau verfälscht das Zahndickenabmaß der Antriebswelle um
−0,05 mm (Spec bleibt unverändert); erwartet genau `{verzahnungen}`, Knoten `z1`, Abweichung „zahnweite W6“. **OK**, 67 s,
Private Bytes 431 → 4015 → 2222 MB. Das Volumen ändert sich nur um −0,13 % (unter der Toleranz 0,5 %); es gab keinen `volumen`-Mangel.

### 4.3 Regression der Teile ohne Verzahnung (Etappe 1)

Einzeln (`--zeit 600`), SolidWorks frisch, Grenze vor einem Lauf 3000 MB: Buchse OK 32 s (427 → 3292 → 927 MB), Formplatte OK 49 s
(927 → 3507 → 1175 MB), Auswerferhalteplatte OK 77 s (1175 → 3851 → 1384 MB). Die Regression der ganzen Stufe steht in Abschnitt 7.

### 4.4 Zeit und Private Bytes je Radbau

Zeit je Feature `verzahnung` aus dem Bauprotokoll (`knoten[].dauer_s`), Private Bytes vor/nach `swki bauen` des ganzen Teils:

| Rad | Zeit Feature | Private Bytes (MB) |
|---|---|---|
| z 20 (Task 4, Teil mit Rad) | Testdauer 14,3 s warm, 22,9–23,5 s mit Kaltstart | Spitze 3,5–3,8 GB |
| z 50 (Antriebswelle, Wegwerf-Auftrag) | **19,7 s** (z1; ganzes `bauen` 29,6 s, davon Vorbereiten 1,5 s, Bauen 27,0 s, Speichern 1,0 s) | 1169 → 2596 (+1427, Dokument und Rad zusammen) |
| Zahnstange z 30 (Task 5) | 8,7 s | Spitze 3,7 GB |

Das Ziel „Rad z ≤ 50 < 15 s“ und „< 300 MB“ ist **nicht erreicht**; die Zeit liegt im COM-Overhead je Punkt (~0,4 s je Zahn). Folge:
Hinweis im Skill `konstruieren` (Bauzeit, +1,4–1,8 GB je Teil mit Rad, Neustart nach jedem Teil mit Rädern in Live-Serien).

## 5. Referenz Zahnstangentrieb und Getriebeprobe

`tests/referenz/zahnstangentrieb/zahnstangentrieb.yaml`: Hub 120, Zahnstange m 2 / z 30, Ritzel z 20 (Ø 40), Räder z 25 und z 50,
Achsabstand 75; Grundplatte, zwei Leisten, Schlitten mit Zahnstange (Gruppe mit Grenze 0 … HUB), zwei Lagerböcke, Ritzel- und
Antriebswelle als Scharnier mit Anlage und `gekoppelt`; Kopplungen `k1` (zahnstange) und `k2` (zahnrad); Bewegung *Schlittenhub*
mit Endlagen für Schlitten, Zahnstange und beide Wellen (Winkel mit `pi`). Werkstoff der Zahnteile 1.0503 (C45).

- **Getriebeprobe** (`tests/live/getriebeprobe/`, Spike S14b und Live-Tests der Tasks 11/12): Bau 226 s, Spitze 5018 MB (Task 11);
  Prüfung bestanden 311 s, Spitze 6708 MB (Task 12), Gegenprobe nach Fix T13-1 309 s / 6859 MB, nach Task 12b 314 s / 6802 MB.
- **Lauf 1 der Referenz** (`test_referenz_besteht`): ein Mangel `freiheitsgrad:antriebswelle` (mit Antrieb unterbestimmt), 525 s,
  Spitze 9819 MB, kein `SPEICHER_KNAPP`. Diagnose (Lauf 2, 410 s, Spitze 10156 MB): mit Antrieb liest `GetConstrainedStatus`
  die Antriebswelle als 2, auch nach `EditRebuild3`; nach `ForceRebuild3(False)` 3; ohne Antrieb 2; statisch alle 3. Der Bauweg war
  richtig, die Statusablesung über die Kopplungskette veraltet. Fix `759eb14` (Ruling T13-1): `SwMechanik.status()` ruft vorher
  `ForceRebuild3(False)`.
- **Danach** (Task 13): Referenz live OK 489 s, Spitze 10215 MB (über `speicher_grenze_mb`, kein `SPEICHER_KNAPP`).
  Prüferlauf `REF-4B-TRIEB`: bauen 361 s (Spitze 10272 MB allein beim Bau), pruefen 137 s (Spitze 7088 MB), `maengel: []`,
  **Prüfer-Urteil `{"bestanden": true, "maengel": []}`** (sonnet, unverändert geschrieben).
- **Eingriffsbild:** die Sichtprobe von `k2-eingriff.png` zeigte den Lagerbock vor den Eingriffsstellen (Spec §5.7 verfehlt). Task 12b
  (`b78fa42`): `kopplungsbild` blendet alle Komponenten außer Seite a/b aus, prüft die Auswahl (`Select4`) und fällt sonst auf
  `ViewZoomtofit2` zurück; live an der Getriebeprobe belegt, Sichtprobe: Zahn in Lücke, nur die zwei Räder.

## 6. Negativfälle (Task 14)

`tests/live/test_live_zahnstangentrieb.py`, je einzeln auf frischem SolidWorks, `--zeit 900`, Herstellung per monkeypatch im Bau
(Spec bleibt unverändert und gültig):

| Fall | Erwartete Mängelmenge (= gemessen) | Dauer | Spitze Private Bytes |
|---|---|---|---|
| 1 `zahnphase_versetzt` (halbe Teilung an `k2`, `TOL_PHASE` 1,0) | `{kollision}` (Antriebswelle/Ritzelwelle) | 495 s | 10253 MB |
| 2 `drehrichtung_umgekehrt` (`REVERSE["zahnrad"]` True) | `{bewegung_kollision, sollweg:antriebswelle, endlage:antriebswelle}` | 482 s | 10244 MB |
| 3 `kopplung_fehlt` (ohne `k2`): erster Lauf abweichend, Erwartung erweitert (T14-1) | `{verknuepfungen, kollision}` (Knoten `k2` bzw. Antriebswelle/Ritzelwelle); `bewegung:Schlittenhub` `ok=None` | erster Lauf 405 s (10093 MB, Menge `{verknuepfungen, kollision}` gegen die damalige Erwartung `{verknuepfungen}`, abweichend); Wiederholung 435 s (OK) | 10105 MB |
| 4 `uebersetzung_verfaelscht` (Zähler × 1,1) | `{eingriff:k2, sollweg:antriebswelle, endlage:antriebswelle, bewegung_kollision}` | 505 s | nicht belegt (Abtaster-Fehlstart) |

Fall 3: ohne `k2` entfällt auch die Zahnphase der Antriebswelle (Präzisierung 17); die Welle steht in der Einbaulage, ihre Zähne
liegen auf denen der Ritzelwelle (vier Paare 69,22 / 61,38 / 18,99 / 3,51 mm³), die strenge Kollisionsprüfung meldet das zu Recht.
Die Erwartung wurde um `kollision` erweitert (strenger, nicht abgeschwächt) und der Fall nach Fall 4 erneut gefahren (Wiederholung
OK). E1 (Abschnitt 4.2) kommt als fünfter Negativfall dazu.

## 7. Regression (Task 15, Step 5)

Je Fall einzeln (`tests\live_einzeln.py`, `--zeit 900`, `PYTHONIOENCODING=utf-8`), Private Bytes vorher → Spitze (0,5-s-Abtastung)
→ nachher. **Ergebnisse folgen** (Controller fährt die Regression).

| Fall | Ergebnis | Dauer | Private Bytes vorher → Spitze → nachher | SolidWorks |
|---|---|---|---|---|
| Teile: `buchse`, `formplatte`, `auswerferhalteplatte`, `zahnstangentrieb-zahnstange`, `-ritzelwelle`, `-antriebswelle` | folgt | folgt | folgt | folgt |
| `stehlager-stehlager` | folgt | folgt | folgt | folgt |
| `schlitten-linearschlitten` | folgt | folgt | folgt | folgt |
| `zahnstangentrieb-zahnstangentrieb` | folgt | folgt | folgt | folgt |
| Linearschlitten-Negativfälle (4, mit `sollweg:`) | folgt | folgt | folgt | folgt |
| `test_live_baugruppe.py::test_probe_besteht_pruefung` | folgt | folgt | folgt | folgt |
| `test_live_bewegung.py` | folgt | folgt | folgt | folgt |
| volle Live-Suite (`tests\live`) | folgt | folgt | folgt | folgt |

Unit-Suite: **835 passed, 133 deselected**.

## 8. Abweichungen von der Spec

Präzisierungen und Rulings des Controllers aus dem Ledger der Umsetzung. **Dieser Abschnitt ist der dauerhafte Nachweis**: der
Ledger (`.superpowers/sdd/2026-10-05-stufe-4b-verzahnung-kopplungen/`) ist nicht versioniert. Die Spec 4b ist an den Stellen
nachgezogen („*Nachgezogen bei der Umsetzung, 2026-10-05*“: §4.2, §4.4, §4.5, §5.2, §5.4–§5.8, §9, §10, §11, §12). Je Ruling:
Entscheidung, Grund, „wenn falsch“. Die Spike-Rulings stehen in den Abschnitten 2 und 3.

**Preflight (vor Task 1)**

- **P1 (Fehlende Verknüpfung als statischer Fehler):** Task 12 erweitert `_statisch_fehlerhaft`, sodass auch eine in der Spec erwartete,
  im Modell fehlende Verknüpfung zählt (wie fehlerhaft/unterdrückt, `fremd` nicht); Spec §10 Fall 3 und §5.5 verlangen „Bewegungsprüfung
  läuft nicht, ok=None“. Umgesetzt als T12-2. Wenn falsch: Fall 3 meldet zusätzlich Bewegungsmängel; Rückbau eine Zeile.
- **P2 (Fall 3 kann `kollision` melden):** vorab vermerkt, live bestätigt, entschieden als T14-1.
- **P3 (Schlitten-Negativfall `test_umgekehrte_richtung`):** bekommt voraussichtlich `sollweg:`-Mängel; Task 15 hält dann an, der
  Controller entscheidet (keine Vorab-Änderung). Ergebnis siehe Abschnitt 7.
- **P4 (`KOPPLUNG_REIHENFOLGE`):** Komponenten ohne Eintrag in `freiheitsgrade` sind statisch voll bestimmt (fest), mit `1` Grenze
  bzw. Gruppe; nur `gekoppelt` kann „noch nicht fest“ sein; „Seite a muss gekoppelt sein“ folgt aus dem Drehen in Phase. Spec §5.2
  nachgezogen. Wenn falsch: eine zu lockere oder strenge Validierung, keine Bauschäden.
- **P5 (`groesste_abweichung`):** Task 10 ergänzt das Feld in `sollweg:` (Spec §5.8), aufsummierte Drehungen stehen in
  `endlage.ist.aufsummiert`. Wenn falsch: kostet ein Feld.
- **P6 (Spec-Nachzug):** Bezugsachse nach Spike, Modulpfad `swki/verzahnung.py`, §11 Skill `baugruppe` §7, §5.2, §5.8. Erledigt.
- **P7 (Reviewer-Befunde zu Duplikaten/privaten Importen):** je Task entschieden, Vorzug kleine Wiederverwendung ohne Kreisimport.
  Kosten: Kosmetik.
- **P8 (Zeitlimits, Trailer):** Teil-Live-Tests 300/600 s, Baugruppen-Live-Tests 900 s. Keine Kosten.
- **P9 (Versatzebene mit Abstand 0):** scheitert in Task 4 Test 3 die Versatzebene live, gilt die Standardebene `oben`. Trat nicht auf.

**Rulings zu den Tasks**

- **T4-1 / T4-2 (S14a-Z2/Z5):** affine Abbildung und `MultiSelect2` im Handler (kein zusätzlicher Unit-Test; Gegenprobe und Live-Tests
  sichern es); `dispatch_array` schon in Task 4. Wenn falsch: Profil verzerrt → Gegenprobe/Live-Volumen schlagen an.
- **T5-1 (S14a-Z3):** Zahnweite per Strahl statt `IMeasure`. Wenn falsch: Zahnweite misst falsch, Live-Test `[stirnrad]` schlägt an.
- **S14a-Z5-Folge:** Rad z 50 braucht live 19,7 s (> 15 s): Hinweis im Skill `konstruieren`, Referenz bleibt. Wenn falsch: nur ein
  Hinweistext.
- **T7-1 / T7-4 (Duplikate in der Kopplungsrechnung):** `_sk`/`_diff` → `anker.skalar`/`anker.differenz`; `_punkt`/`_richtung` bleiben lokal
  ohne Maßstab (swki fügt Komponenten nie skaliert ein). Wenn falsch: skalierte Komponenten (kommen nicht vor) falsch gerechnet.
- **T7-2:** zusätzlicher Unit-Test σ = −1 (Ritzel unter der Stange), Erwartung von Hand. Kosten: nur die Testzahl.
- **T7-3:** Commit-Nachricht von `7331682` per `--amend` korrigiert (lokal, ungepusht).
- **T11-Vorgabe / T12-1 (S14b-Z6):** Unit-Tests und `eingriff` vergleichen die Übersetzung als ungeordnetes Paar (min/max), der
  Meldetext bleibt „Übersetzung 110:50 statt 100:50“; ohne das meldet die Referenz live fälschlich `eingriff:k2`.
- **T12-2 (P1):** fehlende, in der Spec erwartete Verknüpfungen zählen als statischer Fehler (+1 Test).
- **T9-1 (plan-mandated):** `lade_standard()` in `_kopplung_bewegung_befunde`, Schrittvorgabe an drei Stellen und
  `antriebsmenge` ≈ `plausibel._gruppe` bleiben wie im Plan-Code (kein Fehlverhalten, Umbau berührt spätere Ersetzungen); an das
  Gesamt-Review zur Triage. Wenn falsch: kleine Wartungsschuld.
- **T13-1:** `SwMechanik.status()` ruft vor dem Lesen `ForceRebuild3(False)` (API nachgeschlagen: 1 Parameter, seit 2001), Test
  zuerst (+1 Unit-Test). Wirkt auf **alle** Bewegungsprüfungen. Wenn falsch: zusätzlicher Rebuild je Statusablesung (2 × je Bewegung)
  kostet Zeit und Speicher; die Ablesung könnte trotzdem stale sein → Fall erneut vorlegen. Die 4a-Referenzen (Stehlager, Schlitten)
  sind nach dem Fix noch nicht live gelaufen: Regression Abschnitt 7; bei Zeit-/Speicheranstieg `ForceRebuild3` auf Bewegungen mit
  Kopplungen beschränken (T13-3).
- **T13-2 / Task 12b:** Das Eingriffsbild verfehlte Spec §5.7; `kopplungsbild` blendet übrige Komponenten aus. Wenn falsch: der
  Prüfer sieht den Eingriff nicht und prüft über den Prüfbericht.
- **T14-1 (Fall 3):** Erwartung auf `{verknuepfungen, kollision}` erweitert (Abschnitt 6, Spec §10). Wenn falsch: Fall 3 könnte bei
  anderer Einbaulage ohne `kollision` laufen (Test rot); Alternative: nur das `CreateMate` von `k2` unterlassen und die Phase
  behalten.
- **Speicher (S14b-Z9, Nutzer):** strenge Kollision bleibt, Anstieg ~0,5 GB je Bewegungsprüfung dokumentiert. Die Referenz-Spitzen
  liegen bei 10,1–10,3 GB (Abschnitte 5, 6). Wenn falsch: `SPEICHER_KNAPP` auf frischem SolidWorks → Nutzer erneut fragen.

## 9. Offene Punkte

- **Speicher an der Grenze:** Zahnstangentrieb und Negativfälle Spitzen ~10,1–10,3 GB bei `speicher_grenze_mb` 10000, ohne
  `SPEICHER_KNAPP`, weil die Abfrage nur das Dauerniveau sieht (wie 4a). Das Speicherpaket (Ergebnisse 4a, Abschnitt 7) ist
  weiterhin offen und wird wichtiger; Kandidat für die Nutzerwahl nach 4b.
- **Rechner B (SW 2026) ungetestet.**
- **Zeit je Radbau:** Ziel < 15 s (z ≤ 50) verfehlt (19,7 s), Streuung der Skizzenzeit (Faktor 2,5) ungeklärt; Lücke + Kreismuster
  nur nach erneuter Entscheidung.
- **Zahnweite per Strahl** live nur für `winkel` 0 und Ebene „vorne“ belegt (`winkel` ≠ 0, „oben“ + `umkehren` nur hergeleitet).
- **Rücklesen der Kopplungen:** Ob der Tausch von Zähler/Nenner und `Reverse = true` an k1 von der Reihenfolge der Entitäten abhängt,
  ist nicht untersucht; `Reverse` wird nie geprüft (Präzisierung 12).
- **Zahnphase nur über `SetTransformAndSolve2`;** Referenz ohne Befestigung der Lagerböcke (Spec nennt keine, Speicher).
- **Vereinfachtes Profil:** Fußrundung ohne Trochoide, Knick bei z ≥ 42 unter dem aktiven Profil (Spec §14); Modulreihe 25 … 50
  gesperrt (nur eine Quelle).
- **4a-Folgepakete:** das Paket „Messarten“ (Fasen, Gewinde durch, Lagerachse), Änderung von `HUB` direkt im SolidWorks-Modell,
  Deferred Minors aus 4a bleiben offen (Ergebnisse 4a, Abschnitt 7).
- **Deferred Minors 4b** (Ledger, grob): Task 2: Spike-`_flanken` nimmt beim Spline 40 Fußebenen mit, `SPEICHER_GRENZE_MB` 5500 im
  Spike; Task 4: Docstring `test_live_verzahnung` nennt Messung/Negativfall, die erst Task 5/6 ergänzen; Task 8: Spike schreibt
  „gesetzt“ nicht ins JSON, Bild nur über die Dateigröße geprüft, Lauf 2 nicht frisch, Spike legt globale Variablen nicht an
  (Produktionscode ja); Task 9: Triage T9-1 (Duplikate); Task 12b: Wiederherstellung der Sichtbarkeit nicht je Komponente
  abgesichert, Lesen von `Visible` außerhalb von `try`, kein Test für den Filter von `_kopplungsbilder`, Fallback nur per Attrappe,
  n × m COM-Aufrufe je Kopplung.
- **Kandidaten nach 4b:** Stufe 4c (Nut- und Kurvenverknüpfung), Paket „Messarten“, Paket Speicher – der Nutzer wählt.

## Stand

- Datum: 05.10.2026, Rechner A (SOLIDWORKS 2025), Branch `stufe-4b` (von `plan-stufe-4b` @ 295213d). Ohne Push. Commits seit `main`
  (`git log --oneline main..HEAD`); der Doku-Commit von Task 15 folgt nach der Regression.

| Task | Inhalt | Commits |
|---|---|---|
| Plan | Spec, Plan, Übergabe | 30ad9b4, 99e35b0, 295213d |
| 1 | Geometrie `swki/verzahnung.py`, Bezugsprofil, Lage im Teil | 6de5a4c |
| 2 | Spike S14a und Nachtrag | 7182e3f, 023526d |
| 3 | Format, Befunde, Hinweise, Sollvolumen, `pi` | dadd241 |
| 4 | Handler `verzahnung` | e3d04e8 |
| 5 | Teilprüfung `verzahnungen` | 4a640e5 |
| 6 | Teil-Referenzen, E1, Prüfer, Skill; Fix-Runde Ergebnisse | 66f8a36, 493ca8f |
| 7 | Kopplungsrechnung `swki/baugruppe/kopplung.py` und zwei Fix-Runden | d9ede01, c89d401, fe6a04a |
| 8 | Spike S14b und Nachtrag Zeile 13 | 7159b8f, 7df4c3f |
| 9 | Format und Plausibilität der Kopplungen, `gekoppelt`, `GRENZE_REFERENZ` | 038d0f8 |
| 10 | Sollweg je Stellung, aufsummierte Drehung, gekoppelte Freiheitsgrade, Reste aus 4a | e259ec5 |
| 11 | Kopplungen bauen (Zahnphase, `CreateMate`, Rücklesen) | c09a98d |
| 12 | Eingriff, unterdrückte Verknüpfungen, Bilder, Bericht | 0f6e21a |
| 13 | Referenz Zahnstangentrieb, Prüfer-Checkliste; Fix T13-1 | 6cc810c, 759eb14 |
| 12b | Kopplungsbild blendet übrige Komponenten aus | b78fa42 |
| 14 | Negativfälle am Zahnstangentrieb | e73084f |
| 15 | Skill, CLAUDE.md, Design §11, Spec-Nachzug, Ergebnisse, Regression | folgt |
