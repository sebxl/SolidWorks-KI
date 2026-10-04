# Stufe 4a – Ergebnisse (Bewegungen)

Fertig-Kriterium Spec 4a §14 für Rechner A (SW 2025): Der Linearschlitten (Grundplatte, zwei Führungsleisten, Schlitten, Hebel,
Drehbolzen, vier Schrauben; 22 Verknüpfungen, zwei Bewegungen) besteht ohne Code-Mangel mit Prüfer-Urteil „bestanden“; die vier
Negativfälle liefern genau ihre erwartete Mängelmenge; die Bestandsreferenzen bestehen weiter. 700 Unit-Tests grün. Rechner B
(SW 2026) offen.

## 1. Kurzfassung

Was 4a kann:

- **Grenzverknüpfungen** `grenze_abstand` (mm) und `grenze_winkel` (Grad) mit `min`/`max` als Parameter oder `0`
  (`GRENZE_FESTE_ZAHL` sonst); bewegt wird Seite `a`.
- **Scharnier** als zwei Verknüpfungen (`konzentrisch` ohne Drehsperre und `deckungsgleich` als Anlage `<id>.anlage`),
  Passung Drehbolzen ISO 8734 ↔ Bohrung der drehenden Komponente.
- **`freiheitsgrade: 1`** je bewegter Komponente oder Gruppe, genau eine Bewegung treibt sie.
- **`bewegungen`** mit Grenze, `schritte` und erwarteten Endlagen (Verschiebung bzw. Drehung um Achse); eine Prüfsumme der
  Freigabe schützt sie.
- **Bewegungsprüfung** in `swki pruefen`: Freiheitsgrad belegt, Grundstellungslauf je Bewegung mit Kollision je Stellung,
  „Grenze wirkt“, Endlagen, Paarläufe für Bewegungen mit sich schneidenden Räumen, Iso-Bilder `<Bewegung>-min|mitte|max` und
  `-kollision-…`; Speicherschutz `SPEICHER_KNAPP`.
- `bauen` legt jede Grenze mit `min` an (Grundstellung, Prüfung über Maß `D1`), Skill `baugruppe` §6, Prüfer-Anweisung,
  Referenz `tests/referenz/schlitten/`.

Testzahlen: Unit-Tests 622 → **700 bestanden**, abgewählt (Live, `sw`-markiert) 109 → **116**. Zuwachs je Task (bestanden): Task 2
+12 (634), Task 3 +26 (660), Task 4 +17 (677), Task 5 +8 (685), Task 6 +9 (694) und +1 aus der Fix-Runde (695), Task 7 +3 (698),
Task 8 +2 (700), Task 9 ±0 (700); Tasks 1 und 10 ohne neue Unit-Tests. Abgewählt (Live-Tests): +1 Task 6, +1 Task 7, +1 Task 8 (Referenzeintrag Schlitten),
+4 Task 9 (Negativfälle), zusammen 109 → 116. `swki api pruefe-code`: keine Befunde.

Live-Ergebnisse: Referenz Linearschlitten bestanden (Prüfer-Urteil `{"bestanden": true, "maengel": []}`), vier Negativfälle 4/4 mit genau
der erwarteten Mängelmenge, Regression: siehe Abschnitt 5.

## 2. Spike S13 (Task 1) – Ergebnis und Entscheidung je Zeile

Spike `spikes/s13_bewegung.py` (`docs/stufe0/ergebnisse/s13_bewegung.json`), Nachtrag S13b (`s13b_bewegung.json`, Blöcke E, E100, AB, C,
D) und S13c (`s13c_winkelgrenze.json`, E1–E10). SolidWorks 2025. Alle Entscheidungen standen vorab im Ledger („Ruling“).

| Z. | Frage | Ergebnis (gemessen) | Entscheidung |
|---|---|---|---|
| 1 | `AddMate5` Typ 5/6 mit Grenzen | bestätigt: Abstand `g1` 0…100 Status 1, `MinimumVariation` 0, `MaximumVariation` 0,1 m; Winkel `g2` 0…90° (1,5708 rad) | Plan-Code bleibt |
| 2 | Maßnamen der Grenzen, Gleichung | abweichend: nur **ein** Maß `D1` (= aktueller Wert, = `min`); `D2`/`D3` fehlen. Direkte Gleichung auf `D2@g1`/`D3@g1`: `Add2` gibt −1 (abgelehnt); `D1@g1 = "HUB"` wird angenommen, Min/MaxVariation sind relativ zu `D1` (S13b D) | `GRENZ_MASSE = {}`: Werte kommen beim Bau aus den Parametern, Schutz über die Freigabe |
| 3 | Antrieb neben der Grenze, Verhalten über der Grenze | bestätigt: innerhalb Weg = Wert; über `max` Rebuild-Meldung `Code 47` (`swFeatureErrorMateIlldefined`) **und** Lage bleibt bei `max`; zurück auf `max` wieder gelöst | „Grenze wirkt“ = Fehlercode 47 und Lage bleibt; `_zurueck` ohne Neuanlage |
| 4 | Bestimmtheit | abweichend: mit Grenzen **immer 3/3/3/3** (auch ohne Antrieb), nie 2. S13b A: ohne Grenzen/Antrieb Schieber/Bolzen/Hebel 2; B: `SetSuppression2` unterdrückt Grenzen verlustfrei (Lage ±2e-17), unterdrückt 2, mit Antrieben 3, entdrückt wieder 3 und Grenze wirkt; C: ohne `v2` (Negativfall 4) Schieber/Bolzen/Hebel immer 2 | Freiheitsgrad wird mit **unterdrückten** Grenzen gelesen (`Mechanik.unterdruecke`); Mitfahrer melden wie ihr Träger |
| 5 | Antrieb löschen | bestätigt: Lageabweichung 0,0; SHA-256 der Dateien nach Schließen ohne Speichern gleich | keine Kosten |
| 6 | `GetBox(False, False)` | bestätigt, identisch zur Rechnung aus Teilebox und `Transform2` (Abweichung 0,0 mm) | `kiste()` aus Teilebox (je Komponente gecacht) und `Transform2`, kein `GetBox` je Schritt |
| 7 | Drehsinn | abweichend: Achse **[0, −1, 0]** (+x → +z), nicht +y; Winkelantrieb an +z/+z, `gleich` | Endlage der Probe und der Referenz auf Achse `[0, -1, 0]`; Negativfall 1 mit Anschlag auf der rechten Leiste (+z) |
| 8 | Zeit und Speicher je Schritt | abweichend: Probe (4 Komponenten) 0,69 s und +12,3 MB je Schritt (S13b E: 0,60 s, +19,6 MB), ~100 Komponenten 4,36 s und +8,9 MB (S13b: 3,69 s, +18,6 MB); Bau der drei Teile 2,1–2,4 GB, Probe-Aufbau ~275 MB, 96 Stifte +1023 MB (10,7 je Stift) | `bewegung_schritte: 8`, `speicher_grenze_mb` zunächst 3500 (später 5000, 8000, 10000, siehe unten) |
| 9 | Iso-Bild mit aktivem Antrieb | bestätigt (PNG 231 875 Byte, Dokument bleibt offen) | keine Kosten |

Spike S13c (Task 7, Diagnose): Eine Winkelgrenze ist nach Speichern und Neuöffnen faktisch 0…0 (Code 47 schon bei 22,5°), wenn vor dem
Speichern **beide** treibenden Verknüpfungen angelegt und gelöscht wurden (E6); ohne Antrieb (E1) oder mit nur einem (E7, E10) geht sie;
Flip am Antrieb (E8) hilft nicht, entgegengesetzter Antrieb (E9) ist unbrauchbar. Die API zeigt den Defekt nicht
(`Alignment`, `Flipped`, `Min/MaxVariation`, `D1` unverändert). Folge: `bauen` legt keine Hilfsverknüpfungen an, die Grundstellung
entsteht beim Anlegen der Grenze mit `min` und wird über Maß `D1` geprüft.

Gesetzte Vorgaben: `bewegung_schritte: 8`; `speicher_grenze_mb: 10000` (Nutzerentscheidung, Abschnitt 6).

## 3. Referenz Linearschlitten (Task 8)

`tests/referenz/schlitten/` (`grundplatte`, `leiste` (links/rechts), `schlitten`, `hebel`, `linearschlitten`, Eingabe
`beschreibung.md`); Bewegungen *Schlittenhub* (Abstand 0…220 mm, Schlitten, Hebel und Drehbolzen fahren mit) und *Hebelschwenk*
(Winkel 0…90°, Hebel um den Drehbolzen, Achse [0, −1, 0]). Keine Bauweg-Änderung nötig: der Live-Lauf bestand im 1. Anlauf.

- **Lauf:** `test_referenz_besteht[schlitten-linearschlitten.yaml]` OK in 217,6 s (Validieren, Freigeben, Bauen, Prüfen), `maengel: []`,
  keine Hinweise. 22 von 22 Verknüpfungen, Masse 7,9967 kg, Hüllquader 300 × 55 × 100 ist = soll.
- **Bewegungsläufe** (je 9 Stellungen, 0 Kollisionen): Schlittenhub 22,96 s, Hebelschwenk 22,94 s, Paarlauf Schlittenhub (Hebel auf max)
  18,55 s, Paarlauf Hebelschwenk (Schlitten auf max) 18,33 s. Paare: genau eines (Schlittenhub × Hebelschwenk), Schnitt
  (−141,314, 45, −11,314)…(−77,438, 55, 30). Bewegte Menge Schlittenhub {drehbolzen, schlitten, hebel}, Hebelschwenk {hebel}.
- **Endlagen** (ist / soll): Schlitten [220, 0, 0] / [220, 0, 0]; Hebel [220, 0, 0] / [220, 0, 0]; Hebel Drehung um [0, −1, 0] 90,0° / 90°.
- **Freiheitsgrade:** `freiheitsgrad:schlitten` und `freiheitsgrad:hebel` je `ohne_antrieb` 2 / `mit_antrieb` 3, beide ok.
- **Gewindepaarungen:** 4 gleiche, Einschraublänge 8,6 mm, Volumen ist 106,594 = soll 106,594 mm³ (Gewindetiefe 12, Tiefe 16).
- **Prüfer-Urteil** (Task 8, Step 11, opus, Lauf 2 durch den Controller auf frischem SolidWorks nach `speicher_grenze_mb` 8000):
  `{"bestanden": true, "maengel": []}`; `swki status`: Lauf 2 bestanden. Bau 116 s, Prüfen 120 s, Läufe Hub 23,2 s, Schwenk 29,9 s,
  Paarläufe 16,8 s und 8,0 s, Spitze 7816 MB. Auftrag und Arbeitsordner anschließend gelöscht.
- **Speicher:** siehe Abschnitt 6 (Task-8-Live 4031 MB bei 2-s-Abtastung gegenüber 7816 MB bei 0,5 s – nicht aufgeklärt).

## 4. Negativfälle (Task 9)

`tests/live/test_live_schlitten.py`, je einzeln, `--zeit 900`, genau die erwartete Mängelmenge (keine Erwartung angepasst):

| Fall | Erwartete Mängelmenge (= gemessen) | Dauer | Private Bytes vorher → Spitze → nachher |
|---|---|---|---|
| 1 `test_stellungskollision` (Anschlag auf rechter Leiste, L 24) | `{bewegung_kollision:Hebelschwenk, bewegung_kollision:Schlittenhub}`, Grundstellungsläufe 0 Kollisionen | 311 s | 426 → 10153 → 4886 MB |
| 2 `test_grenze_im_modell_zu_weit` | `{grenze:Schlittenhub}` | 272 s | 426 → 7921 → 2498 MB |
| 3 `test_umgekehrte_richtung` | `{endlage:Schlittenhub:schlitten, endlage:Schlittenhub:hebel}`, ist [−220, 0, 0] | 274 s | 428 → 8190 → 2774 MB |
| 4 `test_zweiter_freiheitsgrad` | `{freiheitsgrad:schlitten, freiheitsgrad:hebel, bestimmtheit}` (vorhergesagt, jetzt gemessen) | 258 s | 426 → 9640 → 4312 MB |

Fall 1: Spitze 10153 MB knapp über der Grenze 10000, die Abfrage (Dauerniveau zwischen den Läufen) traf sie nicht, kein `SPEICHER_KNAPP`.
Fall 4 brauchte eine Wiederholung auf frischem SolidWorks, weil der Teilbau der Referenzleiste sporadisch mit `REBUILD_FEHLER –
Gleichungen: Code 1` scheiterte (Abschnitt 7).

## 5. Regression (Task 10)

Je Fall einzeln (`tests\live_einzeln.py`, `--zeit 900`, `PYTHONIOENCODING=utf-8`), Private Bytes von `SLDWORKS.exe` vorher → Spitze
(Hintergrundabtastung alle 0,5 s) → nachher. Alle sechs Fälle OK, kein Fall musste angepasst oder wiederholt werden.

| Fall | Ergebnis | Dauer | Private Bytes vorher → Spitze → nachher | SolidWorks |
|---|---|---|---|---|
| `test_referenz_besteht[buchse-buchse.yaml]` | OK | 30 s | 422 → 3293 → 1008 MB | frisch (PID 35352), gemeinsam mit den nächsten beiden |
| `test_referenz_besteht[formplatte-formplatte_ds.yaml]` | OK | 43 s | 860 → 3511 → 1227 MB | wie oben |
| `test_referenz_besteht[auswerferhalteplatte-auswerferhalteplatte.yaml]` | OK | 73 s | 1079 → 3830 → 1495 MB | wie oben |
| `test_referenz_besteht[stehlager-stehlager.yaml]` | OK | 193 s | 425 → 10827 → 3837 MB | frisch (PID 15048) |
| `test_referenz_besteht[schlitten-linearschlitten.yaml]` | OK | 248 s | 422 → 9900 → 4510 MB | frisch (PID 19212) |
| `test_live_baugruppe.py::test_probe_besteht_pruefung` (3b-Probe, unverändert) | OK | 67 s | 428 → 6902 → 3213 MB | frisch (PID 7972) |

- **Neustarts:** vier (vor den drei Teile-Referenzen, vor Stehlager, Schlitten und 3b-Probe), jeweils durch den Controller; Ausgangswerte
  422–428 MB. Die drei Teile-Referenzen liefen zusammen auf einem SolidWorks, Spitzen unter 3,9 GB.
- **Spitzen der Baugruppenfälle** liegen bei 0,5-s-Abtastung zwischen 6,9 und 10,8 GB. Das gilt auch für die statische Baugruppe
  (Stehlager 10827 MB; 3b-Ergebnis 3,1–3,6 GB bei gröberer Abtastung) und liegt über `speicher_grenze_mb` 10000, ohne
  `SPEICHER_KNAPP`, weil die Abfrage nur das Dauerniveau zwischen den Läufen sieht (Abschnitt 7). Das Dauerniveau nach den Tests
  (3,2–4,5 GB) fällt nach dem Schließen auf 0,2–0,8 GB.
- Referenz Schlitten im Regressionslauf: 248 s (im Task-8-Lauf 217,6 s).

## 6. Abweichungen von der Spec

Präzisierungen und Rulings des Ledgers (Quelle: `.superpowers/sdd/2026-10-03-stufe-4a-bewegungen/progress.md`); die Spec 4a ist an den
Stellen nachgezogen (2026-10-04: §4.1, §7.2, §8.1, §8.2.2, §8.2.3, §8.4, §12).

- **Präzisierung 1 (Scharnier als zwei Verknüpfungen):** `konzentrisch` ohne Drehsperre und `deckungsgleich` (`<id>.anlage`) – ohne
  Anlage bleibt die Höhe frei (Einfügelage); Skill §6 verlangt `anlage_a`/`anlage_b`.
- **Präzisierung 13 (Negativfälle 1 und 4):** Fall 1 mit Anschlag auf der rechten Leiste (+z) und L 24 statt 20; Fall 4 erwartet
  `{freiheitsgrad:schlitten, freiheitsgrad:hebel, bestimmtheit}` statt `{freiheitsgrad:schlitten}` (Mitfahrer melden wie ihr Träger).
- **Ruling Z. 1:** bestätigt, keine Kosten.
- **Ruling Z. 2:** `GRENZ_MASSE = {}` – Grenzwerte lassen sich nicht per Gleichung binden (S13b D), Werte beim Bau aus den Parametern,
  Schutz über die Freigabe. Folge: eine Änderung von `HUB` im SolidWorks-Modell bewegt die Grenze nicht; die Änderungserkennung sieht sie nicht.
- **Ruling Z. 3:** bestätigt (über `max` Code 47 und Lage bleibt; zurück auf `max` gelöst); `_zurueck` ohne Neuanlage.
- **Ruling Z. 4:** `GetConstrainedStatus` zählt eine Grenzverknüpfung als Bindung; „Freiheitsgrad belegt“ mit unterdrückten Grenzen
  (`Mechanik.unterdruecke`, `fahre` liest `status_frei`/`status_gehalten`); statische 3b-Bestimmtheit bleibt streng, `freiheitsgrade: 1`
  erlaubt `unterbestimmt`. Risiko: ein Widerspruch Grenze/Antrieb zeigt sich nur über „Grenze wirkt“ und die Endlagen.
- **Ruling Z. 4 / Negativfall 4:** Mitfahrer melden wie ihr Träger; Fall 4 erwartet `{freiheitsgrad:schlitten, freiheitsgrad:hebel,
  bestimmtheit}` – vorhergesagt, in Task 9 live bestätigt.
- **Ruling Z. 5:** bestätigt (Lage 0,0, SHA gleich).
- **Ruling Z. 6 und 8 (Leistung):** `kiste()` aus Teilebox und `Transform2` statt `GetBox` je Schritt (~10 MB und 0,07–1,1 s je Schritt gespart).
- **Ruling Z. 7:** Drehsinn −y (+x → +z); Endlage der Probe und der Referenz auf Achse `[0, -1, 0]`, Negativfall 1 mit Flächen +z.
- **Ruling Z. 8:** `bewegung_schritte: 8`; Wachstum ~10–20 MB/Schritt als mäßig gewertet, `speicher_grenze_mb` zunächst 3500.
- **Ruling Z. 9:** bestätigt.
- **Kein Task-Review für den Spike (Task 1):** Wegwerf-Messcode ohne Produktionswirkung, Werte vom Controller gegen die Tabelle geprüft.
- **Task 5:** `Mechanik.unterdruecke`, `fahre` liest Status mit unterdrückten Grenzen, Attrappe zustandsabhängig (+1 Test → 685).
- **Task 6:** `GRENZ_MASSE = {}`, `kiste` aus Teilebox und Transform mit Cache in `SwMechanik`, `sw_baugruppe.unterdruecke` über
  `SetSuppression2(0/1, 1, None)`, +2 Unit-Tests (694).
- **Task 7:** `bewerte_bewegungen` ohne `statisch`; Fix der Grundstellung im Rahmen des Tasks (S13c): keine treibenden Verknüpfungen
  beim Bau, `_grundstellung` prüft Maß `D1` der Grenze gegen `min` (Spec §7.2 verlangte eine Hilfsverknüpfung, die nachweislich die
  Winkelgrenze in der gespeicherten Datei zerstört; Nutzervorgabe „im gebauten Modell innerhalb der Grenzen ziehbar“).
- **Speichergrenze:** `speicher_grenze_mb` 3500 → 5000 (Task 7: Grundbedarf von `bauen` und Statik der kleinen Probe 3,6–4,0 GB) → 8000
  (Task 8, Speicherdiagnose: Grundbedarf von `pruefen` für 4 Teile und Baugruppe 6,2–6,9 GB, Spitze 7015,8 MB beim Abbruch der Diagnose bei
  Grenze 9000) → **10000 (Nutzerentscheidung 2026-10-04: „Grenze hochsetzen“**, Commit 945bfc5; Ursache des Speicherbedarfs später als
  eigenes Paket).
- **Task 8:** Endlage Drehachse [0, −1, 0], Anschlag auf +z/rechte Leiste, 8 Schritte (Unit-Test), Speicherspitze messen.
- **Task 9:** Fixture Anschlag L 20 → 24 (Anschlag x 80…104): ein quadratisches Rechteck L = B scheitert im Compiler mit
  `Gleichungen: Code 1` (reproduzierbar), Erwartung unverändert; sporadischer Teilbau-Fehler gleicher Art bei Fall 4, Wiederholung auf
  frischem SolidWorks.
- **Task 10:** Speicherlauf-Hinweis im Skill (frisches SolidWorks, 6–10 GB) und in CLAUDE.md; Skill beschreibt die Grundstellung über Maß
  `D1` statt „speichert in Grundstellung“.

## 7. Offene Punkte

- **Speicherbedarf (eigenes Paket, Nutzerentscheidung):** je geöffnetem Teil ~1 GB (erste Öffnung +2,6 GB, ISO 4762 +1,7 GB; Grundplatte,
  Schlitten und Hebel bleiben für `offen_halten` geöffnet), Kollisionsprüfung ~+0,5 GB je Stellung ohne Bild (`mech.interferenzen`; erst
  das nächste Bild senkt um 370–500 MB). Mögliche Ansätze: offen gehaltene Teile früher schließen, Interferenzprüfung/Bilder in den
  Paarläufen anpassen.
- **Speicherabfrage sieht keine Spitzen:** `speicher_grenze_mb` wird nur vor den Läufen gegen das Dauerniveau geprüft; die Spitzen
  (Stehlager 10,8 GB, Schlitten 9,9 GB, Negativfall 1 10,2 GB) liegen bei 0,5-s-Abtastung nahe oder über der Grenze. Im Regressionslauf
  stürzte SolidWorks nie ab (RAM 31 GB).
- **Unaufgeklärter Unterschied der Speicherspitzen:** Task-8-Live 4031 MB (2-s-Abtastung) gegenüber 7816 MB (0,5-s-Abtastung) und dem
  Plateau 6,2 GB der Diagnose (Hypothese, ungeprüft: anderer Dokument-/Cache-Zustand oder Öffnungsreihenfolge).
- **Compiler-Fehler** `REBUILD_FEHLER – Gleichungen: Code 1`: reproduzierbar bei quadratischem Rechteck (`breite: =L`, `hoehe: =B` mit L = B,
  Task 9), sporadisch bei unveränderter Referenzleiste (2 von 6 Läufen), danach fünf Einzelbauten fehlerfrei; Verdacht auf ein Rennen
  zwischen `Add2` der Gleichungen und `EditRebuild3`. Eigene Folgeaufgabe außerhalb 4a.
- **Deferred minors des Ledgers** (Gesamt-Review soweit nicht erledigt): Task 2: Fall `drehung` in `test_schema_lehnt_ab` kommentieren,
  `test_soll_der_grenze…` prüft nicht den Vorrang von `wert`; Task 3: Tests für `BEWEGUNG_DOPPELT`, „fixiert“, `grenze_abstand min ≥ 0`,
  Gruppenpfad, Scharnier-Achsprüfung akzeptiert jede `referenz` (`plausibel.py:221`), neue Testdateien LF statt CRLF, Zeilen > 120 Zeichen;
  Task 4: `_grenze`/`bewegung:`/`bewegung_kollision:` mit `ok=True`, wenn der Lauf fehlt (besser `ok=None`), Hinweistext „None statt …“,
  `zip` ohne Längenprüfung, unbenutzter Import und Testlücken; Task 5: `unterdrueckt.append(b)` nach dem Aufruf, doppeltes `_zurueck`
  bei `min = 0`, `KeyError` statt Meldung bei `lagen[0]`, Testlücken; Task 6: `GetBox`-Rückfall ungetestet, zwei Konstanten für Wert 1,
  Attrappen-Tests für `halte/stelle/loese/zustand`, `SetSystemValue3`-Rückgabe ungeprüft; Task 7: Grundstellungsprüfung liest `D1` (belegt
  die Lage nur indirekt), Tests nur Winkelzweig, Docstring `loesche`, Schließfehler im `finally` kann die Ursache verdecken, `_grenzen(bg)`
  doppelt berechnet, `SpeicherKnapp` in `pruefen()` nur per `fahre`-Test belegt; Task 8: Kopfkommentar, Zusammenspiel XB; Task 9:
  Vergleich `[x["kollisionen"] for x in grund] == [0, 0]` reihenfolgeabhängig, Kommentarmaße fest statt aus Parametern.
- **Kandidaten für 4b:** Zahnrad-, Nut- und Kurvenverknüpfung (Referenz *Schieber mit Schrägbolzen*); Paket „Messarten“ (Fasen,
  Gewinde durch, Lagerachse); Änderung von `HUB` direkt im SolidWorks-Modell (Grenzwerte nicht per Gleichung bindbar) bleibt unbemerkt
  für die Änderungserkennung; Rechner B (SW 2026) ungetestet.

## Stand

- Datum: 04.10.2026, Rechner A (SOLIDWORKS 2025), Branch `stufe-4a` (von `plan-stufe-4a` @ dab5f61). Ohne Push.

| Task | Inhalt | Commits |
|---|---|---|
| 1 | Spike S13 und Nachtrag S13b | 00f8252, 2fb9183 |
| 2 | Format für Bewegungen (Schema, Datenmodell, Prüfsumme) | d443089 |
| 3 | Plausibilität für Grenzen, Scharnier, Bewegungen; Passung Drehbolzen; Hinweis Prüfaufwand | c503563 |
| 4 | Bewegungslogik ohne SolidWorks | 30de87a |
| 5 | Ablauf der Bewegungsprüfung (`fahre`) | 169c832 |
| 6 | SolidWorks-Schicht (Grenzverknüpfung, Scharnier, Antrieb, `SwMechanik`, Grundstellung) und Fix | dc85d9a, 0344c96 |
| 7 | `swki pruefen` mit Bewegungen, Bericht, Grundstellung ohne Antrieb (Spike S13c) | c162c1f, 2b5719e |
| 8 | Referenz Linearschlitten; Speichergrenze 8000 und 10000 | 52d8adf, cfffcb4, 945bfc5 |
| 9 | Negativfälle am Linearschlitten | e2156bf |
| 10 | Skill, Prüfer, CLAUDE.md, Design §4/§11, Spec-Nachzug, Ergebnisse, Regression | siehe Git |
