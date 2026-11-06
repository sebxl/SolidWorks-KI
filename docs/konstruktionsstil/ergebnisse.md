# Paket Konstruktionsstil – Ergebnisse

Design: `docs/superpowers/specs/2026-11-01-konstruktionsstil-design.md`, Plan: `docs/superpowers/plans/2026-11-06-konstruktionsstil.md`.

## Ergebnis in Kürze

Gebaute Teile bekommen jetzt einen Feature-Baum nach dem Standard des Nutzers (Rückfrage 01.11.2026):
- Formen werden gespiegelt und gemustert, Lochreihen ab 3 Stück gemustert.
- Innenecken gefräster Teile folgen der Fräserregel R ≥ T/5.
- Bohrungseintritte bekommen eine Fase (Stift, Durchgang 0,5; Gewinde Ansenkung auf Nenn-Ø).
- Kanäle und Nuten gehen als `austragung`.

Neu ist:
- Hinweise in `validieren`: Kandidaten für Muster und Spiegeln, Fräserradius, Bohrung ohne Fase.
- Feld `fase` an Bohrungen, Typ `austragung`.
- Instanzen gemusterter Bohrungen sind für `instanz` und `je_position` ansprechbar.
- `swki pruefen` hat die Prüfungen `muster`, `kanten` und `bohrbild`.

## Ausgangsmaß und Endmaß

**Bestand (49 Teil-Specs: 22 Referenzen, 27 AP 6.8; vor dem Paket):**
- 200 Features, davon 77 Extrusionen, 53 Normbohrungen, 28 Schnitte, 16 Bohrungen.
- Stilfeatures: 5 Fasen, 4 Verrundungen, 2 Muster, 1 Spiegeln, keine Fase an einem Bohrungseintritt.

**Neue Hinweise auf genau diesen Specs** (`-m werkzeuge.stil_zaehlung`, ohne die Spannplatte):

| Hinweis | Anzahl | Bedeutung |
|---|---|---|
| `fertigung`, Regel 6 | 62 | Bohrungseintritt ohne Fase |
| `fertigung`, Regel 8 | 10 | Innenecke unter R ≥ T/5 (AP 6.8: Fallschacht, Prüfkanal, Rutsche, Schieber, Trichter, Abdeckung) |
| `zusammenfassen`, Regel 3 | 1 | Lochreihe 3 × in `anschlussplatte` (Teilung 37,5) |

- Der ältere `zusammenfassen`-Hinweis „Senkung wie ISO 4762“ in `formplatte` bleibt.
- Die Specs selbst sind unverändert, außer dem Stehlager. Sie bleiben Bauweg im alten Stil; ihre Tests ignorieren `fertigung`.

**Referenzteil Spannplatte** (`tests/referenz/stil/`; der alte Stil steht zum Vergleich unter `vorher/`):

| | vorher (alte Regeln) | nachher (neuer Stil) |
|---|---|---|
| Knoten | 4: Platte, beide Taschen in einer Skizze mit Skizzen-Radius, 5 Gewindepositionen, 2 Stifte | 8: Platte, Tasche, Verrundung R 4, Spiegeln, Gewinde, Muster × 5, Stifte, Kabelnut `austragung` |
| Features im Baum | 4 (Nut nur als Notausgang-Skript möglich, fehlt) | 10 (dazu `g1_fase`, `st_fase`) |
| Hinweise `validieren` | 2 × `zusammenfassen` (spiegelbildliche Profile, Lochreihe), 2 × `fertigung` (Eintritte ohne Fase) | keine |
| Bau | – | 6,5 s, 1 Körper, 0 Gleichungen |
| `swki pruefen` | – | 0 Mängel; Volumen 438 270,87 = Soll aus `volumen: auto` (Verrundung, Fasen und Austragung eingerechnet), `muster`, `kanten`, `bohrbild` grün, `instanz` 1 → 5 der Musterreihe = 120 |
| Prüfer | – | Lauf 1 Mangel: Screenshots ohne Körper, nur zwei Hilfsebenen. Lauf 2 nach dem Ausblenden der Versatzebenen bestanden. |

Konstruktionsreview der Spannplatte: keine Befunde.

**Stehlager** (`tests/referenz/stehlager/`):
- Grundplatte, Unterteil und Deckel tragen jetzt `fase` an allen Bohrungseintritten (Gewinde `nenn`, sonst 0,5).
- Die Gewindeprüfung der Baugruppe zieht den Teil der Ansenkung von der Soll-Überlappung ab.

## Was wo umgesetzt ist

| Lücke (Design §6) | Umsetzung | Nachweis |
|---|---|---|
| Regel 3 riet von Muster/Spiegeln ab | `_REGEL_3` entfernt; `muster_kandidaten` meldet Lochreihen ≥ 3, gleiche Formen in Reihe, zwei spiegelbildliche Formen, spiegelbildliche Profile einer Skizze | `tests/spec/test_hinweise_stil.py` |
| Fräserradius, Bohrungseintritt | `fertigung_hinweise` (nicht in Bestandsdateien) | `tests/spec/test_hinweise_fertigung.py` |
| Bohrungsfase | Feld `fase` (Schema, `validieren`), Feature `<id>_fase` hinter Bohrung/Senkung (`swki/compiler/handler/kanten.py`), Maß `D1@<id>_fase` im Maßprotokoll (nicht bei `nenn`) | `tests/spec/test_fase_feld.py`, `tests/compiler/test_bohrungsfase.py`, live `test_live_bohrungsfase.py` |
| `volumen: auto` mit Verrundung/Fase | Verrundung `senkrechte_kanten` auf Rechteck/Polygon wie Skizzen-Radius; Fase π·c·(r·c + c²/3) je Position | `tests/pruefung/test_volumen_stil.py`, live exakt |
| Instanzen gemusterter Bohrungen | `swki/spec/instanzen.py`; Muster-Handler hängen die Kopien an die Bohrung (Protokoll-`punkte`, `traeger`); Messung, Baugruppen-Referenzen und `je_position` zählen sie | `tests/spec/test_instanzen.py`, `tests/baugruppe/test_plausibel.py`, live `test_live_musterinstanzen.py` |
| Musteranzahl ungeschützt | Prüfung `muster`: Definition gegen aktuelle Spec, Formmuster zusätzlich gegen die freigegebene Kopie | `tests/pruefung/test_muster_kanten.py` |
| Kantenmaße nur über Volumen | Prüfung `kanten`: Radius bzw. Fasenmaß aus der Definition gegen die Kopie | ebenda |
| Lochreihe zwischen Positionen und Muster | `normbohrungen` vergleicht die Punktzahl mit der aktuellen Spec, `bohrbild` die Instanzzahl je Art/Größe/Tiefe mit der Kopie | ebenda |
| Gewinde mit Ansenkung | `ueberlappung_soll(…, ansenkung)` geschlossen bzw. numerisch | `tests/baugruppe/test_geometrie_baugruppe.py` |
| Neuer Typ | `austragung` (Kreis/Rechteck entlang offenem, tangentenstetigem Pfad; Bögen auch im Uhrzeigersinn) | `tests/spec/test_austragung.py`, live `test_live_austragung.py` |
| Hilfsebenen im Bild | Versatzebenen werden nach dem Anlegen ausgeblendet (alle Handler) | live `test_live_austragung.py` |

## Spike S20 (06.11.2026, SW 2025, `spikes/s20_konstruktionsstil.py`)

| Frage | Ergebnis |
|---|---|
| a – Muster aus Bohrung mit Senkung und Fase | Baut fehlerfrei. Das Muster übernimmt `f2`, `f2_senkung`, `f3` als Quellen, jede Kopie trägt die Fase (3 Kegelflächen im Muster). Volumen 115 590,9046 = Rechnung mit π·c·(r·c + c²/3) je Loch (r = Senkungsradius 5,5). |
| b – Gewinde M8, Fase 0,6 am Kernloch, Muster ×4 | Baut fehlerfrei, vier kosmetische Gewinde (`Bohrungsgewinde1…4`), `rebuild` leer. |
| c – Tasche + Verrundung R 3, gespiegelt an `rechts` und an einer Versatzebene | Baut fehlerfrei, Volumen exakt `VOLL − 2·(600 − (4 − π)·9)·8`. Lage der Kopie an der Versatzebene −5: x 0…30 (gespiegelt an x = −5). |
| d – Kreismuster 4 × bei 360° und 90° | Schritt 360/n bei 360°, sonst Winkel/(n − 1). Drehsinn rechtsdrehend um die **Richtung der Bezugsachse**: `achse_y` zeigt nach −y, `achse_z` nach +z. Der Handler kehrt beim Kreismuster nichts um. |
| e – Sweep Kreis Ø 8 entlang Linie–Bogen–Linie | `InsertProtrusionSwept4` und `InsertCutSwept5` mit Profilskizze Marke 1 und Pfadskizze Marke 4, alle übrigen Werte 0/False, `Merge`/`UseFeatScope`/`UseAutoSelect` True. Namen „Austragung1“ / „Schnitt-Austragung1“ (Typ `Sweep` / `SweepCut`). Volumen = π·r²·Pfadlänge exakt (5097,7205). |
| f – Definitionen | `LPattern`: `D1TotalInstances`, `D2TotalInstances`, `D1Spacing`, `PatternFeatureArray` (Namen der Quellen). `CirPattern`: `TotalInstances`, `Spacing` (Gesamtwinkel bei `EqualSpacing`). `MirrorPattern`: `PatternFeatureArray` lesbar, `Plane` liefert `None`. `Fillet`: `DefaultRadius`. `Chamfer`: `Type` 1, `GetEdgeChamferDistance(0)`, `EdgeChamferAngle`. |
| g – Spannplatte Lauf 1 ohne Körper im Bild (`spikes/s20f_sichtbarkeit.py`, `s20g_datei.py`) | Körper nach jedem Feature sichtbar, die gespeicherte Datei auch. Eine neue Aufnahme derselben Datei zeigt die Platte. Der leere Bild-Lauf war ein Darstellungsaussetzer; nicht nachgestellt. SolidWorks hatte zu der Zeit eine fremde Baugruppe offen. Sichtbar blieben zwei Versatzebenen: Sie werden jetzt ausgeblendet. |

Folgerung: Variante A aus dem Plan (Fase-Feature direkt hinter der Bohrung als Quelle des Musters) trägt, Variante B entfällt.
Instanzpunkte eines Kreismusters entstehen durch Drehung um die Achsrichtung aus `ctx.achsen`.

## Selbst entschiedene Punkte und Grenzen

- **`fertigung` in Bestandsdateien:** nicht gemeldet (Skill `aendern`: nichts aufräumen, Stil des Kollegen bleibt).
- **Fehlalarme des Fräserradius:** abgefangen sind Schnitte über den Rand des Materials (Absatz, Seite weg) und
  `mittig` (Tiefe quer zur Fräsrichtung).
  - Weiter nicht erkannt: Radien aus Verrundungen mit `nahe`-Anker.
  - Weiter nicht unterschieden: gedruckte Teile und Ersatzkörper von Kaufteilen. Die Freigabe-Vorlage begründet solche
    Hinweise.
- **`bohrbild`** vergleicht Instanzzahlen, keine Lagen. Lagen prüfen wie bisher `masse_pruefen` und der Steckbrief. Für
  `normbohrung` vergleicht er schärfer als vorher, `bohrung` wird jetzt mitgezählt.
- **Alte Referenzen** bleiben im alten Stil. Ihre Sollwerte und Läufe gelten weiter; ihre Tests „ohne Hinweise“ ignorieren
  `fertigung`.
- **Bauzeit:** Ein Fase-Feature kostet ca. 0,5–6 s (Stufe 2c). Die Spannplatte mit 10 Features baute in 6,5 s. Das
  BTP-Mittel ist nicht neu erhoben.

## Für Stufe C3a (Schnellbau)

- **Was der Schnellbau heute nicht kann:**
  - `fase` an Bohrungen: nur `meldungen`, der Körper hat keine Fase; Teilmeldungen gehen in die Baugruppenmeldungen.
  - `austragung`: `SCHNELLBAU_NICHT_UNTERSTUETZT`.
  - `verrundung` in Quellen von Muster oder Spiegeln: `NICHT_UNTERSTUETZT`. Darum behalten Specs mit `optimierung`
    vorerst den Skizzen-Radius (Skill `optimieren`).
- **Was C3a übernehmen muss:** die Instanzpunkte gemusterter Bohrungen. `swki/schnellbau/baugruppe.py` nutzt nur die
  `punkte` der Bohrung selbst; für `je_position` über Musterkopien müssen sie wie im Compiler angehängt werden
  (`swki/spec/instanzen.py` hat die reinen Transformationen).
- **`tests/schnellbau/sw_referenz.json`:** Der Eintrag `stehlager/grundplatte` stammt aus einem Lauf ohne Fasen. Mit
  `-m werkzeuge.schnellbau_abgleich` neu erzeugen, sobald SolidWorks frei ist.

## Regression

- `.venv\Scripts\python.exe -m pytest`: grün (Stand des letzten Laufs in diesem Abschnitt unten).
- Live gelaufen:
  - `test_live_bohrungsfase`, `test_live_musterinstanzen`, `test_live_muster`, `test_live_austragung`,
    `test_live_endbedingungen`, `test_live_pruefen`, `test_live_pruefen_normbohrung`
  - Referenz Spannplatte (`test_referenz_besteht[stil-spannplatte.yaml]`)
