# Stufe C1: Schnellbau und MJCF-Generator (zweites Backend der Spec)

Stand 25.10.2026. Grundlage: Entscheidung [2026-10-25-schnelle-konstruktionsschleife.md](../../entscheidungen/2026-10-25-schnelle-konstruktionsschleife.md)
(Ansatz C), Spike S-Schleife-1 ([Ergebnisse](../../entscheidungen/2026-10-25-spike-s-schleife-1.md), Code `spikes/s18_*`).
Nutzer 25.10.2026: „Stufe C1 angehen: Schnellbau und MJCF-Generator als richtigen swki-Code mit Tests (Referenz-Suite
durch beide Backends)“; Pakete als Extra `schnellbau` in die swki-venv.

## 1 Ziel

Eine Teil- oder Baugruppen-Spec wird ohne SolidWorks in Millisekunden bis Sekunden zu exakter Geometrie (B-Rep,
OpenCascade über build123d/OCP) und zu einem MuJoCo-Modell. SolidWorks bleibt der verbindliche Bau; der Schnellbau ist
ein zweites Backend derselben Spec und wird über die Referenz-Suite gegen SolidWorks gehalten.

Nicht in C1: Optuna-Läufer und Block `optimierung` (C2), automatische Prüfstufen 3/4 (C4), äußere Schleife (C5),
Drehungen im Lagelöser, Kaufteil-STEP und Normteile im Simulationsmodell.

## 2 Bausteine

| Modul | Inhalt |
|---|---|
| `swki/schnellbau/teil.py` | Teil-Spec → `Teil` (Solid, Feature-Werkzeuge, Bohrungsachsen, Bezugsebenen, Zeiten). Gleiche Hilfen wie der Compiler: `swki.compiler.skizze.modellpunkt`, `swki.spec.ausdruck.auswerten`, `swki.spec.konturen`, `swki.spec.normen` (Bohrungstabelle), `swki.verzahnung` (Profil), `swki.formschraege`. |
| `swki/schnellbau/zerlegung.py` | B-Rep → konvexe Stücke (Raumteilung an Flächenebenen und Achsebenen konkaver Zylinder, Pfeilhöhe ≤ Toleranz); Summe der Volumen exakt. |
| `swki/schnellbau/baugruppe.py` | Baugruppen-Spec → Lage je Eigenteil (nur Verschiebungen; eine nötige Drehung ist ein Fehler), Gelenke aus `grenze_abstand` (Schub) und `grenze_winkel` (Dreh). |
| `swki/schnellbau/mjcf.py` | Baugruppe + Simulations-Datei → MJCF (Körper je Gelenk, Gelenkbereich, Stücke als Mesh-Geoms, Reibung/Stoßzahl je Werkstoff, Trägheit aus der B-Rep, `angle="radian"`). |
| `swki/schnellbau/stl.py` | STL-Export (Teilkoordinaten, mm). |
| CLI | `swki schnellbau teil <spec> [--stl <datei>] [--setze NAME=wert …]`, `swki schnellbau mjcf <baugruppe> <sim.yaml> <aus.xml>` – Ausgabe JSON wie die übrigen Befehle. |
| `werkzeuge/schnellbau_abgleich.py` | Referenz-Suite durch beide Backends: SolidWorks baut und prüft jede Referenz (eigener Ordner im Arbeitsordner), exportiert STL; der Schnellbau baut dieselbe Spec; Vergleich mit `werkzeuge/messstand/vergleich.py` und gegen das von SolidWorks gemessene Volumen. Schreibt die Sollwerte `tests/schnellbau/sw_referenz.json`. |

## 3 Semantik (wie der SolidWorks-Compiler)

- Skizzen: (u, v) je Standardebene wie `modellpunkt`; Bögen gegen den Uhrzeigersinn in (u, v); Eckradien tangential;
  geschachtelte Konturen gerade/ungerade.
- Ende: blind, mittig, durch_alles, bis_flaeche, versatz_von_flaeche, umkehren; Aufsatz entlang Skizzennormale,
  Schnitt dagegen; Formschräge mit `querschnitt` kleiner/groesser aus Sicht der Skizze (`swki.formschraege`).
- Flächenanker `{feature, flaeche}`: Ebene der äußersten Werkzeugfläche in Richtung (Schnitt: Werkzeugnormale
  entgegengesetzt), `{nahe}`: nächste Fläche des Körpers.
- Kantenanker `nahe`, `{feature, auswahl}` (Kanten der Flächen des Features, die auf dem Werkzeugrand liegen;
  `senkrechte_kanten` parallel zur Feature-Richtung), `{feature, kanten_an}`.
- Muster linear/kreis und spiegeln wiederholen die Werkzeuge der genannten Features mit ihrer Operation (Aufsatz,
  Schnitt, Bohrung); Achsen x/y/z durch den Ursprung. Kreismuster: gleich verteilt über `winkel` (360 → 360/n).
- referenz: Ebene (Standardebene mit Abstand, `umkehren` legt sie auf die andere Seite) oder Achse x/y/z.
- Bohrungen nach `swki/wissen/bohrungsnormen.yaml` (Kernloch mit Bohrspitze `bohrspitze_grad`, Senkungen); Gewinde
  kosmetisch.
- verzahnung: Profil aus `swki.verzahnung.aus_feature` (Linien, Bögen, Splines) → Aufsatz um `breite`.
- skript → `SCHNELLBAU_NICHT_UNTERSTUETZT` (der Notausgang hat kein Gegenstück); ebenso jede andere Lücke, mit
  Feature-ID. Nie still weglassen.

## 4 Prüfung

1. Einheitstests ohne SolidWorks (`tests/schnellbau/`): je Feature analytisch bekannte Volumen/Hüllquader; Zerlegung
   (Volumen exakt, Stücke konvex); Lage und Gelenke der Referenz-Baugruppen gegen `bewegungen.erwartet`; MJCF
   kompiliert in MuJoCo, Gelenkbereiche gleich der Spec.
2. Referenz-Suite durch beide Backends: `tests/schnellbau/test_referenz.py` vergleicht den Schnellbau jeder
   Referenz-Spec mit den von SolidWorks gemessenen Werten in `sw_referenz.json` (Volumen ≤ 0,01 %, Hüllquader
   ≤ 0,001 mm). Die Werte erzeugt `werkzeuge/schnellbau_abgleich.py` live; dort zusätzlich STL-Vergleich (p99 ≤ 0,05 mm,
   max ≤ 0,1 mm).
3. Tests, die build123d brauchen, überspringen sich ohne das Extra (`pytest.importorskip`).

## 5 Fehlercodes

`SCHNELLBAU_NICHT_UNTERSTUETZT` (Feature, Element, Anker, Drehung im Lagelöser), `SCHNELLBAU_GEOMETRIE` (OCC-Operation
ohne Ergebnis, mehrere Körper), `SCHNELLBAU_ANKER` (Anker nicht/mehrdeutig gefunden) – mit Spec-Pfad wie bei
`BauFehler`.
