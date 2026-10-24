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
