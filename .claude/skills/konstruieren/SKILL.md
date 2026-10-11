---
name: konstruieren
description: Konstruiert ein Einzelteil in SolidWorks aus Skizze, Beschreibung oder Anweisung – Spezifikation schreiben, validieren, Rückfragen, Freigabe durch den Nutzer, bauen, prüfen, unabhängiger Prüfer, nachbessern, Bericht. Verwenden, wenn der Nutzer ein Teil konstruiert, gebaut oder geändert haben will.
---

# Konstruieren (Einzelteil, Stufe 2/2c)

Alle Befehle: `.venv\Scripts\python.exe -m swki …` (Ausgabe JSON, Exit 0 = ok). Längen in mm, Winkel in Grad.

## 1. Auftrag anlegen
- Ordner `auftraege/<auftrag>/` (Name wie vom Nutzer, sonst kurz und sprechend), Eingaben nach `eingabe/`.
- Ein Teil je Auftrag.
- Mehrere Teile, die zusammengebaut werden: Skill `baugruppe` (eine Freigabe für Baugruppe und Teile).

## 2. Spezifikation schreiben
- Datei `auftraege/<auftrag>/<name>.yaml` nach `schema/teil.schema.json`. Dieser Skill enthält alles Nötige (Elemente,
  Endbedingungen, Kurzreferenz Prüfwerte) – Schema und Vorlagen nur bei einem Validierfehler nachlesen.
- Zeichnung lesen (vor dem Schreiben, einmal und knapp): Projektionsmethode am Symbol im Schriftfeld – ISO E
  (Erstwinkel): Draufsicht **unter** der Vorderansicht, Ansicht von links **rechts** daneben; ISO A (Drittwinkel):
  Draufsicht **über** der Vorderansicht, Ansicht von rechts **rechts** daneben. Je Ansicht festhalten: Blickrichtung
  als Modellachse und welche Modellachse im Bild nach rechts/oben zeigt; erst dann Lagemaße mit Vorzeichen
  umrechnen und je Maß die Bezugskante nennen (Plattenrand oder Gehäuse?).
- Kommentare knapp: je Annahme eine Zeile.
- Maße, die zusammenhängen, als `parameter` und Ausdrücke (`"=L/2-20"`); sie werden SW-Gleichungen.
- Anforderungsmaße (vom Nutzer vorgegeben oder zu prüfen) immer als `parameter` führen: feste Zahlen in Features
  gehören zum Bauweg und sind von der Freigabe-Prüfsumme nicht geschützt.
- Anforderungen nie nur als Kommentar: was gebaut oder geprüft werden muss, gehört in `parameter`, Features oder
  `pruefung`. Kommentare erläutern nur; die Freigabe-Kopie behält sie für den Prüfer.
- **Spec-Syntax vollständig** (Schema nicht lesen; `?` = optional, `wert` = Zahl oder `"=Ausdruck"`):
  ```yaml
  art: teil
  name: Platte                                  # Kopf: material?, eigenschaften? {Benennung: …}, parameter? {L: 100},
  material: "1.0038"                            #       pruefung?, max_nachbesserungen?
  parameter: {L: 100, B: 60, T: 10}
  features:
    - id: f1
      typ: extrusion                            # oder schnitt
      skizze:
        ebene: oben                             # vorne | oben | rechts | {feature: f1, flaeche: "+y"} (±x/±y/±z)
                                                # | {versatz: {ebene: oben, abstand: 20}} | {nahe: [x, y, z]}
        elemente:                               # mehrere geschlossene Profile: innere sind Löcher
          - {rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B", radius?: 3}}
          - {kreis: {mitte: [u, v], durchmesser: 10}}
          - {langloch: {mitte: [u, v], laenge: 3, breite: 5, winkel?: 0}}   # laenge = Mittenabstand der Bögen
          - {polygon: {punkte: [[u, v], …], radien?: 2}}
          - {kontur: {start: [u, v], segmente: [{linie: [u, v]}, {bogen: [u, v], mitte: [u, v]}]}}
          - {mittellinie: {von: [u, v], bis: [u, v]}}                     # Rotationsachse
      ende: {typ: blind, tiefe: "=T"}           # | {typ: mittig, tiefe} | {typ: durch_alles}
                                                # | {typ: bis_flaeche, flaeche: <anker>}
                                                # | {typ: versatz_von_flaeche, flaeche: <anker>, abstand}
                                                # optional: umkehren: true, formschraege: {winkel, querschnitt}
    - {id: f2, typ: bohrung, flaeche: {feature: f1, flaeche: "+y"}, positionen: [[u, v], …], durchmesser: 6,
       tiefe: 8}                                # oder durch: true; senkung?: {durchmesser, tiefe}
    - {id: f3, typ: normbohrung, art: gewinde, groesse: M6, flaeche: <anker>, positionen: [[u, v]], tiefe: 12,
       gewindetiefe: 10}                        # art: gewinde | zylinderschraube | senkschraube | stift (groesse 8)
    - {id: f4, typ: rotation, skizze: {…, elemente: [<profil>, {mittellinie: …}]}, winkel?: 360, schnitt?: true}
    - {id: f5, typ: verrundung, kanten: [{feature: f1, auswahl: senkrechte_kanten}], radius: 2}   # fase: abstand, winkel?
    - {id: f6, typ: muster_linear, features: [f2], richtung1: {achse: x, abstand: 20, anzahl: 3}}
    - {id: f7, typ: spiegeln, features: [f2], ebene: rechts}
    - {id: f8, typ: referenz, ebene: {basis: oben, abstand: 50}}           # oder achse: x|y|z
  ```
  Kanten: `{feature, auswahl: senkrechte_kanten|alle_kanten}`, `{feature, kanten_an: "+y"}`, `{nahe: [x, y, z]}`.
- Ebenen: `vorne` (Normale +Z), `oben` (+Y), `rechts` (+X). Skizzenkoordinaten (u, v): vorne X=u, Y=v · oben X=u, Z=−v ·
  rechts Z=−u, Y=v.
  Skizzen und `positionen` auf Flächen und Versatzebenen nutzen dieselbe (u, v)-Zuordnung wie die parallele
  Standardebene (Fläche ±y wie `oben`: X=u, Z=−v), unabhängig vom Vorzeichen der Normale.
- Flächen/Kanten bevorzugt semantisch (`{feature, flaeche}`, `{feature, auswahl}`), sonst `{nahe: [x, y, z]}`.
- Schnitt geht standardmäßig gegen die Skizzennormale (von einer Deckfläche ins Material); `umkehren: true` dreht.
- Bohrungen für Schrauben, Gewinde und Stifte als `typ: normbohrung` (`art: gewinde | zylinderschraube |
  senkschraube | stift`, `groesse` wie „M8“, „M10x1“ bzw. Stift-Nenndurchmesser `8`, `durch: true` oder `tiefe`,
  bei Gewinde mit `tiefe` ist `gewindetiefe` ≤ `tiefe` Pflicht, bei Gewinde mit `durch` ist sie erlaubt).
  Nur Größen aus `swki/wissen/bohrungsnormen.yaml`; `validieren` nennt die verfügbaren. Gewinde werden kosmetisch gebaut. `bohrung` bleibt für freie Durchmesser. Die erste Position
  muss auf der gemeinten `flaeche` liegen (kein Absatz davor, sonst Abbruch).
- Zahnräder und Zahnstangen als `typ: verzahnung` (Spec 4b, Vorlage `tests/referenz/zahnstangentrieb/`): `art:
  stirnrad | zahnstange`, `ebene` (Standardebene oder `versatz`, keine Fläche), `mitte` (Stirnrad: Radachse;
  Zahnstange: Mitte von Zahn 1 auf der Profilmittellinie), `modul` (DIN 780 Reihe 1), `zaehne` (Stirnrad ≥ 17),
  `breite`, `zahndickenabmass` (< 0 für Flankenspiel, z. B. −0,05 bei m 2); Stirnrad optional `winkel` (Zahn 1 gegen
  +u), Zahnstange optional `kopf: "-v"`; Anforderungswerte als Parameter. Das Feature baut das ganze Rad bzw. nur das
  Zahnband der Zahnstange: den Rücken als eigene Extrusion genau bis an die Fußlinie (1,25·m unter der
  Profilmittellinie), sonst entstehen zwei Körper. Wellen mit Rädern: Räder als `verzahnung`, die Wellenabschnitte
  zwischen ihnen als Kreis-Extrusionen ohne Überlappung (Ausnahme von Modellierregel 1, sonst stimmt `volumen: auto`
  nicht). Radachse: `{feature: <id>, instanz: 1, achse: true}`. In Ausdrücken ist `pi` erlaubt (Zahnstangenlänge
  `=Z*pi*M`). `swki pruefen` prüft Kopf-/Fußkreis, Zähnezahl und Zahnweite bzw. Teilung und Zahndicke selbst
  (`verzahnungen`); `huellquader` bei Rädern weglassen (die Box hängt von der Lage der Zähne ab).
  Bauzeit und Speicher: ein Rad z 50 braucht ca. 20 s (rund 0,4 s je Zahn), ein Teil mit Rad ca. +1,4–1,8 GB Private
  Bytes; in Live-Serien nach jedem Teil mit Rädern SolidWorks neu starten. Zähnezahlen weit über 50 dauern entsprechend
  länger.
- Skizzenelemente: `rechteck` (optional `radius`), `polygon` (optional `radien`: ein Wert oder je Ecke, 0 = scharf,
  Radius < halbe kürzere Nachbarkante), `langloch` (`mitte`, `laenge` = Mittenabstand der Bögen, `breite`, `winkel`
  zu u in [0, 180)), `kontur` (`start`, `segmente` aus `{linie: [u, v]}` und `{bogen: [u, v], mitte: [u, v]}`, Bögen
  gegen den Uhrzeigersinn in (u, v), letzter Endpunkt = `start`), `kreis`, `mittellinie`.
- Endbedingungen: `blind`, `durch_alles`, `mittig`, `bis_flaeche` (`flaeche`), `versatz_von_flaeche` (`flaeche`,
  `abstand`; der Versatz geht zur Skizze hin – z. B. Restwandstärke über der Unterseite). Bekannte Einschränkung: ein
  Aufsatz mit `versatz_von_flaeche`, dessen Skizze abgesetzt über der Zielfläche liegt, ergibt einen getrennten Körper
  – dafür `bis_flaeche` oder `blind` verwenden. `swki pruefen` meldet mehrere Volumenkörper als Mangel (Prüfung
  `koerper`: „2 Volumenkörper statt 1“).
- Schräge Wände eines extrudierten Elements (konischer Zapfen, Einführschräge, Trichter, verjüngter Steg) als
  `formschraege` im `ende` von `extrusion`/`schnitt` (Paket Formschräge, Vorlage `tests/referenz/zentrieraufnahme/`):
  `formschraege: {winkel: "=W", querschnitt: kleiner | groesser}`. Der Winkel (Grad, 0 < winkel < 90) zählt gegen die
  Extrusionsrichtung und ist ein Parameter. `querschnitt` gilt von der Skizze weg für den extrudierten Bereich
  (Material beim Aufsatz, Aussparung beim Schnitt): `kleiner` = Zapfen verjüngt sich, Tasche wird zum Boden enger;
  `groesser` = wird weiter. Bei `mittig` gilt das zu beiden Seiten. Ein Trichter wird von der Seite skizziert, deren
  Durchmesser Anforderung ist (enge Seite → `groesser`, weite Seite → `kleiner`). Seitenflächen eines schrägen
  Features sind nicht achsparallel: nicht mit `{feature, flaeche: "+x"}`/`kanten_an` quer zur Extrusion und nicht
  mit `senkrechte_kanten` ansprechen (`validieren` lehnt das ab), sondern mit `nahe`; Ecken als Eckradius in der
  Skizze (wird mitgeschrägt). `validieren` meldet, wenn das Profil bei `kleiner` zusammenfällt (Kreis, Rechteck,
  Eckradius, Langloch). `swki pruefen` misst Winkel und Richtung jeder Seitenfläche selbst (`formschraegen`);
  `volumen: auto` rechnet Kreis, Rechteck (auch mit Eckradius), Langloch und konvexe Polygone bei `blind`/`mittig`
  (nur ein Profil je Skizze). Die Skizze eines schrägen Features liegt auf einer Standardebene, einer Versatzebene
  oder einem Flächenanker `{feature, flaeche}` – nicht auf `{nahe}` (`validieren` lehnt das ab).
  `durchmesser_pruefen` findet an schrägen Features keinen Zylinder; Maße über Deck- und Bodenfläche mit
  `masse_pruefen`.
- Reservierte IDs (`achse_x|y|z`, Endungen `_skizze`, `_senkung`, `_positionen`, `<skript-id>_<n>`) nicht als Feature-IDs
  verwenden; `validieren` lehnt sie ab, sie gehören dem Compiler.
- Braucht das Teil Normteile (Schrauben, Stifte …), diese über den Skill `normteile` holen.
- Was das Schema nicht abbildet: `typ: skript` mit `luecke:` und Datei `skripte/<id>.py` (`def bauen(ctx)`), nie weglassen.
- `pruefung` immer füllen: `huellquader` (`auto` oder [X, Y, Z]), `volumen` (`auto` oder Wert), wichtige Maße unter
  `masse_pruefen`, `schwerpunkt` für Symmetrie/Spiegelfehler. Kurzreferenz (vollständig, Schema nicht extra lesen):
  ```yaml
  pruefung:
    huellquader: auto                           # oder Kanten in X, Y, Z: ["=B", "=H", "=L"]
    volumen: {soll: auto}                       # oder Zahl; optional toleranz_prozent
    schwerpunkt: {soll: [0, null, 0]}           # null = Koordinate nicht prüfen; optional tol
    masse_pruefen:                              # Abstand zweier Messpunkte; optional tol (mm)
      - {was: Höhe, von: {feature: f1, flaeche: "-y"}, zu: {feature: f2, flaeche: "+y"}, soll: "=H"}
      - {was: Lochabstand, von: {feature: f3, instanz: 1, achse: true}, zu: {feature: f3, instanz: 2, achse: true}, soll: "=A"}
      - {was: Loch zur Kante, von: {feature: f1, flaeche: "-x"}, zu: {feature: f3, instanz: 1, achse: true}, soll: "=E"}
    durchmesser_pruefen:                        # Zylinderfläche des Features nahe einem Punkt auf dem Mantel
      - {was: Zapfen, feature: f4, nahe: ["=X0+D/2", "=H+5", 0], soll: "=D"}
  ```
  Messpunkte: `{feature, flaeche: "+x"|"-x"|…}`, `{feature, instanz, achse: true}` (nur `bohrung`/`normbohrung`, nicht an
  Extrusionen – deren Lage über `durchmesser_pruefen` mit `nahe` oder `schwerpunkt` prüfen), `{punkt: [x, y, z]}`.
  `huellquader: auto` rechnet aus den Aufsätzen (Schnitte und Bohrungen verkleinern ihn nicht); `validieren` zeigt die
  `auto`-Werte zum Abgleich mit der Zeichnung und lehnt `auto` ab, wo es nicht geht (Verzahnung, Skript, Kreismuster
  von Aufsätzen, Skizze auf `nahe`) – dort Kanten angeben. Weicht ein von Hand angegebener Hüllquader von der Rechnung
  ab, meldet `validieren` einen Hinweis `pruefwert`, und `swki durchlauf --freigeben` hält vor der Freigabe an.
  Nicht von Hand nachrechnen (kein Python für Volumen oder Schwerpunkt): `volumen: {soll: auto}` rechnet auch Löcher
  in derselben Skizze und Durchgänge (`durch_alles`, `durch`) durch eine Platte; `schwerpunkt` nur für
  Symmetrieachsen (0) und sonst `null`. Die Lage asymmetrischer Merkmale prüft der Merkmalsabgleich nach dem Bau.
  Ineinanderliegende Schnitte (oder Aufsätze) ab derselben Skizzenebene, z. B. Freiraum hinter einer Senkung, rechnet
  `auto` richtig (gemeinsamer Teil zählt einmal); Überlappungen anderer Art vermeiden.
  `auto` setzt voraus, dass Aufsätze nicht in andere Körper hineinragen: einen Aufsatz auf der Fläche beginnen lassen,
  auf der er steht. Ausnahme: Wird seine Grundkante mitgeschrägt (Formschräge an einem `mittig`-Steg, der quer zur
  Platte skizziert ist), das Profil 1 mm in die Platte führen – sonst bleibt ein Keilspalt (2 Körper); `auto` zählt
  die Überlappung doppelt, bleibt bei 1 mm aber in der Toleranz.

### Modellierregeln (kompakter Feature-Baum)
Änderbarkeit zuerst, sonst so wenige Features wie möglich:
1. Drehteile als eine Rotation eines Halbschnitts.
2. Gleiche Bohrungen auf derselben Fläche in **einen** Knoten (mehrere `positionen`); `normbohrung` statt Bohrung +
   Senkung, sobald eine Schraube, ein Gewinde oder ein Stift gemeint ist.
3. Muster und Spiegeln nur, wenn Anzahl, Abstand oder Symmetrie eine Anforderung ist (dann als Parameter); sonst
   Positionen direkt.
4. Runde Konturen in der Skizze (Eckradius, Langloch, Kontur) statt nachträglicher Verrundung senkrechter Kanten, wenn
   die Kontur nur einmal vorkommt.
5. Tiefen, die sich auf eine andere Fläche beziehen (Restwandstärke, bis zum Boden), mit `versatz_von_flaeche` /
   `bis_flaeche`, nicht als gerechnete Zahl.
6. Kantenverrundungen und Fasen gleichen Maßes in einem Knoten, am Ende des Baums.
7. Schräge Wände als `formschraege` an der Extrusion, die das Element erzeugt – nicht als eigenes Feature, nicht als
   Rotation eines Trapezes und nicht als Schnitt mit schräger Skizze.

## 3. Validieren und Rückfragen
- `swki validieren <spec>` bis `"gueltig": true` (ohne SolidWorks, schnell). Die Ausgabe enthält
  `vorpruefung_auftrag` (Prompt für die Vorprüfung, Schritt 4).
- `hinweise` aus `validieren` vor der Freigabe abarbeiten (sie blockieren nie):
  - `art: feste_zahl` – feste Zahl in einem maßtragenden Feld: meist als Parameter führen, sonst dem Nutzer bei der
    Freigabe ausdrücklich nennen.
  - `art: zusammenfassen` – Knoten (`knoten`) lassen sich nach den Modellierregeln zusammenfassen: umbauen oder dem
    Nutzer begründen, warum nicht (z. B. Anzahl und Abstand sind Anforderungen).
- Unklarheiten in der Eingabe (fehlende Maße, Toleranzen, Material) gesammelt beim Nutzer erfragen, nicht raten.

## 4. Vorprüfung und Freigabe (einziger menschlicher Eingriff)
Der Prüfer prüft **vor** dem Bau, ob die Spec die Eingabe richtig umsetzt (nur Text: Eingabe + Spec). Nach dem Bau
prüft der Code das Teil gegen die freigegebene Spec (Prüfung `merkmale` aus der STEP) – ein zweiter Prüfer entfällt,
wenn `swki status` danach `bestanden` meldet.
- Vorprüfung: Prüfer-Agent (`subagent_type: pruefer`, `model: sonnet`) mit `vorpruefung_auftrag` aus `swki validieren`
  als Prompt (unverändert). Urteil ablegen: `swki urteil <spec> --vorpruefung` mit dem JSON auf stdin (Heredoc) oder
  `--json '<JSON>'`. Mängel → Spec korrigieren, validieren, Vorprüfung wiederholen (`swki durchlauf --freigeben`
  verweigert bei Mängeln einer Vorprüfung desselben Spec-Texts mit `schritt: vorpruefung`).
- **Freigabe steht noch aus:** Vorprüfung zuerst, dann dem Nutzer die Anforderungen zeigen (Parameter, Material,
  Eigenschaften, Prüfwerte, Feature-Liste in Worten) und das Ergebnis der Vorprüfung nennen. Nach ausdrücklichem OK:
  `swki durchlauf <spec> --freigeben` (validieren → freigeben → bauen → prüfen → status in **einem** Aufruf; legt
  `<name>.freigegeben.yaml` ab, diese Kopie nie ändern). Einzeln geht weiter `swki freigeben <spec>`.
- **Freigabe schon im Auftrag erteilt:** nach `swki validieren` den Prüfer (Vorprüfung) und `swki durchlauf <spec>
  --freigeben` in **einer** Nachricht als zwei parallele Tool-Aufrufe starten (beide im Vordergrund). Danach
  `swki urteil <spec> --vorpruefung` – er legt das Urteil ab, nennt den Status und schreibt bei `bestanden` gleich den
  Bericht.
- Die Spec nach der Vorprüfung nicht mehr ändern, bevor sie freigegeben ist: Die Vorprüfung gilt nur für genau den
  Text, der freigegeben wird.

## 5. Bauen, prüfen, Prüfer
- Nach der Freigabe: `swki durchlauf <spec>` (ohne `--freigeben`) baut den nächsten Lauf und prüft ihn. Ausgabe
  kompakt: `schritt` (wo er endete), `lauf`, `pruefung.fehlgeschlagen`, `pruefung.merkmale` (Merkmalsbericht aus der
  STEP), `empfehlung`, `naechstes`. Einzelbefehle (`swki bauen`, `swki pruefen <spec> --lauf n`) bleiben für
  Sonderfälle.
- `swki pruefen` liest die STEP, die `swki bauen` je Lauf speichert, und sucht jedes Feature der freigegebenen Spec
  darin (Prüfung `merkmale`): Bohrungen und Normbohrungen mit Achse, Lage, Ø, durch/blind, Eintrittsseite, Tiefe und
  Senkung, Kreise von Extrusionen/Schnitten (Zapfen, Löcher), Verrundungen (Radius) und Fasen (Winkel); Muster und
  Spiegelungen werden aufgelöst. Abweichungen sind Mängel mit Knoten; `nicht_geprueft` nennt, was der Abgleich nicht
  abbildet (Rotation, Skript, Verzahnung, Kontur, Fläche über `nahe` ohne Treffer …) – dann bleibt der Prüfer nach dem
  Bau nötig. `swki merkmale <datei.step>` zeigt den Bericht einer beliebigen STEP.
- Endet der Durchlauf mit `schritt: bauen` (Bauabbruch): Fehlercode und Knoten lesen, Bauweg nachbessern (Schritt 6).
- Meldet `swki bauen` **`MANUELL_GEAENDERT`**, hat jemand die Dateien des letzten Laufs geändert: `swki aenderungen <spec>` zeigt die Parameterdifferenz; dem Nutzer zeigen und fragen (übernehmen → Spec ändern, validieren, Nutzer-OK, `swki freigeben`, dann `swki bauen --uebernommen`; verwerfen → nur auf ausdrückliche Anweisung `swki bauen --verwerfen`). Nie still neu bauen.
- **Lage-Selbstcheck:** `pruefung.merkmale` (auch `merkmale.txt` im Laufordner; ohne STEP `pruefung.steckbrief`)
  nennt Hüllquader, Bohrungen, Zapfen, Taschenböden, Rundungen und Fasen mit Lage. Bei Widerspruch zur Eingabe erst
  nachbessern.
- Der Prüfbericht vergleicht Normbohrungen (Art, Größe, Norm, Positionen, durch/Tiefe) mit der freigegebenen Kopie
  (Prüfung `normbohrungen`) und nennt unter `baum` Knoten- und Featurezahl.
- Meldet `swki durchlauf` (bzw. `swki urteil --vorpruefung`) `empfehlung: bestanden`, ist kein Prüfer nach dem Bau
  nötig: weiter mit 7 (der Bericht ist nach `swki urteil` schon geschrieben, sonst `swki bericht <spec>`).
- Sonst (keine gültige Vorprüfung oder `nicht_geprueft`): Prüfer-Agent (`subagent_type: pruefer`, `model: sonnet`) mit
  `pruefer_auftrag` aus der Ausgabe von `swki durchlauf` als Prompt starten (unverändert übernehmen; Screenshots nennt
  er nur, wo der Merkmalsbericht nicht reicht). Ohne durchlauf: Prompt mit den Pfaden: Eingabeordner, freigegebene
  Spezifikation (`<name>.freigegeben.yaml`), Prüfbericht, `merkmale.txt` des Laufs. Keine Protokolle, keine Skripte
  übergeben.
- Sein Urteil mit `swki urteil <spec>` ablegen (JSON auf stdin per Heredoc oder `--json`; Code-Fences werden
  weggelassen, am Inhalt nichts ändern). Der Befehl schreibt `protokolle/<spec>.lauf-<n>.pruefer.json` (letzter Lauf,
  sonst `--lauf n`), nennt `empfehlung` und schreibt bei `bestanden` gleich den Bericht.

## 6. Schleife
- `swki status <spec>` (optional `--max N`, wenn der Nutzer eine Zahl genannt hat) → `empfehlung`:
  - `nachbessern`: nur den Bauweg ändern (Anker, Reihenfolge, Handler-Optionen, Skripte). Anforderungen (Parameter,
    Material, Eigenschaften, Prüfwerte) sind tabu – `swki bauen` verweigert sonst (FREIGABE_VERALTET). Hält Claude eine
    Anforderung für falsch: Nutzer fragen. Dann `swki durchlauf <spec>` (Schritt 5).
  - Bauabbruch (`swki bauen` meldet `status: fehler`): nicht `swki pruefen` (verweigert mit LAUF_ABGEBROCHEN), sondern
    direkt den Bauweg nachbessern und neu bauen. Ein Abbruch verbraucht einen Lauf, wird aber nicht als Mängelzahl
    verglichen; „kein Fortschritt“ vergleicht nur durchgebaute und geprüfte Läufe. Vorgabe: 1 + 3 = 4 Läufe;
    Spezifikation (`max_nachbesserungen`) oder Anweisung im Chat (`--max`)
    können abweichen (`swki status` nennt `max_laeufe`).
  - `stopp_max` / `stopp_kein_fortschritt`: anhalten, Nutzer mit Bericht informieren.
  - `bestanden`: weiter mit 7.
- Wiederholt sich ein Compiler-Problem, Skill `compiler-erweitern` anwenden.

## 7. Bericht
- `swki bericht <spec>` → `auftraege/<auftrag>/bericht.md`; dem Nutzer Status, offene Punkte und Screenshots zeigen.
