# Bewertungsbogen BTP – Ergebnisse

Bogen: `docs/superpowers/specs/2026-10-23-bewertungsbogen-design.md`. Audit: `2026-10-23-audit.md`. Recherche:
`recherche.md`. Auftrag der Goal-Session: `goal-auftrag.md`. Messdaten unter `<arbeitsordner>/MESSSTAND/` (nicht im
Git). Zielscore 6,5, höchstens 5 Umbauten.

## Einrichtung (24.10.2026, Branch `btp`)

- Messstand erweitert: Score `werkzeuge/messstand/btp.py`, Aufgabe `pruefstation` (Vorlage + Ausgangslauf),
  Fallen `werkzeuge/messstand/fallen.py` mit F1–F6, R1–R2 (`tests/messstand/fallen/`).
- Stand der Messung: `main` mit Paket Bemaßungsbezug (PR #17) und AP 6.8 (602dc8f), gemergt in `btp`.
- Vorlage Prüfstation: AP 6.8 Stand Lauf 28, eingefroren 24.10. (`MESSSTAND/vorlagen/pruefstation`); Freigabe der
  Vorlage gilt mit dem neuen Stand weiter.
- Referenz der Änderung (Kamerahalter ± 20, Schenkel B 12, M3 × 12): `MESSREF-pruefstation` Lauf 1, gebaut 263 s,
  `swki pruefen` bestanden (Kameraschrauben 3,4 mm Einschraubung wie vorher), STL `MESSSTAND/referenz/pruefstation.stl`.
  Referenzen der übrigen Aufgaben vom 09.10. (Geometrie unabhängig vom Code-Stand).

### Eigene Entscheidungen bei der Einrichtung

| Entscheidung | Begründung |
|---|---|
| Vorlage ohne `bezug` lassen (validieren meldet `bezug`-Hinweise) | Messung soll den echten AP-6.8-Stand abbilden; `bezug` ist Bauweg und wäre eine Änderung vor der Messung |
| Fallen-Aufträge `MESSFALLE-*` und Referenz `MESSREF-*` ohne Rückfrage freigeben | Bogen §6 sieht ihren Bau vor (vom Nutzer abgenommen); wie `MESSREF-*` am 09.10.; reine Messaufträge |
| Fallen-Prüfer als `general-purpose`-Agent mit eingebetteter `pruefer.md` des gemessenen Commits | Agenten-Definitionen lädt Claude Code beim Sitzungsstart; so prüft jeder Durchgang mit dem Prüfer seines Stands |
| Messdaten vom 09.10. nach `MESSSTAND/messstand-2026-10-09/` verschoben | `vorbereiten` legt Läufe unter `durchgang-<n>` an; die alten Ordner gleichen Namens wären überschrieben worden (bei Durchgang 0 ist das passiert, siehe unten) |
| Lauf `d0-durchlicht-2` wiederholt (`_ungueltig/d0-durchlicht-2-gestoert`) | Fallen F1/F2 wurden versehentlich gleichzeitig mit SolidWorks gebaut; Regel seitdem: nie zwei SolidWorks-Arbeiten gleichzeitig |
| Mess-Prompt: „Alle Schritte vor der Freigabe-Vorlage (auch der Konstruktionsreview) laufen wie im Betrieb“ | Ohne diesen Satz ließ ein Agent den Review aus (Freigabe war erteilt); Nutzerentscheidung „Review wie im Betrieb“ |
| Falle F4 mit gemessenem Sollvolumen, F1/F2 mit stimmigen Kommentaren | Fallen müssen `swki pruefen` bestehen und dürfen sich nicht über widersprüchliche Kommentare verraten |

## Durchgang 0 – Ausgangswert (24.10.2026, Commit 4d28320 auf `btp`)

| Lauf | Zeit s | Modell | Review | Prüfer | Werkzeug (durchlauf) | Tool-Aufrufe | Tokens gew. | Läufe | Fehlerpunkte | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d0-durchlicht-1 | 240 | 122 | 64 | 30 | 18 | 30 | 403123 | 1 | 0 | 3352 | ja |
| d0-durchlicht-2 | 253 | 131 | 58 | 39 | 19 | 31 | 356698 | 1 | 0 | 3357 | ja |
| d0-kamera-1 | 334 | 165 | 109 | 22 | 32 | 31 | 412767 | 2 | 1 | 3570 | ja |
| d0-zentrieraufnahme-1 | 195 | 103 | 23 | 27 | 32 | 28 | 305578 | 2 | 2 | 3570 | ja |
| d0-stehlager-1 | 343 | 204 | 64 | 20 | 46 | 41 | 492854 | 1 | 0 | 10354 | ja |
| d0-pruefstation-1 | 995 | 200 | 105 | 65 | 601 | 52 | 1078019 | 1 | 0 | 28155 | ja |

Fallen: 6 von 6 Treffern, 0 Fehlalarme; alle 24 Einzelurteile eindeutig (keine unklaren).

**Score 4,9** (Ziel 6,5):

| Gruppe | Wert | Teilscore |
|---|---|---|
| Zeit Teile | 258 s (durchlicht 247, kamera 334, zentrieraufnahme 195) | 1,3 |
| Zeit Stehlager | 343 s | 4,8 |
| Zeit Prüfstation | 995 s | 5,0 |
| Präzision erster Lauf | 3 Fehlerpunkte | 3,5 |
| Präzision Fallen | 6 | 10,0 |
| Aufwand | 1,0 (Bezug) | 5,0 |
| Robustheit | 28 155 MB | 0,0 |

**Wo die Zeit jetzt hängt:**
- **Konstruktionsreview** (seit 11.10., im Audit fehlend): 23–109 s je Lauf, bei den Teilen 25–33 % der Zeit. Er ist der
  Hauptgrund, warum die Teile gegenüber dem Messstand Umbau 5 (09.10.: ~140 s) bei ~250 s liegen.
- **Prüfstation:** Durchlauf 601 s (Bauen 256 s: Teile 105 – vorher 274 dank Bemaßungsbezug –, Verknüpfen 91,
  Grundstellung 22; Prüfen ~300 s; 2 Neustarts), Modell 200 s, Review 105 s, Prüfer 65 s.
- **Fehlerpunkte:** Kamera – Bezug `u: mitte` glich die Höhen der beiden M2 an (Zeichnung 20,25/20,22; Paket
  Bemaßungsbezug), Prüfmangel, zweiter Bauweg-Lauf. Zentrieraufnahme – falscher Messanker der Taschentiefe (Prüfwert),
  Prüfmangel und zweite Freigabe.
- **Speicher:** Prüfstation 27,5–28,2 GB beim Bauen (Verknüpfen/Grundstellung, ~390–480 s nach Laufbeginn), Prüfen
  ~14 GB. Vor dem Bemaßungsbezug lag die Spitze bei 14,3 GB. Ursache offen.

**Panne:** Die Rohdaten des Messstand-Durchgangs 0 vom 09.10. (gleiche Lauf-Namen `d0-*`) wurden von `vorbereiten`
überschrieben; die Zusammenfassung steht weiter in `docs/messstand/ergebnisse.md`, die übrigen Durchgänge liegen unter
`MESSSTAND/messstand-2026-10-09/`.
