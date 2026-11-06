# Paket Konstruktionsstil – Ergebnisse

Design: `docs/superpowers/specs/2026-11-01-konstruktionsstil-design.md`, Plan: `docs/superpowers/plans/2026-11-06-konstruktionsstil.md`.

## Spike S20 (06.11.2026, SW 2025, `spikes/s20_konstruktionsstil.py`)

| Frage | Ergebnis |
|---|---|
| a – Muster aus Bohrung mit Senkung und Fase | Baut fehlerfrei. Das Muster übernimmt `f2`, `f2_senkung`, `f3` als Quellen, jede Kopie trägt die Fase (3 Kegelflächen im Muster). Volumen 115 590,9046 = Rechnung mit π·c·(r·c + c²/3) je Loch (r = Senkungsradius 5,5). |
| b – Gewinde M8, Fase 0,6 am Kernloch, Muster ×4 | Baut fehlerfrei, vier kosmetische Gewinde (`Bohrungsgewinde1…4`), `rebuild` leer. |
| c – Tasche + Verrundung R 3, gespiegelt an `rechts` und an einer Versatzebene | Baut fehlerfrei, Volumen exakt `VOLL − 2·(600 − (4 − π)·9)·8`. Lage der Kopie an der Versatzebene −5: x 0…30 (gespiegelt an x = −5). |
| d – Kreismuster 4 × bei 360° und 90° | Schritt 360/n bei 360°, sonst Winkel/(n − 1). Drehsinn rechtsdrehend um die **Richtung der Bezugsachse**: `achse_y` zeigt nach −y, `achse_z` nach +z. Der Handler kehrt beim Kreismuster nichts um. |
| e – Sweep Kreis Ø 8 entlang Linie–Bogen–Linie | `InsertProtrusionSwept4` und `InsertCutSwept5` mit Profilskizze Marke 1 und Pfadskizze Marke 4, alle übrigen Werte 0/False, `Merge`/`UseFeatScope`/`UseAutoSelect` True. Namen „Austragung1“ / „Schnitt-Austragung1“ (Typ `Sweep` / `SweepCut`). Volumen = π·r²·Pfadlänge exakt (5097,7205). |
| f – Definitionen | `LPattern`: `D1TotalInstances`, `D2TotalInstances`, `D1Spacing`, `PatternFeatureArray` (Namen der Quellen). `CirPattern`: `TotalInstances`, `Spacing` (Gesamtwinkel bei `EqualSpacing`). `MirrorPattern`: `PatternFeatureArray` lesbar, `Plane` liefert `None`. `Fillet`: `DefaultRadius`. `Chamfer`: `Type` 1, `GetEdgeChamferDistance(0)`, `EdgeChamferAngle`. |

Folgerung: Variante A aus dem Plan (Fase-Feature direkt hinter der Bohrung als Quelle des Musters) trägt, Variante B entfällt.
Instanzpunkte eines Kreismusters entstehen durch Drehung um die Achsrichtung aus `ctx.achsen`.
