# SolidWorks-KI – Design

Stand: 26.09.2026 · Status: Entwurf zur Durchsicht

## 1. Ziel

Claude Code konstruiert in SolidWorks selbstständig Einzelteile und Baugruppen – einschließlich
mechanischer Abläufe – aus Skizzen, Beschreibungen und Anweisungen, prüft das Ergebnis selbst und
bessert nach. Der Mensch greift an genau einer Stelle ein: der Freigabe der Spezifikation.

Randbedingungen:

- Rechner A: Windows 11, SOLIDWORKS 2025 (deutsche Oberfläche), Python 3.14, Node.js.
- Rechner B: SOLIDWORKS 2026. Dasselbe Projekt muss auf beiden Rechnern laufen.
- Werkzeugbau mit vertraulichen Kundendaten: keine Daten an externe Dienste außer Claude selbst.
- Fokus: allgemeine Konstruktion (Teile, Baugruppen, Verknüpfungen, kinematische Abläufe).
  Blech, Schweißkonstruktionen, Flächen, Zeichnungen folgen später.

Grundlage der Werkzeugwahl: [docs/tool-pruefung-2026-09-26.md](../../tool-pruefung-2026-09-26.md).

## 2. Architektur (Weg 1)

```
Skizze/Beschreibung ──► Claude (Skill „konstruieren“) ──► Spezifikation (YAML, mm)
                                                              │  swki validieren
                                                              ▼
                                                      Freigabe durch Nutzer (swki freigeben)
                                                              │
               ┌──────────────────────────────────────────────┤
               ▼                                              │
     swki bauen (Compiler, pywin32/COM) ──► SolidWorks ◄── SolidworksMCP-python (nur lesen)
               │                                              ▲
               ▼                                              │
     swki pruefen (Code-Prüfungen, Screenshots) ──► Prüfer-Agent (unabhängig)
               │
               ▼
     bestanden → Bericht   |   Mängel → Claude ändert Bauweg → neuer Lauf (max. N)
```

- **Gebaut wird ausschließlich über `swki`**, ein eigenes Python-Paket (pywin32/COM), das eine
  Spezifikation deterministisch in einem Durchlauf umsetzt.
- **SolidworksMCP-python** (andrewbartels1, gepinnter Commit) dient Claude nur zum Ansehen:
  Feature-Baum, Masseeigenschaften, Modellinfo. Alle schreibenden Tools sind gesperrt, ebenso
  `export_image` (Rückfall auf `SaveAs3` kann Dokumente überschreiben, siehe
  docs/stufe0/ergebnisse.md). Screenshots/Bildexport laufen über `swki`, nicht über MCP.
- **Lücken** im Spezifikationsformat werden über einen kontrollierten Skript-Notausgang geschlossen;
  bewährte Skripte werden von Claude selbstständig zu festen Compiler-Handlern.

## 3. Projektstruktur und Mehrrechner-Betrieb

Synchronisation über Git (privates GitHub-Repo).

```
SolidWorks-KI/
  CLAUDE.md
  .mcp.json                   Pfade über ${USERPROFILE} und ${SWKI_SW_YEAR}
  .claude/settings.json       Rechte, Sperren der MCP-Tools
  .claude/skills/             konstruieren, normteile, compiler-erweitern
  .claude/agents/pruefer.md
  swki/                       Python-Paket
  schema/                     JSON-Schemas: teil, baugruppe
  normteile/katalog/          YAML je Hersteller
  normteile/dateien/          eigene Normteile (gespeichert in SW 2025)
  normteile/eigene/           Spezifikationen selbst konstruierter Normteile
  auftraege/<name>/           eingabe/, *.yaml, skripte/, freigabe.json, protokolle/, bericht.md
  config/standard.yaml        max_nachbesserungen: 3, Namensschema, Toleranzen
  config/rechner.beispiel.yaml
  setup/einrichten.ps1
  tests/                      Unit-Tests, Live-Tests (Marker sw), tests/referenz/
```

Nicht im Git, pro Rechner:

- `config/rechner.yaml` – SW-Jahr, Teile-/Baugruppenvorlage, Materialdatenbank, Arbeitsordner.
- `.venv/` – Python-Umgebung.
- `%USERPROFILE%\.swki\` – `SolidworksMCP-python\` (gepinnt), `api\<jahr>\` (API-Index),
  `arbeit\<auftrag>\lauf-<n>\` (erzeugte .sldprt/.sldasm, STEP, Screenshots).

`setup/einrichten.ps1`: SW-Version aus der Registry erkennen, `rechner.yaml` anlegen, `.venv`
und `swki` installieren, MCP-Server gepinnt installieren (nur Basis, keine Extras), API-Index bauen,
Benutzer-Umgebungsvariablen `SWKI_SW_YEAR` setzen. Idempotent.

Versionsregeln:

- Die Spezifikation ist die Quelle; SolidWorks-Dateien aus Aufträgen kommen nicht ins Git.
- Eigene Normteil-Dateien werden nur auf dem 2025-Rechner gespeichert (2026-Dateien sind in 2025
  nicht lesbar). `swki normteil aufnehmen` verweigert das Speichern in die Bibliothek unter SW > 2025.
- Compiler-Code verwendet nur API-Aufrufe, die in SW 2025 verfügbar sind (siehe 7).
- Namensschema für Dateien und Custom Properties ist in `config/standard.yaml` konfigurierbar
  (Vorgabe: `<auftrag>_<name>`; Eigenschaften Benennung, Material, Ersteller, Auftrag).

## 4. Spezifikationsformat

Eine YAML-Datei je Teil oder Baugruppe. Längen in mm, Winkel in Grad. Schema-Prüfung vor jedem Bau.

### Teil

```yaml
art: teil
name: Formplatte_DS
material: "1.2312"
eigenschaften: {Benennung: Formplatte DS}
parameter: {L: 296, B: 246, H: 46}          # werden SW-Gleichungen (globale Variablen)
features:
  - id: f1
    typ: extrusion
    skizze:
      ebene: oben                              # vorne | oben | rechts | {feature: f1, flaeche: ...} | {nahe: [...]}
      elemente: [{rechteck: {mitte: [0, 0], breite: =L, hoehe: =B}}]
    ende: {typ: blind, tiefe: =H}
  - id: f3
    typ: verrundung
    kanten: [{feature: f1, auswahl: senkrechte_kanten}]
    radius: 5
  - id: f4
    typ: fase
    kanten: [{nahe: [148, 123, 46]}]
    abstand: 1
  - id: f5
    typ: skript                                # Notausgang
    datei: skripte/f5_gewinde.py
    luecke: "Gewindedarstellung Bohrungsassistent"
pruefung:
  huellquader: [296, 246, 46]
  volumen: {soll: auto, toleranz_prozent: 0.5}
  masse_pruefen:
    - {was: "Abstand Bohrung 1–2", von: {feature: f2, instanz: 1, achse: true},
       zu: {feature: f2, instanz: 2, achse: true}, soll: 250, tol: 0.01}
max_nachbesserungen: 3                         # optional, überschreibt config/standard.yaml
```

### Baugruppe

**Stand Stufe 3b (2026-10-03):** Format, Referenzen und `je_position` siehe [2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md); `bewegungen`, `treibend` und gezählte `freiheitsgrade` folgen in Stufe 4.

**Stand Stufe 4a:** `bewegungen`, Grenzverknüpfungen, Scharnier und `freiheitsgrade: 1` siehe [2026-10-03-stufe-4a-bewegungen-design.md](2026-10-03-stufe-4a-bewegungen-design.md); `treibend: true` und `antrieb: {von, bis}` im Beispiel unten sind überholt (Antrieb nur während der Prüfung, Bereich = Grenze).

```yaml
art: baugruppe
name: Beispielbaugruppe
komponenten:
  - {id: platte, quelle: {teil: formplatte_ds.yaml}, fixiert: true}
  - {id: saeule1, quelle: {normteil: meusburger/E1000-22x100}}
  - {id: schraube1, quelle: {normteil: toolbox/DIN912-M8x30}}
  - {id: auswerferplatte, quelle: {teil: auswerferplatte.yaml}, gruppe: auswerferpaket}
verknuepfungen:
  - {id: m1, typ: konzentrisch, a: saeule1.einbau_achse, b: {komponente: platte, nahe: [120, 95, 46]}}
  - {id: m2, typ: deckungsgleich, a: saeule1.einbau_flaeche, b: platte.oberseite}
  - {id: hub, typ: abstand, a: auswerferplatte.unterseite, b: platte.oberseite, wert: 0, treibend: true}
freiheitsgrade: {auswerferpaket: 1, rest: 0}
bewegungen:
  - name: Auswerferhub
    antrieb: {verknuepfung: hub, von: 0, bis: 60, schritte: 30}
    erwartet: {kollisionsfrei: true, endlage: {komponente: auswerferplatte, verschiebung: [0, 0, 60]}}
pruefung:
  kollisionsfrei_statisch: true
```

Regeln:

- Skizzen werden vollständig bemaßt und mit Beziehungen voll bestimmt; Parameter werden zu
  SW-Gleichungen. Modelle bleiben in SolidWorks änderbar.
- Ebenen werden sprachunabhängig aufgelöst: zuerst Name, sonst die ersten drei Referenzebenen im Baum
  (Vorne, Oben, Rechts). Achsrichtungen: Vorne → +Z, Oben → +Y, Rechts → +X.
- Kanten/Flächen: bevorzugt semantisch (`{feature, flaeche|auswahl}`), sonst Punkt-Anker `nahe`
  mit Toleranz 0,1 mm. Kein Treffer → `REFERENZ_NICHT_GEFUNDEN` (mit nächstem Abstand),
  mehrere → `REFERENZ_MEHRDEUTIG`.
- Normteile referenzieren ihre benannte Einbaugeometrie (`einbau_achse`, `einbau_flaeche`, …).
- Komponenten können über `gruppe` zusammengefasst werden; `freiheitsgrade` nennt die erwarteten
  Freiheitsgrade je Gruppe oder Komponente, `rest` gilt für alle übrigen.
- Bewegungen werden über eine treibende Verknüpfung dargestellt, die schrittweise verstellt wird.
- Nicht abbildbare Features stehen ausdrücklich als `typ: skript` mit `luecke:`; nie still weglassen.

## 5. Compiler `swki`

Kommandozeile, Ausgabe JSON:

```
python -m swki validieren <spec>            # Schema + Plausibilität, ohne SolidWorks
python -m swki freigeben  <spec>            # schreibt freigabe.json (Prüfsumme)
python -m swki bauen      <spec> [--lauf n]
python -m swki pruefen    <spec> --lauf n
python -m swki normteil suchen|aufnehmen ...
python -m swki api suche|methode|enum|pruefe-code ...
```

Module:

- `verbindung` – Anbindung an laufendes SolidWorks (Version aus `rechner.yaml`), Late Binding
  (`win32com.client.GetActiveObject`, dynamischer Dispatch – `EnsureDispatch` auf das bereits
  laufende Objekt schlägt fehl, siehe docs/stufe0/ergebnisse.md; `EnsureModule(sldworks.tlb)` +
  `CastTo` für echtes Early Binding ist ungetestet, vor Stufe 2 klären), Hilfen `mm()`, `grad()`,
  `VARIANT`-Callout.
- `spec` – Laden, Schema-Prüfung, Parameterauflösung, Prüfsumme.
- `compiler` – Handler-Registry (`@handler("extrusion")`), je Feature-Typ eine kleine Funktion,
  Rückgabe: SW-Featurename und erzeugte Topologie für spätere Anker.
- `anker` – Auflösung von Ebenen, semantischen und Punkt-Ankern.
- `baugruppe` – Teile bauen, Normteile in den Arbeitsordner kopieren, Komponenten einfügen,
  Verknüpfungen setzen.
- `skripte` – Notausgang: lädt `bauen(ctx)` aus dem Auftrag; vorher statische Prüfung (AST) auf
  verbotene Importe/Aufrufe (`os.remove`, `shutil`, `subprocess`, `socket`, `urllib`, `requests`,
  `exec`, `eval` u. ä.).
- `protokoll` – `protokoll.json`: Status, Dauer, SW-Featurename, Fehler je Knoten; Phasenzeiten.

Bauablauf: neues Dokument aus Vorlage → Knoten in Reihenfolge bauen → nach jedem Knoten
Rebuild-Fehler prüfen → beim ersten Fehler anhalten (Knoten-ID, Schritt, Fehlercode, SW-Meldung) →
speichern in `%USERPROFILE%\.swki\arbeit\<auftrag>\lauf-<n>\` → Protokoll schreiben.
Jeder Lauf baut frisch.

Schutzregeln im Code: nur selbst angelegte Dokumente anfassen und schließen; nur im Arbeitsordner
speichern; Bibliotheks-Normteile nur kopieren, nie verändern.

## 6. Prüfung und Nachbesserung

`swki pruefen` → `pruefbericht.json` + Screenshots.

1. **Code-Prüfungen**
   - Teil: Rebuild fehlerfrei, Skizzen voll bestimmt, Hüllquader, Volumen/Oberfläche/Masse gegen
     Soll (Sollvolumen vorab analytisch, wo möglich), Einzelmaße per Messung, Schwerpunktlage
     (Spiegel-/Vorzeichenfehler), Material und Eigenschaften gesetzt.
   - Baugruppe: Verknüpfungen fehlerfrei, Bestimmtheitsstatus je Komponente gegen erwartete
     Freiheitsgrade, statische Kollisionsprüfung (Stand 3b: Gewindepaarungen über das Ringvolumen, Teilprüfung je Eigenteil,
     Lage über `masse_pruefen`; Änderungserkennung vor jedem Lauf.)
   - Bewegung: treibende Verknüpfung schrittweise verstellen, je Schritt Rebuild und
     Kollisionsprüfung, Endlagen messen.
2. **Sichtprüfung** – Screenshots Iso/Vorne/Oben/Rechts; bei Bewegungen Anfang/Mitte/Ende.
3. **Prüfer-Agent** – sieht nur Eingabe, freigegebene Spezifikation, Prüfbericht und Screenshots,
   nicht Protokolle und Skripte. Checkliste: jede Anforderung belegt, nichts ungebaut, keine
   Spiegelfehler, plausibel. Urteil: bestanden oder Mängelliste mit Knoten-IDs.

Nachbesserung:

- `freigabe.json` enthält eine Prüfsumme über Parameter, Material, Eigenschaften, Prüfwerte,
  Komponenten und erwartete Bewegungen. Claude ändert nur den Bauweg (Anker, Reihenfolge,
  Handler-Optionen, Skripte). Weicht die Prüfsumme ab, verweigert `swki bauen`. Hält Claude eine
  Anforderung für falsch, fragt es den Nutzer.
- `swki freigeben` legt zusätzlich die Spezifikation als `<spec>.freigegeben.yaml` ab (Prüfsumme der Kopie in
  `freigabe.json`). Sie ist das Soll für den Prüfer-Agenten und für das Sollvolumen `auto`. Feste Zahlen in Features
  meldet `swki validieren` als Hinweis; Anforderungsmaße gehören in `parameter`.
- Maximale Nachbesserungen: Spezifikation > Anweisung im Chat > `config/standard.yaml` (Vorgabe 3), also höchstens
  1 + 3 = 4 Läufe.
- Abbruch ohne Fortschritt: sinkt die Zahl offener Mängel gegenüber dem letzten durchgebauten und geprüften Lauf nicht,
  stoppt Claude und meldet sich. Ein Bauabbruch wird nicht verglichen und verbraucht nur einen Lauf; `swki pruefen`
  verweigert einen abgebrochenen Lauf (LAUF_ABGEBROCHEN). (Nutzerentscheidung 2026-10-01)
- `bericht.md`: Status, Läufe, offene Punkte, Screenshots, Phasenzeiten, Compiler-Änderungen.

## 7. API-Nachschlagewerk

Pro Rechner durch `einrichten.ps1`:

1. `hh.exe -decompile` für `sldworksapi.chm`, `swconst.chm`, `sldworksapiprogguide.chm` nach
   `%USERPROFILE%\.swki\api\<jahr>\`.
2. Parser → Einträge: Interface, Member, Signatur, Parameter (Typ, Beschreibung), Rückgabe,
   Hinweise, „verfügbar seit“, Enums mit Werten.
3. Abgleich von Parameteranzahl und Enum-Werten mit der Typbibliothek (makepy) – diese ist verbindlich.
4. SQLite-Index mit FTS5.

Befehle: `swki api suche`, `methode`, `enum`, `pruefe-code` (warnt bei API-Aufrufen im Compiler, die
erst nach SW 2025 verfügbar sind). Kuratiertes Wissen in `swki/wissen/pywin32-fallstricke.md`.
Der Index bleibt lokal (Dassault-Dokumentation), ins Git kommt nur der Parser.
Parametertypen und Rückgabetyp werden in Stufe 1 nicht indiziert (nur Name/aus/optional +
Seitentext); Nachrüstung bei Bedarf.

## 8. Normteile

**Stand Stufe 3a (2026-10-02):** Genormte Teile werden selbst konstruiert, aus Normtabelle und Bauvorlage, prüfen sich selbst und füllen eine lokale Bibliothek – siehe [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md). Katalog je Hersteller und `normteil aufnehmen` gelten nur noch für nicht genormte Kaufteile (eigenes Paket bei Bedarf); der Toolbox-Rückfall entfällt.

- Katalog `normteile/katalog/<hersteller>.yaml`: `id`, `benennung`, `typ`, `kennmasse`,
  `quelle` (`datei` oder `toolbox`), `einbau` (Zuordnung Einbaureferenz → Geometrie im Teil),
  `eigenschaften` (Hersteller, Bestellnummer).
- Eigene Normteile erhalten einmalig benannte Referenzgeometrie (`EINBAU_ACHSE`, `EINBAU_FLAECHE`, …).
- `swki normteil suchen` liefert exakte Treffer und nächste Alternativen.
- `swki normteil aufnehmen <sldprt|step>` importiert, legt Einbaureferenzen an (mit Claude),
  speichert (nur SW 2025) und trägt in den Katalog ein.
- Kein Treffer: Claude hält an und nennt Typ, Maße, Einbausituation. Der Nutzer reicht eine Datei
  nach. Nur auf ausdrückliche Anweisung konstruiert Claude selbst (`normteile/eigene/`).
- Toolbox: in Stufe 0 geprüft – keine der Toolbox-Methoden aus den indizierten Typbibliotheken
  (`sldworks.tlb`/`swconst.tlb`) erzeugt ein Toolbox-Teil aus Norm+Größe; das eigene
  Konfigurator-Add-in (eigene, nicht indizierte Typbibliothek) bietet nur Konfigurator-/PDM-Hooks,
  keine Erzeugung (siehe docs/stufe0/ergebnisse.md). Rückfall (einziger Weg): Größe einmal manuell
  in SolidWorks erzeugen und wie ein eigenes Normteil aufnehmen.

## 9. Einbindung in Claude Code

- **CLAUDE.md**: Spezifikation in mm; Bau erst nach Freigabe; freigegebene Anforderungen tabu;
  bauen nur über `swki`, MCP nur lesen; vor neuen API-Aufrufen nachschlagen; Normteil-Regel;
  nie in Bibliotheks-Originale oder Kundenordner schreiben; Normteile nur auf 2025 speichern;
  kein `git push` ohne Rückfrage.
- **Skills**
  - `konstruieren`: Eingabe → Spezifikation → validieren → Rückfragen → Freigabe → bauen →
    prüfen → nachbessern → Bericht.
  - `normteile`: suchen, nachfragen, aufnehmen.
  - `compiler-erweitern` – **wird von Claude selbst ausgelöst**, wenn (a) eine Lücke zum zweiten
    Mal auftritt und ein bestandenes Skript existiert, (b) einem Handler eine Option fehlt,
    (c) ein Handler wiederholt am selben Fehler scheitert. Neue Feature-Typen laufen beim ersten Mal
    über den Notausgang. Schutz: Test zuerst, Regressions-Suite `tests/referenz/` muss bestehen
    (sonst verwerfen), `swki api pruefe-code` muss bestehen, eigener lokaler Commit je Änderung,
    Eintrag im Bericht.
- **Prüfer-Agent** `.claude/agents/pruefer.md`: nur Lesezugriff auf Auftragsordner, Prüfbericht,
  Screenshots.
- **MCP**: SolidworksMCP-python über `${USERPROFILE}` / `${SWKI_SW_YEAR}`; Allowlist nur lesender
  Tools (genaue Namen bei Installation). Gesperrt u. a. `execute_macro`, `batch_execute_macros`,
  `pack_and_go_assembly`, `batch_file_operations`, `execute_workflow`, `batch_process_files`.
  Keine `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GH_TOKEN` in der Server-Umgebung; UI-/Agenten-Schicht
  wird nicht installiert.
- **Rechte**: `python -m swki …` und lesende Git-Befehle ohne Rückfrage; `git push` und
  Schreibzugriffe außerhalb von Projekt und Arbeitsordner mit Rückfrage.

## 10. Jev (später)

Nicht Teil von Stufe 0–4. Jedes Protokoll erfasst Phasenzeiten. In Stufe 5 wird ausgewertet, wo
Claude-Entscheidungen bremsen; Kandidaten: Vorprüfung der Anforderungen in der Prüfschleife,
Normteil-Vorauswahl, Tool-/Skill-Routing. Vor Einsatz klären, welche Daten an TypeSafe gehen.

## 11. Stufen

| Stufe | Inhalt | Fertig, wenn |
|---|---|---|
| 0 | Git/GitHub, `einrichten.ps1`, MCP gepinnt (nur lesen); Machbarkeitstests: pywin32 3.14 ↔ SW 2025, sprachunabhängige Ebenen, voll bemaßte Skizze + Extrusion, Masseeigenschaften + Screenshot, Kollisionsprüfung, Abstandsverknüpfung verstellen, Toolbox per API | Ergebnisse dokumentiert, Designanpassungen eingearbeitet |
| 1 | API-Nachschlagewerk | `swki api` liefert korrekte Signatur für `FeatureExtrusion3` und Werte für `swEndConditions_e` |
| 2 | Einzelteile: Schema, validieren/freigeben, Compiler (Extrusion, Schnitt/Tasche, Rotation, Bohrung, Verrundung, Fase, lineares/Kreismuster, Spiegeln), Anker, Notausgang, Prüfung 1+2, Prüfer-Agent, Schleife, Bericht, CLAUDE.md, Skills `konstruieren` + `compiler-erweitern` | Referenzen *Formplatte* und *Buchse* bestehen auf SW 2025 **und** SW 2026 |
| 2c | Normbohrungen (Bohrungsassistent), runde Skizzenkonturen, Endbedingungen „bis Fläche“/„Versatz von Fläche“, kompakter Feature-Baum – Design: [2026-09-29-stufe-2c-design.md](2026-09-29-stufe-2c-design.md) | Referenz *Auswerferhalteplatte* besteht; Buchse und Formplatte bestehen weiter |
| 3a | Normteile: Normtabellen mit Abgleich, Bauvorlagen, Selbstprüfung, Bibliothek (ISO 4762, 4032, 7089, 8734) – Design: [2026-10-02-stufe-3a-normteile-design.md](2026-10-02-stufe-3a-normteile-design.md) | Tabellen abgeglichen oder begründet gesperrt, Prüfer-Urteile je Vorlage, Stichprobe 20 Teile besteht |
| 3b | Baugruppen statisch: Standardverknüpfungen, Bestimmtheit, statische Kollision, Änderungserkennung – Design: [2026-10-03-stufe-3b-baugruppen-design.md](2026-10-03-stufe-3b-baugruppen-design.md) | Referenz *Stehlager* besteht (Code-Prüfungen und Prüfer); Buchse, Formplatte und Auswerferhalteplatte bestehen weiter |
| 4a | Bewegungen: Grenzverknüpfungen, Scharnier, gezählte Freiheitsgrade, `bewegungen`, Bewegungsprüfung (Kollision je Stellung, Grenze, Freiheitsgrad, Endlagen, Paarläufe) – Design: [2026-10-03-stufe-4a-bewegungen-design.md](2026-10-03-stufe-4a-bewegungen-design.md) | Referenz *Linearschlitten* besteht (Code-Prüfungen und Prüfer), vier Negativfälle; Buchse, Formplatte, Auswerferhalteplatte, Stehlager bestehen weiter |
| 4b | Mechanische Kopplungen: Zahnrad-, Nut-, Kurvenverknüpfung | Referenz *Schieber mit Schrägbolzen* (Kandidat) besteht |
| 5 | Zeitauswertung + Jev; optional `swki` als MCP; Blech, Schweiß, Flächen, Formschräge, Zeichnungen | je Erweiterung eigene Referenz |

## 12. Tests

- Ohne SolidWorks (pytest): Schema, Validierung, Parameter, Einheiten, Anker-Geometrie,
  Volumenberechnung, Skript-Prüfung, Katalogsuche, Prüfsumme.
- Mit SolidWorks (pytest-Marker `sw`): je Handler ein Minimalteil; Referenz-Suite `tests/referenz/`.
- Kein CI (SolidWorks nötig); Tests laufen lokal auf beiden Rechnern.

## 13. Bewusst nicht enthalten

- Bauen über MCP-Tools; UI-/Agenten-Schicht von SolidworksMCP-python.
- Code aus eyfel/mcp-server-solidworks (AGPL) – nur Konzepte nachgebaut.
- solidworks-api-skill, solidworks-automation, alisamsam/Solidworks-MCP.
- Physikalische Simulation (SOLIDWORKS Motion) und Motion-Study-Animationen.
