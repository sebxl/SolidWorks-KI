# Bewertungsbogen „Tempo und Präzision“ (BTP) – Messung für die Optimierungsschleife

Stand 23.10.2026. Grundlage: [Laufzeit-Audit](../../laufzeit-audit/2026-10-23-audit.md). Erweitert den
[Messstand](2026-10-09-messstand-design.md) (Werkzeug `werkzeuge/messstand`, Läufe, Isolation, Richtigkeit gegen
Referenz bleiben). Der Bogen ist das Maß für eine `/goal`-Session, die in **höchstens 5 Umbauten** optimiert.

## 1. Ziel und Warum

Das Tool braucht zum Konstruieren und Prüfen zu lange (Nutzer, 23.10.2026). Hauptziele: **Geschwindigkeit und
Präzision**. Präzision heißt: geometrisch richtig und im ersten Lauf bestanden (Nutzer). Der Bogen muss deshalb
(a) die echte Wartezeit großer Baugruppen abbilden – dort liegen laut Audit 14 min Werkzeugzeit je Zyklus –, (b) die
kleinen Aufgaben weiter messen und (c) verhindern, dass Tempo mit Präzision bezahlt wird.

Anti-Ziele: ein Score, der steigt, weil Prüfungen wegfallen; ein Score, der an einem einzigen Zufallsfehler kippt;
Änderungen, die die Konstruktionsregeln aus CLAUDE.md und den Skills aufweichen.

## 2. Aufgabensatz je Durchgang

| ID | Art | Aufgabe | Eingabe | Referenz |
|---|---|---|---|---|
| `durchlicht` (2×) | Teil aus Maßbild | wie Messstand | Maßbild + Aufgabentext | Messstand-Referenz |
| `kamera` | Teil aus Maßbild (Falle Steckerseite) | wie Messstand | Maßbild + Aufgabentext | Messstand-Referenz |
| `zentrieraufnahme` | Teil aus Beschreibung, Formschrägen | wie Messstand | `beschreibung.md` | `tests/referenz/zentrieraufnahme` |
| `stehlager` | kleine Baugruppe, neu | wie Messstand | `beschreibung.md` | `tests/referenz/stehlager` |
| `pruefstation` | **Änderung an großer Baugruppe** (neu) | siehe §2.1 | Auftrag AP 6.8 Stand Lauf 28 + Änderungstext | eigens gebaute Referenz `MESSREF-pruefstation` |

Die fünf Messstand-Aufgaben bleiben unverändert (vergleichbar mit Durchgang 0–5 vom 09.10.).

### 2.1 Aufgabe `pruefstation`

- Ausgang: Kopie von `auftraege/AP68-Pruefstation` (alle Specs, freigegebene Kopien, `freigabe.json`, `eingabe/`,
  `skripte/`) als Auftrag `MESS-<n>-pruefstation-1` im Lauf-Worktree, **inklusive gebautem und geprüftem Lauf** – so
  wie im echten Betrieb vor einer Nachbesserung. Den Ausgangslauf baut und prüft `vorbereiten` **mit dem gemessenen
  Stand** neu (sonst kann eine Wiederverwendung unveränderter Teile nie greifen); diese ~13 min liegen außerhalb von
  `zeit_s`. Die mitkopierten Protokolle von Lauf 11–28 kommen nicht mit; es zählen nur Läufe nach dem Ausgangslauf.
- Änderungstext (fest, in `werkzeuge/messstand` als Aufgabe abgelegt): **ein Anforderungsmaß in einem Teil** (Parameter,
  neue Freigabe nötig) **und eine Bauweg-Änderung an einer Verschraubung** (Schraubenlänge). Die genaue Änderung legt
  die Einrichtung fest (§6, Schritt 1) und wählt sie so, dass sie zwei Teile, eine Normteilgröße und mindestens eine
  Verknüpfung berührt und die Bewegungsprüfung mitläuft.
- **Festgelegt (24.10.2026):** Vorgabe A12 neu ± 20 statt ± 15 (Kamerahalter `HUB` 30 → 40) und Schenkel B des
  Kamerahalters 12 statt 10 dick (`TB`), Kameraverschraubung mit gleicher Einschraubtiefe (`schraube_kam` M3 × 10 →
  M3 × 12). Text: `tests/messstand/aufgaben/pruefstation/aufgabe.md`; Vorlage und Referenz-Specs unter
  `<arbeitsordner>/MESSSTAND/vorlagen/` (Stand Lauf 28, eingefroren 24.10.).
- Ablauf im Lauf wie im Betrieb: Skill `baugruppe`, Spec ändern, validieren, freigeben (erlaubt, `MESS-*`),
  `swki durchlauf --neustart`, Prüfer, `swki bericht`.
- Referenz: dieselbe Änderung einmal von Hand korrekt umgesetzt, gebaut, geprüft, STL der Baugruppe.
- Leck: die Referenz-Specs (`auftraege/MESSREF-pruefstation`) fehlen im Worktree; Zugriff macht den Lauf ungültig.

## 3. Präzisions-Fallen (neu)

Prüft, ob das Prüfverfahren des jeweiligen Stands Fehler findet, die `swki pruefen` grundsätzlich nicht sieht
(Spec treu gebaut, aber Eingabe falsch gedeutet). Einmal eingerichtet (§6), danach je Durchgang nur geprüft.

| ID | Falle | Herkunft |
|---|---|---|
| F1 | Durchlicht: Stecker in X gespiegelt | echt, AP 6.8 Durchlicht Lauf 4 |
| F2 | Durchlicht: Stecker 3 mm versetzt | echt, AP 6.8 Durchlicht Lauf 6 |
| F3 | Kamera: ein Merkmal aus dem Maßbild auf der falschen Seite | Falle der Messstand-Aufgabe |
| F4 | Zentrieraufnahme: eine Formschräge in falscher Richtung | Mutation der Referenz |
| F5 | Stehlager: Stiftbohrung im falschen Durchmesser laut Beschreibung | Mutation der Referenz |
| F6 | Prüfstation: Einschraublänge M5 in Alu < 2·d | echt, AP 6.8 Prüfstation Lauf 26 |
| R1, R2 | Durchlicht und Stehlager richtig (Fehlalarm-Kontrolle) | Referenzen |

Je Falle liegen fest bereit: Eingabe, freigegebene (fehlerhafte) Spec, Prüfbericht, Bilder, Steckbrief, gebaut mit dem
Stand von Durchgang 0. Je Durchgang läuft auf jeder Falle **das Prüfverfahren, das der Skill des gemessenen Stands
nach `swki pruefen` vorschreibt** (heute: Prüfer-Agent). Schreibt der Skill für diese Aufgabenart keinen Prüfschritt
vor, gibt es auf dieser Falle keinen Treffer.

- **Treffer:** ein Mangel nennt mindestens einen der erwarteten Knoten der Falle (Liste je Falle) oder trifft den Fehler
  laut Kurzbegründung (Entscheid durch die Messung, im Ergebnis vermerkt).
- **Fehlalarm:** ein Mangel auf R1/R2, der kein echter Fehler ist.
- **Streuung:** Das Prüfverfahren läuft je Falle und Durchgang **dreimal** unabhängig; Treffer bzw. Fehlalarm =
  Mehrheit (≥ 2 von 3). 8 Fallen × 3 Prüfungen laufen parallel, ~10 min je Durchgang.
- Ändert ein Umbau `swki pruefen` so, dass eine Falle schon dort auffällt (z. B. Einschraublänge als Prüfung), zählt
  das als Treffer – dann werden die Fallen mit dem neuen Stand neu gebaut und geprüft.

## 4. KPI je Lauf

Wie Messstand §2 (`zeit_s`, `zeit_anteile_s`, `tool_aufrufe`, `tokens_gewichtet`, `laeufe`, `bauabbrueche`,
`pruefmaengel`, `pruefer_maengel`, `freigaben`, `speicher_spitze_mb`, `sw_neustarts`, `bestanden`, `richtig`), dazu:

| KPI | Definition |
|---|---|
| `zeit_anteile_s.neustart` | Zeit in `werkzeuge.sw_neustart` bzw. `--neustart` (aus dem Protokoll von `durchlauf`) |
| `swki_phasen_s` | Phasen aus Bau- und Prüfprotokoll (Teile, Verknüpfen, Grundstellung, Bewegungen, Messen, Bilder) – nur Diagnose |
| `haenger` | Werkzeugaufruf über Zeitlimit oder SolidWorks-Absturz |

Diagnose-KPI gehen nicht in den Score, stehen aber in jedem Ergebnis, damit die nächste Umbau-Wahl begründet ist.

## 5. Score (0–10, absolute Anker)

Jeder Teilscore ist eine stückweise lineare Funktion durch drei Anker: **0** (schlecht), **7** (Ziel), **10** (ideal);
darüber bzw. darunter bleibt er bei 10 bzw. 0. Die Anker sind fest und hängen nicht vom Durchgang 0 ab; damit ist der
Ausgangswert eine echte Messung, kein gesetzter Wert.

| Gruppe | Gewicht | Messgröße | 0 | 7 | 10 |
|---|---|---|---|---|---|
| Zeit Teile | 15 % | Mittel `zeit_s` über durchlicht (Mittel der 2), kamera, zentrieraufnahme | 300 s | 75 s | 40 s |
| Zeit Stehlager | 10 % | `zeit_s` stehlager | 700 s | 180 s | 100 s |
| Zeit Prüfstation | 25 % | `zeit_s` pruefstation | 2400 s | 420 s | 240 s |
| Präzision erster Lauf | 20 % | Fehlerpunkte Σ über alle 6 Läufe: `bauabbrueche` + `pruefmaengel` + `pruefer_maengel` + (`freigaben` − 1) | 5 | 1 | 0 |
| Präzision Fallen | 20 % | Treffer auf F1–F6 minus Fehlalarme auf R1/R2 | 0 | 5 | 6 |
| Aufwand | 5 % | Mittel über Aufgaben `tokens_gewichtet`/Bezug, Bezug = Durchgang 0 | 2,0 | 0,6 | 0,3 |
| Robustheit | 5 % | größte `speicher_spitze_mb` im Durchgang, +2 GB je Hänger oder ungeplantem Neustart | 16 GB | 8 GB | 5 GB |

Gesamtscore = gewichtetes Mittel, eine Nachkommastelle.

**Sperren** (wie Messstand, strenger):
- Lauf nicht `bestanden` oder nicht `richtig` → `zeit_s` dieses Laufs zählt als 1,5 × Durchgang-0-Wert der Aufgabe.
- Eine Aufgabe nicht `richtig` → Gesamtscore höchstens 4,0.
- Präzision Fallen um 1 oder mehr unter dem Wert von Durchgang 0 → der Umbau gilt nicht als besser (gleich, wie der
  Rest aussieht).
- Lauf mit Leck → ungültig, wiederholen.
- **Durchgang 0:** Ein Lauf, der nicht `bestanden` oder nicht `richtig` ist, wird bis zu zweimal wiederholt. Die
  Fehlerpunkte aller Versuche zählen in „Präzision erster Lauf“, die Zeit des bestandenen Versuchs ist der Bezug. Bleibt
  er nach drei Versuchen falsch, hält die Einrichtung an und fragt den Nutzer (kein Ausgangswert mit Deckel 4,0).

Begründung der Anker: „0“ liegt etwa beim Doppelten des heutigen Stands bzw. dem Messstand-Durchgang 0; „7“ verlangt
ungefähr 2–3× schneller (Prüfstation: Werkzeugzeit ~14 min → ~5 min laut Hebel-Rangliste des Audits, Teile: zusätzlich
Modellseite); „10“ ist die geschätzte Untergrenze (SolidWorks-Arbeit + minimale Modellzeit). Präzision „7“ = höchstens
ein Fehlerpunkt im Durchgang bzw. 5 von 6 Fallen.

### 5.1 Entscheidung je Umbau

Ein Umbau darf mehrere Optimierungen bündeln (Recherche §5.1: die meisten liegen einzeln unter +0,3).

**Besser** = Gesamtscore ≥ aktueller Stand + 0,3 **und** Präzision erster Lauf und Präzision Fallen nicht schlechter
**und** keine Sperre. Dann wird der Umbau neuer Stand (Merge in den Optimierungs-Branch). Sonst verwerfen.

- Ein neuer Fehlerpunkt wird vor der Entscheidung untersucht: Folge des Umbaus → zählt; nachweislich unabhängig (z. B.
  Rechenfehler des Agenten in einem Prüfwert, den der Umbau nicht berührt) → genau dieser Lauf wird **einmal**
  wiederholt, der Wiederholungslauf zählt. Begründung steht im Ergebnis.
- Die Präzision darf nicht schlechter werden, auch wenn die Zeit stark gewinnt (Vorgabe des Nutzers: Tempo und
  Präzision sind beide Hauptziel).

### 5.2 Abbruch

Score ≥ Zielscore (§7) oder 5 Umbauten.

## 6. Einrichtung (vor dem Start der /goal-Session)

1. `werkzeuge/messstand` erweitern (Unit-Tests ohne SolidWorks, TDD): Aufgabe `pruefstation` mit Vorlage aus
   AP 6.8 Lauf 28, Referenz `MESSREF-pruefstation`, Änderungstext; Fallen-Befehl (`fallen bauen`, `fallen pruefen`);
   neue Score-Funktion nach §5 neben der alten (alte bleibt für die Ergebnisse vom 09.10.).
2. Referenz der Prüfstation-Änderung bauen und prüfen; Fallen F1–F6, R1–R2 bauen.
3. **Durchgang 0** auf dem Stand nach Einrichtung messen (6 Läufe + Fallen) → Ausgangswert, Bezug für Aufwand.
4. Ergebnisse nach `docs/laufzeit-audit/ergebnisse.md` (Muster `docs/messstand/ergebnisse.md`).

Aufwand je Durchgang geschätzt: 6 Läufe ~45 min (Prüfstation ~20 min), Ausgangslauf Prüfstation ~13 min, Fallen
~10 min – zusammen gut 1 h.

## 7. Ausgangswert und Zielscore

**Vorläufiger Ausgangswert 5,3** (aus Audit-Daten, vor Durchgang 0):

| Gruppe | Datengrundlage | Wert | Teilscore |
|---|---|---|---|
| Zeit Teile | Messstand d5: durchlicht 136 (Mittel), kamera 191, zentrieraufnahme 129 → 152 s | 152 s | 4,6 |
| Zeit Stehlager | d4/d5: 362/368 s | 365 s | 4,5 |
| Zeit Prüfstation | Live: Neustarts 28 + bauen 419 + prüfen 377 + Prüfer ~50 + Modell ~180 (geschätzt) | ~1050 s | 4,8 |
| Präzision erster Lauf | d4: 0, d5: 3 Fehlerpunkte → erwartet ~1,5 | 1,5 | 6,1 |
| Präzision Fallen | Prüfer fand die echten Fallen F1, F2, F6 jeweils; F3–F5 unbekannt → geschätzt 5 von 6 | 5 | 7,0 |
| Aufwand | Bezug = Durchgang 0 → r = 1 | 1,0 | 5,0 |
| Robustheit | Prüfstation-Spitze 14,3 GB | 14,3 GB | 1,5 |

Gewichtet: 0,15·4,6 + 0,10·4,5 + 0,25·4,8 + 0,20·6,1 + 0,20·7,0 + 0,05·5,0 + 0,05·1,5 = **5,3**. Durchgang 0
ersetzt den Wert; er wird in `ergebnisse.md` und im Goal-Auftrag eingetragen.

**Zielscore 6,5** (Nutzer 24.10.2026, nach der Recherche; ursprünglich 7,0). Die Recherche erwartet ohne Fast Mode
und ohne Abschaffung des Konstruktionsreviews +0,4 bis +0,85 über dem Ausgangswert; 6,5 verlangt die belegten Hebel
(Schnellmodus in Bewegungsprüfung und Grundstellung, Verknüpfen ohne Neuaufzählung, Teile wiederverwenden,
Einschraublänge als Prüfung, schlankerer Prüfer und Review) bei gleicher Präzision. Beispiel für 6,5: Prüfstation
350 s (8,2), Teile 130 s (5,3), Stehlager 330 s (5,0), 1 Fehlerpunkt (7,0), 5 Fallen (7,0), Aufwand 0,9 (5,5),
Speicher 13 GB (2,6).

## 8. Regeln für die /goal-Session

- Je Umbau ein Branch `btp-umbau-<n>` ab dem Optimierungs-Branch `btp` (ab `main`); Läufe in eigenen Worktrees ohne
  `docs/`, `tests/live/`, Referenzen (Messstand §1.2).
- Unit-Tests grün und Live-Regression `tests/referenz` grün, bevor gemessen wird. Neue SolidWorks-API-Aufrufe vorher mit
  `swki api methode`/`enum` nachschlagen, `swki api pruefe-code`.
- Freigabe ohne Rückfrage nur in Messstand-Aufträgen `MESS-*`.
- **Prüfer:** darf für eine Aufgabenart nur entfallen oder verkleinert werden, wenn Präzision Fallen nicht sinkt
  (Vorgabe des Nutzers: Entfall nur bei Nachweis, dass er bei 99 % der kleinen Aufgaben unnötig ist; das Audit belegt
  das nicht, siehe Audit B9).
- Keine Änderung an Konstruktionsregeln, Freigabe-Schutz, Prüfungen gegen die freigegebene Kopie oder Schwellen von
  `swki pruefen`, um Zeit zu sparen. Prüfungen dürfen schneller, nicht schwächer werden.
- **Konstruktionsreview** (Skills `konstruieren`/`baugruppe`): läuft in den Messläufen wie im Betrieb. Er darf
  schlanker werden (Modell, effort, Geltungsbereich: z. B. kein Review bei reinen Maß-, Schraubenlängen- oder
  Normteiländerungen), aber **nicht entfallen** (Nutzer 24.10.2026).
- **Fast Mode und effort des Hauptagenten** sind nicht Teil des Bogens (Kostenfrage, Nutzer 24.10.2026): kein Umbau
  darf sie ändern; Messläufe laufen mit dem Betriebsstandard.
- Kein `git push`; Merge nach `main` nur nach Rückfrage beim Nutzer.
- Jeder Durchgang: Ergebnis-Tabelle, Teilscores, Entscheidung mit Begründung in `docs/laufzeit-audit/ergebnisse.md`.

## 9. Entscheidungen des Nutzers vor der Einrichtung (24.10.2026)

1. `ap68-pruefstation` ist nach `main` gemergt (602dc8f); `btp` setzt auf `main` auf.
2. Paket Bemaßungsbezug ist vor der Einrichtung umgesetzt und gemergt; Referenz, Fallen und Durchgang 0 entstehen
   auf diesem Stand.
3. Review, Fast Mode, Zielscore: siehe §7 und §8. Die Recherche (`docs/laufzeit-audit/recherche.md`) ist Startpunkt
   der Umbau-Wahl.

## 10. Was dem Ausführenden überlassen ist

Wahl und Reihenfolge der Umbauten (Startpunkt: Hebel-Rangliste im Audit und die Recherche, falls vorhanden), genaue
Änderung der Prüfstation-Aufgabe innerhalb §2.1, Knotenlisten der Fallen, Mutation F3–F5 im Detail.
