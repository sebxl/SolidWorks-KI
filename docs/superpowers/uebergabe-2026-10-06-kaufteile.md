# Übergabe für das Paket Kaufteile – STEP-Import (Stand 2026-10-06)

## Auftrag der nächsten Sitzung
Für das **Paket Kaufteile (STEP-Import)** zuerst die **Spec** und dann den **Plan** schreiben. Umgesetzt wird erst in
einer späteren Sitzung.

1. **superpowers:brainstorming**:
   - Anforderungen und Entscheidungen mit dem Nutzer klären, **eine Frage je Runde, jede mit Empfehlung** (globale
     Vorgabe des Nutzers, `~/.claude/CLAUDE.md`).
   - Danach die Spec schreiben: `docs/superpowers/specs/2026-10-0x-kaufteile-step-import-design.md`.
   - Der Nutzer stimmt die Spec ab, bevor der Plan beginnt.
2. **superpowers:writing-plans**:
   - Plan nach `docs/superpowers/plans/2026-10-0x-kaufteile-step-import.md`, aufgebaut wie der 4b-Plan
     (`2026-10-05-stufe-4b-verzahnung-kopplungen.md`): „Präzisierungen gegenüber der Spec“, „Global Constraints“,
     Tabelle „Abhängigkeiten vom Spike“ (Annahme / sonst), Spike zuerst, Tasks mit vollständigem Code, Testzahlen je
     Task.
   - Plan-Code ohne SolidWorks vorab in einem Wegwerf-Worktree prüfen (RED-Fehlerbilder, `swki api pruefe-code`), wie
     vor 4a und 4b.
3. Am Ende eine Übergabe für die Umsetzungssitzung (subagent-driven-development) nach dem Muster
   `uebergabe-2026-10-05-stufe4b-umsetzung.md`; CLAUDE.md verweist dann darauf.
4. **Git:**
   - Arbeit auf Branch `plan-kaufteile` (von `main` @ 7f120d0); dort liegt bereits diese Übergabe.
   - Commit-Trailer exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
   - **Kein Push ohne Rückfrage.**

## Stand
- `main` steht auf `7f120d0` (Merge PR #12, Stufe 4b). Außer `main` und `plan-kaufteile` gibt es keine Branches, lokal
  wie remote.
- **Tests auf `main`:** **847 passed, 133 deselected**; `swki api pruefe-code swki spikes tests/live` ohne Befund.
- **Live auf SOLIDWORKS 2025 (Rechner A), 2026-10-06:** Live-Suite 129/129 plus die vier Zahnstangentrieb-Negativfälle;
  Regression Buchse, Formplatte, Auswerferhalteplatte, Stehlager, Linearschlitten, Zahnstangentrieb samt Teilen.
- **Was es schon gibt (Bausteine für Kaufteile):**
  - Normteile (3a): `swki normteil hole` baut genormte Teile selbst, prüft sie und legt sie in der Bibliothek
    `<normteilbibliothek>/<sw_jahr>/` ab (Cache je Rechner und SW-Version). Jedes Normteil hat benannte
    Einbaureferenzen (`EINBAU_ACHSE`, `EINBAU_EBENE` bzw. `EINBAU_EBENE_1/_2`); Lage einheitlich (Achse = Modell-Y,
    Auflage auf y = 0). Code: `swki/normteile/` (`bibliothek.py`, `befehle.py`, `bau.py`).
  - Baugruppen (3b–4b): Komponenten mit `quelle: {teil: <spec>}` oder `{normteil: "<Norm> <Größe>", variante?}`
    (`schema/baugruppe.schema.json`, `$defs/quelle`); Normteile werden in den Lauf-Ordner **kopiert**, die Baugruppe
    verweist nie auf die Bibliothek. Prüfung in `swki pruefen` (Verknüpfungen, Bestimmtheit, Kollision, Lage,
    Teilprüfungen, Bewegungen, Kopplungen).
  - Öffnen fremder Dateien: `app.OpenDoc6` (`swki/pruefung/messen.py`), Speichern als STEP über
    `IModelDocExtension.SaveAs3` (Spike S9b) – damit lassen sich eigene Test-STEP-Dateien ohne Lizenzfragen erzeugen.
  - Änderungserkennung (`MANUELL_GEAENDERT`, `swki aenderungen`) für gebaute Teile und Baugruppen.
- **Kaufteile gibt es noch gar nicht.** `swki normteil aufnehmen` aus dem Gesamtdesign ist nicht umgesetzt; es gibt
  keinen Katalog, keinen Importweg und keine Komponentenquelle `kaufteil`.

## Pflichtlektüre
- **Design** `docs/superpowers/specs/2026-09-26-solidworks-ki-design.md`:
  - Abschnitt Normteile (ab „Stand Stufe 3a“, ~Z. 266–281): Katalog je Hersteller (`id`, `benennung`, `typ`,
    `kennmasse`, `quelle`, `einbau`, `eigenschaften`), `swki normteil aufnehmen <sldprt|step>` (importiert, legt
    Einbaureferenzen an „mit Claude“, speichert nur in SW 2025, trägt in den Katalog ein). Das ist der Ausgangsentwurf.
  - Versionsregeln (~Z. 83–90): Dateien nur unter SW 2025 in Bibliotheken speichern (2026-Dateien in 2025 nicht lesbar).
  - §6 Prüfung, §11 Stufen (Kaufteile stehen dort nicht als eigene Stufe; die Spec legt fest, wo sie einsortiert werden).
- **Spec 3a** `docs/superpowers/specs/2026-10-02-stufe-3a-normteile-design.md`: Entscheidungstabelle („Herstellerdaten
  nur für nicht genormte Kaufteile; nicht in 3a, eigenes Paket bei Bedarf“), Einbaureferenzen, Bibliothek, Prüfer je
  Vorlage.
- **Spec 3b** `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md`: Komponentenquellen, Kopie in den
  Lauf-Ordner, Referenzformen in Verknüpfungen (`referenz: EINBAU_*`), Änderungserkennung.
- **Ergebnisse** `docs/stufe3a/ergebnisse.md`, `docs/stufe4b/ergebnisse.md` (Speicher, Laufzeiten, offene Punkte).
- `swki/wissen/pywin32-fallstricke.md`: Late Binding, nullargumentige Member ohne `()`.
- Im API-Index (nachschlagen, nicht raten): u. a. `ISldWorks.LoadFile4` (2 Parameter laut Index), `ISldWorks.GetImportFileData`
  (1 Parameter), `ISldWorks.OpenDoc6`, die STEP-Importdaten (`IImportStepData`), Bezugsachsen/-ebenen (`InsertAxis2`,
  `InsertRefPlane`), Import-Diagnose. Alles davon ist live noch nicht erprobt → Spike.

## Nutzervorgaben (gelten weiter)
- **Ausrichtung:** allgemeine Konstruktion mit Volumenkörpern, nicht Werkzeugbau. Referenz-Kaufteile allgemein (z. B.
  Motor mit Flansch, Kugellager, Linearführung, Pneumatikzylinder) – keine Meusburger-/Werkzeugbau-Normalien als Standard.
- **Genormte Teile** (Schrauben, Muttern, Scheiben, Stifte) kommen weiter **immer** über `swki normteil hole` – nie als
  STEP-Download. STEP-Import gilt **nur für nicht genormte Kaufteile** (Herstellerdaten).
- **Nur Dokumente anfassen, die selbst angelegt wurden; speichern nur im Arbeitsordner bzw. in Bibliotheken des
  Projekts** – nie in Kundenordner oder Originaldateien des Nutzers schreiben. Eine STEP-Quelldatei wird nur gelesen.
- **Freigabe-Prinzip:** Der Mensch greift an einer Stelle ein (Design §1). Für Kaufteile in der Spec klären, ob und wo
  der Nutzer bestätigt (Normteile brauchen keine Nutzerfreigabe, nur ein Prüfer-Urteil je Vorlage).
- **SolidWorks-Neustarts übernimmt Claude selbst** (Ablauf in `uebergabe-2026-10-05-stufe4b-umsetzung.md`); vor jedem
  Live-Lauf mit Baugruppe frisch starten.
- **Keine künstliche CPU-Last ohne Rückfrage.** Rechner B (SW 2026) bleibt zurückgestellt (Plane SWKI-3).
- Kommunikation auf Deutsch; Fragen einzeln, jede mit Empfehlung.

## Offene Entscheidungen für das Brainstorming (Vorschlag, nicht abschließend)
1. **Umfang und Formate.** Nur STEP (AP203/AP214/AP242) oder auch IGES/Parasolid/SLDPRT des Herstellers? Einzelteil-STEP
   oder auch Baugruppen-STEP (Motor als mehrteilige Baugruppe) – als Mehrkörperteil importieren, als Unterbaugruppe
   (bisher nicht unterstützt) oder ablehnen?
2. **Woher kommen die Dateien?** Herstellerportale verlangen oft ein Konto – Claude legt keine Konten an und meldet sich
   nicht an. Vorschlag: Der Nutzer legt die Datei in `auftraege/<auftrag>/eingabe/` bzw. einen Quellordner; Claude liest
   nur. Lizenz/Herkunft im Katalog festhalten. **Testdaten** ohne Lizenzfragen: per `SaveAs3` aus eigenen Teilen erzeugte
   STEP-Dateien (deterministisch, im Repo ablegbar).
3. **Ablage und Katalog.** Eigene Bibliothek je Rechner/SW-Version (z. B. `kaufteilbibliothek` in `config/rechner.yaml`)
   wie die Normteilbibliothek, oder gemeinsame Bibliothek? Katalog `swki/wissen/kaufteile/<hersteller>.yaml` (im Git) mit
   Bestellnummer, Benennung, Kennmaßen, Prüfsumme der Quelldatei. Speichern nur unter SW 2025 (Versionsregel).
4. **Aufnahme-Ablauf (`swki kaufteil aufnehmen`?).** Import → Diagnose (Körperzahl, offene/fehlerhafte Flächen,
   Einheiten) → Lage normalisieren oder nicht → Einbaureferenzen anlegen → Prüfung → Prüfer → Katalogeintrag. Wo stehen
   die Angaben, die Claude dafür braucht (eine kleine Aufnahme-Spec je Kaufteil als YAML, freigegeben wie eine Teil-Spec)?
5. **Einbaureferenzen an fremder Geometrie.** Wie benennt man Achse/Ebenen reproduzierbar (Zylinderfläche mit Ø x nahe
   Punkt p, ebene Fläche mit Normale n …), sodass ein erneuter Import dieselben Referenzen findet? Bezugsachse/-ebene im
   Teil anlegen (`InsertAxis2`/`InsertRefPlane`) und als `EINBAU_*` benennen, wie bei Normteilen.
6. **Prüfung ohne Spec-Geometrie.** Was ist prüfbar: Import fehlerfrei, ein Volumenkörper (oder erwartete Anzahl),
   Hüllquader und Kennmaße gegen Datenblatt (z. B. Wellen-Ø, Flansch-Lochkreis, Zentrierbund), Lage der Einbaureferenzen
   zueinander, Masse (STEP hat keine Masse: Material setzen oder Masse aus dem Datenblatt überschreiben?), Bilder für den
   Prüfer. Änderungserkennung über die Prüfsumme der Quelldatei.
7. **Baugruppen-Format.** Neue Komponentenquelle, z. B. `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}`, Kopie in
   den Lauf-Ordner wie Normteile; Verknüpfungen über `referenz: EINBAU_*`. Wirkt sich auf Plausibilität, Freigabe-
   Prüfsumme, Stückliste und Teilprüfungen aus.
8. **Kollision und Kontakt.** Kaufteile sind oft vereinfacht oder detailliert (Gewinde, Rändel). Erwartete Überlappungen
   (z. B. Welle in der Kupplungsnabe) wie Gewindepaarungen ausweisen?
9. **Speicher und Zeit.** Detaillierte Herstellerdaten können groß sein; Speicherspitzen liegen schon heute bei 10–11 GB
   (Plane SWKI-2). Grenzen für Dateigröße/Flächenzahl? Vereinfachen (Defeature) ist eher nicht Umfang.
10. **Referenz.** Allgemein, aus bestehenden Bausteinen erweiterbar, z. B. ein Getriebe-/Schrittmotor mit Flansch auf
    einem Lagerbock (Wellenkupplung zur Antriebswelle des Zahnstangentriebs) oder eine Linearführung (Schiene + Wagen)
    unter dem Schlitten. Die Datei muss der Nutzer liefern oder sie wird aus einem eigenen Ersatzteil als STEP erzeugt.
11. **Einordnung.** Eigenes Paket (Vorschlag „Paket Kaufteile“) oder Stufe 3c; Zeile im Gesamtdesign §11 nachziehen.

## Erfahrungen (wichtig für Spikes und spätere Live-Tasks)
- **Speicher:** Private Bytes messen (0,5-s-Abtastung), nicht das Working Set. Teile 3–4 GB Spitze, Baugruppen mit
  Bewegung 8–11 GB. `speicher_grenze_mb` 10000 greift nur am Dauerniveau. Vor jedem Baugruppen-Live-Lauf frisch starten.
- **COM ist teuer:** jeder Aufruf ~10–16 ms (4b: Skizzenpunkte einzeln umgerechnet = Minuten). Massenhafte Aufrufe
  bündeln oder in Python rechnen.
- **Spikes messen, Controller entscheidet:** Abweichungen je Zeile der Tabelle „Abhängigkeiten vom Spike“ mit Ruling im
  Ledger; Messmethoden kritisch prüfen (4b: IMeasure maß nicht W_k; eine Probe-Methode lieferte ein Scheinergebnis).
- **API:** vor jedem neuen Aufruf `swki api methode`/`enum`; Late Binding; nullargumentige Aktionen über
  `_FlagAsMethod`/`sw_baugruppe.rufe`.
- **Nie zwei Implementer gleichzeitig**, solange SolidWorks läuft. Regression/Live-Suite kann der Controller per Skript
  fahren (Neustart vor jedem Baugruppen-Test); Test-IDs mit Leerzeichen sauber übergeben.
- **Modellwahl:** Abschrift mit vollständigem Code günstiges Modell, Live-Tasks und Reviews mittleres, Gesamt-Review
  stärkstes Modell.

## Nicht Teil des Pakets
- Formschräge (eigenes späteres Paket; Design §11 Stufe 5, Teil-Feature über `compiler-erweitern`).
- Genormte Teile als STEP (bleiben bei `swki normteil hole`).
- Bearbeiten/Ändern importierter Geometrie (Feature-Erkennung, Defeature), Zeichnungen.
- Stufe 4c (Nut, Kurve), Paket „Messarten“, Paket Speicher (SWKI-1/SWKI-2) – eigene Pakete.
- Rechner B (SW 2026).
