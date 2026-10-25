# Spike S-Schleife-1 „Weiche G1c aus der Spec“ – Ergebnisse

Stand 25.10.2026. Spike zu Ansatz C aus [2026-10-25-schnelle-konstruktionsschleife.md](2026-10-25-schnelle-konstruktionsschleife.md)
§7, freigegeben vom Nutzer am 25.10.2026. Code in `spikes/s18_*` (Wegwerf-Code, kein `swki`-Code geändert), Daten unter
`<arbeitsordner>/SPIKES/s18/`. Specs, Freigaben, Simulationsordner und SolidWorks-Läufe wurden nur gelesen. SolidWorks
war nur für den STL-Export (M3) in Gebrauch, ohne offene Dokumente anderer.

## Kurzfassung

**Ansatz C funktioniert.** Dieselben freigegebenen Specs, aus denen SolidWorks lauf-28 gebaut hat, ergeben ohne
SolidWorks und ohne abgeschriebene Maße ein MuJoCo-Modell der Weiche. Dieses Modell rechnet die Ergebnisse der
Handmodell-Studie vom 18.10. innerhalb der Vertrauensbereiche nach, und Optuna findet darauf eine Lösung im Bereich von
G1c.

| Nr. | Messgröße | Ergebnis | Ziel (§7.3) |
|---|---|---|---|
| M1 | Schnellbau je Teil, warm | 0,4 … 52 ms, 10 Teile zusammen 235 ms; einmaliger Import 2,2 s | ≤ 2 s je Teil ✔ |
| M2a | Volumen und Hüllquader gegen SolidWorks lauf-28 (Prüfbericht) | 10 von 10 Teilen gleich: Volumen ≤ 2·10⁻⁵ %, Hüllquader 0,000 mm (mit Normbohrungen und Verrundungen) | – ✔ |
| M2b | Geometrie gegen Handmodell der Studie | wo das Messer läuft gleich (Keil, Rutschenträger identisch; Rutschenkanäle gleich; Schieberstirn bis auf 0,4 mm³); Unterschiede nur dort, wo das Handmodell bewusst vereinfacht hat | ≤ 0,01 mm (in den Kontaktbereichen ✔) |
| M3 | STL Schnellbau gegen STL aus SolidWorks (`vergleich.py`) | 8 Teile: p99 0,012 … 0,039 mm, max 0,014 … 0,090 mm. Rutsche und Weichenkeil: von Hand geändert nach lauf-28 (23.10.), siehe unten | p99 ≤ 0,05, max ≤ 0,1 ✔ |
| M4 | Funktion gegen Handmodell, je 1992 Läufe | G1c 100 % = 100 %; G1b 88,8 % gegen 88,6 %; Ist v5 24,7 % falsch gegen 25,8 % – alle innerhalb des 95-%-Bereichs | wie Handmodell ✔ |
| M5 | Optuna, 3 Stellschrauben, 90 Proben | 37 min, 144 Proben/h (101 simulierte/h); erste Probe ≥ 99 %: Nr. 3 (T 179,7 / YS 205,4 / ZF −187,5, G1c: 179,5 / 204,5 / −175) | Lösung ≥ 99 % gefunden ✔ |
| M6 | Prüfstufe 2 für den Besten (1992 Läufe, halber Zeitschritt) | alle Bedingungen ≥ 99,90 %, halber Zeitschritt 99,95 % gegen 99,90 % | innerhalb 95-%-Bereich ✔ |

**Korrektur der Schätzung im Entscheidungsdokument:** Eine Probe kostet nicht 7–10 s, sondern **34 s**. Das sind drei
Bedingungen × 64 Läufe = 192 Läufe. Gemessen wurden 2,4–2,7 CPU-s je Lauf statt 0,5 s; dazu hat der Rechner 8 physische
Kerne, nicht 16. Damit sind es rund **100 simulierte Proben je Stunde**, über Nacht etwa 1000. Schnellbau und Zerlegung
kosten davon nur rund **0,5 s je Probe (1,5 %)**; die Simulation bestimmt das Tempo, wie erwartet.

## M1/M2a: Schnellbau gegen SolidWorks (`spikes/s18_schnellbau.py`, `s18_m1_teile.py`)

Der Schnellbau liest die Teil-Spec wie `swki bauen`. Er nutzt dabei dieselben Funktionen aus `swki`:
`swki.compiler.skizze.modellpunkt` für (u, v) → Modellpunkt, `swki.spec.ausdruck.auswerten` für die Ausdrücke und
`swki/wissen/bohrungsnormen.yaml` für die Normbohrungen (Kernloch, Bohrspitze 118°, Flachsenkung). Gebaut wird mit
build123d 0.13 / OCP 8.0.1.

| Teil | warm ms | Volumen Schnellbau | Volumen SolidWorks lauf-28 | Hüllquader Δ |
|---|---|---|---|---|
| Rutsche | 27,1 | 62 694,580 | 62 694,58 | 0,000 |
| Weichenkeil | 13,5 | 41 019,777 | 41 019,777 | 0,000 |
| Schieber (2 Verrundungen) | 31,2 | 19 584,667 | 19 584,667459 | 0,000 |
| Prüfkanal (8 Normbohrungen) | 52,4 | 60 153,071 | 60 153,071013 | 0,000 |
| Klemmleiste | 8,1 | 3 207,143 | 3 207,143253 | 0,000 |
| Saphirglas | 0,4 | 1 815,841 | 1 815,841 | 0,000 |
| Zwischenplatte | 15,3 | 8 004,287 | 8 004,286507 | 0,000 |
| Durchlicht (Ersatzkörper) | 43,2 | 53 060,162 | 53 060,162 | 0,000 |
| Rutschenträger | 17,0 | 35 866,387 | 35 866,387349 | 0,000 |
| Durchlichtlasche | 26,3 | 14 534,137 | 14 534,137348 | 0,000 |

Gegenprobe: Ohne Bohrungen entspricht die Differenz genau den Normbohrungen. Beim Weichenkeil sind das
110,45 mm³ = 2 × M3-Kernloch Ø 2,5 × 11 mit Spitze, bei der Rutsche 344,16 mm³ = 2 × M5.

Unterstützt wurden nur die Features dieser Teile: extrusion/schnitt (blind, mittig, durch_alles, bis_flaeche,
versatz_von_flaeche, umkehren) mit rechteck, kreis, polygon (radien), kontur (Bögen), langloch; verrundung/fase an
`nahe`-Kanten; bohrung, normbohrung (gewinde, zylinderschraube, stift). Es fehlen noch rotation, muster, spiegeln,
verzahnung, formschraege, referenz, `nahe`-Flächen und Senkschrauben.

## M2b: Spec-Geometrie gegen Handmodell (`s18_m2_hand.py`)

Monte-Carlo-Stichprobe je Gruppe (3 Mio. Punkte), G1c, Grundstellung:

| Gruppe | nur Handmodell mm³ | nur Spec mm³ | Ort und Grund |
|---|---|---|---|
| Keil + Zwischenplatte | 0 | 0 | identisch |
| Rutschenträger | 0 | 0 | identisch |
| Rutsche | 0 | 7 510 | Befestigungslasche unter der Rutsche (X −235 … −216, Z −270 … −255), im Handmodell weggelassen |
| Schieber | 0,8 | 9 803 | Kopf Y 360 … 385 (im Handmodell ohne Kollision); an der Stirn nur 0,4 mm³ an den Taschenradien |
| Prüfkanal + Klemmleisten | 1 842 | 18 | Glassitz und Durchblick unter dem Glas (im Handmodell gefüllt) |
| Saphirglas | 23 | 516 | Handmodell: flächengleiches Rechteck 22 × 30 statt Scheibe Ø 34 |
| Durchlicht | 0 | 2 787 | Kabelverschraubung (Ersatzkörper der Spec), im Handmodell Quader |

Alle Unterschiede sind dokumentierte Vereinfachungen des Handmodells. Fehler im Handmodell kamen dabei nicht zum
Vorschein; die früheren Fehler (Tubus, Schieberhöhe) betrafen Vorgängerstände.

## M3: STL gegen SolidWorks (`s18_m3_stl.py`, `werkzeuge/messstand/vergleich.py`)

STL aus SolidWorks lauf-28 über `werkzeuge/messstand/stl_export.py` (Qualität fein, Teilkoordinaten, 0,55 s je Teil),
Schnellbau-STL mit Toleranz 0,002 mm:

| Teil | p99 mm | max mm | Urteil vergleich.py |
|---|---|---|---|
| Schieber | 0,012 | 0,013 | richtig |
| Prüfkanal | 0,039 | 0,090 | richtig |
| Klemmleiste | 0,012 | 0,014 | richtig |
| Saphirglas | 0,021 | 0,022 | richtig |
| Zwischenplatte | 0,012 | 0,014 | richtig |
| Durchlicht | 0,027 | 0,028 | richtig |
| Rutschenträger | 0,018 | 0,021 | richtig |
| Durchlichtlasche | 0,017 | 0,020 | richtig |
| Rutsche | 12,3 | 22,2 | **falsch** |
| Weichenkeil | 12,8 | 15,2 | **falsch** |

Die Restabweichungen der 8 Teile sind Tessellierung: Die SolidWorks-STL hat 324–402 Dreiecke je Teil.

**Rutsche und Weichenkeil sind in lauf-28 nicht mehr die freigegebene Spec.** `AP68-Pruefstation_Rutsche.SLDPRT` und
`…_Weichenkeil.SLDPRT` (und die Baugruppe) tragen das Datum 23.10.2026 23:04 / 23:13. Der Prüfbericht von lauf-28 stammt
vom 20.10.2026 19:29, alle anderen Teile vom 20.10. Die Volumen der SolidWorks-STLs (Weichenkeil 25 102 mm³, Rutsche
67 685 mm³) passen nicht zu den 41 020 / 62 695 mm³, die SolidWorks selbst beim Prüfen von lauf-28 gemessen hat. Beides
spricht für Handänderungen nach dem Lauf (in den Sitzungen erwähnt). Der STL-Vergleich hat genau diese zwei Teile
gefunden; für die Konsistenzsicherung (Entscheidung §4 C) ist das der gewünschte Befund. Für die Spec ist es ein Fall
von `MANUELL_GEAENDERT`: Vor dem nächsten Bau `swki aenderungen` laufen lassen und den Nutzer fragen. Der Spike hat
daran nichts geändert.

## Baugruppe: Lage und Gelenke aus der Spec (`s18_baugruppe.py`)

- **Lage:** Ein Löser für reine Verschiebungen (deckungsgleich, konzentrisch, parallel) setzt alle 12 gebauten
  Komponenten. Die rechte Klemmleiste ergibt sich aus der Bohrungsachse zu +30 mm in X, das Durchlicht über die
  Durchlichtlasche. Frei bleiben nur die Hubachsen von Schieber und Weiche (Grenze gegen Zylinderaufnahme bzw.
  Kaufteil-Referenz). Für sie gilt die modellierte Grundstellung; das bestätigt der Bewegungsraum im Prüfbericht von
  lauf-28 (Schieber z −385 … −192,614, Weiche bis −179,5).
- **Gelenke:** `grenze_abstand` g1/g2 ergeben Schubgelenke mit Achse −Y (Maschine) und Hub 82 bzw. 25. Das stimmt mit
  dem Ablauf der Prüfaufgabe überein und wird bei jedem Aufbau geprüft.
- **Kollisionsgeometrie** (`s18_zerlegung.py`): exakte Zerlegung der B-Rep in konvexe Stücke (Raumteilung an Flächen
  und Achsebenen konkaver Zylinder, Pfeilhöhe ≤ 0,01 mm). Summe der Stückvolumen = B-Rep-Volumen, Füllfehler
  0 … 1,3 mm³. Stückzahlen:

  | Teil | Stücke |
  |---|---|
  | Weichenkeil | 3 |
  | Rutsche | 12 |
  | Schieber | 56 |
  | Prüfkanal | 259 (runder Glassitz) |

  Zusammen 342 Stücke. Die Zerlegung dauert 4,7 s, dauerhaft zwischengespeichert, je Probe nur die geänderten Teile:
  0,4–0,7 s.

## M4: Funktion gegen Handmodell (`s18_sim.py`, `s18_m4_laeufe.sh`, `s18_m4_vergleich.py`)

Ablauf, Werkstoffe, Startlagen D1 (1992) und Auswertung unverändert aus `simulation/sortierschritt-2026-10-18/skripte/`.
Ersetzt wurden nur die Körper und die Kanalgrenzen der Auswertung (aus der Rutschen-Spec). dt 10 µs, tc 0,15 ms.

| Fall | Spec-Modell | Handmodell | Einzelausgang gleich |
|---|---|---|---|
| G1c (freigegeben), Keil µ 0,55 / e 0,55, i.O. 0,10 m/s | 100 % [99,80 … 100] | 100 % [99,80 … 100] | 100 % |
| G1b = G1c ohne Keilwangen (2 Features weggelassen), Stahl µ 0,55 / e 0,60, i.O. 0,10 m/s | **88,76 %** [87,27 … 90,09] | **88,58 %** [87,08 … 89,92] | 83,5 % |
| Ist v5 (Parameter v5, Fangwand und Keilwangen weggelassen), n.i.O. 0,10 m/s, falscher Schacht | **24,74 %** [22,82 … 26,77] | **25,78 %** [23,84 … 27,81] | 63,4 % |

Der freie Landepunkt (Median) liegt in beiden Modellen bei Y 195,03. Je Lauf weicht er im Median 0,42 mm ab (p95
2,1 mm): Glasscheibe, Glassitz und Schieberkopf ändern einzelne Kontaktfolgen. Wo das Messer auf eine Kante trifft
(Trennwand, Ist-Stand), ist der Einzelausgang chaotisch; das zeigte schon die Rechenkontrolle der Studie (26 … 43 % je
nach Zeitschritt). Belastbar ist die Verteilung, und die ist gleich.

Rechenzeit je Lauf (15 Prozesse auf dem Ryzen 7 7800X3D, 8 Kerne/16 Threads): Handmodell 1,8 CPU-s, Spec-Modell
2,4–2,7 CPU-s (342 statt 40 Kollisionskörper). Mit Pfeilhöhe 0,05 mm sind es 178 Stücke und 2,2 CPU-s. 1992 Läufe
dauern 5,3–5,9 min.

## M5: Optuna (`s18_optuna.py`)

- **Stellschrauben** (nur Spec-Parameter, Topologie G1c):
  - T = Vorderkante Trennwand, 176 … 196; daraus `rutsche.yaml` YV und R_BN, i.O.-Kanal 21 und Trennwand 2 bleiben;
  - YS = Keilfuß, 195 … 225 (`weichenkeil.yaml`);
  - ZF = Fangwand-Oberkante, −199 … −170 (`rutsche.yaml`).
- **Start:** Stand v5 (T 193,5, YS 218,5, ZF −199).
- **Ziel:** min. Anteil richtig über n.i.O. 0,10 m/s, i.O. 0,05 und 0,15 m/s mit rauem Keil, je 64 Startlagen D1
  (dieselben in jeder Probe). TPE (Optuna 5.0, 12 Zufallsproben vorab), `JournalFileBackend` mit `JournalFileOpenLock`
  unter Windows ohne Fehler.
- **Prüfstufe 0 je Probe:**
  - Schema- und Plausibilitätsprüfung von `swki` auf den geänderten Specs;
  - Kollision je Stellung im Schnellbau (Keil ausgefahren gegen Rutsche, eingefahren gegen Durchlicht).

Ergebnis:

- **Umfang:** 90 Proben in 37,4 min, davon 25 in Prüfstufe 0 verworfen (0,6 s je Probe). Grund war immer, dass Keil
  oder Keilwangen ausgefahren in Fangwand oder Wangen fahren (bis 1526 mm³); die Specs selbst waren immer gültig. 65
  Proben wurden simuliert, je 30–45 s.
- **Startpunkt v5:** 0,70, n.i.O. 70 % wie im Handmodell.
- **Erste Probe mit 100 % in allen Bedingungen:** Nr. 3, eine Zufallsprobe (T 179,7, YS 205,4, ZF −187,5), dicht bei
  G1c. Insgesamt erreichten 37 von 65 simulierten Proben 1,0 (Bereich T 178,1 … 189,3, YS 204,4 … 216,2,
  ZF −192,9 … −170,3).
- **Lehre:** Mit 64 Läufen je Bedingung sättigt das Ziel bei 1,0 (Auflösung 1,6 %). Optuna kann dann nicht mehr zwischen
  guten Lösungen unterscheiden. Für die nächste Stufe braucht es:
  1. mehr Läufe für Kandidaten über einer Schwelle (zweistufig);
  2. ein Ziel mit Abstand, z. B. den kleinsten Abstand des freien Landepunkts zur Trennwand oder einen Worst-Case über
     Reibwerte;
  3. den `WilcoxonPruner` für schlechte Proben.
- **Das Feld der Lösungen mit 100 %** ist breit und deckt sich mit der Studie vom 18.10. (G1b/G1c). Die Trennwand muss
  rund 5–15 mm nach vorn, der Keilfuß folgt der Trennwand, und die Fangwand braucht keine 27 mm Höhe.

## M6: Prüfstufe 2 für den Besten (`s18_m6_laeufe.sh`)

Optuna-Bester (Probe 3: T 179,725 → YV 156,725, R_BN 34,775; YS 205,367; ZF −187,494) mit allen 1992 Startlagen D1:

| Bedingung | richtig [95-%-Bereich] | gültige Läufe | Fehler |
|---|---|---|---|
| n.i.O., 0,10 m/s | 100 % [99,81 … 100] | 1992 | – |
| i.O., 0,05 m/s, Keil µ 0,55 / e 0,55 | 99,90 % [99,63 … 99,97] | 1943 | 1 liegt, 1 daneben |
| i.O., 0,15 m/s, Keil rau | 100 % [99,80 … 100] | 1951 | – |
| i.O., 0,05 m/s, Keil rau, **dt 5 µs, tc 0,075 ms** | 99,95 % [99,71 … 99,99] | 1963 | 1 liegt |

Damit ist die Probe-3-Lösung auch bei voller Startlagenzahl und halbem Zeitschritt in allen Bedingungen ≥ 99 % und
innerhalb des 95-%-Bereichs stabil. Gegen G1c (Handmodell: i.O. 0,05 m/s rau 100 % [99,80]) ist sie gleichwertig, aber
mit einer Fangwand von 14,5 statt 27 mm Höhe über der Rutsche. Das ist ein Beispiel dafür, dass Optuna innerhalb einer
Topologie Spielraum für andere Ziele findet (weniger Material, mehr Bauraum). Rechenzeit M6: 4–8 min je Bedingung,
14 min mit halbem Zeitschritt.

Nicht gemacht: Rückbau der Probe-3-Werte nach SolidWorks. Die Spec bleibt unverändert, weil eine neue Freigabe nötig
wäre; nach der Freigabe-Regel §3.1 ist das die Entscheidung des Nutzers.

## Folgerungen für Ansatz C

1. **Der Kern trägt.** Schnellbau, Lage, Gelenke und Zerlegung aus der Spec sind exakt, wo es zählt (Volumen,
   Hüllquader, STL auf Tessellierungsniveau, Funktion innerhalb der Streuung). Abschreiben von Maßen entfällt.
2. **Das Tempo begrenzt die Simulation**, nicht die Geometrie. 100 simulierte Proben je Stunde mit 192 Läufen. Hebel,
   nach Nutzen geordnet:
   - Läufe je Probe adaptiv (wenige für schlechte, viele für Kandidaten);
   - weniger Kollisionskörper, wo kein Messer hinkommt (Glassitz, Durchblick: gröbere Pfeilhöhe oder Ersatz im
     `simulation`-Block);
   - MuJoCo 3.17 `mujoco.batch` statt Prozess-Pool (nach neuer Kalibrierung).
3. **Das Ziel braucht Abstand**, sonst sättigt es (M5). Das gehört in den Zielfunktions-Baustein der Prüfaufgabe.
4. **Konsistenz ist prüfbar und findet echte Abweichungen:** M3 hat die zwei von Hand geänderten Teile in lauf-28
   gefunden.
5. **Offen für Stufe C1/C3:**
   - fehlende Features (rotation, muster, spiegeln, …);
   - ein Lagelöser mit Drehungen (Kaufteile, Normteile);
   - der `simulation`-Block im Schema;
   - die Referenz-Suite durch beide Backends;
   - die Freigabe-Regel für autonome Schleifen (Entscheidung §3.1).

## Nachrechnen

```
.venv-sim\Scripts\python.exe -m spikes.s18_m1_teile <auftrag> <lauf-28>\pruefbericht.json <aus>\m1_teile.json
sh spikes/s18_m4_laeufe.sh .venv-sim/Scripts/python.exe <auftrag> <aus>
.venv-sim\Scripts\python.exe -m spikes.s18_m4_vergleich <aus>\m4_….json <studie>\daten\….json
.venv-sim\Scripts\python.exe -m spikes.s18_m2_hand <aus>\probe_nio.geometrie.json <aus>\m2_hand.json
.venv-sim\Scripts\python.exe -m spikes.s18_optuna <auftrag> <aus>\optuna --proben 90 --n 64
sh spikes/s18_m6_laeufe.sh .venv-sim/Scripts/python.exe <auftrag> <aus>
.venv\Scripts\python.exe -m spikes.s18_m3_stl sw <lauf-28> <aus>\stl_sw        (SolidWorks frei)
.venv-sim\Scripts\python.exe -m spikes.s18_m3_stl schnellbau <auftrag> <aus>\stl_schnellbau
```

`.venv-sim` (Python 3.14): mujoco 3.16.0, optuna 5.0.0, build123d 0.13.0 (cadquery-ocp-novtk 8.0.1.1.0), pyyaml,
jsonschema, trimesh, scipy; shapely 2.2.0 aus der vorhandenen Simulationsumgebung der Sortierschritt-Studie übernommen.
