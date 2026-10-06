# Stufe 3c – Kaufteile (STEP-Import nicht genormter Kaufteile von Herstellern)

Ergänzung zu [2026-09-26-solidworks-ki-design.md](2026-09-26-solidworks-ki-design.md) (§3 Versionsregeln, §4 Spezifikation,
§6 Prüfung, §8 Normteile, §11 Stufen), [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md)
(Bibliothek als Cache, Einbaureferenzen, Prüfer je Vorlage) und
[2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md) (Komponentenquellen, Kopie in den
Lauf-Ordner, Referenzen, Gewindepaarung, Freigabe, Änderungserkennung). Stand 2026-10-06, mit dem Nutzer abgestimmt;
bei der Planung nachgezogen (Plan `docs/superpowers/plans/2026-10-06-kaufteile-step-import.md`): §4.1, §4.2, §4.3, §4.5,
§5.1, §5.3, §6.1, §8.1, §10, §11, §12.

## 1. Ziel

Nicht genormte Kaufteile (Motor mit Flansch, Kugellager, Pneumatikzylinder, Führungswagen …) kommen als STEP-Datei des
Herstellers einmal in einen Katalog: swki importiert die Datei, legt benannte Einbaureferenzen an, prüft das Teil gegen
belegte Kennmaße aus dem Datenblatt und legt es in einem lokalen Cache ab. Baugruppen verwenden Kaufteile wie Normteile über
`quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}` und verknüpfen sie nur über ihre `EINBAU_*`-Referenzen.

Der Mensch greift an einer Stelle je Kaufteil ein: der **Freigabe des Katalogeintrags** (Kennmaße und Bedeutung der
Einbaureferenzen). Genormte Verbindungselemente bleiben ausnahmslos bei `swki normteil hole`.

## 2. Entscheidungen (mit dem Nutzer, 2026-10-06)

| Frage | Entscheidung |
|---|---|
| Formate | **nur STEP** (AP203/AP214/AP242, `.step`/`.stp`); Parasolid später nachrüstbar; kein natives SLDPRT/SLDASM des Herstellers (Versionsregel, fremde Bäume), kein IGES (oft nur Flächen) |
| Mehrteilige STEP | **immer ein Teil**: Baugruppen-STEP wird als **Mehrkörperteil** importiert, die erwartete Körperzahl steht im Eintrag und wird geprüft. Bewegliche Baueinheiten (Schiene + Wagen, Zylinder + Kolbenstange) liefert der Nutzer als **getrennte** STEP-Dateien; Aufteilen importierter Geometrie ist nicht Umfang |
| Herkunft der Datei | Der Nutzer nennt einen Pfad; swki **liest nur** und legt eine unveränderte Kopie des Originals in der Kaufteil-Bibliothek ab (nicht im Git). Claude legt keine Konten an und meldet sich nirgends an |
| Quelle und Cache | wie 3a: **Katalogeintrag (Git) + Original sind die Quelle**, die `.sldprt` je SW-Jahr ist ein Cache und jederzeit neu erzeugbar |
| Aufnahme und Freigabe | `untersuchen` → Claude schreibt den Eintrag → **Nutzerfreigabe des Eintrags** → Prüfer-Urteil je Eintragsversion → `hole` |
| Einbaureferenzen | **Punktanker plus Gegenprobe** (Zylinder: Punkt + Ø; Ebene: Punkt + Normale), daraus benannte Bezugsachsen/-ebenen; Namen frei mit Präfix `EINBAU_`; Drehlage als dritte Referenz (Bauweise im Spike) |
| Lage | **STEP-Koordinaten unverändert**; kein Verschieben/Drehen von Körpern; Baum = Import + Bezugsgeometrie |
| Prüfung | Import fehlerfrei, Körperzahl, nur Volumenkörper, Hüllquader, Kennmaße (`durchmesser_pruefen`, `masse_pruefen`), Referenzen zueinander, **Volumen als Fingerabdruck**, Bilder mit Referenzen |
| Masse | **Material Pflicht; Masse aus dem Datenblatt überschreibt, wenn bekannt** (SW-Massenüberschreibung); sonst Bericht „Masse aus Material geschätzt“ |
| Baugruppe | `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}`, Kopie in den Lauf-Ordner, Verknüpfung nur über `EINBAU_*`; **die Baugruppen-Freigabe enthält die Freigabe-Prüfsumme des Eintrags** |
| Überlappung | **streng**; Gewindebohrungen des Kaufteils als `gewinde`-Gruppen im Eintrag, die Gewindepaarung aus 3b gilt mit; `je_position` auch auf Kaufteil-Gewinde; jede andere Überlappung ist ein Mangel |
| Große Modelle | **nur messen und berichten** (Dateigröße, Flächen, Körper, Importzeit, Speicherspitze); keine Grenze |
| Referenz | **Motorhalter** (statisch) mit Muster-Getriebemotor aus eigener Baugruppe; Negativfälle; zusätzlich eine **echte Herstellerdatei** des Nutzers als einmalige Abnahme |
| Befehle | eigene Gruppe **`swki kaufteil`**, Paket `swki/kaufteile/`, Skill `kaufteile`; `normteil aufnehmen` entfällt im Design |
| Schutzregel | `validieren` des Eintrags weist Kaufteile ab, deren Benennung oder Bestellnummer eine Norm der Normtabellen nennt (`KAUFTEIL_GENORMT`) |
| Einordnung | **Stufe 3c** in Design §11; §8 bekommt einen Stand-Absatz |
| Kennmaße und Masse | Datenblatt mitgeliefert → daraus; sonst **sucht Claude selbst** auf öffentlichen Seiten; nichts gefunden → geprüft wird nur, was belegt ist (kein Mindestumfang), Eintrag und Bericht vermerken „Kennmaße nicht belegt“. Werte nur aus der STEP zählen nie als Kennmaß |
| Belege | **Herstellerquelle allein genügt** (Domain des Herstellers; mitgeliefertes Datenblatt gilt als Herstellerquelle); Händler-/Drittquellen nur mit **≥ 2 unabhängigen** übereinstimmenden; Widerspruch → Wert nicht übernehmen, Nutzer fragen |
| Bauweise | **Katalogeintrag = Spezifikation `art: kaufteil`** (eine YAML-Datei je Kaufteil); `validieren`/`freigeben` verzweigen nach `art`, Freigabe-Kopie und Prüfsumme wie bei Teilen |

## 3. Bausteine

```
schema/kaufteil.schema.json                       Schema des Katalogeintrags (art: kaufteil)
swki/wissen/kaufteile/<hersteller>/<datei>.yaml   Katalogeintrag (Git), daneben freigabe.json, <datei>.freigegeben.yaml,
                                                  <datei>.pruefer.json (Prüfer-Urteil zur Freigabe-Prüfsumme)
swki/kaufteile/                                   Paket: Schlüssel, Laden/Validieren (Belege, Schutzregel), Quelle und
                                                  Prüfsummen, Import und Diagnose, Einbaureferenzen, Prüfung, Cache, Befehle
<kaufteilbibliothek>/quellen/<hersteller>/        Originale (STEP, Datenblatt), unverändert, versionsunabhängig, nicht im Git
<kaufteilbibliothek>/<sw_jahr>/<schluessel>.sldprt + .json   Cache: Import + Einbaureferenzen, geprüft
schema/baugruppe.schema.json                      + quelle kaufteil, je_position/Referenz auf Kaufteil-Gewinde
swki/baugruppe/…                                  Laden, Plausibilität, Passung, Freigabe, Bau, Gewindepaarung, Bericht
.claude/skills/kaufteile/                         neuer Skill
.claude/agents/pruefer.md                         + Checkliste Kaufteil
tests/referenz/motorhalter/                       Referenz (Teil-Specs, Baugruppe, Muster-Motor, Eintrag)
spikes/s15_kaufteile.py                           Spike S15 (§12)
```

`config/rechner.yaml` erhält `kaufteilbibliothek` (Vorgabe `%USERPROFILE%\.swki\kaufteile`); `setup\einrichten.ps1` und
`config/rechner.beispiel.yaml` werden ergänzt. Die Kaufteil-Bibliothek ist getrennt von der Normteilbibliothek (dort liegt
nur Selbstgebautes). Gespeichert wird in ihr nur: unveränderte Kopien der vom Nutzer genannten Originale (`quellen/`) und von
`swki kaufteil hole` geprüfte Teile (`<sw_jahr>/`). Die Modulnamen folgen dem Bestand; der Plan nennt die genauen Dateien.

## 4. Katalogeintrag (`art: kaufteil`)

Eine YAML-Datei je Kaufteil. Beispiel Muster-Getriebemotor. **Zahlen, Punkte und Namen nur zur Veranschaulichung; die echte
Referenz legt der Plan fest.**

```yaml
art: kaufteil
hersteller: SWKI-MUSTER                 # Anzeigename; Ordnername = Kleinbuchstaben, Zeichen außer [a-z0-9-] → "-"
bestellnummer: GM42-10                  # exakt wie beim Hersteller
benennung: Getriebemotor GM42, i = 10 (Muster)
original:
  datei: GM42-10.step                   # Name im Quellordner <kaufteilbibliothek>/quellen/<hersteller>/
  sha256: 3f5c…                         # des Originals
  bezug: {art: nutzer, datum: 2026-10-07, hinweis: "Download Herstellerportal durch den Nutzer"}
datenblatt: {datei: GM42.pdf}           # optional; Datei im Quellordner oder url
koerper: 2
material: "1.0038 (S235JRG2)"           # Pflicht, Name der SW-Materialdatenbank
masse: {kg: 0.62, beleg: [d1]}          # optional; überschreibt die Masse aus dem Material
eigenschaften: {Benennung: Getriebemotor GM42-10}   # Hersteller, Bestellnummer, Ersteller setzt swki
belege:
  d1: {art: datenblatt, datei: GM42.pdf, seite: 2}
  h1: {art: hersteller, url: "https://…", abgerufen: 2026-10-07}
einbau:
  EINBAU_ACHSE:    {zylinder: {nahe: [5, 0, 80], durchmesser: 10, senkrecht_zu: EINBAU_FLANSCH}}   # Wellenachse
  EINBAU_FLANSCH:  {ebene: {nahe: [25, 25, 0], normale: [0, 0, 1]}}          # Anlagefläche hinter dem Zentrierbund
  EINBAU_DREHLAGE: {ebene_durch_achse: {achse: EINBAU_ACHSE, nahe: [21.21, 21.21, 0]}}   # Bauweise: Spike S15c
gewinde:
  flansch: {groesse: M5, gewindetiefe: 8, tiefe: 10, normale: [0, 0, 1], beleg: [d1],
            positionen: [[21.21, 21.21, 0], [-21.21, 21.21, 0], [-21.21, -21.21, 0], [21.21, -21.21, 0]]}
pruefung:
  huellquader: {soll: [60, 60, 103], tol: 0.1, beleg: [d1]}
  volumen: {soll: 221345.678, toleranz_prozent: 0.01}         # Fingerabdruck aus untersuchen (kein Kennmaß)
  durchmesser_pruefen:
    - {was: Wellen-Ø, nahe: [5, 0, 90], soll: 10, tol: 0.01, referenz: EINBAU_ACHSE, beleg: [d1]}
    - {was: Zentrierbund-Ø, nahe: [20, 0, -1.5], soll: 40, tol: 0.01, referenz: EINBAU_ACHSE, beleg: [d1]}
  masse_pruefen:
    - {was: Wellenüberstand, von: {referenz: EINBAU_FLANSCH}, zu: {flaeche: {nahe: [0, 0, 100], normale: [0, 0, 1]}},
       soll: 100, tol: 0.05, beleg: [d1]}
    - {was: Lochkreis-Teilung, von: {gewinde: flansch, instanz: 1}, zu: {gewinde: flansch, instanz: 2}, soll: 42.43,
       tol: 0.05, beleg: [d1]}
```

### 4.1 Felder

- `hersteller`, `bestellnummer`, `benennung` Pflicht. **Schlüssel** `"<hersteller> <bestellnummer>"` (Leerzeichen trennt am
  ersten Leerzeichen; Hersteller ohne Leerzeichen). Katalogordner und Dateiname klein geschrieben (Hersteller:
  `[a-z0-9-]`, Bestellnummer: `[a-z0-9_-]`, andere Zeichen ersetzt), Bibliotheksschlüssel `<Hersteller>_<Bestellnummer>`
  auf `[A-Za-z0-9-]` abgebildet. *Nachgezogen bei der Planung:* statt einer Kollisionsprüfung meldet `validieren`, wenn
  die Datei nicht an dem Platz liegt, der aus Hersteller und Bestellnummer folgt (zwei Einträge können so nie dieselbe
  Datei belegen).
- `original` Pflicht: Dateiname im Quellordner, SHA-256, `bezug` (wie die Datei zum Nutzer kam: `nutzer` | `url` mit Datum).
- `koerper` (≥ 1), `material` Pflicht; `masse` optional.
- `belege`: benannte Quellen mit `art` ∈ `hersteller` | `datenblatt` | `haendler` | `nutzer`; `url` oder `datei` (+ `seite`),
  `abgerufen` bei `url`. `datenblatt` und `hersteller` sind Herstellerquellen; `nutzer` = vom Nutzer im Chat genannt.
- `einbau`: Name `EINBAU_<NAME>` → genau eine Bauform (§4.2).
- `gewinde`: optional, benannte Gruppen (§4.3).
- `pruefung`: wie §4.4. Jedes Kennmaß (`huellquader`, `durchmesser_pruefen`, `masse_pruefen`, `masse`, `gewinde`-Maße)
  trägt `beleg` (Liste von Beleg-IDs) oder fehlt; `volumen` trägt nie einen Beleg (Fingerabdruck).

### 4.2 Einbaureferenzen

Je Name genau eine der Bauformen; Punkte in STEP-Koordinaten (mm), Toleranz der Ortung `toleranzen.anker_mm` (0,1 mm):

| Bauform | Geometrie im Teil | Gegenprobe |
|---|---|---|
| `zylinder: {nahe, durchmesser}` | Bezugsachse der Zylinderfläche, auf deren Mantel `nahe` liegt | Ø auf 0,01 mm |
| `ebene: {nahe, normale}` | Bezugsebene deckungsgleich zur ebenen Fläche durch `nahe` | Normale (Winkel ≤ 0,01°, Vorzeichen zählt) |
| `ebene_durch_achse: {achse, nahe}` | Bezugsebene, die die Bezugsachse `achse` enthält und durch `nahe` geht (z. B. Mitte eines Gewindelochs) | `nahe` nicht auf der Achse (Abstand > 1 mm) |

*Nachgezogen bei der Planung:* Kein Treffer (`REFERENZ_NICHT_GEFUNDEN`), mehrere (`REFERENZ_MEHRDEUTIG`) und eine verfehlte
Gegenprobe sind **Mängel der Prüfung** `einbau:<name>` mit Ist- und Sollwert, kein Abbruch (alle Mängel eines Eintrags auf
einmal); `hole` meldet sie als `KAUFTEIL_PRUEFUNG`. Ein eigener Code `KAUFTEIL_EINBAU` entfällt. Die Bezugsgeometrie heißt im
Teil wie im Eintrag (`EINBAU_ACHSE` …), damit Baugruppen sie wie bei Normteilen per Name auswählen (Spike S12b). Mindestens
eine Einbaureferenz ist Pflicht.

### 4.3 Gewindegruppen

`<gruppe>: {groesse, gewindetiefe, tiefe, normale, positionen, beleg?}`:

- `groesse` aus `swki/wissen/bohrungsnormen.yaml` (Gewinde), `gewindetiefe`/`tiefe` in mm, `normale` zeigt aus dem Material
  (Eintrittsseite), `positionen`: Eintrittspunkte in STEP-Koordinaten.
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
- Ohne `beleg` stammen `gewindetiefe`/`tiefe` nur aus der STEP: zulässig (sie werden für die Gewindepaarung gebraucht), aber
  „nicht belegt“ im Bericht.

### 4.4 `pruefung`

- `huellquader: {soll, tol, beleg?}` (Vorgabe `tol` 0,1 mm, Herstellermodelle sind oft vereinfacht).
- `volumen: {soll, toleranz_prozent}`: Soll aus `untersuchen`, Vorgabe 0,01 % (gleiche Datei, gleicher Import); belegt, dass ein
  neu erzeugter Cache (andere SW-Version, anderer Rechner) dieselbe Geometrie hat.
- `durchmesser_pruefen: [{was, nahe, soll, tol?, referenz?, beleg?}]`: Zylinderfläche durch `nahe` über **alle** Körper (kein
  `feature`), optional koaxial zu einer Einbauachse.
- `masse_pruefen: [{was, von, zu, soll, tol?, beleg?}]` mit Messpunkten `{referenz: EINBAU_*}`, `{gewinde: <gruppe>, instanz: n}`
  (Achse der Position), `{flaeche: {nahe, normale}}` (ebene Fläche, Gegenprobe Normale), `{punkt: [x, y, z]}`.
- Lage der Referenzen zueinander: jede `ebene_durch_achse` enthält ihre Achse (immer geprüft). Eine `zylinder`-Referenz kann
  `senkrecht_zu: <EINBAU_*>` (eine `ebene` desselben Eintrags) tragen, z. B. Wellenachse ⟂ Flanschebene; geprüft unter
  `einbau:<name>` (Winkel zwischen Achse und Ebenennormale ≤ 0,01°). `masse_pruefen` misst nur Abstände, keine Winkel.
- Werte sind Zahlen (keine Parameter, keine Ausdrücke); der Eintrag hat keine `parameter`.

### 4.5 Validieren (ohne SolidWorks)

`swki validieren <eintrag.yaml>` (Weiche nach `art`):

1. Schema `schema/kaufteil.schema.json`.
2. **Belege:** jede Beleg-ID existiert; je Kennmaß gilt die Regel „Herstellerquelle (`hersteller`, `datenblatt`) oder `nutzer`
   allein genügt, sonst ≥ 2 verschiedene `haendler`-Belege (verschiedene Domains)“; sonst Befund `BELEG_UNZUREICHEND`.
3. **Schutzregel:** nennen `benennung` oder `bestellnummer` eine Norm einer Normtabelle (`norm` oder `ersetzt`, z. B.
   „ISO 4762“, „DIN 912“; Schreibweisen wie in `swki normteil hole`), Befund `KAUFTEIL_GENORMT` mit Verweis auf `normteil hole`.
4. `material` nicht leer; `einbau` mit ≥ 1 Eintrag; `ebene_durch_achse.achse` nennt eine `zylinder`-Referenz desselben Eintrags;
   Gewindegrößen in `bohrungsnormen.yaml`; Messpunkte nennen vorhandene Referenzen/Gruppen/Instanzen.
5. Hinweise: Kennmaße ohne `beleg` (`art: nicht_belegt`), gar kein belegtes Kennmaß (`art: kennmasse_nicht_belegt`), keine
   `masse` (`art: masse_aus_material`). *Nachgezogen bei der Planung:* statt „Datei-Kollision“ der Befund zur Lage (§4.1).

Ausgabe wie bei Teilen (`gueltig`, `befunde`, `hinweise`, `pruefsumme`).

### 4.6 Freigabe

`swki freigeben <eintrag.yaml>` (Weiche nach `art`) – **nur nach ausdrücklichem OK des Nutzers**. Die Prüfsumme deckt den
**ganzen Eintrag** ab (ein Kaufteil hat keinen Bauweg: Punkte, Gegenproben und Kennmaße sind die Anforderung). `freigabe.json`
liegt im Herstellerordner, die Kopie `<datei>.freigegeben.yaml` daneben; beide nie ändern. Ohne gültige Freigabe verweigern
`kaufteil muster` und `kaufteil hole` mit `FREIGABE_FEHLT` bzw. `FREIGABE_VERALTET`.

## 5. Befehle und Ablauf

```
swki kaufteil untersuchen <step> --hersteller <h> --bestellnummer <b> [--datenblatt <datei>]
swki validieren <eintrag.yaml>          (Weiche)
swki freigeben  <eintrag.yaml>          (Weiche, nach Nutzer-OK)
swki kaufteil muster "<h> <b>"          (Musterteil mit Bildern für den Prüfer)
swki kaufteil urteil "<h> <b>" <urteil.json> --freigabe-pruefsumme <p>
swki kaufteil hole   "<h> <b>"
swki kaufteil liste [--veraltet]
```

### 5.1 `untersuchen`

1. Endung `.step`/`.stp`, sonst `KAUFTEIL_FORMAT`. Die Datei wird nur gelesen.
2. SHA-256 bilden. Quellordner `<kaufteilbibliothek>/quellen/<hersteller>/`: existiert dort `<b>.<endung>` mit gleicher
   SHA-256 → nichts kopieren; mit anderer → `KAUFTEIL_QUELLE_ABWEICHEND` (beide Prüfsummen; eine neue Herstellerversion wird als
   eigener Eintrag oder durch bewusstes Ändern des Eintrags aufgenommen, §7). Sonst Kopie anlegen (`shutil.copy2`); ebenso das
   Datenblatt. Existiert schon ein Katalogeintrag, muss die SHA-256 zu `original.sha256` passen (sonst
   `KAUFTEIL_QUELLE_ABWEICHEND`); so stellt ein anderer Rechner das Original wieder her.
3. Import der **Kopie** (§6.1) in ein neues Dokument; nichts wird in die Bibliothek gespeichert. Ordner
   `<arbeitsordner>/KAUFTEILE/<schluessel>/lauf-<n>/` (*nachgezogen bei der Planung:* gleiche Laufzählung wie `muster` und
   `hole`, statt `untersuchung-<n>`); die Diagnose steht dort als `diagnose.json`.
4. Diagnose (JSON): Dateigröße, Importzeit, Private Bytes vorher/Spitze/nachher, Körper (Anzahl, Art Volumen/Fläche),
   Ergebnis der Importdiagnose, Flächenzahl, Hüllquader, Volumen, Schwerpunkt, **zylindrische Flächen** (Ø, Achspunkt,
   Richtung, Länge, ein Punkt auf dem Mantel; gleiche Achse und Ø zusammengefasst), **ebene Flächen** (Normale, Punkt, Fläche;
   die größten zuerst, Liste begrenzt auf 50 je Art), Screenshots Iso/Vorne/Oben/Rechts.
5. Ausgabe zusätzlich ein **Gerüst** des Eintrags (`original` mit SHA-256, `koerper`, `pruefung.volumen`), das Claude
   ergänzt. `untersuchen` schreibt nie in den Katalog.

### 5.2 Eintrag schreiben, freigeben, Prüfer

- Claude schreibt den Eintrag aus Diagnose und Belegen (Skill `kaufteile`): Datenblatt mitgeliefert → daraus; sonst selbst
  auf öffentlichen Seiten suchen (Herstellerseite zuerst; keine Anmeldung, keine Konten, keine Daten des Nutzers außer
  Hersteller und Bestellnummer in Suchanfragen); nichts gefunden → nur Belegtes, Rest „nicht belegt“. Werte nur aus der
  Diagnose dürfen nur als Ankerpunkte, `volumen` und unbelegte Gewindetiefen stehen.
- `swki validieren` ohne Befund → Claude legt dem Nutzer Eintrag, Diagnosebilder und Belege vor → nach OK `swki freigeben`.
- `swki kaufteil muster` baut das Teil wie `hole` (§5.3, Schritte 2–6) mit Bildern im Arbeitsordner, ohne Cache; Claude startet
  den Prüfer-Agenten (§9); sein Urteil legt `swki kaufteil urteil` als `<datei>.pruefer.json` ab, gebunden an die
  Freigabe-Prüfsumme. Ohne bestandenes Urteil zur aktuellen Freigabe verweigert `hole` mit `KAUFTEIL_UNGEPRUEFT`.

### 5.3 `hole`

1. Schlüssel auflösen (`KAUFTEIL_UNBEKANNT` mit den Einträgen des Herstellers bzw. allen Herstellern), Freigabe und Urteil
   prüfen.
2. **Cache-Prüfsumme** über Freigabe-Prüfsumme, `original.sha256` und `IMPORTWEG_VERSION` (Konstante im Code, wird bei jeder
   Änderung am Import- oder Referenzweg erhöht). Liegt in `<kaufteilbibliothek>/<sw_jahr>/` eine Datei mit gleicher Prüfsumme
   und bestandener Prüfung → Pfad zurückgeben (`gebaut: false`).
3. Original im Quellordner: fehlt → `KAUFTEIL_QUELLE_FEHLT` (Nutzer gibt die Datei erneut, `untersuchen`; bei
   `original.bezug.art: url` nennt die Meldung die Download-URL mit Datum – *nachgezogen bei der Umsetzung*: Herstellerdateien
   liegen nicht im Git); SHA-256 ≠ `original.sha256` → `KAUFTEIL_QUELLE_ABWEICHEND`.
4. Import (§6.1) in den Arbeitsordner (Auftrag `KAUFTEILE`, Laufnummer wie bei Normteilen); liefert SolidWorks kein Dokument
   → `KAUFTEIL_IMPORT`.
5. Einbaureferenzen und Gewindegruppen orten, Gegenproben, Bezugsgeometrie anlegen (§6.2); Material, Massenüberschreibung,
   Eigenschaften (`Benennung`, `Hersteller`, `Bestellnummer`, `Ersteller`). Ein Fehler beim Einrichten (z. B.
   `MATERIAL_UNBEKANNT`, Bezugsgeometrie nicht erzeugt) bricht mit seinem Code ab.
6. Prüfung (§6.3), Bilder; Speichern im Laufordner.
7. Bestanden → `.sldprt` in den Cache kopieren, `<schluessel>.json` schreiben (Schlüssel, Cache-Prüfsumme, Prüfergebnis,
   Gewindemodell je Gruppe mit gemessenem Ø (§4.3), Kennzahlen der Diagnose, Datum, SW-Version). Nicht bestanden →
   `KAUFTEIL_PRUEFUNG` (Mängel,
   Laufordner), nichts im Cache.
8. Ausgabe `{schluessel, pfad, gebaut, pruefung}`.

`liste` zeigt Einträge, Freigabe- und Urteilsstand und Cache-Dateien je SW-Jahr; `--veraltet` markiert Cache-Dateien mit
abweichender Prüfsumme. Gelöscht wird nichts automatisch.

## 6. Import, Referenzen, Prüfung (SolidWorks)

### 6.1 Import

- Import über die STEP-Importdaten (`GetImportFileData`, `LoadFile4` mit **4 Parametern** laut Index; oder `OpenDoc6` – Spike
  S15a). Baugruppen-STEP als **Mehrkörperteil** (`swImportNeutralAssemblyStructureMapping_e` = 2, `MultibodyPart`).
- **3D Interconnect aus:** sonst behält das Teil einen externen Verweis auf die Originaldatei (API-Hilfe zu `LoadFile4`), und der
  Lauf-Ordner wäre nicht mehr in sich geschlossen. Spike S15a belegt, dass das gespeicherte Teil keine externe Referenz hat.
- Alle verstellten SolidWorks-Optionen (3D Interconnect, Strukturabbildung, ggf. Einheit, Importdiagnose) liest swki vorher,
  setzt sie nur für den Import und stellt sie in `finally` wieder her. Die Werte stehen im Protokoll.
- **Importdiagnose nur lesen, nicht reparieren.** *Nachgezogen bei der Planung:* `IPartDoc.ImportDiagnosis` repariert laut
  API-Hilfe und wird nie aufgerufen; die automatische Importdiagnose ist während des Imports aus. Gelesen werden
  `IBody2.Check3` je Volumenkörper (Fehlerzahl) und die Zahl der Flächenkörper; beides ist die Prüfung `import` (Mangel mit
  Anzahl, §6.3), die Diagnose von `untersuchen` nennt sie. Reparieren wäre ein Eingriff in die Herstellergeometrie; der
  Nutzer holt dann ein anderes Format/Modell beim Hersteller.
- Die importierten Features bleiben unverändert; Name im Baum wie von SolidWorks vergeben (deutsche Oberfläche, nicht
  angefasst).

### 6.2 Referenzen

- Flächen über alle Körper sammeln (vorhandene Topologie-Helfer), `nahe` mit dem Anker-Auflöser orten, Gegenprobe (§4.2).
- `zylinder` → Bezugsachse aus der Zylinderfläche (`InsertAxis2` mit ausgewählter Fläche), `ebene` → Bezugsebene deckungsgleich
  (`InsertRefPlane`), `ebene_durch_achse` → Bezugsebene durch Achse und Punkt (Spike S15c: über eine Skizzenpunkt-Hilfe oder
  die Achse der Gewindeposition); umbenennen auf den Namen im Eintrag. Danach Rebuild ohne Fehler.
- Gewindegruppen erzeugen **keine** Features; ihre Achsen und Eintrittsebenen werden in Prüfung und Baugruppe aus dem Eintrag
  und der georteten Zylinderfläche berechnet.

### 6.3 Prüfung

Code-Prüfungen über die vorhandene Teil-Bewertung (Bewertung mit einer aus dem Eintrag abgeleiteten Prüfspezifikation):

| Prüfung | Soll |
|---|---|
| `rebuild` | ohne Fehler |
| `import` | Importdiagnose ohne Befund, nur Volumenkörper |
| `koerper` | = `koerper` des Eintrags |
| `huellquader` | Soll ± `tol` |
| `volumen` | Fingerabdruck ± `toleranz_prozent` |
| `durchmesser:<was>`, `mass:<was>` | Soll ± `tol` (Vorgabe 0,01 mm) |
| `einbau:<name>` | Gegenprobe (Ø, Normale, Achse in Ebene) und – bei `senkrecht_zu` – Lage zueinander |
| `gewinde:<gruppe>.<i>` | Zylinder gefunden, Ø = Kernloch oder Nenn-Ø |
| `material`, `eigenschaften` | gesetzt |
| `masse` | mit Überschreibung: gelesene Masse = `masse.kg` (relativ 1e-6); ohne: berichtet „aus Material geschätzt“ (`ok: None`) |

Skizzen gibt es nicht (keine Bestimmtheitsprüfung). Bilder Iso/Vorne/Oben/Rechts mit eingeblendeten Bezugsachsen/-ebenen
(Spike S15h); der Prüfbericht nennt die Diagnose-Kennzahlen (Dateigröße, Flächen, Importzeit, Speicherspitze) und je Kennmaß
den Beleg oder „nicht belegt“.

### 6.4 Gewindepaarung mit Kaufteilen

Die Gewindepaarung aus 3b (Spec 3b §9.3) gilt auch für Gewindegruppen von Kaufteilen: Eintrittsebene = Position mit `normale`;
Einschraublänge wie bisher; Mangel, wenn sie `gewindetiefe` oder `tiefe` überschreitet; Soll des Volumens = Ring zwischen Nenn-
und **gemessenem** Ø (Gewindemodell der Aufnahme, §4.3) über die Einschraublänge (Modell `kernloch`, Toleranz wie bisher 1 %,
mindestens 0,01 mm³) bzw. **keine Überlappung** (Modell `nenn`: Schraube und Gewindeloch berühren sich nur; jede Überlappung
über 0,01 mm³ ist ein Mangel); Gewindemodell unbekannt → `ok: null` mit Hinweis. *Nachgezogen bei der Umsetzung
(2026-10-06):* gemessener Ø statt Tabellen-Kernloch; absolute Untergrenze 0,01 mm³, damit Rechenrauschen bei Soll 0 kein
Mangel ist. Jede andere Überlappung mit einem Kaufteil ist ein Mangel; Überlappungen zwischen
Körpern **eines** Kaufteils prüft die Baugruppe nicht (eine Komponente).

## 7. Neue Herstellerversion, Änderungen

- Eine geänderte Herstellerdatei für dieselbe Bestellnummer ist eine Änderung der Anforderung: `untersuchen` meldet
  `KAUFTEIL_QUELLE_ABWEICHEND`. Der Nutzer entscheidet: **neuer Eintrag** (andere Bestellnummer/Revision im Dateinamen) oder
  **Eintrag ändern** (Original im Quellordner wird nicht überschrieben, sondern als `<b>.<sha8>.<endung>` daneben abgelegt;
  `original` im Eintrag zeigt darauf; neue Freigabe, neues Urteil; Baugruppen mit diesem Kaufteil melden `FREIGABE_VERALTET`).
  `untersuchen --neue-version` legt die Datei so ab; ohne die Option wird nie etwas überschrieben.
- Kopien im Lauf-Ordner sind wie alle gespeicherten Dateien über die SHA-256 im Protokoll geschützt (`MANUELL_GEAENDERT`,
  Spec 3b §8). Eine manuelle Änderung an einer Cache-Datei fällt bei `liste --veraltet` nicht auf (Prüfsumme über Eintrag und
  Original, nicht über die Datei); der Cache-Eintrag hält deshalb zusätzlich die SHA-256 der `.sldprt`, und `hole` baut neu,
  wenn sie abweicht.

## 8. Baugruppen

### 8.1 Format

```yaml
komponenten:
  - {id: motor, quelle: {kaufteil: "SWKI-MUSTER GM42-10"}}
  - {id: flanschschraube, quelle: {normteil: "ISO 4762 M5x16"}, je_position: {komponente: bock, feature: f4}}
verknuepfungen:
  - {id: v1, typ: konzentrisch, a: {komponente: motor, referenz: EINBAU_ACHSE},
     b: {komponente: bock, feature: f3, instanz: 1, achse: true}, drehung_sperren: false}
  - {id: v2, typ: deckungsgleich, a: {komponente: motor, referenz: EINBAU_FLANSCH},
     b: {komponente: bock, feature: f1, flaeche: "+x"}, ausrichtung: entgegengesetzt}
  - {id: v3, typ: parallel, a: {komponente: motor, referenz: EINBAU_DREHLAGE}, b: {komponente: bock, ebene: vorne},
     ausrichtung: gleich}
```

- `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}` (Schlüssel wie §4.1). Kein `variante`.
- **Referenzen** auf Kaufteile nur `{komponente, referenz: EINBAU_*}` und neu `{komponente, gewinde: <gruppe>, instanz, achse:
  true}` (Achse einer Gewindeposition); keine `feature`-, `ebene`- oder `nahe`-Referenzen in fremde Geometrie.
- **`je_position: {komponente, gewinde: <gruppe>}`** (neu, alternativ zu `feature`): eine Instanz je Position der Gruppe;
  `instanz: je` in Verknüpfungen wie bisher.
- `drehung_sperren`: Vorgabe `true`, wenn eine Seite ein Normteil **oder Kaufteil** ist. Verknüpft eine spätere Verknüpfung die
  Drehlage desselben Kaufteils (`EINBAU_DREHLAGE` o. ä.), muss `drehung_sperren: false` stehen; sonst Hinweis
  `art: drehlage_doppelt` (wäre überbestimmt).
- *Nachgezogen bei der Planung:* Gewindepositionen gibt es nur in Verknüpfungen und `je_position`, nicht als Messpunkte von
  `pruefung.masse_pruefen` der Baugruppe (das Schema der Messpunkte bleibt unverändert).

### 8.2 Validieren

Zusätzlich zu Spec 3b §5: Eintrag vorhanden (`KAUFTEIL_UNBEKANNT`), gültig (`validieren` des Eintrags ohne Befund), freigegeben
(`KAUFTEIL_NICHT_FREIGEGEBEN`), Urteil zur aktuellen Freigabe (`KAUFTEIL_UNGEPRUEFT`) – alle als Befunde mit Komponenten-ID;
`referenz` im `einbau` des Eintrags; `gewinde`-Gruppe und Instanz vorhanden; `je_position`-Paarungsregel unverändert.
**Passung:** `konzentrisch` zwischen `EINBAU_ACHSE` eines ISO 4762 M*x* und einer Kaufteil-Gewindeposition verlangt
`groesse` M*x*; ISO 7089/4032 auf Kaufteil-Gewinde ist ein Befund.

### 8.3 Freigabe

Die Baugruppen-Prüfsumme (Spec 3b §6) enthält zusätzlich je verwendetem Kaufteil die **Freigabe-Prüfsumme seines Eintrags**
(Schlüssel `kaufteil:<Schlüssel>`). Ändert sich ein Eintrag nach der Baugruppen-Freigabe, verweigert `swki bauen` mit
`FREIGABE_VERALTET` und nennt das Kaufteil. Cache-Prüfsummen gehören nicht zur Freigabe.

### 8.4 Bauen, Prüfen, Bericht

- `bauen`: je Kaufteil `kaufteil hole` (Cache oder Neuaufnahme unter Auftrag `KAUFTEILE`), Datei als `<schluessel>.sldprt` in den
  Lauf-Ordner kopiert; Fehlercodes mit Komponenten-ID weitergereicht; Protokoll mit Schlüssel und Cache-Prüfsumme. Die Baugruppe
  verweist nie auf Bibliothek oder Quellordner.
- `pruefen`: Stückliste zählt Kaufteile; **keine Teilprüfung** (geschah bei der Aufnahme; Cache-Prüfsumme im Bericht);
  Gewindebohrungen der Kaufteile gehen in die Gewindepaarung (§6.4); Gesamtmasse mit überschriebener Masse.
- `bericht`: Kaufteile mit Hersteller, Bestellnummer, Cache-Prüfsumme, Masse (überschrieben / aus Material) und „Kennmaße nicht
  belegt“, wo zutreffend.

## 9. Prüfer

`.claude/agents/pruefer.md` erhält eine **Kaufteil-Checkliste**: Referenzen sitzen auf den beschriebenen Flächen (Bilder),
Richtung von Normalen und Achsen plausibel (Flanschnormale zeigt vom Gehäuse weg …), Kennmaße belegt und mit dem Datenblatt
vereinbar, Masse plausibel, Körperzahl plausibel, kein genormtes Verbindungselement. Eingabe: freigegebener Eintrag,
Datenblatt (falls vorhanden), Prüfbericht, Bilder; keine Protokolle, keine Diagnose-Rohdaten außer im Prüfbericht. Urteilsform
unverändert; Mängel nennen `einbau:<name>`, `gewinde:<gruppe>` oder die Prüfungs-ID. In Baugruppen gilt die Checkliste aus 3b;
Kaufteile werden dort nur auf Lage und Verbindung beurteilt.

## 10. Fehlerfälle

JSON mit `code`, Exit 1. Neu:

| Code | Wann | Inhalt |
|---|---|---|
| `KAUFTEIL_FORMAT` | Endung nicht `.step`/`.stp` | erlaubte Endungen |
| `KAUFTEIL_UNBEKANNT` | Schlüssel ohne Eintrag | vorhandene Einträge des Herstellers bzw. Hersteller |
| `KAUFTEIL_QUELLE_FEHLT` | Original nicht im Quellordner | erwarteter Pfad, Hinweis `untersuchen`; bei `original.bezug.art: url` Download-URL und Datum |
| `KAUFTEIL_QUELLE_ABWEICHEND` | SHA-256 weicht ab | beide Prüfsummen, Pfade |
| `KAUFTEIL_IMPORT` | SolidWorks liefert beim Import kein Dokument | Fehlercode (`swFileLoadError_e`) |
| `KAUFTEIL_UNGEPRUEFT` | kein bestandenes Prüfer-Urteil zur Freigabe | Schlüssel, Freigabe-Prüfsumme |
| `KAUFTEIL_PRUEFUNG` | Prüfung nicht bestanden (auch Gegenproben `einbau:*`/`gewinde:*`, Körperfehler `import`) | Mängel, Laufordner |
| Befunde `validieren` | `KAUFTEIL_GENORMT`, `BELEG_UNZUREICHEND`, `KAUFTEIL_NICHT_FREIGEGEBEN`, `KAUFTEIL_UNGEPRUEFT` | Norm, Wert, Komponente |

*Nachgezogen bei der Planung:* `KAUFTEIL_EINBAU` entfällt (§4.2); Diagnosebefunde und Flächenkörper sind der Mangel `import`.

`REFERENZ_NICHT_GEFUNDEN`/`REFERENZ_MEHRDEUTIG`, `FREIGABE_FEHLT`/`FREIGABE_VERALTET` wie bisher. Ein Prüffehler ist ein Fehler im
Eintrag oder im Importweg: Claude meldet ihn und passt keine Sollwerte an Messwerte an (Ausnahme: `volumen`, das per Definition
aus `untersuchen` stammt – und auch das nur vor der Freigabe).

## 11. Referenz Motorhalter

`tests/referenz/motorhalter/`. **Maße nur zur Veranschaulichung; der Plan legt sie fest.**

- **Muster-Getriebemotor** `muster/`: zwei Teil-Specs (Gehäuse mit Flansch, Zentrierbund Ø 40, 4 × `normbohrung` Gewinde M5 auf
  Lochkreis Ø 60; Welle Ø 10) und eine Baugruppe (Welle konzentrisch im Gehäuse). Der Plan erzeugt daraus einmal per
  `SaveAs3` eine STEP-Datei (Baugruppen-STEP, 2 Körper, Kernloch Ø 4,2 sichtbar). **Präzisierung gegenüber der Antwort zu
  Frage 3:** Die erzeugte Datei `muster/gm42-10.step` wird **ins Git aufgenommen** (eigene Geometrie ohne Lizenzfrage, klein),
  damit SHA-256 im Eintrag und Prüfer-Urteil fest bleiben; eine bei jedem Lauf neu erzeugte Datei hätte wegen des
  Zeitstempels im STEP-Kopf jedes Mal eine andere Prüfsumme. Ausnahme von „erzeugte SolidWorks-Dateien nicht ins Git“; die
  Specs und das Erzeugungsskript bleiben die Quelle.
- **Katalogeintrag** `swki/wissen/kaufteile/swki-muster/gm42-10.yaml` (Beleg: das Muster-Datenblatt `muster/datenblatt.md`,
  aus den Specs abgeleitet), Freigabe, Prüfer-Urteil im Git.
- **Baugruppe** `motorhalter.yaml`: Grundplatte (fixiert), Motorbock (Winkel: Fuß und Wand mit Zentrierbohrung und
  4 × Durchgang M5), Motor (Kaufteil), 4 × ISO 4762 M5 durch die Wand in die Flanschgewinde (`je_position` auf die Bohrung der
  Wand), 2 × ISO 4762 M6 vom Fuß in Gewinde der Grundplatte. Statisch; Lage über `masse_pruefen` (Achshöhe).
- **Negativfälle** (live, je einzeln): falscher Ø in der Gegenprobe von `EINBAU_ACHSE` (Mangel `einbau:EINBAU_ACHSE`);
  Körperzahl 1 statt 2 (Mangel `koerper`); zu lange Flanschschraube (Mangel `gewinde:flanschschraube.<i>`). Ohne SolidWorks
  (*nachgezogen bei der Planung*, die SHA-256-Prüfung läuft vor dem Import): Original geändert
  (`KAUFTEIL_QUELLE_ABWEICHEND`), geänderter Eintrag nach der Baugruppen-Freigabe (`FREIGABE_VERALTET` mit Kaufteil),
  Schutzregel, Belegregel.
- **Abnahme mit echter Herstellerdatei:** Der Nutzer gibt eine STEP-Datei eines realen Kaufteils (seine Wahl, z. B. Motor oder
  Lager) und ggf. das Datenblatt; Claude nimmt sie mit dem vollen Ablauf auf (untersuchen, Eintrag, Freigabe durch den Nutzer,
  Prüfer, hole) und dokumentiert Diagnose-Kennzahlen, Zeiten, Speicher und Befunde in den Ergebnissen. Datei und Eintrag kommen
  nicht ins Git (Eintrag nur, wenn der Nutzer es will), nicht in die Regression.

## 12. Offene Technik (Spike S15 vor dem Plan-Code)

Vor jedem neuen API-Aufruf `swki api methode` / `swki api enum`; nur Aufrufe aus SW 2025.

- **S15a Import:** `GetImportFileData` + `LoadFile4` (4 Parameter) gegen `OpenDoc6` für `.step`; Optionen
  `swImportNeutralAssemblyStructureMapping` (2 = Mehrkörperteil), 3D Interconnect aus; Optionen lesen/setzen/wiederherstellen;
  gespeichertes Teil ohne externe Referenz (Neuöffnen ohne Original); Zoll-STEP (Maßstab).
- **S15b Diagnose:** `IBody2.Check3` (Fehlerzahl je Körper; *nachgezogen bei der Planung:* `IPartDoc.ImportDiagnosis`
  repariert und entfällt); Flächenkörper erkennen; Typname der Importfeatures; Hüllquader eines Mehrkörperteils
  (`sw.teilebox_mm`).
- **S15c Bezugsgeometrie an Importflächen:** Achse aus Zylinderfläche, Ebene deckungsgleich zu ebener Fläche, Ebene durch Achse und
  Punkt (Bauweise), Umbenennen, Auswahl per Name in einer Baugruppe.
- **S15d Masse:** `IMassProperty2.GetOverrideOptions` → `OverrideMass`, `SetOverrideMassValue` (seit 2020); Wirkung nach Speichern
  und Neuöffnen; Gesamtmasse einer Baugruppe mit dem Teil.
- **S15e Testdaten:** Baugruppe als STEP per `SaveAs3`; Re-Import als Mehrkörperteil mit 2 Körpern; Kernloch sichtbar; Unterschied
  zweier Exporte (nur Kopfzeile?).
- **S15f Baugruppe:** Komponente aus dem Kaufteil, Verknüpfungen auf `EINBAU_*`, Gewindeachse; Kollision Schraube ↔ Kaufteil
  (Ringvolumen gegen Soll); keine Paare innerhalb des Kaufteils.
- **S15g Speicher und Zeit:** Import, Referenzen, Prüfung des Musters; dazu ein größeres Modell (die Abnahmedatei, wenn der
  Nutzer sie schon gegeben hat, sonst ein erzeugtes Modell mit vielen Flächen); Private Bytes mit 0,5-s-Abtastung.
- **S15h Bilder:** Bezugsachsen/-ebenen in Screenshots sichtbar (Anzeigeoptionen nur für das eigene Dokument).

## 13. Tests

Ohne SolidWorks (pytest):

- Schema des Eintrags; Schlüssel und Dateinamen (Abbildung, Kollision); Belegregel (Hersteller allein, 2 Händler, 1 Händler,
  Widerspruch nicht im Code – Sache der Recherche); Schutzregel (Norm und `ersetzt`, Schreibweisen); `validieren`-Befunde und
  Hinweise.
- Freigabe des Eintrags (Prüfsumme über alles), Urteil an Freigabe gebunden, `hole` verweigert ohne Freigabe/Urteil.
- Quelle: Kopie, gleiche/abweichende SHA-256, `--neue-version`, nie überschreiben; Cache-Prüfsumme, Cache-Treffer, veraltet,
  nichts im Cache bei gescheiterter Prüfung (Attrappe).
- Abgeleitete Prüfspezifikation und Bewertung mit Attrappen-Messwerten (Körperzahl, Masse, Gegenproben, Gewindemodell).
- Baugruppe: Schema (`kaufteil`, `gewinde`-Referenz, `je_position` auf Gewinde), Laden, Plausibilität, Passung, `drehung_sperren`-
  Vorgabe und Hinweis, Freigabe mit Eintragsprüfsumme (`FREIGABE_VERALTET` nennt das Kaufteil), Gewindepaarung-Soll für
  `kernloch` und `nenn`, Stückliste, Bericht.

Mit SolidWorks (einzeln, `tests\live_einzeln.py`): Spike S15; `untersuchen` und `hole` am Muster (zweiter Aufruf Cache-Treffer);
Negativfälle §11; Referenz Motorhalter (Teil der Regressions-Suite).

## 14. Einbindung

- **Skill `kaufteile`** (neu): wann ein Kaufteil (nicht genormt) gebraucht wird, Abgrenzung zu `normteile`, Ablauf untersuchen →
  Belege (Datenblatt, eigene Suche, Belegregel, Widerspruch → Nutzer) → Eintrag → validieren → Nutzer-OK → freigeben → muster →
  Prüfer → urteil → hole; Umgang mit den Fehlercodes; neue Herstellerversion.
- **Skill `baugruppe`:** Komponentenquelle `kaufteil`, Referenzformen, `je_position` auf Gewinde, `drehung_sperren`.
- **Skill `normteile`:** Verweis „nicht genormt → Skill `kaufteile`“.
- **`.claude/agents/pruefer.md`:** Kaufteil-Checkliste.
- **`CLAUDE.md`:** Abschnitt Kaufteile (Stufe 3c): nur STEP, nur lesen, Bibliothek, Freigabe je Eintrag, Belegregel, keine Konten.
- **Design-Dokument:** §8 Stand-Absatz (Kaufteile → diese Spec; `normteil aufnehmen` entfällt), §11 Zeile 3c, §3
  (`kaufteilbibliothek`).
- **Ergebnisse:** `docs/stufe3c/ergebnisse.md`.

## 15. Fertig, wenn

- Der Muster-Getriebemotor ist aufgenommen (Freigabe, Prüfer-Urteil „bestanden“, Cache) und die Referenz *Motorhalter* besteht
  auf SW 2025: Code-Prüfungen ohne Mangel und Prüfer-Urteil „bestanden“.
- Die Negativfälle liefern die erwarteten Codes bzw. Mängel.
- Die Abnahme mit der echten Herstellerdatei ist dokumentiert (bestanden oder mit begründeten Befunden).
- Buchse, Formplatte, Auswerferhalteplatte, Stehlager, Linearschlitten und Zahnstangentrieb bestehen weiter; alle Unit-Tests grün;
  `swki api pruefe-code` ohne Befund.

## 16. Reihenfolge der Umsetzung

1. Spike S15 (a–h).
2. Schema, Laden, Schlüssel, Belegregel, Schutzregel, Freigabe des Eintrags (ohne SolidWorks).
3. Quelle und Cache (Kopie, Prüfsummen), `untersuchen` mit Diagnose.
4. Import, Referenzen, Prüfung, `muster`, `urteil`, `hole`, `liste`.
5. Muster-Motor (STEP erzeugen), Eintrag, Freigabe, Prüfer-Urteil.
6. Baugruppen-Format, Plausibilität, Passung, Freigabe, Bau, Gewindepaarung, Bericht.
7. Referenz Motorhalter mit Prüfer und Negativfällen.
8. Skills, `pruefer.md`, `CLAUDE.md`, Design §3/§8/§11, Ergebnisse; Abnahme mit echter Herstellerdatei.

## 17. Nicht in 3c

Parasolid, IGES, natives SLDPRT/SLDASM; Unterbaugruppen; Aufteilen, Reparieren, Vereinfachen oder Normalisieren importierter
Geometrie; Feature-Erkennung; Größengrenzen; Konfigurationen/Varianten eines Kaufteils (je Variante ein Eintrag); Konten bei
Herstellerportalen; genormte Teile als STEP; erlaubte Überlappungen außer Gewindepaarungen; Rechner B (SW 2026); Zeichnungen.
