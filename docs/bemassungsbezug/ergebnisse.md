# Paket Bemaßungsbezug – Ergebnisse

Spec: docs/superpowers/specs/2026-10-23-bemassungsbezug-design.md

## 1. Spike S17 (SOLIDWORKS 2025, Rechner A, 2026-10-24)

Rohdaten: docs/stufe0/ergebnisse/s17_bemassungsbezug.json · Spike: spikes/s17_bemassungsbezug.py

- Ein Lauf auf frisch gestartetem SolidWorks, `ok: true`, kein `fehler_fall`.
- 14 Teile gebaut und ungespeichert geschlossen. 6a wurde als Kopie unter `<arbeitsordner>/S17/s17_6a.sldprt` gespeichert.
- Private Bytes 431 → 2320 MB. Einstellungen vorher und nachher `False 1`.
- Die Skizze liegt auf der Deckfläche von f1. Die Spec-Achse u ist dort Skizzen-x: Maße in u sind horizontal, Maße in
  v vertikal.

| # | Frage | Annahme | gemessen | getroffen |
|---|---|---|---|---|
| 1 | Punkt zu Modellkante | `1_punkt_kante_hv`: ein Maß, `driven_state` 2, 10 mm, Status 3 | `1_punkt_kante_hv`: `AddHorizontalDimension2` mit Punkt und linker Kante → D1 = 10,0 mm, `driven_state` 2, Status 3 (offen und geschlossen), `rebuild_fehler` leer. `1_punkt_kante_dim2` (`AddDimension2`): gleiches Ergebnis | ja |
| 2 | Punkt zu Seitenfläche | wie Zeile 1 mit der Seitenfläche −x | Weder `2_punkt_flaeche_hv` (`AddHorizontalDimension2`) noch `2_punkt_flaeche_dim2` (`AddDimension2`) legt ein Maß an: beide liefern `None`, Status 2. Nur das v-Maß zum Ursprung steht | **nein** → Controller entscheidet nach „sonst“: `{flaeche}` auf die Kante der Skizzenfläche in dieser Seitenfläche auflösen. Für die linke Kante belegt Zeile 1 diesen Weg |
| 3 | Rechteckseite zu Kante | `AddDimension2` Linie + Kante: 5 mm, maßgebend, Status 3 | `3_linie_kante`: D4 = 5,0 mm, `driven_state` 2. Status vorher 2, danach 3, `rebuild_fehler` leer | ja |
| 4 | Positionsskizze | Rand- und Symmetriemaße wie Zeilen 1 und 5, zwei Bohrungen; Variante Endpunkt auf der Kante voll bestimmt | `4_mittellinie_kante`: Ende der Mittellinie per `sgCOINCIDENT` auf der Kante. Abstand D1 = 40 mm (`AddVerticalDimension2`), Rand D2 = 10 mm (`AddHorizontalDimension2`), beide maßgebend. Status 2 → 3, zwei Bohrungen bei (x, z) (−40, ∓20). Keine überzähligen Beziehungen. `4_mittellinie_laenge` (Längenmaß 50, maßgebend): ebenso Status 3 und zwei Bohrungen. Beide ohne `fehler` und mit leerem `rebuild_fehler` | ja (beide Varianten) |
| 5 | Symmetrie und Rechteck über Mitte | `sgSYMMETRIC` + Abstandsmaß Status 3, nur gesetzte Beziehungen; Diagonale + `sgATMIDDLE` Status 3 | `5_symmetrie_kreise`: Status 3, Abstand D4 = 60 mm maßgebend, Mittellinie mit Längenmaß 20 (siehe Untervarianten). Neue Beziehungen genau die gesetzten (COINCIDENT, VERTICAL, SYMMETRIC, HORIZPOINTS) plus die Maße, `ueberzaehlig` leer. `5_rechteck_diagonale`: Status 3, `ueberzaehlig` leer. `5_rechteck_symmetrie` (Punkt mittig der Diagonale, Lage 20/10): Status 3, `ueberzaehlig` leer | ja |
| 6 | Handtest | Breite 100 → 90: Achse bei x = 30,00 ± 0,01, `rebuild_fehler` leer – ohne Fase, mit Fase, Bohrungsassistent | Breite gesetzt mit `D1@f1_skizze`. 6a: x 40 → 30,0. 6b (Fase 1 mm an der Bezugskante, im Baum nach dem Schnitt): x 30,0. 6c: x 30,0 / 30,0, zwei Bohrungen. 6c_laenge: x 30,0 / 30,0. Überall `x_abw_max` 0,0, `rebuild_fehler` leer, Randmaß danach 10,0, Skizzenstatus 3, nach `ForceRebuild3` unverändert | ja |
| 7 | Lesen | `Parameter("<maß>@<skizze>").SystemValue` nach dem Öffnen in m | `7_lesen`: `D2@f2_skizze` = 0,010000000000000002, `D1@f1_skizze` = 0,1 | ja |

### Befunde für die Umsetzung

- **Beziehungen und Maße:** `RelationManager.GetRelations(0)` zählt Maße mit. Längen- und Abstandsmaße erscheinen als
  `DISTANCE`, Kreisdurchmesser als `DIAMETER`.
- **Diagonale im Rechteck:** `CreateCenterLine` mit `AddToDB` teilt die vorhandenen Eckpunkte des Rechtecks
  (`diagonale_teilt_ecken` [true, true]). Es entsteht keine eigene Deckungsbeziehung, und es ist keine nötig.
- **Punkte in der Positionsskizze:** Ein Endpunkt lässt sich per `sgCOINCIDENT` direkt an eine Modellkante binden. Die
  Symmetrie (Punkt, Punkt, Mittellinie) wirkt dort genauso wie in normalen Skizzen.

### Untervarianten (über den Auftrag hinaus bzw. Annahmen)

- `6c_handtest_normbohrung_laenge`: Handtest mit Bohrungsassistent, die Mittellinie hat ein Längenmaß 50 statt eines
  Endpunkts auf der Kante. Damit gilt Zeile 6 für beide Wege aus Zeile 4.
- Fall 3: Rechteckmitte bei (−35, 10); die Ecke unten links ist nur in v zum Ursprung bemaßt.
- Fall 5 Kreise: Die Mittellinie entlang v hat ein Längenmaß 20, sonst bliebe ihr Endpunkt frei.
- Abstandsmaße (40 bzw. 60) sind achsparallel gesetzt (`AddVerticalDimension2`/`AddHorizontalDimension2`).
- Normbohrung: Gewinde M6, Tiefe 10, Gewindetiefe 8.
