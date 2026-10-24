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
| 2 | Punkt zu Seitenfläche | wie Zeile 1 mit der Seitenfläche −x | Weder `2_punkt_flaeche_hv` (`AddHorizontalDimension2`) noch `2_punkt_flaeche_dim2` (`AddDimension2`) legt ein Maß an: beide liefern `None`, Status 2. Nur das v-Maß zum Ursprung steht. Versucht wurde nur die Fläche aus `IFeature.GetFaces`; andere Wege zur Fläche (etwa eine Referenzebene darauf) sind nicht erprobt | **nein** → Entscheidung nach „sonst“ (Ruling 2): `{flaeche}` auf die Kante der Skizzenfläche in dieser Seitenfläche auflösen und dazu bemaßen; nur in Skizzen auf Flächen. Für die linke Kante belegt Zeile 1 diesen Weg |
| 3 | Rechteckseite zu Kante | `AddDimension2` Linie + Kante: 5 mm, maßgebend, Status 3 | `3_linie_kante`: D4 = 5,0 mm, `driven_state` 2. Status vorher 2, danach 3, `rebuild_fehler` leer | ja |
| 4 | Positionsskizze | Rand- und Symmetriemaße wie Zeilen 1 und 5, zwei Bohrungen; Variante Endpunkt auf der Kante voll bestimmt | `4_mittellinie_kante`: Ende der Mittellinie per `sgCOINCIDENT` auf der Kante. Abstand D1 = 40 mm (`AddVerticalDimension2`), Rand D2 = 10 mm (`AddHorizontalDimension2`), beide maßgebend. Status 2 → 3, zwei Bohrungen bei (x, z) (−40, ∓20). Keine überzähligen Beziehungen. `4_mittellinie_laenge` (Längenmaß 50, maßgebend): ebenso Status 3 und zwei Bohrungen. Beide ohne `fehler` und mit leerem `rebuild_fehler` | ja (beide Varianten) |
| 5 | Symmetrie und Rechteck über Mitte | `sgSYMMETRIC` + Abstandsmaß Status 3, nur gesetzte Beziehungen; Diagonale + `sgATMIDDLE` Status 3 | `5_symmetrie_kreise`: Status 3, Abstand D4 = 60 mm maßgebend, Mittellinie mit Längenmaß 20 (siehe Untervarianten). Neue Beziehungen genau die gesetzten (COINCIDENT, VERTICAL, SYMMETRIC, HORIZPOINTS) plus die Maße, `ueberzaehlig` leer. `5_rechteck_diagonale`: Status 3, `ueberzaehlig` leer. `5_rechteck_symmetrie` (Punkt mittig der Diagonale, Lage 20/10): Status 3, `ueberzaehlig` leer | ja |
| 6 | Handtest | Breite 100 → 90: Achse bei x = 30,00 ± 0,01, `rebuild_fehler` leer – ohne Fase, mit Fase, Bohrungsassistent | Breite gesetzt mit `D1@f1_skizze`. 6a: x 40 → 30,0. 6b (Fase 1 mm an der Bezugskante, im Baum nach dem Schnitt): x 30,0. 6c: x 30,0 / 30,0, zwei Bohrungen. 6c_laenge: x 30,0 / 30,0. Überall `x_abw_max` 0,0, `rebuild_fehler` leer, Randmaß danach 10,0, Skizzenstatus 3, nach `ForceRebuild3` unverändert. Nicht getestet: Fase **vor** der Bezugsskizze im Baum | ja (Fase vor der Bezugsskizze ungetestet; Ruling 3: Skill-Regel „Fasen am Ende“ genügt) |
| 7 | Lesen | `Parameter("<maß>@<skizze>").SystemValue` nach dem Öffnen in m | `7_lesen`: `D2@f2_skizze` = 0,010000000000000002, `D1@f1_skizze` = 0,1 | ja |

### Befunde für die Umsetzung

- **Beziehungen und Maße:** `RelationManager.GetRelations(0)` zählt Maße mit. Längen- und Abstandsmaße erscheinen als
  `DISTANCE`, Kreisdurchmesser als `DIAMETER`.
- **Diagonale im Rechteck:** `CreateCenterLine` mit `AddToDB` teilt die vorhandenen Eckpunkte des Rechtecks
  (`diagonale_teilt_ecken` [true, true]). Es entsteht keine eigene Deckungsbeziehung, und es ist keine nötig.
- **Punkte in der Positionsskizze:** Ein Endpunkt lässt sich per `sgCOINCIDENT` direkt an eine Modellkante binden. Die
  Symmetrie (Punkt, Punkt, Mittellinie) wirkt dort genauso wie in normalen Skizzen.

### Entscheidungen je Abweichung

- Zeile 2 (Fläche nicht bemaßbar) → Ruling 2: `{flaeche}` wird auf die Kante der Skizzenfläche aufgelöst und gilt nur in
  Skizzen auf Flächen (Spec §3, Nachtrag).
- Zeile 4/5 (Annahmen bestätigt) → Ruling 4: Mittellinie mit Endpunkt auf der Randkante; Ruling 4a: ohne Skizzenfläche
  Längenmaß an der Mittellinie. Rechteck: Diagonale nur bei Mitte ≠ (0, 0), sonst Seitenmittelpunkte (Ruling 6, Spec §5.2).
- Zeile 6 (Fase im Baum nach der Bezugsskizze bestanden) → Ruling 3: keine zusätzliche Skill-Regel.

### Untervarianten (über den Auftrag hinaus bzw. Annahmen)

- `6c_handtest_normbohrung_laenge`: Handtest mit Bohrungsassistent, die Mittellinie hat ein Längenmaß 50 statt eines
  Endpunkts auf der Kante. Damit gilt Zeile 6 für beide Wege aus Zeile 4.
- Fall 3: Rechteckmitte bei (−35, 10); die Ecke unten links ist nur in v zum Ursprung bemaßt.
- Fall 5 Kreise: Die Mittellinie entlang v hat ein Längenmaß 20, sonst bliebe ihr Endpunkt frei.
- Abstandsmaße (40 bzw. 60) sind achsparallel gesetzt (`AddVerticalDimension2`/`AddHorizontalDimension2`).
- Normbohrung: Gewinde M6, Tiefe 10, Gewindetiefe 8.

## 2. Live-Tests (SOLIDWORKS 2025, Rechner A, 2026-10-24)

Jeder Test lief einzeln mit `tests\live_einzeln.py <datei::test> --zeit 900`; SolidWorks bei Bedarf vorher neu gestartet
(Private Bytes 278–435 MB zu Beginn, bis 3832 MB nach einer Serie).

**Neue Tests** (`tests/live/test_live_bemassungsbezug.py`):

| Test | Ergebnis |
|---|---|
| `test_platte_mit_bezuegen_ohne_gleichungen` | `gleichungen_anzahl == 0`, alle Skizzen Status 3, Positionsskizze enthält die Maße 10 und 40, Achsen bei x = −70, `swki pruefen` ohne Mangel |
| `test_handaenderung_erhaelt_randabstand` | Länge per `Parameter(name).SetSystemValue3` auf 150: Achse bei x = −65,00 ± 0,01; `aenderungen` liefert `vorschlaege == [{"parameter": "L", "neu": 150}]`, keine Lagedifferenz |
| `test_handaenderung_randmass_ergibt_delta` | Randmaß 10 → 12: Achse bei x = −68; `vorschlaege == [{"pfad": "features[1].positionen[0][0]", "bezug": "-rand", "delta": 2}]` |
| `test_rechteck_mit_eckradius_und_seitenmittelpunkt` (Fall c und b, Radius 8) | Status 3, Hüllquader wie Spec (Fall c [−50, 0, −30, 50, 10, 30], Fall b [−50, 0, −10, 50, 10, 50]); Breite per API auf 120 bleibt symmetrisch (±60), Volumen exakt |
| `test_rechteck_mit_eckradius_versetzt_mit_mitte` (Fall d, Radius 4) | baut, alle Skizzen Status 3, Volumen exakt |
| `test_kreis_mittig_in_tasche_gleicher_mitte` | `CreatePoint` an belegter Stelle: keine Überbestimmung, Status 3 |
| `test_gleichung_des_paarabstands_mit_negativer_koordinate` (`gleichungen: true`) | SolidWorks nimmt `2 * -"ZG"` an; ZG 20 → 25 verschiebt die Achsen auf z = ±25 |

**Umstellung auf `gleichungen: true`** (Tests, die Gleichungen lesen; `tests/live/bauhilfe.py` folgt jetzt dem Schalter wie
`swki bauen`): `test_live_extrusion` (`test_extrusion_mit_parametern`, `test_quadratisches_rechteck_mit_parametern`),
`test_live_endbedingungen::test_tasche_mit_restwandstaerke`, `test_live_formschraege::test_tasche_mit_eckradius_und_gleichung`,
`test_live_konturen` (Rechteck mit Eckradius, `test_langloch`, `test_kontur_mit_boegen`), `test_live_parametrik`,
`test_live_rotation_bohrung::test_lage_haengt_an_parameter`, `test_live_normbohrung` (Gewinde mit drei Positionen,
Senkschraube von unten), `test_live_aenderungen` (`test_manuelle_aenderung_am_teil` vergleicht Maße statt globaler
Variablen, `test_uebernahme_am_teil`): alle bestanden. Die erwartete Gleichungsliste von `test_extrusion_mit_parametern`
enthält keine Lagegleichung für ein Rechteck um den Ursprung mehr (Fall c: Seitenmittelpunkte, kein Lagemaß).

**Referenzen** (Regressions-Suite, Bau mit Gleichungen aus): `auswerferhalteplatte` (Fall c und b mit Radius) und
`zentrieraufnahme` (Fall c mit Radius, Tasche Fall a mit Radius und `+rand`, Kreise mit `rand`/`mitte`) bestanden. Die
Referenz-Specs tragen `bezug` (Grundplatte des Motorhalters, Zentrieraufnahme); die Freigabe-Prüfsummen blieben
unverändert, da der Bezug Bauweg ist.

**Befunde beim Test**
- Fall b/c mit Eckradius brach zunächst ab (`Ecke …: 0 statt 2 Linien`): `sgATMIDDLE` an der getrimmten Seite verschiebt
  das Rechteck nach der ersten Verrundung. Fix: Ecken über das Linienpaar wählen (Ruling 10, Spec §5.2 Nachtrag); der
  Rückfall (Verrundungen vor den Beziehungen) war nicht nötig.
- Fall d (Diagonale) mit Radius ist als Tasche belegt; Grundplatten um den Ursprung (Fall c) kombinieren Radius nie mit
  einer Diagonale.

## 3. Regression

Lauf 2026-10-24, Branch `bemassungsbezug` bei Commit 4ea2e6b: `python -m werkzeuge.live_frisch tests\referenz --zeit 1800`
(SolidWorks frisch vor jedem Test). **11 von 11 OK** (exit 0).

| Referenz | Dauer s | Spitze Private Bytes MB |
|---|---|---|
| buchse | 15,4 | 3367 |
| formplatte_ds | 16,3 | 3373 |
| auswerferhalteplatte | 19,3 | 3389 |
| stehlager | 44,6 | 9903 |
| linearschlitten | 153,1 | 9434 |
| zahnstange | 18,4 | 3382 |
| ritzelwelle | 23,2 | 3881 |
| antriebswelle | 26,6 | 3928 |
| zahnstangentrieb | 144,5 | 9469 |
| motorhalter | 35,7 | 9059 |
| zentrieraufnahme | 17,3 | 3371 |

Alle Referenzen bauen ohne Gleichungen. Motorhalter-Grundplatte und Zentrieraufnahme bauen mit Bezügen. Die Freigaben
sind unverändert gültig.
