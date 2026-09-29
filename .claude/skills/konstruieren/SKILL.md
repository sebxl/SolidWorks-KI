---
name: konstruieren
description: Konstruiert ein Einzelteil in SolidWorks aus Skizze, Beschreibung oder Anweisung – Spezifikation schreiben, validieren, Rückfragen, Freigabe durch den Nutzer, bauen, prüfen, unabhängiger Prüfer, nachbessern, Bericht. Verwenden, wenn der Nutzer ein Teil konstruiert, gebaut oder geändert haben will.
---

# Konstruieren (Einzelteil, Stufe 2)

Alle Befehle: `.venv\Scripts\python.exe -m swki …` (Ausgabe JSON, Exit 0 = ok). Längen in mm, Winkel in Grad.

## 1. Auftrag anlegen
- Ordner `auftraege/<auftrag>/` (Name wie vom Nutzer, sonst kurz und sprechend), Eingaben nach `eingabe/`.
- Ein Teil je Auftrag.

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
- Was das Schema nicht abbildet: `typ: skript` mit `luecke:` und Datei `skripte/<id>.py` (`def bauen(ctx)`), nie weglassen.
- `pruefung` immer füllen: `huellquader` [X, Y, Z], `volumen` (`auto` oder Wert), wichtige Maße unter `masse_pruefen`,
  `schwerpunkt` für Symmetrie/Spiegelfehler.

## 3. Validieren und Rückfragen
- `swki validieren <spec>` bis `"gueltig": true`.
- `hinweise` aus `validieren` (feste Zahlen in maßtragenden Feldern) vor der Freigabe beheben – meist als Parameter –
  oder dem Nutzer bei der Freigabe ausdrücklich nennen.
- Unklarheiten in der Eingabe (fehlende Maße, Toleranzen, Material) gesammelt beim Nutzer erfragen, nicht raten.

## 4. Freigabe (einziger menschlicher Eingriff)
- Dem Nutzer die Anforderungen zeigen: Parameter, Material, Eigenschaften, Prüfwerte, Feature-Liste in Worten.
- Erst nach ausdrücklichem OK: `swki freigeben <spec>` (legt `<name>.freigegeben.yaml` ab; diese Kopie nie ändern).

## 5. Bauen, prüfen, Prüfer
- `swki bauen <spec>` → Lauf n (Protokoll unter `protokolle/`). Bei Bauabbruch: Fehlercode und Knoten lesen.
- `swki pruefen <spec> --lauf n` → Prüfbericht + Screenshots.
- Prüfer-Agent (`subagent_type: pruefer`) starten mit den Pfaden: Eingabeordner, freigegebene Spezifikation
  (`<name>.freigegeben.yaml`), Prüfbericht, Screenshot-Ordner des Laufs. Keine Protokolle, keine Skripte übergeben.
- Sein JSON-Urteil unverändert nach `auftraege/<auftrag>/protokolle/<spec>.lauf-<n>.pruefer.json` schreiben.

## 6. Schleife
- `swki status <spec>` (optional `--max N`, wenn der Nutzer eine Zahl genannt hat) → `empfehlung`:
  - `nachbessern`: nur den Bauweg ändern (Anker, Reihenfolge, Handler-Optionen, Skripte). Anforderungen (Parameter,
    Material, Eigenschaften, Prüfwerte) sind tabu – `swki bauen` verweigert sonst (FREIGABE_VERALTET). Hält Claude eine
    Anforderung für falsch: Nutzer fragen. Dann neu bauen (Schritt 5).
  - `stopp_max` / `stopp_kein_fortschritt`: anhalten, Nutzer mit Bericht informieren.
  - `bestanden`: weiter mit 7.
- Wiederholt sich ein Compiler-Problem, Skill `compiler-erweitern` anwenden.

## 7. Bericht
- `swki bericht <spec>` → `auftraege/<auftrag>/bericht.md`; dem Nutzer Status, offene Punkte und Screenshots zeigen.
