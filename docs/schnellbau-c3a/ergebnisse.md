# Stufe C3a – Ergebnisse

Stand 07.11.2026, Branch `claude/schnellbau-c3a-95dfd0`. Unterlagen:
- Design: `docs/superpowers/specs/2026-11-06-schnellbau-c3a-design.md` (Nutzer-Freigabe 07.11.2026)
- Plan: `docs/superpowers/plans/2026-11-07-schnellbau-c3a.md`
- Umsetzung: Task 1–5 je ein Subagent mit Task-Review, Task 6 live nach Freigabe des Nutzers

## Umsetzung

| Punkt | Umsetzung | Belege |
|---|---|---|
| Feld `fase` an Bohrungen | Kegelstumpf je Position am Eintritt (r + c → r über c), Teil des Bohrungswerkzeugs. Maße aus `swki/spec/bohrungsfase.py`. Muster, Spiegeln und `bohrungen=False` nehmen die Fase mit dem Werkzeug mit. Die Meldung „nicht gebaut“ entfällt. | `tests/schnellbau/test_stil.py`; live Grundplatte Stehlager |
| `verrundung`/`fase` in Musterquellen | Steht der Knoten in den `features` eines späteren Musters, merkt der Schnellbau Zuwachs und Abtrag als Differenzkörper (`FeatureInfo.teile`). Kopiert wird in Quellreihenfolge. Ohne solche Quellen bleibt der alte Weg (erst plus, dann minus). Ein Fehler der Differenz ist `SCHNELLBAU_GEOMETRIE`, nicht still. | `tests/schnellbau/test_stil.py` (Tasche gespiegelt/gemustert, konvexe Kante, Fase-Knoten) |
| `austragung` | Profil (Kreis oder Rechteck) über `drahtzuege`, Pfad aus `_linie`/`_bogen` (`uhrzeigersinn`), `Solid.sweep`, Aufsatz oder Schnitt. Richtung = Tangente am Pfadanfang. | `tests/schnellbau/test_stil.py` (A × Pfadlänge exakt); live Spannplatte |
| Instanzpunkte | `FeatureInfo.punkte`/`richtungen` je Instanz, Kopien wie `swki/compiler/handler/muster.py` (`_instanzen_der_quellen`) über `swki/spec/instanzen.py`, auch mit `bohrungen=False`. | `tests/schnellbau/test_instanzen.py` (Live-Werte aus `test_live_musterinstanzen.py`, `anzahl_instanzen`) |
| IndexError `instanz` | `SchnellbauFehler(ANKER)` mit Komponente, Feature, Instanz und Anzahl. Instanzen auf Musterkopien lösen richtig auf. | `tests/schnellbau/test_instanzen.py` |
| Drehsinn Kreismuster | `BEZUGSACHSE = {x: +x, y: −y, z: +z}` in `swki/spec/instanzen.py`. Werkzeuge und Punkte drehen darum. | live `test_bezugsachsen_wie_konstante` (x, y, z gegen SolidWorks) |
| Skills | Regel „Skizzen-Radius bis C3a“ aus `konstruieren` (Regel 4) und `optimieren` (§1) gestrichen. Hinweis `fertigung` unverändert. | Diff |

## Live-Abgleich (07.11.2026, SW 2025)

- `tests/live_einzeln.py tests/live/test_live_musterinstanzen.py`: 2/2 bestanden. Die Annahme `achse_x` = +x ist damit belegt.
- `-m werkzeuge.schnellbau_abgleich --nur stehlager,stil`, frisches SolidWorks je Referenz:

| Teil | Volumen SolidWorks | Schnellbau | Hüllquader | STL p99 / max mm |
|---|---|---|---|---|
| stehlager/grundplatte | 394 172,607 | 394 172,607 | gleich | 0,017 / 0,021 |
| stehlager/unterteil | – (Hüllquader) | 288 970,111 | gleich | 0,072 / 0,074 |
| stehlager/deckel | – (Hüllquader) | 97 809,721 | gleich | 0,043 / 0,046 |
| stil/spannplatte | 438 270,870 | 438 270,870 | gleich | 0,013 / 0,086 |

- Unterteil p99 0,072 > 0,05 wie schon in C1 (0,071). Das ist die Tessellierung der SolidWorks-STL; `vergleich.py` urteilt „richtig“.
- Bauzeit Schnellbau: Spannplatte 2,6 s, Stehlager-Teile 2,1–2,4 s. SolidWorks-Durchlauf: Spannplatte 56 s, Stehlager 84 s.
- `sw_referenz.json` hat neue Werte für `stehlager/*` (lauf-4) und den neuen Eintrag `stil/spannplatte`.
- pytest: 2387 bestanden (ohne SolidWorks).

**Befund am Werkzeug:** Der erste Abgleich nahm die Kopie `SBREF-stehlager` aus dem C1-Lauf im Oktober wieder, und deren
Specs hatten noch keine Fasen. Dadurch stimmten SolidWorks und Schnellbau nur scheinbar überein (394 188,054). Seit
Commit 17d5ba8 kopiert `auftrag_aktualisieren` bei jedem Lauf die aktuellen Referenz-Specs über den Auftrag. Frühere
Läufe bleiben erhalten. Getestet in `tests/schnellbau/test_abgleich_kopie.py`.

## Grenzen (selbst entschieden oder gefunden)

- **Kopierte Verrundung:** Die Kopie trägt dieselbe Rundung wie die Quelle. SolidWorks rechnet die Verrundung an der
  Kopie neu. Gleich ist das, solange die Umgebung gleich ist, wie bei Taschen in einer Platte. Eine Meldung je Kopie gibt
  es nicht (Design §3).
- **Austragung, die sich beim Spiegeln selbst überlappt** (z. B. Pfad auf der Spiegelebene): Der Schnellbau meldet
  `SCHNELLBAU_GEOMETRIE` („0 Volumenkörper“), SolidWorks baut einen Körper.
- **Spiegelbild auf einer vorhandenen Bohrung:** Der Schnellbau meldet „Schnitt trifft kein Material“.
- **Fasenkegel** setzt eine volle Kreiskante in einer ebenen Eintrittsfläche voraus, wie der Compiler.

## Offen (kleine Review-Befunde)

- Volumentests der Fase binden die Kegelorientierung nicht. Der Live-Abgleich der Grundplatte belegt sie.
- Kein Einzeltest für `bohrung` mit `senkung` und `fase`.
- `senkschraube` mit `fase` ergibt im Schnellbau einen KeyError. `validieren` lehnt die Kombination vorher ab.
- `_muster_anwenden`: Der Abschlussblock steht doppelt. `_kantenarbeit` ist unklar benannt.
- Kein Test `muster_kreis` mit Verrundung als Quelle.
- Ein Muster von einem Muster mit gemischter Operation endet mit `NICHT_UNTERSTUETZT`; das ist ungetestet.
- `baugruppe.seite` fängt `instanz < 1` nicht ab.
- Kreismuster: Der Schritt prüft `abs(w − 360) < 1e-9`, `kopien_kreis` dagegen `w == 360`.
- `referenz`-Achse y zeigt nach +y, die Bezugsachse des Kreismusters nach −y. Wirkt sich nur aus, wenn eine Referenz
  den Richtungssinn braucht.
- Die Fehlermeldung „0 Volumenkörper“ nennt keine Feature-ID.

## Nebenbei übernommen

- Commit 53873f2 aus `claude/bestandsdateien-etappe-2-3e51d9`: `sw_neustart` startet SolidWorks minimiert und ohne
  Fokus (Schalter `solidworks_hintergrund`, Nutzer 07.11.2026). Übernommen auf Bitte der Session AP 6.8 Rev1.
