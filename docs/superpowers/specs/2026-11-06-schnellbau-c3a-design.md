# Stufe C3a: Konstruktionsstil im Schnellbau – Design

Stand 06.11.2026. Auftrag aus der Hauptsitzung (Paket Konstruktionsstil, PR #25): Der Schnellbau baut die Features des
Pakets so wie der SolidWorks-Compiler. Grundlagen: `docs/superpowers/specs/2026-10-25-schnellbau-c1-design.md`,
`docs/superpowers/specs/2026-11-01-konstruktionsstil-design.md` §9, `docs/konstruktionsstil/ergebnisse.md`
(„Für Stufe C3a“, „Offen“). Was nicht vom Auftrag oder diesen Designs kommt, ist als „Selbst entschieden“ markiert.

## 1. Absicht

Specs mit `optimierung` oder Simulation sollen im Stil des Nutzers geschrieben werden können: Bohrungsfasen, Verrundung als
eigener Knoten in gespiegelten oder gemusterten Formen, `austragung`. Heute meldet der Schnellbau diese Features nur
oder bricht ab. Darum behalten solche Specs den Skizzen-Radius (Skill `konstruieren` Regel 4, Skill `optimieren` §1).

**Ziele:** gleiche Geometrie in beiden Backends (Volumen ≤ 1e-7 relativ, Hüllquader ≤ 1e-4 mm gegen
`sw_referenz.json`). Gleiche Instanzpunkte gemusterter Bohrungen für `instanz` und `je_position`. Danach die
Übergangsregel aus beiden Skills streichen.

**Nicht-Ziele:**
- neue Spec-Felder oder Feature-Typen
- Änderungen am SolidWorks-Compiler, außer einem Live-Test der Achsrichtungen
- Kopplungen und Drehungen im Lagelöser
- die übrigen offenen Review-Befunde aus `docs/konstruktionsstil/ergebnisse.md` (`bohrbild`, Musterprüfung, Fräserhinweis)

**Anti-Ziel:** ein Feature wird still weggelassen oder anders gebaut als in SolidWorks. Was der Schnellbau nicht kann,
meldet er. Die bekannte Grenze der kopierten Verrundung (§3) steht hier im Design und in den Ergebnissen; der
Live-Abgleich hält beide Backends gleich.

## 2. Bohrungsfase (Feld `fase`)

- Maße aus `swki/spec/bohrungsfase.py`: Abstand c = `fase_abstand(f, p)`, Eintrittsradius r = `eintritt_radius(f, p)`
  (bei Senkungen der Senkungsrand, bei Gewinde das Kernloch). Beide Funktionen nutzt schon der Compiler.
- Je Position ein Kegelstumpf am Eintritt: Radius r + c in der Eintrittsebene, Radius r in der Tiefe c, Richtung wie die
  Bohrung. Er wird mit dem Bohrungswerkzeug vereinigt. Mehrvolumen je Position: π·c·(r·c + c²/3), wie `volumen: auto`.
- Muster und Spiegeln übernehmen die Fase mit dem Werkzeug. Das entspricht Variante A des Compilers: Das Fase-Feature ist
  dort Quelle des Musters.
- Die Meldung „fase am Bohrungseintritt nicht gebaut“ entfällt.
- `bohrungen=False` (Simulation ohne Bohrungen) lässt die Fase mit der Bohrung weg, wie bisher die Bohrung.
- **Selbst entschieden:** Kegel statt `chamfer` auf Kanten. Er ist unabhängig von der Kantensuche und deckt sich mit dem
  Compiler, solange die Eintrittskante ein voller Kreis in einer ebenen Fläche ist. Das sichert `validieren` für die
  Eintrittsebene ab.

## 3. Verrundung in Quellen von Muster und Spiegeln

- Die Verrundung bleibt, wie sie ist: `fillet` am Körper.
- Steht ihre ID in `features` eines späteren Musters oder einer Spiegelung, merkt sich der Schnellbau ihre Wirkung als
  Differenzkörper: Zuwachs = nachher − vorher (Aufsatz) und Abtrag = vorher − nachher (Schnitt). Das sind die Werkzeuge
  der Verrundung.
- Gemustert werden die Quellen in Spec-Reihenfolge, je Quelle ihre Werkzeuge mit ihrer Operation. Aufeinanderfolgende
  Werkzeuge gleicher Operation werden zusammengefasst. Für Muster mit nur einer Operation ändert sich nichts.
  Heute gilt „erst alle Aufsätze, dann alle Schnitte“. Das bleibt, wenn die Quellen keine Verrundung enthalten, damit
  bestehende Referenzen unverändert bleiben.
- Machbarkeit belegt (Wegwerfskript): Tasche 30 × 20 × 12 mit R 3, gespiegelt, Volumen exakt wie gerechnet, ein Körper.
- **Selbst entschieden, Grenze:** Die Kopie trägt dieselbe Rundung wie die Quelle. SolidWorks rechnet die Verrundung an
  der Kopie neu. Gleich ist das, solange die Umgebung der Kopie gleich ist, etwa Taschen in einer Platte. Für andere
  Fälle prüft der Live-Abgleich. Eine Erkennung im Schnellbau und eine Meldung je Kopie gibt es nicht: Die Meldung
  stünde in jeder Spec mit gespiegelter Tasche und sagte nichts über den Einzelfall.
- Eine Fase-Knoten-Quelle (`typ: fase`) wird genauso behandelt (gleicher Code).

## 4. `austragung`

- Profil: `kreis` oder `rechteck` auf der Profilebene (Standard- oder Versatzebene), über die vorhandene `drahtzuege`.
- Pfad: `start` und `segmente` (`linie`, `bogen` mit `mitte`, `uhrzeigersinn`) auf der Pfadebene. Bögen über `_bogen`
  mit `gegen_uhrzeigersinn = not uhrzeigersinn`.
- `Solid.sweep(Face(profil), Wire(pfad))` (build123d 0.13, Standard-Übergang). Aufsatz `plus`, `schnitt: true` `minus`.
  Der Körper wird als Werkzeug gemerkt (Flächenanker, Muster, Spiegeln). Die Richtung ist die Tangente am Pfadanfang.
- Gültigkeit (Profil am Pfadanfang, tangentenstetig, Bogenradius) prüft `validieren` (`swki/spec/austragung.befunde`).
  Der Schnellbau prüft das nicht noch einmal.
- Machbarkeit belegt: Rechteck 6 × 4 und Kreis Ø 8 entlang Linie–Bogen–Linie ergeben A × Pfadlänge exakt.

## 5. Instanzpunkte gemusterter und gespiegelter Bohrungen

- Wie der Compiler (`swki/compiler/handler/muster.py`, `_instanzen_der_quellen`, `_kopien_eintragen`):
  - Jedes Muster bzw. jede Spiegelung rechnet je Bohrung die Kopien aus den Instanzpunkten seiner Quellen. Quellen sind
    die eigenen Positionen einer Bohrung oder die Kopien eines früheren Musters. Gerechnet wird mit `kopien_linear`,
    `kopien_kreis` und `kopien_spiegeln` aus `swki/spec/instanzen.py`.
  - Die Kopien werden an `FeatureInfo.punkte` der Bohrung angehängt. Das Muster merkt sie sich als `kopien` für spätere
    Muster.
- **Selbst entschieden:** Je Instanz auch die Achsrichtung (`FeatureInfo.richtungen`, parallel zu `punkte`). Sie wird
  mit derselben Transformation ohne Verschiebung gerechnet: gedreht beim Kreismuster, gespiegelt beim Spiegeln. So hat
  eine Kopie, die gegenüber der Quelle gedreht ist, ihre eigene Achse für `seite()`, Gelenke und die
  Parallelitätsprüfung. Die Bohrung selbst behält `richtung` wie heute.
- Reihenfolge wie `anzahl_instanzen`: Damit treffen `{feature, instanz: n, achse: true}` (Baugruppe, `abstand`) und
  `je_position` dieselben Lagen wie SolidWorks.
- **IndexError:** Eine Instanz über der Anzahl ist `SchnellbauFehler(ANKER)` mit Feature, Instanz und Anzahl.
  Instanzen auf Musterkopien lösen sich richtig auf.
- `je_position` über eine Bohrung eines Eigenteils: Die Seite mit `instanz: je` bleibt ungelöst wie heute, weil die
  Normteile nicht gebaut werden. Neu ist, dass die Instanzen gemusterter Bohrungen existieren. Die Zahl kommt aus
  `anzahl_instanzen`.

## 6. Drehsinn des Kreismusters

- SolidWorks dreht rechtsdrehend um die Richtung der Bezugsachse. Spike S20 d: `achse_y` zeigt nach −y, `achse_z`
  nach +z.
- Neue Konstante `BEZUGSACHSE` in `swki/spec/instanzen.py`:
  - y = (0, −1, 0) und z = (0, 0, 1): belegt durch Spike S20 d.
  - x = (1, 0, 0): Annahme. Sie folgt aus demselben Bildungsgesetz (zweite × erste Ebenennormale der Auswahl), das y und
    z erklärt. Ein Live-Test vor dem Abgleich belegt sie.
- Werkzeuge und Instanzpunkte im Schnellbau drehen um `BEZUGSACHSE`.
- Der Compiler liest die Richtung weiter live. Ein neuer Live-Test vergleicht `ctx.achsen` mit `BEZUGSACHSE` für x, y, z.
- Beim Vollkreis (360°) ändert sich die Geometrie nicht, nur die Instanzreihenfolge. Beim Teilkreis liegen die Kopien
  jetzt auf derselben Seite wie in SolidWorks.

## 7. Regeln und Skills

Design Konstruktionsstil §9 begrenzt die Übergangsregel auf „bis C3a“. Mit C3a fällt sie:
- Skill `konstruieren` Regel 4: Der Satz „und in Specs mit `optimierung` oder Simulation (…)“ entfällt.
- Skill `optimieren` §1: Der Satz zu Skizzen-Radius und `fase` entfällt.
- Hinweis `fertigung` (`swki/spec/hinweise.py`): Der Skizzen-Radius zählt weiter als Radius, denn er ist fachlich ein
  Radius. Sonst ändert sich nichts.
- Bestehende freigegebene Specs mit `optimierung` werden nicht umgeschrieben.

## 8. Prüfung

- TDD je Abschnitt in `tests/schnellbau/`. Analytische Volumen: Fase π·c·(r·c + c²/3), Verrundung (4 − π)·R²·Tiefe je
  Ecke, Austragung A × L. Instanzpunkte gleich `swki/spec/instanzen.py`, Teilkreis mit `achse_y`, Instanz über der
  Anzahl.
- `tests/schnellbau/test_stil_meldungen.py` wird zu Tests, die die Geometrie prüfen.
- `test_referenz.py` baut `austragung` mit und erwartet keinen Fehler mehr. Die Spannplatte läuft gegen die eigene
  `pruefung` mit `volumen: auto` und `huellquader: auto`.
- Live, nur wenn SolidWorks frei ist und keine andere Session es nutzt:
  1. Achsrichtungen (Live-Test, §6).
  2. `-m werkzeuge.schnellbau_abgleich --nur stehlager,stil`. Dazu kommt `("stil", "spannplatte.yaml")` in
     `REFERENZEN`. Der Lauf schreibt nur diese Einträge in `sw_referenz.json` neu.
  3. Ergebnis: Volumen, Hüllquader und STL (p99 ≤ 0,05 mm, max ≤ 0,1 mm) beider Backends gleich.
- pytest ganz grün.
- **Reihenfolge und Tor:** Baut der Schnellbau die Fase, weichen alle drei Stehlager-Einträge (`grundplatte`, `deckel`,
  `unterteil`) von der alten `sw_referenz.json` ab. Der Live-Abgleich ist darum ein hartes Tor vor dem PR, wie im
  Auftrag. Die Einträge werden nicht auf `xfail` gesetzt und nicht entfernt. Ist SolidWorks belegt, wartet der Abschluss
  auf ein freies SolidWorks. `BEZUGSACHSE` x geht nur belegt in den PR.

## 9. Abschluss

- Ergebnisse: `docs/schnellbau-c3a/ergebnisse.md`.
- Stand-Zeile in `CLAUDE.md` und Abschnitt „Schnellbau und Simulation“ ergänzen.
- PR gegen main. Mergen und `git push` nur mit ausdrücklichem OK des Nutzers.
