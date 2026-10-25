---
name: optimieren
description: Optimiert eine Teil- oder Baugruppen-Spec autonom ohne SolidWorks (Schnellbau + MuJoCo + Optuna, swki optimiere) – Optimierungsauftrag (Block optimierung, Prüfaufgabe) schreiben, Raum freigeben lassen, Schleife im Hintergrund starten, am Ende (ZIEL, PLATEAU, BUDGET, FEHLER) eingreifen, Gewinner im Raum übernehmen und in SolidWorks nachbauen. Verwenden, wenn der Nutzer eine Funktion (Fallen, Schieben, Sortieren) per Simulation optimieren oder Stellschrauben abstimmen lassen will, oder wenn ein swki-optimiere-Lauf endet.
---

# Optimieren (Stufe C2, Ausbaustufe 1: Claude in einer Sitzung)

Spec: `docs/superpowers/specs/2026-10-25-optimierung-c2-design.md` (Block §2, Prüfaufgabe §3, Ablauf §4, Freigaberegel §6).
Die innere Schleife läuft **ohne Claude**; Claude schreibt den Auftrag, startet und greift nur am Ende ein. Die Bewertung
ist **eingefroren**: Prüfaufgabe, Simulations-Datei, Ziel und Szenarien während eines Laufs nie ändern; Optuna wählt die
Zahlen, Claude nur Startpunkte (`start`, ≤ 20) und Formen.

## 1. Auftrag
- Spec wie gewohnt (Skill `konstruieren` bzw. `baugruppe`), dazu der Block `optimierung` (Syntax: Spec §2, Beispiel
  `auftraege/C2-WEICHE/pruefstation.yaml`). Stellschrauben verweisen auf Zahlen-Parameter; abhängige Maße schreibt man
  als Ausdruck der Stellschraube in die Features (Beispiel: `rutsche.yaml` mit `T`). `rahmen` = Grenzen des Auftrags
  (vom Nutzer), `bereich` = Startbereich der Suche. Parameter für erlaubte Formen gleich mit anlegen (z. B. `ZF`), sonst
  braucht ihre Stellschraube später eine neue Freigabe.
- Prüfaufgabe als Python-Modul im Auftragsordner (`jobs`, `lauf`, optional `kennzahlen`, `MJCF = True`,
  `ABHAENGIGKEITEN`); Fehlschläge als `fehlerbild` klassifizieren (wo, warum: „Abprall am Keil“, „Treffer auf die
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
- **ZIEL**: `swki optimiere <spec> --uebernehmen` (schreibt die Gewinnerwerte, gibt im Raum frei; `freigegeben: false`
  → Nutzer fragen). Dann, wenn SolidWorks frei ist (nie zwei SolidWorks-Arbeiten gleichzeitig): `swki durchlauf <spec>
  --neustart` → Prüfer → `swki bericht`; Bericht an den Nutzer mit Lauf, Gewinner, Prüfstufe 2, Ablaufgrößen für die
  Steuerung (`ablauf`).
- **PLATEAU**: aus `plateau.md` (Fehlerbilder, Wichtigkeit, Grenzanschläge, bereits versuchte Varianten) **eine** Maßnahme:
  1. eine Formvariante, nur aus `erlaubte_formaenderungen`, als Spec-Änderung mit neuer `variante`; nicht erlaubte
     Formen → Nutzer fragen;
  2. oder `bereich` im `rahmen` ändern (Grenzanschlag am Rahmen → Nutzer fragen, ob der Rahmen wachsen darf);
  3. oder abbrechen/annehmen und dem Nutzer berichten.
  Dann `swki validieren` und neu starten (§2). Eine Variante, die schon unter „Bereits versucht“ steht, nicht wiederholen.
- **BUDGET**: Ergebnis mit Prüfstufe 2 berichten; mehr Budget nur auf Wunsch des Nutzers.
- **FEHLER**: `detail` lesen, Ursache beheben (Prüfaufgabe, Spec), neuen Lauf starten; `BEWERTUNG_GEAENDERT` heißt:
  während des Laufs wurde Bewertung oder Code geändert → neuer Lauf.

## 4. Freigaberegel (Nutzer 25.10.2026)
- Die Freigabe gibt den **Raum** frei; ein Ergebnis im Raum wird ohne Rückfrage freigegeben (`--uebernehmen` bzw.
  `swki freigeben <spec> --im-raum`) und gebaut. `RAUM_GEAENDERT`/`AUSSERHALB_RAUM` → Nutzer fragen, neu freigeben.
- Formänderungen nur aus `erlaubte_formaenderungen`; neue Parameter, neue Stellschrauben, anderer Rahmen, Ziel oder
  Szenario sind Raum-Änderungen (neue Freigabe).
- Der Prüfer bleibt am Ende Pflicht; der Bericht geht an den Nutzer.
