# Stufe 3a – Normteile (selbst konstruiert, selbst geprüft, selbstfüllende Bibliothek)

Ergänzung zu [2026-09-26-solidworks-ki-design.md](2026-09-26-solidworks-ki-design.md) (§4 Spezifikation, §5 Compiler,
§6 Prüfung, §8 Normteile, §9 Skills, §11 Stufen). Stand 2026-10-02, mit dem Nutzer abgestimmt.

## 1. Ziel

Allgemeine genormte Verbindungselemente (Schrauben, Muttern, Scheiben, Stifte) entstehen auf Anforderung in wenigen
Sekunden aus einer Normtabelle und einer Bauvorlage, prüfen sich vollständig selbst und werden in einer lokalen
Bibliothek abgelegt. Beim nächsten Bedarf wird nur noch abgerufen; die Bibliothek füllt sich mit jedem neuen Normteil.

Das Projekt ist auf allgemeine Konstruktion mit Volumenkörpern ausgerichtet, nicht speziell auf den Werkzeugbau.
Stufe 3 wird geteilt: **3a Normteile** (dieses Dokument) und **3b Baugruppen statisch** (eigene Spec, setzt 3a voraus;
die Referenz *Säulenführung* aus Design §11 wird dort durch eine allgemeine Referenzbaugruppe ersetzt).

## 2. Entscheidungen (mit dem Nutzer, 2026-10-02)

| Frage | Entscheidung |
|---|---|
| Zuschnitt | Stufe 3 → 3a Normteile, 3b Baugruppen statisch; 3a zuerst |
| Herkunft genormter Teile | immer selbst konstruiert (einheitlich); keine STEP-Daten von Herstellern, keine Toolbox |
| Herstellerdaten | nur für nicht genormte Kaufteile; nicht in 3a (eigenes Paket bei Bedarf) |
| Normmaße | aus Claudes Normwissen; abgeglichen per Web-Recherche (Workflow mit Agents) **erst bei der Umsetzung** |
| Abgleich | ein Wert gilt als abgeglichen, wenn ≥ 2 unabhängige recherchierte Quellen ihn bestätigen (Claudes Wissen zählt nicht als Quelle); sonst Größe `gesperrt`, Abweichung an den Nutzer |
| Maßgebliche Quelle | Normtabelle + Bauvorlage im Git; die `.sldprt` in der Bibliothek ist ein Cache |
| Umfang | ISO 4762, ISO 4032, ISO 7089, ISO 8734; M5–M16 bzw. Ø 4–12 |
| Gewinde | Nenn-Ø, keine Gewindedarstellung; kosmetisches Gewinde als spätere Erweiterung (mit Zeichnungen) |
| Freigabe | keine Nutzerfreigabe; jedes Teil prüft sich vollständig selbst |
| Selbstprüfung | Tabelle vor dem Bau (Regeln), jedes Tabellenmaß am Körper, Volumen, Einbaureferenzen; Prüfer-Agent nur je neuer Vorlagenversion |
| Bauvorlage | normale Teil-Spezifikation mit Parametern (Ansatz A); je Größe wird nur der `parameter`-Block eingesetzt |
| Werkstoff | eine Bibliotheksdatei je Größe und Variante (Festigkeitsklasse/Werkstoff), Vorgabe je Norm |
| Einbaureferenzen | benannte Bezugsgeometrie aus der Vorlage (`EINBAU_ACHSE`, `EINBAU_EBENE` …) |
| Bibliothek | lokal je Rechner, getrennt nach SW-Version, Ordner aus `config/rechner.yaml` |
| Längen | nur Längen aus der Längenreihe der Norm; sonst Fehler mit nächsten Normlängen |

## 3. Bausteine

```
swki/wissen/normteile/<norm>.yaml            Normtabelle je Norm (Git)
swki/wissen/normteile/vorlagen/<norm>.yaml   Bauvorlage je Norm (Teil-Spezifikation mit Parametern, Git)
swki/wissen/normteile/vorlagen/<norm>.pruefer.json   Prüfer-Urteil zur aktuellen Vorlagenversion (Git)
schema/normtabelle.schema.json               Schema der Normtabellen
swki/normteile/                              Modul: Schlüssel, Tabellenprüfung, Spezifikation erzeugen, bauen, prüfen, ablegen
<normteilbibliothek>/<sw_jahr>/              Bibliothek (nicht im Git): <schluessel>.sldprt + <schluessel>.json
```

Dateinamen der Normen in Kleinbuchstaben ohne Leerzeichen (`iso4762.yaml`). `config/rechner.yaml` erhält den Eintrag
`normteilbibliothek` (Vorgabe `%USERPROFILE%\.swki\normteile`); `setup\einrichten.ps1` und
`config/rechner.beispiel.yaml` werden ergänzt. Die Bibliothek liegt außerhalb jedes Kunden- oder Bibliotheks-Originals;
gespeichert wird dort nur, was `swki normteil` selbst gebaut und geprüft hat.

## 4. Normtabelle

Beispiel ISO 4762. **Die Zahlen sind nur zur Veranschaulichung; die echten Werte entstehen bei der Umsetzung mit
Abgleich.**

```yaml
norm: ISO 4762
benennung: Zylinderschraube mit Innensechskant
ersetzt: DIN 912
vorlage: vorlagen/iso4762.yaml
varianten:                       # Festigkeitsklasse/Werkstoff → Material in der SW-Materialdatenbank
  "8.8": {material: <SW-Material>}
  "10.9": {material: <SW-Material>}
  "12.9": {material: <SW-Material>}
  "A2-70": {material: <SW-Material>}
vorgabe_variante: "8.8"
groessen:
  M8:
    masse: {d: 8, dk: 13, k: 8, s: 6, t: 4}
    laengen: [10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80]
    status: abgeglichen          # abgeglichen | gesperrt
    # grund: "dk: Quelle X 13, Quelle Y 13.5"   # Pflicht bei gesperrt
quellen:
  - {url: "https://…", abgerufen: 2026-10-…, groessen: [M5, M6, M8]}
regeln: ["dk > d", "s < dk", "k == d", "t < k"]
hinweise: ["…"]                  # bekannte Fallen, z. B. abweichende DIN-Werte
```

- Je Größe: Maße der Vorlagen-Parameter (ohne `l`), Längenreihe, Status. Die Länge `l` kommt aus der Anfrage.
- Muttern, Scheiben: ohne `laengen`; Stifte: Längenreihe je Ø.
- `regeln`: Ausdrücke über die Maße einer Größe (Syntax der Spezifikations-Ausdrücke plus Vergleiche), dazu
  feste Regeln für alle Normen: Werte > 0, Maße steigen mit der Größe, Längenreihe aufsteigend ohne Doppel.
- `swki normteil tabellen-pruefen` prüft Schema, Regeln, `quellen` (jede Größe mit Status `abgeglichen` ist in
  mindestens zwei Quellen genannt), `grund` bei `gesperrt` und – mit SolidWorks optional – die Materialnamen.

## 5. Bauvorlage

Eine Teil-Spezifikation nach `schema/teil.schema.json`, in der jedes Maß ein Ausdruck über Parameter ist. Für eine
Größe setzt `swki` den `parameter`-Block aus der Tabellenzeile (plus `l` aus der Anfrage) ein, außerdem `material`
und `eigenschaften` aus Variante und Tabelle. Der Rest der Vorlage bleibt unverändert.

Inhalt je Norm (Skizze, Feature-Folge legt der Plan fest):

- **ISO 4762:** Rotation Kopf + Schaft (Nenn-Ø, volle Länge, ohne Gewinde), Schnitt Sechseck (Ecken als Ausdrücke,
  z. B. `"=s/3**0.5"`) mit flachem Boden, Fasen an Kopf und Schaftende; `EINBAU_ACHSE` (Schraubenachse),
  `EINBAU_EBENE` (Kopfunterseite).
- **ISO 4032:** Sechskant-Prisma mit Bohrung Nenn-Ø, Fasen beidseitig; `EINBAU_ACHSE`, `EINBAU_EBENE` (eine
  Auflagefläche; beide Seiten gleich).
- **ISO 7089:** Ring (Rotation oder Extrusion); `EINBAU_ACHSE`, `EINBAU_EBENE`.
- **ISO 8734:** Zylinder mit Fasen bzw. Rundungen an den Enden (vereinfacht nach Norm); `EINBAU_ACHSE`,
  `EINBAU_EBENE_1`/`_2` (Stirnseiten).

Eigenschaften: `Benennung` nach Normbezeichnung (z. B. „Zylinderschraube ISO 4762 - M8 x 30 - 8.8“), `Norm`,
`Groesse`, `Festigkeitsklasse`; dazu wie bei allen Teilen `Ersteller`. `validieren` der erzeugten Spezifikation darf
keine `feste_zahl`-Hinweise liefern (alle Maße sind Ausdrücke).

## 6. Selbstprüfung

Je Anfrage, ohne Nutzerfreigabe:

1. **Tabelle:** die Zeile erfüllt `regeln` und die festen Regeln; Status `abgeglichen`; Länge in der Längenreihe.
2. **Spezifikation:** `swki validieren` der erzeugten Spezifikation ohne Befunde und ohne `feste_zahl`-Hinweise.
3. **Bau:** Rebuild fehlerfrei, genau 1 Körper, Skizzen voll bestimmt, Material und Eigenschaften gesetzt.
4. **Maße:** jedes Tabellenmaß über `pruefung.masse_pruefen` der Vorlage am Körper gemessen, Soll als Ausdruck
   (`"=dk"`), Toleranz 0,01 mm.
5. **Volumen:** gegen eine Formel in der Vorlage (exaktes Sollvolumen der vereinfachten Geometrie aus den Parametern).
6. **Einbaureferenzen:** Achse auf der Rotationsachse, Ebene auf der vorgesehenen Fläche (Messung).

Die Prüfung nutzt die vorhandenen Code-Prüfungen von `swki pruefen`; neu ist, dass sie ohne Freigabe-Kopie läuft
und ihr Ergebnis über das Ablegen entscheidet.

**Prüfer-Agent:** nur wenn sich die Vorlage geändert hat (Prüfsumme der Vorlagendatei ≠ der in
`<norm>.pruefer.json`). Dann wird ein Musterteil gebaut (kleinste Größe, kürzeste Länge, Vorgabevariante), mit
Screenshots dem Prüfer-Agenten vorgelegt und sein Urteil mit der Prüfsumme abgelegt. Ohne bestandenes Urteil zur
aktuellen Vorlage baut `swki normteil hole` diese Norm nicht (`NORMVORLAGE_UNGEPRUEFT`). Der Prüfer-Agent wird von
Claude gestartet (wie in Stufe 2); `swki` meldet nur, dass ein Urteil fehlt.

## 7. Befehle und Ablauf

```
swki normteil hole "<norm>" <groesse>[x<laenge>] [--variante <v>]
swki normteil tabellen-pruefen [<norm>]
swki normteil liste [--veraltet]
```

Ablauf `hole`:

1. Schlüssel auflösen (Norm-Schreibweisen „ISO 4762“, „ISO4762“, „iso4762“; Größe „M8x30“, „M8 x 30“; Stift
   „8x30“) und gegen die Tabelle prüfen.
2. Prüfsumme bilden über Tabellenzeile, Vorlagendatei und Variante. Liegt in `<normteilbibliothek>/<sw_jahr>/` eine
   Datei mit gleicher Prüfsumme und bestandener Prüfung: Pfad zurückgeben (`gebaut: false`).
3. Sonst: Spezifikation erzeugen, bauen (Arbeitsordner, Auftrag `NORMTEILE`, Laufnummer wie bei `bauen`), Selbst-
   prüfung. Bestanden → `.sldprt` in die Bibliothek kopieren und `<schluessel>.json` schreiben
   (Schlüssel, Prüfsumme, Prüfergebnis, Datum, SW-Version). Nicht bestanden → nichts ablegen, Laufordner bleibt.
4. Ausgabe JSON `{schluessel, pfad, gebaut, pruefung}`.

`liste` zeigt die abgelegten Teile und markiert veraltete (Prüfsumme passt nicht mehr). Veraltete Teile werden beim
nächsten `hole` neu gebaut; gelöscht wird nichts automatisch.

## 8. Fehlerfälle

JSON mit `code`, Exit 1:

| Code | Wann | Inhalt der Meldung |
|---|---|---|
| `NORMTEIL_UNBEKANNT` | Norm oder Größe fehlt | vorhandene Normen bzw. Größen |
| `NORMLAENGE_UNGUELTIG` | Länge nicht in der Längenreihe | nächste Normlänge darunter und darüber |
| `NORMVARIANTE_UNBEKANNT` | Variante nicht in der Tabelle | vorhandene Varianten |
| `NORMTEIL_GESPERRT` | Größe nicht abgeglichen | `grund` aus der Tabelle |
| `NORMTABELLE_UNGUELTIG` | Regel verletzt | Regel, Größe, Werte |
| `NORMVORLAGE_UNGEPRUEFT` | kein Prüfer-Urteil zur aktuellen Vorlage | Norm, Prüfsumme |
| `NORMTEIL_PRUEFUNG` | Bau gelungen, Selbstprüfung gescheitert | Messwerte, Laufordner |

Ein Prüffehler ist ein Fehler in Vorlage oder Tabelle: Claude meldet ihn und umgeht ihn nicht (keine Anpassung von
Sollwerten an Messwerte).

## 9. Einbindung

- **Skill `normteile`** (neu): wann ein Normteil gebraucht wird, Abruf über `swki normteil hole`, Umgang mit den
  Fehlercodes, Ablauf für eine neue Größe oder Norm (Tabelle erweitern, Abgleich mit ≥ 2 Quellen, Vorlage, Tests,
  Prüfer-Urteil).
- **CLAUDE.md:** Genormte Teile kommen immer über `swki normteil` (nie STEP-Download, nie freihändig konstruiert);
  Herstellerdaten nur für nicht genormte Teile; Normtabellen nur mit Abgleich erweitern.
- **Design-Dokument:** §8 Normteile auf diesen Stand (Toolbox-Rückfall und Katalog je Hersteller entfallen für
  genormte Teile), §11 Stufe 3 → 3a/3b.
- **Normbohrung:** Normteile und Normbohrungen passen zusammen (Test: für alle gemeinsamen Größen Schaft-Ø < Durchgang,
  Kopf-Ø < Senkungs-Ø, Kopfhöhe ≤ Senktiefe bei ISO 4762; Stift-Ø = Stiftloch-Ø).

## 10. Offene Technik (Spikes vor dem Bau)

- **S11a – Bezugsgeometrie:** benannte Bezugsachse und -ebene anlegen (neuer Feature-Typ `referenz` in Schema und
  Compiler) und in einer Baugruppe per Name auswählen.
- **S11b – Schlüsselweite messen:** Abstand paralleler Flächen (Innensechskant, Mutter) über `masse_pruefen`; reichen
  die vorhandenen Messgeometrien?
- **S11c – Werkstoffe:** Namen in der Materialdatenbank von Rechner A für die Varianten (Stahl, nichtrostender Stahl).

Vor jedem neuen API-Aufruf `swki api methode` nachschlagen; Compiler-Code nur mit Aufrufen aus SW 2025.

## 11. Tests

Ohne SolidWorks (pytest):

- Schema und Regeln jeder Normtabelle; Quellenpflicht; `gesperrt` mit Grund.
- Schlüssel auflösen, inkl. Fehlerfälle und nächster Normlängen.
- Jede Vorlage mit jeder Größe (und jeder Länge der Längenreihe) ergibt eine Spezifikation, die `validieren` ohne
  Befund und ohne `feste_zahl`-Hinweis annimmt.
- Volumenformel der Vorlagen gegen eine unabhängige Rechnung für einige Größen.
- Bibliothek: Prüfsumme, Cache-Treffer, veraltete Datei, nichts abgelegt bei gescheiterter Prüfung (Fake-Bau).
- Passung Normteil ↔ Normbohrung.

Mit SolidWorks (einzeln, `tests\live_einzeln.py`):

- Je Norm kleinste, mittlere, größte Größe: `hole` baut, prüft, legt ab; zweiter Aufruf ist Cache-Treffer.
- Verfälschter Tabellenwert (Testkopie der Tabelle): Selbstprüfung scheitert, nichts wird abgelegt.

## 12. Fertig, wenn

- Die vier Normtabellen sind über alle Größen M5–M16 bzw. Ø 4–12 abgeglichen (≥ 2 Quellen) oder begründet
  `gesperrt` und dem Nutzer gemeldet.
- Jede Vorlage hat ein bestandenes Prüfer-Urteil im Repo.
- Live-Tests grün; eine Stichprobe von mindestens 20 zufällig gewählten Teilen über alle Normen besteht die
  Selbstprüfung.
- Buchse, Formplatte und Auswerferhalteplatte bestehen weiter; alle Unit-Tests grün; `swki api pruefe-code` ohne
  Befund.

## 13. Reihenfolge der Umsetzung

1. Spikes S11a–c.
2. Feature-Typ `referenz` (Schema, Compiler, Tests).
3. Modul `swki/normteile`: Tabellenformat, Regeln, Schlüssel, Spezifikation erzeugen, Bibliothek (ohne SolidWorks).
4. Normtabellen mit Abgleich (Recherche-Workflow mit Agents).
5. Vorlagen je Norm mit Live-Test und Prüfer-Urteil.
6. Skill `normteile`, CLAUDE.md, Design §8/§11, Ergebnisse.

## 14. Nicht in 3a

Baugruppen (3b), Kaufteile von Herstellern, kosmetisches Gewinde, weitere Normen (ISO 4017, ISO 10642, ISO 2338 …),
gemeinsame Netzwerk-Bibliothek, Rechner B (zurückgestellt).
