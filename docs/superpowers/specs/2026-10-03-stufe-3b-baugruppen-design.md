# Stufe 3b – Baugruppen statisch (Standardverknüpfungen, Bestimmtheit, statische Kollision)

Ergänzung zu [2026-09-26-solidworks-ki-design.md](2026-09-26-solidworks-ki-design.md) (§3 Projektstruktur, §4 Spezifikation,
§5 Compiler, §6 Prüfung, §9 Skills, §11 Stufen) und [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md)
(Einbaureferenzen, Bibliothek). Stand 2026-10-03, mit dem Nutzer abgestimmt.

## 1. Ziel

Claude baut aus einer freigegebenen Spezifikation eine statische Baugruppe aus selbst konstruierten Teilen und Normteilen,
verknüpft sie mit Standardverknüpfungen voll bestimmt, prüft Verknüpfungen, Bestimmtheit, statische Kollision, Lage und jedes
Eigenteil selbst und bessert nach. Der Mensch greift wie bisher nur an einer Stelle ein: der Freigabe (Design §1).

Neu gilt für Teile und Baugruppen: Manuelle Änderungen an gebauten Dateien gehen nicht mehr still verloren. swki erkennt sie vor
jedem neuen Lauf, und Claude fragt, ob sie in die Spezifikation übernommen werden.

## 2. Entscheidungen (mit dem Nutzer, 2026-10-03)

| Frage | Entscheidung |
|---|---|
| Referenzbaugruppe | **Stehlager**: Grundplatte (fixiert), Lagerunterteil, Lagerdeckel; Deckel → Unterteil mit 2 × ISO 4762 in Gewinde; Unterteil → Grundplatte mit 2 Durchsteckverschraubungen (ISO 4762 + 2 × ISO 7089 + ISO 4032) und 2 × ISO 8734 zum Zentrieren |
| Freigabe und Bau der Eigenteile | **eine Freigabe** für Baugruppe und Teil-Specs; jeder Baugruppen-Lauf baut alle Eigenteile frisch, prüft jedes per Code und baut dann zusammen |
| Normteildateien | `swki normteil hole` (Cache oder Neubau), Datei **in den Lauf-Ordner kopiert**; die Baugruppe verweist nie auf die Bibliothek |
| Wiederholungen | **`je_position`**: eine Komponente je Position einer Bohrung, aufgelöst in Einzelinstanzen und Einzelverknüpfungen |
| Referenzen bei Eigenteilen | **alle Teil-Anker**: `referenz`, `{feature, flaeche}`, Bohrungsachse, Fläche einer Bohrungsinstanz, Standardebene, `nahe` (Teilkoordinaten, Hinweis) |
| Manuelle Änderungen | **Spec bleibt Quelle** + Änderungserkennung vor jedem Lauf + Rücklesen der Parameter; Übernahme nur nach Bestätigung mit neuer Freigabe; gilt auch für Einzelteile |
| Bestimmtheit | **Drehung sperren** bei konzentrischen Verknüpfungen mit Normteilen (Vorgabe); jede Komponente voll bestimmt, außer ausdrücklich `unterbestimmt` erlaubt; überbestimmt ist immer ein Mangel |
| Kollision Schraube in Gewinde | **Gewindepaarung erkennen und nachrechnen** (Ringvolumen über die Einschraublänge); jede andere Überlappung ist ein Mangel; Berührung ist keine Kollision |
| Umfang der Prüfung | **vollständig**: Verknüpfungen, Bestimmtheit, Kollision, Stückliste, Teilprüfung je Eigenteil, Passung Normteil ↔ Bohrung (in `validieren`), Hüllquader, `masse_pruefen` über Komponenten, Screenshots; **ein** Prüfer-Agent |
| Skills | eigener Skill **`baugruppe`**; `konstruieren` bekommt nur Verweis und den Schritt „manuelle Änderung erkannt“ |
| Architektur | **gleiche Befehle**, Weiche nach `art`; neues Paket `swki/baugruppe/` |
| Freigabe-Umfang | Prüfsumme über `art, name, parameter, eigenschaften, komponenten, freiheitsgrade, pruefung` und die Teil-Prüfsummen; **Verknüpfungen sind Bauweg** |
| Unterbaugruppen | nicht in 3b (eine Ebene) |

## 3. Bausteine

```
schema/baugruppe.schema.json        Schema der Baugruppen-Spezifikation
swki/baugruppe/                     Paket: laden/auflösen (je_position), Plausibilität und Passung, Freigabe, Bau,
                                    Referenzen im Baugruppenkontext, Messen, Bewertung, Gewindepaarung
swki/aenderungen.py                 Änderungserkennung für Teile und Baugruppen (Hash, Rücklesen)
.claude/skills/baugruppe/           neuer Skill
tests/referenz/stehlager/           Referenz: stehlager.yaml + grundplatte.yaml, unterteil.yaml, deckel.yaml
```

Die Befehle `validieren`, `freigeben`, `bauen`, `pruefen`, `status`, `bericht` lesen `art` und verzweigen bei
`art: baugruppe` in `swki/baugruppe/`. Schleife, Prüfer-Urteil, `status` und `bericht` bleiben gemeinsam. Neu ist der Befehl
`swki aenderungen <spec>` (§8).

## 4. Spezifikationsformat

Eine Baugruppe ist ein Auftragsordner mit einer Baugruppen-Spec und den Teil-Specs ihrer Eigenteile (Teil-Format unverändert).
Beispiel Stehlager. **Maße, Feature-IDs und Längen nur zur Veranschaulichung; die echte Referenz legt der Plan fest.**

```yaml
art: baugruppe
name: Stehlager
eigenschaften: {Benennung: Stehlager}
parameter: {H: 60}
komponenten:
  - {id: grundplatte, quelle: {teil: grundplatte.yaml}, fixiert: true}
  - {id: unterteil,   quelle: {teil: unterteil.yaml}}
  - {id: deckel,      quelle: {teil: deckel.yaml}}
  - {id: deckelschraube, quelle: {normteil: "ISO 4762 M8x30"}, je_position: {komponente: deckel, feature: f4}}
  - {id: fussschraube,   quelle: {normteil: "ISO 4762 M10x50"}, je_position: {komponente: unterteil, feature: f5}}
  - {id: scheibe_kopf,   quelle: {normteil: "ISO 7089 M10"},    je_position: {komponente: unterteil, feature: f5}}
  - {id: scheibe_mutter, quelle: {normteil: "ISO 7089 M10"},    je_position: {komponente: unterteil, feature: f5}}
  - {id: mutter,         quelle: {normteil: "ISO 4032 M10"},    je_position: {komponente: unterteil, feature: f5}}
  - {id: stift,          quelle: {normteil: "ISO 8734 8x30"},   je_position: {komponente: grundplatte, feature: f3}}
verknuepfungen:
  - {id: v1, typ: deckungsgleich, a: {komponente: unterteil, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v2, typ: konzentrisch, a: {komponente: unterteil, feature: f6, instanz: 1, achse: true},
     b: {komponente: grundplatte, feature: f3, instanz: 1, achse: true}}
  - {id: v10, typ: konzentrisch, a: {komponente: deckelschraube, referenz: EINBAU_ACHSE},
     b: {komponente: deckel, feature: f4, instanz: je, achse: true}}
  - {id: v11, typ: deckungsgleich, a: {komponente: deckelschraube, referenz: EINBAU_EBENE},
     b: {komponente: deckel, feature: f4, instanz: je, flaeche: "+y"}, ausrichtung: gleich}
  - {id: v20, typ: deckungsgleich, a: {komponente: mutter, referenz: EINBAU_EBENE},
     b: {komponente: scheibe_mutter, referenz: EINBAU_EBENE_2}, ausrichtung: entgegengesetzt}
pruefung:
  huellquader: [200, 115, 100]
  masse_pruefen:
    - {was: Achshöhe, von: {komponente: grundplatte, feature: f1, flaeche: "-y"},
       zu: {komponente: unterteil, feature: f3, achse: true}, soll: "=H", tol: 0.01}
```

### 4.1 Komponenten

- `id` (eindeutig, Zeichen wie Feature-IDs; der Punkt ist den Instanzen vorbehalten), `quelle` und optional `fixiert`,
  `je_position`, `gruppe`.
- `quelle`: `{teil: <datei.yaml>}` (Teil-Spec im selben Auftragsordner) oder `{normteil: "<Norm> <Größe>", variante?}` in der
  Schreibweise von `swki normteil hole`; ohne `variante` gilt die Vorgabe der Normtabelle.
- **Genau eine** Komponente ist `fixiert: true`. Ihr Ursprung liegt im Baugruppenursprung, ihre Achsen fallen mit den
  Baugruppenachsen zusammen. Alle anderen werden ausschließlich über Verknüpfungen positioniert.
- Eine Teil-Spec darf von mehreren Komponenten verwendet werden (gleiche Datei, mehrere Instanzen).

### 4.2 `je_position`

- `je_position: {komponente, feature}` verweist auf ein Feature vom Typ `normbohrung` oder `bohrung` eines Eigenteils.
- swki erzeugt je Position eine Instanz `<id>.1 … <id>.n` (Reihenfolge der `positionen` im Feature).
- Jede Verknüpfung, die eine solche Komponente nennt, wird je Instanz vervielfältigt (`v10` → `v10.1 … v10.n`); in ihr steht
  `instanz: je` für die Position der jeweiligen Instanz.
- Zwei `je`-Komponenten dürfen in einer Verknüpfung nur gemeinsam vorkommen, wenn sie **dasselbe** `je_position` haben; dann
  paart Instanz i mit Instanz i. Sonst ist es ein Plausibilitätsbefund.
- `instanz: je` ist nur in Verknüpfungen erlaubt, die eine `je`-Komponente nennen, und nur auf das Feature ihres `je_position`.

### 4.3 Referenzen

| Form | Bedeutung |
|---|---|
| `{komponente, referenz: <id>}` | benanntes `referenz`-Feature des Teils; bei Normteilen nur `EINBAU_*` |
| `{komponente, feature, flaeche: <richtung>}` | semantische Fläche wie im Teil-Format |
| `{komponente, feature, instanz, achse: true}` | Achse der Bohrungsinstanz (Zylinderfläche der Position) |
| `{komponente, feature, instanz, flaeche: <richtung>}` | **neu:** Fläche einer Bohrungsinstanz in Richtung, z. B. Senkungsgrund |
| `{komponente, ebene: vorne\|oben\|rechts}` | Standardebene des Teils |
| `{komponente, nahe: [x, y, z]}` | Punktanker in **Teilkoordinaten** (mm); `validieren` meldet einen Hinweis |

`instanz` ist eine Zahl ≥ 1 oder `je` (§4.2). Die Auflösung geschieht im Teildokument mit dem vorhandenen Anker-Auflöser, das
Ergebnis wird in den Baugruppenkontext übertragen (Spike S12b). Normteile werden nur über ihre Einbaureferenzen angesprochen,
nie über Features der Vorlage (die sind Bauweg und können sich mit einer Vorlagenversion ändern).

Lage der Einbaureferenzen (3a, Achse = Modell-Y): ISO 4762 Kopf in y ∈ [0, k], Schaft y < 0, `EINBAU_EBENE` = Kopfunterseite;
ISO 4032 Körper y ∈ [0, m]; ISO 7089 Körper y ∈ [0, h], **neu `EINBAU_EBENE_2` bei y = h**; ISO 8734 Körper y ∈ [0, l],
`EINBAU_EBENE_1` bei y = 0, `EINBAU_EBENE_2` bei y = l. Der Skill `normteile` führt diese Tabelle.

### 4.4 Verknüpfungen

- `id`, `typ`, `a`, `b` und je nach Typ `ausrichtung`, `wert`, `drehung_sperren`.
- Typen: `deckungsgleich`, `konzentrisch`, `parallel`, `senkrecht`, `abstand` (`wert` in mm), `winkel` (`wert` in Grad).
- `ausrichtung: gleich | entgegengesetzt` ist Pflicht bei `deckungsgleich`, `parallel`, `abstand` und `winkel`; `validieren`
  meldet das Fehlen. Bei `konzentrisch` ist sie optional: Ohne Angabe wählt swki die Ausrichtung, die zur schon festgelegten
  Richtung der Komponente passt (Verfahren im Plan nach Spike S12c); mit Angabe gilt sie. „Nächstliegend“ als Vorgabe gibt
  es nicht, weil das Ergebnis von der Einfügelage abhinge.
- `drehung_sperren` (nur `konzentrisch`): Vorgabe `true`, wenn eine Seite ein Normteil ist, sonst `false`.
- `wert` ist bevorzugt ein Ausdruck über `parameter` (`"=H"`); feste Zahlen meldet `validieren` als Hinweis `feste_zahl`.
- Reihenfolge: wie in der Spec; eine vervielfältigte Verknüpfung steht mit allen Instanzen an ihrer Stelle
  (`v10.1, v10.2, v11.1, v11.2`).

### 4.5 `freiheitsgrade`, `parameter`, `eigenschaften`

- `freiheitsgrade: {<komponente|gruppe>: unterbestimmt}`, optional. Ohne Eintrag gilt jede Komponente als „voll bestimmt“.
  Zahlen gibt es erst in Stufe 4.
- `parameter` werden Gleichungen (globale Variablen) der Baugruppe; `wert` von Verknüpfungen wird per Gleichung an sie gebunden.
- `eigenschaften` werden wie beim Teil gesetzt (inklusive `Ersteller`, `Auftrag`). Kein `material`.

### 4.6 `pruefung`

- `huellquader` [X, Y, Z] der Baugruppe.
- `masse_pruefen` mit den Messpunkten des Teil-Formats plus `komponente` (inklusive `instanz: <zahl>` bei Bohrungen);
  `{punkt: [x, y, z]}` in Baugruppenkoordinaten.
- optional `masse: {soll, toleranz_prozent}`; ohne Angabe wird die Gesamtmasse nur gemessen und berichtet.
- Kollision, Bestimmtheit, Stückliste und Teilprüfungen laufen immer und brauchen keinen Eintrag.

## 5. Validieren

`swki validieren <baugruppe.yaml>` ohne SolidWorks, Ausgabe wie beim Teil (`gueltig`, `befunde`, `hinweise`):

1. Schema `schema/baugruppe.schema.json`.
2. Jede Teil-Spec wird mit den vorhandenen Prüfungen validiert; ihre Befunde und Hinweise tragen die Komponenten-ID.
3. Normteile: Schlüssel, Länge, Variante und Status über die vorhandene Auflösung (`NORMTEIL_UNBEKANNT`, `NORMLAENGE_UNGUELTIG`,
   `NORMVARIANTE_UNBEKANNT`, `NORMTEIL_GESPERRT` als Befunde); es wird nichts gebaut.
4. `je_position` auflösen; Paarungsregel (§4.2).
5. Jede Referenz: Komponente vorhanden; Feature vorhanden; bei `instanz` Feature vom Typ `normbohrung`/`bohrung` und Instanz ≤
   Anzahl der Positionen; `referenz`-ID in der Teil-Spec bzw. Einbaureferenz der Normvorlage.
6. Genau eine `fixiert`; `ausrichtung` wo Pflicht; `wert` bei `abstand`/`winkel`; jede Nicht-fixierte Komponente kommt in
   mindestens einer Verknüpfung vor.
7. **Passung** bei `konzentrisch` zwischen der `EINBAU_ACHSE` eines Normteils und einer Bohrungsachse:
   - ISO 4762 M*x*: `normbohrung` `zylinderschraube` M*x* oder `gewinde` M*x*, oder `bohrung` mit Ø > d.
   - ISO 8734 *d*: `normbohrung` `stift` *d*.
   - ISO 7089, ISO 4032 M*x*: `bohrung` mit Ø ≥ Innen-Ø, oder `normbohrung` der Größe M*x* (Durchgang).
   - Jede andere Kombination ist ein Befund mit Norm, Größe und Bohrung.
8. Hinweise: `nahe` in Referenzen, feste Zahlen in `wert`.

## 6. Freigabe

- `swki freigeben <baugruppe.yaml>` schreibt `freigabe.json` mit einer Prüfsumme über `art, name, parameter, eigenschaften,
  komponenten, freiheitsgrade, pruefung` der Baugruppe und die (bestehende) Prüfsumme jeder verwendeten Teil-Spec.
- Freigabe-Kopien `<spec>.freigegeben.yaml` entstehen für die Baugruppe und jede Teil-Spec; sie werden nie geändert.
- Normteile sind über `komponenten` (Schlüssel, Variante) geschützt; die Bibliotheksprüfsumme gehört nicht zur Freigabe
  (die Bibliothek ist ein Cache).
- Verknüpfungen sind Bauweg wie Features beim Teil: Claude darf Referenzen, Typen, Ausrichtung und Reihenfolge nachbessern.
  Abstands- und Winkelwerte, die Anforderungen sind, stehen als `parameter` in der Freigabe; die Lage wird über
  `pruefung.masse_pruefen` belegt.
- Weicht eine Prüfsumme ab, verweigert `swki bauen` mit `FREIGABE_VERALTET` und nennt Baugruppe bzw. Teil.

## 7. Bauen

`swki bauen <baugruppe.yaml> [--lauf n] [--verwerfen]`:

1. Freigabe prüfen (§6), dann Änderungserkennung (§8).
2. Lauf-Ordner `<arbeitsordner>/<auftrag>/lauf-<n>/` anlegen.
3. Je verwendeter Teil-Spec den vorhandenen Teil-Bau aufrufen und als `<auftrag>_<name>.sldprt` im Lauf-Ordner speichern. Ein
   Fehler bricht ab mit `TEIL_BAU` und Knoten `<komponente>/<feature-id>`.
4. Je verwendetem Normteil `swki normteil hole` (Cache oder Neubau unter Auftrag `NORMTEILE`) und die Datei als
   `<schluessel>.sldprt` in den Lauf-Ordner kopieren. Normteil-Fehler werden mit ihrem Code und der Komponenten-ID gemeldet.
5. Neue Baugruppe aus `vorlage_baugruppe`; `parameter` als Gleichungen; `eigenschaften`.
6. Komponenten einfügen: jede mit Ursprung auf dem Baugruppenursprung (den Versatz durch das Bounding-Box-Zentrum von
   `AddComponent5` herausrechnen bzw. die Transformation setzen, S12a). Die fixierte zuerst, fixieren; dann alle übrigen
   in Spec-Reihenfolge, Instanzen in Positionsreihenfolge. Fehler: `KOMPONENTE_FEHLER`.
7. Verknüpfungen in der aufgelösten Reihenfolge setzen. Nach jeder Verknüpfung Rebuild und Fehlerstatus prüfen; der erste
   Fehler bricht ab mit `VERKNUEPFUNG_FEHLER` (Knoten-ID wie `v10.2`, Schritt, SW-Meldung) bzw. `REFERENZ_NICHT_GEFUNDEN` /
   `REFERENZ_MEHRDEUTIG` mit Komponente.
8. `<auftrag>_<name>.sldasm` speichern; Protokoll schreiben: Phasenzeiten, Dateien, je Komponente Quelle (bei Normteilen
   Schlüssel und Bibliotheksprüfsumme), je Verknüpfung SW-Name, **SHA-256 je gespeicherter Datei** im Lauf-Ordner.

Der Lauf-Ordner ist in sich geschlossen: Die Baugruppe verweist nur auf Dateien darin. Die Bibliothek wird nur gelesen;
die Baugruppe schreibt nie dorthin. Protokoll, Prüfbericht und Prüfer-Urteil liegen wie bisher unter `protokolle/` im
Auftragsordner (`<spec>.lauf-<n>.<art>.json`).

## 8. Änderungserkennung (Teile und Baugruppen)

- `swki bauen` schreibt künftig für **jede** Spezifikation (auch Einzelteile) den SHA-256 jeder gespeicherten Datei ins Protokoll.
- Vor jedem `swki bauen` vergleicht swki die Dateien des letzten durchgebauten Laufs mit diesen Werten (ohne SolidWorks).
  Weicht eine Datei ab oder fehlt sie, verweigert `bauen` mit **`MANUELL_GEAENDERT`** und nennt die Dateien. Läufe ohne
  gespeicherte Prüfsummen (vor 3b gebaut) werden übersprungen.
- **`swki aenderungen <spec> [--lauf n]`** (mit SolidWorks) öffnet die geänderten Dateien, liest die globalen Variablen (bei
  Baugruppen auch die Verknüpfungswerte) und meldet je Datei die Differenz zur freigegebenen Spec (`parameter`, Teil-Parameter).
  Andere Änderungen meldet es als „Datei geändert, Parameter gleich“.
- Claude zeigt die Änderung und fragt den Nutzer:
  - **übernehmen:** Claude überträgt die Änderung in die Spec (Parameter direkt; andere Änderungen nach Beschreibung des
    Nutzers), dann `validieren` und neue Freigabe, danach `swki bauen --uebernommen` (erlaubt den Bau trotz der
    geänderten Dateien nur, wenn die Freigabe neuer als der verglichene Lauf ist, sonst `UEBERNAHME_OHNE_NEUE_FREIGABE`;
    das Protokoll vermerkt es unter `uebernommen`; schließt sich mit `--verwerfen` aus);
  - **verwerfen:** nur auf ausdrückliche Anweisung `swki bauen --verwerfen`; das Protokoll vermerkt es.
- `swki pruefen` und `swki aenderungen` öffnen Dateien nur und speichern nie (Test sichert das); sonst erzeugte die Prüfung
  selbst eine Änderung.
- Vollständige Rückführung beliebiger Geometrieänderungen in die Spec gibt es nicht.

## 9. Prüfen

`swki pruefen <baugruppe.yaml> --lauf n` öffnet die `.sldasm` und schreibt `pruefbericht.json` mit Screenshots:

1. **Verknüpfungen:** Rebuild fehlerfrei; jede Verknüpfung ohne Fehlerstatus; Anzahl = aufgelöste Verknüpfungen der Spec.
2. **Bestimmtheit:** `IComponent2.GetConstrainedStatus` je Komponente „voll bestimmt“ bzw. „unterbestimmt“, wo
   `freiheitsgrade` es erlaubt. Überbestimmt ist immer ein Mangel.
3. **Kollision:** `InterferenceDetectionManager` mit „Berührung ist keine Kollision“ (`TreatCoincidenceAsInterference = False`);
   je Überlappung Komponentenpaar und Volumen.
   - **Gewindepaarung:** Überlappung zwischen einer ISO-4762-Instanz und dem Eigenteil, auf dessen `normbohrung` `art: gewinde`
     sie konzentrisch verknüpft ist. swki misst die **Einschraublänge** (Eintrittsfläche der Gewindebohrung bis Schaftende entlang
     der Achse).
     - Mangel, wenn die Einschraublänge die Gewindetiefe oder die Bohrtiefe (zylindrischer Teil) überschreitet.
     - Sonst Vergleich des gemessenen Volumens mit dem Soll: Ring zwischen Nenn-Ø und Kernloch-Ø (`bohrungsnormen.yaml`) über die
       Einschraublänge, abzüglich der Endfase der Schraube aus der Vorlage. Toleranz legt der Plan nach Spike S12d fest
       (Vorschlag 1 %).
     - Die Einschraublänge steht im Bericht.
   - Jede andere Überlappung ist ein Mangel (Paar, Volumen).
4. **Stückliste:** Anzahl der Komponenten je Datei gegen die aufgelösten `komponenten`.
5. **Teilprüfung** je verwendeter Teil-Spec: die vorhandenen Code-Prüfungen im Teildokument des Laufs gegen die freigegebene
   Teil-Spec; Prüfungs-IDs mit Präfix (`unterteil: mass:…`). Normteile werden nicht erneut geprüft; ihre Bibliotheksprüfsumme
   steht im Bericht.
6. **`pruefung`:** Hüllquader, `masse_pruefen` im Baugruppenkontext, Gesamtmasse (Soll nur, wenn angegeben).
7. **Screenshots:** Iso, Vorne, Oben, Rechts der Baugruppe.

`swki pruefen` verweigert abgebrochene Läufe (`LAUF_ABGEBROCHEN`) wie bisher.

## 10. Prüfer, Schleife, Bericht

- **Prüfer-Agent** `pruefer`: `.claude/agents/pruefer.md` erhält eine Baugruppen-Checkliste: jede Komponente vorhanden und
  plausibel gelegen; Verbindungen vollständig (Kopf auf Auflage, Scheibe unter Kopf und Mutter, Mutter auf Scheibe, Stift
  eingesteckt); keine verdrehten oder spiegelverkehrten Teile; Einschraublängen fachlich ausreichend (z. B. ≥ 1·d in Stahl);
  jede Anforderung belegt. Eingabe: Eingabeordner, alle freigegebenen Specs (Baugruppe und Teile), Prüfbericht, Screenshots;
  keine Protokolle, keine Skripte. Mängel nennen Komponenten- (`deckelschraube.2`), Verknüpfungs- (`v11.1`) oder Teil-Knoten
  (`deckel/f4`). Urteilsform unverändert.
- **Schleife:** `swki status` wie bei Teilen (max. 1 + `max_nachbesserungen` Läufe, Abbruch ohne Fortschritt, Bauabbruch zählt
  nicht als Mängelzahl).
- **Bericht:** `swki bericht` wie bei Teilen, zusätzlich Stückliste, Normteile mit Schlüssel und Bibliotheksprüfsumme,
  Gewindepaarungen mit Einschraublänge, Teilprüfungen je Komponente.

## 11. Fehlerfälle

JSON mit `code`, Exit 1. Neu:

| Code | Wann | Inhalt der Meldung |
|---|---|---|
| `TEIL_BAU` | Bauabbruch in einem Eigenteil | Komponente, Knoten, Fehlercode und Meldung des Teil-Baus |
| `KOMPONENTE_FEHLER` | Einfügen einer Komponente gescheitert | Komponente, Datei |
| `VERKNUEPFUNG_FEHLER` | Verknüpfung nicht angelegt oder mit Fehlerstatus | Knoten-ID, Schritt, SW-Meldung |
| `REFERENZ_NICHT_GEFUNDEN` / `REFERENZ_MEHRDEUTIG` | wie beim Teil | zusätzlich Komponente |
| `MANUELL_GEAENDERT` | Änderungserkennung (§8) | Lauf, geänderte bzw. fehlende Dateien |

`FREIGABE_VERALTET` nennt zusätzlich die betroffene Spec. Normteil-Codes aus 3a werden mit der Komponenten-ID weitergereicht.

## 12. Folgen für die Normteile (3a)

- **ISO 7089:** neue Vorlagenversion mit `EINBAU_ACHSE`, `EINBAU_EBENE` (y = 0) und **`EINBAU_EBENE_2` (y = h)**, gemessen;
  neues Prüfer-Urteil.
- **ISO 8734:** neue Vorlagenversion: `EINBAU_EBENE_2` gegen +y mit Soll 0 gemessen (statt nur als Betrag) und `c` direkt
  gemessen; neues Prüfer-Urteil.
- ISO 4762 und ISO 4032 bleiben unverändert. Bibliotheksteile alter Vorlagenversionen werden beim nächsten `hole` neu gebaut
  (Prüfsumme).

## 13. Offene Technik (Spike S12 vor dem Bau)

Vor jedem neuen API-Aufruf `swki api methode` / `swki api enum` nachschlagen; Compiler-Code nur mit Aufrufen aus SW 2025.

- **S12a Einfügen:** `AddComponent5` und Transformation so setzen, dass der Ursprung der Komponente im Baugruppenursprung liegt;
  erste Komponente fixieren. Beleg per `Transform2`.
- **S12b Auswahl in der Komponente:** benannte Bezugsachse/-ebene per Name; Fläche und Bohrungszylinder einer Instanz im Teil
  finden und per `IComponent2.GetCorrespondingEntity` (o. ä.) in den Baugruppenkontext übertragen und auswählen.
- **S12c Verknüpfungen:** `AddMate5` (obsolet, in S6 erprobt) gegen `CreateMate` für die sechs Typen; `ausrichtung`
  gleich/entgegengesetzt bei Fläche/Fläche, Ebene/Fläche und Achse/Zylinder; `LockRotation`; Status je Komponente und
  Fehlerstatus je Verknüpfung lesen; Fall „Ebene + zwei konzentrische Bohrungen“ (überbestimmt gemeldet?).
- **S12d Kollision:** `IInterference` je Paar (Komponenten, Volumen) mit `TreatCoincidenceAsInterference = False`; Mutter auf
  Schaft und Stift in Stiftbohrung → 0; Gewindepaarung → Volumen gegen Ring-Soll.
- **S12e Rücklesen:** globale Variablen und Verknüpfungswerte aus gespeicherten Dateien lesen; Öffnen und Schließen ohne
  Speichern lässt den SHA-256 unverändert.
- **S12f Messen im Baugruppenkontext:** Abstand Fläche–Achse über zwei Komponenten.
- **S12g Speicher:** Private Bytes beim Bau einer Baugruppe mit etwa 15 Komponenten.

## 14. Tests

Ohne SolidWorks (pytest):

- Schema; Auflösung von `je_position` (IDs, Vervielfältigung, `instanz: je`, Paarungsregel).
- Referenzprüfung und Passung inklusive Fehlerfällen; Pflicht von `ausrichtung`; genau eine `fixiert`.
- Freigabe: Prüfsumme über Baugruppe und Teile; geänderte Teil-Spec → `FREIGABE_VERALTET` mit Teilname; geänderte Verknüpfung
  lässt die Freigabe gültig.
- Änderungserkennung: Hash im Protokoll, Verweigern, `--verwerfen`, alte Läufe ohne Hash; für Teile und Baugruppen.
- Soll der Gewindepaarung gegen eine Handrechnung; Stückliste; Bewertung mit Attrappen-Messwerten; Bauablauf mit Attrappe
  (Reihenfolge, Abbruch mit Knoten-ID).

Mit SolidWorks (einzeln, `tests\live_einzeln.py`):

- Je Verknüpfungstyp eine Minimalbaugruppe aus zwei Blöcken (inklusive `ausrichtung` und `drehung_sperren`).
- Referenz **Stehlager** in `tests/referenz/stehlager/` (Teil der Regressions-Suite).
- Negativfälle mit erwartetem Mangel bzw. Code: zu lange Deckelschraube; absichtliche Überlappung; unterbestimmte Komponente;
  manuelle Parameteränderung in Teil und Baugruppe (`MANUELL_GEAENDERT`, Differenz aus `swki aenderungen`).
- Neue Vorlagen ISO 7089 und ISO 8734: kleinste, mittlere, größte Größe.

## 15. Einbindung

- **Skill `baugruppe`** (neu): Auftrag anlegen, Teil-Specs (nach `konstruieren`) und Baugruppen-Spec schreiben, Normteile über
  `normteile`, validieren, eine Freigabe, bauen, prüfen, Prüfer, nachbessern, Bericht; Umgang mit `MANUELL_GEAENDERT`.
- **Skill `konstruieren`:** Verweis „Baugruppe → Skill `baugruppe`“ und der Schritt „manuelle Änderung erkannt“.
- **Skill `normteile`:** Tabelle der Einbaureferenzen mit Lage und Richtung (§4.3).
- **`.claude/agents/pruefer.md`:** Baugruppen-Checkliste.
- **`CLAUDE.md`:** Baugruppen-Regeln (Format, eine Freigabe, Normteile nur kopiert, Änderungserkennung).
- **Design-Dokument:** §4 Baugruppe auf dieses Format, §6 Baugruppen-Prüfung, §11 Zeile 3b.
- **Ergebnisse:** `docs/stufe3b/ergebnisse.md`.

## 16. Fertig, wenn

- Das Stehlager besteht auf SW 2025 innerhalb der Laufgrenze: Code-Prüfungen ohne Mangel und Prüfer-Urteil „bestanden“.
- Die Negativfälle (§14) liefern die erwarteten Mängel bzw. Codes.
- Die Änderungserkennung ist live für ein Teil und eine Baugruppe belegt.
- ISO 7089 und ISO 8734 haben neue Vorlagenversionen mit bestandenem Prüfer-Urteil.
- Buchse, Formplatte und Auswerferhalteplatte bestehen weiter; alle Unit-Tests grün; `swki api pruefe-code` ohne Befund.

## 17. Reihenfolge der Umsetzung

1. Spike S12.
2. Schema, Laden, `je_position`, Plausibilität, Passung (ohne SolidWorks).
3. Freigabe der Baugruppe.
4. Änderungserkennung (Teile und Baugruppen) und `swki aenderungen`.
5. Neue Vorlagen ISO 7089 und ISO 8734 mit Prüfer-Urteilen.
6. Baugruppenbau (Einfügen, Referenzen, Verknüpfungen) mit Live-Minimaltests.
7. Prüfung (Verknüpfungen, Bestimmtheit, Kollision und Gewindepaarung, Stückliste, Teilprüfung, Messen, Screenshots).
8. Referenz Stehlager mit Prüfer und Negativfällen.
9. Skills, `pruefer.md`, `CLAUDE.md`, Design §4/§6/§11, Ergebnisse.

## 18. Nicht in 3b

Bewegungen, treibende und mechanische Verknüpfungen, gezählte Freiheitsgrade (Stufe 4); Unterbaugruppen; Konfigurationen;
native SW-Komponentenmuster; Verbindungssatz-Makro (`verschraubung`); fremde Teile (`quelle: datei`); vollständige Rückführung
manueller Geometrieänderungen; kosmetisches Gewinde; Kaufteile von Herstellern; weitere Normen; Rechner B; die übrigen
3a-Kleinbefunde außer §12.
