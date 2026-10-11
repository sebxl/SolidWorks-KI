# SWKI-12: Mehrdeutige Flächenanker vor dem Bau erkennen

Stand 11.10.2026 · Klärung, keine Umsetzung · zur Entscheidung durch den Nutzer

## Kernaussage

Ja, im häufigen Fall lässt sich das erkennen: `swki validieren` kann für Aufsätze aus **einem Rechteckprofil**
aus der Spec berechnen, ob die Fläche `{feature, flaeche: "±a"}` zum Zeitpunkt ihres Gebrauchs in mehrere Teilflächen
zerfällt. Dabei kann es gleich einen Punkt für `{nahe}` vorschlagen. Die Rechnung baut auf den Hüllquadern auf, die
`swki/pruefung/huellquader.py` (`_koerper(spec, p, bis=…)`) schon je Aufsatz und Schnitt bestimmt.

## Ursache

`flaeche_in_richtung` (`swki/compiler/anker.py`) nimmt unter den ebenen Flächen **des Features** mit Normale ±a die
äußerste. Liegen zwei gleich weit außen (< 1e-4 mm), meldet es `REFERENZ_MEHRDEUTIG`. Beim Messen gilt
`koplanar_ok=True`, dort tritt der Fehler nicht auf. Betroffen sind Bau-Anker (Skizzenebene, `flaeche` von Bohrung und
Normbohrung, `ende.flaeche`, `kanten_an`) und Baugruppen-Anker `{komponente, feature, flaeche}`. Bau-Anker sehen nur die
Features vor dem nutzenden Knoten, Baugruppen-Anker das fertige Teil.

## Beispiel Zylinderhalter (Etappe 4, Lauf 16, Spec vor T7)

- f1 Steg: X −290 … −210, Y 293 … 329,7, Z −207,5 … −202 (Maschinenkoordinaten)
- f3 Flansch: X −300 … −290, Y 293 … 318, Z −209 … −184; Anker von f5 (Normbohrung M5): `{feature: f3, flaeche: "+x"}`
- Der Steg beginnt genau in der +X-Ebene des Flanschs (X −290) und überdeckt sie über die ganze Breite Y 293 … 318.
  Es bleiben zwei Streifen, Z −209 … −207,5 und Z −202 … −184. Damit liegen zwei Flächen bei X −290: `REFERENZ_MEHRDEUTIG`
  nach 250 s Baugruppenbau.
- Eine Probe (Scratch, nicht im Repo) mit Zellzerlegung „Flächenrechteck minus Überdeckungen“ fand genau diesen Fall:
  `f3 +x: 2 Teilflächen in x=-290, z. B. {nahe: [-290.0, -193.0, -305.5]}` (Teilkoordinaten, Mitte des größeren
  Streifens, auf dem auch die M5-Löcher liegen). Bemerkenswert: Der teilende Steg ist ein *früheres* Feature (f1 vor f3).
  Die Prüfung muss also alle Körper vor dem nutzenden Knoten ansehen, nicht nur die späteren.

## Erkennbar (aus Skizze und Extrusion)

1. Ziel-Feature ist eine Extrusion (Aufsatz) aus einem Rechteck: Die Fläche ist ein Rechteck auf der Hüllquaderseite.
   Sie zerfällt, wenn Aufsätze, die außen aufsitzen oder die Ebene durchdringen, oder Schnitte mit bekannter Lage sie
   in mehrere zusammenhängende Teile zerlegen. Ein Zapfen mitten auf der Fläche (innere Schleife) oder ein Aufsatz an
   der Kante (L-förmiger Rest) teilt sie nicht. Das gibt keinen Hinweis.
2. Mehrere getrennte Profile in einer Skizze (zwei Rechtecke nebeneinander): mehrere Deckflächen in Extrusionsrichtung
   bzw. mehrere Seitenflächen auf gleicher Höhe. Verschachtelte Profile (Rechteck mit Loch) zählen nicht.
3. Dieselbe Rechnung für Baugruppen-Anker, dort über alle Features des Teils.

## Nicht (sicher) erkennbar

- Ziel-Feature ist ein **Schnitt** (Taschenboden, z. B. `pruefkanal` f2), **Polygon/Kontur** (T-Profil `schieber` f2,
  `weichenkeil` f1, `rutsche` Lasche), Kreis/Rotation. Polygone ließen sich mit Kantenanalyse erweitern, die Teilung
  durch fremde Körper bliebe aber eine Rechteck-Näherung.
- Körper nicht berechenbar: Skript (`trichter`), Verzahnung (`zahnstange`), Kreismuster von Aufsätzen, Skizzen auf
  `{nahe}`. **Schnitte `durch_alles`** überspringt `_koerper` heute. Eine Nut, die die Fläche quer durchtrennt, bleibt
  deshalb unentdeckt (falsch-negativ).
- Bündig in der Ebene endende Aufsätze (koplanare Verschmelzung, die Zuordnung der Fläche bestimmt SolidWorks):
  kein Hinweis, denn die Referenz `motorhalter` (bock f1 −y bündig mit f2) baut.
- Bohrungen, Fasen und Verrundungen teilen Flächen praktisch nie und werden ignoriert.

## Häufigkeit in den echten Specs

Probe über 62 Specs (`auftraege/**`, `tests/referenz/**`, ohne `*.freigegeben.yaml`) mit 216 Flächenankern:
**196 berechenbar und eindeutig, 19 nicht prüfbar** (Schnitt 6, Polygon 5, Kreis 2, Skript 3, Verzahnung 3, je
Bau- und Baugruppenanker), **1 unsicher** (motorhalter, bündig). In den heutigen Specs gibt es keinen Treffer, sie bauen
ja alle. Den einzigen echten Fall (Zylinderhalter alt) findet die Probe. Rund 90 % der Anker liegen also im
erkennbaren Bereich. Der Nutzen ist selten, aber teuer: Bauabbruch nach Minuten und eine neue Freigabe. Dazu kommt
ein indirekter Nutzen: Die Skill `konstruieren` braucht keine Stufen „für den Bauweg“ mehr aus Vorsicht.

## Empfehlung

**Umsetzen, als Hinweis, nur für Rechteck-Aufsätze.** Aufwand etwa **1 Tag**: Funktion etwa 120 Zeilen in
`swki/spec/hinweise.py` (nutzt `huellquader._koerper`, öffentlich machen), Tests etwa 150 Zeilen. Fixtures: alter
Zylinderhalter, Zapfen mittig, Nut quer, bündig, zwei Rechtecke. Baugruppen-Anker kosten etwa +0,25 Tag in
`swki/baugruppe/hinweise.py`. Teil-Hinweise erscheinen dort schon heute je Komponente. Nicht empfohlen: Polygon- und
Schnitt-Ziele (+1 Tag, geringe Trefferquote), `durch_alles` (braucht Körperausdehnung). Vorschlag: `swki durchlauf
--freigeben` hält wie bei `pruefwert` vor der Freigabe an, weil der Fix eine Spec-Änderung ist.

Skizze des Hinweises:

```json
{"art": "anker_mehrdeutig", "pfad": "features[4].flaeche",
 "meldung": "f3 +x zerfällt vor f5 in 2 Teilflächen bei x = -290 (geteilt durch f1) – beim Bau REFERENZ_MEHRDEUTIG; Fläche mit {nahe: [-290, -193, -305.5]} ansprechen (Mitte der größten Teilfläche)",
 "nahe": [-290.0, -193.0, -305.5]}
```

Nicht dazu gehört: eine Änderung der Anker-Auswahl im Compiler. Eine Alternative wäre, bei koplanaren Teilflächen
einfach die größte zu nehmen. Das würde den Fehler beseitigen statt ihn zu melden, ist aber eine eigene Entscheidung.
