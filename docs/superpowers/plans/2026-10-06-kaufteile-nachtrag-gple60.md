# Stufe 3c – Plan-Nachtrag: Nanotec GPLE60-2S-32 statt Muster-Getriebemotor, Gewinde-Ø-Bereich

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Hauptplan:** `docs/superpowers/plans/2026-10-06-kaufteile-step-import.md` (Stufe 3c). Dieser Nachtrag **ersetzt** dort
Task 7 und Task 10 vollständig (als Task 7N und Task 10N), ändert Task 11 (Task 11N, nur die Abweichungen) und schiebt
davor den neuen Task G. Alles andere im Hauptplan (Global Constraints, Präzisierungen, Ersetzungsregel „genau einmal“,
Speicher- und Neustartregeln, Prüfwerte nie an Messwerte anpassen) gilt weiter, soweit unten nichts anderes steht.

**Spec:** `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` (Task G zieht §4.3, §5.3, §6.4, §10 nach;
Task 11N §2, §11, §15). **Ledger:** `.superpowers/sdd/2026-10-06-kaufteile-step-import/progress.md` (Nutzerentscheidungen,
Rulings N1–N7, Befund G1). **Diagnose GPLE60:** `.superpowers/sdd/2026-10-06-kaufteile-step-import/gple60-untersuchen.json`
(live, `swki kaufteil untersuchen`, lauf-1).

**Stand bei Planbeginn:** Tasks 1–6, 8 (mit Fix 1), Fix-N und Task 9 committet (HEAD `5ee0086`), Unit-Suite
**923 passed, 138 deselected**. Der Muster-Eintrag aus Task 7 wurde nie freigegeben und ist gelöscht (Ruling N2).

## Anlass

1. Der Nutzer hat die Freigabe des fiktiven Muster-Eintrags abgelehnt („echte STEP-Datei von einem Hersteller mit
   Datenblatt“). Der erste echte Kandidat (Nanotec ST4118M1804-A) ist ein reines Flächenmodell (Fix-N: Mangel `import`), der
   zweite (DB42) hat M3-Flanschgewinde, die in `bohrungsnormen.yaml` und ISO 4762 fehlen. Gewählt: **Nanotec GPLE60-2S-32**.
2. **Befund G1:** Nanotec modelliert die Flanschgewinde M5 mit dem Kerndurchmesser **D1 = 4,134** (ISO 724), nicht mit dem
   Bohrer-Ø 4,2 der Tabelle. Die Gegenprobe aus Spec §4.3 (nur 4,2 ± 0,01 oder 5,0 ± 0,01) würde jede solche Datei mit
   Mangel `gewinde:<gruppe>` ablehnen.
3. **Task-9-Review:** Beim Modell `nenn` ist das Soll der Überlappung 0 und die Toleranz relativ (1 % von 0) – jedes
   Rauschvolumen > 0 wäre ein Mangel.

## Nutzerentscheidungen (2026-10-06, nach dem Hauptplan)

1. Der fiktive Muster-Getriebemotor wird **nicht** Katalogeintrag. Katalogeintrag wird das echte Herstellerteil **Nanotec
   GPLE60-2S-32** (Präzisions-Planetengetriebe). Original
   `https://www.nanotec.com/fileadmin/files/Datenblaetter/Getriebe/Planetengetriebe_GPLE60/GPLE60-2S.stp` (heruntergeladen
   2026-10-06, nutzerfreigegeben), Datenblatt
   `https://www.nanotec.com/fileadmin/files/Baureihenuebersichten/Getriebe/Product_Overview_GPLE60.pdf` (Baureihenübersicht,
   Seiten 248/249), Produktseite `https://www.nanotec.com/us/en/products/901-gple60-2s-32`. Beide Dateien liegen unverändert
   in `C:\Users\User\.swki\kaufteile\quellen\nanotec\` (`gple60-2s-32.stp`, `Product_Overview_GPLE60.pdf`).
2. Herstellerdateien **nicht ins Git**. Der Eintrag nennt `original.bezug: {art: url, url, datum: "2026-10-06"}` und die
   SHA-256. Die Regression nimmt die Kopie aus dem Quellordner; fehlt sie, scheitert sie mit `KAUFTEIL_QUELLE_FEHLT`, und die
   Meldung nennt die Download-URL aus dem Eintrag.
3. Der GPLE60 ersetzt das Muster als Katalogeintrag (Task 7N) **und** in der Referenz Motorhalter (Task 10N). Muster-Specs,
   `gm42-10.step` und die Live-Tests aus Task 5 bleiben interne Testdaten (Ruling N1).
4. Gewinde-Gegenprobe: Modell `kernloch` gilt für jeden gemessenen Ø von D1 nach ISO 724 (D − 1,0825·P; M5: 4,134) bis zum
   Tabellen-Kernloch (`bohrungsnormen.yaml`, M5: 4,2), jeweils ± 0,01 mm; Nenn-Ø ± 0,01 bleibt `nenn`; sonst Mangel
   `gewinde:<gruppe>`. Der gemessene Ø je Gruppe kommt in den Cache-Eintrag und ins Bauprotokoll
   (`protokoll.kaufteile[...]`); die Gewindepaarung rechnet das Soll-Ringvolumen mit dem gemessenen Ø. Die alte Form (nur
   `"kernloch"`/`"nenn"`) muss nicht kompatibel bleiben (persistiert nur im Cache) → `IMPORTWEG_VERSION` erhöhen.

## Abweichungen vom Hauptplan

| Hauptplan | Neu (bindend für Tasks G, 7N, 10N, 11N) |
|---|---|
| Präz. 12 `IMPORTWEG_VERSION = 1` | **2** (Task G): Gewinde-Ø-Bereich und Gewindemodell mit gemessenem Ø; alte Cache-Einträge gelten als veraltet. Es gibt noch keinen echten Cache-Eintrag (nur Testordner), alte Form nirgends sonst persistiert. |
| Präz. 16 `gewinde_modell` `{gruppe: "kernloch" \| "nenn"}`; Ring mit Tabellen-Kernloch | `{gruppe: {"modell": "kernloch" \| "nenn", "durchmesser": <gemessener Ø, 4 Stellen>}}` in Aufnahme, Cache, `hole`-Rückgabe, Bauprotokoll; Ring mit dem gemessenen Ø; alte Form (Text) → „Gewindemodell unbekannt“ (`ok: null`). Modell und Ø müssen je Gruppe einheitlich sein, sonst Mangel `gewinde:<gruppe>` („Positionen uneinheitlich“). |
| Präz. 17 Muster-Getriebemotor als Katalogeintrag | Muster bleibt **nur interne Testdatei** (Spike S15, `tests/live/test_live_kaufteile.py`, `tests/kaufteile/beispiel.py`, `tests/baugruppe/beispiel_kaufteil.py`). Katalogeintrag: `swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml` (Task 7N). |
| Präz. 18 Motorhalter mit Muster (LK 60, Zentrierbohrung Ø 40 durch, Gewindetiefe 8) | Motorhalter mit GPLE60 (Task 10N): LK 52 unter 45°, Zentrierbohrung Ø 40 × 5 als Senkung einer Bohrung Ø 20 durch, Gewindetiefe/Bohrtiefe 10 (aus der STEP), Bock 55 mm weiter vorn auf der Platte (XG 10), Achshöhe 62, Hüllquader [160, 102, 100]. |
| Präz. 19 Negativfall M5 × 16 (11,4 > 8) | M5 × 16 bleibt: 11,4 > Gewindetiefe 10 = Bohrtiefe 10. Ø-Gegenprobe und Körperzahl weiter live am Muster (Task 5). |
| Präz. 20 Test-STEP im Git | gilt unverändert für `gm42-10.step` (interne Testdatei); **Herstellerdateien (STEP, Datenblatt) nie ins Git**. |
| Präz. 21 `bereite_vor` kopiert das Muster in den Quellordner | `bereite_vor` **prüft** nur: `quelle.original(...)` je Kaufteil der Referenz – fehlt die Herstellerdatei, `KAUFTEIL_QUELLE_FEHLT` mit URL (Test scheitert, kein Skip). |
| Präz. 22 Bericht `kaufteile` | zusätzlich Spalte „Gewindemodell (Ø mm)“ in `bericht.md`, z. B. `flansch: kernloch Ø 4.134`. |
| – (neu, Präz. 23) | Gewinde-Gegenprobe: `kernloch`, wenn D1 − 0,01 ≤ Ø ≤ Kernloch + 0,01. Steigung P: Feingewinde aus der Größe (`M10x1`), Regelgewinde aus der abgeglichenen Normtabelle ISO 4762 (Spalte `p`, ISO 261 – keine neue Tabelle, keine neue Spalte in `bohrungsnormen.yaml`, deren Werte live gemessen sein müssen). Ohne Steigung nur das Tabellen-Kernloch. |
| – (neu, Präz. 24) | `KAUFTEIL_QUELLE_FEHLT` nennt bei `original.bezug.art: url` die URL und das Datum (Meldung und `daten.url`) sowie den Befehl `swki kaufteil untersuchen <step> --hersteller <H> --bestellnummer <B>`. |
| – (neu, Präz. 25) | Gewindepaarung: Toleranz `max(1 % des Solls, 0,01 mm³)` (`TOL_GEWINDE_MIN_MM3`). Begründung unten bei Task G. |
| – (neu, Präz. 26) | `EINBAU_DREHLAGE` des GPLE60 ist die **Symmetrieebene des Lochbilds**, die durch die Achse und die Mitte einer Seite des □ 60 geht (`nahe` auf dem Lochkreis mittig zwischen Gewinde 1 und 2), nicht die Diagonale durch eine Gewindeposition. Begründung bei Task 7N; Rückfrage unten. |
| Abhängigkeit S15 Zeile 10 (Kernloch Ø 4,2 → kernloch, sonst nenn) | entfällt als Weiche: Bereich D1…Kernloch (Präz. 23). |
| Abhängigkeit S15 Zeile 7 (Normale `EINBAU_FLANSCH`) | gilt für den GPLE60 sinngemäß: erwartet `bezug.richtung` [0, 0, −1] (Task 7N Step 4); sonst Motorhalter `v4` auf `ausrichtung: gleich`. |
| Global Constraints, Git: „einzige Ausnahme Test-STEP“ | bleibt; zusätzlich: STEP und PDF von Herstellern nie `git add`. Die drei swki-Dateien neben dem Eintrag (`freigabe.json`, `*.freigegeben.yaml`, `*.pruefer.json`) werden committet. |

## Reihenfolge und Testzahlen

Neue Reihenfolge: **Task G → Task 7N → Task 10N → Task 11N.** Testzahlen (Unit-Suite `pytest -q`) sind in einer
Wegwerf-Kopie gemessen (siehe „Vorab geprüft“). `N9`/`D9` = Stand nach Task 9 einschließlich eventueller Fix-Runden aus dem
Task-9-Review (bei Planbeginn 923 / 138). Kommen dort Tests hinzu, gelten die Formeln.

| Task | Inhalt | passed | deselected | Formel |
|---|---|---|---|---|
| – | Stand nach Task 9 (HEAD `5ee0086`) | 923 | 138 | N9 / D9 |
| G | Gewinde-Ø-Bereich, Gewindemodell mit Ø, Untergrenze nenn, QUELLE_FEHLT mit URL, IMPORTWEG 2, Bericht, Spec | 930 | 138 | N9 + 7 / D9 |
| 7N | Eintrag GPLE60, Nutzerfreigabe, Prüfer, `hole` (live) | 931 | 139 | N9 + 8 / D9 + 1 |
| 10N | Referenz Motorhalter mit GPLE60 (live) | 932 | 141 | N9 + 9 / D9 + 3 |
| 11N | Doku, Regression, Abnahme | 932 | 141 | N9 + 9 / D9 + 3 |

Neue Tests: Task G +7 (`test_ortung` +2, `test_bewertung` +1, `test_befehle_kaufteile` +2, `test_kaufteil_bau_pruefen` +2;
ersetzt bzw. angepasst werden 1 Test in `test_ortung`, 1 Test und die Fixture `sw` in `test_befehle_kaufteile`,
3 Tests und `_messwerte` in `test_kaufteil_bau_pruefen` sowie eine Zeile im Live-Test aus Task 5), Task 7N +1 Unit
(`tests/kaufteile/test_eintrag_gple60.py`) +1 Live (`tests/live/test_live_kaufteil_hole.py`), Task 10N +1 Unit
(`tests/referenz/test_motorhalter.py`) +2 Live (Parameter `motorhalter-motorhalter.yaml` in `test_referenzen.py`,
`tests/live/test_live_motorhalter.py`).

## Vorab geprüft (2026-10-06, Wegwerf-Kopie im Scratchpad, nicht im Repo)

`git archive HEAD` (5ee0086) in einen Scratch-Ordner, `config/rechner.yaml` dazu, Projekt-`.venv`; dort die Blöcke dieses
Nachtrags mechanisch eingespielt (jede Ersetzung traf genau einmal):

- **Task G:** RED wie in Step 2 beschrieben (Sammelfehler `test_ortung.py`, sonst 7 failed / 50 passed), GREEN 67 passed,
  ganze Suite **930 passed, 138 deselected**, `swki api pruefe-code swki spikes tests/live` → `"befunde": []`. Die fünf
  Spec-Blöcke treffen genau einmal.
- **Task 7N:** Der Eintrag unten validiert `gueltig: true` mit genau dem einen Hinweis `nicht_belegt` / `gewinde.flansch`.
  Ortung offline gegen die Flächenlisten der Diagnose (unendliche Flächen aus `zylinder`/`ebenen`): alle vier Positionen
  `kernloch` Ø 4,134, `gewinde_modelle` → `{"flansch": {"modell": "kernloch", "durchmesser": 4.134}}`; jede `nahe`-Vorauswahl
  eindeutig (Zylinder Ø 14 / 40 / 17 / 60, Ebenen mit passender Normale), `EINBAU_DREHLAGE` Abstand zur Achse 26,0, Normale
  ±y. Freigabe und Urteil per Skript simuliert → `test_eintrag_gple60.py` grün (vorher rot), Suite 931/139 mit Live-Test.
- **Task 10N:** Grundplatte, Motorbock, Motorhalter `gueltig: true`, `hinweise: []`, Motorhalter 9 Komponenten /
  18 Verknüpfungen; `test_motorhalter.py` vorher `SpecFehler`, danach grün; Suite **932 passed, 141 deselected**;
  `pruefe-code` ohne Befund; Live-Tests sammeln sich (`-m sw --collect-only`).
- **Task 11N:** Die vier Spec-Blöcke treffen genau einmal.
- **Ungeprüft (braucht SolidWorks):** echte Abstände der `nahe`-Punkte zur begrenzten Fläche, Bezugsgeometrie, Massen-
  überschreibung mit 3 Körpern, Gewindeloch-Boden, Lage und Kollisionen im Motorhalter, Rauschvolumen der Interferenzprüfung.
  Dafür die Tabelle „Annahmen für die Live-Schritte“ am Ende.

## GPLE60: Diagnose ↔ Datenblatt (Rechnung, Grundlage für Task 7N und 10N)

STEP-Koordinaten (Diagnose lauf-1): Achse durch x = 30, y = 30, Richtung z. Box x 0…60, y 0…60, z −94,5…24. Drei
Volumenkörper (aus den Flächen gelesen: Motoradapter □ 60 z 0…24, Gehäuse Ø 60 z 0…−59,5, Abtriebswelle mit Zentrierbund,
Absatz, Welle und Passfeder), Check3 0, Flächenkörper 0, 55 Flächen (19 Ebenen, 24 Zylinderflächen, 12 sonstige),
Volumen 258960,557 mm³.

| Kennmaß | Datenblatt (Seite) | STEP (Diagnose) | Rechnung / Prüfung im Eintrag |
|---|---|---|---|
| Welle Ø 14h7 | 248 | Zylinder Ø 14, Fläche 1197,27 = π·14·30 − Passfeder-Fußfläche | `durchmesser_pruefen` soll 14, tol 0,018 (IT7 für 10–18 mm) |
| Zentrierbund Ø 40h7, Höhe 3 | 248 | Zylinder Ø 40 z −59,5…−62,5 (376,99 = π·40·3); Ebene z −62,5 Normale −z (1029,66 = π(20² − 8,5²)) | soll 40, tol 0,025 (IT7 für 30–50 mm); Maß Flansch → z −62,5 = 3 |
| Absatz Ø 17 | 248 | Zylinder Ø 17 z −62,5…−64,5 (106,81 = π·17·2) | soll 17 |
| Gehäuse Ø 60 | 248 | Zylinder Ø 60 z 0…−59,5 (11215,49 = π·60·59,5) | soll 60 |
| □ 60 | 248 | Box x, y 0…60 | Hüllquader 60 × 60 |
| L = 59,5 (2S) | 249 | Ebene z = 0 Normale −z (Adapter-Unterseite, 3575,17 = 3600 − 4 · 6,0 Eckabschnitt Ø 80 − π·0,5²) bis Flansch z −59,5 | Maß 59,5 |
| L1 = 24 (NEMA 23/24) | 249 | Adapter z 0…24 | Hüllquader z = 24 + 59,5 + 35 = 118,5 |
| Wellenlänge 35 ab Flansch, 30 Wellenteil | 248 | Wellenende z −94,5 (Ringfläche r 4,43…7), Absatz-Ende z −64,5 | Maß Flansch → Wellenende 35 |
| Passfeder 5 (Breite), 16 (über Passfeder), 25 lang, 2,5 vom Ende | 248 | Ebenen y 27,5 (Normale −y) und y 32,5 (+y), Rücken x = 21 (Normale −x), Rundungen Ø 5 bei z −69,5 und −89,5 → Länge 25, Ende 2,5 vor −94,5 | Breite 5; Rücken–Wellenachse 30 − 21 = 9 = 16 − 14/2 |
| 4-M5 auf 52 | 248 | 4 Zylinder Ø 4,134 bei (30 ± 18,3848 \| 30 ± 18,3848), Fläche je 129,87 = π·4,134·10,00 → Mantel 10 lang, Mitte z −54,5 → z −59,5…−49,5; keine ebene Fläche bei z −49,5 (19 von 19 Ebenen gelistet) → Boden ist eine Spitze (Annahme, Task 7N Step 1) | Lochkreis 2·18,3848·√2 = 52,000; benachbart 52·sin 45° = 36,7696 ≈ 36,77; Gewindetiefe = Bohrtiefe = 10 (nicht belegt) |
| Masse 1,1 kg (2S) | 249 | Volumen 258960,557 mm³ (als Stahl 2,03 kg) | `masse: {kg: 1.1}` überschreibt |
| Werkstoff | – (nicht genannt) | – | `material: "1.0503"` (Annahme, siehe Task 7N) |

---

### Task G: Gewinde-Ø-Bereich, Gewindemodell mit gemessenem Ø, Untergrenze nenn, Quelle mit URL (ohne SolidWorks)

**Files:**
- Modify: `swki/kaufteile/ortung.py`, `swki/kaufteile/bewertung.py`, `swki/kaufteile/aufnahme.py`, `swki/kaufteile/cache.py`,
  `swki/kaufteile/quelle.py`, `swki/baugruppe/bewertung.py`, `swki/pruefung/bericht.py`,
  `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md`
- Test: `tests/kaufteile/test_ortung.py`, `tests/kaufteile/test_bewertung.py`, `tests/kaufteile/test_befehle_kaufteile.py`,
  `tests/baugruppe/test_kaufteil_bau_pruefen.py`, `tests/live/test_live_kaufteile.py` (eine Zeile, live)

**Interfaces:**
- Consumes: Task 4 (`ortung`, `bewertung`), Task 5 (`aufnahme.baue_und_pruefe`), Task 6 (`cache`, `quelle`, `befehle.hole`),
  Task 9 (`baugruppe.bewertung._gewinde_soll`, `BaugruppenMesswerte.gewinde_modelle`, `bericht` Abschnitt „Kaufteile“).
- Produces: `ortung.ISO724_FAKTOR`, `ortung.steigung(groesse)`, `ortung.kernloch_bereich(groesse) -> (unten, oben)`,
  `ortung.gewinde_modelle(gewinde) -> {gruppe: {"modell", "durchmesser"}}`; `cache.IMPORTWEG_VERSION = 2`;
  `baugruppe.bewertung.TOL_GEWINDE_MIN_MM3 = 0.01`; `KaufteilFehler(KAUFTEIL_QUELLE_FEHLT).daten["url"]`.

**Gegen den tatsächlichen Stand prüfen (Implementer):** Die Blöcke in `swki/baugruppe/bewertung.py`,
`swki/pruefung/bericht.py` und `tests/baugruppe/test_kaufteil_bau_pruefen.py` sind gegen den Commit `5ee0086` (Task 9)
geschrieben. Hat eine Fix-Runde aus dem Task-9-Review diese Stellen geändert und trifft ein Block nicht genau einmal:
anhalten und dem Controller melden (nicht raten). Alle anderen Blöcke stammen aus Code, den Task 9 nicht berührt.

**Untergrenze `TOL_GEWINDE_MIN_MM3 = 0,01 mm³` (Präz. 25):** Bei Modell `nenn` ist das Soll 0, die relative Toleranz 1 %
also 0 – jede Zahl > 0 aus `GetInterferences` (Rechenrauschen an berührenden Zylinderflächen) wäre ein Mangel. 0,01 mm³
entspricht einem Span 0,1 × 0,1 × 1 mm und liegt weit unter jeder echten Überlappung, die die Prüfung finden soll: 0,05 mm
radiale Überdeckung einer M5 über 7,4 mm Einschraublänge ergibt ≈ π·5·0,05·7,4 ≈ 5,8 mm³, 0,1 mm zu tief eingeschraubt
≈ π·2,5²·0,1 ≈ 2 mm³. Beim Modell `kernloch` (Soll ≥ 20 mm³ ab 2 mm Einschraublänge M5) bleibt 1 % maßgeblich (≥ 0,2 mm³),
die Untergrenze greift dort praktisch nie; für Eigenteile ändert sich nichts. Weicht das Rauschen live darüber ab (Task 10N
Step 5 meldet `gewinde:*` mit `ist` > 0 bei `nenn`), NEEDS_CONTEXT – nicht still erhöhen.

- [ ] **Step 1: Tests schreiben**

In `tests/kaufteile/test_ortung.py` ersetzen:

```python
from swki.kaufteile.ortung import (ebene_durch_achse, kandidaten, nenn_durchmesser, orte_ebene, orte_gewinde,
                                   orte_zylinder)
```

durch:

```python
from swki.kaufteile.ortung import (ebene_durch_achse, gewinde_modelle, kandidaten, kernloch_bereich, nenn_durchmesser,
                                   orte_ebene, orte_gewinde, orte_zylinder, steigung)
```

In `tests/kaufteile/test_ortung.py` ersetzen:

```python
def test_gewinde_kernloch_nenn_und_falsch():
    w = {"groesse": "M5", "normale": [0, -1, 0], "positionen": [[21, 0, 21], [-21, 0, 21], [0, 0, 30]]}
    flaechen = [_zyl((21, 3, 21), Y, 2.1), _zyl((21, 3, 21), Y, 5.0), _zyl((-21, 5, 21), (0, -1, 0), 2.5),
                _zyl((0, 0, 30), Y, 3.0)]
    a, b, c = orte_gewinde(flaechen, "flansch", w, 0.1)
    assert (a.name, a.ist["modell"], a.abweichung) == ("flansch.1", "kernloch", None)
    assert b.ist["modell"] == "nenn" and c.ist["modell"] is None
    assert c.abweichung == "Ø 6.0000: weder Kernloch 4.2 noch Nenn-Ø 5 (M5)"
    with pytest.raises(AnkerFehler):
        orte_gewinde(flaechen, "flansch", {**w, "positionen": [[50, 0, 0]]}, 0.1)
    assert nenn_durchmesser("M10x1") == 10.0
```

durch:

```python
def test_gewinde_kernloch_bereich_nenn_und_falsch():
    """M5: Kernloch gilt von D1 nach ISO 724 (4,134) bis zum Bohrer der Tabelle (4,2), je ± 0,01 (Spec 3c §4.3)."""
    durchmesser = [4.134, 4.16, 4.2, 5.0, 4.12, 6.0]
    w = {"groesse": "M5", "normale": [0, -1, 0], "positionen": [[10 * i, 0, 0] for i in range(len(durchmesser))]}
    flaechen = [_zyl((10 * i, 3, 0), Y, d / 2) for i, d in enumerate(durchmesser)] + [_zyl((0, 3, 0), Y, 5.0)]
    ergebnis = orte_gewinde(flaechen, "flansch", w, 0.1)
    assert [o.ist["modell"] for o in ergebnis] == ["kernloch", "kernloch", "kernloch", "nenn", None, None]
    assert [o.ist["durchmesser"] for o in ergebnis] == durchmesser
    assert (ergebnis[0].name, ergebnis[0].abweichung) == ("flansch.1", None)
    assert ergebnis[4].abweichung == "Ø 4.1200: weder Kernloch 4.134…4.2 noch Nenn-Ø 5 (M5)"
    with pytest.raises(AnkerFehler):
        orte_gewinde(flaechen, "flansch", {**w, "positionen": [[55, 0, 0]]}, 0.1)
    assert nenn_durchmesser("M10x1") == 10.0


def test_kernloch_bereich_und_steigung():
    assert [steigung(g) for g in ("M5", "M6", "M10x1", "M12x1.5", "M3")] == [0.8, 1.0, 1.0, 1.5, None]
    assert kernloch_bereich("M5") == (4.134, 4.2) and kernloch_bereich("M6") == (4.9175, 5.0)
    assert kernloch_bereich("M8x1") == (6.9175, 7.0) and kernloch_bereich("M16") == (13.835, 14.0)


def test_gewinde_modelle_je_gruppe():
    def m(d, modell="kernloch"):
        return {"ist": {"durchmesser": d, "modell": modell}, "abweichung": None}

    gemessen = {"flansch.1": m(4.134), "flansch.2": m(4.13398), "fuss.1": m(5.0, "nenn"), "deckel.1": m(4.134),
                "deckel.2": m(4.2), "seite.1": m(4.2), "seite.2": "REFERENZ_NICHT_GEFUNDEN: keine Zylinderfläche"}
    assert gewinde_modelle(gemessen) == {"flansch": {"modell": "kernloch", "durchmesser": 4.134},
                                         "fuss": {"modell": "nenn", "durchmesser": 5.0}}
```

Werte: D1(M5) = 5 − 1,0825·0,8 = 4,134; D1(M6) = 6 − 1,0825 = 4,9175; D1(M8x1) = 6,9175; D1(M16) = 16 − 2,165 = 13,835.
4,12 < 4,134 − 0,01 = 4,124 → kein Modell; 4,16 liegt im Bereich; 5,0 ist der Nenn-Ø. Die Zusatzfläche Ø 10 auf der Achse
der Position 1 (Senkung) verliert gegen den kleineren Radius. Gruppe `deckel` (4,134 und 4,2, Spanne 0,066 > 0,01) und
`seite` (eine Position nicht geortet) liefern kein Modell.

In `tests/kaufteile/test_bewertung.py` ersetzen:

```python
    m.eigenschaften = {**m.eigenschaften, "Hersteller": "anders"}
    assert {"mass:Wellenüberstand", "eigenschaften"} <= set(_ids(bewerte_kaufteil(EINTRAG, m), False))
```

durch:

```python
    m.eigenschaften = {**m.eigenschaften, "Hersteller": "anders"}
    assert {"mass:Wellenüberstand", "eigenschaften"} <= set(_ids(bewerte_kaufteil(EINTRAG, m), False))


def test_gewinde_modell_und_uneinheitlich():
    gewinde = next(e for e in bewerte_kaufteil(EINTRAG, _messwerte())["pruefungen"] if e["id"] == "gewinde:flansch")
    assert gewinde["ok"] is True and (gewinde["modell"], gewinde["durchmesser"]) == ("kernloch", 4.2)
    m = _messwerte()
    m.gewinde["flansch.2"] = {"ist": {"durchmesser": 4.134, "modell": "kernloch"}, "abweichung": None}
    mangel = next(x for x in bewerte_kaufteil(EINTRAG, m)["maengel"] if x["pruefung"] == "gewinde:flansch")
    assert "Positionen uneinheitlich" in mangel["beschreibung"]
```

In `tests/kaufteile/test_befehle_kaufteile.py` ersetzen:

```python
SCHLUESSEL = "SWKI-MUSTER GM42-10"
```

durch:

```python
SCHLUESSEL = "SWKI-MUSTER GM42-10"
MODELL = {"flansch": {"modell": "kernloch", "durchmesser": 4.2}}
```

In `tests/kaufteile/test_befehle_kaufteile.py` ersetzen:

```python
                "gewinde_modell": {"flansch": "kernloch"}, "kennzahlen": {"flaechen": 40}}
```

durch:

```python
                "gewinde_modell": MODELL, "kennzahlen": {"flaechen": 40}}
```

In `tests/kaufteile/test_befehle_kaufteile.py` ersetzen:

```python
    assert erst["gebaut"] is True and Path(erst["pfad"]) == ziel and erst["gewinde_modell"] == {"flansch": "kernloch"}
    eintrag = json.loads(ziel.with_suffix(".json").read_text(encoding="utf-8"))
    assert eintrag["sldprt_sha256"] == sha256_datei(ziel) and eintrag["pruefsumme"] == erst["pruefsumme"]
    zweit = befehle.hole(SCHLUESSEL, katalog)
    assert zweit["gebaut"] is False and zweit["gewinde_modell"] == {"flansch": "kernloch"}
```

durch:

```python
    assert erst["gebaut"] is True and Path(erst["pfad"]) == ziel and erst["gewinde_modell"] == MODELL
    eintrag = json.loads(ziel.with_suffix(".json").read_text(encoding="utf-8"))
    assert eintrag["sldprt_sha256"] == sha256_datei(ziel) and eintrag["pruefsumme"] == erst["pruefsumme"]
    assert eintrag["gewinde_modell"] == MODELL
    zweit = befehle.hole(SCHLUESSEL, katalog)
    assert zweit["gebaut"] is False and zweit["gewinde_modell"] == MODELL
```

In `tests/kaufteile/test_befehle_kaufteile.py` ersetzen:

```python
    capsys.readouterr()
    assert main(["kaufteil", "liste"]) == 0 and json.loads(capsys.readouterr().out)["teile"][0]["cache"] is False
```

durch:

```python
    capsys.readouterr()
    assert main(["kaufteil", "liste"]) == 0 and json.loads(capsys.readouterr().out)["teile"][0]["cache"] is False


def test_quelle_fehlt_nennt_download_url(umgebung, sw, tmp_path):
    _, katalog, step, _ = umgebung
    spec = kopie()
    url = "https://example.com/cad/gm42-10.step"
    spec["original"] = {"datei": "gm42-10.step", "sha256": sha256_datei(step),
                        "bezug": {"art": "url", "url": url, "datum": "2026-10-06"}}
    pfad = schreibe(katalog, spec)
    main(["freigeben", str(pfad)])
    _urteil(pfad, tmp_path, katalog)
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_QUELLE_FEHLT" and e.value.daten["url"] == url
    assert f"Download: {url} (Stand 2026-10-06)" in str(e.value) and "--bestellnummer GM42-10" in str(e.value)
    assert sw == []


def test_importweg_version_2():
    """Gewinde-Ø-Bereich und gemessener Ø im Gewindemodell (2026-10-06) ändern den Importweg: alter Cache veraltet."""
    assert cache.IMPORTWEG_VERSION == 2
```

In `tests/baugruppe/test_kaufteil_bau_pruefen.py` ersetzen:

```python
Y = (0.0, 1.0, 0.0)
```

durch:

```python
Y = (0.0, 1.0, 0.0)
KERN = {"modell": "kernloch", "durchmesser": 4.2}
NENN = {"modell": "nenn", "durchmesser": 5.0}
```

In `tests/baugruppe/test_kaufteil_bau_pruefen.py` ersetzen:

```python
        return {"pfad": str(cache), "gebaut": False, "pruefsumme": "abc", "gewinde_modell": {"flansch": "kernloch"}}
```

durch:

```python
        return {"pfad": str(cache), "gebaut": False, "pruefsumme": "abc", "gewinde_modell": {"flansch": KERN}}
```

In `tests/baugruppe/test_kaufteil_bau_pruefen.py` ersetzen:

```python
        "gewinde_modell": {"flansch": "kernloch"}, "masse": "1.2 kg (Datenblatt)", "kennmasse": "belegt"}
```

durch:

```python
        "gewinde_modell": {"flansch": KERN}, "masse": "1.2 kg (Datenblatt)", "kennmasse": "belegt"}
```

In `tests/baugruppe/test_kaufteil_bau_pruefen.py` ersetzen:

```python
def _messwerte(bg, laenge_im_gewinde: float, volumen: float, modell: str | None = "kernloch") -> BaugruppenMesswerte:
```

durch:

```python
def _messwerte(bg, laenge_im_gewinde: float, volumen: float, modell: dict | str | None = KERN) -> BaugruppenMesswerte:
```

In `tests/baugruppe/test_kaufteil_bau_pruefen.py` ersetzen:

```python
    nenn = _gewinde(bg, _messwerte(bg, 7.4, 0.0, "nenn"))
    assert nenn["ok"] is True and nenn["soll"] == 0.0
    assert _gewinde(bg, _messwerte(bg, 7.4, 3.0, "nenn"))["ok"] is False
    unbekannt = _gewinde(bg, _messwerte(bg, 7.4, soll, None))
    assert unbekannt["ok"] is None and "Gewindemodell" in unbekannt["hinweis"]
```

durch:

```python
    nenn = _gewinde(bg, _messwerte(bg, 7.4, 0.0, NENN))
    assert nenn["ok"] is True and nenn["soll"] == 0.0
    assert _gewinde(bg, _messwerte(bg, 7.4, 3.0, NENN))["ok"] is False
    unbekannt = _gewinde(bg, _messwerte(bg, 7.4, soll, None))
    assert unbekannt["ok"] is None and "Gewindemodell" in unbekannt["hinweis"]


def test_gewindepaarung_mit_gemessenem_kernloch(tmp_path, monkeypatch):
    """Spec 3c §6.4 (Nutzerentscheidung 2026-10-06): Ring Nenn-Ø/gemessener Ø – D1 4,134 statt Tabellen-Kernloch 4,2."""
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    d1 = {"modell": "kernloch", "durchmesser": 4.134}
    soll = ueberlappung_soll(5, 0.8, 4.134, 7.4)
    ok = _gewinde(bg, _messwerte(bg, 7.4, soll, d1))
    assert ok["ok"] is True and ok["soll"] == round(soll, 3) == 42.305
    assert _gewinde(bg, _messwerte(bg, 7.4, ueberlappung_soll(5, 0.8, 4.2, 7.4), d1))["ok"] is False
    alt = _gewinde(bg, _messwerte(bg, 7.4, soll, "kernloch"))  # alte Form (nur Text) gilt als unbekannt
    assert alt["ok"] is None and "Gewindemodell" in alt["hinweis"]


def test_gewindepaarung_nenn_mit_untergrenze(tmp_path, monkeypatch):
    """Modell nenn (Soll 0): Rechenrauschen bis TOL_GEWINDE_MIN_MM3 (0,01 mm³) ist kein Mangel, mehr schon."""
    katalog(tmp_path / "kat", monkeypatch)
    bg = lade_baugruppe(schreibe(tmp_path / "A", _ins_gewinde(kopie())))
    assert _gewinde(bg, _messwerte(bg, 7.4, 0.004, NENN))["ok"] is True
    assert _gewinde(bg, _messwerte(bg, 7.4, 0.02, NENN))["ok"] is False
```

Werte: Soll-Ring M5 × 7,4 mm Einschraublänge mit D1 4,134: 42,305 mm³, mit dem Tabellen-Kernloch 4,2: 39,274 mm³
(Abweichung 7,2 % > 1 %, also Mangel – der Test zeigt, dass der gemessene Ø zählt).

In `tests/baugruppe/test_kaufteil_bau_pruefen.py` ersetzen:

```python
        "kaufteil": "SWKI-MUSTER GM42-10", "gebaut": True, "pruefsumme": "abc", "masse": "1.2 kg (Datenblatt)",
        "kennmasse": "nicht belegt"}}}
    text = bericht_markdown({"name": "Motorprobe"}, "A", [], ("WEITER", "x"), pruefbericht, None, None, [])
    assert "| SWKI-MUSTER GM42-10 | ja | abc | 1.2 kg (Datenblatt) | nicht belegt |" in text
```

durch:

```python
        "kaufteil": "SWKI-MUSTER GM42-10", "gebaut": True, "pruefsumme": "abc", "masse": "1.2 kg (Datenblatt)",
        "kennmasse": "nicht belegt", "gewinde_modell": {"flansch": {"modell": "kernloch", "durchmesser": 4.134}}}}}
    text = bericht_markdown({"name": "Motorprobe"}, "A", [], ("WEITER", "x"), pruefbericht, None, None, [])
    assert "| SWKI-MUSTER GM42-10 | ja | abc | 1.2 kg (Datenblatt) | nicht belegt | flansch: kernloch Ø 4.134 |" in text
```

In `tests/live/test_live_kaufteile.py` ersetzen (Live-Test aus Task 5, Muster mit Kernloch 4,2):

```python
    assert e["gewinde_modell"] == {"flansch": "kernloch"} and Path(e["teil"]).is_file()
```

durch:

```python
    assert e["gewinde_modell"] == {"flansch": {"modell": "kernloch", "durchmesser": 4.2}} and Path(e["teil"]).is_file()
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile tests\baugruppe\test_kaufteil_bau_pruefen.py`
Expected: FAIL – `Interrupted: 1 error during collection` (`ImportError: cannot import name 'gewinde_modelle' from
'swki.kaufteile.ortung'`).
Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile tests\baugruppe\test_kaufteil_bau_pruefen.py --ignore tests\kaufteile\test_ortung.py`
Expected: `7 failed, 50 passed` (`test_quelle_fehlt_nennt_download_url`, `test_importweg_version_2`,
`test_gewinde_modell_und_uneinheitlich`, `test_gewindepaarung_im_kaufteil`, `test_gewindepaarung_mit_gemessenem_kernloch`,
`test_gewindepaarung_nenn_mit_untergrenze`, `test_bericht_nennt_kaufteile`).

- [ ] **Step 3: Umsetzen**

In `swki/kaufteile/ortung.py` ersetzen:

```python
import math
from dataclasses import dataclass, field
```

durch:

```python
import math
import re
from dataclasses import dataclass, field
```

In `swki/kaufteile/ortung.py` ersetzen:

```python
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN
from swki.spec.normen import normmasse
```

durch:

```python
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN
from swki.normteile.tabelle import lade_normtabelle
from swki.spec.normen import normmasse
```

In `swki/kaufteile/ortung.py` ersetzen:

```python
_GLEICH_MM = 1e-4
```

durch:

```python
_GLEICH_MM = 1e-4
ISO724_FAKTOR = 1.0825   # Kerndurchmesser des Muttergewindes D1 = D − 1,0825·P (ISO 724)
```

In `swki/kaufteile/ortung.py` ersetzen:

```python
def orte_gewinde(flaechen: list[Flaeche], gruppe: str, w: dict, tol_mm: float) -> list[Ortung]:
    """Je Position die Zylinderfläche, deren Achse durch den Eintrittspunkt läuft und parallel zu `normale` ist
    (der kleinste Radius gewinnt, wie bei Bohrungen mit Senkung); Gegenprobe Ø = Kernloch (modell kernloch) oder
    Nenn-Ø (modell nenn)."""
    n = einheit(tuple(w["normale"]))
    kern = normmasse("gewinde", w["groesse"], "ISO")["kernloch"]
    nenn = nenn_durchmesser(w["groesse"])
```

durch:

```python
def steigung(groesse: str) -> float | None:
    """Steigung P (mm): Feingewinde aus der Größe ("M10x1" → 1.0), Regelgewinde aus der abgeglichenen Normtabelle
    ISO 4762 (Spalte p, ISO 261); None, wenn die Größe dort fehlt."""
    treffer = re.fullmatch(r"M\d+(?:\.\d+)?[xX](\d+(?:\.\d+)?)", groesse)
    if treffer:
        return float(treffer.group(1))
    zeile = lade_normtabelle("ISO 4762").get("groessen", {}).get(groesse)
    return float(zeile["masse"]["p"]) if zeile else None


def kernloch_bereich(groesse: str) -> tuple[float, float]:
    """(kleinster, größter) Ø, der als Kernloch gilt (Spec 3c §4.3, Nutzerentscheidung 2026-10-06): von D1 nach ISO 724
    bis zum Kernloch der Tabelle (Bohrer-Ø, bohrungsnormen.yaml); ohne bekannte Steigung nur das Tabellen-Kernloch."""
    kern = normmasse("gewinde", groesse, "ISO")["kernloch"]
    p = steigung(groesse)
    if p is None:
        return kern, kern
    d1 = round(nenn_durchmesser(groesse) - ISO724_FAKTOR * p, 4)
    return min(d1, kern), max(d1, kern)


def orte_gewinde(flaechen: list[Flaeche], gruppe: str, w: dict, tol_mm: float) -> list[Ortung]:
    """Je Position die Zylinderfläche, deren Achse durch den Eintrittspunkt läuft und parallel zu `normale` ist
    (der kleinste Radius gewinnt, wie bei Bohrungen mit Senkung); Gegenprobe Ø: von D1 bis zum Tabellen-Kernloch
    (modell kernloch) oder Nenn-Ø (modell nenn), je ± TOL_DURCHMESSER; der gemessene Ø steht in ist.durchmesser."""
    n = einheit(tuple(w["normale"]))
    unten, oben = kernloch_bereich(w["groesse"])
    nenn = nenn_durchmesser(w["groesse"])
```

In `swki/kaufteile/ortung.py` ersetzen:

```python
        modell = "kernloch" if abs(d - kern) <= TOL_DURCHMESSER else "nenn" if abs(d - nenn) <= TOL_DURCHMESSER else None
        abweichung = None if modell else f"Ø {d:.4f}: weder Kernloch {kern:g} noch Nenn-Ø {nenn:g} ({w['groesse']})"
        ergebnis.append(Ortung(name, "gewinde", f, {"durchmesser": round(d, 6), "modell": modell,
                                                    "achse": einheit(f.achse), "punkt": f.punkt}, abweichung))
    return ergebnis
```

durch:

```python
        modell = ("kernloch" if unten - TOL_DURCHMESSER <= d <= oben + TOL_DURCHMESSER
                  else "nenn" if abs(d - nenn) <= TOL_DURCHMESSER else None)
        abweichung = None if modell else (f"Ø {d:.4f}: weder Kernloch {unten:g}…{oben:g} noch Nenn-Ø {nenn:g} "
                                          f"({w['groesse']})")
        ergebnis.append(Ortung(name, "gewinde", f, {"durchmesser": round(d, 6), "modell": modell,
                                                    "achse": einheit(f.achse), "punkt": f.punkt}, abweichung))
    return ergebnis


def gewinde_modelle(gewinde: dict) -> dict[str, dict]:
    """Gewindemodell je Gruppe aus den Messungen der Positionen ("<gruppe>.<i>" → {"ist", "abweichung"} oder
    Fehlertext): {gruppe: {"modell": "kernloch" | "nenn", "durchmesser": gemessener Ø in mm}} – nur Gruppen, deren
    Positionen alle geortet sind und dasselbe Modell mit Ø innerhalb TOL_DURCHMESSER haben (Spec 3c §4.3, §5.3)."""
    gruppen: dict[str, list] = {}
    for name, messung in gewinde.items():
        gruppen.setdefault(name.rsplit(".", 1)[0], []).append(messung)
    ergebnis = {}
    for gruppe, messungen in gruppen.items():
        ist = [m["ist"] for m in messungen if isinstance(m, dict)]
        if len(ist) < len(messungen):
            continue
        durchmesser = [i["durchmesser"] for i in ist]
        if (len({i.get("modell") for i in ist}) != 1 or ist[0].get("modell") is None
                or max(durchmesser) - min(durchmesser) > TOL_DURCHMESSER):
            continue
        ergebnis[gruppe] = {"modell": ist[0]["modell"], "durchmesser": round(durchmesser[0], 4)}
    return ergebnis
```

In `swki/kaufteile/bewertung.py` ersetzen:

```python
from swki.kaufteile.ortung import TOL_WINKEL_GRAD, winkel_grad
```

durch:

```python
from swki.kaufteile.ortung import TOL_WINKEL_GRAD, gewinde_modelle, winkel_grad
```

In `swki/kaufteile/bewertung.py` ersetzen:

```python
def _gewinde(gruppe: str, w: dict, m: KaufteilMesswerte) -> dict:
    ist, fehler = {}, []
    for i in range(1, len(w["positionen"]) + 1):
        messung = m.gewinde.get(f"{gruppe}.{i}", "Position nicht geortet")
        if isinstance(messung, str):
            fehler.append(f"{i}: {messung}")
            continue
        ist[str(i)] = {k: v for k, v in messung["ist"].items() if k in ("durchmesser", "modell")}
        if messung.get("abweichung"):
            fehler.append(f"{i}: {messung['abweichung']}")
    daten = {"ist": ist, "beleg": _beleg(w)}
```

durch:

```python
def _gewinde(gruppe: str, w: dict, m: KaufteilMesswerte) -> dict:
    """Gegenprobe je Position; das Modell (kernloch | nenn) und der gemessene Ø müssen in der Gruppe einheitlich sein
    (Spec 3c §4.3) – sie gehen als ein Wert je Gruppe in Cache und Gewindepaarung."""
    ist, fehler = {}, []
    namen = [f"{gruppe}.{i}" for i in range(1, len(w["positionen"]) + 1)]
    for i, name in enumerate(namen, start=1):
        messung = m.gewinde.get(name, "Position nicht geortet")
        if isinstance(messung, str):
            fehler.append(f"{i}: {messung}")
            continue
        ist[str(i)] = {k: v for k, v in messung["ist"].items() if k in ("durchmesser", "modell")}
        if messung.get("abweichung"):
            fehler.append(f"{i}: {messung['abweichung']}")
    modell = gewinde_modelle({n: m.gewinde.get(n, "") for n in namen}).get(gruppe)
    if not fehler and modell is None:
        fehler.append("Positionen uneinheitlich (Modell oder Ø): " +
                      ", ".join(f"{i}: {v['modell']} Ø {v['durchmesser']:g}" for i, v in ist.items()))
    daten = {"ist": ist, **(modell or {}), "beleg": _beleg(w)}
```

In `swki/kaufteile/aufnahme.py` ersetzen:

```python
from swki.kaufteile.katalog import bibliotheksschluessel
```

durch:

```python
from swki.kaufteile.katalog import bibliotheksschluessel
from swki.kaufteile.ortung import gewinde_modelle
```

In `swki/kaufteile/aufnahme.py` ersetzen:

```python
    modelle = {}
    for name, g in gewinde.items():
        if isinstance(g, dict) and g["ist"].get("modell"):
            modelle.setdefault(name.rsplit(".", 1)[0], g["ist"]["modell"])
    return {**bericht, "teil": str(teil), "bilder": bilder, "fehler": None, "gewinde_modell": modelle,
            "kennzahlen": kennzahlen}
```

durch:

```python
    return {**bericht, "teil": str(teil), "bilder": bilder, "fehler": None, "gewinde_modell": gewinde_modelle(gewinde),
            "kennzahlen": kennzahlen}
```

(`befehle.hole` reicht `ergebnis["gewinde_modell"]` unverändert in Cache-Eintrag und Rückgabe, `baugruppe.bau._hole_kaufteile`
ins Bauprotokoll, `baugruppe.pruefen` in `BaugruppenMesswerte.gewinde_modelle` – dort ist kein Code zu ändern.)

In `swki/kaufteile/cache.py` ersetzen:

```python
IMPORTWEG_VERSION = 1  # bei jeder Änderung an Import, Ortung oder Bezugsgeometrie erhöhen (Spec 3c §5.3)
```

durch:

```python
IMPORTWEG_VERSION = 2  # bei jeder Änderung an Import, Ortung oder Bezugsgeometrie erhöhen (Spec 3c §5.3);
#                        2: Gewinde-Ø-Bereich D1…Kernloch, Gewindemodell mit gemessenem Ø (2026-10-06)
```

In `swki/kaufteile/quelle.py` ersetzen:

```python
    if not pfad.is_file():
        raise KaufteilFehler(KAUFTEIL_QUELLE_FEHLT, f"{pfad} fehlt – Nutzer gibt die Datei erneut: swki kaufteil "
                                                    "untersuchen <step> --hersteller … --bestellnummer …", pfad=str(pfad))
```

durch:

```python
    if not pfad.is_file():
        bezug = spec["original"]["bezug"]
        woher = (f"Download: {bezug['url']} (Stand {bezug['datum']}), dann" if bezug.get("url")
                 else "Nutzer gibt die Datei erneut:")
        raise KaufteilFehler(KAUFTEIL_QUELLE_FEHLT,
                             f"{pfad} fehlt – {woher} swki kaufteil untersuchen <step> --hersteller "
                             f"{spec['hersteller']} --bestellnummer {spec['bestellnummer']} (SHA-256 muss passen)",
                             pfad=str(pfad), **({"url": bezug["url"]} if bezug.get("url") else {}))
```

In `swki/baugruppe/bewertung.py` ersetzen (Stand `5ee0086` prüfen):

```python
TOL_GEWINDE_PROZENT = 1.0  # Spike S12 Zeile 9
```

durch:

```python
TOL_GEWINDE_PROZENT = 1.0  # Spike S12 Zeile 9
TOL_GEWINDE_MIN_MM3 = 0.01  # absolute Untergrenze (Soll 0 bei Modell nenn): Rechenrauschen, keine echte Überlappung
```

In `swki/baugruppe/bewertung.py` ersetzen (Stand `5ee0086` prüfen):

```python
    gewinde_modelle: dict[str, dict] = field(default_factory=dict)    # Kaufteil-Schlüssel → {Gruppe: kernloch | nenn}
```

durch:

```python
    gewinde_modelle: dict[str, dict] = field(default_factory=dict)    # Kaufteil-Schlüssel → {Gruppe: {modell, durchmesser}}
```

In `swki/baugruppe/bewertung.py` ersetzen (Stand `5ee0086` prüfen):

```python
    """(tiefe, gewindetiefe, Soll des Überlappungsvolumens, Hinweis): Eigenteil aus der normbohrung, Kaufteil aus der
    Gewindegruppe des Eintrags mit dem Modell aus der Aufnahme (Spec 3c §6.4: kernloch → Ring, nenn → 0)."""
    if qt.art == "kaufteil":
        w = qt.spec["gewinde"][g.feature]
        modell = m.gewinde_modelle.get(qt.schluessel, {}).get(g.feature)
        if modell == "nenn":
            return w["tiefe"], w["gewindetiefe"], 0.0, None
        if modell != "kernloch":
            return w["tiefe"], w["gewindetiefe"], None, f"Gewindemodell von {qt.kaufteil}.{g.feature} unbekannt"
        kernloch = normmasse("gewinde", w["groesse"], "ISO")["kernloch"]
        return w["tiefe"], w["gewindetiefe"], ueberlappung_soll(qs.masse["d"], qs.masse["p"], kernloch, laenge), None
```

durch:

```python
    """(tiefe, gewindetiefe, Soll des Überlappungsvolumens, Hinweis): Eigenteil aus der normbohrung, Kaufteil aus der
    Gewindegruppe des Eintrags mit dem Modell aus der Aufnahme (Spec 3c §6.4: kernloch → Ring bis zum gemessenen Ø,
    nenn → 0); die alte Form (nur Text) gilt als unbekannt."""
    if qt.art == "kaufteil":
        w = qt.spec["gewinde"][g.feature]
        modell = m.gewinde_modelle.get(qt.schluessel, {}).get(g.feature)
        art = modell.get("modell") if isinstance(modell, dict) else None
        if art == "nenn":
            return w["tiefe"], w["gewindetiefe"], 0.0, None
        if art != "kernloch" or not modell.get("durchmesser"):
            return w["tiefe"], w["gewindetiefe"], None, f"Gewindemodell von {qt.kaufteil}.{g.feature} unbekannt"
        return (w["tiefe"], w["gewindetiefe"],
                ueberlappung_soll(qs.masse["d"], qs.masse["p"], modell["durchmesser"], laenge), None)
```

In `swki/baugruppe/bewertung.py` ersetzen (Stand `5ee0086` prüfen):

```python
    ok = None if soll is None else abs(ist - soll) <= soll * TOL_GEWINDE_PROZENT / 100
```

durch:

```python
    ok = None if soll is None else abs(ist - soll) <= max(soll * TOL_GEWINDE_PROZENT / 100, TOL_GEWINDE_MIN_MM3)
```

In `swki/pruefung/bericht.py` ersetzen:

```python
def _zelle(wert) -> str:
    return "–" if wert is None else str(wert)
```

durch:

```python
def _zelle(wert) -> str:
    return "–" if wert is None else str(wert)


def _gewindemodelle(werte: dict | None) -> str:
    """„flansch: kernloch Ø 4.134“ je Gruppe (Spec 3c §4.3); ohne Gewindegruppen „–“."""
    teile = [f"{g}: {m['modell']} Ø {m['durchmesser']:g}" if isinstance(m, dict) and m.get("durchmesser") is not None
             else f"{g}: unbekannt" for g, m in sorted((werte or {}).items())]
    return ", ".join(teile) or "–"
```

In `swki/pruefung/bericht.py` ersetzen (Stand `5ee0086` prüfen):

```python
        zeilen += ["", "## Kaufteile", "", "| Kaufteil | neu aufgenommen | Cache-Prüfsumme | Masse | Kennmaße |",
                   "|---|---|---|---|---|"]
        zeilen += [f"| {e.get('kaufteil', s)} | {'ja' if e.get('gebaut') else 'nein'} | {_zelle(e.get('pruefsumme'))} | "
                   f"{_zelle(e.get('masse'))} | {_zelle(e.get('kennmasse'))} |" for s, e in sorted(letzter["kaufteile"].items())]
```

durch:

```python
        zeilen += ["", "## Kaufteile", "",
                   "| Kaufteil | neu aufgenommen | Cache-Prüfsumme | Masse | Kennmaße | Gewindemodell (Ø mm) |",
                   "|---|---|---|---|---|---|"]
        zeilen += [f"| {e.get('kaufteil', s)} | {'ja' if e.get('gebaut') else 'nein'} | {_zelle(e.get('pruefsumme'))} | "
                   f"{_zelle(e.get('masse'))} | {_zelle(e.get('kennmasse'))} | {_gewindemodelle(e.get('gewinde_modell'))} |"
                   for s, e in sorted(letzter["kaufteile"].items())]
```

- [ ] **Step 4: Spec nachziehen (§4.3, §5.3, §6.4, §10)**

In `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` ersetzen:

~~~markdown
- Gegenprobe je Position: eine Zylinderfläche mit Achse durch den Punkt parallel zu `normale`; ihr Ø ist der **Kernloch-Ø**
  (Gewindepaarung mit Ringvolumen, §6.4) oder der **Nenn-Ø** (Soll der Überlappung 0); sonst Mangel `gewinde:<gruppe>`. Welcher Ø
  vorliegt, schreibt `hole` in den Cache-Eintrag (`modell: kernloch | nenn` je Gruppe).
~~~

durch:

~~~markdown
- Gegenprobe je Position: eine Zylinderfläche mit Achse durch den Punkt parallel zu `normale`; ihr Ø liegt im
  **Kernloch-Bereich** – von D1 nach ISO 724 (D − 1,0825·P; M5: 4,134) bis zum Kernloch der Tabelle (Bohrer-Ø aus
  `bohrungsnormen.yaml`; M5: 4,2), je ± 0,01 mm – (Modell `kernloch`, Gewindepaarung mit Ringvolumen, §6.4) oder ist der
  **Nenn-Ø** ± 0,01 mm (Modell `nenn`, Soll der Überlappung 0); sonst Mangel `gewinde:<gruppe>`. Die Steigung P kommt bei
  Feingewinde aus der Größe (`M10x1`), bei Regelgewinde aus der abgeglichenen Normtabelle ISO 4762 (Spalte `p`); ohne
  Steigung gilt nur das Tabellen-Kernloch. Modell und gemessener Ø müssen in der Gruppe einheitlich sein (sonst Mangel
  `gewinde:<gruppe>`, „Positionen uneinheitlich“). `hole` schreibt je Gruppe `{modell: kernloch | nenn, durchmesser:
  <gemessener Ø>}` in den Cache-Eintrag, der Bau übernimmt es ins Bauprotokoll (`kaufteile.<schluessel>.gewinde_modell`).
  *Nachgezogen bei der Umsetzung (Nutzerentscheidung 2026-10-06):* Hersteller modellieren Gewindelöcher oft mit D1 statt
  mit dem Bohrer-Ø (Nanotec GPLE60-2S-32: Ø 4,134).
~~~

In `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` ersetzen:

~~~markdown
3. Original im Quellordner: fehlt → `KAUFTEIL_QUELLE_FEHLT` (Nutzer gibt die Datei erneut, `untersuchen`); SHA-256 ≠
   `original.sha256` → `KAUFTEIL_QUELLE_ABWEICHEND`.
~~~

durch:

~~~markdown
3. Original im Quellordner: fehlt → `KAUFTEIL_QUELLE_FEHLT` (Nutzer gibt die Datei erneut, `untersuchen`; bei
   `original.bezug.art: url` nennt die Meldung die Download-URL mit Datum – *nachgezogen bei der Umsetzung*: Herstellerdateien
   liegen nicht im Git); SHA-256 ≠ `original.sha256` → `KAUFTEIL_QUELLE_ABWEICHEND`.
~~~

In `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` ersetzen:

~~~markdown
   Gewindemodell je Gruppe, Kennzahlen der Diagnose, Datum, SW-Version). Nicht bestanden → `KAUFTEIL_PRUEFUNG` (Mängel,
~~~

durch:

~~~markdown
   Gewindemodell je Gruppe mit gemessenem Ø (§4.3), Kennzahlen der Diagnose, Datum, SW-Version). Nicht bestanden →
   `KAUFTEIL_PRUEFUNG` (Mängel,
~~~

In `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` ersetzen:

~~~markdown
Einschraublänge wie bisher; Mangel, wenn sie `gewindetiefe` oder `tiefe` überschreitet; Soll des Volumens = Ring zwischen Nenn-
und Kernloch-Ø über die Einschraublänge (Modell `kernloch`, Toleranz wie bisher 1 %) bzw. **keine Überlappung** (Modell `nenn`:
Schraube und Gewindeloch berühren sich nur; jede gemeldete Überlappung ist ein Mangel). Jede andere Überlappung mit einem Kaufteil ist ein Mangel; Überlappungen zwischen
~~~

durch:

~~~markdown
Einschraublänge wie bisher; Mangel, wenn sie `gewindetiefe` oder `tiefe` überschreitet; Soll des Volumens = Ring zwischen Nenn-
und **gemessenem** Ø (Gewindemodell der Aufnahme, §4.3) über die Einschraublänge (Modell `kernloch`, Toleranz wie bisher 1 %,
mindestens 0,01 mm³) bzw. **keine Überlappung** (Modell `nenn`: Schraube und Gewindeloch berühren sich nur; jede Überlappung
über 0,01 mm³ ist ein Mangel); Gewindemodell unbekannt → `ok: null` mit Hinweis. *Nachgezogen bei der Umsetzung
(2026-10-06):* gemessener Ø statt Tabellen-Kernloch; absolute Untergrenze 0,01 mm³, damit Rechenrauschen bei Soll 0 kein
Mangel ist. Jede andere Überlappung mit einem Kaufteil ist ein Mangel; Überlappungen zwischen
~~~

In `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` ersetzen:

~~~markdown
| `KAUFTEIL_QUELLE_FEHLT` | Original nicht im Quellordner | erwarteter Pfad, Hinweis `untersuchen` |
~~~

durch:

~~~markdown
| `KAUFTEIL_QUELLE_FEHLT` | Original nicht im Quellordner | erwarteter Pfad, Hinweis `untersuchen`; bei `original.bezug.art: url` Download-URL und Datum |
~~~

- [ ] **Step 5: Tests laufen lassen, sie bestehen**

Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile tests\baugruppe\test_kaufteil_bau_pruefen.py`
Expected: `67 passed`. Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **930 passed, 138 deselected** (N9 + 7);
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m swki api pruefe-code swki spikes tests/live` → `"befunde": []`.

- [ ] **Step 6: Optionaler Live-Nachweis (Controller entscheidet; frisches SolidWorks)**

Belegt das neue Gewindemodell am Muster (Kernloch 4,2, im Bereich 4,134…4,2): BLOCKED Neustart an den Controller, dann
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m pytest -m sw "tests/live/test_live_kaufteile.py::test_baue_und_pruefe_muster" -q`
Expected: `1 passed`. Import-Optionen vor/nach `True True 0`. Ohne diesen Schritt belegt Task 7N das Modell am GPLE60.

- [ ] **Step 7: Commit**

```powershell
git add swki/kaufteile/ortung.py swki/kaufteile/bewertung.py swki/kaufteile/aufnahme.py swki/kaufteile/cache.py swki/kaufteile/quelle.py swki/baugruppe/bewertung.py swki/pruefung/bericht.py tests/kaufteile/test_ortung.py tests/kaufteile/test_bewertung.py tests/kaufteile/test_befehle_kaufteile.py tests/baugruppe/test_kaufteil_bau_pruefen.py tests/live/test_live_kaufteile.py docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md
git commit -m "kaufteile: Gewinde-Ø-Bereich D1 bis Kernloch, Gewindemodell mit gemessenem Ø, Untergrenze nenn, Quelle mit Download-URL (Stufe 3c, Task G)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7N: Katalogeintrag Nanotec GPLE60-2S-32 – Eintrag, Nutzerfreigabe, Prüfer, hole (live)

Ersetzt Task 7 des Hauptplans.

**Files:**
- Create: `swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml` (dazu von swki: `freigabe.json`, `gple60-2s-32.freigegeben.yaml`,
  `gple60-2s-32.pruefer.json` im selben Ordner)
- Test: `tests/kaufteile/test_eintrag_gple60.py`, `tests/live/test_live_kaufteil_hole.py`

**Interfaces:**
- Consumes: Tasks 1–6, Fix-N, Task G (Gewinde-Ø-Bereich, `IMPORTWEG_VERSION = 2`), Diagnose lauf-1, Original und Datenblatt
  im Quellordner `<kaufteilbibliothek>/quellen/nanotec/`.
- Produces: den freigegebenen und geprüften Katalogeintrag `Nanotec GPLE60-2S-32` (Task 10N braucht ihn) und den Cache-
  Eintrag `<kaufteilbibliothek>/2025/Nanotec_GPLE60-2S-32.sldprt` (+ `.json`).

**Entscheidungen im Eintrag (vom Planer, mit Begründung):**
- **Material `1.0503` (C45):** Pflichtfeld, das Datenblatt nennt keinen Werkstoff. Abtriebswelle, Passfeder und Verzahnung
  eines Präzisions-Planetengetriebes sind Stahl; `1.0503` ist im Bestand und in SW 2025 live erprobt (Muster-Welle, Spike
  S15). Die Masse 1,1 kg aus dem Datenblatt **überschreibt** die Materialmasse (2,03 kg als Vollstahl), daher wirkt das
  Material nur auf Darstellung und Eigenschaften. Das Teil trägt den Hinweis als Eigenschaft `Werkstoffhinweis`.
- **Toleranzen h7:** Das CAD-Modell trägt Nennmaße (oberes Abmaß von h7 = 0). `tol` = Breite des Toleranzfelds IT7
  (Ø 14: 0,018; Ø 40: 0,025), symmetrisch um das Nennmaß; das umfasst das ganze h7-Feld.
- **`EINBAU_DREHLAGE` (Präz. 26):** `ebene_durch_achse` mit `nahe` [56, 30, −59,5] = Punkt auf dem Lochkreis Ø 52 mittig
  zwischen Gewinde 1 und 2 (Winkel 0°). Die Ebene ist die Symmetrieebene des Lochbilds und steht senkrecht auf zwei Seiten
  des □ 60 (Normale ±y). So gilt im Motorhalter beides, was der Auftrag verlangt: Drehlage `parallel` zur Ebene `vorne` des
  Bocks **und** Senkungen „unter 45°“ bei aufrecht stehendem □ 60 (Unterkante 10 mm über dem Fuß). Eine Ebene durch eine
  Gewindeposition (Diagonale) parallel zu `vorne` würde das Getriebe um 45° drehen: Lochbild auf 0°/90°, □ 60 auf der
  Spitze, tiefster Punkt 40 unter der Achse = genau auf der Fußoberseite (Achshöhe 50) – Berührung bzw. Kollision. Rückfrage
  an den Nutzer unten (Empfehlung: so lassen).
- **Gewindegruppe ohne `beleg`:** Größe und Lochkreis sind belegt (Maß `Lochkreis Ø 52`), die Gewindetiefe nicht; die
  Belegregel gilt je Gruppe, also Hinweis `nicht_belegt` für `gewinde.flansch`. `gewindetiefe` = `tiefe` = 10 aus der
  Mantellänge (siehe Rechnung oben).
- **Belege:** `d1` Seite 248 (Maßbild), `d2` Seite 249 (Tabelle Versions), beide `datei` + `url`; `h1` Produktseite
  (abgerufen 2026-10-06: Untersetzung 32, NEMA 23/24, CAD-Download „GPLE60-2S“, **keine Maße**) – nur Herkunft, an kein
  Kennmaß gebunden.

- [ ] **Step 1: Vorbedingungen und Gewindeloch-Boden live bestätigen**

Task G ist committet. SolidWorks läuft, genau eine Instanz, Private Bytes < 3000 MB (sonst BLOCKED Neustart), Einstellungen
`False 1`, Import-Optionen `True True 0`. Original prüfen:
`.venv\Scripts\python.exe -c "from swki.aenderungen import sha256_datei; from swki.kaufteile.quelle import quellordner; from swki.konfig import lade_rechner; print(sha256_datei(quellordner(lade_rechner(), 'Nanotec') / 'gple60-2s-32.stp'))"`
Expected: `b240fd166f19394332c796e2a05cc27a0c7ed14eb500f717012318a203f36aea`. Die Diagnose aus lauf-1 gilt; **nicht** erneut
`untersuchen` (Volumen 258960,557 stammt von dort).

Gewindeloch-Boden (Annahme der Rechnung oben) bestätigen – `auftraege/KAUFTEIL-GPLE60/pruefe_gewindeloch.py` anlegen
(Auftragsordner, nicht im Git; keine neuen API-Aufrufe):

```python
"""Einmalige Bestätigung (Plan-Nachtrag Task 7N): Mantel der Flanschgewinde z −59,5…−49,5 und Boden ohne ebene Fläche."""

from swki.compiler import sw
from swki.kaufteile import quelle, sw_kaufteil
from swki.konfig import lade_rechner
from swki.verbindung import in_mm, verbinde

r = lade_rechner()
app = verbinde(r.sw_jahr)
model = sw_kaufteil.importiere(app, quelle.quellordner(r, "Nanotec") / "gple60-2s-32.stp")
try:
    flaechen = sw_kaufteil.alle_flaechen(model)
    for f in flaechen:
        if f.art == "zylinder" and abs(2 * f.radius - 4.134) < 0.01:
            b = f.objekt.GetBox
            print("Mantel", round(in_mm(b[2]), 3), round(in_mm(b[5]), 3))
    for f in flaechen:
        if f.art == "sonstige" and abs(f.punkt[2] + 50) < 3:
            print("Boden", [round(c, 3) for c in f.punkt])
finally:
    sw.schliesse(app, model)
```

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe auftraege\KAUFTEIL-GPLE60\pruefe_gewindeloch.py`
Expected: viermal `Mantel -59.5 -49.5` (± 0,01) und viermal `Boden` mit z ≈ −50,1 (Bohrspitze; bei 118° liegt die Mitte des
Kegels 2,067/tan 59°/2 ≈ 0,62 unter z −49,5) an den vier Lochmitten (x, y ∈ {11,615; 48,385}). Weicht es ab (Mantel kürzer,
Boden anders, Loch offen): NEEDS_CONTEXT mit der Ausgabe – der Controller fragt den Nutzer nach `gewindetiefe`/`tiefe`.
Danach Import-Optionen wieder `True True 0`.

- [ ] **Step 2: Eintrag anlegen**

`swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml` anlegen:

```yaml
# Nanotec GPLE60-2S-32: Präzisions-Planetengetriebe, 2-stufig, i = 32, Anbau NEMA 23/24 (echtes Herstellerteil,
# Nutzerentscheidung 2026-10-06; ersetzt den Muster-Getriebemotor als Katalogeintrag). Original: STEP „GPLE60-2S“ von
# nanotec.com (gilt für alle 2S-Untersetzungen), Datenblatt: Baureihenübersicht GPLE60 (Seiten 248/249). Beide liegen
# nur im Quellordner der Kaufteil-Bibliothek, nicht im Git (fehlt das Original: KAUFTEIL_QUELLE_FEHLT mit der URL).
# STEP-Koordinaten (Diagnose lauf-1): Achse x = 30, y = 30, Richtung z. Motoradapter □ 60 z 0…24, Gehäuse Ø 60
# z 0…−59,5, Abtriebsflansch z = −59,5 (Normale −z), Zentrierbund Ø 40 bis z −62,5, Absatz Ø 17 bis −64,5, Welle Ø 14 bis
# −94,5 mit Passfeder 5 (Rücken x = 21, Nut z −67…−92); 4 × M5 (modelliert mit D1 Ø 4,134 nach ISO 724, Mantel 10 lang,
# Boden ohne ebene Fläche) auf Lochkreis Ø 52 unter 45° zum □ 60. Drei Volumenkörper (Adapter, Gehäuse, Welle).
# Werkstoff nennt der Hersteller nicht: 1.0503 angenommen (Welle/Verzahnung Stahl); die Masse kommt aus dem Datenblatt.
# Gewindetiefe nennt das Datenblatt nicht: gewindetiefe/tiefe aus der STEP („nicht belegt“).
art: kaufteil
hersteller: Nanotec
bestellnummer: GPLE60-2S-32
benennung: Präzisions-Planetengetriebe GPLE60, 2-stufig, i = 32
original:
  datei: gple60-2s-32.stp
  sha256: "b240fd166f19394332c796e2a05cc27a0c7ed14eb500f717012318a203f36aea"
  bezug:
    art: url
    url: "https://www.nanotec.com/fileadmin/files/Datenblaetter/Getriebe/Planetengetriebe_GPLE60/GPLE60-2S.stp"
    datum: "2026-10-06"
    hinweis: "Download mit Nutzerfreigabe (85716 Byte); STEP der Baureihe 2S, gilt für alle 2S-Untersetzungen"
datenblatt:
  datei: Product_Overview_GPLE60.pdf
  url: "https://www.nanotec.com/fileadmin/files/Baureihenuebersichten/Getriebe/Product_Overview_GPLE60.pdf"
koerper: 3
material: "1.0503"
masse: {kg: 1.1, beleg: [d2]}
eigenschaften: {Untersetzung: "32", Motoranbau: "NEMA 23/24", Werkstoffhinweis: "Hersteller ohne Angabe, Masse aus Datenblatt"}
belege:
  d1: {art: datenblatt, datei: Product_Overview_GPLE60.pdf,
       url: "https://www.nanotec.com/fileadmin/files/Baureihenuebersichten/Getriebe/Product_Overview_GPLE60.pdf",
       seite: 248, hinweis: "Maßbild GPLE60 (Dimensions): Ø14h7, Ø17, Ø40h7, Ø60, □60, 35, 30, 25, 2.5, 3, 5, 16, 4-M5 auf 52"}
  d2: {art: datenblatt, datei: Product_Overview_GPLE60.pdf,
       url: "https://www.nanotec.com/fileadmin/files/Baureihenuebersichten/Getriebe/Product_Overview_GPLE60.pdf",
       seite: 249, hinweis: "Tabelle Versions, Zeile GPLE60-2S-32: L 59,5 mm, L1 24 mm (NEMA 23/24), 1,1 kg"}
  h1: {art: hersteller, url: "https://www.nanotec.com/us/en/products/901-gple60-2s-32", abgerufen: "2026-10-06",
       hinweis: "Produktseite: Untersetzung 32, NEMA 23/24, CAD-Download GPLE60-2S – keine Maße (Herkunft, kein Kennmaß)"}
einbau:
  EINBAU_ACHSE: {zylinder: {nahe: [37, 30, -79.5], durchmesser: 14, senkrecht_zu: EINBAU_FLANSCH}}
  EINBAU_FLANSCH: {ebene: {nahe: [30, 5, -59.5], normale: [0, 0, -1]}}
  EINBAU_DREHLAGE: {ebene_durch_achse: {achse: EINBAU_ACHSE, nahe: [56, 30, -59.5]}}
gewinde:
  flansch:
    groesse: M5
    gewindetiefe: 10
    tiefe: 10
    normale: [0, 0, -1]
    positionen: [[48.3848, 48.3848, -59.5], [48.3848, 11.6152, -59.5], [11.6152, 11.6152, -59.5], [11.6152, 48.3848, -59.5]]
pruefung:
  huellquader: {soll: [60, 60, 118.5], tol: 0.1, beleg: [d1, d2]}
  volumen: {soll: 258960.557, toleranz_prozent: 0.01}
  durchmesser_pruefen:
    - {was: Welle Ø 14h7, nahe: [37, 30, -79.5], soll: 14, tol: 0.018, referenz: EINBAU_ACHSE, beleg: [d1]}
    - {was: Zentrierbund Ø 40h7, nahe: [50, 30, -61], soll: 40, tol: 0.025, referenz: EINBAU_ACHSE, beleg: [d1]}
    - {was: Absatz Ø 17, nahe: [38.5, 30, -63.5], soll: 17, referenz: EINBAU_ACHSE, beleg: [d1]}
    - {was: Gehäuse Ø 60, nahe: [60, 30, -30], soll: 60, referenz: EINBAU_ACHSE, beleg: [d1]}
  masse_pruefen:
    - {was: Wellenlänge ab Flansch, von: {referenz: EINBAU_FLANSCH},
       zu: {flaeche: {nahe: [36, 30, -94.5], normale: [0, 0, -1]}}, soll: 35, beleg: [d1]}
    - {was: Zentrierbundhöhe, von: {referenz: EINBAU_FLANSCH},
       zu: {flaeche: {nahe: [30, 15, -62.5], normale: [0, 0, -1]}}, soll: 3, beleg: [d1]}
    - {was: Getriebelänge L, von: {referenz: EINBAU_FLANSCH},
       zu: {flaeche: {nahe: [30, 2, 0], normale: [0, 0, -1]}}, soll: 59.5, beleg: [d2]}
    - {was: Lochkreis Ø 52, von: {gewinde: flansch, instanz: 1}, zu: {gewinde: flansch, instanz: 3}, soll: 52,
       beleg: [d1]}
    - {was: Lochabstand benachbart, von: {gewinde: flansch, instanz: 1}, zu: {gewinde: flansch, instanz: 2},
       soll: 36.77, beleg: [d1]}
    - {was: Passfederbreite, von: {flaeche: {nahe: [22.2308, 27.5, -79.5], normale: [0, -1, 0]}},
       zu: {flaeche: {nahe: [22.2308, 32.5, -79.5], normale: [0, 1, 0]}}, soll: 5, beleg: [d1]}
    - {was: Wellenachse bis Passfederrücken, von: {referenz: EINBAU_ACHSE},
       zu: {flaeche: {nahe: [21, 30, -79.5], normale: [-1, 0, 0]}}, soll: 9, beleg: [d1]}
```

**Jeder Punkt gegen die Diagnose geprüft** (Zylinder: Punkt auf dem Mantel im Achsabschnitt der Fläche; Ebene: Punkt in der
begrenzten Fläche, Normale aus dem Material):

| Punkt | Fläche (Diagnose) | Nachweis |
|---|---|---|
| `EINBAU_ACHSE` / Welle [37, 30, −79,5] | Zylinder Ø 14, z −64,5…−94,5 | Abstand zur Achse (30, 30) = 7 = r; +x-Seite, die Passfeder sitzt auf −x (Rücken x = 21) |
| `EINBAU_FLANSCH` [30, 5, −59,5] | Ebene z −59,5 Normale −z, 2773,74 = π·30² − 4·π·2,067² (Kreisscheibe Ø 60 ohne Gewindelöcher) | r = 25: außerhalb des Bundes (r 20), innerhalb Ø 60, Abstand zur nächsten Lochmitte (11,62 \| 11,62) 19,5 > 2,07. Die Bund-Oberseite (Normale +z) scheidet über die Normale aus. |
| `EINBAU_DREHLAGE` [56, 30, −59,5] | (Hilfspunkt, keine Fläche) | Abstand zur Achse 26 > 1; Normale der Ebene ±y |
| Zentrierbund [50, 30, −61] | Zylinder Ø 40, z −59,5…−62,5 | r = 20, z im Abschnitt |
| Absatz [38,5, 30, −63,5] | Zylinder Ø 17, z −62,5…−64,5 | r = 8,5, z im Abschnitt |
| Gehäuse [60, 30, −30] | Zylinder Ø 60, z 0…−59,5 | r = 30, z im Abschnitt; die Adapterseite x = 60 liegt bei z 0…24 |
| Wellenende [36, 30, −94,5] | Ebene z −94,5 Normale −z, Ring r 4,43…7 (92,27 = π(7² − 4,4306²)) | r = 6 |
| Bund-Unterseite [30, 15, −62,5] | Ebene z −62,5 Normale −z, Ring r 8,5…20 | r = 15 |
| Adapter-Unterseite [30, 2, 0] | Ebene z 0 Normale −z, ganzes □ 60 ohne Eckabschnitte und Ø 1 | (30 \| 2) im Quadrat; Gehäuse-Oberseite (Normale +z) scheidet über die Normale aus |
| Passfeder-Seiten [22,2308, 27,5 / 32,5, −79,5] | Ebenen y 27,5 (Normale −y) und y 32,5 (+y), x 21…23,46 | Mitte zwischen Rücken x = 21 und Mantel x = 30 − √(7² − 2,5²) = 23,46; z im geraden Teil −69,5…−89,5 |
| Passfeder-Rücken [21, 30, −79,5] | Ebene x = 21 Normale −x | Diagnose-Punkt |
| Gewinde 1–4 [30 ± 18,3848 \| 30 ± 18,3848, −59,5] | Zylinder Ø 4,134, Achse ‖ z | Abstand zur Achse 0 (≤ 0,1); 18,3848 = 26/√2 |

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m swki validieren swki\wissen\kaufteile\nanotec\gple60-2s-32.yaml`
Expected (exakt so):

```json
{
  "gueltig": true,
  "spec": "swki\\wissen\\kaufteile\\nanotec\\gple60-2s-32.yaml",
  "art": "kaufteil",
  "schluessel": "Nanotec GPLE60-2S-32",
  "pruefsumme": "<64 Hex>",
  "hinweise": [
    {
      "art": "nicht_belegt",
      "pfad": "gewinde.flansch",
      "meldung": "Kennmaß ohne Beleg: wird geprüft, gilt im Bericht als „nicht belegt“"
    }
  ]
}
```

(Vorab gemessen: Prüfsumme `a696adb08133ba2507dae5b38699365d62c8c07c478892cf683a6084366c6c7f` bei LF-Zeilenenden; die
Prüfsumme läuft über das geladene YAML, Zeilenenden ändern sie nicht.) Kein `masse_aus_material`, kein
`kennmasse_nicht_belegt`, keine Befunde.

- [ ] **Step 3: Nutzerfreigabe (Controller)**

BLOCKED an den Controller: Der **Controller legt dem Nutzer** den Eintrag vor – Kennmaße mit Belegen (Tabelle
„Diagnose ↔ Datenblatt“ oben), die Diagnosebilder aus `C:\Users\User\.swki\arbeit\KAUFTEILE\Nanotec_GPLE60-2S-32\lauf-1\bilder\`,
die Bedeutung der drei Einbaureferenzen (Achse = Abtriebswelle, Flansch = Anlagefläche Ø 60 hinter dem Zentrierbund,
Drehlage = Symmetrieebene des Lochbilds durch die Mitte einer □-60-Seite) und die Annahmen (Material 1.0503 mit
überschriebener Masse 1,1 kg; Gewindetiefe 10 aus der STEP, nicht belegt; h7 als symmetrische IT7-Toleranz) – und fragt nach
dem OK, eine Frage, Empfehlung „freigeben“. Erst nach ausdrücklichem OK:
`.venv\Scripts\python.exe -m swki freigeben swki\wissen\kaufteile\nanotec\gple60-2s-32.yaml`.
Will der Nutzer etwas ändern: Eintrag ändern, Step 2 wiederholen, erneut fragen.

- [ ] **Step 4: Musterteil und Prüfer (Controller; frisches SolidWorks)**

BLOCKED Neustart an den Controller (Aufnahme mit Bildern: Spitzen bis 5,4 GB, Task 5). Dann:
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m swki kaufteil muster "Nanotec GPLE60-2S-32"`
Expected: `bestanden` true, `maengel` [], `fehler` null, vier Bilder. Im `pruefbericht` (Pfad in der Ausgabe) 23 Prüfungen in
dieser Reihenfolge, alle `ok: true`: `rebuild`, `import`, `koerper` (3), `huellquader` ([60, 60, 118.5]), `volumen`,
`einbau:EINBAU_ACHSE`, `einbau:EINBAU_FLANSCH`, `einbau:EINBAU_DREHLAGE`, `gewinde:flansch` (`modell` `kernloch`,
`durchmesser` 4.134), `durchmesser:Welle Ø 14h7`, `durchmesser:Zentrierbund Ø 40h7`, `durchmesser:Absatz Ø 17`,
`durchmesser:Gehäuse Ø 60`, `mass:Wellenlänge ab Flansch` (35), `mass:Zentrierbundhöhe` (3), `mass:Getriebelänge L` (59.5),
`mass:Lochkreis Ø 52` (52), `mass:Lochabstand benachbart` (36.7696), `mass:Passfederbreite` (5),
`mass:Wellenachse bis Passfederrücken` (9), `material`, `eigenschaften`, `masse` (1.1, `ueberschrieben` true).
**Notieren (für Task 10N):** `einbau:EINBAU_FLANSCH` → `bezug.richtung` (erwartet [0, 0, −1]) und
`einbau:EINBAU_DREHLAGE` → `bezug.richtung` (erwartet [0, ±1, 0]). Steht bei `EINBAU_FLANSCH` [0, 0, 1]: Ledger-Eintrag,
Task 10N `v4` auf `ausrichtung: gleich`. Jede andere Abweichung (Mangel, Ortungsfehler): anhalten, NEEDS_CONTEXT mit dem
Prüfbericht-Auszug – Sollwerte nie an Messwerte anpassen; der Controller klärt mit dem Nutzer (neue Freigabe).

Der **Controller** startet den Prüfer-Agenten (`subagent_type: pruefer`) mit `eintrag`
(`swki/wissen/kaufteile/nanotec/gple60-2s-32.freigegeben.yaml`), `datenblatt` (PDF im Quellordner), `pruefbericht` und den
Bildern aus der Ausgabe und gibt im Auftrag die Kaufteil-Checkliste aus dem Hauptplan Task 11 Step 1 (Block für
`.claude/agents/pruefer.md`, Ruling B3) in der Fassung von Task 11N mit. Urteil unverändert (nur das JSON-Objekt) nach
`auftraege/KAUFTEIL-GPLE60/urteil.json`; dann
`.venv\Scripts\python.exe -m swki kaufteil urteil "Nanotec GPLE60-2S-32" auftraege\KAUFTEIL-GPLE60\urteil.json --freigabe-pruefsumme <freigabe_pruefsumme aus muster>`.
Mängel des Prüfers: mit dem Nutzer klären, Eintrag korrigieren (neue Freigabe, neues Musterteil), nie still.

- [ ] **Step 5: Unit-Test des Eintrags**

`tests/kaufteile/test_eintrag_gple60.py` anlegen:

```python
"""Katalogeintrag Nanotec GPLE60-2S-32 (Plan-Nachtrag Task 7N) ohne SolidWorks: gültig, einziger Hinweis die unbelegte
Gewindegruppe, freigegeben und mit bestandenem Prüfer-Urteil zur aktuellen Freigabe (Spec 3c §4.5, §4.6, §5.2)."""

from swki.kaufteile.eintrag import lade_eintrag, validieren
from swki.kaufteile.katalog import finde, geprueft
from swki.spec.freigabe import pruefe_freigabe

URL = "https://www.nanotec.com/fileadmin/files/Datenblaetter/Getriebe/Planetengetriebe_GPLE60/GPLE60-2S.stp"


def test_gple60_gueltig_freigegeben_geprueft():
    pfad = finde("Nanotec GPLE60-2S-32")
    assert validieren(pfad)["hinweise"] == [{"art": "nicht_belegt", "pfad": "gewinde.flansch",
                                              "meldung": "Kennmaß ohne Beleg: wird geprüft, gilt im Bericht als "
                                                         "„nicht belegt“"}]
    spec = lade_eintrag(pfad)
    pruefe_freigabe(pfad, spec)
    assert geprueft(pfad, spec) and spec["original"]["bezug"] == {
        "art": "url", "url": URL, "datum": "2026-10-06",
        "hinweis": "Download mit Nutzerfreigabe (85716 Byte); STEP der Baureihe 2S, gilt für alle 2S-Untersetzungen"}
```

Run: `.venv\Scripts\python.exe -m pytest -q tests\kaufteile\test_eintrag_gple60.py` → `1 passed` (vor Freigabe und Urteil
rot: `FreigabeFehler` bzw. `geprueft` false). Der Test schützt Eintrag, Freigabe und Urteil vor stillen Änderungen.

- [ ] **Step 6: Live-Test `hole` (Private Bytes < 3000 MB, sonst BLOCKED Neustart)**

`tests/live/test_live_kaufteil_hole.py` anlegen. **Entscheidung (Nutzerentscheidung 2):** fehlt das Original, **scheitert**
der Test mit `KAUFTEIL_QUELLE_FEHLT` und der URL – kein `pytest.skip`. Begründung: Die Regression verhält sich ebenso; ein
Skip würde einen unvollständig eingerichteten Rechner als „grün“ ausweisen, und Live-Tests laufen ohnehin nur gezielt.

```python
"""Live: swki kaufteil hole am freigegebenen und geprüften Eintrag Nanotec GPLE60-2S-32 (Spec 3c §5.3) mit eigenem
Cache; der zweite Aufruf ist ein Cache-Treffer. Das Original ist eine Herstellerdatei und liegt nur im Quellordner der
Kaufteil-Bibliothek dieses Rechners (nicht im Git); fehlt es, scheitert der Test mit KAUFTEIL_QUELLE_FEHLT und der
Download-URL aus dem Eintrag (wie die Regression, Nutzerentscheidung 2026-10-06)."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from swki.kaufteile import befehle, quelle
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.katalog import finde
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
SCHLUESSEL = "Nanotec GPLE60-2S-32"
D1_M5 = 4.134  # Kerndurchmesser D1 nach ISO 724, so modelliert Nanotec die Flanschgewinde (Diagnose lauf-1)


def test_hole_baut_und_trifft_den_cache(tmp_path, monkeypatch):
    echt = lade_rechner()
    eintrag = lade_eintrag(finde(SCHLUESSEL))
    original = quelle.original(echt, eintrag)  # KAUFTEIL_QUELLE_FEHLT mit URL, wenn die Herstellerdatei fehlt
    r = replace(echt, kaufteilbibliothek=tmp_path / "kauf")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    quelle.uebernimm(r, original, "Nanotec", "GPLE60-2S-32", eintrag)
    erst = befehle.hole(SCHLUESSEL)
    modell = erst["gewinde_modell"]["flansch"]
    assert erst["gebaut"] is True and modell["modell"] == "kernloch" and abs(modell["durchmesser"] - D1_M5) <= 0.0005
    cache_eintrag = json.loads(Path(erst["pfad"]).with_suffix(".json").read_text(encoding="utf-8"))
    assert cache_eintrag["bestanden"] is True and cache_eintrag["kennzahlen"]["interconnect"] == []
    assert cache_eintrag["gewinde_modell"] == erst["gewinde_modell"]
    zweit = befehle.hole(SCHLUESSEL)
    assert zweit["gebaut"] is False and zweit["pfad"] == erst["pfad"] and zweit["gewinde_modell"] == erst["gewinde_modell"]
```

(`abs(… − 4,134) ≤ 0,0005`: der Cache hält den Ø auf 4 Stellen; die Diagnose zeigt 4,134 auf 3 Stellen. Das ist keine
Anpassung an Messwerte, sondern die Rundungsbreite der Anzeige.)

Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_kaufteil_hole.py --zeit 600`
Expected: `OK`. Danach (Private Bytes prüfen) den echten Cache füllen:
`.venv\Scripts\python.exe -m swki kaufteil hole "Nanotec GPLE60-2S-32"` → `gebaut` true, `gewinde_modell`
`{"flansch": {"modell": "kernloch", "durchmesser": 4.134}}`; zweiter Aufruf `gebaut` false;
`.venv\Scripts\python.exe -m swki kaufteil liste` → `freigegeben`, `geprueft`, `cache` true. Import-Optionen `True True 0`.
Ganze Suite: `.venv\Scripts\python.exe -m pytest -q` → **931 passed, 139 deselected** (N9 + 8 / D9 + 1);
`… swki api pruefe-code swki spikes tests/live` → `"befunde": []`.

- [ ] **Step 7: Commit (keine Herstellerdatei!)**

```powershell
git status --short swki/wissen/kaufteile
git add swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml swki/wissen/kaufteile/nanotec/freigabe.json swki/wissen/kaufteile/nanotec/gple60-2s-32.freigegeben.yaml swki/wissen/kaufteile/nanotec/gple60-2s-32.pruefer.json tests/kaufteile/test_eintrag_gple60.py tests/live/test_live_kaufteil_hole.py
git commit -m "kaufteile: Katalogeintrag Nanotec GPLE60-2S-32 mit Freigabe und Prüfer-Urteil, Live-Test hole (Stufe 3c, Task 7N)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

`git status` vorher: im Ordner `nanotec/` genau diese vier Dateien, keine `.stp`/`.pdf`.

---

### Task 10N: Referenz Motorhalter mit Nanotec GPLE60-2S-32, Prüfer, Negativfall (live)

Ersetzt Task 10 des Hauptplans. **Name bleibt „Motorhalter“** (Ordner `tests/referenz/motorhalter/`, Spec §11, Test-IDs
`motorhalter-motorhalter.yaml`, CLAUDE.md und Ergebnisse verweisen darauf; funktional trägt der Bock die Antriebseinheit
Getriebe + später angebauter NEMA-23-Motor). Die Komponente heißt fachlich richtig `getriebe`.

**Files:**
- Create: `tests/referenz/motorhalter/grundplatte.yaml`, `motorbock.yaml`, `motorhalter.yaml`, `eingabe/beschreibung.md`,
  `tests/referenz/test_motorhalter.py`, `tests/live/test_live_motorhalter.py`
- Modify: `tests/referenz/test_referenzen.py`

**Interfaces:**
- Consumes: Tasks 1–9, G, 7N (freigegebener, geprüfter Eintrag und Cache-Eintrag `Nanotec_GPLE60-2S-32`).
- Produces: Referenz Motorhalter in der Regressions-Suite (`bereite_vor`), Negativfall „zu lange Flanschschraube“.

**Rechnung Motorhalter** (alle Maße mm; Baugruppe = Koordinaten der fixierten Grundplatte):

| Größe | Rechnung | Ergebnis |
|---|---|---|
| Grundplatte | L 160 (x −80…80), H 12 (y 0…12), B 100 (z −50…50); M6 (GT 10, GG 8) bei u, v = (−XG, ±ZG) → (−10, 12, ∓20) | Restboden 12 − 10 = 2 |
| Bock (Teilkoordinaten) | Fuß x 0…75, y 0…10, z ±30; Wand x 0…10, y 0…90; Senkungen M6 auf der Fußoberseite bei (45, 10, ∓20) | – |
| Lage Bock | v1: y-Versatz 12; v3: Achsen gleich gerichtet; v2: Senkung 1 (45 \| −20) über Gewinde 1 (−10 \| −20) → Δx = −55; Kontrolle Instanz 2: (45 \| 20) → (−10 \| 20) = Gewinde 2 | Bock x −55…20, y 12…102, Wand x −55…−45 |
| Zentrierbohrung | Bohrung DD 20 durch mit Senkung DZ 40 × TZ 5 von der Anlageseite x = DW = 10, Mitte (10, AH = 50, 0) | Tasche Teil-x 5…10 → Baugruppe −50…−45 |
| Getriebe | v4: Flansch auf Wand x = −45, Abtrieb nach −x (Normale −z ↔ −x); x_BG = −45 + (z_STEP + 59,5) | Wellenende −80,0 = Plattenkante; Adapter-Ende 38,5 |
| Achshöhe | 12 + AH 50 | **62** |
| Drehlage | v6: Ebene ±y (STEP) ‖ `vorne` (z = 0) → STEP-y ‖ z, STEP-x ‖ y; □ 60 aufrecht | Lochmitten y 62 ± 18,385, z ± 18,385 |
| Lochbild Wand | f4 auf x = 0, (u, v) = (±LK/√8, AH ± LK/√8) → (0, 50 ± 18,385, ∓18,385), LK 52 | fluchtet mit dem Getriebe (+12 in y) |
| Flanschschraube M5 × 12 | Senkung t 5,4 (`bohrungsnormen`) → Kopfauflage Teil-x 5,4 = BG −49,6; Spitze −49,6 + 12 = −37,6; Einschraublänge 12 − (10 − 5,4) | **7,4 ≤ 10** (Gewindetiefe = Bohrtiefe); Kopf k 5 → Oberkante 0,4 unter der Rückseite; dk 8,5 < Senkung 10 |
| Soll-Ring je Flanschschraube | `ueberlappung_soll(5, 0,8, 4,134, 7,4)` | 42,305 mm³ |
| Negativfall M5 × 16 | 16 − 4,6 | **11,4 > 10** → 4 Mängel `gewinde:flanschschraube.<i>` |
| Fußschraube M6 × 10 | Senkung t 6,4 → Auflage Teil-y 3,6 = BG 15,6; Spitze 5,6; Einschraublänge 10 − 3,6 | **6,4 ≤ 8**; Kopf k 6 → Oberkante 21,6 < Fußoberseite 22; dk 10 < Senkung 11 |
| Freiraum Getriebe ↔ Fuß | Unterkante □ 60/Ø 60: 62 − 30 = 32; Fußoberseite 12 + 10 = 22 | 10 |
| Freiraum Getriebe ↔ Grundplatte | 32 − 12 | 20 |
| Wand ↔ Getriebe | Anlage nur in der Ebene x = −45 (Kreisring Ø 40…60 auf der Wand); Wand y 12…102 deckt Ø 60 (32…92), z ±30 = □ 60 | Berührung, keine Überlappung |
| Zentrierbund in der Tasche | Bund x −45…−48 in Tasche −45…−50, Ø 40 in Ø 40 (Koinzidenz, `TreatCoincidenceAsInterference = False`) | axial 2 frei |
| Absatz Ø 17 / Welle in der Wand | Absatz −48…−50 in der Tasche; Welle Ø 14 ab −50 im Durchgang Ø 20 | radial 3 |
| Passfeder im Durchgang | Rücken r 9 (16 − 7), Nut STEP z −67…−92 → BG −52,5…−77,5, im Durchgang −55…−50 | radial 1 (r 10 − 9) |
| Stege Wand | Senkung Ø 10 bei r 26 → r 21…31 (Teil-x 0…5,4) gegen Tasche r ≤ 20 (Teil-x 5…10) und Durchgang r ≤ 10 | 1 bzw. 11; Durchgang Ø 5,5 (r 23,25) gegen Tasche 3,25 |
| Senkungen in der Wand | y 50 ± 18,385 ± 5 → 26,6…73,4 (Fuß endet bei 10), z ± 23,4 < 30 | im Material |
| Wandhöhe | Getriebe-Oberkante Teil-y 80 < HW 90 | – |
| Hüllquader | x: min(−80, −80) … max(80, 38,5, 20) = 160; y: 0 … max(102, 92) = 102; z: ±50 = 100 | **[160, 102, 100]** |
| Flansch an der Wand | `EINBAU_FLANSCH` ↔ Wand +x | 0 |

Reihenfolge der Getriebe-Verknüpfungen nach Skill `baugruppe` §2 („Ebene mit `ausrichtung` vor Achse“, Spike S12: sonst
kehrt SolidWorks eine Ausrichtung still um): v4 `deckungsgleich` Flansch ↔ Wandfläche, v5 `konzentrisch` Achse ↔
Zentrierbohrung (`drehung_sperren: false`, die Drehlage legt v6 fest – kein Hinweis `drehlage_doppelt`), v6 `parallel`
Drehlage ↔ `vorne`. `ausrichtung` von v6 ist frei wählbar (180° um die Achse bildet Lochbild und □ 60 auf sich ab); `gleich`.

- [ ] **Step 1: Tests schreiben**

`tests/referenz/test_motorhalter.py` anlegen:

```python
"""Referenz Motorhalter (Spec 3c §11, Plan-Nachtrag GPLE60) ohne SolidWorks: gültig mit dem freigegebenen und
geprüften Katalogeintrag Nanotec GPLE60-2S-32 aus dem Repo, ohne Hinweis; 9 Komponenten, 18 Verknüpfungen."""

from pathlib import Path

from swki.baugruppe.befehle import validieren

MOTORHALTER = Path(__file__).parent / "motorhalter" / "motorhalter.yaml"


def test_motorhalter_gueltig_ohne_hinweis():
    v = validieren(MOTORHALTER)
    assert (v["komponenten"], v["verknuepfungen"], v["hinweise"]) == (9, 18, [])
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv\Scripts\python.exe -m pytest -q tests\referenz\test_motorhalter.py`
Expected: FAIL – `1 failed` (`SpecFehler: 1 Befund(e) in der Spezifikation`, `motorhalter.yaml` fehlt noch).

- [ ] **Step 3: Referenz-Specs und Live-Tests**

`tests/referenz/motorhalter/grundplatte.yaml` anlegen:

```yaml
# Referenz Motorhalter (Spec 3c §11, Plan-Nachtrag GPLE60): Grundplatte, fixiert. Ursprung Mitte Unterseite,
# Oberseite y = H; zwei Gewinde M6 für den Fuß des Motorbocks bei x = −XG, z = ±ZG.
art: teil
name: Grundplatte
material: "1.0038"
eigenschaften: {Benennung: Grundplatte Motorhalter}
parameter: {L: 160, B: 100, H: 12, XG: 10, ZG: 20, GT: 10, GG: 8}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: normbohrung, art: gewinde, groesse: M6, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=-XG", "=ZG"], ["=-XG", "=-ZG"]], tiefe: "=GT", gewindetiefe: "=GG"}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  masse_pruefen:
    - {was: Abstand Gewinde, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true},
       soll: "=2*ZG"}
```

`tests/referenz/motorhalter/motorbock.yaml` anlegen:

```yaml
# Referenz Motorhalter (Spec 3c §11, Plan-Nachtrag GPLE60): Motorbock als Winkel für das Planetengetriebe Nanotec
# GPLE60-2S-32. Fuß x 0…LF, y 0…HF; Wand x 0…DW, y 0…HW; Getriebeachse parallel zu x in Höhe AH. Zentrierbohrung DZ
# (Tiefe TZ) für den Zentrierbund Ø 40 h7 (Höhe 3) von der Anlageseite x = DW, Wellendurchgang DD durch die Wand,
# 4 Senkungen M5 auf Lochkreis LK unter 45° auf der Rückseite (x = 0) für die Flanschschrauben, 2 Senkungen M6 im Fuß.
art: teil
name: Motorbock
material: "1.0038"
eigenschaften: {Benennung: Motorbock}
parameter: {LF: 75, BF: 60, HF: 10, DW: 10, HW: 90, AH: 50, DZ: 40, TZ: 5, DD: 20, LK: 52, XS: 45, ZS: 20}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: ["=LF/2", 0], breite: "=LF", hoehe: "=BF"}}]}
    ende: {typ: blind, tiefe: "=HF"}
  - id: f2
    typ: extrusion
    skizze: {ebene: rechts, elemente: [{rechteck: {mitte: [0, "=HW/2"], breite: "=BF", hoehe: "=HW"}}]}
    ende: {typ: blind, tiefe: "=DW"}
  - {id: f3, typ: bohrung, flaeche: {feature: f2, flaeche: "+x"}, positionen: [[0, "=AH"]], durchmesser: "=DD",
     durch: true, senkung: {durchmesser: "=DZ", tiefe: "=TZ"}}
  - {id: f4, typ: normbohrung, art: zylinderschraube, groesse: M5, flaeche: {nahe: [0, "=HW-5", 0]},
     positionen: [["=LK/8**0.5", "=AH+LK/8**0.5"], ["=-LK/8**0.5", "=AH+LK/8**0.5"], ["=-LK/8**0.5", "=AH-LK/8**0.5"],
                  ["=LK/8**0.5", "=AH-LK/8**0.5"]],
     durch: true}
  - {id: f5, typ: normbohrung, art: zylinderschraube, groesse: M6, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=XS", "=ZS"], ["=XS", "=-ZS"]], durch: true}
pruefung:
  huellquader: ["=LF", "=HW", "=BF"]
  masse_pruefen:
    - {was: Achshöhe Zentrierbohrung, von: {feature: f1, flaeche: "-y"}, zu: {feature: f3, instanz: 1, achse: true},
       soll: "=AH"}
    - {was: Lochkreis Flanschschrauben, von: {feature: f4, instanz: 1, achse: true},
       zu: {feature: f4, instanz: 3, achse: true}, soll: "=LK"}
  durchmesser_pruefen:
    - {was: Zentrierbohrung, feature: f3, nahe: ["=DW-TZ/2", "=AH+DZ/2", 0], soll: "=DZ"}
```

(`bohrung` mit `senkung` und `durch` ist live erprobt, Referenz Formplatte `f7`. Die Zentrierbohrung als Senkung statt
Ø 40 durch: mit Lochkreis 52 bliebe sonst zwischen Senkung M5 (r 21) und Bohrung (r 20) nur 1 mm Steg über die ganze
Wanddicke.)

`tests/referenz/motorhalter/motorhalter.yaml` anlegen:

```yaml
# Referenz Motorhalter (Spec 3c §11, Plan-Nachtrag GPLE60): Grundplatte (fixiert), Motorbock, Planetengetriebe
# Nanotec GPLE60-2S-32 als Kaufteil aus dem Katalog (swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml), 4 × ISO 4762
# M5 × 12 durch die Wand in die Flanschgewinde M5 des Getriebes, 2 × ISO 4762 M6 × 10 vom Fuß in die Grundplatte.
# Statisch; Getriebeachse ACHSHOEHE über der Grundplatten-Unterseite, Wellenende bündig mit der Plattenkante x = −80.
art: baugruppe
name: Motorhalter
eigenschaften: {Benennung: Motorhalter}
parameter: {ACHSHOEHE: 62}
komponenten:
  - {id: grundplatte, quelle: {teil: grundplatte.yaml}, fixiert: true}
  - {id: bock, quelle: {teil: motorbock.yaml}}
  - {id: getriebe, quelle: {kaufteil: "Nanotec GPLE60-2S-32"}}
  - {id: flanschschraube, quelle: {normteil: "ISO 4762 M5x12"}, je_position: {komponente: bock, feature: f4}}
  - {id: fussschraube, quelle: {normteil: "ISO 4762 M6x10"}, je_position: {komponente: bock, feature: f5}}
verknuepfungen:
  # Bock auf der Grundplatte: Fuß aufliegend, Senkung 1 über Gewinde 1, Seiten parallel
  - {id: v1, typ: deckungsgleich, a: {komponente: bock, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v2, typ: konzentrisch, a: {komponente: bock, feature: f5, instanz: 1, achse: true},
     b: {komponente: grundplatte, feature: f2, instanz: 1, achse: true}}
  - {id: v3, typ: parallel, a: {komponente: bock, feature: f1, flaeche: "+x"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+x"}, ausrichtung: gleich}
  # Getriebe: Abtriebsflansch an der Wand (Ebene vor Achse), Zentrierbund in der Zentrierbohrung, Drehlage parallel
  - {id: v4, typ: deckungsgleich, a: {komponente: getriebe, referenz: EINBAU_FLANSCH},
     b: {komponente: bock, feature: f2, flaeche: "+x"}, ausrichtung: entgegengesetzt}
  - {id: v5, typ: konzentrisch, a: {komponente: getriebe, referenz: EINBAU_ACHSE},
     b: {komponente: bock, feature: f3, instanz: 1, achse: true}, drehung_sperren: false}
  - {id: v6, typ: parallel, a: {komponente: getriebe, referenz: EINBAU_DREHLAGE}, b: {komponente: bock, ebene: vorne},
     ausrichtung: gleich}
  # Flanschschrauben: Kopf auf dem Senkungsgrund der Wand
  - {id: v7, typ: deckungsgleich, a: {komponente: flanschschraube, referenz: EINBAU_EBENE},
     b: {komponente: bock, feature: f4, instanz: je, flaeche: "-x"}, ausrichtung: gleich}
  - {id: v8, typ: konzentrisch, a: {komponente: flanschschraube, referenz: EINBAU_ACHSE},
     b: {komponente: bock, feature: f4, instanz: je, achse: true}}
  # Fußschrauben: Kopf auf dem Senkungsgrund des Fußes
  - {id: v9, typ: deckungsgleich, a: {komponente: fussschraube, referenz: EINBAU_EBENE},
     b: {komponente: bock, feature: f5, instanz: je, flaeche: "+y"}, ausrichtung: gleich}
  - {id: v10, typ: konzentrisch, a: {komponente: fussschraube, referenz: EINBAU_ACHSE},
     b: {komponente: bock, feature: f5, instanz: je, achse: true}}
pruefung:
  huellquader: [160, 102, 100]
  masse_pruefen:
    - {was: Achshöhe, von: {komponente: grundplatte, feature: f1, flaeche: "-y"},
       zu: {komponente: getriebe, referenz: EINBAU_ACHSE}, soll: "=ACHSHOEHE"}
    - {was: Getriebeflansch an der Wand, von: {komponente: getriebe, referenz: EINBAU_FLANSCH},
       zu: {komponente: bock, feature: f2, flaeche: "+x"}, soll: 0}
```

`tests/referenz/motorhalter/eingabe/beschreibung.md` anlegen:

~~~markdown
# Motorhalter (Referenz Stufe 3c)

Planetengetriebe Nanotec GPLE60-2S-32 (Kaufteil; Katalogeintrag `swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml`,
Datenblatt: Baureihenübersicht GPLE60 von nanotec.com) auf einem Motorbock, der auf einer Grundplatte 160 × 100 × 12 sitzt
(Stahl S235, 1.0038). An den Motoradapter des Getriebes (□ 60, NEMA 23) kommt später ein Schrittmotor; er gehört nicht zur
Referenz.

- Motorbock als Winkel: Fuß 75 × 10 × 60, Wand 10 × 90 × 60. Getriebeachse waagerecht, 50 über der Fußunterseite, also
  62 über der Grundplatten-Unterseite.
- Das Getriebe liegt mit dem Abtriebsflansch an der Wand an. Der Zentrierbund Ø 40 h7 sitzt in einer Zentrierbohrung
  Ø 40 × 5, die Abtriebswelle Ø 14 ragt durch einen Durchgang Ø 20 hinten aus der Wand; ihr Ende ist bündig mit der Kante
  der Grundplatte. Das Getriebe steht gerade (Seiten des □ 60 waagerecht und senkrecht), sein Lochbild 4 × M5 auf Ø 52
  liegt unter 45° und fluchtet mit den Bohrungen der Wand.
- Befestigung Getriebe: 4 × ISO 4762 M5 × 12 von der Wandrückseite in die Flanschgewinde M5 des Getriebes, Köpfe versenkt.
- Befestigung Bock: 2 × ISO 4762 M6 × 10 vom Fuß in Gewinde M6 der Grundplatte (Gewindetiefe 8), Köpfe versenkt.
- Alle Teile voll bestimmt, keine Überlappung außer den Gewindepaarungen, Einschraublänge nicht über der Gewindetiefe.
~~~

In `tests/referenz/test_referenzen.py` ersetzen:

```python
from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
REFERENZEN = Path(__file__).parent
```

durch:

```python
from swki.cli import main
from swki.kaufteile import quelle
from swki.kaufteile.eintrag import lade_eintrag
from swki.kaufteile.katalog import finde
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
REFERENZEN = Path(__file__).parent
KAUFTEILE = {"motorhalter": ["Nanotec GPLE60-2S-32"]}  # Referenz → Kaufteile, deren Original im Quellordner liegen muss
```

In `tests/referenz/test_referenzen.py` ersetzen:

```python
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)
```

durch:

```python
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def bereite_vor(ordner: str) -> None:
    """Vorbereitung ohne SolidWorks: Referenzen mit Kaufteilen brauchen das Original des Herstellers im Quellordner der
    Kaufteil-Bibliothek – es liegt nicht im Git (Nutzerentscheidung 2026-10-06). Fehlt es, scheitert der Test hier mit
    KAUFTEIL_QUELLE_FEHLT samt Download-URL aus dem Eintrag; weicht es ab, mit KAUFTEIL_QUELLE_ABWEICHEND."""
    for schluessel in KAUFTEILE.get(ordner, []):
        quelle.original(lade_rechner(), lade_eintrag(finde(schluessel)))
```

In `tests/referenz/test_referenzen.py` ersetzen:

```python
    ("zahnstangentrieb", "zahnstangentrieb.yaml"),
])
```

durch:

```python
    ("zahnstangentrieb", "zahnstangentrieb.yaml"),
    ("motorhalter", "motorhalter.yaml"),
])
```

In `tests/referenz/test_referenzen.py` ersetzen:

```python
    spec_pfad = auftrag / spec
    try:
```

durch:

```python
    spec_pfad = auftrag / spec
    bereite_vor(ordner)
    try:
```

`tests/live/test_live_motorhalter.py` anlegen:

```python
"""Live-Negativfall der Referenz Motorhalter (Spec 3c §11, Plan-Nachtrag GPLE60): zu lange Flanschschrauben ISO 4762
M5 × 16 – die Einschraublänge (16 − 4,6 = 11,4 mm) überschreitet Gewindetiefe und Bohrtiefe 10 des Kaufteil-Gewindes
(Nanotec GPLE60-2S-32). Erwartet genau die vier Mängel gewinde:flanschschraube.<i>; sonst nichts."""

import json
import shutil

import pytest
import yaml

from swki.cli import main
from swki.konfig import lade_rechner
from tests.referenz.test_referenzen import REFERENZEN, bereite_vor

pytestmark = pytest.mark.sw


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


def test_zu_lange_flanschschraube(capsys, tmp_path):
    auftrag = tmp_path / "NEG-MOTORHALTER"
    shutil.copytree(REFERENZEN / "motorhalter", auftrag)
    spec_pfad = auftrag / "motorhalter.yaml"
    spec = yaml.safe_load(spec_pfad.read_text(encoding="utf-8"))
    assert spec["komponenten"][3]["id"] == "flanschschraube"
    spec["komponenten"][3]["quelle"] = {"normteil": "ISO 4762 M5x16"}
    spec_pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    bereite_vor("motorhalter")
    try:
        assert _lauf(capsys, "validieren", str(spec_pfad))[0] == 0
        assert _lauf(capsys, "freigeben", str(spec_pfad))[0] == 0
        code, bau = _lauf(capsys, "bauen", str(spec_pfad))
        assert code == 0, bau
        code, bericht = _lauf(capsys, "pruefen", str(spec_pfad))
        assert code == 0, bericht
        assert {m["pruefung"] for m in bericht["maengel"]} == {f"gewinde:flanschschraube.{i}" for i in range(1, 5)}, \
            bericht["maengel"]
        assert all("Einschraublänge 11.40 mm größer als Gewindetiefe 10" in m["beschreibung"] for m in bericht["maengel"])
    finally:
        shutil.rmtree(lade_rechner().arbeitsordner / "NEG-MOTORHALTER", ignore_errors=True)
```

- [ ] **Step 4: Validieren ohne SolidWorks**

Run: `.venv\Scripts\python.exe -m pytest -q tests\referenz\test_motorhalter.py` → `1 passed`;
`.venv\Scripts\python.exe -m swki validieren tests\referenz\motorhalter\grundplatte.yaml` und `… motorbock.yaml` →
`"gueltig": true`, `"hinweise": []`. Ganze Suite: **932 passed, 141 deselected** (N9 + 9 / D9 + 3);
`… swki api pruefe-code swki spikes tests/live` → `"befunde": []`.

- [ ] **Step 5: Referenz live (frisches SolidWorks)**

BLOCKED Neustart an den Controller, dann:
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m pytest -m sw "tests/referenz/test_referenzen.py::test_referenz_besteht[motorhalter-motorhalter.yaml]" -q`
Expected: passed (der Test räumt seinen Arbeitsordner auf; die Einzelwerte prüft Step 6 am Prüfbericht des Auftrags:
`gewinde:flanschschraube.1…4` je `einschraublaenge` 7.4, `soll` 42.305, `gewindetiefe` 10; `gewinde:fussschraube.*`
`einschraublaenge` 6.4; `kaufteile` mit `gebaut` false (Cache aus Task 7N) und `gewinde_modell`
`{"flansch": {"modell": "kernloch", "durchmesser": 4.134}}`). Private Bytes (Spitze, 0,5 s) und Dauer notieren.
Mängel: Bauweg nachbessern (Verknüpfungen, Reihenfolge, `ausrichtung` von v4 nach `bezug.richtung` aus Task 7N Step 4),
nie Prüfwerte. Berührt das Getriebe den Fuß oder meldet `kollision` eine Überlappung Getriebe ↔ Bock: NEEDS_CONTEXT (die
Rechnung oben sagt 10 mm Abstand bzw. nur Berührung).

- [ ] **Step 6: Prüfer-Urteil (Controller)**

Auftrag `auftraege/REF-3C-MOTORHALTER/` (Kopie von `tests/referenz/motorhalter/`), `swki validieren`, `freigeben`, `bauen`,
`pruefen` (vorher frisches SolidWorks); Einzelwerte im Prüfbericht wie in Step 5 genannt; der **Controller** startet den Prüfer-Agenten mit Eingabe, allen freigegebenen Specs,
dem Eintrag `swki/wissen/kaufteile/nanotec/gple60-2s-32.freigegeben.yaml`, dem Datenblatt (Quellordner), Prüfbericht und
Bildern; Urteil unverändert nach `protokolle/motorhalter.lauf-<n>.pruefer.json`; `swki status`. Erwartet
`{"bestanden": true, "maengel": []}`. Auftrag und Arbeitsordner danach löschen.

- [ ] **Step 7: Negativfall (frisches SolidWorks)**

BLOCKED Neustart an den Controller, dann:
`$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_motorhalter.py --zeit 900`
Expected: `OK` (genau die Mängel `gewinde:flanschschraube.1` … `.4`, je „Einschraublänge 11.40 mm größer als Gewindetiefe 10
bzw. Bohrtiefe 10 mm“). Abweichung: Erwartung nicht abschwächen, NEEDS_CONTEXT.

- [ ] **Step 8: Commit**

```powershell
git add tests/referenz/motorhalter/grundplatte.yaml tests/referenz/motorhalter/motorbock.yaml tests/referenz/motorhalter/motorhalter.yaml tests/referenz/motorhalter/eingabe/beschreibung.md tests/referenz/test_motorhalter.py tests/referenz/test_referenzen.py tests/live/test_live_motorhalter.py
git commit -m "referenz: Motorhalter mit Planetengetriebe Nanotec GPLE60-2S-32, Regression, Negativfall zu lange Flanschschraube (Stufe 3c, Task 10N)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11N: Skills, Prüfer, CLAUDE.md, Design, Ergebnisse, Regression, Abnahme – Abweichungen von Task 11

Task 11 des Hauptplans gilt mit diesen Änderungen; alle dort nicht genannten Blöcke bleiben, wie sie sind. „Hauptplan-Block
… ändern“ heißt: den angegebenen Text **im neuen Inhalt** des Hauptplan-Blocks ersetzen, bevor der Block eingespielt wird.

- [ ] **Step 1: Skill `kaufteile` (neu, Hauptplan-Block `.claude/skills/kaufteile/SKILL.md`) ändern**

1. Kopf: `Vorlage: Muster-Getriebemotor
   `swki/wissen/kaufteile/swki-muster/gm42-10.yaml`, Referenz `tests/referenz/motorhalter/`.` →
   `Vorlage: Nanotec GPLE60-2S-32 `swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml` (echte Herstellerdatei, Datenblatt mit
   Seitenangaben), Referenz `tests/referenz/motorhalter/`.`
2. §2: `Hersteller ohne Leerzeichen (z. B. `NANOTEC`, `SKF`)` → `Hersteller ohne Leerzeichen, wie der Hersteller sich schreibt
   (z. B. `Nanotec`, `SKF`)`.
3. §2, nach dem Spiegelstrich `KAUFTEIL_IMPORT oder Flächenkörper/Körperfehler …` diese Spiegelstriche ergänzen:
   ~~~markdown
   - Reine Flächenmodelle (nur Flächenkörper, z. B. STEP mit `OPEN_SHELL`/`SHELL_BASED_SURFACE_MODEL`) ergeben den Mangel
     `import` – nicht reparieren, beim Hersteller ein anderes Modell (Volumenmodell) suchen bzw. den Nutzer darum bitten.
   - **Speicher:** Der erste STEP-Import einer SolidWorks-Sitzung kostet ~1,8–3 GB Private Bytes Spitze (Spike S15: +1,8 GB;
     GPLE60 `untersuchen`: 3,2 GB), eine Aufnahme mit Bildern bis ~5,4 GB. Vor `untersuchen`, `muster` und `hole` die
     Private Bytes prüfen und ab ~3 GB SolidWorks selbst neu starten (Skill `baugruppe` §4).
   ~~~
4. §3, Punkt 1: Beispiel des Belegs → `belege: {d1: {art: datenblatt, datei: <name>, url: <url>, seite: n}}` und ergänzen:
   „Herstellerdateien (STEP, Datenblatt) kommen nie ins Git: `original.bezug: {art: url, url: <Download>, datum: "<JJJJ-MM-TT>"}`,
   `datenblatt: {datei, url}`; fehlt die Datei auf einem Rechner, nennt `KAUFTEIL_QUELLE_FEHLT` die URL.“
5. §4, nach dem `gewinde:`-Spiegelstrich ergänzen:
   ~~~markdown
   - Gewindelöcher modellieren Hersteller oft mit dem Kerndurchmesser D1 nach ISO 724 statt mit dem Bohrer-Ø: swki nimmt
     jeden Ø von D1 bis zum Tabellen-Kernloch (± 0,01) als Modell `kernloch`, den Nenn-Ø als `nenn`; der gemessene Ø steht
     im Cache und rechnet die Gewindepaarung. Die Gewindetiefe nennen Datenblätter selten: aus der Mantellänge des
     Gewindezylinders in der Diagnose (Fläche / (π·Ø)), ohne `beleg` (Hinweis `nicht_belegt`); den Boden (Spitze oder eben)
     live prüfen.
   - Die Drehlage (`ebene_durch_achse`) so legen, dass das Teil in der Baugruppe mit `parallel` zu einer Hauptebene
     ausgerichtet werden kann – meist durch die Mitte einer Gehäuseseite (Symmetrieebene des Lochbilds), nicht durch die
     Diagonale.
   ~~~
6. Tabelle der Codes, Zeile `KAUFTEIL_QUELLE_FEHLT` → `| `KAUFTEIL_QUELLE_FEHLT` | Meldung nennt bei `bezug.art: url` die
   Download-URL: Nutzer gibt die Datei (bzw. erlaubt den Download), dann `untersuchen` (SHA-256 muss passen) |`.
7. §6, letzter Spiegelstrich: `(Modell `kernloch` → Ringvolumen, `nenn` → keine Überlappung)` →
   `(Modell `kernloch` → Ringvolumen bis zum gemessenen Ø, `nenn` → keine Überlappung über 0,01 mm³)`.
8. **Nur nach Nutzer-OK (offene Frage 2):** §1 `Claude lädt nichts von Herstellerportalen, legt keine Konten an …` →
   `Claude lädt Dateien nur mit ausdrücklichem OK des Nutzers je Datei (öffentliche Direktlinks, ohne Konto, ohne
   Anmeldung) und legt keine Konten an …`; gleichlautend in CLAUDE.md (Punkt 3 unten).

- [ ] **Step 2: Skill `baugruppe` und Prüfer (Hauptplan-Blöcke) ändern**

1. Skill `baugruppe`, Block „Nicht genormte Kaufteile nie als Teil-Spec …“: `(Skill `kaufteile`, Abschnitt 8 unten)` →
   `(Skill `kaufteile`; Regeln für Baugruppen in Abschnitt 8 dieses Skills)` (Ruling B11 – der Skill `kaufteile` hat keinen
   Abschnitt 8).
2. Skill `baugruppe`, neuer Abschnitt `## 8. Kaufteile (Stufe 3c)`, Passungs-Spiegelstrich: `rechnet die Gewindepaarung mit der
   Gewindetiefe des Eintrags` → `rechnet die Gewindepaarung mit der Gewindetiefe des Eintrags und dem gemessenen Gewinde-Ø
   (Bericht: Spalte „Gewindemodell“)`.
3. `.claude/agents/pruefer.md`, Kaufteil-Checkliste: nach Punkt 4 ergänzen:
   ~~~markdown
   5. Gewindegruppen: `gewinde:<gruppe>` nennt `modell` und `durchmesser`; `kernloch` mit Ø zwischen D1 nach ISO 724 und dem
      Bohrer-Ø (M5: 4,134…4,2) bzw. `nenn` mit dem Nenn-Ø ist in Ordnung. Eine Gewindetiefe aus der STEP ohne Beleg ist kein
      Mangel, wenn der Eintrag sie als „nicht belegt“ ausweist.
   ~~~
   und in Punkt 1 `Drehlage durch das Lochbild` → `Drehlage durch das Lochbild (Gewindeposition oder Symmetrieebene des
   Lochbilds)`.

- [ ] **Step 3: CLAUDE.md und Design (Hauptplan-Blöcke) ändern, Spec nachziehen**

1. CLAUDE.md, neuer Abschnitt „Kaufteile (Stufe 3c)“, letzter Spiegelstrich →
   `- Regressions-Suite enthält den Motorhalter mit Nanotec GPLE60-2S-32 (`tests/referenz/motorhalter/`). Die
   Herstellerdatei liegt nur im Quellordner der `kaufteilbibliothek`; fehlt sie, meldet die Regression
   `KAUFTEIL_QUELLE_FEHLT` mit der Download-URL (Nutzer fragen, dann `swki kaufteil untersuchen`).`
2. CLAUDE.md, zusätzlicher Block (Ruling B16) – In `CLAUDE.md` ersetzen:
   ~~~markdown
   - Erzeugte SolidWorks-Dateien kommen nicht ins Git.
   ~~~
   durch:
   ~~~markdown
   - Erzeugte SolidWorks-Dateien kommen nicht ins Git (einzige Ausnahme: Test-STEP
     `tests/referenz/motorhalter/muster/gm42-10.step`, Spike S15). Herstellerdateien (STEP, Datenblätter) auch nicht.
   ~~~
3. CLAUDE.md, Abschnitt „Kaufteile“, erster Spiegelstrich `keine Downloads durch Claude` – unverändert lassen, außer der
   Nutzer bejaht offene Frage 2 (dann wie Step 1 Punkt 8).
4. Design `2026-09-26-solidworks-ki-design.md`, Tabellenzeile 3c, Spalte „fertig, wenn“:
   `Muster-Getriebemotor aufgenommen und Referenz *Motorhalter* besteht (Code-Prüfungen und Prüfer), Negativfälle, Abnahme mit
   echter Herstellerdatei dokumentiert; bisherige Referenzen bestehen weiter` →
   `Kaufteil Nanotec GPLE60-2S-32 (echte Herstellerdatei) aufgenommen und Referenz *Motorhalter* besteht (Code-Prüfungen und
   Prüfer), Negativfälle; bisherige Referenzen bestehen weiter`.
5. Spec 3c (§2, §11, §15) – In `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` ersetzen:

   ~~~markdown
   | Referenz | **Motorhalter** (statisch) mit Muster-Getriebemotor aus eigener Baugruppe; Negativfälle; zusätzlich eine **echte Herstellerdatei** des Nutzers als einmalige Abnahme |
   ~~~

   durch:

   ~~~markdown
   | Referenz | **Motorhalter** (statisch) mit Muster-Getriebemotor aus eigener Baugruppe; Negativfälle; zusätzlich eine **echte Herstellerdatei** des Nutzers als einmalige Abnahme. *Nachgezogen bei der Umsetzung (Nutzerentscheidung 2026-10-06):* Katalogeintrag und Motorhalter verwenden die echte Herstellerdatei Nanotec GPLE60-2S-32 (Planetengetriebe); das Muster bleibt interne Testdatei |
   ~~~

   In `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` ersetzen:

   ~~~markdown
   - **Katalogeintrag** `swki/wissen/kaufteile/swki-muster/gm42-10.yaml` (Beleg: das Muster-Datenblatt `muster/datenblatt.md`,
     aus den Specs abgeleitet), Freigabe, Prüfer-Urteil im Git.
   ~~~

   durch:

   ~~~markdown
   - **Katalogeintrag** `swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml` (*nachgezogen bei der Umsetzung, Nutzerentscheidung
     2026-10-06*): echtes Herstellerteil Nanotec GPLE60-2S-32, Belege aus dem Hersteller-Datenblatt (Baureihenübersicht,
     Seiten 248/249), Freigabe und Prüfer-Urteil im Git. STEP und Datenblatt liegen **nicht im Git**, nur im Quellordner der
     Kaufteil-Bibliothek; der Eintrag nennt `original.bezug: {art: url, url, datum}` und die SHA-256. Der Muster-Getriebemotor
     wird kein Katalogeintrag; `muster/` bleibt interne Testdatei (Spike S15, Live-Tests der Aufnahme, Unit-Test-Beispiele).
   ~~~

   In `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` ersetzen:

   ~~~markdown
   - **Abnahme mit echter Herstellerdatei:** Der Nutzer gibt eine STEP-Datei eines realen Kaufteils (seine Wahl, z. B. Motor oder
     Lager) und ggf. das Datenblatt; Claude nimmt sie mit dem vollen Ablauf auf (untersuchen, Eintrag, Freigabe durch den Nutzer,
     Prüfer, hole) und dokumentiert Diagnose-Kennzahlen, Zeiten, Speicher und Befunde in den Ergebnissen. Datei und Eintrag kommen
     nicht ins Git (Eintrag nur, wenn der Nutzer es will), nicht in die Regression.
   ~~~

   durch:

   ~~~markdown
   - **Abnahme mit echter Herstellerdatei:** Der Nutzer gibt eine STEP-Datei eines realen Kaufteils (seine Wahl, z. B. Motor oder
     Lager) und ggf. das Datenblatt; Claude nimmt sie mit dem vollen Ablauf auf (untersuchen, Eintrag, Freigabe durch den Nutzer,
     Prüfer, hole) und dokumentiert Diagnose-Kennzahlen, Zeiten, Speicher und Befunde in den Ergebnissen. *Nachgezogen bei der
     Umsetzung:* Die Aufnahme des Nanotec GPLE60-2S-32 erfüllt diese Abnahme (Nutzerwahl, voller Ablauf); Eintrag im Git und in
     der Regression (Nutzerentscheidung), die Herstellerdatei nicht.
   ~~~

   In `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` ersetzen:

   ~~~markdown
   - Der Muster-Getriebemotor ist aufgenommen (Freigabe, Prüfer-Urteil „bestanden“, Cache) und die Referenz *Motorhalter* besteht
   ~~~

   durch:

   ~~~markdown
   - Das Kaufteil Nanotec GPLE60-2S-32 ist aufgenommen (Freigabe, Prüfer-Urteil „bestanden“, Cache) und die Referenz *Motorhalter* besteht
   ~~~

   (Die Blöcke stehen hier eingerückt; eingespielt werden sie ohne die drei führenden Leerzeichen der Listeneinrückung.)

- [ ] **Step 4: Regression (Controller fährt sie per Skript)** – wie Hauptplan Step 3, mit: Live-Tests der Kaufteile
  `test_live_kaufteile` (Muster), `test_live_kaufteil_hole` (GPLE60), `test_live_motorhalter`; vor jedem Kaufteil- und
  Baugruppen-Test frisches SolidWorks. Vorher prüfen, dass `quellen/nanotec/gple60-2s-32.stp` vorhanden ist (sonst scheitern
  Motorhalter und `test_live_kaufteil_hole` mit `KAUFTEIL_QUELLE_FEHLT` – das ist gewollt). Soll Unit-Suite
  **932 passed, 141 deselected** (N9 + 9 / D9 + 3).

- [ ] **Step 5: Abnahme mit echter Herstellerdatei** – statt Hauptplan Step 4: **Vorschlag** „durch Task 7N erfüllt“
  (Nanotec GPLE60-2S-32: Nutzerwahl, Hersteller-STEP und -Datenblatt, voller Ablauf untersuchen → Eintrag → Nutzerfreigabe →
  muster → Prüfer → urteil → hole, Diagnose-Kennzahlen vorhanden). Der **Controller fragt den Nutzer** (eine Frage,
  Empfehlung „ja, erfüllt“); bei „nein“ gilt Hauptplan Step 4 mit einer weiteren Datei. Die Kennzahlen kommen in die
  Ergebnisse: Dateigröße 0,082 MB, 55 Flächen, 3 Körper, Import 5,3 s, Dauer 12,8 s, Private Bytes 425 → 3240 (Spitze) →
  940 MB, dazu die Werte aus `muster` und `hole` (Task 7N).

- [ ] **Step 6: Ergebnisse und Spec-Nachzug** – wie Hauptplan Step 5, zusätzlich in `docs/stufe3c/ergebnisse.md`:
  Nutzerentscheidungen 2026-10-06 (Muster nicht freigegeben, GPLE60, Dateien nicht ins Git, Gewinde-Ø-Bereich), die
  verworfenen Kandidaten (ST4118M1804-A Flächenmodell → Fix-N; DB42 mit M3 – M3 fehlt in `bohrungsnormen.yaml` und
  ISO 4762, offener Punkt), Befund G1 und Task G, Untergrenze 0,01 mm³ (gemessenes Rauschen aus Task 10N), Präz. 26
  (Drehlage), `IMPORTWEG_VERSION` 2, Testzahlen je Task (Tabelle oben).

- [ ] **Step 7: Commit** – Hauptplan Step 6 unverändert (die Spec-Datei ist dort schon enthalten).

---

## Annahmen für die Live-Schritte (bestätigen oder NEEDS_CONTEXT)

| # | Annahme | bestätigt in | sonst |
|---|---|---|---|
| L1 | Flanschgewinde: Mantel Ø 4,134 von z −59,5 bis −49,5, Boden ohne ebene Fläche (Spitze) → `gewindetiefe` = `tiefe` = 10 | 7N Step 1 | Nutzer nach Gewindetiefe fragen; Eintrag vor der Freigabe ändern |
| L2 | Alle `nahe`-Punkte liegen auf der **begrenzten** Fläche (≤ 0,1 mm) | 7N Step 4 (`muster`) | Mangel `einbau:*`/`mass:*`/`durchmesser:*`: Punkt korrigieren (vor neuer Freigabe mit Nutzer) |
| L3 | `EINBAU_FLANSCH` → `bezug.richtung` [0, 0, −1] (wie S15-7) | 7N Step 4 | Motorhalter `v4` `ausrichtung: gleich` (Ledger) |
| L4 | Massenüberschreibung wirkt bei 3 Körpern (S15-9-Weg: alle Körper auswählen) | 7N Step 4 (`masse` 1.1, `ueberschrieben` true) | Ledger, Prüfung `masse` |
| L5 | Gewindemodell `kernloch` mit Ø 4,134 (4 Stellen) | 7N Step 4/6 | Abweichung > 0,0005: NEEDS_CONTEXT |
| L6 | Rauschvolumen der Interferenzprüfung bei Berührung ≤ 0,01 mm³ | 10N Step 5 (bei `nenn` nicht direkt messbar – Kollision Ø 40 Bund ↔ Tasche) | Untergrenze nicht still erhöhen; Nutzer fragen |
| L7 | Getriebe steht mit □ 60 aufrecht (Drehlage-Ebene ±y ‖ `vorne`), 10 mm über dem Fuß | 10N Step 5/6 (Bilder, `kollision`) | NEEDS_CONTEXT |
| L8 | Einschraublänge der Flanschschrauben genau 7,4 (Senkungstiefe M5 5,4 aus SW-Tabelle) | 10N Step 5/7 | Erwartung nicht abschwächen, NEEDS_CONTEXT |

## Offene Fragen an den Nutzer (stellt der Controller, je eine Frage mit Empfehlung)

1. **Drehlage des GPLE60 (Präz. 26):** `EINBAU_DREHLAGE` als Symmetrieebene des Lochbilds (Mitte einer □-60-Seite) statt
   durch eine Gewindeposition? Empfehlung: **ja** – nur so passen „parallel zu `vorne`“ und „Senkungen unter 45°“ bei
   aufrecht stehendem Getriebe zusammen; die Diagonale würde das Getriebe auf die Spitze stellen und auf dem Fuß aufsetzen.
   Zeitpunkt: mit der Freigabefrage in Task 7N Step 3.
2. **Downloads in Skill und CLAUDE.md:** Die Regel „keine Downloads durch Claude“ an die Praxis dieser Stufe anpassen
   („nur mit ausdrücklichem Nutzer-OK je Datei, öffentliche Direktlinks, ohne Konto“)? Empfehlung: **ja**, weil der Nutzer es
   2026-10-06 so gehandhabt hat und `KAUFTEIL_QUELLE_FEHLT` jetzt eine URL nennt. Zeitpunkt: Task 11N Step 1.
3. **Abnahme:** Gilt die Aufnahme des GPLE60 als „Abnahme mit echter Herstellerdatei“ (Spec §11/§15)? Empfehlung: **ja**.
   Zeitpunkt: Task 11N Step 5.
