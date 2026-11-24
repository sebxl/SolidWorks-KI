# Zeichnungsableitung (Stufe Z1: Einzelteile) – Design

Stand 16.11.2026. Grundlage: Recherche `docs/zeichnungsableitung/recherche.md` (Regeln mit Quelle und Belegstärke A/B/C,
Kapitelverweise „R-Kap. n“). Vorgaben des Nutzers vom 16.11.2026 sind als „Nutzer“ markiert, alles andere als
„Selbst entschieden“ (Nutzer: „Alle wie empfohlen“ für die vier Rückfragen, Vorschlagstabelle ohne Widerspruch).

## 1. Absicht

swki baut Teile aus freigegebenen Specs, liefert aber keine Fertigungszeichnung. Der Nutzer will, dass swki zu jedem
Einzelteil eine normgerechte, fertigungs- und prüfgerechte Zeichnung ableitet, die ein Prüfer mit klaren Vorgaben abnimmt
(Nutzer). Die Zeichnung soll so vollständig sein, dass ein Fertiger (Werkstatt oder Lohnfertiger) ohne Rückfrage und
ohne Rechnen fertigen und prüfen kann; das Modell (STEP) wird zusätzlich mitgegeben.

Toleranzen, Passungen und Rauheiten sind keine Zeichnungsfrage, sondern folgen aus der Funktion („Haben wir eine
Lauffläche für ein Lager? Wollen wir etwas verstiften?“, Nutzer). Sie gehören deshalb in die Teil-Spec und laufen durch
die normale Freigabe; Änderungen sperren den Bau wie bisher (Schutz nach Wirkung statt über Feature-IDs, Abschnitt 4.2).

**Ziele**
- `swki zeichnen <spec>` erzeugt aus einem gebauten, freigegebenen Teil eine SolidWorks-Zeichnung (SLDDRW) und ein PDF
  auf der Firmenvorlage.
- Funktionsangaben an Features (Lagersitz, Stiftbohrung, Gleitpassung …) liefern über eine Regeltabelle Passung,
  Rauheit sowie Form und Lage; Einzelwerte sind überschreibbar.
- `swki zeichnung pruefen <spec>` liest die Zeichnung über die API zurück und prüft sie gegen die freigegebene Kopie
  und den Regelkatalog; danach urteilt der Agent `zeichnungspruefer`.
- Teilearten Stufe Z1: Fräs-, Dreh-, Schleif- und Erodierteile (Nutzer).
- Dafür neue Feature-Typen `freistich` (DIN 509) und `zentrierbohrung` (ISO 6411) (Nutzer: Empfehlung A).

**Nicht-Ziele (Stufe Z1)**
- Baugruppenzeichnung, Positionsnummern, Stückliste: Stufe Z2 (R-Kap. 9, Fragen 27–30 dort).
- Blech-, Kant- und Schweißteile: später (Nutzer).
- Eigene Zeichnungsvorlage oder eigenes Schriftfeld: Die Firmenvorlage kommt vom Nutzer (Nutzer).
- DXF/DWG-Export, Bestandsdateien (fremde Zeichnungen), Zeichnungen im Schnellbau.

**Anti-Ziele**
- Eine Zeichnung, die „irgendwie bemaßt“ ist: Auto-Bemaßung mit Maßen an Skizzenpunkten, doppelten oder fehlenden
  Maßen, geschlossenen Ketten. Lieber eine Lücke melden als eine unbrauchbare Zeichnung abgeben.
- Toleranzen „sicherheitshalber“ eng: Jede Einzeltoleranz braucht eine Funktion oder eine ausdrückliche Vorgabe.
- Schwächere Freigabe: Funktions- und Toleranzangaben dürfen nach der Freigabe nicht unbemerkt geändert werden.
- Das Original anfassen oder in SolidWorks arbeiten, während der Nutzer dort arbeitet, ohne Absprache.

## 2. Entscheidungen

| Thema | Entscheidung | Herkunft |
|---|---|---|
| Teilearten Z1 | Fräs-, Dreh-, Schleif-, Erodierteile | Nutzer |
| Vorlage | Blattformate des Nutzers „A3 Quer / A4 / A4 Quer DIN EN ISO 7200“ (.slddrt, 17.11.2026); sie sind mit SW 2026 gespeichert und laden auf Rechner A (SW 2025) nicht. Entwicklung bis Z1.4 mit den mitgelieferten SW-2025-Formaten „a3/a4 - iso“ (Kopien im Arbeitsordner), Umstieg in Z1.5 auf dem Firmenrechner. Pfade in `config/rechner.yaml`; Schriftfeld über Eigenschaften | Nutzer (Formate) / Weg selbst entschieden |
| Allgemeintoleranz | Klasse m, nach ISO 2768-1 mit Ausgabejahr; kein „K“ | Nutzer (m) / Nutzer: Empfehlung A |
| Tolerierungsgrundsatz | ISO 8015; Hülle Ⓔ nur an Passmaßen aus der Funktion | Nutzer („Wie vorgeschlagen“) |
| Form und Lage | an Funktionsflächen ausdrücklich, aus der Regeltabelle bzw. Spec | Nutzer: Empfehlung A (Frage 4) |
| Funktion → Toleranz | Feld `funktion` am Feature + Regeltabelle `swki/wissen/funktionen.yaml`; Einzelwerte überschreibbar | Nutzer: Empfehlung A (Frage 1) |
| Fertigungsverfahren | `verfahren: fraesen \| drehen` je Teil, `bearbeitung: schleifen \| erodieren` je Feature | Nutzer: Empfehlung A (Frage 2) |
| Drehteil-Features | `freistich` (DIN 509), `zentrierbohrung` (ISO 6411) in diesem Paket | Nutzer: Empfehlung A (Frage 3) |
| Maße aus Modell oder neu | Maßplan aus der Spec ist der Hauptweg: je Merkmal genau ein Maß mit Bezug, Ansicht und Toleranz; gesetzt über Kantenauswahl, Modellmaße nur, wo sie genau dem Maßplan entsprechen (Abschnitt 6.2, nach Spike Z1.0) | Nutzer („je nach Fall“, 17.11.: Vorgehen ohne Widerspruch) / Regel selbst entschieden |
| Vollständigkeit | vollständig bemaßt, STEP wird mitgeliefert | selbst entschieden (R-Kap. 8: deutsche Praxis vs. Fictiv) |
| Prüfung | maschinell (Rücklesen) + Agent `zeichnungspruefer` mit Regelkatalog; A/B-Regeln hart, C-Regeln Hinweis | Nutzer (Prüfer mit klaren Vorgaben) / Härte selbst entschieden |
| Ausgabe | SLDDRW + PDF + STEP im Laufordner | selbst entschieden |
| Bemaßungsstil | Fase „0,5 × 45°“; Maßlinienabstände und Symbole aus der Normdatei der Vorlage; Hilfsmaße in Klammern; Prüfmaße nur auf Anforderung | selbst entschieden |
| Sammelangaben | Rauheit Ra 3,2 (Fräsen/Drehen), Kanten ISO 13715 „−0,1 … −0,3“; Oberflächennorm nach Vorlage (ISO 21920 ab SW 2025 SP1) | selbst entschieden, in `config/standard.yaml` |
| Freigabe der Zeichnung | Zeichnung ist Bauweg; Feld „Freigegeben“ im Schriftfeld bleibt leer, bis der Nutzer abnimmt | selbst entschieden |
| Service Pack | jede SP-abhängige Methode mit Ersatzweg bis SW 2025 FCS | selbst entschieden (R-Kap. 10) |
| Rechner | Entwicklung, Spike und Regression auf Rechner A (SW 2025, Student); Teile und Zeichnungen für die Fertigung nur auf der Vollversion (Firmenrechner SW 2026). Bis zu dessen Inbetriebnahme liefert Z1 keine Fertigungszeichnung. Die Firmenvorlage ist vermutlich in SW 2026 gespeichert, Z1.5 hängt dann am Firmenrechner (`docs/bestandsdateien/inbetriebnahme-firmenrechner.md`) | Nutzer: Empfehlung A |
| Behandlung, Halbzeug | neue Anforderungsfelder `behandlung` (Härte, Einsatzhärtetiefe, Beschichtung) und `halbzeug` (Abschnitt 4.1); rohe Halbzeugflächen „wie Halbzeug“ statt Sammelangabe Ra 3,2 | Nutzer: Empfehlung A |
| Modellmaß | Modell im Nennmaß (wie heute); Vermerk „Maßgebend ist die Zeichnung“ auf jeder Zeichnung | Nutzer: Empfehlung A |
| Abnahme | `swki zeichnung abnehmen <spec>` nach ausdrücklichem OK des Nutzers im Chat: trägt „Freigegeben“ (Name, Datum) ein, aktualisiert die SHA-256, legt das PDF unveränderlich ab. Revisionsindex erst mit der Firmenvorlage (Schema ist Firmensache) | selbst entschieden (Builder-Check) |
| Maßtoleranzen ohne Feature | Top-Level `toleranzen` je Parametername (Achsabstand, Gesamtlänge); das Maß, das der Parameter treibt, trägt sie | selbst entschieden (Builder-Check) |
| Teile aus Baugruppen | gehören zu Z1; Quelle ist der letzte bestandene Lauf des Auftrags; Freigabe ist die der Baugruppe | selbst entschieden (Builder-Check) |

**Prüfpunkte an der Firmenvorlage, sobald sie da ist** (Nutzer bzw. Organisator 16.11.):
- Steht dort „DIN 7167“ (Hüllprinzip ohne Eintrag) statt „ISO 8015“ → Widerspruch zum Nutzerentscheid melden.
- Steht dort „ISO 2768-mK“ → melden: ISO 2768-2 ist seit 2021 zurückgezogen, ein undatiertes „K“ verweist auf ISO 22081
  und legt dann keine Form-/Lage-Allgemeintoleranz fest (R-Kap. 7).
- Oberflächensymbol nach ISO 1302 oder ISO 21920? Maßstab und Projektionssymbol im oder neben dem Schriftfeld?
- Welche Felder die Vorlage über `$PRP`/`$PRPSHEET` liest und wie die Eigenschaften heißen (Abschnitt 7).

## 3. Ansätze

| Ansatz | Kern | Bewertung |
|---|---|---|
| **A – Zeichnung aus der Teil-Spec in SolidWorks (gewählt)** | Funktions- und Toleranzangaben in der Teil-Spec (Anforderung), Block `zeichnung:` (Bauweg); `swki zeichnen` erzeugt die Zeichnung über die API aus dem gebauten Teil, übernimmt protokollierte Modellmaße und setzt fehlende neu; Prüfung durch Rücklesen gegen die freigegebene Kopie | nutzt Bemaßungsbezug, Maßprotokoll (`Kontext.mass`), Freigabe und Prüfer-Muster; eine Quelle der Wahrheit |
| B – eigene Zeichnungs-Spec je Teil | `zeichnung.yaml` neben der Teil-Spec mit Ansichten, Maßen, Toleranzen | zweite Freigabe, Toleranz getrennt vom Feature, Doppelpflege; verworfen |
| C – AutoDimension / DimXpert | Bemaßung durch SolidWorks-Automatik | nicht deterministisch, DimXpert nicht im API-Index (R-Kap. 10), nicht gegen die Spec prüfbar; höchstens Ergänzung |
| D – Zeichnung ohne SolidWorks | aus Schnellbau/B-Rep als DXF/PDF | keine SLDDRW, SolidWorks bleibt verbindlich; verworfen |

Gewählt: A (Nutzer hat das Wie übergeben; selbst entschieden).

## 4. Spec-Erweiterung (Anforderungen)

### 4.1 Neue Felder

Teil-Spec (`schema/teil.schema.json`):

```yaml
verfahren: fraesen            # fraesen | drehen; Grundverfahren des Teils (Pflicht, sobald `zeichnung` erzeugt wird)
features:
  - id: f3
    typ: normbohrung
    art: stift
    groesse: "8"
    funktion: stiftbohrung     # Schlüssel aus swki/wissen/funktionen.yaml
    # Überschreibungen, nur wenn die Tabelle nicht passt:
    passung: H7               # ISO-286-Toleranzklasse am Nennmaß
    toleranz: {oben: 0.02, unten: 0}   # alternativ zu passung, in mm
    rauheit: {Ra: 0.8}        # Kenngröße und Wert in µm
    form_lage: [{art: rechtwinkligkeit, wert: 0.02, bezug: [A]}]
    huelle: true              # Ⓔ; Vorgabe aus der Tabelle (Passmaße true)
    bearbeitung: schleifen    # schleifen | erodieren; fehlt = Grundverfahren
```

- `funktion`, `passung`, `toleranz`, `rauheit`, `form_lage`, `huelle`, `bearbeitung` sind an Features erlaubt, die eine
  Fläche oder ein Maß tragen (`bohrung`, `normbohrung`, `extrusion`, `schnitt`, `rotation`, `freistich`, `verrundung`,
  `fase`). Welche Fläche eines Features gemeint ist, sagt bei mehrdeutigen Features ein Flächenanker
  (`flaeche: {feature, flaeche}` wie heute). Der genaue Zuschnitt je Feature-Typ ist dem Bauer überlassen.
- `bezuege`: Bezugsflächen A, B, C des Teils auf Top-Level, als Flächenanker:
  `bezuege: {A: {feature: f1, flaeche: -z}, B: {...}, C: {...}}`. Pflicht, sobald eine Form-/Lagetoleranz einen Bezug
  nennt. Vorschlag aus `validieren`: Anlageflächen, die in Baugruppen-Verknüpfungen `deckungsgleich` sind (R-Kap. 8, B).
- Bohrbilder: Positionstoleranz mit theoretisch genauen Maßen nur, wenn `funktion` es verlangt (z. B. `stiftbild`);
  sonst ±-Allgemeintoleranz (selbst entschieden; R-Kap. 4/7, Frage 13).
- `behandlung` (Top-Level, Liste) für Wärme- und Oberflächenbehandlung, z. B.
  `[{art: einsatzhaerten, haerte: {wert: 60, plus: 2, minus: 2, verfahren: HRC}, tiefe: {art: CHD, wert: 0.8, plus: 0.4,
  grenzhaerte: "550 HV1"}, zustand: fertigteil}, {art: bruenieren}]`. Auf der Zeichnung als Notiz nahe dem Schriftfeld,
  z. B. „einsatzgehärtet und angelassen (60 ± 2) HRC, CHD = (0,8 +0,4/0) mm“. Schreibweise nach DIN ISO 15787:2018
  (Nachrecherche `docs/zeichnungsableitung/haerteangabe.md`; „58+4 HRC“ ist der alte Stil nach DIN 6773). Gilt eine
  Behandlung nur für einzelne Flächen, trägt das Feature `behandlung: <art oder id>` (selbst entschieden). Offen:
  Härtestil (ISO 15787:2016 oder DIN 6773) als Hausregel, Angabe „darf nicht behandelt werden“.
- `halbzeug` (Top-Level), z. B. `{art: flach, norm: "EN 10058", masse: "50 x 10"}`, optional `toleranz`, `zustand`;
  der Werkstoff kommt aus `material`. Flächen des Teils, die kein Feature
  bearbeitet, bleiben Halbzeugoberfläche; die Zeichnung kennzeichnet sie „wie Halbzeug“ (Sammelangabe in Klammern bzw.
  Notiz, genaue Darstellung im Spike/mit der Vorlage). Ohne `halbzeug` gilt die Sammelangabe Ra 3,2 für alle Flächen.
  Welche Flächen roh bleiben, ermittelt swki aus dem Hüllquader (Fläche liegt in der Halbzeug-Außenkontur und ist
  keinem Feature zugeordnet); der Weg ist dem Bauer überlassen.
- `toleranzen` (Top-Level) für Maße, die nicht an einem einzelnen Feature hängen, je Parametername:
  `toleranzen: {A_achse: {oben: 0.02, unten: -0.02}, L: {passung: h11}}`. Über das Maßprotokoll (`roh: "=A_achse"`)
  ist bekannt, welches Maß der Parameter treibt; dieses Maß trägt die Toleranz in der Zeichnung. Treibt ein Parameter
  mehrere Maße, gilt die Toleranz für alle (Hinweis in `validieren`).

### 4.2 Freigabe

Die Prüfsumme deckt heute nur Top-Level-Felder ab (`swki/spec/freigabe.py`, `PRUEF_FELDER`); Features sind Bauweg und
werden beim Nachbessern umbenannt, zusammengefasst oder zwischen `positionen` und Muster gewechselt. Deshalb
(selbst entschieden, Builder-Check; Vorbild: Normbohrungs-Größen und Bohrbilder werden heute schon „nach Wirkung“ gegen
die freigegebene Kopie geprüft, nicht über die Prüfsumme):
- `verfahren`, `toleranzen`, `behandlung` und `halbzeug` kommen in `PRUEF_FELDER`, aber nur in die Summe, wenn vorhanden (wie `bewegungen` bei
  Baugruppen), damit bestehende Freigaben gültig bleiben. `swki bauen` verweigert bei Änderung mit `FREIGABE_VERALTET`.
- Die Feldgruppe am Feature (`funktion`, `passung`, `toleranz`, `rauheit`, `form_lage`, `huelle`, `bearbeitung`) und
  `bezuege` sind **nicht** in der Prüfsumme, weil sie an Feature-IDs hängen. Sie werden nach Wirkung geschützt:
  `swki pruefen` und `swki zeichnung pruefen` lösen beide Specs (Arbeitsdatei und freigegebene Kopie) zu einer Liste
  von Merkmalen auf (Geometrie: Art, Ø/Breite, Lage im Teil, Fläche; Anforderung: aufgelöste Passung, Abmaße, Ra,
  Form/Lage, Ⓔ, Bearbeitung, Bezugsbuchstabe) und vergleichen sie ohne Rücksicht auf Feature-IDs. Fehlt eine
  Anforderung oder ist sie anders, meldet die Prüfung `ANFORDERUNG_GEAENDERT` (Mangel, kein Nachbessern im Bauweg).
- Sperre vor dem Bau: `swki validieren` und `swki bauen` vergleichen schon ohne Modell die Mehrfachmenge der Tupel
  (Feature-Art, Nenngröße wie Ø oder Gewindegröße, Anforderungsfelder wie in der Spec geschrieben, Anzahl der Instanzen
  über Positionen, Muster und Spiegelungen) beider Specs; weicht sie ab, verweigert `swki bauen` mit `FREIGABE_VERALTET`
  wie bei Top-Level-Anforderungen (umgesetzt über die Prüfsumme). Die Tupel enthalten die Felder roh, nicht aufgelöst: Die
  Tabelle gilt wie eine Norm-Tabelle, ihr Stand liegt aufgelöst in `freigabe.json` (jeder Freigabeweg). Die Lage im Teil
  prüft erst `swki pruefen` am Modell (Lage ist auch heute Bauweg plus Messung).
- Die Regeltabelle `funktionen.yaml` gilt wie eine Norm-Tabelle: Ihr Inhalt zum Zeitpunkt der Freigabe wird mit
  aufgelöst und abgelegt; geprüft wird gegen die aufgelösten Werte der freigegebenen Kopie. Wie die Auflösung
  gespeichert wird (in `freigabe.json` oder als eigene Datei), ist dem Bauer überlassen.

### 4.3 Regeltabelle `swki/wissen/funktionen.yaml`

Je Funktion: Passung (Bohrung/Welle), Ⓔ, Ra, Form/Lage, Bearbeitung-Hinweis, Quelle und Belegstärke. Erstbefüllung aus
der Recherche (R-Kap. 7), vom Nutzer vor der ersten Freigabe eines Teils mit Funktion zu bestätigen (selbst entschieden):

| Funktion | Passung | Ra (µm) | Form/Lage | Beleg |
|---|---|---|---|---|
| `stiftbohrung` (Zylinderstift m6) | H7, Ⓔ | 0,8 | – | H7 C; Ra C |
| `lagersitz_welle` / `lagersitz_gehaeuse` | k6 bzw. H7 (Umfangslast Außenring J7), Ⓔ | 0,8 / 1,6 | Rundheit IT3–IT4 / IT4–IT5 | IT6/IT7, Rundheit, Ra B; k6 C |
| `gleitpassung` | H7/g6, Ⓔ | 0,8 | – | Passung A; Ra C |
| `festsitz` | H7/p6 (H7/r6 ohne Verdrehsicherung) | 0,8 | – | Passung A/B; Ra C |
| `uebergang` | H7/k6 bzw. H7/m6 | 1,6 | – | Passung A/B; Ra C |
| `dichtflaeche_rwdr` | h11 (C) | 0,2–0,8 drallfrei | – | B |
| `anlage` | – | 1,6 | Ebenheit (Wert C) | C |

Werte mit C werden in der Tabelle als `beleg: C` geführt; `validieren` meldet sie als Hinweis, bis der Nutzer sie
bestätigt. Ergänzungen nur mit Quelle (≥ 2 für A) wie bei anderen Wissenstabellen.

### 4.4 Neue Feature-Typen

- **`freistich`** (DIN 509, Formen E und F): an einem Absatz eines Drehteils, Größe nur aus einer Tabelle
  `swki/wissen/freistiche.yaml` (Maße r, t1, f, g je Form und Größe; nur mit ≥ 2 Quellen, Muster `bohrungsnormen.yaml`).
  Im Modell ein Rotationsschnitt; in der Zeichnung Bezeichnung „DIN 509 – F 0,6 × 0,3“ an einer Einzelheit, nicht
  ausbemaßt (R-Kap. 8, A). Spec-Felder: `form`, `groesse`, `kante` (Kantenanker an Absatz), optional `funktion`.
- **`zentrierbohrung`** (ISO 6411 / DIN ISO 6411): an einer Stirnfläche; `form` (A, B, R), `groesse`, `verbleibt`
  (am Teil zulässig / erforderlich / nicht zulässig). In der Zeichnung Symbol und Bezeichnung nach ISO 6411; im Modell
  nur, wenn `modell: true` (Vorgabe false, weil ISO 6411 eine vereinfachte Darstellung ist; selbst entschieden).
- Beide über den Skill `compiler-erweitern` (Test zuerst, Regressions-Suite). Schnellbau: `freistich` als
  Differenzkörper oder `SCHNELLBAU_NICHT_UNTERSTUETZT` (Bauer entscheidet nach Aufwand), `zentrierbohrung` ohne Modell
  braucht nichts.

### 4.5 Verfahren und Bearbeitung in `validieren`

- `bearbeitung: erodieren`: Modellierregel 8 (Innenradius R ≥ Tiefe/5) gilt für diese Innenecken nicht; scharfe Ecken
  erlaubt (Drahterodieren: Hinweis auf Mindestradius aus Draht-Ø, Wert C, nur Hinweis).
- `bearbeitung: schleifen` an einem Absatz eines Drehteils ohne `freistich` → Hinweis `fertigung`.
- `verfahren: drehen`: Modellierregel 8 entfällt für Rotationskonturen; Durchmesser werden als Ø bemaßt.
- Rauheit < Ra 0,8 ohne `bearbeitung: schleifen` → Hinweis (Verfahren passt nicht zur Rauheit; Grenze C).
- Neue Hinweise unter der vorhandenen `art: fertigung`.

## 5. Zeichnung erzeugen (`swki zeichnen`)

Quelle ist das Teil aus dem letzten bestandenen Lauf des Auftrags, auch in Baugruppen-Aufträgen (dann gilt die
Baugruppen-Freigabe). Weil `MarkedForDrawing` beim Bau gesetzt wird (Abschnitt 6.2), werden Teile, die vor Z1 gebaut
wurden, einmal neu gebaut; nachträgliches Setzen würde die Teildatei ändern (SHA-256, `MANUELL_GEAENDERT`, keine
Wiederverwendung). Der Spike prüft, ob es ohne Teiländerung geht (alle Modellmaße einfügen, nicht benötigte in der
Zeichnung ausblenden); dann entfällt der Neubau.

Ablauf (nach `swki bauen` und bestandener Teilprüfung; in `swki durchlauf` als Schritt `--zeichnung`):

1. Vorlage aus `config/rechner.yaml` laden (`zeichnung: {vorlage, blattformat, normdatei}`); fehlt sie,
   `ZEICHNUNG_VORLAGE_FEHLT` (Spike und Tests: ISO-Vorlage von SolidWorks).
2. Eigenschaften setzen (Abschnitt 7).
3. Ansichten wählen (Abschnitt 6.1), Blattformat und Maßstab aus der Vorzugsreihe bestimmen.
4. Maße einfügen (Abschnitt 6.2), Toleranzen, Passungen, Ⓔ, Rauheit, Form/Lage, Bezugsdreiecke aus der aufgelösten
   Spec anbringen.
5. Sammelangaben (Allgemeintoleranz, ISO 8015, Rauheit, Kanten ISO 13715, „Maßgebend ist die Zeichnung“, Behandlung,
   Halbzeug) als Notiz bzw. Vorlagenfeld.
6. Anordnen (`AlignDimensions`), neu aufbauen, speichern als `<teil>.SLDDRW` im Laufordner, PDF und STEP exportieren.

Der Block `zeichnung:` in der Spec ist Bauweg (nicht in der Prüfsumme) und überschreibt nur, wenn nötig:
`format`, `massstab`, `ansichten` (Liste mit Richtung und Art: `ansicht | schnitt | einzelheit | abbruch`),
`masse` (je Spec-Pfad oder Feature: `quelle: modell | neu`, `bezug`). Fehlt der Block, entscheidet swki allein.

## 6. Ansichten und Maße

### 6.1 Ansichten (R-Kap. 3)

- Projektionsmethode 1; Hauptansicht nach Fertigungslage: Drehteile mit liegender Achse, Frästeile mit der
  Hauptbearbeitungsseite (die meisten Features) vorn (selbst entschieden, R-Kap. 3 B).
- Ansichten nach Maßbedarf (Nutzer 17.11.2026: „meist 3 oder 4, je nach Bauteil“): Jedes Maß des Maßplans braucht eine
  Ansicht, in der es in wahrer Größe darstellbar ist; keine Ansicht trägt mehr als `max_masse_je_ansicht` Maße
  (`config/standard.yaml`, Vorgabe 12, selbst entschieden). Ein Maß ohne passende Ansicht oder eine volle Ansicht führt
  zu einer weiteren Ansicht; eine Ansicht ohne eigenes Maß entfällt (außer der Hauptansicht).
- Schnitt, wenn Innenkonturen sonst nur verdeckt sichtbar wären (Bohrungsgrund, Freistich, Innennut); Drehteile
  mit Halbschnitt oder Vollschnitt; keine verdeckten Kanten in Maßansichten.
- Einzelheit für Freistich und Merkmale unter einer Mindestgröße (Schwelle dem Bauer überlassen) mit Vorzugsmaßstab.
- Abbruch bei Länge/Durchmesser über einer Schwelle (dem Bauer überlassen).

### 6.2 Maße: Maßplan aus der Spec

Spike Z1.0 (`docs/zeichnungsableitung/spike-z1.md`) hat gezeigt: Die Modellmaße roh sind unbrauchbar. Sie spiegeln den
Skizzenaufbau (Mittellinien, Fasenwinkel, Hilfsmaße), landen in jeder Ansicht doppelt und überlappen. Deshalb rechnet
swki die Maße der Zeichnung aus der Spec (selbst entschieden 17.11., Nutzer: „je nach Fall“):

- **Maßplan** (`swki/zeichnung/massplan.py`, ohne SolidWorks testbar): Liste von Maßen
  `{merkmal, art (laenge|durchmesser|radius|winkel|tiefe|lage), richtung, bezug, wert, toleranz, ansicht, quelle}`.
  - Je Merkmal genau ein Maß; je Richtung ein Bezug (Bezugsbemaßung, keine geschlossenen Ketten; R-Kap. 4/8 A).
  - Lage aus `bezug`/`bezuege` der Spec, Größe aus dem Feature (Ø, Breite, Tiefe, Radius), Toleranz aus der
    aufgelösten Funktion bzw. `toleranzen`.
  - Drehteile: Ø statt Radius, Längen von einer Bezugsplanfläche je Richtung.
  - Hilfsmaß in Klammern, wenn ein Gesamtmaß sich aus anderen ergibt.
  - Nicht bemaßen: Normbohrungs-Details (Bohrungsangabe), Freistich/Zentrierbohrung (Bezeichnung), Fasen 0,5 × 45° an
    Bohrungen (Bohrungsangabe bzw. Sammelangabe).
  - Bohrbilder: Reihen mit Muster „n× Teilung (= Gesamt)“, Lochkreise „n× Ø … auf TK Ø …“; Koordinatentabelle ab einer
    Lochzahl, die dem Bauer überlassen ist.
- **Ansicht je Maß:** die Ansicht, in der das Merkmal in wahrer Größe und sichtbar (nicht verdeckt) erscheint; bei
  mehreren die Hauptansicht, dann die mit den meisten Maßen derselben Richtung (Maße gruppieren).
- **Setzen:** über Kantenauswahl (`GetVisibleEntities2` + Geometrie in Modellkoordinaten + `AddDimension2`, im Spike
  erprobt). Modellmaße (`InsertModelAnnotations4` mit `HiddenFeatureDims=True`) nur, wo ein protokolliertes Maß
  (`Kontext.mass`) genau einem Maßplan-Eintrag entspricht und in dessen Ansicht liegt; alle anderen eingefügten
  Modellmaße werden in der Zeichnung gelöscht (Teildatei bleibt unverändert, Spike Frage 5). Ein Neubau alter Teile ist
  damit nicht nötig.
- **Anordnen:** eigener Schritt (`swki/zeichnung/anordnung.py`): Maßlinien mit Abstand zur Kontur und untereinander
  (Werte aus der Normdatei bzw. Hausregel, R-Kap. 4: 10 mm / 7 mm, Widerspruch 5 mm), parallele Maße gestaffelt,
  kleinere innen; keine Überlappung (Hüllrechtecke); `AlignDimensions` nur als Ergänzung.
- **Bohrungsangaben:** `InsertModelAnnotations` liefert keine (Spike), `AddHoleCallout2` braucht einen Dialog. Folge-
  Spike in Z1.3 Stufe 3: Bohrungstabelle, Notiz mit Text aus der Spec samt Hinweislinie, oder Bohrungsassistent-Maße.
- Der Maßplan liegt im Laufordner als JSON; die Prüfung (Abschnitt 8) läuft gegen ihn und gegen die Spec.

## 7. Schriftfeld und Eigenschaften

- Teil-Eigenschaften (`eigenschaften` der Spec, Material, Benennung) bleiben im Teil; Zeichnungs-Eigenschaften
  (Zeichnungsnummer, Ersteller, Datum, Maßstab, Blatt, Revision) setzt `swki zeichnen` an der Zeichnung.
- Die Zuordnung Vorlagenfeld → Eigenschaft steht in `config/standard.yaml` (`zeichnung.schriftfeld`), weil die Namen
  erst mit der Firmenvorlage bekannt sind. Pflichtfelder nach ISO 7200 (acht Felder, R-Kap. 2, A) werden geprüft;
  „Freigegeben“ bleibt leer bis zur Abnahme durch den Nutzer.
- Zeichnungsnummer = Sachnummer des Teils aus `eigenschaften` (Schlüssel aus der Vorlage); fehlt sie,
  `ZEICHNUNG_SACHNUMMER_FEHLT` (selbst entschieden; Nummernschema ist Firmensache).

## 8. Zeichnung prüfen

### 8.1 Maschinell (`swki zeichnung pruefen`)

Liest die Zeichnung über die API zurück (Ansichten, Display-Dimensions mit Wert, Toleranz, Passung, Klammer, Ⓔ,
angehängten Entitäten; Annotationen; Blatt- und Dokumenteigenschaften) und schreibt
`protokolle/<spec>.lauf-<n>.zeichnung.pruefbericht.json`. Prüfungen (Kurzname, Herkunft):

| Prüfung | Inhalt | Herkunft |
|---|---|---|
| `vollstaendig` | jedes Merkmal des Maßplans ist genau einmal bemaßt; jedes Spec-Maß der freigegebenen Kopie findet sich mit gleichem Wert | R-Kap. 4/8 A |
| `ueberbestimmt` | je Richtung kein geschlossener Maßzyklus (Maßgraph), Ausnahme Hilfsmaß in Klammern | R-Kap. 4/8 A |
| `toleranzen` | Passung, Abmaße, Ⓔ, Rauheit, Form/Lage und Bezüge wie in der aufgelösten Spec; Ⓔ nur an Passmaßen | Nutzer (ISO 8015), R-Kap. 7 |
| `sammelangaben` | Allgemeintoleranz mit Jahr und Klasse m, ISO 8015, Rauheit, Kanten, „Maßgebend ist die Zeichnung“, Behandlung und Halbzeug wie in der Spec vorhanden; kein „ISO 2768-…K“, kein „DIN 7167“ | Nutzer, R-Kap. 7 A |
| `schriftfeld` | acht Pflichtfelder gefüllt (außer „Freigegeben“), Maßstab aus der Vorzugsreihe | R-Kap. 2 A |
| `ansichten` | keine Maße an verdeckten Kanten; Schnittbezeichnung vorhanden; Einzelheit mit Maßstab | R-Kap. 3/4 A/B |
| `lesbarkeit` | keine überlappenden Maße/Annotationen (Hüllrechtecke), Maße außerhalb der Kontur wo möglich | R-Kap. 4 B (Hinweis) |
| `gewinde` | Gewinde mit Bezeichnung (z. B. M6) und Gewindetiefe; Bohrtiefe getrennt | R-Kap. 5 B |
| `drehteil` | Durchmesser als Ø, Freistich- und Zentrierbohrungsbezeichnung | R-Kap. 8 A/B |

Regeln der Stufe C laufen nur als Hinweis (`ok: null` mit Begründung). Die Regeln stehen als Daten in
`swki/wissen/zeichnungsregeln.yaml` (ID, Text, Quelle, Beleg, hart/Hinweis), damit Prüfer und Code dieselbe Liste lesen.

### 8.2 Agent `zeichnungspruefer`

Neuer Agent unter `.claude/agents/zeichnungspruefer.md` nach dem Muster `pruefer`: bekommt Eingabe, freigegebene Spec,
Zeichnungs-Prüfbericht, PDF bzw. PNG je Blatt und den Regelkatalog; sieht keine Bauprotokolle. Checkliste: Kann ein
Fertiger nach dieser Zeichnung ohne Rückfrage fertigen und prüfen? Fehlt ein Maß, muss gerechnet werden, ist eine
Toleranz ohne Funktion, ist die Darstellung missverständlich? Urteil `bestanden` oder Mängelliste mit Merkmal und
Regel-ID. Ablage wie beim Teil: `protokolle/<spec>.lauf-<n>.zeichnungspruefer.json`.

### 8.3 Nachbessern und Handänderungen

- Nachbessern nur im Bauweg (`zeichnung:`-Block, Ansichten, Maßquelle); Anforderungen nur über neue Freigabe.
- `swki zeichnen` speichert SHA-256 der SLDDRW im Laufprotokoll; eine von Hand geänderte Zeichnung meldet
  `swki aenderungen` als `MANUELL_GEAENDERT` (Zeichnung), Ablauf wie bei Teilen (übernehmen/verwerfen auf Anweisung).
- Abnahme: nach Prüfer „bestanden“ und Bericht an den Nutzer trägt `swki zeichnung abnehmen` nach seinem OK im Chat
  „Freigegeben“ ein und aktualisiert die SHA-256 (die Abnahme ist damit keine Handänderung). Eine spätere neue
  Zeichnung desselben Teils lässt das abgenommene PDF unverändert liegen.

## 9. Etappen

| Etappe | Inhalt | Ergebnis |
|---|---|---|
| Z1.0 Spike | live, frisches SolidWorks, nur nach OK des Nutzers: Zeichnung aus Vorlage, Ansichten (Erst-, Schnitt-, Detailansicht), `MarkedForDrawing` + `InsertModelAnnotations3/4` (inkl. Bohrungsangabe ohne Dialog?), Maß über Kantenauswahl setzen, Passung/Ⓔ/Oberflächensymbol setzen, alles zurücklesen; SP-Stand von Rechner A feststellen | erledigt 17.11.: `docs/zeichnungsableitung/spike-z1.md`; Folge: Abschnitt 6.2 Maßplan |
| Z1.1 Spec | Nachrecherche ISO 15787 (Härteangabe); Schema (`verfahren`, `bezuege`, `toleranzen`, `behandlung`, `halbzeug`, Feldgruppe Funktion), Prüfsumme und Sperre nach Wirkung, `funktionen.yaml`, `validieren`-Hinweise | Unit-Tests ohne SolidWorks |
| Z1.2 Drehteil-Features | `freistich`, `zentrierbohrung` über `compiler-erweitern`, Tabelle DIN 509 mit Quellen | Referenzteil Drehteil |
| Z1.3 Zeichnen | fünf Stufen an Buchse und Spannplatte, jede endet mit einem PDF zur Durchsicht durch den Nutzer: **1** Blatt und Ansichten (Format, Maßstab, Lage ohne Überlappung, Mittellinien, Schnitt/Einzelheit an sinnvoller Stelle, Schriftfeld über Eigenschaften), **2** Maßplan und Anordnung, **3** Bohrungsangaben, Gewinde (Folge-Spike), **4** Toleranzen, Passungen, Ⓔ, Rauheit, Sammelangaben, **5** Übergabe an Z1.4 | Zeichnungen der Referenzteile, je Stufe ein PDF |
| Z1.4 Prüfen | `swki zeichnung pruefen`, `zeichnungsregeln.yaml`, Agent `zeichnungspruefer`, `durchlauf --zeichnung` | Regression mit Negativfällen |
| Z1.5 Firmenvorlage | Blattformate des Nutzers (SW 2026) auf dem Firmenrechner einbinden, Prüfpunkte aus Abschnitt 2, Schriftfeld-Zuordnung ($PRP-Namen der Formate) | wartet auf den Firmenrechner (Formate liegen vor) |

Z1.1 und Z1.2 brauchen kein SolidWorks bzw. nur Live-Tests der Handler; Z1.3/Z1.4 laufen zunächst auf der ISO-Vorlage.

## 10. Tests und Referenzen

- Referenzteile `tests/referenz/zeichnung/`: ein Frästeil mit Stiftbohrungen, Gewinden und Tasche (z. B. aus der
  Spannplatte `tests/referenz/stil/` abgeleitet, mit `funktion` und `bezuege`), ein Drehteil (Buchse mit Freistich,
  Zentrierbohrung, Lagersitz), ein Teil mit `bearbeitung: schleifen` und eines mit `erodieren`.
- Negativfälle, die `swki zeichnung pruefen` finden muss: fehlendes Maß, doppeltes Maß, geschlossene Kette, falsche
  Passung, Ⓔ an einem Nicht-Passmaß, fehlendes Pflichtfeld, „ISO 2768-mK“ in der Sammelangabe, Maß an verdeckter Kante.
- Unit-Tests ohne SolidWorks für Schema, Prüfsumme, Funktionsauflösung, Maßplan-Regeln (Abschnitt 6.2) und Maßgraph.
- Live wie bisher einzeln mit Zeitlimit (`tests/live_einzeln.py`), Regressions-Suite um die Zeichnungs-Referenzen
  erweitert; nach Änderungen am Compiler weiter `-m werkzeuge.schnellbau_abgleich`.

## 11. Dem Bauer überlassen

- Genaue Schemaform je Feature-Typ (welche Fläche einer `extrusion` die Funktion trägt), Speicherform der aufgelösten
  Funktionswerte, Schwellen für Einzelheit, Abbruch und Koordinatentabelle, Wahl der Hauptansicht bei unklarer
  Hauptbearbeitungsseite, Layout-Algorithmus (Abstände kommen aus der Normdatei), Name der CLI-Unterbefehle im Detail.
- Was der Spike widerlegt (z. B. Bohrungsangabe nur mit Dialog), wird hier nachgetragen und dem Nutzer gemeldet, bevor
  Z1.3 beginnt.

## 12. Offen beim Nutzer (blockiert nur Z1.5)

- Blattformate liegen vor (17.11., SW 2026); offen: Normdatei (.sldstd) bzw. Maßstil und die Feldnamen des Schriftfelds, auslesbar erst auf dem Firmenrechner.
- Bestätigung der Werte in `funktionen.yaml` (vor der ersten Freigabe eines Teils mit `funktion`).
- OK für den Spike auf frischem SolidWorks (Nutzer arbeitet ggf. parallel).

## 13. Rückfragen aus dem Builder-Check (vom Nutzer beantwortet 16.11.: „Alle wie empfohlen“)

- Rechner und Lizenz → Fertigungsteile und -zeichnungen nur auf der Vollversion (Abschnitt 2).
- Behandlung, Halbzeug, rohe Flächen → eigene Anforderungsfelder (Abschnitt 4.1).
- Modell im Nennmaß mit Vermerk „Maßgebend ist die Zeichnung“ (Abschnitt 2, 5).
