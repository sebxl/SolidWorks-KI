# Stufe 4b – Ergebnisse (Verzahnung und Kopplungen)

Fertig-Kriterium Spec 4b §12 für Rechner A (SW 2025). Rechner B (SW 2026) offen.

## 1. Etappe 1 – Verzahnung (Zwischenstand 2026-10-05)

Etappe 1 (Tasks 1–6: Geometrie, Format, Handler `verzahnung`, Teilprüfung `verzahnungen`, Teil-Referenzen) besteht live auf
Rechner A. Etappe 2 (Kopplungen in der Baugruppe) steht aus.

### 1.1 Spike S14a (Task 2) – Ergebnis und Entscheidung je Zeile

Messwerte: `docs/stufe0/ergebnisse/s14a_verzahnung.json`, `s14a_verzahnung_nachmessung.json`, `s14a_verzahnung_zeit.json`,
`s14a_verzahnung_zahnweite.json`. Alle Entscheidungen standen vorab im Ledger („Ruling“). SolidWorks 2025.

| Z. | Frage | Ergebnis (gemessen) | Entscheidung | Wenn falsch |
|---|---|---|---|---|
| 1 | Spline gegen Polylinie | bestätigt: Spline z 20 Status 3, 160 Segmente, Aufsatz ok, 1 Körper, größte Abweichung von der Soll-Evolvente 0,000114 mm (Polylinie 0,006084 mm) | Spline (`CreateSpline2`, alle Segmente `sgFIXED`) wie Plan-Code | keine Kosten |
| 2 | Ganzes Profil in einer Skizze | abweichend: z 80 Skizze 108 s (im Nachtrag 267 s, Streuung Faktor 2,5 ungeklärt), +597 MB je Rad; Zeit entsteht im COM-Overhead je Punkt (Zeichnen 75–91 % der Skizzenzeit), nicht in der Skizzengröße | Ganzes Profil bleibt; Handler bekommt zwei Beschleunigungen: affine Abbildung (u, v) → Skizze (drei `zu_skizze`-Aufrufe kalibriert, Gegenprobe, Abweichung > 1e-9 m → `BauFehler`) und Auswahl aller Segmente in einem `MultiSelect2`-Aufruf (Auswählen z 80: 36,6 → 3,4 s) | Radbau bleibt langsam (~1–2 min je Rad), Live-Läufe länger; Lücke + Kreismuster erst nach erneuter Entscheidung |
| 3 | Messung | Zylinder (Kopf-/Fußflächen) und Zahnstange (Teilung 6,28319, Zahndicke 3,09159) bestätigt; Zahnweite abweichend: IMeasure zwischen ganzen Flanken 14,85701 statt 15,273894 mm (−0,417 mm, misst den Mindestabstand an den Flankenenden, deckt sich mit der Nachrechnung 14,857005) | Zahnweite per Strahl entlang der Grundkreistangente (`IFace2.GetProjectedPointOn`, Spannmitte φ_m = winkel + (k − 1)·180°/z): Genauigkeit ≤ 0,00001 mm in vier Fällen (z 20/25/50, Abmaß −0,05/−0,10); `verzahnung_mm` bleibt 0,005 | Zahnweite misst falsch; fiele in Task 5/6 live auf (bestätigt: Zahnweite W3 live 15,273894 = Soll) |
| 4 | Radachse als Referenz | bestätigt: koaxiale Fußkreis-Zylinderfläche, r 17,5 (Spline und Polylinie) | wie Plan-Code, keine Bezugsachse im Handler; Spec-Nachzug §4.4 in Task 15 | Bezugsachse im Handler anlegen |
| 5 | Zeit und Speicher je Radbau | abweichend: z 17–50 im Spike 56–112 s und +294…+382 MB je Rad (Zeit in der Skizze) | nach den Beschleunigungen aus Z. 2 live (Task 4): Rad z 20 14–24 s, Spitze 3,5–3,8 GB; Task 5: Stirnrad 13,0 s, Zahnstange 8,7 s; Hinweis zu großen Zähnezahlen nur falls Ziel z ≤ 50 < 15 s verfehlt | Hinweis im Skill zu großen Zähnezahlen; Referenz bleibt |
| 6 | Zahnband auf dem Rücken | bestätigt: Zahnstange z 5 Status 3, 30 Segmente, Aufsatz ok, 1 Körper | eine Kontur je Zahn, Rücken genau bis zur Fußlinie wie Plan-Code | Zahnband 0,01 mm in den Rücken verlängern |

Weitere Entscheidungen (Rulings): T4-2 `dispatch_array` kommt schon in Task 4 nach `swki/verbindung.py` (Task 11 überspringt diese
eine Ersetzung); T5-1 die Messgerade liegt auf halber Zahnbreite, kein Treffer → `REFERENZ_NICHT_GEFUNDEN` („Zahnweite nicht
messbar“).

### 1.2 Testzahlen

Unit-Tests 711 → **763 bestanden**, abgewählt (Live, `sw`-markiert) 117 → **126**. Zuwachs je Task (bestanden): Task 1 +29
(740), Task 2 ±0 (Spike), Task 3 +16 (756), Task 4 ±0 (+3 abgewählt), Task 5 +7 (763; +2 abgewählt), Task 6 ±0 (+4 abgewählt:
drei Referenzeinträge, `test_negativ_zahnweite`). 117 + 3 + 2 + 4 = 126.

### 1.3 Teil-Referenzen Zahnstangentrieb (Task 6)

`tests/referenz/zahnstangentrieb/` (sieben Teil-Specs: Grundplatte, Leiste, Schlitten, Zahnstange, Lagerbock, Ritzelwelle,
Antriebswelle; Eingabe `eingabe/beschreibung.md`). `validieren` aller sieben: `gueltig: true`, `hinweise: []`. Keine
Bauweg-Änderung nötig: alle drei Teile bestanden im ersten Anlauf.

Regressionstest `test_referenz_besteht` je Teil einzeln (`--zeit 600`), Private Bytes vorher → Spitze → nachher:

| Teil | Ergebnis | Dauer | Private Bytes (MB) |
|---|---|---|---|
| Zahnstange (m 2, z 30) | OK | 39 s | 418 → 3423 → 1065 |
| Ritzelwelle (Ritzel z 20, Rad z 25) | OK | 68 s | 889 → 4281 → 2527 |
| Antriebswelle (Rad z 50) | OK | 64 s | 426 → 4002 → 2246 |

Prüfer-Läufe (`swki bauen` + `swki pruefen`, je Lauf 1, Urteil durch den Prüfer-Agenten): `bestanden: true`, 0 Mängel.

| Teil | Bauen | Bauen + Prüfen | Private Bytes (MB) vor → nach Bauen → nach Prüfen | Prüfer-Urteil |
|---|---|---|---|---|
| Zahnstange | 25 s | 36 s | 426 → 1005 → 1042 | bestanden |
| Ritzelwelle | 36 s | 65 s | 892 → 2286 → 2482 | bestanden |
| Antriebswelle | 39 s | 65 s | 429 → 2043 → 2239 | bestanden |

`swki status` je Teil: Lauf 1 `pruefer: bestanden`, Empfehlung „bestanden“. Prüfer-Urteile je
`{"bestanden": true, "maengel": []}`. Aufträge und Arbeitsordner danach gelöscht.

Speicher: Die Spitzen der Teile mit Rad liegen bei 3,4–4,3 GB. Das Niveau nach Bauen und Prüfen steigt bei der Zahnstange
um 0,6 GB (426 → 1042), bei den Teilen mit Rädern um 1,6 GB (Ritzelwelle, 892 → 2482) bzw. 1,8 GB (Antriebswelle,
429 → 2239). Nach jedem Teil mit Rädern ist vor dem nächsten Lauf ein Neustart nötig (Grenze 2000 MB Private Bytes).

### 1.4 Negativfall E1 (Zahnweite)

`tests/live/test_live_verzahnung.py::test_negativ_zahnweite`: der Bau verfälscht das Zahndickenabmaß der Antriebswelle um
−0,05 mm (Spec bleibt unverändert); erwartet genau `{verzahnungen}`, Knoten `z1`, Abweichung „zahnweite W6“. **OK**, 67 s,
Private Bytes 431 → 4015 → 2222 MB. Mängelmenge exakt wie erwartet, Erwartung nicht angepasst; das Volumen ändert sich laut Plan nur um
−0,13 % (nicht gemessen); im Lauf gab es keinen `volumen`-Mangel.

### 1.5 Regression Buchse, Formplatte, Auswerferhalteplatte

Einzeln (`--zeit 600`), SolidWorks frisch gestartet, Grenze vor einem Lauf 3000 MB (Teile ohne Verzahnung):

| Referenz | Ergebnis | Dauer | Private Bytes (MB) vorher → Spitze → nachher |
|---|---|---|---|
| Buchse | OK | 32 s | 427 → 3292 → 927 |
| Formplatte | OK | 49 s | 927 → 3507 → 1175 |
| Auswerferhalteplatte | OK | 77 s | 1175 → 3851 → 1384 |

### 1.6 Abweichungen von der Spec und offene Punkte

- Zahnweite nicht per `IMeasure` zwischen ganzen Flanken, sondern per Strahl entlang der Grundkreistangente (Ruling S14a-Z3,
  Spec §4.5 überlässt den Messweg dem Spike); `verzahnung_mm` 0,005 unverändert.
- Radbau: ganzes Profil in einer Skizze mit affiner Abbildung und `MultiSelect2` (Ruling S14a-Z2/Z5, T4-1); Zeit je Rad nach
  der Umsetzung 14–24 s (z 20) bzw. 19,7 s (z 50) statt ~65 s Skizzenzeit im Spike; das Ziel < 15 s ist nicht erreicht (1.7).
- Radachse über die Fußkreis-Zylinderfläche (Ruling S14a-Z4): Spec-Nachzug §4.4 in Task 15.
- Zeit und Speicher je Radbau (Spec §12, siehe 1.7): Das Ziel „Rad z ≤ 50 < 15 s“ ist **nicht erreicht**: z 20 (ganzes Teil) 14,3 s (warm)
  bzw. 22,9–23,5 s (mit Kaltstart), z 50 (Feature z1) 19,7 s, ganzes Teil 29,6 s. Der Speicher je Radbau liegt deutlich über der Annahme < 300 MB: Bauen der
  Antriebswelle (Dokument und Rad z 50) +1,4 GB Private Bytes (1169 → 2596 MB), Spitzen 3,4–4,3 GB. Ob ein Hinweis im Skill
  zu großen Zähnezahlen nötig ist, entscheidet der Controller.
- Die Versatzebenen der Verzahnungs-Features sind in den Prüfbildern sichtbar (nicht ausgeblendet).
- Offen: Streuung der Skizzenzeit (Faktor 2,5 zwischen Läufen) ungeklärt; Etappe 2 (Kopplungen, Tasks 7–15) und Rechner B
  (SW 2026) offen.

### 1.7 Zeit und Private Bytes je Radbau

Zeit je Feature `verzahnung` aus dem Bauprotokoll (`knoten[].dauer_s`), Private Bytes vor/nach `swki bauen` des ganzen Teils. Die z-20-Werte aus Task 4 sind Testdauern des ganzen Bauteils (Welle und Rad), nicht die Zeit des Features allein:

| Rad | Zeit Feature | Quelle | Private Bytes (MB) |
|---|---|---|---|
| z 20 (Task 4, Teil mit Rad) | Testdauer 14,3 s warm, 22,9–23,5 s mit Kaltstart | Live-Test Task 4 (Bericht Task 4) | Spitze 3,5–3,8 GB (Task 4) |
| z 50 (Antriebswelle, Wegwerf-Auftrag `MESS-4B-RAD`) | **19,7 s** (z1; ganzes `bauen` 29,6 s, davon Vorbereiten 1,5 s, Bauen 27,0 s, Speichern 1,0 s; die beiden Wellenabschnitte je ≈ 3 s) | `protokoll.json` Lauf 1 | 1169 → 2596 (+1427, Dokument und Rad zusammen; Spitze nicht abgetastet) |
| z 20 + z 25 (Ritzelwelle) | nicht gemessen: Private Bytes nach dem z-50-Bau 2596 MB (> 2000 MB) | | |

Der Auftrag und der Arbeitsordner sind danach gelöscht.
