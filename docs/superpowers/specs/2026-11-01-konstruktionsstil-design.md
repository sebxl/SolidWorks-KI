# Paket Konstruktionsstil – Design

Stand 01.11.2026. Vorgaben des Nutzers: Rückfrage vom 01.11.2026; alles andere ist als „Selbst entschieden“ markiert.

## 1. Absicht

Von swki gebaute Teile sollen im Feature-Baum aussehen wie von einem Konstrukteur: Formen gespiegelt, Wiederholungen
gemustert, Radien und Fasen dort, wo sie fachlich hingehören.

Die Features fehlen nicht, die Regeln verhindern sie:
- Regel 3 (Skill `konstruieren`) erlaubt Muster und Spiegeln nur als Anforderung, Regel 4 schiebt Radien in die Skizze.
- `swki validieren` rät in `swki/spec/hinweise.py` (`_REGEL_3`) aktiv von Muster und Spiegeln ab.
- Ausgangsmaß: 22 Referenz-Specs und 27 Specs AP 6.8 haben 200 Features, davon 5 Fasen, 4 Verrundungen, 2 Muster,
  1 Spiegeln.

**Nicht-Ziele:** Schnellbau-Umsetzung (Stufe C3a), Fasen an Außenkanten, die Feature-Typen Rippe, Schale und Loft,
fremde Dateien (Skill `aendern` räumt nichts auf).

**Anti-Ziel:** mehr Features ohne Fertigungssinn. Die Regeln aus `konstruktion-fertigungsgerecht` gelten weiter
(Halbzeug, keine Modellierhilfe-Stufen). Freigabe-Schutz und Prüfungen gegen die freigegebene Kopie werden nicht schwächer.

## 2. Standard des Nutzers

| Thema | Regel | Herkunft |
|---|---|---|
| Fase am Eintritt | Stift-, Pass- und Durchgangsbohrungen 0,5 × 45° | Nutzer |
| Gewindeeintritt | Ansenkung auf Gewinde-Nenn-Ø | Nutzer |
| Außenkanten | keine Fase im Modell | Nutzer (nicht gewählt) |
| Anlage- und Passkanten | keine Fase | Nutzer (in der Frage gesetzt) |
| Innenecken Frästeile | Pflicht, R ≥ Tiefe/5 (Tiefe ≤ 2,5 × Fräser-Ø: Ø 2 bis 5 mm Tiefe) | Nutzer |
| Radiuswahl | größer ist besser, kleiner nur mit Grund; kein fester Wert | Nutzer |
| Spiegeln, Muster | Formen ja; Bohrbilder nur Reihen ab 3 Stück; kleine symmetrische Bohrbilder (2–4) ein Knoten | Nutzer |
| Neuer Typ | Austragung entlang Pfad | Nutzer |

„Tiefe“ ist die Frästiefe an der Ecke: Taschentiefe, bei Durchbrüchen die Dicke (Selbst entschieden: Lesart von
„Höhe der Bauteile“).

## 3. Regeln im Skill `konstruieren`

Neufassung der Modellierregeln. Die Nummern bleiben, weil `validieren` sie zitiert.

- **Regel 3 neu:** Symmetrische Formen (Tasche, Aufsatz, Steg) einmal bauen und spiegeln, gleiche Formen mustern.
  Bohrbilder: Reihe heißt mindestens 3 Löcher auf einer Linie mit gleicher Teilung, auch bei nur 3 oder 4 Löchern. Sie
  wird gemustert, ein Raster mit zwei Richtungen ebenso. Alle anderen Bilder aus 2–4 Löchern (Paare, Eckbilder) bleiben
  in einem Knoten (Regel 2) mit `bezug: mitte`. Lochkreise bleiben in `positionen`: Der Nutzer nannte nur Reihen, und
  `muster_kreis` dreht nur um x, y, z durch den Ursprung (Selbst entschieden).
- **Regel 4 neu (Selbst entschieden, Nutzer hat Baum oder Skizze nicht beantwortet):** Eckradien sind ein Knoten
  `verrundung`. Der Skizzen-`radius` bleibt für Fälle, in denen die Kontur den Bogen trägt (Langloch, Kontur mit Bögen,
  Formschräge, gedruckte Teile), und für Specs mit `optimierung` oder Simulation bis C3a (Abschnitt 9). Grund: Die
  Beschwerde war, dass Radien im Baum fehlen.
- **Regel 6 neu (Selbst entschieden):** Eckradien gleichen Maßes in einem Knoten, direkt hinter dem letzten Element, das
  ihn trägt. Ausnahme: Gehört die Verrundung zur Quelle eines Musters oder einer Spiegelung, bleibt sie ein eigener
  Knoten direkt hinter der Form und steht in `features` des Musters. Echte Kantenverrundungen, die keine Eckradien sind,
  bleiben am Ende des Baums. `_gruppen` meldet weiter gleiche Knoten, außer solche in Quellen. Fasen an Bohrungen laufen
  über das Feld `fase` (Abschnitt 4).
- **Neu Regel 8:** Innenecken gefräster Teile nach der Fräserregel (Tabelle Abschnitt 2).
- `baugruppe`: gemusterte Bohrungen sind Instanzen wie Positionen (Abschnitt 6).
- `konstruktionsreview`: Checkliste Punkt 7 „Konstruktionsstil“ (Innenradien, Bohrungseintritte, Spiegeln und Muster).
  Punkt 1 und 2 bleiben.

## 4. Spec-Änderungen

Neu ist das Feld `fase` an `bohrung` und `normbohrung`:

```yaml
- {id: f3, typ: normbohrung, art: gewinde, groesse: M8, ..., fase: nenn}   # Ansenkung auf Nenn-Ø, nur bei Gewinde
- {id: f5, typ: bohrung, ..., fase: "=FB"}                                  # c × 45° am Eintritt
```

- Der Compiler legt hinter der Bohrung ein Fase-Feature `<id>_fase` an, `_fase` wird reservierte Endung.
- `ergebnis.features` enthält Bohrung und Fase; Muster und Spiegeln nehmen die Fase darum mit.
- Gewählt wird je Position die größte Kreiskante in der Eintrittsebene, also bei Senkungen der Senkungsrand.
- `art: senkschraube` lehnt `validieren` ab: Die Senkung ist schon kegelig.
- Der Wert ist Parameter oder Zahl und läuft über `Kontext.mass`; `nenn` wird berechnet und nicht ins Maßprotokoll
  geschrieben.

**Selbst entschieden:** ein Feld an der Bohrung statt eigener `fase`-Knoten je Bohrung. So bleibt eine Bohrung in der
Spec ein Knoten, und Reihenfolge und Muster können nicht auseinanderlaufen. Der Baum zeigt trotzdem die Fase.

**Selbst entschieden (Rückweg):** Das sichtbare Feature `<id>_fase` gilt auch für `fase: nenn`, die Ansenkung läuft
nicht unsichtbar im Bohrungsassistenten. Das Spec-Format steht fest und hängt nicht am Spike. Trägt der Spike das Mustern
mit Fase als Quelle nicht, legt der Compiler die Fase hinter dem Muster auf alle Kopien. Bohrungen gehen dafür nicht
zurück in `positionen`.

Bestehende Fase- und Verrundungsknoten bleiben unverändert.

## 5. `swki validieren`

Hinweise blockieren nie und werden vor der Freigabe abgearbeitet wie bisher.

Entfällt: `_REGEL_3` mit den Ratschlägen gegen Muster und Spiegeln.

Neu mit `art: zusammenfassen` (Regel 3):
- mindestens 3 Löcher auf einer Linie mit gleicher Teilung in `positionen` → `muster_linear`
- mindestens 3 gleiche Formen mit gleichem Abstand → `muster_linear`
- 2 gleiche Formen spiegelbildlich zu einer Standardebene → `spiegeln`
- mehrere spiegelbildliche Profile in einer Skizze → einmal skizzieren und spiegeln

Neu mit `art: fertigung`:
- Schnitt mit Ecken ohne Radius oder mit R < Tiefe/5 → Text nennt das Mindestmaß. Gilt für `rechteck`, `polygon`,
  `kontur`; Kreis und Langloch haben keine Ecken.
- konkave Polygonecke einer Extrusion ohne Radius, gleiche Regel mit der Extrusionstiefe
- Bohrung mit Eintritt ohne `fase`: `stift`, `gewinde`, `zylinderschraube`, `bohrung`

Die neuen Hinweise werden über alle 49 Specs laufen gelassen. Fehlalarme werden in den Ergebnissen genannt und vor dem
Abschluss beseitigt. Die Fräserregel kennt keine Fertigungsart: Bei gedruckten Teilen und Ersatzkörpern begründet die
Freigabe-Vorlage den Hinweis in einer Zeile (Selbst entschieden: kein neues Spec-Feld dafür).

## 6. Prüfen, Maßprotokoll, Baugruppe

Lücken aus dem Code, je mit Test zuerst:

| Lücke | Heute | Danach |
|---|---|---|
| `volumen: auto` mit `verrundung` | „nicht analytisch“, Spec muss Zahl führen | `{feature, auswahl: senkrechte_kanten}` wird wie Skizzen-Radius gerechnet (Rechteck, Polygon); `nahe` bleibt nicht berechenbar |
| `volumen: auto` mit `fase` | wie oben | Feld `fase`: π·c·(r·c + c²/3) je Position (45°); Knoten `fase` bleibt nicht berechenbar |
| Anzahl im Muster | Freigabe schützt Features nicht, Prüfung fehlt | neue Prüfung `muster` gegen die freigegebene Kopie: Anzahl und Abstand bzw. Winkel, Quellen, Spiegelebene |
| Fasen- und Radienmaß | nur über Volumen | neue Prüfung `kanten` gegen die freigegebene Kopie: Maß aus der Feature-Definition, Fläche vorhanden |
| `instanz` gemusterter Bohrungen | nur `positionen` (`anzahl_positionen`, `plausibel.py`, `messgeometrie`, `_bohrung`) | Punkte werden je Muster und Spiegeln abgeleitet, Instanzen zählen in Muster-Reihenfolge |
| Gewindeprüfung mit Ansenkung | Soll-Überlappung ohne Ansenkung (`swki/baugruppe/geometrie.py`) | Soll berücksichtigt die Ansenkung |
| Lage von Musterkopien | nur Schwerpunkt, Steckbrief | Steckbrief reicht; Prüfer sieht die Liste, keine neue Prüfung |

Warum `muster` Pflicht ist: Eine Lochreihe in `positionen` prüft `normbohrungen` heute auf die Anzahl. Als Muster ginge
diese Prüfung verloren, wenn `muster` fehlt. Das wäre die verbotene Schwächung.

**Maßstab gegen die freigegebene Kopie (Selbst entschieden):** Muster bleiben nach der Freigabe Bauweg, die Wirkung nicht.
- Bohrungen werden nach Wirkung verglichen: Aus der Kopie und aus der aktuellen Spec entsteht je Bohrung (Art, Größe,
  Tiefe) die Liste aller Instanzlagen, die Listen müssen gleich sein. `normbohrungen` vergleicht dazu nicht mehr
  `len(positionen)` allein, sondern die Punktzahl des Knotens mit der aktuellen Spec und das Lagenbild mit der Kopie. So
  darf eine Reihe in der Nachbesserung zwischen `positionen` und Muster wechseln.
- Formen und Kanten werden nach Knoten-ID verglichen wie `normbohrungen`: Fehlt ein Knoten der Kopie oder weicht er ab,
  ist das ein Mangel. Knoten ohne Gegenstück in der Kopie sind Bauweg und bleiben ungeprüft.

**Instanznummern:** Erst die Positionen der Quelle, dann die Kopien in Musterreihenfolge. `{feature, instanz}` in
`masse_pruefen` zeigt auf den Knoten der Kopie und löst Quelle wie Muster zur selben Lage auf. Verschiebt ein Umbau die
Nummern, weicht die Lage von der Kopie ab, und `swki pruefen` meldet das, statt still umzuhängen.

`huellquader: auto` braucht nichts Neues: Muster und Spiegeln sind abgedeckt, Fasen und Verrundungen verkleinern ihn
nicht, solange sie nicht an der äußersten Hülle liegen (Bohrungseintritte, Innenecken).

Maßprotokoll: `muster_linear`, `muster_kreis`, `verrundung`, `fase` schreiben schon. Hinzu kommt das Feld `fase`.
`swki aenderungen` muss eine geänderte Lage einer Bohrung mit `_fase` wie bisher lesen (Test).

## 7. Austragung entlang Pfad

Neuer Typ, Vorgehen über den Skill `compiler-erweitern`, mit Spike vor dem Plan-Code:

```yaml
- id: f4
  typ: austragung
  profil: {ebene: rechts, elemente: [{kreis: {mitte: [0, 0], durchmesser: "=D"}}]}
  pfad:   {ebene: oben, start: [0, 0], segmente: [{linie: [40, 0]}, {bogen: [...], mitte: [...]}]}   # offen
  schnitt?: true
```

- API: `InsertProtrusionSwept4`, `InsertCutSwept5`; Parameter stehen im Index (20 bzw. 22).
- Geschlossene Pfade: nur wenn der Spike sie ohne Sonderfall zeigt.
- `volumen: auto`: Kreis oder Rechteck mit Mitte auf dem Pfadanfang rechnet A × Pfadlänge, sonst nicht berechenbar.
- `huellquader: auto`: nicht berechenbar, Kanten angeben.
- Fehlercode, wenn das Profil nicht auf dem Pfad liegt: `validieren` lehnt es ab.
- Maße von Profil und Pfad über `Kontext.mass`.

## 8. Referenzteile

- **Stehlager neu (Unterteil, Deckel):** Gewinde, Durchgang und Stift bekommen `fase`. Das beweist Bohrungsfasen mit
  Schrauben- und Gewindeprüfung in einer echten Baugruppe.
- **Neu `tests/referenz/stil/`, Teil `spannplatte`:** zwei gespiegelte Taschen mit Tiefe/5-Radius, Lochreihe als Muster
  mit `fase`, Austragung als Kanal. Heute-Stand zum Vergleich: dasselbe Teil nach den alten Regeln als Spec.
  Ausgangsmaß und Endmaß: Knotenzahl je Typ, Bauzeit.
- Negativfälle in `tests/` ohne SolidWorks: Radius zu klein, falsche Musteranzahl gegen die freigegebene Kopie,
  `fase` an Senkschraube, Instanz über Musteranzahl.

Die Referenz-Specs brauchen eine neue Freigabe. Sie gilt als erteilt, wenn der Nutzer dieses Design bestätigt, und nur
für diese Referenzteile.

## 9. Für C3a (Schnellbau)

- Der Schnellbau kennt `fase` an Bohrungen nicht und meldet das in `meldungen`, nie still.
- `austragung` meldet `SCHNELLBAU_NICHT_UNTERSTUETZT`.
- `tests/schnellbau` und `sw_referenz.json` müssen für das Stehlager angepasst werden.
- `verrundung` in Quellen von Muster oder Spiegeln wirft im Schnellbau `NICHT_UNTERSTUETZT`. Darum behalten Specs mit
  `optimierung` oder Simulation bis C3a den Skizzen-`radius`; der Hinweis `fertigung` zählt ihn als Radius, und der Skill
  `optimieren` bekommt dazu einen Satz (Selbst entschieden: billiger als Schnellbau-Arbeit vorzuziehen, C3a folgt direkt).
- C3a soll Bohrungsfasen, Muster aus Formen samt Verrundung und `austragung` umsetzen.

## 10. Reihenfolge

1. Spike: Muster mit Bohrung und Fase als Quelle, Verrundung in Mustern, Fase auf Gewinde-Kernloch, Sweep.
2. Hinweise, Regeln, Review.
3. Feld `fase` samt Volumen und Gewindeprüfung.
4. Prüfungen `muster` und `kanten`, Instanzen.
5. `austragung`.
6. Referenzen, Regression, Ergebnisse, PR.

Bauzeiten kommen in die Ergebnisse: Eine Fase kostet heute 0,5–6 s. Mehr Features verlängern den Bau, das BTP-Mittel wird
nicht neu erhoben, solange der Nutzer das nicht will.
