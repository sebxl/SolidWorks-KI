# Recherche: schneller ohne Präzisionsverlust – Startpunkt für die /goal-Session (BTP)

Stand 24.10.2026. Grundlage: [Laufzeit-Audit](2026-10-23-audit.md) (B1–B11) und
[Bewertungsbogen BTP](../superpowers/specs/2026-10-23-bewertungsbogen-design.md) (Score §5, Regeln §8). Nur Recherche:
kein Produktcode geändert, nichts mit SolidWorks gebaut.

## 1. Methode und Grenzen

- **Workflow** mit 9 Agenten: 5 Rechercheäste (B1 COM-Bindung, B3 Wiederverwenden, B4/B5 Bewegung und Verknüpfung,
  B6/B7 Kleinkram, B8/B9 Agentenseite), adversariale Gegenprüfung für die drei großen Äste, ein Kritiker für Überlappung,
  Lücken und Reihenfolge. Stichproben der Kernaussagen danach selbst nachgeprüft (Code, Profil, Index).
- **Quellen:** Audit-Profile `ap_bauen.prof`, `ap_pruefen.prof`, `z_durchlauf.prof` (cProfile 23.10., Stand `be8f8fd`;
  Scratchpad der Audit-Sitzung `%TEMP%\claude\C--Users-User-Documents-Projekte-SolidWorks-KI\1d9eedde-…\scratchpad\audit\`,
  Wegwerf), Messstand-Profile `<arbeitsordner>/MESSSTAND/profil_*.prof`, Bau- und Prüfprotokolle AP 6.8 Lauf 11–28,
  Transkripte d4/d5 und Prüfstation-Sitzungen, pywin32 312 im venv, `makepy -o` der `sldworks.tlb` in den Scratch
  (gen_py unverändert), SolidWorks-API nur über `swki api methode|enum|suche`, Claude-Code-Doku (code.claude.com).
- **Grenzen:** Profile je Fall einmal gemessen (±10 %). Mehrere Faktoren sind aus anderen Phasen desselben Laufs
  übertragen, nicht direkt gemessen (siehe §6, Vorab-Messung). Ersparnisse sind Spannen; Wirkungen überlappen (§4).

## 2. Kernbefund: Der B1-Overhead im Prüfen ist Latenz außerhalb von `sw.schnell`

Das Audit deutete B1 (240 s pywin32-Overhead) als Bindungsproblem. Die Recherche zeigt etwas anderes:

- `swki/baugruppe/pruefen.py:279-285`: `sw.schnell` umschließt nur `_messe_baugruppe`. Screenshots, Kopplungsbilder und
  die ganze Bewegungsprüfung laufen ohne Schnellmodus. Beim Bauen liegt `_grundstellung` (`swki/baugruppe/bau.py:341-343`)
  ebenfalls außerhalb.
- Am selben Dokument im selben Prozess kostet ein COM-Roundtrip außerhalb von `schnell` 14- bis 35-mal mehr
  (`ap_pruefen.prof`, selbst nachgerechnet):

  | Funktion | in `schnell` | außerhalb |
  |---|---|---|
  | `sw_baugruppe.verknuepfungen` je Aufruf | 0,18 s (1× aus `_messe_baugruppe`) | 4,0 s (25× aus `stelle`, 99,9 s) |
  | `fehlercode` je Aufruf | 0,6 ms | 11,6 ms (4 324×, 50 s) |
  | `transform` je Komponente | ≤ 0,7 ms | 19–20 ms (1 406×, 28 s) |
  | `interferenzen` je Aufruf | 0,8 s | 2,2 s (18×, 40 s) |
  | Grundstellung beim Bauen, `verknuepfungen` je Aufruf | 0,11 s (in `verknuepfe`) | 7,75 s |

- Kosten je Roundtrip: Bauen (fast alles in `schnell`) `GetTypeInfo` 0,38 ms, `GetIDsOfNames` 0,21 ms; Prüfen 4,0 bzw.
  2,0 ms. 238 von 252 s `getattr`-Zeit des Prüfens liegen in der Bewegungsprüfung. Die SolidWorks-Arbeit dort ist klein
  (27 Neuaufbauten 5,0 s).
- Python-seitig kostet ein Zugriff ~2,5 µs (Mikro-Benchmark an `Scripting.Dictionary`). Der Overhead ist also nur
  Anzahl Roundtrips × Latenz je Roundtrip – senken lässt er sich über **Latenz** (Schnellmodus) und **Anzahl**
  (keine Neuaufzählung), kaum über die Bindungsart.
- Index `ISldWorks.CommandInProgress`: „Improves performance of out-of-process applications … reduces the number of
  updates“. `IModelView.EnableGraphicsUpdate` wirkt laut Index nur „during a selection“. Welcher der fünf Schalter in
  `sw.schnell` (`swki/compiler/sw.py:92-116`) die Latenz senkt, ist offen (vermutlich `CommandInProgress`).

Folge: Der größte Hebel ist billig (Kontexte verschieben) und präzisionsneutral, solange die Bilder abgesichert sind.
Früh gebundenes COM (makepy/comtypes) fällt dagegen weg (§3.14).

## 3. Optimierungen

Ersparnisse je **Prüfstation-Zyklus** (Werkzeug ~14 min, BTP-`zeit_s` ~1050 s, nach Bemaßungsbezug ~940 s) bzw. je
**kleiner Aufgabe** (Mittel Teile 152 s). „Allein“ = gegen heutigen Stand; „im Paket“ = nach den davor empfohlenen
Umbauten (§5). Vertrauen: hoch / mittel / niedrig.

### 3.1 O1 – Bewegungsprüfung und Grundstellung im Schnellmodus, Grafik nur für die Bilder (B4, B1) · hoch

- **Was:** `pruefen.py:281-285` (ganzer Block nach `_messe_baugruppe` inkl. Screenshots, `_kopplungsbilder`,
  `_pruefe_bewegungen`) in `sw.schnell`. In `SwMechanik.bild` (`swki/baugruppe/sw_bewegung.py:73-74`) und für die
  statischen Screenshots `CommandInProgress` und `EnableGraphicsUpdate` kurz zurück, dann `IModelView.GraphicsRedraw`
  (Index: 1 Parameter `Rect`, leeres Array = ganzes Fenster; `IModelDoc2.GraphicsRedraw2` ist laut Index obsolet);
  Feature-Baum bleibt aus (sein Nachführen kostet Sekunden). `bau.py:336-343`: `schnell`-Block auf `_grundstellung`
  ausdehnen, `speichern` bleibt außerhalb.
- **Ersparnis:** Prüfen −160 bis −245 s (Rest der Bewegungsprüfung 45–75 s statt 314 s; Bilder +0–15 s durch Umschalten
  abgezogen). Grundstellung −10 bis −21 s, aber derselbe Topf wie O3 (c) – nur einmal zählen. Kleine Aufgaben 0 s
  (keine Bewegungen; Schlitten und Zahnstangentrieb der Regression profitieren).
- **Herleitung:** Profilsumme stelle 167,9 + treibe 18,4 + unterdrücke 20,3 + status 12,4 + zustand 30,3 + Interferenz
  39,7 + Bild 7,7 + loese 11,8 = 308,5 von 314 s. Mit den In-`schnell`-Raten desselben Profils: stelle 13–25, treibe
  2–4, unterdrücke 2–3, status 11–12 (ForceRebuild3 bleibt), zustand 1–2, Interferenz ~14, Bilder 8–20 s.
- **Risiko Präzision:** niedrig, aber drei Punkte belegen:
  1. **Veraltete Bilder.** `iso_bild` nimmt das Grafikfenster auf (`swki/pruefung/bilder.py:20, 72-79`, TIFF-Option 0 =
     Screen capture). Unter `schnell` ist ein altes PNG der erwartbare Fall. Keine Falle F1–F6 prüft Bewegungsbilder –
     der Bogen würde das nicht merken. Abnahme: Pixelvergleich alt/neu am selben gebauten Lauf, min ≠ mitte ≠ max,
     Kollisionsbilder des Schlitten-Negativfalls.
  2. **`GetConstrainedStatus` nach `ForceRebuild3`** über die Kopplungskette (`sw_bewegung.py:45-49`, Ruling T13-1) ist
     nur außerhalb `schnell` belegt. Nachweis am Zahnstangentrieb plus Negativfall (Freiheitsgrad 2 muss gemeldet werden).
  3. Lagen, Interferenzen, Grenzen nach `SetSystemValue3`/`EditRebuild3` unter `schnell`: Prüfbericht-Abschnitt
     `bewegungen` alt/neu feldweise gleich.
- **Risiko Regression:** niedrig bis mittel. Ein Kill (Zeitlimit `tests/live_einzeln.py`) überspringt das `finally`;
  `CommandInProgress` bliebe in der geteilten SolidWorks-Instanz gesetzt – das wäre das längste `schnell`-Fenster
  (~1 min). Gegenmittel: `CommandInProgress = False` am Anfang von `bauen`/`pruefen` und in `werkzeuge/sw_neustart.py`.
- **Messen im Bogen:** `zeit_s` pruefstation, Diagnose `swki_phasen_s.bewegungen`/`.grundstellung`,
  `bewegungen.laeufe[].dauer_s`. Regression Schlitten (4 Negativfälle), Zahnstangentrieb.
- **Aufwand:** 0,5 Tag (Kontexte, Bild-Umschalter als Kontextmanager in `sw.py`, Unit-Test Schalterreihenfolge auch bei
  Ausnahme, Live-Vergleich Prüfstation alt/neu).
- **Belege:** `pruefen.py:279-285`, `bau.py:336-343`, `sw.py:92-116`, `bewegungslauf.py:113-122`; `ap_pruefen.prof`
  (Tabelle oben); `ap_bauen.prof` `_grundstellung` 2× 15,5 s; Messstand Umbau 1 und 5 (`docs/messstand/ergebnisse.md`,
  gleiches Muster beim Bauen und Messen, Prüfwerte identisch).

### 3.2 O2 – Verknüpfungs-Handles in der Bewegungsprüfung statt Neuaufzählung (B4) · hoch

- **Was:** `SwMechanik` hält ein Dict Name → IFeature aus der schon vorhandenen Aufzählung in `_messe_baugruppe`
  (`pruefen.py:142`) plus die treibenden Verknüpfungen `<grenze>.antrieb`. `stelle` (`swki/baugruppe/sw_baugruppe.py:368-378`)
  liest `GetErrorCode2` an diesen Handles statt Baumdurchlauf + Fehlercode; `unterdruecke` (`sw_bewegung.py:41-43`)
  nutzt das Handle; `treibe` findet die neue Verknüpfung wie in O3; `loesche` behält eine Kontrollaufzählung.
- **Ersparnis:** nach O1 −6 bis −8 s; allein −30 bis −40 s (+ Teil der stelle-Aufzählungen). Klein 0.
- **Risiko Präzision:** keines – gleiche Semantik wie heute (jede Verknüpfung, auch Warnungen), nur ohne Baumdurchlauf.
  Offen: Gilt ein Handle nach `SetSuppression2` (unterdrücken → aktivieren) weiter? Heute wird vorher frisch aufgezählt;
  im Zweifel nach `unterdruecke` neu aufzählen (4×).
- **Verworfen (Teil des Asts):** „What's-Wrong-Zähler als Tor“ (`GetWhatsWrongCount` = 0 → keine Prüfung). Bringt nach
  O1 nur ~2,5 s mehr als die Handles, hängt an einer unbelegten Annahme (H1: jeder Fehlercode ≠ 0 erzeugt einen
  What's-Wrong-Eintrag – Index sagt „many of the errors“, Spike S13 belegt nur Code 47, nur außerhalb `schnell`) und
  ließe z. B. eine gebrochene unbeteiligte Verknüpfung (Code 48) durch.
- **Aufwand:** 0,25–0,5 Tag; Unit-Tests `test_sw_bewegung.py`, `test_bewegungslauf.py` patchen heute `verknuepfungen`.

### 3.3 O3 – Verknüpfen beim Bauen ohne quadratische Aufzählung (B5) · hoch

- **Was:**
  (a) `verknuepfe` (`sw_baugruppe.py:202, 210-211`): statt `vorher = len(verknuepfungen())` und `alle[-1]` nach
  `AddMate5` `asm.Extension.GetLastFeatureAdded` (Index: 0 Parameter, „can access subfeature types such as mates“).
  **Pflicht:** Typprüfung (`GetTypeName2` ist ein Verknüpfungstyp) oder Identität über `ISldWorks.IsSame` (Index:
  2 Parameter, `swObjectEquality` 0/1/2) – sonst würde ein falsch erkanntes Feature umbenannt und im Fehlerzweig
  `_loesche_still` (`sw_baugruppe.py:228-232`) womöglich eine Komponente gelöscht. Rückfall:
  `FeatureByPositionReverse(0)` mit Typprüfung, dann die heutige Wanderung.
  (b) Baulauf hält Dict `v.id → IFeature` aus der Rückgabe von `verknuepfe` (`bau.py:248-250`); `_pruefe_ausrichtungen`
  (`sw_baugruppe.py:152-157`) liest `Alignment` nur über diese Handles – **weiter alle gesetzten Verknüpfungen nach
  jeder neuen** (Schutz gegen das stille Umkehren, Spike S12 Z.5, `docs/stufe3b/ergebnisse.md:168-172`).
  (c) `_grundstellung` (`bau.py:270`) nimmt das Handle der Grenze.
- **Ersparnis:** allein −60 bis −75 s (Verknüpfen 87 → ~30 s, Grundstellung 22 → 3–7 s); nach O1 (Grundstellung schon
  billig) −45 bis −57 s. Stehlager −1 bis −2 s. Teile 0.
- **Herleitung:** `ap_bauen.prof` `verknuepfungen` 514× 70,9 s = 342× aus `verknuepfe` 37,2 s + 170× aus
  `_pruefe_ausrichtungen` 18,2 s (+ 14 705 Namenszugriffe 2,9 s) + 2× aus `_grundstellung` 15,5 s. Die 10 453
  Alignment-Lesungen (7,8 s) bleiben.
- **Risiko Präzision:** keine Schwächung; Erkennung der neuen Verknüpfung wird strenger (Typ/Identität statt „Anzahl
  gewachsen“). Offen: Liefert `GetLastFeatureAdded` unter `schnell` (`EnableFeatureTree = False`) richtig? →
  Schattenvergleich alt/neu unter `schnell` über die ganze Regression plus Ausrichtungs-Negativfall.
- **Risiko Regression:** mittel-gering. **Merge-Konflikt mit Bemaßungsbezug** (ändert `verknuepfe`-Signatur und
  `bau.py:248-250`, Commit 80f1eb1) – erst nach dessen Merge beginnen.
- **Verworfen:** „nur die neue Verknüpfung prüfen“ wörtlich (verliert die Umkehr-Erkennung), Ausrichtung blockweise oder
  am Ende (verliert die Zuordnung zur verursachenden Verknüpfung), `IFeatureManager.GetFeatures` (Reihenfolge laut
  Index beliebig), `IComponent2.GetMates` (liefert IMate2 je Komponente, kein `GetErrorCode2`), `CreateMate` statt
  `AddMate5` (großer Umbau, Ausrichtungsverhalten neu zu vermessen). „MateGroup je Dokument merken“ (Ast B1, O3 dort):
  nur als Rückfall; ein Cache nach `id(asm._oleobj_)` ist gefährlich (IDs werden wiederverwendet → Verknüpfungen eines
  anderen Dokuments), jeder Dokument-Cache muss am Dokumentbesitzer hängen und beim Schließen verworfen werden.
- **Aufwand:** 0,5–1 Tag; Unit-Tests `test_bau_baugruppe.py`, `test_sw_kopplung.py` anpassen.

### 3.4 O4 – Kleinkram im Bewegungs- und Prüflauf (B4) · mittel

- `fahre` (`swki/baugruppe/bewegungslauf.py:168-174`): zweites `_zurueck(min)` nur, wenn der Schritt unter die Grenze lief
  oder der Grundlauf einen Fehler hatte (bei `min = 0`, Weichenhub, doppelt).
- `_kopplungsbilder` ohne Kopplungen sofort verlassen (heute `_komponenten` 296 Zugriffe außerhalb `schnell`, 1,7 s).
- **Nicht übernehmen:** Interferenz in Stellung 0 mit Toleranz überspringen (TOL_BEWEGT 1e-3 mm würde Berührkollisionen
  verschlucken; nur exakte Gleichheit wäre neutral und greift kaum); `zustand` → `lage` bringt laut Profil nur 1,5 s.
- **Ersparnis:** allein −8 bis −12 s, nach O1 −0,5 bis −3 s. Nur als Beigabe zu O1/O2.

### 3.5 O5 – Unveränderte Eigenteile wiederverwenden, geänderte zuerst bauen (B3) · hoch

- **Was:** Neues Modul `swki/baugruppe/wiederverwendung.py`.
  - **Schlüssel** = sha256 über: Teil-Spec ohne `pruefung` (der Compiler liest `pruefung` nie – per Unit-Test absichern;
    konservativ: ganze Spec), sha256 der `typ: skript`-Dateien, **Import-Hülle von `swki.compiler.bauen`** (AST,
    samt Registry/Handlern, `spec/`, `verzahnung`, `formschraege`, `pruefung.geometrie`) statt ganz `swki/`, gelesene
    Wissensdateien (`bohrungsnormen.yaml`, `module_din780.yaml`), nur die vom Compiler gelesenen Schlüssel aus
    `config/standard.yaml` (Toleranzen, Namensschema, Bohrungsnorm, `gleichungen`; nicht der Schalter selbst),
    `schema/teil.schema.json`, Auftragsname, `sw_jahr` + `ISldWorks.RevisionNumber` (Index: 0 Parameter, „major.minor“
    je Service-Pack), sha256 der Teilvorlage, bei `material` die Materialdatenbanken (`GetMaterialDatabases`).
  - **Quelle** = Lauf des eigenen Auftrags (nie auftragsübergreifend – Messstand-Leck, `werkzeuge/messstand/__main__.py:97-99`)
    mit Teilstatus ok, gleichem Schlüssel und Datei-sha256 = Protokoll (schützt vor `MANUELL_GEAENDERT`). Gesperrt ist
    jede Datei-sha256 bzw. jeder Schlüssel, zu dem irgendein Prüfbericht des Auftrags einen Teilmangel hat (sonst kann
    ein sporadischer Normbohrungsfehler über einen fehlgeschlagenen Lauf wieder Quelle werden). Fehlgeschlagene Läufe
    sind als Quelle erlaubt (Läufe 21–25).
  - **Ablauf** in `_baue_teile` (`bau.py:58-77`): erst die Teile ohne Quelle bauen – zuletzt gescheitertes, neue,
    geänderte; Abbruch beim ersten Fehler wie heute. Dann wiederverwendete kopieren (`shutil.copy2` wie Normteile,
    `bau.py:92`), sha256 prüfen, `oeffne`, `kontext_aus_datei` (`swki/pruefung/messen.py:318-334`, derselbe Weg wie
    in `pruefen.py:247-251`). Ist ein gleichnamiges Dokument schon offen (`oeffne` wirft `PruefFehler`,
    `messen.py:37-43`), auf Neubau zurückfallen. Teilprotokoll übernehmen (Knoten, Punkte, künftig `masse`), `lauf`
    und `gestartet` neu setzen, `wiederverwendet: {lauf, datei_sha256}` ergänzen, `protokoll.teile` am Ende wieder in
    Spec-Reihenfolge.
  - Ausgabe `teile_gebaut`/`teile_wiederverwendet` in `durchlauf` (Pflicht – sonst fällt ein still abweichender
    Schlüssel nicht auf), Ausweg `--alles-neu`, Schalter `wiederverwenden: true` in `config/standard.yaml`.
  - `--verwerfen`/`--uebernommen` brauchen keinen Sonderfall (sha-Abweichung bzw. geänderter Schlüssel → Neubau).
  - Pack-and-Go unnötig: Eigenteile haben keine externen Referenzen, die Baugruppe wird ohnehin neu mit Pfaden in
    `lauf-<n>` gebaut.
- **Ersparnis:** heute −180 bis −250 s (typisch −220 s); **nach Bemaßungsbezug −100 bis −140 s**; nach O1–O3 und
  Bemaßungsbezug −85 bis −120 s. Abbruch an einem geänderten Teil nach ~10–20 s statt 250–320 s – im Erwartungswert
  −15 bis −45 s je BTP-Aufgabe, **kein Zuschlag** zur Zyklus-Ersparnis. Stehlager im BTP 0 s (neuer Auftrag, keine
  Quelle), im Nachbesserungslauf −12 bis −16 s. Teile 0.
- **Herleitung:** Lauf 28 Teile-Phase 273 s, Median 10 s je Teil (1,9–30,4 s); Öffnen statt Bauen 0,6–1,5 s je Teil
  (`OpenDoc6` 8,65 s/11 beim Bauen, 31,6 s/35 beim Prüfen). BTP-Aufgabe (§2.1): 2 Teile neu (4–55 s) + 21× Öffnen
  (13–32 s) + Erstdokument 3–6 s = 20–93 s. Geschichte Läufe 12–28: geändert je Übergang meist 0–2 von 23 Teilen
  (Ausnahme Umbau v4); mit Code-Änderungen zwischen den Läufen (6 von 17 Übergängen) −1900 s über 17 Läufe.
- **Risiko Präzision:** niedrig – bitgleiche Datei für exakt dieselben Eingaben; `swki pruefen` misst jedes Teil weiter
  gegen die freigegebene Kopie (die Teilprüfung entfällt **nicht**). Restrisiko: Eingaben außerhalb des Schlüssels
  (Hole-Wizard-/Toolbox-Datenbank, Systemoptionen) – fallen über die Prüfung gegen die Freigabe-Kopie auf.
- **Risiko Regression:** mittel – `kontext_aus_datei` löst jetzt bis zu 171 Verknüpfungsreferenzen von Eigenteilen auf
  (`{feature, flaeche}`, `instanz`, `nahe`). In allen 1399 Teilknoten der Baugruppen-Protokolle gilt `sw_name == id`,
  Referenzen brauchen nur `features[0]` (`swki/baugruppe/referenzen.py:102-130`). Nachweis: Regression doppelt bauen
  (zweiter Bau: alle Teile wiederverwendet, Prüfbericht Wert für Wert gleich), dann ein Parameter geändert → genau
  dieses Teil neu.
- **Voraussetzung im BTP:** `vorbereiten` löscht den Arbeitsordner des MESS-Auftrags (`werkzeuge/messstand/__main__.py:82-84`).
  Der Ausgangslauf muss danach mit dem gemessenen Stand gebaut werden, sein Protokoll im Auftragsordner des
  Lauf-Worktrees liegen (dort sucht `lauf_datei`), und `protokolle.auswerten` muss ihn auslassen.
- **Verworfen:** Datei-Hash als Änderungsmerkmal (Lauf 26→27 ohne Änderung, trotzdem alle 23 SLDPRT-Hashes anders),
  Freigabe-Prüfsumme als Schlüssel (deckt nur Anforderungen, nicht den Bauweg – Läufe 22–25 änderten nur den Bauweg),
  Teilprüfungen übernehmen (≤ 10–13 s, schwächere Prüfung), auf Dateien im Vorlauf verweisen (bricht den geschlossenen
  Lauf-Ordner und `MANUELL_GEAENDERT`), inkrementell die alte Baugruppe nachziehen, git-Hash als Code-Stand.
- **Aufwand:** ~2 Tage (1 Tag Code + Unit-Tests ohne SolidWorks, 0,5 Tag Live-Regression doppelt, 0,5 Tag
  Prüfstation-Nachweis und Skill-/CLAUDE.md-Text). „Geändertes zuerst“ allein (0,25 Tag) bewegt den BTP fast nie
  (der erste Bau nach dem Ausgangslauf hat kein neues Teil) – nur im Paket.

### 3.6 O6 – DISPID-Cache in einer eigenen CDispatch-Unterklasse (B1) · mittel

- **Was:** pywin32 312 ruft `GetTypeInfo` bei **jedem** zurückgegebenen Objekt (`win32com/client/dynamic.py:133`) und
  `GetIDsOfNames` bei **jedem** Attributzugriff, ohne das Ergebnis zu speichern (`dynamic.py:594-601`); ein
  Methodenaufruf mit Argumenten kostet je neuem Objekt einen vergeudeten PROPERTYGET (`:615-625`). Stufe 1
  (risikofrei): Cache **je Objekt** (MapEntry im eigenen olerepr) für langlebige Objekte (App, Dokument, Komponenten).
  Stufe 2: Cache je Schnittstellen-Etikett nur für live bestätigte Paare (Etikett, Member) aus einer Whitelist im Repo,
  Prüfmodus mit GetIDsOfNames-Abgleich über die Regression.
- **Ersparnis:** allein −150 bis −210 s; **nach O1 + O3 −30 bis −60 s; nach O1–O3 + O5 nur −5 bis −15 s.** Klein −1 bis
  −3 s.
- **Risiko Präzision:** mittel (Stufe 2). DISPIDs kollidieren über Schnittstellen hinweg: IFeature/IComponent2 teilen
  50 Namen, 40 mit anderer DISPID (DISPID 58 = `IFeature.GetBox`, aber `IComponent2.DeSelect`); IModelDoc2/IPartDoc
  `FirstFeature`, IAssemblyDoc/IPartDoc `FeatureByName` haben verschiedene memids (`sldworks.tlb` offline). Ein falsch
  gelerntes Paar ruft still einen anderen Member – falsche Messwerte bei grüner Prüfung. Die tlb-memid taugt nicht als
  Abgleich (ein SolidWorks-IDispatch vereint mehrere Schnittstellen).
- **Nicht erfasst:** `IUnknown::Release` je freigegebenem Objekt ist ein weiterer Roundtrip (Eigenzeit reiner
  Glue-Funktionen beim Prüfen 36 s); O1 und O3 senken ihn, O6 nicht.
- **Empfehlung:** erst nach O1–O3/O5 neu profilieren; als eigener Umbau kaum lohnend (+0,02 bis +0,05 Score). Stufe 1
  allenfalls als Reserve.
- **Aufwand:** 1,5–2 Tage (Stufe 2), Stufe 1 ~0,5 Tag.

### 3.7 O7 – Ansichtsanimation bei Bildern aus, Auto-Rotate beim Skizzieren aus (B7, B6) · A1 hoch, A2 mittel

- **A1:** `ViewZoomtofit2` kostet in allen fünf Profilen konstant 0,51–0,52 s je Aufruf, beim Teil wie bei der Baugruppe;
  Registry `View Animation Speed = 0.5`. Klammer `swViewAnimationSpeed` (Index `swUserPreferenceDoubleValue_e` = 38)
  auf 0 um `screenshots`, `kopplungsbild`, `iso_bild` (`bilder.py:24-79`), Ursprungswert im `finally` zurück (Muster
  `sw.einstellung_int`, `sw.py:71-79`); bei `kopplungsbild` zusätzlich `swViewTransitionHideShowComponent` = 87.
  Ersparnis: Teile −1,8 bis −2,1 s je Prüflauf, Prüfstation −4,5 bis −5,5 s (10 Bilder), bis −9 s, falls `SaveAs3`
  auch wartet. Risiko: Endbild gleich → Pixelvergleich; nach hartem Abbruch bliebe die Nutzereinstellung auf 0 →
  `sw_neustart` prüft heute nur Toggle 10 und Integer 6, die neuen Werte mit aufnehmen.
- **A2:** `InsertSketch` kostet je Öffnen/Schließen 0,6–0,74 s fast unabhängig von der Teilgröße (Prüfstation 182× 54,5 s,
  13 % des Bauens). Hypothese: Auto-Rotate (`swAutoNormalToSketchMode` = 477) + Animation. In `sw.schnell` beide aus.
  Ersparnis: Prüfstation −20 bis −45 s ohne O5, mit O5 −2 bis −4 s; Teile −0,7 bis −3 s; Stehlager −2,7 bis −5,5 s –
  **oder 0, falls die Hypothese nicht stimmt** (10-min-A/B live vorher). Alle Auswahlen sind ansichtsunabhängig
  (`SelectByRay` in Modellkoordinaten, `SelectByID2` über Namen, Skizzenkoordinaten über `ModelToSketchTransform`).
- **Aufwand:** zusammen 0,5 Tag.

### 3.8 O8 – Normbohrung und Prozess-Kleinkram (B6, B7) · mittel bis niedrig

- **Audit-Korrektur:** „Normbohrung median 7,1 s“ stammt vom 04./05.10.; seit 09.10. liegt der Median bei **1,9–2,4 s**
  (529 Bohrungen). Prüfstation: 32 Features, 74 s, davon nach Bemaßungsbezug ~52 s, angreifbar ~22–25 s. Hebel 7 des
  Audits (−30 bis −50 s) ist zu hoch.
- **B – doppelter Neuaufbau:** `_neu_aufbauen_bis_vollstaendig` (`swki/compiler/handler/normbohrung.py:78-97`) macht nach
  `ForceRebuild3` noch `sw.rebuild` (`EditRebuild3`), danach `nach_knoten` (`ablauf.py:26`) ein drittes Mal. Rückgabe
  von `ForceRebuild3` auswerten, nur What's-Wrong prüfen, `nach_knoten` überspringen; Anzahl Neuaufbauten ins Protokoll
  (heute verworfen, `:140`) – macht das Zeitrennen nach Bemaßungsbezug messbar. `ForceRebuild3` selbst bleibt (Index
  `IWizardHoleFeatureData2.IGetSketchPoints` verlangt es, S10 gemessen). −6 bis −9 s Prüfstation (mit O5 ~0), Stehlager
  −1 s, Teile ~0. Erst nach Bemaßungsbezug (baut `skizze.py`/`normbohrung.py` um).
- **F – `NeedsRebuild2`** vor `nach_knoten` (Index: Property seit 2012): 0 bis −12 s, Quote unbekannt; nur nach
  Messspike ohne Gleichungen.
- **C – Material-Datenbanken einmal je Prozess** (`swki/compiler/eigenschaften.py:46-53`, `GetMaterialDatabases` je Teil
  0,17 s): −3,5 s Prüfstation ohne O5; Steckbrief-Import (numpy/trimesh 0,91 s) im Hintergrund-Thread: −0,5 bis −0,9 s
  je Teil-Aufgabe.
- **Verworfen:** Bohrungen zusammenfassen (1 von 32 möglich, `validieren` meldet es schon), Mehrfach-`SelectByRay`
  statt Positionsskizze (S10: nur 1 Bohrung), `EditRebuild3` statt `ForceRebuild3` (S10: 1 statt 2 Instanzen),
  unsichtbare Dokumente (`EditRebuild3` „only works in-context of the active document“), Dokument wiederverwenden,
  erstes Dokument vorwärmen (verschiebt nur), schlankere Vorlage, weniger/kleinere Screenshots (Prüfer nutzt alle 4
  Ansichten für F1–F3), Screenshots parallel zum Prüfer, BMP statt PNG, Ambient Occlusion aus (ändert Bildinhalt),
  Speicheroptionen (schon optimal: Verify On Rebuild 0, Masseeigenschaften beim Speichern 0).

### 3.9 O9 – Einschraublänge als harte Prüfung in `swki pruefen` (B9, Falle F6) · hoch

- **Was:** `swki/baugruppe/bewertung.py` `_gewinde_ergebnis`/`_gewinde_durch` (165-184): Mindestlänge `k(Werkstoff des
  Mutterteils) · d`; `d` aus `qs.masse["d"]`, Werkstoff aus `qt.spec["material"]`; neue Wissenstabelle
  `swki/wissen/einschraublaenge.yaml` (Werkstoffgruppe → Faktor; heute nur in `.claude/agents/pruefer.md:38`: Stahl 1·d,
  Grauguss 1,25·d, Alu 2·d – Projektregel: ≥ 2 unabhängige Quellen je Wert). **Mangel nur, wenn das Gewinde mehr hergäbe**
  (verfügbare Gewindelänge ≥ k·d), sonst Hinweis. Bei `durch` die eingeschraubte Länge aus dem bereits gemessenen
  Überlappungsvolumen zurückrechnen (Umkehrung `ueberlappung_soll`, `geometrie.py:47-60`) – keine neuen COM-Aufrufe.
  Spalten `d`, `werkstoff`, `mindestens` in der Gewindezeile (`swki/pruefung/bericht.py:74-76`).
- **Warum:** Beide echten Prüfer-Funde der Prüfstation (Lauf 12: M5 7,4 mm; Lauf 26: 8,0 und 7,4 mm in 6061) waren
  Durchgangsgewinde mit `ok: null` („Gewinde durch: Volumen nicht geprüft“, `bewertung.py:182-184`).
- **Gegenprobe Lauf 28** (Prüfer bestanden): starre 2·d-Regel → 11 Fehlalarme an Kaufteil-Ersatzgewinden (Kamera M3 in
  4 mm, Durchlicht M4 in dünner Platte); mit „verfügbar ≥ k·d“ → 0, Lauf 12/26 getroffen. Toleranz der Volumen-Umkehrung
  vorher an Lauf 12/26/28 kalibrieren (Grenzfall `ts`/`ks`: 10,4 mm gegen ~9,6 mm bei Soll 10).
- **Ersparnis:** Erwartungswert ~−10 s je Prüfstation-Zyklus (im Zyklus mit diesem Mangel −19 bis −83 s, weil
  `pruefer_auftrag` nur bei bestandener Prüfung entsteht, `swki/durchlauf.py:107-108`). Teile 0.
- **Präzision:** positiv – F6 deterministisch (BTP §3: Fund in `swki pruefen` zählt als Treffer); Fallen danach neu bauen.
  Risiko: neue `pruefmaengel` im Ausgangslauf, falls die Regel Fehlalarme erzeugt (Gegenprobe Lauf 28 als Unit-Test).
- **Wert:** Voraussetzung dafür, den Prüfer schmaler zu machen (O11), ohne dass F6 am Prüfer hängt.
- **Aufwand:** 1–1,5 Tage (Tabelle mit Quellenabgleich, Unit-Tests aus Lauf 12/26/28, Rückrechnung, Berichtsspalten,
  Satz in `pruefer.md`, Live-Regression).

### 3.10 O10 – Prüfer in einer Lese-Runde (B9, B8) · hoch

- **Was:** `pruefer_auftrag` (`swki/durchlauf.py:44-61`) nennt Dateien statt Ordner (jede Eingabedatei, `aufgabe.md` nur
  wenn vorhanden, jedes Bild mit Ansicht), bei Baugruppen nur die Freigabe-Kopien der Komponenten statt
  `glob("*.freigegeben.yaml")` (Zeile 50), optional „seit dem letzten bestandenen Lauf geändert“. Zusätzlicher
  Kurzbericht `…pruefbericht.kurz.json` (alle `ok: false/null`, `gewinde:*`, `mass:*`, `bewegung*`, `stueckliste`,
  `bestimmtheit`, `kollision` vollständig; bestandene Teilprüfungen als Zähler je Komponente); der volle Bericht
  (`indent=2`, Prüfstation 107 KB/5058 Zeilen, `swki/pruefung/befehle.py:55`) bleibt daneben. `pruefer.md`: „Lies alle
  genannten Dateien in deiner ersten Antwort parallel.“ Skill: `pruefer_auftrag` unverändert übernehmen (Lauf 28: 3,4k
  Zeichen Prompt von Hand, +12,8 s).
- **Ersparnis:** Teile −2 bis −5 s (3–4 → 2 Runden, je Runde 1,5–2,5 s), Prüfstation −8 bis −20 s (6–7 → 3 Runden,
  Bericht in einem Stück), tokens_gewichtet des Prüfers −10 bis −15 %.
- **Präzision:** gering, solange alle nicht bestandenen Zeilen voll im Kurzbericht stehen. Nachweis: Fallen F1–F6,
  R1/R2 je 3× vorher/nachher.
- **Aufwand:** 0,5–1 Tag.

### 3.11 O11 – Prüfer-Frontmatter: `model: sonnet`, `effort: medium`, `omitClaudeMd: true` (B9) · mittel

- **Was:** `.claude/agents/pruefer.md` setzt heute nur `name`, `description`, `tools` und erbt **effort high** (alle
  Transkripte d4/d5, Prüfstation); Standard von Sonnet/Opus 5.5 laut Doku ist medium. Modell fest im Frontmatter (Aufruf-
  Parameter gewinnt, also gleich halten), CLAUDE.md weglassen (~2,7k Tokens je Prüfer, Bau- und Git-Regeln braucht er
  nicht). Haiku nur, falls eine Fallen-Serie 3/3 auf F1–F5 liefert.
- **Ersparnis:** Teile −2 bis −8 s, Prüfstation −6 bis −18 s (Denkzeit 6–24 bzw. 21–36 s, −30 bis −50 %).
- **Präzision:** **mittel** – F1–F3 sind reine Bild- und Maßbilddeutung, genau dort kann weniger Denken schaden.
  Übernahme nur, wenn jede Falle ≥ 2/3 wie vorher trifft und R1/R2 ohne Fehlalarm bleiben (BTP §3, Sperre §5).
- **Risiko Regression:** keine Code-Regression; `omitClaudeMd` laut Doku ab Claude Code 2.1.271 (laufende Version
  ungeprüft, d5 lief mit 2.1.293).
- **Aufwand:** 0,25 Tag + Fallen-Serie 2 × ~10 min.

### 3.12 O12 – Konstruktionsreview schlank (B8; neu seit 11.10., nicht im Audit) · mittel, **Nutzerentscheidung**

- **Befund:** Seit b7ff38c (11.10.) verlangen `konstruieren/SKILL.md:174-176` und `baugruppe/SKILL.md:109` vor jeder
  Freigabe-Vorlage den Subagenten `konstruktionsreview`. In den Prüfstation-Sitzungen dauerte er **174 s, 227 s, 362 s**
  (Opus 5.5, effort high – kein `model:` im Frontmatter; Denkblöcke bis 121 s; 152–302k tokens_gewichtet). Weder die
  Audit-Zahlen noch der BTP-Schätzwert „Modell ~180 s“ enthalten ihn.
- **Was:** Frontmatter `model: sonnet`, `effort: medium`; Geltungsbereich „nur neue Teile und Formänderungen; kein Review
  bei reiner Parameter-, Schraubenlängen- oder Normteiländerung und bei Kaufteil-Ersatzkörpern“; im Auftrag nur
  geänderte Specs und den Diff zur Freigabe-Kopie.
- **Ersparnis:** Prüfstation −100 bis −360 s (Modellwechsel −100 bis −250 s; bei der BTP-Änderung – Maß + Schraubenlänge –
  entfiele er ganz), Teile 0 bis −100 s (nur falls er dort läuft).
- **Präzision:** im Bogen nicht gemessen (F1–F6 prüfen das Prüfverfahren nach dem Bau); ein schwächerer Review kann
  Fertigungsgerechtheit kosten, die der Bogen nicht sieht. Ändert eine Regel der Retro Etappe 4 → BTP §8 „keine
  Änderung an Konstruktionsregeln“ → nur mit Nutzer-OK.

### 3.13 O13 – Skill-Kleinkorrekturen gegen Fehlrunden (B8) · hoch

- `konstruieren/SKILL.md:32`: `name`-Muster `^[A-Za-z0-9][A-Za-z0-9_-]*$` nennen (schema/teil.schema.json:10). Die
  Fehlrunde trat in **13 von ~18 Maßbild-Läufen d0–d5 und in 6 von 6 in d4/d5** auf, je 4,3–4,6 s; die
  Baugruppen-Referenz nennt das Muster schon.
- `normbohrung`: verfügbare Größen je `art` in einer Zeile (Kamera: 3 Erkundungsrunden in `bohrungsnormen.yaml`).
- `baugruppe/SKILL.md:141-147`: mit `durchlauf --neustart` entfällt Speicherabfrage + Neustart nach dem Lauf (11–18 s +
  2 Runden, Lauf 28).
- Kein separates `validieren` vor `durchlauf --freigeben`; `pruefer_auftrag` unverändert übernehmen (mit O10).
- Nach Bemaßungsbezug die neue Regel `bezug` gleich in die Syntax-Kurzreferenz (sonst eine Hinweis-Runde mehr).
- **Ersparnis:** Teile −3 bis −8 s (Mittel ~−4 s), Prüfstation −15 bis −30 s. Präzision: keine. Aufwand 0,25–0,5 Tag,
  auf dem Skill-Stand nach Bemaßungsbezug.
- **Verworfen:** Progressive Disclosure der Skills als eigener Umbau (entbehrlich ~1k Tokens beim Teil, ~2,5k bei
  statischer Baugruppe; ≤ 2–4 % tokens_gewichtet, Skill kommt nach dem ersten Lesen aus dem Cache – cache_read
  500–860k je Lauf –, jede nachgeladene Referenz kostet eine Runde).

### 3.14 O14 – Modellgeschwindigkeit des Hauptagenten: Fast Mode bzw. effort (B8) · niedrig, **Nutzerentscheidung**

- **Befund:** 60–75 % der kleinen Aufgaben sind Modellzeit, davon 28–48 % Denken (`thinkingDurationMs` 36–91 s Teile,
  123–143 s Stehlager); alle Läufe mit effort high.
- **Fast Mode** (Opus 5.5, laut Doku „up to 2.5x faster“, gleiche Qualität, $8/$40 je MTok, im Abo nur über
  Nutzungsguthaben): Teile −30 bis −60 s, Stehlager −50 bis −100 s, Prüfstation −60 bis −200 s. Ob er auf Subagenten
  (Messstand-Lauf-Agenten) wirkt, ist zu prüfen (`usage.speed` im Transkript). Kann am Ratenlimit still auf
  Standardgeschwindigkeit fallen (Streuung).
- **effort medium** (Doku: Opus 5.5 medium ≥ Opus 5 high): Teile −15 bis −45 s; echtes Risiko für `richtig` bei der
  Zeichnungsdeutung.
- **Score:** stärkster Einzelhebel (+0,3 bis +0,9), aber Konfiguration und Kosten, kein Code → vor Durchgang 0 als
  Betriebsstandard festlegen oder ausdrücklich als Umbau zulassen.

### 3.15 Verworfen (Übersicht)

| Idee | Grund |
|---|---|
| makepy/`gencache` früh gebunden | `makepy -o` (6,3 MB, 484 Klassen) deklariert fast alle Objekt-Rückgaben als VT_DISPATCH ohne CLSID → `Dispatch(ret, name, None)` versucht wieder `GetTypeInfo`, das bei SolidWorks scheitert (S8); Typisieren nur von Hand je Aufrufstelle, ByRef-Ausgaben als Tupel statt `VARIANT.value`, ()-Regel kehrt sich um, Hunderte Aufrufstellen, gen_py-Cache geteilt und SW-jahrabhängig. Gewinn nur der GetIDsOfNames-Anteil. |
| comtypes | nicht im venv, andere Out-Parameter-Semantik, untypisierte Rückgaben brauchen ebenfalls je Objekt ein QueryInterface; Wochen Aufwand |
| DISPID-Cache nur nach Membernamen | DISPID-Kollisionen zwischen Schnittstellen → stille Fehlaufrufe |
| `GetTypeInfo` global abschalten | IBody2 hat Typinfo; `body.GetFaces()` bräche |
| In-Process-Add-in | Architekturwechsel, nicht in 5 Umbauten |
| What's-Wrong-Tor in der Bewegungsprüfung | siehe O2: ~2,5 s Gewinn, unbelegte Annahme H1 |
| Interferenz-Vorfilter `GetComponentsTransformInterference` | liefert Komponenten statt Paare; bewegte Schrauben mit bekannten Gewindeüberlappungen → greift fast nie (0–5 s), Semantik unklar |
| `bewegung_schritte` senken, weniger Screenshots | schwächere Prüfung (BTP §8) |
| `IDragOperator.CollisionDetection`, `ICollisionDetectionManager` | ändert, wie die Lage entsteht; kein Volumen |
| `ForceRebuild3` in `SwMechanik.status` durch `EditRebuild3` ersetzen | Ruling T13-1: Status über die Kopplungskette veraltet |
| Prüfer für kleine Aufgaben streichen | Nachweis „99 % unnötig“ fehlt (Audit B9); F1–F3 sieht nur der Prüfer |
| Prüfer je Teil parallel, statischer Prüfer während der Bewegungsprüfung | Aufwand steigt N-fach bzw. zwei Prüfer + geteilter Bericht; nach O1 ist die Bewegungsprüfung < 100 s |
| Hooks zum Kürzen von Ausgaben | `durchlauf` ist schon kompakt; der große Brocken (Prüfbericht) wird an der Quelle gelöst (O10) |

## 4. Überlappung und bereinigte Wirkung

### 4.1 Was doppelt zählt

- **B1 im Prüfen (150 s)** steckt zu ~94 % in der Bewegungsprüfung → O1 nimmt ihn; für O6 bleiben beim Prüfen 6–11 s.
- **B1 im Bauen (90 s):** ~38 s nimmt O3 (Baumwanderung der obersten Ebene), ~35 s O5 (Teilbauten) → für O6 bleiben
  5–15 s.
- **Grundstellung** steht in O1, O2 und O3 (c) → einmal zählen (Handle-Weg).
- **Fehlversuch-Erwartungswert** (B3): nur einmal, −15 bis −45 s, ersetzt die Zyklus-Ersparnis eines abgebrochenen Laufs.
- **Bemaßungsbezug** nimmt < 2 s B1-Overhead weg, aber ~110 s echte SolidWorks-Arbeit; O5 sinkt dadurch um ~40 %.
- **A2, O8 B/C** wirken je Teilbau → mit O5 für die Prüfstation ~0, für Teile und Stehlager bleiben sie.

### 4.2 Prüfstation-Zyklus (Annahme: Bemaßungsbezug vor Durchgang 0 gemergt)

Ausgang ~940 s `zeit_s` (Werkzeug ~714 s: Neustarts 28, bauen ~309, prüfen 377) – **plus 174–362 s, falls der
Konstruktionsreview im Messlauf läuft** (§6).

| Schritt (Reihenfolge §5) | Δ | `zeit_s` danach |
|---|---|---|
| U1 Latenz-Paket (O1, O2, O3, O4, A1) | −285 bis −395 s | 545–655 s |
| U2 Wiederverwenden (O5) | −85 bis −120 s | 425–570 s |
| U4 Prüf- und Agentenpaket (O9, O10, O11, O13) | −30 bis −100 s | **~325–540 s** |
| optional Fast Mode (O14) | −60 bis −200 s | ~250–480 s |

Werkzeug je Zyklus 714 s → **~195–345 s (3,3–5,7 min)**, im Einklang mit dem Audit (4–5 min). Das Beispiel in BTP §7
(„Prüfstation 300 s“) geht ohne Modellhebel nicht auf: Modell ~180 s + Prüfer ~40 s + Neustarts 28 s sind schon ~250 s.

### 4.3 Kleine Aufgabe (Mittel 152 s; Werkzeug ~25 s, davon −6 s Bemaßungsbezug schon vor Durchgang 0)

A1 −2 s, A2 −1 bis −3 s, O8 C −0,5 bis −0,9 s, O13 −3 bis −4 s, O10 −2 bis −5 s, O11 −2 bis −8 s → **−11 bis −23 s
(129–141 s)**; mit Fast Mode zusätzlich −30 bis −60 s. Stehlager −17 bis −35 s.

## 5. Score-Mechanik, Rangliste und Empfehlung für die 5 Umbauten

### 5.1 Was die Anker für die +0,3-Schwelle (§5.1) bedeuten

| Gruppe | Bereich | Gesamtscore je Einheit |
|---|---|---|
| Zeit Prüfstation | über 420 s | 0,00088 je s (+0,3 ≙ −340 s) |
| Zeit Prüfstation | unter 420 s | 0,0042 je s |
| Zeit Teile | über 75 s | 0,0047 je s (+0,3 ≙ −64 s) |
| Zeit Stehlager | über 180 s | 0,00135 je s (+0,3 ≙ −222 s) |
| Präzision erster Lauf | über 1 Fehlerpunkt | 0,35 je Fehlerpunkt |
| Präzision Fallen | 5 → 6 Treffer | 0,6 |
| Robustheit | über 8 GB | 0,044 je GB |

Folgen: Fast jeder Einzelhebel liegt unter +0,3 (O5 allein +0,08 bis +0,12) – **Umbauten müssen gebündelt werden**.
Ein zufälliger Fehlerpunkt (−0,35) wiegt mehr als die meisten Umbau-Gewinne; die Wiederholungsregel §5.1 wird oft
gebraucht. Agenten-Sekunden an der Prüfstation zählen erst unter ~420 s nennenswert – Agentenhebel deshalb spät.

### 5.2 Rangliste

| Rang | Optimierung | Δ Prüfstation (im Paket) | Δ Teile | Präzisionsrisiko | Aufwand |
|---|---|---|---|---|---|
| 1 | O1 Schnellmodus Bewegung/Grundstellung | −160 bis −265 s | 0 | niedrig (Bilder, Freiheitsgrad-Status belegen) | 0,5 T |
| 2 | O3 Verknüpfen ohne Neuaufzählung | −45 bis −57 s | 0 | keins (Typprüfung Pflicht) | 0,5–1 T |
| 3 | O5 Teile wiederverwenden + Vorrang | −85 bis −120 s | 0 | niedrig | 2 T |
| 4 | O12 Review schlank (Nutzer) | −100 bis −360 s | 0 bis −100 s | im Bogen nicht gemessen | 0,5 T |
| 5 | O14 Fast Mode / effort (Nutzer) | −60 bis −200 s | −30 bis −60 s | Fast Mode keins laut Doku; effort: `richtig` | 0,1 T |
| 6 | O9 Einschraublänge | ~−10 s (Erwartung) | 0 | positiv (F6 sicher) | 1–1,5 T |
| 7 | O10 Prüfer-Lesepaket | −8 bis −20 s | −2 bis −5 s | gering (Fallen-Nachweis) | 0,5–1 T |
| 8 | O13 Skill-Kleinkorrekturen | −15 bis −30 s | −3 bis −8 s | keins | 0,25–0,5 T |
| 9 | O11 Prüfer-Frontmatter | −6 bis −18 s | −2 bis −8 s | mittel (F1–F3) | 0,25 T |
| 10 | O2 Handles Bewegungsprüfung | −6 bis −8 s | 0 | keins | 0,25–0,5 T |
| 11 | O7 A1/A2 Animation | −5 bis −9 s (A2 mit O5 ~0) | −2 bis −5 s | niedrig | 0,5 T |
| 12 | O6 DISPID-Cache | −5 bis −15 s | −1 bis −3 s | mittel (Stufe 2) | 0,5–2 T |
| 13 | O8 Normbohrung B, C, F | −1 bis −4 s (mit O5) | ~−1 s | niedrig | je 0,25–0,5 T |
| 14 | O4 Kleinkram Bewegungslauf | −0,5 bis −3 s | 0 | keins | 0,25 T |

### 5.3 Empfohlene Reihenfolge

| Umbau | Inhalt | Erwartete Wirkung | Score-Δ geschätzt | Risiko / Abnahme |
|---|---|---|---|---|
| **U1 Baugruppen-Latenz** | O1 + O2 + O3 + O4 + A1 (gleiche Dateien: `pruefen.py`, `bau.py`, `sw_baugruppe.py`, `sw_bewegung.py`, `bilder.py`) | Prüfstation −285 bis −395 s (prüfen 377 → ~120 s, verknüpfen 87 → ~30 s, Grundstellung 22 → ~4 s); Teile −2 s | **+0,27 bis +0,37** | mittel: Pixelvergleich der Bilder, Zahnstangentrieb-Negativfall Freiheitsgrad 2, Schattenvergleich `GetLastFeatureAdded` unter `schnell` |
| **U2 Teile wiederverwenden** | O5 inkl. Vorrang-Reihenfolge; gebündelt mit O12, falls der Nutzer zustimmt – sonst in U1 mitnehmen oder mit O13 bündeln | −85 bis −120 s (O5), mit O12 −100 bis −360 s zusätzlich | +0,08 bis +0,12 allein; mit O12 +0,17 bis +0,45 | mittel: doppelter Regressionsbau, Prüfbericht Wert für Wert gleich; `teile_wiederverwendet` in jedem Lauf |
| **U3 Fast Mode** (nur falls als Umbau zugelassen) | O14 für die Konstruktions- bzw. Lauf-Agenten | Teile −30 bis −60 s, Stehlager −50 bis −100 s, Prüfstation −60 bis −200 s | +0,3 bis +0,9 | niedrig für Qualität; Kosten beim Nutzer; drückt die Prüfstation in den steilen Bereich unter ~450 s, deshalb vor U4 |
| **U4 Prüf- und Agentenpaket** | O9 + O10 + O11 + O13 (ein gemeinsamer Fallen-Nachweis 8 × 3) | Prüfstation −45 bis −100 s, Teile −9 bis −21 s, Stehlager −10 bis −25 s, F6 sicher | +0,15 bis +0,5 | mittel: Fallen-Sperre (`effort: medium` an F1–F3 nur nach Serie), Fehlalarme der Einschraubregel (Gegenprobe Lauf 28) |
| **U5 Reserve** | nach neuem Profil: A2 + O8 B/C gebündelt, oder O6 Stufe 1, oder Ersatzkandidat „abgeleitete Prüfwerte“ | −5 bis −30 s bzw. Fehlerpunkte | +0,02 bis +0,13 (Präzisionshebel bis +0,6) | je nach Wahl |

Begründung:
- **U1 zuerst:** größter und billigster Hebel, präzisionsneutral, sobald die Bilder abgesichert sind. Er verändert die
  Profile grundlegend (B1 schrumpft) – **danach neu profilieren**, bevor O6 oder O8 gewählt werden.
- **O5 nicht allein:** liegt allein unter +0,3; bündeln (mit O12, sonst in U1 oder mit O13).
- **Agentenhebel spät:** ihre Sekunden zählen an der Prüfstation erst unter ~420 s.
- **Präzisionssperre:** U4 trägt sie (Prüfer-Änderungen), darum mit gemeinsamem Fallen-Nachweis und O9 vorab im selben
  Umbau, damit F6 nicht am Prüfer hängt.

**Ersatzkandidaten**, falls ein Umbau verworfen wird:
1. **Abgeleitete Prüfwerte nachrechnen** (Präzisionshebel, außerhalb dieser Recherche): `validieren` rechnet von Hand
   gesetzte Baugruppen-Prüfwerte gegen die Spec nach – d5-Stehlager hatte dadurch 3 Fehlerpunkte; je vermiedenem
   Fehlerpunkt +0,35 bis +0,6. Ersatz für U4/U5, falls Durchgang 0 Fehlerpunkte zeigt.
2. effort medium für den Hauptagenten statt Fast Mode (+0,07 bis +0,21), nur wenn alle Aufgaben `richtig` bleiben.
3. Dokumente öffnen im Prüfen unter `schnell` (35× `OpenDoc6` 31,6 s, außerhalb `schnell`) – unbelegt, vorher Profil-Spike.
4. O3 nur mit `FeatureByPositionReverse(0)`, falls `GetLastFeatureAdded` unter `schnell` scheitert (−33 bis −42 s).

**Endstand grob:** ohne Fast Mode und ohne Review-Änderung +0,4 bis +0,85 → ~5,7–6,2 (vom vorläufigen 5,3). Die
„6,5–7,0“ aus BTP §7 sind nur mit O12/O14 oder einem Präzisionshebel erreichbar.

## 6. Vor Durchgang 0 klären (Einrichtung, kein Umbau)

1. **Bemaßungsbezug mergen** (BTP §9.2). Als einer der 5 Umbauten käme er auf ~+0,14 und scheiterte an §5.1. Er
   kollidiert mit O3 (`verknuepfe`, `bau.py:248-250`) und O5 (`swki/pruefung/messen.py`, `kontext_aus_datei`).
2. **Konstruktionsreview im Messlauf:** Läuft er in `MESS-*` bzw. bei der Prüfstation-Änderung (Maß + Schraubenlänge)?
   Er bestimmt den Bezug um 174–362 s. Nutzerentscheidung (Regel der Retro Etappe 4).
3. **Fast Mode / effort:** Betriebsstandard vor Durchgang 0 oder als Umbau zugelassen? Kosten über Nutzungsguthaben.
4. **Schwelle §5.1:** Bündeln ausdrücklich erlauben (oder Schwelle für die Prüfstation über 420 s senken) – sonst
   besteht kaum ein Einzelumbau.
5. **2-min-Live-Messung** an der Prüfstation: eine Stellung mit Aufzählung, `zustand`, Interferenz – mit und ohne
   `schnell`, dazu je Schalter einzeln (welcher Schalter wirkt; ob Bilder billiger werden). Bestätigt den Kernbefund §2
   für Aufrufe direkt nach `SetSystemValue3`/`EditRebuild3`.
6. **`CommandInProgress` zurücksetzen** am Anfang von `bauen`/`pruefen` und in `werkzeuge/sw_neustart.py` (geteilte
   SolidWorks-Instanz; Nutzereinstellungen aus A1/A2 ebenso).
7. **Messbasis:** `tokens_gewichtet` d5-durchlicht-1 neu gerechnet 223k gegen 269k in `kpi.json` (gleiche Formel,
   `werkzeuge/messstand/transkript.py:90-103`) – Ursache klären, der Teilscore Aufwand hängt am Bezug. Nach dem Merge
   von Bemaßungsbezug die Prüfstation neu profilieren.
8. **BTP-Ausgangslauf für O5:** zwischen Löschen des Arbeitsordners und Start des Abtasters bauen, Protokoll im
   Auftragsordner des Lauf-Worktrees, von der KPI-Zählung ausnehmen.

## 7. Offene Fragen (für Umsetzung, nicht blockierend)

- Gilt ein Verknüpfungs-Handle nach `SetSuppression2` weiter (O2)? Bleibt ein IMate2-Handle (`GetSpecificFeature2`) über
  Neuaufbauten aktuell (O3 b: 1 statt 2 Zugriffe)? Findet `IAssemblyDoc.FeatureByName` Verknüpfungen als Unterfeatures
  (Kontrolle in `loesche` ohne Aufzählung)?
- Senkt O1 die Speicherspitze der Prüfstation (14,3 GB; Robustheit 5 %)? Unbekannt.
- Wie oft greift die Normbohrungs-Wiederholung nach Bemaßungsbezug (Zählfeld aus O8 B, `werkzeuge.bau_wiederholen`
  n ≥ 50)?
- Einschraublänge: Faktoren mit ≥ 2 Quellen belegen; Kunststoffe (ABS in 10 Specs) Richtwert oder nur Hinweis;
  Festigkeitsklasse der Schraube berücksichtigen?
- Aus Datei geöffnete Teile haben keinen Bau-/Undo-Verlauf – senkt O5 die Speicherspitze beim Bauen? Nicht gemessen.

## 8. Korrekturen am Audit

- **B1:** kein reines Bindungsproblem; der Prüfen-Anteil ist Latenz außerhalb `sw.schnell` (§2). Hebel 1 des Audits
  („früh gebundenes COM“) wird zu „Schnellmodus + weniger Roundtrips“; makepy/comtypes verworfen.
- **B6 / Hebel 7:** Normbohrung median 1,9–2,4 s seit 09.10. (nicht 7,1 s); Wirkung −6 bis −9 s statt −30 bis −50 s.
- **B8:** Konstruktionsreview (seit 11.10.) fehlt in Audit und BTP-Schätzung: 174–362 s je Freigabe-Vorlage.
- **B5:** „nur die neue Verknüpfung prüfen“ wörtlich würde die Ausrichtungsumkehr-Erkennung (S12 Z.5) verlieren; richtig
  ist „alle gesetzten Ausrichtungen über Handles“ (O3).
