# Paket Bemaßungsbezug – Konstruktionsabsicht über Bezüge statt Gleichungen

Ergänzung zu [2026-09-26-solidworks-ki-design.md](2026-09-26-solidworks-ki-design.md) (§4 Spezifikation, Regel
„Parameter werden zu SW-Gleichungen“) und [2026-09-29-stufe-2c-design.md](2026-09-29-stufe-2c-design.md) (Hinweise,
Normbohrung). Stand 2026-10-23, mit dem Nutzer abgestimmt.

## 1. Ziel und Warum

Gebaute Teile sollen sich in SolidWorks **von Hand optimieren lassen wie von einem Konstrukteur gebaute**: Maß
doppelklicken, ändern, alles Abhängige zieht sinnvoll mit.

Heute bemaßt swki jeden Skizzenpunkt zum Ursprung (`Skizzierer.lage`, [skizze.py](../../../swki/compiler/skizze.py))
und bindet jedes Maß, das in der Spec ein Ausdruck ist, per SW-Gleichung an globale Variablen
(`Kontext.verknuepfe`, `eigenschaften.globale_variablen`). Die Gleichungen ersetzen einen fehlenden Bezug: „5 mm vom
Rand“ steht in SolidWorks als `"D3@Skizze" = L/2 - 5`. Folgen für den Nutzer:

- Fast jedes Maß ist gesperrt (Σ-Maß); ändern geht nur über die globale Variable oder nach Löschen der Gleichung.
- Wer die Gleichung löscht und die Platte kürzt, verliert die Absicht: die Bohrung bleibt am alten Ursprungsabstand.

Die Absicht gehört in den **Bemaßungsbezug** (Nutzer, 2026-10-23): Eine Bohrung, die mit 5 mm zum Plattenrand bemaßt ist,
bleibt beim Kürzen der Platte 5 mm vom Rand – ohne Gleichung.

Für die KI-Konstruktion sind die Gleichungen entbehrlich: swki rechnet alle Ausdrücke selbst aus (`swki/spec/ausdruck.py`)
und setzt Maße mit dem fertigen Zahlenwert; `swki pruefen` misst Geometrie gegen die freigegebene Kopie. Einziger
Leser der globalen Variablen ist `swki aenderungen` (§8).

## 2. Entscheidungen (mit dem Nutzer, 2026-10-23)

| Frage | Entscheidung |
|---|---|
| Gleichungen | **standardmäßig aus** (keine globalen Variablen, keine Gleichungen an Maßen oder Verknüpfungen); einschaltbar (§4) |
| Bezug | in der Spec je Lageachse angegeben (`bezug`, §3); Maße stehen in SolidWorks als **Zahl** zum Bezug |
| Bemaßungsstil der KI | **symmetrisch angeordnete Elemente zur Mitte, alles andere von der Kante** (Rand der Fläche) |
| Freigabe | Bezug ist **Bauweg**: steht in der Freigabe-Vorlage in Worten, nicht in der Prüfsumme; die KI darf ihn beim Nachbessern ändern |
| Umfang Schritt 1 | `rechteck`, `kreis`, `langloch`, Positionen von `bohrung` und `normbohrung`. **Konturen (`polygon`, `kontur`) später**; sie bleiben Koordinatenmaße zum Ursprung (ohne Gleichungen) |

Eigene Entscheidungen beim Schreiben (vom Nutzer nicht ausdrücklich bestätigt, beim Review prüfen):

- Die Spec behält ihre **absoluten (u, v)-Koordinaten** mit Parametern und Ausdrücken. Prüfung, `huellquader: auto`,
  Sollvolumen und Freigabe hängen daran und bleiben unverändert. `bezug` sagt nur, **von wo aus** swki in SolidWorks
  bemaßt; den Maßwert berechnet swki als Zahl aus der absoluten Lage und der Lage des Bezugs.
- Ein Rechteck wird nie mehr über eine Ecke mit `=-L/2` festgelegt, sondern je Achse über die Mitte (`mitte`) oder
  über die Seite zum Bezug (§3). So wächst eine um den Ursprung gebaute Platte beim Ändern symmetrisch, eine Platte mit
  der Ecke im Ursprung (`ursprung`) nur zur freien Seite.
- `mitte` meint immer die Mittelebene **durch den Ursprung**. Symmetrische Bilder um eine andere Mitte (Lochkreis um
  eine versetzte Achse) bemaßt die KI von der Kante bzw. legt den Ursprung auf diese Mitte; eine eigene
  „Flächenmitte“ ist nicht im Paket (§13).
- Parameter bleiben Pflicht für Anforderungsmaße (Freigabe-Schutz, Hinweis `feste_zahl` unverändert) – das hatte nie
  etwas mit SW-Gleichungen zu tun.

## 3. Format

Neues optionales Feld `bezug` mit den Schlüsseln `u` und/oder `v`:

- an `bohrung` und `normbohrung` (Feature-Ebene, gilt für alle `positionen` und eine `senkung`),
- an den Skizzenelementen `rechteck`, `kreis`, `langloch` (im Element).

Werte je Achse:

| Wert | Bedeutung in SolidWorks |
|---|---|
| `ursprung` | Koordinatenmaß zum Ursprung (Projektion in die Skizze) – wie heute, ohne Gleichung. **Vorgabe**, wenn `bezug` oder die Achse fehlt |
| `mitte` | symmetrisch zur Mittelebene durch den Ursprung (§5.2): Paare, die spiegelbildlich zu u = 0 (bzw. v = 0) liegen, bekommen eine Symmetriebeziehung zu einer Mittellinie und **ein** Abstandsmaß zwischeneinander; Punkte auf der Mittelebene eine Ausrichtung; übrige ein Maß zum Ursprung |
| `"-rand"` / `"+rand"` | Abstand zur **Randkante der Skizzenfläche** in −u bzw. +u (für `v`: −v / +v). Nur für Skizzen auf Flächen (Flächenanker) – alle Bohrungen, Schnitte auf Flächen |
| `{flaeche: <flaechenanker>}` | Abstand zur Kante der Skizzenfläche, die in dieser Seitenfläche liegt (die Fläche steht senkrecht zur Skizzenebene, z. B. Seitenfläche eines anderen Features). Nur für Skizzen auf Flächen, wie `rand` |

*Nachgezogen bei der Umsetzung, 2026-10-24:* SolidWorks bemaßt nicht zu Flächen (Spike S17 Zeile 2: `AddHorizontalDimension2`
und `AddDimension2` mit der Seitenfläche legen kein Maß an; versucht wurde nur die Fläche aus `IFeature.GetFaces`). Darum
löst swki `{flaeche}` auf die Kante der Skizzenfläche auf, die in der genannten Seitenfläche liegt, und bemaßt dazu (Weg
von Zeile 1). Die frühere Aussage „auch für Skizzen auf Standardebenen“ entfällt: `{flaeche}` geht wie `rand` nur in
Skizzen auf Flächen (`validieren` lehnt es sonst ab); berührt die Seitenfläche die Skizzenfläche nicht, meldet der Bau
`REFERENZ_NICHT_GEFUNDEN`. Basisskizzen auf Standardebenen lassen sich nicht zu Flächen anderer Features bemaßen.

Was bemaßt wird:

- `kreis`, `langloch`, Bohrungspositionen: der **Mittelpunkt**.
- `rechteck`: bei `mitte` die Mitte; bei `ursprung` die dem Ursprung nächste Seite (liegt sie auf 0: kollinear zur
  Achse, z. B. Platte mit Ecke im Ursprung), bei Mitte auf 0 die Mitte; bei `rand`/`flaeche` die **dem Bezug
  zugewandte Seite** (eine Tasche „5 mm vom Rand“ meint die Taschenwand, nicht ihre Mitte).

Randkante: die geradlinige Kante der Skizzenfläche, die parallel zur anderen Achse liegt und die Fläche in der
genannten Richtung begrenzt (äußerste). Keine solche Kante → `REFERENZ_NICHT_GEFUNDEN`; mehrere gleich weit außen
(unterbrochener Rand) → die zur Position nächste, bei Gleichstand `REFERENZ_MEHRDEUTIG`.

Beispiel (Platte L × B um den Ursprung, zwei Gewinde 10 mm vom linken Rand, symmetrisch ±ZG):

```yaml
parameter: {L: 160, B: 100, H: 12, RA: 10, ZG: 20}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B", bezug: {u: mitte, v: mitte}}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: normbohrung, art: gewinde, groesse: M6, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=-L/2+RA", "=ZG"], ["=-L/2+RA", "=-ZG"]], bezug: {u: "-rand", v: mitte}, tiefe: 10}
```

In SolidWorks: Rechteck 160 × 100 symmetrisch zum Ursprung; Bohrungen 10 mm zur linken Plattenkante, 40 mm
zueinander, symmetrisch zur Mittellinie. Kürzt der Nutzer die Platte auf 150, bleiben die Bohrungen 10 mm vom Rand.

## 4. Gleichungen ein/aus

- `config/standard.yaml`: `gleichungen: false` (Vorgabe). Je Spec überschreibbar mit Top-Level `gleichungen: true`
  (Teil- und Baugruppen-Schema; Bauweg, nicht in `PRUEF_FELDER`).
- **Aus:** `globale_variablen` legt nichts an, `Kontext.verknuepfe` und die Gleichungen an Verknüpfungen
  (`sw_baugruppe.verknuepfe`) entfallen. Das gilt für Teile, Baugruppen und von `swki normteil` gebaute Normteile.
  Vorhandene Bibliotheksteile werden nicht nachgerüstet.
- **An:** Verhalten wie heute, mit einer Ausnahme: Lagemaße mit Bezug ≠ `ursprung` bekommen keine Gleichung (der
  Bezug trägt die Absicht; eine Gleichung würde ihn überschreiben).
  *Nachgezogen bei der Umsetzung, 2026-10-24:* „Bezug ≠ `ursprung`“ meint `rand` und `flaeche`. Mit `gleichungen: true`
  binden Lagemaße mit Bezug `ursprung`, die Paarabstände der Symmetrie und die Rechteckseiten von `mitte` wie bisher per
  Ausdruck (Paarabstand = 2 × Koordinatenausdruck, Rechteckseite `=(mitte) ± (groesse)/2`).

## 5. Compiler

### 5.1 Allgemein

- `Skizzierer.lage` bekommt den Bezug je Achse; der Maßwert ist eine Zahl (mm), nicht mehr ein Ausdruck.
- Skizzen bleiben **voll bestimmt** (Pflicht, `SKIZZE_NICHT_BESTIMMT` wie heute).
- Rechteck: Kennpunkt und Lage je Fall, siehe Nachtrag in §5.2.
- `bohrung`: `bezug` an die Kreise und die Senkungskreise weitergeben. `normbohrung`: `positionen_festlegen` mit Bezug.
- Bauprotokoll: neues Feld `masse` je Knoten – Liste `{name, pfad, art, bezug, wert}`; `name` wie `D3@f2_positionen`,
  `pfad` der Spec-Pfad (`features[1].positionen[0][0]`, `features[0].skizze.elemente[0].rechteck.breite`), `art`
  `lage`|`groesse`|`tiefe`|…, `wert` in mm bzw. Grad. Grundlage für `aenderungen` (§8). Erfasst werden alle Maße, die
  heute `verknuepfe` durchlaufen, auch Tiefen, Radien, Musterabstände und Verknüpfungswerte.

### 5.2 `mitte`

Paarbildung je Achse **über die ganze Skizze** (in `skizziere` bzw. `positionen_festlegen`, nicht je Element): zwei
Bezugspunkte mit `mitte` auf dieser Achse – Positionen einer Liste oder Mittelpunkte gleichartiger, gleich großer
Elemente (zwei Taschen, zwei Langlöcher) –, deren Koordinate auf der Achse entgegengesetzt gleich ist (Toleranz
`anker_mm`) und auf der anderen Achse gleich. Eine Mittellinie (Konstruktion) durch den Ursprung entlang der anderen
Achse; je Paar Symmetriebeziehung und ein Abstandsmaß. Ungepaarte Punkte ≠ 0 bekommen ein Maß zum Ursprung, Punkte auf
0 eine Ausrichtung. Ein Rechteck mit Mitte auf 0 liegt mit seiner Mitte auf der Mittelebene (Breite bleibt
symmetrisch).

Keine Überbestimmung: Die Symmetrie legt den Partner fest. Nur ein Punkt je Paar bzw. Gruppe (2×2-Lochbild mit `mitte`
auf beiden Achsen: ein Eckpunkt) bekommt die übrigen Lage- und Abstandsmaße; Randmaße auf der anderen Achse (Beispiel
§3) nur am ersten Punkt.

*Nachgezogen bei der Umsetzung, 2026-10-24 (Spike S17 Zeilen 4–5, Rulings 4, 4a, 6, 10):*

- **Mittellinie:** Ihr Endpunkt liegt per `sgCOINCIDENT` auf der Randkante der Skizzenfläche. Skizzen ohne Skizzenfläche
  (Standard- und Versatzebene) haben keine Randkante; dort bekommt die Mittellinie ein Längenmaß (Konstruktionsmaß).
- **Rechteck** (Spike: Diagonale mit `sgATMIDDLE`, Seitenmittelpunkt über `CreatePoint` + `sgATMIDDLE`), festgelegt je
  Fall. „Seitenbezug“ heißt je Achse `rand`, `flaeche` oder `ursprung` mit Mitte ≠ 0 (zugewandte bzw. nächste Seite),
  „mitte“ heißt `mitte` oder `ursprung` mit Mitte auf 0:
  - (a) beide Achsen Seitenbezug: die Ecke der zugewandten Seiten;
  - (b) eine Achse Seitenbezug, die andere mitte: Mittelpunkt der zugewandten Seite, ein Kennpunkt mit beiden Achsen
    (paarfähig);
  - (c) beide Achsen mitte um (0, 0): zwei Seitenmittelpunkte (u über die waagrechte, v über die senkrechte Seite, je
    eine Ausrichtung), keine Konstruktionslinie;
  - (d) beide Achsen mitte, Mitte ≠ (0, 0): Mittelpunkt über die Diagonale (paarfähig). In Rotationsskizzen statt (d)
    zwei Seitenmittelpunkte mit Maßen zum Ursprung, ohne Paare.
  Die Diagonale kommt damit nur in (d) vor; Radius und Diagonale in Grundplatten sind so nie kombiniert.
- **Verrundungen** der Rechteckecken wählt swki über das Linienpaar der Ecke (`seg[i-1]`, `seg[i]`), nicht über die
  Koordinate: Nach der ersten Verrundung verschiebt `sgATMIDDLE` an der getrimmten Seite das Rechteck, erst nach allen
  vier Verrundungen liegt der Seitenmittelpunkt wieder in der Mitte (live belegt, Fall b und c mit Radius).

### 5.3 `rand` und `flaeche`

Bezugskante bzw. -fläche über die vorhandene Topologie (`swki/compiler/topologie.py`) suchen, in der Skizze wählen und
Punkt (bzw. Rechteckseite) dazu bemaßen. SolidWorks bemaßt direkt zur Modellkante, auch in der Positionsskizze des
Bohrungsassistenten (Spike S17 Zeilen 1, 3, 4); zu Flächen bemaßt es nicht (§3, Nachtrag). Bezug ist immer Geometrie, die
im Baum **vor** dem Feature liegt.

## 6. Validieren

- Schema: `bezug` an den genannten Stellen; Werte wie §3.
- Fehler: `rand` oder `{flaeche}` in einer Skizze auf Standard- oder Versatzebene (keine Skizzenfläche, §3 Nachtrag);
  `bezug` an `polygon`/`kontur` (noch nicht unterstützt).
- Neuer Hinweis `art: bezug`: Lagekoordinate ≠ 0 in `bohrung`/`normbohrung`-Positionen oder in `rechteck`/`kreis`/
  `langloch` auf einer Skizzenfläche **ohne** Bezug auf dieser Achse – „Bemaßungsbezug angeben (mitte oder rand),
  sonst wird zum Ursprung bemaßt“. Nicht für Konturen, Mittellinien und Basisskizzen auf Standardebenen.
- `feste_zahl` bleibt unverändert; Meldungstext ohne Bezug auf Gleichungen.
- Freigabe-Vorlage (Skill `konstruieren`): Bezüge in der Feature-Liste in Worten („2 × M6, 10 mm vom linken Rand,
  symmetrisch zur Mitte, Abstand 40“).

## 7. Prüfen

- Geometrieprüfung unverändert (misst gegen die freigegebene Kopie; Bezüge sind Bauweg).
- Neu, nur bei Gleichungen aus: `swki pruefen` meldet einen Befund, wenn das Modell Gleichungen oder globale Variablen
  enthält (`GLEICHUNGEN_VORHANDEN`) – fängt Handler, die `verknuepfe` umgehen. In Baugruppen nur am Baugruppendokument
  und an Eigenteilen; Normteile aus der Bibliothek tragen weiter ihre globalen Variablen (nicht nachgerüstet).
  *Nachgezogen bei der Umsetzung, 2026-10-24:* Ein alter Lauf mit globalen Variablen bekommt bei erneutem `swki pruefen`
  ebenfalls `GLEICHUNGEN_VORHANDEN`, ohne Ausnahme (sonst wäre die Invariante aufgeweicht). Abhilfe: `swki bauen`; die
  Freigabe bleibt gültig.
- Prüfer-Agent: keine Änderung.

## 8. `swki aenderungen`

- Liest statt der globalen Variablen die Maße aus `masse` des Bauprotokolls (`model.Parameter(name).SystemValue`) und
  meldet je geändertem Maß `{pfad, art, bezug, soll, ist}`.
- `aenderungen` misst keine Geometrie und rechnet nicht symbolisch. `masse` speichert je Lagemaß zusätzlich den
  Rohwert der Spec-Koordinate (`=-L/2+RA`) und das Vorzeichen (Richtung vom Bezug zum Punkt).
- Vorschlag nur, wenn eindeutig: Größenmaß, dessen Ausdruck genau ein Parameter ist (`=P`, `=-P`) → Parameter P neu.
  Hängen zwei geänderte Maße am selben Parameter mit verschiedenen Werten → `konflikt`, die KI fragt den Nutzer.
- Lagemaß mit Bezug: Meldung mit Pfad, Rohwert, Bezug und Δ = ist − soll (Randabstand 10 → 12: Δ = +2 vom Rand weg).
  Die KI leitet die Spec-Änderung ab (meist: den Abstandsparameter um Δ ändern, `RA = 12`) und legt sie dem Nutzer vor;
  `swki pruefen` nach dem Neubau bestätigt die Geometrie. Steht in der Spec eine feste Zahl, schreibt die KI die
  Koordinate dabei als Ausdruck des Bezugs um.
- Ein Lagemaß, das unverändert blieb, während sich sein Bezug bewegt hat (Bohrung 10 mm vom Rand, Platte gekürzt), ist
  Absicht und erscheint nicht als Differenz; die Spec stimmt, wenn die Koordinate als Ausdruck des Bezugs geschrieben ist
  (Skill-Regel §9), sonst meldet erst `swki pruefen` die Abweichung.
- Nicht über Maße erklärbare Änderungen (neues Feature, gelöschte Bohrung): wie heute „Datei geändert, Maße gleich –
  Nutzer fragen“.
- Läufe aus der Zeit mit Gleichungen (Protokoll ohne `masse`): wie heute über globale Variablen.
- Danach wie bisher: Spec ändern, validieren, Nutzer-OK, `swki freigeben`, `swki bauen --uebernommen`, prüfen.

*Nachgezogen bei der Umsetzung, 2026-10-24:* `swki aenderungen` liefert je Datei `parameter` (nur Läufe ohne `masse`), `masse`
(je geändertem Maß `{name, pfad, art, bezug, roh, vorzeichen, soll, ist, delta}`; fehlt das Maß, ist `ist` und `delta`
`None`) und `vorschlaege`. Der Parametervorschlag `{parameter, neu}` hat den **Betrag** des Maßes und das **Vorzeichen des
freigegebenen Parameters** (SolidWorks-Maße sind Beträge; bei Parameter 0 positiv), unabhängig vom Minus im Ausdruck
(`=-P`); bei verschiedenen Werten `{parameter, konflikt: […]}`. Lagemaße erscheinen als `{pfad, bezug, delta}`, nie als
Parameter. Konstruktions- und Skriptmaße ergeben keinen Vorschlag.

## 9. Skill `konstruieren` und `baugruppe`

- Regel „Maße als Parameter und Ausdrücke; sie werden SW-Gleichungen“ ersetzen: Parameter für Anforderungen; Lagen, die
  vom Rand oder von der Mitte abhängen, als Ausdruck **des Bezugs** schreiben (`=-L/2+RA`) und den `bezug` setzen.
- Bemaßungsstil (Nutzerentscheidung §2): symmetrische Bilder `mitte`, sonst `rand` der Fläche, an der das Teil gefertigt
  bzw. angeschlagen wird; ein Teil hat möglichst eine Bezugsecke (keine Maßketten).
- `baugruppe`: Hinweis, dass Verknüpfungswerte ohne Gleichung als Zahl stehen.

## 10. Spike S17 (vor dem Plan-Code)

Live, ein Wegwerf-Teil, Ergebnisse in die Spec nachziehen:

1. Skizzenpunkt auf einer Fläche zur Modellkante dieser Fläche bemaßen (`AddHorizontalDimension2`/
   `AddVerticalDimension2`/`AddDimension2` mit gewählter Kante): Maß maßgebend, Wert, Skizze voll bestimmt?
2. Dasselbe in der Positionsskizze des Bohrungsassistenten (`HoleWizard5`, mehrere Punkte).
3. Zu einer Seitenfläche senkrecht zur Skizzenebene bemaßen (Fläche statt Kante).
4. Zwei Punkte symmetrisch zu einer Mittellinie plus Abstandsmaß; Rechteck über Mittelpunkt (Diagonale oder Punkt +
   Symmetrie) – voll bestimmt, ohne automatische Beziehungen.
5. Handtest: Plattenlänge per `Parameter(...).SystemValue` ändern, neu aufbauen → Bohrung bleibt am Randabstand, keine
   Neuaufbaufehler; ebenso mit einer Fase an der Bezugskante, die im Baum später liegt.
6. `Parameter(name).SystemValue` in einer frisch geöffneten, von Hand geänderten Datei lesen (für §8).

Jeder neue API-Aufruf vorher über `swki api methode` nachschlagen.

*Nachgezogen bei der Umsetzung, 2026-10-24:* Ergebnisse und Abweichungen in
[docs/bemassungsbezug/ergebnisse.md](../../bemassungsbezug/ergebnisse.md) §1.

## 11. Tests und Referenzen

- Unit-Tests (ohne SolidWorks): Schema, Hinweis `bezug`, Paarbildung `mitte`, Maßwert aus Lage und Bezug, Protokoll
  `masse`, `aenderungen`-Vorschläge und Konflikt, Gleichungen aus/an.
- Bestehende Tests, die Gleichungen erwarten (`tests/compiler/test_kontext.py`, `tests/live/test_live_*`), auf
  `gleichungen: true` stellen oder auf Maße umstellen.
- Referenz-Specs der Regressions-Suite um `bezug` ergänzen, wo sinnvoll (mindestens Motorhalter-Grundplatte und
  Zentrieraufnahme); die Suite läuft mit Gleichungen aus und muss bestehen.
- Live-Test „Handänderung“: Referenzplatte bauen, Länge per API ändern, Randabstand der Bohrung messen,
  `swki aenderungen` liefert den Parameter-Vorschlag.

## 12. Fertig, wenn

- Neu gebaute Teile und Baugruppen enthalten ohne `gleichungen: true` keine Gleichung und keine globale Variable.
- Bohrungen und Ausschnitte mit `bezug` sind in SolidWorks zur Kante bzw. symmetrisch bemaßt; der Handtest (§10.5)
  besteht.
- `swki aenderungen` erkennt eine Handänderung an einem Maß und schlägt die Spec-Änderung vor.
- Regressions-Suite grün; CLAUDE.md, Skills `konstruieren`/`baugruppe` und die Designspec-Regel (§4 der Grundspec)
  nachgezogen.

## 13. Nicht im Paket

- Bezüge für Konturpunkte (`polygon`, `kontur`) und Mittellinien.
- Bezug zu einem anderen Element derselben Skizze (Kettenmaß, „Bohrung 20 mm neben Bohrung 1“).
- `mitte` um eine andere Mitte als den Ursprung (Flächenmitte, versetzte Achse).
- Messen der Geometrie oder symbolisches Rückrechnen in `swki aenderungen`.
- Bezüge an Mustern, Fasen, Verrundungen, Endbedingungen (dort gibt es keine Lagemaße).
- Nachrüsten vorhandener Läufe und Bibliotheksteile; Zeichnungsableitung.
