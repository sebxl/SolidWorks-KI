# Stufe 3b – Ergebnisse (Baugruppen statisch)

Fertig-Kriterium Spec 3b §16 für Rechner A (SW 2025): Das Stehlager (Grundplatte, Lagerunterteil, Lagerdeckel, 12 Normteil-Instanzen
aus 5 Normteilen, 30 Verknüpfungen) besteht im ersten Lauf (Bau 171 s) ohne Code-Mangel und mit Prüfer-Urteil „bestanden“; die vier
Negativfälle liefern die erwarteten Mängel bzw. Codes; die Änderungserkennung ist live für ein Teil und eine Baugruppe belegt; ISO 7089
und ISO 8734 haben neue Vorlagenversionen mit bestandenem Prüfer-Urteil; 590 Unit-Tests grün. Die Regression der Bestandsreferenzen
steht im Abschnitt „Regression im Gesamtlauf“. Rechner B (SW 2026) offen.

## Fertig-Kriterium (Spec §16) und Belege

| Kriterium | Beleg |
|---|---|
| Stehlager besteht auf SW 2025 (Code-Prüfungen ohne Mangel, Prüfer „bestanden“) | `tests/referenz/test_referenzen.py::test_referenz_besteht[stehlager-stehlager.yaml]` OK im ersten Lauf (0 Bauweg-Änderungen). Auftrag `auftraege/REF-stehlager/`: Lauf 1 ok (170,8 s), 30 von 30 Verknüpfungen, `maengel` leer; Prüfer-Urteil `{"bestanden": true, "maengel": []}`; `swki status` → bestanden (Lauf 1). Einzelheiten: Abschnitt „Stehlager“ |
| Negativfälle (§14) liefern die erwarteten Mängel/Codes | `tests/live/test_live_stehlager.py`, 4/4 OK: zu lange Deckelschraube → Mangel `gewinde:deckelschraube.1` (Einschraublänge 18,60 mm); Überlappung → `kollision` mit Knoten `stift.1`, `unterteil`; unterbestimmte Komponente → `bestimmtheit` mit Knoten `unterteil`; manuelle Änderung → `MANUELL_GEAENDERT`, `aenderungen` zeigt `L` soll 200 / ist 210,0 |
| Änderungserkennung live für Teil und Baugruppe | Teil: `test_live_aenderungen.py::test_manuelle_aenderung_am_teil` (Bau → `L` von Hand auf 120 → `MANUELL_GEAENDERT` → `aenderungen` `{L, soll 100, ist 120.0}` → `bauen --verwerfen` baut Lauf 2). Baugruppe: `test_live_baugruppe.py::test_manuelle_aenderung_an_der_baugruppe` (`S` 5 → 8, Verknüpfungswert `verknuepfung:w1` soll 5,0 / ist 8,0; Prüfsummen vor/nach `aenderungen` identisch) und der Stehlager-Negativfall |
| ISO 7089 und ISO 8734: neue Vorlagenversionen mit bestandenem Urteil | Vorlagenprüfsummen `4ccce508…` (ISO 7089) und `f0a14a8f…` (ISO 8734), Urteil je `{"bestanden": true, "maengel": []}` (03.10.2026); `mass:EINBAU_EBENE_2` in beiden Musterteilen `ok: true`; `test_live_normteile.py` 13/13 OK |
| Bestandsreferenzen bestehen weiter; Unit grün; `swki api pruefe-code` ohne Befund | Unit: 590 bestanden, 108 abgewählt; `pruefe-code`: `{"max_jahr": 2025, "befunde": []}`; `tabellen-pruefen`: `"gueltig": true`. Live-Regression: Abschnitt „Regression im Gesamtlauf“ |

## Stand

- Datum: 03.10.2026, Rechner A (SOLIDWORKS 2025), Branch `stufe-3b` (von `plan-stufe-3b` @ 5605594). Ohne Push.
- Commits (5605594 = Stand der Übergabe, vor Task 1):

| Task | Inhalt | Commits |
|---|---|---|
| 1 | Spike S12 (Einfügen, Auswahl, Verknüpfungen, Kollision, Rücklesen) | 96edc7d |
| 2 | Schema, Datenmodell, Laden, `je_position` | 766d1f5 |
| 3 | Plausibilität, Passung Normteil ↔ Bohrung, Hinweise, `validieren` | 1597732 |
| 4 | Eine Freigabe für Baugruppe und Teil-Specs | 9af0007 |
| 5 | Änderungserkennung: Prüfsummen je Lauf, `MANUELL_GEAENDERT`, `swki aenderungen`, `bauen --verwerfen`; Live-Test am Teil | f6666bb, 141e9e5 |
| 6 | Neue Vorlagen ISO 7089, ISO 8734 (Einbauebene 2) und Prüfer-Urteile | e76e48d, 4c69eb7 |
| 7 | Referenzen im Teil auflösen, SolidWorks-Helfer für Baugruppen | 27327a7 |
| 8 | `swki bauen` für Baugruppen (Unit, Live, Review-Fix) | 48b2c7e, ab66f23, 34156ba |
| 9 | Bewertung (Verknüpfungen, Bestimmtheit, Kollision, Gewinde, Lage) | 6f40e8c, e9ad9dc |
| 10 | `swki pruefen`, `status`, `bericht`, Verknüpfungswerte in `aenderungen` (Unit, Live, Fix) | 74dc3e2, be8e031, a60abfd |
| 11 | Referenz Stehlager und Negativfälle | f513e28, b7ef5a6 |
| 12 | Skill `baugruppe`, Prüfer, `CLAUDE.md`, Design §4/§6/§11, Ergebnisse, Regression | Doku-Commit „docs: Skill baugruppe …“, Commit „docs: Regression Stufe 3b“ |

Jeder Task wurde einzeln reviewt (Spec- und Qualitätsprüfung); Tasks 8, 9 und 10 brauchten je eine Fix-Runde (siehe Entscheidungen).

## Unit-Tests

`.venv\Scripts\python.exe -m pytest -q`: **590 bestanden, 108 abgewählt** (die `sw`-markierten Live-Tests). Vor dem Plan: 456
bestanden, 95 abgewählt. Zuwachs je Task (bestanden): Task 2 +17 (473), Task 3 +33 (506), Task 4 +7 (513), Task 5 +10 (523),
Task 6 +2 (525), Task 7 +15 (540; 6 mehr als im Plan wegen Ruling A), Task 8 +6 (546) und +5 aus der Fix-Runde (551), Task 9 +22
(573) und +10 aus der Fix-Runde (583), Task 10 +6 (589), Task 11 +1 (590); Tasks 1 und 12 ohne neue Unit-Tests. Die Planzahl 566
wird übertroffen, weil Rulings und Review-Fixes zusätzliche Tests brauchten. Die 13 zusätzlichen abgewählten Tests sind
Live-Tests: `test_live_aenderungen` 1 (Task 5), `test_live_baugruppe` 4 (Task 8) und 3 (Task 10), Referenzeintrag Stehlager 1 und
`test_live_stehlager` 4 (Task 11).
`swki api pruefe-code`: keine Befunde (`max_jahr` 2025). `swki normteil tabellen-pruefen`: `"gueltig": true`, 6 Größen je Norm,
nichts gesperrt.

## Live-Ergebnisse je Task (SolidWorks 2025, Rechner A)

Alle Live-Tests liefen einzeln (`tests\live_einzeln.py`, `PYTHONIOENCODING=utf-8`), mit genau einer SolidWorks-Instanz und
Toggle 10 / Integer 6 = `False 1` vor und nach dem Lauf. Private Bytes von `SLDWORKS.exe`:

| Task | Datei / Test | Ergebnis | Private Bytes vorher → nachher |
|---|---|---|---|
| 1 | `spikes/s12_baugruppe.py` (4 Läufe) | `"ok": true` | 414 → 3368 MB |
| 5 | `test_live_aenderungen.py` (1) | OK | 430 → 1099 MB |
| 5 | `test_live_bauen.py` (3) | OK | 1099 → 1305 MB |
| 6 | `test_live_normteile.py` (13, mit ISO 7089 ×3 und ISO 8734 ×3 gegen die neuen Vorlagen) | 13/13 OK | 1039 → 3309 MB (danach Musterteile: 3700 MB) |
| 8 | `test_live_baugruppe.py` (4: Probe, Wertverknüpfungen, senkrecht, fehlende Referenz) | 4/4 OK, wiederholt nach dem Fix | 421 → 2480 MB; zweiter Lauf → 4168 MB |
| 10 | `test_live_baugruppe.py` (6, mit Prüfung und Kollision) | 6/6 OK | 420 → 5635 MB (Neustart danach) |
| 10 | `test_live_pruefen.py` (2) | 2/2 OK | 424 → 1166 MB |
| 10 | `test_live_aenderungen.py` (1) | OK | 1166 → 1467 MB |
| 10 | Probe-Baugruppe, Werte der Gewindepaarung (Scratch-Lauf) | `maengel` leer | → 3248 MB |
| 10 | `test_manuelle_aenderung_an_der_baugruppe` | OK | 420 → 1331 MB |
| 11 | `test_referenzen.py::…stehlager…` | OK | 416 → 4039 MB |
| 11 | `test_zu_lange_deckelschraube` | OK | 426 → 3496 MB |
| 11 | `test_ueberlappung` | OK | 427 → 3467 MB |
| 11 | `test_unterbestimmte_komponente` | OK | 424 → 3753 MB |
| 11 | `test_manuelle_aenderung_in_der_baugruppe` | OK | 426 → 2282 MB |

Prüfwerte, Toleranzen und Sollvolumen wurden in keinem Lauf an Messwerte angepasst. In Task 11 war keine Bauweg-Änderung nötig.

### Speicher

Ein Stehlager-Lauf (Bau und Prüfen nach frischem Start) kostete 3,1–3,6 GB Private Bytes (416 → 4039 MB, 426 → 3496 MB, 427 → 3467 MB,
424 → 3753 MB) statt der im Plan geschätzten 0,6–1 GB. Darin steckt der Aufbausprung des ersten Baus nach einem Neustart
(ca. +1,6 GB), doch auch danach wächst SolidWorks je Baugruppe um mehrere hundert MB bis 1 GB. Folgen: jeder Stehlager-Test läuft in
einem eigenen Prozess und mit einem SolidWorks-Neustart davor; die Probe-Baugruppe (vier Bauten und Prüfungen) erreichte
5,6 GB. Der Skill `baugruppe` verlangt nach jedem Baugruppenlauf die Prüfung der Private Bytes und einen Neustart ab ca. 4 GB;
SolidWorks startet Claude selbst neu (Nutzervorgabe 03.10.2026), nicht der Nutzer. Beim Gesamtlauf der Regression hält der
Ablauf ab ca. 3 GB vor dem nächsten Test an.

## Spike S12

Rohdaten: `docs/stufe0/ergebnisse/s12_baugruppe.json` (`"ok": true`, vierter Lauf), Code `spikes/s12_baugruppe.py`. Antworten auf die
14 Zeilen der Abhängigkeitstabelle des Plans:

| Nr. | Frage | Antwort | Beleg |
|---|---|---|---|
| 1 | Einfügen mit Boxzentrum: Ursprung im Baugruppenursprung | ja, Translation 0 (das Boxzentrum landet auf dem Einfügepunkt, der Teilursprung bleibt bei 0) | `baugruppe_1.einfuegen_*.transform_nach_einfuegen` |
| 2 | `FixComponent` → `IsFixed` | ja | `baugruppe_1.sockel_fixiert` |
| 3 | Auswahl in der Komponente | ja (Ebenen/Achsen über `FeatureByName`, Flächen/Zylinder über `GetCorrespondingEntity`) | `baugruppe_1.mates.*.auswahl` |
| 4 | `AddMate5` für die sechs Typen | ja, Status 1, Fehlercode 0; Typen 0, 1, 3, 2, 5, 6 | `imate2_typ`, `status` |
| 5 | Bedeutung der Ausrichtung | **teilweise:** „gleich = Ebenennormale gleichgerichtet zur äußeren Flächennormale“ stimmt, aber SolidWorks kehrt die Ausrichtung einer früheren Verknüpfung still um, wenn eine spätere widerspricht (siehe Ruling A) | `baugruppe_1.mate_ausrichtungen_nachher`, 5a–5f |
| 6 | `LockRotation` | ja: Schraube Status 3 mit Sperre, Stift Status 2 ohne | `lage.*.status` |
| 7 | Status der fixierten Komponente | 3, `IsFixed` wahr | `lage.sockel` |
| 8 | Maß der Abstands-/Winkelverknüpfung | ja, `D1@w1` = 0,015 m, 30° = 0,5236 rad; die Gleichung `"D1@w1" = "S"` bindet (S = 25 → y = 45) | `baugruppe_2_werte` |
| 9 | Kollision | ja: genau eine Interferenz Sockel/Schraube mit 126,122379 mm³ gegen Soll 126,1224 (Abweichung 0,00002 %); Berührung ist keine Interferenz | `baugruppe_5b/5d/5e.interferenzen` |
| 10 | Wieder öffnen | ja, 0 Fehler, dieselben Interferenzen und Status, Prüfsumme unverändert; Reihenfolge von `GetComponents` weicht ab → nach `Name2` zuordnen | `wieder_geoeffnet*` |
| 11 | Rücklesen von Gleichungen | ja, Format `"L"= 100`, Prüfsumme unverändert | `ruecklesen_sockel` |
| 12 | Transform-Konvention | **teilweise:** Zeilenkonvention bestätigt (`MultiplyTransform`), aber `GetCorrespondingEntity(...).Normal` liefert Teilkoordinaten, nicht Baugruppenkontext (siehe Ruling B) | `baugruppe_2_werte.bild_*` |
| 13 | Ebene + zwei konzentrische Bohrungen | Status 3 (voll bestimmt, nicht überbestimmt); ein widersprüchliches Maß liefert Status 5, Fehlercode 47, Lage 4 | `baugruppe_4_zwei_konzentrische`, `baugruppe_6_widerspruch` |
| 14 | `GetBox(0)` | ja, eng (≤ 0,0001 mm Abweichung); Vorbehalt: die Extremwerte lagen in y, die Enge bei drehungsempfindlicher Geometrie ist nicht belegt | `getbox_mm` |

## Stehlager

Auftrag `REF-stehlager` (Specs unter `tests/referenz/stehlager/`): Grundplatte (Platte mit zwei Durchgangsbohrungen und zwei
Stiftbohrungen), Lagerunterteil (Fuß und Lagerblock mit Lagerbohrung Ø 40, zwei Gewinde M8, zwei Durchgangsbohrungen, zwei Stiftbohrungen), Lagerdeckel
(Halbschale Ø 40, zwei Normbohrungen für Zylinderschrauben M8); Normteile ISO 8734 8×30 (2), ISO 4762 M8×35 (2) und M10×55 (2), ISO 7089 M10 (4), ISO 4032 M10 (2); 30
Verknüpfungen, eine Freigabe für alles. Parameter `H` = 70 (Achshöhe).

- **Läufe:** ein Lauf, Bau ok in 170,8 s (Teile 54,4 s, Normteile 3,0 s, Einfügen 4,2 s, Verknüpfen 107,0 s, Speichern 0,4 s), keine
  Compiler-Änderung. Im Live-Test (Referenz-Suite) und im Controller-Lauf je im ersten Versuch bestanden, 0 Bauweg-Änderungen.
- **Prüfbericht (alle `ok`):** Rebuild ohne Fehler; Verknüpfungen 30 von 30 (nichts fehlend, fehlerhaft oder fremd); Bestimmtheit
  ohne Abweichung; Stückliste stimmt (1 Grundplatte, 1 Lagerunterteil, 1 Lagerdeckel, 2 ISO 8734 8×30, 2 ISO 4762 M8×35, 2 ISO 4762 M10×55,
  4 ISO 7089 M10, 2 ISO 4032 M10); Kollision keine; Hüllquader [200, 113, 100] mm = Soll; Maße Achshöhe Unterteil 70,0 / 70, Deckel auf
  der Trennebene 70,0 / 70, Stift bündig 0,0 / 0; Gesamtmasse 6,2827 kg.
- **Gewindepaarungen (Einschraublänge, Volumen ist/soll):**

  | Schraube | Teil | Bohrung | Einschraublänge (mm) | Gewindetiefe (mm) | Volumen ist / soll (mm³) |
  |---|---|---|---|---|---|
  | deckelschraube.1 | unterteil | f3.1 | 13,6 | 16,0 | 176,338 / 176,338 |
  | deckelschraube.2 | unterteil | f3.2 | 13,6 | 16,0 | 176,338 / 176,338 |

  Zusätzlich die Probe-Baugruppe aus Task 10: Einschraublänge 9,6 mm (Gewindetiefe 12, Bohrtiefe 16), Volumen 120,543 mm³ = Soll 120,543 mm³
  an beiden Schrauben.
- **Teilprüfungen:** Grundplatte, Unterteil und Deckel bestehen (Hüllquader, Abstände, Lagerbohrung Ø 40, Material 1.0038, Eigenschaften). Das Volumen der
  Grundplatte ist `ok: null` mit Hinweis „Sollvolumen nicht berechenbar (f2: Bohrung durch)“; Unterteil und Deckel haben kein Volumenziel.
- **Prüfer-Urteil** (Eingabe, alle freigegebenen Specs, Prüfbericht, Screenshots; keine Protokolle): `{"bestanden": true, "maengel": []}`,
  abgelegt als `protokolle/stehlager.lauf-1.pruefer.json`; der Iso-Screenshot wurde zusätzlich gesichtet und ist plausibel.
  `swki status` → bestanden (Lauf 1), `swki bericht` → `bericht.md`.
- **Negativfälle:** siehe Fertig-Kriterium (4/4 OK).

## Präzisierungen gegenüber der Spec

Die zehn Präzisierungen des Plans und ihr Schicksal in der Umsetzung:

1. **Gewindepaarung über die Lage (Spec §9.3):** umgesetzt und im Stehlager bestätigt (die Schraube sitzt auf der Senkung im Deckel,
   der Eintrittspunkt liegt im Unterteil; Zuordnung über die Achse, Toleranz `anker_mm`).
2. **Gewinde `durch`:** umgesetzt (Volumen ohne Soll, `ok: null` mit Hinweis); das Stehlager nutzt Gewinde mit `tiefe`.
3. **ISO 8734 `c` (Spec §12): Abweichung, nicht direkt gemessen.** Für Fasen gibt es keine Messart; `c` bleibt wie in 3a über das Volumen
   belegt, die neue Vorlagenversion misst nur `EINBAU_EBENE_2` gegen +y mit Soll 0. **Dem Nutzer bei der Übergabe als Abweichung von Spec
   §12 melden.**
4. **Teilprüfung je Teil-Spec** (nicht je Instanz): umgesetzt, Präfix und Knoten nennen die erste Komponente (`unterteil: …`, `unterteil/f3`).
5. **Messpunkte der Baugruppe:** umgesetzt wie festgelegt (`punkt` oder `komponente` + Teil-Messpunkt; gemessen im Teildokument, übertragen mit
   `Transform2`).
6. **Gesamtmasse** (`pruefung.masse`) in kg: umgesetzt (das Stehlager führt sie nicht; im Prüfbericht steht die Masse 6,2827 kg).
7. **Bestimmtheit und Kollision** als je eine Prüfung mit den abweichenden Komponenten als Knoten, Gewinde je Schraube
   `gewinde:<instanz>`: umgesetzt.
8. **Änderungserkennung** (höchster Lauf mit Status `ok`, keine Verweigerung ohne Prüfsummen oder bei fehlendem Lauf-Ordner,
   `.sldprt`/`.sldasm` inhaltlich verglichen): umgesetzt, live belegt (Teil, Baugruppe).
9. **Konzentrisch ohne `ausrichtung`: ersetzt durch Ruling A** (nächstliegend statt „gleich, bei Fehler entgegengesetzt“), siehe unten.
10. **Hüllquader der Baugruppe** über `GetBox(0)`: eng anliegend (Spike Z14), Toleranz wie im Plan; im Stehlager [200, 113, 100] = Soll.

Nicht übernommen in die Spec 3b (siehe Ruling G): Die abgestimmte Spec ist unverändert. Sie weicht in diesen Punkten von der Umsetzung ab:
Spec §4.4 („nächstliegend als Vorgabe gibt es nicht“) – swki legt `konzentrisch` ohne `ausrichtung` intern mit nächstliegend an, als
Spec-Wert bleibt es verboten; Spec §11 kennt `SCHLIESSEN_FEHLER` nicht; Spec §12 verlangt `c` direkt gemessen (Präzisierung 3).

## Entscheidungen während der Umsetzung

Rulings des Controllers, jeweils mit Begründung; „kostet bei Irrtum“ = Aufwand der Korrektur:

- **Ruling A (Task 1, Spike Z5): Konzentrisch ohne `ausrichtung` mit CLOSEST statt „gleich, bei Fehler entgegengesetzt“.**
  SolidWorks kehrt die Ausrichtung einer früheren Verknüpfung still um (kein Status, kein Fehlercode, kein Rebuild-Fehler); der
  Plan-Fallback hätte nie angeschlagen, die Schraube stünde kopfüber. Mit CLOSEST bleibt die schon festgelegte Richtung erhalten (Spike 5e/5f).
  Zusätzlich liest `verknuepfe` nach jeder neuen Verknüpfung die Ausrichtung aller bisher ausdrücklich gesetzten zurück
  (`IMate2.Alignment`, Dict `gesetzt` über alle Verknüpfungen); weicht eine ab, wird die neue Verknüpfung gelöscht und der Bau bricht mit
  `VERKNUEPFUNG_FEHLER` „<id> kehrt die Ausrichtung von <name> um“ ab. Kostet bei Irrtum: Die Einfügelage bestimmt die Richtung der
  ersten konzentrischen Verknüpfung einer Komponente (alle Einfügungen mit Identität, also deterministisch); eine spätere ausdrückliche Ebene gewinnt ohnehin.
- **Ruling B (Z12):** Messgeometrie im Baugruppenkontext nur über Teil-Geometrie × `Transform2`, nie über `.Normal` der Corresponding Entity
  (liefert Teilkoordinaten). Keine Codeänderung, der Plan-Code maß schon im Teildokument.
- **Ruling C (Z10):** Komponenten nach dem Öffnen nur über `Name2` zuordnen, nie über den Index von `GetComponents`. Dazu Dateinamen schreibungsunabhängig
  vergleichen (`GetPathName` liefert bei Eigenteilen `.SLDPRT`, bei Normteilen `.sldprt`); die Stückliste vergleicht mit `casefold`.
- **Ruling D (Z9, Z14):** `KOLLISION_MIN_MM3` entfällt (Berührung liefert keine Treffer), `TOL_GEWINDE_PROZENT = 1,0` bestätigt (Abweichung 0,00002 %),
  `huellquader_tol` bleibt der Planwert.
- **Ruling E:** Die Spec verlangt, dass `pruefen` und `aenderungen` nie speichern, hatte aber keinen Test. Die Live-Tests der Baugruppe prüfen jetzt,
  dass alle SHA-256 des Laufs nach `pruefen` und nach `aenderungen` unverändert sind.
- **Ruling F (Task 9):** Eine fixierte Komponente ist ein Mangel, wenn sie nicht fixiert ist **oder** ihr Status überbestimmt ist. Der Plan prüfte nur
  `IsFixed`, was der Regel „überbestimmt ist immer ein Mangel“ widersprach. Der Spike zeigt Status 3 für die fixierte Komponente, also kein Fehlalarm.
- **Ruling G (Task 12):** Die mit dem Nutzer abgestimmte Spec 3b bleibt unverändert; Abweichungen stehen hier und im Skill `baugruppe`. Die Skill-Zeile
  „eine zweite konzentrische Bohrung kann überbestimmen (Spike S12)“ aus dem Plan wurde korrigiert, weil Spike Z13 Status 3 zeigt: empfohlen bleibt
  Auflage + **eine** konzentrische Bohrung + `parallel` (bewährt im Stehlager); Widersprüche meldet SolidWorks als überbestimmt (Status 5, Fehlercode 47),
  `swki pruefen` als Mangel `bestimmtheit`.
- **Neuer Fehlercode `SCHLIESSEN_FEHLER` (Task 8):** Schließen eines Dokuments nach dem Bau scheitert, ohne früheren Fehler. Ein Schließfehler verdeckt
  einen ursprünglichen Fehler nie und hält die übrigen Schließvorgänge nicht auf. Er fehlt in Spec §11.
- **Fehlermeldungen (Review Task 8):** `bauen` nennt Komponente bzw. Verknüpfung in der `meldung` (Spec §11), und jedes selbst geöffnete Dokument wird im
  `finally` fehlerfest geschlossen.
- **Teilbericht-Pflicht (Task 9/10):** Ein fehlender Teilbericht gilt nicht als bestanden; der Plan-Code war hier fail-open (siehe Offene Punkte).
- **Live-Test an der Baugruppe (Review Task 10):** `aenderungen` öffnet SolidWorks nur für geänderte Dateien; der Test `test_manuelle_aenderung_an_der_baugruppe`
  belegt den Verknüpfungswert `w1` und das Nicht-Speichern live.
- **Neustarts:** SolidWorks wurde nach den Tasks 1, 6, 8, 10 und mehrfach in Task 11 neu gestartet (Speicher, siehe oben); der Controller prüfte danach jedes Mal
  eine Instanz, sichtbares Fenster und `False 1`.
- **Zwei Commits je Live-Task:** Unit-Teil zuerst, Live-Teil nachgeholt, sobald SolidWorks frei war (bewährtes Muster aus 3a).

## Offene Punkte

- **Spec 3b nicht nachgezogen (Ruling G):** Spec §4.4, §11, §12 weichen von der Umsetzung ab (siehe Präzisierungen); bei Wunsch eine kleine Doku-Änderung.
- **`c` bei ISO 8734** nur über das Volumen belegt (Präzisierung 3); gilt auch für `p` und die Kopffase bei ISO 4762 aus 3a. Eine Messart für Fasen
  wäre ein eigenes Paket.
- **Gewinde `durch`:** keine Volumenprüfung (Bohrungslänge nicht in der Spec); Gewinde mit `tiefe` werden geprüft.
- **Grundplatte:** `volumen` ist `ok: null` (Sollvolumen bei Bohrung `durch` nicht berechenbar); Unterteil und Deckel haben kein Volumenziel.
- **Rechner B (SW 2026):** nicht gelaufen; die Vorlagen und das Stehlager müssen dort einmal bestehen.
- **Speicher:** ein Baugruppenlauf kostet 3–4 GB; größere Baugruppen brauchen mehr Neustarts, ein Ablauf mit Speichergrenze im Compiler steht aus.
- **Stufe 4 (mechanische Abläufe):** `bewegungen`, `treibend`, gezählte `freiheitsgrade`, Unterbaugruppen und Konfigurationen sind nicht in 3b.
- **Zurückgestellte Kleinbefunde aus den Reviews** (nichts blockierte; vor dem Merge triagieren):
  - **Task 1:** Bericht-Deutungen Z1/Z10 ungenau; `EditRebuild3`/`EvaluateAll` im Spike ohne `_FlagAsMethod`; CLOSEST nur für „Ebene vor Achse“ belegt; Zeilenkonvention nur für
    Drehung um y belegt.
  - **Task 2:** Schema erlaubt `drehung_sperren` bei jedem Typ (Spec nur `konzentrisch`); Schema-Tests prüfen nur „nicht leer“; fehlende Tests (Schemafehler über `lade_baugruppe`,
    `NORMTEIL_UNBEKANNT`/`VARIANTE`/`GESPERRT`, geteilte Teil-Spec); `anzahl_positionen` bei fehlendem Feature ohne Meldung.
  - **Task 3:** mehrere Plausibilitätszweige ungetestet (doppelte IDs, `fixiert` + `je_position`, `abstand < 0`, `winkel`, Ausdrucksfehler); ISO 7089/4032 passen auch auf `normbohrung`
    `gewinde` (Spec-Wortlaut, fachlich fragwürdig).
  - **Task 4:** kein Golden-Test für die unveränderte Teil-Prüfsumme; die Meldung nennt das Teil nicht, wenn es einzeln neu freigegeben wurde; Teile vor der Baugruppe nicht atomar geschrieben.
  - **Task 5:** `baue_teil_dokument` schließt das Dokument bei unerwarteten Ausnahmen nicht; `aenderungen` braucht immer eine gültige Freigabe; aufgeräumter Lauf-Ordner → alles
    „fehlend“ ohne Hinweis; SolidWorks-Zweig von `aenderungen` ohne Unit-Test.
  - **Task 6:** neuer Vorlagen-Test spiegelt die YAML-Struktur; `EINBAU_EBENE` von ISO 7089 nicht mitgeprüft.
  - **Task 7:** Ausrichtungsprüfung erst nach `Add2` (die Gleichung bleibt bei Umkehr stehen); nur `BauFehler` gefangen (ein COM-Fehler beim Rücklesen lässt die Verknüpfung stehen);
    `GLEICHUNG_FEHLER` wird zu `VERKNUEPFUNG_FEHLER` umgepackt; Testlücken (Gleichungspfad, Mehrfachnamen, `loese_im_teil` für `nahe`/Fläche/Instanzfläche).
  - **Task 8:** fehlende Unit-Tests für Kernpfade (Schließen, `uebersprungen`, Reihenfolge, Bibliothek unverändert); nicht eingefügte Komponenten nicht als `uebersprungen`;
    `NormteilFehler.daten` gehen beim Umwickeln verloren; `test_senkrecht` prüft nur den Exit-Code.
  - **Task 9:** `next(...)` dupliziert `komponente_von` (StopIteration); Hüllquader-/Maßlogik dupliziert aus `pruefung/bewertung.py`; `abs()` in `einschraublaenge` verdeckt das Vorzeichen;
    Division durch 0 bei `masse.soll = 0`; doppelte Prüf-IDs `gewinde:<schraube>` bei Mehrfachpaarung.
  - **Task 10:** `soll_verknuepfungswerte` nutzt die Parameter der aktuellen statt der freigegebenen Spec; Teilprüfungen im Live-Test nicht assertiert; `KeyError` bei fehlendem
    `protokoll["teile"]`-Eintrag; `default=str` im Prüfbericht.
  - **Task 11:** Negativtests prüfen nur das Vorkommen des Mangels (nicht, dass keine Zusatzmängel fehlen); nur `deckelschraube.1`; der Test der Änderungserkennung prüft nur die Grundplatte;
    Import des privaten Helfers `_setze_parameter`; die Achshöhe ist fast tautologisch gemessen, die Lagerbohrungsachse nicht in der Höhe; die Commit-Message b7ef5a6 („noch nicht live gelaufen“) ist
    veraltet (Tests sind gelaufen).

## Regression im Gesamtlauf

Wird nach dem Lauf eingetragen (Task 12, Step 8).
