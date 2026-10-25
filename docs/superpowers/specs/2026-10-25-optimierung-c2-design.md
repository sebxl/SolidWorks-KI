# Stufe C2: innere Optimierungsschleife (`swki optimiere`, Block `optimierung`)

Stand 25.10.2026. Grundlage: Entscheidung [2026-10-25-schnelle-konstruktionsschleife.md](../../entscheidungen/2026-10-25-schnelle-konstruktionsschleife.md)
(§3 Rahmen, §3.2 zwei Ebenen, §3.3 Prüfstufen, §6 C2), Spike S-Schleife-1 (`spikes/s18_optuna.py`, Lehren M5), Stufe C1
(`swki.schnellbau`). Ausbaustufe 1: Claude in einer Sitzung startet die Schleife und greift nur an ihrem Ende ein.
Freigaberegel vom Nutzer am 25.10.2026 bestätigt („Das passt so“), §6.

## 1 Ziel

Die innere Schleife läuft als Python-Prozess **ohne Claude**: Optuna stimmt die Stellschrauben einer Spec ab, jede
Probe wird aus derselben Spec schnell gebaut (C1), in MuJoCo mit festen Saaten geprüft und bewertet. Sie endet mit genau
einem Grund – `ZIEL`, `PLATEAU`, `BUDGET` oder `FEHLER` – und schreibt `status.json` und `plateau.md` (≈ 1–2 k Tokens).
Claude liest nur diese Dateien.

Nicht in C2: Prüfstufen 3–4 automatisch (C4: Claude stößt den SolidWorks-Nachbau an), äußere Schleife ohne Claude (C5),
Ausbaustufe 2 (Runner ruft `claude -p`, nur skizziert §8).

## 2 Block `optimierung` (Teil- und Baugruppen-Spec, `schema/*.schema.json` `$defs.optimierung`)

```yaml
optimierung:
  variante: "G1: Trennwand vorn, ohne Fangwand und Keilwangen"   # Name der Form (Liste versuchter Varianten)
  pruefaufgabe: {modul: aufgabe_sortierschritt.py, simulation: weiche.sim.yaml}  # relativ zum Auftragsordner
  ziel: {kennzahl: min_anteil_richtig, richtung: max, zielwert: 0.99}
  stellschrauben:                       # Geometrie: Verweis auf einen Zahlen-Parameter; Ablauf: an jeden Lauf
    - {name: T,  spec: rutsche.yaml,     parameter: T,  rahmen: [176, 196], bereich: [180, 196]}
    - {name: YS, spec: weichenkeil.yaml, parameter: YS, rahmen: [190, 225], schritt: 0.1}
    - {name: v_keil, ablauf: v_keil, rahmen: [0.15, 0.5]}
  nebenbedingungen:
    kollision: {toleranz_mm3: 0.01, ausnehmen: [[schieber, pruefkanal]]}   # je Gelenk-Endstellung
    bauraum: {min: [-300, 100, -400], max: [0, 400, 0]}                    # Baugruppenkoordinaten, alle Stellungen
    kennzahlen: ["abstand_trennwand_mm >= 5"]                               # aus der Prüfaufgabe
  szenarien:
    - {name: nio_v0.10, laeufe: 64, werte: {stellung: nio, v: 0.10}}
    - {name: io_v0.05_rau, laeufe: 64, werte: {stellung: io_fest, v: 0.05, mu_keil: 0.55, e_keil: 0.55},
       streuung: {t_reaktion: [0.010, 0.040]}}                               # je Lauf gleichverteilt, feste Saat
  nachlauf: {laeufe: 192}               # Proben ab Zielwert bis zu so vielen Läufen je Szenario (Lehre M5: Sättigung)
  pruefstufe2: {top_k: 3, laeufe: 384, zeitschritt_faktor: 0.5, kontakt_faktor: 0.5,
                szenarien: [{name: io_v0.05_mu+30, laeufe: 192, werte: {...}}]}
  budget: {proben: 300, minuten: 120}
  plateau: {proben: 20, minuten: 30, epsilon: 0.005}
  automatik: {bereich_erweitern: true, sampler: [tpe, qmc, tpe_multivariat], mehrfachstart: 3}
  start: [{T: 193.5, YS: 218.5}]        # höchstens 20 Startpunkte (enqueue_trial), keine Zahlen je Probe
  erlaubte_formaenderungen: ["Fangwand mit Wangen an der Rutsche", "Wangen am Keil"]   # leer = keine
```

`validieren` prüft zusätzlich: Stellschrauben verweisen auf vorhandene Specs/Parameter mit einer Zahl (kein Ausdruck),
`bereich` ⊆ `rahmen`, Startwert und Startpunkte im Rahmen, Namen eindeutig, Modul und Simulations-Datei vorhanden,
Szenario-Namen eindeutig, `ziel.kennzahl` vorhanden.

**Raum** (Teil der Freigabe, §6): `pruefaufgabe` (mit SHA-256 von Modul und Simulations-Datei), `ziel`, `stellschrauben`
ohne `bereich`, `nebenbedingungen`, `szenarien`, `nachlauf`, `pruefstufe2`, `erlaubte_formaenderungen`.
**Bauweg der Schleife** (frei änderbar): `variante`, `bereich`, `budget`, `plateau`, `automatik`, `start`.

## 3 Prüfaufgabe (Zielfunktions-Baustein)

Ein versioniertes Python-Modul im Auftragsordner (Fachwissen, Claude schreibt es mit Bericht an den Nutzer; während
einer Studie eingefroren, §5). Schnittstelle:

```python
def jobs(szenario: dict, n: int, saat: int, erster: int = 0) -> list[dict]   # Läufe erster … erster+n−1, JSON
def lauf(probe: dict, job: dict) -> dict      # im Arbeitsprozess: {"ergebnis": "richtig"|…, "fehlerbild": str|None,
                                              #  "gueltig": bool (Energieprüfung), weitere Felder}
def kennzahlen(laeufe: dict[str, list[dict]]) -> dict   # optional: eigene Kennzahlen je Probe
```

`probe` (eine JSON-Datei je Probe, je Arbeitsprozess einmal geladen): `stuecke` {Komponente: [[x, y, z] …] je konvexem
Stück, Baugruppenkoordinaten mm}, `koerper` {Komponente: Gelenkkörper | "welt"}, `gelenke`, `parameter` {Spec-Datei:
{NAME: Zahl}} (ausgewertet), `werte` (Stellschrauben), `genauigkeit` {zeitschritt_faktor, kontakt_faktor},
`simulation` (Inhalt der Simulations-Datei). Ablauf-Stellschrauben stehen im Job.

Allgemeine Kennzahlen des Runners (nur gültige Läufe): `anteil_richtig:<szenario>`, `min_anteil_richtig`,
`mittel_anteil_richtig`, `anteil_ungueltig`. Fehlerbilder: Anteile je `fehlerbild` aller gültigen Läufe der Probe.

## 4 Ablauf `swki optimiere <spec>`

Lauf-Ordner `<arbeitsordner>/<auftrag>/optimierung-<n>/`: `studie.journal` (Optuna `JournalFileBackend` mit
`JournalFileOpenLock`), `bewertung.json`, `proben.jsonl`, `status.json`, `plateau.md`, `cache/` (Zerlegung je Teil und
Parameterstand), `proben/` (Probe-Dateien, nach der Probe gelöscht außer Top-k).

Je Probe (Optuna ask/tell, ein Prozess-Pool mit `kerne` Arbeitern für die Läufe):
1. **Prüfstufe 0**: Werte in die Specs (im Speicher), `validieren` der geänderten Specs (Schema + Plausibilität),
   Schnellbau der Baugruppe, Kollision je Gelenk-Endstellung (Körper samt Kindern verschoben bzw. gedreht, Schnittvolumen
   gegen alle anderen Körper, `ausnehmen`), Bauraum. Verletzt → `set_constraint` > 0, Wert = schlechtester, keine
   Simulation (0,5 s).
2. **Prüfstufe 1**: Läufe aller Szenarien verschränkt in Paketen zu 2 · `kerne`; nach jedem Paket meldet der Runner je
   Lauf 1/0 (richtig) an Schritt = Laufindex, `WilcoxonPruner` bricht schlechte Proben ab. Läufe mit `gueltig: false`
   (Energieprüfung) zählen nicht; über 15 % ungültig → Nebenbedingung `energie` verletzt. Erreicht die Probe den
   Zielwert, rechnet sie bis `nachlauf.laeufe` je Szenario nach.
3. Kennzahl-Nebenbedingungen (`a >= b`) → `set_constraint`.

Ende (genau ein Grund):
- `ZIEL`: eine Probe erreicht den Zielwert und besteht Prüfstufe 2 (unten). Besteht sie nicht, wird sie als „nicht
  belastbar“ geführt und die Studie läuft weiter.
- `PLATEAU`: `plateau.proben` Proben bzw. `plateau.minuten` ohne Verbesserung ≥ `epsilon`, nachdem die Automatik
  erschöpft ist: (a) **Bereich erweitern** bei Grenzanschlag des Besten (≤ 2 % der Spanne an einer Bereichsgrenze) um die
  halbe Spanne, nur innerhalb `rahmen`; (b) **Samplerwechsel** nach `automatik.sampler`; jede neue Phase ist eine neue
  Optuna-Studie im selben Journal, die alle bisherigen Proben übernimmt (`add_trial`, ohne Neurechnen) und als
  **Mehrfachstart** die besten `mehrfachstart` Proben leicht versetzt neu ansetzt.
- `BUDGET`: `budget.proben` oder `budget.minuten` erreicht.
- `FEHLER`: Bewertung geändert, Prüfaufgabe wirft, Startprobe nicht baubar, Abbruch.

**Prüfstufe 2** (Top-k bei PLATEAU/BUDGET, der Kandidat bei Zielwert): alle Szenarien mit `pruefstufe2.laeufe`
und verkleinertem Zeitschritt/Kontakt-Zeitkonstante, dazu die Worst-Case-Szenarien. Bestanden, wenn die Kennzahl den
Zielwert hält und jeder Szenario-Anteil im 95-%-Wilson-Bereich der Prüfstufe 1 liegt (sonst „nicht belastbar“, §3.3).

## 5 Bewertung eingefroren

`bewertung.json` hält die SHA-256 von Raum, Prüfaufgabe, Simulations-Datei und Runner-Code. Vor jeder Probe und in jeder
Phase wird neu gerechnet; eine Abweichung beendet die Studie mit `FEHLER` (`BEWERTUNG_GEAENDERT`). `--fortsetzen <n>`
setzt einen abgebrochenen Lauf nur mit gleicher Bewertung fort.

## 6 Freigaberegel für autonome Schleifen (Nutzer 25.10.2026)

- Die Freigabe des Optimierungsauftrags gibt den **Raum** frei. `swki freigeben` speichert dazu je Spec eine
  **Raum-Prüfsumme**: die Prüfsumme der Anforderungen mit maskierten Werten der Stellschrauben-Parameter, plus Raum
  (§2). Die gewöhnliche Prüfsumme deckt den Raum mit ab (Raum ändern = neu freigeben).
- Ein Ergebnis innerhalb des Raums gilt als freigegeben: `swki freigeben --im-raum <spec>` (ohne Rückfrage) prüft
  (1) Raum-Prüfsummen unverändert, (2) jede Stellschraube im `rahmen` (und auf dem `schritt`), (3) `validieren`, und
  schreibt dann neue Freigabe-Kopien und Prüfsummen mit Nachweis (`im_raum`: Werte vorher/nachher, Optimierungslauf).
  `swki optimiere uebernehmen <spec> [--lauf n] [--probe k]` schreibt die Gewinnerwerte in die Specs (Kommentare
  bleiben) und ruft dasselbe. `swki bauen` meldet bei `FREIGABE_VERALTET`, ob die Änderung im Raum liegt.
- Formänderungen (Features hinzufügen/entfernen) sind Bauweg; erlaubt nur, wenn `erlaubte_formaenderungen` sie nennt,
  sonst Rückfrage (Regel für Claude im Skill `optimieren`; der Runner listet Formänderungen gegenüber der Freigabe-Kopie
  in `status.json`). Neue Parameter ändern die Prüfsumme und brauchen immer eine neue Freigabe.
- Der Prüfer bleibt am Ende Pflicht, der Bericht geht an den Nutzer.

## 7 Ausgabe für Claude

`status.json` (vollständig, maschinenlesbar) und `plateau.md` (kompakt): Grund mit Erklärung, Verlauf des Besten,
Top 5 mit Parametern und Kennzahlen, Fehlerbilder des Besten (Anteile), Parameter-Wichtigkeit (fANOVA), Grenzanschläge
(am Rahmen, nicht mehr erweiterbar), Phasen der Automatik, Formänderungen gegenüber der Freigabe, bereits versuchte
Varianten des Auftrags (alle `optimierung-*` mit Variante, Grund, bestem Wert), erlaubte Formänderungen, nächster Schritt.

## 8 Ausbaustufe 2 (nur Skizze)

Der Runner ruft bei `PLATEAU` selbst `claude -p` mit `plateau.md`, der Spec und dem Skill `optimieren` als Kontext auf,
mit eingeschränkten Werkzeugen (Lesen, Edit der Specs des Auftrags, `swki validieren`, `swki optimiere`), höchstens
N Eingriffe und einem Token-Budget je Eingriff; das Ergebnis jedes Eingriffs ist eine Spec-Änderung mit `variante`, die
Freigaberegel §6 gilt unverändert. Erst nach Erfahrung mit Ausbaustufe 1 (Tokens je Eingriff, Qualität der Ideen).

## 9 Prüfung

TDD ohne SolidWorks (`tests/optimierung/`): Schema und `validieren` des Blocks; Raum-Prüfsumme und `--im-raum`; Plateau-
und Grenzanschlag-Logik als reine Funktionen; Runner an einer kleinen Baugruppe mit einer Test-Prüfaufgabe (Ziel,
Plateau, Budget, Fehler, eingefrorene Bewertung, Fortsetzen); `uebernehmen`. Abnahme live an der Weiche G1c (eigener
Auftrag `C2-WEICHE`): ein `PLATEAU`-Ende mit `plateau.md`, ein Claude-Eingriff (erlaubte Formänderung), ein `ZIEL`-Ende;
gemessen Proben/Stunde und Tokens je Eingriff (`docs/entscheidungen/2026-10-25-c2-abnahme.md`).
