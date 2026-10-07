# Paket Formschräge – Ergebnisse

Spec: docs/superpowers/specs/2026-10-07-formschraege-design.md · Plan: docs/superpowers/plans/2026-10-07-formschraege.md

## 1. Spike S16 (SOLIDWORKS 2025, Rechner A, 2026-10-08)

Rohdaten: docs/stufe0/ergebnisse/s16_formschraege.json (Lauf 3, maßgeblich) · Spike: spikes/s16_formschraege.py

Lauf 3: 150,5 s, `ok: true`, 17 Teile gebaut und ungespeichert geschlossen, Private Bytes 422 → 3554 MB.

| # | Frage | Annahme | gemessen (Lauf 3) | getroffen | Entscheidung (Ledger) |
|---|---|---|---|---|---|
| 1 | Richtung | `DDIR_KLEINER = True` für Aufsatz und Schnitt, alle sechs Fälle `vorzeichen_passt`, Volumen < 0,01 % | Mit `Ddir1 = True` (Lauf 2) waren alle Fälle gespiegelt: Vorzeichen umgekehrt, Volumen = Formel des anderen `querschnitt` (≤ 1e-5 %), auch mit `umkehren`. Lauf 3 (`False`): alle sechs `fehler` null, `vorzeichen_passt` true, `volumen_abw_prozent` 0,0; ex_kleiner 2175,418 (+1), ex_groesser 2884,471 (−1), sc_kleiner −2175,418 (−1), sc_groesser −2884,471 (+1), ex_kleiner_umkehren 3028,488 (+1), sc_kleiner_umkehren −1783,051 (−1), je 10,0° | Lauf 2: nein; Lauf 3: ja | `DDIR_KLEINER = {"extrusion": False, "schnitt": False}`, unabhängig von `umkehren` (Fix 5b, 2ef590b) |
| 2 | Endbedingungen | `mittig`, `durch_alles`, `bis_flaeche`, `versatz_von_flaeche` bauen, Vorzeichen passt, Volumen < 0,01 %, `mittig` beidseitig | Alle vier gebaut, `vorzeichen_passt` true, Abweichung 0,0 %: mittig 3695,725 mm³ (acht Seitenflächen alle +1, alle 5,0°), durch_alles −8759,445 (Kegel, +1), bis_flaeche −4327,864 (Kegel, −1), versatz_von_flaeche −3575,892 (Ebene + Kegel, −1). `mittig`: `koerper` 2 (Steg bewusst frei über dem Block) | ja | `mittig` schrägt beidseitig; `Dchk2`/`Ddir2`/`Dang2` bleiben ungesetzt; alle vier Endbedingungen bauen, keine Ablehnung in `validieren` |
| 3 | Ring | `volumen_aenderung` = `innen_waechst` ± 0,01 %, alle Vorzeichen +1 | `volumen_aenderung` 5175,290 = `innen_waechst` 5175,290 (< 1e-5 %); `innen_schrumpft` 5729,238 (10,7 % daneben); zwei Seitenflächen (außen, innen) beide +1, 10,0°; `koerper` 1; 2 Kegel + 1 Ebene | ja | Innenrand wächst bei `kleiner` (Spec §3 bestätigt); keine Ablehnung mehrerer Profile |
| 4 | Maße | Winkelmaß `WINKEL_MASS[ende]` (D2 bzw. D1), Gleichung `"<Maß>@f2" = "W"` | Lauf 1: `"D2@f2" = "W"`/`"D1@f2" = "W"` abgelehnt. Winkelmaß ist **D3** in allen fünf Endbedingungen (D1 = Tiefe bzw. Abstand, falls vorhanden); Wert in rad (5° 0,087266463; 10° 0,174532925; 16° 0,27925268; 17° 0,296705973; 20° 0,34906585); `"D3@f2" = "W"` angenommen und in `gleichungen` | Lauf 1: nein; Lauf 3: ja (mit D3) | `WINKEL_MASS = "D3"` für alle fünf Endbedingungen (Fix 5a, 0010215; Spec §4 nachgezogen) |
| 5 | Messung | `abw_normale_max` < 1e-9, `abw_kegelwinkel_max_grad` < 1e-6, `winkel_abw_max_grad` < 0,001 | `abw_normale_max` höchstens 1,11e-16 (Ebenen in 6_*, 7_*, mittig), `abw_kegelwinkel_max_grad` höchstens 3,6e-15, `winkel_abw_max_grad` 0,0 (< 5e-7; Winkel auf 6 Stellen gerundet) | ja | `toleranzen.winkel_grad` bleibt 0.01; `punkt_und_normale` bleibt bei `EvaluateAtPoint`/`FaceInSurfaceSense` |
| 6 | Eckradius | 16° gebaut, Volumen < 0,01 %; 17°/20° nicht gebaut oder Volumen ≠ Formel | 16°: gebaut, −4648,963 mm³ (0,0 %), 8 Seitenflächen −1. 17°: gebaut, −4570,705 (0,0 %). 20°: gebaut, −4335,555 gegen Formel −4335,349 (0,00475 %), 5 Ebenen + 4 Kegel, Seitenflächen −1, 20,0° | 16°: ja; 17°/20°: nein (bauen mit passendem Volumen) | Die Regel in `validieren` (Einzug < Eckradius) bleibt als vorsichtige Regel |
| 7 | weitere Profile | Rechteck mit Eckradius `groesser` und Sechseck `kleiner`: Volumen < 0,01 % | `7_eckradius_groesser` 6791,529 mm³ (0,0 %), acht Seitenflächen −1; `7_sechseck_kleiner` 2889,188 mm³ (0,0 %), sechs Seitenflächen +1, 10,0°; alle `koerper` 1 | ja | `querschnitt_koeffizienten` bleibt |

Verlauf: Lauf 1 scheiterte an der Gleichung `D2@f2`/`D1@f2` (Winkelmaß heißt D3) → Fix 5a (0010215). Lauf 2 lieferte mit
`Ddir1 = True` in allen 17 Fällen die gespiegelte Richtung → Fix 5b (2ef590b). Lauf 3 bestätigt beide Korrekturen.
Größte Volumenabweichung in Lauf 3: 0,00475 % (`6_eckradius_20`).
