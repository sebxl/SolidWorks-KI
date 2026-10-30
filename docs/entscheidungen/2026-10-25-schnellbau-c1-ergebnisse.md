# Stufe C1 Schnellbau – Ergebnisse

Stand 25.10.2026. Spec: [2026-10-25-schnellbau-c1-design.md](../superpowers/specs/2026-10-25-schnellbau-c1-design.md). Code
`swki/schnellbau/` (teil, zerlegung, baugruppe, mjcf, befehle), Tests `tests/schnellbau/`, Live-Abgleich
`werkzeuge/schnellbau_abgleich.py`. Extra `schnellbau` (build123d 0.13.0, mujoco 3.16.0, optuna 5.0.0) in der swki-venv
nach Nutzer-OK vom 25.10.2026.

## Referenz-Suite durch beide Backends

`-m werkzeuge.schnellbau_abgleich`: Jede Referenz der Live-Suite wurde in SolidWorks gebaut und geprüft
(`swki durchlauf --freigeben --neustart` auf einer Kopie im Arbeitsordner, `SCHNELLBAU-ABGLEICH/SBREF-*`), zusammen in
rund 12 min. Danach wurde dieselbe Teil-Spec im Schnellbau gebaut (ms) und je Eigenteil verglichen.

| Teil-Spec | Volumen SolidWorks | Schnellbau | Abw. % | STL p99 / max mm |
|---|---|---|---|---|
| buchse (rotation, fase, Kreismuster) | 37 425,139 | 37 425,139 | −1·10⁻⁶ | 0,041 / 0,042 |
| auswerferhalteplatte (Normbohrungen, fase) | 692 653,890 | 692 653,890 | 0 | 0,026 / 0,038 |
| zentrieraufnahme (Formschräge ×4) | 315 014,796 | 315 014,796 | 0 | 0,048 / 0,069 |
| stehlager/grundplatte | 394 188,054 | 394 188,054 | 0 | 0,017 / 0,021 |
| stehlager/unterteil, deckel | – (Hüllquader gleich) | 288 993,700 / 97 821,764 | – | 0,071 / 0,074; 0,043 / 0,046 |
| schlitten/grundplatte, leiste, schlitten, hebel | 597 576,801 / 144 873,863 / 118 743,363 / 9 032,550 | gleich | ≤ 2·10⁻⁶ | ≤ 0,024 / 0,028 |
| zahnstange (Verzahnung) | 46 366,372 | 46 366,372 | −1·10⁻⁶ | 0,004 / 0,009 |
| ritzelwelle (2 Stirnräder) | 57 625,473 | 57 624,988 | −8,4·10⁻⁴ | 0,034 / 0,038 |
| antriebswelle (Stirnrad) | 105 798,187 | 105 797,912 | −2,6·10⁻⁴ | 0,031 / 0,035 |
| zahnstangentrieb/lagerbock, schlitten; motorhalter/grundplatte, motorbock | – (Hüllquader gleich) | – | – | ≤ 0,047 / 0,068 |
| formplatte | 3 069 575,535 | – | – | Skript-Notausgang f10: im Schnellbau bewusst nicht unterstützt |

- **STL:** Alle 19 Vergleiche sind nach `vergleich.py` „richtig“; die Reste entsprechen der Tessellierung der
  SolidWorks-STL.
- **Verzahnung:** Die kleine Volumenabweichung kommt vom Spline durch die Evolventenpunkte (SolidWorks `CreateSpline2`
  gegen OCC-Interpolation); er liegt unter 10⁻³ %.
- **Sollwerte im Repo:** Die SolidWorks-Messwerte stehen in `tests/schnellbau/sw_referenz.json` (19 Teil-Specs) und
  sind Sollwerte von `tests/schnellbau/test_referenz.py`, ohne SolidWorks: Volumen rel 10⁻⁷, mit Verzahnung 10⁻⁵;
  Hüllquader 10⁻⁴ mm.

## Baugruppen (ohne SolidWorks geprüft)

Lage, Körper und Gelenke der vier Referenz-Baugruppen gegen ihre eigenen `masse_pruefen` und `bewegungen.erwartet`:

| Baugruppe | Prüfung | Ergebnis |
|---|---|---|
| Stehlager | Achshöhe Unterteil, Deckel auf der Trennebene | 70 = 70, 70 = 70 |
| Linearschlitten | Hebel auf dem Schlitten; Schlittenhub; Hebelschwenk | 25 = 25; Schubgelenk +x, 0 … 220; Drehgelenk um −y in der Bolzenbohrung, 0 … 90°, Kind des Schlittens |
| Zahnstangentrieb | Achsabstand der Wellen; Ritzelachse über der Grundplatte; Endlagen | 75 = 75; 77,5 = 77,5; Zahnstange am Schlitten, Wellen drehen um +z / −z; Kopplungen k1/k2 gemeldet |
| Motorhalter | Bock auf der Grundplatte | gelöst; Kaufteil (Getriebe) nicht gebaut, gemeldet |

MJCF: Der Linearschlitten kompiliert in MuJoCo 3.16 mit Gelenkbaum Welt → Schlitten (slide) → Hebel (hinge); die
Massen stammen aus der B-Rep (Stahl 7850). Ein 10-mm-Klotz als Werkstück fällt auf die Grundplatte und liegt nach
0,5 s ruhig auf (Eindringung < 0,5 mm, verrutscht < 0,01 mm).

## Befunde beim Bau

- **`distance_to` eines Volumenkörpers ist innen 0.** Kantenanker `{feature, auswahl}` müssen gegen den Rand des
  Werkzeugs prüfen, sonst gehören die Wände einer späteren Tasche zum Grundkörper (Formplatte f4/f5). Ein eigener Test
  sichert das ab.
- **Freie Werkstücke brauchen den Körperrahmen im Schwerpunkt.** Liegt er 100 mm daneben, schaukelt ein ruhender Klotz
  dauerhaft auf zwei Kontakten.
- **Kontakt-Zeitkonstante ≥ 15 × Zeitschritt** (wie in den AP-6.8-Studien). Mit 3 × federt der Klotz dauerhaft nach.

## Grenzen (für C3)

- Lagelöser nur für Verschiebungen; eine nötige Drehung ist ein Fehler.
- Normteile und Kaufteile werden nicht gebaut (nur Achsen über Normteile weitergereicht).
- Kopplungen werden gemeldet, nicht als Gleichheitsbedingung übertragen.
- fase nur 45°.
- Kreismuster unter 360° und rotation unter 360° sind nicht gegen SolidWorks belegt (in der Referenz-Suite nicht
  vorhanden).
- skript ist bewusst nicht unterstützt.
