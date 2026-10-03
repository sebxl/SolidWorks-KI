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
- Datei `auftraege/<auftrag>/<name>.yaml` nach `schema/teil.schema.json`. Vorlagen: `tests/referenz/*/`.
- Maße, die zusammenhängen, als `parameter` und Ausdrücke (`"=L/2-20"`); sie werden SW-Gleichungen.
- Anforderungsmaße (vom Nutzer vorgegeben oder zu prüfen) immer als `parameter` führen: feste Zahlen in Features
  gehören zum Bauweg und sind von der Freigabe-Prüfsumme nicht geschützt.
- Anforderungen nie nur als Kommentar: was gebaut oder geprüft werden muss, gehört in `parameter`, Features oder
  `pruefung`. Kommentare erläutern nur; die Freigabe-Kopie behält sie für den Prüfer.
- Ebenen: `vorne` (Normale +Z), `oben` (+Y), `rechts` (+X). Skizzenkoordinaten (u, v): vorne X=u, Y=v · oben X=u, Z=−v ·
  rechts Z=−u, Y=v.
- Flächen/Kanten bevorzugt semantisch (`{feature, flaeche}`, `{feature, auswahl}`), sonst `{nahe: [x, y, z]}`.
- Schnitt geht standardmäßig gegen die Skizzennormale (von einer Deckfläche ins Material); `umkehren: true` dreht.
- Bohrungen für Schrauben, Gewinde und Stifte als `typ: normbohrung` (`art: gewinde | zylinderschraube |
  senkschraube | stift`, `groesse` wie „M8“, „M10x1“ bzw. Stift-Nenndurchmesser `8`, `durch: true` oder `tiefe`,
  bei Gewinde mit `tiefe` ist `gewindetiefe` ≤ `tiefe` Pflicht, bei Gewinde mit `durch` ist sie erlaubt).
  Nur Größen aus `swki/wissen/bohrungsnormen.yaml`; `validieren` nennt die verfügbaren. Gewinde werden kosmetisch gebaut. `bohrung` bleibt für freie Durchmesser. Die erste Position
  muss auf der gemeinten `flaeche` liegen (kein Absatz davor, sonst Abbruch).
- Skizzenelemente: `rechteck` (optional `radius`), `polygon` (optional `radien`: ein Wert oder je Ecke, 0 = scharf,
  Radius < halbe kürzere Nachbarkante), `langloch` (`mitte`, `laenge` = Mittenabstand der Bögen, `breite`, `winkel`
  zu u in [0, 180)), `kontur` (`start`, `segmente` aus `{linie: [u, v]}` und `{bogen: [u, v], mitte: [u, v]}`, Bögen
  gegen den Uhrzeigersinn in (u, v), letzter Endpunkt = `start`), `kreis`, `mittellinie`.
- Endbedingungen: `blind`, `durch_alles`, `mittig`, `bis_flaeche` (`flaeche`), `versatz_von_flaeche` (`flaeche`,
  `abstand`; der Versatz geht zur Skizze hin – z. B. Restwandstärke über der Unterseite). Bekannte Einschränkung: ein
  Aufsatz mit `versatz_von_flaeche`, dessen Skizze abgesetzt über der Zielfläche liegt, ergibt einen getrennten Körper
  – dafür `bis_flaeche` oder `blind` verwenden. `swki pruefen` meldet mehrere Volumenkörper als Mangel (Prüfung
  `koerper`: „2 Volumenkörper statt 1“).
- Reservierte IDs (`achse_x|y|z`, Endungen `_skizze`, `_senkung`, `_positionen`, `<skript-id>_<n>`) nicht als Feature-IDs
  verwenden; `validieren` lehnt sie ab, sie gehören dem Compiler.
- Braucht das Teil Normteile (Schrauben, Stifte …), diese über den Skill `normteile` holen.
- Was das Schema nicht abbildet: `typ: skript` mit `luecke:` und Datei `skripte/<id>.py` (`def bauen(ctx)`), nie weglassen.
- `pruefung` immer füllen: `huellquader` [X, Y, Z], `volumen` (`auto` oder Wert), wichtige Maße unter `masse_pruefen`,
  `schwerpunkt` für Symmetrie/Spiegelfehler.

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

## 3. Validieren und Rückfragen
- `swki validieren <spec>` bis `"gueltig": true`.
- `hinweise` aus `validieren` vor der Freigabe abarbeiten (sie blockieren nie):
  - `art: feste_zahl` – feste Zahl in einem maßtragenden Feld: meist als Parameter führen, sonst dem Nutzer bei der
    Freigabe ausdrücklich nennen.
  - `art: zusammenfassen` – Knoten (`knoten`) lassen sich nach den Modellierregeln zusammenfassen: umbauen oder dem
    Nutzer begründen, warum nicht (z. B. Anzahl und Abstand sind Anforderungen).
- Unklarheiten in der Eingabe (fehlende Maße, Toleranzen, Material) gesammelt beim Nutzer erfragen, nicht raten.

## 4. Freigabe (einziger menschlicher Eingriff)
- Dem Nutzer die Anforderungen zeigen: Parameter, Material, Eigenschaften, Prüfwerte, Feature-Liste in Worten.
- Erst nach ausdrücklichem OK: `swki freigeben <spec>` (legt `<name>.freigegeben.yaml` ab; diese Kopie nie ändern).

## 5. Bauen, prüfen, Prüfer
- Meldet `swki bauen` **`MANUELL_GEAENDERT`**, hat jemand die Dateien des letzten Laufs geändert: `swki aenderungen <spec>` zeigt die Parameterdifferenz; dem Nutzer zeigen und fragen (übernehmen → Spec ändern, validieren, Nutzer-OK, `swki freigeben`, dann `swki bauen --uebernommen`; verwerfen → nur auf ausdrückliche Anweisung `swki bauen --verwerfen`). Nie still neu bauen.
- `swki bauen <spec>` → Lauf n (Protokoll unter `protokolle/`). Bei Bauabbruch: Fehlercode und Knoten lesen,
  dann nicht `swki pruefen`, sondern nachbessern (Schritt 6, „Bauabbruch“).
- `swki pruefen <spec> --lauf n` → Prüfbericht + Screenshots.
- Der Prüfbericht vergleicht Normbohrungen (Art, Größe, Norm, Positionen, durch/Tiefe) mit der freigegebenen Kopie
  (Prüfung `normbohrungen`) und nennt unter `baum` Knoten- und Featurezahl.
- Prüfer-Agent (`subagent_type: pruefer`) starten mit den Pfaden: Eingabeordner, freigegebene Spezifikation
  (`<name>.freigegeben.yaml`), Prüfbericht, Screenshot-Ordner des Laufs. Keine Protokolle, keine Skripte übergeben.
- Sein JSON-Urteil unverändert nach `auftraege/<auftrag>/protokolle/<spec>.lauf-<n>.pruefer.json` schreiben – nur das
  JSON-Objekt (Code-Fences und Text drumherum weglassen, am Inhalt nichts ändern).
  Beispiel für `auftraege/A-1/platte.yaml` (Dateistamm `platte` = Name der Spezifikationsdatei ohne `.yaml`), Lauf 2:
  Freigabe-Kopie `auftraege/A-1/platte.freigegeben.yaml`, Prüfbericht
  `auftraege/A-1/protokolle/platte.lauf-2.pruefbericht.json`, Urteil
  `auftraege/A-1/protokolle/platte.lauf-2.pruefer.json`.

## 6. Schleife
- `swki status <spec>` (optional `--max N`, wenn der Nutzer eine Zahl genannt hat) → `empfehlung`:
  - `nachbessern`: nur den Bauweg ändern (Anker, Reihenfolge, Handler-Optionen, Skripte). Anforderungen (Parameter,
    Material, Eigenschaften, Prüfwerte) sind tabu – `swki bauen` verweigert sonst (FREIGABE_VERALTET). Hält Claude eine
    Anforderung für falsch: Nutzer fragen. Dann neu bauen (Schritt 5).
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
