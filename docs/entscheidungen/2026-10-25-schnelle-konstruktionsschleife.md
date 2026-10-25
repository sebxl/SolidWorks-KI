# Schnelle Konstruktionsschleife: Zwischenmodell, MuJoCo, Optuna, SolidWorks-Nachbau

Stand 25.10.2026. Recherche- und Konzeptauftrag (nichts gebaut, nichts installiert, SolidWorks nicht gestartet).
Anhang mit Werkzeugvergleich und Quellen: [2026-10-25-schnelle-konstruktionsschleife-recherche.md](2026-10-25-schnelle-konstruktionsschleife-recherche.md).

## Kurzfassung

**Empfehlung: Ansatz C „Eine Spec, zwei Backends“.** Die `swki`-Spec bleibt die einzige Quelle der Geometrie. Neben
dem SolidWorks-Compiler bekommt `swki` einen zweiten, schnellen Bauweg (Schnellbau mit OpenCascade über build123d/OCP,
exakte B-Rep, ohne SolidWorks). Ein MJCF-Generator macht daraus das MuJoCo-Modell (Kollisionskörper, Gelenke aus den
Grenzverknüpfungen). Dazu kommt ein neuer Spec-Block `simulation`/`optimierung` mit Szenarien, Zielwert und
Stellschrauben. Optuna verändert nur `parameter` der Spec. Der Gewinner wird mit derselben Spec in SolidWorks gebaut.
„1:1“ ist dann eine Eigenschaft des Aufbaus und hängt nicht an einer Übersetzung. Nachgewiesen wird es mit dem
vorhandenen STL-Vergleich (`werkzeuge/messstand/vergleich.py`) und einer Gegenprobe-Simulation auf der SolidWorks-Geometrie.

Erwartetes Tempo (Schätzung, im Spike zu messen): eine Optuna-Probe mit 200 Monte-Carlo-Läufen dauert rund 7–10 s Wandzeit
auf den 16 Kernen dieses Rechners. Das sind etwa 400–500 Proben je Stunde, über Nacht 4000–5000. Mit SolidWorks sind es
heute 4–10 min je Bau- und Prüfzyklus der Prüfstation, nur eine Instanz und 10–11 GB Speicher, also 6–15 Zyklen je
Stunde, und das ohne Funktionsprüfung.

Der wichtigste Befund aus den bisherigen Studien: Die großen Sprünge kamen aus **Topologie-Ideen** (Trapez-Stirn,
Prallkaskade, Fangwand, Keilwangen G1c). Feinabstimmung brachte weniger. Optuna findet solche Ideen nicht. Die Schleife
hat deshalb zwei Ebenen: Claude schlägt Varianten der Spec vor (Topologie), Optuna stimmt ihre Zahlen ab.

Erster Schritt: Spike **S-Schleife-1 „Weiche G1c aus der Spec“** (§7). Dafür braucht es die Freigabe des Nutzers für
die Installation von vier Paketen in einer eigenen venv (§7.4).

## 1 Ausgangslage

### 1.1 Was die bisherigen MuJoCo-Studien gemacht haben (AP 6.8, 16.–19.10.2026)

| Studie | Frage | Umfang | Rechenzeit |
|---|---|---|---|
| `fallschacht-lauf-20` | Verklemmt das Messer nach dem Fall? Trifft es die Linse? | 4 Szenarien × 2000 Würfe | ≈ 5–8 min auf 12 Kernen |
| `varianten-2026-10-16` | Welcher Zulauf hebt den Anteil „brauchbar“ (64,8 % → 98,4 %)? | 13–15 Varianten an einem Nachmittag, je 2000 Würfe | 6–15 min je Variante ab Freigabe der Geometrie |
| `v-schieber-2026-10-16` | Platziert die Schieberstirn das Messer randfrei? | ≈ 10 Stirnformen in 90 min ohne Nutzer, je 1992–3984 Startlagen + Raster | 10–40 min je Variante |
| `sortierschritt-2026-10-18` | Fällt das Messer in den richtigen Schacht? | 21 + 11 + 16 Fälle × 1992 Läufe | ≈ 4 h für die ganze Studie |

Gemeinsames Modell: MuJoCo 3.16, Starrkörper mit weichen Kontakten, Zeitschritt 10–20 µs, rund 0,5–0,6 s CPU je Lauf.
Die Geometrie besteht aus Quadern und konvexen Prismen in Maschinenkoordinaten. Das Messer kommt aus der echten Kontur,
von Hand in 2–6 konvexe Teile zerlegt. Schieber und Keil sind kinematisch geführte Schubgelenke. Reibwert und
Stoßzahl stehen je Werkstoffpaarung als Literaturwert in der Tabelle, die Stoßzahl ist über `kalib.py` auf `solref`
abgebildet. Ergebnisse sind Anteile mit 95-%-Wilson-Bereich, Lauf für Lauf deterministisch.

### 1.2 Wo es hakte

1. **Geometrie von Hand übertragen.** Jedes `modell.py` schreibt die Maße aus den YAML-Specs und dem Prüfbericht als
   Python-Konstanten ab, z. B. `sortierschritt/skripte/modell.py`: „Alle Maße aus den Specs … und mit dem Prüfbericht
   von lauf-27 verglichen“. Die Fehler dabei fand meist der Nutzer an den Bildern:
   - Das Tubus-Rohr ragte 4,9 mm in den Schacht. Damit sind 20 Varianten nur eingeschränkt gültig.
   - Der Schieber war zu niedrig.
   - Die Simulation hatte eine Stufe, die nicht in der Spec steht.
   - Eine konstruierte statt der echten Lage führte zur Kollision mit der Klemmleiste.
   - Pos. 2/3 standen in Konstruktionsvorgabe und Steuerung noch auf 28/58 statt 52/82.
   - In `layout.yaml` gibt es einen Kantenradius R 1, der in der Spec fehlt.

   Seitdem gilt: Vor jedem Rechnen wird die Geometrie als 3D-Wiedergabe gezeigt, und der Nutzer gibt sie frei. Für
   eine Schleife ohne Menschen ist genau das der Engpass.
2. **Kontaktmodell an dünnen Kanten.**
   - Treffer auf die 2 mm dicke Trennwand sind numerisch empfindlich: Je nach Zeitschritt und Kontaktsteifigkeit
     liegt der Anteil „falsch“ zwischen 26 und 43 %.
   - Läufe mit Energiezuwachs werden ausgeschlossen (0,3–13 %).
   - `margin`/`gap` ließen ein ruhendes Messer wandern.
   - Ein eingesetzter Glaszylinder erzeugte unphysikalische Stöße; er wurde durch ein flächengleiches Rechteck ersetzt.
3. **Kalibrierung.**
   - Reibwerte und Stoßzahlen sind geschätzt, Versuche nach Ü11/Ü13 stehen aus.
   - Die abgebildete Stoßzahl hängt vom Kippwinkel ab (Soll 0,40 → 0,46 / 0,40 / 0,29).
   - Das Bewegungsprofil der Festo-Zylinder ist angenommen.
4. **Rückweg nach SolidWorks.** Die Ergebnisse gingen über Übergabedokumente (`uebergabe_weiche_g1c.md`) von Hand in
   die Specs. Beim Nachrechnen fiel eine falsche Wangenhöhe auf („16 … 7“ statt „10 … 16 mm“).
5. **Mensch im Takt.** Jede Variante brauchte eine Geometriefreigabe. Zwei Sitzungen, die gleichzeitig rechnen,
   verdoppeln die Zeit; alle Kerne waren belegt.

### 1.3 SolidWorks-Weg heute (Laufzeit-Audit, BTP Umbau 2)

| Aufgabe | ganzer Agentenlauf | davon `swki durchlauf` (bauen + prüfen) | Speicher |
|---|---|---|---|
| Einzelteil (Durchlicht, Kamera, Zentrieraufnahme) | 148–220 s | 16–19 s | ≈ 3,4 GB |
| Stehlager | 336–343 s | 35–37 s | 4,6–6,4 GB |
| Prüfstation AP 6.8 (Änderung) | 454–635 s | 237–256 s | 10,6–11,2 GB |

SolidWorks läuft in nur einer Instanz; die Prüfstation braucht vor Bauen und Prüfen einen frischen Start. 1000
Iterationen wären 3–7 Tage reine Bauzeit, und eine Funktionsprüfung (Fallen, Schieben, Sortieren) liefert SolidWorks
dabei gar nicht. **Für die Schleife taugt SolidWorks nur als letzter Schritt.**

### 1.4 Was schon im Repo dafür spricht

- **Die Spec ist schon Code.** `parameter` mit Ausdrücken (`"=YS+(ZW-ZU)*(YK-YS)/(ZO-ZU)"`) und Skizzenelemente
  (`polygon`, `rechteck`, `kreis`, `bogen`, `linie`). Die Feature-Typen sind überschaubar: extrusion/schnitt, rotation,
  bohrung, normbohrung, verrundung, fase, muster, spiegeln, referenz, verzahnung. Die Handler umfassen nur ≈ 800 Zeilen,
  dazu kommen Skizze, Anker und Topologie.
- **Die simulationsrelevanten Teile der Prüfstation** (Rutsche, Weichenkeil, Schieber, Prüfkanal, Klemmleiste,
  Fallschacht, Saphirglas, Zwischenplatte) bestehen nur aus Extrusionen und Schnitten von Skizzen, Bohrungen und zwei
  Verrundungen. Kollisionskörper lassen sich daraus exakt in konvexe Prismen zerlegen.
- **Skelett-Prinzip.** Alle Eigenteile der Prüfstation sind in Maschinenkoordinaten modelliert. Feste Teile liegen ohne
  Verschiebung, bewegt wird über `grenze_abstand` (Schieber 0 … 82, Keil 0 … 25). Die Lage im MuJoCo-Modell braucht
  deshalb keinen Verknüpfungslöser.
- Es gibt schon:
  - `swki validieren` (Fertigungs- und Plausibilitätsregeln ohne SolidWorks);
  - `swki/baugruppe/bewegung.py` (Bewegungsprüfung aus Transformationen);
  - `werkzeuge/messstand/vergleich.py` (STL gegen STL, lageunabhängig, p99/max/Volumen);
  - `layout.yaml` mit Ausdrücken und Kollisionsprüfung in Blender.

## 2 Recherche in Kürze

Details und Quellen stehen im Anhang. Für die Entscheidung zählt:

| Werkzeug | Rolle in der Schleife | Urteil |
|---|---|---|
| **MuJoCo 3.16/3.17** (MJCF, MjSpec) | Funktionsprüfung | **behalten.** CPU, deterministisch je Version, Windows-Wheels bis cp315. MjSpec baut Modelle aus Code und kompiliert in unter 1 s. 3.17 bringt `mujoco.batch`, viele Läufe bitgleich auf einem Thread-Pool. **Jedes Mesh kollidiert als konvexe Hülle** → konkave Teile zerlegen. Nach den Kollisions-Umbauten 3.12–3.17 ist eine neue Kalibrierung nötig. Weiche Kontakte, Rückprall nur über `solref`. GPU (MJX/Warp) bringt hier nichts: float32, nicht deterministisch, kleine Szenen. |
| **build123d 0.13 / OCP 8.0** (OpenCascade) | Schnellbau, exakte B-Rep | **geeignet.** Apache-2.0, Wheels für Windows und Python 3.14 (OCP 8.0.1.1.0, ≈ 50 MB). Export STEP, STL, glTF. Gelenke nur zur Positionierung, kein MJCF-Export. Mehrere Prozesse nötig (Threads bringen nichts). Version pinnen (Brüche zwischen Releases). |
| CadQuery 2.8 | dasselbe, älteres API | geeignet, Standard in den LLM-Benchmarks. Für einen *Compiler-Backend* spielt das keine Rolle. |
| FreeCAD 1.1 (Skript) | Schnellbau | schwer, kein pip-Paket, langsamer Start → nein |
| OpenSCAD / Manifold | Schnellbau | nur Mesh, keine Verrundung → nein |
| CodeToCad | – | seit 2024 kaum gepflegt → nein |
| Onshape-API | paralleles Cloud-CAD | API-Jahreskontingent (2500–10000 Aufrufe je Nutzer, danach HTTP 402) → für tausende Iterationen ungeeignet |
| Zoo KCL | Cloud-CAD | nur in der Zoo-Cloud, Abrechnung je Sekunde → nein |
| Blender 5.2 | Layout, Bilder | float32-Koordinaten, Mesh, CAD Sketcher experimentell → **nicht als Maßquelle**; weiter für Layout und Wiedergabe in der Maschinenumgebung |
| Optuna 5.0 | Abstimmung der Zahlen | **geeignet.** TPE 100–1000 Proben, GP bis 500, CMA-ES 1000+. `WilcoxonPruner` bricht Proben mit verrauschtem Monte-Carlo-Ziel früh ab. Mehrere Prozesse mit `JournalStorage`/`JournalFileBackend` (SQLite für parallele Läufe ausdrücklich nicht empfohlen). Nebenbedingungen über `trial.set_constraint()`. |
| Drake (hydroelastisch) | Alternative Physik | genauer bei nicht konvexen Kontakten, langsamer; nur als Gegenprobe bei Kantenstößen erwägen |

Aus der Literatur:

- **Alle Exporter gehen nur CAD → Simulation** (onshape-to-robot, SolidWorks-URDF-Exporter, obj2mjcf). Keiner führt
  zurück zu Features. STEP kommt in SolidWorks als toter Körper an; FeatureWorks erkennt zwar Features, aber
  interaktiv und ohne Namen.
- **Nächste veröffentlichte Arbeit zum Plan:** IIT, arXiv 2509.14935. SolidWorks baut dort einen Pool parametrischer
  Varianten, und Masseeigenschaften gehen automatisch nach URDF/MuJoCo. Gesamtlaufzeit 15–75 h.
- **LLM in der Schleife:** Am besten funktioniert eine Aufteilung, in der das LLM Struktur, Parametrierung und
  Prüfregeln schreibt und ein numerischer Optimierer mit eingefrorener Bewertung auswählt (Debate2Create: „LLMs never
  decide which candidate wins“). Ein LLM, das selbst Zahlen vorschlägt, erreichte nur 50–70 % der Sucheffizienz von
  Bayes-Optimierung.
- **Ausnutzen von Simulator-Artefakten ist der Hauptfehler** solcher Schleifen. Beispiele: schwebende Strukturen und
  Diskretisierungsfehler in einer PV-Studie 2026, dazu 26 Fälle in „AI Finds A Way“ 2026. Gegenmittel sind
  physikalische Prüfregeln, Robustheit über Szenarien und eine Prüfung der Besten mit höherer Genauigkeit.
- **LLM-Benchmarks für CAD-Code** (Text2CAD-Bench, BenchCAD 2026): Selbst die besten Modelle schreiben bei schwierigen
  Teilen 54–70 % nicht ausführbaren Code. Bei BenchCAD verändern 64 % der „gelungenen“ Code-Änderungen unbemerkt
  andere Features. Das spricht gegen freien CAD-Code als Quelle und für die strukturierte, validierte `swki`-Spec.

## 3 Gemeinsamer Rahmen aller Ansätze

### 3.1 Was der Mensch macht

Der Mensch schreibt nur den **Optimierungsauftrag**:

- Funktion und Zielwert (z. B. „≥ 99 % richtig in beiden Weichenstellungen bei 0,05 … 0,15 m/s“);
- Bauraum und Anschlussteile, Werkstoffe und Fertigungsart;
- die **Stellschrauben mit Bereichen**. Das sind nicht nur Maße, sondern auch Ablaufgrößen wie Schiebergeschwindigkeit
  oder Schaltzeitpunkte. Im Sortierschritt war die Steuerungsänderung G2 genauso nötig wie die Geometrie G1c, und die
  Literatur zeigt, dass reine Steuerungsoptimierung Co-Design oft einholt;
- die Szenarien (Reibwerte und Stoßzahlen je Paarung, Startverteilungen, Zeitstreuungen);
- Abbruchgrenzen (Zeit, Zahl der Proben).

Er gibt den Auftrag einmal frei und bekommt am Ende das Ergebnis mit Bericht und 3D-Wiedergabe. Dazwischen greift er
nicht ein.

**Offene Regel (Entscheidung des Nutzers nötig):**

- Heute darf `swki freigeben` nur nach ausdrücklichem OK laufen. Eine Ausnahme gilt nur für Messstand-Aufträge `MESS-*`.
- Eine autonome Schleife ändert aber `parameter`, und genau die schützt die Freigabe.
- Vorschlag: Die Freigabe des Optimierungsauftrags gibt den **Raum** frei, also Stellschrauben, Bereiche und
  Nebenbedingungen. Ein Ergebnis innerhalb dieses Raums darf ohne Rückfrage freigegeben und gebaut werden.
- Neue Topologien (Features hinzufügen oder entfernen) brauchen entweder ein OK oder müssen im Auftrag ausdrücklich
  erlaubt sein, z. B. „Wangen hinzufügen erlaubt“.

### 3.2 Zwei Ebenen

```
Mensch ── Optimierungsauftrag (Ziel, Bauraum, Stellschrauben, Szenarien) ── Freigabe des Raums
                         │
   ┌─────────────────────▼──────────────────────────────────────────────┐
   │ äußere Schleife (Claude): Topologie-Varianten der Spec               │
   │   Variante k = Spec + neue/entfernte Features, eigene Stellschrauben │
   │   ┌───────────────────────────────────────────────────────────┐   │
   │   │ innere Schleife (Optuna, ohne LLM):                       │   │
   │   │   Probe = Parameterwerte → Modell → N Läufe → Ziel        │   │
   │   │   Abbruch: Zielwert erreicht / Budget / Stillstand        │   │
   │   └───────────────────────────────────────────────────────────┘   │
   │   Claude liest Fehlerbilder der Besten (wo, warum), nächste Idee   │
   └─────────────────────┬──────────────────────────────────────────────┘
                         ▼
   Gewinner → Prüfstufen (§3.3) → swki-Spec mit Gewinnerwerten → SolidWorks → Prüfer → Bericht
```

Claude schlägt der inneren Schleife höchstens 5–20 Startpunkte vor (`enqueue_trial`), aber keine Zahlen je Probe. Die
Bewertung ist eingefroren: Claude darf sie während einer Studie nicht ändern. So erfindet es sich keinen Erfolg.

### 3.3 Prüfstufen gegen Simulator-Artefakte

| Stufe | Was | Wann |
|---|---|---|
| 0 | `swki validieren` (Fertigungsregeln, Mindestwand, Hinweise) und Bauraum-/Kollisionsprüfung je Stellung im Schnellmodell | jede Probe, vor der Simulation; ungültig → `set_constraint` verletzt |
| 1 | N Läufe (z. B. 200) mit festem Satz an Saaten, Energieprüfung je Lauf, `WilcoxonPruner` | jede Probe |
| 2 | Top-k (z. B. 5): 2000 Läufe, Zeitschritt halbiert, Kontakt-Zeitkonstante halbiert, Worst-Case-Szenarien (µ ± 30 %, rauer Keil) | nach jeder Studie |
| 3 | SolidWorks-Nachbau, `swki pruefen` (inkl. Bewegungsprüfung), Prüfer-Agent | einmal je Ergebnis |
| 4 | Gegenprobe: dieselbe Simulation auf der Geometrie aus der SolidWorks-STL | einmal je Ergebnis |
| 5 | Versuch am Muster (Ü11/Ü13): Reibwerte, Stoßzahlen, Drosselgeschwindigkeit | vor der Abnahme, Mensch |

Zusätzliche Regel aus der Sortierschritt-Studie: Fällt ein Ergebnis in Stufe 2 mit dem Zeitschritt um mehr als den
Vertrauensbereich auseinander (wie 26 … 43 %), zählt es als **nicht belastbar**, und der Optimierer muss einen Abstand
zur kritischen Kante suchen. Das geht als Nebenbedingung, z. B. „freier Landepunkt ≥ 5 mm von der Trennwand“.

## 4 Die drei Ansätze

### Ansatz A – Funktionsmodell direkt in MuJoCo (Parametermodell aus Primitiven)

**Idee.** Die heutigen `modell.py`-Skripte werden zum System. Je Mechanismus entsteht ein Python-Funktionsmodell
(MjSpec), das Geometrie aus Quadern, Prismen und Zylindern direkt aus Stellschrauben baut. Eine **Zuordnungstabelle**
verknüpft jede Stellschraube mit einem Spec-Parameter (`rutsche.yaml: Y_TRENN`). Nach dem Erfolg setzt Claude die Werte
in die Specs, SolidWorks baut nach.

```
Optimierungsauftrag ─► funktionsmodell_<mechanismus>.py (MjSpec, Primitiven) ◄── Optuna
                                   │ Gewinnerwerte
                       Zuordnungstabelle Stellschraube → Spec-Parameter
                                   ▼
                       swki-Specs (von Claude angepasst) ─► SolidWorks ─► Prüfung
                                   ▼
                       Abgleich: Maße aus Prüfbericht vs. Funktionsmodell (Liste kritischer Maße)
```

- **Stellschrauben:** frei wählbar, auch solche, die es in der Spec noch nicht gibt (z. B. Fangwandhöhe).
- **Konsistenz:**
  - Prüft eine Liste kritischer Maße (Abgabekante, Keil-OK, Spalte) gegen `pruefbericht.json`, so wie in
    `sortierschritt/BERICHT.md` von Hand.
  - Alles Übrige ist ungeprüft: Hier entstanden die Tubus-, Schieberhöhen- und Stufenfehler.
- **Zeit je Probe:** Modellbau einige ms; 200 Läufe × 0,5 s = 100 CPU-s → ≈ 7 s Wandzeit auf 16 Kernen, 400–500 Proben/h.
  Das ist der schnellste Ansatz.
- **Vorteile:**
  - sofort machbar, die Bausteine gibt es schon (Messerkontur, Stirnformen, Kalibrierung, Energieprüfung);
  - Primitiven kollidieren am günstigsten und am robustesten;
  - keine neuen CAD-Pakete.
- **Nachteile:**
  - doppelte Buchführung, zwei Wahrheiten;
  - jeder neue Mechanismus braucht ein neues Funktionsmodell von Hand;
  - Verrundungen, Fasen und Formen aus der Spec fehlen;
  - der Rückweg ist eine Übersetzung, also „1:1“ nur so gut wie die Zuordnungstabelle.
  - Für ganze Montageanlagen skaliert das nicht: Mit jedem Teil wächst die Handarbeit.
- **Aufwand:** 2–3 Tage (Runner, Prüfstufen, Zuordnungstabelle), danach je Mechanismus 0,5–1 Tag.
- **Risiko:** hoch bei der Konsistenz, niedrig bei der Technik.

### Ansatz B – Code-CAD als Zwischenmodell (build123d schreibt die Geometrie)

**Idee.** Claude schreibt die Teile als build123d-Code. Das Skript erzeugt B-Rep, daraus STL und Zerlegung in konvexe
Teile (2,5D exakt oder CoACD) und eine MJCF-Szene. Optuna verändert die Funktionsargumente. Nach dem Erfolg übersetzt
Claude den build123d-Code in `swki`-Specs; SolidWorks baut, und `vergleich.py` vergleicht die SolidWorks-STL mit der
build123d-STL.

```
Optimierungsauftrag ─► teile/*.py (build123d, von Claude) ─► STEP/STL ─► Zerlegung ─► MJCF ◄── Optuna
                                   │ Gewinner
                       Übersetzung build123d → swki-Spec (Claude, je Teil)
                                   ▼
                       SolidWorks ─► STL ─► vergleich.py gegen build123d-STL (p99, Volumen)
```

- **Stellschrauben:** Funktionsargumente der Teile.
- **Konsistenz:**
  - geometrisch gut prüfbar: B-Rep gegen B-Rep über STL, Schwellen aus dem Messstand (p99 ≤ 0,3 mm; für
    Funktionsflächen enger);
  - die Übersetzung selbst ist aber eine zweite Konstruktion, ein Fehler fällt erst nach dem SolidWorks-Bau auf.
- **Zeit je Probe:** Schnellbau der geänderten Teile 0,2–2 s je Teil (Schätzung; veröffentlichte Zahlen gibt es nicht),
  Zerlegung ms (2,5D) bis Sekunden (CoACD, zwischengespeichert), Simulation wie A → 8–12 s, 300–450 Proben/h.
  Dazu kommt die Übersetzung am Ende: 5–20 min Agentenzeit je Teil plus Nachbesserungsrunden.
- **Vorteile:**
  - beliebige Geometrie, auch Formen, die `swki` noch nicht kann;
  - echte B-Rep mit Verrundungen;
  - großes Werkzeug-Ökosystem, STEP für andere Werkzeuge.
- **Nachteile:**
  - Freier CAD-Code ist für LLMs fehleranfällig (Benchmarks oben); in der Schleife fallen Fehler zwar als
    Ausführungsfehler auf, stille Fehler aber nicht.
  - Zwei Formate: Regeln, die `swki validieren` schon kennt (Fertigungsgerecht, Bemaßungsbezug, Normbohrungen), fehlen
    in build123d.
  - Gelenke und Grenzen müssen ein drittes Mal beschrieben werden (MJCF).
  - Die Freigabe-Logik von `swki` gilt für das Zwischenmodell nicht.
- **Aufwand:** ≈ 1 Woche (build123d-Bausteine, MJCF-Generator, Runner), danach je Teil die Übersetzung.
- **Risiko:** mittel; der Rückweg bleibt eine Übersetzung, nur gut geprüft.

### Ansatz C – Eine Spec, zwei Backends (empfohlen)

**Idee.** Die `swki`-Spec (Teil und Baugruppe) ist die einzige Quelle. Neu kommen hinzu:

1. **Schnellbau-Backend** `swki/schnellbau/`: Es interpretiert dieselben Features wie der SolidWorks-Compiler mit
   build123d/OCP. Das sind dieselben Skizzen, Ausdrücke, Anker (`flaeche: {feature: f1, flaeche: "-z"}`), Bezüge,
   Ende-Typen und Muster. Ergebnis je Teil ist eine B-Rep, daraus STL und Masseeigenschaften. Normbohrungen werden als
   Kernloch oder glatt gebaut; Gewinde sind für die Simulation ohne Belang. Kaufteile kommen aus der STEP im
   Quellordner, nur gelesen, über OCP.
2. **MJCF-Generator** `swki/simulation/`: Er erzeugt aus der Baugruppen-Spec und dem neuen Block `simulation` die
   MuJoCo-Szene.
   - Lage: aus dem Skelett-Prinzip oder aus dem letzten SolidWorks-Lauf für unveränderte Teile.
   - Gelenke: `grenze_abstand` → Schubgelenk mit Bereich, `grenze_winkel`/`scharnier` → Drehgelenk.
   - Kopplungen: `zahnrad`/`zahnstange` → Gleichheitsbedingung.
   - Kollisionskörper: 2,5D-Teile exakt aus den Skizzen in konvexe Prismen zerlegt; sonst CoACD mit Cache und
     Volumenprüfung.
   - Werkstoffpaarungen → `friction`/`solref` über die vorhandene Kalibrierung.
   - Bekannte Fallen der Exporter fest im Generator gelöst:
     - `<compiler angle="radian"/>` setzen, weil MJCF ohne Angabe in Grad rechnet;
     - `<inertial>` aus den B-Rep-Masseeigenschaften schreiben statt aus dem Netz;
     - die Nulllage der Gelenke aus der Spec-Grundstellung nehmen, nicht aus der aktuellen Stellung;
     - eine unbekannte Verknüpfung ist ein Fehler und wird nicht still übergangen.
3. **Simulations- und Optimierungsblock** in der Spec (Schema-Erweiterung, Bauweg wie `bezug`: nicht in der
   Freigabe-Prüfsumme). Inhalt: Szenarien, Ablauf (Bewegungsprofile, Zeiten), Auswertung (Klassen „richtig“,
   „falsch“, „liegt“), Ziel, Stellschrauben als Verweise auf `parameter` mit Bereichen, Nebenbedingungen. Das
   Zielfunktions-Skript ist ein versionierter Baustein je Prüfaufgabe, z. B. `fallen`, `schieben`, `sortieren`.

```
                 Optimierungsauftrag (Mensch) = Spec-Rahmen + Block simulation/optimierung
                                        │
              ┌─────────────────────────┴──────────────────────────┐
              ▼                                                    ▼
   swki schnellbau (OCP/build123d)                      swki bauen (SolidWorks, wie heute)
   Teile → B-Rep → STL, Masse                                  ▲
              │                                                │ Gewinnerwerte in parameter
   swki simulation: Baugruppe → MJCF                           │ (dieselbe Spec, nichts übersetzt)
   (Lage, Gelenke, Kollision, Werkstoffe)                      │
              │                                                │
   Runner: N Läufe/Probe, Energieprüfung ◄── Optuna ───────────┘ (nach Prüfstufe 2)
              │
   Konsistenz:
     (a) dieselbe Spec → strukturell 1:1
     (b) Backend-Gleichheit: Referenz-Suite tests/referenz in beiden Backends, vergleich.py (p99, max, Volumen)
     (c) Lauf-Gleichheit: Schnellbau-STL gegen SolidWorks-STL des Gewinners (vergleich.py), Transformationen
         der Komponenten gegen pruefbericht.json
     (d) Funktions-Gleichheit: Gegenprobe-Simulation auf der SolidWorks-STL (Prüfstufe 4)
```

**Beispiel Stellschrauben** (Skizze, kein fertiges Schema), für die Weiche aus dem Sortierschritt:

```yaml
optimierung:
  ziel: {kennzahl: min_anteil_richtig, ueber: [stellung, schiebergeschwindigkeit], mindestens: 0.99}
  stellschrauben:               # nur Verweise auf parameter der Specs, Bereiche in mm/Grad
    - {spec: rutsche.yaml,     parameter: Y_TRENN, von: 179.5, bis: 195.5}
    - {spec: weichenkeil.yaml, parameter: YS,      von: 200,   bis: 220}
    - {spec: rutsche.yaml,     parameter: Z_FANG,  von: -202,  bis: -170}
  nebenbedingungen:
    - "freier_landepunkt_abstand_trennwand >= 5"   # Abstand zur kritischen Kante (Lehre aus 26 … 43 %)
    - kollisionsfrei_je_stellung                    # Weichenhub 0 … 25 gegen Durchlicht, Fangwand
  szenarien: {startlagen: v-schieber/D1, geschwindigkeit: [0.05, 0.10, 0.15], keil_mu: [0.25, 0.55]}
  budget: {proben: 300, laeufe_je_probe: 200, wandzeit_h: 2}
```

- **Zeit je Probe:**
  - Schnellbau nur der Teile, deren Parameter sich ändern: 0,2–2 s je Teil (Schätzung, im Spike messen).
  - 2,5D-Zerlegung im ms-Bereich, MjSpec-Kompilieren unter 1 s.
  - Die Simulation dominiert mit ≈ 100 CPU-s bei 200 Läufen. Der Mehraufwand gegenüber A liegt geschätzt bei < 5 %,
    also 7–10 s Wandzeit und 400–500 Proben/h.
  - Der SolidWorks-Nachbau des Gewinners ist ein normaler `swki durchlauf` mit 4–10 min.
- **Vorteile:**
  - **Keine Übersetzung, kein Abschreiben.** Die Fehlerklasse aus §1.2 Punkt 1 verschwindet, weil Simulation und
    SolidWorks dieselben Zahlen lesen.
  - Optuna verändert genau die Größen, die der Konstrukteur kennt und die SolidWorks als Maße bekommt.
  - `swki validieren`, Fertigungsregeln, Normbohrungen, Kaufteile und Bewegungsgrenzen gelten unverändert. Die Schleife
    kann keine Teile erzeugen, die `swki` nicht bauen kann.
  - Topologie-Varianten (äußere Schleife) sind Spec-Änderungen. Diese Arbeit kann Claude schon; validiert wird sie in
    Sekunden.
  - Skaliert auf Montageanlagen: Jedes neue Teil ist eine normale Spec, nur neue Prüfaufgaben brauchen einen neuen
    Zielfunktions-Baustein.
  - Nebennutzen: Mit dem Schnellbau kann `swki` Specs schon vor dem SolidWorks-Bau als STL zeigen, für die
    3D-Wiedergabe und Vorab-Kollisionsprüfungen. Das spart SolidWorks-Runden im normalen Konstruieren.
- **Nachteile:**
  - Ein zweiter Interpreter muss dieselbe Semantik treffen. Besonders heikel sind Flächenwahl über Richtung (`-z`),
    Kantenauswahl bei `verrundung` (`senkrechte_kanten`), `bis_flaeche` und `bezug`.
  - Geometrie, die die Spec nicht kann, kann auch die Schleife nicht. Der Notausgang `typ: skript` hat im Schnellbau
    kein Gegenstück: Solche Teile sind dort nur Ersatzkörper oder gesperrt.
  - Baugruppen ohne Skelett-Prinzip brauchen einen kleinen Lagelöser oder die Transformationen des letzten
    SolidWorks-Laufs.
- **Aufwand (Schätzung, Agententage):**
  - Schnellbau für extrusion/schnitt/rotation/bohrung/normbohrung (glatt)/verrundung/fase/muster/spiegeln/referenz: 3–4;
  - MJCF-Generator mit Gelenken, Zerlegung und Werkstoffen: 2;
  - Schema `simulation`/`optimierung` und Runner mit Optuna und Prüfstufen: 2;
  - Backend-Gleichheit über die Referenz-Suite: 1.

  Zusammen ≈ 2 Wochen, in Stufen nutzbar (§6).
- **Risiko:** mittel bei der Technik, das Risiko liegt in der Semantik des zweiten Backends und ist über die
  Referenz-Suite messbar. Niedrig bei der Konsistenz.

## 5 Vergleich und Empfehlung

| Kriterium | A Funktionsmodell MuJoCo | B Code-CAD build123d | **C Eine Spec, zwei Backends** |
|---|---|---|---|
| Zeit je Optuna-Probe (200 Läufe, 16 Kerne) | ≈ 7 s | ≈ 8–12 s | ≈ 7–10 s |
| Proben je Nacht (10 h) | ≈ 5000 | ≈ 3000–4500 | ≈ 4000–5000 |
| Weg nach SolidWorks | Werte übertragen (Tabelle) | Code übersetzen | **keiner nötig** (dieselbe Spec) |
| 1:1-Nachweis | kritische Maße gegen Prüfbericht | STL-Vergleich nach dem Bau | STL-Vergleich + Lagevergleich + Gegenprobe; Abweichung nur durch Backend-Unterschied, über Referenz-Suite überwacht |
| Fehlerklasse „von Hand abgeschrieben“ | bleibt | verschoben in die Übersetzung | entfällt |
| Maßtreue Kollisionsgeometrie | Primitiven, Ersatzformen | B-Rep → Zerlegung | B-Rep → exakte 2,5D-Zerlegung |
| Neue Mechanismen | neues Funktionsmodell von Hand | neuer Code | normale Spec + Zielfunktions-Baustein |
| Topologie-Varianten durch Claude | Python-Code | Python-Code | Spec-Änderung, validiert |
| Fertigungsregeln, Normteile, Kaufteile | fehlen | fehlen | gelten |
| Skalierung auf Montageanlagen | schlecht | mittel | gut |
| Aufbauaufwand | 2–3 Tage | ≈ 1 Woche | ≈ 2 Wochen (stufenweise) |
| Neue Pakete | mujoco, optuna | + build123d/OCP | + build123d/OCP |
| Hauptrisiko | Inkonsistenz | Übersetzung | Semantik des zweiten Backends |

**Empfehlung: Ansatz C, stufenweise aufgebaut, mit A als optionaler Grobstufe.**

Begründung:

1. Das Ziel des Nutzers ist ein **1:1-Nachbau ohne Menschen dazwischen**. Das ist der Punkt, an dem die bisherigen
   Studien am meisten Zeit und Vertrauen gekostet haben, also die Abschreibfehler und die Nutzer-Freigabe jeder
   Geometrie. Nur C beseitigt diese Fehlerklasse grundsätzlich; A und B verlagern sie.
2. **Das Tempo ist bei allen drei Ansätzen dasselbe**, weil die Simulation die Zeit bestimmt und nicht der Geometriebau.
   Der Mehraufwand von C gegenüber A ist ein einmaliger Entwicklungsaufwand und kostet keine Laufzeit.
3. C nutzt, was `swki` schon kann: das Format, das Claude zuverlässig schreibt, `validieren`, die Freigabe-Logik, die
   Bewegungsgrenzen und die Referenz-Suite als Prüfstein für das zweite Backend. B müsste das alles neu erfinden.
4. Für ganze Montageanlagen braucht es ein Format, das mit der Zahl der Teile wächst, ohne dass die Handarbeit wächst.
   Das ist die Spec.

A bleibt als **Grobstufe** sinnvoll, wenn eine Idee noch keine Spec hat, etwa „Bringt eine Prallkaskade überhaupt
etwas?“. Dann darf Claude mit Primitiven vorsondieren. Das Ergebnis zählt aber erst, wenn es als Spec-Variante in C
bestätigt ist.

## 6 Stufenplan für C

| Stufe | Inhalt | Nutzen danach |
|---|---|---|
| C1 | Schnellbau für extrusion/schnitt/bohrung (glatt)/referenz; MJCF-Generator nur für fest + `grenze_abstand`; exakte 2,5D-Zerlegung | Prüfstations-Weiche aus der Spec simulierbar (Spike, §7) |
| C2 | Runner + Optuna (JournalStorage, Mehrprozess, WilcoxonPruner, Prüfstufen 0–2), Block `optimierung` im Schema | autonome innere Schleife |
| C3 | verrundung, fase, muster, spiegeln, rotation, normbohrung, Kaufteil-STEP; Backend-Gleichheit über `tests/referenz` | alle Teile der Prüfstation |
| C4 | Prüfstufen 3–4 automatisch (`swki durchlauf` des Gewinners, STL-Export, Gegenprobe), Bericht mit 3D-Wiedergabe aus dem Schnellbau | Schleife bis SolidWorks ohne Menschen |
| C5 | äußere Schleife (Topologie-Varianten mit erlaubten Feature-Änderungen), Kalibrierung aus Versuchen (Ü13) übernehmen | Montageanlagen-Maßstab |

Kalibrierung: Mit MuJoCo-Version 3.16 die bisherigen Ergebnisse nachrechnen, bevor die Version wechselt. Erst danach auf
3.17 gehen (wegen `mujoco.batch`), und das nur mit neuer `kalib.py`-Abbildung und einem Nachrechnen einer
Referenzstudie, etwa Fallschacht trocken. Determinismus gilt nur je Version und Architektur, deshalb die Version im
Ergebnis festhalten.

## 7 Erster Spike: S-Schleife-1 „Weiche G1c aus der Spec“

### 7.1 Ziel

Belegen oder widerlegen, dass (1) die Prüfstations-Weiche aus den freigegebenen Specs ohne Abschreiben als
MuJoCo-Modell entsteht, (2) dieses Modell die Handmodell-Ergebnisse des Sortierschritts reproduziert und (3) eine
Optuna-Studie darauf in der erwarteten Zeit läuft und die bekannte Lösungsrichtung findet. Keine Änderung an Specs,
Freigaben oder SolidWorks-Läufen.

### 7.2 Umfang

- **Teile:** `rutsche`, `weichenkeil`, `zwischenplatte`, `pruefkanal` (vorderer Teil), `klemmleiste`, `schieber`.
  Durchlicht als Hindernis-Quader aus dem Ersatzkörper.
- **Schnellbau:** Wegwerf-Code im Spike-Ordner (`spikes/s_schleife1_*.py`), nur die Features dieser Specs:
  extrusion/schnitt mit polygon/rechteck/kreis/linie/bogen, Bohrungen glatt, zwei Verrundungen am Schieber. Danach
  STL und exakte konvexe Prismen.
- **MJCF:** Teile in Maschinenkoordinaten, Schieber 0 … 82 und Keil 0 … 25 als kinematisch geführte Schubgelenke,
  Werkstoffe und Ablauf aus `sortierschritt/skripte/` übernommen. Die Messer-Startlagen D1 werden nur gelesen.

### 7.3 Messen

| Nr. | Messgröße | Bestanden, wenn |
|---|---|---|
| M1 | Schnellbau-Zeit je Teil und für alle sechs, kalt/warm | ≤ 2 s je Teil warm (sonst Ansatz neu bewerten) |
| M2 | Geometrie Schnellbau gegen Handmodell: alle Werte der Tabelle „Nachgemessene Spalte und Kanten“ (`sortierschritt/BERICHT.md`) | Abweichung ≤ 0,01 mm |
| M3 | Geometrie Schnellbau gegen SolidWorks lauf-28: `vergleich.py` je Teil (STL aus SolidWorks, einmaliger Export, erst wenn SolidWorks frei ist und keine andere Sitzung misst) | p99 ≤ 0,05 mm, max ≤ 0,1 mm, Volumen ≤ 0,1 % |
| M4 | Funktion: G1c i.O./n.i.O. bei 0,05/0,10/0,15 m/s mit D1 (1992 Läufe), dazu der Ist-Stand v5 (aus der freigegebenen Fassung vor G1c, falls vorhanden; sonst nur G1c) | G1c: ≥ 99,5 % wie Handmodell; Ist: Median des freien Landepunkts Y 195,0 ± 0,2 mm |
| M5 | Optuna-Studie vom Ist-Stand v5 aus, 2–3 Stellschrauben (Trennwandlage, Keilfuß, Fangwandhöhe), 200 Läufe je Probe, 100–150 Proben, 12 Prozesse | Proben je Stunde gemessen; die Studie findet eine Lösung ≥ 99 % in beiden Stellungen (wie G1b/G1c) oder zeigt, warum nicht |
| M6 | Prüfstufe 2 auf den Top-3: Zeitschritt halbiert | Ergebnis innerhalb des 95-%-Bereichs |

Ergebnis in `docs/entscheidungen/` bzw. `spikes/`. Mit den Zahlen aus M1, M5 und M6 wird die Schätzung in §5 bestätigt
oder korrigiert. Erst danach beginnt Stufe C1 als richtiger Code (Test zuerst, Skill `compiler-erweitern` sinngemäß).
Dauer: etwa 1–2 Agententage. M3 braucht einmal SolidWorks für den STL-Export und wird deshalb ans Ende gelegt.

### 7.4 Was der Nutzer freigeben muss

1. **Pakete in einer eigenen venv** (`.venv-sim`, damit die `swki`-venv unverändert bleibt). Alle Pakete kommen von
   PyPI, und für alle gibt es Wheels für Windows und Python 3.14:

   | Paket | Version | Größe (Wheel) |
   |---|---|---|
   | `mujoco` | 3.16.0 (wie die bisherigen Studien) | ≈ 5–10 MB (vor dem Download prüfen) |
   | `optuna` | 5.0.0 | < 1 MB, dazu sqlalchemy, alembic, colorlog, tqdm, PyYAML ≈ 5 MB |
   | `build123d` | 0.13.0 | 0,4 MB, zieht `cadquery-ocp-novtk` 8.0.1.1.0 (≈ 50 MB) und u. a. scikit-learn, sympy, ezdxf, ipython (zusammen geschätzt 100–150 MB) |
   | `coacd` | 1.0.14 (nur falls nicht-prismatische Teile vorkommen) | 1,5 MB |

   Alternative mit weniger Abhängigkeiten: `cadquery-ocp-novtk` allein (OCP direkt, ohne build123d). Das bedeutet mehr
   eigenen Code im Backend, dafür kein scikit-learn und kein ipython.
2. Die **Regel für Freigaben** in autonomen Schleifen (§3.1). Sie ist für den Spike nicht nötig, weil der Spike nichts
   freigibt, aber für Stufe C2.
3. Einmal **SolidWorks-Zeit** für den STL-Export von lauf-28 (M3), abgestimmt mit den BTP-Sitzungen.

## 8 Offene Punkte und Grenzen dieser Recherche

- **Schnellbau-Zeiten sind Schätzungen.** Für keines der Code-CAD-Werkzeuge gibt es veröffentlichte Zeiten je
  Neuaufbau; sie werden im Spike gemessen (M1).
- **Mehrprozess-Betrieb von OCP unter Windows** (Start je Prozess, Speicher) ist nicht belegt. Es wird erwartet, dass
  ein Prozess je Kern mit warmem Kern reicht; ob das stimmt, zeigt M5.
- **Optuna-Journal unter Windows:** Die Sperre `JournalFileOpenLock` gilt als sicherer als die Symlink-Sperre. Das ist
  abgeleitet, nicht dokumentiert, und wird im Spike geprüft.
- **Die Physik bleibt der Engpass der Aussagekraft.** Der Spike belegt keine Genauigkeit gegenüber der Wirklichkeit:
  Reibwerte und Stoßzahlen bleiben Schätzwerte bis zu Ü11/Ü13. Eine Schleife, die auf geschätzten Werten bis 99,9 %
  optimiert, muss über Worst-Case-Szenarien robust sein, nicht über den Nennfall.
- Nicht geprüft: Drake, Chrono und Genesis im Detail, Fusion-360-Exporter, Phobos, KCL-Simulation.
- Der Zielfunktions-Baustein je Prüfaufgabe (fallen, schieben, sortieren) wird aus den bisherigen `sim.py`
  übernommen. Er ist Fachwissen und bleibt in der Hand von Claude mit Bericht an den Nutzer. Ein Sprachmodell darf
  ihn während einer Studie nicht ändern.
