# Stufe 2c – Normbohrungen, runde Konturen, Endbedingungen, kompakter Feature-Baum

Ergänzung zu [2026-09-26-solidworks-ki-design.md](2026-09-26-solidworks-ki-design.md) (§4 Spezifikation, §5 Compiler,
§6 Prüfung, §9 Skills, §11 Stufen). Stand 2026-09-29, mit dem Nutzer abgestimmt.

## 1. Ziel

Typische Werkzeugbau-Einzelteile (Formplatten, Einsätze, Auswerfer- und Halteplatten) sollen ohne Notausgang baubar
sein, und der Feature-Baum soll so klein bleiben, wie es die Änderbarkeit erlaubt. Stufe 2c liegt zwischen Stufe 2 und
Stufe 3 und ändert nichts an Baugruppen.

Fertig, wenn: die neue Referenz *Auswerferhalteplatte* auf SW 2025 besteht (SW 2026 zusammen mit dem Abschluss von
Stufe 2 auf Rechner B), Buchse und Formplatte unverändert weiter bestehen und alle Unit-Tests grün sind.

## 2. Entscheidungen (mit dem Nutzer, 2026-09-29)

| Frage | Entscheidung |
|---|---|
| Umfang | Normbohrungen, Bögen/Langlöcher, Endbedingungen „bis Fläche“/„Versatz von Fläche“, kompakter Baum |
| Bohrungsarten | M-Gewinde (Regel- und Feingewinde), Senkung für Zylinderschrauben ISO 4762, Kegelsenkung für Senkschrauben ISO 10642, Passbohrung für Zylinderstifte |
| Rohrgewinde | nicht in 2c (Kühlanschlüsse über M-Feingewinde) |
| Norm | ISO; Vorgabe in `config/standard.yaml`, je Bohrung überschreibbar |
| Baum-Regel | Änderbarkeit zuerst: Muster/Spiegeln nur, wenn Anzahl, Abstand oder Symmetrie eine Anforderung ist; sonst so wenige Features wie möglich |
| Format | neuer Feature-Typ `normbohrung` (Ansatz A); `bohrung` bleibt für freie Durchmesser |
| Absicherung | neues Referenzteil; Buchse und Formplatte bleiben unverändert (sichern alte Wege und den Notausgang) |

## 3. Normbohrung

### 3.1 Format

```yaml
- id: f4
  typ: normbohrung
  art: zylinderschraube          # gewinde | zylinderschraube | senkschraube | stift
  groesse: M8                    # gewinde: "M8", "M10x1"; Schrauben: "M8"; stift: Nenndurchmesser, z. B. 8
  flaeche: {feature: f1, flaeche: "+y"}
  positionen: [["=-L/2+20", "=-B/2+20"], ["=L/2-20", "=-B/2+20"]]
  durch: true                    # oder tiefe: <Bohrungstiefe>
  gewindetiefe: 12               # nur art: gewinde, Pflicht wenn nicht durch
  # norm: ISO                    # optional, Vorgabe aus config/standard.yaml (bohrungsnorm: ISO)
```

- `flaeche` und `positionen` wie bei `bohrung`: (u, v) auf der ebenen Fläche, Bohrungsachse senkrecht zur Fläche,
  Instanzen 1, 2, … in Reihenfolge der Positionen (für `masse_pruefen`).
- Genau eines von `durch` und `tiefe`. `gewindetiefe` ≤ `tiefe`.
- Gewinde immer als kosmetisches Gewinde (wie Spike S9b), Kernloch nach Norm.
- Stiftbohrung: Passung H7 nach Norm des Bohrungsassistenten (ISO Dowel Hole).
- Ein Feature je `normbohrung`-Knoten, auch bei mehreren Positionen (Bohrungsassistent mit mehreren Punkten in der
  Positionsskizze). Feature-Name = ID.

### 3.2 Zuordnung zum Bohrungsassistenten (`IFeatureManager.HoleWizard5`)

| art | GenericHoleType (`swWzdGeneralHoleTypes_e`) | FastenerType (`swWzdHoleStandardFastenerTypes_e`, ISO) |
|---|---|---|
| gewinde | `swWzdTap` (4) | `swStandardISOTappedHole` |
| zylinderschraube | `swWzdCounterBore` (0) | `swStandardISOSocketHeadCap` |
| senkschraube | `swWzdCounterSink` (1) | `swStandardISOSocketCTSKFlatHead` |
| stift | `swWzdHole` (2) | `swStandardISODowelHole` |

Norm `swStandardISO` (8). Enum-Werte und Parameterbelegung werden im Spike S10 live bestätigt und dann im Code
festgeschrieben (Größen-Strings wie „M10x1.0“, Durchgangsbohrung „normal“, Endbedingung durch/blind).

### 3.3 Maßtabelle und Sollvolumen

`swki/wissen/bohrungsnormen.yaml` enthält je Art und Größe die Maße, die der Bohrungsassistent verwendet
(Kernloch-/Durchgangs-Ø, Senkungs-Ø und -tiefe bzw. Senkwinkel, Stift-Ø, Bohrspitzenwinkel 118°). Die Werte stammen aus
den ISO-Normen und werden im Spike S10 gegen SolidWorks gemessen; weichen sie ab, gilt der SolidWorks-Wert und die
Abweichung wird in der Tabelle vermerkt.

- `validieren` lehnt eine Größe ab, die nicht in der Tabelle steht (Befund mit den verfügbaren Größen).
- `volumen_auto` rechnet Normbohrungen aus der Tabelle (Kernloch bei Gewinden, kosmetisches Gewinde ohne Volumen).
- Die Tabelle wird nur um Größen erweitert, die live geprüft sind.

### 3.4 Prüfung

Neue Code-Prüfung `normbohrungen`: Für jeden `normbohrung`-Knoten der **freigegebenen Kopie** liest `swki pruefen` das
gleichnamige Feature (`IFeature.GetDefinition` → Bohrungsassistent-Daten) und vergleicht Art, Größe, Norm, Anzahl der
Positionen und durch/Tiefe. Fehlt das Feature oder weicht etwas ab, ist das ein Mangel mit dem Knoten.
Grund: Größen wie „M8“ sind Text, keine Parameter; die Freigabe-Prüfsumme schützt sie nicht. Der Vergleich mit der
freigegebenen Kopie verhindert, dass eine Nachbesserung die Anforderung verschiebt (wie beim Sollvolumen `auto`).

Achsen für `masse_pruefen` wie bei `bohrung`: Positionen aus dem Bauprotokoll, Achse aus der Zylinderfläche. Bei
Senkungen liegen zwei koaxiale Zylinder vor; jeder davon liefert dieselbe Achse.

## 4. Runde Konturen in Skizzen

Neue bzw. erweiterte Skizzenelemente (alle voll bestimmt, Maße per Gleichung an Parameter bindbar wie bisher):

```yaml
- rechteck: {mitte: [0, 0], breite: 120, hoehe: 80, radius: 6}        # Eckradius (optional)
- polygon: {punkte: [[0, 0], [40, 0], [40, 20], [0, 30]], radien: 3}   # ein Wert für alle Ecken oder Liste je Ecke (0 = scharf)
- langloch: {mitte: [0, 0], laenge: 30, breite: 8, winkel: 0}          # laenge = Mittenabstand der Bögen, winkel in Grad zu u
- kontur:                                                             # geschlossener Linienzug aus Linien und Bögen
    start: [0, 0]
    segmente:
      - {linie: [40, 0]}
      - {bogen: [40, 30], mitte: [40, 15]}   # Endpunkt und Mittelpunkt; Richtung gegen den Uhrzeigersinn in (u, v)
      - {linie: [0, 30]}                     # letzter Endpunkt = start (Validierung)
```

- Eckradien über Skizzenverrundung (`ISketchManager.CreateFillet`), Langloch über `CreateSketchSlot`, Bögen über
  `CreateArc` – Parameteranzahlen laut Index: 2, 14, 10. Bestimmtheit und Bemaßung werden im Spike S10 geklärt.
- Validierung: Bogen-Endpunkte gleich weit vom Mittelpunkt (Toleranz 1e-6 mm), Kontur geschlossen, Radius < halbe
  kürzere Nachbarkante, Langloch `breite` > 0 und `laenge` > 0.
- `volumen_auto`: Flächen von Rechteck mit Radius, Polygon mit Radien (konvexe und konkave Ecken), Langloch und Kontur
  analytisch; für Rotationen (Pappus) mit neuen Elementen `None` (Hinweis statt Mangel).

## 5. Endbedingungen

`ende.typ` für `extrusion` und `schnitt` zusätzlich:

```yaml
ende: {typ: bis_flaeche, flaeche: {feature: f1, flaeche: "-y"}}
ende: {typ: versatz_von_flaeche, flaeche: {feature: f1, flaeche: "-y"}, abstand: 5}   # z. B. Restwandstärke 5
```

- `swEndCondUpToSurface` (4) und `swEndCondOffsetFromSurface` (5); die Zielfläche wird über den Flächenanker aufgelöst
  und mit der Auswahlmarke gewählt, die der Spike S10 ermittelt.
- `abstand` ist maßtragend (Hinweis bei fester Zahl, Gleichung an `D1`/Versatzmaß).
- `volumen_auto` gibt `None` (Tiefe hängt von Geometrie ab); das Referenzteil nennt sein Sollvolumen ausdrücklich.

## 6. Kompakter Feature-Baum

### 6.1 Modellierregeln (Skill `konstruieren`)
1. Drehteile als eine Rotation eines Halbschnitts.
2. Gleiche Bohrungen auf derselben Fläche in **einen** Knoten (mehrere Positionen); Normbohrungen statt Bohrung +
   Senkung, sobald eine Schraube, ein Gewinde oder ein Stift gemeint ist.
3. Muster und Spiegeln nur, wenn Anzahl, Abstand oder Symmetrie eine Anforderung ist (dann als Parameter); sonst
   Positionen direkt.
4. Runde Konturen in der Skizze (Eckradius, Langloch, Kontur) statt nachträglicher Verrundung senkrechter Kanten, wenn
   die Kontur nur einmal vorkommt.
5. Tiefen, die sich auf eine andere Fläche beziehen (Restwandstärke, bis zum Boden), mit `versatz_von_flaeche` /
   `bis_flaeche`, nicht als gerechnete Zahl.
6. Kantenverrundungen und Fasen gleichen Maßes in einem Knoten, am Ende des Baums.

### 6.2 Hinweise in `swki validieren`
Neben den festen Maßen meldet `validieren` Zusammenfassbares als `hinweise` mit `art: zusammenfassen`:
- zwei oder mehr `bohrung`-/`normbohrung`-Knoten mit gleicher Fläche und gleichen Maßen bzw. gleicher Art/Größe/Tiefe;
- zwei oder mehr `fase`- bzw. `verrundung`-Knoten mit gleichem Maß;
- `muster_linear`/`muster_kreis`/`spiegeln`, deren Anzahl und Abstand feste Zahlen sind (Regel 3);
- `bohrung` mit `senkung`, deren Maße einer ISO-4762-Senkung aus der Maßtabelle entsprechen (→ `normbohrung`).

Die bestehenden Hinweise erhalten `art: feste_zahl`. Hinweise blockieren nie.

### 6.3 Kennzahl
Prüfbericht und `bericht.md` nennen die Anzahl der Knoten der Spezifikation und der vom Bau erzeugten Features
(ohne Skizzen, Ebenen und Achsen).

## 7. Spike S10 (vor der Umsetzung)

Live gegen SW 2025, Ergebnisse in `docs/stufe0/ergebnisse/s10_*.json` und `docs/stufe0/ergebnisse.md`:
1. `HoleWizard5` für die vier Arten (ISO), Größen-Strings, Endbedingung durch/blind, Gewindetiefe.
2. Mehrere Positionen in **einem** Bohrungsassistent-Feature (Positionsskizze bearbeiten), Punkte voll bestimmt.
3. Maße, die SolidWorks je Größe erzeugt (Zylinder, Kegel, Volumen) → `bohrungsnormen.yaml`.
4. Auslesen der Bohrungsassistent-Daten eines Features (Art, Größe, Norm) für die Prüfung.
5. Skizzen: `CreateFillet` an Rechteck/Polygon-Ecken, `CreateSketchSlot`, `CreateArc` in Konturen – jeweils voll bestimmt.
6. `FeatureCut4`/`FeatureExtrusion3` mit `swEndCondUpToSurface`/`OffsetFromSurface`: Auswahl der Zielfläche (Marke),
   Versatzrichtung.

Ergibt der Spike, dass ein Punkt nicht geht, wird er vor dem Weiterbauen mit dem Nutzer entschieden (Notausgang oder
Umfang kürzen).

## 8. Referenzteil *Auswerferhalteplatte*

Selbst definiert, angelehnt an eine Auswerferhalteplatte im Formenbau, nutzt jedes neue Element mindestens einmal:
Grundplatte (Rechteck mit Eckradius), Befestigung ISO 4762 (4×), Stiftbohrungen (2×), Gewinde M-Regel und
M-Feingewinde, Senkschraube ISO 10642, Tasche mit Eckradius und `versatz_von_flaeche` (Restwandstärke), Langloch-
Durchbruch mit `bis_flaeche`, Aussparung als `kontur` mit Bogen, umlaufende Fase. Maße, Sollvolumen (analytisch aus der
Maßtabelle) und Prüfmaße legt der Plan fest.

## 9. Nicht in 2c

Rohrgewinde, Formschräge, Bohrungen auf gekrümmten Flächen oder schräg, Muster über Skizzenpunkte, variable
Verrundung, Austragung/Loft, Gravur. Kleine offene Punkte aus 2b (`docs/stufe2/ergebnisse.md`) sind eigene Aufgaben.
