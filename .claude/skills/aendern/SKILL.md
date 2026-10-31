---
name: aendern
description: Ändert ein fremdes SolidWorks-Teil (Datei eines Kollegen, nicht von swki gebaut) gezielt an einer Arbeitskopie – Bestand aufnehmen, Revisionspunkte zuordnen, Änderungs-Spec, Freigabe durch den Nutzer, bauen, vorher/nachher prüfen, Prüfer, Ausgabe unter dem Originalnamen. Verwenden, wenn der Nutzer eine .sldprt eines Kollegen revidieren lässt. Eigene swki-Teile ändert der Skill konstruieren.
---

# Ändern (Bestandsdateien, Etappe 1)

Alle Befehle: `.venv\Scripts\python.exe -m swki …` (JSON, Exit 0 = ok). Längen in mm, Winkel in Grad. Vorlage: `tests/referenz/bestand/`
(`eingabe/aufgabe.md`, `lagerdeckel_rev.yaml`). Spec `docs/superpowers/specs/2026-10-25-bestandsdateien-design.md`, Messwerte und Fallen
der API `docs/bestandsdateien/ergebnisse.md`, Teil-Syntax neuer Features Skill `konstruieren`.

Zurück geht **dieselbe Datei**: Baum, Namen, Gleichungen, Konfigurationen und die Absicht des Kollegen bleiben, neu sind nur die
genannten Punkte. Der **Präzisionsschutz** weist das nach. Fünf Regeln gelten in jedem Schritt:

- **Nur die Punkte.** swki und die KI lassen alles andere, wie es ist: Skizzen unbestimmt, Namen, Bemaßungsstil, Gleichungen, Fehler im
  Bestand. Die Punkte nennt der Nutzer.
- **An der Quelle ändern.** Ein gesteuertes Maß ändert sich über seine Gleichung oder Variable.
- **Bereiche eng.** Je Punkt und Stelle eine eigene Box; ein Bereich belegt die Lage (§4).
- **Soll bleibt.** Bereiche, Sollwerte und `folgen` folgen der Absicht, nie den Messwerten. Hält die KI die Spec für falsch, fragt sie den Nutzer.
- **Original nur lesen.** swki kopiert es und schreibt nur in den Arbeitsordner; zurückkopieren tut der Nutzer.

## 1. Abgrenzung

- **Eigene swki-Konstruktionen:** Die Spec ist die Quelle, Skill `konstruieren` bzw. `baugruppe`.
- **Baugruppen** kommen in Etappe 2 (`BESTAND_FORMAT`). **Dateien ohne Baum** (STEP, IGES) gibt es hier nicht; Kaufteile bleiben nur lesen.
- **Teile mit externen Referenzen** (abgeleitet, gespiegelt, im Kontext, verknüpfte Gleichungsdatei) lehnt `aufnehmen` ab
  (`BESTAND_REFERENZ_EXTERN` mit Liste): dem Nutzer nennen.
- **Konstruktionstabelle** (`tabelle: true`): Tabellenmaße und alle `unterdruecken`/`aufheben`-Punkte der Datei sperrt `validieren`
  (`MASS_GESTEUERT`), tabellengesteuerte Unterdrückung lässt sich ohne Excel nicht lesen. Dem Nutzer die Tabelle nennen; nur auf seine
  Anweisung geht es über `skript`.
- **Gleichungsgesteuerte Unterdrückung erkennt swki nicht.** Vor einem `unterdruecken`/`aufheben`-Punkt die `gleichungen` in `bestand.json`
  lesen; nennt eine das Feature, den Nutzer fragen.

## 2. Aufnehmen

1. Ordner `auftraege/<auftrag>/`, die Punkte des Nutzers wörtlich nach `eingabe/aufgabe.md` (der Prüfer liest sie). Ein Teil je Auftrag.
2. `swki bestand aufnehmen <pfad> --auftrag <auftrag>`; `<auftrag>` ist genau der Ordnername.

Die Ausgabe nennt `sha256`, `aufnahme`, Konfigurationen, Variablen, `tabelle`, Features und je Maß Name, Wert, `zustand` (`treibend`,
`gesteuert`, `getrieben`), dazu `skizzen_offen`, `neuaufbau`, `bilder`, `bestand_json` (Rohdaten: Quelle, Gruppe, `punkte` = Modelllage des Maßes).
Bilder ansehen. Fehler in `neuaufbau` und offene Skizzen gehören dem Kollegen: dem Nutzer nennen, sie bleiben. `version_aelter: true` siehe §5.
Hat der Kollege weitergearbeitet (andere SHA-256), entsteht `bestand-<n+1>` und die Spec zieht auf die neue Aufnahme um (`BESTAND_VERALTET`).

## 3. Punkte zuordnen

Je Nutzerpunkt das Ziel im Bestand finden: „das 40er Maß an der Bohrung“ → `D2@Skizze4`, über Wert, Lage (`punkte`) und Feature.

`swki bestand zeige <auftrag> --mass <name>` bzw. `--feature <name>` schreibt ein Bild mit dem rot markierten Maß bzw. Feature; ansehen.
Fertig ist der Schritt, wenn jeder Punkt ein Ziel hat, das im Bild an der gemeinten Stelle sitzt. Passen zwei Ziele oder keines: den Nutzer
fragen, gebündelt in einer Nachricht, mit Bild.

Punkte entstehen nur aus dem, was der Nutzer genannt hat. Eine Revision (`Revision: B`) oder Eigenschaft ändert sich nur als eigener Punkt.

## 4. Änderungs-Spec

Datei `auftraege/<auftrag>/<name>.yaml` nach `schema/aenderung.schema.json`. Anforderungsmaße als `parameter`, wie beim Teil.

```yaml
art: aenderung
name: Lagerdeckel_Rev
bestand: {datei: Lagerdeckel.SLDPRT, sha256: 048e…, aufnahme: 1}       # aus der Ausgabe von aufnehmen
parameter: {A_neu: 45, RA: 12}
punkte:
  - {id: p1, was: "Bohrung 5 mm nach außen", typ: mass, mass: "D2@Skizze4", alt: 40, neu: "=A_neu", konfigurationen?: alle}  # alle | [Namen]
  - {id: p2, typ: gleichung, variable: L, alt: 100, neu: 110, folgen: ["D1@Skizze1"]}   # oder gleichung: <linke Seite>, alt/neu rechte Seite
  - {id: p3, typ: unterdruecken, feature: "Fase1", konfigurationen?: […]}               # oder aufheben
  - {id: p4, typ: loeschen, feature: "Schnitt-Linear austragen1", kinder?: […]}
  - {id: p5, typ: feature, name: "Gewinde M6 Deckel", nach?: "Fase1",                   # Eintrag wie in features einer Teil-Spec, ohne id
     feature: {typ: normbohrung, art: gewinde, groesse: M6, flaeche: {nahe: [45, 0, 20]}, positionen: [["=-50+RA", 24]],
               bezug: {u: "-rand", v: mitte}, tiefe: 10, gewindetiefe: 8}}
  - {id: p6, typ: material, neu: "1.4301"}
  - {id: p7, typ: eigenschaft, name: Revision, neu: "B", konfiguration?: "Variante B"}  # neu: null entfernt
  - {id: p8, typ: skript, datei: skripte/p8.py, luecke: "Endbedingung eines fremden Schnitts"}
bereiche:
  - {punkte: [p1], box: {min: [35.5, -20, 0], max: [50, -10, 20]}}     # Modellkoordinaten des Bestands
  - {punkte: [p3], features: ["Fase1"]}                                # Flächen dieser Features vorher und nachher
pruefung?:
  masse_pruefen:                                                       # Messpunkte: {punkt}, {flaeche: {nahe, normale}}, {feature, flaeche: "+x"}
    - {was: "Länge", von: {flaeche: {nahe: [-50, 0, 10], normale: [-1, 0, 0]}}, zu: {flaeche: {nahe: [60, 0, 10], normale: [1, 0, 0]}}, soll: 110, tol: 0.01}
  volumen_delta: {soll: 1250, toleranz_prozent: 1}
```

- **Namen** wie in der Aufnahme. Ein verknüpftes Maß heißt nach seiner Gruppe (`Bohrung_D@Skizze3`). Punkt-IDs tragen keinen Featurenamen.
- **Gesteuertes Maß:** `gleichung`-Punkt an der Quelle (`quelle` in `bestand.json`). Verknüpfte Maße haben keine Führung: Jedes Mitglied setzt alle, die
  übrigen stehen in `folgen`.
- **`folgen`** nennt alle Maße, die mitgehen; `validieren` rechnet sie aus (Feld `folgen` der Ausgabe). Das ist die Liste für die Freigabe-Vorlage.
- **Anker** neuer Features: `{feature: <Name im Bestand>, flaeche: …}` oder `{nahe}` in Modellkoordinaten, mit `bezug` wie beim Teil. swki legt keine
  Gleichungen an und benennt das neue Feature mit `name`.
- **`loeschen`:** `kinder` nennt erklärte Abhängigkeiten, `GetChildren` sieht aber nicht alles (die Rippe in der Tasche). Unerklärtes zeigt erst der Bau.

**Skript-Punkte** sind der Notausgang für das, was keinen Punkt-Typ hat (Endbedingung, Skizzengeometrie), `luecke` nennt die Lücke:

- `skripte/<id>.py` mit `def bauen(ctx)`; es **gibt neue Features und Skizzen zurück** (`return ctx.skizze(…)[0]`, auch als Liste). Sonst bleibt `baum` `ok: None`.
- Jeder Skript-Punkt steht in einem Bereich. `punkt:<id>` verlangt je Bereich eine Differenz; die Wirkung selbst belegen `masse_pruefen` und der Prüfer.
- Neue Geometrie gehört in einen Punkt `feature`, inneres `typ: skript` dort weist `validieren` ab.

**Bereiche:**

- Je Punkt eine eigene enge Box, je getrennter Stelle eine weitere (zwei Gewinde: zwei Boxen). Eine gemeinsame Box über beide Stellen erlaubte alles dazwischen.
- Alte und neue Lage gehören beide hinein (Bohrung wandert: alte plus neue Stelle). Zwei Punkte an einer Stelle teilen sich einen Bereich.
- Vermutung, nicht gemessen: Differenzkörper verschmelzen, wenn zwei Punkte aneinanderstoßen, etwa eine Fase an einer Kante, die zugleich durch eine
  Längenänderung wandert. Ein Körper über zwei Bereiche passt in keinen. Solche Punkte bekommen einen gemeinsamen Bereich, oder der Nutzer entscheidet.
- `features`-Bereiche passen für ein Feature, das nur verschwindet oder sich ändert, Boxen überall sonst.

## 5. Validieren, Freigabe

`swki validieren <spec>` bis `gueltig`. `hinweise` wie beim Teil abarbeiten.

| Befund | Vorgehen |
|---|---|
| `BESTAND_REFERENZ` | Name aus der Aufnahme nehmen |
| `BESTAND_ALTWERT` | Zuordnung falsch oder Wert anders als genannt: Ziel neu prüfen, sonst den Nutzer fragen |
| `MASS_GESTEUERT` | an der Quelle ändern; Tabelle: §1 |
| `FOLGEN_ABWEICHEND` | die `erwartet`-Liste prüfen und eintragen |
| `KINDER_FEHLEN` | `fehlen` in `kinder` eintragen, in der Freigabe-Vorlage nennen |
| `BEREICH_FEHLT` | Bereich ergänzen |

**Freigabe-Vorlage** (eine Nachricht): je Punkt **Stelle** in Worten, **alt → neu**, **Folgen** (Maße, die mitgehen; mitgelöschte Features), **Konfigurationen**,
**Bereich** und bei fremden Maßen und Features ein **Bild** aus `swki bestand zeige`. Dazu „Selbst entschieden“, offene Skizzen und Fehler im Bestand, und bei einer älteren Datei: „Nach dem Speichern
nur noch mit SolidWorks ≥ <Jahr> lesbar.“ Ohne ausdrückliches OK wird nichts freigegeben. Ein OK gilt für den ganzen Auftrag. Nach dem OK: `swki durchlauf <spec> --freigeben`.

Die Prüfsumme schützt `bestand`, `parameter`, Punkte, `bereiche` und `pruefung`. Bauweg bleiben Anker, `bezug`, `nach`, Skriptdateien und die Reihenfolge der Punkte.
Ältere Datei: `swki durchlauf` baut sie nicht. Nach dem OK zum Hochstufen `swki freigeben <spec>`, `swki bauen <spec> --hochstufen`, `swki pruefen <spec>`, `swki status <spec>`.

## 6. Bauen, prüfen, Prüfer

`swki durchlauf <spec>` baut aus einer frischen Kopie des Bestands (nie auf einem geänderten Lauf) und prüft: Punkte, Baum, Maße, Gleichungen, Konfigurationen, Eigenschaften,
Material, Neuaufbau, Skizzen, externe Referenzen, Differenz je Konfiguration, `feature`-Punkte gegen die freigegebene Kopie. Ausgabe wie beim Teil (`schritt`, `lauf`,
`pruefung.fehlgeschlagen`, `pruefung.ohne_urteil`).

**`ok: None` heißt nicht nachgewiesen und ist nicht bestanden.** Es steht als `nicht_nachgewiesen` in `maengel`. Die Ursache klären (Skript gibt ein Feature nicht zurück, Wert nicht
lesbar, dünner Körper außerhalb der Bereiche), bis der Nachweis steht; ein Bereich oder Soll wird dafür nicht passend gemacht.

Nach bestandenen Code-Prüfungen den Prüfer-Agenten (`subagent_type: pruefer`, `model: sonnet`) mit `pruefer_auftrag` aus der Ausgabe unverändert starten; der Auftrag nennt die
**Vorher-Bilder**, ohne sie sieht der Prüfer keine Änderung. Das JSON-Urteil unverändert nach `auftraege/<auftrag>/protokolle/<spec>.lauf-<n>.pruefer.json`, dann `swki status <spec>`.

`empfehlung: nachbessern`: nur den Bauweg ändern, neuer `swki durchlauf <spec>`, ein Abbruch zählt als Lauf. Ist ein Bereich zu eng oder eine Folge vergessen, ist das eine Änderung der
Anforderung: Nutzer fragen, neue Freigabe. Wiederholt sich eine Lücke, Skill `compiler-erweitern`. `stopp_*`: anhalten, Nutzer informieren.

| Code | Vorgehen |
|---|---|
| `BESTAND_ABWEICHEND` | jemand hat die Bestandskopie verändert: Nutzer fragen, die Kopie bleibt unberührt |
| `BESTAND_VERALTET`, `BESTAND_UNBEKANNT` | Spec auf die jüngste Aufnahme stellen, `alt`-Werte neu prüfen, neue Freigabe |
| `BESTAND_VERSION_AELTER` / `BESTAND_VERSION_NEUER` | §5 / Datei stammt aus neuerem SolidWorks: Nutzer informieren |
| `MANUELL_GEAENDERT` | wie Skill `konstruieren` §5 |
| Mängel `bereich`, `masse`, `baum`, `konfigurationen` | etwas hat sich außerhalb der Punkte geändert: Bauweg korrigieren, Lage aus `differenzen` im Prüfbericht |
| `neuaufbau`, `skizzen` | neuer Fehler bzw. schlechter bestimmt als im Bestand: am Punkt beheben, ältere des Kollegen zählen nicht |

## 7. Ausgabe, Bericht

Nach `bestanden`: `swki bestand ausgabe <spec> [--lauf n]` kopiert die geänderten Dateien unter Originalnamen nach `<arbeitsordner>/<auftrag>/ausgabe/` und listet sie mit Originalpfad. Dann
`swki bericht <spec>`. Dem Nutzer nennen: Ausgabepfad, Originalpfad, Punkte, Prüfer-Urteil, Warnungen, „Wirkung auf Baugruppen nicht geprüft“.

- `BESTAND_LIZENZ`: Rechner A läuft laut API als Student, die Datei trägt das mit. Ob sie sich beim Kollegen mit Vollversion so verwenden lässt, ist nicht gemessen. Vor dem Rückweg an einen
  Kollegen mit dem Nutzer klären.
- `BESTAND_ORIGINAL_GEAENDERT`: Das Original ist neuer als die Aufnahme, Zurückkopieren überschriebe Arbeit des Kollegen. Nutzer fragen, ggf. neu aufnehmen.
- `LAUF_NICHT_BESTANDEN`: Ausgegeben wird nur ein Lauf mit bestandenen Code-Prüfungen und Prüfer-Urteil.
