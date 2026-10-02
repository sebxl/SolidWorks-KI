# Stufe 3a – Ergebnisse (Normteile)

Fertig-Kriterium Spec 3a §12 für Rechner A (SW 2025) erfüllt: Normtabellen für ISO 4762, ISO 4032, ISO 7089 und ISO 8734
(je Größen M5, M6, M8, M10, M12, M16 bzw. Ø 4, 5, 6, 8, 10, 12) sind mit Web-Recherche abgeglichen (24 von 24 Größen, keine
gesperrt), je Bauvorlage liegt ein Prüfer-Urteil „bestanden“ vor, die Stichprobe mit 21 Teilen besteht, und die Referenzen
(Buchse, Formplatte, Auswerferhalteplatte) bestehen weiter. 449 Unit-Tests grün. Rechner B (SW 2026) offen.

## Stand

- Datum: 02.–03.10.2026, Rechner A (SOLIDWORKS 2025), Branch `stufe-3a` (von `plan-stufe-3a` a69a9f8, Merge-Base `main` 5b9d774).
- Commits (ohne Push):

| Task | Inhalt | Commits |
|---|---|---|
| 1 | Spike S11 | a50ee9c |
| 2 | Feature-Typ `referenz` (Bezugsachse, Bezugsebene) | d67c8e7, 1589311 |
| 3 | Messpunkt `referenz`, `pruefung.durchmesser_pruefen` | c673c4b, fc753d1 |
| 4 | Konfiguration `normteilbibliothek`, Normtabellen-Modul (Schema, Regeln, Quellenpflicht) | 88cdf78, f0694e7 |
| 5 | Anfrage auflösen, Spezifikation aus Vorlage, Prüfsummen | 06f21e5 |
| 6 | Bau mit Selbstprüfung, Bibliothek, Befehle `swki normteil` | 2631f53 |
| 7 | ISO 4762 (Tabelle, Bauvorlage, Tests) | 8de0742, d56d94d |
| 8 | ISO 4032 | d056c04 |
| 9 | ISO 7089, ISO 8734, Passung zu Normbohrungen | a6acb60 |
| 10 | Abgleich mit Web-Recherche, Nutzerentscheidungen | 7b30f25, dd787b8 |
| 11 | Prüfer-Urteile je Vorlage, `hole` live, Stichprobe | feb2024 |
| 12 | Skill `normteile`, `CLAUDE.md`, Design §8/§11, Ergebnisse | e8ddf87, dieser Commit |

## Unit-Tests

`.venv\Scripts\python.exe -m pytest -q`: **449 bestanden, 95 abgewählt** (die `sw`-markierten Live-Tests). Vor dem Plan:
349 bestanden, 55 abgewählt. Zuwachs je Task (bestanden): Task 2 +10 (359), Task 3 +10 (369), Task 4 +31 (400), Task 5 +11
(411), Task 6 +11 (422), Task 7 +7 (429), Task 8 +6 (435), Task 9 +14 (449); Tasks 1, 10–12 ohne neue Unit-Tests. Die
40 zusätzlichen abgewählten Tests sind Live-Tests: `test_live_referenz` 1, `test_live_durchmesser` 1,
`test_live_normteile` 13, `test_live_normteil_hole` 4, `test_live_normteile_stichprobe` 21.
`swki api pruefe-code`: keine Befunde (`max_jahr` 2025). `swki normteil tabellen-pruefen`: `"gueltig": true`, 6 Größen je
Norm, nichts gesperrt.

## Live-Ergebnisse (SolidWorks 2025, Rechner A)

Alle Live-Tests liefen dateiweise (`tests\live_einzeln.py`, `--zeit 240`, `PYTHONIOENCODING=utf-8`), jeweils mit genau einer
SolidWorks-Instanz und Toggle 10 / Integer 6 = `False 1` vor und nach dem Lauf (Private Bytes von `SLDWORKS.exe`).

| Datei | Ergebnis | Private Bytes vorher → nachher | Task |
|---|---|---|---|
| `test_live_referenz.py` (1) und `test_live_muster.py` (3) | alle OK | 419 → 1060 MB | 2 |
| `test_live_durchmesser.py` (1), `test_live_pruefen.py` (2) | alle OK nach Fix fc753d1 (siehe Erkenntnis unten) | 827 → 1303 MB | 3 |
| `test_live_normteile.py` (13: ISO 4762 ×3, ISO 4032 ×3, Verfälschung ×1, ISO 7089 ×3, ISO 8734 ×3) | 13/13 OK | 1303 → 3170 MB | 7–9 |
| `test_live_normteil_hole.py` (4) | 4/4 OK | 1900 → 2534 MB | 11 |
| `test_live_normteile_stichprobe.py` (21) | 21/21 OK, in Blöcken (siehe Stichprobe) | 2285 → 3704 MB, nach Neustart 427 → 3324 MB | 11 |

Regression im Gesamtlauf (Task 12, 03.10.2026, Instanz PID 22756, 0 offene Dokumente, `False 1` vor und nach jeder Datei,
kein SolidWorks-Neustart nötig):

| Datei | Ergebnis | Private Bytes vorher → nachher |
|---|---|---|
| `tests\referenz` (Buchse, Formplatte, Auswerferhalteplatte) | 3/3 OK | 417 → 1297 MB |
| `tests\live\test_live_muster.py` | 3/3 OK | 1104 → 1526 MB |
| `tests\live\test_live_pruefen.py` | 2/2 OK | 1526 → 1800 MB |
| `tests\live\test_live_referenz.py` | 1/1 OK | 1800 → 1890 MB |
| `tests\live\test_live_durchmesser.py` | 1/1 OK | 1890 → 1941 MB |

Prüfwerte wurden in keinem Lauf angepasst. Der Fix fc753d1 betraf nur den Testaufbau (Parameter `D` → `Da`), nicht die Prüfwerte.

### Speicher

Der erste Bau nach einem SolidWorks-Neustart kostet einen Aufbausprung: 427 → 2036 MB (ca. +1,6 GB) beim ersten Bau von
Block 3 der Stichprobe. Jeder weitere Bau wächst um etwa 80–160 MB Private Bytes, einmal um 374 MB. Der Mittelwert der vier
Musterteile (424 → 2112 MB, ca. 420 MB je Bau) enthält diesen Aufbausprung und ist kein typischer Wert je Teil. Der Speicher sinkt
zwischendurch durch Freigabe nur teilweise. Deshalb lief die Stichprobe in Blöcken, je Test ein Prozess:
Block 1 (Stichprobe 0–6) 2285 → 3421 MB, Block 2 (7–8) 3189 → 3704 MB, danach Halt und SolidWorks-Neustart durch den Nutzer,
Block 3 (9–20) 427 → 3324 MB (Zwischenwerte: 2036, 2184, 2313, 2405, 2469, 2522, 2682, 2826, 2969, 3114, 3255, 3324 MB). Die
Grenze von ca. 3,8 GB wurde nicht überschritten. Für größere Läufe (z. B. weitere Normen) sind Neustarts einzuplanen.

## Spike S11

Rohdaten: `docs/stufe0/ergebnisse/s11_normteile.json`, Code `spikes/s11_normteile.py`. Antworten auf die vier Fragen:

1. **Bezugsebene deckungsgleich und mit Abstand: geht.** `InsertRefPlane` (Constraint 4 bzw. 8) erzeugt ein Feature vom Typ
   `RefPlane`, per `FeatureByName` wiederzufinden. Die **Normale steht in `ArrayData[6:9]`** (dritte Zeile, nicht die dritte
   Spalte `[2, 5, 8]`), der Ursprung in `ArrayData[9:12]` (m). Ebene „oben“ (XZ): Normale +Y; mit Abstand 12 mm Ursprung (0, 12, 0).
2. **Achse aus vorne ∩ rechts: geht.** `InsertAxis2(True)` liefert ein Feature vom Typ `RefAxis`; `GetRefAxisParams` gibt
   Start- und Endpunkt (m); die Achse liegt parallel zu Y durch x = z = 0.
3. **Schraubenbauweg messbar: geht, aber nur mit überstehender Mittellinie.** Liegt ein Mittellinien-Endpunkt eines Rotationsprofils
   auf einem Profilpunkt (Mittellinie auf der Profilkante), meldet der Rebuild „Gleichungen: Code 1“ (`REBUILD_FEHLER`), auch
   in der Rückfallform `k`…`k+1`. Ursache nach Variantentest: die Skizze legt je Kennpunkt ein Lagemaß an; liegt der
   Mittellinienpunkt auf einem Profilpunkt, entsteht ein zweites Maß auf denselben Punkt, und die Gleichung darauf scheitert.
   Mit der Mittellinie `von [0, "=-l-1"]`, `bis [0, "=k+1"]` (an **beiden Enden** über das Profil hinaus) baut das Teil voll bestimmt,
   und alle fünf `flaeche_in_richtung`-Aufrufe sind eindeutig (Abstände k = 8, l = 30, s = 6, t = 4, Zylinderradien 4,0 und 6,5 mm
   wie erwartet). Gilt für Profile, die die Achse berühren (ISO 4762, ISO 4032, ISO 8734); ISO 7089 (Ring) braucht es nicht.
   Der Schutz im Compiler (Doppelmaß auf Profilpunkt vermeiden) ist nicht umgesetzt (siehe Offene Punkte).
4. **Werkstoffe: 4 von 5 vorhanden.** `1.1191 (C45E)`, `1.7225 (42CrMo4)`, `1.4301 (X5CrNi18-10)`, `1.0038 (S235JRG2)` gefunden;
   **`1.3505` fehlt** in allen fünf Materialdatenbanken (kein Name mit `1.3`, kein Treffer auf 100Cr6/52100/Wälzlager). Ersatz
   für ISO 8734 Variante St: `1.2210 (115CrV3)` (siehe Entscheidungen).

## Erkenntnis aus Task 3: Groß-/Kleinschreibung bei Parametern

SolidWorks-Gleichungen unterscheiden Groß- und Kleinschreibung nicht. Zwei Parameter, die sich nur darin unterscheiden
(`d` und `D`), kollidieren: SolidWorks lehnt die globale Variable ab (`Globale Variable D = 20 abgelehnt`). Der Live-Test
`test_live_durchmesser` wurde deshalb auf `Da` umgestellt (fc753d1). Die Normtabellen sind kollisionsfrei (geprüft:
`d, dk, k, s, t, p, l` / `d, s, m` / `d1, d2, h` / `d, c, l`). Der Skill `normteile` nennt die Regel für neue Vorlagen;
`validieren` erkennt die Kollision noch nicht (siehe Offene Punkte).

## Abgleich der Normtabellen

Rohdaten der Web-Recherche: `docs/stufe3a/abgleich/<norm>.<a|b>.json` (zwei getrennte Quellenkreise je Norm) und
`…laengen.<a|b>.json` (Nachrecherche ISO 4762 und ISO 8734). Ein Wert gilt als abgeglichen, wenn ≥ 2 unabhängige Quellen
ihn bestätigen; Claudes Normwissen zählt nicht. Unabhängig heißt: verschiedene Unternehmen/Organisationen über beide
Rechercheläufe hinweg; je Unternehmen steht genau eine URL in `quellen`. Ergebnis: **24 von 24 Größen abgeglichen, keine
Maßkorrektur** (alle Tabellenwerte wurden von den Quellen bestätigt), keine Größe gesperrt.

| Norm | Quellen (Unternehmen) | Maße | Längenreihe |
|---|---|---|---|
| ISO 4762 | 13 für die Maße (u. a. fasteners.eu, Fuller, Wegertseder, Reyher, iTeh-Vorschau der ISO-Norm); dk, k, s je Größe 11–12, t 5–6, p 6–7 | alle bestätigt | nach Nachrecherche unverändert gegenüber dem Planstand: M5 8…50, M6 10…60, M8 12…80, M10 16…100, M12 20…120, M16 25…160 |
| ISO 4032 | 7 (schraube-mutter.de, Wegertseder, schrauben24.biz, fasteners.eu, Fuller, AmesWeb, MechaHandbook) | s, m je Größe von 7 bestätigt | keine (Mutter) |
| ISO 7089 | 7 (fasten.it, fasteners.eu, Hasler/Bossard BN715, schraube-mutter.de, schrauben-lexikon.de, theo-schrauben.de, Wegertseder) | d1, d2 je Größe von 7, h von 6 bestätigt | keine (Scheibe) |
| ISO 8734 | 5 für die Maße (Mühl, Fuller, iTeh/ISO-8734-Normtext, Seimatec, Reyher); für die Längen 9 Händler (neue-physik und schraubenhandel24 aus Runde 1, dazu 7 aus der Nachrecherche: Seefelder, Dunken, Der Schraubenladen, Biker-Normalien, Intafast, Blohm, Theo Schrauben) | d von 4 Unternehmen; c je Größe von 4–5, bei Ø 5 widersprüchlich (siehe unten) | Schnittmenge der Quellen ∩ ISO-Nennlängen; ohne 35 und 36 |

Besonderheiten:

- **ISO 4032:** schrauben24.biz zeigt ISO- und DIN-Werte gemeinsam; nur die ISO-Werte zählen (M10 s 16, M12 s 18, abweichend von DIN 934).
  Die Tabelle trägt dazu einen Hinweis.
- **ISO 7089:** schraube-mutter.de nennt DIN 125 A / ISO 7089 gemeinsam (gleiche Zahlen); auch ohne diese Quelle bleiben ≥ 5.
- **ISO 4762, Längen:** Die erste Recherche fand die kurzen Längen (M5 8…16, M6 10…16, M8 12…16, M10 16) nur bei EKINSUN; sie
  entfielen zunächst. Auf Wunsch des Nutzers folgte eine Nachrecherche: Der ISO-Normtext (DIN EN ISO 4762:2004, bolt.msk.ru;
  die Kopien iTeh/Aramfix zählen als eine Quelle) plus EKINSUN, Wegertseder, Boellhoff, TR Fastenings (Farnell) und Aspen belegen
  sie (je Länge ≥ 4 Unternehmen). Nur Längen aus der Normreihe des ISO-Textes werden übernommen; Händler-Lagerlängen außerhalb der
  Norm (z. B. M5 14, 55, 60; M8 75, 90, 110; M10 75, 85, 110…) bleiben draußen.
- **ISO 8734, Ø 5, Maß c (Fasen-Richtwert):** Widerspruch, deshalb vorübergehend gesperrt. 0,8 nennen Mühl, Fuller und der
  ISO-Normtext (iTeh, Table 1), 0,98 nennen Reyher und Seimatec. Der Nutzer entschied am 02.10.2026: c = 0,8 (Eintrag
  `entscheidung` in der Tabelle, Status `abgeglichen`).
- **ISO 8734, Längen:** Reihe = Längen, die ≥ 2 unabhängige Unternehmen je Größe nennen und die in der ISO-Nennlängenreihe stehen.
  36 (alle Größen) ist DIN-6325-/Handelslänge und entfällt; 35 hat nur eine Quelle; der Nutzer bestätigte: weder 35 noch 36
  (Hinweis in der Tabelle). 65, 75, 85, 95 nennt keine Quelle. Dünn belegt (DIN-6325-Händlerlisten): Ø 5 L 6 (nur Dunken und Intafast) und Ø 12 L 18 (nur Blohm und
  Intafast); Ø 5 L 70 nennen Dunken, schraubenhandel24, Seefelder und Theo (die letzten drei mit identischen Listen).
- **Werkstoff ISO 8734, Variante St:** `1.2210 (115CrV3)` statt `1.3505` (100Cr6), weil 1.3505 in der SW-Materialdatenbank fehlt
  (Spike S11). Gewählt: ein für Zylinderstifte DIN 6325/ISO 8734 von Herstellern genannter Werkstoff mit praktisch gleicher Dichte.

## Prüfer-Urteile

Je Bauvorlage hat der unabhängige Prüfer-Agent (`pruefer`, Eingabe: Tabelle, Spezifikation, Prüfbericht, Screenshots) ein
Musterteil beurteilt (`swki normteil muster`), das Urteil liegt per `swki normteil urteil` neben der Vorlage
(`swki/wissen/normteile/vorlagen/<norm>.pruefer.json`, an die Vorlagenprüfsumme gebunden):

| Norm | Musterteil | Vorlagenprüfsumme (Anfang) | Urteil (02.10.2026) |
|---|---|---|---|
| ISO 4762 | M5 × 8, 8.8 | 9c345bf9 | bestanden, keine Mängel |
| ISO 4032 | M5, 8 | 6231430d | bestanden, keine Mängel |
| ISO 7089 | M5, 200 HV | fab6eb26 | bestanden, keine Mängel |
| ISO 8734 | 4 × 6, St | 790eb057 | bestanden, keine Mängel |

Die Musterteile haben vorher die Selbstprüfung (Tabelle, Spezifikation, Bau, Maße, Volumen, Bezugsgeometrie) bestanden.
Ändert sich eine Vorlage, ist `hole` wieder `NORMVORLAGE_UNGEPRUEFT`, bis ein neues Urteil vorliegt.

## Stichprobe

`tests/live/test_live_normteile_stichprobe.py`: 20 Teile über alle Größen, Längen und Varianten, gezogen mit festem Seed 3
(gleichverteilt über alle Teile, daher dominiert ISO 4762), dazu ein Teil für die nicht vertretene Norm: **21 Teile, alle
bestanden.** Gezogen: 16 × ISO 4762 (M8×30 10.9, M16×45 A2-70, M12×110 12.9, M6×16 12.9, M10×50 10.9, M16×55 10.9, M12×45 12.9,
M16×70 8.8, M16×40 10.9, M5×25 10.9, M16×55 12.9, M12×45 8.8, M8×45 8.8, M12×120 12.9, M8×25 A2-70, M6×55 12.9),
3 × ISO 8734 (10×70, 10×50, 6×70, jeweils St), 1 × ISO 4032 (M10, 8); ergänzt: ISO 7089 M16 (A2). Dazu `test_live_normteil_hole.py`: `hole` für
ISO 4762 M8×30, ISO 4032 M8, ISO 7089 M8, ISO 8734 8×30, 4/4 bestanden. Läufe in Blöcken mit SolidWorks-Neustart (siehe Speicher).

## Präzisierungen gegenüber der Spec

Im Plan festgelegt und umgesetzt:

1. **Verfälschungstest (Spec §11):** Ein verfälschter Tabellenwert kann die Selbstprüfung nicht scheitern lassen (das Teil wird
   aus diesem Wert gebaut und gegen ihn gemessen). Getestet wird (a) eine verfälschte Vorlage (falscher Bauweg, Prüfung
   unverändert) → Selbstprüfung scheitert, nichts wird abgelegt; (b) ein Tabellenwert, der eine Regel verletzt → `NORMTABELLE_UNGUELTIG`.
   Der Live-Test fordert dabei nur den Mangel `mass:t`; das Sollvolumen folgt dem Bauweg (siehe Entscheidungen).
2. **Sollvolumen:** `pruefung.volumen.soll: auto` (analytisch aus der Spezifikation) statt handgeschriebener Formel; Fasen liegen dafür
   im Rotationsprofil. Je Norm sichert eine unabhängige Handrechnung die Rechnung ab (Unit-Tests, relative Abweichung 1e-9).
3. **Prüfer-Ablauf:** zwei zusätzliche Befehle `swki normteil muster` und `swki normteil urteil … --vorlage-pruefsumme`.
4. **Neue Messarten** (gelten für alle Teile): Messpunkt `{referenz: <id>}` und `pruefung.durchmesser_pruefen` (Zylinderfläche durch
   einen Punkt, optional koaxial zu einer Bezugsachse).
5. **Mutter ISO 4032:** „Fasen beidseitig“ = 90°-Senkung an beiden Bohrungskanten (Senk-Ø 1,1·d); Eckfasen am Sechskant entfallen
   (vereinfachte Darstellung, wie das Gewinde).

Abweichung von Spec §6 („jedes Tabellenmaß gemessen“): Bei ISO 4762 sind die Schaftfase `p` und die Kopffase `k/10` nicht direkt
gemessen; das Volumen deckt `p` nur bei kleinen Größen. Bei ISO 8734 ist `c` nur über das Volumen belegt. `mass:EINBAU_EBENE`
ist bei ISO 4762 äquivalent zu `mass:k`.

## Entscheidungen während der Umsetzung

Rulings des Controllers (jeweils mit Begründung; „kostet bei Irrtum“ = Aufwand der Korrektur):

- **Mittellinie (Task 1):** In allen Vorlagen, deren Profil die Achse berührt (ISO 4762 f1, ISO 4032 f2, ISO 8734 f1), steht die
  Mittellinie an beiden Enden 1 mm über dem Profil (z. B. von `[0, "=-l-1"]` bis `[0, "=k+1"]`). ISO 7089 bleibt wie im Plan.
  Grund: Spike-Beleg Frage 3. Bei Irrtum nur eine Vorlagenänderung plus neues Prüfer-Urteil.
- **Werkstoff ISO 8734 St (Task 1):** `1.2210 (115CrV3)` statt `1.3505`. Grund: 1.3505 fehlt in der SW-Datenbank; 1.2210 wird von
  Herstellern für Zylinderstifte genannt, Dichte praktisch gleich. Bei Irrtum nur eine Tabellenänderung (Prüfsumme → Neubau im Cache).
- **`referenz`-Ebene (Task 2):** meldet `richtung` immer als Basisnormale; `umkehren` ohne `abstand` ist ein Plausibilitätsbefund.
  Grund: Der Flip verschiebt nur die Lage, die Normale bleibt (live belegt in `skizze.py`); der Plan-Code war hier falsch.
- **Quellenpflicht und Laden (Task 4):** (1) je Größe zählt die Menge verschiedener URLs, nicht Nennungen (Spec verlangt ≥ 2 unabhängige
  Quellen; doppelte URL oder Größe darf nicht doppelt zählen). (2) `lade_normtabelle` prüft nach `safe_load` auf `dict`, normalisiert
  nur bei passendem Typ und meldet sonst `NORMTABELLE_UNGUELTIG` (Spec §8: JSON-Fehler mit Code). Beides strenger, kostet nichts.
- **Verfälschungstest (Task 7):** fordert nur `mass:t`. Grund: Das Sollvolumen (`auto`) folgt der verfälschten Spezifikation, der
  Bauwegfehler wird von `masse_pruefen` gefangen; ein Freigabe-Parameter für `baue_und_pruefe` wäre Überbau.
- **Recherche vorgezogen (Task 6):** Der Recherche-Workflow aus Task 10 lief parallel zu Task 6 und zum SolidWorks-Neustart; er braucht
  weder SolidWorks noch die Tabellendateien. Die Ergebnisse wurden erst in Task 10 eingepflegt.
- **Zwei Recherche-Agenten je Norm:** getrennte Quellenkreise (A: Bossard, Würth, Fabory, Reyher, Böllhoff …; B: Hoffmann, Kipp, Norelem,
  Ganter, Misumi, Normauszüge/Händler …), Rohdaten je Agent als `docs/stufe3a/abgleich/<norm>.<a|b>.json`. Erhöht die Chance auf ≥ 2
  unabhängige Quellen; 8 Agenten liegen unter dem Richtwert von 10.
- **Abgleich von `d`:** gilt als von jeder Quelle bestätigt, die die Größe (M8 bzw. Ø 8) führt, denn `d` ist die Größenbezeichnung
  selbst und steht in keiner Tabelle als eigene Zahl.
- **Unabhängigkeit:** verschiedene Unternehmen/Organisationen über beide Rechercheläufe hinweg; dieselbe Domain/Firma in a und b zählt
  einmal; je Unternehmen genau eine URL in `quellen` (der Code zählt URLs, daher muss die Tabelle selbst entdoppelt sein). Bei Irrtum
  zu strenge Sperren.
- **ISO 8734, Zusatzfilter „nur ISO-Nennlängen“ (Task 10):** 36 Händlerlängen verworfen. Grund: Global Constraint „nur Längen aus der
  Längenreihe der Norm“; 36 ist DIN-6325-/Handelslänge. Bei Irrtum: Länge 36 nicht abrufbar.
- **Task 12, Steps 1–3 vorgezogen:** Skill, `CLAUDE.md`, Design-Dokument und `konstruieren`-Verweis wurden während des SolidWorks-Neustarts
  vor Task 11 erledigt (reine Doku, unabhängig von Task-11-Ergebnissen).
- **Stichprobe ergänzt (Task 11):** je ein zufälliges Teil (fester Seed) für jede in den 20 nicht vertretene Norm (heute ISO 7089) →
  21 Teile; die 20 gezogenen bleiben unverändert. Grund: Spec §12 verlangt ≥ 20 Teile über alle Normen, der Plan-Code zieht gleichverteilt
  über Teile und lässt ISO 7089 aus.

Entscheidungen des Nutzers (02.10.2026):

- ISO 8734 Ø 5: **c = 0,8** (Größe wieder `abgeglichen`).
- ISO 4762 kurze Längen M5–M10: **gezielt nachrecherchieren** (Ergebnis: Längen wieder in der Tabelle, siehe Abgleich).
- ISO 8734 Längenbereich je Ø (35/65/75/85/95, Grenzen): **gezielt nachrecherchieren** (Ergebnis: Reihen erweitert, 65/75/85/95 ohne Beleg).
- ISO 8734 zwischen 32 und 40: **weder 35 noch 36** (Regel bleibt).

Am 03.10.2026 erlaubte der Nutzer ausdrücklich, SolidWorks für die Regression bei Bedarf selbst neu zu starten (ab ca. 3 GB
Private Bytes vor einer Datei); das war im Lauf nicht nötig.

## Offene Punkte

- **Kosmetisches Gewinde:** Normteile haben nur den Nenn-Ø, keine Gewindedarstellung.
- **Kaufteile:** Katalog je Hersteller und `normteil aufnehmen` nur für nicht genormte Kaufteile (eigenes Paket bei Bedarf).
- **Weitere Normen und Größen:** nur ISO 4762, 4032, 7089, 8734 mit je 6 Größen; neue Größen nur mit Abgleich (≥ 2 Quellen) und live gemessener Tabelle.
- **Rechner B (SW 2026):** nicht gelaufen; Bibliothek ist je SW-Version getrennt, die Vorlagen müssen dort einmal bestehen.
- **Stufe 3b (Baugruppen):** Standardverknüpfungen, Bestimmtheit, statische Kollision, Passung Normteil ↔ Normbohrung in der Baugruppe.
- **Compiler-Schutz Mittellinie:** Mittellinien-Endpunkt auf einem Profilpunkt führt zu „Gleichungen: Code 1“; die Vorlagen umgehen es
  mit überstehender Mittellinie, ein Schutz im Compiler (Doppelmaß vermeiden) steht aus.
- **`validieren` und Groß-/Kleinschreibung:** Parameter, die sich nur darin unterscheiden, werden nicht erkannt (SW lehnt die globale
  Variable ab); Kandidat für einen Plausibilitätsbefund.
- **Speicher:** SolidWorks wächst je gebautem Teil, Stichproben und Neubauten brauchen Neustarts.

Zurückgestellte Kleinbefunde aus den Reviews (Material für das Gesamt-Review, nichts davon blockiert):

- **Task 1:** Kommentar `spikes/s11_normteile.py:239` verweist auf einen nicht eingecheckten Bericht (Erkenntnis steht jetzt hier); Spike ohne
  `try` um `_ebene`/`_achse`/`flaechen`, JSON ohne Zeilenende (Wegwerf-Spike).
- **Task 2:** `REF_PLANE_DECKUNGSGLEICH` in `referenz.py` statt bei `REF_PLANE_*` in `skizze.py`; Achsberechnung doppelt in
  `muster.neue_referenzachse` und `topologie.referenz_geometrie`; `referenz_geometrie` ohne Unit-Test mit Attrappe; Anker
  (`flaeche`/`kanten`) auf eine `referenz`-ID scheitert ohne klare Meldung.
- **Task 3:** `bewerte`-Zweige `NichtMessbar` (nicht parallel) und „Messung fehlt“ ohne Test; `referenz` auf Nicht-Bezugsgeometrie
  erst zur Messzeit erkannt; `zylinder_durch_punkt` prüft den unendlichen Zylinder und nimmt bei zwei gleichen Treffern still den ersten;
  `validieren` erkennt Parameter-Kollisionen in der Schreibweise nicht (Finding fürs Gesamt-Review).
- **Task 4:** Normalisierungstest prüft unquotierte Schlüssel (`8`, `8.8`, Datum) nicht (relevant für ISO 4032 Variante „8“ und ISO 8734
  Größen „4“…); Quellen mit unbekannten Größen bleiben unbemerkt; Pfadformat „/“ statt „.“ in Befunden; Monotonie nach Dateireihenfolge
  inkl. gesperrter Größen; fehlende Randtests; komplexe Zahl/Überlauf in Regeln nicht gefangen.
- **Task 5:** `NORMLAENGE_UNGUELTIG`-Text zeigt „None“ bei fehlender Nachbarlänge; Größe/Variante case-sensitiv („m6x12“, „a2“); `gesperrt` erst
  nach Längen/Variante gemeldet; `spec_befunde`-Parameter `ordner` ist semantisch der Auftragsordner; Teile ohne Länge (`laenge: false`) in den
  Task-5-Tests ungetestet (kommt mit ISO 4032/7089); `loese_auf` validiert die Tabelle nicht vorher (`hole` ruft `pruefe_tabelle` danach).
- **Task 6:** `bau.py`: Ausnahmen in `messe`/`bewerte`/`screenshots`/`speichere` kommen roh heraus (Protokoll steht schon auf ok, kein
  `NORMTEIL_PRUEFUNG` mit Ordner); `muster` nimmt die erste Tabellenzeile/Länge statt der kleinsten; defekte Eintrags-JSON bricht
  `hole`/`liste` roh ab; `.sldprt` ohne JSON in `liste` unsichtbar; kein Unit-Test für `baue_und_pruefe`; `fehler_dict` doppelt.
- **Task 7:** `p` und Kopffase `k/10` nicht direkt gemessen (siehe Abweichung von Spec §6); `mass:EINBAU_EBENE` äquivalent zu `mass:k`.
- **Task 8:** Kopfkommentare von `iso4032` (Abgleich-Satz, Senkung nicht normativ) dünner als bei `iso4762`.
- **Task 9:** `EINBAU_EBENE_2`-Lage nur als Betrag belegt (Messung gegen +y mit Soll 0 wäre direkter); `c` (ISO 8734) nur über das
  Volumen; keine Passung Scheibe ↔ Schraube.
- **Task 10:** Mühl-URL deckt Ø 10/12 nicht (zweite Mühl-Seite 6325_c1); EKINSUN-Längen aus Bereich plus ISO-888-Reihe abgeleitet; ISO 7089 `h` meist
  unbeschriftet; schraubenhandel24-URL nur für d4; bolt.msk.ru und iTeh als zwei URLs in `quellen` von ISO 4762 (fachlich eine Quelle, für keine
  Größe tragend); schraubenhandel24/Seefelder/Theo mit identischen Listen (Runde 1 vs. 2 uneinheitlich, alle Längen trotzdem ≥ 2);
  dünne Belege ISO 8734 Ø 5 L 6, Ø 5 L 70, Ø 12 L 18 (DIN-6325-Händler).
- **Task 12 Teil 1:** Skill `normteile`: `tabellen-pruefen` zeigt Anzahl Größen und gesperrte; Herkunft von `<x>` für `--vorlage-pruefsumme`
  (aus `muster`) nennen; Leerzeile vor „## Fehlercodes“.
