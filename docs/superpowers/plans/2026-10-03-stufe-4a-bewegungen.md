# Stufe 4a – Bewegungen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** swki baut Baugruppen mit beweglichen Komponenten (Grenzverknüpfungen für Abstand und Winkel, Scharnier, gezählte Freiheitsgrade), speichert sie in Grundstellung und prüft in `swki pruefen` jede Bewegung schrittweise: Kollision je Stellung, Grenze wirkt, Freiheitsgrad belegt, Endlagen, Paarläufe für Bewegungen mit sich schneidenden Räumen.

**Architecture:** Erweiterung des Pakets `swki/baugruppe/`. Neu: `bewegung.py` (Logik ohne SolidWorks: Bewegungen aus der Spec, Lagevergleich, Räume, Paare, Bewertung), `bewegungslauf.py` (Ablauf der Prüfung über eine Mechanik-Schnittstelle, mit Attrappe testbar), `sw_bewegung.py` (SolidWorks-Mechanik), `swki/speicher.py` (Private Bytes). Schema, Auflösen, Plausibilität, Passung, Freigabe, Bau (Grundstellung), Prüfen, Bewertung, Bericht und `swki aenderungen` werden erweitert. Ein Scharnier wird zu zwei SolidWorks-Verknüpfungen.

**Tech Stack:** Python ≥ 3.13, pywin32 (Late Binding), ctypes (Private Bytes), PyYAML, jsonschema, pytest; SOLIDWORKS 2025 (Rechner A) für Spike und Live-Tests.

**Spec:** `docs/superpowers/specs/2026-10-03-stufe-4a-bewegungen-design.md` (mit dem Nutzer abgestimmt, 2026-10-03). Kontext: `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md`, `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`.

## Präzisierungen gegenüber der Spec (vom Planer, bindend für diesen Plan)

1. **Scharnier = zwei Verknüpfungen (Spec §4.2):** `scharnier` wird beim Auflösen zu `konzentrisch` (ID `<id>`, ohne Drehsperre) und `deckungsgleich` der Anlage (ID `<id>.anlage`, Ausrichtung aus `ausrichtung`, Vorgabe `entgegengesetzt`). Das ist der Rückfall der Spec, hier als Regelweg: beide Typen sind seit Spike S12 belegt, `swMateHINGE` (22) über `AddMate5` wird nicht verwendet. **Dem Nutzer bei der Übergabe melden.**
2. **Grenzverknüpfung:** `AddMate5` mit `swMateDISTANCE` (5) bzw. `swMateANGLE` (6), `Distance`/`Angle` = `min`, `…AbsUpperLimit` = `max`, `…AbsLowerLimit` = `min` (Spike S13 Zeile 1/2). Bewegt wird Seite `a`.
3. **Befundcodes in `validieren`:** `GRENZE_FESTE_ZAHL`, `FREIHEITSGRADE_NICHT_UNTERSTUETZT`, `BEWEGUNG_FEHLT`, `BEWEGUNG_DOPPELT` stehen als Präfix in der Meldung des Befunds (Befunde sind `{pfad, meldung}`). Zusätzliche Befunde: die bewegte Komponente einer Bewegung braucht `freiheitsgrade: 1` (Komponente oder Gruppe) und darf nicht fixiert sein; Grenzverknüpfungen und Scharniere nennen keine Komponente mit `je_position`; eine Grenze treibt höchstens eine Bewegung.
4. **„Grenze wirkt“ (Spec §8.2.4):** Ein Schritt außerhalb der Grenze „geht durch“, wenn die treibende Verknüpfung ohne Meldung gelöst wird **und** die bewegte Komponente den Sollweg erreicht (`|Weg − |w − min|| ≤ anker_mm` bzw. ≤ 0,01°; Weg = Betrag der Verschiebung bzw. Drehwinkel gegenüber der ersten Stellung). So hängt das Ergebnis nicht davon ab, wie SolidWorks den Fehlschlag meldet (Spike S13 Zeile 3). Der Schritt unter `min` entfällt bei `min = 0` (negativer Abstand bzw. Winkel ist nicht darstellbar; im Bericht `unten: null`).
5. **Freiheitsgrad belegt (Spec §8.1/§8.2.2):** Gelesen wird zweimal: statisch in Grundstellung ohne Antrieb (muss `unterbestimmt` sein) und einmal mit allen Antrieben auf `min` (muss `voll bestimmt` sein). Beides ergibt die Prüfung `freiheitsgrad:<komponente>`. Die statische Bestimmtheitsprüfung aus 3b erlaubt `unterbestimmt` bei `freiheitsgrade: 1`.
6. **Toleranzen:** Endlage-Verschiebung je Achse `toleranzen.anker_mm` (0,1 mm); Drehung über den Abweichungswinkel zwischen gemessener und Soll-Drehung ≤ 0,01°.
7. **Bewegte Menge und Raum:** Instanzen, deren `Transform2` sich in einer Stellung des Grundstellungslaufs gegenüber der ersten Stellung ändert (> 0,001 mm bzw. > 1e-6 in der Drehung). Überstrichener Raum = Vereinigung ihrer Hüllquader (`IComponent2.GetBox(False, False)`, mm) über alle Stellungen. Zwei Bewegungen bilden ein Paar, wenn sich ihre Räume in allen drei Achsen um mehr als 0,001 mm überschneiden.
8. **Neue Kollision:** ein Komponentenpaar, das in der statischen Prüfung nicht überlappte (statische Mängel und Gewindepaarungen bleiben in der statischen Prüfung).
9. **Prüfsumme:** `bewegungen` geht nur in die Prüfsumme ein, wenn die Spec den Schlüssel hat – bestehende Freigaben (ohne Bewegungen) bleiben gültig.
10. **Protokoll:** Grundstellung als Knoten `grundstellung:<Bewegung>` (Typ `grundstellung`), Phase `grundstellung` nur bei Specs mit Bewegungen.
11. **Bilder:** `<Bewegung>-min|mitte|max.png` und `<Bewegung>-kollision-[<Gegenbewegung>-]<n>.png` im Bilderordner des Laufs; im Prüfbericht unter `bilder` mit dem Dateinamen ohne Endung als Schlüssel.
12. **`swki aenderungen`:** Soll einer Grenzverknüpfung ist ihr Wert in Grundstellung (`min`), weil `bauen` in Grundstellung speichert (Spike S13 Zeile 1: Maß `D1` = aktueller Wert).
13. **Negativfälle (Spec §12, nachgezogen):** Fall 1 erwartet `{bewegung_kollision:Hebelschwenk, bewegung_kollision:Schlittenhub}` – beide Paarläufe treffen den Anschlag. Fall 3 legt `g1` an die Flächen +x (eine umgekehrte `ausrichtung` bei Abstand 0 würde den Schlitten um 180° drehen wollen und schon beim Bau scheitern). Fall 4 lässt statt des Scharniers die seitliche Führung des Schlittens (`v21`) weg → `{freiheitsgrad:schlitten}` (Annahme Spike S13 Zeile 4); „Hebel nur konzentrisch“ ließe die Höhe des Hebels offen (Einfügelage im Ursprung, Zusatzkollisionen mit der Grundplatte). **Dem Nutzer bei der Übergabe melden.**
14. **`SPEICHER_KNAPP`:** `swki pruefen` endet mit Exit 1 und `{"fehler", "code": "SPEICHER_KNAPP", "privat_mb", "grenze_mb"}`, ohne Prüfbericht; die Dokumente werden ohne Speichern geschlossen.

## Global Constraints

- **Umfang 4a:** `grenze_abstand`, `grenze_winkel`, `scharnier`, `freiheitsgrade` mit `1`, `bewegungen` (`name`, `grenze`, `schritte`, `erwartet.endlagen`), Bewegungsprüfung in `swki pruefen`. Nicht: Zahnrad, Nut, Kurve, gekoppelte Antriebe, Teilbereiche (`von`/`bis`), Mindestabstände über den Weg, mehr als ein Freiheitsgrad je Komponente, Motion-Studien, Unterbaugruppen.
- **Freigabe:** Prüfsumme der Baugruppe über `art, name, parameter, eigenschaften, komponenten, freiheitsgrade, pruefung`, zusätzlich `bewegungen` (nur wenn vorhanden), plus `teile`. **Verknüpfungen (auch Grenzen und Scharniere) sind Bauweg**; `min`/`max` einer Grenze sind `0` oder ein Parameter-Ausdruck.
- **Antrieb nur während der Prüfung:** Das gebaute Modell enthält keine treibenden Verknüpfungen; `bauen` stellt die Grundstellung (alle bewegten Komponenten auf `min`) her und löscht die treibenden Verknüpfungen vor dem Speichern. `swki pruefen` legt sie vorübergehend an und schließt **ohne Speichern**; `pruefen` und `aenderungen` speichern nie.
- **Bewegungsprüfung:** je Bewegung `schritte + 1` Stellungen `min … max`; Kollision je Stellung (Berührung ist keine Kollision, Gewindepaarungen aus der Statik); „Grenze wirkt“; „Freiheitsgrad belegt“; Endlagen; Paarläufe nur für Paare mit sich schneidenden Räumen (andere Bewegung auf `max`, die übrigen auf `min`).
- **Vorgaben in `config/standard.yaml`:** `bewegung_schritte: 16`, `speicher_grenze_mb: 3500` (Annahmen; nach Spike S13 Zeile 8 bestätigen oder per Ledger ändern).
- **Late Binding** (`swki/wissen/pywin32-fallstricke.md`): nullargumentige COM-Member **ohne** `()` (`Transform2`, `GetConstrainedStatus`, `Name2`, `GetProcessID`, `GetFirstDisplayDimension`, `GetSpecificFeature2`, `MinimumVariation`, `MaximumVariation`, `SystemValue`, `EvaluateAll`, `EditRebuild3` …); nullargumentige Aktionen (`EditDelete`, `Done`, `FixComponent`) über `sw_baugruppe.rufe`.
- **API nachschlagen:** vor jedem **neuen** SolidWorks-API-Aufruf `.venv\Scripts\python.exe -m swki api methode <Interface.Member>` bzw. `… api enum <Name>` (vorher `PYTHONIOENCODING=utf-8`). `.venv\Scripts\python.exe -m swki api pruefe-code` muss ohne Befunde bleiben. Bereits nachgeschlagen (2026-10-03): `IAssemblyDoc.AddMate5` (15 Parameter: MateTypeFromEnum, AlignFromEnum, Flip, Distance, DistanceAbsUpperLimit, DistanceAbsLowerLimit, GearRatioNumerator, GearRatioDenominator, Angle, AngleAbsUpperLimit, AngleAbsLowerLimit, ForPositioningOnly, LockRotation, WidthMateOption, ErrorStatus; seit 2015), `swMateType_e` (DISTANCE 5, ANGLE 6, HINGE 22 – nicht verwendet), `IMate2.MinimumVariation`/`MaximumVariation`/`Alignment` (Property, 0), `IComponent2.GetBox` (2: IncludeRefPlanes, IncludeSketches), `IComponent2.GetConstrainedStatus` (0), `ISldWorks.GetProcessID` (0), `IDimension.SetSystemValue3` (3: NewValue, WhichConfigurations, Config_names), `swSetValueInConfiguration_e` (InThisConfiguration 1), `IFeature.GetFirstDisplayDimension` (0), `IFeature.GetNextDisplayDimension` (1: DispIn), `IDisplayDimension.GetDimension2` (1: Index), `IDimension.Name`/`FullName` (Property).
- **Einheiten:** Spezifikation und Ausgaben in mm und Grad; die API rechnet in m und rad (`mm()`, `grad()`, `in_mm()` aus `swki.verbindung`).
- **Bestand bleibt:** Referenzen *Buchse*, *Formplatte*, *Auswerferhalteplatte*, *Stehlager* bestehen weiter; Verhalten für Teile und Baugruppen ohne `bewegungen` unverändert.
- **Prüfwerte nie an Messwerte anpassen.** Testerwartungen der Negativfälle nie abschwächen; weicht ein Live-Ergebnis ab, anhalten (NEEDS_CONTEXT) und dem Controller den Prüfbericht-Auszug melden.
- **Sprache:** Code-Bezeichner, Docstrings, Kommentare, Commit-Messages, Berichte auf Deutsch (mit Umlauten in Texten).
- **Tests:** `.venv\Scripts\python.exe -m pytest -q` (ohne SolidWorks; Stand vor dem Plan: **622 passed, 109 deselected**). Jeder Task nennt die neuen Tests; maßgeblich ist „vorher + neu“, abweichende Zahlen im Bericht begründen. Live-Tests nur einzeln: `.venv\Scripts\python.exe tests\live_einzeln.py <datei::test-id> --zeit 600` mit `PYTHONIOENCODING=utf-8`.
- **SolidWorks-Speicher (Live-Tasks):** Private Bytes messen (`Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`), nicht das Working Set. Der Implementer hält ab ca. 3 GB **vor** dem nächsten Live-Test an und meldet BLOCKED (Speicher) mit den offenen Test-IDs; **der Controller startet SolidWorks neu** und setzt den Implementer fort. Vor jedem Referenz- und Negativlauf mit Baugruppe frisches SolidWorks (BLOCKED Neustart). Genau eine Instanz (`tasklist /V /FI "IMAGENAME eq SLDWORKS.exe"`); Einstellungen vor und nach Live-Läufen `False 1` (`.venv\Scripts\python.exe -c "from swki.konfig import lade_rechner; from swki.verbindung import verbinde; app = verbinde(lade_rechner().sw_jahr); print(app.GetUserPreferenceToggle(10), app.GetUserPreferenceIntegerValue(6))"`). Implementer starten oder beenden SolidWorks nie.
- **Nur eigene Dokumente** anfassen; speichern nur im `arbeitsordner` aus `config/rechner.yaml`; nie ein SolidWorks-Jahr oder einen Pfad fest in Code schreiben; nie in die Normteilbibliothek schreiben (außer `swki normteil`).
- **Git:** Branch `stufe-4a` (von `plan-stufe-4a`), kleine Commits je Task; Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; **kein `git push` ohne Rückfrage**; nichts aus `auftraege/` committen; erzeugte SolidWorks-Dateien nie committen; immer gezielt `git add <dateien>`. Zeilenenden der bestehenden Dateien beibehalten (Edit-Werkzeug; kein sed auf CRLF-Dateien).
- **Subagents:** Implementer starten keine Subagents. Prüfer-Agenten startet der Controller. Nie zwei Implementer gleichzeitig, solange SolidWorks läuft.

## Dateistruktur nach diesem Plan

```
schema/baugruppe.schema.json            + grenze_abstand, grenze_winkel, scharnier, min/max, anlage_a/b; freiheitsgrade 1; bewegungen
swki/baugruppe/aufloesen.py             Verknuepfung.min/max, GRENZEN, ANLAGE; Scharnier → konzentrisch + deckungsgleich
swki/baugruppe/plausibel.py             Grenzen, Scharnier, freiheitsgrade-Zahl, Bewegungen
swki/baugruppe/passung.py               passt_drehbolzen() für Scharniere
swki/baugruppe/hinweise.py              Hinweis pruefaufwand
swki/spec/freigabe.py                   bewegungen in der Prüfsumme (nur wenn vorhanden)
swki/aenderungen.py                     Soll der Grenzverknüpfung = min
config/standard.yaml                    bewegung_schritte, speicher_grenze_mb
swki/baugruppe/bewegung.py              neu: Bewegung, Lagevergleich, Räume, Paare, Bewertung (ohne SolidWorks)
swki/baugruppe/bewegungslauf.py         neu: fahre() über die Mechanik-Schnittstelle, SpeicherKnapp, StellungFehler
swki/speicher.py                        neu: privat_mb(pid)
swki/baugruppe/sw_baugruppe.py          Grenzen in verknuepfe, treibe(), stelle(), loesche(), kiste()
swki/baugruppe/sw_bewegung.py           neu: SwMechanik
swki/baugruppe/fehler.py                + GRUNDSTELLUNG_FEHLER
swki/baugruppe/bau.py                   _grundstellung() vor dem Speichern
swki/baugruppe/bewertung.py             freiheitsgrade 1 erlaubt unterbestimmt
swki/baugruppe/pruefen.py               Bewegungsprüfung nach der Statik, Kontexte der Grenzflächen offen halten
swki/pruefung/bilder.py                 iso_bild()
swki/pruefung/bericht.py                Abschnitt Bewegungen
spikes/s13_bewegung.py                  Spike S13 (Ergebnis docs/stufe0/ergebnisse/s13_bewegung.json)
tests/baugruppe/beispiel_bewegung.py    Bewegungsprobe (Grundplatte, Schieber, Bolzen, Hebel)
tests/baugruppe/test_bewegung_spec.py, test_bewegung_plausibel.py, test_bewegung.py, test_bewegungslauf.py,
tests/baugruppe/test_sw_bewegung.py, tests/test_speicher.py, tests/baugruppe/test_schlitten_spec.py
tests/live/test_live_bewegung.py, tests/live/test_live_schlitten.py
tests/referenz/schlitten/               Referenz Linearschlitten (5 Specs + eingabe/beschreibung.md) + Eintrag in test_referenzen.py
.claude/skills/baugruppe/SKILL.md, .claude/agents/pruefer.md, CLAUDE.md, Design §4/§11, Spec 4a §12
docs/stufe4a/ergebnisse.md              Ergebnisse 4a
```

## Abhängigkeiten vom Spike S13 (Task 1)

Der Plan-Code setzt die Spalte „Annahme“ voraus. Weicht der Spike ab, entscheidet der Controller nach der Spalte „sonst“ und hält es im Ledger fest, bevor der betroffene Task beginnt.

| # | Frage | Annahme (Plan-Code) | sonst | betrifft |
|---|---|---|---|---|
| 1 | `AddMate5` Typ 5 mit Grenzen | Status 1, Feature umbenennbar, `MinimumVariation`/`MaximumVariation` = Grenzen (m), Maß `D1` = aktueller Abstand | Grenzen anders übergeben (z. B. `Distance` = Mitte) – im Ledger, `_mate_werte` anpassen; geht gar nicht: Nutzer fragen | 6, 7 |
| 2 | Maße der Grenzen und Gleichung | obere Grenze heißt `D2`, untere `D3`; `"D2@g1" = "HUB"` bindet, nach `HUB` = 120 ist die Grenze 120 | `GRENZ_MASSE` auf die gemessenen Namen setzen; keine Bindung möglich: `GRENZ_MASSE = {}` (Werte aus den Parametern beim Bau, Schutz über die Freigabe; Ledger) | 6 |
| 3 | Antrieb neben der Grenze | innerhalb: gelöst, Weg = `w − min`; über `max`: irgendeine Meldung **oder** Lage bleibt bei `max`; zurück auf `max` wieder gelöst | bleibt der Zustand nach dem Schritt über die Grenze fehlerhaft: in `bewegungslauf._zurueck` den Antrieb löschen und neu anlegen (Ledger) | 5, 6 |
| 4 | Bestimmtheit | nur Grenze: bewegte Komponente 2; mit Antrieb 3; Mitfahrer (Bolzen im Schieber, Hebel mit eigenem Antrieb) melden 3; Antrieb genau auf `min` neben der Grenze: nicht 4 | Mitfahrer melden 2: statische Bestimmtheit erlaubt `unterbestimmt` für Mitglieder bewegter Mengen; Negativfall 4 erwartet zusätzlich `freiheitsgrad:hebel` (Ledger); Status 4 auf `min`: Antrieb auf `min + 1e-6` (Ledger) | 4, 7, 9 |
| 5 | Antrieb löschen | Lage bleibt; nach Speichern, Öffnen, Verstellen und Schließen ohne Speichern sind alle SHA-256 unverändert | Lage springt: Grundstellung nach dem Löschen erneut messen und protokollieren (Ledger); Hash ändert sich: Nutzer fragen (Änderungserkennung) | 6, 7 |
| 6 | `IComponent2.GetBox(False, False)` | Baugruppenkoordinaten, deckt sich mit der umgerechneten Teilebox (± 0,01 mm) | `kiste()` aus Teilebox und `Transform2` rechnen (8 Ecken, Ledger) | 6 |
| 7 | Drehsinn Winkelantrieb (Flächen +z/+z, gleich) | 0 → 90 dreht um +y (Rechte-Hand-Regel), also +x → −z | Endlage der Probe und der Referenz auf Achse `[0, -1, 0]`, Anschlag in Negativfall 1 nach +z spiegeln (Ledger) | 3, 8, 9 |
| 8 | Zeit und Speicher je Schritt | Probe < 0,5 s, ~100 Komponenten < 3 s je Schritt; Private Bytes wachsen < 5 MB je Schritt | `bewegung_schritte` auf 8 setzen bzw. `speicher_grenze_mb` nach Messung; starkes Wachstum: Nutzer fragen (Spec §11.7) | 3, 7 |
| 9 | Iso-Bild mit aktivem Antrieb | PNG > 0 Byte, Dokument bleibt geöffnet | Bilder erst nach `loese` je Stellung (Ledger) | 6 |

---

### Task 1: Spike S13 – Grenzen, Antrieb, Bestimmtheit, Lage, Zeit und Speicher (live)

**Files:**
- Create: `spikes/s13_bewegung.py`
- Ergebnis: `docs/stufe0/ergebnisse/s13_bewegung.json` (schreibt der Spike; wird committet)

**Interfaces:**
- Consumes: `baue_teil_dokument` (Teil-Bau), `sw_baugruppe` (`neue_baugruppe`, `fuege_ein`, `fixiere`, `in_baugruppe`, `waehle`, `verknuepfe`, `verknuepfungen`, `fehlercode`, `_loesche`, `transform`, `status`, `interferenzen`, `komponenten`, `aufloesen`), `loese_im_teil`, `normteil_befehle.hole`, `kontext_aus_datei`, `oeffne`.
- Produces: Antworten auf die 9 Zeilen der Tabelle „Abhängigkeiten vom Spike S13“.

- [ ] **Step 1: Vorbedingungen prüfen**

SolidWorks 2025 läuft, genau eine Instanz, keine fremden offenen Dokumente, Einstellungen `False 1` (Befehle in den Global Constraints). Private Bytes notieren. `config/rechner.yaml` hat `vorlage_baugruppe`. Sonst anhalten und melden.

- [ ] **Step 2: `spikes/s13_bewegung.py` schreiben**

```python
"""S13 (Stufe 4a): Grenzverknüpfungen, treibende Verknüpfung, Bestimmtheit, Lage, Hüllquader, Zeit und Speicher.

1 AddMate5 swMateDISTANCE mit Grenzen (Distance = min, DistanceAbsUpperLimit = max, DistanceAbsLowerLimit = min):
  Status, IMate2.MinimumVariation/MaximumVariation, Maße des Features (Name, Wert), Maß D1.
2 Gleichung auf das Maß der oberen Grenze ("<Name>@g1" = "HUB") bindet; nach HUB = 120 ist die Grenze 120? Dito Winkel.
3 Treibende Verknüpfung (Abstand an denselben Flächen) neben der Grenze: innerhalb verstellen (Weg = Wert?), über max
  hinaus (Rebuild, Fehlercodes, Weg), zurück auf max (wieder gelöst?).
4 GetConstrainedStatus: nur Grenzen, mit Antrieb des Schiebers, mit beiden Antrieben; Mitfahrer (Bolzen) jeweils.
5 Antriebe löschen: Lage bleibt; speichern, schließen, öffnen, verstellen, ohne Speichern schließen → SHA-256 gleich.
6 IComponent2.GetBox(False, False) gegen die mit Transform2 umgerechnete Teilebox.
7 Drehsinn: Winkelantrieb 0 → 45 → 90 an den Flächen +z/+z (gleich): Drehachse und Winkel aus Transform2.
8 Zeit und Private Bytes je Schritt (stellen + Rebuild, Kollision, Lage und Hüllquader) an der Probe und an der Probe
  mit 96 zusätzlichen fixierten Stiften (~100 Komponenten), je 20 Schritte.
9 Iso-Bild mit aktivem Antrieb.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s13_bewegung
"""

import ctypes
import hashlib
import math
import shutil
import time
from ctypes import wintypes
from pathlib import Path

import pythoncom

from spikes._gemeinsam import lauf
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import Verknuepfung
from swki.baugruppe.referenzen import loese_im_teil
from swki.compiler import sw
from swki.compiler.bauen import baue_teil_dokument
from swki.compiler.fehler import BauFehler
from swki.compiler.protokoll import Protokoll
from swki.konfig import lade_rechner, lade_standard
from swki.normteile import befehle as normteil_befehle
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.schluessel import loese_auf
from swki.pruefung.bilder import ANSICHTEN, SW_TIFF_SCREEN_OR_PRINT_CAPTURE
from swki.pruefung.messen import kontext_aus_datei, oeffne
from swki.verbindung import byref_long, grad, in_mm, mm, r8_array, verbinde

AUFTRAG = "S13"
TYP = {"abstand": 5, "winkel": 6}  # swMateType_e


def _block(name, laenge, breite, hoehe, weitere):
    return {"art": "teil", "name": name, "material": "1.0038", "eigenschaften": {"Benennung": name},
            "parameter": {"L": laenge, "B": breite, "H": hoehe},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "oben",
                                     "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
                          "ende": {"typ": "blind", "tiefe": "=H"}}, *weitere]}


PLATTE = _block("S13_Platte", 200, 60, 20, [])
SCHIEBER = _block("S13_Schieber", 60, 40, 20, [
    {"id": "f2", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[10, 0]], "durch": True}])
HEBEL = _block("S13_Hebel", 50, 12, 8, [
    {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[-18, 0]],
     "durchmesser": 8.5, "durch": True}])


class _Speicher(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]


def _privat_mb(pid):
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    k32.K32GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(_Speicher), wintypes.DWORD)
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    try:
        z = _Speicher()
        z.cb = ctypes.sizeof(z)
        if not k32.K32GetProcessMemoryInfo(h, ctypes.byref(z), z.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return round(z.PrivateUsage / 2 ** 20, 1)
    finally:
        k32.CloseHandle(h)


def _v(vid, typ, ausrichtung=None, wert=None, sperren=False):
    return Verknuepfung(vid, vid, typ, {}, {}, ausrichtung, wert, sperren)


def _rebuild(asm):
    try:
        sw.rebuild(asm)
        return "ok"
    except BauFehler as e:
        return str(e)


def _sha(ordner):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ordner.glob("*.SLD*"))
            if p.suffix.lower() in (".sldprt", ".sldasm")}


def _teile(app, r, standard, ordner):
    """Platte, Schieber, Hebel bauen und speichern (bleiben offen), Bolzen ISO 8734 8 × 30 holen und öffnen."""
    teile = {}
    for name, spec in (("platte", PLATTE), ("schieber", SCHIEBER), ("hebel", HEBEL)):
        model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, ordner / f"{name}.yaml", AUFTRAG,
                                                Protokoll(AUFTRAG, f"{name}.yaml", 0, r.sw_jahr))
        if fehler is not None:
            raise fehler
        sw.speichere(model, ordner / f"{spec['name']}.sldprt")
        teile[name] = (model, ctx)
    t, a = loese_auf("ISO 8734", "8x30", None)
    ziel = ordner / f"{a.schluessel}.sldprt"
    shutil.copy2(normteil_befehle.hole("ISO 8734", "8x30", None)["pfad"], ziel)
    model = oeffne(app, ziel)
    teile["bolzen"] = (model, kontext_aus_datei(app, model, erzeuge_spec(t, a, vorlage_text(t)), ziel.with_suffix(".yaml"),
                                                standard["toleranzen"]["anker_mm"], {"knoten": []}))
    return teile


def _probe(app, r, teile):
    """Bewegungsprobe ohne Grenzen: Schieber auf der Platte (bündig -z), Bolzen im Schieber, Hebel (Scharnier als
    konzentrisch + Anlage). Liefert (asm, Komponenten, Entität-Funktion)."""
    asm = sw_baugruppe.neue_baugruppe(app, r.vorlage_baugruppe)
    k = {}
    for name in ("platte", "schieber", "bolzen", "hebel"):
        model = teile[name][0]
        k[name] = sw_baugruppe.fuege_ein(app, asm, Path(model.GetPathName), sw.teilebox_mm(model))
    sw_baugruppe.fixiere(asm, k["platte"])

    def e(name, seite):
        return sw_baugruppe.in_baugruppe(k[name], loese_im_teil(teile[name][1], seite))

    f1 = {"feature": "f1"}
    sw_baugruppe.verknuepfe(asm, _v("v1", "deckungsgleich", "entgegengesetzt"), e("schieber", {**f1, "flaeche": "-y"}),
                            e("platte", {**f1, "flaeche": "+y"}), {})
    sw_baugruppe.verknuepfe(asm, _v("v2", "deckungsgleich", "gleich"), e("schieber", {**f1, "flaeche": "-z"}),
                            e("platte", {**f1, "flaeche": "-z"}), {})
    sw_baugruppe.verknuepfe(asm, _v("v3", "deckungsgleich", "entgegengesetzt"), e("bolzen", {"referenz": "EINBAU_EBENE_1"}),
                            e("schieber", {**f1, "flaeche": "-y"}), {})
    sw_baugruppe.verknuepfe(asm, _v("v4", "konzentrisch", sperren=True), e("bolzen", {"referenz": "EINBAU_ACHSE"}),
                            e("schieber", {"feature": "f2", "instanz": 1, "achse": True}), {})
    sw_baugruppe.verknuepfe(asm, _v("s1", "konzentrisch"), e("hebel", {"feature": "f2", "instanz": 1, "achse": True}),
                            e("bolzen", {"referenz": "EINBAU_ACHSE"}), {})
    sw_baugruppe.verknuepfe(asm, _v("s1.anlage", "deckungsgleich", "entgegengesetzt"), e("hebel", {**f1, "flaeche": "-y"}),
                            e("schieber", {**f1, "flaeche": "+y"}), {})
    return asm, k, e


def _masse(feature):
    ergebnis = []
    d = feature.GetFirstDisplayDimension
    while d is not None:
        dim = d.GetDimension2(0)
        ergebnis.append({"name": dim.Name, "voll": dim.FullName, "wert": dim.SystemValue})
        d = feature.GetNextDisplayDimension(d)
    for n in ("D1", "D2", "D3", "D4"):
        p = feature.Parameter(n)
        ergebnis.append({"parameter": n, "wert": None if p is None else p.SystemValue})
    return ergebnis


def _grenze(asm, name, art, a, b, ausrichtung, unten, oben):
    """Grenzverknüpfung direkt über AddMate5 (der Handler kommt mit Task 6)."""
    sw.auswahl_leeren(asm)
    sw_baugruppe.waehle(asm, a, False)
    sw_baugruppe.waehle(asm, b, True)
    status = byref_long()
    if art == "abstand":
        w = (mm(unten), mm(oben), mm(unten), 0.0, 0.0, 0.0)
    else:
        w = (0.0, 0.0, 0.0, grad(unten), grad(oben), grad(unten))
    vorher = len(sw_baugruppe.verknuepfungen(asm))
    mate = asm.AddMate5(TYP[art], sw_baugruppe.AUSRICHTUNG[ausrichtung], False, w[0], w[1], w[2], 1, 1, w[3], w[4], w[5],
                        False, False, 0, status)
    sw.auswahl_leeren(asm)
    alle = sw_baugruppe.verknuepfungen(asm)
    neu = alle[-1] if mate is not None and len(alle) > vorher else None
    e = {"status": status.value, "mate": mate is not None, "neu": neu is not None}
    if neu is not None:
        neu.Name = name
        e["name"] = neu.Name
        e["rebuild"] = _rebuild(asm)
        e["fehlercode"] = sw_baugruppe.fehlercode(neu)
        spez = neu.GetSpecificFeature2
        for attr in ("Type", "MinimumVariation", "MaximumVariation", "Alignment"):
            try:
                e[attr] = getattr(spez, attr)
            except Exception as ex:  # Spike: festhalten
                e[attr] = repr(ex)
        e["masse"] = _masse(neu)
    return neu, e


def _setze_gv(asm, name, wert):
    gl = asm.GetEquationMgr
    index = next(i for i in range(gl.GetCount) if gl.Equation(i).startswith(f'"{name}"'))
    dispid = gl._oleobj_.GetIDsOfNames("Equation")
    gl._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, f'"{name}" = {wert}')
    gl.EvaluateAll
    return _rebuild(asm)


def _binde(asm, grenze, masse, oben_sw, gv, gv_wert, gv_neu):
    """Gleichung auf das Maß mit dem Wert der oberen Grenze; danach gv ändern und die Grenze lesen."""
    name = next((m["name"] for m in masse if "name" in m and abs(m["wert"] - oben_sw) < 1e-9), None)
    e = {"mass_obere_grenze": name}
    if name is None:
        return e
    gl = asm.GetEquationMgr
    e["add_gv"] = gl.Add2(-1, f'"{gv}" = {gv_wert}', True)
    e["add_bindung"] = gl.Add2(-1, f'"{name}@{grenze.Name}" = "{gv}"', True)
    e["rebuild"] = _rebuild(asm)
    e["rebuild_nach_aenderung"] = _setze_gv(asm, gv, gv_neu)
    spez = grenze.GetSpecificFeature2
    e["MaximumVariation_nach_aenderung"] = spez.MaximumVariation
    e["masse_nach_aenderung"] = _masse(grenze)
    e["rebuild_zurueck"] = _setze_gv(asm, gv, gv_wert)
    return e


def _drehung(t):
    return [[t[3 * j + i] for j in range(3)] for i in range(3)]


def _achse_winkel(t0, t1):
    c0, c1 = _drehung(t0), _drehung(t1)
    q = [[sum(c1[i][k] * c0[j][k] for k in range(3)) for j in range(3)] for i in range(3)]
    w = math.degrees(math.acos(max(-1.0, min(1.0, (q[0][0] + q[1][1] + q[2][2] - 1) / 2))))
    v = (q[2][1] - q[1][2], q[0][2] - q[2][0], q[1][0] - q[0][1])
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return [round(c / n, 6) for c in v], round(w, 4)


def _weg(t0, t1):
    return round(math.sqrt(sum(in_mm(t1[9 + i] - t0[9 + i]) ** 2 for i in range(3))), 4)


def _stelle(asm, antrieb, art, wert, k, t0):
    mass = antrieb.Parameter("D1")
    mass.SetSystemValue3(mm(wert) if art == "abstand" else grad(wert), 1, None)
    e = {"wert": wert, "rebuild": _rebuild(asm),
         "fehlercodes": {f.Name: c for f in sw_baugruppe.verknuepfungen(asm) if (c := sw_baugruppe.fehlercode(f))}}
    t = sw_baugruppe.transform(k)
    e["weg"] = _weg(t0, t) if art == "abstand" else _achse_winkel(t0, t)
    return e


def _status(k):
    return {n: sw_baugruppe.status(x) for n, x in k.items()}


def _kiste_aus_transform(k, model):
    box = sw.teilebox_mm(model)
    t = sw_baugruppe.transform(k)
    ecken = [(x, y, z) for x in (box[0], box[3]) for y in (box[1], box[4]) for z in (box[2], box[5])]
    welt = [tuple(p[0] * t[i] + p[1] * t[3 + i] + p[2] * t[6 + i] + in_mm(t[9 + i]) for i in range(3)) for p in ecken]
    return [round(min(w[i] for w in welt), 4) for i in range(3)] + [round(max(w[i] for w in welt), 4) for i in range(3)]


def _schritte(app, asm, antrieb, k, n=20):
    pid = int(app.GetProcessID)
    vorher = _privat_mb(pid)
    zeiten = {"stellen": 0.0, "kollision": 0.0, "lage": 0.0}
    for i in range(n):
        t = time.perf_counter()
        antrieb.Parameter("D1").SetSystemValue3(mm((i % 5) * 20), 1, None)
        _rebuild(asm)
        zeiten["stellen"] += time.perf_counter() - t
        t = time.perf_counter()
        sw_baugruppe.interferenzen(asm)
        zeiten["kollision"] += time.perf_counter() - t
        t = time.perf_counter()
        for x in sw_baugruppe.komponenten(asm):
            sw_baugruppe.transform(x)
            x.GetBox(False, False)
        zeiten["lage"] += time.perf_counter() - t
    return {"schritte": n, "komponenten": len(k) if isinstance(k, dict) else k, "s_je_schritt":
            {n_: round(z / n, 4) for n_, z in zeiten.items()}, "privat_mb_vorher": vorher, "privat_mb_nachher": _privat_mb(pid)}


def _iso(app, asm, pfad):
    asm._FlagAsMethod("ViewZoomtofit2")
    with sw.einstellung_int(app, SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0):
        asm.ShowNamedView2("", ANSICHTEN["iso"])
        asm.ViewZoomtofit2()
        sw.speichere(asm, pfad, kopie=True)
    return pfad.stat().st_size


def _untersuche():
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    ordner = r.arbeitsordner / AUFTRAG
    shutil.rmtree(ordner, ignore_errors=True)
    ordner.mkdir(parents=True)
    ergebnis = {"privat_mb_start": _privat_mb(int(app.GetProcessID))}
    teile = _teile(app, r, standard, ordner)
    try:
        asm, k, e = _probe(app, r, teile)
        try:
            f1 = {"feature": "f1"}
            g1, ergebnis["1_grenze_abstand"] = _grenze(asm, "g1", "abstand", e("schieber", {**f1, "flaeche": "-x"}),
                                                       e("platte", {**f1, "flaeche": "-x"}), "gleich", 0, 100)
            g2, ergebnis["1_grenze_winkel"] = _grenze(asm, "g2", "winkel", e("hebel", {**f1, "flaeche": "+z"}),
                                                      e("schieber", {**f1, "flaeche": "+z"}), "gleich", 0, 90)
            ergebnis["2_bindung_abstand"] = _binde(asm, g1, ergebnis["1_grenze_abstand"].get("masse", []), mm(100),
                                                   "HUB", 100, 120)
            ergebnis["2_bindung_winkel"] = _binde(asm, g2, ergebnis["1_grenze_winkel"].get("masse", []), grad(90),
                                                  "SCHWENK", 90, 80)
            ergebnis["4_status_nur_grenzen"] = _status(k)
            a1 = sw_baugruppe.verknuepfe(asm, _v("g1.antrieb", "abstand", "gleich", 0), e("schieber", {**f1, "flaeche": "-x"}),
                                         e("platte", {**f1, "flaeche": "-x"}), {})
            ergebnis["4_status_antrieb_hub_auf_min"] = _status(k)
            t0 = sw_baugruppe.transform(k["schieber"])
            ergebnis["3_antrieb_hub"] = [_stelle(asm, a1, "abstand", w, k["schieber"], t0)
                                         for w in (25, 50, 100, 103.125, 100, 120, 100, 0)]
            a2 = sw_baugruppe.verknuepfe(asm, _v("g2.antrieb", "winkel", "gleich", 0), e("hebel", {**f1, "flaeche": "+z"}),
                                         e("schieber", {**f1, "flaeche": "+z"}), {})
            ergebnis["4_status_beide_antriebe"] = _status(k)
            th = sw_baugruppe.transform(k["hebel"])
            ergebnis["7_drehsinn"] = [_stelle(asm, a2, "winkel", w, k["hebel"], th) for w in (45, 90, 92.8125, 90, 0)]
            _stelle(asm, a2, "winkel", 90, k["hebel"], th)
            ergebnis["6_getbox_hebel"] = [round(in_mm(x), 4) for x in k["hebel"].GetBox(False, False)]
            ergebnis["6_teilebox_umgerechnet_hebel"] = _kiste_aus_transform(k["hebel"], teile["hebel"][0])
            (ordner / "bilder").mkdir(exist_ok=True)
            ergebnis["9_iso_bytes"] = _iso(app, asm, ordner / "bilder" / "s13_iso.png")
            _stelle(asm, a2, "winkel", 0, k["hebel"], th)
            ergebnis["8_probe"] = _schritte(app, asm, a1, k)
            _stelle(asm, a1, "abstand", 0, k["schieber"], t0)
            vor_loeschen = {n: sw_baugruppe.transform(x) for n, x in k.items()}
            for a in (a2, a1):
                sw_baugruppe._loesche(asm, a)
            ergebnis["5_rebuild_nach_loeschen"] = _rebuild(asm)
            ergebnis["5_lage_unveraendert"] = {
                n: max(abs(p - q) for p, q in zip(vor_loeschen[n], sw_baugruppe.transform(x))) for n, x in k.items()}
            ergebnis["5_status_nach_loeschen"] = _status(k)
            sw.speichere(asm, ordner / "S13_Probe.sldasm")
        finally:
            sw.schliesse(app, asm)
        vorher = _sha(ordner)
        asm = oeffne(app, ordner / "S13_Probe.sldasm")
        try:
            sw_baugruppe.aufloesen(asm)
            namen = {x.Name2: n for n, x in k.items()}
            k2 = {namen.get(x.Name2, x.Name2): x for x in sw_baugruppe.komponenten(asm)}

            def e2(name, seite):
                return sw_baugruppe.in_baugruppe(k2[name], loese_im_teil(teile[name][1], seite))

            a1 = sw_baugruppe.verknuepfe(asm, _v("g1.antrieb", "abstand", "gleich", 0),
                                         e2("schieber", {"feature": "f1", "flaeche": "-x"}),
                                         e2("platte", {"feature": "f1", "flaeche": "-x"}), {})
            t0 = sw_baugruppe.transform(k2["schieber"])
            ergebnis["5_nach_oeffnen_verstellen"] = _stelle(asm, a1, "abstand", 60, k2["schieber"], t0)
        finally:
            sw.schliesse(app, asm)
        ergebnis["5_sha_unveraendert"] = _sha(ordner) == vorher
        asm, k, e = _probe(app, r, teile)
        try:
            a1 = sw_baugruppe.verknuepfe(asm, _v("g1.antrieb", "abstand", "gleich", 0),
                                         e("schieber", {"feature": "f1", "flaeche": "-x"}),
                                         e("platte", {"feature": "f1", "flaeche": "-x"}), {})
            bolzen = Path(teile["bolzen"][0].GetPathName)
            box = sw.teilebox_mm(teile["bolzen"][0])
            mu = sw.mathutil(app)
            for i in range(96):
                x = sw_baugruppe.fuege_ein(app, asm, bolzen, box)
                lage = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0,
                        mm(-90 + (i % 12) * 16), mm(-60), mm(-60 - (i // 12) * 16), 1.0, 0.0, 0.0, 0.0]
                x.SetTransformAndSolve2(mu.CreateTransform(r8_array(lage)))
                sw_baugruppe.fixiere(asm, x)
            ergebnis["8_hundert_komponenten"] = _schritte(app, asm, a1, len(sw_baugruppe.komponenten(asm)))
        finally:
            sw.schliesse(app, asm)
    finally:
        for model, _ in reversed(list(teile.values())):
            sw.schliesse(app, model)
    ergebnis["privat_mb_ende"] = _privat_mb(int(app.GetProcessID))
    return ergebnis


if __name__ == "__main__":
    lauf("s13_bewegung", _untersuche)
```

- [ ] **Step 3: Spike laufen lassen**

Run (PowerShell): `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m spikes.s13_bewegung`
Expected: `"ok": true` und `docs/stufe0/ergebnisse/s13_bewegung.json`. Bricht der Spike ab: Fehler und Trace im JSON lesen, den Spike (nicht den Produktionscode) korrigieren, erneut laufen lassen; jede Korrektur im Bericht nennen. Danach Private Bytes notieren, eine Instanz, `False 1`, keine offenen Dokumente.

- [ ] **Step 4: Auswertung in den Bericht**

Für jede Zeile 1–9 der Tabelle „Abhängigkeiten vom Spike S13“: Annahme bestätigt / abweichend, mit den Werten aus dem JSON (z. B. Zeile 2: Name des Maßes der oberen Grenze und `MaximumVariation` nach der Änderung; Zeile 3: Weg je Stellung und die Meldungen bei 103,125 und 120; Zeile 4: Status je Komponente in den drei Zuständen; Zeile 7: Achse und Winkel bei 90; Zeile 8: s je Schritt und Private Bytes vorher/nachher). Keine Entscheidung treffen – die trifft der Controller.

- [ ] **Step 5: Commit**

```powershell
git add spikes/s13_bewegung.py docs/stufe0/ergebnisse/s13_bewegung.json
git commit -m "spike: S13 Grenzverknüpfungen, Antrieb, Bestimmtheit, Lage, Zeit und Speicher je Schritt" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Status DONE_WITH_CONCERNS, wenn eine Zeile abweicht (Controller entscheidet nach der Spalte „sonst“).

---

### Task 2: Format – Schema, Auflösen (Grenze, Scharnier), Prüfsumme, Soll in `swki aenderungen` (ohne SolidWorks)

**Files:**
- Modify: `schema/baugruppe.schema.json`
- Modify: `swki/baugruppe/aufloesen.py`
- Modify: `swki/spec/freigabe.py:21-43`
- Modify: `swki/aenderungen.py` (`soll_verknuepfungswerte`)
- Create: `tests/baugruppe/beispiel_bewegung.py`, `tests/baugruppe/test_bewegung_spec.py`

**Interfaces:**
- Consumes: `Verknuepfung`, `verknuepfungen()`, `_drehung_sperren()`, `_setze()` (`aufloesen.py`); `pruefsumme()`, `PRUEF_FELDER_BAUGRUPPE` (`swki/spec/freigabe.py`); `schema_befunde(spec, erwartet)` (`swki/spec/laden.py`); `lade_quellen(spec, ordner)` (`swki/baugruppe/laden.py`).
- Produces:
  - `Verknuepfung(id, vorlage, typ, a, b, ausrichtung, wert, drehung_sperren, min=None, max=None)` (zwei neue Felder mit Vorgabe – bestehende Aufrufe mit 8 Argumenten bleiben gültig).
  - `GRENZEN = ("grenze_abstand", "grenze_winkel")`, `ANLAGE = ".anlage"` in `aufloesen.py`.
  - `verknuepfungen(spec, quellen)`: `scharnier` → `[Verknuepfung(<id>, <id>, "konzentrisch", a, b, None, None, False), Verknuepfung(<id>.anlage, <id>, "deckungsgleich", anlage_a, anlage_b, ausrichtung or "entgegengesetzt", None, False)]`; Grenzen mit `min`/`max`.
  - `tests/baugruppe/beispiel_bewegung.py`: `GRUNDPLATTE`, `SCHIEBER`, `HEBEL`, `BAUGRUPPE`, `kopie()`, `schreibe(ordner, baugruppe=None, grundplatte=None, schieber=None, hebel=None) -> Path` (schreibt `grundplatte.yaml`, `schieber.yaml`, `hebel.yaml`, `bewegungsprobe.yaml`).
  - `pruefsumme(spec)` mit `bewegungen` nur, wenn vorhanden; `soll_verknuepfungswerte()` liefert für Grenzen den Wert von `min`.

- [ ] **Step 1: `tests/baugruppe/beispiel_bewegung.py` (neu)**

```python
"""Kleine gültige Baugruppe mit Bewegungen für Tests (Stufe 4a, selbst formuliert): Grundplatte (fixiert), Schieber auf
der Platte, bündig an deren Seite −z und über eine Abstandsgrenze in x verschiebbar, Drehbolzen ISO 8734 8 × 30 im
Schieber, Hebel auf dem Schieber über ein Scharnier um den Bolzen und eine Winkelgrenze schwenkbar.

Lage in Grundstellung (mm): Platte x −100…100, y 0…20, z −30…30; Schieber x −100…−40, y 20…40, z −30…10; Bolzen in
x = −60, z = −10, y 20…50; Hebel y 40…48, entlang +x von der Bohrung (x −67…−17). Hub 0…HUB, Schwenk 0…SCHWENK."""

import copy
from pathlib import Path

import yaml


def _block(name: str, laenge: float, breite: float, hoehe: float, weitere: list) -> dict:
    return {
        "art": "teil", "name": name, "material": "1.0038", "eigenschaften": {"Benennung": name},
        "parameter": {"L": laenge, "B": breite, "H": hoehe},
        "features": [
            {"id": "f1", "typ": "extrusion",
             "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
             "ende": {"typ": "blind", "tiefe": "=H"}},
            *weitere,
        ],
        "pruefung": {"huellquader": ["=L", "=H", "=B"]},
    }


GRUNDPLATTE = _block("Grundplatte", 200, 60, 20, [])
SCHIEBER = _block("Schieber", 60, 40, 20, [
    {"id": "f2", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[10, 0]], "durch": True},
])
HEBEL = _block("Hebel", 50, 12, 8, [
    {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[-18, 0]],
     "durchmesser": 8.5, "durch": True},
])
BAUGRUPPE = {
    "art": "baugruppe", "name": "Bewegungsprobe", "eigenschaften": {"Benennung": "Bewegungsprobe"},
    "parameter": {"HUB": 100, "SCHWENK": 90},
    "komponenten": [
        {"id": "platte", "quelle": {"teil": "grundplatte.yaml"}, "fixiert": True},
        {"id": "schieber", "quelle": {"teil": "schieber.yaml"}},
        {"id": "bolzen", "quelle": {"normteil": "ISO 8734 8x30"}},
        {"id": "hebel", "quelle": {"teil": "hebel.yaml"}},
    ],
    "verknuepfungen": [
        {"id": "v1", "typ": "deckungsgleich", "a": {"komponente": "schieber", "feature": "f1", "flaeche": "-y"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v2", "typ": "deckungsgleich", "a": {"komponente": "schieber", "feature": "f1", "flaeche": "-z"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "-z"}, "ausrichtung": "gleich"},
        {"id": "g1", "typ": "grenze_abstand", "a": {"komponente": "schieber", "feature": "f1", "flaeche": "-x"},
         "b": {"komponente": "platte", "feature": "f1", "flaeche": "-x"}, "ausrichtung": "gleich",
         "min": 0, "max": "=HUB"},
        {"id": "v3", "typ": "deckungsgleich", "a": {"komponente": "bolzen", "referenz": "EINBAU_EBENE_1"},
         "b": {"komponente": "schieber", "feature": "f1", "flaeche": "-y"}, "ausrichtung": "entgegengesetzt"},
        {"id": "v4", "typ": "konzentrisch", "a": {"komponente": "bolzen", "referenz": "EINBAU_ACHSE"},
         "b": {"komponente": "schieber", "feature": "f2", "instanz": 1, "achse": True}},
        {"id": "s1", "typ": "scharnier", "a": {"komponente": "hebel", "feature": "f2", "instanz": 1, "achse": True},
         "b": {"komponente": "bolzen", "referenz": "EINBAU_ACHSE"},
         "anlage_a": {"komponente": "hebel", "feature": "f1", "flaeche": "-y"},
         "anlage_b": {"komponente": "schieber", "feature": "f1", "flaeche": "+y"}},
        {"id": "g2", "typ": "grenze_winkel", "a": {"komponente": "hebel", "feature": "f1", "flaeche": "+z"},
         "b": {"komponente": "schieber", "feature": "f1", "flaeche": "+z"}, "ausrichtung": "gleich",
         "min": 0, "max": "=SCHWENK"},
    ],
    "freiheitsgrade": {"schieber": 1, "hebel": 1},
    "bewegungen": [
        {"name": "Hub", "grenze": "g1", "schritte": 4, "erwartet": {"endlagen": [
            {"komponente": "schieber", "verschiebung": ["=HUB", 0, 0]},
            {"komponente": "hebel", "verschiebung": ["=HUB", 0, 0]},
        ]}},
        {"name": "Schwenk", "grenze": "g2", "schritte": 4, "erwartet": {"endlagen": [
            {"komponente": "hebel", "drehung": {"achse": [0, 1, 0], "winkel": "=SCHWENK"}},
        ]}},
    ],
}


def kopie(spec: dict) -> dict:
    return copy.deepcopy(spec)


def schreibe(ordner: Path, baugruppe: dict | None = None, grundplatte: dict | None = None, schieber: dict | None = None,
             hebel: dict | None = None) -> Path:
    """Schreibt die drei Teil-Specs und bewegungsprobe.yaml nach ordner; liefert den Pfad der Baugruppen-Spec."""
    ordner.mkdir(parents=True, exist_ok=True)
    for name, spec in (("grundplatte.yaml", grundplatte or GRUNDPLATTE), ("schieber.yaml", schieber or SCHIEBER),
                       ("hebel.yaml", hebel or HEBEL), ("bewegungsprobe.yaml", baugruppe or BAUGRUPPE)):
        (ordner / name).write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ordner / "bewegungsprobe.yaml"
```

- [ ] **Step 2: Failing tests – `tests/baugruppe/test_bewegung_spec.py` (neu)**

```python
"""Stufe 4a: Format der Bewegungen – Schema, Auflösen von Grenze und Scharnier, Prüfsumme, Soll der Grenzverknüpfung."""

import json

import pytest

from swki.aenderungen import soll_verknuepfungswerte
from swki.baugruppe.aufloesen import verknuepfungen
from swki.baugruppe.laden import lade_quellen
from swki.spec.freigabe import PRUEF_FELDER_BAUGRUPPE, _sha256, pruefsumme
from swki.spec.laden import schema_befunde
from tests.baugruppe.beispiel import BAUGRUPPE as STATISCH
from tests.baugruppe.beispiel_bewegung import BAUGRUPPE, kopie, schreibe


def _quellen(tmp_path, spec):
    pfad = schreibe(tmp_path / "A", baugruppe=spec)
    quellen, _, befunde = lade_quellen(spec, pfad.parent)
    assert befunde == []
    return quellen


def test_schema_bewegungsprobe_gueltig():
    assert schema_befunde(kopie(BAUGRUPPE), "baugruppe") == []


@pytest.mark.parametrize("aendern", [
    lambda s: s["freiheitsgrade"].update(schieber=0),
    lambda s: s["freiheitsgrade"].update(schieber="frei"),
    lambda s: s["bewegungen"][0].update(schritte=1),
    lambda s: s["bewegungen"][0].update(von=0),
    lambda s: s["bewegungen"][0]["erwartet"]["endlagen"][0].update(drehung={"achse": [0, 1, 0], "winkel": 90}),
    lambda s: s["verknuepfungen"][2].update(typ="grenze"),
])
def test_schema_lehnt_ab(aendern):
    spec = kopie(BAUGRUPPE)
    aendern(spec)
    assert schema_befunde(spec, "baugruppe")


def test_scharnier_wird_zu_achse_und_anlage(tmp_path):
    spec = kopie(BAUGRUPPE)
    vs = verknuepfungen(spec, _quellen(tmp_path, spec))
    assert [v.id for v in vs] == ["v1", "v2", "g1", "v3", "v4", "s1", "s1.anlage", "g2"]
    v = {x.id: x for x in vs}
    assert (v["s1"].typ, v["s1"].drehung_sperren, v["s1"].ausrichtung, v["s1"].b) == (
        "konzentrisch", False, None, {"komponente": "bolzen", "referenz": "EINBAU_ACHSE"})
    assert (v["s1.anlage"].typ, v["s1.anlage"].ausrichtung, v["s1.anlage"].vorlage) == (
        "deckungsgleich", "entgegengesetzt", "s1")
    assert v["s1.anlage"].a == {"komponente": "hebel", "feature": "f1", "flaeche": "-y"}
    assert (v["g1"].typ, v["g1"].min, v["g1"].max, v["g1"].wert, v["g1"].drehung_sperren) == (
        "grenze_abstand", 0, "=HUB", None, False)
    assert v["v4"].drehung_sperren is True  # konzentrisch mit Normteil wie bisher


def test_scharnier_ausrichtung_der_anlage_aus_der_spec(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][5]["ausrichtung"] = "gleich"
    v = {x.id: x for x in verknuepfungen(spec, _quellen(tmp_path, spec))}
    assert v["s1.anlage"].ausrichtung == "gleich" and v["s1"].ausrichtung is None


def test_pruefsumme_ohne_bewegungen_unveraendert():
    spec = kopie(STATISCH)
    kern = {f: spec.get(f) for f in PRUEF_FELDER_BAUGRUPPE}
    assert pruefsumme(spec) == _sha256(json.dumps(kern, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def test_pruefsumme_schuetzt_bewegungen():
    spec = kopie(BAUGRUPPE)
    vorher = pruefsumme(spec)
    spec["bewegungen"][0]["schritte"] = 8
    assert pruefsumme(spec) != vorher
    ohne = kopie(BAUGRUPPE)
    ohne.pop("bewegungen")
    assert pruefsumme(ohne) != vorher


def test_soll_der_grenze_ist_der_wert_in_grundstellung(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["verknuepfungen"][2]["min"] = "=HUB/4"
    assert soll_verknuepfungswerte(spec, _quellen(tmp_path, spec)) == {"g1": 25.0, "g2": 0.0}
```

- [ ] **Step 3: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bewegung_spec.py -q`
Expected: FAIL – das Schema kennt `grenze_abstand`, `scharnier` und `bewegungen` nicht, `Verknuepfung` hat kein `min`, das Scharnier wird nicht aufgelöst, die Prüfsumme ändert sich mit `bewegungen` nicht. Schon grün sein können `test_pruefsumme_ohne_bewegungen_unveraendert` und Fälle von `test_schema_lehnt_ab`, die das Schema schon heute ablehnt.

- [ ] **Step 4: `schema/baugruppe.schema.json` erweitern**

1. In `properties` die Zeile(n) von `freiheitsgrade` ersetzen und `bewegungen` ergänzen:

```json
    "freiheitsgrade": {"type": "object", "propertyNames": {"$ref": "#/$defs/instanz_id"},
                       "additionalProperties": {"oneOf": [{"const": "unterbestimmt"},
                                                           {"type": "integer", "minimum": 1}]}},
    "bewegungen": {"type": "array", "items": {"$ref": "#/$defs/bewegung"}},
```

2. In `$defs.verknuepfung.properties` den `typ` ersetzen und vier Eigenschaften ergänzen:

```json
        "typ": {"enum": ["deckungsgleich", "konzentrisch", "parallel", "senkrecht", "abstand", "winkel",
                         "grenze_abstand", "grenze_winkel", "scharnier"]},
        "min": {"$ref": "#/$defs/wert"},
        "max": {"$ref": "#/$defs/wert"},
        "anlage_a": {"$ref": "#/$defs/referenz"},
        "anlage_b": {"$ref": "#/$defs/referenz"},
```

3. In `$defs` nach `pruefung` ergänzen (Komma nach dessen schließender Klammer; die Datei muss gültiges JSON bleiben):

```json
    "endlage": {"oneOf": [
      {"type": "object", "required": ["komponente", "verschiebung"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/instanz_id"}, "verschiebung": {"$ref": "#/$defs/punkt3"}}},
      {"type": "object", "required": ["komponente", "drehung"], "additionalProperties": false,
       "properties": {"komponente": {"$ref": "#/$defs/instanz_id"},
                      "drehung": {"type": "object", "required": ["achse", "winkel"], "additionalProperties": false,
                                  "properties": {"achse": {"$ref": "#/$defs/punkt3"}, "winkel": {"$ref": "#/$defs/wert"}}}}}
    ]},
    "bewegung": {
      "type": "object", "required": ["name", "grenze"], "additionalProperties": false,
      "properties": {
        "name": {"$ref": "#/$defs/id"},
        "grenze": {"$ref": "#/$defs/id"},
        "schritte": {"type": "integer", "minimum": 2},
        "erwartet": {"type": "object", "additionalProperties": false,
                     "properties": {"endlagen": {"type": "array", "items": {"$ref": "#/$defs/endlage"}}}}
      }
    }
```

- [ ] **Step 5: `swki/baugruppe/aufloesen.py`**

Die Dataclass `Verknuepfung` nach `drehung_sperren` um zwei Felder mit Vorgabe ergänzen:

```python
    min: object = None      # grenze_abstand/grenze_winkel: Zahl oder "=Ausdruck" (mm bzw. Grad)
    max: object = None
```

Nach `basis()` die Konstanten ergänzen:

```python
GRENZEN = ("grenze_abstand", "grenze_winkel")
ANLAGE = ".anlage"  # Endung der zweiten SolidWorks-Verknüpfung eines Scharniers (Präzisierung 1)
```

`verknuepfungen()` ersetzen durch:

```python
def _einzeln(v: dict, vid: str, a: dict, b: dict, quellen: dict[str, Quelle], anlage_a: dict | None,
             anlage_b: dict | None) -> list[Verknuepfung]:
    """Eine Verknüpfung der Spezifikation als SolidWorks-Verknüpfungen. Ein Scharnier wird zu konzentrisch (ohne
    Drehsperre, die Drehung bleibt frei) und deckungsgleich der Anlageflächen (Präzisierung 1)."""
    if v["typ"] == "scharnier":
        return [Verknuepfung(vid, v["id"], "konzentrisch", a, b, None, None, False),
                Verknuepfung(f"{vid}{ANLAGE}", v["id"], "deckungsgleich", anlage_a, anlage_b,
                             v.get("ausrichtung", "entgegengesetzt"), None, False)]
    return [Verknuepfung(vid, v["id"], v["typ"], a, b, v.get("ausrichtung"), v.get("wert"), _drehung_sperren(v, quellen),
                         v.get("min"), v.get("max"))]


def verknuepfungen(spec: dict, quellen: dict[str, Quelle]) -> list[Verknuepfung]:
    """Aufgelöste Verknüpfungen in Spec-Reihenfolge; je_position vervielfältigt (Grenzen und Scharniere nennen keine
    Komponente mit je_position, das prüft swki.baugruppe.plausibel)."""
    ergebnis = []
    for v in spec.get("verknuepfungen", []):
        je = {v[s]["komponente"] for s in ("a", "b") if je_position(spec, v[s]["komponente"])}
        if not je:
            ergebnis += _einzeln(v, v["id"], dict(v["a"]), dict(v["b"]), quellen,
                                 dict(v["anlage_a"]) if "anlage_a" in v else None,
                                 dict(v["anlage_b"]) if "anlage_b" in v else None)
            continue
        for i in range(1, anzahl_positionen(spec, quellen, next(iter(je))) + 1):
            ergebnis += _einzeln(v, f"{v['id']}.{i}", _setze(v["a"], je, i), _setze(v["b"], je, i), quellen, None, None)
    return ergebnis
```

- [ ] **Step 6: `swki/spec/freigabe.py` – Prüfsumme**

Nach `PRUEF_FELDER_BAUGRUPPE` ergänzen:

```python
OPTIONAL_BAUGRUPPE = ("bewegungen",)  # nur in der Prüfsumme, wenn vorhanden: Freigaben ohne Bewegungen bleiben gültig
```

In `pruefsumme()` nach `kern = {feld: spec.get(feld) for feld in felder}` einfügen:

```python
    if spec.get("art") == "baugruppe":
        kern |= {feld: spec[feld] for feld in OPTIONAL_BAUGRUPPE if feld in spec}
```

- [ ] **Step 7: `swki/aenderungen.py` – `soll_verknuepfungswerte`**

Die Funktion ersetzen:

```python
def soll_verknuepfungswerte(spec: dict, quellen: dict, parameter: dict | None = None) -> dict[str, float]:
    """Abstands- und Winkelwerte der aufgelösten Verknüpfungen (mm bzw. Grad) nach Verknüpfungs-ID; die Ausdrücke
    werden mit parameter ausgewertet (Vorgabe: die Parameter von spec). Eine Grenzverknüpfung steht mit ihrem Wert in
    Grundstellung (min), so speichert swki bauen sie (Spec 4a §7)."""
    from swki.baugruppe.aufloesen import verknuepfungen  # spät importiert (Kreisimport)

    p = spec.get("parameter", {}) if parameter is None else parameter
    return {v.id: auswerten(v.wert if v.wert is not None else v.min, p) for v in verknuepfungen(spec, quellen)
            if v.wert is not None or v.min is not None}
```

- [ ] **Step 8: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bewegung_spec.py -q` → 11 passed.
Run: `.venv\Scripts\python.exe -m pytest -q` → **633 passed, 109 deselected** (622 + 11).

- [ ] **Step 9: Commit**

```powershell
git add schema/baugruppe.schema.json swki/baugruppe/aufloesen.py swki/spec/freigabe.py swki/aenderungen.py tests/baugruppe/beispiel_bewegung.py tests/baugruppe/test_bewegung_spec.py
git commit -m "baugruppe: Format für Bewegungen (Grenzen, Scharnier, freiheitsgrade 1, bewegungen) und Prüfsumme" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Plausibilität, Passung, Hinweis, Vorgaben (ohne SolidWorks)

**Files:**
- Modify: `swki/baugruppe/plausibel.py`
- Modify: `swki/baugruppe/passung.py`
- Modify: `swki/baugruppe/hinweise.py`
- Modify: `config/standard.yaml`
- Create: `tests/baugruppe/test_bewegung_plausibel.py`

**Interfaces:**
- Consumes: `GRENZEN` (Task 2), `referenz_befunde()`, `_instanz_befunde()`, `_b()` (`plausibel.py`), `passt()` (`passung.py`), `lade_standard()`.
- Produces: Befunde aus Spec 4a §5 und Präzisierung 3; `bewegte_komponente(spec, bewegung) -> str | None` (`plausibel.py`); `passt_drehbolzen(q, f, parameter) -> str | None`; Hinweis `{"art": "pruefaufwand", "pfad": "bewegungen", "meldung": …}` ab 4 Bewegungen; `config/standard.yaml` mit `bewegung_schritte: 16`, `speicher_grenze_mb: 3500`.

- [ ] **Step 1: Failing tests – `tests/baugruppe/test_bewegung_plausibel.py` (neu)**

```python
"""Stufe 4a: Plausibilität der Bewegungen (Spec 4a §5, Präzisierung 3), Passung des Drehbolzens, Hinweis
pruefaufwand, Vorgaben in config/standard.yaml."""

from types import SimpleNamespace

import pytest

from swki.baugruppe.hinweise import hinweise_baugruppe
from swki.baugruppe.laden import lade_quellen
from swki.baugruppe.plausibel import plausibel_befunde
from swki.konfig import lade_standard
from tests.baugruppe.beispiel_bewegung import BAUGRUPPE, HEBEL, kopie, schreibe


def _befunde(tmp_path, spec, **teile) -> str:
    pfad = schreibe(tmp_path / "A", baugruppe=spec, **teile)
    quellen, _, befunde = lade_quellen(spec, pfad.parent)
    assert befunde == []
    return " | ".join(f"{b['pfad']}: {b['meldung']}" for b in plausibel_befunde(spec, quellen))


def _v(spec: dict, vid: str) -> dict:
    return next(v for v in spec["verknuepfungen"] if v["id"] == vid)


def test_bewegungsprobe_ohne_befunde(tmp_path):
    assert _befunde(tmp_path, kopie(BAUGRUPPE)) == ""


@pytest.mark.parametrize(("aendern", "erwartet"), [
    (lambda s: _v(s, "g1").update(max=100), "GRENZE_FESTE_ZAHL"),
    (lambda s: _v(s, "g1").pop("max"), "max ist bei grenze_abstand Pflicht"),
    (lambda s: _v(s, "g1").update(min="=HUB", max="=HUB/2"), "muss kleiner als max"),
    (lambda s: _v(s, "g2").update(max="=SCHWENK*5"), "[0, 360]"),
    (lambda s: _v(s, "g1").pop("ausrichtung"), "ausrichtung (gleich | entgegengesetzt) ist bei grenze_abstand Pflicht"),
    (lambda s: _v(s, "v1").update(min=0), "min/max gelten nur bei grenze_abstand/grenze_winkel"),
    (lambda s: _v(s, "s1").pop("anlage_b"), "anlage_b ist bei scharnier Pflicht"),
    (lambda s: _v(s, "s1")["anlage_a"].update(komponente="schieber"), "anlage_a gehört zur Komponente von a"),
    (lambda s: _v(s, "s1").update(a={"komponente": "hebel", "feature": "f1", "flaeche": "+y"}), "a und b sind Achsen"),
    (lambda s: _v(s, "v1").update(anlage_a={"komponente": "schieber", "feature": "f1", "flaeche": "+y"}),
     "anlage_a/anlage_b gelten nur bei scharnier"),
    (lambda s: s["freiheitsgrade"].update(hebel=2), "FREIHEITSGRADE_NICHT_UNTERSTUETZT"),
    (lambda s: s["bewegungen"].pop(1), "BEWEGUNG_FEHLT"),
    (lambda s: s["bewegungen"].append({"name": "Hub2", "grenze": "g1"}), "Grenze g1 treibt schon Hub"),
    (lambda s: s["bewegungen"][1].update(grenze="v1"), "'v1' ist keine grenze_abstand/grenze_winkel"),
    (lambda s: s["freiheitsgrade"].pop("schieber"), "Bewegung Hub: schieber braucht freiheitsgrade: 1"),
    (lambda s: s["bewegungen"][0].update(name="Schwenk"), "Name 'Schwenk' ist doppelt"),
    (lambda s: s["bewegungen"][1]["erwartet"]["endlagen"][0]["drehung"].update(achse=[0, 0, 0]), "Nullvektor"),
    (lambda s: s["bewegungen"][0]["erwartet"]["endlagen"][0].update(komponente="wagen"), "Komponente 'wagen' unbekannt"),
])
def test_befunde(tmp_path, aendern, erwartet):
    spec = kopie(BAUGRUPPE)
    aendern(spec)
    assert erwartet in _befunde(tmp_path, spec)


def test_grenze_nicht_mit_je_position(tmp_path):
    spec = kopie(BAUGRUPPE)
    spec["komponenten"].append({"id": "stifte", "quelle": {"normteil": "ISO 8734 8x30"},
                                "je_position": {"komponente": "schieber", "feature": "f2"}})
    _v(spec, "g1")["a"] = {"komponente": "stifte", "referenz": "EINBAU_EBENE_1"}
    assert "nicht mit Komponenten mit je_position" in _befunde(tmp_path, spec)


def test_drehbolzen_braucht_groessere_bohrung(tmp_path):
    hebel = kopie(HEBEL)
    hebel["features"][1]["durchmesser"] = 8
    assert "als Drehbolzen: Bohrung Ø 8 nicht größer als 8" in _befunde(tmp_path, kopie(BAUGRUPPE), hebel=hebel)


def test_drehbolzen_nicht_in_normbohrung(tmp_path):
    hebel = kopie(HEBEL)
    hebel["features"][1] = {"id": "f2", "typ": "normbohrung", "art": "stift", "groesse": 8,
                            "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[-18, 0]], "durch": True}
    assert "braucht eine bohrung" in _befunde(tmp_path, kopie(BAUGRUPPE), hebel=hebel)


def _bg(n: int) -> SimpleNamespace:
    return SimpleNamespace(teile={}, spec={"verknuepfungen": [],
                                           "bewegungen": [{"name": f"B{i}", "grenze": f"g{i}", "schritte": 4}
                                                          for i in range(n)]})


def test_hinweis_pruefaufwand_ab_vier_bewegungen():
    [h] = [x for x in hinweise_baugruppe(_bg(4)) if x["art"] == "pruefaufwand"]
    assert h["pfad"] == "bewegungen"
    assert h["meldung"].startswith("4 Bewegungen: 20 Stellungen in Grundstellung") and "80 mit Paarläufen" in h["meldung"]


def test_kein_hinweis_bei_drei_bewegungen():
    assert [x for x in hinweise_baugruppe(_bg(3)) if x["art"] == "pruefaufwand"] == []


def test_vorgaben_in_standard():
    standard = lade_standard()
    assert (standard["bewegung_schritte"], standard["speicher_grenze_mb"]) == (16, 3500)
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bewegung_plausibel.py -q`
Expected: FAIL – `test_bewegungsprobe_ohne_befunde` meldet Passung („ISO 8734 8 gehört nicht in eine freie Bohrung“ entfällt erst mit `passt_drehbolzen` – heute prüft die Passung nur `konzentrisch`, daher kann der Test schon grün sein), die neuen Meldungen der Parametrisierung fehlen, `KeyError: 'bewegung_schritte'`.

- [ ] **Step 3: `config/standard.yaml` – am Ende ergänzen**

```yaml
# Bewegungen (Stufe 4a): Schritte je Bewegung (Vorgabe) und Speichergrenze von SolidWorks (Private Bytes) für swki pruefen
bewegung_schritte: 16
speicher_grenze_mb: 3500
```

- [ ] **Step 4: `swki/baugruppe/passung.py`**

Nach `passt()` einfügen:

```python
def passt_drehbolzen(q: Quelle, f: dict, parameter: dict) -> str | None:
    """Scharnier (Spec 4a §4.2): ISO 8734 als Drehbolzen braucht auf der drehenden Seite eine bohrung mit Ø > d; andere
    Normteile wie bei konzentrisch."""
    if q.norm != "ISO 8734":
        return passt(q, f, parameter)
    d_bolzen = q.masse["d"]
    if f["typ"] != "bohrung":
        return f"ISO 8734 {q.groesse} als Drehbolzen braucht eine bohrung mit Ø > {d_bolzen:g} (keine normbohrung)"
    try:
        d = auswerten(f["durchmesser"], parameter)
    except AusdruckFehler:
        return None  # meldet die Prüfung der Teil-Spec
    return None if d > d_bolzen else f"ISO 8734 {q.groesse} als Drehbolzen: Bohrung Ø {d:g} nicht größer als {d_bolzen:g}"
```

In `passung_befunde()` die Schleife ersetzen:

```python
    for i, v in enumerate(spec.get("verknuepfungen", [])):
        if v["typ"] not in ("konzentrisch", "scharnier") or (paar := _paar(v, quellen)) is None:
            continue
        qn, qt, seite = paar
        f = next((x for x in qt.spec["features"] if x["id"] == seite["feature"]), None)
        if f is None or f["typ"] not in ("normbohrung", "bohrung"):
            continue
        pruefe = passt_drehbolzen if v["typ"] == "scharnier" else passt
        if meldung := pruefe(qn, f, qt.spec.get("parameter", {})):
            befunde.append({"pfad": f"verknuepfungen[{i}]", "meldung": f"Passung: {meldung}"})
```

- [ ] **Step 5: `swki/baugruppe/plausibel.py`**

Importe ersetzen:

```python
from swki.baugruppe.aufloesen import GRENZEN, anzahl_positionen, basis, je_position
from swki.baugruppe.modell import Quelle
from swki.baugruppe.passung import passung_befunde
from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck
```

`MIT_AUSRICHTUNG` ersetzen:

```python
MIT_AUSRICHTUNG = ("deckungsgleich", "parallel", "abstand", "winkel", *GRENZEN)
```

Vor `_verknuepfung_befunde()` einfügen:

```python
def _grenze_befunde(v: dict, pfad: str, p: dict) -> list[dict]:
    """min/max einer Grenzverknüpfung: Pflicht, 0 oder Parameter-Ausdruck (GRENZE_FESTE_ZAHL), min < max, Bereich."""
    if v["typ"] not in GRENZEN:
        return [_b(f"{pfad}.{s}", "min/max gelten nur bei grenze_abstand/grenze_winkel") for s in ("min", "max") if s in v]
    befunde, werte = [], {}
    for s in ("min", "max"):
        if s not in v:
            befunde.append(_b(f"{pfad}.{s}", f"{s} ist bei {v['typ']} Pflicht"))
            continue
        w = v[s]
        if not ist_ausdruck(w) and w != 0:
            befunde.append(_b(f"{pfad}.{s}", f"GRENZE_FESTE_ZAHL: {s} = {w:g} als Parameter-Ausdruck führen (\"=NAME\"); "
                                             "nur so schützt die Freigabe den Bewegungsbereich"))
            continue
        try:
            werte[s] = auswerten(w, p)
        except AusdruckFehler as e:
            befunde.append(_b(f"{pfad}.{s}", str(e)))
    if len(werte) == 2:
        unten, oben = werte["min"], werte["max"]
        if not unten < oben:
            befunde.append(_b(pfad, f"min ({unten:g}) muss kleiner als max ({oben:g}) sein"))
        elif v["typ"] == "grenze_abstand" and unten < 0:
            befunde.append(_b(f"{pfad}.min", f"grenze_abstand: min muss ≥ 0 sein (ist {unten:g})"))
        elif v["typ"] == "grenze_winkel" and not (0 <= unten and oben <= 360):
            befunde.append(_b(pfad, f"grenze_winkel: min und max müssen in [0, 360] liegen (sind {unten:g}, {oben:g})"))
    return befunde


def _scharnier_befunde(v: dict, pfad: str, spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Scharnier: a und b Achsen, anlage_a/anlage_b ebene Flächen derselben Komponenten (Spec 4a §4.2)."""
    if v["typ"] != "scharnier":
        return [_b(f"{pfad}.{s}", "anlage_a/anlage_b gelten nur bei scharnier") for s in ("anlage_a", "anlage_b") if s in v]
    befunde = []
    for s in ("a", "b"):
        if not (v[s].get("achse") or "referenz" in v[s]):
            befunde.append(_b(f"{pfad}.{s}", "scharnier: a und b sind Achsen (achse: true oder Achsreferenz wie EINBAU_ACHSE)"))
    for s, gegen in (("anlage_a", "a"), ("anlage_b", "b")):
        if s not in v:
            befunde.append(_b(f"{pfad}.{s}", f"{s} ist bei scharnier Pflicht (ebene Anlagefläche)"))
            continue
        befunde += referenz_befunde(v[s], f"{pfad}.{s}", quellen, spec)
        if v[s].get("achse"):
            befunde.append(_b(f"{pfad}.{s}", f"{s} ist eine ebene Fläche, keine Achse"))
        if v[s]["komponente"] != v[gegen]["komponente"]:
            befunde.append(_b(f"{pfad}.{s}.komponente",
                              f"{s} gehört zur Komponente von {gegen} ({v[gegen]['komponente']})"))
    return befunde
```

In `_verknuepfung_befunde()` direkt nach `befunde += _je_befunde(v, pfad, spec)` einfügen:

```python
        befunde += _grenze_befunde(v, pfad, p) + _scharnier_befunde(v, pfad, spec, quellen)
        if v["typ"] in (*GRENZEN, "scharnier") and any(je_position(spec, v[s]["komponente"]) for s in ("a", "b")):
            befunde.append(_b(pfad, f"{v['typ']} nicht mit Komponenten mit je_position"))
```

`_freiheitsgrade_befunde()` ersetzen:

```python
def _freiheitsgrade_befunde(spec: dict) -> list[dict]:
    bekannt = {k["id"] for k in spec["komponenten"]} | {k["gruppe"] for k in spec["komponenten"] if k.get("gruppe")}
    befunde = [_b(f"freiheitsgrade.{n}", f"{n!r} ist weder Komponente noch Gruppe")
               for n in spec.get("freiheitsgrade", {}) if n.split(".")[0] not in bekannt]
    return befunde + [_b(f"freiheitsgrade.{n}", f"FREIHEITSGRADE_NICHT_UNTERSTUETZT: {w} Freiheitsgrade – in Stufe 4a "
                                                 "höchstens 1 je Komponente oder Gruppe")
                      for n, w in spec.get("freiheitsgrade", {}).items() if isinstance(w, int) and w > 1]
```

Nach `_freiheitsgrade_befunde()` einfügen:

```python
def bewegte_komponente(spec: dict, bewegung: dict) -> str | None:
    """Seite a der Grenzverknüpfung einer Bewegung, None wenn grenze keine Grenzverknüpfung ist."""
    v = next((x for x in spec.get("verknuepfungen", []) if x["id"] == bewegung["grenze"]), None)
    return v["a"]["komponente"] if v is not None and v["typ"] in GRENZEN else None


def _gruppe(spec: dict, kid: str) -> str | None:
    return next((k.get("gruppe") for k in spec["komponenten"] if k["id"] == kid), None)


def _endlage_befunde(e: dict, pfad: str, spec: dict, quellen: dict[str, Quelle], p: dict) -> list[dict]:
    kid = e["komponente"]
    if basis(kid) not in quellen:
        return [_b(f"{pfad}.komponente", f"Komponente {kid!r} unbekannt")]
    befunde = _instanz_befunde(kid, basis(kid), pfad, spec, quellen)
    werte = e["verschiebung"] if "verschiebung" in e else [*e["drehung"]["achse"], e["drehung"]["winkel"]]
    try:
        zahlen = [auswerten(w, p) for w in werte]
    except AusdruckFehler as ex:
        return befunde + [_b(pfad, str(ex))]
    if "drehung" in e and not any(zahlen[:3]):
        befunde.append(_b(f"{pfad}.drehung.achse", "Drehachse darf nicht der Nullvektor sein"))
    return befunde


def _bewegungen_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Spec 4a §4.3/§4.4 und Präzisierung 3."""
    befunde = []
    bws = spec.get("bewegungen", [])
    namen = [b["name"] for b in bws]
    fg = spec.get("freiheitsgrade", {})
    fix = {k["id"] for k in spec["komponenten"] if k.get("fixiert")}
    p = spec.get("parameter", {})
    genutzt: dict[str, str] = {}
    for i, b in enumerate(bws):
        pfad = f"bewegungen[{i}]"
        if b["name"] in namen[:i]:
            befunde.append(_b(f"{pfad}.name", f"Name {b['name']!r} ist doppelt"))
        kid = bewegte_komponente(spec, b)
        if kid is None:
            befunde.append(_b(f"{pfad}.grenze", f"{b['grenze']!r} ist keine grenze_abstand/grenze_winkel"))
            continue
        if b["grenze"] in genutzt:
            befunde.append(_b(f"{pfad}.grenze", f"Grenze {b['grenze']} treibt schon {genutzt[b['grenze']]}"))
        genutzt.setdefault(b["grenze"], b["name"])
        if kid in fix:
            befunde.append(_b(f"{pfad}.grenze", f"{kid} ist fixiert und kann sich nicht bewegen"))
        if fg.get(kid) != 1 and fg.get(_gruppe(spec, kid)) != 1:
            befunde.append(_b(f"{pfad}.grenze", f"Bewegung {b['name']}: {kid} braucht freiheitsgrade: 1 "
                                                "(Komponente oder Gruppe)"))
        for j, e in enumerate(b.get("erwartet", {}).get("endlagen", [])):
            befunde += _endlage_befunde(e, f"{pfad}.erwartet.endlagen[{j}]", spec, quellen, p)
    for n, w in fg.items():
        if w != 1:
            continue
        mitglieder = {n} | {k["id"] for k in spec["komponenten"] if k.get("gruppe") == n}
        anzahl = sum(1 for b in bws if bewegte_komponente(spec, b) in mitglieder)
        if anzahl == 0:
            befunde.append(_b(f"freiheitsgrade.{n}", f"BEWEGUNG_FEHLT: {n} hat freiheitsgrade: 1, aber keine Bewegung "
                                                     "treibt es"))
        elif anzahl > 1:
            befunde.append(_b(f"freiheitsgrade.{n}", f"BEWEGUNG_DOPPELT: {anzahl} Bewegungen treiben {n}"))
    return befunde
```

In `plausibel_befunde()` die Zeile `befunde = _verknuepfung_befunde(spec, quellen) + _freiheitsgrade_befunde(spec) + _pruefung_befunde(spec, quellen)` ersetzen:

```python
    befunde = (_verknuepfung_befunde(spec, quellen) + _freiheitsgrade_befunde(spec) + _pruefung_befunde(spec, quellen)
               + _bewegungen_befunde(spec, quellen))
```

- [ ] **Step 6: `swki/baugruppe/hinweise.py`**

Import ergänzen: `from swki.konfig import lade_standard`. Nach den Importen: `PRUEFAUFWAND_AB = 4  # Bewegungen; Spec 4a §4.4`. Vor `return ergebnis` einfügen:

```python
    bws = bg.spec.get("bewegungen", [])
    if len(bws) >= PRUEFAUFWAND_AB:
        vorgabe = lade_standard()["bewegung_schritte"]
        stellungen = sum(b.get("schritte", vorgabe) + 1 for b in bws)
        ergebnis.append({"art": "pruefaufwand", "pfad": "bewegungen",
                         "meldung": f"{len(bws)} Bewegungen: {stellungen} Stellungen in Grundstellung, im ungünstigsten "
                                    f"Fall {len(bws) * stellungen} mit Paarläufen – Zeit und SolidWorks-Speicher beachten"})
```

(Jeder Paarlauf fährt beide Bewegungen eines Paares einmal; bei n Bewegungen und allen Paaren kommen (n − 1) · Σ(schritte + 1) Stellungen dazu, zusammen n · Σ(schritte + 1).)

- [ ] **Step 7: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bewegung_plausibel.py -q` → 24 passed.
Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe -q` → alle grün (Stehlager- und Probe-Specs ohne neue Befunde).
Run: `.venv\Scripts\python.exe -m pytest -q` → **657 passed, 109 deselected** (633 + 24).

- [ ] **Step 8: Commit**

```powershell
git add swki/baugruppe/plausibel.py swki/baugruppe/passung.py swki/baugruppe/hinweise.py config/standard.yaml tests/baugruppe/test_bewegung_plausibel.py
git commit -m "baugruppe: Plausibilität für Grenzen, Scharnier und Bewegungen, Passung Drehbolzen, Hinweis Prüfaufwand" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Bewegungslogik ohne SolidWorks (`swki/baugruppe/bewegung.py`)

**Files:**
- Create: `swki/baugruppe/bewegung.py`
- Create: `tests/baugruppe/test_bewegung.py`

**Interfaces:**
- Consumes: `STATUS_TEXT`, `UNTERBESTIMMT`, `VOLL_BESTIMMT` (`swki/baugruppe/bewertung.py`); `_pruefung`, `_beschreibung` (`swki/pruefung/bewertung.py`); `auswerten`; `in_mm`; `standard["bewegung_schritte"]` (Task 3).
- Produces (von Task 5–7 verwendet):
  - `Bewegung(name, grenze, art, komponente, min, max, schritte)` (frozen; `art` = `"abstand"` | `"winkel"`), `.schrittweite`, `.stellungen() -> list[float]`.
  - `bewegungen(spec, standard) -> list[Bewegung]`.
  - `verschiebung_mm(t0, t1)`, `relative_drehung(t0, t1)`, `winkel_grad(q)`, `achse_winkel(q)`, `drehmatrix(achse, winkel)`, `ist_bewegt(t0, t1)`, `weg(b, t0, t1)`, `soll_weg(b, wert)`.
  - `vereinige(a, b)`, `schnitt(a, b)`, `paare(bws, grund) -> list[tuple[Bewegung, Bewegung, list[float]]]`.
  - `Lauf` (Dataclass: `bewegung`, `gegen`, `stellungen`, `lagen`, `bewegt`, `raum`, `kollisionen`, `fehler`, `grenze`, `bilder`, `dauer_s`), `BewegungsMesswerte(status_gehalten, laeufe, paare)`.
  - `bewerte_bewegungen(spec, bws, m, statisch, tol_mm) -> tuple[list[dict], dict]`; `ergaenze_bericht(bericht, pruefungen, bewegungsbericht, bilder) -> dict`; `TOL_WINKEL_GRAD`.

- [ ] **Step 1: Failing tests – `tests/baugruppe/test_bewegung.py` (neu)**

```python
"""Stufe 4a: Bewegungslogik ohne SolidWorks – Bewegungen aus der Spec, Lagevergleich, Räume, Paare, Bewertung."""

import math

import pytest

from swki.baugruppe.bewegung import (Bewegung, BewegungsMesswerte, Lauf, achse_winkel, bewegungen, bewerte_bewegungen,
                                     drehmatrix, ergaenze_bericht, ist_bewegt, paare, relative_drehung, schnitt,
                                     soll_weg, vereinige, verschiebung_mm, weg, winkel_grad)
from swki.konfig import lade_standard
from tests.baugruppe.beispiel_bewegung import BAUGRUPPE, kopie

EINS = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
STATISCH = {"schieber": {"status": 2, "fixiert": False}, "hebel": {"status": 2, "fixiert": False}}


def _t(c, v=(0.0, 0.0, 0.0)) -> list[float]:
    """Transform2.ArrayData aus der Spaltenform c (C · p = Bild von p) und einer Verschiebung in mm."""
    return [c[k % 3][k // 3] for k in range(9)] + [x / 1000 for x in v] + [1.0, 0.0, 0.0, 0.0]


def _mal(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _bws():
    return bewegungen(BAUGRUPPE, lade_standard())


def test_bewegungen_aus_der_spec():
    assert _bws() == [Bewegung("Hub", "g1", "abstand", "schieber", 0.0, 100.0, 4),
                      Bewegung("Schwenk", "g2", "winkel", "hebel", 0.0, 90.0, 4)]


def test_schritte_aus_der_vorgabe():
    spec = kopie(BAUGRUPPE)
    del spec["bewegungen"][0]["schritte"]
    assert bewegungen(spec, {"bewegung_schritte": 16})[0].schritte == 16


def test_stellungen():
    hub = _bws()[0]
    assert hub.schrittweite == 25.0 and hub.stellungen() == [0.0, 25.0, 50.0, 75.0, 100.0]


def test_verschiebung_und_weg():
    hub = _bws()[0]
    t0, t1 = _t(EINS, (-70, 30, -10)), _t(EINS, (30, 30, -10))
    assert verschiebung_mm(t0, t1) == pytest.approx((100.0, 0.0, 0.0))
    assert weg(hub, t0, t1) == pytest.approx(100.0)


def test_drehung_achse_und_winkel():
    t1 = _t(drehmatrix((0, 1, 0), 90))
    achse, winkel = achse_winkel(relative_drehung(_t(EINS), t1))
    assert achse == pytest.approx((0.0, 1.0, 0.0)) and winkel == pytest.approx(90.0)
    assert weg(_bws()[1], _t(EINS), t1) == pytest.approx(90.0)
    assert [c * 1 for c in drehmatrix((0, 1, 0), 90)[2]] == pytest.approx([-1.0, 0.0, 0.0])  # +x → −z


def test_relative_drehung_bei_gedrehter_ausgangslage():
    c0 = drehmatrix((0, 0, 1), 30)
    q = relative_drehung(_t(c0), _t(_mal(drehmatrix((0, 1, 0), 90), c0)))
    assert winkel_grad(_mal(q, [list(r) for r in zip(*drehmatrix((0, 1, 0), 90))])) == pytest.approx(0.0, abs=1e-6)


def test_ist_bewegt():
    assert not ist_bewegt(_t(EINS, (1, 2, 3)), _t(EINS, (1, 2, 3.0005)))
    assert ist_bewegt(_t(EINS, (1, 2, 3)), _t(EINS, (1, 2, 3.01)))
    assert ist_bewegt(_t(EINS), _t(drehmatrix((0, 1, 0), 0.01)))


def test_soll_weg_winkel_gefaltet():
    schwenk = Bewegung("S", "g", "winkel", "k", 0.0, 300.0, 4)
    assert soll_weg(schwenk, 270) == pytest.approx(90.0) and soll_weg(schwenk, 92.8) == pytest.approx(92.8)
    assert soll_weg(Bewegung("H", "g", "abstand", "k", 10.0, 50.0, 4), 5) == pytest.approx(5.0)


def test_vereinige_und_schnitt():
    a, b = [0, 0, 0, 10, 10, 10], [5, 5, 5, 20, 20, 20]
    assert vereinige(None, a) == a and vereinige(a, b) == [0, 0, 0, 20, 20, 20]
    assert schnitt(a, b) == [5, 5, 5, 10, 10, 10]
    assert schnitt(a, [10, 0, 0, 20, 10, 10]) is None  # nur Berührung


def test_paare():
    a, b, c = (Bewegung(n, "g", "abstand", "k", 0.0, 1.0, 2) for n in "ABC")
    grund = {"A": Lauf("A", raum=[0, 0, 0, 10, 10, 10]), "B": Lauf("B", raum=[5, 5, 5, 20, 20, 20]),
             "C": Lauf("C", raum=[50, 50, 50, 60, 60, 60])}
    assert paare([a, b, c], grund) == [(a, b, [5, 5, 5, 10, 10, 10])]


def _messwerte(hub_ende=(100, 0, 0), achse=(0, 1, 0), gehalten=None, grenze=None, kollisionen=(), fehler=None):
    hub = Lauf("Hub", stellungen=[0.0, 100.0], fehler=fehler, grenze=grenze or {"oben": False, "unten": None},
               lagen=[{"schieber": _t(EINS), "hebel": _t(EINS)},
                      {"schieber": _t(EINS, hub_ende), "hebel": _t(EINS, hub_ende)}])
    schwenk = Lauf("Schwenk", stellungen=[0.0, 90.0], grenze={"oben": False, "unten": None},
                   lagen=[{"hebel": _t(EINS)}, {"hebel": _t(drehmatrix(achse, 90))}])
    paar = Lauf("Schwenk", gegen={"Hub": "max"}, stellungen=[0.0, 90.0], kollisionen=list(kollisionen))
    return BewegungsMesswerte(gehalten or {"schieber": 3, "hebel": 3}, [hub, schwenk, paar], [])


def _pruefungen(m, statisch=STATISCH):
    pruefungen, _ = bewerte_bewegungen(kopie(BAUGRUPPE), _bws(), m, statisch, 0.1)
    return {p["id"]: p for p in pruefungen}


def test_bewertung_bestanden():
    pruefungen, bericht = bewerte_bewegungen(kopie(BAUGRUPPE), _bws(), _messwerte(), STATISCH, 0.1)
    assert [p["id"] for p in pruefungen] == [
        "freiheitsgrad:schieber", "bewegung:Hub", "bewegung_kollision:Hub", "grenze:Hub", "endlage:Hub:schieber",
        "endlage:Hub:hebel", "freiheitsgrad:hebel", "bewegung:Schwenk", "bewegung_kollision:Schwenk", "grenze:Schwenk",
        "endlage:Schwenk:hebel"]
    assert all(p["ok"] is True for p in pruefungen), pruefungen
    assert [(x["bewegung"], x["gegen"], x["stellungen"]) for x in bericht["laeufe"]] == [
        ("Hub", {}, 2), ("Schwenk", {}, 2), ("Schwenk", {"Hub": "max"}, 2)]


def test_endlage_falsche_richtung():
    p = _pruefungen(_messwerte(hub_ende=(-100, 0, 0)))
    assert p["endlage:Hub:schieber"]["ok"] is False and p["endlage:Hub:schieber"]["ist"] == pytest.approx([-100, 0, 0])
    assert p["endlage:Hub:hebel"]["ok"] is False


def test_endlage_falsche_drehachse():
    p = _pruefungen(_messwerte(achse=(0, -1, 0)))["endlage:Schwenk:hebel"]
    assert p["ok"] is False and p["abweichung_grad"] == pytest.approx(180.0)
    assert p["ist"]["achse"] == pytest.approx([0, -1, 0]) and p["ist"]["winkel"] == pytest.approx(90.0)


def test_freiheitsgrad():
    p = _pruefungen(_messwerte(gehalten={"schieber": 3, "hebel": 2}),
                    {"schieber": {"status": 3}, "hebel": {"status": 2}})
    assert p["freiheitsgrad:schieber"]["ok"] is False and "nicht beweglich" in p["freiheitsgrad:schieber"]["hinweis"]
    assert p["freiheitsgrad:hebel"]["ok"] is False
    assert "mehr als ein Freiheitsgrad offen" in p["freiheitsgrad:hebel"]["hinweis"]


def test_grenze_geht_durch():
    p = _pruefungen(_messwerte(grenze={"oben": True, "unten": None}))["grenze:Hub"]
    assert p["ok"] is False and "oben" in p["hinweis"]


def test_kollision_und_lauffehler():
    kollision = {"paar": ["anschlag", "hebel"], "volumen": 5.0, "stellung": 67.5, "gegen": {"Hub": "max"}, "bild": "x.png"}
    p = _pruefungen(_messwerte(kollisionen=[kollision], fehler={"stellung": 50.0, "meldung": "Rebuild-Fehler"}))
    assert p["bewegung_kollision:Schwenk"]["ok"] is False and p["bewegung_kollision:Schwenk"]["knoten"] == ["anschlag", "hebel"]
    assert p["bewegung:Hub"]["ok"] is False and p["grenze:Hub"]["ok"] is None
    assert p["endlage:Hub:schieber"]["ok"] is False and "abgebrochen" in p["endlage:Hub:schieber"]["hinweis"]


def test_ergaenze_bericht():
    bericht = {"bestanden": True, "pruefungen": [{"id": "rebuild", "ok": True}], "maengel": [], "bilder": {"iso": "i.png"}}
    neu = ergaenze_bericht(bericht, [{"id": "grenze:Hub", "ok": False, "hinweis": "geht durch", "knoten": ["schieber"]}],
                           {"laeufe": [], "paare": []}, {"Hub-min": "Hub-min.png"})
    assert neu["bestanden"] is False and [m["pruefung"] for m in neu["maengel"]] == ["grenze:Hub"]
    assert neu["bilder"] == {"iso": "i.png", "Hub-min": "Hub-min.png"} and neu["bewegungen"] == {"laeufe": [], "paare": []}
    assert len(neu["pruefungen"]) == 2 and bericht["maengel"] == []  # das Original bleibt unverändert
```

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bewegung.py -q`
Expected: FAIL mit `ModuleNotFoundError: No module named 'swki.baugruppe.bewegung'`.

- [ ] **Step 3: `swki/baugruppe/bewegung.py` (neu)**

```python
"""Bewegungsprüfung ohne SolidWorks (Spec 4a §8.2): Bewegungen aus der Spezifikation, Lagevergleich aus
Transformationen, überstrichene Räume, Paare, Endlagen und die Bewertung zu Prüfungen und Mängeln.

Transformationen wie IComponent2.Transform2.ArrayData: [0:9] Drehung in Zeilenvektor-Konvention (Zeile i = Bild der
Teilachse i, wie swki.baugruppe.geometrie.transformiere), [9:12] Verschiebung in m. Drehungen rechnet dieses Modul in
Spaltenform (C · p = Bild von p). Hüllquader [xmin, ymin, zmin, xmax, ymax, zmax] in mm."""

import math
from dataclasses import dataclass, field

from swki.baugruppe.bewertung import STATUS_TEXT, UNTERBESTIMMT, VOLL_BESTIMMT
from swki.pruefung.bewertung import _beschreibung, _pruefung
from swki.spec.ausdruck import auswerten
from swki.verbindung import in_mm

TOL_BEWEGT_MM = 1e-3      # Präzisierung 7
TOL_BEWEGT_DREHUNG = 1e-6
TOL_WINKEL_GRAD = 0.01    # Präzisierung 6
TOL_RAUM_MM = 1e-3        # Präzisierung 7


@dataclass(frozen=True)
class Bewegung:
    name: str
    grenze: str          # ID der Grenzverknüpfung
    art: str             # "abstand" | "winkel"
    komponente: str      # bewegte Komponente (Seite a der Grenze)
    min: float           # mm bzw. Grad
    max: float
    schritte: int

    @property
    def schrittweite(self) -> float:
        return (self.max - self.min) / self.schritte

    def stellungen(self) -> list[float]:
        return [self.min + i * self.schrittweite for i in range(self.schritte)] + [self.max]


def bewegungen(spec: dict, standard: dict) -> list[Bewegung]:
    """Bewegungen der Spezifikation mit ausgewerteten Grenzen (setzt eine plausible Spezifikation voraus)."""
    p = spec.get("parameter", {})
    grenzen = {v["id"]: v for v in spec.get("verknuepfungen", [])}
    ergebnis = []
    for b in spec.get("bewegungen", []):
        v = grenzen[b["grenze"]]
        ergebnis.append(Bewegung(b["name"], b["grenze"], "abstand" if v["typ"] == "grenze_abstand" else "winkel",
                                 v["a"]["komponente"], auswerten(v["min"], p), auswerten(v["max"], p),
                                 b.get("schritte", standard["bewegung_schritte"])))
    return ergebnis


def _drehung(t) -> list[list[float]]:
    """Spaltenform C aus der Zeilenvektor-Konvention: C[i][j] = t[3j + i]."""
    return [[t[3 * j + i] for j in range(3)] for i in range(3)]


def _mal(a, b) -> list[list[float]]:
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _transponiert(a) -> list[list[float]]:
    return [[a[j][i] for j in range(3)] for i in range(3)]


def verschiebung_mm(t0, t1) -> tuple[float, float, float]:
    """Verschiebung des Komponentenursprungs von t0 nach t1 in Baugruppenkoordinaten (mm)."""
    return tuple(in_mm(t1[9 + i] - t0[9 + i]) for i in range(3))


def relative_drehung(t0, t1) -> list[list[float]]:
    """Drehung der Komponente von Lage t0 nach t1 in Baugruppenkoordinaten (Spaltenform): C1 · C0ᵀ."""
    return _mal(_drehung(t1), _transponiert(_drehung(t0)))


def winkel_grad(q) -> float:
    """Drehwinkel einer Drehmatrix in Grad (0 … 180)."""
    return math.degrees(math.acos(max(-1.0, min(1.0, (q[0][0] + q[1][1] + q[2][2] - 1) / 2))))


def achse_winkel(q) -> tuple[tuple[float, float, float] | None, float]:
    """Drehachse (Einheitsvektor, Rechte-Hand-Regel) und Winkel in Grad; bei 0° und 180° ohne Achse."""
    w = winkel_grad(q)
    v = (q[2][1] - q[1][2], q[0][2] - q[2][0], q[1][0] - q[0][1])
    n = math.sqrt(sum(c * c for c in v))
    if n < 1e-12:
        return None, w
    return tuple(c / n for c in v), w


def drehmatrix(achse, winkel: float) -> list[list[float]]:
    """Drehung um achse (wird normiert) um winkel Grad nach der Rechte-Hand-Regel, Spaltenform (Rodrigues)."""
    n = math.sqrt(sum(c * c for c in achse))
    x, y, z = (c / n for c in achse)
    a = math.radians(winkel)
    c, s = math.cos(a), math.sin(a)
    k = 1 - c
    return [[c + x * x * k, x * y * k - z * s, x * z * k + y * s],
            [y * x * k + z * s, c + y * y * k, y * z * k - x * s],
            [z * x * k - y * s, z * y * k + x * s, c + z * z * k]]


def ist_bewegt(t0, t1) -> bool:
    return (any(abs(c) > TOL_BEWEGT_MM for c in verschiebung_mm(t0, t1))
            or any(abs(t1[i] - t0[i]) > TOL_BEWEGT_DREHUNG for i in range(9)))


def weg(b: Bewegung, t0, t1) -> float:
    """Zurückgelegter Weg der bewegten Komponente: Betrag der Verschiebung (mm) bzw. Drehwinkel (Grad)."""
    if b.art == "abstand":
        return math.sqrt(sum(c * c for c in verschiebung_mm(t0, t1)))
    return winkel_grad(relative_drehung(t0, t1))


def soll_weg(b: Bewegung, wert: float) -> float:
    """Soll zu weg(): |wert − min|; beim Winkel auf [0, 180] gefaltet wie der Drehwinkel aus der Matrix."""
    d = abs(wert - b.min)
    if b.art == "winkel":
        d %= 360
        d = min(d, 360 - d)
    return d


def vereinige(a: list[float] | None, b: list[float]) -> list[float]:
    if a is None:
        return list(b)
    return [min(a[i], b[i]) for i in range(3)] + [max(a[i], b[i]) for i in range(3, 6)]


def schnitt(a: list[float], b: list[float]) -> list[float] | None:
    """Schnitt zweier Hüllquader oder None, wenn sie sich in einer Achse nur berühren oder gar nicht überdecken."""
    unten = [max(a[i], b[i]) for i in range(3)]
    oben = [min(a[i + 3], b[i + 3]) for i in range(3)]
    return unten + oben if all(oben[i] - unten[i] > TOL_RAUM_MM for i in range(3)) else None


@dataclass
class Lauf:
    """Ein Durchlauf einer Bewegung von min bis max (Grundstellungslauf: gegen = {}; Paarlauf: {andere: "max"})."""
    bewegung: str
    gegen: dict[str, str] = field(default_factory=dict)
    stellungen: list[float] = field(default_factory=list)            # angefahrene Stellungen
    lagen: list[dict[str, list[float]]] = field(default_factory=list)  # Grundstellungslauf: je Stellung Instanz → Transform
    bewegt: list[str] = field(default_factory=list)
    raum: list[float] | None = None
    kollisionen: list[dict] = field(default_factory=list)  # {"paar", "volumen", "stellung", "gegen", "bild"}
    fehler: dict | None = None                              # {"stellung", "meldung"}: Lauf vorzeitig beendet
    grenze: dict = field(default_factory=dict)              # {"oben": bool, "unten": bool | None}; True = ging durch
    bilder: dict[str, str] = field(default_factory=dict)    # "min" | "mitte" | "max" → Pfad
    dauer_s: float = 0.0


@dataclass
class BewegungsMesswerte:
    status_gehalten: dict[str, int]  # Instanz-ID → GetConstrainedStatus, alle Bewegungen auf min festgehalten
    laeufe: list[Lauf]
    paare: list[dict]                # {"bewegungen": [b1, b2], "schnitt": [...]}


def paare(bws: list[Bewegung], grund: dict[str, Lauf]) -> list[tuple[Bewegung, Bewegung, list[float]]]:
    """Paare von Bewegungen, deren überstrichene Räume sich schneiden (Spec 4a §8.2.6), in Spec-Reihenfolge."""
    ergebnis = []
    for i, b1 in enumerate(bws):
        for b2 in bws[i + 1:]:
            r1, r2 = grund[b1.name].raum, grund[b2.name].raum
            if r1 is not None and r2 is not None and (s := schnitt(r1, r2)) is not None:
                ergebnis.append((b1, b2, s))
    return ergebnis


def _freiheitsgrad(b: Bewegung, statisch: dict[str, dict], gehalten: dict[str, int]) -> dict:
    vorher = (statisch.get(b.komponente) or {}).get("status")
    nachher = gehalten.get(b.komponente)
    gruende = []
    if vorher != UNTERBESTIMMT:
        gruende.append(f"in Grundstellung {STATUS_TEXT.get(vorher, vorher)} statt unterbestimmt (nicht beweglich)")
    if nachher != VOLL_BESTIMMT:
        gruende.append(f"mit Antrieb {STATUS_TEXT.get(nachher, nachher)} statt voll bestimmt"
                       + (" (mehr als ein Freiheitsgrad offen)" if nachher == UNTERBESTIMMT else ""))
    return _pruefung(f"freiheitsgrad:{b.komponente}", not gruende,
                     ist={"grundstellung": vorher, "mit_antrieb": nachher}, knoten=[b.komponente],
                     **({"hinweis": "; ".join(gruende)} if gruende else {}))


def _grenze(b: Bewegung, grund: Lauf | None) -> dict:
    pid = f"grenze:{b.name}"
    if grund is None or grund.fehler is not None:
        return _pruefung(pid, None, hinweis="Lauf abgebrochen – Grenze nicht geprüft", knoten=[b.komponente])
    durch = [s for s in ("oben", "unten") if grund.grenze.get(s)]
    if durch:
        return _pruefung(pid, False, ist=grund.grenze, knoten=[b.komponente],
                         hinweis=f"Schritt {' und '.join(durch)} über die Grenze ging durch – die Grenze im Modell wirkt "
                                 "nicht wie freigegeben")
    return _pruefung(pid, True, ist=grund.grenze, knoten=[])


def _endlage(b: Bewegung, e: dict, grund: Lauf | None, p: dict, tol_mm: float) -> dict:
    kid = e["komponente"]
    pid = f"endlage:{b.name}:{kid}"
    if grund is None or grund.fehler is not None or not grund.lagen:
        return _pruefung(pid, False, hinweis="Lauf abgebrochen – Endlage nicht messbar", knoten=[kid])
    erste, letzte = grund.lagen[0].get(kid), grund.lagen[-1].get(kid)
    if erste is None or letzte is None:
        return _pruefung(pid, False, hinweis=f"Komponente {kid} fehlt in der Baugruppe", knoten=[kid])
    if "verschiebung" in e:
        soll = [auswerten(w, p) for w in e["verschiebung"]]
        ist = [round(c, 4) for c in verschiebung_mm(erste, letzte)]
        return _pruefung(pid, all(abs(i - s) <= tol_mm for i, s in zip(ist, soll)), ist=ist, soll=soll, tol=tol_mm,
                         knoten=[kid])
    achse = [auswerten(w, p) for w in e["drehung"]["achse"]]
    winkel = auswerten(e["drehung"]["winkel"], p)
    q = relative_drehung(erste, letzte)
    abweichung = winkel_grad(_mal(q, _transponiert(drehmatrix(achse, winkel))))
    ist_achse, ist_winkel = achse_winkel(q)
    return _pruefung(pid, abweichung <= TOL_WINKEL_GRAD,
                     ist={"achse": [round(c, 6) for c in ist_achse] if ist_achse else None, "winkel": round(ist_winkel, 4)},
                     soll={"achse": achse, "winkel": winkel}, abweichung_grad=round(abweichung, 4), knoten=[kid])


def _lauf_bericht(lauf: Lauf) -> dict:
    return {"bewegung": lauf.bewegung, "gegen": lauf.gegen, "stellungen": len(lauf.stellungen), "bewegt": lauf.bewegt,
            "raum": [round(v, 3) for v in lauf.raum] if lauf.raum else None, "kollisionen": len(lauf.kollisionen),
            "grenze": lauf.grenze, "fehler": lauf.fehler, "dauer_s": lauf.dauer_s}


def bewerte_bewegungen(spec: dict, bws: list[Bewegung], m: BewegungsMesswerte, statisch: dict[str, dict],
                       tol_mm: float) -> tuple[list[dict], dict]:
    """Prüfungen je Bewegung (Spec 4a §8.2): freiheitsgrad, bewegung, bewegung_kollision, grenze, endlage; dazu der
    Bewegungsteil des Prüfberichts (Spec 4a §8.5). statisch: Zustand der Komponenten aus der statischen Prüfung."""
    p = spec.get("parameter", {})
    erwartet = {b["name"]: b.get("erwartet", {}) for b in spec.get("bewegungen", [])}
    pruefungen = []
    for b in bws:
        laeufe = [lauf for lauf in m.laeufe if lauf.bewegung == b.name]
        grund = next((lauf for lauf in laeufe if not lauf.gegen), None)
        pruefungen.append(_freiheitsgrad(b, statisch, m.status_gehalten))
        fehler = [{"gegen": lauf.gegen, **lauf.fehler} for lauf in laeufe if lauf.fehler]
        pruefungen.append(_pruefung(f"bewegung:{b.name}", not fehler, ist=fehler, knoten=[b.komponente] if fehler else []))
        kollisionen = [k for lauf in laeufe for k in lauf.kollisionen]
        pruefungen.append(_pruefung(f"bewegung_kollision:{b.name}", not kollisionen, ist=kollisionen,
                                    knoten=sorted({x for k in kollisionen for x in k["paar"]})))
        pruefungen.append(_grenze(b, grund))
        pruefungen += [_endlage(b, e, grund, p, tol_mm) for e in erwartet.get(b.name, {}).get("endlagen", [])]
    return pruefungen, {"laeufe": [_lauf_bericht(lauf) for lauf in m.laeufe], "paare": m.paare}


def ergaenze_bericht(bericht: dict, pruefungen: list[dict], bewegungsbericht: dict, bilder: dict[str, str]) -> dict:
    """Prüfbericht der Statik um die Bewegungsprüfung ergänzen (neues Dict; Mängel, bestanden, Bilder)."""
    neu = [{"pruefung": e["id"], "knoten": e["knoten"], "beschreibung": _beschreibung(e)}
           for e in pruefungen if e["ok"] is False]
    return {**bericht, "pruefungen": bericht["pruefungen"] + pruefungen, "maengel": bericht["maengel"] + neu,
            "bestanden": bericht["bestanden"] and not neu, "bewegungen": bewegungsbericht,
            "bilder": {**bericht.get("bilder", {}), **bilder}}
```

- [ ] **Step 4: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bewegung.py -q` → 17 passed.
Run: `.venv\Scripts\python.exe -m pytest -q` → **674 passed, 109 deselected** (657 + 17).

- [ ] **Step 5: Commit**

```powershell
git add swki/baugruppe/bewegung.py tests/baugruppe/test_bewegung.py
git commit -m "baugruppe: Bewegungslogik ohne SolidWorks (Lagevergleich, Räume, Paare, Endlagen, Bewertung)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Ablauf der Bewegungsprüfung (`swki/baugruppe/bewegungslauf.py`, ohne SolidWorks)

**Files:**
- Create: `swki/baugruppe/bewegungslauf.py`
- Modify: `swki/baugruppe/fehler.py` (+ `GRUNDSTELLUNG_FEHLER`)
- Create: `tests/baugruppe/attrappe_mechanik.py`, `tests/baugruppe/test_bewegungslauf.py`

**Interfaces:**
- Consumes: `Bewegung`, `Lauf`, `BewegungsMesswerte`, `ist_bewegt`, `paare`, `soll_weg`, `vereinige`, `weg`, `TOL_WINKEL_GRAD` (Task 4); `SwkiFehler`.
- Produces (von Task 6/7 verwendet):
  - `GRUNDSTELLUNG_FEHLER = "GRUNDSTELLUNG_FEHLER"` in `swki/baugruppe/fehler.py`.
  - `Mechanik` (Protocol): `halte(b, wert) -> None`, `stelle(b, wert) -> str | None`, `loese(b) -> None`, `status() -> dict[str, int]`, `zustand() -> dict[str, tuple[list[float], list[float]]]` (Instanz-ID → (Transform, Hüllquader mm)), `interferenzen() -> list[dict]` (`{"paar": [Instanz-IDs], "volumen"}`), `bild(name) -> str`, `speicher_mb() -> float`.
  - `SpeicherKnapp(privat_mb, grenze_mb)` und `StellungFehler(bewegung, wert, meldung)` (beide `SwkiFehler` mit `daten["code"]`).
  - `fahre(mech, bws, bekannt, grenze_mb, tol_mm) -> BewegungsMesswerte`.
  - `tests/baugruppe/attrappe_mechanik.py`: `Attrappe(…)` für die Bewegungsprobe.

- [ ] **Step 1: `tests/baugruppe/attrappe_mechanik.py` (neu)**

```python
"""Attrappe der Mechanik-Schnittstelle (swki.baugruppe.bewegungslauf.Mechanik) für die Bewegungsprobe: der Schieber
verschiebt in x um den Hub, der Hebel fährt mit und dreht um +y um den Schwenk (Drehpunkt in x = Hub − 60, z = −10)."""

import math

from swki.baugruppe.bewegung import drehmatrix

EINS = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def transform(c, v=(0.0, 0.0, 0.0)) -> list[float]:
    """Transform2.ArrayData aus der Spaltenform c und einer Verschiebung in mm."""
    return [c[k % 3][k // 3] for k in range(9)] + [x / 1000 for x in v] + [1.0, 0.0, 0.0, 0.0]


def _hebelkiste(hub: float, schwenk: float) -> list[float]:
    a = math.radians(schwenk)
    c, s = math.cos(a), math.sin(a)
    ecken = [(c * x + s * z, -s * x + c * z) for x in (-7, 43) for z in (-6, 6)]
    xs = [hub - 60 + e[0] for e in ecken]
    zs = [-10 + e[1] for e in ecken]
    return [min(xs), 40.0, min(zs), max(xs), 48.0, max(zs)]


class Attrappe:
    def __init__(self, durchlass=(), kollision=None, fehler_bei=None, speicher=1000.0, loese_wirft=False,
                 interferenz_wirft=False):
        self.werte = {"Hub": 0.0, "Schwenk": 0.0}
        self.grenzen = {"Hub": (0.0, 100.0), "Schwenk": (0.0, 90.0)}
        self.durchlass = set(durchlass)        # Bewegungen, deren Grenze im Modell nicht wirkt
        self.kollision = kollision or (lambda werte: [])
        self.fehler_bei = fehler_bei           # (Bewegung, Wert): dort meldet stelle() einen Fehler
        self.speicher = speicher
        self.loese_wirft = loese_wirft
        self.interferenz_wirft = interferenz_wirft
        self.aufrufe: list[tuple] = []
        self.geloest: list[str] = []
        self.bilder: list[str] = []

    def halte(self, b, wert):
        self.aufrufe.append(("halte", b.name))
        self.werte[b.name] = wert

    def stelle(self, b, wert):
        unten, oben = self.grenzen[b.name]
        if self.fehler_bei == (b.name, wert):
            return "Rebuild-Fehler"
        if not unten - 1e-9 <= wert <= oben + 1e-9 and b.name not in self.durchlass:
            return "Verknüpfungsfehler: g"
        self.werte[b.name] = wert
        return None

    def loese(self, b):
        self.geloest.append(b.name)
        if self.loese_wirft:
            raise RuntimeError("Löschen kaputt")

    def status(self):
        self.aufrufe.append(("status",))
        return {"platte": 3, "schieber": 3, "hebel": 3}

    def zustand(self):
        hub, schwenk = self.werte["Hub"], self.werte["Schwenk"]
        return {"platte": (transform(EINS), [-100.0, 0.0, -30.0, 100.0, 20.0, 30.0]),
                "schieber": (transform(EINS, (hub, 0, 0)), [hub - 100, 20.0, -30.0, hub - 40, 40.0, 10.0]),
                "hebel": (transform(drehmatrix((0, 1, 0), schwenk), (hub - 60, 0, -10)), _hebelkiste(hub, schwenk))}

    def interferenzen(self):
        if self.interferenz_wirft:
            raise RuntimeError("Kollision kaputt")
        return [{"paar": ["bolzen", "schieber"], "volumen": 1.0}] + self.kollision(self.werte)

    def bild(self, name):
        self.bilder.append(name)
        return f"{name}.png"

    def speicher_mb(self):
        return self.speicher
```

- [ ] **Step 2: Failing tests – `tests/baugruppe/test_bewegungslauf.py` (neu)**

```python
"""Stufe 4a: Ablauf der Bewegungsprüfung mit der Attrappe – Grundstellung, Grenze, Paarläufe, Speicher, Aufräumen."""

import pytest

from swki.baugruppe.bewegung import bewegungen
from swki.baugruppe.bewegungslauf import SpeicherKnapp, fahre
from swki.konfig import lade_standard
from tests.baugruppe.attrappe_mechanik import Attrappe
from tests.baugruppe.beispiel_bewegung import BAUGRUPPE

BEKANNT = {frozenset({"bolzen", "schieber"})}  # statische Überlappung: in den Läufen nicht neu


def _fahre(mech, grenze_mb=3500):
    return fahre(mech, bewegungen(BAUGRUPPE, lade_standard()), BEKANNT, grenze_mb, 0.1)


def test_ohne_befund():
    mech = Attrappe()
    m = _fahre(mech)
    assert mech.aufrufe[:3] == [("halte", "Hub"), ("halte", "Schwenk"), ("status",)]  # erst alle festhalten
    assert m.status_gehalten == {"platte": 3, "schieber": 3, "hebel": 3}
    assert [(x.bewegung, x.gegen) for x in m.laeufe] == [("Hub", {}), ("Schwenk", {}), ("Hub", {"Schwenk": "max"}),
                                                          ("Schwenk", {"Hub": "max"})]
    hub = m.laeufe[0]
    assert hub.stellungen == [0.0, 25.0, 50.0, 75.0, 100.0] and hub.grenze == {"oben": False, "unten": None}
    assert all(x.kollisionen == [] and x.fehler is None for x in m.laeufe)
    assert [p["bewegungen"] for p in m.paare] == [["Hub", "Schwenk"]]
    assert mech.bilder == ["Hub-min", "Hub-mitte", "Hub-max", "Schwenk-min", "Schwenk-mitte", "Schwenk-max"]
    assert mech.geloest == ["Schwenk", "Hub"] and mech.werte == {"Hub": 0.0, "Schwenk": 0.0}


def test_bewegte_menge_und_raum():
    hub = _fahre(Attrappe()).laeufe[0]
    assert hub.bewegt == ["schieber", "hebel"] and len(hub.lagen) == 5
    assert hub.raum == pytest.approx([-100.0, 20.0, -30.0, 83.0, 48.0, 10.0])


def test_kollision_nur_im_paarlauf():
    mech = Attrappe(kollision=lambda w: [{"paar": ["anschlag", "hebel"], "volumen": 5.0}]
                    if w["Hub"] >= 75 and w["Schwenk"] >= 60 else [])
    m = _fahre(mech)
    assert [x.kollisionen for x in m.laeufe[:2]] == [[], []]
    assert [(k["stellung"], k["gegen"], k["paar"], k["bild"]) for x in m.laeufe[2:] for k in x.kollisionen] == [
        (75.0, {"Schwenk": "max"}, ["anschlag", "hebel"], "Hub-kollision-Schwenk-1.png"),
        (67.5, {"Hub": "max"}, ["anschlag", "hebel"], "Schwenk-kollision-Hub-1.png")]


def test_grenze_geht_durch():
    assert _fahre(Attrappe(durchlass={"Hub"})).laeufe[0].grenze == {"oben": True, "unten": None}


def test_lauffehler_beendet_den_lauf():
    m = _fahre(Attrappe(fehler_bei=("Hub", 50.0)))
    hub = m.laeufe[0]
    assert hub.fehler == {"stellung": 50.0, "meldung": "Rebuild-Fehler"} and hub.stellungen == [0.0, 25.0]
    assert hub.grenze == {} and [x.bewegung for x in m.laeufe] == ["Hub", "Schwenk"]  # keine Paarläufe mit Hub


def test_speicher_knapp_raeumt_auf():
    mech = Attrappe(speicher=5000.0)
    with pytest.raises(SpeicherKnapp) as e:
        _fahre(mech)
    assert e.value.daten == {"code": "SPEICHER_KNAPP", "privat_mb": 5000, "grenze_mb": 3500}
    assert mech.geloest == ["Schwenk", "Hub"]


def test_aufraeumfehler_verdeckt_die_ursache_nicht():
    mech = Attrappe(interferenz_wirft=True, loese_wirft=True)
    with pytest.raises(RuntimeError, match="Kollision kaputt"):
        _fahre(mech)
    assert mech.geloest == ["Schwenk", "Hub"]
```

- [ ] **Step 3: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bewegungslauf.py -q`
Expected: FAIL mit `ModuleNotFoundError: No module named 'swki.baugruppe.bewegungslauf'`.

- [ ] **Step 4: `swki/baugruppe/fehler.py` – Code ergänzen**

```python
GRUNDSTELLUNG_FEHLER = "GRUNDSTELLUNG_FEHLER"  # Spec 4a §7.2/§10: eine Stellung ließ sich nicht herstellen
```

- [ ] **Step 5: `swki/baugruppe/bewegungslauf.py` (neu)**

```python
"""Ablauf der Bewegungsprüfung (Spec 4a §8.2–§8.4) über eine Mechanik-Schnittstelle: alle Bewegungen festhalten,
je Bewegung ein Grundstellungslauf mit „Grenze wirkt“, Paarläufe, Bilder, Speichergrenze, Aufräumen. Die
SolidWorks-Umsetzung ist swki.baugruppe.sw_bewegung.SwMechanik; die Tests nutzen eine Attrappe."""

import time
from typing import Protocol

from swki.baugruppe.bewegung import (TOL_WINKEL_GRAD, Bewegung, BewegungsMesswerte, Lauf, ist_bewegt, paare, soll_weg,
                                     vereinige, weg)
from swki.baugruppe.fehler import GRUNDSTELLUNG_FEHLER
from swki.cli import SwkiFehler

SPEICHER_KNAPP = "SPEICHER_KNAPP"


class SpeicherKnapp(SwkiFehler):
    """SolidWorks belegt mehr Private Bytes als speicher_grenze_mb (Spec 4a §8.4, Präzisierung 14)."""

    def __init__(self, privat_mb: float, grenze_mb: float):
        super().__init__(f"SolidWorks belegt {privat_mb:.0f} MB Private Bytes (Grenze {grenze_mb:.0f} MB) – SolidWorks "
                         "neu starten und swki pruefen erneut aufrufen")
        self.daten = {"code": SPEICHER_KNAPP, "privat_mb": round(privat_mb), "grenze_mb": grenze_mb}


class StellungFehler(SwkiFehler):
    """Eine Stellung, die gelingen muss (Grundstellung, Gegenstellung eines Paarlaufs), ließ sich nicht herstellen."""

    def __init__(self, bewegung: str, wert: float, meldung: str):
        super().__init__(f"Bewegung {bewegung}: Stellung {wert:g} nicht herstellbar ({meldung})")
        self.daten = {"code": GRUNDSTELLUNG_FEHLER, "bewegung": bewegung, "stellung": wert}


class Mechanik(Protocol):
    def halte(self, b: Bewegung, wert: float) -> None:
        """Treibende Verknüpfung anlegen (falls nötig) und auf wert stellen; StellungFehler, wenn das misslingt."""

    def stelle(self, b: Bewegung, wert: float) -> str | None:
        """Wert setzen und neu aufbauen; None = gelöst, sonst die Meldung."""

    def loese(self, b: Bewegung) -> None:
        """Treibende Verknüpfung löschen (ohne Wirkung, wenn keine angelegt ist)."""

    def status(self) -> dict[str, int]:
        """Instanz-ID → GetConstrainedStatus."""

    def zustand(self) -> dict[str, tuple[list[float], list[float]]]:
        """Instanz-ID → (Transform2.ArrayData, Hüllquader in mm)."""

    def interferenzen(self) -> list[dict]:
        """Überlappungen {"paar": [Instanz-IDs], "volumen": mm³}."""

    def bild(self, name: str) -> str:
        """Iso-Bild der aktuellen Stellung; liefert den Pfad."""

    def speicher_mb(self) -> float:
        """Private Bytes des SolidWorks-Prozesses in MB."""


def _speicher(mech: Mechanik, grenze_mb: float) -> None:
    if (mb := mech.speicher_mb()) > grenze_mb:
        raise SpeicherKnapp(mb, grenze_mb)


def _zurueck(mech: Mechanik, b: Bewegung, wert: float) -> None:
    if (meldung := mech.stelle(b, wert)) is not None:
        raise StellungFehler(b.name, wert, meldung)


def _durchlauf(mech: Mechanik, b: Bewegung, gegen: dict[str, str], bekannt: set[frozenset], grund: bool) -> Lauf:
    """Fährt b von min bis max. Im Grundstellungslauf mit Lagen, bewegter Menge, Raum und drei Bildern; in jedem Lauf
    die Kollisionen, die nicht schon statisch bestanden (je Paar nur die erste Stellung, mit Bild)."""
    lauf = Lauf(b.name, dict(gegen))
    beginn = time.perf_counter()
    stellungen = b.stellungen()
    bilder_bei = {0: "min", b.schritte // 2: "mitte", len(stellungen) - 1: "max"} if grund else {}
    gemeldet: set[frozenset] = set()
    kisten: list[dict[str, list[float]]] = []
    for i, w in enumerate(stellungen):
        if (meldung := mech.stelle(b, w)) is not None:
            lauf.fehler = {"stellung": round(w, 6), "meldung": meldung}
            break
        lauf.stellungen.append(round(w, 6))
        if grund:
            z = mech.zustand()
            lauf.lagen.append({k: t for k, (t, _) in z.items()})
            kisten.append({k: kiste for k, (_, kiste) in z.items()})
            erste = lauf.lagen[0]
            lauf.bewegt += [k for k, t in lauf.lagen[-1].items()
                            if k not in lauf.bewegt and k in erste and ist_bewegt(erste[k], t)]
        for kollision in mech.interferenzen():
            paar = frozenset(kollision["paar"])
            if paar in bekannt or paar in gemeldet:
                continue
            gemeldet.add(paar)
            name = "-".join([b.name, "kollision", *gegen, str(len(lauf.kollisionen) + 1)])
            lauf.kollisionen.append({"paar": sorted(paar), "volumen": kollision["volumen"], "stellung": round(w, 6),
                                     "gegen": dict(gegen), "bild": mech.bild(name)})
        if i in bilder_bei:
            lauf.bilder[bilder_bei[i]] = mech.bild(f"{b.name}-{bilder_bei[i]}")
    for k in lauf.bewegt:
        for schritt in kisten:
            if k in schritt:
                lauf.raum = vereinige(lauf.raum, schritt[k])
    lauf.dauer_s = round(time.perf_counter() - beginn, 3)
    return lauf


def _grenze_geht(mech: Mechanik, b: Bewegung, wert: float, start: list[float], tol_mm: float) -> bool:
    """True, wenn der Schritt auf wert (außerhalb der Grenze) durchgeht: gelöst und die bewegte Komponente am Sollweg
    (Präzisierung 4)."""
    if mech.stelle(b, wert) is not None:
        return False
    lage = mech.zustand().get(b.komponente)
    if lage is None:
        return False
    tol = tol_mm if b.art == "abstand" else TOL_WINKEL_GRAD
    return abs(weg(b, start, lage[0]) - soll_weg(b, wert)) <= tol


def fahre(mech: Mechanik, bws: list[Bewegung], bekannt: set[frozenset], grenze_mb: float,
          tol_mm: float) -> BewegungsMesswerte:
    """Alle Bewegungen auf min festhalten (Status lesen), je Bewegung ein Grundstellungslauf mit „Grenze wirkt“, dann
    die Paarläufe (die andere Bewegung auf max). Die treibenden Verknüpfungen werden immer gelöscht; ein Fehler beim
    Aufräumen verdeckt die Ursache nicht."""
    try:
        for b in bws:
            mech.halte(b, b.min)
        gehalten = mech.status()
        laeufe: list[Lauf] = []
        grund: dict[str, Lauf] = {}
        for b in bws:
            _speicher(mech, grenze_mb)
            lauf = _durchlauf(mech, b, {}, bekannt, True)
            if lauf.fehler is None:
                start = lauf.lagen[0][b.komponente]
                lauf.grenze["oben"] = _grenze_geht(mech, b, b.max + b.schrittweite / 2, start, tol_mm)
                _zurueck(mech, b, b.min)
                lauf.grenze["unten"] = (None if b.min == 0
                                        else _grenze_geht(mech, b, b.min - b.schrittweite / 2, start, tol_mm))
            _zurueck(mech, b, b.min)
            laeufe.append(lauf)
            grund[b.name] = lauf
        gefunden = paare(bws, grund)
        for b1, b2, _ in gefunden:
            for x, y in ((b1, b2), (b2, b1)):
                if grund[x.name].fehler is not None or grund[y.name].fehler is not None:
                    continue
                _speicher(mech, grenze_mb)
                _zurueck(mech, y, y.max)
                laeufe.append(_durchlauf(mech, x, {y.name: "max"}, bekannt, False))
                _zurueck(mech, x, x.min)
                _zurueck(mech, y, y.min)
        return BewegungsMesswerte(gehalten, laeufe, [{"bewegungen": [a.name, c.name], "schnitt": [round(v, 3) for v in s]}
                                                     for a, c, s in gefunden])
    finally:
        for b in reversed(bws):
            try:
                mech.loese(b)
            except Exception:
                pass  # Aufräumfehler verdecken die Ursache nicht (Muster aus dem Aufräumen nach 3b)
```

- [ ] **Step 6: Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_bewegungslauf.py -q` → 7 passed.
Run: `.venv\Scripts\python.exe -m pytest -q` → **681 passed, 109 deselected** (674 + 7).

- [ ] **Step 7: Commit**

```powershell
git add swki/baugruppe/bewegungslauf.py swki/baugruppe/fehler.py tests/baugruppe/attrappe_mechanik.py tests/baugruppe/test_bewegungslauf.py
git commit -m "baugruppe: Ablauf der Bewegungsprüfung (Grundstellung, Grenze, Paarläufe, Speichergrenze, Aufräumen)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: SolidWorks-Schicht – Grenzverknüpfung, Antrieb, Mechanik, Grundstellung beim Bau (live)

**Files:**
- Create: `swki/speicher.py`, `swki/baugruppe/sw_bewegung.py`
- Modify: `swki/baugruppe/sw_baugruppe.py` (`MATE_TYP`, `verknuepfe`; neu `GRENZ_MASSE`, `ANTRIEB`, `grenzen`, `_mate_werte`, `_gleichungen`, `treibe`, `stelle`, `loesche`, `kiste`)
- Modify: `swki/pruefung/bilder.py` (+ `iso_bild`)
- Modify: `swki/baugruppe/bau.py` (+ `_grundstellung`, Aufruf in `bauen`)
- Create: `tests/test_speicher.py`, `tests/baugruppe/test_sw_bewegung.py`, `tests/live/test_live_bewegung.py`

**Interfaces:**
- Consumes: `Verknuepfung` (min/max), `GRENZEN` (Task 2); `Bewegung`, `bewegungen()` (Task 4); `StellungFehler`, `Mechanik` (Task 5); `GRUNDSTELLUNG_FEHLER` (Task 5); `verknuepfe`, `verknuepfungen`, `fehlercode`, `_loesche`, `transform`, `status`, `interferenzen`, `in_baugruppe` (`sw_baugruppe.py`); `Baulauf`, `_entitaet`, `_mit_kontext` (`bau.py`).
- Produces:
  - `privat_mb(pid: int) -> float` (`swki/speicher.py`).
  - `iso_bild(app, model, pfad: Path) -> str` (`swki/pruefung/bilder.py`).
  - `sw_baugruppe.grenzen(v, parameter) -> dict[str, tuple[float, str | None]]`, `treibe(asm, v, a, b, wert) -> IFeature` (Name `<id>.antrieb`), `stelle(asm, antrieb, art, wert) -> str | None`, `loesche(asm, feature)`, `kiste(komp) -> list[float]`; `GRENZ_MASSE = {"max": "D2", "min": "D3"}`.
  - `SwMechanik(app, asm, grenzen, entitaet, komponenten, bilder=None)` erfüllt `Mechanik` (Task 5).
  - `bau._grundstellung(b, alle) -> Exception | None`; Knoten `grundstellung:<Bewegung>`; Phase `grundstellung` nur bei Specs mit `bewegungen`.

**Vor dem Task:** Die Controller-Entscheidungen zu Spike-Zeilen 1, 2, 3, 5, 6 und 9 stehen im Ledger; weichen sie ab, gilt die Spalte „sonst“ (z. B. andere `GRENZ_MASSE`, `kiste()` aus Teilebox und Transform).

- [ ] **Step 1: Failing tests – `tests/test_speicher.py` (neu)**

```python
import os

from swki.speicher import privat_mb


def test_privat_mb_des_eigenen_prozesses():
    assert 1 < privat_mb(os.getpid()) < 100_000
```

- [ ] **Step 2: Failing tests – `tests/baugruppe/test_sw_bewegung.py` (neu)**

```python
"""Stufe 4a: SolidWorks-Schicht mit Attrappen – Grenzverknüpfung an AddMate5, Gleichung der Grenze, treibende
Verknüpfung, Stellen, Grundstellung beim Bau."""

import math
from types import SimpleNamespace

import pytest

from swki.baugruppe import bau, sw_baugruppe
from swki.baugruppe.aufloesen import Verknuepfung, verknuepfungen
from swki.baugruppe.bewegungslauf import StellungFehler
from swki.baugruppe.laden import lade_baugruppe
from swki.compiler.fehler import BauFehler
from swki.compiler.protokoll import Protokoll
from swki.konfig import lade_standard
from tests.baugruppe.beispiel_bewegung import schreibe


class _Mass:
    def __init__(self):
        self.gesetzt = []

    def SetSystemValue3(self, wert, konfiguration, namen):  # noqa: N802 (SolidWorks-Name)
        self.gesetzt.append((wert, konfiguration, namen))


class _Mate:
    def __init__(self):
        self.Name = "Mate1"
        self.GetSpecificFeature2 = SimpleNamespace(Alignment=0)
        self.masse: dict[str, _Mass] = {}

    def Parameter(self, name):  # noqa: N802 (SolidWorks-Name)
        return self.masse.setdefault(name, _Mass())


class _Asm:
    def __init__(self):
        self.mates: list[_Mate] = []
        self.aufrufe: list[tuple] = []
        self.gleichungen: list[str] = []
        self.GetEquationMgr = SimpleNamespace(Add2=lambda index, text, loesen: self.gleichungen.append(text) or 0)

    def AddMate5(self, *args):  # noqa: N802 (SolidWorks-Name)
        self.aufrufe.append(args[:-1])
        args[-1].value = 1  # ErrorStatus
        mate = _Mate()
        self.mates.append(mate)
        return mate


@pytest.fixture
def asm(monkeypatch):
    a = _Asm()
    monkeypatch.setattr(sw_baugruppe, "verknuepfungen", lambda _asm: list(a.mates))
    monkeypatch.setattr(sw_baugruppe, "waehle", lambda *args: None)
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda feature: 0)
    monkeypatch.setattr(sw_baugruppe.sw, "auswahl_leeren", lambda model: None)
    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", lambda model: None)
    return a


def _grenze(vid="g1", typ="grenze_abstand", oben="=HUB"):
    return Verknuepfung(vid, vid, typ, {}, {}, "gleich", None, False, 0, oben)


def _bindung(vid, parameter):
    name = sw_baugruppe.GRENZ_MASSE.get("max")
    return [f'"{name}@{vid}" = "{parameter}"'] if name else []


def test_grenze_abstand_an_addmate5(asm):
    gesetzt: dict[str, int] = {}
    sw_baugruppe.verknuepfe(asm, _grenze(), None, None, {"HUB": 100}, gesetzt)
    assert asm.aufrufe == [(5, 0, False, 0.0, pytest.approx(0.1), 0.0, 1, 1, 0.0, 0.0, 0.0, False, False, 0)]
    assert asm.gleichungen == _bindung("g1", "HUB") and gesetzt == {"g1": 0}


def test_grenze_winkel_an_addmate5(asm):
    sw_baugruppe.verknuepfe(asm, _grenze("g2", "grenze_winkel", "=SCHWENK"), None, None, {"SCHWENK": 90}, {})
    assert asm.aufrufe == [(6, 0, False, 0.0, 0.0, 0.0, 1, 1, 0.0, pytest.approx(math.pi / 2), 0.0, False, False, 0)]
    assert asm.gleichungen == _bindung("g2", "SCHWENK")


def test_treibe_legt_eine_abstandsverknuepfung_an(asm):
    feature = sw_baugruppe.treibe(asm, _grenze(), None, None, 25.0)
    assert feature.Name == "g1.antrieb" and asm.gleichungen == []
    assert asm.aufrufe == [(5, 0, False, pytest.approx(0.025), pytest.approx(0.025), pytest.approx(0.025), 1, 1, 0.0,
                            0.0, 0.0, False, False, 0)]


def test_stelle(asm, monkeypatch):
    feature = sw_baugruppe.treibe(asm, _grenze("g2", "grenze_winkel", "=SCHWENK"), None, None, 0.0)
    assert sw_baugruppe.stelle(asm, feature, "winkel", 45.0) is None
    assert feature.masse["D1"].gesetzt == [(pytest.approx(math.pi / 4), 1, None)]

    def kaputt(model):
        raise BauFehler("REBUILD_FEHLER", "g2: Code 5", schritt="rebuild")

    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", kaputt)
    assert "g2: Code 5" in sw_baugruppe.stelle(asm, feature, "winkel", 100.0)
    monkeypatch.setattr(sw_baugruppe.sw, "rebuild", lambda model: None)
    monkeypatch.setattr(sw_baugruppe, "fehlercode", lambda f: 7 if f is feature else 0)
    assert sw_baugruppe.stelle(asm, feature, "winkel", 100.0) == "Verknüpfungsfehler: g2.antrieb"


class _Mech:
    """Attrappe von SwMechanik für bau._grundstellung; fehler_name: dort scheitert halte()."""
    letzte = None
    fehler_name: str | None = None

    def __init__(self, *args):
        self.args = args
        self.aufrufe: list[tuple] = []
        _Mech.letzte = self

    def halte(self, b, wert):
        self.aufrufe.append(("halte", b.name, wert))
        if b.name == _Mech.fehler_name:
            raise StellungFehler(b.name, wert, "Verknüpfungsfehler: g2.antrieb")

    def loese(self, b):
        self.aufrufe.append(("loese", b.name))


def _baulauf(tmp_path):
    bg = lade_baugruppe(schreibe(tmp_path / "A"))
    b = bau.Baulauf(None, bg, "A", tmp_path, lade_standard(), Protokoll("A", "bewegungsprobe.yaml", 1, 2025),
                    asm=object())
    return b, verknuepfungen(bg.spec, bg.quellen)


def test_grundstellung_haelt_alle_und_loest_rueckwaerts(tmp_path, monkeypatch):
    _Mech.fehler_name = None
    monkeypatch.setattr(bau, "SwMechanik", _Mech)
    b, alle = _baulauf(tmp_path)
    assert bau._grundstellung(b, alle) is None
    assert _Mech.letzte.aufrufe == [("halte", "Hub", 0.0), ("halte", "Schwenk", 0.0), ("loese", "Schwenk"),
                                    ("loese", "Hub")]
    assert set(_Mech.letzte.args[2]) == {"g1", "g2"}
    assert [(k.id, k.typ, k.status) for k in b.protokoll.knoten] == [
        ("grundstellung:Hub", "grundstellung", "ok"), ("grundstellung:Schwenk", "grundstellung", "ok")]


def test_grundstellung_fehler(tmp_path, monkeypatch):
    _Mech.fehler_name = "Schwenk"
    monkeypatch.setattr(bau, "SwMechanik", _Mech)
    b, alle = _baulauf(tmp_path)
    fehler = bau._grundstellung(b, alle)
    assert fehler.code == "GRUNDSTELLUNG_FEHLER" and "Grundstellung Schwenk" in str(fehler)
    assert _Mech.letzte.aufrufe[-2:] == [("loese", "Schwenk"), ("loese", "Hub")]
    assert [k.status for k in b.protokoll.knoten] == ["ok", "fehler"]
```

- [ ] **Step 3: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/test_speicher.py tests/baugruppe/test_sw_bewegung.py -q`
Expected: FAIL – `ModuleNotFoundError: No module named 'swki.speicher'`, `KeyError: 'grenze_abstand'` (MATE_TYP), `AttributeError: module 'swki.baugruppe.sw_baugruppe' has no attribute 'treibe'`, `AttributeError: … bau … 'SwMechanik'`.

- [ ] **Step 4: `swki/speicher.py` (neu)**

```python
"""Private Bytes eines Prozesses (Windows, ctypes): SolidWorks-Speicher für die Speichergrenze der Bewegungsprüfung
(Spec 4a §8.4). Gemessen wird PrivateUsage aus PROCESS_MEMORY_COUNTERS_EX, nicht das Working Set."""

import ctypes
from ctypes import wintypes

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class _Speicher(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]


def privat_mb(pid: int) -> float:
    """Private Bytes des Prozesses pid in MB."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    k32.K32GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(_Speicher), wintypes.DWORD)
    k32.K32GetProcessMemoryInfo.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    h = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        z = _Speicher()
        z.cb = ctypes.sizeof(z)
        if not k32.K32GetProcessMemoryInfo(h, ctypes.byref(z), z.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return round(z.PrivateUsage / 2 ** 20, 1)
    finally:
        k32.CloseHandle(h)
```

- [ ] **Step 5: `swki/pruefung/bilder.py` – `iso_bild` am Dateiende**

```python
def iso_bild(app, model, pfad: Path) -> str:
    """Ein Iso-Bild der aktuellen Stellung (Bewegungsprüfung, Spec 4a §8.3); gleiche Einstellungen wie screenshots()."""
    model._FlagAsMethod("ViewZoomtofit2")
    with sw.einstellung_int(app, SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0):
        model.ShowNamedView2("", ANSICHTEN["iso"])
        model.ViewZoomtofit2()
        sw.speichere(model, pfad, kopie=True)
    return str(pfad)
```

- [ ] **Step 6: `swki/baugruppe/sw_baugruppe.py`**

Importe ergänzen: `from dataclasses import replace` und in der Zeile `from swki.baugruppe.fehler import …` nichts ändern; zusätzlich `from swki.baugruppe.aufloesen import GRENZEN`.

`MATE_TYP` ersetzen und Konstanten ergänzen (nach `MASS_NAME`):

```python
MATE_TYP = {"deckungsgleich": 0, "konzentrisch": 1, "senkrecht": 2, "parallel": 3, "abstand": 5, "winkel": 6,
            "grenze_abstand": 5, "grenze_winkel": 6}  # swMateType_e; Grenze = Abstand/Winkel mit Grenzen (Spike S13 Zeile 1)
GRENZ_MASSE = {"max": "D2", "min": "D3"}  # Maße der Grenzwerte einer Grenzverknüpfung (Spike S13 Zeile 2)
ANTRIEB = ".antrieb"  # Endung der vorübergehenden treibenden Verknüpfung (Spec 4a §7, §8.2)
SW_WERT_DIESE_KONFIGURATION = 1  # swSetValueInConfiguration_e.swSetValue_InThisConfiguration
```

Vor `verknuepfe()` einfügen:

```python
def grenzen(v, parameter: dict) -> dict[str, tuple[float, str | None]]:
    """min/max einer Grenzverknüpfung: (Wert in mm bzw. Grad, Ausdruck für die Gleichung oder None)."""
    return {s: (auswerten(getattr(v, s), parameter), getattr(v, s) if ist_ausdruck(getattr(v, s)) else None)
            for s in ("min", "max")}


def _mate_werte(v, parameter: dict) -> tuple[float, float, float, float, float, float]:
    """(Abstand, Abstand oben, Abstand unten, Winkel, Winkel oben, Winkel unten) für AddMate5 in m bzw. rad. Eine
    Grenzverknüpfung wird mit dem Wert min und den Grenzen min/max angelegt (Präzisierung 2)."""
    if v.typ in GRENZEN:
        g = grenzen(v, parameter)
        unten, oben = g["min"][0], g["max"][0]
        if v.typ == "grenze_abstand":
            return mm(unten), mm(oben), mm(unten), 0.0, 0.0, 0.0
        return 0.0, 0.0, 0.0, grad(unten), grad(oben), grad(unten)
    wert = auswerten(v.wert, parameter) if v.wert is not None else 0.0
    abstand = mm(wert) if v.typ == "abstand" else 0.0
    winkel = grad(wert) if v.typ == "winkel" else 0.0
    return abstand, abstand, abstand, winkel, winkel, winkel


def _gleichungen(v, parameter: dict) -> list[tuple[str, str]]:
    """(Maßname, Ausdruck) der Gleichungen, die den Wert bzw. die Grenzen an die Parameter binden."""
    if v.typ in GRENZEN:
        return [(GRENZ_MASSE[s], a) for s, (_, a) in grenzen(v, parameter).items() if a is not None and s in GRENZ_MASSE]
    return [(MASS_NAME, v.wert)] if ist_ausdruck(v.wert) else []
```

In `verknuepfe()`:
- die drei Zeilen `wert = …`, `abstand = …`, `winkel = …` ersetzen durch
  `d, d_oben, d_unten, w, w_oben, w_unten = _mate_werte(v, parameter)`,
- den `AddMate5`-Aufruf ersetzen durch

```python
    mate = asm.AddMate5(MATE_TYP[v.typ], code, False, d, d_oben, d_unten, 1, 1, w, w_oben, w_unten,
                        False, v.drehung_sperren, 0, status)
```

- den Block `if ist_ausdruck(v.wert): … sw.rebuild(asm)` ersetzen durch

```python
        gleichungen = _gleichungen(v, parameter)
        for name, ausdruck in gleichungen:
            if asm.GetEquationMgr.Add2(-1, f'"{name}@{v.id}" = {sw_ausdruck(ausdruck)}', True) < 0:
                raise BauFehler(GLEICHUNG_FEHLER, f"Gleichung für {v.id} = {ausdruck} abgelehnt", schritt="gleichung")
        if gleichungen:
            sw.rebuild(asm)
```

- im Docstring den ersten Satz ergänzen: „Grenzverknüpfungen mit min/max und Gleichungen auf die Grenzwerte (Spec 4a §4.1).“

Nach `verknuepfungswerte()` am Dateiende ergänzen:

```python
def treibe(asm, v, a: tuple[object, bool], b: tuple[object, bool], wert: float):
    """Vorübergehende treibende Verknüpfung zur Grenzverknüpfung v: Abstand bzw. Winkel an denselben Flächen mit
    gleicher Ausrichtung, Name <id>.antrieb, Wert in mm bzw. Grad (Spec 4a §7, §8.2)."""
    antrieb = replace(v, id=f"{v.id}{ANTRIEB}", typ="abstand" if v.typ == "grenze_abstand" else "winkel", wert=wert,
                      min=None, max=None, drehung_sperren=False)
    return verknuepfe(asm, antrieb, a, b, {}, None)


def stelle(asm, antrieb, art: str, wert: float) -> str | None:
    """Treibende Verknüpfung auf wert stellen und neu aufbauen; None = gelöst, sonst die Meldung (Rebuild-Fehler oder
    Fehlercode einer Verknüpfung). Ob die Komponente dort steht, prüft der Aufrufer über die Lage (Präzisierung 4)."""
    antrieb.Parameter(MASS_NAME).SetSystemValue3(mm(wert) if art == "abstand" else grad(wert),
                                                 SW_WERT_DIESE_KONFIGURATION, None)
    try:
        sw.rebuild(asm)
    except BauFehler as e:
        return str(e)
    fehlerhaft = [f.Name for f in verknuepfungen(asm) if fehlercode(f)]
    return f"Verknüpfungsfehler: {', '.join(fehlerhaft)}" if fehlerhaft else None


def loesche(asm, feature) -> None:
    """Verknüpfung löschen (die treibende nach Bau bzw. Prüfung) und neu aufbauen."""
    _loesche(asm, feature)
    sw.rebuild(asm)


def kiste(komp) -> list[float]:
    """Hüllquader der Komponente in Baugruppenkoordinaten (mm; Spike S13 Zeile 6)."""
    return [in_mm(x) for x in komp.GetBox(False, False)]
```

- [ ] **Step 7: `swki/baugruppe/sw_bewegung.py` (neu)**

```python
"""SolidWorks-Mechanik der Bewegungsprüfung (Spec 4a §8.2): treibende Verknüpfungen anlegen, stellen und löschen, Lage,
Hüllquader und Bestimmtheit der Komponenten lesen, Kollision, Iso-Bilder, Private Bytes. Erfüllt
swki.baugruppe.bewegungslauf.Mechanik."""

from pathlib import Path

from swki.baugruppe import sw_baugruppe
from swki.baugruppe.bewegung import Bewegung
from swki.baugruppe.bewegungslauf import StellungFehler
from swki.pruefung.bilder import iso_bild
from swki.speicher import privat_mb


class SwMechanik:
    def __init__(self, app, asm, grenzen: dict, entitaet, komponenten: dict, bilder: Path | None = None):
        self.app, self.asm = app, asm
        self.grenzen = grenzen              # Verknüpfungs-ID → Verknuepfung (Grenzverknüpfungen)
        self.entitaet = entitaet            # Referenz der Spec → Entität im Baugruppenkontext
        self.komponenten = komponenten      # Instanz-ID → IComponent2
        self.bilder = bilder
        self.antriebe: dict[str, object] = {}  # Bewegung → treibende Verknüpfung
        self._namen = {k.Name2: iid for iid, k in komponenten.items()}

    def halte(self, b: Bewegung, wert: float) -> None:
        if b.name not in self.antriebe:
            v = self.grenzen[b.grenze]
            self.antriebe[b.name] = sw_baugruppe.treibe(self.asm, v, self.entitaet(v.a), self.entitaet(v.b), wert)
        if (meldung := self.stelle(b, wert)) is not None:
            raise StellungFehler(b.name, wert, meldung)

    def stelle(self, b: Bewegung, wert: float) -> str | None:
        return sw_baugruppe.stelle(self.asm, self.antriebe[b.name], b.art, wert)

    def loese(self, b: Bewegung) -> None:
        if (antrieb := self.antriebe.pop(b.name, None)) is not None:
            sw_baugruppe.loesche(self.asm, antrieb)

    def status(self) -> dict[str, int]:
        return {iid: sw_baugruppe.status(k) for iid, k in self.komponenten.items()}

    def zustand(self) -> dict[str, tuple[list[float], list[float]]]:
        return {iid: (sw_baugruppe.transform(k), sw_baugruppe.kiste(k)) for iid, k in self.komponenten.items()}

    def interferenzen(self) -> list[dict]:
        return [{"paar": sorted(self._namen.get(n, n) for n in paar), "volumen": round(volumen, 3)}
                for paar, volumen in sw_baugruppe.interferenzen(self.asm)]

    def bild(self, name: str) -> str:
        return "" if self.bilder is None else iso_bild(self.app, self.asm, self.bilder / f"{name}.png")

    def speicher_mb(self) -> float:
        return privat_mb(int(self.app.GetProcessID))
```

- [ ] **Step 8: `swki/baugruppe/bau.py` – Grundstellung**

Importe ergänzen:

```python
from swki.baugruppe.aufloesen import GRENZEN, Instanz, Verknuepfung, basis, instanzen, verknuepfungen
from swki.baugruppe.bewegung import bewegungen
from swki.baugruppe.fehler import GRUNDSTELLUNG_FEHLER, KOMPONENTE_FEHLER, SCHLIESSEN_FEHLER, TEIL_BAU, VERKNUEPFUNG_FEHLER
from swki.baugruppe.sw_bewegung import SwMechanik
```

(die bisherigen Zeilen `from swki.baugruppe.aufloesen import …` und `from swki.baugruppe.fehler import …` ersetzen.)

Nach `_verknuepfe()` einfügen:

```python
def _grundstellung(b: Baulauf, alle: list[Verknuepfung]) -> Exception | None:
    """Jede bewegte Komponente über eine treibende Verknüpfung auf min stellen, dann alle treibenden wieder löschen
    (Spec 4a §7.2): gespeichert wird in Grundstellung. Eine treibende Verknüpfung, die sich nicht löschen lässt, ist ein
    Fehler – sie darf nicht in der gespeicherten Baugruppe bleiben."""
    bws = bewegungen(b.bg.spec, b.standard)
    mech = SwMechanik(b.app, b.asm, {v.id: v for v in alle if v.typ in GRENZEN}, lambda seite: _entitaet(b, seite),
                      b.komponenten)
    fehler = None
    try:
        for bw in bws:
            with b.protokoll.knoten_lauf(f"grundstellung:{bw.name}", "grundstellung"):
                try:
                    mech.halte(bw, bw.min)
                except Exception as e:
                    raise _mit_kontext(e, GRUNDSTELLUNG_FEHLER, f"Grundstellung {bw.name}", "grundstellung") from e
    except Exception as e:
        fehler = e
    for bw in reversed(bws):
        try:
            mech.loese(bw)
        except Exception as e:
            fehler = fehler or _mit_kontext(e, GRUNDSTELLUNG_FEHLER, f"Antrieb {bw.name} löschen", "grundstellung")
    return fehler
```

In `bauen()` direkt nach dem Block `with protokoll.phase("verknuepfen"): …` (gleiche Einrückung) einfügen:

```python
        if fehler is None and b.asm is not None and bg.spec.get("bewegungen"):
            with protokoll.phase("grundstellung"):
                fehler = _grundstellung(b, alle_verknuepfungen)
```

- [ ] **Step 9: Unit-Tests und Code-Prüfung**

Run: `.venv\Scripts\python.exe -m pytest tests/test_speicher.py tests/baugruppe/test_sw_bewegung.py -q` → 7 passed.
Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe -q` → alle grün (die `verknuepfe`-Tests aus 3b unverändert).
Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.
Run: `.venv\Scripts\python.exe -m pytest -q` → **688 passed, 109 deselected** (681 + 7).

- [ ] **Step 10: Live-Test – `tests/live/test_live_bewegung.py` (neu)**

```python
"""Live: Bewegungsprobe (Spec 4a) – bauen in Grundstellung, prüfen mit Bewegungen, Bilder, Dateien unverändert."""

import json
import pathlib
import shutil

import pytest

from swki.aenderungen import abweichungen
from swki.cli import main
from swki.konfig import lade_rechner
from tests.baugruppe.beispiel_bewegung import schreibe

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-BEWEGUNG"


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def auftrag(tmp_path):
    yield tmp_path / AUFTRAG
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _baue(capsys, ordner):
    pfad = schreibe(ordner)
    assert _lauf(capsys, "validieren", str(pfad))[0] == 0
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, bau
    return pfad, bau


def _protokoll(pfad):
    return json.loads((pfad.parent / "protokolle" / "bewegungsprobe.lauf-1.protokoll.json").read_text(encoding="utf-8"))


def test_bewegungsprobe_baut_in_grundstellung(capsys, auftrag):
    pfad, bau = _baue(capsys, auftrag)
    assert [k["id"] for k in bau["knoten"]] == ["platte", "schieber", "bolzen", "hebel", "v1", "v2", "g1", "v3", "v4",
                                                "s1", "s1.anlage", "g2", "grundstellung:Hub", "grundstellung:Schwenk"]
    assert all(k["status"] == "ok" for k in bau["knoten"]), bau["knoten"]
    assert "grundstellung" in _protokoll(pfad)["phasen"]
```

Run (einzeln, Vorbedingungen und Speicher wie in den Global Constraints): `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_bewegung.py::test_bewegungsprobe_baut_in_grundstellung --zeit 600` → OK. Danach `.venv\Scripts\python.exe -m pytest -q` → **688 passed, 110 deselected**.

Scheitert der Live-Test an einer Verknüpfung oder der Grundstellung: Fehlercode und Meldung aus dem Protokoll in den Bericht, anhalten (NEEDS_CONTEXT) – der Controller gleicht mit der Spike-Tabelle ab.

- [ ] **Step 11: Commit**

```powershell
git add swki/speicher.py swki/pruefung/bilder.py swki/baugruppe/sw_baugruppe.py swki/baugruppe/sw_bewegung.py swki/baugruppe/bau.py tests/test_speicher.py tests/baugruppe/test_sw_bewegung.py tests/live/test_live_bewegung.py
git commit -m "baugruppe: Grenzverknüpfung und Scharnier bauen, treibende Verknüpfung, Grundstellung vor dem Speichern" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Im Bericht: Live-Ergebnis, Private Bytes vorher → nachher.

---

### Task 7: Bewegungsprüfung in `swki pruefen`, Bestimmtheit, Bericht (live)

**Files:**
- Modify: `swki/baugruppe/pruefen.py` (Funktion `pruefen` ersetzen; neue Helfer)
- Modify: `swki/baugruppe/bewertung.py` (`_erlaubt_unterbestimmt`)
- Modify: `swki/pruefung/bericht.py` (Abschnitt Bewegungen)
- Modify: `tests/baugruppe/test_pruefen_baugruppe.py` (3 Tests), `tests/live/test_live_bewegung.py` (1 Test)

**Interfaces:**
- Consumes: `bewegungen`, `bewerte_bewegungen`, `ergaenze_bericht` (Task 4); `fahre` (Task 5); `SwMechanik` (Task 6); `GRENZEN`, `verknuepfungen` (Task 2); `loese_im_teil`, `sw_baugruppe.in_baugruppe`.
- Produces: Prüfbericht mit `bewegungen` (`{"laeufe": [...], "paare": [...]}`), Bewegungsprüfungen und -mängeln, Bewegungsbildern unter `bilder`; `swki pruefen` endet bei `SPEICHER_KNAPP` mit Exit 1 ohne Prüfbericht; `bericht.md` mit Abschnitt „Bewegungen (letzter Lauf)“.

- [ ] **Step 1: Failing tests – an `tests/baugruppe/test_pruefen_baugruppe.py` anhängen**

```python
def test_freiheitsgrad_1_erlaubt_unterbestimmt():
    from swki.baugruppe.bewertung import _erlaubt_unterbestimmt

    spec = {"komponenten": [{"id": "schieber"}, {"id": "hebel"}], "freiheitsgrade": {"schieber": 1}}
    assert _erlaubt_unterbestimmt(spec, "schieber") and not _erlaubt_unterbestimmt(spec, "hebel")


def test_dokumente_der_grenzen_bleiben_offen(tmp_path):
    from swki.baugruppe import pruefen as pruefen_modul
    from swki.baugruppe.laden import lade_baugruppe
    from tests.baugruppe.beispiel_bewegung import schreibe as schreibe_bewegung

    bg = lade_baugruppe(schreibe_bewegung(tmp_path / "B"))
    assert pruefen_modul._dokumente_der_grenzen(bg) == {"schieber.yaml", "grundplatte.yaml", "hebel.yaml"}


def test_bericht_bewegungen():
    laeufe = [{"bewegung": "Hub", "gegen": {}, "stellungen": 17, "bewegt": ["schlitten", "hebel"], "kollisionen": 0,
               "grenze": {"oben": False, "unten": None}, "dauer_s": 12.5},
              {"bewegung": "Hub", "gegen": {"Schwenk": "max"}, "stellungen": 17, "bewegt": [], "kollisionen": 1,
               "grenze": {}, "dauer_s": 9.0}]
    bericht = {"maengel": [], "bilder": {},
               "bewegungen": {"laeufe": laeufe, "paare": [{"bewegungen": ["Hub", "Schwenk"], "schnitt": [0] * 6}]}}
    text = bericht_markdown(BAUGRUPPE, "A", [], ("pruefen", "…"), bericht, None, None, [])
    for teil in ("## Bewegungen (letzter Lauf)", "| Hub | Grundstellung | 17 | schlitten, hebel | 0 | wirkt / – | 12.5 |",
                 "| Hub | Schwenk auf max | 17 | – | 1 | – / – | 9.0 |", "Paarläufe für: Hub × Schwenk"):
        assert teil in text, text
```

(`bericht_markdown` und `BAUGRUPPE` sind in der Datei schon importiert.)

- [ ] **Step 2: Tests fehlschlagen lassen**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_pruefen_baugruppe.py -q -k "freiheitsgrad_1 or dokumente_der_grenzen or bericht_bewegungen"`
Expected: 3 FAIL (`_erlaubt_unterbestimmt` lehnt 1 ab; `_dokumente_der_grenzen` fehlt; Abschnitt fehlt).

- [ ] **Step 3: `swki/baugruppe/bewertung.py`**

In `_erlaubt_unterbestimmt` die Rückgabe ersetzen:

```python
    return any(fg.get(s) in ("unterbestimmt", 1) for s in (instanz_id, k, gruppe) if s)  # 1: Spec 4a §8.1
```

- [ ] **Step 4: `swki/pruefung/bericht.py` – Abschnitt Bewegungen**

Nach `_zelle()` einfügen:

```python
def _grenze_text(wert) -> str:
    return {True: "geht durch", False: "wirkt", None: "–"}[wert]
```

In `bericht_markdown()` direkt vor `zeilen += ["", "## Screenshots (letzter Lauf)", ""]` einfügen:

```python
    bewegungen = letzter.get("bewegungen")
    if bewegungen:
        zeilen += ["", "## Bewegungen (letzter Lauf)", "",
                   "| Bewegung | Lauf | Stellungen | bewegt | Kollisionen | Grenze oben / unten | Dauer (s) |",
                   "|---|---|---|---|---|---|---|"]
        for lauf in bewegungen["laeufe"]:
            gegen = ", ".join(f"{n} auf {s}" for n, s in lauf["gegen"].items()) or "Grundstellung"
            grenze = " / ".join(_grenze_text(lauf["grenze"].get(s)) for s in ("oben", "unten"))
            zeilen.append(f"| {lauf['bewegung']} | {gegen} | {lauf['stellungen']} | {', '.join(lauf['bewegt']) or '–'} | "
                          f"{lauf['kollisionen']} | {grenze} | {lauf['dauer_s']} |")
        if bewegungen.get("paare"):
            zeilen += ["", "Paarläufe für: " + "; ".join(" × ".join(p["bewegungen"]) for p in bewegungen["paare"])]
```

- [ ] **Step 5: `swki/baugruppe/pruefen.py`**

Importe ergänzen bzw. ersetzen:

```python
from swki.baugruppe.aufloesen import GRENZEN, basis, instanzen, verknuepfungen
from swki.baugruppe.bewegung import bewegungen, bewerte_bewegungen, ergaenze_bericht
from swki.baugruppe.bewegungslauf import fahre
from swki.baugruppe.referenzen import loese_im_teil
from swki.baugruppe.sw_bewegung import SwMechanik
```

(die Zeile `from swki.baugruppe.aufloesen import basis, instanzen` ersetzen.)

Vor `pruefen()` einfügen:

```python
def _grenzen(bg: Baugruppe) -> dict:
    return {v.id: v for v in verknuepfungen(bg.spec, bg.quellen) if v.typ in GRENZEN}


def _dokumente_der_grenzen(bg: Baugruppe) -> set[str]:
    """Quelldokumente, deren Flächen die Grenzverknüpfungen nennen: sie bleiben für die treibenden Verknüpfungen offen."""
    return {bg.quellen[basis(seite["komponente"])].schluessel_dokument
            for v in _grenzen(bg).values() for seite in (v.a, v.b)}


def _komponenten(asm, protokoll: dict) -> dict:
    """Instanz-ID → IComponent2 der geöffneten Baugruppe (SolidWorks-Namen aus dem Bauprotokoll)."""
    namen = {k["sw_name"]: k["id"] for k in protokoll.get("komponenten", [])}
    return {namen.get(k.Name2, k.Name2): k for k in sw_baugruppe.komponenten(asm)}


def _pruefe_bewegungen(app, asm, bg: Baugruppe, protokoll: dict, kontexte: dict, messwerte, standard: dict,
                       ordner: Path) -> tuple[list[dict], dict, dict]:
    """Bewegungsprüfung am geöffneten Lauf-Dokument (Spec 4a §8.2); liefert Prüfungen, Bewegungsbericht und Bilder.
    Die treibenden Verknüpfungen verschwinden wieder; der Aufrufer schließt ohne Speichern."""
    komponenten = _komponenten(asm, protokoll)

    def entitaet(seite: dict):
        ctx = kontexte[bg.quellen[basis(seite["komponente"])].schluessel_dokument]
        ref = loese_im_teil(ctx, {k: v for k, v in seite.items() if k != "komponente"})
        return sw_baugruppe.in_baugruppe(komponenten[seite["komponente"]], ref)

    bws = bewegungen(bg.spec, standard)
    tol = standard["toleranzen"]["anker_mm"]
    mech = SwMechanik(app, asm, _grenzen(bg), entitaet, komponenten, ordner / "bilder")
    m = fahre(mech, bws, {frozenset(i["paar"]) for i in messwerte.interferenzen}, standard["speicher_grenze_mb"], tol)
    pruefungen, bericht = bewerte_bewegungen(bg.spec, bws, m, messwerte.komponenten, tol)
    bilder = {Path(p).stem: p for lauf in m.laeufe
              for p in [*lauf.bilder.values(), *(k["bild"] for k in lauf.kollisionen)] if p}
    return pruefungen, bericht, bilder
```

`pruefen()` ab der Zeile `soll_teile = freigegebene_teile(bg)` bis zum Ende ersetzen durch:

```python
    soll_teile = freigegebene_teile(bg)
    bedarf = teil_messpunkte(bg)
    mit_bewegung = bool(bg.spec.get("bewegungen"))
    offen_halten = _dokumente_der_grenzen(bg) if mit_bewegung else set()
    app = verbinde(r.sw_jahr)
    teilberichte, geometrie, kontexte, offen = {}, {}, {}, []
    bewegung = None
    try:
        for datei, teil_spec in bg.teile.items():
            model = oeffne(app, ordner / dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard))
            behalten = False
            try:
                ctx = kontext_aus_datei(app, model, teil_spec, bg.pfad.parent / datei, tol, protokoll["teile"][datei])
                teilberichte[datei] = bewerte(teil_spec, messe(ctx, soll_teile[datei]), standard, soll_teile[datei])
                geometrie[datei] = _geometrie(ctx, bedarf.get(datei, []))
                if datei in offen_halten:
                    kontexte[datei], behalten = ctx, True
                    offen.append(model)
            finally:
                if not behalten:
                    sw.schliesse(app, model)
        for q in {q.schluessel: q for q in bg.quellen.values() if q.art == "normteil"}.values():
            if q.schluessel not in bedarf and q.schluessel not in offen_halten:
                continue
            pfad = ordner / dokument_name(q, auftrag, standard)
            model = oeffne(app, pfad)
            behalten = False
            try:
                ctx = kontext_aus_datei(app, model, q.spec, pfad.with_suffix(".yaml"), tol, {"knoten": []})
                geometrie[q.schluessel] = _geometrie(ctx, bedarf.get(q.schluessel, []))
                if q.schluessel in offen_halten:
                    kontexte[q.schluessel], behalten = ctx, True
                    offen.append(model)
            finally:
                if not behalten:
                    sw.schliesse(app, model)
        asm = oeffne(app, asm_pfad)
        try:
            sw_baugruppe.aufloesen(asm)
            messwerte = _messe_baugruppe(asm, bg, protokoll, geometrie, teilberichte)
            bilder = screenshots(app, asm, ordner / "bilder")
            if mit_bewegung:
                bewegung = _pruefe_bewegungen(app, asm, bg, protokoll, kontexte, messwerte, standard, ordner)
        finally:
            sw.schliesse(app, asm)  # ohne Speichern: keine treibende Verknüpfung bleibt in der Datei (Spec 4a §8)
    finally:
        for model in reversed(offen):
            sw.schliesse(app, model)
    bericht = {
        "auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(asm_pfad), "art": "baugruppe",
        **bewerte_baugruppe(bg.spec, bg.quellen, messwerte, standard,
                            stueckliste_soll(bg.spec, freigegebene_quellen(bg), auftrag, standard)),
        "normteile": protokoll.get("normteile", {}), "bilder": bilder,
    }
    if bewegung is not None:
        bericht = ergaenze_bericht(bericht, *bewegung)
    schreibe_pruefbericht(spec_pfad, lauf, ordner, bericht)
    return bericht
```

- [ ] **Step 6: Unit-Tests**

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe tests/pruefung -q` → alle grün.
Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.
Run: `.venv\Scripts\python.exe -m pytest -q` → **691 passed, 110 deselected** (688 + 3).

- [ ] **Step 7: Live-Test – an `tests/live/test_live_bewegung.py` anhängen**

```python
def test_bewegungsprobe_besteht_pruefung(capsys, auftrag):
    pfad, bau = _baue(capsys, auftrag)
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    assert code == 0, bericht
    assert bericht["maengel"] == [], json.dumps(bericht["pruefungen"], indent=1, ensure_ascii=False)
    assert [(x["bewegung"], x["gegen"]) for x in bericht["bewegungen"]["laeufe"]] == [
        ("Hub", {}), ("Schwenk", {}), ("Hub", {"Schwenk": "max"}), ("Schwenk", {"Hub": "max"})]
    assert {p["id"] for p in bericht["pruefungen"]} >= {
        "freiheitsgrad:schieber", "freiheitsgrad:hebel", "grenze:Hub", "grenze:Schwenk", "endlage:Hub:schieber",
        "endlage:Hub:hebel", "endlage:Schwenk:hebel", "bewegung_kollision:Hub", "bewegung_kollision:Schwenk"}
    for name in ("Hub-min", "Hub-mitte", "Hub-max", "Schwenk-min", "Schwenk-mitte", "Schwenk-max"):
        assert pathlib.Path(bericht["bilder"][name]).stat().st_size > 0
    assert abweichungen(pathlib.Path(bau["ordner"]), _protokoll(pfad)["sha256"]) == {"geaendert": [], "fehlend": []}
```

Run (einzeln, frisches SolidWorks; vorher bei ≥ 3 GB BLOCKED Speicher): `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_bewegung.py::test_bewegungsprobe_besteht_pruefung --zeit 600` → OK. Danach `.venv\Scripts\python.exe -m pytest -q` → **691 passed, 111 deselected**.

Meldet der Prüfbericht einen Mangel: nicht die Erwartung ändern, sondern anhalten (NEEDS_CONTEXT) mit Auszug aus `pruefungen` (betroffene IDs, `ist`, `soll`, `hinweis`) und dem Abschnitt `bewegungen` – der Controller gleicht mit den Spike-Zeilen 3, 4, 7 ab.

- [ ] **Step 8: Commit**

```powershell
git add swki/baugruppe/pruefen.py swki/baugruppe/bewertung.py swki/pruefung/bericht.py tests/baugruppe/test_pruefen_baugruppe.py tests/live/test_live_bewegung.py
git commit -m "pruefen: Bewegungsprüfung nach der Statik, freiheitsgrade 1, Abschnitt Bewegungen im Bericht" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Im Bericht: Live-Ergebnis mit Dauer je Lauf (`bewegungen.laeufe[].dauer_s`), Private Bytes vorher → nachher.

---

### Task 8: Referenz Linearschlitten mit Prüfer-Urteil (live)

**Files:**
- Create: `tests/referenz/schlitten/linearschlitten.yaml`, `grundplatte.yaml`, `leiste.yaml`, `schlitten.yaml`, `hebel.yaml`, `eingabe/beschreibung.md`
- Modify: `tests/referenz/test_referenzen.py` (Eintrag Schlitten)
- Create: `tests/baugruppe/test_schlitten_spec.py`

**Interfaces:**
- Consumes: alle vorherigen Tasks; Normteile ISO 4762 M8 × 25 und ISO 8734 8 × 30.
- Produces: die Referenzbaugruppe des Fertig-Kriteriums (Spec 4a §14); Basis der Negativfälle (Task 9).

Geometrie (Baugruppenkoordinaten, mm): Grundplatte 300 × 100 × 20 (x −150…150, y 0…20, z −50…50, fixiert) mit 4 × Gewinde M8 (Tiefe 16, Gewindetiefe 12) bei x = ±100, z = ±40. Führungsleisten 300 × 20 × 25 bündig an den Enden und Außenseiten (links z −50…−30, rechts z 30…50, y 20…45), je 2 × ISO 4762 M8 × 25 in Senkungen (Senkungsgrund y = 36,4, Einschraublänge 8,6). Schlitten 80 × 60 × 25 auf der Grundplatte, seitlich an der linken Leiste (z −30…30), Grenze `g1` zwischen den Flächen −x von Schlitten und Grundplatte, 0…`HUB` = 220 (Grundstellung x −150…−70, Endlage x 70…150). Drehbolzen ISO 8734 8 × 30 in einer Stiftbohrung des Schlittens bei Schlitten-x −20 (Grundstellung x = −130), bündig mit der Schlitten-Unterseite (y 20…50). Hebel 60 × 16 × 10 auf dem Schlitten (y 45…55), Bohrung Ø 8,5 bei Hebel-x −22 um den Bolzen (Scharnier), Grenze `g2` zwischen den Flächen +z von Hebel und Schlitten, 0…`SCHWENK` = 90; in Grundstellung zeigt der Hebel nach +x (x −138…−78), geschwenkt nach −z über die linke Leiste (Spike-Zeile 7). Hülle in Grundstellung 300 × 55 × 100.

- [ ] **Step 1: `tests/referenz/schlitten/grundplatte.yaml`**

```yaml
# Referenz Linearschlitten (Spec 4a): Grundplatte, fixiert. Ursprung Mitte Unterseite, Oberseite y = H.
# Gewinde M8 für die Führungsleisten: zwei je Leiste auf deren Mittellinie (z = ±ZL).
art: teil
name: Grundplatte
material: "1.0038"
eigenschaften: {Benennung: Grundplatte Linearschlitten}
parameter: {L: 300, B: 100, H: 20, AL: 200, ZL: 40, TG: 16, GT: 12}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: normbohrung, art: gewinde, groesse: M8, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=-AL/2", "=ZL"], ["=AL/2", "=ZL"], ["=-AL/2", "=-ZL"], ["=AL/2", "=-ZL"]], tiefe: "=TG", gewindetiefe: "=GT"}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: Abstand Gewinde in x, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true}, soll: "=AL"}
```

- [ ] **Step 2: `tests/referenz/schlitten/leiste.yaml`**

```yaml
# Referenz Linearschlitten (Spec 4a): Führungsleiste (zweimal verwendet). Ursprung Mitte Unterseite; Senkungen für
# ISO 4762 M8 auf der Mittellinie.
art: teil
name: Leiste
material: "1.0038"
eigenschaften: {Benennung: Führungsleiste Linearschlitten}
parameter: {L: 300, B: 20, H: 25, AL: 200}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: normbohrung, art: zylinderschraube, groesse: M8, flaeche: {feature: f1, flaeche: "+y"},
     positionen: [["=-AL/2", 0], ["=AL/2", 0]], durch: true}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen: {soll: auto}
  masse_pruefen:
    - {was: Abstand Senkungen, von: {feature: f2, instanz: 1, achse: true}, zu: {feature: f2, instanz: 2, achse: true}, soll: "=AL"}
```

- [ ] **Step 3: `tests/referenz/schlitten/schlitten.yaml`**

```yaml
# Referenz Linearschlitten (Spec 4a): Schlitten zwischen den Leisten; Stiftbohrung für den Drehbolzen des Hebels bei
# x = XB.
art: teil
name: Schlitten
material: "1.0038"
eigenschaften: {Benennung: Schlitten Linearschlitten}
parameter: {L: 80, B: 60, H: 25, XB: -20}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: normbohrung, art: stift, groesse: 8, flaeche: {feature: f1, flaeche: "+y"}, positionen: [["=XB", 0]],
     durch: true}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen: {soll: auto}
```

- [ ] **Step 4: `tests/referenz/schlitten/hebel.yaml`**

```yaml
# Referenz Linearschlitten (Spec 4a): Hebel; Bohrung um den Drehbolzen bei x = XB (Ø DB > 8).
art: teil
name: Hebel
material: "1.0038"
eigenschaften: {Benennung: Hebel Linearschlitten}
parameter: {L: 60, B: 16, H: 10, XB: -22, DB: 8.5}
features:
  - id: f1
    typ: extrusion
    skizze: {ebene: oben, elemente: [{rechteck: {mitte: [0, 0], breite: "=L", hoehe: "=B"}}]}
    ende: {typ: blind, tiefe: "=H"}
  - {id: f2, typ: bohrung, flaeche: {feature: f1, flaeche: "+y"}, positionen: [["=XB", 0]], durchmesser: "=DB", durch: true}
pruefung:
  huellquader: ["=L", "=H", "=B"]
  volumen: {soll: auto}
```

- [ ] **Step 5: `tests/referenz/schlitten/linearschlitten.yaml`**

```yaml
# Referenz Linearschlitten (Spec 4a §2, §14): Grundplatte (fixiert) mit zwei verschraubten Führungsleisten
# (je 2 × ISO 4762 M8 × 25 in Gewinde), Schlitten zwischen den Leisten mit Abstandsgrenze 0 … HUB, Drehbolzen
# ISO 8734 8 × 30 im Schlitten, Hebel auf dem Schlitten (Scharnier um den Bolzen) mit Winkelgrenze 0 … SCHWENK.
# Grundstellung: Schlitten am Ende −x, Hebel entlang +x.
art: baugruppe
name: Linearschlitten
eigenschaften: {Benennung: Linearschlitten}
parameter: {HUB: 220, SCHWENK: 90}
komponenten:
  - {id: grundplatte, quelle: {teil: grundplatte.yaml}, fixiert: true}
  - {id: leiste_links, quelle: {teil: leiste.yaml}}
  - {id: leiste_rechts, quelle: {teil: leiste.yaml}}
  - {id: schraube_links, quelle: {normteil: "ISO 4762 M8x25"}, je_position: {komponente: leiste_links, feature: f2}}
  - {id: schraube_rechts, quelle: {normteil: "ISO 4762 M8x25"}, je_position: {komponente: leiste_rechts, feature: f2}}
  - {id: schlitten, quelle: {teil: schlitten.yaml}}
  - {id: drehbolzen, quelle: {normteil: "ISO 8734 8x30"}}
  - {id: hebel, quelle: {teil: hebel.yaml}}
verknuepfungen:
  # Führungsleisten bündig an den Enden und Außenseiten der Grundplatte
  - {id: v1, typ: deckungsgleich, a: {komponente: leiste_links, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v2, typ: deckungsgleich, a: {komponente: leiste_links, feature: f1, flaeche: "-x"},
     b: {komponente: grundplatte, feature: f1, flaeche: "-x"}, ausrichtung: gleich}
  - {id: v3, typ: deckungsgleich, a: {komponente: leiste_links, feature: f1, flaeche: "-z"},
     b: {komponente: grundplatte, feature: f1, flaeche: "-z"}, ausrichtung: gleich}
  - {id: v4, typ: deckungsgleich, a: {komponente: leiste_rechts, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v5, typ: deckungsgleich, a: {komponente: leiste_rechts, feature: f1, flaeche: "-x"},
     b: {komponente: grundplatte, feature: f1, flaeche: "-x"}, ausrichtung: gleich}
  - {id: v6, typ: deckungsgleich, a: {komponente: leiste_rechts, feature: f1, flaeche: "+z"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+z"}, ausrichtung: gleich}
  # Leistenschrauben: Kopf auf dem Senkungsgrund, in der Senkungsachse
  - {id: v10, typ: deckungsgleich, a: {komponente: schraube_links, referenz: EINBAU_EBENE},
     b: {komponente: leiste_links, feature: f2, instanz: je, flaeche: "+y"}, ausrichtung: gleich}
  - {id: v11, typ: konzentrisch, a: {komponente: schraube_links, referenz: EINBAU_ACHSE},
     b: {komponente: leiste_links, feature: f2, instanz: je, achse: true}}
  - {id: v12, typ: deckungsgleich, a: {komponente: schraube_rechts, referenz: EINBAU_EBENE},
     b: {komponente: leiste_rechts, feature: f2, instanz: je, flaeche: "+y"}, ausrichtung: gleich}
  - {id: v13, typ: konzentrisch, a: {komponente: schraube_rechts, referenz: EINBAU_ACHSE},
     b: {komponente: leiste_rechts, feature: f2, instanz: je, achse: true}}
  # Schlitten: auf der Grundplatte, seitlich an der linken Leiste; Hub über die Grenze g1
  - {id: v20, typ: deckungsgleich, a: {komponente: schlitten, feature: f1, flaeche: "-y"},
     b: {komponente: grundplatte, feature: f1, flaeche: "+y"}, ausrichtung: entgegengesetzt}
  - {id: v21, typ: deckungsgleich, a: {komponente: schlitten, feature: f1, flaeche: "-z"},
     b: {komponente: leiste_links, feature: f1, flaeche: "+z"}, ausrichtung: entgegengesetzt}
  - {id: g1, typ: grenze_abstand, a: {komponente: schlitten, feature: f1, flaeche: "-x"},
     b: {komponente: grundplatte, feature: f1, flaeche: "-x"}, ausrichtung: gleich, min: 0, max: "=HUB"}
  # Drehbolzen im Schlitten, bündig mit der Unterseite
  - {id: v22, typ: deckungsgleich, a: {komponente: drehbolzen, referenz: EINBAU_EBENE_1},
     b: {komponente: schlitten, feature: f1, flaeche: "-y"}, ausrichtung: entgegengesetzt}
  - {id: v23, typ: konzentrisch, a: {komponente: drehbolzen, referenz: EINBAU_ACHSE},
     b: {komponente: schlitten, feature: f2, instanz: 1, achse: true}}
  # Hebel: Scharnier um den Bolzen, liegt auf dem Schlitten; Schwenk über die Grenze g2
  - {id: s1, typ: scharnier, a: {komponente: hebel, feature: f2, instanz: 1, achse: true},
     b: {komponente: drehbolzen, referenz: EINBAU_ACHSE},
     anlage_a: {komponente: hebel, feature: f1, flaeche: "-y"}, anlage_b: {komponente: schlitten, feature: f1, flaeche: "+y"}}
  - {id: g2, typ: grenze_winkel, a: {komponente: hebel, feature: f1, flaeche: "+z"},
     b: {komponente: schlitten, feature: f1, flaeche: "+z"}, ausrichtung: gleich, min: 0, max: "=SCHWENK"}
freiheitsgrade: {schlitten: 1, hebel: 1}
bewegungen:
  - name: Schlittenhub
    grenze: g1
    erwartet:
      endlagen:
        - {komponente: schlitten, verschiebung: ["=HUB", 0, 0]}
        - {komponente: hebel, verschiebung: ["=HUB", 0, 0]}
  - name: Hebelschwenk
    grenze: g2
    erwartet:
      endlagen:
        - {komponente: hebel, drehung: {achse: [0, 1, 0], winkel: "=SCHWENK"}}
pruefung:
  huellquader: [300, 55, 100]
  masse_pruefen:
    - {was: Hebel auf dem Schlitten, von: {komponente: grundplatte, feature: f1, flaeche: "+y"},
       zu: {komponente: hebel, feature: f1, flaeche: "-y"}, soll: 25}
```

Ergibt Spike-Zeile 7 den anderen Drehsinn, gilt die Ledger-Entscheidung (Achse der Endlage `[0, -1, 0]`); die Spec-Datei wird dann vor der ersten Freigabe so geschrieben.

- [ ] **Step 6: `tests/referenz/schlitten/eingabe/beschreibung.md`**

```markdown
# Linearschlitten (Referenz Stufe 4a)

Ein Schlitten läuft zwischen zwei Führungsleisten auf einer Grundplatte 300 × 100 × 20 mm. Die Leisten (300 × 20 × 25)
sind bündig an den Enden und Außenseiten mit je zwei Zylinderschrauben ISO 4762 M8 in Gewinde der Grundplatte
verschraubt. Der Schlitten (80 × 60 × 25) liegt auf der Grundplatte und an der linken Leiste an und fährt über einen
Hub von 220 mm von einem Ende der Grundplatte zum anderen.

Auf dem Schlitten sitzt ein Hebel (60 × 16 × 10), der um einen Zylinderstift ISO 8734 8 × 30 im Schlitten um 90°
schwenkt. In Grundstellung steht der Schlitten am Ende −x und der Hebel zeigt in Fahrtrichtung (+x); geschwenkt zeigt
er über die linke Leiste.

Anforderungen: Hub 220 mm, Schwenk 90°, beide Bewegungen begrenzt und über den ganzen Weg kollisionsfrei; der Hebel
fährt mit dem Schlitten mit; der Hebel liegt 25 mm über der Grundplatte.
```

- [ ] **Step 7: Unit-Test `tests/baugruppe/test_schlitten_spec.py` (neu)**

```python
"""Referenz Linearschlitten (Spec 4a): Spezifikation gültig und ohne Hinweise, Bewegungen aufgelöst."""

from pathlib import Path

from swki.baugruppe.befehle import validieren
from swki.baugruppe.bewegung import bewegungen
from swki.baugruppe.laden import lade_baugruppe
from swki.konfig import lade_standard

REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "schlitten" / "linearschlitten.yaml"


def test_referenz_schlitten_gueltig_ohne_hinweise():
    ergebnis = validieren(REFERENZ)
    assert ergebnis["gueltig"] and ergebnis["hinweise"] == [], ergebnis["hinweise"]
    assert (ergebnis["komponenten"], ergebnis["verknuepfungen"]) == (10, 22)


def test_referenz_schlitten_bewegungen():
    bws = bewegungen(lade_baugruppe(REFERENZ).spec, lade_standard())
    assert [(b.name, b.art, b.komponente, b.min, b.max, b.schritte) for b in bws] == [
        ("Schlittenhub", "abstand", "schlitten", 0.0, 220.0, 16), ("Hebelschwenk", "winkel", "hebel", 0.0, 90.0, 16)]
```

Run: `.venv\Scripts\python.exe -m pytest tests/baugruppe/test_schlitten_spec.py -q` → 2 passed. Meldet `validieren` Hinweise (z. B. feste Zahlen in Features), sie über Parameter beseitigen und im Bericht nennen; die Anforderungen (Maße) bleiben gleich.

- [ ] **Step 8: `tests/referenz/test_referenzen.py` – Schlitten aufnehmen**

In der Parametrisierung nach `("stehlager", "stehlager.yaml"),` ergänzen:

```python
    ("schlitten", "linearschlitten.yaml"),
```

Run: `.venv\Scripts\python.exe -m pytest -q` → **693 passed, 112 deselected** (691 + 2; ein Referenzfall mehr).

- [ ] **Step 9: Live – Referenz**

Vorbedingungen (frisches SolidWorks, eine Instanz, `False 1`; sonst BLOCKED Neustart). Run: `.venv\Scripts\python.exe tests\live_einzeln.py "tests\referenz\test_referenzen.py::test_referenz_besteht[schlitten-linearschlitten.yaml]" --zeit 900` → OK.

Schlägt der Schlitten fehl: nur den **Bauweg** nachbessern (Verknüpfungsreferenzen, Ausrichtungen, Reihenfolge, Feature-Reihenfolge der Teile), nie Parameter, Normteile, `freiheitsgrade`, `bewegungen` oder `pruefung`. Jede Änderung mit Grund in den Bericht. Bleibt ein Mangel, der eine Anforderung betrifft: anhalten (NEEDS_CONTEXT) mit Prüfbericht-Auszug, der Controller entscheidet.

- [ ] **Step 10: Commit (Implementer), dann anhalten**

```powershell
git add tests/referenz/schlitten tests/referenz/test_referenzen.py tests/baugruppe/test_schlitten_spec.py
git commit -m "referenz: Linearschlitten mit Schlittenhub und Hebelschwenk (Stufe 4a)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Status DONE_WITH_CONCERNS „Prüfer-Urteil ausstehend“; im Bericht: Lauf-Ergebnis, Dauer je Bewegungslauf, Gewindepaarungen (Einschraublänge, Volumen ist/soll), Private Bytes, jede Bauweg-Änderung.

- [ ] **Step 11 (Controller): Linearschlitten als Auftrag mit Prüfer-Urteil**

1. `tests/referenz/schlitten/` nach `auftraege/REF-schlitten/` kopieren (nicht ins Git); frisches SolidWorks.
2. `swki validieren` → `swki freigeben` → `swki bauen` → `swki pruefen` (je mit `auftraege/REF-schlitten/linearschlitten.yaml`).
3. Prüfer-Agent (`subagent_type: pruefer`) mit: Eingabeordner `auftraege/REF-schlitten/eingabe/`, freigegebene Specs (`linearschlitten.freigegeben.yaml`, `grundplatte.freigegeben.yaml`, `leiste.freigegeben.yaml`, `schlitten.freigegeben.yaml`, `hebel.freigegeben.yaml`), Prüfbericht `protokolle/linearschlitten.lauf-<n>.pruefbericht.json`, Bilderordner des Laufs. Urteil unverändert nach `protokolle/linearschlitten.lauf-<n>.pruefer.json`.
4. `swki status` → „bestanden“; bei Mängeln des Prüfers: Bauweg nachbessern (neuer Lauf) oder dem Nutzer melden, wenn eine Anforderung betroffen ist.
5. Ergebnis (Lauf, Urteil, Dauer je Bewegungslauf) in den Ledger; `auftraege/REF-schlitten/` und `%USERPROFILE%\.swki\arbeit\REF-schlitten\` danach löschen (wie REF-stehlager).

---

### Task 9: Negativfälle am Linearschlitten (live)

**Files:**
- Create: `tests/live/test_live_schlitten.py`

**Interfaces:**
- Consumes: Referenz Linearschlitten (Task 8); `sw_baugruppe.grenzen` (Task 6, Ziel des monkeypatch in Fall 2).
- Produces: die vier Negativfälle der Spec 4a §12 (Präzisierung 13); jeder liefert **genau** seine Mängelmenge.

- [ ] **Step 1: `tests/live/test_live_schlitten.py` (neu)**

```python
"""Live: Negativfälle am Linearschlitten (Spec 4a §12, Präzisierung 13) – Stellungskollision, Grenze im Modell zu weit,
umgekehrte Richtung, zweiter Freiheitsgrad. Jeder Fall liefert genau seine Mängelmenge."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from swki.baugruppe import sw_baugruppe
from swki.cli import main
from swki.konfig import lade_rechner

pytestmark = pytest.mark.sw
AUFTRAG = "SWKI-LIVE-SCHLITTEN"
REFERENZ = Path(__file__).resolve().parents[1] / "referenz" / "schlitten"
ANSCHLAG = {
    "art": "teil", "name": "Anschlag", "material": "1.0038", "eigenschaften": {"Benennung": "Anschlag"},
    "parameter": {"L": 20, "B": 20, "H": 20},
    "features": [{"id": "f1", "typ": "extrusion",
                  "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
                  "ende": {"typ": "blind", "tiefe": "=H"}}],
    "pruefung": {"huellquader": ["=L", "=H", "=B"]},
}


def _lauf(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def auftrag(tmp_path):
    ordner = tmp_path / AUFTRAG
    shutil.copytree(REFERENZ, ordner)
    yield ordner
    shutil.rmtree(lade_rechner().arbeitsordner / AUFTRAG, ignore_errors=True)


def _aendere(ordner: Path, aendern) -> Path:
    pfad = ordner / "linearschlitten.yaml"
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    aendern(spec)
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def _v(spec: dict, vid: str) -> dict:
    return next(v for v in spec["verknuepfungen"] if v["id"] == vid)


def _baue_und_pruefe(capsys, pfad: Path) -> dict:
    assert _lauf(capsys, "validieren", str(pfad))[0] == 0
    assert _lauf(capsys, "freigeben", str(pfad))[0] == 0
    code, bau = _lauf(capsys, "bauen", str(pfad))
    assert code == 0, bau
    code, bericht = _lauf(capsys, "pruefen", str(pfad))
    assert code in (0, 1) and "maengel" in bericht, bericht
    return bericht


def _maengel(bericht: dict) -> dict:
    assert bericht["bestanden"] is False, bericht
    return {m["pruefung"]: m for m in bericht["maengel"]}


def test_stellungskollision(capsys, auftrag):
    # Anschlag auf der linken Leiste bei x 80…100: trifft den geschwenkten Hebel nur, wenn der Schlitten auf max steht
    # (Bolzen bei x = 90) – das finden nur die Paarläufe, in beiden Richtungen; die Grundstellungsläufe bleiben frei
    (auftrag / "anschlag.yaml").write_text(yaml.safe_dump(ANSCHLAG, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def aendern(s):
        s["parameter"]["AX"] = 230
        s["komponenten"].append({"id": "anschlag", "quelle": {"teil": "anschlag.yaml"}})
        s["verknuepfungen"] += [
            {"id": "v30", "typ": "deckungsgleich", "a": {"komponente": "anschlag", "feature": "f1", "flaeche": "-y"},
             "b": {"komponente": "leiste_links", "feature": "f1", "flaeche": "+y"}, "ausrichtung": "entgegengesetzt"},
            {"id": "v31", "typ": "abstand", "a": {"komponente": "anschlag", "feature": "f1", "flaeche": "-x"},
             "b": {"komponente": "grundplatte", "feature": "f1", "flaeche": "-x"}, "ausrichtung": "gleich", "wert": "=AX"},
            {"id": "v32", "typ": "deckungsgleich", "a": {"komponente": "anschlag", "feature": "f1", "flaeche": "-z"},
             "b": {"komponente": "grundplatte", "feature": "f1", "flaeche": "-z"}, "ausrichtung": "gleich"},
        ]
        s["pruefung"]["huellquader"] = [300, 65, 100]  # der Anschlag ragt 10 mm über den Hebel

    bericht = _baue_und_pruefe(capsys, _aendere(auftrag, aendern))
    maengel = _maengel(bericht)
    assert set(maengel) == {"bewegung_kollision:Hebelschwenk", "bewegung_kollision:Schlittenhub"}, maengel
    for m in maengel.values():
        assert set(m["knoten"]) == {"anschlag", "hebel"}, maengel
    grund = [x for x in bericht["bewegungen"]["laeufe"] if not x["gegen"]]
    assert [x["kollisionen"] for x in grund] == [0, 0], bericht["bewegungen"]


def test_grenze_im_modell_zu_weit(capsys, auftrag, monkeypatch):
    # Der Bau setzt die obere Grenze von g1 um 20 mm zu weit (die Spec bleibt gültig und unverändert): der Schritt
    # über HUB hinaus geht durch
    original = sw_baugruppe.grenzen

    def zu_weit(v, parameter):
        g = original(v, parameter)
        return {**g, "max": (g["max"][0] + 20, None)} if v.id == "g1" else g

    monkeypatch.setattr(sw_baugruppe, "grenzen", zu_weit)
    maengel = _maengel(_baue_und_pruefe(capsys, auftrag / "linearschlitten.yaml"))
    assert set(maengel) == {"grenze:Schlittenhub"}, maengel


def test_umgekehrte_richtung(capsys, auftrag):
    # g1 an den Flächen +x: Grundstellung am Ende +x, der Hub fährt nach −x – Schlitten und Hebel enden 2 · HUB neben
    # der Soll-Endlage; sonst bleibt alles frei
    def aendern(s):
        _v(s, "g1")["a"]["flaeche"] = "+x"
        _v(s, "g1")["b"]["flaeche"] = "+x"

    bericht = _baue_und_pruefe(capsys, _aendere(auftrag, aendern))
    maengel = _maengel(bericht)
    assert set(maengel) == {"endlage:Schlittenhub:schlitten", "endlage:Schlittenhub:hebel"}, maengel
    ist = next(p["ist"] for p in bericht["pruefungen"] if p["id"] == "endlage:Schlittenhub:schlitten")
    assert ist == pytest.approx([-220.0, 0.0, 0.0], abs=0.1), ist


def test_zweiter_freiheitsgrad(capsys, auftrag):
    # ohne v21 ist der Schlitten auch quer (z) verschiebbar: mit Antrieb bleibt er unterbestimmt
    maengel = _maengel(_baue_und_pruefe(capsys, _aendere(
        auftrag, lambda s: s.update(verknuepfungen=[v for v in s["verknuepfungen"] if v["id"] != "v21"]))))
    assert set(maengel) == {"freiheitsgrad:schlitten"}, maengel
```

Gilt nach Spike-Zeile 7 der andere Drehsinn (Hebel schwenkt nach +z), legt Fall 1 den Anschlag auf die rechte Leiste (`v30` an `leiste_rechts`, `v32` mit den Flächen `+z`). Gilt nach Spike-Zeile 4 „Mitfahrer melden 2“, erwartet Fall 4 die Menge aus der Ledger-Entscheidung.

- [ ] **Step 2: Unit-Tests**

Run: `.venv\Scripts\python.exe -m pytest -q` → **693 passed, 116 deselected** (vier neue Live-Tests).

- [ ] **Step 3: Live – einzeln, je frisches SolidWorks**

Je Test-ID `.venv\Scripts\python.exe tests\live_einzeln.py tests\live\test_live_schlitten.py::<test> --zeit 900`; vor jedem Test BLOCKED (Neustart), außer der Controller meldet „frisch neu gestartet“. Erwartet: 4/4 OK.

Weicht die Mängelmenge eines Falls ab: **nicht** die Erwartung anpassen, sondern anhalten (NEEDS_CONTEXT) und den Prüfbericht-Auszug melden (alle Mängel mit `beschreibung`, Abschnitt `bewegungen`) – der Controller entscheidet, ob die Erwartung oder der Code falsch ist.

- [ ] **Step 4: Commit**

```powershell
git add tests/live/test_live_schlitten.py
git commit -m "live: Negativfälle am Linearschlitten (Stellungskollision, Grenze, Richtung, Freiheitsgrad)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Im Bericht: je Test OK/Fehler, Dauer, Private Bytes vorher → nachher, Instanzen und Einstellungen am Ende.

---

### Task 10: Skill, Prüfer, CLAUDE.md, Design, Ergebnisse, Regression

**Files:**
- Modify: `.claude/skills/baugruppe/SKILL.md`, `.claude/agents/pruefer.md`, `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` (§4 Baugruppe, §11)
- Create: `docs/stufe4a/ergebnisse.md`

**Interfaces:**
- Consumes: Ergebnisse von Task 1–9 (Ledger, Berichte, Spike-JSON).
- Produces: Doku im Stand der Umsetzung; Regression live.

- [ ] **Step 1: `.claude/skills/baugruppe/SKILL.md` – neuen Abschnitt am Ende**

```markdown
## 6. Bewegungen (Stufe 4a)

Bewegliche Komponenten bekommen eine **Grenzverknüpfung** und `freiheitsgrade: 1`; jede Bewegung nennt ihre Grenze.

- `grenze_abstand` (mm) / `grenze_winkel` (Grad): `a`, `b` (ebene Flächen), `ausrichtung` (Pflicht), `min`, `max`.
  **Bewegt wird Seite `a`.** `min`/`max` sind `0` oder Parameter (`"=HUB"`); eine feste Zahl ist ein Befund
  (`GRENZE_FESTE_ZAHL`), weil nur Parameter von der Freigabe geschützt werden.
- `scharnier`: `a`, `b` sind Achsen (Bohrungsachse bzw. `EINBAU_ACHSE` des Drehbolzens), `anlage_a`/`anlage_b` ebene
  Flächen derselben Komponenten – die Anlage nicht vergessen, sonst ist die Höhe frei. swki legt `konzentrisch` (ohne
  Drehsperre) und `deckungsgleich` (`<id>.anlage`) an. Ein Drehbolzen ISO 8734 braucht auf der drehenden Seite eine
  `bohrung` mit Ø > d.
- `freiheitsgrade: {<komponente|gruppe>: 1}`; genau eine Bewegung treibt sie.
- `bewegungen`: `{name, grenze, schritte?, erwartet: {endlagen: [...]}}`. Endlagen als `verschiebung: [x, y, z]` (mm)
  oder `drehung: {achse, winkel}` (Grad, Rechte-Hand-Regel) in Baugruppenkoordinaten, Differenz zwischen `min` und
  `max`. Mitfahrende Komponenten als eigene Endlage eintragen (z. B. der Hebel auf dem Schlitten).
- `bauen` speichert in Grundstellung (alle bewegten Komponenten auf `min`).
- `pruefen` fährt jede Bewegung in `schritte + 1` Stellungen ab (Vorgabe `bewegung_schritte`) und prüft Kollision je
  Stellung, „Grenze wirkt“, „Freiheitsgrad belegt“ und die Endlagen; Bewegungen mit sich schneidenden Räumen zusätzlich
  gegeneinander (Paarläufe). Mängel: `freiheitsgrad:<k>`, `bewegung:<name>`, `bewegung_kollision:<name>`,
  `grenze:<name>`, `endlage:<name>:<k>`. Bilder `<Bewegung>-min|mitte|max` und `<Bewegung>-kollision-…`.
- **`SPEICHER_KNAPP`** (Exit 1, kein Prüfbericht): SolidWorks selbst neu starten und `swki pruefen` erneut aufrufen;
  scheitert es auch frisch, dem Nutzer melden.
- Ab vier Bewegungen meldet `validieren` den Hinweis `pruefaufwand` – mit dem Nutzer klären, ob alle nötig sind.
```

Zusätzlich im Kopf des Skills (Titelzeile `# Baugruppe (statisch, Stufe 3b)`) den Titel ändern zu `# Baugruppe (Stufe 3b, Bewegungen Stufe 4a)` und in der Beschreibung im Frontmatter „statische Baugruppe“ durch „Baugruppe (statisch oder mit begrenzten Bewegungen)“ ersetzen.

- [ ] **Step 2: `.claude/agents/pruefer.md` – Abschnitt vor „## Antwort“**

```markdown
## Zusätzlich bei Bewegungen (`bewegungen` in der Spezifikation)

- Je Bewegung gibt es Iso-Bilder `<Bewegung>-min`, `-mitte`, `-max`: Bewegt sich die richtige Komponente um die richtige
  Achse in die richtige Richtung? Fahren die mitbewegten Komponenten mit? Ist eine Durchdringung zu sehen?
- Sind die Grenzen fachlich sinnvoll (Bewegungsbereich passt zur Eingabe, Anschlag statt Durchfahren)?
- Bilder `<Bewegung>-kollision-…` zeigen gemeldete Kollisionen; sie stehen schon als Mängel im Prüfbericht.
```

- [ ] **Step 3: `CLAUDE.md`**

1. Den „Stand:“-Absatz (ab „Stand:“ bis vor die Leerzeile vor „## Umgebung“) ersetzen durch:

```markdown
Stand: Stufe 4a (Bewegungen) umgesetzt – Ergebnisse: docs/stufe4a/ergebnisse.md. Nächster Schritt nach Nutzerwahl:
Stufe 4b (Zahnrad, Nut, Kurve; Referenz Schieber mit Schrägbolzen) oder Paket „Messarten“ (Fasen, Gewinde durch,
Lagerachse).
```

2. Nach dem Abschnitt „## Baugruppen (Stufe 3b)“ einfügen:

```markdown
## Bewegungen (Stufe 4a)
- Bewegliche Komponenten: Grenzverknüpfung (`grenze_abstand`/`grenze_winkel`, bewegt wird Seite `a`, `min`/`max` als
  Parameter), `freiheitsgrade: 1`, eine Bewegung je Grenze; Scharnier mit Anlage. Regeln im Skill `baugruppe` (§6).
- `swki pruefen` prüft die Bewegungen mit; `SPEICHER_KNAPP` → SolidWorks selbst neu starten und erneut prüfen.
- Regressions-Suite enthält den Linearschlitten (`tests/referenz/schlitten/`).
```

- [ ] **Step 4: Design `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`**

1. §4 „Baugruppe“: nach der Zeile „**Stand Stufe 3b (2026-10-03):** …“ eine Zeile einfügen:
   „**Stand Stufe 4a:** `bewegungen`, Grenzverknüpfungen, Scharnier und `freiheitsgrade: 1` siehe [2026-10-03-stufe-4a-bewegungen-design.md](2026-10-03-stufe-4a-bewegungen-design.md); `treibend: true` und `antrieb: {von, bis}` im Beispiel unten sind überholt (Antrieb nur während der Prüfung, Bereich = Grenze).“
2. §11: die Zeile, die mit `| 4 | Mechanische Abläufe:` beginnt, ersetzen durch:

```markdown
| 4a | Bewegungen: Grenzverknüpfungen, Scharnier, gezählte Freiheitsgrade, `bewegungen`, Bewegungsprüfung (Kollision je Stellung, Grenze, Freiheitsgrad, Endlagen, Paarläufe) – Design: [2026-10-03-stufe-4a-bewegungen-design.md](2026-10-03-stufe-4a-bewegungen-design.md) | Referenz *Linearschlitten* besteht (Code-Prüfungen und Prüfer), vier Negativfälle; Buchse, Formplatte, Auswerferhalteplatte, Stehlager bestehen weiter |
| 4b | Mechanische Kopplungen: Zahnrad-, Nut-, Kurvenverknüpfung | Referenz *Schieber mit Schrägbolzen* (Kandidat) besteht |
```

- [ ] **Step 5: Regression live**

Je Fall einzeln (`--zeit 900`), frisches SolidWorks vor dem Stehlager und vor dem Schlitten (BLOCKED Neustart):
`tests\referenz\test_referenzen.py::test_referenz_besteht[buchse-buchse.yaml]`, `…[formplatte-formplatte_ds.yaml]`, `…[auswerferhalteplatte-auswerferhalteplatte.yaml]`, `…[stehlager-stehlager.yaml]`, `…[schlitten-linearschlitten.yaml]` → 5/5 OK. Dazu `tests\live\test_live_baugruppe.py::test_probe_besteht_pruefung` (3b-Probe unverändert) → OK.

- [ ] **Step 6: `docs/stufe4a/ergebnisse.md` (neu)**

Gliederung (Inhalte aus Ledger, Berichten und Spike-JSON; Zahlen nicht schätzen, sondern übernehmen):

1. **Kurzfassung:** was 4a kann, Testzahlen vorher → nachher (622 → …, 109 → … deselected), Live-Ergebnisse.
2. **Spike S13:** je Zeile 1–9 Ergebnis und Entscheidung (Ledger), besonders Maßnamen der Grenzen, Verhalten über der Grenze, Status der Mitfahrer, Drehsinn, Zeit und Private Bytes je Schritt (Probe, ~100 Komponenten) und die daraus gesetzten Vorgaben `bewegung_schritte`, `speicher_grenze_mb`.
3. **Referenz Linearschlitten:** Lauf, Prüfer-Urteil, Dauer je Bewegungslauf, Paare, Gewindepaarungen.
4. **Negativfälle:** je Fall Mängelmenge und Dauer.
5. **Regression:** 5 Referenzen + 3b-Probe, Private Bytes, Neustarts.
6. **Abweichungen von der Spec:** Präzisierungen 1 (Scharnier als zwei Verknüpfungen) und 13 (Negativfälle 1 und 4), weitere Rulings des Ledgers.
7. **Offene Punkte:** aus dem Gesamt-Review und den Rulings; Kandidaten für 4b.

- [ ] **Step 7: Gesamtlauf**

Run: `.venv\Scripts\python.exe -m pytest -q` → **693 passed, 116 deselected** (oder die im Ledger begründete Zahl).
Run: `$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -m swki api pruefe-code` → keine Befunde.

- [ ] **Step 8: Commit**

```powershell
git add .claude/skills/baugruppe/SKILL.md .claude/agents/pruefer.md CLAUDE.md docs/superpowers/specs/2026-09-26-solidworks-ki-design.md docs/stufe4a/ergebnisse.md
git commit -m "docs: Stufe 4a – Skill, Prüfer, CLAUDE.md, Design §4/§11, Ergebnisse" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Abdeckung (Selbstprüfung gegen die Spec 4a)

| Spec 4a | Task |
|---|---|
| §2 Entscheidungen: Zuschnitt, Referenz, Antrieb nur während der Prüfung, Freigabe, Prüfung je Bewegung, Paare, Bilder, Negativfälle, Architektur | 2–9 (Einzelzeilen unten) |
| §3 Bausteine | 2–7, 10 |
| §4.1 Grenzverknüpfungen (Parameter-Pflicht, Seite a, Gleichung) | 2, 3, 6 |
| §4.2 Scharnier (Präzisierung 1), Passung Drehbolzen | 2, 3, 6 |
| §4.3 `freiheitsgrade` (1, > 1 Befund, Zuordnung zu Bewegungen) | 2, 3 |
| §4.4 `bewegungen` (Bereich = Grenze, Schritte, Endlagen, Hinweis) | 2, 3, 4 |
| §5 Validieren | 3 |
| §6 Freigabe (`bewegungen` in der Prüfsumme) | 2 |
| §7 Bauen (Grenzen, Grundstellung, Protokoll) | 6 |
| §8.1 Statik (unterbestimmt in Grundstellung) | 4, 7 |
| §8.2 Bewegungsprüfung (Festhalten, Freiheitsgrad, Grundstellungslauf, Grenze, Endlagen, Paarläufe, Aufräumen) | 4, 5, 6, 7 |
| §8.3 Bilder | 5, 6, 7 |
| §8.4 Speicher (`SPEICHER_KNAPP`) | 5, 6, 7 |
| §8.5 Prüfbericht | 4, 7 |
| §9 Prüfer, Schleife, Bericht | 7, 8, 10 |
| §10 Fehlerfälle | 3, 5, 6 |
| §11 Spike S13 | 1 |
| §12 Tests (Unit, Live, Negativfälle) | 2–9 |
| §13 Einbindung (Skill, Standard, CLAUDE.md, Design §11) | 3, 10 |
| §14 Fertig, wenn | 8, 9, 10 |
| §15 Reihenfolge | Task-Reihenfolge |
