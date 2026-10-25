# Bewertungsbogen BTP – Ergebnisse

Bogen: `docs/superpowers/specs/2026-10-23-bewertungsbogen-design.md`. Audit: `2026-10-23-audit.md`. Recherche:
`recherche.md`. Auftrag der Goal-Session: `goal-auftrag.md`. Messdaten unter `<arbeitsordner>/MESSSTAND/` (nicht im
Git). Zielscore 6,5, höchstens 5 Umbauten.

## Einrichtung (24.10.2026, Branch `btp`)

- Messstand erweitert: Score `werkzeuge/messstand/btp.py`, Aufgabe `pruefstation` (Vorlage + Ausgangslauf),
  Fallen `werkzeuge/messstand/fallen.py` mit F1–F6, R1–R2 (`tests/messstand/fallen/`).
- Stand der Messung: `main` mit Paket Bemaßungsbezug (PR #17) und AP 6.8 (602dc8f), gemergt in `btp`.
- Vorlage Prüfstation: AP 6.8 Stand Lauf 28, eingefroren 24.10. (`MESSSTAND/vorlagen/pruefstation`); Freigabe der
  Vorlage gilt mit dem neuen Stand weiter.
- Referenz der Änderung (Kamerahalter ± 20, Schenkel B 12, M3 × 12): `MESSREF-pruefstation` Lauf 1, gebaut 263 s,
  `swki pruefen` bestanden (Kameraschrauben 3,4 mm Einschraubung wie vorher), STL `MESSSTAND/referenz/pruefstation.stl`.
  Referenzen der übrigen Aufgaben vom 09.10. (Geometrie unabhängig vom Code-Stand).

### Eigene Entscheidungen bei der Einrichtung

| Entscheidung | Begründung |
|---|---|
| Vorlage ohne `bezug` lassen (validieren meldet `bezug`-Hinweise) | Messung soll den echten AP-6.8-Stand abbilden; `bezug` ist Bauweg und wäre eine Änderung vor der Messung |
| Fallen-Aufträge `MESSFALLE-*` und Referenz `MESSREF-*` ohne Rückfrage freigeben | Bogen §6 sieht ihren Bau vor (vom Nutzer abgenommen); wie `MESSREF-*` am 09.10.; reine Messaufträge |
| Fallen-Prüfer als `general-purpose`-Agent mit eingebetteter `pruefer.md` des gemessenen Commits | Agenten-Definitionen lädt Claude Code beim Sitzungsstart; so prüft jeder Durchgang mit dem Prüfer seines Stands |
| Messdaten vom 09.10. nach `MESSSTAND/messstand-2026-10-09/` verschoben | `vorbereiten` legt Läufe unter `durchgang-<n>` an; die alten Ordner gleichen Namens wären überschrieben worden (bei Durchgang 0 ist das passiert, siehe unten) |
| Lauf `d0-durchlicht-2` wiederholt (`_ungueltig/d0-durchlicht-2-gestoert`) | Fallen F1/F2 wurden versehentlich gleichzeitig mit SolidWorks gebaut; Regel seitdem: nie zwei SolidWorks-Arbeiten gleichzeitig |
| Mess-Prompt: „Alle Schritte vor der Freigabe-Vorlage (auch der Konstruktionsreview) laufen wie im Betrieb“ | Ohne diesen Satz ließ ein Agent den Review aus (Freigabe war erteilt); Nutzerentscheidung „Review wie im Betrieb“ |
| Falle F4 mit gemessenem Sollvolumen, F1/F2 mit stimmigen Kommentaren | Fallen müssen `swki pruefen` bestehen und dürfen sich nicht über widersprüchliche Kommentare verraten |

## Durchgang 0 – Ausgangswert (24.10.2026, Commit 4d28320 auf `btp`)

| Lauf | Zeit s | Modell | Review | Prüfer | Werkzeug (durchlauf) | Tool-Aufrufe | Tokens gew. | Läufe | Fehlerpunkte | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d0-durchlicht-1 | 240 | 122 | 64 | 30 | 18 | 30 | 403123 | 1 | 0 | 3352 | ja |
| d0-durchlicht-2 | 253 | 131 | 58 | 39 | 19 | 31 | 356698 | 1 | 0 | 3357 | ja |
| d0-kamera-1 | 334 | 165 | 109 | 22 | 32 | 31 | 412767 | 2 | 1 | 3570 | ja |
| d0-zentrieraufnahme-1 | 195 | 103 | 23 | 27 | 32 | 28 | 305578 | 2 | 2 | 3570 | ja |
| d0-stehlager-1 | 343 | 204 | 64 | 20 | 46 | 41 | 492854 | 1 | 0 | 10354 | ja |
| d0-pruefstation-1 | 995 | 200 | 105 | 65 | 601 | 52 | 1078019 | 1 | 0 | 28155 | ja |

Fallen: 6 von 6 Treffern, 0 Fehlalarme; alle 24 Einzelurteile eindeutig (keine unklaren).

**Score 4,9** (Ziel 6,5):

| Gruppe | Wert | Teilscore |
|---|---|---|
| Zeit Teile | 258 s (durchlicht 247, kamera 334, zentrieraufnahme 195) | 1,3 |
| Zeit Stehlager | 343 s | 4,8 |
| Zeit Prüfstation | 995 s | 5,0 |
| Präzision erster Lauf | 3 Fehlerpunkte | 3,5 |
| Präzision Fallen | 6 | 10,0 |
| Aufwand | 1,0 (Bezug) | 5,0 |
| Robustheit | 28 155 MB | 0,0 |

**Wo die Zeit jetzt hängt:**
- **Konstruktionsreview** (seit 11.10., im Audit fehlend): 23–109 s je Lauf, bei den Teilen 25–33 % der Zeit. Er ist der
  Hauptgrund, warum die Teile gegenüber dem Messstand Umbau 5 (09.10.: ~140 s) bei ~250 s liegen.
- **Prüfstation:** Durchlauf 601 s (Bauen 256 s: Teile 105 – vorher 274 dank Bemaßungsbezug –, Verknüpfen 91,
  Grundstellung 22; Prüfen ~300 s; 2 Neustarts), Modell 200 s, Review 105 s, Prüfer 65 s.
- **Fehlerpunkte:** Kamera – Bezug `u: mitte` glich die Höhen der beiden M2 an (Zeichnung 20,25/20,22; Paket
  Bemaßungsbezug), Prüfmangel, zweiter Bauweg-Lauf. Zentrieraufnahme – falscher Messanker der Taschentiefe (Prüfwert),
  Prüfmangel und zweite Freigabe.
- **Speicher:** Prüfstation 27,5–28,2 GB beim Bauen (Verknüpfen/Grundstellung, ~390–480 s nach Laufbeginn), Prüfen
  ~14 GB. Vor dem Bemaßungsbezug lag die Spitze bei 14,3 GB. Ursache offen.

**Panne:** Die Rohdaten des Messstand-Durchgangs 0 vom 09.10. (gleiche Lauf-Namen `d0-*`) wurden von `vorbereiten`
überschrieben; die Zusammenfassung steht weiter in `docs/messstand/ergebnisse.md`, die übrigen Durchgänge liegen unter
`MESSSTAND/messstand-2026-10-09/`.

## Umbau 1 – Baugruppen-Latenz, Speicher, Präzisionsfehler, schlankerer Review (24.10.2026, Branch `btp-umbau-1`)

Gebündelt (Bogen §5.1 erlaubt Bündeln; Einzelhebel lägen meist unter +0,3), vier Commits:

| Commit | Inhalt | Recherche |
|---|---|---|
| 8e711ca | Bemaßungsbezug: `mitte`-Paare und Null-Lagen nur bei rechnerischer Gleichheit (1e-6 mm) statt in der Ankertoleranz 0,1 mm – Ursache des Kamera-Fehlerpunkts in D0 (M2 bei v 20,25/20,22 auf eine Höhe gezogen); ebenso Rechteck 0,05 neben dem Ursprung | neu (Fehlerpunkt D0) |
| a78b2f5 | Prüfen: Screenshots, Kopplungsbilder, Bewegungsprüfung in `sw.schnell`; Bilder schalten die Grafik kurz an (`sw.mit_grafik`) und die Ansichtsanimation aus; Grundstellung in `schnell`; Verknüpfen ohne Baumdurchlauf (`GetLastFeatureAdded` mit Namens- und Typprüfung `IMate2.Type`, Rückfall Baum, nie eine vorhandene); Ausrichtungsprüfung und Grundstellung über Handles; `SwMechanik` liest die Verknüpfungen einmal statt je Stellung; `verbinde` setzt `CommandInProgress` zurück | O1, O2, O3, O4 (Kopplungsbilder), A1 |
| b2f9dc9 | Agentenseite: Konstruktionsreview mit `model: sonnet`, `effort: medium` (Aufrufparameter im Skill + Frontmatter); kein Review für Kaufteil-Ersatzkörper und reine Parameter-/Schraubenlängen-/Normteiländerungen; Namensmuster in der Syntaxreferenz; Normale der Messanker („aus dem Material heraus“, Fehlerpunkt Zentrieraufnahme D0); kein Speichercheck nach `--neustart`; `pruefer_auftrag` nennt jede Datei und verlangt paralleles Lesen | O12, O13, O10 |
| 1c21de9 | Speicher: Norm-/Kaufteile beim Bauen und alle Teile beim Prüfen ohne Fenster öffnen (`DocumentVisible`); `schliesse` nimmt ein mitgeschlossenes Dokument hin | neu (Ursache 28 GB) |

**Speicherursache gefunden:** Ein sichtbar geöffnetes Normteil kostet SolidWorks ~1,7 GB Private Bytes, unsichtbar
~1 MB (Spike 24.10.). Die Prüfstation sprang in der Phase `normteile` in 10 Stufen à 1,48 GB von 10 auf 27 GB.
SolidWorks schließt unsichtbare Dokumente mit, sobald das sichtbare Dokument schließt, das sie hält (Baugruppe) –
deshalb nur dort unsichtbar, wo bis zum Schluss nichts Sichtbares geschlossen wird.

**Abnahme vor der Messung:**
- Entwicklungslauf Prüfstation (Vorlage, alter gegen neuen Code): Bauen 249 → 150 s, Spitze 27,5 → 10,7 GB; Prüfen
  362 → 47 s, Spitze 14,3 → 4,3 GB; Bewegungsprüfung je Bewegung 97 → 10 s. Prüfbericht Wert für Wert gleich (432
  Prüfungen, Bewegungen samt Lagen, Raum, Grenzen; nur die Reihenfolge der Liste `bewegt` variiert), Bilder pixelgleich
  bis auf Kantenrauschen (≤ 0,01 %; min/mitte/max unterscheiden sich deutlich, also keine veralteten Bilder).
- Live-Regression `tests/referenz` 11/11 OK (Stehlager 53 → 33 s, 10,6 → 4,7 GB; Schlitten 127 → 52 s;
  Zahnstangentrieb 135 → 89 s); dazu Live-Tests Baugruppe, Bewegung, Schlitten (4 Negativfälle inkl. zweiter
  Freiheitsgrad und umgekehrte Richtung), Kopplung, Zahnstangentrieb (4 Negativfälle), Stehlager, Bemaßungsbezug: 41/43
  OK. Die zwei Fehler (`test_manuelle_aenderung_an_der_baugruppe`, `…_in_der_baugruppe`) scheitern mit dem alten Code
  genauso (sie suchen eine globale Variable, die es seit dem Bemaßungsbezug ohne `gleichungen: true` nicht mehr gibt).
- Unit-Tests 1427 grün, `swki api pruefe-code` ohne Befund.
- Fallen mit dem neuen Stand neu gebaut (alle 8 bestehen `swki pruefen` wie vorgesehen); Stand von D0 gesichert unter
  `MESSSTAND/fallen-stand-d0/`.

## Durchgang 1 – Umbau 1 (24.10.2026, Commit 1c21de9 auf `btp-umbau-1`)

| Lauf | Zeit s | Modell | Review | Prüfer | Werkzeug (durchlauf) | Tool-Aufrufe | Tokens gew. | Läufe | Fehlerpunkte | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d1-durchlicht-1 | 166 | 92 | – | 51 | 16 | 19 | 310331 | 1 | 0 | 3361 | ja |
| d1-durchlicht-2 | 147 | 98 | – | 26 | 16 | 20 | 247490 | 1 | 0 | 3361 | ja |
| d1-kamera-1 | 210 | 132 | – | 55 | 16 | 19 | 296136 | 1 | 0 | 3366 | ja |
| d1-zentrieraufnahme-1 | 192 | 128 | 19 | 22 | 16 | 24 | 272965 | 1 | 0 | 3372 | ja |
| d1-stehlager-1 (ersetzt) | 555 | 290 | 50 | 17 | 62 | 46 | 604435 | 2 | 3 | 4942 | ja |
| d1-stehlager-2 (Wiederholung) | 353 | 244 | 37 | 22 | 34 | 41 | 538468 | 1 | 0 | 4407 | ja |
| d1-pruefstation-1 | 536 | 182 | – | 84 | 245 | 40 | 699933 | 1 | 0 | 11304 | ja |

Fallen: 6 von 6 Treffern (je 3/3), 0 Fehlalarme (R1, R2 je 3× ok), keine unklaren Urteile.

**Score 7,1** (vorher 4,9; Ziel 6,5):

| Gruppe | Wert | Teilscore (D0) |
|---|---|---|
| Zeit Teile | 186 s (durchlicht 156, kamera 210, zentrieraufnahme 192) | 3,55 (1,29) |
| Zeit Stehlager | 353 s | 4,68 (4,81) |
| Zeit Prüfstation | 536 s | 6,59 (4,97) |
| Präzision erster Lauf | 0 Fehlerpunkte | 10,0 (3,5) |
| Präzision Fallen | 6 | 10,0 (10,0) |
| Aufwand | 0,80 | 5,91 (5,0) |
| Robustheit | 11 304 MB | 4,11 (0,0) |

**Entscheidung: besser → übernommen** (Merge `btp-umbau-1` in den Optimierungs-Branch, e8ca7fb). Score +2,2 ≥ +0,3,
Präzision erster Lauf und Fallen nicht schlechter, keine Sperre. Ziel 6,5 erreicht → Abbruch nach Umbau 1 (§5.2).

**Wiederholung d1-stehlager-1 (§5.1):** Lauf 1 scheiterte an `volumen: auto` von Unterteil und Deckel: Der Agent legte
die Lagerbohrung als Vollkreis-Schnitt an, der zur Hälfte über das Material hinausragt; `volumen_auto` zieht den
ganzen Kreis ab (die Annahme „Schnitte liegen ganz im Material“ steht nur im Code, nicht im Skill). Danach neue
Freigabe → 2 Prüfmängel + 1 Freigabe = 3 Fehlerpunkte. Umbau 1 berührt weder `volumen_auto` noch die Volumen-Hinweise
des Skills; der Agent in D0 hatte die Bohrung direkt in die Kontur gelegt (andere Modellierwahl). Zusätzlich hing ein
`python -` ohne Heredoc 2 min auf stdin. → nachweislich unabhängig, genau dieser Lauf einmal wiederholt; der
Wiederholungslauf zählt. **Empfindlichkeit:** Hätte Lauf 1 gezählt, läge der Score bei ~5,6 (Präzision erster Lauf
3,5, Stehlager 2,98) – Umbau 1 wäre trotzdem „besser“ (≥ 4,9 + 0,3, Präzision nicht schlechter), das Ziel 6,5 aber
nicht erreicht. Der Hebel dagegen ist klein (offene Hebel, Punkt 1).

**Wo die Zeit jetzt hängt:**
- Teile: Modell 92–132 s (davon die eine Runde „Spec schreiben“ ~60–80 s), Prüfer 22–55 s (liest jetzt alles in einer
  Runde, denkt dafür länger – Streuung), Werkzeug nur noch 16 s. Review entfällt bei Ersatzkörpern, sonst 19 s (Sonnet).
- Stehlager: Modell 244 s, davon ~120 s Quelltextsuche des Agenten (`je_position`-Instanzen, `volumen_auto`).
- Prüfstation: Durchlauf 245 s (Bauen + Prüfen + 2 Neustarts), Modell 182 s, Prüfer 84 s, kein Review (Maß- und
  Schraubenlängenänderung).

### Eigene Entscheidungen in Umbau 1 (sonst hätte ich gefragt)

| Entscheidung | Begründung |
|---|---|
| Kein Review für Kaufteil-Ersatzkörper | Der Review prüft Fertigungs- und Montagegerechtheit; ein Ersatzkörper wird nie gefertigt (Hüllgeometrie eines Kaufteils). Bogen §8 erlaubt einen kleineren Geltungsbereich, nicht das Abschaffen – neue Teile und Formänderungen behalten ihn |
| Kein Review bei reinen Parameter-, Schraubenlängen- und Normteiländerungen | Beispiel des Bogens §8 wörtlich |
| Review mit Sonnet und effort medium als Aufrufparameter im Skill (zusätzlich Frontmatter) | Agentendefinitionen lädt Claude Code beim Sitzungsstart; der Aufrufparameter gewinnt laut Doku und wirkt deshalb auch im Messlauf; Frontmatter-Felder `model`/`effort` laut code.claude.com gültig |
| Fallen nach Umbau 1 neu gebaut | `swki pruefen` und `pruefer_auftrag` haben sich geändert (Goal-Auftrag Schritt 3), obwohl die Prüfberichte gleich bleiben |
| Fallen-Prüfer schreiben ihr Urteil selbst nach `urteil-*.json` (Write nur für diese Datei) | Wie in D0 („meist selbst“); spart 24 Abschriften; Prompt sonst unverändert aus `auftrag-*.md` |
| Fallen-Prüfer erst nach den sechs Messläufen gestartet | 20 parallele Agenten hätten die gemessene Modellzeit verfälschen können |
| Entwicklungsaufträge `MESS-devalt-pruefstation`/`MESS-devneu-pruefstation` ohne Rückfrage gebaut | Messstand-Aufträge (`MESS-*`), Vorlage mit gültiger Freigabe |
| Unsichtbares Öffnen nur für Norm-/Kaufteile beim Bauen und alle Teile beim Prüfen, Eigenteile beim Bauen sichtbar | Eigenteile unsichtbar anzulegen hatte der Messstand (Umbau 2, 09.10.) verworfen (globale Variablen); Norm-/Kaufteile tragen zwei Drittel der Spitze |

## Schlusszusammenfassung (24.10.2026)

- **Bestätigung (Durchgang 2, unten):** D2 = 6,1, Mittel D1/D2 = 6,5 – das Ziel hält nur im Mittel und nur knapp.
- **Endstand: Score 7,1** nach einem Umbau (Ausgang 4,9, Ziel 6,5). Alle Läufe geometrisch richtig, alle Fallen
  erkannt, kein Fehlalarm. Stand auf dem Optimierungs-Branch `claude/eager-mirzakhani-66b569` (Merge e8ca7fb), nicht
  gepusht, nicht nach `main` gemergt; `btp` selbst ist unverändert (in eigenem Worktree ausgecheckt).
- **Übernommen:** Umbau 1 (oben). Wirkung: Prüfstation 995 → 536 s, Teile 258 → 186 s, Speicherspitze 28,2 → 11,3 GB,
  Fehlerpunkte 3 → 0 (zwei echte Ursachen behoben: Symmetrie-Toleranz im Compiler, Messanker-Normale im Skill).
- **Verworfen:** nichts gemessen verworfen. Bewusst nicht angefasst: Prüfer-Modell/effort (O11; Fallen-Risiko F1–F3),
  DISPID-Cache (O6), Teile wiederverwenden (O5; die Teilephase der Prüfstation ist seit dem Bemaßungsbezug nur noch
  ~100 s), Fast Mode/effort des Hauptagenten (gestrichen).
- **Offene Hebel** (nach Wirkung):
  1. ~~`volumen: auto` gegen Schnitte, die über das bisherige Material hinausragen~~ – **nachgezogen** (Nutzerauftrag
     nach dem Goal, nicht gemessen): `volumen_auto` meldet einen Schnitt, dessen Box über die Box der vorher gebauten
     Aufsätze hinausragt, als nicht berechenbar; `validieren` lehnt `volumen: auto` genau dann ab (Befund
     `pruefung.volumen`), wenn das sonst rechenbar wäre – andere Gründe bleiben wie bisher ein Hinweis, damit die
     Prüfstation-Vorlage (`fallschacht`, `schieber`: Schnitte ragen absichtlich ins Leere, `auto` dort ohnehin nicht
     berechenbar) gültig bleibt. Skill `konstruieren` nennt die Grenze. Gegenprobe über 246 vorhandene Teil-Specs:
     nur das Stehlager-Referenzteil (ohne Volumenprüfung) bekommt statt des falschen `auto`-Werts „nicht berechenbar“.
  2. Skill `baugruppe`: Instanzen (`je_position`, `stift.1`) und Grenzen von `volumen: auto` knapp erklären – der
     Stehlager-Agent suchte ~120 s im Quelltext.
  3. Prüfer: 22–84 s; Kurzbericht statt vollem Prüfbericht (O10 zweiter Teil), Frontmatter `omitClaudeMd`.
  4. Teile wiederverwenden (O5) für Nachbesserungsläufe großer Baugruppen.
  5. Prüfen: 23 Eigenteile werden einzeln geöffnet und gemessen – im Baugruppenkontext messen spart weitere Sekunden.
- **Vorbestehend, nicht behoben:** Live-Tests `test_manuelle_aenderung_an_der_baugruppe` und
  `test_manuelle_aenderung_in_der_baugruppe` erwarten globale Variablen (seit dem Bemaßungsbezug ohne
  `gleichungen: true` nicht mehr vorhanden).
- **Befunde der Fallen-Prüfer an der AP-6.8-Vorlage** (Stand Lauf 28, nicht geändert; F6-Prüfer 3/3 ähnlich):
  Zylinderhalter-Schrauben M5 × 16 greifen 8,0 statt ≥ 10 in die Alu-Anschlussplatte; Durchlicht-Schrauben M4 × 12 nur
  7,4 (≥ 8); Bandpass `LV = 51,1` statt 51,0 (0,1 Luft vor der Objektivfront); Übergang Trichter → Fallschacht mit
  0,3 Stoßkante. Bitte prüfen – mögliche echte Mängel des Auftrags AP 6.8, nicht des Messverfahrens.

## Durchgang 2 – Bestätigung (24.10.2026, Commit 14b811b = Umbau 1, ohne neuen Umbau)

Auftrag des Nutzers: Streuung des Stands Umbau 1 sehen. Gemessen auf 14b811b (nicht 750668c mit der späteren
`volumen: auto`-Prüfung), alle Prompts zeichengleich zu D1 bis auf den Laufnamen. **Keine Wiederholung nach §5.1** –
jeder Lauf zählt, wie er ist. Fallen nicht neu gebaut (seit dem Neubau nach Umbau 1 unverändert; zwischen 14b811b und
dem Stand der Fallen-Aufträge sind `pruefer.md` und `pruefer_auftrag` gleich, die Prompts sind bis auf den
Durchgangsordner identisch zu D1).

| Lauf | Zeit s | Modell | Review | Prüfer | Werkzeug (durchlauf) | Tool-Aufrufe | Tokens gew. | Läufe | Fehlerpunkte | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d2-durchlicht-1 | 145 | 102 | – | 22 | 17 | 18 | 286219 | 1 | 0 | 3309 | ja |
| d2-durchlicht-2 | 145 | 98 | – | 23 | 18 | 19 | 239909 | 1 | 0 | 3316 | ja |
| d2-kamera-1 | 324 | 180 | – | 96 | 29 | 37 | 483480 | 2 | 2 | 3486 | ja |
| d2-zentrieraufnahme-1 | 173 | 112 | 10 | 26 | 17 | 24 | 275339 | 1 | 0 | 3367 | ja |
| d2-stehlager-1 | 324 | 218 | 32 | 26 | 37 | 37 | 487362 | 1 | 0 | 4392 | ja |
| d2-pruefstation-1 | 565 | 164 | – | 29 | 234 | 33 | 598038 | 1 | 0 | 10788 | ja |

Fallen: 6 von 6, 0 Fehlalarme. F6-3 war „unklar“ (fand Bandpass-Spalt und Trichter-Stoßkante, nicht die
Einschraublänge der Falle) → in `entscheid.json` als „verfehlt“ gewertet; F6 bleibt mit 2/3 Treffer.

**Fehlerursachen je Lauf:**
- d2-kamera-1 (2 Fehlerpunkte): Der Agent übersah in Rückansicht A das Maß 20,3 und setzte den M8-Stecker mittig; der
  Prüfer fand es (1 Prüfermangel), Korrektur mit neuem Parameter → zweite Freigabe. Reine Zeichnungsdeutung, kein Bezug
  zum Umbau (die M2-Höhen hat der Agent diesmal selbst auf 20,25 vereinheitlicht und kommentiert; `richtig` = ja).
- Alle übrigen Läufe: 0 Fehlerpunkte.
- Zeitverluste ohne Fehlerpunkt: d2-pruefstation-1 121 s in einem Python-Heredoc mit `||`-Rückfall
  (`python - <<'EOF' … || python - <<'EOF'`), der bis zum 2-min-Zeitlimit des Bash-Tools auf stdin wartete – dasselbe
  Muster kostete in d1-stehlager-1 rund 2 min. d2-kamera-1: Nachbesserungsrunde (Prüfer 96 s für zwei Urteile).

**Score D2 = 6,1** (`btp 2 --vergleich 1`):

| Gruppe | D1 | D2 | Mittel D1/D2 (Wert → Teilscore) |
|---|---|---|---|
| Zeit Teile | 186 s → 3,55 | 214 s → 2,68 | 200 s → 3,11 |
| Zeit Stehlager | 353 s → 4,68 | 324 s → 5,06 | 338 s → 4,87 |
| Zeit Prüfstation | 536 s → 6,59 | 565 s → 6,49 | 551 s → 6,54 |
| Präzision erster Lauf | 0 → 10,0 | 2 → 5,25 | 1 → 7,0 |
| Präzision Fallen | 6 → 10,0 | 6 → 10,0 | 6 → 10,0 |
| Aufwand | 0,80 → 5,91 | 0,90 → 5,69 | 0,85 → 5,75 |
| Robustheit | 11 304 MB → 4,11 | 10 788 MB → 4,56 | 11 046 MB → 4,33 |
| **Score** | **7,1** | **6,1** | **6,49** |

Mittel = je Aufgabe Mittel der Zeiten (Teile aus den gemittelten Aufgabenzeiten), Fehlerpunkte, Fallen, Aufwand und
Speicher je Durchgang gemittelt, dann die Anker. Ohne die §5.1-Wiederholung in D1 (also Stehlager-Lauf 1 mit 555 s und
3 Fehlerpunkten) wäre D1 = 5,6 und das Mittel 5,8.

**Einschätzung – hält der Stand die 6,5 robust? Nein, nur knapp im Mittel.**
- **Robust ist die Zeit- und Speicherseite:** Prüfstation 536/565 s (D0 995), Durchlicht 156/145 s, Zentrieraufnahme
  192/173 s, Stehlager 353/324 s, Speicher 11,3/10,8 GB (D0 28,2), Fallen beide Male 6/6 ohne Fehlalarm. Diese Gruppen
  tragen zusammen ~4,3 Punkte und schwanken zwischen den Durchgängen um weniger als 0,15.
- **Nicht robust ist „Präzision erster Lauf“:** 20 % Gewicht, und jeder Fehlerpunkt kostet bei 0–2 Punkten 0,7, darüber
  0,35. D1 hatte (nach Wiederholung) 0, D2 hat 2 – beide Male aus der Deutung der Eingabe durch den Agenten (D1
  Stehlager: Modellierwahl gegen eine Grenze von `volumen: auto`; D2 Kamera: übersehenes Maß), nicht aus dem
  Werkzeug. Allein diese Gruppe verschiebt den Score zwischen 6,1 und 7,1.
- **Kamera als Zeitausreißer:** Ein Nachbesserungslauf verdoppelt die Kamerazeit (210 → 324 s) und drückt „Zeit Teile“
  um ~0,9 Teilscore.
- Erwartungswert des Stands bei 0–2 Fehlerpunkten je Durchgang: ~6,1–7,1, Mittel ~6,5. Für einen sicheren Abstand zur
  6,5 fehlen Hebel auf der Präzisionsseite: die nachgezogene `volumen: auto`-Prüfung (750668c, hätte den D1-Fehler vor
  der Freigabe abgefangen; in D2 nicht gemessen), eine Maßliste je Ansicht vor dem Schreiben der Spec (D2-Kamera) und
  der Hinweis gegen Heredoc-Rückfälle (Zeit, kein Score-Risiko).

## Umbau 2 – Durchgang 3 und 4 (24.10.2026, Branch `btp-umbau-2`, Commit 17e4111)

**Bogenregel (Schritt 0, Nutzer-Auftrag 24.10.):** Ab Umbau 2 entscheidet das **Mittel aus zwei Durchgängen** (Bogen
§5.1, neuer Absatz); Wiederholungen nach §5.1 entfallen – jeder Lauf zählt, wie er ist. Neuer Befehl
`-m werkzeuge.messstand btp-mittel <n> <m> --vergleich <k> <l>` (`btp.mittel`, Unit-Tests ohne SolidWorks; Commit
295cff5). Er rechnet D1/D2 wie von Hand in D2 auf **6,49** nach.

Umbau 2 (gebündelt, nur Skills und `CLAUDE.md`, kein Code; Commit 17e4111):

| Teil | Inhalt | Anlass |
|---|---|---|
| Heredoc-Hänger | Skills `konstruieren`/`baugruppe` und `CLAUDE.md`: längere Python-Schnipsel als Datei (Write-Tool) und `.venv\Scripts\python.exe <datei>`; nie `python - <<'EOF' … \|\| python - <<'EOF'`, `python -` oder `cat` ohne Eingabe | d1-stehlager-1, d2-pruefstation-1: je ~2 min auf stdin |
| Maßliste | Skill `konstruieren` §2: Pflichtschritt bei Zeichnung/Maßbild – jedes Maß jeder Ansicht mit Bezugskante als Kommentarblock am Kopf der Spec, jedes Maß muss in Parameter, Ausdruck oder Kommentar wieder auftauchen; ungleiche Maße eines Merkmals nicht still angleichen; §5: Steckbrief Zeile für Zeile gegen die Liste, bevor der Prüfer startet | D0 Kamera (M2-Höhen angeglichen), D2 Kamera (Maß 20,3 übersehen) |
| Skill `baugruppe` | Instanzen (`je_position`, Reihenfolge, `instanz: je`, Normteil auf Normteil mit gleichem `je_position`, `stift.1` nur in `pruefung`) und Grenzen von `volumen: auto` (Lagerbohrung in der Teilfuge) | d1-stehlager-1: ~120 s Quelltextsuche |
| 750668c (schon auf dem Branch) | `validieren` lehnt `volumen: auto` bei Schnitten über das bisherige Material ab | D1-Fehler Stehlager |

Abnahme: Unit-Tests 1434 grün; Live-Regression `tests/referenz` 11/11 OK, dazu `tests/live/test_live_baugruppe.py`
6/7 (nur der vorbestehende `test_manuelle_aenderung_an_der_baugruppe`); Log `MESSSTAND/regression-btp-u2.log`.
Fallen nicht neu gebaut (der Umbau berührt weder `swki pruefen` noch `pruefer.md`/`pruefer_auftrag`; die
Fallen-Aufträge D3/D4 sind bis auf den Durchgangsordner zeichengleich zu D2), aber je Durchgang 8 × 3 neu geprüft.

| Lauf | Zeit s | Modell | Review | Prüfer | Werkzeug (durchlauf) | Tool-Aufrufe | Tokens gew. | Läufe | Fehlerpunkte | Speicher MB | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d3-durchlicht-1 | 175 | 123 | – | 28 | 19 | 20 | 319975 | 1 | 0 | 3361 | ja |
| d3-durchlicht-2 | 213 | 114 | – | 76 | 16 | 21 | 312856 | 1 | 0 | 3372 | ja |
| d3-kamera-1 | 220 | 142 | – | 57 | 16 | 19 | 309186 | 1 | 0 | 3373 | ja |
| d3-zentrieraufnahme-1 | 166 | 94 | 27 | 22 | 16 | 24 | 296036 | 1 | 0 | 3404 | ja |
| d3-stehlager-1 | 336 | 234 | 40 | 18 | 35 | 38 | 503164 | 1 | 0 | 4589 | ja |
| d3-pruefstation-1 | 454 | 124 | – | 71 | 237 | 33 | 681144 | 1 | 0 | 10587 | ja |
| d4-durchlicht-1 | 198 | 127 | – | 49 | 17 | 19 | 290693 | 1 | 0 | 3329 | ja |
| d4-durchlicht-2 | 180 | 111 | – | 48 | 17 | 19 | 267743 | 1 | 0 | 3360 | ja |
| d4-kamera-1 | 205 | 145 | – | 36 | 17 | 21 | 319631 | 1 | 0 | 3350 | ja |
| d4-zentrieraufnahme-1 | 148 | 85 | 22 | 19 | 17 | 24 | 258039 | 1 | 0 | 3358 | ja |
| d4-stehlager-1 | 343 | 225 | 44 | 21 | 37 | 39 | 527641 | 1 | 0 | 6362 | ja |
| d4-pruefstation-1 | 635 | 125 | – | 118 | 256 | 43 | 699087 | 1 | 0 | 11222 | ja |

Fallen: D3 und D4 je 6 von 6 (alle 36 Fallen-Urteile Treffer), R1/R2 je 3× ok, keine unklaren Urteile.

**Score** (`btp 3 --vergleich 1`, `btp 4 --vergleich 2`, `btp-mittel 3 4 --vergleich 1 2`):

| Gruppe | D3 | D4 | **Mittel D3/D4** (Wert → Teilscore) | Mittel D1/D2 |
|---|---|---|---|---|
| Zeit Teile | 193 s → 3,31 | 181 s → 3,71 | 187 s → 3,51 | 200 s → 3,11 |
| Zeit Stehlager | 336 s → 4,90 | 343 s → 4,80 | 340 s → 4,85 | 338 s → 4,87 |
| Zeit Prüfstation | 454 s → 6,88 | 635 s → 6,24 | 544 s → 6,56 | 551 s → 6,54 |
| Präzision erster Lauf | 0 → 10,0 | 0 → 10,0 | 0 → 10,0 | 1 → 7,0 |
| Präzision Fallen | 6 → 10,0 | 6 → 10,0 | 6 → 10,0 | 6 → 10,0 |
| Aufwand | 0,8 → 5,80 | 0,8 → 5,93 | 0,8 → 5,86 | 0,8 → 5,80 |
| Robustheit | 10 587 MB → 4,74 | 11 222 MB → 4,18 | 10 904 MB → 4,46 | 11 046 MB → 4,33 |
| **Score** | **7,2** | **7,1** | **7,17** | **6,49** |

**Entscheidung: besser → übernommen** (Merge `btp-umbau-2` in `claude/btp-umbau-2-a44754`, 1756243). Mittel 7,17 ≥
6,49 + 0,3, Präzision erster Lauf (10,0 gegen 7,0) und Fallen (10,0 gegen 10,0) nicht schlechter, keine Sperre, alle
12 Läufe `richtig`. Einzeln: `btp 4 --vergleich 2` besser; `btp 3 --vergleich 1` 7,2 gegen 7,1 (nicht +0,3 gegen den
günstigen D1 mit Wiederholung) – genau dafür entscheidet seit Schritt 0 das Mittel.

**Woher der Gewinn kommt (+0,68):**
- **Präzision erster Lauf** (+0,6 gewichtet): 12 von 12 Läufen ohne Fehlerpunkt, ohne Wiederholung. Kamera beide Male im
  ersten Lauf richtig: M2-Höhen 20,25/20,22 getrennt geführt, Stecker samt 20,3 richtig (die Maßliste steht als
  Kommentarblock in den Specs); Stehlager beide Male ohne `volumen: auto`-Falle. Vorbehalt: zwei Durchgänge je Stand
  sind eine kleine Stichprobe; auch D1 hatte nach der Wiederholung 0 Fehlerpunkte.
- **Zeit Teile** (+0,06): Kamera 267 → 212 s (keine Nachbesserungsrunde mehr), Zentrieraufnahme 183 → 157 s;
  dagegen Durchlicht 151 → 192 s (Maßliste kostet ~10–25 s Modellzeit, dazu Prüfer-Streuung 28–76 s).
- Stehlager unverändert (340 s): die Quelltextsuche ist weg (nur noch `grep` in den Normteiltabellen), die Modellzeit
  bleibt aber bei ~230 s – Nachdenken über drei Teil-Specs, nicht Suche.
- Prüfstation im Mittel unverändert: D3 454 s (bester bisheriger Wert), D4 635 s, davon 127 s ein stdin-Hänger
  (leerer Python-Heredoc mit `|| true`), den der neue Hinweis **nicht** verhindert hat; Prüfer 71/118 s.

### Eigene Entscheidungen in Umbau 2 (sonst hätte ich gefragt)

| Entscheidung | Begründung |
|---|---|
| Mittelwert-Befehl als `btp-mittel` neben `btp`, Score mit zwei Nachkommastellen | `btp` bleibt für Einzeldurchgänge unverändert; 6,49 statt 6,5 zählt bei der +0,3-Schwelle |
| Nicht richtig im Mittel = in einem der Durchgänge nicht richtig (Deckel 4,0) | Strengste Lesart der Sperre; trat nicht auf |
| Bogenregel und `btp-mittel` direkt auf dem Optimierungs-Branch, Umbau 2 auf `btp-umbau-2` | Die Messregel gilt unabhängig vom Ausgang des Umbaus |
| Maßliste nur Pflicht bei Zeichnung/Maßbild, nicht bei Beschreibungen | Die Fehler kamen aus Zeichnungen; Modellzeit der übrigen Aufgaben schonen |
| Maßliste als Kommentarblock in der Spec, nicht nur „im Kopf“ | Prüfbar für Prüfer und Nutzer; die Freigabe-Kopie behält sie |
| Live-Regression: `tests/referenz` und `test_live_baugruppe.py` | Umbau ändert keinen Code; 750668c berührt nur `validieren` (Unit-getestet) |
| Fallen nicht neu gebaut | Goal-Auftrag Schritt 3: nur bei Änderung von `swki pruefen`/Prüferweg |
| Fallen-Prüfer wie D1/D2 (`general-purpose`, Standardmodell, Prompt wortgleich, Urteil selbst schreiben), erst nach den sechs Läufen je Durchgang; höchstens 20 gleichzeitig (Limit der Sitzung), Rest nachgestartet | Vergleichbarkeit mit D1/D2; parallele Prüfer könnten die gemessene Modellzeit verfälschen |
| Urteil F6-3 (D4) aus der Rückmeldung unverändert abgelegt; Fehlablagen unter `arbeit/MESSFALLE-F6/durchgang-3` und `-4` gelöscht | Zwei F6-Prüfer schrieben zuerst unter einen falschen Pfad, einer nur dorthin (Lehre im Goal-Auftrag) |
| d4-pruefstation-1 ohne `--haenger` | Kein SolidWorks-Absturz oder Werkzeug-Zeitlimit von swki, sondern ein Shell-Aufruf des Agenten; kostet nur Zeit (wie D1/D2 gewertet) |

**Offene Hebel nach Umbau 2:**
1. ~~**stdin-Hänger technisch verhindern**~~ – **nachgezogen** (Nutzerauftrag nach Umbau 2, nicht gemessen):
   PreToolUse-Hook `werkzeuge/stdin_sperre.py` in `.claude/settings.json` lehnt Bash-Befehle ab, die ein Python-Skript
   über stdin lesen (`python -`, auch mit Heredoc/Pipe/`<`) oder ohne Eingabe warten (`python` ohne Skript, `cat` ohne
   Datei/Heredoc/Pipe), und nennt den Weg über eine Datei. Gegenprobe über alle 230 Bash-Aufrufe der Messläufe D0–D4:
   8 abgelehnt, darunter alle drei Hänger (je ~121 s) und ein 601-s-Aufruf; die übrigen vier liefen damals durch und
   kosten künftig einen zweiten Anlauf; kein anderer Befehl betroffen. Wirkt erst in neu gestarteten Sitzungen (Hooks
   werden beim Sitzungsstart geladen) – auch für Messläufe, die als Subagenten laufen.
2. Prüfer-Streuung (18–118 s): Kurzbericht statt vollem Prüfbericht (O10), `omitClaudeMd`.
3. Durchlicht-Modellzeit: die Maßliste lohnt bei Kamera mehr, als sie bei Durchlicht kostet; eine knappere Form (nur
   Lagemaße) wäre zu prüfen, ohne die Präzision zu riskieren.
4. Stehlager-Modellzeit ~230 s (drei neue Teil-Specs): Muster-Specs bzw. Teile-Vorlagen wären der nächste Hebel.
5. Wie bisher: Teile wiederverwenden (O5), Prüfen im Baugruppenkontext.

## Umbau 3 – Durchgang 5 und 6 (25.10.2026, Branch `btp-umbau-3`, Commit 6cfae5b)

Umbau 3 (gebündelt, Branch `btp-umbau-3` ab `main` ff95658 mit Umbau 1 und 2):

| Teil | Inhalt | Commits |
|---|---|---|
| 1 – Teile wiederverwenden (Recherche O5) | `swki/baugruppe/wiederverwendung.py`: Schlüssel je Eigenteil = SHA-256 über Teil-Spec (ganz, samt Dateiname), Skriptdateien, Import-Hülle von `swki.compiler.bauen` (AST, mit Importen in Funktionen außer in der Befehlsschicht `cli`/`aenderungen`/`compiler.bauen`; ohne `swki/baugruppe`), `swki/wissen/*.yaml`, `schema/teil.schema.json`, `config/standard.yaml` ohne Schalter und Prüfgrenzen, Auftrag, `sw_jahr`/`RevisionNumber`, Teilvorlage, Materialdatenbanken (nur bei `material`). Quelle nur ein Lauf desselben Auftrags mit Teilstatus ok, gleichem Schlüssel und Datei-SHA-256 = Protokoll; Teilmangel im Prüfbericht sperrt Schlüssel und Datei, ein Prüfer-Mangel am Teil die Datei. Bauen: zuletzt gescheiterte, dann neue/geänderte Teile zuerst, dann übernehmen (Kopie mit der Schreibweise der Quelle, SHA-Prüfung, unsichtbar öffnen, Kontext wie `swki pruefen` aus Datei und Quellprotokoll; Rückfall Neubau). Ausgabe `teile_gebaut`/`teile_wiederverwendet` (bauen, durchlauf, Messstand), `--alles-neu`, Schalter `wiederverwenden: true` | b9fba95, d39a670, 6cfae5b |
| 2 – Teil-Specs parallel (Skill `baugruppe` §1) | Bei ≥ 2 neuen Eigenteilen: `schnittstellen.md` (Teile, Hauptmaße, Bezugsflächen, Bohrbilder, Feature-IDs, Normteile), je Teil ein Subagent (`claude`, ohne `model` = Modell der Sitzung) in einer Antwort, dann die Baugruppen-Spec; Änderungsaufgaben unverändert | d39a670 |

**Abnahme vor der Messung:**
- Unit-Tests 1505 grün (neu: 27 für `wiederverwendung`, 7 für den Teilbau, 2 Durchlauf, 1 Messstand), `swki api
  pruefe-code` ohne Befund.
- Live-Nachweis `tests/live/test_live_wiederverwendung.py` (neu, je Referenz-Baugruppe frisches SolidWorks): Stehlager,
  Schlitten, Zahnstangentrieb, Motorhalter je OK – Durchlauf 1 baut alle Eigenteile, Durchlauf 2 übernimmt alle und
  der Prüfbericht ist Wert für Wert gleich (ohne Laufnummer, Pfade, Bilder und die Laufzeit `dauer_s` der
  Bewegungsläufe, Zahlen auf 1e-9); eine von Hand geänderte Datei löst `MANUELL_GEAENDERT` aus und `--verwerfen` holt
  das Teil aus dem unveränderten Lauf 1; nach einer Parameteränderung wird genau dieses Teil neu gebaut. Der erste
  Lauf fand einen echten Unterschied: kopierte Teile hießen `.sldprt` statt `.SLDPRT` (Stücklisten-Schlüssel) → die
  Kopie behält die Schreibweise der Quelle (d39a670).
- Prüfstation (Vorlage Lauf 28, `MESS-devu3-pruefstation`): Bauen 154 → 35 s (Teilephase 112,7 → 3,4 s), 23/23
  übernommen, Prüfbericht Wert für Wert gleich; nach der BTP-Änderung (Referenz-Specs) nur `kamerahalter.yaml` neu, 22
  übernommen, Bauen 45 s, bestanden. Log `MESSSTAND/dev-u3-pruefstation.log`.
- Live-Regression `tests/referenz` 11/11 OK, `tests/live/test_live_baugruppe.py` 6/7 (nur der vorbestehende
  `test_manuelle_aenderung_an_der_baugruppe`); Log `MESSSTAND/regression-btp-u3.log`.
- Fallen nicht neu gebaut: Umbau 3 ändert weder `swki pruefen` noch `pruefer.md`/`pruefer_auftrag`; die
  Fallen-Aufträge D5/D6 sind bis auf den Durchgangsordner zeichengleich zu D4 (mit `diff` geprüft). Je Durchgang 8 × 3
  neu geprüft.

| Lauf | Zeit s | Modell | Subagenten (Review, Teil-Specs) | Prüfer | Werkzeug (durchlauf) | Tool-Aufrufe | Tokens gew. | Läufe | Fehlerpunkte | Speicher MB | übernommen/gebaut | richtig |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| d5-durchlicht-1 | 169 | 117 | – | 29 | 19 | 20 | 312990 | 1 | 0 | 3322 | – | ja |
| d5-durchlicht-2 | 150 | 107 | – | 24 | 16 | 18 | 298620 | 1 | 0 | 3374 | – | ja |
| d5-kamera-1 | 197 | 155 | – | 20 | 16 | 23 | 317585 | 1 | 0 | 3375 | – | ja |
| d5-zentrieraufnahme-1 | 232 | 161 | 29 | 20 | 17 | 23 | 282716 | 1 | 0 | 3371 | – | ja |
| d5-stehlager-1 | 413 | 228 | 213 | 17 | 38 | 54 | 974970 | 1 | 0 | 4489 | 0/3 | ja |
| d5-pruefstation-1 | 426 | 182 | – | 97 | 130 | 46 | 848504 | 1 | 0 | 5317 | **22/1** | ja |
| (d5-pruefstation-2, zählt nicht) | 385 | 127 | – | 110 | 135 | 37 | 685181 | 1 | 0 | 5180 | 22/1 | ja |
| d6-durchlicht-1 | 169 | 116 | – | 30 | 19 | 22 | 338645 | 1 | 0 | 3376 | – | ja |
| d6-durchlicht-2 | 135 | 96 | – | 20 | 16 | 18 | 236546 | 1 | 0 | 3371 | – | ja |
| d6-kamera-1 | 230 | 149 | – | 59 | 16 | 21 | 324403 | 1 | 0 | 3487 | – | ja |
| d6-zentrieraufnahme-1 | 181 | 96 | 32 | 32 | 16 | 24 | 295194 | 1 | 0 | 3364 | – | ja |
| d6-stehlager-1 | 361 | 190 | 209 | 17 | 36 | 53 | 962904 | 1 | 0 | 4594 | 0/3 | ja |
| d6-pruefstation-1 | 348 | 147 | – | 58 | 128 | 42 | 715768 | 1 | 0 | 5288 | **22/1** | ja |

Subagenten-Zeit überlappt beim Stehlager (drei Teil-Specs parallel); die Spalten summieren sich deshalb nicht zu
`zeit_s`. Fallen: D5 und D6 je 6 von 6 (alle 36 Fallen-Urteile Treffer), R1/R2 je 3× ok, keine unklaren Urteile.

**Score** (`btp 5 --vergleich 3`, `btp 6 --vergleich 4`, `btp-mittel 5 6 --vergleich 3 4`):

| Gruppe | D5 | D6 | **Mittel D5/D6** (Wert → Teilscore) | Mittel D3/D4 |
|---|---|---|---|---|
| Zeit Teile | 196 s → 3,24 | 188 s → 3,49 | 192 s → 3,36 | 187 s → 3,51 |
| Zeit Stehlager | 413 s → 3,86 | 361 s → 4,56 | 387 s → 4,21 | 340 s → 4,85 |
| Zeit Prüfstation | 426 s → 6,98 | 348 s → 8,20 | 387 s → 7,55 | 544 s → 6,56 |
| Präzision erster Lauf | 0 → 10,0 | 0 → 10,0 | 0 → 10,0 | 0 → 10,0 |
| Präzision Fallen | 6 → 10,0 | 6 → 10,0 | 6 → 10,0 | 6 → 10,0 |
| Aufwand | 1,1 → 4,74 | 1,0 → 4,87 | 1,0 → 4,80 | 0,8 → 5,86 |
| Robustheit | 5 317 MB → 9,68 | 5 288 MB → 9,71 | 5 302 MB → 9,70 | 10 904 MB → 4,46 |
| **Score** | **7,3** | **7,8** | **7,54** | **7,17** |

**Entscheidung nach §5.1: besser** – Mittel 7,54 ≥ 7,17 + 0,3, Präzision erster Lauf (10,0) und Fallen (10,0) nicht
schlechter, keine Sperre, alle 12 Läufe `richtig`, 0 Fehlerpunkte. Einzeln: `btp 6 --vergleich 4` besser (7,8 gegen
7,1), `btp 5 --vergleich 3` 7,3 gegen 7,2 (nicht +0,3). Kein `git push`, kein Merge – ein PR nach `main` erst nach
Rückfrage beim Nutzer (wie Umbau 2).

**Zeitgewinn je Aufgabe (Mittel D5/D6 gegen D3/D4):**
- **Prüfstation 544 → 387 s (−157 s)** – Teil 1: `durchlauf` 237/256 → 130/128 s; Teilephase des Messlaufs 13,0/12,3 s
  statt ~117 s, **22 von 23 Eigenteilen übernommen**, nur `kamerahalter.yaml` gebaut (beide Durchgänge, d5-
  pruefstation-2 ebenso; eine reine Kommentaränderung an `kamerasaeule.yaml` in d5-pruefstation-1 ließ den Schlüssel
  gleich). Der Prüfer bleibt mit 58–110 s der größte Streuer.
- **Robustheit 10,9 → 5,3 GB** – Nebenwirkung von Teil 1: übernommene Teile öffnen ohne Fenster (wie Norm- und
  Kaufteile), die Prüfstation-Spitze fällt von ~10,6 auf ~5,3 GB.
- **Stehlager 340 → 387 s (+47 s), Tokens ~500 k → ~970 k** – Teil 2 hilft nicht: Die Hauptsitzung brauchte vor den
  Subagenten 124–150 s (beide Skills lesen, Schnittstellen festlegen – praktisch die ganze Konstruktionsarbeit), die drei
  Teil-Subagenten liefen parallel 69–74 s (jeder liest Skill und Eingabe neu), danach Baugruppen-Spec und Review wie
  vorher. Gespart ist die frühere Schreibrunde (~60–80 s), dazu kommen Startkosten und das zweite Lesen. Folge:
  Aufwand-Teilscore 5,86 → 4,80 (fast nur Stehlager), Zeit Stehlager 4,85 → 4,21.
- Teile (Durchlicht 192 → 156 s, Kamera 212 → 214 s, Zentrieraufnahme 157 → 206 s) – vom Umbau nicht berührt (Skill
  `konstruieren` und Einzelteil-`bauen` unverändert); Streuung von Modell (96–161 s) und Prüfer (20–59 s).
- **Empfindlichkeit:** Ohne Teil 2 (Stehlager und Aufwand wie D3/D4) läge das Mittel geschätzt bei ~7,65; ohne Teil 1
  bliebe es unter 7,17. Der Gewinn kommt allein aus Teil 1.

### Eigene Entscheidungen in Umbau 3 (sonst hätte ich gefragt)

| Entscheidung | Begründung |
|---|---|
| Ganze Teil-Spec im Schlüssel (auch `pruefung`, nicht nur der vom Compiler gelesene Teil) | Vorsichtige Variante der Recherche; eine `pruefung`-Änderung braucht ohnehin eine neue Freigabe und kostet nur einen Teilbau |
| Code-Hülle: AST mit Importen in Funktionen, außer in `swki.cli`, `swki.aenderungen`, `swki.compiler.bauen` | Ohne Funktions-Importe fehlen die Handler (`registry.alle_handler`) und `skizze`; mit allen käme über `_bauen` ganz `swki` (Baugruppe, Prüfen) hinein, und jede Prüf-Änderung baute alle Teile neu |
| `config/standard.yaml` mit Sperrliste (`wiederverwenden`, `max_nachbesserungen`, `bewegung_schritte`, `speicher_grenze_mb`) statt Erlaubnisliste | Neue Schlüssel zählen automatisch mit (vorsichtig) |
| Prüfer-Mangel sperrt nur die Datei, Teilmangel im Prüfbericht Schlüssel und Datei | Wie Recherche O5 (sporadischer Fehlbau); ein Prüfer-Mangel ändert in der Regel die Spec und damit den Schlüssel |
| Übernommene Teile unsichtbar öffnen | Wie Norm- und Kaufteile; bis zum Schluss schließt nichts Sichtbares (Baugruppe zuerst, `schliesse` nimmt Mitgeschlossenes hin) – Ergebnis 5,3 statt 10,6 GB |
| `durchlauf` meldet `teile_gebaut` als Liste, `teile_wiederverwendet` als Anzahl | Bei 23 Teilen bleibt die Ausgabe für den Agenten kurz; `bauen` nennt beide als Liste |
| Schnittstellen in `schnittstellen.md` statt `plan.md` | Der Mess-Prompt verbietet „Pläne“ (gemeint ist der Plan-Skill); der Name vermeidet die Kollision |
| Arbeitsordner `MESS-d5-*` vom 09.10. nach `<arbeitsordner>/_messstand-2026-10-09-arbeit/` verschoben | `vorbereiten 5 …` hätte sie gelöscht (Panne aus D0); die Messdaten unter `MESSSTAND/messstand-2026-10-09` sind unberührt |
| d5-pruefstation-1 zählt trotz `lecks`-Befund, d5-pruefstation-2 nicht | Der Prüfer-Subagent läuft im Arbeitsverzeichnis der Goal-Sitzung und las per relativem Glob/Grep `schema/teil.schema.json`, `swki/compiler/skizze.py` bzw. den Skill `konstruieren` aus deren Worktree – dateigleich mit dem Lauf-Commit 6cfae5b, keine Referenz-Specs. Erst nach Bogen wiederholt (d5-pruefstation-2); der Wiederholer griff genauso zu → diese Zugriffsart als kein Leck entschieden (`lecks_entscheid` in `kpi.json`), der reguläre Lauf zählt, d6-pruefstation-1 ebenso. Mit dem Wiederholer statt des Originals läge D5 bei ~7,4 und das Mittel bei ~7,6 |
| Fallen-Prüfer wie D3/D4 (Verweis-Prompt auf `auftrag-*.md`, Urteil selbst schreiben), 20 + 4 gestartet; je Durchgang zwei F6-Urteile vom falschen Pfad `MESSFALLE-F6/durchgang-<n>` an den richtigen verschoben, Fehlablage gelöscht | Vergleichbarkeit; dieselbe Fehlablage wie in D3/D4 |

**Offene Hebel nach Umbau 3:**
1. **Teil 2 zurücknehmen** (Skill `baugruppe` §1, „Zwei oder mehr neue Eigenteile“): in beiden Durchgängen langsamer
   und doppelte Tokens. Wenn überhaupt, dann nur die Schnittstellenliste ohne Subagenten oder Subagenten mit fertigem
   Teil-Skelett statt Skill-Lektüre.
2. Prüfer (20–110 s, größter Streuer bei Prüfstation und Kamera): Kurzbericht statt vollem Prüfbericht (O10).
3. Prüfer-Subagenten lesen über relative Pfade aus dem Arbeitsverzeichnis der aufrufenden Sitzung (Leck-Befunde D5/D6):
   im Messstand die Leck-Prüfung auf Referenz-Pfade beschränken oder den Prüfer-Prompt auf absolute Pfade festlegen.
4. Verknüpfen (~23 s) und Prüfen (~70 s) sind jetzt der Werkzeug-Rest des Prüfstation-`durchlauf` (130 s).
