# Paket Formschräge – Ergebnisse

Spec: docs/superpowers/specs/2026-10-07-formschraege-design.md · Plan: docs/superpowers/plans/2026-10-07-formschraege.md

## 1. Spike S16 (SOLIDWORKS 2025, Rechner A, 2026-10-08)

Rohdaten: docs/stufe0/ergebnisse/s16_formschraege.json (Lauf 3, maßgeblich) · Spike: spikes/s16_formschraege.py

Lauf 3: 150,5 s, `ok: true`, 16 Teile gebaut und ungespeichert geschlossen, Private Bytes 422 → 3554 MB. Lauf 1: 134 s, 427 → 3516 MB; Lauf 2: 150 s, 421 → 3599 MB.

| # | Frage | Annahme | gemessen (Lauf 3) | getroffen | Entscheidung (Ledger) |
|---|---|---|---|---|---|
| 1 | Richtung | `DDIR_KLEINER = True` für Aufsatz und Schnitt, alle sechs Fälle `vorzeichen_passt`, Volumen < 0,01 % | Mit `Ddir1 = True` (Lauf 2) waren alle Fälle gespiegelt: Vorzeichen umgekehrt, Volumen = Formel des anderen `querschnitt` (≤ 1e-5 %), auch mit `umkehren`. Lauf 3 (`False`): alle sechs `fehler` null, `vorzeichen_passt` true, `volumen_abw_prozent` 0,0; ex_kleiner 2175,418 (+1), ex_groesser 2884,471 (−1), sc_kleiner −2175,418 (−1), sc_groesser −2884,471 (+1), ex_kleiner_umkehren 3028,488 (+1), sc_kleiner_umkehren −1783,051 (−1), je 10,0° | Lauf 2: nein; Lauf 3: ja | `DDIR_KLEINER = {"extrusion": False, "schnitt": False}`, unabhängig von `umkehren` (Fix 5b, 2ef590b) |
| 2 | Endbedingungen | `mittig`, `durch_alles`, `bis_flaeche`, `versatz_von_flaeche` bauen, Vorzeichen passt, Volumen < 0,01 %, `mittig` beidseitig | Alle vier gebaut, `vorzeichen_passt` true, Abweichung 0,0 %: mittig 3695,725 mm³ (acht Seitenflächen alle +1, alle 5,0°), durch_alles −8759,445 (Kegel, +1), bis_flaeche −4327,864 (Kegel, −1), versatz_von_flaeche −3575,892 (Ebene + Kegel, −1). `mittig`: `koerper` 2 (Steg bewusst frei über dem Block) | ja | `mittig` schrägt beidseitig; `Dchk2`/`Ddir2`/`Dang2` bleiben ungesetzt; alle vier Endbedingungen bauen, keine Ablehnung in `validieren` |
| 3 | Ring | `volumen_aenderung` = `innen_waechst` ± 0,01 %, alle Vorzeichen +1 | `volumen_aenderung` 5175,290 = `innen_waechst` 5175,290 (< 1e-5 %); `innen_schrumpft` 5729,238 (10,7 % daneben); zwei Seitenflächen (außen, innen) beide +1, 10,0°; `koerper` 1; 2 Kegel + 1 Ebene | ja | Innenrand wächst bei `kleiner` (Spec §3 bestätigt); keine Ablehnung mehrerer Profile |
| 4 | Maße | Winkelmaß `WINKEL_MASS[ende]` (D2 bzw. D1), Gleichung `"<Maß>@f2" = "W"` | Lauf 1: `"D2@f2" = "W"`/`"D1@f2" = "W"` abgelehnt. Winkelmaß ist **D3** in allen fünf Endbedingungen (D1 = Tiefe bzw. Abstand, falls vorhanden); Wert in rad (5° 0,087266463; 10° 0,174532925; 16° 0,27925268; 17° 0,296705973; 20° 0,34906585); `"D3@f2" = "W"` angenommen und in `gleichungen` | Lauf 1: nein; Lauf 3: ja (mit D3) | `WINKEL_MASS = "D3"` für alle fünf Endbedingungen (Fix 5a, 0010215; Spec §4 nachgezogen) |
| 5 | Messung | `abw_normale_max` < 1e-9, `abw_kegelwinkel_max_grad` < 1e-6, `winkel_abw_max_grad` < 0,001 | `abw_normale_max` höchstens 1,11e-16 (Ebenen in 6_*, 7_*, mittig), `abw_kegelwinkel_max_grad` höchstens 3,6e-15 (bei Kegeln wird nur der halbe Winkel verglichen, die Richtung der Kegelschräge ist über das Volumen belegt), `winkel_abw_max_grad` 0,0 (< 5e-7; Winkel auf 6 Stellen gerundet) | ja | `toleranzen.winkel_grad` bleibt 0.01; `punkt_und_normale` bleibt bei `EvaluateAtPoint`/`FaceInSurfaceSense` |
| 6 | Eckradius | 16° gebaut, Volumen < 0,01 %; 17°/20° nicht gebaut oder Volumen ≠ Formel | 16°: gebaut, −4648,963 mm³ (0,0 %), 8 Seitenflächen −1. 17°: gebaut, −4570,705 (0,0 %). 20°: gebaut, −4335,555 gegen Formel −4335,349 (0,00475 %), 5 Ebenen + 4 Kegel, Seitenflächen −1, 20,0° (bei 20° nicht gesondert gemessen, ob die Ecken zusammenfallen) | 16°: ja; 17°/20°: nein (bauen mit passendem Volumen) | Die Regel in `validieren` (Einzug < Eckradius) bleibt als vorsichtige Regel |
| 7 | weitere Profile | Rechteck mit Eckradius `groesser` und Sechseck `kleiner`: Volumen < 0,01 % | `7_eckradius_groesser` 6791,529 mm³ (0,0 %), acht Seitenflächen −1; `7_sechseck_kleiner` 2889,188 mm³ (0,0 %), sechs Seitenflächen +1, 10,0°; alle `koerper` 1 | ja | `querschnitt_koeffizienten` bleibt |

Verlauf: Lauf 1 scheiterte an der Gleichung `D2@f2`/`D1@f2` (Winkelmaß heißt D3) → Fix 5a (0010215). Lauf 2 lieferte mit
`Ddir1 = True` in allen 16 Fällen die gespiegelte Richtung → Fix 5b (2ef590b). Lauf 3 bestätigt beide Korrekturen.
Größte Volumenabweichung in Lauf 3: 0,00475 % (`6_eckradius_20`).

## 2. Live-Tests

Quelle: `tests/live/test_live_formschraege.py` (Commit a965209)

8 Tests, alle bestanden; Volumen gegen Sollwert `swki.formschraege.volumen` mit Toleranz < 0,0001 % geprüft, Winkeltoleranz 0,01°. SW frisch (422 MB), nachher 2524 MB Private Bytes.

- `test_kreis_blind[extrusion-kleiner]`
- `test_kreis_blind[extrusion-groesser]`
- `test_kreis_blind[schnitt-kleiner]`
- `test_kreis_blind[schnitt-groesser]`
- `test_tasche_mit_eckradius_und_gleichung` (Gleichung `"D3@f2" = "W"`, W 10 → 15)
- `test_aufsatz_umgekehrt`
- `test_steg_mittig`
- `test_trichter_durch_alles`

## 3. Referenz Zentrieraufnahme

Spezifikation: `tests/referenz/zentrieraufnahme/zentrieraufnahme.yaml` (Platte 160 × 100 × 20, Eckradius 8; Zapfen, Tasche, Trichter, Steg mit Formschrägen, alle Lagen als Parameter)

**Regressionstest (Task 7):** 1 passed in 48 s, Private Bytes 419 → 1026 MB.

**Prüfer-Lauf des Controllers:** bauen Lauf 1 ok in 35 s, Prüfung 9 s, Prüfer-Agent bestanden (0 Mängel), Private Bytes nach dem Lauf 1678 MB.

| Prüfwert | Ist | Soll | Abweichung |
|----------|-----|------|-----------|
| Volumen | 315014,796 mm³ | 315014,796 mm³ | 0,0 % (Toleranz 0,05 %) |
| Hüllquader | 160 × 45 × 100 | 160 × 45 × 100 | ✓ |
| Körper | 1 | 1 | ✓ |

Formschrägen gemessen: Zapfen 10,0°, Tasche 8,0°, Steg 5,0°.

**Regression (Task 8):** OK in 46 s, Spitze ca. 3,9 GB kumuliert.

### Trichter

Der Trichter wird von der Unterseite skizziert, Auslauf Ø 10 an der Unterseite, 30° `groesser` (wird weiter), `durch_alles` durch 20 mm Platte. Oben resultiert Ø 33,09 mm (10 + 2·20·tan 30°).

Volumen Trichter (Kegelstumpf): 7990,922 mm³ (Sollwert aus `sollvolumen.py`). Gemessen 30,0° an der Kegelfläche; Richtung passt (oben weit).

## 4. Negativfälle

Quelle: `tests/live/test_live_zentrieraufnahme.py` (Commit 7495f73) · Zusammen 86,9 s, 1453 MB Private Bytes

- `test_richtung_vertauscht`: Mängel {formschraegen, volumen} am Knoten Zapfen. Text „Querschnitt nicht kleiner (…)“.
- `test_winkel_verfaelscht` (WZ+3 → 13° statt 10°): Mängel {formschraegen, volumen} am Knoten Zapfen. Text „Winkel 13° statt 10° (…)“, gemessen 13,0°.

## 5. Regression

Alle Tests über `tests\live_einzeln.py` (Rechner A, frisches SW, 2026-10-08)

**Einzelteile:** buchse OK 32 s; formplatte OK 44 s; auswerferhalteplatte OK 75 s; zentrieraufnahme OK 46 s (Spitze 3942 MB). Nach Neustart: zahnstange OK 38 s; ritzelwelle OK 66 s; antriebswelle OK 60 s (Spitze 4579 MB).

**Baugruppen (je auf frischem SW):** stehlager OK 213 s (Spitze 11191 MB); linearschlitten OK 277 s (9644 MB); zahnstangentrieb OK 499 s (10409 MB); motorhalter OK 119 s (9118 MB).

**Live-Suites berührter Bereiche (frisches SW):** `test_live_extrusion` 6/6 OK; `test_live_endbedingungen` 4/4 OK; `test_live_pruefen` 2/2 OK; `test_live_verzahnung` 6/6 OK.

**pytest -q:** 1022 passed, 152 deselected (Plan: 1021; ein Test mehr: `test_ddir_kleiner_aus_spike` aus Fix 5b).

Einstellungen nach jedem Lauf False 1, eine Instanz.

## 6. Abweichungen vom Plan

**Ledger-Entscheidungen des Controllers** (Spike S16, Tasks 5–7):

1. **Winkelmaß (Spike 4):** Alle fünf Endbedingungen nutzen **D3** als Winkelmaß, nicht D2/D1. Fix 5a (0010215). Spec §4 nachgezogen. Live-Test erwartet `"D3@f2" = "W"`.

2. **Richtung (Spike 1):** `DDIR_KLEINER = {"extrusion": False, "schnitt": False}` (True baute „groesser“), unabhängig von `umkehren`. Fix 5b (2ef590b). Neuer Test `test_ddir_kleiner_aus_spike` (+1 Test: 1022/152).

3. **Mittig (Spike 2):** Beidseitig schrägen, `Dchk2`/`Ddir2`/`Dang2` ungesetzt. Alle Endbedingungen bauen.

4. **Eckradius (Spike 6):** 17° und 20° bauen auch (Plan erwartete: nicht). Zusammenfallregel in `validieren` bleibt vorsichtig.

5. **Messung (Spike 5):** `toleranzen.winkel_grad` bleibt 0.01; Messung über `EvaluateAtPoint`/`FaceInSurfaceSense` bestätigt.

6. **Ring (Spike 3):** `volumen_aenderung` = `innen_waechst` (Innenrand wächst bei `kleiner`); keine Ablehnung mehrerer Profile.

7. **Weitere Profile (Spike 7):** Rechteck mit Eckradius `groesser` und Sechseck `kleiner` bestätigt; `querschnitt_koeffizienten` bleibt.

8. **Task 7 Step 6 (Prüfer) und Task 8 Step 4 (Regression):** Der Controller hat beide selbst ausgeführt (SolidWorks-Neustarts).

9. **Gesamt-Review:** `{nahe}`-Skizzen an schrägen Features lehnt `validieren` ab (Übergangslösung, Controller-Entscheidung), `senkrechte_kanten` wird an schrägen Features immer abgelehnt.

## 7. Offene Punkte

- Eigenes Feature Formschräge (`InsertMultiFaceDraft`) bei Bedarf über Skill `compiler-erweitern`; Formschräge an Rotation.
- Polygon bei `kleiner`: Gültigkeitsgrenze (A + P·d + K·d²), wenn eine Kante verschwindet – nicht abgefangen. Trapez mit kurzer Kante könnte falschen Volumen-Mangel auslösen.
- Bei 20° mit Eckradius: nicht gemessen, ob Ecken zusammenfallen (Volumen 0,00475 % neben Formel); Regel bleibt vorsichtig.
- Formschräge auf einer `{nahe}`-Skizze: `validieren` lehnt sie vorerst ab, weil `swki pruefen` die Skizzenebene im fertigen Teil neu auflösen müsste. Echter Fix: Extrusionsrichtung und bei `mittig` einen Punkt der Skizzenebene beim Bau ins Bauprotokoll schreiben (wie die Bohrungspunkte) und `formschraegen` daraus lesen.
- `mittig` auf einem Flächenanker, dessen Deckfläche geteilt ist: die Messung sucht die Skizzenfläche neu und kann `REFERENZ_MEHRDEUTIG` melden (gleicher Fix wie oben).
- `durchmesser_pruefen` findet an schrägen Features keinen Zylinder (Kegelfläche); Maße über Deck-/Bodenfläche mit `masse_pruefen`.
