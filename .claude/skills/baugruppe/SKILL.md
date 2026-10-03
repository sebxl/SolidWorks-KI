---
name: baugruppe
description: Konstruiert eine statische Baugruppe in SolidWorks aus Eigenteilen und Normteilen – Teil-Specs und Baugruppen-Spec schreiben, validieren, eine Freigabe, bauen, prüfen (Verknüpfungen, Bestimmtheit, Kollision, Gewinde, Lage, Teilprüfungen), Prüfer, nachbessern, Bericht. Verwenden, wenn der Nutzer mehrere Teile zusammenbauen, verschrauben, verstiften oder eine Baugruppe ändern will.
---

# Baugruppe (statisch, Stufe 3b)

Spec: `docs/superpowers/specs/2026-10-03-stufe-3b-baugruppen-design.md` (Abweichungen der Umsetzung: `docs/stufe3b/ergebnisse.md`).
Befehle wie beim Teil (`.venv\Scripts\python.exe -m swki …`, JSON). Längen mm, Winkel Grad. Vorlage: `tests/referenz/stehlager/`.

## 1. Auftrag
- `auftraege/<auftrag>/` mit `eingabe/`, einer Baugruppen-Spec und den Teil-Specs der Eigenteile (Teil-Format,
  Regeln aus dem Skill `konstruieren`, Abschnitt 2).
- Normteile nie als Teil-Spec: in der Baugruppe als `quelle: {normteil: "<Norm> <Größe>"}` (Skill `normteile`).

## 2. Baugruppen-Spec
- `komponenten`: `id`, `quelle` (`{teil: <datei.yaml>}` | `{normteil: "ISO 4762 M8x30", variante?}`), genau eine
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
  - Normteil-Codes wie im Skill `normteile`.
- **`MANUELL_GEAENDERT`:** jemand hat Dateien des letzten Laufs geändert. `swki aenderungen <spec>` zeigt die
  Parameterdifferenz. Dem Nutzer zeigen und fragen (eine Frage, Empfehlung „übernehmen“): übernehmen → Spec ändern,
  validieren, Nutzer-OK, `swki freigeben`, dann `swki bauen --uebernommen` (verweigert mit
  `UEBERNAHME_OHNE_NEUE_FREIGABE`, solange die Freigabe nicht neuer als der Lauf ist); verwerfen → nur auf
  ausdrückliche Anweisung `swki bauen --verwerfen`. Beide Schalter nie zugleich.
- `swki pruefen <baugruppe.yaml>` → Prüfbericht mit `verknuepfungen`, `bestimmtheit`, `stueckliste`, `kollision`,
  `gewinde:<schraube>` (Einschraublänge, Volumen ist/soll), `mass:*`, `huellquader`, Teilprüfungen
  `<komponente>: <prüfung>`.
- Prüfer-Agent (`subagent_type: pruefer`) mit Eingabeordner, allen freigegebenen Specs (Baugruppe und Teile),
  Prüfbericht und Screenshot-Ordner; Urteil unverändert nach `protokolle/<spec>.lauf-<n>.pruefer.json`.
- **Speicher:** Ein Baugruppenlauf (Bau + Prüfen) kostet SolidWorks mehrere GB (Stehlager 3,1–3,6 GB Private Bytes).
  Nach jedem Baugruppenlauf die Private Bytes von `SLDWORKS.exe` prüfen
  (`Get-Process SLDWORKS | Select-Object Id,@{n='Privat_MB';e={[int]($_.PrivateMemorySize64/1MB)}}`); ab ca. 4 GB
  SolidWorks selbst neu starten, nicht den Nutzer fragen: vorher genau eine Instanz und keine fremden ungespeicherten
  Dokumente (MCP `list_open_documents`), beenden (`ExitApp`), Start über `installationsordner` aus `config/rechner.yaml`,
  danach genau eine Instanz, sichtbares Fenster und Einstellungen Toggle 10 / Integer 6 = `False 1` prüfen.

## 5. Schleife und Bericht
- `swki status <spec>` und `swki bericht <spec>` wie beim Teil (Skill `konstruieren`, Abschnitte 6–7).
- Nachbessern nur am Bauweg; hält Claude eine Anforderung für falsch (z. B. Schraube zu lang), den Nutzer fragen.
