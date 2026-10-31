# Paket Bestandsdateien – fremde SolidWorks-Dateien gezielt ändern

Ergänzung zu [2026-09-26-solidworks-ki-design.md](2026-09-26-solidworks-ki-design.md) (§5 Schutzregeln, §6 Prüfung und
Freigabe), [2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md) (Änderungserkennung,
Komponentenquellen), [2026-10-06-kaufteile-step-import-design.md](2026-10-06-kaufteile-step-import-design.md) (Original nur
lesen, Kopie mit SHA-256, Messpunkte ohne Feature-IDs) und
[2026-10-23-bemassungsbezug-design.md](2026-10-23-bemassungsbezug-design.md) (Maßprotokoll, Bezüge). Stand 2026-10-25, mit
dem Nutzer abgestimmt.

## 1. Ziel und Warum

Ein Konstrukteur aus dem Unternehmen schickt dem Nutzer eine SolidWorks-Datei zur Revision. Der Nutzer sieht sie durch,
findet Punkte, die nicht passen, und lässt sie von der KI **gezielt ändern** – von Abständen über Geometrie bis zu Normteilen.
Zurück geht **dieselbe Datei**: Feature-Baum, Namen, Gleichungen, Konfigurationen und Konstruktionsabsicht des Kollegen bleiben,
nur die genannten Punkte sind neu.

Heute kann swki das nicht. Es kennt nur Spec → vollständiger Neubau und fasst nur selbst angelegte Dokumente an. Die KI würde
die fremde Datei ansehen und nachbauen. Dabei ginge der Baum des Kollegen verloren, nicht abbildbare Features (Blech,
Flächen …) landeten im Notausgang, und niemand prüfte, ob der Nachbau außerhalb der Änderung dem Original gleicht.

Der Kern des Pakets ist der **Präzisionsschutz**: swki weist nach, dass sich nur die freigegebenen Stellen geändert haben.

## 2. Ziele, Nicht-Ziele, Anti-Ziele

Ziele:

- Native SolidWorks-Teile und -Baugruppen von Kollegen (SW 2025, normale Dateien auf einem Laufwerk) an einer Kopie
  im Arbeitsordner ändern: Maße, Features (unterdrücken, löschen, neu), Material, Eigenschaften, Normteile und Kaufteile,
  Verknüpfungen.
- Vorher/nachher prüfen: Geometrie, Baum, Maße, Konfigurationen, Eigenschaften und Verknüpfungen ändern sich nur dort, wo die
  Änderungs-Spec es erlaubt.
- Das Ergebnis behält den Originalnamen und die interne Datei-ID, sodass Baugruppen des Kollegen es nach dem Zurückkopieren
  weiter finden.

Nicht-Ziele (dieses Paket):

- Die KI findet die Revisionspunkte nicht selbst; der Nutzer nennt sie. Eine Revision durch die KI ist ein späteres Paket.
- STEP oder andere Dateien ohne Feature-Baum gezielt ändern (direkte Bearbeitung). Kaufteile bleiben „nur lesen“ (3c).
- SOLIDWORKS PDM oder andere Tresore (gibt es beim Nutzer nicht).
- Eigene swki-Konstruktionen ändern: Dort ist die Spec die Quelle (Spec ändern, neu bauen, unveränderte Teile wiederverwenden –
  BTP Umbau 3, `swki/baugruppe/wiederverwendung.py`).
- Zeichnungen der Bestandsdatei nachziehen.

Anti-Ziele (wäre ein Fehlschlag, auch wenn es technisch läuft):

- Das Original auf dem Laufwerk wird geöffnet, verändert, gesperrt oder überschrieben.
- Die Datei wird still nachgebaut, umbenannt, umstrukturiert oder „aufgeräumt“ (Gleichungen entfernt, Skizzen voll bestimmt,
  Features umbenannt, Bemaßungsstil umgestellt).
- Eine Änderung zieht unbemerkt etwas anderes mit (Folge-Features verschoben, eine Konfiguration geändert, eine Verknüpfung
  gebrochen) und die Prüfung meldet „bestanden“.
- Ein gesteuertes Maß wird an der Gleichung vorbei überschrieben, sodass der Kollege beim nächsten Neuaufbau etwas anderes
  bekommt als freigegeben.

## 3. Entscheidungen (mit dem Nutzer, 2026-10-25)

| # | Thema | Entscheidung |
|---|---|---|
| 1 | Original | nur lesen, nie in SolidWorks öffnen; swki kopiert es mit SHA-256 in den Arbeitsordner, Baugruppen samt aller referenzierten Dateien (§5.1) |
| 2 | Grundregel | CLAUDE.md wird bewusst erweitert: „Nur Dokumente anfassen, die selbst angelegt **oder über `swki bestand aufnehmen` als Arbeitskopie aufgenommen** wurden“ |
| 3 | Bestandsaufnahme | `swki bestand aufnehmen` liest Baum, Maße, Gleichungen, Konfigurationen, Material, Eigenschaften, externe Referenzen, Skizzenstatus, Neuaufbau-Fehler, bei Baugruppen Komponenten und Verknüpfungen; Bilder und Vorher-Geometrie (§5.2) |
| 4 | Wer findet die Punkte | der Nutzer; die KI setzt um, was er nennt |
| 5 | Format | Änderungs-Spec `art: aenderung` als Delta (§4) |
| 6 | Neue Features | über die vorhandenen Handler, verankert an der fremden Geometrie; Bemaßungsbezug wie bei eigenen Teilen |
| 7 | Freigabe | **ein** ausdrückliches OK je Änderungsauftrag für alle Punkte (`swki freigeben`) |
| 8 | Absicht des Kollegen | gesteuerte Maße (Gleichung, globale Variable, verknüpftes Maß) werden an der Quelle geändert; Folgeänderungen stehen in der Freigabe-Vorlage (§4.3) |
| 9 | Präzisionsschutz | Vorher/nachher-Vergleich in `swki pruefen` (§7), danach Prüfer mit Vorher-/Nachher-Bildern |
| 10 | Konfigurationen | je Punkt benannt (Vorgabe: alle); verglichen werden alle |
| 11 | Was swki nicht kann | bleibt im Bestand unberührt; nur ein Eingriff daran geht über den Notausgang `skript` |
| 12 | Dateiversion | gleich SW-Jahr: normal; älter: Hinweis, Speichern nur mit OK (Hochstufen ist unumkehrbar); neuer: Abbruch |
| 13 | Revisionsstand, Eigenschaften | nur, wenn ein Punkt es verlangt |
| 14 | Etappen | 1: Einzelteile; 2: Baugruppen (Normteile, Kaufteile, Verknüpfungen, Wirkung eines geänderten Teils) |
| 15 | Referenz | Musterteil und Musterbaugruppe in „fremdem“ Stil, per Skript ohne swki-Compiler erzeugt, als SolidWorks-Dateien ins Git (Ausnahme wie `gm42-10.step`); Negativfälle; einmalige Abnahme an einer echten Kollegen-Datei (nicht ins Git) |
| F1 | Rückweg | **Ausgabe im Arbeitsordner unter dem Originalnamen**; swki listet die geänderten Dateien, der Nutzer kopiert sie selbst zurück. swki schreibt nie außerhalb des Arbeitsordners |
| F2 | Ablage beim Nutzer | normale Dateien auf einem Laufwerk, kein PDM |
| F3 | Normteile | keine Toolbox im Haus; Kollegen verwenden Hersteller-STEP oder keine Normteile. **Neue oder getauschte Normteile kommen aus der swki-Bibliothek** (`swki normteil hole`), Kaufteile aus dem Kaufteil-Katalog (3c). Vorhandene Komponenten des Kollegen bleiben, wie sie sind; ein Punkt darf ausdrücklich eine vorhandene Komponente vervielfältigen („wie Schraube X“) |
| F4 | Konstruktionstabellen | Im Haus werden Varianten nicht über Excel gesteuert (Nutzer, 2026-10-30). **Kein eigener Punkt-Typ:** swki erkennt tabellengesteuerte Maße und Unterdrückungszustände und weist `mass`-, `unterdruecken`- und `aufheben`-Punkte darauf mit `MASS_GESTEUERT` ab; ein seltener Fall läuft über `skript` mit `luecke` |

Eigene Entscheidungen beim Schreiben (vom Nutzer nicht ausdrücklich bestätigt, beim Review prüfen):

- Jeder Lauf beginnt mit einer frischen Kopie der unveränderten Bestandskopie („jeder Lauf baut frisch“). Nachbessern heißt
  also: Bauweg ändern, neuer Lauf ab Bestand – nie Änderungen auf einen schon geänderten Lauf stapeln.
- Das Namensschema `<auftrag>_<name>` gilt nicht für Bestandsdateien; sie behalten Namen und relative Ordnerstruktur.
- `GLEICHUNGEN_VORHANDEN` (Bemaßungsbezug §7) gilt nicht für Bestandsdateien; swki legt dort aber selbst keine neuen
  Gleichungen oder globalen Variablen an (Ausnahme: ein Punkt ändert eine vorhandene, §4.3).
- Neue Features bekommen einen Namen im Stil des Baums des Kollegen (deutsch, sprechend, z. B. „Gewinde M6 Lagerdeckel“); swki
  benennt sie nach dem Bau um und prüft, dass der Name im Teil eindeutig ist.
- Das Löschen eines fremden Features ist erlaubt, aber die Freigabe-Vorlage nennt seine abhängigen Features (Kinder); swki
  verweigert, wenn beim Löschen weitere Features mitgelöscht würden, die der Punkt nicht nennt.
- Ändern von Endbedingungen oder Skizzengeometrie fremder Features hat im ersten Schritt keinen eigenen Punkt-Typ, sondern läuft
  über `skript` mit `luecke`. Wiederholt sich eine Lücke, entsteht der Punkt-Typ über den Skill `compiler-erweitern` (wie bei
  Handlern).
- Ist nur ein Teil gegeben, steht im Bericht „Wirkung auf Baugruppen nicht geprüft“; der Nutzer kann die Baugruppe als Kontext
  mitgeben (Etappe 2, §8.3).
- **Ein Bestand je Auftrag** (ein Teil oder eine Hauptbaugruppe mit ihren Dateien). Mehrere einzelne Teile eines Kollegen sind
  mehrere Aufträge oder – wenn sie zusammengehören – eine Baugruppe (Etappe 2). Damit passen `bestand-<n>` und `lauf-<n>` zur
  heutigen Zählung je Auftrag (`swki/auftrag.py`).
- **Teile mit externen Referenzen** (abgeleitetes oder gespiegeltes Teil, Referenzen im Kontext einer Baugruppe, mit einer
  Datei verknüpfte Gleichungen) lehnt Etappe 1 ab (`BESTAND_REFERENZ_EXTERN` mit Liste), weil SolidWorks beim Öffnen der Kopie
  sonst Dateien des Kollegen vom Originalpfad laden könnte. Etappe 2 kopiert die referenzierten Dateien mit (gleicher Weg wie
  bei Baugruppen) und hebt die Sperre auf. Die Referenzen werden vor dem Öffnen aus der Datei gelesen (Weg im Spike S18b; geht
  das nicht ohne Öffnen, wird mit unterdrücktem Laden der Referenzen geöffnet).
- **Getriebene Maße (Referenzmaße)** steuern nichts und sind weder Punkt-Ziel noch `folgen`; die Prüfung `masse` nimmt sie aus
  und der Prüfbericht nennt ihre Werte vorher/nachher. Abgesichert sind sie über die Geometrie (§7.2).

## 4. Änderungs-Spec (`art: aenderung`)

Eine YAML-Datei je Änderungsauftrag im Auftragsordner (`auftraege/<auftrag>/<name>.yaml`), Schema
`schema/aenderung.schema.json`. Längen in mm, Winkel in Grad. **Namen, Punkte und Zahlen nur zur Veranschaulichung.**

```yaml
art: aenderung
name: Lagerdeckel_Rev
bestand:
  datei: Lagerdeckel.SLDPRT            # relativ zur Bestandskopie (Baugruppe: Hauptdatei)
  sha256: 9a1c…                        # des Originals bei der Aufnahme
  aufnahme: 1                          # Nummer der Bestandsaufnahme (§5.1)
parameter: {A_neu: 45, RA: 12}         # Anforderungsmaße der Punkte (Freigabe-Schutz wie bei Teilen)
punkte:
  - id: p1
    was: "Abstand Bohrung zur linken Kante 40 → 45"
    typ: mass
    mass: "D2@Skizze4"                 # vollständiger SolidWorks-Name aus der Bestandsaufnahme
    alt: 40                            # Sperre: muss im Bestand so stehen, sonst BESTAND_ALTWERT
    neu: "=A_neu"
    konfigurationen: alle              # alle | [Namen]
  - id: p2
    was: "Fase an der Oberkante entfällt"
    typ: unterdruecken                 # unterdruecken | aufheben | loeschen
    feature: "Fase3"
  - id: p3
    was: "Zwei Gewinde M6 für den Deckel ergänzen"
    typ: feature                       # neues Feature über die vorhandenen Handler
    name: "Gewinde M6 Deckel"
    feature: {typ: normbohrung, art: gewinde, groesse: M6, flaeche: {nahe: [0, 30, 20]},
              positionen: [["=-50+RA", 15], ["=-50+RA", -15]], bezug: {u: "-rand", v: mitte}, tiefe: 10,
              gewindetiefe: 8}
  - id: p4
    typ: material
    neu: "1.4301"
  - id: p5
    typ: eigenschaft
    name: Revision
    neu: "B"
  - id: p6
    typ: skript                        # Notausgang
    datei: skripte/p6_endbedingung.py
    luecke: "Endbedingung eines fremden Schnitts ändern"
bereiche:                              # wo sich Geometrie ändern darf (Anforderung, §7.2)
  - {punkte: [p1, p3], box: {min: [-50, -20, 0], max: [-20, 40, 20]}}
  - {punkte: [p2], features: ["Fase3"]}
pruefung:
  masse_pruefen:
    - {was: "Randabstand Gewinde", von: {flaeche: {nahe: [-50, 0, 10], normale: [-1, 0, 0]}},
       zu: {punkt: [-38, 15, 20]}, soll: "=RA", tol: 0.01}
  volumen_delta: {soll: 1250, toleranz_prozent: 1}    # optional
```

*Nachgezogen bei der Umsetzung, 2026-10-31:* `volumen_delta.soll` ist in Etappe 1 nur eine Zahl; `auto` entfällt (Plan, Präzisierung 2).

### 4.1 Punkt-Typen

Etappe 1 (Teile):

| `typ` | Pflichtfelder | Wirkung |
|---|---|---|
| `mass` | `mass`, `alt`, `neu`, `konfigurationen?` | setzt den Wert eines Maßes (Gesteuertes siehe §4.3) |
| `gleichung` | `variable` oder `gleichung`, `alt`, `neu` | ändert eine globale Variable bzw. die rechte Seite einer vorhandenen Gleichung |
| `unterdruecken`, `aufheben` | `feature`, `konfigurationen?` | Unterdrückungszustand |
| `loeschen` | `feature`, `kinder?` | löscht das Feature; `kinder` nennt mitgelöschte Features ausdrücklich |
| `feature` | `name`, `feature` | neues Feature: Inhalt wie ein Eintrag in `features` einer Teil-Spec (alle vorhandenen Handler außer `skript`, Notausgang ist der Punkt `skript`), eingefügt am Ende des Baums oder nach `nach: <Featurename>` |
| `material` | `neu` | Material (Name der SW-Materialdatenbank) |
| `eigenschaft` | `name`, `neu` (`null` = entfernen), `konfiguration?` | benutzerdefinierte Eigenschaft |
| `skript` | `datei`, `luecke` | Notausgang wie bei Teilen (`bauen(ctx)`, AST-Prüfung) |

Etappe 2 (Baugruppen) zusätzlich: `komponente_neu` (Quelle `normteil`/`kaufteil`/`teil` wie Spec 3b/3c oder `wie: <vorhandene
Komponente>`), `komponente_entfernen`, `komponente_ersetzen`, `verknuepfung_neu` (wie Spec 3b), `verknuepfung_wert` (Abstand,
Winkel: `alt`/`neu`), `verknuepfung_loeschen`; Punkte, die ein Teil der Baugruppe ändern, nennen es mit `datei:` (relativer Pfad
in der Bestandskopie) und benutzen die Teil-Typen.

### 4.2 Bezüge auf fremde Geometrie

- Fremde Features, Maße, Komponenten und Verknüpfungen werden mit ihrem **SolidWorks-Namen** aus der Bestandsaufnahme
  genannt (deutsch, wie im Baum).
  *Nachgezogen bei der Umsetzung, 2026-10-31:* Maßname ist `IDimension.FullName` ohne das letzte `@…` (Dokument). Ein verknüpftes Maß heißt nach seiner Gruppe,
  `Bohrung_D@Skizze3`, nicht `D1@Skizze3`; `Parameter` findet nur diesen Namen (S18b).
- In neuen Features gelten die Anker der Teil-Spec. `{feature: <Name>, flaeche|auswahl: …}` löst einen Namen auf, der keine
  Punkt-ID ist, auf das fremde Feature (Kontext wie `kontext_aus_datei`, `swki/pruefung/messen.py`); Punkt-IDs dürfen keinen
  Featurenamen des Bestands tragen. `{nahe: […]}` geht immer (Modellkoordinaten des Bestands, mm).
- Messpunkte in `pruefung.masse_pruefen` wie beim Kaufteil (3c §4.4): `{punkt}`, `{flaeche: {nahe, normale}}`, dazu
  `{feature: <Name>, …}` wie oben.

### 4.3 Gesteuerte Maße und Absicht des Kollegen

Die Bestandsaufnahme markiert je Maß, ob es **gesteuert** ist (Gleichung, globale Variable, verknüpftes Maß,
Konstruktionstabelle) oder **getrieben** (Referenzmaß, §3). Ebenso Unterdrückungszustände, die eine Konstruktionstabelle
steuert.

*Nachgezogen bei der Umsetzung, 2026-10-31:* Verknüpfte Maße sind treibend (Plan, Präzisierung 1): Es gibt kein führendes Maß, jedes Mitglied setzt alle (S18c), die
übrigen stehen in `folgen`. `DrivenState` ist bei Gleichung und Referenzmaß gleich 1: Gesteuert ist, was links in einer Gleichung
steht oder `IsDesignTableDimension` meldet; getrieben der Rest mit `DrivenState` 1 (S18b). `SetSystemValue3` meldet auf einem
gesteuerten Maß Erfolg, der nächste Neuaufbau nimmt den Wert still zurück (S18c).
**Offen:** Tabellengesteuerte Unterdrückungszustände lassen sich ohne Excel nicht lesen (S18b, Ergebnisse §1). Maße gehen ohne
Excel.
*Nachgezogen bei der Umsetzung, 2026-10-31 (Abschlussreview):* Steht das Feature links in einer Gleichung, ist `unterdruecken`/`aufheben` ebenfalls `MASS_GESTEUERT`.
Dafür gibt es in Etappe 1 keinen Punkt-Weg: Der Vergleich `konfigurationen` lässt einen Wechsel des Unterdrückungszustands nur aus `unterdruecken`/`aufheben` zu, ein `gleichung`-Punkt
endete in einem Mangel, den kein Nachbessern behebt. Die Meldung nennt die Gleichung, die KI fragt den Nutzer und umgeht den Befund nicht über einen `gleichung`- oder `skript`-Punkt.

- Ein `mass`-Punkt auf ein gesteuertes Maß ist ein Befund `MASS_GESTEUERT` (`validieren`) mit der steuernden Quelle; die KI
  schreibt stattdessen einen `gleichung`-Punkt an der Quelle bzw. ändert das führende verknüpfte Maß. Ist die Quelle eine
  Konstruktionstabelle, gibt es keinen Quell-Punkt (Entscheidung F4): Der Befund gilt auch für `unterdruecken` und `aufheben`,
  die KI nennt dem Nutzer die Tabelle, und nur auf seine Anweisung geht die Änderung über `skript` mit `luecke`.
- Die Freigabe-Vorlage nennt je Punkt die **erwarteten Folgeänderungen** (alle Maße, die über dieselbe Variable oder
  Verknüpfung mitgehen, und die Konfigurationen), aus der Bestandsaufnahme abgeleitet. Sie stehen in der Spec als
  `folgen: ["D1@Skizze7", …]` am Punkt; `swki pruefen` erlaubt genau diese Folgeänderungen (§7.1).
- swki entfernt, ersetzt oder ergänzt keine Gleichungen, Beziehungen oder Bemaßungen des Kollegen außer über einen Punkt.

### 4.4 Validieren (ohne SolidWorks)

`swki validieren <aenderung.yaml>` (Weiche nach `art`, wie bei Kaufteilen):

1. Schema.
2. Bestandsaufnahme vorhanden und passend zu `bestand.sha256` (`BESTAND_UNBEKANNT`).
3. Gegen die Bestandsaufnahme (`bestand.json`, §5.2): genannte Maße, Features, Variablen, Konfigurationen, Komponenten,
   Verknüpfungen existieren (`BESTAND_REFERENZ`); `alt` stimmt mit dem aufgenommenen Wert überein (`BESTAND_ALTWERT`);
   gesteuerte Maße (`MASS_GESTEUERT`); `folgen` vollständig und nicht zu viel (`FOLGEN_ABWEICHEND`, berechnet aus der
   Aufnahme); `loeschen` nennt alle Kinder (`KINDER_FEHLEN`).
   *Nachgezogen bei der Umsetzung, 2026-10-31:* `GetChildren` kennt nur erklärte Abhängigkeiten. Die Rippe hängt geometrisch an der Tasche und steht dort nicht; `KINDER_FEHLEN`
   ist darum eine Vorprüfung, den Rest fängt der Neuaufbau-Vergleich beim Bau (S18b, S18c).
4. `feature`-Punkte: der Feature-Inhalt wird wie in einer Teil-Spec validiert (Schema, Normbohrungsgrößen, Bezüge, Hinweise
   `feste_zahl`/`bezug`).
5. Jeder Punkt, der Geometrie ändern kann (`mass`, `gleichung`, `unterdruecken`, `aufheben`, `loeschen`, `feature`, `skript`,
   Komponenten-Punkte), steht in mindestens einem `bereich` (`BEREICH_FEHLT`).
6. Dateiversion (§5.1) als Befund bzw. Hinweis.

*Nachgezogen bei der Umsetzung, 2026-10-31 (Abschlussreview):* Gleichungen und globale Variablen rechnen in der Einheit der Datei. Ist das Einheitensystem nicht MMGS, ist jeder
`gleichung`-Punkt ein Befund `BESTAND_EINHEIT` mit der Dokumenteinheit, `aufnehmen` nennt sie. Maße betrifft das nicht, sie gehen in Metern an SolidWorks.

### 4.5 Freigabe

`swki freigeben <aenderung.yaml>` nur nach ausdrücklichem OK des Nutzers. Die Freigabe-Vorlage zeigt je Punkt in Worten, was
sich ändert, den Altwert, die Folgeänderungen, die Konfigurationen und die Bereiche, dazu je `mass`-Punkt ein Bild mit
hervorgehobenem Maß (`swki bestand zeige`, §5.3).

*Nachgezogen bei der Umsetzung, 2026-10-31 (Abschlussreview):* `freigeben` prüft voll wie §4.4 und verweigert bei Befunden: `swki bauen` prüft die Punkte nicht gegen die Aufnahme, und
der Weg für ältere Dateien (`swki freigeben`, `swki bauen --hochstufen`) führt an `swki validieren` vorbei.

Grundsatz der Prüfsumme: **Was geändert wird und wo sich die Geometrie ändern darf, ist Anforderung; wie swki es erreicht, ist
Bauweg.** Geschützt sind `bestand`, `parameter`, alle Punkte (außer Bauweg-Feldern), `bereiche`, `pruefung`. Bauweg sind die
Anker und `bezug` neuer Features, `nach`, die Skriptdateien und die Reihenfolge der Punkte, soweit sie die Wirkung nicht
ändert; der Plan legt die genaue Feldliste fest. Freigabe-Kopie `<spec>.freigegeben.yaml` und `FREIGABE_VERALTET` wie bisher.

## 5. Bestand aufnehmen

### 5.1 Kopie

`swki bestand aufnehmen <pfad> --auftrag <auftrag>`:

1. Endung `.sldprt` (Etappe 1) bzw. `.sldasm` (Etappe 2), sonst `BESTAND_FORMAT`.
2. **Version** ohne Öffnen (`ISldWorks.VersionHistory`, 1 Parameter laut Index): neuer als das laufende SW-Jahr →
   `BESTAND_VERSION_NEUER`, Abbruch. Älter → Hinweis `version_aelter` in der Aufnahme; `swki bauen` speichert dann nur mit
   `--hochstufen` (der Nutzer bestätigt, dass die Datei danach nur noch mit SW ≥ <Jahr> lesbar ist).
3. SHA-256 des Originals. Kopie per Datei-Kopie (`shutil.copy2`) nach `<arbeitsordner>/<auftrag>/bestand-<n>/`, Original wird
   nicht in SolidWorks geöffnet. Die Kopie wird schreibgeschützt markiert. Baugruppen: alle referenzierten Dateien
   (Abhängigkeiten aus der Datei gelesen, ohne das Original zu öffnen – Weg im Spike S18) mit relativer Ordnerstruktur; was
   außerhalb des Ordners des Originals liegt, unter `extern/` mit Zuordnung in `bestand.json`. Fehlende Referenzen →
   `BESTAND_REFERENZ_FEHLT` (Liste).
   *Nachgezogen bei der Umsetzung, 2026-10-31:* `VersionHistory` liefert z. B. `18000[2025/268]`, Vergleich gegen `GetLatestSupportedFileVersion`.
   `GetDocumentDependencies2(pfad, True, False, False)` geht ohne Öffnen (gespeicherte Pfade, Paare Titel/Pfad, `None` ohne
   Referenz). Die schreibgeschützte Kopie öffnet still mit Warnung 2, `Save3` scheitert mit Fehler 2 (S18b).
4. Erneutes `aufnehmen` derselben Datei: gleiche SHA-256 → vorhandene Aufnahme; andere → neue Aufnahme `bestand-<n+1>`
   (der Kollege hat weitergearbeitet); eine Spec auf die alte Aufnahme meldet `BESTAND_VERALTET`.

### 5.2 Bestandsaufnahme (`bestand.json`, nur lesend in SolidWorks)

Die Kopie wird geöffnet und gelesen, nicht gespeichert:

- Datei: Name, SHA-256, Versionsverlauf, Einheitensystem, Konfigurationen (aktive zuerst), externe Referenzen
  (`ListExternalFileReferences`), Material und Eigenschaften (Datei und je Konfiguration).
- Baum: je Feature Name, Typ (`GetTypeName2`), Eltern/Kinder, Unterdrückung je Konfiguration, Neuaufbau-Fehler und -Warnungen
  (What's Wrong), Skizzen mit Bestimmtheitsstatus.
- Maße: vollständiger Name, Wert (mm/Grad) je Konfiguration, Feature/Skizze, gesteuert ja/nein mit Quelle, Lage (Modellpunkt
  der bemaßten Elemente).
- Gleichungen und globale Variablen (`GetEquationMgr`).
- Geometrie je Konfiguration: Körper, Volumen, Hüllquader, Schwerpunkt, Vorher-Geometrie für §7.2 (Form legt der Spike fest:
  gespeicherte Körper oder STL).
- Baugruppe (Etappe 2): Komponenten mit Datei, Konfiguration, fixiert/frei, Verknüpfungen mit Typ, Partnern, Wert, Fehlern,
  Bestimmtheit, statische Kollisionen.
- Bilder Iso/Vorne/Oben/Rechts.

*Nachgezogen bei der Umsetzung, 2026-10-31:* Werte je Konfiguration nur durch Umschalten lesen: `GetSystemValue3` mit Namen liefert 0 für nicht aktive Konfigurationen.
Maße unterdrückter Features sind lesbar. Lage aus `IDimension.ReferencePoints` (Abweichung bis 0,1 mm). Die Bestandskopie bleibt die
Vorher-Geometrie, eine eigene Ablage ist nicht nötig. Lesen geht unsichtbar (1,4 statt 5,3 s, kein Fenster mit 2,3 GB); nur die Bilder
brauchen ein Fenster (S18b, S18d).

Ausgabe kompakt (Zusammenfassung in JSON, Rohdaten in `bestand.json`), damit die KI die Zuordnung „das 40er Maß an der Bohrung“
→ `D2@Skizze4` trifft.

### 5.3 `swki bestand zeige`

`swki bestand zeige <auftrag> (--mass <name> | --feature <name>)`: Bild der Bestandskopie mit hervorgehobenem Maß bzw. Feature
(Weg im Spike). Für die Zuordnung und die Freigabe-Vorlage.

*Nachgezogen bei der Umsetzung, 2026-10-31:* Feature: `Select2` genügt. Maß: Bloße Auswahl zeigt nichts. Im offenen Dokument Toggle 31 und 32 einschalten
(`Extension.SetUserPreferenceToggle`), Ansicht zur Skizzenebene, `IAnnotation.Color` rot setzen, PNG, nicht speichern (S18e, Lauf `e2`). Auswahl allein hebt das Maß nur schwach hervor.

## 6. Bauen

`swki bauen <aenderung.yaml>` (Weiche nach `art`):

1. Freigabe prüfen; Änderungserkennung des letzten Laufs wie bisher (`MANUELL_GEAENDERT`).
2. Bestandskopie unverändert? (SHA-256 gegen `bestand.json`, sonst `BESTAND_ABWEICHEND`.) Frische Kopie nach
   `<auftrag>/lauf-<n>/` (gleiche Struktur, Schreibschutz aufheben).
3. Öffnen, Punkte in Reihenfolge anwenden; nach jedem Punkt Neuaufbau und What's Wrong; **neu** ist nur, was in der Aufnahme
   nicht stand. Neuer Fehler → Abbruch mit Punkt-ID, Schritt, Code, SW-Meldung (wie Knoten). `alt` wird vor dem Setzen live
   gegengeprüft.
4. Speichern **an Ort und Stelle** (kein Speichern unter neuem Namen; die interne Datei-ID bleibt – Spike S18a), Protokoll mit
   Maßprotokoll der Punkte (`Kontext.mass`), SHA-256 aller Dateien des Laufs.

*Nachgezogen bei der Umsetzung, 2026-10-31:* Gemessene Fallen (S18c): Option `swThisConfiguration` trifft bei einem vor dem Umschalten geholten `IFeature` die alte
Konfiguration, darum `SetSuppression2` nur mit `swSpecifyConfiguration` und Namen. Ein Feature, das in einer anderen Konfiguration
als der ersten entsteht, ist in der ersten unterdrückt: Punkt `feature` hebt das in allen Konfigurationen auf. Doppelte Namen
scheitern still, Namen zurücklesen. `ReorderFeature` (für `nach`) beschädigt bei Rückgabe False die aktive Konfiguration dauerhaft (Feature-Reihenfolge gilt je
Konfiguration, Fehler und Volumen ändern sich nur dort, `Save3` meldet Erfolg, in anderen Konfigurationen ist nichts zu sehen): Lauf
abbrechen; vor dem Speichern Fehler, Volumen und Baum in allen Konfigurationen prüfen (`c3`). Löschen mit
`DeleteSelection2(3)`, Baum vorher/nachher vergleichen; eine Skizze mit Kind lässt sich so nicht löschen. Vor dem Speichern auf die
aufgenommene aktive Konfiguration zurück, `Save3` übernimmt die gerade aktive. Handler laufen auf fremden Flächen (`normbohrung`
mit Randbezug). `Save3` hält die Datei-ID; `SaveAs3` tut das gemessen ebenfalls (S18a), gespeichert wird trotzdem an Ort und Stelle.
`ReorderFeature` wirkt auch bei Erfolg nur in der aktiven Konfiguration, `nach` läuft deshalb je Konfiguration. `material` setzt je
Konfiguration über den Namen, `""` träfe nur die aktive. Nach einem Fehler wird nie gespeichert, anders als beim Teil. Vor dem
Speichern muss jedes Bestandsfeature noch da sein, außer ein `loeschen`-Punkt hat es genommen, das gilt auch für Skripte. `alt` wird
je Konfiguration gegengeprüft, auch bei Gleichungen.

Schutzregeln im Code: swki öffnet und speichert nur Dateien unter `<arbeitsordner>/<auftrag>/lauf-<n>/`; die Bestandskopie wird
nur zum Lesen geöffnet; das Original nie.

## 7. Prüfen – der Präzisionsschutz

`swki pruefen <aenderung.yaml> --lauf n` liest Lauf und Bestandskopie (beide nur lesend) und vergleicht.

### 7.1 Vorher/nachher ohne Geometrie

| Prüfung | Soll |
|---|---|
| `punkt:<id>` | Wirkung je Punkt: Maß hat den neuen Wert (in den genannten Konfigurationen, sonst den alten), Feature unterdrückt/da/weg, Material/Eigenschaft gesetzt |
| `baum` | gleiche Features (Name, Typ, Reihenfolge, Eltern) wie im Bestand, außer neuen, gelöschten und den genannten Kindern |
| `masse` | jedes treibende Maß außer den geänderten und ihren `folgen` hat seinen Bestandswert, in allen Konfigurationen (getriebene Maße nur berichtet) |
| `gleichungen` | unverändert außer `gleichung`-Punkten |
| `konfigurationen` | gleiche Konfigurationen; Unterdrückungszustände nur wie die Punkte |
| `eigenschaften`, `material` | unverändert außer Punkten |
| `neuaufbau` | keine neuen Fehler oder Warnungen gegenüber der Aufnahme |
| `skizzen` | keine Skizze schlechter bestimmt als im Bestand (unterbestimmte des Kollegen bleiben unterbestimmt, das ist kein Mangel) |
| `externe_referenzen` | keine neuen; keine, die aus dem Lauf-Ordner herauszeigen |
| `pruefung.masse_pruefen` | wie bei Teilen |

*Nachgezogen bei der Umsetzung, 2026-10-31 (Task 10, Prüfer):* `punkt:<id>` eines `feature`-Punkts misst gegen die freigegebene Kopie wie beim Teil, je Konfiguration, und
trägt `ist`/`soll`: Normbohrung (Größe, Tiefe, Gewindetiefe, Anzahl, Achsen gegen `positionen`), Verzahnung, Formschräge. Ohne Messung ist ein messbarer Typ
nicht bestanden. Andere Typen bleiben ungemessen, der Eintrag nennt das. Ein Gewinde sieht man weder in der Differenz noch im Bild.

### 7.2 Geometrie

Je Konfiguration und Körper: **Differenz vorher/nachher** in denselben Modellkoordinaten (keine Ausrichtung wie im Messstand –
eine Verschiebung ist hier ein Fehler). Bevorzugter Weg: exakte Körper-Differenz an Kopien (`IBody2.Copy2`, `Operations2`
Subtraktion in beide Richtungen; Spike S18d), Rückfall STL-Abstand (`werkzeuge/messstand/vergleich.py` ohne Ausrichtung).

*Nachgezogen bei der Umsetzung, 2026-10-31:* Exakte Differenz trägt (S18d): unverändert leer ohne Splitter, Ø1-Bohrung auf 6 Stellen, Flächenversatz bis 0,05 µm, 0,05 s, an
unsichtbaren Dokumenten. Der Körper ist genauer als die Toleranz; ob er sie überschreitet, entscheidet seine Dicke
(`2·Volumen/Fläche`, kleinste Box-Kante). **Der STL-Rückfall ist nicht gleichwertig:** 0,03 mm Rauschen bei gleicher Geometrie, Ø1
und 50 µm gehen darin unter, und STL-Export am unsichtbaren Dokument bringt SolidWorks zum Absturz. Er taugt nur als Hinweis, nicht als
Nachweis der 0,01 mm.

*Nachgezogen bei der Umsetzung, 2026-10-31 (Task 8):* Unter der Toleranz liegt ein Körper nur, wenn seine kleinste Box-Kante darunter liegt;
sie allein beweist die Dicke. `2·2·Volumen/Fläche` schätzt die größte Dicke einer dünnen Schicht aus dem Mittel (Sichel, Keil), gilt aber für
den ganzen Körper, ein Buckel an einer dünnen Schicht verschwindet darin: Ein Körper außerhalb aller Bereiche, der nur so dünn erscheint,
ergibt `ok: None`, sonst Mangel `bereich`. Ein `features`-Bereich prüft gegen die Vereinigung der Feature-Boxen, die den Körper berühren,
nicht gegen den Hüllquader aller Features, zwei Fasen an beiden Enden erlauben keine Tasche dazwischen. Je Bereich eines Punkts muss eine
Abweichung darin liegen, Berühren reicht nicht. `punkt:<id>` eines `skript`-Punkts ist ok, wenn das Skript durchlief und je Bereich eine
Differenz liegt; ohne Bereich ändert er keine Geometrie. Neue Features, die `bauen(ctx)` zurückgibt, gelten in `baum` als erklärt. Das Bild mit
Differenzkörpern entfällt in Etappe 1: Differenzliste und Vorher-/Nachher-Bilder genügen.

*Nachgezogen bei der Umsetzung, 2026-10-31 (Abschlussreview):* Decken die berührten Feature-Boxen den Hüllquader des Körpers, liegt er im Bereich. Sonst ist er ein Mangel, wenn er
über ihren Hüllquader ragt oder sich zwei von ihnen nicht berühren (ein Körper über zwei entfernte Features hätte alles dazwischen mitgeändert), und `ok: None`, wenn nur eine Ecke
frei bleibt: Ob dort Körper liegt, zeigen achsparallele Boxen nicht.

- Jeder Differenzkörper (bzw. jede abweichende Stelle über der Toleranz, Vorgabe 0,01 mm) muss vollständig in einem `bereich`
  liegen: `box` (achsparallel in Modellkoordinaten, mm) oder `features` (Hüllquader der Flächen dieser Features vorher und
  nachher, mit Toleranz). Sonst Mangel `bereich` mit Lage und Volumen der Abweichung.
- `volumen_delta`: Soll als Zahl; optional. *Nachgezogen bei der Umsetzung, 2026-10-31:* `auto` entfällt in Etappe 1 (Plan, Präzisierung 2).
- Bereiche ohne Differenz sind ein Mangel `punkt:<id>`, wenn der Punkt Geometrie ändern sollte.
- Der Prüfbericht nennt je Differenz Lage, Hüllquader, Volumen und zugeordneten Bereich; dazu Vorher-/Nachher-Bilder derselben
  Ansichten und ein Bild mit den Differenzkörpern (wenn der Spike das hergibt).

### 7.3 Prüfer

`.claude/agents/pruefer.md` bekommt eine **Änderungs-Checkliste**. Eingabe: Nutzerauftrag, freigegebene Änderungs-Spec,
Prüfbericht, Vorher-/Nachher-Bilder – keine Bauprotokolle, keine Skripte. Prüft: jeder Punkt sichtbar umgesetzt und an der
gemeinten Stelle; nichts sonst verändert (Bilder, Differenzliste); Folgeänderungen plausibel; nichts „aufgeräumt“. Urteil wie
bisher, Mängel mit Punkt-IDs oder Prüfungs-ID. Nachbessern, Abbruch ohne Fortschritt und `max_nachbesserungen` wie bisher.

## 8. Etappe 2 – Baugruppen

### 8.1 Aufnahme und Lauf

*Nachgezogen bei der Umsetzung, 2026-10-31:* S18g: Datei-Kopie aller Dateien reicht, die Datei neben der Baugruppe hat Vorrang. **Fehlt eine, lädt SolidWorks still vom
gespeicherten Pfad, also vom Original (Warnung 0).** Darum nach dem Öffnen jeden `GetPathName` gegen den Lauf-Ordner prüfen. Nur
das geänderte Teil speichern: Baugruppe und andere Teile bleiben byteweise gleich. Teil neben alter Baugruppe: nur Warnung 32. Mit
`OpenDoc6`-Option 64 öffnen, sonst sind Komponenten leicht geladen und `GetModelDoc2` liefert `None`. Pack and Go ist über IDispatch
nicht erreichbar und nicht nötig; `ReplaceReferencedDocument` geht, ändert aber die SHA-256 der Baugruppe.

Wie §5–§7 mit der Hauptbaugruppe; alle referenzierten Dateien liegen in der Bestandskopie und im Lauf-Ordner. Die Kopie im Lauf
verweist nur auf Dateien im Lauf-Ordner (Spike S18g). Nach dem Bau prüft swki je geänderter Datei die SHA-256 gegen die
Bestandskopie: was sich nicht ändern sollte, darf sich nicht ändern (auch nicht durch bloßes Speichern; Baugruppe nur speichern,
was die Punkte ändern – Weg im Spike).

### 8.2 Komponenten und Verknüpfungen

- Neue Normteile über `swki normteil hole`, Kaufteile über `swki kaufteil hole`, eigene Teile über eine Teil-Spec im Auftrag;
  die Dateien kommen in den Lauf-Ordner neben die Baugruppe (Unterordner `swki/`, Name nach Bibliotheksschlüssel).
- `wie: <Komponente>` vervielfältigt eine vorhandene Komponente des Kollegen (gleiche Datei, gleiche Konfiguration).
- Verknüpfungen wie Spec 3b; Partner in fremden Komponenten über `{komponente: <SW-Komponentenname>, nahe | feature | referenz}`.
- Gewindepaarung und Kollision: nur **neue** Kollisionen und Paarungen neuer Normteile sind Mängel; Kollisionen, die der Bestand
  schon hatte, stehen im Bericht.

### 8.3 Prüfungen zusätzlich

| Prüfung | Soll |
|---|---|
| `komponenten` | gleiche Komponenten außer Punkten (Datei, Konfiguration, Lage der nicht betroffenen) |
| `verknuepfungen` | gleiche Verknüpfungen und Werte außer Punkten; keine neuen Fehler |
| `bestimmtheit` | Freiheitsgrade je Komponente wie im Bestand, außer den Punkten |
| `kollision` | keine neue statische Kollision |
| `lage` | nicht betroffene Komponenten haben dieselbe Transformation |

Ändert ein Punkt ein Teil, das in der Baugruppe steckt, laufen die Teilprüfungen (§7) für dieses Teil und die Baugruppenprüfungen
für die Baugruppe.

## 9. Ausgabe

`swki bestand ausgabe <aenderung.yaml> [--lauf n]` – nur für einen geprüften Lauf mit bestandenem Prüfer-Urteil:

1. Liste der Dateien, deren SHA-256 sich gegenüber der Bestandskopie geändert hat, mit relativem Pfad und Originalpfad; die
   unveränderten werden nicht ausgegeben.
2. Kopie der geänderten Dateien nach `<arbeitsordner>/<auftrag>/ausgabe/` mit Originalnamen und Struktur.
3. Gegenprobe am Original: hat es sich seit der Aufnahme geändert (SHA-256), Warnung `BESTAND_ORIGINAL_GEAENDERT` – das
   Zurückkopieren würde Arbeit des Kollegen überschreiben.
4. Der Nutzer kopiert selbst zurück. swki schreibt nie außerhalb des Arbeitsordners.

*Nachgezogen bei der Umsetzung, 2026-10-31 (Abschlussreview):* Der Bau schreibt `bestand: {sha256, aufnahme}` ins Protokoll. `ausgabe` und `pruefen` verweigern mit `BESTAND_VERALTET` einen
Lauf, der nicht zu `bestand` der Spec passt oder das Feld nicht trägt: Zieht die Spec auf eine neue Aufnahme um, passt das Original wieder zur Aufnahme und die Warnung aus Schritt 3
schweigt, dem alten Lauf fehlt aber die Arbeit des Kollegen.

`swki bericht` nennt Punkte, Folgeänderungen, Differenzen, Prüfer-Urteil, Ausgabeliste und „Wirkung auf Baugruppen nicht
geprüft“, wo zutreffend.

## 10. Fehlercodes

| Code | Wann |
|---|---|
| `BESTAND_FORMAT` | Endung nicht `.sldprt` (bzw. `.sldasm` ab Etappe 2) |
| `BESTAND_ANDERE_DATEI` | Auftrag hat schon eine andere Datei aufgenommen |
| `BESTAND_NICHT_LESBAR` | Original fehlt oder ist gesperrt, Kopie weicht vom Original ab, kein Versionsverlauf, Konfiguration nicht aktivierbar (bei `ausgabe` Warnung) |
| `BESTAND_VERSION_NEUER` | Datei in neuerem SW-Jahr gespeichert |
| `BESTAND_VERSION_AELTER` | `swki bauen` an einer Datei aus älterem SW-Jahr ohne `--hochstufen` |
| `BESTAND_REFERENZ_FEHLT` | referenzierte Datei nicht gefunden |
| `BESTAND_REFERENZ_EXTERN` | Teil mit externen Referenzen (Etappe 1) |
| `BESTAND_UNBEKANNT`, `BESTAND_VERALTET` | keine bzw. nicht die neueste Aufnahme zur Spec; `BESTAND_VERALTET` auch für einen Lauf aus einem anderen Stand als dem der Spec (§9) |
| `BESTAND_ABWEICHEND` | Bestandskopie verändert |
| `BESTAND_ORIGINAL_GEAENDERT` | Original seit der Aufnahme geändert (Warnung bei `ausgabe`) |
| `BESTAND_LIZENZ` | Lauf nicht mit einer Vollversion oder Lizenz unbekannt (Warnung bei `ausgabe`) |
| `LAUF_NICHT_BESTANDEN` | `ausgabe` eines Laufs ohne bestandene Code-Prüfungen und Prüfer-Urteil |
| Befunde `validieren` | `BESTAND_REFERENZ`, `BESTAND_ALTWERT`, `BESTAND_EINHEIT`, `MASS_GESTEUERT`, `FOLGEN_ABWEICHEND`, `KINDER_FEHLEN`, `BEREICH_FEHLT` |
| Mängel `pruefen` | `punkt:<id>`, `baum`, `masse`, `gleichungen`, `konfigurationen`, `neuaufbau`, `skizzen`, `externe_referenzen`, `bereich`, Etappe 2 §8.3 |

Ein Prüfmangel ist ein Fehler im Bauweg oder in der Spec: Die KI passt keine Bereiche oder Sollwerte an Messwerte an; hält sie
die Spec für falsch (Bereich zu eng, Folgeänderung vergessen), fragt sie den Nutzer.

## 11. Spike S18 (vor dem Plan-Code)

Live, nur nach Freigabe durch den Nutzer und nie parallel zu einer anderen SolidWorks-Arbeit. Vor jedem neuen API-Aufruf
`swki api methode` / `enum`; nur Aufrufe aus SW 2025.

- **S18a Datei-ID:** Teil kopieren, Kopie öffnen, Maß ändern, an Ort und Stelle speichern; eine Baugruppe, die auf das Original
  verweist, öffnet die zurückkopierte Datei ohne Warnung zur internen ID. Gegenprobe: „Speichern unter“ bricht das.
  *Nachgezogen bei der Umsetzung, 2026-10-31:* Erster Teil bestätigt. Die Gegenprobe nicht: `SaveAs3` (neuer Name, anderer Ordner, Copy) erhält die ID ebenfalls; nur ein neu
  angelegtes Dokument löst IdMismatch aus (Warnung Bit 1). Ergebnisse aller Zeilen: `docs/bestandsdateien/ergebnisse.md` §1.
- **S18b Aufnahme:** `VersionHistory` ohne Öffnen; Abhängigkeiten einer Baugruppe ohne Öffnen; Baum, Maße mit Namen und Werten
  je Konfiguration, gesteuert/getrieben/verknüpft erkennen (auch über eine Konstruktionstabelle, ohne Excel zu starten),
  Gleichungsmanager, What's Wrong, externe Referenzen.
- **S18c Ändern:** Maß setzen in allen bzw. einer Konfiguration (`SetSystemValue3` o. ä.), globale Variable ändern,
  `SetSuppression2` (3 Parameter), Feature löschen mit/ohne Kinder, ein vorhandener Handler (Normbohrung mit `rand`-Bezug) auf
  einer fremden Fläche, Umbenennen.
- **S18d Differenz:** `Copy2` + `Operations2` (3 Parameter) in beide Richtungen; Ergebnis bei unveränderter Geometrie (leer?
  Splitter an deckungsgleichen Flächen?), bei kleiner Bohrung, bei verschobener Fläche; Zeit und Speicher an einem mittleren
  Teil; je Konfiguration; Vergleich mit STL ohne Ausrichtung.
- **S18e Bild** mit hervorgehobenem Maß bzw. Feature.
- **S18f Musterdateien:** Skript, das Musterteil und Musterbaugruppe in „fremdem“ Stil erzeugt (ohne swki-Compiler: globale
  Variable mit Gleichung, verknüpftes Maß, zwei Konfigurationen, unterbestimmte Skizze, Feature-Typ, den swki nicht kennt,
  z. B. Rippe oder Wandung, eine importierte STEP-Komponente in der Baugruppe).
- **S18g Baugruppe:** Pack and Go (`GetPackAndGo`) bzw. Datei-Kopie plus Pfadumleitung in den Lauf-Ordner; Original-Dateien
  unverändert (SHA-256 vorher/nachher); nur geänderte Dateien speichern.

## 12. Referenz und Tests

`tests/referenz/bestand/`:

- **Musterteil** und **Musterbaugruppe** (S18f) als SolidWorks-2025-Dateien im Git (Ausnahme von „erzeugte SolidWorks-Dateien
  nicht ins Git“ wie `gm42-10.step`, damit SHA-256 und Aufnahme fest bleiben); das Erzeugungsskript bleibt die Quelle.
  *Nachgezogen bei der Umsetzung, 2026-10-31:* Dritte Datei `gm42-10.SLDPRT` (Import der Test-STEP), die Baugruppe braucht sie. Das Muster hat zusätzlich ein Referenzmaß.
- Änderungs-Spec Teil mit `mass` (frei und gesteuert über `gleichung`), `unterdruecken`, `feature` (Normbohrung mit Randbezug),
  `eigenschaft`; Baugruppe mit `komponente_neu` (Normteil ISO 4762), `verknuepfung_neu`, Teiländerung in der Baugruppe.
- **Negativfälle:** falscher Altwert (`BESTAND_ALTWERT`); `mass` auf gesteuertes Maß (`MASS_GESTEUERT`); Bereich zu eng
  (Mangel `bereich`); Änderung in nur einer Konfiguration verlangt, in allen umgesetzt (Mangel `masse`/`punkt`); Original
  zwischen Aufnahme und Ausgabe geändert (`BESTAND_ORIGINAL_GEAENDERT`); neuere Dateiversion (Unit-Test mit Attrappe).
- **Abnahme** an einer echten Datei eines Kollegen: voller Ablauf, Kennzahlen (Zeiten, Speicher, Differenzen, Befunde) in den
  Ergebnissen; Datei und Spec nicht ins Git. Eine bestimmte Datei steht nicht fest: Der Nutzer stellt vor dem Ende von Etappe 1
  eine beliebige echte Kollegen-Datei bereit (Nutzer, 2026-10-30). Ihr Inhalt (Konfigurationen, Gleichungen, Blech, Flächen) ist
  vorab unbekannt; das Musterteil (S18f) deckt diese Fälle darum selbst ab, die Abnahme belegt nur, dass der Ablauf an einer
  echten Datei trägt. Trifft sie auf eine Lücke, ist das ein begründeter Befund in den Ergebnissen.

Unit-Tests ohne SolidWorks: Schema, Validierung gegen eine Attrappe von `bestand.json` (alle Befunde), Prüfsumme und Bauweg,
Folgen-Berechnung, Bereichsprüfung mit Attrappen-Differenzen, Ausgabe-Liste und Originalprüfung, Version.

## 13. Einbindung

- **Skill** `aendern` (neu): wann (fremde Datei, nicht von swki), Abgrenzung zu `konstruieren`/`baugruppe` (eigene Specs),
  Ablauf aufnehmen → Zuordnung der Nutzerpunkte (mit `zeige`) → Spec → validieren → Freigabe-Vorlage → Nutzer-OK → freigeben →
  bauen → prüfen → Prüfer → nachbessern → ausgabe; Regeln: nichts aufräumen, an der Quelle ändern, Bereiche eng, Rückfrage
  bei Zweifel an der Zuordnung.
- **CLAUDE.md:** Grundregel (Entscheidung 2), Abschnitt Bestandsdateien.
- **`.claude/agents/pruefer.md`:** Änderungs-Checkliste.
- **Design §5/§11:** Schutzregel erweitert, Zeile „Bestandsdateien“.
- **Ergebnisse:** `docs/bestandsdateien/ergebnisse.md`.

## 14. Fertig, wenn

- Etappe 1: Musterteil-Änderung besteht (Code-Prüfungen ohne Mangel, Prüfer „bestanden“), die Negativfälle liefern ihre Codes,
  S18a belegt die Datei-ID, die Abnahme an einer echten Kollegen-Datei ist dokumentiert.
- Etappe 2: Musterbaugruppen-Änderung besteht ebenso, Originale nachweislich unverändert.
- Bisherige Regressions-Suite besteht weiter, Unit-Tests grün, `swki api pruefe-code` ohne Befund.

## 15. Reihenfolge der Umsetzung

1. Spike S18 (a–g).
2. Schema, Laden, Validierung gegen `bestand.json`, Freigabe (ohne SolidWorks).
3. `bestand aufnehmen` (Kopie, Version, Aufnahme), `zeige`.
4. `bauen` für die Teil-Punkte, Handler auf fremder Geometrie.
5. `pruefen` §7.1, Differenz §7.2, Prüfer-Checkliste, `ausgabe`, `bericht`.
6. Musterteil, Referenz, Negativfälle, Abnahme Etappe 1.
7. Etappe 2 (§8) mit eigener Referenz.
8. Skill, CLAUDE.md, `pruefer.md`, Design, Ergebnisse.

Etappe 2 bekommt nach Etappe 1 einen eigenen Plan; die Spikes S18b/g für Baugruppen laufen trotzdem vorher, damit Etappe 1
keine Entscheidung trifft, die Baugruppen verbaut.

## 16. Nicht im Paket

Dateien ohne Feature-Baum (STEP, IGES, Parasolid) ändern; PDM; Zeichnungen nachziehen; Revision durch die KI; eigene
Punkt-Typen für Endbedingungen und Skizzengeometrie (zunächst Notausgang) und für Konstruktionstabellen; Aufräumen fremder Modelle (Skizzen voll bestimmen,
Gleichungen entfernen, umbenennen); Schreiben außerhalb des Arbeitsordners; SW 2026 (Rechner B).
