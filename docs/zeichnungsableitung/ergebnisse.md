# Zeichnungsableitung – Ergebnisse

Design: `docs/superpowers/specs/2026-11-16-zeichnungsableitung-design.md`. Plan Z1.0/Z1.1:
`docs/superpowers/plans/2026-11-16-zeichnungsableitung-z1-spike-spec.md`. Recherche: `recherche.md`, Härte und Halbzeug:
`haerteangabe.md`.

## Stand 17.11.2026

| Etappe | Stand |
|---|---|
| Z1.0 Spike (API live) | erledigt 17.11. (`spike-z1.md`): alles ohne Dialog außer Bohrungsangaben; Modellmaße nur gefiltert brauchbar |
| Z1.1 Spec-Erweiterung | umgesetzt (Branch `claude/zeichnungsableitung-recherche`) |
| Z1.2 Freistich, Zentrierbohrung | offen (Skill `compiler-erweitern`) |
| Z1.3 Zeichnen | Stufe 1 (Blatt und Ansichten) umgesetzt 17.11., wartet auf Durchsicht der PDFs; Stufen 2–5 offen |
| Z1.4 Prüfen | offen |
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
  sortierte Tupel [Art, Nenngröße, Felder, Anzahl Instanzen] ohne Feature-IDs. Specs ohne neue Felder: Prüfsumme unverändert
  (fester Hash im Test). `bezuege` sind Bauweg (Anker auf ein unbekanntes Feature ist ein Befund). Jeder Freigabeweg legt die
  aufgelösten Werte in `freigabe.json` (`anforderungen`) ab.
- Hinweise: Regel 8 entfällt bei `bearbeitung: erodieren`; Ra < 0,8 ohne Schleifen; geschliffenes Drehteil ohne
  Freistich.

## Z1.3 Stufe 1 – Blatt und Ansichten (17.11.2026)

- `swki zeichnen <spec> [--lauf N]` (`swki/zeichnung/`): Format A4 hoch oder A3 quer und Vorzugsmaßstab (`blatt.py`),
  Ansichten aus der Spec (`ansichten.py`), Anordnung nach Projektionsmethode 1 mit 25 mm Maßrand (`layout.py`),
  Umsetzung in SolidWorks (`zeichnen.py`); Ausgabe SLDDRW, PDF, PNG unter `<laufordner>/zeichnung/`, Teildatei unverändert.
- Drehteil mit Innenkontur: Stirnansicht als Modellansicht, Hauptansicht = Vollschnitt A-A daraus. Ohne Innenkontur:
  Hauptansicht mit liegender Achse, Stirnansicht projiziert bei Bohrungen. Frästeil: Hauptansicht von der Seite mit den
  meisten Features, Dickenansicht projiziert darunter, Seitenansicht bei Features quer dazu.
- Mittellinien und Mittelpunktmarken über die Dokumentoptionen (automatisch beim Erzeugen der Ansichten).
- Schriftfeld über Eigenschaften der Zeichnung (Gezeichnet, Datum, Werkstoff); das SW-2025-Muster liest Benennung als
  `$PRPSHEET:"Description"` aus dem Modell und die Zeichnungsnummer aus dem Dateinamen – Zuordnung erst mit den
  Formaten des Nutzers (Z1.5).
- Live-Befunde (korrigieren Spike Z1.0): Skizzen in Ansichten liegen in Ansichtskoordinaten ((Blatt − Position) ÷
  Maßstab); in gedrehten Ansichten zusätzlich gedreht, ein Ausbruch dort wirkt nicht. Neue Ansichten sind automatisch
  skaliert; der Maßstab wird je Ansicht gesetzt. `IView.Position` nur als double-Array.
- Laufzeit 39–58 s je Zeichnung (Ursache offen). PDFs zur Durchsicht: `<arbeitsordner>/Z1-STUFE1/`.

## Härte und Halbzeug (Nachrecherche `haerteangabe.md`)

- Härteangabe nach DIN ISO 15787:2018-08 (= ISO 15787:2016): Wert mit Grenzabmaßen in Klammern, „(60 ± 2) HRC“;
  „58+4 HRC“ ist der alte Stil (DIN 6773). Schema: `haerte`/`kernhaerte` als `{wert, plus?, minus?, verfahren}`,
  `tiefe` als `{art: CHD|SHD|NHD|CLT, wert, plus?, minus?, grenzhaerte?}`, `zustand: fertigteil|vor_schleifen`,
  `schicht: {norm, bezeichnung, dicke_um?}` (z. B. DIN EN ISO 19598 „Fe//Zn8//Cn//T0“), optionale `id` für örtliche
  Behandlung. `halbzeug` ohne `werkstoff` (aus `material`), mit `toleranz`, `zustand`.
- Offen beim Nutzer: Härtestil als Hausregel (ISO 15787:2016 empfohlen oder DIN 6773); Angabe „darf nicht behandelt
  werden“ (z. B. weich bleibendes Gewinde) hat noch kein Feld; PDF-Kandidaten (iTeh-Auszug ISO 15787:2016) brauchen OK.

## Offen für Z1.3/Z1.4

- Bezugsvorschlag aus `deckungsgleich`-Verknüpfungen der Baugruppe (Design §4.1).
- Zahlenwert für `form_lage` mit `it` (Rundheit IT4/IT5) aus ISO 286 rechnen.
- Prüfung der Lage und Anzahl der Funktionsmerkmale am Modell (`ANFORDERUNG_GEAENDERT`, Design §4.2).
- Hinweis „Parameter in `toleranzen` treibt mehrere Maße“ (§4.1), Mindestradius beim Drahterodieren (§4.5).
- Kleinere Review-Punkte (Ledger „minor (deferred)“): weitere Plausibilitätsprüfungen der Toleranzfelder, Beleg je
  Feld im Hinweis, `lagersitz_gehaeuse` vom Nutzer bestätigen lassen, RWDR-Hinweis in der Auflösung.
