---
name: optimieren
description: Optimiert eine Teil- oder Baugruppen-Spec autonom ohne SolidWorks (Schnellbau + MuJoCo + Optuna, swki optimiere) – Optimierungsauftrag (Block optimierung, Prüfaufgabe) schreiben, Raum freigeben lassen, Schleife im Hintergrund starten, am Ende (ZIEL, PLATEAU, BUDGET, FEHLER) eingreifen, Gewinner übernehmen und dem Nutzer zur Freigabe vorlegen. Verwenden, wenn der Nutzer eine Funktion (Fallen, Schieben, Sortieren) per Simulation optimieren oder Stellschrauben abstimmen lassen will, oder wenn ein swki-optimiere-Lauf endet.
---

# Optimieren (Stufe C2, Ausbaustufe 1: Claude in einer Sitzung)

Spec: `docs/superpowers/specs/2026-10-25-optimierung-c2-design.md` (Block §2, Prüfaufgabe §3, Ablauf §4, Freigaberegel §6).
Die innere Schleife läuft **ohne Claude**; Claude schreibt den Auftrag, startet und greift nur am Ende ein. Die Bewertung
ist **eingefroren**: Prüfaufgabe, Simulations-Datei, Ziel und Szenarien während eines Laufs nie ändern; Optuna wählt die
Zahlen, Claude nur Startpunkte (`start`, ≤ 20) und Formen.

## 1. Auftrag
- Spec wie gewohnt (Skill `konstruieren` bzw. `baugruppe`), dazu der Block `optimierung` (Syntax: Spec §2).
  Stellschrauben verweisen auf Zahlen-Parameter; abhängige Maße schreibt man als Ausdruck der Stellschraube in die
  Features. `rahmen` = Grenzen des Auftrags (vom Nutzer), `bereich` = Startbereich der Suche. Parameter für erlaubte
  Formen gleich mit anlegen, sonst braucht ihre Stellschraube später eine neue Freigabe.
- Prüfaufgabe als Python-Modul im Auftragsordner (`jobs`, `lauf`, optional `kennzahlen`, `MJCF = True`); jede weitere
  Datei der Bewertung (Hilfsmodul, Daten) unter `pruefaufgabe.abhaengigkeiten` nennen. Fehlschläge als `fehlerbild` klassifizieren (wo, warum: „Abprall am Keil“, „Treffer auf die
  Trennwandkante“) – davon lebt der Eingriff bei PLATEAU. Werte aus der Probe lesen (`parameter`, `stuecke`), nie aus
  der Spec abschreiben.
- `swki validieren <spec>` → Nutzer den Raum zeigen (Stellschrauben mit Rahmen, Ziel, Szenarien, erlaubte
  Formänderungen) → nach ausdrücklichem OK `swki freigeben <spec>`.

## 2. Starten
- `.venv\Scripts\python.exe -m swki optimiere <spec>` mit `run_in_background` starten und auf die Benachrichtigung warten
  (keine Polling-Schleife, kein `sleep`; der Lauf schreibt `<lauf>/fortschritt.log`). Läuft schon ein Lauf auf allen
  Kernen, keinen zweiten starten. Abgebrochen: `--fortsetzen <n>`. Anhalten: Datei `stop` in den Lauf-Ordner legen.
- Das Ende-JSON nennt `grund`, `plateau_md`, `status_json`. Gelesen wird **nur `plateau.md`** (≈ 1–2 k Tokens);
  `status.json` nur für ein einzelnes Feld, `proben.jsonl` nie ganz.

## 3. Am Ende – genau ein Zweig
- **ZIEL**: `swki optimiere <spec> --uebernehmen` schreibt die Gewinnerwerte und legt `<lauf>/freigabe_vorlage.md` an.
  **Hier endet die Arbeit ohne Rückfrage:** dem Nutzer die Vorlage zeigen (Lauf, Gewinner, Prüfstufe 2, Formänderungen,
  Ablaufgrößen für die Steuerung) und auf sein ausdrückliches OK warten. Erst danach, wenn SolidWorks frei ist (nie zwei
  SolidWorks-Arbeiten gleichzeitig): `swki freigeben <spec> --im-raum --quelle <quelle>` → `swki durchlauf <spec>
  --neustart` → Prüfer → `swki bericht`.
- **PLATEAU**: aus `plateau.md` (Fehlerbilder, Wichtigkeit, Grenzanschläge, bereits versuchte Varianten) **eine** Maßnahme:
  1. eine Formvariante, nur aus `erlaubte_formaenderungen`, als Spec-Änderung mit neuer `variante`; nicht erlaubte
     Formen → Nutzer fragen;
  2. oder `bereich` im `rahmen` ändern (Grenzanschlag am Rahmen → Nutzer fragen, ob der Rahmen wachsen darf);
  3. oder abbrechen/annehmen und dem Nutzer berichten.
  Dann `swki validieren` und neu starten (§2). Eine Variante, die schon unter „Bereits versucht“ steht, nicht wiederholen.
- **BUDGET**: Ergebnis mit Prüfstufe 2 berichten; mehr Budget nur auf Wunsch des Nutzers.
- **FEHLER**: `detail` lesen, Ursache beheben (Prüfaufgabe, Spec), neuen Lauf starten; `BEWERTUNG_GEAENDERT` heißt:
  während des Laufs wurde Bewertung oder Code geändert → neuer Lauf.

## 4. Freigaberegel (Nutzer 25.10. und 30.10.2026)
- Die Freigabe des Auftrags gibt den **Raum** frei: Schnellbau, Simulation, Optuna und Plateau-Eingriffe laufen darin ohne
  Rückfrage.
- Eine fertige Baugruppe oder ein fertiges Teil gibt der Nutzer immer selbst frei, bevor SolidWorks baut. `--im-raum`
  ersetzt dieses OK nicht, es stellt nur sicher, dass das OK genau das Ergebnis deckt. `RAUM_GEAENDERT`,
  `AUSSERHALB_RAUM`, `KOPIE_GEAENDERT`, `FORM_GEAENDERT` → Nutzer fragen, neu freigeben.
- Formänderungen nur aus `erlaubte_formaenderungen`; neue Parameter, neue Stellschrauben, anderer Rahmen, Ziel oder
  Szenario sind Raum-Änderungen (neue Freigabe).
- Der Prüfer bleibt am Ende Pflicht; der Bericht geht an den Nutzer.
