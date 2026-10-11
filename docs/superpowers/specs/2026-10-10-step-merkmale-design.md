# Prüfen ohne Bilder: Merkmalsbericht aus der STEP und Vorprüfung vor dem Bau

Stand 10.10.2026, Branch `ccr-7fed9b39-on3n01`. Auftrag des Nutzers: Aufgaben dauern zu lange, das Modell prüft
visuell. Idee des Nutzers: das gebaute Teil als STEP (o. ä.) auslesen und daran prüfen statt an Screenshots. Eingaben
sind meist Text, höchstens Handskizzen – keine Maßzeichnungen.

## 1. Ausgangslage (Messstand, Umbau 4)

- Modell (Denken, Schreiben) 60–75 % der Zeit, Prüfer 12–20 %, SolidWorks 15–20 %.
- Der Prüfer liest Eingabe, Spec, Prüfbericht und vier Screenshots und läuft **nach** dem Bau. Ein Deutungsfehler
  fällt erst dort auf und kostet einen Lauf und eine neue Freigabe (~100 s).
- Die Prüfung „gebautes Teil = Spec“ macht `swki pruefen` schon im Code, aber nicht vollständig: ob jedes Feature
  gebaut ist und auf der richtigen Seite sitzt, sah bisher nur der Prüfer in den Bildern.
- `swki bauen` speichert je Lauf schon `<name>.step` (SolidWorks-Standard, AP203/214, mm).

## 2. Neuer Ablauf (Einzelteile)

```
Spec schreiben → swki validieren (liefert vorpruefung_auftrag)
  → Prüfer: Vorprüfung (Eingabe + Spec, nur Text)      ┐ bei erteilter Freigabe parallel
  → swki durchlauf --freigeben (bauen, prüfen inkl. merkmale) ┘
  → swki urteil --vorpruefung → status bestanden → Bericht
```

- **Vorprüfung** (Prüfer-Agent, Abschnitt „Vorprüfung“): Setzt die Spec die Eingabe vollständig und richtig um
  (Maße, Lage, Seite, Prüfwerte)? Das ist die einzige Frage, die eine unabhängige Deutung braucht. Urteil in
  `protokolle/<spec>.vorpruefung.json` mit SHA-256 des Spec-Texts.
- **Prüfung `merkmale`** (Code): Die STEP des Laufs wird gelesen, jedes Feature der freigegebenen Spec gesucht.
- **Ersatz des Prüfers nach dem Bau:** `swki status` zählt das Vorprüfungs-Urteil als Urteil eines Laufs, wenn
  (a) genau der vorgeprüfte Text freigegeben ist (`kopie_sha256` in `freigabe.json`) und (b) die Prüfung `merkmale`
  ok ist und nichts offen lässt (Ausnahme: Lücken, die `formschraegen`/`koerper` abdecken). Sonst bleibt der Prüfer
  nach dem Bau nötig – dann text-basiert mit `merkmale.txt`, Screenshots nur, wo der Abgleich Lücken hat.
- `swki durchlauf --freigeben` hält an (`schritt: vorpruefung`), wenn eine Vorprüfung desselben Spec-Texts Mängel hat.
- `swki urteil <spec> [--vorpruefung] [--lauf n]` legt ein Urteil ab (stdin oder `--json`, Code-Fences werden
  weggelassen) und liefert Status und bei `bestanden` den Bericht – ersetzt Heredoc + status + bericht.
- Baugruppen: unverändert (Prüfer nach dem Bau), nur `swki urteil` als Abkürzung.

## 3. Bausteine

| Modul | Aufgabe |
|---|---|
| `swki/pruefung/step.py` | ISO-10303-21 lesen (reines Python, keine CAD-Bibliothek): Körper, ADVANCED_FACE mit Trägerfläche (Ebene, Zylinder, Kegel, Torus, Kugel), same_sense, Randpunkte (Kreisbögen alle 15°), Einheiten (mm, m, Zoll; rad, Grad). |
| `swki/pruefung/merkmale.py` | Flächen → Merkmale: Bohrungszüge (innere volle Zylinder/Kegel auf einer Achslinie; Enden offen/Boden/Spitze; Senkung, Tiefe von der Eintrittsseite), Zapfen, Rundungen (Teilzylinder, Torus), ebene Flächen je Richtung und Höhe, schräge Ebenen, freie Kegel, Hüllquader, Körper. SolidWorks teilt volle Zylinder in zwei Hälften – sie werden zusammengefasst. Textform ≤ 60 Zeilen. |
| `swki/pruefung/abgleich.py` | Freigegebene Spec ↔ Merkmale: `bohrung` (Ø, durch/blind, Eintrittsseite, Tiefe, Senkung), `normbohrung` (Lage, durch/blind, Seite; Größe prüft weiter `normbohrungen`), Kreise in `extrusion`/`schnitt` (Zapfen bzw. Loch, Innen/Außen über Umriss-Schachtelung), `verrundung` (Radius vorhanden), `fase` (Winkel vorhanden), `muster_linear`, `spiegeln` (Standardebene), `muster_kreis` (360°). Unerwartete Bohrungen sind Mangel, wenn alles abgebildet ist. |
| `swki/pruefung/vorpruefung.py` | Vorprüfungs-Urteil ablegen, Gültigkeit, Ersatz des Lauf-Urteils. |

Toleranzen: Lage 0,05 mm, Ø 0,02 mm, Tiefe 0,05 mm, Winkel 0,1°.
Kein neuer SolidWorks-API-Aufruf (die STEP entsteht schon in `swki bauen`).

## 4. Grenzen

- Nicht abgebildet (→ `nicht_geprueft`, Prüfer nach dem Bau mit Bildern): `rotation`, `skript`, `verzahnung`,
  Konturen, Kreismuster mit Teilwinkel oder quer zur Achse, Spiegeln an Nicht-Standardebenen, Flächen über `nahe`
  ohne passende Ebene im Teil.
- Gewinde sind kosmetisch und nicht in der STEP – Größe und Norm prüft weiter `normbohrungen` über SolidWorks.
- Taschen und Absätze aus Rechtecken/Polygonen werden nicht einzeln gesucht; sie stehen im Merkmalsbericht (Ebenen
  mit Höhe) und sind über `volumen`/`huellquader`/`masse_pruefen` abgedeckt.

## 5. Erprobung

- Ohne SolidWorks getestet: echte SolidWorks-2025-STEP (`tests/referenz/motorhalter/muster/gm42-10.step`) und ein
  mit CadQuery erzeugtes Testteil (`tests/pruefung/daten/platte_merkmale.step`: Senkbohrungen, Blindbohrung, Kernloch
  mit Spitze, Tasche mit Eckradius, Zapfen, Verrundung, Fase).
- **Offen (live, auf dem Rechner des Nutzers):** `swki merkmale <lauf>/<name>.step` an Läufen der Referenz-Suite
  ansehen; Regressions-Suite; Messstand-Durchgang mit überwiegend Textaufgaben (z. B. 3 Text-Teile, 1 Baugruppe,
  1 Skizze) gegen Umbau 4.
