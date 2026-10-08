---
name: baugruppe
description: Konstruiert eine Baugruppe (statisch oder mit begrenzten Bewegungen) in SolidWorks aus Eigenteilen und Normteilen – Teil-Specs und Baugruppen-Spec schreiben, validieren, eine Freigabe, bauen, prüfen (Verknüpfungen, Bestimmtheit, Kollision, Gewinde, Lage, Teilprüfungen), Prüfer, nachbessern, Bericht. Verwenden, wenn der Nutzer mehrere Teile zusammenbauen, verschrauben, verstiften oder eine Baugruppe ändern will.
---

# Baugruppe (Stufe 3b, Kaufteile Stufe 3c, Bewegungen Stufe 4a, Kopplungen Stufe 4b)

Spec: `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md` (Abweichungen der Umsetzung: `docs/stufe3b/ergebnisse.md`).
Befehle wie beim Teil (`.venv\Scripts\python.exe -m swki …`, JSON). Längen mm, Winkel Grad. Vorlage: `tests/referenz/stehlager/`.

## 1. Auftrag
- `auftraege/<auftrag>/` mit `eingabe/`, einer Baugruppen-Spec und den Teil-Specs der Eigenteile (Teil-Format,
  Regeln aus dem Skill `konstruieren`, Abschnitt 2).
- Normteile nie als Teil-Spec: in der Baugruppe als `quelle: {normteil: "<Norm> <Größe>"}` (Skill `normteile`).
- Nicht genormte Kaufteile nie als Teil-Spec: `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}` aus dem Katalog
  (Skill `kaufteile`; Regeln für Baugruppen in Abschnitt 8 dieses Skills).

## 2. Baugruppen-Spec
- `komponenten`: `id`, `quelle` (`{teil: <datei.yaml>}` | `{normteil: "ISO 4762 M8x30", variante?}` | `{kaufteil: "<Hersteller> <Bestellnummer>"}`
  Skill `kaufteile`, Abschnitt 8), genau eine
  `fixiert: true` (ihr Ursprung = Baugruppenursprung), `je_position: {komponente, feature}` für eine Instanz je
  Position einer `normbohrung`/`bohrung` (Instanzen `<id>.1 …`).
- `verknuepfungen`: `deckungsgleich`, `konzentrisch`, `parallel`, `senkrecht`, `abstand` (`wert`), `winkel` (`wert`).
  `ausrichtung: gleich | entgegengesetzt` (Normalen nach dem Verknüpfen gleich- bzw. gegensinnig; Flächennormalen
  zeigen aus dem Material, Bezugsebenen haben die Normale ihrer Basis) – Pflicht bei `deckungsgleich`, `parallel`, `abstand`
  und `winkel`; bei `konzentrisch` optional, bei `senkrecht` entfällt sie.
- Referenzen: `{komponente, referenz}` (bei Normteilen nur `EINBAU_*`, Tabelle im Skill `normteile`),
  `{komponente, feature, flaeche}`, `{komponente, feature, instanz, achse}`, `{komponente, feature, instanz, flaeche}`
  (z. B. Senkungsgrund), `{komponente, ebene}`, `{komponente, nahe}` (Teilkoordinaten, nur als Rückfall).
  `instanz: je` = Position der jeweiligen Instanz.
- Flächen, die ein späteres Feature teilt (Trennfläche mit Lagerbohrung), über ein benanntes `referenz`-Feature der
  Teil-Spec ansprechen.
- Je Normteil: **Ebene (mit `ausrichtung`) vor Achse** (erst die Auflage, dann `konzentrisch`). `konzentrisch` ohne
  `ausrichtung` legt swki mit „nächstliegend“ an: SolidWorks behält dann die Richtung, die die Ebene schon festgelegt
  hat. Legt man die Achse zuerst oder widersprechen sich zwei Ausrichtungen, kehrt SolidWorks die Ausrichtung einer
  früheren Verknüpfung **still** um (Spike S12); `swki bauen` erkennt das beim Rücklesen für Verknüpfungen mit
  **ausdrücklicher** `ausrichtung` (eine `konzentrisch` ohne Angabe, die vor der Ebene steht, wird ohne Meldung der
  später festgelegten Ebene angepasst) und bricht mit
  `VERKNUEPFUNG_FEHLER` „<id> kehrt die Ausrichtung von <name> um“ ab. Dann die Ausrichtung der genannten Verknüpfung
  bzw. der neuen prüfen (sie widersprechen sich) oder die Reihenfolge ändern (Ebene vor Achse).
- `drehung_sperren` ist bei Normteilen Vorgabe – jede Komponente muss voll bestimmt sein (sonst
  `freiheitsgrade: {<id>: unterbestimmt}` mit Begründung beim Nutzer).
- Ein Eigenteil richtet man mit Auflage + **einer** konzentrischen Bohrung + `parallel` aus (bewährt im Stehlager).
  Widersprechen sich Verknüpfungen, bricht `swki bauen` mit `VERKNUEPFUNG_FEHLER` ab (SolidWorks meldet Status 5 bzw.
  Fehlercode 47 in der Meldung) und löscht die Verknüpfung: Verknüpfung oder Reihenfolge nachbessern. Ist eine Komponente
  trotz angelegter Verknüpfungen über- oder unterbestimmt, meldet `swki pruefen` den Mangel `bestimmtheit`.
- Eine fixierte Komponente ist ein Mangel, wenn sie nicht fixiert ist **oder** ihr Status überbestimmt ist.
- Anforderungen als `parameter` (`wert: "=S"`); `pruefung`: `huellquader`, `masse_pruefen` (Messpunkte mit
  `komponente`, bei `je_position` die Instanz `stift.1`), optional `masse` (kg). Kollision, Bestimmtheit, Stückliste
  und Teilprüfungen laufen immer.

## 3. Validieren, Freigabe
- `swki validieren <baugruppe.yaml>` (prüft auch alle Teil-Specs, die Normteile und die Passung Normteil ↔ Bohrung)
  bis `"gueltig": true`; `hinweise` abarbeiten wie beim Teil.
- Dem Nutzer zeigen: Teile (Parameter, Material), Normteile (Norm, Größe, Variante, Anzahl), Verknüpfungen in Worten,
  Prüfwerte. Erst nach ausdrücklichem OK: `swki freigeben <baugruppe.yaml>` – **eine** Freigabe für alles.
- Verknüpfungen sind Bauweg (nachbesserbar); Komponenten, Parameter, `freiheitsgrade`, `pruefung` und die
  Anforderungen der Teil-Specs nicht (sonst `FREIGABE_VERALTET`).

## 4. Bauen, prüfen, Prüfer
- `swki bauen <baugruppe.yaml>`: baut alle Eigenteile frisch, holt die Normteile, kopiert sie in den Lauf, fügt ein,
  verknüpft. Fehlercodes (die `meldung` nennt Komponente bzw. Verknüpfung):
  - `TEIL_BAU` (Knoten `<komponente>/<feature>`): Bauweg der Teil-Spec nachbessern.
  - `KOMPONENTE_FEHLER`: Einfügen oder Fixieren einer Komponente gescheitert (Komponente und Datei in der Meldung).
  - `VERKNUEPFUNG_FEHLER`, `REFERENZ_NICHT_GEFUNDEN`, `REFERENZ_MEHRDEUTIG` (Knoten `v<n>[.<i>]`): Referenz,
    Ausrichtung oder Reihenfolge nachbessern; „kehrt die Ausrichtung von … um“ siehe Abschnitt 2.
  - `SCHLIESSEN_FEHLER`: Schließen eines Dokuments nach dem Bau scheitert (ohne früheren Fehler); SolidWorks prüfen
    (offene Dokumente, Speicher), neu bauen.
  - Normteil-Codes wie im Skill `normteile`, Kaufteil-Codes (`KAUFTEIL_*`) wie im Skill `kaufteile`, Abschnitt 5.
- **`MANUELL_GEAENDERT`:** jemand hat Dateien des letzten Laufs geändert. `swki aenderungen <spec>` zeigt die
  Parameterdifferenz. Dem Nutzer zeigen und fragen (eine Frage, Empfehlung „übernehmen“): übernehmen → Spec ändern,
  validieren, Nutzer-OK, `swki freigeben`, dann `swki bauen --uebernommen` (verweigert mit
  `UEBERNAHME_OHNE_NEUE_FREIGABE`, solange die Freigabe nicht neuer als der Lauf ist); verwerfen → nur auf
  ausdrückliche Anweisung `swki bauen --verwerfen`. Beide Schalter nie zugleich. An der Kopie eines **Kaufteils**
  (Herstellergeometrie, importiert) gibt es kein „übernehmen“: nur verwerfen, und zwar erst nach Nutzer-OK.
- `swki pruefen <baugruppe.yaml>` → Prüfbericht mit `verknuepfungen`, `bestimmtheit`, `stueckliste`, `kollision`,
  `gewinde:<schraube>` (Einschraublänge, Volumen ist/soll), `mass:*`, `huellquader`, Teilprüfungen
  `<komponente>: <prüfung>`.
- Prüfer-Agent (`subagent_type: pruefer`) mit Eingabeordner, allen freigegebenen Specs (Baugruppe und Teile),
  Prüfbericht und Screenshot-Ordner; Urteil unverändert nach `protokolle/<spec>.lauf-<n>.pruefer.json`.
- **Speicher:** Ein Baugruppenlauf (Bau + Prüfen) kostet SolidWorks mehrere GB (Stehlager 3,1–3,6 GB Private Bytes).
  Nach jedem Baugruppenlauf die Private Bytes von `SLDWORKS.exe` prüfen
  (`Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`); ab ca. 4 GB
  SolidWorks selbst neu starten, nicht den Nutzer fragen: `.venv\Scripts\python.exe -m werkzeuge.sw_neustart` (prüft
  genau eine Instanz und keine offenen Dokumente, beendet per `ExitApp`, startet aus `installationsordner`, meldet
  Instanzen und Einstellungen Toggle 10 / Integer 6 als JSON; `einstellungen_ok` muss `true` sein). Live-Serien je Test
  auf frischem SolidWorks: `-m werkzeuge.live_frisch`.

## 5. Schleife und Bericht
- `swki status <spec>` und `swki bericht <spec>` wie beim Teil (Skill `konstruieren`, Abschnitte 6–7).
- Nachbessern nur am Bauweg; hält Claude eine Anforderung für falsch (z. B. Schraube zu lang), den Nutzer fragen.

## 6. Bewegungen (Stufe 4a)

Bewegliche Komponenten bekommen eine **Grenzverknüpfung** und `freiheitsgrade: 1`; jede Bewegung nennt ihre Grenze.
Spec: `docs/superpowers/specs/2026-10-03-stufe-4a-bewegungen-design.md` (Abweichungen der Umsetzung: `docs/stufe4a/ergebnisse.md`).
Vorlage: `tests/referenz/schlitten/`.

- `grenze_abstand` (mm) / `grenze_winkel` (Grad): `a`, `b` (ebene Flächen), `ausrichtung` (Pflicht), `min`, `max`.
  **Bewegt wird Seite `a`.** `min`/`max` sind `0` oder Parameter (`"=HUB"`); eine feste Zahl ist ein Befund
  (`GRENZE_FESTE_ZAHL`), weil nur Parameter von der Freigabe geschützt werden.
- `scharnier`: `a`, `b` sind Achsen (Bohrungsachse bzw. `EINBAU_ACHSE` des Drehbolzens); `anlage_a` ist eine ebene
  Fläche der drehenden Komponente (`a`), `anlage_b` die Fläche, auf der sie aufliegt – die Anlage nicht vergessen, sonst
  ist die Höhe frei. swki legt `konzentrisch` (ohne
  Drehsperre) und `deckungsgleich` (`<id>.anlage`) an. Ein Drehbolzen ISO 8734 braucht auf der drehenden Seite eine
  `bohrung` mit Ø > d.
- `freiheitsgrade: {<komponente|gruppe>: 1}`; genau eine Bewegung treibt sie.
- `bewegungen`: `{name, grenze, schritte?, erwartet: {endlagen: [...]}}`. Endlagen als `verschiebung: [x, y, z]` (mm)
  oder `drehung: {achse, winkel}` (Grad, Rechte-Hand-Regel) in Baugruppenkoordinaten, Differenz zwischen `min` und
  `max`. Mitfahrende Komponenten als eigene Endlage eintragen (z. B. der Hebel auf dem Schlitten).
- **Drehsinn** (gemessen, Spike S13 Zeile 7): Beispiel Hebel/Schlitten: Winkelgrenze an den Flächen +z (Hebel) /
  +z (Schlitten), `gleich`, gemessener Drehsinn −y: 0 → 90° dreht den Hebel um
  [0, −1, 0] (+x → +z). Den Drehsinn einer neuen
  Anordnung nicht raten, sondern aus der Eingabe ableiten und als Endlage eintragen; scheitert die Endlage, ist das ein
  Befund (Bauweg prüfen), nie die Erwartung nachträglich anpassen.
- `bauen` legt jede Grenze mit dem Wert `min` an – das ist die Grundstellung; `bauen` prüft sie über das Maß der Grenze
  (Knoten `grundstellung:<Bewegung>`). Beim Bau keine Hilfsverknüpfungen: zwei treibende Verknüpfungen vor dem Speichern
  machen eine Winkelgrenze in der Datei unbrauchbar (Spike S13c).
- `pruefen` fährt jede Bewegung in `schritte + 1` Stellungen ab (Vorgabe `bewegung_schritte` ist 8) und prüft Kollision je
  Stellung, „Grenze wirkt“, „Freiheitsgrad belegt“ und die Endlagen; Bewegungen mit sich schneidenden Räumen zusätzlich
  gegeneinander (Paarläufe). Mängel: `freiheitsgrad:<k>`, `bewegung:<name>`, `bewegung_kollision:<name>`,
  `grenze:<name>`, `endlage:<name>:<k>`. Bilder `<Bewegung>-min|mitte|max` und `<Bewegung>-kollision-…`.
- **Speicher:** Die Bewegungsprüfung braucht auf Rechner A bis ~11 GB Private Bytes (gemessene Spitzen: Stehlager
  10,8 GB, Schlitten 9,9–10,2 GB; die Abfrage vor jedem Lauf sieht nur das Dauerniveau); vor jedem Baugruppenlauf mit
  Bewegungen frisches SolidWorks; `speicher_grenze_mb` 10000 (Nutzerentscheidung 2026-10-04).
- **Fehler der Bewegungsprüfung sind Mängel:** Rebuild-/Verknüpfungsfehler im Lauf-Dokument (die Bewegungsprüfung läuft
  dann nicht, `bewegung:<name>` mit `ok=None`) und Fehler in den Läufen (`bewegung:<name>` mit `ok=False`) landen im
  Prüfbericht; nachbessern wie jeden Mangel. Nur `SPEICHER_KNAPP` bricht ab.
- **`SPEICHER_KNAPP`** (Exit 1, kein Prüfbericht): SolidWorks selbst neu starten und `swki pruefen` erneut aufrufen;
  scheitert es auch frisch, dem Nutzer melden.
- Ab vier Bewegungen meldet `validieren` den Hinweis `pruefaufwand` – mit dem Nutzer klären, ob alle nötig sind.

## 7. Kopplungen (Stufe 4b)

Zahnrad- und Zahnstangenverknüpfung koppeln die Drehung von Wellen an eine Bewegung.
Spec: `docs/superpowers/specs/2026-10-05-stufe-4b-verzahnung-kopplungen-design.md` (Abweichungen der Umsetzung:
`docs/stufe4b/ergebnisse.md`). Vorlage: `tests/referenz/zahnstangentrieb/`.

- `zahnrad` (a und b Stirnräder) und `zahnstange` (a Ritzel, b Zahnstange); beide Seiten als `{komponente, feature}` auf
  ein Verzahnungs-Feature, gleiche Module. Keine Übersetzung angeben: swki leitet sie aus den Zähnezahlen ab.
- Seite `a` wird beim Bau um ihre Achse gedreht, bis Zahn in Lücke steht: `a` braucht `freiheitsgrade: gekoppelt` und
  ist Seite a nur einer Kopplung; `b` steht fest (fixiert, Teil der bewegten Gruppe oder Seite a einer früheren
  Kopplung). Kopplungen stehen nach allen anderen Verknüpfungen ihrer Komponenten (`KOPPLUNG_REIHENFOLGE`).
- Gekoppelte Wellen: Scharnier (Achse + Anlage) im Lager und `freiheitsgrade: {<welle>: gekoppelt}`; eine Zahnstange, die
  mit dem Schlitten fährt, kommt mit ihm in eine Gruppe mit `1`.
- Endlagen: jede gekoppelte Komponente braucht in der treibenden Bewegung eine Endlage `drehung` (`ENDLAGE_FEHLT`), Winkel
  als Ausdruck mit `pi` – Zahnstange: Weg·360/(π·m·z), Zahnrad: Winkel·z_a/z_b. `validieren` vergleicht die Beträge mit der
  Übersetzung (`UEBERSETZUNG_WIDERSPRUCH`). Den Drehsinn aus der Geometrie ableiten (Außenräder gegensinnig; Ritzel:
  Rechte-Hand-Regel mit der Fahrrichtung am Wälzpunkt) und nie nachträglich an eine Messung anpassen. Je Schritt weniger als
  180° Drehung (`SCHRITTE_ZU_GROB` nennt die nötige Schrittzahl).
- `bauen`: Knoten `zahnphase:<id>` vor jeder Kopplung, Fehler `ZAHNPHASE_FEHLER` (Phase nicht herstellbar – Lage der
  Komponenten bzw. Achsen prüfen).
- `pruefen`: `eingriff:<id>` (Achslage, Achsabstand, Überdeckung der Zahnbreiten, Wälzpunkt auf der Zahnstange,
  zurückgelesene Übersetzung), Kollision im Eingriff streng (Flankenspiel kommt aus `zahndickenabmass`),
  `freiheitsgrad:<welle>`, `sollweg:<Bewegung>:<k>` je Stellung (für alle Bewegungen, auch ohne Kopplung), Bilder
  `<id>-eingriff`; das Eingriffsbild blendet die übrigen Komponenten aus, damit der Eingriff nicht verdeckt ist.
  Unterdrückte Verknüpfungen meldet `verknuepfungen` als fehlerhaft.
- Speicher und Neustart wie §6: Live-Läufe mit Kopplungen je Test auf frischem SolidWorks.

## 8. Kaufteile (Stufe 3c)

Nicht genormte Kaufteile kommen aus dem Katalog (Skill `kaufteile`). Spec:
`docs/superpowers/specs/2026-10-06-kaufteile-step-import-design.md`. Vorlage: `tests/referenz/motorhalter/`.

- `quelle: {kaufteil: "<Hersteller> <Bestellnummer>"}`; der Eintrag muss freigegeben sein und ein bestandenes
  Prüfer-Urteil haben (`KAUFTEIL_NICHT_FREIGEGEBEN`, `KAUFTEIL_UNGEPRUEFT` als Befunde von `validieren`).
- Referenzen nur `{komponente, referenz: EINBAU_*}` (Namen aus dem Eintrag) und `{komponente, gewinde, instanz, achse: true}`
  (Achse einer Gewindeposition); nie `feature`, `ebene` oder `nahe` in fremder Geometrie. `je_position: {komponente,
  gewinde}` erzeugt eine Instanz je Gewindeposition (in der Reihenfolge der `positionen` des Eintrags); meist genügt aber
  `je_position` auf die Bohrungen des Gegenstücks. `{gewinde, instanz}` und `je_position: {gewinde}` sind unit-getestet,
  aber noch nicht live erprobt – erster Einsatz mit Prüfer und Sichtprobe.
- Bei `konzentrisch` auf `EINBAU_ACHSE` eines Kaufteils keine `ausrichtung` angeben (die Achsrichtung legt SolidWorks fest,
  Spec 3c §4.2); die Orientierung legt die Anlagefläche (`ebene`) fest.
- Reihenfolge wie bei Normteilen: Anlagefläche (`deckungsgleich` mit `ausrichtung`), dann Achse (`konzentrisch`), dann die
  Drehlage (`parallel`/`winkel` auf die `ebene_durch_achse`). Mit Drehlage `drehung_sperren: false` an der Achse.
- Passung: ISO 4762 nur in Kaufteil-Gewinde gleicher Größe (`validieren`). `pruefen` rechnet die Gewindepaarung mit der
  Gewindetiefe des Eintrags und dem gemessenen Gewinde-Ø (Bericht: Spalte „Gewindemodell“); Kaufteile bekommen keine
  Teilprüfung (sie wurden bei der Aufnahme geprüft), der Bericht nennt Cache-Prüfsumme, Masse (Datenblatt oder Material)
  und Belegstand.
- Ändert sich ein Eintrag nach der Baugruppen-Freigabe: `FREIGABE_VERALTET` mit dem Kaufteil – Nutzer fragen, neu freigeben.
- Speicher: der Motorhalter (mit Kaufteil-Import) hat Spitzen ~9,1–9,3 GB; Live-Läufe wie §6 auf frischem SolidWorks.
