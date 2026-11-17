# Zeichnungsableitung – Ergebnisse

Design: `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md`. Plan Z1.0/Z1.1:
`docs/superpowers/plans/2026-11-16-zeichnungsableitung-z1-spike-spec.md`. Recherche: `recherche.md`, Härte und Halbzeug:
`haerteangabe.md`.

## Stand 17.11.2026

| Etappe | Stand |
|---|---|
| Z1.0 Spike (API live) | offen, wartet auf OK des Nutzers für SolidWorks |
| Z1.1 Spec-Erweiterung | umgesetzt (Branch `claude/zeichnungsableitung-recherche`) |
| Z1.2 Freistich, Zentrierbohrung | offen (Skill `compiler-erweitern`) |
| Z1.3 Zeichnen, Z1.4 Prüfen | offen, Plan nach dem Spike |
| Z1.5 Firmenvorlage | wartet auf die Vorlage des Nutzers; Fertigungszeichnungen nur auf dem Firmenrechner |

## Z1.1 – was jetzt gilt

- Schema `teil.schema.json`: am Feature (`extrusion`/`schnitt`, `rotation`, `austragung`, `bohrung`, `normbohrung`,
  `verrundung`, `fase`) `funktion`, `passung`, `toleranz`, `rauheit`, `form_lage`, `huelle`, `bearbeitung`,
  `behandlung`; Top-Level `verfahren`, `bezuege`, `toleranzen`, `behandlung`, `halbzeug`.
- Regeltabelle `swki/wissen/funktionen.yaml` (11 Funktionen) mit Quelle, Beleg je Wert, `bestaetigt`. Nur
  `lagersitz_gehaeuse` ist ohne C-Wert; alle anderen meldet `validieren` als Hinweis `funktion`, bis der Nutzer bestätigt.
- `swki/spec/funktionen.py`: `aufloesen` (eigene Werte vor Tabelle, eigene Toleranz ersetzt Tabellenpassung),
  `anforderung_befunde` (blockierend in `validieren`).
- Prüfsumme: `verfahren`, `toleranzen`, `behandlung`, `halbzeug` nur wenn vorhanden; Anforderungen an Features als
  sortierte, doppelfreie Tupel [Art, Nenngröße, Felder] ohne Feature-IDs. Specs ohne neue Felder: Prüfsumme unverändert
  (fester Hash im Test). `bezuege` sind Bauweg. Teil-Freigabe legt die aufgelösten Werte in `freigabe.json`
  (`anforderungen`) ab.
- Hinweise: Regel 8 entfällt bei `bearbeitung: erodieren`; Ra < 0,8 ohne Schleifen; geschliffenes Drehteil ohne
  Freistich.

## Offen für Z1.3/Z1.4

- Aufgelöste Werte für Teile, die über eine Baugruppen-Freigabe laufen (heute nur Teil-Freigaben).
- Bezugsvorschlag aus `deckungsgleich`-Verknüpfungen der Baugruppe (Design §4.1).
- Zahlenwert für `form_lage` mit `it` (Rundheit IT4/IT5) aus ISO 286 rechnen.
- Prüfung der Lage und Anzahl der Funktionsmerkmale am Modell (`ANFORDERUNG_GEAENDERT`, Design §4.2).
