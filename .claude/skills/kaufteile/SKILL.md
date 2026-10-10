---
name: kaufteile
description: Nicht genormte Kaufteile von Herstellern (Motor mit Flansch, Kugellager, Pneumatikzylinder, Führungswagen …) als STEP aufnehmen – untersuchen, Belege für Kennmaße, Katalogeintrag, Freigabe durch den Nutzer, Prüfer, holen – und in Baugruppen verwenden. Verwenden, wenn der Nutzer eine Herstellerdatei gibt oder eine Baugruppe ein nicht genormtes Kaufteil braucht. Genormte Schrauben, Muttern, Scheiben, Stifte nie hierüber (Skill normteile).
---

# Kaufteile (Stufe 3c)

Spec: `docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md` (Abweichungen der Umsetzung:
`docs/stufe3c/ergebnisse.md`). Befehle `.venv\Scripts\python.exe -m swki …` (JSON). Vorlage: Nanotec GPLE60-2S-32
`swki/wissen/kaufteile/nanotec/gple60-2s-32.yaml` (echte Herstellerdatei, Datenblatt mit Seitenangaben), Referenz
`tests/referenz/motorhalter/`. Die Aufnahme des GPLE60 (voller Ablauf mit echter Herstellerdatei) ist die Abnahme der Stufe.

## 1. Abgrenzung
- **Nur nicht genormte Kaufteile.** Genormte Verbindungselemente kommen immer über `swki normteil hole` (Skill
  `normteile`); `validieren` weist Einträge ab, deren Benennung oder Bestellnummer eine Norm der Normtabellen nennt
  (`KAUFTEIL_GENORMT`). Fehlt eine Normgröße: Normtabelle erweitern, nie eine STEP holen.
- **Nur STEP** (`.step`/`.stp`). Andere Formate: den Nutzer bitten, beim Hersteller die STEP zu laden.
- **Dateien kommen vom Nutzer, Downloads nur mit OK.** Claude lädt Herstellerdateien nur über öffentliche Direktlinks ohne
  Konto und nur mit ausdrücklichem OK des Nutzers je Datei (Name, Quelle und Größe nennen); Konten und Anmeldungen bei
  Herstellerportalen sind ausgeschlossen. Die Datei wird nur gelesen; swki kopiert sie unverändert in den Quellordner der
  Kaufteil-Bibliothek.
- Eine STEP wird **ein Teil** (Mehrkörper erlaubt). Bewegliche Baueinheiten (Schiene + Wagen, Zylinder + Kolbenstange)
  braucht es als getrennte STEP-Dateien – sonst den Nutzer darum bitten.

## 2. Untersuchen
`swki kaufteil untersuchen <step> --hersteller <H> --bestellnummer <B> [--datenblatt <datei>]`
- Hersteller ohne Leerzeichen, wie der Hersteller sich schreibt (z. B. `Nanotec`, `SKF`), Bestellnummer genau wie beim
  Hersteller.
- Ausgabe: `diagnose` (Körper, Flächenkörper, `koerperfehler`, Hüllquader, Volumen, `zylinder`/`ebenen` mit Punkten
  `nahe`, Dateigröße, Importzeit, Speicherspitze, Bilder) und `geruest` des Eintrags. Bilder ansehen.
- `KAUFTEIL_IMPORT` oder Flächenkörper/Körperfehler: nicht reparieren – den Nutzer um ein anderes Modell bitten.
- Reine Flächenmodelle (nur Flächenkörper, z. B. STEP mit `OPEN_SHELL`/`SHELL_BASED_SURFACE_MODEL`, auch ältere
  Inventor-Exporte) ergeben den Mangel `import` – nicht reparieren, beim Hersteller ein anderes Modell (Volumenmodell)
  holen bzw. den Nutzer darum bitten.
- **Speicher:** Der erste STEP-Import einer SolidWorks-Sitzung kostet ~1,8–2,8 GB Private Bytes Zuwachs (Spike S15: +1,8 GB;
  GPLE60 `untersuchen`: Spitze 3,2 GB), `untersuchen`/`muster` mit Bildern erreichen ~3,2–5,4 GB Spitze. Vor `untersuchen`,
  `muster` und `hole` die Private Bytes prüfen und ab ~3 GB SolidWorks selbst neu starten (Skill `baugruppe` §4).
- `KAUFTEIL_QUELLE_ABWEICHEND`: Die Datei unterscheidet sich vom Original im Quellordner bzw. im Eintrag. Den Nutzer fragen:
  neue Herstellerversion als **eigener Eintrag** oder **Eintrag ändern** (`--neue-version` legt die Datei neben das alte
  Original; dann `original` im Eintrag anpassen, neu validieren, Nutzer-OK, freigeben, neues Prüfer-Urteil).
- Große Modelle (viele Flächen, lange Importzeit) sind erlaubt; Kennzahlen dem Nutzer nennen.

## 3. Belege für Kennmaße und Masse
1. Datenblatt vom Nutzer → daraus (`belege: {d1: {art: datenblatt, datei: <name>, url: <url>, seite: n}}`, Datei mit
   `--datenblatt` in den Quellordner). Herstellerdateien (STEP, Datenblatt) kommen nie ins Git:
   `original.bezug: {art: url, url: <Download>, datum: "<JJJJ-MM-TT>"}`, `datenblatt: {datei, url}`; fehlt die Datei auf
   einem Rechner, nennt `KAUFTEIL_QUELLE_FEHLT` die URL.
2. Sonst selbst suchen, nur öffentliche Seiten ohne Anmeldung, Herstellerseite zuerst. In Suchanfragen nur Hersteller und
   Bestellnummer, keine Daten des Nutzers.
3. Belegregel: eine Herstellerquelle (`hersteller` mit `url` und `abgerufen`, oder `datenblatt`) oder `nutzer` genügt
   allein; Händler- und Drittseiten (`haendler`) nur mit ≥ 2 verschiedenen Domains. Widersprechen sich Quellen: den Wert
   nicht übernehmen, den Nutzer fragen (eine Frage, mit Empfehlung).
4. Nichts gefunden: nur das Belegte prüfen; der Rest bleibt ohne `beleg` („nicht belegt“ in Eintrag und Bericht).
   **Werte aus der STEP-Diagnose sind nie Kennmaße** – nur Ankerpunkte, `pruefung.volumen` und unbelegte Gewindetiefen.

## 4. Eintrag schreiben
`swki/wissen/kaufteile/<hersteller-ordner>/<bestellnummer-datei>.yaml` (Ordner und Datei kleingeschrieben, wie
`untersuchen` sie in `eintrag` nennt). Aus dem `geruest`, dazu:
- `benennung`, `material` (Name der SW-Materialdatenbank, Pflicht), `masse: {kg, beleg}` wenn bekannt, `eigenschaften`.
- `einbau` mit `EINBAU_<NAME>`: `zylinder: {nahe, durchmesser, senkrecht_zu?}` (Achse), `ebene: {nahe, normale}`
  (Anlagefläche, Normale aus dem Material), `ebene_durch_achse: {achse, nahe}` (Drehlage, z. B. durch eine Lochmitte).
  `nahe` liegt auf der Fläche (Punkte aus der Diagnose); Ø und Normale sind die Gegenprobe.
- `gewinde: {<gruppe>: {groesse, gewindetiefe, tiefe, normale, positionen, beleg?}}` für Gewindelöcher, in die Normteile
  geschraubt werden (Eintrittspunkte, `normale` aus dem Material).
- Außengewinde (z. B. Kolbenstange): Gruppe mit `art: aussen` (Vorgabe `innen`). `positionen` = Gewindeanfang auf der
  Achse (Körperseite, z. B. Stangenbund), `normale` = Richtung zur Gewindespitze, `gewindetiefe` = nutzbare
  Gewindelänge, `tiefe` = Länge des Gewindezylinders (≥ `gewindetiefe`). Die Aufnahme sucht den koaxialen Zylinder mit
  Nenn-Ø (Modell `nenn`); fehlt er, ist das eine Abweichung mit den gemessenen Ø. Keine Schraube hinein (`validieren`).
- Gewindelöcher modellieren Hersteller oft mit dem Kerndurchmesser D1 nach ISO 724 statt mit dem Bohrer-Ø: swki nimmt
  jeden Ø von D1 bis zum Tabellen-Kernloch (± 0,01) als Modell `kernloch`, den Nenn-Ø als `nenn`; der gemessene Ø steht
  im Cache und rechnet die Gewindepaarung (M5: D1 4,134 bis Bohrer-Ø 4,2). Die Gewindetiefe nennen Datenblätter selten:
  aus der Mantellänge des Gewindezylinders in der Diagnose (Fläche / (π·Ø)), ohne `beleg` (Hinweis `nicht_belegt`); den
  Boden (Spitze oder eben) live prüfen.
- Die Drehlage (`ebene_durch_achse`) so legen, dass das Teil in der Baugruppe mit `parallel` zu einer Hauptebene
  ausgerichtet werden kann – meist durch die Mitte einer Gehäuseseite (Symmetrieebene des Lochbilds), nicht durch die
  Diagonale.
- Die Richtung einer Bezugsachse aus einer Zylinderfläche legt SolidWorks fest und ist kein Kriterium (Spec §4.2: Lage und
  Ø; `konzentrisch` ohne Angabe nutzt die nächste Ausrichtung), ebenso die Normale einer `ebene_durch_achse`. Maßgeblich
  sind die Normalen der `ebene`-Referenzen (`bezug.richtung`) und die Lage: die Ebenennormale der Bezugsebene muss
  gleichsinnig zur Flächennormale sein, sonst Mangel `einbau:<name>`.
- `pruefung`: `huellquader {soll, tol, beleg}`, `volumen` aus dem Gerüst, `durchmesser_pruefen`, `masse_pruefen` (Messpunkte
  `referenz`, `gewinde`+`instanz`, `flaeche {nahe, normale}`, `punkt`).
- Datumsangaben in Anführungszeichen (`"2026-10-07"`).
`swki validieren <eintrag.yaml>` bis `gueltig`; `hinweise` (`nicht_belegt`, `masse_aus_material`) dem Nutzer nennen.

## 5. Freigabe, Prüfer, holen
- Dem Nutzer zeigen: Eintrag (Kennmaße mit Belegen), Diagnosebilder, was jede Einbaureferenz bedeutet. Erst nach
  ausdrücklichem OK: `swki freigeben <eintrag.yaml>` (deckt den ganzen Eintrag ab).
- `swki kaufteil muster "<H> <B>"` → Prüfer-Agent (`subagent_type: pruefer`) mit `eintrag` (freigegebene Kopie),
  `datenblatt`, `pruefbericht`, Bildern → Urteil als rohes JSON in eine Datei →
  `swki kaufteil urteil "<H> <B>" <datei> --freigabe-pruefsumme <x>` (`freigabe_pruefsumme` aus `muster`). Der Prüfbericht
  nennt die gelesenen Eigenschaften, das Gewindemodell mit Ø je Gruppe und `bezug.richtung`.
- `swki kaufteil hole "<H> <B>"` → Cache-Treffer (`gebaut: false`) oder Aufnahme mit Prüfung. `swki kaufteil liste
  [--veraltet]` zeigt Freigabe, Urteil, Cache.

| Code | Vorgehen |
|---|---|
| `KAUFTEIL_FORMAT` | nur STEP; Nutzer um STEP bitten |
| `KAUFTEIL_UNBEKANNT` | vorhandene Schlüssel nennen; neues Kaufteil → Abschnitt 2 |
| `KAUFTEIL_QUELLE_FEHLT` | Meldung nennt bei `bezug.art: url` die Download-URL: Nutzer gibt die Datei (bzw. erlaubt den Download), dann `untersuchen` (SHA-256 muss passen) |
| `KAUFTEIL_QUELLE_ABWEICHEND` | Abschnitt 2 |
| `KAUFTEIL_IMPORT` | Modell defekt oder nicht importierbar (auch reines Flächenmodell) – Nutzer fragen, anderes Modell |
| `KAUFTEIL_UNGEPRUEFT` | Prüfer-Ablauf oben |
| `KAUFTEIL_PRUEFUNG` | Mängel lesen: `einbau:<name>` / `gewinde:<gruppe>` (Punkt falsch oder Gegenprobe verfehlt), `koerper`, `huellquader`, `mass:*` – Eintrag nach Rücksprache korrigieren (Nutzer-OK, neue Freigabe); Sollwerte nie an Messwerte anpassen |
| `KAUFTEIL_GENORMT` | Befund von `validieren`: Benennung oder Bestellnummer nennen eine Norm einer Normtabelle (auch `DIN 912-12`) – Normteil über `swki normteil hole` (Skill `normteile`), nie als STEP |
| `KAUFTEIL_NICHT_FREIGEGEBEN` | Befund von `validieren` (Baugruppe verweist auf einen Eintrag ohne Freigabe): Eintrag freigeben lassen (Abschnitt 5) |
| `FREIGABE_FEHLT` / `FREIGABE_VERALTET` | Nutzer fragen, neu freigeben |

## 6. In Baugruppen
- `quelle: {kaufteil: "<H> <B>"}`; Referenzen nur `{komponente, referenz: EINBAU_*}` und
  `{komponente, gewinde, instanz, achse: true}`; `je_position: {komponente, gewinde}` für Schrauben je Gewindeposition.
  Die Instanzen entstehen in der Reihenfolge der `positionen` des Eintrags. **Noch nicht live erprobt:** `{gewinde,
  instanz}` und `je_position: {gewinde}` sind unit-getestet (Attrappen), der Motorhalter nutzt sie nicht – erster Einsatz
  mit Prüfer und Sichtprobe.
- Ausrichtung: Flächen- und Bezugsebenen-Normalen wie im Prüfbericht des Kaufteils (`einbau:<name>` → `bezug.richtung`).
  Bei `konzentrisch` auf `EINBAU_ACHSE` eines Kaufteils keine `ausrichtung` angeben (die Achsrichtung legt SolidWorks fest).
- `drehung_sperren` ist bei Kaufteilen Vorgabe; wer die Drehlage über eine `ebene_durch_achse` verknüpft, setzt an der
  konzentrischen Verknüpfung `drehung_sperren: false` (Hinweis `drehlage_doppelt`).
- Die Baugruppen-Freigabe schützt den Eintrag mit: Ändert sich ein Eintrag, meldet `bauen` `FREIGABE_VERALTET` mit dem
  Kaufteil – Nutzer fragen, Baugruppe neu freigeben.
- Schrauben im Kaufteil-Gewinde: Gewindepaarung wie bei Eigenteilen (Modell `kernloch` → Ringvolumen bis zum gemessenen Ø,
  `nenn` → keine Überlappung über 0,01 mm³). Toleranz im Kaufteil-Gewinde (innen und außen): ± eine Steigung
  Gewindering (Senkung am Eintritt, Freistich, Auslauf der Herstellergeometrie); mehr ist ein Mangel. Beim Außengewinde
  den Gewindeanfang auf den Beginn des Auslaufs legen, nicht auf einen Freistich davor.
- Regeln für Baugruppen im Einzelnen: Skill `baugruppe` §8.
