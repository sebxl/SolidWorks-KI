# Paket Formschräge – schräge Wände an Extrusion und Schnitt

Ergänzung zu [2026-09-26-solidworks-ki-design.md](2026-09-26-solidworks-ki-design.md) (§4 Spezifikation, §6 Prüfung,
§11 Stufen) und [2026-09-29-stufe-2c-design.md](2026-09-29-stufe-2c-design.md) (Endbedingungen, Sollvolumen, kompakter
Baum). Stand 2026-10-07, mit dem Nutzer abgestimmt.

## 1. Ziel

`extrusion` und `schnitt` bekommen eine Option `formschraege`: Die Seitenwände des Features laufen unter einem Winkel zur
Extrusionsrichtung, der Querschnitt wird von der Skizze weg kleiner oder größer. Zweck sind **Gestaltungselemente** der
allgemeinen Konstruktion (konischer Zapfen, Einführschräge, Trichter, verjüngter Steg) – keine Entformungsschräge mit
Mindestwinkel. Ein eigenes Feature `formschraege` (nachträgliche Schräge an beliebigen Flächen, `InsertMultiFaceDraft`)
ist nicht Umfang und kommt erst, wenn es gebraucht wird (§12).

## 2. Entscheidungen (mit dem Nutzer, 2026-10-07)

| Frage | Entscheidung |
|---|---|
| Weg | **Option an `extrusion`/`schnitt`** (Formschräge beim Extrudieren); kein eigenes Feature |
| Zweck | Gestaltungselement; Winkel frei in 0° < winkel < 90°, keine Mindestschräge |
| Richtung | **über den Querschnitt** von der Skizze weg: `kleiner` / `groesser` – gleich zu lesen für Aufsatz und Schnitt; nicht die SolidWorks-Bedeutung innen/außen |
| Winkel | in Grad gegen die Extrusionsrichtung (0° = gerade Wand); Anforderungsmaß → als Parameter (Hinweis `feste_zahl` sonst) |
| Endbedingungen | alle bestehenden (`blind`, `mittig`, `durch_alles`, `bis_flaeche`, `versatz_von_flaeche`); Verhalten je Endbedingung misst Spike S16 |
| Anker | Seitenflächen eines Features mit Formschräge sind nicht achsparallel: `validieren` lehnt Richtungsanker quer zur Extrusionsrichtung und `senkrechte_kanten` an solchen Features ab (Ausweg `nahe`, Eckradius in der Skizze) |
| Prüfung | automatisch je Feature mit Formschräge (Winkel und Richtung jeder Seitenfläche) gegen die **freigegebene Kopie**; Sollvolumen analytisch, wo möglich |
| Referenz | **Zentrieraufnahme** (neu): Grundplatte mit konischem Zapfen, Einführtasche mit Eckradius, Trichter-Durchbruch, beidseitig verjüngtem Steg. Den Trichter braucht der Nutzer im nächsten Projekt |
| Einordnung | eigenes kleines **Paket Formschräge**; Zeile Stufe 5 in Design §11 wird nachgezogen; Ergebnisse `docs/formschraege/ergebnisse.md` |

## 3. Format

```yaml
parameter:
  WZ: 15        # Schräge des Zentrierzapfens in Grad
features:
  - id: zapfen
    typ: extrusion
    skizze:
      ebene: {feature: f1, flaeche: "+y"}
      elemente: [{kreis: {mitte: [0, 0], durchmesser: "=DZ"}}]
    ende:
      typ: blind
      tiefe: "=HZ"
      formschraege: {winkel: "=WZ", querschnitt: kleiner}
```

Schema (`schema/teil.schema.json`, `$defs/ende`): neue Eigenschaft

```json
"formschraege": {
  "type": "object", "required": ["winkel", "querschnitt"], "additionalProperties": false,
  "properties": {"winkel": {"$ref": "#/$defs/wert"}, "querschnitt": {"enum": ["kleiner", "groesser"]}}
}
```

Bedeutung:
- **r** ist die Richtung von der Skizzenebene weg ins Feature: beim Aufsatz die Wachstumsrichtung, beim Schnitt die
  Schnittrichtung, bei `mittig` je Hälfte von der Skizzenebene weg.
- **Querschnitt** ist der extrudierte Bereich: Material beim Aufsatz, Aussparung beim Schnitt. `kleiner` heißt, er wird
  mit wachsendem Abstand entlang r kleiner (Zapfen verjüngt sich nach oben; Tasche wird zum Boden hin enger).
  `groesser` heißt, er wächst (Trichter, von der engen Seite aus skizziert).
- Bei mehreren Profilen in einer Skizze gilt die Bedeutung für den Bereich zwischen den Profilen (bei `kleiner` rückt
  der Außenrand nach innen und ein Innenrand nach außen). Ob SolidWorks das so baut, prüft Spike S16 (§8, Frage 3).
- `formschraege` gilt nur für `extrusion` und `schnitt`; `rotation` und `verzahnung` haben kein `ende` mit dieser Option.

## 4. Compiler

`swki/compiler/handler/extrusion.py`: `aufsatz()` und `schnitt()` erhalten die Formschräge und setzen
`Dchk1 = True`, `Ddir1` und `Dang1` (Radiant) von `FeatureExtrusion3` (Index 7, 9, 11) bzw. `FeatureCut4` (Index 7, 9,
11; laut API-Index). Kein neuer API-Aufruf für den Bau; die Zuordnung `querschnitt` → `Ddir1` getrennt für Aufsatz und
Schnitt kommt aus dem Spike (Konstante mit Spike-Verweis, wie `VERSATZ_WEG_VON_SKIZZE`).

Der Winkel wird wie die Tiefe mit dem Parameter verknüpft (`ctx.verknuepfe("<Maß>@<id>", winkel)`); den Namen des
Winkelmaßes am Feature misst der Spike. Ohne `formschraege` bleibt der Aufruf unverändert (`Dchk1 = False`, Winkel 0).

Fehler: Erzeugt SolidWorks kein Feature (z. B. Profil fällt zusammen bei Polygonen, die `validieren` nicht vorab prüft),
meldet der Handler wie bisher `FEATURE_NICHT_ERZEUGT`, mit dem Zusatz „Formschräge zu groß für das Profil?“.

## 5. Validieren (ohne SolidWorks)

Neue Befunde in `swki/spec/laden.py` (Format `{pfad, meldung}`):
1. **Winkel:** 0 < winkel < 90 (nach Auswertung der Parameter).
2. **Profil fällt zusammen** (nur `querschnitt: kleiner` und bekannte Tiefe T: `blind` = tiefe, `mittig` = tiefe/2;
   sonst keine Vorabprüfung) bei genau einem Profil:
   - Kreis: T·tan α < d/2
   - Rechteck: T·tan α < min(b, h)/2; mit Eckradius zusätzlich T·tan α < radius (Eckbogen schrumpft nicht auf null)
   - Langloch: T·tan α < breite/2
   - Polygon, Kontur, mehrere Profile: keine Vorabprüfung (SolidWorks meldet es, §4)
3. **Anker an Features mit Formschräge:** Flächenanker `{feature: <id>, flaeche: <richtung>}` und Kantenanker
   `kanten_an: <richtung>` mit Richtung quer zur Extrusionsrichtung sowie `auswahl: senkrechte_kanten` sind Fehler, mit
   Hinweis auf `nahe` bzw. Eckradius in der Skizze. Richtungen parallel zur Extrusionsrichtung (Deck- und Bodenfläche)
   bleiben erlaubt. Die Extrusionsrichtung folgt aus der Skizzenebene (Standardebene, Versatzebene oder Flächenanker).

Der feste Winkel fällt unter den bestehenden Hinweis `feste_zahl` (maßtragendes Feld); `swki/spec/hinweise.py` wird
geprüft und bei Bedarf ergänzt, damit `formschraege.winkel` erfasst wird.

## 6. Prüfung

### 6.1 Formschrägen messen (`formschraegen`)
Für jeden `extrusion`/`schnitt`-Knoten der **freigegebenen Kopie** mit `formschraege` (die Richtung ist Text und von der
Freigabe-Prüfsumme nicht geschützt, wie Normbohrungsgrößen) liest `swki/pruefung/messen.py` das gleichnamige Feature und
misst seine **Seitenflächen** (alle Flächen des Features, deren Normale nicht parallel zu r ist):
- ebene Fläche mit äußerer Normale n: Ist-Winkel = asin(|n·r|); Vorzeichen s = sign(n·r)
- Kegelfläche: Ist-Winkel = halber Öffnungswinkel (`ISurface.ConeParams`); Vorzeichen aus der Normale an einem Punkt der
  Fläche (Auswertung im Spike)
- Soll-Vorzeichen: Aufsatz `kleiner` → +1, Aufsatz `groesser` → −1, Schnitt `kleiner` → −1, Schnitt `groesser` → +1
  (bei `mittig` r je Seite der Skizzenebene)
- andere Flächenarten: nicht messbar (Hinweis, kein Mangel); ohne eine einzige gemessene Seitenfläche: Mangel

`swki/pruefung/bewertung.py` bewertet wie `normbohrungen`: ein Eintrag `formschraegen` mit `ok`, abweichenden Knoten
(`knoten`) und je Knoten der Abweichung (Winkel Soll/Ist, Richtung). Toleranz `toleranzen.winkel_grad` in
`config/standard.yaml` (neu, Wert nach Spike). Feature fehlt im Modell → Mangel.

### 6.2 Sollvolumen
`volumen_auto` (`swki/pruefung/geometrie.py`) rechnet Features mit Formschräge analytisch über den versetzten Querschnitt
A(d) = A + P·d + K·d² mit d = ±h·tan α (+ bei `groesser`, − bei `kleiner`):

V = A·T ± P·tan α·T²/2 + K·tan² α·T³/3 (bei `mittig` zweimal mit T/2)

K je Profil: Kreis und Langloch π, Rechteck 4, Rechteck mit Eckradius π, konvexes Polygon ohne Radien Σ tan(θᵢ/2)
(θᵢ Außenwinkel). Andere Profile, mehrere Profile und Endbedingungen ohne bekannte Tiefe → `None` mit Grund (wie bisher).

### 6.3 Bericht und Prüfer
- Prüfbericht und `bericht.md`: Abschnitt Formschrägen (Knoten, Soll-/Ist-Winkel, Richtung).
- Prüfer-Agent (`.claude/agents/pruefer.md`): Abschnitt „Zusätzlich bei Formschrägen“ – Richtung im Bild gegen
  `querschnitt` plausibel, Ergebnis `formschraegen` im Prüfbericht, Anschlüsse (Zapfen auf Fläche, Tasche ohne Hinterschnitt).

## 7. Skill `konstruieren`

Modellierregeln ergänzen:
- Schräge Wände eines extrudierten Elements als `formschraege` an der Extrusion, nicht als eigenes Feature und nicht als
  Polygon-Rotation.
- Winkel als Parameter; Richtung mit `kleiner`/`groesser` aus Sicht der Skizze.
- Seitenflächen schräger Features über `nahe` ansprechen; Ecken über Eckradius in der Skizze runden (wird mitgeschrägt).
- Ein Trichter wird von der engen Seite aus skizziert (`groesser`) oder von der weiten (`kleiner`) – maßgebend ist, welcher
  Durchmesser Anforderung ist.

## 8. Spike S16 (vor dem Plan-Code)

Live gegen SW 2025, Ergebnisse in `docs/formschraege/ergebnisse.md` und `docs/stufe0/ergebnisse/s16_*.json`,
Skript `spikes/s16_formschraege.py`:
1. `Ddir1` ↔ `kleiner`/`groesser` für Aufsatz und Schnitt, jeweils ohne und mit `umkehren`.
2. Verhalten bei `mittig` (beide Seiten geschrägt, Richtung je Seite), `durch_alles`, `bis_flaeche`,
   `versatz_von_flaeche`.
3. Mehrere Profile (Ring): Richtung des Innenrands.
4. Name des Winkelmaßes am Feature und Verknüpfung über Gleichung (wie `D1`).
5. Messung: `IFace2.Normal` der ebenen Seitenflächen, `ISurface.ConeParams` und Vorzeichen bei Kegelflächen; Toleranz für
   `winkel_grad`.
6. Rechteck mit Eckradius bei `kleiner`, wenn T·tan α den Radius erreicht (bestätigt oder lockert Regel §5.2).
7. Volumen gegen §6.2 (Kreis, Rechteck, Rechteck mit Eckradius, Polygon, `mittig`).

Ergibt der Spike, dass ein Punkt nicht geht, wird er vor dem Weiterbauen mit dem Nutzer entschieden (Umfang kürzen oder
Notausgang).

## 9. Referenzteil *Zentrieraufnahme*

Selbst definiert (`tests/referenz/zentrieraufnahme/`), allgemeine Konstruktion; nutzt beide Richtungen, Aufsatz und
Schnitt, Kreis, Rechteck mit Eckradius und vier Endbedingungen:

| Element | Feature | Profil | Ende | Formschräge |
|---|---|---|---|---|
| Grundplatte | extrusion | Rechteck mit Eckradius | blind | – |
| Zentrierzapfen | extrusion auf der Deckfläche | Kreis | blind | `kleiner`, ~15° |
| Einführtasche | schnitt von der Deckfläche | Rechteck mit Eckradius | blind | `kleiner`, ~10° |
| Trichter-Durchbruch | schnitt von der Unterseite | Kreis (Auslauf-Ø) | `durch_alles` | `groesser` (oben weit) |
| Steg | extrusion auf Ebene vorne, ragt in die Platte | Rechteck | `mittig` | `kleiner` |

Maße, Winkel und Prüfmaße legt der Plan fest; das Sollvolumen steht ausdrücklich in `sollvolumen.py` (Trichter
`durch_alles`, Steg überlappt die Platte – `volumen_auto` reicht dafür nicht).

**Negativfälle** (Live, Spec unverändert und gültig, Fehler im Bau eingeschleust):
1. Richtung vertauscht (`Ddir1` invertiert) → `formschraegen` Mangel mit Knoten.
2. Winkel verfälscht → `formschraegen` Mangel mit Knoten.

**Negativfälle ohne SolidWorks** (`validieren`): Winkel ≥ 90°, Profil fällt zusammen (Kreis und Eckradius),
Flächenanker `"+x"` an einem Feature mit Formschräge, `senkrechte_kanten` an einem Feature mit Formschräge.

## 10. Tests

- Ohne SolidWorks: Schema (gültig/ungültig), Befunde §5, Hinweis `feste_zahl` für den Winkel, `volumen_auto` je Profil
  und `mittig`, Bewertung `formschraegen` aus erfundenen Messwerten (Winkel, Vorzeichen, fehlendes Feature,
  nicht messbare Fläche), Bericht.
- Mit SolidWorks (`-m sw`): je Kombination aus Aufsatz/Schnitt × `kleiner`/`groesser` ein Minimalteil, `mittig`,
  Kegel- und Ebenenmessung; Referenz Zentrieraufnahme; die zwei Negativfälle.
- Regressions-Suite: alle bisherigen Referenzen bestehen weiter (die Option ist rein additiv; ohne `formschraege`
  identische Aufrufe).

## 11. Fertig, wenn

Spike S16 dokumentiert; Referenz *Zentrieraufnahme* besteht (Code-Prüfungen und Prüfer); die Negativfälle werden
erkannt; Regressions-Suite besteht weiter; Skill `konstruieren`, Prüfer, CLAUDE.md und Design §11 nachgezogen.

## 12. Nicht im Paket

- Eigenes Feature `formschraege` an beliebigen Flächen (`InsertMultiFaceDraft`, Neutralebene, Trennlinie, Stufenschräge)
  – kommt bei Bedarf über `compiler-erweitern`.
- Formschräge an `rotation`, `verzahnung`, `normbohrung`, Mustern als eigene Option (Muster schrägen Features kopieren die
  Schräge ohnehin mit).
- Entformungsanalyse (`MoldDraftAnalysis`), Mindestschräge, Werkzeugbau-Prüfungen.
- Unterschiedliche Winkel je Seite bei `mittig` (`Dang2`).
