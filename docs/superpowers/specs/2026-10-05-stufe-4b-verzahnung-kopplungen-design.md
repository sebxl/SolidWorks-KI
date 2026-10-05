# Stufe 4b – Verzahnung und Kopplungen (Evolventen-Stirnrad, Zahnstange, Zahnrad- und Zahnstangenverknüpfung)

Ergänzung zu [2026-09-26-solidworks-ki-design.md](2026-09-26-solidworks-ki-design.md) (§4 Spezifikation, §6 Prüfung, §11 Stufen),
[2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md) (Baugruppen-Format, Bauen, Prüfen) und
[2026-10-03-stufe-4a-bewegungen-design.md](2026-10-03-stufe-4a-bewegungen-design.md) (Grenzen, `freiheitsgrade`, `bewegungen`,
Bewegungsprüfung; Abweichungen der Umsetzung in `docs/stufe4a/ergebnisse.md`). Stand 2026-10-05, mit dem Nutzer abgestimmt;
bei der Planung nachgezogen (Plan `docs/superpowers/plans/2026-10-05-stufe-4b-verzahnung-kopplungen.md`): §3, §4.2, §4.3,
§4.5, §4.6, §5.4, §5.5, §8.

## 1. Ziel

Claude baut aus einer freigegebenen Spezifikation Teile mit **Evolventenverzahnung** (geradverzahntes Außen-Stirnrad,
Zahnstange) und Baugruppen, in denen **Zahnrad- und Zahnstangenverknüpfungen** eine Bewegung übertragen. `swki pruefen` belegt
die Verzahnung am Teil (Kopf- und Fußkreis, Zähnezahl, Zahnweite) und die Kopplung in der Baugruppe (Sollweg je Stellung,
kollisionsfreier Eingriff, Achsabstand, ein gemeinsamer Freiheitsgrad). Der Mensch greift wie bisher nur an der Freigabe ein.

4b hat **zwei Etappen**: Etappe 1 Verzahnung (Teil-Compiler), Etappe 2 Kopplungen (Baugruppe). Etappe 2 beginnt erst, wenn
Etappe 1 live besteht.

## 2. Entscheidungen (mit dem Nutzer, 2026-10-05)

| Frage | Entscheidung |
|---|---|
| Referenz | **Zahnstangentrieb** statt *Schieber mit Schrägbolzen* (Werkzeugbau, widerspricht der Ausrichtung „allgemeine Konstruktion“). 4b = Zahnrad + Zahnstange; Nut und Kurve werden ein eigenes Paket 4c |
| Zahnform | **echte Evolvente** (keine Teilkreis-Zylinder, keine Trapezzähne) |
| Zuschnitt | **eine Spec, ein Plan, zwei Etappen**: 1 Verzahnung (Feature, Teilprüfung, Teil-Referenzen), 2 Kopplungen (Referenz Zahnstangentrieb); Etappe 2 erst nach Live-Bestehen von Etappe 1 |
| Umfang Verzahnung | **gerade Außenverzahnung + Zahnstange**, Bezugsprofil DIN 867 (α = 20°, Kopfhöhe m, Fußhöhe 1,25 m, Fußrundung 0,38 m), Modul DIN 780 Reihe 1, ohne Profilverschiebung (z ≥ 17), Flankenspiel über Zahndickenabmaß |
| Aufbau Referenz | **Linearschlitten aus 4a ohne Hebel**, Zahnstange am Schlitten (ISO 4762), Lagerbock mit Antriebswelle (Rad z1) und Ritzelwelle (Rad z2 + Ritzel), eine Bewegung *Schlittenhub* |
| Sollweg | **je Stellung für alle Bewegungen** (bewegte Komponente und Endlagen-Komponenten); schließt den offenen 4a-Punkt „Kein Nachweis des Sollwegs je Stellung“ |
| Eingriff | **streng**: Zahnpaare werden wie alle Paare auf Kollision geprüft (Voraussetzung Flankenspiel und richtige Zahnphase) |
| Flankenspiel | **Zahndickenabmaß je Rad** (`zahndickenabmass`, mm, < 0), als Parameter von der Freigabe geschützt; Achsabstand bleibt m·(z1+z2)/2 |
| Teilprüfung | **Kopf-/Fußkreis, Zähnezahl, Zahnweite W_k** (Stirnrad); Zahnhöhe, Teilung, Zahndicke, Zähnezahl (Zahnstange); automatisch aus der Verzahnung |
| Übersetzung | **aus den Verzahnungen abgeleitet** (Zähnezahlen bzw. Teilkreis); die Verknüpfung nennt nur die beiden Verzahnungs-Features; erwartete Drehungen stehen als Endlagen in der Bewegung, `validieren` vergleicht beide |
| Negativfälle | Etappe 1: Zahnweite; Etappe 2: Zahnphase versetzt, Drehrichtung umgekehrt, Kopplung fehlt, Übersetzung verfälscht |
| Kopplung fehlt | Fall erwartet `{verknuepfungen}`; zusätzlich meldet `verknuepfungen` künftig **unterdrückte** Verknüpfungen als fehlerhaft (Lücke geschlossen); der Freiheitsgrad gekoppelter Wellen wird live positiv an der Referenz und negativ per Attrappe belegt |
| 4a-Reste | mitgenommen: Bericht vervollständigen (Grenz-ID, Bereich, Endlagen-/Sollweg-Spalte), abgebrochene Läufe einheitlich `ok=None`, `plausibel` prüft ebene Grenzflächen, privater Import öffentlich. **Nicht** mitgenommen: Speicherpaket, Deferred Minors |
| Ansatz | **neuer Feature-Typ `verzahnung`**: Profil in Python berechnet, Skizze mit fixierten Punkten, Extrusion; Kopplungen über `CreateMate` mit `IGearMateFeatureData` bzw. `IRackPinionMateFeatureData` (`AddMate5` hat keinen Teilkreis für die Zahnstange). Verworfen: Notausgang-Skript je Rad (nicht wiederholbar), Toolbox-Zahnräder (keine exakte Evolvente, nicht selbst gebaut) |

## 3. Bausteine

```
swki/verzahnung.py                    neu: Bezugsprofil, Kreise, Evolventenpunkte, Profil, Zahnweite, Profilfläche, Lage im
                                      Teil (rein Python; nachgezogen bei der Planung: nicht unter wissen/, das nur Daten hält)
swki/baugruppe/kopplung.py            neu: Kopplungsgraph, Übersetzung, Zahnphase, Eingriff (rein Python)
swki/wissen/module_din780.yaml        neu: Modulreihe 1 (Abgleich ≥ 2 Quellen)
swki/compiler/handler/verzahnung.py   neu: Handler (Skizze aus berechneten Punkten, Extrusion, Bezugsachse)
schema/teil.schema.json               + typ verzahnung
swki/spec/…                           validieren (Befunde §4.3), Ausdruck: Konstante pi
swki/pruefung/{messen,bewertung,geometrie}.py   Prüfung verzahnungen, volumen auto
schema/baugruppe.schema.json          + zahnrad, zahnstange, Referenzform {komponente, feature}; freiheitsgrade „gekoppelt“
swki/baugruppe/{plausibel,bau,sw_baugruppe,bewegung,bewertung,pruefen}.py   Kopplung, Zahnphase, Eingriff, Sollweg, 4a-Reste
config/standard.yaml                  + toleranzen.verzahnung_mm
.claude/skills/{konstruieren,baugruppe}/   + Verzahnung, Kopplungen
.claude/agents/pruefer.md             + Checkliste Verzahnung und Eingriff
tests/referenz/zahnstangentrieb/      Teil-Referenzen (Etappe 1) und Baugruppe (Etappe 2)
spikes/s14a_*.py, s14b_*.py           Spike S14a (vor Etappe 1), S14b (vor Etappe 2), §9
```

Die Modulnamen folgen dem Bestand; der Plan nennt die genauen Dateien.

## 4. Etappe 1 – Verzahnung im Teil

### 4.1 Format

**Maße, Feature-IDs und Flächen nur zur Veranschaulichung; die echten Referenzen legt der Plan fest.**

```yaml
art: teil
name: Ritzelwelle
parameter: {M: 2, ZR: 20, Z2: 25, BR: 24, B2: 16, AS: -0.05}
features:
  - id: f1                   # Welle (Rotation), spart die Radbereiche aus (volumen auto, §4.5)
    typ: rotation
    skizze: {…}
  - id: z1                   # Ritzel
    typ: verzahnung
    art: stirnrad            # | zahnstange
    ebene: {versatz: {ebene: vorne, abstand: 30}}   # Stirnseite; Formen wie skizze.ebene
    mitte: [0, 0]            # Stirnrad: Radachse
    modul: "=M"
    zaehne: "=ZR"
    breite: "=BR"            # Extrusion in Normalenrichtung der Ebene; optional umkehren: true
    zahndickenabmass: "=AS"  # mm, < 0
    winkel: 0                # nur Stirnrad: Lage der Mitte von Zahn 1 gegen +u (Grad), Vorgabe 0
  - {id: z2, typ: verzahnung, art: stirnrad, ebene: {versatz: {ebene: vorne, abstand: 70}}, mitte: [0, 0],
     modul: "=M", zaehne: "=Z2", breite: "=B2", zahndickenabmass: "=AS"}
```

Zahnstange:

```yaml
  - id: z1
    typ: verzahnung
    art: zahnstange
    ebene: vorne
    mitte: [0, 20]           # Zahn 1 auf der Profilmittellinie (u = Zahnmitte, v = Profilmittellinie)
    modul: "=M"
    zaehne: "=ZS"
    breite: "=BS"
    zahndickenabmass: "=AS"
    kopf: "+v"               # Zähne zeigen nach +v (Vorgabe) oder -v; die Zähne reihen sich entlang +u
```

- Pflicht: `art`, `ebene`, `mitte`, `modul`, `zaehne`, `breite`, `zahndickenabmass`. `winkel` nur beim Stirnrad, `kopf` nur bei der
  Zahnstange.
- Werte dürfen Ausdrücke sein; feste Zahlen meldet `validieren` wie bei anderen Features als `hinweise`.
- Die Achse eines Stirnrads ist als `{feature: <id>, instanz: 1, achse: true}` ansprechbar (Teil-`pruefung`, Baugruppen-Referenzen),
  wie eine Bohrungsachse.

### 4.2 Geometrie

Rein in Python (`swki/wissen/verzahnung.py`), ohne SolidWorks testbar. Bezugsprofil DIN 867, α = 20°, ohne Profilverschiebung.
*Nachgezogen bei der Umsetzung, 2026-10-05:* Das Modul heißt `swki/verzahnung.py` (nicht `swki/wissen/`: dort liegen nur Daten); es enthält auch das Lagemodell
`Verzahnung`/`verzahnung_im_teil` (Teilkoordinaten aus der Spec). Die Kopplungsrechnung steht in `swki/baugruppe/kopplung.py`.

**Stirnrad:**
- Teilkreis d = m·z, Grundkreis d_b = d·cos α, Kopfkreis d_a = d + 2m, Fußkreis d_f = d − 2,5m, Fußrundung ρ_f = 0,38m.
- Flanken: Evolventen vom Grundkreis bis zum Kopfkreis. Liegt der Grundkreis über dem Fußkreis (z < 42), geht die Flanke radial
  bis zur Fußrundung weiter; die Fußrundung schließt tangential an Flanke bzw. radiale Verlängerung und Fußkreis an. Die Trochoide
  des Wälzfräsers wird **vereinfacht** nicht erzeugt; ob das kollisionsfrei kämmt, belegt die Eingriffsprüfung (§5.6).
  *Nachgezogen bei der Planung, 2026-10-05:* Die Evolvente beginnt bei `r_start = max(r_b, √(r_f² + 2·r_f·ρ_f))`; die Fußrundung berührt die radiale
  Linie (nicht die Evolvente). Liegt `r_start` über `r_b`, entsteht dort ein flacher Knick unter dem aktiven Profil.
- Zahndicke am Teilkreis (Bogen) s = π·m/2 + A_s, die Flanken symmetrisch zur Zahnmitte.
- **Bezug:** Die Mitte von Zahn 1 liegt auf +u (Skizzenkoordinaten), gedreht um `winkel`.

**Zahnstange:**
- Gerade Flanken unter α zur Profilnormale, Teilung p = π·m, Zahndicke auf der Profilmittellinie s = π·m/2 + A_s, Kopfhöhe m,
  Fußhöhe 1,25m, Fußrundung 0,38m.
- Das Feature erzeugt nur das **Zahnband** von der Fuß- bis zur Kopflinie, Länge z·p, an beiden Enden in Lückenmitte. Den Rücken
  baut ein eigenes Feature (Extrusion), mit dem das Zahnband verschmilzt.
  *Nachgezogen bei der Planung, 2026-10-05:* Das Zahnband besteht aus einer geschlossenen Kontur **je Zahn** (Fußlinie unter dem Zahn, Fußrundungen,
  Flanken, Kopflinie); eine einzige Kontur entartet, weil die Fußlinien zwischen den Zähnen auf der Schlusslinie lägen. Diese
  Fußlinien sind Flächen des Rückens, der deshalb genau bis an die Fußlinie reichen muss (sonst zwei Körper, Prüfung
  `koerper`).
- **Bezug:** Die Mitte von Zahn 1 liegt bei u = `mitte[0]` auf der Profilmittellinie v = `mitte[1]`.

**Weitere Größen:** Zahnweite W_k mit Messzähnezahl k (§4.5), Profilfläche (für `volumen: auto`).

### 4.3 Validieren

Zusätzlich zu den bestehenden Prüfungen:

| Befund | Wann |
|---|---|
| `MODUL_NICHT_GENORMT` | `modul` nach Auswertung nicht in DIN 780 Reihe 1 (`swki/wissen/module_din780.yaml`) |
| `UNTERSCHNITT` | Stirnrad mit z < 17 |
| `ZAEHNE_UNGANZ` | `zaehne` nach Auswertung keine ganze Zahl bzw. < 1 (Zahnstange) |
| `FLANKENSPIEL_FEHLT` | `zahndickenabmass` ≥ 0 |

Hinweis `art: abmass_gross`, wenn |A_s| > 0,1·m. Die Modultabelle wird nur mit Abgleich erweitert (≥ 2 unabhängige Quellen, wie
die Normtabellen).

*Nachgezogen bei der Planung, 2026-10-05:* zusätzlich `VERZAHNUNG_GEOMETRIE`, wenn das vereinfachte Profil nicht konstruierbar ist (Zahn spitz, Lücke
zu eng); `winkel` nur beim Stirnrad und in [0, 360), `kopf` nur bei der Zahnstange; `pi` ist kein Parametername. Die Tabelle
enthält Reihe 1 von 0,05 bis 20 mm (zwei Quellen); 25 … 50 sind bis zu einem weiteren Abgleich gesperrt.

### 4.4 Bauen und Freigabe

- Der Handler berechnet das Profil beim Bau und zeichnet es als Skizze mit **fixierten Punkten** (ohne Gleichungen), extrudiert
  um `breite` und verschmilzt mit vorhandenen Körpern. Er legt eine Bezugsachse für die Radachse an. Spike S14a legt fest:
  Evolvente als Spline durch berechnete Punkte oder als Polylinie, ganzes Profil in einer Skizze oder eine Lücke + Kreismuster.
  *Nachgezogen bei der Umsetzung, 2026-10-05:* Keine Bezugsachse: die Radachse ist die koaxiale Fußkreis-Zylinderfläche des Features (S14a Zeile 4, r 17,5 bei m 2,
  z 20), angesprochen wie `{feature, instanz: 1, achse: true}`. Evolvente als Spline (`CreateSpline2`, alle Segmente `sgFIXED`,
  Abweichung 0,000114 mm, S14a Zeile 1), ganzes Profil in einer Skizze. Der COM-Overhead je Punkt macht die Skizze langsam
  (S14a Zeile 2/5); der Handler rechnet deshalb die Skizzenkoordinaten per affiner Abbildung (drei `zu_skizze`-Aufrufe
  kalibriert, vierter Punkt als Gegenprobe, Abweichung > 1e-9 m → `BauFehler`) und wählt alle Segmente in einem
  `MultiSelect2`-Aufruf zum Fixieren aus (Ruling T4-1).
- **Schutz:** Die Verzahnungswerte stehen in Features (Bauweg). Wie bei der Normbohrung misst `swki pruefen` gegen die
  **freigegebene Kopie** (§4.5); eine nachträgliche Änderung von `zaehne`, `modul` oder `zahndickenabmass` fällt dort auf.
  Anforderungswerte gehören in `parameter` (von der Prüfsumme geschützt).
- Die Zahnmaße sind im SolidWorks-Modell nicht gleichungsgebunden; eine Änderung von z in SolidWorks baut das Rad nicht neu
  (§14). `swki aenderungen` meldet nur die geänderte Datei.

### 4.5 Prüfen (Teil)

Neue automatische Prüfung **`verzahnungen`** nach dem Muster `normbohrungen`: Soll aus der freigegebenen Kopie, Knoten = Feature-ID,
Abweichungen im Klartext.

- **Stirnrad:** Kopfkreis-Ø d_a, Fußkreis-Ø d_f, Zähnezahl (Anzahl der Kopfflächen), **Zahnweite**
  W_k = m·cos α·[π·(k − 0,5) + z·inv α] + A_s·cos α mit k = round(z·α/π + 0,5) und inv α = tan α − α, gemessen als kürzester
  Abstand der beiden äußeren Flanken über k Zähne (die gemeinsame Normale tangiert den Grundkreis).
- **Zahnstange:** Zahnhöhe 2,25m, Teilung als Normalabstand gleichgerichteter Flanken π·m·cos α, Zahndicke auf der
  Profilmittellinie π·m/2 + A_s (aus den Flankenebenen gerechnet), Zähnezahl.
  *Nachgezogen bei der Planung, 2026-10-05:* statt der Zahnhöhe die **Kopflinie** (Abstand der Kopfflächen von der Profilmittellinie = m), weil die
  Fußlinie zum Rücken gehört; die Teilung als Abstand der Schnittpunkte gleichgerichteter Flanken mit der Profilmittellinie
  (= π·m).
- **Toleranz** `toleranzen.verzahnung_mm` (`config/standard.yaml`); der Wert kommt aus Spike S14a (erreichbare Genauigkeit von
  Spline bzw. Polylinie), deutlich unter |A_s|.
- Der Messweg (IMeasure zwischen Flankenflächen oder Rechnung aus den Flächendefinitionen) folgt aus Spike S14a.
  *Nachgezogen bei der Umsetzung, 2026-10-05:* Die Zahnweite wird nicht per `IMeasure` zwischen den ganzen Flanken gemessen (das liefert den Mindestabstand an den
  Flankenenden, −0,417 mm, S14a Zeile 3), sondern per Strahl entlang der Grundkreistangente (`IFace2.GetProjectedPointOn`,
  Spannmitte φ_m = `winkel` + (k − 1)·180°/z, Messgerade auf halber Zahnbreite); Genauigkeit ≤ 0,00001 mm, `verzahnung_mm`
  bleibt 0,005 (Ruling S14a-Z3, T5-1). Kein Treffer → `REFERENZ_NICHT_GEFUNDEN` („Zahnweite nicht messbar“).
- **`volumen: {soll: auto}`:** Die Verzahnung trägt Profilfläche × Breite bei. Es gilt die bestehende Regel, dass sich Features
  nicht überlappen; ein Rad auf einer Welle wird so modelliert, dass die Welle den Radbereich ausspart.

### 4.6 Referenzen und Negativfall Etappe 1

- `tests/referenz/zahnstangentrieb/`: `ritzelwelle.yaml` (Welle mit Rad z2 und Ritzel – zwei Verzahnungen auf einem Teil),
  `antriebswelle.yaml` (Welle mit Rad z1), `zahnstange.yaml` (Rücken, Zahnband, zwei Gewinde für ISO 4762). Die Referenzliste der
  Regression nimmt die drei Teile als Einzelteil-Referenzen auf.
- Beispielwerte (der Plan legt sie fest): m = 2, Ritzel z = 20, Rad z2 = 25, Rad z1 = 50, Achsabstand 75 mm.
  *Nachgezogen bei der Planung, 2026-10-05:* Zahnstange z = 30; die Referenz enthält außerdem Grundplatte, Leiste, Schlitten und Lagerbock.
- **Negativfall E1 (Zahnweite):** Zahndickenabmaß im Modell verfälscht (monkeypatch im Bau, Spec unverändert und gültig) →
  genau `{verzahnungen}` mit dem Knoten des Features und Zahnweite ist ≠ soll.
  *Nachgezogen bei der Planung, 2026-10-05:* an der Antriebswelle um −0,05 mm; das Volumen ändert sich nur um −0,13 % (unter der Toleranz 0,5 %).

## 5. Etappe 2 – Kopplungen in der Baugruppe

### 5.1 Format

**Maße, Feature-IDs und Flächen nur zur Veranschaulichung; die echte Referenz legt der Plan fest.**

```yaml
art: baugruppe
name: Zahnstangentrieb
parameter: {HUB: 220}
komponenten:
  - {id: grundplatte, quelle: {teil: grundplatte.yaml}, fixiert: true}
  # … Leisten, Leistenschrauben wie Linearschlitten (4a) …
  - {id: schlitten, quelle: {teil: schlitten.yaml}, gruppe: schieber}
  - {id: zahnstange, quelle: {teil: zahnstange.yaml}, gruppe: schieber}
  - {id: stangenschraube, quelle: {normteil: "ISO 4762 M5x16"}, je_position: {komponente: zahnstange, feature: f2}}
  - {id: lagerbock, quelle: {teil: lagerbock.yaml}}
  - {id: ritzelwelle, quelle: {teil: ritzelwelle.yaml}}
  - {id: antriebswelle, quelle: {teil: antriebswelle.yaml}}
verknuepfungen:
  # … statische Verknüpfungen, Grenze g1 am Schlitten (0 … HUB), Wellen je als scharnier im Lagerbock …
  - {id: k1, typ: zahnstange, a: {komponente: ritzelwelle, feature: z1}, b: {komponente: zahnstange, feature: z1}}
  - {id: k2, typ: zahnrad, a: {komponente: antriebswelle, feature: z1}, b: {komponente: ritzelwelle, feature: z2}}
freiheitsgrade: {schieber: 1, ritzelwelle: gekoppelt, antriebswelle: gekoppelt}
bewegungen:
  - name: Schlittenhub
    grenze: g1
    erwartet:
      endlagen:
        - {komponente: schlitten, verschiebung: ["=HUB", 0, 0]}
        - {komponente: zahnstange, verschiebung: ["=HUB", 0, 0]}
        # Drehsinn aus der Eingabe ableiten (Skill baugruppe §6), hier nur Beispiel
        - {komponente: ritzelwelle, drehung: {achse: [0, 0, -1], winkel: "=HUB*360/(pi*40)"}}
        - {komponente: antriebswelle, drehung: {achse: [0, 0, 1], winkel: "=HUB*360/(pi*40)*25/50"}}
```

- **Referenzform `{komponente, feature}`** (ohne `flaeche`/`achse`): ein Verzahnungs-Feature der Komponente; nur bei `zahnrad`
  und `zahnstange`.
- `typ: zahnrad`: `a` und `b` sind Stirnräder. `typ: zahnstange`: `a` ist das Stirnrad (Ritzel), `b` die Zahnstange.
- Kein Feld für die Übersetzung: `zahnrad` koppelt im Verhältnis z_b : z_a (Drehwinkel), `zahnstange` mit dem Teilkreis-Ø m·z_a.
- **`freiheitsgrade: gekoppelt`:** Die Komponente hat keinen eigenen Freiheitsgrad; sie folgt über Kopplungen einer Bewegung.
- Neue Konstante **`pi`** im Ausdrucksauswerter (`swki/spec/ausdruck.py`, in SolidWorks-Gleichungen als `pi` gültig).

### 5.2 Validieren

Zusätzlich zu Spec 3b §5 und 4a §5:

| Befund | Wann |
|---|---|
| `KOPPLUNG_ART` | Seite verweist nicht auf eine Verzahnung der passenden `art` (§5.1) |
| `MODUL_UNGLEICH` | die beiden Verzahnungen einer Kopplung haben verschiedene Module |
| `GEKOPPELT_OHNE_ANTRIEB` | eine `gekoppelt`-Komponente erreicht über Kopplungen keine Komponente bzw. Gruppe mit `1` |
| `KOPPLUNG_REIHENFOLGE` | Seite `b` einer Kopplung steht beim Anlegen noch nicht fest: sie ist weder fixiert, noch Seite `a` einer Grenze bzw. Mitglied ihrer Gruppe, noch Seite `a` einer **früheren** Kopplung; oder eine Kopplung steht vor einer anderen Verknüpfung einer ihrer Komponenten |
| `ENDLAGE_FEHLT` | eine `gekoppelt`-Komponente hat in der Bewegung, die sie treibt, keine Endlage `drehung` |
| `UEBERSETZUNG_WIDERSPRUCH` | Beträge der erwarteten Drehungen passen nicht zur abgeleiteten Übersetzung (Zahnstange: Winkel = Weg·360°/(π·m·z); Zahnrad: Winkel_a·z_a = Winkel_b·z_b), Toleranz 0,01°. Der Weg der Zahnstange ist ihre Endlage `verschiebung` bzw. der Bereich der Grenze ihrer Gruppe |
| `SCHRITTE_ZU_GROB` | eine erwartete Drehung erreicht je Schritt ≥ 180° (Aufsummieren nicht eindeutig, §5.6); die Meldung nennt die nötige Schrittzahl |
| `GRENZE_REFERENZ` | `a`/`b` einer Grenze ist keine ebene Fläche (4a-Rest, §6) |

Die Richtung (Vorzeichen) prüft `validieren` nicht; sie hängt von der Geometrie ab und wird live über Sollweg und Endlage belegt.

*Nachgezogen bei der Umsetzung, 2026-10-05:* `KOPPLUNG_REIHENFOLGE` gilt wie umgesetzt (Ruling P4): Komponenten ohne Eintrag in `freiheitsgrade` sind statisch
voll bestimmt (fest), Komponenten mit `1` sind Grenze bzw. Gruppe; nur `gekoppelt` kann „noch nicht fest“ sein. Der Befund tritt
auf, wenn (1) Seite `a` nicht `gekoppelt` ist (sie wird beim Bau in Phase gedreht), (2) Seite `a` schon Seite `a` einer anderen
Kopplung ist, (3) Seite `b` `gekoppelt` und nicht Seite `a` einer früheren Kopplung ist oder (4) nach der Kopplung noch eine
andere Verknüpfung ihrer Komponenten folgt. Die Bedingung „Seite `a` muss gekoppelt sein“ folgt damit aus dem Drehen in Phase.

### 5.3 Freigabe

- Kopplungen sind Bauweg wie alle Verknüpfungen. `freiheitsgrade` (mit `gekoppelt`) und `bewegungen` stehen schon in der
  Prüfsumme (4a §6).
- Die Übersetzung hängt an den Zähnezahlen der Teil-Specs; diese sind über die Teil-Freigabe und die Prüfung gegen die
  freigegebene Kopie (§4.4) geschützt.

### 5.4 Bauen

Wie Spec 3b §7 und 4a §7, zusätzlich:

1. **Reihenfolge:** Kopplungen nach allen übrigen Verknüpfungen ihrer Komponenten, in Spec-Reihenfolge (`KOPPLUNG_REIHENFOLGE`).
2. **Zahnphase:** Vor dem Anlegen wird Seite `a` um ihre Achse gedreht, bis eine Zahnmitte genau auf einer Lückenmitte von `b`
   steht: zwei Stirnräder auf der Mittenlinie, Ritzel und Zahnstange am Wälzpunkt (Lot von der Radachse auf die
   Profilmittellinie). Gerechnet wird aus dem Bezug der Verzahnung (Zahn 1, `winkel`, `mitte`) und der Lage `Transform2` beider
   Komponenten. Kandidat für die Drehung: `AddMate5` mit `ForPositioningOnly` (positioniert, legt keine Verknüpfung an);
   Alternativen klärt Spike S14b. Danach rechnet `bauen` die Phase nach (Knoten `zahnphase:<id>`, Fehler `ZAHNPHASE_FEHLER`
   mit Soll/Ist-Winkel).
   *Nachgezogen bei der Planung, 2026-10-05:* gedreht wird über `SetTransformAndSolve2` mit der gerechneten Lage (`AddMate5 … ForPositioningOnly` ist
   die Alternative, falls Spike S14b Zeile 7 abweicht); Toleranz 1e-3 Teilung.
3. **Kopplung anlegen:** `CreateMate` mit `IGearMateFeatureData` (Zähler/Nenner aus den Zähnezahlen) bzw.
   `IRackPinionMateFeatureData` (`DiameterVal` = m·z_a, `DiameterType` laut Spike). Name = ID, Rebuild, Fehlerstatus wie bei
   allen Verknüpfungen; Rücklesen von Übersetzung bzw. Durchmesser.
4. **Richtung:** `Reverse` setzt swki aus der Geometrie (Außenräder drehen gegensinnig; Zahnstange: v = ω × r am Wälzpunkt) nach
   der in Spike S14b gemessenen SolidWorks-Konvention. Die Spec hat dafür keinen Schalter; liegt die Konvention falsch, zeigen es
   Sollweg und Kollision sofort.
   *Nachgezogen bei der Planung, 2026-10-05:* Annahme: `Reverse = False` ergibt die physikalisch richtige Richtung (SolidWorks wertet die Geometrie
   aus); swki führt je Typ eine Konstante, die der Spike bestätigt oder umstellt.
   *Nachgezogen bei der Umsetzung, 2026-10-05:* `Reverse = False` ist bestätigt (S14b Zeile 6, Ruling S14b-Z6): die Bewegung ist physikalisch richtig (Ritzel +171,89°,
   Antriebswelle −85,94° bei Hub 60 mm). Das Rücklesen weicht ab: SolidWorks liefert Zähler und Nenner vertauscht (gesetzt 100/50,
   gelesen 50/100) und meldet an `k1` `Reverse` als `true`; deshalb vergleicht `eingriff` die Übersetzung als ungeordnetes Paar
   (§5.5) und prüft `Reverse` nie.
5. **Keine treibenden Hilfsverknüpfungen beim Bau** (Spike S13c). Die Grundstellung bleibt „Grenze mit `min`“ (4a §7.2).

### 5.5 Prüfen – statisch

Zusätzlich zu 3b §9 und 4a §8.1:

- **Bestimmtheit:** `gekoppelt` erlaubt den Status `unterbestimmt`, wie `freiheitsgrade: 1` (4a §8.1).
- **`eingriff:<kopplung>`:** Achsen parallel; Achsabstand m·(z_a + z_b)/2 (`zahnrad`) bzw. Abstand Radachse–Profilmittellinie
  m·z_a/2 (`zahnstange`); die Zahnbreiten überdecken sich (Überdeckung > 0); zurückgelesene Übersetzung bzw. Teilkreis-Ø gleich
  der Ableitung. Toleranz `verzahnung_mm` bzw. relativ 1e-6 für die Übersetzung. Der Rückleseteil steht hier und nicht in
  `verknuepfungen`, damit die Bewegungsprüfung bei einer verfälschten Übersetzung läuft (Negativfall 4).
  *Nachgezogen bei der Planung, 2026-10-05:* Fehlt die Kopplung im Modell, prüft `eingriff` nur die Geometrie (die fehlende Kopplung meldet
  `verknuepfungen`, Negativfall 3).
  *Nachgezogen bei der Umsetzung, 2026-10-05:* Die Übersetzung wird als **ungeordnetes Paar** verglichen (min/max der gelesenen Werte gegen min/max der Teilkreise,
  relativ 1e-6; Ruling T12-1, wegen S14b Zeile 6); der Meldetext bleibt „Übersetzung 110:50 statt 100:50“. Eine in der Spec
  erwartete, im Modell **fehlende** Verknüpfung zählt wie eine fehlerhafte oder unterdrückte als statischer Fehler: die
  Bewegungsprüfung läuft dann nicht, `bewegung:<name>` hat `ok=None` (Ruling T12-2/P1).
- **`verknuepfungen`:** meldet zusätzlich **unterdrückte** Verknüpfungen als fehlerhaft (Lücke aus dem Brainstorming, Negativfall 3).
- **Kollision streng:** Zahnpaare werden wie alle Paare geprüft (keine Ausnahme wie bei Gewindepaarungen).

### 5.6 Bewegungsprüfung

Wie 4a §8.2, zusätzlich bzw. geändert:

1. **Freiheitsgrad belegt:** `gekoppelt`-Komponenten werden wie Komponenten mit `1` geprüft: mit unterdrückten Grenzen und ohne
   Antrieb unterbestimmt, mit Antrieb voll bestimmt; sonst `freiheitsgrad:<komponente>`.
2. **Sollweg je Stellung (alle Bewegungen):**
   - (a) Die bewegte Komponente (Seite `a` der Grenze) erreicht in jeder Stellung den befohlenen Wert (gemessen wie `soll_weg` in
     „Grenze wirkt“, 4a §8.2.4).
   - (b) Jede Endlage vom Typ `drehung` und jede `verschiebung` einer **Abstands**bewegung steht in Stellung i auf
     i/schritte × Endlage (alle Kopplungen und Grenzen sind linear). Eine `verschiebung` in einer **Winkel**bewegung (Bogen) wird
     nur am Ende geprüft (Endlage).
   - Toleranz `anker_mm` bzw. 0,01°. Mangel `sollweg:<Bewegung>:<komponente>` mit erster abweichender Stellung, Soll und Ist.
   - `endlage:` bleibt unverändert; eine falsche Endlage meldet deshalb `endlage:` und `sollweg:`.
3. **Drehwinkel über 360°:** Die Drehung einer Komponente wird **über die Stellungen aufsummiert** (je Schritt der Winkel um die
   Endlagen-Achse aus der Rotationsdifferenz benachbarter Stellungen), nicht aus erster und letzter Stellung gerechnet. Das gilt
   auch für die Endlage `drehung`. Voraussetzung: jede Teildrehung < 180° (`SCHRITTE_ZU_GROB`, §5.2).
4. **Kollision je Stellung:** wie 4a, Zahnpaare eingeschlossen.
5. **Grenze wirkt, Paarläufe, Speicherabbruch `SPEICHER_KNAPP`, Aufräumen:** unverändert.
   *Nachgezogen bei der Umsetzung, 2026-10-05:* Der Status der Komponenten (`GetConstrainedStatus`) wird nach `ForceRebuild3(False)` gelesen (Ruling T13-1): ohne den
   Neuaufbau liest SolidWorks mit Antrieb die Antriebswelle über die Kopplungskette veraltet als 2 (statt 3), auch nach
   `EditRebuild3`; ohne Antrieb bleibt 2. Das wirkt auf alle Bewegungsprüfungen (Regression in `docs/stufe4b/ergebnisse.md`).

### 5.7 Bilder

- Wie 4a §8.3, zusätzlich je Kopplung eine Ansicht entlang der Radachse in Grundstellung (`<kopplung>-eingriff.png`), damit der
  Prüfer den Eingriff sieht. Ob auf die Kopplung gezoomt werden kann, klärt Spike S14b; sonst die ganze Baugruppe in dieser
  Richtung.
  *Nachgezogen bei der Umsetzung, 2026-10-05:* Zoom auf die Auswahl der beiden Komponenten ist bestätigt (S14b Zeile 12). Das Bild blendet während der Aufnahme alle
  übrigen Komponenten aus (der Lagerbock verdeckte sonst die Eingriffsstellen; Task 12b), blendet sie danach wieder ein (die
  Prüfung speichert nie) und fällt ohne gültige Auswahl auf `ViewZoomtofit2` zurück.

### 5.8 Prüfbericht

- Je Kopplung: Typ, Verzahnungen, Übersetzung soll/ist, Achsabstand soll/ist, Breitenüberdeckung.
- Je Bewegung zusätzlich zu 4a §8.5: Sollweg je Komponente (erste Abweichung, größte Abweichung), aufsummierte Drehungen.
  *Nachgezogen bei der Umsetzung, 2026-10-05:* Die größte Abweichung steht im Feld `groesste_abweichung` der Prüfung `sollweg:` (Ruling P5); aufsummierte Drehungen
  stehen in `endlage.ist.aufsummiert`.

## 6. Reste aus 4a

1. **Bericht:** Der Prüfbericht nennt je Lauf die Grenz-ID und den Bereich (`min`/`max`); `bericht.md` hat Spalten für Endlagen
   und Sollweg.
2. **Abgebrochene Läufe einheitlich:** Ist ein Lauf abgebrochen, sind `endlage`, `grenze` und `sollweg` `ok=None` (nicht
   geprüft); den Abbruch trägt der Mangel `bewegung:<name>`.
3. **`plausibel`:** `a`/`b` einer Grenze müssen ebene Flächen sein (Befund `GRENZE_REFERENZ`, §5.2).
4. **Privater Import:** `swki/baugruppe/bewegung.py` importiert keine privaten Namen aus `swki.pruefung.bewertung` mehr
   (`_pruefung`/`_beschreibung` öffentlich oder gemeinsame Hilfe).

## 7. Prüfer, Schleife, Bericht

- Prüfer-Checkliste (`.claude/agents/pruefer.md`) zusätzlich:
  - **Teil:** Verzahnung vollständig sichtbar (keine fehlenden oder verschmolzenen Zähne), Zahnform symmetrisch, Rad an der richtigen
    Wellenstelle.
  - **Baugruppe:** Räder kämmen sichtbar (Zahn in Lücke), Drehrichtungen plausibel (Außenräder gegensinnig), die Zahnstange
    überdeckt das Ritzel über den ganzen Hub.
- `status`, Nachbesserung und Abbruch ohne Fortschritt wie bisher; die neuen Mängel zählen wie alle anderen.
- `bericht.md`: Tabelle je Kopplung (Übersetzung, Achsabstand) und die Spalten aus §6.1.

## 8. Fehlerfälle

| Code | Wann | Daten |
|---|---|---|
| `MODUL_NICHT_GENORMT`, `UNTERSCHNITT`, `ZAEHNE_UNGANZ`, `FLANKENSPIEL_FEHLT` | `validieren` (Teil), §4.3 | Feature, Wert |
| `KOPPLUNG_ART`, `MODUL_UNGLEICH`, `GEKOPPELT_OHNE_ANTRIEB`, `KOPPLUNG_REIHENFOLGE`, `ENDLAGE_FEHLT`, `UEBERSETZUNG_WIDERSPRUCH`, `SCHRITTE_ZU_GROB`, `GRENZE_REFERENZ` | `validieren` (Baugruppe), §5.2 | Verknüpfung bzw. Komponente, Werte |
| `ZAHNPHASE_FEHLER` | `bauen`: Phase nach dem Drehen nicht erreicht | Kopplung, Soll/Ist-Winkel |
| `VERZAHNUNG_GEOMETRIE` | `validieren` (Teil): Profil nicht konstruierbar (nachgezogen bei der Planung) | Feature, Grund |

Mängel im Prüfbericht (keine Fehlercodes): `verzahnungen` (Teil), `eingriff:<kopplung>`, `sollweg:<Bewegung>:<komponente>`;
weiter alle aus 4a.

## 9. Offene Technik (Spike S14 vor dem Plan-Code der jeweiligen Etappe)

Live, mit eigenen Probe-Teilen bzw. -Baugruppen; vor jedem neuen API-Aufruf `swki api methode`/`enum`. Je Zeile Annahme und
„sonst“ im Plan (Tabelle „Abhängigkeiten vom Spike“).

**S14a (vor Etappe 1):**
1. Evolvente als Spline durch berechnete Punkte gegen Polylinie: Abweichung von der Soll-Evolvente, voll bestimmte Skizze mit
   fixierten Punkten, Rebuild-Zeit.
2. Ganzes Profil in einer Skizze gegen eine Lücke + Kreismuster, für z = 17 … 80.
3. Messweg für d_a, d_f, Zähnezahl, W_k und die Zahnstangenmaße; erreichbare Genauigkeit → `verzahnung_mm`.
4. Achse der Verzahnung als Referenz (Teilprüfung und Baugruppe).
5. Zeit und Private Bytes je Radbau.

**S14b (vor Etappe 2, mit dem Handler aus Etappe 1):**

6. `CreateMate` mit `IGearMateFeatureData` / `IRackPinionMateFeatureData`: Entitäten (Achse oder Zylinderfläche; Kante der
   Zahnstange), Rücklesen der Werte, Konvention von `Reverse`; ob `AddMate5` für `zahnrad` gleichwertig wäre.
7. Zahnphase über `AddMate5` mit `ForPositioningOnly` oder eine Alternative; erreichte Genauigkeit.
8. `GetConstrainedStatus` mit Kopplungen (Grenzen unterdrückt, ohne und mit Antrieb).
9. Kollisionsprüfung im Eingriff mit Flankenspiel über mindestens eine volle Umdrehung (keine Scheinkollision) und mit versetzter
   Phase (wird erkannt); Zeit und Private Bytes je Schritt. Liegt die Prüfung der Referenz absehbar über `speicher_grenze_mb`
   (10000) auf frischem SolidWorks, wird **vor dem Plan-Code** neu entschieden (nicht still die Grenze angehoben).
10. „Grenze wirkt“ durch die Kopplungskette.
11. Aufsummierte Drehung aus `Transform2`.
12. Bild entlang der Radachse, Zoom auf die Kopplung.
13. Speichern und Neuöffnen: Kopplungen und Grenze wirken weiter, das Modell bleibt ziehbar (Lehre aus S13c).

*Nachgezogen bei der Umsetzung, 2026-10-05:* **Ergebnisse S14a und S14b** (Einzelheiten und Rulings je Zeile in `docs/stufe4b/ergebnisse.md`):
S14a: Zeilen 1, 4 und 6 bestätigt; Zeile 2/5 abweichend (Skizzenzeit 56–112 s, im COM-Overhead je Punkt; Beschleunigungen im
Handler), Zeile 3 nur für die Zahnweite abweichend (Strahl statt `IMeasure`). S14b: Zeilen 7, 8, 9 (Kollision, Zeit), 10, 11, 12
und 13 bestätigt; Zeile 6 abweichend im Rücklesen (Zähler/Nenner vertauscht, `Reverse` gelesen `true`), Bewegung richtig;
Zeile 9 Speicher abweichend (+364/+123 MB in den ersten zwei Schritten, danach flach; Nutzer: „Annehmen, weiter“).

## 10. Tests

- **Ohne SolidWorks:**
  - Geometrie-Modul: Evolventenpunkte, Kreise, Zahndicke, W_k gegen Tabellenwerte aus ≥ 2 Quellen, Profilfläche, Zahnstange.
  - Schema und alle neuen Befunde und Hinweise; Konstante `pi`.
  - Rechnung der Zahnphase und der Richtung (`Reverse`).
  - Sollweg: Interpolation, aufsummierte Drehung, `SCHRITTE_ZU_GROB`, Winkelbewegung mit `verschiebung` nur am Ende.
  - Mängelbildung: `verzahnungen`, `eingriff`, `sollweg`, Freiheitsgrad `gekoppelt` per Attrappe (ohne Antrieb 2 / mit 3 bzw.
    falsch), unterdrückte Verknüpfung, 4a-Reste, Bericht.
- **Mit SolidWorks:**
  - Minimalprobe je Verzahnungsart (`tests/live/`) und je Kopplungstyp.
  - Teil-Referenzen (§4.6) und Referenz *Zahnstangentrieb* (`tests/referenz/zahnstangentrieb/`).
  - Negativfälle einzeln, je mit frischem SolidWorks (Erfahrung 4a: zwei Bewegungs-Negativfälle nacheinander in einer Sitzung
    scheiterten).
  - Regression: Buchse, Formplatte, Auswerferhalteplatte, Stehlager, Linearschlitten. Der Schlitten jetzt mit Sollweg; seine vier
    Negativfälle werden neu bestätigt, weil `sollweg:`-Mängel hinzukommen können (Erwartung nach Live-Lauf, nicht vorab
    angepasst).
- **Negativfälle Etappe 2** (alle per monkeypatch im Bau; die Spec bleibt unverändert und gültig; Mengen vorhergesagt, live
  bestätigen, Abweichungen entscheidet der Controller nach dem Muster aus 4a):

| Fall | Herstellung | erwartete Mängelmenge |
|---|---|---|
| 1 Zahnphase versetzt | Phase von `k2` um eine halbe Teilung versetzt | `{kollision}` – schon in Grundstellung; das Paar meldet die Bewegungsprüfung nicht noch einmal (4a §8.2.3) |
| 2 Drehrichtung umgekehrt | `Reverse` von `k2` umgedreht | `{bewegung_kollision:Schlittenhub, sollweg:Schlittenhub:antriebswelle, endlage:Schlittenhub:antriebswelle}` |
| 3 Kopplung fehlt | `k2` wird nicht angelegt | `{verknuepfungen}` (Knoten `k2`; die Bewegungsprüfung läuft dann nicht, `bewegung:Schlittenhub` mit `ok=None`) |
| 4 Übersetzung verfälscht | Zähler/Nenner von `k2` verfälscht | `{eingriff:k2, sollweg:Schlittenhub:antriebswelle, endlage:Schlittenhub:antriebswelle, bewegung_kollision:Schlittenhub}`; der Plan wählt die Verfälschung so groß, dass die Zähne innerhalb des Hubs aufeinanderlaufen |

*Nachgezogen bei der Umsetzung, 2026-10-05:* Fall 3 liefert live `{verknuepfungen, kollision}` (Ruling T14-1): ohne `k2` fehlt auch die Zahnphase der Antriebswelle (der
Bau legt für `k2` weder Phase noch Kopplung an), sie steht in der Einbaulage, und ihre Zähne liegen auf denen der Ritzelwelle;
die strenge Kollisionsprüfung meldet das zu Recht (Paar Antriebswelle/Ritzelwelle, vier Volumina 69,22/61,38/18,99/3,51 mm³).
Die Erwartung wurde damit erweitert (strenger), nicht abgeschwächt; die übrigen Aussagen bleiben (`k2` einziger Knoten von
`verknuepfungen`, `bewegung:Schlittenhub` mit `ok=None`). Die Einbaulage ist deterministisch. Alternative: nur das `CreateMate` von
`k2` unterlassen und die Phase behalten (Menge `{verknuepfungen}`).

## 11. Einbindung

- Skill `konstruieren`: Feature `verzahnung` (Format, Bezug Zahn 1, Welle spart den Radbereich aus, Anforderungswerte als
  Parameter, `zahndickenabmass` < 0).
- Skill `baugruppe` §6: Kopplungen (`zahnrad`, `zahnstange`, Seite `a` wird in Phase gedreht, Kopplungen zuletzt),
  `gekoppelt`, Endlagen gekoppelter Komponenten mit `pi`, Drehsinn aus der Eingabe ableiten, Sollweg.
  *Nachgezogen bei der Umsetzung, 2026-10-05:* Die Kopplungen stehen im Skill `baugruppe` als §7 (§6 sind die Bewegungen aus 4a).
- `config/standard.yaml`: `toleranzen.verzahnung_mm`.
- CLAUDE.md: Abschnitt „Verzahnung und Kopplungen (Stufe 4b)“ (Kurzregeln).
- Gesamtdesign §11: Zeile 4b neu (Verzahnung, Zahnrad- und Zahnstangenkopplung, Referenz *Zahnstangentrieb*); neue Zeile 4c
  (Nut- und Kurvenverknüpfung, Referenz offen).

## 12. Fertig, wenn

- **Etappe 1:** Die drei Teil-Referenzen bestehen (Code-Prüfungen und Prüfer); Negativfall E1 liefert genau `{verzahnungen}`;
  Buchse, Formplatte und Auswerferhalteplatte bestehen weiter.
- **Etappe 2:** Referenz *Zahnstangentrieb* besteht (Code-Prüfungen und Prüfer); die vier Negativfälle liefern genau ihre
  Mängelmenge; Buchse, Formplatte, Auswerferhalteplatte, Stehlager und Linearschlitten (mit Sollweg und seinen Negativfällen)
  bestehen weiter.
- Zeit und Private Bytes je Radbau und je Bewegungsschritt mit Verzahnung sind in `docs/stufe4b/ergebnisse.md` dokumentiert.
  *Nachgezogen bei der Umsetzung, 2026-10-05:* Zeit und Speicher: Rad z 50 ca. 20 s, Teil mit Rad ca. +1,4–1,8 GB Private Bytes (Ziel < 15 s und < 300 MB nicht
  erreicht, Hinweis im Skill `konstruieren`). Die Speicherspitzen der Referenz *Zahnstangentrieb* und der Negativfälle liegen bei
  ~10,1–10,3 GB, also über `speicher_grenze_mb` 10000, ohne `SPEICHER_KNAPP`, weil die Abfrage nur das Dauerniveau sieht.

## 13. Reihenfolge der Umsetzung

- **Etappe 1:** Spike S14a → Geometrie-Modul → Schema, `validieren` → Handler → Teilprüfung `verzahnungen` → Teil-Referenzen →
  Negativfall E1 → Zwischenstand in `docs/stufe4b/ergebnisse.md`.
- **Etappe 2:** Spike S14b → Schema, `validieren` der Kopplungen, `pi` → Bauen (Zahnphase, Kopplung, Richtung) → Prüfen (Eingriff,
  `gekoppelt`, Sollweg, unterdrückte Verknüpfungen, 4a-Reste) → Bilder, Bericht, Prüfer → Referenz *Zahnstangentrieb* →
  Negativfälle → Doku, Regression.

## 14. Nicht in 4b

Nut- und Kurvenverknüpfung (4c); Schräg-, Innen-, Kegel- und Schneckenverzahnung; Profilverschiebung; exakte Trochoide im Fuß;
Schraub- und Linearkoppler; Kopplungen ohne Verzahnung (Reibrad); Zahnparameter im SolidWorks-Modell ändern (kein Neuaufbau, nur
Dateiänderung erkannt); Kräfte, Motion-Studien, Animationen; Speicherpaket (Ergebnisse 4a, Abschnitt 7) und Deferred Minors aus 4a;
Unterbaugruppen; Rechner B (SW 2026).
