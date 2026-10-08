# Messstand – Ergebnisse

Spec: `docs/superpowers/specs/2026-10-09-messstand-design.md`. Messdaten (Transkripte, STL, `kpi.json`, `score.json`)
unter `<arbeitsordner>/MESSSTAND/durchgang-<n>/`. Score-Anker: Durchgang 0 = 2,0.

## Durchgang 0 – Baseline (09.10.2026, Commit a104b8d)

Alle 5 Läufe bestanden, alle **richtig** (Oberflächenabstand zur Referenz < 1e-8 mm), keine Lecks.

| Lauf | Zeit s | Modell | bauen | prüfen | Prüfer | Rest | Tool-Aufrufe | Ausgabe-Tokens | Tokens gew. | Läufe | Fehler | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| d0-durchlicht-1 | 221 | 118 | 50 | 12 | 37 | 4 | 26 | 15339 | 314019 | 1 | 0 | 3923 | ja |
| d0-durchlicht-2 | 212 | 117 | 40 | 9 | 40 | 5 | 26 | 13368 | 292352 | 1 | 0 | 3911 | ja |
| d0-kamera-1 | 332 | 198 | 55 | 21 | 52 | 7 | 36 | 22607 | 465409 | 2 | 3 | 3546 | ja |
| d0-stehlager-1 | 499 | 267 | 184 | 22 | 18 | 8 | 37 | 33871 | 540018 | 1 | 0 | 11083 | ja |
| d0-zentrieraufnahme-1 | 220 | 134 | 49 | 10 | 20 | 7 | 31 | 15514 | 386521 | 1 | 0 | 3954 | ja |

**Wo die Zeit hängt (Summe 1484 s):** Modell (Denken/Schreiben) 56 %, `swki bauen` 25 %, Prüfer-Agent 11 %,
`swki pruefen` 5 %.

- **Modell:** Zeit ≈ Ausgabe-Tokens / ~100 je s plus ~2 s je Runde. Teuer sind das Lesen der Zeichnung (29–50 s) und
  das Schreiben der Spec (33 s); dazu 3–6 Runden Erkundung von Schema und Vorlagen, je Befehl eine eigene Runde
  (validieren, freigeben+bauen, prüfen, ls, Prüfer, status+bericht).
- **bauen:** jedes Feature 3,5–5 s, unabhängig von der Größe (Durchlicht: Platte mit 4 Langlöchern 30 s). Profil
  (cProfile, Durchlicht 39,8 s): 22 s COM-`Invoke` (2480 Aufrufe, ~9 ms, prozessübergreifend), 13,6 s pywin32-
  Overhead (`GetTypeInfo` 7,8 s, `GetIDsOfNames` 5,8 s). Grafikaktualisierung, Feature-Baum und Skizzenanzeige laufen
  beim Bauen mit (nirgends abgeschaltet).
- **prüfen:** 10 s, davon Screenshots 4,9 s, Messen 4,2 s.
- **Prüfer:** 3–4 Runden, 2–5k Ausgabe-Tokens; liest Aufgabe, Spec, Prüfbericht, Zeichnung und 4 Screenshots.
- **Fehler:** nur Kamera (eine Prüfung „Lage des Steckers“ war an einer Extrusion nicht messbar → 2 Prüfmängel,
  neue Freigabe, zweiter Lauf).
- **Speicher:** Teile 3,5–4 GB, Stehlager 11,1 GB.
