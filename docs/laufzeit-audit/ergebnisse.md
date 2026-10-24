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
