# Übergabe für Stufe 3b – Baugruppen statisch (Stand 2026-10-03)

## Auftrag der nächsten Sitzung
Für **Stufe 3b Baugruppen statisch** zuerst die **Spec** und dann den **Plan** schreiben. Umgesetzt wird erst in einer
späteren Sitzung.

1. **superpowers:brainstorming**:
   - Anforderungen und Entscheidungen mit dem Nutzer klären, **eine Frage je Runde, jede mit Empfehlung** (globale
     Vorgabe des Nutzers).
   - Danach die Spec schreiben: `docs/superpowers/specs/2026-10-0x-stufe-3b-baugruppen-design.md`.
   - Der Nutzer stimmt die Spec ab, bevor der Plan beginnt.
2. **superpowers:writing-plans**:
   - Plan nach `docs/superpowers/plans/2026-10-0x-stufe-3b-baugruppen.md`.
   - Mit „Präzisierungen gegenüber der Spec“ und „Global Constraints“ im Kopf, wie bei 3a.
   - Spikes zuerst, Tasks mit vollständigem Code, Testzahlen je Task.
3. Am Ende eine Übergabe für die Umsetzungssitzung (subagent-driven-development), wie
   `uebergabe-2026-10-02-stufe3a.md`.
4. **Git:**
   - Arbeit auf Branch `plan-stufe-3b`; dort liegt bereits diese Übergabe.
   - Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
   - **Kein Push ohne Rückfrage.**

## Stand
- `main` steht auf `04d0c1c` (Merge PR #7, Stufe 3a). Außer `main` gibt es keine Branches, lokal wie remote.
- **Tests:** 456 Unit-Tests grün, `swki api pruefe-code` ohne Befund, `swki normteil tabellen-pruefen` gültig.
- **Live auf SOLIDWORKS 2025 (Rechner A) grün:** alle Live-Tests, darunter die Referenzen Buchse, Formplatte und
  Auswerferhalteplatte, die Normteile, `hole` und die Stichprobe mit 21 Teilen.
- **3a fertig:**
  - Normteile ISO 4762, 4032, 7089 und 8734 kommen über `swki normteil hole`.
  - Jedes Teil hat benannte Einbaureferenzen: `EINBAU_ACHSE`, `EINBAU_EBENE` bzw. `EINBAU_EBENE_1/_2`.
  - Die Lage ist bei allen gleich: Achse = Modell-Y, Auflage auf y = 0.
  - Die Bibliothek liegt unter `<normteilbibliothek>/<sw_jahr>/` und ist ein Cache.
  - Ergebnisse: `docs/stufe3a/ergebnisse.md`.
- Baugruppen sind noch gar nicht umgesetzt.
  - Es gibt nur das Teil-Schema `schema/teil.schema.json`.
  - `config/rechner.yaml` kennt bereits `vorlage_baugruppe`.

## Pflichtlektüre
- **Design** `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`:
  - §4 „Baugruppe“: Entwurf des Formats; die Beispiele dort sind noch werkzeugbaulastig.
  - §6: Baugruppen-Prüfung (Verknüpfungen fehlerfrei, Bestimmtheit gegen erwartete Freiheitsgrade, statische
    Kollision) und Prüfer-Agent.
  - §11: Zeile 3b; „Fertig, wenn“: allgemeine Referenzbaugruppe besteht, Festlegung in der Spec 3b.
- **Spec 3a** `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md`: Einbaureferenzen, Bibliothek, §14.
- **Ergebnisse 3a** `docs/stufe3a/ergebnisse.md`: Spike S11, „Offene Punkte“, zurückgestellte Kleinbefunde (einige
  betreffen 3b, siehe unten).
- **Stufe 0** `docs/stufe0/ergebnisse.md`:
  - S5 Kollision: `AddComponent5` + `InterferenceDetectionManager` / `GetInterferenceCount` funktionieren.
  - S6 Abstand: `AddMate5` mit `swMateDISTANCE`, `SetSystemValue3`, `Transform2`.
  - Offene Punkte: `AddMate5` ist laut Hilfe obsolet (Nachfolger `CreateMate`). `AddComponent5` setzt das **Zentrum
    der Bounding-Box**, nicht den Ursprung.
- `swki/wissen/pywin32-fallstricke.md`: Late Binding, nullargumentige Member ohne `()`.
- Die Spikes `spikes/s5_kollision.py` und `spikes/s6_abstand_verstellen.py` sind die Ausgangspunkte für neue
  Baugruppen-Spikes.

## Nutzervorgaben (gelten weiter)
- **Ausrichtung:** allgemeine Konstruktion mit Volumenkörpern, nicht Werkzeugbau.
  - Die Referenzbaugruppe ist allgemein und wird in der Spec 3b festgelegt; die Säulenführung entfällt.
  - Meusburger- und Werkzeugbau-Beispiele nicht als Standard vorschlagen.
- **Umfang 3b statisch:** Standardverknüpfungen, Bestimmtheit, statische Kollision.
  - Bewegungen, treibende Verknüpfungen und mechanische Verknüpfungen gehören zu **Stufe 4**.
- **Normteile in Baugruppen** kommen immer über `swki normteil hole`, nie als STEP-Download oder freihändig konstruiert.
- **Freigabe-Prinzip:** Der Mensch greift an einer Stelle ein, der Freigabe der Spezifikation (Design §1).
- **SolidWorks-Neustarts übernimmt Claude selbst**, wenn die Private Bytes etwa 4 GB erreichen (Nutzer, 2026-10-03).
  - Ablauf: genau eine Instanz, keine fremden offenen Dokumente, `ExitApp`, Start über `installationsordner`.
  - Danach prüfen: eine Instanz, Fenster sichtbar, Toggle 10 / Integer 6 = `False 1`.
- **Rechner B (SW 2026)** bleibt zurückgestellt.

## Offene Entscheidungen für das Brainstorming (Vorschlag, nicht abschließend)
1. **Referenzbaugruppe.**
   - Allgemein, aus bestehenden Bausteinen: eigene Teile mit Normbohrungen aus 2c und Normteile aus 3a.
   - Beispiel: eine Flanschverbindung oder ein Lagerbock aus Grundplatte und Winkel/Deckel, verschraubt mit
     ISO 4762 + ISO 7089 (+ ISO 4032), zentriert mit ISO-8734-Stiften.
   - Damit wird die Spec-3a-Forderung „Passung Normteil ↔ Normbohrung in der Baugruppe“ prüfbar.
2. **Spezifikationsformat Baugruppe** (`schema/baugruppe.schema.json`):
   - Komponenten mit `quelle: {teil: <spec>}` bzw. `{normteil: "<Norm> <Größe>", variante?}`.
   - Komponenten-IDs, Gruppen, erwartete Freiheitsgrade, `pruefung`.
   - Wiederholungen: z. B. 4 Schrauben als Komponentenmuster an einem Bohrungsmuster oder als einzelne Komponenten.
3. **Referenzen in Verknüpfungen:**
   - Bei Normteilen die Einbaureferenzen `EINBAU_*`.
   - Bei Eigenteilen: benannte `referenz`-Features (seit 3a im Teil-Format), semantische Flächen (`{feature, flaeche}`),
     Bohrungsachsen der Normbohrungen oder Punkt-Anker `nahe`.
   - Wie wählt man Geometrie *in einer Komponente* per Name aus? Spec 3a §10 S11a nennt das, **live geprüft wurde in 3a
     aber nur das Teil, nicht die Auswahl in der Baugruppe**. Das gehört in einen Spike.
4. **Verknüpfungstypen 3b:** deckungsgleich, konzentrisch, parallel, senkrecht, Abstand, Winkel; Ausrichtung
   (gleich/entgegengesetzt). Weg über `AddMate5` (obsolet, live erprobt) oder `CreateMate` (neu, nicht erprobt)? Das
   gehört in einen Spike.
5. **Platzierung:** Den Versatz durch `AddComponent5` (Zentrum der Bounding-Box) herausrechnen oder ausschließlich
   über Verknüpfungen positionieren. Erste Komponente fixiert.
6. **Bestimmtheit:**
   - Wie liest man den Bestimmtheitsstatus bzw. die Freiheitsgrade je Komponente per API aus?
   - Wie geht man mit Rotation um die Achse um (Schraube, Stift, Scheibe)? Das ist bei rotationssymmetrischen
     Normteilen typisch unterbestimmt.
   - Erwartung `freiheitsgrade` je Komponente/Gruppe, oder Rotationssymmetrie bewusst zulassen?
7. **Statische Kollision – wichtig:**
   - Normteile haben den **Nenn-Ø ohne Gewinde**. Eine Schraube in einer Gewindebohrung (Kernloch-Ø < Nenn-Ø)
     überlappt deshalb geometrisch, eine Mutter auf dem Schaft ebenso.
   - Zu klären: erwartete Überlappungen (Gewindepaarungen) zulassen bzw. ausweisen, oder anders modellieren.
   - Zu klären: Kontakt (Berührung) ≠ Kollision; Toleranzen.
8. **Dateien und Speicherorte:**
   - Eigenteile der Baugruppe werden per `swki bauen` erzeugt. Wohin? Wie verweist die Baugruppe auf welchen Lauf?
   - Normteile: Die Baugruppe darf **nie in die Bibliothek schreiben**.
   - `lege_ab` überschreibt Bibliotheksdateien an Ort und Stelle (3a-Review). Eine Baugruppe, die auf die
     Bibliotheksdatei verweist, bekäme still neue Geometrie, und eine in SolidWorks geöffnete Datei blockiert das
     Kopieren.
   - Entscheiden: verweisen oder ins Auftrags-/Arbeitsverzeichnis kopieren.
9. **Prüfung und Prüfer:**
   - `swki pruefen` für Baugruppen: Rebuild, Verknüpfungsfehler, Bestimmtheit, Kollision, ggf. Lage einzelner
     Komponenten per Messung.
   - Screenshots, Prüfer-Agent mit Baugruppen-Checkliste.
   - Freigabe-Prüfsumme über Komponenten und Verknüpfungen (Design §6).
10. **Skill `konstruieren`:** um Baugruppen erweitern oder einen eigenen Skill `baugruppe` anlegen.

## Aus 3a für 3b vormerken (`docs/stufe3a/ergebnisse.md`)
- `EINBAU_EBENE_2` bei ISO 8734 ist nur als Betrag geprüft. Vor der Nutzung in Verknüpfungen gegen +y mit Soll 0
  messen; das braucht eine neue Vorlagenversion und ein neues Prüfer-Urteil.
- Fasen `p` (ISO 4762) und `c` (ISO 8734) werden nicht direkt gemessen; das lässt sich mit derselben neuen
  Vorlagenversion nachholen.
- Plausibilitätsbefunde in `validieren` fehlen noch:
  - Parameter, die sich nur in Groß-/Kleinschreibung unterscheiden (SolidWorks-Gleichungen unterscheiden das nicht).
  - Anker (`flaeche`/`kanten`) auf eine `referenz`-ID.
- Eine Mittellinie mit Endpunkt auf einem Profilpunkt scheitert („Gleichungen: Code 1“). Die Vorlagen umgehen es mit
  überstehender Mittellinie; ein Schutz im Compiler fehlt.
- `teil_pruefsumme` enthält weder Längenreihe noch Status: `liste` zeigt eine gestrichene Länge weiter als aktuell.

## Erfahrungen (wichtig für Spikes und spätere Live-Tasks)
- **Speicher:**
  - Messgröße sind Private Bytes, nicht das Working Set.
  - Der erste Bau nach einem Neustart kostet etwa 1,6 GB, jeder weitere 80–160 MB (Ausreißer bis 420 MB).
  - Ab etwa 4 GB neu starten.
  - Live-Tests dateiweise laufen lassen: `tests\live_einzeln.py <datei> --zeit 240`, Node-IDs werden angenommen.
- **Nie zwei Implementer gleichzeitig**, solange SolidWorks läuft.
- **Bewährtes Muster:** Unit-Teile committen, Live-Teile nachholen, sobald SolidWorks frei ist.
- **Modellwahl:**
  - Abschrift mit vollständigem Code: mittleres Modell, bei kleinen Tasks das günstigste.
  - Live-Tasks und Reviews: mittleres Modell.
  - Gesamt-Review: stärkstes Modell.
- **API:**
  - Vor jedem neuen Aufruf `swki api methode` / `swki api enum` nachschlagen.
  - Late Binding: nullargumentige Member ohne `()`.
  - Normale einer Bezugsebene = `Transform.ArrayData[6:9]`.
- **Web-Recherche mit Agents** (Workflow, zwei getrennte Quellenkreise) hat sich für Normwerte bewährt.

## Nicht Teil von 3b
- Bewegungen und mechanische Verknüpfungen (Stufe 4).
- Kosmetisches Gewinde (mit Zeichnungen, Stufe 5).
- Kaufteile von Herstellern.
- Weitere Normen.
- Rechner B.
