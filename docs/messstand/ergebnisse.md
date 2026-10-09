# Messstand – Ergebnisse

Spec: `docs/superpowers/specs/2026-10-09-messstand-design.md`. Messdaten (Transkripte, STL, `kpi.json`, `score.json`)
unter `<arbeitsordner>/MESSSTAND/durchgang-<n>/`. Score-Anker: Durchgang 0 = 2,0. Ziel 7,0, höchstens 5 Umbauten.

## Korrekturen am Messverfahren (vor jeder Score-Entscheidung)

- **Leck:** Ein Agent übernahm die Stehlager-Specs aus `docs/superpowers/plans/…3b…`; zwei Baseline-Läufe hatten
  Ergebnisdokumente mit Teilen der Lösung gelesen. Seitdem fehlen in jedem Lauf-Worktree `docs/`, `tests/live/`,
  `tests/baugruppe/test_referenzen.py`; das ganze Hauptrepo gilt als Leck. Betroffene Läufe liegen unter
  `durchgang-<n>/_ungueltig/` und wurden wiederholt.
- **Stehlager-Aufgabe präzisiert:** Die Beschreibung ließ Details offen (Stiftbohrungstiefe, Ø der Durchgänge);
  ein Agent wählte 15 statt 12 mm Stiftbohrung → „nicht richtig“, obwohl beschreibungskonform. Die Aufgabe enthält
  jetzt die Nutzervorgaben (wie Durchlicht/Kamera); beide Stehlager-Läufe (Baseline, Umbau 1) wurden wiederholt.
- **Skill-Stand:** Das Skill-Tool liefert in einer laufenden Sitzung den Stand vom Sitzungsstart. Ab den
  Wiederholungen liest der Agent den Skill per Read aus seinem Worktree (Baseline-Worktree = Original-Skill).
- **Vordergrund:** Prüfer und Befehle laufen im Vordergrund (Hintergrund-Meldungen gingen bei einer Unterbrechung
  der Sitzung verloren).
- **Richtig:** zusätzlich größter Oberflächenabstand ≤ 1,0 mm (vor der ersten Bewertung festgelegt).

## Durchgang 0 – Baseline (Commit a104b8d)

| Lauf | Zeit s | Modell | Bauen+Prüfen | Prüfer | Tool-Aufrufe | Ausgabe-Tokens | Tokens gew. | Läufe | Fehler | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d0-durchlicht-1 | 221 | 118 | 62 | 37 | 26 | 15339 | 314019 | 1 | 0 | 3923 | ja |
| d0-durchlicht-2 | 212 | 117 | 50 | 40 | 26 | 13368 | 292352 | 1 | 0 | 3911 | ja |
| d0-kamera-1 | 332 | 198 | 76 | 52 | 36 | 22607 | 465409 | 2 | 3 | 3546 | ja |
| d0-stehlager-1 | 459 | 234 | 196 | 23 | 32 | 28971 | 493838 | 1 | 0 | 10729 | ja |
| d0-zentrieraufnahme-1 | 216 | 140 | 49 | 21 | 27 | 16857 | 338556 | 1 | 0 | 3637 | ja |

Summe 1441 s: Modell 56 %, Bauen+Prüfen 30 %, Prüfer 12 %.

**Wo die Zeit hängt:**
- **Modell:** Zeit ≈ Ausgabe-Tokens / ~100 je s plus ~2 s je Runde. Teuer: Zeichnung lesen (29–50 s), Spec schreiben
  (23–33 s), Prüfwerte (Volumen, Schwerpunkt) von Hand nachrechnen (bis 18 s), Erkundung von Schema und Vorlagen
  (3–6 Runden), je swki-Befehl eine Runde.
- **bauen:** jedes Feature 3,5–5 s. Profil (Durchlicht 39,8 s): 22 s COM-`Invoke` (2480 Aufrufe à ~9 ms),
  13,6 s pywin32-Overhead (`GetTypeInfo` 7,8 s, `GetIDsOfNames` 5,8 s); Grafik, Feature-Baum und Skizzenanzeige
  liefen beim Bauen mit.
- **prüfen:** ~10 s (Screenshots 4,9 s, Messen 4,2 s). **Prüfer:** 3–4 Runden, 2–5k Ausgabe-Tokens.
- **Speicher:** schon das Anlegen eines Teils hebt SolidWorks von ~0,4 auf ~2,9 GB (Grafikfenster); Teile 3,5–4 GB,
  Stehlager 10,7 GB.

## Durchgang 1 – Umbau 1 (Commit c6a0d96): deutlich besser → neue Baseline

Umbau: Schnellmodus beim Bauen (CommandInProgress, keine Grafik/Feature-Baum/Skizzenanzeige), `swki durchlauf`
(validieren → freigeben → bauen → prüfen → status in einem Aufruf), Geometrie-Steckbrief aus STL (numpy/scipy/trimesh:
Zylinder mit Achse/Mitte/Ø, Hüllquader, Schwerpunkt) für Agent und Prüfer, Skill mit Kurzreferenz der Prüfwerte.
Live-Regression 11/11 (Stehlager Bau+Prüfung 61 s statt 125–213 s).

| Lauf | Zeit s | Modell | Bauen+Prüfen | Prüfer | Tool-Aufrufe | Ausgabe-Tokens | Tokens gew. | Läufe | Fehler | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d1-durchlicht-1 | 202 | 136 | 29 | 32 | 25 | 17197 | 365608 | 1 | 0 | 3954 | ja |
| d1-durchlicht-2 | 220 | 144 | 28 | 44 | 24 | 17598 | 312704 | 1 | 0 | 3922 | ja |
| d1-kamera-1 | 268 | 172 | 31 | 60 | 28 | 23378 | 397813 | 1 | 0 | 3374 | ja |
| d1-stehlager-1 | 364 | 262 | 61 | 34 | 35 | 32334 | 525022 | 1 | 0 | 10643 | ja |
| d1-zentrieraufnahme-1 | 183 | 129 | 30 | 20 | 24 | 15125 | 285941 | 1 | 0 | 3920 | ja |

Summe 1237 s: Modell 68 %, Bauen+Prüfen 14 %, Prüfer 15 %.

**Score 4,1** (Zeit 2,8 · Aufwand 2,4 · Fehler 10 · Speicher 2,0; Verhältnisse Zeit 0,88, Aufwand 0,96, Fehler 0,
Speicher 1,0). Regel erfüllt (+2,1, kein Teilscore > 1 schlechter, alles richtig) → Merge in `messstand`.
Einordnung: Bauen+Prüfen 3–4× schneller, die Gesamtzeit nur 12 % – das Modell (Denken/Schreiben) ist jetzt 68 % der
Zeit. Der Fehler-Teilscore springt von wenigen Baseline-Fehlern (3, alle Kamera) auf 0 und ist entsprechend unsicher.
Agenten rechnen weiter Volumen von Hand (`volumen: auto` kann Durchgänge und Löcher in der Skizze nicht) und schauen
in Vorlagen.

## Durchgang 2 – Umbau 2 (Commit 433ad57): nicht deutlich besser → verworfen

Umbau (auf Umbau 1): `volumen: auto` rechnet Durchgänge (`durch_alles`, `durch`, auch mit Formschräge) durch eine Platte
und innere Profile einer Skizze als Löcher; Skill ohne Erkundung und Handrechnung, Kurzanleitung Zeichnung lesen,
knappe Kommentare, `durchlauf --freigeben` validiert selbst, Urteil + status + bericht in einem Aufruf; Prüfer auf
Sonnet. Verworfen schon vor der Messung: Teile unsichtbar anlegen (`DocumentVisible False`) – SolidWorks lehnt dann
die globalen Variablen ab (Regression 0/11). Regression des gemessenen Stands 11/11.

| Lauf | Zeit s | Modell | Bauen+Prüfen | Prüfer | Tool-Aufrufe | Ausgabe-Tokens | Tokens gew. | Läufe | Fehler | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d2-durchlicht-1 | 176 | 121 | 29 | 24 | 22 | 15179 | 338693 | 1 | 0 | 3911 | ja |
| d2-durchlicht-2 | 184 | 105 | 31 | 46 | 21 | 16141 | 275625 | 1 | 0 | 3926 | ja |
| d2-kamera-1 | 208 | 145 | 27 | 33 | 23 | 17526 | 304261 | 1 | 0 | 3361 | ja |
| d2-stehlager-1 | 377 | 290 | 61 | 20 | 35 | 35569 | 574978 | 1 | 0 | 10482 | ja |
| d2-zentrieraufnahme-1 | 267 | 186 | 56 | 23 | 26 | 19840 | 332373 | 2 | 1 | 4156 | ja |

Summe 1212 s: Modell 70 %, Bauen+Prüfen 17 %, Prüfer 12 %.

**Score 3,8** (Zeit 2,9 · Aufwand 2,8 · Fehler 8,0 · Speicher 2,0) < 4,1 + 1,0 → verworfen, Umbau 1 bleibt Baseline.
Ursache des Rückschritts: die neue Regel „Aufsatz auf der Fläche beginnen“ ist bei einem `mittig`-Steg mit Formschräge
falsch (die Grundkante wird mitgeschrägt → Keilspalt → 2 Körper → zweiter Lauf). Kamera (−37 %) und Durchlicht
(−17 %) wurden schneller; Agenten lesen trotz Hinweis weiter Schema und Vorlagen (Teile 3–5 Runden, Stehlager
13 Aufrufe).

**Speicher-Test (Wegwerf):** ein neues Teil hebt SolidWorks von 0,43 auf ~3,0 GB – gleich bei normalem,
minimiertem und unsichtbarem Hauptfenster. Der Speicher hängt nicht am Fenster; kein Hebel über die Anzeige.

## Durchgang 3 – Umbau 3 (Commit f583a35): nicht deutlich besser → verworfen

Umbau (Umbau 2 ohne unsichtbares Anlegen, Steg-Regel korrigiert: mitgeschrägter Steg 1 mm in die Platte) plus
vollständige Syntax-Kurzreferenzen im Skill `konstruieren` (alle Elemente, Ebenen, Endbedingungen, Feature-Typen,
(u, v)-Regel auf Flächen) und `baugruppe` (Komponenten, Referenzen, Verknüpfungen, EINBAU-Referenzen der Normteile,
Ausrichtungsregel; Beispiel „Klemmhalter“ mit `swki validieren` gültig).


| Lauf | Zeit s | Modell | Bauen+Prüfen | Prüfer | Tool-Aufrufe | Ausgabe-Tokens | Tokens gew. | Läufe | Fehler | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d3-durchlicht-1 | 165 | 94 | 27 | 42 | 20 | 13497 | 244509 | 1 | 0 | 3367 | ja |
| d3-durchlicht-2 | 140 | 88 | 28 | 22 | 18 | 12154 | 221488 | 1 | 0 | 3362 | ja |
| d3-kamera-1 | 290 | 176 | 78 | 34 | 23 | 21840 | 327526 | 3 | 3 | 4289 | ja |
| d3-stehlager-1 | 309 | 221 | 60 | 23 | 30 | 29882 | 438163 | 1 | 0 | 10534 | ja |
| d3-zentrieraufnahme-1 | 146 | 95 | 29 | 18 | 22 | 11780 | 242769 | 1 | 0 | 3373 | ja |

**Score 3,4** (Zeit 3,8 · Aufwand 4,3 · Fehler 2,0 · Speicher 2,5; Verhältnisse Zeit 0,73, Aufwand 0,77) < 5,1 →
verworfen. Zeit und Aufwand so gut wie nie (Durchlicht 140–165 s, Zentrieraufnahme 146 s, Stehlager 309 s), aber
Kamera 3 Läufe + neue Freigabe: C-Mount und Freiraum ab derselben Fläche überlappen, `volumen: auto` zählt doppelt,
und weil `auto` aus der Freigabe-Kopie rechnet, hilft kein Bauweg → neue Freigabe. Ein Fehlerfall kippt den
Fehler-Teilscore von 10 auf 2 (Baseline: 0,6 Fehler je Lauf).

## Durchgang 4 – Umbau 4 (Commit 3bac8d7): deutlich besser → neue Baseline

Umbau 3 plus: `volumen: auto` zieht den gemeinsamen Teil ineinanderliegender Schnitte (bzw. Aufsätze) ab derselben
Skizzenebene ab (Kamera: Freiraum hinter der C-Mount-Senkung). Sollvolumen aller 20 Referenz-Teilspecs unverändert
(ohne SolidWorks geprüft), Code sonst wie Umbau 2 (Regression 11/11).


| Lauf | Zeit s | Modell | Bauen+Prüfen | Prüfer | Tool-Aufrufe | Ausgabe-Tokens | Tokens gew. | Läufe | Fehler | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d4-durchlicht-1 | 149 | 90 | 27 | 30 | 20 | 12725 | 235793 | 1 | 0 | 3355 | ja |
| d4-durchlicht-2 | 140 | 83 | 30 | 26 | 20 | 12104 | 224112 | 1 | 0 | 3298 | ja |
| d4-kamera-1 | 180 | 116 | 28 | 35 | 20 | 16069 | 259258 | 1 | 0 | 3563 | ja |
| d4-stehlager-1 | 362 | 271 | 64 | 22 | 31 | 34410 | 467827 | 1 | 0 | 10462 | ja |
| d4-zentrieraufnahme-1 | 131 | 79 | 29 | 21 | 19 | 10733 | 211155 | 1 | 0 | 3294 | ja |

**Score 5,4** (Zeit 4,3 · Aufwand 4,6 · Fehler 10 · Speicher 3,4; Verhältnisse Zeit 0,65, Aufwand 0,74, Fehler 0,
Speicher 0,92) ≥ 4,1 + 1,0, kein Teilscore schlechter, alles richtig → Merge in `messstand`. Alle Läufe im ersten
Baulauf bestanden, Agenten lesen kein Schema mehr (Teile 9 Tool-Aufrufe im Hauptagenten statt 16–26).
