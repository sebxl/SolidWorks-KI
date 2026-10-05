# Übergabe für Stufe 4b – mechanische Kopplungen (Stand 2026-10-05)

## Auftrag der nächsten Sitzung
Für **Stufe 4b** zuerst die **Spec** und dann den **Plan** schreiben. Umgesetzt wird erst in einer späteren Sitzung.

1. **superpowers:brainstorming**:
   - Anforderungen und Entscheidungen mit dem Nutzer klären, **eine Frage je Runde, jede mit Empfehlung** (globale
     Vorgabe des Nutzers, `~/.claude/CLAUDE.md`).
   - Danach die Spec schreiben: `docs/superpowers/specs/2026-10-0x-stufe-4b-<thema>-design.md`.
   - Der Nutzer stimmt die Spec ab, bevor der Plan beginnt.
2. **superpowers:writing-plans**:
   - Plan nach `docs/superpowers/plans/2026-10-0x-stufe-4b-<thema>.md`, aufgebaut wie der 4a-Plan
     (`2026-10-03-stufe-4a-bewegungen.md`): „Präzisierungen gegenüber der Spec“, „Global Constraints“, Tabelle
     „Abhängigkeiten vom Spike“ (Annahme / sonst), Spike zuerst, Tasks mit vollständigem Code, Testzahlen je Task.
   - Plan-Code ohne SolidWorks vorab in einem Wegwerf-Worktree prüfen (RED-Fehlerbilder, `swki api pruefe-code`), wie
     vor 4a.
3. Am Ende eine Übergabe für die Umsetzungssitzung (subagent-driven-development) nach dem Muster
   `uebergabe-2026-10-04-stufe4a.md`; CLAUDE.md verweist dann darauf.
4. **Git:**
   - Arbeit auf Branch `plan-stufe-4b` (von `main` @ 91a62f3); dort liegt bereits diese Übergabe.
   - Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
   - **Kein Push ohne Rückfrage.**

## Stand
- `main` steht auf `91a62f3` (Merge PR #11, Fix sporadischer Normbohrungsfehler; davor PR #10 Stufe 4a, `cf6631d`).
  Außer `main` und `plan-stufe-4b` gibt es keine Branches, lokal wie remote.
- **Tests auf `main`:** **711 passed, 117 deselected**; `swki api pruefe-code` ohne Befund.
- **Live auf SOLIDWORKS 2025 (Rechner A), 2026-10-05:** Live-Suite 112/112, Regressions-Suite 5/5 (Buchse, Formplatte,
  Auswerferhalteplatte, Stehlager, Linearschlitten).
- **4a fertig:** Grenzverknüpfungen (`grenze_abstand`/`grenze_winkel`, Seite `a` bewegt, `min`/`max` als Parameter),
  Scharnier (konzentrisch + Anlage), `freiheitsgrade: 1`, `bewegungen` mit Endlagen, Bewegungsprüfung in `swki pruefen`
  (Kollision je Stellung, „Grenze wirkt“, Freiheitsgrad belegt, Paarläufe, Bilder, `SPEICHER_KNAPP`). Verknüpfungen
  werden mit `AddMate5` angelegt (`swki/baugruppe/sw_baugruppe.py`, `MATE_TYP`).
- **Normbohrung (PR #11):** der Handler wiederholt `ForceRebuild3` bis jede Position ihre Bohrung hat (Zeitrennen nach
  dem Schließen der Positionsskizze); Details `docs/stufe4a/ergebnisse.md` Abschnitt 7.

## Pflichtlektüre
- **Design** `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md` §11, Zeile 4b: „Mechanische Kopplungen:
  Zahnrad-, Nut-, Kurvenverknüpfung – Referenz *Schieber mit Schrägbolzen* (Kandidat) besteht“.
- **Spec 4a** `docs/superpowers/specs/2026-10-03-stufe-4a-bewegungen-design.md`: Format `bewegungen`/Grenzen,
  Bewegungsprüfung, §16 „Nicht in 4a“ (u. a. gekoppelte Antriebe, Teilbereiche `von`/`bis`, mehr als ein Freiheitsgrad
  je Komponente).
- **Ergebnisse 4a** `docs/stufe4a/ergebnisse.md`: Abschnitt 2 (Spike S13: nur Maß `D1`, Grenzwerte nicht per Gleichung
  bindbar, Bestimmtheit mit unterdrückten Grenzen lesen, Drehsinn `[0, −1, 0]`, Zeit/Speicher je Schritt, S13c:
  Antriebe vor dem Speichern zerstören die Winkelgrenze), Abschnitt 6 (Abweichungen), **Abschnitt 7 (offene Punkte)**.
- **Skill `baugruppe`** (`.claude/skills/baugruppe/`), §6 Bewegungen; Prüfer-Agent `pruefer`.
- `schema/baugruppe.schema.json` (Verknüpfungstypen, `bewegungen`), `swki/baugruppe/` (Bau, Bewegung, Mechanik).
- `swki/wissen/pywin32-fallstricke.md`; die Spikes `spikes/s13_bewegung.py`, `s13b_bewegung.py`,
  `s13c_winkelgrenze.py` als Ausgangspunkt für den 4b-Spike.

## Nutzervorgaben (gelten weiter)
- **Ausrichtung:** allgemeine Konstruktion mit Volumenkörpern, **nicht Werkzeugbau**; Werkzeugbau-Beispiele nicht als
  Standard vorschlagen (Nutzer, 2026-10-02).
- **Normteile** immer über `swki normteil hole`; Normtabellen nur mit Abgleich (≥ 2 Quellen) erweitern.
- **Freigabe-Prinzip:** der Mensch greift an einer Stelle ein, der Freigabe der Spezifikation.
- **SolidWorks-Neustarts übernimmt Claude selbst** (Ablauf in `uebergabe-2026-10-04-stufe4a.md`); vor jedem Live-Lauf
  mit Bewegungen frisch starten.
- **Keine künstliche CPU-Last ohne Rückfrage** (Nutzer bemerkte 98 % CPU beim Reproduzieren, 2026-10-05).
- Rechner B (SW 2026) bleibt zurückgestellt.

## Offene Entscheidungen für das Brainstorming (Vorschlag, nicht abschließend)
1. **Referenzbaugruppe – zuerst klären.** Das Design nennt den *Schieber mit Schrägbolzen*; das ist ein
   Werkzeugbau-Bauteil (Spritzgießwerkzeug) und widerspricht der Ausrichtung. Allgemeine Alternativen vorschlagen, die
   die gewählten Kopplungen abdecken, z. B. Zahnstangentrieb (Ritzel + Zahnstange auf dem 4a-Schlitten), Stirnradstufe
   mit zwei Wellen im Lagerbock, Kurbelschwinge/Kulisse mit Nutführung, Nockenwelle mit Stößel (Kurve). Möglichst auf 3b/4a
   aufbauen (Stehlager, Linearschlitten).
2. **Umfang der Kopplungen:** welche aus `swMateType_e` – `swMateGEAR` (10), `swMateRACKPINION` (13), `swMateSLOT` (21),
   `swMateCAMFOLLOWER` (9); ggf. `swMateSCREW` (17), `swMateLINEARCOUPLER` (18). Alle in einem Paket oder 4b weiter teilen?
3. **API-Weg:** `AddMate5` (bisheriger Weg, für Kopplungen ungeprüft – Übersetzung/Ratio, Kurvenflächen) oder
   `CreateMate` mit `*MateFeatureData` (z. B. Zahnrad-, Nut-, Kurvendaten). Gehört in den Spike.
4. **Geometrie der gekoppelten Teile:** echte Verzahnung (Evolvente; der Compiler kann sie nicht) oder vereinfachte
   Teilkreis-Zylinder? Folgen für Kollisionsprüfung (Zahneingriff ≠ Kollision) und Prüfer. Kurvenscheibe aus `kontur`
   (Linien + Bögen, Stufe 2c), Nut aus `langloch` – reicht das?
5. **Format:** wie `bewegungen` gekoppelte Komponenten ausdrückt – eine treibende Bewegung, getriebene Komponenten mit
   erwarteter Übersetzung bzw. Kurve; `freiheitsgrade` einer gekoppelten Gruppe (1 gemeinsamer); Übersetzung/Parameter
   in `parameter` (Freigabe schützt sie); Plausibilität (z. B. Übersetzung = Zähnezahlverhältnis/Teilkreise).
6. **Prüfung:** je Stellung die Lage der getriebenen Komponente gegen den Sollweg (Übersetzung, Kurve). Das schließt den
   offenen 4a-Punkt „Kein Nachweis des Sollwegs je Stellung“ (Ergebnisse 4a, Abschnitt 7) – mitnehmen oder getrennt?
7. **Negativfälle** analog 4a (falsche Übersetzung, falsche Drehrichtung, fehlende Kopplung → zweiter Freiheitsgrad,
   Kollision der Kurvenrolle).
8. **Speicher/Zeit:** Spitzen bis ~11 GB Private Bytes in 4a; `speicher_grenze_mb` 10000. Ein Plan für 4b sollte die
   Kosten je Schritt im Spike messen.
9. **Aus 4a mitnehmen oder bewusst liegen lassen** (Abschnitt 7): Prüfbericht ohne Grenz-ID/Bereich, `plausibel` prüft
   nicht, dass `a`/`b` einer Grenze eben sind, uneinheitliche Bewertung abgebrochener Läufe (`endlage` False vs. `grenze`
   None), privater Import in `swki/baugruppe/bewegung.py`, Deferred Minors.

## Erfahrungen (wichtig für Spike und Live-Tasks)
- **Neustart je Bewegungslauf:** zwei Schlitten-Negativfälle nacheinander in einer SolidWorks-Sitzung scheiterten in der
  Live-Suite (2026-10-05); einzeln mit frischem SolidWorks bestanden alle. Live-Tests mit Bewegungen deshalb je Test,
  nicht je Datei, frisch starten.
- **Sporadische Fehler:** ~1 %-Fehler brauchen viele Läufe; bewährt hat sich eine Schleife „Neustart + n × `swki bauen`“
  mit Diagnose nur im Fehlerzweig (Werkzeuge in `auftraege/REPRO-NB/diagnose/`, gitignored).
- **Speicher:** Private Bytes messen, nicht das Working Set; Baugruppenläufe mit Bewegungen 7–11 GB Spitze.
- **Nie zwei Implementer gleichzeitig**, solange SolidWorks läuft.
- **API:** vor jedem neuen Aufruf `swki api methode` / `swki api enum`; Late Binding: nullargumentige Member ohne `()`.
- **Modellwahl:** Abschrift mit vollständigem Code mittleres/günstiges Modell, Live-Tasks und Reviews mittleres,
  Gesamt-Review stärkstes Modell.

## Nicht Teil von 4b (Vorschlag)
- Paket „Messarten“ (Fasen, Gewinde durch, Lagerachse) – bleibt eigene Alternative.
- Motion-Studien, Animationen, Kräfte; Unterbaugruppen; Rechner B.
