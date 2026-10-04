# Stufe 4a – Bewegungen (Grenzverknüpfungen, Scharnier, gezählte Freiheitsgrade, Bewegungsprüfung)

Ergänzung zu [2026-09-26-solidworks-ki-design.md](2026-09-26-solidworks-ki-design.md) (§4 Spezifikation, §6 Prüfung, §11 Stufen)
und [2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md) (Baugruppen-Format, Bauen, Prüfen,
Änderungserkennung). Stand 2026-10-03, mit dem Nutzer abgestimmt; bei der Planung nachgezogen: §4.2, §11.2, §12
(Negativfälle 1, 3, 4).

## 1. Ziel

Claude baut aus einer freigegebenen Spezifikation eine Baugruppe mit beweglichen Komponenten. Die Bewegungen sind durch
Grenzverknüpfungen begrenzt, und das gebaute Modell bleibt in SolidWorks innerhalb der Grenzen frei ziehbar. `swki pruefen`
fährt jede Bewegung schrittweise ab, prüft je Stellung auf Kollision, belegt die Grenzen und die gezählten Freiheitsgrade und
misst die Endlagen. Bewegungen, deren überstrichene Räume sich schneiden, werden zusätzlich gegeneinander geprüft. Der Mensch
greift wie bisher nur an der Freigabe ein.

## 2. Entscheidungen (mit dem Nutzer, 2026-10-03)

| Frage | Entscheidung |
|---|---|
| Zuschnitt Stufe 4 | **zwei Pakete**: 4a Bewegungen, Grenzverknüpfungen, Scharnier, gezählte Freiheitsgrade, Bewegungsprüfung; 4b mechanische Kopplungen (Zahnrad, Nut, Kurve) |
| Referenz 4a | **Linearschlitten mit Schwenkhebel**: Schlitten linear zwischen zwei Führungsleisten, Hebel auf dem Schlitten über Drehbolzen (ISO 8734) schwenkbar; zwei Bewegungen, je 1 Freiheitsgrad. *Schieber mit Schrägbolzen* ist Kandidat für 4b |
| Antrieb | **nur während der Prüfung**: das Modell enthält Grenzverknüpfungen (frei ziehbar); `swki pruefen` legt je Bewegung eine vorübergehende treibende Verknüpfung an, verstellt sie, löscht sie und schließt ohne Speichern; ein Schritt über die Grenze hinaus muss scheitern |
| Freigabe | `bewegungen` und gezählte `freiheitsgrade` sind Anforderung (Prüfsumme); `min`/`max` der Grenzverknüpfungen **müssen** Parameter-Ausdrücke sein; eine Bewegung läuft immer über den ganzen Bereich ihrer Grenze (kein eigenes `von`/`bis`) |
| Prüfung je Bewegung | **automatisch** kollisionsfrei je Schritt, Grenze wirkt, Freiheitsgrad belegt (ohne Antrieb unterbestimmt, mit Antrieb voll bestimmt); **ausdrücklich** `erwartet.endlagen` (Verschiebung bzw. Drehung beliebiger Komponenten) |
| Kombination der Bewegungen | **Paare mit sich schneidenden überstrichenen Räumen**: jede Bewegung einmal in Grundstellung; nur für Paare, deren überstrichene Hüllquader sich schneiden, zusätzlich jede in der Endstellung der anderen (Aufwand ~linear statt 2^(n−1)) |
| Bilder für den Prüfer | je Bewegung drei Iso-Bilder (`min`, Mitte, `max`) aus dem Grundstellungslauf, je Bewegungskollision ein Bild der ersten kollidierenden Stellung; die vier statischen Ansichten aus 3b bleiben |
| Negativfälle | **vier**: Stellungskollision (nur im Paarlauf), Grenze wirkt nicht (im Modell zu weit, §12), umgekehrte Richtung, zweiter Freiheitsgrad |
| Architektur | Bewegungsprüfung ist Teil von **`swki pruefen`** (ein Prüfbericht, eine Schleife); eigenes Modul `swki/baugruppe/bewegung.py`; Speicherabbruch `SPEICHER_KNAPP` mit Neustart durch den Controller |

## 3. Bausteine

```
schema/baugruppe.schema.json        + grenze_abstand, grenze_winkel, scharnier; freiheitsgrade als Zahl; bewegungen
swki/baugruppe/bewegung.py          neu: Bewegungsprüfung (Festhalten, Läufe, überstrichene Räume, Paare, Endlagen, Mängel)
swki/baugruppe/sw_baugruppe.py      + Grenzverknüpfung, Scharnier, Hilfsverknüpfung setzen/verstellen/löschen, Lage lesen
swki/baugruppe/{plausibel,freigabe,bau,pruefen}.py   Erweiterungen (validieren, Prüfsumme, Grundstellung, Weiche)
config/standard.yaml                + bewegung_schritte, speicher_grenze_mb
.claude/skills/baugruppe/           + Bewegungen, Grenzen, Scharnier
.claude/agents/pruefer.md           + Bewegungs-Checkliste
tests/referenz/schlitten/           Referenz: schlitten.yaml + Teil-Specs
spikes/s13_*.py                     Spike S13 (§11)
```

Die Modulnamen in `swki/baugruppe/` folgen dem Bestand aus 3b; der Plan nennt die genauen Dateien.

## 4. Spezifikationsformat

Erweiterung des Baugruppen-Formats aus Spec 3b §4. **Maße, Feature-IDs und Flächen nur zur Veranschaulichung; die echte
Referenz legt der Plan fest.**

```yaml
art: baugruppe
name: Schlitten
parameter: {HUB: 80, SCHWENK: 90}
komponenten:
  - {id: grundplatte, quelle: {teil: grundplatte.yaml}, fixiert: true}
  - {id: leiste_links, quelle: {teil: leiste.yaml}}
  - {id: leiste_rechts, quelle: {teil: leiste.yaml}}
  - {id: schlitten, quelle: {teil: schlitten.yaml}}
  - {id: drehbolzen, quelle: {normteil: "ISO 8734 8x30"}}
  - {id: hebel, quelle: {teil: hebel.yaml}}
  - {id: leistenschraube, quelle: {normteil: "ISO 4762 M6x20"}, je_position: {komponente: leiste_links, feature: f2}}
verknuepfungen:
  # … statische Verknüpfungen wie in 3b (Leisten, Schrauben, Drehbolzen im Schlitten) …
  - {id: v30, typ: deckungsgleich, a: {komponente: schlitten, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v31, typ: deckungsgleich, a: {komponente: schlitten, feature: f1, flaeche: "-z"},
     b: {komponente: leiste_links, feature: f1, flaeche: "+z"}, ausrichtung: entgegengesetzt}
  - {id: g1, typ: grenze_abstand, a: {komponente: schlitten, feature: f1, flaeche: "-x"},
     b: {komponente: leiste_links, feature: f1, flaeche: "-x"}, min: 0, max: "=HUB", ausrichtung: gleich}
  - {id: s1, typ: scharnier, a: {komponente: hebel, feature: f2, instanz: 1, achse: true},
     b: {komponente: drehbolzen, referenz: EINBAU_ACHSE},
     anlage_a: {komponente: hebel, feature: f1, flaeche: "-y"},
     anlage_b: {komponente: schlitten, feature: f1, flaeche: "+y"}}
  - {id: g2, typ: grenze_winkel, a: {komponente: hebel, feature: f1, flaeche: "+x"},
     b: {komponente: schlitten, feature: f1, flaeche: "+x"}, min: 0, max: "=SCHWENK", ausrichtung: gleich}
freiheitsgrade: {schlitten: 1, hebel: 1}
bewegungen:
  - name: Schlittenhub
    grenze: g1
    schritte: 16
    erwartet:
      endlagen:
        - {komponente: schlitten, verschiebung: ["=HUB", 0, 0]}
        - {komponente: hebel, verschiebung: ["=HUB", 0, 0]}
  - name: Hebelschwenk
    grenze: g2
    erwartet:
      endlagen:
        - {komponente: hebel, drehung: {achse: [0, 1, 0], winkel: "=SCHWENK"}}
pruefung:
  huellquader: [300, 60, 120]
```

### 4.1 Grenzverknüpfungen

- `grenze_abstand` (mm) und `grenze_winkel` (Grad) mit `a`, `b`, `ausrichtung` (Pflicht), `min`, `max`.
- `min` und `max` sind **Ausdrücke über `parameter`** oder `0`. Eine andere feste Zahl ist ein Befund `GRENZE_FESTE_ZAHL`
  (kein Hinweis wie bei `wert`; Entscheidung „Freigabe“). Es gilt `min < max`; bei `grenze_winkel` zusätzlich
  `0 ≤ min < max ≤ 360`.
- Die **bewegte** Seite ist immer `a`. `a` und `b` sind Flächen (Ebenen) mit den Referenzformen aus Spec 3b §4.3.
- Grenzverknüpfungen sind Bauweg wie alle Verknüpfungen. Der Bewegungsbereich ist über die Parameter geschützt.
- Lassen sich die Grenzwerte in SolidWorks per Gleichung an globale Variablen binden (Spike S13.1), bindet swki sie so;
  sonst setzt `bauen` sie aus dem Parameterwert und `swki aenderungen` liest sie als `verknuepfung:<id>.min|max` zurück.
  *Nachgezogen bei der Umsetzung, 2026-10-04:* Die Grenzwerte lassen sich nicht per Gleichung binden: Die Grenzverknüpfung hat nur das Maß `D1` (aktueller Wert,
  Min/MaxVariation relativ dazu); `D2@g1`/`D3@g1` werden von `Add2` abgelehnt (Spike S13 Zeile 2, S13b D). `bauen` setzt die
  Werte aus den Parametern; geschützt sind sie über die Freigabe (`min`/`max` sind Parameter oder 0).

### 4.2 Scharnier

- `typ: scharnier` mit `a`, `b` (Achsen: Bohrungsachse oder `EINBAU_ACHSE`) und `anlage_a`, `anlage_b` (ebene Flächen,
  deckungsgleich). Frei bleibt nur die Drehung um die gemeinsame Achse.
- Optional `ausrichtung` für die Anlage (Vorgabe `entgegengesetzt`, aufeinanderliegende Flächen).
- Umsetzung als zwei SolidWorks-Verknüpfungen: `konzentrisch` ohne Drehsperre (`s1`) und `deckungsgleich` der Anlage
  (`s1.anlage`); beide Typen sind seit Spike S12 belegt. `swMateHINGE` über `AddMate5` wird nicht verwendet (Planung,
  Präzisierung 1).
- Passung wie in 3b §5.7: ISO 8734 *d* als Drehbolzen braucht auf der drehenden Seite eine `bohrung` mit Ø > d.

### 4.3 `freiheitsgrade`

- Werte: `unterbestimmt` (3b, weiter gültig, ohne Bewegungsprüfung) oder die Zahl `1`. Ohne Eintrag gilt „voll bestimmt“.
- Eine Zahl > 1 ist in 4a ein Befund `FREIHEITSGRADE_NICHT_UNTERSTUETZT`.
- Jede Komponente bzw. Gruppe mit `1` wird von **genau einer** Bewegung angetrieben (Seite `a` ihrer Grenze ist die
  Komponente bzw. ein Mitglied der Gruppe); sonst Befund `BEWEGUNG_FEHLT` bzw. `BEWEGUNG_DOPPELT`.

### 4.4 `bewegungen`

- `name` (eindeutig, Zeichen wie IDs), `grenze` (ID einer `grenze_abstand`/`grenze_winkel`), optional `schritte`
  (ganze Zahl ≥ 2; Vorgabe `bewegung_schritte` aus `config/standard.yaml`), `erwartet`.
- Bereich: immer `min` … `max` der Grenze; `schritte + 1` Stellungen mit gleicher Schrittweite.
- `erwartet.endlagen`: Liste von `{komponente, verschiebung: [x, y, z]}` (mm) oder
  `{komponente, drehung: {achse: [x, y, z], winkel}}` (Grad), jeweils Differenz zwischen erster und letzter Stellung in
  Baugruppenkoordinaten. Werte dürfen Ausdrücke sein. `komponente` darf eine Instanz (`schraube.2`) nennen. `achse` wird
  normiert; das Vorzeichen des Winkels folgt der Rechte-Hand-Regel um `achse`.
- `erwartet` ist optional; die automatischen Prüfungen (§7) laufen immer.
- Ab vier Bewegungen meldet `validieren` den Hinweis `art: pruefaufwand` mit der geschätzten Schrittzahl.

## 5. Validieren

Zusätzlich zu Spec 3b §5:

1. Schema der neuen Typen und Schlüssel.
2. Grenzverknüpfungen: `ausrichtung`, `min`/`max` vorhanden, Parameter-Ausdrücke (§4.1), `min < max` nach Auswertung.
3. Scharnier: vier Referenzen auflösbar wie in 3b; Achsen und Flächen vom passenden Typ; Passung (§4.2).
4. `freiheitsgrade`-Zahlen und Zuordnung zu Bewegungen (§4.3).
5. `bewegungen`: Name eindeutig, `grenze` verweist auf eine Grenzverknüpfung, jede Grenze höchstens von einer Bewegung
   genutzt, `endlagen.komponente` vorhanden, `achse` nicht null.
6. Hinweis `pruefaufwand` (§4.4).

## 6. Freigabe

- Die Prüfsumme der Baugruppe umfasst zusätzlich `bewegungen` (Felder `art, name, parameter, eigenschaften, komponenten,
  freiheitsgrade, bewegungen, pruefung` und die Teil-Prüfsummen).
- Grenzverknüpfungen und Scharniere sind Bauweg (Spec 3b §6). Claude darf Referenzen, Ausrichtung und Reihenfolge
  nachbessern; Grenzwerte ändern sich nur über `parameter` mit neuer Freigabe.

## 7. Bauen

Wie Spec 3b §7, zusätzlich:

1. Grenzverknüpfungen und Scharnier über den Verknüpfungs-Handler (Rebuild und Fehlerstatus nach jeder Verknüpfung,
   Rücklese-Prüfung der Ausrichtungen wie in 3b §4.4).
2. **Grundstellung vor dem Speichern:** Jede bewegte Komponente (Seite `a` einer Grenze mit Bewegung) wird über eine
   vorübergehende Hilfsverknüpfung (Abstand bzw. Winkel an den Flächen ihrer Grenze, Wert `min`) in die Grundstellung
   gebracht; Rebuild; die Hilfsverknüpfung wird gelöscht (Spike S13.5: Lage bleibt erhalten). Erst dann wird gespeichert.
   Fehler: `GRUNDSTELLUNG_FEHLER` mit Bewegung und SW-Meldung.
   *Nachgezogen bei der Umsetzung, 2026-10-04:* Keine Hilfsverknüpfung beim Bau. Die Grenze wird mit dem Wert `min` angelegt (`AddMate5`, Maß `D1` = aktueller
   Wert); das ist die Grundstellung. `bauen` prüft sie über das Maß `D1` der Grenze gegen `min` (Knoten
   `grundstellung:<Bewegung>`, Fehler `GRUNDSTELLUNG_FEHLER` bei Abweichung). Grund: Zwei treibende Verknüpfungen, die vor dem
   Speichern angelegt und gelöscht werden, machen eine Winkelgrenze in der gespeicherten Datei unbrauchbar (nach dem
   Neuöffnen faktisch 0…0, Code 47 schon bei 22,5°; Spike S13c E6; mit nur einem oder ohne Antrieb geht sie, E1, E7, E10).
3. Das Protokoll vermerkt je Bewegung die Grundstellung.

## 8. Prüfen

`swki pruefen <baugruppe.yaml> --lauf n` führt erst die statischen Prüfungen aus Spec 3b §9 aus, dann die Bewegungsprüfung,
und schreibt **einen** `pruefbericht.json`. Das Dokument wird ohne Speichern geschlossen; die Prüfsummen der Lauf-Dateien
(3b §8) bleiben unberührt (Test sichert das).

### 8.1 Statisch

- Bestimmtheit wie 3b §9.2; eine Komponente mit `freiheitsgrade: 1` muss in Grundstellung **unterbestimmt** sein
  (sonst Mangel `freiheitsgrad:<komponente>`).
  *Nachgezogen bei der Umsetzung, 2026-10-04:* `GetConstrainedStatus` zählt eine Grenzverknüpfung als Bindung (mit Grenzen sind alle Komponenten voll bestimmt,
  Spike S13 Zeile 4, S13b A/B). Die statische Bestimmtheit erlaubt deshalb für Komponenten mit `freiheitsgrade: 1` den Status
  `unterbestimmt`; der Freiheitsgrad wird in der Bewegungsprüfung mit unterdrückten Grenzen gelesen (§8.2.2).

### 8.2 Bewegungsprüfung

1. **Festhalten:** Jede bewegte Komponente erhält eine Hilfsverknüpfung (§7.2) mit Wert `min`.
2. **Freiheitsgrad belegt:** Je Bewegung: mit ihrer Hilfsverknüpfung und allen übrigen festgehalten muss die bewegte
   Komponente bzw. Gruppe **voll bestimmt** sein (`GetConstrainedStatus`). Bleibt sie unterbestimmt, ist mehr als ein
   Freiheitsgrad offen: Mangel `freiheitsgrad:<komponente>`. Überbestimmt: Mangel `freiheitsgrad:<komponente>` mit Hinweis
   auf Widerspruch zur Grenze.
   *Nachgezogen bei der Umsetzung, 2026-10-04:* Gelesen wird mit **unterdrückten** Grenzen (`IFeature.SetSuppression2`, verlustfrei, Lage unverändert, S13b B):
   (1) Grenzen unterdrückt, ohne Antrieb muss die bewegte Komponente unterbestimmt sein (2); (2) Grenzen unterdrückt, alle
   Antriebe auf `min` muss sie voll bestimmt sein (3); danach werden die Grenzen entdrückt und die Läufe gefahren. Mitfahrer
   melden wie ihr Träger (S13b A, C). Im Bericht je Bewegung `ohne_antrieb`/`mit_antrieb` (Werte 2/3). Gründe: Spike S13 Zeile 4
   (mit Grenzen immer 3), S13b A/B/C.
3. **Grundstellungslauf** je Bewegung, die übrigen auf `min`: für jede der `schritte + 1` Stellungen
   - Wert setzen, Rebuild. Fehler → Mangel `bewegung:<name>` mit Stellung und SW-Meldung; der Lauf dieser Bewegung endet.
   - Kollisionsprüfung mit den Regeln aus 3b §9.3 (Gewindepaarungen ausgenommen). Ein Paar, das in der statischen Prüfung
     nicht vorkam, ist ein Mangel `bewegung_kollision:<name>` mit Stellung, Paar und Volumen; je Paar und Lauf wird nur die
     erste Stellung gemeldet.
   - Lage jeder Komponente (`Transform2`). Komponenten, deren Lage sich gegenüber der ersten Stellung ändert, bilden die
     **bewegte Menge**; ihre Hüllquader in Baugruppenkoordinaten werden über alle Stellungen zum **überstrichenen Raum**
     vereinigt.
     *Nachgezogen bei der Umsetzung, 2026-10-04:* Der Hüllquader einer Komponente wird aus ihrer Teilebox (einmal je Komponente gelesen und gecacht) und der
     Lage `Transform2` gerechnet, nicht per `GetBox` je Stellung (Spike S13 Zeile 6: identisch; S13b E: `GetBox` kostet
     ~10 MB und 0,07–1,1 s je Schritt).
4. **Grenze wirkt:** Stellung `max + Schrittweite/2` und `min − Schrittweite/2` müssen scheitern. Was „scheitern“ genau heißt
   (Fehlerstatus, nicht lösbar, Lage unverändert), legt Spike S13.3 fest. Geht ein Schritt durch: Mangel `grenze:<name>`.
5. **Endlagen:** Differenz zwischen erster und letzter Stellung je Eintrag in `erwartet.endlagen` (Verschiebung des
   Komponentenursprungs; Drehwinkel um `achse` aus der Rotationsdifferenz). Toleranz `anker_mm` bzw. 0,01°. Abweichung:
   Mangel `endlage:<name>:<komponente>` mit Soll und Ist. Eine Drehachse, die nicht zur gemessenen Rotation passt, ist
   ebenfalls eine Abweichung.
6. **Paarläufe:** Für jedes Paar (B1, B2) von Bewegungen, deren überstrichene Räume sich schneiden: B1 erneut durchfahren
   mit B2 auf `max`, und B2 mit B1 auf `max` (die übrigen auf `min`). Nur Kollision (wie Punkt 3); Mangel
   `bewegung_kollision:<name>` mit Angabe der Gegenstellung. Der Bericht nennt die Paare und die Schnittmenge der Räume.
7. **Aufräumen:** Hilfsverknüpfungen löschen (auch bei Ausnahmen, Muster aus dem Aufräumen nach 3b: Aufräumfehler verdecken
   die Ursache nicht); Dokument ohne Speichern schließen.

### 8.3 Bilder

- Je Bewegung drei Iso-Bilder aus dem Grundstellungslauf: `min`, mittlere Stellung, `max` (`<name>-min.png`, …).
- Je Mangel `bewegung_kollision` ein Iso-Bild der ersten kollidierenden Stellung.
- Die vier statischen Ansichten aus 3b §9.7 bleiben.

### 8.4 Speicher

- Vor dem Grundstellungslauf und vor jedem Paarlauf misst swki die Private Bytes des SolidWorks-Prozesses. Liegen sie über
  `speicher_grenze_mb` (`config/standard.yaml`), bricht `pruefen` mit `SPEICHER_KNAPP` (Exit 1, gemessener Wert, Grenze)
  ab, räumt auf (§8.2.7) und schreibt **keinen** Prüfbericht.
- Der Controller startet SolidWorks neu (Ablauf wie in der Übergabe 3b) und ruft `pruefen` erneut auf. Scheitert auch der
  Lauf auf frischem SolidWorks an der Grenze, hält Claude an und meldet sich.
- Vorgaben für `speicher_grenze_mb` und `bewegung_schritte` legt der Plan nach Spike S13.7 fest.
  *Nachgezogen bei der Umsetzung, 2026-10-04:* `bewegung_schritte: 8` (Spike S13 Zeile 8: Probe 0,69 s und 12,3 MB je Schritt, ~100 Komponenten 4,36 s und
  8,9 MB; S13b E: 0,60 s und 19,6 MB bzw. 3,69 s und 18,6 MB, die Annahmen < 0,5 s und < 5 MB wurden verfehlt).
  `speicher_grenze_mb: 10000` (Nutzerentscheidung 2026-10-04; Verlauf 3500 → 5000 → 8000 → 10000): Die Prüfung des
  Linearschlittens braucht auf frischem SolidWorks 6,2–6,9 GB als Dauerniveau (je geöffnetem Teil ~1 GB, erste Öffnung
  +2,6 GB, ISO 4762 +1,7 GB; Kollision ~+0,5 GB je Stellung ohne Bild), Spitze 7,8 GB (0,5-s-Abtastung), mit Anschlag
  (Negativfall 1) 10,2 GB. Die Abfrage misst das Dauerniveau; die Spitze folgt zwischen den Abfragen (speicher-diagnose.md).

### 8.5 Prüfbericht

Je Bewegung: Name, Grenze, Bereich, Schritte, Dauer, bewegte Menge, überstrichener Raum, Kollisionen, Endlagen (Soll/Ist),
Grenze wirkt, Freiheitsgrad; dazu die Paarläufe. Mängel mit den IDs aus §8.2.

## 9. Prüfer, Schleife, Bericht

- Prüfer-Checkliste (`.claude/agents/pruefer.md`) zusätzlich: Bewegung plausibel (richtige Achse und Richtung, mitbewegte
  Komponenten fahren mit, keine sichtbare Durchdringung in `min`/Mitte/`max`), Grenzen fachlich sinnvoll (Anschlag statt
  Durchfahren).
- `status`, Nachbesserung und Abbruch ohne Fortschritt wie bisher; die neuen Mängel zählen wie alle anderen.
- `bericht.md`: Tabelle je Bewegung (Schritte, Kollisionen, Endlagen, Paare, Dauer).

## 10. Fehlerfälle

| Code | Wann | Daten |
|---|---|---|
| `GRENZE_FESTE_ZAHL` | `validieren`: `min`/`max` einer Grenze ist eine feste Zahl ≠ 0 | Verknüpfung, Wert |
| `FREIHEITSGRADE_NICHT_UNTERSTUETZT` | `validieren`: Zahl > 1 | Komponente, Zahl |
| `BEWEGUNG_FEHLT` / `BEWEGUNG_DOPPELT` | `validieren`: Freiheitsgrad 1 ohne bzw. mit mehr als einer Bewegung | Komponente |
| `GRUNDSTELLUNG_FEHLER` | `bauen`: Grundstellung nicht herstellbar | Bewegung, SW-Meldung |
| `SPEICHER_KNAPP` | `pruefen`: Private Bytes über der Grenze | gemessen, Grenze |

Mängel im Prüfbericht (keine Fehlercodes): `freiheitsgrad:<komponente>`, `bewegung:<name>`, `bewegung_kollision:<name>`,
`grenze:<name>`, `endlage:<name>:<komponente>`.

## 11. Offene Technik (Spike S13 vor dem Plan-Code)

Live, mit eigenen Probe-Baugruppen; vor jedem neuen API-Aufruf `swki api methode`/`enum`.

1. `AddMate5` mit Abstands- und Winkelgrenzen: anlegen, Grenzen zurücklesen, Grenzwerte per Gleichung an globale Variablen
   binden.
2. Maße der Grenzwerte (Namen) und ihre Bindung per Gleichung. (Das Scharnier braucht keinen Spike mehr, §4.2.)
3. Hilfsverknüpfung neben der Grenze: verstellen innerhalb der Grenze; wie sich ein Schritt über die Grenze zeigt (Status,
   Fehlercode, Lage). Ergebnis legt „scheitert“ in §8.2.4 fest.
4. `GetConstrainedStatus` ohne und mit Hilfsverknüpfung (gezählter Freiheitsgrad).
5. Hilfsverknüpfung löschen: Lage bleibt; Schließen ohne Speichern ändert die Dateien nicht (Prüfsumme).
6. `Transform2` und Hüllquader je Komponente in Baugruppenkoordinaten; Drehwinkel um eine Achse aus zwei Transformationen.
7. **Zeit und Private Bytes je Schritt** (Wert setzen, Rebuild, Kollisionsprüfung, Lage lesen) am Stehlager und an einer
   synthetischen Baugruppe mit etwa 100 Komponenten. Daraus: Vorgaben `bewegung_schritte`, `speicher_grenze_mb`. Wächst der
   Speicher je Kollisionsprüfung deutlich, wird vor dem Plan neu entschieden (z. B. Kollisionsprüfung nur über die bewegte
   Menge).

## 12. Tests

- **Ohne SolidWorks:** Schema; `validieren` mit allen neuen Befunden und Hinweisen; Prüfsumme mit `bewegungen`;
  Bewegungslogik mit Attrappen: Stellungen aus Grenze und Schritten, bewegte Menge, Vereinigung der Hüllquader,
  Paarbildung, Endlagen (Verschiebung, Drehwinkel um Achse, falsche Achse), Mängelbildung, `SPEICHER_KNAPP`, Aufräumen bei
  Ausnahmen, Bildauswahl.
- **Mit SolidWorks:** je neuer Verknüpfungstyp eine Minimalprobe (`tests/live/`); Referenz `tests/referenz/schlitten/`;
  Negativfälle `tests/live/test_live_schlitten.py`; Regression Buchse, Formplatte, Auswerferhalteplatte, Stehlager.
- **Negativfälle** (je genau die erwartete Mängelmenge):
  1. Stellungskollision: ein Anschlag am Führungsende trifft den Hebel nur bei Schlitten auf `max` und geschwenktem Hebel
     (*Nachgezogen bei der Umsetzung, 2026-10-04:* Anschlag auf der rechten Leiste, +z, weil der Hebel nach +z schwenkt – Drehsinn −y, Spike S13 Zeile 7; Länge 24
     statt 20, weil ein quadratisches Rechteck L = B im Compiler `Gleichungen: Code 1` liefert) →
     `{bewegung_kollision:Hebelschwenk, bewegung_kollision:Schlittenhub}` – beide Paarläufe treffen ihn, die
     Grundstellungsläufe nicht.
  2. Grenze im Modell zu weit: Der Test baut die Referenz mit verfälschtem Grenzwert im Modell (`max` + 20 mm, per
     monkeypatch im Bau; die Spec bleibt unverändert und gültig) → `{grenze:Schlittenhub}`. Ohne Grenzverknüpfung kann der
     Fall nicht gebaut werden, weil `validieren` eine Bewegung ohne Grenze ablehnt.
  3. Umgekehrte Richtung: `g1` an den Flächen +x statt −x (Grundstellung am anderen Ende, der Hub fährt nach −x) →
     `{endlage:Schlittenhub:schlitten, endlage:Schlittenhub:hebel}`.
  4. Zweiter Freiheitsgrad: ohne die seitliche Führung des Schlittens (`v21`) ist er auch quer verschiebbar →
     `{freiheitsgrad:schlitten}` (Menge nach Spike S13.4 bestätigen; **gemessen, Task 9:** `{freiheitsgrad:schlitten,
     freiheitsgrad:hebel, bestimmtheit}` – der Hebel fährt als Mitfahrer mit dem Träger und meldet wie er, die statische
     Bestimmtheit meldet den als Mitfahrer unterbestimmten Drehbolzen). „Hebel nur konzentrisch“ ließe die Höhe des Hebels
     offen (Einfügelage im Ursprung, zusätzliche Kollisionen) und prüfte nicht nur den Freiheitsgrad.
- Live-Tests einzeln mit Zeitlimit; Speicher nach jedem Test messen; frisches SolidWorks vor jedem Referenz- und Negativlauf.

## 13. Einbindung

- Skill `baugruppe`: Abschnitt Bewegungen (Grenzen, Scharnier, `freiheitsgrade: 1`, `bewegungen`, `endlagen`); Regeln:
  bewegte Komponente ist Seite `a`, Grenzwerte gehören in `parameter`, beim Scharnier die Anlage nicht vergessen, Endlagen
  in Baugruppenkoordinaten.
- `config/standard.yaml`: `bewegung_schritte`, `speicher_grenze_mb`.
- CLAUDE.md: Abschnitt „Bewegungen (Stufe 4a)“ (Kurzregeln, Speicherabbruch und Neustart).
- Gesamtdesign §11: Stufe 4 in 4a und 4b geteilt.

## 14. Fertig, wenn

- Referenz *Schlitten* besteht (Code-Prüfungen und Prüfer).
- Die vier Negativfälle liefern genau ihre Mängelmenge.
- Buchse, Formplatte, Auswerferhalteplatte und Stehlager bestehen weiter.
- Zeit und Private Bytes je Bewegungsschritt sind in `docs/stufe4a/ergebnisse.md` dokumentiert.

## 15. Reihenfolge der Umsetzung

Spike S13 → Schema, `validieren`, Freigabe → Bauen (Typen, Grundstellung) → Bewegungsprüfung → Bilder, Bericht, Prüfer →
Referenz → Negativfälle → Doku.

## 16. Nicht in 4a

Zahnrad-, Nut-, Kurvenverknüpfung und die Referenz *Schieber mit Schrägbolzen* (4b); Teilbereiche einer Bewegung (`von`/`bis`);
Mindestabstände über den Weg; mehr als ein Freiheitsgrad je Komponente; gekoppelte Antriebe; Motion-Studien und Animationen;
Unterbaugruppen.
